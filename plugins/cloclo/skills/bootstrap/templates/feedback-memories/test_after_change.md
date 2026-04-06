---
name: test_after_change
description: Apres chaque modification, lancer les tests correspondants avant de claim done
type: feedback
---
Jamais claim "c'est fixe" ou "c'est fait" sans avoir execute la verification.

**Why:** Le code qui "devrait marcher" ne marche pas dans 30% des cas.
Seule la verification mesuree compte.

**How to apply:** Apres chaque modif :
- Python : `pytest tests/ -x` ou `pytest tests/test_<module>.py`
- TypeScript : `pnpm build` ou `pnpm typecheck`
- Docker : `curl -sf health_url` ou `docker compose logs --tail=20`
- Si pas de tests : au minimum verifier que le service demarre
