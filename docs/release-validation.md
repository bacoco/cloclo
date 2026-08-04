# Unified companions release validation

Validation date: 2026-08-04
Candidate branch: `agent/unified-companions`

## Distribution validation

| Check | Result |
|---|---|
| `claude plugin validate .` | PASS |
| `claude plugin validate plugins/cloclo` | PASS |
| `claude plugin validate plugins/glm` | PASS |
| Codex validator for `plugins/claude` | PASS |
| Codex validator for `plugins/glm` | PASS |
| Codex skill validator for `$claude` | PASS |
| Codex skill validator for `$glm` | PASS |
| isolated Claude marketplace install | PASS; `cloclo` installed `glm` as its dependency |
| local Codex marketplace install | PASS; `claude@cloclo` and `glm@cloclo` installed |
| GitHub Actions `Validate companions` | PASS on draft PR #7 |

The repository CI runs Python compilation plus all distribution, adapter,
Claude Companion, and GLM Companion regression suites. The local campaign
contains 45 tests.

## Acceptance evidence

| ID | Workflow | Evidence | Result |
|---|---|---|---|
| A1 | Codex → Claude task | live runtime returned `CLAUDE_COMPANION_OK` | PASS |
| A2 | Codex → GLM task | live runtime returned `GLM_COMPANION_OK`; actual fallback reported | PASS |
| A3 | Claude → Codex | official `/codex:rescue` route returned `CLAUDE_TO_CODEX_OK` | PASS |
| A4 | Claude → GLM | `/glm:glm` route returned `CLAUDE_TO_GLM_OK` | PASS |
| A5 | context transfer | two-message synthetic visible transcript reached both companions; both returned resumable session IDs and message count `2` | PASS |
| A6 | background lifecycle | GLM task moved `queued → completed`; status, wait, result, and stable job ID verified | PASS |
| A7 | read-only review | live CLoClo adapter produced a verdict file and runtime log without source edits | PASS |
| A8 | write boundary | both transport command tests require explicit write mode and assert `acceptEdits`; default review/task tests remain read-only | PASS |
| A9 | pipeline GLM adapter | live review returned `Verdict global: CONCERNS`, model `glm-4.7`, and `fallbackFrom: glm-5.2` | PASS |
| A10 | provider failure | regression tests cover missing context, provider failure, retry fallback, malformed verdict, and fail-open stop gates without fabricated success | PASS |

The provider probe authenticated successfully and reported `glm-5.2` as the
preferred model. During live inference Z.AI rate-limited that model; the runtime
made the documented fallback attempt with `glm-4.7`, returned correct results,
and surfaced the fallback instead of hiding it.

## Context and credential safety

The current Codex transcript export found 144 visible messages. The exporter
excluded hidden records and replaced the provider-key form present in visible
history with `[REDACTED_SECRET]`; a post-export scan found no matching key.
Synthetic transfer tests separately verified the exact visible-message count so
the safety check did not require retransmitting the long working conversation.

## Independent GLM review disposition

The live GLM specification review returned `CONCERNS`. Findings were handled as
follows:

- Claims that Claude/GLM test directories were absent were disproved by the
  passing suites and repository paths.
- The request for durable acceptance evidence produced this document.
- The cross-host contract now states that stop gates fail open on
  infrastructure and malformed-output failures.
- The command reference now spells out namespace priority and the exact
  provider-retry fallback behavior.
- The Codex marketplace intentionally contains only `claude` and `glm`; CLoClo
  remains a Claude-first pipeline and this boundary is explicit in the plan.

## Independent staged-diff review disposition

Claude independently reviewed all 57 staged files in read-only mode. The first
pass found no P0, four P1, and six P2 findings. They produced regression changes
for CI portability, inner timeout forwarding, valid setup flags, dependency
discovery without `PATH`, state-root configuration, rate-limit-only fallback,
strict context bounds, queued-worker tracking, tracked-file secret scanning,
and state-artifact pruning.

A targeted second pass inspected those ten corrections and their tests and
returned **PASS with no remaining P0/P1/P2**. Two sub-P2 observations were also
closed afterward: a single oversized message is now truncated to the strict
context budget, and job creation now writes detail/state under one lock so a
concurrent prune cannot remove a newly created job file.

## PDG pass

- **Trigger decision:** yes; this release changes public routes, install paths,
  provider routing, context export, and durable documentation.
- **Known knowns:** both marketplace schemas validate, all four live delegation
  directions work, the provider probe authenticates, context is redacted, and
  the local regression campaign passes.
- **Known unknowns:** installation from the repository's default branch cannot
  be observed until the PR merges; provider quota/rate-limit state remains
  external and variable.
- **Unknown knowns surfaced:** Claude dependencies are installed automatically;
  marketplace binaries are not assumed to be globally on `PATH`; GLM resume
  must preserve the provider-scoped companion environment.
- **Unknown unknowns guarded:** future provider errors fail truthfully, stop
  gates fail open, fallback is reported, recursive delegation is blocked, and
  setup probes expose transport/model drift.
- **Bad implementation path rejected:** fork the official OpenAI plugin, keep a
  second GLM transport inside CLoClo, copy hidden prompts, or silently fall back
  without reporting the actual model.
- **Guardrail added:** one GLM runtime, explicit write permission, secret
  redaction, bounded context, dependency discovery, stable job state, CI, and
  manifest/secret contract tests.
- **Existing behavior preserved:** CLoClo remains Claude-first; pipeline files,
  verdict guards, consensus rules, retry caps, session artifacts, hooks,
  bootstrap, wiki, toggle, and rollback remain on their existing routes.
- **Forbidden shortcuts:** MUST NOT commit credentials/state, call Z.AI directly
  from CLoClo, vendor `codex-plugin-cc`, infer write permission, or advertise a
  raw `claude --resume` command for a GLM session.
- **Regression proof required:** official validators, all unit suites, isolated
  install, all four public routes, context transfer, background lifecycle, live
  pipeline review, independent diff review, and `git diff --check`.

Documentation review passes:

1. **Coverage:** README, plan, reference, release receipt, four public routes,
   two marketplaces, configuration variables, state roots, pipeline adapter,
   security boundaries, and rollback were cross-checked against the changed
   manifests, skills, scripts, hooks, prompts, schemas, and tests.
2. **Grounding:** install commands were exercised; command tables map to parser
   subcommands; key/fallback claims map to `glm_runtime.py`; context claims map
   to both exporters; pipeline claims map to the adapter and pipeline sources.
3. **Regression:** both local marketplaces installed, namespaced Claude routes
   ran live, Codex runtimes ran live, transfer/resume/background/review paths
   ran live, and stale direct-transport wording was scanned.

This PDG section is a self-check, distinct from the two independent staged-diff
review passes recorded above.

## Release boundary

This validation does not change provider accounts, quotas, subscriptions, or
secret files. The feature branch is published in draft PR #7 and GitHub Actions
passes; the validation does not merge the pull request.
