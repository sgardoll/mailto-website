# pyright: basic
import json
import re
import urllib.error
import urllib.parse
import urllib.request

import yaml

from apps.workflow_engine import secrets as keychain_secrets

# (wizard_state_key, nested_section_key, nested_field_name, keychain_account)
# Maps every wizard-managed secret to where it lives in wizard state, in the
# emitted YAML section, and in the OS keychain.
_KEYCHAIN_SECRETS = (
    ('sg-key_passphrase', 'siteground', 'key_passphrase',
     keychain_secrets.ACCOUNT_SITEGROUND_KEY_PASSPHRASE),
    ('sg-password', 'siteground', 'password',
     keychain_secrets.ACCOUNT_SITEGROUND_PASSWORD),
    ('ssh-password', 'ssh_sftp', 'password',
     keychain_secrets.ACCOUNT_SSH_SFTP_PASSWORD),
    ('vercel_api_token', 'vercel', 'api_token',
     keychain_secrets.ACCOUNT_VERCEL_API_TOKEN),
)

DEFAULTS = {
    'gmail_folder': 'INBOX',
    'lms_base_url': 'http://localhost:1234/v1',
    'lms_model': 'google/gemma-4-26b-a4b',
    'lms_temperature': 0.4,
    'lms_max_tokens': 4096,
    'lms_cli_path': 'lms',
    'autostart': True,
    'request_timeout_s': 600,
}

RUNTIME_DEFAULTS = {
    'git_branch': 'main',
    'git_push': True,
    'dry_run': False,
}


def validate(form_data: dict) -> list[dict]:
    """Return list of {field, message} dicts. Empty list means valid."""
    errors = []
    if not form_data.get('gmail_address', '').strip():
        errors.append({'field': 'gmail_address', 'message': 'Required'})
    if not form_data.get('gmail_app_password', '').strip():
        errors.append({'field': 'gmail_app_password', 'message': 'Required'})
    senders = form_data.get('allowed_senders', [])
    if not isinstance(senders, list) or len(senders) == 0:
        errors.append({'field': 'allowed_senders', 'message': 'At least one sender required'})
    return errors


def _build_base_config(form_data: dict) -> dict:
    email = form_data['gmail_address'].strip()
    return {
        'global_allowed_senders': form_data['allowed_senders'],
        'imap': {
            'host': 'imap.gmail.com',
            'port': 993,
            'user': email,
            'password': '${GMAIL_APP_PASSWORD}',
            'folder': form_data.get('gmail_folder', DEFAULTS['gmail_folder']),
            'use_ssl': True,
        },
        'smtp': {
            'host': 'smtp.gmail.com',
            'port': 587,
            'user': email,
            'password': '${GMAIL_APP_PASSWORD}',
            'from_address': email,
            'use_starttls': True,
        },
        'lm_studio': {
            'base_url': form_data.get('lms_base_url', DEFAULTS['lms_base_url']),
            'api_key': 'lm-studio',
            'model': form_data.get('lms_model', DEFAULTS['lms_model']),
            'lms_cli_path': form_data.get('lms_cli_path', DEFAULTS['lms_cli_path']),
            'autostart': form_data.get('autostart', DEFAULTS['autostart']),
            'temperature': float(form_data.get('lms_temperature', DEFAULTS['lms_temperature'])),
            'max_tokens': int(form_data.get('lms_max_tokens', DEFAULTS['lms_max_tokens'])),
            'request_timeout_s': int(form_data.get('request_timeout_s', DEFAULTS['request_timeout_s'])),
        },
    }


