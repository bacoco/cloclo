#!/usr/bin/env bash
# CLoClo PostToolUse hook — remind about visual verification after UI file edits
# Fires on Edit/Write tools. Checks if the modified file is a UI file.
# If yes, injects a reminder to verify with agent-browser.

# No set -e: hooks must never crash
set -o pipefail 2>/dev/null || true

INPUT=$(cat)

# Extract file path from tool input
FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
tool_input = data.get('tool_input', {})
if isinstance(tool_input, dict):
    print(tool_input.get('file_path', ''))
" 2>/dev/null || echo "")

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# Check if it's a UI file
if echo "$FILE_PATH" | grep -qE '\.(tsx|jsx|vue|svelte|html|css|scss)$'; then
  REMINDER="CLoClo: UI file modified ($FILE_PATH). After you're done with this change, verify visually with agent-browser: open the page, take a screenshot, verify it looks correct."
  REMINDER_ESCAPED=$(echo "$REMINDER" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))" 2>/dev/null)
  printf '{"additionalContext":%s}\n' "$REMINDER_ESCAPED"
fi
