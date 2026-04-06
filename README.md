# CLoClo — Code Loop Orchestrator: Claude + Codex

A Claude Code plugin with two superpowers:

1. **`/pipeline`** — Inserts independent [Codex](https://github.com/openai/codex-plugin-cc) reviews into the [SuperPowers](https://github.com/obra/superpowers) workflow. Design, review, plan, review, execute, review, verify.

2. **`/bootstrap`** — Sets up Claude Code infrastructure on any new project. CLAUDE.md, hooks, memory, skills, behavioral patterns — all adapted to your actual stack.

## Installation

Tell Claude Code:

```
Install the CLoClo plugin from marketplace bacoco/cloclo on GitHub
```

Claude adds the marketplace and plugin to your `settings.json` automatically. Restart when prompted.

---

## /pipeline — Development Workflow

### How It Works

You open Claude Code in your project and type:

```
/pipeline I want to add a search filter to the dashboard
```

Here is what happens:

**Phase 1 — SuperPowers brainstorms.**
SuperPowers asks you questions one at a time. If it involves UI, it starts a local server with HTML mockups in your browser — you click to choose between options A, B, C. It proposes 2-3 approaches with trade-offs. You pick. It writes a spec, self-reviews it, shows it to you. You approve (or ask for changes).

**Phase 2 — Codex reviews the spec.**
CLoClo sends the spec to Codex. Codex reads it, then freely explores your codebase (30-80+ files, 2-10 minutes). It checks that every file, function, and line mentioned in the spec actually exists. It writes its findings to a file.

You see the findings and react however you want:
- "integrate everything"
- "point 2 is wrong because..."
- "ignore that, not relevant"
- "dig deeper into the type issue"
- or anything else

SuperPowers takes the findings and your feedback, rewrites the spec, and moves on.

**Phase 3 — SuperPowers writes the implementation plan.**
Full SuperPowers writing-plans: scope check, file structure table, bite-sized tasks (2-5 min each), TDD cycle, complete code blocks, pre-written commit messages.

**Phase 4 — Codex reviews the plan.**
Same as Phase 2. Codex verifies every file/line/function exists, checks task ordering, flags risks. You react. SuperPowers rewrites the plan.

**Phase 5 — SuperPowers executes.**
Full superpowers:subagent-driven-development: fresh subagent per task, two-stage review (spec compliance + code quality), status handling, model selection, red flags.

**Phase 6 — Codex reviews the code.**
Codex does a real code review: git diff, full file reads, type checks, bug hunting. You react. SuperPowers fixes.

**Phase 7 — SuperPowers verifies.**
Full verification-before-completion: no claims without evidence, commands executed, output shown.

### Summary

```
SuperPowers brainstorms ──► spec
                              ↓ Codex reviews ↓ you react ↓ SuperPowers rewrites
SuperPowers writes plan ──► plan
                              ↓ Codex reviews ↓ you react ↓ SuperPowers rewrites
SuperPowers executes    ──► code
                              ↓ Codex reviews ↓ you react ↓ SuperPowers fixes
SuperPowers verifies    ──► done
```

### Without Codex

If Codex is not installed or not authenticated, CLoClo skips the review phases. You get pure SuperPowers — still excellent, just without the independent Codex reviews between phases.

### Session Files

All artifacts are tracked in `docs/cloclo-sessions/YYYY-MM-DD-<slug>/`:

| File | Written by | Content |
|------|-----------|---------|
| `01-spec.md` | SuperPowers | Design specification |
| `02-codex-review-spec.md` | Codex | Findings on the spec |
| `03-spec-v2.md` | SuperPowers | Rewritten spec after feedback |
| `04-plan.md` | SuperPowers | Implementation plan |
| `05-codex-review-plan.md` | Codex | Findings on the plan |
| `06-plan-v2.md` | SuperPowers | Rewritten plan after feedback |
| `07-codex-review-impl.md` | Codex | Code review findings |
| `session.log` | CLoClo | Decisions, timestamps, job IDs |

---

## /bootstrap — Project Setup

Sets up Claude Code infrastructure on any project in one command:

```
/bootstrap
```

### What it creates

| Phase | What | Files |
|-------|------|-------|
| 1 | Project analysis | (mental model) |
| 2 | CLAUDE.md | `CLAUDE.md` — 6 mandatory rules, architecture, patterns |
| 3 | Hooks | `.claude/settings.json` — type-check + commit-blocker |
| 4 | Memory | `MEMORY.md` — initialized index |
| 4.5 | Behavioral patterns | 7 feedback memories (verified Tier 1-2 patterns) |
| 5 | Skills | orchestrateur, smoke-test, deploy-verify, debug, review, audit, task, opensrc-sync |
| 6 | opensrc | Source code of key dependencies for AI context |
| 7 | Verification | All skills tested |
| 8 | Commit | Everything committed |

### The 7 seeded behavioral patterns

These are generic feedback memories validated by real-world experience. They work on any project:

| Pattern | Tier | What it does |
|---------|------|-------------|
| `verify_before_writing` | 1 | Grep/Glob BEFORE creating anything |
| `test_after_change` | 1 | Run tests AFTER every modification |
| `diagnostic_sequence` | 1 | Read the FULL error when something breaks |
| `execute_not_plan` | 2 | Do the thing, don't plan the thing |
| `never_remove_features` | 2 | Change HOW, not WHAT |
| `no_speculation` | 2 | Facts or "I don't know yet" |
| `commit_checkpoints` | 2 | Commit every 3-5 tested changes |

### Hook templates

The bootstrap installs hooks adapted to your stack:

| Hook Type | What | Available for |
|-----------|------|---------------|
| PostToolUse type-check | Auto type-check after every edit | TS, Python, Go, Rust |
| PreToolUse commit-blocker | Block commits with anti-patterns | TS (console.log), Python (except:pass) |
| PostToolUse test-runner | Run tests after edit (optional) | pytest, next build |

---

## Behavioral Patterns Guide

See [`docs/behavioral-patterns.md`](docs/behavioral-patterns.md) for a detailed guide on which AI coding patterns actually work, based on experience and research.

Key insight: **Mechanical enforcement (hooks) > Written rules (CLAUDE.md) > Passive memory**. A hook that blocks a commit is 10x more effective than a rule that says "don't do this."

---

## Usage Examples

```
# Set up a new project
/bootstrap

# Build a feature with Codex reviews
/pipeline Add a search filter to the user dashboard

# Build a feature without Codex
/pipeline Refactor the auth middleware to support JWT rotation
```

## License

MIT
