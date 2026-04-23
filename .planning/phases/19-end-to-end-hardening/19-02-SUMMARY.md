---
phase: 19-end-to-end-hardening
plan: "02"
subsystem: workflow_engine/tests
tags:
  - testing
  - e2e
  - integration
  - lm-studio
  - pytest
dependency_graph:
  requires:
    - "19-01 (conftest.py + pytest.ini marker registration)"
  provides:
    - "apps/workflow_engine/tests/test_e2e_pipeline.py — real-LM E2E pipeline test"
  affects:
    - "apps/workflow_engine/orchestrator.py (exercised end-to-end, no changes)"
tech_stack:
  added: []
  patterns:
    - "pytest.mark.requires_lm marker for CI-skip"
    - "monkeypatch.setattr(site_bootstrap, 'ensure_site', ...) to redirect tmp_path"
    - "MagicMock for ProcessedLog.record + seen (deferred assertions only)"
    - "LM_BASE_URL / LM_MODEL env vars with defaults pattern"
key_files:
  created:
    - apps/workflow_engine/tests/test_e2e_pipeline.py
  modified: []
decisions:
  - "LmStudioConfig attribute overrides wrapped in try/except AttributeError to handle frozen dataclasses"
  - "No mocks for distill, plan, build, integrate, ingest — real implementations used"
  - "only site_bootstrap.ensure_site is redirected to tmp_path to avoid touching real sites dir"
  - "D-05 assertion takes first module in manifest (not by known module_id) since real LM generates the ID"
metrics:
  duration: "~2 minutes"
  completed: "2026-04-23"
  tasks_completed: 1
  tasks_total: 1
  files_created: 1
  files_modified: 0
---

# Phase 19 Plan 02: Real-LM E2E Pipeline Test Summary

**One-liner:** Real-LM end-to-end pipeline test exercising all 5 stages (INGEST → DISTILL → PLAN → BUILD → INTEGRATE) against live LM Studio, marked `@pytest.mark.requires_lm` for CI skip.

## What Was Built

Created `apps/workflow_engine/tests/test_e2e_pipeline.py` — a single test file containing one test function (`test_full_v2_pipeline_against_real_lm`) that:

1. Seeds a tmp site dir with an empty `spa_manifest.json`
2. Redirects `site_bootstrap.ensure_site` to the tmp dir via `monkeypatch`
3. Calls `orchestrator._process_locked()` with a real `Config` pointing at a live LM Studio server
4. Asserts (D-05): at least one module appears in the manifest AND its `index.html` exists
5. Asserts the version field is a 7-char short SHA (INT-03 requirement)
6. Asserts `processed.record` was called with `outcome="ok"`

## Environment Variables

| Var | Default | Purpose |
|-----|---------|---------|
| `LM_BASE_URL` | `http://localhost:1234` | LM Studio server address |
| `LM_MODEL` | `local-model` | Model name to use |

`LmStudioConfig` attribute overrides are wrapped in `try/except AttributeError` to handle frozen Pydantic models that reject direct attribute assignment post-construction.

## LmStudioConfig Guard Pattern

The CONTEXT.md noted LmStudioConfig might be a frozen dataclass. The `hasattr` guard is defensive — if neither `base_url` nor `model` attributes exist or are assignable, the test still runs using LmStudioConfig defaults. This is documented with `try/except AttributeError: pass` blocks.

## Real-LM Run

A real-LM run was NOT performed in this execution — LM Studio is not running in this environment. The test collects cleanly and is correctly deselected by `pytest -m 'not requires_lm'`. The test is designed to be run manually with a live LM Studio instance.

## Verification Results

| Check | Result |
|-------|--------|
| `pytest tests/test_e2e_pipeline.py --collect-only` | 1 test collected, exit 0 |
| `pytest -m 'not requires_lm' tests/test_e2e_pipeline.py` | 1 deselected, exit 0 |
| `@pytest.mark.requires_lm` count | 1 |
| `def test_full_v2_pipeline_against_real_lm` count | 1 |
| `orchestrator._process_locked` count | 1 |
| `LM_BASE_URL` count | 5 (>= 2 required) |
| `LM_MODEL` count | 3 (>= 1 required) |
| No pipeline stage mocks (distill/plan/build/integrate/ingest) | PASS |

## Deviations from Plan

None — plan executed exactly as written. The file contents match the plan's specified code block with one minor addition: the `hasattr` checks for `LmStudioConfig.base_url` and `LmStudioConfig.model` are wrapped in `try/except AttributeError: pass` blocks per the "Critical notes for the executor" instruction in the plan itself.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced. The test introduces a developer-controlled env var path (T-19-10, accepted) and filesystem write via tmp_path (T-19-09, mitigated by `ensure_site` redirect).

## Self-Check: PASSED

- File exists: `apps/workflow_engine/tests/test_e2e_pipeline.py` — FOUND
- Commit `faa4a21` exists — FOUND
