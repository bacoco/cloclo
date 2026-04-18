# CLoClo — Code Loop Orchestrator: Claude + Codex + CodeRabbit

A Claude Code plugin that works invisibly. You code normally — CLoClo handles the rest:

- **Codex reviews your specs, plans, and code** between each development phase
- **CodeRabbit runs static analysis** on every implementation before verification
- **A persistent wiki compounds your project knowledge** with every change you make
- **UI changes get visual verification** automatically via agent-browser

You never need to call a command. CLoClo detects what you're doing and acts — or use `/coderabbit` to run a CodeRabbit review on demand, outside the pipeline.

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

SuperPowers builds task DAG ──► dependency graph with file reservations
    Tasks without dependencies run in parallel (wave dispatch)
    Each agent gets a structured brief: owned files, read-only, forbidden
    Stakes-based approval: low-risk auto-dispatches, high-risk asks first

SuperPowers executes ──► code (fresh subagent per task, bounded retries)
    Codex does a real code review (git diff, type checks, bug hunting)
    + Adversarial triple-perspective: Skeptic / Devil's Advocate / Edge-Case Hunter
    + Every finding tagged [TOOL], [CODE], or [LLM-JUDGMENT]
    You react
    SuperPowers fixes → re-review loop until convergence (3 iterations max)

CodeRabbit reviews the same commits (static analysis + AI)
    Lint / security / style findings with file:line precision
    Severity mapped to P0/P1/P2/P3
    When CodeRabbit AND Codex flag the same line → [CONSENSUS], severity escalated
    When they disagree → [DISAGREEMENT] surfaced, no averaging
    You react (A/B/C/D/E or free comment)

SuperPowers verifies ──► evidence (commands run, output shown)
    AC compliance report: each acceptance criterion mapped to covering test
    If UI was touched: agent-browser opens each page, takes screenshots, verifies
    Wiki silently ingests the session (decisions, trade-offs, what was learned)
    Checkpoint saved — crash here? Resume from this phase next time
```

You experience this as a natural conversation. CLoClo orchestrates the phases, inserts Codex reviews at the right moments, and feeds everything into the wiki — without you ever typing a command.

### The full pipeline — 9 phases end-to-end

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              /pipeline                                   │
└─────────────────────────────────────────────────────────────────────────┘

  PHASE 1  ► Design                          superpowers:brainstorming
           │  One question at a time, HTML mockups, A/B/C options,
           │  spec self-review, user approval gate
           ▼
           Artifact: 01-spec.md
           │
  PHASE 2  ► Codex Review (spec)             codex-review (spec)
           │  Independent model reads spec, catches ambiguity,
           │  missing edge cases, infeasibility
           ▼
           Artifact: 02-codex-review-spec.md → Decision #1 (A-E)
           │
  PHASE 3  ► Plan                            superpowers:writing-plans
           │  Bite-sized tasks, TDD cycle, complete code blocks,
           │  pre-written commit messages
           ▼
           Artifact: 04-plan.md
           │
  PHASE 4  ► Codex Review (plan)             codex-review (plan)
           │  Verifies plan covers the spec, no circular deps,
           │  code snippets compile against real types
           ▼
           Artifact: 05-codex-review-plan.md → Decision #2 (A-E)
           │
  PHASE 4.5 ► Task DAG + Briefs              inline
           │  Dependency graph, file ownership matrix,
           │  wave dispatch for parallel tasks
           ▼
           Artifacts: 08-task-dag.md, task-briefs/
           │
  PHASE 5  ► Execute                         superpowers:subagent-driven-development
           │  Fresh subagent per task, two-stage review
           │  (spec compliance → code quality), bounded retries
           ▼
           Output: commits on feature branch
           │
  PHASE 6  ► Codex Review (impl)             codex-review (impl)
           │  Reads the diff, verifies impl matches spec,
           │  adversarial triple-perspective pass
           ▼
           Artifact: 07-codex-review-impl.md → Decision #3 (A-E)
           │
  PHASE 6.5 ► CodeRabbit CLI (opt-in)        coderabbit-review
           │  Local static analysis before push.
           │  Skipped by default when Phase 9 runs
           │  (the App reviews on the PR anyway).
           ▼
           Artifact: 07b-coderabbit-review-impl.md → Decision #3b
           │
  PHASE 7  ► Verify                          superpowers:verification-before-completion
           │  Iron Law: NO completion claim without fresh evidence.
           │  AC-level compliance report: every criterion mapped to test.
           ▼
           Artifact: 09-compliance-report.md
           │
  PHASE 7.5 ► Visual Verify (if UI)          agent-browser
           │  Open each affected page, take screenshot,
           │  read + verify every screenshot immediately
           ▼
           Artifacts: screenshots/*.png
           │
  PHASE 8  ► Wiki Ingest (auto)              inline
           │  Session summary, new entity/concept pages,
           │  architecture decisions, patterns + fixes
           ▼
           Artifact: wiki/sources/... + log entry
           │
  PHASE 9  ► Open PR + Multi-Bot Auto-Integrate  superpowers:finishing-a-development-branch
           │  Open PR → wait 10 min → parse bot findings →
           │  auto-apply concrete patches (3 gates) →
           │  push → re-review → loop max 3× →
           │  auto-merge when clean. User stays in terminal.
           │  Escalation ONLY on: cap hit with criticals,
           │  patch failed, CI blocked, P0 disagreement.
           ▼
           Artifact: 10-pr-bot-digest.md + merged PR
```

