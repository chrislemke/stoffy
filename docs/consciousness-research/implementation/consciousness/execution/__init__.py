"""
Consciousness Execution - Task Delegation Layer

Implements the ACT phase of OIDA loop.
Delegates tasks to:
- Claude API (Anthropic SDK) for single tasks with tool use
- Claude Flow (optional) for multi-agent swarms
"""

from .claude_api import ClaudeExecutor, TaskResult
from .task_queue import TaskQueue, Task, TaskStatus

__all__ = [
    "ClaudeExecutor",
    "TaskResult",
    "TaskQueue",
    "Task",
    "TaskStatus",
]
