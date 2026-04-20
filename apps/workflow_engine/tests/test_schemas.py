"""Unit tests for apps/workflow_engine/schemas/ package."""
from __future__ import annotations

import subprocess
import sys

import pytest
from pydantic import ValidationError

from apps.workflow_engine.schemas import MechanicSpec, AnyContent
from apps.workflow_engine.schemas.mechanic_content import (
    CalculatorContent,
    WizardContent,
    DrillContent,
    ScorerContent,
    GeneratorContent,
    CalculatorVariable,
    WizardStep,
    ScorerDimension,
    GeneratorParameter,
)
from apps.workflow_engine.schemas.json_schema import DISTILL_SCHEMA
from packages.config_contract import MechanicKind


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_calculator_content():
    return CalculatorContent(
        formula_description="BMI = weight / height^2",
        variables=[CalculatorVariable(name="weight", unit="kg", default=70)],
        unit="kg/m²",
    )


def _make_wizard_content():
    return WizardContent(
        steps=[
            WizardStep(title="Step 1", prompt="Enter name", input_type="text"),
            WizardStep(title="Step 2", prompt="Enter age", input_type="number"),
        ]
    )


def _make_mechanic_spec(kind, content):
    return MechanicSpec(
        kind=kind,
        title="Test",
        intent="testing",
        inputs=["email"],
        outputs=["html"],
        content=content,
    )


# ── MechanicSpec validation ───────────────────────────────────────────────────

def test_mechanic_spec_calculator_validates():
    content = _make_calculator_content()
    spec = _make_mechanic_spec(MechanicKind.CALCULATOR, content)
    assert spec.kind == MechanicKind.CALCULATOR
    assert spec.content.kind == "calculator"


def test_mechanic_spec_kind_content_mismatch_raises():
    calculator_content = _make_calculator_content()
    with pytest.raises(ValueError, match="does not match content.kind"):
        _make_mechanic_spec(MechanicKind.WIZARD, calculator_content)


# ── WizardContent constraints ─────────────────────────────────────────────────

def test_wizard_content_empty_steps_raises():
    with pytest.raises(ValidationError):
        WizardContent(steps=[])


def test_wizard_content_nine_steps_raises():
    steps = [WizardStep(title=f"Step {i}", prompt="p", input_type="text") for i in range(9)]
    with pytest.raises(ValidationError):
        WizardContent(steps=steps)


# ── CalculatorContent constraints ─────────────────────────────────────────────

def test_calculator_content_empty_variables_raises():
    with pytest.raises(ValidationError):
        CalculatorContent(formula_description="x", variables=[], unit="kg")


# ── Default values ────────────────────────────────────────────────────────────

def test_scorer_content_default_scale():
    content = ScorerContent(
        dimensions=[ScorerDimension(name="clarity", weight=1.0, rubric="clear text")]
    )
    assert content.scale == 10


def test_drill_content_default_hint():
    content = DrillContent(question="What is 2+2?", answer="4")
    assert content.hint == ""


# ── DISTILL_SCHEMA structure ──────────────────────────────────────────────────

def test_distill_schema_is_dict_with_top_level_keys():
    assert isinstance(DISTILL_SCHEMA, dict)
    assert {"type", "properties", "required"}.issubset(DISTILL_SCHEMA.keys())


def test_distill_schema_mechanic_oneof_has_two_entries():
    one_of = DISTILL_SCHEMA["properties"]["mechanic"]["oneOf"]
    assert len(one_of) == 2
    # One should be an object (MechanicSpec schema), one should be {"type": "null"}
    types = [entry.get("type") for entry in one_of]
    assert "null" in types


# ── Import cleanliness ────────────────────────────────────────────────────────

def test_schemas_package_exports_correctly():
    from apps.workflow_engine.schemas import MechanicSpec, RoutingDecision, AiCall, AnyContent  # noqa: F401


def test_schemas_package_does_not_import_lm_studio():
    import pathlib
    # Run subprocess from the worktree root so 'apps' package is importable
    worktree_root = pathlib.Path(__file__).parent.parent.parent.parent
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import apps.workflow_engine.schemas; "
                "import sys; "
                "assert 'apps.workflow_engine.lm_studio' not in sys.modules, "
                "'lm_studio was imported'"
            ),
        ],
        capture_output=True,
        text=True,
        cwd=str(worktree_root),
    )
    assert result.returncode == 0, result.stderr
