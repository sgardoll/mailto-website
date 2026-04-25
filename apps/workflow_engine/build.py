"""BUILD stage: generate an Alpine/Tailwind HTML module from a MechanicSpec."""
from __future__ import annotations

import base64
import dataclasses
from typing import Any

from . import lm_studio, validator
from .exemplars import (
    CALCULATOR_EXEMPLAR,
    WIZARD_EXEMPLAR,
    DRILL_EXEMPLAR,
    SCORER_EXEMPLAR,
    GENERATOR_EXEMPLAR,
)
from .logging_setup import get
from .schemas.envelope import MechanicSpec
from .schemas.json_schema import BUILD_SCHEMA

log = get("build")

_EXEMPLARS: dict[str, str] = {
    "calculator": CALCULATOR_EXEMPLAR,
    "wizard": WIZARD_EXEMPLAR,
    "drill": DRILL_EXEMPLAR,
    "scorer": SCORER_EXEMPLAR,
    "generator": GENERATOR_EXEMPLAR,
}

MAX_RETRIES = 3


class BuildFailed(RuntimeError):
    def __init__(self, errors: list[str], attempts: int):
        super().__init__(f"BUILD failed after {attempts} attempt(s): {errors}")
        self.errors = errors
        self.attempts = attempts


def build(spec: MechanicSpec, lm_cfg) -> dict[str, Any]:
    """Generate a validated Alpine/Tailwind HTML module from a MechanicSpec.

    Returns {"html_b64": str, "kind": str, "attempts": int} on success.
    Raises BuildFailed on exhaustion or truncation.
    """
    # Enforce min max_tokens without mutating caller's config
    max_tokens = getattr(lm_cfg, "max_tokens", 8000)
    if isinstance(max_tokens, int) and max_tokens < 8000:
        lm_cfg = dataclasses.replace(lm_cfg, max_tokens=8000)

    system = _build_system_prompt(spec)
    user = _build_user_prompt(spec)
    prev_errors: frozenset[str] | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            raw, finish_reason = lm_studio.chat_json_with_meta(
                lm_cfg, system=system, user=user, schema=BUILD_SCHEMA, task="build"
            )
        except ValueError as e:
            # Model emitted malformed JSON (JSONDecodeError is a ValueError).
            # Treat as a build failure and retry with feedback.
            log.warning("BUILD attempt %d: model returned malformed JSON: %s", attempt, e)
            if attempt >= MAX_RETRIES:
                raise BuildFailed([f"malformed JSON after {MAX_RETRIES} attempts: {e}"], attempt)
            user = (
                user
                + f"\n\nPrevious attempt returned malformed JSON: {e}\n"
                + "Please return a single valid JSON object only — no thinking, no prose, no truncation."
            )
            continue
        if finish_reason == "length":
            raise BuildFailed(["finish_reason=length: output truncated"], attempt)
        html = raw.get("html", "")
        errors = validator.validate_module(html)
        if not errors:
            return {
                "html_b64": base64.b64encode(html.encode("utf-8")).decode("ascii"),
                "kind": spec.kind.value,
                "attempts": attempt,
            }
        cur_errors = frozenset(errors)
        if cur_errors == prev_errors:
            log.error("BUILD error set unchanged after attempt %d; aborting early", attempt)
            raise BuildFailed(list(cur_errors), attempt)
        prev_errors = cur_errors
        log.warning("BUILD attempt %d failed (%d errors): %s", attempt, len(errors), errors)
        if attempt < MAX_RETRIES:
            user = (
                user
                + "\n\nPrevious attempt produced invalid HTML. Errors:\n"
                + "\n".join(f"- {e}" for e in errors)
                + "\nPlease fix all issues and return valid HTML."
            )

    raise BuildFailed(errors, MAX_RETRIES)


def _build_system_prompt(spec: MechanicSpec) -> str:
    kind_str = spec.kind.value
    exemplar = _EXEMPLARS[kind_str]
    return (
        "You generate self-contained Alpine.js v3 + Tailwind CSS interactive modules.\n"
        "Rules:\n"
        "- Use Alpine.js CDN: https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js (with defer)\n"
        "- Use Tailwind CDN: https://cdn.tailwindcss.com\n"
        "- Include x-data on the root element\n"
        "- Include at least one @click or x-on: event handler\n"
        "- Use <template x-if> NOT <div x-if>\n"
        "- No TODO, FIXME, placeholder, or stub code\n"
        "- No fetch() or XHR to external domains\n\n"
        f"Here is a reference Alpine/Tailwind module for {kind_str}:\n\n"
        f"{exemplar}\n\n"
        'Return a single JSON object with one field: "html" containing the complete HTML as a string.'
    )


def _build_user_prompt(spec: MechanicSpec) -> str:
    lines = [
        f"Title: {spec.title}",
        f"Intent: {spec.intent}",
        f"Inputs: {', '.join(spec.inputs)}",
        f"Outputs: {', '.join(spec.outputs)}",
        "",
        "Generate a complete, valid, self-contained Alpine.js + Tailwind HTML module.",
    ]
    return "\n".join(lines)
