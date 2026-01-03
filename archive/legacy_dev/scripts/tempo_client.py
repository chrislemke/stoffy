#!/usr/bin/env python3
"""
Tempo Timesheet Client for opencode

Fetches work logs from Tempo API and generates reports comparing
logged hours vs expected hours based on working patterns.

Usage:
    python tempo_client.py tempo-hours <names> [--weeks N]
    python tempo_client.py lookup-user <email>

Commands:
    tempo-hours <names>     Get tempo hours for comma-separated names
                            Names can be aliases (e.g., "alex,anna")
    lookup-user <email>     Look up Jira accountId for an email

Options:
    --weeks N               Number of weeks to look back (default: 1)

Environment Variables:
    TEMPO_API_TOKEN         Required: Tempo API token
    ATLASSIAN_URL           Required: Atlassian instance URL
    ATLASSIAN_USERNAME      Required: Atlassian username (email)
    ATLASSIAN_API_TOKEN     Required: Atlassian API token
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

# Try to import tempo client, provide helpful error if missing
try:
    from tempoapiclient import client_v4
except ImportError:
    print(
        json.dumps(
            {
                "error": "Missing tempo-api-python-client. Install with: pip install tempo-api-python-client"
            }
        )
    )
    sys.exit(1)


# =============================================================================
# Environment & Configuration
# =============================================================================


def find_project_root() -> Path:
    """Find project root by looking for .opencode folder or opencode.jsonc."""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "opencode.jsonc").exists() or (current / ".opencode").is_dir():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    # Fallback: assume we're in .opencode/tool
    return Path(__file__).resolve().parent.parent.parent


PROJECT_ROOT = find_project_root()


def load_env() -> dict[str, str]:
    """Load environment variables from .env file."""
    env_vars = {}
    env_file = PROJECT_ROOT / ".env"

    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    value = value.strip().strip("'\"")
                    env_vars[key.strip()] = value

    # Environment variables take precedence
    for key in [
        "TEMPO_API_TOKEN",
        "ATLASSIAN_URL",
        "ATLASSIAN_USERNAME",
        "ATLASSIAN_API_TOKEN",
    ]:
        if key in os.environ:
            env_vars[key] = os.environ[key]

    return env_vars


# =============================================================================
# Entity Resolution
# =============================================================================


def load_known_entities() -> dict[str, Any]:
    """Load known entities from JSON file."""
    entities_file = PROJECT_ROOT / ".opencode" / "data" / "known_entities.json"
    if not entities_file.exists():
        return {"people": {}}

    with open(entities_file) as f:
        return json.load(f)


def resolve_person_name(name: str, entities: dict[str, Any]) -> str | None:
    """
    Resolve a person name/alias to their entity key (slug).

    Args:
        name: Name or alias to resolve (e.g., "alex", "Alex Kumar", "anna")
        entities: Known entities dict

    Returns:
        Person slug (e.g., "alex_kumar") or None if not found
    """
    name_lower = name.strip().lower()
    people = entities.get("people", {})

    for slug, info in people.items():
        # Check slug directly
        if slug.lower() == name_lower:
            return slug

        # Check full name
        full_name = info.get("full_name", "")
        if full_name.lower() == name_lower:
            return slug

        # Check aliases
        aliases = info.get("aliases", [])
        for alias in aliases:
            if alias.lower() == name_lower:
                return slug

    return None


def resolve_person_names(names_str: str) -> list[dict[str, str]]:
    """
    Resolve comma-separated names to person slugs.

    Returns list of dicts with 'input', 'slug', 'folder' keys.
    """
    entities = load_known_entities()
    results = []

    for name in names_str.split(","):
        name = name.strip()
        if not name:
            continue

        slug = resolve_person_name(name, entities)
        if slug:
            folder = entities["people"][slug].get("folder", "")
            results.append({"input": name, "slug": slug, "folder": folder})
        else:
            results.append(
                {
                    "input": name,
                    "slug": None,
                    "folder": None,
                    "error": f"Unknown person: {name}",
                }
            )

    return results


# =============================================================================
# Profile Parsing
# =============================================================================


def get_profile_path(slug: str) -> Path:
    """Get path to person's profile.md."""
    return PROJECT_ROOT / "communication" / "people" / slug / "profile.md"


