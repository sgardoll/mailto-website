import atexit, os, signal, socket, subprocess, sys, tempfile, threading, time, webbrowser
from pathlib import Path
from flask import Flask, jsonify, redirect, render_template, request, url_for
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

import apps.setup_wizard.builder as builder

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

app = Flask(__name__, template_folder='templates', static_folder='static')

# Port used by the running server; set in main() before app.run().
_port = None
_wizard_state = {}
# True after _try_prefill() has been called once.
_prefilled = False

# Service launch state for POST /api/launch + GET /api/services polling.
_service_procs: list[subprocess.Popen] = []
_launch_lock = threading.Lock()
_launch_state = "idle"  # idle | launching | running | error
_launch_error: str | None = None

# Deploy state for POST /deploy + GET /deploy-status polling.
_deploy_lock = threading.Lock()
_deploy_state: dict = {
    "status": "idle",       # idle | running | complete | failed
    "started_at": None,
    "inboxes": [],          # [{slug, phase, detail, url, ok, error}, ...]
    "error": None,
}


def _try_prefill() -> None:
    """Read existing .env and apps/workflow_engine/config.yaml once at launch and hydrate _wizard_state."""
    global _prefilled
    if _prefilled:
        return
    _prefilled = True

    env_path = REPO_ROOT / '.env'
    config_path = REPO_ROOT / 'apps' / 'workflow_engine' / 'config.yaml'

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


def _service_up(port: int) -> bool:
    """Return True when a local TCP service is accepting connections."""
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=0.3):
            return True
    except OSError:
        return False


def _config_files_exist() -> bool:
    env_path = REPO_ROOT / '.env'
    config_path = REPO_ROOT / 'apps' / 'workflow_engine' / 'config.yaml'
    return env_path.exists() and config_path.exists()


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
    for proc in list(_service_procs):
        if proc.poll() is None:
            try:
                proc.terminate()
            except OSError:
                pass
    print("\nSetup wizard exited cleanly.", flush=True)


def _launch_worker() -> None:
    global _launch_state, _launch_error

    try:
        env = os.environ.copy()
        env_path = REPO_ROOT / '.env'
        if env_path.exists():
            env.update({k: v for k, v in dotenv_values(str(env_path)).items() if v is not None})

        python_path = REPO_ROOT / '.venv' / 'bin' / 'python'
        listener_proc = subprocess.Popen(
            [str(python_path), '-m', 'apps.workflow_engine.listener'],
            cwd=str(REPO_ROOT),
            env=env,
        )
        _service_procs.append(listener_proc)

        site_dir = REPO_ROOT / 'packages' / 'site-template'
        if not (site_dir / 'node_modules').exists():
            subprocess.run(['npm', 'install'], cwd=str(site_dir), env=env, check=True)

        astro_proc = subprocess.Popen(
            ['npm', 'run', 'dev'],
            cwd=str(site_dir),
            env=env,
        )
        _service_procs.append(astro_proc)

        with _launch_lock:
            _launch_state = "running"
            _launch_error = None
    except Exception as e:
        for proc in list(_service_procs):
            if proc.poll() is None:
                try:
                    proc.terminate()
                except OSError:
                    pass
        with _launch_lock:
            _launch_state = "error"
            _launch_error = f"{type(e).__name__}: {e}"


@app.route('/')
def index():
    if _config_files_exist():
        return redirect(url_for('ready'))
    return render_template('index.html', port=_port, active_step='gmail', completed_steps=[])


@app.route('/step/gmail')
def step_gmail():
    return render_template('index.html', port=_port, active_step='gmail', completed_steps=[])


@app.route('/ready')
def ready():
    return render_template('ready.html', port=_port, active_step='preview', completed_steps=['gmail', 'lmstudio', 'hosting', 'inboxes', 'preview'])


@app.route('/launch-status')
def launch_status():
    return render_template('launch_status.html', port=_port)


@app.route('/api/launch', methods=['POST'])
def api_launch():
    global _launch_state, _launch_error

    with _launch_lock:
        if _launch_state in ("idle", "error"):
            _service_procs.clear()
            _launch_state = "launching"
            _launch_error = None
            threading.Thread(target=_launch_worker, daemon=True).start()
        return jsonify({"ok": _launch_state != "error", "launch_status": _launch_state, "launch_error": _launch_error})


@app.route('/api/services')
def api_services():
    with _launch_lock:
        status = _launch_state
        error = _launch_error

    listener_url = 'http://127.0.0.1:8899/'
    astro_url = 'http://localhost:4321/'
    return jsonify({
        "launch_status": status,
        "launch_error": error,
        "services": {
            "listener": {"up": _service_up(8899), "url": listener_url},
            "astro": {"up": _service_up(4321), "url": astro_url},
        },
    })


@app.route('/step/lmstudio')
def step_lmstudio():
    _try_prefill()
    return render_template('lmstudio.html', port=_port, active_step='lmstudio',
                           completed_steps=['gmail'], wizard_state=_wizard_state)


