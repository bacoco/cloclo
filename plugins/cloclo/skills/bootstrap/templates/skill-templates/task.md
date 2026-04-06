# Task — Template

## Frontmatter
```yaml
name: task
description: "Execute une tache numerotee. Triggers: /task"
```

## Input
`/task N — description`

## Workflow
1. **Lire la tache** — Comprendre ce qui est demande
2. **Explorer les fichiers concernes** — Max 5 lectures avant de commencer
3. **Implementer** — Code minimal et focalise
4. **Verifier** — Type-check, tests, imports
5. **Commit** — `feat(task-N): <description>`

## Contraintes
- Ne PAS creer de nouveaux fichiers sauf si absolument necessaire
- Ne PAS refactorer le code environnant
- Ne PAS ajouter des docstrings au code non modifie
- Rester focalise sur la tache — pas de scope creep
