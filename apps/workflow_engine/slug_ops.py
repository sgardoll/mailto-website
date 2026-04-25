"""Pause / resume / delete / reset operations for slugs.

Pure(ish) functions the dashboard calls. Each op mutates disk state and
config.yaml and is idempotent-ish — running twice is safe, the second call
is a no-op for the already-removed parts.
"""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from . import config as cfg_mod
from . import site_bootstrap
from .logging_setup import get
from .providers import registry

log = get("slug_ops")


@dataclass
class OpResult:
    ok: bool
    slug: str
    action: str
    steps: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None


def _paused_flag(cfg: cfg_mod.Config, slug: str) -> Path:
    return cfg.state_dir / slug / "paused"


def is_paused(cfg: cfg_mod.Config, slug: str) -> bool:
    return _paused_flag(cfg, slug).exists()


def pause(cfg: cfg_mod.Config, slug: str) -> OpResult:
    res = OpResult(ok=True, slug=slug, action="pause")
    flag = _paused_flag(cfg, slug)
    flag.parent.mkdir(parents=True, exist_ok=True)
    flag.touch(exist_ok=True)
    res.steps.append(f"paused flag: {flag}")
    log.info("paused slug '%s'", slug)
    return res


def resume(cfg: cfg_mod.Config, slug: str) -> OpResult:
    res = OpResult(ok=True, slug=slug, action="resume")
    flag = _paused_flag(cfg, slug)
    if flag.exists():
        flag.unlink()
        res.steps.append(f"removed flag: {flag}")
    else:
        res.steps.append("not paused; no-op")
    log.info("resumed slug '%s'", slug)
    return res


def _remote_delete(cfg: cfg_mod.Config, slug: str, res: OpResult) -> None:
    """Best-effort remote cleanup — warnings only, never raises."""
    ib = next((i for i in cfg.inboxes if i.slug == slug), None)
    if not ib:
        res.warnings.append("no config entry; skipped remote cleanup")
        return
    provider_name = ib.hosting_provider or "siteground"
    try:
        provider = registry.get_provider(provider_name)
    except Exception as e:
        res.warnings.append(f"unknown provider '{provider_name}': {e}")
        return
    delete_fn = getattr(provider, "delete", None)
    if not callable(delete_fn):
        res.warnings.append(f"provider '{provider_name}' has no delete()")
        return
    try:
        provider_cfg = _build_provider_config(cfg, ib)
        delete_fn(provider_cfg)
        res.steps.append(f"remote cleanup via {provider_name}")
    except Exception as e:
        res.warnings.append(f"remote cleanup failed: {e}")


def _build_provider_config(cfg: cfg_mod.Config, ib: Any) -> dict:
    """Assemble the provider config dict the same way deploy_once.py does."""
    provider_name = ib.hosting_provider or "siteground"
    provider_block: dict = {}
    if provider_name == "siteground" and cfg.siteground is not None:
        provider_block = cfg.siteground.model_dump() if hasattr(cfg.siteground, "model_dump") else dict(cfg.siteground.__dict__)
    elif provider_name == "vercel" and getattr(cfg, "vercel", None) is not None:
        provider_block = cfg.vercel.model_dump() if hasattr(cfg.vercel, "model_dump") else dict(cfg.vercel.__dict__)
    provider_block.update({
        "slug": ib.slug,
        "site_url": ib.site_url or "",
        "site_base": ib.site_base or "/",
    })
    return provider_block


def _strip_from_config_yaml(slug: str) -> bool:
    """Remove the inbox entry for `slug` from config.yaml. Returns True if removed."""
    path = cfg_mod.WORKFLOW_DIR / "config.yaml"
    if not path.exists():
        return False
    raw = yaml.safe_load(path.read_text()) or {}
    inboxes = raw.get("inboxes") or []
    new = [ib for ib in inboxes if ib.get("slug") != slug]
    if len(new) == len(inboxes):
        return False
    raw["inboxes"] = new
    path.write_text(yaml.safe_dump(raw, sort_keys=False))
    return True


def _strip_processed_entries(cfg: cfg_mod.Config, slug: str) -> int:
    """Remove processed.jsonl rows for the given slug. Returns count removed."""
    path = cfg.state_dir / "processed.jsonl"
    if not path.exists():
        return 0
    kept: list[str] = []
    removed = 0
    for line in path.read_text().splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            kept.append(line)
            continue
        if rec.get("inbox") == slug:
            removed += 1
            continue
        kept.append(line)
    if removed:
        path.write_text("\n".join(kept) + ("\n" if kept else ""))
    return removed


def _remove_local_artifacts(cfg: cfg_mod.Config, slug: str, res: OpResult) -> None:
    site_dir = cfg.sites_dir / slug
    if site_dir.exists():
        shutil.rmtree(site_dir)
        res.steps.append(f"removed {site_dir}")
    state_dir = cfg.state_dir / slug
    if state_dir.exists():
        shutil.rmtree(state_dir)
        res.steps.append(f"removed {state_dir}")
    lock = cfg.state_dir / "locks" / f"{slug}.lock"
    if lock.exists():
        lock.unlink()
        res.steps.append(f"removed {lock}")
    removed = _strip_processed_entries(cfg, slug)
    if removed:
        res.steps.append(f"stripped {removed} row(s) from processed.jsonl")


def delete(cfg: cfg_mod.Config, slug: str) -> OpResult:
    res = OpResult(ok=True, slug=slug, action="delete")
    _remote_delete(cfg, slug, res)
    _remove_local_artifacts(cfg, slug, res)
    if _strip_from_config_yaml(slug):
        res.steps.append("removed from config.yaml")
    log.info("deleted slug '%s' (steps=%d warnings=%d)", slug, len(res.steps), len(res.warnings))
    return res


def reset(cfg: cfg_mod.Config, slug: str) -> OpResult:
    res = OpResult(ok=True, slug=slug, action="reset")
    ib = next((i for i in cfg.inboxes if i.slug == slug), None)
    if not ib:
        res.ok = False
        res.error = f"no inbox '{slug}' in config"
        return res
    _remote_delete(cfg, slug, res)
    _remove_local_artifacts(cfg, slug, res)
    site_bootstrap.ensure_site(ib, force=True)
    res.steps.append(f"re-bootstrapped site at {cfg.sites_dir / slug}")
    log.info("reset slug '%s'", slug)
    return res
