"""Tests for apps.workflow_engine.build."""
from __future__ import annotations

import base64
from unittest.mock import MagicMock

import pytest

from apps.workflow_engine import lm_studio
import apps.workflow_engine.build as build_mod

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BASE = """<!DOCTYPE html>
<html>
<head>
  <script src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js" defer></script>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body>
  <div x-data="{ count: 0 }">
    <button @click="count++" class="bg-blue-500 text-white px-4 py-2">Click</button>
    <p x-text="count"></p>
  </div>
</body>
</html>"""

VALID_HTML = _BASE * 3  # ensures > 800 bytes
SHORT_INVALID_HTML = "<div>too short</div>"  # < 800 bytes, missing x-data, missing CDN tags

# A second invalid HTML that produces different errors from SHORT_INVALID_HTML
# (has x-data but still < 800 bytes and missing CDN tags — same validator errors)
# We rely on the fact that prev_errors starts as None on attempt 1 for retry tests.

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CALCULATOR_DATA = {
    "kind": "calculator",
    "title": "BMI Calculator",
    "intent": "Calculate body mass index",
    "inputs": ["weight_kg", "height_m"],
    "outputs": ["bmi"],
    "content": {
        "kind": "calculator",
        "formula_description": "weight / height^2",
        "variables": [{"name": "weight", "unit": "kg", "default": 70}],
        "unit": "kg/m2",
    },
}


def _make_spec():
    from apps.workflow_engine.schemas.envelope import MechanicSpec
    return MechanicSpec.model_validate(_CALCULATOR_DATA)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_happy_path_returns_html_b64(monkeypatch):
    monkeypatch.setattr(
        lm_studio, "chat_json_with_meta", MagicMock(return_value=({"html": VALID_HTML}, "stop"))
    )
    result = build_mod.build(_make_spec(), MagicMock())
    assert "html_b64" in result
    assert result["kind"] == "calculator"
    assert result["attempts"] == 1
    assert base64.b64decode(result["html_b64"]).decode("utf-8") == VALID_HTML


def test_base64_encoding_is_correct(monkeypatch):
    monkeypatch.setattr(
        lm_studio, "chat_json_with_meta", MagicMock(return_value=({"html": VALID_HTML}, "stop"))
    )
    result = build_mod.build(_make_spec(), MagicMock())
    decoded = base64.b64decode(result["html_b64"]).decode("utf-8")
    assert decoded == VALID_HTML


def test_finish_reason_length_raises_immediately(monkeypatch):
    mock = MagicMock(return_value=({"html": VALID_HTML}, "length"))
    monkeypatch.setattr(lm_studio, "chat_json_with_meta", mock)
    with pytest.raises(build_mod.BuildFailed) as exc_info:
        build_mod.build(_make_spec(), MagicMock())
    assert exc_info.value.attempts == 1
    assert "finish_reason=length" in exc_info.value.errors[0]
    assert mock.call_count == 1


def test_finish_reason_stop_does_not_abort(monkeypatch):
    monkeypatch.setattr(
        lm_studio, "chat_json_with_meta", MagicMock(return_value=({"html": VALID_HTML}, "stop"))
    )
    result = build_mod.build(_make_spec(), MagicMock())
    assert "html_b64" in result


def test_retry_on_validation_failure_calls_lm_three_times(monkeypatch):
    mock = MagicMock(return_value=({"html": SHORT_INVALID_HTML}, "stop"))
    monkeypatch.setattr(lm_studio, "chat_json_with_meta", mock)
    with pytest.raises(build_mod.BuildFailed) as exc_info:
        build_mod.build(_make_spec(), MagicMock())
    # SHORT_INVALID_HTML produces the same errors every time, so early abort fires on attempt 2.
    # Attempts: 1 (first call) + 2 (second call, errors same as prev -> abort).
    assert mock.call_count == 2
    assert exc_info.value.attempts == 2


