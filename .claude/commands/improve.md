---
description: Apply improvements from memory files to project files with Ultrathinking methodology
allowed-tools: Read, Glob, Grep, Write, Edit, Bash(*), TodoWrite, Task, AskUserQuestion
argument-hint: <memory_file_path>
---

# Improve from Memory: $ARGUMENTS

You are applying improvements from a memory file to project files using the **Ultrathinking** methodology.

**ULTRATHINK** about every aspect of this task. This command requires careful analysis, planning, and user confirmation before each change.

---

## Step 1: Parse & Validate Input

### 1.1 Check for Arguments

If `$ARGUMENTS` is empty or contains only whitespace:

```
=== IMPROVE COMMAND ERROR ===

Missing required argument: memory file path

Usage:
  /improve <memory_file_path>

Examples:
  /improve debates/2025-12-30_predictive_brain_karl_friston_vs_laozi_memory.md
  /improve thinkers/karl_friston/profile_memory.md
  /improve .claude/commands/debate_memory.md

The memory file must:
- End with `_memory.md`
- Exist in the repository
- Contain human feedback about project files

To see available memory files, check:
  indices/memories.yaml
```
**STOP** - do not proceed.

### 1.2 Validate Memory File Path

Extract the path from `$ARGUMENTS`:
- Remove leading/trailing whitespace
- Remove leading `@` symbol if present
- Handle paths with spaces

**Validation Checks:**

```bash
test -f "$ARGUMENTS" && echo "File exists" || echo "NOT FOUND"
```

1. **File must exist** - if not:
   ```
   === IMPROVE COMMAND ERROR ===

   Memory file not found: `$ARGUMENTS`

   Did you mean one of these?
   [Use Glob to find similar *_memory.md files and suggest alternatives]
   ```
   **STOP** - do not proceed.

2. **File must end with `_memory.md`** - if not:
   ```
   === IMPROVE COMMAND ERROR ===

   Invalid file type: `$ARGUMENTS`

   The /improve command only processes memory files (*_memory.md).
   These files contain human feedback created by the /learn command.

   If this file contains feedback you want to apply, rename it to:
     ${ARGUMENTS%.md}_memory.md
   ```
   **STOP** - do not proceed.

---

## Step 2: Read Memory File

### 2.1 Load Content

```
Read: $ARGUMENTS (full file)
```

### 2.2 Parse Structure

Extract from the memory file:

**YAML frontmatter (if present):**
```yaml
source: "path/to/original/file.md"  # Primary source file
type: memory
created: "YYYY-MM-DD"
feedback_count: N
```

**Feedback entries:**
- Look for `## Human Feedback` or `## Entries` sections
- Each entry has: Issue, Root Cause, Recommendations, Priority, Status (if previously processed)

### 2.3 Check for Already-Applied Entries

If feedback entries have `status: applied`:
```
Note: Some feedback in this file has already been applied.
Only processing unapplied entries...
```

Skip entries with `status: applied` in subsequent steps.

---

## Step 3: Extract File References

### 3.1 Detection Patterns

Scan the memory file content for file references using these patterns:

| Pattern | Example | Regex Hint |
|---------|---------|------------|
| Backtick paths | `` `path/to/file.md` `` | `` `([^`]+\.md)` `` |
| Source field | `Source: \`path/to/file.md\`` | `Source:\s*\`?([^\`\n]+)` |
| Related links | `- \`path/to/file.md\` - desc` | `- \`([^`]+)\`` |
| YAML source | `source: "path/to/file.md"` | `source:\s*["']?([^"'\n]+)` |
| Inline paths | `the file at path/to/file.md` | Common path patterns |

### 3.2 Validate References

For each extracted path:

```bash
test -f "<path>" && echo "EXISTS" || echo "NOT FOUND"
```

Build a reference list:
```yaml
references:
  - path: "path/to/file.md"
    exists: true
    source_file: true  # If this is the memory file's source
  - path: ".claude/commands/debate.md"
    exists: true
    mentioned_in: "Root Cause section"
```

### 3.3 Group by File

Group all feedback that applies to each referenced file:

```yaml
file_feedback_map:
  ".claude/commands/debate.md":
    - issue: "Agents talking past each other"
      section: "Root Cause: Debate Command Limitations"
      recommendations:
        - "Add Argument Extraction step"
        - "Require understanding verification"
      priority: HIGH
```

### 3.4 Handle Edge Cases

**No file references found:**
```
=== IMPROVE: NO ACTIONABLE REFERENCES ===

Memory file: $ARGUMENTS

This memory file doesn't reference any project files that need improvement.

The feedback may be:
- General observations about the source content
- Comments without specific file targets
- Already-applied improvements

No changes will be made.
```
**STOP** - do not proceed.

**Referenced file doesn't exist:**
```
Warning: Referenced file not found: `<path>`
         Skipping this reference...
```
Continue with other references.

---

## Step 4: Analyze Context Per File

