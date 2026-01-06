# Philosophy Repository Integration Architecture

## Overview

This document describes the architecture for integrating Stoffy with the `chrislemke/philosophy` GitHub repository. The integration enables automatic detection of philosophical content in conversations and seamless persistence to the remote repository via the `gh` CLI.

**Design Principles**: KISS - minimal complexity, maximum clarity.

---

## 1. Module Structure

```
.claude/skills/philosophy-repo/
|
+-- SKILL.md                    # Main skill definition (auto-detection triggers)
+-- scripts/
|   +-- repo.sh                 # gh CLI wrapper for all repo operations
|   +-- detect.sh               # Content detection helper
+-- templates/
|   +-- thought.md              # Local copy of thought template
|   +-- thinker_notes.md        # Local copy of notes template
|   +-- source.md               # Local copy of source template
+-- config.yaml                 # Repository configuration
```

### Module Responsibilities

| Module | Purpose | Dependencies |
|--------|---------|--------------|
| `SKILL.md` | Trigger detection, main instructions | None |
| `scripts/repo.sh` | All gh CLI operations (read/write/commit) | gh CLI |
| `scripts/detect.sh` | Pattern matching for auto-detection | grep/sed |
| `templates/` | Local template cache (avoid API calls) | None |
| `config.yaml` | Repo URL, branch, paths | None |

---

## 2. Data Flow Diagrams

### 2.1 Read Flow (Fetch from Philosophy Repo)

```
+----------------+     +-------------+     +------------------+     +--------------+
|  User Request  | --> |  SKILL.md   | --> |  scripts/repo.sh | --> |  gh api      |
|  "who is X?"   |     |  (routing)  |     |  read_file()     |     |  contents/   |
+----------------+     +-------------+     +------------------+     +--------------+
                                                   |
                                                   v
                              +------------------------------------------+
                              |  gh api repos/chrislemke/philosophy/     |
                              |  contents/thinkers/X/profile.md          |
                              |  --jq '.content' | base64 -d             |
                              +------------------------------------------+
                                                   |
                                                   v
                              +------------------------------------------+
                              |  Return Markdown content to Claude       |
                              +------------------------------------------+
```

### 2.2 Write Flow (Auto-commit to Philosophy Repo)

```
+------------------+     +-----------------+     +------------------+
|  Philosophical   | --> |  Auto-detect    | --> |  Confirm with    |
|  Content in Chat |     |  (SKILL.md)     |     |  User (optional) |
+------------------+     +-----------------+     +------------------+
                                                        |
                                                        v
+------------------+     +------------------+     +------------------+
|  gh api PUT      | <-- |  scripts/repo.sh | <-- |  Format using    |
|  contents/path   |     |  write_file()    |     |  template        |
+------------------+     +------------------+     +------------------+
        |
        v
+-------------------------------------------+
|  gh api -X PUT repos/chrislemke/philosophy|
|  /contents/{path}                         |
|  -f message="Add thought: X"              |
|  -f content="$(base64 < file)"            |
|  -f branch="main"                         |
+-------------------------------------------+
```

### 2.3 Auto-Detection Flow

```
+---------------+
|  User Input   |
+-------+-------+
        |
        v
+-------+------------------+
|  Pattern Matching        |
|  (see Section 3)         |
+-------+------------------+
        |
        +---> [No Match] --> Continue normal conversation
        |
        +---> [Match Found]
                    |
                    v
        +-----------+-------------+
        |  Classify Content Type  |
        +-----------+-------------+
                    |
    +---------------+---------------+
    |               |               |
    v               v               v
+-------+     +---------+     +--------+
|THOUGHT|     |THINKER  |     |SOURCE  |
+---+---+     +----+----+     +---+----+
    |              |              |
    v              v              v
+---+---+     +----+----+     +---+----+
|Route  |     |Route    |     |Route   |
|thoughts/|   |thinkers/|     |sources/|
+-------+     +---------+     +--------+
```

---

## 3. Auto-Detection Triggers

### 3.1 Thought Detection

