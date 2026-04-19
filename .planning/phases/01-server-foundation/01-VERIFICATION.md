---
phase: 01-server-foundation
verified: 2026-04-19T00:00:00Z
status: human_needed
score: 11/11 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run ./scripts/setup.sh with a real .venv present"
    expected: "Wizard launches in default browser automatically at http://127.0.0.1:7331/ (or fallback port)"
    why_human: "Browser auto-open requires a display/browser environment and a real .venv; cannot test programmatically without starting a live server and observing browser launch"
  - test: "Click Exit Setup button in the browser"
    expected: "Button disables, shows 'Exiting...', status text updates to 'Wizard shut down. You can close this tab.', and server process terminates within 3 seconds"
    why_human: "Requires a live browser session; end-to-end button interaction cannot be verified by grep or unit test alone"
  - test: "Send Ctrl-C while wizard is running"
    expected: "Process exits cleanly, terminal prints 'Setup wizard exited cleanly.', no orphaned python processes remain"
    why_human: "Interactive terminal signal delivery; automated tests mock os.kill so the atexit/_cleanup path is not exercised live"
  - test: "Run ./scripts/setup.sh in a directory without write permission (chmod 555 on repo root)"
    expected: "Server prints clear error to stderr and exits before Flask starts; no browser window opens"
    why_human: "Pre-flight path requires manipulating filesystem permissions and observing stderr output — not safely automatable in CI"
---

# Phase 1: Server Foundation Verification Report

**Phase Goal:** The wizard process runs reliably — it finds a free port, opens the browser at the right moment, survives Ctrl-C cleanly, and refuses to start if it cannot write to the project directory.
**Verified:** 2026-04-19
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

All must-haves from Plans 01, 02, and 03 were checked against the actual codebase. Truths are grouped by plan.

**Plan 01 truths (SRV-02, SRV-04 partial, SRV-01 partial)**

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `python -m setup.server` binds to a port that is not 5000 or 8080 | VERIFIED | `find_free_port()` prefers 7331; fallback uses `socket.bind(('', 0))`; grep for 5000/8080 in server.py returns only a docstring comment, no hardcoded value |
| 2 | If preferred port 7331 is taken, server binds to a random OS-assigned port | VERIFIED | OSError branch in `find_free_port()` binds `('', 0)` and returns `getsockname()[1]`; `test_find_free_port_falls_back` passes |
| 3 | Browser opens only after socket probe confirms server is accepting connections | VERIFIED | `open_browser_after_ready()` calls `wait_for_port(port)` before `subprocess.Popen(['open', url])` / `webbrowser.open(url)`; no `time.sleep()` in that function |
| 4 | If project directory is not writable, server prints clear error and exits before Flask starts | VERIFIED | `main()` calls `check_write_permission(REPO_ROOT)` first; on False prints to stderr and calls `sys.exit(1)` before `app.run()` (lines 89–95) |
| 5 | Placeholder page loads at http://127.0.0.1:{PORT}/ confirming server is running | VERIFIED | `index.html` is valid HTML5, renders `{{ port }}` in a `<p>` tag, `<h1>Setup Wizard</h1>` present; GET / route uses `render_template('index.html', port=_port)` |

**Plan 02 truths (SRV-01)**

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 6 | Running `./scripts/setup.sh` activates the venv and launches the wizard | VERIFIED (automated partial) | Script is executable (`-rwxr-xr-x`), passes `bash -n`, activates `.venv`, installs requirements, then runs `python -m setup.server`; live browser launch requires human test |
| 7 | `setup/requirements.txt` lists `flask>=3.1.0` and `python-dotenv>=1.0.0` | VERIFIED | File contains exactly those two lines, no extras |
| 8 | `setup.sh` is executable and uses the project venv at `.venv/` | VERIFIED | `ls -la` confirms `-rwxr-xr-x`; script sources `$REPO_ROOT/.venv/bin/activate` |
| 9 | After setup.sh exits, the terminal prints the next-step command | VERIFIED | Lines 19–23 echo "Setup complete." and `./scripts/run-workflow.sh` after `python -m setup.server` returns |

