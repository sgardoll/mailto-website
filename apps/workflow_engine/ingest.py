"""Normalise inbound email into a structured payload before any LLM stage."""
from __future__ import annotations

import glob
import os
import re
import shutil
import tempfile
from typing import Any

from .logging_setup import get

log = get("ingest")

# ── Third-party imports (guarded for ING-04 graceful degradation) ─────────────
try:
    import yt_dlp  # noqa: F401
    _HAS_YTDLP = True
except ImportError:
    _HAS_YTDLP = False

try:
    from pywhispercpp.model import Model as _WhisperModel
    _HAS_WHISPER = True
except ImportError:
    _WhisperModel = None  # type: ignore[assignment]
    _HAS_WHISPER = False

try:
    import trafilatura  # noqa: F401
    from readability import Document  # noqa: F401
    from lxml import html as lxml_html  # noqa: F401
    _HAS_ARTICLE = True
except ImportError:
    _HAS_ARTICLE = False

# ── Module constants ──────────────────────────────────────────────────────────
VIDEO_URL_PATTERNS = re.compile(
    r"https?://(?:"
    r"(?:www\.)?youtube\.com/watch|"
    r"youtu\.be/|"
    r"(?:www\.)?vimeo\.com/\d|"
    r"(?:www\.)?dailymotion\.com/video/|"
    r"(?:www\.)?tiktok\.com/@[^/]+/video/|"
    r"(?:www\.)?instagram\.com/(?:reel|p)/|"
    r"(?:www\.)?facebook\.com/(?:watch|video)|"
    r"(?:www\.)?twitter\.com/\w+/status/|"
    r"(?:www\.)?x\.com/\w+/status/"
    r")",
    re.IGNORECASE,
)

URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)

WHISPER_MODEL = "base.en"


def _plain_text_result(body: str, subject: str, sender: str) -> dict[str, Any]:
    return {"body": body, "subject": subject, "sender": sender,
            "source_type": "text", "source_url": None}


def ingest(email: dict[str, Any]) -> dict[str, Any]:
    """Return normalized_input dict for one inbound email.

    Always returns a dict with exactly these keys:
      body, subject, sender, source_type ("text"|"video"|"article"), source_url
    Never raises on recoverable extraction failures — degrades to plain text.
    """
    body = email.get("body", "") or ""
    subject = email.get("subject", "") or ""
    sender = email.get("from", "") or ""

    urls = URL_PATTERN.findall(body)
    if not urls:
        return _plain_text_result(body, subject, sender)

    url = urls[0]
    if len(urls) > 1:
        log.warning("multiple URLs found; processing first, skipping: %s", urls[1:])

    if VIDEO_URL_PATTERNS.match(url):
        return _handle_video(url, body, subject, sender)
    return _handle_article(url, body, subject, sender)


def _handle_video(url: str, body: str, subject: str, sender: str) -> dict[str, Any]:
    if not _HAS_YTDLP or not _HAS_WHISPER:
        log.info("video tools missing (ytdlp=%s, whisper=%s) — plain text for %s",
                 _HAS_YTDLP, _HAS_WHISPER, url)
        return _plain_text_result(body, subject, sender)
    if shutil.which("ffmpeg") is None:
        log.info("ffmpeg absent — skipping video transcription for %s", url)
        return _plain_text_result(body, subject, sender)

    tmpdir = tempfile.mkdtemp()
    transcript = ""
    try:
        wav_path = _download_audio(url, tmpdir)
        transcript = _transcribe(wav_path)
    except Exception as e:
        log.warning("whisper transcription failed for %s: %s", url, e)
        transcript = ""
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    return {"body": transcript, "subject": subject, "sender": sender,
            "source_type": "video", "source_url": url}


def _handle_article(url: str, body: str, subject: str, sender: str) -> dict[str, Any]:
    try:
        text = _extract_article(url)
    except Exception as e:
        log.warning("article extraction failed for %s: %s", url, e)
        text = None
    if not text:
        return _plain_text_result(body, subject, sender)
    return {"body": text, "subject": subject, "sender": sender,
            "source_type": "article", "source_url": url}


def _download_audio(url: str, tmpdir: str) -> str:
    """Download best audio from URL, convert to WAV in tmpdir. Returns wav path."""
    outtmpl = os.path.join(tmpdir, "audio.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "wav",
        }],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    matches = glob.glob(os.path.join(tmpdir, "*.wav"))
    if not matches:
        raise FileNotFoundError(f"no .wav produced in {tmpdir}")
    return matches[0]


def _transcribe(wav_path: str) -> str:
    """Transcribe wav_path. Returns joined transcript string."""
    model = _WhisperModel(WHISPER_MODEL)
    segments = model.transcribe(wav_path)
    return " ".join(seg.text.strip() for seg in segments).strip()


def _extract_article(url: str) -> str | None:
    """Extract main text from URL. Returns None if tools absent or both extractors yield nothing."""
    if not _HAS_ARTICLE:
        log.info("article tools missing — plain text for %s", url)
        return None
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        return None
    result = trafilatura.extract(downloaded)
    if result:
        return result
    try:
        doc = Document(downloaded)
        summary_html = doc.summary()
        text = lxml_html.fromstring(summary_html).text_content().strip()
        return text or None
    except Exception as e:
        log.warning("readability fallback failed: %s", e)
        return None
