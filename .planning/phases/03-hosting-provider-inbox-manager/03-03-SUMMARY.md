---
phase: 03
plan: 03
subsystem: setup-wizard
tags: [hosting, template, html, jinja2]
requires:
  - setup/templates/index.html (header/nav/footer pattern)
  - setup/static/wizard.css (field-group, toggle-visibility, error styles)
provides:
  - setup/templates/hosting.html (hosting wizard step template)
affects:
  - setup/server.py (will GET /step/hosting render this template in a later plan)
  - setup/static/wizard.js (JS targets #hosting-provider and .provider-fields[data-provider])
tech_stack:
  added: []
  patterns:
    - Conditional field groups via `hidden` attribute + `data-provider` selector
    - Reused show/hide toggle pattern for password inputs
key_files:
  created:
    - setup/templates/hosting.html
  modified: []
decisions:
  - Followed D-04/D-05/D-06: <select> with conditional .provider-fields groups; SSH group shows both key_path and password always
  - Name attributes mix hyphens and underscores per plan spec to match builder.py validate_hosting() keys
metrics:
  duration: ~10m
  completed: 2026-04-19
tasks_completed: 1
tasks_total: 1
files_created: 1
files_modified: 0
---

# Phase 03 Plan 03: Hosting Template Summary

One-liner: Created `setup/templates/hosting.html` — hosting wizard step with a provider `<select>` and five conditional `.provider-fields` groups (SiteGround visible by default; Generic SSH/SFTP, Netlify, Vercel, GitHub Pages hidden).

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create hosting.html with provider dropdown and all 5 field groups | 029243d | setup/templates/hosting.html |

## What Was Built

- **Provider dropdown** (`id="hosting-provider"`, `name="hosting_provider"`) with 5 options in spec order: siteground (selected), ssh_sftp, netlify, vercel, github_pages.
- **SiteGround group** (`data-provider="siteground"`, no `hidden`): sg-host, sg-port (value=18765), sg-username, sg-ssh_key_path, sg-password (with Show/Hide toggle), sg-remote_base_path.
- **Generic SSH/SFTP group** (`data-provider="ssh_sftp"`, hidden): ssh-host, ssh-port (value=22), ssh-username, ssh-ssh_key_path, ssh-password (with toggle), ssh-remote_base_path.
- **Netlify group** (hidden): netlify-api-token (with toggle, `name="netlify_api_token"`), netlify-site-id (`name="netlify_site_id"`).
- **Vercel group** (hidden): vercel-api-token (with toggle, `name="vercel_api_token"`), vercel-project-id (`name="vercel_project_id"`).
- **GitHub Pages group** (hidden): gh-pages-branch (value="gh-pages", `name="gh_pages_branch"`).
- **Name-attribute convention** per plan: sg-* and ssh-* field names keep hyphens to match `builder.py validate_hosting()` keys; netlify/vercel/github_pages fields use underscores in the `name` attribute matching the builder parameter names.
- **Accessibility**: every field has a `<label for>`, `aria-describedby` pointing at the help + error spans, `aria-live="polite"` on error spans, `aria-hidden="true"` on hidden provider groups, `aria-pressed="false"` on toggle buttons.
- **Header/nav/footer**: copied verbatim from `index.html`, including the shared `steps` block so the progress indicator highlights `active_step='hosting'`.

## Verification

```
provider-fields:    5   (expected 5)
data-provider=:     5   (expected 5)
hidden occurrences: 30  (4 on provider groups + error spans + form-error-summary; expected >= 4)
toggle-visibility:  4   (sg-password, ssh-password, netlify-api-token, vercel-api-token; expected >= 4)
sg-* fields:        6   (host, port, username, ssh_key_path, password, remote_base_path)
netlify fields:     2   (api-token, site-id)
gh-pages-branch:    present
```

SiteGround group line confirmed free of `hidden` attribute:
```
<div class="provider-fields" data-provider="siteground">
```

All done criteria met.

## Deviations from Plan

None — plan executed exactly as written.

## Threat Model Coverage

- **T-03-03-01 (Information Disclosure on credential inputs)** → mitigated. All credential inputs use `type="password"` with the existing Show/Hide toggle pattern (sg-password, ssh-password, netlify-api-token, vercel-api-token). Non-credential fields use `type="text"`.

No new surface introduced beyond the threat model.

## Known Stubs

None — template is fully wired for the upcoming JS (Plan G) and server route integration.

## Follow-ups (for later plans in Phase 03)

- `setup/static/wizard.js` must handle `change` on `#hosting-provider` to toggle `.provider-fields[data-provider]` `hidden` / `aria-hidden` (Plan G).
- `setup/server.py` must register `GET /step/hosting` to render this template with `active_step='hosting'`.
- `setup/static/wizard.css` needs `select` styling and `.provider-fields[hidden] { display: none; }` rule per UI-SPEC CSS additions section (separate plan).

## Self-Check: PASSED

- FOUND: setup/templates/hosting.html
- FOUND commit: 029243d (feat(03-03): add hosting.html wizard step with 5 provider field groups)