**Trigger Phrases** (from `rules.yaml`):
- "I've been thinking about..."
- "What if..."
- "I wonder whether..."
- "It seems to me that..."
- "I believe that..."
- "My position on..."

**Theme Keywords** (for routing to correct subfolder):

| Theme | Keywords | Target Path |
|-------|----------|-------------|
| consciousness | mind, awareness, qualia, experience, phenomenal | `thoughts/consciousness/` |
| free_will | choice, determinism, agency, responsibility | `thoughts/free_will/` |
| existence | being, nothing, why, existence, ontology | `thoughts/existence/` |
| knowledge | epistemic, belief, justified, truth, certainty | `thoughts/knowledge/` |
| computational | algorithm, computation, information, simulation | `thoughts/computational_philosophy/` |

### 3.2 Thinker Detection

**Trigger Phrases**:
- "[Name] argued/believed/wrote..."
- "According to [Name]..."
- "I agree/disagree with [Name]..."

**Action**: Check if thinker exists in `thinkers/`, offer to add notes or create profile.

### 3.3 Source Detection

**Trigger Phrases**:
- "I read [Book/Article]..."
- "In [Work], [Author] says..."
- "[Author] wrote in [Work]..."

**Action**: Offer to create source entry in `sources/books/` or `sources/articles/`.

### 3.4 Auto-Ingestion Pattern

**Pattern**: `@<path> <information>`

**Example**: `@thinkers/kant/ insight about categorical imperative`

**Action**: Immediately append to `thinkers/kant/notes.md` without confirmation.

---

## 4. Integration Points with Stoffy

### 4.1 Consciousness Daemon Integration

The philosophy skill can register as an action handler in Stoffy's autonomous decision engine:

```python
# In consciousness/decision/actions.py

PHILOSOPHY_ACTIONS = [
    ActionTemplate(
        name="capture_philosophical_thought",
        description="Capture philosophical reflection to repository",
        patterns=["thinking about", "wonder whether", "believe that"],
        executor_type="skill",
        skill_name="philosophy-repo",
        priority=6,  # Medium priority
        cooldown_seconds=60,
    ),
    ActionTemplate(
        name="lookup_thinker",
        description="Fetch philosopher information from repository",
        patterns=["who is", "what did .* believe", ".*'s philosophy"],
        executor_type="skill",
        skill_name="philosophy-repo",
        priority=3,  # Higher priority for lookups
        cooldown_seconds=10,
    ),
]
```

### 4.2 Event Flow from Daemon

```
ConsciousnessDaemon (watcher_git.py or watcher.py)
        |
        v
DecisionEngine.process() --> categorize_changes()
        |
        v
match_actions() --> finds philosophy-related patterns
        |
        v
AutonomousEngine.decide() --> confidence > threshold
        |
        v
ExpandedExecutor.execute() --> invokes skill
        |
        v
Skill("philosophy-repo") --> scripts/repo.sh
```

### 4.3 Memory Integration

The skill respects the repository's memory file convention:

```
When reading: profile.md
Also check:   profile_memory.md (higher weight)

Memory corrections OVERRIDE source content.
```

This integrates with Stoffy's existing `StateManager` for local caching.

---

## 5. API Design

### 5.1 Script Interface: `scripts/repo.sh`

```bash
# READ OPERATIONS
repo.sh read <path>                    # Read file content
repo.sh list <directory>               # List directory contents
repo.sh exists <path>                  # Check if file exists
repo.sh search <pattern>               # Search file contents

# WRITE OPERATIONS
repo.sh write <path> <content>         # Create/update file
repo.sh append <path> <content>        # Append to existing file
repo.sh delete <path>                  # Delete file

# INDEX OPERATIONS
repo.sh index <name>                   # Read index file (root, themes, thinkers, etc.)
repo.sh template <name>                # Get template content

# UTILITY
repo.sh thinkers                       # List all thinkers
repo.sh thoughts                       # List all thoughts
repo.sh sources                        # List all sources
```

### 5.2 Internal Functions

