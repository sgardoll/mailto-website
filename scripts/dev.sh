#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  ./.venv/bin/pip install --upgrade pip
  ./.venv/bin/pip install -r apps/workflow_engine/requirements.txt
  ./.venv/bin/pip install -r apps/setup_wizard/requirements.txt
fi

exec ./.venv/bin/python -m apps.setup_wizard.server
