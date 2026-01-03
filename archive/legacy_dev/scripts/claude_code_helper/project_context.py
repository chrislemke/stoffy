#!/usr/bin/env python3
"""Project Context Extractor for Claude Code Agent.

Extracts all project-related context in one call, replacing multiple file reads.
Provides project mapping, test configuration, recent progress, and dependencies.

This script gathers comprehensive context about a repository to help the Claude
Code agent understand the project structure without performing multiple file
reads. It automatically maps repositories to their corresponding project
folders in lead_stuff/project_management/.

Usage:
    python scripts/claude_code_helper/project_context.py <repo_path>
    python scripts/claude_code_helper/project_context.py /path/to/repo
    python scripts/claude_code_helper/project_context.py .  # Current directory

Output:
    JSON object containing:
        - success: bool indicating if extraction succeeded
        - repo_path: absolute path to the repository
        - project_mapping: matched project folder in lead_stuff
        - test_config: pytest configuration and test directories
        - recent_progress: last 5 progress entries from progress_notes.md
        - related_tickets: ticket IDs found in recent git commits
        - languages: detected programming languages
        - has_opencode_config: whether repo has .opencode or AGENTS.md
        - primary_dependencies: key ML/AI/web framework dependencies

Token Savings:
    ~500-1000 tokens per invocation (replaces multiple file reads).

Example:
    >>> import subprocess
    >>> result = subprocess.run(
    ...     ["python", "scripts/claude_code_helper/project_context.py", "/path/to/repo"],
    ...     capture_output=True, text=True
    ... )
    >>> import json
    >>> context = json.loads(result.stdout)
    >>> context["project_mapping"]["matched_project"]
    'invia-flights-conversational-ai-bot'
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


def find_lead_stuff_root() -> Path | None:
    """Find the lead_stuff repository root by looking for marker files.

    Walks up the directory tree from the script location searching for
    characteristic files that indicate the lead_stuff repository root.

    Returns:
        Path to the lead_stuff root directory if found, None otherwise.

    Note:
        Searches for agents_index.yaml or opencode.jsonc as markers.
        Limited to 10 levels up to avoid infinite loops.
    """
    # Start from script location and walk up
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "agents_index.yaml").exists():
            return current
        if (current / "opencode.jsonc").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def resolve_repo_path(repo_path_arg: str) -> Path:
    """Resolve a repository path argument to an absolute path.

    Attempts to resolve the path in the following order:
    1. If absolute, return as-is (resolved)
    2. If relative and exists from CWD, use that
    3. If relative and exists from lead_stuff root, use that
    4. Return the resolved path and let caller handle errors

    Args:
        repo_path_arg: Path to the repository. Can be:
            - An absolute path (e.g., '/Users/dev/myrepo')
            - A relative path from CWD (e.g., '../myrepo')
            - A relative path from lead_stuff root (e.g., 'project_management/foo')
            - A path with ~ for home directory (e.g., '~/Developer/myrepo')

    Returns:
        Resolved absolute Path to the repository directory.

    Example:
        >>> resolve_repo_path("/absolute/path")
        PosixPath('/absolute/path')
        >>> resolve_repo_path(".")  # Current directory
        PosixPath('/current/working/directory')
    """
    path = Path(repo_path_arg).expanduser()
    if path.is_absolute():
        return path.resolve()
    # Try relative to current working directory
    cwd_relative = Path.cwd() / path
    if cwd_relative.exists():
        return cwd_relative.resolve()
    # Try relative to lead_stuff root
    lead_stuff = find_lead_stuff_root()
    if lead_stuff:
        lead_relative = lead_stuff / path
        if lead_relative.exists():
            return lead_relative.resolve()
    # Return as-is and let caller handle errors
    return path.resolve()


def is_git_repo(path: Path) -> bool:
    """Check if a path is inside a git repository.

    Uses `git rev-parse --is-inside-work-tree` to determine if the
    given path is within a git working tree.

    Args:
        path: Directory path to check. Must be an existing directory.

    Returns:
        True if the path is inside a git repository, False otherwise.
        Also returns False if git is not installed or times out.

    Note:
        Times out after 5 seconds to prevent hanging on network filesystems.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0 and result.stdout.strip() == "true"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def get_repo_name(path: Path) -> str | None:
    """Get the repository name from git remote URL or folder name.

    Attempts to extract the repository name from the git origin remote URL.
    Falls back to using the directory name if git is unavailable or no
    remote is configured.

    Args:
        path: Path to the repository directory.

    Returns:
        Repository name extracted from the remote URL (without .git suffix),
        or the directory name as fallback. Returns None only if path.name
        is empty (which shouldn't happen for valid paths).

    Example:
        For a repo with origin 'git@github.com:org/my-repo.git':
        >>> get_repo_name(Path("/path/to/my-repo"))
        'my-repo'

    Note:
        Handles both SSH (git@) and HTTPS remote URL formats.
    """
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            # Extract repo name from URL
            # Handles: git@github.com:org/repo.git or https://github.com/org/repo.git
            match = re.search(r"/([^/]+?)(?:\.git)?$", url)
            if match:
                return match.group(1)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    # Fallback to folder name
    return path.name


