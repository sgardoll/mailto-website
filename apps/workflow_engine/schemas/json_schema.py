"""DISTILL_SCHEMA dict — passed as the schema kwarg to chat_json."""
from __future__ import annotations

from .envelope import MechanicSpec

DISTILL_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "mechanic": {
            "oneOf": [
                MechanicSpec.model_json_schema(),
                {"type": "null"},
            ]
        },
        "skip_reason": {"type": "string"},
    },
    "required": ["mechanic"],
}
