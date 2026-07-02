# Code Audit — Template

## Frontmatter
```yaml
name: code-audit
description: "Use when scanning the codebase for dangerous patterns and code smells before a release or review. Triggers: audit, quality, check the code, scan"
```

## Checks by stack

### TypeScript/React
- [ ] Zustand/Redux selectors with `|| []` (infinite re-render loop)
- [ ] Unguarded API responses (`response.data.field` without a check)
- [ ] `useEffect` with no deps array or unstable deps
- [ ] `any` type that hides errors
- [ ] Hydration mismatches (SSR vs client)

### Python/FastAPI
- [ ] `except: pass` or `except Exception: pass` (swallowed exceptions)
- [ ] `list[0]` without checking length (IndexError)
- [ ] Direct file access instead of the storage abstraction
- [ ] `response_model` classes defined after the route (NameError at startup)
- [ ] SQL/Cypher injection (f-strings in queries)

### Go
- [ ] Unchecked errors (`err` ignored)
- [ ] Goroutine leaks (no context cancel)
- [ ] Race conditions (concurrent access without a mutex)

### General
- [ ] Hardcoded secrets in code
- [ ] Hardcoded URLs/ports instead of env vars
- [ ] Files > 500 lines without a good reason
- [ ] Functions > 50 lines

## Report
Table: File:line | Pattern | Severity | Fix
Sort by severity (High → Medium → Low).
