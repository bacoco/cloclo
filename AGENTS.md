# AGENTS.md

This file provides guidance to Codex and other coding agents working in this repository.

## Golden Rule

Take the most direct, safe, verifiable path:
- Define "done" in one sentence before starting.
- Work in small, reviewable increments — one skill, hook, or command per change.
- Use the project's existing harness: this repo has no build or test framework; verification means running hook scripts directly and reading SKILL.md flows end to end. Do not add a framework.
- Prefer editing existing SKILL.md/hook files over inventing new mechanisms.

## Repository Guidance

`CLAUDE.md` at the repo root is the detailed authority on structure, skill format, versioning, and constraints. Read it first.

## Branch Rule

The main branch is `main`. The checkout may currently be on a working branch (e.g. `fix/skills-review-2026-07-02`) — stay on the current branch; never switch or create branches unless explicitly asked.

## Critical Constraints

- This is a Claude Code plugin: skills live in `plugins/cloclo/skills/<name>/SKILL.md`, hooks in `plugins/cloclo/hooks/`, commands in `plugins/cloclo/commands/`. Skill frontmatter descriptions drive auto-triggering — change them deliberately.
- Reviewer independence is the core invariant: Claude generates; Codex, GLM, and CodeRabbit verify. Never substitute a self-review for an external reviewer.
- Keep hooks fast (declared timeouts: 10s/5s/3s), silent on the happy path, and respectful of the `.cloclo-disabled` toggle marker.
- Missing `ZAI_API_KEY`/`GLM_API_KEY` must remain a silent skip, never a pipeline-blocking error.
- Version is defined in `plugins/cloclo/.claude-plugin/plugin.json`; mirror changes in `.claude-plugin/marketplace.json`.
