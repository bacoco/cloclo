---
name: test_after_change
description: Use when about to claim a change is done or fixed — run the matching verification first
type: feedback
---
Never claim "it's fixed" or "it's done" without running the verification.

**Why:** Code that "should work" often doesn't. Only measured verification counts.

**How to apply:** After each change:
- Python: `pytest tests/ -x` or `pytest tests/test_<module>.py`
- TypeScript: `pnpm build` or `pnpm typecheck`
- Docker: `curl -sf health_url` or `docker compose logs --tail=20`
- No tests? At minimum confirm the service starts.