### 4.1 Extract Surrounding Context

For each file reference, extract the paragraph/section context to understand:
- What is the issue or problem?
- What is recommended?
- What is the priority?
- What type of change is needed?

### 4.2 Classify Change Type

| Type | Indicators | Approach |
|------|------------|----------|
| **Correction** | "wrong", "error", "should be" | Edit specific lines |
| **Addition** | "missing", "add", "include" | Insert new content |
| **Restructure** | "rewrite", "restructure", "refactor" | Major rewrite |
| **Improvement** | "improve", "enhance", "better" | Modify existing |

### 4.3 Read Target Files

For each file that needs changes:
```
Read: <target_file_path>
```

Understand the current structure, find the location for changes.

---

## Step 5: Ultrathink & Plan Fixes

### 5.1 ULTRATHINK Process

For each file with feedback, engage in deep analysis:

**Analysis Questions:**
1. What exactly is the problem described in the feedback?
2. Where in the target file does this problem manifest?
3. What is the minimal change that addresses the issue?
4. What are the potential side effects?
5. What is the confidence level for this fix?

### 5.2 Formulate Specific Changes

For each fix, determine:
- **Location**: Line numbers or section names
- **Change Type**: Edit, Insert, Replace, Delete
- **Content**: Exact text to add/change
- **Impact**: Scope of affected functionality

### 5.3 Estimate Complexity

Rate each fix:
- **Low**: Single edit, few lines, obvious change
- **Medium**: Multiple edits, structural change, moderate impact
- **High**: Major rewrite, architectural change, broad impact

---

## Step 6: Create Todo List

Use TodoWrite to track the improvement process:

```
TodoWrite:
  1. [completed] Parse memory file: $ARGUMENTS
  2. [completed] Extract file references
  3. [in_progress] Review fix for <file1>
  4. [pending] User confirmation for <file1>
  5. [pending] Apply fix to <file1>
  6. [pending] Review fix for <file2>
  7. [pending] User confirmation for <file2>
  8. [pending] Apply fix to <file2>
  9. [pending] Update memory file with applied status
  10. [pending] Report results
```

---

## Step 7: Present Analysis to User

Display the analysis results:

```
=== IMPROVE: MEMORY FILE ANALYSIS ===

Memory File: $ARGUMENTS
Created: <date>
Feedback Entries: <N>
Previously Applied: <M>

---

## FILE REFERENCES FOUND

| # | File | Exists | Issues |
|---|------|--------|--------|
| 1 | debates/..._laozi.md | ✓ | Source file |
| 2 | .claude/commands/debate.md | ✓ | 4 issues |

---

## IMPROVEMENT PLAN

### File: .claude/commands/debate.md
Priority: HIGH (from memory file)
Change Type: Addition/Improvement

Issues to Address:
1. No Argument Extraction step
2. Position Lock Bias
3. Pre-formulated responses
4. No validation feedback loop

Proposed Fixes:
1. Add "Argument Extraction" step after Step 3.1
2. Modify agent prompts to require understanding verification
3. Add "I understand you to claim..." requirement

Estimated Changes: ~50 lines added
Complexity: MEDIUM

---

Proceeding to fix proposals...
```

---

## Step 8: Confirm Each Fix

### 8.1 Present Fix Proposal

For each proposed fix, present to user:

```
=== FIX PROPOSAL #<N> of <TOTAL> ===

Target: <file_path>
Location: <section or line numbers>

Issue (from memory):
> "<quoted feedback text>"

Proposed Change:
<description of what will change>

Exact Edit:
```
[Show the specific edit - old text vs new text]
```

Impact: <LOW | MEDIUM | HIGH>
Confidence: <HIGH | MEDIUM | LOW>

---
```

### 8.2 Ask for Confirmation

Use AskUserQuestion tool:

```
AskUserQuestion:
  question: "Apply this fix to <file_path>?"
  header: "Fix #N"
  options:
    - label: "Apply this fix"
      description: "Proceed with the proposed change (Recommended)"
    - label: "Skip this fix"
      description: "Do not apply this change, move to next"
    - label: "Show me more context"
      description: "Display more of the target file before deciding"
    - label: "Stop processing"
      description: "Exit without applying remaining fixes"
  multiSelect: false
```

### 8.3 Handle User Response

**"Apply this fix"**: Proceed to Step 9 for this fix
**"Skip this fix"**: Log as skipped, move to next fix
**"Show me more context"**: Display ±20 lines around the change location, then re-ask
**"Stop processing"**: Jump to Step 11 (Report Results)

---

## Step 9: Implement Fixes

### 9.1 Apply Changes

For approved fixes:

**For targeted edits:**
```
Edit(
  file_path: "<target_file>",
  old_string: "<existing text>",
  new_string: "<replacement text>"
)
```

**For insertions:**
```
Edit(
  file_path: "<target_file>",
  old_string: "<anchor text>",
  new_string: "<anchor text>\n\n<new content>"
)
```

