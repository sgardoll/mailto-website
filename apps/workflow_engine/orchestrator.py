"""End-to-end processing for one inbound email."""
from __future__ import annotations
import time
from pathlib import Path
from typing import Any

from . import apply_changes, build_and_deploy, distill, git_ops, ingest, lm_studio, notify, plan as _plan_stage, prompt, site_bootstrap, site_index, topic_curator
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
    idx = site_index.build(site_dir, inbox_slug=inbox.slug, site_name=inbox.site_name or inbox.slug)

    try:
        normalized_input = ingest.ingest(email)
        log.info("ingest source_type=%s source_url=%s",
                 normalized_input["source_type"], normalized_input["source_url"])

        if getattr(inbox, "pipeline_version", "v1") == "v2":
            # DISTILL stage
            try:
                spec = distill.distill(normalized_input, cfg.lm_studio)
            except distill.DistillFailed as e:
                log.error("DISTILL failed for %s: %s", mid, e)
                _reply_failure(cfg, inbox, email, f"DISTILL failed: {e}")
                processed.record(mid, inbox.slug, outcome="distill_failed", error=str(e))
                return

            if spec is None:
                # D-13/D-17: informational email — upgrade_state_only, skip BUILD
                log.info("DISTILL returned null mechanic for %s; routing to upgrade_state_only", mid)
                processed.record(mid, inbox.slug, outcome="upgrade_state_only")
                return

            # PLAN stage
            routing = _plan_stage.plan(spec, site_dir, cfg.lm_studio)
            log.info("PLAN routing=%s for %s (kind=%s module_id=%s)", routing, mid, spec.kind, spec.module_id)
            # Phase 17/18 will hook BUILD + INTEGRATE here using spec + routing
            processed.record(mid, inbox.slug, outcome=f"v2_planned_{routing}")
            return
        # v1 path falls through unchanged below

        new_topic = topic_curator.update_topic(
            site_dir=site_dir, idx=idx, email=email,
            lm_cfg=cfg.lm_studio, dry_run=cfg.dry_run,
        )
        idx.topic = new_topic

        sys = prompt.system_for("synthesise_and_fold_in")
        user = prompt.synthesis_prompt_user(idx, email)
        plan = lm_studio.chat_json(cfg.lm_studio, system=sys, user=user)

        log.info("plan rationale: %s", plan.get("rationale"))
        written = apply_changes.apply(site_dir, plan, dry_run=cfg.dry_run)

        if cfg.dry_run:
            processed.record(mid, inbox.slug, outcome="dry_run",
                             rationale=plan.get("rationale"), files=[str(p) for p in written])
            return

        # Build; on failure, roll back content writes via git restore so site
        # stays buildable.
        try:
            result = build_and_deploy.build(site_dir, inbox=inbox)
        except build_and_deploy.BuildFailed as e:
            log.error("build failed; rolling back: %s", e)
            _git_restore(cfg.repo_root, str(site_dir.relative_to(cfg.repo_root)))
            _reply_failure(cfg, inbox, email, str(e))
            processed.record(mid, inbox.slug, outcome="build_failed", error=str(e))
            return

        try:
            build_and_deploy.deploy(result, cfg=cfg, inbox=inbox)
        except build_and_deploy.DeployFailed as e:
            log.error("deploy failed: %s", e)
            _reply_failure(cfg, inbox, email, str(e))
            processed.record(mid, inbox.slug, outcome="deploy_failed", error=str(e))
            return

        sha = git_ops.commit_and_push(
            cfg.repo_root,
            message=_commit_message(inbox, plan),
            branch=cfg.git_branch,
            paths=[str(site_dir.relative_to(cfg.repo_root))],
            push=cfg.git_push,
        )

        _reply_success(cfg, inbox, email, plan, sha)
        processed.record(
            mid, inbox.slug, outcome="ok",
            rationale=plan.get("rationale"),
            files=[str(p.relative_to(cfg.repo_root)) for p in written],
            commit=sha,
        )

    except Exception as e:
        log.exception("orchestrator failed for %s", mid)
        _reply_failure(cfg, inbox, email, str(e))
        processed.record(mid, inbox.slug, outcome="error", error=str(e))


def _git_restore(repo: Path, path: str) -> None:
    """Roll back both tracked modifications and untracked new files under path.

    git restore only reverts tracked files; without the clean step, a failed
    build leaves behind newly-written entry/thread .md files that poison the
    next run (same schema error repeats forever).
    """
    import subprocess
    r1 = subprocess.run(["git", "restore", "--source=HEAD", "--", path],
                        cwd=repo, capture_output=True, text=True)
    if r1.returncode != 0:
        log.error("git restore failed: %s", r1.stderr.strip())
    r2 = subprocess.run(["git", "clean", "-fd", "--", path],
                        cwd=repo, capture_output=True, text=True)
    if r2.returncode != 0:
        log.error("git clean failed: %s", r2.stderr.strip())


def _commit_message(inbox: InboxConfig, plan: dict) -> str:
    head = f"[{inbox.slug}] integrate email"
    rationale = (plan.get("rationale") or "").strip().splitlines()
    body = "\n".join(rationale[:8])
    ops = plan.get("operations") or []
    files = ", ".join(f"{o.get('collection')}/{o.get('slug')}" for o in ops)
    return f"{head}\n\n{body}\n\nfiles: {files}\n"


def _reply_success(cfg: Config, inbox: InboxConfig, email: dict, plan: dict, sha: str | None) -> None:
    if not (cfg.smtp.host and email.get("from")):
        return
    summary = (plan.get("reply_summary") or plan.get("rationale") or "Integrated.").strip()
    files = ", ".join(f"{o.get('collection')}/{o.get('slug')}" for o in (plan.get("operations") or []))
    body = (
        f"{summary}\n\n"
        f"Files touched: {files or '(none)'}\n"
        f"Site: {inbox.site_url or '(no URL configured)'}\n"
        f"Commit: {sha or '(no commit)'}\n"
    )
    notify.send(
        cfg.smtp,
        to=email["from"],
        subject=f"Re: {email.get('subject', '(no subject)')}",
        body=body,
        in_reply_to=email.get("message_id"),
    )


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
