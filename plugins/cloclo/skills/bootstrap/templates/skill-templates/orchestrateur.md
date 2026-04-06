# Orchestrateur — Template

## Frontmatter
```yaml
name: orchestrateur
description: "Orchestrateur intelligent. Analyse le contexte et dispatch les bons skills. Triggers: /orchestrateur, help me, que faire, next step, je suis perdu, par ou commencer"
```

## Phase 1 — Lire le contexte (10 secondes max)

Lancer EN PARALLELE :
```bash
git status --short && git diff --stat HEAD
docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null | head -20
git log --oneline -5
```

Aussi : relire les derniers messages de la conversation.

## Phase 2 — Router

| Priorite | Signal detecte | Profil |
|----------|---------------|--------|
| 1 | Erreur, crash, 500, timeout, "bug" | **DEBUGGER** |
| 2 | Services down | **OPS** |
| 3 | "audit", "qualite", "verifie" | **AUDITEUR** |
| 4 | Fichiers modifies + pas rebuild | **DEPLOYER** |
| 5 | Travail actif sur {{DOMAIN_1}} | **{{DEV_1}}** |
| 6 | Travail actif sur {{DOMAIN_2}} | **{{DEV_2}}** |
| 7 | "review", "relis" | **REVIEWER** |
| 8 | "met a jour la doc", "update sources" | **DOC-SYNC** |
| 9 | Debut de session, rien de specifique | **HEALTH-CHECK** |
| 10 | Rien ne matche | **CONSEILLER** |

## Phase 3 — Dispatch

Annoncer : `"Contexte: [resume 1 ligne]. Je lance le profil [NOM]."`
Invoquer le skill correspondant.

Si HEALTH-CHECK et tout OK : "Tout tourne. Qu'est-ce qu'on attaque ?"
Si CONSEILLER : Lister les 5 actions les plus pertinentes.

## Regles
1. **UN seul profil** — ne pas combiner
2. **Action immediate** — dispatcher directement quand le profil est clair
3. **Rapport court** — 2-3 lignes apres dispatch
