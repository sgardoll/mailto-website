# pyright: basic
"""Integration tests for Phase 4 backend flow: prefill, preview, write-config, rollback, done."""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

import setup.server as server_module
from setup.server import app, _write_config_pair


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MINIMAL_STATE = {
    'gmail_address': 'user@gmail.com',
    'gmail_app_password': 'abcdefghijklmnop',
    'gmail_folder': 'INBOX',
    'allowed_senders': ['sender@example.com'],
    'lms_base_url': 'http://localhost:1234/v1',
    'lms_model': 'google/gemma-4-26b-a4b',
    'lms_temperature': 0.4,
    'lms_max_tokens': 4096,
    'lms_cli_path': 'lms',
    'autostart': True,
    'request_timeout_s': 600,
    'hosting_provider': 'siteground',
    'siteground': {
        'host': 'ssh.example.com',
        'port': 18765,
        'user': 'u123-customer',
        'key_path': '~/.ssh/id_ed25519',
        'password': '',
        'base_remote_path': '/home/customer/public_html',
    },
    'site_base_url': 'https://example.com',
    'inboxes': [
        {
            'slug': 'blog',
            'address': 'user+blog@gmail.com',
            'site_name': 'My Blog',
            'site_url': 'https://example.com/blog',
            'site_base': '/blog/',
            'allowed_senders': [],
        }
    ],
    'git_branch': 'main',
    'git_push': True,
    'dry_run': False,
}


@pytest.fixture()
def client():
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def reset_server_state():
    """Reset _wizard_state and _prefilled between tests."""
    original_state = dict(server_module._wizard_state)
    original_prefilled = server_module._prefilled
    server_module._wizard_state.clear()
    server_module._prefilled = False
    yield
    server_module._wizard_state.clear()
    server_module._wizard_state.update(original_state)
    server_module._prefilled = original_prefilled


# ---------------------------------------------------------------------------
# Prefill hydration
# ---------------------------------------------------------------------------

def test_prefill_populates_wizard_state_from_existing_files():
    """When .env and workflow/config.yaml exist, _try_prefill() hydrates _wizard_state."""
    env_content = 'GMAIL_APP_PASSWORD=testpassword1234\n'
    config_content = yaml.dump({
        'git_branch': 'main',
        'git_push': True,
        'dry_run': False,
        'global_allowed_senders': ['sender@example.com'],
        'imap': {
            'host': 'imap.gmail.com',
            'port': 993,
            'user': 'user@gmail.com',
            'password': '${GMAIL_APP_PASSWORD}',
            'folder': 'INBOX',
            'use_ssl': True,
        },
        'smtp': {
            'host': 'smtp.gmail.com',
            'port': 587,
            'user': 'user@gmail.com',
            'password': '${GMAIL_APP_PASSWORD}',
            'from_address': 'user@gmail.com',
            'use_starttls': True,
        },
        'lm_studio': {
            'base_url': 'http://localhost:1234/v1',
            'api_key': 'lm-studio',
            'model': 'google/gemma-4-26b-a4b',
            'lms_cli_path': 'lms',
            'autostart': True,
            'temperature': 0.4,
            'max_tokens': 4096,
            'request_timeout_s': 600,
        },
        'inboxes': [],
    })

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        env_path = tmp / '.env'
        config_dir = tmp / 'workflow'
        config_dir.mkdir()
        config_path = config_dir / 'config.yaml'

        env_path.write_text(env_content)
        config_path.write_text(config_content)

        with patch.object(server_module, 'REPO_ROOT', tmp):
            server_module._prefilled = False
            server_module._try_prefill()

        assert server_module._wizard_state.get('gmail_address') == 'user@gmail.com'
        assert server_module._wizard_state.get('gmail_app_password') == 'testpassword1234'


