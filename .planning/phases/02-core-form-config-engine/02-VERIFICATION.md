---
phase: 02-core-form-config-engine
verified: 2026-04-19T00:00:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Open the wizard in a browser (./scripts/setup.sh) and tab through each required field blank — verify inline error appears per field on blur, not on submit"
    expected: "gmail-address, gmail-app-password, lms-base-url, lms-model, lms-cli-path each show their respective error messages when left blank and tabbed away from"
    why_human: "Blur validation requires real browser DOM and focus events — cannot be triggered programmatically in a unit test context"
  - test: "Click the show/hide toggle on the app password field and verify (a) field becomes readable, (b) button text changes to 'Hide', (c) field is still paste-friendly"
    expected: "input type toggles between 'password' and 'text'; button text is 'Show'/'Hide'; aria-pressed updates; pasting still works"
    why_human: "Password field type toggle and paste behaviour require an actual browser"
  - test: "Type a Gmail address (e.g. test@gmail.com) into the gmail-address field and verify that the derived-values paragraph updates live with that address in both the imap and smtp preview codes"
    expected: "Both <code id='imap-user-preview'> and <code id='smtp-user-preview'> show 'test@gmail.com' immediately on input"
    why_human: "Live DOM text update via input event requires a browser with a live JS runtime"
  - test: "Inspect the generated YAML by submitting a valid form — verify that config.yaml output string contains '${GMAIL_APP_PASSWORD}' literally and NOT the actual password value, and that .env output string contains 'GMAIL_APP_PASSWORD=<actual-password>'"
    expected: "yaml_preview in server JSON response contains '${GMAIL_APP_PASSWORD}'; env_preview contains the raw password; the two are never swapped"
    why_human: "End-to-end UX review of the config preview output — visually confirm correct separation on a real form submission"
---

# Phase 2: Core Form & Config Engine — Verification Report

**Phase Goal:** Users can fill in Gmail credentials and LM Studio settings through a polished, validated form, and the underlying builder/validator logic produces correct .env and config.yaml output strings
**Verified:** 2026-04-19
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A visible progress indicator names all wizard steps and highlights the active one | VERIFIED | `<nav class="wizard-steps">` present in index.html with 5 steps (Gmail Setup, LM Studio, Hosting, Inboxes, Preview & Write); `active_step='gmail'` passed from server.py; Jinja2 loop applies `class="active"` and `aria-current="step"` to the matching step |
| 2 | Leaving a required field blank and tabbing away shows an inline error on that field — not on submit | VERIFIED (human confirm) | wizard.js implements `attachValidation()` with a `touched` flag — blur sets `touched=true` then calls rule; each of 8 fields has a rule function; `{id}-error` spans with `hidden` and `aria-live="polite"` are present in HTML; JS wires all 8 fields |
| 3 | Every password or token field has a show/hide toggle and remains pasteable | VERIFIED (human confirm) | `<button class="toggle-visibility" data-target="gmail-app-password">` in HTML; wizard.js `querySelectorAll('.toggle-visibility')` click handler toggles `input.type` between `'password'` and `'text'`; input remains a standard text field — paste-friendly by browser default |
| 4 | Each field has help text and a link to the relevant external documentation page | VERIFIED | All `<small id="{id}-help" class="help-text">` elements present in index.html for every field; gmail-address help links to support.google.com; gmail-app-password links to myaccount.google.com/apppasswords; lms-base-url links to lmstudio.ai/docs |
| 5 | Entering a Gmail address once populates imap.user, smtp.user, and smtp.from_address; app password in .env, ${GMAIL_APP_PASSWORD} in config.yaml | VERIFIED | builder.py `build()` fans `email` into `imap.user`, `smtp.user`, `smtp.from_address`; env_str = `f"GMAIL_APP_PASSWORD={...}\n"`; yaml uses `'${GMAIL_APP_PASSWORD}'` literal; test `test_build_gmail_address_fans_out` passes; test `test_build_yaml_references_env_var_not_password` passes |

