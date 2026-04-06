# Code Audit — Template

## Frontmatter
```yaml
name: code-audit
description: "Audit de patterns dangereux dans le code. Triggers: audit, qualite, verifie le code, scan"
```

## Checks par stack

### TypeScript/React
- [ ] Selecteurs Zustand/Redux avec `|| []` (boucle infinie de re-render)
- [ ] Reponses API non gardees (`response.data.field` sans verification)
- [ ] `useEffect` sans deps array ou avec deps instables
- [ ] `any` type qui masque des erreurs
- [ ] Hydration mismatches (SSR vs client)

### Python/FastAPI
- [ ] `except: pass` ou `except Exception: pass` (exceptions avalees)
- [ ] `list[0]` sans verifier la longueur (IndexError)
- [ ] Acces fichier direct au lieu du storage abstrait
- [ ] Classes response_model definies apres la route (NameError au startup)
- [ ] SQL/Cypher injection (f-strings dans les queries)

### Go
- [ ] Erreurs non verifiees (`err` ignore)
- [ ] Goroutine leaks (pas de context.Cancel)
- [ ] Race conditions (acces concurrent sans mutex)

### General
- [ ] Secrets en dur dans le code
- [ ] URLs/ports hardcodes au lieu de variables d'env
- [ ] Fichiers > 500 lignes sans bonne raison
- [ ] Fonctions > 50 lignes

## Rapport
Table : Fichier:ligne | Pattern | Severite | Fix
Trier par severite (High → Medium → Low).
