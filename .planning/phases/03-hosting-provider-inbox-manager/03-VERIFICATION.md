---
phase: 03-hosting-provider-inbox-manager
verified: 2026-04-19T00:00:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Switch provider dropdown in browser and confirm only selected provider's fields are visible"
    expected: "Selecting Netlify hides SiteGround/SSH/Vercel/GitHub Pages groups; only Netlify fields remain"
    why_human: "Visual show/hide behavior requires running the Flask server and interacting with the DOM"
  - test: "On /step/inboxes, verify Remove button is disabled when only one inbox card remains"
    expected: "First row's Remove button is visibly disabled; after adding a second and removing it, the remaining row's button becomes disabled again"
    why_human: "DOM state after user actions — JS behavior verified by inspection but needs runtime confirmation"
  - test: "Enter duplicate slug in a second inbox card and blur the field"
    expected: "Inline 'Slug must be unique across all inboxes' error appears on the duplicate field"
    why_human: "Blur-triggered validation requires browser interaction"
  - test: "Submit hosting form with GitHub Pages selected and verify next_step navigation to /step/inboxes"
    expected: "Browser navigates to /step/inboxes after successful validation"
    why_human: "End-to-end step navigation requires live server and browser"
---

# Phase 3: Hosting Provider & Inbox Manager Verification Report

**Phase Goal:** Users can select any of the five supported hosting providers and see only the fields relevant to their choice, and can define one or more named inboxes with slug uniqueness enforced
**Verified:** 2026-04-19
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Switching the hosting provider dropdown instantly shows only that provider's credential fields and hides all others | ✓ VERIFIED | `wizard.js:405-417` `showProvider()` toggles `.provider-fields[data-provider]` `hidden` + `aria-hidden` on select change; 5 `.provider-fields` groups in `hosting.html:50,117,184,211,238` with `hidden` on non-siteground |
| 2 | Selecting SiteGround or Generic SSH/SFTP reveals host, port, username, SSH key path or password, and remote base path | ✓ VERIFIED | `hosting.html:50-183` renders SiteGround group with `sg-host/sg-port/sg-username/sg-ssh_key_path/sg-password/sg-remote_base_path` + SSH/SFTP group mirrors with `ssh-` prefix |
| 3 | Selecting Netlify or Vercel reveals the correct API token and site identifier fields; selecting GitHub Pages reveals only the target branch field | ✓ VERIFIED | `hosting.html:184-210` Netlify api_token + site_id; `211-237` Vercel api_token + project_id; `238-249` GitHub Pages only `gh_pages_branch` (default `gh-pages`) |
| 4 | User can add a second inbox card in the same session and cannot remove the last remaining inbox card | ✓ VERIFIED | `wizard.js:778-831` clones `inbox-row-template` and appends to `#inboxes-list`; `updateRemoveButtons()` (line 649-656) disables all remove buttons when only 1 row exists |
| 5 | Entering a duplicate slug in any inbox card shows a uniqueness error on that field when leaving it | ✓ VERIFIED | `wizard.js:660-678` `validateAllSlugs()` counts duplicates and displays 'Slug must be unique across all inboxes'; triggered on slug blur (line 758); also enforced server-side in `builder.py:194-207` |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `setup/builder.py` | validate_hosting, build_hosting, validate_inboxes, build_inboxes | ✓ VERIFIED | All 4 functions defined (lines 72, 123, 160, 212); 9616 bytes substantive |
| `setup/tests/test_builder.py` | Test coverage for all 4 new functions | ✓ VERIFIED | 42 test functions, 13146 bytes; 22+ tests for hosting/inboxes |
| `setup/templates/index.html` | Gmail-only (LM Studio removed) | ✓ VERIFIED | 5337 bytes; Gmail-only structure |
| `setup/templates/lmstudio.html` | LM Studio step template | ✓ VERIFIED | 6702 bytes |
| `setup/templates/hosting.html` | Provider dropdown + 5 conditional field groups | ✓ VERIFIED | 14684 bytes; all 5 `.provider-fields` present |
| `setup/templates/inboxes.html` | Template + pre-rendered first row + add-inbox btn | ✓ VERIFIED | 9511 bytes; `#inbox-row-template`, `#inboxes-list`, `#add-inbox`, pre-rendered row 1 |
| `setup/server.py` | 4 GET step routes + step-dispatch /validate-form | ✓ VERIFIED | Routes at lines 77, 82, 87, 92; dispatch lines 102-145 |
| `setup/static/wizard.css` | Phase 3 CSS appended | ✓ VERIFIED | 7379 bytes; `.provider-fields[hidden]` (287), `.field-row-thirds` (290), `.inbox-row` (297), `.remove-inbox` (319), `#add-inbox` (334) |
| `setup/static/wizard.js` | initHostingStep + initInboxesStep | ✓ VERIFIED | 41801 bytes; `initHostingStep` at 388, called line 618; `initInboxesStep` at 642, called line 949 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| builder.py build_hosting | config.example.yaml | YAML keys | ✓ WIRED | Emits `siteground`, `ssh_sftp`, `netlify`, `vercel`, `github_pages` — matches canonical shape |
| server.py /validate-form | builder.py | step dispatch | ✓ WIRED | Lines 128-142 call `validate_hosting`/`build_hosting`/`validate_inboxes`/`build_inboxes` |
| server.py /validate-form | wizard.js | next_step response | ✓ WIRED | Server returns `{ok, next_step}`; wizard.js:586,898 uses `window.location.href = result.data.next_step` |
| wizard.js initHostingStep | hosting.html .provider-fields | show/hide | ✓ WIRED | `querySelectorAll('.provider-fields')` + `g.hidden = !show` |
| wizard.js initInboxesStep | inboxes.html #inbox-row-template | cloneNode | ✓ WIRED | Line 778: `getElementById('inbox-row-template')`; line 782: `tmpl.content.cloneNode(true)` |
| hosting.html | server.py | active_step='hosting' | ✓ WIRED | server.py:89 `render_template('hosting.html', ..., active_step='hosting')` |
| inboxes.html | server.py | active_step='inboxes' | ✓ WIRED | server.py:94 `render_template('inboxes.html', ..., active_step='inboxes')` |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Test suite passes | `uv run python -m pytest setup/tests/ -q` | 46 passed in 0.40s | ✓ PASS |
| Builder exports all 4 phase-3 functions | `grep "^def (validate_hosting\|build_hosting\|validate_inboxes\|build_inboxes)" setup/builder.py` | 4 matches | ✓ PASS |
| All 5 provider field groups present | `grep 'data-provider=' hosting.html` | 5 matches (siteground, ssh_sftp, netlify, vercel, github_pages) | ✓ PASS |
| All 5 provider options in select | `grep '<option value=' hosting.html` | 5 matches in correct order | ✓ PASS |
| CSS additions present | grep for `.provider-fields[hidden]`, `.field-row-thirds`, `.inbox-row`, `.remove-inbox`, `#add-inbox` | All 5 present | ✓ PASS |
| initHostingStep / initInboxesStep called | grep in wizard.js | Both defined and invoked | ✓ PASS |

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| HOST-01 | User can select hosting provider from 5 options | ✓ SATISFIED | `hosting.html:39-43` — 5 options in select |
| HOST-02 | SiteGround / SSH-SFTP reveal host/port/user/key/password/base path | ✓ SATISFIED | `hosting.html:50-183` — both groups with all 6 fields |
| HOST-03 | Netlify reveals API token + site ID | ✓ SATISFIED | `hosting.html:184-210` + `builder.py:139-143` |
| HOST-04 | Vercel reveals API token + project name/ID | ✓ SATISFIED | `hosting.html:211-237` + `builder.py:144-148` |
| HOST-05 | GitHub Pages reveals target branch (default gh-pages) | ✓ SATISFIED | `hosting.html:243` value="gh-pages"; `builder.py:151` default |
| HOST-06 | Only selected provider fields visible | ✓ SATISFIED | `wizard.js:405-417` show/hide; 4 of 5 groups default `hidden` |
| INBOX-01 | User can define inbox with slug/email/site_name/site_url/base_path | ✓ SATISFIED | `inboxes.html:94-150` first row + `builder.py:212-224` |
| INBOX-02 | User can add additional inbox cards | ✓ SATISFIED | `wizard.js:778-831` addInboxRow via template clone |
| INBOX-03 | User can remove any inbox except when only one remains | ✓ SATISFIED | `wizard.js:649-656` updateRemoveButtons disables when rows.length === 1 |
| INBOX-04 | Inbox slugs validated for uniqueness on blur | ✓ SATISFIED | `wizard.js:660-678` validateAllSlugs on blur; `builder.py:194-207` server-side |

