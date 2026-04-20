"""Simulated deployment that mirrors the real pipeline.

The real pipeline, given a plan from the LLM, does this (see
`apps/workflow_engine/orchestrator.py`):

  1. site_bootstrap.ensure_site() — copy packages/site-template -> runtime/sites/<slug>/
  2. apply_changes.apply()        — validate + write entries/threads .md files
  3. build_and_deploy.build()     — `npm run build` producing site_dir/dist/
  4. build_and_deploy.deploy()    — SFTP dist/ to hosting (SiteGround/Vercel/…)

This module reproduces steps 1-3 against an ephemeral per-model site directory
and then "deploys" step 4 by serving the produced `dist/` folder directly via
Flask at a path unique to that run. Functionally identical to what the hosting
provider would serve.
"""
from __future__ import annotations
import os
import re
import shutil
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

# Re-use the real validation + write logic so what we preview is exactly what
# would be written to a real site if the pipeline accepted this plan.
from apps.workflow_engine import apply_changes


REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = REPO_ROOT / "packages" / "site-template"
SITES_ROOT = REPO_ROOT / "runtime" / "sites" / "prompt-lab"
SHARED_NODE_MODULES = REPO_ROOT / "runtime" / "sites" / "prompt-lab" / "_shared_node_modules"


@dataclass
class DeployState:
    preview_id: str
    model_label: str
    phase: str = "queued"   # queued|copying|applying|installing|building|ready|failed
    detail: str = ""
    error: str | None = None
    site_dir: str = ""
    preview_url: str = ""
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    files_written: list[str] = field(default_factory=list)
    build_log_tail: str = ""


# In-memory registry of deploys for the lifetime of the Flask process.
_STATES: dict[str, DeployState] = {}
_LOCK = threading.Lock()


