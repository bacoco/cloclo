# opensrc-sync — Template

## Frontmatter
```yaml
name: opensrc-sync
description: "Use when refreshing the vendored source of core dependencies to enrich AI context — only on explicit request. Triggers: update the docs, update sources, refresh deps, sync sources"
```

> This skill is OPTIONAL and opt-in. It requires Node.js 18+. Only create it if the
> project opted into opensrc during bootstrap Phase 6.

## Prerequisites (single source of truth for the install)

Install opensrc **user-locally** — no root, persistent path (never `/usr/local/bin`,
never `/tmp` which is wiped on reboot):

```bash
mkdir -p "$HOME/.local/opensrc" "$HOME/.local/bin"
git clone https://github.com/vercel-labs/opensrc.git "$HOME/.local/opensrc/opensrc-cli" 2>/dev/null || true
( cd "$HOME/.local/opensrc/opensrc-cli" && npm install && npm run build )

cat > "$HOME/.local/bin/opensrc-run" << 'SCRIPT'
#!/usr/bin/env node
import(process.env.HOME + '/.local/opensrc/opensrc-cli/dist/index.js').then(m => m.createProgram().parse());
SCRIPT
chmod +x "$HOME/.local/bin/opensrc-run"
# Requires ~/.local/bin on PATH (add it to your shell profile if it isn't).
```

## Phase 1 — Current state
```bash
opensrc-run list --json 2>/dev/null || echo '{"packages":[],"repos":[]}'
cat .claude/opensrc-tracked.json
```

## Phase 2 — Detect updates

Compare the versions in `opensrc/sources.json` against the installed versions.

| Situation | Action |
|-----------|--------|
| Not fetched yet | Fetch |
| Different version | Re-fetch |
| Same version | Skip |

## Phase 3 — Fetch/update
```bash
# npm packages
opensrc-run {{PKG_1}} {{PKG_2}} --modify true

# pypi packages
opensrc-run pypi:{{PKG_1}} pypi:{{PKG_2}} --modify true

# github repos
opensrc-run {{OWNER/REPO}} --modify true
```

## Phase 4 — Report
```
Sources updated:
  + [package] [version] (new)
  ~ [package] [old] → [new] (updated)
  = [package] [version] (already current)
```

## Rules
1. Never mass-fetch unprompted — only when the user asks.
2. No deletion without confirmation.
3. Always report — even if nothing changed.
