# Review Chain — Shared Contract

Canonical definitions shared by the pipeline and the reviewer skills
(`codex-review`, `glm-review`, `coderabbit-review`). Every other file
that mentions consensus, the bot-wait rule, the Phase 6.5 enable
condition, the 3 gates, or escalation triggers points HERE. Do not
restate these rules elsewhere — link to this file.

## Reviewer Roster (the chain)

| Phase | Reviewers | Target |
|-------|-----------|--------|
| 2 | `codex-review` + `glm-review` (parallel) | spec |
| 4 | `codex-review` + `glm-review` (parallel) | plan |
| 6 | `codex-review` + `glm-review` (parallel) | implementation diff |
| 6.5 | `coderabbit-review` (CLI) — see enable condition below | implementation diff |
| 9 | GitHub PR bots: CodeRabbit App + Gemini (default); Codex Cloud, Claude Action (opt-in) | PR diff |
| 9.5 | `glm-review` (post-merge, non-blocking) | post-merge HEAD |

Each reviewer writes findings to its own session file. The pipeline
merges findings using the rules below. There are no interactive
decision points in review phases (this replaced the former
decision-point model). Auto-integration under the 3 gates is the only
model.

## Reviewer Availability Matrix (canonical)

The single source of truth for how each reviewer is probed, bounded, and
handled on failure. Every reviewer CLI call runs with `< /dev/null` and
`timeout 900`. The post-run guard for a successful review is:
`exit==0 && [ -s "$output_file" ] && grep -qiE 'Verdict.*(PASS|CONCERNS|FAIL)' "$output_file"`.

| Reviewer | Availability check | Timeout | Retries | On exhaustion | Fallback | Skip-semantics | Log line |
|----------|--------------------|---------|---------|---------------|----------|----------------|----------|
| `codex-review` (Codex CLI) | `codex --version` succeeds | 900 s | 2 | dispatch fallback | Claude subagent — `general-purpose`, or `superpowers:code-reviewer` **only if** present in the running session's available agent types | never silently skipped; falls back | `Phase N codex: fell back to Claude subagent` |
| `glm-review` (GLM Companion via Z.ai) | the adapter resolves `GLM_COMPANION_BIN` → `PATH` → repository sibling → Claude plugin cache, the key resolves (`~/.glm.env` → process `ZAI_API_KEY` / `GLM_API_KEY` → project `.env`), and the call succeeds | 900 s | 2 | skip | provider model fallback: `glm-5.2` → `glm-4.7` on rate limits | missing key or failure of both provider models → skipped with a logged warning | `Phase N glm: skipped (no key / failed)` |
| `coderabbit-review` (CodeRabbit CLI) | `command -v coderabbit` AND guard passes | 900 s | 2 | skip | none | failure or unavailable → skipped with a warning, non-blocking | `Phase N coderabbit: skipped (unavailable)` |

A phase is fully skipped only when **all** of its reviewers are
unavailable. As long as one reviewer (or the Codex fallback) produces a
review, the phase proceeds.

## Evidence Tagging (canonical)

Every finding carries exactly one evidence tag describing how it was
established:

- `[TOOL]` — produced by a deterministic tool (linter, type-checker,
  test run, static analyzer). Highest trust.
- `[CODE]` — grounded in a concrete code reference (file:line the
  reviewer read and quoted).
- `[LLM-JUDGMENT]` — the reviewer's opinion with no tool or exact code
  citation. Lowest trust; qualifies for auto-apply only via gate 1 (a
  concrete patch) or consensus.

## Severity Scale (canonical)

Three levels, no P3:

- **P0** — blocker: correctness bug, security hole, data loss, broken
  build. Auto-escalates when it survives the iteration cap.
- **P1** — should fix: real defect or risk, not a blocker.
- **P2** — nit / advisory: style, naming, minor cleanup.

CodeRabbit's `nit` maps to **P2** and is **advisory, never
auto-applied, logged only**. There is no P3. Where reviewer output uses
`critical`/`high`/`medium`/`low`, read `critical`→P0, `high`→P1,
everything else→P2.

