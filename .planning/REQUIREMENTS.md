# Requirements: v2.0 Interactive SPA Pipeline

## Pipeline Architecture

- [ ] **PIPE-01**: User's email is processed through a 5-stage pipeline: INGEST → DISTILL → PLAN → BUILD → INTEGRATE
- [x] **PIPE-02**: Pipeline version (`v1`/`v2`) is selectable per-inbox via `config.yaml`; v1 remains the default
- [x] **PIPE-03**: Each stage receives only its predecessor's structured output — raw email body never reaches DISTILL or beyond
- [x] **PIPE-04**: Three sequential LM calls per email (DISTILL, PLAN, BUILD) use the single LM Studio server

## INGEST

- [x] **ING-01**: Email body, subject, and sender are normalized into a structured `normalized_input` payload
- [x] **ING-02**: Video URLs in email are downloaded via yt-dlp and transcribed via whisper.cpp (subprocess with `Popen` + stderr drain to avoid M4 deadlock)
- [x] **ING-03**: Article URLs are extracted via trafilatura with readability-lxml fallback
- [x] **ING-04**: Pipeline starts and falls back to plain email text when yt-dlp / ffmpeg / whisper-cli are absent (`shutil.which()` pre-flight)

## DISTILL

- [x] **DIST-01**: Email content is distilled into a `mechanic_spec` JSON object via LM Studio `json_schema` structured output (constrained decoding, not prompt-only JSON)
- [x] **DIST-02**: `mechanic_spec` schema: `{kind, title, intent, inputs[], outputs[], content{}}` — max 2 nesting levels
- [ ] **DIST-03**: `mechanic.kind` enum (wizard, calculator, drill, scorer, generator) is defined in `packages/config_contract/` as the shared source of truth for DISTILL, BUILD, and the validator

## PLAN

- [x] **PLAN-01**: PLAN stage decides `new_module` vs. `extend_module` vs. `upgrade_state_only` given the SPA manifest and new `mechanic_spec`
- [x] **PLAN-02**: Emails semantically unrelated to existing modules trigger a new SPA rather than a forced merge

## BUILD

- [x] **BUILD-01**: `mechanic_spec` drives generation of a self-contained HTML/JS module via LM Studio
- [x] **BUILD-02**: Generated module uses Alpine.js CDN (`<script defer>`, v3.x pinned) + Tailwind Play CDN (v3.4.x pinned)
- [x] **BUILD-03**: HTML is returned as a JSON-escaped string field; base64 encoding is applied in Python post-extraction (never inside the model response)
- [x] **BUILD-04**: BUILD stage sets `max_tokens ≥ 6000` and aborts with error if `finish_reason == "length"`
- [x] **BUILD-05**: BUILD prompt includes a known-good Alpine v3 exemplar per module kind (one per kind, five total)

## Validator

- [x] **VAL-01**: Validator checks HTML is parseable, `x-data` is present, and at least one `@click`/`x-on:` handler exists
- [x] **VAL-02**: Validator confirms Alpine + Tailwind CDN `<script>` tags use pinned URLs
- [x] **VAL-03**: Validator rejects stub phrases: TODO, FIXME, placeholder, coming soon, `// implement`, ellipsis-in-code
- [x] **VAL-04**: Validator asserts `x-if` only appears on `<template>` elements, never on `<div>`
- [x] **VAL-05**: Validator rejects external `fetch`/XHR calls to non-localhost origins
- [x] **VAL-06**: Validator rejects decoded HTML shorter than 800 bytes
- [x] **VAL-07**: Failed validation triggers retry up to `MAX_RETRIES = 3`; aborts if retry N produces the same error as N-1

## INTEGRATE

