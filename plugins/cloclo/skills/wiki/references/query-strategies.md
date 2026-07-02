# Query Strategies & Auto-Filing (reference)

Detailed strategies for `/wiki query`. SKILL.md's QUERY operation defers here for the
graph-traversal mechanics and the auto-file criteria.

---

## Query classification

Classify the query to pick a search strategy:

| Type | Pattern | Strategy |
|------|---------|----------|
| **Factual** | "What is X?", "When did Y?" | Direct lookup — find the entity/concept page |
| **Relational** | "How does X relate to Y?" | Graph walk — shortest path via `[[wiki-links]]` |
| **Analytical** | "Why did X happen?", "Compare X vs Y" | Multi-page synthesis — read the neighborhood |
| **Gap** | "What don't we know about X?" | Scan sources for mentions without wiki pages |
| **Exploratory** | "What's interesting about X?" | Neighborhood walk — 2 hops from entry point |

---

## Graph-traversal search

For relational, analytical, and exploratory queries, walk the `[[wiki-links]]` graph
from entry-point pages found via `index.md`:

- **Shortest path** (relational): from page A and page B, follow outgoing
  `[[wiki-links]]` via BFS until a common page is found. Read all pages on the path.
  Max depth: 4 hops.
- **Neighborhood** (exploratory): from the entry point, follow all `[[wiki-links]]`
  up to N hops (N=2 quick, N=3 deep). Collect a neighborhood map of connected knowledge.
- **Shared connections** (analytical): for pages A and B, find all pages that link to
  BOTH — these are the bridge concepts between them.

**Provenance.** When reading a page, extract its `sources:` frontmatter (the provenance
chain). For claims needing authoritative verification (technical decisions, audits,
disputed facts), read the actual raw source file listed there.

---

## Auto-file synthesis pages

A query that traverses the graph generates valuable cross-page inferences. Cache them as
synthesis pages to avoid re-deriving the same answer.

**Auto-file when ALL are true:**
- The answer consulted 4+ pages across 2+ subdirectories.
- The answer reveals a cross-page relationship, resolves a contradiction, or identifies a gap.
- No existing synthesis page already covers this (check `wiki/pages/syntheses/`).

**Auto-file synthesis frontmatter** (uses synthesis-only fields — see schema-template.md):
```yaml
---
title: "{descriptive title}"
type: synthesis
synthesis-type: comparison | pattern | contradiction | gap-analysis | framework-application
created: YYYY-MM-DD
updated: YYYY-MM-DD
derived-from:
  - pages/entities/page-a.md
  - pages/concepts/page-b.md
sources:
  - sources/YYYY-MM-DD-source1.md
tags: [tag1, tag2]
---
```

Add back-links (`[[synthesis-page-name]]`) to the `## Related` section of ALL
derived-from pages. Then add the new synthesis to `index.md` (Syntheses section, at the
top of the injected window).

**Ask before filing when** the answer is substantial (>5 sentences) but doesn't meet the
auto-file bar: `This answer synthesizes {N} pages. Save as wiki page? (oui/non)`.

**Never auto-file when** it's a factual single-source lookup, or the answer is
<3 sentences.
