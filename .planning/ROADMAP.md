# Roadmap: mailto.website

## Milestones

- ✅ **v1.0 Onboarding Wizard + SiteGround Deploy** — Phases 1-4 (shipped 2026-04-20)
- ✅ **v1.1 Runtime/Setup Separation + Deploy Contract Alignment** — Phases 5-13 (shipped 2026-04-20)
- ✅ **v2.0 Interactive SPA Pipeline** — Phases 14-19 (shipped 2026-04-24)

## Phases

<details>
<summary>✅ v1.0 Onboarding Wizard + SiteGround Deploy (Phases 1-4) — SHIPPED 2026-04-20</summary>

- [x] Phase 1: Server Foundation (3/3 plans) — completed 2026-04-19
- [x] Phase 2: Core Form & Config Engine (6/6 plans) — completed 2026-04-19
- [x] Phase 3: Hosting Provider & Inbox Manager (7/7 plans) — completed 2026-04-19
- [x] Phase 4: Preview, Write & Completion (3/3 plans) — completed 2026-04-19

See `.planning/milestones/v1.0-ROADMAP.md` for full phase details, `v1.0-REQUIREMENTS.md` for the traceability archive, and `v1.0-MILESTONE-AUDIT.md` for verification.

</details>

<details>
<summary>✅ v1.1 Runtime/Setup Separation + Deploy Contract Alignment (Phases 5-13) — SHIPPED 2026-04-20</summary>

- [x] Phase 5: Architecture Split + Folder Moves (3/3 plans) — completed 2026-04-20
- [x] Phase 6: Config Contract Extraction + Migration (3/3 plans) — completed 2026-04-20
- [x] Phase 7: Runtime Deploy Adapter Abstraction (3/3 plans) — completed 2026-04-20
- [x] Phase 8: Vercel Runtime Deploy Implementation (3/3 plans) — completed 2026-04-20
- [x] Phase 9: Multi-Inbox Routing/Deploy Validation (2/2 plans) — completed 2026-04-20
- [x] Phase 10: Stepper Indicator UI (2/2 plans) — completed 2026-04-20
- [x] Phase 11: End-to-End UAT and Cleanup (2/2 plans) — completed 2026-04-20
- [x] Phase 12: Workflow Engine Deployment to Target Server (3/3 plans) — completed 2026-04-20
- [x] Phase 13: End-to-End Verification + Milestone Close (2/2 plans) — completed 2026-04-20

See `.planning/milestones/v1.1-ROADMAP.md` for full phase details and `.planning/milestones/v1.1-REQUIREMENTS.md` for the requirements archive.

</details>

### v2.0 Interactive SPA Pipeline (Phases 14-19)

- [x] **Phase 14: Foundation** - mechanic enum, manifest schema, config contract extension, SPA shell skeleton, profile.json bootstrap
- [x] **Phase 15: INGEST** - content extractors, ingest.py, yt-dlp + whisper.cpp + trafilatura wrappers, shutil.which pre-flights (completed 2026-04-20)
- [x] **Phase 16: DISTILL + PLAN** - prompt builders, distill.py, plan.py, mechanic_spec schema, structured LM output (completed 2026-04-21)
- [x] **Phase 17: BUILD + Validator** - validator.py TDD-first, build.py, Alpine exemplars per kind, retry loop (completed 2026-04-21)
- [x] **Phase 18: INTEGRATE + Orchestrator** - integrate.py, orchestrator wiring, pipeline_version flag, window.AI() proxy, .gitignore audit (completed 2026-04-22)
- [x] **Phase 19: End-to-End + Hardening** - integration tests, rollback tests, v1 regression, browser smoke test (completed 2026-04-24)

---

## Phase Details

