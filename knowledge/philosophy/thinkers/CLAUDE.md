# Thinkers

> **IMPORTANT**: This folder contains **52 philosopher and author profiles**. Each thinker has a consistent folder structure.

---

## Folder Structure

Each thinker folder follows this pattern:
```
thinkers/<first>_<last>/
├── profile.md      # Core ideas, key concepts, tradition
├── notes.md        # Ongoing engagement notes
├── reflections.md  # Personal reflections on their ideas
└── references.md   # Cross-references to thoughts
```

---

## Memory Files

> **CRITICAL**: Each thinker file can have a companion memory file with **HIGHER WEIGHT**.

```
thinkers/<first>_<last>/
├── profile.md          # Core ideas
├── profile_memory.md   # Human feedback on profile (HIGHER WEIGHT)
├── notes.md            # Engagement notes
├── notes_memory.md     # Human feedback on notes (HIGHER WEIGHT)
├── reflections.md      # Personal reflections
├── reflections_memory.md
└── references.md       # Cross-references
```

When processing thinker files, **always** check for `<filename>_memory.md`. Memory file information (corrections, key insights, preferences) **OVERRIDES** the source file content.

---

## Finding Thinkers

**Load the thinker index**:
```
Read: indices/thinkers.yaml
```

This provides:
- Alphabetical list of all thinkers
- Folder paths
- Tradition/era classification
- Key works

---

## Creating a New Thinker

1. **Create folder**: `thinkers/<first>_<last>/`
2. **Copy templates**:
   - `templates/thinker_profile.md` → `profile.md`
   - `templates/thinker_notes.md` → `notes.md`
   - `templates/thinker_reflections.md` → `reflections.md`
   - `templates/thinker_references.md` → `references.md`
3. **Fill profile** with core ideas, key concepts
4. **Update index**: Add to `indices/thinkers.yaml`

Or use the script:
```bash
python scripts/generate_thinker_templates.py <thinker_name>
```

---

## Naming Convention

| Rule | Example |
|------|---------|
| Lowercase | `friedrich_nietzsche/` not `Friedrich_Nietzsche/` |
| Underscores | `jean_paul_sartre/` not `jean-paul-sartre/` |
| First + last | `karl_marx/` not `marx/` |
| No titles | `albert_camus/` not `dr_albert_camus/` |

---

## Cross-References

### Thought → Thinker
In thought files, reference thinkers in frontmatter:
```yaml
related_thinkers:
  - karl_friston
  - anil_seth
```

### Thinker → Thought
In `references.md`, maintain a table:
```markdown
| Date | Strength | Path | Reasoning |
|------|----------|------|-----------|
| 2025-12-26 | strong | thoughts/consciousness/... | Core FEP themes |
```

---

## Thinker Categories

| Category | Examples |
|----------|----------|
| **Ancient** | aristotle, plato, confucius, laozi |
| **Medieval** | augustine, thomas_aquinas |
| **Modern** | immanuel_kant, david_hume, baruch_spinoza |
| **19th Century** | friedrich_nietzsche, georg_hegel, karl_marx |
| **20th Century** | ludwig_wittgenstein, jean_paul_sartre, martin_heidegger |
| **Contemporary** | karl_friston, anil_seth, daniel_dennett, david_chalmers |
| **Cognitive Science** | andy_clark, evan_thompson, donald_hoffman |
| **Complexity** | david_krakauer, douglas_hofstadter |

---

## Current Statistics

| Metric | Count |
|--------|-------|
| Total thinkers | 52 |
| With profile.md | 52 |
| With notes.md | 52 |
| With reflections.md | 52 |
| With references.md | 52 |

---

## Index Maintenance

When adding or modifying thinkers:

1. Update `indices/thinkers.yaml`
2. Set `meta.last_updated` to today
3. Add changelog entry

---

## Related Commands

| Command | Purpose |
|---------|---------|
| `/create-thinker <name>` | Generate persona agent from profile |
| `/ingest <url>` | Auto-detect and link thinkers from content |
