---
name: codex-review
description: "Use when the pipeline needs an independent review of a spec, plan, or implementation via the Codex CLI (falls back to a Claude subagent when Codex is unavailable)."
user-invocable: false
---

# codex-review

Review a spec, plan, or implementation with Codex (`codex exec`, read-only OS
sandbox). If Codex is unavailable (CLI missing, usage limits, runtime error), a
Claude subagent reviews instead. Either way, findings are written to `output_file`,
which the calling skill reads back verbatim.

The shared review policy — evidence tags, severities, the adversarial pass,
severity escalation, the consensus matrix, the convergence loop, the
auto-integration gates, the CodeRabbit `nit`→P2 mapping, and escalation triggers —
lives in
[`../pipeline/references/review-chain.md`](../pipeline/references/review-chain.md).
This skill covers only the Codex-specific mechanics; do not restate the shared
rules here.

## 1. Context Reception

The calling skill (typically `pipeline`) passes:

| Parameter     | Required for   | Description                                             |
|---------------|----------------|--------------------------------------------------------|
| `review_type` | all            | One of `spec`, `plan`, `impl`                           |
| `session_dir` | all            | Absolute path to the session directory                 |
| `input_file`  | all            | Path to the artifact under review                      |
| `output_file` | all            | Path where the review must be written                  |
| `spec_path`   | `plan`, `impl` | Path to the approved spec                              |
| `plan_path`   | `impl`         | Path to the approved plan                              |
| `base_ref`    | `impl`         | Git ref before implementation started                  |
| `commit_list` | `impl`         | Space-separated commit hashes to review                |
| `maturity`    | all            | `spike`/`dev`/`ship` — gates the adversarial pass (see review-chain) |
| `iterate`     | optional       | When true, run the convergence loop (see review-chain) instead of a single pass |

## 2. Try Codex First

### Prerequisites

```bash
command -v codex &>/dev/null || CODEX_UNAVAILABLE=1
# Auth is managed by Codex CLI internally — do NOT check codex whoami or OPENAI_API_KEY
```

### Prompt construction

1. Read `${SKILL_DIR}/templates/review-{review_type}-prompt.md`.
2. Resolve placeholders per this mapping (templates use `{{SPEC_PATH}}` /
   `{{PLAN_PATH}}` — there is no `{{INPUT_FILE}}`):

   | `review_type` | Placeholder ← source |
   |---------------|----------------------|
   | `spec` | `{{SPEC_PATH}}` ← `input_file` |
   | `plan` | `{{PLAN_PATH}}` ← `input_file`; `{{SPEC_PATH}}` ← `spec_path` |
   | `impl` | `{{SPEC_PATH}}` ← `spec_path`; `{{PLAN_PATH}}` ← `plan_path`; `{{BASE_REF}}` ← `base_ref`; `{{COMMIT_LIST}}` ← `commit_list`. For `impl`, `input_file` *is* the diff `base_ref..HEAD`, which the reviewer computes with `git diff` — it is not substituted into a placeholder. |
   | all | `{{OUTPUT_PATH}}` ← `output_file` |

3. Write the resolved prompt to `/tmp/cloclo-codex-prompt-$(date +%s).md`
   (referenced below as `$PROMPT_FILE`).

### Execution (FOREGROUND)

```bash
echo "Codex is reviewing (read-only sandbox)... output -> $output_file"

# Pre-clear stale review file so the post-run guard can't validate old content
# as success.
rm -f "$output_file"

# `< /dev/null` is MANDATORY: in a non-interactive shell (background subshell, CI
# job, inherited pipe) codex-cli blocks forever on "Reading additional input from
# stdin...". Closing stdin forces it to start from the positional prompt alone.
# `timeout 900` caps a stuck session at 15 minutes.
timeout 900 codex exec \
  -s read-only \
  -o "$output_file" \
  "$(cat "$PROMPT_FILE")" \
  < /dev/null \
  > "${output_file}.runtime.log" 2>&1
CODEX_EXIT=$?

rm -f "$PROMPT_FILE"
```