def find_project_mapping(repo_path: Path, lead_stuff: Path) -> dict[str, str | None]:
    """Find the project_management folder that corresponds to a repository.

    Searches through project_management/ subdirectories looking for project.md
    files that reference the given repository by name.

    Args:
        repo_path: Path to the repository to find a mapping for.
        lead_stuff: Path to the lead_stuff repository root.

    Returns:
        Dictionary containing:
            - matched_project: Name of the matched project folder (e.g.,
                'invia-flights-conversational-ai-bot'), or None if not found.
            - project_folder: Relative path to the project folder from lead_stuff
                (e.g., 'project_management/invia-flights-conversational-ai-bot'),
                or None if not found.
            - match_method: How the match was found. One of:
                - 'repo_name_in_project_md': Found repo name in project.md
                - 'folder_name_match': Project folder name matches repo name
                - None: No match found

    Example:
        >>> mapping = find_project_mapping(
        ...     Path("/repos/invia-flights-conversational-ai-bot"),
        ...     Path("/Users/dev/lead_stuff")
        ... )
        >>> mapping["matched_project"]
        'invia-flights-conversational-ai-bot'
    """
    result: dict[str, str | None] = {
        "matched_project": None,
        "project_folder": None,
        "match_method": None,
    }

    repo_name = get_repo_name(repo_path)
    if not repo_name:
        return result

    projects_dir = lead_stuff / "project_management"
    if not projects_dir.exists():
        return result

    # Search project.md files for repo name matches
    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir() or project_dir.name.startswith("."):
            continue

        project_file = project_dir / "project.md"
        if not project_file.exists():
            continue

        try:
            content = project_file.read_text(encoding="utf-8")

            # Check for repository field
            repo_patterns = [
                rf"\*\*Repository\*\*:\s*`{re.escape(repo_name)}`",
                rf"[Rr]epository:\s*{re.escape(repo_name)}\b",
                rf"`{re.escape(repo_name)}`",
            ]

            for pattern in repo_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    result["matched_project"] = project_dir.name
                    result["project_folder"] = str(project_dir.relative_to(lead_stuff))
                    result["match_method"] = "repo_name_in_project_md"
                    return result

            # Also check if project folder name matches repo name
            if project_dir.name.lower() == repo_name.lower():
                result["matched_project"] = project_dir.name
                result["project_folder"] = str(project_dir.relative_to(lead_stuff))
                result["match_method"] = "folder_name_match"
                return result

        except Exception:
            continue

    return result


