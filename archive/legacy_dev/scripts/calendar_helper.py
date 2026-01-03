#!/usr/bin/env python3
"""
Calendar Helper for opencode

Manages calendar events including parsing natural language dates,
listing events by date range, creating/updating/deleting events,
and formatting calendar views.

Usage:
    python scripts/calendar_helper.py list <date_range> [--format table|calendar|json]
    python scripts/calendar_helper.py create --title "Title" --date "2025-01-15" [options]
    python scripts/calendar_helper.py get <event_id>
    python scripts/calendar_helper.py update <event_id> [--field value ...]
    python scripts/calendar_helper.py delete <event_id>
    python scripts/calendar_helper.py next-id

Commands:
    list        List events within a date range
    create      Create a new calendar event
    get         Get details of a specific event
    update      Update an existing event
    delete      Delete (cancel) an event
    next-id     Get the next available event ID

Date Range Examples:
    today, tomorrow, yesterday
    this week, next week, last week
    this month, next month, last month
    this year, next year
    2025-01-15 (specific date)
    2025-01-01 to 2025-01-31 (date range)
    next Monday, this Friday
    in 3 days, 2 weeks ago
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import re
import sys
from typing import Any

import dateparser
import yaml

# ============================================================================
# Configuration
# ============================================================================

REPO_ROOT = Path(__file__).parent.parent
CALENDAR_DIR = REPO_ROOT / "calendar" / "events"
TEMPLATE_PATH = REPO_ROOT / "templates" / "calendar_event.md"
MEETINGS_DIR = REPO_ROOT / "communication" / "meetings"

# Event types
EVENT_TYPES = [
    "meeting",
    "reminder",
    "deadline",
    "appointment",
    "personal",
    "holiday",
    "vacation",
    "blocked",
]

# Recurrence patterns
RECURRENCE_PATTERNS = ["daily", "weekly", "monthly", "yearly"]


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class CalendarEvent:
    """Represents a calendar event."""

    id: str
    title: str
    date: date
    time: str | None = None
    duration: str | None = None
    end_date: date | None = None
    location: str | None = None
    participants: list[str] = field(default_factory=list)
    type: str = "appointment"
    status: str = "scheduled"
    reminder: str | None = None
    recurrence: dict[str, Any] | None = None
    context: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=lambda: ["calendar"])
    description: str = ""
    created: date = field(default_factory=lambda: date.today())
    file_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "type": self.type,
            "date": self.date.isoformat(),
            "time": self.time,
            "duration": self.duration,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "location": self.location,
            "participants": self.participants,
            "recurrence": self.recurrence,
            "status": self.status,
            "reminder": self.reminder,
            "context": self.context,
            "tags": self.tags,
            "created": self.created.isoformat(),
        }


# ============================================================================
# Date Parsing Functions
# ============================================================================


def parse_date(date_str: str, prefer_future: bool = True) -> date | None:
    """
    Parse a date string using dateparser.

    Supports natural language like "tomorrow", "next Monday", "in 3 days",
    as well as explicit formats like "2025-01-15".

    NOTE: This function is ONLY used for the 'list' command's date range parsing.
    For create/update operations, use parse_date_strict() instead.
    """
    settings: dict[str, Any] = {
        "PREFER_DATES_FROM": "future" if prefer_future else "past",
        "PREFER_DAY_OF_MONTH": "first",
        "RETURN_AS_TIMEZONE_AWARE": False,
    }

    result = dateparser.parse(date_str, settings=settings)  # type: ignore[arg-type]
    if result:
        return result.date()
    return None


def parse_date_strict(date_str: str) -> date | None:
    """
    Parse a date string in STRICT ISO format (YYYY-MM-DD) only.

    This function does NOT use dateparser and requires exact ISO format.
    Used for create/update operations to ensure deterministic behavior.

    Args:
        date_str: Date string in YYYY-MM-DD format

    Returns:
        date object if valid, None otherwise
    """
    if not date_str:
        return None

    date_str = date_str.strip()

    # Validate strict ISO format: YYYY-MM-DD
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return None

    try:
        return date.fromisoformat(date_str)
    except ValueError:
        # Invalid date like 2025-02-30
        return None


def parse_date_range(range_str: str) -> tuple[date, date]:
    """
    Parse a date range string.

    Supports:
    - Single terms: "today", "tomorrow", "yesterday"
    - Week ranges: "this week", "next week", "last week"
    - Month ranges: "this month", "next month", "last month"
    - Year ranges: "this year", "next year"
    - Specific dates: "2025-01-15"
    - Explicit ranges: "2025-01-01 to 2025-01-31"
    """
    range_str = range_str.lower().strip()
    today = date.today()

    # Handle explicit range with "to"
    if " to " in range_str:
        parts = range_str.split(" to ")
        start = parse_date(parts[0].strip(), prefer_future=False)
        end = parse_date(parts[1].strip(), prefer_future=True)
        if start and end:
            return (start, end)

    # Handle special keywords
    if range_str == "today":
        return (today, today)

    if range_str == "tomorrow":
        tomorrow = today + timedelta(days=1)
        return (tomorrow, tomorrow)

    if range_str == "yesterday":
        yesterday = today - timedelta(days=1)
        return (yesterday, yesterday)

    # Week handling
    if "week" in range_str:
        # Monday = 0, Sunday = 6
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        if "this week" in range_str:
            return (start_of_week, end_of_week)
        elif "next week" in range_str:
            return (
                start_of_week + timedelta(days=7),
                end_of_week + timedelta(days=7),
            )
        elif "last week" in range_str:
            return (
                start_of_week - timedelta(days=7),
                end_of_week - timedelta(days=7),
            )

    # Month handling
    if "month" in range_str:
        first_of_month = today.replace(day=1)

        if "this month" in range_str:
            # Get last day of current month
            if today.month == 12:
                last_of_month = today.replace(day=31)
            else:
                last_of_month = today.replace(month=today.month + 1, day=1) - timedelta(
                    days=1
                )
            return (first_of_month, last_of_month)

        elif "next month" in range_str:
            if today.month == 12:
                first_of_next = today.replace(year=today.year + 1, month=1, day=1)
            else:
                first_of_next = today.replace(month=today.month + 1, day=1)
            if first_of_next.month == 12:
                last_of_next = first_of_next.replace(day=31)
            else:
                last_of_next = first_of_next.replace(
                    month=first_of_next.month + 1, day=1
                ) - timedelta(days=1)
            return (first_of_next, last_of_next)

        elif "last month" in range_str:
            last_of_prev = first_of_month - timedelta(days=1)
            first_of_prev = last_of_prev.replace(day=1)
            return (first_of_prev, last_of_prev)

    # Year handling
    if "year" in range_str:
        if "this year" in range_str:
            return (today.replace(month=1, day=1), today.replace(month=12, day=31))
        elif "next year" in range_str:
            return (
                today.replace(year=today.year + 1, month=1, day=1),
                today.replace(year=today.year + 1, month=12, day=31),
            )
        elif "last year" in range_str:
            return (
                today.replace(year=today.year - 1, month=1, day=1),
                today.replace(year=today.year - 1, month=12, day=31),
            )

    # Try to parse as a single date
    parsed = parse_date(range_str, prefer_future=False)
    if parsed:
        return (parsed, parsed)

    # Default to this week
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    return (start_of_week, end_of_week)


def parse_time(time_str: str) -> str | None:
    """
    Parse time string and return in HH:MM format.

    NOTE: This function uses dateparser. For strict validation,
    use parse_time_strict() instead.
    """
    if not time_str:
        return None

    # Try parsing with dateparser
    result = dateparser.parse(time_str)
    if result:
        return result.strftime("%H:%M")

    # Try direct HH:MM format
    if re.match(r"^\d{1,2}:\d{2}$", time_str):
        parts = time_str.split(":")
        return f"{int(parts[0]):02d}:{parts[1]}"

    return None


def parse_time_strict(time_str: str) -> str | None:
    """
    Parse a time string in STRICT HH:MM format (24-hour) only.

    This function does NOT use dateparser and requires exact format.
    Used for create/update operations to ensure deterministic behavior.

    Args:
        time_str: Time string in HH:MM format (24-hour)

    Returns:
        Normalized time string (HH:MM) if valid, None otherwise
    """
    if not time_str:
        return None

    time_str = time_str.strip()

    # Accept H:MM or HH:MM format
    match = re.match(r"^(\d{1,2}):(\d{2})$", time_str)
    if not match:
        return None

    hours = int(match.group(1))
    minutes = int(match.group(2))

    # Validate ranges
    if hours < 0 or hours > 23:
        return None
    if minutes < 0 or minutes > 59:
        return None

    return f"{hours:02d}:{minutes:02d}"

    # Try parsing with dateparser
    result = dateparser.parse(time_str)
    if result:
        return result.strftime("%H:%M")

    # Try direct HH:MM format
    if re.match(r"^\d{1,2}:\d{2}$", time_str):
        parts = time_str.split(":")
        return f"{int(parts[0]):02d}:{parts[1]}"

    return None


# ============================================================================
# Event Management Functions
# ============================================================================


def get_next_event_id() -> str:
    """Get the next sequential event ID."""
    CALENDAR_DIR.mkdir(parents=True, exist_ok=True)

    existing_ids = []
    for file in CALENDAR_DIR.glob("event_*.md"):
        match = re.match(r"event_(\d+)\.md", file.name)
        if match:
            existing_ids.append(int(match.group(1)))

    next_num = max(existing_ids) + 1 if existing_ids else 1
    return f"EVENT-{next_num:03d}"


def parse_event_file(file_path: Path) -> CalendarEvent | None:
    """Parse an event file and return a CalendarEvent object."""
    try:
        content = file_path.read_text(encoding="utf-8")

        # Extract YAML frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1])
                body = parts[2].strip()

                # Parse date
                event_date = frontmatter.get("date")
                if isinstance(event_date, str):
                    event_date = date.fromisoformat(event_date)
                elif isinstance(event_date, datetime):
                    event_date = event_date.date()

                # Parse end_date
                end_date = frontmatter.get("end_date")
                if isinstance(end_date, str):
                    end_date = date.fromisoformat(end_date)
                elif isinstance(end_date, datetime):
                    end_date = end_date.date()

                # Parse created
                created = frontmatter.get("created", date.today())
                if isinstance(created, str):
                    created = date.fromisoformat(created)
                elif isinstance(created, datetime):
                    created = created.date()

                return CalendarEvent(
                    id=frontmatter.get("id", ""),
                    title=frontmatter.get("title", ""),
                    date=event_date,
                    time=frontmatter.get("time"),
                    duration=frontmatter.get("duration"),
                    end_date=end_date,
                    location=frontmatter.get("location"),
                    participants=frontmatter.get("participants", []) or [],
                    type=frontmatter.get("type", "appointment"),
                    status=frontmatter.get("status", "scheduled"),
                    reminder=frontmatter.get("reminder"),
                    recurrence=frontmatter.get("recurrence"),
                    context=frontmatter.get("context", {}) or {},
                    tags=frontmatter.get("tags", ["calendar"]),
                    description=body,
                    created=created,
                    file_path=file_path,
                )
    except Exception as e:
        print(f"Error parsing {file_path}: {e}", file=sys.stderr)
    return None


def list_events(start_date: date, end_date: date) -> list[CalendarEvent]:
    """List all events within a date range."""
    CALENDAR_DIR.mkdir(parents=True, exist_ok=True)

    events = []
    for file in CALENDAR_DIR.glob("event_*.md"):
        event = parse_event_file(file)
        if event and event.status != "cancelled":
            # Check if event falls within range
            if event.end_date:
                # Multi-day event
                if event.date <= end_date and event.end_date >= start_date:
                    events.append(event)
            else:
                # Single day event
                if start_date <= event.date <= end_date:
                    events.append(event)

            # Handle recurring events
            if event.recurrence and event.recurrence.get("pattern"):
                recurring_dates = generate_recurring_dates(event, start_date, end_date)
                for rec_date in recurring_dates:
                    if rec_date != event.date:  # Don't duplicate the original
                        # Create a copy with the recurring date
                        rec_event = CalendarEvent(
                            id=f"{event.id}*",  # Mark as recurring instance
                            title=event.title,
                            date=rec_date,
                            time=event.time,
                            duration=event.duration,
                            location=event.location,
                            participants=event.participants,
                            type=event.type,
                            status=event.status,
                            recurrence=event.recurrence,
                            context=event.context,
                            tags=event.tags,
                            file_path=event.file_path,
                        )
                        events.append(rec_event)

    # Sort by date and time
    events.sort(key=lambda e: (e.date, e.time or "00:00"))
    return events


def generate_recurring_dates(
    event: CalendarEvent, start_date: date, end_date: date
) -> list[date]:
    """Generate recurring dates for an event within a range."""
    if not event.recurrence:
        return []

    pattern = event.recurrence.get("pattern")
    interval = event.recurrence.get("interval", 1)
    rec_end = event.recurrence.get("end_date")
    rec_count = event.recurrence.get("count")
    weekdays = event.recurrence.get("weekdays", [])

    if rec_end and isinstance(rec_end, str):
        rec_end = date.fromisoformat(rec_end)

    dates = []
    current = event.date
    count = 0
    max_iterations = 1000  # Safety limit

    while count < max_iterations:
        # Check end conditions
        if rec_end and current > rec_end:
            break
        if rec_count and len(dates) >= rec_count:
            break
        if current > end_date:
            break

        # Add date if within range
        if current >= start_date and current <= end_date:
            if pattern == "weekly" and weekdays:
                # Check if current weekday matches
                day_name = current.strftime("%a").lower()[:3]
                if day_name in [w.lower()[:3] for w in weekdays]:
                    dates.append(current)
            else:
                dates.append(current)

        # Advance to next occurrence
        if pattern == "daily":
            current += timedelta(days=interval)
        elif pattern == "weekly":
            current += timedelta(weeks=interval)
        elif pattern == "monthly":
            # Add months
            month = current.month + interval
            year = current.year + (month - 1) // 12
            month = ((month - 1) % 12) + 1
            day = min(current.day, 28)  # Safe day for all months
            current = current.replace(year=year, month=month, day=day)
        elif pattern == "yearly":
            current = current.replace(year=current.year + interval)
        else:
            break

        count += 1

    return dates


def create_event(
    title: str,
    date_str: str,
    time: str | None = None,
    duration: str | None = None,
    event_type: str = "appointment",
    location: str | None = None,
    participants: list[str] | None = None,
    project: str | None = None,
    ticket: str | None = None,
    recurrence: str | None = None,
    description: str = "",
    reminder: str | None = None,
) -> dict[str, Any]:
    """
    Create a new calendar event.

    IMPORTANT: The date parameter MUST be in ISO format (YYYY-MM-DD).
    The time parameter MUST be in HH:MM format (24-hour).
    Natural language dates are NOT supported - the LLM must convert them first.
    """
    today = date.today()

    # Parse date - STRICT ISO format required
    event_date = parse_date_strict(date_str)
    if not event_date:
        return {
            "error": f"Invalid date format: '{date_str}'. "
            f"Use YYYY-MM-DD format (e.g., {today.isoformat()}). "
            f"Today is {today.isoformat()}. "
            "The LLM must convert natural language dates to ISO format before calling this function."
        }

    # Parse time if provided - STRICT HH:MM format required
    parsed_time = None
    if time:
        parsed_time = parse_time_strict(time)
        if not parsed_time:
            return {
                "error": f"Invalid time format: '{time}'. "
                "Use HH:MM format in 24-hour notation (e.g., 14:30 for 2:30 PM). "
                "The LLM must convert natural language times to HH:MM format before calling this function."
            }

    # Get next ID
    event_id = get_next_event_id()

    # Build recurrence dict if provided
    recurrence_dict = None
    if recurrence and recurrence in RECURRENCE_PATTERNS:
        recurrence_dict = {
            "pattern": recurrence,
            "interval": 1,
            "weekdays": None,
            "day_of_month": None,
            "end_date": None,
            "count": None,
        }

    # Build context
    context: dict[str, Any] = {}
    if project:
        context["project"] = project
    if ticket:
        context["ticket"] = ticket

    # Create event object
    event = CalendarEvent(
        id=event_id,
        title=title,
        date=event_date,
        time=parsed_time,
        duration=duration,
        type=event_type,
        location=location,
        participants=participants or [],
        recurrence=recurrence_dict,
        context=context,
        description=description,
        reminder=reminder,
    )

    # Generate file content
    file_content = generate_event_file(event)

    # Save file
    CALENDAR_DIR.mkdir(parents=True, exist_ok=True)
    file_num = int(event_id.split("-")[1])
    file_path = CALENDAR_DIR / f"event_{file_num:03d}.md"
    file_path.write_text(file_content, encoding="utf-8")

    # Create meeting file if type is meeting
    meeting_file = None
    if event_type == "meeting":
        meeting_file = create_meeting_file(event)
        if meeting_file:
            # Update event with meeting file reference
            event.context["meeting_file"] = str(meeting_file.relative_to(REPO_ROOT))
            file_content = generate_event_file(event)
            file_path.write_text(file_content, encoding="utf-8")

    result: dict[str, Any] = {
        "event_id": event_id,
        "title": title,
        "date": event_date.isoformat(),
        "time": parsed_time,
        "file_path": str(file_path.relative_to(REPO_ROOT)),
        "message": f"Created {event_id}: {title} on {event_date.isoformat()}",
    }

    if meeting_file:
        result["meeting_file"] = str(meeting_file.relative_to(REPO_ROOT))
        result["message"] += f" (meeting file: {meeting_file.name})"

    return result


def generate_event_file(event: CalendarEvent) -> str:
    """Generate the markdown content for an event file."""
    frontmatter: dict[str, Any] = {
        "id": event.id,
        "title": event.title,
        "type": event.type,
        "date": event.date.isoformat(),
        "time": event.time,
        "duration": event.duration,
        "end_date": event.end_date.isoformat() if event.end_date else None,
        "location": event.location,
        "participants": event.participants if event.participants else None,
        "recurrence": event.recurrence,
        "status": event.status,
        "reminder": event.reminder,
        "context": event.context if event.context else None,
        "tags": event.tags,
        "created": event.created.isoformat(),
    }

    # Remove None values for cleaner output
    frontmatter = {k: v for k, v in frontmatter.items() if v is not None}

    yaml_str = yaml.dump(
        frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False
    )

    description = event.description or "Brief description of the event."

    content = f"""---
{yaml_str.strip()}
---

