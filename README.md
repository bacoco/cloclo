# CLoClo — Code Loop Orchestrator: Claude + Codex + GLM + CodeRabbit + Gemini (Codex Cloud opt-in)

A Claude Code plugin that works invisibly. You code normally — CLoClo handles the rest:

- **Claude generates; Codex + GLM verify.** Two independent frontier models review your specs, plans, and code in parallel between each development phase — with a consensus matrix for agreement/disagreement.
- **CodeRabbit runs static analysis** on every implementation, and Gemini Code Assist reviews the PR.
- **A persistent wiki compounds your project knowledge** with every change you make.
- **UI changes get visual verification** automatically via agent-browser.

You never need to call a command. CLoClo detects what you're doing and acts — findings are auto-integrated under guardrails, and the pipeline only escalates on genuine blockers. Or use `/coderabbit` / `/glm` for a standalone review.

**GLM-5.2 is optional.** Set `ZAI_API_KEY` or `GLM_API_KEY` in your shell. Missing key = silent skip; Codex still reviews every phase alone.

## Installation

The canonical two-step flow in Claude Code:

```bash
claude plugin marketplace add bacoco/cloclo
claude plugin install cloclo@cloclo
```

Restart when prompted. CLoClo is now active on every session.

Prefer conversational install? Just tell Claude Code:

```
Install the CLoClo plugin from marketplace bacoco/cloclo on GitHub
```

## What's inside

CLoClo ships **8 skills**, **2 slash commands**, and **3 always-on hooks**. Almost everything runs automatically — you rarely call a skill by name.

### Skills

| Skill | What it does | When to call explicitly |
|-------|--------------|-------------------------|
| `cloclo:pipeline` | Full dev cycle (design → review → plan → review → execute → review → verify → PR → auto-merge) | Almost never — CLoClo detects feature requests |
| `cloclo:wiki` | Persistent LLM wiki: init, ingest, query, lint | `/wiki lint` for health checks, `/wiki ingest <file>` for manual sources |
| `cloclo:bootstrap` | First-time project setup (CLAUDE.md, hooks, memory, skills, wiki) | Almost never — offered on first session |
| `cloclo:rollback` | Undo pipeline work — soft (uncommit) or hard (revert) | When you need to undo a pipeline run |
| `cloclo:toggle` | Turn CLoClo on/off/status (creates or removes `.cloclo-disabled`) | `cloclo off` / `cloclo on` / `cloclo status` |
| `cloclo:codex-review` | Codex CLI review of a spec, plan, or impl (Claude subagent fallback) | Almost never — pipeline calls it |
| `cloclo:glm-review` | GLM-5.2 review via Z.ai Anthropic-compatible endpoint (no fallback) | Almost never — pipeline calls it |
| `cloclo:coderabbit-review` | Local CodeRabbit CLI review of a git diff | Almost never — pipeline calls it |

### Commands

| Command | What it does |
|---------|--------------|
| `/coderabbit` | Standalone CodeRabbit CLI review of current changes (committed or uncommitted) |
| `/glm` | Standalone GLM-5.2 review of current changes via Z.ai |

### Hooks

| Hook | When | What it does |
|------|------|--------------|
| SessionStart (`session-start.sh`) | Every session opens | Injects wiki state into Claude's context (or a single "paused" line when disabled) |
| PostToolUse commit (`post-commit.sh`) | After `git commit` | Nudges Claude to update relevant wiki pages |
| PostToolUse UI edit (`post-ui-edit.sh`) | After editing `.tsx/.vue/.css/...` | Reminds Claude to verify with agent-browser |

## How the pipeline works

You describe a feature; CLoClo runs a structured cycle. Claude generates each artifact, independent reviewers verify it, findings auto-integrate under guardrails, and the loop only stops to ask you when confidence is genuinely low.

```
Design (brainstorm)  ─►  spec
    └─ Codex + GLM review the spec (parallel)  ─► auto-integrate
Plan                 ─►  implementation plan
    └─ Codex + GLM review the plan (parallel)  ─► auto-integrate
Execute              ─►  commits (fresh subagent per task, bounded retries)
    └─ Codex + GLM review the diff + CodeRabbit static analysis  ─► auto-integrate
Verify               ─►  evidence (commands run, AC compliance)
    └─ If UI touched: agent-browser screenshots + verify
Wiki ingest          ─►  session decisions folded into the wiki
Open PR              ─►  installed bots review → auto-apply patches → auto-merge
```

