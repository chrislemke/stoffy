"""
Autonomous Executor - Executes tasks in fallback mode.

This executor handles task execution when operating in fallback mode,
routing to Claude Code or other execution backends based on task type.
It maintains autonomy even when the primary LM Studio backend is down.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

import structlog

from .task_intent import TaskIntent, IntentType, Urgency
from .gemini_consciousness import ConsciousnessThought

logger = structlog.get_logger(__name__)


@dataclass
class ExecutionResult:
    """Result of executing a task."""
    success: bool
    output: str
    error: Optional[str] = None
    duration_seconds: float = 0.0
    executor_used: str = ""
    files_created: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "output": self.output[:1000] if self.output else "",
            "error": self.error,
            "duration_seconds": self.duration_seconds,
            "executor_used": self.executor_used,
            "files_created": self.files_created,
            "files_modified": self.files_modified,
            "metadata": self.metadata,
        }


@dataclass
class ExecutorConfig:
    """Configuration for the autonomous executor."""
    # Timeouts
    default_timeout: int = 300
    claude_timeout: int = 600

    # Execution settings
    max_output_size: int = 100_000
    working_dir: Optional[Path] = None

    # Safety
    allow_file_deletion: bool = False
    blocked_patterns: List[str] = field(default_factory=lambda: [
        "rm -rf /", "sudo rm", "> /dev"
    ])


class AutonomousExecutor:
    """
    Executes tasks autonomously in fallback mode.

    Routes execution requests to appropriate backends:
    - Claude Code for code execution and complex tasks
    - Direct execution for simple file/bash operations
    - Gemini for analysis-only tasks (no execution)

    Maintains full autonomy even without LM Studio.
    """

    def __init__(
        self,
        working_dir: Path,
        config: Optional[ExecutorConfig] = None,
    ):
        """
        Initialize the executor.

        Args:
            working_dir: Working directory for execution
            config: Executor configuration
        """
        self.working_dir = Path(working_dir).resolve()
        self.config = config or ExecutorConfig()

        if self.config.working_dir is None:
            self.config.working_dir = self.working_dir

        # Import here to avoid circular imports
        self._claude_executor = None
        self._initialized = False

        # Statistics
        self._execution_count = 0
        self._success_count = 0
        self._failure_count = 0

    async def initialize(self) -> None:
        """Initialize execution backends."""
        if self._initialized:
            return

        try:
            # Import executor from parent package
            from ..executor import ExpandedExecutor, ExecutionConfig

            self._claude_executor = ExpandedExecutor(
                working_dir=self.working_dir,
                config=ExecutionConfig(
                    default_timeout=self.config.default_timeout,
                    claude_timeout=self.config.claude_timeout,
                    allow_delete=self.config.allow_file_deletion,
                ),
            )
            self._initialized = True
            logger.info("autonomous_executor.initialized")

        except Exception as e:
            logger.error(f"autonomous_executor.init_error: {e}")

    async def execute_from_thought(
        self,
        thought: ConsciousnessThought,
        intent: Optional[TaskIntent] = None,
    ) -> ExecutionResult:
        """
        Execute an action based on a consciousness thought.

        Args:
            thought: The thought that suggested an action
            intent: Optional classified intent

        Returns:
            ExecutionResult
        """
        await self.initialize()

        if not thought.suggested_action:
            return ExecutionResult(
                success=True,
                output="No action needed",
                executor_used="none",
            )

        # Determine execution method based on thought and intent
        if thought.conclusion == "wait":
            return ExecutionResult(
                success=True,
                output="Decided to wait - no action taken",
                executor_used="none",
            )

        if thought.conclusion == "investigate":
            # Investigation doesn't execute, just records intent
            return ExecutionResult(
                success=True,
                output=f"Investigation noted: {thought.suggested_action}",
                executor_used="none",
                metadata={"investigation": thought.suggested_action},
            )

        # Execute the suggested action
        return await self.execute_claude_code(thought.suggested_action)

    async def execute_claude_code(
        self,
        prompt: str,
        timeout: Optional[int] = None,
    ) -> ExecutionResult:
        """
        Execute a task using Claude Code.

        Args:
            prompt: The prompt/task for Claude Code
            timeout: Optional timeout override

        Returns:
            ExecutionResult
        """
        await self.initialize()

        if not self._claude_executor:
            return ExecutionResult(
                success=False,
                output="",
                error="Claude executor not initialized",
                executor_used="claude_code",
            )

        start_time = datetime.now(timezone.utc)
        self._execution_count += 1

        try:
            from ..executor import Action, ActionType

            result = await self._claude_executor.execute(Action(
                type=ActionType.CLAUDE_CODE,
                details={"prompt": prompt},
                timeout=timeout or self.config.claude_timeout,
            ))

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            if result.success:
                self._success_count += 1
            else:
                self._failure_count += 1

            return ExecutionResult(
                success=result.success,
                output=result.output[:self.config.max_output_size],
                error=result.error,
                duration_seconds=duration,
                executor_used="claude_code",
                files_created=result.files_created,
                files_modified=result.files_modified,
            )

        except Exception as e:
            self._failure_count += 1
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
                duration_seconds=duration,
                executor_used="claude_code",
            )

    async def execute_bash(
        self,
        command: str,
        timeout: Optional[int] = None,
    ) -> ExecutionResult:
        """
        Execute a bash command directly.

        Args:
            command: Bash command to execute
            timeout: Optional timeout

        Returns:
            ExecutionResult
        """
        # Safety check
        for pattern in self.config.blocked_patterns:
            if pattern in command:
                return ExecutionResult(
                    success=False,
                    output="",
                    error=f"Command blocked: contains '{pattern}'",
                    executor_used="bash",
                )

        start_time = datetime.now(timezone.utc)
        self._execution_count += 1

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.working_dir),
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout or self.config.default_timeout,
            )

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            success = process.returncode == 0

            if success:
                self._success_count += 1
            else:
                self._failure_count += 1

            return ExecutionResult(
                success=success,
                output=stdout.decode("utf-8", errors="replace")[:self.config.max_output_size],
                error=stderr.decode("utf-8", errors="replace") if not success else None,
                duration_seconds=duration,
                executor_used="bash",
            )

        except asyncio.TimeoutError:
            self._failure_count += 1
            return ExecutionResult(
                success=False,
                output="",
                error="Command timed out",
                duration_seconds=timeout or self.config.default_timeout,
                executor_used="bash",
            )
        except Exception as e:
            self._failure_count += 1
            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
                executor_used="bash",
            )

    async def execute_python(
        self,
        code: str,
        timeout: Optional[int] = None,
    ) -> ExecutionResult:
        """
        Execute Python code.

        Args:
            code: Python code to execute
            timeout: Optional timeout

        Returns:
            ExecutionResult
        """
        start_time = datetime.now(timezone.utc)
        self._execution_count += 1

        try:
            process = await asyncio.create_subprocess_exec(
                "python3", "-c", code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.working_dir),
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout or self.config.default_timeout,
            )

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            success = process.returncode == 0

            if success:
                self._success_count += 1
            else:
                self._failure_count += 1

            return ExecutionResult(
                success=success,
                output=stdout.decode("utf-8", errors="replace")[:self.config.max_output_size],
                error=stderr.decode("utf-8", errors="replace") if not success else None,
                duration_seconds=duration,
                executor_used="python",
            )

        except asyncio.TimeoutError:
            self._failure_count += 1
            return ExecutionResult(
                success=False,
                output="",
                error="Python execution timed out",
                duration_seconds=timeout or self.config.default_timeout,
                executor_used="python",
            )
        except Exception as e:
            self._failure_count += 1
            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
                executor_used="python",
            )

    async def write_file(
        self,
        path: str,
        content: str,
    ) -> ExecutionResult:
        """
        Write content to a file.

        Args:
            path: File path (relative to working dir)
            content: Content to write

        Returns:
            ExecutionResult
        """
        self._execution_count += 1

        try:
            file_path = self.working_dir / path
            file_path.parent.mkdir(parents=True, exist_ok=True)

            is_new = not file_path.exists()
            file_path.write_text(content, encoding="utf-8")

            self._success_count += 1

            result = ExecutionResult(
                success=True,
                output=f"Wrote {len(content)} bytes to {path}",
                executor_used="file_write",
            )

            if is_new:
                result.files_created = [str(file_path)]
            else:
                result.files_modified = [str(file_path)]

            return result

        except Exception as e:
            self._failure_count += 1
            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
                executor_used="file_write",
            )

    def get_statistics(self) -> dict:
        """Get execution statistics."""
        return {
            "execution_count": self._execution_count,
            "success_count": self._success_count,
            "failure_count": self._failure_count,
            "success_rate": (
                self._success_count / self._execution_count
                if self._execution_count > 0 else 0.0
            ),
            "initialized": self._initialized,
            "working_dir": str(self.working_dir),
        }


if __name__ == "__main__":
    async def test():
        print("Testing Autonomous Executor...")

        executor = AutonomousExecutor(
            working_dir=Path.cwd(),
        )

        await executor.initialize()

        # Test bash
        result = await executor.execute_bash("echo 'Hello from executor!'")
        print(f"\nBash result: {result.to_dict()}")

        # Test Python
        result = await executor.execute_python("print(2 + 2)")
        print(f"\nPython result: {result.to_dict()}")

        print(f"\nStatistics: {executor.get_statistics()}")

    asyncio.run(test())
