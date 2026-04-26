"""Listener dashboard — in-process Flask app served on the listener's daemon thread.

Replaces the old stdlib health handler. Exposes a single-page UI over the top
of the listener for visibility + slug control (pause/resume/delete/reset).
"""
from __future__ import annotations

import fcntl
import json
import socket
import threading
import time
from pathlib import Path
from typing import Callable
from werkzeug.serving import make_server

from flask import Flask, jsonify, render_template, request

from . import config as cfg_mod
from . import lm_studio as _lm_mod
from . import slug_ops
from .logging_setup import get

log = get("dashboard")

HERE = Path(__file__).resolve().parent
PORT_CANDIDATES = (8899, 8900, 8901, 8902)


def _port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _pick_port(preferred: int) -> int:
    for p in (preferred, *PORT_CANDIDATES):
        if _port_available(p):
            return p
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _lock_is_held(lock_path: Path) -> bool:
    """True only if a process currently holds an exclusive lock on the file.

    A file that merely exists from a prior run is NOT held.
    """
    if not lock_path.exists():
        return False
    try:
        with open(lock_path, "a+") as f:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                return False
            except BlockingIOError:
                return True
    except OSError:
        return False


def _slug_row(cfg: cfg_mod.Config, ib, health: dict) -> dict:
    slug = ib.slug
    site_dir = cfg.sites_dir / slug
    lock = cfg.state_dir / "locks" / f"{slug}.lock"
    row = {
        "slug": slug,
        "address": ib.address,
        "site_name": ib.site_name or slug,
        "site_url": ib.site_url or "",
        "provider": ib.hosting_provider or "siteground",
        "paused": slug_ops.is_paused(cfg, slug),
        "site_exists": site_dir.exists(),
        "in_flight": _lock_is_held(lock),
        "last_event": None,
        "last_outcome": None,
        "model": ib.model or cfg.lm_studio.model,
    }
    processed = cfg.state_dir / "processed.jsonl"
    if processed.exists():
        for line in reversed(processed.read_text().splitlines()[-500:]):
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("inbox") == slug:
                row["last_event"] = rec.get("ts")
                row["last_outcome"] = rec.get("outcome")
                break
    return row


def create_app(cfg: cfg_mod.Config, health: dict, config_reload: Callable[[], cfg_mod.Config]) -> Flask:
    app = Flask(
        __name__,
        template_folder=str(HERE / "templates"),
        static_folder=str(HERE / "static"),
    )

    def _cfg():
        # Pull a fresh config each request so config.yaml edits are live.
        try:
            return config_reload()
        except Exception as e:
            log.warning("config reload failed, using cached: %s", e)
            return cfg

    @app.route("/")
    def index():
        return render_template("dashboard.html")

    @app.route("/health")
    def health_route():
        return jsonify(health)

    @app.route("/api/slugs")
    def list_slugs():
        c = _cfg()
        return jsonify({
            "slugs": [_slug_row(c, ib, health) for ib in c.inboxes],
            "health": health,
        })

    @app.route("/api/slugs/<slug>/pause", methods=["POST"])
    def api_pause(slug):
        return jsonify(_result_to_dict(slug_ops.pause(_cfg(), slug)))

    @app.route("/api/slugs/<slug>/resume", methods=["POST"])
    def api_resume(slug):
        return jsonify(_result_to_dict(slug_ops.resume(_cfg(), slug)))

    @app.route("/api/slugs/<slug>/reset", methods=["POST"])
    def api_reset(slug):
        return jsonify(_result_to_dict(slug_ops.reset(_cfg(), slug)))

    @app.route("/api/slugs/<slug>", methods=["DELETE"])
    def api_delete(slug):
        return jsonify(_result_to_dict(slug_ops.delete(_cfg(), slug)))

    @app.route("/api/models")
    def list_models():
        downloaded = _lm_mod._list_downloaded_models("lms")
        loaded = _lm_mod._loaded_models("lms")
        return jsonify({
            "downloaded": [{"key": k, "size_gb": round(s / 1e9, 2)} for k, s in downloaded],
            "loaded": loaded,
        })

    @app.route("/api/slugs/<slug>/model", methods=["PATCH"])
    def api_set_model(slug):
        c = _cfg()
        inbox = next((ib for ib in c.inboxes if ib.slug == slug), None)
        if not inbox:
            return jsonify({"error": f"slug {slug!r} not found"}), 404
        data = request.get_json()
        model = data.get("model") if isinstance(data, dict) else None
        if model is not None:
            inbox.model = model or None
            cfg_mod.save_inbox_model(slug, inbox.model)
        return jsonify({"slug": slug, "model": inbox.model or c.lm_studio.model})

    return app


def _result_to_dict(r: slug_ops.OpResult) -> dict:
    return {
        "ok": r.ok,
        "slug": r.slug,
        "action": r.action,
        "steps": r.steps,
        "warnings": r.warnings,
        "error": r.error,
    }


def start_dashboard(
    cfg: cfg_mod.Config,
    health: dict,
    *,
    preferred_port: int = 8899,
    config_reload: Callable[[], cfg_mod.Config] | None = None,
) -> tuple[threading.Thread, int]:
    """Start the dashboard in a daemon thread. Returns (thread, bound_port)."""
    port = _pick_port(preferred_port)
    reload_fn = config_reload or (lambda: cfg)
    app = create_app(cfg, health, reload_fn)
    server = make_server("127.0.0.1", port, app, threaded=True)
    t = threading.Thread(target=server.serve_forever, daemon=True, name="dashboard")
    t.start()
    # Persist port so user can find the UI after launch.
    try:
        port_file = cfg.state_dir / "dashboard.port"
        port_file.parent.mkdir(parents=True, exist_ok=True)
        port_file.write_text(str(port))
    except Exception as e:
        log.warning("failed to write dashboard.port: %s", e)
    log.info("dashboard running on http://127.0.0.1:%d", port)
    return t, port
