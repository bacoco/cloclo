# Wiki Formats (reference)

The generated `wiki/schema.md` is the **runtime authority** — the "CLAUDE.md of the
wiki". This file is the detailed spec behind it; when they differ, the generated
`wiki/schema.md` wins. Templates live at
`${CLAUDE_PLUGIN_ROOT}/skills/wiki/templates/`.

---

## Page format

Every wiki page (`page-template.md`) uses YAML frontmatter:

```yaml
---
title: Page Title
type: entity | concept | topic | comparison | synthesis | source-summary
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources:
  - sources/YYYY-MM-DD-source-name.md
tags: [tag1, tag2]
---
```

Body is standard markdown with `[[wiki-links]]` for cross-references. Every page ends
with `## Sources` and `## Related` sections.

**Provenance for code-derived facts (UPDATE op).** Pages written from the codebase
(not from a file in `wiki/sources/`) cite the code in `sources:` using the `code:`
prefix, pinned to a commit:

```yaml
sources:
  - "code: path/to/file.py@<commit-sha>"
```

Lint treats a `code:` entry as valid grounding (Phase 3) — it is NOT flagged as an
ungrounded page, and the path is NOT treated as a wiki-link or a `sources/` file.

**Exception: source-summary pages** (`source-summary-template.md`). Their `## Sources`
section references the raw source path, not a wiki-link, because the raw source is an
immutable file in `sources/`, not a wiki page:
`- Raw source: \`sources/YYYY-MM-DD-filename.md\``. Their `## Related` section uses
standard `[[wiki-links]]`. Lint knows this exception and does not flag it.

---

## Cross-referencing

- **Format:** `[[page-name]]` — filename without `.md`, without path prefix.
- **Example:** `wiki/pages/entities/andrej-karpathy.md` → `[[andrej-karpathy]]`.
- **Resolution:** Glob `wiki/pages/**/<name>.md`.
- **Uniqueness:** Filenames must be unique across categories. On collision, prefix:
  `concept-attention` vs `entity-attention`.
- **Maintenance:** On every ingest/update, scan touched pages for mentions of other
  wiki entities and add links.

---

## Index format — budget-governed

`wiki/index.md` is the master catalog, read FIRST for every query. The SessionStart
hook injects only the **first ~60 lines AND first ~4KB** of this file. Everything
below that window is invisible at session start, so the head must carry the
highest-value knowledge.

**Rules:**

1. **One line per page**, summary **≤ 80 characters**:
   `- [Title](pages/category/filename.md) — one-line summary (YYYY-MM-DD)`
   The trailing `(YYYY-MM-DD)` date is mandatory on every entry.
2. **High-value categories FIRST.** Order sections: **Syntheses → Decisions →
   Comparisons → Topics → Entities → Concepts → Sources.** Sources are last —
   they are the lowest-value thing to keep in the injected window.
3. **Header stats line:** `> Pages: N | Sources: M | Last updated: YYYY-MM-DD`.
4. **Alphabetical within each section.**

**Digest restructure (when the index exceeds ~55 lines).** Split the file into an
injected digest + a non-injected full index:

```markdown
# Wiki Index

> Pages: N | Sources: M | Last updated: YYYY-MM-DD
> Syntheses: a | Entities: b | Concepts: c | Topics: d | Comparisons: e | Sources: f

## Syntheses            ← highest value, ALWAYS lead with this
- ...most important synthesis/decision pages...

## Key Entities & Concepts
- ...only the most important, not the full list...

<!-- full-index below (not injected) -->

## All Syntheses
...
## All Entities
...
(full per-category list, alphabetical)
```

**Targets:** the digest (everything above the `<!-- full-index below (not injected) -->`
marker) stays **≤ 60 lines and under ~6KB**, and leads with Syntheses/Decisions — never
Sources. The full per-category list below the marker can grow without bound.

---

## Log format

`wiki/log.md` is **append-only**: new entries are appended at the END (newest LAST).
The hook reads recent activity with `grep "^## \[" wiki/log.md | tail -5`, so newest
must be last. Never reorder; never edit existing entries **except** the single
permitted operation: **log compaction during `/wiki lint`** (see `lint-report.md`).

- Each entry header: `## [YYYY-MM-DD HH:MM] OPERATION | Title`
- Operations: `INIT`, `INGEST`, `UPDATE`, `QUERY`, `LINT`, `FIX`
- Parseable: `grep "^## \[" wiki/log.md | tail -N`
