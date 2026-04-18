# Retry Ceilings & Maturity Levels

## Bounded Retries

Every phase that can fail has a hard ceiling. Prevents infinite loops and
runaway token spend.

| Phase                                 | Max retries | On exhaustion                                       |
|---------------------------------------|-------------|-----------------------------------------------------|
| Phase 2 (Codex review spec)           | 2           | Skip review, warn user                              |
| Phase 4 (Codex review plan)           | 2           | Skip review, warn user                              |
| Phase 5 (Subagent execution)          | 3 per task  | Mark task BLOCKED, continue others                  |
| Phase 6 (Codex review impl)           | 2           | Skip review, warn user                              |
| Phase 6.5 (CodeRabbit review)         | 2           | Skip review, warn user — does NOT block pipeline    |
| Phase 7 (Verification)                | 3           | FAIL pipeline, require user intervention            |
| Phase 7.5 (Visual verification)       | 2 per page  | Log failure, continue to next page                  |

When a retry triggers:
1. Log: `[timestamp] Phase {N} retry {attempt}/{max}: {reason}`
2. If exhausted: `[timestamp] Phase {N} EXHAUSTED after {max} retries — {action}`
3. Never retry silently — always print what failed and what happens next.

## Maturity Levels

A single `maturity` field controls strictness. Set in `pipeline.config.md` or
auto-detected.

| Level  | When                          | Gates                                       | Parallelism | Review depth                                  |
|--------|-------------------------------|---------------------------------------------|-------------|-----------------------------------------------|
| `spike`| Exploring, prototyping        | Soft (user can skip freely)                 | 1 agent     | Codex optional, CodeRabbit optional           |
| `dev`  | Active dev (default)          | Standard (A-E decisions)                    | Up to 3     | Codex all phases, CodeRabbit Phase 6.5        |
| `ship` | Pre-release, production       | Hard (no skip without documented reason)    | Up to 5     | Codex + CodeRabbit + adversarial triple-perspective |

## Auto-detection

If no maturity set:
- No tests, no CI → `spike`
- Tests exist, active branch → `dev`
- CI passing, release branch or tag → `ship`

Maturity is logged in `session.log` and passed to all skill invocations.
SuperPowers skills adapt depth accordingly (e.g., brainstorming in spike mode
asks fewer questions).
