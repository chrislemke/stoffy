#!/usr/bin/env python3
"""
Git Commit Helper

A utility script for smart commits that provides functions to:
- Get uncommitted changes (staged and unstaged)
- Get the full diff for LLM analysis
- Stage all changes
- Execute commits with conventional commit format

Usage:
    # Get status of uncommitted changes
    python scripts/git_commit_helper.py status

    # Get full diff for analysis
    python scripts/git_commit_helper.py diff

    # Stage all changes and commit
    python scripts/git_commit_helper.py commit --message "feat: add new feature" --description "Detailed description"

    # Full workflow: stage all + commit
    python scripts/git_commit_helper.py commit --message "fix: resolve bug" --description "Fixed the issue" --stage-all

Prerequisites:
    - Git must be installed and available in PATH
    - Must be run from within a git repository
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

# Files/patterns to exclude from commit message analysis.
# These are infrastructure files that should be committed but not mentioned
# in commit messages or descriptions.
EXCLUDED_PATTERNS: list[str] = [
    ".opencode/",  # opencode configuration directory
    "scripts/",  # Automation scripts directory
    "AGENTS.md",  # Agent instruction files (any directory)
    "conda-lock.yml",  # Environment lock file
    "environment.yml",  # Environment definition
    "opencode.jsonc",  # opencode config
]


def is_infrastructure_file(filepath: str) -> bool:
    """
    Check if a file is an infrastructure file that should be excluded
    from commit message analysis.

    Infrastructure files are still committed, but they should not influence
    the commit message or description.

    Args:
        filepath: Path to the file (relative to repo root)

    Returns:
        True if the file is an infrastructure file, False otherwise
    """
    for pattern in EXCLUDED_PATTERNS:
        if pattern.endswith("/"):
            # Directory pattern - check if file is inside this directory
            if filepath.startswith(pattern):
                return True
        else:
            # File pattern - check exact match or filename match (any directory)
            if filepath == pattern or filepath.endswith("/" + pattern):
                return True
    return False


def partition_files(files: list[str]) -> tuple[list[str], list[str]]:
    """
    Partition a list of files into content files and infrastructure files.

    Args:
        files: List of file paths

    Returns:
        Tuple of (content_files, infrastructure_files)
    """
    content_files = []
    infrastructure_files = []
    for f in files:
        if is_infrastructure_file(f):
            infrastructure_files.append(f)
        else:
            content_files.append(f)
    return content_files, infrastructure_files


@dataclass
class GitStatus:
    """Represents the current git status."""

    # Content files (should influence commit message)
    staged_files: list[str]
    unstaged_files: list[str]
    untracked_files: list[str]
    # Infrastructure files (committed but excluded from commit message analysis)
    infrastructure_files: list[str] = field(default_factory=list)
    has_changes: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON output."""
        content_total = (
            len(self.staged_files)
            + len(self.unstaged_files)
            + len(self.untracked_files)
        )
        return {
            "staged_files": self.staged_files,
            "unstaged_files": self.unstaged_files,
            "untracked_files": self.untracked_files,
            "infrastructure_files": self.infrastructure_files,
            "has_changes": self.has_changes,
            "summary": {
                "staged_count": len(self.staged_files),
                "unstaged_count": len(self.unstaged_files),
                "untracked_count": len(self.untracked_files),
                "content_total": content_total,
                "infrastructure_count": len(self.infrastructure_files),
                "total_changes": content_total + len(self.infrastructure_files),
            },
        }


def run_git_command(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """
    Execute a git command.

    Args:
        args: Git command arguments (without 'git' prefix)
        check: Whether to raise on non-zero exit code

    Returns:
        CompletedProcess with stdout and stderr

    Raises:
        subprocess.CalledProcessError: If check=True and command fails
    """
    cmd = ["git"] + args
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=check,
    )


def is_git_repository() -> bool:
    """Check if current directory is inside a git repository."""
    result = run_git_command(["rev-parse", "--is-inside-work-tree"], check=False)
    return result.returncode == 0 and result.stdout.strip() == "true"


def get_repository_root() -> Path | None:
    """Get the root directory of the git repository."""
    result = run_git_command(["rev-parse", "--show-toplevel"], check=False)
    if result.returncode == 0:
        return Path(result.stdout.strip())
    return None


