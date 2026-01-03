---
description: Learn from repository content by providing feedback that creates persistent memories
allowed-tools: Read, Glob, Grep, Bash(ls:*), Bash(file:*), Task, AskUserQuestion
argument-hint: <file or folder path>
---

# Learn from Content: $ARGUMENTS

You are facilitating learning from repository content. Your role is to prepare context and prompt for human feedback, then delegate to the `student` subagent to create persistent memory files.

## Step 1: Parse and Validate Path

Extract the path from `$ARGUMENTS`:
- Remove any leading `@` symbol if present
- Handle paths with spaces (the full argument is the path)
- Resolve relative paths from repository root

**Validation**:
- Use `ls` or `file` to verify the path exists
- Determine if it's a file or folder

**If path doesn't exist**:
```
=== PATH NOT FOUND ===

Could not find: `$ARGUMENTS`

Did you mean one of these?
[Use Glob to find similar paths and suggest alternatives]
```
Then stop.

## Step 2: Detect Content Type

Determine content type based on path pattern:

| Path Pattern | Type | Key |
|--------------|------|-----|
| `debates/*.md` | debate | participants, rounds, outcome |
| `thoughts/**/thought.md` or `thoughts/**/*.md` | thought | theme, status, related_thinkers |
| `thinkers/*/profile.md` | thinker_profile | core_ideas, key_concepts |
| `thinkers/*/notes.md` | thinker_notes | engagement points |
| `thinkers/*/reflections.md` | thinker_reflections | personal insights |
| `thinkers/*/references.md` | thinker_references | cross-references |
| `thinkers/*/` (folder) | thinker_folder | all files |
| `sources/**/*.md` | source | author, title, arguments |
| Other folder | folder | list of files |
| Other file | generic | frontmatter, headings |

## Step 3: Extract Context

Read the content and extract structure based on type:

### For Debates
```yaml
extract:
  - topic (from frontmatter)
  - participants (names and roles)
  - rounds (count)
  - outcome (SYNTHESIS, IMPASSE, etc.)
  - key_sections: [Opening Positions, Dialectical Exchange, Closing Statements, Summary]
  - synthesis_points (from Summary > Areas of Agreement)
  - open_questions (from Summary > Open Questions)
```

### For Thoughts
```yaml
extract:
  - title
  - theme (from path or frontmatter)
  - status (seed, exploring, developing, crystallized, etc.)
  - related_thinkers (from frontmatter)
  - key_insight (first paragraph of content)
  - sections (list of ## headings)
```

### For Thinker Profiles
```yaml
extract:
  - name
  - tradition
  - key_concepts (list)
  - core_ideas (summaries)
  - influences (influenced_by, influenced)
```

### For Thinker Notes/Reflections
```yaml
extract:
  - thinker_name (from parent folder)
  - sections (list of ## headings)
  - key_points (first few bullet points)
```

### For Sources
```yaml
extract:
  - title
  - author
  - type (book, article, lecture)
  - key_arguments (if present)
```

### For Folders
```yaml
extract:
  - folder_path
  - files (list with brief descriptions)
  - common_theme (inferred from folder name)
```

### For Generic Files
```yaml
extract:
  - frontmatter (all YAML fields)
  - sections (list of ## headings)
  - first_paragraph
```

## Step 4: Display Learning Context

Present the extracted context to the user:

```
=== LEARNING CONTEXT ===

Content: <path>
Type: <content_type>

<type-specific summary>

Key Sections:
<list of main sections/headings>

<if debate: synthesis points>
<if thought: related thinkers>
<if thinker: core ideas>

---

```

## Step 5: Prompt for Feedback

Use the AskUserQuestion tool to gather feedback:

```
Ask the user:
"What would you like me to learn about this content?"

Provide type-specific example prompts:
```

**For debates**:
- "The synthesis on X is THE key insight - emphasize this"
- "Round 2 oversimplifies the Markov blanket concept"
- "Missing connection to Helmholtz's unconscious inference"
- "Laozi's response in Round 1 is the strongest argument"

**For thoughts**:
- "The key insight that should be emphasized is..."
- "The connection to X thinker is missing"
- "This contradicts the thought on Y - needs reconciliation"
- "The status should be 'crystallized', not 'seed'"

**For thinkers**:
- "The Active Inference section is oversimplified"
- "Missing: collaboration with Anil Seth on interoception"
- "Birth year is wrong - should be 1844, not 1845"
- "Core idea X is not accurately represented"

**For sources**:
- "The key argument that should be captured is..."
- "This connects strongly to thinker X's ideas on Y"
- "The date/author is incorrect"

**For generic content**:
- "Section X is key, emphasize it"
- "This is wrong: X, should be: Y"
- "Add connection to [related content]"

## Step 6: Invoke Student Agent

Once feedback is received, invoke the student agent with the Task tool:

```
Task(subagent_type: "student")

Prompt:
Learn from the following human feedback about repository content.

PATH: @<original_path>

FEEDBACK:
<user's feedback from Step 5>

CONTEXT:
<summary of extracted context from Step 3>

Process this feedback and create/update the appropriate memory file.
Follow your standard workflow:
1. Classify feedback type(s)
2. Determine confidence level
3. Create or update memory file next to source
4. Update indices/memories.yaml
5. Report what was learned
```

## Step 7: Report Results

After the student agent completes, display a summary:

```
=== LEARNING COMPLETE ===

Source: <path>
Memory: <memory_file_path>

What was learned:
<student agent's summary>

Feedback type(s): <types>
Confidence: <level>

Memory entry added to capture the delta.
```

## Error Handling

| Situation | Response |
|-----------|----------|
| Path not found | Suggest similar paths, stop |
| Empty path | "Please provide a file or folder path" |
| Cannot read file | Report error, suggest checking permissions |
| Student agent fails | Report error, preserve user feedback |

## Important Notes

1. **Always read the full content** before presenting context
2. **Extract YAML frontmatter** when present - it contains rich metadata
3. **Be concise in context display** - focus on structure, not full content
4. **Preserve user's exact words** in feedback passed to student
5. **The delta is what matters** - what's wrong → what's right
6. **Do not modify the source file** - only create memory files
7. **Memory files persist knowledge** for future interactions
