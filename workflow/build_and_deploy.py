"""Build the per-inbox Astro site and SFTP-deploy it to SiteGround."""
from __future__ import annotations
import os
import shutil
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import paramiko

from .config import Config, InboxConfig, SiteGroundConfig
from .logging_setup import get

log = get("deploy")


class BuildFailed(RuntimeError):
    pass


class DeployFailed(RuntimeError):
    pass


@dataclass
class BuildResult:
    site_dir: Path
    dist_dir: Path


def build(site_dir: Path, *, inbox: InboxConfig) -> BuildResult:
    npm = shutil.which("npm")
    if not npm:
        raise BuildFailed("npm not on PATH")
    node_modules = site_dir / "node_modules"
    if not node_modules.exists():
        log.info("Installing site deps in %s ...", site_dir)
        _run([npm, "install"], cwd=site_dir)
    env = {
        **os.environ,
        "SITE_URL": inbox.site_url or "https://example.com",
        "SITE_BASE": inbox.site_base or "/",
        "SITE_NAME": inbox.site_name or inbox.slug,
    }
    log.info("Building %s ...", site_dir)
    _run([npm, "run", "build"], cwd=site_dir, env=env)
    dist = site_dir / "dist"
    if not dist.exists():
        raise BuildFailed(f"build completed but no dist at {dist}")
    return BuildResult(site_dir=site_dir, dist_dir=dist)


def _run(cmd: list[str], *, cwd: Path, env: dict | None = None) -> None:
    proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        log.error("Command failed: %s\nstdout:\n%s\nstderr:\n%s",
                  " ".join(cmd), proc.stdout, proc.stderr)
        raise BuildFailed(f"{cmd[0]} exited {proc.returncode}")


def _open_sftp(sg: SiteGroundConfig) -> tuple[paramiko.SSHClient, paramiko.SFTPClient]:
    if not sg.host or not sg.user:
        raise DeployFailed("siteground host/user not configured")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    kw: dict = {"hostname": sg.host, "port": sg.port, "username": sg.user, "timeout": 30}
    if sg.key_path:
        kw["key_filename"] = os.path.expanduser(sg.key_path)
    elif sg.password:
        kw["password"] = sg.password
    else:
        raise DeployFailed("siteground requires key_path or password")
    client.connect(**kw)
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
            sftp.mkdir(cur_no_slash)


def _walk_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*"):
        if p.is_file():
            yield p


def deploy(result: BuildResult, *, cfg: Config, inbox: InboxConfig) -> None:
    remote_root = cfg.remote_path_for(inbox)
    log.info("Deploying %s -> %s@%s:%s", result.dist_dir, cfg.siteground.user,
             cfg.siteground.host, remote_root)
    client, sftp = _open_sftp(cfg.siteground)
    try:
        _ensure_remote_dir(sftp, remote_root)
        # Mirror: upload everything; remove files no longer present locally.
        local_files = {p.relative_to(result.dist_dir).as_posix(): p
                       for p in _walk_files(result.dist_dir)}
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