## Auto-Integration — The 3 Gates (canonical)

A finding is auto-applied only when ALL three gates pass:

1. **Concrete patch or revision provided.** The reviewer gave a diff,
   an AI-Agent prompt with file:line + exact replacement, or — for a
   spec/plan — a specific section + exact new text. Judgment-only
   findings ("consider refactoring X") are skipped.
2. **Not auth / payments / data migration.** Critical domains escalate
   to the user even with a concrete patch.
3. **No conflicting patches.** Two reviewers (or two findings) propose
   different fixes at the same file:line → skip both, log `[CONFLICT]`,
   escalate.

**Iteration caps:** 3 rounds for code phases (6, 6.5, 9), 2 for
spec/plan phases (2, 4). After the cap, exit the loop and escalate any
remaining `critical`/`high` findings.

## Consensus (defined once, generically)

**Consensus = any 2+ independent reviewers flag the same file:line.**

"Independent" means separate reviewer runs backed by different engines
(e.g. Codex + GLM, GLM + CodeRabbit, CodeRabbit App + Gemini). Two
passes of the same engine (e.g. Codex CLI in Phase 6 and Codex Cloud in
Phase 9) do not form consensus.

When consensus is detected:

- Mark the finding `[CONSENSUS]`.
- Escalate severity to the highest among the flagging reviewers.
- Apply even when gate 1 alone would skip it (judgment-only): agreement
  between independent reviewers substitutes for a concrete patch — if
  no patch exists, derive one from the shared description.
- Gate 2 still holds: consensus in a critical domain escalates, never
  auto-applies.
- If the reviewers agree on the problem but propose **different**
  patches, gate 3 applies: skip both patches, log `[CONFLICT]`,
  escalate.

There are no named reviewer pairs. Any combination of 2+ independent
reviewers qualifies, in any phase where multiple reviewers saw the same
content.

## Disagreement

Two reviewers flag the same file:line with different severities:

- Mark `[DISAGREEMENT]`.
- Severity spread > 1 level AND the higher is `critical` → escalate.
- Otherwise apply the higher-severity fix and log the disagreement.
- Never average, never hide the split.

## Bot-Wait Rule (single rule)

Phase 9 waits for PR bots as follows:

- **First review round:** wait until at least ONE bot has posted (a
  comment or a review), with a hard maximum of **10 minutes**
  wall-clock. If no bot has posted after 10 minutes, proceed with
  whatever is there (possibly nothing).
- **Re-review iterations** (after pushing an auto-applied fix commit):
  maximum **5 minutes** wall-clock per iteration.

Poll both `comments` and `reviews` (several bots post via reviews, not
comments). There is no other wait rule anywhere in the pipeline.

## Phase 6.5 Enable Condition (single version)

Phase 6.5 (local CodeRabbit CLI review) runs when ANY of:

1. `maturity = ship`, OR
2. the CodeRabbit GitHub App is **not** installed on the repo, OR
3. the user asked for CodeRabbit in their directive
   (e.g. `/pipeline with coderabbit`).

Otherwise it is skipped — the CodeRabbit App will review the PR in
Phase 9, and a local CLI pass would duplicate it. There are no
CLI-style flags; `--coderabbit-cli` does not exist.

**App-installed check:** look at recent PRs on the repo for activity by
`coderabbitai` (`gh pr list` + `gh pr view --json comments,reviews`).
If the App's presence cannot be confirmed, treat it as not installed
and run the CLI review — a redundant local pass is cheaper than a
missing one.

If the CodeRabbit CLI is unavailable when the phase should run → skip
with a warning; never block the pipeline on it.

## Escalation Triggers (shared list)

Escalate to the user — in the terminal, never on GitHub — only when:

- An iteration cap is hit with `critical`/`high` findings still open.
- A patch failed to apply (merge conflict or compile error).
- CI or required reviewers block the merge.
- `[DISAGREEMENT]` at `critical` severity.
- `[CONFLICT]` — conflicting patches at the same file:line.
- A finding lands in auth / payments / data migration.

Escalation uses the standard ask format from `confidence-first.md`.
