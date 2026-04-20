---
phase: 14-foundation
plan: 02
subsystem: spa-shell
tags: [spa, manifest, shell, window-state, window-ai, hash-routing, iframe, v2.0, foundation]

# Dependency graph
requires: [14-01]
provides:
  - "spa_manifest_schema.json (JSON Schema draft-07 for spa_manifest.json)"
  - "seed spa_manifest.json (empty modules array)"
  - "shell.html with window.STATE, window.AI(), hash-based navigation, sandboxed iframe"
affects: [17-build-validator, 18-integrate-orchestrator]

# Tech tracking
tech-stack:
  added: []
  patterns: [localStorage proxy via window.STATE, LM Studio bridge via window.AI(), hash-based SPA navigation, iframe sandbox isolation]

key-files:
  created:
    - packages/config_contract/spa_manifest_schema.json
    - packages/site-template/public/spa/spa_manifest.json
    - packages/site-template/public/spa/shell.html
  modified: []

key-decisions:
  - "iframe sandbox='allow-scripts' only — allow-same-origin explicitly excluded per SPA-04"
  - "window.AI endpoint hardcoded to localhost:1234 — Phase 18 adds proxy routing"
  - "Zero external dependencies — no Alpine.js, no Tailwind, no CDN in shell (those belong to generated modules)"
  - "STATE + AI scripts in <head>, routing script at end of <body> — ordering enforced"

patterns-established:
  - "localStorage proxy pattern: window.STATE wraps get/set/remove with JSON parse/stringify"
  - "LM Studio bridge pattern: window.AI() wraps fetch to localhost:1234/v1/chat/completions"
  - "Hash routing pattern: hashchange event + fetch('spa_manifest.json') on init"

requirements-completed: [SPA-01, SPA-02, SPA-03, SPA-04]

# Metrics
duration: 15min
completed: 2026-04-20
---

# Phase 14 Plan 02: Foundation Summary

**SPA shell infrastructure — JSON Schema, seed manifest, and shell.html with STATE/AI injection, hash routing, sandboxed iframes**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-04-20
- **Tasks:** 4 (3 auto + 1 human-verify checkpoint)
- **Files created:** 3

## Accomplishments

- Created `packages/config_contract/spa_manifest_schema.json` — JSON Schema draft-07 enforcing `schema_version` + `modules[]` required fields, `kind` constrained to 5 MechanicKind values, `additionalProperties: false` on root and module items
- Created `packages/site-template/public/spa/spa_manifest.json` — seed manifest with empty `modules` array; prevents 404 on first shell load before any module is added
- Created `packages/site-template/public/spa/shell.html` — minimal SPA shell with:
  - `window.STATE` localStorage proxy (get/set/remove with JSON serialisation) injected before any other script
  - `window.AI()` async bridge to `http://localhost:1234/v1/chat/completions` injected second
  - Hash-based navigation reading `spa_manifest.json` on load
  - `<iframe sandbox="allow-scripts">` (no `allow-same-origin`) for module isolation per SPA-04
  - Empty-state copy: "No modules yet. Send an email to add one."
  - Error-state copy: "Could not load spa_manifest.json. Check the file exists at public/spa/spa_manifest.json."
- Human browser verification passed: STATE/AI console messages confirmed in order, STATE round-trip (`set`/`get`/`remove`) verified, iframe sandbox attribute confirmed, no console errors

## Task Commits

1. **Task 1: spa_manifest_schema.json** — `a05e58c` (feat)
2. **Task 2: seed spa_manifest.json** — `310548c` (included in project-name commit)
3. **Task 3: shell.html** — `36d8b68` (feat)
4. **Task 4: Human verify** — approved by user

## Script Ordering (verified)

| Position | Script | Location |
|----------|--------|----------|
| 1 | window.STATE | `<head>` block 1 |
| 2 | window.AI() | `<head>` block 2 |
| 3 | `<iframe>` element | `<body>` |
| 4 | routing + init() | End of `<body>` |

## Deviations from Plan

None — all acceptance criteria pass.

## Threat Flags

- T-14-02-01 mitigated: iframe `sandbox="allow-scripts"` only, no same-origin
- T-14-02-02 mitigated: buildNav uses DOM methods + textContent, no innerHTML injection
- T-14-02-03 accepted: localStorage inaccessible to sandboxed iframes by design
- T-14-02-04 accepted: localhost endpoint by design; proxy added in Phase 18
- T-14-02-05 mitigated: fetch failure renders error copy, shell stays navigable
- T-14-02-06 mitigated: no innerHTML in routing logic

## Next Phase Readiness

- Shell is the runtime surface for all Phase 17-generated modules — they load inside the sandboxed iframe
- Phase 18 INTEGRATE will atomically update `spa_manifest.json` with new module entries
- `window.STATE` and `window.AI()` are available to all modules via `window.parent.STATE` / `window.parent.AI`

---
*Phase: 14-foundation*
*Completed: 2026-04-20*
