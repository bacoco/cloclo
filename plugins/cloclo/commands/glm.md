---
description: Run a GLM-5.2 code review on current changes via Z.ai Anthropic-compatible endpoint. Standalone, outside the /pipeline flow.
argument-hint: "[committed|uncommitted|all] [base-ref]"
allowed-tools: Bash(claude:*), Bash(git:*), Bash(grep:*), Read
---

# /glm — Standalone GLM-5.2 Review

Run a GLM-5.2 review on the current repo. Uses the installed `claude` CLI with
three environment variables overridden so the calls land on Z.ai instead of
Anthropic. Useful before opening a PR, after a quick fix, or to sanity-check
work without entering the full pipeline.

**Cost:** Z.ai is metered — each review spends tokens. Run it when a GLM opinion is
worth the cost.

## Arguments

- `$1` (type, optional) — one of `committed`, `uncommitted`, `all`. Default: `all`.
- `$2` (base-ref, optional) — git base for comparison when type=`committed`. Default: `main`.

Examples:
- `/glm` → review ALL local changes
- `/glm committed` → review committed changes on current branch vs `main`
- `/glm committed HEAD~5` → review last 5 commits
- `/glm uncommitted` → review only working-tree changes

## Execution Steps

1. **Resolve the z.ai API key** (first match wins):

   ```bash
   GLM_KEY=""
   for var in ZAI_API_KEY GLM_API_KEY; do
     val="${!var:-}"
     [ -n "$val" ] && GLM_KEY="$val" && break
   done
   # Project-local fallback: read ZAI_API_KEY / GLM_API_KEY from a .env at the repo root.
   if [ -z "$GLM_KEY" ]; then
     ENV_FILE="$(git rev-parse --show-toplevel 2>/dev/null)/.env"
     [ -f "$ENV_FILE" ] && GLM_KEY=$(grep -E '^(ZAI_API_KEY|GLM_API_KEY)=' "$ENV_FILE" | head -n1 | cut -d= -f2-)
   fi
   [ -z "$GLM_KEY" ] && {
     echo "No Z.ai API key found. Set ZAI_API_KEY or GLM_API_KEY and retry."
     exit 1
   }
   ```

2. **Verify `claude` CLI is installed:**

   ```bash
   command -v claude &>/dev/null || {
     echo "claude CLI not installed — install via https://claude.com/claude-code"
     exit 1
   }
   ```

3. **Parse arguments from $ARGUMENTS:**
   - Word 1 → `$TYPE` (default `all`, validate against `committed|uncommitted|all`)
   - Word 2 → `$BASE` (default `main`, only used when type=`committed`)

4. **Compute the diff to review:**

   ```bash
   cd "$(git rev-parse --show-toplevel)"
   case "$TYPE" in
     committed)   DIFF=$(git diff "$BASE"..HEAD) ;;
     uncommitted) DIFF=$(git diff HEAD) ;;
     all|*)       DIFF=$(git diff "$BASE"..HEAD; git diff HEAD) ;;
   esac

   # Cap the inlined diff so a huge changeset can't blow past the model's context
   # (or bloat argv). Beyond the cap, tell GLM to read the repo for the rest.
   DIFF_MAX=200000   # ~200 KB
   if [ "${#DIFF}" -gt "$DIFF_MAX" ]; then
     DIFF="${DIFF:0:$DIFF_MAX}

[... diff truncated at ${DIFF_MAX} bytes — inspect the remaining files directly with git in the repo ...]"
   fi
   ```

5. **Build the prompt:** a short code-review brief + the diff.

   ```bash
   PROMPT_FILE="/tmp/glm-review-$(date +%s).md"
   # The prompt file holds the diff — clean it up even on interrupt.
   trap 'rm -f "$PROMPT_FILE"' EXIT
   cat > "$PROMPT_FILE" <<EOF
   Tu es un reviewer senior. Analyse le diff ci-dessous et produis une review
   structuree : verdict global, puis findings par severite (P0/P1/P2) avec
   file:line. Sois exhaustif, concret, pas de langue de bois.

   ## Diff a reviewer

   \`\`\`diff
   $DIFF
   \`\`\`

   Format de sortie :
   - Verdict: PASS | CONCERNS | FAIL
   - Findings:
     - [P0|P1|P2] [TOOL|CODE|LLM-JUDGMENT] file:line — description courte
   - Suggestions concretes si CONCERNS/FAIL
   EOF
   ```

6. **Invoke `claude` with GLM env vars** (foreground, 2-8 min):

   ```bash
   echo "GLM-5.2 is reviewing... (this takes 2-8 minutes)"
   # This command only prints the review to stdout — no file writes, so no
   # acceptEdits. Read-only tools let GLM pull extra context if needed. `< /dev/null`
   # closes stdin so a non-interactive child can't hang; `timeout 900` caps it.
   ANTHROPIC_BASE_URL="https://api.z.ai/api/anthropic" \
   ANTHROPIC_AUTH_TOKEN="$GLM_KEY" \
   ANTHROPIC_DEFAULT_OPUS_MODEL="glm-5.2" \
   ANTHROPIC_DEFAULT_SONNET_MODEL="glm-5.2" \
   ANTHROPIC_DEFAULT_HAIKU_MODEL="glm-5.2" \
   timeout 900 claude -p \
     --allowedTools 'Read Grep Glob Bash(git diff:*) Bash(git log:*) Bash(git show:*)' \
     "$(cat "$PROMPT_FILE")" \
     < /dev/null
   # $PROMPT_FILE is removed by the EXIT trap set in step 5.
   ```

7. **Show findings verbatim** to the user. Do NOT summarize or filter.

8. **Offer next steps** (short):
   - "Corrige les findings P0/P1" → apply fixes
   - "Ignore et continue"
   - "Relance sur un diff different (uncommitted / branche X)"

## Important Rules

- **Do NOT use `/pipeline`.** This command is standalone. No session dir, no phase tracking.
- **Do NOT touch `~/.claude/settings.json`.** The GLM env vars MUST stay scoped to the single `claude -p` subprocess. The parent Claude Code session keeps its real Anthropic auth.
- **Do NOT auto-fix.** Show findings; user decides.
- **Foreground only.** No background, no polling.
- **Never echo the API key.** Env var is scoped; don't print it to stdout or logs.
- **Cost-aware.** Z.ai is metered — each review spends tokens. Re-run only when a fresh GLM pass is worth it.
