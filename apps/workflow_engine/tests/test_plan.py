"""Tests for apps.workflow_engine.plan."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import apps.workflow_engine.plan as plan_mod
from apps.workflow_engine import lm_studio
from apps.workflow_engine.schemas.envelope import MechanicSpec

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CALCULATOR_SPEC_DATA = {
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
}

MODULE_IN_MANIFEST = {
    "module_id": "bmi-calc",
    "title": "BMI Calculator",
    "kind": "calculator",
}


def _make_spec() -> MechanicSpec:
    return MechanicSpec.model_validate(CALCULATOR_SPEC_DATA)


def _make_manifest(modules: list[dict]) -> dict:
    return {"schema_version": "1", "modules": modules}


def _write_manifest(site_dir: Path, modules: list[dict]) -> None:
    spa_dir = site_dir / "public" / "spa"
    spa_dir.mkdir(parents=True, exist_ok=True)
    (spa_dir / "spa_manifest.json").write_text(json.dumps(_make_manifest(modules)))


def _mock_model(sim_value: float) -> MagicMock:
    model = MagicMock()
    model.encode.return_value = [[0.0] * 384]
    model.similarity.return_value = [[sim_value]]
    return model


# ---------------------------------------------------------------------------
# Autouse fixture: reset _MODEL between tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_model():
    plan_mod._MODEL = None
    yield
    plan_mod._MODEL = None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_no_manifest_file_returns_new_module(monkeypatch, tmp_path):
    # No manifest file exists — should return new_module without calling _get_model
    get_model_mock = MagicMock()
    monkeypatch.setattr(plan_mod, "_get_model", get_model_mock)
    result = plan_mod.plan(_make_spec(), tmp_path, MagicMock())
    assert result == "new_module"
    get_model_mock.assert_not_called()


def test_empty_modules_returns_new_module(monkeypatch, tmp_path):
    _write_manifest(tmp_path, [])
    get_model_mock = MagicMock()
    monkeypatch.setattr(plan_mod, "_get_model", get_model_mock)
    result = plan_mod.plan(_make_spec(), tmp_path, MagicMock())
    assert result == "new_module"
    get_model_mock.assert_not_called()


def test_high_similarity_returns_extend_module(monkeypatch, tmp_path):
    _write_manifest(tmp_path, [MODULE_IN_MANIFEST])
    monkeypatch.setattr(plan_mod, "_get_model", lambda: _mock_model(0.90))
    result = plan_mod.plan(_make_spec(), tmp_path, MagicMock())
    assert result == "extend_module"


def test_low_similarity_returns_new_module(monkeypatch, tmp_path):
    _write_manifest(tmp_path, [MODULE_IN_MANIFEST])
    monkeypatch.setattr(plan_mod, "_get_model", lambda: _mock_model(0.30))
    result = plan_mod.plan(_make_spec(), tmp_path, MagicMock())
    assert result == "new_module"


def test_ambiguous_triggers_judge(monkeypatch, tmp_path):
    _write_manifest(tmp_path, [MODULE_IN_MANIFEST])
    monkeypatch.setattr(plan_mod, "_get_model", lambda: _mock_model(0.60))
    monkeypatch.setattr(
        lm_studio,
        "chat_json",
        MagicMock(return_value={"decision": "extend_module", "rationale": "close enough"}),
    )
    result = plan_mod.plan(_make_spec(), tmp_path, MagicMock())
    assert result == "extend_module"


def test_judge_unknown_decision_defaults_new_module(monkeypatch, tmp_path):
    _write_manifest(tmp_path, [MODULE_IN_MANIFEST])
    monkeypatch.setattr(plan_mod, "_get_model", lambda: _mock_model(0.60))
    monkeypatch.setattr(
        lm_studio,
        "chat_json",
        MagicMock(return_value={"decision": "frobnicate", "rationale": "weird"}),
    )
    result = plan_mod.plan(_make_spec(), tmp_path, MagicMock())
    assert result == "new_module"


def test_judge_receives_no_raw_body(monkeypatch, tmp_path):
    _write_manifest(tmp_path, [MODULE_IN_MANIFEST])
    monkeypatch.setattr(plan_mod, "_get_model", lambda: _mock_model(0.60))

    captured_user: list[str] = []

    def fake_chat_json(cfg, *, system, user, schema=None, schema_hint=None, task=None):
        captured_user.append(user)
        return {"decision": "new_module", "rationale": "ok"}

    monkeypatch.setattr(lm_studio, "chat_json", fake_chat_json)
    plan_mod.plan(_make_spec(), tmp_path, MagicMock())

    assert len(captured_user) == 1
    user_msg = captured_user[0]
    assert '"body"' not in user_msg
    assert "raw_email" not in user_msg


def test_rationale_logged_with_snapshot(monkeypatch, tmp_path, caplog):
    _write_manifest(tmp_path, [MODULE_IN_MANIFEST])
    monkeypatch.setattr(plan_mod, "_get_model", lambda: _mock_model(0.90))
    with caplog.at_level(logging.INFO, logger="workflow.plan"):
        plan_mod.plan(_make_spec(), tmp_path, MagicMock())
    msgs = [r.getMessage() for r in caplog.records]
    assert any("decision=" in m for m in msgs), msgs
    assert any("snapshot=" in m for m in msgs), msgs


def test_threshold_boundary_085_triggers_judge(monkeypatch, tmp_path):
    # sim=0.85 is NOT > 0.85 so judge should be called
    _write_manifest(tmp_path, [MODULE_IN_MANIFEST])
    monkeypatch.setattr(plan_mod, "_get_model", lambda: _mock_model(0.85))
    judge_mock = MagicMock(return_value={"decision": "extend_module", "rationale": "boundary"})
    monkeypatch.setattr(lm_studio, "chat_json", judge_mock)
    result = plan_mod.plan(_make_spec(), tmp_path, MagicMock())
    judge_mock.assert_called_once()
    assert result == "extend_module"


def test_threshold_boundary_040_triggers_judge(monkeypatch, tmp_path):
    # sim=0.40 is NOT < 0.40 so judge should be called
    _write_manifest(tmp_path, [MODULE_IN_MANIFEST])
    monkeypatch.setattr(plan_mod, "_get_model", lambda: _mock_model(0.40))
    judge_mock = MagicMock(return_value={"decision": "new_module", "rationale": "boundary"})
    monkeypatch.setattr(lm_studio, "chat_json", judge_mock)
    result = plan_mod.plan(_make_spec(), tmp_path, MagicMock())
    judge_mock.assert_called_once()
    assert result == "new_module"
