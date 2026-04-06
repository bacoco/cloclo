---
name: verify_before_writing
description: Toujours Grep/Glob le code existant AVANT de creer quoi que ce soit
type: feedback
---
Ne jamais supposer qu'un composant, hook, utility, ou pattern n'existe pas.
Avant de creer un nouveau fichier, faire minimum 3 recherches Grep/Glob.

**Why:** L'IA a tendance a creer du code duplique. Dans un audit, 5 "gaps"
declares comme manquants existaient tous deja dans le codebase.

**How to apply:** Avant chaque Write d'un nouveau fichier, faire :
1. Glob pour le nom du composant/module
2. Grep pour les fonctions/classes similaires
3. Grep pour les patterns existants dans le meme domaine
Si un equivalent existe, l'utiliser ou l'etendre. Ne creer que si rien n'existe.
