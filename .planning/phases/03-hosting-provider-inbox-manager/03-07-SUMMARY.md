---
phase: 03-hosting-provider-inbox-manager
plan: 07
subsystem: ui
tags: [vanilla-js, dom, validation, fetch]

requires:
  - phase: 03-hosting-provider-inbox-manager
    provides: hosting.html and inboxes.html templates (Plans 03-03/03-04), Phase 3 CSS (Plan 03-06)
provides:
  - Phase 3 client-side behavior for hosting and inboxes wizard steps
  - Provider show/hide on hosting page
  - Inbox row template cloning, blur validation, slug uniqueness
  - Form submission to /validate-form with step dispatch
affects: [04-preview-write-flow]

tech-stack:
  added: []
  patterns:
    - Independent IIFEs per phase (Phase 3 code appended; Phase 2 IIFE untouched)
    - Per-IIFE scoped helpers (showFieldError, attachFieldValidation) re-defined since IIFE scoping prevents reuse
    - Touched-flag pattern for blur-then-input validation
    - Server-driven navigation via window.location.href = data.next_step

key-files:
  created: []
  modified:
    - setup/static/wizard.js (lines 1-350 unchanged; +601 lines for hosting + inboxes IIFEs)

key-decisions:
  - "Three independent IIFEs in wizard.js — Phase 2 (lines 1-350), Phase 3 hosting (351-620), Phase 3 inboxes (621-951). Each defines its own helpers because IIFE scoping prevents calling the others' internals."
  - "validateAllSlugs only overrides field errors when the prior message was the duplicate-slug message — preserves per-field 'Slug is required' / format errors."
  - "Inbox counter is a persistent monotonic integer; never reused even after row removal, preventing ID collisions per T-03-07-02."

patterns-established:
  - "Phase code is appended, not interleaved — keeps prior phases bit-identical and preserves git blame"
  - "Form submit handlers POST {step: '<step>', ...fields} to /validate-form and navigate via response.next_step"
  - "Server error mapping by row index for repeated-row payloads (inboxes)"

requirements-completed: [HOST-01, HOST-02, HOST-03, HOST-04, HOST-05, HOST-06, INBOX-01, INBOX-02, INBOX-03, INBOX-04]

duration: ~3min
completed: 2026-04-19
---

# Phase 03 Plan 07: Wizard JS for Hosting & Inboxes Summary

**Two new IIFEs appended to wizard.js: initHostingStep() handles provider switching, blur validation, and SSH at-least-one credential rule; initInboxesStep() handles row template cloning, per-field validation, and slug uniqueness across rows.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-19T08:38:57Z
- **Completed:** 2026-04-19T08:41:25Z
- **Tasks:** 2
- **Files modified:** 1 (setup/static/wizard.js: 350 → 951 lines)

## Accomplishments
- Provider show/hide on hosting page driven by `<select>` change with initial render matching the select value
- Blur validation across all SiteGround, SSH/SFTP, Netlify, Vercel, GitHub Pages fields with field-specific error copy
- SSH at-least-one credential rule wired to both key_path and password blur events
- Inbox row cloning from `<template>` with auto-incremented IDs, aria-describedby, and label `for` attributes
- Slug uniqueness validated on every slug blur across all rows; duplicate flag is non-destructive (preserves per-field errors)
- Form submission for both steps POSTs to `/validate-form` with `step` field and navigates via `next_step`
- Server error mapping by `index` field routes inbox-row errors to the correct row

## Task Commits

1. **Task 1: Append initHostingStep** — `e536da8` (feat)
2. **Task 2: Append initInboxesStep** — `caa8a09` (feat)

**Plan metadata:** pending (this commit)

## Files Created/Modified
- `setup/static/wizard.js` — appended 601 lines (two IIFEs); original lines 1-350 untouched

## Decisions Made
- See key-decisions in frontmatter; all followed plan specification exactly. The IIFE-isolation tradeoff (helpers re-declared) is a deliberate consequence of leaving Phase 2 code untouched.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None.

## Next Phase Readiness
- Phase 3 client behavior is feature-complete
- All 46 setup/tests/ tests still pass
- Ready for end-to-end verification (manual UAT against the running wizard)
- Phase 4 (preview + write flow) can begin once Phase 3 verifier completes

## Self-Check: PASSED

Verified:
- `setup/static/wizard.js` exists and is 951 lines (350 original + 601 appended)
- `grep -c "})();"` returns 3 (original IIFE + hosting IIFE + inboxes IIFE)
- Original line 350 unchanged (`})();`)
- Commit `e536da8` present on main
- Commit `caa8a09` present on main
- All 46 tests pass: `uv run python -m pytest setup/tests/ -q` → 46 passed in 0.43s

---
*Phase: 03-hosting-provider-inbox-manager*
*Completed: 2026-04-19*
