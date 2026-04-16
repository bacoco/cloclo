---
name: rollback
description: "Undo pipeline work — soft (uncommit, keep files) or hard (revert files). Shows recent commits, checks for uncommitted changes, confirms before acting. Triggers: /rollback, undo, annule, reviens en arriere"
---

# /rollback — Undo Pipeline Work

Safely undo commits made by the CLoClo pipeline. Two modes: soft (keep changes as unstaged) and hard (revert all file changes).

## Step 1: Show Recent Commits

```bash
git log --oneline -10
```

Display to user with numbered list:
```
Recent commits:
  1. a1b2c3d feat: add upload component (3 min ago)
  2. d4e5f6g feat: add upload tests (5 min ago)
  3. h7i8j9k refactor: extract form hook (8 min ago)
  4. k0l1m2n chore: update deps (yesterday) ← probably not from this pipeline
```

## Step 2: Safety Checks

```bash
git status --porcelain
```

If uncommitted changes exist:
```
WARNING: You have uncommitted changes. Rollback will affect committed code only.
Uncommitted changes are preserved regardless of rollback type.
```

Check if commits are already pushed:
```bash
git log --oneline origin/HEAD..HEAD 2>/dev/null | wc -l
```

If pushed commits would be affected:
```
WARNING: {N} of these commits are already pushed to remote.
Soft rollback is safe (local only). Hard rollback will create revert commits.
Do NOT force-push unless you are the only person on this branch.
```

## Step 3: Ask What to Undo

```
Que veux-tu annuler ?

A. Dernier commit seulement (#1)
B. Les N derniers commits (tu precises N)
C. Jusqu'au commit #X (tu precises)
D. Annuler — ne rien faire
```

## Step 4: Choose Rollback Type

After the user picks commits:

```
Comment annuler ?

Soft — Uncommit, mais garder les fichiers modifies (staged)
  → git reset --soft HEAD~{N}
  → Tu peux re-editer et re-committer

Hard — Revenir en arriere completement (fichiers aussi)
  → git revert HEAD~{N}..HEAD --no-edit (si pousse)
  → git reset --hard HEAD~{N} (si local seulement)
  → Les changements sont perdus

Choix ? (soft/hard)
```

## Step 5: Execute

**Soft rollback:**
```bash
git reset --soft HEAD~{N}
```
Print: `{N} commits annules. Les fichiers sont toujours modifies (staged). Tu peux re-editer.`

**Hard rollback (local commits only):**
```bash
git reset --hard HEAD~{N}
```
Print: `{N} commits annules. Les fichiers sont revenus a l'etat precedent.`

**Hard rollback (pushed commits):**
```bash
git revert HEAD~{N}..HEAD --no-edit
```
Print: `{N} commits revertes via nouveaux commits de revert. Push quand pret.`

## Step 6: Update Pipeline State

If a `checkpoint.json` exists in the most recent session dir:
1. Read it
2. Set `last_completed_phase` to the phase BEFORE the rolled-back work
3. Write updated checkpoint
4. Print: `Checkpoint mis a jour — /pipeline reprendra a Phase {N}.`

If a `handoff.md` exists, append:
```
## Rollback: {date}
- Rolled back {N} commits ({soft|hard})
- Pipeline checkpoint reset to Phase {M}
```

## Rules

- **NEVER force-push.** Use `git revert` for pushed commits.
- **ALWAYS confirm before hard rollback.** Show exactly which files will change.
- **Preserve uncommitted work.** Rollback only touches committed history.
- **Update checkpoint.** The pipeline must know where to resume after rollback.
