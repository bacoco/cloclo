---
name: pipeline
description: "CLOco — Claude + Codex Collaboration pipeline. Orchestrates the full dev cycle by chaining SuperPowers skills (brainstorming, writing-plans, subagent-driven-development, verification-before-completion) with Codex reviews between phases. Triggers on: /pipeline, new feature, implement, build, create"
---

# CLOco Pipeline

Orchestrate the full development cycle by combining **existing skills** with
Codex review phases and interactive decision points.

**CLOco does NOT reimplement brainstorming, planning, execution, or verification.**
It invokes the real skills and adds Codex reviews + decision points between them.

## Prerequisites

Check these at pipeline start. If a prerequisite is missing, show the install
command and let the user decide whether to continue in degraded mode.

### Required

| Prerequisite | Check | Install |
|---|---|---|
| SuperPowers plugin | Skill `superpowers:brainstorming` is available | Add `"superpowers@superpowers-marketplace": true` to `~/.claude/settings.json` and restart Claude Code. If the marketplace is not registered, add to `extraKnownMarketplaces`: `"superpowers-marketplace": {"source": {"source": "github", "repo": "obra/superpowers-marketplace"}}` |
| Codex CLI | `codex --version` | `npm install -g @openai/codex` then `codex login` |
| Codex Claude Code plugin | `find ~/.claude/plugins -name codex-companion.mjs -path '*/codex/scripts/*'` finds a file | Add `"codex@openai-codex": true` to `~/.claude/settings.json`. If the marketplace is not registered, add to `extraKnownMarketplaces`: `"openai-codex": {"source": {"source": "github", "repo": "openai/codex-plugin-cc"}}` |

### Degraded Modes

| Missing | Consequence |
|---|---|
| SuperPowers | **STOP.** Cannot proceed — brainstorming, planning, execution, and verification depend on it. |
| Codex CLI or plugin | **WARNING.** Continue without Codex reviews. Phases 2, 4, and 6 are skipped. The user gets Claude-only mode. |
| Codex not authenticated | **WARNING.** Same as above. Show: "Run `codex login` to enable Codex reviews." |

## Session Setup

1. Ask the user what they want to build (or take their initial message).
2. Create session directory: `docs/cloco-sessions/YYYY-MM-DD-<slug>/`
   - `<slug>` = 2-3 word kebab-case summary of the topic
3. Initialize `session.log`:
   ```
   [timestamp] CLOco session started: <slug>
   [timestamp] Prerequisites: superpowers=OK, codex=OK|MISSING, auth=OK|MISSING
   ```
4. If the project has specific verification needs, create `pipeline.config.md`
   in the session directory (ask the user or auto-detect from project files).

## Phase 1: Design — Invoke `superpowers:brainstorming`

**Invoke Skill("superpowers:brainstorming")**

This gives you the FULL SuperPowers brainstorming experience:
- One-question-at-a-time exploration
- Visual companion with HTML mockups in the browser
- Options A/B/C with pros/cons
- 2-3 approach proposals with trade-offs
- Design-for-isolation principles
- "Too simple to need a design" anti-pattern prevention
- Spec self-review (placeholders, coherence, scope, ambiguity)
- User approval gate

**After brainstorming completes:** The spec will be in `docs/superpowers/specs/YYYY-MM-DD-*-design.md`.
Copy or symlink it to `{session_dir}/01-spec.md` for session tracking.

Log: `[timestamp] Phase 1 complete: 01-spec.md`

**GATE:** Do not proceed until the user has explicitly approved the spec.

---

## Phase 2: Codex Review Spec

**If Codex available:** Invoke the `codex-review` skill with:
- `review_type`: `spec`
- `input_file`: `{session_dir}/01-spec.md`
- `output_file`: `{session_dir}/02-codex-review-spec.md`

**If Codex unavailable:** Skip with warning, go directly to Decision Point #1.

Log: `[timestamp] Codex review spec: {status}`

### Decision Point #1

Present the Codex findings (raw, no filtering) and ask:

```
Codex a review ta spec. Voici ses findings :

[3-5 line summary of key findings from 02-codex-review-spec.md]

Fichier complet : {session_dir}/02-codex-review-spec.md

Que veux-tu faire ?

A. Integrer tous les findings et continuer
   → SuperPowers corrige la spec, ecrit 03-spec-v2.md

B. Integrer certains findings (tu precises lesquels)

C. Ignorer la review et continuer avec la spec actuelle

D. Demander a Codex de creuser un point precis
   → Codex repart en review ciblee

E. Modifier la spec toi-meme
   → Tu edites le fichier, dis "c'est bon" quand pret

Ou tape ce que tu veux — commentaire libre.
```

Log the user's choice in `session.log`.

After A or B: SuperPowers corrects the spec → `{session_dir}/03-spec-v2.md`.
Do NOT automatically re-submit to Codex. User controls re-review via D.

---

## Phase 3: Plan — Invoke `superpowers:writing-plans`

**Invoke Skill("superpowers:writing-plans")**

Input: the approved spec (01-spec.md or 03-spec-v2.md).

This gives you the FULL SuperPowers plan writing:
- Scope check with decomposition
- File structure table
- Bite-sized tasks (2-5 minutes each)
- TDD cycle (write failing test, verify failure, implement, verify pass)
- Complete code blocks (no TBD, no placeholders)
- Pre-written commit messages
- Self-review checklist
- DRY, YAGNI, frequent commits

**After plan is written:** The plan will be in `docs/superpowers/plans/YYYY-MM-DD-*.md`.
Copy or symlink it to `{session_dir}/04-plan.md`.

Log: `[timestamp] Phase 3 complete: 04-plan.md`

---

## Phase 4: Codex Review Plan

