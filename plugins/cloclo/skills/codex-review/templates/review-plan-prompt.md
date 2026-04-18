**OBJECTIF FINAL — lis en PREMIER, relis en DERNIER** :

Tu DOIS ecrire ta review complete au format markdown dans le fichier :
{{OUTPUT_PATH}}

Utilise ton tool d'ecriture fichier (Write pour Claude, file-write pour Codex). Ne termine JAMAIS avec "j'ai fini l'analyse" sans avoir ecrit ce fichier.

Un fichier {{OUTPUT_PATH}} vide ou manquant = echec total du review, peu importe la qualite de ton analyse interne. Le markdown qui reste dans ta reponse sans ecriture fichier est perdu — le caller lit UNIQUEMENT {{OUTPUT_PATH}}.

---

Voici un plan d'implementation : {{PLAN_PATH}}
Base sur la spec : {{SPEC_PATH}}

Tu es un reviewer senior. Fais ce que tu veux :
- Lis le plan en detail
- Verifie que chaque fichier/ligne/fonction mentionne existe reellement
- Verifie que le plan couvre bien tout ce que la spec demande
- Identifie les risques d'implementation, les edge cases oublies
- Verifie que les tasks sont dans le bon ordre (pas de dependances circulaires)

Format libre. Prends le temps qu'il faut.

---

**RAPPEL FINAL AVANT DE CONCLURE** :
- Le fichier {{OUTPUT_PATH}} doit exister et etre non-vide.
- Si tu ne l'as pas encore ecrit : appelle ton write tool MAINTENANT avec le contenu complet de la review.
- Ne te contente pas d'emettre le markdown en reponse — seule l'ecriture fichier compte.
