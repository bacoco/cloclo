#!/usr/bin/env bash
# CLoClo PostToolUse hook — remind to update the wiki after git commits.
# Fires on Bash tool calls whose command contains "git commit".
# Lightweight: injects a text nudge only, never runs a real wiki operation.
#
# Input: PostToolUse JSON on stdin (fields read via jq: .cwd, .tool_input.command).
# Requires: jq. If jq is missing we exit 0 silently — a hook must never crash a session.

# No set -e: hooks must never exit non-zero
set -o pipefail 2>/dev/null || true

INPUT=$(cat)

# jq is a hard dependency for JSON parsing; degrade to a silent no-op if absent.
command -v jq >/dev/null 2>&1 || exit 0

# Cheap pre-filter: avoid spawning jq on every Bash call unless the raw input
# even mentions "git commit". Substring match on the whole JSON blob is fine here.
case "$INPUT" in
  *'git commit'*) ;;
  *) exit 0 ;;
esac

# Resolve the project root (robust to a subdirectory cwd).
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(jq -r '.cwd // empty' <<<"$INPUT" 2>/dev/null)}"
PROJECT_DIR="${PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

# Kill switch anchored at the project root, not cwd.
[ -f "$PROJECT_DIR/.cloclo-disabled" ] && exit 0

# Extract the actual command and confirm it is a git commit (not just any string
# that happened to contain the words elsewhere in the payload).
COMMAND=$(jq -r '.tool_input.command // empty' <<<"$INPUT" 2>/dev/null)
case "$COMMAND" in
  *"git commit"*) ;;
  *) exit 0 ;;
esac

# Only nudge when a wiki actually exists at the project root.
[ -f "$PROJECT_DIR/wiki/schema.md" ] || exit 0

REMINDER="CLoClo: Commit detected. If this was a significant change, update relevant wiki pages (entities, concepts, decisions)."
printf '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":%s}}\n' \
  "$(jq -n --arg m "$REMINDER" '$m')"
exit 0
