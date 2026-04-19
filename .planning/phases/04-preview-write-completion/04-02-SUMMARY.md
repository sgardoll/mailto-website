---
phase: 04-preview-write-completion
plan: 02
subsystem: server
tags: [python, flask, preview, write-config, atomic-write, prefill, templates, testing]

requires:
  - phase: 04-preview-write-completion
    plan: 01
    provides: build_final_outputs, mask_for_preview, hydrate_wizard_state in setup/builder.py

provides:
  - GET /step/preview with server-side masked preview and overwrite gate flag
  - POST /write-config with explicit confirmation, overwrite gating, atomic pair-write, rollback
  - GET /step/done success screen
  - _try_prefill() reads existing .env + config.yaml once at launch and hydrates _wizard_state
  - preview.html and done.html templates
  - test_phase4_flow.py with 15 route/integration tests

affects: [04-03, setup/server.py, setup/templates/preview.html, setup/templates/done.html]

tech-stack:
  added:
    - tempfile.mkstemp + os.replace + os.fsync for crash-safe pair-write
    - dotenv_values (python-dotenv) with inline fallback parser if not installed
  patterns:
    - Prefill runs once at launch via _try_prefill() guarded by _prefilled flag
    - Preview and write share one builder.build_final_outputs() call — no drift possible
    - Atomic pair-write: write+fsync both temps, backup originals, replace first, replace second, rollback first if second fails
    - File I/O in server.py; builder remains pure

key-files:
  created:
    - setup/templates/preview.html
    - setup/templates/done.html
    - setup/tests/test_phase4_flow.py
    - .planning/phases/04-preview-write-completion/04-02-SUMMARY.md
  modified:
    - setup/server.py

key-decisions:
  - "_try_prefill() is guarded by _prefilled flag so it runs at most once per server process (on main() startup or first request to /step/preview)."
  - "File I/O (reading .env and config.yaml) lives in server.py, not builder.py — builder stays pure per established contract."
  - "_write_config_pair() writes and fsyncs both temp files before replacing either target, takes restorable backups, and rolls back the first replace if the second fails."
  - "Overwrite confirmation is a separate field (overwrite_confirmed) from the base confirmation field (confirmed) so the UI can present them independently."

duration: ~4 min
completed: 2026-04-19
---

# Phase 04 Plan 02: Preview/Write Backend Flow Summary

**setup/server.py now owns the full prefill -> preview -> write -> success lifecycle, consuming the builder contract from Plan 01 without duplicating config assembly.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-19T13:22:38Z
- **Completed:** 2026-04-19T13:26:53Z
- **Tasks:** 3
- **Files modified:** 1 (server.py)
- **Files created:** 4 (preview.html, done.html, test_phase4_flow.py, SUMMARY.md)

## Accomplishments

- Added `_try_prefill()` to read existing `.env` and `workflow/config.yaml` at launch and merge into `_wizard_state` via `builder.hydrate_wizard_state()`. Runs once, guarded by `_prefilled` flag.
- Added `GET /step/preview`: requires `gmail_address` in state (redirects to gmail step if missing), calls `build_final_outputs()` + `mask_for_preview()`, renders `preview.html` with masked blocks and `has_existing_config` flag.
- Added `GET /step/done`: renders `done.html` success screen.
- Added `POST /write-config`: enforces `confirmed` field, checks for existing files and rejects with `409 + overwrite_required` if not `overwrite_confirmed`, calls `build_final_outputs()` immediately before write (preview/write cannot drift), delegates to `_write_config_pair()`.
- Added `_write_config_pair()`: writes and fsyncs both temp files first, captures backups of existing targets, replaces first target, rolls back first target from backup if second replace fails.
- Added `preview.html`: 5-step header with `preview` as active step, two read-only `<pre>` blocks for `.env` and YAML, conditional overwrite warning and checkbox shell, Write Config Files button with `data-has-existing` attribute for Plan 03 JS wiring.
- Added `done.html`: success screen confirming written files, `./scripts/run-workflow.sh` as primary next action.
- Added `setup/tests/test_phase4_flow.py`: 15 tests covering prefill population, prefill skip when no files, prefill idempotency, preview rendering and masking, preview redirect when state incomplete, overwrite warning presence/absence, write confirmation gate, overwrite gate (409), successful pair-write, env content correctness, overwrite with confirmation, rollback on second-replace failure, no leftover temp files, done route.

## Task Commits

1. **Tasks 1+2: server.py prefill, preview/done routes, write-config, pair-write** — `81d6699`
2. **Task 3: preview.html, done.html, test_phase4_flow.py** — `3a74630`

## Files Created/Modified

- `setup/server.py` — added _try_prefill, /step/preview, /step/done, /write-config, _write_config_pair
- `setup/templates/preview.html` — read-only preview screen with overwrite gate shell
- `setup/templates/done.html` — success screen with run-workflow.sh
- `setup/tests/test_phase4_flow.py` — 15 Phase 4 backend integration tests

## Decisions Made

See key-decisions in frontmatter.

## Deviations from Plan

None - plan executed exactly as written. The three plan tasks were committed in two commits (server.py changes combined for Tasks 1+2 since they are in the same file; templates+tests as Task 3 commit).

## Known Stubs

- `preview.html` Write Config Files button and overwrite checkbox are wired to backend contract but have no JS interaction handlers yet — those are intentionally deferred to Plan 03 (wizard.js/wizard.css wiring). The button and checkbox are present and correctly structured for Plan 03 to wire.

## Self-Check: PASSED

Verified:
- `setup/server.py` exports `/step/preview`, `/write-config`, `/step/done`, `_try_prefill`, `_write_config_pair`
- `setup/templates/preview.html` exists and renders through Flask
- `setup/templates/done.html` exists and contains `run-workflow.sh`
- `setup/tests/test_phase4_flow.py` exists with 15 tests
- `.venv/bin/python -m pytest setup/tests/test_phase4_flow.py -q` → `15 passed`
- Task commits present: `81d6699`, `3a74630`

---
*Phase: 04-preview-write-completion*
*Completed: 2026-04-19*
