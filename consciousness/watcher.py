"""
Consciousness File Watcher

Watches all files in the Stoffy folder and yields batched, debounced
file change events for LLM consumption.

Uses watchfiles (Rust-based) for high-performance file system monitoring.

Also provides CombinedWatcher that integrates file watching with git status
monitoring for complete repository awareness.
"""

import asyncio
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional, TYPE_CHECKING
import fnmatch

from watchfiles import awatch, Change

if TYPE_CHECKING:
    from .watcher_git import GitWatcher, GitObservation


@dataclass
class FileChange:
    """Represents a single file change event."""

    path: str
    change_type: str  # 'created', 'modified', 'deleted'
    timestamp: float
    relative_path: str = field(default="")

    def __post_init__(self):
        if not self.relative_path:
            self.relative_path = self.path


@dataclass
class ChangeBatch:
    """A batch of file changes with metadata."""

    changes: list[FileChange]
    batch_timestamp: float

    @property
    def created(self) -> list[FileChange]:
        return [c for c in self.changes if c.change_type == 'created']

    @property
    def modified(self) -> list[FileChange]:
        return [c for c in self.changes if c.change_type == 'modified']

    @property
    def deleted(self) -> list[FileChange]:
        return [c for c in self.changes if c.change_type == 'deleted']


# Default patterns to ignore
DEFAULT_IGNORE_PATTERNS = [
    ".git",
    ".git/**",
    "__pycache__",
    "__pycache__/**",
    "*.pyc",
    "*.pyo",
    ".venv",
    ".venv/**",
    "venv",
    "venv/**",
    ".DS_Store",
    "logs",
    "logs/**",
    "*.db",
    "*.db-journal",
    "*.db-wal",
    "*.db-shm",
    "node_modules",
    "node_modules/**",
    ".pytest_cache",
    ".pytest_cache/**",
    ".mypy_cache",
    ".mypy_cache/**",
    "*.egg-info",
    "*.egg-info/**",
    ".eggs",
    ".eggs/**",
    "dist",
    "dist/**",
    "build",
    "build/**",
    "*.swp",
    "*.swo",
    "*~",
    ".coverage",
    "htmlcov",
    "htmlcov/**",
]


