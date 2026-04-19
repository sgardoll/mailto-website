---
slug: done-screen-site-link
created: 2026-04-19
type: quick
---

# Done Screen — Replace Workflow Launcher with Site Link

## Problem

The `/step/done` screen currently shows a `Start Workflow` button that launches
`scripts/run-workflow.sh` as a detached subprocess and tails its log. This was
added mid-plan-04-03 in response to the first user feedback, but on reflection
it's the wrong metaphor:

- `run-workflow.sh` runs a long-lived IMAP listener that auto-publishes incoming
  emails to the deployed site. It is a background concern, not a deploy action.
- The wizard has already collected the site deploy target (`site_base_url`).
  The meaningful handoff is pointing the user at their live site, not showing a
  log tail of a listener running forever.

User feedback: "we write the script to our local project folder and we attempt
to launch it. But that's not really the right thing to do here… We need a sort
of a link now. We've given the wizard all of the deployment instructions. So it
now needs to deploy with the config that we've set up and launch the URL for
the user."

## Solution

Replace the Start Workflow launcher with a hero link to `site_base_url`. Keep
the listener as a small secondary manual note so users who want to run it know
the command exists.

## Changes

### `setup/server.py`
- Remove `_workflow_proc`, `_workflow_log` state
- Remove `POST /start-workflow` and `GET /workflow-status` routes
- Update `/step/done` to pass `site_base_url` from `_wizard_state` into the template

### `setup/templates/done.html`
- Remove `#workflow-launch` and `#workflow-status-panel` sections
- Add hero "View your site" button/link pointing at `{{ site_base_url }}`
  (opens in new tab, rel="noopener")
- Keep `.env` + `workflow/config.yaml` written-files confirmation
- Secondary help text mentions `./scripts/run-workflow.sh` for enabling the
  auto-publish listener

### `setup/static/wizard.js`
- Remove `initDoneStep()` launcher function and the `initDoneStep()` call

### `setup/static/wizard.css`
- Remove `.workflow-status` and `.workflow-log` styles
- Keep `.success-next-action` for the site-link hero block

### `setup/tests/test_phase4_flow.py`
- Remove 6 tests for `/start-workflow` and `/workflow-status`
- Remove `reset_workflow_state` fixture and `_FakeProc` helper
- Update `test_done_route_renders_run_workflow_command` →
  `test_done_route_renders_site_link` asserting `site_base_url` appears in the
  rendered page (with a seeded `_wizard_state['site_base_url']`)

### `.gitignore`
- Keep `logs/` gitignored — harmless even though no longer auto-created

## Verification

- `.venv/bin/python -m pytest setup/tests/ -q` → all passing
- Browser check: complete wizard through Inboxes → Preview → Write → success
  screen shows View Your Site link pointing at the SiteGround/Netlify/Vercel
  URL collected during wizard
