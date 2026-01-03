---
description: Ingest philosophical content from URLs or text, extracting insights and organizing into the repository
allowed-tools: Read, Glob, Grep, Write, Edit, Bash(*), TodoWrite, Task
argument-hint: <url(s) or text content to ingest>
---

# Ingest Philosophical Content: $ARGUMENTS

You are ingesting philosophical content into the repository. Follow this workflow precisely.

## Step 1: Parse Input

Analyze `$ARGUMENTS` to determine input type:

**URL Detection**: Look for patterns matching `https?://\S+`
- If URLs found: Extract all URLs, process each sequentially
- If no URLs: Treat entire input as raw text

**Examples**:
- `/ingest https://example.com/article` → Single URL
- `/ingest https://a.com https://b.com` → Multiple URLs
- `/ingest I've been thinking about free will...` → Raw text

## Step 2: Run Extraction Script

For each input, call `scripts/ingest.py`:

**For URLs** (run once per URL):
```bash
python scripts/ingest.py --url "<url>" --json --plan-only --verbose
```

**For text**:
```bash
python scripts/ingest.py --text "<text>" --json --plan-only --verbose
```

**Parse the JSON output** to extract:
- `metadata.content_type` (thought, source, reflection, notes, thinker)
- `metadata.detected_theme` (life_meaning, consciousness, free_will, morality, existence, knowledge, general)
- `metadata.detected_date`
- `entities.thinkers` (array of explicitly mentioned philosophers)
- `extracted.key_insights` (main arguments/insights)
- `extracted.questions` (philosophical questions found)
- `analysis_context.full_content` (complete content for analysis)
- `analysis_context.philosophical_concepts` (extracted concepts for matching)
- `analysis_context.preliminary_thinkers` (explicitly mentioned thinker slugs)
- `raw_content_preview` (content summary)

## Step 2.5: Philosophical Connection Analysis

**Use the philosophical-analyst agent** to identify deep connections to existing repository content.

### Load Repository Context

Before analysis, gather context:
1. Read `indices/themes.yaml` for theme-thinker mappings
2. Read the "Core Ideas" section from each thinker profile in `thinkers/*/profile.md`
3. List existing thoughts in `thoughts/*/` folders

### Invoke the Philosophical Analyst

Use the Task tool with `subagent_type: "philosophical-analyst"` to analyze connections:

```
Analyze this philosophical content and identify connections to the existing knowledge in this repository.

## Content to Analyze
<content>
{analysis_context.full_content from script output}
</content>

## Extracted Concepts
{analysis_context.philosophical_concepts}

## Preliminary Theme
{analysis_context.preliminary_theme}

## Your Task

1. **Related Thinkers**: Identify which thinkers' ideas resonate with this content.
   - Check ALL 35 thinker profiles in `thinkers/`
   - Match against their Core Ideas, not just explicit mentions
   - Consider conceptual echoes even when thinkers aren't named
   - Rate each as: strong (direct conceptual match), moderate (related ideas), tangential (distant echo)

2. **Related Thoughts**: Identify connections to existing thoughts.
   - Check all thoughts in `thoughts/*/` folders
   - Consider thematic and conceptual overlap
   - Only include if thoughts actually exist

For each connection, provide:
- The slug/path
- Strength rating (strong/moderate/tangential)
- 1-2 sentence reasoning explaining the connection

## Output Format

Return a YAML structure:
```yaml
related_thinkers:
  - slug: jean_paul_sartre
    name: Jean-Paul Sartre
    strength: strong
    reason: "Content echoes existentialist themes of radical freedom and responsibility"
  - slug: aristotle
    name: Aristotle
    strength: moderate
    reason: "Discussion of virtue and character development aligns with virtue ethics"

related_thoughts:
  - path: thoughts/life_meaning/2025-01-15_meaning_through_action/
    strength: moderate
    reason: "Both explore how action creates meaning"

analysis_summary: "Brief 1-2 sentence summary of the content's philosophical significance"
```
```

### Parse Analyst Output

Extract from the analyst's response:
- `related_thinkers[]` - array of thinker connections with strength and reasoning
- `related_thoughts[]` - array of thought connections with strength and reasoning
- `analysis_summary` - philosophical summary

**Merge with preliminary thinkers**: Combine analyst results with `entities.thinkers` from Step 2, avoiding duplicates.

## Step 3: Create Files Using Templates

Based on `content_type`, create the appropriate file using analyst-enhanced data:

### For `thought` or `reflection`:
1. Read template: `templates/thought.md`
2. Generate slug from first line (max 30 chars, lowercase, underscores)
3. Create folder: `thoughts/<theme>/<date>_<slug>/`
4. Create file: `thoughts/<theme>/<date>_<slug>/thought.md`
5. Fill template placeholders:
   - `{{thought_title}}` → First line or extracted title
   - `{{theme}}` → Detected theme
   - `{{date: YYYY-MM-DD}}` → Today's date or detected date
   - `{{what_triggered_this_thought}}` → First 500 chars of content
   - `related_thinkers: [<slugs>]` → **From analyst output**, list of thinker slugs
   - `related_thoughts: [<paths>]` → **From analyst output**, list of thought paths
6. Fill "Philosophical Connections" section with analyst reasoning (see Step 3.5)

### For `source`:
1. Read template: `templates/source.md`
2. Generate slug from title (max 40 chars)
3. Create file at: `sources/books/<slug>.md`
4. Fill template with extracted metadata
5. Add `related_thinkers` from analyst output

### For `notes` or unclassified:
1. Store in `texts/<date>_<source_slug>.md`
2. Add YAML frontmatter with date, source URL, and related_thinkers

## Step 3.5: Populate Philosophical Connections Section

For thoughts/reflections, add the "Philosophical Connections" section after "Related Ideas":

```markdown
## Philosophical Connections

### Thinker Connections
<!-- Identified by philosophical analysis -->
{{#each related_thinkers}}
- **[[thinkers/{{slug}}/profile|{{name}}]]** ({{strength}}): {{reason}}
{{/each}}

### Thought Connections
<!-- Identified by philosophical analysis -->
{{#each related_thoughts}}
- **[[{{path}}]]** ({{strength}}): {{reason}}
{{/each}}

### Analysis Summary
{{analysis_summary}}
```

Replace the `{{#each}}` placeholders with actual markdown content from the analyst output.

## Step 4: Handle Thinker References (Bidirectional Linking)

For EACH thinker in the merged `related_thinkers` list (from analyst + entities.thinkers):

1. Check if `thinkers/<slug>/` folder exists
2. If exists:
   - Read `thinkers/<slug>/references.md`
   - Append new reference entry to the table:
   ```markdown
   | <today's date> | <strength> | <path to new file> | <analyst reasoning> |
   ```
   - This creates **bidirectional links**:
     - Thought → Thinker (via `related_thinkers` array in frontmatter)
     - Thinker → Thought (via `references.md` table entry)
3. If not exists:
   - Note in output that thinker profile could be created
   - Do NOT auto-create profiles (user should explicitly request)

## Step 5: Update Indices

After creating files, update relevant indices with connection data:

### If thought created → Update `indices/thoughts.yaml`:
```yaml
thoughts:
  <slug>:
    title: "<title>"
    theme: <theme>
    status: seed
    path: thoughts/<theme>/<slug>/
    related_thinkers: [<slugs from analyst>]  # NEW: connection data
    created: <YYYY-MM-DD>
```

### If source created → Update `indices/sources.yaml`:
```yaml
sources:
  <slug>:
    title: "<title>"
    type: <book|article|lecture>
    path: sources/books/<slug>.md
    related_thinkers: [<slugs from analyst>]  # NEW: connection data
```

### Always:
- Update `meta.last_updated` in modified index
- Add changelog entry: `"Added <type>: <title> with connections to <N> thinkers"`

## Step 6: Output Summary

Display a comprehensive summary:

```
=== INGEST COMPLETE ===

Input: <url or "raw text">
Content Type: <type>
Theme: <theme>
Analysis: <analysis_summary from analyst>

FILES CREATED:
  + thoughts/consciousness/2025-12-25_nature_of_qualia/thought.md

PHILOSOPHICAL CONNECTIONS IDENTIFIED:
  Strong:
    ⦿ Jean-Paul Sartre - "Core existentialist themes of radical freedom"
    ⦿ David Chalmers - "Directly addresses the hard problem"
  Moderate:
    ◉ Aristotle - "Virtue ethics undertones in character discussion"
  Tangential:
    ○ Camus - "Echoes of absurdist acceptance"

THINKER REFERENCES UPDATED:
  ~ thinkers/jean_paul_sartre/references.md
  ~ thinkers/david_chalmers/references.md
  ~ thinkers/aristotle/references.md
  ~ thinkers/albert_camus/references.md

INDICES UPDATED:
  ~ indices/thoughts.yaml

INSIGHTS EXTRACTED:
  • "<key insight 1>"
  • "<key insight 2>"

QUESTIONS FOUND:
  ? "<philosophical question 1>"
```

## Important Notes

1. **Always use the philosophical-analyst agent** for connection analysis
2. **Always use templates** from `templates/` folder when creating new files
3. **Use ISO 8601 dates** (YYYY-MM-DD) everywhere
4. **Follow naming conventions**: lowercase_with_underscores
5. **Do not ask for confirmation** - just process and report results
6. **Process multiple URLs sequentially** if multiple are provided
7. **Update indices immediately** after file creation
8. **Create bidirectional links** - both in new file AND in thinker references.md
9. **Include connection reasoning** in both the file and the summary output
