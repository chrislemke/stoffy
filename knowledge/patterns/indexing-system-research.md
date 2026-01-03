# Indexing System Research: Optimal Format for LLM Agent Access

**Date**: 2026-01-03
**Research Scope**: 8M+ tokens across 7 parallel research agents
**Status**: Crystallized

---

## Executive Summary

**VERDICT: Keep YAML. Your current system is already excellent.**

The current YAML-based hierarchical index system with lazy loading and intent routing is optimal for Stoffy's current scale (54 thinkers, 27 thoughts, ~100 total entries). It achieves **62-92% token savings**. No format change needed.

---

## Format Comparison

| Format | Verdict | Token Efficiency | Human Editing | When to Use |
|--------|---------|------------------|---------------|-------------|
| **YAML** | KEEP | Good (comments add 30% but aid understanding) | Excellent | Current system, up to 500 entries |
| **JSON** | Optional | Excellent (60% smaller minified) | Poor | Cache for performance |
| **SQLite + sqlite-vec** | Future | Excellent (query what you need) | N/A | When entries > 500 |
| **TOML** | No | Poor | Good | Never for indices (no top-level lists) |
| **Custom DSL** | No | Variable | Poor | Never (20% LLM accuracy baseline) |
| **Binary (Protobuf, MessagePack)** | No | N/A | None | Agent-to-agent only |

---

## Current System Assessment

**Score: 7.5/10**

### What's Working Well

1. **Hierarchical Lazy Loading** - root.yaml → domain indices → entity files
2. **Intent-Based Routing** - Keywords + load_when hints guide LLMs naturally
3. **Self-Documenting** - Comments explain purpose and usage
4. **Token Efficiency** - 62-92% savings via selective loading
5. **Worker Assignments** - Named workers (archaeologist, scribe) create semantic mental models

### Token Savings (Documented in indices/philosophy/CLAUDE.md)

| Query Type | Monolithic | Lazy | Savings |
|------------|-----------|------|---------|
| Thinker lookup | ~13K tokens | ~5K tokens | **62%** |
| Theme exploration | ~13K tokens | ~3K tokens | **77%** |
| General orientation | ~13K tokens | ~1K tokens | **92%** |

---

## Critical Issues

### 1. DUPLICATION (HIGH PRIORITY)

**Problem**: Every philosophy index exists twice:
- `indices/philosophy_thinkers.yaml` (flat)
- `indices/philosophy/thinkers.yaml` (nested)

**Impact**: 112KB of duplicated data, maintenance nightmare.

**Fix**: Delete the flat `indices/philosophy_*.yaml` files. Keep only `indices/philosophy/*.yaml`.

### 2. Path Inconsistencies

**Problem**: `philosophy/root.yaml` references `indices/thinkers.yaml` but should reference `indices/philosophy/thinkers.yaml`.

**Fix**: Update paths to be absolute from project root.

---

## Missing Features

| Feature | Priority | Rationale |
|---------|----------|-----------|
| **Tags reverse lookup** (indices/tags.yaml) | High | Enables cross-domain tag queries |
| **Temporal index** (indices/recency.yaml) | Medium | Enables "what's new" queries |
| **Typed links** (influences, critiques, extends) | Medium | Edge semantics enable smarter traversal |
| **Schema validation** | Low | Prevents data corruption |

---

## Recommended Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LAYER 1: ROUTING                         │
│                    Format: YAML                             │
│                    File: indices/root.yaml                  │
│                    Size: <2KB                               │
│  Purpose: Intent mapping, domain routing, lazy loading      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    LAYER 2: DOMAIN INDICES                  │
│                    Format: YAML                             │
│                    Path: indices/{domain}/*.yaml            │
│                    Size: 2-6KB each                         │
│  Purpose: Entity registries with metadata                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    LAYER 3: CONTENT                         │
│              Format: Markdown + YAML Frontmatter            │
│  Purpose: Self-indexing content files                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ (when entries > 500)
┌─────────────────────────────────────────────────────────────┐
│                    LAYER 4: SEARCH                          │
│              Format: SQLite + sqlite-vec                    │
│  Purpose: Fast lookup, semantic search, cross-references    │
│  Trigger: When thinkers > 100 or thoughts > 200             │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Research Insights

1. **Intent routing is the killer feature** - LLMs understand natural language intents better than folder hierarchies

2. **YAML comments add 30% overhead but significantly aid LLM comprehension** - Worth the trade-off for human-edited files

3. **Lazy loading with clear routing saves 62-92% tokens** - Already implemented in Stoffy

4. **Plain text is most token-efficient** (40-60% savings) but lacks structure for relationships

5. **Custom DSLs have 20% LLM accuracy baseline** - Avoid unless heavily prompted

6. **SQLite + sqlite-vec enables semantic search without external services** - Good future option

7. **Markdown frontmatter enables self-indexing content** - Each file can index itself

8. **Your system is already well-designed** - Optimize, don't rebuild

---

## Immediate Action Items

| Priority | Action | Impact |
|----------|--------|--------|
| CRITICAL | Delete `indices/philosophy_*.yaml` (keep `indices/philosophy/*.yaml`) | Removes 112KB duplication |
| HIGH | Fix path inconsistencies in `indices/philosophy/root.yaml` | Prevents broken refs |
| MEDIUM | Create `indices/tags.yaml` with tag → entries mapping | Cross-domain discovery |
| LOW | Add few-shot examples to `intent_mappings` | Better routing accuracy |

---

## Research Sources

- Obsidian Dataview patterns
- Docusaurus/MkDocs/GitBook navigation systems
- LSP/LSIF code indexing
- BM25/RAG inverted indices
- Claude Projects CLAUDE.md best practices
- sqlite-vec vector database research
- Microsoft DSL + LLM research (20% baseline accuracy finding)

---

## Related

- [[genesis]] - Stoffy's founding philosophy
- [[philosophy-repo-patterns]] - Patterns from philosophy repository
