# Unified companions — implementation plan and acceptance contract

## Mission

Keep `bacoco/cloclo` as the canonical distribution repository and make delegation
bidirectional:

- Codex delegates to Claude and GLM.
- Claude Code delegates to Codex and GLM.
- The same lifecycle vocabulary applies across providers.
- CLoClo's existing pipeline continues to use independent Codex and GLM reviews.

## Non-goals

- Do not fork OpenAI's `codex-plugin-cc`.
- Do not route normal Anthropic traffic through Z.AI.
- Do not make the Claude-first CLoClo pipeline appear Codex-native before it is
  actually ported.
- Do not persist API keys, copy hidden prompts, or permit recursive delegation.
- Do not replace pipeline session files, consensus rules, or review severities.

## Baseline and gaps

Before this work, CLoClo contained one Claude marketplace entry and embedded a
second GLM transport inside `cloclo:glm-review`. The local machine separately had
a Claude Companion for Codex and a cross-host GLM Companion. The gaps were:

1. no Codex marketplace in the repository;
2. no distributable `$claude` or `$glm` from CLoClo;
3. no full GLM task/job/context lifecycle in the repository;
4. duplicated GLM provider logic in the pipeline;
5. stale documentation claiming `glm-5.2` had no fallback;
6. no single install and command reference for all four delegation directions.

## Target architecture

### Distribution layer

- `.claude-plugin/marketplace.json` distributes `cloclo` and `glm`.
- `.agents/plugins/marketplace.json` distributes `claude` and `glm` to Codex.
- `plugins/cloclo/.claude-plugin/plugin.json` depends on `glm` from the same
  Claude marketplace.
- Claude → Codex remains `codex@openai-codex` from its official marketplace.

### Runtime layer

- `plugins/claude` owns Codex → Claude transport, context export, jobs, review,
  transfer, cancellation, and stop gate.
- `plugins/glm` owns all Z.AI authentication and model routing for both hosts.
- `plugins/cloclo/scripts/run_glm_review.py` adapts canonical GLM JSON results to
  CLoClo's pipeline review-file contract.
- `glm-companion` and `claude-companion` are stable executable entry points
  exposed from each plugin's `bin/` directory.

### State and secrets

- Claude Companion state remains under `~/.codex/state/claude-companion`.
- GLM Companion state remains under `~/.glm-companion/state` unless overridden.
- GLM secrets resolve from `~/.glm.env`, then environment, then workspace `.env`.
- No runtime state or credential enters the repository.

## Cross-host behavior contract

Every companion MUST provide:

1. a fresh task command;
2. an explicit write flag, with read-only default for diagnosis/review/research;
3. foreground and background execution;
4. stable job IDs with status, result, wait, and cancel;
5. resume-last and explicit model session resume;
6. visible-conversation context import and explicit transfer;
7. normal and adversarial reviews;
8. setup diagnostics and an optional stop-review gate that fails open on
   provider, transport, timeout, or malformed-output failures;
9. recursion prevention;
10. truthful reporting of edits, denials, timeouts, model fallback, and failures.

Context export MUST include only visible user/host-agent messages. It MUST NOT
include hidden system/developer instructions, private reasoning, raw tool traces,
or attachments. Known provider and source-control token forms MUST be replaced
with `[REDACTED_SECRET]` before delegation; bounded exports MUST report the
number of retained messages.

## Implementation phases

### Phase 1 — package the existing companions

- Import the tested local Claude and GLM plugins as self-contained plugin roots.
- Remove caches and machine-specific data.
- Replace local publisher metadata with repository metadata.
- Add stable `bin/` entry points.

### Phase 2 — make CLoClo a dual marketplace

- Add the Codex marketplace manifest.
- Extend the Claude marketplace with GLM.
- Add the CLoClo → GLM dependency.
- Keep OpenAI Codex on the official marketplace and update channel.

### Phase 3 — remove GLM transport duplication

- Replace the standalone CLoClo GLM command with a canonical-runtime route.
- Replace direct `claude -p`/Z.AI review instructions with the deterministic
  pipeline adapter.
- Capture GLM's final result into the existing review file.
- Preserve `.runtime.log`, verdict guards, and skip semantics.

### Phase 4 — align configuration and documentation

- Document the four delegation directions and namespace behavior.
- Document key precedence, model preference, and explicit `5.2 → 4.7` fallback.
- Update pipeline phases, prerequisites, review-chain, and session-file docs.
- Rewrite the README around the unified suite rather than one Claude plugin.

### Phase 5 — validation and release

- Validate both marketplace schemas and all plugin manifests.
- Run all companion and adapter unit tests.
- Install the branch marketplace into Codex and Claude test environments.
- Exercise one real task through each public route.
- Run one independent read-only review of the complete diff.
- Push a feature branch and open a draft PR; merge only after review.

## Acceptance tests

| ID | Public workflow | Expected evidence |
|---|---|---|
| A1 | Codex `$claude` task | exact Claude response, no recursion |
| A2 | Codex `$glm` task | exact GLM response and reported model |
| A3 | Claude `/codex:rescue` task | exact Codex response via official plugin |
| A4 | Claude `/glm:glm` task | exact GLM response and reported fallback if used |
| A5 | context transfer | visible-message count and resumable session ID |
| A6 | background task | stable job ID, status, result, cancel behavior |
| A7 | read-only review | no source writes; structured verdict |
| A8 | write-capable task | only explicit requested changes are reported |
| A9 | CLoClo GLM review | pipeline review file plus runtime log |
| A10 | missing provider | logged skip/failure without fabricated output |

## Release and rollback

- Release CLoClo, Claude Companion, and GLM Companion with independent manifest
  versions even though they share one repository.
- Keep marketplace and plugin versions synchronized for Claude installs.
- Roll back by reverting the marketplace entries and adapter commit; existing
  cached plugin versions remain available until users update or uninstall.
- Never delete user state or secret files during install, update, or rollback.
