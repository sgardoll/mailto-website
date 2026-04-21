---
phase: 17-build-validator
plan: "02"
subsystem: lm_studio
tags: [lm_studio, chat_json, finish_reason, build_validator]
dependency_graph:
  requires: []
  provides: [chat_json_with_meta]
  affects: [apps/workflow_engine/build.py]
tech_stack:
  added: []
  patterns: [parallel-function, zero-blast-radius]
key_files:
  modified:
    - apps/workflow_engine/lm_studio.py
decisions:
  - "Added chat_json_with_meta as a parallel function rather than modifying chat_json to preserve zero blast radius"
  - "finish_reason extracted after all try/except branching so both normal and fallback paths are covered"
  - "None finish_reason normalised to 'stop' so build.py check == 'length' cannot be tripped by None"
metrics:
  duration: "5m"
  completed: "2026-04-22"
---

# Phase 17 Plan 02: chat_json_with_meta Summary

**One-liner:** Added `chat_json_with_meta` to lm_studio.py — same body as `chat_json` but returns `(dict, finish_reason)` tuple so build.py can detect truncated output via `finish_reason == "length"`.

## What Was Done

Single surgical addition: `chat_json_with_meta` inserted between `chat_json` and `_parse_json_lenient` in `apps/workflow_engine/lm_studio.py`. The function is byte-for-byte identical to `chat_json` except:

- Function name: `chat_json_with_meta`
- Return annotation: `tuple[dict[str, Any], str]`
- Docstring updated
- Final lines extract `finish_reason` after all branching, then return `(_parse_json_lenient(text), finish_reason)`

`chat_json` was not modified.

## Verification

| Check | Result |
|-------|--------|
| `grep -n "def chat_json_with_meta"` | Line 143 found |
| `grep -n "def chat_json"` | Line 91 (original, unchanged) |
| Return annotation via `inspect.signature` | `tuple[dict[str, Any], str]` |
| test_distill.py + test_plan.py | 21 passed |

## Deviations from Plan

None — plan executed exactly as written.

## Threat Mitigations Applied

- T-17-02-01: `finish_reason or "stop"` normalises None to "stop"
- T-17-02-02: Zero changes to `chat_json`; all existing tests pass green

## Self-Check: PASSED

- `apps/workflow_engine/lm_studio.py` modified and committed at `0b4ced6`
- Both `chat_json` (line 91) and `chat_json_with_meta` (line 143) present
- 21 tests pass
