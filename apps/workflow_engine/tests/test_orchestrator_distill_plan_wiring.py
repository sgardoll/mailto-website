"""Wiring tests: orchestrator v2 branch calls distill then plan in correct order."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from apps.workflow_engine import orchestrator, distill, ingest, lm_studio, \
    site_bootstrap, site_index, topic_curator, apply_changes, build_and_deploy, \
    git_ops, notify
import apps.workflow_engine.plan as _plan_stage_mod
from packages.config_contract import (
    Config, InboxConfig, ImapConfig, SmtpConfig, LmStudioConfig,
)
from apps.workflow_engine.schemas.envelope import MechanicSpec

# ---------------------------------------------------------------------------
# Shared setup (mirrors test_orchestrator_ingest_wiring.py patterns)
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


def _make_inbox(pipeline_version: str = "v1") -> InboxConfig:
    return InboxConfig(
        slug="test",
        address="a@b.com",
        site_name="Test",
        pipeline_version=pipeline_version,
    )


def _neutralise(monkeypatch, tmp_path):
    """Neutralise all side-effectful modules so only the target calls matter."""
    monkeypatch.setattr(site_bootstrap, "ensure_site", lambda inbox: tmp_path / "site")
    monkeypatch.setattr(site_index, "build", lambda *a, **kw: MagicMock(topic=""))
    monkeypatch.setattr(ingest, "ingest", lambda email: {
        "body": "How do I compute BMI?",
        "subject": "BMI question",
        "sender": "a@b.com",
        "source_type": "text",
        "source_url": None,
    })
    monkeypatch.setattr(topic_curator, "update_topic", MagicMock(return_value="topic"))
    monkeypatch.setattr(lm_studio, "chat_json", MagicMock(return_value={"rationale": "ok", "operations": []}))
    monkeypatch.setattr(apply_changes, "apply", MagicMock(return_value=[]))
    monkeypatch.setattr(build_and_deploy, "build", MagicMock())
    monkeypatch.setattr(build_and_deploy, "deploy", MagicMock())
    monkeypatch.setattr(git_ops, "commit_and_push", MagicMock(return_value="abc1234"))
    monkeypatch.setattr(notify, "send", MagicMock())


EMAIL = {"body": "hi", "subject": "s", "from": "a@b.com", "message_id": "m1"}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_v1_inbox_skips_distill_and_plan(monkeypatch, tmp_path):
    _neutralise(monkeypatch, tmp_path)
    distill_mock = MagicMock(return_value=CALCULATOR_SPEC)
    plan_mock = MagicMock(return_value="new_module")
    monkeypatch.setattr(distill, "distill", distill_mock)
    monkeypatch.setattr(_plan_stage_mod, "plan", plan_mock)

    processed = MagicMock()
    orchestrator._process_locked(_make_cfg(tmp_path), _make_inbox("v1"), EMAIL, processed, mid="m1")

    distill_mock.assert_not_called()
    plan_mock.assert_not_called()


def test_v2_happy_path_calls_distill_then_plan_in_order(monkeypatch, tmp_path):
    _neutralise(monkeypatch, tmp_path)
    call_order: list[str] = []

    def fake_distill(ni, lm_cfg):
        call_order.append("distill")
        return CALCULATOR_SPEC

    def fake_plan(spec, site_dir, lm_cfg):
        call_order.append("plan")
        return "new_module"

    monkeypatch.setattr(distill, "distill", fake_distill)
    monkeypatch.setattr(_plan_stage_mod, "plan", fake_plan)

    processed = MagicMock()
    orchestrator._process_locked(_make_cfg(tmp_path), _make_inbox("v2"), EMAIL, processed, mid="m1")

    assert call_order == ["distill", "plan"]


def test_v2_informational_skips_plan_records_upgrade_state_only(monkeypatch, tmp_path):
    _neutralise(monkeypatch, tmp_path)
    monkeypatch.setattr(distill, "distill", MagicMock(return_value=None))
    plan_mock = MagicMock(return_value="new_module")
    monkeypatch.setattr(_plan_stage_mod, "plan", plan_mock)

    processed = MagicMock()
    orchestrator._process_locked(_make_cfg(tmp_path), _make_inbox("v2"), EMAIL, processed, mid="m1")

    plan_mock.assert_not_called()
    # Check that processed.record was called with outcome="upgrade_state_only"
    outcomes = [c.kwargs.get("outcome") for c in processed.record.call_args_list]
    assert "upgrade_state_only" in outcomes


def test_v2_distill_failure_calls_reply_failure_records_distill_failed(monkeypatch, tmp_path):
    _neutralise(monkeypatch, tmp_path)
    monkeypatch.setattr(distill, "distill", MagicMock(side_effect=distill.DistillFailed("boom")))
    reply_mock = MagicMock()
    monkeypatch.setattr(orchestrator, "_reply_failure", reply_mock)

    processed = MagicMock()
    orchestrator._process_locked(_make_cfg(tmp_path), _make_inbox("v2"), EMAIL, processed, mid="m1")

    reply_mock.assert_called_once()
    outcomes = [c.kwargs.get("outcome") for c in processed.record.call_args_list]
    assert "distill_failed" in outcomes


def test_pipe_03_spec_has_no_body_field(monkeypatch, tmp_path):
    _neutralise(monkeypatch, tmp_path)
    captured_specs: list[MechanicSpec] = []

    def fake_distill(ni, lm_cfg):
        return CALCULATOR_SPEC

    def fake_plan(spec, site_dir, lm_cfg):
        captured_specs.append(spec)
        return "new_module"

    monkeypatch.setattr(distill, "distill", fake_distill)
    monkeypatch.setattr(_plan_stage_mod, "plan", fake_plan)

    processed = MagicMock()
    orchestrator._process_locked(_make_cfg(tmp_path), _make_inbox("v2"), EMAIL, processed, mid="m1")

    assert len(captured_specs) == 1
    spec_dict = captured_specs[0].model_dump()
    for forbidden in ("body", "raw_email", "original_text"):
        assert forbidden not in spec_dict, f"Unexpected field in spec passed to plan: {forbidden}"


def test_v2_happy_path_records_v2_planned_outcome(monkeypatch, tmp_path):
    _neutralise(monkeypatch, tmp_path)
    monkeypatch.setattr(distill, "distill", MagicMock(return_value=CALCULATOR_SPEC))
    monkeypatch.setattr(_plan_stage_mod, "plan", MagicMock(return_value="new_module"))

    processed = MagicMock()
    orchestrator._process_locked(_make_cfg(tmp_path), _make_inbox("v2"), EMAIL, processed, mid="m1")

    outcomes = [c.kwargs.get("outcome") for c in processed.record.call_args_list]
    assert any(o and o.startswith("v2_planned_") for o in outcomes), outcomes
