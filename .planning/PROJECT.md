# thoughts-to-platform-builder

## What This Is

A self-extending publishing platform powered by your inbox and a local LLM. Email an idea to a Gmail plus-alias, and the pipeline — IMAP listener → orchestrator → local LLM (via LM Studio) → Astro build → deploy — folds it into a living website. A five-step browser wizard handles first-time setup: Gmail credentials, LM Studio model selection, hosting provider, inbox definition, and config preview/write.

The model operates under two prime directives enforced in code: **fold in, don't silo** (every new entry must extend or link to an existing thread) and **take initiative** (synthesise the email into something useful, never a verbatim transcription).

## Core Value

Email an idea. Get a website. No CMS, no editor, no dashboard — just send mail to a plus-alias and watch the site evolve. The wizard collapses all setup friction into a five-step browser flow with server-side validation, atomic file writes, and one-click deploy.

## Current State (v1.1 shipped 2026-04-20)

- **13 phases, ~6,400 LOC Python + ~2,250 additional LOC for v1.1 (Python: 4,100; HTML/CSS/JS: 2,530)**
- **92 automated tests** covering validator, builder, preview/write, deploy
- **Bounded context separation** — `apps/setup-wizard/`, `apps/workflow-engine/`, `packages/config-contract/`, `packages/site-template/`, `runtime/`
- **DeployProvider adapter pattern** with SiteGround + Vercel implementations
- **Workflow engine SSH deploy** with systemd service and health check endpoint
- Timeline: 2026-04-19 → 2026-04-20 (~24 hours total wall time)

## Current Milestone: v2.0 Interactive SPA Pipeline

**Goal:** Redesign the email-to-site generation pipeline from a markdown-curator model to a 5-stage interactive module builder that produces Gemini Canvas–style SPA output per inbox.

**Target features:**
- 5-stage pipeline: INGEST → DISTILL → PLAN → BUILD → INTEGRATE
- mechanic.kind enum (13 types) forces output variety — wizards, matchers, scorers, drills
- Tailwind CDN + Alpine.js modules with window.AI() + window.STATE shared state
- JSON envelope with base64-encoded HTML/JS artifacts
- Deterministic post-build validator + auto-retry
- SPA manifest-only context passback (not full HTML each turn)
- Per-inbox profile.json for shared state persistence
- Module-level versioning + rollback via git
- Content extraction: yt-dlp + whisper.cpp (video), readability (articles)

## Context

The platform watches one or more Gmail plus-aliases via IMAP IDLE. When an email arrives, the pipeline processes it through a local LLM (via a single LM Studio server) and publishes the result to the matching per-inbox Astro site. Before v1.0, onboarding required hand-editing a YAML file and understanding SSH/SFTP credential layouts — high friction for non-technical collaborators.

