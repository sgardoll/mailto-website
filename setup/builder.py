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
