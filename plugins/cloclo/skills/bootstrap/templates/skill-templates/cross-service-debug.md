# Cross-Service Debug — Template

## Frontmatter
```yaml
name: cross-service-debug
description: "Trace les erreurs cross-service. Triggers: debug, trace erreur, 500 error, timeout"
```

## Chaine de services
```
{{FRONTEND}} → {{API_GATEWAY}} → {{BACKEND_1}} → {{BACKEND_2}} → {{DB_CACHE}}
```

## Workflow

1. **Identifier le symptome** — Ou est l'erreur visible ? (frontend, logs, monitoring)
2. **Tracer en remontant** — Lire les logs du service le plus proche de l'erreur, puis remonter la chaine
3. **Identifier la root cause** — Quel service genere l'erreur originale ?
4. **Fixer** — Corriger dans le bon service
5. **Verifier** — Re-tester la chaine complete

## Patterns d'erreur courants

| Symptome | Cause probable |
|----------|---------------|
| 502 Bad Gateway | Service backend down ou timeout |
| 200 mais contenu HTML | Proxy retourne page 404 avec status 200 |
| Timeout cascade | Service lent qui bloque toute la chaine |
| JSON parse error | Reponse non-JSON (HTML, texte brut) |
