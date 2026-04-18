# Phase Details

Detailed execution for each phase. The main SKILL.md provides the overview
table; this file has the per-phase specifics.

## Phase 1: Design — `superpowers:brainstorming`

Invoke `Skill("superpowers:brainstorming")`. Gives one-question-at-a-time
exploration, HTML mockups, A/B/C option framing, spec self-review, user
approval gate.

**Output:** spec in `docs/superpowers/specs/YYYY-MM-DD-*-design.md`.
Copy or symlink to `{session_dir}/01-spec.md`.

**GATE:** Do not proceed until user explicitly approves the spec.

## Phase 2: Codex Review Spec

Invoke `codex-review` skill with:
- `review_type`: `spec`
- `input_file`: `{session_dir}/01-spec.md`
- `output_file`: `{session_dir}/02-codex-review-spec.md`

If Codex unavailable → skip with warning, proceed to Decision Point #1.

**Decision Point #1:** present findings raw, ask A-E (see SKILL.md for format).
After A or B → SuperPowers rewrites spec → `{session_dir}/03-spec-v2.md`.
Do NOT auto-resubmit to Codex — user controls via option D.

## Phase 3: Plan — `superpowers:writing-plans`

Invoke `Skill("superpowers:writing-plans")`. Input: approved spec (01-spec.md
or 03-spec-v2.md). Produces bite-sized tasks, TDD cycle, complete code blocks,
pre-written commit messages.

**Output:** plan in `docs/superpowers/plans/YYYY-MM-DD-*.md` →
`{session_dir}/04-plan.md`.

## Phase 4: Codex Review Plan

Invoke `codex-review` with `review_type: plan`, `input_file: 04-plan.md`,
`output_file: 05-codex-review-plan.md`, `spec_path: <approved spec>`.

**Decision Point #2:** same A-E format.
After correction → `{session_dir}/06-plan-v2.md`.

## Phase 4.5: Task DAG + Sub-Agent Briefs

### Step 1: Build DAG

Read the plan, extract tasks. For each: `depends_on`, `files_owned`,
`files_readonly`, `files_forbidden`. Tasks with no mutual deps run in parallel
(same wave).

### Step 2: Generate Briefs

For each task, write `{session_dir}/task-briefs/task-{N}.md`:

```markdown
## Task Brief: {N} — {title}

### TASK
{what to implement — from plan}

### SCOPE
- OWNED files (write): {list}
- READ-ONLY files: {list}
- FORBIDDEN files: {list}

### SPEC REFERENCE
{link to spec section}

### SUCCESS CRITERIA
{numbered ACs: AC-001, AC-002}

### DEPENDENCIES
- Depends on: {task numbers or "none"}
- Depended on by: {task numbers or "none"}

### LEARNINGS TO APPLY
{relevant `.shipguard/mistakes.md` entries, if any}
```

### Step 3: Dispatch Waves

- Wave 1: tasks with no deps (parallel)
- Wave 2: tasks whose deps are all in Wave 1
- Wave N: ...

Between waves, verify previous wave succeeded.

### Stakes-Based Approval Matrix

|                | Easy to reverse                | Hard to reverse                |
|----------------|---------------------------------|---------------------------------|
| **Low stakes** | Auto-dispatch                   | Quick confirm: "Task N ok?"     |
| **High stakes**| Show plan, auto-dispatch        | **Explicit approval required**  |

- High stakes = auth, payments, data migration, production config, or >5 files
- Hard to reverse = DB schema changes, file deletions, API contract changes
- Spike maturity: auto-dispatch everything
- Dev maturity: use matrix
- Ship maturity: minimum quick-confirm everywhere

Write DAG + wave plan to `{session_dir}/08-task-dag.md`.

## Phase 5: Execute — `superpowers:subagent-driven-development`

Invoke `Skill("superpowers:subagent-driven-development")`. Input: approved plan
+ task briefs. Fresh subagent per task, two-stage review (spec compliance
then code quality), status handling (DONE / DONE_WITH_CONCERNS / BLOCKED /
NEEDS_CONTEXT).

