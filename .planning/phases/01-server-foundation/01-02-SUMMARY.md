---
phase: 01-server-foundation
plan: 02
subsystem: infra
tags: [bash, flask, python-dotenv, venv, shell]

# Dependency graph
requires: []
provides:
  - scripts/setup.sh shell entry point with venv activation, pip install, and wizard delegation
  - setup/requirements.txt with flask>=3.1.0 and python-dotenv>=1.0.0
affects: [01-server-foundation, setup-wizard]

# Tech tracking
tech-stack:
  added: [flask>=3.1.0, python-dotenv>=1.0.0]
  patterns: [shell-script uses REPO_ROOT from $0 not $PWD, venv guard before activation]

key-files:
  created:
    - scripts/setup.sh
    - setup/requirements.txt
  modified: []

key-decisions:
  - "REPO_ROOT derived from $0 (script location) not $PWD to prevent PATH injection (T-02-02)"
  - "Explicit .venv existence check with clear error message before any action (T-02-03)"
  - "PyYAML excluded from setup/requirements.txt — already available via workflow/requirements.txt"

patterns-established:
  - "Shell scripts: #!/usr/bin/env bash + set -euo pipefail + REPO_ROOT from dirname $0"
  - "Venv guard pattern: check .venv/bin/activate exists, print actionable error and exit 1 if not"

requirements-completed: [SRV-01]

# Metrics
duration: 1min
completed: 2026-04-19
---

# Phase 1 Plan 02: Shell Entry Point and Wizard Requirements

**Bash entry point scripts/setup.sh with venv guard, silent pip install of flask and python-dotenv, and delegation to python -m setup.server**

## Performance

- **Duration:** 1 min
- **Started:** 2026-04-19T05:01:42Z
- **Completed:** 2026-04-19T05:02:55Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- setup/requirements.txt created with exactly flask>=3.1.0 and python-dotenv>=1.0.0 (no extras)
- scripts/setup.sh created: guards against missing .venv, activates it, installs wizard deps, runs python -m setup.server, prints next-step instruction
- Threat mitigations T-02-02 (REPO_ROOT from $0) and T-02-03 (.venv guard) applied as required by threat model

## Task Commits

Each task was committed atomically:

1. **Task 1: Create setup/requirements.txt with wizard dependencies** - `dc303ea` (feat)
2. **Task 2: Create scripts/setup.sh entry point** - `353450d` (feat)

**Plan metadata:** (committed after this file)

## Files Created/Modified
- `setup/requirements.txt` - Wizard pip dependencies: flask>=3.1.0, python-dotenv>=1.0.0
- `scripts/setup.sh` - Shell entry point: venv guard, pip install -q, cd REPO_ROOT, python -m setup.server, post-exit echo

## Decisions Made
- REPO_ROOT computed from `$(dirname "$0")` rather than `$PWD` to prevent PATH-based elevation of privilege (T-02-02 mitigation)
- Guard checks `.venv/bin/activate` existence before activation; prints actionable error pointing at the exact commands to fix it (T-02-03 mitigation)
- PyYAML intentionally absent from setup/requirements.txt — it ships in workflow/requirements.txt and will already be in the venv

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- scripts/setup.sh is the single command entry point for SRV-01; delegates to python -m setup.server which is the subject of Plan 01 (Flask server) and Plans 03+ (wizard routes)
- setup/requirements.txt ready for pip install in the shell wrapper

---
*Phase: 01-server-foundation*
*Completed: 2026-04-19*
