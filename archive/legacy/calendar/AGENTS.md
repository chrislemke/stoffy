# Calendar AGENTS.md

This folder contains calendar events for scheduling and time management.

## Structure

```
calendar/
├── AGENTS.md          # This file
└── events/            # Individual event files
    ├── event_001.md
    ├── event_002.md
    └── ...
```

## File Naming

Events use sequential IDs: `event_XXX.md` (zero-padded: 001, 002, etc.)

---

## Auto-Detection Rules

There are **two types** of automatic calendar event creation:

1. **Calendar Detection** - For future scheduling (meetings, appointments, deadlines)
2. **Activity Log Detection** - For recording past/present accomplishments and events

Both trigger automatically without asking for confirmation.

---

### 1. Calendar Detection (Future Scheduling)

**CRITICAL**: When a date or scheduling context is mentioned in conversation, AUTOMATICALLY create a calendar event without asking for confirmation.

### Detection Triggers

| Pattern | Example | Action |
|---------|---------|--------|
| Date + event | "on December 15th I have..." | Create event |
| Time reference | "meeting at 3pm tomorrow" | Create event |
| Relative date | "next Monday I need to..." | Create event |
| Scheduling phrase | "schedule a call for..." | Create event |
| Calendar mention | "add to calendar..." | Create event |
| Appointment | "appointment with..." | Create event |
| Deadline | "deadline is Friday" | Create event (type: deadline) |
| Reminder | "remind me on..." | Create event (type: reminder) |

### Trigger Phrases

**Date indicators:**
- "today", "tomorrow", "yesterday"
- "this/next/last Monday/Tuesday/.../Sunday"
- "this/next/last week/month/year"
- "on [date]", "at [time]"
- "in X days/weeks/months"
- "December 15th", "Dec 15", "2025-01-15"

**Event indicators:**
- "schedule", "meeting", "call", "sync"
- "appointment", "event", "block time"
- "reminder", "remind me"
- "deadline", "due date"
- "calendar:", "event:"

### Auto-Creation Process

1. **Detect** date/scheduling phrase in user input
2. **Parse** the date using natural language (via `calendar_create` tool)
3. **Extract** event details:
   - Title (from context)
   - Date (parsed from input)
   - Time (if mentioned)
   - Type (meeting, reminder, deadline, etc.)
   - Participants (if people mentioned)
   - Project/Ticket (if mentioned)
4. **Create** `calendar/events/event_XXX.md` using template
5. **Create meeting file** if type is "meeting" (auto-linked)
6. **Confirm** briefly: "Created EVENT-XXX: [title] on [date]"

### Date Parsing Examples

| Input | Parsed Date | Notes |
|-------|-------------|-------|
| "tomorrow" | Next day | Relative |
| "next Monday" | Next Monday | Weekday |
| "in 3 days" | +3 days | Relative |
| "December 15" | 2025-12-15 | Month day |
| "12/15/2025" | 2025-12-15 | US format |
| "15.12.2025" | 2025-12-15 | DE format |
| "this Friday at 3pm" | Friday 15:00 | Day + time |

### Meeting File Auto-Creation

When `type: meeting` is detected:

1. **1:1 meetings** (single participant):
   - Create file in `communication/people/<person>/meetings/`
   - Format: `YYYY-MM-DD_<topic>.md`

2. **Group meetings** (multiple participants):
   - Create file in `communication/meetings/`
   - Format: `YYYY-MM-DD_<topic>.md`

3. **Link** the meeting file to the calendar event via `context.meeting_file`

---

### 2. Activity Log Detection (Historical Record)

**CRITICAL**: When user shares notable accomplishments, events, or activities, AUTOMATICALLY create a calendar event to record WHEN it happened. This is a **historical activity log**.

#### Key Difference from Calendar Detection

| Aspect | Calendar Detection | Activity Log Detection |
|--------|-------------------|----------------------|
| **Purpose** | Schedule future events | Record what happened |
| **Date used** | Parsed from input | TODAY (when told) |
| **Triggers** | "tomorrow", "next week", "at 3pm" | "I deployed", "we released", "I fixed" |
| **Event type** | Meeting, deadline, etc. | Inferred (usually reminder) |

#### Activity Trigger Phrases

**Accomplishment language:**
- "I just deployed...", "I deployed..."
- "we released...", "I released..."
- "I finished...", "I completed..."
- "I launched...", "we launched..."
- "I shipped...", "we shipped..."
- "I merged...", "I pushed..."
- "went live...", "is now live..."
- "I fixed...", "we fixed..."
- "I implemented...", "we implemented..."

**Decision/milestone language:**
- "we decided...", "I decided..."
- "signed off on...", "approved..."
- "milestone reached...", "achieved..."

