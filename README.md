# CLoClo — Claude ↔ Codex ↔ GLM

CLoClo is a dual marketplace and development orchestrator. It gives Codex access
to Claude and GLM, gives Claude Code access to Codex and GLM, and keeps the
existing multi-review development pipeline, project bootstrap, hooks, and wiki.

## Companion matrix

| Host | Delegate to | Distribution | Primary invocation |
|---|---|---|---|
| Codex | Claude Code | `claude@cloclo` | `$claude` |
| Codex | GLM through Z.AI | `glm@cloclo` | `$glm` |
| Claude Code | Codex | `codex@openai-codex` | `/codex:rescue` and `/codex:*` |
| Claude Code | GLM through Z.AI | `glm@cloclo` | `/glm:glm` |

The Claude Code plugin system namespaces marketplace commands. A personal
`~/.claude/commands/glm.md` alias may expose `/glm`, but the portable marketplace
name is `/glm:glm`. CLoClo also keeps `/cloclo:glm` as a compatibility route.

## Install the complete suite

### Claude Code

Keep the Codex companion on its official OpenAI update channel and install
CLoClo plus GLM from this marketplace:

```bash
claude plugin marketplace add openai/codex-plugin-cc
claude plugin marketplace add bacoco/cloclo
claude plugin install codex@openai-codex
claude plugin install cloclo@cloclo
```

`cloclo@cloclo` declares `glm@cloclo` as a dependency, so Claude installs GLM
with it. Run `/reload-plugins` or start a new Claude Code session.

### Codex

```bash
codex plugin marketplace add bacoco/cloclo
codex plugin add claude@cloclo
codex plugin add glm@cloclo
```

Start a new Codex session after installation so `$claude` and `$glm` are loaded.

## One feature contract

The Claude and GLM companions intentionally expose the same lifecycle:

- fresh delegated tasks with visible host-conversation context;
- explicit read-only or write-capable execution;
- foreground and background jobs;
- resumable model sessions;
- conversation transfer;
- normal and adversarial reviews;
- setup, status, result, wait, and cancellation;
- recursion protection and optional fail-open stop-review gates.

Claude → Codex uses OpenAI's official companion, which provides the corresponding
task, transfer, review, job-control, and setup commands. CLoClo does not fork or
vendor the OpenAI plugin.

## Quick use

From Codex:

```text
$claude investigate this failure
$claude implement the fix and verify it
$claude transfer this conversation
$glm review the current branch
$glm continue
```

From Claude Code:

```text
/codex:rescue investigate this failure
/codex:review
/codex:transfer
/glm:glm review the current branch
/glm:glm continue
```

## GLM setup

GLM uses the Z.AI Anthropic-compatible endpoint through the installed Claude Code
CLI. Store the key in a user-owned file with mode `0600`:

```bash
printf 'ZAI_API_KEY="replace-me"\n' > ~/.glm.env
chmod 600 ~/.glm.env
```

Key lookup order is:

1. `~/.glm.env`
2. `ZAI_API_KEY` or `GLM_API_KEY` from the process environment
3. the same keys in the workspace `.env`

The runtime prefers `glm-5.3`. If Z.AI rate-limits that model, it retries once
with the independent `glm-4.7` model and reports the fallback in the result. It never prints the key or
writes provider credentials into Claude settings.

Run setup checks with `$glm setup` in Codex or `/glm:glm setup` in Claude Code.

## CLoClo development pipeline

The `cloclo:pipeline` skill remains Claude-first:

```text
Design → Codex + GLM review → Plan → Codex + GLM review
       → Execute → Codex + GLM + CodeRabbit review
       → Verify → Wiki → PR bots → Merge → post-merge GLM review
```

GLM pipeline reviews use the canonical `glm@cloclo` runtime. CLoClo no longer
contains a second direct Z.AI transport. The adapter preserves the existing
review-file, severity, consensus, retry, and escalation contracts.

The pipeline also includes:

- project bootstrap with `CLAUDE.md`, hooks, behavioral memories, and skills;
- checkpointed sessions and smart resume;
- confidence-first questions instead of low-confidence guesses;
- optional CodeRabbit, Gemini, Codex Cloud, and visual verification;
- a persistent, PII-scanned project wiki;
- guarded rollback and pause/resume controls.

## Repository layout

```text
.claude-plugin/marketplace.json       Claude Code marketplace
.agents/plugins/marketplace.json      Codex marketplace
plugins/cloclo/                       Claude-first orchestration plugin
plugins/claude/                       Claude Companion for Codex
plugins/glm/                          GLM Companion for Claude and Codex
docs/unified-companions-plan.md       architecture and acceptance contract
docs/companion-reference.md           commands, configuration, and operations
```

Each companion plugin is self-contained because marketplace installers copy
plugin roots into versioned caches. CLoClo's adapter resolves GLM from the
declared marketplace dependency, from a repository sibling during development,
or from an explicit `GLM_COMPANION_BIN` override.

## Security boundaries

- Visible user/assistant messages may be transferred; hidden instructions,
  private reasoning, raw tool traces, and attachments are excluded. Known
  provider-token forms are deterministically replaced with
  `[REDACTED_SECRET]` before delegation.
- Read-only work denies edit tools and uses an OS sandbox where available.
- Write permission is enabled only for explicit mutation requests.
- Delegated workers cannot delegate back to the originating model.
- Provider variables exist only in the child GLM process.
- Stop-review gates fail open on infrastructure failure and are disabled by
  default.
- No API key, `.env`, job state, or runtime log belongs in git.

## Documentation

- [Unified companion plan](docs/unified-companions-plan.md)
- [Companion command and operations reference](docs/companion-reference.md)
- [Release validation evidence](docs/release-validation.md)
- [Pipeline phases](plugins/cloclo/skills/pipeline/references/phases.md)
- [Review chain](plugins/cloclo/skills/pipeline/references/review-chain.md)
- [Behavioral patterns](docs/behavioral-patterns.md)

## Validate locally

```bash
claude plugin validate .
python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py plugins/claude
python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py plugins/glm
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s plugins/cloclo/tests -v
python3 -m unittest discover -s plugins/claude/tests -v
python3 -m unittest discover -s plugins/glm/tests -v
```

## License

[MIT](LICENSE) © 2026 Loic Baconnier
