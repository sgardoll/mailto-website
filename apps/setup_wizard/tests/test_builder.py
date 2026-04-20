# pyright: basic
"""Unit tests for setup.builder validate() and build() functions."""
import json

import yaml
import pytest

from unittest.mock import patch

from apps.setup_wizard.builder import (
    validate, build, validate_hosting, build_hosting, validate_inboxes, build_inboxes,
    fetch_vercel_project_url, ProviderLookupError,
    build_final_outputs, mask_for_preview, hydrate_wizard_state,
)


VALID_DATA = {
    'gmail_address': 'user@gmail.com',
    'gmail_app_password': 'abcd efgh ijkl mnop',
    'gmail_folder': 'INBOX',
    'allowed_senders': ['sender@example.com'],
    'lms_base_url': 'http://localhost:1234/v1',
    'lms_model': 'google/gemma-4-26b-a4b',
    'lms_temperature': 0.4,
    'lms_max_tokens': 4096,
    'lms_cli_path': 'lms',
    'autostart': True,
    'request_timeout_s': 600,
}


# -- validate() tests --------------------------------------------------------

def test_validate_passes_on_valid_data():
    """When all required fields are present and valid, validate returns no errors."""
    assert validate(VALID_DATA) == []


def test_validate_requires_gmail_address():
    """When gmail_address is empty, validate returns a field error for gmail_address."""
    data = {**VALID_DATA, 'gmail_address': ''}
    errors = validate(data)
    assert any(e['field'] == 'gmail_address' for e in errors)


def test_validate_rejects_whitespace_only_password():
    """When gmail_app_password is whitespace only, validate returns a field error."""
    data = {**VALID_DATA, 'gmail_app_password': '   '}
    errors = validate(data)
    assert any(e['field'] == 'gmail_app_password' for e in errors)


def test_validate_requires_at_least_one_sender():
    """When allowed_senders is an empty list, validate returns a field error."""
    data = {**VALID_DATA, 'allowed_senders': []}
    errors = validate(data)
    assert any(e['field'] == 'allowed_senders' for e in errors)


def test_validate_requires_list_not_string():
    """When allowed_senders is a string instead of a list, validate returns a field error."""
    data = {**VALID_DATA, 'allowed_senders': 'sender@example.com'}
    errors = validate(data)
    assert any(e['field'] == 'allowed_senders' for e in errors)


# -- build() tests -----------------------------------------------------------

def test_build_env_str_contains_app_password():
    """When build() is called, env_str contains GMAIL_APP_PASSWORD with the actual password."""
    env_str, _ = build(VALID_DATA)
    assert env_str == 'GMAIL_APP_PASSWORD=abcd efgh ijkl mnop\n'


def test_build_yaml_references_env_var_not_password():
    """When build() is called, yaml_str uses the env-var reference, not the raw password."""
    _, yaml_str = build(VALID_DATA)
    assert '${GMAIL_APP_PASSWORD}' in yaml_str
    assert 'abcd efgh ijkl mnop' not in yaml_str


def test_build_gmail_address_fans_out():
    """When build() is called, gmail_address appears in imap.user, smtp.user, smtp.from_address."""
    _, yaml_str = build(VALID_DATA)
    config = yaml.safe_load(yaml_str)
    assert config['imap']['user'] == 'user@gmail.com'
    assert config['smtp']['user'] == 'user@gmail.com'
    assert config['smtp']['from_address'] == 'user@gmail.com'


def test_build_api_key_is_hardcoded():
    """When build() is called, lm_studio.api_key is always 'lm-studio' regardless of input."""
    _, yaml_str = build(VALID_DATA)
    config = yaml.safe_load(yaml_str)
    assert config['lm_studio']['api_key'] == 'lm-studio'


def test_build_output_sections_only():
    """When build() is called, config contains only the Phase 2 sections (D-01)."""
    _, yaml_str = build(VALID_DATA)
    config = yaml.safe_load(yaml_str)
    assert set(config.keys()) == {'global_allowed_senders', 'imap', 'smtp', 'lm_studio'}
    for forbidden in ('git_branch', 'git_push', 'dry_run', 'siteground', 'inboxes'):
        assert forbidden not in config


