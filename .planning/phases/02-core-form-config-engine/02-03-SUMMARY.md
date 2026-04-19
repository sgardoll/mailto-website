---
phase: 02-core-form-config-engine
plan: 03
subsystem: setup
tags: [html, jinja2, form, accessibility]
dependency_graph:
  requires: []
  provides: [wizard form HTML structure]
  affects: [wizard.css (Plan 04), wizard.js (Plan 05)]
tech_stack:
  added: []
  patterns: [Jinja2 template with active_step context variable]
key_files:
  created: []
  modified:
    - setup/templates/index.html
decisions: []
metrics:
  duration: "< 5 min"
  completed_date: "2026-04-19"
---

# Phase 2 Plan 03: HTML Wizard Form Summary

**One-liner:** Replaced Phase 1 placeholder index.html with the full wizard form: progress indicator, Gmail section, LM Studio section (with collapsible Advanced), allowed-senders widget, all field groups per UI-SPEC.

## What Was Done

Complete rewrite of `setup/templates/index.html`. Removed all inline styles and scripts. Added:
- 5-step progress indicator via Jinja2 loop with active_step context variable
- Gmail section: address, app password (with show/hide toggle), folder, allowed-senders widget
- LM Studio section: base URL, model, temperature/max-tokens split row, CLI path, collapsible Advanced with autostart checkbox and request timeout
- All fields have aria-describedby linking help text and error spans, aria-live="polite" on error spans
- External CSS and JS via url_for()

## Tasks

| Task | Name | Files |
|------|------|-------|
| 1 | Replace index.html with full wizard form | setup/templates/index.html |

## Deviations from Plan

None.

## Verification

- `GET /` returns 200 with 9634 bytes via Flask test client
- grep confirms: wizard-steps, wizard-form, all field IDs, toggle-visibility, sender-input, add-sender, exit-btn present
- No `<style>` tags, no inline `<script>` blocks

## Self-Check: PASSED
