#!/usr/bin/env bash
# Foreground runner. Loads .env if present, then runs the IMAP IDLE listener.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  set -o allexport
  # shellcheck disable=SC1091
  source .env
  set +o allexport
fi

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  ./.venv/bin/pip install --upgrade pip
  ./.venv/bin/pip install -r apps/workflow_engine/requirements.txt
fi

exec ./.venv/bin/python -m apps.workflow_engine.listener "$@"