def get_test_config(repo_path: Path) -> dict[str, Any]:
    """Extract pytest test configuration from a repository.

    Searches for test directories and parses configuration files to
    determine how tests should be run.

    Args:
        repo_path: Path to the repository to analyze.

    Returns:
        Dictionary containing:
            - test_command: Base command to run tests (always 'pytest').
            - test_dir: Path to the test directory relative to repo root
                (e.g., 'tests', 'test'), or None if not found.
            - unit_test_marker: Name of the marker for unit tests if configured
                (e.g., 'unit'), or None.
            - has_pytest: True if pytest configuration was detected.

    Note:
        Checks the following locations for pytest configuration:
        - pyproject.toml ([tool.pytest] section)
        - pytest.ini
        - setup.cfg ([tool:pytest] section)
    """
    config: dict[str, Any] = {
        "test_command": "pytest",
        "test_dir": None,
        "unit_test_marker": None,
        "has_pytest": False,
    }

    # Check for test directories
    test_dirs = ["tests", "test", "tests/unit_tests"]
    for test_dir in test_dirs:
        if (repo_path / test_dir).is_dir():
            config["test_dir"] = test_dir
            config["has_pytest"] = True
            break

    # Check pyproject.toml for pytest config
    pyproject = repo_path / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text(encoding="utf-8")

            # Look for pytest markers
            if "markers" in content and "unit" in content:
                config["unit_test_marker"] = "unit"

            # Look for pytest ini options
            if "[tool.pytest" in content:
                config["has_pytest"] = True

            # Look for testpaths
            testpaths_match = re.search(r"testpaths\s*=\s*\[([^\]]+)\]", content)
            if testpaths_match:
                paths = testpaths_match.group(1)
                first_path = re.search(r'"([^"]+)"', paths)
                if first_path:
                    config["test_dir"] = first_path.group(1)

        except Exception:
            pass

    # Check pytest.ini
    pytest_ini = repo_path / "pytest.ini"
    if pytest_ini.exists():
        config["has_pytest"] = True
        try:
            content = pytest_ini.read_text(encoding="utf-8")
            if "markers" in content and "unit" in content:
                config["unit_test_marker"] = "unit"
        except Exception:
            pass

    # Check setup.cfg
    setup_cfg = repo_path / "setup.cfg"
    if setup_cfg.exists():
        try:
            content = setup_cfg.read_text(encoding="utf-8")
            if "[tool:pytest]" in content:
                config["has_pytest"] = True
                if "markers" in content and "unit" in content:
                    config["unit_test_marker"] = "unit"
        except Exception:
            pass

    return config


def get_recent_progress(project_folder: Path | None) -> list[dict[str, Any]]:
    """Get recent progress entries from a project's progress_notes.md file.

    Parses the progress_notes.md file looking for dated section headers
    and extracts the most recent entries.

    Args:
        project_folder: Path to the project folder in lead_stuff, or None.
            If None, returns an empty list.

    Returns:
        List of up to 5 most recent progress entries, each containing:
            - date: ISO date string (e.g., '2025-01-15').
            - title: First line of the section after the date.
            - session_link: Path to linked Claude Code session file
                (e.g., 'sessions/claude_code/session-ses_4f5e.md'), or None.

    Example:
        >>> progress = get_recent_progress(Path("/lead_stuff/project_management/myproj"))
        >>> progress[0]
        {'date': '2025-01-15', 'title': 'Implement feature X', 'session_link': None}
    """
    if not project_folder:
        return []

    progress_file = project_folder / "progress_notes.md"
    if not progress_file.exists():
        return []

    entries: list[dict[str, Any]] = []
    try:
        content = progress_file.read_text(encoding="utf-8")

        # Parse ## YYYY-MM-DD - Title sections
        pattern = r"##\s+(\d{4}-\d{2}-\d{2})\s*[-–]\s*(.+?)(?=\n##|\n---|\Z)"
        matches = re.findall(pattern, content, re.DOTALL)

        for date, section in matches[:5]:  # Last 5 entries
            # Extract session link if present
            session_match = re.search(r"\[\[sessions/claude_code/([^\]]+)\]\]", section)
            entries.append(
                {
                    "date": date.strip(),
                    "title": section.split("\n")[0].strip(),
                    "session_link": f"sessions/claude_code/{session_match.group(1)}"
                    if session_match
                    else None,
                }
            )

    except Exception:
        pass

    return entries


def get_related_tickets(repo_path: Path) -> list[str]:
    """Find Jira ticket IDs mentioned in recent git commits.

    Scans the last 20 git commit messages for ticket ID patterns matching
    fluege.de's Jira project prefixes.

    Args:
        repo_path: Path to the git repository to analyze.

    Returns:
        Sorted list of up to 10 unique ticket IDs found in commit messages.
        Each ID is uppercase (e.g., 'FML-123', 'FLUG-456').

    Note:
        Recognized ticket prefixes: DS, FML, FLUG, FLIGHTS, FIOS, FPRO, BI, HD.
        Returns empty list if git is unavailable or path is not a git repo.
    """
    tickets: set[str] = set()
    ticket_pattern = re.compile(
        r"\b(DS|FML|FLUG|FLIGHTS|FIOS|FPRO|BI|HD)-(\d+)\b", re.IGNORECASE
    )

    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-n", "20"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            for match in ticket_pattern.findall(result.stdout):
                tickets.add(f"{match[0].upper()}-{match[1]}")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return sorted(tickets)[:10]


