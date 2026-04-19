"""Unit tests for setup.builder validate() and build() functions."""
import json

import yaml
import pytest

from setup.builder import validate, build, validate_hosting, build_hosting, validate_inboxes, build_inboxes


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
    from setup.server import app
    with patch('setup.server._wizard_state', {}):
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
    from setup.server import app
    with patch('setup.server._wizard_state', {}):
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

VALID_HOSTING_SITEGROUND = {
    'hosting_provider': 'siteground',
    'sg-host': 'ssh.example.com',
    'sg-port': '18765',
    'sg-username': 'u123-user',
    'sg-ssh_key_path': '/home/user/.ssh/id_rsa',
    'sg-password': '',
    'sg-remote_base_path': '/home/user/public_html',
}

VALID_HOSTING_NETLIFY = {
    'hosting_provider': 'netlify',
    'netlify_api_token': 'tok123',
    'netlify_site_id': 'abc-site',
}

VALID_HOSTING_VERCEL = {
    'hosting_provider': 'vercel',
    'vercel_api_token': 'vtok456',
    'vercel_project_id': 'my-project',
}

VALID_HOSTING_GITHUB_PAGES = {
    'hosting_provider': 'github_pages',
    'gh_pages_branch': 'gh-pages',
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


def test_validate_hosting_ssh_at_least_one_credential():
    data = {**VALID_HOSTING_SITEGROUND, 'sg-ssh_key_path': '', 'sg-password': ''}
    errors = validate_hosting(data)
    assert any(e['field'] == 'sg-ssh_key_path' and 'required' in e['message'].lower() for e in errors)


def test_validate_hosting_ssh_password_alone_is_sufficient():
    data = {**VALID_HOSTING_SITEGROUND, 'sg-ssh_key_path': '', 'sg-password': 'secret'}
    assert validate_hosting(data) == []


def test_validate_hosting_netlify_requires_token_and_site_id():
    errors = validate_hosting({'hosting_provider': 'netlify', 'netlify_api_token': '', 'netlify_site_id': ''})
    fields = [e['field'] for e in errors]
    assert 'netlify_api_token' in fields
    assert 'netlify_site_id' in fields


def test_validate_hosting_vercel_passes():
    assert validate_hosting(VALID_HOSTING_VERCEL) == []


def test_validate_hosting_github_pages_passes():
    assert validate_hosting(VALID_HOSTING_GITHUB_PAGES) == []


def test_validate_hosting_does_not_validate_hidden_provider_fields():
    """Only siteground fields should be validated when provider='siteground', not netlify fields."""
    data = {**VALID_HOSTING_SITEGROUND}  # no netlify_api_token present
    assert validate_hosting(data) == []


def test_build_hosting_siteground_emits_correct_keys():
    result = build_hosting(VALID_HOSTING_SITEGROUND)
    assert 'siteground' in result
    sg = result['siteground']
    assert sg['host'] == 'ssh.example.com'
    assert sg['port'] == 18765  # must be int
    assert sg['user'] == 'u123-user'
    assert sg['key_path'] == '/home/user/.ssh/id_rsa'
    assert sg['base_remote_path'] == '/home/user/public_html'


def test_build_hosting_stores_hosting_provider():
    result = build_hosting(VALID_HOSTING_NETLIFY)
    assert result.get('hosting_provider') == 'netlify'


def test_build_hosting_netlify_keys():
    result = build_hosting(VALID_HOSTING_NETLIFY)
    assert result['netlify'] == {'api_token': 'tok123', 'site_id': 'abc-site'}


def test_build_hosting_github_pages_uses_default_branch():
    data = {'hosting_provider': 'github_pages', 'gh_pages_branch': ''}
    result = build_hosting(data)
    assert result['github_pages']['branch'] == 'gh-pages'
