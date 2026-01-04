"""
Git Status Watcher for Consciousness Daemon

Monitors git repository status and yields observations about:
- Staged/unstaged changes
- Untracked files
- Branch information
- Recent commits
- Ahead/behind status relative to remote

Uses polling (git doesn't have native watch events).
"""

import asyncio
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator, Optional


@dataclass
class Commit:
    """Represents a git commit."""

    hash: str
    message: str
    author: str
    timestamp: datetime
    relative_time: str = ""

    def __post_init__(self):
        if not self.relative_time:
            # Calculate relative time
            now = datetime.now(timezone.utc)
            diff = now - self.timestamp
            seconds = diff.total_seconds()

            if seconds < 60:
                self.relative_time = "just now"
            elif seconds < 3600:
                mins = int(seconds / 60)
                self.relative_time = f"{mins} min ago"
            elif seconds < 86400:
                hours = int(seconds / 3600)
                self.relative_time = f"{hours} hour{'s' if hours > 1 else ''} ago"
            else:
                days = int(seconds / 86400)
                self.relative_time = f"{days} day{'s' if days > 1 else ''} ago"


@dataclass
class GitFileChange:
    """Represents a file change in git status."""

    path: str
    status: str  # 'A' added, 'M' modified, 'D' deleted, 'R' renamed, '?' untracked
    status_label: str = ""

    def __post_init__(self):
        status_map = {
            "A": "added",
            "M": "modified",
            "D": "deleted",
            "R": "renamed",
            "C": "copied",
            "U": "updated",
            "?": "untracked",
            "!": "ignored",
        }
        self.status_label = status_map.get(self.status, self.status)


@dataclass
class GitStatus:
    """Complete git repository status snapshot."""

    branch: str
    staged: list[GitFileChange] = field(default_factory=list)
    unstaged: list[GitFileChange] = field(default_factory=list)
    untracked: list[GitFileChange] = field(default_factory=list)
    ahead: int = 0
    behind: int = 0
    is_dirty: bool = False
    has_conflicts: bool = False
    timestamp: float = field(default_factory=time.time)
    remote_branch: Optional[str] = None

    def __post_init__(self):
        self.is_dirty = bool(self.staged or self.unstaged or self.untracked)

    def __eq__(self, other: object) -> bool:
        """Check if two git statuses are equivalent (ignoring timestamp)."""
        if not isinstance(other, GitStatus):
            return False
        return (
            self.branch == other.branch
            and self.staged == other.staged
            and self.unstaged == other.unstaged
            and self.untracked == other.untracked
            and self.ahead == other.ahead
            and self.behind == other.behind
        )


@dataclass
class GitObservation:
    """A git observation to be processed by the daemon."""

    status: GitStatus
    recent_commits: list[Commit]
    diff_summary: str = ""
    has_changes: bool = False

    def __post_init__(self):
        self.has_changes = self.status.is_dirty or bool(self.recent_commits)