**Only Phase 1 (brainstorming) requires your input** — that's where design intent lives. Every review phase (2, 4, 6, 6.5, 9) auto-integrates findings under three guardrails and only escalates on genuine blockers. You stay in the terminal from spec approval to merged PR.

**The three auto-apply gates** (identical for spec edits, plan edits, code fixes, and PR bot findings):
1. Reviewer provides a concrete revision or patch — not just "consider X"
2. Not a design pivot (approach A vs B on spec) and not in auth/payments/data-migration
3. No contradictions between reviewers or findings at the same location

**Escalation** happens in the terminal only, never on GitHub. Triggers: design pivot, critical-domain touch, cross-reviewer conflict, iteration cap hit, or patch apply failed. Answer one question and the loop resumes.

**Confidence-first principle** applies everywhere, not just at scheduled escalation points. If the pipeline's confidence on any decision drops below 95% — ambiguous directive, reviewer finding touching out-of-scope code, test failure that could be regression or flake, CI red that could be infra — it asks you with 2-3 concrete options (recommended one marked). Autonomous means applying clear things under gates, not guessing on unclear ones. Free-form text responses are always accepted.

### Smart-resume — re-entering a session mid-pipeline

`/pipeline` takes **no flags**. Two ways to resume:

**1. Dialogue (default when you invoke bare):** the pipeline detects what's done and asks one terminal question.

```
Session "{slug}" a deja :
  ✓ Phase 1 spec    ({path})
  ✓ Phase 3 plan    ({path})
  ✓ Phase 5 commits (branch {branch}, {N} commits ahead of main)

Quoi faire ?
A. Continue avec l'existant (skip ce qui est fait)          ← default
B. Refais tout from Phase 1 (ecrase les artifacts existants)
C. Jumpe a la phase de review (part de Phase 6)
```

Hit Enter for A, or type B / C.

**2. Natural-language directive (write what you want after the command):** skip the dialogue by telling the pipeline directly.

```
/pipeline passe au plan                # skip Phases 1+2, start at Phase 3
/pipeline le code est ecrit, revois    # start at Phase 6 (review+merge)
/pipeline refais tout                  # wipe artifacts, fresh run
/pipeline pas de codex                 # skip Phases 2+4+6 (Codex reviews)
/pipeline pas de PR                    # skip Phase 9
/pipeline ship mode                    # maturity=ship (hard gates, adversarial)
/pipeline passe au plan, pas de codex  # compositional: combine multiple
```

The pipeline interprets French, English, or mixed phrasing. If it's 80% clear, it acts. If truly ambiguous, one clarifying question, then go.

**C is the common case** when code is already written and you just want the review → verify → PR → auto-merge loop. It skips design/plan/execute, runs review + verify on current commits, opens a PR, lets bots review, auto-applies their fixes, merges, deletes the branch.

After a successful auto-merge, the feature branch is deleted both locally and on the remote (`gh pr merge --squash --delete-branch --auto`). If the merge escalates instead, the branch stays alive so you can push manual fixes.

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

**Graph-traversal queries:** Instead of flat keyword search, the wiki classifies questions (factual, relational, analytical, gap, exploratory) and walks the `[[wiki-link]]` graph — shortest path between concepts, neighborhood exploration, shared connections.

**Auto-synthesis:** When a query traverses 4+ pages across 2+ categories, the answer is cached as a synthesis page with `derived-from` backlinks. Next time someone asks a similar question, the wiki already has the answer.

**PII protection:** Every wiki write is scanned for emails, API keys, passwords, and private key headers. Matches block the write and warn the user.

### Codex reviews (independent verification)

