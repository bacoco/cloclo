# Code Review — Template

## Frontmatter
```yaml
name: code-review
description: "Review de code end-to-end. Triggers: review, relis, verifie le code, audit code"
```

## Scope
1. `git diff --stat HEAD~5` — Quels fichiers ont change recemment ?
2. Pour chaque fichier modifie : lire le code, comprendre le changement

## Checklist
- [ ] Pas de secrets commites (.env, credentials)
- [ ] Pas de console.log / print de debug
- [ ] Gestion d'erreurs appropriee
- [ ] Types corrects (pas de `any` en TS, pas de types manquants en Python)
- [ ] Pas de code duplique
- [ ] Tests pour les nouvelles fonctionnalites
- [ ] Pas de regressions dans les fonctionnalites existantes

## Rapport
Pour chaque issue trouvee :
- **Fichier:ligne** — Description du probleme
- **Severite** : High / Medium / Low
- **Fix suggere** : [code ou description]
