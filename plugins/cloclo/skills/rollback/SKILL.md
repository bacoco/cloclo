---
name: rollback
description: "Use when the user asks to roll back or undo work from a CLoClo pipeline run (/rollback, 'undo pipeline', annule, reviens en arriere)."
---

# /rollback — Undo Pipeline Work

Safely undo commits made by the CLoClo pipeline. Two modes: **soft** (uncommit, keep the
files as staged changes) and **hard** (also discard the file changes). This skill only
touches pipeline commits and never force-pushes; read the whole flow before acting.

## Step 0: Sanity checks (fail gracefully)

```bash
# Are we in a git repo at all?
git rev-parse --git-dir >/dev/null 2>&1 || { echo "NOT_A_REPO"; exit 0; }

# Detached HEAD? Rolling back is ambiguous — bail with a clear message.
git symbolic-ref -q HEAD >/dev/null || echo "DETACHED_HEAD"

# How many commits does history actually have? (avoids HEAD~N errors on short history)
DEPTH=$(git rev-list --count HEAD 2>/dev/null || echo 0)
echo "DEPTH=$DEPTH"
```

Handle each case explicitly, then stop:
- **NOT_A_REPO** → `Pas de dépôt git ici — rien à annuler.`
- **DETACHED_HEAD** → `HEAD est détaché (pas sur une branche). Checkout une branche avant de rollback.`
- **DEPTH=0** → `Aucun commit dans l'historique — rien à annuler.`
- If a requested range would exceed `DEPTH` (e.g. `reset HEAD~10` in a 3-commit repo),
  clamp to the repo root or refuse with `Seulement {DEPTH} commit(s) dans l'historique.`

## Step 1: Identify the pipeline commits

The **only** reliable pipeline-commit boundary is `base_ref..HEAD` from the latest session's
`checkpoint.json` (Phase 5 execution commits carry no marker). Find the latest session by
mtime and read the boundary from it.

```bash
SESSION_DIR=$(ls -dt docs/cloclo-sessions/*/ 2>/dev/null | head -1)
CHECKPOINT="$SESSION_DIR/checkpoint.json"
if [ -n "$SESSION_DIR" ] && [ -f "$CHECKPOINT" ]; then
  BASE_REF=$(jq -r '.artifacts.base_ref // empty' "$CHECKPOINT")
  # Pipeline-created commits (either key may be present):
  jq -r '(.artifacts.commit_list // .artifacts.commits // [])[]' "$CHECKPOINT"
  echo "BASE_REF=$BASE_REF"
fi
```

**If a checkpoint with `base_ref` exists** → default the rollback range to `${BASE_REF}..HEAD`:

```bash
git log --oneline "${BASE_REF}..HEAD"
```

Then diff the range against the recorded `commit_list` and **flag interlopers** — any commit
in the range that the pipeline did NOT create (a user commit interleaved with pipeline work):

```bash
# For each SHA in ${BASE_REF}..HEAD, check membership in commit_list.
git rev-list "${BASE_REF}..HEAD"
```

For every SHA in the range that is absent from `commit_list`, tell the user:
`Ce commit ne vient pas du pipeline : <sha> "<subject>" — l'exclure du rollback ?`
Default to excluding non-pipeline commits.

**If no checkpoint / no `base_ref` exists** → fall back to the manual numbered list:

```bash
git log --oneline -10
```

```
Recent commits:
  1. a1b2c3d feat: add upload component (3 min ago)
  2. d4e5f6g feat: add upload tests (5 min ago)
  3. h7i8j9k refactor: extract form hook (8 min ago)
  4. k0l1m2n chore: update deps (yesterday) ← probably not from this pipeline
```

**If the session produced zero commits** (empty `commit_list` / `base_ref == HEAD`) →
`Cette session n'a créé aucun commit — rien à annuler.` and stop.

## Step 2: Safety checks

```bash
git status --porcelain
```

If the tree is **not** clean, be precise about what each mode does — do NOT claim work is
always preserved:

```
Tu as des changements non commités.
- Soft rollback : ils sont conservés (le reset --soft ne touche pas le working tree).
- Hard rollback : ils seraient DÉTRUITS. Je refuse tant que l'arbre n'est pas propre,
  ou je les mets de côté avec `git stash push -u` d'abord (je te le dis explicitement).
```

Detect commits that are **already pushed** — compare against the current branch's upstream,
NOT the remote default branch:

```bash
git rev-parse --abbrev-ref --symbolic-full-name @{u} >/dev/null 2>&1 \
  && git log --oneline @{u}..HEAD 2>/dev/null | wc -l \
  || echo "NO_UPSTREAM"
```

- **NO_UPSTREAM** → no upstream configured: treat **all** commits as local (safe to reset).
- Otherwise, commits NOT in `@{u}..HEAD` are already pushed. Never `reset --hard` a pushed
  commit (unrecoverable given the NEVER-force-push rule) — revert it instead:

