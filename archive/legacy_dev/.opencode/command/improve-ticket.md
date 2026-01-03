---
description: Improve a JIRA ticket description with an LLM-optimized implementation guide
subtask: true
---

# Improve Ticket

Enhance a JIRA ticket with a comprehensive, LLM-optimized implementation guide. This command gathers context from JIRA, Confluence, local files, and GitHub to generate detailed implementation instructions that can be directly consumed by AI coding assistants.

**Usage:**
```
/improve-ticket <TICKET_ID> [optional user comment]
```

**Examples:**
```
/improve-ticket FML-247
/improve-ticket FML-247 Focus on the CrewAI pipeline changes
/improve-ticket FPRO-896 The backend team needs this by Friday
```

---

## Step 1: Parse Arguments

Extract the ticket ID from `$ARGUMENTS`:
- First word should be the ticket ID (e.g., `FML-247`, `FPRO-896`, `DS-1123`)
- Remaining text (if any) is the optional user comment

**Validation:**
- Ticket ID must match pattern: `(DS|FML|FLUG|FLIGHTS|FIOS|FPRO|BI|HD)-\d+`
- If invalid or missing, show usage and exit

Store:
- `$TICKET_ID` = extracted ticket ID (uppercase)
- `$USER_COMMENT` = remaining text (may be empty)

---

## Step 2: Gather Atlassian Context

Use the consolidated Atlassian client to gather all JIRA context in one call:

```bash
python .opencode/tool/atlassian_client.py jira-gather-context $TICKET_ID --include-confluence
```

**Store the JSON output as `$ATLASSIAN_CONTEXT`.**

**If `error` field is present:**
```
Error: Could not fetch ticket $TICKET_ID from JIRA.
Reason: [error message]
```
Exit the command.

**Display ticket summary:**
```
Fetching ticket $TICKET_ID from JIRA...
✓ $TICKET_ID: [ticket.summary]
  Status: [ticket.status] | Assignee: [ticket.assignee] | Priority: [ticket.priority]
  Epic: [ticket.epic_key] - [ticket.epic_summary]
  Linked Issues: [linked_issues count]
  Epic Siblings: [epic_children count]
  [if confluence_pages] Confluence Pages: [confluence_pages count]
```

---

## Step 3: Find Local Context

```bash
python scripts/ticket_improver.py local-context $TICKET_ID
```

**Store the JSON output as `$LOCAL_CONTEXT`.**

**Display what was found:**
```
Finding local context...
[if local_ticket_file] ✓ Found: Local ticket file at [path]
[if epic] ✓ Found: Epic [epic]
[if project] ✓ Found: Project at [project.folder]
[if related_tickets] ✓ Found: [count] related tickets
```

---

## Step 4: Ensure Repository is Available Locally

```bash
python scripts/ticket_improver.py ensure-repo $TICKET_ID --org invia-flights
```

**Store the JSON output as `$REPO_ENSURE`.**

### Case A: Repository already exists locally

If `already_exists` is `true`:
```
Checking local repository...
✓ Repository found at [local_repo_path]
```
Set `$LOCAL_REPO_PATH` = `local_repo_path`

### Case B: Repository cloned successfully

If `cloned` is `true`:
```
Checking local repository...
✓ Cloned [repository] to [local_repo_path]
```
Set `$LOCAL_REPO_PATH` = `local_repo_path`

### Case C: No project found

If `error` contains "No project found":
```
Checking local repository...
⚠ No project folder found for this ticket.

The ticket must be associated with a project in project_management/ that has a
**Repository**: `repo-name` field in its project.md file.

Options:
  1. Enter project folder path manually (e.g., project_management/my-project)
  2. Skip repository context

Select an option (1-2):
```

If option 1: Ask for project path, then verify project.md exists and has repository field
If option 2: Set `$LOCAL_REPO_PATH` to `null`

### Case D: No repository defined in project

If `error` contains "No repository defined":
```
Checking local repository...
⚠ No repository defined in project: [project_folder]

Please add a **Repository**: `repo-name` line to the project.md file.

Options:
  1. Enter repository name manually
  2. Skip repository context

Select an option (1-2) or enter a repository name:
```

If option 1 or repository name entered:
- Update the project.md to add the repository field
- Re-run ensure-repo command
If option 2: Set `$LOCAL_REPO_PATH` to `null`

### Case E: Clone failed