- `-s read-only` — **OS-level sandbox**. Codex has full read access to the repo
  (source, git history, CLAUDE.md); writes are blocked at the kernel level. Belt +
  suspenders with the template's "don't modify code" instruction.
- `-o "$output_file"` — the final agent message is captured directly into the
  review file (no stdout pollution, no tool call needed). This removes the old
  "Codex forgot to call its write tool → empty file despite exit 0" failure mode.
- `> "${output_file}.runtime.log" 2>&1` — stdout + stderr (auth/quota/network
  diagnostics) go to the sibling runtime log; `$output_file` holds only the review.

### Result check (mandatory post-run guard)

```bash
if [ $CODEX_EXIT -eq 0 ] && [ -s "$output_file" ] \
   && grep -qiE 'Verdict.*(PASS|CONCERNS|FAIL)' "$output_file"; then
  echo "[codex-review] OK: $output_file"
else
  echo "[codex-review] FAIL: exit=$CODEX_EXIT, empty/missing/no-verdict. Falling back to Claude." >&2
  # fall through to the Claude fallback (section 3)
fi
```

The verdict sniff rejects auth-error / refusal text that would otherwise pass the
`[ -s ]` check. Log to `session.log` either way.

## 3. Claude Fallback

When Codex is unavailable or fails the guard, dispatch a Claude subagent to review.

**Subagent type:** use `superpowers:code-reviewer` if it appears in your available
agent types — this is known to the running session, not something you can query
from the shell (there is no such CLI subcommand; do not try to discover it via
bash). Otherwise use `general-purpose`.

**Model:** always `opus` for the fallback review. Do not downgrade to Sonnet —
reviews are where the model gap catches real bugs.

**Prompt:** reuse the *same* resolved template from §2
(`templates/review-{review_type}-prompt.md`, same placeholder substitution) as the
single source of truth. Do not hand-write a separate fallback prompt — the template
already covers both runtimes (its OBJECTIF FINAL block tells a Write-capable
runtime to call Write on `{{OUTPUT_PATH}}` before concluding).

```bash
rm -f "$output_file"   # pre-clear, same guarantee as the Codex path
```

```
Agent(
  subagent_type: <selected above>,
  model: "opus",
  prompt: <resolved templates/review-{review_type}-prompt.md>
)
```

After dispatch, apply the same result guard as §2 (exit 0 + non-empty + verdict
sniff). If the subagent also fails, warn and return — never skip the review
silently.

## 4. Result Handling

- Read `output_file` in its entirety.
- Return raw content to the calling skill — no summarization, no reformatting.
- Log to `session.log`:
  ```
  [timestamp] Review (type=spec|plan|impl, engine=codex|claude) complete: /path/to/output_file
  ```

## 5. Shared Review Policy — see review-chain.md

The following are defined once in
[`../pipeline/references/review-chain.md`](../pipeline/references/review-chain.md).
Follow it; do not duplicate:

- **Adversarial triple-perspective pass** (Skeptic / Devil's Advocate /
  Edge-Case Hunter), including when it runs per maturity.
- **Evidence tagging** — `[TOOL]` / `[CODE]` / `[LLM-JUDGMENT]` on every finding,
  plus the low-evidence warning.
- **Severities** P0 / P1 / P2 and **severity escalation** across reviewers.
- **Consensus matrix** and `[DISAGREEMENT]` / `[CONSENSUS]` handling for
  multi-model reviews.
- **Convergence loop** when `iterate` is set.
- **Auto-integration gates, escalation triggers, and the CodeRabbit `nit`→P2
  mapping.**

## 6. Important Rules

- **NEVER summarize or filter findings.** Return the raw file as written.
- **NEVER skip the review entirely.** Codex fails → Claude reviews; Claude fails →
  warn and return.
- **Foreground only.** No background promises, no polling loops.
- **Clean up temp files.** The `/tmp` prompt is deleted; `output_file` in
  `session_dir/` is permanent.
- **Log which engine was used** (codex vs claude) so the caller and user know.
- **Tag every finding** per review-chain.md — no untagged findings.
