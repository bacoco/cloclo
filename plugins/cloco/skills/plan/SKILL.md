---
name: plan
description: "Phase 3 of the dev pipeline: convert an approved spec into a detailed implementation plan with file-by-file tasks, complete code blocks, and pre-written commit messages."
user-invocable: false
---

# Plan — Implementation Plan Generation

## Overview

Convert an approved spec into a task-by-task implementation plan. Every task is self-contained, every code block is complete, every file path is verified. The plan targets an agentic worker (the execute skill) that has zero prior context.

**Announce at start:** "Generating implementation plan from spec."

## Inputs

The pipeline orchestrator passes:
- `session_dir`: path to the pipeline session directory (e.g., `docs/cloco-sessions/<id>/`)
- `spec_path`: path to the approved spec (`01-spec.md` or `03-spec-v2.md`)

## Pre-Planning: Scope Check

1. **Read the spec completely.** Do not skim.
2. **Read ALL source files referenced in the spec** using Grep, Read, and Glob. Verify they exist.
3. **Flag missing files immediately.** If the spec references a file that does not exist, stop and report — do not guess contents.
4. **Check scope.** If the spec would produce more than 15 tasks, suggest splitting into multiple plans (one per subsystem). Each plan must produce working, testable software on its own.

## File Structure Table

Before defining tasks, map every file that will be created or modified. This locks in decomposition decisions.

- One clear responsibility per file. Files that change together should live together.
- Follow established patterns in the codebase. Do not restructure unless the spec calls for it.
- Prefer smaller, focused files. Reason: the execute skill handles one task at a time.

## Plan Document

Write to `{session_dir}/04-plan.md` with this exact structure:

````markdown
# [Feature Name] Implementation Plan

> **For agentic workers:** Use the execute skill to implement this plan task-by-task.

**Goal:** [One sentence]
**Spec:** [Path to spec file]
**Tech Stack:** [Key technologies/libraries]

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `exact/path/to/file.ext` | Create | What this file handles |
| `exact/path/to/other.ext` | Modify | What changes and why |

---

### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/new-file.ext`
- Modify: `exact/path/to/existing.ext:line_start-line_end`

- [ ] **Step 1: [Action]**

```language
// Complete code — never a placeholder
```

- [ ] **Step 2: Verify**

Run: `exact command`
Expected: `exact output or behavior`

- [ ] **Step 3: Commit**

```bash
git add exact/path/to/file.ext
git commit -m "type(scope): description"
```

---

## Execution Order

Tasks that touch non-overlapping files can run in parallel:
- Group 1 (parallel): Task 1, Task 3 [different files, no dependencies]
- Group 2 (sequential after Group 1): Task 2 [depends on Task 1 output]
````

## Task Granularity Rules

- Each task = 2-5 minutes of implementation work.
- Every code block is **COMPLETE**. No TBD, no TODO, no placeholders, no "add validation here".
- Every task is **SELF-CONTAINED**. A developer reading only that task must have everything needed.
- **Never reference another task's code.** "Similar to Task X" is forbidden — repeat the code.
- Every task has a **verify step**: test command, typecheck, curl, or syntax check.
- Every task has a **pre-written commit message** following conventional commits (`feat`, `fix`, `refactor`, `test`, `docs`).

## No Placeholders

These are plan failures. Never write them:
- "TBD", "TODO", "implement later", "fill in details"
- "Add appropriate error handling" / "add validation" / "handle edge cases"
- "Write tests for the above" (without actual test code)
- "Similar to Task N" (repeat the code — tasks are read independently)
- Steps that describe what to do without showing how
- References to types, functions, or methods not defined in any task

## Anti-Patterns

- DO NOT assume file content. Always Read before referencing line numbers.
- DO NOT create two tasks that modify the same file. Split differently or merge them.
- DO NOT group unrelated changes in one task.
- DO NOT write vague tasks ("add error handling") without exact code.
- DO NOT skip the verify step for any task.

## Self-Review Checklist (MANDATORY)

Run this yourself before writing the output. Fix issues inline.

1. **Spec coverage:** Skim each section of the spec. Point to the task that implements it. Add missing tasks.
2. **File paths:** Every path must be verified against the current codebase (use Glob/Read). No guessing.
3. **Line numbers:** If referencing line ranges, confirm them by reading the file. Stale line numbers break the execute skill.
4. **Dependency order:** No task depends on a later task. If Task 5 needs Task 3's output, Task 3 comes first.
5. **Placeholder scan:** Search the plan for TBD, TODO, "similar to", "add appropriate". Fix every one.
6. **Type consistency:** Function names, method signatures, and property names must match across all tasks that reference them.
7. **Zero-context test:** Could a developer with no codebase knowledge follow each task independently? If not, add context.

## Output Contract

- **File written:** `{session_dir}/04-plan.md`
- **Return to orchestrator:** `PLAN_WRITTEN`
