---
name: pipeline
description: Use when the user invokes /pipeline or asks to build, implement, create, or ship a feature through a structured Claude+Codex+CodeRabbit+Gemini dev cycle with autonomous review checkpoints
---

# CLoClo Pipeline

Chains SuperPowers skills (brainstorming, writing-plans, subagent-driven-
development, verification) with autonomous reviews (Codex + CodeRabbit)
and a PR-first auto-merge flow. Invokes underlying skills — does not
reimplement them.

## When to Use

`/pipeline`, "new feature", "build X", "implement Y". Multi-step work
worth spec → plan → impl → verify gating. Not for one-liners, typos,
or reads.

## Invocation — no flags, ever

- `/pipeline` → read `checkpoint.json` (authoritative); if missing or
  corrupt, fall back to the artifact scan. If prior state exists, ask
  A/B/C in the terminal. Else run fresh from Phase 1.
- `/pipeline <free text>` → interpret text as a directive, skip the
  dialogue. Examples: `passe au plan`, `le code est ecrit revois`,
  `refais tout`, `pas de codex`, `ship mode`, `pas de PR`.

French, English, and mixed phrasing all accepted. 80% clear intent →
act and log. Ambiguity → one clarifying terminal question. Full
directive vocabulary: `references/smart-resume.md`.

## The Pipeline Flow

| # | Phase | Skill invoked | Output |
|---|-------|---------------|--------|
| 1 | Design | `superpowers:brainstorming` | `01-spec.md` |
| 2 | Review spec (Codex + GLM parallel, auto-integrate) | `codex-review` + `glm-review` (spec) | `02-codex-review-spec.md`, `02-glm-review-spec.md` |
| 3 | Plan | `superpowers:writing-plans` | `04-plan.md` |
| 4 | Review plan (Codex + GLM parallel, auto-integrate) | `codex-review` + `glm-review` (plan) | `05-codex-review-plan.md`, `05-glm-review-plan.md` |
| 4.5 | Task DAG + briefs | inline | `08-task-dag.md`, `task-briefs/` |
| 5 | Execute | `superpowers:subagent-driven-development` | commits on feature branch |
| 6 | Review impl (Codex + GLM parallel, auto-integrate) | `codex-review` + `glm-review` (impl) | `07-codex-review-impl.md`, `07-glm-review-impl.md` |
| 6.5 | Review impl static (conditional — see `references/review-chain.md`) | `coderabbit-review` | `07b-coderabbit-review-impl.md` |
| 7 | Verify | `superpowers:verification-before-completion` | `09-compliance-report.md` |
| 7.5 | Visual verify (if UI) | `agent-browser` | `screenshots/` |
| 8 | Wiki ingest (auto) | inline | wiki updated |
| 9 | Open PR + multi-bot auto-integrate + auto-merge | `superpowers:finishing-a-development-branch` | PR URL, merged, branch deleted |
| 9.5 | Post-merge GLM review (safety net) | `glm-review` (impl) | `11-glm-post-merge-review.md` |

Full per-phase execution: `references/phases.md`. GLM runs only when a Z.ai API key is available (`ZAI_API_KEY` → `GLM_API_KEY`, optionally read from a project `.env`). Missing key = skipped with a logged warning; Codex alone covers the review.

## Step 0: Toggle Check

Before running the flagship, resolve the project root and check for a
pause flag:

```bash
ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
[ -f "$ROOT/.cloclo-disabled" ] && echo "PAUSED"
```

If `.cloclo-disabled` exists, tell the user CLoClo is paused and ask
whether to proceed anyway before starting Phase 1. Otherwise continue
normally. (`/toggle` manages this flag.)

## Confidence-First Principle (applies everywhere)

**Autonomous does not mean guessing.** Every decision — applying a
finding, skipping it, interpreting a directive, picking a default —
passes a confidence check. Below 95% confidence, ask the user in the
terminal (never GitHub) with 2-3 concrete options, marking the
recommended one and accepting free-form text.

Canonical decision flow, ask format, and the when / when-not-to-ask
lists: `references/confidence-first.md`.

## Auto-Integration — The 3 Gates

Every review phase (2, 4, 6, 6.5, 9) applies findings automatically
under the same rule — this is the ONLY integration model; there are no
interactive decision points in review phases. A finding is auto-applied
only when ALL three gates pass:

1. **Concrete patch or revision provided.** Bot/reviewer gave a diff,
   an AI-Agent prompt with file:line+replacement, or for spec/plan a
   specific section + exact new text. Judgment-only findings
   ("consider refactoring X") are skipped.
2. **Not auth / payments / data migration.** Critical domains escalate
   to the user even with a concrete patch.
3. **No conflicting patches across reviewers or findings.** Different
   fixes at the same file:line → skip both, log `[CONFLICT]`, ask.

