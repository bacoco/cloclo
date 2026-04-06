---
name: design
description: "Phase 1 of the CLOco pipeline: interactive brainstorming, visual mockups, and spec writing. Explores user intent through one-question-at-a-time dialogue, generates HTML mockups for visual decisions, writes a self-reviewed spec document."
user-invocable: false
---

# Design — Brainstorming and Spec Writing

Turn a user request into a validated spec through focused dialogue. No code gets written until the spec exists and the user approves it.

<HARD-GATE>
Do NOT write implementation code, create plans, scaffold files, or take any action beyond exploration and spec writing. This skill produces ONE artifact: `{session_dir}/01-spec.md`. Nothing else.
</HARD-GATE>

## Context Reception

This skill receives from the pipeline orchestrator:
- `session_dir` — path to the CLOco session directory (e.g., `docs/cloco-sessions/<id>/`)
- The user's initial description of what they want to build or change

## Step 1: Explore the Need

Understand what exists before asking what to build.

1. Read relevant code with Grep/Read/Glob to map the current state
2. Ask questions **one at a time** — each waits for a response before the next
3. Prefer multiple-choice when possible ("A, B, or C?")
4. Focus on: purpose, constraints, success criteria, edge cases
5. Maximum 5 questions before proposing a direction
6. If the need is simple and unambiguous, skip directly to Step 3

**Scope check:** If the request spans multiple independent subsystems, flag it immediately. Help the user decompose into sub-projects. Each sub-project gets its own pipeline cycle. Brainstorm the first one.

## Step 2: Visual Companion (UI Work Only)

Skip this step entirely if the work has no visual component.

When upcoming decisions involve layouts, mockups, or visual comparisons, offer once:
> "Some decisions would be clearer with visual mockups in a browser. Want me to show HTML mockups as we go? (Opens a local URL)"

This offer is its own message — no other content. Wait for the response.

If accepted, start the server:
```bash
bash "${SKILL_DIR}/scripts/start-server.sh" --project-dir "$(pwd)"
```

The server returns JSON: `{ "url": "...", "screen_dir": "...", "state_dir": "..." }`

**Per-question rule:** Even after acceptance, decide for each question whether to use the browser or terminal. The test: would the user understand this better by **seeing** it than **reading** it?

- **Browser:** layout comparisons, wireframes, component mockups, side-by-side designs
- **Terminal:** requirements questions, conceptual choices, tradeoff lists, scope decisions

When using the browser:
- Write styled HTML to `screen_dir/` — the server auto-serves the newest file
- Present 2-3 options (never more than 3) with pros/cons and a recommendation
- Read user choices from `state_dir/events`

## Step 3: Write the Spec

Write to `{session_dir}/01-spec.md` using this structure:

```markdown
# [Feature Name]

**Date:** YYYY-MM-DD
**Session:** {session_dir}
**Problem:** [What is wrong or missing — concrete, not abstract]
**Objective:** [What success looks like when this is done]

---

## Key Concepts
[Technical terms, domain constraints, invariants the implementation must respect]

## Technical Decisions
[Architecture choices made during brainstorming, with rationale for each]

## Scope
**In scope:**
- [bullet list — specific deliverables]

**Out of scope:**
- [bullet list — explicit exclusions to prevent drift]

## Files Concerned
| File | Action | Reason |
|------|--------|--------|
| path/to/file.ts | modify | Add X to handle Y |
```

**Rules:**
- No implementation code in the spec — describe behavior, not syntax
- Every "File Concerned" entry must name a real file verified with Glob/Grep
- Keep it concise: the spec should fit on one screen for small features

## Step 4: Self-Review (Mandatory)

Before showing the spec to the user, run these four checks and fix inline:

1. **Placeholder scan** — Any TBD, TODO, "to be defined", empty sections? Fill them or remove the section.
2. **Internal coherence** — Do Technical Decisions contradict Scope? Does Files Concerned match Key Concepts? Resolve conflicts.
3. **Scope check** — Can each in-scope item be completed in 2-5 minutes? If not, decompose further or narrow.
4. **Ambiguity check** — Any sentence interpretable two ways? Pick one meaning and make it explicit.

Fix issues directly. No separate review pass needed — just fix and proceed.

## Step 5: User Approval (Mandatory)

Present the spec to the user:
> "Spec written to `{session_dir}/01-spec.md`. Please review and let me know: approve, modify, or rework."

Wait for the response. Do not proceed without it.

- **Approve:** Return `SPEC_APPROVED` to the pipeline orchestrator
- **Modify:** Incorporate changes, re-run self-review (Step 4), re-present
- **Rework:** Return to Step 1 with the new direction

No handoff to the plan phase without explicit user approval.

## Anti-Patterns

- Skipping questions and jumping straight to spec writing
- Writing code, pseudocode, or implementation details in the spec
- Proposing an implementation plan — that is the `plan` skill's job
- Starting the brainstorm server for non-visual work
- Presenting more than 3 options per question (cognitive overload)
- Combining the visual companion offer with a clarifying question
- Listing files in "Files Concerned" without verifying they exist

## Output Contract

| Key | Value |
|-----|-------|
| **File produced** | `{session_dir}/01-spec.md` |
| **Return status** | `SPEC_APPROVED` (success) or `SPEC_REWORK` (user wants to restart) |
| **Next phase** | `plan` skill receives the approved spec |
