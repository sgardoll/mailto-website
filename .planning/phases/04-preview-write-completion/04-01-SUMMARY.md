---
phase: 04-preview-write-completion
plan: 01
subsystem: testing
tags: [python, pyyaml, builder, config, preview]

requires:
  - phase: 02-core-form-config-engine
    provides: base Gmail/LM Studio builder contract and hidden runtime defaults
  - phase: 03-hosting-provider-inbox-manager
    provides: provider/inbox builder fragments consumed by the final assembler
provides:
  - Authoritative final .env + workflow/config.yaml builder output for Phase 4
  - Masked preview helper that keeps Gmail placeholder literals intact
  - Existing-config hydration path for builder-driven preview/write flows
affects: [04-02, 04-03, setup/server.py]

tech-stack:
  added: []
  patterns:
    - Single authoritative builder path for both preview and final disk write
    - Server-side secret masking to last-4 while leaving ${GMAIL_APP_PASSWORD} literal in YAML
    - Hydration derives site_base_url only from consistent inbox URL roots and otherwise returns empty

key-files:
  created:
    - .planning/phases/04-preview-write-completion/04-01-SUMMARY.md
  modified:
    - setup/builder.py
    - setup/tests/test_builder.py

key-decisions:
  - "build_final_outputs() accepts either stored provider/inbox fragments or wizard-visible fields and normalizes them into the canonical final config shape."
  - "mask_for_preview() only masks raw secrets and intentionally leaves ${GMAIL_APP_PASSWORD} untouched inside YAML preview output."
  - "hydrate_wizard_state() preserves hidden runtime keys and only derives site_base_url when every inbox URL shares the same root."

patterns-established:
  - "Builder remains pure: no Flask imports, no file I/O, no preview/write duplication outside setup/builder.py."
  - "Hydrated wizard state preserves hidden runtime keys (git_branch, git_push, dry_run) for pass-through rewrites."
  - "Phase 4 contract coverage lives in setup/tests/test_builder.py before server/UI integration begins."

requirements-completed: [OUT-01, OUT-04, OUT-05]

duration: ~28 min
completed: 2026-04-19
---

# Phase 04 Plan 01: Preview/Write Builder Contract Summary

**setup/builder.py now owns the authoritative final-output, preview-masking, and existing-config hydration contract that later Phase 4 server work can consume without re-deriving config state.**

## Performance

- **Duration:** ~28 min
- **Started:** 2026-04-19T12:34:00Z
- **Completed:** 2026-04-19T13:02:00Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- Added `build_final_outputs()` to assemble the final `.env` and `workflow/config.yaml` strings in canonical order, with hidden runtime key preservation and exactly one provider section.
- Added `mask_for_preview()` so preview output is server-maskable without leaking provider credentials or the raw Gmail app password.
- Added `hydrate_wizard_state()` plus shared-root derivation so existing `.env` + YAML can prefill `_wizard_state` without losing runtime passthrough keys.
- Expanded `setup/tests/test_builder.py` to lock the final assembly, masking, hydration, defaults, and ambiguous-base-url behavior before any server/UI Phase 4 work.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add final-output assembler and masked-preview helpers** - `1d93d64` (feat)
2. **Task 2: Add pure prefill normalization helpers for existing config** - `1e84fbf` (feat)
3. **Task 3: Expand builder tests to lock the Phase 4 contract** - `7751d44` (test)

**Plan metadata:** pending (this commit)

## Files Created/Modified
- `setup/builder.py` - added final output assembly, preview masking, and hydration helpers while keeping builder logic pure.
- `setup/tests/test_builder.py` - added behavior-focused coverage for final assembly, masked preview output, hydration, runtime defaults, and ambiguous site-base derivation.
- `.planning/phases/04-preview-write-completion/04-01-SUMMARY.md` - recorded the plan outcome, commit hashes, and next-phase readiness.

## Decisions Made
- See key-decisions in frontmatter; all followed plan scope exactly.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `python -m pytest` was unavailable in this shell (`python` missing; `yaml` unavailable in system Python), so verification was run in a local `.venv` with setup requirements installed.

## User Setup Required
None.

## Next Phase Readiness
- `setup/builder.py` now exposes the pure contract Phase 4 server routes need for preview/write integration.
- Hidden runtime keys survive hydration and rewrite flows.
- `setup/tests/test_builder.py` passes with 56 assertions covering the new contract.
- Ready for `04-02-PLAN.md`.

## Self-Check: PASSED

Verified:
- `setup/builder.py` exports `build_final_outputs`, `mask_for_preview`, and `hydrate_wizard_state`
- `setup/tests/test_builder.py` covers final assembly, preview masking, hydration, runtime defaults, and ambiguous shared-root derivation
- `.venv/bin/python -m pytest setup/tests/test_builder.py -q` → `56 passed`
- Task commits present on `main`: `1d93d64`, `1e84fbf`, `7751d44`

---
*Phase: 04-preview-write-completion*
*Completed: 2026-04-19*
