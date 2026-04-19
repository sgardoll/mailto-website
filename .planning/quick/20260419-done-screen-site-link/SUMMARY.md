---
slug: done-screen-site-link
status: complete
completed: 2026-04-19
commit: f70ba6e
---

# Done Screen — Site Link Refactor

Replaced the Start Workflow launcher (added earlier the same day in plan 04-03)
with a hero link to the site URL the wizard already collected.

## What changed

- `setup/server.py` — dropped `_workflow_proc` / `_workflow_log` state and the
  `POST /start-workflow` + `GET /workflow-status` routes. `/step/done` now
  passes `site_base_url` from `_wizard_state` into the template.
- `setup/templates/done.html` — hero "View Your Site" link (target=_blank,
  rel=noopener) + visible URL when `site_base_url` is set. Listener command
  moved to a small secondary help block.
- `setup/static/wizard.js` — removed `initDoneStep()` and its call; no JS on
  the done page now.
- `setup/static/wizard.css` — dropped `.workflow-status` / `.workflow-log`
  styles; added `.site-link-row` and `.site-url` styling.
- `setup/tests/test_phase4_flow.py` — removed 6 launcher tests and the
  `_FakeProc` helper; added 2 tests covering site-link render + omission.
- `.gitignore` — removed `logs/` (no longer auto-created).

## Tests

`.venv/bin/python -m pytest setup/tests/ -q` → **78 passed** (was 83 with
workflow-launcher tests; net -5 by design).

## Browser verification

Wizard restarted at http://127.0.0.1:7331. Complete the flow end-to-end and
confirm the success screen shows the live site URL as the primary action.
