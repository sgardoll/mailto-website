#!/usr/bin/env bash
# Sync template chrome (layouts/ + pages/) from packages/site-template into
# every per-inbox runtime site. Skips src/content/ — that's LM-owned and
# must never be clobbered.
#
# Why this exists: site_bootstrap.ensure_site() is intentionally one-shot
# (it returns existing dirs unchanged). That preserves curated content but
# means fixes to the template's chrome never propagate to sites that
# already exist. Run this after any layouts/ or pages/ change.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TEMPLATE="$REPO_ROOT/packages/site-template"
SITES_ROOT="$REPO_ROOT/runtime/sites"

if [[ ! -d "$SITES_ROOT" ]]; then
  echo "no $SITES_ROOT — nothing to sync"
  exit 0
fi

shopt -s nullglob
synced=0
for site in "$SITES_ROOT"/*/; do
  slug=$(basename "$site")
  for sub in layouts pages; do
    src="$TEMPLATE/src/$sub"
    dst="$site/src/$sub"
    [[ -d "$src" ]] || continue
    mkdir -p "$dst"
    rsync -a --delete "$src/" "$dst/"
  done
  echo "synced chrome -> $slug"
  synced=$((synced + 1))
done

echo "done ($synced site(s) updated)"
