---
phase: "01"
plan: "01"
subsystem: setup
tags: [flask, server, port-probe, pre-flight, tdd]
dependency_graph:
  requires: []
  provides: [flask-server-skeleton, setup-package]
  affects: [01-02, 01-03]
tech_stack:
  added: [flask==3.1.3, pytest==9.0.3]
  patterns: [daemon-thread-browser-open, socket-probe-readiness-gate, os.access-preflight]
key_files:
  created:
    - setup/__init__.py
    - setup/server.py
    - setup/templates/index.html
    - setup/tests/__init__.py
    - setup/tests/test_server_lifecycle.py
  modified: []
decisions:
  - "Used socket.bind() to probe port 7331 rather than os.getpid trick — simpler and idiomatic"
  - "wait_for_port() placed its time.sleep inside its own loop so open_browser_after_ready() never calls sleep directly"
  - "_port global set in main() so the index route can access the bound port without threading complexity"
metrics:
  duration: "~5 minutes"
  completed: "2026-04-19"
  tasks_completed: 2
  files_created: 5
  files_modified: 0
---

# Phase 01 Plan 01: Flask Server Skeleton Summary

**One-liner:** Flask setup-wizard server with port 7331 probe, os.access pre-flight check, and daemon-thread browser open gated on socket readiness.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for server lifecycle | 08edce5 | setup/__init__.py, setup/tests/__init__.py, setup/tests/test_server_lifecycle.py |
| 1 (GREEN) | Server implementation | fb0ea9b | setup/server.py |
| 2 | Placeholder index.html template + smoke test | 9bce756 | setup/templates/index.html |

## What Was Built

- **`setup/__init__.py`** — empty package marker
- **`setup/server.py`** — Flask app entry point with five functions:
  - `find_free_port(preferred=7331)`: binds to 127.0.0.1:7331; on OSError falls back to OS-assigned port
  - `wait_for_port(port, timeout=5.0)`: socket probe loop, 50ms polling, RuntimeError on timeout
  - `check_write_permission(project_root)`: delegates to `os.access(path, os.W_OK)`
  - `open_browser_after_ready(url, port)`: daemon thread; waits on `wait_for_port()` then opens via `open` (macOS) or `webbrowser` (other)
  - `main()`: pre-flight check → find port → start browser thread → `app.run(host='127.0.0.1')`
- **`setup/templates/index.html`** — valid HTML5, no CDN, renders `{{ port }}`, includes `#status` and `#exit-btn` placeholders

## TDD Gate Compliance

- RED gate: commit `08edce5` — 4 failing tests (import error — `setup.server` did not exist)
- GREEN gate: commit `fb0ea9b` — all 4 tests pass
- REFACTOR gate: not needed (code was clean on first pass)

## Verification Results

All success criteria met:

- `setup/__init__.py` exists (empty package marker)
- `setup/server.py` exports: `app`, `find_free_port`, `wait_for_port`, `check_write_permission`, `open_browser_after_ready`, `main`
- `find_free_port()` prefers 7331, never returns 5000 or 8080 (confirmed by code review and grep)
- `wait_for_port()` uses socket probe loop; `time.sleep` inside the probe loop only — not in `open_browser_after_ready`
- `check_write_permission()` uses `os.access()`; `main()` calls `sys.exit(1)` on failure
- Flask binds to `127.0.0.1` only (line 86: `app.run(host='127.0.0.1', ...)`)
- GET / returns 200 with "Setup Wizard" body — confirmed by smoke test (PASS)
- All 4 unit tests pass

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

| Stub | File | Line | Reason |
|------|------|------|--------|
| `#exit-btn` button (not wired) | setup/templates/index.html | 26 | Intentional — POST /exit route deferred to Plan 03 |
| `<p id="status">Loading...</p>` | setup/templates/index.html | 25 | Intentional — status updates deferred to future plans |
| `# TODO: Plan 03 will add a POST /exit route` | setup/server.py | 69 | Intentional placeholder |

These stubs do NOT block the plan goal (running server with placeholder page). They are tracked for Plans 02 and 03.

## Threat Flags

No new security surface introduced beyond the plan's threat model. All threats mitigated per T-01-01 through T-01-04:
- Server binds to 127.0.0.1 only (T-01-04)
- OS fallback port ensures server always starts (T-01-02)
- REPO_ROOT computed from `__file__`, not user input (T-01-03)

## Self-Check: PASSED

Files confirmed present:
- setup/__init__.py: FOUND
- setup/server.py: FOUND
- setup/templates/index.html: FOUND
- setup/tests/test_server_lifecycle.py: FOUND

Commits confirmed:
- 08edce5 (RED tests): in git log
- fb0ea9b (GREEN implementation): in git log
- 9bce756 (template + smoke test): in git log
