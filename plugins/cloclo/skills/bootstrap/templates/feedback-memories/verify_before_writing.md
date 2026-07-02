---
name: verify_before_writing
description: Use when about to create any new file, component, hook, or utility — Grep/Glob the existing code first
type: feedback
---
Never assume a component, hook, utility, or pattern does not exist.
Before creating a new file, do at least 3 Grep/Glob searches.

**Why:** AI tends to create duplicate code. It is common in audits for "missing"
functionality to already exist somewhere in the codebase.

**How to apply:** Before every Write of a new file:
1. Glob for the component/module name
2. Grep for similar functions/classes
3. Grep for existing patterns in the same domain
If an equivalent exists, use or extend it. Only create when nothing exists.