Canonical statement, consensus and disagreement rules, iteration caps:
`references/review-chain.md`.

**Iteration caps:** 3 rounds for code phases, 2 for spec/plan. After
the cap, exit the loop and escalate any remaining critical findings.

**Commit format for auto-applied fixes:**

```
fix(phase-{N}): auto-apply {reviewer} findings ({N} fixes)

- [file:line] — description
- [CONSENSUS file:line] — description (2+ independent reviewers agreed)

Skipped (judgment-only or critical domain):
- [file:line] — reason
```

## PR-First + Auto-Merge (Phase 9)

Phase 9 opens a Pull Request via `superpowers:finishing-a-development-
branch`, waits for installed bots (bot-wait rule: first round until ≥1
bot has posted, max 10 min; re-review iterations max 5 min — see
`references/review-chain.md`), auto-applies their concrete patches
under the 3 gates, re-reviews, and auto-merges with `--delete-branch`
when clean. The user stays in the terminal. When a
Z.ai API key is available, Phase 9.5 runs a final GLM-5.2 pass on the
post-merge HEAD — an independent safety net, non-blocking for P1/P2,
auto-escalates P0.

**Default bots** (no extra config once installed): CodeRabbit GitHub App
+ Gemini Code Assist. **Opt-in:** Codex Cloud, Claude Code Action. Full
stack + install URLs: `references/bot-stack.md`.

**Consensus:** any 2+ independent reviewers flag the same file:line →
`[CONSENSUS]`. Full rule (severity escalation, when it overrides gate
1, conflict handling): `references/review-chain.md`.

**Disagreement handling and escalation triggers:** defined once in
`references/review-chain.md`. Escalation is terminal-only with the
standard ask format.

**Branch lifecycle:** on successful auto-merge,
`gh pr merge --squash --delete-branch --auto` removes the branch
locally AND on the remote. On escalation, the branch stays alive so
the user can push manual fixes and resume.

## Session Setup

1. Take the user message (or ask what to build if empty)
2. Create `docs/cloclo-sessions/YYYY-MM-DD-<slug>/`
3. Init `session.log`:
   `[timestamp] CLoClo session started: <slug>`
   `[timestamp] Prerequisites: superpowers=OK, codex=OK|MISSING, coderabbit=OK|MISSING`
4. Optional `pipeline.config.md` for project-specific verification commands

## Supporting References

Heavy detail, variant tables, and lookups live in `references/`:

- `review-chain.md` — SHARED CONTRACT: 3 gates, consensus, disagreement, bot-wait rule, Phase 6.5 enable condition, escalation triggers
- `smart-resume.md` — checkpoint-first resume, artifact-scan fallback, A/B/C dialogue, directive interpretation table
- `bot-stack.md` — default + opt-in bot list with install URLs and costs
- `phases.md` — full per-phase execution (the longest reference, 450+ lines)
- `prerequisites.md` — SuperPowers/Codex/CodeRabbit/agent-browser auto-install + degraded modes
- `model-policy.md` — Opus/Sonnet/Haiku mixed policy, per-phase assignments
- `retries.md` — bounded retries, spike/dev/ship maturity levels
- `session-files.md` — session dir layout, checkpoint.json, handoff.md formats
- `confidence-first.md` — the 95% confidence gate, decision flow, ask format

## Important Rules

1. **Invoke underlying skills; never reimplement them.** SuperPowers,
   Codex, CodeRabbit, and the finishing skill do the real work.
2. **Phase 1 (brainstorming) is the only scheduled interactive phase.**
   Every other phase auto-integrates under the 3 gates. BUT
   Confidence-First applies universally — ask when unsure, don't guess.
3. **Questions stay in the terminal, never on GitHub.** The user should
   never have to open the GitHub UI to answer the pipeline.
4. **No flags, ever.** Natural-language directives replace every flag
   use case. Escape hatch = edit the session dir before re-running.
5. **Each phase outputs to the session dir** with numbered filenames
   for traceability.
6. **Checkpoint after every phase; handoff on exit, always.** Session
   resumes via `checkpoint.json` after any crash.
7. **SuperPowers specs/plans live in their own directories**
   (`docs/superpowers/specs/`, `docs/superpowers/plans/`). CLoClo
   copies/symlinks them into the session dir.
8. **Wiki ingest (Phase 8) is automatic and silent.** Skipped when no
   wiki exists in the project.
9. **Reviews NEVER auto-skip.** Codex fails → Claude subagent fallback.
   CodeRabbit fails → warn and continue (static analysis is a safety
   net, not a blocker).
10. **Branch deleted on auto-merge success** (`--delete-branch` flag).
    On escalation the branch stays alive so the user can push manual
    fixes and rerun `/pipeline`.