**If Codex available:** Invoke `codex-review` with:
- `review_type`: `plan`
- `input_file`: `{session_dir}/04-plan.md`
- `output_file`: `{session_dir}/05-codex-review-plan.md`
- `spec_path`: path to approved spec

**If Codex unavailable:** Skip with warning.

### Decision Point #2

Same A-E format as Decision Point #1.
If corrections: SuperPowers rewrites → `{session_dir}/06-plan-v2.md`.

---

## Phase 5: Execute — Invoke `superpowers:subagent-driven-development`

**Invoke Skill("superpowers:subagent-driven-development")**

Input: the approved plan (04-plan.md or 06-plan-v2.md).

This gives you the FULL SuperPowers execution:
- Fresh subagent per task (no context pollution)
- Two-stage review: spec compliance then code quality
- Status handling (DONE, DONE_WITH_CONCERNS, BLOCKED, NEEDS_CONTEXT)
- Review loops until approved
- Model selection guidance (cheap for mechanical, capable for architecture)
- Process flow with decision diamonds
- Red flags and anti-patterns
- Final integration review

Log: `[timestamp] Phase 5 complete: [commit list]`

Record `base_ref` (git SHA before execution) and `commit_list` (all new commits).

---

## Phase 6: Codex Review Implementation

**If Codex available:** Invoke `codex-review` with:
- `review_type`: `impl`
- `input_file`: `{session_dir}/04-plan.md` (or 06-plan-v2.md)
- `output_file`: `{session_dir}/07-codex-review-impl.md`
- `spec_path`: approved spec
- `plan_path`: approved plan
- `base_ref`: git SHA recorded before Phase 5
- `commit_list`: all commits from Phase 5

**If Codex unavailable:** Skip with warning.

### Decision Point #3

```
Codex a review l'implementation. Voici ses findings :

[Summary of findings]

A. Integrer tous les findings → SuperPowers corrige, nouveau commit

B. Corriger certains findings (tu precises)

C. Ignorer et passer a la verification

D. Demander a Codex de creuser un bug potentiel

E. Lancer un audit complet du projet

Ou commentaire libre.
```

---

## Phase 7: Verify — Invoke `superpowers:verification-before-completion`

**Invoke Skill("superpowers:verification-before-completion")**

This gives you the FULL SuperPowers verification:
- Iron Law: NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
- 5-step Gate Function (IDENTIFY, RUN, READ, VERIFY, ONLY THEN)
- Common Failures table
- Red Flags section
- Rationalization prevention table
- Key Patterns (tests, regression, build, requirements, delegation)

If `pipeline.config.md` exists in the session, use its verification commands.
Otherwise, let the verification skill auto-detect or ask the user.

Log: `[timestamp] Phase 7 complete: {PASSED|FAILED}`

---

## Session File Structure

```
docs/cloco-sessions/YYYY-MM-DD-<slug>/
├── 01-spec.md                  ← From superpowers:brainstorming
├── 02-codex-review-spec.md     ← From codex-review skill
├── 03-spec-v2.md               ← If corrections after review
├── 04-plan.md                  ← From superpowers:writing-plans
├── 05-codex-review-plan.md     ← From codex-review skill
├── 06-plan-v2.md               ← If corrections after review
├── 07-codex-review-impl.md     ← From codex-review skill
├── session.log                 ← All decisions + timestamps + job-ids
└── pipeline.config.md          ← Optional verification config
```

## Session Log Format

```
[2026-04-06T14:30:00] CLOco session started: auth-refactor
[2026-04-06T14:30:01] Prerequisites: superpowers=OK, codex=OK, auth=OK
[2026-04-06T14:45:00] Phase 1 complete: 01-spec.md
[2026-04-06T14:45:30] User approved spec
[2026-04-06T14:50:00] Codex review spec started (job-id: task-abc123)
[2026-04-06T14:55:00] Codex review spec complete: 02-codex-review-spec.md
[2026-04-06T14:55:30] Decision #1: A (integrate all)
[2026-04-06T14:58:00] Spec corrected: 03-spec-v2.md
[2026-04-06T15:10:00] Phase 3 complete: 04-plan.md
[2026-04-06T15:15:00] Codex review plan started (job-id: task-def456)
[2026-04-06T15:22:00] Codex review plan complete: 05-codex-review-plan.md
[2026-04-06T15:22:30] Decision #2: B (integrate findings 1,3, ignore 2)
[2026-04-06T15:25:00] Plan corrected: 06-plan-v2.md
[2026-04-06T15:26:00] Phase 5 started (base_ref: a1b2c3d)
[2026-04-06T15:45:00] Phase 5 complete: 5 commits (a1b..f6e)
[2026-04-06T15:50:00] Codex review impl started (job-id: task-ghi789)
[2026-04-06T16:02:00] Codex review impl complete: 07-codex-review-impl.md
[2026-04-06T16:02:30] Decision #3: A (fix all)
[2026-04-06T16:10:00] Phase 7: VERIFICATION_PASSED
```

## Important Rules

1. **Do NOT reimplement SuperPowers or Codex skills.** Invoke them. They are the real thing.
2. **After correction (A or B), do NOT auto-resubmit to Codex.** User controls via option D.
3. **Codex reviews are FOREGROUND.** Claude waits, shows "Codex is reviewing...", reads the result.
4. **If user types anything other than A-E:** treat as free-form comment and adapt.
5. **Each phase outputs to session dir** with numbered filenames for traceability.
6. **Session can be resumed.** Check session.log for last completed phase and continue from there.
7. **SuperPowers specs and plans** are saved to their own directories (`docs/superpowers/specs/`, `docs/superpowers/plans/`). CLOco copies or symlinks them into the session dir for session tracking.
