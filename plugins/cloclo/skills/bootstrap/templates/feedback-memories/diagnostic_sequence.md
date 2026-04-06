---
name: diagnostic_sequence
description: Sequence de diagnostic quand un build/test/deploy echoue
type: feedback
---
Quand quelque chose echoue, suivre cette sequence AVANT de proposer un fix :

**Why:** L'IA a tendance a proposer des fixes bases sur l'intuition plutot
que sur l'erreur reelle. Lire l'erreur complete evite les fixes a cote.

**How to apply:**
1. Lire l'erreur COMPLETE (pas juste la derniere ligne)
2. Identifier la PREMIERE erreur (les suivantes sont souvent des cascades)
3. Verifier si l'erreur est dans du code modifie ou existant
4. Si docker : `docker ps` puis `docker logs --tail=50 <service>`
5. Si import/module : verifier que le package est installe
6. Ne JAMAIS dire "ca devrait marcher" apres un echec