- [x] **INT-01**: Valid module HTML is written atomically to `public/spa/<module_id>/index.html` via staging path + `os.replace`
- [x] **INT-02**: `spa_manifest.json` is updated and committed to the site git repo alongside the module file; implemented as two sequential commits (module first, then manifest with the module's commit SHA as version) to resolve the INT-02/INT-03 circularity — a file cannot contain the SHA of its own commit
- [x] **INT-03**: Module version field in manifest = git short hash of that commit
- [x] **INT-04**: `.gitignore` is audited before first INTEGRATE run; `public/spa/` must not be excluded
- [x] **INT-05**: Existing Astro build + deploy flow is unchanged for v1 inboxes

## SPA Shell

- [ ] **SPA-01**: SPA shell provides hash-based module navigation populated from `spa_manifest.json`
- [ ] **SPA-02**: SPA shell injects `window.STATE` proxy (localStorage-backed) before module scripts load
- [ ] **SPA-03**: SPA shell provides `window.AI()` bridge to the LM Studio OpenAI-compatible endpoint
- [ ] **SPA-04**: Each module renders inside `<iframe sandbox="allow-scripts">` for Alpine scope isolation
- [x] **SPA-05**: `window.AI()` routes through a thin Python proxy endpoint in the workflow engine for HTTPS-deployed SPAs

## Per-Inbox Profile

- [ ] **PROF-01**: `profile.json` (`{schema_version, inbox_slug, state{}}`) is created in `runtime/state/<slug>/` at site bootstrap
- [ ] **PROF-02**: `profile.json` is not committed with the site git tree

## Security

- [x] **SEC-01**: `x-html` directive is banned in generated modules; validator enforces `x-text` only for LLM-inserted content
- [x] **SEC-02**: Generated modules are served in sandboxed iframes; SPA shell sets a restrictive Content-Security-Policy

## Config & Dependencies

- [ ] **CONF-01**: `pipeline_version` flag added to `packages/config_contract/`; v1 is the default; both pipeline paths coexist
- [x] **CONF-02**: New pip deps added to `apps/workflow_engine/requirements.txt`: yt-dlp, pywhispercpp, trafilatura, sentence-transformers, faiss-cpu, gitpython, jsonschema

---

## Future Requirements (deferred)

- comparator, matcher kinds — validate model reliability with target model first
- Rollback UI — `git revert` + redeploy is the v2.0 path
- tracker, sandbox, simulator, evaluator, decision_matrix, prompt_lab kinds — later milestone
- Vector RAG with imperative-verb filtering for long articles — INGEST enhancement for v2.x

## Out of Scope

- window.ai Chrome built-in (behind flags, English-only, not suitable for code generation)
- LangChain, ChromaDB, Celery, React — no new infrastructure beyond pip deps listed above
- Per-stage LM temperature tuning — single temperature (0.4); revisit only if output quality testing demands it
- Drag-and-drop interactions in modules — outside reliable 14B generation capability

---

## Traceability

| REQ-ID | Phase |
|--------|-------|
| PIPE-01 | Phase 14 |
| PIPE-02 | Phase 18 |
| PIPE-03 | Phase 16 |
| PIPE-04 | Phase 16 |
| ING-01 | Phase 15 |
| ING-02 | Phase 15 |
| ING-03 | Phase 15 |
| ING-04 | Phase 15 |
| DIST-01 | Phase 16 |
| DIST-02 | Phase 16 |
| DIST-03 | Phase 14 |
| PLAN-01 | Phase 16 |
| PLAN-02 | Phase 16 |
| BUILD-01 | Phase 17 |
| BUILD-02 | Phase 17 |
| BUILD-03 | Phase 17 |
| BUILD-04 | Phase 17 |
| BUILD-05 | Phase 17 |
| VAL-01 | Phase 17 |
| VAL-02 | Phase 17 |
| VAL-03 | Phase 17 |
| VAL-04 | Phase 17 |
| VAL-05 | Phase 17 |
| VAL-06 | Phase 17 |
| VAL-07 | Phase 17 |
| INT-01 | Phase 18 |
| INT-02 | Phase 18 |
| INT-03 | Phase 18 |
| INT-04 | Phase 18 |
| INT-05 | Phase 18 |
| SPA-01 | Phase 14 |
| SPA-02 | Phase 14 |
| SPA-03 | Phase 14 |
| SPA-04 | Phase 14 |
| SPA-05 | Phase 18 |
| PROF-01 | Phase 14 |
| PROF-02 | Phase 14 |
| SEC-01 | Phase 18 |
| SEC-02 | Phase 18 |
| CONF-01 | Phase 14 |
| CONF-02 | Phase 15 |