[Codex](https://github.com/openai/codex-plugin-cc) freely explores your codebase (30-80+ files) and verifies that specs, plans, and code actually match reality. It catches things Claude missed. You see the findings and decide what to do — integrate, ignore, or dig deeper.

If Codex is unavailable (not installed, usage limits, auth issues), CLoClo falls back to a Claude subagent for reviews. Less independent than Codex (same model family), but still catches real bugs because the reviewer has fresh context. Reviews are never skipped entirely.

**Adversarial triple-perspective:** After every review, three mandatory failure-seeking perspectives run — Skeptic ("which assumption is wrong?"), Devil's Advocate ("how could this fail?"), Edge-Case Hunter ("what input causes silent failure?"). Prevents rubber-stamp PASS verdicts.

**Evidence tagging:** Every finding is tagged `[TOOL]` (test/lint output), `[CODE]` (file:line evidence), or `[LLM-JUDGMENT]` (reasoning only). Low-evidence reviews are flagged.

**Convergence loop:** In `ship` maturity, reviews iterate until convergence — fix findings, re-review changed files, repeat up to 3 times. Findings can be PASS, FAIL (auto-fix), ESCALATE (ask user), or DEFER (acknowledged risk).

**Consensus matrix:** When both Codex and Claude review, spread detection flags disagreements (one says P0, other says P2). Highest severity from any model wins.

### CodeRabbit reviews (static analysis + AI)

[CodeRabbit CLI](https://cli.coderabbit.ai) complements Codex. Where Codex catches architectural and spec-compliance issues by exploring the codebase, CodeRabbit catches lint, security, and style issues with static-analysis backing. The pipeline runs both at Phase 6 / Phase 6.5 — Codex first (architecture), then CodeRabbit (static) on the same commit range.

```bash
# What CLoClo runs under the hood at Phase 6.5
coderabbit review --agent --type committed --base <base_ref>
```

**When one reviewer flags something:** presented as-is, decision point A-E (integrate all / some / ignore / dig deeper / edit yourself).

**When BOTH flag the same file:line:** marked `[CONSENSUS]`, severity escalated to the higher of the two, presented first.

**When they disagree** (Codex says P2, CodeRabbit says P0, or vice versa): marked `[DISAGREEMENT]`, both opinions surfaced explicitly — no averaging, no hiding the split.

**Standalone command:** `/coderabbit` runs a CodeRabbit review on your current changes (committed or uncommitted) without going through the full pipeline. Useful before opening a PR, or to sanity-check a quick fix.

**Install:** `curl -fsSL https://cli.coderabbit.ai/install.sh | sh` then `coderabbit auth login` once. Missing CodeRabbit is non-blocking — Phase 6.5 skips with a warning; Codex is still the gating reviewer.

### Model selection (Opus quota optimization)

CLoClo uses a mixed-model strategy to balance review quality against Max plan weekly Opus cap (24-40h/week vs 240-480h/week for Sonnet).

- **Reviewers (spec, plan, impl — Codex fallback)** → **Opus 4.7** — the +8 pts SWE-bench Verified gap over Sonnet 4.6 catches real cross-file bugs.
- **Implementer subagents (1-2 files, clear spec)** → **Sonnet 4.6** — mechanical work where Opus adds no measurable quality.
- **Implementer subagents (>5 files, architecture)** → **Opus 4.7** — cross-file coherence required.
- **DAG building, verification, visual verification** → **Sonnet 4.6** — scripted / tools-driven.
- **Brainstorming, writing-plans, reviewers** → **Opus 4.7** — design judgment.
- **Adversarial triple-perspective pass** → **Haiku 4.5** — read-only questions.

See [Model Selection Policy](plugins/cloclo/skills/pipeline/SKILL.md#model-selection-policy) in the pipeline skill for the full matrix.

### Visual verification (agent-browser)

After UI changes, [agent-browser](https://github.com/vrsalis/agent-browser) opens the affected pages, takes screenshots, and verifies the UI matches the spec. If agent-browser is not installed, visual verification is skipped with a warning.

### PR-first workflow + multi-bot review + auto-integration (Phase 9)

Since 0.5.0, the pipeline ends by opening a **Pull Request** instead of merging to main. The PR triggers every review bot installed on the repo, then CLoClo **auto-applies** the concrete patches the bots suggest, re-reviews, and **auto-merges** when clean. You stay in the terminal — GitHub is only opened when the autonomous loop genuinely cannot resolve (iteration cap hit, patch failed, CI blocked, critical disagreement).

**What "auto-apply" means:** a bot finding is applied automatically only when (1) the bot provides a concrete diff or file:line+replacement, (2) the finding is not in auth / payments / data migration domain, and (3) no two bots propose conflicting patches on the same line. Everything else is logged and skipped. Iteration cap = 3 rounds, then escalate.

**Escape hatch:** if you want manual control, answer `B` (redo all) or `C` (jump to review) at the smart-resume prompt, or edit the session dir before re-running `/pipeline`.

**Default bots** (install once, review every PR automatically):

| Bot | Install URL | Focus |
|-----|-------------|-------|
| CodeRabbit | [github.com/apps/coderabbitai](https://github.com/apps/coderabbitai) | Inline nits, security, summary |
| Gemini Code Assist | [github.com/apps/gemini-code-assist](https://github.com/apps/gemini-code-assist) | High-level architecture |

**Opt-in bots** (add to the stack only when the extra angle is worth the config overhead):

| Bot | Install URL | Focus |
|-----|-------------|-------|
| Codex Cloud | [chatgpt.com/codex](https://chatgpt.com/codex) | Spec compliance, test coverage |
| Claude Code Action | [anthropics/claude-code-action](https://github.com/anthropics/claude-code-action) | Claude review via GitHub Actions |

**Default stack** = CodeRabbit + Gemini. Two angles, both zero-config after install, both post reviews directly on the PR. Adding Codex Cloud or Claude Code Action is an explicit opt-in per repo.

**Why Codex Cloud is opt-in (not default).** Phases 2, 4, and 6 already invoke Codex on the spec, plan, and implementation — three independent Codex passes against the same code before the PR opens. Polling the Codex Cloud GitHub bot on the PR duplicates that work, consumes extra quota, and surfaces near-identical findings in different words, which creates noise in the auto-integration loop. Enable it only when the repo has external contributors whose code did not pass through CLoClo's own Codex gates, or set `bots.codex_cloud: true` in `pipeline.config.md` for a permanent per-repo opt-in. The per-session form is `/pipeline avec codex cloud`.

**Direct merges to main** are reserved for trivial out-of-pipeline changes (typos, config one-liners). Anything substantive goes through a PR. Phase 9 is skipped only on `maturity: spike` (prototyping) or when there's no git remote configured.

**Phase 6.5 CodeRabbit CLI becomes opt-in** when Phase 9 runs (the GitHub App will review the PR anyway). Enable 6.5 explicitly on `ship` maturity for defense-in-depth, or when the App is not installed on the repo.

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
    │     Codex reviews between phases (adversarial + evidence-tagged)
    │     CodeRabbit CLI runs static analysis (opt-in when Phase 9 active)
    │     agent-browser verifies UI
    │     Pipeline opens a PR → all installed bots review in parallel
    │     (CodeRabbit App, Gemini, Codex Cloud, Claude Action)
    │     User reviews bot digest → merges when ready
    │     Checkpoint saved after each phase (crash-safe)
    ├─► You commit → wiki updates (automatic, PII-protected)
    ├─► You ask questions → wiki answers with graph traversal + citations
    ├─► Something goes wrong → /rollback (soft or hard)
    └─► Session ends → handoff.md written for next session continuity
```

**Maturity levels** control how strictly CLoClo runs:

| Level | Gate strictness | Agents | Reviews |
|-------|----------------|--------|---------|
| `spike` | Soft (skip freely) | 1 | Optional |
| `dev` | Standard (A-E decisions) | Up to 3 | All phases |
| `ship` | Hard (documented skip only) | Up to 5 | Adversarial + convergence loop |

Auto-detected from project state (no tests → spike, CI passing → ship), or set manually in `pipeline.config.md`.

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

CLoClo has five skills that you can call explicitly if needed, but rarely should:

| Skill | What | When to call explicitly |
|-------|------|----------------------|
| `cloclo:pipeline` | Full dev cycle with Codex reviews | Almost never — CLoClo detects feature requests |
| `cloclo:wiki` | Wiki operations (init, ingest, query, lint) | `/wiki lint` for health checks, `/wiki ingest <file>` for manual sources |
| `cloclo:bootstrap` | Project setup | Almost never — CLoClo offers setup on first session |
| `cloclo:rollback` | Undo pipeline commits (soft or hard) | When you need to undo work from a pipeline run |
| `cloclo:codex-review` | Review a spec, plan, or implementation | Almost never — pipeline calls it automatically |

## Coexistence with SuperPowers

CLoClo complements SuperPowers — it never duplicates or overrides:

| | SuperPowers | CLoClo adds |
|---|-----------|-------------|
| **Workflow** | Brainstorming, planning, execution, verification | Codex reviews between phases, maturity levels (spike/dev/ship) |
| **Knowledge** | Conversation memory | Persistent wiki (graph-traversal queries, auto-synthesis, PII protection) |
| **Visual** | — | agent-browser verification after UI changes |
| **Quality gates** | — | Convergence-gated critic loops, adversarial triple-perspective, AC compliance reports |
| **Resilience** | — | Checkpoint/resume, session handoff, bounded retries, rollback |
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
