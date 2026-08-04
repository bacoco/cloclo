# Prerequisites — Detect, Install, and Report

At pipeline start, check dependencies and install only those the user has
authorized. Prefer each product's plugin CLI; never edit Claude Code settings
JSON directly.

## Step 1: SuperPowers

Try to invoke a SuperPowers skill. If it is unavailable, report that the
pipeline cannot start and give the marketplace's current documented install
command. Do not invent or silently mutate `~/.claude/settings.json`. After an
authorized installation, ask the user to restart Claude Code and run
`/pipeline` again. **STOP** because a restart is required.

## Step 2: Codex CLI

```bash
codex --version
```

If NOT found and installation is authorized:
- Run: `npm install -g @openai/codex`
- If fails: `"Install manually: npm install -g @openai/codex"`
- Confirm with `codex --version`

## Step 3: Codex Claude Code Plugin (optional since 0.8.0)

Since 0.8.0, `codex-review` invokes `codex exec -s read-only -o` directly — the
native CLI, no wrapper. The `codex-companion.mjs` script from the Codex Claude
Code plugin is NOT required.

If the user wants the full `/codex` delegation surface in Claude Code, install
the official OpenAI plugin with its supported CLI flow:

```bash
claude plugin marketplace add openai/codex-plugin-cc
claude plugin install codex@openai-codex
```

**Do not block the pipeline on this step** — the CLI check in Step 2 is sufficient.

Codex CLI manages its own auth — do NOT check `codex whoami` (requires TTY)
or `OPENAI_API_KEY` (unused by Codex CLI).

## Step 4: GLM Companion

The CLoClo marketplace declares `glm` as a plugin dependency. Verify the
runtime and configuration without printing credentials:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/run_glm_companion.py" setup --host claude --json
```

Credential resolution order is `~/.glm.env`, process `ZAI_API_KEY` or
`GLM_API_KEY`, then the workspace `.env`. The runtime prefers `glm-5.2` and
uses the configured `glm-4.7` fallback only for provider rate limits. A missing
key or failure of both models does not block the pipeline; GLM review phases
are skipped with a logged warning and Codex remains active.

To install or repair the marketplace plugins with authorization:

```bash
claude plugin marketplace add bacoco/cloclo
claude plugin install cloclo@cloclo
```

## Step 5: CodeRabbit CLI

```bash
command -v coderabbit
```

If NOT found:
- Run: `curl -fsSL https://cli.coderabbit.ai/install.sh | sh`
- If fails: `"Install manually: curl -fsSL https://cli.coderabbit.ai/install.sh | sh"`
- User must run `coderabbit auth login` once (interactive)
- **Do not block pipeline** — Phase 6.5 skips with warning if unavailable

## Step 6: agent-browser (UI projects only)

```bash
command -v agent-browser
```

If NOT found: warn only. Phase 7.5 skips with warning; do not block the pipeline.

## Degraded Mode

If Codex CLI, companion, or runtime fail (including usage limits):
- WARNING: `"Codex unavailable. Using Claude agent review as fallback."`
- Phases 2, 4, 6 still run via a Claude subagent. Dispatch
  `subagent_type: "general-purpose"` (or `"superpowers:code-reviewer"`
  **only if** it is present in the running session's available agent
  types — this is not discoverable from bash, so check the session's
  own available agent types, never a shell probe). Use a
  high-capability model for the review.
- Same session file names (e.g. `02-codex-review-spec.md`) — just the engine differs
- Auto-integration under the 3 gates still applies (`review-chain.md`)
- Pipeline NEVER skips review phases entirely. At minimum, a Claude agent reviews.

If CodeRabbit CLI unavailable:
- Phase 6.5 is skipped with warning
- Pipeline continues to Phase 7 (verification)

If GLM Companion is unavailable:
- Phases 2, 4, 6, and 9.5 log a GLM skip reason
- Codex review and its Claude fallback remain unchanged
- No direct Z.ai or `claude -p` call is attempted from CLoClo
