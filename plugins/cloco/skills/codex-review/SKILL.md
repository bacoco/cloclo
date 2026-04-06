---
name: codex-review
description: "Invoke Codex (GPT-5.4) to review a spec, plan, or implementation. Codex explores the codebase freely and writes findings to a file. Foreground execution — Claude waits for result."
user-invocable: false
---

# codex-review

Invoke the Codex companion (GPT-5.4) to produce an independent review of a spec,
plan, or implementation. Codex has full codebase access and writes its findings to
a file that Claude reads back verbatim.

## 1. Context Reception

The calling skill (typically `pipeline`) passes:

| Parameter     | Required for          | Description                                      |
|---------------|-----------------------|--------------------------------------------------|
| `review_type` | all                   | One of `spec`, `plan`, `impl`                    |
| `session_dir` | all                   | Absolute path to the session directory            |
| `input_file`  | all                   | Path to the artifact under review                |
| `output_file` | all                   | Path where Codex must write its review            |
| `spec_path`   | `plan`, `impl`        | Path to the approved spec                        |
| `plan_path`   | `impl`                | Path to the approved plan                        |
| `base_ref`    | `impl`                | Git ref before implementation started            |
| `commit_list` | `impl`                | Space-separated commit hashes to review          |

## 2. Prerequisites Check

First, verify that the Codex CLI is installed:

```bash
# Check Codex CLI availability
if ! command -v codex &>/dev/null; then
  echo "Codex CLI not found. Install it with: npm install -g @openai/codex"
  # return CODEX_UNAVAILABLE
fi
```

Then, locate the companion script:

```bash
# Find companion
CODEX_COMPANION_PATH="${CODEX_COMPANION_PATH:-$(find ~/.claude/plugins -name codex-companion.mjs -path '*/codex/scripts/*' 2>/dev/null | head -1)}"

# If not found: return CODEX_UNAVAILABLE
# Check auth: codex whoami
# If not authenticated: return CODEX_NOT_AUTHENTICATED
```

If the Codex CLI is not installed, return status `CODEX_UNAVAILABLE` with the message:
"Codex CLI not found. Install it with: `npm install -g @openai/codex`"

If `CODEX_COMPANION_PATH` resolves to nothing, return status `CODEX_UNAVAILABLE` with
the message: "Codex companion not found. Install the Codex plugin from the Claude Code marketplace."

If `codex whoami` fails, return status `CODEX_NOT_AUTHENTICATED` with the message:
"Codex is not authenticated. Run `codex login` first."

## 3. Prompt Construction

1. Read the template matching the review type:
   `${SKILL_DIR}/templates/review-{review_type}-prompt.md`
2. Replace placeholders with actual values:
   - `{{SPEC_PATH}}` -- path to the spec
   - `{{PLAN_PATH}}` -- path to the plan
   - `{{OUTPUT_PATH}}` -- path where Codex writes its review
   - `{{BASE_REF}}` -- git ref before implementation
   - `{{COMMIT_LIST}}` -- space-separated commit hashes
3. Write the resolved prompt to a temp file:
   `/tmp/cloco-codex-prompt-$(date +%s).md`

Only placeholders present in the template are replaced. Missing placeholders for
the given review type are an error in the template, not in the skill.

## 4. Execution (FOREGROUND)

```bash
node "$CODEX_COMPANION_PATH" task --write --prompt-file /tmp/cloco-codex-prompt-{timestamp}.md
```

- Print to the user: "Codex is reviewing... (this takes 2-10 minutes)"
- Block until the Codex process exits
- Delete the temp prompt file after completion regardless of exit code

This is a **foreground** call. Claude does not proceed until Codex finishes.
No background promises, no polling loops.

## 5. Result Handling

After Codex exits, check whether `output_file` exists and is non-empty.

**Success path:**
- Read `output_file` in its entirety
- Return the raw content to the calling skill -- no summarization, no reformatting
- Log to `${session_dir}/session.log`:
  ```
  [2026-04-06T14:32:01] Codex review (type=spec) started (job-id: abc123)
  [2026-04-06T14:34:47] Codex review complete: /path/to/output_file
  ```

**Failure path:**
- Return status `CODEX_REVIEW_FAILED` with whatever stderr or exit code Codex produced
- Log the failure to `session.log` with the same format
- Do NOT retry automatically

## 6. Important Rules

- **NEVER summarize or filter Codex findings.** The calling skill receives the raw
  file exactly as Codex wrote it. Post-processing destroys signal.
- **NEVER re-run Codex automatically.** If the review is unsatisfactory, the user
  decides whether to iterate. One invocation per skill call.
- **If Codex fails, warn and return.** Do not block the pipeline. The calling skill
  handles degraded mode (proceed without review or abort).
- **Foreground ONLY.** No `run_in_background`, no `&`, no detached processes.
  Claude waits, reads the result, and continues.
- **Clean up temp files.** The resolved prompt in `/tmp/` is deleted after execution.
  The output file in `session_dir/` is permanent.
