#!/usr/bin/env python3
"""
Calendar Reminder Daemon for opencode

Monitors calendar events and sends notifications when reminder times are reached.
Supports both macOS native notifications and terminal output.

Usage:
    python scripts/calendar_reminder.py check     # Check and send due reminders
    python scripts/calendar_reminder.py status    # Show pending reminders
    python scripts/calendar_reminder.py clear     # Clear reminder state
    python scripts/calendar_reminder.py test      # Send a test notification

Reminder Format:
    Events with a 'reminder' field in their frontmatter will trigger notifications.
    Supported formats: 15m, 30m, 1h, 2h, 1d, 2d, 1w (minutes, hours, days, weeks)

State Tracking:
    Sent reminders are tracked in calendar/events/.reminder_state.json to prevent
    duplicate notifications. The state file is gitignored.

Installation:
    Run 'make install-reminder-daemon' to install as a macOS LaunchAgent that
    runs every 5 minutes automatically.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

import yaml

# ============================================================================
# Configuration
# ============================================================================

REPO_ROOT = Path(__file__).parent.parent
CALENDAR_DIR = REPO_ROOT / "calendar" / "events"
STATE_FILE = CALENDAR_DIR / ".reminder_state.json"

# Notification settings
APP_NAME = "Calendar Reminder"
NOTIFICATION_SOUND = "default"  # macOS notification sound

# Reminder time units in minutes
REMINDER_UNITS: dict[str, int] = {
    "m": 1,  # minutes
    "h": 60,  # hours
    "d": 60 * 24,  # days
    "w": 60 * 24 * 7,  # weeks
}

# Event type emoji mapping
EVENT_EMOJIS: dict[str, str] = {
    "meeting": "\U0001f4c5",  # calendar
    "reminder": "\U0001f514",  # bell
    "deadline": "\u23f0",  # alarm clock
    "appointment": "\U0001f4cb",  # clipboard
    "personal": "\U0001f3e0",  # house
    "holiday": "\U0001f389",  # party
    "vacation": "\u2708\ufe0f",  # airplane
    "blocked": "\U0001f6ab",  # no entry
}


# ============================================================================
# Data Classes
# ============================================================================


class CalendarEvent:
    """Represents a calendar event parsed from a markdown file."""

    def __init__(
        self,
        id: str,
        title: str,
        event_date: date,
        time: str | None = None,
        event_type: str = "appointment",
        location: str | None = None,
        status: str = "scheduled",
        reminder: str | None = None,
        file_path: Path | None = None,
    ) -> None:
        self.id = id
        self.title = title
        self.date = event_date
        self.time = time
        self.type = event_type
        self.location = location
        self.status = status
        self.reminder = reminder
        self.file_path = file_path

    @property
    def datetime(self) -> datetime:
        """Get the event datetime. If no time specified, defaults to 00:00."""
        if self.time:
            try:
                hour, minute = map(int, self.time.split(":"))
                return datetime.combine(
                    self.date, datetime.min.time().replace(hour=hour, minute=minute)
                )
            except (ValueError, AttributeError):
                pass
        return datetime.combine(self.date, datetime.min.time())

    @property
    def state_key(self) -> str:
        """Unique key for state tracking (handles recurring events)."""
        return f"{self.id}:{self.date.isoformat()}"

    def __repr__(self) -> str:
        return f"CalendarEvent(id={self.id!r}, title={self.title!r}, date={self.date}, time={self.time})"


# ============================================================================
# Reminder Parsing
# ============================================================================


def parse_reminder_offset(reminder: str | None) -> timedelta | None:
    """
    Parse a reminder string into a timedelta offset.

    Args:
        reminder: String like "30m", "1h", "2d", "1w"

    Returns:
        timedelta or None if parsing fails

    Examples:
        >>> parse_reminder_offset("30m")
        timedelta(minutes=30)
        >>> parse_reminder_offset("1h")
        timedelta(hours=1)
        >>> parse_reminder_offset("2d")
        timedelta(days=2)
    """
    if not reminder:
        return None

    reminder = reminder.strip().lower()
    match = re.match(r"^(\d+)([mhdw])$", reminder)

    if not match:
        return None

    value = int(match.group(1))
    unit = match.group(2)

    minutes = value * REMINDER_UNITS.get(unit, 0)
    if minutes <= 0:
        return None

    return timedelta(minutes=minutes)


def format_time_until(delta: timedelta) -> str:
    """
    Format a timedelta into human-readable "time until" string.

    Args:
        delta: The time difference

    Returns:
        Human-readable string like "30 minutes", "2 hours", "1 day"
    """
    total_minutes = int(delta.total_seconds() / 60)

    if total_minutes < 0:
        return "now"
    elif total_minutes < 60:
        return f"{total_minutes} minute{'s' if total_minutes != 1 else ''}"
    elif total_minutes < 60 * 24:
        hours = total_minutes // 60
        return f"{hours} hour{'s' if hours != 1 else ''}"
    else:
        days = total_minutes // (60 * 24)
        return f"{days} day{'s' if days != 1 else ''}"


# ============================================================================
# Event Parsing
# ============================================================================


def parse_event_file(file_path: Path) -> CalendarEvent | None:
    """
    Parse a calendar event from a markdown file.

    Args:
        file_path: Path to the event markdown file

    Returns:
        CalendarEvent or None if parsing fails
    """
    try:
        content = file_path.read_text(encoding="utf-8")

        # Extract YAML frontmatter
        if not content.startswith("---"):
            return None

        parts = content.split("---", 2)
        if len(parts) < 3:
            return None

        frontmatter = yaml.safe_load(parts[1])
        if not frontmatter:
            return None

        # Parse date
        event_date = frontmatter.get("date")
        if isinstance(event_date, str):
            event_date = date.fromisoformat(event_date)
        elif isinstance(event_date, datetime):
            event_date = event_date.date()
        elif not isinstance(event_date, date):
            return None

        return CalendarEvent(
            id=frontmatter.get("id", ""),
            title=frontmatter.get("title", "Untitled Event"),
            event_date=event_date,
            time=frontmatter.get("time"),
            event_type=frontmatter.get("type", "appointment"),
            location=frontmatter.get("location"),
            status=frontmatter.get("status", "scheduled"),
            reminder=frontmatter.get("reminder"),
            file_path=file_path,
        )

    except Exception:
        # Silent failure - don't log unless in debug mode
        return None


def get_events_with_reminders() -> list[CalendarEvent]:
    """
    Get all calendar events that have a reminder set.

    Returns:
        List of CalendarEvent objects with reminder field set
    """
    events = []

    if not CALENDAR_DIR.exists():
        return events

    for file_path in CALENDAR_DIR.glob("event_*.md"):
        event = parse_event_file(file_path)
        if event and event.reminder and event.status != "cancelled":
            events.append(event)

    return events


# ============================================================================
# State Management
# ============================================================================


def load_state() -> dict[str, str]:
    """
    Load the reminder state from the state file.

    Returns:
        Dictionary mapping state_key to ISO timestamp when reminder was sent
    """
    if not STATE_FILE.exists():
        return {}

    try:
        content = STATE_FILE.read_text(encoding="utf-8")
        return json.loads(content)
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(state: dict[str, str]) -> None:
    """
    Save the reminder state to the state file.

    Args:
        state: Dictionary mapping state_key to ISO timestamp
    """
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def is_reminder_sent(state: dict[str, str], event: CalendarEvent) -> bool:
    """
    Check if a reminder has already been sent for this event.

    Args:
        state: Current state dictionary
        event: The calendar event

    Returns:
        True if reminder was already sent
    """
    return event.state_key in state


def mark_reminder_sent(state: dict[str, str], event: CalendarEvent) -> None:
    """
    Mark a reminder as sent in the state.

    Args:
        state: Current state dictionary (modified in place)
        event: The calendar event
    """
    state[event.state_key] = datetime.now().isoformat()


def cleanup_old_state(state: dict[str, str], days_to_keep: int = 30) -> dict[str, str]:
    """
    Remove state entries older than the specified number of days.

    Args:
        state: Current state dictionary
        days_to_keep: Number of days to keep entries

    Returns:
        Cleaned state dictionary
    """
    cutoff = datetime.now() - timedelta(days=days_to_keep)
    cleaned = {}

    for key, timestamp_str in state.items():
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            if timestamp >= cutoff:
                cleaned[key] = timestamp_str
        except (ValueError, TypeError):
            # Keep entries we can't parse (safer than deleting)
            cleaned[key] = timestamp_str

    return cleaned


# ============================================================================
# Notifications
# ============================================================================


def send_macos_notification(title: str, message: str, subtitle: str = "") -> bool:
    """
    Send a macOS notification using terminal-notifier (preferred) or osascript fallback.

    Args:
        title: Notification title
        message: Notification body
        subtitle: Optional subtitle

    Returns:
        True if notification was sent successfully
    """
    # Try terminal-notifier first (more reliable, works with any terminal)
    try:
        cmd = [
            "terminal-notifier",
            "-title",
            title,
            "-message",
            message,
            "-sound",
            "default",
        ]
        if subtitle:
            cmd.extend(["-subtitle", subtitle])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return True
    except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
        pass  # Fall back to osascript

    # Fallback to osascript
    title = title.replace('"', '\\"').replace("\\", "\\\\")
    message = message.replace('"', '\\"').replace("\\", "\\\\")
    subtitle = subtitle.replace('"', '\\"').replace("\\", "\\\\")

    script = f'display notification "{message}" with title "{title}"'
    if subtitle:
        script += f' subtitle "{subtitle}"'

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def send_terminal_notification(title: str, message: str) -> None:
    """
    Send a terminal notification (colored output with bell).

    Args:
        title: Notification title
        message: Notification body
    """
    # ANSI color codes
    bold = "\033[1m"
    blue = "\033[94m"
    yellow = "\033[93m"
    reset = "\033[0m"
    bell = "\a"

    print(f"{bell}{bold}{blue}[{APP_NAME}]{reset} {bold}{title}{reset}")
    print(f"  {yellow}{message}{reset}")
    print()


def send_notification(event: CalendarEvent, time_until: timedelta) -> bool:
    """
    Send notifications for an event (both macOS and terminal).

    Args:
        event: The calendar event
        time_until: Time until the event starts

    Returns:
        True if at least one notification was sent successfully
    """
    emoji = EVENT_EMOJIS.get(event.type, "\U0001f4c5")
    time_str = format_time_until(time_until)

    # Build notification content
    if time_until.total_seconds() <= 0:
        title = f"{emoji} {event.title} - NOW"
    else:
        title = f"{emoji} {event.title} in {time_str}"

    # Build message body
    parts = []
    if event.time:
        parts.append(f"At {event.time}")
    if event.location:
        parts.append(event.location)

    message = " - ".join(parts) if parts else f"Event: {event.title}"

    # Send both notifications
    macos_success = send_macos_notification(title, message)
    send_terminal_notification(title, message)

    return macos_success


# ============================================================================
# Commands
# ============================================================================


def cmd_check() -> int:
    """
    Check for due reminders and send notifications.

    Returns:
        Exit code (0 = success, 1 = error)
    """
    now = datetime.now()
    state = load_state()
    state = cleanup_old_state(state)  # Clean up old entries

    events = get_events_with_reminders()
    notifications_sent = 0

    for event in events:
        # Skip if reminder already sent
        if is_reminder_sent(state, event):
            continue

        # Skip past events
        if event.datetime < now - timedelta(hours=1):
            continue

        # Parse reminder offset
        offset = parse_reminder_offset(event.reminder)
        if not offset:
            continue

        # Calculate when to notify
        notify_at = event.datetime - offset

        # Check if it's time to notify
        if now >= notify_at:
            time_until = event.datetime - now
            if send_notification(event, time_until):
                mark_reminder_sent(state, event)
                notifications_sent += 1

    # Save updated state
    save_state(state)

    return 0


def cmd_status() -> int:
    """
    Show pending reminders.

    Returns:
        Exit code (0 = success)
    """
    now = datetime.now()
    state = load_state()
    events = get_events_with_reminders()

    # Separate into pending and already notified
    pending: list[tuple[CalendarEvent, datetime, timedelta]] = []
    notified: list[CalendarEvent] = []

    for event in events:
        # Skip past events
        if event.datetime < now - timedelta(hours=1):
            continue

        offset = parse_reminder_offset(event.reminder)
        if not offset:
            continue

        notify_at = event.datetime - offset

        if is_reminder_sent(state, event):
            notified.append(event)
        elif notify_at > now:
            # Future reminder
            pending.append((event, notify_at, event.datetime - now))
        else:
            # Due now but not yet sent
            pending.append((event, notify_at, event.datetime - now))

    # Print pending reminders
    if pending:
        print("\n\033[1mPending Reminders:\033[0m\n")
        pending.sort(key=lambda x: x[1])  # Sort by notify_at time

        for event, notify_at, time_until in pending:
            emoji = EVENT_EMOJIS.get(event.type, "\U0001f4c5")
            time_str = event.time or "All day"
            notify_in = notify_at - now

            if notify_in.total_seconds() <= 0:
                notify_status = "\033[93m(due now)\033[0m"
            else:
                notify_status = f"(notifies in {format_time_until(notify_in)})"

            print(f"  {emoji} {event.title}")
            print(f"     Date: {event.date} at {time_str}")
            print(f"     Reminder: {event.reminder} before {notify_status}")
            print()
    else:
        print("\nNo pending reminders.\n")

    # Print already notified
    if notified:
        print(f"\033[90mAlready notified: {len(notified)} event(s)\033[0m\n")

    return 0


def cmd_clear() -> int:
    """
    Clear the reminder state file.

    Returns:
        Exit code (0 = success)
    """
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print("Reminder state cleared.")
    else:
        print("No state file to clear.")
    return 0


def cmd_test() -> int:
    """
    Send a test notification.

    Returns:
        Exit code (0 = success, 1 = notification failed)
    """
    print("Sending test notification...")

    title = "\U0001f514 Test Reminder"
    message = "Calendar reminder system is working!"

    macos_success = send_macos_notification(title, message)
    send_terminal_notification(title, message)

    if macos_success:
        print("\033[92mmacOS notification sent successfully!\033[0m")
    else:
        print("\033[91mmacOS notification failed (check permissions)\033[0m")

    return 0 if macos_success else 1


# ============================================================================
# Main
# ============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calendar reminder daemon",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("check", help="Check and send due reminders")
    subparsers.add_parser("status", help="Show pending reminders")
    subparsers.add_parser("clear", help="Clear reminder state")
    subparsers.add_parser("test", help="Send a test notification")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands: dict[str, Any] = {
        "check": cmd_check,
        "status": cmd_status,
        "clear": cmd_clear,
        "test": cmd_test,
    }

    exit_code = commands[args.command]()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
