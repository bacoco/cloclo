# Session Files — Structure, Logs, Checkpoints, Handoff

## Directory Structure

```
docs/cloclo-sessions/YYYY-MM-DD-<slug>/
├── 01-spec.md                      ← from superpowers:brainstorming
├── 02-codex-review-spec.md         ← from codex-review skill
├── 03-spec-v2.md                   ← if corrections after review
├── 04-plan.md                      ← from superpowers:writing-plans
├── 05-codex-review-plan.md         ← from codex-review skill
├── 06-plan-v2.md                   ← if corrections after review
├── 07-codex-review-impl.md         ← from codex-review skill
├── 07b-coderabbit-review-impl.md   ← from coderabbit-review skill (Phase 6.5)
├── 08-task-dag.md                  ← from Phase 4.5
├── 09-compliance-report.md         ← AC-level coverage (Phase 7)
├── task-briefs/
│   ├── task-1.md
│   └── task-2.md
├── screenshots/                    ← visual verification evidence (Phase 7.5)
│   ├── page-name-01.png
│   └── page-name-02.png
├── session.log                     ← decisions + timestamps + job-ids
├── checkpoint.json                 ← resume state after each phase
├── handoff.md                      ← auto-written at end of every run
└── pipeline.config.md              ← optional verification config
```

## Session Log Format

One line per event. Timestamps are ISO 8601 UTC.

```
[2026-04-06T14:30:00] CLoClo session started: auth-refactor
[2026-04-06T14:30:01] Prerequisites: superpowers=OK, codex=OK, coderabbit=OK
[2026-04-06T14:45:00] Phase 1 complete: 01-spec.md
[2026-04-06T14:45:30] User approved spec
[2026-04-06T14:50:00] Codex review spec started (job-id: task-abc123)
[2026-04-06T14:55:00] Codex review spec complete: 02-codex-review-spec.md
[2026-04-06T14:55:30] Decision #1: A (integrate all)
[2026-04-06T14:58:00] Spec corrected: 03-spec-v2.md
[2026-04-06T15:10:00] Phase 3 complete: 04-plan.md
[2026-04-06T15:15:00] Codex review plan started (job-id: task-def456)
[2026-04-06T15:22:00] Codex review plan complete: 05-codex-review-plan.md
[2026-04-06T15:22:30] Decision #2: B (integrate findings 1,3; ignore 2)
[2026-04-06T15:25:00] Plan corrected: 06-plan-v2.md
[2026-04-06T15:26:00] Phase 5 started (base_ref: a1b2c3d)
[2026-04-06T15:45:00] Phase 5 complete: 5 commits (a1b..f6e)
[2026-04-06T15:50:00] Codex review impl started (job-id: task-ghi789)
[2026-04-06T16:02:00] Codex review impl complete: 07-codex-review-impl.md
[2026-04-06T16:02:30] Decision #3: A (fix all)
[2026-04-06T16:05:00] CodeRabbit review started
[2026-04-06T16:07:00] CodeRabbit review complete: 07b-coderabbit-review-impl.md (3 high, 5 medium, 12 low)
[2026-04-06T16:07:30] Decision #3b: B (fix 2 high, ignore nits)
[2026-04-06T16:10:00] Phase 7: VERIFICATION_PASSED | AC coverage: 8/8
```

## Checkpoint Format

Written to `{session_dir}/checkpoint.json` after each phase succeeds:

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
  "retries": {"phase_2": 0, "phase_4": 0, "phase_6_5": 0}
}
```

### Resume Behavior

On pipeline start, if `checkpoint.json` exists in session dir:
1. Show: `"Resuming session \"{slug}\" from Phase {N+1}. Last completed: Phase {N} at {time}."`
2. Ask: `"Reprendre a partir de Phase {N+1} ? (oui/non/restart)"`
3. `oui` → skip to Phase N+1 with checkpoint artifacts
4. `restart` → delete checkpoint, start from Phase 1
5. `non` → ask what to do

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
- Decision #1: {choice} — {reason}
- Decision #2: {choice} — {reason}

## Files to read for context
- Spec: {path}
- Plan: {path}
- Reviews: {paths}
```

This enables a new Claude session to pick up where the previous left off by
reading `handoff.md` instead of replaying the entire conversation.