class ConsciousnessWatcher:
    """
    Watches the Stoffy project folder for file changes.

    Provides debounced, batched file change events suitable for
    consumption by an LLM that decides what actions to take.
    """

    def __init__(
        self,
        root_path: Path,
        ignore_patterns: list[str] | None = None,
        debounce_ms: int = 500,
    ):
        """
        Initialize the file watcher.

        Args:
            root_path: The root directory to watch
            ignore_patterns: List of glob patterns to ignore (uses defaults if None)
            debounce_ms: Debounce interval in milliseconds
        """
        self.root_path = Path(root_path).resolve()
        self.ignore_patterns = ignore_patterns or DEFAULT_IGNORE_PATTERNS.copy()
        self.debounce_ms = debounce_ms
        self._running = False
        self._stop_event = asyncio.Event()

    def _should_ignore(self, path: Path) -> bool:
        """Check if a path should be ignored based on patterns."""
        try:
            relative = path.relative_to(self.root_path)
            path_str = str(relative)
            path_parts = relative.parts
        except ValueError:
            # Path is not relative to root
            return True

        for pattern in self.ignore_patterns:
            # Check the full relative path
            if fnmatch.fnmatch(path_str, pattern):
                return True

            # Check each component of the path
            for part in path_parts:
                if fnmatch.fnmatch(part, pattern):
                    return True

            # Check if any parent directory matches
            if "**" not in pattern and "/" not in pattern:
                # Simple pattern - check against filename and directory names
                if fnmatch.fnmatch(path.name, pattern):
                    return True

        return False

    def _change_type_to_str(self, change: Change) -> str:
        """Convert watchfiles Change enum to string."""
        if change == Change.added:
            return "created"
        elif change == Change.modified:
            return "modified"
        elif change == Change.deleted:
            return "deleted"
        else:
            return "unknown"

    def _create_file_change(self, change: Change, path_str: str) -> FileChange | None:
        """Create a FileChange from a watchfiles event."""
        path = Path(path_str)

        if self._should_ignore(path):
            return None

        try:
            relative_path = str(path.relative_to(self.root_path))
        except ValueError:
            relative_path = path_str

        return FileChange(
            path=path_str,
            change_type=self._change_type_to_str(change),
            timestamp=time.time(),
            relative_path=relative_path,
        )

    async def watch(self) -> AsyncIterator[list[FileChange]]:
        """
        Yield batches of file changes.

        Changes are debounced and batched according to debounce_ms.
        Each yield contains all changes that occurred within the
        debounce window.

        Yields:
            List of FileChange objects representing changes in the batch
        """
        self._running = True
        self._stop_event.clear()  # Reset for potential restart

        async for changes in awatch(
            self.root_path,
            debounce=self.debounce_ms,
            recursive=True,
            force_polling=False,
            stop_event=self._stop_event,
        ):
            if not self._running:
                break

            batch = []
            for change_type, path_str in changes:
                file_change = self._create_file_change(change_type, path_str)
                if file_change is not None:
                    batch.append(file_change)

            if batch:
                yield batch

    def stop(self):
        """Stop the watcher."""
        self._running = False
        self._stop_event.set()

    def format_for_llm(self, changes: list[FileChange]) -> str:
        """
        Format changes as text for LM Studio consumption.

        Creates a structured, human-readable format that provides
        context for the LLM to understand what happened.

        Args:
            changes: List of file changes to format

        Returns:
            Formatted string suitable for LLM processing
        """
        if not changes:
            return "No file changes detected."

        # Group by change type
        created = [c for c in changes if c.change_type == "created"]
        modified = [c for c in changes if c.change_type == "modified"]
        deleted = [c for c in changes if c.change_type == "deleted"]

        lines = [
            "=== FILE SYSTEM OBSERVATION ===",
            f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total changes: {len(changes)}",
            "",
        ]

        if created:
            lines.append(f"CREATED ({len(created)} files):")
            for c in created:
                lines.append(f"  + {c.relative_path}")
            lines.append("")

        if modified:
            lines.append(f"MODIFIED ({len(modified)} files):")
            for c in modified:
                lines.append(f"  ~ {c.relative_path}")
            lines.append("")

        if deleted:
            lines.append(f"DELETED ({len(deleted)} files):")
            for c in deleted:
                lines.append(f"  - {c.relative_path}")
            lines.append("")

        # Add context hints for the LLM
        lines.append("CONTEXT:")

        # Identify file types
        extensions = set()
        for c in changes:
            ext = Path(c.path).suffix.lower()
            if ext:
                extensions.add(ext)

        if extensions:
            lines.append(f"  File types affected: {', '.join(sorted(extensions))}")

        # Identify directories affected
        directories = set()
        for c in changes:
            parent = Path(c.relative_path).parent
            if str(parent) != ".":
                directories.add(str(parent))

        if directories:
            lines.append(f"  Directories affected: {', '.join(sorted(directories)[:5])}")
            if len(directories) > 5:
                lines.append(f"    ... and {len(directories) - 5} more")

        lines.append("")
        lines.append("=== END OBSERVATION ===")

        return "\n".join(lines)

    def format_for_llm_compact(self, changes: list[FileChange]) -> str:
        """
        Format changes in a compact format for token efficiency.

        Args:
            changes: List of file changes to format

        Returns:
            Compact formatted string
        """
        if not changes:
            return "No changes."

        parts = []
        for c in changes:
            symbol = {"created": "+", "modified": "~", "deleted": "-"}.get(
                c.change_type, "?"
            )
            parts.append(f"{symbol}{c.relative_path}")

        return f"[{time.strftime('%H:%M:%S')}] " + ", ".join(parts)