def test_build_yaml_is_parseable():
    """When build() is called, the yaml_str can be parsed by yaml.safe_load without error."""
    _, yaml_str = build(VALID_DATA)
    config = yaml.safe_load(yaml_str)
    assert isinstance(config, dict)


def test_build_advanced_fields_included():
    """When build() is called, lm_studio includes autostart and request_timeout_s (D-02)."""
    _, yaml_str = build(VALID_DATA)
    config = yaml.safe_load(yaml_str)
    assert config['lm_studio']['autostart'] is True
    assert config['lm_studio']['request_timeout_s'] == 600


def test_build_defaults_applied_when_optional_keys_absent():
    """When optional LMS keys are absent, build() applies DEFAULTS values."""
    minimal = {
        'gmail_address': 'user@gmail.com',
        'gmail_app_password': 'abcd efgh ijkl mnop',
        'allowed_senders': ['sender@example.com'],
    }
    _, yaml_str = build(minimal)
    config = yaml.safe_load(yaml_str)
    assert config['lm_studio']['base_url'] == 'http://localhost:1234/v1'
    assert config['lm_studio']['model'] == 'google/gemma-4-26b-a4b'
    assert config['imap']['folder'] == 'INBOX'


# -- Integration: POST /validate-form route -----------------------------------

def test_validate_form_route_returns_ok():
    """When valid data is POSTed to /validate-form, the route returns 200 with ok=true."""
    from unittest.mock import patch
    from apps.setup_wizard.server import app
    with patch('apps.setup_wizard.server._wizard_state', {}):
        with app.test_client() as client:
            response = client.post(
                '/validate-form',
                data=json.dumps(VALID_DATA),
                content_type='application/json',
            )
    assert response.status_code == 200
    data = response.get_json()
    assert data['ok'] is True
    assert 'env_preview' in data
    assert 'yaml_preview' in data


def test_validate_form_route_returns_errors_on_invalid_data():
    """When required fields are missing, /validate-form returns 400 with ok=false and errors list."""
    from unittest.mock import patch
    from apps.setup_wizard.server import app
    with patch('apps.setup_wizard.server._wizard_state', {}):
        with app.test_client() as client:
            response = client.post(
                '/validate-form',
                data=json.dumps({}),
                content_type='application/json',
            )
    assert response.status_code == 400
    data = response.get_json()
    assert data['ok'] is False
    assert isinstance(data['errors'], list)
    assert len(data['errors']) > 0


# -- Phase 3: validate_hosting / build_hosting tests --------------------------

SAMPLE_PRIVATE_KEY = (
    "-----BEGIN OPENSSH PRIVATE KEY-----\n"
    "b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gt\n"
    "ZWQyNTUxOQAAACBsampledsamplelinesampledsamplelinesampleysample=\n"
    "-----END OPENSSH PRIVATE KEY-----\n"
)


VALID_HOSTING_SITEGROUND = {
    'hosting_provider': 'siteground',
    'sg-host': 'ssh.example.com',
    'sg-port': '18765',
    'sg-username': 'u123-user',
    'sg-ssh_private_key': SAMPLE_PRIVATE_KEY,
    'sg-password': '',
    'sg-remote_base_path': '/home/user/public_html',
    'site_base_url': 'https://example.com',
}

VALID_HOSTING_VERCEL = {
    'hosting_provider': 'vercel',
    'vercel_api_token': 'vtok456',
    'vercel_project_id': 'my-project',
}


def test_validate_hosting_passes_siteground():
    assert validate_hosting(VALID_HOSTING_SITEGROUND) == []


def test_validate_hosting_rejects_unknown_provider():
    errors = validate_hosting({'hosting_provider': 'ftp'})
    assert any(e['field'] == 'hosting_provider' for e in errors)


