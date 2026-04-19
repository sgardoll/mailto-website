# Milestones

## v1.1 — Runtime/Setup Separation + Deploy Contract Alignment

**Status:** ✅ SHIPPED 2026-04-20
**Phases:** 9 (Phase 5 → Phase 13)
**Plans:** 23 | **Commits:** 6 | **LOC:** ~1,750 added, ~400 modified
**Timeline:** 2026-04-20 (~1.5 hours wall time)

### Delivered

Clean bounded-context separation with deploy provider adapter pattern, Vercel runtime support, multi-inbox diagnostics, stepper UI, and critical workflow engine deployment to remote servers via SSH with systemd service management.

### Key Accomplishments

1. **Bounded context separation** — repo restructured into `apps/setup-wizard/`, `apps/workflow-engine/`, `packages/config-contract/`, `packages/site-template/`, `runtime/` (Phase 05)
2. **Config contract extraction** — typed schema with validation, migration tooling, unified provider enum (Phase 06)
3. **DeployProvider adapter pattern** — SiteGround migrated to adapter, provider registry with fail-fast for unimplemented providers (Phase 07)
4. **Vercel runtime** — API token auth, project creation, deploy via Vercel API (Phase 08)
5. **Multi-inbox diagnostics** — startup logging of inboxes/route map, per-inbox deploy reporting (Phase 09)
6. **Stepper indicator UI** — visual progress across all 5 wizard steps (Phase 10)
7. **Workflow engine SSH deploy** — deploy_engine.py with systemd service template, health check endpoint on port 8899 (Phase 12)

### Known Deferrals (v1.2 candidates)

- Live credential validation (IMAP/SMTP/SSH probe) — requires network test infrastructure
- Streaming npm/SFTP output in deploy panel — UX enhancement
- Additional providers (Netlify, GitHub Pages, Generic SSH) — Vercel proves the pattern

### Phases

| # | Name | Plans | Completed |
|---|------|-------|-----------|
| 05 | Architecture Split + Folder Moves | 3/3 | 2026-04-20 |
| 06 | Config Contract Extraction | 3/3 | 2026-04-20 |
| 07 | Runtime Deploy Adapter Abstraction | 3/3 | 2026-04-20 |
| 08 | Vercel Runtime Deploy | 3/3 | 2026-04-20 |
| 09 | Multi-Inbox Routing/Deploy Validation | 2/2 | 2026-04-20 |
| 10 | Stepper Indicator UI | 2/2 | 2026-04-20 |
| 11 | End-to-End UAT and Cleanup | 2/2 | 2026-04-20 |
| 12 | Workflow Engine Deployment to Target Server | 3/3 | 2026-04-20 |
| 13 | End-to-End Verification + Milestone Close | 2/2 | 2026-04-20 |

Detail in `.planning/milestones/v1.1-ROADMAP.md` and `.planning/milestones/v1.1-MILESTONE-AUDIT.md`.

---

## v1.0 — Onboarding Wizard + SiteGround Deploy

**Status:** ✅ SHIPPED 2026-04-20
**Phases:** 4 (01 Server Foundation → 04 Preview, Write & Completion)
**Plans:** 19 | **Commits:** 80 | **LOC:** ~6,400 (Python 3,865 + JS/CSS/HTML 2,530)
**Timeline:** 2026-04-19 → 2026-04-20 (~22 hours wall time)
**Tests:** 92 passing

### Delivered

A local web-based onboarding wizard that takes a user from cloning the repo to a working `.env` + `workflow/config.yaml` and — for SiteGround targets — a live deployed site, all through a 5-step browser flow with server-side validation, atomic writes, and one-click deploy.

### Key Accomplishments

1. **Flask wizard skeleton** with free-port probing, browser auto-open, clean shutdown, and write-permission pre-flight (Phase 01)
2. **Pure builder/validator module** (`setup/builder.py`) produces final `.env` + `config.yaml` strings with 58 tests covering validation, building, hydration from existing files, and preview masking (Phase 02)
3. **Polished 5-step form** with progress indicator, blur validation, show/hide toggles, help text, and Gmail-address fan-out into imap/smtp config (Phase 02)
4. **Conditional provider fields + multi-inbox manager** covering SiteGround, Generic SSH, Netlify, Vercel, GitHub Pages (Phase 03)
5. **Preview → atomic write lifecycle**: server-side preview with masked secrets, temp-file + fsync + os.replace pair-write with rollback, overwrite gate (Phase 04)
6. **One-click SiteGround deploy from success screen** (in-phase stretch): bootstrap → npm install → build → SFTP mirror → live URL, with per-inbox progress tracking and pasteable private key + passphrase support (Phase 04 stretch)

### Architecture Highlights

- Single authoritative `setup/builder.py` — server and UI consume its contract, never duplicate
- `workflow/deploy_once.py` — reusable bootstrap+build+deploy loop, usable from wizard and CLI (`python -m workflow.deploy_once`)
- SSH key persisted at `workflow/state/siteground.key` with 0600 perms on hosting submit (not as an afterthought at write-config time)
- Paramiko auth errors surface as actionable messages instead of generic "Authentication failed"

### Known Deferrals (v1.1 candidates)

- Non-SiteGround deploy implementations (Netlify/Vercel/GHP/Generic SSH return `not_implemented` from `POST /deploy`)
- Provider dataclasses in `workflow/config.py` (only `SiteGroundConfig` parses today)
- Streaming npm/SFTP output in deploy panel (currently phase-level progress)
- Live credential validation (IMAP/SMTP probe, SSH connectivity test)

### Phases

| # | Name | Plans | Completed |
|---|------|-------|-----------|
| 01 | Server Foundation | 3/3 | 2026-04-19 |
| 02 | Core Form & Config Engine | 6/6 | 2026-04-19 |
| 03 | Hosting Provider & Inbox Manager | 7/7 | 2026-04-19 |
| 04 | Preview, Write & Completion | 3/3 | 2026-04-19 |

Detail in `.planning/milestones/v1.0-ROADMAP.md` and `.planning/milestones/v1.0-MILESTONE-AUDIT.md`.

### Quick Tasks in this Milestone

- `done-screen-site-link` (f70ba6e) — first iteration of the success-screen redesign
- `wizard-deploy-siteground` (07f20c7) — in-wizard deploy launcher
