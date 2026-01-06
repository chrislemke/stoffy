"""
Self-Write Tracker

Tracks files that the consciousness daemon has recently written to,
allowing the daemon to filter out its own writes and avoid infinite loops.

This prevents the consciousness from detecting its own output as user input.
"""

import time
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class WriteRecord:
    """Record of a file write by the consciousness."""
    file_path: str
    timestamp: float

    def is_expired(self, ttl_seconds: float = 5.0) -> bool:
        """Check if this write record has expired."""
        return (time.time() - self.timestamp) > ttl_seconds


class SelfWriteTracker:
    """
    Thread-safe tracker for files written by the consciousness.

    When the consciousness writes to a file (e.g., responding to a user message),
    it registers the write here. The daemon then checks this tracker before
    processing file changes to filter out its own writes.

    Usage:
        # When writing to a file
        tracker.record_write("/path/to/file.md")

        # When checking if a change should be ignored
        if tracker.should_ignore("/path/to/file.md"):
            continue  # Skip this file
    """

    # Default time-to-live for write records (seconds)
    # Increased from 5.0 to 30.0 to prevent false positives when the file watcher
    # detects changes slightly delayed after a write operation
    DEFAULT_TTL = 30.0

    def __init__(self, ttl_seconds: float = DEFAULT_TTL):
        """
        Initialize the tracker.

        Args:
            ttl_seconds: How long to ignore a file after writing to it
        """
        self._writes: Dict[str, WriteRecord] = {}
        self._lock = threading.Lock()
        self._ttl = ttl_seconds

    def record_write(self, file_path: str | Path) -> None:
        """
        Record that the consciousness wrote to a file.

        Args:
            file_path: Path to the file that was written
        """
        path_str = str(Path(file_path).resolve())
        with self._lock:
            self._writes[path_str] = WriteRecord(
                file_path=path_str,
                timestamp=time.time(),
            )

    def should_ignore(self, file_path: str | Path) -> bool:
        """
        Check if a file change should be ignored (recently written by consciousness).

        Args:
            file_path: Path to check

        Returns:
            True if the file was recently written by consciousness and should be ignored
        """
        path_str = str(Path(file_path).resolve())
        with self._lock:
            record = self._writes.get(path_str)
            if record is None:
                return False

            if record.is_expired(self._ttl):
                # Clean up expired record
                del self._writes[path_str]
                return False

            return True

    def cleanup_expired(self) -> int:
        """
        Remove expired write records.

        Returns:
            Number of records cleaned up
        """
        with self._lock:
            expired = [
                path for path, record in self._writes.items()
                if record.is_expired(self._ttl)
            ]
            for path in expired:
                del self._writes[path]
            return len(expired)

    def clear(self) -> None:
        """Clear all write records."""
        with self._lock:
            self._writes.clear()

    @property
    def tracked_count(self) -> int:
        """Get the number of currently tracked writes."""
        with self._lock:
            return len(self._writes)


# Global singleton instance for cross-module access
_global_tracker: Optional[SelfWriteTracker] = None
_tracker_lock = threading.Lock()


def get_self_write_tracker() -> SelfWriteTracker:
    """
    Get the global self-write tracker instance.

    Returns:
        The singleton SelfWriteTracker instance
    """
    global _global_tracker
    with _tracker_lock:
        if _global_tracker is None:
            _global_tracker = SelfWriteTracker()
        return _global_tracker
