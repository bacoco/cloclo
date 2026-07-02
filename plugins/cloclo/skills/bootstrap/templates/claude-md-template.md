# CLAUDE.md

## What This Is
**{{PROJECT_NAME}}** is {{DESCRIPTION}}. Stack: {{STACK}}.

## Project Structure
```
{{TREE}}
```

## Build & Dev Commands

### {{FRAMEWORK_1}}
```bash
{{COMMANDS}}
```

### {{FRAMEWORK_2}} (if applicable)
```bash
{{COMMANDS}}
```

## Architecture — How Services Connect
```
{{ARCHITECTURE_DIAGRAM}}
```

## Key Patterns
- **{{PATTERN_1}}**: {{DESCRIPTION}}
- **{{PATTERN_2}}**: {{DESCRIPTION}}
- **{{PATTERN_3}}**: {{DESCRIPTION}}

## Core Rules (MANDATORY)

1. **Confidence first** — never modify code without being at least 95% sure. Below that, ask targeted questions.
2. **Read before writing** — always read the existing code (Read/Grep/Glob) before changing it. Never assume the current state.
3. **Act fast, verify immediately** — after every fix, test right away (test, curl, build) and show the output.
4. **Explore before creating** — always Glob/Grep before creating a hook, store, or component. It probably already exists.
5. **Read types before accessing** — check the real interface/type before assuming a field exists.
6. **Commit by checkpoint** — after 3-5 tested changes, commit. Never 10+ uncommitted changes.

## Recurring Errors (MANDATORY)

1. **Explore before creating** — always Glob/Grep before creating. It probably already exists.
2. **Read interfaces before accessing fields** — never assume a field exists; check the real structure.
3. {{STACK_SPECIFIC_ERROR_1}}
4. {{STACK_SPECIFIC_ERROR_2}}

## Session Start (MANDATORY)

At the VERY FIRST message of a session, BEFORE replying to the user:

1. `git log --oneline -5` + `git status --short`
2. `docker ps --format "table {{.Names}}\t{{.Status}}" | head -15` (if Docker; the `{{.Names}}`/`{{.Status}}` are literal Go template tokens, not placeholders)
3. Read `MEMORY.md` for persistent context
4. Summarize in 3-4 lines: "Last work: X. State: Y services up, Z files changed."
5. Propose the most relevant action OR ask "What do we tackle?"

## Secrets & Credentials

Never store credentials in this file (it is tracked in git). Keep dev credentials and API
keys in an untracked `.env.local` at the project root, and ensure `.env.local` is listed in
`.gitignore`. Reference the variable names here if needed, never the values.

---
**Adapt every section to the real project. Sections marked MANDATORY are non-negotiable.**
**The `{{PLACEHOLDER}}` tokens must be replaced with the real values detected in Phase 1.**
**Exception: literal `{{.Names}}` / `{{.Status}}` in docker `--format` strings are Go template syntax — leave them as-is.**
