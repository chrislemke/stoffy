# Thought Development

> **For entity lookups and global rules**: See `../indices/root.yaml`
>
> **Index Updates**: When creating a new thought or changing thought status, you MUST update `../indices/thoughts.yaml` and update `meta.last_updated` and `changelog`.

This folder captures and develops philosophical thoughts, reflections, and explorations.

## Purpose

- Capture spontaneous philosophical insights before they fade
- Develop coherent positions on fundamental questions
- Track the evolution of thinking over time
- Build connections between ideas across themes
- Engage deeply with philosophical questions

## Thought Lifecycle

```
┌──────┐    ┌───────────┐    ┌────────────┐    ┌─────────────┐    ┌────────────┐
│ SEED │ -> │ EXPLORING │ -> │ DEVELOPING │ -> │ CRYSTALLIZED│ -> │ INTEGRATED │
└──────┘    └───────────┘    └────────────┘    └─────────────┘    └────────────┘
                                    |                 |
                                    v                 v
                             ┌────────────┐    ┌──────────┐
                             │ CHALLENGED │    │ ARCHIVED │
                             └────────────┘    └──────────┘
```

| Stage | Description | Exit Criteria |
|-------|-------------|---------------|
| **Seed** | Initial spark or question | Thought is clearly articulated |
| **Exploring** | Actively thinking through | Core insight emerges |
| **Developing** | Building coherent position | Position articulated with arguments |
| **Crystallized** | Clear position formed | Can defend against objections |
| **Challenged** | Under reconsideration | Resolved or evolved |
| **Integrated** | Woven into worldview | Connected to other positions |
| **Archived** | No longer active | Documented for reference |

## Folder Organization by Theme

| Theme | Folder | Focus |
|-------|--------|-------|
| Meaning of Life | `life_meaning/` | Purpose, fulfillment, value |
| Consciousness | `consciousness/` | Mind, awareness, experience |
| Free Will | `free_will/` | Agency, determinism, choice |
| Morality | `morality/` | Ethics, virtue, obligation |
| Existence | `existence/` | Being, reality, metaphysics |
| Knowledge | `knowledge/` | Epistemology, truth, belief |

## Each Thought Folder Contains

| File | Required | Purpose |
|------|----------|---------|
| `thought.md` | Yes | Main exploration, position, arguments |
| `sources.md` | No | References to books, articles, lectures |
| `evolution.md` | No | How the thought has developed over time |

## Memory Files

> **CRITICAL**: Each thought file can have a companion memory file with **HIGHER WEIGHT**.

| Source | Memory |
|--------|--------|
| `thought.md` | `thought_memory.md` |
| `sources.md` | `sources_memory.md` |
| `evolution.md` | `evolution_memory.md` |

When processing thought files, **always** check for `_memory.md` files. Memory file information (corrections, insights, preferences) has **higher weight** than the source and should be applied first.

## Creating a New Thought

1. Identify the relevant theme from the list above
2. Create folder: `thoughts/<theme>/<thought_name>/`
3. Copy `../templates/thought.md` -> `thought.md`
4. Fill in the initial spark and current position
5. **REQUIRED**: Update `../indices/thoughts.yaml`:
   - Add entry with path, theme, status, started date
   - Update `meta.last_updated` to today's date
   - Add changelog entry

## Thought Development Guidelines

### When Starting (Seed -> Exploring)
- Write down the initial question or insight
- Note what triggered this thought
- List related thinkers to consult

### When Developing (Exploring -> Developing)
- Articulate your emerging position
- Identify supporting arguments
- Acknowledge objections and challenges

### When Crystallizing (Developing -> Crystallized)
- State your position clearly
- Present your strongest arguments
- Address major objections

### When Integrating (Crystallized -> Integrated)
- Connect to other crystallized thoughts
- Show how it fits your broader worldview
- Update related thought files

## Cross-References

| When updating thought content... | Also update... |
|---------------------------------|----------------|
| Thinker mentioned | Their `../thinkers/<name>/references.md` |
| Source referenced | `../sources/<type>/<source>.md` |
| Related to another thought | Both thoughts' `related_thoughts` field |

## Theme Keywords for Auto-Categorization

When ingesting new content, these keywords help identify the appropriate theme:

| Theme | Keywords |
|-------|----------|
| life_meaning | meaning, purpose, fulfillment, worth, value, happiness, good life |
| consciousness | consciousness, mind, awareness, experience, qualia, subjective |
| free_will | free will, determinism, choice, agency, responsibility, decision |
| morality | moral, ethical, virtue, duty, obligation, right, wrong, justice |
| existence | existence, being, reality, metaphysics, time, space, nothing |
| knowledge | knowledge, epistemology, truth, belief, certainty, skepticism |
