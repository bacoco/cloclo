# Behavioral Patterns — Ce qui marche vraiment

Guide de reference pour optimiser la collaboration humain-IA en developpement.
Base sur l'experience reelle (excenia-hub, 15+ feedback memories, 800+ sessions)
et la recherche sur les assistants de code IA.

---

## La hierarchie d'impact

### Tier 1 — Impact maximal : Boucles de verification

**Principe :** Les patterns qui creent un cycle ecris → teste → corrige
produisent 2-3x d'amelioration qualite (source: recherche agentmemory,
MemCoder, retours communaute Claude Code/Cursor).

**Exemples concrets :**
- Un hook PostToolUse qui lance `tsc --noEmit` apres chaque edit TS
- Une memoire qui dit "lance pytest apres chaque modif Python"
- Un PreToolUse qui bloque les commits contenant des anti-patterns

**Pourquoi ca marche :** L'IA voit le resultat de son action immediatement.
Si `tsc` echoue, elle corrige tout de suite au lieu de passer au fichier suivant.
C'est la difference entre "confiance aveugle" et "verification factuelle".

**Patterns Tier 1 actuels :**
1. `verify_before_writing` — Grep/Glob AVANT de creer
2. `test_after_change` — Tester APRES chaque modif
3. `diagnostic_sequence` — Lire l'erreur COMPLETE quand ca casse

---

### Tier 2 — Impact eleve : Garde-fous comportementaux

**Principe :** Les regles "ne fais JAMAIS X parce que Y" sont les instructions
les plus suivies par l'IA, surtout quand le WHY est concret (incident passe,
crash en prod, perte de travail).

**Exemples concrets :**
- "Ne JAMAIS supprimer une feature en simplifiant" → Pourquoi : regression en prod
- "Ne JAMAIS planifier au lieu d'executer" → Pourquoi : frustration user, temps perdu
- "Ne JAMAIS speculate dans un diagnostic" → Pourquoi : fausse confiance, mauvais fix

**Pourquoi ca marche :** Le format "JAMAIS X parce que Y" est sans ambiguite.
L'IA ne peut pas rationaliser une exception quand le WHY est clair.

**Patterns Tier 2 actuels :**
4. `execute_not_plan` — Faire, pas planifier
5. `never_remove_features` — HOW pas WHAT
6. `no_speculation` — Faits ou "je ne sais pas"
7. `commit_checkpoints` — Commit reguliers

---

### Tier 3 — Enforcement mecanique > Instruction passive

**Principe :** Un hook qui BLOQUE automatiquement est 10x plus efficace
qu'une regle ecrite. L'IA peut "oublier" une instruction dans CLAUDE.md.
Elle ne peut pas ignorer un hook qui retourne exit code 1.

**Le gold standard :**
```
CLAUDE.md dit "pas de || [] dans les selectors"     → Suivie ~80% du temps
Hook PreToolUse qui bloque le commit si || [] existe → Suivie 100% du temps
```

**Recommandation :** Pour chaque regle critique, creer a la fois :
1. Une memoire feedback (pour l'intention + le WHY)
2. Un hook mecanique (pour l'enforcement)

---

## Anti-patterns memoire — Ce qu'il NE FAUT PAS stocker

### Ne pas stocker en memoire :
| Type | Pourquoi | Ou mettre |
|------|----------|-----------|
| Mots de passe / credentials | Doublon avec CLAUDE.md "Test Credentials" | CLAUDE.md |
| Config infra machine-specific | Change trop souvent, pas generique | CLAUDE.md section "Infrastructure" |
| La meme regle 3 fois | Bruit, dilue le signal | Consolider en 1 seul fichier |
| Ce qui peut etre derive du code/git | Stale rapidement | Lire le code/git a chaque session |
| Architecture, file paths, patterns | Le code est la source de verite | CLAUDE.md ou rien |

### Ne stocker en memoire QUE :
- Les corrections comportementales (feedback)
- Le contexte non-deductible du code (decisions, motivations, deadlines)
- Le profil user (role, preferences, style de communication)
- Les pointeurs vers des ressources externes

---

## Adapter les patterns a un nouveau projet

### Etape 1 — Les 7 generiques (bootstrap)
Les 7 feedback memories du bootstrap fonctionnent sur TOUT projet.
Elles sont la fondation. Ne pas les modifier sauf si le projet a un bon motif.

### Etape 2 — Ajouter 2-3 patterns specifiques
Apres 5-10 sessions, l'IA et le user auront accumule des corrections specifiques :
- Framework X a un piege specifique → feedback memory
- Le projet a un pattern architectural unique → CLAUDE.md
- Un bug a coute 2h parce que l'IA a fait Y → feedback "ne JAMAIS Y"

### Etape 3 — Pruner
Apres 20+ sessions, certaines memoires deviennent obsoletes :
- Le bug a ete fixe definitivement → la memoire n'a plus de raison d'etre
- Le projet a change de stack → les regles specifiques sont caduques
- L'IA a "internalise" un pattern → la memoire est redondante

**Regle :** Si une memoire n'a pas ete utile en 10 sessions, la supprimer.

---

## Metriques de reference

| Metrique | Bon | Excellent |
|----------|-----|-----------|
| Feedback memories | 5-10 | 7-12 |
| CLAUDE.md longueur | < 200 lignes | < 150 lignes |
| Hooks mecaniques | 1-2 | 3-4 |
| Ratio Tier 1-2 / Tier 3-4 | > 60% | > 80% |
| Token cost memoire/session | < 8K | < 5K |

---

## Sources

- Experience excenia-hub (15 feedback memories, 800+ sessions, 10+ PRs de remediation)
- [Claude Code Memory Docs](https://code.claude.com/docs/en/memory)
- [Writing a good CLAUDE.md](https://www.builder.io/blog/claude-md-guide)
- [Best Practices for Claude Code](https://code.claude.com/docs/en/best-practices)
- [Persistent memory for AI coding agents](https://dev.to/ohugonnot/persistent-memory-in-claude-code-whats-worth-keeping-54ck)
- [MemCoder: structured memory for AI coding agents](https://arxiv.org/html/2603.13258)
- [agentmemory: 92% token reduction](https://github.com/rohitg00/agentmemory)
- [Addy Osmani: LLM coding workflow 2026](https://addyosmani.com/blog/ai-coding-workflow/)
- [Cursor Rules best practices](https://trigger.dev/blog/cursor-rules)
- [Martin Fowler: Harness engineering for coding agents](https://martinfowler.com/articles/harness-engineering.html)
