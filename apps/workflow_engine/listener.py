"""IMAP IDLE listener. Pulls new messages, hands them to the dispatcher."""
from __future__ import annotations
import argparse
import time
from pathlib import Path
from typing import Any

from imap_tools import MailBox, AND, MailMessage

from . import config as cfg_mod
from . import dispatcher, orchestrator
from .logging_setup import get, setup
from .state import ProcessedLog

log = get("listener")


def _email_dict(msg: MailMessage) -> dict[str, Any]:
    return {
        "message_id": msg.uid and f"<uid:{msg.uid}>" or msg.headers.get("message-id", [""])[0],
        "from": msg.from_,
        "to": msg.to,
        "subject": msg.subject or "",
        "date": msg.date_str,
        "text": msg.text or "",
        "html": msg.html or "",
        "headers": {k.lower(): (v[0] if isinstance(v, (list, tuple)) and v else v)
                    for k, v in (msg.headers or {}).items()},
    }


def _flat_headers(msg: MailMessage) -> dict[str, str]:
    """Flat header dict including To/Delivered-To for routing."""
    out: dict[str, str] = {}
    for k, v in (msg.headers or {}).items():
        if isinstance(v, (list, tuple)) and v:
            out[k] = v[0]
        elif isinstance(v, str):
            out[k] = v
    out["to"] = msg.to[0] if msg.to else out.get("to", "")
    return out


def run_once(cfg: cfg_mod.Config) -> int:
    processed = ProcessedLog(cfg.state_dir / "processed.jsonl")
    handled = 0
    with MailBox(cfg.imap.host, port=cfg.imap.port).login(
        cfg.imap.user, cfg.imap.password, initial_folder=cfg.imap.folder,
    ) as mb:
        for msg in mb.fetch(AND(seen=False), mark_seen=False, bulk=True):
            email = _email_dict(msg)
            mid = email["message_id"]
            if processed.seen(mid):
                mb.flags(msg.uid, ["\\Seen"], True)
                continue
            ib = dispatcher.route(cfg, _flat_headers(msg))
            if not ib:
                processed.record(mid, "(none)", outcome="no_inbox_match")
                mb.flags(msg.uid, ["\\Seen"], True)
                continue
            try:
                orchestrator.process(cfg, ib, email, processed)
                handled += 1
            finally:
                mb.flags(msg.uid, ["\\Seen"], True)
    return handled


def run_idle(cfg: cfg_mod.Config) -> None:
    """Persistent IMAP IDLE loop with reconnect."""
    backoff = 2.0
    while True:
        try:
            with MailBox(cfg.imap.host, port=cfg.imap.port).login(
                cfg.imap.user, cfg.imap.password, initial_folder=cfg.imap.folder,
            ) as mb:
                log.info("connected; entering IDLE loop")
                backoff = 2.0
                # Drain any unread first.
                run_once(cfg)
                while True:
                    responses = mb.idle.wait(timeout=29 * 60)
                    log.info("IDLE wake (responses=%s); checking for new mail", responses)
                    run_once(cfg)
        except Exception as e:
            log.warning("listener error: %s; reconnecting in %.1fs", e, backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60.0)


def _log_startup_diagnostics(cfg: cfg_mod.Config) -> None:
    log.info("=== Engine Startup Diagnostics ===")
    log.info("Loaded %d inbox(es):", len(cfg.inboxes))
    for ib in cfg.inboxes:
        provider = ib.hosting_provider or "siteground"
        log.info("  [%s] %s -> %s (provider: %s, url: %s)",
                 ib.slug, ib.address, ib.site_name or ib.slug, provider, ib.site_url or "N/A")
    log.info("Global allowed senders: %s", cfg.global_allowed_senders or "(none)")
    log.info("Route map:")
    for ib in cfg.inboxes:
        log.info("  %s -> %s", ib.address, ib.slug)
    log.info("=====================================")


def _log_startup_diagnostics(cfg: cfg_mod.Config) -> None:
    log.info("=== Engine Startup Diagnostics ===")
    log.info("Loaded %d inbox(es):", len(cfg.inboxes))
    for ib in cfg.inboxes:
        provider = ib.hosting_provider or "siteground"
        log.info("  [%s] %s -> %s (provider: %s, url: %s)",
                 ib.slug, ib.address, ib.site_name or ib.slug, provider, ib.site_url or "N/A")
    log.info("Global allowed senders: %s", cfg.global_allowed_senders or "(none)")
    log.info("Route map:")
    for ib in cfg.inboxes:
        log.info("  %s -> %s", ib.address, ib.slug)
    log.info("=====================================")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--once", action="store_true", help="poll once and exit (for cron / testing)")
    p.add_argument("--dry-run", action="store_true",
                   help="run synthesis but do not write, build, or deploy")
    p.add_argument("--config", type=Path, default=None)
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args()
    setup(level=args.log_level, log_file=cfg_mod.STATE_DIR / "listener.log")
    cfg = cfg_mod.load(args.config)
    if args.dry_run:
        cfg.dry_run = True
    _log_startup_diagnostics(cfg)
    if args.once:
        n = run_once(cfg)
        log.info("processed %d message(s)", n)
        return
    run_idle(cfg)


if __name__ == "__main__":
    main()
