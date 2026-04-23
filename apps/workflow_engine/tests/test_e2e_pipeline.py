"""End-to-end pipeline test against a live LM Studio server.

Requires LM Studio running at LM_BASE_URL (default http://localhost:1234).
Skip in CI with: pytest -m 'not requires_lm'

Covers Phase 19 SC1: a single email to a v2 inbox travels through
INGEST -> DISTILL -> PLAN -> BUILD -> INTEGRATE and produces a
committed, validator-passing module that can be rendered by the SPA shell.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from apps.workflow_engine import orchestrator, site_bootstrap


# Environment configuration (D-04 — env vars with defaults)
LM_BASE_URL = os.environ.get("LM_BASE_URL", "http://localhost:1234")
LM_MODEL = os.environ.get("LM_MODEL", "local-model")


def _make_cfg(tmp_path: Path):
    """Build a real Config pointing at a live LM Studio server."""
    from packages.config_contract import (
        Config, ImapConfig, SmtpConfig, LmStudioConfig,
    )
    # LmStudioConfig picks up base_url from env or uses default;
    # tests can override via LM_BASE_URL / LM_MODEL.
    lm_cfg = LmStudioConfig()
    try:
        if hasattr(lm_cfg, "base_url"):
            lm_cfg.base_url = LM_BASE_URL
    except AttributeError:
        pass
    try:
        if hasattr(lm_cfg, "model"):
            lm_cfg.model = LM_MODEL
    except AttributeError:
        pass

    cfg = Config(
        imap=ImapConfig(host="x"),
        smtp=SmtpConfig(host=""),  # empty host disables notify
        lm_studio=lm_cfg,
        inboxes=[],
        repo_root=tmp_path,
        state_dir=tmp_path / "state",
        sites_dir=tmp_path / "sites",
        template_dir=tmp_path / "tpl",
        dry_run=False,
        git_push=False,
    )
    (tmp_path / "state" / "locks").mkdir(parents=True, exist_ok=True)
    return cfg


def _make_inbox():
    from packages.config_contract import InboxConfig
    return InboxConfig(
        slug="e2e_test",
        address="e2e@example.com",
        site_name="E2E Test Site",
        pipeline_version="v2",
    )


def _seed_site_dir(tmp_path: Path) -> Path:
    """Create a tmp site dir with a seeded empty manifest (D-04)."""
    site_dir = tmp_path / "site"
    spa_dir = site_dir / "public" / "spa"
    spa_dir.mkdir(parents=True, exist_ok=True)
    (spa_dir / "spa_manifest.json").write_text(
        json.dumps({"schema_version": "1", "modules": []})
    )
    return site_dir


@pytest.mark.requires_lm
def test_full_v2_pipeline_against_real_lm(tmp_path, monkeypatch):
    """SC1: real email -> INGEST -> DISTILL -> PLAN -> BUILD -> INTEGRATE.

    Requires LM Studio running at LM_BASE_URL. Skip in CI with
    `pytest -m 'not requires_lm'`.

    Assertion (D-05): module file exists at public/spa/<module_id>/index.html
    AND spa_manifest.json contains that module entry.
    """
    # Redirect site_bootstrap.ensure_site to our tmp site dir so we don't
    # touch the real sites directory.
    site_dir = _seed_site_dir(tmp_path)
    monkeypatch.setattr(site_bootstrap, "ensure_site", lambda inbox: site_dir)

    # Concrete email with enough substance for DISTILL to produce a real spec.
    email = {
        "body": (
            "I want a BMI calculator. Enter weight in kg and height in metres, "
            "then compute BMI = weight / height^2 and display the result."
        ),
        "subject": "BMI calculator please",
        "from": "e2e@example.com",
        "message_id": "e2e-test-msg-1",
    }

    cfg = _make_cfg(tmp_path)
    inbox = _make_inbox()
    processed = MagicMock()

    # Run the pipeline end-to-end.
    orchestrator._process_locked(cfg, inbox, email, processed, "e2e-test-msg-1")

    # D-05 assertions: module dir exists with index.html, manifest lists it.
    manifest_path = site_dir / "public" / "spa" / "spa_manifest.json"
    assert manifest_path.exists(), "spa_manifest.json must exist after pipeline run"

    manifest = json.loads(manifest_path.read_text())
    modules = manifest.get("modules", [])
    assert len(modules) >= 1, (
        f"manifest should contain at least one module after a successful "
        f"pipeline run; got {modules!r}"
    )

    # Take the first module (the one just integrated) and verify its file.
    module_id = modules[0]["module_id"]
    module_file = site_dir / "public" / "spa" / module_id / "index.html"
    assert module_file.exists(), (
        f"module file must exist at {module_file}; "
        f"manifest referenced module_id={module_id!r}"
    )

    # Sanity: version field is a 7-char hex short SHA (INT-03).
    version = modules[0]["version"]
    assert len(version) == 7, f"version should be 7-char short SHA, got {version!r}"

    # Sanity: processed.record was called with an 'ok' outcome.
    ok_calls = [
        c for c in processed.record.call_args_list
        if c.kwargs.get("outcome") == "ok"
    ]
    assert ok_calls, f"no 'ok' outcome recorded; calls={processed.record.call_args_list}"
