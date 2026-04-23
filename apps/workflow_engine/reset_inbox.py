"""Wipe all modules for one inbox and redeploy a blank SPA.

Usage:
    python -m apps.workflow_engine.reset_inbox --inbox newstuff

Keeps node_modules / built tooling intact so the rebuild is fast. Clears:
  - runtime/sites/<slug>/public/spa/<module_id>/  (all module dirs)
  - runtime/sites/<slug>/public/spa/spa_manifest.json  -> empty
  - runtime/sites/<slug>/.git  (local module history)
  - runtime/state/processed.jsonl entries for this inbox

Then rebuilds and redeploys so the live site shows an empty SPA shell.
"""
from __future__ import annotations
import argparse
import json
import shutil
import sys

from . import build_and_deploy
from .config import load
from .logging_setup import get, setup

log = get("reset_inbox")


def reset_inbox(slug: str) -> None:
    cfg = load()
    inbox = next((ib for ib in cfg.inboxes if ib.slug == slug), None)
    if not inbox:
        raise SystemExit(f"no inbox with slug={slug!r} in config.yaml")

    site_dir = cfg.sites_dir / inbox.slug
    if not site_dir.exists():
        raise SystemExit(f"site dir missing: {site_dir}. Run site_bootstrap first.")

    spa_dir = site_dir / "public" / "spa"
    manifest_path = spa_dir / "spa_manifest.json"

    removed = []
    if spa_dir.exists():
        for child in spa_dir.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
                removed.append(child.name)

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"schema_version": "1", "modules": []}, indent=2))
    log.info("Cleared %d module dir(s): %s", len(removed), removed)

    git_dir = site_dir / ".git"
    if git_dir.exists():
        shutil.rmtree(git_dir)
        log.info("Removed local module git repo at %s", git_dir)

    processed_log = cfg.state_dir / "processed.jsonl"
    if processed_log.exists():
        lines = processed_log.read_text().splitlines()
        kept = [l for l in lines if f'"{slug}"' not in l]
        processed_log.write_text("\n".join(kept) + ("\n" if kept else ""))
        log.info("Dropped %d processed.jsonl entries for %s", len(lines) - len(kept), slug)

    log.info("Rebuilding + redeploying %s ...", slug)
    result = build_and_deploy.build(site_dir, inbox=inbox)
    build_and_deploy.deploy(result, cfg=cfg, inbox=inbox)
    log.info("Done. %s is now an empty SPA at %s", slug, inbox.site_url)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--inbox", required=True, help="inbox slug from config.yaml")
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args()
    setup(level=args.log_level)
    reset_inbox(args.inbox)


if __name__ == "__main__":
    main()
