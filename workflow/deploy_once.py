"""One-shot deploy: bootstrap, build, and deploy every inbox's site.

Reusable entry point for the setup wizard and as a CLI (`python -m workflow.deploy_once`).
Currently SiteGround-only — other providers are Phase 5 and raise NotImplementedError.
"""
from __future__ import annotations
import sys
from pathlib import Path
from typing import Callable

from . import build_and_deploy, site_bootstrap
from .config import Config, InboxConfig, load
from .logging_setup import get, setup

log = get("deploy_once")


# on_progress(inbox_slug, phase, detail) — phase in {bootstrap, install, build, deploy, done, failed}
ProgressCb = Callable[[str, str, str], None]


def _noop(_slug: str, _phase: str, _detail: str) -> None:
    pass


def deploy_inbox(cfg: Config, inbox: InboxConfig, on_progress: ProgressCb = _noop) -> dict:
    """Bootstrap, build, and deploy one inbox. Returns {slug, url, ok, error}."""
    result = {"slug": inbox.slug, "url": inbox.site_url, "ok": False, "error": None}
    try:
        on_progress(inbox.slug, "bootstrap", f"creating sites/{inbox.slug}")
        site_dir = site_bootstrap.ensure_site(inbox)

        on_progress(inbox.slug, "install", "npm install + build")
        build_result = build_and_deploy.build(site_dir, inbox=inbox)
        on_progress(inbox.slug, "build", f"built dist at {build_result.dist_dir}")

        on_progress(inbox.slug, "deploy", "uploading via SFTP")
        build_and_deploy.deploy(build_result, cfg=cfg, inbox=inbox)

        on_progress(inbox.slug, "done", inbox.site_url)
        result["ok"] = True
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        log.exception("Deploy failed for inbox %s", inbox.slug)
        result["error"] = err
        on_progress(inbox.slug, "failed", err)
    return result


def deploy_all(cfg: Config, on_progress: ProgressCb = _noop) -> list[dict]:
    """Deploy every inbox in cfg sequentially. Continues on per-inbox failure."""
    results: list[dict] = []
    for inbox in cfg.inboxes:
        results.append(deploy_inbox(cfg, inbox, on_progress))
    return results


def _guard_provider_supported(provider: str) -> None:
    if provider and provider != "siteground":
        raise NotImplementedError(
            f"Deploy for provider '{provider}' is not implemented yet. "
            f"Only 'siteground' is supported. See Phase 5."
        )


def main() -> None:
    setup()
    cfg = load()
    results = deploy_all(cfg, on_progress=lambda s, p, d: log.info("[%s] %s: %s", s, p, d))
    failed = [r for r in results if not r["ok"]]
    if failed:
        for r in failed:
            log.error("Inbox %s failed: %s", r["slug"], r["error"])
        sys.exit(1)


if __name__ == "__main__":
    main()
