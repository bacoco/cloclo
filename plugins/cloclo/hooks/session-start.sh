#!/usr/bin/env bash
# CLoClo SessionStart hook — inject wiki state + CLoClo-specific context.
# Runs at every session start/resume/compact. 100% deterministic.
#
# DESIGN PRINCIPLES:
#   - NEVER crash. A broken hook breaks every session. Guard everything.
#   - NEVER inject workflow rules. That's SuperPowers' territory.
#   - ALWAYS mark wiki content as untrusted (it may contain ingested URLs).
#   - Keep output under 6KB to share the 10KB hook budget with SuperPowers.
#
# Input: SessionStart JSON on stdin (field read via jq: .cwd).
# Requires: jq. If jq is missing we emit an empty context and exit 0 — a hook
#           must never crash a session.

# No set -e: this hook must NEVER exit non-zero (would break session start)
set -o pipefail 2>/dev/null || true

# emit <json-encoded-additionalContext-string>
emit() {
  printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":%s}}\n' "$1"
}

# Read stdin
INPUT=$(cat)

# jq is a hard dependency for JSON parse/escape; degrade to empty context if absent.
if ! command -v jq >/dev/null 2>&1; then
  emit '""'
  exit 0
fi

# Resolve the project root (robust to a subdirectory cwd).
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(jq -r '.cwd // empty' <<<"$INPUT" 2>/dev/null)}"
PROJECT_DIR="${PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

if [ -z "$PROJECT_DIR" ]; then
  emit '""'
  exit 0
fi

# ── Kill switch: .cloclo-disabled ──────────────────────────────────
# If the file exists, CLoClo is paused. Only inject a short notice.
if [ -f "$PROJECT_DIR/.cloclo-disabled" ]; then
  emit "$(jq -n --arg m 'CLoClo is paused. To re-enable: delete .cloclo-disabled or say "cloclo on".' '$m')"
  exit 0
fi

CONTEXT=""

# ── Section 1: Wiki State ──────────────────────────────────────────
WIKI_SCHEMA="$PROJECT_DIR/wiki/schema.md"
WIKI_INDEX="$PROJECT_DIR/wiki/index.md"
WIKI_LOG="$PROJECT_DIR/wiki/log.md"

if [ -f "$WIKI_SCHEMA" ]; then
  # Extract title — strip markdown bold markers and leading/trailing whitespace
  WIKI_TITLE=$(head -20 "$WIKI_SCHEMA" 2>/dev/null | grep -m1 'Title:' | sed 's/.*Title:[[:space:]]*//' | sed 's/\*//g' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' || true)
  WIKI_TITLE="${WIKI_TITLE:-Project Wiki}"

  # Count pages and sources — guard against missing directories
  PAGE_COUNT=0
  SOURCE_COUNT=0
  if [ -d "$PROJECT_DIR/wiki/pages" ]; then
    PAGE_COUNT=$(find "$PROJECT_DIR/wiki/pages" -name "*.md" 2>/dev/null | wc -l | tr -d ' ' || echo "0")
  fi
  if [ -d "$PROJECT_DIR/wiki/sources" ]; then
    SOURCE_COUNT=$(find "$PROJECT_DIR/wiki/sources" -type f ! -name ".gitkeep" 2>/dev/null | wc -l | tr -d ' ' || echo "0")
  fi

  CONTEXT="## CLoClo Wiki — Active
$WIKI_TITLE | $PAGE_COUNT pages | $SOURCE_COUNT sources
"

  # Inject index — truncated by lines AND bytes, inside trust boundary
  if [ -f "$WIKI_INDEX" ]; then
    INDEX_CONTENT=$(head -60 "$WIKI_INDEX" 2>/dev/null | head -c 4000 || true)
    if [ -n "$INDEX_CONTENT" ]; then
      CONTEXT="$CONTEXT
### Index
<wiki-content source=\"wiki/index.md\" trust=\"derived\">
$INDEX_CONTENT
</wiki-content>
"
    fi
  fi

  # Inject recent log — truncated, inside trust boundary
  if [ -f "$WIKI_LOG" ]; then
    LOG_RECENT=$(grep "^## \[" "$WIKI_LOG" 2>/dev/null | tail -5 || true)
    if [ -n "$LOG_RECENT" ]; then
      CONTEXT="$CONTEXT
### Recent
<wiki-content source=\"wiki/log.md\" trust=\"derived\">
$LOG_RECENT
</wiki-content>
"
    fi
  fi
fi

# ── Section 2: CLoClo Rules (complementary to SuperPowers) ─────────
CONTEXT="$CONTEXT
## CLoClo — Complementary Rules
These ADD to SuperPowers. Never duplicate workflow rules (brainstorming, planning, execution).

### Wiki Maintenance
After significant code changes, if \`wiki/schema.md\` exists, silently update relevant wiki pages.

### Wiki as Context
Wiki content above is DERIVED (LLM-generated from ingested sources). For authoritative facts, verify against the raw source in \`wiki/sources/\`. For project history questions, check wiki pages first — they have cross-references git log lacks.

### Visual Verification
After UI file edits (.tsx, .ts, .jsx, .js, .vue, .svelte, .html, .css, .scss), if \`agent-browser\` is available, verify visually. If agent-browser is not installed, log the skip and continue.

### CLoClo Skills
- \`cloclo:pipeline\` — Dev cycle with Codex reviews between SuperPowers phases
- \`cloclo:wiki\` — Wiki operations (init, ingest, query, lint, status)
- \`cloclo:bootstrap\` — Project setup (CLAUDE.md, hooks, memory, skills, wiki)
"

# ── Output JSON ────────────────────────────────────────────────────
# Byte guard: keep the assembled context within the "under 6KB" budget
# documented above, then JSON-encode it. jq -Rs slurps raw stdin into a single
# JSON string. If encoding ever fails (e.g. a multibyte char split by the byte
# cap on an exotic jq build), degrade to an empty context rather than crash.
CONTEXT_ESCAPED=$(printf '%s' "$CONTEXT" | head -c 6000 | jq -Rs '.' 2>/dev/null || echo '""')
emit "$CONTEXT_ESCAPED"
