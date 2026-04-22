---
phase: 18-integrate-orchestrator
plan: "01"
subsystem: workflow_engine/validator
tags: [validator, security, alpine, xss, sec-01, tdd]
requirements: [SEC-01]

dependency_graph:
  requires: []
  provides: [SEC-01 x-html ban in validator]
  affects: [apps/workflow_engine/validator.py]

tech_stack:
  added: []
  patterns: [HTMLParser attribute flag pattern (mirrors x_if_on_div / has_x_html)]

key_files:
  created: []
  modified:
    - apps/workflow_engine/validator.py
    - apps/workflow_engine/tests/test_validator.py

decisions:
  - "x-html check applied to ANY tag (not just div) — Alpine x-html is valid on any element"
  - "Error inserted after VAL-04 (x-if-on-div) and before VAL-02 (CDN checks) per plan placement note"

metrics:
  duration: "60s"
  completed_date: "2026-04-22"
  tasks_completed: 2
  files_modified: 2
---

# Phase 18 Plan 01: SEC-01 x-html Directive Ban Summary

**One-liner:** Added `has_x_html` flag to `_Inspector` + SEC-01 error append in `validate_module` — any Alpine module with `x-html` on any element is now rejected to prevent LLM-generated XSS.

## What Was Built

`validator.py` now detects the `x-html` Alpine directive via a new `_Inspector.has_x_html` boolean flag set in `handle_starttag` for any tag. When `validate_module` runs, it appends `"x-html directive is banned (use x-text for LLM-inserted content)"` to the errors list if the flag is true. The check sits after VAL-04 (x-if-on-div) and before VAL-02 (CDN pinning).

Two new tests in `test_validator.py`:
- `test_x_html_directive_rejected` — confirms `x-html="foo"` on any element produces an error containing `"x-html"` (SEC-01 gate).
- `test_x_text_allowed` — regression guard confirming `x-text` modules are unaffected.

All 22 validator tests pass.

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED  | dfd77ee | test_x_html_directive_rejected failed (as required) |
| GREEN | 586d2ca | All 22 tests pass |

## Deviations from Plan

**Plan's pseudo-code used `result.ok` and `result.errors`** — the actual `validate_module` API returns `list[str]`. Tests were written to match the real API (plain list), consistent with all existing tests. No behavioral deviation; only the test assertion style was adapted.

## Known Stubs

None.

## Threat Flags

No new security surface introduced. The change closes T-18-01 and T-18-02 from the plan's threat register.

## Self-Check: PASSED

- `apps/workflow_engine/validator.py` — exists and contains all three required changes
- `apps/workflow_engine/tests/test_validator.py` — exists with both new tests
- Commit `dfd77ee` (RED) — confirmed in git log
- Commit `586d2ca` (GREEN) — confirmed in git log
- All 22 tests pass (`pytest apps/workflow_engine/tests/test_validator.py`)
