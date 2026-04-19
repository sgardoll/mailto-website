---
phase: 03
plan: 04
subsystem: setup-wizard-ui
tags: [template, jinja2, inboxes, wizard-step]
requires:
  - setup/templates/index.html (header/nav/footer pattern)
  - .planning/phases/03-hosting-provider-inbox-manager/03-UI-SPEC.md
provides:
  - setup/templates/inboxes.html (inboxes wizard step template)
affects:
  - setup/server.py (GET /step/inboxes renders this template — wired in a later plan)
  - setup/static/wizard.js (targets #inboxes-list, #add-inbox, template#inbox-row-template — wired in a later plan)
tech_stack:
  added: []
  patterns:
    - "<template> element cloning for dynamic row append (native DOM, no framework)"
    - "Pre-rendered first row with explicit IDs; template rows use empty aria-describedby filled by JS"
key_files:
  created:
    - setup/templates/inboxes.html
  modified: []
decisions:
  - "First inbox row is pre-rendered server-side with IDs suffixed -1; subsequent rows are cloned from the <template> by JS"
  - "Pre-rendered Remove button ships with disabled attribute since only one row exists on page load; JS toggles state on add/remove"
  - "aria-describedby attributes in the template are empty strings — JS fills in generated IDs on clone to keep a11y linkage"
  - "Help text placed inside each .field-group (above input) consistent with index.html's pattern"
metrics:
  duration_minutes: ~3
  tasks_completed: 1
  files_touched: 1
  completed_date: 2026-04-19
---

# Phase 03 Plan 04: Inboxes Wizard Step Template Summary

One-liner: Created `setup/templates/inboxes.html` — the Inboxes wizard step with a `<template id="inbox-row-template">` for JS cloning, one pre-rendered inbox row in `#inboxes-list`, an `#add-inbox` button, and all CSS classes/error spans wired for the Phase 3 JS to target.

## What Was Built

- **setup/templates/inboxes.html** (172 lines) — full wizard step page following the header/nav/footer pattern from `index.html`:
  - Progress indicator uses the shared `{% set steps = [...] %}` block with `active_step='inboxes'` highlighting
  - `<section class="form-section" aria-labelledby="inboxes-heading">` wraps the Inboxes step
  - `<template id="inbox-row-template">` contains a complete inbox row with all five inputs (`.inbox-slug`, `.inbox-email`, `.inbox-site-name`, `.inbox-site-url`, `.inbox-base-path`), help text, error spans, and a Remove button — ready for JS `template.content.cloneNode(true)`
  - `#inboxes-list` contains one pre-rendered `.inbox-row` with IDs ending in `-1` and a `disabled` Remove button
  - `#add-inbox` button below the list for appending new rows
  - `#inboxes-list-error` span for list-level errors (e.g. empty-list validation)
  - Form actions: submit button and `#form-error-summary`
  - Footer: Exit Setup button and `<script src="wizard.js">`

## Verification

All acceptance criteria grep counts met:

| Criterion | Required | Actual |
|-----------|----------|--------|
| `inbox-row-template` | ≥ 1 | 1 |
| `inboxes-list` | ≥ 1 | 2 |
| `add-inbox` | ≥ 1 | 1 |
| field classes (5 × ≥ 2 occurrences) | ≥ 10 | 30 |
| `remove-inbox` (template + pre-rendered) | ≥ 2 | 2 |
| `field-row-thirds` (template + pre-rendered) | ≥ 2 | 2 |
| `disabled` (only pre-rendered Remove) | 1 | 1 |
| `active_step` reference | ≥ 1 | 1 |

## Deviations from Plan

None — plan executed exactly as written.

## Threat Flags

None — template rendering boundary unchanged from Phase 2; no user input flows into the template.

## Commits

- `db2b060` — feat(03-04): add inboxes wizard step template

## Self-Check: PASSED

- [x] `setup/templates/inboxes.html` exists
- [x] Commit `db2b060` exists in git log
- [x] All acceptance criteria grep counts satisfied
