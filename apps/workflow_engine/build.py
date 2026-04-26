"""BUILD stage: generate an Alpine/Tailwind HTML module from a MechanicSpec.

Two strategies, dispatched by lm_cfg.build_strategy:

- "single" — legacy one-shot: ask the model to emit the entire module as a
  JSON-string field, retry up to MAX_RETRIES with validator-error feedback.
  Fast when the active model can do it in one call (e.g. Qwen 3.6) but small
  local models (e.g. gemma-4-26b-a4b) mode-collapse on the strict-JSON
  ~5KB emit.

- "multi" (default) — deterministic skeleton + per-region fill calls. Each
  region (INPUTS / LOGIC / OUTPUT) is a small (~500-1500 byte) snippet, so
  the model never has to produce the full module in one shot. Validation
  failures trigger targeted re-fills of the implicated region rather than
  full regeneration.
"""
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
from .schemas.json_schema import BUILD_SCHEMA, BUILD_REGION_SCHEMA

log = get("build")

_EXEMPLARS: dict[str, str] = {
    "calculator": CALCULATOR_EXEMPLAR,
    "wizard": WIZARD_EXEMPLAR,
    "drill": DRILL_EXEMPLAR,
    "scorer": SCORER_EXEMPLAR,
    "generator": GENERATOR_EXEMPLAR,
}


def _extract_inner_div(html: str) -> str:
    """Extract the root x-data div from a full-page exemplar for the multi-step path."""
    import re
    m = re.search(r'(<div\s[^>]*x-data="[^"]*"[^>]*>.*?</div>\s*</body>)', html, re.DOTALL)
    if m:
        inner = m.group(1)
        inner = re.sub(r'\s*</body>\s*$', '', inner)
        return inner.strip()
    return html


_EXEMPLAR_REGIONS: dict[str, str] = {
    "calculator": _extract_inner_div(CALCULATOR_EXEMPLAR),
    "wizard": _extract_inner_div(WIZARD_EXEMPLAR),
    "drill": _extract_inner_div(DRILL_EXEMPLAR),
    "scorer": _extract_inner_div(SCORER_EXEMPLAR),
    "generator": _extract_inner_div(GENERATOR_EXEMPLAR),
}

MAX_RETRIES = 3

# Multi-step pipeline regions. Order is the order they appear in the skeleton.
_REGIONS = ("INPUTS", "LOGIC", "OUTPUT")
_REGION_DESCRIPTIONS = {
    "INPUTS": (
        "the form controls the user interacts with — <input>/<select>/<textarea>"
        " elements bound to x-data state via x-model, with labels and Tailwind"
        " styling. No buttons, no result display."
    ),
    "LOGIC": (
        "the action element(s) — at minimum a <button> with @click (or another"
        " event handler) that reads x-data inputs and writes outputs back to"
        " x-data. Inline JS only (no fetch, no XHR, no external network)."
    ),
    "OUTPUT": (
        "the result display — a <template x-if=\"...\"> wrapping a div that shows"
        " the computed output via x-text/x-show. Use <template x-if>, never"
        " <div x-if>."
    ),
}


class BuildFailed(RuntimeError):
    def __init__(self, errors: list[str], attempts: int):
        super().__init__(f"BUILD failed after {attempts} attempt(s): {errors}")
        self.errors = errors
        self.attempts = attempts


def build(spec: MechanicSpec, lm_cfg) -> dict[str, Any]:
    """Generate a validated Alpine/Tailwind HTML module from a MechanicSpec.

    Returns {"html_b64": str, "kind": str, "attempts": int} on success.
    Raises BuildFailed on exhaustion or truncation.

    Strategy is chosen by lm_cfg.build_strategy. Anything other than the
    literal string "multi" routes to the legacy single-call path — this
    keeps MagicMock-based tests on the single path by default.
    """
    if getattr(lm_cfg, "build_strategy", None) == "multi":
        return _build_multi(spec, lm_cfg)
    return _build_single(spec, lm_cfg)


# ---------------------------------------------------------------------------
# Single-call (legacy) path
# ---------------------------------------------------------------------------


def _build_single(spec: MechanicSpec, lm_cfg) -> dict[str, Any]:
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


# ---------------------------------------------------------------------------
# Multi-step path
# ---------------------------------------------------------------------------


