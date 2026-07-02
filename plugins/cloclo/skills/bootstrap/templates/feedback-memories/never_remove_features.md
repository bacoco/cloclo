---
name: never_remove_features
description: Use when simplifying, refactoring, or rewriting code — change the HOW, never the WHAT
type: feedback
---
When simplifying, refactoring, or rewriting code, NEVER drop existing
behavior unless the user explicitly asked for it.

**Why:** AI tends to "simplify" by removing edge-case features it deems
non-essential. The user discovers the regressions later.

**How to apply:**
1. BEFORE rewriting: list every existing behavior.
2. DURING: change the implementation, not the features.
3. AFTER: verify each behavior from the list still works.