def get_uncommitted_changes() -> GitStatus:
    """
    Get all uncommitted changes (staged, unstaged, and untracked).

    Files are partitioned into content files (which should influence the commit
    message) and infrastructure files (which are committed but excluded from
    commit message analysis).

    Returns:
        GitStatus object with categorized file lists
    """
    # Get staged files
    staged_result = run_git_command(
        ["diff", "--cached", "--name-only"],
        check=False,
    )
    all_staged = [f for f in staged_result.stdout.strip().split("\n") if f]

    # Get unstaged changes (modified but not staged)
    unstaged_result = run_git_command(
        ["diff", "--name-only"],
        check=False,
    )
    all_unstaged = [f for f in unstaged_result.stdout.strip().split("\n") if f]

    # Get untracked files
    untracked_result = run_git_command(
        ["ls-files", "--others", "--exclude-standard"],
        check=False,
    )
    all_untracked = [f for f in untracked_result.stdout.strip().split("\n") if f]

    # Partition files into content and infrastructure
    staged_files, staged_infra = partition_files(all_staged)
    unstaged_files, unstaged_infra = partition_files(all_unstaged)
    untracked_files, untracked_infra = partition_files(all_untracked)

    # Combine all infrastructure files (deduplicated, preserving order)
    infrastructure_files = []
    seen = set()
    for f in staged_infra + unstaged_infra + untracked_infra:
        if f not in seen:
            seen.add(f)
            infrastructure_files.append(f)

    has_changes = bool(
        staged_files or unstaged_files or untracked_files or infrastructure_files
    )

    return GitStatus(
        staged_files=staged_files,
        unstaged_files=unstaged_files,
        untracked_files=untracked_files,
        infrastructure_files=infrastructure_files,
        has_changes=has_changes,
    )


def filter_diff_by_files(
    diff_output: str, exclude_infra: bool = True
) -> tuple[str, list[str]]:
    """
    Filter a git diff output to exclude infrastructure files.

    Parses the diff and removes sections for files that match infrastructure patterns.

    Args:
        diff_output: Raw git diff output
        exclude_infra: Whether to exclude infrastructure files

    Returns:
        Tuple of (filtered_diff, list_of_excluded_files)
    """
    if not exclude_infra or not diff_output.strip():
        return diff_output, []

    filtered_parts = []
    excluded_files = []
    current_file = None
    current_section = []
    in_excluded_section = False

    for line in diff_output.split("\n"):
        # Detect start of a new file diff
        if line.startswith("diff --git "):
            # Save previous section if not excluded
            if current_section and not in_excluded_section:
                filtered_parts.extend(current_section)

            # Parse file path from "diff --git a/path b/path"
            parts = line.split(" ")
            if len(parts) >= 4:
                # Extract path from "b/path"
                current_file = parts[3][2:] if parts[3].startswith("b/") else parts[3]
            else:
                current_file = None

            # Check if this file should be excluded
            in_excluded_section = current_file and is_infrastructure_file(current_file)
            if in_excluded_section and current_file:
                excluded_files.append(current_file)

            current_section = [line + "\n"]
        else:
            current_section.append(line + "\n")

    # Don't forget the last section
    if current_section and not in_excluded_section:
        filtered_parts.extend(current_section)

    return "".join(filtered_parts).rstrip("\n"), excluded_files


