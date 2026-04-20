"""Thin OpenRouter client. Mirrors the lm_studio.chat_json surface area so we
can swap the local runtime for a cloud proxy of the *same* open-weight models
during prompt iteration.

Uses httpx directly (OpenRouter speaks the OpenAI chat/completions schema) to
avoid dragging in the `openai` package purely for the SDK wrapper.
"""
from __future__ import annotations
import json
import time
from dataclasses import dataclass
from typing import Any

import httpx


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterError(RuntimeError):
    pass


@dataclass
class RunResult:
    model_label: str
    slug: str
    ok: bool
    duration_ms: int
    raw_text: str
    parsed: dict[str, Any] | None
    error: str | None = None
    usage: dict[str, Any] | None = None


def _parse_json_lenient(text: str) -> dict[str, Any]:
    """Same strategy as lm_studio._parse_json_lenient: strip fences, pull the
    outermost braces if the model wrapped the object in prose."""
    s = text.strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s.lower().startswith("json"):
            s = s[4:]
        s = s.strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        start, end = s.find("{"), s.rfind("}")
        if start >= 0 and end > start:
            return json.loads(s[start : end + 1])
        raise


def call(
    *,
    api_key: str,
    slug: str,
    system: str,
    user: str,
    temperature: float = 0.4,
    max_tokens: int = 4096,
    timeout_s: float = 300.0,
    referer: str = "http://localhost:5050",
    title: str = "prompt-lab",
) -> tuple[str, dict[str, Any] | None]:
    """Single blocking call. Returns (raw_text, usage_dict|None)."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        # OpenRouter attribution headers (free-tier routing hints).
        "HTTP-Referer": referer,
        "X-Title": title,
    }
    body = {
        "model": slug,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    try:
        r = httpx.post(OPENROUTER_URL, headers=headers, json=body, timeout=timeout_s)
    except httpx.HTTPError as e:
        raise OpenRouterError(f"network error: {e}") from e
    if r.status_code >= 400:
        # Retry once without response_format, since a few open-weight models
        # 400 on json_object despite OpenRouter advertising it.
        if "response_format" in r.text or r.status_code == 400:
            body.pop("response_format", None)
            r = httpx.post(OPENROUTER_URL, headers=headers, json=body, timeout=timeout_s)
        if r.status_code >= 400:
            raise OpenRouterError(f"HTTP {r.status_code}: {r.text[:500]}")
    payload = r.json()
    choices = payload.get("choices") or []
    if not choices:
        raise OpenRouterError(f"no choices in response: {payload}")
    text = choices[0].get("message", {}).get("content") or ""
    return text, payload.get("usage")


def run(
    *,
    api_key: str,
    model_label: str,
    slug: str,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int,
) -> RunResult:
    t0 = time.monotonic()
    try:
        text, usage = call(
            api_key=api_key, slug=slug, system=system, user=user,
            temperature=temperature, max_tokens=max_tokens,
        )
    except OpenRouterError as e:
        return RunResult(
            model_label=model_label, slug=slug, ok=False,
            duration_ms=int((time.monotonic() - t0) * 1000),
            raw_text="", parsed=None, error=str(e),
        )
    duration = int((time.monotonic() - t0) * 1000)
    try:
        parsed = _parse_json_lenient(text)
        return RunResult(
            model_label=model_label, slug=slug, ok=True,
            duration_ms=duration, raw_text=text, parsed=parsed, usage=usage,
        )
    except json.JSONDecodeError as e:
        return RunResult(
            model_label=model_label, slug=slug, ok=False,
            duration_ms=duration, raw_text=text, parsed=None,
            error=f"model returned non-JSON: {e}", usage=usage,
        )
