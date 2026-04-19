"""Validate and apply the model's file operations against a site."""
from __future__ import annotations
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import frontmatter
import yaml

from .logging_setup import get

log = get("apply_changes")

ALLOWED_COLLECTIONS = {"entries", "threads"}
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{0,80}$")
ALLOWED_KEYS = {
    "entries": {"title", "summary", "receivedAt", "source", "tags", "threads"},
    "threads": {"title", "summary", "createdAt", "updatedAt", "tags", "status",
                "relatedEntries", "relatedThreads"},
}
REQUIRED_KEYS = {
    "entries": {"title", "summary", "receivedAt", "threads"},
    "threads": {"title", "summary", "createdAt", "updatedAt"},
}


class InvalidOperation(ValueError):
    pass


def _validate_slug(slug: str) -> None:
    if not SLUG_RE.match(slug):
        raise InvalidOperation(f"slug not kebab-case or too long: {slug!r}")


def _coerce_iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, str) and value:
        # trust; Astro's z.coerce.date will parse
        return value
    return datetime.now(timezone.utc).isoformat()


def _validate_op(op: dict[str, Any]) -> dict[str, Any]:
    if op.get("op") not in {"create", "edit"}:
        raise InvalidOperation(f"unsupported op: {op.get('op')!r}")
    coll = op.get("collection")
    if coll not in ALLOWED_COLLECTIONS:
        raise InvalidOperation(f"collection must be entries|threads, got {coll!r}")
    slug = op.get("slug", "")
    _validate_slug(slug)

    fm = dict(op.get("frontmatter") or {})
    body = op.get("body_markdown") or ""

    # Strip unknown keys defensively.
    fm = {k: v for k, v in fm.items() if k in ALLOWED_KEYS[coll]}

    # Defaults / coercions.
    if coll == "entries":
        fm["receivedAt"] = _coerce_iso(fm.get("receivedAt"))
        fm.setdefault("source", {})
        # The model sometimes hallucinates source.from; the Astro schema requires
        # a valid email. Drop it if it doesn't look like one — source.from is
        # optional in the schema.
        src = fm["source"]
        if isinstance(src, dict):
            f = src.get("from")
            if f is not None and not (isinstance(f, str) and "@" in f and "." in f.split("@")[-1]):
                src.pop("from", None)
        fm.setdefault("tags", [])
        threads_refs = fm.get("threads") or []
        if not isinstance(threads_refs, list) or not threads_refs:
            raise InvalidOperation("entries must reference >=1 thread (fold in, do not silo)")
        # Normalise thread refs into Astro's reference shape: {collection, slug} or just slug string.
        norm: list[Any] = []
        for r in threads_refs:
            if isinstance(r, str):
                _validate_slug(r)
                norm.append(r)
            elif isinstance(r, dict) and "slug" in r:
                _validate_slug(r["slug"])
                norm.append(r["slug"])
            else:
                raise InvalidOperation(f"invalid thread reference: {r!r}")
        fm["threads"] = norm
    else:
        fm["createdAt"] = _coerce_iso(fm.get("createdAt"))
        fm["updatedAt"] = _coerce_iso(fm.get("updatedAt"))
        fm.setdefault("status", "active")
        fm.setdefault("tags", [])
        fm.setdefault("relatedEntries", [])
        fm.setdefault("relatedThreads", [])

    missing = REQUIRED_KEYS[coll] - set(fm)
    if missing:
        raise InvalidOperation(f"missing required keys for {coll}: {missing}")

    return {"op": op["op"], "collection": coll, "slug": slug,
            "frontmatter": fm, "body_markdown": body}


def _target_path(site_dir: Path, op: dict[str, Any]) -> Path:
    target = site_dir / "src" / "content" / op["collection"] / f"{op['slug']}.md"
    target_resolved = target.resolve()
    root_resolved = (site_dir / "src" / "content").resolve()
    if root_resolved not in target_resolved.parents:
        raise InvalidOperation(f"path escapes content root: {target}")
    return target


def apply(site_dir: Path, plan: dict[str, Any], *, dry_run: bool = False) -> list[Path]:
    """Validate every op first; if any fails, no writes happen."""
    raw_ops = plan.get("operations") or []
    ops = [_validate_op(o) for o in raw_ops]

    written: list[Path] = []
    pending: list[tuple[Path, str]] = []
    for op in ops:
        path = _target_path(site_dir, op)
        if op["op"] == "create" and path.exists():
            log.info("op=create on existing %s; treating as edit (overwrite)", path)
        post = frontmatter.Post(op["body_markdown"], **op["frontmatter"])
        text = frontmatter.dumps(post, Dumper=yaml.SafeDumper) + "\n"
        pending.append((path, text))

    for path, text in pending:
        if dry_run:
            log.info("[dry-run] would write %s (%d bytes)", path, len(text))
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        written.append(path)
        log.info("wrote %s", path)
    return written
