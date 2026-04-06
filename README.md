# CLOco — Claude + Codex Collaboration

A Claude Code plugin that orchestrates Claude and Codex as two developers collaborating via files.

## What It Does

CLOco automates the full development cycle:

1. **Design** -- Interactive brainstorming with visual mockups in the browser
2. **Spec** -- Claude writes a design spec, self-reviews it
3. **Review** -- Codex independently reviews the spec against your actual codebase
4. **Plan** -- Claude writes a task-by-task implementation plan
5. **Review** -- Codex reviews the plan against real code
6. **Execute** -- Claude implements via isolated subagents with two-stage review
7. **Review** -- Codex reviews the actual code changes
8. **Verify** -- Configurable verification (tests, browser, deploy)

At every review stage, you get intelligent decision points (not just yes/no) -- integrate all findings, cherry-pick some, ask for deeper investigation, or take over yourself.

## How It Works

Claude and Codex communicate via markdown files in a session directory:

```
docs/cloco-sessions/YYYY-MM-DD-<slug>/
  00-brainstorm.html        # Interactive design exploration
  01-spec.md                # Design specification
  02-spec-review.md         # Codex review of the spec
  03-spec-decision.md       # Your decision on spec review findings
  04-plan.md                # Task-by-task implementation plan
  05-plan-review.md         # Codex review of the plan
  06-plan-decision.md       # Your decision on plan review findings
  07-code-review.md         # Codex review of the implementation
  08-code-decision.md       # Your decision on code review findings
  09-verification.md        # Test and verification results
  pipeline.config.md        # Session-specific verification config
```

Codex has full freedom to explore your codebase during reviews -- reading 30-80+ files is normal and expected. Reviews take 2-10 minutes. This is a feature, not a bug.

## Prerequisites

| Requirement | Install |
|---|---|
| Claude Code | You're running it |
| Codex CLI | `npm install -g @openai/codex` then `codex login` |
| Codex Claude Code plugin | Install from the Claude Code plugin marketplace (openai-codex) |

CLOco works without Codex -- reviews are skipped with a warning, and you get Claude-only mode.

## Installation

### From GitHub

```bash
git clone https://github.com/anthropics/cloco.git ~/.claude/plugins/marketplaces/cloco
```

Then add to `~/.claude/settings.json`:

```json
{
  "enabledPlugins": {
    "cloco@cloco": true
  }
}
```

## Usage

Start a new session:

```
/pipeline
```

Or just describe what you want to build -- CLOco triggers automatically on creative/implementation work.

## Session Files

All artifacts are saved to `docs/cloco-sessions/YYYY-MM-DD-<slug>/` in your project:

| File | Content |
|------|---------|
| `00-brainstorm.html` | Interactive design exploration with visual mockups |
| `01-spec.md` | Design specification (problem, scope, decisions, files) |
| `02-spec-review.md` | Codex review of the spec against your codebase |
| `03-spec-decision.md` | Decision point: integrate, cherry-pick, investigate, or override |
| `04-plan.md` | Task-by-task implementation plan with verification steps |
| `05-plan-review.md` | Codex review of the plan against real code |
| `06-plan-decision.md` | Decision point on plan review findings |
| `07-code-review.md` | Codex review of the actual implementation |
| `08-code-decision.md` | Decision point on code review findings |
| `09-verification.md` | Test results and verification output |
| `pipeline.config.md` | Verification commands and optional browser/deploy config |

Sessions are designed to be committed to git for traceability.

## Configuration

Create `pipeline.config.md` in your session directory to configure verification:

```markdown
# Pipeline Config

## Verification
base_ref: main
verification_commands:
  - npm test
  - npm run build

## Browser Testing (optional)
browser_base_url: http://localhost:3000
screenshot_output_dir: public/screenshots/
browser_tool: playwright

## Deploy (optional)
deploy_commands:
  - docker compose up -d --build
```

## License

MIT

Brainstorm server forked from [SuperPowers](https://github.com/obra/superpowers) (MIT).
