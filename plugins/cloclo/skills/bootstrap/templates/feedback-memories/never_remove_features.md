---
name: never_remove_features
description: En simplifiant ou refactorant, changer le HOW pas le WHAT
type: feedback
---
Quand on simplifie, refactore, ou reecrit du code, ne JAMAIS retirer
un comportement existant sans que le user l'ait explicitement demande.

**Why:** L'IA tend a "simplifier" en supprimant des features edge-case
qu'elle considere non essentielles. Le user decouvre les regressions plus tard.

**How to apply:**
1. AVANT de reecrire : lister tous les comportements existants
2. Pendant : changer l'implementation, pas les features
3. APRES : verifier que chaque comportement de la liste fonctionne encore
