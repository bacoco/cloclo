---
name: claude
description: Use the local Claude Code CLI as a full companion from Codex. Trigger when the user writes `$claude`, asks Claude to implement, debug, investigate, plan, research, review, challenge, or continue work, wants the current Codex conversation transferred to Claude, or asks to setup, monitor, retrieve, wait for, resume, or cancel Claude work. Support foreground/background jobs, visible-thread context transfer, read-only/write modes, structured reviews, resumable sessions, status/result/cancel, and the optional stop-review gate.
---

# Claude Companion

Resolve `../../scripts/claude_companion.py` relative to this file and use it as
the only runtime entry point. Never invoke `claude` directly.

## Route `$claude`

Interpret the first intent after `$claude` as follows:

| Intent | Runtime command |
|---|---|
| task, rescue, ask, implement, fix | `task` |
| continue, resume, keep going | `task --resume-last` |
| setup, auth, enable/disable gate | `setup` |
| review | `review` |
| adversarial review, challenge | `adversarial-review` |
| transfer this conversation | `transfer` |
| progress, jobs, status | `status` |
| result, output | `result` |
| cancel, stop job | `cancel` |

If the user writes only `$claude`, ask what Claude should do.

## Delegate tasks

- Fresh tasks automatically include the current visible Codex conversation.
  The exporter includes user and Codex messages but excludes hidden
  system/developer instructions, private reasoning, and raw tool traces.
- Add `--write` only when the user explicitly requests implementation, edits,
  fixes, or other mutations. Reviews, diagnosis, research, and planning stay
  read-only.
- Leave model, effort, budget, and timeout unset unless the user requests them.
- Use foreground for a small bounded task. Use `--background` for complicated,
  open-ended, or multi-step work, or when the user explicitly asks for it.
- Preserve `--wait` and `--background` choices. Never pass both.
- Use `--resume-last` for a clear follow-up. Use `--fresh` when explicitly
  requested. Do not retransmit the whole transcript on an ordinary resume.
- Use `--no-context` only when the user explicitly wants an isolated fresh
  Claude task. Use `--source <codex-jsonl>` only for an explicit transcript.

Examples:

```bash
python3 <runtime> task --wait -- "Investigate the failing test and report evidence."
python3 <runtime> task --background --write -- "Implement the requested fix and verify it."
python3 <runtime> task --resume-last --write -- "Continue and fix the remaining issue."
```

Pass arbitrary user text through stdin when shell quoting could be unsafe.

## Transfer the Codex conversation

Run `transfer` to create a resumable Claude session seeded with the entire
visible Codex turn history:

```bash
python3 <runtime> transfer --wait
```

Return the Claude session ID and `claude --resume <id>` command unchanged.
This is the explicit handoff equivalent of the source plugin's transfer flow.

## Run reviews

Use `review` for material defects and `adversarial-review` to challenge the
approach, assumptions, and design. Both are read-only and return structured
findings with severity, file, line, confidence, and recommendation.

```bash
python3 <runtime> review --background --scope auto
python3 <runtime> adversarial-review --wait --base main "Focus on retries and data loss"
```

After presenting review findings, stop. Do not apply recommendations unless the
user separately authorizes fixes.

## Control jobs

```bash
python3 <runtime> status
python3 <runtime> status <job-id> --wait
python3 <runtime> result <job-id>
python3 <runtime> cancel <job-id>
python3 <runtime> task-resume-candidate --json
```

Keep job IDs exact. Report failures, permission denials, malformed structured
output, and timeouts without inventing substitute Claude results.

## Setup and review gate

```bash
python3 <runtime> setup
python3 <runtime> setup --enable-review-gate
python3 <runtime> setup --disable-review-gate
```

The optional stop gate asks Claude to review code changes from the immediately
previous Codex turn before allowing the session to stop. Leave it disabled
unless the user explicitly enables it.

## Verify delegated edits

Claude and Codex share the same workspace. After write-capable work completes,
inspect the actual diff, preserve unrelated user changes, and run proportionate
verification before Codex claims completion. Claude's output is evidence, not
automatic proof.
