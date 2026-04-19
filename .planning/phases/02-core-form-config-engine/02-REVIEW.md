---
status: issues_found
phase: 02-core-form-config-engine
files_reviewed:
  - setup/builder.py
  - setup/tests/test_builder.py
  - setup/templates/index.html
  - setup/server.py
  - setup/static/wizard.css
  - setup/static/wizard.js
  - setup/requirements.txt
findings:
  critical: 2
  warning: 1
  info: 0
  total: 3
depth: standard
---

# Phase 02 Code Review

## Critical

### CR-01: No CSRF protection on POST routes — any local page can kill the wizard

**File:** `setup/server.py` — `/exit` (line ~93) and `/validate-form` (line ~82)
**Confidence:** 85

`/exit` and `/validate-form` are unauthenticated POST endpoints with no CSRF token and no `Origin`/`Referer` check. `get_json(force=True)` disables the Content-Type guard. Any page open in the browser — a malicious ad, a locally-served page, or another open tab — can `fetch('http://127.0.0.1:7331/exit', {method:'POST'})` and kill the wizard process. The port is predictable (preferred 7331; printed to stdout).

**Fix:** Generate a startup secret (`secrets.token_hex(16)`), store in Flask `app.config`. Require it as `X-Wizard-Token` header on all POST routes. Embed it in a `<meta>` tag in the template; `wizard.js` reads it and sends it with every fetch call.

---

### CR-02: `builder.build(_wizard_state)` uses accumulated global dict, not validated payload

**File:** `setup/server.py` — `/validate-form` route, line ~88-89
**Confidence:** 80

`_wizard_state.update(data)` grows the global dict, then `builder.build(_wizard_state)` is called with the accumulated state rather than the freshly validated `data`. If a prior request left a non-numeric `lms_temperature` or `lms_max_tokens` in `_wizard_state`, `build()` will crash with an unhandled `ValueError` from `float()`/`int()` in `builder.py`, returning an unhandled 500 to the browser.

**Fix:** Replace `builder.build(_wizard_state)` with `builder.build(data)`. The `_wizard_state` accumulation pattern is only needed for multi-step state that spans separate route calls; within a single `/validate-form` POST, `data` is already the complete validated payload.

---

## Warning

### WR-01: `find_free_port` docstring promises 5000/8080 exclusion but code doesn't enforce it

**File:** `setup/server.py` — `find_free_port()`, lines ~15-26
**Confidence:** 80

The OS fallback path (`sock.bind(('', 0))`) returns any OS-assigned ephemeral port unconditionally. The OS can assign 5000 (AirPlay Receiver on macOS) or 8080 (common dev HTTP alt port) if they happen to be available. The docstring claim is false.

**Fix:** Filter the OS-assigned port against an exclusion set `{5000, 8080}` and retry if hit, or iterate over a fixed candidate range excluding those ports.
