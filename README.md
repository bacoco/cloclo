# CLoClo — Code Loop Orchestrator: Claude + Codex

A Claude Code plugin with three superpowers:

1. **`/pipeline`** — Inserts independent [Codex](https://github.com/openai/codex-plugin-cc) reviews into the [SuperPowers](https://github.com/obra/superpowers) workflow. Design, review, plan, review, execute, review, verify — and auto-feed everything into the wiki.

2. **`/bootstrap`** — Sets up Claude Code infrastructure on any new project. CLAUDE.md, hooks, memory, skills, wiki, behavioral patterns — all adapted to your actual stack.

3. **`/wiki`** — LLM-maintained persistent knowledge base. Ingest sources, query knowledge, lint for quality. Based on [Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). The wiki grows transparently as you work.

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

**Phase 7.5 — Visual verification (if UI modified).**
If the implementation touched UI files and agent-browser is installed, it opens each affected page, takes screenshots, and verifies the UI matches the spec. Screenshots are saved as evidence. If agent-browser is not available, visual verification is skipped with a warning.

**Phase 8 — Wiki auto-ingest.**
If a project wiki exists, CLoClo automatically distills the session — decisions, trade-offs, Codex findings, architecture choices — into wiki pages. This is silent and transparent. Your project knowledge compounds with every pipeline run.

### Summary

```
SuperPowers brainstorms ──► spec
                              ↓ Codex reviews ↓ you react ↓ SuperPowers rewrites
SuperPowers writes plan ──► plan
                              ↓ Codex reviews ↓ you react ↓ SuperPowers rewrites
SuperPowers executes    ──► code
                              ↓ Codex reviews ↓ you react ↓ SuperPowers fixes
SuperPowers verifies    ──► done
                              ↓ agent-browser visual check (if UI)
                              ↓ wiki auto-ingest (silent)
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

## /wiki — LLM Knowledge Base

A persistent wiki that grows as you work. Claude does the bookkeeping — summaries, cross-references, contradictions, index maintenance. You curate sources and ask questions.

Based on [Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

### How It Works

```
wiki/
  schema.md     ← conventions (like CLAUDE.md, but for the wiki)
  index.md      ← master catalog — Claude reads this FIRST
  log.md        ← append-only operation history
  sources/      ← your raw documents (immutable)
  pages/        ← Claude-maintained wiki pages
    entities/     people, tools, organizations
    concepts/     ideas, patterns, principles
    topics/       broader themes
    comparisons/  X vs Y analysis
    syntheses/    cross-cutting analysis
    sources/      per-source summaries
```

### Three Layers

1. **Raw sources** (`sources/`) — Articles, papers, docs you drop in. Claude reads, never modifies.
2. **Wiki pages** (`pages/`) — Claude owns entirely. Summaries, entity pages, cross-references.
3. **Schema** (`schema.md`) — Tells Claude how the wiki is structured.

### Commands

| Command | What |
|---------|------|
| `/wiki init` | Set up wiki scaffold (one question: what domain?) |
| `/wiki ingest <path>` | Read source, extract knowledge, update 5-15 wiki pages |
| `/wiki query <question>` | Answer from wiki with citations |
| `/wiki lint` | Health-check: orphans, broken links, stubs, contradictions |
| `/wiki status` | Quick stats and recent activity |

### Transparent Integration

**You rarely need to call `/wiki` manually.** The wiki grows automatically:

- **`/pipeline`** auto-ingests session artifacts (specs, plans, reviews, decisions) into the wiki after Phase 7.
- **`/bootstrap`** creates the wiki scaffold as part of project setup.
- **`/wiki query`** is there when you need to ask the wiki a question.
- **`/wiki lint`** is there for periodic health checks.

The knowledge compounds silently. After 10 pipeline runs, you have a rich project wiki documenting every design decision, every Codex finding, every architecture choice — without ever having manually organized anything.

### Key Insight

> "The tedious part of maintaining a knowledge base is not the reading...it's the bookkeeping."
> — Karpathy

LLMs handle the bookkeeping cost-free. You focus on building; the wiki maintains itself.

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
| 5.5 | Wiki | `wiki/` — persistent knowledge base scaffold |
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

## How Everything Connects

```
/bootstrap
  └─► Sets up: CLAUDE.md + hooks + memory + skills + wiki + opensrc
        ↓
/pipeline <task>  (or just describe the task — CLoClo detects intent)
  ├─► SuperPowers brainstorms ──► spec
  │     ↓ Codex reviews ↓ you react ↓ rewrite
  ├─► SuperPowers plans ──► plan
  │     ↓ Codex reviews ↓ you react ↓ rewrite
  ├─► SuperPowers executes ──► code
  │     ↓ Codex reviews ↓ you react ↓ fix
  ├─► SuperPowers verifies ──► done
  ├─► agent-browser visual check (if UI modified)
  └─► Wiki auto-ingest ──► knowledge compounds
        ↓
/wiki query "why did we choose X?"
  └─► Answer from accumulated project knowledge, with citations
```

The loop is: **build → review → verify → see → learn → build better next time.**

### Coexistence with SuperPowers

CLoClo is designed to **complement** SuperPowers, not compete with it:

| Concern | SuperPowers handles | CLoClo adds |
|---------|-------------------|-------------|
| **Workflow** | Brainstorming, planning, execution, verification | Codex reviews between phases |
| **Knowledge** | Session memory (conversation context) | Persistent wiki (cross-referenced, queryable) |
| **Visual testing** | — | agent-browser verification after UI changes |
| **Hooks** | SessionStart: skill invocation rules | SessionStart: wiki state + visual verification rules |

Both plugins' SessionStart hooks run and concatenate. They inject different, complementary context:
- SuperPowers: "check for skills before acting"
- CLoClo: "here's the wiki state, update it after changes, verify UI with agent-browser"

No conflict because CLoClo never injects workflow rules (brainstorming, planning steps) — that's SuperPowers' territory.

---

## Behavioral Patterns Guide

See [`docs/behavioral-patterns.md`](docs/behavioral-patterns.md) for a detailed guide on which AI coding patterns actually work, based on experience and research.

Key insight: **Mechanical enforcement (hooks) > Written rules (CLAUDE.md) > Passive memory**. A hook that blocks a commit is 10x more effective than a rule that says "don't do this."

---

## Usage Examples

```
# Set up a new project (includes wiki)
/bootstrap

# Build a feature with Codex reviews (auto-feeds wiki)
/pipeline Add a search filter to the user dashboard

# Query accumulated project knowledge
/wiki query "what authentication approach did we choose and why?"

# Manually ingest an external article
/wiki ingest docs/research/oauth2-best-practices.md

# Health-check the wiki
/wiki lint
```

## License

MIT
