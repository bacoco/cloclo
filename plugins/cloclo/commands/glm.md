---
description: Use the installed GLM companion for tasks, reviews, transfers, resumable jobs, and setup.
argument-hint: "[task|continue|review|adversarial-review|transfer|status|result|cancel|setup] [arguments]"
allowed-tools: Bash(python3:*), Bash(git:*), Read, Grep, Glob
---

# CLoClo GLM compatibility command

Resolve `${CLAUDE_PLUGIN_ROOT}/scripts/run_glm_companion.py` and invoke it with
`python3` as the only runtime bridge. It locates the installed `glm@cloclo`
dependency without assuming its `bin/` directory is globally on `PATH`. Always
pass `--host claude`. Never call Z.AI or `claude -p` directly.

Route `$ARGUMENTS` by intent:

- `setup` → `python3 <bridge> setup --host claude`
- `continue` or `resume` → `python3 <bridge> task --host claude --resume-last`
- `review` → `python3 <bridge> review --host claude --wait`
- `adversarial-review` or `challenge` → `python3 <bridge> adversarial-review --host claude --wait`
- `transfer` → `python3 <bridge> transfer --host claude --wait`
- `status` → `python3 <bridge> status --host claude`
- `result` → `python3 <bridge> result --host claude`
- `cancel` or `stop` → `python3 <bridge> cancel --host claude`
- anything else → `python3 <bridge> task --host claude --wait -- "$ARGUMENTS"`

Add `--write` only for explicit mutation requests. Use `--background` instead
of `--wait` for explicitly asynchronous or long-running work. Preserve the
runtime output, including model fallback and permission diagnostics.

The canonical plugin skill is `/glm:glm`; this command remains a CLoClo
compatibility route under the CLoClo namespace.
