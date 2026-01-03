#!/usr/bin/env python3
"""
Ticket Improver Script - GitHub & Local Operations

Provides functionality for ticket improvement workflows that involve
GitHub repositories and local filesystem context. All Atlassian (JIRA/Confluence)
operations have been moved to .opencode/tool/atlassian_client.py.

Usage:
    python scripts/ticket_improver.py local-context <TICKET_ID>
    python scripts/ticket_improver.py find-repos <TICKET_ID> [--org ORG]
    python scripts/ticket_improver.py repo-context <OWNER> <REPO>
    python scripts/ticket_improver.py ensure-repo <TICKET_ID> [--org ORG]
    python scripts/ticket_improver.py local-repo-context <REPO_PATH>

Commands:
    local-context        Find local context for a ticket (project, epic, related tickets)
    find-repos           Search GitHub for repositories matching a ticket (via API)
    repo-context         Get repository context via GitHub API (remote)
    ensure-repo          Ensure repository exists locally at project_management/<project>/repo/
                         Clones via gh CLI if not present
    local-repo-context   Get repository context from local filesystem clone

All commands output JSON for easy parsing by LLM agents.

Note: For JIRA/Confluence operations, use:
    python .opencode/tool/atlassian_client.py <command> [args...]
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

# ============================================================================
# Configuration
# ============================================================================

REPO_ROOT = Path(__file__).parent.parent
TICKETS_DIR = REPO_ROOT / "tickets"
PROJECTS_DIR = REPO_ROOT / "project_management"
COMMUNICATION_DIR = REPO_ROOT / "communication"
AGENTS_INDEX = REPO_ROOT / "agents_index.yaml"

# Ticket ID pattern - matches common JIRA prefixes
TICKET_PATTERN = re.compile(
    r"\b(DS|FML|FLUG|FLIGHTS|FIOS|FPRO|BI|HD)-(\d+)\b", re.IGNORECASE
)

# Default GitHub organization
DEFAULT_ORG = "invia-flights"

# Subdirectory name for cloned repos within project folders
REPO_SUBDIR = "repo"


# ============================================================================
# Local Context Search
# ============================================================================


def find_local_context(ticket_id: str) -> dict[str, Any]:
    """
    Search local repository for context related to a ticket.

    Searches:
    - tickets/ folder for the ticket file and epic relationships
    - project_management/ for project information
    - agents_index.yaml for project mappings
    """
    result = {
        "ticket_id": ticket_id,
        "local_ticket_file": None,
        "epic": None,
        "project": None,
        "related_tickets": [],
        "communication_refs": [],
    }

    # Extract ticket prefix and number
    match = TICKET_PATTERN.match(ticket_id)
    if not match:
        result["error"] = f"Invalid ticket ID format: {ticket_id}"
        return result

    prefix = match.group(1).upper()
    number = int(match.group(2))

    # Check for local ticket file
    ticket_file = TICKETS_DIR / f"{ticket_id}.md"
    if ticket_file.exists():
        result["local_ticket_file"] = str(ticket_file.relative_to(REPO_ROOT))
        ticket_content = ticket_file.read_text()

        # Extract epic from frontmatter
        epic_match = re.search(r"^epic:\s*(\S+)", ticket_content, re.MULTILINE)
        if epic_match and epic_match.group(1) != "null":
            result["epic"] = epic_match.group(1)

        # Extract project from frontmatter
        project_match = re.search(r"^project:\s*(.+)$", ticket_content, re.MULTILINE)
        if project_match:
            result["project_from_ticket"] = project_match.group(1).strip()

    # Search for related tickets (same prefix, nearby numbers)
    nearby_range = range(max(1, number - 20), number + 20)
    for n in nearby_range:
        if n == number:
            continue
        related_id = f"{prefix}-{n}"
        related_file = TICKETS_DIR / f"{related_id}.md"
        if related_file.exists():
            # Read to get epic info
            content = related_file.read_text()
            epic_match = re.search(r"^epic:\s*(\S+)", content, re.MULTILINE)
            epic = (
                epic_match.group(1)
                if epic_match and epic_match.group(1) != "null"
                else None
            )
            result["related_tickets"].append(
                {
                    "ticket_id": related_id,
                    "epic": epic,
                    "distance": abs(n - number),
                }
            )

    # Sort related tickets by distance
    result["related_tickets"].sort(key=lambda x: x["distance"])
    result["related_tickets"] = result["related_tickets"][:10]  # Limit to 10

    # If we found an epic, find the project
    epic_to_find = result.get("epic")
    if not epic_to_find and result["related_tickets"]:
        # Use epic from nearest related ticket
        for rt in result["related_tickets"]:
            if rt.get("epic"):
                epic_to_find = rt["epic"]
                result["epic_inferred_from"] = rt["ticket_id"]
                break

    if epic_to_find:
        result["epic"] = epic_to_find
        # Search project_management for this epic
        for project_dir in PROJECTS_DIR.iterdir():
            if not project_dir.is_dir() or project_dir.name.startswith("."):
                continue
            project_file = project_dir / "project.md"
            if project_file.exists():
                content = project_file.read_text()
                if epic_to_find in content:
                    result["project"] = {
                        "folder": str(project_dir.relative_to(REPO_ROOT)),
                        "name": project_dir.name,
                    }
                    # Try to extract repository
                    # Match patterns like: **Repository**: `repo-name` or repository: repo-name
                    repo_match = re.search(
                        r"(?:\*\*)?[Rr]epository(?:\*\*)?[:\s]*`([a-zA-Z0-9_-]+)`",
                        content,
                    )
                    if not repo_match:
                        # Fallback pattern without backticks
                        repo_match = re.search(
                            r"[Rr]epository[:\s]+([a-zA-Z0-9_-]+)",
                            content,
                        )
                    if repo_match:
                        result["project"]["repository"] = repo_match.group(1)
                    break

    # Also search project_management by ticket prefix pattern
    if not result.get("project"):
        for project_dir in PROJECTS_DIR.iterdir():
            if not project_dir.is_dir() or project_dir.name.startswith("."):
                continue
            project_file = project_dir / "project.md"
            if project_file.exists():
                content = project_file.read_text()
                # Look for ticket prefix mentions
                if f"{prefix}-" in content.upper():
                    result["project"] = {
                        "folder": str(project_dir.relative_to(REPO_ROOT)),
                        "name": project_dir.name,
                        "match_type": "prefix_mention",
                    }
                    repo_match = re.search(
                        r"(?:\*\*)?[Rr]epository(?:\*\*)?[:\s]*`([a-zA-Z0-9_-]+)`",
                        content,
                    )
                    if not repo_match:
                        repo_match = re.search(
                            r"[Rr]epository[:\s]+([a-zA-Z0-9_-]+)",
                            content,
                        )
                    if repo_match:
                        result["project"]["repository"] = repo_match.group(1)
                    break

    # Search communication folder for references
    for person_dir in (COMMUNICATION_DIR / "people").iterdir():
        if not person_dir.is_dir():
            continue
        refs_file = person_dir / "references.md"
        if refs_file.exists():
            content = refs_file.read_text()
            if ticket_id in content:
                result["communication_refs"].append(
                    str(refs_file.relative_to(REPO_ROOT))
                )

    return result


# ============================================================================
# GitHub Repository Operations
# ============================================================================


def run_gh_command(args: list[str]) -> tuple[bool, str]:
    """Run a GitHub CLI command and return (success, output)."""
    try:
        result = subprocess.run(
            ["gh"] + args,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return True, result.stdout
        return False, result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except FileNotFoundError:
        return False, "GitHub CLI (gh) not found. Please install it."
    except Exception as e:
        return False, str(e)


def find_repos_for_ticket(ticket_id: str, org: str = DEFAULT_ORG) -> dict[str, Any]:
    """
    Find GitHub repositories that likely belong to this ticket.

    Strategy:
    1. Check local context for known repository mapping
    2. List recent repos in the organization
    3. Search commit messages for ticket ID patterns
    4. Score and rank repositories by relevance
    """
    result = {
        "ticket_id": ticket_id,
        "organization": org,
        "local_match": None,
        "github_candidates": [],
        "needs_user_input": False,
        "error": None,
    }

    # Extract ticket prefix and number
    match = TICKET_PATTERN.match(ticket_id)
    if not match:
        result["error"] = f"Invalid ticket ID format: {ticket_id}"
        return result

    prefix = match.group(1).upper()
    number = int(match.group(2))

    # First, check local context
    local_ctx = find_local_context(ticket_id)
    project = local_ctx.get("project") or {}
    if project.get("repository"):
        result["local_match"] = {
            "repository": project["repository"],
            "project_folder": project["folder"],
            "epic": local_ctx.get("epic"),
            "confidence": 1.0,
            "reason": "Found in local project configuration",
        }

    # Get list of repositories from GitHub
    success, output = run_gh_command(
        [
            "repo",
            "list",
            org,
            "--limit",
            "30",
            "--json",
            "name,updatedAt,description",
        ]
    )

    if not success:
        result["error"] = f"Failed to list repos: {output}"
        if result["local_match"]:
            return result  # We have local match, continue
        return result

    try:
        repos = json.loads(output)
    except json.JSONDecodeError:
        result["error"] = f"Failed to parse repo list: {output}"
        return result

    # Filter to recently updated repos (last 60 days)
    cutoff = datetime.now() - timedelta(days=60)
    active_repos = []
    for repo in repos:
        updated = repo.get("updatedAt", "")
        if updated:
            try:
                updated_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                if updated_dt.replace(tzinfo=None) > cutoff:
                    active_repos.append(repo)
            except (ValueError, TypeError):
                pass

    # Search commits in each active repo for ticket patterns
    candidates = []
    for repo in active_repos:
        repo_name = repo["name"]

        # Get recent commits
        success, commits_output = run_gh_command(
            [
                "api",
                f"repos/{org}/{repo_name}/commits",
                "--jq",
                ".[0:20] | .[].commit.message",
            ]
        )

        if not success:
            continue

        commit_messages = commits_output.strip()
        if not commit_messages:
            continue

        # Search for ticket patterns in commit messages
        found_tickets = []
        for line in commit_messages.split("\n"):
            matches = TICKET_PATTERN.findall(line)
            for m in matches:
                found_prefix = m[0].upper()
                found_number = int(m[1])
                if found_prefix == prefix:
                    found_tickets.append(
                        {
                            "ticket": f"{found_prefix}-{found_number}",
                            "number": found_number,
                            "distance": abs(found_number - number),
                        }
                    )

        if found_tickets:
            # Calculate relevance score
            # Lower distance = higher relevance
            min_distance = min(t["distance"] for t in found_tickets)
            exact_match = any(t["distance"] == 0 for t in found_tickets)

            if exact_match:
                confidence = 1.0
                reason = f"Exact match: {ticket_id} found in commit history"
            elif min_distance <= 5:
                confidence = 0.9
                nearby = [t["ticket"] for t in found_tickets if t["distance"] <= 5][:3]
                reason = f"Very close tickets found: {', '.join(nearby)}"
            elif min_distance <= 20:
                confidence = 0.7
                nearby = [t["ticket"] for t in found_tickets if t["distance"] <= 20][:3]
                reason = f"Related tickets found: {', '.join(nearby)}"
            else:
                confidence = 0.4
                reason = f"Same prefix ({prefix}) found but tickets are distant"

            candidates.append(
                {
                    "repository": repo_name,
                    "full_name": f"{org}/{repo_name}",
                    "description": repo.get("description"),
                    "confidence": confidence,
                    "reason": reason,
                    "found_tickets": [
                        t["ticket"]
                        for t in sorted(found_tickets, key=lambda x: x["distance"])[:5]
                    ],
                    "min_distance": min_distance,
                    "updated_at": repo.get("updatedAt"),
                }
            )

    # Sort candidates by confidence, then by min_distance
    candidates.sort(key=lambda x: (-x["confidence"], x["min_distance"]))
    result["github_candidates"] = candidates[:5]  # Top 5

    # Determine if user input is needed
    if result["local_match"] and result["local_match"]["confidence"] >= 0.9:
        result["needs_user_input"] = False
    elif candidates and candidates[0]["confidence"] >= 0.9:
        result["needs_user_input"] = False
    elif not candidates and not result["local_match"]:
        result["needs_user_input"] = True
    else:
        # Multiple candidates with similar confidence
        if (
            len(candidates) >= 2
            and candidates[0]["confidence"] - candidates[1]["confidence"] < 0.2
        ):
            result["needs_user_input"] = True
        elif candidates and candidates[0]["confidence"] < 0.7:
            result["needs_user_input"] = True

    return result


def ensure_repo_local(ticket_id: str, org: str = DEFAULT_ORG) -> dict[str, Any]:
    """
    Ensure repository for a ticket exists locally.

    Workflow:
    1. Find project folder from local context
    2. Check if repo/ subdirectory exists with a .git folder
    3. If not, identify repo name and clone via gh
    4. Return path info

    Returns dict with:
    - ticket_id: The input ticket ID
    - organization: GitHub org used
    - project_folder: Path to the project folder (relative to REPO_ROOT)
    - repository: Name of the repository
    - local_repo_path: Absolute path to local repo clone
    - cloned: True if repo was cloned during this call
    - already_exists: True if repo already existed locally
    - error: Error message if any step failed
    """
    result = {
        "ticket_id": ticket_id,
        "organization": org,
        "project_folder": None,
        "repository": None,
        "local_repo_path": None,
        "cloned": False,
        "already_exists": False,
        "error": None,
    }

    # Step 1: Get local context to find project and repo name
    local_ctx = find_local_context(ticket_id)
    project = local_ctx.get("project")

    if not project:
        result["error"] = (
            f"No project found for ticket {ticket_id}. "
            "Cannot determine repository location."
        )
        return result

    result["project_folder"] = project.get("folder")
    repo_name = project.get("repository")

    if not repo_name:
        result["error"] = (
            f"No repository defined in project {project['folder']}. "
            "Check project.md for **Repository**: `repo-name` field."
        )
        return result

    result["repository"] = repo_name

    # Step 2: Check if repo already exists locally
    project_path = REPO_ROOT / project["folder"]
    local_repo_path = project_path / REPO_SUBDIR

    if local_repo_path.exists() and (local_repo_path / ".git").exists():
        result["local_repo_path"] = str(local_repo_path)
        result["already_exists"] = True
        return result

    # Step 3: Ensure parent directory exists
    try:
        local_repo_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        result["error"] = f"Failed to create directory {local_repo_path.parent}: {e}"
        return result

    # Step 4: Clone the repository using gh CLI
    clone_target = str(local_repo_path)
    success, output = run_gh_command(
        ["repo", "clone", f"{org}/{repo_name}", clone_target]
    )

    if not success:
        result["error"] = f"Failed to clone {org}/{repo_name}: {output}"
        return result

    result["local_repo_path"] = clone_target
    result["cloned"] = True
    return result


def get_local_repo_context(repo_path: str) -> dict[str, Any]:
    """
    Get context information from a LOCAL repository clone.

    Reads directly from filesystem instead of GitHub API:
    - README.md (or variants)
    - Dependency files (requirements.txt, environment.yml, etc.)
    - Top-level file structure
    - opencode/Claude configuration detection

    Returns dict with:
    - repository_path: The input path
    - readme: Content of README file (truncated to 8000 chars)
    - readme_file: Name of the README file found
    - dependencies: List of dependency info from various package files
    - file_structure: List of {path, type} for top-level items
    - has_opencode: True if .opencode, .claude, CLAUDE.md, or AGENTS.md found
    - primary_language: Detected primary programming language
    - error: Error message if any
    """
    repo_path_obj = Path(repo_path)

    result = {
        "repository_path": str(repo_path_obj),
        "readme": None,
        "readme_file": None,
        "dependencies": [],
        "file_structure": [],
        "has_opencode": False,
        "primary_language": None,
        "error": None,
    }

    if not repo_path_obj.exists():
        result["error"] = f"Repository path does not exist: {repo_path_obj}"
        return result

    if not repo_path_obj.is_dir():
        result["error"] = f"Repository path is not a directory: {repo_path_obj}"
        return result

    # Language detection map
    language_map = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".go": "Go",
        ".rs": "Rust",
        ".java": "Java",
        ".rb": "Ruby",
        ".php": "PHP",
    }

    # Get README content
    readme_locations = [
        "README.md",
        "docs/README.md",
        "README.rst",
        "README.txt",
        "README",
        "docs/index.md",
    ]
    for readme_name in readme_locations:
        readme_path = repo_path_obj / readme_name
        if readme_path.exists():
            try:
                content = readme_path.read_text(encoding="utf-8")
                result["readme"] = content[:8000]  # Limit size
                result["readme_file"] = readme_name
                break
            except Exception:
                pass

    # Get file structure (top level)
    files = []
    ext_counts: dict[str, int] = {}

    try:
        for item in sorted(repo_path_obj.iterdir()):
            item_name = item.name

            # Handle hidden files/dirs
            if item_name.startswith("."):
                # Check for opencode/claude config
                if item_name in [".opencode", ".claude"]:
                    result["has_opencode"] = True
                    files.append({"path": item_name, "type": "tree"})
                continue

            item_type = "tree" if item.is_dir() else "blob"
            files.append({"path": item_name, "type": item_type})

            # Check for AGENTS.md or CLAUDE.md
            if item_name in ["CLAUDE.md", "AGENTS.md"]:
                result["has_opencode"] = True

            # Count extensions for language detection
            if item_type == "blob":
                ext = Path(item_name).suffix.lower()
                if ext in language_map:
                    ext_counts[ext] = ext_counts.get(ext, 0) + 1

        result["file_structure"] = files
    except Exception as e:
        result["error"] = f"Error reading file structure: {e}"
        return result

    # Detect primary language from top-level files
    # Also scan src/ if present for better detection
    src_dir = repo_path_obj / "src"
    if src_dir.exists() and src_dir.is_dir():
        try:
            for item in src_dir.iterdir():
                if item.is_file():
                    ext = item.suffix.lower()
                    if ext in language_map:
                        ext_counts[ext] = ext_counts.get(ext, 0) + 1
        except Exception:
            pass

    if ext_counts:
        primary_ext = max(ext_counts, key=lambda k: ext_counts[k])
        result["primary_language"] = language_map.get(primary_ext)

    # Get dependencies from various package files
    dep_files = [
        ("requirements.txt", "python"),
        ("environment.yml", "python/conda"),
        ("pyproject.toml", "python"),
        ("package.json", "javascript"),
        ("Cargo.toml", "rust"),
        ("go.mod", "go"),
    ]

    for dep_file, lang in dep_files:
        dep_path = repo_path_obj / dep_file
        if dep_path.exists():
            try:
                content = dep_path.read_text(encoding="utf-8")
                deps = parse_dependencies(content, dep_file)
                if deps:
                    filtered_deps = filter_dependencies(deps)
                    result["dependencies"].append(
                        {
                            "file": dep_file,
                            "language": lang,
                            "packages": filtered_deps,
                            "total_count": len(deps),
                            "filtered_count": len(filtered_deps),
                        }
                    )
            except Exception:
                pass

    return result


def get_repo_context(owner: str, repo: str) -> dict[str, Any]:
    """
    Get context information about a GitHub repository (via API).

    Returns:
    - README content
    - Dependencies (from requirements.txt, environment.yml, pyproject.toml, package.json)
    - Key files and structure
    """
    result = {
        "owner": owner,
        "repository": repo,
        "full_name": f"{owner}/{repo}",
        "readme": None,
        "dependencies": [],
        "file_structure": [],
        "has_opencode": False,
        "primary_language": None,
        "error": None,
    }

    # Get repository info
    success, output = run_gh_command(
        [
            "api",
            f"repos/{owner}/{repo}",
            "--jq",
            "{language: .language, description: .description, default_branch: .default_branch}",
        ]
    )
    if success:
        try:
            repo_info = json.loads(output)
            result["primary_language"] = repo_info.get("language")
            result["description"] = repo_info.get("description")
            result["default_branch"] = repo_info.get("default_branch", "main")
        except json.JSONDecodeError:
            pass

    # Get README content - check multiple locations
    readme_locations = [
        "README.md",
        "docs/README.md",
        "README.rst",
        "README.txt",
        "README",
        "docs/index.md",
    ]
    for readme_name in readme_locations:
        success, readme_content = run_gh_command(
            [
                "api",
                f"repos/{owner}/{repo}/contents/{readme_name}",
                "--jq",
                ".content",
            ]
        )
        if success and readme_content.strip() and not readme_content.startswith("{"):
            import base64

            try:
                decoded = base64.b64decode(readme_content.strip()).decode("utf-8")
                result["readme"] = decoded[:8000]  # Limit size
                result["readme_file"] = readme_name
                break
            except Exception:
                pass

    # Get file tree (top level + key directories)
    success, tree_output = run_gh_command(
        [
            "api",
            f"repos/{owner}/{repo}/git/trees/{result.get('default_branch', 'main')}",
            "--jq",
            ".tree[] | {path: .path, type: .type}",
        ]
    )
    if success:
        files = []
        for line in tree_output.strip().split("\n"):
            if line:
                try:
                    item = json.loads(line)
                    files.append(item)
                except json.JSONDecodeError:
                    pass
        result["file_structure"] = files

        # Check for .opencode or .claude directories
        for f in files:
            if f.get("path") in [".opencode", ".claude", "CLAUDE.md", "AGENTS.md"]:
                result["has_opencode"] = True
                break

    # Get dependencies based on language
    dep_files = [
        ("requirements.txt", "python"),
        ("environment.yml", "python/conda"),
        ("pyproject.toml", "python"),
        ("package.json", "javascript"),
        ("Cargo.toml", "rust"),
        ("go.mod", "go"),
    ]

    for dep_file, lang in dep_files:
        success, content = run_gh_command(
            [
                "api",
                f"repos/{owner}/{repo}/contents/{dep_file}",
                "--jq",
                ".content",
            ]
        )
        if success and content.strip():
            import base64

            try:
                decoded = base64.b64decode(content.strip()).decode("utf-8")
                deps = parse_dependencies(decoded, dep_file)
                if deps:
                    filtered_deps = filter_dependencies(deps)
                    result["dependencies"].append(
                        {
                            "file": dep_file,
                            "language": lang,
                            "packages": filtered_deps,
                            "total_count": len(deps),
                            "filtered_count": len(filtered_deps),
                        }
                    )
            except Exception:
                pass

    return result


# ============================================================================
# Dependency Parsing
# ============================================================================

# Packages to skip (dev tools, low-level infra)
SKIP_PACKAGES = {
    # Dev tools
    "pytest",
    "pytest-cov",
    "pytest-asyncio",
    "pytest-mock",
    "pytest-xdist",
    "black",
    "ruff",
    "mypy",
    "flake8",
    "isort",
    "pre-commit",
    "pylint",
    "coverage",
    "tox",
    "nox",
    "bandit",
    "safety",
    # Type stubs
    "types-requests",
    "types-pyyaml",
    "types-python-dateutil",
    # Low-level / common
    "pip",
    "setuptools",
    "wheel",
    "build",
    "twine",
    "typing-extensions",
    "typing_extensions",
    # Conda internals
    "_libgcc_mutex",
    "_openmp_mutex",
    "ca-certificates",
    "ld_impl_linux",
}

# Packages that are likely relevant for ML/AI projects
IMPORTANT_PACKAGES = {
    # ML/AI frameworks
    "crewai",
    "langchain",
    "langchain-core",
    "langchain-community",
    "openai",
    "anthropic",
    "transformers",
    "torch",
    "tensorflow",
    "scikit-learn",
    "xgboost",
    "lightgbm",
    "catboost",
    # Web frameworks
    "fastapi",
    "flask",
    "django",
    "streamlit",
    "gradio",
    "uvicorn",
    "gunicorn",
    "starlette",
    # Data
    "pandas",
    "numpy",
    "polars",
    "pydantic",
    "sqlalchemy",
    # AWS/Cloud
    "boto3",
    "botocore",
    "sagemaker",
    # Other important
    "httpx",
    "aiohttp",
    "requests",
    "websockets",
}


def filter_dependencies(packages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Filter dependencies to remove dev tools and highlight important packages.

    Returns filtered list with 'important' flag set on relevant packages.
    """
    filtered = []
    for pkg in packages:
        name = pkg.get("name", "").lower().replace("_", "-")

        # Skip dev tools and low-level packages
        if name in SKIP_PACKAGES or any(
            name.startswith(prefix) for prefix in ["types-", "pytest-"]
        ):
            continue

        # Mark important packages
        pkg_copy = pkg.copy()
        if name in IMPORTANT_PACKAGES:
            pkg_copy["important"] = True

        filtered.append(pkg_copy)

    # Sort: important packages first, then alphabetically
    filtered.sort(
        key=lambda x: (not x.get("important", False), x.get("name", "").lower())
    )

    return filtered


