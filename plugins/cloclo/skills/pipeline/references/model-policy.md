# Model Selection Policy

CLoClo uses a mixed-model strategy to balance review quality against quota
consumption: the highest-capability model has a much smaller usage budget than
the mid-tier model, so reserve it for the work where reasoning depth actually
changes the outcome (review, audit, design) and use lighter models for
mechanical work.

Model tiers below are referred to by capability role:
- **Opus** — highest-capability tier (deepest reasoning; smallest budget).
- **Sonnet** — mid-tier (strong, cheaper, generous budget).
- **Haiku** — light tier (fast, cheapest).

## Per-Phase Model Assignment

| Work type | Model | Why |
|-----------|-------|-----|
| Reviewers (spec, plan, impl — Phase 2/4/6 Codex fallback) | **Opus** | Deepest reasoning catches the most real bugs |
| Adversarial triple-perspective pass | **Haiku** | Read-only skeptic questions |
| Phase 1 brainstorming (main session) | **Opus** | Design judgment, dialogue |
| Phase 3 writing-plans (main session) | **Opus** | Cross-module coherence |
| Phase 4.5 Task DAG + briefs | **Sonnet** | Mechanical decomposition |
| Phase 5 implementer subagents (1-2 files, clear spec) | **Sonnet** | Spec is blueprint, impl is mechanical |
| Phase 5 implementer subagents (>5 files or architecture) | **Opus** | Cross-file coherence |
| Phase 5 spec reviewer / code-quality reviewer subagents | **Opus** | Reasoning depth benefits reviews |
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
