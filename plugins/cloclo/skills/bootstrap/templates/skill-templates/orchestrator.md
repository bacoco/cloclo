# Orchestrator — Template

## Frontmatter
```yaml
name: orchestrator
description: "Use when you're unsure which skill to run or need routing — reads git/docker/log context and dispatches the right profile. Triggers: /orchestrator, help me, what now, next step, where do I start"
```

## Phase 1 — Read context (10 seconds max)

Run IN PARALLEL:
```bash
git status --short && git diff --stat HEAD
docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null | head -20
git log --oneline -5
```
(The `{{.Names}}`/`{{.Status}}` are literal Go template tokens for docker `--format`, not placeholders — leave them as-is.)

Also: re-read the last few messages of the conversation.

## Phase 2 — Route

| Priority | Detected signal | Profile |
|----------|-----------------|---------|
| 1 | Error, crash, 500, timeout, "bug" | **DEBUGGER** |
| 2 | Services down | **OPS** |
| 3 | "audit", "quality", "check the code" | **AUDITOR** |
| 4 | Files changed + not rebuilt | **DEPLOYER** |
| 5 | Active work on {{DOMAIN_1}} | **{{DEV_1}}** |
| 6 | Active work on {{DOMAIN_2}} | **{{DEV_2}}** |
| 7 | "review", "read over" | **REVIEWER** |
| 8 | "wiki", "history", "decision", "why did we" | **WIKI-QUERY** |
| 9 | "update the docs", "update sources" | **DOC-SYNC** |
| 10 | Session start, nothing specific | **HEALTH-CHECK** |
| 11 | Nothing matches | **ADVISOR** |

Only keep the rows for skills that were actually created during bootstrap.

## Phase 3 — Dispatch

Announce: `"Context: [1-line summary]. Launching profile [NAME]."`
Invoke the matching skill.

If HEALTH-CHECK and all OK: "Everything is up. What do we tackle?"
If ADVISOR: list the 5 most relevant actions.

## Rules
1. **One profile only** — don't combine.
2. **Immediate action** — dispatch directly once the profile is clear.
3. **Short report** — 2-3 lines after dispatch.