async def create_watcher(
    root_path: str | Path,
    ignore_patterns: list[str] | None = None,
    debounce_ms: int = 500,
) -> ConsciousnessWatcher:
    """
    Factory function to create a configured watcher.

    Args:
        root_path: Path to watch
        ignore_patterns: Patterns to ignore (optional)
        debounce_ms: Debounce interval

    Returns:
        Configured ConsciousnessWatcher instance
    """
    return ConsciousnessWatcher(
        root_path=Path(root_path),
        ignore_patterns=ignore_patterns,
        debounce_ms=debounce_ms,
    )


@dataclass
class CombinedObservation:
    """Combined observation from file watcher and git watcher."""

    file_changes: list[FileChange]
    git_observation: Optional["GitObservation"]
    timestamp: float = field(default_factory=time.time)

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes to report."""
        if self.file_changes:
            return True
        if self.git_observation and self.git_observation.has_changes:
            return True
        return False


class CombinedWatcher:
    """
    Watches both file system changes and git status.

    Combines ConsciousnessWatcher (event-driven file watching) with
    GitWatcher (polling-based git status monitoring) to provide
    complete repository awareness.
    """

    def __init__(
        self,
        root_path: Path,
        ignore_patterns: list[str] | None = None,
        debounce_ms: int = 500,
        git_poll_interval: float = 30.0,
        commits_to_track: int = 5,
    ):
        """
        Initialize the combined watcher.

        Args:
            root_path: The root directory to watch
            ignore_patterns: List of glob patterns to ignore (uses defaults if None)
            debounce_ms: Debounce interval for file watching
            git_poll_interval: Seconds between git status polls
            commits_to_track: Number of recent commits to include
        """
        self.root_path = Path(root_path).resolve()

        # File watcher
        self.file_watcher = ConsciousnessWatcher(
            root_path=self.root_path,
            ignore_patterns=ignore_patterns,
            debounce_ms=debounce_ms,
        )

        # Git watcher (lazy initialization)
        self._git_watcher: Optional["GitWatcher"] = None
        self._git_poll_interval = git_poll_interval
        self._commits_to_track = commits_to_track
        self._git_enabled = True

        self._running = False
        self._last_git_observation: Optional["GitObservation"] = None

    async def _init_git_watcher(self) -> bool:
        """Initialize git watcher if in a git repo."""
        if not self._git_enabled:
            return False

        try:
            from .watcher_git import GitWatcher

            watcher = GitWatcher(
                repo_path=self.root_path,
                poll_interval=self._git_poll_interval,
                commits_to_track=self._commits_to_track,
            )

            if await watcher.is_git_repo():
                self._git_watcher = watcher
                return True
        except ImportError:
            pass

        return False

    async def watch(self) -> AsyncIterator[CombinedObservation]:
        """
        Yield combined observations from file and git watchers.

        File changes are event-driven (immediate).
        Git status is polled on interval and checked after file changes.
        """
        self._running = True

        # Initialize git watcher
        await self._init_git_watcher()

        # Create tasks for both watchers
        file_queue: asyncio.Queue[list[FileChange]] = asyncio.Queue()
        git_queue: asyncio.Queue["GitObservation"] = asyncio.Queue()

        async def file_watcher_task():
            """Task to collect file changes."""
            try:
                async for changes in self.file_watcher.watch():
                    if not self._running:
                        break
                    await file_queue.put(changes)
            except asyncio.CancelledError:
                pass

        async def git_watcher_task():
            """Task to collect git observations."""
            if not self._git_watcher:
                return
            try:
                async for observation in self._git_watcher.watch():
                    if not self._running:
                        break
                    await git_queue.put(observation)
            except asyncio.CancelledError:
                pass

        # Start watcher tasks
        file_task = asyncio.create_task(file_watcher_task())
        git_task = asyncio.create_task(git_watcher_task())

        try:
            while self._running:
                file_changes: list[FileChange] = []
                git_observation: Optional["GitObservation"] = None

                # Wait for any observation with timeout
                try:
                    # Check file queue first (more frequent)
                    try:
                        file_changes = await asyncio.wait_for(
                            file_queue.get(), timeout=1.0
                        )
                    except asyncio.TimeoutError:
                        pass

                    # Check git queue (less frequent)
                    try:
                        git_observation = git_queue.get_nowait()
                        self._last_git_observation = git_observation
                    except asyncio.QueueEmpty:
                        pass

                except asyncio.CancelledError:
                    break

                # Yield if we have anything to report
                if file_changes or git_observation:
                    yield CombinedObservation(
                        file_changes=file_changes,
                        git_observation=git_observation,
                    )

        finally:
            # Cancel tasks
            file_task.cancel()
            git_task.cancel()
            try:
                await file_task
            except asyncio.CancelledError:
                pass
            try:
                await git_task
            except asyncio.CancelledError:
                pass

    def stop(self) -> None:
        """Stop all watchers."""
        self._running = False
        self.file_watcher.stop()
        if self._git_watcher:
            self._git_watcher.stop()

    async def get_current_git_status(self) -> Optional["GitObservation"]:
        """Get current git status (forces a fresh check)."""
        if self._git_watcher:
            return await self._git_watcher.get_observation()
        return None

    def format_for_llm(self, observation: CombinedObservation) -> str:
        """
        Format combined observation for LLM consumption.

        Combines file changes and git status in a unified format.
        """
        parts = []

        # File changes section
        if observation.file_changes:
            parts.append(self.file_watcher.format_for_llm(observation.file_changes))

        # Git status section
        if observation.git_observation and self._git_watcher:
            parts.append(
                self._git_watcher.format_for_llm(observation.git_observation)
            )

        if not parts:
            return "No changes detected."

        return "\n\n".join(parts)

    def format_for_llm_compact(self, observation: CombinedObservation) -> str:
        """
        Format combined observation in compact form.
        """
        parts = []

        if observation.file_changes:
            parts.append(
                self.file_watcher.format_for_llm_compact(observation.file_changes)
            )

        if observation.git_observation and self._git_watcher:
            parts.append(
                self._git_watcher.format_for_llm_compact(observation.git_observation)
            )

        return " | ".join(parts) if parts else "No changes"


async def create_combined_watcher(
    root_path: str | Path,
    ignore_patterns: list[str] | None = None,
    debounce_ms: int = 500,
    git_poll_interval: float = 30.0,
) -> CombinedWatcher:
    """
    Factory function to create a combined file + git watcher.

    Args:
        root_path: Path to watch
        ignore_patterns: Patterns to ignore (optional)
        debounce_ms: Debounce interval for files
        git_poll_interval: Git polling interval

    Returns:
        Configured CombinedWatcher instance
    """
    return CombinedWatcher(
        root_path=Path(root_path),
        ignore_patterns=ignore_patterns,
        debounce_ms=debounce_ms,
        git_poll_interval=git_poll_interval,
    )


# Example usage and testing
async def _demo():
    """Demo function to test the watcher."""
    import sys

    root = Path(__file__).parent.parent
    print(f"Watching: {root}")
    print("Press Ctrl+C to stop\n")

    watcher = ConsciousnessWatcher(root)

    try:
        async for changes in watcher.watch():
            print(watcher.format_for_llm(changes))
            print()
    except KeyboardInterrupt:
        print("\nStopping watcher...")
        watcher.stop()


async def _demo_combined():
    """Demo function to test the combined watcher."""
    root = Path(__file__).parent.parent
    print(f"Watching (combined): {root}")
    print("Press Ctrl+C to stop\n")

    watcher = CombinedWatcher(root, git_poll_interval=10.0)

    # Show initial git status
    git_obs = await watcher.get_current_git_status()
    if git_obs and watcher._git_watcher:
        print("Initial git status:")
        print(watcher._git_watcher.format_for_llm(git_obs))
        print()

    try:
        async for observation in watcher.watch():
            print(watcher.format_for_llm(observation))
            print()
    except KeyboardInterrupt:
        print("\nStopping watcher...")
        watcher.stop()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--combined":
        asyncio.run(_demo_combined())
    else:
        asyncio.run(_demo())
