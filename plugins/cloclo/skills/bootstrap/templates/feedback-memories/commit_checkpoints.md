---
name: commit_checkpoints
description: Use when several changes have accumulated — commit every 3-5 tested changes, never 10+ uncommitted
type: feedback
---
After 3 successfully tested changes, create a commit.
Never accumulate more than 5 uncommitted changes.

**Why:** Accumulating many uncommitted changes makes rollback impossible and
turns a small mistake into losing all the work.

**How to apply:**
- Group commits by logic (not by volume).
- Format: `type(scope): description` — feat, fix, refactor, test, docs.
- If a task needs 10+ files: commit in groups of 3-4.
- Reverting 3 files is manageable. Reverting 15 is a nightmare.
