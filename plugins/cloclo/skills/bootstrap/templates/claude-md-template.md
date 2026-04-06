# CLAUDE.md

## What This Is
**{{PROJECT_NAME}}** is {{DESCRIPTION}}. Stack: {{STACK}}.

## Project Structure
```
{{TREE}}
```

## Build & Dev Commands

### {{FRAMEWORK_1}}
```bash
{{COMMANDS}}
```

### {{FRAMEWORK_2}} (if applicable)
```bash
{{COMMANDS}}
```

## Architecture — How Services Connect
```
{{ARCHITECTURE_DIAGRAM}}
```

## Key Patterns
- **{{PATTERN_1}}**: {{DESCRIPTION}}
- **{{PATTERN_2}}**: {{DESCRIPTION}}
- **{{PATTERN_3}}**: {{DESCRIPTION}}

## Regles Fondamentales (OBLIGATOIRE)

1. **Confidence first** — Ne jamais modifier sans etre au moins 95% sur. En dessous, poser des questions ciblees.
2. **Read before writing** — Toujours lire le code existant (Read/Grep/Glob) avant de modifier. Ne jamais supposer l'etat actuel.
3. **Act fast, verify immediately** — Apres chaque fix, tester immediatement (test, curl, build) et montrer l'output.
4. **Explorer avant de creer** — Toujours Glob/Grep avant de creer un hook, store, ou composant. Ils existent probablement deja.
5. **Lire les types avant d'acceder** — Verifier l'interface/type reel avant de supposer qu'un champ existe.
6. **Commit par checkpoint** — Apres 3-5 changements testes, commit. Jamais 10+ changements non commites.

## Erreurs Recurrentes (OBLIGATOIRE)

1. **Explorer avant de creer** — Toujours Glob/Grep avant de creer. Ca existe probablement deja.
2. **Lire les interfaces avant d'acceder aux champs** — Ne jamais supposer qu'un champ existe. Verifier la structure reelle.
3. {{STACK_SPECIFIC_ERROR_1}}
4. {{STACK_SPECIFIC_ERROR_2}}

## Demarrage Session (OBLIGATOIRE)

Au TOUT PREMIER message d'une session, AVANT de repondre au user :

1. `git log --oneline -5` + `git status --short`
2. `docker ps --format "table {{.Names}}\t{{.Status}}" | head -15` (si Docker)
3. Lire `MEMORY.md` pour le contexte persistant
4. Resume en 3-4 lignes : "Dernier travail: X. Etat: Y services up, Z fichiers modifies."
5. Proposer l'action la plus pertinente OU demander "Qu'est-ce qu'on attaque ?"

## Test Credentials (Dev)
```
{{CREDENTIALS}}
```

---
**Adapte chaque section au projet reel. Les sections marquees OBLIGATOIRE sont non-negociables.**
**Les {{PLACEHOLDERS}} doivent etre remplaces par les valeurs reelles detectees en Phase 1.**
