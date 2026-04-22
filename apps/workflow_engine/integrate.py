"""INTEGRATE stage: atomically write module HTML, upsert SPA manifest, commit both.

Two-commit approach (resolves INT-02/INT-03 circularity):
  1. Commit module HTML alone → capture SHA_A
  2. Upsert manifest with SHA_A as version → commit manifest → SHA_B
  Returns SHA_A (the commit containing the module). Manifest version refers to
  the module's commit, which is what INT-03 requires ("version field = commit SHA
  of the module-bearing commit").
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile
from pathlib import Path

from .git_ops import commit_and_push
from .logging_setup import get
from .schemas.envelope import MechanicSpec

log = get("integrate")


class IntegrateFailed(RuntimeError):
    pass


def _ensure_git_repo(site_dir: Path) -> None:
    """Idempotent: init git repo and set local user config if .git absent."""
    if (site_dir / ".git").exists():
        return
    subprocess.run(["git", "init"], cwd=site_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "workflow@localhost"],
        cwd=site_dir, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Workflow Engine"],
        cwd=site_dir, check=True, capture_output=True,
    )


def _atomic_write(path: Path, content: bytes) -> None:
    """Write content to path via tempfile + os.replace (no partial writes)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _upsert_manifest(manifest_path: Path, spec: MechanicSpec, sha: str) -> None:
    """Load manifest, upsert entry by module_id, atomic write back."""
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
    else:
        manifest = {"schema_version": "1", "modules": []}
    modules = manifest.setdefault("modules", [])
    entry = {
        "module_id": spec.module_id,
        "kind": spec.kind.value,
        "title": spec.title,
        "version": sha,
    }
    idx = next(
        (i for i, m in enumerate(modules) if m.get("module_id") == spec.module_id),
        None,
    )
    if idx is not None:
        modules[idx] = entry
    else:
        modules.append(entry)
    _atomic_write(manifest_path, json.dumps(manifest, indent=2).encode())


def startup_assert_gitignore(site_dir: Path) -> None:
    """Raise RuntimeError if .gitignore excludes public/spa/; no-op if .gitignore absent."""
    gitignore = site_dir / ".gitignore"
    if not gitignore.exists():
        return
    for raw in gitignore.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        if "public/spa" in line or line in ("public", "public/"):
            raise RuntimeError(
                f"site_dir .gitignore excludes public/spa/ (pattern: {line!r}). "
                "Remove the pattern before running INTEGRATE."
            )


def integrate(
    spec: MechanicSpec,
    html_b64: str,
    site_dir: Path,
    *,
    push: bool = False,
) -> str:
    """Write module HTML atomically, upsert manifest, commit. Returns 7-char short SHA."""
    _ensure_git_repo(site_dir)

    html_bytes = base64.b64decode(html_b64)
    module_path = site_dir / "public" / "spa" / spec.module_id / "index.html"
    _atomic_write(module_path, html_bytes)

    sha_module = commit_and_push(
        site_dir,
        message=f"[{spec.module_id}] integrate module",
        branch="main",
        paths=[f"public/spa/{spec.module_id}/"],
        push=push,
    )
    if sha_module is None:
        raise IntegrateFailed(
            f"nothing committed for module {spec.module_id!r} — file may be unchanged"
        )

    manifest_path = site_dir / "public" / "spa" / "spa_manifest.json"
    _upsert_manifest(manifest_path, spec, sha_module[:7])
    commit_and_push(
        site_dir,
        message=f"[{spec.module_id}] update manifest -> {sha_module[:7]}",
        branch="main",
        paths=["public/spa/spa_manifest.json"],
        push=push,
    )
    # sha_manifest may be None if manifest entry was already up-to-date — acceptable;
    # the module commit is what matters for INT-03.

    return sha_module[:7]
