#!/usr/bin/env python3
"""
Information Ingestion Script

Extracts entities and actionable information from text input (files, folders, URLs, or direct text)
and outputs a structured JSON plan for repository updates.

This script handles ALL deterministic extraction:
- Entity detection via regex and fuzzy matching
- Content type classification
- File operation planning
- Template-based file generation
- Web content fetching (generic websites, Confluence, JIRA)

The LLM/Agent handles ONLY:
- Semantic disambiguation
- Complex entity resolution

Usage:
    python scripts/ingest.py --file path/to/file.txt
    python scripts/ingest.py --folder path/to/folder/ [--recursive]
    python scripts/ingest.py --text "content..."
    python scripts/ingest.py --url "https://example.com"
    python scripts/ingest.py --url "fluege.de"
    python scripts/ingest.py --url "https://invia.atlassian.net/wiki/spaces/..."
    python scripts/ingest.py --url "https://invia.atlassian.net/jira/browse/FML-247"
    echo "content" | python scripts/ingest.py --stdin

Options:
    --json          Output JSON (for command parsing)
    --pretty        Pretty-print JSON
    --date DATE     Override auto-detected date (YYYY-MM-DD)
    --plan-only     Output plan without executing file operations
    --verbose       Show detailed processing info
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, NamedTuple
from urllib.parse import urlparse

# ============================================================================
# Configuration
# ============================================================================

REPO_ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = REPO_ROOT / "templates"
PEOPLE_DIR = REPO_ROOT / "communication" / "people"
TICKETS_DIR = REPO_ROOT / "tickets"
PROJECTS_DIR = REPO_ROOT / "project_management"
IDEAS_DIR = REPO_ROOT / "idea_development"
MEETINGS_DIR = REPO_ROOT / "communication" / "meetings"
DATA_DIR = REPO_ROOT / ".opencode" / "data"
# NOTE: Calendar events are now created by the LLM agent using calendar_create tool

# File extensions to process
TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".html",
    ".htm",
    ".eml",
    ".msg",
    ".json",
    ".yaml",
    ".yml",
    ".xml",
    ".csv",
    ".log",
    ".rst",
}

# Maximum file size to process (100KB)
MAX_FILE_SIZE = 100 * 1024

# Ticket ID patterns
TICKET_PATTERNS = [
    r"\b(DS-\d{3,5})\b",
    r"\b(FML-\d{2,4})\b",
    r"\b(FLUG-\d{4,6})\b",
    r"\b(FLIGHTS-\d{3,5})\b",
    r"\b(FIOS-\d{2,4})\b",
    r"\b(FPRO-\d{2,4})\b",
    r"\b(BI-\d{3,5})\b",
    r"\b(HD-\d{4,6})\b",
]

# Date patterns
DATE_PATTERNS = [
    # ISO format: 2025-12-10
    (r"\b(\d{4}-\d{2}-\d{2})\b", "%Y-%m-%d"),
    # German format: 10.12.2025
    (r"\b(\d{1,2}\.\d{1,2}\.\d{4})\b", "%d.%m.%Y"),
    # US format: 12/10/2025
    (r"\b(\d{1,2}/\d{1,2}/\d{4})\b", "%m/%d/%Y"),
    # Written: December 10, 2025
    (
        r"\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})\b",
        "%B %d, %Y",
    ),
]

# Content type keywords
CONTENT_TYPE_KEYWORDS = {
    "meeting": [
        "meeting",
        "call",
        "sync",
        "standup",
        "retro",
        "1:1",
        "one-on-one",
        "agenda",
        "minutes",
    ],
    "email": ["from:", "to:", "subject:", "re:", "fwd:", "sent:"],
    "ticket": [
        "acceptance criteria",
        "story points",
        "sprint",
        "jira",
        "issue",
        "bug",
        "feature request",
    ],
    "idea": [
        "idea",
        "concept",
        "poc",
        "proof of concept",
        "what if",
        "could we",
        "brainstorm",
        "proposal",
    ],
    "status_update": [
        "this week",
        "last week",
        "next week",
        "progress",
        "update",
        "done",
        "planned",
        "blocked",
    ],
    "notes": ["notes", "summary", "takeaways", "key points"],
}

# Action item patterns
ACTION_PATTERNS = [
    r"^\s*-\s*\[\s*\]\s*(.+)$",  # - [ ] task
    r"^\s*\*\s*\[\s*\]\s*(.+)$",  # * [ ] task
    r"(?:TODO|Action|ACTION|Task|TASK):\s*(.+?)(?:\n|$)",  # TODO: task
    r"@(\w+)\s+(?:to|should|will|must|needs? to)\s+(.+?)(?:\n|$)",  # @person to do something
]

# Decision patterns
DECISION_PATTERNS = [
    r"(?:decided|agreed|approved|confirmed|will)\s+(?:to\s+)?(.+?)(?:\.|$)",
    r"(?:Decision|DECISION):\s*(.+?)(?:\n|$)",
]

# Risk patterns
RISK_PATTERNS = [
    r"(?:risk|Risk|RISK|blocker|Blocker|BLOCKER|issue|Issue|ISSUE|concern|Concern|problem|Problem):\s*(.+?)(?:\n|$)",
    r"(?:⚠️|🚨|❗)\s*(.+?)(?:\n|$)",
]

# URL patterns for Atlassian detection
CONFLUENCE_URL_PATTERN = re.compile(
    r"(?:https?://)?(?:[\w-]+\.)?atlassian\.net/wiki(?:/spaces/([A-Z0-9]+))?(?:/pages/(\d+))?",
    re.IGNORECASE,
)
JIRA_URL_PATTERN = re.compile(
    r"(?:https?://)?(?:[\w-]+\.)?atlassian\.net/(?:jira/)?(?:browse/|software/projects/[^/]+/boards/\d+\?selectedIssue=)?([A-Z]+-\d+)",
    re.IGNORECASE,
)

# Atlassian client script path (located in scripts/ folder alongside this file)
ATLASSIAN_CLIENT = Path(__file__).parent / "atlassian_client.py"


# ============================================================================
# Data Classes
# ============================================================================


class ExtractedEntity(NamedTuple):
    """Represents an extracted entity."""

    type: str
    value: str
    context: str
    exists: bool
    slug: str | None = None
    confidence: float = 1.0


class FileOperation(NamedTuple):
    """Represents a file operation to perform."""

    action: str  # "create" or "update"
    path: str
    template: str | None
    data: dict[str, Any]
    append_content: str | None = None
    section: str | None = None


# ============================================================================
# Known Entities Management
# ============================================================================


def load_known_entities() -> dict[str, Any]:
    """Load known entities from JSON file or generate from AGENTS.md."""
    entities_file = DATA_DIR / "known_entities.json"
    agents_file = REPO_ROOT / "AGENTS.md"

    # Check if we need to regenerate
    if entities_file.exists():
        entities_mtime = entities_file.stat().st_mtime
        agents_mtime = agents_file.stat().st_mtime if agents_file.exists() else 0

        if entities_mtime >= agents_mtime:
            with open(entities_file) as f:
                return json.load(f)

    # Generate from AGENTS.md and existing folders
    entities = generate_known_entities()

    # Save for future use
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(entities_file, "w") as f:
        json.dump(entities, f, indent=2, ensure_ascii=False)

    return entities


def generate_known_entities() -> dict[str, Any]:
    """Generate known entities from repository structure."""
    entities: dict[str, Any] = {
        "people": {},
        "projects": {},
        "ideas": {},
        "ticket_prefixes": ["DS", "FML", "FLUG", "FLIGHTS", "FIOS", "FPRO", "BI", "HD"],
        "generated_at": datetime.now().isoformat(),
    }

    # Scan people folders
    if PEOPLE_DIR.exists():
        for person_dir in PEOPLE_DIR.iterdir():
            if person_dir.is_dir() and not person_dir.name.startswith("."):
                slug = person_dir.name
                profile_file = person_dir / "profile.md"

                # Try to extract full name from profile
                full_name = slug.replace("_", " ").title()
                if profile_file.exists():
                    content = profile_file.read_text()
                    # Look for name in frontmatter or title
                    name_match = re.search(r"name:\s*(.+)", content)
                    if name_match:
                        full_name = name_match.group(1).strip()
                    else:
                        title_match = re.search(r"#\s*Person Profile:\s*(.+)", content)
                        if title_match:
                            full_name = title_match.group(1).strip()

                # Generate aliases
                name_parts = full_name.split()
                aliases = [full_name, slug]
                if len(name_parts) >= 2:
                    aliases.extend(
                        [
                            name_parts[0],  # First name
                            name_parts[-1],  # Last name
                            f"{name_parts[0][0]}. {name_parts[-1]}",  # F. Lastname
                        ]
                    )

                entities["people"][slug] = {
                    "full_name": full_name,
                    "aliases": list(set(aliases)),
                    "folder": str(person_dir.relative_to(REPO_ROOT)),
                }

    # Scan project folders
    if PROJECTS_DIR.exists():
        for project_dir in PROJECTS_DIR.iterdir():
            if (
                project_dir.is_dir()
                and not project_dir.name.startswith(".")
                and project_dir.name != "data_resources"
            ):
                slug = project_dir.name
                name = slug.replace("-", " ").replace("_", " ").title()

                # Check for project.md or any md file for name
                for md_file in project_dir.glob("*.md"):
                    if md_file.name != "AGENTS.md":
                        content = md_file.read_text()
                        name_match = re.search(r"#\s*(.+?)(?:\n|$)", content)
                        if name_match:
                            name = name_match.group(1).strip()
                            break

                entities["projects"][slug] = {
                    "name": name,
                    "aliases": [
                        name,
                        slug,
                        slug.replace("-", " "),
                        slug.replace("_", " "),
                    ],
                    "folder": str(project_dir.relative_to(REPO_ROOT)),
                }

    # Scan idea folders
    if IDEAS_DIR.exists():
        for idea_dir in IDEAS_DIR.iterdir():
            if idea_dir.is_dir() and not idea_dir.name.startswith("."):
                slug = idea_dir.name
                name = slug.replace("-", " ").replace("_", " ").title()

                entities["ideas"][slug] = {
                    "name": name,
                    "aliases": [name, slug],
                    "folder": str(idea_dir.relative_to(REPO_ROOT)),
                }

    return entities


# ============================================================================
# URL Type Detection and Fetching
# ============================================================================


class URLType:
    """Enum-like class for URL types."""

    GENERIC = "generic"
    CONFLUENCE = "confluence"
    JIRA = "jira"


def normalize_url(url: str) -> str:
    """
    Normalize a URL by adding https:// if no scheme is provided.

    Args:
        url: URL string (may or may not have scheme)

    Returns:
        Normalized URL with https:// scheme
    """
    url = url.strip()
    if not url:
        return url

    # Check if URL already has a scheme
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    return url


def detect_url_type(url: str) -> tuple[str, dict[str, Any]]:
    """
    Detect the type of URL and extract relevant information.

    Args:
        url: The URL to analyze

    Returns:
        Tuple of (url_type, extracted_info)
        - url_type: One of URLType constants
        - extracted_info: Dict with type-specific info (e.g., ticket_id, page_id, space)
    """
    normalized = normalize_url(url)

    # Check for JIRA URL first (more specific pattern)
    jira_match = JIRA_URL_PATTERN.search(normalized)
    if jira_match:
        ticket_id = jira_match.group(1).upper()
        return URLType.JIRA, {"ticket_id": ticket_id, "url": normalized}

    # Check for Confluence URL
    confluence_match = CONFLUENCE_URL_PATTERN.search(normalized)
    if confluence_match:
        space = confluence_match.group(1) if confluence_match.group(1) else None
        page_id = confluence_match.group(2) if confluence_match.group(2) else None

        # Try to extract page ID from different URL formats
        # Format: /wiki/spaces/SPACE/pages/PAGE_ID/Title
        page_id_match = re.search(r"/pages/(\d+)", normalized)
        if page_id_match:
            page_id = page_id_match.group(1)

        return URLType.CONFLUENCE, {
            "space": space,
            "page_id": page_id,
            "url": normalized,
        }

    # Check if URL contains atlassian.net/wiki or atlassian.net/jira even if patterns didn't match
    if "atlassian.net/wiki" in normalized.lower():
        # Extract what we can from the URL
        page_id_match = re.search(r"/pages/(\d+)", normalized)
        space_match = re.search(r"/spaces/([A-Z0-9]+)", normalized, re.IGNORECASE)
        return URLType.CONFLUENCE, {
            "space": space_match.group(1) if space_match else None,
            "page_id": page_id_match.group(1) if page_id_match else None,
            "url": normalized,
        }

    if "atlassian.net" in normalized.lower() and (
        "/browse/" in normalized or "/jira/" in normalized
    ):
        # Try harder to extract ticket ID
        ticket_match = re.search(r"([A-Z]+-\d+)", normalized, re.IGNORECASE)
        if ticket_match:
            return URLType.JIRA, {
                "ticket_id": ticket_match.group(1).upper(),
                "url": normalized,
            }

    # Generic web URL
    return URLType.GENERIC, {"url": normalized}


def fetch_confluence_content(
    page_id: str | None = None,
    space: str | None = None,
    verbose: bool = False,
) -> tuple[str, dict[str, Any]]:
    """
    Fetch content from Confluence using the atlassian_client.py script.

    Args:
        page_id: Confluence page ID (numeric)
        space: Confluence space key (optional, used for context)
        verbose: Print verbose output

    Returns:
        Tuple of (content_text, metadata)
    """
    if not ATLASSIAN_CLIENT.exists():
        raise FileNotFoundError(
            f"Atlassian client script not found at {ATLASSIAN_CLIENT}"
        )

    if not page_id:
        raise ValueError("page_id is required to fetch Confluence content")

    try:
        if verbose:
            print(f"Fetching Confluence page ID: {page_id}", file=sys.stderr)

        # Use confluence-page-id command
        result = subprocess.run(
            ["python3", str(ATLASSIAN_CLIENT), "confluence-page-id", page_id],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            raise RuntimeError(f"Failed to fetch Confluence page: {error_msg}")

        # Parse JSON response
        response = json.loads(result.stdout)

        if response.get("error"):
            raise RuntimeError(f"Confluence API error: {response['error']}")

        # Extract text content
        content = response.get("content", "") or ""
        title = response.get("title", "")

        # Build text representation
        text_parts = []
        if title:
            text_parts.append(f"# {title}")
            text_parts.append("")
        if content:
            text_parts.append(content)

        metadata = {
            "source": "confluence",
            "page_id": page_id,
            "title": title,
            "space": response.get("space"),
            "url": response.get("url", ""),
            "version": response.get("version"),
        }

        return "\n".join(text_parts), metadata

    except subprocess.TimeoutExpired:
        raise RuntimeError("Confluence request timed out after 60 seconds")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse Confluence response: {e}")


def fetch_jira_content(
    ticket_id: str,
    verbose: bool = False,
) -> tuple[str, dict[str, Any]]:
    """
    Fetch content from JIRA using the atlassian_client.py script.

    Args:
        ticket_id: JIRA ticket ID (e.g., FML-247)
        verbose: Print verbose output

    Returns:
        Tuple of (content_text, metadata)
    """
    if not ATLASSIAN_CLIENT.exists():
        raise FileNotFoundError(
            f"Atlassian client script not found at {ATLASSIAN_CLIENT}"
        )

    try:
        if verbose:
            print(f"Fetching JIRA ticket: {ticket_id}", file=sys.stderr)

        # Use jira-issue command
        result = subprocess.run(
            ["python3", str(ATLASSIAN_CLIENT), "jira-issue", ticket_id],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            raise RuntimeError(f"Failed to fetch JIRA ticket: {error_msg}")

        # Parse JSON response
        response = json.loads(result.stdout)

        if response.get("error"):
            raise RuntimeError(f"JIRA API error: {response['error']}")

        # Build text representation
        text_parts = []
        text_parts.append(
            f"# {response.get('key', ticket_id)}: {response.get('summary', '')}"
        )
        text_parts.append("")
        text_parts.append(f"**Status:** {response.get('status', 'Unknown')}")
        text_parts.append(f"**Type:** {response.get('type', 'Unknown')}")
        text_parts.append(f"**Priority:** {response.get('priority', 'Unknown')}")
        if response.get("assignee"):
            text_parts.append(f"**Assignee:** {response.get('assignee')}")
        if response.get("reporter"):
            text_parts.append(f"**Reporter:** {response.get('reporter')}")
        if response.get("labels"):
            text_parts.append(f"**Labels:** {', '.join(response.get('labels', []))}")
        text_parts.append("")

        description = response.get("description", "")
        if description:
            # Handle ADF format (dict) vs plain text
            if isinstance(description, dict):
                # Extract text from ADF - simplified extraction
                desc_text = extract_text_from_adf(description)
                text_parts.append("## Description")
                text_parts.append(desc_text)
            else:
                text_parts.append("## Description")
                text_parts.append(str(description))

        metadata = {
            "source": "jira",
            "ticket_id": ticket_id,
            "summary": response.get("summary"),
            "status": response.get("status"),
            "type": response.get("type"),
            "assignee": response.get("assignee"),
            "url": response.get("url", ""),
        }

        return "\n".join(text_parts), metadata

    except subprocess.TimeoutExpired:
        raise RuntimeError("JIRA request timed out after 60 seconds")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse JIRA response: {e}")


def extract_text_from_adf(adf: dict[str, Any]) -> str:
    """
    Extract plain text from Atlassian Document Format (ADF).

    Args:
        adf: ADF document as dict

    Returns:
        Plain text content
    """
    if not isinstance(adf, dict):
        return str(adf)

    text_parts: list[str] = []

    def extract_node(node: dict[str, Any] | list[Any] | str) -> None:
        if isinstance(node, str):
            text_parts.append(node)
        elif isinstance(node, list):
            for item in node:
                extract_node(item)
        elif isinstance(node, dict):
            # Handle text nodes
            if node.get("type") == "text":
                text_parts.append(node.get("text", ""))
            # Handle paragraph breaks
            elif node.get("type") == "paragraph":
                if node.get("content"):
                    extract_node(node["content"])
                text_parts.append("\n")
            # Handle headings
            elif node.get("type") == "heading":
                level = node.get("attrs", {}).get("level", 1)
                text_parts.append("\n" + "#" * level + " ")
                if node.get("content"):
                    extract_node(node["content"])
                text_parts.append("\n")
            # Handle bullet lists
            elif node.get("type") in ("bulletList", "orderedList"):
                if node.get("content"):
                    for item in node["content"]:
                        text_parts.append("- ")
                        extract_node(item)
            # Handle list items
            elif node.get("type") == "listItem":
                if node.get("content"):
                    extract_node(node["content"])
            # Handle code blocks
            elif node.get("type") == "codeBlock":
                text_parts.append("\n```\n")
                if node.get("content"):
                    extract_node(node["content"])
                text_parts.append("\n```\n")
            # Recurse into content
            elif node.get("content"):
                extract_node(node["content"])

    extract_node(adf)
    return "".join(text_parts).strip()


def fetch_web_content(
    url: str,
    verbose: bool = False,
) -> tuple[str, dict[str, Any]]:
    """
    Fetch content from a generic web URL using BeautifulSoup.

    Args:
        url: The URL to fetch
        verbose: Print verbose output

    Returns:
        Tuple of (content_text, metadata)
    """
    try:
        from bs4 import BeautifulSoup
        import requests
    except ImportError as e:
        raise RuntimeError(
            f"Required packages not installed. Run: pip install beautifulsoup4 requests. Error: {e}"
        )

    try:
        if verbose:
            print(f"Fetching web content from: {url}", file=sys.stderr)

        # Make request with reasonable timeout and user agent
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.content, "html.parser")

        # Remove unwanted elements
        for element in soup(
            [
                "script",
                "style",
                "nav",
                "footer",
                "header",
                "aside",
                "noscript",
                "iframe",
            ]
        ):
            element.decompose()

        # Extract title
        title = ""
        if soup.title:
            title = soup.title.get_text(strip=True)
        elif soup.find("h1"):
            title = soup.find("h1").get_text(strip=True)

        # Extract meta description
        meta_desc = ""
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag:
            meta_desc = meta_tag.get("content", "")

        # Extract main content
        # Try to find main content area first
        main_content = None
        for selector in [
            "main",
            "article",
            '[role="main"]',
            ".content",
            "#content",
            ".post",
            ".entry",
        ]:
            main_content = soup.select_one(selector)
            if main_content:
                break

        if not main_content:
            main_content = soup.body if soup.body else soup

        # Extract text from content
        if main_content:
            # Get text with newlines preserved for readability
            text = main_content.get_text(separator="\n", strip=True)
            # Clean up excessive whitespace
            text = re.sub(r"\n{3,}", "\n\n", text)
            text = re.sub(r"[ \t]+", " ", text)
        else:
            text = soup.get_text(separator="\n", strip=True)

        # Build output
        text_parts = []
        if title:
            text_parts.append(f"# {title}")
            text_parts.append("")
        if meta_desc:
            text_parts.append(f"> {meta_desc}")
            text_parts.append("")
        text_parts.append(text)

        # Parse URL for metadata
        parsed = urlparse(url)

        metadata = {
            "source": "web",
            "url": url,
            "domain": parsed.netloc,
            "title": title,
            "description": meta_desc,
            "content_length": len(text),
        }

        return "\n".join(text_parts), metadata

    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch URL: {e}")


def fetch_url_content(
    url: str,
    verbose: bool = False,
) -> tuple[str, str, dict[str, Any]]:
    """
    Fetch content from a URL, automatically detecting the type.

    Args:
        url: The URL to fetch
        verbose: Print verbose output

    Returns:
        Tuple of (content_text, url_type, metadata)
    """
    url_type, info = detect_url_type(url)

    if verbose:
        print(f"Detected URL type: {url_type}", file=sys.stderr)
        print(f"URL info: {info}", file=sys.stderr)

    if url_type == URLType.JIRA:
        ticket_id = info.get("ticket_id")
        if not ticket_id:
            raise ValueError(f"Could not extract ticket ID from JIRA URL: {url}")
        content, metadata = fetch_jira_content(ticket_id, verbose=verbose)
        return content, url_type, metadata

    elif url_type == URLType.CONFLUENCE:
        page_id = info.get("page_id")
        if not page_id:
            raise ValueError(
                f"Could not extract page ID from Confluence URL: {url}. "
                "Please use a URL that includes the page ID (e.g., /pages/12345/)"
            )
        content, metadata = fetch_confluence_content(
            page_id=page_id,
            space=info.get("space"),
            verbose=verbose,
        )
        return content, url_type, metadata

    else:
        # Generic web URL
        normalized_url = info.get("url", url)
        content, metadata = fetch_web_content(normalized_url, verbose=verbose)
        return content, url_type, metadata


# ============================================================================
# Input Handling
# ============================================================================


def fetch_multiple_urls(
    urls: list[str],
    verbose: bool = False,
) -> tuple[str, str, list[str], dict[str, Any]]:
    """
    Fetch content from multiple URLs and merge them.

    Args:
        urls: List of URLs to fetch
        verbose: Print verbose output

    Returns:
        Tuple of (merged_content, input_type, source_urls, merged_metadata)
    """
    all_contents: list[str] = []
    all_metadata: dict[str, Any] = {
        "urls": [],
        "url_types": [],
        "per_url_metadata": [],
    }

    for url in urls:
        try:
            if verbose:
                print(f"Fetching URL: {url}", file=sys.stderr)

            content, url_type, metadata = fetch_url_content(url, verbose=verbose)

            # Add header to distinguish content from different URLs
            header = f"\n{'=' * 60}\n=== SOURCE: {url} ===\n=== TYPE: {url_type} ===\n{'=' * 60}\n"
            all_contents.append(header + content)

            all_metadata["urls"].append(url)
            all_metadata["url_types"].append(url_type)
            all_metadata["per_url_metadata"].append(metadata)

            if verbose:
                print(
                    f"  Fetched {len(content)} chars from {url_type} URL",
                    file=sys.stderr,
                )

        except Exception as e:
            print(f"Warning: Failed to fetch {url}: {e}", file=sys.stderr)
            all_metadata["urls"].append(url)
            all_metadata["url_types"].append("error")
            all_metadata["per_url_metadata"].append({"error": str(e)})

    if not all_contents:
        raise ValueError("Failed to fetch content from any of the provided URLs")

    # Determine the primary input type based on URL types
    url_types = [t for t in all_metadata["url_types"] if t != "error"]
    if url_types:
        # Use the most common URL type, prefer confluence/jira over generic web
        type_priority = {URLType.CONFLUENCE: 1, URLType.JIRA: 2, URLType.GENERIC: 3}
        primary_type = min(url_types, key=lambda t: type_priority.get(t, 99))
    else:
        primary_type = "unknown"

    merged_content = "\n\n".join(all_contents)
    input_type = f"multi_url_{primary_type}"

    return merged_content, input_type, urls, all_metadata


def read_input(
    args: argparse.Namespace,
) -> tuple[str, str, list[str], dict[str, Any] | None]:
    """
    Read input based on provided arguments.

    Returns:
        Tuple of (content, input_type, source_files, url_metadata)
        - url_metadata is only populated for URL inputs
    """
    if getattr(args, "url", None):
        try:
            content, url_type, metadata = fetch_url_content(
                args.url, verbose=getattr(args, "verbose", False)
            )
            input_type = f"url_{url_type}"
            return content, input_type, [args.url], metadata
        except Exception as e:
            print(f"Error fetching URL: {e}", file=sys.stderr)
            sys.exit(1)

    if getattr(args, "urls", None):
        try:
            return fetch_multiple_urls(
                args.urls, verbose=getattr(args, "verbose", False)
            )
        except Exception as e:
            print(f"Error fetching URLs: {e}", file=sys.stderr)
            sys.exit(1)

    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)

        if path.stat().st_size > MAX_FILE_SIZE:
            print(
                f"Warning: File {args.file} exceeds {MAX_FILE_SIZE // 1024}KB, may be truncated",
                file=sys.stderr,
            )

        content = path.read_text(errors="replace")
        return content, "file", [str(path)], None

    elif args.folder:
        folder = Path(args.folder)
        if not folder.exists() or not folder.is_dir():
            print(f"Error: Folder not found: {args.folder}", file=sys.stderr)
            sys.exit(1)

        contents = []
        source_files = []

        pattern = "**/*" if args.recursive else "*"
        for file_path in folder.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in TEXT_EXTENSIONS:
                if file_path.stat().st_size <= MAX_FILE_SIZE:
                    try:
                        file_content = file_path.read_text(errors="replace")
                        contents.append(
                            f"=== FILE: {file_path.name} ===\n{file_content}"
                        )
                        source_files.append(str(file_path))
                    except Exception as e:
                        print(
                            f"Warning: Could not read {file_path}: {e}", file=sys.stderr
                        )

        if not contents:
            print(
                f"Error: No readable text files found in {args.folder}", file=sys.stderr
            )
            sys.exit(1)

        return "\n\n".join(contents), "folder", source_files, None

    elif args.text:
        return args.text, "text", [], None

    elif args.stdin:
        content = sys.stdin.read()
        return content, "stdin", [], None

    else:
        print(
            "Error: No input provided. Use --file, --folder, --text, --url, or --stdin",
            file=sys.stderr,
        )
        sys.exit(1)


# ============================================================================
# Entity Extraction
# ============================================================================


def extract_tickets(content: str) -> list[ExtractedEntity]:
    """Extract ticket IDs from content."""
    tickets = []
    seen = set()

    for pattern in TICKET_PATTERNS:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            ticket_id = match.group(1).upper()
            if ticket_id not in seen:
                seen.add(ticket_id)

                # Get surrounding context
                start = max(0, match.start() - 50)
                end = min(len(content), match.end() + 100)
                context = content[start:end].replace("\n", " ").strip()

                # Check if ticket file exists
                ticket_file = TICKETS_DIR / f"{ticket_id}.md"
                exists = ticket_file.exists()

                tickets.append(
                    ExtractedEntity(
                        type="ticket",
                        value=ticket_id,
                        context=context,
                        exists=exists,
                        slug=ticket_id,
                    )
                )

    return tickets


def extract_dates(content: str) -> list[tuple[str, int]]:
    """Extract dates from content with their positions."""
    dates_with_pos = []
    seen = set()

    for pattern, fmt in DATE_PATTERNS:
        for match in re.finditer(pattern, content):
            date_str = match.group(1)
            try:
                # Try to parse and normalize to ISO format
                parsed = datetime.strptime(
                    date_str.replace(",", ""), fmt.replace(",", "")
                )
                iso_date = parsed.strftime("%Y-%m-%d")
                if iso_date not in seen:
                    seen.add(iso_date)
                    dates_with_pos.append((iso_date, match.start()))
            except ValueError:
                continue

    # Sort by position in text (first appearing date first)
    dates_with_pos.sort(key=lambda x: x[1])
    return [d[0] for d in dates_with_pos]


def extract_people(
    content: str, known_entities: dict[str, Any]
) -> list[ExtractedEntity]:
    """Extract people mentions from content."""
    people = []
    seen_slugs = set()
    content_lower = content.lower()

    for slug, person_data in known_entities.get("people", {}).items():
        for alias in person_data.get("aliases", []):
            # Case-insensitive search
            alias_lower = alias.lower()
            if alias_lower in content_lower:
                if slug not in seen_slugs:
                    seen_slugs.add(slug)

                    # Count mentions
                    mentions = content_lower.count(alias_lower)

                    # Get context around first mention
                    idx = content_lower.find(alias_lower)
                    start = max(0, idx - 30)
                    end = min(len(content), idx + len(alias) + 50)
                    context = content[start:end].replace("\n", " ").strip()

                    people.append(
                        ExtractedEntity(
                            type="person",
                            value=person_data["full_name"],
                            context=context,
                            exists=True,
                            slug=slug,
                            confidence=1.0 if mentions > 1 else 0.8,
                        )
                    )
                    break

    return people


def extract_projects(
    content: str, known_entities: dict[str, Any]
) -> list[ExtractedEntity]:
    """Extract project mentions from content."""
    projects = []
    seen_slugs = set()
    content_lower = content.lower()

    for slug, project_data in known_entities.get("projects", {}).items():
        for alias in project_data.get("aliases", []):
            alias_lower = alias.lower()
            if (
                alias_lower in content_lower and len(alias_lower) > 3
            ):  # Avoid short matches
                if slug not in seen_slugs:
                    seen_slugs.add(slug)

                    idx = content_lower.find(alias_lower)
                    start = max(0, idx - 30)
                    end = min(len(content), idx + len(alias) + 50)
                    context = content[start:end].replace("\n", " ").strip()

                    projects.append(
                        ExtractedEntity(
                            type="project",
                            value=project_data["name"],
                            context=context,
                            exists=True,
                            slug=slug,
                        )
                    )
                    break

    return projects


def extract_action_items(content: str) -> list[dict[str, Any]]:
    """Extract action items from content."""
    actions = []

    for pattern in ACTION_PATTERNS:
        for match in re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE):
            if len(match.groups()) == 1:
                task = match.group(1).strip()
                owner = None
            else:
                owner = match.group(1)
                task = match.group(2).strip()

            # Try to extract due date from task
            due_date = None
            for date_pattern, fmt in DATE_PATTERNS:
                date_match = re.search(date_pattern, task)
                if date_match:
                    try:
                        parsed = datetime.strptime(
                            date_match.group(1).replace(",", ""), fmt.replace(",", "")
                        )
                        due_date = parsed.strftime("%Y-%m-%d")
                        break
                    except ValueError:
                        continue

            actions.append(
                {
                    "task": task,
                    "owner": owner,
                    "due": due_date,
                }
            )

    return actions


def extract_decisions(content: str) -> list[dict[str, Any]]:
    """Extract decisions from content."""
    decisions = []

    for pattern in DECISION_PATTERNS:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            decision_text = match.group(1).strip()
            if len(decision_text) > 10:  # Filter out short/incomplete matches
                decisions.append(
                    {
                        "text": decision_text,
                        "stakeholders": [],
                    }
                )

    return decisions


def extract_risks(content: str) -> list[dict[str, Any]]:
    """Extract risks and blockers from content."""
    risks = []

    for pattern in RISK_PATTERNS:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            risk_text = match.group(1).strip()
            if len(risk_text) > 10:
                # Determine severity based on keywords
                severity = "medium"
                if any(
                    word in risk_text.lower()
                    for word in ["critical", "blocker", "urgent", "showstopper"]
                ):
                    severity = "high"
                elif any(
                    word in risk_text.lower() for word in ["minor", "low priority"]
                ):
                    severity = "low"

                risks.append(
                    {
                        "text": risk_text,
                        "severity": severity,
                    }
                )

    return risks


# ============================================================================
# Content Type Detection
# ============================================================================


def detect_content_type(content: str) -> str:
    """Detect the type of content."""
    content_lower = content.lower()

    scores = {content_type: 0 for content_type in CONTENT_TYPE_KEYWORDS}

    for content_type, keywords in CONTENT_TYPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in content_lower:
                scores[content_type] += 1

    # Get the type with highest score
    best_type = max(scores, key=scores.get)

    # If no clear winner, default to "notes"
    if scores[best_type] == 0:
        return "notes"

    return best_type


# ============================================================================
# File Operations Planning
# ============================================================================


def load_template(template_name: str) -> str:
    """Load a template file."""
    template_path = TEMPLATES_DIR / template_name
    if template_path.exists():
        return template_path.read_text()
    return ""


def plan_ticket_operations(
    tickets: list[ExtractedEntity],
    content: str,
    detected_date: str,
) -> tuple[list[FileOperation], list[str]]:
    """Plan file operations for tickets."""
    operations = []
    jira_enrichment = []

    for ticket in tickets:
        ticket_path = f"tickets/{ticket.value}.md"

        if not ticket.exists:
            # Create new ticket file
            operations.append(
                FileOperation(
                    action="create",
                    path=ticket_path,
                    template="ticket.md",
                    data={
                        "ticket_id": ticket.value,
                        "project": "Unknown",
                        "type": "Request",
                        "status": "Open",
                        "priority": "Medium",
                        "assignee": "",
                        "summary": ticket.context[:100] if ticket.context else "",
                        "date": detected_date,
                    },
                )
            )
            jira_enrichment.append(ticket.value)
        else:
            # Append context to existing ticket
            operations.append(
                FileOperation(
                    action="update",
                    path=ticket_path,
                    template=None,
                    data={},
                    append_content=f"\n### {detected_date} – Context Update\n\n{ticket.context}\n",
                    section="Details / Context",
                )
            )

    return operations, jira_enrichment


def plan_person_operations(
    people: list[ExtractedEntity],
    content: str,
    content_type: str,
    detected_date: str,
    action_items: list[dict[str, Any]],
) -> list[FileOperation]:
    """Plan file operations for people."""
    operations = []

    for person in people:
        if not person.slug:
            continue

        person_folder = f"communication/people/{person.slug}"
        notes_path = f"{person_folder}/notes.md"
        references_path = f"{person_folder}/references.md"

        # Build notes entry
        notes_entry = (
            f"### {detected_date} – {content_type.replace('_', ' ').title()}\n"
        )
        notes_entry += f"- Context: {person.context}\n"

        # Add relevant action items
        person_actions = [
            a
            for a in action_items
            if a.get("owner") and person.value.lower() in a["owner"].lower()
        ]
        if person_actions:
            notes_entry += "- Actions:\n"
            for action in person_actions:
                due = f" (due: {action['due']})" if action.get("due") else ""
                notes_entry += f"  - [ ] {action['task']}{due}\n"

        operations.append(
            FileOperation(
                action="update",
                path=notes_path,
                template=None,
                data={},
                append_content=f"\n{notes_entry}",
                section=None,
            )
        )

        # Add reference entry
        ref_entry = f"| {detected_date} | {content_type.replace('_', ' ').title()} | Ingested content | {person.context[:50]}... |"
        operations.append(
            FileOperation(
                action="update",
                path=references_path,
                template=None,
                data={},
                append_content=f"\n{ref_entry}",
                section="table",
            )
        )

    return operations


def plan_new_person_operations(
    new_person_name: str,
    detected_date: str,
) -> list[FileOperation]:
    """Plan operations to create a new person folder."""
    slug = new_person_name.lower().replace(" ", "_").replace("-", "_")
    slug = re.sub(r"[^a-z0-9_]", "", slug)

    person_folder = f"communication/people/{slug}"

    operations = [
        FileOperation(
            action="create",
            path=f"{person_folder}/profile.md",
            template="person_profile.md",
            data={
                "full_name": new_person_name,
                "nickname": "",
                "role": "Unknown",
                "team": "Unknown",
                "communication_focus": "",
                "date": detected_date,
            },
        ),
        FileOperation(
            action="create",
            path=f"{person_folder}/notes.md",
            template="person_notes.md",
            data={"full_name": new_person_name},
        ),
        FileOperation(
            action="create",
            path=f"{person_folder}/references.md",
            template="person_references.md",
            data={"full_name": new_person_name},
        ),
        FileOperation(
            action="create",
            path=f"{person_folder}/thoughts.md",
            template="person_thoughts.md",
            data={"full_name": new_person_name},
        ),
    ]

    return operations


def plan_meeting_operations(
    content: str,
    content_type: str,
    people: list[ExtractedEntity],
    detected_date: str,
    action_items: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    risks: list[dict[str, Any]],
) -> list[FileOperation]:
    """Plan operations for meeting notes."""
    operations = []

    if content_type != "meeting":
        return operations

    # Determine meeting file location
    participants = [p.value for p in people]

    if len(participants) == 2 and any("chris" in p.lower() for p in participants):
        # 1:1 meeting - put in other person's folder
        other_person = next((p for p in people if "chris" not in p.value.lower()), None)
        if other_person and other_person.slug:
            meeting_path = f"communication/people/{other_person.slug}/meetings/{detected_date}_meeting.md"
        else:
            meeting_path = f"communication/meetings/{detected_date}_meeting.md"
    else:
        # Multi-person meeting - put in central location
        meeting_path = f"communication/meetings/{detected_date}_meeting.md"

    # Build meeting data
    meeting_data = {
        "date": detected_date,
        "time": "00:00",
        "duration": "30m",
        "location": "Remote",
        "participants": participants,
        "owner": participants[0] if participants else "Unknown",
        "type": "1:1" if len(participants) == 2 else "Team Sync",
        "notes": content[:500] if len(content) > 500 else content,
        "actions": action_items,
        "decisions": decisions,
        "risks": risks,
    }

    operations.append(
        FileOperation(
            action="create",
            path=meeting_path,
            template="meeting_template.md",
            data=meeting_data,
        )
    )

    return operations


def plan_idea_operations(
    content: str,
    content_type: str,
    detected_date: str,
    people: list[ExtractedEntity],
) -> list[FileOperation]:
    """Plan operations for new ideas."""
    operations = []

    if content_type != "idea":
        return operations

    # Try to extract idea title from content
    title_match = re.search(
        r"(?:idea|concept|proposal):\s*(.+?)(?:\n|$)", content, re.IGNORECASE
    )
    if title_match:
        title = title_match.group(1).strip()
    else:
        # Use first line or first sentence
        first_line = content.split("\n")[0][:50]
        title = first_line.strip() or "New Idea"

    slug = title.lower().replace(" ", "_")
    slug = re.sub(r"[^a-z0-9_]", "", slug)[:30]

    idea_path = f"idea_development/{slug}/project.md"

    # Check if idea folder already exists
    if not (IDEAS_DIR / slug).exists():
        operations.append(
            FileOperation(
                action="create",
                path=idea_path,
                template="project_idea.md",
                data={
                    "name": title,
                    "status": "Idea",
                    "originator": people[0].value if people else "Unknown",
                    "request_date": detected_date,
                    "context": content[:500],
                },
            )
        )

    return operations


# NOTE: Calendar event creation has been moved to the LLM agent workflow.
# The agent uses the calendar_create tool (via calendar_helper.py) instead of
# creating calendar events directly in this script. This allows:
# 1. Proper natural language date conversion by the LLM
# 2. Consistent event creation through the calendar tool
# 3. Automatic meeting file generation for meeting-type events
#
# The dates_found list in the extraction result provides the dates for the
# LLM to use when creating calendar events.


# ============================================================================
# File Operation Execution
# ============================================================================


def fill_template(template_content: str, data: dict[str, Any]) -> str:
    """Fill a template with data."""
    result = template_content

    # Handle YAML frontmatter first
    if result.startswith("---"):
        frontmatter_end = result.find("---", 3)
        if frontmatter_end != -1:
            frontmatter = result[3:frontmatter_end]
            body = result[frontmatter_end + 3 :]

            for key, value in data.items():
                if isinstance(value, str) and value:
                    # Update existing frontmatter field
                    pattern = rf"^{key}:.*$"
                    replacement = f"{key}: {value}"
                    frontmatter = re.sub(
                        pattern, replacement, frontmatter, flags=re.MULTILINE
                    )
                elif isinstance(value, list) and key == "participants":
                    # Handle participants list specially for YAML
                    pattern = rf"^{key}:.*?(?=^\w+:|^---|\Z)"
                    participants_yaml = f"{key}:\n" + "\n".join(
                        f"  - {p}" for p in value
                    )
                    frontmatter = re.sub(
                        pattern,
                        participants_yaml + "\n",
                        frontmatter,
                        flags=re.MULTILINE | re.DOTALL,
                    )

            result = "---" + frontmatter + "---" + body

    # Replace placeholders in body
    for key, value in data.items():
        if isinstance(value, str):
            result = result.replace(f"${{{key}}}", value)
            result = result.replace(f"[{key.title()}]", value)
            result = result.replace(f"<{key.title()}>", value)
            result = result.replace(f"<{key}>", value)
            result = result.replace(f"[{key}]", value)

    # Handle ticket-specific replacements
    if "ticket_id" in data:
        result = result.replace("TICKET-ID", data["ticket_id"])
        result = result.replace("# TICKET-ID:", f"# {data['ticket_id']}:")
        if data.get("summary"):
            result = result.replace("Title Description", data["summary"][:80])

    # Handle meeting-specific content
    if "notes" in data and data["notes"]:
        # Replace the Notes section placeholder
        notes_pattern = r"(## Notes\n).*?(?=\n## )"
        notes_content = f"\\1- {data['notes'][:500]}\n\n"
        result = re.sub(notes_pattern, notes_content, result, flags=re.DOTALL)

    if "actions" in data and data["actions"]:
        # Build actions section
        actions_content = "## Actions\n"
        for action in data["actions"]:
            owner = action.get("owner", "TBD")
            task = action.get("task", "")
            due = action.get("due", data.get("date", "TBD"))
            actions_content += f"- [ ] {owner} – {task} (due: {due})\n"

        # Replace actions section
        actions_pattern = r"## Actions\n.*?(?=\n## |\Z)"
        result = re.sub(
            actions_pattern, actions_content + "\n", result, flags=re.DOTALL
        )

    if "decisions" in data and data["decisions"]:
        # Build decisions section
        decisions_content = "## Decisions\n"
        for decision in data["decisions"]:
            text = decision.get("text", "")
            decisions_content += f"- {text}\n"

        # Replace decisions section
        decisions_pattern = r"## Decisions\n.*?(?=\n## |\Z)"
        result = re.sub(
            decisions_pattern, decisions_content + "\n", result, flags=re.DOTALL
        )

    if "risks" in data and data["risks"]:
        # Build risks section
        risks_content = "## Risks / Issues\n"
        for risk in data["risks"]:
            text = risk.get("text", "")
            severity = risk.get("severity", "medium")
            risks_content += f"- [{severity.upper()}] {text}\n"

        # Replace risks section
        risks_pattern = r"## Risks / Issues\n.*?(?=\n## |\Z)"
        result = re.sub(risks_pattern, risks_content + "\n", result, flags=re.DOTALL)

    # Replace meeting title
    if "participants" in data and "Meeting:" not in data.get("title", ""):
        participants = data.get("participants", [])
        title = f"Meeting: {', '.join(participants[:3])}"
        if len(participants) > 3:
            title += f" +{len(participants) - 3}"
        result = result.replace("# <Meeting Title>", f"# {title}")
        result = result.replace("# \n", f"# {title}\n")

    # Handle calendar event templates
    if "event_id" in data:
        event_id = data["event_id"]
        result = result.replace("EVENT-XXX", event_id)
        result = result.replace("id: EVENT-XXX", f"id: {event_id}")

        if data.get("title"):
            result = result.replace('title: "Event title"', f'title: "{data["title"]}"')
            result = result.replace(
                f"# {event_id}: Title", f"# {event_id}: {data['title']}"
            )

        if data.get("type"):
            result = re.sub(
                r"type: meeting.*",
                f"type: {data['type']}",
                result,
            )

        if data.get("date"):
            result = result.replace("date: YYYY-MM-DD", f"date: {data['date']}")

        if data.get("participants"):
            participants_yaml = "participants:\n" + "\n".join(
                f"  - {p}" for p in data["participants"]
            )
            result = re.sub(
                r"participants:\n  - person_slug",
                participants_yaml,
                result,
            )

        if data.get("ticket"):
            result = result.replace("ticket: null", f"ticket: {data['ticket']}")

        if data.get("project"):
            result = result.replace("project: null", f"project: {data['project']}")

        if data.get("description"):
            result = result.replace(
                "Brief description of the event.", data["description"]
            )

        if data.get("created"):
            result = result.replace(
                "created: YYYY-MM-DD", f"created: {data['created']}"
            )

    # Clean up remaining generic placeholders
    result = re.sub(
        r"YYYY-MM-DD", data.get("date", datetime.now().strftime("%Y-%m-%d")), result
    )

    # Remove empty placeholder patterns but keep structure
    result = re.sub(r"\[Video Call Link\]", "", result)
    result = re.sub(
        r"- What do we want to achieve in this meeting\?",
        f"- Discussed: {data.get('notes', '')[:100]}..."
        if data.get("notes")
        else "- TBD",
        result,
    )

    return result


def execute_operations(
    operations: list[FileOperation], verbose: bool = False
) -> dict[str, list[str]]:
    """Execute file operations."""
    results = {
        "created": [],
        "updated": [],
        "errors": [],
    }

    for op in operations:
        full_path = REPO_ROOT / op.path

        try:
            if op.action == "create":
                # Create parent directories
                full_path.parent.mkdir(parents=True, exist_ok=True)

                if full_path.exists():
                    if verbose:
                        print(f"Skipping existing file: {op.path}", file=sys.stderr)
                    continue

                # Load and fill template
                if op.template:
                    template_content = load_template(op.template)
                    content = fill_template(template_content, op.data)
                else:
                    content = op.append_content or ""

                full_path.write_text(content)
                results["created"].append(op.path)
                if verbose:
                    print(f"Created: {op.path}", file=sys.stderr)

            elif op.action == "update":
                if not full_path.exists():
                    if verbose:
                        print(f"File not found for update: {op.path}", file=sys.stderr)
                    continue

                existing_content = full_path.read_text()

                if op.append_content:
                    if op.section == "table":
                        # Find the table and append before the last row
                        # For references.md, just append to end
                        new_content = (
                            existing_content.rstrip() + "\n" + op.append_content
                        )
                    elif op.section:
                        # Find the section and append after it
                        section_pattern = (
                            rf"(##\s*{re.escape(op.section)}.*?)(?=\n##|\Z)"
                        )
                        match = re.search(section_pattern, existing_content, re.DOTALL)
                        if match:
                            insert_pos = match.end()
                            new_content = (
                                existing_content[:insert_pos]
                                + op.append_content
                                + existing_content[insert_pos:]
                            )
                        else:
                            new_content = (
                                existing_content.rstrip() + "\n" + op.append_content
                            )
                    else:
                        new_content = (
                            existing_content.rstrip() + "\n" + op.append_content
                        )

                    full_path.write_text(new_content)
                    results["updated"].append(op.path)
                    if verbose:
                        print(f"Updated: {op.path}", file=sys.stderr)

        except Exception as e:
            results["errors"].append(f"{op.path}: {str(e)}")
            if verbose:
                print(f"Error with {op.path}: {e}", file=sys.stderr)

    return results


# ============================================================================
# Main Processing
# ============================================================================


def process_content(
    content: str,
    input_type: str,
    source_files: list[str],
    override_date: str | None,
    plan_only: bool,
    verbose: bool,
    url_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Process content and extract all entities."""

    # Load known entities
    known_entities = load_known_entities()

    # Detect content type
    content_type = detect_content_type(content)
    if verbose:
        print(f"Detected content type: {content_type}", file=sys.stderr)

    # Extract dates
    dates = extract_dates(content)
    detected_date = override_date or (
        dates[0] if dates else datetime.now().strftime("%Y-%m-%d")
    )
    if verbose:
        print(f"Detected date: {detected_date}", file=sys.stderr)

    # Extract entities
    tickets = extract_tickets(content)
    people = extract_people(content, known_entities)
    projects = extract_projects(content, known_entities)
    action_items = extract_action_items(content)
    decisions = extract_decisions(content)
    risks = extract_risks(content)

    if verbose:
        print(
            f"Found: {len(tickets)} tickets, {len(people)} people, {len(projects)} projects",
            file=sys.stderr,
        )
        print(
            f"Found: {len(action_items)} actions, {len(decisions)} decisions, {len(risks)} risks",
            file=sys.stderr,
        )

    # Plan file operations
    all_operations: list[FileOperation] = []
    jira_enrichment: list[str] = []

    # Ticket operations
    ticket_ops, jira_tickets = plan_ticket_operations(tickets, content, detected_date)
    all_operations.extend(ticket_ops)
    jira_enrichment.extend(jira_tickets)

    # Person operations
    person_ops = plan_person_operations(
        people, content, content_type, detected_date, action_items
    )
    all_operations.extend(person_ops)

    # Meeting operations
    meeting_ops = plan_meeting_operations(
        content, content_type, people, detected_date, action_items, decisions, risks
    )
    all_operations.extend(meeting_ops)

    # Idea operations
    idea_ops = plan_idea_operations(content, content_type, detected_date, people)
    all_operations.extend(idea_ops)

    # NOTE: Calendar operations are now handled by the LLM agent using the calendar_create tool.
    # The dates are passed in the extraction result for the agent to process.

    # Execute operations (unless plan_only)
    execution_results = {"created": [], "updated": [], "errors": []}
    if not plan_only:
        execution_results = execute_operations(all_operations, verbose)

    # Build result
    result: dict[str, Any] = {
        "metadata": {
            "input_type": input_type,
            "source_files": source_files,
            "files_processed": len(source_files) if source_files else 1,
            "content_type": content_type,
            "detected_date": detected_date,
            "content_length": len(content),
        },
    }

    # Add URL-specific metadata if present
    if url_metadata:
        result["metadata"]["url_source"] = url_metadata

    result.update(
        {
            "entities": {
                "people": [
                    {
                        "name": p.value,
                        "slug": p.slug,
                        "exists": p.exists,
                        "context": p.context[:100],
                        "confidence": p.confidence,
                    }
                    for p in people
                ],
                "tickets": [
                    {
                        "id": t.value,
                        "exists": t.exists,
                        "context": t.context[:100],
                    }
                    for t in tickets
                ],
                "projects": [
                    {
                        "name": p.value,
                        "slug": p.slug,
                        "exists": p.exists,
                    }
                    for p in projects
                ],
            },
            "extracted": {
                "action_items": action_items,
                "decisions": decisions,
                "risks": risks,
                "dates_found": dates,
                # NOTE: Calendar events are created by the LLM agent using calendar_create tool
                # based on the dates_found list. The agent converts dates to ISO format.
            },
            "file_operations": {
                "planned": [
                    {
                        "action": op.action,
                        "path": op.path,
                        "template": op.template,
                    }
                    for op in all_operations
                ],
                "executed": execution_results if not plan_only else None,
            },
            "jira_enrichment_needed": jira_enrichment,
            "ambiguous": [],  # To be filled by LLM if needed
            "raw_content_preview": content[:500] + "..."
            if len(content) > 500
            else content,
        }
    )

    return result


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract and ingest information from text into repository files"
    )

    # Input options (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--file", "-f", type=str, help="Path to input file")
    input_group.add_argument("--folder", "-d", type=str, help="Path to input folder")
    input_group.add_argument("--text", "-t", type=str, help="Direct text input")
    input_group.add_argument(
        "--url",
        "-u",
        type=str,
        help="URL to fetch content from (web page, Confluence, or JIRA)",
    )
    input_group.add_argument(
        "--urls",
        type=str,
        nargs="+",
        help="Multiple URLs to fetch and merge (space-separated)",
    )
    input_group.add_argument(
        "--stdin", "-s", action="store_true", help="Read from stdin"
    )

    # Processing options
    parser.add_argument(
        "--recursive", "-r", action="store_true", help="Process folder recursively"
    )
    parser.add_argument("--date", type=str, help="Override detected date (YYYY-MM-DD)")
    parser.add_argument(
        "--plan-only", action="store_true", help="Output plan without executing"
    )

    # Output options
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Read input
    content, input_type, source_files, url_metadata = read_input(args)

    if args.verbose:
        print(f"Input type: {input_type}", file=sys.stderr)
        print(f"Content length: {len(content)} characters", file=sys.stderr)
        if url_metadata:
            print(f"URL metadata: {url_metadata}", file=sys.stderr)

    # Process content
    result = process_content(
        content=content,
        input_type=input_type,
        source_files=source_files,
        override_date=args.date,
        plan_only=args.plan_only,
        verbose=args.verbose,
        url_metadata=url_metadata,
    )

    # Output
    if args.json or args.pretty:
        indent = 2 if args.pretty else None
        print(json.dumps(result, indent=indent, ensure_ascii=False))
    else:
        # Human-readable summary
        print("\n" + "=" * 60)
        print("INFORMATION INGESTED")
        print("=" * 60)
        print(f"Input:         {input_type}")
        print(f"Content Type:  {result['metadata']['content_type']}")
        print(f"Source Date:   {result['metadata']['detected_date']}")
        print("-" * 60)

        if result["file_operations"]["executed"]:
            created = result["file_operations"]["executed"]["created"]
            updated = result["file_operations"]["executed"]["updated"]

            if created:
                print("CREATED:")
                for f in created:
                    print(f"  ✓ {f}")

            if updated:
                print("UPDATED:")
                for f in updated:
                    print(f"  ✓ {f}")
        else:
            print("PLANNED OPERATIONS:")
            for op in result["file_operations"]["planned"]:
                print(f"  • {op['action'].upper()}: {op['path']}")

        print("-" * 60)
        print("ENTITIES:")
        print(f"  People:   {len(result['entities']['people'])}")
        print(f"  Tickets:  {len(result['entities']['tickets'])}")
        print(f"  Projects: {len(result['entities']['projects'])}")
        print(f"  Actions:  {len(result['extracted']['action_items'])}")
        print(f"  Decisions:{len(result['extracted']['decisions'])}")
        print(f"  Risks:    {len(result['extracted']['risks'])}")
        print(f"  Calendar: {len(result['extracted']['calendar_events'])}")

        if result["jira_enrichment_needed"]:
            print("-" * 60)
            print(
                f"JIRA ENRICHMENT NEEDED: {', '.join(result['jira_enrichment_needed'])}"
            )

        print("=" * 60)


if __name__ == "__main__":
    main()