def build(form_data: dict) -> tuple[str, str]:
    """Return (env_str, yaml_str). Assumes validate() returned empty list."""
    config = _build_base_config(form_data)
    env_str = f"GMAIL_APP_PASSWORD={form_data['gmail_app_password'].strip()}\n"
    yaml_str = yaml.dump(config, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return env_str, yaml_str


from packages.config_contract import DeployProvider, normalize_provider, normalize_provider
_VALID_PROVIDERS = {p.value for p in DeployProvider}
_SSH_PROVIDERS = {'siteground', 'ssh_sftp'}
_SSH_PREFIX = {'siteground': 'sg-', 'ssh_sftp': 'ssh-'}

# Where the wizard writes pasted SSH keys. Relative to the repo root;
# the server resolves this against the actual project root.
SITEGROUND_KEY_RELPATH = 'runtime/state/siteground.key'


def _looks_like_private_key(text: str) -> bool:
    """True if text is a plausible OpenSSH/PEM private key block."""
    t = text.strip()
    if '-----BEGIN' not in t or '-----END' not in t:
        return False
    # Reject absolute paths that happen to contain the marker text
    if '\n' not in t:
        return False
    return t.startswith('-----BEGIN') and t.rstrip().endswith('-----')


def extract_siteground_key(form_data: dict) -> str | None:
    """Return the pasted SiteGround SSH private key, normalized, or None.
    Newlines normalized to \\n; trailing newline ensured. Used by the server
    write step to persist the key to disk before YAML output is written.
    """
    raw = form_data.get('sg-ssh_private_key', '')
    if not raw or not raw.strip():
        return None
    key = raw.replace('\r\n', '\n').replace('\r', '\n').strip()
    if not key.endswith('\n'):
        key = key + '\n'
    return key
_API_PROVIDERS = {'vercel'}
_URL_RE = re.compile(r'^https?://', re.IGNORECASE)


def _needs_manual_site_base_url(provider: str) -> bool:
    return provider in _SSH_PROVIDERS


def validate_hosting(form_data: dict) -> list[dict]:
    """Return list of {field, message} dicts for the hosting step."""
    errors = []
    provider = form_data.get('hosting_provider', '').strip()
    if provider not in _VALID_PROVIDERS:
        errors.append({'field': 'hosting_provider', 'message': 'Select a hosting provider'})
        return errors

    if provider in _SSH_PROVIDERS:
        prefix = _SSH_PREFIX[provider]
        host = form_data.get(f'{prefix}host', '').strip()
        if not host:
            errors.append({'field': f'{prefix}host', 'message': 'Host is required'})
        port_raw = form_data.get(f'{prefix}port', '')
        try:
            port = int(port_raw)
            if not (1 <= port <= 65535):
                raise ValueError
        except (ValueError, TypeError):
            errors.append({'field': f'{prefix}port', 'message': 'Port must be a number between 1 and 65535'})
        username = form_data.get(f'{prefix}username', '').strip()
        if not username:
            errors.append({'field': f'{prefix}username', 'message': 'Username is required'})
        password = form_data.get(f'{prefix}password', '').strip()
        if provider == 'siteground':
            # SiteGround: pasteable private key textarea replaces the legacy path input.
            key_contents = form_data.get(f'{prefix}ssh_private_key', '').strip()
            existing_key_path = (form_data.get(f'{prefix}existing_key_path') or '').strip()
            if key_contents:
                if not _looks_like_private_key(key_contents):
                    errors.append({'field': f'{prefix}ssh_private_key',
                                   'message': 'Paste the full key including -----BEGIN ... -----END lines'})
            elif not password and not existing_key_path:
                errors.append({'field': f'{prefix}ssh_private_key',
                               'message': 'Paste an SSH private key or enter a password — at least one is required'})
        else:
            key_path = form_data.get(f'{prefix}ssh_key_path', '').strip()
            if not key_path and not password:
                errors.append({'field': f'{prefix}ssh_key_path',
                               'message': 'Enter an SSH key path or a password — at least one is required'})
        remote_base_path = form_data.get(f'{prefix}remote_base_path', '').strip()
        if not remote_base_path:
            errors.append({'field': f'{prefix}remote_base_path', 'message': 'Remote base path is required'})

    elif provider == 'vercel':
        if not form_data.get('vercel_api_token', '').strip():
            errors.append({'field': 'vercel_api_token', 'message': 'API token is required'})
        if not form_data.get('vercel_project_id', '').strip():
            errors.append({'field': 'vercel_project_id', 'message': 'Project name or ID is required'})

    if _needs_manual_site_base_url(provider):
        site_base_url = form_data.get('site_base_url', '').strip()
        if not site_base_url:
            errors.append({'field': 'site_base_url', 'message': 'Site base URL is required'})
        elif not _URL_RE.match(site_base_url):
            errors.append({'field': 'site_base_url',
                           'message': 'Enter a valid URL (e.g. https://example.com)'})

    return errors


def build_hosting(form_data: dict) -> dict:
    """Return provider-keyed YAML section dict plus hosting_provider and site_base_url keys."""
    provider = form_data['hosting_provider']
    result = {'hosting_provider': provider}

    if provider in _SSH_PROVIDERS:
        prefix = _SSH_PREFIX[provider]
        section_key = 'siteground' if provider == 'siteground' else 'ssh_sftp'
        if provider == 'siteground':
            # Pasted key → the server will write to SITEGROUND_KEY_RELPATH and
            # set key_path to its absolute form. At build-hosting time we
            # emit the relative path; the server rewrites to absolute before
            # final YAML assembly if it actually wrote a key.
            pasted = form_data.get('sg-ssh_private_key', '').strip()
            existing = (form_data.get('sg-existing_key_path') or '').strip()
            if pasted:
                key_path = SITEGROUND_KEY_RELPATH
            else:
                key_path = existing
        else:
            key_path = form_data.get(f'{prefix}ssh_key_path', '').strip()
        section = {
            'host': form_data.get(f'{prefix}host', '').strip(),
            'port': int(form_data.get(f'{prefix}port', 22)),
            'user': form_data.get(f'{prefix}username', '').strip(),
            'key_path': key_path,
            'password': form_data.get(f'{prefix}password', '').strip(),
            'base_remote_path': form_data.get(f'{prefix}remote_base_path', '').strip(),
        }
        if provider == 'siteground':
            section['key_passphrase'] = form_data.get('sg-key_passphrase', '')
        result[section_key] = section
    elif provider == 'vercel':
        result['vercel'] = {
            'api_token': form_data.get('vercel_api_token', '').strip(),
            'project_id': form_data.get('vercel_project_id', '').strip(),
        }

    site_base_url = form_data.get('site_base_url', '').strip()
    if site_base_url:
        result['site_base_url'] = site_base_url.rstrip('/')

    # Workflow engine deployment config
    result['workflow_engine_enabled'] = form_data.get('workflow_engine_enabled', 'true').lower() == 'true'

    return result


class ProviderLookupError(Exception):
    """Raised when the provider API cannot resolve a site base URL."""


def _http_get_json(url: str, headers: dict, timeout: int = 10) -> dict:
    req = urllib.request.Request(url, headers=headers, method='GET')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        raise ProviderLookupError(f'HTTP {e.code}: {e.reason}') from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ProviderLookupError(f'Network error: {e}') from e


def fetch_vercel_project_url(api_token: str, project_id: str) -> str:
    """Return the public HTTPS URL for a Vercel project, raising ProviderLookupError on failure."""
    data = _http_get_json(
        f'https://api.vercel.com/v9/projects/{project_id}',
        {'Authorization': f'Bearer {api_token}'},
    )
    targets = data.get('targets') or {}
    production = targets.get('production') or {}
    aliases = production.get('alias') or []
    if aliases:
        host = aliases[0]
        return f'https://{host}' if not host.startswith('http') else host.rstrip('/')
    name = data.get('name')
    if name:
        return f'https://{name}.vercel.app'
    raise ProviderLookupError('Vercel project has no public URL or name yet')


_SLUG_RE = re.compile(r'^[a-z0-9-]+$')


def validate_inboxes(form_data: dict) -> list[dict]:
    """Return list of {field, message[, index]} dicts for the inboxes step.

    Each inbox only carries `slug` and `site_name` from the form — address,
    site_url and site_base are derived during build_inboxes().
    """
    errors = []
    inboxes = form_data.get('inboxes', None)
    if not isinstance(inboxes, list) or len(inboxes) == 0:
        errors.append({'field': 'inboxes', 'message': 'At least one inbox is required'})
        return errors

    slugs = []
    for i, inbox in enumerate(inboxes):
        slug = inbox.get('slug', '').strip()
        if not slug:
            errors.append({'field': 'inbox_slug', 'index': i, 'message': 'Slug is required'})
        elif not _SLUG_RE.match(slug):
            errors.append({'field': 'inbox_slug', 'index': i,
                           'message': 'Slug may only contain lowercase letters, numbers, and hyphens'})
        slugs.append(slug)

        if not inbox.get('site_name', '').strip():
            errors.append({'field': 'inbox_site_name', 'index': i, 'message': 'Site name is required'})

    seen = {}
    for i, slug in enumerate(slugs):
        if not slug:
            continue
        if slug in seen:
            errors.append({'field': 'inbox_slug', 'index': i,
                           'message': 'Slug must be unique across all inboxes'})
            if seen[slug] != -1:
                errors.append({'field': 'inbox_slug', 'index': seen[slug],
                               'message': 'Slug must be unique across all inboxes'})
                seen[slug] = -1
        else:
            seen[slug] = i

    return errors


def _gmail_plus_alias(gmail_address: str, slug: str) -> str:
    local, _, domain = gmail_address.partition('@')
    return f'{local}+{slug}@{domain}'


def build_inboxes(form_data: dict, gmail_address: str, site_base_url: str, hosting_provider: str = '') -> dict:
    """Return inboxes list dict with address, site_url, site_base derived from slug."""
    base = site_base_url.rstrip('/') if site_base_url else ''
    inboxes = []
    for inbox in form_data.get('inboxes', []):
        slug = inbox['slug'].strip()
        inboxes.append({
            'slug': slug,
            'address': _gmail_plus_alias(gmail_address.strip(), slug),
            'site_name': inbox['site_name'].strip(),
            'site_url': f'{base}/{slug}' if base else '',
            'site_base': f'/{slug}/',
            'hosting_provider': hosting_provider,
            'allowed_senders': [],
        })
    return {'inboxes': inboxes}


_PROVIDER_SECTION_KEYS = {
    'siteground': 'siteground',
    'ssh_sftp': 'ssh_sftp',
    'vercel': 'vercel',
}


def _provider_section_key(provider: str) -> str | None:
    return _PROVIDER_SECTION_KEYS.get((provider or '').strip())


def _normalized_runtime_value(state: dict, key: str):
    value = state.get(key)
    if value is None or value == '':
        return RUNTIME_DEFAULTS[key]
    return value


def _provider_section_from_state(wizard_state: dict) -> tuple[str | None, dict | None]:
    provider = (wizard_state.get('hosting_provider') or '').strip()
    section_key = _provider_section_key(provider)
    if not section_key:
        return None, None

    section = wizard_state.get(section_key)
    if isinstance(section, dict):
        return section_key, dict(section)

    built = build_hosting(wizard_state)
    section = built.get(section_key)
    if isinstance(section, dict):
        return section_key, dict(section)
    return section_key, None


def _normalize_inboxes_for_output(wizard_state: dict) -> list[dict]:
    inboxes = wizard_state.get('inboxes') or []
    if not inboxes:
        return []

    first = inboxes[0] if isinstance(inboxes[0], dict) else {}
    if first.get('address') and first.get('site_url') and first.get('site_base'):
        return [dict(inbox) for inbox in inboxes]

    built = build_inboxes(
        {'inboxes': inboxes},
        wizard_state.get('gmail_address', '').strip(),
        wizard_state.get('site_base_url', '').strip(),
        wizard_state.get('hosting_provider', ''),
    )
    return built['inboxes']


def _apply_secret_policy(wizard_state: dict, config: dict, *, persist: bool) -> None:
    """Replace plaintext secrets in the config with keychain sentinels.

    When `persist=True`, non-empty plaintext values are written to the OS
    keychain before being replaced. When `persist=False` (preview), nothing
    is written but the emitted YAML still shows sentinels so plaintext never
    leaks into previews or on-disk files without the user hitting the
    commit button.

    A blank field means "keep whatever's already in the keychain" when a
    stored secret exists — letting users re-run the wizard without
    retyping credentials that haven't changed.
    """
    for state_key, section_key, field_name, account in _KEYCHAIN_SECRETS:
        section = config.get(section_key)
        if not isinstance(section, dict) or field_name not in section:
            continue
        section_value = section.get(field_name) or ''
        if keychain_secrets.is_sentinel(section_value):
            continue
        submitted = section_value if section_value else (wizard_state.get(state_key) or '')
        if submitted:
            if persist:
                keychain_secrets.set(account, submitted)
            section[field_name] = keychain_secrets.sentinel(account)
        elif keychain_secrets.has(account):
            section[field_name] = keychain_secrets.sentinel(account)
        else:
            section[field_name] = ''


def build_final_outputs(wizard_state: dict, *, persist_secrets: bool = False) -> tuple[str, str]:
    """Return the authoritative final .env and apps/workflow_engine/config.yaml content.

    Pass `persist_secrets=True` only at the `/write-config` commit point; the
    preview renderer calls this with `persist_secrets=False` so viewing the
    preview does not side-effect the OS keychain.
    """
    env_str = f"GMAIL_APP_PASSWORD={wizard_state.get('gmail_app_password', '').strip()}\n"
    config = {
        'git_branch': _normalized_runtime_value(wizard_state, 'git_branch'),
        'git_push': _normalized_runtime_value(wizard_state, 'git_push'),
        'dry_run': _normalized_runtime_value(wizard_state, 'dry_run'),
    }
    config.update(_build_base_config(wizard_state))

    section_key, section = _provider_section_from_state(wizard_state)
    if section_key and section is not None:
        config[section_key] = section

    _apply_secret_policy(wizard_state, config, persist=persist_secrets)

    config['inboxes'] = _normalize_inboxes_for_output(wizard_state)
    yaml_str = yaml.dump(config, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return env_str, yaml_str


def _mask_secret(value: object) -> str:
    if value is None:
        return ''
    text = str(value)
    if not text:
        return ''
    if len(text) <= 4:
        return '*' * len(text)
    return f"{'*' * (len(text) - 4)}{text[-4:]}"


def mask_for_preview(env_str: str, yaml_str: str) -> tuple[str, str]:
    """Return masked preview strings without mutating the final outputs."""
    env_lines = []
    for line in env_str.splitlines():
        if '=' not in line:
            env_lines.append(line)
            continue
        key, value = line.split('=', 1)
        if key == 'GMAIL_APP_PASSWORD':
            env_lines.append(f'{key}={_mask_secret(value)}')
        else:
            env_lines.append(line)
    env_preview = '\n'.join(env_lines)
    if env_str.endswith('\n'):
        env_preview += '\n'

    config = yaml.safe_load(yaml_str) or {}
    for section_key, field_names in {
        'siteground': ('password', 'key_passphrase'),
        'ssh_sftp': ('password',),
        'vercel': ('api_token',),
    }.items():
        section = config.get(section_key)
        if not isinstance(section, dict):
            continue
        for field_name in field_names:
            value = section.get(field_name)
            if value:
                section[field_name] = _mask_secret(value)

    yaml_preview = yaml.dump(config, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return env_preview, yaml_preview


def _derive_site_base_url(inboxes: list[dict]) -> str:
    candidates = []
    for inbox in inboxes or []:
        if not isinstance(inbox, dict):
            return ''
        slug = (inbox.get('slug') or '').strip()
        site_url = (inbox.get('site_url') or '').strip().rstrip('/')
        if not slug or not site_url:
            return ''

        parsed = urllib.parse.urlsplit(site_url)
        if not parsed.scheme or not parsed.netloc:
            return ''

        slug_suffix = f'/{slug}'
        if parsed.path == slug_suffix:
            base_path = ''
        elif parsed.path.endswith(slug_suffix):
            base_path = parsed.path[:-len(slug_suffix)].rstrip('/')
        else:
            return ''

        candidates.append(urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, base_path, '', '')).rstrip('/'))

    if not candidates:
        return ''
    first = candidates[0]
    return first if all(candidate == first for candidate in candidates[1:]) else ''


def hydrate_wizard_state(env_values: dict, config_values: dict) -> dict:
    """Normalize parsed .env and apps/workflow_engine/config.yaml data into wizard-state shape."""
    config = config_values or {}
    imap = config.get('imap') or {}
    smtp = config.get('smtp') or {}
    lm_studio = config.get('lm_studio') or {}
    inboxes = config.get('inboxes') or []

    provider = ''
    provider_section = {}
    for candidate in _PROVIDER_SECTION_KEYS:
        section = config.get(candidate)
        if isinstance(section, dict):
            provider = candidate
            provider_section = section
            break

    site_base_url = config.get('site_base_url') or _derive_site_base_url(inboxes)

    state = {
        'gmail_address': (imap.get('user') or smtp.get('user') or '').strip(),
        'gmail_app_password': (env_values or {}).get('GMAIL_APP_PASSWORD', ''),
        'gmail_folder': imap.get('folder', DEFAULTS['gmail_folder']),
        'allowed_senders': list(config.get('global_allowed_senders') or []),
        'lms_base_url': lm_studio.get('base_url', DEFAULTS['lms_base_url']),
        'lms_model': lm_studio.get('model', DEFAULTS['lms_model']),
        'lms_temperature': lm_studio.get('temperature', DEFAULTS['lms_temperature']),
        'lms_max_tokens': lm_studio.get('max_tokens', DEFAULTS['lms_max_tokens']),
        'lms_cli_path': lm_studio.get('lms_cli_path', DEFAULTS['lms_cli_path']),
        'autostart': lm_studio.get('autostart', DEFAULTS['autostart']),
        'request_timeout_s': lm_studio.get('request_timeout_s', DEFAULTS['request_timeout_s']),
        'hosting_provider': provider,
        'site_base_url': site_base_url,
        'inboxes': [
            {
                'slug': (inbox.get('slug') or '').strip(),
                'site_name': (inbox.get('site_name') or '').strip(),
            }
            for inbox in inboxes
            if isinstance(inbox, dict)
        ],
        'git_branch': config.get('git_branch', RUNTIME_DEFAULTS['git_branch']),
        'git_push': config.get('git_push', RUNTIME_DEFAULTS['git_push']),
        'dry_run': config.get('dry_run', RUNTIME_DEFAULTS['dry_run']),
    }

    def _secret_from_section(raw_value: object) -> tuple[str, bool]:
        """Return (plaintext_for_state, is_stored_in_keychain).

        Sentinel values never leak into wizard_state — the input field stays
        blank and a `_stored` flag signals the UI to show "saved" indicator.
        """
        if keychain_secrets.is_sentinel(raw_value):
            return '', True
        return (raw_value or ''), False

    if provider == 'siteground':
        passphrase_val, passphrase_stored = _secret_from_section(
            provider_section.get('key_passphrase', ''))
        password_val, password_stored = _secret_from_section(
            provider_section.get('password', ''))
        state.update({
            'sg-host': provider_section.get('host', ''),
            'sg-port': provider_section.get('port', 18765),
            'sg-username': provider_section.get('user', ''),
            # SiteGround key is pasted, never prefilled back into the textarea.
            # existing_key_path lets validation know a key is already configured.
            'sg-ssh_private_key': '',
            'sg-existing_key_path': provider_section.get('key_path', ''),
            'sg-password': password_val,
            'sg-password_stored': password_stored,
            'sg-key_passphrase': passphrase_val,
            'sg-key_passphrase_stored': passphrase_stored,
            'sg-remote_base_path': provider_section.get('base_remote_path', ''),
        })
    elif provider == 'ssh_sftp':
        ssh_password_val, ssh_password_stored = _secret_from_section(
            provider_section.get('password', ''))
        state.update({
            'ssh-host': provider_section.get('host', ''),
            'ssh-port': provider_section.get('port', 22),
            'ssh-username': provider_section.get('user', ''),
            'ssh-ssh_key_path': provider_section.get('key_path', ''),
            'ssh-password': ssh_password_val,
            'ssh-password_stored': ssh_password_stored,
            'ssh-remote_base_path': provider_section.get('base_remote_path', ''),
        })
    elif provider == 'vercel':
        vercel_token_val, vercel_token_stored = _secret_from_section(
            provider_section.get('api_token', ''))
        state.update({
            'vercel_api_token': vercel_token_val,
            'vercel_api_token_stored': vercel_token_stored,
            'vercel_project_id': provider_section.get('project_id', ''),
        })

    return state
