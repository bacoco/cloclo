**OBJECTIF FINAL — lis en PREMIER, relis en DERNIER** :

Ta mission se termine SEULEMENT quand le fichier {{OUTPUT_PATH}} contient ta review en markdown. Deux mecanismes selon ton runtime :

- **Si tu tournes sous Codex `exec -s read-only -o`** : le sandbox OS bloque tous les write tools (by design, c'est read-only). Ton DERNIER message agent est capture automatiquement vers {{OUTPUT_PATH}} par le flag `-o`. Emets donc la review complete en markdown comme ta reponse finale agent.
- **Si tu as un tool Write/Edit disponible (ex: Claude ou GLM via `claude -p --permission-mode acceptEdits`)** : APPELLE Write sur {{OUTPUT_PATH}} avec le markdown complet AVANT de conclure. Le markdown qui reste dans ta reponse conversation sans ecriture fichier est perdu.

Un fichier {{OUTPUT_PATH}} vide ou manquant = echec total du review, peu importe la qualite de ton analyse interne.

---

L'implementation suivante vient d'etre realisee.

Spec : {{SPEC_PATH}}
Plan : {{PLAN_PATH}}
Commits : {{COMMIT_LIST}}

Tu es un reviewer senior. Review le code qui a ete ecrit :
- `git diff {{BASE_REF}}..HEAD` pour voir tout ce qui a change
- Lis chaque fichier modifie en entier (pas juste le diff) — tu as acces lecture complet au repo
- Explore le codebase autant que necessaire pour comprendre le contexte (callsites, tests existants, types)
- Verifie que l'implementation correspond a la spec
- Verifie que l'implementation suit le plan
- Cherche les bugs, les edge cases, les regressions
- Lance les commandes de verification appropriees au projet (typecheck, tests)

C'est une vraie code review. Prends le temps qu'il faut. Sois exhaustif. Signale tout ce qui te derange.

---

**RAPPEL FINAL AVANT DE CONCLURE** :
- {{OUTPUT_PATH}} doit exister et etre non-vide.
- Codex exec : ton DERNIER message = ta review. Emets-le maintenant en markdown complet.
- Claude/GLM : appelle Write tool sur {{OUTPUT_PATH}} MAINTENANT si pas deja fait.
- Ne te contente pas d'un "j'ai termine l'analyse" — sans output file, le review est perdu.
