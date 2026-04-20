"""Catalogue of LM-Studio-viable models, mapped to OpenRouter slugs.

Only models that fit on an Apple-Silicon M4-class MacBook Pro (>=36 GB unified
memory) are listed. The OpenRouter slug is the default the UI sends; the user
can override it in the form before a run, because OpenRouter occasionally
renames identifiers.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    label: str
    lm_studio_hint: str
    openrouter_slug: str
    notes: str = ""


CATALOGUE: list[ModelSpec] = [
    ModelSpec(
        label="Qwen3-Coder-30B-A3B (Q4_K_M)",
        lm_studio_hint="qwen/qwen3-coder-30b-a3b",
        openrouter_slug="qwen/qwen3-coder-30b-a3b-instruct",
        notes="MoE 30B, 3B active. Fast on M4 Pro/Max.",
    ),
    ModelSpec(
        label="Qwen3-Coder-14B (Q4_K_M or Q6_K)",
        lm_studio_hint="qwen/qwen3-coder-14b",
        openrouter_slug="qwen/qwen3-coder-14b-instruct",
        notes="Dense 14B. Strong small coder baseline.",
    ),
    ModelSpec(
        label="Gemma 4 26B A4B",
        lm_studio_hint="google/gemma-4-26b-a4b",
        openrouter_slug="google/gemma-4-26b-a4b",
        notes="Google MoE; good instruction following.",
    ),
    ModelSpec(
        label="Devstral-Small-2507",
        lm_studio_hint="mistralai/devstral-small-2507",
        openrouter_slug="mistralai/devstral-small-2507",
        notes="Mistral code/agent small. JSON-friendly.",
    ),
    ModelSpec(
        label="Kimi K2.5",
        lm_studio_hint="moonshotai/kimi-k2.5",
        openrouter_slug="moonshotai/kimi-k2.5",
        notes="Moonshot flagship-small variant.",
    ),
]


def by_label(label: str) -> ModelSpec | None:
    for m in CATALOGUE:
        if m.label == label:
            return m
    return None
