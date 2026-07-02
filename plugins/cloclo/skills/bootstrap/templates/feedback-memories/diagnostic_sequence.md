---
name: diagnostic_sequence
description: Use when a build, test, or deploy fails — follow this sequence before proposing a fix
type: feedback
---
When something fails, follow this sequence BEFORE proposing a fix:

**Why:** AI tends to propose fixes based on intuition rather than the real error.
Reading the full error avoids off-target fixes.

**How to apply:**
1. Read the FULL error (not just the last line).
2. Identify the FIRST error (later ones are often cascades).
3. Check whether the error is in changed code or existing code.
4. If Docker: `docker ps` then `docker logs --tail=50 <service>`.
5. If import/module: verify the package is installed.
6. NEVER say "it should work" after a failure.
