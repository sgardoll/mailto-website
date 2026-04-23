"""OS keychain storage for wizard-managed secrets.

Secrets live in the OS credential store (macOS Keychain, Windows Credential
Manager, Linux Secret Service) under a single service name. YAML config files
reference secrets via a `keychain://<account>` sentinel that is resolved at
load time by `packages.config_contract._expand`.
"""
from __future__ import annotations

import keyring

SERVICE = "mailto.website"
SENTINEL_PREFIX = "keychain://"

# Stable account identifiers for each secret the wizard manages.
ACCOUNT_SITEGROUND_KEY_PASSPHRASE = "siteground:key_passphrase"
ACCOUNT_SITEGROUND_PASSWORD = "siteground:password"
ACCOUNT_SSH_SFTP_PASSWORD = "ssh_sftp:password"
ACCOUNT_VERCEL_API_TOKEN = "vercel:api_token"

SECRET_ACCOUNTS = (
    ACCOUNT_SITEGROUND_KEY_PASSPHRASE,
    ACCOUNT_SITEGROUND_PASSWORD,
    ACCOUNT_SSH_SFTP_PASSWORD,
    ACCOUNT_VERCEL_API_TOKEN,
)


def get(account: str) -> str | None:
    return keyring.get_password(SERVICE, account)


def set(account: str, value: str) -> None:
    keyring.set_password(SERVICE, account, value)


def delete(account: str) -> None:
    try:
        keyring.delete_password(SERVICE, account)
    except keyring.errors.PasswordDeleteError:
        pass


def has(account: str) -> bool:
    return get(account) is not None


def sentinel(account: str) -> str:
    return f"{SENTINEL_PREFIX}{account}"


def is_sentinel(value: object) -> bool:
    return isinstance(value, str) and value.startswith(SENTINEL_PREFIX)


def resolve(value: str) -> str:
    """Resolve a keychain sentinel to its stored value.

    Non-sentinel strings are returned unchanged. Missing entries resolve to
    the empty string so downstream code treats them the same as an unset
    secret.
    """
    if not is_sentinel(value):
        return value
    account = value[len(SENTINEL_PREFIX):]
    return get(account) or ""
