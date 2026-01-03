---
description: Weekly status report for invia-flights AI team projects to be used in Atlassian project updates
agent: report_assistant
subtask: true
---

# AI Team – Weekly Status Report

Generate a concise, Atlassian-ready last week status report of for GitHub repositories owned by the **Artificial intelligence** team in the `invia-flights` GitHub organization that had **recent activity**.

---

## 1. Data Collection (Automated)

Run the Python script to collect GitHub data efficiently:

```bash
python scripts/github_weekly_report.py --pretty
```

This script:
- Fetches all repositories from `invia-flights/artificial-intelligence` team
- Collects commits, PRs, and issues from the last week (Monday to Friday)
- Outputs a JSON summary with all necessary data
- Uses the `gh` CLI (requires `gh auth login`)

**Parse the JSON output** and use it for the analysis below.

---

## 2. Activity Filtering

From the script output, **only report on projects in the `active_projects` array**.

The script pre-filters repositories based on activity:
- Commits pushed to the default branch
- Pull requests created, merged, or closed
- Issues created, closed, or updated

**Skip all projects in `inactive_projects`** – do not generate any output for them.

---

## 3. Per-project Analysis
For each project in `active_projects`, read all reports in `docs/reports` and contributor-specific folders to extract work summaries.
For each repository in `active_projects`, use the provided data to infer:

**Narrative elements**:
- *This week*: 1–3 short bullets summarizing key outcomes from `merged_prs` and `commits`
- *Next week*: 1–2 bullets based on `open_prs`
- *Risks / blockers*: 0–3 bullets from `critical_issues`; if empty, state "none"

---

## 4. Atlassian-ready Output

For each active repository, generate a **280-character status text** suitable for the Atlassian project update field.

**Format:**
```
This week: <1–2 key outcomes>. Next: <planned work>. Risks: <blockers or "none">.
```

**Requirements:**
- **Strictly enforce the 280-character limit** (Atlassian field maximum).
- If the text exceeds 280 characters, shorten phrases, abbreviate, or truncate with ellipsis.
- Include the most important information first (key accomplishments).

**Output per project:**
1. **Project name**
2. **280-character status text**

---

## 5. Report File

- Path: `reports/status_updates/project_updates_<YYYY>-W<WW>.md`
  - Use the `iso_week` from the script's metadata
- Ensure the directory `reports/status_updates/` exists.
- Contents:
  - Heading with ISO week and timeframe (from `metadata.timeframe`)
  - **Only projects with activity** – one section per active repository including:
    - Project name and status (ON TRACK / AT RISK / OFF TRACK)
    - 280-character status text (ready to copy-paste into Atlassian)
    - Bullets for **This week**, **Next week**, and **Risks / blockers**
    - Link to the repository
  - An "Overall summary" section with:
    - Count of active projects (`summary.active_repositories`)
    - Total projects in scope (`summary.total_repositories`)
    - Brief cross-project narrative

---

## 6. Status Determination

Determine project status based on the data:

- **ON TRACK**: No critical issues, normal activity
- **AT RISK**: Has critical/blocker issues OR no merged PRs despite open PRs
- **OFF TRACK**: Multiple critical issues OR stalled development

---