def test_validate_hosting_requires_sg_host():
    data = {**VALID_HOSTING_SITEGROUND, 'sg-host': ''}
    errors = validate_hosting(data)
    assert any(e['field'] == 'sg-host' and 'required' in e['message'].lower() for e in errors)


def test_validate_hosting_sg_port_must_be_integer_in_range():
    data = {**VALID_HOSTING_SITEGROUND, 'sg-port': '99999'}
    errors = validate_hosting(data)
    assert any(e['field'] == 'sg-port' for e in errors)


def test_validate_hosting_siteground_at_least_one_credential():
    data = {**VALID_HOSTING_SITEGROUND, 'sg-ssh_private_key': '', 'sg-password': ''}
    errors = validate_hosting(data)
    assert any(e['field'] == 'sg-ssh_private_key' and 'required' in e['message'].lower() for e in errors)


def test_validate_hosting_siteground_password_alone_is_sufficient():
    data = {**VALID_HOSTING_SITEGROUND, 'sg-ssh_private_key': '', 'sg-password': 'secret'}
    assert validate_hosting(data) == []


def test_validate_hosting_siteground_rejects_malformed_key():
    data = {**VALID_HOSTING_SITEGROUND, 'sg-ssh_private_key': 'not-a-key'}
    errors = validate_hosting(data)
    assert any(e['field'] == 'sg-ssh_private_key' for e in errors)


def test_validate_hosting_siteground_existing_key_satisfies_credential():
    """Re-running wizard: existing key_path loaded by hydration counts as a credential."""
    data = {**VALID_HOSTING_SITEGROUND,
            'sg-ssh_private_key': '',
            'sg-password': '',
            'sg-existing_key_path': '/abs/path/to/siteground.key'}
    assert validate_hosting(data) == []


def test_validate_hosting_vercel_passes():
    assert validate_hosting(VALID_HOSTING_VERCEL) == []


def test_validate_hosting_does_not_validate_hidden_provider_fields():
    """Only siteground fields should be validated when provider='siteground', not vercel fields."""
    data = {**VALID_HOSTING_SITEGROUND}  # no vercel_api_token present
    assert validate_hosting(data) == []


def test_build_hosting_siteground_emits_correct_keys():
    result = build_hosting(VALID_HOSTING_SITEGROUND)
    assert 'siteground' in result
    sg = result['siteground']
    assert sg['host'] == 'ssh.example.com'
    assert sg['port'] == 18765  # must be int
    assert sg['user'] == 'u123-user'
    # Pasted key → build_hosting emits the relative target path;
    # server./write-config resolves it to an absolute path and writes the key.
    assert sg['key_path'] == 'runtime/state/siteground.key'
    assert sg['base_remote_path'] == '/home/user/public_html'


def test_build_hosting_siteground_preserves_existing_key_path_when_no_paste():
    data = {**VALID_HOSTING_SITEGROUND,
            'sg-ssh_private_key': '',
            'sg-existing_key_path': '/abs/previously/configured.key'}
    result = build_hosting(data)
    assert result['siteground']['key_path'] == '/abs/previously/configured.key'


def test_build_hosting_stores_hosting_provider():
    result = build_hosting(VALID_HOSTING_VERCEL)
    assert result.get('hosting_provider') == 'vercel'


def test_build_hosting_vercel_keys():
    result = build_hosting(VALID_HOSTING_VERCEL)
    assert result['vercel'] == {'api_token': 'vtok456', 'project_id': 'my-project'}


def test_validate_hosting_requires_site_base_url_for_siteground():
    data = {**VALID_HOSTING_SITEGROUND, 'site_base_url': ''}
    errors = validate_hosting(data)
    assert any(e['field'] == 'site_base_url' and 'required' in e['message'].lower() for e in errors)


def test_validate_hosting_rejects_non_url_site_base_url():
    data = {**VALID_HOSTING_SITEGROUND, 'site_base_url': 'example.com'}
    errors = validate_hosting(data)
    assert any(e['field'] == 'site_base_url' and 'valid url' in e['message'].lower() for e in errors)


