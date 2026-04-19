---
phase: 01-server-foundation
plan: 03
subsystem: infra
tags: [flask, python, signal, atexit, threading]

requires:
  - phase: 01-01
    provides: Flask app, server.py with find_free_port/main, index.html with #exit-btn

provides:
  - POST /exit route with threading-based dispatch (deadlock-safe)
  - _shutdown_server() using os.kill(os.getpid(), signal.SIGINT)
  - _cleanup() atexit handler printing clean exit message
  - SIGTERM handler for process-manager compatibility
  - index.html Exit Setup button wired via fetch('/exit')

affects: [02-core-form]

tech-stack:
  added: []
  patterns: [threading-based shutdown dispatch, SIGINT self-signal for clean exit]

key-files:
  created: []
  modified:
    - setup/server.py
    - setup/templates/index.html
    - setup/tests/test_server_lifecycle.py

key-decisions:
  - "threaded=False in app.run() — avoids block_on_close keep-alive delay on SIGINT (Python 3.14 ThreadingMixIn default)"
  - "time.sleep(0.3) in _shutdown_server() — ensures /exit response flushes before SIGINT fires"
  - "os.kill(os.getpid(), SIGINT) not server.shutdown() — no deadlock risk from any calling context"

patterns-established:
  - "Shutdown pattern: threading.Thread(target=_shutdown_server, daemon=True).start() in route handler"
  - "Self-signal pattern: os.kill(os.getpid(), signal.SIGINT) with brief pre-delay for response flush"

requirements-completed:
  - SRV-03
  - SRV-04

duration: 25min
completed: 2026-04-19
---

# Phase 1: Plan 03 Summary

**Flask server clean shutdown via SIGINT self-signal — POST /exit with threading dispatch, atexit cleanup, SIGTERM handler, and fetch-wired Exit Setup button**

## Performance

- **Duration:** 25 min
- **Started:** 2026-04-19T15:00:00Z
- **Completed:** 2026-04-19T15:25:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- `_shutdown_server()` uses `os.kill(os.getpid(), signal.SIGINT)` with a 0.3s pre-delay — deadlock-free, response always flushes first
- `POST /exit` route starts shutdown in a daemon thread and returns `{"ok": true}` immediately
- `_cleanup()` registered via `atexit` — prints "Setup wizard exited cleanly." on any exit path
- SIGTERM handler registered for process-manager compatibility
- Exit Setup button wired in `index.html` via `fetch('/exit')` with disabled state and status feedback
- `threaded=False` prevents Python 3.14 `block_on_close` from delaying SIGINT delivery via keep-alive threads

## Task Commits

1. **Task 1+2: Shutdown lifecycle + button wiring** - `decaa33` (feat)

## Files Created/Modified
- `setup/server.py` — added `_shutdown_server`, `_cleanup`, `POST /exit` route, atexit/SIGTERM registration, `threaded=False`
- `setup/templates/index.html` — Exit Setup button wired to `fetch('/exit')` with JS
- `setup/tests/test_server_lifecycle.py` — `test_shutdown_sends_sigint`, `test_exit_route_returns_ok` (both passing)

## Decisions Made
- `threaded=False`: Flask 3.x / Python 3.14 `ThreadingMixIn` defaults `block_on_close=True`, which holds `serve_forever()` open until all HTTP keep-alive connections close. Single-user local wizard — sequential handling is correct and makes SIGINT delivery immediate.
- `time.sleep(0.3)` pre-delay: with `threaded=False`, the daemon thread and request handler share the main thread's time slice. The delay guarantees the response is fully sent before SIGINT is processed.

## Deviations from Plan

### Auto-fixed Issues

**1. [threaded=False + delay] Flask 3.x keep-alive blocks graceful SIGINT**
- **Found during:** Task 2 integration test
- **Issue:** `os.kill(os.getpid(), SIGINT)` sent correctly, but server remained accepting connections because `block_on_close=True` (Python 3.14 default) caused `serve_forever()` to wait for all HTTP keep-alive connection threads to close before returning.
- **Fix:** Added `threaded=False` to `app.run()` (eliminates thread pool / block_on_close issue) and `time.sleep(0.3)` in `_shutdown_server()` (ensures response flushes before SIGINT fires when all I/O is on the main thread).
- **Files modified:** `setup/server.py`
- **Verification:** Integration test passes — POST /exit returns `{"ok": true}`, server port unreachable within 3 seconds, process exits with code 0.
- **Committed in:** `decaa33`

---

**Total deviations:** 1 auto-fixed (Flask threading behavior in Python 3.14)
**Impact on plan:** Necessary correctness fix. No scope creep. All must-haves satisfied.

## Issues Encountered
- Integration test false failures due to port 7331 being held by stale test server processes from earlier test runs. Root cause: background test processes weren't fully killed between runs. Resolved by force-killing all processes and running integration test with dynamic port detection.

## Self-Check: PASSED

- `server.shutdown()` not called from any request handler: confirmed
- `threading.Thread(target=_shutdown_server, daemon=True).start()` in exit_wizard: confirmed (line 82)
- `os.kill(os.getpid(), signal.SIGINT)` in `_shutdown_server`: confirmed (line 68)
- `atexit.register(_cleanup)` in `main()`: confirmed (line 99)
- `fetch('/exit')` in `index.html`: confirmed (line 32)
- All 6 unit tests pass
- End-to-end: POST /exit → `{"ok": true}` → server unreachable within 3s → exit code 0

## Next Phase Readiness
- Server lifecycle complete: port probe, browser auto-open, pre-flight check, clean shutdown all working
- `setup/server.py` ready for Phase 2 form routes to be added
- `setup/templates/index.html` placeholder ready to be replaced with the real wizard form

---
*Phase: 01-server-foundation*
*Completed: 2026-04-19*
