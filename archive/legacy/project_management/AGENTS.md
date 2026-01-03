# Project Management

> **For entity lookups and global rules**: See `../agents_index.yaml`
> 
> **Index Updates**: When creating a new project folder or changing project status, you MUST update `../agents_index.yaml` in the `projects` registry and update `meta.last_updated` and `changelog`.

This folder steers ML/AI delivery: ShapeUp cycles, roadmaps, KPIs, and operational ownership.

## Project Folder Structure

Each project folder (`<project_name>/`) may contain:

| File | Purpose | Frequency |
|------|---------|-----------|
| `project.md` | Project overview and context | Once |
| `progress_report_YYYY-MM-DD.md` | Detailed analysis and status | Weekly or on-demand |
| `daily_updates.md` | Running log of daily progress | Daily during active work |
| `decisions.md` | Key technical/architectural decisions | As needed |
| `risks.md` | Risk register with mitigations | Updated as identified |

## Progress Report Structure

Use `../templates/project_progress_report.md`. Key sections:

| Section | Content |
|---------|---------|
| **Executive Summary** | High-level status and recent highlights |
| **Project Maturity Score** | Scored assessment across dimensions |
| **Contributor Analysis** | Per-contributor breakdown |
| **Technical Overview** | Architecture, ML components |
| **Risk Assessment** | Blockers, debt, security concerns |
| **Recommendations** | Prioritized action items |

## Methodology: ShapeUp

| Concept | Description |
|---------|-------------|
| **Cycles** | Fixed 6-week timeboxes for building |
| **Cooldown** | 2-week buffer between cycles |
| **Pitches** | Shaped proposals with problem, appetite, solution |
| **Betting Table** | Deciding what to build next cycle |

### Idea → Project Flow

```
idea_development/    →    Betting Table    →    project_management/
    (project.md)            (approved)           (<project>/)
```

When a pitch is approved:
1. Create project folder: `project_management/<project_name>/`
2. Initialize with first progress report
3. Track in `../reports/status_updates/` weekly reports
4. **REQUIRED**: Update `../agents_index.yaml`:
   - Add entry to `projects` registry with path, status, contributors
   - Update `meta.last_updated` to today's date
   - Add changelog entry describing the new project

## "You Build It, You Run It"

Team members own their systems end-to-end:
- Development, deployment, monitoring, maintenance
- Accountability for availability and scalability
- Quality is built in, not bolted on

## Cross-References

| If you mention... | Also update... |
|-------------------|----------------|
| A team member's contribution | Their `../communication/people/<name>/references.md` |
| A ticket (DS-xxx, FML-xxx) | `../tickets/<TICKET-ID>.md` |
| An idea from `idea_development/` | Link back to the idea folder |
| A stakeholder decision | Their `../communication/people/<name>/notes.md` |

## Stakeholder Communication

Project status flows to stakeholders through:
1. **Weekly status reports** → `../reports/status_updates/` → Leadership
2. **Progress reports** → This folder → Technical audience

## Calendar Event Integration

**CRITICAL**: When documenting project milestones, deadlines, or review dates, ALSO create/update corresponding calendar events.

| Content Type | Calendar Event Type |
|--------------|---------------------|
| Project milestone with target date | `deadline` |
| Next review date in progress report | `reminder` |
| Sprint/cycle end date | `deadline` |
| Demo or presentation date | `meeting` |

**Process**:
1. Detect dates in project documentation (milestones, reviews, demos)
2. Use `calendar_create` tool with appropriate type
3. Set `context.source_file` to link back to project file
4. Set `project` field to link to project
5. Confirm: "Also created/updated calendar event for [milestone/review] on [date]"

**Example**:
```
Adding milestone to project.md: "MVP launch target: 2025-01-15"
→ Also creates: calendar/events/event_XXX.md
  - title: [Project Name] MVP Launch
  - date: 2025-01-15
  - type: deadline
  - project: <project_name>
  - context.source_file: project_management/<project>/project.md
```

**Conflict Resolution**: If a calendar event already exists for this milestone date, UPDATE it (merge information, never lose data).
