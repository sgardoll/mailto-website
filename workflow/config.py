"""Config loader. Reads workflow/config.yaml; falls back to env-only."""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_DIR = REPO_ROOT / "workflow"
SITES_DIR = REPO_ROOT / "sites"
TEMPLATE_DIR = REPO_ROOT / "framework" / "site-template"
STATE_DIR = WORKFLOW_DIR / "state"


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
    # If set, the workflow will try to start LM Studio + load the model
    # before its first call by shelling out to `lms`.
    lms_cli_path: str = "lms"
    autostart: bool = True
    # Per-call generation knobs.
    temperature: float = 0.4
    max_tokens: int = 4096
    request_timeout_s: int = 600


@dataclass
class SiteGroundConfig:
    """Default SFTP target. Per-inbox overrides allowed."""
    host: str = ""
    port: int = 22
    user: str = ""
    # Path to private key on disk. Password is also accepted but discouraged.
    key_path: str = ""
    password: str = ""
    # Base remote path; per inbox, deploy goes to {base_remote_path}/{slug}/
    base_remote_path: str = "/home/USER/public_html"


@dataclass
class InboxConfig:
    """One inbox = one self-extending site."""
    slug: str  # filesystem-safe, used as sites/<slug>/ and remote subpath
    address: str  # the To: address that routes mail to this inbox
    site_name: str = ""  # human-readable site title (model may evolve it)
    site_url: str = ""  # public URL for the deployed site
    site_base: str = "/"  # Astro base path
    remote_path: str = ""  # if set, overrides {SiteGround.base_remote_path}/{slug}
    allowed_senders: list[str] = field(default_factory=list)


@dataclass
class Config:
    imap: ImapConfig
    smtp: SmtpConfig
    lm_studio: LmStudioConfig
    siteground: SiteGroundConfig
    inboxes: list[InboxConfig]
    # Global allowlist (applied in addition to per-inbox allowlists; if both empty, mail is rejected).
    global_allowed_senders: list[str] = field(default_factory=list)
    repo_root: Path = REPO_ROOT
    sites_dir: Path = SITES_DIR
    template_dir: Path = TEMPLATE_DIR
    state_dir: Path = STATE_DIR
    git_branch: str = "main"
    git_push: bool = True
    dry_run: bool = False

    def find_inbox(self, address: str) -> InboxConfig | None:
        addr = address.strip().lower()
        for ib in self.inboxes:
            if ib.address.lower() == addr:
                return ib
        return None

    def remote_path_for(self, inbox: InboxConfig) -> str:
        if inbox.remote_path:
            return inbox.remote_path
        base = self.siteground.base_remote_path.rstrip("/")
        return f"{base}/{inbox.slug}"


def _expand(value: Any) -> Any:
    if isinstance(value, str):
        return os.path.expandvars(value)
    if isinstance(value, dict):
        return {k: _expand(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand(v) for v in value]
    return value


def load(path: Path | None = None) -> Config:
    config_path = path or (WORKFLOW_DIR / "config.yaml")
    if not config_path.exists():
        raise FileNotFoundError(
            f"No config at {config_path}. Copy workflow/config.example.yaml "
            f"to workflow/config.yaml and fill it in."
        )
    raw = yaml.safe_load(config_path.read_text()) or {}
    raw = _expand(raw)

    imap = ImapConfig(**raw["imap"])
    smtp = SmtpConfig(**raw["smtp"])
    lm = LmStudioConfig(**(raw.get("lm_studio") or {}))
    sg = SiteGroundConfig(**(raw.get("siteground") or {}))
    inboxes = [InboxConfig(**ib) for ib in raw.get("inboxes", [])]
    if not inboxes:
        raise ValueError("config.yaml must define at least one inbox.")

    return Config(
        imap=imap,
        smtp=smtp,
        lm_studio=lm,
        siteground=sg,
        inboxes=inboxes,
        global_allowed_senders=raw.get("global_allowed_senders", []),
        git_branch=raw.get("git_branch", "main"),
        git_push=bool(raw.get("git_push", True)),
        dry_run=bool(raw.get("dry_run", False)),
    )
