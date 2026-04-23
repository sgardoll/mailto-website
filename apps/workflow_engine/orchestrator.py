"""End-to-end processing for one inbound email."""
from __future__ import annotations
import time
from pathlib import Path
from typing import Any

from . import build, build_and_deploy, distill, ingest, integrate, notify, plan as _plan_stage, site_bootstrap
from .config import Config, InboxConfig
from .logging_setup import get
from .state import ProcessedLog, file_lock

log = get("orchestrator")


def is_allowed(cfg: Config, inbox: InboxConfig, sender: str) -> bool:
    s = sender.strip().lower()
    if any(s == a.lower() for a in inbox.allowed_senders):
        return True
    if any(s == a.lower() for a in cfg.global_allowed_senders):
        return True
    return False


def process(cfg: Config, inbox: InboxConfig, email: dict[str, Any], processed: ProcessedLog) -> None:
    mid = email.get("message_id") or email.get("subject") or str(time.time())
    if processed.seen(mid):
        log.info("already processed %s; skipping", mid)
        return

    sender = email.get("from", "")
    if not is_allowed(cfg, inbox, sender):
        log.warning("rejecting message %s from %s (not allowed)", mid, sender)
        processed.record(mid, inbox.slug, outcome="rejected_sender", sender=sender)
        return

    lock_path = cfg.state_dir / "locks" / f"{inbox.slug}.lock"
    with file_lock(lock_path):
        _process_locked(cfg, inbox, email, processed, mid)


def _process_locked(
    cfg: Config, inbox: InboxConfig, email: dict[str, Any],
    processed: ProcessedLog, mid: str,
) -> None:
    site_dir = site_bootstrap.ensure_site(inbox)
    integrate.startup_assert_gitignore(site_dir)

    try:
        normalized_input = ingest.ingest(email)
        log.info("ingest source_type=%s source_url=%s",
                 normalized_input["source_type"], normalized_input["source_url"])

        # DISTILL stage
        try:
            spec = distill.distill(normalized_input, cfg.lm_studio)
        except distill.DistillFailed as e:
            log.error("DISTILL failed for %s: %s", mid, e)
            _reply_failure(cfg, inbox, email, f"DISTILL failed: {e}")
            processed.record(mid, inbox.slug, outcome="distill_failed", error=str(e))
            return

        # PLAN stage
        routing = _plan_stage.plan(spec, site_dir, cfg.lm_studio)
        log.info("PLAN routing=%s for %s (kind=%s module_id=%s)", routing, mid, spec.kind, spec.module_id)

        if routing == "upgrade_state_only":
            processed.record(mid, inbox.slug, outcome="upgrade_state_only", module_id=spec.module_id)
            return

        # BUILD stage
        try:
            build_result = build.build(spec, cfg.lm_studio)
        except build.BuildFailed as e:
            log.error("BUILD failed for %s: %s", mid, e)
            _reply_failure(cfg, inbox, email, f"BUILD failed: {e}")
            processed.record(mid, inbox.slug, outcome="build_failed", error=str(e))
            return

        # INTEGRATE stage
        try:
            sha = integrate.integrate(spec, build_result["html_b64"], site_dir, push=False)
        except integrate.IntegrateFailed as e:
            log.error("INTEGRATE failed for %s: %s", mid, e)
            _reply_failure(cfg, inbox, email, f"INTEGRATE failed: {e}")
            processed.record(mid, inbox.slug, outcome="integrate_failed", error=str(e))
            return

        # DEPLOY stage
        try:
            site_build = build_and_deploy.build(site_dir, inbox=inbox)
        except build_and_deploy.BuildFailed as e:
            log.error("SITE BUILD failed for %s: %s", mid, e)
            _reply_failure(cfg, inbox, email, f"Site build failed: {e}")
            processed.record(mid, inbox.slug, outcome="build_failed", error=str(e))
            return

        try:
            build_and_deploy.deploy(site_build, cfg=cfg, inbox=inbox)
        except build_and_deploy.DeployFailed as e:
            log.error("DEPLOY failed for %s: %s", mid, e)
            _reply_failure(cfg, inbox, email, f"Deploy failed: {e}")
            processed.record(mid, inbox.slug, outcome="deploy_failed", error=str(e))
            return

        log.info("pipeline complete for %s: module_id=%s routing=%s sha=%s",
                 mid, spec.module_id, routing, sha)
        processed.record(
            mid, inbox.slug, outcome="ok",
            routing=routing,
            module_id=spec.module_id,
            kind=spec.kind.value,
            commit=sha,
        )

    except Exception as e:
        log.exception("orchestrator failed for %s", mid)
        _reply_failure(cfg, inbox, email, str(e))
        processed.record(mid, inbox.slug, outcome="error", error=str(e))


def _reply_failure(cfg: Config, inbox: InboxConfig, email: dict, err: str) -> None:
    if not (cfg.smtp.host and email.get("from")):
        return
    notify.send(
        cfg.smtp,
        to=email["from"],
        subject=f"[failed] Re: {email.get('subject', '(no subject)')}",
        body=f"Could not integrate this email into the {inbox.slug} site.\n\nError:\n{err}\n",
        in_reply_to=email.get("message_id"),
    )
