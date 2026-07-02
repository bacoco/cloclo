# Wiki Schema

## Meta
- **Title:** {{WIKI_TITLE}}
- **Created:** {{DATE}}
- **Domain:** {{DOMAIN}}
- **Wiki root:** `wiki/`

## Structure

### Sources (immutable)
Location: `sources/`
Human-curated. Drop files here. Claude reads but never modifies.
Supported formats: `.md`, `.txt`, `.pdf`, URLs (fetched and saved as `.md`).

### Pages (LLM-maintained)
Location: `pages/`
Claude owns this layer entirely. Organized by category:

- `pages/entities/` — Named things: people, organizations, tools, projects
- `pages/concepts/` — Abstract ideas, principles, patterns, methods
- `pages/topics/` — Broader themes spanning multiple concepts
- `pages/comparisons/` — X vs Y analysis pages
- `pages/syntheses/` — Cross-cutting analysis, timelines, overviews
- `pages/sources/` — Per-source summary pages (one per ingested source)

### Special Files
- `index.md` — Master catalog. Claude reads this FIRST for every query.
- `log.md` — Append-only operation record. Never edited, only appended.
- `schema.md` — This file. Defines conventions. Updated when structure evolves.

## Conventions

### Page filenames
Kebab-case. Examples: `reinforcement-learning.md`, `andrej-karpathy.md`, `attention-vs-recurrence.md`

### Frontmatter (every page)
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

**Synthesis-only extensions.** Pages with `type: synthesis` may also carry:
```yaml
synthesis-type: comparison | pattern | contradiction | gap-analysis | framework-application
derived-from:
  - pages/entities/page-a.md
  - pages/concepts/page-b.md
```

**Code-derived provenance (UPDATE op).** Pages built from the codebase (not from a file
in `sources/`) cite the code in `sources:` with a `code:` prefix pinned to a commit:
```yaml
sources:
  - "code: path/to/file.py@<commit-sha>"
```
Lint accepts a `code:` entry as valid grounding — it is not a wiki-link or a `sources/`
file and is never flagged.

### Cross-references
Use `[[page-name]]` (filename without `.md`). Example: `[[reinforcement-learning]]`.
Claude maintains these. On ingest, Claude adds links to all related pages.

### Claims and attribution
Every factual claim should trace to a source. Use inline: `(source: [[source-name]])`.
When sources contradict, note both claims and flag the contradiction explicitly.

### Index entries
One line per page, summary <= 80 chars with mandatory trailing date:
`- [Title](pages/category/filename.md) — one-line summary (YYYY-MM-DD)`
Alphabetical within each section. High-value categories first (Syntheses lead), Sources
last. The SessionStart hook injects only the top ~60 lines / ~4KB — see
references/formats.md for the digest restructure when the index grows past ~55 lines.

## Workflow Preferences
- **Ingest:** Create source summary + update all related pages + update index + log
- **Update:** Refresh code-derived pages after code changes; cite `code: path@commit`
- **Query:** Consult index first, read relevant pages, cite sources in answer
- **Lint:** Report issues, ask before bulk-fixing; may compact old log entries
- **Contradictions:** Flag but do not auto-resolve — human arbitrates