### Phase 14: Foundation
**Goal**: The shared data contracts and SPA shell that all pipeline stages will reference are stable and importable
**Depends on**: Nothing (first phase of v2.0)
**Requirements**: PIPE-01, DIST-03, CONF-01, SPA-01, SPA-02, SPA-03, SPA-04, PROF-01, PROF-02
**Success Criteria** (what must be TRUE):
  1. `mechanic.kind` enum (calculator, wizard, drill, scorer, generator) is importable from `packages/config_contract/` and used identically by DISTILL, BUILD, and the validator — no local redefinitions
  2. `spa_manifest.json` schema is defined and parseable; a skeleton SPA shell reads it and renders hash-based navigation with at least one placeholder module
  3. `window.STATE` (localStorage-backed) and `window.AI()` bridge are injected by the SPA shell before any module script loads, verifiable in browser console
  4. `profile.json` is created at `runtime/state/<slug>/` during site bootstrap and is absent from the site git tree (covered by `.gitignore`)
  5. `pipeline_version` key is present in `packages/config_contract/`; `v1` is the default; importing the contract in both v1 and v2 code paths does not raise
**Plans**: 3 plans
- [ ] 14-01-PLAN.md — Config contract extension: MechanicKind enum + pipeline_version field + workflow_engine re-export (PIPE-01, DIST-03, CONF-01)
- [ ] 14-02-PLAN.md — SPA shell: spa_manifest_schema.json + seed manifest + shell.html with window.STATE, window.AI, hash routing, sandboxed iframe (SPA-01..04)
- [ ] 14-03-PLAN.md — profile.json bootstrap: extend ensure_site() + .gitignore rule (PROF-01, PROF-02)
**UI hint**: yes

### Phase 15: INGEST
**Goal**: Emails containing video URLs, article URLs, or plain text are all normalised into the same structured `normalized_input` payload regardless of whether optional system tools are installed
**Depends on**: Phase 14
**Requirements**: ING-01, ING-02, ING-03, ING-04, CONF-02
**Success Criteria** (what must be TRUE):
  1. A plain-text email produces a `normalized_input` dict with `body`, `subject`, and `sender` fields; no extraction is attempted
  2. A video-URL email triggers yt-dlp download + whisper.cpp transcription and the resulting transcript is present in `normalized_input`; the pipeline does not hang or deadlock on stderr (M4 Popen drain verified)
  3. An article-URL email produces extracted article text via trafilatura (readability-lxml fallback on parse failure)
  4. When yt-dlp, ffmpeg, or whisper-cli are absent (`shutil.which()` returns None), the pipeline starts without error and falls back to treating the URL as plain text
  5. New pip deps (`yt-dlp`, `pywhispercpp`, `trafilatura`, `sentence-transformers`, `faiss-cpu`, `gitpython`, `jsonschema`) are listed in `apps/workflow_engine/requirements.txt`
**Plans**: 3 plans
- [x] 15-01-PLAN.md — Append v2.0 pip deps to apps/workflow_engine/requirements.txt (CONF-02)
- [x] 15-02-PLAN.md — Create ingest.py module + unit tests: plain-text/video/article paths with tool-absent fallback (ING-01..ING-04)
- [x] 15-03-PLAN.md — Wire ingest.ingest() into orchestrator._process_locked before topic_curator (ING-01 integration)

### Phase 16: DISTILL + PLAN
**Goal**: An email's `normalized_input` is converted into a validated `mechanic_spec` and a routing decision (new module / extend / upgrade state only) before any HTML is generated
**Depends on**: Phase 14
**Requirements**: DIST-01, DIST-02, PLAN-01, PLAN-02, PIPE-03, PIPE-04
**Success Criteria** (what must be TRUE):
  1. DISTILL calls LM Studio with `json_schema` structured output mode and always returns a parseable `mechanic_spec` with fields `{kind, title, intent, inputs[], outputs[], content{}}` at max 2 nesting levels; schema violations raise before PLAN is called
  2. `mechanic_spec.kind` is always one of the values in the `mechanic.kind` enum from Phase 14 — DISTILL cannot produce an unknown kind
  3. PLAN stage inspects the SPA manifest and emits one of `new_module`, `extend_module`, or `upgrade_state_only`; the decision is logged alongside the manifest at that moment
  4. An email whose content is semantically unrelated to all existing modules results in `new_module` decision, not a forced merge
  5. The raw email body is not present in any object passed from DISTILL stage onward — only `mechanic_spec` crosses the stage boundary
