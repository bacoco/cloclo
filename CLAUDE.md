# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

CLoClo — Code Loop Orchestrator, v0.9.0. A Claude Code plugin that runs an autonomous dev pipeline: Claude generates specs/plans/code, then independent reviewers verify each phase (Codex CLI + GLM-5.2 in parallel, CodeRabbit static analysis on implementations, Gemini Code Assist on the PR). Also ships a persistent LLM wiki, project bootstrap, rollback, and on/off toggle. GitHub: `bacoco/cloclo`. License MIT.

Design principle: CLoClo works invisibly — hooks and skill descriptions trigger behavior; users rarely call skills by name. Findings auto-integrate under guardrails; the pipeline escalates in the terminal (never on GitHub) only on genuine blockers. GLM is optional (`ZAI_API_KEY`/`GLM_API_KEY`; missing key = silent skip).

## Structure

```
.claude-plugin/marketplace.json      # Marketplace manifest (bacoco/cloclo)
plugins/cloclo/
├── .claude-plugin/plugin.json       # Plugin manifest — version source of truth (0.9.0)
├── commands/                        # Slash commands: coderabbit.md, glm.md
├── hooks/
│   ├── hooks.json                   # SessionStart + PostToolUse(Bash, Edit|Write) wiring
│   ├── session-start.sh             # Injects wiki state into context (or "paused" line)
│   ├── post-commit.sh               # After git commit: nudge wiki update
│   └── post-ui-edit.sh              # After UI file edit: nudge agent-browser verification
└── skills/                          # 8 skills, one dir each with SKILL.md
    ├── pipeline/                    # Full dev cycle: design → review → plan → review → execute → review → verify → PR
    ├── wiki/                        # Persistent LLM wiki: init, ingest, query, lint (references/, templates/)
    ├── bootstrap/                   # First-time project setup (CLAUDE.md, hooks, memory, skills, wiki)
    ├── rollback/                    # Undo pipeline work: soft (uncommit) or hard (revert)
    ├── toggle/                      # cloclo on/off/status via .cloclo-disabled marker file
    ├── codex-review/                # Codex CLI review; Claude subagent fallback
    ├── glm-review/                  # GLM-5.2 via Z.ai Anthropic-compatible endpoint; no fallback
    └── coderabbit-review/           # Local CodeRabbit CLI review of a git diff
docs/                                # behavioral-patterns.md, scout-reports/
```

## Skill format

Each skill is a directory under `plugins/cloclo/skills/` containing `SKILL.md` (YAML frontmatter with `name`/`description`, then the prompt) plus optional `templates/` and `references/`. Skill descriptions are load-bearing: they are what makes auto-triggering work — edit them deliberately.

## Development

- No build system, no package.json, no test framework. The plugin is Markdown + bash. Verify hooks by running them directly (`bash plugins/cloclo/hooks/session-start.sh`) with hook JSON on stdin where applicable, and by reading SKILL.md flows end to end.
- Hook budget is tight: hooks.json declares timeouts of 10s (SessionStart), 5s and 3s (PostToolUse). Keep hook scripts fast, silent on the happy path, and safe when jq/git are missing.
- Version bumps: update `plugins/cloclo/.claude-plugin/plugin.json` and mirror version/description in `.claude-plugin/marketplace.json` (both `metadata` and the plugin entry).

## Constraints

- **Branch**: main branch is `main`. Current working branch may differ (e.g. a `fix/...` review branch) — never switch branches without being asked.
- Reviewer independence is the core invariant: Claude generates, Codex/GLM/CodeRabbit verify. Do not replace an external reviewer with a Claude self-review (the codex-review fallback subagent is the only sanctioned exception).
- `toggle` must keep working via the `.cloclo-disabled` marker; every hook and auto-trigger must respect it.
- Missing GLM key must remain a silent skip, never an error that blocks the pipeline.
- Rollback must stay non-destructive by default (soft = uncommit, keep files; hard = revert only after confirmation).
