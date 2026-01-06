# Philosophy Repository Integration

Stoffy integrates with the philosophy knowledge base at `knowledge/philosophy/` for capturing, exploring, and connecting philosophical thoughts.

---

## Quick Start

When I detect philosophical content, I automatically:
1. Load `indices/philosophy/root.yaml` for routing
2. Load the relevant domain index (thinkers, thoughts, themes)
3. Create or update files using templates
4. Maintain bidirectional links

**No manual setup required.** Just think, and I capture.

---

## Available Operations

### Capture a Thought

```
"I've been thinking about how consciousness might be
an emergent property of predictive processing..."
```

I create: `knowledge/philosophy/thoughts/consciousness/YYYY-MM-DD_<topic>.md`

### Explore a Theme

```
"What have I written about free will?"
"Show me my consciousness explorations"
```

I load `indices/philosophy/themes.yaml` and navigate to the relevant folder.

### Look Up a Thinker

```
"What does Friston say about active inference?"
"Tell me about Joscha Bach's views"
```

I load `indices/philosophy/thinkers.yaml` and read their profile at `knowledge/philosophy/thinkers/<name>/profile.md`.

### Create Connections

```
"This thought connects to what Hofstadter wrote about strange loops"
```

I update:
- The thought's `related_thinkers` field
- The thinker's `references.md` file

### Add a Source

```
"I just read The Predictive Mind by Hohwy"
```

I create: `knowledge/philosophy/sources/books/<title>.md`

---

## Auto-Detection Triggers

| What You Say | What I Do |
|--------------|-----------|
| "I've been thinking...", "What if..." | Create thought in appropriate theme |
| "I read...", "According to..." | Log source reference |
| "[Philosopher] argued...", "[Author] wrote..." | Link to thinker profile |
| "@knowledge/philosophy/path info" | Ingest info to that file |

---

## Repository Structure

```
knowledge/philosophy/
  thoughts/           # Philosophical explorations
    consciousness/    # Mind, awareness, experience
    existence/        # Being, reality, metaphysics
    free_will/        # Agency, determinism, choice
    knowledge/        # Epistemology, truth, belief
  thinkers/           # 53 philosopher profiles
    <name>/
      profile.md      # Core ideas, key concepts
      notes.md        # Ongoing engagement
      reflections.md  # Personal reflections
      references.md   # Links to thoughts
  sources/            # Books, articles, lectures
  debates/            # Philosophical debates
```

**Indices** at `indices/philosophy/`:
- `root.yaml` - Entry point, routing rules
- `thinkers.yaml` - 53 philosophers from Socrates to Friston
- `thoughts.yaml` - Active thought explorations
- `themes.yaml` - 6 thematic categories

---

## Common Workflows

### New Philosophical Insight

1. Express your thought naturally
2. I detect the theme (consciousness, free will, etc.)
3. I create a dated thought file using the template
4. I update `indices/philosophy/thoughts.yaml`

### Connecting Ideas

1. Mention a thinker while exploring a thought
2. I add them to the thought's `related_thinkers`
3. I add a reference in their `references.md`
4. Both files now link to each other

### Research Mode

1. Ask about a thinker or theme
2. I load the relevant index
3. I read the profile or thought file
4. I synthesize what you've captured about them

---

## Thought Development Lifecycle

```
SEED -> EXPLORING -> DEVELOPING -> CRYSTALLIZED -> INTEGRATED
                          |               |
                          v               v
                     CHALLENGED       ARCHIVED
```

| Stage | Description |
|-------|-------------|
| Seed | Initial spark |
| Exploring | Actively thinking through |
| Developing | Building coherent position |
| Crystallized | Clear position formed |
| Challenged | Under reconsideration |
| Integrated | Woven into worldview |

---

## Memory Files

Any file can have a `<name>_memory.md` companion containing human feedback. Memory files override the source file content.

Example: `profile.md` + `profile_memory.md` -> memory wins.

---

## Tips

- **Just think out loud** - I detect and organize
- **Name thinkers explicitly** - "Friston argues..." triggers linking
- **Review periodically** - Ask "what are my developing thoughts?"
- **Cross-pollinate** - Mention multiple thinkers to find connections
