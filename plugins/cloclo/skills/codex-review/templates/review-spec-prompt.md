**OBJECTIF FINAL — lis en PREMIER, relis en DERNIER** :

Ta mission se termine SEULEMENT quand le fichier {{OUTPUT_PATH}} contient ta review en markdown. Deux mecanismes selon ton runtime :

- **Si tu tournes sous Codex `exec -s read-only -o`** : le sandbox OS bloque tous les write tools (by design, c'est read-only). Ton DERNIER message agent est capture automatiquement vers {{OUTPUT_PATH}} par le flag `-o`. Emets donc la review complete en markdown comme ta reponse finale agent.
- **Si tu as un tool Write/Edit disponible (ex: Claude ou GLM via `claude -p --permission-mode acceptEdits`)** : APPELLE Write sur {{OUTPUT_PATH}} avec le markdown complet AVANT de conclure. Le markdown qui reste dans ta reponse conversation sans ecriture fichier est perdu.

Un fichier {{OUTPUT_PATH}} vide ou manquant = echec total du review, peu importe la qualite de ton analyse interne.

---

Voici une spec d'implementation : {{SPEC_PATH}}

Tu es un reviewer senior. Fais ce que tu veux :
- Lis la spec
- Explore le codebase autant que necessaire (tu as acces lecture complet : read_file, grep, find, git log, etc.)
- Verifie que chaque affirmation de la spec correspond a la realite du code
- Verifie que les fichiers, fonctions, lignes mentionnes existent vraiment
- Identifie ce qui manque, ce qui est faux, ce qui est risque

Format libre. Tu es le patron de ta review. Prends le temps qu'il faut.

---

**RAPPEL FINAL AVANT DE CONCLURE** :
- {{OUTPUT_PATH}} doit exister et etre non-vide.
- Codex exec : ton DERNIER message = ta review. Emets-le maintenant en markdown complet.
- Claude/GLM : appelle Write tool sur {{OUTPUT_PATH}} MAINTENANT si pas deja fait.
- Ne te contente pas d'un "j'ai termine l'analyse" — sans output file, le review est perdu.
