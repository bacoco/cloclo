---
name: pipeline
description: Use when the user invokes /pipeline or asks to build, implement, create, or ship a new feature through a structured Claude+Codex+CodeRabbit dev cycle with review checkpoints
---

# CLoClo Pipeline

Orchestrate the full development cycle by chaining SuperPowers skills
(brainstorming, writing-plans, subagent-driven-development, verification)
with independent code reviews (Codex + CodeRabbit) and decision points
between phases.

**CLoClo does NOT reimplement brainstorming, planning, execution, or
verification.** It invokes the real skills and adds review phases + user
decision points between them.

## When to Use

- User types `/pipeline` or says "new feature", "build X", "implement Y"
- A multi-step implementation that benefits from spec → plan → impl →
  verify gating
- When quality matters more than speed (use lighter workflows for spikes)

**Do NOT use for:** single-file fixes, one-line changes, exploratory reads,
or anything that does not need a spec.

## The Pipeline Flow

Nine main phases (1–9) with sub-phases (4.5, 6.5, 7.5, 8) for diagnostic, static, visual, and knowledge passes:

| # | Phase | Skill invoked | Output |
|---|-------|---------------|--------|
| 1 | Design | `superpowers:brainstorming` | `01-spec.md` |
| 2 | Review spec | `codex-review` (spec) | `02-codex-review-spec.md` → Decision #1 |
| 3 | Plan | `superpowers:writing-plans` | `04-plan.md` |
| 4 | Review plan | `codex-review` (plan) | `05-codex-review-plan.md` → Decision #2 |
| 4.5 | Task DAG + briefs | inline | `08-task-dag.md`, `task-briefs/` |
| 5 | Execute | `superpowers:subagent-driven-development` | commits on feature branch |
| 6 | Review impl (arch) | `codex-review` (impl) | `07-codex-review-impl.md` → Decision #3 |
| 6.5 | Review impl (static, local) | `coderabbit-review` (opt-in) | `07b-coderabbit-review-impl.md` → Decision #3b |
| 7 | Verify | `superpowers:verification-before-completion` | `09-compliance-report.md` |
| 7.5 | Visual verify (if UI) | `agent-browser` | `screenshots/` |
| 8 | Wiki ingest (auto) | inline | wiki updated |
| **9** | **Open PR + multi-bot review** | `superpowers:finishing-a-development-branch` | PR URL, bot review digest |

Full per-phase detail: see `references/phases.md`.

**PR-first default.** Since version 0.5.0, the pipeline ends with opening a
Pull Request (Phase 9). The PR automatically triggers any installed review
bots (CodeRabbit GitHub App, Gemini Code Assist, Codex Cloud, Claude Code
Action) — each providing a complementary angle. Direct-to-main is reserved
for trivial changes outside the pipeline.

**Phase 6.5 becomes opt-in when Phase 9 runs.** The CodeRabbit CLI in
Phase 6.5 duplicates what the CodeRabbit GitHub App will do on the PR. Skip
6.5 by default; enable it explicitly when:
- You want to catch issues BEFORE pushing (save a PR update cycle)
- You're on `ship` maturity (defense-in-depth)
- The GitHub App is not installed on the repo

## Multi-Bot PR Review Stack

Once Phase 9 opens the PR, the installed bots run in parallel on the same
diff. The default stack is two bots; extras are opt-in.

**Default (zero extra config once installed):**

