# Cross-Service Debug — Template

## Frontmatter
```yaml
name: cross-service-debug
description: "Use when an error crosses service boundaries and you need to trace it to the root service. Triggers: debug, trace error, 500 error, timeout"
```

## Service chain
```
{{FRONTEND}} → {{API_GATEWAY}} → {{BACKEND_1}} → {{BACKEND_2}} → {{DB_CACHE}}
```

## Workflow

1. **Identify the symptom** — where is the error visible? (frontend, logs, monitoring)
2. **Trace upstream** — read the logs of the service closest to the error, then walk up the chain.
3. **Find the root cause** — which service raises the original error?
4. **Fix** — correct it in the right service.
5. **Verify** — re-test the full chain.

## Common error patterns

| Symptom | Likely cause |
|---------|--------------|
| 502 Bad Gateway | Backend service down or timeout |
| 200 but HTML content | Proxy returns a 404 page with status 200 |
| Timeout cascade | Slow service blocking the whole chain |
| JSON parse error | Non-JSON response (HTML, plain text) |
