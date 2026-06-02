#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="${LMI_SOURCE_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
OPENCLAW_GLOBAL_DIR="${LMI_OPENCLAW_GLOBAL_DIR:-$HOME/.openclaw/skills/lmi-management-system}"
OPENCLAW_WORKSPACE_MAIN_DIR="${LMI_OPENCLAW_WORKSPACE_MAIN_DIR:-$HOME/.openclaw/workspace-main/skills/lmi-management-system}"
OPENCLAW_WORKSPACE_AZAI_DIR="${LMI_OPENCLAW_WORKSPACE_AZAI_DIR:-$HOME/.openclaw/workspace-azai/skills/lmi-management-system}"
CODEX_DIR="${LMI_CODEX_DIR:-$HOME/.codex/skills/lmi-management-system}"

TMP_ROOT="$(mktemp -d)"
TMP_SOURCE="$TMP_ROOT/source"

cleanup() {
  rm -rf "$TMP_ROOT"
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
    --exclude '.DS_Store' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '*.log' \
    --exclude 'vibecoding-lmi-time-management-blog-draft.md' \
    --exclude 'wechat-lmi-skill-article.md' \
    --exclude 'blog-assets' \
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
    return 1
  fi
}

copy_normalized "$SOURCE_DIR" "$TMP_SOURCE"

STATUS=0

LABELS=(
  "OpenClaw global vs source"
  "OpenClaw workspace-main vs source"
  "OpenClaw workspace-azai vs source"
  "Codex vs source"
)

DIRS=(
  "$OPENCLAW_GLOBAL_DIR"
  "$OPENCLAW_WORKSPACE_MAIN_DIR"
  "$OPENCLAW_WORKSPACE_AZAI_DIR"
  "$CODEX_DIR"
)

for i in "${!LABELS[@]}"; do
  label="${LABELS[$i]}"
  dir="${DIRS[$i]}"
  tmp_target="$TMP_ROOT/target-$i"

  if copy_normalized "$dir" "$tmp_target"; then
    if ! compare_dirs "$label" "$TMP_SOURCE" "$tmp_target"; then
      STATUS=1
    fi
  else
    echo "[MISSING] $label not found: $dir"
    STATUS=1
  fi
done

exit "$STATUS"
