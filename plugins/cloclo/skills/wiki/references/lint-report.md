# Lint Report & Definitions (reference)

The report template and the mechanical definitions behind `/wiki lint`. SKILL.md's LINT
operation runs the phases; this file holds the output shape and the checkable rules.

---

## Mechanical definitions

- **Orphan:** file exists under `wiki/pages/`, not listed in `index.md`.
- **Ghost:** listed in `index.md`, file missing.
- **Broken link:** `[[target]]` with no `wiki/pages/**/target.md`. Exception:
  source-summary `## Sources` raw paths (`sources/…`) and `code:` provenance entries are
  NOT wiki-links — never flagged.
- **Isolated page:** zero inbound `[[wiki-links]]` from any other page.
- **Ungrounded page:** empty `sources:` frontmatter. A `code: path@commit` entry counts
  as valid grounding (UPDATE op) — do NOT flag it.
- **Stub:** fewer than 3 sentences of body content.
- **Stale page:** its `updated:` date is more than **90 days older** than the newest
  ingested source (`sources/YYYY-MM-DD-*`) whose title/slug is mentioned on the page.
  If no such newer source exists, the page is NOT stale.
- **Contradiction:** same entity, different facts asserted from different sources.

---

## Log compaction (the one permitted edit of old log entries)

`/wiki lint` is the ONLY operation allowed to rewrite existing `log.md` entries. Optional
step: collapse entries older than 7 days into one weekly summary line per ISO week,
preserving append-only order (newest LAST):

```
## [YYYY-Www] SUMMARY | week of YYYY-MM-DD
- N ingests, M updates, Q queries, L lint runs
```

Keep the most recent 7 days in full so `grep "^## \[" | tail -5` still surfaces real
recent activity. Compaction is optional — skip it if the log is short.

---

## Report template

```
Wiki Lint Report
================

Orphan pages (not in index): N
  - path/to/orphan.md

Broken links: N
  - [[missing-page]] referenced from page-a.md, page-b.md

Isolated pages (no inbound links): N
  - path/to/isolated.md

Stubs (< 3 sentences): N
  - path/to/stub.md

Stale pages (>90d older than a newer source): N
  - path/to/stale.md

Contradictions: N
  - entity-x: "claim A" (source-1) vs "claim B" (source-2)

Missing pages (mentioned in sources, no page): N
  - entity-y (mentioned in 3 sources)

Missing syntheses:
  - topic-a spans 4 sources, no synthesis page
```

Then ask:
> Fix orphans (add to index), create missing pages, resolve stubs?
> Contradictions left for you to arbitrate.

If yes → fix auto-fixable items and log everything. Contradictions are flagged, never
auto-resolved.
