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
        hosting_provider: vercel

    Netlify and GitHub Pages were dropped — they're static-only hosts
    that cannot run the IMAP listener, and the local-listener-pushing-
    to-static-host model adds no value over Vercel for static sites.
    """
    SITEGROUND = "siteground"
    SSH_SFTP = "ssh_sftp"
    VERCEL = "vercel"

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


# ── Mechanic Enum ─────────────────────────────────────────────────────────────

class MechanicKind(str, Enum):
    """Canonical mechanic kinds for v2.0 pipeline.

    Defined once here. DISTILL, BUILD, and validator import from this module.
    Never redefine locally. v2.0 is capped at 5 kinds; comparator/matcher deferred.
    """
    CALCULATOR = "calculator"
    WIZARD     = "wizard"
    DRILL      = "drill"
    SCORER     = "scorer"
    GENERATOR  = "generator"


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
    password: str = field(default="", repr=False)
    folder: str = "INBOX"
    use_ssl: bool = True


@dataclass
class SmtpConfig:
    host: str
    port: int = 587
    user: str = ""
    password: str = field(default="", repr=False)
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
    # Optional sampling knobs. Passed through to the OpenAI-compatible server
    # when set; omitted otherwise so the server keeps its default.
    top_p: float | None = None
    top_k: int | None = None
    min_p: float | None = None
    presence_penalty: float | None = None
    repetition_penalty: float | None = None
    # Qwen3.6 / Gemma 4 thinking-mode toggle. Sent as
    # extra_body.chat_template_kwargs.enable_thinking. None = server default.
    enable_thinking: bool | None = None
    # Model-load parameters passed to `lms load`. None = LM Studio default,
    # which on a Mac with a 26B+ model and a 32k–256k default window can
    # exhaust unified memory and freeze the system. Always pin these.
    context_length: int | None = None       # `-c` / KV-cache token budget
    gpu_offload: str | None = None          # `--gpu` ("max", "off", or 0..1)
    ttl_seconds: int | None = None          # `--ttl` auto-unload idle timeout
    # Refuse to load if `lms load --estimate-only` reports the model won't fit
    # under LM Studio's resource guardrails. Default on — this is the safety
    # net that prevents another freeze/reboot.
    estimate_before_load: bool = True
    # Per-task sampling overrides. Key = task name (e.g. "topic_curation",
    # "synthesis", "build", "distill", "plan"). Value = dict with any subset of
    # the sampling fields above (including enable_thinking). Shallow-merged
    # over the base config for that call only.
    task_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class SiteGroundConfig:
    """SiteGround SFTP deploy target."""
    host: str = ""
    port: int = 22
    user: str = ""
    key_path: str = ""
    key_passphrase: str = field(default="", repr=False)
    password: str = field(default="", repr=False)
    base_remote_path: str = "/home/USER/public_html"


@dataclass
class SshSftpConfig:
    """Generic SSH/SFTP deploy target."""
    host: str = ""
    port: int = 22
    user: str = ""
    key_path: str = ""
    key_passphrase: str = field(default="", repr=False)
    password: str = field(default="", repr=False)
    remote_path: str = ""


@dataclass
class VercelConfig:
    """Vercel deploy target."""
    api_token: str = field(default="", repr=False)
    project_id: str = ""
    team_id: str = ""


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
    vercel: VercelConfig = field(default_factory=VercelConfig)
    inboxes: list[InboxConfig] = field(default_factory=list)
    global_allowed_senders: list[str] = field(default_factory=list)
    git_branch: str = "main"
    git_push: bool = True
    dry_run: bool = False
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
    """Expand environment variables and keychain sentinels in string values."""
    if isinstance(value, str):
        expanded = os.path.expandvars(value)
        if expanded.startswith("keychain://"):
            # Local import to keep the contract package free of a hard keyring
            # dependency at import time.
            from apps.workflow_engine import secrets as _secrets
            return _secrets.resolve(expanded)
        return expanded
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
        ssh_sftp=SshSftpConfig(**(raw.get("ssh_sftp") or {})),
        vercel=VercelConfig(**(raw.get("vercel") or {})),
        inboxes=[InboxConfig(**ib) for ib in raw.get("inboxes", [])],
        global_allowed_senders=raw.get("global_allowed_senders", []),
        git_branch=raw.get("git_branch", "main"),
        git_push=bool(raw.get("git_push", True)),
        dry_run=bool(raw.get("dry_run", False)),
    )
