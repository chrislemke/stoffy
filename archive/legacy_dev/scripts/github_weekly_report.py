#!/usr/bin/env python3
"""
GitHub Weekly Report Data Collector

Fetches weekly activity data from GitHub repositories owned by the
Artificial Intelligence team in the invia-flights organization.

Uses the GitHub CLI (gh) for efficient API access, outputting a compact
JSON summary for use in status report generation.

Usage:
    python scripts/github_weekly_report.py [--days N] [--output FILE] [--pretty]

Prerequisites:
    - GitHub CLI (gh) must be installed and authenticated via `gh auth login`
    - User must have access to invia-flights/artificial-intelligence team repos
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

# Configuration
ORG = "invia-flights"
TEAM_SLUG = "artificial-intelligence"
DEFAULT_BRANCH = "main"


def run_gh_api(
    endpoint: str,
    params: dict[str, str] | None = None,
    paginate: bool = False,
) -> Any:
    """
    Execute a GitHub API call using the gh CLI.

    Args:
        endpoint: API endpoint (e.g., '/orgs/{org}/teams/{team}/repos')
        params: Query parameters
        paginate: Whether to use pagination

    Returns:
        Parsed JSON response

    Raises:
        SystemExit: If the API call fails
    """
    # Build endpoint with query parameters
    if params:
        query_parts = [f"{key}={value}" for key, value in params.items()]
        endpoint = f"{endpoint}?{'&'.join(query_parts)}"

    cmd = ["gh", "api", endpoint]

    if paginate:
        cmd.append("--paginate")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        # Handle paginated results (multiple JSON objects)
        if paginate and result.stdout.strip():
            # gh --paginate outputs multiple JSON arrays, need to merge them
            lines = result.stdout.strip()
            # Try to parse as single JSON first
            try:
                return json.loads(lines)
            except json.JSONDecodeError:
                # Multiple JSON arrays, merge them
                items = []
                for line in lines.split("\n"):
                    if line.strip():
                        try:
                            parsed = json.loads(line)
                            if isinstance(parsed, list):
                                items.extend(parsed)
                            else:
                                items.append(parsed)
                        except json.JSONDecodeError:
                            continue
                return items
        return json.loads(result.stdout) if result.stdout.strip() else []
    except subprocess.CalledProcessError as e:
        print(f"Error calling gh API {endpoint}: {e.stderr}", file=sys.stderr)
        return [] if paginate else {}
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from {endpoint}: {e}", file=sys.stderr)
        return [] if paginate else {}


def get_team_repositories() -> list[dict[str, Any]]:
    """
    Fetch all repositories for the AI team.

    Returns:
        List of repository metadata dictionaries

    Raises:
        SystemExit: If team repositories cannot be fetched
    """
    endpoint = f"/orgs/{ORG}/teams/{TEAM_SLUG}/repos"
    repos = run_gh_api(endpoint, paginate=True)

    if not repos:
        print(
            f"Error: Could not fetch repositories for team {ORG}/{TEAM_SLUG}. "
            "Ensure you have access and are authenticated via 'gh auth login'.",
            file=sys.stderr,
        )
        sys.exit(1)

    return [
        {
            "name": repo["name"],
            "full_name": repo["full_name"],
            "url": repo["html_url"],
            "default_branch": repo.get("default_branch", DEFAULT_BRANCH),
            "description": repo.get("description", ""),
            "archived": repo.get("archived", False),
        }
        for repo in repos
        if not repo.get("archived", False)  # Skip archived repositories
    ]


def get_commits(
    repo_full_name: str,
    since: datetime,
    until: datetime,
    branch: str = DEFAULT_BRANCH,
) -> list[dict[str, Any]]:
    """Fetch commits on the default branch within the timeframe."""
    endpoint = f"/repos/{repo_full_name}/commits"
    params = {
        "sha": branch,
        "since": since.isoformat(),
        "until": until.isoformat(),
        "per_page": "100",
    }
    commits = run_gh_api(endpoint, params=params)

    if not isinstance(commits, list):
        return []

    return [
        {
            "sha": c["sha"][:7],
            "message": c["commit"]["message"].split("\n")[0][:100],
            "author": c["commit"]["author"]["name"],
            "date": c["commit"]["author"]["date"],
            "url": c["html_url"],
        }
        for c in commits
    ]


def get_pull_requests(
    repo_full_name: str,
    since: datetime,
    state: str = "all",
) -> list[dict[str, Any]]:
    """Fetch pull requests with activity in the timeframe."""
    endpoint = f"/repos/{repo_full_name}/pulls"
    params = {
        "state": state,
        "sort": "updated",
        "direction": "desc",
        "per_page": "100",
    }
    prs = run_gh_api(endpoint, params=params)

    if not isinstance(prs, list):
        return []

    since_ts = since.timestamp()
    results = []

    for pr in prs:
        # Check if PR has activity in the timeframe
        updated_at = datetime.fromisoformat(pr["updated_at"].replace("Z", "+00:00"))
        created_at = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
        merged_at = None
        closed_at = None

        if pr.get("merged_at"):
            merged_at = datetime.fromisoformat(pr["merged_at"].replace("Z", "+00:00"))
        if pr.get("closed_at"):
            closed_at = datetime.fromisoformat(pr["closed_at"].replace("Z", "+00:00"))

        # Skip if last update is before our window
        if updated_at.timestamp() < since_ts:
            continue

        # Determine PR status
        status = "open"
        if pr.get("merged_at"):
            status = "merged"
        elif pr["state"] == "closed":
            status = "closed"

        # Check what kind of activity happened in the window
        activity_in_window = []
        if created_at.timestamp() >= since_ts:
            activity_in_window.append("created")
        if merged_at and merged_at.timestamp() >= since_ts:
            activity_in_window.append("merged")
        if closed_at and closed_at.timestamp() >= since_ts and status == "closed":
            activity_in_window.append("closed")

        results.append(
            {
                "number": pr["number"],
                "title": pr["title"][:100],
                "status": status,
                "author": pr["user"]["login"],
                "created_at": pr["created_at"],
                "updated_at": pr["updated_at"],
                "merged_at": pr.get("merged_at"),
                "closed_at": pr.get("closed_at"),
                "url": pr["html_url"],
                "activity_in_window": activity_in_window,
            }
        )

    return results


def get_open_prs(repo_full_name: str) -> list[dict[str, Any]]:
    """Fetch currently open PRs for 'next week' inference."""
    endpoint = f"/repos/{repo_full_name}/pulls"
    params = {
        "state": "open",
        "sort": "updated",
        "direction": "desc",
        "per_page": "20",
    }
    prs = run_gh_api(endpoint, params=params)

    if not isinstance(prs, list):
        return []

    return [
        {
            "number": pr["number"],
            "title": pr["title"][:100],
            "author": pr["user"]["login"],
            "created_at": pr["created_at"],
            "url": pr["html_url"],
            "draft": pr.get("draft", False),
        }
        for pr in prs
    ]


def get_issues(
    repo_full_name: str,
    since: datetime,
    labels: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Fetch issues with activity in the timeframe or with critical labels."""
    endpoint = f"/repos/{repo_full_name}/issues"
    params = {
        "state": "all",
        "sort": "updated",
        "direction": "desc",
        "since": since.isoformat(),
        "per_page": "100",
    }
    if labels:
        params["labels"] = ",".join(labels)

    issues = run_gh_api(endpoint, params=params)

    if not isinstance(issues, list):
        return []

    # Filter out pull requests (GitHub API returns PRs as issues too)
    return [
        {
            "number": issue["number"],
            "title": issue["title"][:100],
            "state": issue["state"],
            "labels": [label["name"] for label in issue.get("labels", [])],
            "author": issue["user"]["login"],
            "created_at": issue["created_at"],
            "updated_at": issue["updated_at"],
            "closed_at": issue.get("closed_at"),
            "url": issue["html_url"],
        }
        for issue in issues
        if "pull_request" not in issue
    ]


