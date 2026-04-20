# pyright: basic
"""Integration tests for Phase 4 backend flow: prefill, preview, write-config, rollback, done."""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

import apps.setup_wizard.server as server_module
from apps.setup_wizard.server import app, _write_config_pair


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
    """When .env and apps/workflow_engine/config.yaml exist, _try_prefill() hydrates _wizard_state."""
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
        config_dir = tmp / 'apps' / 'workflow_engine'
        config_dir.mkdir(parents=True)
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
    """POST /write-config writes .env and apps/workflow_engine/config.yaml when confirmed."""
    server_module._wizard_state.update(MINIMAL_STATE)
    server_module._prefilled = True

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        (tmp / 'apps' / 'workflow_engine').mkdir(parents=True)

        with patch.object(server_module, 'REPO_ROOT', tmp):
            resp = client.post('/write-config', json={'confirmed': True})

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['ok'] is True
        assert data['next_step'] == '/step/done'

        assert (tmp / '.env').exists()
        assert (tmp / 'apps' / 'workflow_engine' / 'config.yaml').exists()


def test_write_config_env_content_correct(client):
    """Written .env contains the correct GMAIL_APP_PASSWORD value."""
    server_module._wizard_state.update(MINIMAL_STATE)
    server_module._prefilled = True

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        (tmp / 'apps' / 'workflow_engine').mkdir(parents=True)

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
        (tmp / 'apps' / 'workflow_engine').mkdir(parents=True)
        (tmp / '.env').write_text('GMAIL_APP_PASSWORD=old\n')
        (tmp / 'apps' / 'workflow_engine' / 'config.yaml').write_text('git_branch: old\n')

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
        config_dir = tmp / 'apps' / 'workflow_engine'
        config_dir.mkdir(parents=True)
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
        config_dir = tmp / 'apps' / 'workflow_engine'
        config_dir.mkdir(parents=True)
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

def _seed_siteground_state():
    server_module._wizard_state.update({
        'hosting_provider': 'siteground',
        'site_base_url': 'https://example.com',
        'inboxes': [
            {'slug': 'guitar', 'address': 'u+guitar@gmail.com',
             'site_name': 'Guitar', 'site_url': 'https://example.com/guitar', 'site_base': '/guitar/'},
            {'slug': 'parenting', 'address': 'u+parenting@gmail.com',
             'site_name': 'Parenting', 'site_url': 'https://example.com/parenting', 'site_base': '/parenting/'},
        ],
    })


def test_hosting_submit_persists_siteground_key_to_disk(client, tmp_path, monkeypatch):
    """POST /validate-form step=hosting with a pasted SiteGround key writes the
    key to runtime/state/siteground.key at 0600 and stores the absolute path
    in wizard state so deploy can read it later.
    """
    monkeypatch.setattr(server_module, 'REPO_ROOT', tmp_path)
    key_text = (
        "-----BEGIN OPENSSH PRIVATE KEY-----\n"
        "c29tZS1mYWtlLWtleS1jb250ZW50cy1mb3ItdGVzdA==\n"
        "-----END OPENSSH PRIVATE KEY-----\n"
    )

    resp = client.post('/validate-form', json={
        'step': 'hosting',
        'hosting_provider': 'siteground',
        'sg-host': 'ssh.example.com',
        'sg-port': '18765',
        'sg-username': 'u123-user',
        'sg-ssh_private_key': key_text,
        'sg-password': '',
        'sg-remote_base_path': '/home/user/public_html',
        'site_base_url': 'https://example.com',
    })
    assert resp.status_code == 200
    assert resp.get_json()['ok'] is True

    # Key written to runtime/state/siteground.key with 0600 perms
    written = tmp_path / 'runtime' / 'state' / 'siteground.key'
    assert written.exists()
    assert written.read_text() == key_text
    mode = oct(written.stat().st_mode & 0o777)
    assert mode == '0o600'

    # Wizard state holds absolute path ready for YAML output
    sg = server_module._wizard_state.get('siteground')
    assert sg is not None
    assert sg['key_path'] == str(written.resolve())


def test_done_route_siteground_shows_deploy_button(client):
    _seed_siteground_state()
    resp = client.get('/step/done')
    assert resp.status_code == 200
    body = resp.data.decode()
    assert 'deploy-btn' in body
    assert 'Deploy Site' in body
    # Per-inbox rows pre-rendered for the progress panel
    assert 'data-slug="guitar"' in body
    assert 'data-slug="parenting"' in body
    # Manual fallback unchanged
    assert 'run-workflow.sh' in body


