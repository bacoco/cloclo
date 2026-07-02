# Session Files — Structure, Logs, Checkpoints, Handoff

## Directory Structure

```
docs/cloclo-sessions/YYYY-MM-DD-<slug>/
├── 01-spec.md                      ← from superpowers:brainstorming
├── 02-codex-review-spec.md         ← from codex-review skill
├── 02-glm-review-spec.md           ← from glm-review skill (parallel with Codex)
├── 02-codex-review-spec.md.runtime.log  ← stderr from codex exec
├── 02-glm-review-spec.md.runtime.log    ← stderr from claude -p (GLM)
├── 03-spec-v2.md                   ← if corrections after review
├── 04-plan.md                      ← from superpowers:writing-plans
├── 05-codex-review-plan.md         ← from codex-review skill
├── 05-glm-review-plan.md           ← from glm-review skill (parallel)
├── 06-plan-v2.md                   ← if corrections after review
├── 07-codex-review-impl.md         ← from codex-review skill
├── 07-glm-review-impl.md           ← from glm-review skill (parallel)
├── 07b-coderabbit-review-impl.md   ← from coderabbit-review skill (Phase 6.5)
├── 08-task-dag.md                  ← from Phase 4.5
├── 09-compliance-report.md         ← AC-level coverage (Phase 7)
├── 10-pr-bot-digest.md             ← consolidated PR bot findings (Phase 9)
├── 11-glm-post-merge-review.md     ← post-merge GLM pass (Phase 9.5)
├── task-briefs/
│   ├── task-1.md
│   └── task-2.md
├── screenshots/                    ← visual verification evidence (Phase 7.5)
│   ├── page-name-01.png
│   └── page-name-02.png
├── .bak/                           ← prior session dir, saved before a "refais tout" reset
├── session.log                     ← events + timestamps + job-ids
├── checkpoint.json                 ← resume state after each phase
├── handoff.md                      ← auto-written at end of every run
└── pipeline.config.md              ← optional verification config
```

**Runtime logs**: every reviewer (codex-review, glm-review, coderabbit-review) writes its process stderr to `{output_file}.runtime.log` — a sibling of the review `.md` file. This is the ONE runtime-log naming convention (there is no separate `0X-codex.runtime.log` form). The review content itself lives in the `.md` file. If a review fails (empty file), the runtime log is the first place to look for diagnostics.

## Session Log Format

One line per event. Timestamps are ISO 8601 UTC.

```
[2026-04-06T14:30:00] CLoClo session started: auth-refactor
[2026-04-06T14:30:01] Prerequisites: superpowers=OK, codex=OK, coderabbit=OK
[2026-04-06T14:45:00] Phase 1 complete: 01-spec.md
[2026-04-06T14:45:30] User approved spec
[2026-04-06T14:50:00] Codex review spec started (job-id: task-abc123)
[2026-04-06T14:55:00] Codex review spec complete: 02-codex-review-spec.md
[2026-04-06T14:55:30] Phase 2 auto-integrate: 3 applied, 1 skipped, 0 escalated
[2026-04-06T14:58:00] Spec corrected: 03-spec-v2.md
[2026-04-06T15:10:00] Phase 3 complete: 04-plan.md
[2026-04-06T15:15:00] Codex review plan started (job-id: task-def456)
[2026-04-06T15:22:00] Codex review plan complete: 05-codex-review-plan.md
[2026-04-06T15:22:30] Phase 4 auto-integrate: 2 applied, 1 skipped, 0 escalated
[2026-04-06T15:25:00] Plan corrected: 06-plan-v2.md
[2026-04-06T15:26:00] Phase 5 started (base_ref: a1b2c3d)
[2026-04-06T15:45:00] Phase 5 complete: 5 commits (a1b..f6e)
[2026-04-06T15:50:00] Codex review impl started (job-id: task-ghi789)
[2026-04-06T16:02:00] Codex review impl complete: 07-codex-review-impl.md
[2026-04-06T16:02:30] Phase 6 auto-integrate: 4 applied, 2 skipped, 0 escalated
[2026-04-06T16:05:00] CodeRabbit review started
[2026-04-06T16:07:00] CodeRabbit review complete: 07b-coderabbit-review-impl.md (3 P1, 17 P2)
[2026-04-06T16:07:30] Phase 6.5 auto-integrate: 2 applied, 18 skipped (P2 advisory), 0 escalated
[2026-04-06T16:10:00] Phase 7: VERIFICATION_PASSED | AC coverage: 8/8
```

## Checkpoint Format

Written to `{session_dir}/checkpoint.json` after each phase succeeds:

```json
{
  "session": "2026-04-16-auth-refactor",
  "maturity": "dev",
  "completed_phases": ["1", "2", "3", "4", "4.5"],
  "last_completed_at": "2026-04-16T15:22:00Z",
  "artifacts": {
    "spec": "03-spec-v2.md",
    "plan": "06-plan-v2.md",
    "base_ref": "a1b2c3d",
    "commits": []
  },
  "escalations": [
    {"phase": "4", "question": "spec-plan mismatch on auth flow", "choice": "A", "at": "2026-04-16T15:22:30Z"}
  ],
  "retries": {"phase_2": 0, "phase_4": 0, "phase_6_5": 0}
}
```

`completed_phases` is an **ordered list of phase labels** (strings,
matching the pipeline table: `"1"`, `"2"`, `"3"`, `"4"`, `"4.5"`,
`"5"`, `"6"`, `"6.5"`, `"7"`, `"7.5"`, `"8"`, `"9"`, `"9.5"`). No
numeric arithmetic is ever performed on it.

### Resume Behavior

**`checkpoint.json` is authoritative** (the artifact scan in
`smart-resume.md` is the fallback when it is missing or corrupt).

On pipeline start, if `checkpoint.json` exists and parses:
1. The next phase = the phase that follows the LAST entry of
   `completed_phases` in the canonical order above — a list lookup,
   never `N+1` arithmetic (after `"4.5"` comes `"5"`, after `"6.5"`
   comes `"7"`).
2. Show: `"Resuming session \"{slug}\". Completed: {completed_phases}. Next: Phase {X}."`
3. Ask: `"Resume from Phase {X}? (yes/no/restart)"`
4. `yes` → skip to Phase X with checkpoint artifacts
5. `restart` → delete checkpoint, start from Phase 1
6. `no` → ask what to do

A crash mid-phase only loses that phase's work, not the entire session.

## Handoff Format

Auto-written to `{session_dir}/handoff.md` at end of every run (success or failure):

```markdown
# Session Handoff: {slug}

## Status: {COMPLETED | FAILED_AT_PHASE_N | PARTIAL}

## What was done
- [completed phases with key outcomes]
- Commits: {commit_list}

## What is blocked (if any)
- [phase that failed + reason]
- [unresolved review findings]

## Next recommended action
- [specific next step]

## Key decisions made
- Auto-integrate summary per review phase: {applied}/{skipped}/{escalated}
- Escalations answered: {phase} — {question} → {choice} — {reason}

## Files to read for context
- Spec: {path}
- Plan: {path}
- Reviews: {paths}
```

This enables a new Claude session to pick up where the previous left off by
reading `handoff.md` instead of replaying the entire conversation.
