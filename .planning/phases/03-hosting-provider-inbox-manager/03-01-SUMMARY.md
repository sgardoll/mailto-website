---
phase: 03
plan: 01
subsystem: setup/builder
tags: [tdd, validation, yaml, hosting, inboxes]
dependency_graph:
  requires:
    - setup/builder.py (existing validate/build from Phase 2)
    - workflow/config.example.yaml (canonical YAML shape)
  provides:
    - validate_hosting
    - build_hosting
    - validate_inboxes
    - build_inboxes
  affects:
    - setup/server.py (will call these in Plan 03-02 /validate-form dispatch)
tech_stack:
  added: []
  patterns:
    - Flat form_data -> provider-keyed YAML section
    - Per-row error shape {field, index, message} for inbox list validation
key_files:
  created: []
  modified:
    - setup/builder.py
    - setup/tests/test_builder.py
decisions:
  - D-06 hosting field groups honored via sg-/ssh- prefixes
  - D-07 provider-specific top-level YAML keys (siteground, ssh_sftp, netlify, vercel, github_pages)
  - D-08 hosting_provider preserved in returned dict for Phase 4 assembler
metrics:
  duration: ~15 min
  completed: 2026-04-19
  tasks: 3
  tests_added: 25
  tests_total: 40
requirements:
  - HOST-01
  - HOST-02
  - HOST-03
  - HOST-04
  - HOST-05
  - HOST-06
  - INBOX-01
  - INBOX-02
  - INBOX-03
  - INBOX-04
---

# Phase 3 Plan 1: Hosting & Inboxes Builder Logic Summary

**One-liner:** Server-side validation and YAML assembly for 5 hosting providers (siteground/ssh_sftp/netlify/vercel/github_pages) and multi-inbox manager, implemented TDD with 25 new tests.

## What Was Built

Extended `setup/builder.py` with four new pure functions, each with per-concern unit tests in `setup/tests/test_builder.py`:

- **`validate_hosting(form_data)`** — Rejects unknown providers; for SSH providers enforces host/port/username/remote_base_path plus an at-least-one rule for `key_path`/`password`; for Netlify/Vercel enforces token + site/project id; for GitHub Pages enforces target branch. Fields outside the selected provider are not validated.
- **`build_hosting(form_data)`** — Returns `{hosting_provider, <provider_key>: {...}}` with field names matching `workflow/config.example.yaml` exactly (`user`, `key_path`, `base_remote_path` for SSH; `api_token`/`site_id` for Netlify; `api_token`/`project_id` for Vercel; `branch` for GitHub Pages). Port coerced to int; `gh-pages` default branch applied.
- **`validate_inboxes(form_data)`** — Rejects empty/missing list; per-row validates slug (regex `/^[a-z0-9-]+$/`), email (contains `@`), site_name (non-empty), site_url (`http(s)://` prefix), base_path (leading `/`); flags duplicate slugs across rows with errors on all duplicate positions.
- **`build_inboxes(form_data)`** — Maps input `email` → `address` and `base_path` → `site_base` per canonical YAML, adds empty `allowed_senders: []`, preserves input order.

## Commits

| Hash | Message |
|------|---------|
| b845671 | test(03-01): add failing tests for validate_hosting and build_hosting |
| f8362ac | test(03-01): add failing tests for validate_inboxes and build_inboxes |
| da5ecf8 | feat(03-01): implement validate_hosting, build_hosting, validate_inboxes, build_inboxes |

## Test Results

```
40 passed in 0.10s
```

All 15 pre-existing Phase 2 tests still green. 25 new tests added for Phase 3 hosting + inbox coverage.

## TDD Gate Compliance

- RED gate: two `test(...)` commits (b845671, f8362ac) confirmed failing with `ImportError` before implementation.
- GREEN gate: `feat(...)` commit (da5ecf8) makes all tests pass.
- REFACTOR gate: not needed — implementation is already minimal.

## Deviations from Plan

None — plan executed exactly as written. One minor defensive addition not contradicting the spec: `validate_inboxes` skips the uniqueness check for rows whose slug is empty (empty slugs are already caught by the "Slug is required" error, so reporting them as duplicates too would be noise). This preserves the duplicate-reporting contract for non-empty slugs.

## Threat Model Compliance

| Threat | Mitigation | Status |
|--------|------------|--------|
| T-03-01 Port tampering | `int()` cast + `1..65535` bounds check in `validate_hosting` | Implemented |
| T-03-02 Slug path traversal | `_SLUG_RE = re.compile(r'^[a-z0-9-]+$')` enforced | Implemented |
| T-03-03 SSH password disclosure | Accepted (localhost only) | No code change |
| T-03-04 Inbox list injection | `inbox.get(..., '')` defaults trigger field errors for missing keys | Implemented |

## Threat Flags

None — no new network surface, auth paths, file access, or schema changes at trust boundaries introduced by this plan.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: setup/builder.py (lines 72, 123, 160, 212 define the four new functions)
- FOUND: setup/tests/test_builder.py (25 new tests added)
- FOUND: commit b845671
- FOUND: commit f8362ac
- FOUND: commit da5ecf8
- All 40 tests pass under `uv run python -m pytest setup/tests/test_builder.py`
