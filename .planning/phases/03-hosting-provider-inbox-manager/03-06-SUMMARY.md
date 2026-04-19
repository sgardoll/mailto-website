---
phase: 03
plan: 06
subsystem: setup-wizard
tags: [css, ui, wizard, hosting, inbox]
requires:
  - 03-03-PLAN.md (hosting.html — references .provider-fields[hidden])
  - 03-04-PLAN.md (inboxes.html — references .inbox-row, .field-row-thirds, #add-inbox)
provides:
  - .provider-fields[hidden] visibility rule
  - .field-row-thirds 3-column grid
  - .inbox-row / .inbox-row-header / .inbox-row-label container styles
  - .remove-inbox + .remove-inbox:disabled button styles
  - #add-inbox link-style button
  - select + select:focus base styling
affects:
  - setup/static/wizard.css
tech-stack:
  added: []
  patterns:
    - Append-only CSS additions (no existing rule modified)
    - Comment-fenced phase block (`/* ── Phase 3 additions ── */`)
key-files:
  created: []
  modified:
    - setup/static/wizard.css (lines 266–344, +79 lines)
decisions:
  - Appended after the final existing rule rather than interleaving — preserves Phase 1/2 stylesheet exactly and makes the phase boundary auditable.
metrics:
  duration: ~5 min
  completed: 2026-04-19
requirements:
  - HOST-01
  - HOST-06
  - INBOX-01
  - INBOX-02
  - INBOX-03
---

# Phase 03 Plan 06: Wizard CSS Phase 3 Additions Summary

Append-only CSS additions to `setup/static/wizard.css` providing select styling, conditional provider-field hiding, three-column row layout, and the inbox row container plus add/remove button styles needed by the hosting and inbox steps.

## What Shipped

- **select / select:focus** — matches the existing input field appearance (same border, padding, font-size, focus ring) so the provider dropdown is visually consistent with the rest of the wizard.
- **.provider-fields[hidden]** — `display: none` rule that lets the hosting step show only the active provider's fields by toggling the `hidden` attribute from JS.
- **.field-row-thirds** — CSS Grid with `1fr 1fr 1fr` and a 16px gap; used by the inbox row's site-name + URL + base-path row.
- **.inbox-row, .inbox-row-header, .inbox-row-label** — light-grey card container (`#f3f4f6`, 1px `#d1d5db` border, 8px radius, 16px padding) with a flex header for label + remove-button alignment.
- **.remove-inbox / .remove-inbox:disabled** — matches the existing `.remove-sender` button pattern (44px min-height, white background, red text, disabled state).
- **#add-inbox** — matches the existing `#add-sender` link-style button (blue text, underline, no border/background).

All rules sit inside a single `/* ── Phase 3 additions ── */` block appended after the previous final rule (`.field-row:has(input[type="checkbox"]) label`).

## Verification

| Check | Expected | Actual |
|------|----------|--------|
| Line count grew | > 265 | 343 |
| `.provider-fields[hidden]` | 1 | 1 |
| `.field-row-thirds` | 1 | 1 |
| `inbox-row` matches | ≥ 3 | 3 |
| `remove-inbox` matches | 2 | 2 |
| `#add-inbox` | 1 | 1 |
| `.remove-sender` rule lines | 149, 161 unchanged | 149, 161 unchanged |
| `.toggle-visibility` rule lines | 124, 136 unchanged | 124, 136 unchanged |
| `.field-row-split` rule line | 71 unchanged | 71 unchanged |

Note: `grep -c remove-sender` returns 3 (was 2) because the new block contains the comment "Remove inbox button — matches remove-sender". The underlying `.remove-sender` selector and `.remove-sender:disabled` rule are unchanged at lines 149/161.

## Deviations from Plan

None — plan executed exactly as written.

## Threat Surface

T-03-06-01 (CSS tampering) — accepted; static asset, no runtime modification path. No new threat surface introduced.

## Commits

- `6c3c876` — feat(03-06): append Phase 3 CSS rules to wizard.css

## Self-Check: PASSED

- FOUND: setup/static/wizard.css (modified, +79 lines)
- FOUND: commit 6c3c876
- FOUND: .planning/phases/03-hosting-provider-inbox-manager/03-06-SUMMARY.md
