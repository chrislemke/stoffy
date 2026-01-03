# Hierarchical Index System

## Purpose

This index system is optimized for **Claude Code** to minimize token usage through lazy loading. Instead of loading one large monolithic index, agents load only the specific indices they need for a given task.

## Design Philosophy

1. **Lazy Loading**: Load `root.yaml` first (~1K tokens), then load domain-specific indices only when needed
2. **Domain Separation**: Each index covers one domain (thinkers, themes, thoughts, etc.)
3. **Self-Contained**: Each domain index has all info needed for that domain - no cross-references required
4. **Minimal Overhead**: Root index contains routing logic to guide agents to the right domain index

## Token Savings

| Query Type | Old Cost | New Cost | Savings |
|------------|----------|----------|---------|
| Thinker lookup | ~13K tokens | ~5K tokens | **62%** |
| Theme exploration | ~13K tokens | ~3K tokens | **77%** |
| Thought status | ~13K tokens | ~3K tokens | **77%** |
| General orientation | ~13K tokens | ~1K tokens | **92%** |

## Index Files

| File | Purpose | When to Load |
|------|---------|--------------|
| `root.yaml` | Entry point, routing, intent mappings | **Always load first** |
| `thinkers.yaml` | Philosopher/author registry | "who is", philosopher lookups, influences |
| `themes.yaml` | Philosophical categories | theme exploration, categorizing thoughts |
| `thoughts.yaml` | Active thought explorations | thought status, developing ideas |
| `sources.yaml` | Books, articles, lectures | references, citations, reading list |
| `folders.yaml` | Folder purposes & structure | navigation, "where is" |
| `templates.yaml` | Document templates | creating new files |
| `rules.yaml` | Global behavioral rules | auto-detection, naming conventions |
| `memories.yaml` | Human feedback memory files | memory lookup, viewing learned corrections |

## How to Use (for Claude Code)

### Step 1: Load Root Index
```
Read: indices/root.yaml
```
This gives you:
- List of available domain indices
- Intent-to-index routing rules
- Quick patterns for common lookups

### Step 2: Determine Which Domain Index to Load
Use the `intent_mappings` in root.yaml to match user query to domain:
- "Tell me about Aristotle" -> Load `thinkers.yaml`
- "Explore consciousness" -> Load `themes.yaml`
- "What thoughts am I developing?" -> Load `thoughts.yaml`

### Step 3: Load Domain Index and Resolve
```
Read: indices/<domain>.yaml
```
Find the entity, get its path, then read the actual file if needed.

### Example Flow
```
User: "I want to explore my thoughts on free will"

1. Agent loads: indices/root.yaml
2. Matches intent: "theme exploration" -> themes.yaml
3. Agent loads: indices/themes.yaml
4. Finds: free_will -> thoughts/free_will/
5. Agent explores: thoughts/free_will/ folder
```

## Memory File Processing

> **CRITICAL**: This index system respects the memory file convention.

When reading any file from an index lookup:
1. Read the target file (e.g., `thinkers/nietzsche/profile.md`)
2. Check for `<filename>_memory.md` (e.g., `profile_memory.md`)
3. If memory file exists, apply its learnings with **higher weight**

Memory file information **OVERRIDES** source file content. See `indices/rules.yaml` for the full `memory_processing` rule.

## Maintenance Rules

### Adding New Entities

| Action | Update This Index |
|--------|-------------------|
| New thinker profile | `thinkers.yaml` |
| New philosophical theme | `themes.yaml` |
| New thought exploration | `thoughts.yaml` |
| New source/reference | `sources.yaml` |
| New folder with CLAUDE.md | `folders.yaml` |
| New template | `templates.yaml` |
| New global rule | `rules.yaml` |

### Changelog Management

Each domain index has its own `changelog` section at the bottom. When updating an index:

1. Make your changes to the relevant section
2. Add an entry to that index's `changelog` with today's date
3. Update `last_updated` in the index's `meta` section

**Do NOT update root.yaml changelog** unless you're changing routing logic or adding new indices.

## File Size Targets

To maintain efficiency, each index should stay within these limits:

| Index | Target Size | Max Size |
|-------|-------------|----------|
| root.yaml | ~1KB | 2KB |
| thinkers.yaml | ~4KB | 6KB |
| themes.yaml | ~2KB | 4KB |
| thoughts.yaml | ~2KB | 4KB |
| sources.yaml | ~2KB | 4KB |
| folders.yaml | ~2KB | 3KB |
| templates.yaml | ~1KB | 2KB |
| rules.yaml | ~3KB | 5KB |

If an index exceeds its max size, consider:
1. Archiving old/inactive entries
2. Moving detailed info to the actual entity files
3. Splitting into sub-indices (e.g., `thoughts_active.yaml`, `thoughts_archived.yaml`)