def parse_dependencies(content: str, filename: str) -> list[dict[str, Any]]:
    """Parse dependencies from various dependency file formats."""
    packages = []

    if filename == "requirements.txt":
        for line in content.split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("-"):
                # Parse package name (ignore version specifiers)
                match = re.match(r"([a-zA-Z0-9_-]+)", line)
                if match:
                    packages.append({"name": match.group(1), "raw": line})

    elif filename == "environment.yml":
        # Simple YAML parsing for conda environment
        in_deps = False
        for line in content.split("\n"):
            if "dependencies:" in line:
                in_deps = True
                continue
            if in_deps:
                if line.strip().startswith("-"):
                    dep = line.strip().lstrip("-").strip()
                    # Handle pip: section
                    if dep == "pip:":
                        continue
                    # Skip channel specs and version specs
                    match = re.match(r"([a-zA-Z0-9_-]+)", dep)
                    if match:
                        packages.append({"name": match.group(1), "raw": dep})
                elif line and not line.startswith(" ") and not line.startswith("\t"):
                    in_deps = False

    elif filename == "pyproject.toml":
        # Simple TOML parsing for dependencies
        in_deps = False
        for line in content.split("\n"):
            if "[project.dependencies]" in line or "[tool.poetry.dependencies]" in line:
                in_deps = True
                continue
            if in_deps:
                if line.startswith("["):
                    in_deps = False
                    continue
                if "=" in line or line.strip().startswith('"'):
                    # Extract package name
                    match = re.match(r'["\']?([a-zA-Z0-9_-]+)', line.strip())
                    if match:
                        packages.append({"name": match.group(1), "raw": line.strip()})

    elif filename == "package.json":
        try:
            data = json.loads(content)
            for dep_type in ["dependencies", "devDependencies"]:
                deps = data.get(dep_type, {})
                for name, version in deps.items():
                    packages.append(
                        {
                            "name": name,
                            "version": version,
                            "type": dep_type,
                        }
                    )
        except json.JSONDecodeError:
            pass

    return packages


