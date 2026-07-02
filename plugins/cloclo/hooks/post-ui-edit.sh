#!/usr/bin/env bash
# CLoClo PostToolUse hook — remind about visual verification after UI file edits.
# Fires on Edit/Write tools; only when the edited file is a UI file.
# Injects a TEXT reminder only — it NEVER spawns agent-browser (no child
# processes are launched here, so there is nothing to leak).
#
# Input: PostToolUse JSON on stdin (fields read via jq: .cwd, .tool_input.file_path).
# Requires: jq. If jq is missing we exit 0 silently — a hook must never crash a session.

# No set -e: hooks must never exit non-zero
set -o pipefail 2>/dev/null || true

INPUT=$(cat)

# jq is a hard dependency for JSON parsing; degrade to a silent no-op if absent.
command -v jq >/dev/null 2>&1 || exit 0

# Resolve the project root (robust to a subdirectory cwd).
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(jq -r '.cwd // empty' <<<"$INPUT" 2>/dev/null)}"
PROJECT_DIR="${PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

# Kill switch anchored at the project root, not cwd.
[ -f "$PROJECT_DIR/.cloclo-disabled" ] && exit 0

FILE_PATH=$(jq -r '.tool_input.file_path // empty' <<<"$INPUT" 2>/dev/null)
[ -n "$FILE_PATH" ] || exit 0

# Canonical UI extension list — kept in sync with session-start.sh rule text:
#   .tsx .ts .jsx .js .vue .svelte .html .css .scss
case "$FILE_PATH" in
  *.tsx|*.ts|*.jsx|*.js|*.vue|*.svelte|*.html|*.css|*.scss)
    REMINDER="CLoClo: UI file modified ($FILE_PATH). After you're done with this change, verify visually with agent-browser: open the page, take a screenshot, verify it looks correct."
    printf '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":%s}}\n' \
      "$(jq -n --arg m "$REMINDER" '$m')"
    ;;
esac
exit 0
