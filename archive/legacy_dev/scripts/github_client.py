#!/usr/bin/env python3
"""
GitHub Client for LLM-Assisted Workflows

Comprehensive access to GitHub repositories, pull requests, issues, releases,
and workflow runs via the GitHub CLI (gh). Designed for easy consumption by
LLM agents with Google-style docstrings and full type annotations.

Usage:
    python scripts/github_client.py <command> [args...]

Commands:
    # Authentication
    auth-status                          Check GitHub authentication status

    # Repositories
    list-repos [--limit N] [--type TYPE] List user's accessible repositories
    list-org-repos <org> [--limit N]     List repositories in an organization
    list-team-repos <org> <team>         List repositories for a team
    get-repo <owner/repo>                Get detailed repository information
    search-repos <query> [--owner ORG]   Search repositories

    # Pull Requests
    list-prs <owner/repo> [--state STATE] [--limit N]
    get-pr <owner/repo> <number>         Get detailed PR information

    # Issues
    list-issues <owner/repo> [--state STATE] [--limit N]
    get-issue <owner/repo> <number>      Get detailed issue information

    # Releases
    list-releases <owner/repo> [--limit N]

    # Actions/Workflows
    list-runs <owner/repo> [--status STATUS] [--limit N]

    # Organizations
    list-teams <org>                     List teams in an organization

Prerequisites:
    - GitHub CLI (gh) must be installed: https://cli.github.com/
    - Must be authenticated via `gh auth login`

Examples:
    # Check if authenticated
    python scripts/github_client.py auth-status

    # List all repos you have access to
    python scripts/github_client.py list-repos --limit 50

    # List repos for the AI team
    python scripts/github_client.py list-team-repos invia-flights artificial-intelligence

    # Get details about a specific repo
    python scripts/github_client.py get-repo invia-flights/flight-recommender

    # List open PRs
    python scripts/github_client.py list-prs invia-flights/flight-recommender --state open

    # Search for ML-related repos
    python scripts/github_client.py search-repos "machine learning" --owner invia-flights
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any

# =============================================================================
# Constants
# =============================================================================

DEFAULT_LIMIT = 30

# JSON fields to request for each resource type (optimized for LLM consumption)
REPO_FIELDS = [
    "name",
    "nameWithOwner",
    "description",
    "url",
    "defaultBranchRef",
    "visibility",
    "primaryLanguage",
    "isArchived",
    "isFork",
    "isPrivate",
    "createdAt",
    "updatedAt",
    "pushedAt",
    "stargazerCount",
    "forkCount",
    "diskUsage",
    "repositoryTopics",
]

PR_FIELDS = [
    "number",
    "title",
    "state",
    "author",
    "baseRefName",
    "headRefName",
    "url",
    "createdAt",
    "updatedAt",
    "mergedAt",
    "closedAt",
    "isDraft",
    "labels",
    "assignees",
    "reviewDecision",
    "additions",
    "deletions",
    "changedFiles",
]

ISSUE_FIELDS = [
    "number",
    "title",
    "state",
    "author",
    "url",
    "createdAt",
    "updatedAt",
    "closedAt",
    "labels",
    "assignees",
    "comments",
    "milestone",
]

RELEASE_FIELDS = [
    "tagName",
    "name",
    "isDraft",
    "isPrerelease",
    "isLatest",
    "publishedAt",
    "createdAt",
]

RUN_FIELDS = [
    "databaseId",
    "displayTitle",
    "workflowName",
    "status",
    "conclusion",
    "headBranch",
    "event",
    "createdAt",
    "updatedAt",
    "url",
]


# =============================================================================
# Core Functions
# =============================================================================


def run_gh_command(
    args: list[str],
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """
    Execute a GitHub CLI command.

    Args:
        args: Command arguments to pass to gh (e.g., ["repo", "list"]).
        check: Whether to raise an exception on non-zero exit code.

    Returns:
        CompletedProcess with stdout and stderr.

    Raises:
        subprocess.CalledProcessError: If check=True and command fails.

    Example:
        >>> result = run_gh_command(["repo", "list", "--limit", "10"])
        >>> print(result.stdout)
    """
    cmd = ["gh"] + args
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=check,
    )


def _parse_paginated_output(stdout: str) -> list[Any]:
    """Parse paginated output that may contain multiple JSON arrays."""
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        pass

    # Multiple JSON arrays, merge them
    items: list[Any] = []
    for line in stdout.strip().split("\n"):
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
            if isinstance(parsed, list):
                items.extend(parsed)
            else:
                items.append(parsed)
        except json.JSONDecodeError:
            continue
    return items


def run_gh_api(
    endpoint: str,
    params: dict[str, str] | None = None,
    paginate: bool = False,
) -> Any:
    """
    Execute a GitHub API call using the gh CLI.

    Args:
        endpoint: API endpoint (e.g., '/orgs/{org}/teams').
        params: Query parameters to append to the endpoint.
        paginate: Whether to fetch all pages of results.

    Returns:
        Parsed JSON response (list or dict depending on endpoint).

    Raises:
        SystemExit: Prints error JSON and exits on failure.

    Example:
        >>> teams = run_gh_api("/orgs/invia-flights/teams")
        >>> for team in teams:
        ...     print(team["name"])
    """
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

        if not result.stdout.strip():
            return [] if paginate else {}

        if paginate:
            return _parse_paginated_output(result.stdout)

        return json.loads(result.stdout)

    except subprocess.CalledProcessError as e:
        return {"error": f"GitHub API error: {e.stderr.strip()}", "endpoint": endpoint}
    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse JSON: {e}", "endpoint": endpoint}


def check_auth() -> dict[str, Any]:
    """
    Check GitHub CLI authentication status.

    Returns:
        Dict with authentication status, including:
        - authenticated: bool indicating if user is logged in
        - username: GitHub username if authenticated
        - scopes: List of token scopes
        - error: Error message if not authenticated

    Example:
        >>> status = check_auth()
        >>> if status["authenticated"]:
        ...     print(f"Logged in as {status['username']}")
    """
    result = run_gh_command(["auth", "status"], check=False)

    if result.returncode != 0:
        return {
            "authenticated": False,
            "error": "Not authenticated. Run 'gh auth login' to authenticate.",
            "hint": "gh auth login",
            "stderr": result.stderr.strip(),
        }

    # Parse auth status output
    output = result.stderr  # gh auth status writes to stderr
    lines = output.strip().split("\n")

    status: dict[str, Any] = {
        "authenticated": True,
        "host": "github.com",
    }

    for line in lines:
        line = line.strip()
        if "Logged in to" in line:
            # Extract host
            parts = line.split("account")
            if len(parts) > 1:
                username = parts[1].strip().split()[0]
                status["username"] = username
        elif "Token scopes:" in line:
            scopes_str = line.split(":", 1)[1].strip().strip("'")
            status["scopes"] = [s.strip() for s in scopes_str.split(",")]

    return status


# =============================================================================
# Repository Functions
# =============================================================================


def list_repos(
    limit: int = DEFAULT_LIMIT,
    repo_type: str = "all",
    visibility: str | None = None,
    language: str | None = None,
) -> dict[str, Any]:
    """
    List repositories accessible to the authenticated user.

    Args:
        limit: Maximum number of repositories to return.
        repo_type: Filter by type - 'all', 'owner', 'member', or 'forks'.
        visibility: Filter by visibility - 'public', 'private', or 'internal'.
        language: Filter by primary programming language.

    Returns:
        Dict containing:
        - repos: List of repository objects with name, url, description, etc.
        - total: Number of repositories returned.
        - error: Error message if request failed.

    Example:
        >>> result = list_repos(limit=10, repo_type="owner")
        >>> for repo in result["repos"]:
        ...     print(repo["name"])
    """
    cmd = [
        "repo",
        "list",
        "--limit",
        str(limit),
        "--json",
        ",".join(REPO_FIELDS),
    ]

    if visibility:
        cmd.extend(["--visibility", visibility])

    if language:
        cmd.extend(["--language", language])

    # repo_type maps to specific flags
    if repo_type == "forks":
        cmd.append("--fork")
    elif repo_type == "source":
        cmd.append("--source")

    result = run_gh_command(cmd, check=False)

    if result.returncode != 0:
        return {"error": result.stderr.strip(), "repos": [], "total": 0}

    try:
        repos = json.loads(result.stdout) if result.stdout.strip() else []
        return {
            "repos": [_format_repo(r) for r in repos],
            "total": len(repos),
        }
    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse response: {e}", "repos": [], "total": 0}


def list_org_repos(
    org: str,
    limit: int = DEFAULT_LIMIT,
    visibility: str | None = None,
    language: str | None = None,
) -> dict[str, Any]:
    """
    List repositories in an organization.

    Args:
        org: Organization name (e.g., 'invia-flights').
        limit: Maximum number of repositories to return.
        visibility: Filter by visibility - 'public', 'private', or 'internal'.
        language: Filter by primary programming language.

    Returns:
        Dict containing:
        - repos: List of repository objects.
        - total: Number of repositories returned.
        - org: Organization name.
        - error: Error message if request failed.

    Example:
        >>> result = list_org_repos("invia-flights", limit=50)
        >>> print(f"Found {result['total']} repos in {result['org']}")
    """
    cmd = [
        "repo",
        "list",
        org,
        "--limit",
        str(limit),
        "--json",
        ",".join(REPO_FIELDS),
    ]

    if visibility:
        cmd.extend(["--visibility", visibility])

    if language:
        cmd.extend(["--language", language])

    result = run_gh_command(cmd, check=False)

    if result.returncode != 0:
        return {"error": result.stderr.strip(), "repos": [], "total": 0, "org": org}

    try:
        repos = json.loads(result.stdout) if result.stdout.strip() else []
        return {
            "repos": [_format_repo(r) for r in repos],
            "total": len(repos),
            "org": org,
        }
    except json.JSONDecodeError as e:
        return {
            "error": f"Failed to parse response: {e}",
            "repos": [],
            "total": 0,
            "org": org,
        }


def list_team_repos(
    org: str,
    team: str,
    limit: int = DEFAULT_LIMIT,
) -> dict[str, Any]:
    """
    List repositories accessible to a team.

    Args:
        org: Organization name (e.g., 'invia-flights').
        team: Team slug (e.g., 'artificial-intelligence').
        limit: Maximum number of repositories to return.

    Returns:
        Dict containing:
        - repos: List of repository objects.
        - total: Number of repositories returned.
        - org: Organization name.
        - team: Team slug.
        - error: Error message if request failed.

    Example:
        >>> result = list_team_repos("invia-flights", "artificial-intelligence")
        >>> for repo in result["repos"]:
        ...     print(f"{repo['name']}: {repo['description']}")
    """
    endpoint = f"/orgs/{org}/teams/{team}/repos"
    params = {"per_page": str(min(limit, 100))}

    repos_raw = run_gh_api(endpoint, params=params, paginate=True)

    if isinstance(repos_raw, dict) and repos_raw.get("error"):
        return {
            "error": repos_raw["error"],
            "repos": [],
            "total": 0,
            "org": org,
            "team": team,
        }

    if not isinstance(repos_raw, list):
        repos_raw = []

    # Filter out archived repos and limit
    repos = [
        _format_repo_from_api(r)
        for r in repos_raw[:limit]
        if not r.get("archived", False)
    ]

    return {
        "repos": repos,
        "total": len(repos),
        "org": org,
        "team": team,
    }


def get_repo(repo: str) -> dict[str, Any]:
    """
    Get detailed information about a repository.

    Args:
        repo: Repository in 'owner/repo' format (e.g., 'invia-flights/flight-recommender').

    Returns:
        Dict containing repository details:
        - name, full_name, description, url
        - default_branch, visibility, language
        - is_archived, is_fork, is_private
        - stars, forks, disk_usage_kb
        - topics, created_at, updated_at, pushed_at
        - error: Error message if request failed.

    Example:
        >>> repo = get_repo("invia-flights/flight-recommender")
        >>> print(f"{repo['name']}: {repo['description']}")
        >>> print(f"Stars: {repo['stars']}, Forks: {repo['forks']}")
    """
    cmd = [
        "repo",
        "view",
        repo,
        "--json",
        ",".join(REPO_FIELDS),
    ]

    result = run_gh_command(cmd, check=False)

    if result.returncode != 0:
        return {"error": result.stderr.strip(), "repo": repo}

    try:
        data = json.loads(result.stdout)
        return _format_repo(data)
    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse response: {e}", "repo": repo}


def search_repos(
    query: str,
    owner: str | None = None,
    language: str | None = None,
    limit: int = DEFAULT_LIMIT,
    visibility: str | None = None,
) -> dict[str, Any]:
    """
    Search for repositories on GitHub.

    Args:
        query: Search query (e.g., 'machine learning', 'flight recommender').
        owner: Filter by owner/organization (e.g., 'invia-flights').
        language: Filter by programming language (e.g., 'python').
        limit: Maximum number of results to return.
        visibility: Filter by visibility - 'public', 'private', or 'internal'.

    Returns:
        Dict containing:
        - repos: List of matching repository objects.
        - total: Number of results returned.
        - query: Original search query.
        - error: Error message if request failed.

    Example:
        >>> result = search_repos("flight ML", owner="invia-flights")
        >>> for repo in result["repos"]:
        ...     print(f"{repo['full_name']}: {repo['description']}")
    """
    cmd = [
        "search",
        "repos",
        query,
        "--limit",
        str(limit),
        "--json",
        "name,fullName,description,url,defaultBranch,visibility,language,"
        "isArchived,isFork,isPrivate,createdAt,updatedAt,stargazersCount,forksCount",
    ]

    if owner:
        cmd.extend(["--owner", owner])

    if language:
        cmd.extend(["--language", language])

    if visibility:
        cmd.extend(["--visibility", visibility])

    result = run_gh_command(cmd, check=False)

    if result.returncode != 0:
        return {"error": result.stderr.strip(), "repos": [], "total": 0, "query": query}

    try:
        repos = json.loads(result.stdout) if result.stdout.strip() else []
        return {
            "repos": [_format_repo_from_search(r) for r in repos],
            "total": len(repos),
            "query": query,
        }
    except json.JSONDecodeError as e:
        return {
            "error": f"Failed to parse response: {e}",
            "repos": [],
            "total": 0,
            "query": query,
        }


# =============================================================================
# Pull Request Functions
# =============================================================================


def list_prs(
    repo: str,
    state: str = "open",
    limit: int = DEFAULT_LIMIT,
    author: str | None = None,
    label: str | None = None,
    base: str | None = None,
) -> dict[str, Any]:
    """
    List pull requests in a repository.

    Args:
        repo: Repository in 'owner/repo' format.
        state: Filter by state - 'open', 'closed', 'merged', or 'all'.
        limit: Maximum number of PRs to return.
        author: Filter by author username.
        label: Filter by label.
        base: Filter by base branch.

    Returns:
        Dict containing:
        - prs: List of pull request objects.
        - total: Number of PRs returned.
        - repo: Repository name.
        - state: Filter state used.
        - error: Error message if request failed.

    Example:
        >>> result = list_prs("invia-flights/flight-recommender", state="open")
        >>> for pr in result["prs"]:
        ...     print(f"#{pr['number']}: {pr['title']} ({pr['state']})")
    """
    cmd = [
        "pr",
        "list",
        "--repo",
        repo,
        "--state",
        state,
        "--limit",
        str(limit),
        "--json",
        ",".join(PR_FIELDS),
    ]

    if author:
        cmd.extend(["--author", author])

    if label:
        cmd.extend(["--label", label])

    if base:
        cmd.extend(["--base", base])

    result = run_gh_command(cmd, check=False)

    if result.returncode != 0:
        return {
            "error": result.stderr.strip(),
            "prs": [],
            "total": 0,
            "repo": repo,
            "state": state,
        }

    try:
        prs = json.loads(result.stdout) if result.stdout.strip() else []
        return {
            "prs": [_format_pr(pr) for pr in prs],
            "total": len(prs),
            "repo": repo,
            "state": state,
        }
    except json.JSONDecodeError as e:
        return {
            "error": f"Failed to parse response: {e}",
            "prs": [],
            "total": 0,
            "repo": repo,
            "state": state,
        }


def get_pr(repo: str, number: int) -> dict[str, Any]:
    """
    Get detailed information about a pull request.

    Args:
        repo: Repository in 'owner/repo' format.
        number: Pull request number.

    Returns:
        Dict containing PR details:
        - number, title, state, author, url
        - base_branch, head_branch
        - created_at, updated_at, merged_at, closed_at
        - is_draft, labels, assignees
        - review_decision, additions, deletions, changed_files
        - error: Error message if request failed.

    Example:
        >>> pr = get_pr("invia-flights/flight-recommender", 123)
        >>> print(f"PR #{pr['number']}: {pr['title']}")
        >>> print(f"Changes: +{pr['additions']} -{pr['deletions']}")
    """
    cmd = [
        "pr",
        "view",
        str(number),
        "--repo",
        repo,
        "--json",
        ",".join(PR_FIELDS),
    ]

    result = run_gh_command(cmd, check=False)

    if result.returncode != 0:
        return {"error": result.stderr.strip(), "repo": repo, "number": number}

    try:
        data = json.loads(result.stdout)
        return _format_pr(data)
    except json.JSONDecodeError as e:
        return {
            "error": f"Failed to parse response: {e}",
            "repo": repo,
            "number": number,
        }


# =============================================================================
# Issue Functions
# =============================================================================


def list_issues(
    repo: str,
    state: str = "open",
    limit: int = DEFAULT_LIMIT,
    author: str | None = None,
    label: str | None = None,
    assignee: str | None = None,
) -> dict[str, Any]:
    """
    List issues in a repository.

    Args:
        repo: Repository in 'owner/repo' format.
        state: Filter by state - 'open', 'closed', or 'all'.
        limit: Maximum number of issues to return.
        author: Filter by author username.
        label: Filter by label.
        assignee: Filter by assignee username.

    Returns:
        Dict containing:
        - issues: List of issue objects.
        - total: Number of issues returned.
        - repo: Repository name.
        - state: Filter state used.
        - error: Error message if request failed.

    Example:
        >>> result = list_issues("invia-flights/flight-recommender", state="open")
        >>> for issue in result["issues"]:
        ...     print(f"#{issue['number']}: {issue['title']}")
    """
    cmd = [
        "issue",
        "list",
        "--repo",
        repo,
        "--state",
        state,
        "--limit",
        str(limit),
        "--json",
        ",".join(ISSUE_FIELDS),
    ]

    if author:
        cmd.extend(["--author", author])

    if label:
        cmd.extend(["--label", label])

    if assignee:
        cmd.extend(["--assignee", assignee])

    result = run_gh_command(cmd, check=False)

    if result.returncode != 0:
        return {
            "error": result.stderr.strip(),
            "issues": [],
            "total": 0,
            "repo": repo,
            "state": state,
        }

    try:
        issues = json.loads(result.stdout) if result.stdout.strip() else []
        return {
            "issues": [_format_issue(issue) for issue in issues],
            "total": len(issues),
            "repo": repo,
            "state": state,
        }
    except json.JSONDecodeError as e:
        return {
            "error": f"Failed to parse response: {e}",
            "issues": [],
            "total": 0,
            "repo": repo,
            "state": state,
        }


def get_issue(repo: str, number: int) -> dict[str, Any]:
    """
    Get detailed information about an issue.

    Args:
        repo: Repository in 'owner/repo' format.
        number: Issue number.

    Returns:
        Dict containing issue details:
        - number, title, state, author, url
        - created_at, updated_at, closed_at
        - labels, assignees, comments_count
        - milestone
        - error: Error message if request failed.

    Example:
        >>> issue = get_issue("invia-flights/flight-recommender", 45)
        >>> print(f"Issue #{issue['number']}: {issue['title']}")
        >>> print(f"State: {issue['state']}, Comments: {issue['comments_count']}")
    """
    cmd = [
        "issue",
        "view",
        str(number),
        "--repo",
        repo,
        "--json",
        ",".join(ISSUE_FIELDS),
    ]

    result = run_gh_command(cmd, check=False)

    if result.returncode != 0:
        return {"error": result.stderr.strip(), "repo": repo, "number": number}

    try:
        data = json.loads(result.stdout)
        return _format_issue(data)
    except json.JSONDecodeError as e:
        return {
            "error": f"Failed to parse response: {e}",
            "repo": repo,
            "number": number,
        }


# =============================================================================
# Release Functions
# =============================================================================


def list_releases(
    repo: str,
    limit: int = DEFAULT_LIMIT,
    exclude_drafts: bool = False,
    exclude_prereleases: bool = False,
) -> dict[str, Any]:
    """
    List releases in a repository.

    Args:
        repo: Repository in 'owner/repo' format.
        limit: Maximum number of releases to return.
        exclude_drafts: Exclude draft releases.
        exclude_prereleases: Exclude pre-releases.

    Returns:
        Dict containing:
        - releases: List of release objects.
        - total: Number of releases returned.
        - repo: Repository name.
        - error: Error message if request failed.

    Example:
        >>> result = list_releases("invia-flights/flight-recommender")
        >>> for release in result["releases"]:
        ...     print(f"{release['tag_name']}: {release['name']}")
    """
    cmd = [
        "release",
        "list",
        "--repo",
        repo,
        "--limit",
        str(limit),
        "--json",
        ",".join(RELEASE_FIELDS),
    ]

    if exclude_drafts:
        cmd.append("--exclude-drafts")

    if exclude_prereleases:
        cmd.append("--exclude-pre-releases")

    result = run_gh_command(cmd, check=False)

    if result.returncode != 0:
        return {
            "error": result.stderr.strip(),
            "releases": [],
            "total": 0,
            "repo": repo,
        }

    try:
        releases = json.loads(result.stdout) if result.stdout.strip() else []
        return {
            "releases": [_format_release(r) for r in releases],
            "total": len(releases),
            "repo": repo,
        }
    except json.JSONDecodeError as e:
        return {
            "error": f"Failed to parse response: {e}",
            "releases": [],
            "total": 0,
            "repo": repo,
        }


# =============================================================================
# Actions/Workflow Functions
# =============================================================================


def list_runs(
    repo: str,
    limit: int = DEFAULT_LIMIT,
    status: str | None = None,
    branch: str | None = None,
    workflow: str | None = None,
    event: str | None = None,
) -> dict[str, Any]:
    """
    List workflow runs in a repository.

    Args:
        repo: Repository in 'owner/repo' format.
        limit: Maximum number of runs to return.
        status: Filter by status - 'queued', 'in_progress', 'completed',
                'success', 'failure', 'cancelled', etc.
        branch: Filter by branch name.
        workflow: Filter by workflow name or filename.
        event: Filter by triggering event (e.g., 'push', 'pull_request').

    Returns:
        Dict containing:
        - runs: List of workflow run objects.
        - total: Number of runs returned.
        - repo: Repository name.
        - error: Error message if request failed.

    Example:
        >>> result = list_runs("invia-flights/flight-recommender", status="failure")
        >>> for run in result["runs"]:
        ...     print(f"{run['workflow_name']}: {run['conclusion']} ({run['branch']})")
    """
    cmd = [
        "run",
        "list",
        "--repo",
        repo,
        "--limit",
        str(limit),
        "--json",
        ",".join(RUN_FIELDS),
    ]

    if status:
        cmd.extend(["--status", status])

    if branch:
        cmd.extend(["--branch", branch])

    if workflow:
        cmd.extend(["--workflow", workflow])

    if event:
        cmd.extend(["--event", event])

    result = run_gh_command(cmd, check=False)

    if result.returncode != 0:
        return {"error": result.stderr.strip(), "runs": [], "total": 0, "repo": repo}

    try:
        runs = json.loads(result.stdout) if result.stdout.strip() else []
        return {
            "runs": [_format_run(r) for r in runs],
            "total": len(runs),
            "repo": repo,
        }
    except json.JSONDecodeError as e:
        return {
            "error": f"Failed to parse response: {e}",
            "runs": [],
            "total": 0,
            "repo": repo,
        }


# =============================================================================
# Organization Functions
# =============================================================================


def list_teams(org: str) -> dict[str, Any]:
    """
    List teams in an organization.

    Args:
        org: Organization name (e.g., 'invia-flights').

    Returns:
        Dict containing:
        - teams: List of team objects with slug, name, description, privacy.
        - total: Number of teams returned.
        - org: Organization name.
        - error: Error message if request failed.

    Example:
        >>> result = list_teams("invia-flights")
        >>> for team in result["teams"]:
        ...     print(f"{team['slug']}: {team['name']}")
    """
    endpoint = f"/orgs/{org}/teams"
    teams_raw = run_gh_api(endpoint, paginate=True)

    if isinstance(teams_raw, dict) and teams_raw.get("error"):
        return {"error": teams_raw["error"], "teams": [], "total": 0, "org": org}

    if not isinstance(teams_raw, list):
        teams_raw = []

    teams = [
        {
            "slug": t.get("slug"),
            "name": t.get("name"),
            "description": t.get("description"),
            "privacy": t.get("privacy"),
            "url": f"https://github.com/orgs/{org}/teams/{t.get('slug')}",
        }
        for t in teams_raw
    ]

    return {
        "teams": teams,
        "total": len(teams),
        "org": org,
    }


# =============================================================================
# Formatting Helpers
# =============================================================================


def _extract_topic_names(topics: list[Any]) -> list[str]:
    """Extract topic names from nested repository topics structure."""
    topic_names: list[str] = []
    for t in topics:
        if isinstance(t, dict):
            topic_node = t.get("topic") or {}
            name = topic_node.get("name")
            if name:
                topic_names.append(name)
        elif isinstance(t, str):
            topic_names.append(t)
    return topic_names


def _format_repo(data: dict[str, Any]) -> dict[str, Any]:
    """Format repository data from gh repo list/view."""
    default_branch_ref = data.get("defaultBranchRef") or {}
    primary_language = data.get("primaryLanguage") or {}
    topics = data.get("repositoryTopics") or []
    visibility = data.get("visibility")

    return {
        "name": data.get("name"),
        "full_name": data.get("nameWithOwner"),
        "description": data.get("description"),
        "url": data.get("url"),
        "default_branch": default_branch_ref.get("name"),
        "visibility": visibility.lower() if visibility else None,
        "language": primary_language.get("name") if primary_language else None,
        "is_archived": data.get("isArchived", False),
        "is_fork": data.get("isFork", False),
        "is_private": data.get("isPrivate", False),
        "stars": data.get("stargazerCount", 0),
        "forks": data.get("forkCount", 0),
        "disk_usage_kb": data.get("diskUsage"),
        "topics": _extract_topic_names(topics) if isinstance(topics, list) else [],
        "created_at": data.get("createdAt"),
        "updated_at": data.get("updatedAt"),
        "pushed_at": data.get("pushedAt"),
    }


def _format_repo_from_api(data: dict[str, Any]) -> dict[str, Any]:
    """Format repository data from direct API calls."""
    return {
        "name": data.get("name"),
        "full_name": data.get("full_name"),
        "description": data.get("description"),
        "url": data.get("html_url"),
        "default_branch": data.get("default_branch"),
        "visibility": data.get("visibility"),
        "language": data.get("language"),
        "is_archived": data.get("archived", False),
        "is_fork": data.get("fork", False),
        "is_private": data.get("private", False),
        "stars": data.get("stargazers_count", 0),
        "forks": data.get("forks_count", 0),
        "disk_usage_kb": data.get("size"),
        "topics": data.get("topics", []),
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
        "pushed_at": data.get("pushed_at"),
    }


def _format_repo_from_search(data: dict[str, Any]) -> dict[str, Any]:
    """Format repository data from search results."""
    return {
        "name": data.get("name"),
        "full_name": data.get("fullName"),
        "description": data.get("description"),
        "url": data.get("url"),
        "default_branch": data.get("defaultBranch"),
        "visibility": data.get("visibility", "").lower()
        if data.get("visibility")
        else None,
        "language": data.get("language"),
        "is_archived": data.get("isArchived", False),
        "is_fork": data.get("isFork", False),
        "is_private": data.get("isPrivate", False),
        "stars": data.get("stargazersCount", 0),
        "forks": data.get("forksCount", 0),
        "created_at": data.get("createdAt"),
        "updated_at": data.get("updatedAt"),
    }


def _extract_names(items: list[dict[str, Any]], key: str) -> list[str]:
    """Extract values for a key from a list of dicts, filtering out empty values."""
    return [item.get(key) for item in items if item.get(key)]


def _format_pr(data: dict[str, Any]) -> dict[str, Any]:
    """Format pull request data."""
    author = data.get("author") or {}
    labels = data.get("labels") or []
    assignees = data.get("assignees") or []
    state = data.get("state")

    return {
        "number": data.get("number"),
        "title": data.get("title"),
        "state": state.lower() if state else None,
        "author": author.get("login"),
        "base_branch": data.get("baseRefName"),
        "head_branch": data.get("headRefName"),
        "url": data.get("url"),
        "created_at": data.get("createdAt"),
        "updated_at": data.get("updatedAt"),
        "merged_at": data.get("mergedAt"),
        "closed_at": data.get("closedAt"),
        "is_draft": data.get("isDraft", False),
        "labels": _extract_names(labels, "name"),
        "assignees": _extract_names(assignees, "login"),
        "review_decision": data.get("reviewDecision"),
        "additions": data.get("additions", 0),
        "deletions": data.get("deletions", 0),
        "changed_files": data.get("changedFiles", 0),
    }


def _format_issue(data: dict[str, Any]) -> dict[str, Any]:
    """Format issue data."""
    author = data.get("author") or {}
    labels = data.get("labels") or []
    assignees = data.get("assignees") or []
    milestone = data.get("milestone") or {}
    comments = data.get("comments") or []
    state = data.get("state")

    return {
        "number": data.get("number"),
        "title": data.get("title"),
        "state": state.lower() if state else None,
        "author": author.get("login"),
        "url": data.get("url"),
        "created_at": data.get("createdAt"),
        "updated_at": data.get("updatedAt"),
        "closed_at": data.get("closedAt"),
        "labels": _extract_names(labels, "name"),
        "assignees": _extract_names(assignees, "login"),
        "comments_count": len(comments) if isinstance(comments, list) else 0,
        "milestone": milestone.get("title"),
    }


def _format_release(data: dict[str, Any]) -> dict[str, Any]:
    """Format release data."""
    return {
        "tag_name": data.get("tagName"),
        "name": data.get("name"),
        "is_draft": data.get("isDraft", False),
        "is_prerelease": data.get("isPrerelease", False),
        "is_latest": data.get("isLatest", False),
        "published_at": data.get("publishedAt"),
        "created_at": data.get("createdAt"),
    }


def _format_run(data: dict[str, Any]) -> dict[str, Any]:
    """Format workflow run data."""
    return {
        "id": data.get("databaseId"),
        "title": data.get("displayTitle"),
        "workflow_name": data.get("workflowName"),
        "status": data.get("status", "").lower() if data.get("status") else None,
        "conclusion": data.get("conclusion", "").lower()
        if data.get("conclusion")
        else None,
        "branch": data.get("headBranch"),
        "event": data.get("event"),
        "created_at": data.get("createdAt"),
        "updated_at": data.get("updatedAt"),
        "url": data.get("url"),
    }


# =============================================================================
# CLI Commands
# =============================================================================


def cmd_auth_status(_args: argparse.Namespace) -> None:
    """Command: auth-status"""
    result = check_auth()
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("authenticated") else 1)


def cmd_list_repos(args: argparse.Namespace) -> None:
    """Command: list-repos"""
    result = list_repos(
        limit=args.limit,
        repo_type=args.type,
        visibility=args.visibility,
        language=args.language,
    )
    print(json.dumps(result, indent=2 if args.pretty else None))
    sys.exit(0 if not result.get("error") else 1)


def cmd_list_org_repos(args: argparse.Namespace) -> None:
    """Command: list-org-repos"""
    result = list_org_repos(
        org=args.org,
        limit=args.limit,
        visibility=args.visibility,
        language=args.language,
    )
    print(json.dumps(result, indent=2 if args.pretty else None))
    sys.exit(0 if not result.get("error") else 1)


def cmd_list_team_repos(args: argparse.Namespace) -> None:
    """Command: list-team-repos"""
    result = list_team_repos(
        org=args.org,
        team=args.team,
        limit=args.limit,
    )
    print(json.dumps(result, indent=2 if args.pretty else None))
    sys.exit(0 if not result.get("error") else 1)


def cmd_get_repo(args: argparse.Namespace) -> None:
    """Command: get-repo"""
    result = get_repo(repo=args.repo)
    print(json.dumps(result, indent=2 if args.pretty else None))
    sys.exit(0 if not result.get("error") else 1)


def cmd_search_repos(args: argparse.Namespace) -> None:
    """Command: search-repos"""
    result = search_repos(
        query=args.query,
        owner=args.owner,
        language=args.language,
        limit=args.limit,
        visibility=args.visibility,
    )
    print(json.dumps(result, indent=2 if args.pretty else None))
    sys.exit(0 if not result.get("error") else 1)


def cmd_list_prs(args: argparse.Namespace) -> None:
    """Command: list-prs"""
    result = list_prs(
        repo=args.repo,
        state=args.state,
        limit=args.limit,
        author=args.author,
        label=args.label,
        base=args.base,
    )
    print(json.dumps(result, indent=2 if args.pretty else None))
    sys.exit(0 if not result.get("error") else 1)


def cmd_get_pr(args: argparse.Namespace) -> None:
    """Command: get-pr"""
    result = get_pr(repo=args.repo, number=args.number)
    print(json.dumps(result, indent=2 if args.pretty else None))
    sys.exit(0 if not result.get("error") else 1)


def cmd_list_issues(args: argparse.Namespace) -> None:
    """Command: list-issues"""
    result = list_issues(
        repo=args.repo,
        state=args.state,
        limit=args.limit,
        author=args.author,
        label=args.label,
        assignee=args.assignee,
    )
    print(json.dumps(result, indent=2 if args.pretty else None))
    sys.exit(0 if not result.get("error") else 1)


def cmd_get_issue(args: argparse.Namespace) -> None:
    """Command: get-issue"""
    result = get_issue(repo=args.repo, number=args.number)
    print(json.dumps(result, indent=2 if args.pretty else None))
    sys.exit(0 if not result.get("error") else 1)


def cmd_list_releases(args: argparse.Namespace) -> None:
    """Command: list-releases"""
    result = list_releases(
        repo=args.repo,
        limit=args.limit,
        exclude_drafts=args.exclude_drafts,
        exclude_prereleases=args.exclude_prereleases,
    )
    print(json.dumps(result, indent=2 if args.pretty else None))
    sys.exit(0 if not result.get("error") else 1)


def cmd_list_runs(args: argparse.Namespace) -> None:
    """Command: list-runs"""
    result = list_runs(
        repo=args.repo,
        limit=args.limit,
        status=args.status,
        branch=args.branch,
        workflow=args.workflow,
        event=args.event,
    )
    print(json.dumps(result, indent=2 if args.pretty else None))
    sys.exit(0 if not result.get("error") else 1)


def cmd_list_teams(args: argparse.Namespace) -> None:
    """Command: list-teams"""
    result = list_teams(org=args.org)
    print(json.dumps(result, indent=2 if args.pretty else None))
    sys.exit(0 if not result.get("error") else 1)


# =============================================================================
# Main
# =============================================================================


def main() -> None:
    """Main entry point for the GitHub client CLI."""
    parser = argparse.ArgumentParser(
        description="GitHub Client for LLM-Assisted Workflows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s auth-status
  %(prog)s list-repos --limit 50
  %(prog)s list-org-repos invia-flights
  %(prog)s list-team-repos invia-flights artificial-intelligence
  %(prog)s get-repo invia-flights/flight-recommender
  %(prog)s search-repos "machine learning" --owner invia-flights
  %(prog)s list-prs invia-flights/flight-recommender --state open
  %(prog)s list-runs invia-flights/flight-recommender --status failure
        """,
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # auth-status
    sub_auth = subparsers.add_parser(
        "auth-status", help="Check GitHub authentication status"
    )
    sub_auth.set_defaults(func=cmd_auth_status)

    # list-repos
    sub_list_repos = subparsers.add_parser(
        "list-repos", help="List user's accessible repositories"
    )
    sub_list_repos.add_argument(
        "--limit", "-L", type=int, default=DEFAULT_LIMIT, help="Max repos to return"
    )
    sub_list_repos.add_argument(
        "--type", choices=["all", "owner", "member", "forks", "source"], default="all"
    )
    sub_list_repos.add_argument(
        "--visibility", choices=["public", "private", "internal"]
    )
    sub_list_repos.add_argument("--language", help="Filter by language")
    sub_list_repos.set_defaults(func=cmd_list_repos)

    # list-org-repos
    sub_list_org = subparsers.add_parser(
        "list-org-repos", help="List repositories in an organization"
    )
    sub_list_org.add_argument("org", help="Organization name")
    sub_list_org.add_argument("--limit", "-L", type=int, default=DEFAULT_LIMIT)
    sub_list_org.add_argument("--visibility", choices=["public", "private", "internal"])
    sub_list_org.add_argument("--language", help="Filter by language")
    sub_list_org.set_defaults(func=cmd_list_org_repos)

    # list-team-repos
    sub_list_team = subparsers.add_parser(
        "list-team-repos", help="List repositories for a team"
    )
    sub_list_team.add_argument("org", help="Organization name")
    sub_list_team.add_argument("team", help="Team slug")
    sub_list_team.add_argument("--limit", "-L", type=int, default=DEFAULT_LIMIT)
    sub_list_team.set_defaults(func=cmd_list_team_repos)

    # get-repo
    sub_get_repo = subparsers.add_parser(
        "get-repo", help="Get detailed repository information"
    )
    sub_get_repo.add_argument("repo", help="Repository in owner/repo format")
    sub_get_repo.set_defaults(func=cmd_get_repo)

    # search-repos
    sub_search = subparsers.add_parser("search-repos", help="Search repositories")
    sub_search.add_argument("query", help="Search query")
    sub_search.add_argument("--owner", help="Filter by owner/organization")
    sub_search.add_argument("--language", help="Filter by language")
    sub_search.add_argument("--limit", "-L", type=int, default=DEFAULT_LIMIT)
    sub_search.add_argument("--visibility", choices=["public", "private", "internal"])
    sub_search.set_defaults(func=cmd_search_repos)

    # list-prs
    sub_list_prs = subparsers.add_parser("list-prs", help="List pull requests")
    sub_list_prs.add_argument("repo", help="Repository in owner/repo format")
    sub_list_prs.add_argument(
        "--state", "-s", choices=["open", "closed", "merged", "all"], default="open"
    )
    sub_list_prs.add_argument("--limit", "-L", type=int, default=DEFAULT_LIMIT)
    sub_list_prs.add_argument("--author", help="Filter by author")
    sub_list_prs.add_argument("--label", help="Filter by label")
    sub_list_prs.add_argument("--base", help="Filter by base branch")
    sub_list_prs.set_defaults(func=cmd_list_prs)

    # get-pr
    sub_get_pr = subparsers.add_parser("get-pr", help="Get detailed PR information")
    sub_get_pr.add_argument("repo", help="Repository in owner/repo format")
    sub_get_pr.add_argument("number", type=int, help="PR number")
    sub_get_pr.set_defaults(func=cmd_get_pr)

    # list-issues
    sub_list_issues = subparsers.add_parser("list-issues", help="List issues")
    sub_list_issues.add_argument("repo", help="Repository in owner/repo format")
    sub_list_issues.add_argument(
        "--state", "-s", choices=["open", "closed", "all"], default="open"
    )
    sub_list_issues.add_argument("--limit", "-L", type=int, default=DEFAULT_LIMIT)
    sub_list_issues.add_argument("--author", help="Filter by author")
    sub_list_issues.add_argument("--label", help="Filter by label")
    sub_list_issues.add_argument("--assignee", help="Filter by assignee")
    sub_list_issues.set_defaults(func=cmd_list_issues)

    # get-issue
    sub_get_issue = subparsers.add_parser(
        "get-issue", help="Get detailed issue information"
    )
    sub_get_issue.add_argument("repo", help="Repository in owner/repo format")
    sub_get_issue.add_argument("number", type=int, help="Issue number")
    sub_get_issue.set_defaults(func=cmd_get_issue)

    # list-releases
    sub_list_releases = subparsers.add_parser("list-releases", help="List releases")
    sub_list_releases.add_argument("repo", help="Repository in owner/repo format")
    sub_list_releases.add_argument("--limit", "-L", type=int, default=DEFAULT_LIMIT)
    sub_list_releases.add_argument("--exclude-drafts", action="store_true")
    sub_list_releases.add_argument("--exclude-prereleases", action="store_true")
    sub_list_releases.set_defaults(func=cmd_list_releases)

    # list-runs
    sub_list_runs = subparsers.add_parser("list-runs", help="List workflow runs")
    sub_list_runs.add_argument("repo", help="Repository in owner/repo format")
    sub_list_runs.add_argument("--limit", "-L", type=int, default=DEFAULT_LIMIT)
    sub_list_runs.add_argument(
        "--status", help="Filter by status (e.g., success, failure, in_progress)"
    )
    sub_list_runs.add_argument("--branch", help="Filter by branch")
    sub_list_runs.add_argument("--workflow", help="Filter by workflow name")
    sub_list_runs.add_argument(
        "--event", help="Filter by event (e.g., push, pull_request)"
    )
    sub_list_runs.set_defaults(func=cmd_list_runs)

    # list-teams
    sub_list_teams = subparsers.add_parser(
        "list-teams", help="List teams in an organization"
    )
    sub_list_teams.add_argument("org", help="Organization name")
    sub_list_teams.set_defaults(func=cmd_list_teams)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Pass pretty flag to subcommand
    if not hasattr(args, "pretty"):
        args.pretty = False

    args.func(args)


if __name__ == "__main__":
    main()