def detect_languages(repo_path: Path) -> list[str]:
    """Detect primary programming languages in a repository.

    Counts files by extension in the repository root and src/ directory
    to determine the primary languages used.

    Args:
        repo_path: Path to the repository to analyze.

    Returns:
        List of up to 3 language names, sorted by file count (most common first).
        Possible values: 'python', 'javascript', 'typescript', 'go', 'rust',
        'java', 'ruby', 'php'.

    Example:
        >>> detect_languages(Path("/path/to/python-project"))
        ['python']

    Note:
        Only checks root directory and src/ subdirectory, not recursively.
        This provides a quick heuristic without full directory traversal.
    """
    extensions = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".rb": "ruby",
        ".php": "php",
    }

    counts: dict[str, int] = {}

    # Check src/ directory and root level
    dirs_to_check = [repo_path, repo_path / "src"]

    for check_dir in dirs_to_check:
        if not check_dir.exists():
            continue
        try:
            for item in check_dir.iterdir():
                if item.is_file():
                    ext = item.suffix.lower()
                    if ext in extensions:
                        lang = extensions[ext]
                        counts[lang] = counts.get(lang, 0) + 1
        except Exception:
            pass

    # Sort by count and return top languages
    sorted_langs = sorted(counts.items(), key=lambda x: -x[1])
    return [lang for lang, _ in sorted_langs[:3]]


def has_opencode_config(repo_path: Path) -> bool:
    """Check if a repository has opencode or Claude Code configuration.

    Looks for configuration files/directories that indicate the repo
    is set up for use with opencode or Claude Code agents.

    Args:
        repo_path: Path to the repository to check.

    Returns:
        True if any configuration indicator is found, False otherwise.

    Note:
        Checked indicators: .opencode/, .claude/, CLAUDE.md, AGENTS.md
    """
    config_indicators = [
        ".opencode",
        ".claude",
        "CLAUDE.md",
        "AGENTS.md",
    ]

    for indicator in config_indicators:
        if (repo_path / indicator).exists():
            return True
    return False


def get_primary_dependencies(repo_path: Path) -> list[str]:
    """Extract primary ML/AI and web framework dependencies from a repository.

    Searches dependency files for a curated list of important packages
    commonly used in ML/AI and web development projects.

    Args:
        repo_path: Path to the repository to analyze.

    Returns:
        Sorted list of important package names found in dependency files.
        Only returns packages from a curated list of ~25 key packages.

    Note:
        Checks: pyproject.toml, requirements.txt, environment.yml.
        Key packages include: crewai, langchain, openai, anthropic, fastapi,
        pandas, numpy, boto3, sagemaker, and others.
    """
    important_packages = {
        # ML/AI
        "crewai",
        "langchain",
        "langchain-core",
        "openai",
        "anthropic",
        "transformers",
        "torch",
        "tensorflow",
        "scikit-learn",
        # Web
        "fastapi",
        "flask",
        "django",
        "streamlit",
        "uvicorn",
        "starlette",
        # Data
        "pandas",
        "numpy",
        "polars",
        "pydantic",
        "sqlalchemy",
        # AWS
        "boto3",
        "sagemaker",
        # Other
        "httpx",
        "aiohttp",
        "requests",
    }

    found_deps: set[str] = set()

    # Check pyproject.toml
    pyproject = repo_path / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text(encoding="utf-8").lower()
            for pkg in important_packages:
                if pkg.lower() in content:
                    found_deps.add(pkg)
        except Exception:
            pass

    # Check requirements.txt
    requirements = repo_path / "requirements.txt"
    if requirements.exists():
        try:
            content = requirements.read_text(encoding="utf-8").lower()
            for pkg in important_packages:
                if pkg.lower() in content:
                    found_deps.add(pkg)
        except Exception:
            pass

    # Check environment.yml
    env_yml = repo_path / "environment.yml"
    if env_yml.exists():
        try:
            content = env_yml.read_text(encoding="utf-8").lower()
            for pkg in important_packages:
                if pkg.lower() in content:
                    found_deps.add(pkg)
        except Exception:
            pass

    return sorted(found_deps)


