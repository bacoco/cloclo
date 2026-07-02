---
name: no_speculation
description: Use when writing a technical diagnosis — state facts or "I don't know yet", never speculation
type: feedback
---
Never use "probably", "maybe", "it might be", "it should" in a technical diagnosis.

**Why:** Speculative language gives a false impression of understanding and
delays the real diagnosis. The user prefers "I don't know yet, I'll check"
over a guess that turns out wrong.

**How to apply:**
- BAD: "The problem is probably in the auth middleware."
- GOOD: "I'll read the auth middleware to check." → [reads] → "The error is at line 42: the expired token isn't refreshed."
- BAD: "It should work now."
- GOOD: "I'll run the tests to check." → [runs] → "Tests pass / fail at X."
