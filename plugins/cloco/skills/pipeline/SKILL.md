---
name: pipeline
description: "CLOco pipeline: orchestrate the full dev cycle — design, spec, Codex review, plan, Codex review, execute, Codex review impl, verify. Triggers on: /pipeline, new feature, implement, build, create"
---

# Pipeline Orchestrator

Master skill that routes through all 7 phases of the CLOco dev pipeline.
Each phase produces numbered artifacts in a session directory. Codex reviews
are optional — the pipeline degrades gracefully when Codex is unavailable.

---

## 1. Prerequisites Check

Run these checks at the very start. Failures are warnings, not blockers.

```bash
# 1a. Check codex CLI installed
if command -v codex &>/dev/null; then
  CODEX_VERSION=$(codex --version 2>&1)
  echo "OK: codex $CODEX_VERSION"
  CODEX_AVAILABLE=true
else
  echo "ERROR: Codex CLI is not installed. Install it with: npm install -g @openai/codex"
  echo "Codex reviews will be skipped for this session."
  CODEX_AVAILABLE=false
fi

# 1b. Locate codex-companion.mjs
CODEX_COMPANION_PATH="${CODEX_COMPANION_PATH:-$(find ~/.claude/plugins -name codex-companion.mjs -path '*/codex/scripts/*' 2>/dev/null | head -1)}"
if [ -z "$CODEX_COMPANION_PATH" ]; then
  echo "ERROR: Codex Claude Code plugin is not installed. Install it from the Claude Code plugin marketplace."
  echo "Codex reviews will be skipped for this session."
  CODEX_AVAILABLE=false
else
  echo "OK: codex-companion.mjs found at $CODEX_COMPANION_PATH"
fi

# 1c. Check codex authenticated
if [ "$CODEX_AVAILABLE" = true ]; then
  CODEX_AUTH=$(codex whoami 2>&1)
  if echo "$CODEX_AUTH" | grep -qi "error\|not.*logged\|unauthenticated"; then
    echo "WARNING: codex not authenticated. Codex reviews will be skipped."
    CODEX_AVAILABLE=false
  else
    echo "OK: codex authenticated as $CODEX_AUTH"
  fi
fi
```

If any check fails, set `CODEX_AVAILABLE=false` and continue. Do NOT abort.

---

## 2. Session Creation

**2a. Slug.** Derive a short slug from the user's topic (lowercase, hyphens).
Ask if not clear. Examples: `search-filter`, `export-pdf`, `auth-refactor`.

**2b. Directory.** Create `docs/cloco-sessions/YYYY-MM-DD-<slug>/` with
two files: `session.log` and `pipeline.config.md`.

**2c. session.log.** Write opening entries: session start, prerequisites
status (OK/SKIP for each of companion, cli, auth), working directory.

**2d. pipeline.config.md.** Copy from project root template if it exists.
Otherwise create with these defaults (ask user to confirm/adjust):

```markdown
# Pipeline Configuration
## Project
- repo_root: <detected from git>
- base_branch: main
## Verification
- typecheck: tsc --noEmit
- lint: npm run lint
- test: npm test
- build: npm run build
## Codex
- review_effort: medium
- model: (default)
```

---

## 3. Phase Routing

Execute phases sequentially. Each phase writes numbered output files to the
session directory. Log every phase transition to `session.log`.

### Phase 1: Design

Invoke the `design` skill with `session_dir`.

**Input:** User's feature description.
**Output:** `01-spec.md`. Log completion with line count.

**GATE:** Present the spec to the user. Iterate on edits until explicit
approval ("approved", "LGTM", "go"). Log: `User approved spec`.

### Phase 2: Codex Review Spec

**Skip:** If `CODEX_AVAILABLE=false`, log skip, jump to Phase 3.

Invoke `codex-review` with `review_type=spec`, `input_file=01-spec.md`,
`session_dir`. Show **"Codex is reviewing the spec..."** and wait (foreground).

**Output:** `02-codex-review-spec.md`. **Present Decision Point #1** (section 4).

