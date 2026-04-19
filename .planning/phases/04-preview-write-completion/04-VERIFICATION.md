---
status: passed
phase: 04-preview-write-completion
score: 5/5 must-haves verified
verified: 2026-04-20
method: UAT (see 04-UAT.md) + automated tests (test_phase4_flow.py)
---

# Phase 04 — Preview, Write & Completion: Verification

## Definition of Done (from ROADMAP.md)

> Users see exactly what will be written before committing, the write is atomic,
> existing configs are detected and protected behind an explicit overwrite
> checkbox, and a success screen tells the user what to run next.

All criteria satisfied. The shipped scope exceeded the ROADMAP definition: the
success screen also deploys the site directly to SiteGround and surfaces the
live URL (added via two in-phase scope expansions, both user-approved).

## Must-Haves — Per-Plan Check

### Plan 04-01 (Builder contract)

- [x] `setup/builder.py` owns final `.env` + `workflow/config.yaml` assembly
- [x] `mask_for_preview()` masks secrets to last 4 chars (incl. SiteGround `key_passphrase`)
- [x] `hydrate_wizard_state()` reads existing files without leaking secrets back into the UI
- [x] Hidden runtime keys (`git_branch`, `git_push`, `dry_run`) survive hydrate → preview → rewrite
- [x] 56 tests in `test_builder.py` passing

### Plan 04-02 (Backend flow)

- [x] `GET /step/preview` renders masked `.env` + YAML using the builder contract
- [x] `POST /write-config` requires `confirmed: true`
- [x] Overwrite gate: 409 when files exist without `overwrite_confirmed`
- [x] `_write_config_pair` uses mkstemp + fsync + os.replace; rolls back first file if second fails
- [x] `GET /step/done` renders the success screen
- [x] 15+ tests in `test_phase4_flow.py` passing

### Plan 04-03 (Frontend wiring + workflow launcher)

- [x] `wizard.js initPreviewStep()` wires overwrite checkbox + `POST /write-config` + navigate to /step/done
- [x] `wizard.css` styles preview, overwrite warning, success next-action, deploy panel
- [x] Human verification passed (2026-04-19)

## In-Phase Scope Expansions (Both User-Approved)

### A. In-wizard deploy (quick/20260419-wizard-deploy-siteground — commit 07f20c7)

On the success screen, SiteGround users now click **Deploy Site** and watch
per-inbox rows tick through bootstrap → install → build → deploy → done. The
other 4 providers show a targeted manual-setup guidance block. Reuses
`workflow/site_bootstrap.ensure_site`, `workflow/build_and_deploy.build`, and
`workflow/build_and_deploy.deploy` as-is. New files: `workflow/deploy_once.py`.
Phase 5 will implement Netlify / Vercel / GitHub Pages / Generic SSH deploy.

### B. Pasteable SSH key + passphrase (commits ae204f4, 6e3e4d2, 52712da, edb2cea)

SiteGround hands you the private key as plain text. Instead of asking for a
filesystem path, the wizard now accepts a pasteable textarea, writes the key
to `workflow/state/siteground.key` at 0600 on the Hosting step submit, and
includes an optional "Key passphrase" field plumbed through to paramiko. Also
added actionable error messages for common SSH failures
(`PasswordRequiredException` → "Re-run and fill the passphrase field"; mkdir
Failure → "path is outside your home; use /home/<user>/www/<domain>/...").

## Test Coverage

- **test_builder.py** — 58 tests covering validation, building, hydration,
  masking, existing_key_path preservation, malformed key rejection
- **test_phase4_flow.py** — 21 tests covering prefill, preview rendering,
  overwrite gate, atomic write + rollback, deploy endpoint provider gating,
  deploy worker spawn + progress state transitions, done-route rendering per
  provider, hosting-submit key persistence to disk

Total: 92 tests passing (`.venv/bin/python -m pytest setup/tests/`)

## UAT

All 6 user-observable tests passed — see `04-UAT.md`. End-to-end wizard flow
verified against a real SiteGround account on 2026-04-20:
complete wizard → paste key + passphrase → preview → write → deploy →
live site at https://platform.connectio.com.au/.

## Requirements Traceability

| Requirement | Verified by |
|-------------|-------------|
| OUT-01 (preview with masked secrets) | Plan 04-01 + test_preview_route_renders_masked_content + UAT test 1 |
| OUT-02 (explicit Write Config Files) | Plan 04-02 + test_write_config_requires_confirmation + UAT test 4 |
| OUT-03 (atomic write, no partial files) | Plan 04-02 + test_pair_write_rollback_restores_env_on_second_replace_failure + UAT test 4 |
| OUT-04 (prefill from existing files) | Plan 04-01 + test_prefill_populates_wizard_state_from_existing_files + UAT test 2 |
| OUT-05 (overwrite checkbox gate) | Plan 04-02 + Plan 04-03 + test_write_config_requires_overwrite_confirmation_when_files_exist + UAT test 3 |
| OUT-06 (success screen, next-step command) | Plan 04-02 + Plan 04-03 + test_done_route_siteground_shows_deploy_button + UAT test 5 |

## Acknowledged Deferrals

- Non-SiteGround deploy implementations (Phase 5)
- Provider dataclasses in `workflow/config.py` (Phase 5)
- Streaming npm/SFTP output in deploy panel (currently phase-level progress)