**Decision model — auto-integration.** Only the design phase requires your input; that's where intent lives. Every review phase auto-applies findings under three gates and only escalates in the terminal (never on GitHub) on a genuine blocker:

1. The reviewer gives a concrete revision or patch — not just "consider X".
2. It's not a design pivot and not in auth / payments / data-migration.
3. No contradiction between reviewers at the same location.

Escalation triggers: design pivot, critical-domain touch, cross-reviewer conflict, iteration cap hit (3 rounds), or a patch that failed to apply. A **confidence-first** rule runs everywhere: if confidence on any decision drops below 95%, the pipeline asks one question with 2-3 concrete options instead of guessing.

**Reviewers.** Claude generates the work. Codex CLI (OS-level read-only sandbox), GLM-5.2 (Z.ai), CodeRabbit CLI, and — on the PR — Gemini Code Assist verify it. Codex Cloud is opt-in (`/pipeline avec codex cloud` or `bots.codex_cloud: true`) since Phases 2/4/6 already run Codex against the same code.

The pipeline reference files are the single source of truth for the details:

- [Phases](plugins/cloclo/skills/pipeline/references/phases.md) — every phase end-to-end
- [Model policy](plugins/cloclo/skills/pipeline/references/model-policy.md) — which model runs each role
- [Review chain](plugins/cloclo/skills/pipeline/references/review-chain.md) — Codex / GLM / CodeRabbit interplay, consensus matrix
- [Confidence-first](plugins/cloclo/skills/pipeline/references/confidence-first.md) — when the loop stops to ask
- [Smart-resume](plugins/cloclo/skills/pipeline/references/smart-resume.md) — re-entering a session mid-pipeline
- [Bot stack](plugins/cloclo/skills/pipeline/references/bot-stack.md) — PR bots, defaults vs opt-in
- [Session files](plugins/cloclo/skills/pipeline/references/session-files.md), [retries](plugins/cloclo/skills/pipeline/references/retries.md), [prerequisites](plugins/cloclo/skills/pipeline/references/prerequisites.md)

## The wiki

An LLM-maintained knowledge base (based on [Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)) that grows from pipeline sessions and commits. Claude does the bookkeeping — you curate sources and ask questions. Graph-traversal queries walk the `[[wiki-link]]` graph, frequent multi-page answers get cached as synthesis pages, and every write is PII-scanned. See the [`cloclo:wiki`](plugins/cloclo/skills/wiki/SKILL.md) skill.

## First-time setup

On the first session in a new project, `cloclo:bootstrap` offers to set up a `CLAUDE.md` adapted to your stack, mechanical hooks, seven behavioral-pattern memories, a wiki scaffold, and skills adapted to your services. It happens once; after that everything is automatic. See [`cloclo:bootstrap`](plugins/cloclo/skills/bootstrap/SKILL.md).

## Pause / resume

```
cloclo off        # creates .cloclo-disabled — all hooks go silent
cloclo on         # removes it — CLoClo resumes
cloclo status     # report current state
```

Or just tell Claude "pause CLoClo" / "resume CLoClo". When paused, SessionStart injects a single "CLoClo is paused" line; your wiki, skills, and session files stay untouched. See [`cloclo:toggle`](plugins/cloclo/skills/toggle/SKILL.md).

## Coexistence with SuperPowers

CLoClo complements [SuperPowers](https://github.com/obra/superpowers) — it never duplicates or overrides. SuperPowers owns the workflow (brainstorming, planning, execution, verification); CLoClo adds the review layer (Codex + GLM), the static-analysis layer (CodeRabbit), the knowledge layer (wiki), and the visual layer ([agent-browser](https://github.com/vercel-labs/agent-browser)). Both SessionStart hooks run and concatenate — no conflict.

## Behavioral patterns

Bootstrap seeds 7 behavioral patterns validated by real-world experience: verify before writing, test after change, diagnostic sequence, execute don't plan, never remove features, no speculation, and commit checkpoints. Key insight: **hooks that block > rules in CLAUDE.md > passive memory**. See [`docs/behavioral-patterns.md`](docs/behavioral-patterns.md).

## License

[MIT](LICENSE) © 2026 Loic Baconnier
