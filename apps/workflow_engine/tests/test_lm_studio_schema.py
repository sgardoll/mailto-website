"""Tests for lm_studio.chat_json() schema kwarg extension."""
from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from apps.workflow_engine import lm_studio
from packages.config_contract import LmStudioConfig


def _fake_client(response_json: str = '{"a": 1}'):
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content=response_json))
    ]
    return fake_client


def _cfg(**overrides):
    return LmStudioConfig(model="m", temperature=0.4, max_tokens=1000, **overrides)


# ── schema=None uses json_object ──────────────────────────────────────────────

def test_schema_none_uses_json_object(monkeypatch):
    fake_client = _fake_client()
    monkeypatch.setattr(lm_studio, "make_client", lambda cfg: fake_client)
    monkeypatch.setattr(lm_studio, "ensure_running", lambda cfg: None)
    lm_studio.chat_json(_cfg(), system="s", user="u")
    kwargs = fake_client.chat.completions.create.call_args.kwargs
    assert kwargs["response_format"] == {"type": "json_object"}


# ── schema={...} uses json_schema ─────────────────────────────────────────────

def test_schema_provided_uses_json_schema(monkeypatch):
    fake_client = _fake_client('{"mechanic": null}')
    monkeypatch.setattr(lm_studio, "make_client", lambda cfg: fake_client)
    monkeypatch.setattr(lm_studio, "ensure_running", lambda cfg: None)
    schema = {"type": "object", "properties": {"mechanic": {"type": "string"}}, "required": ["mechanic"]}
    lm_studio.chat_json(_cfg(), system="s", user="u", schema=schema)
    kwargs = fake_client.chat.completions.create.call_args.kwargs
    assert kwargs["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "schema": schema,
            "strict": False,
        },
    }


# ── backward compat: schema_hint-only call works unchanged ───────────────────

def test_schema_hint_only_backward_compat(monkeypatch):
    fake_client = _fake_client()
    monkeypatch.setattr(lm_studio, "make_client", lambda cfg: fake_client)
    monkeypatch.setattr(lm_studio, "ensure_running", lambda cfg: None)
    lm_studio.chat_json(_cfg(), system="s", user="u", schema_hint="hint text")
    kwargs = fake_client.chat.completions.create.call_args.kwargs
    assert kwargs["response_format"] == {"type": "json_object"}


# ── fallback: response_format rejection with schema=None ─────────────────────

def test_fallback_on_response_format_error_schema_none(monkeypatch):
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = [
        Exception("model does not support response_format"),
        MagicMock(choices=[MagicMock(message=MagicMock(content='{"x": 1}'))]),
    ]
    monkeypatch.setattr(lm_studio, "make_client", lambda cfg: fake_client)
    monkeypatch.setattr(lm_studio, "ensure_running", lambda cfg: None)
    result = lm_studio.chat_json(_cfg(), system="s", user="u")
    assert result == {"x": 1}
    assert fake_client.chat.completions.create.call_count == 2


# ── fallback: response_format rejection with schema={...} ────────────────────

def test_fallback_on_response_format_error_schema_provided(monkeypatch):
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = [
        Exception("response_format not supported"),
        MagicMock(choices=[MagicMock(message=MagicMock(content='{"y": 2}'))]),
    ]
    monkeypatch.setattr(lm_studio, "make_client", lambda cfg: fake_client)
    monkeypatch.setattr(lm_studio, "ensure_running", lambda cfg: None)
    schema = {"type": "object"}
    result = lm_studio.chat_json(_cfg(), system="s", user="u", schema=schema)
    assert result == {"y": 2}
    assert fake_client.chat.completions.create.call_count == 2


# ── non-response_format error re-raises ──────────────────────────────────────

def test_non_response_format_error_reraises(monkeypatch):
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = RuntimeError("network timeout")
    monkeypatch.setattr(lm_studio, "make_client", lambda cfg: fake_client)
    monkeypatch.setattr(lm_studio, "ensure_running", lambda cfg: None)
    with pytest.raises(RuntimeError, match="network timeout"):
        lm_studio.chat_json(_cfg(), system="s", user="u")


# ── log line includes schema flag ─────────────────────────────────────────────

def test_log_includes_schema_true(monkeypatch, caplog):
    fake_client = _fake_client()
    monkeypatch.setattr(lm_studio, "make_client", lambda cfg: fake_client)
    monkeypatch.setattr(lm_studio, "ensure_running", lambda cfg: None)
    schema = {"type": "object"}
    with caplog.at_level(logging.INFO, logger="workflow.lm_studio"):
        lm_studio.chat_json(_cfg(), system="s", user="u", schema=schema)
    assert any("schema=True" in r.getMessage() for r in caplog.records)


def test_log_includes_schema_false(monkeypatch, caplog):
    fake_client = _fake_client()
    monkeypatch.setattr(lm_studio, "make_client", lambda cfg: fake_client)
    monkeypatch.setattr(lm_studio, "ensure_running", lambda cfg: None)
    with caplog.at_level(logging.INFO, logger="workflow.lm_studio"):
        lm_studio.chat_json(_cfg(), system="s", user="u")
    assert any("schema=False" in r.getMessage() for r in caplog.records)


def test_reasoning_content_fallback_when_empty(monkeypatch):
    fake_client = MagicMock()
    message = MagicMock(content="", reasoning_content='{"snippet": "<button>OK</button>"}')
    fake_client.chat.completions.create.return_value.choices = [
        MagicMock(message=message, finish_reason="stop")
    ]
    monkeypatch.setattr(lm_studio, "make_client", lambda cfg: fake_client)
    monkeypatch.setattr(lm_studio, "ensure_running", lambda cfg: None)

    result = lm_studio.chat_json(_cfg(), system="s", user="u", schema={"type": "object"})
    assert result == {"snippet": "<button>OK</button>"}


def test_reasoning_non_json_is_rejected(monkeypatch):
    """When content is empty and reasoning_content is prose, reject."""
    fake_client = MagicMock()
    message = MagicMock(content="", reasoning_content="Let me think about this...")
    fake_client.chat.completions.create.return_value.choices = [
        MagicMock(message=message, finish_reason="stop")
    ]
    monkeypatch.setattr(lm_studio, "make_client", lambda cfg: fake_client)
    monkeypatch.setattr(lm_studio, "ensure_running", lambda cfg: None)

    with pytest.raises(ValueError, match="non-JSON text in reasoning_content"):
        lm_studio.chat_json(_cfg(), system="s", user="u", schema={"type": "object"})
