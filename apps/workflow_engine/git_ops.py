"""Commit + push changes for the workflow's edits."""
from __future__ import annotations
import subprocess
from pathlib import Path

from .logging_setup import get

log = get("git")


def _run(args: list[str], *, cwd: Path) -> str:
    proc = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if proc.returncode != 0:
        log.error("git failed: %s\n%s", " ".join(args), proc.stderr)
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    return proc.stdout


def commit_and_push(
    repo: Path,
    *,
    message: str,
    branch: str,
    paths: list[str] | None = None,
    push: bool = True,
) -> str | None:
    """Returns the new commit SHA, or None if there was nothing to commit."""
    add_args = ["git", "add", "--"] + (paths or ["."])
    _run(add_args, cwd=repo)
    status = _run(["git", "status", "--porcelain"], cwd=repo)
    if not status.strip():
        log.info("nothing to commit")
        return None
    _run(["git", "commit", "-m", message], cwd=repo)
    sha = _run(["git", "rev-parse", "HEAD"], cwd=repo).strip()
    if push:
        # Best-effort with retries handled by caller; here a single push.
        _run(["git", "push", "-u", "origin", branch], cwd=repo)
    return sha
