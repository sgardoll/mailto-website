"""Create sites/<slug>/ from the template the first time an inbox is hit."""
from __future__ import annotations
import argparse
import json
import shutil
from pathlib import Path

from .config import REPO_ROOT, SITES_DIR, STATE_DIR, TEMPLATE_DIR, InboxConfig, load
from .logging_setup import get, setup

log = get("site_bootstrap")


def site_path(slug: str) -> Path:
    return SITES_DIR / slug


def ensure_site(inbox: InboxConfig, *, force: bool = False) -> Path:
    target = site_path(inbox.slug)
    if target.exists() and not force:
        return target
    if force and target.exists():
        log.warning("Removing existing site at %s (force=True)", target)
        shutil.rmtree(target)
    log.info("Bootstrapping site for inbox '%s' at %s", inbox.slug, target)
    shutil.copytree(TEMPLATE_DIR, target, ignore=shutil.ignore_patterns(
        "node_modules", "dist", ".astro",
    ))
    # Stamp inbox-specific metadata into a small file the workflow can read.
    (target / ".inbox.json").write_text(
        f'{{"slug": "{inbox.slug}", "address": "{inbox.address}", "site_name": "{inbox.site_name or inbox.slug}"}}\n'
    )
    # PROF-01: bootstrap per-inbox profile.json (idempotent; not in site git tree — see .gitignore).
    profile_dir = STATE_DIR / inbox.slug
    profile_dir.mkdir(parents=True, exist_ok=True)
    profile_path = profile_dir / "profile.json"
    if not profile_path.exists():
        profile_path.write_text(json.dumps({
            "schema_version": "1",
            "inbox_slug": inbox.slug,
            "state": {},
        }, indent=2))
        log.info("Wrote profile.json for inbox '%s' at %s", inbox.slug, profile_path)
    return target


def main() -> None:
    setup()
    p = argparse.ArgumentParser()
    p.add_argument("--inbox", required=True, help="inbox slug")
    p.add_argument("--force", action="store_true")
    args = p.parse_args()
    cfg = load()
    ib = next((i for i in cfg.inboxes if i.slug == args.inbox), None)
    if not ib:
        raise SystemExit(f"No inbox '{args.inbox}' in config.")
    path = ensure_site(ib, force=args.force)
    print(path)


if __name__ == "__main__":
    main()
