---
phase: 15-ingest
plan: "01"
subsystem: workflow-engine
tags: [dependencies, requirements, conf-02, ingest, v2.0]
dependency_graph:
  requires: []
  provides: [apps/workflow_engine/requirements.txt with v2.0 pip deps]
  affects: [apps/workflow_engine/ingest.py, apps/workflow_engine/orchestrator.py, Phase 16-18 pipeline modules]
tech_stack:
  added: [yt-dlp>=2026.3.17, pywhispercpp>=1.4.1, trafilatura>=2.0.0, readability-lxml>=0.8.4.1, sentence-transformers, faiss-cpu, gitpython, jsonschema]
  patterns: [requirements.txt append — no-pin style for Phase 16-18 supporting deps]
key_files:
  modified: [apps/workflow_engine/requirements.txt]
decisions:
  - "Pinned yt-dlp/pywhispercpp/trafilatura/readability-lxml with >= constraints; left sentence-transformers/faiss-cpu/gitpython/jsonschema unpinned per CONTEXT.md locked decision"
metrics:
  duration: 47s
  completed: "2026-04-20T15:16:47Z"
  tasks_completed: 1
  tasks_total: 1
  files_changed: 1
---

# Phase 15 Plan 01: Append v2.0 pip dependencies to requirements.txt Summary

Appended 8 pip dependencies (yt-dlp, pywhispercpp, trafilatura, readability-lxml, sentence-transformers, faiss-cpu, gitpython, jsonschema) to `apps/workflow_engine/requirements.txt`, satisfying CONF-02 so Phase 15-18 pipeline modules can import without error.

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Append v2.0 pip dependencies to requirements.txt | 242dece | apps/workflow_engine/requirements.txt |

## Lines Added (verbatim)

```
yt-dlp>=2026.3.17
pywhispercpp>=1.4.1
trafilatura>=2.0.0
readability-lxml>=0.8.4.1
sentence-transformers
faiss-cpu
gitpython
jsonschema
```

## Verification Output

```
wc -l apps/workflow_engine/requirements.txt → 14
grep -c '^' apps/workflow_engine/requirements.txt → 14
```

All 6 original entries preserved unchanged. All 8 new entries present in the specified order. No blank lines. `>=` constraints used where versions specified; no pins for the four Phase 16-18 supporting deps.

## Deviations from Plan

None — plan executed exactly as written. Version specifiers match 15-RESEARCH.md "Standard Stack" table (verified against PyPI 2026-04-20). No reordering of existing entries.

## Threat Flags

None. The two threats in the plan's threat register (T-15-01 PyPI supply chain, T-15-02 unversioned deps) are both accepted per plan — no new surface introduced beyond what was planned.

## Self-Check: PASSED

- FOUND: apps/workflow_engine/requirements.txt
- FOUND: commit 242dece
- FOUND: .planning/phases/15-ingest/15-01-SUMMARY.md
