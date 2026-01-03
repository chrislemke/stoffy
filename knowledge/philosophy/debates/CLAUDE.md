# Debates

> **IMPORTANT**: This folder stores transcripts of philosophical debates orchestrated by the `/debate` command.

---

## Purpose

Store and archive structured philosophical debates between agents for:
- Future reference and learning
- Tracking argument development
- Extracting insights for thoughts

---

## Debate Format

Each debate transcript follows this structure:

```markdown
# Debate: <topic>

**Agents**: <agent1> vs <agent2>
**Rounds**: <n>
**Date**: YYYY-MM-DD
**Orchestrated by**: symposiarch

---

## Round 1

### <agent1>
<agent1's opening position>

### <agent2>
<agent2's response>

---

## Round 2
...

---

## Synthesis

<Key points of agreement and disagreement>
<Insights generated>
<Open questions remaining>
```

---

## Naming Convention

```
YYYY-MM-DD_<topic>_<agent1>_vs_<agent2>.md
```

Examples:
- `2025-12-30_moral_realism_devils-advocate_vs_philosophical-analyst.md`
- `2025-12-30_consciousness_radical-innovator_vs_thought-experimenter.md`

---

## Creating Debates

Use the `/debate` command:
```
/debate <agent1> <agent2> <rounds> <topic>
```

Example:
```
/debate devils-advocate philosophical-analyst 5 Is consciousness fundamentally computational?
```

---

## Post-Debate Workflow

After a debate:

1. **Review transcript** for key insights
2. **Extract thoughts** - create new thoughts from compelling arguments
3. **Update thinker references** - if specific philosophers were invoked
4. **Link to sources** - if academic sources were cited

---

## Archiving

Debates are kept indefinitely for reference. No automatic archiving policy.

---

## Memory Files

Debate transcripts can have memory files (`<debate>_memory.md`) for noting key insights or corrections about the debate content. Memory file information has **higher weight**.

---

## Related

| Resource | Purpose |
|----------|---------|
| `/debate` command | Create new debates |
| `symposiarch` agent | Orchestrates debates |
| `thoughts/` | Where debate insights become formal thoughts |
