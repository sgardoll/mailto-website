---
phase: 17-build-validator
plan: "01"
subsystem: workflow_engine
tags: [tdd, validator, html-parser, alpine, tailwind]
dependency_graph:
  requires: []
  provides: [validator.validate_module]
  affects: [apps/workflow_engine/validator.py, apps/workflow_engine/tests/test_validator.py]
tech_stack:
  added: []
  patterns: [HTMLParser subclass, error-list accumulator, stdlib-only validation]
key_files:
  created:
    - apps/workflow_engine/validator.py
    - apps/workflow_engine/tests/test_validator.py
  modified: []
decisions:
  - "HTMLParseError compat shim: try-import from html.parser with Exception fallback for Python 3.14+"
  - "Ellipsis check scoped to script_texts only (not full HTML) per Pitfall 4"
  - "Tailwind CDN checked as literal string; Alpine CDN checked via @semver regex per Pitfall 3"
metrics:
  duration: "~12 minutes"
  completed: "2026-04-22"
  tasks_completed: 2
  files_created: 2
  files_modified: 0
---

# Phase 17 Plan 01: Validator TDD Summary

**One-liner:** Pure-Python HTMLParser subclass validator enforcing 8 structural rules on Alpine/Tailwind HTML; all 20 tests pass RED->GREEN.

## What Was Built

`validate_module(html: str) -> list[str]` implemented in `apps/workflow_engine/validator.py` using only stdlib `html.parser` and `re`. A single-pass `_Inspector(HTMLParser)` subclass accumulates all structural observations, then post-parse checks evaluate each VAL rule in order.

### Checks Implemented

| Rule | Description | Check |
|------|-------------|-------|
| VAL-06 | Minimum length | `len(html.encode("utf-8")) < 800` |
| VAL-03 | Stub phrases (full HTML) | case-insensitive regex: TODO/FIXME/placeholder/coming soon/implement |
| VAL-01 | x-data present | `inspector.has_x_data` |
| VAL-01 | Event handler present | `@click`/`@input`/`@change`/`x-on:*` |
| VAL-04 | x-if not on div | `inspector.x_if_on_div` |
| VAL-02 | Alpine CDN pinned | `cdn.jsdelivr.net/npm/alpinejs@{semver}/` regex |
| VAL-02 | Tailwind CDN present | `cdn.tailwindcss.com` literal |
| VAL-03 | Ellipsis in script only | `...` scan on `script_texts` only |
| VAL-05 | No external fetch/XHR | URL extraction from `fetch()` and `.open()` calls |

## TDD Gate Compliance

- RED commit: `ef546be` -- `test(17-01): RED -- validator tests fail`
- GREEN commit: `ed816eb` -- `feat(17-01): GREEN -- validator impl passes all tests`
- Gate order preserved: RED precedes GREEN in git log.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] HTMLParseError removed in Python 3.14**
- **Found during:** Task 2 (GREEN phase), first test run
- **Issue:** `from html.parser import HTMLParseError` raises `ImportError` on Python 3.14 -- the exception class was removed from stdlib
- **Fix:** Added a try/except import shim -- `except ImportError: HTMLParseError = Exception` -- preserving the try/except guard in `validate_module` without breaking Python 3.12/3.13 compatibility
- **Files modified:** `apps/workflow_engine/validator.py`
- **Commit:** `ed816eb`

## Test Results

```
20 passed in 0.02s
```

All 20 test functions pass. No new pip dependencies added. `validator.py` importable without LM Studio running (verified with `python -c "from apps.workflow_engine import validator; print('ok')"`).

## Known Stubs

None -- `validate_module` is fully wired and returns real error lists from real HTML parsing.

## Threat Flags

No new network endpoints, auth paths, or file access patterns introduced. `validator.py` is a pure in-process function.

## Self-Check: PASSED

- [x] `apps/workflow_engine/validator.py` exists
- [x] `apps/workflow_engine/tests/test_validator.py` exists
- [x] RED commit `ef546be` in git log
- [x] GREEN commit `ed816eb` in git log
- [x] 20 tests collected and passing
