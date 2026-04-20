---
phase: 15-ingest
plan: "02"
subsystem: workflow_engine
tags: [ingest, tdd, content-extraction, video, article, normalization]
dependency_graph:
  requires: []
  provides: [apps/workflow_engine/ingest.py, apps/workflow_engine/tests/test_ingest.py]
  affects: [apps/workflow_engine/orchestrator.py]
tech_stack:
  added: [yt-dlp, pywhispercpp, trafilatura, readability-lxml]
  patterns: [guarded-import, shutil.which-preflight, tempdir-finally-cleanup, monkeypatch-module-attrs]
key_files:
  created:
    - apps/workflow_engine/ingest.py
    - apps/workflow_engine/tests/__init__.py
    - apps/workflow_engine/tests/test_ingest.py
  modified: []
decisions:
  - _HAS_ARTICLE guard moved into _extract_article (not _handle_article) so tests can monkeypatch _extract_article without also patching _HAS_ARTICLE
  - test assertion r.message % r.args replaced with r.getMessage() — the plan template used string-format syntax that fails when r.args contains a list
metrics:
  duration: 178s
  completed: "2026-04-20"
  tasks_completed: 2
  files_created: 3
---

# Phase 15 Plan 02: INGEST Module Summary

**One-liner:** `ingest(email) -> normalized_input` with plain-text/video/article paths, guarded imports, and tempdir cleanup — all externals mocked in 12 passing tests.

## Tasks Completed

| Task | Type | Commit | Status |
|------|------|--------|--------|
| 1: Create tests/__init__.py and failing tests | RED | cc9898f | Done |
| 2: Implement apps/workflow_engine/ingest.py | GREEN | 20b5a06 | Done |

## Test Results

- **12 passed / 0 failed / 0 errored**
- All externals mocked (no network, no yt-dlp/pywhispercpp/trafilatura installed at test time)
- Test coverage: plain-text passthrough, sender key mapping, subject exclusion, empty body, multi-URL warning, video with tools present, video ffmpeg absent, video whisper absent, transcription failure, tempdir cleanup on exception, article success, article extraction None fallback

## File Sizes

```
169  apps/workflow_engine/ingest.py
145  apps/workflow_engine/tests/test_ingest.py
  0  apps/workflow_engine/tests/__init__.py
314  total
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing functionality] _HAS_ARTICLE guard placement**
- **Found during:** Task 2 GREEN phase (2 tests failing)
- **Issue:** Plan spec placed `if not _HAS_ARTICLE` guard in `_handle_article()`. Since trafilatura is not installed in the dev environment, this made the guard fire before `_extract_article` was ever called — meaning tests that monkeypatched `_extract_article` still returned plain text.
- **Fix:** Moved the `_HAS_ARTICLE` guard into `_extract_article()` instead. When the test monkeypatches `_extract_article`, the patched function runs directly without hitting the guard. The behavior contract is preserved: absent tools still degrade gracefully.
- **Files modified:** `apps/workflow_engine/ingest.py`
- **Commit:** 20b5a06

**2. [Rule 1 - Bug] Test assertion TypeError in test_multiple_urls_first_wins_warning_logged**
- **Found during:** Task 2 GREEN phase (1 test failing after fix #1)
- **Issue:** The plan template assertion `r.message % r.args if r.args else r.getMessage()` raised `TypeError: not all arguments converted during string formatting` when `r.args` contains a list (the skipped URLs list). Python's `%` string formatting treats a tuple as positional args but a single list arg `(['url'],)` doesn't match `%s` cleanly.
- **Fix:** Replaced with `r.getMessage()` which is the correct stdlib method for formatting a log record's message. Assertion intent is unchanged — still checks that the second URL appears in the log output.
- **Files modified:** `apps/workflow_engine/tests/test_ingest.py`
- **Commit:** 20b5a06

## STRIDE Threat Mitigations

### T-15-03: Shell injection via URL (Tampering)

```
$ grep -n 'subprocess\|shell=' apps/workflow_engine/ingest.py
(no output)
```

No subprocess calls in ingest.py. yt-dlp is invoked via Python API with URL as a list argument — zero shell interpolation.

### T-15-06: Tempdir not cleaned on exception (Information Disclosure)

```
$ grep -n 'ignore_errors=True' apps/workflow_engine/ingest.py
105:        shutil.rmtree(tmpdir, ignore_errors=True)
```

`finally` block guarantees cleanup even when `_download_audio` or `_transcribe` raises. Covered by `test_video_tempdir_cleaned_even_on_exception`.

### T-15-05: Malicious audio crashes pywhispercpp (DoS)

`_transcribe` wrapped in `try/except Exception` → `log.warning(...)` → `transcript = ""`. Covered by `test_video_transcription_failure_returns_empty_body`.

### T-15-08: Tempdir reuse across concurrent invocations (Repudiation)

`tempfile.mkdtemp()` returns a unique directory per call (POSIX guarantee). No cross-invocation aliasing.

## TDD Gate Compliance

```
20b5a06 feat(15-02): implement ingest() module with video/article/text paths  <- GREEN
cc9898f test(15-02): add failing tests for ingest module                       <- RED
```

RED gate: tests failed with `ImportError: cannot import name 'ingest'`
GREEN gate: all 12 tests pass after implementation

## Known Stubs

None. All code paths are fully implemented. The optional third-party libraries (yt-dlp, pywhispercpp, trafilatura, readability-lxml) degrade gracefully when absent but the implementations are complete and wired correctly.

## Threat Flags

None. No new network endpoints, auth paths, or trust boundaries introduced beyond what is documented in the plan's threat model.

## Self-Check: PASSED

- [x] `apps/workflow_engine/ingest.py` exists (169 lines)
- [x] `apps/workflow_engine/tests/__init__.py` exists (empty package marker)
- [x] `apps/workflow_engine/tests/test_ingest.py` exists (145 lines, 12 test functions)
- [x] RED commit cc9898f exists in git log
- [x] GREEN commit 20b5a06 exists in git log
- [x] 12 passed, 0 failed
