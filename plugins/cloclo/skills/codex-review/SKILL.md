---
name: codex-review
description: "Review a spec, plan, or implementation — first tries Codex (GPT-5.4), falls back to Claude subagent if unavailable. Writes findings to a file. Foreground execution."
user-invocable: false
---

# codex-review

Review a spec, plan, or implementation. Tries Codex first (independent model, explores
codebase freely). If Codex is unavailable (CLI missing, usage limits, runtime error),
falls back to a Claude subagent review. Either way, findings are written to a file
that the calling skill reads back verbatim.

## 1. Context Reception

The calling skill (typically `pipeline`) passes:

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

## 2. Try Codex First

### Prerequisites

```bash
# Only the Codex CLI is required — the codex-companion.mjs wrapper is no longer used.
command -v codex &>/dev/null || CODEX_UNAVAILABLE=1

# Auth is managed by Codex CLI internally — do NOT check codex whoami or OPENAI_API_KEY
```

### Prompt Construction

1. Read the template: `${SKILL_DIR}/templates/review-{review_type}-prompt.md`
2. Replace placeholders: `{{SPEC_PATH}}`, `{{PLAN_PATH}}`, `{{OUTPUT_PATH}}`, `{{BASE_REF}}`, `{{COMMIT_LIST}}`
3. Write resolved prompt to `/tmp/cloclo-codex-prompt-$(date +%s).md`

### Execution (FOREGROUND)

```bash
echo "Codex is reviewing (read-only sandbox)... output -> $output_file"

codex exec \
  -s read-only \
  -o "$output_file" \
  "$(cat "$PROMPT_FILE")" \
  > /dev/null 2>&1
CODEX_EXIT=$?

rm -f "$PROMPT_FILE"
```

**Pattern** : native `codex exec` (no wrapper). Matches the interactive `codex` terminal experience, minus the per-tool approval prompts.

- `codex exec` — non-interactive one-shot session. Same tools, same working-directory rooting as an interactive `codex` run.
- `-s read-only` — **OS-level sandbox**. Codex has FULL READ access to the entire repo (every source file, git history, CLAUDE.md, everything). Writes are blocked at the kernel level — Codex physically cannot modify any file in the project, even if the prompt told it to. Belt + suspenders with the prompt template's "don't modify code" instruction.
- `-o "$output_file"` — the final agent message is captured directly into the review file. No stdout pollution, no tool call needed; Codex's native output flag handles it.
- `> /dev/null 2>&1` — stdout and stderr discarded. Only `$output_file` matters.
- Block until exit. Delete temp prompt after.

### Why this approach over `codex-companion.mjs task --write`

| Aspect | `codex exec -s read-only -o` (this version) | `node codex-companion.mjs task --write` (old) |
|---|---|---|
| Wrapper | None (native CLI) | 63-import node wrapper |
| Read-only enforcement | Kernel syscall sandbox | Relied on prompt instruction |
| Output capture | `-o` flag, guaranteed | Depended on Codex calling its write tool |
| Coupling | OpenAI's stable public CLI | Script path hardcoded, breaks if OpenAI refactors |
| Stdout pollution | None | JSONL events + progress lines |

Past behaviour: Codex occasionally completed exploration without calling its write tool → empty output file despite exit=0. `-o` removes that failure mode entirely — the final agent message is captured whether or not the model thinks to emit it as a tool call.

### Result Check (strict — mandatory post-run guard)

```bash
if [ $CODEX_EXIT -eq 0 ] && [ -s "$output_file" ]; then
  echo "[codex-review] OK: $output_file"
else
  echo "[codex-review] FAIL: exit=$CODEX_EXIT, file empty or missing. Falling back to Claude." >&2
  # fall through to Claude fallback (section 3)
fi
```

**Why still a guard** : `-o` handles the "Codex forgot to write" case at the CLI level, but can't cover infra failures (auth expired mid-session, quota hit, network cut). The `[ -s "$output_file" ]` check catches both cleanly.

Log to `session.log` either way.

## 3. Claude Fallback

When Codex is unavailable or fails, dispatch a Claude subagent to do the review.

