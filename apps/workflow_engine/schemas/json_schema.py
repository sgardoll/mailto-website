"""DISTILL_SCHEMA and BUILD_SCHEMA dicts — passed as the schema kwarg to chat_json."""
from __future__ import annotations

import copy

from .envelope import MechanicSpec

# Hoist $defs to root so that $ref pointers (#/$defs/...) within the embedded
# MechanicSpec schema resolve correctly when jsonschema.validate() uses this
# as the document root.
_spec_schema = copy.deepcopy(MechanicSpec.model_json_schema())
_spec_defs = _spec_schema.pop("$defs", {})

# LM Studio's structured-output mode only emits fields listed in "required".
# Pydantic omits `kind` from required because it has a default, but the
# discriminated-union validator needs it present in the JSON. Force it.
_CONTENT_DEFS = {"CalculatorContent", "WizardContent", "DrillContent", "ScorerContent", "GeneratorContent"}
for _name, _def in _spec_defs.items():
    if _name in _CONTENT_DEFS and "kind" not in _def.get("required", []):
        _def.setdefault("required", []).insert(0, "kind")

DISTILL_SCHEMA: dict = {
    "type": "object",
    "$defs": _spec_defs,
    "properties": {
        "mechanic": {
            "oneOf": [
                _spec_schema,
                {"type": "null"},
            ]
        },
        "skip_reason": {"type": "string"},
    },
    "required": ["mechanic"],
}

BUILD_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "html": {"type": "string"},
    },
    "required": ["html"],
}

# Used by the multi-step BUILD pipeline for per-region fill calls. Each call
# emits only a small HTML snippet (~500-1500 bytes) for one labeled region,
# so the model never has to produce the full ~5KB module in one shot.
BUILD_REGION_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "snippet": {"type": "string"},
    },
    "required": ["snippet"],
}
