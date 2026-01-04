"""
Claude Code Executor - Executes decisions using Claude CLI via subprocess.

This is the KEY component of the Consciousness daemon. It does NOT use Anthropic API.
Instead, it uses the `claude` CLI via subprocess, leveraging the user's logged-in account.

Flow:
1. File watcher detects changes
2. LM Studio thinks and decides
3. Claude Code EXECUTES the decision (this module)
"""

import asyncio
import subprocess
import time
import json
import shutil
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from pathlib import Path
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """Mode of execution for Claude Code."""
    SIMPLE = "simple"  # Single claude --print command
    SWARM = "swarm"    # Claude Flow swarm orchestration


@dataclass
class ExecutionResult:
    """Result of a Claude Code execution."""
    success: bool
    output: str
    error: Optional[str] = None
    duration: float = 0.0
    mode: ExecutionMode = ExecutionMode.SIMPLE
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "duration": self.duration,
            "mode": self.mode.value,
            "metadata": self.metadata
        }


@dataclass
class SwarmConfig:
    """Configuration for Claude Flow swarm execution."""
    topology: str = "hierarchical"
    max_agents: int = 8
    strategy: str = "adaptive"
    priority: str = "medium"


class ClaudeCodeExecutor:
    """
    Executes tasks using Claude Code CLI via subprocess.

    Uses the `claude` CLI with --print flag for non-interactive output.
    Supports both simple tasks and Claude Flow swarm orchestration.
    """

    def __init__(
        self,
        working_dir: Path,
        timeout: int = 300,
        claude_path: Optional[str] = None,
        npx_path: Optional[str] = None
    ):
        """
        Initialize the Claude Code Executor.

        Args:
            working_dir: Working directory for command execution
            timeout: Default timeout in seconds (5 minutes)
            claude_path: Optional path to claude CLI (auto-detected if None)
            npx_path: Optional path to npx (auto-detected if None)
        """
        self.working_dir = Path(working_dir)
        self.timeout = timeout
        self.claude_path = claude_path or self._find_executable("claude")
        self.npx_path = npx_path or self._find_executable("npx")

        # Validate working directory exists
        if not self.working_dir.exists():
            self.working_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created working directory: {self.working_dir}")

    def _find_executable(self, name: str) -> str:
        """Find executable in PATH."""
        path = shutil.which(name)
        if path is None:
            logger.warning(f"Executable '{name}' not found in PATH")
            return name  # Return name anyway, will fail at execution time
        return path

    async def execute(
        self,
        prompt: str,
        output_format: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> ExecutionResult:
        """
        Execute a task using Claude Code CLI.

        Args:
            prompt: The prompt to send to Claude
            output_format: Optional output format (e.g., "json", "text")
            timeout: Optional timeout override in seconds

        Returns:
            ExecutionResult with success status, output, and metadata
        """
        start_time = time.time()
        effective_timeout = timeout or self.timeout

        # Build command
        cmd = [self.claude_path, "--print"]

        if output_format:
            cmd.extend(["--output-format", output_format])

        cmd.append(prompt)

        logger.debug(f"Executing Claude command: {' '.join(cmd[:3])}...")

        try:
            result = await self._run_subprocess(
                cmd,
                timeout=effective_timeout
            )

            duration = time.time() - start_time

            return ExecutionResult(
                success=result["returncode"] == 0,
                output=result["stdout"],
                error=result["stderr"] if result["returncode"] != 0 else None,
                duration=duration,
                mode=ExecutionMode.SIMPLE,
                metadata={
                    "command": "claude --print",
                    "returncode": result["returncode"],
                    "output_format": output_format
                }
            )

        except asyncio.TimeoutError:
            duration = time.time() - start_time
            logger.error(f"Claude execution timed out after {effective_timeout}s")
            return ExecutionResult(
                success=False,
                output="",
                error=f"Execution timed out after {effective_timeout} seconds",
                duration=duration,
                mode=ExecutionMode.SIMPLE,
                metadata={"timeout": True}
            )
        except Exception as e:
            duration = time.time() - start_time
            logger.exception(f"Claude execution failed: {e}")
            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
                duration=duration,
                mode=ExecutionMode.SIMPLE,
                metadata={"exception": type(e).__name__}
            )

    async def execute_swarm(
        self,
        task: str,
        config: Optional[SwarmConfig] = None,
        timeout: Optional[int] = None
    ) -> ExecutionResult:
        """
        Execute a Claude Flow swarm for complex tasks.

        Args:
            task: The task description for the swarm
            config: Optional SwarmConfig for swarm parameters
            timeout: Optional timeout override in seconds

        Returns:
            ExecutionResult with success status, output, and metadata
        """
        start_time = time.time()
        config = config or SwarmConfig()
        effective_timeout = timeout or self.timeout * 2  # Swarms get more time

        results: List[Dict[str, Any]] = []

        try:
            # Step 1: Initialize the swarm
            init_cmd = [
                self.npx_path, "claude-flow@alpha", "swarm", "init",
                "--topology", config.topology,
                "--max-agents", str(config.max_agents),
                "--strategy", config.strategy
            ]

            logger.debug(f"Initializing swarm with topology: {config.topology}")

            init_result = await self._run_subprocess(
                init_cmd,
                timeout=60  # 1 minute for init
            )

            results.append({
                "step": "swarm_init",
                "success": init_result["returncode"] == 0,
                "output": init_result["stdout"],
                "error": init_result["stderr"]
            })

            if init_result["returncode"] != 0:
                duration = time.time() - start_time
                return ExecutionResult(
                    success=False,
                    output=init_result["stdout"],
                    error=f"Swarm initialization failed: {init_result['stderr']}",
                    duration=duration,
                    mode=ExecutionMode.SWARM,
                    metadata={"steps": results}
                )

            # Step 2: Orchestrate the task
            orchestrate_cmd = [
                self.npx_path, "claude-flow@alpha", "task", "orchestrate",
                "--priority", config.priority,
                "--strategy", config.strategy,
                task
            ]

            logger.debug(f"Orchestrating task: {task[:50]}...")

            orchestrate_result = await self._run_subprocess(
                orchestrate_cmd,
                timeout=effective_timeout - 60  # Remaining time after init
            )

            results.append({
                "step": "task_orchestrate",
                "success": orchestrate_result["returncode"] == 0,
                "output": orchestrate_result["stdout"],
                "error": orchestrate_result["stderr"]
            })

            duration = time.time() - start_time

            # Combine outputs
            combined_output = "\n".join([
                r["output"] for r in results if r["output"]
            ])

            return ExecutionResult(
                success=orchestrate_result["returncode"] == 0,
                output=combined_output,
                error=orchestrate_result["stderr"] if orchestrate_result["returncode"] != 0 else None,
                duration=duration,
                mode=ExecutionMode.SWARM,
                metadata={
                    "steps": results,
                    "topology": config.topology,
                    "max_agents": config.max_agents,
                    "strategy": config.strategy
                }
            )

        except asyncio.TimeoutError:
            duration = time.time() - start_time
            logger.error(f"Swarm execution timed out after {effective_timeout}s")
            return ExecutionResult(
                success=False,
                output="\n".join([r.get("output", "") for r in results]),
                error=f"Swarm execution timed out after {effective_timeout} seconds",
                duration=duration,
                mode=ExecutionMode.SWARM,
                metadata={"steps": results, "timeout": True}
            )
        except Exception as e:
            duration = time.time() - start_time
            logger.exception(f"Swarm execution failed: {e}")
            return ExecutionResult(
                success=False,
                output="\n".join([r.get("output", "") for r in results]),
                error=str(e),
                duration=duration,
                mode=ExecutionMode.SWARM,
                metadata={"steps": results, "exception": type(e).__name__}
            )

    async def execute_with_context(
        self,
        prompt: str,
        context_files: List[Path],
        output_format: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> ExecutionResult:
        """
        Execute a task with file context.

        Reads the content of context files and includes them in the prompt.

        Args:
            prompt: The prompt to send to Claude
            context_files: List of file paths to include as context
            output_format: Optional output format
            timeout: Optional timeout override

        Returns:
            ExecutionResult with success status, output, and metadata
        """
        # Build context from files
        context_parts = []
        valid_files = []

        for file_path in context_files:
            path = Path(file_path)
            if path.exists() and path.is_file():
                try:
                    content = path.read_text(encoding='utf-8')
                    context_parts.append(f"--- {path.name} ---\n{content}")
                    valid_files.append(str(path))
                except Exception as e:
                    logger.warning(f"Failed to read context file {path}: {e}")

        # Build enhanced prompt with context
        if context_parts:
            context_str = "\n\n".join(context_parts)
            enhanced_prompt = f"""Context files:
{context_str}

Task:
{prompt}"""
        else:
            enhanced_prompt = prompt

        result = await self.execute(
            enhanced_prompt,
            output_format=output_format,
            timeout=timeout
        )

        # Add context metadata
        result.metadata["context_files"] = valid_files

        return result

    async def _run_subprocess(
        self,
        cmd: List[str],
        timeout: int
    ) -> Dict[str, Any]:
        """
        Run a subprocess asynchronously with timeout.

        Args:
            cmd: Command and arguments
            timeout: Timeout in seconds

        Returns:
            Dict with stdout, stderr, and returncode
        """
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.working_dir)
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            return {
                "stdout": stdout.decode('utf-8', errors='replace'),
                "stderr": stderr.decode('utf-8', errors='replace'),
                "returncode": process.returncode
            }
        except asyncio.TimeoutError:
            # Kill the process on timeout
            process.kill()
            await process.wait()
            raise

    def is_available(self) -> bool:
        """Check if Claude CLI is available."""
        try:
            result = subprocess.run(
                [self.claude_path, "--version"],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    def is_swarm_available(self) -> bool:
        """Check if Claude Flow (swarm) is available."""
        try:
            result = subprocess.run(
                [self.npx_path, "claude-flow@alpha", "--version"],
                capture_output=True,
                timeout=30
            )
            return result.returncode == 0
        except Exception:
            return False


class ExecutorPool:
    """
    Pool of executors for managing concurrent task execution.

    Useful when the daemon needs to handle multiple decisions simultaneously.
    """

    def __init__(
        self,
        working_dir: Path,
        max_concurrent: int = 3,
        timeout: int = 300
    ):
        """
        Initialize the executor pool.

        Args:
            working_dir: Working directory for execution
            max_concurrent: Maximum concurrent executions
            timeout: Default timeout per execution
        """
        self.working_dir = Path(working_dir)
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._executor = ClaudeCodeExecutor(working_dir, timeout)
        self._active_tasks: Dict[str, asyncio.Task] = {}

    async def execute(
        self,
        task_id: str,
        prompt: str,
        **kwargs
    ) -> ExecutionResult:
        """
        Execute a task with concurrency control.

        Args:
            task_id: Unique identifier for the task
            prompt: The prompt to execute
            **kwargs: Additional arguments for execute()

        Returns:
            ExecutionResult from the execution
        """
        async with self._semaphore:
            task = asyncio.current_task()
            if task:
                self._active_tasks[task_id] = task

            try:
                return await self._executor.execute(prompt, **kwargs)
            finally:
                self._active_tasks.pop(task_id, None)

    async def execute_swarm(
        self,
        task_id: str,
        task: str,
        **kwargs
    ) -> ExecutionResult:
        """
        Execute a swarm task with concurrency control.

        Args:
            task_id: Unique identifier for the task
            task: The task description
            **kwargs: Additional arguments for execute_swarm()

        Returns:
            ExecutionResult from the swarm execution
        """
        async with self._semaphore:
            current_task = asyncio.current_task()
            if current_task:
                self._active_tasks[task_id] = current_task

            try:
                return await self._executor.execute_swarm(task, **kwargs)
            finally:
                self._active_tasks.pop(task_id, None)

    def get_active_tasks(self) -> List[str]:
        """Get list of active task IDs."""
        return list(self._active_tasks.keys())

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task.

        Args:
            task_id: ID of the task to cancel

        Returns:
            True if task was cancelled, False if not found
        """
        task = self._active_tasks.get(task_id)
        if task:
            task.cancel()
            return True
        return False


# Convenience function for simple one-off execution
async def execute_claude(
    prompt: str,
    working_dir: Optional[Path] = None,
    timeout: int = 300
) -> ExecutionResult:
    """
    Convenience function for simple Claude execution.

    Args:
        prompt: The prompt to execute
        working_dir: Optional working directory (defaults to cwd)
        timeout: Timeout in seconds

    Returns:
        ExecutionResult from the execution
    """
    wd = working_dir or Path.cwd()
    executor = ClaudeCodeExecutor(wd, timeout)
    return await executor.execute(prompt)


# Example usage and testing
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG)

    async def main():
        # Create executor
        executor = ClaudeCodeExecutor(
            working_dir=Path.cwd(),
            timeout=60
        )

        # Check availability
        print(f"Claude CLI available: {executor.is_available()}")
        print(f"Claude Flow available: {executor.is_swarm_available()}")

        if not executor.is_available():
            print("Claude CLI not available. Please ensure 'claude' is installed.")
            sys.exit(1)

        # Simple execution test
        print("\n--- Simple Execution Test ---")
        result = await executor.execute(
            "Say 'Hello from consciousness daemon!' and nothing else.",
            timeout=30
        )

        print(f"Success: {result.success}")
        print(f"Duration: {result.duration:.2f}s")
        print(f"Output: {result.output[:200] if result.output else 'No output'}")
        if result.error:
            print(f"Error: {result.error}")

    asyncio.run(main())
