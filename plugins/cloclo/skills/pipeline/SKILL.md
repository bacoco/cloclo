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

## The 9-Phase Flow

| # | Phase | Skill invoked | Output |
|---|-------|---------------|--------|
| 1 | Design | `superpowers:brainstorming` | `01-spec.md` |
| 2 | Review spec | `codex-review` (spec) | `02-codex-review-spec.md` → Decision #1 |
| 3 | Plan | `superpowers:writing-plans` | `04-plan.md` |
| 4 | Review plan | `codex-review` (plan) | `05-codex-review-plan.md` → Decision #2 |
| 4.5 | Task DAG + briefs | inline | `08-task-dag.md`, `task-briefs/` |
| 5 | Execute | `superpowers:subagent-driven-development` | commits |
| 6 | Review impl (arch) | `codex-review` (impl) | `07-codex-review-impl.md` → Decision #3 |
| 6.5 | Review impl (static) | `coderabbit-review` | `07b-coderabbit-review-impl.md` → Decision #3b |
| 7 | Verify | `superpowers:verification-before-completion` | `09-compliance-report.md` |
| 7.5 | Visual verify (if UI) | `agent-browser` | `screenshots/` |
| 8 | Wiki ingest (auto) | inline | wiki updated |

Full per-phase detail: see `references/phases.md`.

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

## Decision Point Format

After each review phase (2, 4, 6, 6.5), present findings raw and ask:

```
{Reviewer} a review ton {artifact}. Voici ses findings :

[3-5 line summary from the review file]

Fichier complet : {session_dir}/{review_file}.md

Que veux-tu faire ?

A. Integrer tous les findings et continuer
B. Integrer certains findings (tu precises lesquels)
C. Ignorer la review et continuer
D. Demander au reviewer de creuser un point precis
E. Modifier toi-meme (edite le fichier, dis "c'est bon")

Ou tape un commentaire libre.
```

Log the user's choice in `session.log`. After A or B, SuperPowers rewrites
the artifact. **Do NOT auto-resubmit to the reviewer** — user controls via
option D.

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
2. **After correction (A or B), do NOT auto-resubmit.** User controls via option D.
3. **All reviews are FOREGROUND.** Claude waits, shows progress, reads the result.
4. **Free-form user input at decision points** is valid — treat as comment and adapt.
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