def test_prefill_skips_if_no_files_exist():
    """When neither .env nor config.yaml exist, _try_prefill() leaves _wizard_state empty."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        with patch.object(server_module, 'REPO_ROOT', tmp):
            server_module._prefilled = False
            server_module._try_prefill()

    assert server_module._wizard_state == {}


def test_prefill_runs_only_once():
    """_try_prefill() does not re-read files on a second call."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        env_path = tmp / '.env'
        env_path.write_text('GMAIL_APP_PASSWORD=first\n')

        with patch.object(server_module, 'REPO_ROOT', tmp):
            server_module._prefilled = False
            server_module._try_prefill()
            # Overwrite the file after first prefill
            env_path.write_text('GMAIL_APP_PASSWORD=second\n')
            server_module._try_prefill()

        # Should still have the value from the first read
        assert server_module._wizard_state.get('gmail_app_password') == 'first'


# ---------------------------------------------------------------------------
# Preview route
# ---------------------------------------------------------------------------

def test_preview_route_renders_masked_content(client):
    """GET /step/preview returns 200 and contains masked preview content."""
    server_module._wizard_state.update(MINIMAL_STATE)
    server_module._prefilled = True  # skip prefill I/O

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        with patch.object(server_module, 'REPO_ROOT', tmp):
            resp = client.get('/step/preview')

    assert resp.status_code == 200
    body = resp.data.decode()
    # Password should be masked (not the raw value)
    assert 'abcdefghijklmnop' not in body
    # Last 4 of password should appear
    assert 'mnop' in body


def test_preview_route_redirects_when_state_incomplete(client):
    """GET /step/preview redirects to gmail step when wizard state has no gmail_address."""
    server_module._prefilled = True

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        with patch.object(server_module, 'REPO_ROOT', tmp):
            resp = client.get('/step/preview')

    assert resp.status_code == 200
    body = resp.data.decode()
    # Should render the gmail step (index.html)
    assert 'Gmail' in body


def test_preview_shows_overwrite_warning_when_files_exist(client):
    """GET /step/preview includes overwrite warning when existing config files are present."""
    server_module._wizard_state.update(MINIMAL_STATE)
    server_module._prefilled = True

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        (tmp / '.env').write_text('GMAIL_APP_PASSWORD=old\n')

        with patch.object(server_module, 'REPO_ROOT', tmp):
            resp = client.get('/step/preview')

    body = resp.data.decode()
    assert 'overwrite' in body.lower() or 'Existing config' in body


def test_preview_no_overwrite_warning_when_no_files(client):
    """GET /step/preview does not show overwrite warning when no existing config files."""
    server_module._wizard_state.update(MINIMAL_STATE)
    server_module._prefilled = True

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        with patch.object(server_module, 'REPO_ROOT', tmp):
            resp = client.get('/step/preview')

    body = resp.data.decode()
    assert 'overwrite-warning' not in body


# ---------------------------------------------------------------------------
# /write-config — confirmation gate
# ---------------------------------------------------------------------------

def test_write_config_requires_confirmation(client):
    """POST /write-config returns 400 when confirmed is missing."""
    resp = client.post('/write-config', json={})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data['ok'] is False
    assert 'confirm' in data['error'].lower()


def test_write_config_requires_overwrite_confirmation_when_files_exist(client):
    """POST /write-config returns 409 when existing files present and overwrite not confirmed."""
    server_module._wizard_state.update(MINIMAL_STATE)
    server_module._prefilled = True

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        (tmp / '.env').write_text('GMAIL_APP_PASSWORD=old\n')

        with patch.object(server_module, 'REPO_ROOT', tmp):
            resp = client.post('/write-config', json={'confirmed': True})

    assert resp.status_code == 409
    data = resp.get_json()
    assert data['ok'] is False
    assert data.get('overwrite_required') is True


# ---------------------------------------------------------------------------
# /write-config — successful pair-write
# ---------------------------------------------------------------------------

def test_write_config_writes_both_files(client):
    """POST /write-config writes .env and workflow/config.yaml when confirmed."""
    server_module._wizard_state.update(MINIMAL_STATE)
    server_module._prefilled = True

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        (tmp / 'workflow').mkdir()

        with patch.object(server_module, 'REPO_ROOT', tmp):
            resp = client.post('/write-config', json={'confirmed': True})

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['ok'] is True
        assert data['next_step'] == '/step/done'

        assert (tmp / '.env').exists()
        assert (tmp / 'workflow' / 'config.yaml').exists()


