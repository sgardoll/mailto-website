# Requirements — thoughts-to-platform-builder Onboarding Wizard

## v1 Requirements

### Server & Launch (SRV)

- [x] **SRV-01**: User can run `./scripts/setup.sh` and the wizard launches in their default browser automatically
- [x] **SRV-02**: Wizard probes for a free port (avoiding 5000/8080), falls back to a random available port if preferred port is taken
- [x] **SRV-03**: User can click an "Exit Setup" button to shut down the wizard cleanly; process also cleans up on Ctrl-C via `atexit` handler
- [x] **SRV-04**: Wizard checks write permissions on the project directory before rendering the form and surfaces a clear error if it cannot write

### Form UX (UX)

- [x] **UX-01**: User sees a progress indicator showing all steps by name and which step is active
- [x] **UX-02**: Validation errors appear on individual fields when the user leaves them (on blur), not only on submission
- [x] **UX-03**: User can toggle visibility of any password or token field with a show/hide control; field remains paste-friendly
- [x] **UX-04**: Each credential field has help text and a link to the relevant external documentation (Gmail app password page, LM Studio docs, provider-specific docs)

### Gmail Configuration (GMAIL)

- [x] **GMAIL-01**: User can enter their Gmail address once and it is applied to both imap.user, smtp.user, and smtp.from_address in the generated config
- [x] **GMAIL-02**: User can enter their Gmail app password; it is stored in `.env` as `GMAIL_APP_PASSWORD` and referenced as `${GMAIL_APP_PASSWORD}` in `config.yaml`
- [x] **GMAIL-03**: User can specify which Gmail folder to watch (default: INBOX)
- [x] **GMAIL-04**: User can configure the global allowed senders list (at least one address required)

### LM Studio Configuration (LMS)

- [x] **LMS-01**: User can enter the LM Studio base URL (default pre-filled: `http://localhost:1234/v1`)
- [x] **LMS-02**: User can enter the model tag (default pre-filled: `google/gemma-4-26b-a4b`)
- [x] **LMS-03**: User can set temperature and max_tokens (defaults pre-filled: 0.4, 4096)
- [x] **LMS-04**: User can set the `lms` CLI path (default pre-filled: `lms`)

### Hosting Provider (HOST)

- [x] **HOST-01**: User can select their hosting provider from: SiteGround, Generic SSH/SFTP, Netlify, Vercel, GitHub Pages
- [x] **HOST-02**: When SiteGround or Generic SSH/SFTP is selected, user sees SSH/SFTP fields: host, port, username, SSH key path or password, remote base path
- [x] **HOST-03**: When Netlify is selected, user sees: API token, site ID
- [x] **HOST-04**: When Vercel is selected, user sees: API token, project name/ID
- [x] **HOST-05**: When GitHub Pages is selected, user sees: target branch (default: `gh-pages`)
- [x] **HOST-06**: Only the fields for the selected provider are visible; other provider fields are hidden
- [x] **HOST-07**: Site base URL is collected on the hosting step for SiteGround/SSH-SFTP/GitHub Pages; for Netlify and Vercel it is fetched via their respective APIs using the token and site/project identifier

### Inbox Manager (INBOX)

- [x] **INBOX-01**: User can define at least one inbox with slug + site name. Monitoring address (`gmail_local+slug@gmail.com`), site URL (`<site_base_url>/<slug>`), and site base path (`/<slug>/`) are derived from prior-step inputs, not re-entered.
- [x] **INBOX-02**: User can add additional inbox cards in the same session
- [x] **INBOX-03**: User can remove any inbox card except when only one remains
- [x] **INBOX-04**: Inbox slugs are validated for uniqueness across all defined inboxes on blur

### Output & File Writing (OUT)

- [x] **OUT-01**: Wizard displays a preview of the generated `.env` and `config.yaml` contents before writing to disk; sensitive fields show only the last 4 characters (`••••••••3f9a`)
- [x] **OUT-02**: User must explicitly click "Write Config Files" to trigger the write — no writes happen before this action
- [x] **OUT-03**: Files are written atomically using `tempfile.mkstemp()` + `os.replace()` — a crash or Ctrl-C mid-write cannot produce a partial or zero-byte config
- [x] **OUT-04**: If `.env` or `config.yaml` already exist when the wizard launches, all fields are pre-filled from the existing values
- [x] **OUT-05**: If existing config is detected, user must check an "Overwrite existing config" checkbox before the "Write Config Files" button becomes active
- [x] **OUT-06**: After a successful write, user sees a success screen with the exact command to run the workflow (`./scripts/run-workflow.sh`)

---

## v2 Requirements (Deferred)

- Live credential validation (IMAP connection test, SSH connectivity check)
- Copy-to-clipboard on preview output
- Save-and-resume across sessions
- Windows path normalisation (Windows not in v1 scope)
- Per-inbox allowed_senders configuration in the wizard

---

## Out of Scope

- Cloud-hosted setup UI — localhost only; no authentication or access control needed
- Database or persistent wizard state — one-shot, stateless
- Drag-to-reorder inboxes — inbox order in config.yaml is not meaningful
- Modifying `workflow/config.py` to support non-SiteGround providers — wizard collects the fields; workflow-side loader changes are a separate task
- Web framework login/sessions — single local user, no auth layer

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SRV-01 | Phase 1 | Pending |
| SRV-02 | Phase 1 | Pending |
| SRV-03 | Phase 1 | Pending |
| SRV-04 | Phase 1 | Pending |
| UX-01 | Phase 2 | Pending |
| UX-02 | Phase 2 | Pending |
| UX-03 | Phase 2 | Pending |
| UX-04 | Phase 2 | Pending |
| GMAIL-01 | Phase 2 | Pending |
| GMAIL-02 | Phase 2 | Pending |
| GMAIL-03 | Phase 2 | Pending |
| GMAIL-04 | Phase 2 | Pending |
| LMS-01 | Phase 2 | Pending |
| LMS-02 | Phase 2 | Pending |
| LMS-03 | Phase 2 | Pending |
| LMS-04 | Phase 2 | Pending |
| HOST-01 | Phase 3 | Validated |
| HOST-02 | Phase 3 | Validated |
| HOST-03 | Phase 3 | Validated |
| HOST-04 | Phase 3 | Validated |
| HOST-05 | Phase 3 | Validated |
| HOST-06 | Phase 3 | Validated |
| HOST-07 | Phase 3 | Validated |
| INBOX-01 | Phase 3 | Validated |
| INBOX-02 | Phase 3 | Validated |
| INBOX-03 | Phase 3 | Validated |
| INBOX-04 | Phase 3 | Validated |
| OUT-01 | Phase 4 | Pending |
| OUT-02 | Phase 4 | Pending |
| OUT-03 | Phase 4 | Pending |
| OUT-04 | Phase 4 | Pending |
| OUT-05 | Phase 4 | Pending |
| OUT-06 | Phase 4 | Pending |
