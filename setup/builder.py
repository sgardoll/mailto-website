import json
import re
import urllib.error
import urllib.request

import yaml

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


def build(form_data: dict) -> tuple[str, str]:
    """Return (env_str, yaml_str). Assumes validate() returned empty list."""
    email = form_data['gmail_address'].strip()
    config = {
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
    env_str = f"GMAIL_APP_PASSWORD={form_data['gmail_app_password'].strip()}\n"
    yaml_str = yaml.dump(config, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return env_str, yaml_str


_VALID_PROVIDERS = {'siteground', 'ssh_sftp', 'netlify', 'vercel', 'github_pages'}
_SSH_PROVIDERS = {'siteground', 'ssh_sftp'}
_SSH_PREFIX = {'siteground': 'sg-', 'ssh_sftp': 'ssh-'}
_API_PROVIDERS = {'netlify', 'vercel'}
_URL_RE = re.compile(r'^https?://', re.IGNORECASE)


def _needs_manual_site_base_url(provider: str) -> bool:
    return provider in _SSH_PROVIDERS or provider == 'github_pages'


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
        key_path = form_data.get(f'{prefix}ssh_key_path', '').strip()
        password = form_data.get(f'{prefix}password', '').strip()
        if not key_path and not password:
            errors.append({'field': f'{prefix}ssh_key_path',
                           'message': 'Enter an SSH key path or a password — at least one is required'})
        remote_base_path = form_data.get(f'{prefix}remote_base_path', '').strip()
        if not remote_base_path:
            errors.append({'field': f'{prefix}remote_base_path', 'message': 'Remote base path is required'})

    elif provider == 'netlify':
        if not form_data.get('netlify_api_token', '').strip():
            errors.append({'field': 'netlify_api_token', 'message': 'API token is required'})
        if not form_data.get('netlify_site_id', '').strip():
            errors.append({'field': 'netlify_site_id', 'message': 'Site ID is required'})

    elif provider == 'vercel':
        if not form_data.get('vercel_api_token', '').strip():
            errors.append({'field': 'vercel_api_token', 'message': 'API token is required'})
        if not form_data.get('vercel_project_id', '').strip():
            errors.append({'field': 'vercel_project_id', 'message': 'Project name or ID is required'})

    elif provider == 'github_pages':
        if not form_data.get('gh_pages_branch', '').strip():
            errors.append({'field': 'gh_pages_branch', 'message': 'Target branch is required'})

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
        result[section_key] = {
            'host': form_data.get(f'{prefix}host', '').strip(),
            'port': int(form_data.get(f'{prefix}port', 22)),
            'user': form_data.get(f'{prefix}username', '').strip(),
            'key_path': form_data.get(f'{prefix}ssh_key_path', '').strip(),
            'password': form_data.get(f'{prefix}password', '').strip(),
            'base_remote_path': form_data.get(f'{prefix}remote_base_path', '').strip(),
        }
    elif provider == 'netlify':
        result['netlify'] = {
            'api_token': form_data.get('netlify_api_token', '').strip(),
            'site_id': form_data.get('netlify_site_id', '').strip(),
        }
    elif provider == 'vercel':
        result['vercel'] = {
            'api_token': form_data.get('vercel_api_token', '').strip(),
            'project_id': form_data.get('vercel_project_id', '').strip(),
        }
    elif provider == 'github_pages':
        result['github_pages'] = {
            'branch': form_data.get('gh_pages_branch', '').strip() or 'gh-pages',
        }

    site_base_url = form_data.get('site_base_url', '').strip()
    if site_base_url:
        result['site_base_url'] = site_base_url.rstrip('/')

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


def fetch_netlify_site_url(api_token: str, site_id: str) -> str:
    """Return the public HTTPS URL for a Netlify site, raising ProviderLookupError on failure."""
    data = _http_get_json(
        f'https://api.netlify.com/api/v1/sites/{site_id}',
        {'Authorization': f'Bearer {api_token}'},
    )
    url = data.get('ssl_url') or data.get('url')
    if not url:
        raise ProviderLookupError('Netlify site has no public URL yet')
    return url.rstrip('/')


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


def build_inboxes(form_data: dict, gmail_address: str, site_base_url: str) -> dict:
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
            'allowed_senders': [],
        })
    return {'inboxes': inboxes}
