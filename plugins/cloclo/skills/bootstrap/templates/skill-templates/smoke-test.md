# Smoke Test — Template

## Frontmatter
```yaml
name: smoke-test-all
description: "Health check rapide de tous les services. Triggers: smoke test, health check, verifie que tout tourne, status"
```

## Step 1 — Status des containers
```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | sort
```

## Step 2 — Health checks paralleles

Lancer UN curl par service en parallele :
```bash
curl -s -o /dev/null -w "{{SERVICE_NAME}}|%{http_code}|%{time_total}s\n" --max-time 5 http://localhost:{{PORT}}/{{HEALTH_PATH}}
```

Services a verifier :
| Service | Port | Health Path |
|---------|------|-------------|
| {{SERVICE_1}} | {{PORT_1}} | {{HEALTH_1}} |
| {{SERVICE_2}} | {{PORT_2}} | {{HEALTH_2}} |

## Step 3 — Resume

Table markdown : Service | Status | Latence

Si tout OK : "Tous les services sont healthy."
Si echec : lister les services down + derniers logs.
