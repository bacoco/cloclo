---
name: execute
description: "Phase 5 of the dev pipeline: implement an approved plan task-by-task using fresh subagents with two-stage review (spec compliance + code quality). Sequential by default, parallel opt-in."
user-invocable: false
---

# Execute -- Subagent-Driven Implementation

Implement an approved plan task-by-task. Each task gets a fresh implementer
subagent, followed by two independent review stages: spec compliance first,
then code quality. No task moves forward until both reviews pass.

<HARD-GATE>
Do NOT modify the spec or the plan. This skill implements what was already
approved. If the plan is wrong, return EXECUTION_PARTIAL and let the pipeline
orchestrator handle re-planning.
</HARD-GATE>

## 1. Context Reception

This skill receives from the pipeline orchestrator:

| Parameter    | Required | Description                                               |
|--------------|----------|-----------------------------------------------------------|
| `session_dir`| yes      | Absolute path to the pipeline session directory            |
| `plan_path`  | yes      | Path to the approved plan (`04-plan.md` or `06-plan-v2.md`)|
| `spec_path`  | yes      | Path to the approved spec (`01-spec.md` or `03-spec-v2.md`)|

## 2. Plan Parsing

Read the plan file once. Extract:

1. **All tasks** -- sections starting with `### Task N:` through the next
   `### Task` heading or end of file. Capture the full text of each task
   including description, steps, verify commands, commit messages, and file lists.
2. **File structure table** -- the `| File | Action | Reason |` table from the
   plan. Use this to verify that tasks do not overlap on files.
3. **Parallelism hints** -- any explicit notes about which tasks can run in
   parallel (present only if the plan author added them).

After extraction, create a TodoWrite checklist with one entry per task:

```
Task 1: <task name> -- pending
Task 2: <task name> -- pending
...
Task N: <task name> -- pending
Integration check -- pending
```

Record the starting git SHA for the session:

```bash
git rev-parse HEAD
```

Log to `session.log`:

```
[<ISO-8601>] Execute phase started: <N> tasks extracted from <plan_path>
[<ISO-8601>] Base SHA: <sha>
```

## 3. Execution Mode

### Default: Sequential

Tasks execute one at a time, in the order defined by the plan. This is the
safe default. Use it unless the user explicitly requests parallel execution.

### Opt-in: Parallel

Only if ALL of these conditions are met:

1. The user explicitly requests parallel execution
2. The plan contains parallelism hints marking specific tasks as independent
3. No two parallel tasks touch the same file (verified against the file table)

**Parallel rules:**

- Dispatch at most 3 implementer subagents simultaneously
- Each parallel batch must have strictly non-overlapping file lists
- If any subagent reports BLOCKED, pause all parallel work and resolve sequentially
- If git detects a merge conflict after any subagent commits, STOP immediately
  and escalate to the user
- Reviews still run sequentially per task (no parallel reviews)

## 4. Per-Task Flow

This is the core loop. For each task in plan order:

### 4a. Dispatch Implementer (fresh Agent subagent)

Use the `implementer-prompt.md` template. Inject into the template:

- `{{TASK_TEXT}}` -- full text of the current task (pasted, not a file reference)
- `{{SPEC_PATH}}` -- path to the approved spec
- `{{PLAN_PATH}}` -- path to the approved plan
- `{{FILE_LIST}}` -- the specific files this task should touch

The implementer is a fresh subagent with no inherited session context.
Provide exactly the context it needs -- nothing more, nothing less.

**Handle the implementer's response:**

| Status              | Action                                                      |
|---------------------|-------------------------------------------------------------|
| DONE                | Proceed to spec compliance review (4b)                      |
| DONE_WITH_CONCERNS  | Read the concerns. If about correctness or scope, investigate before review. If observational, note them and proceed to review. |
| BLOCKED             | Assess the blocker. If context problem: provide context, re-dispatch. If task too complex: break it down. If plan is wrong: escalate to user, pause pipeline. |
| NEEDS_CONTEXT       | Provide the requested context and re-dispatch the same task. |

**Re-dispatch limits:**

- NEEDS_CONTEXT: max 2 re-dispatches per task, then escalate to user
- BLOCKED: max 1 re-dispatch with additional context, then escalate

Log each dispatch:

```
[<ISO-8601>] Task <N>: dispatched implementer
[<ISO-8601>] Task <N>: implementer status = <STATUS>
```

### 4b. Spec Compliance Review (fresh Agent subagent)

Use the `spec-reviewer-prompt.md` template. Inject:

- `{{TASK_TEXT}}` -- full text of the current task
- `{{SPEC_PATH}}` -- path to the approved spec

**CRITICAL:** The reviewer must READ the actual code changes, not trust the
implementer's report. The reviewer is an independent verifier.

