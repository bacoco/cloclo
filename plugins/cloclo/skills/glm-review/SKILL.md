---
name: glm-review
description: "Review a spec, plan, or implementation using GLM-5.1 via Z.ai's Anthropic-compatible endpoint. Runs `claude -p` with GLM env vars in a child process. No fallback — if the API key is missing or the call fails, the review is skipped (the calling skill proceeds without GLM). Writes findings to a file. Foreground execution."
user-invocable: false
---

# glm-review

Review a spec, plan, or implementation using Zhipu AI's **GLM-5.1** model via the
`api.z.ai/api/anthropic` Anthropic-compatible endpoint. Runs the already-installed
`claude` CLI in a child process with three environment variables overridden so the
tool calls land on Z.ai instead of Anthropic.

Designed to run **in parallel with `codex-review`** so each review phase gets two
independent model opinions. The consensus matrix (see `codex-review` §8) extends
naturally to three reviewers.

**No fallback.** If Z.ai is unreachable or the API key is missing, the review is
skipped with a warning and the calling skill continues without GLM input. This is
intentional — the user's z.ai quota is open-bar, so failures here are always
configuration/network issues, never quota exhaustion worth retrying with a
different model.

## 1. Context Reception

Identical to `codex-review`:

| Parameter     | Required for          | Description                                      |
|---------------|-----------------------|--------------------------------------------------|
| `review_type` | all                   | One of `spec`, `plan`, `impl`                    |
| `session_dir` | all                   | Absolute path to the session directory            |
| `input_file`  | all                   | Path to the artifact under review                |
| `output_file` | all                   | Path where the review must be written             |
| `spec_path`   | `plan`, `impl`        | Path to the approved spec                        |
| `plan_path`   | `impl`                | Path to the approved plan                        |
| `base_ref`    | `impl`                | Git ref before implementation started            |
| `commit_list` | `impl`                | Space-separated commit hashes to review          |

## 2. Prerequisites

### API key lookup (first match wins)

```bash
GLM_KEY=""
for var in ZAI_API_KEY GLM_API_KEY LLM_API_KEY_EXCENIA; do
  val="${!var:-}"
  if [ -n "$val" ]; then GLM_KEY="$val"; break; fi
done

# Project-local fallback: parse $(git rev-parse --show-toplevel)/infra/.env for
# LLM_API_KEY_EXCENIA if the var is still empty. Matches excenia-hub convention.
if [ -z "$GLM_KEY" ] && [ -f "$(git rev-parse --show-toplevel 2>/dev/null)/infra/.env" ]; then
  GLM_KEY=$(grep -E '^LLM_API_KEY_EXCENIA=' "$(git rev-parse --show-toplevel)/infra/.env" | cut -d= -f2-)
fi

if [ -z "$GLM_KEY" ]; then
  echo "[glm-review] No Z.ai API key found (ZAI_API_KEY / GLM_API_KEY / LLM_API_KEY_EXCENIA). Skipping GLM review." >&2
  exit 0   # skip, don't block the pipeline
fi
```

### Claude CLI check

```bash
command -v claude &>/dev/null || {
  echo "[glm-review] claude CLI not installed. Skipping GLM review." >&2
  exit 0
}
```

## 3. Prompt Construction

Same template layout as `codex-review`:

1. Read `${SKILL_DIR}/templates/review-{review_type}-prompt.md`
2. Replace `{{SPEC_PATH}}`, `{{PLAN_PATH}}`, `{{OUTPUT_PATH}}`, `{{BASE_REF}}`, `{{COMMIT_LIST}}`
3. Write resolved prompt to `/tmp/cloclo-glm-prompt-$(date +%s).md`

Templates are intentionally identical between codex-review and glm-review so the
two models see the exact same instructions — any difference in output is pure
model divergence, which is what makes the dual-review useful.

## 4. Execution (FOREGROUND)

**Pattern**: GLM writes the review file itself via the Write tool (symmetric with
Codex). No stdout redirect. The prompt template sets `{{OUTPUT_PATH}}` — the
`acceptEdits` permission mode lets `claude -p` call Write without prompting.

```bash
TS=$(date +%s)
PROMPT_FILE="/tmp/cloclo-glm-prompt-${TS}.md"
# ... resolved template written to PROMPT_FILE above ...

echo "GLM-5.1 is reviewing... (this takes 2-8 minutes). Output: $output_file"

# Pre-clear stale review file — prevents the post-run guard from accepting
# an old file as success when GLM silently skips the Write call.
rm -f "$output_file"

# Stderr routed to sibling runtime log for diagnosability; only $output_file
# is the review content (written by GLM via Write tool).
ANTHROPIC_BASE_URL="https://api.z.ai/api/anthropic" \
ANTHROPIC_AUTH_TOKEN="$GLM_KEY" \
ANTHROPIC_DEFAULT_OPUS_MODEL="glm-5.1" \
ANTHROPIC_DEFAULT_SONNET_MODEL="glm-5.1" \
claude -p --permission-mode acceptEdits "$(cat "$PROMPT_FILE")" \
  > "${output_file}.runtime.log" 2>&1
GLM_EXIT=$?

rm -f "$PROMPT_FILE"
```

**No `> "$output_file"` redirect.** GLM calls Write tool itself, targeting
`{{OUTPUT_PATH}}` resolved inside the prompt. This matches Codex's behavior
(via `codex exec -s read-only -o`) and gives the caller a single file contract: "read
the output_file after the call" — regardless of which reviewer produced it.

