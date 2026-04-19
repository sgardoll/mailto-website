---
phase: 02-core-form-config-engine
plan: 06
subsystem: setup
tags: [flask, integration, routing]
dependency_graph:
  requires: [builder.py (Plan 02), index.html (Plan 03)]
  provides: [POST /validate-form route, _wizard_state dict, active_step in GET /]
  affects: []
tech_stack:
  added: []
  patterns: [Module-level mutable dict, request.get_json(force=True)]
key_files:
  created: []
  modified:
    - setup/server.py
decisions: []
metrics:
  duration: "< 5 min"
  completed_date: "2026-04-19"
---

# Phase 2 Plan 06: Flask Integration Summary

**One-liner:** Added _wizard_state dict, POST /validate-form route, and active_step='gmail' to setup/server.py with 5 surgical edits.

## What Was Done

Five changes to `setup/server.py`:
1. Added `request` to flask import
2. Added `import setup.builder as builder`
3. Added `_wizard_state = {}` at module level
4. Updated GET / render_template to pass `active_step='gmail'`
5. Added POST /validate-form route: validates via builder.validate(), stores in _wizard_state, returns env_preview and yaml_preview

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add _wizard_state, update GET /, add POST /validate-form | pending | setup/server.py |

## Deviations from Plan

None.

## Verification

- All 21 tests pass: `pytest setup/tests/ -v` (6 lifecycle + 15 builder including 2 route integration)
- POST /validate-form returns 200 with env_preview and yaml_preview for valid input
- POST /validate-form returns 400 with errors list for invalid input
- GET / renders with active_step='gmail'

## Self-Check: PASSED