```bash
# repo.sh internals

_api_get() {
    # GET request to GitHub API
    gh api "repos/chrislemke/philosophy/contents/$1" --jq '.content' | base64 -d
}

_api_put() {
    # PUT request to GitHub API (create/update)
    local path="$1"
    local content="$2"
    local message="$3"

    # Get current SHA if file exists
    local sha=$(gh api "repos/chrislemke/philosophy/contents/$path" --jq '.sha' 2>/dev/null || echo "")

    local args=(-X PUT "repos/chrislemke/philosophy/contents/$path")
    args+=(-f "message=$message")
    args+=(-f "content=$(echo "$content" | base64)")
    args+=(-f "branch=main")

    if [[ -n "$sha" ]]; then
        args+=(-f "sha=$sha")
    fi

    gh api "${args[@]}"
}

_api_list() {
    # List directory contents
    gh api "repos/chrislemke/philosophy/contents/$1" --jq '.[].name'
}
```

### 5.3 Skill YAML Frontmatter

```yaml
---
name: "Philosophy Repository"
description: "Integrate with chrislemke/philosophy GitHub repository for philosophical thought management. Auto-detects philosophical content (thoughts, thinker references, source mentions) and offers to persist to repository. Use when: discussing philosophy, mentioning philosophers, expressing beliefs/positions, referencing philosophical works, or using @path syntax for direct ingestion. Triggers: 'I believe', 'thinking about', 'what if', 'wonder whether', '[Name] argued', 'I read [Book]'."
---
```

---

## 6. Configuration

### 6.1 config.yaml

```yaml
repository:
  owner: chrislemke
  name: philosophy
  branch: main

paths:
  indices: indices/
  thoughts: thoughts/
  thinkers: thinkers/
  sources: sources/
  templates: templates/

auto_commit:
  enabled: true
  confirm_threshold: medium  # low = always auto, medium = confirm new files, high = always confirm
  commit_message_prefix: "stoffy:"

detection:
  enabled: true
  sensitivity: medium  # low, medium, high

cache:
  templates: true
  indices: true
  ttl_seconds: 3600
```

### 6.2 Environment Requirements

```bash
# Required
gh --version  # GitHub CLI must be installed and authenticated

# Verify access
gh api repos/chrislemke/philosophy --jq '.full_name'
# Expected: chrislemke/philosophy
```

---

## 7. Example Interactions

### 7.1 Thought Capture

**User Input**:
> I've been thinking about consciousness and whether the hard problem is actually solvable. It seems to me that we might be asking the wrong question entirely.

**Skill Response**:
1. Detects: "I've been thinking about..." + "consciousness" keyword
2. Routes to: `thoughts/consciousness/`
3. Offers: "Would you like me to capture this thought in your philosophy repository?"
4. If yes: Creates `thoughts/consciousness/hard_problem_wrong_question.md` using template
5. Commits: `stoffy: Add thought - hard problem wrong question`

### 7.2 Thinker Lookup

**User Input**:
> What did Karl Friston believe about consciousness?

**Skill Response**:
1. Detects: "What did [Name] believe..."
2. Executes: `repo.sh read thinkers/karl_friston/profile.md`
3. Also checks: `repo.sh exists thinkers/karl_friston/profile_memory.md`
4. Returns: Formatted profile content with memory corrections applied

### 7.3 Auto-Ingestion

**User Input**:
> @thinkers/nietzsche/ Key insight: his concept of amor fati connects to Stoic acceptance but with affirmation rather than mere resignation.

**Skill Response**:
1. Detects: `@path` pattern
2. Executes: `repo.sh append thinkers/nietzsche/notes.md "..."`
3. Commits: `stoffy: Add note to nietzsche`
4. Confirms: "Added insight to nietzsche/notes.md"

---

## 8. Error Handling

| Error | Detection | Recovery |
|-------|-----------|----------|
| gh not authenticated | `gh auth status` fails | Prompt user to run `gh auth login` |
| File not found | API returns 404 | Offer to create new file |
| Rate limit | API returns 403 | Back off, cache more aggressively |
| Network error | API timeout | Retry with exponential backoff |
| Invalid template | Template parse fails | Fall back to minimal markdown |
| Commit conflict | SHA mismatch | Re-fetch, merge, retry |

