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
    """Build the `lms load` argv using cfg defaults."""
    return _load_args_at(cfg.lms_cli_path, model, cfg.context_length, cfg.gpu_offload, cfg.ttl_seconds)


def _load_args_at(
    cli: str, model: str, ctx: int | None, gpu: str | None, ttl: int | None
) -> list[str]:
    """Build `lms load` argv with explicit context_length / gpu / ttl overrides."""
    args = [cli, "load", model, "--yes"]
    if ctx is not None:
        args += ["-c", str(ctx)]
    if gpu is not None:
        args += ["--gpu", gpu]
    if ttl is not None:
        args += ["--ttl", str(ttl)]
    return args


class LmStudioEstimateRefused(LmStudioUnavailable):
    """Raised when no (model, context) combo fits under LM Studio's guardrails."""


# Below this context, distill/build prompts almost always overflow at runtime,
# so loading the model only to fail on the first call is wasted work.
_LOAD_CONTEXT_FLOOR = 2048


def _estimate_load(cfg: LmStudioConfig, model: str) -> tuple[bool, str]:
    """Run `lms load --estimate-only` for cfg defaults. Kept for backward compat."""
    return _estimate_load_at(cfg.lms_cli_path, model, cfg.context_length, cfg.gpu_offload, cfg.ttl_seconds)


def _estimate_load_at(
    cli: str, model: str, ctx: int | None, gpu: str | None, ttl: int | None
) -> tuple[bool, str]:
    """Run `lms load --estimate-only` for an explicit (model, ctx) combo.

    Returns (will_fit, summary). On any tooling error, returns (True, "") so
    the caller falls through to the real load — we don't want a flaky
    estimator to block legitimate loads.
    """
    if not shutil.which(cli):
        return True, ""
    args = _load_args_at(cli, model, ctx, gpu, ttl) + ["--estimate-only"]
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=30)
    except (subprocess.TimeoutExpired, OSError):
        return True, ""
    summary = ((r.stdout or "") + (r.stderr or "")).strip()
    if "will fail to load" in summary.lower():
        return False, summary
    return True, summary


