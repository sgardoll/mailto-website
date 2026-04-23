"""Pytest configuration for apps.workflow_engine tests.

Registers the `requires_lm` marker used by real-LM integration tests
(e.g. test_e2e_pipeline.py, test_browser_smoke.py). CI runs with
`pytest -m 'not requires_lm'` to skip these tests automatically.
"""
from __future__ import annotations

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "requires_lm: mark test as requiring a live LM Studio instance (skipped in CI)",
    )
