---
description: Extract and store information from text, files, or folders into repository
subtask: true
---

# Ingest Command

Automatically extract and store **ALL relevant information** from text input into the appropriate repository files. This command processes text to identify people, tickets, projects, ideas, action items, decisions, risks, dates, technical details, and more.

**Core Principle: It is better to save too much than too little data.**

## Usage

```
/ingest <file_path>           # Process a single file
/ingest <folder_path>         # Process all text files in a folder
/ingest "<text content>"      # Process direct text input
/ingest <url>                 # Fetch and process content from a URL
/ingest <url1> <url2> ...     # Fetch and merge content from multiple URLs
```

## Examples

```bash
# Process meeting notes from a file
/ingest ~/Downloads/meeting_notes.txt

# Process all files in a folder (recursively)
/ingest ~/Documents/imported_notes/

# Process direct text
/ingest "Had a call with Stefan Wagner about FLIGHT-250. Decided to use GPT-4 for the chatbot. TODO: Alex to deploy to staging by Friday."

# Process a web page (with or without https://)
/ingest https://docs.example.com/api-guide
/ingest fluege.de/about

# Process a Confluence page (uses Atlassian API, not scraping)
/ingest https://invia.atlassian.net/wiki/spaces/FML/pages/12345678/Page-Title

# Process a JIRA ticket (uses Atlassian API, not scraping)
/ingest https://invia.atlassian.net/browse/FML-247

# Process MULTIPLE URLs at once (merged into single extraction)
/ingest https://invia.atlassian.net/wiki/spaces/FML/pages/123/Page1 https://invia.atlassian.net/wiki/spaces/FML/pages/456/Page2
```

---

## Step 1: Determine Input Type and Infer Source

Parse `$ARGUMENTS` to determine input type:

1. **If input contains multiple URLs** (space-separated URLs): Use `--urls` mode
2. **If input looks like a single URL**: Use `--url` mode
3. **If path exists and is a file**: Use `--file` mode
4. **If path exists and is a directory**: Use `--folder --recursive` mode
5. **Otherwise**: Treat as direct text using `--text` mode

### Source Inference (CRITICAL)

Before processing, **infer the original source** of the information to determine proper tagging and file placement:

| Source Indicators | Inferred Source | Tags to Add | Primary Storage |
|-------------------|-----------------|-------------|-----------------|
| Atlassian URL, JIRA patterns | `jira` | `jira`, `ticket` | `tickets/` |
| Confluence URL, wiki patterns | `confluence` | `confluence`, `documentation` | Depends on content |
| "From:", "To:", "Subject:" | `email` | `email`, `communication` | Person notes |
| "meeting", "call", "sync", participants | `meeting` | `meeting`, `calendar` | `communication/meetings/` |
| Slack URL, channel mentions | `slack` | `slack`, `communication` | Person notes |
| "standup", "daily", "weekly update" | `standup` | `standup`, `status` | Project progress |
| Code blocks, technical patterns | `technical` | `technical`, `code` | Project or ticket |
| "idea", "proposal", "POC" | `brainstorm` | `idea`, `innovation` | `idea_development/` |
| File path ending in `.md`, `.txt` | `document` | `notes` | Depends on content |
| Generic web URL | `web` | `external`, `reference` | Depends on content |

**Store the inferred source as `$SOURCE_TYPE` for use in file operations and tagging.**

---

## Step 2: Run Python Extraction Script

Execute the extraction script with appropriate flags:

**For multiple URLs input:**
```bash
python scripts/ingest.py --urls $URL1 $URL2 $URL3 --json --pretty
```

**For single URL input:**
```bash
python scripts/ingest.py --url "$ARGUMENTS" --json --pretty
```

**For file input:**
```bash
python scripts/ingest.py --file "$ARGUMENTS" --json --pretty
```

**For folder input:**
```bash
python scripts/ingest.py --folder "$ARGUMENTS" --recursive --json --pretty
```

**For text input:**
```bash
python scripts/ingest.py --text "$ARGUMENTS" --json --pretty
```

**Store the JSON output as `$EXTRACTION_RESULT`.**

If the script fails, report the error and exit.

---

## Step 3: Display Initial Summary

Show the user what was detected:

```
╔══════════════════════════════════════════════════════════════════╗
║                    EXTRACTION COMPLETE                            ║
╠══════════════════════════════════════════════════════════════════╣
║ Input Type:     [file/folder/text/url]                           ║
║ Source Type:    [jira/confluence/email/meeting/slack/etc.]       ║
║ Content Type:   [meeting/email/ticket/idea/status_update/notes]  ║
║ Source Date:    [YYYY-MM-DD]                                     ║
║ Content Length: [X characters]                                   ║
╠══════════════════════════════════════════════════════════════════╣
║ DETECTED ENTITIES (from Python script):                           ║
║   People:        X [list all names]                              ║
║   Tickets:       X [list all IDs]                                ║
║   Projects:      X [list all names]                              ║
║   Dates Found:   X [list all dates]                              ║
║                                                                   ║
║ EXTRACTED ITEMS:                                                  ║
║   Action Items:  X                                               ║
║   Decisions:     X                                               ║
║   Risks:         X                                               ║
╠══════════════════════════════════════════════════════════════════╣
║ Next: LLM Semantic Extraction Pass...                             ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## Step 4: LLM Semantic Extraction Pass (CRITICAL - DO NOT SKIP)

The Python script uses regex patterns which may miss information. **This step is MANDATORY.**

### 4.1 Read Full Content

Analyze the full content from `$EXTRACTION_RESULT.raw_content_preview` and source to identify information that regex patterns may have missed.

### 4.2 Extract Additional Information

Look for these categories that regex might miss:

| Category | What to Look For | Examples |
|----------|------------------|----------|
| **Relative Dates** | Informal date references | "next Friday", "by EOD", "end of Q1", "before holidays" |
| **Implicit Actions** | Statements implying future work | "we should...", "it would be good to...", "let's consider..." |
| **Commitments** | Promises or agreements | "I'll send...", "we agreed to...", "I will follow up..." |
| **Technical Details** | Configs, versions, endpoints, IDs | "v2.3.1", "api.example.com/v2", "config: enabled=true" |
| **Key Statements** | Important quotes, conclusions | Direct quotes, summary statements, key decisions |
| **Links & References** | URLs, document names, systems | Confluence pages, external docs, Slack links |
| **Mentioned People** | Names regex might miss | Nicknames, partial names, role references ("the PM") |
| **Project References** | Informal project mentions | Codenames, abbreviations, informal names |
| **Risks & Blockers** | Issues not explicitly marked | Concerns, dependencies, potential problems |
| **Context & Background** | Important situational info | Why something is being done, historical context |

### 4.3 Convert ALL Dates to ISO Format

**CRITICAL:** For ALL detected dates (from Python AND semantic analysis), convert to absolute ISO format (`YYYY-MM-DD`).

| Original Text | Convert To (assuming today is 2025-12-12) |
|---------------|-------------------------------------------|
| "tomorrow" | 2025-12-13 |
| "next Friday" | 2025-12-19 |
| "in 2 weeks" | 2025-12-26 |
| "end of Q1" | 2026-03-31 |
| "by EOD Friday" | 2025-12-13 (this Friday) |
| "next sprint" | Calculate based on known sprint schedule |
| "before holidays" | 2025-12-23 (or appropriate cutoff) |
| "January 15" | 2026-01-15 (next occurrence) |
| "last Monday" | 2025-12-09 |

**Store all dates (converted to ISO) in `$ALL_DATES` list.**

### 4.4 Information Preservation Principle

**When in doubt, INCLUDE the information:**

- Unsure if it's an action item? → Include it as an action item
- Unsure if a date is relevant? → Create a calendar event for it
- Unsure if a person reference is known? → Add it and let disambiguation handle it
- Technical details seem potentially relevant? → Include them in context
- A statement might be a decision? → Record it as a decision

---

## Step 5: Execute File Operations

The Python script has already created/updated some files. Review what was done:

From `$EXTRACTION_RESULT.file_operations.executed`:
- List all created files
- List all updated files
- Report any errors

---

## Step 6: JIRA Enrichment

If `$EXTRACTION_RESULT.jira_enrichment_needed` is not empty:

For each ticket ID in the list:

1. **Fetch ticket from JIRA:**
   ```
   Use: atlassian_jira_get_issue(issue_key: "<TICKET_ID>")
   ```

2. **Parse the JIRA response** and extract:
   - `summary`: Ticket title
   - `status`: Current status
   - `assignee`: Person assigned
   - `priority`: Priority level
   - `description`: Full description
   - `labels`: Any labels

3. **Update the ticket file** at `tickets/<TICKET_ID>.md`:
   - Fill in YAML frontmatter with JIRA data
   - Add `source: jira` tag
   - Update summary and description sections

4. **Update assignee's references.md** if they exist in `communication/people/`

---

## Step 7: Handle Ambiguous Entities

If `$EXTRACTION_RESULT.ambiguous` is not empty:

Use semantic understanding and context to resolve ambiguities:

| Ambiguous | Context Signals | Resolution |
|-----------|-----------------|------------|
| "Sarah" | Product, UX, features | → Sarah Mueller |
| "Lisa" | SE Optimization, fees | → Lisa Weber |
| "Paul" | Check surrounding context | → Paul Lange or Felix Wolf |

**Process:**
1. Read context around the ambiguous mention
2. Match to known person roles from `known_entities.json`
3. If truly ambiguous, update BOTH people with a disambiguation note

---

## Step 8: Create New Person Folders (If Needed)

If new people were detected not in `known_entities.json`:

1. **Create person folder structure:**
   ```
   communication/people/<slug>/
   ├── profile.md
   ├── notes.md
   ├── references.md
   └── thoughts.md
   ```

2. **Use templates from `templates/`**

3. **Fill in available information** including inferred source tags

4. **Update `known_entities.json`** with the new person

---

## Step 9: Create Calendar Events (USING CALENDAR TOOL)

For ALL dates in `$ALL_DATES` (from both Python extraction and LLM semantic pass), create calendar events using the `calendar_create` tool.

### 9.1 Date Format Requirements (CRITICAL)

**ALL dates passed to `calendar_create` MUST be in ISO format: `YYYY-MM-DD`**

The calendar tool will REJECT non-ISO formats. Convert all dates before calling.

### 9.2 Event Creation Rules

| Content/Context | Event Type | Title Format |
|-----------------|------------|--------------|
| Meeting detected | `meeting` | "Meeting: [topic/participants]" |
| Ticket deadline | `deadline` | "[TICKET-ID]: [summary]" |
| Action item due date | `deadline` | "Due: [task description]" |
| Idea review | `reminder` | "Idea: [idea name]" |
| Follow-up needed | `reminder` | "Follow-up: [topic]" |
| Status update | `reminder` | "Review: [topic]" |
| Historical event | `reminder` | "[Event]: [description]" |

### 9.3 Call Calendar Tool for Each Event

For each date, call:

```
calendar_create(
  title: "<Event title>",
  date: "<YYYY-MM-DD>",           # MUST be ISO format
  time: "<HH:MM>",                # Optional, MUST be 24-hour format
  type: "<meeting|deadline|reminder|appointment>",
  participants: "<comma-separated person slugs>",
  project: "<project slug if applicable>",
  ticket: "<ticket ID if applicable>",
  description: "<relevant context>"
)
```

### 9.4 Example Tool Calls

**Meeting detected (date: "next Tuesday" → 2025-12-17):**
```
calendar_create(
  title: "1:1 with Stefan Wagner - FLIGHT-250",
  date: "2025-12-17",
  time: "14:00",
  type: "meeting",
  participants: "stefan_wagner",
  ticket: "FLIGHT-250",
  description: "Discussion about GPT-4 integration for chatbot"
)
```

**Action item with deadline ("by Friday" → 2025-12-13):**
```
calendar_create(
  title: "Due: Deploy chatbot to staging",
  date: "2025-12-13",
  type: "deadline",
  participants: "alex_kumar",
  ticket: "FLIGHT-250",
  description: "Alex to deploy chatbot to staging environment"
)
```

**Informal date reference ("end of Q1" → 2026-03-31):**
```
calendar_create(
  title: "Q1 Planning Review",
  date: "2026-03-31",
  type: "reminder",
  project: "flight_recommender",
  description: "Team mentioned Q1 planning discussion needed"
)
```

### 9.5 Track Created Events

Maintain list of all created events for final summary:
- Event ID (returned by tool)
- Title and date
- Associated meeting file (if type=meeting)

---

## Step 10: Update Cross-References

For all people detected in the content:

1. **Read their `references.md`**
2. **Add new reference entries** with source tags:

```markdown
| YYYY-MM-DD | Source | Context | File Path | Notes |
|------------|--------|---------|-----------|-------|
| 2025-12-12 | meeting | 1:1 Call | communication/meetings/2025-12-12_meeting.md | Discussed FML-250 |
| 2025-12-12 | jira | Ticket Update | tickets/FML-250.md | Assigned as developer |
```

---

## Step 11: Information Preservation Checklist

Before completing, verify ALL relevant information was captured:

### Mandatory Checklist

- [ ] **All people mentioned** are tracked
- [ ] **All ticket IDs** have files created/updated
- [ ] **All dates** have calendar events (via `calendar_create` tool)
- [ ] **All action items** (explicit AND implicit) are recorded
- [ ] **All decisions** are documented
- [ ] **All technical details** are preserved
- [ ] **All links/references** are included
- [ ] **Key quotes/statements** are captured
- [ ] **Commitments/promises** are tracked as action items
- [ ] **Source type** is tagged on all created files

### If Information Was Missed

Create additional updates:
1. Add more file updates for missed entities
2. Call `calendar_create` for missed dates
3. Append missed details to relevant notes files

---

## Step 12: Final Summary

Display the complete ingestion summary:

```
╔══════════════════════════════════════════════════════════════════╗
║                    INGESTION COMPLETE                            ║
╠══════════════════════════════════════════════════════════════════╣
║ SOURCE: [jira/confluence/email/meeting/slack/document/web]       ║
╠══════════════════════════════════════════════════════════════════╣
║ FILES CREATED:                                                   ║
║   ✓ tickets/FLIGHT-250.md                                        ║
║   ✓ communication/meetings/2025-12-17_meeting.md                 ║
║                                                                  ║
║ FILES UPDATED:                                                   ║
║   ✓ communication/people/stefan_wagner/notes.md                  ║
║   ✓ communication/people/stefan_wagner/references.md             ║
║   ✓ communication/people/alex_kumar/notes.md                     ║
║                                                                  ║
║ JIRA ENRICHMENT:                                                 ║
║   ✓ FLIGHT-250: Status=In Progress, Assignee=Alex Kumar          ║
║                                                                  ║
║ CALENDAR EVENTS CREATED (via calendar_create tool):              ║
║   ✓ EVENT-047: Meeting on 2025-12-17 (meeting)                   ║
║     → Meeting file: communication/meetings/2025-12-17_meeting.md ║
║   ✓ EVENT-048: Due: Deploy to staging (2025-12-13, deadline)     ║
║   ✓ EVENT-049: Q1 Planning reminder (2026-03-31, reminder)       ║
║                                                                  ║
║ INFORMATION EXTRACTED:                                           ║
║   • 2 people referenced                                          ║
║   • 1 ticket processed                                           ║
║   • 4 action items captured                                      ║
║   • 1 decision recorded                                          ║
║   • 3 dates → calendar events                                    ║
║   • 2 technical details preserved                                ║
║                                                                  ║
║ PRESERVATION CHECK: ✓ Complete                                   ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## Error Handling

