---
name: glm-review
description: "Use when the pipeline needs an independent review of a spec, plan, or implementation via GLM (skipped when no Z.ai key is configured)."
user-invocable: false
---

# glm-review

Review a spec, plan, or implementation using Zhipu AI's **GLM-5.2** via the
`api.z.ai/api/anthropic` Anthropic-compatible endpoint. Runs the already-installed
`claude` CLI in a child process with a few environment variables overridden so its
tool calls land on Z.ai instead of Anthropic.

Designed to run **in parallel with `codex-review`** so each review phase gets two
independent model opinions. The shared review policy — evidence tags, severities,
the adversarial pass, the consensus matrix, the convergence loop, the
auto-integration gates, and escalation triggers — lives in
[`../pipeline/references/review-chain.md`](../pipeline/references/review-chain.md).
This skill covers only the GLM-specific mechanics; do not restate the shared rules
here.

**No fallback.** If Z.ai is unreachable or the API key is missing, the review is
skipped with a warning and the calling skill continues without GLM input — Codex is
already running in parallel and provides the independent voice.

> **Cost:** Z.ai is metered — every GLM review spends tokens. Run it where a second
> independent opinion is worth the cost, not gratuitously.

## 1. Context Reception

Identical to `codex-review` (§1), including `maturity` and `iterate`:

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

## 2. Prerequisites

### API key lookup (first match wins)

```bash
GLM_KEY=""
for var in ZAI_API_KEY GLM_API_KEY; do
  val="${!var:-}"
  if [ -n "$val" ]; then GLM_KEY="$val"; break; fi
done

# Project-local fallback: if still empty, read ZAI_API_KEY / GLM_API_KEY from a
# .env at the repo root.
if [ -z "$GLM_KEY" ]; then
  ENV_FILE="$(git rev-parse --show-toplevel 2>/dev/null)/.env"
  if [ -f "$ENV_FILE" ]; then
    GLM_KEY=$(grep -E '^(ZAI_API_KEY|GLM_API_KEY)=' "$ENV_FILE" | head -n1 | cut -d= -f2-)
  fi
fi

if [ -z "$GLM_KEY" ]; then
  echo "[glm-review] No Z.ai API key found (ZAI_API_KEY / GLM_API_KEY). Skipping GLM review." >&2
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

Same template layout and placeholder mapping as `codex-review` (§2):

1. Read `${SKILL_DIR}/templates/review-{review_type}-prompt.md`.
2. Resolve `{{SPEC_PATH}}` / `{{PLAN_PATH}}` / `{{OUTPUT_PATH}}` / `{{BASE_REF}}` /
   `{{COMMIT_LIST}}` per the mapping in `codex-review` §2.
3. Write the resolved prompt to `/tmp/cloclo-glm-prompt-$(date +%s).md`.

The templates are identical between codex-review and glm-review **except for a
runtime-mechanics note**: the impl template's verification line differs, because
GLM has no execution sandbox (it cannot run typecheck/tests in headless `-p` — see
§4). Same instructions otherwise, so any output difference is pure model divergence.

## 4. Execution (FOREGROUND)

GLM writes the review file itself via the Write tool, targeting `{{OUTPUT_PATH}}`
resolved inside the prompt. Unlike Codex, **GLM has no OS sandbox** — the read-only
invariant is enforced by the prompt and by the `--allowedTools` whitelist below,
not by the kernel. The whitelist grants read/search/write plus read-only git, so
GLM can inspect the diff and write its review but cannot edit arbitrary source.

```bash
TS=$(date +%s)
PROMPT_FILE="/tmp/cloclo-glm-prompt-${TS}.md"
# ... resolved template written to PROMPT_FILE above ...

echo "GLM-5.2 is reviewing... (this takes 2-8 minutes). Output: $output_file"

# Pre-clear stale review file so the post-run guard can't accept an old file as
# success when GLM silently skips the Write call.
rm -f "$output_file"

# `< /dev/null` mirrors the codex hang fix: a non-interactive child must have stdin
# closed or it can block waiting for input. `timeout 900` caps a stuck session at
# 15 min. The three ANTHROPIC_DEFAULT_*_MODEL vars pin every Claude alias (opus /
# sonnet / haiku) to glm-5.2 so internal small-model calls don't hit a bad model
# id. --allowedTools whitelists tools so Write runs without a prompt in headless
# `-p` mode, while blocking arbitrary edits (no general Bash, no repo-wide write).
ANTHROPIC_BASE_URL="https://api.z.ai/api/anthropic" \
ANTHROPIC_AUTH_TOKEN="$GLM_KEY" \
ANTHROPIC_DEFAULT_OPUS_MODEL="glm-5.2" \
ANTHROPIC_DEFAULT_SONNET_MODEL="glm-5.2" \
ANTHROPIC_DEFAULT_HAIKU_MODEL="glm-5.2" \
timeout 900 claude -p \
  --allowedTools 'Read Grep Glob Write Bash(git diff:*) Bash(git log:*) Bash(git show:*)' \
  "$(cat "$PROMPT_FILE")" \
  < /dev/null \
  > "${output_file}.runtime.log" 2>&1
GLM_EXIT=$?

