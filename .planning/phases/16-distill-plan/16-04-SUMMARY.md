# 16-04 SUMMARY: Orchestrator v2 branch wiring

## What was built

Surgical edit to `apps/workflow_engine/orchestrator.py` + new `test_orchestrator_distill_plan_wiring.py`.

## Key decisions

- Imported as `from . import distill` and `from . import plan as _plan_stage` to avoid collision with the local variable `plan = lm_studio.chat_json(...)` in the v1 path.
- v2 branch inserted immediately after `normalized_input = ingest.ingest(email)` and before the v1 `topic_curator.update_topic()` call.
- Flow: DISTILL → if `DistillFailed`: `_reply_failure` + record `distill_failed` + return. If `spec is None`: record `upgrade_state_only` + return. PLAN → record `v2_planned_{routing}` + return.
- v1 path unchanged — no existing tests broken.
- `InboxConfig.pipeline_version` (already in config_contract as `str = "v1"`) used directly; no SimpleNamespace needed.

## Tests (6 passing)

- `test_v1_inbox_skips_distill_and_plan`
- `test_v2_happy_path_calls_distill_then_plan_in_order`
- `test_v2_informational_skips_plan_records_upgrade_state_only`
- `test_v2_distill_failure_calls_reply_failure_records_distill_failed`
- `test_pipe_03_spec_has_no_body_field`
- `test_v2_happy_path_records_v2_planned_outcome`

## Commit

`a824cb2` feat(16-04): wire distill+plan into orchestrator v2 branch
