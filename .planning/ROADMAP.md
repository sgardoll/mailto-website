# Roadmap: thoughts-to-platform-builder Onboarding Wizard

## Milestones

- ✅ **v1.0 Onboarding Wizard + SiteGround Deploy** — Phases 1-4 (shipped 2026-04-20)
- 🚧 **v1.1 Runtime/Setup Separation + Deploy Contract Alignment** — Phases 5-11 (in progress)

## Phases

<details>
<summary>✅ v1.0 Onboarding Wizard + SiteGround Deploy (Phases 1-4) — SHIPPED 2026-04-20</summary>

- [x] Phase 1: Server Foundation (3/3 plans) — completed 2026-04-19
- [x] Phase 2: Core Form & Config Engine (6/6 plans) — completed 2026-04-19
- [x] Phase 3: Hosting Provider & Inbox Manager (7/7 plans) — completed 2026-04-19
- [x] Phase 4: Preview, Write & Completion (3/3 plans) — completed 2026-04-19

See `.planning/milestones/v1.0-ROADMAP.md` for full phase details, `v1.0-REQUIREMENTS.md` for the traceability archive, and `v1.0-MILESTONE-AUDIT.md` for verification.

</details>

### 🚧 v1.1 Runtime/Setup Separation + Deploy Contract Alignment (In Progress)

**Milestone Goal:** Cleanly separate setup/onboarding code from workflow/runtime engine, normalize deploy provider contracts, implement Vercel runtime, and harden multi-inbox routing.

#### Phase 5: Architecture Split + Folder Moves
**Goal**: Reorganize repo tree into bounded contexts — `apps/setup-wizard`, `apps/workflow-engine`, `packages/config-contract`, `packages/site-template`, `runtime/sites`, `runtime/state`
**Depends on**: Phase 4
**Requirements**: [SEP-01, SEP-02, SEP-04, SEP-05]
**Success Criteria** (what must be TRUE):
  1. `setup/` code moved to `apps/setup-wizard/` with no runtime mutations
  2. `workflow/` code moved to `apps/workflow-engine/` with no setup UI
  3. `framework/site-template/` moved to `packages/site-template/`
  4. `sites/` and `workflow/state/` relocated under `runtime/` root
  5. All imports, scripts, and references updated to new paths
**Plans**: 3 plans

Plans:
- [ ] 05-01: Audit all cross-references between setup/ and workflow/ (import map, script references, config paths)
- [ ] 05-02: Execute folder moves + update all imports/paths atomically
- [ ] 05-03: Verify build, tests, and end-to-end wizard flow still work post-move

#### Phase 6: Config Contract Extraction + Migration Tooling
**Goal**: Extract typed config schema into `packages/config-contract/` with validation and migration; replace direct `.env`/`config.yaml` writes with contract-driven config
**Depends on**: Phase 5
**Requirements**: [SEP-03, SEP-06, SEP-07, PROV-01]
**Success Criteria** (what must be TRUE):
  1. `packages/config-contract/` defines validated schema for all config fields
  2. Setup writes config through contract (not directly to files)
  3. Runtime reads config through contract (not hardcoded paths)
  4. Provider enum unified between setup and runtime (`ssh_sftp` canonical)
  5. Migration tool converts old `config.yaml` to new schema
**Plans**: 3 plans

Plans:
- [ ] 06-01: Define config schema (dataclasses + validation) in `packages/config-contract/`
- [ ] 06-02: Refactor setup builder to use contract for config generation
- [ ] 06-03: Refactor runtime config loader to use contract + migration tool

#### Phase 7: Runtime Deploy Adapter Abstraction
**Goal**: Define `DeployProvider` protocol/interface; migrate SiteGround into adapter; implement provider capability checks centrally
**Depends on**: Phase 6
**Requirements**: [PROV-02, PROV-03, PROV-05, PROV-06]
**Success Criteria** (what must be TRUE):
  1. `DeployProvider` protocol defined with `bootstrap()`, `build()`, `deploy()`, `report()` methods
  2. SiteGround provider implements the protocol (migrated from hardcoded logic)
  3. Provider registry/factory resolves provider by config key
  4. Non-implemented providers raise actionable errors (no silent `not_implemented`)
  5. Capability checks enforced centrally (not scattered guard functions)
**Plans**: 3 plans

Plans:
- [ ] 07-01: Define `DeployProvider` protocol + provider registry in `apps/workflow-engine/`
- [ ] 07-02: Migrate SiteGround deploy logic into `SiteGroundProvider` adapter
- [ ] 07-03: Centralize provider capability checks + fail-fast for unimplemented providers