**Plan 03 truths (SRV-03, SRV-04)**

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 10 | POST /exit causes the Flask process to terminate without deadlock | VERIFIED (unit) | `/exit` route starts `threading.Thread(target=_shutdown_server, daemon=True)` before returning `jsonify({"ok": True})`; `_shutdown_server()` uses `os.kill(os.getpid(), SIGINT)` not `server.shutdown()`; `test_exit_route_returns_ok` passes |
| 11 | The index.html Exit Setup button is wired to POST /exit | VERIFIED | `fetch('/exit', {method: 'POST', ...})` in `<script>` block on button click; button disabled and status text updated on response |

**Score:** 11/11 truths verified (automated) + 4 items require human confirmation for live behavior

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `setup/__init__.py` | Makes setup/ a Python package | VERIFIED | Exists, contains `# setup package` comment |
| `setup/server.py` | Flask app with port probing, pre-flight, browser auto-open, shutdown | VERIFIED | 108 lines; exports `app`, `find_free_port`, `wait_for_port`, `check_write_permission`, `open_browser_after_ready`, `_shutdown_server`, `_cleanup`, `main` |
| `setup/templates/index.html` | Placeholder wizard page | VERIFIED | Valid HTML5, no CDN links, renders `{{ port }}`, has `#status` and `#exit-btn`, wired `fetch('/exit')` script |
| `setup/requirements.txt` | Wizard pip dependencies | VERIFIED | Exactly `flask>=3.1.0` and `python-dotenv>=1.0.0` |
| `scripts/setup.sh` | Shell entry point | VERIFIED | Executable, strict mode, venv guard, pip install -q, `python -m setup.server`, post-exit echo |
| `setup/tests/test_server_lifecycle.py` | 6 unit tests | VERIFIED | All 6 pass: `test_find_free_port_returns_preferred`, `test_find_free_port_falls_back`, `test_check_write_permission_true`, `test_check_write_permission_false`, `test_shutdown_sends_sigint`, `test_exit_route_returns_ok` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `find_free_port()` | `app.run()` | `_port` variable in `main()` | WIRED | `_port = find_free_port()` then `app.run(host='127.0.0.1', port=_port, ...)` (lines 97, 103) |
| `check_write_permission()` | `main()` startup | `sys.exit(1)` on failure before `app.run()` | WIRED | Lines 89–95: guard is first thing in `main()` |
| `open_browser_after_ready()` | `wait_for_port()` socket probe | daemon `threading.Thread` started before `app.run()` blocks | WIRED | Line 101: `open_browser_after_ready(url, _port)` before line 103 `app.run()` |
| POST `/exit` route handler | `_shutdown_server()` | `threading.Thread(target=_shutdown_server, daemon=True).start()` | WIRED | Line 82; response returned before signal fires due to 0.3s delay in `_shutdown_server` |
| `_shutdown_server()` | process SIGINT | `os.kill(os.getpid(), signal.SIGINT)` | WIRED | Line 68 |
| `atexit.register(_cleanup)` | `main()` | registered after write-permission check, before `app.run()` | WIRED | Line 99 |
| Exit Setup button | POST `/exit` | `fetch('/exit', {method: 'POST', ...})` in `<script>` | WIRED | `index.html` line 32 |
| `scripts/setup.sh` | `python -m setup.server` | `exec` after venv activation and pip install | WIRED | `setup.sh` line 17 |

### Data-Flow Trace (Level 4)