def test_early_abort_when_errors_frozen(monkeypatch):
    mock = MagicMock(return_value=({"html": SHORT_INVALID_HTML}, "stop"))
    monkeypatch.setattr(lm_studio, "chat_json_with_meta", mock)
    with pytest.raises(build_mod.BuildFailed) as exc_info:
        build_mod.build(_make_spec(), MagicMock())
    # Same error set on attempt 2 as attempt 1 -> early abort
    assert mock.call_count == 2
    assert exc_info.value.attempts == 2


def test_retry_succeeds_on_second_attempt(monkeypatch):
    # attempt 1: invalid (prev_errors is None -> no early abort)
    # attempt 2: valid -> success
    mock = MagicMock(side_effect=[
        ({"html": SHORT_INVALID_HTML}, "stop"),
        ({"html": VALID_HTML}, "stop"),
    ])
    monkeypatch.setattr(lm_studio, "chat_json_with_meta", mock)
    result = build_mod.build(_make_spec(), MagicMock())
    assert result["attempts"] == 2
    assert mock.call_count == 2


def test_schema_kwarg_passed_to_chat_json_with_meta(monkeypatch):
    from apps.workflow_engine.schemas.json_schema import BUILD_SCHEMA

    captured: list[dict] = []

    def fake(cfg, *, system, user, schema=None, schema_hint=None):
        captured.append({"schema": schema})
        return ({"html": VALID_HTML}, "stop")

    monkeypatch.setattr(lm_studio, "chat_json_with_meta", fake)
    build_mod.build(_make_spec(), MagicMock())
    assert len(captured) == 1
    assert captured[0]["schema"] is BUILD_SCHEMA


def test_exemplar_selection_by_kind(monkeypatch):
    from apps.workflow_engine.exemplars import CALCULATOR_EXEMPLAR, WIZARD_EXEMPLAR

    captured_system: list[str] = []

    def fake(cfg, *, system, user, schema=None, schema_hint=None):
        captured_system.append(system)
        return ({"html": VALID_HTML}, "stop")

    monkeypatch.setattr(lm_studio, "chat_json_with_meta", fake)
    build_mod.build(_make_spec(), MagicMock())
    assert len(captured_system) == 1
    assert "calculator" in captured_system[0]
    assert CALCULATOR_EXEMPLAR in captured_system[0]
    assert WIZARD_EXEMPLAR not in captured_system[0]


def test_exemplar_passes_validator(monkeypatch):
    from apps.workflow_engine.exemplars import (
        CALCULATOR_EXEMPLAR,
        WIZARD_EXEMPLAR,
        DRILL_EXEMPLAR,
        SCORER_EXEMPLAR,
        GENERATOR_EXEMPLAR,
    )
    from apps.workflow_engine import validator

    for name, exemplar in [
        ("CALCULATOR", CALCULATOR_EXEMPLAR),
        ("WIZARD", WIZARD_EXEMPLAR),
        ("DRILL", DRILL_EXEMPLAR),
        ("SCORER", SCORER_EXEMPLAR),
        ("GENERATOR", GENERATOR_EXEMPLAR),
    ]:
        errors = validator.validate_module(exemplar)
        assert errors == [], f"{name}_EXEMPLAR failed validation: {errors}"


def test_build_failed_carries_errors_and_attempts(monkeypatch):
    mock = MagicMock(return_value=({"html": SHORT_INVALID_HTML}, "stop"))
    monkeypatch.setattr(lm_studio, "chat_json_with_meta", mock)
    with pytest.raises(build_mod.BuildFailed) as exc_info:
        build_mod.build(_make_spec(), MagicMock())
    assert isinstance(exc_info.value.errors, list)
    assert len(exc_info.value.errors) > 0
    assert exc_info.value.attempts >= 1


def test_max_tokens_enforced_internally(monkeypatch):
    captured_cfgs: list = []

    def fake(cfg, *, system, user, schema=None, schema_hint=None):
        captured_cfgs.append(cfg)
        return ({"html": VALID_HTML}, "stop")

    monkeypatch.setattr(lm_studio, "chat_json_with_meta", fake)

    from packages.config_contract import LmStudioConfig
    low_cfg = LmStudioConfig(max_tokens=512)
    build_mod.build(_make_spec(), low_cfg)
    assert len(captured_cfgs) == 1
    assert captured_cfgs[0].max_tokens >= 8000