def get_critical_issues(repo_full_name: str) -> list[dict[str, Any]]:
    """Fetch open issues with blocker or critical labels."""
    critical_labels = ["blocker", "critical", "priority:critical", "priority:high"]
    all_critical = []

    for label in critical_labels:
        endpoint = f"/repos/{repo_full_name}/issues"
        params = {
            "state": "open",
            "labels": label,
            "per_page": "10",
        }
        issues = run_gh_api(endpoint, params=params)

        if isinstance(issues, list):
            for issue in issues:
                if "pull_request" not in issue:
                    all_critical.append(
                        {
                            "number": issue["number"],
                            "title": issue["title"][:100],
                            "labels": [
                                label["name"] for label in issue.get("labels", [])
                            ],
                            "url": issue["html_url"],
                        }
                    )

    # Deduplicate by issue number
    seen = set()
    unique = []
    for issue in all_critical:
        if issue["number"] not in seen:
            seen.add(issue["number"])
            unique.append(issue)

    return unique


def collect_repo_data(
    repo: dict[str, Any],
    since: datetime,
    until: datetime,
) -> dict[str, Any]:
    """Collect all relevant data for a single repository."""
    full_name = repo["full_name"]
    branch = repo["default_branch"]

    commits = get_commits(full_name, since, until, branch)
    prs = get_pull_requests(full_name, since)
    open_prs = get_open_prs(full_name)
    issues = get_issues(full_name, since)
    critical_issues = get_critical_issues(full_name)

    # Categorize PRs
    merged_prs = [pr for pr in prs if pr["status"] == "merged"]
    closed_prs = [pr for pr in prs if pr["status"] == "closed"]
    created_prs = [pr for pr in prs if "created" in pr.get("activity_in_window", [])]

    # Determine if there was activity
    has_activity = bool(commits or merged_prs or closed_prs or created_prs or issues)

    return {
        "name": repo["name"],
        "full_name": full_name,
        "url": repo["url"],
        "description": repo["description"],
        "default_branch": branch,
        "has_activity": has_activity,
        "summary": {
            "total_commits": len(commits),
            "total_prs_with_activity": len(prs),
            "merged_prs": len(merged_prs),
            "created_prs": len(created_prs),
            "closed_prs": len(closed_prs),
            "open_prs": len(open_prs),
            "issues_with_activity": len(issues),
            "critical_issues": len(critical_issues),
        },
        "commits": commits[:10],  # Limit to 10 most recent
        "merged_prs": merged_prs,
        "created_prs": created_prs,
        "open_prs": open_prs[:5],  # Top 5 for "next week"
        "issues": issues[:10],  # Limit to 10 most recent
        "critical_issues": critical_issues,
    }