If `error` contains "Failed to clone":
```
Checking local repository...
✗ Failed to clone repository: [error]

This could mean:
- The repository doesn't exist or was renamed
- You don't have access to the repository
- GitHub CLI is not authenticated (run: gh auth login)

Options:
  1. Enter a different repository name
  2. Skip repository context

Select an option (1-2) or enter a repository name:
```

---

## Step 5: Get Repository Context (if available)

**If `$LOCAL_REPO_PATH` is not null:**

```bash
python scripts/ticket_improver.py local-repo-context $LOCAL_REPO_PATH
```

**Store the JSON output as `$REPO_CONTEXT`.**

**Display summary:**
```
Getting repository context...
✓ README loaded ([readme_file])
✓ Dependencies: [count] packages from [dependencies[0].file]
✓ Structure: [count] files at root level
[if has_opencode] ✓ Found opencode/Claude configuration
```

**If `$LOCAL_REPO_PATH` is null:**
```
Proceeding without repository context...
```
Set `$REPO_CONTEXT` to empty object.

---

## Step 6: Invoke Ticket Improver Agent

Prepare the context object:

```json
{
  "ticket": {
    "ticket_id": "$ATLASSIAN_CONTEXT.ticket.key",
    "summary": "$ATLASSIAN_CONTEXT.ticket.summary",
    "description": "$ATLASSIAN_CONTEXT.ticket.description",
    "status": "$ATLASSIAN_CONTEXT.ticket.status",
    "assignee": "$ATLASSIAN_CONTEXT.ticket.assignee",
    "priority": "$ATLASSIAN_CONTEXT.ticket.priority",
    "type": "$ATLASSIAN_CONTEXT.ticket.type",
    "labels": "$ATLASSIAN_CONTEXT.ticket.labels",
    "epic_key": "$ATLASSIAN_CONTEXT.ticket.epic_key",
    "epic_summary": "$ATLASSIAN_CONTEXT.ticket.epic_summary",
    "project_key": "$ATLASSIAN_CONTEXT.ticket.project_key",
    "url": "$ATLASSIAN_CONTEXT.ticket.url"
  },
  "atlassian_context": {
    "epic": "$ATLASSIAN_CONTEXT.epic",
    "epic_children": "$ATLASSIAN_CONTEXT.epic_children",
    "linked_issues": "$ATLASSIAN_CONTEXT.linked_issues",
    "confluence_pages": "$ATLASSIAN_CONTEXT.confluence_pages"
  },
  "local_context": {
    "project": "$LOCAL_CONTEXT.project",
    "epic": "$LOCAL_CONTEXT.epic",
    "related_tickets": "$LOCAL_CONTEXT.related_tickets"
  },
  "repo_context": {
    "repository": "$REPO_ENSURE.repository",
    "local_repo_path": "$LOCAL_REPO_PATH",
    "readme": "$REPO_CONTEXT.readme",
    "dependencies": "$REPO_CONTEXT.dependencies",
    "file_structure": "$REPO_CONTEXT.file_structure",
    "primary_language": "$REPO_CONTEXT.primary_language",
    "has_opencode": "$REPO_CONTEXT.has_opencode"
  },
  "user_comment": "$USER_COMMENT"
}
```

**Invoke the `ticket-improver` subagent** with this context.

The agent will:
1. Analyze the ticket and context
2. Use Context7 MCP to look up relevant package documentation
3. Optionally search the web for implementation patterns
4. Generate a unified output with:
   - **Implementation Guide** with inline code blocks
   - **Witty Comment** for the JIRA ticket

**Display progress:**
```
Generating implementation guide...
[agent will show its progress]
```

**The agent should return:**

### Output 1: Implementation Guide (`$IMPLEMENTATION_GUIDE`)

This goes in the JIRA ticket description. It MAY contain code blocks - the ADF converter handles them correctly.

Structure:
- AI-Enhanced Implementation Guide header
- Understanding the Task
- Technical Context
- Implementation Steps (with code blocks)
- Key Dependencies (table)
- Developer Hints
- Files to Modify (table)
- Verification checklist

### Output 2: Witty Comment (`$WITTY_COMMENT`)

A short, funny comment starting with "🤖 OpenAssistant enhanced this ticket description."

---

## Step 7: Review and Confirm

Display the generated content for review:

```
══════════════════════════════════════════════════════════════════
PROPOSED IMPROVEMENT FOR $TICKET_ID
══════════════════════════════════════════════════════════════════

$IMPLEMENTATION_GUIDE

══════════════════════════════════════════════════════════════════

COMMENT TO BE ADDED:

$WITTY_COMMENT

══════════════════════════════════════════════════════════════════

Actions:
1. Update JIRA ticket description with implementation guide
2. Add witty comment to ticket

Proceed? (y/n/edit):
```

**Handle user response:**

- **`y` or `yes`**: Continue to Step 8
- **`n` or `no`**:
  ```
  Cancelled. No changes made to $TICKET_ID.
  ```
  Exit the command.
- **`edit`**: Allow user to provide edits, then regenerate or modify

---

## Step 8: Update JIRA and Save Local Backup

### Step 8a: Write content to temp file

Write `$IMPLEMENTATION_GUIDE` to a temp file (avoids shell escaping issues):

```bash
# Write implementation guide to temp file
cat > /tmp/${TICKET_ID}_guide.md << 'EOF'
$IMPLEMENTATION_GUIDE
EOF
```

### Step 8b: Update JIRA Ticket Description

```bash
python .opencode/tool/atlassian_client.py jira-update-description $TICKET_ID \
    --file /tmp/${TICKET_ID}_guide.md
```

**Store the JSON output as `$UPDATE_RESULT`.**

**If `error` field is present:**
```
Error: Failed to update $TICKET_ID
Reason: [error]

The generated guide was NOT saved to JIRA.
Would you like to save it locally instead? (y/n):
```

If yes, save to `tickets/$TICKET_ID_improved.md`.
Exit after handling error.

**If successful:**
```
✓ JIRA ticket description updated
  URL: [url]
```

### Step 8c: Add Witty Comment to JIRA

```bash
python .opencode/tool/atlassian_client.py jira-add-comment $TICKET_ID \
    --content "$WITTY_COMMENT"
```

**Store the JSON output as `$COMMENT_RESULT`.**

**If `error` field is present:**
```
Warning: Failed to add comment: [error]
(Ticket description was still updated successfully)
```

**If successful:**
```
✓ Comment added to ticket
```

### Step 8d: Save Local Backup

Always save a local backup of the generated content:

```bash
# Save to tickets folder
cat > tickets/${TICKET_ID}_improved.md << 'EOF'
# Implementation Guide for $TICKET_ID

Generated: $(date -Iseconds)
JIRA URL: $ATLASSIAN_CONTEXT.ticket.url

---

$IMPLEMENTATION_GUIDE
EOF
```

### Step 8e: Display Final Summary

```
══════════════════════════════════════════════════════════════════
✓ Ticket $TICKET_ID updated successfully!
══════════════════════════════════════════════════════════════════

JIRA Ticket: [jira_url]
Local Backup: tickets/${TICKET_ID}_improved.md

The implementation guide has been appended to the ticket description.
```

### Step 8f: Cleanup

```bash
rm -f /tmp/${TICKET_ID}_guide.md
```

---

## Error Handling

### JIRA Connection Failed
```
Error: Cannot connect to JIRA.
Please check:
- ATLASSIAN_URL, ATLASSIAN_USERNAME, ATLASSIAN_API_TOKEN in .env
- Network connectivity to Atlassian

You can try:
  python .opencode/tool/atlassian_client.py jira-issue $TICKET_ID
to diagnose the issue.
```

### GitHub CLI Not Available
```
Warning: GitHub CLI (gh) not found or not authenticated.
Repository context will not be available.

To enable GitHub integration:
1. Install gh: brew install gh
2. Authenticate: gh auth login

Proceeding with JIRA and local context only...
```

### Invalid Ticket Format
```
Error: Invalid ticket ID format: [input]

Expected format: PREFIX-NUMBER
Valid prefixes: DS, FML, FLUG, FLIGHTS, FIOS, FPRO, BI, HD

Examples:
  /improve-ticket FML-247
  /improve-ticket FPRO-896
```

---

## Notes

- The command preserves the original JIRA description and appends the new guide
- A horizontal rule (`----`) separates the original from the addition
- The agent may use Context7 MCP for package documentation
- The agent may use web search for implementation patterns
- All generated content is reviewed before updating JIRA
- **Single unified output** with inline code blocks (no separate Confluence page)
- **Confluence is READ-ONLY** - used only to gather context, never modified
- File-based content passing (`--file`) is used to avoid shell escaping issues with complex markdown
- A local backup is always saved to `tickets/$TICKET_ID_improved.md`
- Check for `error` field in JSON responses (not `success: false`)
