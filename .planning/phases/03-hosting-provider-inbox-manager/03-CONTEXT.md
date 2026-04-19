# Phase 3: Hosting Provider & Inbox Manager - Context

**Gathered:** 2026-04-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 3 adds two new wizard steps to the existing multi-page form:

1. **Hosting step** (`/step/hosting`) — a provider dropdown (5 options) plus conditional credential field groups; only the selected provider's fields are visible at any time.
2. **Inboxes step** (`/step/inboxes`) — a multi-inbox row manager where users define one or more named inboxes; slug uniqueness is validated on blur across all rows.

Phase 3 also extends the existing `/validate-form` route and `builder.py` to handle these two steps. It does NOT write files to disk (Phase 4) or produce a preview (Phase 4).

</domain>

<decisions>
## Implementation Decisions

### Page routing
- **D-01:** Each wizard step has its own Jinja2 template. The 5 pages are: gmail (existing `index.html`), lmstudio (new), hosting (new), inboxes (new), preview (Phase 4). Each Flask `GET` route renders the relevant template with `active_step='{slug}'`.
- **D-02:** Step-to-step navigation uses the **existing `/validate-form` POST route**, extended to cover all 5 steps. The JS sends `{step: 'hosting', ...field_values}` in the JSON body. The server validates only that step's fields, merges into `_wizard_state`, and returns `{ok: true, next_step: '/step/inboxes'}` or `{ok: false, errors: {...}}`. No new per-step POST routes.
- **D-03:** On success, the JS does `window.location.href = data.next_step` to advance the wizard. This keeps navigation server-driven (the server tells the client where to go next).

### Hosting provider fields
- **D-04:** Provider selection uses a `<select>` dropdown (not radio buttons). On `change`, JS shows the field group for the selected provider and hides all others. Uses the same show/hide CSS pattern already established in wizard.js.
- **D-05:** SSH-based providers (SiteGround, Generic SSH/SFTP) show **both** `key_path` and `password` fields always — no toggle. Validation rule: at least one of the two must be non-empty. The other may be blank.
- **D-06:** Field groups per provider:
  - **SiteGround**: host, port (default 18765), username, SSH key path, password, remote base path
  - **Generic SSH/SFTP**: host, port (default 22), username, SSH key path, password, remote base path
  - **Netlify**: API token, site ID
  - **Vercel**: API token, project name/ID
  - **GitHub Pages**: target branch (default: `gh-pages`)

### Config YAML key shape
- **D-07:** Phase 3's builder emits **provider-specific top-level keys** matching config.example.yaml:
  - `siteground:` for SiteGround
  - `ssh_sftp:` for Generic SSH/SFTP
  - `netlify:` for Netlify
  - `vercel:` for Vercel
  - `github_pages:` for GitHub Pages
- **D-08:** The selected provider name is stored in `_wizard_state` as `hosting_provider` so Phase 4's assembler knows which section key to include.

### Inbox card layout
- **D-09:** Each inbox is a **compact multi-column row** (not a full bordered card). Row layout within the 640px constraint is Claude's discretion — the two-row split pattern (row 1: slug + address; row 2: site name + site URL + base path) is recommended to match the existing temperature+max_tokens split-row precedent.
- **D-10:** The inbox widget mirrors the **allowed-senders pattern**: an `Add inbox` button appends a new row (JS clones a `<template>` element). Each row has a `Remove` button disabled when only one row exists.
- **D-11:** Slug uniqueness is validated on `blur` across all inbox rows. JS collects all slug values, finds duplicates, and sets an inline error on the offending field. Server-side validation in `/validate-form` also enforces this before accepting the step.

### Builder scope
- **D-12:** Phase 3 extends **`setup/builder.py`** with new functions: `validate_hosting(data)`, `build_hosting(data)`, `validate_inboxes(data)`, `build_inboxes(data)`. No separate module files — keeps the builder in one place consistent with Phase 2's approach.

### Claude's Discretion
- Exact layout within the inbox compact row (two-row wrap vs single row with overflow — go with what fits cleanest at 640px)
- Whether `lmstudio` gets its own template or shares `index.html` with a step parameter (either approach is fine; separate template is cleaner)
- Field tab order within provider groups
- Exact error messages for "at least one of key_path/password required"

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — HOST-01–HOST-06 and INBOX-01–INBOX-04 (the full acceptance criteria for this phase)

### Config structure
- `workflow/config.example.yaml` — Canonical YAML shape. Phase 3 builder must produce sections whose keys and field names match exactly: `siteground:`, `netlify:`, `vercel:`, `github_pages:` (key for Generic SSH/SFTP: `ssh_sftp:`), and `inboxes:` array.

### Prior phase UI contract
- `.planning/phases/02-core-form-config-engine/02-UI-SPEC.md` — Design tokens (spacing scale, typography, colour palette), field-group HTML pattern, validation behaviour, and file targets. Phase 3 pages MUST follow the same tokens and patterns — do not re-derive.

### Prior phase decisions
- `.planning/phases/02-core-form-config-engine/02-CONTEXT.md` — Established decisions: `_wizard_state` flat dict, builder partial-YAML pattern, stack constraints (no build step, no framework), route registration conventions.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `setup/static/wizard.js` — allowed-senders widget (add row / remove row / disable-last-remove pattern) — inbox manager reuses this exact approach
- `setup/static/wizard.css` — split-row layout (`.field-row-split`), show/hide toggle visibility pattern, field-group structure — reuse for provider conditional groups and inbox rows
- `setup/server.py` — `_wizard_state` dict, `/validate-form` route, `render_template()` pattern — extend in place
- `setup/builder.py` — `validate()` and `build()` functions — extend with hosting and inbox variants

### Established Patterns
- Blur validation: JS sets `data-touched` on blur, then validates; errors shown in `<span class="error">` sibling
- Show/hide: CSS class toggle (or `hidden` attribute) on provider field groups — triggered by the provider `<select>` `change` event
- Split row: `.field-row-split` CSS class wraps two `.field-group` divs side by side (used for temperature + max_tokens)
- Flat state: `_wizard_state.update(data)` merges the step's fields into the module-level dict

### Integration Points
- `setup/server.py` `/validate-form` route — add `step` dispatch: read `data['step']`, route to the appropriate `validate_*()` function, merge into `_wizard_state`, return `{ok, next_step, errors}`
- `setup/templates/` — add `hosting.html` and `inboxes.html` Jinja2 templates; add GET routes for `/step/hosting` and `/step/inboxes`
- `setup/builder.py` — add `validate_hosting()`, `build_hosting()`, `validate_inboxes()`, `build_inboxes()` functions

</code_context>

<specifics>
## Specific Ideas

- The progress indicator already has all 5 step labels defined in index.html (gmail, lmstudio, hosting, inboxes, preview) — new templates can reuse the same `{% set steps = [...] %}` block.
- config.example.yaml shows SiteGround port default as 18765 — use this as the pre-filled default for the SiteGround host port field.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-hosting-provider-inbox-manager*
*Context gathered: 2026-04-19*
