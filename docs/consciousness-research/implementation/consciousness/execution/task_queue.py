"""
Task Queue - Prioritized Task Management

Manages delegated tasks with:
- Priority ordering (critical > high > medium > low)
- Concurrency limits
- Retry logic
- Status tracking
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from ..inference.lm_studio import Action


class TaskStatus(Enum):
    """Task lifecycle states."""
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3

    @classmethod
    def from_string(cls, s: str) -> "TaskPriority":
        return cls[s.upper()]


@dataclass
class Task:
    """A task in the queue."""
    id: UUID = field(default_factory=uuid4)
    action: Action = field(default_factory=lambda: Action(
        type="internal",
        description="",
        prompt="",
    ))
    status: TaskStatus = TaskStatus.CREATED
    priority: TaskPriority = TaskPriority.MEDIUM
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    retries: int = 0
    max_retries: int = 3
    metadata: dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other: "Task") -> bool:
        """Enable priority queue ordering."""
        # Higher priority first, then earlier created
        if self.priority != other.priority:
            return self.priority.value > other.priority.value
        return self.created_at < other.created_at


class TaskQueue:
    """
    Priority queue for task management.

    Features:
    - Automatic priority ordering
    - Concurrency control
    - Retry on failure
    - Status callbacks
    """

    def __init__(
        self,
        max_concurrent: int = 5,
        max_queue_size: int = 100,
        default_timeout: int = 600,
    ):
        self.max_concurrent = max_concurrent
        self.max_queue_size = max_queue_size
        self.default_timeout = default_timeout

        self._queue: list[Task] = []
        self._running: dict[UUID, Task] = {}
        self._completed: list[Task] = []
        self._lock = asyncio.Lock()

    async def add(self, action: Action) -> Task:
        """Add a task to the queue."""
        async with self._lock:
            if len(self._queue) >= self.max_queue_size:
                # Remove lowest priority task
                self._queue.sort()
                self._queue.pop()

            task = Task(
                action=action,
                status=TaskStatus.QUEUED,
                priority=TaskPriority.from_string(action.priority),
            )
            self._queue.append(task)
            self._queue.sort()

            return task

    async def get_next(self) -> Optional[Task]:
        """Get the next task to execute."""
        async with self._lock:
            if not self._queue:
                return None

            if len(self._running) >= self.max_concurrent:
                return None

            task = self._queue.pop(0)
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.utcnow()
            self._running[task.id] = task

            return task

    async def complete(
        self,
        task_id: UUID,
        result: Any,
        success: bool = True,
    ) -> None:
        """Mark a task as completed."""
        async with self._lock:
            task = self._running.pop(task_id, None)
            if task:
                task.completed_at = datetime.utcnow()
                task.result = result

                if success:
                    task.status = TaskStatus.COMPLETED
                else:
                    task.error = str(result)
                    if task.retries < task.max_retries:
                        task.retries += 1
                        task.status = TaskStatus.QUEUED
                        self._queue.append(task)
                        self._queue.sort()
                    else:
                        task.status = TaskStatus.FAILED

                self._completed.append(task)

    async def cancel(self, task_id: UUID) -> bool:
        """Cancel a task."""
        async with self._lock:
            # Check queue
            for i, task in enumerate(self._queue):
                if task.id == task_id:
                    task.status = TaskStatus.CANCELLED
                    self._queue.pop(i)
                    self._completed.append(task)
                    return True

            # Check running (can't cancel running tasks directly)
            if task_id in self._running:
                return False

            return False

    @property
    def active_count(self) -> int:
        """Number of currently running tasks."""
        return len(self._running)

    @property
    def pending_count(self) -> int:
        """Number of tasks waiting in queue."""
        return len(self._queue)

    def get_status(self) -> dict[str, Any]:
        """Get queue status summary."""
        return {
            "queued": len(self._queue),
            "running": len(self._running),
            "completed": len([t for t in self._completed if t.status == TaskStatus.COMPLETED]),
            "failed": len([t for t in self._completed if t.status == TaskStatus.FAILED]),
            "cancelled": len([t for t in self._completed if t.status == TaskStatus.CANCELLED]),
        }

    def get_running_tasks(self) -> list[Task]:
        """Get list of currently running tasks."""
        return list(self._running.values())
