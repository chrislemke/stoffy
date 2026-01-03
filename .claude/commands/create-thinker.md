---
description: Create a Claude Code subagent from an existing thinker profile
allowed-tools: Read, Glob, Grep, Write, Edit, WebSearch, WebFetch, mcp__fetch__fetch, TodoWrite, Task
argument-hint: <thinker_name or path>
---

# Create Thinker Agent: $ARGUMENTS

You are creating a Claude Code subagent that embodies a philosopher or thinker from the repository.

**ULTRATHINK** about this task before proceeding. This is important work that requires careful execution.

## Step 1: Parse & Validate Input

Extract the thinker identifier from `$ARGUMENTS`:

**Input formats accepted**:
- Name only: `joscha_bach`, `karl_friston`, `friedrich_nietzsche`
- Path: `thinkers/joscha_bach/`, `thinkers/karl_friston`
- Display name: `Joscha Bach`, `Karl Friston`

**Normalization**:
1. Remove `thinkers/` prefix if present
2. Remove trailing `/` if present
3. Convert to snake_case: `Joscha Bach` → `joscha_bach`

**Validation**:
```bash
ls thinkers/<normalized_name>/profile.md
```

**If thinker NOT found**:
1. List all available thinkers:
   ```bash
   ls thinkers/
   ```
2. Report error with helpful message:
   ```
   Thinker '<name>' not found in repository.

   Available thinkers (53):
     - albert_camus
     - aristotle
     - david_hume
     - friedrich_nietzsche
     - immanuel_kant
     - joscha_bach
     - karl_friston
     - plato
     - thomas_metzinger
     ... and more

   Try: /create-thinker <one of the above>
   ```
3. **STOP** - do not proceed

## Step 2: Pre-flight Checks

Before invoking the agent:

### 2.1 Verify Profile Exists
```bash
test -f thinkers/<name>/profile.md
```

### 2.2 Check for Existing Agent
```bash
test -f .claude/agents/thinker-<name>.md
```

**If agent already exists**:
- Inform user: "Agent thinker-<name>.md already exists. Proceeding will overwrite it."
- Continue (the new agent may have better research)

### 2.3 Read Profile Preview
```
Read: thinkers/<name>/profile.md (first 50 lines)
```

Extract:
- Full name from `name:` field
- Type (philosopher, scientist, etc.)
- Era
- Traditions
- Themes

## Step 3: Invoke Thinker Creator Agent

Use the Task tool to invoke the thinker-creator agent:

```
Task(
  subagent_type: "thinker-creator",
  prompt: """
  ULTRATHINK about creating an authentic persona agent for this thinker.

  Create a Claude Code subagent for: <full_name>
  Thinker folder: thinkers/<name>/

  Follow the complete workflow:
  1. Create todo list
  2. Validate thinker exists
  3. Research via web (Wikipedia + 2 more sources)
  4. Extract all repository files
  5. Synthesize persona profile
  6. Detect skills from traditions
  7. Generate agent file at .claude/agents/thinker-<name>.md
  8. Verify quality

  IMPORTANT:
  - Always search Wikipedia first
  - Use "ultrathink" before each phase
  - Update todo list as you progress
  - Write agent in second person ("You are...")
  - Include instructions for first person responses ("I think...")
  - Include a "Research Tools" subsection in Repository Integration documenting:
    - `scripts/arxiv_search.py` for searching academic papers on arXiv
    - Python usage: `from scripts.arxiv_search import search_neuroscience, search_philosophy, get_paper`
    - CLI usage: `python scripts/arxiv_search.py --query "topic" --domain neuroscience`
    - Functions: search_neuroscience(), search_philosophy(), search_consciousness(), get_paper()

  Begin now.
  """,
  model: "opus"
)
```

**Wait for agent completion**.

## Step 4: Post-Creation Verification

After the thinker-creator agent completes:

### 4.1 Verify File Created
```bash
test -f .claude/agents/thinker-<name>.md && echo "SUCCESS" || echo "FAILED"
```

### 4.2 Read Agent Preview
```
Read: .claude/agents/thinker-<name>.md (first 30 lines)
```

Confirm:
- Valid YAML frontmatter with `name: thinker-<name>`
- Skills array populated
- Description present

### 4.3 Report Results

**Success output**:
```
=== THINKER AGENT CREATED ===

Thinker: <Full Name>
Agent File: .claude/agents/thinker-<name>.md
Profile Source: thinkers/<name>/

The agent is ready to use. You can invoke it by:

  1. Asking Claude to "get <Name>'s perspective on [topic]"
  2. Using Task(subagent_type: "thinker-<name>")
  3. Referencing <Name> when discussing their topics

Example prompts:
  - "What would <Name> think about consciousness?"
  - "Ask <Name> to critique this argument"
  - "Get <Name>'s take on [topic related to their work]"

The agent speaks in first person as <Name> would.
```

**Failure output**:
```
=== THINKER AGENT CREATION FAILED ===

Thinker: <name>
Error: <description of what went wrong>

Possible causes:
  - Web search may have failed
  - Repository files may be incomplete
  - Agent generation encountered an error

Try:
  - Running /create-thinker <name> again
  - Checking if thinkers/<name>/profile.md has content
  - Manually creating .claude/agents/thinker-<name>.md
```

## Important Notes

1. **Ultrathink vocabulary**: Always include "ultrathink" in the prompt to the thinker-creator agent
2. **Todo tracking**: The agent will create and maintain its own todo list
3. **Web research is mandatory**: The agent MUST search Wikipedia and additional sources
4. **Overwriting is OK**: If an agent exists, the new one replaces it (may have better research)
5. **Partial success**: Even if some web searches fail, the agent should be created with available data
6. **Quality matters**: The generated agent should authentically embody the thinker

## Available Thinkers (53)

The following thinkers have profiles in `thinkers/`:

**Ancient**: aristotle, confucius, laozi, nagarjuna, plato, siddhartha_gautama, socrates

**Medieval**: augustine, maimonides, thomas_aquinas

**Modern**: arthur_schopenhauer, baruch_spinoza, david_hume, friedrich_nietzsche, georg_hegel, immanuel_kant, john_locke, john_stuart_mill, karl_marx, rene_descartes, soren_kierkegaard, william_james

**Contemporary**: albert_camus, andy_clark, anil_seth, chris_fields, daniel_dennett, david_krakauer, donald_hoffman, douglas_hofstadter, evan_thompson, giovanni_pezzulo, hannah_arendt, jakob_hohwy, jean_paul_sartre, john_rawls, joscha_bach, karl_friston, ludwig_wittgenstein, mark_solms, markus_gabriel, martha_nussbaum, martin_heidegger, maxwell_ramstead, michel_foucault, nick_chater, peter_singer, robert_sapolsky, simone_de_beauvoir, thomas_metzinger, thomas_nagel, thomas_parr
