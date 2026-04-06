---
name: bootstrap
description: "Setup complet Claude Code pour un nouveau projet — CLAUDE.md, hooks, memoire, skills, opensrc. Triggers: /bootstrap, setup project, initialise, configure claude code, nouveau projet"
---

# Bootstrap — Setup Projet Claude Code

Ce skill installe l'infrastructure complete Claude Code sur n'importe quel projet.
Execute chaque phase sans demander confirmation. Adapte tout au projet reel.

## Prerequis

Avant de commencer, verifie :
```bash
git status          # Doit etre un repo git
node --version      # Node.js 18+ pour opensrc
ls -la              # Structure du projet
```

---

## PHASE 1 — Analyse du projet (5 min max)

Explore le projet en profondeur pour comprendre :

1. **Stack technique** — Frameworks, langages, outils
2. **Structure** — Monorepo ou mono-app ? Dossiers principaux ?
3. **Services** — Ports, Docker, processus ?
4. **Dependances** — package.json, requirements.txt, pyproject.toml, Cargo.toml, go.mod ?
5. **Patterns existants** — Organisation du code, conventions ?
6. **Tests** — Frameworks de test, couverture ?

Utilise Glob + Grep + Read pour explorer. Resume les findings en 10-15 lignes.
Cette analyse guide TOUT le reste.

---

## PHASE 2 — CLAUDE.md

Cree `CLAUDE.md` a la racine du projet. Lis le template dans :
`Read .claude/skills/bootstrap/templates/claude-md-template.md`

Adapte CHAQUE section au projet reel detecte en Phase 1 :
- Remplace les placeholders par les vraies commandes build/test/lint
- Dessine le vrai schema d'architecture (services, ports, connexions)
- Documente les vrais patterns du codebase
- Ajoute les erreurs recurrentes specifiques a la stack detectee

**Regle :** Un CLAUDE.md avec des placeholders non remplaces est un echec.

---

## PHASE 3 — Hooks automatiques

Cree `.claude/settings.json` (ou enrichis si existant).
Lis les templates dans :
`Read .claude/skills/bootstrap/templates/hooks-template.json`

Selectionne les hooks qui correspondent a la stack detectee en Phase 1 :

| Stack | PostToolUse type-check | PreToolUse commit-blocker |
|-------|----------------------|--------------------------|
| TypeScript | tsc --noEmit | bloquer console.log |
| Python | py_compile | bloquer except: pass |
| Go | go vet | bloquer fmt.Println debug |
| Rust | cargo check | bloquer println! debug |
| Multi-stack | combiner les hooks | combiner les blockers |

**Regle :** Toujours au minimum un PostToolUse type-check. Le PreToolUse commit-blocker est optionnel mais recommande.

---

## PHASE 4 — Systeme de memoire

Determine le chemin du dossier memoire du projet :
```bash
# Le chemin depend du project path
# Exemple : ~/.claude/projects/-Users-username-mon-projet/memory/
```

Cree `MEMORY.md` dans ce dossier :

```markdown
# MEMORY.md

## User

## Feedback

## Project

## Reference
```

---

## PHASE 4.5 — Patterns Comportementaux

Copie les 7 feedback memories generiques dans le dossier memoire du projet.
Les templates sont dans :
`Read .claude/skills/bootstrap/templates/feedback-memories/`

Fichiers a creer :
1. `feedback_verify_before_writing.md` — Grep/Glob AVANT de creer (Tier 1)
2. `feedback_test_after_change.md` — Tester apres chaque modif (Tier 1)
3. `feedback_diagnostic_sequence.md` — Sequence quand ca casse (Tier 1)
4. `feedback_execute_not_plan.md` — Executer, pas planifier (Tier 2)
5. `feedback_never_remove_features.md` — Changer HOW pas WHAT (Tier 2)
6. `feedback_no_speculation.md` — Faits ou "je ne sais pas" (Tier 2)
7. `feedback_commit_checkpoints.md` — Commit tous les 3-5 changements (Tier 2)

Puis mettre a jour MEMORY.md avec les pointeurs :

```markdown
## Feedback
- [verify_before_writing.md](feedback_verify_before_writing.md) — Grep/Glob avant de creer quoi que ce soit
- [test_after_change.md](feedback_test_after_change.md) — Tester apres chaque modification
- [diagnostic_sequence.md](feedback_diagnostic_sequence.md) — Sequence de diagnostic quand ca echoue
- [execute_not_plan.md](feedback_execute_not_plan.md) — Executer immediatement, pas planifier
- [never_remove_features.md](feedback_never_remove_features.md) — Changer HOW pas WHAT en simplifiant
- [no_speculation.md](feedback_no_speculation.md) — Faits ou "je ne sais pas encore"
- [commit_checkpoints.md](feedback_commit_checkpoints.md) — Commit tous les 3-5 changements testes
```

