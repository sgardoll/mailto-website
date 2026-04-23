"""Convert normalized_input to MechanicSpec via LM Studio json_schema structured output."""
from __future__ import annotations

import re
from typing import Any

from jsonschema import validate, ValidationError as JsonSchemaError
from pydantic import ValidationError as PydanticValidationError

from . import lm_studio
from .logging_setup import get
from packages.config_contract import MechanicKind
from .schemas.envelope import MechanicSpec
from .schemas.json_schema import DISTILL_SCHEMA
from .schemas.mechanic_content import GeneratorContent, GeneratorParameter

log = get("distill")


class DistillFailed(RuntimeError):
    pass


def distill(normalized_input: dict[str, Any], lm_cfg) -> MechanicSpec:
    """Convert normalized_input to a MechanicSpec. Never returns None — if the
    model tries to skip informational content, we retry with a forcing prompt
    that demands *some* interactive mechanic (usually a generator).
    """
    source_type = normalized_input.get("source_type", "text")
    system = _build_system_prompt(source_type)
    user = _build_user_prompt(normalized_input)
    source_url = normalized_input.get("source_url")

    # Attempt 1: normal prompt.
    spec = _try_once(lm_cfg, system, user, source_url)
    if spec is not None:
        return spec

    # Attempt 2: force a mechanic out of informational content.
    log.warning("DISTILL attempt 1 returned null; retrying with forcing prompt.")
    force_system = _build_forcing_system_prompt(source_type)
    spec = _try_once(lm_cfg, force_system, user, source_url)
    if spec is not None:
        return spec

    # Attempt 3: generic generator mechanic as last resort — never return null.
    log.warning("DISTILL attempt 2 still returned null; using generator fallback.")
    last_system = _build_forcing_system_prompt(source_type) + (
        " Kind MUST be 'generator'. Make a mechanic that generates a themed "
        "variation, quote, or summary from the content each time it is used."
    )
    spec = _try_once(lm_cfg, last_system, user, source_url)
    if spec is not None:
        return spec

    # Final fallback: hand-craft a generator mechanic in code. The model
    # couldn't produce anything usable, but we refuse to drop the email.
    log.warning("DISTILL attempt 3 failed; hand-crafting a generator mechanic.")
    return _hand_crafted_fallback(normalized_input, source_url)


def _hand_crafted_fallback(ni: dict[str, Any], source_url: str | None) -> MechanicSpec:
    """Build a generic 'content card' generator spec when the LM gives up.

    Presents the original content as a themed card with a "new view" button
    that cycles through excerpts. Non-interactive-ish, but it's a valid module.
    """
    subject = (ni.get("subject") or "Inbound content").strip()[:80] or "Inbound content"
    body = (ni.get("body") or "").strip()[:800] or source_url or "(no content)"
    return MechanicSpec(
        kind=MechanicKind.GENERATOR,
        title=subject,
        intent=f"Surface an excerpt from: {subject}",
        inputs=["trigger"],
        outputs=["excerpt"],
        content=GeneratorContent(
            template=body,
            parameters=[GeneratorParameter(
                name="trigger",
                description="Click to show a fresh excerpt from the content.",
            )],
        ),
        source_url=source_url,
    )


def _try_once(lm_cfg, system: str, user: str, source_url: str | None) -> MechanicSpec | None:
    raw = lm_studio.chat_json(lm_cfg, system=system, user=user, schema=DISTILL_SCHEMA)
    try:
        return _parse_and_validate(raw, source_url)
    except (JsonSchemaError, PydanticValidationError, ValueError) as e:
        log.warning("DISTILL validation failed: %s", e)
        user_retry = user + f"\n\nPrevious attempt failed: {e}\nPlease fix and retry."
        raw2 = lm_studio.chat_json(lm_cfg, system=system, user=user_retry, schema=DISTILL_SCHEMA)
        try:
            return _parse_and_validate(raw2, source_url)
        except (JsonSchemaError, PydanticValidationError, ValueError) as e2:
            log.warning("DISTILL validation failed on retry: %s", e2)
            return None


def _parse_and_validate(raw: dict, source_url: str | None) -> MechanicSpec | None:
    validate(instance=raw, schema=DISTILL_SCHEMA)
    if raw.get("mechanic") is None:
        return None
    spec = MechanicSpec.model_validate(raw["mechanic"])
    if source_url and not spec.source_url:
        spec.source_url = source_url
    if not spec.module_id:
        spec.module_id = _slugify(spec.title)
    return spec


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:64] or "module"


def _build_system_prompt(source_type: str) -> str:
    source_hint = {
        "video": "The content is from a video transcript.",
        "article": "The content is from a web article.",
        "text": "The content is plain email text.",
    }.get(source_type, "")
    return (
        f"You are an expert at extracting interactive mechanic specifications from user content. "
        f"{source_hint} "
        "Respond with a single JSON object describing an interactive mechanic derived from the content. "
        "kind must be one of: calculator, wizard, drill, scorer, generator. "
        "content.kind MUST match the outer kind field. "
        "Prefer to produce a mechanic. Only set mechanic to null as an absolute last resort."
    )


def _build_forcing_system_prompt(source_type: str) -> str:
    source_hint = {
        "video": "The content is from a video transcript.",
        "article": "The content is from a web article.",
        "text": "The content is plain email text.",
    }.get(source_type, "")
    return (
        f"You are an expert at turning arbitrary content into interactive mechanics. "
        f"{source_hint} "
        "The previous attempt returned null — that is NOT acceptable here. "
        "You MUST produce a mechanic, even if the content is informational. "
        "If the content is news/announcements/FYI, build a 'generator' mechanic "
        "that surfaces a themed quote, fact, or summary from the material. "
        "If it lists steps or decisions, build a 'wizard'. If it involves numbers, "
        "build a 'calculator'. If it involves quiz-style recall, build a 'drill'. "
        "If it involves judging something, build a 'scorer'. "
        "kind must be one of: calculator, wizard, drill, scorer, generator. "
        "content.kind MUST match the outer kind field. "
        "mechanic MUST NOT be null."
    )


def _build_user_prompt(ni: dict[str, Any]) -> str:
    body = (ni.get("body") or "")[:12000]
    lines = [
        f"Subject: {ni.get('subject', '')}",
        f"From: {ni.get('sender', '')}",
        f"Source type: {ni.get('source_type', 'text')}",
    ]
    if ni.get("source_url"):
        lines.append(f"Source URL: {ni['source_url']}")
    lines.extend(["", "Content:", body])
    return "\n".join(lines)
