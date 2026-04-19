---
status: partial
phase: 02-core-form-config-engine
source: [02-VERIFICATION.md]
started: "2026-04-19T00:00:00.000Z"
updated: "2026-04-19T00:00:00.000Z"
---

## Current Test

[awaiting human testing]

## Tests

### 1. Blur validation
expected: When you tab out of a required field without entering a value, an inline error message appears on that field immediately — before form submission.
result: [pending]

### 2. Show/Hide toggle on Gmail app password
expected: Clicking "Show" on the app password field reveals the password text; clicking "Hide" hides it again. The field remains pasteable in both states.
result: [pending]

### 3. Gmail fan-out live preview
expected: Typing a Gmail address into the gmail-address field immediately updates the IMAP user preview and SMTP user preview text shown in the derived-values paragraph below the field.
result: [pending]

### 4. End-to-end config output
expected: Filling in the form and clicking "Save & Continue" sends a POST to /validate-form and returns a 200 JSON response containing env_preview (with the raw app password as GMAIL_APP_PASSWORD=...) and yaml_preview (with ${GMAIL_APP_PASSWORD} reference, not the raw password).
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
