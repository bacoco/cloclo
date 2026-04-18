---
description: Run a GLM-5.1 code review on current changes via Z.ai Anthropic-compatible endpoint. Standalone, outside the /pipeline flow.
argument-hint: "[committed|uncommitted|all] [base-ref]"
allowed-tools: Bash(claude *), Bash(git *), Bash(grep *), Read, Write
---

# /glm — Standalone GLM-5.1 Review

Run a GLM-5.1 review on the current repo. Uses the installed `claude` CLI with
three environment variables overridden so the calls land on Z.ai instead of
Anthropic. Useful before opening a PR, after a quick fix, or to sanity-check
work without entering the full pipeline.

**Open bar.** The user has unlimited z.ai quota. Run this as often as you want.

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
   for var in ZAI_API_KEY GLM_API_KEY LLM_API_KEY_EXCENIA; do
     val="${!var:-}"
     [ -n "$val" ] && GLM_KEY="$val" && break
   done
   if [ -z "$GLM_KEY" ] && [ -f "$(git rev-parse --show-toplevel 2>/dev/null)/infra/.env" ]; then
     GLM_KEY=$(grep -E '^LLM_API_KEY_EXCENIA=' "$(git rev-parse --show-toplevel)/infra/.env" | cut -d= -f2-)
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
   ```

5. **Build the prompt:** a short code-review brief + the diff.

   ```bash
   PROMPT_FILE="/tmp/glm-review-$(date +%s).md"
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
   echo "GLM-5.1 is reviewing... (this takes 2-8 minutes)"
   ANTHROPIC_BASE_URL="https://api.z.ai/api/anthropic" \
   ANTHROPIC_AUTH_TOKEN="$GLM_KEY" \
   ANTHROPIC_DEFAULT_OPUS_MODEL="glm-5.1" \
   ANTHROPIC_DEFAULT_SONNET_MODEL="glm-5.1" \
   claude -p --permission-mode acceptEdits "$(cat "$PROMPT_FILE")"
   rm -f "$PROMPT_FILE"
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
- **Open bar quota.** Re-run this as often as needed — z.ai is unlimited for this user.