@app.route('/step/hosting')
def step_hosting():
    return render_template(
        'hosting.html',
        port=_port,
        active_step='hosting',
        completed_steps=['gmail', 'lmstudio'],
        sg_key_passphrase_stored=bool(_wizard_state.get('sg-key_passphrase_stored')),
        sg_password_stored=bool(_wizard_state.get('sg-password_stored')),
        ssh_password_stored=bool(_wizard_state.get('ssh-password_stored')),
        vercel_api_token_stored=bool(_wizard_state.get('vercel_api_token_stored')),
    )


@app.route('/step/inboxes')
def step_inboxes():
    return render_template('inboxes.html', port=_port, active_step='inboxes', completed_steps=['gmail', 'lmstudio', 'hosting'])


@app.route('/step/preview')
def step_preview():
    _try_prefill()
    # Guard: require gmail_address and at least one inbox to render a meaningful preview.
    if not _wizard_state.get('gmail_address'):
        return render_template('index.html', port=_port, active_step='gmail', completed_steps=[])

    env_str, yaml_str = builder.build_final_outputs(_wizard_state)
    env_preview, yaml_preview = builder.mask_for_preview(env_str, yaml_str)

    env_path = REPO_ROOT / '.env'
    config_path = REPO_ROOT / 'apps' / 'workflow_engine' / 'config.yaml'
    has_existing_config = env_path.exists() or config_path.exists()

    return render_template(
        'preview.html',
        port=_port,
        active_step='preview',
        completed_steps=['gmail', 'lmstudio', 'hosting', 'inboxes'],
        env_preview=env_preview,
        yaml_preview=yaml_preview,
        has_existing_config=has_existing_config,
    )


@app.route('/step/done')
def step_done():
    site_base_url = _wizard_state.get('site_base_url', '').strip()
    hosting_provider = (_wizard_state.get('hosting_provider') or '').strip()
    inboxes = _wizard_state.get('inboxes') or []
    # Normalize to a template-friendly shape — slug + site_url + site_name
    inbox_rows = [
        {
            'slug': ib.get('slug', ''),
            'site_url': ib.get('site_url', ''),
            'site_name': ib.get('site_name') or ib.get('slug', ''),
            'address': ib.get('address', ''),
        }
        for ib in inboxes if ib.get('slug')
    ]
    return render_template(
        'done.html',
        port=_port,
        active_step='preview',
        completed_steps=['gmail', 'lmstudio', 'hosting', 'inboxes', 'preview'],
        site_base_url=site_base_url,
        hosting_provider=hosting_provider,
        inboxes=inbox_rows,
    )


def _reset_deploy_state(slugs: list[str]) -> None:
    with _deploy_lock:
        _deploy_state.update({
            "status": "running",
            "started_at": time.time(),
            "inboxes": [
                {"slug": s, "phase": "pending", "detail": "", "url": "", "ok": False, "error": None}
                for s in slugs
            ],
            "error": None,
        })


def _update_inbox_progress(slug: str, phase: str, detail: str) -> None:
    with _deploy_lock:
        for row in _deploy_state["inboxes"]:
            if row["slug"] == slug:
                row["phase"] = phase
                row["detail"] = detail
                if phase == "done":
                    row["ok"] = True
                elif phase == "failed":
                    row["error"] = detail
                break


def _deploy_worker() -> None:
    """Run the deploy loop on a background thread. Captures final state."""
    try:
        from apps.workflow_engine import config as wf_config
        from apps.workflow_engine import deploy_once
        cfg = wf_config.load(REPO_ROOT / 'apps' / 'workflow_engine' / 'config.yaml')
        results = deploy_once.deploy_all(cfg, on_progress=_update_inbox_progress)
        with _deploy_lock:
            for row, r in zip(_deploy_state["inboxes"], results):
                row["ok"] = r["ok"]
                row["url"] = r["url"]
                if not r["ok"]:
                    row["error"] = r["error"]
            failures = [r for r in results if not r["ok"]]
            _deploy_state["status"] = "failed" if failures else "complete"
    except Exception as e:
        with _deploy_lock:
            _deploy_state["status"] = "failed"
            _deploy_state["error"] = f"{type(e).__name__}: {e}"


_VCARD_SLUG_RE = __import__('re').compile(r'^[a-z0-9][a-z0-9\-]{0,80}$')


@app.route('/contact-vcard/<slug>')
def contact_vcard(slug: str):
    """Download a vCard for the inbox so the user can import it into
    Google Contacts (or any contacts app). Avoids OAuth: the user
    double-clicks the file → Contacts opens with fields prefilled.
    """
    if not _VCARD_SLUG_RE.match(slug or ''):
        return ('Invalid slug', 400)
    inbox = next((ib for ib in (_wizard_state.get('inboxes') or [])
                  if ib.get('slug') == slug), None)
    if not inbox or not inbox.get('address'):
        return ('Inbox not found', 404)
    name = inbox.get('site_name') or slug
    addr = inbox['address']
    # Minimal vCard 3.0 (most widely supported by Contacts apps + Google import)
    vcard = (
        "BEGIN:VCARD\r\n"
        "VERSION:3.0\r\n"
        f"FN:{name}\r\n"
        f"N:{name};;;;\r\n"
        f"EMAIL;TYPE=INTERNET:{addr}\r\n"
        f"NOTE:Inbox alias for {name} on mailto.website.\r\n"
        "END:VCARD\r\n"
    )
    from flask import Response
    return Response(
        vcard,
        mimetype='text/vcard',
        headers={'Content-Disposition': f'attachment; filename="{slug}.vcf"'},
    )