---

## 9. Security Considerations

1. **No secrets in code**: gh CLI handles authentication via OS keychain
2. **Read-only by default**: Write operations require explicit confirmation (unless auto-ingestion pattern)
3. **Main branch protection**: The repository owner should enable branch protection rules
4. **Audit trail**: All commits include `stoffy:` prefix for traceability

---

## 10. Future Extensions

1. **Bi-directional sync**: Watch for remote changes and notify Stoffy
2. **Debate mode**: Cross-reference thinkers and generate synthetic debates
3. **Graph visualization**: Generate thought connection graphs from `related_thoughts` fields
4. **Semantic search**: Index repository content for semantic retrieval
5. **Multi-repo support**: Extend pattern to other philosophical/personal repositories

---

## Appendix A: Repository Structure Reference

```
chrislemke/philosophy/
|
+-- indices/
|   +-- root.yaml           # Entry point, routing
|   +-- thinkers.yaml       # Philosopher registry
|   +-- themes.yaml         # Theme categories
|   +-- thoughts.yaml       # Active thoughts
|   +-- sources.yaml        # Reference materials
|   +-- templates.yaml      # Template registry
|   +-- rules.yaml          # Behavioral rules
|   +-- memories.yaml       # Memory file index
|
+-- thoughts/
|   +-- consciousness/      # Mind, awareness, qualia
|   +-- existence/          # Being, ontology
|   +-- free_will/          # Agency, determinism
|   +-- knowledge/          # Epistemology
|   +-- computational_philosophy/
|
+-- thinkers/               # 52+ philosopher profiles
|   +-- <name>/
|       +-- profile.md      # Bio, key ideas
|       +-- notes.md        # Personal notes
|       +-- reflections.md  # Extended analysis
|       +-- references.md   # Works, citations
|       +-- *_memory.md     # Human feedback (higher weight)
|
+-- sources/
|   +-- books/
|   +-- articles/
|   +-- lectures/
|
+-- templates/              # Document templates
    +-- thought.md
    +-- thinker_profile.md
    +-- thinker_notes.md
    +-- source.md
```

---

## Appendix B: SKILL.md Template

```markdown
---
name: "Philosophy Repository"
description: "Integrate with chrislemke/philosophy GitHub repository for philosophical thought management. Auto-detects philosophical content (thoughts, thinker references, source mentions) and persists to repository. Triggers on: 'I believe', 'I've been thinking', 'what if', 'wonder whether', '[Philosopher] argued', 'I read [Book]', '@path' syntax."
---

# Philosophy Repository Integration

## What This Skill Does

Connects Stoffy to the `chrislemke/philosophy` GitHub repository for:
1. **Reading**: Fetch philosopher profiles, thoughts, sources
2. **Writing**: Capture new thoughts, notes, reflections
3. **Auto-detection**: Recognize philosophical content in conversation

## Quick Start

### Read a Thinker Profile
"Who is Karl Friston?" or "Tell me about Nietzsche's philosophy"

### Capture a Thought
"I've been thinking about consciousness..." (will offer to save)

### Direct Ingestion
`@thinkers/kant/ New insight about the categorical imperative`

## Prerequisites

- `gh` CLI installed and authenticated
- Access to `chrislemke/philosophy` repository

## Commands

| Command | Example |
|---------|---------|
| Lookup thinker | "What did Hume believe about causation?" |
| List thinkers | "Who are the thinkers in my philosophy repo?" |
| Capture thought | Express a philosophical position |
| Add note | `@thinkers/<name>/ <note>` |
| Create source | "I read [Book] by [Author]..." |

## Detailed Instructions

See [scripts/repo.sh](scripts/repo.sh) for gh CLI operations.
See [config.yaml](config.yaml) for configuration options.
```

---

*Architecture Version: 1.0*
*Last Updated: 2026-01-06*
*Author: Stoffy Hive Mind*