**Explicit memory requests:**
- "remember that...", "remember this..."
- "note that...", "log this..."
- "record that...", "keep track..."
- "for the record..."

#### Activity Log Process

1. **Detect** accomplishment/activity phrase in user input
2. **Use TODAY's date** (when user tells you, NOT parsed from their text)
3. **Extract**: activity title, related project/ticket/people
4. **Infer event type** from context (most map to `reminder`)
5. **Create** calendar event using `calendar_create`
6. **Confirm** briefly: "Logged: [title] (EVENT-XXX)"

#### What to Log vs. Skip

| Log (Relevant) | Skip (Not Relevant) |
|----------------|---------------------|
| Deployments, releases | Casual conversation |
| Major bug fixes, hotfixes | Questions/information requests |
| Feature completions | General discussions |
| Important decisions | Minor routine tasks |
| Milestones achieved | Planning/future intent |
| User explicitly asks to remember | |

#### Example: Activity Log Flow

**User says:**
> "I just deployed the new version of the service fee model to production"

**Agent action:**

1. **Detect triggers**: "I just deployed"
2. **Use date**: TODAY (2025-12-11, not parsed from text)
3. **Extract**:
   - Title: "Deployed service fee model to production"
   - Type: reminder (inferred: deployment)
   - Project: service-fee-optimization
4. **Execute**:
   ```
   calendar_create(
     title: "Deployed service fee model to production",
     date: "today",
     type: "reminder",
     description: "Deployed new version of service fee model",
     project: "service-fee-optimization"
   )
   ```
5. **Result**: Creates `calendar/events/event_XXX.md`
6. **Confirm**: "Logged: Deployed service fee model to production (EVENT-XXX)"

---

## Event Types

| Type | Use Case |
|------|----------|
| `meeting` | Calls, syncs, 1:1s, team meetings |
| `reminder` | Things to remember |
| `deadline` | Due dates, submission dates |
| `appointment` | General scheduled events |
| `personal` | Personal events |
| `holiday` | Public holidays, company holidays |
| `vacation` | PTO, vacation days |
| `blocked` | Focus time, no-meeting blocks |

---

## Recurrence Patterns

| Pattern | Description | Example |
|---------|-------------|---------|
| `daily` | Every day | Daily standup |
| `weekly` | Every week (same day) | Weekly 1:1 |
| `monthly` | Every month (same date) | Monthly review |
| `yearly` | Every year (same date) | Annual review |

Recurrence can include:
- `interval`: Every N periods (e.g., every 2 weeks)
- `weekdays`: Specific days for weekly (e.g., Mon, Wed, Fri)
- `end_date`: When recurrence stops
- `count`: Number of occurrences

---

## Example: Auto-Detection Flow

**User says:**
> "I have a meeting with Alex tomorrow at 2pm to discuss the chatbot project"

**Agent action:**

1. **Detect triggers**: "meeting", "tomorrow at 2pm"
2. **Parse date**: tomorrow = 2025-12-12
3. **Parse time**: 2pm = 14:00
4. **Extract**:
   - Title: "Meeting with Alex - chatbot discussion"
   - Participants: ["alex_kumar"]
   - Type: meeting
   - Project: conversational-ai-bot
5. **Execute**:
   ```
   calendar_create(
     title: "Meeting with Alex - chatbot discussion",
     date: "tomorrow",
     time: "14:00",
     type: "meeting",
     participants: "alex_kumar",
     project: "conversational-ai-bot"
   )
   ```
6. **Result**: Creates:
   - `calendar/events/event_001.md`
   - `communication/people/alex_kumar/

### How It Works

1. **LaunchAgent** runs `calendar_reminder.py check` every 5 minutes
2. Script scans all events in `calendar/events/` for those with `reminder` set
3. For each event, calculates `notify_at = event_time - reminder_offset`
4. If `now >= notify_at` and not already notified:
   - Sends **macOS notification** (appears in Notification Center)
   - Prints **terminal notification** (with bell sound)
5. Tracks sent reminders in `.reminder_state.json` to avoid duplicates

### State File

Sent reminders are tracked in `calendar/events/.reminder_state.json` (gitignored).

To re-send all reminders (e.g., after testing):
```bash
python scripts/calendar_reminder.py clear
```

### Requirements

- **macOS** (uses native notification system via `osascript`)
- **Conda environment** with `dateparser` and `pyyaml` installed
- **LaunchAgent** installed via `make install-reminder-daemon`

### Notification Appearance

Notifications include:
- Event type emoji (meeting, deadline, reminder, etc.)
- Event title
- Time until event starts
- Event time and location (if set)

Example:
```
📅 1:1 with Alex in 30 minutes
   At 14:00 - Conference Room A
```