def generate_report(days: int = 7) -> dict[str, Any]:
    """Generate the complete weekly report data."""
    # Calculate time window
    now = datetime.now(UTC)
    until = now.replace(hour=23, minute=59, second=59, microsecond=0)
    since = (now - timedelta(days=days)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # Calculate ISO week
    iso_calendar = now.isocalendar()
    iso_week = f"{iso_calendar.year}-W{iso_calendar.week:02d}"

    print(f"Fetching team repositories from {ORG}/{TEAM_SLUG}...", file=sys.stderr)
    repos = get_team_repositories()
    print(f"Found {len(repos)} repositories", file=sys.stderr)

    # Collect data for each repository
    all_repos = []
    active_repos = []

    for i, repo in enumerate(repos, 1):
        print(f"Processing [{i}/{len(repos)}] {repo['name']}...", file=sys.stderr)
        repo_data = collect_repo_data(repo, since, until)
        all_repos.append(repo_data)
        if repo_data["has_activity"]:
            active_repos.append(repo_data)

    # Build final report
    report = {
        "metadata": {
            "generated_at": now.isoformat(),
            "iso_week": iso_week,
            "timeframe": {
                "start": since.isoformat(),
                "end": until.isoformat(),
                "days": days,
            },
            "organization": ORG,
            "team": TEAM_SLUG,
        },
        "summary": {
            "total_repositories": len(repos),
            "active_repositories": len(active_repos),
            "inactive_repositories": len(repos) - len(active_repos),
        },
        "active_projects": active_repos,
        "inactive_projects": [
            {"name": r["name"], "url": r["url"]}
            for r in all_repos
            if not r["has_activity"]
        ],
    }

    return report


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Collect GitHub weekly activity data for AI team repositories"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to look back (default: 7)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file path (default: stdout)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    args = parser.parse_args()

    report = generate_report(days=args.days)

    # Output
    indent = 2 if args.pretty else None
    json_output = json.dumps(report, indent=indent, ensure_ascii=False)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json_output)
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(json_output)


if __name__ == "__main__":
    main()
