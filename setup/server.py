import atexit, os, signal, socket, subprocess, sys, tempfile, threading, time, webbrowser
from pathlib import Path
from flask import Flask, jsonify, render_template, request
import yaml
try:
    from dotenv import dotenv_values
except ImportError:
    def dotenv_values(path):  # type: ignore[misc]
        """Minimal fallback: parse key=value lines from a .env file."""
        result = {}
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or '=' not in line:
                        continue
                    key, _, value = line.partition('=')
                    result[key.strip()] = value.strip()
        except OSError:
            pass
        return result

import setup.builder as builder

REPO_ROOT = Path(__file__).resolve().parent.parent

app = Flask(__name__, template_folder='templates', static_folder='static')

# Port used by the running server; set in main() before app.run().
_port = None
_wizard_state = {}
# True after _try_prefill() has been called once.
_prefilled = False
# Workflow subprocess launched from /start-workflow; survives wizard exit.
_workflow_proc: "subprocess.Popen | None" = None
_workflow_log: "Path | None" = None


def _try_prefill() -> None:
    """Read existing .env and workflow/config.yaml once at launch and hydrate _wizard_state."""
    global _prefilled
    if _prefilled:
        return
    _prefilled = True

    env_path = REPO_ROOT / '.env'
    config_path = REPO_ROOT / 'workflow' / 'config.yaml'

    env_values: dict = {}
    if env_path.exists():
        env_values = dict(dotenv_values(str(env_path)))

    config_values: dict = {}
    if config_path.exists():
        try:
            with open(config_path) as f:
                loaded = yaml.safe_load(f)
            if isinstance(loaded, dict):
                config_values = loaded
        except Exception:
            pass

    if env_values or config_values:
        hydrated = builder.hydrate_wizard_state(env_values, config_values)
        _wizard_state.update(hydrated)


def find_free_port(preferred: int = 7331) -> int:
    """Return preferred port if free, otherwise return an OS-assigned port.

    Never returns 5000 or 8080.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(('127.0.0.1', preferred))
            return sock.getsockname()[1]
        except OSError:
            sock.bind(('', 0))
            return sock.getsockname()[1]


def wait_for_port(port: int, timeout: float = 5.0) -> None:
    """Block until a TCP listener appears on 127.0.0.1:port or timeout expires.

    Raises RuntimeError if the port is not reachable within *timeout* seconds.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.1):
                return
        except OSError:
            time.sleep(0.05)
    raise RuntimeError(f"Port {port} not reachable after {timeout}s")


def check_write_permission(project_root: Path) -> bool:
    """Return True if *project_root* is writable by the current process."""
    return os.access(project_root, os.W_OK)


def open_browser_after_ready(url: str, port: int) -> None:
    """Start a daemon thread that opens *url* once the server is accepting connections."""

    def _open():
        try:
            wait_for_port(port)
        except RuntimeError:
            return
        if sys.platform == 'darwin':
            subprocess.Popen(['open', url])
        else:
            webbrowser.open(url)

    t = threading.Thread(target=_open, daemon=True)
    t.start()


def _shutdown_server() -> None:
    # Brief delay lets the /exit response flush before SIGINT fires.
    # Do NOT call server.shutdown() from inside a request handler — that deadlocks Werkzeug.
    time.sleep(0.3)
    os.kill(os.getpid(), signal.SIGINT)


def _cleanup() -> None:
    print("\nSetup wizard exited cleanly.", flush=True)


@app.route('/')
def index():
    return render_template('index.html', port=_port, active_step='gmail')


@app.route('/step/lmstudio')
def step_lmstudio():
    return render_template('lmstudio.html', port=_port, active_step='lmstudio')


@app.route('/step/hosting')
def step_hosting():
    return render_template('hosting.html', port=_port, active_step='hosting')


@app.route('/step/inboxes')
def step_inboxes():
    return render_template('inboxes.html', port=_port, active_step='inboxes')


@app.route('/step/preview')
def step_preview():
    _try_prefill()
    # Guard: require gmail_address and at least one inbox to render a meaningful preview.
    if not _wizard_state.get('gmail_address'):
        return render_template('index.html', port=_port, active_step='gmail')

    env_str, yaml_str = builder.build_final_outputs(_wizard_state)
    env_preview, yaml_preview = builder.mask_for_preview(env_str, yaml_str)

    env_path = REPO_ROOT / '.env'
    config_path = REPO_ROOT / 'workflow' / 'config.yaml'
    has_existing_config = env_path.exists() or config_path.exists()

    return render_template(
        'preview.html',
        port=_port,
        active_step='preview',
        env_preview=env_preview,
        yaml_preview=yaml_preview,
        has_existing_config=has_existing_config,
    )