# {event.id}: {event.title}

## Description

{description}

## Notes

Additional context or preparation needed.

## Updates

| Date | Update |
|------|--------|
| {event.created.isoformat()} | Created |
"""
    return content


def create_meeting_file(event: CalendarEvent) -> Path | None:
    """Create a meeting file for a meeting-type event."""
    # Determine meeting location based on participants
    if len(event.participants) == 1:
        # 1:1 meeting - place in person's folder
        person_slug = event.participants[0]
        meeting_dir = REPO_ROOT / "communication" / "people" / person_slug / "meetings"
    else:
        # Group meeting - place in meetings folder
        meeting_dir = MEETINGS_DIR

    meeting_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    date_str = event.date.isoformat()
    title_slug = re.sub(r"[^a-z0-9]+", "_", event.title.lower()).strip("_")[:30]
    filename = f"{date_str}_{title_slug}.md"
    file_path = meeting_dir / filename

    # Check if file already exists
    if file_path.exists():
        return file_path  # Return existing file

    # Generate meeting content
    participants_list = (
        "\n".join(f"  - {p}" for p in event.participants)
        if event.participants
        else "  - TBD"
    )

    content = f"""---
date: {event.date.isoformat()}
time: "{event.time or "TBD"}"
duration: "{event.duration or "30m"}"
location: "{event.location or "Remote"}"
participants:
{participants_list}
owner: chris_lemke
type: "{event.type}"
tags:
  - meeting
  - calendar
