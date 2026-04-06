# CLOco — Claude + Codex Collaboration

A Claude Code plugin that inserts [Codex](https://github.com/openai/codex-plugin-cc) reviews into the [SuperPowers](https://github.com/obra/superpowers) workflow.

SuperPowers already does everything well: interactive brainstorming with a visual companion server, one-question-at-a-time UX exploration, spec writing, implementation plans with TDD, subagent execution, verification. CLOco does not touch any of that.

What CLOco adds: after each SuperPowers phase produces an artifact (spec, plan, or code), Codex independently reviews it against your real codebase. The findings come back, you react naturally, and SuperPowers takes over again to integrate and continue.

## How It Works

### Example session

You open Claude Code in your project and type:

```
/pipeline I want to add a search filter to the dashboard
```

Here is what happens:

**Phase 1 — SuperPowers brainstorms.**
SuperPowers asks you questions one at a time. If it involves UI, it starts a local server with HTML mockups in your browser — you click to choose between options A, B, C. It proposes 2-3 approaches with trade-offs. You pick. It writes a spec, self-reviews it, shows it to you. You approve (or ask for changes).

**Phase 2 — Codex reviews the spec.**
CLOco sends the spec to Codex. Codex reads it, then freely explores your codebase (30-80+ files, 2-10 minutes). It checks that every file, function, and line mentioned in the spec actually exists. It writes its findings to a file.

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

## Installation

Add these two entries to your `~/.claude/settings.json` and restart Claude Code:

```json
{
  "enabledPlugins": {
    "cloco@cloco": true
  },
  "extraKnownMarketplaces": {
    "cloco": {
      "source": {
        "source": "github",
        "repo": "bacoco/cloco"
      }
    }
  }
}
```

That's it. Claude Code downloads CLOco from GitHub automatically.

On first run, `/pipeline` checks for SuperPowers and Codex. If either is missing, it installs them for you:

- **SuperPowers missing:** CLOco adds it to your `settings.json` and tells you to restart.
- **Codex CLI missing:** CLOco runs `npm install -g @openai/codex` and prompts `codex login`.
- **Codex plugin missing:** CLOco adds it to your `settings.json` and tells you to restart.

## Usage

```
/pipeline <describe what you want to build>
```

Examples:
```
/pipeline Add a search filter to the user dashboard
/pipeline Refactor the auth middleware to support JWT rotation
/pipeline Build a CSV export feature for the reports page
```

You can also just describe what you want without `/pipeline` — CLOco triggers automatically when it detects creative or implementation work.

### Without Codex

If Codex is not installed or not authenticated, CLOco skips the review phases. You get pure SuperPowers — still excellent, just without the independent Codex reviews between phases.

## Session Files

All artifacts are tracked in `docs/cloco-sessions/YYYY-MM-DD-<slug>/`:

| File | Written by | Content |
|------|-----------|---------|
| `01-spec.md` | SuperPowers | Design specification |
| `02-codex-review-spec.md` | Codex | Findings on the spec |
| `03-spec-v2.md` | SuperPowers | Rewritten spec after feedback |
| `04-plan.md` | SuperPowers | Implementation plan |
| `05-codex-review-plan.md` | Codex | Findings on the plan |
| `06-plan-v2.md` | SuperPowers | Rewritten plan after feedback |
| `07-codex-review-impl.md` | Codex | Code review findings |
| `session.log` | CLOco | Decisions, timestamps, job IDs |

Sessions are designed to be committed to git for traceability.

## License

MIT
