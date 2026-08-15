---
name: glm-review
description: Use when the CLoClo pipeline needs an independent GLM review of a specification, plan, or implementation through the canonical glm@cloclo companion.
user-invocable: false
---

# GLM review adapter

Use the deterministic adapter at `${CLAUDE_PLUGIN_ROOT}/scripts/run_glm_review.py`.
Do not call Z.AI or `claude -p` directly from CLoClo.

## Contract

Receive the same parameters as `codex-review`:

- `review_type`: `spec`, `plan`, or `impl`
- `session_dir`, `output_file`, and repository root
- `spec_path`, `plan_path`, `base_ref`, and `commit_list` when applicable
- `maturity`: `spike`, `dev`, or `ship`
- `iterate`: optional convergence-oriented pass

Run one foreground adapter process while the pipeline may run this skill and
`codex-review` concurrently:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/run_glm_review.py" \
  --review-type "$review_type" \
  --cwd "$repo_root" \
  --output-file "$output_file" \
  --spec-path "$spec_path" \
  --plan-path "$plan_path" \
  --base-ref "$base_ref" \
  --commit-list "$commit_list" \
  --maturity "$maturity"
```

Add `--iterate` only when requested. Omit arguments that do not apply.

## Result handling

- Exit `0` plus a non-empty review containing `Verdict global` means success.
- Exit `2` means GLM was unavailable or the result contract failed. Log the
  warning and continue with Codex; do not substitute a Claude review.
- Read the review from `output_file`. Runtime diagnostics live at
  `${output_file}.runtime.log`.
- Record the actual engine. The runtime prefers `glm-5.3` and may explicitly
  report a `glm-4.7` fallback when Z.AI rate-limits the preferred model.

The adapter is the only component allowed to translate GLM output into the
pipeline review-file contract. Preserve the consensus, severity, escalation,
and retry rules from `../pipeline/references/review-chain.md`.