def test_write_config_env_content_correct(client):
    """Written .env contains the correct GMAIL_APP_PASSWORD value."""
    server_module._wizard_state.update(MINIMAL_STATE)
    server_module._prefilled = True

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        (tmp / 'workflow').mkdir()

        with patch.object(server_module, 'REPO_ROOT', tmp):
            client.post('/write-config', json={'confirmed': True})

        env_text = (tmp / '.env').read_text()
        assert 'GMAIL_APP_PASSWORD=abcdefghijklmnop' in env_text


def test_write_config_overwrites_when_confirmed(client):
    """POST /write-config succeeds when overwrite_confirmed is True and files exist."""
    server_module._wizard_state.update(MINIMAL_STATE)
    server_module._prefilled = True

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        (tmp / 'workflow').mkdir()
        (tmp / '.env').write_text('GMAIL_APP_PASSWORD=old\n')
        (tmp / 'workflow' / 'config.yaml').write_text('git_branch: old\n')

        with patch.object(server_module, 'REPO_ROOT', tmp):
            resp = client.post('/write-config', json={
                'confirmed': True,
                'overwrite_confirmed': True,
            })

        assert resp.status_code == 200
        env_text = (tmp / '.env').read_text()
        assert 'abcdefghijklmnop' in env_text


# ---------------------------------------------------------------------------
# _write_config_pair — rollback on second-write failure
# ---------------------------------------------------------------------------

def test_pair_write_rollback_restores_env_on_second_replace_failure():
    """If the second os.replace fails after the first succeeds, .env is restored from backup."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        env_path = tmp / '.env'
        config_dir = tmp / 'workflow'
        config_dir.mkdir()
        config_path = config_dir / 'config.yaml'

        # Write original content
        original_env = 'GMAIL_APP_PASSWORD=original\n'
        original_yaml = 'git_branch: original\n'
        env_path.write_text(original_env)
        config_path.write_text(original_yaml)

        call_count = [0]
        original_replace = os.replace

        def patched_replace(src, dst):
            call_count[0] += 1
            if call_count[0] == 2:
                raise OSError("Simulated second replace failure")
            return original_replace(src, dst)

        with patch('os.replace', side_effect=patched_replace):
            with pytest.raises(OSError, match="Simulated"):
                _write_config_pair(env_path, 'GMAIL_APP_PASSWORD=new\n', config_path, 'git_branch: new\n')

        # .env should be restored to original content
        assert env_path.read_text() == original_env
        # config.yaml should be unchanged
        assert config_path.read_text() == original_yaml


def test_pair_write_no_partial_files_on_success():
    """After a successful pair-write, both targets exist and no tmp/bak files remain."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        env_path = tmp / '.env'
        config_dir = tmp / 'workflow'
        config_dir.mkdir()
        config_path = config_dir / 'config.yaml'

        _write_config_pair(env_path, 'GMAIL_APP_PASSWORD=newval\n', config_path, 'git_branch: main\n')

        assert env_path.exists()
        assert config_path.exists()

        # No leftover temp or backup files
        root_extras = [f for f in tmp.iterdir() if f.name != '.env' and not f.is_dir()]
        assert root_extras == [], f"Unexpected files in root: {root_extras}"

        workflow_extras = [f for f in config_dir.iterdir() if f.name != 'config.yaml']
        assert workflow_extras == [], f"Unexpected files in workflow: {workflow_extras}"


# ---------------------------------------------------------------------------
# /step/done route
# ---------------------------------------------------------------------------

def test_done_route_renders_run_workflow_command(client):
    """GET /step/done renders the success screen with a Start Workflow button."""
    resp = client.get('/step/done')
    assert resp.status_code == 200
    body = resp.data.decode()
    assert 'start-workflow-btn' in body
    # manual fallback reference remains for users who prefer the shell
    assert 'run-workflow.sh' in body