### Script Execution Errors

If `scripts/ingest.py` fails:
```
Error: Failed to execute extraction script.
[Error message from script]

Please check:
- Input file/folder exists
- File is readable text format
- Python environment is active
```

### Calendar Tool Errors

If `calendar_create` returns an error:
```
Error creating calendar event: [error message]

Common causes:
- Date not in YYYY-MM-DD format (convert it first!)
- Time not in HH:MM format
- Invalid event type

Fix: Ensure date is ISO format (e.g., 2025-12-15) not natural language
```

### JIRA API Errors

If JIRA enrichment fails:
```
Warning: Could not fetch JIRA data for [TICKET-ID]
Reason: [API error message]
Action: Ticket file created with extracted context only
```

---

## Source Type Reference

| Source Type | Typical Indicators | Default Tags | Storage Location |
|-------------|-------------------|--------------|------------------|
| `jira` | JIRA URL, ticket ID in title | `jira`, `ticket` | `tickets/` |
| `confluence` | Confluence URL, wiki format | `confluence`, `docs` | Context-dependent |
| `email` | From/To/Subject headers | `email`, `communication` | Person notes |
| `meeting` | Meeting keywords, participants | `meeting`, `calendar` | `communication/meetings/` |
| `slack` | Slack URL, channel format | `slack`, `chat` | Person notes |
| `standup` | Daily/weekly update format | `standup`, `status` | Project progress |
| `technical` | Code blocks, tech patterns | `technical`, `code` | Project or ticket |
| `brainstorm` | Idea/proposal keywords | `idea`, `innovation` | `idea_development/` |
| `document` | File input, markdown | `notes`, `document` | Context-dependent |
| `web` | Generic web URL | `external`, `reference` | Context-dependent |

---

## Supported Entity Patterns

### Ticket IDs
- `DS-####` (Data Science)
- `FML-###` (Flight ML)
- `FLUG-#####` (Flight)
- `FLIGHTS-####` (Flights)
- `FIOS-###` (Flight iOS)
- `FPRO-###` (Flight Product)
- `BI-####` (Business Intelligence)
- `HD-#####` (Helpdesk)

### Date Formats (Input)
- ISO: `2025-12-10`
- German: `10.12.2025`
- US: `12/10/2025`
- Written: `December 10, 2025`
- Relative: `tomorrow`, `next Friday`, `in 2 weeks` (LLM converts these)

### Action Items
- `- [ ] task description`
- `TODO: task description`
- `Action: task description`
- `@person to do something`
- Implicit: "we should...", "let's...", "need to..."

---

## Key Reminders

1. **Source Inference**: Always determine and tag the source type
2. **LLM Semantic Pass**: Never skip Step 4 - regex misses important information
3. **ISO Dates**: Calendar tool requires `YYYY-MM-DD` format - convert all dates
4. **Preserve More**: When uncertain, include the information
5. **Calendar Events**: Use `calendar_create` tool for ALL dates found
6. **Cross-References**: Update person references.md with source tags
