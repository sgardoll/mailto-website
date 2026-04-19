"""Config loader for the workflow engine.

Delegates parsing/validation to packages/config_contract.
Adds runtime path resolution (SITES_DIR, TEMPLATE_DIR, STATE_DIR).
"""
from __future__ import annotations

import yaml
from pathlib import Path

# Re-export everything from the contract so existing imports still work.
from packages.config_contract import (
    Config,
    DeployProvider,
    GitHubPagesConfig,
    ImapConfig,
    InboxConfig,
    LmStudioConfig,
    NetlifyConfig,
    SiteGroundConfig,
    SshSftpConfig,
    VercelConfig,
    load_config,
    normalize_provider,
    validate_config,
)

# ── Runtime Path Constants ────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WORKFLOW_DIR = REPO_ROOT / "apps" / "workflow_engine"
SITES_DIR = REPO_ROOT / "runtime" / "sites"
TEMPLATE_DIR = REPO_ROOT / "packages" / "site-template"
STATE_DIR = REPO_ROOT / "runtime" / "state"


def load(path: Path | None = None) -> Config:
    """Load config from YAML file, applying runtime path defaults."""
    config_path = path or (WORKFLOW_DIR / "config.yaml")
    if not config_path.exists():
        raise FileNotFoundError(
            f"No config at {config_path}. Copy apps/workflow_engine/config.example.yaml "
            f"to apps/workflow_engine/config.yaml and fill it in."
        )
    raw = yaml.safe_load(config_path.read_text()) or {}
    cfg = load_config(raw)
    # Inject runtime paths
    cfg.repo_root = REPO_ROOT
    cfg.sites_dir = SITES_DIR  # type: ignore[attr-defined]
    cfg.template_dir = TEMPLATE_DIR  # type: ignore[attr-defined]
    cfg.state_dir = STATE_DIR  # type: ignore[attr-defined]
    return cfg
