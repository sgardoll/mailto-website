# Phase 3: Hosting Provider & Inbox Manager - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-19
**Phase:** 03-hosting-provider-inbox-manager
**Areas discussed:** Page structure, SSH auth method, Inbox card layout, Config key shape

---

## Page structure

| Option | Description | Selected |
|--------|-------------|----------|
| Separate pages (Recommended) | 5 separate HTML pages, one per step. Hosting = `/step/hosting`, Inboxes = `/step/inboxes`. Cleaner step isolation, easier per-step validation. | ✓ |
| One shared page | Hosting + Inboxes on one page, like Gmail + LM Studio currently share one. Fewer routes. | |

**User's choice:** Separate pages

| Option | Description | Selected |
|--------|-------------|----------|
| POST to /step/hosting redirect | Per-step POST handlers. Clean separation but more Flask routes. | |
| Reuse /validate-form with step in body | Extend existing route; JS sends `{step: 'hosting', ...fields}`. Server returns `{ok, next_step}`. | ✓ |

**User's choice:** Reuse `/validate-form` extended to cover all 5 steps. Step name sent in POST body. Server returns `next_step` URL; JS navigates on success.

---

## SSH auth method

| Option | Description | Selected |
|--------|-------------|----------|
| Show both fields always (Recommended) | SSH key path + password both visible. User fills whichever applies, leaves the other blank. Validation: at least one non-empty. | ✓ |
| Auth method toggle first | Radio/select (Key / Password) reveals only the relevant field. Cleaner UI but more complex JS. | |

**User's choice:** Show both fields always.

---

## Inbox card layout

| Option | Description | Selected |
|--------|-------------|----------|
| Fuller card with labelled fields (Recommended) | Bordered card, all 5 field-groups with labels, cards stack vertically. | |
| Compact multi-column row | 5 inputs in a compact row, wrapping layout. | ✓ |

**User's choice:** Compact multi-column row. Layout within the row deferred to Claude's discretion (two-row wrap recommended).

| Option | Description | Selected |
|--------|-------------|----------|
| Same pattern as allowed-senders (Recommended) | JS clones template row, Remove disabled when one row remains. | ✓ |
| Different | Custom interaction pattern. | |

**User's choice:** Same add/remove pattern as allowed-senders widget.

---

## Config key shape

| Option | Description | Selected |
|--------|-------------|----------|
| Provider-specific keys (Recommended) | `siteground:`, `netlify:`, `vercel:`, `github_pages:`, `ssh_sftp:`. Matches config.example.yaml exactly. | ✓ |
| Generic `hosting:` key | `hosting: {provider: netlify, ...}`. Uniform shape, requires config.example.yaml update. | |

**User's choice:** Provider-specific top-level keys matching config.example.yaml.

---

## Claude's Discretion

- Exact layout within the inbox compact row (two-row wrap vs single row)
- Whether lmstudio gets its own template or shares index.html with a step parameter
- Field tab order within provider groups
- Exact error message for the SSH key/password "at least one required" rule

## Deferred Ideas

None.
