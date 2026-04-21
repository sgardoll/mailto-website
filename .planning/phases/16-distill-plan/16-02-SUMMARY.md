# 16-02 SUMMARY: distill.py + test_distill.py

## What was built

`apps/workflow_engine/distill.py` — DISTILL stage converting `normalized_input` to `MechanicSpec` via LM Studio structured output.

## Key decisions

- `chat_json()` called with `schema=DISTILL_SCHEMA` to get jsonschema-validated structured output from the LM.
- Single retry loop on validation failure (jsonschema, Pydantic, or ValueError); raises `DistillFailed` after two failures.
- Returns `None` for informational emails (mechanic=null in LM response) — D-13/D-17 path.
- `source_url` propagated from `normalized_input` if the LM omits it.
- `module_id` auto-slugified from `title` if blank.
- `_slugify` capped at 64 chars, falls back to "module" for empty result.

## Tests (11 passing)

- `test_happy_path_returns_mechanic_spec`
- `test_informational_email_returns_none`
- `test_retry_success_calls_chat_json_twice`
- `test_retry_failure_raises_distill_failed`
- `test_kind_content_mismatch_triggers_retry_then_fails`
- `test_source_url_preserved_from_normalized_input`
- `test_module_id_auto_generated_from_title`
- `test_module_id_respected_when_provided`
- `test_schema_kwarg_passed_to_chat_json`
- `test_spec_has_no_raw_body_fields`
- `test_slugify_special_characters`

## Commit

`d1a8f66` feat(16-02): implement distill.py + tests — DISTILL stage with retry and DistillFailed
