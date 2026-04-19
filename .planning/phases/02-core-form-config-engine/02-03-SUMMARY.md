---
phase: 02-core-form-config-engine
plan: 03
subsystem: setup
tags: [html, jinja2, forms, accessibility, wizard]
dependency_graph:
  requires: [02-01]
  provides: [setup/templates/index.html full wizard form]
  affects: [setup/static/wizard.css (Plan 04), setup/static/wizard.js (Plan 05)]
tech_stack:
  added: []
  patterns: [field-group pattern, aria-describedby for help+error, details/summary collapsible]
key_files:
  created:
    - setup/static/.gitkeep
  modified:
    - setup/templates/index.html
    - setup/server.py
decisions:
  - active_step passed as 'gmail' constant from server.py — not user input, safe Jinja2 variable
  - Exit Setup button retained in footer, wired by wizard.js (Plan 05)
  - setup/static/ directory created to enable Flask static file serving for Plans 04 and 05
metrics:
  duration: "< 5 min"
  completed_date: "2026-04-19"
---

# Phase 2 Plan 03: Full Wizard Form HTML Summary

**One-liner:** Replaced Phase 1 placeholder index.html with complete wizard form — progress indicator, Gmail section, LM Studio section (with collapsible Advanced), allowed-senders widget, all aria-describedby accessibility wiring, and external CSS/JS links.

## What Was Done

`setup/templates/index.html` was fully replaced. The Phase 1 placeholder had inline `<style>` and `<script>` blocks and a single Exit button. The new file contains:

- Progress indicator `<nav class="wizard-steps">` with 5 steps rendered via Jinja2 loop, `active_step` variable controls which step gets `class="active"` and `aria-current="step"`
- Gmail section: gmail-address (email), gmail-app-password (password + show/hide toggle), gmail-folder (text), allowed-senders widget (sender-input + add-sender + remove-sender)
- Fan-out derived-values paragraph with `id="imap-user-preview"` and `id="smtp-user-preview"` for wizard.js to update
- LM Studio section: lms-base-url, lms-model, lms-temperature + lms-max-tokens (split row), lms-cli-path
- Advanced collapsible via `<details><summary>Advanced</summary>` containing lms-autostart (checkbox) and lms-request-timeout
- All fields: `aria-describedby="{id}-help {id}-error"`, `<small id="{id}-help">` with help copy, `<span id="{id}-error" class="error" hidden aria-live="polite">`
- External stylesheet: `url_for('static', filename='wizard.css')`
- External script: `url_for('static', filename='wizard.js')` at end of body
- No inline `<style>` or `<script>` blocks
- Form `id="wizard-form"` with `novalidate` (JS handles validation)
- Footer Exit button `id="exit-btn"` retained

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Replace setup/templates/index.html with full wizard form | d31a75e | setup/templates/index.html, setup/server.py, setup/static/.gitkeep |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Pass active_step to render_template**
- **Found during:** Task 1
- **Issue:** `server.py` called `render_template('index.html', port=_port)` but the new template requires `{{ active_step }}` Jinja2 variable. Without it, Flask raises `UndefinedError` on every page load.
- **Fix:** Added `active_step='gmail'` argument to `render_template` call in `server.py`
- **Files modified:** `setup/server.py`
- **Commit:** d31a75e

**2. [Rule 3 - Blocking Issue] Created setup/static/ directory**
- **Found during:** Task 1
- **Issue:** `setup/static/` did not exist. Flask's `url_for('static', ...)` references it; Plans 04 and 05 write wizard.css and wizard.js there. Directory must exist so Flask can serve static files.
- **Fix:** Created `setup/static/.gitkeep` to establish the directory in git
- **Files modified:** `setup/static/.gitkeep`
- **Commit:** d31a75e

## Verification

- `python3 -c "from setup.server import app; client = app.test_client(); r = client.get('/'); print(r.status_code, len(r.data))"` → `200 10382`
- `grep "wizard-steps" setup/templates/index.html` → match
- `grep -c "field-group" setup/templates/index.html` → `11` (>= 9 required)
- `grep "smtp-user-preview" setup/templates/index.html` → match
- All 22 acceptance criteria: PASS
- `aria-describedby` count: 11 (>= 10 required)

## Known Stubs

None. All fields have correct IDs, defaults, help text, and error spans. wizard.css and wizard.js are referenced but not yet created — Plans 04 and 05 create them.

## Threat Flags

None beyond what is documented in the plan's threat model.

## Self-Check: PASSED

- `setup/templates/index.html` exists with full wizard form at commit d31a75e
- `setup/server.py` passes `active_step='gmail'` at commit d31a75e
- `setup/static/.gitkeep` exists at commit d31a75e
- Flask GET `/` returns HTTP 200 with 10382-byte body
