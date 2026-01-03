---
title: "Patterns from Philosophy Repository"
created: 2026-01-03
source: github:chrislemke/philosophy
tags: [patterns, ingested, philosophy, meta]
connections:
  - knowledge/genesis.md
---

# Patterns Learned from Philosophy Repository

Source: Private GitHub repo `chrislemke/philosophy` (52 thinkers, 25+ thoughts)

## 1. Memory File Convention

**The Pattern**: Every file can have a `_memory.md` companion containing human feedback. Memory files have **HIGHER WEIGHT** than source files.

```
source_file.md       <- Base content
source_file_memory.md  <- Human corrections, insights, preferences
```

**Weight Hierarchy**:
1. Memory file (highest) - Human feedback, corrections
2. Source file (base) - Original content

**What memory files contain**:
- Corrections (factual errors to fix)
- Key insights (crucial points to emphasize)
- Missing elements (gaps to add)
- Preferences (stylistic notes)
- Irrelevant items (things to skip)

**Application to Stoffy**: Implement this pattern for any knowledge that evolves through human feedback.

---

## 2. Thought Lifecycle

**The Pattern**: Thoughts evolve through stages, tracked in frontmatter status.

```
SEED → EXPLORING → DEVELOPING → CRYSTALLIZED → INTEGRATED
                        ↓              ↓
                   CHALLENGED      ARCHIVED
```

| Stage | Description |
|-------|-------------|
| Seed | Initial spark or question |
| Exploring | Actively thinking through |
| Developing | Building coherent position |
| Crystallized | Clear position formed |
| Challenged | Position under reconsideration |
| Integrated | Woven into broader worldview |
| Archived | No longer active, preserved |

**Application to Stoffy**: Apply this lifecycle to any evolving ideas, not just philosophical thoughts.

---

## 3. Bidirectional Linking

**The Pattern**: Entities link to each other in both directions.

**Thought → Thinker**: Via frontmatter
```yaml
related_thinkers:
  - jean_paul_sartre
  - martin_heidegger
```

**Thinker → Thought**: Via `references.md` table
```markdown
| Date | Strength | Path | Reasoning |
|------|----------|------|-----------|
| 2025-12-26 | strong | thoughts/consciousness/... | Core themes |
```

**Application to Stoffy**: Any entity should link both ways to related entities.

---

## 4. Specialized Agents

The philosophy repo has 11 specialized agents for different tasks:

| Agent | Purpose |
|-------|---------|
| philosophical-analyst | Rigorous argument analysis |
| philosophical-generator | Creative ideation |
| philosophical-historian | Genealogy, intellectual history |
| symposiarch | Debate orchestration |
| concept-mapper | Visual/structural mapping |
| cross-cultural-bridge | Cross-traditional translation |
| devils-advocate | Systematic objection generation |
| radical-innovator | Iconoclastic thinking |
| thought-experimenter | Thought experiment design |
| student | Learn from human feedback |
| thinker-creator | Create persona agents from profiles |

**Key Insight**: The `student` agent creates memory files from human feedback - a learning loop.

---

## 5. Auto-Detection Rules

**The Pattern**: Certain input patterns trigger automatic actions without asking.

| Trigger Pattern | Action |
|-----------------|--------|
| `@path/to/entity info` | Auto-ingest info to that file |
| "I've been thinking..." | Create thought in theme folder |
| "I read...", "According to..." | Log source reference |
| "[Philosopher] argued..." | Link to thinker profile |

**Application to Stoffy**: Define auto-detection triggers for common knowledge capture scenarios.

---

## 6. Ingest Command Pattern

The `/ingest` command workflow:
1. Parse input (URL or raw text)
2. Run extraction script
3. Invoke analyst for deep connection analysis
4. Create files using templates
5. Update bidirectional links
6. Update indices

**Application to Stoffy**: The existing `/ingest` command can be adapted for pure knowledge ingestion.

---

## 7. Thematic Organization

Thoughts organized by philosophical domain:

| Theme | Focus |
|-------|-------|
| Consciousness | Mind, awareness, qualia |
| Free Will | Agency, determinism, choice |
| Existence | Being, reality, metaphysics |
| Knowledge | Epistemology, truth, belief |
| Computational Philosophy | Algorithms, information, prediction |

**Application to Stoffy**: Knowledge can be organized by emerging domains as the organism grows.

---

## Key Thinkers Tracked

52 thinker profiles including:
- Karl Friston (Free Energy Principle)
- Joscha Bach (Computational consciousness)
- Nietzsche, Heidegger, Sartre (Existentialism)
- Anil Seth, Andy Clark, Donald Hoffman (Consciousness)
- David Krakauer (Complexity)

---

## Crystallized Insights

Notable synthesized thoughts from the repo:
- **Wu Wei und Freie Energie**: Wu Wei as phenomenology of free energy minimization
- **Inferential Architecture of Complexity**: FEP unifying Krakauer's complexity pillars
- **Complexity and Constructivism**: Epistemological synthesis of FEP + constructivism

---

## Recommendations for Stoffy

1. **Implement memory file convention** - Allow _memory.md companions for any file
2. **Add lifecycle tracking** - Frontmatter status for evolving knowledge
3. **Enable bidirectional linking** - Update both ends when connecting
4. **Define auto-detection triggers** - Capture knowledge without asking
5. **Consider a student agent** - Learn from corrections, create memory files