def get_full_diff() -> str:
    """
    Get the combined diff of all changes (staged + unstaged).

    For untracked files, shows the full file content as a diff.
    Infrastructure files are excluded from the diff output but listed
    in a summary section at the end.

    Returns:
        Combined diff string for LLM analysis
    """
    diff_parts = []
    all_excluded_files = []

    # Get staged diff and filter
    staged_result = run_git_command(["diff", "--cached"], check=False)
    if staged_result.stdout.strip():
        filtered_staged, excluded = filter_diff_by_files(staged_result.stdout)
        all_excluded_files.extend(excluded)
        if filtered_staged.strip():
            diff_parts.append("=== STAGED CHANGES ===\n")
            diff_parts.append(filtered_staged)
            diff_parts.append("\n")

    # Get unstaged diff and filter
    unstaged_result = run_git_command(["diff"], check=False)
    if unstaged_result.stdout.strip():
        filtered_unstaged, excluded = filter_diff_by_files(unstaged_result.stdout)
        all_excluded_files.extend(excluded)
        if filtered_unstaged.strip():
            diff_parts.append("\n=== UNSTAGED CHANGES ===\n")
            diff_parts.append(filtered_unstaged)
            diff_parts.append("\n")

    # Get untracked files content (show as new files, excluding infrastructure)
    untracked_result = run_git_command(
        ["ls-files", "--others", "--exclude-standard"],
        check=False,
    )
    all_untracked = [f for f in untracked_result.stdout.strip().split("\n") if f]

    # Partition untracked files
    content_untracked = []
    for filepath in all_untracked:
        if is_infrastructure_file(filepath):
            all_excluded_files.append(filepath)
        else:
            content_untracked.append(filepath)

    if content_untracked:
        diff_parts.append("\n=== UNTRACKED (NEW) FILES ===\n")
        for filepath in content_untracked:
            try:
                path = Path(filepath)
                if path.exists() and path.is_file():
                    # Check if it's a binary file
                    try:
                        content = path.read_text(encoding="utf-8")
                        # Limit content size for very large files
                        if len(content) > 10000:
                            content = (
                                content[:10000] + "\n... (truncated, file too large)"
                            )
                        diff_parts.append(f"\n--- /dev/null\n+++ b/{filepath}\n")
                        for line in content.split("\n"):
                            diff_parts.append(f"+{line}\n")
                    except UnicodeDecodeError:
                        diff_parts.append(f"\n[Binary file: {filepath}]\n")
            except Exception as e:
                diff_parts.append(f"\n[Could not read {filepath}: {e}]\n")

    # Add summary of excluded infrastructure files
    if all_excluded_files:
        # Deduplicate while preserving order
        seen = set()
        unique_excluded = []
        for f in all_excluded_files:
            if f not in seen:
                seen.add(f)
                unique_excluded.append(f)

        diff_parts.append("\n=== INFRASTRUCTURE FILES (excluded from analysis) ===\n")
        diff_parts.append(
            f"The following {len(unique_excluded)} infrastructure file(s) were also changed:\n"
        )
        for f in unique_excluded:
            diff_parts.append(f"  - {f}\n")
        diff_parts.append(
            "\nThese files will be included in the commit but should NOT influence\n"
            "the commit message or description.\n"
        )

    return "".join(diff_parts)


def stage_all_changes() -> bool:
    """
    Stage all changes (modified, deleted, and untracked files).

    Returns:
        True if successful, False otherwise
    """
    result = run_git_command(["add", "--all"], check=False)
    return result.returncode == 0


def commit_changes(message: str, description: str | None = None) -> tuple[bool, str]:
    """
    Create a git commit with the given message and optional description.

    Args:
        message: Commit subject line (should follow conventional commits)
        description: Optional commit body/description

    Returns:
        Tuple of (success: bool, output: str)
    """
    # Build commit message
    if description:
        full_message = f"{message}\n\n{description}"
    else:
        full_message = message

    result = run_git_command(["commit", "-m", full_message], check=False)

    if result.returncode == 0:
        return True, result.stdout.strip()
    else:
        return False, result.stderr.strip() or result.stdout.strip()


def validate_conventional_commit(message: str) -> tuple[bool, str | None]:
    """
    Validate that a commit message follows conventional commits format.

    Conventional Commits specification:
    - Format: <type>[optional scope]: <description>
    - Types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert
    - Subject line max 50 chars (soft limit), 72 chars (hard limit)
    - No period at end of subject

    Args:
        message: The commit subject line to validate

    Returns:
        Tuple of (is_valid: bool, error_message: str | None)
    """
    valid_types = [
        "feat",
        "fix",
        "docs",
        "style",
        "refactor",
        "perf",
        "test",
        "build",
        "ci",
        "chore",
        "revert",
    ]

    # Check if empty
    if not message or not message.strip():
        return False, "Commit message cannot be empty"

    # Check length (hard limit 72 chars for subject)
    if len(message) > 72:
        return (
            False,
            f"Subject line too long ({len(message)} chars). Maximum is 72 characters.",
        )

    # Check for trailing period
    if message.rstrip().endswith("."):
        return False, "Subject line should not end with a period"

    # Parse type and optional scope
    if ":" not in message:
        return (
            False,
            f"Missing colon. Format should be: <type>[scope]: <description>. Valid types: {', '.join(valid_types)}",
        )

    type_part = message.split(":")[0].strip()

    # Handle optional scope: type(scope) or just type
    if "(" in type_part:
        if ")" not in type_part:
            return False, "Malformed scope. Use format: type(scope)"
        commit_type = type_part.split("(")[0]
    else:
        commit_type = type_part

    # Validate type
    if commit_type not in valid_types:
        return (
            False,
            f"Invalid type '{commit_type}'. Valid types: {', '.join(valid_types)}",
        )

    # Check description exists after colon
    description_part = message.split(":", 1)[1].strip()
    if not description_part:
        return False, "Description after colon cannot be empty"

    # Check description starts with lowercase (convention)
    if description_part[0].isupper():
        # This is a soft warning, not a hard error in most specs
        pass  # We allow it but could warn

    return True, None


