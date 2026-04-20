"""Prompt Lab — Flask UI for iterating on the site-builder prompt against
multiple open-weight models hosted on OpenRouter.

Run:
    python -m apps.prompt_lab.server

The app listens on http://localhost:5050 by default (override with
PROMPT_LAB_PORT). API key is never persisted; pass it in the UI each time, or
set OPENROUTER_API_KEY in .env / the environment.
"""
from __future__ import annotations
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request, send_file

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:
    pass

from apps.prompt_lab import deploy_sim, defaults, openrouter
from apps.prompt_lab.models import CATALOGUE


app = Flask(__name__, template_folder="templates", static_folder="static")


@app.get("/")
def index():
    return render_template(
        "index.html",
        models=[
            {
                "label": m.label,
                "slug": m.openrouter_slug,
                "notes": m.notes,
            }
            for m in CATALOGUE
        ],
        system_default=defaults.system_for("synthesise_and_fold_in"),
        user_default_synthesis=defaults.default_user_for("synthesise_and_fold_in"),
        user_default_topic=defaults.default_user_for("topic_curation"),
        topic_md_default=defaults.SAMPLE_TOPIC_MD,
        existing_threads_default=defaults.SAMPLE_EXISTING_THREADS,
        existing_entries_default=defaults.SAMPLE_EXISTING_ENTRIES,
        has_env_api_key=bool(os.environ.get("OPENROUTER_API_KEY")),
    )


@app.post("/api/run")
def api_run():
    data = request.get_json(force=True)
    api_key = data.get("api_key") or os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        return jsonify({"error": "missing OpenRouter API key"}), 400

    system = data.get("system") or ""
    user = data.get("user") or ""
    models = data.get("models") or []
    if not models:
        return jsonify({"error": "select at least one model"}), 400
    if not system.strip() or not user.strip():
        return jsonify({"error": "system and user prompts must be non-empty"}), 400

    temperature = float(data.get("temperature", 0.4))
    max_tokens = int(data.get("max_tokens", 4096))

    def _one(m):
        return openrouter.run(
            api_key=api_key,
            model_label=m.get("label") or m.get("slug"),
            slug=m.get("slug"),
            system=system, user=user,
            temperature=temperature, max_tokens=max_tokens,
        )

    # Run models in parallel so the slowest one doesn't block the rest.
    with ThreadPoolExecutor(max_workers=min(8, len(models))) as pool:
        results = list(pool.map(_one, models))

    return jsonify({
        "results": [
            {
                "model_label": r.model_label,
                "slug": r.slug,
                "ok": r.ok,
                "duration_ms": r.duration_ms,
                "raw_text": r.raw_text,
                "parsed": r.parsed,
                "error": r.error,
                "usage": r.usage,
            }
            for r in results
        ]
    })


@app.post("/api/deploy")
def api_deploy():
    data = request.get_json(force=True)
    plan = data.get("plan") or {}
    model_label = data.get("model_label") or "unknown"
    topic_md = data.get("topic_md") or ""
    seed_threads = data.get("seed_threads") or []
    seed_entries = data.get("seed_entries") or []

    if not isinstance(plan, dict) or "operations" not in plan:
        return jsonify({"error": "plan must be an object with an 'operations' array"}), 400

    # Run the deploy in a background thread so the UI can poll for progress.
    result = {"preview_id": None}
    done = threading.Event()

    def _go():
        result["preview_id"] = deploy_sim.deploy_plan(
            model_label=model_label, plan=plan, topic_md=topic_md,
            seed_threads=seed_threads, seed_entries=seed_entries,
        )
        done.set()

    t = threading.Thread(target=_go, daemon=True)
    t.start()
    # Block briefly so the client gets a preview_id back; state goes through
    # the polling endpoint after that.
    done.wait(timeout=1.5)
    # If the job wasn't even registered yet, wait a touch longer.
    if not result["preview_id"]:
        done.wait(timeout=3.0)
    return jsonify({"preview_id": result["preview_id"]}), 202


@app.get("/api/deploy/<preview_id>")
def api_deploy_status(preview_id):
    state = deploy_sim.get_state(preview_id)
    if not state:
        return jsonify({"error": "unknown preview_id"}), 404
    return jsonify(asdict(state))


@app.get("/api/deploys")
def api_deploys():
    return jsonify({"deploys": deploy_sim.list_states()})


# Static serving of the built sites. This is what "deployment" means in the
# lab — the dist/ output is reachable at /preview/<id>/ exactly as it would
# be on the real hosting provider's document root.
@app.get("/preview/<preview_id>/")
@app.get("/preview/<preview_id>/<path:rel>")
def serve_preview(preview_id, rel=""):
    resolved = deploy_sim.serve_file(preview_id, rel)
    if resolved is None:
        state = deploy_sim.get_state(preview_id)
        if state and state.phase != "ready":
            return Response(
                f"preview {preview_id} is {state.phase}: {state.detail}",
                status=409, mimetype="text/plain",
            )
        return Response("not found", status=404, mimetype="text/plain")
    path, mime = resolved
    return send_file(path, mimetype=mime)


def main() -> None:
    port = int(os.environ.get("PROMPT_LAB_PORT", "5050"))
    print(f"prompt-lab listening on http://localhost:{port}")
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