`server.py` and `index.html` serve a static placeholder page with no dynamic data beyond `_port`. No DB queries or external data sources are involved — this phase is infrastructure only. Level 4 data-flow trace is not applicable.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 6 unit tests pass | `python3 -m pytest setup/tests/test_server_lifecycle.py -v` | 6 passed in 0.44s | PASS |
| `server.shutdown()` not called from handler | `grep -n "^[^#]*server\.shutdown()" setup/server.py` | No match | PASS |
| Ports 5000/8080 not hardcoded | `grep -n "5000\|8080" setup/server.py` | Only docstring comment | PASS |
| threading.Thread wraps shutdown in /exit | `grep -n "threading.Thread.*_shutdown_server" setup/server.py` | Line 82 | PASS |
| os.kill SIGINT used | `grep -n "os.kill.*SIGINT" setup/server.py` | Line 68 | PASS |
| atexit registered in main | `grep -n "atexit.register" setup/server.py` | Line 99 | PASS |
| setup.sh passes bash syntax check | `bash -n scripts/setup.sh` | syntax OK | PASS |
| setup.sh is executable | `ls -la scripts/setup.sh` | `-rwxr-xr-x` | PASS |
| Actual browser launch in real session | Requires live run | Not testable programmatically | SKIP |
| Ctrl-C clean exit with atexit message | Requires interactive terminal | Not testable programmatically | SKIP |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SRV-01 | 01-02 | User can run `./scripts/setup.sh` and wizard launches in default browser automatically | VERIFIED (unit/static) + HUMAN NEEDED (live browser) | `setup.sh` wired correctly to `python -m setup.server`; browser auto-open logic wired via `open_browser_after_ready()`; live launch requires human |
| SRV-02 | 01-01 | Wizard probes for free port (avoiding 5000/8080), falls back to random available port | VERIFIED | `find_free_port()` implementation confirmed; unit tests pass; no hardcoded 5000/8080 |
| SRV-03 | 01-03 | Exit Setup button shuts down cleanly; Ctrl-C triggers atexit handler | VERIFIED (unit) + HUMAN NEEDED (Ctrl-C) | POST /exit wired, `_shutdown_server` uses SIGINT self-signal, atexit registered; Ctrl-C+atexit output requires human |
| SRV-04 | 01-01 + 01-03 | Pre-flight write permission check; clear error if not writable | VERIFIED (static) + HUMAN NEEDED (live) | `check_write_permission()` and `sys.exit(1)` path confirmed in code; live error surface requires human test |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `setup/templates/index.html` | 26–27 | `<p id="status">Loading...</p>` static initial text | Info | Intentional placeholder for Phase 2 form; does not block phase goal |
| `setup/server.py` | 67 | `time.sleep(0.3)` in `_shutdown_server()` | Info | Intentional: documented deviation from plan (needed to flush response before SIGINT with `threaded=False`); not a stub |

No blockers found. No TODOs or FIXME comments remain in the phase-1 files (the TODO comment from Plan 01 was replaced by the actual `/exit` route in Plan 03).

### Human Verification Required

#### 1. Live browser launch via setup.sh

**Test:** With a valid `.venv` present, run `./scripts/setup.sh` from the project root.
**Expected:** Terminal shows venv activation and pip install output; Flask starts on port 7331 (or fallback); default browser opens automatically at `http://127.0.0.1:7331/`; page displays "Setup Wizard" heading and port number.
**Why human:** Browser auto-open (`subprocess.Popen(['open', url])` / `webbrowser.open`) requires a display environment and a real browser; cannot be verified without a live process.

#### 2. Exit Setup button end-to-end

**Test:** With the wizard running in the browser, click the "Exit Setup" button.
**Expected:** Button becomes disabled and shows "Exiting...", status text changes to "Wizard shut down. You can close this tab.", Flask process terminates within 3 seconds, port 7331 is released (curl returns connection refused).
**Why human:** Requires a live browser session to observe button state transitions and confirm fetch → server shutdown → port release chain.

#### 3. Ctrl-C clean exit

**Test:** Start the wizard with `./scripts/setup.sh`, press Ctrl-C in the terminal.
**Expected:** Process exits, terminal prints "Setup wizard exited cleanly.", no orphaned `python` processes for `setup.server` remain (`pgrep -f "setup.server"` returns nothing).
**Why human:** Interactive terminal signal delivery; the atexit handler and cleanup print cannot be asserted without a real PTY session.

#### 4. Pre-flight write-permission rejection

**Test:** Temporarily make the project directory non-writable (`chmod 555 .`) and run `python -m setup.server`.
**Expected:** Server prints to stderr: "ERROR: Project directory ... is not writable. Cannot start setup wizard." and exits with code 1 before Flask binds any port. No browser window opens.
**Why human:** Requires filesystem permission manipulation; unsafe to automate without risk of leaving the repo in a broken state.

### Gaps Summary

No gaps. All 11 automated must-haves are verified against the actual codebase. The 4 human verification items above are behavioral live-run checks that cannot be automated by static analysis or unit tests — they are the final confirmation that the wired code actually works end-to-end. No missing artifacts, no stubs, no broken wiring, no blocker anti-patterns.

---

_Verified: 2026-04-19_
_Verifier: Claude (gsd-verifier)_
