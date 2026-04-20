---
phase: 14-foundation
plan: 01
subsystem: config
tags: [enum, config-contract, pipeline-version, mechanic-kind, v2.0, foundation]

# Dependency graph
requires: []
provides:
  - "MechanicKind(str, Enum) with 5 canonical values: calculator, wizard, drill, scorer, generator"
  - "InboxConfig.pipeline_version field defaulting to 'v1'"
  - "MechanicKind re-exported from apps/workflow_engine/config.py"
affects: [16-distill-plan, 17-build-validator, 18-integrate-orchestrator]

# Tech tracking
tech-stack:
  added: []
  patterns: [str-based Enum for mechanic kinds (prevents ordinal misuse), per-inbox pipeline selector via default field]

key-files:
  created: []
  modified:
    - packages/config_contract/__init__.py
    - apps/workflow_engine/config.py

key-decisions:
  - "MechanicKind capped at 5 values for v2.0 — comparator/matcher explicitly deferred per REQUIREMENTS.md"
  - "pipeline_version is free-form string with 'v1' default — Phase 18 owns routing logic, no validation in Phase 14"
  - "No helper methods added to MechanicKind — DIST-03 downstream code compares by value string or enum member"

patterns-established:
  - "str-based Enum pattern: MechanicKind(str, Enum) ensures JSON-serialisable values and prevents integer-index misuse"
  - "Re-export pattern: workflow_engine/config.py is the single import surface for pipeline code"

requirements-completed: [PIPE-01, DIST-03, CONF-01]

# Metrics
duration: 8min
completed: 2026-04-20
---

# Phase 14 Plan 01: Foundation Summary

**MechanicKind str-Enum (5 values) + InboxConfig.pipeline_version field added to config_contract, re-exported via workflow_engine/config.py**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-20T00:00:00Z
- **Completed:** 2026-04-20T00:08:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added `MechanicKind(str, Enum)` to `packages/config_contract/__init__.py` with exactly 5 canonical values: calculator, wizard, drill, scorer, generator
- Added `pipeline_version: str = "v1"` field to `InboxConfig` — existing v1 YAML configs load unchanged (default absorbs missing key)
- Re-exported `MechanicKind` from `apps/workflow_engine/config.py` between `LmStudioConfig` and `SiteGroundConfig` (alphabetical order preserved)
- Full contract smoke test passes: round-trip load_config(), re-export identity check (`MK2 is MechanicKind`), all 5 enum values confirmed

## Task Commits

1. **Task 1: Add MechanicKind enum + pipeline_version field to config_contract** - `d293130` (feat)
2. **Task 2: Re-export MechanicKind from workflow_engine config** - `a48b62a` (feat)

**Plan metadata:** (committed with SUMMARY)

## Files Created/Modified
- `packages/config_contract/__init__.py` - Added MechanicKind enum block after DeployProvider.from_string; added pipeline_version field to InboxConfig
- `apps/workflow_engine/config.py` - Added MechanicKind to re-export import tuple

## Decisions Made
- MechanicKind capped at 5 values — comparator and matcher deferred per plan directive, not added
- No `from_string()` or other helpers added to MechanicKind — Phase 14 scope only
- pipeline_version left as free-form string — Phase 18 will add routing logic

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

The automated verify command in the plan used `python3` which resolved to Homebrew Python 3.14 (no yaml module). Switched to `.venv/bin/python3` for full smoke test — the project venv has PyYAML installed. Core config_contract imports (Task 1) worked with system Python since they have no external deps. Not a code issue; no deviation applied.

## Known Stubs

None - no stub values or placeholder data introduced.

## Threat Flags

No new security surface introduced. MechanicKind values are fixed source literals (T-14-01-03 accept). InboxConfig.pipeline_version is free-form string with no action taken in Phase 14 (T-14-01-01 accept). str-based Enum mitigates ordinal misuse per T-14-01-02.

## Next Phase Readiness
- MechanicKind and pipeline_version are stable — all downstream phases (16 DISTILL, 17 BUILD, 18 INTEGRATE) can import from either `packages.config_contract` or `apps.workflow_engine.config`
- No blockers

---
*Phase: 14-foundation*
*Completed: 2026-04-20*
