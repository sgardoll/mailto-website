"""Tests for orchestrator v2 wiring + PIPE-02 verification."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from apps.workflow_engine import orchestrator
from apps.workflow_engine.build import BuildFailed
from apps.workflow_engine.integrate import IntegrateFailed
from apps.workflow_engine import (
    distill, ingest, site_bootstrap, site_index,
    build as build_mod, integrate as integrate_mod,
    build_and_deploy, notify,
)
import apps.workflow_engine.plan as _plan_stage_mod
from apps.workflow_engine.schemas.envelope import MechanicSpec


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

CALCULATOR_SPEC = MechanicSpec.model_validate({
    "kind": "calculator",
    "title": "BMI Calculator",
    "intent": "Compute body mass index",
    "inputs": ["weight_kg", "height_m"],
    "outputs": ["bmi"],
    "content": {
        "kind": "calculator",
        "formula_description": "bmi = weight / height^2",
        "variables": [{"name": "weight_kg", "unit": "kg", "default": 70}],
        "unit": "kg/m^2",
    },
})

EMAIL = {"body": "hi", "subject": "s", "from": "a@b.com", "message_id": "m1"}


def _make_cfg(tmp_path: Path):
    from packages.config_contract import (
        Config, ImapConfig, SmtpConfig, LmStudioConfig,
    )
    cfg = Config(
        imap=ImapConfig(host="x"),
        smtp=SmtpConfig(host=""),  # empty host disables notify
        lm_studio=LmStudioConfig(),
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
        slug="test",
        address="a@b.com",
        site_name="Test Site",
    )


def _neutralise(monkeypatch, tmp_path: Path):
    """Stub all I/O so tests exercise wiring only."""
    monkeypatch.setattr(site_bootstrap, "ensure_site", lambda inbox: tmp_path / "site")
    monkeypatch.setattr(site_index, "build", lambda *a, **kw: MagicMock(topic=""))
    monkeypatch.setattr(ingest, "ingest", lambda email: {
        "body": "BMI question",
        "subject": "s",
        "sender": "a@b.com",
        "source_type": "text",
        "source_url": None,
    })
    monkeypatch.setattr(build_and_deploy, "build", MagicMock())
    monkeypatch.setattr(build_and_deploy, "deploy", MagicMock())
    monkeypatch.setattr(notify, "send", MagicMock())
    # stage defaults (happy-path; override per test as needed)
    monkeypatch.setattr(integrate_mod, "startup_assert_gitignore", MagicMock())
    monkeypatch.setattr(distill, "distill", MagicMock(return_value=CALCULATOR_SPEC))
    monkeypatch.setattr(_plan_stage_mod, "plan", MagicMock(return_value="new_module"))
    monkeypatch.setattr(build_mod, "build", MagicMock(
        return_value={"html_b64": "aGk=", "kind": "calculator", "attempts": 1}
    ))
    monkeypatch.setattr(integrate_mod, "integrate", MagicMock(return_value="abc1234"))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_pipe_02_inbox_calls_all_stages(monkeypatch, tmp_path):
    """Pipeline calls distill, plan, build, and integrate in order."""
    _neutralise(monkeypatch, tmp_path)
    call_order: list[str] = []

    def fake_distill(ni, lm_cfg):
        call_order.append("distill")
        return CALCULATOR_SPEC

    def fake_plan(spec, site_dir, lm_cfg):
        call_order.append("plan")
        return "new_module"

    def fake_build(spec, lm_cfg):
        call_order.append("build")
        return {"html_b64": "aGk=", "kind": "calculator", "attempts": 1}

    def fake_integrate(spec, html_b64, site_dir, *, push=False):
        call_order.append("integrate")
        return "abc1234"

    monkeypatch.setattr(distill, "distill", fake_distill)
    monkeypatch.setattr(_plan_stage_mod, "plan", fake_plan)
    monkeypatch.setattr(build_mod, "build", fake_build)
    monkeypatch.setattr(integrate_mod, "integrate", fake_integrate)

    processed = MagicMock()
    orchestrator._process_locked(_make_cfg(tmp_path), _make_inbox(), EMAIL, processed, "m1")

    assert call_order == ["distill", "plan", "build", "integrate"]
    ok_calls = [c for c in processed.record.call_args_list if c.kwargs.get("outcome") == "ok"]
    assert ok_calls, "no ok outcome recorded"
    assert ok_calls[-1].kwargs.get("commit") == "abc1234"


def test_v2_upgrade_state_only_skips_build_integrate(monkeypatch, tmp_path):
    """upgrade_state_only routing returns early without calling BUILD or INTEGRATE."""
    _neutralise(monkeypatch, tmp_path)
    monkeypatch.setattr(_plan_stage_mod, "plan", MagicMock(return_value="upgrade_state_only"))
    build_spy = MagicMock(return_value={"html_b64": "aGk=", "kind": "calculator", "attempts": 1})
    integrate_spy = MagicMock(return_value="abc1234")
    monkeypatch.setattr(build_mod, "build", build_spy)
    monkeypatch.setattr(integrate_mod, "integrate", integrate_spy)

    processed = MagicMock()
    orchestrator._process_locked(_make_cfg(tmp_path), _make_inbox(), EMAIL, processed, "m1")

    build_spy.assert_not_called()
    integrate_spy.assert_not_called()
    outcomes = [c.kwargs.get("outcome") for c in processed.record.call_args_list]
    assert "upgrade_state_only" in outcomes, outcomes


def test_v2_build_failed_records_and_returns(monkeypatch, tmp_path):
    """build.BuildFailed triggers _reply_failure and records outcome='build_failed'."""
    _neutralise(monkeypatch, tmp_path)
    monkeypatch.setattr(
        build_mod, "build",
        MagicMock(side_effect=BuildFailed(["validation error"], 1)),
    )
    integrate_spy = MagicMock(return_value="abc1234")
    monkeypatch.setattr(integrate_mod, "integrate", integrate_spy)
    reply_mock = MagicMock()
    monkeypatch.setattr(orchestrator, "_reply_failure", reply_mock)

    processed = MagicMock()
    orchestrator._process_locked(_make_cfg(tmp_path), _make_inbox(), EMAIL, processed, "m1")

    integrate_spy.assert_not_called()
    reply_args = reply_mock.call_args[0]
    assert "BUILD failed" in reply_args[3], f"Expected 'BUILD failed' in reply message, got: {reply_args[3]}"
    outcomes = [c.kwargs.get("outcome") for c in processed.record.call_args_list]
    assert "build_failed" in outcomes, outcomes


def test_v2_integrate_failed_records_and_returns(monkeypatch, tmp_path):
    """integrate.IntegrateFailed triggers _reply_failure and records outcome='integrate_failed'."""
    _neutralise(monkeypatch, tmp_path)
    monkeypatch.setattr(
        integrate_mod, "integrate",
        MagicMock(side_effect=IntegrateFailed("no commit")),
    )
    reply_mock = MagicMock()
    monkeypatch.setattr(orchestrator, "_reply_failure", reply_mock)

    processed = MagicMock()
    orchestrator._process_locked(_make_cfg(tmp_path), _make_inbox(), EMAIL, processed, "m1")

    reply_args = reply_mock.call_args[0]
    assert "INTEGRATE failed" in reply_args[3], f"Expected 'INTEGRATE failed' in reply, got: {reply_args[3]}"
    assert "no commit" in reply_args[3]
    outcomes = [c.kwargs.get("outcome") for c in processed.record.call_args_list]
    assert "integrate_failed" in outcomes, outcomes


def test_v2_startup_assert_gitignore_called(monkeypatch, tmp_path):
    """integrate.startup_assert_gitignore(site_dir) is called exactly once per _process_locked."""
    _neutralise(monkeypatch, tmp_path)
    gitignore_spy = MagicMock()
    monkeypatch.setattr(integrate_mod, "startup_assert_gitignore", gitignore_spy)

    expected_site_dir = tmp_path / "site"
    processed = MagicMock()
    orchestrator._process_locked(_make_cfg(tmp_path), _make_inbox(), EMAIL, processed, "m1")

    gitignore_spy.assert_called_once_with(expected_site_dir)
