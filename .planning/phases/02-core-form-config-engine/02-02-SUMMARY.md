---
phase: 02-core-form-config-engine
plan: 02
subsystem: setup
tags: [python, yaml, pyyaml, builder, validation, config-generation]

dependency_graph:
  requires:
    - phase: 02-core-form-config-engine
      plan: 01
      provides: PyYAML>=6.0.1 in setup venv
  provides:
    - setup/builder.py with validate() and build() pure functions
    - setup/tests/test_builder.py with 15 tests (13 unit + 2 integration stubs)
  affects:
    - 02-06 (validate-form route wires server.py to builder)
    - Phase 4 (config assembly uses builder output format)

tech-stack:
  added: []
  patterns:
    - "Pure function module pattern: no Flask imports, no file I/O, fully unit-testable"
    - "Secret separation: raw password in env_str, ${GMAIL_APP_PASSWORD} reference in yaml_str"
    - "Fan-out pattern: single gmail_address fans into imap.user, smtp.user, smtp.from_address"
    - "DEFAULTS dict for optional fields with hardcoded-value escape hatch (api_key)"

key-files:
  created:
    - setup/builder.py
    - setup/tests/test_builder.py
  modified: []

key-decisions:
  - "D-01 enforced: builder emits only global_allowed_senders, imap, smtp, lm_studio"
  - "D-03 enforced: lm_studio.api_key hardcoded to 'lm-studio' — not collected from form"
  - "D-02 enforced: lm_studio.autostart and request_timeout_s always included in output"
  - "yaml.dump() called with sort_keys=False, default_flow_style=False, allow_unicode=True"
  - "Integration route tests written now to drive Plan 06 TDD for /validate-form"

patterns-established:
  - "test_{subject}_{condition} naming, one-sentence docstrings, module-level VALID_DATA baseline"
  - "Integration tests colocated with unit tests, excluded via -k 'not route' until route exists"

requirements-completed:
  - GMAIL-01
  - GMAIL-02
  - GMAIL-03
  - GMAIL-04
  - LMS-01
  - LMS-02
  - LMS-03
  - LMS-04

duration: 2min
completed: 2026-04-19
---

# Phase 2 Plan 02: Pure Config Builder Summary

**Pure Python builder module with validate() and build() implementing Gmail fan-out, secret separation (.env vs yaml reference), and LM Studio advanced fields — 13 unit tests all passing**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-19T07:16:55Z
- **Completed:** 2026-04-19T07:18:31Z
- **Tasks:** 2
- **Files modified:** 2 created

## Accomplishments

- `setup/builder.py` created as a pure function module (no Flask, no file I/O) with `validate()`, `build()`, and `DEFAULTS`
- `build()` fans `gmail_address` into `imap.user`, `smtp.user`, `smtp.from_address`; emits raw password to `.env`, literal `${GMAIL_APP_PASSWORD}` reference to YAML
- `setup/tests/test_builder.py` created with 15 tests — 13 unit tests all passing, 2 integration route tests as TDD drivers for Plan 06

## Task Commits

1. **Task 1: Create setup/builder.py** - `c631bb1` (feat)
2. **Task 2: Create setup/tests/test_builder.py** - `57ce718` (test)

## Files Created/Modified

- `setup/builder.py` - Pure config builder: validate() validates required fields; build() produces (env_str, yaml_str) pair
- `setup/tests/test_builder.py` - 15 test functions covering all validate() and build() behaviors; 2 integration stubs for Plan 06

## Decisions Made

Followed D-01, D-02, D-03 exactly as documented in 02-CONTEXT.md. No new decisions required.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- pytest was not installed in the project venv; installed via `.venv/bin/pip install pytest` during Task 2 verification. Environment gap, not a code issue.

## Threat Surface Scan

No new network endpoints introduced. `build()` uses `yaml.dump()` exclusively (T-02-02-01 mitigated). `validate()` enforces `isinstance(senders, list)` (T-02-02-03 mitigated). `env_str` contains raw password by design (T-02-02-02 accepted).

## Known Stubs

None.

## Next Phase Readiness

- `setup/builder.py` is importable and ready for Plan 06 to wire into `POST /validate-form`
- `test_builder.py` integration tests will validate the route when Plan 06 adds it
- All 8 requirements (GMAIL-01–04, LMS-01–04) satisfied by this builder's fan-out and output scope logic

## Self-Check

- `setup/builder.py` exists at commit c631bb1
- `setup/tests/test_builder.py` exists at commit 57ce718
- 13/13 unit tests pass; 2 route tests deferred to Plan 06

## Self-Check: PASSED

---
*Phase: 02-core-form-config-engine*
*Completed: 2026-04-19*