### Phase 3: Plan

Invoke `plan` skill.

**Input:** `03-spec-v2.md` if Decision #1 produced a v2, else `01-spec.md`.
**Output:** `04-plan.md`. Log completion with line count.

### Phase 4: Codex Review Plan

Same as Phase 2 but `review_type=plan`, input `04-plan.md`.
**Output:** `05-codex-review-plan.md`. **Present Decision Point #2.**
If corrections: write `06-plan-v2.md`.

### Phase 5: Execute

Invoke `execute` skill.

**Input:** `06-plan-v2.md` if Decision #2 produced a v2, else `04-plan.md`.
**Output:** Committed code. Log commit range (`Commits: <first>..<last>`).
Store range for Phase 6.

### Phase 6: Codex Review Implementation

Same as Phase 2 but `review_type=impl`. Pass additional context:
- `commit_list`: SHAs from Phase 5
- `base_ref`: `base_branch` from `pipeline.config.md`

**Output:** `07-codex-review-impl.md`. **Present Decision Point #3** (section 4).

### Phase 7: Verify

Invoke `verify` skill with commands from `pipeline.config.md`.

**Output:** Summary table (command, PASS/FAIL, exit code, duration).
Log: `Phase 7 complete: verify -- typecheck=X, lint=X, test=X, build=X`.

If any fail, present failures and ask: fix + re-verify, skip, or abort.

---

## 4. Decision Points

Decision points are presented after each Codex review. They follow the same
structure but with context-appropriate options.

### Decision Points #1 and #2 (after spec / plan review)

Show a brief summary of Codex findings (count of issues by severity, key
themes). Then present:

```
Codex found <N> items (<X> high, <Y> medium, <Z> low).

How would you like to proceed?

  A. Integrate all findings — Claude corrects the spec/plan and writes
     <03-spec-v2.md / 06-plan-v2.md>
  B. Integrate some findings — tell me which ones to apply
  C. Ignore the review, continue with the current spec/plan
  D. Ask Codex to dig deeper on a specific point
  E. Edit the spec/plan yourself

Or type a free-form comment and I will adapt.
```

**Handling each option:**

- **A:** Read all findings from the review file. Apply every correction to
  produce the v2 document. Do NOT re-submit to Codex automatically.
- **B:** Ask the user which findings to apply (by number or description).
  Apply only those. Write the v2 document.
- **C:** Continue to the next phase with the current document unchanged.
- **D:** Ask the user what specific point to investigate. Invoke `codex-review`
  again with a focused prompt. Write the result as an addendum to the existing
  review file (append, do not overwrite). Then re-present the decision point.
- **E:** Tell the user to edit the file directly. Wait for them to confirm
  they are done. Re-read the file and continue.

**Free-form input:** If the user types anything that is not A-E, treat it as
a comment. Interpret their intent and act accordingly. Log what was decided.

Log the decision:

```
[<ISO-8601>] Decision #<N>: <choice> (<summary>)
```

### Decision Point #3 (after implementation review)

Same structure but with implementation-specific options:

```
Codex found <N> items (<X> high, <Y> medium, <Z> low).

How would you like to proceed?

  A. Claude fixes all findings — creates a new commit
  B. Fix some findings — tell me which ones to fix
  C. Ignore, proceed to verification
  D. Ask Codex to dig deeper on a potential bug
  E. Run a project-specific audit

Or type a free-form comment and I will adapt.
```

Option E here invokes an appropriate audit skill based on the nature of the
findings. Ask the user which audit to run if ambiguous.

---

## 5. Session Log Format

Format: `[<ISO-8601>] <event>` -- append-only, never truncate. Example:

