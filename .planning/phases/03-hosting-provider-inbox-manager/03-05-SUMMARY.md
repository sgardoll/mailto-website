---
phase: 03
plan: 05
subsystem: setup/server
tags: [flask, routing, wizard, step-dispatch]
dependency_graph:
  requires:
    - setup/builder.py (validate_hosting/build_hosting/validate_inboxes/build_inboxes from 03-01)
    - setup/templates/lmstudio.html (from 03-02)
    - setup/templates/hosting.html (from 03-03)
    - setup/templates/inboxes.html (from 03-04)
  provides:
    - GET /step/lmstudio
    - GET /step/hosting
    - GET /step/inboxes
    - POST /validate-form (step-dispatched)
  affects:
    - setup/static/wizard.js (clients expect next_step in success responses)
tech_stack:
  added: []
  patterns:
    - Step-field dispatch in single /validate-form route
    - Server-driven navigation via {ok, next_step} response envelope
key_files:
  created: []
  modified:
    - setup/server.py
decisions:
  - D-02 honored: single /validate-form route dispatches by step field
  - D-03 honored: success response includes next_step for client redirect
  - D-08 honored: hosting_provider merged into _wizard_state via build_hosting output
metrics:
  duration: ~5 min
  completed: 2026-04-19
  tasks: 2
  tests_added: 0
  tests_total: 46
requirements:
  - HOST-01
  - HOST-02
  - HOST-03
  - HOST-04
  - HOST-05
  - HOST-06
  - INBOX-01
  - INBOX-02
  - INBOX-03
  - INBOX-04
---

# Phase 3 Plan 5: Server Wiring Summary

**One-liner:** Wired three new GET step routes (lmstudio/hosting/inboxes) and rewrote `/validate-form` to dispatch validation by `step` field, returning `next_step` for server-driven client navigation.

## What Was Built

Two surgical changes to `setup/server.py`:

1. **Three GET step routes** — Each renders the step's template with the matching `active_step` slug so the progress indicator highlights correctly:
   - `/step/lmstudio` -> `lmstudio.html`
   - `/step/hosting` -> `hosting.html`
   - `/step/inboxes` -> `inboxes.html`

2. **Step-dispatching `/validate-form`** — Reads `data['step']` (defaults to `'gmail'` for backward compatibility) and routes to the appropriate validator/builder pair. On success returns `{ok: true, next_step: '/step/...'}` so JS can do `window.location.href = data.next_step`. Unknown `step` values return 400 with an explicit error (threat T-03-05-01 mitigation — explicit allowlist).

Dispatch map:

| step | Validator | Builder | next_step |
|------|-----------|---------|-----------|
| `gmail` (default) | `builder.validate` | `builder.build` | `/step/lmstudio` |
| `lmstudio` | `builder.validate` | `builder.build` | `/step/hosting` |
| `hosting` | `builder.validate_hosting` | `builder.build_hosting` | `/step/inboxes` |
| `inboxes` | `builder.validate_inboxes` | `builder.build_inboxes` | `/step/preview` |
| other | — | — | 400 unknown step |

The lmstudio branch reuses gmail's validator/builder deliberately — `builder.validate()` only checks gmail fields and ignores LMS fields, but merging LMS data into `_wizard_state` is what the Phase 4 assembler needs.

## Commits

| Hash | Message |
|------|---------|
| b0d0f7e | feat(03-05): add GET routes for lmstudio/hosting/inboxes steps |
| 898bddf | feat(03-05): dispatch /validate-form by step with next_step response |

## Test Results

```
46 passed in 0.41s
```

All Phase 2 + Phase 3 unit tests green. Existing `test_validate_form_route_returns_ok` passes without modification — it sends `VALID_DATA` without a `step` key, which defaults to `'gmail'` and preserves the original response envelope (plus the additive `next_step` field, which the test does not assert against).

Smoke-test of the live Flask test client confirmed:
- `step='hosting'` with valid netlify data -> `200 {ok:true, next_step:'/step/inboxes'}`
- `step='inboxes'` with valid inbox list -> `200 {ok:true, next_step:'/step/preview'}`
- `step='bogus'` -> `400 {ok:false, errors:[{field:'step', message:'Unknown step'}]}`

## Deviations from Plan

None — plan executed exactly as written.

## Threat Model Compliance

| Threat | Mitigation | Status |
|--------|------------|--------|
| T-03-05-01 Step tampering | Explicit allowlist (`gmail`/`lmstudio`/`hosting`/`inboxes`); unknown step -> 400 | Implemented |
| T-03-05-02 Skipping steps | Accepted (localhost single-user) | No code change |
| T-03-05-03 Large inboxes array | Accepted (localhost tool) | No code change |

## Threat Flags

None — no new network surface, auth path, file access, or schema change at trust boundaries.

## Known Stubs

None. Routes and dispatch are fully wired. `/step/preview` is referenced as a next_step but lives in Phase 4 — not a stub of this plan, a planned handoff.

## Self-Check: PASSED

- FOUND: setup/server.py (lines 82-94 hold the three new step routes; lines 97-148 hold step-dispatch validate_form)
- FOUND: commit b0d0f7e
- FOUND: commit 898bddf
- All 46 tests pass under `uv run python -m pytest setup/tests/ -q`
- Live dispatch smoke test confirms all four step branches plus unknown-step 400 path
