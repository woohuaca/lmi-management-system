#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3)}"
OPENCLAW_BIN="${OPENCLAW_BIN:-$(command -v openclaw)}"
MEMORY_DIR="${MEMORY_DIR:-$HOME/.openclaw/workspace-azai/memory}"
LABEL="com.woohuaca.lmi-focus-reminder"
PLIST_PATH="$HOME/Library/LaunchAgents/${LABEL}.plist"
LOG_DIR="$HOME/.openclaw/logs"
OUT_LOG="$LOG_DIR/lmi-focus-reminder.out.log"
ERR_LOG="$LOG_DIR/lmi-focus-reminder.err.log"

if [[ -z "$PYTHON_BIN" || ! -x "$PYTHON_BIN" ]]; then
  echo "python3 not found" >&2
  exit 1
fi

if [[ -z "$OPENCLAW_BIN" || ! -x "$OPENCLAW_BIN" ]]; then
  echo "openclaw not found; set OPENCLAW_BIN explicitly" >&2
  exit 1
fi

PYTHON_BIN="$(python3 - <<'PY' "$PYTHON_BIN"
import os, sys
print(os.path.realpath(sys.argv[1]))
PY
)"

OPENCLAW_BIN="$(python3 - <<'PY' "$OPENCLAW_BIN"
import os, sys
raw = sys.argv[1]
resolved = os.path.realpath(raw)
suffix = '/lib/node_modules/openclaw/openclaw.mjs'
if '/.local/state/fnm_multishells/' in raw and resolved.endswith(suffix):
    print(resolved[:-len(suffix)] + '/bin/openclaw')
else:
    print(raw if '/bin/openclaw' in raw else resolved)
PY
)"

OPENCLAW_BIN_DIR="$(dirname "$OPENCLAW_BIN")"

mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR"

cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${PYTHON_BIN}</string>
    <string>${REPO_DIR}/scripts/lmi_focus_reminder.py</string>
    <string>--memory-dir</string>
    <string>${MEMORY_DIR}</string>
    <string>--openclaw-bin</string>
    <string>${OPENCLAW_BIN}</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>${OPENCLAW_BIN_DIR}:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>StartInterval</key>
  <integer>60</integer>
  <key>WorkingDirectory</key>
  <string>${REPO_DIR}</string>
  <key>StandardOutPath</key>
  <string>${OUT_LOG}</string>
  <key>StandardErrorPath</key>
  <string>${ERR_LOG}</string>
</dict>
</plist>
PLIST

launchctl bootout "gui/$(id -u)/${LABEL}" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"
launchctl kickstart -k "gui/$(id -u)/${LABEL}"

echo "Installed ${LABEL}"
echo "Plist: $PLIST_PATH"
echo "Out log: $OUT_LOG"
echo "Err log: $ERR_LOG"
