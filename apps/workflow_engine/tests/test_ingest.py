"""Unit tests for apps/workflow_engine/ingest.py — all externals mocked."""
from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from apps.workflow_engine import ingest


def _email(body="", subject="", sender="a@b.com"):
    return {"body": body, "subject": subject, "from": sender, "message_id": "m1"}


def test_plain_text_passthrough():
    result = ingest.ingest(_email(body="just a thought", subject="s"))
    assert result == {
        "body": "just a thought",
        "subject": "s",
        "sender": "a@b.com",
        "source_type": "text",
        "source_url": None,
    }


def test_return_dict_has_exactly_five_keys():
    result = ingest.ingest(_email(body="x"))
    assert set(result.keys()) == {"body", "subject", "sender", "source_type", "source_url"}


def test_subject_never_scanned():
    result = ingest.ingest(_email(body="nothing", subject="https://youtube.com/watch?v=abc"))
    assert result["source_type"] == "text"
    assert result["source_url"] is None


def test_empty_body():
    result = ingest.ingest(_email(body="", subject="", sender=""))
    assert result["source_type"] == "text"
    assert result["body"] == ""


def test_multiple_urls_first_wins_warning_logged(monkeypatch, caplog):
    monkeypatch.setattr(ingest, "_extract_article", lambda url: "article text")
    body = "see https://example.com/a then https://example.com/b"
    with caplog.at_level(logging.WARNING, logger="workflow.ingest"):
        result = ingest.ingest(_email(body=body))
    assert result["source_url"] == "https://example.com/a"
    assert any("https://example.com/b" in r.message % r.args if r.args else "https://example.com/b" in r.getMessage() for r in caplog.records)


def test_video_url_detected_tools_present(monkeypatch):
    monkeypatch.setattr(ingest.shutil, "which", lambda name: "/fake/ffmpeg" if name == "ffmpeg" else None)
    monkeypatch.setattr(ingest, "_HAS_WHISPER", True)
    monkeypatch.setattr(ingest, "_HAS_YTDLP", True)
    monkeypatch.setattr(ingest, "_download_audio", lambda url, tmp: "/tmp/fake.wav")
    monkeypatch.setattr(ingest, "_transcribe", lambda path: "transcript content")
    monkeypatch.setattr(ingest.tempfile, "mkdtemp", lambda: "/tmp/fake-dir")
    monkeypatch.setattr(ingest.shutil, "rmtree", lambda p, ignore_errors=False: None)
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    result = ingest.ingest(_email(body=f"watch this {url}"))
    assert result["source_type"] == "video"
    assert result["body"] == "transcript content"
    assert result["source_url"] == url


def test_video_url_ffmpeg_absent_falls_back_to_text(monkeypatch, caplog):
    monkeypatch.setattr(ingest.shutil, "which", lambda name: None)
    monkeypatch.setattr(ingest, "_HAS_WHISPER", True)
    monkeypatch.setattr(ingest, "_HAS_YTDLP", True)
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    original = f"watch this {url}"
    with caplog.at_level(logging.INFO, logger="workflow.ingest"):
        result = ingest.ingest(_email(body=original))
    assert result["source_type"] == "text"
    assert result["body"] == original
    assert result["source_url"] is None
    assert any(r.levelname == "INFO" and "ffmpeg" in r.getMessage().lower() for r in caplog.records)


def test_video_url_whisper_import_absent_falls_back_to_text(monkeypatch):
    monkeypatch.setattr(ingest.shutil, "which", lambda name: "/fake/ffmpeg")
    monkeypatch.setattr(ingest, "_HAS_WHISPER", False)
    monkeypatch.setattr(ingest, "_HAS_YTDLP", True)
    url = "https://www.youtube.com/watch?v=abc"
    body = f"watch {url}"
    result = ingest.ingest(_email(body=body))
    assert result["source_type"] == "text"
    assert result["body"] == body


def test_video_transcription_failure_returns_empty_body(monkeypatch, caplog):
    monkeypatch.setattr(ingest.shutil, "which", lambda name: "/fake/ffmpeg")
    monkeypatch.setattr(ingest, "_HAS_WHISPER", True)
    monkeypatch.setattr(ingest, "_HAS_YTDLP", True)
    monkeypatch.setattr(ingest, "_download_audio", lambda url, tmp: "/tmp/fake.wav")
    def boom(_):
        raise RuntimeError("whisper crash")
    monkeypatch.setattr(ingest, "_transcribe", boom)
    monkeypatch.setattr(ingest.tempfile, "mkdtemp", lambda: "/tmp/fake-dir")
    monkeypatch.setattr(ingest.shutil, "rmtree", lambda p, ignore_errors=False: None)
    url = "https://youtu.be/abc"
    with caplog.at_level(logging.WARNING, logger="workflow.ingest"):
        result = ingest.ingest(_email(body=f"v {url}"))
    assert result["source_type"] == "video"
    assert result["body"] == ""
    assert any("whisper" in r.getMessage().lower() or "transcrip" in r.getMessage().lower() for r in caplog.records)


def test_video_tempdir_cleaned_even_on_exception(monkeypatch):
    rmtree_mock = MagicMock()
    monkeypatch.setattr(ingest.shutil, "which", lambda name: "/fake/ffmpeg")
    monkeypatch.setattr(ingest, "_HAS_WHISPER", True)
    monkeypatch.setattr(ingest, "_HAS_YTDLP", True)
    monkeypatch.setattr(ingest.tempfile, "mkdtemp", lambda: "/tmp/fake-dir")
    monkeypatch.setattr(ingest.shutil, "rmtree", rmtree_mock)
    def boom(url, tmp):
        raise RuntimeError("download crash")
    monkeypatch.setattr(ingest, "_download_audio", boom)
    url = "https://www.youtube.com/watch?v=abc"
    ingest.ingest(_email(body=f"v {url}"))
    rmtree_mock.assert_called_once()
    args, kwargs = rmtree_mock.call_args
    assert args[0] == "/tmp/fake-dir"
    assert kwargs.get("ignore_errors") is True


def test_article_url_trafilatura_success(monkeypatch):
    monkeypatch.setattr(ingest, "_extract_article", lambda url: "article body text")
    url = "https://example.com/post"
    result = ingest.ingest(_email(body=f"read {url}"))
    assert result["source_type"] == "article"
    assert result["body"] == "article body text"
    assert result["source_url"] == url


def test_article_extraction_none_falls_back_to_plain_text(monkeypatch):
    monkeypatch.setattr(ingest, "_extract_article", lambda url: None)
    url = "https://example.com/post"
    original = f"read {url}"
    result = ingest.ingest(_email(body=original))
    assert result["source_type"] == "text"
    assert result["body"] == original
    assert result["source_url"] is None
