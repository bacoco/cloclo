# Prerequisites — Auto-Install

At pipeline start, check and automatically fix missing dependencies.

## Step 1: SuperPowers

Try to invoke a SuperPowers skill. If NOT available:

1. Read `~/.claude/settings.json`
2. Add `"superpowers@superpowers-marketplace": true` to `enabledPlugins`
3. Add `"superpowers-marketplace": {"source": {"source": "github", "repo": "obra/superpowers-marketplace"}}` to `extraKnownMarketplaces`
4. Write back `settings.json`
5. Tell user: `"SuperPowers not installed. Added to settings. Please restart Claude Code and run /pipeline again."`
6. **STOP.** Restart required.

## Step 2: Codex CLI

```bash
codex --version
```

If NOT found:
- Run: `npm install -g @openai/codex`
- If fails: `"Install manually: npm install -g @openai/codex"`
- Confirm with `codex --version`

## Step 3: Codex Claude Code Plugin (optional since 0.8.0)

Since 0.8.0, `codex-review` invokes `codex exec -s read-only -o` directly — the
native CLI, no wrapper. The `codex-companion.mjs` script from the Codex Claude
Code plugin is NOT required.

If the user still wants the plugin installed (for `codex:rescue` or other plugin
skills), the check is informational only, not blocking:

```bash
find ~/.claude/plugins -name codex-companion.mjs -path '*/codex/scripts/*' 2>/dev/null | head -1
```

If not installed and the user asks to install:
1. Read `~/.claude/settings.json`
2. Add `"codex@openai-codex": true` to `enabledPlugins`
3. Add `"openai-codex": {"source": {"source": "github", "repo": "openai/codex-plugin-cc"}}` to `extraKnownMarketplaces`
4. Write back `settings.json`
5. Tell user to restart for the plugin to load.

**Do not block the pipeline on this step** — the CLI check in Step 2 is sufficient.

Codex CLI manages its own auth — do NOT check `codex whoami` (requires TTY)
or `OPENAI_API_KEY` (unused by Codex CLI).

## Step 4: CodeRabbit CLI

```bash
command -v coderabbit
```

If NOT found:
- Run: `curl -fsSL https://cli.coderabbit.ai/install.sh | sh`
- If fails: `"Install manually: curl -fsSL https://cli.coderabbit.ai/install.sh | sh"`
- User must run `coderabbit auth login` once (interactive)
- **Do not block pipeline** — Phase 6.5 skips with warning if unavailable

## Step 5: agent-browser (UI projects only)

```bash
command -v agent-browser
```

If NOT found: warn only. Phase 7.5 skips with warning; do not block the pipeline.

## Degraded Mode

If Codex CLI, companion, or runtime fail (including usage limits):
- WARNING: `"Codex unavailable. Using Claude agent review as fallback."`
- Phases 2, 4, 6 still run, but use a Claude subagent (`subagent_type: "superpowers:code-reviewer"`, `model: "opus"`)
- Same session file names (e.g. `02-review-spec.md`) — just engine differs
- Decision Points A-E still apply
- Pipeline NEVER skips review phases entirely. At minimum, a Claude agent reviews.

If CodeRabbit CLI unavailable:
- Phase 6.5 is skipped with warning
- Pipeline continues to Phase 7 (verification)
