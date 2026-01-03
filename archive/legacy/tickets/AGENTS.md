# Tickets

> **For entity lookups, ticket prefixes, and global rules**: See `../agents_index.yaml`
> 
> **Index Updates**: When encountering a new ticket prefix not in the index, you MUST add it to `../agents_index.yaml` in the `ticket_prefixes` registry and update `meta.last_updated` and `changelog`.

This folder tracks **external tickets** (from Jira, issue trackers) relevant to ML/AI team work.

## Purpose

Capture context, decisions, and progress for tickets referenced in communications, meetings, or projects. Context persists here even if external systems change or access is limited.

## File Naming Convention

Files are named by their ticket identifier (uppercase):
```
<PREFIX>-<NUMBER>.md
```

Examples: `DS-1068.md`, `FML-242.md`, `FLUG-17004.md`

## Ticket Prefixes

See `../agents_index.yaml` section 5 (`ticket_prefixes`) for the complete registry of known prefixes, patterns, and teams.

## When to Create a Ticket File

**Create** when:
- A ticket is discussed in a meeting
- A ticket is mentioned in communication with context
- You need to track decisions or context for a ticket
- A ticket involves multiple stakeholders with a timeline

**Do not create** for:
- Simple tasks needing no context tracking
- Tickets fully contained in person notes or meeting notes

## Ticket File Structure

Use `../templates/ticket.md`. Key sections:

| Section | Purpose |
|---------|---------|
| **YAML Frontmatter** | ticket_id, status, priority, assignee, tags |
| **Summary** | What is this ticket about (2-3 sentences) |
| **Key Stakeholders** | Table of people and their involvement |
| **Meetings & Discussions** | Links to meeting notes |
| **Details / Context** | Background and requirements |
| **Open Actions** | `- [ ] Owner – action (due: YYYY-MM-DD)` |
| **Related** | Links to projects and other tickets |

## Status Definitions

| Status | Meaning |
|--------|---------|
| **Open** | Created, not yet actively worked |
| **In Progress** | Active work happening |
| **Blocked** | Cannot proceed due to dependency |
| **Approval** | Awaiting approval/review |
| **Done** | Work complete |

## Cross-References

| When ticket appears in... | Action |
|---------------------------|--------|
| Meeting notes | Add link in ticket's Related section |
| Person's notes | Add link in ticket's Related section |
| Project docs | Add link in ticket's Related section |
| New content | Update timeline with key points |

## Workflow: Updating a Ticket File

When new information emerges:
1. Update status if changed
2. Add entry to Meetings & Discussions table
3. Update Open Actions (check off completed, add new)
4. Add relevant links to Related section
5. **If deadline changed**: Update/create calendar event (see below)

## Calendar Event Integration

**CRITICAL**: When a ticket has a deadline or due_date, ALSO create/update a corresponding calendar event.

| Field | Calendar Behavior |
|-------|-------------------|
| `deadline` or `due_date` in frontmatter | Create calendar event (type: `deadline`) |
| Deadline mentioned in content | Create calendar event (type: `deadline`) |
| Calendar event already exists for deadline | UPDATE with ticket link, merge info |

**Process**:
1. Detect deadline/due_date in ticket frontmatter or content
2. Use `calendar_create` tool with `type: deadline`
3. Set `context.source_file` to link back to ticket file
4. Include ticket ID in event title
5. Confirm: "Also created/updated calendar event for deadline [date]"

**Example**:
```
Creating: FML-242.md with deadline: 2025-12-20
→ Also creates: calendar/events/event_XXX.md
  - title: FML-242 Deadline
  - date: 2025-12-20
  - type: deadline
  - ticket: FML-242
  - context.source_file: tickets/FML-242.md
```

**Conflict Resolution**: If a calendar event already exists for this ticket's deadline, UPDATE it (merge information, never lose data).
