---
name: commit_checkpoints
description: Commit apres 3-5 changements testes — jamais 10+ non commites
type: feedback
---
Apres 3 changements testes avec succes, creer un commit.
Ne jamais accumuler plus de 5 changements non commites.

**Why:** Accumuler beaucoup de changements sans commit rend le rollback
impossible et transforme une petite erreur en perte de tout le travail.

**How to apply:**
- Grouper les commits par logique (pas par volume)
- Format : `type(scope): description` — feat, fix, refactor, test, docs
- Si la tache necessite 10+ fichiers : commit en groupes de 3-4
- Un revert de 3 fichiers est gerable. Un revert de 15 est un cauchemar.
