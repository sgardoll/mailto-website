#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ ! -f "$REPO_ROOT/.venv/bin/activate" ]]; then
  echo "ERROR: .venv not found. Run: python3 -m venv .venv && .venv/bin/pip install -r workflow/requirements.txt" >&2
  exit 1
fi

source "$REPO_ROOT/.venv/bin/activate"

pip install -q -r "$REPO_ROOT/setup/requirements.txt"

cd "$REPO_ROOT"

python -m setup.server

echo ""
echo "Setup complete."
echo "To start the workflow:"
echo "  ./scripts/run-workflow.sh"
