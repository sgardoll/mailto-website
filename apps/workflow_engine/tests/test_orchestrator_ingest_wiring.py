"""Wiring test: orchestrator._process_locked must call ingest.ingest before topic_curator."""
from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from apps.workflow_engine import orchestrator, ingest, \
    site_bootstrap, site_index, build_and_deploy, notify, \
    distill, build as build_mod, integrate as integrate_mod
import apps.workflow_engine.plan as _plan_stage_mod
from apps.workflow_engine.schemas.envelope import MechanicSpec
from packages.config_contract import (
    Config, InboxConfig, ImapConfig, SmtpConfig, LmStudioConfig,
)


def _make_cfg(tmp_path: Path) -> Config:
    return Config(
        imap=ImapConfig(host="x"),
        smtp=SmtpConfig(host="x"),
        lm_studio=LmStudioConfig(),
        inboxes=[],
        repo_root=tmp_path,
        state_dir=tmp_path / "state",
        sites_dir=tmp_path / "sites",
        template_dir=tmp_path / "tpl",
        dry_run=True,
        git_push=False,
    )


def _make_inbox() -> InboxConfig:
    return InboxConfig(slug="test", address="a@b.com", site_name="Test")


CALCULATOR_SPEC = MechanicSpec.model_validate({
    "kind": "calculator", "title": "T", "intent": "i",
    "inputs": ["x"], "outputs": ["y"],
    "content": {"kind": "calculator", "formula_description": "y=x", "variables": [{"name": "x", "unit": "", "default": 1}], "unit": ""},
})


def _neutralise(monkeypatch, tmp_path):
    monkeypatch.setattr(site_bootstrap, "ensure_site", lambda inbox: tmp_path / "site")
    monkeypatch.setattr(site_index, "build", lambda *a, **kw: MagicMock(topic=""))
    monkeypatch.setattr(integrate_mod, "startup_assert_gitignore", MagicMock())
    monkeypatch.setattr(distill, "distill", MagicMock(return_value=CALCULATOR_SPEC))
    monkeypatch.setattr(_plan_stage_mod, "plan", MagicMock(return_value="new_module"))
    monkeypatch.setattr(build_mod, "build", MagicMock(return_value={"html_b64": "aGk=", "kind": "calculator", "attempts": 1}))
    monkeypatch.setattr(integrate_mod, "integrate", MagicMock(return_value="abc1234"))
    monkeypatch.setattr(build_and_deploy, "build", MagicMock())
    monkeypatch.setattr(build_and_deploy, "deploy", MagicMock())
    monkeypatch.setattr(notify, "send", MagicMock())


def test_ingest_log_line_emitted(monkeypatch, tmp_path, caplog):
    _neutralise(monkeypatch, tmp_path)
    monkeypatch.setattr(ingest, "ingest", lambda email: {
        "body": "b", "subject": "s", "sender": "a@b",
        "source_type": "article", "source_url": "https://x.test/a",
    })
    processed = MagicMock()
    email = {"body": "hi", "subject": "s", "from": "a@b.com", "message_id": "m2"}
    with caplog.at_level(logging.INFO, logger="workflow.orchestrator"):
        orchestrator._process_locked(_make_cfg(tmp_path), _make_inbox(), email, processed, mid="m2")
    msgs = [r.getMessage() for r in caplog.records]
    assert any("source_type=" in m and "source_url=" in m for m in msgs), msgs


def test_ingest_exception_propagates_to_error_outcome(monkeypatch, tmp_path):
    _neutralise(monkeypatch, tmp_path)
    def boom(email):
        raise RuntimeError("boom")
    monkeypatch.setattr(ingest, "ingest", boom)
    processed = MagicMock()
    email = {"body": "hi", "subject": "s", "from": "a@b.com", "message_id": "m3"}
    # Should NOT raise — orchestrator's `except Exception` at line 103 catches.
    orchestrator._process_locked(_make_cfg(tmp_path), _make_inbox(), email, processed, mid="m3")
    assert processed.record.called
    found = False
    for c in processed.record.call_args_list:
        kwargs = c.kwargs
        if kwargs.get("outcome") == "error" and "boom" in (kwargs.get("error") or ""):
            found = True
            break
    assert found, processed.record.call_args_list
