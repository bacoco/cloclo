# GLM implementation-plan review

Review the plan at `{{PLAN_PATH}}` against the specification at `{{SPEC_PATH}}`.

- Read both artifacts completely.
- Inspect the repository to confirm named files, functions, dependencies, and existing behavior.
- Check coverage, task order, verification, migration, rollback, and compatibility risks.
- Keep the review read-only. Return the complete review as the final Markdown response; do not write files.

Required format:

- `Verdict global: PASS | CONCERNS | FAIL`
- Numbered findings with severity `P0`, `P1`, or `P2`
- Tag each finding `[TOOL]`, `[CODE]`, or `[LLM-JUDGMENT]`
- Include `file:line` for every `[CODE]` finding
- End with residual risks or state that none were found