**Why this works:** The subagent has fresh context (hasn't seen the conversation), reads
the actual files, and catches real bugs. Less independent than Codex (same model family),
but far better than skipping the review.

### Dispatch by review_type

**Model: always Opus for review fallback.** Reviews are where the +8 points SWE-bench Verified gap between Opus 4.7 and Sonnet 4.6 translates to real bugs caught. Do not downgrade the fallback reviewer to Sonnet.

**For `spec` review:**

```
Agent(
  subagent_type: "superpowers:code-reviewer",
  model: "opus",
  prompt: "Review this implementation spec: {input_file}

  You are a senior reviewer. Read the spec, explore the codebase, and verify:
  - Every file, function, and hook mentioned actually exists
  - The architecture is feasible
  - Edge cases and fallbacks are defined
  - No contradictions between sections

  Write your review to: {output_file}

  Format: Verdict, then findings with severity (P0/P1/P2), file refs, and line numbers."
)
```

**For `plan` review:**

```
Agent(
  subagent_type: "superpowers:code-reviewer",
  model: "opus",
  prompt: "Review this implementation plan: {input_file}
  Based on the spec: {spec_path}

  You are a senior reviewer. Read the plan, explore the codebase, and verify:
  - Every file/function/hook mentioned exists and has the right signature
  - The plan covers everything the spec requires
  - Task order has no circular dependencies
  - Code snippets will compile against real types
  - Edge cases from the spec have matching implementation steps

  Write your review to: {output_file}

  Format: Verdict, then findings with severity (P0/P1/P2), file refs, and line numbers."
)
```

**For `impl` review:**

```
Agent(
  subagent_type: "superpowers:code-reviewer",
  model: "opus",
  prompt: "Review this implementation against its spec and plan.

  Spec: {spec_path}
  Plan: {plan_path}
  Base ref: {base_ref}
  Commits: {commit_list}

  Run git diff {base_ref}..HEAD to see all changes. Read each modified file in full.
  Verify:
  - Implementation matches the spec
  - Hook signatures, field names, and types are correct
  - Fallbacks defined for empty/error states
  - No regressions in modified files
  - Mobile responsive if UI was touched

  Write your review to: {output_file}

  Format: Verdict, then findings with severity (P0/P1/P2), file refs, and line numbers."
)
```

### Result Handling (same for both Codex and Claude)

- Read `output_file` in its entirety
- Return raw content to the calling skill — no summarization, no reformatting
- Log to `session.log`:
  ```
  [timestamp] Review (type=spec, engine=codex|claude) complete: /path/to/output_file
  ```

## 4. Adversarial Triple-Perspective Pass

After the primary review (Codex or Claude fallback) completes, run a mandatory adversarial pass. This prevents rubber-stamp PASS verdicts by forcing three failure-seeking perspectives.

**When to run:** Always in `ship` maturity. In `dev` maturity, run only for `impl` reviews. Skip in `spike` maturity.

**How:** Append these three questions to the review output file, then dispatch a single **Haiku** agent (`model: "haiku"`) to answer all three — this is a cheap, read-only pass:

```
## Adversarial Analysis

### Skeptic — "Which assumption is most likely wrong?"
[Identify the strongest assumption in the reviewed artifact and explain how it could fail]

### Devil's Advocate — "How could this be misused or fail unexpectedly?"
[Describe a realistic scenario where this code/spec causes harm despite passing review]

### Edge-Case Hunter — "What input causes silent failure?"
[Find one concrete input or state that produces wrong results without raising an error]
```

**Rules:**
- Each perspective MUST produce at least one concrete scenario (not "everything looks fine")
- Scenarios judged unrealistic must include quantitative rationale ("this requires >10^9 concurrent users")
- Realistic scenarios are tagged `[ADVERSARIAL-REAL]` and escalated to findings
- The adversarial section is appended to the same output file, not a separate file

## 5. Evidence Tagging

Every finding in the review must be tagged with its evidence source:

| Tag | Meaning | Weight |
|-----|---------|--------|
| `[TOOL]` | Finding backed by tool output (test failure, type error, lint warning) | Full weight |
| `[CODE]` | Finding backed by reading actual code at file:line | Full weight |
| `[LLM-JUDGMENT]` | Finding based on LLM reasoning alone, no tool/code evidence | Half weight — may be wrong |

**Rule:** If `[LLM-JUDGMENT]` findings outnumber `[TOOL]` + `[CODE]` findings, the review is flagged as low-evidence. The calling skill shows: `"⚠ Review is mostly LLM judgment — consider running tests before integrating findings."`

## 6. Severity Escalation

When both Codex and Claude review the same artifact (e.g., Codex primary + Claude adversarial):
- **Highest severity wins.** If Codex says P2 and Claude says P0 → final is P0.
- **Only the original reviewer can de-escalate** with explicit technical reasoning citing file:line.
- **Cross-model agreement** (both flag same issue) → severity is confirmed and marked `[CONSENSUS]`.

## 7. Convergence-Gated Critic Loop

When the calling skill requests iterative review (e.g., `iterate: true` parameter), the review enters a convergence loop instead of a single pass.

**Loop logic:**
1. Run the review (Codex or Claude fallback) → collect findings
2. If all findings are PASS or DEFER → **converged**, exit loop
3. If new findings found → apply fixes for FAIL items, log ESCALATE items
4. Re-review **only changed files** (delta review, not full re-review)
5. Check convergence: no new findings AND zero fixes applied in this pass → **converged**
6. Hard cap: **3 iterations maximum** (ship maturity) or **2 iterations** (dev maturity)
7. On cap exhaustion: report final state regardless of convergence

**Verdicts per finding:**
| Verdict | Action | Continues loop? |
|---------|--------|-----------------|
| `PASS` | No action needed (must cite evidence, not just "looks good") | No |
| `FAIL` | Auto-fix applied | Yes (re-review needed) |
| `ESCALATE` | Ambiguous — batch up to 3 ESCALATEs, pause loop, present to user with options | Pauses |
| `DEFER` | Acknowledged risk, not blocking — documented with rationale | No |

**ESCALATE batching:** When multiple ESCALATEs occur in one pass, batch them into a single user question:
```
Review found {N} ambiguous items that need your input:

1. {finding} — Options: A) {approach1} B) {approach2}
2. {finding} — Options: A) {approach1} B) {approach2}
3. {finding} — Options: A) {approach1} B) {approach2}

Reply with choices (e.g., "1A 2B 3A") or comment freely.
```

After user responds, resume the loop with the chosen approach.

## 8. Consensus Matrix (Multi-Model Reviews)

When both Codex AND Claude review the same artifact (available in `ship` maturity or when user requests via Decision Point D):

**Spread detection:** For each finding domain, compute:
- `consensus` = average severity across models
- `spread` = max severity - min severity

If `spread > 1 severity level` (e.g., Codex says P2, Claude says P0), flag as `[DISAGREEMENT]` and surface explicitly in the report. Don't hide model disagreements in an average.

**Report table:**
```markdown
## Model Consensus

| Domain | Codex | Claude | Consensus | Spread | Flag |
|--------|-------|--------|-----------|--------|------|
| Security | P1 | P0 | P0 | 1 | [DISAGREEMENT] |
| Logic | P2 | P2 | P2 | 0 | [CONSENSUS] |
| Performance | — | P1 | P1 | 0 | |
```

Cross-model `[CONSENSUS]` findings (both models flag same issue) are high-confidence — always include, never filter.

## 9. Important Rules

- **NEVER summarize or filter findings.** Raw file, as written by the reviewer.
- **NEVER re-run automatically.** User decides via decision points A-E.
- **NEVER skip reviews entirely.** If Codex fails, Claude reviews. If Claude fails, warn and return.
- **Foreground ONLY.** No background promises, no polling loops.
- **Clean up temp files.** Codex prompt in `/tmp/` is deleted. Output in `session_dir/` is permanent.
- **Log which engine was used.** The calling skill and the user should know if the review came from Codex or Claude.
- **Tag every finding.** `[TOOL]`, `[CODE]`, or `[LLM-JUDGMENT]` — no untagged findings.