@app.route('/step/done')
def step_done():
    return render_template('done.html', port=_port, active_step='preview')


@app.route('/start-workflow', methods=['POST'])
def start_workflow():
    """Launch scripts/run-workflow.sh as a detached subprocess, piping output to a log file.
    The subprocess survives wizard exit via start_new_session=True so the user can close
    the tab once the workflow is running.
    """
    global _workflow_proc, _workflow_log

    if _workflow_proc and _workflow_proc.poll() is None:
        return jsonify({"ok": True, "status": "running", "pid": _workflow_proc.pid})

    script = REPO_ROOT / 'scripts' / 'run-workflow.sh'
    if not script.exists():
        return jsonify({"ok": False, "error": "scripts/run-workflow.sh not found"}), 500

    logs_dir = REPO_ROOT / 'logs'
    try:
        logs_dir.mkdir(exist_ok=True)
    except OSError as e:
        return jsonify({"ok": False, "error": f"cannot create logs directory: {e}"}), 500

    _workflow_log = logs_dir / 'workflow.log'
    try:
        log_fh = open(_workflow_log, 'w', buffering=1)
    except OSError as e:
        return jsonify({"ok": False, "error": f"cannot open log file: {e}"}), 500

    try:
        _workflow_proc = subprocess.Popen(
            [str(script)],
            cwd=str(REPO_ROOT),
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as e:
        log_fh.close()
        return jsonify({"ok": False, "error": f"failed to spawn workflow: {e}"}), 500

    return jsonify({"ok": True, "status": "running", "pid": _workflow_proc.pid})


@app.route('/workflow-status')
def workflow_status():
    """Return current workflow subprocess status + last ~50 log lines for live tail."""
    global _workflow_proc, _workflow_log

    if not _workflow_proc:
        return jsonify({"status": "not_started", "log": []})

    rc = _workflow_proc.poll()
    if rc is None:
        status = "running"
    elif rc == 0:
        status = "exited"
    else:
        status = "failed"

    log_lines: list = []
    if _workflow_log and _workflow_log.exists():
        try:
            with open(_workflow_log) as f:
                log_lines = f.readlines()[-50:]
        except OSError:
            pass

    return jsonify({
        "status": status,
        "exit_code": rc,
        "pid": _workflow_proc.pid,
        "log": [line.rstrip('\n') for line in log_lines],
    })


@app.route('/validate-form', methods=['POST'])
def validate_form():
    data = request.get_json(force=True) or {}
    step = data.get('step', 'gmail')

    if step == 'gmail':
        errors = builder.validate(data)
        next_step = '/step/lmstudio'
        if not errors:
            _wizard_state.update(data)
            env_str, yaml_str = builder.build(_wizard_state)
            return jsonify({
                "ok": True,
                "next_step": next_step,
                "env_preview": env_str,
                "yaml_preview": yaml_str,
            })

    elif step == 'lmstudio':
        next_step = '/step/hosting'
        _wizard_state.update(data)
        return jsonify({"ok": True, "next_step": next_step})

    elif step == 'hosting':
        errors = builder.validate_hosting(data)
        next_step = '/step/inboxes'
        if not errors:
            provider = data.get('hosting_provider', '')
            if provider == 'netlify':
                try:
                    data['site_base_url'] = builder.fetch_netlify_site_url(
                        data.get('netlify_api_token', '').strip(),
                        data.get('netlify_site_id', '').strip(),
                    )
                except builder.ProviderLookupError as e:
                    return jsonify({"ok": False, "errors": [{
                        "field": "netlify_site_id",
                        "message": f"Could not fetch site URL from Netlify: {e}",
                    }]}), 400
            elif provider == 'vercel':
                try:
                    data['site_base_url'] = builder.fetch_vercel_project_url(
                        data.get('vercel_api_token', '').strip(),
                        data.get('vercel_project_id', '').strip(),
                    )
                except builder.ProviderLookupError as e:
                    return jsonify({"ok": False, "errors": [{
                        "field": "vercel_project_id",
                        "message": f"Could not fetch project URL from Vercel: {e}",
                    }]}), 400

            hosting_data = builder.build_hosting(data)
            _wizard_state.update(hosting_data)
            return jsonify({"ok": True, "next_step": next_step})

    elif step == 'inboxes':
        errors = builder.validate_inboxes(data)
        next_step = '/step/preview'
        if not errors:
            gmail_address = _wizard_state.get('gmail_address', '').strip()
            site_base_url = _wizard_state.get('site_base_url', '').strip()
            if not gmail_address:
                return jsonify({"ok": False, "errors": [{
                    "field": "inboxes",
                    "message": "Gmail address missing — return to the Gmail step.",
                }]}), 400
            if not site_base_url:
                return jsonify({"ok": False, "errors": [{
                    "field": "inboxes",
                    "message": "Site base URL missing — return to the Hosting step.",
                }]}), 400
            inboxes_data = builder.build_inboxes(data, gmail_address, site_base_url)
            _wizard_state.update(inboxes_data)
            return jsonify({"ok": True, "next_step": next_step})

    else:
        return jsonify({"ok": False, "errors": [{"field": "step", "message": "Unknown step"}]}), 400

    # Reach here only on validation errors
    return jsonify({"ok": False, "errors": errors}), 400


@app.route('/write-config', methods=['POST'])
def write_config():
    data = request.get_json(force=True) or {}

    if not data.get('confirmed'):
        return jsonify({"ok": False, "error": "confirmation required"}), 400

    env_path = REPO_ROOT / '.env'
    config_path = REPO_ROOT / 'workflow' / 'config.yaml'
    has_existing = env_path.exists() or config_path.exists()

    if has_existing and not data.get('overwrite_confirmed'):
        return jsonify({
            "ok": False,
            "overwrite_required": True,
            "error": "existing config files detected — set overwrite_confirmed to proceed",
        }), 409

    env_str, yaml_str = builder.build_final_outputs(_wizard_state)
    _write_config_pair(env_path, env_str, config_path, yaml_str)
    return jsonify({"ok": True, "next_step": "/step/done"})


def _write_config_pair(env_path: Path, env_str: str, config_path: Path, yaml_str: str) -> None:
    """Write env_path and config_path using temp-file + replace semantics.

    Both files are fully written and fsynced before either target is replaced.
    If the second os.replace fails after the first succeeds, the first target is
    restored from backup so the pair does not end up in split state.
    """
    import shutil

    config_path.parent.mkdir(parents=True, exist_ok=True)

    env_tmp: str | None = None
    cfg_tmp: str | None = None
    env_backup: str | None = None
    cfg_backup: str | None = None

    try:
        # Write both temp files fully before touching any target.
        env_fd, env_tmp = tempfile.mkstemp(dir=env_path.parent, prefix='.env.tmp.')
        with os.fdopen(env_fd, 'w', encoding='utf-8') as f:
            f.write(env_str)
            f.flush()
            os.fsync(f.fileno())

        cfg_fd, cfg_tmp = tempfile.mkstemp(dir=config_path.parent, prefix='.config.tmp.')
        with os.fdopen(cfg_fd, 'w', encoding='utf-8') as f:
            f.write(yaml_str)
            f.flush()
            os.fsync(f.fileno())

        # Capture backups of existing targets so we can rollback.
        if env_path.exists():
            bfd, env_backup = tempfile.mkstemp(dir=env_path.parent, prefix='.env.bak.')
            os.close(bfd)
            shutil.copy2(str(env_path), env_backup)

        if config_path.exists():
            bfd, cfg_backup = tempfile.mkstemp(dir=config_path.parent, prefix='.config.bak.')
            os.close(bfd)
            shutil.copy2(str(config_path), cfg_backup)

        # Replace first target.
        os.replace(env_tmp, str(env_path))
        env_tmp = None  # consumed — do not unlink in finally

        # Replace second target; on failure, restore first from backup.
        try:
            os.replace(cfg_tmp, str(config_path))
            cfg_tmp = None
        except OSError:
            if env_backup:
                try:
                    os.replace(env_backup, str(env_path))
                    env_backup = None
                except OSError:
                    pass
            raise

    finally:
        for tmp in (env_tmp, cfg_tmp):
            if tmp:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
        for bak in (env_backup, cfg_backup):
            if bak:
                try:
                    os.unlink(bak)
                except OSError:
                    pass


@app.route('/exit', methods=['POST'])
def exit_wizard():
    threading.Thread(target=_shutdown_server, daemon=True).start()
    return jsonify({"ok": True})


def main():
    global _port

    if not check_write_permission(REPO_ROOT):
        print(
            f"ERROR: Project directory {REPO_ROOT} is not writable. "
            "Cannot start setup wizard.",
            file=sys.stderr,
        )
        sys.exit(1)

    _try_prefill()
    _port = find_free_port()
    url = f"http://127.0.0.1:{_port}/"
    atexit.register(_cleanup)
    signal.signal(signal.SIGTERM, lambda s, f: _shutdown_server())
    open_browser_after_ready(url, _port)
    # threaded=False: single-user local wizard; avoids block_on_close keep-alive delay on SIGINT
    app.run(host='127.0.0.1', port=_port, debug=False, use_reloader=False, threaded=False)


if __name__ == '__main__':
    main()