**Score:** 5/5 truths verified (3 require human browser confirmation for the UX layer)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `setup/builder.py` | validate() and build() pure functions | VERIFIED | 63 lines; exports `validate`, `build`, `DEFAULTS`; no Flask imports; no file I/O; `yaml.dump()` with all three required kwargs |
| `setup/tests/test_builder.py` | Unit + integration tests | VERIFIED | 165 lines; 15 test functions; all 15 pass via `.venv/bin/python3 -m pytest` |
| `setup/templates/index.html` | Full wizard form | VERIFIED | 221 lines; `class="wizard-steps"`, `id="wizard-form"`, all field IDs, no inline `<style>` or `<script>` blocks |
| `setup/static/wizard.css` | All Phase 2 styles | VERIFIED | 264 lines (>=120 required); all design tokens applied; no `@import`, no `var(--` |
| `setup/static/wizard.js` | Client-side interactivity | VERIFIED | 350 lines (>=150 required); 0 `console.log`; 0 arrow functions; IIFE + `'use strict'` |
| `setup/server.py` | POST /validate-form route + _wizard_state | VERIFIED | `_wizard_state = {}` at module level; `@app.route('/validate-form', methods=['POST'])`; `active_step='gmail'` in GET /; `import setup.builder as builder` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `setup/builder.py` | `workflow/config.example.yaml` | Key names and structure match | VERIFIED | builder emits `global_allowed_senders`, `imap`, `smtp`, `lm_studio` — matching the config.example.yaml section scope |
| `setup/tests/test_builder.py` | `setup/builder.py` | `from setup.builder import validate, build` | VERIFIED | Import present on line 7; all 15 tests collected and pass |
| `setup/templates/index.html` | `setup/static/wizard.css` | `url_for('static', filename='wizard.css')` | VERIFIED | Line 7 of index.html |
| `setup/templates/index.html` | `setup/static/wizard.js` | `url_for('static', filename='wizard.js')` | VERIFIED | Line 219 of index.html |
| `setup/templates/index.html` | `setup/server.py` | `{{ active_step }}` Jinja2 variable | VERIFIED | `active_step='gmail'` passed in `render_template` call in server.py line 79 |
| `setup/static/wizard.js` | `setup/templates/index.html` | `getElementById('gmail-address')` | VERIFIED | All 8 field IDs targeted by `attachValidation()` match index.html field IDs exactly |
| `setup/static/wizard.js` | `setup/server.py POST /validate-form` | `fetch('/validate-form', {method: 'POST'})` | VERIFIED | Line 290 of wizard.js |
| `setup/server.py POST /validate-form` | `setup/builder.py validate() and build()` | `builder.validate(data)` / `builder.build(_wizard_state)` | VERIFIED | Lines 85 and 89 of server.py |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `setup/server.py /validate-form` | `data` from `request.get_json()` | Browser POST body | Yes — user-entered form values | FLOWING |
| `setup/builder.py build()` | `form_data` dict | Caller passes `_wizard_state` | Yes — real form data via `.update(data)` | FLOWING |
| `setup/builder.py build()` | `env_str` / `yaml_str` | `yaml.dump(config, ...)` | Yes — real config values, not hardcoded | FLOWING |
| `setup/static/wizard.js` | `payload` | DOM `getElementById` reads on submit | Yes — real input values from user | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 15 builder + route tests pass | `.venv/bin/python3 -m pytest setup/tests/test_builder.py -v` | 15 passed in 0.10s | PASS |
| All 21 tests pass (both test files) | `.venv/bin/python3 -m pytest setup/tests/ -v` | 21 passed in 0.37s | PASS |
| builder.py importable, exports correct symbols | `.venv/bin/python3 -c "from setup.builder import validate, build, DEFAULTS; print('OK')"` | OK | PASS |
| server.py importable after Phase 2 changes | `.venv/bin/python3 -c "from setup.server import app; print('OK')"` | OK | PASS |
| `build()` produces correct env_str format | Covered by `test_build_env_str_contains_app_password` | `GMAIL_APP_PASSWORD=abcd efgh ijkl mnop\n` | PASS |
| `build()` uses `${GMAIL_APP_PASSWORD}` reference in yaml | Covered by `test_build_yaml_references_env_var_not_password` | Reference present; raw password absent | PASS |
| Fan-out: gmail_address populates imap.user, smtp.user, smtp.from_address | Covered by `test_build_gmail_address_fans_out` | All three match | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| UX-01 | 02-03, 02-06 | Progress indicator showing all steps and active one | SATISFIED | `<nav class="wizard-steps">` with 5 named steps; `active_step='gmail'` highlights Gmail step |
| UX-02 | 02-05 | Blur validation — errors on field blur, not only submit | SATISFIED | `attachValidation()` with `touched` flag in wizard.js; 8 fields wired |
| UX-03 | 02-03, 02-05 | Show/hide toggle on password/token fields | SATISFIED | `toggle-visibility` button in HTML; click handler in wizard.js toggles `input.type` |
| UX-04 | 02-03 | Help text and external documentation links per field | SATISFIED | All `{id}-help` small elements present with help copy and links in index.html |
| GMAIL-01 | 02-02, 02-05 | Gmail address fans out to imap.user, smtp.user, smtp.from_address | SATISFIED | builder.py `build()` confirmed by test; wizard.js preview updates in DOM |
| GMAIL-02 | 02-02 | App password in .env as GMAIL_APP_PASSWORD; referenced as ${GMAIL_APP_PASSWORD} in config.yaml | SATISFIED | builder.py `build()` confirmed by `test_build_yaml_references_env_var_not_password` and `test_build_env_str_contains_app_password` |
| GMAIL-03 | 02-02, 02-03 | Gmail folder field with default INBOX | SATISFIED | `id="gmail-folder"` with `value="INBOX"` in HTML; `gmail_folder` key in DEFAULTS dict |
| GMAIL-04 | 02-02, 02-03, 02-05 | Allowed senders list (at least one required) | SATISFIED | `sender-input` widget in HTML; `validate()` enforces `isinstance(senders, list) and len >= 1`; wizard.js senders widget + form collect |
| LMS-01 | 02-02, 02-03 | LM Studio base URL field with default pre-filled | SATISFIED | `id="lms-base-url"` with `value="http://localhost:1234/v1"` in HTML; DEFAULTS key present |
| LMS-02 | 02-02, 02-03 | Model tag field with default pre-filled | SATISFIED | `id="lms-model"` with `value="google/gemma-4-26b-a4b"` in HTML; DEFAULTS key present |
| LMS-03 | 02-02, 02-03 | Temperature and max_tokens with defaults | SATISFIED | Both fields in HTML with `value="0.4"` and `value="4096"`; `test_build_advanced_fields_included` passes |
| LMS-04 | 02-02, 02-03 | lms CLI path field with default pre-filled | SATISFIED | `id="lms-cli-path"` with `value="lms"` in HTML; DEFAULTS key present |

