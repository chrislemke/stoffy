# Idea Development

> **For entity lookups and global rules**: See `../agents_index.yaml`
> 
> **Index Updates**: When creating a new idea folder or changing idea status, you MUST update `../agents_index.yaml` in the `ideas` registry and update `meta.last_updated` and `changelog`.

This folder captures and matures ideas, research, and POCs that could become future ML/AI initiatives.

## Purpose

- Stay current with ML trends (team requirement)
- Explore new tools, methods, frameworks
- Validate ideas before committing resources
- Feed the ShapeUp pitch pipeline in `../project_management/`

## Idea Lifecycle

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ CAPTURE │ → │ EXPLORE │ → │   POC   │ → │ PROPOSE │ → │ PROJECT │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
```

| Stage | Exit Criteria |
|-------|---------------|
| **Capture** | Idea is clearly articulated |
| **Explore** | Feasibility understood, risks identified |
| **POC** | Technical viability proven |
| **Propose** | Shaped pitch with bounded appetite and risks |
| **Project** | Approved at betting table → moves to `../project_management/` |

## Folder Organization

Each idea has a folder: `<idea_name>/`

| File | Required | Purpose |
|------|----------|---------|
| `project.md` | Yes | Main documentation, context, status |
| `research.md` | No | Background research and findings |
| `poc_results.md` | No | POC outcomes and learnings |
| `pitch.md` | No | Shaped pitch for betting table |

## Creating a New Idea

1. Create folder: `idea_development/<idea_name>/`
2. Copy `../templates/project_idea.md` → `project.md`
3. Fill in context, origin, and requirements
4. **REQUIRED**: Update `../agents_index.yaml`:
   - Add entry to `ideas` registry with path, status, owner, next_step
   - Update `meta.last_updated` to today's date
   - Add changelog entry: "Added <idea_name> to ideas registry"

## Evaluation Criteria

| Criterion | Questions to Answer |
|-----------|---------------------|
| **Business Value** | Aligns with fluege.de goals? Who benefits? |
| **Technical Feasibility** | Can we build it? Complexity? |
| **Data Availability** | Do we have data? Privacy concerns? |
| **Resource Fit** | Skills, time, infrastructure available? |
| **Risk** | What could go wrong? How bounded? |

## From Idea to Project

When an idea is approved at the betting table:
1. Create folder in `../project_management/<project_name>/`
2. Copy or link relevant documentation
3. Update idea status to "graduated" in the index
4. Begin tracking in project management

## Cross-References

| When updating idea content... | Also update... |
|-------------------------------|----------------|
| Person contributed idea | Their `../communication/people/<name>/references.md` |
| Idea generates ticket | `../tickets/<TICKET-ID>.md` |
| Idea graduates to project | `../project_management/<project>/` |

## Calendar Event Integration

**CRITICAL**: When documenting POC deadlines, pitch dates, or exploration timelines, ALSO create/update corresponding calendar events.

| Content Type | Calendar Event Type |
|--------------|---------------------|
| POC deadline | `deadline` |
| Pitch date (betting table) | `deadline` |
| Research review date | `reminder` |
| Demo date for POC | `meeting` |

**Process**:
1. Detect dates in idea documentation (POC deadlines, pitch dates, reviews)
2. Use `calendar_create` tool with appropriate type
3. Set `context.source_file` to link back to idea file
4. Confirm: "Also created/updated calendar event for [POC/pitch] on [date]"

**Example**:
```
Adding to project.md: "POC completion target: 2025-01-10"
→ Also creates: calendar/events/event_XXX.md
  - title: [Idea Name] POC Deadline
  - date: 2025-01-10
  - type: deadline
  - context.source_file: idea_development/<idea>/project.md
```

**Conflict Resolution**: If a calendar event already exists for this date/idea, UPDATE it (merge information, never lose data).