**Plans**: 4 plans
- [x] 16-01-PLAN.md — schemas/ package (Pydantic discriminated union + DISTILL_SCHEMA) + lm_studio.chat_json schema kwarg (DIST-02, PIPE-04)
- [x] 16-02-PLAN.md — distill.py + tests: json_schema structured output, retry-once, DistillFailed (DIST-01, DIST-02, PIPE-03)
- [x] 16-03-PLAN.md — plan.py + tests: cosine similarity routing + LM judge on ambiguous (PLAN-01, PLAN-02)
- [x] 16-04-PLAN.md — orchestrator wiring: v2 branch for DISTILL+PLAN (PIPE-03, PIPE-04)

### Phase 17: BUILD + Validator
**Goal**: A `mechanic_spec` deterministically produces a valid, self-contained Alpine/Tailwind HTML module that passes all validator checks; invalid output triggers an automatic retry that terminates on repeated failure
**Depends on**: Phase 16
**Requirements**: BUILD-01, BUILD-02, BUILD-03, BUILD-04, BUILD-05, VAL-01, VAL-02, VAL-03, VAL-04, VAL-05, VAL-06, VAL-07
**Success Criteria** (what must be TRUE):
  1. `validator.py` is written and all tests pass before `build.py` is written (TDD gate enforced by commit order); the validator is callable without a running LM Studio server
  2. Validator correctly rejects: non-parseable HTML, missing `x-data`, missing event handler, unpinned CDN URLs, stub phrases (TODO/FIXME/placeholder/coming soon/`// implement`/ellipsis-in-code), `x-if` on `<div>`, external fetch/XHR to non-localhost, decoded HTML shorter than 800 bytes
  3. BUILD output uses Alpine.js CDN with `<script defer>` (v3.x pinned URL) and Tailwind Play CDN (v3.4.x pinned URL); validator confirms both tags are present
  4. HTML is returned from the LM as a JSON-escaped string and base64-encoded in Python post-extraction; `finish_reason == "length"` causes an immediate abort with an error, not a silent truncation; `max_tokens` is set to at least 6000
  5. Each of the 5 module kinds has a known-good Alpine v3 exemplar injected into the BUILD prompt; failed validation triggers retry up to `MAX_RETRIES = 3`; retry aborts early if error on attempt N matches error on attempt N-1
**Plans**: 4 plans
- [x] 17-01-PLAN.md — validator.py TDD: test_validator.py (RED) + validate_module implementation (GREEN) (VAL-01..07)
- [x] 17-02-PLAN.md — lm_studio.py extension: add chat_json_with_meta returning (dict, finish_reason) tuple (BUILD-04)
- [x] 17-03-PLAN.md — BUILD_SCHEMA in schemas/json_schema.py + exemplars.py with five kind-specific Alpine/Tailwind constants (BUILD-02, BUILD-05)
- [x] 17-04-PLAN.md — build.py TDD: test_build.py (RED) + build() + BuildFailed implementation (GREEN) (BUILD-01..05, VAL-07)

### Phase 18: INTEGRATE + Orchestrator
**Goal**: Valid modules are written to disk and committed atomically, the orchestrator routes v1/v2 emails to the correct pipeline, and HTTPS-deployed SPAs can reach the LM Studio endpoint via proxy
**Depends on**: Phase 15, Phase 17
**Requirements**: INT-01, INT-02, INT-03, INT-04, INT-05, SPA-05, PIPE-02, SEC-01, SEC-02
**Success Criteria** (what must be TRUE):
  1. `.gitignore` is audited at the start of this phase (before any file writes); `public/spa/` is confirmed to not be excluded from the site git tree — this check is encoded as a startup assertion in integrate.py
  2. A valid module HTML is written atomically to `public/spa/<module_id>/index.html` via staging path + `os.replace`; the matching `spa_manifest.json` update and module file write land in a single git commit whose short hash becomes the module's `version` field
  3. Sending an email to a v1-configured inbox triggers the v1 pipeline unchanged; sending to a v2-configured inbox triggers the 5-stage pipeline — both paths run from the same orchestrator entry point, gated by `pipeline_version` from `config.yaml`
  4. `window.AI()` calls from HTTPS-deployed SPAs route through the Python proxy endpoint in the workflow engine and reach LM Studio; the proxy is not invoked for `http://localhost` serving
  5. Generated modules are served inside `<iframe sandbox="allow-scripts">`; the SPA shell sets a restrictive Content-Security-Policy; `x-html` usage in any generated module is rejected by the validator (enforcing `x-text` only)
