"""Tests for apps.workflow_engine.distill."""
from __future__ import annotations

from unittest.mock import MagicMock, call

import pytest

from apps.workflow_engine import distill, lm_studio
from apps.workflow_engine.schemas.envelope import MechanicSpec

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

VALID_CALCULATOR_ENVELOPE = {
    "mechanic": {
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
}

NI = {
    "body": "How do I compute BMI?",
    "subject": "BMI question",
    "sender": "a@b.com",
    "source_type": "text",
    "source_url": None,
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_happy_path_returns_mechanic_spec(monkeypatch):
    monkeypatch.setattr(lm_studio, "chat_json", MagicMock(return_value=VALID_CALCULATOR_ENVELOPE))
    result = distill.distill(NI, MagicMock())
    assert isinstance(result, MechanicSpec)
    assert result.title == "BMI Calculator"
    assert result.kind.value == "calculator"


def test_informational_email_returns_none(monkeypatch):
    monkeypatch.setattr(
        lm_studio,
        "chat_json",
        MagicMock(return_value={"mechanic": None, "skip_reason": "announcement"}),
    )
    result = distill.distill(NI, MagicMock())
    assert result is None


def test_retry_success_calls_chat_json_twice(monkeypatch):
    invalid = {"mechanic": {"kind": "calculator"}}  # missing required fields
    mock_chat = MagicMock(side_effect=[invalid, VALID_CALCULATOR_ENVELOPE])
    monkeypatch.setattr(lm_studio, "chat_json", mock_chat)
    result = distill.distill(NI, MagicMock())
    assert mock_chat.call_count == 2
    assert isinstance(result, MechanicSpec)


def test_retry_failure_raises_distill_failed(monkeypatch):
    invalid = {"mechanic": {"kind": "calculator"}}  # missing required fields
    mock_chat = MagicMock(side_effect=[invalid, invalid])
    monkeypatch.setattr(lm_studio, "chat_json", mock_chat)
    with pytest.raises(distill.DistillFailed):
        distill.distill(NI, MagicMock())
    assert mock_chat.call_count == 2


def test_kind_content_mismatch_triggers_retry_then_fails(monkeypatch):
    # kind=wizard but content.kind=calculator — jsonschema passes but Pydantic raises ValueError
    mismatch = {
        "mechanic": {
            "kind": "wizard",
            "title": "BMI",
            "intent": "test",
            "inputs": ["x"],
            "outputs": ["y"],
            "content": {
                "kind": "calculator",
                "formula_description": "f",
                "variables": [{"name": "v", "unit": "u", "default": 1}],
                "unit": "u",
            },
        }
    }
    mock_chat = MagicMock(side_effect=[mismatch, mismatch])
    monkeypatch.setattr(lm_studio, "chat_json", mock_chat)
    with pytest.raises(distill.DistillFailed):
        distill.distill(NI, MagicMock())
    assert mock_chat.call_count == 2


def test_source_url_preserved_from_normalized_input(monkeypatch):
    monkeypatch.setattr(lm_studio, "chat_json", MagicMock(return_value=VALID_CALCULATOR_ENVELOPE))
    ni_with_url = {**NI, "source_url": "https://example.com/bmi"}
    result = distill.distill(ni_with_url, MagicMock())
    assert result is not None
    assert result.source_url == "https://example.com/bmi"


def test_module_id_auto_generated_from_title(monkeypatch):
    monkeypatch.setattr(lm_studio, "chat_json", MagicMock(return_value=VALID_CALCULATOR_ENVELOPE))
    result = distill.distill(NI, MagicMock())
    assert result is not None
    assert result.module_id == "bmi-calculator"


def test_module_id_respected_when_provided(monkeypatch):
    envelope_with_id = {
        "mechanic": {
            **VALID_CALCULATOR_ENVELOPE["mechanic"],
            "module_id": "my-custom-id",
        }
    }
    monkeypatch.setattr(lm_studio, "chat_json", MagicMock(return_value=envelope_with_id))
    result = distill.distill(NI, MagicMock())
    assert result is not None
    assert result.module_id == "my-custom-id"


def test_schema_kwarg_passed_to_chat_json(monkeypatch):
    from apps.workflow_engine.schemas.json_schema import DISTILL_SCHEMA

    captured_kwargs: list[dict] = []

    def fake_chat_json(cfg, *, system, user, schema=None, schema_hint=None):
        captured_kwargs.append({"schema": schema})
        return VALID_CALCULATOR_ENVELOPE

    monkeypatch.setattr(lm_studio, "chat_json", fake_chat_json)
    distill.distill(NI, MagicMock())
    assert len(captured_kwargs) == 1
    assert captured_kwargs[0]["schema"] is DISTILL_SCHEMA


def test_spec_has_no_raw_body_fields(monkeypatch):
    monkeypatch.setattr(lm_studio, "chat_json", MagicMock(return_value=VALID_CALCULATOR_ENVELOPE))
    result = distill.distill(NI, MagicMock())
    assert result is not None
    spec_dict = result.model_dump()
    for forbidden in ("body", "raw_email", "original_text", "raw_body"):
        assert forbidden not in spec_dict, f"Unexpected field in spec: {forbidden}"


def test_slugify_special_characters():
    assert distill._slugify("Hello World! 123") == "hello-world-123"
    assert distill._slugify("  ---  ") == "module"
    assert distill._slugify("A" * 100) == "a" * 64
