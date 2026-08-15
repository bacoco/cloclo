# Companion command and operations reference

## Installation sources

| Capability | Plugin | Marketplace |
|---|---|---|
| Codex → Claude | `claude` | `bacoco/cloclo` |
| Codex → GLM | `glm` | `bacoco/cloclo` |
| Claude → Codex | `codex` | `openai/codex-plugin-cc` |
| Claude → GLM | `glm` | `bacoco/cloclo` |
| Claude pipeline | `cloclo` | `bacoco/cloclo` |

## Codex → Claude

Invoke `$claude` followed by an intent:

| Intent | Behavior |
|---|---|
| task, ask, implement, fix | fresh Claude task |
| continue, resume | resume the last Claude task session |
| transfer | seed a resumable Claude session with visible Codex context |
| review | structured read-only review |
| adversarial-review | skeptical read-only review |
| status | list or inspect jobs; optionally wait |
| result | retrieve completed output |
| cancel | terminate a tracked job |
| setup | CLI, authentication, and contract diagnostics |

Fresh tasks import visible Codex messages unless `--no-context` is explicitly
requested. Implementation requests use `--write`; diagnosis, planning, research,
and reviews remain read-only.

## Codex → GLM

Invoke `$glm` with the same intent vocabulary. The runtime adds `--host codex`
internally and imports visible Codex context. It uses Z.AI through a child Claude
Code process whose provider environment is isolated from the parent.

## Claude → Codex

Use OpenAI's official plugin commands:

| Command | Behavior |
|---|---|
| `/codex:rescue` | delegate a task, optionally write-capable |
| `/codex:transfer` | transfer visible Claude conversation context |
| `/codex:review` | review local changes |
| `/codex:adversarial-review` | challenge the implementation or approach |
| `/codex:status` | inspect tracked Codex jobs |
| `/codex:result` | retrieve a job result |
| `/codex:cancel` | cancel a job |
| `/codex:setup` | verify Codex installation and authentication |

CLoClo intentionally does not copy the official runtime. Update it through the
`openai-codex` marketplace.

## Claude → GLM

Invoke `/glm:glm` with the same task, continue, transfer, review, status, result,
cancel, and setup intents. `/cloclo:glm` is a compatibility command that routes
to the same `glm-companion` executable.

Claude Code namespaces plugin skills. Resolution order is the portable
marketplace skill `/glm:glm`, then CLoClo's `/cloclo:glm` compatibility route,
then an optional user/project `/glm` alias outside the marketplace.

## Job lifecycle

Foreground execution waits and renders the result immediately. Background
execution returns a job ID. Jobs transition through:

```text
queued → running → completed | failed | cancelled
```

Use status with `--wait` for bounded polling. Results are immutable after a
terminal state. Cancellation targets the tracked process group and records a
terminal result; it does not delete logs or session metadata.

## Context and transfer

- Fresh delegated tasks normally include visible conversation context.
- Ordinary resume sends only the delta instruction to the existing model
  session rather than retransmitting the transcript.
- Explicit transfer creates a model session whose only initial task is to import
  the visible history and wait.
- Hidden instructions, private reasoning, tool traces, and attachments are
  excluded from text export. Z.AI-style provider keys and common OpenAI/GitHub
  token forms are replaced with `[REDACTED_SECRET]` before delegation.
- Claude and GLM retain the newest 80 visible messages within a
  120,000-character safety budget. The returned `contextMessageCount` makes
  truncation observable.
- Missing automatic context degrades to an isolated task; missing explicitly
  requested context is reported as an error.

## Permission modes

| Mode | Source edits | Intended use |
|---|---|---|
| read-only | denied | review, diagnosis, research, planning |
| write-capable | explicitly enabled | implementation, fixes, requested mutations |

On macOS, the companions add an OS sandbox around read-only work when available.
Tool denial remains in place on other systems. Delegation-depth environment
guards block Claude ↔ Codex and GLM recursion before spawning a child.

## GLM configuration

Supported variables:

| Variable | Purpose |
|---|---|
| `ZAI_API_KEY` | preferred Z.AI credential name |
| `GLM_API_KEY` | compatible credential alias |
| `GLM_MODEL` | preferred model override |
| `GLM_FALLBACK_MODEL` | rate-limit fallback override |
| `GLM_COMPANION_HOME` | optional state-root override |

The key is resolved from `~/.glm.env`, process environment, then workspace
`.env`. Provider variables are removed/rebuilt only for the child process.
`glm-5.3` is preferred. After the transport reports three provider retries for
a rate-limit failure, the companion makes one fresh attempt with `glm-5.2` (or
`GLM_FALLBACK_MODEL`) and reports `fallbackFrom`, the primary error, and the
actual model. Other failure classes do not silently switch models.

## Persistent state

| Companion | Default state root |
|---|---|
| Claude | `~/.codex/state/claude-companion` |
| GLM | `~/.glm-companion/state` |

State is partitioned by workspace and protected with file locks and atomic
writes. Each companion retains all active jobs plus the newest completed jobs
up to the normal 50-job window, and removes evicted job/detail logs.

## Stop-review gates

Stop gates are disabled by default and enabled separately per host. When
enabled, the gate runs a read-only review of the immediately preceding host
response. Only an explicit `BLOCK:` result blocks. Provider errors, timeouts,
malformed output, or missing configuration fail open and emit diagnostics.

## Troubleshooting order

1. Confirm the marketplace and plugin are installed and enabled.
2. Start a new session or run `/reload-plugins` in Claude Code.
3. Run the relevant setup command.
4. For GLM, confirm `~/.glm.env` mode and the provider probe.
5. Inspect the job result and runtime log rather than retrying blindly.
6. Confirm recursion protection did not reject a nested delegation.
7. For CLoClo pipeline reviews, inspect `<review>.runtime.log`; if dependency
   discovery fails, set `GLM_COMPANION_BIN` to the trusted executable path.
