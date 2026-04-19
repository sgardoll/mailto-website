---
status: partial
phase: 03-hosting-provider-inbox-manager
source: [03-VERIFICATION.md]
started: 2026-04-19T08:46:30Z
updated: 2026-04-19T08:46:30Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Provider dropdown visual show/hide
expected: Selecting Netlify hides SiteGround/SSH/Vercel/GitHub Pages groups; only Netlify fields remain
result: [pending]

### 2. Remove button disabled on last inbox row
expected: First row's Remove button is visibly disabled; after adding a second and removing it, the remaining row's button becomes disabled again
result: [pending]

### 3. Slug uniqueness inline error on blur
expected: Inline 'Slug must be unique across all inboxes' error appears on the duplicate field after blur
result: [pending]

### 4. Step navigation after hosting submit
expected: Submitting hosting form with GitHub Pages selected navigates the browser to /step/inboxes
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