def get_email_from_profile(slug: str) -> str | None:
    """Extract email from profile.md."""
    profile_path = get_profile_path(slug)
    if not profile_path.exists():
        return None

    content = profile_path.read_text()

    # Look for email in table format: | Email | xxx@yyy.de |
    match = re.search(
        r"\|\s*Email\s*\|\s*([^\s|]+@[^\s|]+)\s*\|", content, re.IGNORECASE
    )
    if match:
        return match.group(1).strip()

    return None


def parse_working_pattern(slug: str) -> dict[str, Any]:
    """
    Parse working pattern from profile.md.

    Returns dict with:
        - weekly_hours: int (e.g., 40)
        - working_days: list of day names (e.g., ["Monday", "Tuesday", ...])
        - hours_per_day: float (e.g., 8.0)
        - pattern_description: str
    """
    profile_path = get_profile_path(slug)
    if not profile_path.exists():
        return {
            "weekly_hours": 40,
            "working_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "hours_per_day": 8.0,
            "pattern_description": "Default 40h/week (profile not found)",
        }

    content = profile_path.read_text()
    result = {
        "weekly_hours": 40,
        "working_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        "hours_per_day": 8.0,
        "pattern_description": "",
    }

    # Extract weekly hours: "40h / 40h" or "32h / 40h"
    hours_match = re.search(
        r"\|\s*Weekly hours\s*\|\s*(\d+)h\s*/\s*\d+h", content, re.IGNORECASE
    )
    if hours_match:
        result["weekly_hours"] = int(hours_match.group(1))

    # Extract working days per week
    days_match = re.search(
        r"\|\s*Working days per week\s*\|\s*(\d+)\s*\|", content, re.IGNORECASE
    )
    working_days_count = 5
    if days_match:
        working_days_count = int(days_match.group(1))

    # Extract working pattern description
    pattern_match = re.search(
        r"\|\s*Working pattern\s*\|\s*([^|]+)\|", content, re.IGNORECASE
    )
    if pattern_match:
        pattern_desc = pattern_match.group(1).strip()
        result["pattern_description"] = pattern_desc

        # Parse specific patterns
        pattern_lower = pattern_desc.lower()

        if "monday to thursday" in pattern_lower or "mon-thu" in pattern_lower:
            result["working_days"] = ["Monday", "Tuesday", "Wednesday", "Thursday"]
        elif "monday to friday" in pattern_lower or "mon-fri" in pattern_lower:
            result["working_days"] = [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
            ]
        elif "every day" in pattern_lower:
            # Works every day but we only count weekdays for business purposes
            result["working_days"] = [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
            ]
        elif "tuesday to friday" in pattern_lower:
            result["working_days"] = ["Tuesday", "Wednesday", "Thursday", "Friday"]
        else:
            # Default based on working_days_count
            all_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
            result["working_days"] = all_days[:working_days_count]

    # Calculate hours per day
    if result["working_days"]:
        result["hours_per_day"] = result["weekly_hours"] / len(result["working_days"])

    return result


# =============================================================================
# Jira User Lookup
# =============================================================================


def get_jira_account_id(email: str) -> str | None:
    """
    Look up Jira accountId by email using Jira REST API.
    """
    try:
        from atlassian import Jira
    except ImportError:
        print(
            json.dumps(
                {
                    "error": "Missing atlassian-python-api. Install with: pip install atlassian-python-api"
                }
            )
        )
        sys.exit(1)

    env = load_env()
    url = env.get("ATLASSIAN_URL")
    username = env.get("ATLASSIAN_USERNAME")
    token = env.get("ATLASSIAN_API_TOKEN")

    if not all([url, username, token]):
        return None

    jira = Jira(url=url, username=username, password=token, cloud=True)  # type: ignore

    try:
        # Search for user by email using the user_find_by_user_string method
        users = jira.user_find_by_user_string(query=email, limit=1)
        if users and len(users) > 0:
            return users[0].get("accountId")

        # Try searching with just the username part of email
        email_prefix = email.split("@")[0]
        users = jira.user_find_by_user_string(query=email_prefix, limit=10)
        if users:
            for user in users:
                user_email = user.get("emailAddress", "")
                if user_email.lower() == email.lower():
                    return user.get("accountId")

    except Exception:
        # Log error but don't fail - try alternative approach
        pass

    return None


