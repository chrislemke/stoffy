#!/usr/bin/env python3
"""
Atlassian Client for opencode Custom Tools

Consolidated access to JIRA and Confluence via atlassian-python-api.
Credentials are loaded from .env file at project root.

JIRA: READ + limited WRITE (update description, add comment)
Confluence: READ-ONLY (search for context, never create/modify)

Usage:
    python atlassian_client.py <command> [args...]

Commands:
    # JIRA Read Operations
    jira-issue <key> [fields]           Get JIRA issue by key
    jira-search <jql> [max_results]     Search JIRA issues via JQL
    jira-comments <key>                 Get comments on a JIRA issue
    jira-epic-children <epic_key> [max] Get all issues under an epic
    jira-linked-issues <key>            Get linked issues for a ticket
    jira-gather-context <ticket_id>     Gather all context for a ticket
        [--include-confluence]          Include Confluence search results

    # JIRA Write Operations
    jira-update-description <key> --file <path>  Update/append to ticket description
    jira-add-comment <key> --content <text>      Add a comment to a ticket
    jira-add-comment <key> --file <path>         Add a comment from file

    # Confluence Read Operations (READ-ONLY)
    confluence-page <space> <title>     Get Confluence page by space and title
    confluence-page-id <page_id>        Get Confluence page by ID
    confluence-search <cql> [limit]     Search Confluence via CQL
    confluence-space <space_key> [limit] List pages in a Confluence space
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

# ============================================================================
# Configuration
# ============================================================================

# Ticket ID pattern - matches common JIRA prefixes
TICKET_PATTERN = re.compile(
    r"^(DS|FML|FLUG|FLIGHTS|FIOS|FPRO|BI|HD)-(\d+)$", re.IGNORECASE
)

# Map ticket prefixes to Confluence spaces
SPACE_MAPPING = {
    "FML": "FML",
    "FPRO": "FPRO",
    "DS": "DS",
    "FLUG": "FLUG",
    "FLIGHTS": "FLIGHTS",
    "FIOS": "FIOS",
    "BI": "BI",
    "HD": "HD",
}


# ============================================================================
# Environment and Credentials
# ============================================================================


def find_env_file() -> Path | None:
    """Find .env file by walking up directory tree."""
    current = Path(__file__).resolve().parent
    for _ in range(10):  # Max 10 levels up
        env_path = current / ".env"
        if env_path.exists():
            return env_path
        # Also check if we're in .opencode/tool, go to project root
        if (current / "opencode.jsonc").exists() or (current / ".opencode").exists():
            env_path = current / ".env"
            if env_path.exists():
                return env_path
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def load_env() -> dict[str, str]:
    """Load environment variables from .env file."""
    env_vars = {}
    env_file = find_env_file()

    if env_file and env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    # Remove quotes if present
                    value = value.strip().strip("'\"")
                    env_vars[key.strip()] = value

    # Environment variables take precedence
    for key in [
        "ATLASSIAN_URL",
        "ATLASSIAN_USERNAME",
        "ATLASSIAN_API_TOKEN",
        "ATLASSIAN_CLOUD",
    ]:
        if key in os.environ:
            env_vars[key] = os.environ[key]

    return env_vars


def get_jira_client():
    """Create and return JIRA client."""
    from atlassian import Jira

    env = load_env()
    url = env.get("ATLASSIAN_URL")
    username = env.get("ATLASSIAN_USERNAME")
    token = env.get("ATLASSIAN_API_TOKEN")
    is_cloud = env.get("ATLASSIAN_CLOUD", "true").lower() == "true"

    if not all([url, username, token]):
        raise ValueError(
            "Missing Atlassian credentials. Required: ATLASSIAN_URL, ATLASSIAN_USERNAME, ATLASSIAN_API_TOKEN"
        )

    return Jira(url=url, username=username, password=token, cloud=is_cloud)


def get_confluence_client():
    """Create and return Confluence client."""
    from atlassian import Confluence

    env = load_env()
    url = env.get("ATLASSIAN_URL")
    username = env.get("ATLASSIAN_USERNAME")
    token = env.get("ATLASSIAN_API_TOKEN")
    is_cloud = env.get("ATLASSIAN_CLOUD", "true").lower() == "true"

    if not all([url, username, token]):
        raise ValueError(
            "Missing Atlassian credentials. Required: ATLASSIAN_URL, ATLASSIAN_USERNAME, ATLASSIAN_API_TOKEN"
        )

    return Confluence(url=url, username=username, password=token, cloud=is_cloud)


# ============================================================================
# Formatting Helpers
# ============================================================================


def format_jira_issue(
    issue: dict[str, Any], include_description: bool = True
) -> dict[str, Any]:
    """Extract key fields from JIRA issue for readable output."""
    fields = issue.get("fields", {}) or {}

    # Handle assignee/reporter which might be None
    assignee = fields.get("assignee")
    reporter = fields.get("reporter")
    status = fields.get("status", {})
    priority = fields.get("priority", {})
    issuetype = fields.get("issuetype", {})
    project = fields.get("project", {})
    parent = fields.get("parent", {})  # Epic in JIRA Cloud

    result = {
        "key": issue.get("key"),
        "summary": fields.get("summary"),
        "status": status.get("name") if status else None,
        "status_category": status.get("statusCategory", {}).get("name")
        if status
        else None,
        "type": issuetype.get("name") if issuetype else None,
        "priority": priority.get("name") if priority else None,
        "assignee": assignee.get("displayName") if assignee else None,
        "assignee_email": assignee.get("emailAddress") if assignee else None,
        "reporter": reporter.get("displayName") if reporter else None,
        "labels": fields.get("labels", []),
        "components": [c.get("name") for c in fields.get("components", [])],
        "project_key": project.get("key") if project else None,
        "project_name": project.get("name") if project else None,
        "epic_key": parent.get("key") if parent else None,
        "epic_summary": parent.get("fields", {}).get("summary") if parent else None,
        "created": fields.get("created"),
        "updated": fields.get("updated"),
        "url": issue.get("self", "")
        .replace("/rest/api/2/issue/", "/browse/")
        .replace("/rest/api/3/issue/", "/browse/")
        .split("?")[0],
    }

    if include_description:
        result["description"] = fields.get("description")

    return result


def format_confluence_page(
    page: dict[str, Any], include_content: bool = True
) -> dict[str, Any]:
    """Extract key fields from Confluence page for readable output."""
    body = page.get("body", {})
    storage_body = body.get("storage", {}).get("value", "")
    view_body = body.get("view", {}).get("value", "")

    # Prefer view (rendered) over storage (raw)
    content = view_body or storage_body

    # Strip HTML tags for plain text (basic)
    plain_content = re.sub(r"<[^>]+>", "", content) if content else ""

    result = {
        "id": page.get("id"),
        "title": page.get("title"),
        "space": page.get("space", {}).get("key") if page.get("space") else None,
        "space_name": page.get("space", {}).get("name") if page.get("space") else None,
        "version": page.get("version", {}).get("number")
        if page.get("version")
        else None,
        "created": page.get("history", {}).get("createdDate")
        if page.get("history")
        else None,
        "updated": page.get("version", {}).get("when") if page.get("version") else None,
        "url": page.get("_links", {}).get("webui", ""),
    }

    if include_content:
        result["content"] = plain_content[:5000] if plain_content else None
        result["content_html"] = content[:10000] if content else None

    return result


def extract_ticket_prefix(ticket_id: str) -> str | None:
    """Extract the prefix from a ticket ID (e.g., FML from FML-247)."""
    match = TICKET_PATTERN.match(ticket_id.upper())
    if match:
        return match.group(1).upper()
    return None


# ============================================================================
# JIRA Read Operations
# ============================================================================


def jira_get_issue(ticket_id: str, fields: str | None = None) -> dict[str, Any]:
    """Get a JIRA issue by key."""
    jira = get_jira_client()

    try:
        issue = jira.issue(ticket_id, fields=fields)
        if not issue:
            return {"error": f"Issue {ticket_id} not found"}

        result = format_jira_issue(issue)
        result["url"] = f"https://invia.atlassian.net/browse/{ticket_id}"
        return result

    except Exception as e:
        return {"error": str(e), "ticket_id": ticket_id}


def jira_search(jql: str, max_results: int = 20) -> dict[str, Any]:
    """Search JIRA issues via JQL."""
    jira = get_jira_client()

    try:
        result = jira.jql(jql, limit=max_results)
        issues = [format_jira_issue(issue) for issue in result.get("issues", [])]
        return {
            "total": result.get("total", 0),
            "returned": len(issues),
            "issues": issues,
        }
    except Exception as e:
        return {"error": str(e)}


def jira_get_comments(ticket_id: str) -> dict[str, Any]:
    """Get comments on a JIRA issue."""
    jira = get_jira_client()

    try:
        comments = jira.issue_get_comments(ticket_id)
        formatted = []
        for comment in comments.get("comments", []):
            author = comment.get("author", {})
            formatted.append(
                {
                    "id": comment.get("id"),
                    "author": author.get("displayName") if author else None,
                    "created": comment.get("created"),
                    "updated": comment.get("updated"),
                    "body": comment.get("body"),
                }
            )

        return {
            "issue_key": ticket_id,
            "total": len(formatted),
            "comments": formatted,
        }
    except Exception as e:
        return {"error": str(e), "issue_key": ticket_id}


def jira_get_epic_children(epic_key: str, max_results: int = 50) -> dict[str, Any]:
    """Get all issues under an epic."""
    jira = get_jira_client()

    try:
        # JQL to find issues under epic
        jql = f'"Parent" = {epic_key} ORDER BY created DESC'
        result = jira.jql(jql, limit=max_results)

        issues = []
        for issue in result.get("issues", []):
            issues.append(format_jira_issue(issue, include_description=False))

        return {
            "epic_key": epic_key,
            "total": result.get("total", 0),
            "returned": len(issues),
            "issues": issues,
        }

    except Exception as e:
        return {"error": str(e), "epic_key": epic_key}


def jira_get_linked_issues(ticket_id: str) -> dict[str, Any]:
    """Get issues linked to a specific ticket."""
    jira = get_jira_client()

    try:
        issue = jira.issue(ticket_id, fields="issuelinks")
        if not issue:
            return {"error": f"Issue {ticket_id} not found", "ticket_id": ticket_id}

        fields = issue.get("fields", {}) or {}
        issue_links = fields.get("issuelinks", []) or []

        linked_issues = []
        for link in issue_links:
            link_type = link.get("type", {}).get("name", "Unknown")

            # Determine direction and get the linked issue
            if "outwardIssue" in link:
                direction = "outward"
                linked = link["outwardIssue"]
                link_description = link.get("type", {}).get("outward", link_type)
            elif "inwardIssue" in link:
                direction = "inward"
                linked = link["inwardIssue"]
                link_description = link.get("type", {}).get("inward", link_type)
            else:
                continue

            linked_issues.append(
                {
                    "key": linked.get("key"),
                    "summary": linked.get("fields", {}).get("summary"),
                    "status": linked.get("fields", {}).get("status", {}).get("name"),
                    "type": linked.get("fields", {}).get("issuetype", {}).get("name"),
                    "link_type": link_type,
                    "link_description": link_description,
                    "direction": direction,
                }
            )

        return {
            "ticket_id": ticket_id,
            "total": len(linked_issues),
            "linked_issues": linked_issues,
        }

    except Exception as e:
        return {"error": str(e), "ticket_id": ticket_id}


def jira_gather_context(
    ticket_id: str, include_confluence: bool = False
) -> dict[str, Any]:
    """
    Gather all relevant context for a ticket.

    Aggregates:
    - Ticket details
    - Epic information (if ticket has parent epic)
    - Linked issues
    - Sibling tickets under the same epic
    - Confluence pages mentioning the project (if include_confluence=True)
    """
    result = {
        "ticket_id": ticket_id,
        "ticket": None,
        "epic": None,
        "epic_children": [],
        "linked_issues": [],
        "confluence_pages": [],
        "errors": [],
    }

    # Validate ticket ID format
    prefix = extract_ticket_prefix(ticket_id)
    if not prefix:
        return {
            "error": f"Invalid ticket ID format: {ticket_id}",
            "ticket_id": ticket_id,
        }

    # Get ticket details
    ticket_result = jira_get_issue(ticket_id)
    if ticket_result.get("error"):
        return {
            "error": f"Failed to fetch ticket: {ticket_result.get('error')}",
            "ticket_id": ticket_id,
        }
    result["ticket"] = ticket_result

    # Get epic information if ticket has a parent epic
    epic_key = ticket_result.get("epic_key")
    if epic_key:
        # Get epic details
        epic_result = jira_get_issue(epic_key)
        if not epic_result.get("error"):
            result["epic"] = epic_result
        else:
            result["errors"].append(
                f"Failed to fetch epic {epic_key}: {epic_result.get('error')}"
            )

        # Get sibling tickets under the same epic
        children_result = jira_get_epic_children(epic_key)
        if not children_result.get("error"):
            # Filter out the current ticket from children
            result["epic_children"] = [
                child
                for child in children_result.get("issues", [])
                if child.get("key") != ticket_id
            ]
        else:
            result["errors"].append(
                f"Failed to fetch epic children: {children_result.get('error')}"
            )

    # Get linked issues
    linked_result = jira_get_linked_issues(ticket_id)
    if not linked_result.get("error"):
        result["linked_issues"] = linked_result.get("linked_issues", [])
    else:
        result["errors"].append(
            f"Failed to fetch linked issues: {linked_result.get('error')}"
        )

    # Search Confluence for related pages (limited to ticket's space)
    if include_confluence:
        space = SPACE_MAPPING.get(prefix, prefix)

        # Search for pages mentioning the ticket or epic
        search_terms = [ticket_id]
        if epic_key:
            search_terms.append(epic_key)

        # Also search for project-related terms from ticket summary
        summary = ticket_result.get("summary", "")
        if summary:
            # Extract key terms (words > 4 chars that aren't common)
            common_words = {
                "with",
                "from",
                "that",
                "this",
                "have",
                "will",
                "should",
                "could",
                "would",
                "about",
                "being",
                "their",
            }
            words = re.findall(r"\b[a-zA-Z]{5,}\b", summary)
            key_terms = [w for w in words[:3] if w.lower() not in common_words]
            search_terms.extend(key_terms)

        # Perform searches
        all_pages: dict[str, dict[str, Any]] = {}
        for term in search_terms:
            search_result = confluence_search(term, space=space, limit=5)
            if not search_result.get("error"):
                for page in search_result.get("results", []):
                    # Deduplicate by page ID
                    page_id = page.get("id")
                    if page_id and page_id not in all_pages:
                        all_pages[page_id] = page

        result["confluence_pages"] = list(all_pages.values())[:10]  # Limit to 10 pages

    return result


# ============================================================================
# JIRA Write Operations
# ============================================================================


def jira_update_description(ticket_id: str, content_file: str) -> dict[str, Any]:
    """
    Update JIRA ticket description by appending new content.

    Converts Markdown content to Atlassian Document Format (ADF) and appends
    it to the existing description with a horizontal rule separator.

    Uses JIRA Cloud v3 API directly for proper ADF support.

    Args:
        ticket_id: JIRA ticket ID (e.g., FML-247)
        content_file: Path to file containing markdown content to append

    Returns:
        Dict with ticket_id, message, url, or error
    """
    # Import markdown_to_adf (same directory)
    try:
        from markdown_to_adf import create_adf_separator, markdown_to_adf
    except ImportError as e:
        return {
            "error": f"Failed to import markdown_to_adf: {e}",
            "ticket_id": ticket_id,
        }

    # Read content from file
    content_path = Path(content_file)
    if not content_path.exists():
        return {"error": f"File not found: {content_file}", "ticket_id": ticket_id}

    try:
        new_content = content_path.read_text(encoding="utf-8")
    except Exception as e:
        return {"error": f"Failed to read file: {e}", "ticket_id": ticket_id}

    import requests

    env = load_env()
    base_url = env.get("ATLASSIAN_URL", "").rstrip("/")
    username = env.get("ATLASSIAN_USERNAME", "")
    token = env.get("ATLASSIAN_API_TOKEN", "")

    if not all([base_url, username, token]):
        return {"error": "Missing Atlassian credentials", "ticket_id": ticket_id}

    auth = (username, token)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    try:
        # Get current description using v3 API (returns ADF)
        get_url = f"{base_url}/rest/api/3/issue/{ticket_id}?fields=description"
        response = requests.get(get_url, auth=auth, headers=headers, timeout=30)

        if response.status_code == 404:
            return {"error": f"Issue {ticket_id} not found", "ticket_id": ticket_id}

        response.raise_for_status()
        issue_data = response.json()
        current_desc_adf = issue_data.get("fields", {}).get("description")

        # Convert new markdown content to ADF
        new_content_adf = markdown_to_adf(new_content)

        # Build combined ADF document
        combined_content: list[dict[str, Any]] = []

        # Add existing description content if present
        if current_desc_adf and isinstance(current_desc_adf, dict):
            existing_content = current_desc_adf.get("content", [])
            combined_content.extend(existing_content)

        # Add separator (horizontal rule)
        combined_content.append(create_adf_separator())

        # Add new content
        new_nodes = new_content_adf.get("content", [])
        combined_content.extend(new_nodes)

        # Build final ADF document
        updated_desc_adf = {
            "version": 1,
            "type": "doc",
            "content": combined_content,
        }

        # Update the issue using v3 API
        update_url = f"{base_url}/rest/api/3/issue/{ticket_id}"
        update_payload = {"fields": {"description": updated_desc_adf}}

        update_response = requests.put(
            update_url,
            auth=auth,
            headers=headers,
            json=update_payload,
            timeout=30,
        )

        if update_response.status_code == 204:
            return {
                "ticket_id": ticket_id,
                "message": "Description updated successfully with ADF formatting",
                "url": f"{base_url}/browse/{ticket_id}",
            }

        update_response.raise_for_status()

        return {
            "ticket_id": ticket_id,
            "message": "Description updated successfully",
            "url": f"{base_url}/browse/{ticket_id}",
        }

    except requests.exceptions.RequestException as e:
        return {"error": f"JIRA API error: {str(e)}", "ticket_id": ticket_id}
    except Exception as e:
        return {"error": str(e), "ticket_id": ticket_id}


def jira_add_comment(ticket_id: str, comment: str) -> dict[str, Any]:
    """
    Add a comment to a JIRA ticket.

    Args:
        ticket_id: JIRA ticket ID (e.g., FML-247)
        comment: Comment text (supports basic wiki markup)

    Returns:
        Dict with ticket_id, comment_id, message, or error
    """
    jira = get_jira_client()

    try:
        result = jira.issue_add_comment(ticket_id, comment)
        return {
            "ticket_id": ticket_id,
            "comment_id": result.get("id") if isinstance(result, dict) else None,
            "message": "Comment added successfully",
        }
    except Exception as e:
        return {"error": str(e), "ticket_id": ticket_id}


# ============================================================================
# Confluence Read Operations (READ-ONLY)
# ============================================================================


def confluence_get_page(space: str, title: str) -> dict[str, Any]:
    """Get Confluence page by space and title."""
    confluence = get_confluence_client()

    try:
        page = confluence.get_page_by_title(
            space, title, expand="body.storage,body.view,version,history,space"
        )
        if not page:
            return {"error": f"Page not found: '{title}' in space '{space}'"}

        return format_confluence_page(page)
    except Exception as e:
        return {"error": str(e)}


def confluence_get_page_by_id(page_id: str) -> dict[str, Any]:
    """Get Confluence page by ID."""
    confluence = get_confluence_client()

    try:
        page = confluence.get_page_by_id(
            page_id, expand="body.storage,body.view,version,history,space"
        )
        return format_confluence_page(page)
    except Exception as e:
        return {"error": str(e), "page_id": page_id}


def confluence_search(
    query: str, space: str | None = None, limit: int = 20
) -> dict[str, Any]:
    """Search Confluence via CQL.

    The query can be either:
    1. A simple search term (e.g., "flight recommender") - will be wrapped in text ~ "..."
    2. A full CQL query (e.g., "type=page AND title ~ flight") - used as-is

    Detection: If query contains CQL operators (~, =, AND, OR, IN), treat as full CQL.
    """
    confluence = get_confluence_client()

    try:
        # Detect if this is a full CQL query or a simple search term
        cql_operators = [
            " ~ ",
            " = ",
            " AND ",
            " OR ",
            " IN ",
            " NOT ",
            "type=",
            "space=",
            "title~",
            "text~",
        ]
        is_full_cql = any(op.lower() in query.lower() for op in cql_operators)

        if is_full_cql:
            # Use query as-is (it's already a CQL query)
            cql = query
            # Optionally add space filter if not already in query
            if space and "space" not in query.lower():
                cql = f'{cql} AND space = "{space}"'
        else:
            # Build CQL query from simple search term
            cql_parts = [f'text ~ "{query}"', "type = page"]
            if space:
                cql_parts.append(f'space = "{space}"')
            cql = " AND ".join(cql_parts)

        result = confluence.cql(cql, limit=limit, expand="space,version")
        pages = []
        for item in result.get("results", []):
            content = item.get("content", {})
            pages.append(
                {
                    "id": content.get("id") or item.get("id"),
                    "title": content.get("title") or item.get("title"),
                    "type": content.get("type") or item.get("type"),
                    "space": content.get("space", {}).get("key")
                    if content.get("space")
                    else None,
                    "url": content.get("_links", {}).get("webui", "")
                    or item.get("_links", {}).get("webui", ""),
                    "excerpt": item.get("excerpt", "")[:500]
                    if item.get("excerpt")
                    else None,
                }
            )

        return {
            "query": query,
            "cql_executed": cql,  # Show the actual CQL that was executed
            "space": space,
            "total": result.get("totalSize", len(pages)),
            "returned": len(pages),
            "results": pages,
        }
    except Exception as e:
        # Use locals() to safely check if cql was defined before the exception
        cql_value = locals().get("cql")
        return {
            "error": str(e),
            "query": query,
            "cql_executed": cql_value,
        }


def confluence_list_space(space_key: str, limit: int = 50) -> dict[str, Any]:
    """List pages in a Confluence space."""
    confluence = get_confluence_client()

    try:
        pages = confluence.get_all_pages_from_space(
            space_key, limit=limit, expand="version"
        )
        formatted = []
        for page in pages:
            formatted.append(
                {
                    "id": page.get("id"),
                    "title": page.get("title"),
                    "type": page.get("type"),
                    "version": page.get("version", {}).get("number")
                    if page.get("version")
                    else None,
                    "url": page.get("_links", {}).get("webui", ""),
                }
            )

        return {
            "space": space_key,
            "total": len(formatted),
            "pages": formatted,
        }
    except Exception as e:
        return {"error": str(e), "space": space_key}


# ============================================================================
# CLI Commands
# ============================================================================


def cmd_jira_issue(args: list[str]) -> None:
    """Command: jira-issue <key> [fields]"""
    if not args:
        print(
            json.dumps({"error": "Missing issue key. Usage: jira-issue <key> [fields]"})
        )
        sys.exit(1)

    issue_key = args[0]
    fields = args[1] if len(args) > 1 else None

    result = jira_get_issue(issue_key, fields=fields)
    print(json.dumps(result, indent=2, default=str))
    sys.exit(1 if result.get("error") else 0)


def cmd_jira_search(args: list[str]) -> None:
    """Command: jira-search <jql> [max_results]"""
    if not args:
        print(
            json.dumps(
                {"error": "Missing JQL query. Usage: jira-search <jql> [max_results]"}
            )
        )
        sys.exit(1)

    jql = args[0]
    max_results = int(args[1]) if len(args) > 1 else 20

    result = jira_search(jql, max_results=max_results)
    print(json.dumps(result, indent=2, default=str))
    sys.exit(1 if result.get("error") else 0)


def cmd_jira_comments(args: list[str]) -> None:
    """Command: jira-comments <key>"""
    if not args:
        print(json.dumps({"error": "Missing issue key. Usage: jira-comments <key>"}))
        sys.exit(1)

    result = jira_get_comments(args[0])
    print(json.dumps(result, indent=2, default=str))
    sys.exit(1 if result.get("error") else 0)


def cmd_jira_epic_children(args: list[str]) -> None:
    """Command: jira-epic-children <epic_key> [max_results]"""
    if not args:
        print(
            json.dumps(
                {
                    "error": "Missing epic key. Usage: jira-epic-children <epic_key> [max]"
                }
            )
        )
        sys.exit(1)

    epic_key = args[0]
    max_results = int(args[1]) if len(args) > 1 else 50

    result = jira_get_epic_children(epic_key, max_results=max_results)
    print(json.dumps(result, indent=2, default=str))
    sys.exit(1 if result.get("error") else 0)


def cmd_jira_linked_issues(args: list[str]) -> None:
    """Command: jira-linked-issues <key>"""
    if not args:
        print(
            json.dumps({"error": "Missing issue key. Usage: jira-linked-issues <key>"})
        )
        sys.exit(1)

    result = jira_get_linked_issues(args[0])
    print(json.dumps(result, indent=2, default=str))
    sys.exit(1 if result.get("error") else 0)


def cmd_jira_gather_context(args: list[str]) -> None:
    """Command: jira-gather-context <ticket_id> [--include-confluence]"""
    parser = argparse.ArgumentParser(prog="jira-gather-context")
    parser.add_argument("ticket_id", help="JIRA ticket ID")
    parser.add_argument(
        "--include-confluence",
        action="store_true",
        help="Include Confluence search results",
    )

    parsed = parser.parse_args(args)
    result = jira_gather_context(
        parsed.ticket_id, include_confluence=parsed.include_confluence
    )
    print(json.dumps(result, indent=2, default=str))
    sys.exit(1 if result.get("error") else 0)


def cmd_jira_update_description(args: list[str]) -> None:
    """Command: jira-update-description <key> --file <path>"""
    parser = argparse.ArgumentParser(prog="jira-update-description")
    parser.add_argument("ticket_id", help="JIRA ticket ID")
    parser.add_argument("--file", required=True, help="Path to file containing content")

    parsed = parser.parse_args(args)
    result = jira_update_description(parsed.ticket_id, parsed.file)
    print(json.dumps(result, indent=2, default=str))
    sys.exit(1 if result.get("error") else 0)


def cmd_jira_add_comment(args: list[str]) -> None:
    """Command: jira-add-comment <key> --content <text> OR --file <path>"""
    parser = argparse.ArgumentParser(prog="jira-add-comment")
    parser.add_argument("ticket_id", help="JIRA ticket ID")
    content_group = parser.add_mutually_exclusive_group(required=True)
    content_group.add_argument("--content", help="Comment text")
    content_group.add_argument("--file", help="Path to file containing comment")

    parsed = parser.parse_args(args)

    if parsed.file:
        try:
            comment = Path(parsed.file).read_text(encoding="utf-8")
        except FileNotFoundError:
            print(
                json.dumps(
                    {
                        "error": f"File not found: {parsed.file}",
                        "ticket_id": parsed.ticket_id,
                    }
                )
            )
            sys.exit(1)
        except Exception as e:
            print(
                json.dumps(
                    {
                        "error": f"Failed to read file: {e}",
                        "ticket_id": parsed.ticket_id,
                    }
                )
            )
            sys.exit(1)
    else:
        comment = parsed.content

    result = jira_add_comment(parsed.ticket_id, comment)
    print(json.dumps(result, indent=2, default=str))
    sys.exit(1 if result.get("error") else 0)


def cmd_confluence_page(args: list[str]) -> None:
    """Command: confluence-page <space> <title>"""
    if len(args) < 2:
        print(
            json.dumps(
                {"error": "Missing arguments. Usage: confluence-page <space> <title>"}
            )
        )
        sys.exit(1)

    result = confluence_get_page(args[0], args[1])
    print(json.dumps(result, indent=2, default=str))
    sys.exit(1 if result.get("error") else 0)


def cmd_confluence_page_id(args: list[str]) -> None:
    """Command: confluence-page-id <page_id>"""
    if not args:
        print(
            json.dumps(
                {"error": "Missing page ID. Usage: confluence-page-id <page_id>"}
            )
        )
        sys.exit(1)

    result = confluence_get_page_by_id(args[0])
    print(json.dumps(result, indent=2, default=str))
    sys.exit(1 if result.get("error") else 0)


def cmd_confluence_search(args: list[str]) -> None:
    """Command: confluence-search <query> [--space SPACE] [--limit N]"""
    parser = argparse.ArgumentParser(prog="confluence-search")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--space", help="Limit search to space")
    parser.add_argument("--limit", type=int, default=20, help="Max results")

    # Handle positional limit for backward compatibility
    if len(args) >= 2 and args[1].isdigit():
        query = args[0]
        limit = int(args[1])
        result = confluence_search(query, limit=limit)
    else:
        parsed = parser.parse_args(args)
        result = confluence_search(parsed.query, space=parsed.space, limit=parsed.limit)

    print(json.dumps(result, indent=2, default=str))
    sys.exit(1 if result.get("error") else 0)


def cmd_confluence_space(args: list[str]) -> None:
    """Command: confluence-space <space_key> [limit]"""
    if not args:
        print(
            json.dumps(
                {
                    "error": "Missing space key. Usage: confluence-space <space_key> [limit]"
                }
            )
        )
        sys.exit(1)

    space_key = args[0]
    limit = int(args[1]) if len(args) > 1 else 50

    result = confluence_list_space(space_key, limit=limit)
    print(json.dumps(result, indent=2, default=str))
    sys.exit(1 if result.get("error") else 0)


# ============================================================================
# Main
# ============================================================================

COMMANDS = {
    # JIRA Read
    "jira-issue": cmd_jira_issue,
    "jira-search": cmd_jira_search,
    "jira-comments": cmd_jira_comments,
    "jira-epic-children": cmd_jira_epic_children,
    "jira-linked-issues": cmd_jira_linked_issues,
    "jira-gather-context": cmd_jira_gather_context,
    # JIRA Write
    "jira-update-description": cmd_jira_update_description,
    "jira-add-comment": cmd_jira_add_comment,
    # Confluence Read
    "confluence-page": cmd_confluence_page,
    "confluence-page-id": cmd_confluence_page_id,
    "confluence-search": cmd_confluence_search,
    "confluence-space": cmd_confluence_space,
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