# ---------------------------------------------------------------------------
# /start-workflow and /workflow-status
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_workflow_state():
    original_proc = server_module._workflow_proc
    original_log = server_module._workflow_log
    server_module._workflow_proc = None
    server_module._workflow_log = None
    yield
    server_module._workflow_proc = original_proc
    server_module._workflow_log = original_log


class _FakeProc:
    def __init__(self, pid=12345, returncode=None):
        self.pid = pid
        self._rc = returncode

    def poll(self):
        return self._rc


def test_start_workflow_spawns_subprocess(client, tmp_path, monkeypatch):
    """POST /start-workflow spawns run-workflow.sh detached and returns running status."""
    script_dir = tmp_path / 'scripts'
    script_dir.mkdir()
    (script_dir / 'run-workflow.sh').write_text('#!/usr/bin/env bash\necho ok\n')
    (tmp_path / 'logs').mkdir(exist_ok=True)

    monkeypatch.setattr(server_module, 'REPO_ROOT', tmp_path)

    captured = {}

    class FakePopen:
        def __init__(self, args, **kwargs):
            captured['args'] = args
            captured['kwargs'] = kwargs
            self.pid = 99999
            self._rc = None

        def poll(self):
            return self._rc

    monkeypatch.setattr(server_module.subprocess, 'Popen', FakePopen)

    resp = client.post('/start-workflow')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['ok'] is True
    assert data['status'] == 'running'
    assert data['pid'] == 99999
    assert captured['args'] == [str(script_dir / 'run-workflow.sh')]
    # Must be detached so wizard exit doesn't kill the workflow
    assert captured['kwargs'].get('start_new_session') is True
    assert captured['kwargs'].get('cwd') == str(tmp_path)


def test_start_workflow_returns_existing_if_already_running(client, monkeypatch):
    """Second /start-workflow call while running returns the existing pid without respawning."""
    server_module._workflow_proc = _FakeProc(pid=42, returncode=None)

    def fail_popen(*a, **kw):
        raise AssertionError('Popen should not be called when already running')

    monkeypatch.setattr(server_module.subprocess, 'Popen', fail_popen)

    resp = client.post('/start-workflow')
    data = resp.get_json()
    assert resp.status_code == 200
    assert data['ok'] is True
    assert data['status'] == 'running'
    assert data['pid'] == 42


def test_start_workflow_missing_script_returns_error(client, tmp_path, monkeypatch):
    """If scripts/run-workflow.sh is missing, /start-workflow returns an error payload."""
    monkeypatch.setattr(server_module, 'REPO_ROOT', tmp_path)

    resp = client.post('/start-workflow')
    assert resp.status_code == 500
    data = resp.get_json()
    assert data['ok'] is False
    assert 'run-workflow.sh' in data['error']


def test_workflow_status_not_started(client):
    """GET /workflow-status before launch reports not_started."""
    resp = client.get('/workflow-status')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'not_started'
    assert data['log'] == []


def test_workflow_status_running_returns_log_tail(client, tmp_path):
    """GET /workflow-status while running returns the last log lines."""
    log = tmp_path / 'workflow.log'
    log.write_text('\n'.join(f'line {i}' for i in range(60)) + '\n')
    server_module._workflow_proc = _FakeProc(pid=77, returncode=None)
    server_module._workflow_log = log

    resp = client.get('/workflow-status')
    data = resp.get_json()
    assert data['status'] == 'running'
    assert data['pid'] == 77
    # Trimmed to last 50 lines
    assert len(data['log']) == 50
    assert data['log'][-1] == 'line 59'


def test_workflow_status_reports_failure_exit_code(client, tmp_path):
    """Non-zero exit reports status=failed with the exit code."""
    log = tmp_path / 'workflow.log'
    log.write_text('crashed\n')
    server_module._workflow_proc = _FakeProc(pid=77, returncode=1)
    server_module._workflow_log = log

    resp = client.get('/workflow-status')
    data = resp.get_json()
    assert data['status'] == 'failed'
    assert data['exit_code'] == 1
