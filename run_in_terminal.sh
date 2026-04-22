#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

osascript <<EOF
set projectDir to "$(printf '%s' "$SCRIPT_DIR")"
tell application "Terminal"
    activate
    do script "cd " & quoted form of projectDir & " && ./run.sh"
end tell
EOF
