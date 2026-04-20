---
phase: 14-foundation
plan: "03"
subsystem: workflow_engine
tags: [profile-bootstrap, gitignore, state, v2.0, foundation]
dependency_graph:
  requires: []
  provides: [PROF-01, PROF-02]
  affects: [runtime/state/<slug>/profile.json, apps/workflow_engine/site_bootstrap.py, .gitignore]
tech_stack:
  added: []
  patterns: [idempotent-file-bootstrap, gitignore-defence-in-depth]
key_files:
  created: []
  modified:
    - apps/workflow_engine/site_bootstrap.py
    - .gitignore
decisions:
  - "profile.json is written to STATE_DIR/inbox.slug/ (runtime/state/<slug>/), not inside the site tree (runtime/sites/<slug>/), ensuring PROF-02 structural separation"
  - "Write is gated by if not profile_path.exists() — even force=True site re-bootstrap does not clobber existing user state"
  - "json.dumps used instead of f-string templating (unlike the existing .inbox.json wart) for correctness"
metrics:
  duration: "5m"
  completed: "2026-04-20"
  tasks_completed: 2
  tasks_total: 2
requirements: [PROF-01, PROF-02]
---

# Phase 14 Plan 03: Profile.json Bootstrap Summary

**One-liner:** Idempotent profile.json bootstrap written to runtime/state/<slug>/ on first ensure_site() call, excluded from git via explicit .gitignore rule.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Extend ensure_site() to write idempotent profile.json | 695cf7f | apps/workflow_engine/site_bootstrap.py |
| 2 | Add profile.json exclusion to .gitignore | 06e4f64 | .gitignore |

## Diff Summary

### apps/workflow_engine/site_bootstrap.py (+13 lines, -1 line)

Three precise edits:

1. Added `import json` (alphabetically before `shutil`)
2. Added `STATE_DIR` to the `.config` import line (alphabetically between `SITES_DIR` and `TEMPLATE_DIR`)
3. Inserted profile.json bootstrap block after the `.inbox.json` write:
   - `profile_dir = STATE_DIR / inbox.slug` — writes outside site tree
   - `profile_dir.mkdir(parents=True, exist_ok=True)` — creates state dir on first use
   - `if not profile_path.exists():` — idempotency guard
   - `json.dumps({"schema_version": "1", "inbox_slug": inbox.slug, "state": {}}, indent=2)`
   - `log.info(...)` — write is observable in logs

### .gitignore (+1 line)

Inserted `runtime/state/**/profile.json` after `runtime/state/siteground.key` and before `/runtime`, keeping fine-grained rules adjacent to each other.

## Idempotency Verification

Test confirmed three behaviors:
1. First call: `profile.json` created with correct schema at `STATE_DIR/demo/profile.json`
2. Second call (no force): existing `profile.json` with mutated state `{"k": "v"}` was NOT overwritten
3. Third call (`force=True`): site directory removed and re-created, but `profile.json` preserved (lives outside site tree)

All three assertions passed. Full smoke test: `Phase 14-03 smoke PASS`.

## git check-ignore Output

```
.gitignore:35:/runtime    runtime/state/demo/profile.json
```

The `/runtime` umbrella rule (line 35) catches `runtime/state/demo/profile.json`. The explicit `runtime/state/**/profile.json` rule (line 34) provides defence-in-depth documentation of intent per PROF-02.

## Deviations from Plan

None — plan executed exactly as written.

## Threat Model Coverage

All four threats from the plan's threat register were addressed:

| Threat ID | Disposition | Outcome |
|-----------|-------------|---------|
| T-14-03-01 | accept | Slug from trusted operator config; pathlib / operator used; flagged for Phase 15 if untrusted provisioning added |
| T-14-03-02 | mitigate | Three layers: explicit rule + /runtime umbrella + structural separation. git check-ignore verified. |
| T-14-03-03 | mitigate | `if not profile_path.exists()` guard + log.info emission. Idempotency test proves non-destructive re-runs. |
| T-14-03-04 | accept | PermissionError from Path.mkdir/write_text is same class as existing .inbox.json failure — no new surface. |

## Self-Check

- [x] `apps/workflow_engine/site_bootstrap.py` exists and contains all required edits
- [x] `.gitignore` contains `runtime/state/**/profile.json` at correct position
- [x] Commit 695cf7f exists (Task 1)
- [x] Commit 06e4f64 exists (Task 2)
- [x] Verification tests passed (idempotency + smoke)
- [x] git check-ignore exits 0 for runtime/state/demo/profile.json

## Self-Check: PASSED
