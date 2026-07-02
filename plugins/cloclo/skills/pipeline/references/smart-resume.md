# Smart-Resume + Natural-Language Directives

`/pipeline` takes **no flags**. Two ways to resume an existing session:
the terminal dialogue (bare invocation) or a natural-language directive
(free text after the command).

## Resume State: checkpoint.json First, Artifact Scan as Fallback

**`checkpoint.json` is authoritative.** When it exists and parses, its
`completed_phases` ordered list (see `session-files.md`) determines
where the session stands — do NOT re-derive state from artifacts.

**The artifact scan below is the FALLBACK**, used only when
`checkpoint.json` is missing or corrupt (unparseable JSON, missing
`completed_phases`). It reconstructs the same state from files on disk.

Either way, the result feeds the same single A/B/C resume question —
there is only one resume dialogue.

## Detection Map (fallback artifact scan)

| Artifact found | Means | Effect |
|----------------|-------|--------|
| `{session_dir}/01-spec.md` (or `03-spec-v2.md`) | Phase 1 done | Reuse spec |
| `{session_dir}/02-codex-review-spec.md` | Phase 2 done | Reuse review |
| `{session_dir}/04-plan.md` (or `06-plan-v2.md`) | Phase 3 done | Reuse plan |
| `{session_dir}/05-codex-review-plan.md` | Phase 4 done | Reuse review |
| `{session_dir}/task-briefs/` has files | Phase 4.5 done | Reuse briefs |
| Feature branch has commits ahead of main | Phase 5 done / partial | Reuse commits |
| `{session_dir}/07-codex-review-impl.md` recent | Phase 6 done | Reuse review |
| `{session_dir}/07b-coderabbit-review-impl.md` | Phase 6.5 done | Reuse review |
| `{session_dir}/09-compliance-report.md` | Phase 7 done | Reuse report |
| Open PR exists for the branch | Phase 9 started | Resume at bot loop |

## Decision Logic

1. Read `checkpoint.json`. If valid → state = its `completed_phases`.
   If missing/corrupt → run the fallback artifact scan.
2. If user passed free text after `/pipeline` → interpret as directive, skip dialogue.
3. If nothing exists and no directive → run from Phase 1.
4. If prior state exists and no directive → ask ONE terminal question:

```
Session "{slug}" already has:
  ✓ Phase 1 spec    ({path})
  ✓ Phase 3 plan    ({path})
  ✓ Phase 5 commits (branch {branch}, {N} commits ahead of main)

Missing phases: 2, 4, 6, 6.5, 7, 7.5, 8, 9

What next?
A. Continue with the existing artifacts (skip what is done)   ← default
B. Redo everything from Phase 1 (overwrites existing artifacts)
C. Jump to the review phase (start at Phase 6)
```

Default = A. No flags, ever.

## Natural-Language Directives

`/pipeline <free text>` skips the dialogue. Interpret the text, log the
interpretation, act. French, English, and mixed phrasing all accepted.

### Interpretation Map

| User says | Intent | Effect |
|-----------|--------|--------|
| `passe au plan`, `start at plan`, `skip spec` | Skip 1+2, start at 3 | Use existing spec, else user's initial message |
| `passe a la review`, `review et merge`, `findings only`, `le code est ecrit` | Start at 6 | Review → verify → PR → merge on current commits |
| `refais tout`, `from scratch`, `redo all`, `ecrase tout` | Start at 1 | Backup session dir to `.bak/`, fresh run |
| `continue`, `reprend`, `resume` | First missing phase | Dialogue option A |
| `skip codex`, `pas de codex` | Skip Phases 2+4+6 | No Codex reviews (CodeRabbit/Gemini still run on PR) |
| `pas de PR`, `no PR`, `direct merge` | Skip Phase 9 | Commits stay on feature branch or merge direct |
| `spike mode`, `en prototype` | maturity=spike | Soft gates, no Phase 9 |
| `ship mode`, `production` | maturity=ship | Hard gates, adversarial pass |
| `avec coderabbit`, `with coderabbit` | Enable Phase 6.5 | CodeRabbit CLI review runs (enable condition: `review-chain.md`) |
| `avec claude action`, `with codex cloud` | Opt-in extra bots | Add to Phase 9 wait-set |

### Parsing Rules

- **Liberal interpretation.** 80% clear intent → act. Log decision.
- **Log before acting:**
  ```
  [timestamp] Directive received: "{user text}"
  [timestamp] Interpreted as: start at Phase 6, skip Phases 1-5
  ```
- **Compositional directives.** Multiple hints combine: `/pipeline passe
  au plan, pas de codex` → start at Phase 3 AND skip Phases 2+4+6.
- **Ambiguity → ONE clarifying question** (not a full dialogue), then act.

### Escape Hatch

User truly needs an exotic flow → edit the session dir manually before
re-running `/pipeline`. No flags, ever.

## Branch Lifecycle

Phase 5 creates a feature branch. Phase 9 opens a PR on it. On successful
auto-merge:

```bash
gh pr merge --squash --delete-branch --auto
```

Branch deleted both locally and on the remote. On escalation (iteration
cap, patch failed, CI blocked), the branch stays alive so the user can
push manual fixes.