def test_validate_hosting_does_not_require_site_base_url_for_vercel():
    # Vercel resolves the URL via API, so the form does not collect it.
    assert validate_hosting(VALID_HOSTING_VERCEL) == []


def test_build_hosting_includes_site_base_url_stripped_of_trailing_slash():
    data = {**VALID_HOSTING_SITEGROUND, 'site_base_url': 'https://example.com/'}
    result = build_hosting(data)
    assert result['site_base_url'] == 'https://example.com'


# -- Phase 3: validate_inboxes / build_inboxes tests --------------------------

VALID_INBOXES_DATA = {
    'inboxes': [
        {'slug': 'guitar', 'site_name': 'Guitar Notes'},
        {'slug': 'cooking', 'site_name': 'Cooking Notes'},
    ]
}


def test_validate_inboxes_passes_on_valid_data():
    assert validate_inboxes(VALID_INBOXES_DATA) == []


def test_validate_inboxes_rejects_empty_list():
    errors = validate_inboxes({'inboxes': []})
    assert any(e['field'] == 'inboxes' for e in errors)


def test_validate_inboxes_rejects_missing_inboxes_key():
    errors = validate_inboxes({})
    assert any(e['field'] == 'inboxes' for e in errors)


def test_validate_inboxes_rejects_invalid_slug_format():
    data = {'inboxes': [{'slug': 'My Inbox!', 'site_name': 'X'}]}
    errors = validate_inboxes(data)
    assert any(e['field'] == 'inbox_slug' and e['index'] == 0 for e in errors)


def test_validate_inboxes_rejects_empty_slug():
    data = {'inboxes': [{'slug': '', 'site_name': 'X'}]}
    errors = validate_inboxes(data)
    assert any(e['field'] == 'inbox_slug' and e['index'] == 0 for e in errors)


def test_validate_inboxes_requires_site_name():
    data = {'inboxes': [{'slug': 'guitar', 'site_name': ''}]}
    errors = validate_inboxes(data)
    assert any(e['field'] == 'inbox_site_name' and e['index'] == 0 for e in errors)


def test_validate_inboxes_rejects_duplicate_slugs():
    data = {'inboxes': [
        {'slug': 'guitar', 'site_name': 'A'},
        {'slug': 'guitar', 'site_name': 'B'},
    ]}
    errors = validate_inboxes(data)
    dup_errors = [e for e in errors if e.get('message') == 'Slug must be unique across all inboxes']
    assert len(dup_errors) == 2


def test_build_inboxes_derives_address_url_and_base_from_slug():
    result = build_inboxes(VALID_INBOXES_DATA, 'me@gmail.com', 'https://example.com')
    first = result['inboxes'][0]
    assert first['slug'] == 'guitar'
    assert first['address'] == 'me+guitar@gmail.com'
    assert first['site_name'] == 'Guitar Notes'
    assert first['site_url'] == 'https://example.com/guitar'
    assert first['site_base'] == '/guitar/'
    assert first['allowed_senders'] == []


def test_build_inboxes_strips_trailing_slash_from_site_base_url():
    result = build_inboxes(VALID_INBOXES_DATA, 'me@gmail.com', 'https://example.com/')
    assert result['inboxes'][0]['site_url'] == 'https://example.com/guitar'


def test_build_inboxes_preserves_order():
    result = build_inboxes(VALID_INBOXES_DATA, 'me@gmail.com', 'https://example.com')
    slugs = [i['slug'] for i in result['inboxes']]
    assert slugs == ['guitar', 'cooking']


# -- Phase 3: provider URL lookup tests --------------------------------------

class _FakeHTTPResponse:
    def __init__(self, payload):
        self._payload = json.dumps(payload).encode('utf-8')
    def read(self):
        return self._payload
    def __enter__(self):
        return self
    def __exit__(self, *exc):
        return False


def test_fetch_vercel_project_url_uses_production_alias():
    payload = {'targets': {'production': {'alias': ['my-proj.vercel.app']}}, 'name': 'my-proj'}
    with patch('apps.setup_wizard.builder.urllib.request.urlopen', return_value=_FakeHTTPResponse(payload)):
        assert fetch_vercel_project_url('tok', 'proj') == 'https://my-proj.vercel.app'


