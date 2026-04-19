---
phase: 04-preview-write-completion
plan: 03
status: complete
completed: 2026-04-19
commits:
  - 78004c1 feat(04-03): add Phase 4 preview/write wiring to wizard.js
  - d7b4bdc feat(04-03): add Phase 4 preview/overwrite/success styles to wizard.css
  - 1daab33 feat(04-03): launch workflow in-wizard via Start Workflow button
---

# Plan 04-03 — Frontend Wiring & Workflow Launcher

## What was built

The Phase 4 frontend is now live end-to-end and the success screen launches the workflow in-wizard instead of handing the user a manual command.

### `setup/static/wizard.js`
- `initPreviewStep()` detects the preview page via `#write-btn` and wires:
  - overwrite checkbox → gates `#write-btn` disabled state when `has_existing_config`
  - POST `/write-config` with `{ confirmed: true, overwrite_confirmed: ... }`
  - success → `window.location.href = '/step/done'`
  - server errors surfaced in `#write-error` without failing silently
- `initDoneStep()` detects the success page via `#start-workflow-btn` and wires:
  - POST `/start-workflow` on click
  - swaps launch panel → status panel with live log tail
  - polls `/workflow-status` every 2s while `status == 'running'`; backs off to 5s on network error

### `setup/static/wizard.css`
- `.config-preview` monospace read-only block used for `.env` and YAML previews
- `.overwrite-warning` amber banner + `#write-btn:disabled` unavailable state
- `.success-next-action` green-bordered block for primary next-action emphasis
- `.workflow-status` panel + `.workflow-log` dark-background live tail (max-height 280 px, auto-scroll)

### `setup/templates/done.html`
- Replaced the manual `./scripts/run-workflow.sh` instruction with a `Start Workflow` button
- Added hidden `#workflow-status-panel` that reveals on click with a live log tail
- Manual fallback reference kept as secondary help text

### `setup/server.py`
- `POST /start-workflow` spawns `scripts/run-workflow.sh` as a detached subprocess (`start_new_session=True`) so the IMAP listener survives wizard exit; stdout/stderr piped to `logs/workflow.log`; returns existing pid without respawn if already running
- `GET /workflow-status` returns `{ status, exit_code, pid, log[-50:] }` — `running` | `exited` | `failed` | `not_started`
- Missing script, mkdir failures, open failures, and Popen failures all return 500 with a readable error payload

### `setup/tests/test_phase4_flow.py`
- Updated `test_done_route_renders_run_workflow_command` to check the Start Workflow button
- Added 6 tests:
  - `test_start_workflow_spawns_subprocess` (validates `start_new_session=True` + `cwd`)
  - `test_start_workflow_returns_existing_if_already_running`
  - `test_start_workflow_missing_script_returns_error`
  - `test_workflow_status_not_started`
  - `test_workflow_status_running_returns_log_tail` (60-line fixture → last 50 returned)
  - `test_workflow_status_reports_failure_exit_code`

## Scope expansion

Plan 04-03 originally specified a success screen that told the user to run `./scripts/run-workflow.sh` manually. During human verification the user flagged this as poor UX: "the site should run this once the user has confirmed and that script should then load their stuff". The scope was extended in the same plan to add the subprocess launcher + status polling rather than deferring to a follow-up plan.

The original must_have — "success screen visibly emphasizes ./scripts/run-workflow.sh as the next action" — still holds: the manual command reference remains in secondary help text as a fallback.

## Test results

`.venv/bin/python -m pytest setup/tests/test_phase4_flow.py -q` → **21 passed**
Full setup suite → **83 passed** (77 prior + 6 new workflow-launcher tests)

## Human verification

Verified end-to-end at `http://127.0.0.1:7331`:
- Wizard completes Gmail → LM Studio → Hosting → Inboxes → Preview without regression
- Preview page shows masked read-only `.env` + YAML blocks
- Overwrite gate disables `Write Config Files` until checkbox is ticked when existing config is present
- Successful write lands on success screen
- **Start Workflow button** spawns the listener in-wizard with a live log tail (approved 2026-04-19)

## Key files

### Created
- `logs/workflow.log` (runtime-only, gitignored)

### Modified
- `setup/server.py` — `/start-workflow`, `/workflow-status`, workflow subprocess state
- `setup/templates/done.html` — Start Workflow button + status panel
- `setup/static/wizard.js` — `initPreviewStep()` + `initDoneStep()`
- `setup/static/wizard.css` — preview/overwrite/success/workflow-log styles
- `setup/tests/test_phase4_flow.py` — 6 new tests
- `.gitignore` — `logs/`
