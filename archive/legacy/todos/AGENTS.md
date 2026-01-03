# AGENTS.md - Todos

This folder tracks personal action items, tasks, and reminders for the ML/AI Team Lead.

## Purpose

Capture todos mentioned during conversations so nothing falls through the cracks. Each todo is stored as an individual file in `todos/list/`.

## Structure

```
todos/
├── AGENTS.md          # This file
└── list/              # Individual todo files
    ├── todo_001.md
    ├── todo_002.md
    └── ...
```

## Auto-Detection Rules

**CRITICAL**: When the user mentions something they need to do, AUTOMATICALLY create a new todo file without asking for confirmation.

### Detection Keywords

Create a todo when the user says any of:
- "I need to..."
- "I should..."
- "I have to..."
- "remind me to..."
- "todo:"
- "task:"
- "don't forget to..."
- "action item:"
- "need to remember..."
- "make sure to..."
- "follow up on..."

### Auto-Creation Process

1. **Detect** a todo phrase in user input
2. **Generate** the next sequential ID (check existing files in `todos/list/`)
3. **Extract** relevant information:
   - Title from the task description
   - People mentioned (use person slugs from `agents_index.yaml`)
   - Related project/ticket if mentioned
   - Due date if mentioned
4. **Create** a new file using `templates/todo_item.md`
5. **Confirm** briefly: "Created todo_XXX: [title]"

### Naming Convention

Files are named: `todo_XXX.md` where XXX is a zero-padded sequential number (001, 002, etc.)

## Todo Fields

| Field | Description | Values |
|-------|-------------|--------|
| `id` | Unique identifier | TODO-XXX |
| `title` | Short task description | Free text |
| `status` | Current state | `open`, `in_progress`, `blocked`, `done`, `cancelled` |
| `priority` | Urgency level | `low`, `medium`, `high`, `critical` |
| `due_date` | Deadline (optional) | YYYY-MM-DD or null |
| `created` | Creation date | YYYY-MM-DD |
| `people` | People involved | List of person slugs (e.g., `alex_kumar`) |
| `context.project` | Related project | Project slug or null |
| `context.ticket` | Related ticket | Ticket ID or null |

## Status Management

When user mentions completing or updating a todo:
- "Done with..." / "Finished..." → Update status to `done`
- "Working on..." / "Started..." → Update status to `in_progress`
- "Blocked on..." / "Waiting for..." → Update status to `blocked`
- "Cancel..." / "Never mind..." → Update status to `cancelled`

## Cross-Referencing

- When a todo mentions a person, use their slug from `agents_index.yaml` people registry
- When a todo relates to a project, use the project key from `agents_index.yaml` projects registry
- When a todo relates to a ticket, use the ticket ID (e.g., FML-242, FPRO-868)

## Example

User says: "I need to talk to Alex about the service fee optimization results next week"

Creates `todos/list/todo_001.md`:
```yaml
---
id: TODO-001
title: "Talk to Alex about service fee optimization results"
status: open
priority: medium
due_date: null
created: 2025-12-11
people:
  - alex_kumar
context:
  project: service_fee_optimization
  ticket: null
tags:
  - todo
---

# TODO-001: Talk to Alex about service fee optimization results

## Description

Discuss the service fee optimization results with Alex.

## Notes

Mentioned: next week

## Updates

| Date | Update |
|------|--------|
| 2025-12-11 | Created |
```
