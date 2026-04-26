#!/usr/bin/env bash
# Foreground runner. Loads .env if present, then runs the IMAP IDLE listener.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  ./.venv/bin/pip install --upgrade pip
  ./.venv/bin/pip install -r apps/workflow_engine/requirements.txt
fi

exec ./.venv/bin/python -c 'import os, runpy, sys
from pathlib import Path
from dotenv import dotenv_values
env_path = Path(".env")
if env_path.exists():
    for key, value in dotenv_values(env_path).items():
        if value is not None:
            os.environ[key] = value
sys.argv = ["apps.workflow_engine.listener", *sys.argv[1:]]
runpy.run_module("apps.workflow_engine.listener", run_name="__main__")
' "$@"
