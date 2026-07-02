---
name: toggle
description: "Use when the user asks to pause, resume, or check CLoClo (cloclo off/on/status)."
---

# CLoClo Toggle

Parse the user's message to determine the action:

- **off / pause / desactive** → Disable CLoClo
- **on / resume / reactive** → Enable CLoClo
- **status** (or no argument) → Report current state

The kill-switch is a single file, `.cloclo-disabled`, at the **project root** — resolved
the same way the hooks resolve it, so a toggle run from any subdirectory targets the same
file the hooks check. Anchor every command with this exact expression:

```bash
STATE="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}/.cloclo-disabled"
```

## Off

```bash
STATE="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}/.cloclo-disabled"
touch "$STATE"
```

Confirm:

```
CLoClo paused for this project. Hooks are silent, and /pipeline and /wiki ingest will
warn before proceeding (they check .cloclo-disabled at Step 0). Your wiki and skills are
otherwise untouched.

Note: .cloclo-disabled is LOCAL to this project (per-project, not global). Consider adding
it to .gitignore — committing it would disable CLoClo for every collaborator.
To resume: cloclo on
```

## On

```bash
STATE="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}/.cloclo-disabled"
rm -f "$STATE"
```

Confirm:

```
CLoClo active. Hooks resumed, and /pipeline and /wiki no longer warn.
```

## Status

```bash
ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
if [ -f "$ROOT/.cloclo-disabled" ]; then echo "PAUSED: $ROOT"; else echo "ACTIVE: $ROOT"; fi
```

Report:

```
CLoClo is [ACTIVE|PAUSED] for project <resolved project root>.
```

## Scope (be honest about what "off" does)

- **Hooks are always gated** on `.cloclo-disabled` — when paused they stay silent.
- **/pipeline and /wiki** check the same file at Step 0 and warn before proceeding. This is
  the intended contract; if a given skill hasn't wired it up yet, the hook gating above
  still holds regardless.

## Rules

1. Execute immediately. No confirmation needed.
2. One line of output. Don't explain what hooks do.
3. If the file already exists (off when already off), just confirm the current state.
