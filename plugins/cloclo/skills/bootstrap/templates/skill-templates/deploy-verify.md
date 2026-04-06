# Deploy & Verify — Template

## Frontmatter
```yaml
name: deploy-and-verify
description: "Rebuild + test + verify apres changements. Triggers: deploy, rebuild, verify, test after fix"
```

## 1. Identifier + Rebuild

| Fichier modifie | Commande rebuild | Health URL |
|----------------|-----------------|------------|
| {{APP_1}}/ | {{BUILD_CMD_1}} | {{HEALTH_URL_1}} |
| {{APP_2}}/ | {{BUILD_CMD_2}} | {{HEALTH_URL_2}} |

## 2. Health Check

Poll `curl -sf {{HEALTH_URL}}` (max 30s, 5s intervals).
Sur echec : lire les logs.

## 3. Tests

| Service | Commande test |
|---------|--------------|
| {{APP_1}} | {{TEST_CMD_1}} |
| {{APP_2}} | {{TEST_CMD_2}} |

## 4. Rapport
```
Deploy verifie: [service] rebuilt + healthy + tests pass
```

## Regles
- JAMAIS demander "should I rebuild?" — juste le faire
- JAMAIS claim done avant que le health check passe
