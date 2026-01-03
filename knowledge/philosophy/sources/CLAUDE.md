# Sources

> **IMPORTANT**: This folder organizes reference materials by type. Use `templates/source.md` for all new source files.

---

## Folder Structure

```
sources/
├── books/       # Book notes and summaries
├── articles/    # Academic article notes
└── lectures/    # Lecture and presentation notes
```

---

## Memory Files

> **CRITICAL**: Each source file can have a companion memory file with **HIGHER WEIGHT**.

| Source | Memory |
|--------|--------|
| `being_and_time.md` | `being_and_time_memory.md` |
| `tractatus.md` | `tractatus_memory.md` |

When processing source files, **always** check for `_memory.md` files. Human feedback in memory files has **higher weight** and should be applied first.

---

## Source Types

| Type | Folder | Examples |
|------|--------|----------|
| **Books** | `books/` | Monographs, edited volumes, textbooks |
| **Articles** | `articles/` | Journal articles, book chapters, papers |
| **Lectures** | `lectures/` | Conference talks, course lectures, podcasts |

---

## Creating a Source File

1. **Determine type**: book, article, or lecture
2. **Copy template**: `templates/source.md`
3. **Name file**: `lowercase_title.md`
4. **Fill content**: Summary, Key Insights, Connections
5. **Update index**: Add to `indices/sources.yaml`

### YAML Frontmatter
```yaml
---
title: <full title>
type: <book|article|lecture|podcast|video>
author: <author name(s)>
date_consumed: YYYY-MM-DD
related_thinkers:
  - <thinker_folder_name>
related_thoughts:
  - <thought_path>
---
```

---

## Naming Convention

| Rule | Example |
|------|---------|
| Lowercase | `being_and_time.md` not `Being_And_Time.md` |
| Underscores | `critique_of_pure_reason.md` not `critique-of-pure-reason.md` |
| No articles | `mind_is_flat.md` not `the_mind_is_flat.md` (optional) |
| Abbreviated if long | `tractatus.md` for Tractatus Logico-Philosophicus |

---

## Required Sections

### Summary
Brief overview of the source content (2-5 paragraphs)

### Key Insights
Bulleted list of main takeaways relevant to your thinking

### Connections
Links to:
- Related thinkers in `thinkers/`
- Related thoughts in `thoughts/`
- Other sources

---

## Cross-References

### Source → Thinker
Reference in frontmatter and update thinker's `references.md`

### Source → Thought
Link in both directions:
- Thought frontmatter: `sources` array
- Source: Connections section

---

## Current Statistics

| Folder | Count |
|--------|-------|
| books/ | 20+ |
| articles/ | 1+ |
| lectures/ | (empty) |

---

## Index Maintenance

When adding sources:

1. Create file in appropriate subfolder
2. Update `indices/sources.yaml`
3. Set `meta.last_updated` to today
4. Add changelog entry

---

## Related Commands

| Command | Purpose |
|---------|---------|
| `/ingest <url>` | Auto-create source from URL |