rm -f "$PROMPT_FILE"
```

**No `> "$output_file"` redirect.** GLM calls Write itself, targeting
`{{OUTPUT_PATH}}` resolved inside the prompt. The caller reads that file after the
call — a single file contract regardless of which reviewer produced it.

### Why the env-var pattern works

- `ANTHROPIC_BASE_URL` redirects the CLI's HTTP calls to Z.ai's Anthropic-compatible endpoint.
- `ANTHROPIC_AUTH_TOKEN` is sent as the `x-api-key` / `authorization` header — Z.ai accepts its own key there.
- `ANTHROPIC_DEFAULT_{OPUS,SONNET,HAIKU}_MODEL` force every Claude alias the CLI might request to `glm-5.2`. Setting all three (per Z.ai's own guidance) catches internal small-model calls that would otherwise hit a nonexistent Anthropic model id.
- **Only the child process inherits these vars.** The parent Claude Code session keeps its real Anthropic auth. Codex CLI, CodeRabbit CLI, and other tooling are unaffected.

### Result check (mandatory post-run guard)

```bash
if [ $GLM_EXIT -eq 0 ] && [ -s "$output_file" ] \
   && grep -qiE 'Verdict.*(PASS|CONCERNS|FAIL)' "$output_file"; then
  echo "[glm-review] OK: $output_file"
else
  echo "[glm-review] FAIL: exit=$GLM_EXIT, empty/missing/no-verdict. Skipping GLM for this phase." >&2
  # no fallback — Codex is already running in parallel
fi
```

The verdict sniff rejects auth-error / refusal text (e.g. a Z.ai 401 body) that
would otherwise pass the `[ -s ]` check. A failed guard means GLM either skipped the
Write tool despite the prompt or an HTTP/quota error aborted mid-session.

**No fallback to another model** — Codex provides the independent voice.

Log to `session.log`:
```
[timestamp] GLM review (type=spec|plan|impl) {complete|failed}: /path/to/output_file
```

## 5. Running in Parallel with codex-review

The pipeline dispatches both reviewers as background jobs and waits for both. Each
reviewer writes its review to its own `output_file` via its native mechanism
(Codex → `codex exec -s read-only -o`, GLM → `claude -p` + Write tool) and routes
its stdout/stderr to `${output_file}.runtime.log`. The pipeline reads the review
files after both jobs complete — it never parses stdout.

```bash
# In the pipeline's Phase 2/4/6 orchestration:
CODEX_OUT="$session_dir/0X-codex-review-XXX.md"
GLM_OUT="$session_dir/0X-glm-review-XXX.md"

# Each reviewer already writes ${output_file}.runtime.log itself; the backgrounded
# wrappers just close stdin (< /dev/null) so neither child blocks on input.
(invoke codex-review output_file=$CODEX_OUT ... < /dev/null) &
CODEX_PID=$!

(invoke glm-review output_file=$GLM_OUT ... < /dev/null) &
GLM_PID=$!

wait $CODEX_PID; CODEX_RC=$?
wait $GLM_PID;   GLM_RC=$?

echo "Reviews complete: codex=$CODEX_RC ($CODEX_OUT), glm=$GLM_RC ($GLM_OUT)"
```

The calling skill then reads `$CODEX_OUT` and `$GLM_OUT` and merges findings via
the consensus rules in review-chain.md. **Single file contract: whoever reviewed,
the review is at `output_file`.**

## 6. Findings & Shared Policy

Findings format, evidence tags (`[TOOL]`/`[CODE]`/`[LLM-JUDGMENT]`), severities
(P0/P1/P2), file:line requirements, the adversarial pass, the consensus matrix, and
the convergence loop are all defined in
[`../pipeline/references/review-chain.md`](../pipeline/references/review-chain.md).
GLM findings plug into the same consensus table as Codex and CodeRabbit — no extra
logic here.

Phase 9.5 (post-merge, non-blocking) runs glm-review once more against post-merge
HEAD and writes `11-glm-post-merge-review.md` (registered in the pipeline's
session-files reference). It uses the same `${output_file}.runtime.log` naming as
every other phase.

## 7. Important Rules

- **NO FALLBACK.** If GLM fails, the review is skipped for this phase; Codex runs in parallel. Do not dispatch a Claude subagent to replace GLM.
- **No OS sandbox.** GLM's read-only behavior is prompt- and `--allowedTools`-enforced, not kernel-enforced. Never widen `--allowedTools` to general `Bash` or to `Edit` on source.
- **Child-process isolation.** The `ANTHROPIC_*` env vars MUST live only in the single `claude -p` invocation's environment. Never write them to `~/.claude/settings.json`, never export them in the parent shell.
- **Foreground only.** The pipeline runs glm-review in a background job for parallelism, but the skill's internal `claude -p` call is always foreground. No polling, no daemons.
- **Cost-aware.** Z.ai is metered — each review spends tokens. Don't re-run gratuitously.
- **Clean up `/tmp` prompt files.** Same as codex-review.
- **Never send the API key to stdout/stderr.** The env var is scoped to the subprocess; don't echo it.
- **Log which engine was used** — "Review (engine=glm-5.2) complete" in session.log.
