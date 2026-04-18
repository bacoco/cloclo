# Model Selection Policy

CLoClo uses a mixed-model strategy to balance quality vs. quota consumption on
Max 20x / Max 5x plans (Opus weekly cap ~24-40h vs ~240-480h for Sonnet).
Opus 4.7 is ~8 points ahead of Sonnet 4.6 on SWE-bench Verified — that gap
matters for review/audit, is wasted on mechanical work.

## Per-Phase Model Assignment

| Work type | Model | Why |
|-----------|-------|-----|
| Reviewers (spec, plan, impl — Phase 2/4/6 Codex fallback) | **Opus** | +8 pts SWE-bench = real bugs caught |
| Adversarial triple-perspective pass | **Haiku** | Read-only skeptic questions |
| Phase 1 brainstorming (main session) | **Opus** | Design judgment, dialogue |
| Phase 3 writing-plans (main session) | **Opus** | Cross-module coherence |
| Phase 4.5 Task DAG + briefs | **Sonnet** | Mechanical decomposition |
| Phase 5 implementer subagents (1-2 files, clear spec) | **Sonnet** | Spec is blueprint, impl is mechanical |
| Phase 5 implementer subagents (>5 files or architecture) | **Opus** | Cross-file coherence |
| Phase 5 spec reviewer / code-quality reviewer subagents | **Opus** | +8 pts gap benefits reviews |
| Phase 7 verification-before-completion | **Sonnet** | Run tests + read output |
| Phase 7.5 visual verification (agent-browser) | **Sonnet** | Scripted capture + visual check |

## Override Rule

Critical domains (auth, payments, data migration, security) always use Opus
regardless of the table above.

## How to Apply

When invoking SuperPowers skills that dispatch subagents
(`subagent-driven-development`, `writing-plans`), pass the `model` parameter
on each `Agent(...)` call explicitly. Do not rely on inherit — inherit
defaults to the main session's model which is typically Opus.