def _build_multi(spec: MechanicSpec, lm_cfg) -> dict[str, Any]:
    # Each fill call emits only a small snippet, so a much lower max_tokens
    # ceiling is fine — but we still bump if the caller pinned an absurdly
    # tight budget that wouldn't fit even one region.
    max_tokens = getattr(lm_cfg, "max_tokens", 4096)
    if isinstance(max_tokens, int) and max_tokens < 4096:
        lm_cfg = dataclasses.replace(lm_cfg, max_tokens=4096)

    skeleton = _render_skeleton(spec)
    snippets: dict[str, str] = {r: f"<!-- {r} -->" for r in _REGIONS}

    # Pass 1: fill each region in order. Earlier fills are visible to later
    # calls so the model can pick state names consistent with what it just
    # emitted.
    for region in _REGIONS:
        snippets[region] = _fill_region(spec, lm_cfg, skeleton, snippets, region, prior_errors=None)

    html = _assemble(skeleton, snippets)
    errors = validator.validate_module(html)
    attempts = 1
    prev_errors: frozenset[str] | None = None

    while errors and attempts < MAX_RETRIES:
        attempts += 1
        cur = frozenset(errors)
        if cur == prev_errors:
            log.error("BUILD multi: error set unchanged after attempt %d; aborting early", attempts - 1)
            break
        prev_errors = cur
        target = _pick_region_for_errors(errors)
        log.warning(
            "BUILD multi attempt %d: %d errors, re-filling %s: %s",
            attempts, len(errors), target, errors,
        )
        snippets[target] = _fill_region(
            spec, lm_cfg, skeleton, snippets, target, prior_errors=errors
        )
        html = _assemble(skeleton, snippets)
        errors = validator.validate_module(html)

    if errors:
        raise BuildFailed(list(errors), attempts)

    return {
        "html_b64": base64.b64encode(html.encode("utf-8")).decode("ascii"),
        "kind": spec.kind.value,
        "attempts": attempts,
    }


def _render_skeleton(spec: MechanicSpec) -> str:
    """Deterministically render the structural shell with region markers.

    No LLM call. The skeleton on its own does NOT pass the validator (no
    event handler, no result display) — that's by design; validation runs
    after the fills land.
    """
    state_parts: list[str] = []
    for name in spec.inputs:
        state_parts.append(f"{_js_ident(name)}: ''")
    for name in spec.outputs:
        state_parts.append(f"{_js_ident(name)}: null")
    state_init = ", ".join(state_parts) if state_parts else ""

    title = _html_escape(spec.title)
    return (
        '<!DOCTYPE html>\n'
        '<html lang="en">\n'
        '<head>\n'
        '  <meta charset="UTF-8" />\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0" />\n'
        f'  <title>{title}</title>\n'
        '  <script src="https://cdn.tailwindcss.com"></script>\n'
        '  <script src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js" defer></script>\n'
        '</head>\n'
        '<body class="bg-gray-50 min-h-screen flex items-center justify-center p-4">\n'
        '  <div class="bg-white rounded-2xl shadow-md p-8 w-full max-w-md"\n'
        f'       x-data="{{ {state_init} }}">\n'
        f'    <h1 class="text-2xl font-bold text-gray-800 mb-6">{title}</h1>\n'
        '    <!-- INPUTS -->\n'
        '    <!-- LOGIC -->\n'
        '    <!-- OUTPUT -->\n'
        '  </div>\n'
        '</body>\n'
        '</html>\n'
    )


def _assemble(skeleton: str, snippets: dict[str, str]) -> str:
    html = skeleton
    for region in _REGIONS:
        marker = f"<!-- {region} -->"
        html = html.replace(marker, snippets.get(region, marker), 1)
    return html


def _fill_region(
    spec: MechanicSpec,
    lm_cfg,
    skeleton: str,
    snippets: dict[str, str],
    region: str,
    prior_errors: list[str] | None,
) -> str:
    """Ask the model for one region's snippet. Returns the snippet HTML."""
    system = _fill_system_prompt(spec, region)
    user = _fill_user_prompt(spec, skeleton, snippets, region, prior_errors)

    try:
        raw, finish_reason = lm_studio.chat_json_with_meta(
            lm_cfg, system=system, user=user, schema=BUILD_REGION_SCHEMA, task="build"
        )
    except ValueError as e:
        log.warning("BUILD multi: malformed JSON filling %s: %s", region, e)
        # Return the marker unchanged so the caller's validator picks up the
        # missing region as a normal validation error and re-fill cycles run.
        return f"<!-- {region} -->"

    if finish_reason == "length":
        log.warning("BUILD multi: finish_reason=length filling %s", region)
        # Don't raise here — let the validator decide. A truncated snippet
        # will surface as a structural error and trigger a re-fill.

    snippet = raw.get("snippet", "")
    if not isinstance(snippet, str):
        return f"<!-- {region} -->"
    return snippet.strip()