The five-step wizard collapses all setup into a browser-based flow with server-side validation, prefill from existing config (re-runs don't start from scratch), atomic file writes with rollback, and a one-click SiteGround or Vercel deploy.

## Who It's For

- Developers cloning this repo for the first time
- Non-technical collaborators running the pipeline on their own machine
- Stuart, for onboarding future contributors without setup support calls

## Requirements

### Validated (v1.0)

- ✓ Local web UI launches from a single command (`./scripts/setup.sh`) — v1.0 (SRV-01)
- ✓ Detects whether `.env` and `workflow/config.yaml` already exist and prefills — v1.0 (OUT-04)
- ✓ Collects Gmail app password with link to app-password creation page — v1.0 (GMAIL-02, UX-04)
- ✓ Collects imap/smtp user (same Gmail address applied across both) — v1.0 (GMAIL-01)
- ✓ Hosting provider selection (SiteGround / Generic SSH / Netlify / Vercel / GitHub Pages) — v1.0 (HOST-01..06)
- ✓ Per-provider credential fields with conditional visibility — v1.0 (HOST-02..05)
- ✓ LM Studio config (base_url, model, CLI path, temperature, max_tokens) — v1.0 (LMS-01..04)
- ✓ Inbox definition with slug uniqueness enforcement — v1.0 (INBOX-01..04)
- ✓ Multi-inbox UI (add/remove cards in-session) — v1.0 (INBOX-02, INBOX-03)
- ✓ Preview step with masked secrets (last-4 display) — v1.0 (OUT-01)
- ✓ Atomic file writes with pair-write + rollback — v1.0 (OUT-03)
- ✓ Overwrite checkbox gate when existing config detected — v1.0 (OUT-05)
- ✓ Browser auto-open with free-port probing — v1.0 (SRV-01, SRV-02)
- ✓ Clean shutdown via Exit button + atexit + SIGTERM — v1.0 (SRV-03)
- ✓ Write-permission pre-flight — v1.0 (SRV-04)
- ✓ Progress indicator with active step highlight — v1.0 (UX-01)
- ✓ Inline blur validation, not submit-only — v1.0 (UX-02)
- ✓ Show/hide toggles on all password/token fields — v1.0 (UX-03)
- ✓ Python 3.11+ only, no new runtime deps beyond Flask + PyYAML + paramiko — v1.0
- ✓ Success screen with next-step command — v1.0 (OUT-06)

### Validated (v1.1)

- ✓ Bounded context separation (SEP-01, SEP-02, SEP-04, SEP-05) — v1.1
- ✓ Config contract extraction with validation + migration (SEP-03, SEP-06, SEP-07) — v1.1
- ✓ Unified provider enum (PROV-01) — v1.1
- ✓ DeployProvider adapter interface (PROV-02) — v1.1
- ✓ SiteGround adapter implementation (PROV-03) — v1.1
- ✓ Vercel adapter implementation (PROV-04) — v1.1
- ✓ Fail-fast for unimplemented providers (PROV-05) — v1.1
- ✓ Centralized capability checks (PROV-06) — v1.1
- ✓ Multi-inbox config semantics (INBOX-01) — v1.1
- ✓ Startup diagnostics (INBOX-02) — v1.1
- ✓ Per-inbox deploy reporting (INBOX-03) — v1.1
- ✓ Workflow engine SSH deploy with systemd (INBOX-04, INBOX-05) — v1.1
- ✓ Stepper indicator UI (UX-01) — v1.1

### Validated beyond original scope (v1.0 stretch)

- ✓ Pasteable SSH private key textarea (instead of file path) — v1.0 stretch, driven by SiteGround's UX (they hand you the key as text)
- ✓ SSH key passphrase support — v1.0 stretch, required for SiteGround-generated encrypted keys
- ✓ One-click SiteGround deploy from success screen — v1.0 stretch, replaces "run `./scripts/run-workflow.sh` manually" with an in-wizard bootstrap → npm install → build → SFTP deploy flow per inbox

### Active (v1.2)

- [ ] Live credential validation (IMAP/SMTP/SSH probe)
- [ ] Streaming npm/SFTP output in deploy panel
- [ ] Additional deploy providers (Netlify, GitHub Pages, Generic SSH)

### Out of Scope

- Authentication or access control on the local UI — it's localhost, single user
- Persistent state / database — one-shot wizard, stateless
- Cloud-hosted setup wizard — local only
- Save-and-resume across sessions — prefill-from-existing-config covers the resume need
- Windows path normalization — Windows not in scope
- Per-inbox `allowed_senders` in the wizard — global list is sufficient for v1

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Local web UI over CLI prompts | Visual for credential entry, easier multi-inbox, easier preview | ✓ Good — users report the flow is intuitive |
| Flask + Jinja2 (no build step) | Matches existing Python stack; no new runtime | ✓ Good — server boots in < 2s |
| Pure builder/validator module (`setup/builder.py`) | Testable without the Flask layer | ✓ Good — 58 builder tests run without any network |
| Preview before write | Safer UX; user sees bytes before they hit disk | ✓ Good — caught several masking bugs in dev |
| Atomic pair-write with rollback | Power-loss / Ctrl-C mid-write must not produce partial config | ✓ Good — rollback verified in tests |
| Pasteable SSH key textarea (v1.0 stretch) | SiteGround hands you the key as text — asking for a path meant users had to save + chmod themselves | ✓ Good — key is written to `workflow/state/siteground.key` at 0600 on hosting submit |
| One-click deploy from success screen (v1.0 stretch) | Success screen previously showed "run this shell command" — unfriendly for non-technical users | ✓ Good for SiteGround; other providers deferred to v1.1 |
| `workflow/config.py` only parses `SiteGroundConfig` | Runtime deploy loop only supports SiteGround today | ⚠️ Revisit in v1.1 when adding Netlify/Vercel/GHP deploy |
| Clean break migration (no shim layer) for v1.1 | Long shims accumulate debt; clean break forces honest boundaries | ✓ v1.1 decision — folder moves + contract extraction happen together |
| Runtime deploy adapter interface pattern | Providers must be pluggable without touching core pipeline logic | ✓ v1.1 decision — adapter pattern for SiteGround + Vercel |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

## Constraints

- **No new runtime dependencies.** Flask + PyYAML + paramiko (already in the project) + python-dotenv (optional, fallback included).
- **Python 3.11+.** Matches existing pipeline prereqs.
- **Single-user localhost.** No auth, no multi-tenancy.
- **Astro template in `framework/site-template/`** is the single source of truth for site structure; `workflow/site_bootstrap.ensure_site` copies it per inbox.

---
*Last updated: 2026-04-20 — v1.1 milestone shipped (Runtime/Setup Separation + Deploy Contract Alignment)*
