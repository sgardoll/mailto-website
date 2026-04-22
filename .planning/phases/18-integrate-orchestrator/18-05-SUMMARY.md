---
phase: 18-integrate-orchestrator
plan: "05"
subsystem: workflow_engine/orchestrator
tags: [orchestrator, wiring, v2-pipeline, INT-05, PIPE-02]

dependency_graph:
  requires:
    - 18-01  # integrate.py with startup_assert_gitignore + IntegrateFailed
    - 18-02  # integrate.integrate() implementation
    - 17-04  # build.py with BuildFailed + build()
    - 16-02  # plan.py returning bare string routing decision
  provides:
    - orchestrator._process_locked v2 branch fully wired (BUILD + INTEGRATE)
    - PIPE-02 routing verified by tests
    - INT-05 closed (v1 path unchanged)
  affects:
    - apps/workflow_engine/orchestrator.py
    - apps/workflow_engine/tests/test_orchestrator_v2.py
    - apps/workflow_engine/tests/test_orchestrator_distill_plan_wiring.py

tech_stack:
  added: []
  patterns:
    - try/except per stage with _reply_failure + processed.record on error
    - startup_assert_gitignore called once near top of _process_locked (belt-and-braces .gitignore check)
    - monkeypatch-based wiring tests isolating each stage independently

key_files:
  created:
    - apps/workflow_engine/tests/test_orchestrator_v2.py
  modified:
    - apps/workflow_engine/orchestrator.py
    - apps/workflow_engine/tests/test_orchestrator_distill_plan_wiring.py

decisions:
  - v2 does not call _reply_success on completion — log only, defers reply to avoid inbox spam per CONTEXT.md
  - upgrade_state_only routing returns early after PLAN stage, before BUILD/INTEGRATE
  - startup_assert_gitignore placed immediately after ensure_site (before v1/v2 branch), so it fires for both paths

metrics:
  duration_minutes: 20
  completed_date: "2026-04-22"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 3
---

# Phase 18 Plan 05: Wire BUILD + INTEGRATE into Orchestrator v2 Branch Summary

**One-liner:** Replaced the PLAN-stage stub with a full BUILD → INTEGRATE pipeline, wired error handling for BuildFailed/IntegrateFailed mirroring v1, and verified PIPE-02 routing with 6 new tests — 116 total passing.

## What Was Built

The v2 branch of `orchestrator._process_locked` now executes the complete 5-stage pipeline:

1. INGEST (pre-existing)
2. DISTILL (pre-existing)
3. PLAN (pre-existing)
4. BUILD — calls `build.build(spec, cfg.lm_studio)` → returns `{"html_b64": ..., "kind": ..., "attempts": ...}`
5. INTEGRATE — calls `integrate.integrate(spec, html_b64, site_dir, push=False)` → returns 7-char SHA

`integrate.startup_assert_gitignore(site_dir)` is called once per `_process_locked` entry (before the v1/v2 branch), ensuring .gitignore never silently excludes `public/spa/`.

The old stub comment `# Phase 17/18 will hook BUILD + INTEGRATE here` is gone.

## Tasks Completed

| Task | Commit | Description |
|------|--------|-------------|
| 1 — Wire v2 branch | c6eaa04 | orchestrator.py: imports, startup_assert, BUILD + INTEGRATE stages, error handlers |
| 2 — Add v2 tests   | 3eedc23 | test_orchestrator_v2.py: 6 tests covering PIPE-02 routing + all error/success paths |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated existing distill/plan wiring tests to mock v2 stages**

- **Found during:** Task 1 — running existing orchestrator test suite after wiring BUILD + INTEGRATE
- **Issue:** `test_orchestrator_distill_plan_wiring.py` had one failing test (`test_v2_happy_path_records_v2_planned_outcome`) that checked for the old stub outcome `v2_planned_new_module`. The test also lacked mocks for `build.build` and `integrate.integrate`, which would now be called during v2 happy-path tests.
- **Fix:** Added `build_mod` and `integrate_mod` stubs to `_neutralise()` (returning happy-path defaults). Renamed the failing test to `test_v2_happy_path_records_ok_outcome` and changed the assertion to check `outcome="ok"`.
- **Files modified:** `apps/workflow_engine/tests/test_orchestrator_distill_plan_wiring.py`
- **Commit:** c6eaa04 (included in Task 1 commit)

## Verification

```
pytest apps/workflow_engine/tests/test_orchestrator_v2.py -x  → 6 passed
pytest apps/workflow_engine/tests/ -q                          → 116 passed
grep -c "Phase 17/18 will hook" apps/workflow_engine/orchestrator.py → 0
grep -q "integrate.integrate(spec, build_result" apps/workflow_engine/orchestrator.py → match
```

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes introduced. The plan's threat model (T-18-19 through T-18-22) is fully implemented:
- T-18-19: `getattr(inbox, "pipeline_version", "v1")` defaults to v1 (safe)
- T-18-20: Explicit try/except around BUILD and INTEGRATE; outcomes recorded per stage
- T-18-21: `_reply_failure` forwards exception strings (accepted, consistent with v1)
- T-18-22: `startup_assert_gitignore` raises on exclusion but is non-blocking when .gitignore absent

## Known Stubs

None. The v2 pipeline is fully wired end-to-end from INGEST through INTEGRATE.

## Self-Check: PASSED

- `apps/workflow_engine/orchestrator.py` — modified, exists
- `apps/workflow_engine/tests/test_orchestrator_v2.py` — created, exists
- `apps/workflow_engine/tests/test_orchestrator_distill_plan_wiring.py` — modified, exists
- Commit c6eaa04 — exists (feat 18-05)
- Commit 3eedc23 — exists (test 18-05)
- 116 tests pass, 0 failures
