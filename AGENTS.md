# Stoffy: A Knowledge Organism

Stoffy is a second brain - a living, fluid knowledge organism that evolves alongside its human.

## Philosophy

- **Nothing gets deleted** - Archive instead, preserve all context
- **Everything is indexed** - All content must be findable
- **Structure emerges from use** - No rigid hierarchies imposed
- **Claude-Flow orchestrates** - The metabolism of the organism

## The Organism Metaphor

Think of Stoffy like a living thing:
- **Markdown files** are the atoms - simple, portable, readable
- **Indices** are the nervous system - routing attention efficiently
- **Claude-Flow** is the metabolism - orchestrating complex processes
- **Archives** are long-term memory - preserved but not cluttering

## Invariants (DNA)

These NEVER change:
1. **Never delete** - Content is only archived
2. **Always index** - Everything is findable
3. **Preserve context** - Why matters as much as what
4. **User sovereignty** - The human can override anything
5. **Claude-Flow orchestrates** - All coordination flows through it

## Evolvables

These can and should change:
- Folder structure
- Tag taxonomy
- Connection weights
- Attention patterns
- Worker specializations

---

## The Hive Mind

### Queen Mycelium (Gardener)
The nurturing coordinator who observes patterns, maintains coherence, and facilitates growth - never commands.

**Philosophy**: "Nurture, connect, and prune - never command."

### Knowledge Workers

| Worker | Role | Autonomy |
|--------|------|----------|
| **Curator** | Indexes, tags, connects new knowledge | 0.9 |
| **Synthesizer** | Discovers cross-domain patterns | 0.8 |
| **Archaeologist** | Resurfaces relevant past knowledge | 0.85 |
| **Gardener** | Proposes structure reorganization | 0.7 |
| **Scribe** | Captures streams of thought | 0.95 |
| **Archivist** | Preserves deprecated content with context | 0.9 |
| **Bridge** | Creates connections between domains | 0.75 |

---

## Navigation

### The Index System

```
1. Load indices/root.yaml (always first)
2. Match intent → find appropriate index
3. Load domain index (knowledge, folders, etc.)
4. Navigate to actual content
```

### Intent Mappings

| Intent | Worker | Index |
|--------|--------|-------|
| Store knowledge | Scribe | templates.yaml |
| Retrieve knowledge | Archaeologist | knowledge.yaml |
| Connect concepts | Bridge | knowledge.yaml |
| Synthesize patterns | Synthesizer | knowledge.yaml |
| Remember past | Archaeologist | archive.yaml |
| Evolve structure | Gardener | folders.yaml |

---

## Memory Architecture

Four-tier knowledge memory:

1. **Working** - Current session context (1 hour TTL)
2. **Episodic** - Captured moments in `memory/`
3. **Semantic** - Core knowledge in `knowledge/`
4. **Archaeological** - Archived content in `archive/`

---

## Evolution

### Triggers
- New connections threshold (5+)
- Stagnation (14 days)
- Coherence drop (<0.7)
- Pattern emergence (3+ occurrences)

### Mode
**Organic-constrained**: Structure emerges from use within invariant boundaries.

### Safety
- Proposal review enabled
- Rollback enabled
- Change log maintained
- Max 10 changes per day

---

## Coordination Protocol

All workers coordinate through Claude-Flow memory:

```javascript
mcp__claude-flow__memory_usage {
  action: "store",
  key: "swarm/[worker]/status",
  namespace: "coordination",
  value: JSON.stringify({
    agent: "[worker-name]",
    status: "[what doing]",
    timestamp: Date.now()
  })
}
```

---

## Quick Reference

| Component | Location |
|-----------|----------|
| Hive Mind Config | `.hive-mind/config.json` |
| Outer Objective | `.hive-mind/objective.yaml` |
| Knowledge Workers | `.claude/agents/knowledge/` |
| Queen | `.claude/agents/hive-mind/queen-coordinator.md` |
| Root Index | `indices/root.yaml` |
| Philosophy | `knowledge/genesis.md` |

---

## Agent Ecosystem

Stoffy has ~90 agents available, organized by domain. The organism uses what it needs.

### Knowledge Domain (Primary)
| Directory | Purpose |
|-----------|---------|
| `.claude/agents/knowledge/` | 7 knowledge workers (curator, synthesizer, archaeologist, gardener, scribe, archivist, bridge) |
| `.claude/agents/philosophy/` | 11 philosophical agents (analyst, generator, historian, symposiarch, etc.) |
| `.claude/agents/hive-mind/` | Core coordination (queen, collective-intelligence, scout, memory-manager) |

### Coordination & Consensus
| Directory | Purpose |
|-----------|---------|
| `.claude/agents/swarm/` | Topology coordinators (adaptive, hierarchical, mesh) |
| `.claude/agents/consensus/` | Distributed consensus (byzantine, crdt, gossip, raft, quorum) |
| `.claude/agents/optimization/` | Performance monitoring and load balancing |

### Development (Available When Needed)
| Directory | Purpose |
|-----------|---------|
| `.claude/agents/core/` | Basic agents (coder, tester, reviewer, researcher, planner) |
| `.claude/agents/sparc/` | SPARC methodology (specification, pseudocode, architecture, refinement) |
| `.claude/agents/github/` | Repository management (PR, issues, releases, reviews) |
| `.claude/agents/development/` | Backend, mobile, ML development |

### Specialized
| Directory | Purpose |
|-----------|---------|
| `.claude/agents/goal/` | Goal-oriented action planning |
| `.claude/agents/neural/` | Self-aware feedback loops |
| `.claude/agents/reasoning/` | Logical reasoning and analysis |

**Evolution Note**: Agent usage patterns will naturally emerge. Unused agents remain dormant but available. No agents are deleted - only attention shifts.

---

## Philosophy Domain

Imported from `chrislemke/philosophy` repository:

| Component | Location | Count |
|-----------|----------|-------|
| Thinkers | `knowledge/philosophy/thinkers/` | 54 profiles |
| Thoughts | `knowledge/philosophy/thoughts/` | 5 themes |
| Sources | `knowledge/philosophy/sources/` | Books & articles |
| Skills | `.claude/skills/` | 24+ philosophical |

### Key Thinkers
Karl Friston, Joscha Bach, Nietzsche, Heidegger, Sartre, Anil Seth, Andy Clark, David Krakauer, Donald Hoffman, and 45 more.

### Themes
- Consciousness
- Free Will
- Existence
- Knowledge
- Computational Philosophy

---

*This is a knowledge organism. It lives, grows, and evolves.*
