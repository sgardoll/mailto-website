# Roadmap: thoughts-to-platform-builder Onboarding Wizard

## Overview

Four phases deliver the wizard from bare server skeleton to a fully functioning, browser-based onboarding UI. Phase 1 establishes the server process and its lifecycle. Phase 2 builds the core form — Gmail, LM Studio, UX polish — backed by pure config-generation logic. Phase 3 adds hosting-provider conditional fields and the multi-inbox manager. Phase 4 closes the loop with the preview/confirm step, atomic file writes, overwrite protection, and the success screen.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Server Foundation** - Flask server skeleton with port probing, browser auto-open, pre-flight checks, and clean shutdown (2026-04-19)
- [ ] **Phase 2: Core Form & Config Engine** - Gmail and LM Studio form sections, UX framework (progress indicator, blur validation, show/hide, help text), and pure builder/validator logic
- [ ] **Phase 3: Hosting Provider & Inbox Manager** - Conditional hosting-provider fields for all 5 providers and the multi-inbox card manager
- [ ] **Phase 4: Preview, Write & Completion** - Preview screen with masking, atomic file writes, overwrite detection, and success screen

## Phase Details

### Phase 1: Server Foundation
**Goal**: The wizard process runs reliably — it finds a free port, opens the browser at the right moment, survives Ctrl-C cleanly, and refuses to start if it cannot write to the project directory
**Depends on**: Nothing (first phase)
**Requirements**: SRV-01, SRV-02, SRV-03, SRV-04
**Success Criteria** (what must be TRUE):
  1. Running `./scripts/setup.sh` opens the wizard in the default browser without manual URL copy-paste
  2. The server binds to a working port even when 5000 and 8080 are occupied
  3. Clicking "Exit Setup" or pressing Ctrl-C terminates the process without leaving orphaned Python processes
  4. If the project directory is not writable, the wizard shows a clear error before rendering the form
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — Flask server core: package init, port probe (prefer 7331, avoid 5000/8080), write-permission pre-flight, socket-probe browser auto-open, placeholder index.html (2026-04-19)
- [x] 01-02-PLAN.md — Entry point wiring: setup/requirements.txt (flask, python-dotenv), scripts/setup.sh (venv activation + pip install + python -m setup.server) (2026-04-19)
- [x] 01-03-PLAN.md — Shutdown lifecycle: POST /exit with threading dispatch (not direct shutdown — deadlock risk), atexit cleanup, SIGINT handler, Exit Setup button wired in index.html (2026-04-19)

### Phase 2: Core Form & Config Engine
**Goal**: Users can fill in Gmail credentials and LM Studio settings through a polished, validated form, and the underlying builder/validator logic produces correct `.env` and `config.yaml` output strings
**Depends on**: Phase 1
**Requirements**: UX-01, UX-02, UX-03, UX-04, GMAIL-01, GMAIL-02, GMAIL-03, GMAIL-04, LMS-01, LMS-02, LMS-03, LMS-04
**Success Criteria** (what must be TRUE):
  1. A visible progress indicator names all wizard steps and highlights the active one
  2. Leaving a required field blank and tabbing away shows an inline error on that field — not on submit
  3. Every password or token field has a show/hide toggle and remains pasteable
  4. Each field has help text and a link to the relevant external documentation page
  5. Entering a Gmail address once populates imap.user, smtp.user, and smtp.from_address in the generated config; the app password lands in `.env` and is referenced as `${GMAIL_APP_PASSWORD}` in `config.yaml`
**Plans**: TBD
**UI hint**: yes

### Phase 3: Hosting Provider & Inbox Manager
**Goal**: Users can select any of the five supported hosting providers and see only the fields relevant to their choice, and can define one or more named inboxes with slug uniqueness enforced
**Depends on**: Phase 2
**Requirements**: HOST-01, HOST-02, HOST-03, HOST-04, HOST-05, HOST-06, INBOX-01, INBOX-02, INBOX-03, INBOX-04
**Success Criteria** (what must be TRUE):
  1. Switching the hosting provider dropdown instantly shows only that provider's credential fields and hides all others
  2. Selecting SiteGround or Generic SSH/SFTP reveals host, port, username, SSH key path or password, and remote base path
  3. Selecting Netlify or Vercel reveals the correct API token and site identifier fields; selecting GitHub Pages reveals only the target branch field
  4. User can add a second inbox card in the same session and cannot remove the last remaining inbox card
  5. Entering a duplicate slug in any inbox card shows a uniqueness error on that field when leaving it
**Plans**: TBD
**UI hint**: yes

### Phase 4: Preview, Write & Completion
**Goal**: Users see exactly what will be written before committing, the write is atomic, existing configs are detected and protected behind an explicit overwrite checkbox, and a success screen tells the user what to run next
**Depends on**: Phase 3
**Requirements**: OUT-01, OUT-02, OUT-03, OUT-04, OUT-05, OUT-06
**Success Criteria** (what must be TRUE):
  1. The preview screen shows the full generated `.env` and `config.yaml` text with sensitive fields redacted to last-4 characters (`••••••••3f9a`)
  2. No files are written to disk until the user explicitly clicks "Write Config Files"
  3. A crash or Ctrl-C during the write does not leave a partial or zero-byte config on disk
  4. When existing `.env` or `config.yaml` are present on launch, all form fields are pre-filled from those values and the "Write Config Files" button is disabled until the user checks the "Overwrite existing config" checkbox
  5. After a successful write, the user sees a success screen displaying the exact command to run the workflow (`./scripts/run-workflow.sh`)
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Server Foundation | 0/3 | Not started | - |
| 2. Core Form & Config Engine | 0/TBD | Not started | - |
| 3. Hosting Provider & Inbox Manager | 0/TBD | Not started | - |
| 4. Preview, Write & Completion | 0/TBD | Not started | - |
