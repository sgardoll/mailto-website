---
phase: 15-ingest
plan: "03"
subsystem: workflow_engine
tags: [ingest, orchestrator, wiring, tdd]
dependency_graph:
  requires: [15-02]
  provides: [orchestrator-ingest-wiring]
  affects: [apps/workflow_engine/orchestrator.py]
tech_stack:
  added: []
  patterns: [monkeypatch-call-ordering, caplog-assertion]
key_files:
  created:
    - apps/workflow_engine/tests/test_orchestrator_ingest_wiring.py
  modified:
    - apps/workflow_engine/orchestrator.py
decisions:
  - "ingest.ingest(email) placed INSIDE try: block so exceptions propagate to existing except Exception handler (plan diff showed it outside — corrected to satisfy must_have truth T-15-09)"
metrics:
  duration: "~8 minutes"
  completed: "2026-04-21"
  tasks_completed: 1
  files_changed: 2
---

# Phase 15 Plan 03: Orchestrator Ingest Wiring Summary

**One-liner:** Wired `ingest.ingest(email)` into `orchestrator._process_locked` inside the existing `try` block, logging `source_type`/`source_url` at INFO before `topic_curator.update_topic`.

## What Was Built

- `apps/workflow_engine/orchestrator.py`: surgical edit — 1 import line modified (added `ingest` alphabetically between `git_ops` and `lm_studio`), 3 lines inserted at top of `_process_locked`'s `try:` block.
- `apps/workflow_engine/tests/test_orchestrator_ingest_wiring.py`: 3 wiring tests (TDD RED→GREEN).

## Exact Lines Added/Removed to orchestrator.py

```diff
-from . import apply_changes, build_and_deploy, git_ops, lm_studio, notify, prompt, site_bootstrap, site_index, topic_curator
+from . import apply_changes, build_and_deploy, git_ops, ingest, lm_studio, notify, prompt, site_bootstrap, site_index, topic_curator

     try:
+        normalized_input = ingest.ingest(email)
+        log.info("ingest source_type=%s source_url=%s",
+                 normalized_input["source_type"], normalized_input["source_url"])
+
         new_topic = topic_curator.update_topic(
```

Net change: 5 insertions, 1 deletion.

## Test-Pass Summary

| Suite | Tests | Result |
|-------|-------|--------|
| test_orchestrator_ingest_wiring.py | 3 | PASSED |
| test_ingest.py (Plan 02 regression) | 12 | PASSED |
| **Total** | **15** | **15 passed** |

## normalized_input Not Yet Consumed Downstream

`normalized_input` is assigned and logged only. It is NOT passed to:
- `topic_curator.update_topic` (still receives `email=email`)
- `prompt.synthesis_prompt_user` (still receives `idx, email`)
- `apply_changes.apply` (unchanged)

Consumer wiring is scheduled for Phases 16-18.

## STRIDE Mitigation Evidence

| Threat | Mitigation | Evidence |
|--------|------------|----------|
| T-15-09: ingest() raises, blocks email processing | `ingest.ingest()` is inside the existing `try:` block; `except Exception` at line 107 catches, records `outcome="error"` | `test_ingest_exception_propagates_to_error_outcome` — PASSED |
| T-15-10: source_url leaks to logs | Accepted — source URL already present in email body which flows through standard logging | No test needed (accept disposition) |
| T-15-11: out-of-order call breaks Phase 16+ contract | `test_ingest_called_before_topic_curator` asserts call ordering via parent Mock | PASSED — `names.index("ingest") < names.index("topic")` |

## Phase 15 Completion Statement

All Phase 15 requirement IDs now have landing artifacts:

| Req ID | Plan | Artifact |
|--------|------|---------|
| ING-01 | 15-03 | `orchestrator._process_locked` calls `ingest.ingest(email)` |
| ING-02 | 15-02 | `ingest._handle_video` with yt-dlp + pywhispercpp |
| ING-03 | 15-02 | `ingest._handle_article` with trafilatura + readability |
| ING-04 | 15-02 | Graceful degradation via `_HAS_YTDLP`, `_HAS_WHISPER`, `_HAS_ARTICLE` guards |
| CONF-02 | 15-01 | `pipeline_version` field in `InboxConfig` |

## Commits

| Phase | Hash | Message |
|-------|------|---------|
| RED | e7917b3 | test(15-03): add failing wiring test for orchestrator→ingest call |
| GREEN | 85ee0a5 | feat(15-03): wire ingest() into orchestrator._process_locked |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ingest call placed inside try block instead of outside**
- **Found during:** GREEN phase — test_ingest_exception_propagates_to_error_outcome failed
- **Issue:** The plan's `<interfaces>` after-edit diff showed `normalized_input = ingest.ingest(email)` inserted BETWEEN `idx = site_index.build(...)` and `try:` — i.e., outside the try block. The must_have truth T-15-09 says "exception raised from ingest() propagates... caught by existing `except Exception` at line 103". These are contradictory: outside the try block, the exception propagates out of `_process_locked` entirely without being caught.
- **Fix:** Inserted `ingest.ingest()` call and log at the TOP of the existing `try:` block instead of before it. This satisfies T-15-09, the test, and preserves the call-ordering invariant (ingest before topic_curator).
- **Files modified:** apps/workflow_engine/orchestrator.py
- **Commit:** 85ee0a5

## Known Stubs

None — `ingest.ingest()` is wired to the live module from Plan 02 with no stubs.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes beyond what the plan's threat model covers.

## Self-Check: PASSED

- [x] `apps/workflow_engine/tests/test_orchestrator_ingest_wiring.py` — exists
- [x] `apps/workflow_engine/orchestrator.py` — modified
- [x] RED commit e7917b3 — verified in git log
- [x] GREEN commit 85ee0a5 — verified in git log
- [x] All 15 tests pass
- [x] `normalized_input` not passed to any downstream function
