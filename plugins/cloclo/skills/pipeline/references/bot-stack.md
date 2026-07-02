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

## Consensus, Disagreement, Auto-Integration

Defined once in `review-chain.md`:

- **Consensus** — any 2+ independent reviewers flag the same file:line
  → `[CONSENSUS]`, severity escalated to the highest.
- **Disagreement** — same file:line, different severities →
  `[DISAGREEMENT]`, never averaged.
- **Auto-integration** — the 3 gates (concrete patch, non-critical
  domain, no conflicting patches) with an iteration cap of 3 for the
  PR loop.

Do not restate these rules here — `review-chain.md` is canonical.
