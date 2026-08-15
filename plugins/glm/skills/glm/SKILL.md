---
name: glm
description: Use GLM 5.3 through the Z.ai Coding Plan Anthropic-compatible API as a complete companion from Codex or Claude Code. Trigger on `$glm` in Codex, `/glm` in Claude, requests to delegate to GLM, independent GLM implementation/debugging/research/planning/review, conversation transfer, or GLM setup/status/result/resume/cancel. Supports foreground/background jobs, visible host context, read-only/write modes, structured and adversarial reviews, resumable sessions, and optional stop-review gates.
---

# GLM Companion

Resolve `../../scripts/glm_companion.py` relative to this file and use it as the
only runtime entry point. Pass `--host codex` when running inside Codex and
`--host claude` when running inside Claude Code. Never invoke Z.ai or
`claude -p` directly.

## Route `$glm` or `/glm`

| Intent | Runtime command |
|---|---|
| task, ask, implement, fix, investigate | `task` |
| continue, resume | `task --resume-last` |
| setup, key, enable/disable gate | `setup` |
| review | `review` |
| adversarial review, challenge | `adversarial-review` |
| transfer this conversation | `transfer` |
| jobs, progress, status | `status` |
| result, output | `result` |
| cancel, stop | `cancel` |

If the user writes only `$glm`, ask what GLM should do.

## Delegate

- Fresh tasks automatically include visible user/host-agent messages when the
  current transcript can be identified. Hidden instructions, private reasoning,
  tool traces, attachments, and secrets are excluded.
- Add `--write` only for explicit implementation or mutation requests.
  Diagnosis, planning, research, and reviews remain read-only.
- Use foreground for bounded work and `--background` for long or explicitly
  asynchronous work. Never combine `--background` and `--wait`.
- Use `--resume-last` for an obvious follow-up. Use `--no-context` only when the
  user requests isolation.
- Leave model, effort, budget, and timeout unset unless requested. The runtime
  tries `glm-5.3` first and transparently falls back to `glm-5.2` only when
  Z.ai rate-limits the preferred model. The result always reports a fallback.

```bash
python3 <runtime> task --host <codex|claude> --wait -- "Investigate and report evidence."
python3 <runtime> task --host <codex|claude> --background --write -- "Implement and verify the fix."
python3 <runtime> task --host <codex|claude> --resume-last --write -- "Continue the implementation."
```

Use stdin or a safely quoted argument for arbitrary user text.

## Transfer and review

`transfer` seeds a resumable GLM session with the visible host conversation.
`review` and `adversarial-review` are read-only and return structured findings.

```bash
python3 <runtime> transfer --host <codex|claude> --wait
python3 <runtime> review --host <codex|claude> --scope auto --wait
python3 <runtime> adversarial-review --host <codex|claude> --base main --wait "Focus on data loss"
```

Present findings without applying them until the user authorizes fixes.

## Control and setup

```bash
python3 <runtime> setup --host <codex|claude>
python3 <runtime> status --host <codex|claude>
python3 <runtime> status --host <codex|claude> <job-id> --wait
python3 <runtime> result --host <codex|claude> <job-id>
python3 <runtime> cancel --host <codex|claude> <job-id>
python3 <runtime> setup --host <codex|claude> --enable-review-gate
```

The runtime looks first in the user-owned `~/.glm.env` secret file (mode 0600),
then for `ZAI_API_KEY`, `GLM_API_KEY`, and the same keys in the workspace `.env`.
Never print the key. Leave the stop gate disabled unless explicitly requested.

After write-capable work, inspect the real diff and run proportionate checks.
GLM output is evidence, not automatic proof.
