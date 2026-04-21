"""Convert normalized_input to MechanicSpec via LM Studio json_schema structured output."""
from __future__ import annotations

import re
from typing import Any

from jsonschema import validate, ValidationError as JsonSchemaError
from pydantic import ValidationError as PydanticValidationError

from . import lm_studio
from .logging_setup import get
from .schemas.envelope import MechanicSpec
from .schemas.json_schema import DISTILL_SCHEMA

log = get("distill")


class DistillFailed(RuntimeError):
    pass


def distill(normalized_input: dict[str, Any], lm_cfg) -> MechanicSpec | None:
    """Convert normalized_input to MechanicSpec. Returns None for informational emails (D-13)."""
    source_type = normalized_input.get("source_type", "text")
    system = _build_system_prompt(source_type)
    user = _build_user_prompt(normalized_input)
    raw = lm_studio.chat_json(lm_cfg, system=system, user=user, schema=DISTILL_SCHEMA)
    try:
        return _parse_and_validate(raw, normalized_input.get("source_url"))
    except (JsonSchemaError, PydanticValidationError, ValueError) as e:
        log.warning("DISTILL validation failed (attempt 1): %s", e)
        user_retry = user + f"\n\nPrevious attempt failed: {e}\nPlease fix and retry."
        raw2 = lm_studio.chat_json(lm_cfg, system=system, user=user_retry, schema=DISTILL_SCHEMA)
        try:
            return _parse_and_validate(raw2, normalized_input.get("source_url"))
        except (JsonSchemaError, PydanticValidationError, ValueError) as e2:
            log.error("DISTILL validation failed (attempt 2): %s", e2)
            raise DistillFailed(str(e2)) from e2


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
        "Respond with a single JSON object. "
        "Set mechanic to null and supply skip_reason if the content is purely informational "
        "(announcements, news summaries, FYI updates) and does not describe an interactive mechanic. "
        "kind must be one of: calculator, wizard, drill, scorer, generator. "
        "content.kind MUST match the outer kind field."
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
