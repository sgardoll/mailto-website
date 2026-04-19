"""Typed config contract shared between setup wizard and workflow engine.

This module defines the canonical schema for apps/workflow_engine/config.yaml.
Both apps/setup_wizard and apps/workflow_engine import from here —
never duplicate validation logic.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


# ── Provider Enum ─────────────────────────────────────────────────────────────

class DeployProvider(str, Enum):
    """Canonical provider identifiers.

    Use these exact string values in config.yaml:
        hosting_provider: siteground
        hosting_provider: ssh_sftp
        hosting_provider: netlify
        hosting_provider: vercel
        hosting_provider: github_pages
    """
    SITEGROUND = "siteground"
    SSH_SFTP = "ssh_sftp"
    NETLIFY = "netlify"
    VERCEL = "vercel"
    GITHUB_PAGES = "github_pages"

    @property
    def is_ssh(self) -> bool:
        return self in (DeployProvider.SITEGROUND, DeployProvider.SSH_SFTP)

    @classmethod
    def from_string(cls, value: str) -> "DeployProvider":
        """Parse provider string, raising ValueError on unknown values."""
        try:
            return cls(value)
        except ValueError:
            raise ValueError(
                f"Unknown hosting provider: {value!r}. "
                f"Valid providers: {[p.value for p in cls]}"
            )


# ── Legacy alias for backward compatibility ───────────────────────────────────
_PROVIDER_ALIASES = {
    "generic_ssh": "ssh_sftp",
}


def normalize_provider(value: str) -> str:
    """Normalize a provider string, resolving legacy aliases."""
    resolved = _PROVIDER_ALIASES.get(value, value)
    DeployProvider.from_string(resolved)  # validates
    return resolved


# ── Config Dataclasses ────────────────────────────────────────────────────────

@dataclass
class ImapConfig:
    host: str
    port: int = 993
    user: str = ""
    password: str = ""
    folder: str = "INBOX"
    use_ssl: bool = True


@dataclass
class SmtpConfig:
    host: str
    port: int = 587
    user: str = ""
    password: str = ""
    from_address: str = ""
    use_starttls: bool = True


@dataclass
class LmStudioConfig:
    base_url: str = "http://localhost:1234/v1"
    api_key: str = "lm-studio"
    model: str = "google/gemma-4-26b-a4b"
    lms_cli_path: str = "lms"
    autostart: bool = True
    temperature: float = 0.4
    max_tokens: int = 4096
    request_timeout_s: int = 600


@dataclass
class SiteGroundConfig:
    """SiteGround SFTP deploy target."""
    host: str = ""
    port: int = 22
    user: str = ""
    key_path: str = ""
    key_passphrase: str = ""
    password: str = ""
    base_remote_path: str = "/home/USER/public_html"


@dataclass
class SshSftpConfig:
    """Generic SSH/SFTP deploy target."""
    host: str = ""
    port: int = 22
    user: str = ""
    key_path: str = ""
    key_passphrase: str = ""
    password: str = ""
    remote_path: str = ""


@dataclass
class NetlifyConfig:
    """Netlify deploy target."""
    api_token: str = ""
    site_id: str = ""


@dataclass
class VercelConfig:
    """Vercel deploy target."""
    api_token: str = ""
    project_id: str = ""
    team_id: str = ""


@dataclass
class GitHubPagesConfig:
    """GitHub Pages deploy target."""
    repo_url: str = ""
    branch: str = "gh-pages"


@dataclass
class InboxConfig:
    """One inbox = one self-extending site."""
    slug: str
    address: str
    site_name: str = ""
    site_url: str = ""
    site_base: str = "/"
    remote_path: str = ""
    hosting_provider: str = ""
    allowed_senders: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.slug:
            raise ValueError("inbox slug is required")
        if not self.address:
            raise ValueError("inbox address is required")


@dataclass
class Config:
    """Top-level config. Mirrors apps/workflow_engine/config.yaml structure."""
    imap: ImapConfig
    smtp: SmtpConfig
    lm_studio: LmStudioConfig
    siteground: SiteGroundConfig = field(default_factory=SiteGroundConfig)
    ssh_sftp: SshSftpConfig = field(default_factory=SshSftpConfig)
    netlify: NetlifyConfig = field(default_factory=NetlifyConfig)
    vercel: VercelConfig = field(default_factory=VercelConfig)
    github_pages: GitHubPagesConfig = field(default_factory=GitHubPagesConfig)
    inboxes: list[InboxConfig] = field(default_factory=list)
    global_allowed_senders: list[str] = field(default_factory=list)
    git_branch: str = "main"
    git_push: bool = True
    dry_run: bool = False
    repo_root: Path = Path(".")
    sites_dir: Path = Path("runtime/sites")
    template_dir: Path = Path("packages/site-template")
    state_dir: Path = Path("runtime/state")
    repo_root: Path = Path(".")
    sites_dir: Path = Path("runtime/sites")
    template_dir: Path = Path("packages/site-template")
    state_dir: Path = Path("runtime/state")

    def find_inbox(self, address: str) -> InboxConfig | None:
        addr = address.strip().lower()
        for ib in self.inboxes:
            if ib.address.lower() == addr:
                return ib
        return None

    def remote_path_for(self, inbox: InboxConfig) -> str:
        if inbox.remote_path:
            return inbox.remote_path
        provider = inbox.hosting_provider or DeployProvider.SITEGROUND.value
        if provider == DeployProvider.SITEGROUND.value:
            base = self.siteground.base_remote_path.rstrip("/")
            return f"{base}/{inbox.slug}"
        return f"/{inbox.slug}"


# ── Validation ────────────────────────────────────────────────────────────────

def validate_config(raw: dict) -> list[str]:
    """Return list of error strings. Empty means valid."""
    errors = []

    if "imap" not in raw:
        errors.append("Missing 'imap' section")
    if "smtp" not in raw:
        errors.append("Missing 'smtp' section")
    if "lm_studio" not in raw:
        errors.append("Missing 'lm_studio' section")

    inboxes = raw.get("inboxes", [])
    if not inboxes:
        errors.append("At least one inbox is required")
    else:
        slugs = set()
        for i, ib in enumerate(inboxes):
            if not ib.get("slug"):
                errors.append(f"Inbox {i}: missing 'slug'")
            if not ib.get("address"):
                errors.append(f"Inbox {i}: missing 'address'")
            slug = ib.get("slug", "")
            if slug in slugs:
                errors.append(f"Inbox {i}: duplicate slug '{slug}'")
            slugs.add(slug)

            provider = ib.get("hosting_provider", "")
            if provider:
                try:
                    normalize_provider(provider)
                except ValueError as e:
                    errors.append(f"Inbox '{slug}': {e}")

    return errors


# ── Loader ────────────────────────────────────────────────────────────────────

def _expand(value: Any) -> Any:
    """Expand environment variables in string values."""
    if isinstance(value, str):
        return os.path.expandvars(value)
    if isinstance(value, dict):
        return {k: _expand(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand(v) for v in value]
    return value


def _normalize_raw(raw: dict) -> dict:
    """Apply legacy aliases and defaults to raw config dict."""
    for inbox in raw.get("inboxes", []):
        provider = inbox.get("hosting_provider", "")
        if provider:
            inbox["hosting_provider"] = normalize_provider(provider)

    if "generic_ssh" in raw:
        raw["ssh_sftp"] = raw.pop("generic_ssh")

    return raw


def load_config(raw: dict) -> Config:
    """Parse a raw dict (from YAML) into a validated Config."""
    raw = _expand(raw)
    raw = _normalize_raw(raw)

    errors = validate_config(raw)
    if errors:
        raise ValueError("; ".join(errors))

    return Config(
        imap=ImapConfig(**raw["imap"]),
        smtp=SmtpConfig(**raw["smtp"]),
        lm_studio=LmStudioConfig(**(raw.get("lm_studio") or {})),
        siteground=SiteGroundConfig(**(raw.get("siteground") or {})),
        ssh_sftp=SshSftpConfig(**(raw.get("ssh_sftp") or raw.get("generic_ssh") or {})),
        netlify=NetlifyConfig(**(raw.get("netlify") or {})),
        vercel=VercelConfig(**(raw.get("vercel") or {})),
        github_pages=GitHubPagesConfig(**(raw.get("github_pages") or {})),
        inboxes=[InboxConfig(**ib) for ib in raw.get("inboxes", [])],
        global_allowed_senders=raw.get("global_allowed_senders", []),
        git_branch=raw.get("git_branch", "main"),
        git_push=bool(raw.get("git_push", True)),
        dry_run=bool(raw.get("dry_run", False)),
    )
