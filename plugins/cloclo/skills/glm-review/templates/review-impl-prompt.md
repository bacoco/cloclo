**OBJECTIF FINAL — lis en PREMIER, relis en DERNIER** :

Tu DOIS ecrire ta review complete au format markdown dans le fichier :
{{OUTPUT_PATH}}

Utilise ton tool d'ecriture fichier (Write pour Claude, file-write pour Codex). Ne termine JAMAIS avec "j'ai fini l'analyse" sans avoir ecrit ce fichier.

Un fichier {{OUTPUT_PATH}} vide ou manquant = echec total du review, peu importe la qualite de ton analyse interne. Le markdown qui reste dans ta reponse sans ecriture fichier est perdu — le caller lit UNIQUEMENT {{OUTPUT_PATH}}.

---

L'implementation suivante vient d'etre realisee.

Spec : {{SPEC_PATH}}
Plan : {{PLAN_PATH}}
Commits : {{COMMIT_LIST}}

Tu es un reviewer senior. Review le code qui a ete ecrit :
- `git diff {{BASE_REF}}..HEAD` pour voir tout ce qui a change
- Lis chaque fichier modifie en entier (pas juste le diff)
- Verifie que l'implementation correspond a la spec
- Verifie que l'implementation suit le plan
- Cherche les bugs, les edge cases, les regressions
- Lance les commandes de verification appropriees au projet

C'est une vraie code review. Prends le temps qu'il faut. Sois exhaustif. Signale tout ce qui te derange.

---

**RAPPEL FINAL AVANT DE CONCLURE** :
- Le fichier {{OUTPUT_PATH}} doit exister et etre non-vide.
- Si tu ne l'as pas encore ecrit : appelle ton write tool MAINTENANT avec le contenu complet de la review.
- Ne te contente pas d'emettre le markdown en reponse — seule l'ecriture fichier compte.
