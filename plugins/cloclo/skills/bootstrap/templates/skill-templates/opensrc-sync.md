# opensrc-sync — Template

## Frontmatter
```yaml
name: opensrc-sync
description: "Synchronise le code source des dependances pour enrichir le contexte IA. Triggers: met a jour la doc, update sources, refresh deps, synchronise les sources, maj deps"
```

## Prerequis

Si opensrc n'est pas installe :
```bash
cd /tmp && git clone https://github.com/vercel-labs/opensrc.git opensrc-cli
cd opensrc-cli && npm install && npm run build && npm link
```

Si le wrapper n'existe pas :
```bash
cat > /usr/local/bin/opensrc-run << 'SCRIPT'
#!/usr/bin/env node
import('/tmp/opensrc-cli/dist/index.js').then(m => m.createProgram().parse());
SCRIPT
chmod +x /usr/local/bin/opensrc-run
```

## Phase 1 — Etat actuel
```bash
opensrc-run list --json 2>/dev/null || echo '{"packages":[],"repos":[]}'
cat .claude/opensrc-tracked.json
```

## Phase 2 — Detecter les mises a jour

Comparer les versions dans `opensrc/sources.json` avec les versions installees.

| Situation | Action |
|-----------|--------|
| Pas encore fetche | Fetch |
| Version differente | Re-fetch |
| Version identique | Skip |

## Phase 3 — Fetch/Update
```bash
# npm packages
opensrc-run {{PKG_1}} {{PKG_2}} --modify true

# pypi packages
opensrc-run pypi:{{PKG_1}} pypi:{{PKG_2}} --modify true

# github repos
opensrc-run {{OWNER/REPO}} --modify true
```

## Phase 4 — Rapport
```
Sources mises a jour :
  + [package] [version] (nouveau)
  ~ [package] [old] → [new] (mis a jour)
  = [package] [version] (deja a jour)
```

## Regles
1. Jamais de fetch massif non demande — QUE quand le user le demande
2. Pas de suppression sans confirmation
3. Rapport toujours — meme si rien a faire
