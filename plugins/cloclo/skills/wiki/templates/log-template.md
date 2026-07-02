# Wiki Log

Append-only record of all wiki operations. New entries are appended at the END
(newest LAST). Never edit existing entries — the one exception is log compaction
during `/wiki lint`. Operations: INIT, INGEST, UPDATE, QUERY, LINT, FIX.

Parse recent entries: `grep "^## \[" wiki/log.md | tail -10`

---