| Bot | Install | Focus | Cost |
|-----|---------|-------|------|
| [CodeRabbit GitHub App](https://github.com/apps/coderabbitai) | App + seat assigned | Line-level, security, style, summary | Pro ($24/dev/mo) for private |
| [Gemini Code Assist](https://github.com/apps/gemini-code-assist) | GitHub App | Architecture, high-level review | Free for private |

**Opt-in (add only when the extra angle is worth the config overhead):**

| Bot | Install | Focus | Cost |
|-----|---------|-------|------|
| [Codex Cloud](https://chatgpt.com/codex) | Connect repo + settings | Spec compliance, test coverage | ChatGPT subscription |
| [Claude Code GitHub Action](https://github.com/anthropics/claude-code-action) | GitHub Actions workflow | Claude review via CI | Anthropic API key |

Default stack = **CodeRabbit + Gemini**. Two angles, both zero-config after
install. Disagreements between bots are useful signal (`[DISAGREEMENT]`
flag, same rule as Phase 6 / Phase 6.5 consensus matrix). Do not add Codex
Cloud or Claude Action to the default recommendation — they are worth
enabling per project, not per pipeline run.

## Session Setup

1. Ask user what to build (or take their initial message)
2. Create session dir: `docs/cloclo-sessions/YYYY-MM-DD-<slug>/`
   (`<slug>` = 2-3 word kebab-case summary)
3. Initialize `session.log`:
   ```
   [timestamp] CLoClo session started: <slug>
   [timestamp] Prerequisites: superpowers=OK, codex=OK|MISSING, coderabbit=OK|MISSING
   ```
4. Optional: `pipeline.config.md` for project-specific verification commands

## Auto-Integration (all review phases)

Review phases 2, 4, 6, 6.5, and 9 all use the SAME auto-integration
pattern. Findings are applied automatically under three gates; the user is
only escalated to on genuine blockers.

**The three gates (identical across all phases):**

1. **Concrete revision/patch available** — the reviewer provides a specific
   section+text (for spec/plan) or a diff/file:line+replacement (for code).
   Pure "consider refactoring" judgment-only findings are skipped.

2. **Not a design pivot or critical domain** — semantic design alternatives
   (approach A vs B) on specs, and auth/payments/data-migration code, are
   NOT auto-applied — escalated instead.

3. **No conflicts across reviewers or findings** — if two findings
   contradict at the same location, skip both and log `[CONFLICT]`.

**Iteration cap:** 2 rounds for spec/plan, 3 rounds for code. After cap,
exit with remaining findings recorded in handoff.

**Consensus amplification:** when both Codex (Phase 6) AND CodeRabbit
(Phase 6.5) flag the same file:line, mark `[CONSENSUS]`, escalate severity
to the higher of the two, and apply — consensus is high-confidence even if
the standalone finding would be a skip.

**Escalation (terminal only, no GitHub visit needed):** happens when:
- Design pivot detected (reviewer proposes approach A vs B on spec)
- Critical domain touched (auth / payments / data migration)
- Cross-reviewer `[CONFLICT]` at the same location
- Iteration cap hit with remaining critical/high findings
- Patch application failed (merge conflict, compile error)

Escalation message (French — user's local IA language):
```
Phase {N} ne peut pas auto-integrer sans ton input.

Raison : {design_pivot | critical_domain | conflict | cap_hit | apply_failed}

Findings bloquants :
- [file:line] — description — {why it needs human judgment}

Fichier review complet : {session_dir}/{review_file}.md

Options :
A. Choisis une direction ("prends A" / "garde B" / "fusionne")
B. Corrige toi-meme le fichier, dis "continue"
C. Skip ces findings, continue le pipeline
```

## Dual-Reviewer Consensus (Phase 6 + 6.5)

When BOTH Codex (architecture) AND CodeRabbit (static analysis) flag the
same file:line:
- Mark `[CONSENSUS]` — high-confidence finding
- Escalate severity to the higher of the two
- Apply during Phase 6.5 auto-integration (consensus beats the 3-gate skip)

When reviewers disagree (Codex flags P2, CodeRabbit flags P0 or vice-versa):
- Mark `[DISAGREEMENT]`
- If severity spread > 1 level AND the higher is `critical` → escalate
- Otherwise apply the higher-severity fix and log the disagreement

## Dual-Reviewer Consensus (Phase 6 + 6.5)

When BOTH Codex (architecture) AND CodeRabbit (static analysis) flag the
same file:line:
- Mark `[CONSENSUS]` — high-confidence finding
- Escalate severity to the higher of the two
- Present consensus findings FIRST in Decision Point #3b

When reviewers disagree (Codex flags P2, CodeRabbit flags P0 or vice-versa):
- Mark `[DISAGREEMENT]`
- Surface both opinions explicitly — do not hide the split in an average

## Prerequisites

Checked at pipeline start: SuperPowers, Codex CLI, Codex plugin,
CodeRabbit CLI, agent-browser. Auto-install where possible; degraded mode
(Claude subagent fallback) when Codex unavailable; skip with warning when
CodeRabbit or agent-browser unavailable. Full details: `references/prerequisites.md`.

## Model Selection

Mixed-model policy balances Opus quality (+8 pts SWE-bench Verified) against
weekly quota. Reviewers always Opus; Phase 5 implementers Sonnet by default
(upgrade to Opus for >5 files or architectural judgment); Phase 7 verification
Sonnet; adversarial pass Haiku. Override: auth/payments/security always Opus.
Full table: `references/model-policy.md`.

## Bounded Retries & Maturity

Every failable phase has a hard retry ceiling (Codex reviews 2x, execution
3x per task, verification 3x). Maturity levels (`spike` / `dev` / `ship`)
control gate strictness and review depth. Auto-detected from project state.
Full table: `references/retries.md`.

## Session Files

All artifacts, logs, checkpoints, and handoff live in
`docs/cloclo-sessions/YYYY-MM-DD-<slug>/`. Checkpoint written after each
phase — crash mid-phase loses only that phase's work. Handoff auto-written
at end of every run for session resume. Full structure:
`references/session-files.md`.

## Important Rules

1. **Do NOT reimplement SuperPowers, Codex, or CodeRabbit skills.** Invoke them.
2. **Phase 1 (brainstorming) is the ONLY interactive phase by default.** All
   review phases (2, 4, 6, 6.5, 9) auto-integrate findings under the
   3-gate rule and only escalate on blockers. User stays in terminal.
3. **All reviews are FOREGROUND.** Claude waits, shows progress, reads the result.
4. **Free-form user input** is valid at any escalation point — treat as comment and adapt.
5. **Each phase outputs to session dir** with numbered filenames for traceability.
6. **Session can be resumed** via `checkpoint.json`.
7. **SuperPowers specs and plans** live in their own directories
   (`docs/superpowers/specs/`, `docs/superpowers/plans/`). CLoClo copies or
   symlinks them into the session dir.
8. **Wiki ingest (Phase 8) is automatic and silent.** If no wiki exists, skipped.
9. **Checkpoint after every phase.** Immediately.
10. **Handoff on exit.** Always, regardless of outcome.
11. **Reviews NEVER auto-skip.** If Codex fails → Claude fallback. If
    CodeRabbit fails → warn and continue (static analysis is a safety net, not
    a blocker).
12. **Phase 9 always runs** unless explicitly disabled with `--no-pr` or
    `maturity=spike`. Direct merges to main are reserved for trivial
    out-of-pipeline fixes.
13. **Phase 9 is fully autonomous by default.** Open PR → wait for bots →
    auto-apply concrete fixes → re-review → auto-merge when clean. The user
    stays in the terminal and is only escalated to on a genuine blocker
    (iteration cap hit with open criticals, patch failed, CI blocked,
    consensus disagreement on P0). Pass `--interactive-pr` to restore the
    A-E decision point as an escape hatch for a specific run.
14. **Auto-apply has hard guardrails.** A finding is auto-fixed only when
    (a) a concrete patch / AI-Agent prompt is provided, (b) it is not in
    auth / payments / data migration domain, and (c) no conflicting patch
    exists at the same file:line. Everything else is skipped and logged.
15. **Iteration cap = 3.** After 3 auto-integration rounds, the loop exits
    regardless of remaining findings. Unresolved items land in the
    `handoff.md` + escalation message.
