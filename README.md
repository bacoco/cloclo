# CLOco — Claude + Codex Collaboration

Un plugin Claude Code qui insere des reviews Codex entre les phases de [SuperPowers](https://github.com/obra/superpowers).

## Comment ca marche

SuperPowers fait deja tout tres bien : brainstorming interactif avec serveur UX, mockups dans le browser, questions une par une, ecriture de spec, ecriture de plan d'implementation, execution par subagents, verification. CLOco ne touche a rien de ca.

Ce que CLOco ajoute : quand SuperPowers produit un artefact (spec, plan, ou code), CLOco le passe a Codex (GPT-5.4) qui le review independamment en explorant le vrai codebase. Les findings reviennent, tu reagis comme tu veux, et SuperPowers reprend la main pour integrer et continuer.

### Le processus concret

**1. Tu decris ce que tu veux faire.**

**2. SuperPowers demarre son brainstorming.**
Il te pose des questions une par une. Il demarre le serveur UX avec des mockups HTML dans le browser si c'est pertinent. Tu cliques tes choix, tu reponds, il explore le code existant. Il te propose 2-3 approches avec pros/cons. Tu choisis. Il ecrit la spec, la self-review, te la montre. Tu approuves.

Tout ca, c'est SuperPowers. CLOco n'intervient pas.

**3. CLOco envoie la spec a Codex.**
Codex lit la spec. Puis il explore ton codebase librement — 30, 50, 80 fichiers. Il verifie que chaque affirmation de la spec correspond a la realite du code. Il ecrit ses findings dans un fichier. Ca prend 2-10 minutes. C'est normal.

**4. Tu vois les findings de Codex et tu reagis.**
Exactement comme avec SuperPowers normalement. C'est pas un menu rigide. Tu dis ce que tu veux :
- "integre tout"
- "le point 2 est faux parce que..."
- "ignore ca, c'est pas pertinent"
- "creuse le point sur les types"
- ou n'importe quoi d'autre

**5. SuperPowers reprend la main.**
Il integre les findings de Codex et ton feedback. Il reecrit la spec. Puis il passe a l'ecriture du plan d'implementation (writing-plans) avec toute sa rigueur : TDD, tasks de 2-5 min, code complet, pas de placeholders.

**6. CLOco envoie le plan a Codex.**
Meme chose : Codex lit le plan, verifie que chaque fichier/fonction/ligne existe vraiment, identifie les risques. Findings dans un fichier. Tu reagis. SuperPowers reecrit le plan.

**7. SuperPowers execute le plan.**
Subagents frais par task, review spec compliance + code quality, gestion des blocages, model selection. Tout le moteur de superpowers:subagent-driven-development.

**8. CLOco envoie le code a Codex.**
Codex fait une vraie code review : git diff, lecture complete des fichiers modifies, verification des types, recherche de bugs. Findings. Tu reagis. SuperPowers corrige.

**9. SuperPowers verifie.**
verification-before-completion : pas de claims sans evidence, commandes de test executees, output affiche.

### En resume

```
SuperPowers brainstorme ──► spec
                              ↓ Codex review ↓ tu reagis ↓ SuperPowers reecrit
SuperPowers ecrit le plan ──► plan
                              ↓ Codex review ↓ tu reagis ↓ SuperPowers reecrit
SuperPowers execute ──► code
                              ↓ Codex review ↓ tu reagis ↓ SuperPowers corrige
SuperPowers verifie ──► done
```

## Prerequis

### SuperPowers (obligatoire — fait tout le travail)

Ajouter dans `~/.claude/settings.json` :

```json
{
  "enabledPlugins": {
    "superpowers@superpowers-marketplace": true
  },
  "extraKnownMarketplaces": {
    "superpowers-marketplace": {
      "source": {
        "source": "github",
        "repo": "obra/superpowers-marketplace"
      }
    }
  }
}
```

Redemarrer Claude Code.

### Codex (optionnel — le reviewer)

```bash
npm install -g @openai/codex
codex login
```

Puis ajouter dans `~/.claude/settings.json` :

```json
{
  "enabledPlugins": {
    "codex@openai-codex": true
  },
  "extraKnownMarketplaces": {
    "openai-codex": {
      "source": {
        "source": "github",
        "repo": "openai/codex-plugin-cc"
      }
    }
  }
}
```

Sans Codex, c'est juste SuperPowers normal — les reviews sont sautees.

## Installer CLOco

```bash
git clone https://github.com/bacoco/cloco.git ~/.claude/plugins/marketplaces/cloco
```

Ajouter dans `~/.claude/settings.json` :

```json
{
  "enabledPlugins": {
    "cloco@cloco": true
  }
}
```

Redemarrer Claude Code.

## Utilisation

```
/pipeline
```

Ou simplement decrire ce que tu veux construire.

## Fichiers de session

Tous les artefacts sont traces dans `docs/cloco-sessions/YYYY-MM-DD-<slug>/` :

```
01-spec.md                  ← SuperPowers brainstorming
02-codex-review-spec.md     ← Findings Codex sur la spec
03-spec-v2.md               ← SuperPowers reecrit apres feedback
04-plan.md                  ← SuperPowers writing-plans
05-codex-review-plan.md     ← Findings Codex sur le plan
06-plan-v2.md               ← SuperPowers reecrit apres feedback
07-codex-review-impl.md     ← Findings Codex sur le code
session.log                 ← Decisions + timestamps
```

## Licence

MIT
