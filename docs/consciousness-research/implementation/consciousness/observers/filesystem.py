"""
File System Observer - Perceptual Level Observation

Uses watchfiles (Rust-based) for efficient file system monitoring.
Implements debouncing and pattern filtering.
"""

import asyncio
from collections import deque
from datetime import datetime
from fnmatch import fnmatch
from pathlib import Path
from typing import Optional

from watchfiles import awatch, Change

from . import EventType, Observation, ObserverLevel, ObserverProtocol


class FileSystemObserver:
    """
    Watches file system for changes.

    Perceptual-level observer (Level 1):
    - High resolution (milliseconds to seconds)
    - Raw events with minimal interpretation
    - Debouncing to prevent event storms
    """

    def __init__(
        self,
        watch_paths: list[str],
        ignore_patterns: list[str],
        debounce_ms: int = 500,
        root_path: Optional[Path] = None,
    ):
        self.id = "filesystem"
        self.level = ObserverLevel.PERCEPTUAL

        self.root_path = root_path or Path.cwd()
        self.watch_paths = [self.root_path / p for p in watch_paths]
        self.ignore_patterns = ignore_patterns
        self.debounce_ms = debounce_ms

        self._observations: deque[Observation] = deque(maxlen=1000)
        self._watch_task: Optional[asyncio.Task] = None
        self._running = False

    def _should_ignore(self, path: Path) -> bool:
        """Check if path matches any ignore pattern."""
        path_str = str(path)
        for pattern in self.ignore_patterns:
            if fnmatch(path_str, f"*{pattern}*"):
                return True
            if fnmatch(path.name, pattern):
                return True
        return False

    def _change_to_event_type(self, change: Change) -> EventType:
        """Map watchfiles Change to EventType."""
        if change == Change.added:
            return EventType.FILE_CREATED
        elif change == Change.modified:
            return EventType.FILE_MODIFIED
        elif change == Change.deleted:
            return EventType.FILE_DELETED
        return EventType.FILE_MODIFIED

    def _calculate_priority(self, path: Path, event_type: EventType) -> float:
        """
        Calculate observation priority based on file characteristics.

        Higher priority for:
        - Configuration files
        - Source code changes
        - New files (creates)
        - Files in watched directories
        """
        priority = 0.5

        # Boost for creates and deletes
        if event_type == EventType.FILE_CREATED:
            priority += 0.2
        elif event_type == EventType.FILE_DELETED:
            priority += 0.1

        # Boost for important file types
        suffix = path.suffix.lower()
        if suffix in {".py", ".ts", ".js", ".md", ".yaml", ".yml", ".json"}:
            priority += 0.1

        # Boost for config files
        if path.name in {"pyproject.toml", "package.json", "CLAUDE.md", ".env"}:
            priority += 0.2

        return min(1.0, priority)

    async def _watch_loop(self) -> None:
        """Main watch loop using watchfiles."""
        try:
            async for changes in awatch(
                *self.watch_paths,
                debounce=self.debounce_ms,
                recursive=True,
            ):
                if not self._running:
                    break

                for change, path_str in changes:
                    path = Path(path_str)

                    if self._should_ignore(path):
                        continue

                    event_type = self._change_to_event_type(change)
                    priority = self._calculate_priority(path, event_type)

                    observation = Observation(
                        event_type=event_type,
                        source=self.id,
                        level=self.level,
                        priority=priority,
                        payload={
                            "path": str(path.relative_to(self.root_path)),
                            "absolute_path": str(path),
                            "change_type": change.name,
                            "exists": path.exists(),
                            "is_dir": path.is_dir() if path.exists() else False,
                            "suffix": path.suffix,
                            "size": path.stat().st_size if path.exists() and path.is_file() else 0,
                        },
                    )

                    self._observations.append(observation)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            # Log error but don't crash
            self._observations.append(Observation(
                event_type=EventType.ANOMALY_DETECTED,
                source=self.id,
                level=ObserverLevel.METACOGNITIVE,
                priority=0.8,
                payload={"error": str(e), "type": "observer_error"},
            ))

    async def start(self) -> None:
        """Start file system observation."""
        if self._running:
            return

        self._running = True
        self._watch_task = asyncio.create_task(self._watch_loop())

    async def stop(self) -> None:
        """Stop file system observation."""
        self._running = False
        if self._watch_task:
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:
                pass

    async def get_observations(self) -> list[Observation]:
        """Get and clear pending observations."""
        observations = list(self._observations)
        self._observations.clear()
        return observations


# Protocol compliance check
_: ObserverProtocol = FileSystemObserver([], [])
