"""MechanicSpec envelope and RoutingDecision — shared data contracts."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self

from packages.config_contract import MechanicKind
from .mechanic_content import AnyContent


class MechanicSpec(BaseModel):
    kind: MechanicKind
    title: str
    intent: str
    inputs: list[str]
    outputs: list[str]
    content: AnyContent
    module_id: str = ""
    reads_state: list[str] = Field(default_factory=list)
    writes_state: list[str] = Field(default_factory=list)
    delight_mechanic: str = ""
    source_url: str | None = None

    @model_validator(mode="after")
    def _kind_matches_content(self) -> Self:
        if self.kind.value != self.content.kind:
            raise ValueError(
                f"MechanicSpec.kind={self.kind!r} does not match content.kind={self.content.kind!r}"
            )
        return self


RoutingDecision = Literal["new_module", "extend_module", "upgrade_state_only"]


class AiCall(BaseModel):
    stage: str
    model: str
    decision: str
    rationale: str
    manifest_snapshot: list[dict]