def get_project_context(repo_path_arg: str) -> dict[str, Any]:
    """Gather all project context from a repository in a single call.

    This is the main entry point for the project context extractor. It
    collects comprehensive information about a repository including its
    mapping to lead_stuff projects, test configuration, dependencies,
    and recent development history.

    Args:
        repo_path_arg: Path to the repository. Can be absolute, relative to
            CWD, or relative to lead_stuff root. Supports ~ expansion.

    Returns:
        Dictionary containing all extracted context:
            - success: bool, True if extraction completed without errors.
            - repo_path: str, resolved absolute path to the repository.
            - project_mapping: dict with matched_project, project_folder,
                and match_method keys.
            - test_config: dict with test_command, test_dir, unit_test_marker,
                and has_pytest keys.
            - recent_progress: list of recent progress entries (up to 5).
            - related_tickets: list of Jira ticket IDs from git history.
            - languages: list of detected programming languages.
            - has_opencode_config: bool, True if opencode/Claude config exists.
            - primary_dependencies: list of key package dependencies.
            - error: str, present only if success is False.
            - warning: str, present if non-fatal issues occurred.

    Raises:
        This function does not raise exceptions; errors are returned in the
        result dictionary with success=False.

    Example:
        >>> context = get_project_context("/path/to/repo")
        >>> if context["success"]:
        ...     print(f"Project: {context['project_mapping']['matched_project']}")
        ...     print(f"Languages: {context['languages']}")
    """
    repo_path = resolve_repo_path(repo_path_arg)
    lead_stuff = find_lead_stuff_root()

    result: dict[str, Any] = {
        "success": True,
        "repo_path": str(repo_path),
        "project_mapping": {
            "matched_project": None,
            "project_folder": None,
            "match_method": None,
        },
        "test_config": {
            "test_command": "pytest",
            "test_dir": None,
            "unit_test_marker": None,
            "has_pytest": False,
        },
        "recent_progress": [],
        "related_tickets": [],
        "languages": [],
        "has_opencode_config": False,
        "primary_dependencies": [],
    }

    # Validate repo path
    if not repo_path.exists():
        result["success"] = False
        result["error"] = f"Repository path does not exist: {repo_path}"
        return result

    if not repo_path.is_dir():
        result["success"] = False
        result["error"] = f"Repository path is not a directory: {repo_path}"
        return result

    # Check if it's a git repo
    if not is_git_repo(repo_path):
        result["warning"] = "Not a git repository - some features may be limited"

    # Find project mapping
    if lead_stuff:
        result["project_mapping"] = find_project_mapping(repo_path, lead_stuff)

        # Get recent progress if project found
        if result["project_mapping"]["project_folder"]:
            project_folder = lead_stuff / result["project_mapping"]["project_folder"]
            result["recent_progress"] = get_recent_progress(project_folder)

    # Get test configuration
    result["test_config"] = get_test_config(repo_path)

    # Get related tickets from git history
    result["related_tickets"] = get_related_tickets(repo_path)

    # Detect languages
    result["languages"] = detect_languages(repo_path)

    # Check for opencode config
    result["has_opencode_config"] = has_opencode_config(repo_path)

    # Get primary dependencies
    result["primary_dependencies"] = get_primary_dependencies(repo_path)

    return result


def main() -> int:
    """Main entry point for the project context extractor CLI.

    Parses command line arguments, extracts project context, and prints
    the result as formatted JSON to stdout.

    Returns:
        Exit code: 0 if successful, 1 if an error occurred.
    """
    parser = argparse.ArgumentParser(
        description="Extract project context for claude-code agent workflow"
    )
    parser.add_argument(
        "repo_path",
        help="Path to the repository (absolute or relative to lead_stuff)",
    )

    args = parser.parse_args()

    result = get_project_context(args.repo_path)
    print(json.dumps(result, indent=2))

    return 0 if result.get("success", False) else 1


if __name__ == "__main__":
    sys.exit(main())
