"""Deploy workflow engine to remote server via SSH."""
from __future__ import annotations

import os
import stat
from pathlib import Path

import paramiko

from .logging_setup import get

log = get("deploy_engine")

ENGINE_SERVICE_TEMPLATE = """[Unit]
Description=Thoughts-to-Platform Workflow Engine
After=network.target

[Service]
Type=simple
User={ssh_user}
WorkingDirectory={install_dir}/workflow-engine
Environment="PATH={venv_path}/bin"
ExecStart={venv_path}/bin/python -m apps.workflow_engine.listener
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""


def deploy_workflow_engine(config: dict, install_dir: str = "/home/{user}") -> dict:
    """Deploy workflow engine to target server via SSH.

    Args:
        config: Dict with host, port, user, key_path, key_passphrase, password
        install_dir: Remote installation directory (default: /home/{user}/workflow-engine)

    Returns:
        Dict with ok, error, service_status keys
    """
    result = {"ok": False, "error": None, "service_status": None}
    host = config.get("host", "").strip()
    port = config.get("port", 22)
    user = config.get("user", "").strip()
    key_path = config.get("key_path", "")
    key_passphrase = config.get("key_passphrase", "")
    password = config.get("password", "")

    if not host or not user:
        result["error"] = "Workflow engine deploy: host and user are required"
        return result

    install_dir = install_dir.format(user=user)
    venv_path = f"{install_dir}/.venv"
    remote_engine_dir = f"{install_dir}/workflow-engine"

    log.info("Deploying workflow engine to %s@%s:%s", user, host, remote_engine_dir)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    kw = {"hostname": host, "port": port, "username": user, "timeout": 30}
    if key_path:
        kw["key_filename"] = os.path.expanduser(key_path)
        if key_passphrase:
            kw["passphrase"] = key_passphrase
    elif password:
        kw["password"] = password
    else:
        result["error"] = "Workflow engine deploy: key_path or password required"
        return result

    try:
        client.connect(**kw)
    except paramiko.AuthenticationException as e:
        result["error"] = f"Workflow engine SSH auth failed: {e}"
        return result

    try:
        sftp = client.open_sftp()

        # Create remote directory structure
        _ensure_remote_dir(sftp, remote_engine_dir)
        _ensure_remote_dir(sftp, f"{remote_engine_dir}/apps")
        _ensure_remote_dir(sftp, f"{remote_engine_dir}/apps/workflow_engine")
        _ensure_remote_dir(sftp, f"{remote_engine_dir}/runtime")
        _ensure_remote_dir(sftp, f"{remote_engine_dir}/runtime/state")
        _ensure_remote_dir(sftp, f"{remote_engine_dir}/runtime/sites")

        # Upload workflow engine code
        engine_dir = Path(__file__).resolve().parent
        _upload_dir(sftp, engine_dir, f"{remote_engine_dir}/apps/workflow_engine")

        # Upload requirements.txt
        req_file = engine_dir / "requirements.txt"
        if req_file.exists():
            sftp.put(str(req_file), f"{remote_engine_dir}/requirements.txt")

        # Upload config.yaml if it exists
        config_file = engine_dir / "config.yaml"
        if config_file.exists():
            sftp.put(str(config_file), f"{remote_engine_dir}/config.yaml")

        # Install dependencies
        _run_ssh(client, f"cd {remote_engine_dir} && python3 -m venv .venv && {venv_path}/bin/pip install -r requirements.txt")

        # Generate and install systemd service
        service_content = ENGINE_SERVICE_TEMPLATE.format(
            ssh_user=user,
            install_dir=install_dir,
            venv_path=venv_path,
        )
        service_path = f"/etc/systemd/system/mailto-website.service"
        _run_ssh(client, f"echo '{service_content}' | sudo tee {service_path}")
        _run_ssh(client, "sudo systemctl daemon-reload")
        _run_ssh(client, "sudo systemctl enable mailto-website.service")
        _run_ssh(client, "sudo systemctl restart mailto-website.service")

        # Check service status
        stdout, _, _ = _run_ssh(client, "sudo systemctl is-active mailto-website.service")
        result["service_status"] = stdout.strip()
        result["ok"] = result["service_status"] == "active"
        if not result["ok"]:
            result["error"] = f"Workflow engine service status: {result['service_status']}"

        sftp.close()
    except Exception as e:
        result["error"] = f"Workflow engine deploy failed: {e}"
        log.exception("Workflow engine deploy failed")
    finally:
        client.close()

    return result


def _ensure_remote_dir(sftp: paramiko.SFTPClient, path: str) -> None:
    """Create remote directory recursively."""
    parts = [p for p in path.split("/") if p]
    cur = "/" if path.startswith("/") else ""
    for part in parts:
        cur = f"{cur}{part}/" if cur.endswith("/") else f"{cur}/{part}/"
        cur_no_slash = cur.rstrip("/")
        try:
            sftp.stat(cur_no_slash)
        except FileNotFoundError:
            sftp.mkdir(cur_no_slash)


def _upload_dir(sftp: paramiko.SFTPClient, local_dir: Path, remote_dir: str) -> None:
    """Upload directory contents via SFTP."""
    for item in local_dir.iterdir():
        remote_path = f"{remote_dir}/{item.name}"
        if item.is_file():
            # Skip __pycache__ and .pyc files
            if "__pycache__" in str(item) or item.suffix == ".pyc":
                continue
            sftp.put(str(item), remote_path)
        elif item.is_dir():
            try:
                sftp.stat(remote_path)
            except FileNotFoundError:
                sftp.mkdir(remote_path)
            _upload_dir(sftp, item, remote_path)


def _run_ssh(client: paramiko.SSHClient, command: str) -> tuple[str, str, int]:
    """Run SSH command and return (stdout, stderr, exit_code)."""
    log.info("SSH: %s", command)
    _, stdout, stderr = client.exec_command(command, timeout=120)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    exit_code = stdout.channel.recv_exit_status()
    if exit_code != 0:
        log.warning("SSH command exited %d: %s", exit_code, err)
    return out, err, exit_code