def test_fetch_vercel_project_url_falls_back_to_name():
    payload = {'name': 'my-proj'}
    with patch('apps.setup_wizard.builder.urllib.request.urlopen', return_value=_FakeHTTPResponse(payload)):
        assert fetch_vercel_project_url('tok', 'proj') == 'https://my-proj.vercel.app'


# -- Phase 4: final assembly / preview masking / hydration --------------------

FINAL_WIZARD_STATE = {
    **VALID_DATA,
    'hosting_provider': 'siteground',
    'siteground': {
        'host': 'ssh.example.com',
        'port': 18765,
        'user': 'u123-user',
        'key_path': '/home/user/.ssh/id_rsa',
        'password': 'super-secret-password',
        'base_remote_path': '/home/user/public_html',
    },
    'site_base_url': 'https://example.com',
    'inboxes': [
        {
            'slug': 'guitar',
            'address': 'user+guitar@gmail.com',
            'site_name': 'Guitar Notes',
            'site_url': 'https://example.com/guitar',
            'site_base': '/guitar/',
            'allowed_senders': [],
        },
    ],
}


def test_build_final_outputs_includes_runtime_defaults_provider_and_inboxes():
    env_str, yaml_str = build_final_outputs(FINAL_WIZARD_STATE)
    config = yaml.safe_load(yaml_str)

    assert env_str == 'GMAIL_APP_PASSWORD=abcd efgh ijkl mnop\n'
    assert list(config.keys()) == [
        'git_branch', 'git_push', 'dry_run', 'global_allowed_senders',
        'imap', 'smtp', 'lm_studio', 'siteground', 'inboxes',
    ]
    assert config['git_branch'] == 'main'
    assert config['git_push'] is True
    assert config['dry_run'] is False
    assert config['siteground']['host'] == 'ssh.example.com'
    assert config['inboxes'][0]['site_url'] == 'https://example.com/guitar'
    for forbidden in ('vercel', 'ssh_sftp', 'hosting_provider', 'site_base_url'):
        assert forbidden not in config


def test_build_final_outputs_preserves_hidden_runtime_keys_when_present():
    state = {
        **FINAL_WIZARD_STATE,
        'git_branch': 'release',
        'git_push': False,
        'dry_run': True,
    }
    _, yaml_str = build_final_outputs(state)
    config = yaml.safe_load(yaml_str)
    assert config['git_branch'] == 'release'
    assert config['git_push'] is False
    assert config['dry_run'] is True


def test_build_final_outputs_can_derive_provider_and_inboxes_from_wizard_fields():
    state = {
        **VALID_DATA,
        **VALID_HOSTING_SITEGROUND,
        **VALID_INBOXES_DATA,
    }
    env_str, yaml_str = build_final_outputs(state)
    config = yaml.safe_load(yaml_str)
    assert env_str == 'GMAIL_APP_PASSWORD=abcd efgh ijkl mnop\n'
    assert config['siteground']['host'] == 'ssh.example.com'
    assert config['inboxes'][0]['address'] == 'user+guitar@gmail.com'
    assert config['inboxes'][0]['site_base'] == '/guitar/'


def test_mask_for_preview_masks_env_secret_but_keeps_yaml_placeholder_literal():
    env_str, yaml_str = build_final_outputs(FINAL_WIZARD_STATE)
    masked_env, masked_yaml = mask_for_preview(env_str, yaml_str)

    assert 'abcd efgh ijkl mnop' not in masked_env
    assert masked_env == 'GMAIL_APP_PASSWORD=***************mnop\n'
    assert '${GMAIL_APP_PASSWORD}' in masked_yaml
    assert 'abcd efgh ijkl mnop' not in masked_yaml


