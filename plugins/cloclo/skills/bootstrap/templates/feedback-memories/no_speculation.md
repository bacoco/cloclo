---
name: no_speculation
description: Pas de langage speculatif dans les diagnostics — faits ou "je ne sais pas"
type: feedback
---
Ne jamais utiliser "probablement", "peut-etre", "il se pourrait que",
"ca devrait" dans un diagnostic technique.

**Why:** Le langage speculatif donne une fausse impression de comprehension
et retarde le vrai diagnostic. Le user prefere "je ne sais pas encore,
je vais verifier" a une speculation qui se revele fausse.

**How to apply:**
- BAD: "Le probleme est probablement dans le middleware d'auth"
- GOOD: "Je vais lire le middleware d'auth pour verifier" → [lit le code] → "L'erreur est ligne 42 : le token expire n'est pas rafraichi"
- BAD: "Ca devrait marcher maintenant"
- GOOD: "Je lance les tests pour verifier" → [lance] → "Tests passent / echouent a X"