@pytest.mark.parametrize('provider,expected_marker', [
    ('vercel', 'Vercel dashboard'),
    ('ssh_sftp', 'rsync'),
])
def test_done_route_non_siteground_shows_manual_instructions(client, provider, expected_marker):
    server_module._wizard_state['hosting_provider'] = provider
    server_module._wizard_state['inboxes'] = [
        {'slug': 'x', 'address': 'u+x@gmail.com', 'site_name': 'X',
         'site_url': 'https://x.example/', 'site_base': '/'},
    ]
    resp = client.get('/step/done')
    assert resp.status_code == 200
    body = resp.data.decode()
    assert 'deploy-btn' not in body
    assert expected_marker in body


# ---------------------------------------------------------------------------
# /deploy and /deploy-status
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_deploy_state():
    original = dict(server_module._deploy_state)
    server_module._deploy_state.update({
        "status": "idle", "started_at": None, "inboxes": [], "error": None,
    })
    yield
    server_module._deploy_state.clear()
    server_module._deploy_state.update(original)


def test_deploy_endpoint_rejects_unimplemented_provider(client):
    # ssh_sftp is configurable in the wizard but has no provider impl yet,
    # so /deploy should reject it cleanly with a structured error.
    server_module._wizard_state['hosting_provider'] = 'ssh_sftp'
    server_module._wizard_state['inboxes'] = [
        {'slug': 'x', 'address': 'u+x@gmail.com', 'site_name': 'X',
         'site_url': 'https://x.example/', 'site_base': '/'},
    ]
    resp = client.post('/deploy')
    assert resp.status_code == 400
    data = resp.get_json()
    assert data['ok'] is False
    assert data['error'] == 'not_implemented'
    assert data['provider'] == 'ssh_sftp'


def test_deploy_endpoint_rejects_when_no_inboxes(client):
    server_module._wizard_state['hosting_provider'] = 'siteground'
    server_module._wizard_state['inboxes'] = []
    resp = client.post('/deploy')
    assert resp.status_code == 400
    assert resp.get_json()['error'] == 'no inboxes configured'


def test_deploy_endpoint_spawns_worker_for_siteground(client, monkeypatch):
    _seed_siteground_state()
    captured = {}

    class FakeThread:
        def __init__(self, target, daemon=None):
            captured['target'] = target
            captured['daemon'] = daemon
        def start(self):
            captured['started'] = True

    monkeypatch.setattr(server_module.threading, 'Thread', FakeThread)

    resp = client.post('/deploy')
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True, "status": "running"}
    assert captured.get('started') is True
    assert captured['daemon'] is True
    # State initialised with pending rows for each inbox
    assert server_module._deploy_state['status'] == 'running'
    slugs = [r['slug'] for r in server_module._deploy_state['inboxes']]
    assert slugs == ['guitar', 'parenting']
    assert all(r['phase'] == 'pending' for r in server_module._deploy_state['inboxes'])


def test_deploy_endpoint_noop_when_already_running(client, monkeypatch):
    _seed_siteground_state()
    server_module._deploy_state['status'] = 'running'

    def fail_thread(*a, **kw):
        raise AssertionError('Thread should not spawn when already running')

    monkeypatch.setattr(server_module.threading, 'Thread', fail_thread)

    resp = client.post('/deploy')
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True, "status": "running"}


def test_deploy_status_idle_by_default(client):
    resp = client.get('/deploy-status')
    data = resp.get_json()
    assert resp.status_code == 200
    assert data['status'] == 'idle'
    assert data['inboxes'] == []
    assert data['error'] is None


def test_update_inbox_progress_transitions(client):
    """_update_inbox_progress drives state correctly through phases."""
    server_module._reset_deploy_state(['alpha', 'beta'])
    server_module._update_inbox_progress('alpha', 'install', 'npm install')
    server_module._update_inbox_progress('alpha', 'done', 'https://alpha.example')

    resp = client.get('/deploy-status')
    rows = resp.get_json()['inboxes']
    alpha = next(r for r in rows if r['slug'] == 'alpha')
    beta = next(r for r in rows if r['slug'] == 'beta')
    assert alpha['phase'] == 'done'
    assert alpha['ok'] is True
    assert beta['phase'] == 'pending'
    assert beta['ok'] is False


def test_update_inbox_progress_records_failure(client):
    server_module._reset_deploy_state(['alpha'])
    server_module._update_inbox_progress('alpha', 'failed', 'BuildFailed: npm exited 1')

    rows = client.get('/deploy-status').get_json()['inboxes']
    assert rows[0]['phase'] == 'failed'
    assert rows[0]['error'] == 'BuildFailed: npm exited 1'
    assert rows[0]['ok'] is False