**Handle the reviewer's response:**

| Status         | Action                                                          |
|----------------|-----------------------------------------------------------------|
| SPEC_COMPLIANT | Proceed to code quality review (4c)                             |
| ISSUES_FOUND   | Send issues back to the implementer subagent. The implementer fixes, then the spec reviewer reviews again. |

**Review loop limit:** Max 3 spec review iterations per task. If the third
review still finds issues, escalate to the user with the full issue list.

Log each review:

```
[<ISO-8601>] Task <N>: spec review #<iteration> = <STATUS>
```

### 4c. Code Quality Review (fresh Agent subagent)

Only runs AFTER spec compliance passes. Use the `code-quality-reviewer-prompt.md`
template.

The code quality reviewer checks readability, patterns, edge cases, performance,
and security -- but does NOT re-check spec compliance.

**Handle the reviewer's response:**

| Status           | Action                                                        |
|------------------|---------------------------------------------------------------|
| QUALITY_APPROVED | Task is complete. Proceed to 4d.                              |
| QUALITY_ISSUES   | Send issues back to the implementer. The implementer fixes, then the quality reviewer reviews again. |

**Review loop limit:** Max 2 quality review iterations per task. If the second
review still has issues, log the remaining issues as technical debt and proceed
(quality issues are less critical than spec gaps).

Log each review:

```
[<ISO-8601>] Task <N>: quality review #<iteration> = <STATUS>
```

### 4d. Mark Task Complete

Update the TodoWrite checklist to mark the task as completed. Log:

```
[<ISO-8601>] Task <N>: COMPLETE (<commit SHA>)
```

## 5. After All Tasks

### 5a. Integration Check

Once every task is marked complete, run a final integration verification:

1. Read the spec's objective and success criteria
2. Read all committed code as a whole (git diff from base SHA to HEAD)
3. Verify the pieces connect: imports resolve, interfaces match, data flows
4. Run any project-level verify commands from `pipeline.config.md`
   (typecheck, lint, test, build)

If integration issues are found, dispatch a fix subagent with specific
instructions. Do NOT re-run the full task loop.

### 5b. Completion Report

Compile the final report:

```
## Execution Report

**Status:** EXECUTION_COMPLETE | EXECUTION_PARTIAL
**Tasks:** <completed>/<total>
**Commits:** <first-sha>..<last-sha> (<count> commits)
**Base SHA:** <sha recorded at start>

### Tasks Completed
- Task 1: <name> -- <commit sha>
- Task 2: <name> -- <commit sha>
...

### Concerns Raised
- [Any DONE_WITH_CONCERNS notes]
- [Any quality issues logged as tech debt]

### Blockers (if EXECUTION_PARTIAL)
- [Task N]: [why it could not be completed]
```

Log to `session.log`:

```
[<ISO-8601>] Execute phase complete: <completed>/<total> tasks
[<ISO-8601>] Commits: <first-sha>..<last-sha>
```

## 6. Red Flags -- STOP Immediately

Halt execution and escalate to the user if any of these occur:

1. **File collision** -- two subagents (parallel mode) touched the same file
2. **Repeated blockers** -- implementer reports BLOCKED on 2 or more tasks
3. **Review loop exceeded** -- spec review hits 3 iterations without resolution
4. **Git conflict** -- any merge conflict detected after a commit
5. **Spec drift** -- a reviewer notes that the plan contradicts the spec
6. **Test regression** -- a previously passing test now fails after a task

When stopping, log the reason and return EXECUTION_PARTIAL with the blocker
description. Do not attempt heroic recovery.

## 7. Output Contract

| Key              | Value                                                    |
|------------------|----------------------------------------------------------|
| **Return status**| `EXECUTION_COMPLETE` or `EXECUTION_PARTIAL`              |
| **Commit range** | `<base-sha>..<head-sha>` covering all implementation work|
| **Report**       | Completion report written to conversation (not a file)   |
| **Session log**  | All events appended to `{session_dir}/session.log`       |
| **Next phase**   | Pipeline orchestrator proceeds to implementation review (Phase 6) |

## 8. Anti-Patterns

- Letting an implementer subagent read the full plan file (paste the task text)
- Running code quality review before spec compliance passes
- Skipping reviews to "save time" (reviews catch real bugs)
- Re-dispatching the same subagent instead of a fresh one after a fix
- Fixing code yourself instead of dispatching a subagent (context pollution)
- Proceeding to the next task with unresolved review issues
- Running parallel execution without explicit user consent
- Modifying the spec or plan during execution (return EXECUTION_PARTIAL instead)
- Ignoring DONE_WITH_CONCERNS (always read and assess the concerns)
- Retrying a BLOCKED task without changing something (more context, smaller scope, or escalation)
