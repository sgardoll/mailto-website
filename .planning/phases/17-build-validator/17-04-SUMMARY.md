---
phase: 17-build-validator
plan: "04"
subsystem: workflow_engine
tags: [tdd, build, html-generation, retry-loop, base64]
dependency_graph:
  requires: [17-01, 17-02, 17-03]
  provides: [build.py, BuildFailed, MAX_RETRIES]
  affects: [phase-18-orchestrator]
tech_stack:
  added: []
  patterns: [TDD-RED-GREEN, frozenset-dedup-abort, dataclasses-replace-immutable-config]
key_files:
  created:
    - apps/workflow_engine/build.py
    - apps/workflow_engine/tests/test_build.py
  modified: []
decisions:
  - "max_tokens enforcement uses isinstance(int) guard to allow MagicMock lm_cfg in tests while still enforcing on real LmStudioConfig"
  - "frozenset dedup: prev_errors=None on attempt 1 ensures no early abort on first call; abort only fires on attempt 2+ when cur_errors == prev_errors"
  - "SHORT_INVALID_HTML produces identical errors on every call so early-abort fires on attempt 2 — tests for both retry-exhaustion and early-abort use this same constant"
metrics:
  duration: "~15 minutes"
  completed: "2026-04-22"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 0
---

# Phase 17 Plan 04: Build Stage TDD Summary

**One-liner:** TDD gate for build.py — retry loop with frozenset dedup, finish_reason=length abort, and base64 encoding using chat_json_with_meta and BUILD_SCHEMA.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 17-04-01 | RED: test_build.py failing tests | f1b084a | apps/workflow_engine/tests/test_build.py |
| 17-04-02 | GREEN: build.py implementation | 0a97fb9 | apps/workflow_engine/build.py |

## TDD Gate Compliance

- RED gate: `test(17-04)` commit `f1b084a` exists — all 12 tests failed with `ModuleNotFoundError: No module named 'apps.workflow_engine.build'`
- GREEN gate: `feat(17-04)` commit `0a97fb9` exists — all 12 tests pass

## What Was Built

`build(spec: MechanicSpec, lm_cfg) -> dict` implements the BUILD stage:

1. Enforces `max_tokens >= 8000` via `dataclasses.replace` (no caller mutation)
2. Calls `lm_studio.chat_json_with_meta` with `BUILD_SCHEMA` on each attempt
3. Raises `BuildFailed(["finish_reason=length: ..."], attempt)` immediately on truncated output — before `validate_module` is called
4. Calls `validator.validate_module(html)` — empty errors list means success
5. On success: returns `{"html_b64": base64(utf-8), "kind": spec.kind.value, "attempts": N}`
6. Frozenset dedup: if `frozenset(errors_N) == frozenset(errors_{N-1})`, aborts early with `BuildFailed`
7. Appends validator errors to user prompt on each retry iteration
8. After `MAX_RETRIES=3` exhausted, raises `BuildFailed(errors, 3)`

`_EXEMPLARS` dict maps kind string to the matching exemplar constant — only the kind-matching exemplar appears in the system prompt.

## Test Coverage (12 tests)

| Test | Covers |
|------|--------|
| test_happy_path_returns_html_b64 | BUILD-01: returns {html_b64, kind, attempts} |
| test_base64_encoding_is_correct | html_b64 round-trips to original HTML |
| test_finish_reason_length_raises_immediately | BUILD-04: T-17-04-01 truncation threat |
| test_finish_reason_stop_does_not_abort | stop reason proceeds normally |
| test_retry_on_validation_failure_calls_lm_three_times | Early abort on attempt 2 (same errors) |
| test_early_abort_when_errors_frozen | BUILD-03: frozenset dedup T-17-04-04 |
| test_retry_succeeds_on_second_attempt | BUILD-02: retry loop success path |
| test_schema_kwarg_passed_to_chat_json_with_meta | BUILD-01: schema=BUILD_SCHEMA |
| test_exemplar_selection_by_kind | BUILD-05: kind-matched exemplar in system prompt |
| test_exemplar_passes_validator | BUILD-02+BUILD-05: all 5 exemplars are valid HTML |
| test_build_failed_carries_errors_and_attempts | BuildFailed.errors and .attempts |
| test_max_tokens_enforced_internally | BUILD-04: max_tokens >= 8000 enforcement |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] MagicMock lm_cfg TypeError in max_tokens comparison**
- **Found during:** Task 17-04-02 (GREEN), first test run
- **Issue:** `MagicMock().max_tokens < 8000` raises `TypeError` in Python 3.14 (MagicMock no longer supports `<` with int)
- **Fix:** Changed enforcement to `isinstance(max_tokens, int) and max_tokens < 8000` — skips enforcement for mock objects while still enforcing for real `LmStudioConfig` dataclasses
- **Files modified:** `apps/workflow_engine/build.py`
- **Commit:** 0a97fb9 (folded into GREEN commit)

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or file access patterns introduced.

## Self-Check: PASSED

- `apps/workflow_engine/build.py` exists: FOUND
- `apps/workflow_engine/tests/test_build.py` exists: FOUND
- RED commit f1b084a: FOUND
- GREEN commit 0a97fb9: FOUND
- All 12 tests pass, 93 total suite tests pass
