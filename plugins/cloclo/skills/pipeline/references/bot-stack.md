# Multi-Bot PR Review Stack (Phase 9)

Once Phase 9 opens the PR, installed bots run in parallel on the same
diff. The default stack is two bots; extras are opt-in.

## Default (zero extra config once installed)

| Bot | Install | Focus | Cost |
|-----|---------|-------|------|
| [CodeRabbit GitHub App](https://github.com/apps/coderabbitai) | App + seat assigned | Line-level, security, style, summary | Pro ($24/dev/mo) for private |
| [Gemini Code Assist](https://github.com/apps/gemini-code-assist) | GitHub App | Architecture, high-level review | Free for private |

## Opt-in (add only when the extra angle is worth the config overhead)

| Bot | Install | Focus | Cost |
|-----|---------|-------|------|
| [Codex Cloud](https://chatgpt.com/codex) | Connect repo + settings | Spec compliance, test coverage | ChatGPT subscription |
| [Claude Code GitHub Action](https://github.com/anthropics/claude-code-action) | GitHub Actions workflow | Claude review via CI | Anthropic API key |

Default stack = **CodeRabbit + Gemini**. Two angles, both zero-config
after install.

### Why Codex Cloud is opt-in (not default)

Phases 2, 4, and 6 already invoke `codex-review` against the spec, plan,
and implementation. That is three independent Codex passes against the
same code before Phase 9 even opens the PR. Polling
`chatgpt-codex-connector[bot]` on the PR:

- Consumes Codex quota for a review that largely duplicates Phase 6.
- Surfaces near-identical findings in different words, which creates
  noise and false "new finding" signals in the auto-integration loop.
- Adds 5-10 minutes per iteration waiting for Codex Cloud to finish.

If a user genuinely wants an independent Codex double-check on the PR
(for example, because the repo has external contributors whose code did
not go through Phases 2/4/6), they can enable the opt-in. The directive
`/pipeline avec codex cloud` (see `smart-resume.md`) adds Codex Cloud to
the Phase 9 wait-set for a single session. Permanent enablement happens
in `pipeline.config.md`:

```yaml
bots:
  codex_cloud: true
```

When Codex Cloud is opted in AND the GitHub App is installed on the
repo, Phase 9 polls `chatgpt-codex-connector[bot]` alongside CodeRabbit
and Gemini. Otherwise the bot login is simply absent from the regex
match and the polling loop ignores it. No error, no warning — Codex
Cloud is treated as optional by design.

## Consensus Amplification

When BOTH Codex (architecture) AND CodeRabbit (static analysis) flag the
same file:line:
- Mark `[CONSENSUS]` — high-confidence finding
- Escalate severity to the higher of the two
- Apply during Phase 6.5 auto-integration (consensus beats the 3-gate
  skip)

## Disagreement Handling

When reviewers disagree (Codex flags P2, CodeRabbit flags P0 or vice-
versa):
- Mark `[DISAGREEMENT]`
- If severity spread > 1 level AND the higher is `critical` → escalate
- Otherwise apply the higher-severity fix and log the disagreement

No averaging, no hiding the split.

## Auto-Integration (the 3 gates)

A bot finding is auto-applied only when ALL three gates pass:

1. **Concrete patch available.** Bot provided a diff block or AI-Agent
   prompt with file:line + replacement. Pure judgment-only findings
   ("consider refactoring X") skipped.
2. **Not auth / payments / data migration domain.** Escalate instead.
3. **No conflicting patches across bots.** Different fixes at same
   file:line → skip both, log `[CONFLICT]`.

Iteration cap: 3. After cap, exit and log remaining findings.
