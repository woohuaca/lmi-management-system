#!/usr/bin/env bash

set -euo pipefail

SOURCE_DIR="/Users/woohuaca/Documents/New project/lmi-management-system"
OPENCLAW_DIR="/Users/woohuaca/.openclaw/skills/lmi-management-system"
CODEX_DIR="/Users/woohuaca/.codex/skills/lmi-management-system"

TMP_SOURCE="$(mktemp -d)"
TMP_OPENCLAW="$(mktemp -d)"
TMP_CODEX="$(mktemp -d)"

cleanup() {
  rm -rf "$TMP_SOURCE" "$TMP_OPENCLAW" "$TMP_CODEX"
}
trap cleanup EXIT

copy_normalized() {
  local src="$1"
  local dst="$2"

  if [[ ! -d "$src" ]]; then
    return 1
  fi

  rsync -a \
    --exclude '.git' \
    --exclude '.clawhub' \
    --exclude '_meta.json' \
    "$src/" "$dst/"
}

compare_dirs() {
  local label="$1"
  local left="$2"
  local right="$3"

  if diff -rq "$left" "$right" >/dev/null; then
    echo "[OK] $label is in sync"
  else
    echo "[DIFF] $label has drift"
    diff -rq "$left" "$right" || true
  fi
}

copy_normalized "$SOURCE_DIR" "$TMP_SOURCE"

if copy_normalized "$OPENCLAW_DIR" "$TMP_OPENCLAW"; then
  compare_dirs "OpenClaw vs source" "$TMP_SOURCE" "$TMP_OPENCLAW"
else
  echo "[MISSING] OpenClaw install not found: $OPENCLAW_DIR"
fi

if copy_normalized "$CODEX_DIR" "$TMP_CODEX"; then
  compare_dirs "Codex vs source" "$TMP_SOURCE" "$TMP_CODEX"
else
  echo "[MISSING] Codex install not found: $CODEX_DIR"
fi
