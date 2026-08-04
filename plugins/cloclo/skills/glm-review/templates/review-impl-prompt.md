# GLM implementation review

Review the implementation against:

- specification: `{{SPEC_PATH}}`
- plan: `{{PLAN_PATH}}`
- base ref: `{{BASE_REF}}`
- commits: `{{COMMIT_LIST}}`

Inspect `git diff {{BASE_REF}}..HEAD`, then read every modified file and relevant callsite completely.
Check correctness, regressions, edge cases, tests, security boundaries, and compliance with the specification and plan.
Keep the review read-only. Return the complete review as the final Markdown response; do not write files.

Required format:

- `Verdict global: PASS | CONCERNS | FAIL`
- Numbered findings with severity `P0`, `P1`, or `P2`
- Tag each finding `[TOOL]`, `[CODE]`, or `[LLM-JUDGMENT]`
- Include `file:line` for every `[CODE]` finding
- End with `Ce que la PR fait bien` and residual risks
