"""Tests for per-task sampling overrides and thinking-mode plumbing."""
from __future__ import annotations

from unittest.mock import MagicMock

from apps.workflow_engine import lm_studio
from packages.config_contract import LmStudioConfig


def _fake_client(response_json: str = '{"a": 1}'):
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content=response_json), finish_reason="stop")
    ]
    return fake_client


def _patch(monkeypatch, client):
    monkeypatch.setattr(lm_studio, "make_client", lambda cfg: client)
    monkeypatch.setattr(lm_studio, "ensure_running", lambda cfg: None)


# ── _sampling_for: base config only ──────────────────────────────────────────

def test_sampling_base_only_uses_temperature():
    cfg = LmStudioConfig(model="m", temperature=0.4, max_tokens=1000)
    openai_kwargs, extra_body = lm_studio._sampling_for(cfg, task=None)
    assert openai_kwargs == {"temperature": 0.4}
    assert extra_body == {}


def test_sampling_base_includes_optional_knobs_when_set():
    cfg = LmStudioConfig(
        model="m", temperature=0.6, max_tokens=1000,
        top_p=0.95, top_k=20, min_p=0.0, presence_penalty=1.5,
        repetition_penalty=1.1, enable_thinking=True,
    )
    openai_kwargs, extra_body = lm_studio._sampling_for(cfg, task=None)
    assert openai_kwargs == {"temperature": 0.6, "top_p": 0.95, "presence_penalty": 1.5}
    assert extra_body == {
        "top_k": 20,
        "min_p": 0.0,
        "repetition_penalty": 1.1,
        "chat_template_kwargs": {"enable_thinking": True},
    }


# ── _sampling_for: task override shallow-merges over base ────────────────────

def test_task_override_shallow_merges_over_base():
    cfg = LmStudioConfig(
        model="m", temperature=1.0, max_tokens=1000,
        top_p=0.95, top_k=64, enable_thinking=False,
        task_overrides={
            "build": {
                "temperature": 0.6,
                "top_k": 20,
                "enable_thinking": True,
            }
        },
    )
    openai_kwargs, extra_body = lm_studio._sampling_for(cfg, task="build")
    # temperature + top_k overridden, top_p inherited, enable_thinking flipped
    assert openai_kwargs == {"temperature": 0.6, "top_p": 0.95}
    assert extra_body == {
        "top_k": 20,
        "chat_template_kwargs": {"enable_thinking": True},
    }


def test_task_override_ignored_when_task_not_listed():
    cfg = LmStudioConfig(
        model="m", temperature=0.4, max_tokens=1000,
        task_overrides={"build": {"temperature": 0.6}},
    )
    openai_kwargs, _ = lm_studio._sampling_for(cfg, task="topic_curation")
    assert openai_kwargs == {"temperature": 0.4}


def test_task_override_none_values_are_skipped():
    cfg = LmStudioConfig(
        model="m", temperature=0.4, max_tokens=1000, top_p=0.95,
        task_overrides={"plan": {"temperature": None, "top_k": 20}},
    )
    openai_kwargs, extra_body = lm_studio._sampling_for(cfg, task="plan")
    # temperature None ignored (base wins); top_k added via extra_body
    assert openai_kwargs == {"temperature": 0.4, "top_p": 0.95}
    assert extra_body == {"top_k": 20}


# ── chat_json: task kwarg threads through to the create() call ───────────────

def test_chat_json_passes_overrides_to_openai_call(monkeypatch):
    fake_client = _fake_client()
    _patch(monkeypatch, fake_client)
    cfg = LmStudioConfig(
        model="m", temperature=1.0, max_tokens=1000,
        task_overrides={
            "topic_curation": {
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 20,
                "presence_penalty": 1.5,
                "enable_thinking": False,
            }
        },
    )
    lm_studio.chat_json(cfg, system="s", user="u", task="topic_curation")
    kwargs = fake_client.chat.completions.create.call_args.kwargs
    assert kwargs["temperature"] == 0.7
    assert kwargs["top_p"] == 0.8
    assert kwargs["presence_penalty"] == 1.5
    assert kwargs["extra_body"] == {
        "top_k": 20,
        "chat_template_kwargs": {"enable_thinking": False},
    }


def test_chat_json_without_task_uses_base_sampling(monkeypatch):
    fake_client = _fake_client()
    _patch(monkeypatch, fake_client)
    cfg = LmStudioConfig(
        model="m", temperature=0.4, max_tokens=1000,
        task_overrides={"build": {"temperature": 0.6}},
    )
    lm_studio.chat_json(cfg, system="s", user="u")
    kwargs = fake_client.chat.completions.create.call_args.kwargs
    assert kwargs["temperature"] == 0.4
    assert "extra_body" not in kwargs


def test_chat_json_with_meta_threads_task(monkeypatch):
    fake_client = _fake_client()
    _patch(monkeypatch, fake_client)
    cfg = LmStudioConfig(
        model="m", temperature=1.0, max_tokens=1000,
        task_overrides={"build": {"temperature": 0.6, "enable_thinking": True}},
    )
    lm_studio.chat_json_with_meta(cfg, system="s", user="u", task="build")
    kwargs = fake_client.chat.completions.create.call_args.kwargs
    assert kwargs["temperature"] == 0.6
    assert kwargs["extra_body"]["chat_template_kwargs"]["enable_thinking"] is True