**Plans**: 5 plans
- [x] 18-01-PLAN.md — Validator SEC-01: ban x-html directive (TDD)
- [x] 18-02-PLAN.md — integrate.py: atomic write + manifest upsert + git init + startup_assert_gitignore (TDD)
- [x] 18-03-PLAN.md — /api/ai proxy + listener wiring + duplicate handler cleanup
- [x] 18-04-PLAN.md — shell.html: CSP meta + HTTPS-aware window.AI()
- [x] 18-05-PLAN.md — Orchestrator v2 wiring + PIPE-02 verification tests
**UI hint**: yes

### Phase 19: End-to-End + Hardening
**Goal**: The full v2.0 pipeline is verified end-to-end against real LM output, v1 inboxes are confirmed unbroken, and the milestone is closed
**Depends on**: Phase 18
**Requirements**: (coverage phase — validates PIPE-01 through INT-05 in combination; no new requirements)
**Success Criteria** (what must be TRUE):
  1. A single email sent to a v2 inbox travels through all 5 stages (INGEST → DISTILL → PLAN → BUILD → INTEGRATE) and produces a committed, validator-passing module that renders in the SPA shell in a real browser
  2. Sending a rollback trigger (reverting the last git commit) removes the module from the manifest and the SPA shell no longer navigates to it on refresh
  3. An email sent to a v1 inbox produces the same output as it did before v2.0 — no regressions in the v1 pipeline path
  4. All automated tests (validator unit tests, ingest unit tests, integration tests) pass in CI without a running LM Studio server; tests that require LM Studio are clearly marked and skipped in CI
**Plans**: 4 plans
- [x] 19-01-PLAN.md — Test harness (conftest.py + pytest.ini + requires_lm marker) + rollback_module() in integrate.py + jsonschema verify
- [x] 19-02-PLAN.md — test_e2e_pipeline.py: real-LM end-to-end test marked requires_lm (SC1)
- [x] 19-03-PLAN.md — test_browser_smoke.py: Playwright SPA shell smoke test + fixture assets (SC1 browser portion)
- [x] 19-04-PLAN.md — v1 regression gate + VERIFICATION.md + REQUIREMENTS.md close-out + milestone close (SC2/SC3/SC4)

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Server Foundation | v1.0 | 3/3 | Complete | 2026-04-19 |
| 2. Core Form & Config Engine | v1.0 | 6/6 | Complete | 2026-04-19 |
| 3. Hosting Provider & Inbox Manager | v1.0 | 7/7 | Complete | 2026-04-19 |
| 4. Preview, Write & Completion | v1.0 | 3/3 | Complete | 2026-04-19 |
| 5. Architecture Split + Folder Moves | v1.1 | 3/3 | Complete | 2026-04-20 |
| 6. Config Contract Extraction + Migration | v1.1 | 3/3 | Complete | 2026-04-20 |
| 7. Runtime Deploy Adapter Abstraction | v1.1 | 3/3 | Complete | 2026-04-20 |
| 8. Vercel Runtime Deploy Implementation | v1.1 | 3/3 | Complete | 2026-04-20 |
| 9. Multi-Inbox Routing/Deploy Validation | v1.1 | 2/2 | Complete | 2026-04-20 |
| 10. Stepper Indicator UI | v1.1 | 2/2 | Complete | 2026-04-20 |
| 11. End-to-End UAT and Cleanup | v1.1 | 2/2 | Complete | 2026-04-20 |
| 12. Workflow Engine Deployment to Target Server | v1.1 | 3/3 | Complete | 2026-04-20 |
| 13. End-to-End Verification + Milestone Close | v1.1 | 2/2 | Complete | 2026-04-20 |
| 14. Foundation | v2.0 | 3/3 | Complete | 2026-04-20 |
| 15. INGEST | v2.0 | 3/3 | Complete    | 2026-04-20 |
| 16. DISTILL + PLAN | v2.0 | 4/4 | Complete    | 2026-04-21 |
| 17. BUILD + Validator | v2.0 | 4/4 | Complete    | 2026-04-21 |
| 18. INTEGRATE + Orchestrator | v2.0 | 5/5 | Complete    | 2026-04-22 |
| 19. End-to-End + Hardening | v2.0 | 4/4 | Complete | 2026-04-24 |
