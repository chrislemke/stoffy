# Templates

> **IMPORTANT**: Always use these templates when creating new files in the repository. This ensures consistency and proper index integration.

---

## Template Selection Guide

| Creating a... | Use template | Target folder |
|---------------|--------------|---------------|
| New philosophical exploration | `thought.md` | `thoughts/<theme>/` |
| Book/article/lecture notes | `source.md` | `sources/<type>/` |
| New philosopher profile | `thinker_profile.md` | `thinkers/<name>/profile.md` |
| Thinker engagement notes | `thinker_notes.md` | `thinkers/<name>/notes.md` |
| Personal thinker reflections | `thinker_reflections.md` | `thinkers/<name>/reflections.md` |
| Thinker cross-references | `thinker_references.md` | `thinkers/<name>/references.md` |
| Learning/correction memory | `memory.md` | `<filename>_memory.md` (same dir as source) |

> **MEMORY FILE RULE**: When any file `xyz.md` is processed, also process `xyz_memory.md` if it exists. Memory file content has **HIGHER WEIGHT** than the source file.

---

## Template Files

### thought.md
For new philosophical explorations.

**YAML Frontmatter**:
```yaml
---
title: <title>
theme: <consciousness|free_will|existence|knowledge|life_meaning|morality>
status: <seed|exploring|developing|crystallized|challenged|integrated|archived>
started: YYYY-MM-DD
last_updated: YYYY-MM-DD
related_thinkers:
  - <thinker_folder_name>
related_thoughts:
  - <thought_path>
---
```

**Required sections**: Initial Spark, Current Position, Open Questions

---

### source.md
For book, article, and lecture notes.

**YAML Frontmatter**:
```yaml
---
title: <title>
type: <book|article|lecture|podcast|video>
author: <author>
date_consumed: YYYY-MM-DD
---
```

**Required sections**: Summary, Key Insights, Connections

---

### thinker_profile.md
For philosopher/author profiles.

**YAML Frontmatter**:
```yaml
---
name: <display name>
tradition: <Western|Eastern|African|Contemporary|etc>
era: <Ancient|Medieval|Modern|Contemporary>
key_works:
  - <work1>
  - <work2>
---
```

**Required sections**: Core Ideas, Key Concepts, Influence

---

### thinker_notes.md
For ongoing engagement notes with a thinker.

**Structure**: Timestamped entries documenting engagement

---

### thinker_reflections.md
For personal reflections on a thinker's ideas.

**Structure**: Synthesis of how thinker influences your thinking

---

### thinker_references.md
For cross-references between thinker and thoughts.

**Table format**:
```markdown
| Date | Strength | Path | Reasoning |
|------|----------|------|-----------|
| YYYY-MM-DD | strong/medium/weak | thoughts/... | Why this connects |
```

---

### memory.md
For capturing learned corrections and insights.

**YAML Frontmatter**:
```yaml
---
type: memory
created: YYYY-MM-DD
source: <user feedback description>
target: <file or folder affected>
---
```

---

## Index Updates

**IMPORTANT**: After creating files from templates, update the relevant index:

| File type | Update this index |
|-----------|-------------------|
| Thought | `indices/thoughts.yaml` |
| Thinker | `indices/thinkers.yaml` |
| Source | `indices/sources.yaml` |

Also update:
- `meta.last_updated` field
- `changelog` section

---

## Naming Conventions

| Entity | Pattern | Example |
|--------|---------|---------|
| Thought file | `YYYY-MM-DD_<topic>.md` | `2025-12-30_free_will_synthesis.md` |
| Thought folder | `YYYY-MM-DD_<topic>/` | `2025-12-30_inferential_autonomy/` |
| Thinker folder | `<first>_<last>/` | `karl_friston/` |
| Source file | `<lowercase_title>.md` | `being_and_time.md` |

---

## Files in This Folder

| File | Purpose |
|------|---------|
| `thought.md` | Philosophical exploration template |
| `source.md` | Book/article/lecture notes template |
| `thinker_profile.md` | Philosopher profile template |
| `thinker_notes.md` | Thinker engagement notes template |
| `thinker_reflections.md` | Personal thinker reflections template |
| `thinker_references.md` | Thinker cross-reference template |
| `memory.md` | Learning memory template |
| `claude_index.yaml` | (Legacy) Index template |