# ============================================================================
# CLI Commands
# ============================================================================


def cmd_local_context(args: argparse.Namespace) -> None:
    """Command: local-context"""
    result = find_local_context(args.ticket_id)
    print(json.dumps(result, indent=2, default=str))
    sys.exit(1 if result.get("error") else 0)


def cmd_find_repos(args: argparse.Namespace) -> None:
    """Command: find-repos"""
    org = args.org or DEFAULT_ORG
    result = find_repos_for_ticket(args.ticket_id, org)
    print(json.dumps(result, indent=2, default=str))
    sys.exit(1 if result.get("error") else 0)


def cmd_repo_context(args: argparse.Namespace) -> None:
    """Command: repo-context"""
    result = get_repo_context(args.owner, args.repo)
    print(json.dumps(result, indent=2, default=str))
    sys.exit(1 if result.get("error") else 0)


def cmd_ensure_repo(args: argparse.Namespace) -> None:
    """Command: ensure-repo

    Ensure the repository for a ticket exists locally.
    If not present, clone it via gh CLI into project_management/<project>/repo/
    """
    org = args.org or DEFAULT_ORG
    result = ensure_repo_local(args.ticket_id, org)
    print(json.dumps(result, indent=2, default=str))
    sys.exit(1 if result.get("error") else 0)


