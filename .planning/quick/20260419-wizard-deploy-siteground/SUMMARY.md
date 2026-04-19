---
slug: wizard-deploy-siteground
status: complete
completed: 2026-04-19
commit: 07f20c7
---

# Wizard-driven Deploy — SiteGround

After config write, the wizard success screen now deploys the per-inbox Astro
site(s) to the configured SiteGround target and shows per-inbox progress +
final URLs. Non-SiteGround providers show honest "not implemented" guidance
pending Phase 5.

## Why this scope

The 4 other providers the wizard collects (Netlify / Vercel / GitHub Pages /
Generic SSH) have zero server-side deploy code today. `workflow/config.py`
only defines `SiteGroundConfig` and silently ignores the other provider
blocks the wizard writes. Adding real deploy support for them is a proper
new phase (Phase 5) — user chose "SiteGround-only now, defer others".

## What was built

### `workflow/deploy_once.py` (new)
Reusable bootstrap → build → deploy loop with a phase-level progress
callback. Exposes `deploy_all(cfg, on_progress)` for the wizard and
`main()` for `python -m workflow.deploy_once` CLI use.

### `setup/server.py`
- `POST /deploy` — validates `hosting_provider == 'siteground'`, else
  returns 400 with `error=not_implemented`. Spawns a daemon thread,
  re-entrant safe.
- `GET /deploy-status` — snapshot for 2s polling.
- `/step/done` now passes `hosting_provider` + `inboxes` into the template.

### `setup/templates/done.html`
Provider-aware branches: SiteGround → Deploy Site button + pre-rendered
per-inbox progress panel. Others → targeted manual-setup guidance.

### `setup/static/wizard.js`
`initDoneStep()` wires click → POST /deploy → poll loop → update each
inbox row with phase + final URL / error.

### `setup/static/wizard.css`
`.deploy-panel`, `.deploy-row`, `.deploy-phase-badge` (state-aware via
`[data-phase]`) in existing token language.

### `setup/tests/test_phase4_flow.py`
Replaced the two done-route tests with 10 new tests. External side
effects (config load, bootstrap, npm, SFTP) fully monkeypatched.

## Tests

`.venv/bin/python -m pytest setup/tests/ -q` → **88 passed** (was 78).

## Deferred (Phase 5)

- Netlify / Vercel / GitHub Pages / Generic SSH deploy implementations
- Provider dataclasses in `workflow/config.py`
- Streaming npm/SFTP output (current: phase-level only)
- Retry-on-partial-failure in the UI
