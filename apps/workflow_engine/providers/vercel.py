"""Vercel deploy provider — deploys built static sites via Vercel REST API."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .base import BuildResult, DeployProvider, DeployResult
from ..logging_setup import get

log = get("vercel_provider")

VERCEL_API = "https://api.vercel.com"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB per file (Vercel limit)


class BuildFailed(RuntimeError):
    pass


class DeployFailed(RuntimeError):
    pass


class VercelProvider:
    """Vercel deploy implementation."""

    name = "vercel"

    def build(self, site_dir: Path, site_url: str, site_name: str) -> BuildResult:
        npm = shutil.which("npm")
        if not npm:
            raise BuildFailed("npm not on PATH")
        node_modules = site_dir / "node_modules"
        if not node_modules.exists():
            log.info("Installing site deps in %s ...", site_dir)
            _run([npm, "install"], cwd=site_dir)
        env = {
            **os.environ,
            "SITE_URL": site_url or "https://example.com",
            "SITE_BASE": "/",
            "SITE_NAME": site_name,
        }
        log.info("Building %s ...", site_dir)
        _run([npm, "run", "build"], cwd=site_dir, env=env)
        dist = site_dir / "dist"
        if not dist.exists():
            raise BuildFailed(f"build completed but no dist at {dist}")
        return BuildResult(site_dir=site_dir, dist_dir=dist)

    def deploy(self, build_result: BuildResult, config: dict) -> DeployResult:
        token = config.get("api_token", "").strip()
        project_id = config.get("project_id", "").strip()
        team_id = config.get("team_id", "").strip()
        slug = config.get("slug", "")
        site_url = config.get("site_url", "")

        if not token:
            raise DeployFailed("Vercel: api_token is required")
        if not project_id:
            raise DeployFailed("Vercel: project_id is required")

        # Collect files from dist/
        files = _collect_files(build_result.dist_dir)
        if not files:
            raise DeployFailed("Vercel: no files found in dist/ to deploy")

        log.info("Deploying %d files to Vercel project %s ...", len(files), project_id)

        # Create deployment
        deployment_url = self._create_deployment(token, project_id, team_id, files, slug)

        log.info("Vercel deployment URL: %s", deployment_url)
        return DeployResult(
            slug=slug,
            provider=self.name,
            target=f"vercel.com/{project_id}",
            url=deployment_url,
            ok=True,
        )

    def validate_config(self, config: dict) -> list[str]:
        errors = []
        if not config.get("api_token"):
            errors.append("Vercel: api_token is required")
        if not config.get("project_id"):
            errors.append("Vercel: project_id is required")
        return errors

    def _create_deployment(
        self, token: str, project_id: str, team_id: str, files: list[dict], slug: str
    ) -> str:
        """Create a Vercel deployment and return the deployment URL."""
        body = {
            "name": project_id,
            "project": project_id,
            "files": files,
        }
        if team_id:
            body["teamId"] = team_id

        url = f"{VERCEL_API}/v13/deployments"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        data = json.dumps(body).encode("utf-8")
        req = Request(url, data=data, headers=headers, method="POST")

        try:
            with urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            raise DeployFailed(
                f"Vercel API error {e.code}: {error_body}"
            ) from e
        except URLError as e:
            raise DeployFailed(f"Vercel API unreachable: {e.reason}") from e

        # Vercel returns the deployment URL in the response
        return result.get("url", f"https://{project_id}.vercel.app")


def _collect_files(dist_dir: Path) -> list[dict]:
    """Walk dist/ and collect files as {file: "relative/path", data: "content"}."""
    files = []
    for p in dist_dir.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(dist_dir).as_posix()
        size = p.stat().st_size
        if size > MAX_FILE_SIZE:
            log.warning("Skipping file %s (%d bytes exceeds %d limit)", rel, size, MAX_FILE_SIZE)
            continue
        try:
            content = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Binary file — skip (Vercel API expects text content)
            log.warning("Skipping binary file: %s", rel)
            continue
        files.append({"file": rel, "data": content})
    return files


def _run(cmd: list[str], *, cwd: Path, env: dict | None = None) -> None:
    proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        log.error("Command failed: %s\nstdout:\n%s\nstderr:\n%s",
                  " ".join(cmd), proc.stdout, proc.stderr)
        raise BuildFailed(f"{cmd[0]} exited {proc.returncode}")