def _fill_system_prompt(spec: MechanicSpec, region: str) -> str:
    kind_str = spec.kind.value
    exemplar = _EXEMPLAR_REGIONS[kind_str]
    return (
        "You generate one fragment of a self-contained Alpine.js v3 + Tailwind"
        " CSS interactive module. The surrounding skeleton (DOCTYPE, head with"
        " CDNs, body, root x-data element) is already built — DO NOT include"
        " any of those.\n\n"
        "Rules for your snippet:\n"
        "- HTML fragment only. No <html>, <head>, <body>, <script src=...>, or"
        " <!DOCTYPE>.\n"
        "- Reference x-data state by the same names declared in the skeleton.\n"
        "- Use <template x-if> NEVER <div x-if>.\n"
        "- No TODO, FIXME, placeholder, or stub code.\n"
        "- No fetch() or XHR to external domains. No ellipsis (...) in script.\n"
        "- No x-html directive. Use x-text for inserted content.\n"
        "\n"
        "Visual quality rules:\n"
        "- Use a single accent color family (e.g. blue+slate, emerald+teal,"
        " amber+stone, rose+warm-gray). Apply consistently.\n"
        "- NEVER use purple (#8b5cf6/#7c3aed), fuchsia (#d946ef), or combinations"
        " of cyan+magenta+pink — they signal low-quality generated output.\n"
        "- NEVER use gradient text (bg-clip-to-text). NEVER use animated glowing"
        " box-shadows. NEVER use emoji in visible text.\n"
        "- Ensure visual hierarchy: the title should be most prominent, then"
        " inputs, then action, then results. Vary sizes and weights.\n"
        "\n"
        f"For reference, here is a complete Alpine/Tailwind {kind_str}:\n\n"
        f"{exemplar}\n\n"
        f'Return a single JSON object: {{"snippet": "<your HTML fragment>"}}.'
    )


def _fill_user_prompt(
    spec: MechanicSpec,
    skeleton: str,
    snippets: dict[str, str],
    region: str,
    prior_errors: list[str] | None,
) -> str:
    current = _assemble(skeleton, snippets)
    desc = _REGION_DESCRIPTIONS[region]
    parts = [
        f"Title: {spec.title}",
        f"Intent: {spec.intent}",
        f"Inputs: {', '.join(spec.inputs)}",
        f"Outputs: {', '.join(spec.outputs)}",
        "",
        "Current module so far (other regions may already be filled in):",
        "```html",
        current,
        "```",
        "",
        f"Produce only the {region} region. It is {desc}",
    ]
    if prior_errors:
        parts.extend([
            "",
            "The previous attempt produced these validation errors. Fix them:",
            *(f"- {e}" for e in prior_errors),
        ])
    return "\n".join(parts)


def _pick_region_for_errors(errors: list[str]) -> str:
    """Map a validator error set to the region most likely responsible."""
    blob = " ".join(errors).lower()
    if "event handler" in blob or "external fetch" in blob or "ellipsis" in blob:
        return "LOGIC"
    if "x-if used on <div>" in blob or "x-html" in blob:
        return "OUTPUT"
    if "shorter than 800 bytes" in blob:
        # Module is too thin overall — fill OUTPUT, which tends to add the most
        # body-text bytes (result display + labels).
        return "OUTPUT"
    if "stub phrase" in blob:
        return "LOGIC"
    # Skeleton-level structural errors (missing x-data / missing CDN) shouldn't
    # happen because the skeleton is deterministic; if they do, retrying LOGIC
    # is cheap and harmless.
    return "LOGIC"


def _js_ident(name: str) -> str:
    """Coerce a spec input/output name into a safe JS identifier."""
    cleaned = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
    if not cleaned or not (cleaned[0].isalpha() or cleaned[0] == "_"):
        cleaned = "_" + cleaned
    return cleaned


def _html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
    )


# ---------------------------------------------------------------------------
# Single-call prompts (kept for the legacy "single" strategy)
# ---------------------------------------------------------------------------


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
        "- No fetch() or XHR to external domains\n"
        "\n"
        "Visual quality rules:\n"
        "- Pick one accent color family and apply consistently (blue+slate, emerald+teal, amber+stone, rose+warm-gray).\n"
        "- NEVER use purple (#8b5cf6/#7c3aed), fuchsia (#d946ef), or cyan+magenta+pink combinations.\n"
        "- NEVER use gradient text, animated glowing shadows, or emoji in visible text.\n"
        "- Establish visual hierarchy: title most prominent, then inputs, then action, then results.\n"
        "\n"
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
