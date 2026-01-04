"""
Consciousness Observers - Multi-level Observation Hierarchy

Observer Levels (from implementation plan):
- Level 1 (Perceptual): File changes, process states, raw events
- Level 2 (Cognitive): Pattern recognition, anomaly detection, semantic meaning
- Level 3 (Meta-Cognitive): Self-observation, attention patterns, strategy evaluation

Each observer implements the ObserverProtocol and emits typed events.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol
from uuid import UUID, uuid4


class ObserverLevel(Enum):
    """Observer hierarchy levels."""
    PERCEPTUAL = 1   # Raw events, milliseconds-seconds
    COGNITIVE = 2     # Patterns, seconds-minutes
    METACOGNITIVE = 3 # Self-observation, minutes-hours


class EventType(Enum):
    """Types of observable events."""
    # File system events
    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    FILE_DELETED = "file_deleted"

    # Process events
    PROCESS_STARTED = "process_started"
    PROCESS_ENDED = "process_ended"
    TASK_COMPLETED = "task_completed"

    # Git events
    GIT_COMMIT = "git_commit"
    GIT_BRANCH_CHANGED = "git_branch_changed"
    GIT_PUSH = "git_push"

    # Meta events
    PATTERN_DETECTED = "pattern_detected"
    ANOMALY_DETECTED = "anomaly_detected"
    ATTENTION_SHIFT = "attention_shift"


@dataclass
class Observation:
    """A single observation from any observer."""
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_type: EventType = EventType.FILE_MODIFIED
    source: str = ""  # Observer ID
    level: ObserverLevel = ObserverLevel.PERCEPTUAL
    priority: float = 0.5  # 0.0 to 1.0
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "source": self.source,
            "level": self.level.value,
            "priority": self.priority,
            "payload": self.payload,
        }


class ObserverProtocol(Protocol):
    """Protocol that all observers must implement."""

    id: str
    level: ObserverLevel

    async def start(self) -> None:
        """Start observing."""
        ...

    async def stop(self) -> None:
        """Stop observing."""
        ...

    async def get_observations(self) -> list[Observation]:
        """Get pending observations (clears the queue)."""
        ...


__all__ = [
    "ObserverLevel",
    "EventType",
    "Observation",
    "ObserverProtocol",
]
