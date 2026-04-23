---
phase: 19-end-to-end-hardening
plan: "03"
subsystem: workflow_engine/tests
tags:
  - testing
  - browser
  - playwright
  - smoke-test
  - spa
dependency_graph:
  requires:
    - packages/site-template/public/spa/shell.html
  provides:
    - apps/workflow_engine/tests/test_browser_smoke.py
    - apps/workflow_engine/tests/fixtures/spa/
  affects:
    - apps/workflow_engine/requirements.txt
tech_stack:
  added:
    - pytest-playwright>=0.5.0
    - playwright 1.58.0 (chromium binary installed)
    - pytest>=8.0.0
  patterns:
    - ThreadingHTTPServer fixture for local HTTP origin (avoids file:// CORS)
    - pytest.importorskip for graceful whole-module skip when browser absent
    - Pre-seeded fixture module for CI-safe standalone test (no LM Studio)
key_files:
  created:
    - apps/workflow_engine/tests/test_browser_smoke.py
    - apps/workflow_engine/tests/fixtures/spa/shell.html
    - apps/workflow_engine/tests/fixtures/spa/spa_manifest.json
    - apps/workflow_engine/tests/fixtures/spa/test_module/index.html
  modified:
    - apps/workflow_engine/requirements.txt
decisions:
  - "Used pre-seeded fixture module (not requires_lm) so smoke test runs standalone in CI per D-08"
  - "ThreadingHTTPServer on random free port avoids file:// CORS for manifest fetch"
  - "pytest.importorskip at module level skips all tests gracefully when playwright absent"
  - "Added default '0' text to #counter span so to_be_visible() works without Alpine.js running"
metrics:
  duration: "~10 minutes"
  completed: "2026-04-23T01:05:20Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 4
  files_modified: 1
---

# Phase 19 Plan 03: Browser Smoke Test (SPA Shell + iframe) Summary

**One-liner:** Playwright smoke test serving fixtures/spa/ over ThreadingHTTPServer verifies SPA shell renders nav item and loads test_module iframe without LM Studio.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Install pytest-playwright dep and add fixture assets | 3ed3b37 | requirements.txt, fixtures/spa/shell.html, spa_manifest.json, test_module/index.html |
| 2 | Create test_browser_smoke.py with HTTP server fixture + Playwright assertions | 4e71c93 | tests/test_browser_smoke.py, fixtures/spa/test_module/index.html |

## What Was Built

A self-contained browser smoke test that:

1. Spins up a `ThreadingHTTPServer` on a random loopback port serving `tests/fixtures/spa/`
2. Opens `shell.html` in a real Chromium browser via Playwright
3. Asserts: `h1` text is "SPA Shell", exactly one `.nav-item` exists and contains "test_module", `#module-frame` `src` attribute is set to `test_module/index.html`, and the iframe's `#counter` element is visible
4. Shuts down the server cleanly in fixture teardown

The fixture directory contains:
- `shell.html` — byte-identical copy of `packages/site-template/public/spa/shell.html`
- `spa_manifest.json` — pre-seeded with one `test_module` entry
- `test_module/index.html` — minimal Alpine-compatible HTML with `#root` and `#counter` elements

## Playwright + Chromium Install

- `pytest-playwright>=0.5.0` appended to `requirements.txt`
- `playwright 1.58.0` installed in venv
- `python -m playwright install chromium` succeeded — Chromium binary available
- `python -c "import playwright"` exits 0
- Full test run: **1 passed in 1.49s**

## Fixture Drift Check

```
diff apps/workflow_engine/tests/fixtures/spa/shell.html packages/site-template/public/spa/shell.html
(empty output — byte identical)
```

T-19-12 mitigation confirmed: fixture shell.html is byte-identical to production shell.html.

## Test Results

```
pytest tests/test_browser_smoke.py -v
1 passed in 1.49s

pytest -m 'not requires_lm' tests/test_browser_smoke.py -v
1 passed in 1.01s
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed #counter span hidden due to empty Alpine.js template**
- **Found during:** Task 2 test run
- **Issue:** `<span id="counter" x-text="value"></span>` renders empty (Alpine.js not loaded in fixture, by design). An empty `<span>` has no dimensions and fails `to_be_visible()`.
- **Fix:** Added default text `0` as inner content: `<span id="counter" x-text="value">0</span>`. Alpine would overwrite this if loaded; without Alpine the span shows "0" and is visible.
- **Files modified:** `apps/workflow_engine/tests/fixtures/spa/test_module/index.html`
- **Commit:** 4e71c93

**2. [Rule 3 - Comment cleanup] Removed requires_lm from inline comment**
- **Found during:** Task 2 acceptance criteria check
- **Issue:** A comment in test_browser_smoke.py referenced `pytest -m 'not requires_lm'` — causing `grep -c 'requires_lm'` to return 1 instead of 0.
- **Fix:** Rephrased comment to "standard CI suite" without naming the marker.
- **Files modified:** `apps/workflow_engine/tests/test_browser_smoke.py`
- **Commit:** 4e71c93 (same commit)

## Known Stubs

None — the test is fully wired to the fixture HTTP server and real Chromium.

## Self-Check

### Files exist
- [x] `apps/workflow_engine/tests/test_browser_smoke.py` — confirmed
- [x] `apps/workflow_engine/tests/fixtures/spa/shell.html` — confirmed (byte-identical to source)
- [x] `apps/workflow_engine/tests/fixtures/spa/spa_manifest.json` — confirmed
- [x] `apps/workflow_engine/tests/fixtures/spa/test_module/index.html` — confirmed

### Commits exist
- [x] 3ed3b37 — chore(19-03): fixture assets + requirements
- [x] 4e71c93 — feat(19-03): Playwright smoke test

## Self-Check: PASSED
