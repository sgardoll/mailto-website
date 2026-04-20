#!/usr/bin/env bash
# Installs a systemd --user service so the listener auto-starts on login (Linux).
set -euo pipefail
cd "$(dirname "$0")/.."
REPO_ROOT="$(pwd)"
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
mkdir -p "$UNIT_DIR"
UNIT="$UNIT_DIR/mailto-website.service"
cat >"$UNIT" <<EOF
[Unit]
Description=mailto.website email-AI workflow listener
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$REPO_ROOT
ExecStart=$REPO_ROOT/scripts/run-workflow.sh
Restart=on-failure
RestartSec=5
EnvironmentFile=-$REPO_ROOT/.env

[Install]
WantedBy=default.target
EOF
echo "Wrote $UNIT"
systemctl --user daemon-reload
systemctl --user enable --now mailto-website.service
echo "Started. Tail logs with: journalctl --user -u mailto-website -f"
