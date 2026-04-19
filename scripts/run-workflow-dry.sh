#!/usr/bin/env bash
# Same as run-workflow.sh but adds --dry-run and --once for safe testing.
set -euo pipefail
exec "$(dirname "$0")/run-workflow.sh" --once --dry-run "$@"