#### Phase 8: Vercel Runtime Deploy Implementation
**Goal**: Implement `VercelProvider` — API token auth, project creation, deploy via Vercel API
**Depends on**: Phase 7
**Requirements**: [PROV-04]
**Success Criteria** (what must be TRUE):
  1. `VercelProvider` implements `DeployProvider` protocol
  2. Vercel API token collected in setup wizard (new provider fields)
  3. Deploy flow: create project → push content → verify deployment → report live URL
  4. Per-inbox deploy works independently (multi-inbox support)
  5. Deploy result reported with provider + target + URL per inbox
**Plans**: 3 plans

Plans:
- [ ] 08-01: Research Vercel deploy API + define `VercelProvider` skeleton
- [ ] 08-02: Implement Vercel auth, project creation, and deploy flow
- [ ] 08-03: Wire Vercel provider into setup wizard + end-to-end test

#### Phase 9: Multi-Inbox Routing/Deploy Validation and Diagnostics
**Goal**: Multi-inbox config semantics, startup diagnostics, per-inbox deploy reporting
**Depends on**: Phase 7
**Requirements**: [INBOX-01, INBOX-02, INBOX-03]
**Success Criteria** (what must be TRUE):
  1. `config.yaml` with multiple inboxes loads without errors
  2. Engine boot logs all loaded inboxes + route map
  3. Deploy reports provider + target + result per inbox (not aggregate)
  4. Routing logs prove message-to-inbox correctness
  5. Each inbox deploys to its own provider target independently
**Plans**: 2 plans

Plans:
- [ ] 09-01: Implement startup diagnostics (inbox loading, route map, validation)
- [ ] 09-02: Per-inbox deploy reporting + routing log verification

#### Phase 10: Stepper Indicator UI
**Goal**: Implement the stepper indicator design from `.planning/sketches/001-stepper-indicator` into the setup wizard
**Depends on**: Phase 5 (folder moves must not break template paths)
**Requirements**: [UX-01]
**Success Criteria** (what must be TRUE):
  1. Stepper indicator renders in setup wizard with active step highlight
  2. Visual matches the design in `.planning/sketches/001-stepper-indicator`
  3. Step transitions animate smoothly
  4. Works across all 5 wizard steps
**Plans**: 2 plans

Plans:
- [ ] 10-01: Extract stepper design from sketch into reusable component
- [ ] 10-02: Integrate stepper into wizard layout + test across all steps

#### Phase 11: End-to-End UAT and Cleanup
**Goal**: Full end-to-end validation across SiteGround + Vercel with 2 inboxes each; cleanup dead code; final verification
**Depends on**: Phases 8, 9, 10
**Requirements**: [INBOX-04, INBOX-05, UAT-01]
**Success Criteria** (what must be TRUE):
  1. SiteGround + 2 inboxes: full flow verified (config → deploy → live URL)
  2. Vercel + 2 inboxes: full flow verified (config → deploy → live URL)
  3. No dead code, unused imports, or orphaned references remain
  4. All 92+ v1.0 tests still pass
  5. Repo tree clearly separates authored code vs generated/runtime data
**Plans**: 2 plans

Plans:
- [ ] 11-01: End-to-end UAT: SiteGround + 2 inboxes, Vercel + 2 inboxes
- [ ] 11-02: Dead code cleanup + final test suite verification

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Server Foundation | v1.0 | 3/3 | Complete | 2026-04-19 |
| 2. Core Form & Config Engine | v1.0 | 6/6 | Complete | 2026-04-19 |
| 3. Hosting Provider & Inbox Manager | v1.0 | 7/7 | Complete | 2026-04-19 |
| 4. Preview, Write & Completion | v1.0 | 3/3 | Complete | 2026-04-19 |
| 5. Architecture Split + Folder Moves | v1.1 | 0/3 | Not started | - |
| 6. Config Contract Extraction + Migration | v1.1 | 0/3 | Not started | - |
| 7. Runtime Deploy Adapter Abstraction | v1.1 | 0/3 | Not started | - |
| 8. Vercel Runtime Deploy Implementation | v1.1 | 0/3 | Not started | - |
| 9. Multi-Inbox Routing/Deploy Validation | v1.1 | 0/2 | Not started | - |
| 10. Stepper Indicator UI | v1.1 | 0/2 | Not started | - |
| 11. End-to-End UAT and Cleanup | v1.1 | 0/2 | Not started | - |
| 5. Architecture Split + Folder Moves | v1.1 | 0/3 | Not started | - |
| 6. Config Contract Extraction + Migration | v1.1 | 0/3 | Not started | - |
| 7. Runtime Deploy Adapter Abstraction | v1.1 | 0/3 | Not started | - |
| 8. Vercel Runtime Deploy Implementation | v1.1 | 0/3 | Not started | - |
| 9. Multi-Inbox Routing/Deploy Validation | v1.1 | 0/2 | Not started | - |
| 10. Stepper Indicator UI | v1.1 | 0/2 | Not started | - |
| 11. End-to-End UAT and Cleanup | v1.1 | 0/2 | Not started | - |
