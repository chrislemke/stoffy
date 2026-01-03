---
description: Fetch Tempo timesheet hours for team members and generate reports
agent: general
subtask: true
---

# Tempo Hours Report

Fetch logged work hours from Tempo for specified team members and compare against their expected working patterns.

## Usage

```
/tempo-hours <names> [--weeks N]
```

**Arguments:**
- `<names>`: Comma-separated list of person names or aliases (e.g., `alex,anna` or `Alex Kumar,Anna Kowalski`)
- `--weeks N`: Number of weeks to look back (default: 1, meaning last complete week)

**Examples:**
```
/tempo-hours alex
/tempo-hours alex,anna
/tempo-hours "Alex Kumar,Anna" --weeks 2
```

---

## Execution Steps

### 1. Run the Python Script

Execute the tempo client script to fetch worklog data:

```bash
python3 .opencode/tool/tempo_client.py tempo-hours "$ARGUMENTS"
```

Parse the JSON output and store it in a variable for processing.

### 2. Process Results

For each person in the results:

1. **Check for errors**: If the person has an `error` field, report it and skip to the next person.

2. **Display summary**: Show a quick summary of logged vs expected hours:
   - Person name
   - Week range
   - Total logged hours
   - Total expected hours
   - Percentage (with status indicator)

3. **Save report**: Append the generated report to the person's tempo.md file:
   - Path: `communication/people/<slug>/tempo.md`
   - If the file doesn't exist, create it with a header
   - Append the report content (it already has a separator)

### 3. Report File Format

When creating a new `tempo.md` file, use this header:

```markdown
---
tags:
  - tempo
  - timesheet
updated: <YYYY-MM-DD>
---

# Tempo Time Tracking

Weekly time tracking reports from Tempo, comparing logged hours against expected working patterns.

```

Then append the report content from the script output.

**IMPORTANT**: When creating a new `tempo.md` file for a person, you MUST also update `agents_index.yaml`:
1. Add `tempo.md` to the `key_files` list for the `communication/people/` folder entry (if not already present)
2. Update `meta.last_updated` to today's date
3. Add a changelog entry describing the addition

### 4. Output Summary

After processing all people, display:

1. **Summary table** showing all people processed:
   | Person | Week | Logged | Expected | % | Status |

2. **Any errors encountered** (people who couldn't be processed)

3. **File paths** where reports were saved

---

## Working Pattern Reference

The script reads working patterns from each person's `profile.md`:

- **Weekly hours**: Found in "Working Hours" section (e.g., `40h / 40h full-time hours`)
- **Working days**: Found in "Working pattern" field (e.g., `Works Monday to Thursday`)
- **Expected daily hours**: Calculated as weekly_hours / working_days

Common patterns:
- Full-time (40h): 8h/day, Mon-Fri
- Part-time 32h: 8h/day, Mon-Thu
- Part-time 30h: 6h/day, Mon-Fri

---

## Requirements

**Environment Variables** (in `.env`):
- `TEMPO_API_TOKEN`: Tempo API token for authentication
- `ATLASSIAN_URL`: Jira instance URL
- `ATLASSIAN_USERNAME`: Jira username (email)
- `ATLASSIAN_API_TOKEN`: Jira API token

**Python Packages**:
- `tempo-api-python-client` - For Tempo API access
- `atlassian-python-api` - For Jira user lookup

Install if needed:
```bash
pip install tempo-api-python-client atlassian-python-api
```

---

## Error Handling

Common issues and solutions:

| Error | Cause | Solution |
|-------|-------|----------|
| "Unknown person: X" | Name/alias not in known_entities.json | Use full name or add alias |
| "No email found in profile" | Profile.md missing email | Add email to profile |
| "Could not find Jira account" | Email not registered in Jira | Verify email is correct |
| "Missing TEMPO_API_TOKEN" | .env not configured | Add token to .env |
| "Failed to fetch worklogs" | API error | Check token permissions |

---

## Notes

- Reports are **appended** to `tempo.md`, preserving history
- The script uses the **last complete week** (Mon-Sun) by default
- Weekend days are shown but not counted in expected hours (unless working pattern specifies them)
- Time is displayed in `Xh Ym` format for readability