# =============================================================================
# Tempo API
# =============================================================================


def get_tempo_client():
    """Create and return Tempo API client."""
    env = load_env()
    token = env.get("TEMPO_API_TOKEN")

    if not token:
        raise ValueError("Missing TEMPO_API_TOKEN in environment")

    return client_v4.Tempo(auth_token=token)


def extract_issue_key_from_description(description: str) -> str | None:
    """Extract issue key (e.g., FML-220) from description text."""
    if not description:
        return None

    # Common ticket patterns: FML-123, FLUG-12345, DS-1234, etc.
    match = re.search(r"\b([A-Z]+-\d+)\b", description)
    if match:
        return match.group(1)
    return None


def get_worklogs_for_user(
    account_id: str, date_from: date, date_to: date
) -> list[dict[str, Any]]:
    """
    Fetch worklogs for a user from Tempo API.

    Returns list of worklog dicts with: date, issue_key, hours, minutes, description
    """
    tempo = get_tempo_client()

    try:
        worklogs = tempo.get_worklogs(
            dateFrom=date_from.isoformat(),
            dateTo=date_to.isoformat(),
            accountId=account_id,
        )

        results = []
        for wl in worklogs:
            time_spent = wl.get("timeSpentSeconds", 0)
            hours = time_spent // 3600
            minutes = (time_spent % 3600) // 60

            # Try to get issue key from issue object first
            issue = wl.get("issue", {})
            issue_key = issue.get("key") if isinstance(issue, dict) else None

            # If no key in issue object, try to extract from description
            description = wl.get("description", "")
            if not issue_key:
                issue_key = extract_issue_key_from_description(description)

            # Fallback to issue ID if available
            if not issue_key and isinstance(issue, dict) and issue.get("id"):
                issue_key = f"#{issue.get('id')}"

            if not issue_key:
                issue_key = "Unknown"

            results.append(
                {
                    "date": wl.get("startDate"),
                    "issue_key": issue_key,
                    "hours": hours,
                    "minutes": minutes,
                    "time_spent_seconds": time_spent,
                    "description": description,
                }
            )

        return results

    except Exception as e:
        raise RuntimeError(f"Failed to fetch worklogs: {e}")


# =============================================================================
# Date Range Calculation
# =============================================================================


def get_last_week_range(weeks_back: int = 1) -> tuple[date, date]:
    """
    Get date range for the last complete week(s).

    Returns (monday, sunday) of the week that was `weeks_back` weeks ago.
    """
    today = date.today()

    # Find the Monday of the current week
    current_monday = today - timedelta(days=today.weekday())

    # Go back the specified number of weeks
    target_monday = current_monday - timedelta(weeks=weeks_back)
    target_sunday = target_monday + timedelta(days=6)

    return target_monday, target_sunday


def get_iso_week(d: date) -> str:
    """Get ISO week string like '2025-W50'."""
    return f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}"


# =============================================================================
# Report Generation
# =============================================================================


def format_time(hours: int, minutes: int) -> str:
    """Format time as 'Xh Ym'."""
    if hours == 0 and minutes == 0:
        return "0h"
    if hours == 0:
        return f"{minutes}m"
    if minutes == 0:
        return f"{hours}h"
    return f"{hours}h {minutes}m"


def format_decimal_hours(total_seconds: int) -> str:
    """Format seconds as decimal hours like '7.5h'."""
    hours = total_seconds / 3600
    return f"{hours:.1f}h"


