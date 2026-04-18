---
description: Run a CodeRabbit CLI review on current changes (committed or uncommitted) — standalone, outside the /pipeline flow
argument-hint: "[committed|uncommitted|all] [base-ref]"
allowed-tools: Bash(coderabbit *), Bash(git *), Read
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

1. **Verify CodeRabbit CLI available.** If missing, tell the user to install:
   ```bash
   command -v coderabbit || {
     echo "CodeRabbit CLI not found. Install:"
     echo "  curl -fsSL https://cli.coderabbit.ai/install.sh | sh"
     echo "  coderabbit auth login"
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
   if [ "$TYPE" = "committed" ]; then
     coderabbit review --plain --type committed --base "$BASE"
   elif [ "$TYPE" = "uncommitted" ]; then
     coderabbit review --plain --type uncommitted
   else
     coderabbit review --plain --type all
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

- **Do NOT use `/pipeline`.** This command is standalone. No session dir, no decision point files, no phase tracking.
- **Do NOT auto-fix.** Show findings first; user decides.
- **Foreground only.** No background, no polling.
- **Plain-text output** (`--plain`), not `--agent`. The user sees the review directly; structured parsing not needed for standalone use.
- **Never dismiss nits silently.** If only nits were found, still report the count — the user may care.
- **Do NOT summarize and hide details.** If the full output is short enough, show it verbatim after your 3-line summary.
