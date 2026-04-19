"""SiteGround SFTP deploy provider."""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path
from typing import Iterable

import paramiko

from .base import BuildResult, DeployProvider, DeployResult
from ..logging_setup import get

log = get("siteground_provider")


class BuildFailed(RuntimeError):
    pass


class DeployFailed(RuntimeError):
    pass


class SiteGroundProvider:
    """SiteGround SFTP deploy implementation."""

    name = "siteground"

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
        sg = _parse_config(config)
        remote_root = sg["base_remote_path"].rstrip("/") + "/" + sg.get("slug", "")
        log.info("Deploying %s -> %s@%s:%s", build_result.dist_dir,
                 sg["user"], sg["host"], remote_root)

        client, sftp = _open_sftp(sg)
        try:
            _ensure_remote_dir(sftp, remote_root)
            local_files = {
                p.relative_to(build_result.dist_dir).as_posix(): p
                for p in _walk_files(build_result.dist_dir)
            }
            remote_files = _list_remote_files(sftp, remote_root)
            for rel, lp in local_files.items():
                target = f"{remote_root}/{rel}"
                _ensure_remote_dir(sftp, "/".join(target.rsplit("/", 1)[:-1]))
                sftp.put(str(lp), target)
                sftp.chmod(target, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
            for rel in remote_files - set(local_files):
                try:
                    sftp.remove(f"{remote_root}/{rel}")
                except OSError:
                    pass
            log.info("Deployed %d files (%d removed).",
                     len(local_files), len(remote_files - set(local_files)))
        finally:
            sftp.close()
            client.close()

        return DeployResult(
            slug=sg.get("slug", ""),
            provider=self.name,
            target=f"{sg['host']}:{remote_root}",
            url=sg.get("site_url", ""),
            ok=True,
        )

    def validate_config(self, config: dict) -> list[str]:
        errors = []
        if not config.get("host"):
            errors.append("SiteGround: host is required")
        if not config.get("user"):
            errors.append("SiteGround: user is required")
        if not config.get("key_path") and not config.get("password"):
            errors.append("SiteGround: key_path or password is required")
        return errors


def _parse_config(config: dict) -> dict:
    """Extract and validate SiteGround config from the provider section."""
    return {
        "host": config.get("host", ""),
        "port": config.get("port", 22),
        "user": config.get("user", ""),
        "key_path": config.get("key_path", ""),
        "key_passphrase": config.get("key_passphrase", ""),
        "password": config.get("password", ""),
        "base_remote_path": config.get("base_remote_path", "/home/USER/public_html"),
        "slug": config.get("slug", ""),
        "site_url": config.get("site_url", ""),
    }


def _open_sftp(sg: dict) -> tuple[paramiko.SSHClient, paramiko.SFTPClient]:
    if not sg["host"] or not sg["user"]:
        raise DeployFailed("SiteGround host/user not configured")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    kw = {
        "hostname": sg["host"],
        "port": sg["port"],
        "username": sg["user"],
        "timeout": 30,
    }
    if sg["key_path"]:
        kw["key_filename"] = os.path.expanduser(sg["key_path"])
        if sg["key_passphrase"]:
            kw["passphrase"] = sg["key_passphrase"]
    elif sg["password"]:
        kw["password"] = sg["password"]
    else:
        raise DeployFailed("SiteGround requires key_path or password")
    try:
        client.connect(**kw)
    except paramiko.PasswordRequiredException as e:
        raise DeployFailed(
            "SSH private key is passphrase-protected but no passphrase was provided."
        ) from e
    except paramiko.AuthenticationException as e:
        hint = ""
        if sg["key_path"] and not sg["key_passphrase"]:
            hint = " (if your key has a passphrase, add it in the wizard)"
        raise DeployFailed(f"SSH authentication failed{hint}: {e}") from e
    return client, client.open_sftp()


def _ensure_remote_dir(sftp: paramiko.SFTPClient, path: str) -> None:
    parts = [p for p in path.split("/") if p]
    cur = "/" if path.startswith("/") else ""
    for part in parts:
        cur = f"{cur}{part}/" if cur.endswith("/") else f"{cur}/{part}/"
        cur_no_slash = cur.rstrip("/")
        try:
            sftp.stat(cur_no_slash)
        except FileNotFoundError:
            try:
                sftp.mkdir(cur_no_slash)
            except (IOError, OSError) as e:
                raise DeployFailed(
                    f"Cannot create remote directory {cur_no_slash!r}. "
                    f"Check the remote base path in the wizard."
                ) from e


def _walk_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*"):
        if p.is_file():
            yield p


def _list_remote_files(sftp: paramiko.SFTPClient, root: str) -> set[str]:
    out: set[str] = set()
    def _walk(d: str) -> None:
        try:
            entries = sftp.listdir_attr(d)
        except FileNotFoundError:
            return
        for e in entries:
            full = f"{d}/{e.filename}"
            if stat.S_ISDIR(e.st_mode or 0):
                _walk(full)
            else:
                out.add(full[len(root) + 1:])
    _walk(root)
    return out


def _run(cmd: list[str], *, cwd: Path, env: dict | None = None) -> None:
    proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        log.error("Command failed: %s\nstdout:\n%s\nstderr:\n%s",
                  " ".join(cmd), proc.stdout, proc.stderr)
        raise BuildFailed(f"{cmd[0]} exited {proc.returncode}")