def generate_tempo_report(
    person_slug: str,
    worklogs: list[dict[str, Any]],
    working_pattern: dict[str, Any],
    date_from: date,
    date_to: date,
) -> str:
    """
    Generate markdown report comparing logged vs expected hours.
    """
    iso_week = get_iso_week(date_from)

    # Group worklogs by date
    daily_worklogs: dict[str, list[dict]] = defaultdict(list)
    for wl in worklogs:
        daily_worklogs[wl["date"]].append(wl)

    # Calculate daily totals
    daily_totals: dict[str, int] = {}
    for day_str, day_wls in daily_worklogs.items():
        daily_totals[day_str] = sum(wl["time_spent_seconds"] for wl in day_wls)

    # Build day-by-day summary
    working_days_set = set(working_pattern["working_days"])
    expected_seconds_per_day = int(working_pattern["hours_per_day"] * 3600)

    day_rows = []
    total_logged = 0
    total_expected = 0

    current = date_from
    while current <= date_to:
        day_name = current.strftime("%A")
        day_str = current.isoformat()
        logged_seconds = daily_totals.get(day_str, 0)
        total_logged += logged_seconds

        # Only expect hours on working days
        if day_name in working_days_set:
            expected = expected_seconds_per_day
            total_expected += expected
        else:
            expected = 0

        # Format row
        logged_fmt = format_time(logged_seconds // 3600, (logged_seconds % 3600) // 60)
        expected_fmt = (
            format_time(expected // 3600, (expected % 3600) // 60)
            if expected > 0
            else "-"
        )

        # Status indicator
        if expected == 0:
            status = "📅 Off"
        elif logged_seconds >= expected:
            diff = logged_seconds - expected
            if diff > 0:
                status = f"✅ +{format_time(diff // 3600, (diff % 3600) // 60)}"
            else:
                status = "✅"
        else:
            diff = expected - logged_seconds
            if logged_seconds == 0:
                status = f"❌ -{format_time(diff // 3600, (diff % 3600) // 60)}"
            elif diff > 1800:  # More than 30 min under
                status = f"⚠️ -{format_time(diff // 3600, (diff % 3600) // 60)}"
            else:
                status = f"✅ -{format_time(diff // 3600, (diff % 3600) // 60)}"

        day_rows.append(
            f"| {current.strftime('%a %d')} | {expected_fmt} | {logged_fmt} | {status} |"
        )

        current += timedelta(days=1)

    # Calculate percentage
    percentage = (total_logged / total_expected * 100) if total_expected > 0 else 0

    # Format totals
    total_logged_fmt = format_time(total_logged // 3600, (total_logged % 3600) // 60)
    total_expected_fmt = format_time(
        total_expected // 3600, (total_expected % 3600) // 60
    )

    # Overall status
    if percentage >= 95:
        overall_status = "✅ Good"
    elif percentage >= 80:
        overall_status = "⚠️ Slightly Under"
    else:
        overall_status = "❌ Significantly Under"

    # Build worklog details table
    worklog_rows = []
    for wl in sorted(worklogs, key=lambda x: (x["date"], x["issue_key"])):
        time_fmt = format_time(wl["hours"], wl["minutes"])
        desc = wl.get("description", "")[:50]  # Truncate long descriptions
        if len(wl.get("description", "")) > 50:
            desc += "..."
        worklog_rows.append(
            f"| {wl['date']} | {wl['issue_key']} | {time_fmt} | {desc} |"
        )

    # Build the report
    report = f"""## Week {iso_week} ({date_from.isoformat()} to {date_to.isoformat()})

### Summary

| Day | Expected | Logged | Status |
|-----|----------|--------|--------|
{chr(10).join(day_rows)}

**Total**: {total_logged_fmt} logged / {total_expected_fmt} expected ({percentage:.1f}%) - {overall_status}

**Working Pattern**: {working_pattern.get("pattern_description", "Standard")} ({working_pattern["weekly_hours"]}h/week)

### Worklog Details

| Date | Ticket | Time | Description |
|------|--------|------|-------------|
{chr(10).join(worklog_rows) if worklog_rows else "| - | - | - | No worklogs found |"}

---
*Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}*
"""

    return report


# =============================================================================
# Main Commands
# =============================================================================


def cmd_tempo_hours(args: list[str]) -> None:
    """Get tempo hours for specified people."""
    if not args:
        print(json.dumps({"error": "Usage: tempo-hours <names> [--weeks N]"}))
        sys.exit(1)

    # Parse arguments
    names_str = args[0]
    weeks_back = 1

    for i, arg in enumerate(args[1:], 1):
        if arg == "--weeks" and i + 1 < len(args):
            weeks_back = int(args[i + 1])

    # Get date range
    date_from, date_to = get_last_week_range(weeks_back)

    # Resolve person names
    people = resolve_person_names(names_str)

    results = []
    for person in people:
        person_result = {
            "input": person["input"],
            "slug": person.get("slug"),
            "success": False,
        }

        if person.get("error"):
            person_result["error"] = person["error"]
            results.append(person_result)
            continue

        slug = person["slug"]
        folder = person.get("folder", "")

        # Get email from profile
        email = get_email_from_profile(slug)
        if not email:
            person_result["error"] = f"No email found in profile for {slug}"
            results.append(person_result)
            continue

        person_result["email"] = email

        # Get Jira account ID
        account_id = get_jira_account_id(email)
        if not account_id:
            person_result["error"] = f"Could not find Jira account for {email}"
            results.append(person_result)
            continue

        person_result["account_id"] = account_id

        # Get working pattern
        working_pattern = parse_working_pattern(slug)
        person_result["working_pattern"] = working_pattern

        # Fetch worklogs
        try:
            worklogs = get_worklogs_for_user(account_id, date_from, date_to)
            person_result["worklogs"] = worklogs
            person_result["worklog_count"] = len(worklogs)

            # Calculate totals
            total_seconds = sum(wl["time_spent_seconds"] for wl in worklogs)
            person_result["total_logged_seconds"] = total_seconds
            person_result["total_logged_hours"] = total_seconds / 3600

            # Calculate expected
            working_days_in_range = 0
            current = date_from
            working_days_set = set(working_pattern["working_days"])
            while current <= date_to:
                if current.strftime("%A") in working_days_set:
                    working_days_in_range += 1
                current += timedelta(days=1)

            expected_seconds = int(
                working_days_in_range * working_pattern["hours_per_day"] * 3600
            )
            person_result["total_expected_seconds"] = expected_seconds
            person_result["total_expected_hours"] = expected_seconds / 3600
            person_result["percentage"] = (
                (total_seconds / expected_seconds * 100) if expected_seconds > 0 else 0
            )

            # Generate report
            report = generate_tempo_report(
                slug, worklogs, working_pattern, date_from, date_to
            )
            person_result["report"] = report

            # Determine output path
            tempo_file = PROJECT_ROOT / folder / "tempo.md" if folder else None
            person_result["tempo_file"] = str(tempo_file) if tempo_file else None

            person_result["success"] = True

        except Exception as e:
            person_result["error"] = str(e)

        results.append(person_result)

    output = {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "iso_week": get_iso_week(date_from),
        "weeks_back": weeks_back,
        "results": results,
    }

    print(json.dumps(output, indent=2, default=str))


def cmd_lookup_user(args: list[str]) -> None:
    """Look up Jira accountId for an email."""
    if not args:
        print(json.dumps({"error": "Usage: lookup-user <email>"}))
        sys.exit(1)

    email = args[0]
    account_id = get_jira_account_id(email)

    if account_id:
        print(json.dumps({"email": email, "account_id": account_id}))
    else:
        print(json.dumps({"email": email, "error": "Account not found"}))
        sys.exit(1)


# =============================================================================
# CLI Entry Point
# =============================================================================

COMMANDS = {
    "tempo-hours": cmd_tempo_hours,
    "lookup-user": cmd_lookup_user,
}


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nAvailable commands:", ", ".join(COMMANDS.keys()))
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    if command in ("--help", "-h", "help"):
        print(__doc__)
        sys.exit(0)

    if command not in COMMANDS:
        print(
            json.dumps(
                {
                    "error": f"Unknown command: {command}. Available: {', '.join(COMMANDS.keys())}"
                }
            )
        )
        sys.exit(1)

    COMMANDS[command](args)


if __name__ == "__main__":
    main()
