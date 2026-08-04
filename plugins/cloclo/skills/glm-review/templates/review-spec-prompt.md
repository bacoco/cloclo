# GLM specification review

Review the implementation specification at `{{SPEC_PATH}}`.

- Read the specification completely.
- Inspect the repository to verify every factual claim, path, function, and dependency.
- Identify missing requirements, contradictions, unsafe assumptions, and unhandled edge cases.
- Keep the review read-only. Return the complete review as the final Markdown response; do not write files.

Required format:

- `Verdict global: PASS | CONCERNS | FAIL`
- Numbered findings with severity `P0`, `P1`, or `P2`
- Tag each finding `[TOOL]`, `[CODE]`, or `[LLM-JUDGMENT]`
- Include `file:line` for every `[CODE]` finding
- End with residual risks or state that none were found
