#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ ! -f "$REPO_ROOT/.venv/bin/activate" ]]; then
  echo "ERROR: .venv not found. Run: python3 -m venv .venv && .venv/bin/pip install -r apps/workflow_engine/requirements.txt" >&2
  exit 1
fi

source "$REPO_ROOT/.venv/bin/activate"

pip install -q -r "$REPO_ROOT/apps/setup_wizard/requirements.txt"

cd "$REPO_ROOT"

python -m apps.setup_wizard.server

echo ""
echo "Setup complete."
echo "To start the workflow:"
echo "  ./scripts/run-workflow.sh"
