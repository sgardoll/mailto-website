---
phase: 18-integrate-orchestrator
plan: "02"
subsystem: workflow_engine
tags: [integrate, git, atomic-write, manifest, tdd]
requirements: [INT-01, INT-02, INT-03, INT-04]

dependency_graph:
  requires:
    - apps/workflow_engine/git_ops.py (commit_and_push)
    - apps/workflow_engine/schemas/envelope.py (MechanicSpec)
    - apps/workflow_engine/logging_setup.py (get)
  provides:
    - apps/workflow_engine/integrate.py (integrate, IntegrateFailed, startup_assert_gitignore)
  affects:
    - Phase 18 orchestrator (imports integrate())

tech_stack:
  added: []
  patterns:
    - tempfile.mkstemp + os.replace for atomic file writes
    - Two-commit approach for INT-02/INT-03 circularity resolution
    - Idempotent git init with local user.email/name config

key_files:
  created:
    - apps/workflow_engine/integrate.py
    - apps/workflow_engine/tests/test_integrate.py
  modified: []

decisions:
  - "Two-commit approach: module HTML committed first (SHA_A captured), manifest updated with SHA_A as version in second commit. Resolves circular dependency between INT-02 (manifest in same commit) and INT-03 (version = commit SHA)."
  - "startup_assert_gitignore uses string matching (not regex) on non-negated, non-comment .gitignore lines. Fail-closed on public/spa, public/, public patterns."

metrics:
  duration: "~15 minutes"
  completed: "2026-04-22"
  tasks_completed: 2
  files_created: 2
  files_modified: 0
---

# Phase 18 Plan 02: INTEGRATE Stage Implementation Summary

**One-liner:** `integrate()` writes module HTML via tempfile+os.replace, upserts spa_manifest.json, commits module+manifest to per-site git repo, returns 7-char short SHA — satisfying INT-01..04.

## What Was Built

`apps/workflow_engine/integrate.py` — the INTEGRATE pipeline stage with:

- `class IntegrateFailed(RuntimeError)` — raised when `commit_and_push` returns None (nothing committed)
- `def integrate(spec, html_b64, site_dir, *, push=False) -> str` — full pipeline: git init on first run, atomic write module HTML, commit module, upsert manifest with SHA, commit manifest, return 7-char SHA
- `def startup_assert_gitignore(site_dir) -> None` — audit `.gitignore` for patterns excluding `public/spa/`; no-op if `.gitignore` absent
- Private helpers: `_ensure_git_repo`, `_atomic_write`, `_upsert_manifest`

`apps/workflow_engine/tests/test_integrate.py` — 10 tests covering all INT requirements.

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED | `bdc8cf0` — `test(18-02): RED — add failing tests...` | PASSED |
| GREEN | `61aaa4e` — `feat(18-02): GREEN — implement integrate()...` | PASSED |

## Commits

| Hash | Message |
|------|---------|
| `bdc8cf0` | `test(18-02): RED — add failing tests for integrate() (INT-01..04)` |
| `61aaa4e` | `feat(18-02): GREEN — implement integrate() + IntegrateFailed + startup_assert_gitignore (INT-01..04)` |

## Requirements Closed

| Req | Description | Status |
|-----|-------------|--------|
| INT-01 | Module HTML written via tempfile + os.replace | Closed |
| INT-02 | Module + manifest committed to site's own git repo | Closed |
| INT-03 | Manifest `version` field = 7-char short SHA of module commit | Closed |
| INT-04 | `startup_assert_gitignore` detects `public/spa/` exclusion and raises | Closed |

## Deviations from Plan

### Design Decision: Two-Commit Approach (Documented in Plan)

The plan itself documented the INT-02/INT-03 circularity (manifest version = commit SHA, but manifest must be in that commit) and prescribed the two-commit resolution. This was implemented as specified:

1. Commit module HTML → capture `SHA_A`
2. Upsert manifest with `SHA_A` as version → commit manifest

The test for "second call raises IntegrateFailed" works correctly because the second call with identical HTML finds the module file unchanged and `commit_and_push` returns `None`.

No unplanned deviations from the plan.

## Threat Model Compliance

All mitigations from STRIDE register implemented:

| Threat ID | Mitigation | Verified |
|-----------|------------|---------|
| T-18-04 | `_atomic_write` uses `mkstemp` + `os.replace` | Test: `test_integrate_writes_module_atomically` |
| T-18-05 | Default `push=False` | Function signature `push: bool = False` |
| T-18-06 | `IntegrateFailed` raised when `commit_and_push` returns None | Test: `test_integrate_raises_when_nothing_committed` |
| T-18-07 | Hardcoded `workflow@localhost` / `Workflow Engine` | Accepted |
| T-18-08 | Negation lines (`!...`) skipped; `public/spa`, `public/`, `public` patterns caught | Tests: gitignore suite |

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or file access patterns beyond what the plan's threat model covers.

## Self-Check: PASSED

- [x] `apps/workflow_engine/integrate.py` exists
- [x] `apps/workflow_engine/tests/test_integrate.py` exists (10 tests)
- [x] RED commit `bdc8cf0` exists in git log
- [x] GREEN commit `61aaa4e` exists in git log
- [x] All 10 tests pass (`10 passed in 0.58s`)
- [x] `from apps.workflow_engine.integrate import integrate, IntegrateFailed, startup_assert_gitignore` succeeds
