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


def _loaded_models(lms_cli_path: str) -> list[str]:
    """Return identifiers of models currently held in memory by LM Studio.

    Uses `lms ps --json`, which reports only in-memory models (the OpenAI
    `/v1/models` endpoint returns all discoverable models, not just loaded
    ones, so it can't be used for this).
    """
    if not shutil.which(lms_cli_path):
        return []
    try:
        r = subprocess.run(
            [lms_cli_path, "ps", "--json"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode != 0:
            return []
        data = json.loads(r.stdout or "[]")
        return [m.get("identifier") or m.get("modelKey") for m in data if m.get("identifier") or m.get("modelKey")]
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return []


def _load_args(cfg: LmStudioConfig, model: str) -> list[str]:
    """Build the `lms load` argv. Adds optional --gpu, -c, --ttl when set."""
    args = [cfg.lms_cli_path, "load", model, "--yes"]
    if cfg.context_length is not None:
        args += ["-c", str(cfg.context_length)]
    if cfg.gpu_offload is not None:
        args += ["--gpu", cfg.gpu_offload]
    if cfg.ttl_seconds is not None:
        args += ["--ttl", str(cfg.ttl_seconds)]
    return args


class LmStudioEstimateRefused(LmStudioUnavailable):
    """Raised when `lms load --estimate-only` says the model won't fit."""


def _estimate_load(cfg: LmStudioConfig, model: str) -> tuple[bool, str]:
    """Run `lms load --estimate-only` and parse its plain-text output.

    Returns (will_fit, summary). On any error, returns (True, "") so the caller
    falls through to the real load — we don't want a flaky estimator to block
    legitimate loads.
    """
    if not shutil.which(cfg.lms_cli_path):
        return True, ""
    args = _load_args(cfg, model) + ["--estimate-only"]
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=30)
    except (subprocess.TimeoutExpired, OSError):
        return True, ""
    out = (r.stdout or "") + (r.stderr or "")
    summary = out.strip()
    # `lms load --estimate-only` ends with a sentence containing
    # "will fail to load" when guardrails would reject it.
    if "will fail to load" in summary.lower():
        return False, summary
    return True, summary


def ensure_running(cfg: LmStudioConfig) -> None:
    """Ensure an LM is usable. Mutates cfg.model if a fallback model is chosen.

    Resilience policy: rather than failing when the configured model can't be
    loaded (memory pressure, model removed, etc.), fall back to whatever is
    already loaded in memory. Only try to load the configured model if nothing
    is loaded at all.
    """
    loaded = _loaded_models(cfg.lms_cli_path) if _server_alive(cfg.base_url) else []

    if cfg.model in loaded:
        return

    if loaded:
        log.warning(
            "Configured model %r is not loaded in LM Studio; falling back to %r (already in memory).",
            cfg.model, loaded[0],
        )
        cfg.model = loaded[0]
        return

    # Nothing loaded — start server and load configured model.
    if not cfg.autostart:
        if _server_alive(cfg.base_url):
            log.warning("Server alive but no model loaded; not autostarting.")
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
    if cfg.estimate_before_load:
        will_fit, summary = _estimate_load(cfg, cfg.model)
        if not will_fit:
            raise LmStudioEstimateRefused(
                f"Refusing to load {cfg.model!r}: LM Studio resource estimate "
                f"says it won't fit. Lower context_length or gpu_offload, or "
                f"choose a smaller model.\n{summary}"
            )
        if summary:
            log.info("Load estimate for %s:\n%s", cfg.model, summary)
    args = _load_args(cfg, cfg.model)
    log.info("Loading model via: %s", " ".join(args))
    load = subprocess.run(args, capture_output=True, text=True)
    for _ in range(60):
        if cfg.model in _loaded_models(cfg.lms_cli_path):
            return
        time.sleep(1)
    # Load failed (likely memory). Try any model that might have loaded meanwhile.
    fallback = _loaded_models(cfg.lms_cli_path)
    if fallback:
        log.warning(
            "Could not load %r (stderr: %s); falling back to %r.",
            cfg.model, load.stderr.strip()[:200], fallback[0],
        )
        cfg.model = fallback[0]
        return
    raise LmStudioUnavailable(
        f"Model {cfg.model} did not load in 60s and nothing else is loaded either. "
        f"Load any model manually in LM Studio and retry. Last loader stderr: {load.stderr.strip()[:200]}"
    )


def _is_model_load_failure(e: Exception) -> bool:
    """True if an OpenAI error looks like a 'model unavailable / crashed' failure."""
    s = str(e).lower()
    return (
        "failed to load model" in s
        or "insufficient system resources" in s
        or "model has crashed" in s
        or "channel error" in s
        or "model not found" in s
    )


def _try_load(cfg: LmStudioConfig, model: str, wait_s: int = 60) -> bool:
    """Try to load a specific model via lms CLI. Returns True if it ended up loaded."""
    if not shutil.which(cfg.lms_cli_path):
        return False
    if cfg.estimate_before_load:
        will_fit, summary = _estimate_load(cfg, model)
        if not will_fit:
            log.warning(
                "Refusing to reload %r: estimate says it won't fit.\n%s",
                model, summary,
            )
            return False
    args = _load_args(cfg, model)
    log.info("Attempting to load %r via: %s", model, " ".join(args))
    load = subprocess.run(args, capture_output=True, text=True)
    for _ in range(wait_s):
        if model in _loaded_models(cfg.lms_cli_path):
            return True
        time.sleep(1)
    log.warning(
        "Could not load %r within %ds (stderr: %s).",
        model, wait_s, load.stderr.strip()[:200],
    )
    return False


def make_client(cfg: LmStudioConfig) -> OpenAI:
    return OpenAI(
        base_url=cfg.base_url,
        api_key=cfg.api_key,
        timeout=cfg.request_timeout_s,
    )


_OPENAI_SAMPLING_KEYS = ("temperature", "top_p", "presence_penalty")
_EXTRA_BODY_SAMPLING_KEYS = ("top_k", "min_p", "repetition_penalty")


def _sampling_for(cfg: LmStudioConfig, task: str | None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build (openai_kwargs, extra_body) for this call.

    - OpenAI-native kwargs (temperature, top_p, presence_penalty) go on the
      top-level create() call.
    - Vendor knobs (top_k, min_p, repetition_penalty) and enable_thinking go
      in extra_body so LM Studio / vLLM / llama.cpp servers receive them.
    - Per-task overrides shallow-merge over base cfg; None values are skipped.
    """
    merged: dict[str, Any] = {"temperature": cfg.temperature}
    for key in _OPENAI_SAMPLING_KEYS[1:] + _EXTRA_BODY_SAMPLING_KEYS:
        val = getattr(cfg, key, None)
        if val is not None:
            merged[key] = val
    enable_thinking = cfg.enable_thinking

    overrides = (cfg.task_overrides or {}).get(task) if task else None
    if overrides:
        for key in _OPENAI_SAMPLING_KEYS + _EXTRA_BODY_SAMPLING_KEYS:
            if key in overrides and overrides[key] is not None:
                merged[key] = overrides[key]
        if "enable_thinking" in overrides:
            enable_thinking = overrides["enable_thinking"]

    openai_kwargs = {k: merged[k] for k in _OPENAI_SAMPLING_KEYS if k in merged}
    extra_body: dict[str, Any] = {
        k: merged[k] for k in _EXTRA_BODY_SAMPLING_KEYS if k in merged
    }
    if enable_thinking is not None:
        extra_body.setdefault("chat_template_kwargs", {})["enable_thinking"] = enable_thinking
    return openai_kwargs, extra_body


def chat_json(
    cfg: LmStudioConfig,
    *,
    system: str,
    user: str,
    schema: dict | None = None,
    schema_hint: str | None = None,
    task: str | None = None,
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
                "strict": False,
            },
        }
    else:
        response_format = {"type": "json_object"}

    sampling, extra_body = _sampling_for(cfg, task)
    log.info(
        "Calling %s (task=%s, sampling=%s, extra_body=%s, schema=%s)",
        cfg.model, task, sampling, extra_body, schema is not None,
    )
    completion = _call_with_fallbacks(cfg, client, messages, response_format, sampling, extra_body)
    text = completion.choices[0].message.content or "{}"
    return _parse_json_lenient(text)


def chat_json_with_meta(
    cfg: LmStudioConfig,
    *,
    system: str,
    user: str,
    schema: dict | None = None,
    schema_hint: str | None = None,
    task: str | None = None,
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
                "strict": False,
            },
        }
    else:
        response_format = {"type": "json_object"}

    sampling, extra_body = _sampling_for(cfg, task)
    log.info(
        "Calling %s (task=%s, sampling=%s, extra_body=%s, schema=%s)",
        cfg.model, task, sampling, extra_body, schema is not None,
    )
    completion = _call_with_fallbacks(cfg, client, messages, response_format, sampling, extra_body)
    finish_reason = completion.choices[0].finish_reason or "stop"
    text = completion.choices[0].message.content or "{}"
    return _parse_json_lenient(text), finish_reason


def _call_with_fallbacks(
    cfg: LmStudioConfig,
    client: OpenAI,
    messages: list,
    response_format: dict,
    sampling: dict[str, Any],
    extra_body: dict[str, Any],
):
    """Call chat.completions.create with two fallbacks:

    1. If the model rejects the response_format (some local models do), retry
       without it and rely on lenient JSON parsing.
    2. If the model can't be loaded (e.g. memory pressure), switch to whatever
       LM Studio has already loaded and retry.
    """
    def _do(model: str, rf: dict | None):
        kwargs: dict[str, Any] = dict(
            model=model,
            messages=messages,
            max_tokens=cfg.max_tokens,
            **sampling,
        )
        if extra_body:
            kwargs["extra_body"] = extra_body
        if rf is not None:
            kwargs["response_format"] = rf
        return client.chat.completions.create(**kwargs)

    original = cfg.model
    try:
        return _do(cfg.model, response_format)
    except Exception as e:
        if "response_format" in str(e) and not _is_model_load_failure(e):
            log.info("Model rejected json_object response_format; retrying as text")
            return _do(cfg.model, None)
        if not _is_model_load_failure(e):
            raise

        log.warning("Model %r failed (%s); attempting recovery.", cfg.model, str(e)[:200])
        # Recovery step 1: try to load the configured model (it may have been
        # unloaded or crashed — reloading it is usually the right fix).
        if _try_load(cfg, original):
            cfg.model = original
            try:
                return _do(cfg.model, response_format)
            except Exception as e2:
                if not _is_model_load_failure(e2):
                    raise
                log.warning("Retry with %r still failed (%s).", original, str(e2)[:200])

        # Recovery step 2: use any *other* model that happens to be loaded
        # (excluding the one that just crashed to avoid a loop).
        loaded = [m for m in _loaded_models(cfg.lms_cli_path) if m != original]
        if loaded:
            log.warning("Falling back to %r already in memory.", loaded[0])
            cfg.model = loaded[0]
            return _do(cfg.model, response_format)
        raise


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