def test_mask_for_preview_masks_provider_secrets_to_last_four_only():
    env_str, yaml_str = build_final_outputs({
        **FINAL_WIZARD_STATE,
        'hosting_provider': 'vercel',
        'vercel': {'api_token': 'vercel-secret-token', 'project_id': 'proj-123'},
    })
    _, masked_yaml = mask_for_preview(env_str, yaml_str)
    config = yaml.safe_load(masked_yaml)

    assert config['vercel']['api_token'].endswith('oken')
    assert config['vercel']['api_token'] != 'vercel-secret-token'
    assert 'vercel-secret-token' not in masked_yaml


def test_hydrate_wizard_state_reconstructs_visible_values_and_hidden_runtime_keys():
    env_values = {'GMAIL_APP_PASSWORD': 'abcd efgh ijkl mnop'}
    config_values = {
        'git_branch': 'release',
        'git_push': False,
        'dry_run': True,
        'global_allowed_senders': ['sender@example.com'],
        'imap': {
            'user': 'user@gmail.com',
            'folder': 'Ideas',
        },
        'smtp': {'user': 'user@gmail.com'},
        'lm_studio': {
            'base_url': 'http://localhost:2233/v1',
            'model': 'custom-model',
            'temperature': 0.8,
            'max_tokens': 1234,
            'lms_cli_path': '/usr/local/bin/lms',
            'autostart': False,
            'request_timeout_s': 321,
        },
        'siteground': {
            'host': 'ssh.example.com',
            'port': 18765,
            'user': 'u123-user',
            'key_path': '/home/user/.ssh/id_rsa',
            'password': 'existing-password',
            'base_remote_path': '/home/user/public_html',
        },
        'inboxes': [
            {
                'slug': 'guitar',
                'site_name': 'Guitar Notes',
                'site_url': 'https://example.com/guitar',
            },
            {
                'slug': 'cooking',
                'site_name': 'Cooking Notes',
                'site_url': 'https://example.com/cooking',
            },
        ],
    }

    state = hydrate_wizard_state(env_values, config_values)

    assert state['gmail_address'] == 'user@gmail.com'
    assert state['gmail_app_password'] == 'abcd efgh ijkl mnop'
    assert state['gmail_folder'] == 'Ideas'
    assert state['allowed_senders'] == ['sender@example.com']
    assert state['hosting_provider'] == 'siteground'
    assert state['site_base_url'] == 'https://example.com'
    assert state['sg-host'] == 'ssh.example.com'
    assert state['sg-port'] == 18765
    assert state['sg-password'] == 'existing-password'
    assert state['inboxes'] == [
        {'slug': 'guitar', 'site_name': 'Guitar Notes'},
        {'slug': 'cooking', 'site_name': 'Cooking Notes'},
    ]
    assert state['git_branch'] == 'release'
    assert state['git_push'] is False
    assert state['dry_run'] is True


def test_hydrate_wizard_state_uses_runtime_defaults_when_absent():
    state = hydrate_wizard_state(
        {'GMAIL_APP_PASSWORD': 'secret'},
        {
            'imap': {'user': 'user@gmail.com'},
            'smtp': {'user': 'user@gmail.com'},
            'lm_studio': {},
            'inboxes': [],
        },
    )

    assert state['git_branch'] == 'main'
    assert state['git_push'] is True
    assert state['dry_run'] is False


def test_hydrate_wizard_state_leaves_site_base_url_empty_when_inbox_urls_are_ambiguous():
    state = hydrate_wizard_state(
        {'GMAIL_APP_PASSWORD': 'secret'},
        {
            'imap': {'user': 'user@gmail.com'},
            'smtp': {'user': 'user@gmail.com'},
            'lm_studio': {},
            'ssh_sftp': {'host': 'h', 'user': 'u'},
            'inboxes': [
                {
                    'slug': 'guitar',
                    'site_name': 'Guitar Notes',
                    'site_url': 'https://example.com/guitar',
                },
                {
                    'slug': 'cooking',
                    'site_name': 'Cooking Notes',
                    'site_url': 'https://other.example.com/cooking',
                },
            ],
        },
    )

    assert state['hosting_provider'] == 'ssh_sftp'
    assert state['site_base_url'] == ''
