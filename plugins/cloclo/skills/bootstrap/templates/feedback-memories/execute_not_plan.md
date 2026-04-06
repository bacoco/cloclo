---
name: execute_not_plan
description: Quand le user dit fix/cree/corrige — executer, pas planifier
type: feedback
---
Ne JAMAIS proposer un plan de 15 etapes puis attendre validation.
Quand le user dit "fix", "cree", "corrige", "merge" — le FAIRE.

**Why:** Le user paie pour du code, pas pour des documents de planification.
Les plans sans execution sont la frustration #1 des utilisateurs d'IA coding.

**How to apply:** Si le verbe est un imperatif d'action :
1. Lire le code concerne (verify first)
2. Faire le changement
3. Tester
4. Montrer le resultat
Pas de "voici mon plan en 8 etapes" — juste faire.
