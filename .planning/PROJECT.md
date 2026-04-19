# thoughts-to-platform-builder — Onboarding UI

## What This Is

A local web-based onboarding wizard for the email-to-website pipeline. New users clone the repo, run `./scripts/setup.sh`, complete a 5-step wizard (Gmail → LM Studio → Hosting → Inboxes → Preview), and end up with a working `.env` + `workflow/config.yaml` plus — for SiteGround targets — a live deployed site launched directly from the success screen.

## Core Value

Zero-friction first-time setup: clone → one command → working config → optional one-click deploy. No hand-editing YAML, no copy-pasting example files, no manual SSH key plumbing.

## Current State (v1.0 shipped 2026-04-20)

- **4 phases, 19 plans, ~6,400 LOC (Python: 3,865; HTML/CSS/JS: 2,530)**
- **92 automated tests** covering validator, builder, preview/write, deploy
- **End-to-end verified** against a real SiteGround account (ssh.connectio.com.au) — pasteable private key + passphrase, atomic config write, Astro build per inbox, SFTP mirror deploy, live URL rendered on success screen
- Timeline: 2026-04-19 → 2026-04-20 (~22 hours wall time, 80 commits)

## Context

The underlying project (`thoughts-to-platform-builder`) is an email-to-website pipeline that watches a Gmail inbox, processes incoming emails with a local LM Studio model, and publishes them as posts to per-inbox Astro sites. Before v1.0, onboarding required hand-editing a YAML file and understanding SSH/SFTP credential layouts — high friction for non-technical collaborators.

The wizard collapses all that setup into a browser-based flow with server-side validation, prefill from existing config (re-runs don't start from scratch), atomic file writes with rollback, and a one-click SiteGround deploy.

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

### Validated beyond original scope (v1.0 stretch)

- ✓ Pasteable SSH private key textarea (instead of file path) — v1.0 stretch, driven by SiteGround's UX (they hand you the key as text)
- ✓ SSH key passphrase support — v1.0 stretch, required for SiteGround-generated encrypted keys
- ✓ One-click SiteGround deploy from success screen — v1.0 stretch, replaces "run `./scripts/run-workflow.sh` manually" with an in-wizard bootstrap → npm install → build → SFTP deploy flow per inbox

### Active (v1.1 candidates)

- [ ] Deploy implementations for Netlify / Vercel / GitHub Pages / Generic SSH (wizard currently returns `not_implemented` for non-SiteGround; Phase 5 scope)
- [ ] Provider dataclasses in `workflow/config.py` (only `SiteGroundConfig` today; other provider YAML blocks are silently ignored at runtime)
- [ ] Live credential validation (IMAP/SMTP probe, SSH connectivity test) before write
- [ ] Streaming npm/SFTP output in deploy panel (currently phase-level progress only)
- [ ] Copy-to-clipboard on the preview output blocks

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

## Constraints

- **No new runtime dependencies.** Flask + PyYAML + paramiko (already in the project) + python-dotenv (optional, fallback included).
- **Python 3.11+.** Matches existing pipeline prereqs.
- **Single-user localhost.** No auth, no multi-tenancy.
- **Astro template in `framework/site-template/`** is the single source of truth for site structure; `workflow/site_bootstrap.ensure_site` copies it per inbox.

---
*Last updated: 2026-04-20 after v1.0 milestone shipped*
