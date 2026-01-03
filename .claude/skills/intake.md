# /intake - Process New Input Files

Process a file from the `_input/` folder through the intelligent intake pipeline.

## Core Philosophy

**COMPUTE IS CHEAP. INSIGHT IS VALUABLE.**

Don't hesitate to spawn 5, 10, or more swarms if the content warrants it. The goal is understanding, not efficiency.

## Usage

```
/intake <file_path>         # Process specific file
/intake                     # Process all files in _input/
/intake --pending           # Review pending items
```

## What This Does

1. Reads the input file content
2. Analyzes: What is this REALLY about? What's beneath the surface?
3. Decides: Simple storage OR complex processing (and HOW MUCH processing?)
4. Executes: Spawns as many Claude Flow swarms as needed
5. Aggregates results from all swarms
6. Stores enriched results with connections
7. Updates indices
8. Archives the original

## Processing Paths

### Simple Storage
Quick, self-contained content goes directly to:
- `memory/quick/` - brief thoughts
- `memory/moments/` - captured moments
- `ideas/seeds/` - idea starting points
- `knowledge/` - factual content

### Complex Processing
Content that needs deeper analysis gets Claude Flow swarms:
- **connection_finder** - links to existing knowledge
- **synthesis_engine** - combines with existing content
- **deep_explorer** - expands promising ideas
- **thought_weaver** - processes philosophical content

## Steps

### Step 1: Load Configuration
Read `indices/intake.yaml` for processing rules.

### Step 2: Read Input
```bash
# Get the input file(s)
ls _input/
# Then read content
```

### Step 3: Analyze & Decide
Invoke the intake-processor agent logic:
- Detect content type
- Assess complexity
- Choose processing path

### Step 4: Execute

**For Simple:**
1. Select template from `templates/`
2. Create file in appropriate folder
3. Update `indices/knowledge.yaml`

**For Complex (the norm, not the exception):**

Spawn ALL relevant swarms in a SINGLE message for parallel execution:

```javascript
// Example: Philosophical content about consciousness
[Single Message - Parallel Agent Execution]:

// Perspective swarms (5 perspectives)
Task("Philosophical Analyst", "Analyze consciousness from philosophy of mind perspective. Reference Chalmers, Nagel, Dennett.", "analyst")
Task("Scientific Analyst", "Analyze from neuroscience/cognitive science perspective. What does research say?", "researcher")
Task("Historical Analyst", "Trace the history of this idea. Who thought about this before?", "researcher")
Task("Critical Analyst", "What are the weaknesses, blind spots, counterarguments?", "analyst")
Task("Practical Analyst", "What are the practical implications? How does this affect action?", "coder")

// Connection swarms
Task("Knowledge Archaeologist", "Search all indices for related entries. Map the connection network.", "researcher")
Task("Pattern Finder", "What patterns does this share with existing knowledge?", "analyst")

// Synthesis swarms
Task("Synthesizer", "Combine all perspectives into coherent understanding.", "coder")
Task("Documenter", "Create the final enriched entry with all connections.", "coder")

// That's 9 swarms for ONE piece of content. This is GOOD.
```

2. Wait for all agents to complete
3. Read all outputs and synthesize
4. Create enriched file with all connections
5. Update indices with new entry and all cross-references

### Step 5: Finalize
```bash
# Move original to archive
mv _input/file.txt _intake/archive/$(date +%Y-%m-%d)_file.txt

# Log the processing
```

### Step 6: Report
```
╔════════════════════════════════════════════════════════════════╗
║                    INTAKE COMPLETE                              ║
╠════════════════════════════════════════════════════════════════╣
║ Input:     thoughts.txt                                         ║
║ Type:      philosophical thought                                ║
║ Processing: complex (thought_weaver swarm)                      ║
╠════════════════════════════════════════════════════════════════╣
║ OUTPUT:                                                         ║
║   ✓ knowledge/philosophy/consciousness-reflection.md            ║
║                                                                 ║
║ CONNECTIONS MADE:                                               ║
║   → knowledge/philosophy/awareness.md                           ║
║   → knowledge/genesis.md                                        ║
║                                                                 ║
║ ARCHIVE: _intake/archive/2025-01-03_thoughts.txt                ║
╚════════════════════════════════════════════════════════════════╝
```

## Decision Heuristics

For every piece of content, ask:

1. **Depth Check**: Is there more here than meets the eye?
2. **Connection Check**: Could this link to existing knowledge?
3. **Perspective Check**: Would multiple viewpoints add value?
4. **Research Check**: Does this open questions needing investigation?
5. **Exploration Check**: Could this idea branch in interesting directions?

**If YES to any → spawn swarms for that dimension.**
**If YES to multiple → spawn ALL relevant swarms in parallel.**

Simple storage is ONLY when ALL answers are clearly "no" (rare).

## Example Scales

| Content Type | Swarms |
|--------------|--------|
| "Buy milk" reminder | 0 (simple storage) |
| Short observation with depth | 2-3 |
| Promising idea | 4-6 |
| Philosophical content | 5-8 |
| Complex research topic | 8-12+ |
| Major new territory | Unlimited - spawn waves |

## See Also

- `indices/intake.yaml` - Full processing rules and swarm patterns
- `.claude/agents/intake-processor.md` - Detailed agent behavior
- `templates/` - Content templates
