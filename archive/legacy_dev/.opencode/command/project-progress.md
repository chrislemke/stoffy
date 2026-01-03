---
description: Analyze project progress and generate contributor reports
agent: report_assistant
subtask: true
---

## 1. Repository Setup

1. Use the GitHub MCP to find the repository matching `$ARGUMENTS` from the `invia-flights` organization (team: "Artificial Intelligence").
2. Store the official repository name as `${REPO_NAME}`.
3. Clone or pull the repository to: `project_management/${REPO_NAME}/repo`.
4. `cd` into the repository directory for all subsequent operations.

## 2. Progress Analysis

Invoke the `project-analyzer` subagent with the following instructions:

### Analysis Scope
- **Primary timeframe**: Last weeks commits
- **Fallback**: If still <5 commits, analyze all available commits and flag as "low activity project"

### Required Analysis
1. **Project maturity assessment** using the 7-dimension scoring rubric
2. **Contributor analysis** with individual contribution summaries
3. **Technical deep-dive** on architecture, models, and data pipelines
4. **Risk assessment** identifying blockers and technical debt
5. **Report analysis**: Read all reports in `docs/reports` and contributor-specific folders to extract work summaries

## 3. Output Generation

### Main Progress Report
**Path**: `project_management/${REPO_NAME}/progress_report_<YYYY-MM-DD>.md`

The report must include all sections defined in the subagent's output format.

### Contributor Summaries
For each contributor identified:

**Path**: `communication/<contributor_name>/projects/${REPO_NAME}/contribution.md`

Rules:
- Use the contributor's GitHub username (lowercase, spaces replaced with underscores)
- If the file already exists, append new content with this separator:
```

  ---
```
- Each entry must be dated and include the analysis timeframe

## 4. Final Output

After the subagent completes:
1. Verify all files were created successfully
2. Display the overall project maturity score (X/14)
3. List the top 3 risks or blockers identified
4. Summarize each contributor's main focus area