def cmd_status(args: argparse.Namespace) -> int:
    """Handle the 'status' command."""
    status = get_uncommitted_changes()

    if args.json:
        print(json.dumps(status.to_dict(), indent=2))
    else:
        if not status.has_changes:
            print("No uncommitted changes found.")
            return 0

        summary = status.to_dict()["summary"]
        print("Uncommitted Changes Summary:")
        print(f"  Content files:        {summary['content_total']}")
        print(f"    - Staged:           {summary['staged_count']}")
        print(f"    - Unstaged:         {summary['unstaged_count']}")
        print(f"    - Untracked:        {summary['untracked_count']}")
        print(f"  Infrastructure files: {summary['infrastructure_count']}")

        if status.staged_files:
            print("\nStaged content files:")
            for f in status.staged_files:
                print(f"  + {f}")

        if status.unstaged_files:
            print("\nUnstaged content files:")
            for f in status.unstaged_files:
                print(f"  M {f}")

        if status.untracked_files:
            print("\nUntracked content files:")
            for f in status.untracked_files:
                print(f"  ? {f}")

        if status.infrastructure_files:
            print("\nInfrastructure files (will be committed, excluded from message):")
            for f in status.infrastructure_files:
                print(f"  * {f}")

    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    """Handle the 'diff' command."""
    status = get_uncommitted_changes()

    if not status.has_changes:
        print("No uncommitted changes to diff.")
        return 0

    diff = get_full_diff()
    print(diff)
    return 0


def cmd_commit(args: argparse.Namespace) -> int:
    """Handle the 'commit' command."""
    # Validate message format
    is_valid, error = validate_conventional_commit(args.message)
    if not is_valid:
        print("Error: Invalid commit message format.", file=sys.stderr)
        print(f"  {error}", file=sys.stderr)
        return 1

    # Check for changes
    status = get_uncommitted_changes()
    if not status.has_changes:
        print("Nothing to commit. Working tree is clean.")
        return 0

    # Stage all if requested
    if args.stage_all:
        if not stage_all_changes():
            print("Error: Failed to stage changes.", file=sys.stderr)
            return 1
        print(
            f"Staged all changes ({status.to_dict()['summary']['total_changes']} files)"
        )

    # Verify we have staged changes
    status_after_staging = get_uncommitted_changes()
    if not status_after_staging.staged_files:
        print("Error: No staged changes to commit.", file=sys.stderr)
        print(
            "Use --stage-all to stage all changes, or stage files manually.",
            file=sys.stderr,
        )
        return 1

    # Commit
    success, output = commit_changes(args.message, args.description)

    if success:
        print("Commit successful!")
        print(output)
        return 0
    else:
        print("Error: Commit failed.", file=sys.stderr)
        print(output, file=sys.stderr)
        return 1


def cmd_validate(args: argparse.Namespace) -> int:
    """Handle the 'validate' command to check commit message format."""
    is_valid, error = validate_conventional_commit(args.message)

    if is_valid:
        print("Valid conventional commit message.")
        return 0
    else:
        print(f"Invalid: {error}", file=sys.stderr)
        return 1


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Git commit helper for smart commits with conventional commit format"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Status command
    status_parser = subparsers.add_parser(
        "status",
        help="Show uncommitted changes (staged, unstaged, untracked)",
    )
    status_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    # Diff command
    subparsers.add_parser(
        "diff",
        help="Show full diff of all uncommitted changes",
    )

    # Commit command
    commit_parser = subparsers.add_parser(
        "commit",
        help="Create a commit with conventional commit format",
    )
    commit_parser.add_argument(
        "--message",
        "-m",
        type=str,
        required=True,
        help="Commit message (conventional commit format: type: description)",
    )
    commit_parser.add_argument(
        "--description",
        "-d",
        type=str,
        help="Optional commit body/description",
    )
    commit_parser.add_argument(
        "--stage-all",
        action="store_true",
        help="Stage all changes before committing",
    )

    # Validate command
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate a commit message against conventional commits format",
    )
    validate_parser.add_argument(
        "message",
        type=str,
        help="Commit message to validate",
    )

    args = parser.parse_args()

    # Check if we're in a git repository
    if not is_git_repository():
        print("Error: Not a git repository.", file=sys.stderr)
        return 1

    # Dispatch to appropriate command
    if args.command == "status":
        return cmd_status(args)
    elif args.command == "diff":
        return cmd_diff(args)
    elif args.command == "commit":
        return cmd_commit(args)
    elif args.command == "validate":
        return cmd_validate(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