### Why the env var pattern works

- `ANTHROPIC_BASE_URL` redirects the CLI's HTTP calls to Z.ai's anthropic-compatible endpoint.
- `ANTHROPIC_AUTH_TOKEN` is sent as the `x-api-key` / `authorization` header — Z.ai accepts its own key in that slot.
- `ANTHROPIC_DEFAULT_OPUS_MODEL` forces the model ID to `glm-5.1` regardless of which Claude alias the CLI requests internally. Setting `SONNET_MODEL` too catches the case where the CLI upgrades/downgrades model aliases mid-session.
- **Only the child process inherits these vars.** The parent Claude Code session (the one running cloclo) keeps its real Anthropic auth untouched. Codex CLI, CodeRabbit CLI, and any other tooling are unaffected.

### Result Check (strict — mandatory post-run guard)

After `claude -p` exits, run this check explicitly:

```bash
if [ $GLM_EXIT -eq 0 ] && [ -s "$output_file" ]; then
  echo "[glm-review] OK: $output_file"
else
  echo "[glm-review] FAIL: exit=$GLM_EXIT, file empty or missing. Skipping GLM for this phase." >&2
  # no fallback — Codex is already running in parallel
fi
```

**Why this is a dedicated guard** : GLM must call the Write tool on `{{OUTPUT_PATH}}` itself — the prompt template's "OBJECTIF FINAL" block demands it, and the `--permission-mode acceptEdits` flag lets the call succeed without prompting. If the file is still empty or missing after exit, either the model skipped the Write tool despite the prompt (rare but possible) or an HTTP/quota error aborted mid-session. The `[ -s "$output_file" ]` check catches both cleanly.

**No fallback to another model** — Codex is already running in parallel and provides the independent voice.

Log to `session.log`:
```
[timestamp] GLM review (type=spec|plan|impl) {complete|failed}: /path/to/output_file
```

## 5. Running in Parallel with codex-review

The pipeline dispatches both reviewers as background jobs and waits for both.
Each reviewer writes its review to its own `output_file` via its native mechanism
(Codex → `codex exec -s read-only -o`, GLM → `claude -p` with `acceptEdits` +
Write tool). The pipeline reads those files after both jobs complete — it never
parses stdout.

```bash
# In the pipeline's Phase 2/4/6 orchestration:
CODEX_OUT="$session_dir/0X-codex-review-XXX.md"
GLM_OUT="$session_dir/0X-glm-review-XXX.md"

# stdout/stderr go to *.runtime.log for debugging only; the review itself is
# written to $CODEX_OUT / $GLM_OUT by the tools.
(invoke codex-review output_file=$CODEX_OUT ... > "$session_dir/0X-codex.runtime.log" 2>&1) &
CODEX_PID=$!

(invoke glm-review output_file=$GLM_OUT ... > "$session_dir/0X-glm.runtime.log" 2>&1) &
GLM_PID=$!

wait $CODEX_PID
CODEX_RC=$?
wait $GLM_PID
GLM_RC=$?

echo "Reviews complete: codex=$CODEX_RC ($CODEX_OUT), glm=$GLM_RC ($GLM_OUT)"
```

The calling skill then reads `$CODEX_OUT` and `$GLM_OUT` and merges findings
through the consensus matrix (see `codex-review` §8, extended to 3 reviewers
when CodeRabbit also runs). **Single file contract: whoever reviewed, the
review is at `output_file`.**

## 6. Findings Format

Identical to `codex-review`. Every finding tagged `[TOOL]`, `[CODE]`, or
`[LLM-JUDGMENT]`. Severity P0/P1/P2. File:line references mandatory.

The consensus matrix in `codex-review` §8 already handles multi-model convergence.
No extra logic needed here — GLM findings plug into the same table.

## 7. Adversarial Triple-Perspective (Optional)

In `ship` maturity, after the GLM review produces its main findings, append the
same adversarial triple-perspective section (`Skeptic` / `Devil's Advocate` /
`Edge-Case Hunter`) as `codex-review` §4. Since the adversarial pass is cheap
(Haiku agent, read-only), running it against GLM's output catches cases where
GLM's main review missed an edge the adversarial lens would spot.

In `dev` maturity, skip the adversarial pass for GLM (Codex's adversarial is enough).

## 8. Important Rules

- **NO FALLBACK.** If GLM fails, the review is skipped for this phase. Codex runs in parallel and provides the independent opinion. Do not dispatch a Claude subagent to replace GLM.
- **Child-process isolation.** The three env vars (`ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_DEFAULT_*_MODEL`) MUST live in the single `claude -p` invocation's environment. Never write them to `~/.claude/settings.json`, never export them in the parent shell.
- **Foreground only.** The pipeline itself runs glm-review in a background job for parallelism, but the skill's internal `claude -p` call is always foreground. No polling, no daemons.
- **Clean up `/tmp` prompt files.** Same as codex-review.
- **Open bar quota.** Unlike Anthropic Claude or Codex, the user has unlimited z.ai access. It is OK to re-run glm-review multiple times in a single pipeline (e.g., adversarial pass, post-merge review, ad-hoc `/glm` invocation).
- **Log which engine was used.** The calling skill and the user should see "Review (engine=glm-5.1) complete" in session.log.
- **Never send the API key to stdout/stderr.** The env var is scoped to the subprocess; don't echo it.