All 12 Phase 2 requirement IDs are satisfied. No orphaned requirements.

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| None found | — | — | — |

No `TODO`, `FIXME`, `placeholder`, `return null`, `return {}`, or `return []` patterns detected in the key files. No stub implementations found. `builder.py` has no Flask imports and no file I/O. wizard.js has 0 `console.log` matches and 0 arrow function matches. wizard.css has no `@import` and no `var(--` CSS custom properties.

### Human Verification Required

#### 1. Blur Validation UX

**Test:** Open wizard in browser via `./scripts/setup.sh`. Click on the gmail-address field, leave it empty, then press Tab. Repeat for gmail-app-password (fewer than 16 chars), lms-base-url (invalid URL), lms-model (empty), and lms-cli-path (empty).
**Expected:** Each field shows its specific error message immediately on blur — before the form is submitted. Errors appear in the `{id}-error` span below the field, not in a global banner.
**Why human:** Blur event + `touched` flag pattern cannot be triggered in Flask's test client. Requires a live browser DOM.

#### 2. Show/Hide Toggle Behaviour

**Test:** Click the "Show" button next to the Gmail app password field.
**Expected:** Field content becomes readable (type changes to text); button text changes to "Hide"; aria-label and aria-pressed update accordingly; pasting a new password into the now-visible field works normally.
**Why human:** DOM type attribute toggle and paste-friendliness require a real browser.

#### 3. Gmail Fan-Out Live Preview

**Test:** Type any Gmail address into the gmail-address field while watching the derived-values paragraph below it.
**Expected:** Both `<code id="imap-user-preview">` and `<code id="smtp-user-preview">` update in real time with the address being typed, demonstrating the fan-out before any form submission.
**Why human:** Live `input` event DOM mutation requires a browser with a running JS engine.

#### 4. End-to-End Config Generation Preview

**Test:** Fill in the full form (valid gmail address, valid 16-char app password, at least one allowed sender, LM Studio defaults), then click "Save & Continue".
**Expected:** No page navigation occurs (JS-handled); form-error-summary remains hidden; browser devtools Network tab shows a 200 response from `/validate-form` with JSON containing `"ok": true`, `"env_preview": "GMAIL_APP_PASSWORD=...\n"`, and `"yaml_preview"` containing `${GMAIL_APP_PASSWORD}` as a literal string (not the actual password).
**Why human:** End-to-end form submission with visual inspection of the JSON response body and confirmation that secret separation is correct in the output strings.

### Gaps Summary

No gaps found. All 5 roadmap success criteria are verified by code inspection and automated tests. All 12 Phase 2 requirements (UX-01 through UX-04, GMAIL-01 through GMAIL-04, LMS-01 through LMS-04) have implementation evidence.

The 4 human verification items are UX-layer checks that require a browser — the underlying code that drives those behaviours (wizard.js, server.py route, index.html structure) is fully implemented and wired. Human verification confirms the user-facing experience, not whether the implementation exists.

---

_Verified: 2026-04-19_
_Verifier: Claude (gsd-verifier)_