```
ATTENTION : {N} de ces commits sont déjà poussés (upstream).
Soft rollback : sans risque (local). Pour les commits poussés, hard = `git revert` (nouveaux
commits d'annulation), jamais `reset --hard`. Ne force-push jamais.
```

## Step 3: Ask what to undo

The default selection is the flagged pipeline range from Step 1.

```
Que veux-tu annuler ?

A. Dernier commit du pipeline seulement
B. Toute la plage du pipeline (base_ref..HEAD)
C. Les N derniers commits (tu précises N, borné à la plage pipeline)
D. Annuler — ne rien faire
```

## Step 4: Choose rollback type

Always show the exact file impact of the chosen range BEFORE asking (soft and hard both):

```bash
git diff --stat "${BASE_REF}..HEAD"   # or the selected sub-range
```

```
Comment annuler ?

Soft — Décommit, mais garde les fichiers modifiés (staged)
  → git reset --soft <range-base>
  → Tu peux ré-éditer et re-committer.
  → Note : des changements staged peuvent bloquer la reprise (garde-fou arbre-propre
    de la Phase 9). Committe ou stash avant de relancer /pipeline.

Hard — Revenir complètement en arrière (fichiers inclus)
  → commits LOCAUX : git reset --hard <range-base> (arbre propre requis)
  → commits POUSSÉS ou merge/squash : git revert (voir Step 5)

Choix ? (soft/hard)
```

## Step 5: Execute

Use an explicit base SHA (`${BASE_REF}` or the selected commit's parent) rather than a bare
`HEAD~{N}` so short/interleaved history can't miscount.

**Soft rollback:**
```bash
git reset --soft "$BASE_REF"
```
Print: `Commits décommittés. Les fichiers restent modifiés (staged). Tu peux ré-éditer.`

**Hard rollback — local commits, clean tree only:**
```bash
# Gate: refuse or stash first if the tree is dirty.
if [ -n "$(git status --porcelain)" ]; then
  git stash push -u -m "rollback-safety $(date +%F-%T)"   # only after telling the user
fi
git reset --hard "$BASE_REF"
```
Print: `Commits annulés, fichiers revenus à l'état précédent.` (If you stashed, add:
`Tes changements non commités sont dans git stash (stash@{0}).`)

**Hard rollback — pushed commits, or any merge/squash commit:**
```bash
# Plain revert of a linear range fails on merge commits; use -m 1 for those.
# Phase 9 squash-merge case: undo ONE squash SHA recorded in the checkpoint.
git revert -m 1 <squash_or_merge_sha> --no-edit     # merge/squash commit
git revert "${BASE_REF}..HEAD" --no-edit            # linear, non-merge range
```
Detect merge/squash commits first (`git rev-list --merges "${BASE_REF}..HEAD"`, or the
`squash_sha` recorded in the checkpoint after Phase 9 merged to main) and route them through
`git revert -m 1 <sha>`. Print: `Commits revertés via nouveaux commits d'annulation. Push quand tu es prêt.`

**Post-auto-merge scenario:** after Phase 9 squash-merges to `main`, the whole run is a
single squash commit (its SHA is in the checkpoint). Undoing it is one `git revert -m 1 <squash_sha>`
— not a multi-commit range.

## Step 6: Update pipeline state

Locate the session the same way as Step 1: the most recent directory by mtime under
`docs/cloclo-sessions/` — its `checkpoint.json` holds the phase state.

If that `checkpoint.json` exists:
1. Read it.
2. Set `last_completed_phase` to the phase BEFORE the rolled-back work.
3. Write the updated checkpoint.
4. Print: `Checkpoint mis à jour — /pipeline reprendra à Phase {N}.`

If a `handoff.md` exists, append:
```
## Rollback: {date}
- Rolled back {N} commits ({soft|hard})
- Pipeline checkpoint reset to Phase {M}
```

## Rules

- **NEVER force-push.** Use `git revert` (with `-m 1` for merge/squash commits) for anything
  already pushed — a `reset --hard` on pushed commits is unrecoverable under this rule.
- **NEVER `reset --hard` on a dirty tree.** Require a clean tree, or `git stash push -u` first
  and say so; state precisely what each mode preserves (soft keeps the working tree, hard
  discards it).
- **ALWAYS show exactly which files will change** — `git diff --stat <range>` in the
  confirmation for both soft and hard.
- **Only roll back pipeline commits.** Default to `base_ref..HEAD` from the latest checkpoint
  and flag any non-pipeline commit in the range for exclusion.
- **Fail gracefully** on no-repo, detached HEAD, short/empty history, and zero-commit sessions.
- **Update checkpoint.** The pipeline must know where to resume after rollback.