```
[2026-04-06T14:30:00] Session started: search-filter
[2026-04-06T14:30:01] Prerequisites: codex=OK, companion=OK, auth=OK
[2026-04-06T14:30:01] Working directory: /home/user/my-project
[2026-04-06T14:35:00] Phase 1 complete: 01-spec.md written (87 lines)
[2026-04-06T14:35:30] User approved spec
[2026-04-06T14:40:00] Codex review started (type: spec)
[2026-04-06T14:45:00] Codex review complete: 02-codex-review-spec.md
[2026-04-06T14:45:30] Decision #1: A (integrate all findings)
[2026-04-06T14:46:00] Wrote 03-spec-v2.md (94 lines)
[2026-04-06T14:50:00] Phase 3 complete: 04-plan.md written (142 lines)
[2026-04-06T14:55:00] Codex review started (type: plan)
[2026-04-06T15:00:00] Codex review complete: 05-codex-review-plan.md
[2026-04-06T15:00:30] Decision #2: C (ignore review, continue with current plan)
[2026-04-06T15:15:00] Phase 5 complete: execute
[2026-04-06T15:15:00] Commits: abc1234..def5678 (3 commits)
[2026-04-06T15:25:30] Decision #3: A (fix all findings)
[2026-04-06T15:30:00] Phase 7 complete: verify — typecheck=PASS, lint=PASS, test=PASS, build=PASS
[2026-04-06T15:30:01] Pipeline complete
```

---

## 6. Resumption

If the pipeline is interrupted (crash, timeout, user closes session), it can
be resumed. On invocation, check for existing sessions:

1. Look for directories matching `docs/cloco-sessions/YYYY-MM-DD-*`.
2. For each, read `session.log` and find the last completed phase.
3. If an incomplete session exists from today, ask the user:

```
Found incomplete session: <slug> (last completed: Phase <N>).
  R. Resume from Phase <N+1>
  N. Start a new session
  V. View the session log
```

To resume, re-read all existing artifacts from the session directory and
pick up from the next phase. Do NOT re-run completed phases.

---

## 7. Brainstorm Directory

When brainstorming or exploring ideas before committing to a pipeline session,
use `.cloco/brainstorm/` as the scratch space. Files here are ephemeral and
not tracked in session logs. Once the user commits to a feature, move relevant
content into the session directory as `01-spec.md`.

---

## 8. Important Rules

1. **No automatic re-review.** After applying corrections (option A or B at a
   decision point), do NOT automatically re-submit to Codex. The user controls
   iteration via option D. This prevents review loops.

2. **Codex reviews are foreground.** Claude waits for the Codex result and
   shows a "Codex is reviewing..." message. Do not run reviews in the
   background or proceed without the result.

3. **Free-form input at decision points.** If the user types something other
   than A-E, do not reject it. Interpret their intent, act on it, and log
   what was decided using their own words.

4. **Numbered filenames.** Every artifact uses a two-digit prefix matching its
   phase position. This makes the session directory self-documenting:
   ```
   01-spec.md
   02-codex-review-spec.md
   03-spec-v2.md           (only if Decision #1 = A or B)
   04-plan.md
   05-codex-review-plan.md
   06-plan-v2.md           (only if Decision #2 = A or B)
   07-codex-review-impl.md
   ```

5. **Session directory is the single source of truth.** All skill invocations
   read from and write to the session directory. Do not scatter artifacts
   across other locations.

6. **Graceful Codex degradation.** When `CODEX_AVAILABLE=false`, phases 2, 4,
   and 6 are skipped entirely. The pipeline becomes: design -> plan -> execute
   -> verify. Decision points are skipped. Log each skip.

7. **Do not modify pipeline.config.md during execution.** It is set once at
   session creation. If the user needs to change verification commands or
   base_branch mid-pipeline, they edit it directly and confirm.

8. **Log everything.** Every phase start, phase end, decision, file write,
   skip, error, and user comment goes into `session.log`. This is the audit
   trail.

9. **Skill invocation pattern.** When invoking sub-skills (design, plan,
   codex-review, execute, verify), always pass `session_dir` so they know
   where to write their output. Each skill is responsible for writing its own
   numbered file. The pipeline orchestrator reads the result after the skill
   completes.

10. **Completion.** After Phase 7 (or after the last non-skipped phase),
    append `[<ISO-8601>] Pipeline complete` to the session log and print a
    final summary showing all phases, their statuses, and the session
    directory path.
