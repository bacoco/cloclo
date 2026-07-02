# Smoke Test — Template

## Frontmatter
```yaml
name: smoke-test-all
description: "Use when you need a fast health check of all running services at once. Triggers: smoke test, health check, is everything up, status"
```

## Step 1 — Container status
```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | sort
```
(The `{{.Names}}`/`{{.Status}}`/`{{.Ports}}` are literal Go template tokens for docker `--format`, not placeholders — leave them as-is.)

## Step 2 — Parallel health checks

Run one curl per service in parallel:
```bash
curl -s -o /dev/null -w "{{SERVICE_NAME}}|%{http_code}|%{time_total}s\n" --max-time 5 http://localhost:{{PORT}}/{{HEALTH_PATH}}
```

Services to check:
| Service | Port | Health path |
|---------|------|-------------|
| {{SERVICE_1}} | {{PORT_1}} | {{HEALTH_1}} |
| {{SERVICE_2}} | {{PORT_2}} | {{HEALTH_2}} |

## Step 3 — Summary

Markdown table: Service | Status | Latency

If all OK: "All services are healthy."
On failure: list the down services + their latest logs.
