"""One-shot deploy: bootstrap, build, and deploy every inbox's site.

Reusable entry point for the setup wizard and as a CLI (`python -m apps.workflow_engine.deploy_once`).
Uses the provider registry to resolve the correct deploy implementation per inbox.
"""
from __future__ import annotations
import sys
from pathlib import Path
from typing import Callable

from . import site_bootstrap
from .config import Config, InboxConfig, load
from .logging_setup import get, setup
from .providers import get_provider, list_providers

log = get("deploy_once")


# on_progress(inbox_slug, phase, detail) — phase in {bootstrap, install, build, deploy, done, failed}
ProgressCb = Callable[[str, str, str], None]


def _noop(_slug: str, _phase: str, _detail: str) -> None:
    pass


def deploy_inbox(cfg: Config, inbox: InboxConfig, on_progress: ProgressCb = _noop) -> dict:
    """Bootstrap, build, and deploy one inbox. Returns {slug, provider, url, ok, error}."""
    # Determine provider for this inbox
    provider_name = inbox.hosting_provider or "siteground"
    result = {
        "slug": inbox.slug,
        "provider": provider_name,
        "url": inbox.site_url,
        "ok": False,
        "error": None,
    }
    try:
        provider = get_provider(provider_name)
        on_progress(inbox.slug, "bootstrap", f"creating runtime/sites/{inbox.slug}")
        site_dir = site_bootstrap.ensure_site(inbox)

        on_progress(inbox.slug, "install", "npm install + build")
        build_result = provider.build(
            site_dir,
            site_url=inbox.site_url or "https://example.com",
            site_name=inbox.site_name or inbox.slug,
            site_base=inbox.site_base or "/",
        )
        on_progress(inbox.slug, "build", f"built dist at {build_result.dist_dir}")

        on_progress(inbox.slug, "deploy", f"uploading via {provider_name}")
        # Build provider-specific config from the full config
        provider_config = _build_provider_config(cfg, inbox, provider_name)
        deploy_result = provider.deploy(build_result, provider_config)

        on_progress(inbox.slug, "done", deploy_result.url)
        result["ok"] = True
        result["url"] = deploy_result.url
        result["target"] = deploy_result.target
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        log.exception("Deploy failed for inbox %s", inbox.slug)
        result["error"] = err
        on_progress(inbox.slug, "failed", err)
    return result


def _build_provider_config(cfg: Config, inbox: InboxConfig, provider_name: str) -> dict:
    """Build provider-specific config dict from the full Config object."""
    base = {
        "slug": inbox.slug,
        "site_url": inbox.site_url,
        "remote_path": inbox.remote_path,
    }
    # Merge provider-specific section
    provider_section = getattr(cfg, provider_name, None)
    if provider_section is not None:
        # Convert dataclass to dict
        if hasattr(provider_section, "__dataclass_fields__"):
            for field_name in provider_section.__dataclass_fields__:
                base[field_name] = getattr(provider_section, field_name)
        else:
            base.update(provider_section)
    return base


def deploy_all(cfg: Config, on_progress: ProgressCb = _noop) -> list[dict]:
    """Deploy every inbox in cfg sequentially. Continues on per-inbox failure."""
    results: list[dict] = []
    for inbox in cfg.inboxes:
        results.append(deploy_inbox(cfg, inbox, on_progress))
    return results


def main() -> None:
    setup()
    cfg = load()
    log.info("Available providers: %s", list_providers())
    results = deploy_all(cfg, on_progress=lambda s, p, d: log.info("[%s] %s: %s", s, p, d))
    failed = [r for r in results if not r["ok"]]
    if failed:
        for r in failed:
            log.error("Inbox %s failed: %s", r["slug"], r["error"])
        sys.exit(1)
    log.info("Deploy complete — starting listener")
    from . import listener as _listener
    _listener.run_idle(cfg)


if __name__ == "__main__":
    main()
