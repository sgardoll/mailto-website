---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Interactive SPA Pipeline
status: roadmap_ready
stopped_at: Phase 14
last_updated: "2026-04-20T00:00:00Z"
last_activity: 2026-04-20 — v2.0 roadmap created (Phases 14-19)
progress:
  total_phases: 6
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-20 for v2.0 milestone start)

**Core value:** Email an idea. Get a website. No CMS, no editor, no dashboard.
**Current focus:** Redesign generation pipeline — 5-stage interactive SPA module builder

## Current Position

Phase: 14 — Foundation (not started)
Plan: —
Status: Roadmap ready, awaiting phase planning
Last activity: 2026-04-20 — v2.0 roadmap written (Phases 14-19, 30 requirements mapped)

```
v2.0 progress: [                    ] 0% (0/6 phases)
```

## Phase Overview

| Phase | Name | Requirements | Status |
|-------|------|--------------|--------|
| 14 | Foundation | PIPE-01, DIST-03, CONF-01, SPA-01..04, PROF-01..02 | Not started |
| 15 | INGEST | ING-01..04, CONF-02 | Not started |
| 16 | DISTILL + PLAN | DIST-01..02, PLAN-01..02, PIPE-03..04 | Not started |
| 17 | BUILD + Validator | BUILD-01..05, VAL-01..07 | Not started |
| 18 | INTEGRATE + Orchestrator | INT-01..05, SPA-05, PIPE-02, SEC-01..02 | Not started |
| 19 | End-to-End + Hardening | (integration/regression — no new REQ-IDs) | Not started |

## Key Decisions (v2.0)

| Decision | Rationale |
|----------|-----------|
| mechanic.kind enum capped at 5 for v2.0 (calculator, wizard, drill, scorer, generator) | Research confirmed 14B model reliability; comparator/matcher deferred |
| Phase 14 is hard prerequisite for all others | Enum + manifest schema must be stable before any pipeline stage is written |
| Phase 15 (INGEST) independent of 16-17 | Can be developed in parallel once Phase 14 is complete |
| validator.py written before build.py (TDD) | Prevents shipping BUILD without a deterministic correctness gate |
| .gitignore audit encoded as startup assertion in integrate.py | Prevents silent failure where generated modules are written but never committed |
| window.AI() proxy in Phase 18 only | Direct localhost fetch is the primary path; proxy only needed for HTTPS deployments |
| New pip deps scoped to workflow_engine/requirements.txt | v1.0 "no new deps" constraint applied only to setup wizard; workflow engine is a separate app |

## Accumulated Context

### Open Questions (must resolve before noted phase)

| Question | Blocks | Notes |
|----------|--------|-------|
| Full mechanic.kind list — 5 confirmed, original brief said 13 | Phase 14 | Research recommends 5 for v2.0; resolve before writing enum |
| yt-dlp + whisper.cpp installation model — system tools or wizard installs | Phase 15 | shutil.which() pre-flight handles absence gracefully either way |
| window.AI() scope: local-only or proxy for HTTPS | Phase 18 | SPA-05 is in Phase 18; decide before integrate.py is written |

### Watch-Outs

- Base64 truncation at max_tokens: generate raw HTML as JSON-escaped string, base64 in Python post-extraction; always check finish_reason == "length"
- Alpine.js x-if on div / Alpine.store() without alpine:init: inject known-good exemplar in every BUILD prompt
- Retry loop cap: MAX_RETRIES = 3; abort if error on attempt N matches error on N-1; never raise temperature on retry
- Chromium Private Network Access blocks window.AI() for HTTPS deployments — proxy or graceful static degradation required

## Quick Tasks Completed

| Date | Slug | Summary | Commit |
|------|------|---------|--------|
| 2026-04-19 | done-screen-site-link | First iteration of success-screen redesign | f70ba6e |
| 2026-04-19 | wizard-deploy-siteground | In-wizard SiteGround deploy button | 07f20c7 |
| 2026-04-20 | v1.1-architecture-split | Repo restructured into bounded contexts | f5f22c1 |
| 2026-04-20 | v1.1-config-contract | Config contract + provider enum extracted | 258a87a |
| 2026-04-20 | v1.1-deploy-adapter | Provider registry + SiteGround adapter | 9c371c1 |
| 2026-04-20 | v1.1-vercel-stepper-cleanup | Vercel provider + stepper UI + diagnostics + cleanup | 159393d |
| 2026-04-20 | v1.1-workflow-engine-deploy | Workflow engine SSH deploy + systemd + health check | 478c826 |

## Deferred Items

| Category | Item | Status |
|----------|------|--------|
| Runtime | Live credential validation (IMAP/SMTP/SSH probe) | Deferred to v1.2 |
| Runtime | Streaming npm/SFTP output in deploy panel | Deferred to v1.2 |
| Runtime | Netlify/GitHub Pages/Generic SSH providers | Deferred to v1.2 |
| Runtime | Live E2E test with real SiteGround/Vercel credentials | Requires human-provided credentials |
| v2.0 | comparator, matcher kinds | Deferred — validate model reliability first |
| v2.0 | Rollback UI | git revert + redeploy is the v2.0 path |
| v2.0 | tracker, sandbox, simulator, evaluator, decision_matrix, prompt_lab kinds | Later milestone |
| v2.0 | Vector RAG with imperative-verb filtering | INGEST enhancement for v2.x |

## Session Continuity

Last session: 2026-04-20
Stopped at: v2.0 roadmap created — ready for `/gsd-plan-phase 14`
Resume file: None
