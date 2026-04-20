"""Pydantic discriminated union for mechanic content — one class per kind."""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class CalculatorVariable(BaseModel):
    name: str
    unit: str
    default: float | int | str = ""


class CalculatorContent(BaseModel):
    kind: Literal["calculator"] = "calculator"
    formula_description: str
    variables: list[CalculatorVariable] = Field(min_length=1)
    unit: str


class WizardStep(BaseModel):
    title: str
    prompt: str
    input_type: str


class WizardContent(BaseModel):
    kind: Literal["wizard"] = "wizard"
    steps: list[WizardStep] = Field(min_length=2, max_length=8)


class DrillContent(BaseModel):
    kind: Literal["drill"] = "drill"
    question: str
    answer: str
    hint: str = ""


class ScorerDimension(BaseModel):
    name: str
    weight: float
    rubric: str


class ScorerContent(BaseModel):
    kind: Literal["scorer"] = "scorer"
    dimensions: list[ScorerDimension] = Field(min_length=1)
    scale: int = 10


class GeneratorParameter(BaseModel):
    name: str
    description: str


class GeneratorContent(BaseModel):
    kind: Literal["generator"] = "generator"
    template: str
    parameters: list[GeneratorParameter] = Field(min_length=1)


AnyContent = Annotated[
    Union[CalculatorContent, WizardContent, DrillContent, ScorerContent, GeneratorContent],
    Field(discriminator="kind"),
]
