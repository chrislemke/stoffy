---
description: View and manage calendar events with visual calendar display
subtask: true
---

# Calendar Command

View calendar events for a specified date range with both visual calendar grid and table listing. Supports interactive event detail viewing.

## Usage

```
/calendar [date_range]
```

**Date range examples:**
- `today` - Today's events
- `tomorrow` - Tomorrow's events
- `this week` - Current week (Mon-Sun)
- `next week` - Following week
- `this month` - Current month
- `next month` - Following month
- `this year` - Current year
- `2025-01-15` - Specific date
- `2025-01-01 to 2025-01-31` - Date range

**Default:** `this week` if no range specified

---

## Step 1: Parse Date Range

Parse `$ARGUMENTS` as the date range. If empty or blank, default to "this week".

---

## Step 2: Query Calendar Events

Use the `calendar_list` tool to get events within the specified range.

For week-range queries (today, tomorrow, this week, next week):
```
calendar_list(range: "$ARGUMENTS", format: "calendar")
```

For month/year queries:
```
calendar_list(range: "$ARGUMENTS", format: "calendar")
```

---

## Step 3: Display Results

Present the calendar view to the user. The output includes:

1. **Visual Calendar Grid** (for week views):
   - ASCII box drawing showing Mon-Sun columns
   - Events displayed with time and truncated title
   - Event IDs shown for reference

2. **Event Table**:
   - ID, Date, Time, Event title, Type, Location
   - Sorted chronologically

Example output:
```
+============================================================================+
|                    CALENDAR: Dec 09 - Dec 15, 2025                         |
+============+============+============+============+============+================+
| Mon 09     | Tue 10     | Wed 11     | Thu 12     | Fri 13     | Sat/Sun        |
+------------+------------+------------+------------+------------+----------------+
| 09:00      |            | 10:00      |            | 14:00      |                |
| Team Stan  |            | 1:1 Alex   |            | Sprint Rev |                |
| [001]      |            | [003]      |            | [005]      |                |
+============+============+============+============+============+================+

## Events: Dec 09, 2025 - Dec 15, 2025

| ID        | Date   | Time  | Event                       | Type    | Location |
|:----------|:-------|:------|:----------------------------|:--------|:---------|
| EVENT-001 | Dec 09 | 09:00 | Team Standup                | meeting | Remote   |
| EVENT-003 | Dec 11 | 10:00 | 1:1 with Alex               | meeting | Office   |
| EVENT-005 | Dec 13 | 14:00 | Sprint Review               | meeting | Remote   |

*Total: 3 event(s)*
```

---

## Step 4: Offer Event Details

After displaying the calendar, ask:

> "Would you like detailed information on any specific event? Enter an event ID (e.g., EVENT-001 or just 001), or say 'no' to continue."

---

## Step 5: Show Event Details (If Requested)

If the user provides an event ID, use the `calendar_get` tool:

```
calendar_get(event_id: "<user_input>")
```

Display the full event details including:
- **Title and ID**
- **Type** (meeting, reminder, deadline, etc.)
- **Date and Time**
- **Duration**
- **Location**
- **Status** (scheduled, completed, cancelled)
- **Participants** (with links to their profile folders)
- **Recurrence** (if recurring)
- **Related Project/Ticket** (if any)
- **Meeting File** (if type is meeting)
- **Description**
- **Notes**

Example:
```
## EVENT-003: 1:1 with Alex

| Field        | Value                                                  |
|:-------------|:-------------------------------------------------------|
| Type         | meeting                                                |
| Date         | 2025-12-11                                             |
| Time         | 10:00                                                  |
| Duration     | 30m                                                    |
| Location     | Office                                                 |
| Status       | scheduled                                              |
| Participants | alex_kumar                                             |
| Meeting File | communication/people/alex_kumar/meetings/...           |

### Description
Weekly 1:1 to discuss project progress and career development.
```

Then ask if they want to see another event, or continue with something else.

---

## Error Handling

If no events are found:
```
No events found for [date_range].

Would you like to create a new event? You can say something like:
"Create a meeting with Alex tomorrow at 2pm"
```

If the date range cannot be parsed:
```
Could not parse date range: "[input]"

Try formats like:
- today, tomorrow
- this week, next week
- this month, next month
- 2025-01-15 (specific date)
- 2025-01-01 to 2025-01-31 (date range)
```