class GitWatcher:
    """
    Watches a git repository for status changes.

    Unlike file watching, git monitoring uses polling since git
    doesn't provide native file system events for repository state.
    """

    def __init__(
        self,
        repo_path: Path,
        poll_interval: float = 30.0,
        commits_to_track: int = 5,
        include_diff: bool = True,
    ):
        """
        Initialize the git watcher.

        Args:
            repo_path: Path to the git repository root
            poll_interval: Seconds between status checks
            commits_to_track: Number of recent commits to include
            include_diff: Whether to include diff summary
        """
        self.repo_path = Path(repo_path).resolve()
        self.poll_interval = poll_interval
        self.commits_to_track = commits_to_track
        self.include_diff = include_diff
        self._running = False
        self._last_status: Optional[GitStatus] = None
        self._last_commit_hash: Optional[str] = None

    async def _run_git(self, *args: str) -> tuple[bool, str]:
        """
        Run a git command and return output.

        Returns:
            Tuple of (success, output)
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                "git",
                *args,
                cwd=self.repo_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode == 0:
                return True, stdout.decode("utf-8", errors="replace").strip()
            else:
                return False, stderr.decode("utf-8", errors="replace").strip()

        except FileNotFoundError:
            return False, "git command not found"
        except Exception as e:
            return False, str(e)

    async def is_git_repo(self) -> bool:
        """Check if the path is a valid git repository."""
        success, _ = await self._run_git("rev-parse", "--git-dir")
        return success

    async def get_branch(self) -> tuple[str, Optional[str]]:
        """
        Get current branch name and tracking remote.

        Returns:
            Tuple of (branch_name, remote_branch or None)
        """
        success, branch = await self._run_git("rev-parse", "--abbrev-ref", "HEAD")
        if not success:
            return "unknown", None

        # Get tracking branch
        success, remote = await self._run_git(
            "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"
        )
        remote_branch = remote if success else None

        return branch, remote_branch

    async def get_ahead_behind(self) -> tuple[int, int]:
        """
        Get commits ahead/behind remote.

        Returns:
            Tuple of (ahead, behind) counts
        """
        success, output = await self._run_git(
            "rev-list", "--left-right", "--count", "@{u}...HEAD"
        )

        if not success or not output:
            return 0, 0

        try:
            parts = output.split()
            if len(parts) == 2:
                return int(parts[1]), int(parts[0])
        except (ValueError, IndexError):
            pass

        return 0, 0

    async def get_status(self) -> GitStatus:
        """
        Get current git status.

        Parses `git status --porcelain=v1` output.
        """
        branch, remote_branch = await self.get_branch()
        ahead, behind = await self.get_ahead_behind()

        success, output = await self._run_git("status", "--porcelain=v1")

        staged: list[GitFileChange] = []
        unstaged: list[GitFileChange] = []
        untracked: list[GitFileChange] = []
        has_conflicts = False

        if success and output:
            for line in output.split("\n"):
                if not line or len(line) < 3:
                    continue

                index_status = line[0]
                worktree_status = line[1]
                path = line[3:]

                # Handle renames (format: R  old -> new)
                if " -> " in path:
                    path = path.split(" -> ")[1]

                # Check for conflicts
                if index_status == "U" or worktree_status == "U":
                    has_conflicts = True

                # Untracked files
                if index_status == "?" and worktree_status == "?":
                    untracked.append(GitFileChange(path=path, status="?"))
                    continue

                # Staged changes (index)
                if index_status not in (" ", "?"):
                    staged.append(GitFileChange(path=path, status=index_status))

                # Unstaged changes (worktree)
                if worktree_status not in (" ", "?"):
                    unstaged.append(GitFileChange(path=path, status=worktree_status))

        return GitStatus(
            branch=branch,
            remote_branch=remote_branch,
            staged=staged,
            unstaged=unstaged,
            untracked=untracked,
            ahead=ahead,
            behind=behind,
            has_conflicts=has_conflicts,
        )

    async def get_recent_commits(self, n: Optional[int] = None) -> list[Commit]:
        """
        Get recent commits.

        Args:
            n: Number of commits to retrieve (uses instance default if None)

        Returns:
            List of recent Commit objects
        """
        count = n if n is not None else self.commits_to_track

        # Format: hash|message|author|timestamp
        success, output = await self._run_git(
            "log",
            f"-{count}",
            "--format=%H|%s|%an|%aI",
        )

        commits: list[Commit] = []

        if success and output:
            for line in output.split("\n"):
                if not line:
                    continue

                parts = line.split("|", 3)
                if len(parts) >= 4:
                    try:
                        timestamp = datetime.fromisoformat(parts[3])
                        commits.append(
                            Commit(
                                hash=parts[0][:7],  # Short hash
                                message=parts[1],
                                author=parts[2],
                                timestamp=timestamp,
                            )
                        )
                    except (ValueError, IndexError):
                        continue

        return commits

    async def get_diff_summary(self) -> str:
        """
        Get a summary of current diff (staged + unstaged).

        Returns compact diff stats.
        """
        if not self.include_diff:
            return ""

        # Get staged diff stats
        success_staged, staged = await self._run_git("diff", "--cached", "--stat")

        # Get unstaged diff stats
        success_unstaged, unstaged = await self._run_git("diff", "--stat")

        parts = []
        if success_staged and staged:
            parts.append(f"Staged:\n{staged}")
        if success_unstaged and unstaged:
            parts.append(f"Unstaged:\n{unstaged}")

        return "\n\n".join(parts)

    async def get_observation(self) -> GitObservation:
        """
        Get complete git observation for LLM consumption.

        Returns:
            GitObservation with status, commits, and diff
        """
        status = await self.get_status()
        commits = await self.get_recent_commits()
        diff_summary = await self.get_diff_summary() if status.is_dirty else ""

        return GitObservation(
            status=status,
            recent_commits=commits,
            diff_summary=diff_summary,
        )

    def _has_status_changed(self, new_status: GitStatus) -> bool:
        """Check if status has meaningfully changed."""
        if self._last_status is None:
            return True
        return new_status != self._last_status

    def _has_new_commits(self, commits: list[Commit]) -> bool:
        """Check if there are new commits since last check."""
        if not commits:
            return False
        if self._last_commit_hash is None:
            return True
        return commits[0].hash != self._last_commit_hash

    async def watch(self) -> AsyncIterator[GitObservation]:
        """
        Yield git observations when changes are detected.

        This is a polling-based watcher that yields observations
        only when the git status or commits have changed.
        """
        self._running = True

        # Check if this is a git repo
        if not await self.is_git_repo():
            return

        while self._running:
            observation = await self.get_observation()

            # Check if anything changed
            status_changed = self._has_status_changed(observation.status)
            new_commits = self._has_new_commits(observation.recent_commits)

            if status_changed or new_commits:
                # Update tracking
                self._last_status = observation.status
                if observation.recent_commits:
                    self._last_commit_hash = observation.recent_commits[0].hash

                yield observation

            await asyncio.sleep(self.poll_interval)

    def stop(self) -> None:
        """Stop the watcher."""
        self._running = False

    def format_for_llm(self, observation: GitObservation) -> str:
        """
        Format git observation as text for LLM consumption.

        Creates a structured, human-readable format that provides
        context for the LLM to understand the repository state.
        """
        status = observation.status
        lines = [
            "=== GIT STATUS ===",
            f"Branch: {status.branch}",
        ]

        # Remote tracking
        if status.remote_branch:
            lines.append(f"Tracking: {status.remote_branch}")

        # Ahead/Behind
        if status.ahead or status.behind:
            ahead_str = f"{status.ahead} ahead" if status.ahead else ""
            behind_str = f"{status.behind} behind" if status.behind else ""
            sep = ", " if ahead_str and behind_str else ""
            lines.append(f"Status: {ahead_str}{sep}{behind_str}")

        # Conflicts warning
        if status.has_conflicts:
            lines.append("")
            lines.append("WARNING: Merge conflicts detected!")

        lines.append("")

        # Staged files
        if status.staged:
            lines.append(f"STAGED ({len(status.staged)} files):")
            for f in status.staged:
                symbol = {"A": "+", "M": "~", "D": "-", "R": ">", "C": "c"}.get(
                    f.status, f.status
                )
                lines.append(f"  {symbol} {f.path}")
            lines.append("")

        # Unstaged files
        if status.unstaged:
            lines.append(f"UNSTAGED ({len(status.unstaged)} files):")
            for f in status.unstaged:
                symbol = {"M": "~", "D": "-"}.get(f.status, f.status)
                lines.append(f"  {symbol} {f.path}")
            lines.append("")

        # Untracked files
        if status.untracked:
            lines.append(f"UNTRACKED ({len(status.untracked)} files):")
            for f in status.untracked:
                lines.append(f"  ? {f.path}")
            lines.append("")

        # Recent commits
        if observation.recent_commits:
            lines.append("RECENT COMMITS:")
            for commit in observation.recent_commits:
                # Truncate long messages
                msg = commit.message[:50]
                if len(commit.message) > 50:
                    msg += "..."
                lines.append(f'  {commit.hash} - "{msg}" ({commit.relative_time})')
            lines.append("")

        # Clean status indicator
        if not status.is_dirty:
            lines.append("Working tree is clean.")
            lines.append("")

        lines.append("=== END GIT STATUS ===")

        return "\n".join(lines)

    def format_for_llm_compact(self, observation: GitObservation) -> str:
        """
        Format git observation in compact form for token efficiency.
        """
        status = observation.status
        parts = []

        if status.branch != "main" and status.branch != "master":
            parts.append(f"[{status.branch}]")

        if status.ahead:
            parts.append(f"+{status.ahead}")
        if status.behind:
            parts.append(f"-{status.behind}")

        if status.staged:
            staged_count = len(status.staged)
            parts.append(f"staged:{staged_count}")

        if status.unstaged:
            unstaged_count = len(status.unstaged)
            parts.append(f"unstaged:{unstaged_count}")

        if status.untracked:
            untracked_count = len(status.untracked)
            parts.append(f"untracked:{untracked_count}")

        if status.has_conflicts:
            parts.append("CONFLICTS!")

        if not parts:
            return "git:clean"

        return "git:" + " ".join(parts)


async def create_git_watcher(
    repo_path: str | Path,
    poll_interval: float = 30.0,
    commits_to_track: int = 5,
) -> Optional[GitWatcher]:
    """
    Factory function to create a configured git watcher.

    Args:
        repo_path: Path to the git repository
        poll_interval: Seconds between polls
        commits_to_track: Number of recent commits to track

    Returns:
        Configured GitWatcher instance, or None if not a git repo
    """
    watcher = GitWatcher(
        repo_path=Path(repo_path),
        poll_interval=poll_interval,
        commits_to_track=commits_to_track,
    )

    if await watcher.is_git_repo():
        return watcher
    return None


# Example usage and testing
async def _demo():
    """Demo function to test the git watcher."""
    from pathlib import Path

    repo = Path(__file__).parent.parent
    print(f"Watching git repo: {repo}")
    print("Press Ctrl+C to stop\n")

    watcher = GitWatcher(repo, poll_interval=5.0)

    if not await watcher.is_git_repo():
        print("Not a git repository!")
        return

    # Get initial observation
    obs = await watcher.get_observation()
    print(watcher.format_for_llm(obs))
    print()

    # Watch for changes
    try:
        async for observation in watcher.watch():
            print(watcher.format_for_llm(observation))
            print()
    except KeyboardInterrupt:
        print("\nStopping watcher...")
        watcher.stop()


if __name__ == "__main__":
    asyncio.run(_demo())