def _slugify(label: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", label).strip("-").lower()
    return s[:40] or "model"


def list_states() -> list[dict]:
    with _LOCK:
        return [asdict(s) for s in _STATES.values()]


def get_state(preview_id: str) -> DeployState | None:
    with _LOCK:
        return _STATES.get(preview_id)


def _set(preview_id: str, **kw) -> None:
    with _LOCK:
        s = _STATES[preview_id]
        for k, v in kw.items():
            setattr(s, k, v)


def _copy_template(site_dir: Path) -> None:
    if site_dir.exists():
        shutil.rmtree(site_dir)
    shutil.copytree(
        TEMPLATE_DIR, site_dir,
        ignore=shutil.ignore_patterns("node_modules", "dist", ".astro"),
    )


def _ensure_shared_node_modules() -> Path:
    """Install node_modules once in a shared directory and symlink into each
    per-run site. Avoids ~60s of `npm install` per preview."""
    SHARED_NODE_MODULES.parent.mkdir(parents=True, exist_ok=True)
    marker = SHARED_NODE_MODULES / ".installed"
    if marker.exists():
        return SHARED_NODE_MODULES
    SHARED_NODE_MODULES.mkdir(exist_ok=True)
    # Copy package.json / lockfile into the shared install root and install there.
    for name in ("package.json", "package-lock.json"):
        src = TEMPLATE_DIR / name
        if src.exists():
            shutil.copy2(src, SHARED_NODE_MODULES / name)
    npm = shutil.which("npm")
    if not npm:
        raise RuntimeError("npm not on PATH; install Node.js 20+.")
    proc = subprocess.run(
        [npm, "install", "--no-audit", "--no-fund"],
        cwd=SHARED_NODE_MODULES, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"shared `npm install` failed:\nstdout:\n{proc.stdout[-2000:]}\n"
            f"stderr:\n{proc.stderr[-2000:]}"
        )
    marker.write_text("ok\n")
    return SHARED_NODE_MODULES


def _link_node_modules(site_dir: Path) -> None:
    shared = _ensure_shared_node_modules() / "node_modules"
    link = site_dir / "node_modules"
    if link.exists() or link.is_symlink():
        if link.is_symlink():
            link.unlink()
        else:
            shutil.rmtree(link)
    os.symlink(shared, link)


def _write_topic(site_dir: Path, topic_md: str) -> None:
    if topic_md and topic_md.strip():
        (site_dir / "topic.md").write_text(topic_md.strip() + "\n")


def _write_seed_content(site_dir: Path, threads: list[dict], entries: list[dict]) -> None:
    """Seed the site with the `existing_threads`/`existing_entries` that the
    prompt claimed were present, so edit-operations and cross-references resolve
    during the Astro build. Only minimal frontmatter — enough to satisfy the
    Zod schema in packages/site-template/src/content/config.ts."""
    import frontmatter
    import yaml
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    threads_dir = site_dir / "src" / "content" / "threads"
    entries_dir = site_dir / "src" / "content" / "entries"
    threads_dir.mkdir(parents=True, exist_ok=True)
    entries_dir.mkdir(parents=True, exist_ok=True)

    for t in threads or []:
        slug = t.get("slug")
        if not slug:
            continue
        fm = {
            "title": t.get("title") or slug,
            "summary": t.get("summary") or "(seeded by prompt lab)",
            "createdAt": t.get("createdAt") or now,
            "updatedAt": t.get("updatedAt") or now,
            "status": t.get("status") or "active",
            "tags": list(t.get("tags") or []),
            "relatedEntries": [],
            "relatedThreads": [],
        }
        body = t.get("excerpt") or t.get("body") or ""
        (threads_dir / f"{slug}.md").write_text(
            frontmatter.dumps(frontmatter.Post(body, **fm), Dumper=yaml.SafeDumper) + "\n"
        )

    for e in entries or []:
        slug = e.get("slug")
        if not slug:
            continue
        refs = list(e.get("threads") or [])
        if not refs:
            continue  # entries without a thread would fail schema validation
        fm = {
            "title": e.get("title") or slug,
            "summary": e.get("summary") or "(seeded by prompt lab)",
            "receivedAt": e.get("receivedAt") or now,
            "source": {},
            "tags": list(e.get("tags") or []),
            "threads": refs,
        }
        body = e.get("excerpt") or e.get("body") or ""
        (entries_dir / f"{slug}.md").write_text(
            frontmatter.dumps(frontmatter.Post(body, **fm), Dumper=yaml.SafeDumper) + "\n"
        )


def _build(site_dir: Path) -> str:
    npm = shutil.which("npm")
    if not npm:
        raise RuntimeError("npm not on PATH")
    env = {
        **os.environ,
        "SITE_URL": "http://localhost:5050",
        "SITE_BASE": f"/preview/{site_dir.name}/",
        "SITE_NAME": site_dir.name,
    }
    proc = subprocess.run(
        [npm, "run", "build"], cwd=site_dir, env=env,
        capture_output=True, text=True, timeout=300,
    )
    tail = (proc.stdout[-1500:] + "\n---\n" + proc.stderr[-1500:]).strip()
    if proc.returncode != 0:
        raise RuntimeError(f"astro build failed:\n{tail}")
    dist = site_dir / "dist"
    if not dist.exists():
        raise RuntimeError(f"build completed but no dist/ at {dist}")
    return tail


def deploy_plan(
    *,
    model_label: str,
    plan: dict[str, Any],
    topic_md: str,
    seed_threads: list[dict],
    seed_entries: list[dict],
) -> str:
    """Run a full simulated deploy in the current thread.

    Returns the preview_id. Caller can poll get_state() / fetch the site via
    /preview/<preview_id>/.
    """
    preview_id = f"{_slugify(model_label)}-{uuid.uuid4().hex[:8]}"
    state = DeployState(preview_id=preview_id, model_label=model_label)
    with _LOCK:
        _STATES[preview_id] = state

    site_dir = SITES_ROOT / preview_id
    _set(preview_id, site_dir=str(site_dir))

    try:
        _set(preview_id, phase="copying", detail=f"copying template -> {site_dir.name}")
        SITES_ROOT.mkdir(parents=True, exist_ok=True)
        _copy_template(site_dir)
        _write_topic(site_dir, topic_md)
        _write_seed_content(site_dir, seed_threads, seed_entries)

        _set(preview_id, phase="applying", detail="validating and writing plan operations")
        written = apply_changes.apply(site_dir, plan, dry_run=False)
        _set(preview_id, files_written=[str(p.relative_to(site_dir)) for p in written])

        _set(preview_id, phase="installing", detail="linking shared node_modules")
        _link_node_modules(site_dir)

        _set(preview_id, phase="building", detail="astro build")
        tail = _build(site_dir)
        _set(preview_id, build_log_tail=tail)

        preview_url = f"/preview/{preview_id}/"
        _set(preview_id, phase="ready", detail="deployed (simulated)",
             preview_url=preview_url, finished_at=time.time())
        return preview_id

    except Exception as e:
        _set(preview_id, phase="failed", error=str(e), finished_at=time.time())
        return preview_id


def serve_file(preview_id: str, rel_path: str) -> tuple[Path, str] | None:
    """Resolve /preview/<id>/<rel> to a safe path inside that build's dist/.
    Returns (absolute_path, mime) or None if missing or escapes root."""
    import mimetypes
    state = get_state(preview_id)
    if not state or state.phase != "ready":
        return None
    dist_root = (Path(state.site_dir) / "dist").resolve()
    if not dist_root.exists():
        return None
    # Default to index.html for directory requests.
    if not rel_path or rel_path.endswith("/"):
        rel_path = rel_path + "index.html"
    target = (dist_root / rel_path).resolve()
    try:
        target.relative_to(dist_root)
    except ValueError:
        return None
    if target.is_dir():
        target = target / "index.html"
    if not target.exists():
        # Try the "pretty URL" fallback (foo -> foo/index.html).
        alt = dist_root / rel_path / "index.html"
        if alt.exists():
            target = alt
        else:
            return None
    mime, _ = mimetypes.guess_type(str(target))
    return target, mime or "application/octet-stream"
