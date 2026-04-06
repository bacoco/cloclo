# CLOco — Claude + Codex Collaboration

A Claude Code plugin that inserts Codex reviews into the [SuperPowers](https://github.com/obra/superpowers) workflow.

**SuperPowers does all the work.** CLOco just passes each artifact to Codex for an independent review before SuperPowers continues to the next phase.

## The Flow

**Without CLOco** (SuperPowers alone):
```
superpowers:brainstorming ──► spec
superpowers:writing-plans ──► plan
superpowers:subagent-driven-development ──► code
superpowers:verification-before-completion ──► done
```

**With CLOco** (same flow, Codex reviews inserted):
```
superpowers:brainstorming ──► spec
    ↓
    Codex reviews the spec (reads your codebase, writes findings to a file)
    You read the findings, react however you want
    SuperPowers rewrites the spec
    ↓
superpowers:writing-plans ──► plan
    ↓
    Codex reviews the plan (same thing)
    You react, SuperPowers rewrites the plan
    ↓
superpowers:subagent-driven-development ──► code
    ↓
    Codex reviews the implementation (git diff, full file reads)
    You react, SuperPowers fixes
    ↓
superpowers:verification-before-completion ──► done
```

SuperPowers handles everything: the brainstorming with visual mockups, the question-by-question UX exploration, the spec writing, the plan with TDD tasks, the subagent execution, the verification. CLOco only adds the Codex review steps between phases.

## What Codex Does

Codex (GPT-5.4) is invoked as an independent reviewer between SuperPowers phases. It:
- Reads the artifact SuperPowers just produced (spec, plan, or code)
- Explores your codebase freely (30-80+ files, 2-10 minutes)
- Writes findings to a markdown file in the session directory

SuperPowers then reads the findings and presents them to you. You react however you want — natural language, just like normal SuperPowers interaction. SuperPowers rewrites the artifact based on the findings and your feedback, then continues to the next phase.

This is the same loop you already do manually when you open Codex in a separate terminal and paste findings back — CLOco automates the file exchange.

## Prerequisites

CLOco depends on two plugins. Install them first.

### SuperPowers (required — does all the real work)

Add to `~/.claude/settings.json`:

```json
{
  "enabledPlugins": {
    "superpowers@superpowers-marketplace": true
  },
  "extraKnownMarketplaces": {
    "superpowers-marketplace": {
      "source": {
        "source": "github",
        "repo": "obra/superpowers-marketplace"
      }
    }
  }
}
```

Restart Claude Code.

### Codex (optional but recommended — the reviewer)

```bash
npm install -g @openai/codex
codex login
```

Then add to `~/.claude/settings.json`:

```json
{
  "enabledPlugins": {
    "codex@openai-codex": true
  },
  "extraKnownMarketplaces": {
    "openai-codex": {
      "source": {
        "source": "github",
        "repo": "openai/codex-plugin-cc"
      }
    }
  }
}
```

Without Codex, CLOco is just SuperPowers — review phases are skipped.

## Install CLOco

```bash
git clone https://github.com/bacoco/cloco.git ~/.claude/plugins/marketplaces/cloco
```

Add to `~/.claude/settings.json`:

```json
{
  "enabledPlugins": {
    "cloco@cloco": true
  }
}
```

Restart Claude Code.

## Usage

```
/pipeline
```

Or just describe what you want to build.

## Session Files

```
docs/cloco-sessions/YYYY-MM-DD-<slug>/
├── 01-spec.md                  ← SuperPowers brainstorming
├── 02-codex-review-spec.md     ← Codex findings on the spec
├── 03-spec-v2.md               ← SuperPowers rewrites after feedback
├── 04-plan.md                  ← SuperPowers writing-plans
├── 05-codex-review-plan.md     ← Codex findings on the plan
├── 06-plan-v2.md               ← SuperPowers rewrites after feedback
├── 07-codex-review-impl.md     ← Codex findings on the code
├── session.log                 ← Decisions + timestamps
└── pipeline.config.md          ← Optional verification config
```

## License

MIT