calendar_event: {event.id}
---

# {event.title}

**Link**: [Video Call Link]

## Goals
- What do we want to achieve in this meeting?

## Agenda
- Item 1
- Item 2
- Item 3

## Notes
- Key discussion points in bullet form.

## Decisions
- Decision 1 - who decided, what exactly

## Actions
- [ ] Owner - action description (due: YYYY-MM-DD)

## Risks / Issues
- Risk or issue - short description, potential impact, owner

## Follow-ups / Parking Lot
- Topic that didn't fit into this meeting but should be revisited later.
"""

    file_path.write_text(content, encoding="utf-8")
    return file_path


def get_event(event_id: str) -> dict[str, Any]:
    """Get details of a specific event."""
    # Normalize ID format
    event_id = event_id.upper()
    if not event_id.startswith("EVENT-"):
        # Handle various formats: "001", "E-001", "1"
        event_id = event_id.replace("E-", "").replace("EVENT", "")
        event_id = f"EVENT-{int(event_id):03d}"

    # Extract number
    match = re.search(r"\d+", event_id)
    if not match:
        return {"error": f"Invalid event ID: {event_id}"}

    file_num = int(match.group())
    file_path = CALENDAR_DIR / f"event_{file_num:03d}.md"

    if not file_path.exists():
        return {"error": f"Event not found: {event_id}"}

    event = parse_event_file(file_path)
    if not event:
        return {"error": f"Could not parse event: {event_id}"}

    result = event.to_dict()
    result["file_path"] = str(file_path.relative_to(REPO_ROOT))
    result["description"] = event.description
    return result


def update_event(event_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    """Update an existing event."""
    # Get existing event
    result = get_event(event_id)
    if "error" in result:
        return result

    file_path = REPO_ROOT / result["file_path"]
    event = parse_event_file(file_path)

    if not event:
        return {"error": f"Could not parse event: {event_id}"}

    today = date.today()

    # Apply updates
    for key, value in updates.items():
        if key == "date" and value:
            parsed = parse_date_strict(value)
            if parsed:
                event.date = parsed
            else:
                return {
                    "error": f"Invalid date format: '{value}'. "
                    f"Use YYYY-MM-DD format (e.g., {today.isoformat()}). "
                    f"Today is {today.isoformat()}."
                }
        elif key == "time":
            if value:
                parsed_time = parse_time_strict(value)
                if parsed_time:
                    event.time = parsed_time
                else:
                    return {
                        "error": f"Invalid time format: '{value}'. "
                        "Use HH:MM format in 24-hour notation (e.g., 14:30)."
                    }
            else:
                event.time = None
        elif key == "title":
            event.title = value
        elif key == "duration":
            event.duration = value
        elif key == "location":
            event.location = value
        elif key == "type":
            event.type = value
        elif key == "status":
            event.status = value
        elif key == "participants":
            if isinstance(value, str):
                event.participants = [p.strip() for p in value.split(",")]
            else:
                event.participants = value
        elif key == "description":
            event.description = value
        elif key == "reminder":
            event.reminder = value

    # Save updated file
    file_content = generate_event_file(event)
    file_path.write_text(file_content, encoding="utf-8")

    return {
        "event_id": event.id,
        "message": f"Updated {event.id}: {event.title}",
        "file_path": str(file_path.relative_to(REPO_ROOT)),
    }


def delete_event(event_id: str) -> dict[str, Any]:
    """Delete (cancel) an event."""
    # Get existing event
    result = get_event(event_id)
    if "error" in result:
        return result

    file_path = REPO_ROOT / result["file_path"]
    event = parse_event_file(file_path)

    if not event:
        return {"error": f"Could not parse event: {event_id}"}

    # Mark as cancelled instead of deleting
    event.status = "cancelled"

    # Save updated file
    file_content = generate_event_file(event)
    file_path.write_text(file_content, encoding="utf-8")

    return {
        "event_id": event.id,
        "message": f"Cancelled {event.id}: {event.title}",
        "file_path": str(file_path.relative_to(REPO_ROOT)),
    }


# ============================================================================
# Formatting Functions
# ============================================================================


def format_events_table(
    events: list[CalendarEvent], start_date: date, end_date: date
) -> str:
    """Format events as a markdown table."""
    if not events:
        return f"No events found between {start_date} and {end_date}."

    lines = [
        f"## Events: {start_date.strftime('%b %d, %Y')} - {end_date.strftime('%b %d, %Y')}",
        "",
        "| ID | Date | Time | Event | Type | Location |",
        "|:---|:-----|:-----|:------|:-----|:---------|",
    ]

    for event in events:
        date_str = event.date.strftime("%b %d")
        time_str = event.time or "All day"
        title = event.title[:35] + "..." if len(event.title) > 35 else event.title
        location = (event.location or "-")[:20]

        lines.append(
            f"| {event.id} | {date_str} | {time_str} | {title} | {event.type} | {location} |"
        )

    lines.append("")
    lines.append(f"*Total: {len(events)} event(s)*")

    return "\n".join(lines)


def format_calendar_view(
    events: list[CalendarEvent], start_date: date, end_date: date
) -> str:
    """Format events as a visual calendar grid."""
    lines: list[str] = []

    # Determine view type based on range
    days_range = (end_date - start_date).days + 1

    if days_range <= 7:
        # Week view
        lines.extend(format_week_view(events, start_date, end_date))
    else:
        # Month/multi-week view - show as table with weekly groupings
        lines.extend(format_month_view(events, start_date, end_date))

    # Add table listing
    lines.append("")
    lines.extend(format_events_table(events, start_date, end_date).split("\n"))

    return "\n".join(lines)


def format_week_view(
    events: list[CalendarEvent], start_date: date, end_date: date
) -> list[str]:
    """Format a week view calendar."""
    # Ensure we show full week (Mon-Sun)
    week_start = start_date - timedelta(days=start_date.weekday())
    week_end = week_start + timedelta(days=6)

    lines = [
        "```",
        "+" + "=" * 77 + "+",
        f"|{'CALENDAR: ' + week_start.strftime('%b %d') + ' - ' + week_end.strftime('%b %d, %Y'):^77}|",
        "+" + "=" * 12 + "+" + ("=" * 12 + "+") * 4 + "=" * 16 + "+",
    ]

    # Day headers
    header = "|"
    for i in range(5):
        d = week_start + timedelta(days=i)
        day_name = d.strftime("%a")
        header += f" {day_name} {d.day:02d}   |"
    header += f" {'Sat/Sun':^14} |"
    lines.append(header)
    lines.append("+" + "-" * 12 + "+" + ("-" * 12 + "+") * 4 + "-" * 16 + "+")

    # Group events by day
    events_by_day: dict[date, list[CalendarEvent]] = {}
    for event in events:
        if event.date not in events_by_day:
            events_by_day[event.date] = []
        events_by_day[event.date].append(event)

    # Find max events per day for row count
    max_events = max((len(e) for e in events_by_day.values()), default=0)
    max_events = max(max_events, 2)  # At least 2 rows

    # Generate rows for each event slot
    for row in range(max_events):
        # Time row
        time_row = "|"
        for i in range(5):  # Mon-Fri
            d = week_start + timedelta(days=i)
            day_events = events_by_day.get(d, [])
            if row < len(day_events):
                event = day_events[row]
                time_str = event.time[:5] if event.time else "     "
                time_row += f" {time_str}      |"
            else:
                time_row += "            |"

        # Weekend (Sat+Sun combined)
        weekend_events = events_by_day.get(
            week_start + timedelta(days=5), []
        ) + events_by_day.get(week_start + timedelta(days=6), [])
        if row < len(weekend_events):
            event = weekend_events[row]
            time_str = event.time[:5] if event.time else ""
            time_row += f" {time_str:^14} |"
        else:
            time_row += "                |"

        lines.append(time_row)

        # Title row
        title_row = "|"
        for i in range(5):
            d = week_start + timedelta(days=i)
            day_events = events_by_day.get(d, [])
            if row < len(day_events):
                event = day_events[row]
                title = event.title[:10]
                title_row += f" {title:<10} |"
            else:
                title_row += "            |"

        if row < len(weekend_events):
            event = weekend_events[row]
            title = event.title[:12]
            title_row += f" {title:<14} |"
        else:
            title_row += "                |"

        lines.append(title_row)

        # ID row
        id_row = "|"
        for i in range(5):
            d = week_start + timedelta(days=i)
            day_events = events_by_day.get(d, [])
            if row < len(day_events):
                event = day_events[row]
                id_str = f"[{event.id[-3:]}]"
                id_row += f" {id_str:<10} |"
            else:
                id_row += "            |"

        if row < len(weekend_events):
            event = weekend_events[row]
            id_str = f"[{event.id[-3:]}]"
            id_row += f" {id_str:<14} |"
        else:
            id_row += "                |"

        lines.append(id_row)

        # Separator between event slots
        if row < max_events - 1:
            lines.append("|" + " " * 12 + "|" + (" " * 12 + "|") * 4 + " " * 16 + "|")

    lines.append("+" + "=" * 12 + "+" + ("=" * 12 + "+") * 4 + "=" * 16 + "+")
    lines.append("```")

    return lines


def format_month_view(
    events: list[CalendarEvent], start_date: date, end_date: date
) -> list[str]:
    """Format a month view calendar."""
    lines = [
        f"## Calendar: {start_date.strftime('%B %Y')}",
        "",
    ]

    # Group events by week
    current = start_date - timedelta(days=start_date.weekday())

    while current <= end_date:
        week_end = current + timedelta(days=6)
        week_events = [e for e in events if current <= e.date <= week_end]

        if week_events:
            lines.append(f"### Week of {current.strftime('%b %d')}")
            lines.append("")
            for event in sorted(week_events, key=lambda e: (e.date, e.time or "00:00")):
                time_str = f" {event.time}" if event.time else ""
                lines.append(
                    f"- **{event.date.strftime('%a %d')}**{time_str}: {event.title} `{event.id}`"
                )
            lines.append("")

        current += timedelta(days=7)

    return lines


def format_json(events: list[CalendarEvent], start_date: date, end_date: date) -> str:
    """Format events as JSON."""
    result = {
        "range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        "count": len(events),
        "events": [e.to_dict() for e in events],
    }
    return json.dumps(result, indent=2, default=str)


# ============================================================================
# CLI Commands
# ============================================================================


def cmd_list(args: argparse.Namespace) -> None:
    """Command: list events."""
    range_str = " ".join(args.range) if args.range else "this week"
    start_date, end_date = parse_date_range(range_str)
    events = list_events(start_date, end_date)

    if args.format == "json":
        output = format_json(events, start_date, end_date)
    elif args.format == "calendar":
        output = format_calendar_view(events, start_date, end_date)
    else:
        output = format_events_table(events, start_date, end_date)

    print(output)


def cmd_create(args: argparse.Namespace) -> None:
    """Command: create event."""
    participants = None
    if args.participants:
        participants = [p.strip() for p in args.participants.split(",")]

    result = create_event(
        title=args.title,
        date_str=args.date,
        time=args.time,
        duration=args.duration,
        event_type=args.type or "appointment",
        location=args.location,
        participants=participants,
        project=args.project,
        ticket=args.ticket,
        recurrence=args.recurrence,
        description=args.description or "",
        reminder=args.reminder,
    )

    print(json.dumps(result, indent=2))
    sys.exit(1 if result.get("error") else 0)


def cmd_get(args: argparse.Namespace) -> None:
    """Command: get event details."""
    result = get_event(args.event_id)
    print(json.dumps(result, indent=2, default=str))
    sys.exit(1 if result.get("error") else 0)


def cmd_update(args: argparse.Namespace) -> None:
    """Command: update event."""
    updates: dict[str, Any] = {}
    if args.title:
        updates["title"] = args.title
    if args.date:
        updates["date"] = args.date
    if args.time:
        updates["time"] = args.time
    if args.duration:
        updates["duration"] = args.duration
    if args.location:
        updates["location"] = args.location
    if args.type:
        updates["type"] = args.type
    if args.status:
        updates["status"] = args.status
    if args.participants:
        updates["participants"] = args.participants
    if args.reminder:
        updates["reminder"] = args.reminder

    result = update_event(args.event_id, updates)
    print(json.dumps(result, indent=2))
    sys.exit(1 if result.get("error") else 0)


def cmd_delete(args: argparse.Namespace) -> None:
    """Command: delete event."""
    result = delete_event(args.event_id)
    print(json.dumps(result, indent=2))
    sys.exit(1 if result.get("error") else 0)


def cmd_next_id(args: argparse.Namespace) -> None:
    """Command: get next event ID."""
    print(json.dumps({"next_id": get_next_event_id()}))


# ============================================================================
# Main
# ============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calendar helper for opencode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # list command
    p_list = subparsers.add_parser("list", help="List events within a date range")
    p_list.add_argument(
        "range", nargs="*", help="Date range (e.g., 'this week', 'next month')"
    )
    p_list.add_argument(
        "--format", choices=["table", "calendar", "json"], default="table"
    )
    p_list.set_defaults(func=cmd_list)

    # create command
    p_create = subparsers.add_parser("create", help="Create a new event")
    p_create.add_argument("--title", required=True, help="Event title")
    p_create.add_argument("--date", required=True, help="Event date")
    p_create.add_argument("--time", help="Event time (HH:MM)")
    p_create.add_argument("--duration", help="Duration (e.g., 1h, 30m)")
    p_create.add_argument("--type", choices=EVENT_TYPES, help="Event type")
    p_create.add_argument("--location", help="Event location")
    p_create.add_argument("--participants", help="Comma-separated person slugs")
    p_create.add_argument("--project", help="Related project")
    p_create.add_argument("--ticket", help="Related ticket ID")
    p_create.add_argument(
        "--recurrence", choices=RECURRENCE_PATTERNS, help="Recurrence pattern"
    )
    p_create.add_argument("--description", help="Event description")
    p_create.add_argument(
        "--reminder",
        help="Reminder offset (e.g., 15m, 30m, 1h, 2h, 1d, 1w)",
    )
    p_create.set_defaults(func=cmd_create)

    # get command
    p_get = subparsers.add_parser("get", help="Get event details")
    p_get.add_argument("event_id", help="Event ID (e.g., EVENT-001 or 001)")
    p_get.set_defaults(func=cmd_get)

    # update command
    p_update = subparsers.add_parser("update", help="Update an event")
    p_update.add_argument("event_id", help="Event ID")
    p_update.add_argument("--title", help="New title")
    p_update.add_argument("--date", help="New date")
    p_update.add_argument("--time", help="New time")
    p_update.add_argument("--duration", help="New duration")
    p_update.add_argument("--location", help="New location")
    p_update.add_argument("--type", choices=EVENT_TYPES, help="New type")
    p_update.add_argument(
        "--status", choices=["scheduled", "completed", "cancelled"], help="New status"
    )
    p_update.add_argument("--participants", help="New participants (comma-separated)")
    p_update.add_argument(
        "--reminder",
        help="Reminder offset (e.g., 15m, 30m, 1h, 2h, 1d, 1w)",
    )
    p_update.set_defaults(func=cmd_update)

    # delete command
    p_delete = subparsers.add_parser("delete", help="Delete (cancel) an event")
    p_delete.add_argument("event_id", help="Event ID")
    p_delete.set_defaults(func=cmd_delete)

    # next-id command
    p_next = subparsers.add_parser("next-id", help="Get next available event ID")
    p_next.set_defaults(func=cmd_next_id)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
