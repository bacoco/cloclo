# Task — Template

## Frontmatter
```yaml
name: task
description: "Use when executing a single numbered task with tight scope and no refactoring drift. Triggers: /task"
```

## Input
`/task N — description`

## Workflow
1. **Read the task** — understand what is asked.
2. **Explore the relevant files** — max 5 reads before starting.
3. **Implement** — minimal, focused code.
4. **Verify** — type-check, tests, imports.
5. **Commit** — `feat(task-N): <description>`

## Constraints
- Do NOT create new files unless absolutely necessary.
- Do NOT refactor surrounding code.
- Do NOT add docstrings to unmodified code.
- Stay focused on the task — no scope creep.