def cmd_local_repo_context(args: argparse.Namespace) -> None:
    """Command: local-repo-context

    Get context information from a local repository clone.
    Reads README, dependencies, and file structure from the filesystem.
    """
    result = get_local_repo_context(args.repo_path)
    print(json.dumps(result, indent=2, default=str))
    sys.exit(1 if result.get("error") else 0)


# ============================================================================
# Main
# ============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ticket Improver - GitHub/Local repository operations for ticket enhancement"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # local-context
    p_local = subparsers.add_parser(
        "local-context", help="Find local context for a ticket"
    )
    p_local.add_argument("ticket_id", help="JIRA ticket ID (e.g., FML-247)")
    p_local.set_defaults(func=cmd_local_context)

    # find-repos
    p_repos = subparsers.add_parser("find-repos", help="Find GitHub repos for a ticket")
    p_repos.add_argument("ticket_id", help="JIRA ticket ID (e.g., FML-247)")
    p_repos.add_argument("--org", help=f"GitHub organization (default: {DEFAULT_ORG})")
    p_repos.set_defaults(func=cmd_find_repos)

    # repo-context
    p_ctx = subparsers.add_parser("repo-context", help="Get context from a GitHub repo")
    p_ctx.add_argument("owner", help="Repository owner/organization")
    p_ctx.add_argument("repo", help="Repository name")
    p_ctx.set_defaults(func=cmd_repo_context)

    # ensure-repo
    p_ensure = subparsers.add_parser(
        "ensure-repo",
        help="Ensure repository exists locally (clone if needed)",
    )
    p_ensure.add_argument("ticket_id", help="JIRA ticket ID (e.g., FML-247)")
    p_ensure.add_argument("--org", help=f"GitHub organization (default: {DEFAULT_ORG})")
    p_ensure.set_defaults(func=cmd_ensure_repo)

    # local-repo-context
    p_local_repo = subparsers.add_parser(
        "local-repo-context",
        help="Get context from a local repository clone",
    )
    p_local_repo.add_argument("repo_path", help="Path to local repository")
    p_local_repo.set_defaults(func=cmd_local_repo_context)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        print("\nNote: For JIRA/Confluence operations, use:")
        print("    python .opencode/tool/atlassian_client.py <command> [args...]")
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