def _list_downloaded_models(cli: str) -> list[tuple[str, int]]:
    """Return [(modelKey, sizeBytes), ...] sorted by size DESCENDING.

    Largest-first ordering means the smart-load fallback picks the biggest
    model that still fits under guardrails — better answer quality than
    auto-falling-back to a 1B model when a 4B would fit. Embedding-only
    models are filtered out.
    """
    if not shutil.which(cli):
        return []
    try:
        r = subprocess.run([cli, "ls", "--json"], capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            return []
        data = json.loads(r.stdout or "[]")
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return []
    out: list[tuple[str, int]] = []
    for m in data:
        key = m.get("modelKey")
        if not key:
            continue
        if (m.get("type") or "").lower() == "embedding":
            continue
        if "embed" in key.lower():
            continue
        out.append((key, int(m.get("sizeBytes") or 0)))
    out.sort(key=lambda x: x[1], reverse=True)
    return out


def _candidate_contexts(start: int | None) -> list[int]:
    """Decreasing context lengths to attempt.

    Starts at the user's configured value (or 8192 default), then halves down
    to `_LOAD_CONTEXT_FLOOR`. If the user explicitly chose a value below the
    floor, that's the only candidate — we honour the user's intent rather than
    silently raising it.
    """
    base = start or 8192
    out = [base]
    val = base
    while val // 2 >= _LOAD_CONTEXT_FLOOR:
        val //= 2
        if val not in out:
            out.append(val)
    return out


def _attempt_load(
    cfg: LmStudioConfig, model: str, ctx: int, wait_s: int = 60, *, use_estimate: bool = True
) -> bool:
    """Estimate then load (model, ctx). Returns True iff model is in memory afterwards.

    `use_estimate=False` skips the `--estimate-only` preflight. Used for the
    user's preferred model — the estimator is conservative and false-rejects
    models that actually load fine. The `context_length` cap still protects
    against runaway loads regardless.
    """
    if use_estimate and cfg.estimate_before_load:
        will_fit, summary = _estimate_load_at(
            cfg.lms_cli_path, model, ctx, cfg.gpu_offload, cfg.ttl_seconds
        )
        if not will_fit:
            log.info("skip %s @ ctx=%d (estimator: won't fit)", model, ctx)
            return False
        if summary:
            log.debug("estimate %s @ ctx=%d:\n%s", model, ctx, summary)
    args = _load_args_at(cfg.lms_cli_path, model, ctx, cfg.gpu_offload, cfg.ttl_seconds)
    log.info("loading: %s", " ".join(args))
    subprocess.run(args, capture_output=True, text=True)
    for _ in range(wait_s):
        if model in _loaded_models(cfg.lms_cli_path):
            return True
        time.sleep(1)
    return False


def _smart_load(cfg: LmStudioConfig, primary_model: str) -> str | None:
    """Cascading fallback: primary model at decreasing contexts, then alternates.

    Returns the model name that ended up loaded, or None if nothing fit.
    Mutation of cfg.model is left to the caller so tests can assert behaviour.
    """
    contexts = _candidate_contexts(cfg.context_length)
    log.info("smart-load: trying %s at contexts %s, then fallbacks", primary_model, contexts)

    # Primary model: skip estimator. The user picked this model; honour the
    # choice and let an actual load attempt decide. context_length cap keeps
    # the load bounded regardless.
    for ctx in contexts:
        if _attempt_load(cfg, primary_model, ctx, use_estimate=False):
            log.info("loaded primary %s at ctx=%d", primary_model, ctx)
            return primary_model

    log.warning(
        "primary %s did not load at any ctx in %s; trying alternate downloaded models",
        primary_model, contexts,
    )
    # Alternates: keep estimator on so we don't waste 30+ seconds attempting
    # 25 models the estimator can quickly rule out.
    for alt, size in _list_downloaded_models(cfg.lms_cli_path):
        if alt == primary_model:
            continue
        for ctx in contexts:
            if _attempt_load(cfg, alt, ctx):
                log.warning(
                    "fell back to %s (%.2f GB) at ctx=%d — primary %s did not load",
                    alt, size / 1e9, ctx, primary_model,
                )
                return alt

    return None


def ensure_running(cfg: LmStudioConfig) -> None:
    """Ensure an LM is usable. Mutates cfg.model if a fallback model is chosen.

    Resilience policy: prefer the user's originally-configured model
    (`cfg.preferred_model`), then any in-memory alternate, then a smart-load
    cascade. cfg.model is mutated to whatever ended up usable.

    Without preferred_model tracking, once cfg.model gets mutated to an
    in-memory alternate (e.g. a tiny Qwen variant the user manually loaded),
    later runs would never reconsider the user's preferred big model — even
    after the alternate gets unloaded.
    """
    preferred = cfg.preferred_model or cfg.model
    loaded = _loaded_models(cfg.lms_cli_path) if _server_alive(cfg.base_url) else []

    if preferred in loaded:
        cfg.model = preferred
        return

    if loaded:
        log.warning(
            "Preferred model %r is not loaded in LM Studio; falling back to %r (already in memory).",
            preferred, loaded[0],
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
    loaded_model = _smart_load(cfg, preferred)
    if loaded_model is not None:
        cfg.model = loaded_model
        return
    raise LmStudioEstimateRefused(
        f"Could not load any downloaded model under LM Studio's resource "
        f"guardrails. Tried {cfg.model!r} and all alternates at contexts "
        f"down to {_LOAD_CONTEXT_FLOOR}. Raise the guardrails in LM Studio "
        f"Settings → Hardware, free up GPU memory, or download a smaller model."
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
    """Recovery reload after a runtime crash. Routes through smart-load so a
    crashed primary can degrade to a smaller context or fall back to an
    alternate downloaded model.

    Mutates cfg.model if smart-load picks an alternate. Returns True iff
    *something* ended up loaded.
    """
    del wait_s  # smart-load owns its own per-attempt timeout
    if not shutil.which(cfg.lms_cli_path):
        return False
    loaded_model = _smart_load(cfg, model)
    if loaded_model is None:
        return False
    cfg.model = loaded_model
    return True


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
