#!/usr/bin/env bash
# Installs a launchd agent so the listener auto-starts on login (macOS).
set -euo pipefail
cd "$(dirname "$0")/.."
REPO_ROOT="$(pwd)"
LABEL="com.thoughts-to-platform.email-ai"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
mkdir -p "$HOME/Library/LaunchAgents"
cat >"$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>WorkingDirectory</key><string>$REPO_ROOT</string>
  <key>ProgramArguments</key>
    <array>
      <string>$REPO_ROOT/scripts/run-workflow.sh</string>
    </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$REPO_ROOT/runtime/state/launchd.out.log</string>
  <key>StandardErrorPath</key><string>$REPO_ROOT/runtime/state/launchd.err.log</string>
</dict></plist>
EOF
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load -w "$PLIST"
echo "Loaded $LABEL"
echo "Tail logs with: tail -f $REPO_ROOT/runtime/state/launchd.err.log"
