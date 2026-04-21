# 16-03 SUMMARY: plan.py + test_plan.py

## What was built

`apps/workflow_engine/plan.py` — PLAN stage routing `MechanicSpec` to one of `new_module`, `extend_module`, or `upgrade_state_only`.

## Key decisions

- Reads `public/spa/spa_manifest.json`; if absent or empty modules list → `new_module` immediately (no model load).
- Sentence-transformers model (`all-MiniLM-L6-v2`) is lazy-loaded on first use via `_get_model()`, `_MODEL = None` at module level.
- Cosine similarity thresholds: >0.85 → `extend_module`, <0.40 → `new_module`, [0.40, 0.85] → LM judge.
- Boundaries (exactly 0.85 or 0.40) fall into the ambiguous range and trigger the LM judge.
- LM judge uses `chat_json()` without a schema (returns `{"decision": ..., "rationale": ...}`); unknown decisions fall back to `new_module` with a warning.
- `manifest_snapshot` (module_id/title/kind only) logged at INFO alongside decision and rationale — no raw email body in judge prompt.

## Tests (10 passing)

- `test_no_manifest_file_returns_new_module`
- `test_empty_modules_returns_new_module`
- `test_high_similarity_returns_extend_module`
- `test_low_similarity_returns_new_module`
- `test_ambiguous_triggers_judge`
- `test_judge_unknown_decision_defaults_new_module`
- `test_judge_receives_no_raw_body`
- `test_rationale_logged_with_snapshot`
- `test_threshold_boundary_085_triggers_judge`
- `test_threshold_boundary_040_triggers_judge`

## Commit

`c017aee` feat(16-03): implement plan.py + tests — cosine routing with LM judge fallback