@app.route('/deploy', methods=['POST'])
def deploy():
    provider = (_wizard_state.get('hosting_provider') or '').strip()
    try:
        from apps.workflow_engine.providers import get_provider
        get_provider(provider)
    except (ValueError, ImportError) as e:
        return jsonify({
            "ok": False,
            "error": "not_implemented",
            "provider": provider,
            "message": str(e),
        }), 400

    with _deploy_lock:
        if _deploy_state["status"] == "running":
            return jsonify({"ok": True, "status": "running"})

    inboxes = _wizard_state.get('inboxes') or []
    slugs = [ib.get('slug') for ib in inboxes if ib.get('slug')]
    if not slugs:
        return jsonify({"ok": False, "error": "no inboxes configured"}), 400

    _reset_deploy_state(slugs)
    threading.Thread(target=_deploy_worker, daemon=True).start()
    return jsonify({"ok": True, "status": "running"})


@app.route('/deploy-status')
def deploy_status():
    with _deploy_lock:
        # Return a shallow copy so callers see a consistent snapshot
        return jsonify({
            "status": _deploy_state["status"],
            "started_at": _deploy_state["started_at"],
            "inboxes": [dict(row) for row in _deploy_state["inboxes"]],
            "error": _deploy_state["error"],
        })


@app.route('/api/models')
def api_models():
    """Return chat-capable models — loaded (from API) or downloaded (from lms ls)."""
    import json as _json
    import shutil
    import subprocess
    import urllib.error as _url_error
    import urllib.request as _url_request
    models = []

    # First try the running server's /v1/models endpoint
    try:
        req = _url_request.Request('http://localhost:1234/v1/models', method='GET')
        with _url_request.urlopen(req, timeout=3) as resp:
            data = _json.loads(resp.read().decode('utf-8'))
        for m in data.get('data', []):
            mid = m.get('id', '')
            if mid and 'embed' not in mid.lower():
                models.append(mid)
    except (_url_error.URLError, OSError, ValueError):
        pass

    # Fallback: query downloaded models via lms CLI (not just loaded ones)
    if not models and shutil.which('lms'):
        try:
            r = subprocess.run(['lms', 'ls', '--json'], capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                data = _json.loads(r.stdout or '[]')
                for m in data:
                    mid = m.get('modelKey', '')
                    mtype = (m.get('type') or '').lower()
                    if mid and mtype != 'embedding' and 'embed' not in mid.lower():
                        models.append(mid)
        except (subprocess.TimeoutExpired, OSError, ValueError):
            pass

    return jsonify({'models': [{'id': m, 'object': 'model'} for m in models]})


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
            # Persist any pasted SiteGround private key to disk BEFORE build_hosting
            # runs, so the YAML path it emits is already absolute and the key is
            # available at deploy time.
            if provider == 'siteground':
                key_text = builder.extract_siteground_key(data)
                if key_text:
                    key_path = _write_siteground_key_file(key_text)
                    data['sg-existing_key_path'] = str(key_path)
                    data['sg-ssh_private_key'] = ''  # consumed — drop from state
            if provider == 'vercel':
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
            hosting_provider = _wizard_state.get('hosting_provider', '').strip()
            inboxes_data = builder.build_inboxes(data, gmail_address, site_base_url, hosting_provider)
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
    config_path = REPO_ROOT / 'apps' / 'workflow_engine' / 'config.yaml'
    has_existing = env_path.exists() or config_path.exists()

    if has_existing and not data.get('overwrite_confirmed'):
        return jsonify({
            "ok": False,
            "overwrite_required": True,
            "error": "existing config files detected — set overwrite_confirmed to proceed",
        }), 409

    env_str, yaml_str = builder.build_final_outputs(_wizard_state, persist_secrets=True)
    _write_config_pair(env_path, env_str, config_path, yaml_str)
    return jsonify({"ok": True, "next_step": "/step/done"})


def _write_siteground_key_file(key_contents: str) -> Path:
    """Atomically write the pasted SiteGround private key with 0600 perms.
    Returns the absolute path the caller should store in wizard state.
    """
    key_path = (REPO_ROOT / builder.SITEGROUND_KEY_RELPATH).resolve()
    key_path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp = tempfile.mkstemp(dir=key_path.parent, prefix='.siteground.key.')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(key_contents)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, str(key_path))
        tmp = None
    finally:
        if tmp and os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass

    return key_path


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
