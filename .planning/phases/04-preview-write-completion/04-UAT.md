---
status: complete
phase: 04-preview-write-completion
source:
  - 04-01-SUMMARY.md
  - 04-02-SUMMARY.md
  - 04-03-SUMMARY.md
  - quick/20260419-wizard-deploy-siteground
  - quick/20260419-done-screen-site-link
started: 2026-04-20T00:30:00Z
updated: 2026-04-20T00:35:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Preview shows masked .env and config.yaml
expected: |
  On /step/preview, both the .env block and the workflow/config.yaml block
  render as read-only monospace panels. Sensitive values (GMAIL_APP_PASSWORD,
  SiteGround password + key_passphrase, any API tokens) show only the last 4
  characters preceded by asterisks, e.g. ********mnop.
result: pass

### 2. Existing config prefills the wizard on re-run
expected: |
  After writing config once, reload the wizard at http://127.0.0.1:7331.
  All steps (Gmail, LM Studio, Hosting, Inboxes) should have their fields
  already populated from the existing .env and workflow/config.yaml.
  The SSH private-key textarea stays empty (by design — secret not re-displayed)
  but the wizard still recognizes an existing key is configured.
result: pass

### 3. Overwrite gate disables Write Config Files
expected: |
  When existing .env or workflow/config.yaml are present, the preview page
  shows an amber "Overwrite existing config" warning and the Write Config
  Files button is visibly disabled. Checking the overwrite checkbox enables
  the button. Unchecking re-disables it.
result: pass

### 4. Write Config Files is atomic
expected: |
  Clicking Write Config Files writes both .env and workflow/config.yaml in
  one go. Neither file should ever be zero bytes or partially written,
  even under interruption. You land on /step/done after success.
result: pass

### 5. Success screen shows Deploy Site + View Your Site
expected: |
  On /step/done with SiteGround configured, the screen shows a Deploy Site
  button (primary action) and the site URL. A secondary help text mentions
  ./scripts/run-workflow.sh for starting the email listener later.
  Non-SiteGround providers show a "not yet implemented" manual-setup block
  instead of the Deploy button.
result: pass

### 6. Deploy Site completes end-to-end (SiteGround)
expected: |
  Clicking Deploy Site swaps to a progress panel with per-inbox rows.
  Each row ticks through phases: pending → bootstrap → install → build →
  deploy → done. On success the row shows a green border and a clickable
  live URL. The deployed site loads in the browser.
result: pass

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
