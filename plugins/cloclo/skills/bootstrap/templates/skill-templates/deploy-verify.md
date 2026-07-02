# Deploy & Verify — Template

## Frontmatter
```yaml
name: deploy-and-verify
description: "Use when files changed and you need to rebuild, health-check, and test before claiming done. Triggers: deploy, rebuild, verify, test after fix"
```

## 1. Identify + rebuild

| Changed file | Rebuild command | Health URL |
|--------------|-----------------|------------|
| {{APP_1}}/ | {{BUILD_CMD_1}} | {{HEALTH_URL_1}} |
| {{APP_2}}/ | {{BUILD_CMD_2}} | {{HEALTH_URL_2}} |

## 2. Health check

Poll `curl -sf {{HEALTH_URL}}` (max 30s, 5s intervals).
On failure: read the logs.

## 3. Tests

| Service | Test command |
|---------|--------------|
| {{APP_1}} | {{TEST_CMD_1}} |
| {{APP_2}} | {{TEST_CMD_2}} |

## 4. Report
```
Deploy verified: [service] rebuilt + healthy + tests pass
```

## Rules
- NEVER ask "should I rebuild?" — just do it.
- NEVER claim done before the health check passes.
