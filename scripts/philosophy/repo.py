"""
GitHub API layer for philosophy repository using gh CLI.

Provides remote-only access to chrislemke/philosophy repository
with auto-commit to main branch.
"""

import subprocess
import json
import base64
from typing import Optional


REPO = "chrislemke/philosophy"
BRANCH = "main"


def _run_gh(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run gh CLI command and return result."""
    cmd = ["gh"] + args
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def _api_get(endpoint: str) -> dict | list | None:
    """Make GET request to GitHub API."""
    result = _run_gh(["api", endpoint], check=False)
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)


def _api_request(method: str, endpoint: str, data: dict) -> dict | None:
    """Make API request with JSON body."""
    result = _run_gh([
        "api", endpoint,
        "-X", method,
        "-H", "Accept: application/vnd.github+json",
        "--input", "-"
    ], check=False)

    # Actually pass the data via stdin
    result = subprocess.run(
        ["gh", "api", endpoint, "-X", method, "-H", "Accept: application/vnd.github+json", "--input", "-"],
        input=json.dumps(data),
        capture_output=True,
        text=True,
        check=False
    )

    if result.returncode != 0:
        return None
    return json.loads(result.stdout) if result.stdout else {}


def get_file_content(path: str) -> str:
    """
    Get content of a file from the repository.

    Args:
        path: File path relative to repository root

    Returns:
        File content as string

    Raises:
        FileNotFoundError: If file does not exist
        RuntimeError: If API request fails
    """
    endpoint = f"repos/{REPO}/contents/{path}?ref={BRANCH}"
    data = _api_get(endpoint)

    if data is None:
        raise FileNotFoundError(f"File not found: {path}")

    if isinstance(data, list):
        raise IsADirectoryError(f"Path is a directory: {path}")

    if data.get("encoding") == "base64":
        return base64.b64decode(data["content"]).decode("utf-8")

    return data.get("content", "")


def list_directory(path: str = "") -> list[str]:
    """
    List contents of a directory in the repository.

    Args:
        path: Directory path relative to repository root (empty for root)

    Returns:
        List of file/directory names

    Raises:
        FileNotFoundError: If directory does not exist
    """
    endpoint = f"repos/{REPO}/contents/{path}?ref={BRANCH}"
    data = _api_get(endpoint)

    if data is None:
        raise FileNotFoundError(f"Directory not found: {path}")

    if not isinstance(data, list):
        raise NotADirectoryError(f"Path is not a directory: {path}")

    return [item["name"] for item in data]


def file_exists(path: str) -> bool:
    """
    Check if a file exists in the repository.

    Args:
        path: File path relative to repository root

    Returns:
        True if file exists, False otherwise
    """
    endpoint = f"repos/{REPO}/contents/{path}?ref={BRANCH}"
    data = _api_get(endpoint)
    return data is not None and not isinstance(data, list)


def get_file_sha(path: str) -> str:
    """
    Get SHA of a file (required for updates/deletes).

    Args:
        path: File path relative to repository root

    Returns:
        File SHA as string

    Raises:
        FileNotFoundError: If file does not exist
    """
    endpoint = f"repos/{REPO}/contents/{path}?ref={BRANCH}"
    data = _api_get(endpoint)

    if data is None:
        raise FileNotFoundError(f"File not found: {path}")

    if isinstance(data, list):
        raise IsADirectoryError(f"Path is a directory: {path}")

    return data["sha"]


def create_file(path: str, content: str, commit_message: str) -> bool:
    """
    Create a new file in the repository.

    Args:
        path: File path relative to repository root
        content: File content as string
        commit_message: Commit message

    Returns:
        True if successful

    Raises:
        FileExistsError: If file already exists
        RuntimeError: If API request fails
    """
    if file_exists(path):
        raise FileExistsError(f"File already exists: {path}")

    endpoint = f"repos/{REPO}/contents/{path}"
    encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")

    data = {
        "message": commit_message,
        "content": encoded_content,
        "branch": BRANCH
    }

    result = subprocess.run(
        ["gh", "api", endpoint, "-X", "PUT", "-H", "Accept: application/vnd.github+json", "--input", "-"],
        input=json.dumps(data),
        capture_output=True,
        text=True,
        check=False
    )

    if result.returncode != 0:
        raise RuntimeError(f"Failed to create file: {result.stderr}")

    return True


def update_file(path: str, content: str, commit_message: str) -> bool:
    """
    Update an existing file in the repository.

    Args:
        path: File path relative to repository root
        content: New file content as string
        commit_message: Commit message

    Returns:
        True if successful

    Raises:
        FileNotFoundError: If file does not exist
        RuntimeError: If API request fails
    """
    sha = get_file_sha(path)  # Raises FileNotFoundError if not exists

    endpoint = f"repos/{REPO}/contents/{path}"
    encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")

    data = {
        "message": commit_message,
        "content": encoded_content,
        "sha": sha,
        "branch": BRANCH
    }

    result = subprocess.run(
        ["gh", "api", endpoint, "-X", "PUT", "-H", "Accept: application/vnd.github+json", "--input", "-"],
        input=json.dumps(data),
        capture_output=True,
        text=True,
        check=False
    )

    if result.returncode != 0:
        raise RuntimeError(f"Failed to update file: {result.stderr}")

    return True


def delete_file(path: str, commit_message: str) -> bool:
    """
    Delete a file from the repository.

    Args:
        path: File path relative to repository root
        commit_message: Commit message

    Returns:
        True if successful

    Raises:
        FileNotFoundError: If file does not exist
        RuntimeError: If API request fails
    """
    sha = get_file_sha(path)  # Raises FileNotFoundError if not exists

    endpoint = f"repos/{REPO}/contents/{path}"

    data = {
        "message": commit_message,
        "sha": sha,
        "branch": BRANCH
    }

    result = subprocess.run(
        ["gh", "api", endpoint, "-X", "DELETE", "-H", "Accept: application/vnd.github+json", "--input", "-"],
        input=json.dumps(data),
        capture_output=True,
        text=True,
        check=False
    )

    if result.returncode != 0:
        raise RuntimeError(f"Failed to delete file: {result.stderr}")

    return True
