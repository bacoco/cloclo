---
description: Run a CodeRabbit CLI review on current changes (committed or uncommitted) — standalone, outside the /pipeline flow
argument-hint: "[committed|uncommitted|all] [base-ref]"
allowed-tools: Bash(coderabbit:*), Bash(git:*), Read
---

# /coderabbit — Standalone CodeRabbit Review

Run CodeRabbit CLI directly on the current repo. Useful before opening a PR,
after a quick fix, or to sanity-check work without entering the full pipeline.

## Arguments

- `$1` (type, optional) — one of `committed`, `uncommitted`, `all`. Default: `all`.
- `$2` (base-ref, optional) — git base for comparison when type=`committed`. Default: `main`.

Examples:
- `/coderabbit` → review ALL local changes (default)
- `/coderabbit committed` → review committed changes on current branch vs `main`
- `/coderabbit committed HEAD~5` → review last 5 commits
- `/coderabbit uncommitted` → review only working-tree changes (staged + unstaged)

## Execution Steps

1. **Verify CodeRabbit CLI available.** Install/auth requirements are documented
   once in the `coderabbit-review` skill (§2 Prerequisites) — do not duplicate
   them here. Just gate on presence:
   ```bash
   command -v coderabbit >/dev/null || {
     echo "CodeRabbit CLI not found. See the coderabbit-review skill §2 for install + auth."
     exit 1
   }
   ```

2. **Parse arguments from $ARGUMENTS:**
   - Word 1 → `$TYPE` (default `all`, validate against `committed|uncommitted|all`)
   - Word 2 → `$BASE` (default `main`, only used when type=`committed`)

3. **Show context to user** — one line: which repo, which type, which base.

4. **Run CodeRabbit** (foreground, 30-90 seconds typical):

   ```bash
   cd "$(git rev-parse --show-toplevel)"
   # < /dev/null: coderabbit's default mode is interactive and can hang on
   #   inherited stdin / auth prompts. timeout 600 caps a wedged run.
   # --plain: standalone human-readable output (no session files, no --agent).
   if [ "$TYPE" = "committed" ]; then
     # $BASE may be a branch (main) or a ref (HEAD~5). Resolve to a SHA and use
     # --base-commit (--base takes a branch name only). rev-parse handles both.
     BASE_SHA=$(git rev-parse "$BASE") || { echo "Invalid base ref: $BASE"; exit 1; }
     timeout 600 coderabbit review --plain --type committed --base-commit "$BASE_SHA" < /dev/null
   elif [ "$TYPE" = "uncommitted" ]; then
     timeout 600 coderabbit review --plain --type uncommitted < /dev/null
   else
     timeout 600 coderabbit review --plain --type all < /dev/null
   fi
   ```

5. **Read and summarize findings.** Present:
   - Total findings count by severity (high / medium / low / nit)
   - Top 3-5 highest-severity items with file:line
   - If zero high/medium findings: say so plainly ("Clean — 0 high, 0 medium; N nits/lows")

6. **Offer next steps** — short and optional:
   - "Corrige les findings high/medium" → apply fixes
   - "Ignore et continue"
   - "Relance avec --type uncommitted" (or autre variante)

## Important Rules

- **Do NOT use `/pipeline`.** This command is standalone. No session dir, no session files, no phase tracking, no auto-integration.
- **Do NOT auto-fix.** Show findings first; user decides.
- **Foreground only.** No background, no polling.
- **Plain-text output** (`--plain`), not `--agent`. The user sees the review directly; structured parsing not needed for standalone use.
- **Never dismiss nits silently.** If only nits were found, still report the count — the user may care.
- **Do NOT summarize and hide details.** If the full output is short enough, show it verbatim after your 3-line summary.