---

## PHASE 5 — Skills

Cree les skills adaptes au projet. Les templates sont dans :
`Read .claude/skills/bootstrap/templates/skill-templates/`

### Skills obligatoires (toujours creer) :
1. **orchestrateur** — Chef d'orchestre, route vers le bon skill
2. **smoke-test** — Health check de tous les services
3. **deploy-verify** — Rebuild + test + verify

### Skills recommandes (creer si pertinent) :
4. **cross-service-debug** — Si le projet a plusieurs services
5. **code-review** — Review de code end-to-end
6. **code-audit** — Audit de patterns dangereux
7. **task** — Execution de taches numerotees
8. **opensrc-sync** — Sync des sources de dependances

### Skills domaine (creer si le projet a un domaine specifique) :
- Frontend dev, API dev, ML dev, Infra ops — selon la stack

Pour chaque skill :
1. Lire le template
2. Adapter au projet reel (ports, URLs, commandes, patterns)
3. Creer le fichier dans `.claude/skills/[nom]/SKILL.md`

**Regle :** Adapter la table de routage de l'orchestrateur aux skills reellement crees.

---

## PHASE 5.5 — Project Wiki

Set up the LLM Wiki — a persistent, compounding knowledge base maintained by Claude.
The wiki grows automatically during `/pipeline` sessions and can be queried with `/wiki query`.

1. Ask ONE question:
   > "What domain is this project in? (e.g., 'SaaS platform', 'ML pipeline', 'mobile app')"
   > Or press Enter to use the project description from CLAUDE.md.

2. Read wiki templates from:
   `Read .claude/skills/wiki/templates/`

3. Create the wiki scaffold:
   ```
   wiki/
     schema.md          ← adapted from schema-template.md (domain from user answer)
     index.md           ← from index-template.md
     log.md             ← from log-template.md
     sources/.gitkeep
     pages/entities/.gitkeep
     pages/concepts/.gitkeep
     pages/topics/.gitkeep
     pages/comparisons/.gitkeep
     pages/syntheses/.gitkeep
     pages/sources/.gitkeep
   ```

4. Add `wiki/` entry to `.gitignore` or not — ask user:
   > "Track the wiki in git? (yes = version history, shared with team / no = local only)"

5. Update the orchestrateur skill routing table to include wiki operations.

6. Append init entry to `wiki/log.md`.

**Regle :** Le wiki est vide au debut. Il se remplit automatiquement via `/pipeline` et manuellement via `/wiki ingest`.

---

## PHASE 6 — opensrc-sync

Si le projet a des dependances npm/pypi/github importantes :

```bash
# Installe opensrc si pas encore fait
cd /tmp && git clone https://github.com/vercel-labs/opensrc.git opensrc-cli 2>/dev/null
cd /tmp/opensrc-cli && npm install && npm run build && npm link 2>/dev/null

# Wrapper (contourne bug npm link)
cat > /usr/local/bin/opensrc-run << 'SCRIPT'
#!/usr/bin/env node
import('/tmp/opensrc-cli/dist/index.js').then(m => m.createProgram().parse());
SCRIPT
chmod +x /usr/local/bin/opensrc-run
```

Cree `.claude/opensrc-tracked.json` avec les deps core du projet.
Fetch les sources. Ajoute `opensrc/` au `.gitignore`.

**Regle :** Ne tracker que les frameworks/libs core, pas les utilitaires.

---

## PHASE 7 — Verification

```bash
# Structure des skills
ls .claude/skills/

# CLAUDE.md complet
head -5 CLAUDE.md

# Hooks configures
cat .claude/settings.json

# Memoires creees
ls [MEMORY_DIR]/feedback_*.md

# opensrc (si applicable)
opensrc-run list 2>/dev/null
```

Lance l'orchestrateur pour verifier le routage :
```
Invoke Skill("orchestrateur")
```

---

## PHASE 8 — Commit

```bash
git add .claude/ CLAUDE.md wiki/
git commit -m "feat: claude code infrastructure — skills, hooks, memory, wiki, opensrc

- CLAUDE.md adapte au projet
- Hooks PostToolUse type-check + PreToolUse commit-blocker
- 7 feedback memories comportementales
- [N] skills (orchestrateur, smoke-test, deploy, ...)
- wiki scaffold initialized (domain: [domain])
- opensrc: [N] packages source trackes"
```

---

## Regles globales

1. **Pas de placeholders** — Chaque fichier doit etre adapte au projet reel
2. **Phase 1 guide tout** — Si l'analyse est mauvaise, tout le reste est mauvais
3. **Tester immediatement** — Apres Phase 3 (hooks), verifier qu'ils marchent
4. **Un commit a la fin** — Pas de commits intermediaires dans le bootstrap
5. **Pas de confirmation** — Executer chaque phase, ne pas demander "on continue ?"