**For major restructures:**
Use Write tool with complete new content (after reading and modifying).

### 9.2 Verify Success

After each edit:
- Confirm tool returned success
- Optionally re-read file to verify change

### 9.3 Update Todo Progress

```
TodoWrite:
  [completed] Apply fix to <file>
```

---

## Step 10: Update Memory File

### 10.1 Mark Applied Entries

For each successfully applied fix, update the memory file to mark it as applied.

**Add after the feedback entry:**
```markdown
**Status**: applied
**Applied Date**: YYYY-MM-DD
```

**Or if using YAML-style:**
```yaml
status: applied
applied_date: "YYYY-MM-DD"
```

### 10.2 Apply Edit

```
Edit(
  file_path: "$ARGUMENTS",  # The memory file
  old_string: "<original feedback section>",
  new_string: "<feedback section with status: applied>"
)
```

---

## Step 11: Report Results

### 11.1 Display Summary

```
=== IMPROVEMENT COMPLETE ===

Memory File: $ARGUMENTS

---

## APPLIED FIXES

| # | File | Fix Description | Status |
|---|------|-----------------|--------|
| 1 | .claude/commands/debate.md | Added Argument Extraction step | ✓ Applied |
| 2 | .claude/commands/debate.md | Added understanding verification | ✓ Applied |

---

## SKIPPED FIXES

| # | File | Reason |
|---|------|--------|
| 3 | debates/..._laozi.md | User chose to skip |

---

## MEMORY FILE UPDATED

Applied entries have been marked with:
- status: applied
- applied_date: YYYY-MM-DD

To re-process this memory file, remove the `status: applied` markers.

---

Files Modified:
- .claude/commands/debate.md (2 edits)
- $ARGUMENTS (status updates)

🧠 Ultrathinking applied throughout this improvement process.
```

---

## Error Handling

| Situation | Response |
|-----------|----------|
| Memory file not found | Display error with suggestions, stop |
| Invalid file type | Display error explaining _memory.md requirement, stop |
| No file references | Report "nothing to improve", stop |
| Referenced file missing | Warn and skip that reference |
| Edit fails | Report error, ask if user wants to continue |
| User stops early | Report partial results |

---

## Important Notes

1. **ALWAYS ULTRATHINK** - This command requires deep analysis at every stage
2. **ALWAYS ASK CONFIRMATION** - Never apply changes without explicit user approval
3. **TRACK PROGRESS** - Use TodoWrite throughout to show progress
4. **UPDATE MEMORY FILE** - Mark applied entries to prevent re-processing
5. **PRESERVE CONTEXT** - Keep surrounding text intact when editing
6. **REPORT EVERYTHING** - Clear summary of what was done and what was skipped
7. **HANDLE EDGE CASES** - Gracefully handle missing files, empty feedback, etc.
8. **ONE FIX AT A TIME** - Present and confirm each fix individually
9. **SHOW EXACT CHANGES** - User should see precisely what will change
10. **NO SILENT FAILURES** - Report all errors and ask how to proceed

---

## Example Session

```
User: /improve debates/2025-12-30_predictive_brain_karl_friston_vs_laozi_memory.md

Claude:
=== IMPROVE: MEMORY FILE ANALYSIS ===

Memory File: debates/2025-12-30_predictive_brain_karl_friston_vs_laozi_memory.md
Created: 2025-12-31
Feedback Entries: 1
Previously Applied: 0

## ULTRATHINKING...

Reading memory file and extracting context...

## FILE REFERENCES FOUND

| # | File | Exists | Role |
|---|------|--------|------|
| 1 | debates/2025-12-30_predictive_brain_karl_friston_vs_laozi.md | ✓ | Source |
| 2 | .claude/commands/debate.md | ✓ | Needs fixes |

## IMPROVEMENT PLAN

### File: .claude/commands/debate.md
Priority: HIGH
Issues: 4 identified problems in debate command

Proposed Fixes:
1. Add Argument Extraction step requiring agents to summarize opponent claims
2. Add understanding verification: "I understand you to claim..."
3. Reduce position-lock bias toward genuine engagement

Proceeding to individual fix proposals...

---

=== FIX PROPOSAL #1 of 3 ===

Target: .claude/commands/debate.md
Location: After Step 3.1 (Agent 1 Opening)

Issue (from memory):
> "No Argument Extraction Step: Agents receive opponent's response but
>  aren't required to summarize what was claimed"

Proposed Change:
Add new step 3.1.5 - Argument Extraction step that requires:
- Agent to state "I understand you to claim that: [specific claim]"
- List 2-3 key points before formulating response

[User confirms: "Apply this fix"]

Applying edit to .claude/commands/debate.md...
✓ Edit successful

[Continue with remaining fixes...]

=== IMPROVEMENT COMPLETE ===

Applied: 3 fixes
Skipped: 0 fixes
Memory file updated with applied status

🧠 Ultrathinking complete.
```
