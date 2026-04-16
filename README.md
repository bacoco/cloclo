# CLoClo — Code Loop Orchestrator: Claude + Codex

A Claude Code plugin that works invisibly. You code normally — CLoClo handles the rest:

- **Codex reviews your specs, plans, and code** between each development phase
- **A persistent wiki compounds your project knowledge** with every change you make
- **UI changes get visual verification** automatically via agent-browser

You never need to call a command. CLoClo detects what you're doing and acts.

## Installation

Tell Claude Code:

```
Install the CLoClo plugin from marketplace bacoco/cloclo on GitHub
```

Restart when prompted. That's it. CLoClo is now active on every session.

## What Happens When You Work

### You say "add a search filter to the dashboard"

CLoClo detects a feature request. Behind the scenes:

```
SuperPowers brainstorms with you ──► spec
    Codex independently reviews the spec
    You react ("integrate all" / "point 2 is wrong" / anything)
    SuperPowers rewrites ──► final spec

SuperPowers writes the plan ──► implementation plan
    Codex independently reviews the plan
    You react
    SuperPowers rewrites ──► final plan

SuperPowers executes ──► code (fresh subagent per task)
    Codex does a real code review (git diff, type checks, bug hunting)
    You react
    SuperPowers fixes

SuperPowers verifies ──► evidence (commands run, output shown)
    If UI was touched: agent-browser opens each page, takes screenshots, verifies
    Wiki silently ingests the session (decisions, trade-offs, what was learned)
```

You experience this as a natural conversation. CLoClo orchestrates the phases, inserts Codex reviews at the right moments, and feeds everything into the wiki — without you ever typing a command.

### You commit code

CLoClo notices. If the change was significant, it silently updates wiki pages — new components get entity pages, architecture decisions become concept pages, patterns get documented.

### You ask "why did we choose JWT over sessions?"

CLoClo checks the wiki first. It finds the architecture decision page from three weeks ago, cites the spec that led to it, and points to the raw source document. The answer comes with provenance.

### You edit a `.tsx` file

CLoClo reminds Claude to verify the change visually with agent-browser before moving on. Screenshots are saved as evidence.

## How It Works

### Always-on hooks (invisible)

CLoClo installs three hooks that fire automatically:

| Hook | When | What it does |
|------|------|-------------|
| **SessionStart** | Every session opens | Injects wiki state into Claude's context — Claude knows your project history |
| **PostToolUse** (commit) | After `git commit` | Nudges Claude to update relevant wiki pages |
| **PostToolUse** (UI edit) | After editing `.tsx/.vue/.css/...` | Reminds Claude to verify with agent-browser |

These are complementary to [SuperPowers](https://github.com/obra/superpowers). SuperPowers handles the workflow (brainstorming, planning, execution). CLoClo adds the review layer (Codex), the knowledge layer (wiki), and the visual layer (agent-browser).

### The wiki (persistent, compounding)

Based on [Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). Claude maintains a structured knowledge base that grows with your project:

```
wiki/
  schema.md     ← conventions (like CLAUDE.md, but for the wiki)
  index.md      ← master catalog — Claude reads this at every session start
  log.md        ← what happened and when
  sources/      ← raw documents (articles, specs, papers — immutable)
  pages/        ← Claude-maintained pages (entities, concepts, decisions, syntheses)
```

The wiki builds up automatically from pipeline sessions and commits. You never organize anything — Claude does the bookkeeping.

### Codex reviews (independent verification)

[Codex](https://github.com/openai/codex-plugin-cc) freely explores your codebase (30-80+ files) and verifies that specs, plans, and code actually match reality. It catches things Claude missed. You see the findings and decide what to do — integrate, ignore, or dig deeper.

If Codex is unavailable (not installed, usage limits, auth issues), CLoClo falls back to a Claude subagent for reviews. Less independent than Codex (same model family), but still catches real bugs because the reviewer has fresh context. Reviews are never skipped entirely.

### Visual verification (agent-browser)

After UI changes, [agent-browser](https://github.com/vrsalis/agent-browser) opens the affected pages, takes screenshots, and verifies the UI matches the spec. If agent-browser is not installed, visual verification is skipped with a warning.

## First-time setup on a new project

On the first session in a new project, CLoClo offers to set up infrastructure:

- `CLAUDE.md` adapted to your actual stack
- Hooks (type-check after edits, commit blockers for anti-patterns)
- Memory (7 behavioral patterns validated by experience)
- Wiki scaffold (empty, fills up as you work)
- Skills adapted to your services

This happens once. After that, everything is automatic.

## The full picture

```
Install CLoClo (once)
    ↓
First session: infrastructure setup (once)
    ↓
Every session after that:
    ├─► Wiki state loaded into Claude's context (automatic)
    ├─► You describe what you want → full dev cycle runs (automatic)
    │     SuperPowers handles workflow
    │     Codex reviews between phases
    │     agent-browser verifies UI
    ├─► You commit → wiki updates (automatic)
    └─► You ask questions → wiki answers with citations (automatic)
```

The loop: **build → review → verify → learn → build better next time.**

## Pause / Resume

Sometimes you just want plain Claude Code without CLoClo's hooks. One command:

```
cloclo off        # creates .cloclo-disabled — all hooks go silent
cloclo on         # removes .cloclo-disabled — CLoClo resumes
```

Or just tell Claude: "pause CLoClo" / "resume CLoClo". It creates or removes the file.

When paused, the SessionStart hook injects a single line: *"CLoClo is paused."* Everything else is silent. Your wiki, skills, and session files stay untouched — nothing is lost.

---

## Under the hood

CLoClo has three skills that you can call explicitly if needed, but rarely should:

| Skill | What | When to call explicitly |
|-------|------|----------------------|
| `cloclo:pipeline` | Full dev cycle with Codex reviews | Almost never — CLoClo detects feature requests |
| `cloclo:wiki` | Wiki operations (init, ingest, query, lint) | `/wiki lint` for health checks, `/wiki ingest <file>` for manual sources |
| `cloclo:bootstrap` | Project setup | Almost never — CLoClo offers setup on first session |

## Coexistence with SuperPowers

CLoClo complements SuperPowers — it never duplicates or overrides:

| | SuperPowers | CLoClo adds |
|---|-----------|-------------|
| **Workflow** | Brainstorming, planning, execution, verification | Codex reviews between phases |
| **Knowledge** | Conversation memory | Persistent wiki (cross-referenced, queryable, compounding) |
| **Visual** | — | agent-browser verification after UI changes |
| **Hooks** | Skill invocation rules | Wiki state + visual verification reminders |

Both SessionStart hooks run and concatenate. No conflict.

## Behavioral patterns

CLoClo seeds 7 behavioral patterns validated by real-world experience:

| Pattern | What |
|---------|------|
| Verify before writing | Grep/Glob BEFORE creating anything |
| Test after change | Run tests AFTER every modification |
| Diagnostic sequence | Read the FULL error when something breaks |
| Execute, don't plan | Do the thing, don't write a plan about doing the thing |
| Never remove features | Change HOW, not WHAT |
| No speculation | Facts or "I don't know yet" |
| Commit checkpoints | Commit every 3-5 tested changes |

Key insight: **Hooks that block > Rules in CLAUDE.md > Passive memory**. See [`docs/behavioral-patterns.md`](docs/behavioral-patterns.md) for details.

## License

MIT
