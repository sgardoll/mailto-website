"""LM Studio client. Uses OpenAI-compatible API; auto-starts if needed."""
from __future__ import annotations
import json
import shutil
import subprocess
import time
from typing import Any

import httpx
from openai import OpenAI

from .config import LmStudioConfig
from .logging_setup import get

log = get("lm_studio")


class LmStudioUnavailable(RuntimeError):
    pass


def _server_alive(base_url: str, timeout_s: float = 2.0) -> bool:
    try:
        r = httpx.get(f"{base_url.rstrip('/')}/models", timeout=timeout_s)
        return r.status_code == 200
    except (httpx.HTTPError, OSError):
        return False


def _model_loaded(base_url: str, model: str) -> bool:
    try:
        r = httpx.get(f"{base_url.rstrip('/')}/models", timeout=5.0)
        if r.status_code != 200:
            return False
        data = r.json().get("data", [])
        return any(m.get("id") == model for m in data)
    except (httpx.HTTPError, OSError, ValueError):
        return False


def ensure_running(cfg: LmStudioConfig) -> None:
    """Best-effort: bring up LM Studio's server and ensure the model is loaded."""
    if _model_loaded(cfg.base_url, cfg.model):
        return
    if not cfg.autostart:
        if _server_alive(cfg.base_url):
            log.warning("Server alive but model %s not loaded; not autostarting.", cfg.model)
            return
        raise LmStudioUnavailable(
            f"LM Studio not reachable at {cfg.base_url} and autostart is off."
        )
    if not shutil.which(cfg.lms_cli_path):
        raise LmStudioUnavailable(
            f"`{cfg.lms_cli_path}` CLI not found on PATH; install it from "
            f"LM Studio (Developer tab) or set lm_studio.lms_cli_path."
        )
    if not _server_alive(cfg.base_url):
        log.info("Starting LM Studio server via `%s server start`...", cfg.lms_cli_path)
        subprocess.run(
            [cfg.lms_cli_path, "server", "start"],
            check=False, capture_output=True, text=True,
        )
        for _ in range(30):
            if _server_alive(cfg.base_url):
                break
            time.sleep(1)
        else:
            raise LmStudioUnavailable("LM Studio server did not come up in 30s.")
    if not _model_loaded(cfg.base_url, cfg.model):
        log.info("Loading model %s via `%s load`...", cfg.model, cfg.lms_cli_path)
        subprocess.run(
            [cfg.lms_cli_path, "load", cfg.model, "--yes"],
            check=False, capture_output=True, text=True,
        )
        for _ in range(60):
            if _model_loaded(cfg.base_url, cfg.model):
                break
            time.sleep(1)
        else:
            raise LmStudioUnavailable(f"Model {cfg.model} did not load in 60s.")


def make_client(cfg: LmStudioConfig) -> OpenAI:
    return OpenAI(
        base_url=cfg.base_url,
        api_key=cfg.api_key,
        timeout=cfg.request_timeout_s,
    )


def chat_json(
    cfg: LmStudioConfig,
    *,
    system: str,
    user: str,
    schema: dict | None = None,
    schema_hint: str | None = None,
) -> dict[str, Any]:
    """Run a chat completion expected to return JSON. Robustly extracts the JSON object."""
    ensure_running(cfg)
    client = make_client(cfg)
    messages = [{"role": "system", "content": system}]
    if schema_hint:
        messages.append({"role": "system", "content": f"Respond with a single JSON object matching:\n{schema_hint}"})
    messages.append({"role": "user", "content": user})

    if schema is not None:
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "schema": schema,
                "strict": True,
            },
        }
    else:
        response_format = {"type": "json_object"}

    log.info("Calling %s (temp=%s, max_tokens=%s, schema=%s)", cfg.model, cfg.temperature, cfg.max_tokens, schema is not None)
    try:
        completion = client.chat.completions.create(
            model=cfg.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            response_format=response_format,
        )
    except Exception as e:
        # Some LM Studio models reject response_format=json_object and only
        # accept 'text' or 'json_schema'. Fall back to text + lenient parse.
        if "response_format" not in str(e):
            raise
        log.info("Model rejected json_object response_format; retrying as text")
        completion = client.chat.completions.create(
            model=cfg.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        )
    text = completion.choices[0].message.content or "{}"
    return _parse_json_lenient(text)


def chat_json_with_meta(
    cfg: LmStudioConfig,
    *,
    system: str,
    user: str,
    schema: dict | None = None,
    schema_hint: str | None = None,
) -> tuple[dict[str, Any], str]:
    """Like chat_json but also returns finish_reason as the second tuple element."""
    ensure_running(cfg)
    client = make_client(cfg)
    messages = [{"role": "system", "content": system}]
    if schema_hint:
        messages.append({"role": "system", "content": f"Respond with a single JSON object matching:\n{schema_hint}"})
    messages.append({"role": "user", "content": user})

    if schema is not None:
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "schema": schema,
                "strict": True,
            },
        }
    else:
        response_format = {"type": "json_object"}

    log.info("Calling %s (temp=%s, max_tokens=%s, schema=%s)", cfg.model, cfg.temperature, cfg.max_tokens, schema is not None)
    try:
        completion = client.chat.completions.create(
            model=cfg.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            response_format=response_format,
        )
    except Exception as e:
        # Some LM Studio models reject response_format=json_object and only
        # accept 'text' or 'json_schema'. Fall back to text + lenient parse.
        if "response_format" not in str(e):
            raise
        log.info("Model rejected json_object response_format; retrying as text")
        completion = client.chat.completions.create(
            model=cfg.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        )
    finish_reason = completion.choices[0].finish_reason or "stop"
    text = completion.choices[0].message.content or "{}"
    return _parse_json_lenient(text), finish_reason


def _parse_json_lenient(text: str) -> dict[str, Any]:
    text = text.strip()
    # Strip ```json fences if the model added them despite response_format.
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find the outermost {...}.
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise
