---
name: pipeline
description: "CLoClo — Claude + Codex Collaboration pipeline. Orchestrates the full dev cycle by chaining SuperPowers skills (brainstorming, writing-plans, subagent-driven-development, verification-before-completion) with Codex reviews between phases. Triggers on: /pipeline, new feature, implement, build, create"
---

# CLoClo Pipeline

Orchestrate the full development cycle by combining **existing skills** with
Codex review phases and interactive decision points.

**CLoClo does NOT reimplement brainstorming, planning, execution, or verification.**
It invokes the real skills and adds Codex reviews + decision points between them.

## Model Selection Policy

**CLoClo uses a mixed-model strategy to balance quality vs. quota consumption.**

On Max 20x / Max 5x plans, Opus has a tight weekly cap (~24-40h vs ~240-480h for Sonnet). Opus 4.7 is ~8 points ahead of Sonnet 4.6 on SWE-bench Verified — that gap matters for review/audit but is wasted on mechanical work.

Apply this policy when dispatching subagents across phases:

| Work type | Model | Why |
|-----------|-------|-----|
| Reviewers (spec, plan, impl — Phase 2/4/6 Codex fallback) | **Opus** | +8 pts SWE-bench Verified = real bugs caught |
| Adversarial triple-perspective pass | **Haiku** | Read-only skeptic questions |
| Phase 1 brainstorming (main session) | **Opus** | Design judgment, dialogue |
| Phase 3 writing-plans (main session) | **Opus** | Cross-module coherence |
| Phase 4.5 Task DAG + briefs | **Sonnet** | Mechanical decomposition of an approved plan |
| Phase 5 implementer subagents (1-2 files, clear spec) | **Sonnet** | Spec is the blueprint, implementation is mechanical |
| Phase 5 implementer subagents (touches >5 files, architecture) | **Opus** | Cross-file coherence required |
| Phase 5 spec reviewer / code-quality reviewer subagents | **Opus** | Reviews benefit from the +8 pts gap |
| Phase 7 verification-before-completion | **Sonnet** | Run tests + read output, no design judgment |
| Phase 7.5 visual verification (agent-browser) | **Sonnet** | Scripted capture + visual check |

**Override rule:** Critical domains (auth, payments, data migration, security) always use Opus regardless of the table above.

**How to apply in practice:** When invoking SuperPowers skills that dispatch subagents (`subagent-driven-development`, `writing-plans`), pass the `model` parameter on each `Agent(...)` call explicitly. Do not rely on inherit — inherit defaults to the main session's model which is typically Opus.

---

## Prerequisites — Auto-Install

At pipeline start, check and **automatically fix** missing dependencies.

### Step 1: Check SuperPowers

```bash
# Try to invoke a SuperPowers skill to see if it's available
```

If SuperPowers is NOT available:
1. Read `~/.claude/settings.json`
2. Add `"superpowers@superpowers-marketplace": true` to `enabledPlugins`
3. Add `"superpowers-marketplace": {"source": {"source": "github", "repo": "obra/superpowers-marketplace"}}` to `extraKnownMarketplaces` (if not already present)
4. Write back `settings.json`
5. Tell the user: "SuperPowers was not installed. I've added it to your settings. **Please restart Claude Code** and run `/pipeline` again."
6. **STOP.** SuperPowers requires a restart to load.

### Step 2: Check Codex CLI

```bash
codex --version
```

If `codex` is NOT found:
1. Run: `npm install -g @openai/codex`
2. If npm fails, tell the user: "Could not install Codex CLI. Install it manually: `npm install -g @openai/codex`"
3. After install, run: `codex --version` to confirm

### Step 3: Check Codex companion (replaces old auth check)

The Codex CLI manages its own authentication (stored token). Do NOT check
`codex whoami` (requires TTY) or `OPENAI_API_KEY` (not used by Codex CLI).
The companion script handles auth internally — if it fails at runtime,
the pipeline falls back to degraded mode.

### Step 4: Check Codex Claude Code plugin

```bash
find ~/.claude/plugins -name codex-companion.mjs -path '*/codex/scripts/*' 2>/dev/null | head -1
```

If companion NOT found:
1. Read `~/.claude/settings.json`
2. Add `"codex@openai-codex": true` to `enabledPlugins`
3. Add `"openai-codex": {"source": {"source": "github", "repo": "openai/codex-plugin-cc"}}` to `extraKnownMarketplaces` (if not already present)
4. Write back `settings.json`
5. Tell the user: "Codex plugin was not installed. I've added it to your settings. **Please restart Claude Code** and run `/pipeline` again."
6. **STOP.** Plugin requires a restart to load.

### Degraded Mode

### Degraded Mode — Claude Fallback

If Codex CLI, companion, or runtime fail (including usage limits):
- **WARNING:** "Codex unavailable. Using Claude agent review as fallback."
- Phases 2, 4, 6 still run, but use a **Claude subagent** instead of Codex.
- The subagent is dispatched with `subagent_type: "superpowers:code-reviewer"` and receives
  the same review brief (spec, plan, file paths, base_ref).
- Output is written to the same session file (e.g., `02-claude-review-spec.md` instead of `02-codex-review-spec.md`).
- Decision points A-E still apply — the user decides what to integrate.
- This is NOT as good as Codex (same model family, less independence), but it catches
  real bugs because the reviewer agent has fresh context and hasn't seen the conversation.
- The pipeline NEVER skips review phases entirely. At minimum, a Claude agent reviews.

## Session Setup

1. Ask the user what they want to build (or take their initial message).
2. Create session directory: `docs/cloclo-sessions/YYYY-MM-DD-<slug>/`
   - `<slug>` = 2-3 word kebab-case summary of the topic
3. Initialize `session.log`:
   ```
   [timestamp] CLoClo session started: <slug>
   [timestamp] Prerequisites: superpowers=OK, codex=OK|MISSING, auth=OK|MISSING
   ```
4. If the project has specific verification needs, create `pipeline.config.md`
   in the session directory (ask the user or auto-detect from project files).

## Phase 1: Design — Invoke `superpowers:brainstorming`

**Invoke Skill("superpowers:brainstorming")**

This gives you the FULL SuperPowers brainstorming experience:
- One-question-at-a-time exploration
- Visual companion with HTML mockups in the browser
- Options A/B/C with pros/cons
- 2-3 approach proposals with trade-offs
- Design-for-isolation principles
- "Too simple to need a design" anti-pattern prevention
- Spec self-review (placeholders, coherence, scope, ambiguity)
- User approval gate

**After brainstorming completes:** The spec will be in `docs/superpowers/specs/YYYY-MM-DD-*-design.md`.
Copy or symlink it to `{session_dir}/01-spec.md` for session tracking.

Log: `[timestamp] Phase 1 complete: 01-spec.md`

**GATE:** Do not proceed until the user has explicitly approved the spec.

---

## Phase 2: Codex Review Spec

**If Codex available:** Invoke the `codex-review` skill with:
- `review_type`: `spec`
- `input_file`: `{session_dir}/01-spec.md`
- `output_file`: `{session_dir}/02-codex-review-spec.md`

**If Codex unavailable:** Skip with warning, go directly to Decision Point #1.

Log: `[timestamp] Codex review spec: {status}`

### Decision Point #1

Present the Codex findings (raw, no filtering) and ask:

```
Codex a review ta spec. Voici ses findings :

[3-5 line summary of key findings from 02-codex-review-spec.md]

Fichier complet : {session_dir}/02-codex-review-spec.md

Que veux-tu faire ?

A. Integrer tous les findings et continuer
   → SuperPowers corrige la spec, ecrit 03-spec-v2.md

B. Integrer certains findings (tu precises lesquels)

C. Ignorer la review et continuer avec la spec actuelle

D. Demander a Codex de creuser un point precis
   → Codex repart en review ciblee

E. Modifier la spec toi-meme
   → Tu edites le fichier, dis "c'est bon" quand pret

Ou tape ce que tu veux — commentaire libre.
```

Log the user's choice in `session.log`.

After A or B: SuperPowers corrects the spec → `{session_dir}/03-spec-v2.md`.
Do NOT automatically re-submit to Codex. User controls re-review via D.

---

## Phase 3: Plan — Invoke `superpowers:writing-plans`

**Invoke Skill("superpowers:writing-plans")**

Input: the approved spec (01-spec.md or 03-spec-v2.md).

This gives you the FULL SuperPowers plan writing:
- Scope check with decomposition
- File structure table
- Bite-sized tasks (2-5 minutes each)
- TDD cycle (write failing test, verify failure, implement, verify pass)
- Complete code blocks (no TBD, no placeholders)
- Pre-written commit messages
- Self-review checklist
- DRY, YAGNI, frequent commits

**After plan is written:** The plan will be in `docs/superpowers/plans/YYYY-MM-DD-*.md`.
Copy or symlink it to `{session_dir}/04-plan.md`.

Log: `[timestamp] Phase 3 complete: 04-plan.md`

---

## Phase 4: Codex Review Plan

**If Codex available:** Invoke `codex-review` with:
- `review_type`: `plan`
- `input_file`: `{session_dir}/04-plan.md`
- `output_file`: `{session_dir}/05-codex-review-plan.md`
- `spec_path`: path to approved spec

**If Codex unavailable:** Skip with warning.

### Decision Point #2

Same A-E format as Decision Point #1.
If corrections: SuperPowers rewrites → `{session_dir}/06-plan-v2.md`.

---

## Phase 4.5: Task DAG + Sub-Agent Briefs

Before executing, build a dependency graph and structured briefs from the approved plan.

### Step 1: Build Task DAG

Read the plan and extract tasks. For each task, identify:
- **Depends on:** which other tasks must complete first (by task number)
- **Files owned:** files this task will create or modify (exclusive write access)
- **Files read-only:** files this task needs to read but must NOT modify
- **Files forbidden:** files this task must never touch (other tasks' owned files)

Produce a DAG (directed acyclic graph) where edges represent dependencies:
```
Task 1 (no deps) ──► Task 3 (depends on 1)
Task 2 (no deps) ──► Task 4 (depends on 2, 3)
```

Tasks with no mutual dependencies run **in parallel** (same wave). Tasks with dependencies run **after** their prerequisites complete.

### Step 2: Generate Sub-Agent Briefs

For each task, generate a structured brief:
```markdown
## Task Brief: {task_number} — {title}

### TASK
{What to implement — from the plan}

### SCOPE
- OWNED files (write access): {list}
- READ-ONLY files: {list}
- FORBIDDEN files (do not touch): {list}

### SPEC REFERENCE
{Link to specific section of the spec that defines this task's requirements}

### SUCCESS CRITERIA
{Numbered acceptance criteria from the spec, e.g., AC-001, AC-002}

### DEPENDENCIES
- Depends on: {task numbers that must complete first, or "none"}
- Depended on by: {task numbers waiting for this, or "none"}

### LEARNINGS TO APPLY
{Relevant entries from .shipguard/mistakes.md or project memory, if any}
```

Write all briefs to `{session_dir}/task-briefs/task-{N}.md`.

### Step 3: Dispatch Waves

Group tasks into waves based on the DAG:
- **Wave 1:** All tasks with no dependencies (run in parallel)
- **Wave 2:** Tasks whose dependencies are all in Wave 1 (run after Wave 1 completes)
- **Wave N:** And so on

Each wave's agents run in parallel. Between waves, verify all tasks in the previous wave completed successfully before dispatching the next wave.

### Stakes-Based Approval Matrix

Before dispatching each task, classify it on two axes:

| | Easy to reverse | Hard to reverse |
|---|---|---|
| **Low stakes** | Auto-dispatch (no confirmation) | Quick confirm: "Task {N} modifies {file} — ok?" |
| **High stakes** | Show plan, auto-dispatch | **Explicit approval required** — show full brief, wait for "oui" |

**Classification rules:**
- High stakes = modifies auth, payments, data migration, production config, or >5 files
- Hard to reverse = modifies database schema, deletes files, changes API contracts
- Everything else = low stakes + easy to reverse

In `spike` maturity: everything auto-dispatches (no approvals).
In `dev` maturity: use the matrix above.
In `ship` maturity: everything requires at least quick confirm.

Write the DAG and wave plan to `{session_dir}/08-task-dag.md`.

---

## Phase 5: Execute — Invoke `superpowers:subagent-driven-development`

**Invoke Skill("superpowers:subagent-driven-development")**

Input: the approved plan (04-plan.md or 06-plan-v2.md) AND the task briefs from Phase 4.5.

This gives you the FULL SuperPowers execution:
- Fresh subagent per task (no context pollution)
- Two-stage review: spec compliance then code quality
- Status handling (DONE, DONE_WITH_CONCERNS, BLOCKED, NEEDS_CONTEXT)
- Review loops until approved
- Model selection guidance (cheap for mechanical, capable for architecture)
- Process flow with decision diamonds
- Red flags and anti-patterns
- Final integration review

**Model Selection — apply the policy from the top of this SKILL.md:**
- Implementer subagents: `model: "sonnet"` by default. Upgrade to `model: "opus"` only if the task touches >5 files or requires architectural judgment.
- Spec reviewer subagents: always `model: "opus"` (the review step is where bugs are caught).
- Code-quality reviewer subagents: always `model: "opus"`.
- If an implementer returns `BLOCKED` on a Sonnet dispatch and the blocker is a reasoning issue, re-dispatch with `model: "opus"`.

Log: `[timestamp] Phase 5 complete: [commit list]`

Record `base_ref` (git SHA before execution) and `commit_list` (all new commits).

---

## Phase 6: Codex Review Implementation

**If Codex available:** Invoke `codex-review` with:
- `review_type`: `impl`
- `input_file`: `{session_dir}/04-plan.md` (or 06-plan-v2.md)
- `output_file`: `{session_dir}/07-codex-review-impl.md`
- `spec_path`: approved spec
- `plan_path`: approved plan
- `base_ref`: git SHA recorded before Phase 5
- `commit_list`: all commits from Phase 5

**If Codex unavailable:** Skip with warning.

### Decision Point #3

```
Codex a review l'implementation. Voici ses findings :

[Summary of findings]

A. Integrer tous les findings → SuperPowers corrige, nouveau commit

B. Corriger certains findings (tu precises)

C. Ignorer et passer a la verification

D. Demander a Codex de creuser un bug potentiel

E. Lancer un audit complet du projet

Ou commentaire libre.
```

---

## Phase 7: Verify — Invoke `superpowers:verification-before-completion`

**Invoke Skill("superpowers:verification-before-completion")**

This gives you the FULL SuperPowers verification:
- Iron Law: NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
- 5-step Gate Function (IDENTIFY, RUN, READ, VERIFY, ONLY THEN)
- Common Failures table
- Red Flags section
- Rationalization prevention table
- Key Patterns (tests, regression, build, requirements, delegation)

If `pipeline.config.md` exists in the session, use its verification commands.
Otherwise, let the verification skill auto-detect or ask the user.

### AC-Level Spec Compliance Report

After verification passes, produce a machine-readable compliance report mapping every acceptance criterion from the spec to its covering test(s):

```markdown
## Spec Compliance Report

| AC | Description | Test | Status |
|----|-------------|------|--------|
| AC-001 | User can upload PDF | test_upload_pdf() in tests/test_upload.py:42 | COVERED |
| AC-002 | Upload rejects >50MB files | test_upload_size_limit() in tests/test_upload.py:67 | COVERED |
| AC-003 | Progress bar shows during upload | — | NOT COVERED |
| AC-004 | Error toast on network failure | — | NOT COVERED |
```

**Rules:**
- Extract ACs from the approved spec (01-spec.md or 03-spec-v2.md). If the spec doesn't have numbered ACs, derive them from requirements sections.
- For each AC, grep the codebase for tests that exercise that behavior.
- `COVERED` = at least one passing test directly verifies this criterion.
- `NOT COVERED` = no test found. Flag for the user's attention.
- A feature is complete when ALL ACs are COVERED. If any are NOT COVERED, report but don't block (user decides).

Write to `{session_dir}/09-compliance-report.md`.

Log: `[timestamp] Phase 7 complete: {PASSED|FAILED} | AC coverage: {covered}/{total}`

---

## Phase 7.5: Visual Verification (If UI Modified)

**This phase runs only if the implementation touched UI files** (`.tsx`, `.jsx`, `.vue`, `.svelte`, `.html`, `.css`).
If no UI files were modified, skip to Phase 8.

### Prerequisite: Check agent-browser

```bash
command -v agent-browser >/dev/null 2>&1
```

**If agent-browser is NOT found:**
- **WARNING:** "agent-browser is not installed. Visual verification skipped. Install it for UI verification: https://github.com/vrsalis/agent-browser"
- Log: `[timestamp] Phase 7.5 SKIPPED: agent-browser not available`
- Continue to Phase 8. Do NOT block the pipeline.

**If agent-browser IS available:**

### Steps

1. Detect if any commits from Phase 5 modified UI files:
   ```bash
   git diff --name-only {base_ref}..HEAD | grep -E '\.(tsx|jsx|vue|svelte|html|css|scss)$'
   ```

2. If UI files found, identify the affected pages/routes.

3. For each affected page:
   ```bash
   agent-browser open <url>          # Open the page
   agent-browser snapshot            # Get interactive elements
   agent-browser screenshot <path>   # Capture visual state
   ```

4. **Read and verify EVERY screenshot immediately.** Do not skip this.
   - Does the UI match the spec from Phase 1?
   - Are there visual regressions? Broken layouts? Missing elements?
   - Do interactive elements work? Click buttons, fill forms, verify modals.

5. Save verification screenshots to `{session_dir}/screenshots/` for evidence.

6. If issues found:
   - Fix the code.
   - Re-run agent-browser to verify the fix.
   - New commit with fix.

**Rules:**
- **agent-browser is the preferred visual testing tool.** If available, use it exclusively.
- **Screenshots are evidence.** They go in the session directory and optionally in the wiki.
- **Every screenshot must be READ and verified.** An unread screenshot is not a verification.
- Use the project's actual port (typically from docker/dev server), never assume.

Log: `[timestamp] Phase 7.5 complete: {N pages verified, M screenshots}`

---

## Session File Structure

```
docs/cloclo-sessions/YYYY-MM-DD-<slug>/
├── 01-spec.md                  ← From superpowers:brainstorming
├── 02-codex-review-spec.md     ← From codex-review skill
├── 03-spec-v2.md               ← If corrections after review
├── 04-plan.md                  ← From superpowers:writing-plans
├── 05-codex-review-plan.md     ← From codex-review skill
├── 06-plan-v2.md               ← If corrections after review
├── 07-codex-review-impl.md     ← From codex-review skill
├── screenshots/                ← Visual verification evidence (Phase 7.5)
│   ├── page-name-01.png
│   └── page-name-02.png
├── session.log                 ← All decisions + timestamps + job-ids
└── pipeline.config.md          ← Optional verification config
```

## Session Log Format

```
[2026-04-06T14:30:00] CLoClo session started: auth-refactor
[2026-04-06T14:30:01] Prerequisites: superpowers=OK, codex=OK, auth=OK
[2026-04-06T14:45:00] Phase 1 complete: 01-spec.md
[2026-04-06T14:45:30] User approved spec
[2026-04-06T14:50:00] Codex review spec started (job-id: task-abc123)
[2026-04-06T14:55:00] Codex review spec complete: 02-codex-review-spec.md
[2026-04-06T14:55:30] Decision #1: A (integrate all)
[2026-04-06T14:58:00] Spec corrected: 03-spec-v2.md
[2026-04-06T15:10:00] Phase 3 complete: 04-plan.md
[2026-04-06T15:15:00] Codex review plan started (job-id: task-def456)
[2026-04-06T15:22:00] Codex review plan complete: 05-codex-review-plan.md
[2026-04-06T15:22:30] Decision #2: B (integrate findings 1,3, ignore 2)
[2026-04-06T15:25:00] Plan corrected: 06-plan-v2.md
[2026-04-06T15:26:00] Phase 5 started (base_ref: a1b2c3d)
[2026-04-06T15:45:00] Phase 5 complete: 5 commits (a1b..f6e)
[2026-04-06T15:50:00] Codex review impl started (job-id: task-ghi789)
[2026-04-06T16:02:00] Codex review impl complete: 07-codex-review-impl.md
[2026-04-06T16:02:30] Decision #3: A (fix all)
[2026-04-06T16:10:00] Phase 7: VERIFICATION_PASSED
```

## Phase 8: Wiki Ingest (Automatic)

**This phase runs automatically if a project wiki exists (`wiki/schema.md`).**
If no wiki exists, skip silently. The user can set one up later with `/wiki init`.

### What gets ingested

The pipeline session is a rich knowledge source — decisions, trade-offs, reviews, patterns.
Auto-ingest the session as a single source:

1. Check if `wiki/schema.md` exists. If not → skip Phase 8 entirely.
2. Read `wiki/schema.md` and `wiki/index.md` for context.
3. Create a **combined session source** at `wiki/sources/YYYY-MM-DD-pipeline-<slug>.md`:
   ```markdown
   # Pipeline Session: <slug>

   ## Spec Summary
   [Key decisions and trade-offs from 01-spec.md or 03-spec-v2.md]

   ## Codex Findings
   [Important findings from reviews — bugs caught, patterns flagged]

   ## Implementation Decisions
   [Architecture choices, rejected alternatives, lessons learned]

   ## Verification
   [What was tested, what passed, what needed fixing]
   ```
4. Create a **source summary page** at `wiki/pages/sources/YYYY-MM-DD-pipeline-<slug>.md`.
5. Update/create entity and concept pages for:
   - New components, services, or modules created
   - Patterns established or changed
   - Bugs found and how they were fixed
   - Architecture decisions and their rationale
6. Update `wiki/index.md` with new/modified pages.
7. Append to `wiki/log.md`:
   ```
   ## [YYYY-MM-DD HH:MM] INGEST | Pipeline session: <slug>
   - Source: sources/YYYY-MM-DD-pipeline-<slug>.md
   - Pages created: <list>
   - Pages updated: <list>
   ```
8. Report:
   ```
   Wiki updated: +N pages from pipeline session
   ```

Log: `[timestamp] Phase 8 complete: wiki updated (N pages)`

---

## Maturity Levels

A single `maturity` field controls how strictly the pipeline runs. Set in `pipeline.config.md` or auto-detected from project state.

| Level | When | Gate strictness | Parallelism | Review depth |
|-------|------|-----------------|-------------|-------------|
| `spike` | Exploring, prototyping | Soft gates (user can skip freely) | 1 agent | Codex review optional |
| `dev` | Active development (default) | Standard gates (A-E decisions) | Up to 3 agents | Codex reviews all phases |
| `ship` | Pre-release, production | Hard gates (no skip without documented reason) | Up to 5 agents | Codex + adversarial triple-perspective |

**Auto-detection:** If no maturity is set, detect from context:
- No tests, no CI → `spike`
- Tests exist, active branch → `dev`
- CI passing, release branch or tag → `ship`

The maturity level is logged in session.log and passed to all skill invocations. SuperPowers skills adapt their depth accordingly (e.g., brainstorming in spike mode asks fewer questions).

---

## Bounded Retry Loops

Every phase that can fail has a hard retry ceiling. Prevents infinite loops and runaway token spend.

| Phase | Max retries | On exhaustion |
|-------|-------------|---------------|
| Phase 2 (Codex review spec) | 2 | Skip review, warn user |
| Phase 4 (Codex review plan) | 2 | Skip review, warn user |
| Phase 5 (Subagent execution) | 3 per task | Mark task BLOCKED, continue others |
| Phase 6 (Codex review impl) | 2 | Skip review, warn user |
| Phase 7 (Verification) | 3 | FAIL pipeline, require user intervention |
| Phase 7.5 (Visual verification) | 2 per page | Log failure, continue to next page |

When a retry triggers:
1. Log: `[timestamp] Phase {N} retry {attempt}/{max}: {reason}`
2. If exhausted: `[timestamp] Phase {N} EXHAUSTED after {max} retries — {action taken}`
3. Never retry silently — always print what failed and what happens next.

---

## Resume / Checkpoint

The pipeline writes `{session_dir}/checkpoint.json` after each phase completion:

```json
{
  "session": "2026-04-16-auth-refactor",
  "maturity": "dev",
  "last_completed_phase": 4,
  "last_completed_at": "2026-04-16T15:22:00Z",
  "artifacts": {
    "spec": "03-spec-v2.md",
    "plan": "04-plan.md",
    "base_ref": "a1b2c3d",
    "commits": []
  },
  "decisions": {
    "1": {"choice": "A", "at": "2026-04-16T14:55:30Z"},
    "2": {"choice": "B", "details": "integrate 1,3 only", "at": "2026-04-16T15:22:30Z"}
  },
  "retries": {"phase_2": 0, "phase_4": 0}
}
```

**On pipeline start:** If `checkpoint.json` exists in the session dir:
1. Read it and show: `Resuming session "{slug}" from Phase {N+1}. Last completed: Phase {N} at {time}.`
2. Ask: `Reprendre a partir de Phase {N+1} ? (oui/non/restart)`
3. If `oui`: skip to Phase N+1 with all artifacts from checkpoint.
4. If `restart`: delete checkpoint, start from Phase 1.
5. If `non`: ask what to do.

**Checkpoint writes:** After EACH phase completes successfully, update checkpoint.json. This means a crash mid-Phase 5 loses only that phase's work, not the entire session.

---

## Auto-Written Session Handoff

At the end of every pipeline run (success or failure), automatically write `{session_dir}/handoff.md`:

```markdown
# Session Handoff: {slug}

## Status: {COMPLETED | FAILED_AT_PHASE_N | PARTIAL}

## What was done
- [List of completed phases with key outcomes]
- Commits: {commit_list}

## What is blocked (if any)
- [Phase that failed + reason]
- [Unresolved review findings]

## Next recommended action
- [Specific next step: "Run verification again after fixing X", "Resume with /pipeline", etc.]

## Key decisions made
- Decision #1: {choice} — {reason}
- Decision #2: {choice} — {reason}

## Files to read for context
- Spec: {path}
- Plan: {path}
- Review: {path}
```

This enables a new Claude session to pick up where the previous one left off by reading handoff.md instead of replaying the entire conversation.

---

## Important Rules

1. **Do NOT reimplement SuperPowers or Codex skills.** Invoke them. They are the real thing.
2. **After correction (A or B), do NOT auto-resubmit to Codex.** User controls via option D.
3. **Codex reviews are FOREGROUND.** Claude waits, shows "Codex is reviewing...", reads the result.
4. **If user types anything other than A-E:** treat as free-form comment and adapt.
5. **Each phase outputs to session dir** with numbered filenames for traceability.
6. **Session can be resumed.** Check checkpoint.json for last completed phase and continue from there.
7. **SuperPowers specs and plans** are saved to their own directories (`docs/superpowers/specs/`, `docs/superpowers/plans/`). CLoClo copies or symlinks them into the session dir for session tracking.
8. **Wiki ingest is automatic and silent.** If no wiki exists, Phase 8 is skipped without mention. The wiki grows transparently as the user works.
9. **Checkpoint after every phase.** Write checkpoint.json immediately after each phase succeeds.
10. **Handoff on exit.** Write handoff.md at the end of every pipeline run, regardless of outcome.