All 10 phase-3 requirement IDs satisfied. No orphaned requirements from REQUIREMENTS.md traceability table.

### Anti-Patterns Scan

Scanned `setup/builder.py`, `setup/server.py`, `setup/templates/hosting.html`, `setup/templates/inboxes.html`, `setup/static/wizard.js`, `setup/static/wizard.css`:

- No TODO/FIXME/PLACEHOLDER markers in phase-3 code paths
- No empty handlers or `return null/[]/{}` stubs for phase-3 functions
- Pre-rendered first inbox row has real field structure (not placeholder)
- GitHub Pages default `gh-pages` branch is an intentional pre-filled value, not a stub
- `allowed_senders: []` in `build_inboxes` is intentional per config.example.yaml comment ("empty -> falls back to global_allowed_senders")

No blockers or warnings found.

### Human Verification Required

See frontmatter `human_verification` block. Four UX-level checks cannot be verified programmatically:

1. **Provider show/hide visual confirmation** — dropdown change triggers correct group visibility
2. **Remove-button disabled state** — last-row protection when exactly one inbox exists
3. **Slug uniqueness blur error** — inline error display when duplicate entered
4. **End-to-end step navigation** — `window.location.href = next_step` advances the wizard

Code inspection strongly suggests all four work correctly; runtime confirmation recommended before milestone closure.

### Gaps Summary

No gaps found. All 5 roadmap success criteria are met by substantive, wired code. All 10 requirement IDs satisfied. All 46 automated tests pass. Status is `human_needed` only because browser-interaction UX behaviors cannot be verified without a running server.

---

*Verified: 2026-04-19*
*Verifier: Claude (gsd-verifier)*