**Model selection:** apply policy from `model-policy.md`. If implementer
returns BLOCKED on Sonnet due to reasoning issue, re-dispatch with Opus.

Record `base_ref` (SHA before execution) and `commit_list` (all new commits).

## Phase 6: Codex Review Implementation

Invoke `codex-review` with `review_type: impl`, `base_ref`, `commit_list`,
output `07-codex-review-impl.md`.

**Decision Point #3:** A-E format. A/B corrections create new commits.

## Phase 6.5: CodeRabbit Review (NEW)

Invoke `coderabbit-review` skill with:
- `session_dir`: current session dir
- `output_file`: `{session_dir}/07b-coderabbit-review-impl.md`
- `base_ref`: git SHA from Phase 5

If CodeRabbit CLI unavailable → skip with warning.

**Decision Point #3b:** same A-E format as #3, but applied to CodeRabbit
findings. Complements Codex (architectural) with static-analysis grounding
(lint, security, style, nits).

If both Codex AND CodeRabbit flag the same file:line → mark `[CONSENSUS]`
and escalate severity to the higher of the two.

## Phase 7: Verify — `superpowers:verification-before-completion`

Invoke `Skill("superpowers:verification-before-completion")`. Iron Law: NO
COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE. 5-step Gate Function
(IDENTIFY → RUN → READ → VERIFY → ONLY THEN).

If `pipeline.config.md` exists, use its verification commands. Otherwise
auto-detect or ask the user.

### AC-Level Spec Compliance Report

After verification passes, produce `{session_dir}/09-compliance-report.md`:

```markdown
| AC | Description | Test | Status |
|----|-------------|------|--------|
| AC-001 | User can upload PDF | test_upload_pdf() in tests/test_upload.py:42 | COVERED |
| AC-002 | Upload rejects >50MB | test_upload_size_limit() in tests/test_upload.py:67 | COVERED |
| AC-003 | Progress bar during upload | — | NOT COVERED |
```

- Extract ACs from approved spec. If spec has no numbered ACs, derive from requirements sections.
- For each AC: grep codebase for tests that exercise that behavior.
- COVERED = at least one passing test directly verifies the criterion.
- NOT COVERED → flag, don't block. User decides.

## Phase 7.5: Visual Verification (If UI Modified)

Runs only if Phase 5 touched `.tsx`, `.jsx`, `.vue`, `.svelte`, `.html`,
`.css`, `.scss`.

1. `git diff --name-only {base_ref}..HEAD | grep -E '\.(tsx|jsx|vue|svelte|html|css|scss)$'`
2. For each affected page: `agent-browser open <url>`, `snapshot`,
   `screenshot {session_dir}/screenshots/<page>.png`
3. **Read and verify EVERY screenshot immediately.** Unread = not verified.
4. If issues → fix code → re-run → new commit.

Use the project's actual port (typically from docker/dev server), never assume.

## Phase 8: Wiki Ingest (Automatic)

Runs if `wiki/schema.md` exists. Otherwise skip silently.

1. Read `wiki/schema.md` + `wiki/index.md` for context
2. Create combined session source at `wiki/sources/YYYY-MM-DD-pipeline-<slug>.md`:
   - Spec summary (key decisions, trade-offs)
   - Codex + CodeRabbit findings (bugs caught, patterns flagged)
   - Implementation decisions (architecture choices, rejected alternatives)
   - Verification (what was tested, what passed)
3. Create source summary at `wiki/pages/sources/YYYY-MM-DD-pipeline-<slug>.md`
4. Update/create entity + concept pages for: new components/services/modules,
   patterns established/changed, bugs found + fixes, architecture decisions
5. Update `wiki/index.md`
6. Append to `wiki/log.md`:
   ```
   ## [YYYY-MM-DD HH:MM] INGEST | Pipeline session: <slug>
   - Source: sources/YYYY-MM-DD-pipeline-<slug>.md
   - Pages created: <list>
   - Pages updated: <list>
   ```
