"""
Claude Code Executor - Executes decisions using Claude CLI via subprocess.

This is the KEY component of the Consciousness daemon. It does NOT use Anthropic API.
Instead, it uses the `claude` CLI via subprocess, leveraging the user's logged-in account.

EXPANDED CAPABILITIES (v0.2.0):
- File operations: write, edit, delete files
- Code execution: Python, TypeScript, Bash, custom scripts
- Claude delegation: Claude Code and Claude Flow for heavy tasks
- Thinking: Internal reasoning, debates, research
- Custom scripts: Write and execute on the fly

Flow:
1. File watcher detects changes
2. LM Studio thinks and decides
3. Executor EXECUTES the decision (this module)

Safety:
- Path validation (stay within project)
- Timeout limits on all operations
- Resource limits for code execution
- Sandboxing considerations documented
"""

import asyncio
import subprocess
import time
import json
import shutil
import tempfile
import os
import stat
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
from enum import Enum
import logging
import hashlib

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class ExecutionMode(Enum):
    """Mode of execution for Claude Code."""
    SIMPLE = "simple"      # Single claude --print command
    SWARM = "swarm"        # Claude Flow swarm orchestration
    DIRECT = "direct"      # Direct file/code operations


class ActionType(Enum):
    """
    Comprehensive action types the executor can handle.

    Categories:
    - File operations: WRITE_FILE, EDIT_FILE, READ_FILE, DELETE_FILE
    - Code execution: RUN_PYTHON, RUN_TYPESCRIPT, RUN_BASH, RUN_NODE
    - Claude delegation: CLAUDE_CODE, CLAUDE_FLOW
    - Thinking: THINK, DEBATE, RESEARCH, DISCUSS
    - Custom: CUSTOM_SCRIPT
    """
    # File operations
    WRITE_FILE = "write_file"
    EDIT_FILE = "edit_file"
    READ_FILE = "read_file"
    DELETE_FILE = "delete_file"
    CREATE_DIRECTORY = "create_directory"

    # Code execution
    RUN_PYTHON = "run_python"
    RUN_TYPESCRIPT = "run_typescript"
    RUN_BASH = "run_bash"
    RUN_NODE = "run_node"

    # Claude delegation
    CLAUDE_CODE = "claude_code"
    CLAUDE_FLOW = "claude_flow"

    # Gemini delegation (Tier 4 - Librarian)
    GEMINI_ANALYZE = "gemini_analyze"

    # Thinking and discussion
    THINK = "think"             # Internal reasoning
    DEBATE = "debate"           # Spawn a debate between thinkers
    RESEARCH = "research"       # Deep research on a topic
    DISCUSS = "discuss"         # Multi-perspective discussion

    # Custom operations
    CUSTOM_SCRIPT = "custom_script"
    SHELL_COMMAND = "shell_command"


class Priority(Enum):
    """Priority levels for actions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ExecutionResult:
    """Result of any execution."""
    success: bool
    output: str
    error: Optional[str] = None
    duration: float = 0.0
    mode: ExecutionMode = ExecutionMode.SIMPLE
    action_type: Optional[ActionType] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Additional result fields
    files_created: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    files_deleted: List[str] = field(default_factory=list)
    return_code: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "duration": self.duration,
            "mode": self.mode.value,
            "action_type": self.action_type.value if self.action_type else None,
            "metadata": self.metadata,
            "files_created": self.files_created,
            "files_modified": self.files_modified,
            "files_deleted": self.files_deleted,
            "return_code": self.return_code,
        }

    @classmethod
    def failure(cls, error: str, action_type: Optional[ActionType] = None) -> "ExecutionResult":
        """Create a failure result."""
        return cls(
            success=False,
            output="",
            error=error,
            action_type=action_type
        )

    @classmethod
    def success_result(
        cls,
        output: str,
        action_type: Optional[ActionType] = None,
        **kwargs
    ) -> "ExecutionResult":
        """Create a success result."""
        return cls(
            success=True,
            output=output,
            action_type=action_type,
            **kwargs
        )


@dataclass
class Action:
    """
    Represents an action to be executed.

    Expanded to support all action types with their specific details.
    """
    type: ActionType
    details: Dict[str, Any] = field(default_factory=dict)
    priority: Priority = Priority.MEDIUM
    timeout: Optional[int] = None  # Override default timeout

    # For backwards compatibility
    prompt: str = ""

    def __post_init__(self):
        # If prompt is set but details isn't, migrate it
        if self.prompt and "prompt" not in self.details:
            self.details["prompt"] = self.prompt

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "details": self.details,
            "priority": self.priority.value,
            "timeout": self.timeout,
            "prompt": self.prompt,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Action":
        return cls(
            type=ActionType(data.get("type", "claude_code")),
            details=data.get("details", {}),
            priority=Priority(data.get("priority", "medium")),
            timeout=data.get("timeout"),
            prompt=data.get("prompt", ""),
        )

    # Factory methods for common action types
    @classmethod
    def write_file(cls, path: str, content: str, priority: Priority = Priority.MEDIUM) -> "Action":
        """Create a write file action."""
        return cls(
            type=ActionType.WRITE_FILE,
            details={"path": path, "content": content},
            priority=priority
        )

    @classmethod
    def run_python(cls, code: str, priority: Priority = Priority.MEDIUM) -> "Action":
        """Create a run Python action."""
        return cls(
            type=ActionType.RUN_PYTHON,
            details={"code": code},
            priority=priority
        )

    @classmethod
    def claude_code(cls, prompt: str, priority: Priority = Priority.MEDIUM) -> "Action":
        """Create a Claude Code action."""
        return cls(
            type=ActionType.CLAUDE_CODE,
            details={"prompt": prompt},
            prompt=prompt,
            priority=priority
        )

    @classmethod
    def debate(cls, topic: str, thinkers: List[str], priority: Priority = Priority.MEDIUM) -> "Action":
        """Create a debate action."""
        return cls(
            type=ActionType.DEBATE,
            details={"topic": topic, "thinkers": thinkers},
            priority=priority
        )

    @classmethod
    def gemini_analyze(
        cls,
        prompt: str,
        files: Optional[List[str]] = None,
        context: Optional[str] = None,
        model: str = "gemini-1.5-pro",
        priority: Priority = Priority.MEDIUM
    ) -> "Action":
        """
        Create a Gemini analysis action (Tier 4 - Librarian).

        Gemini excels at analyzing massive context (2M+ tokens) for:
        - Document summarization
        - Log analysis
        - Pattern finding in large datasets
        - Historical data analysis

        WARNING: Medium/Low trust - verify code output with Claude.

        Args:
            prompt: Analysis prompt
            files: Optional list of file paths to include as context
            context: Optional large text context
            model: Gemini model (gemini-1.5-pro, gemini-1.5-flash, etc.)
            priority: Action priority

        Returns:
            Action configured for Gemini analysis
        """
        return cls(
            type=ActionType.GEMINI_ANALYZE,
            details={
                "prompt": prompt,
                "files": files or [],
                "context": context,
                "model": model,
            },
            priority=priority,
            timeout=900  # 15 minutes for large context processing
        )


@dataclass
class SwarmConfig:
    """Configuration for Claude Flow swarm execution."""
    topology: str = "hierarchical"
    max_agents: int = 8
    strategy: str = "adaptive"
    priority: str = "medium"


@dataclass
class ExecutionConfig:
    """Configuration for the executor."""
    # Timeouts (in seconds)
    default_timeout: int = 300
    file_operation_timeout: int = 30
    code_execution_timeout: int = 120
    claude_timeout: int = 600
    gemini_timeout: int = 900  # 15 minutes for large context processing

    # Limits
    max_output_size: int = 1_000_000  # 1MB
    max_file_size: int = 10_000_000   # 10MB

    # Security
    allow_delete: bool = False        # Require explicit enable
    allow_shell: bool = True
    sandbox_code: bool = False        # Future: run code in sandbox

    # Paths
    temp_dir: Optional[Path] = None

    # Blocked patterns for safety
    blocked_paths: List[str] = field(default_factory=lambda: [
        "/etc", "/usr", "/bin", "/sbin", "/var", "/root",
        "~/.ssh", "~/.aws", "~/.config"
    ])

    blocked_commands: List[str] = field(default_factory=lambda: [
        "rm -rf /", "rm -rf ~", "sudo", "> /dev",
        "chmod 777", "curl | bash", "wget | sh"
    ])


# =============================================================================
# MAIN EXECUTOR CLASS
# =============================================================================

class ExpandedExecutor:
    """
    Expanded executor that handles all action types.

    This is the main executor class that routes actions to appropriate handlers.
    """

    def __init__(
        self,
        working_dir: Path,
        config: Optional[ExecutionConfig] = None,
        claude_path: Optional[str] = None,
        npx_path: Optional[str] = None
    ):
        """
        Initialize the Expanded Executor.

        Args:
            working_dir: Working directory for command execution
            config: Execution configuration
            claude_path: Optional path to claude CLI
            npx_path: Optional path to npx
        """
        self.working_dir = Path(working_dir).resolve()
        self.config = config or ExecutionConfig()
        self.claude_path = claude_path or self._find_executable("claude")
        self.npx_path = npx_path or self._find_executable("npx")
        self.python_path = self._find_executable("python3") or self._find_executable("python")
        self.node_path = self._find_executable("node")
        self.ts_node_path = self._find_executable("ts-node") or self._find_executable("npx")

        # Ensure working directory exists
        if not self.working_dir.exists():
            self.working_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created working directory: {self.working_dir}")

        # Create temp directory if not specified
        if self.config.temp_dir is None:
            self.config.temp_dir = self.working_dir / ".consciousness" / "temp"
        self.config.temp_dir.mkdir(parents=True, exist_ok=True)

    def _find_executable(self, name: str) -> Optional[str]:
        """Find executable in PATH."""
        path = shutil.which(name)
        if path is None:
            logger.debug(f"Executable '{name}' not found in PATH")
        return path

    def _validate_path(self, path: Union[str, Path]) -> Path:
        """
        Validate that a path is safe to operate on.

        Args:
            path: Path to validate

        Returns:
            Resolved absolute path

        Raises:
            ValueError: If path is outside working directory or blocked
        """
        # Resolve to absolute path
        if isinstance(path, str):
            path = Path(path)

        if not path.is_absolute():
            path = self.working_dir / path

        path = path.resolve()

        # Check if within working directory
        try:
            path.relative_to(self.working_dir)
        except ValueError:
            raise ValueError(
                f"Path {path} is outside working directory {self.working_dir}"
            )

        # Check blocked patterns
        path_str = str(path)
        for blocked in self.config.blocked_paths:
            if blocked.startswith("~"):
                blocked = str(Path.home() / blocked[2:])
            if path_str.startswith(blocked):
                raise ValueError(f"Path {path} matches blocked pattern {blocked}")

        return path

    def _validate_command(self, command: str) -> None:
        """
        Validate that a command is safe to execute.

        Args:
            command: Command string to validate

        Raises:
            ValueError: If command matches blocked patterns
        """
        for blocked in self.config.blocked_commands:
            if blocked in command:
                raise ValueError(f"Command contains blocked pattern: {blocked}")

    # =========================================================================
    # MAIN EXECUTE METHOD
    # =========================================================================

    async def execute(self, action: Action) -> ExecutionResult:
        """
        Execute an action based on its type.

        This is the main entry point that routes to specific handlers.

        Args:
            action: The action to execute

        Returns:
            ExecutionResult with success status, output, and metadata
        """
        start_time = time.time()

        logger.info(f"Executing action: {action.type.value} (priority: {action.priority.value})")

        try:
            # Route to appropriate handler
            result = await self._route_action(action)

        except ValueError as e:
            # Validation errors
            result = ExecutionResult.failure(f"Validation error: {e}", action.type)

        except asyncio.TimeoutError:
            result = ExecutionResult.failure(
                f"Action timed out after {action.timeout or self.config.default_timeout}s",
                action.type
            )

        except Exception as e:
            logger.exception(f"Action execution failed: {e}")
            result = ExecutionResult.failure(str(e), action.type)

        # Set duration
        result.duration = time.time() - start_time

        return result

    async def _route_action(self, action: Action) -> ExecutionResult:
        """Route action to appropriate handler."""
        handlers = {
            # File operations
            ActionType.WRITE_FILE: self._write_file,
            ActionType.EDIT_FILE: self._edit_file,
            ActionType.READ_FILE: self._read_file,
            ActionType.DELETE_FILE: self._delete_file,
            ActionType.CREATE_DIRECTORY: self._create_directory,

            # Code execution
            ActionType.RUN_PYTHON: self._run_python,
            ActionType.RUN_TYPESCRIPT: self._run_typescript,
            ActionType.RUN_BASH: self._run_bash,
            ActionType.RUN_NODE: self._run_node,

            # Claude delegation
            ActionType.CLAUDE_CODE: self._claude_code,
            ActionType.CLAUDE_FLOW: self._claude_flow,

            # Gemini delegation (Tier 4)
            ActionType.GEMINI_ANALYZE: self._execute_gemini,

            # Thinking
            ActionType.THINK: self._think,
            ActionType.DEBATE: self._spawn_debate,
            ActionType.RESEARCH: self._research,
            ActionType.DISCUSS: self._discuss,

            # Custom
            ActionType.CUSTOM_SCRIPT: self._run_custom_script,
            ActionType.SHELL_COMMAND: self._run_shell_command,
        }

        handler = handlers.get(action.type)
        if handler is None:
            return ExecutionResult.failure(f"Unknown action type: {action.type}", action.type)

        return await handler(action)

    # =========================================================================
    # FILE OPERATIONS
    # =========================================================================

    async def _write_file(self, action: Action) -> ExecutionResult:
        """
        Write content to a file.

        Details:
            - path: File path (relative to working_dir or absolute)
            - content: Content to write
            - mode: 'w' (overwrite) or 'a' (append), default 'w'
            - encoding: File encoding, default 'utf-8'
        """
        details = action.details
        path = self._validate_path(details.get("path", ""))
        content = details.get("content", "")
        mode = details.get("mode", "w")
        encoding = details.get("encoding", "utf-8")

        # Check file size
        if len(content.encode(encoding)) > self.config.max_file_size:
            return ExecutionResult.failure(
                f"Content exceeds max file size ({self.config.max_file_size} bytes)",
                ActionType.WRITE_FILE
            )

        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Determine if creating or modifying
        is_new = not path.exists()

        # Write file
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: path.write_text(content, encoding=encoding) if mode == "w"
                    else self._append_file(path, content, encoding)
        )

        result = ExecutionResult.success_result(
            f"Written {len(content)} bytes to {path}",
            ActionType.WRITE_FILE,
            metadata={"path": str(path), "size": len(content), "mode": mode}
        )

        if is_new:
            result.files_created = [str(path)]
        else:
            result.files_modified = [str(path)]

        return result

    def _append_file(self, path: Path, content: str, encoding: str) -> None:
        """Append content to a file."""
        with open(path, "a", encoding=encoding) as f:
            f.write(content)

    async def _edit_file(self, action: Action) -> ExecutionResult:
        """
        Edit a file with search/replace or line-based edits.

        Details:
            - path: File path
            - edits: List of {search: str, replace: str} or {line: int, content: str}
            - backup: Whether to create backup, default True
        """
        details = action.details
        path = self._validate_path(details.get("path", ""))
        edits = details.get("edits", [])
        backup = details.get("backup", True)

        if not path.exists():
            return ExecutionResult.failure(f"File not found: {path}", ActionType.EDIT_FILE)

        # Read current content
        content = path.read_text()

        # Create backup if requested
        if backup:
            backup_path = path.with_suffix(path.suffix + ".bak")
            backup_path.write_text(content)

        # Apply edits
        for edit in edits:
            if "search" in edit and "replace" in edit:
                content = content.replace(edit["search"], edit["replace"])
            elif "line" in edit and "content" in edit:
                lines = content.split("\n")
                line_num = edit["line"] - 1  # 0-indexed
                if 0 <= line_num < len(lines):
                    lines[line_num] = edit["content"]
                    content = "\n".join(lines)

        # Write back
        path.write_text(content)

        return ExecutionResult.success_result(
            f"Applied {len(edits)} edits to {path}",
            ActionType.EDIT_FILE,
            files_modified=[str(path)],
            metadata={"path": str(path), "edits_count": len(edits)}
        )

    async def _read_file(self, action: Action) -> ExecutionResult:
        """
        Read a file's content.

        Details:
            - path: File path
            - encoding: File encoding, default 'utf-8'
            - lines: Optional tuple (start, end) for line range
        """
        details = action.details
        path = self._validate_path(details.get("path", ""))
        encoding = details.get("encoding", "utf-8")
        lines = details.get("lines")

        if not path.exists():
            return ExecutionResult.failure(f"File not found: {path}", ActionType.READ_FILE)

        content = path.read_text(encoding=encoding)

        if lines:
            start, end = lines
            content_lines = content.split("\n")
            content = "\n".join(content_lines[start-1:end])

        return ExecutionResult.success_result(
            content,
            ActionType.READ_FILE,
            metadata={"path": str(path), "size": len(content)}
        )

    async def _delete_file(self, action: Action) -> ExecutionResult:
        """
        Delete a file.

        Details:
            - path: File path
            - force: Whether to ignore if file doesn't exist, default False
        """
        if not self.config.allow_delete:
            return ExecutionResult.failure(
                "File deletion is disabled in configuration",
                ActionType.DELETE_FILE
            )

        details = action.details
        path = self._validate_path(details.get("path", ""))
        force = details.get("force", False)

        if not path.exists():
            if force:
                return ExecutionResult.success_result(
                    f"File already deleted: {path}",
                    ActionType.DELETE_FILE
                )
            return ExecutionResult.failure(f"File not found: {path}", ActionType.DELETE_FILE)

        # Backup before delete
        backup_path = self.config.temp_dir / f"deleted_{path.name}_{int(time.time())}"
        shutil.copy2(path, backup_path)

        path.unlink()

        return ExecutionResult.success_result(
            f"Deleted {path} (backup at {backup_path})",
            ActionType.DELETE_FILE,
            files_deleted=[str(path)],
            metadata={"path": str(path), "backup": str(backup_path)}
        )

    async def _create_directory(self, action: Action) -> ExecutionResult:
        """
        Create a directory.

        Details:
            - path: Directory path
            - parents: Whether to create parent directories, default True
            - exist_ok: Whether to ignore if exists, default True
        """
        details = action.details
        path = self._validate_path(details.get("path", ""))
        parents = details.get("parents", True)
        exist_ok = details.get("exist_ok", True)

        path.mkdir(parents=parents, exist_ok=exist_ok)

        return ExecutionResult.success_result(
            f"Created directory: {path}",
            ActionType.CREATE_DIRECTORY,
            files_created=[str(path)],
            metadata={"path": str(path)}
        )

    # =========================================================================
    # CODE EXECUTION
    # =========================================================================

    async def _run_python(self, action: Action) -> ExecutionResult:
        """
        Execute Python code.

        Details:
            - code: Python code to execute
            - file: Optional file path to execute instead of code
            - args: Optional list of arguments
            - venv: Optional virtual environment path
        """
        details = action.details
        code = details.get("code")
        file_path = details.get("file")
        args = details.get("args", [])
        venv = details.get("venv")

        if not self.python_path:
            return ExecutionResult.failure(
                "Python not found in PATH",
                ActionType.RUN_PYTHON
            )

        python_cmd = self.python_path

        # Use venv if specified
        if venv:
            venv_python = Path(venv) / "bin" / "python"
            if venv_python.exists():
                python_cmd = str(venv_python)

        if code:
            # Write code to temp file and execute
            temp_file = self.config.temp_dir / f"script_{int(time.time())}.py"
            temp_file.write_text(code)

            cmd = [python_cmd, str(temp_file)] + args
        elif file_path:
            path = self._validate_path(file_path)
            cmd = [python_cmd, str(path)] + args
        else:
            return ExecutionResult.failure(
                "Either 'code' or 'file' must be provided",
                ActionType.RUN_PYTHON
            )

        result = await self._run_subprocess(
            cmd,
            timeout=action.timeout or self.config.code_execution_timeout
        )

        # Cleanup temp file
        if code and temp_file.exists():
            temp_file.unlink()

        return ExecutionResult(
            success=result["returncode"] == 0,
            output=result["stdout"],
            error=result["stderr"] if result["returncode"] != 0 else None,
            action_type=ActionType.RUN_PYTHON,
            return_code=result["returncode"],
            mode=ExecutionMode.DIRECT,
            metadata={"command": " ".join(cmd)}
        )

    async def _run_typescript(self, action: Action) -> ExecutionResult:
        """
        Execute TypeScript code using ts-node or tsx.

        Details:
            - code: TypeScript code to execute
            - file: Optional file path to execute instead
            - args: Optional list of arguments
        """
        details = action.details
        code = details.get("code")
        file_path = details.get("file")
        args = details.get("args", [])

        # Try different TS runners
        ts_runner = None
        if self.ts_node_path and "ts-node" in self.ts_node_path:
            ts_runner = [self.ts_node_path]
        elif self.npx_path:
            ts_runner = [self.npx_path, "tsx"]
        else:
            return ExecutionResult.failure(
                "TypeScript runner (ts-node/tsx) not found",
                ActionType.RUN_TYPESCRIPT
            )

        if code:
            temp_file = self.config.temp_dir / f"script_{int(time.time())}.ts"
            temp_file.write_text(code)
            cmd = ts_runner + [str(temp_file)] + args
        elif file_path:
            path = self._validate_path(file_path)
            cmd = ts_runner + [str(path)] + args
        else:
            return ExecutionResult.failure(
                "Either 'code' or 'file' must be provided",
                ActionType.RUN_TYPESCRIPT
            )

        result = await self._run_subprocess(
            cmd,
            timeout=action.timeout or self.config.code_execution_timeout
        )

        if code and temp_file.exists():
            temp_file.unlink()

        return ExecutionResult(
            success=result["returncode"] == 0,
            output=result["stdout"],
            error=result["stderr"] if result["returncode"] != 0 else None,
            action_type=ActionType.RUN_TYPESCRIPT,
            return_code=result["returncode"],
            mode=ExecutionMode.DIRECT,
            metadata={"command": " ".join(cmd)}
        )

    async def _run_bash(self, action: Action) -> ExecutionResult:
        """
        Execute Bash script.

        Details:
            - script: Bash script content
            - file: Optional file path to execute
            - args: Optional list of arguments
        """
        details = action.details
        script = details.get("script")
        file_path = details.get("file")
        args = details.get("args", [])

        self._validate_command(script or "")

        bash_path = shutil.which("bash") or "/bin/bash"

        if script:
            temp_file = self.config.temp_dir / f"script_{int(time.time())}.sh"
            temp_file.write_text(script)
            temp_file.chmod(temp_file.stat().st_mode | stat.S_IEXEC)

            cmd = [bash_path, str(temp_file)] + args
        elif file_path:
            path = self._validate_path(file_path)
            cmd = [bash_path, str(path)] + args
        else:
            return ExecutionResult.failure(
                "Either 'script' or 'file' must be provided",
                ActionType.RUN_BASH
            )

        result = await self._run_subprocess(
            cmd,
            timeout=action.timeout or self.config.code_execution_timeout
        )

        if script and temp_file.exists():
            temp_file.unlink()

        return ExecutionResult(
            success=result["returncode"] == 0,
            output=result["stdout"],
            error=result["stderr"] if result["returncode"] != 0 else None,
            action_type=ActionType.RUN_BASH,
            return_code=result["returncode"],
            mode=ExecutionMode.DIRECT,
            metadata={"command": cmd[0]}
        )

    async def _run_node(self, action: Action) -> ExecutionResult:
        """
        Execute JavaScript code with Node.js.

        Details:
            - code: JavaScript code to execute
            - file: Optional file path to execute
            - args: Optional list of arguments
        """
        details = action.details
        code = details.get("code")
        file_path = details.get("file")
        args = details.get("args", [])

        if not self.node_path:
            return ExecutionResult.failure(
                "Node.js not found in PATH",
                ActionType.RUN_NODE
            )

        if code:
            temp_file = self.config.temp_dir / f"script_{int(time.time())}.js"
            temp_file.write_text(code)
            cmd = [self.node_path, str(temp_file)] + args
        elif file_path:
            path = self._validate_path(file_path)
            cmd = [self.node_path, str(path)] + args
        else:
            return ExecutionResult.failure(
                "Either 'code' or 'file' must be provided",
                ActionType.RUN_NODE
            )

        result = await self._run_subprocess(
            cmd,
            timeout=action.timeout or self.config.code_execution_timeout
        )

        if code and temp_file.exists():
            temp_file.unlink()

        return ExecutionResult(
            success=result["returncode"] == 0,
            output=result["stdout"],
            error=result["stderr"] if result["returncode"] != 0 else None,
            action_type=ActionType.RUN_NODE,
            return_code=result["returncode"],
            mode=ExecutionMode.DIRECT,
            metadata={"command": " ".join(cmd)}
        )

    async def _run_custom_script(self, action: Action) -> ExecutionResult:
        """
        Write and execute a custom script with specified interpreter.

        Details:
            - code: Script content
            - interpreter: Interpreter to use (python, bash, node, etc.)
            - extension: File extension (.py, .sh, .js, etc.)
            - args: Optional arguments
        """
        details = action.details
        code = details.get("code", "")
        interpreter = details.get("interpreter", "bash")
        extension = details.get("extension", ".sh")
        args = details.get("args", [])

        self._validate_command(code)

        # Find interpreter
        interp_path = shutil.which(interpreter)
        if not interp_path:
            return ExecutionResult.failure(
                f"Interpreter '{interpreter}' not found",
                ActionType.CUSTOM_SCRIPT
            )

        # Create temp script
        script_hash = hashlib.md5(code.encode()).hexdigest()[:8]
        temp_file = self.config.temp_dir / f"custom_{script_hash}{extension}"
        temp_file.write_text(code)
        temp_file.chmod(temp_file.stat().st_mode | stat.S_IEXEC)

        cmd = [interp_path, str(temp_file)] + args

        try:
            result = await self._run_subprocess(
                cmd,
                timeout=action.timeout or self.config.code_execution_timeout
            )

            return ExecutionResult(
                success=result["returncode"] == 0,
                output=result["stdout"],
                error=result["stderr"] if result["returncode"] != 0 else None,
                action_type=ActionType.CUSTOM_SCRIPT,
                return_code=result["returncode"],
                mode=ExecutionMode.DIRECT,
                metadata={
                    "interpreter": interpreter,
                    "script_file": str(temp_file)
                }
            )
        finally:
            if temp_file.exists():
                temp_file.unlink()

    async def _run_shell_command(self, action: Action) -> ExecutionResult:
        """
        Run a shell command directly.

        Details:
            - command: Command string to execute
            - shell: Whether to use shell (default True)
        """
        if not self.config.allow_shell:
            return ExecutionResult.failure(
                "Shell commands are disabled",
                ActionType.SHELL_COMMAND
            )

        details = action.details
        command = details.get("command", "")
        use_shell = details.get("shell", True)

        self._validate_command(command)

        result = await self._run_subprocess(
            command if use_shell else command.split(),
            timeout=action.timeout or self.config.code_execution_timeout,
            shell=use_shell
        )

        return ExecutionResult(
            success=result["returncode"] == 0,
            output=result["stdout"],
            error=result["stderr"] if result["returncode"] != 0 else None,
            action_type=ActionType.SHELL_COMMAND,
            return_code=result["returncode"],
            mode=ExecutionMode.DIRECT,
            metadata={"command": command}
        )

    # =========================================================================
    # CLAUDE DELEGATION
    # =========================================================================

    async def _claude_code(self, action: Action) -> ExecutionResult:
        """
        Execute a task using Claude Code CLI.

        Details:
            - prompt: The prompt for Claude Code
            - output_format: Optional output format (json, text)
            - allowedTools: Optional list of allowed tools
        """
        details = action.details
        prompt = details.get("prompt", action.prompt)
        output_format = details.get("output_format")
        allowed_tools = details.get("allowedTools", [])

        if not prompt:
            return ExecutionResult.failure(
                "Prompt is required for Claude Code",
                ActionType.CLAUDE_CODE
            )

        if not self.claude_path:
            return ExecutionResult.failure(
                "Claude CLI not found. Ensure 'claude' is installed.",
                ActionType.CLAUDE_CODE
            )

        # Build command
        cmd = [self.claude_path, "--print"]

        if output_format:
            cmd.extend(["--output-format", output_format])

        if allowed_tools:
            cmd.extend(["--allowedTools", ",".join(allowed_tools)])

        cmd.append(prompt)

        result = await self._run_subprocess(
            cmd,
            timeout=action.timeout or self.config.claude_timeout
        )

        return ExecutionResult(
            success=result["returncode"] == 0,
            output=result["stdout"],
            error=result["stderr"] if result["returncode"] != 0 else None,
            action_type=ActionType.CLAUDE_CODE,
            return_code=result["returncode"],
            mode=ExecutionMode.SIMPLE,
            metadata={
                "command": "claude --print",
                "output_format": output_format
            }
        )

    async def _claude_flow(self, action: Action) -> ExecutionResult:
        """
        Execute a Claude Flow swarm for complex tasks.

        Details:
            - task: Task description
            - topology: Swarm topology (hierarchical, mesh, ring, star)
            - max_agents: Maximum agents
            - strategy: Execution strategy
        """
        details = action.details
        task = details.get("task", details.get("prompt", ""))
        topology = details.get("topology", "hierarchical")
        max_agents = details.get("max_agents", 8)
        strategy = details.get("strategy", "adaptive")
        priority = details.get("priority", "medium")

        if not task:
            return ExecutionResult.failure(
                "Task is required for Claude Flow",
                ActionType.CLAUDE_FLOW
            )

        if not self.npx_path:
            return ExecutionResult.failure(
                "npx not found. Ensure Node.js is installed.",
                ActionType.CLAUDE_FLOW
            )

        results: List[Dict[str, Any]] = []

        # Step 1: Initialize swarm
        init_cmd = [
            self.npx_path, "claude-flow@alpha", "swarm", "init",
            "--topology", topology,
            "--max-agents", str(max_agents),
            "--strategy", strategy
        ]

        init_result = await self._run_subprocess(init_cmd, timeout=60)
        results.append({
            "step": "swarm_init",
            "success": init_result["returncode"] == 0,
            "output": init_result["stdout"],
            "error": init_result["stderr"]
        })

        if init_result["returncode"] != 0:
            return ExecutionResult(
                success=False,
                output=init_result["stdout"],
                error=f"Swarm init failed: {init_result['stderr']}",
                action_type=ActionType.CLAUDE_FLOW,
                mode=ExecutionMode.SWARM,
                metadata={"steps": results}
            )

        # Step 2: Orchestrate task
        orchestrate_cmd = [
            self.npx_path, "claude-flow@alpha", "task", "orchestrate",
            "--priority", priority,
            "--strategy", strategy,
            task
        ]

        orchestrate_result = await self._run_subprocess(
            orchestrate_cmd,
            timeout=action.timeout or self.config.claude_timeout
        )

        results.append({
            "step": "task_orchestrate",
            "success": orchestrate_result["returncode"] == 0,
            "output": orchestrate_result["stdout"],
            "error": orchestrate_result["stderr"]
        })

        combined_output = "\n".join([r["output"] for r in results if r["output"]])

        return ExecutionResult(
            success=orchestrate_result["returncode"] == 0,
            output=combined_output,
            error=orchestrate_result["stderr"] if orchestrate_result["returncode"] != 0 else None,
            action_type=ActionType.CLAUDE_FLOW,
            mode=ExecutionMode.SWARM,
            metadata={
                "steps": results,
                "topology": topology,
                "max_agents": max_agents,
                "strategy": strategy
            }
        )

    # =========================================================================
    # GEMINI DELEGATION (TIER 4 - LIBRARIAN)
    # =========================================================================

    async def _execute_gemini(self, action: Action) -> ExecutionResult:
        """
        Execute a Gemini analysis action (Tier 4).

        Gemini is the "Librarian" tier with MASSIVE context window (2M+ tokens).
        Ideal for:
        - "Read these 50 documentation files and summarize the API"
        - "Analyze the entire git log history for the last year"
        - "Find the needle in the haystack of 10,000 log lines"

        CRITICAL: Medium/Low trust - prone to hallucination on specific logic.
        Use for analysis, summarization, and retrieval. Code output MUST be
        verified with Claude.

        Details:
            - prompt: Analysis prompt
            - files: Optional list of file paths to include as context
            - context: Optional large text context
            - model: Gemini model to use (default: gemini-1.5-pro)

        Warning: High context, lower trust. Verify code output with Claude.
        """
        details = action.details
        prompt = details.get("prompt", "")
        files = details.get("files", [])
        context = details.get("context", "")
        model = details.get("model", "gemini-1.5-pro")

        if not prompt:
            return ExecutionResult.failure(
                "Prompt is required for Gemini analysis",
                ActionType.GEMINI_ANALYZE
            )

        # Check if Gemini is available
        if not self._check_gemini_available():
            return ExecutionResult.failure(
                "Gemini API not available. Set GOOGLE_API_KEY environment variable "
                "or install google-generativeai package.",
                ActionType.GEMINI_ANALYZE
            )

        # Build full context from files
        file_contexts = []
        files_loaded = []

        for file_path in files:
            try:
                path = self._validate_path(file_path)
                if path.exists() and path.is_file():
                    content = path.read_text(encoding='utf-8', errors='replace')
                    file_contexts.append(f"--- FILE: {path.name} ---\n{content}\n--- END FILE ---")
                    files_loaded.append(str(path))
                else:
                    logger.warning(f"Gemini: File not found or not a file: {path}")
            except ValueError as e:
                logger.warning(f"Gemini: Path validation failed for {file_path}: {e}")
            except Exception as e:
                logger.warning(f"Gemini: Failed to read file {file_path}: {e}")

        # Combine all context
        full_context = ""
        if file_contexts:
            full_context += "=== FILE CONTEXT ===\n"
            full_context += "\n\n".join(file_contexts)
            full_context += "\n=== END FILE CONTEXT ===\n\n"

        if context:
            full_context += "=== ADDITIONAL CONTEXT ===\n"
            full_context += context
            full_context += "\n=== END ADDITIONAL CONTEXT ===\n\n"

        # Build the full prompt
        full_prompt = full_context + prompt

        # Log context size for monitoring
        context_size = len(full_prompt)
        logger.info(
            f"Gemini analysis: model={model}, context_size={context_size} chars, "
            f"files={len(files_loaded)}"
        )

        # Try Python SDK first, fall back to CLI
        result = await self._execute_gemini_sdk(full_prompt, model, action.timeout)

        if result is None:
            # SDK failed, try CLI wrapper
            result = await self._execute_gemini_cli(full_prompt, model, action.timeout)

        if result is None:
            return ExecutionResult.failure(
                "Gemini execution failed - both SDK and CLI methods unavailable",
                ActionType.GEMINI_ANALYZE
            )

        # Add Tier 4 trust level metadata
        result.metadata["tier"] = 4
        result.metadata["trust_level"] = "verify"
        result.metadata["warning"] = "Gemini output - verify code with Claude before using"
        result.metadata["model"] = model
        result.metadata["context_size"] = context_size
        result.metadata["files_loaded"] = files_loaded

        return result

    async def _execute_gemini_sdk(
        self,
        prompt: str,
        model: str,
        timeout: Optional[int]
    ) -> Optional[ExecutionResult]:
        """
        Execute Gemini using the google-generativeai Python SDK.

        Returns None if SDK is not available or fails to initialize.
        """
        try:
            import google.generativeai as genai
        except ImportError:
            logger.debug("google-generativeai package not installed")
            return None

        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            logger.debug("GOOGLE_API_KEY not set for SDK")
            return None

        try:
            # Configure the SDK
            genai.configure(api_key=api_key)

            # Get the model
            gemini_model = genai.GenerativeModel(model)

            # Generate content with timeout
            timeout_seconds = timeout or self.config.gemini_timeout

            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()

            def generate():
                response = gemini_model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=8192,
                        temperature=0.3,  # Lower temperature for analysis
                    ),
                    safety_settings={
                        "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
                        "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
                        "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
                        "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
                    }
                )
                return response

            try:
                response = await asyncio.wait_for(
                    loop.run_in_executor(None, generate),
                    timeout=timeout_seconds
                )

                # Extract text from response
                output = response.text if hasattr(response, 'text') else str(response)

                return ExecutionResult(
                    success=True,
                    output=output,
                    action_type=ActionType.GEMINI_ANALYZE,
                    mode=ExecutionMode.SIMPLE,
                    metadata={"method": "sdk"}
                )

            except asyncio.TimeoutError:
                return ExecutionResult.failure(
                    f"Gemini SDK timed out after {timeout_seconds}s",
                    ActionType.GEMINI_ANALYZE
                )

        except Exception as e:
            logger.warning(f"Gemini SDK execution failed: {e}")
            return ExecutionResult.failure(
                f"Gemini SDK error: {str(e)}",
                ActionType.GEMINI_ANALYZE
            )

    async def _execute_gemini_cli(
        self,
        prompt: str,
        model: str,
        timeout: Optional[int]
    ) -> Optional[ExecutionResult]:
        """
        Execute Gemini using a CLI wrapper (gemini-cli or custom script).

        Falls back to using curl with the Gemini API directly.
        """
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            logger.debug("GOOGLE_API_KEY not set for CLI")
            return None

        # Try gemini CLI if available
        gemini_cli = shutil.which("gemini")
        if gemini_cli:
            # Write prompt to temp file for large context
            temp_file = self.config.temp_dir / f"gemini_prompt_{int(time.time())}.txt"
            temp_file.write_text(prompt)

            try:
                cmd = [gemini_cli, "--model", model, "--file", str(temp_file)]
                result = await self._run_subprocess(
                    cmd,
                    timeout=timeout or self.config.gemini_timeout,
                    env={"GOOGLE_API_KEY": api_key}
                )

                return ExecutionResult(
                    success=result["returncode"] == 0,
                    output=result["stdout"],
                    error=result["stderr"] if result["returncode"] != 0 else None,
                    action_type=ActionType.GEMINI_ANALYZE,
                    return_code=result["returncode"],
                    mode=ExecutionMode.SIMPLE,
                    metadata={"method": "cli"}
                )
            finally:
                if temp_file.exists():
                    temp_file.unlink()

        # Fall back to curl API call
        try:
            import json as json_module

            # Prepare API request
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

            request_body = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "maxOutputTokens": 8192,
                    "temperature": 0.3
                }
            }

            # Write request body to temp file
            temp_request = self.config.temp_dir / f"gemini_request_{int(time.time())}.json"
            temp_request.write_text(json_module.dumps(request_body))

            try:
                cmd = [
                    "curl", "-s", "-X", "POST",
                    f"{api_url}?key={api_key}",
                    "-H", "Content-Type: application/json",
                    "-d", f"@{temp_request}"
                ]

                result = await self._run_subprocess(
                    cmd,
                    timeout=timeout or self.config.gemini_timeout
                )

                if result["returncode"] == 0:
                    try:
                        response_data = json_module.loads(result["stdout"])
                        # Extract text from Gemini API response
                        if "candidates" in response_data:
                            text_parts = []
                            for candidate in response_data["candidates"]:
                                if "content" in candidate and "parts" in candidate["content"]:
                                    for part in candidate["content"]["parts"]:
                                        if "text" in part:
                                            text_parts.append(part["text"])
                            output = "\n".join(text_parts)
                        elif "error" in response_data:
                            return ExecutionResult.failure(
                                f"Gemini API error: {response_data['error'].get('message', 'Unknown error')}",
                                ActionType.GEMINI_ANALYZE
                            )
                        else:
                            output = result["stdout"]

                        return ExecutionResult(
                            success=True,
                            output=output,
                            action_type=ActionType.GEMINI_ANALYZE,
                            mode=ExecutionMode.SIMPLE,
                            metadata={"method": "curl"}
                        )
                    except json_module.JSONDecodeError:
                        return ExecutionResult.failure(
                            f"Failed to parse Gemini response: {result['stdout'][:500]}",
                            ActionType.GEMINI_ANALYZE
                        )
                else:
                    return ExecutionResult.failure(
                        f"Gemini curl request failed: {result['stderr']}",
                        ActionType.GEMINI_ANALYZE
                    )

            finally:
                if temp_request.exists():
                    temp_request.unlink()

        except Exception as e:
            logger.warning(f"Gemini CLI/curl execution failed: {e}")
            return None

    def _check_gemini_available(self) -> bool:
        """
        Check if Gemini is available.

        Checks for:
        1. GOOGLE_API_KEY environment variable
        2. google-generativeai SDK (preferred)
        3. gemini CLI tool
        4. curl for API fallback

        Returns True if at least one method is available.
        """
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            return False

        # Check for SDK
        try:
            import google.generativeai
            return True
        except ImportError:
            pass

        # Check for CLI
        if shutil.which("gemini"):
            return True

        # Check for curl (fallback)
        if shutil.which("curl"):
            return True

        return False

    # =========================================================================
    # THINKING AND DISCUSSION
    # =========================================================================

    async def _think(self, action: Action) -> ExecutionResult:
        """
        Internal reasoning/thinking action.

        Uses Claude Code to perform deep thinking on a topic.

        Details:
            - topic: What to think about
            - depth: shallow, medium, deep
            - output_file: Optional file to save thoughts
        """
        details = action.details
        topic = details.get("topic", "")
        depth = details.get("depth", "medium")
        output_file = details.get("output_file")

        if not topic:
            return ExecutionResult.failure("Topic is required for thinking", ActionType.THINK)

        depth_instructions = {
            "shallow": "Provide a brief analysis in 2-3 paragraphs.",
            "medium": "Provide a thorough analysis covering multiple perspectives.",
            "deep": "Provide an exhaustive analysis exploring all facets, implications, and edge cases."
        }

        prompt = f"""Think deeply about the following topic:

Topic: {topic}

{depth_instructions.get(depth, depth_instructions["medium"])}

Structure your thinking as:
1. Initial observations
2. Key considerations
3. Different perspectives
4. Potential implications
5. Conclusions or open questions
"""

        # Use Claude Code to think
        result = await self._claude_code(Action(
            type=ActionType.CLAUDE_CODE,
            details={"prompt": prompt}
        ))

        # Save to file if requested
        if output_file and result.success:
            await self._write_file(Action(
                type=ActionType.WRITE_FILE,
                details={
                    "path": output_file,
                    "content": f"# Thoughts on: {topic}\n\n{result.output}"
                }
            ))
            result.files_created = [output_file]

        result.action_type = ActionType.THINK
        return result

    async def _spawn_debate(self, action: Action) -> ExecutionResult:
        """
        Spawn a philosophical debate between thinkers.

        Uses the /debate command or simulates it with Claude.

        Details:
            - topic: Debate topic
            - thinkers: List of thinker names (e.g., ["plato", "aristotle"])
            - rounds: Number of debate rounds
            - output_file: Optional file to save debate
        """
        details = action.details
        topic = details.get("topic", "")
        thinkers = details.get("thinkers", [])
        rounds = details.get("rounds", 3)
        output_file = details.get("output_file")

        if not topic:
            return ExecutionResult.failure("Topic is required for debate", ActionType.DEBATE)

        if len(thinkers) < 2:
            thinkers = ["socrates", "plato"]  # Default thinkers

        # Try using the /debate command via Claude
        thinker_args = " ".join(thinkers[:2])
        prompt = f"""Run a philosophical debate on the topic: "{topic}"

Between thinkers: {thinker_args}
Number of rounds: {rounds}

Format the debate with clear speaker labels and thoughtful arguments from each perspective.
Include opening statements, rebuttals, and closing remarks.
"""

        result = await self._claude_code(Action(
            type=ActionType.CLAUDE_CODE,
            details={"prompt": prompt}
        ))

        # Save to file if requested
        if output_file and result.success:
            await self._write_file(Action(
                type=ActionType.WRITE_FILE,
                details={
                    "path": output_file,
                    "content": f"# Debate: {topic}\n\n**Participants**: {', '.join(thinkers)}\n\n{result.output}"
                }
            ))
            result.files_created = [output_file]

        result.action_type = ActionType.DEBATE
        result.metadata["topic"] = topic
        result.metadata["thinkers"] = thinkers
        return result

    async def _research(self, action: Action) -> ExecutionResult:
        """
        Deep research on a topic.

        Uses Claude Code/Flow to perform comprehensive research.

        Details:
            - topic: Research topic
            - sources: Optional list of sources to consult
            - depth: How deep to research
            - output_file: Optional file to save research
        """
        details = action.details
        topic = details.get("topic", "")
        sources = details.get("sources", [])
        depth = details.get("depth", "comprehensive")
        output_file = details.get("output_file")

        if not topic:
            return ExecutionResult.failure("Topic is required for research", ActionType.RESEARCH)

        source_context = ""
        if sources:
            source_context = f"\nConsult these sources if available: {', '.join(sources)}"

        prompt = f"""Conduct {depth} research on the following topic:

Topic: {topic}
{source_context}

Provide:
1. Overview and definition
2. Historical context and development
3. Key theories and perspectives
4. Current understanding and debates
5. Open questions and future directions
6. Relevant references and further reading

Be thorough and cite sources where applicable.
"""

        # For comprehensive research, use Claude Flow swarm
        if depth == "comprehensive":
            result = await self._claude_flow(Action(
                type=ActionType.CLAUDE_FLOW,
                details={
                    "task": prompt,
                    "topology": "mesh",
                    "max_agents": 5,
                    "strategy": "balanced"
                }
            ))
        else:
            result = await self._claude_code(Action(
                type=ActionType.CLAUDE_CODE,
                details={"prompt": prompt}
            ))

        # Save to file if requested
        if output_file and result.success:
            await self._write_file(Action(
                type=ActionType.WRITE_FILE,
                details={
                    "path": output_file,
                    "content": f"# Research: {topic}\n\n{result.output}"
                }
            ))
            result.files_created = [output_file]

        result.action_type = ActionType.RESEARCH
        return result

    async def _discuss(self, action: Action) -> ExecutionResult:
        """
        Multi-perspective discussion on a topic.

        Details:
            - topic: Discussion topic
            - perspectives: List of perspectives to include
            - goal: Goal of the discussion
            - output_file: Optional file to save discussion
        """
        details = action.details
        topic = details.get("topic", "")
        perspectives = details.get("perspectives", [])
        goal = details.get("goal", "explore different viewpoints")
        output_file = details.get("output_file")

        if not topic:
            return ExecutionResult.failure("Topic is required for discussion", ActionType.DISCUSS)

        if not perspectives:
            perspectives = ["philosophical", "scientific", "practical", "ethical"]

        prompt = f"""Facilitate a multi-perspective discussion on:

Topic: {topic}
Goal: {goal}

Include these perspectives:
{chr(10).join(f"- {p}" for p in perspectives)}

For each perspective:
1. Present the main viewpoint
2. Highlight key arguments
3. Note potential objections
4. Find common ground with other perspectives

Conclude with a synthesis that integrates insights from all perspectives.
"""

        result = await self._claude_code(Action(
            type=ActionType.CLAUDE_CODE,
            details={"prompt": prompt}
        ))

        if output_file and result.success:
            await self._write_file(Action(
                type=ActionType.WRITE_FILE,
                details={
                    "path": output_file,
                    "content": f"# Discussion: {topic}\n\n{result.output}"
                }
            ))
            result.files_created = [output_file]

        result.action_type = ActionType.DISCUSS
        return result

    # =========================================================================
    # SUBPROCESS UTILITIES
    # =========================================================================

    async def _run_subprocess(
        self,
        cmd: Union[List[str], str],
        timeout: int,
        shell: bool = False,
        env: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Run a subprocess asynchronously with timeout.

        Args:
            cmd: Command and arguments (list) or command string (if shell=True)
            timeout: Timeout in seconds
            shell: Whether to use shell
            env: Optional environment variables

        Returns:
            Dict with stdout, stderr, and returncode
        """
        # Merge environment
        full_env = os.environ.copy()
        if env:
            full_env.update(env)

        if shell:
            process = await asyncio.create_subprocess_shell(
                cmd if isinstance(cmd, str) else " ".join(cmd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.working_dir),
                env=full_env
            )
        else:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.working_dir),
                env=full_env
            )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            # Truncate output if too large
            stdout_str = stdout.decode('utf-8', errors='replace')
            stderr_str = stderr.decode('utf-8', errors='replace')

            if len(stdout_str) > self.config.max_output_size:
                stdout_str = stdout_str[:self.config.max_output_size] + "\n... (truncated)"
            if len(stderr_str) > self.config.max_output_size:
                stderr_str = stderr_str[:self.config.max_output_size] + "\n... (truncated)"

            return {
                "stdout": stdout_str,
                "stderr": stderr_str,
                "returncode": process.returncode
            }

        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def is_available(self) -> bool:
        """Check if Claude CLI is available."""
        if not self.claude_path:
            return False
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
        if not self.npx_path:
            return False
        try:
            result = subprocess.run(
                [self.npx_path, "claude-flow@alpha", "--version"],
                capture_output=True,
                timeout=30
            )
            return result.returncode == 0
        except Exception:
            return False

    def get_capabilities(self) -> Dict[str, bool]:
        """Get a dictionary of available capabilities."""
        return {
            "claude_code": self.is_available(),
            "claude_flow": self.is_swarm_available(),
            "gemini": self._check_gemini_available(),
            "python": self.python_path is not None,
            "node": self.node_path is not None,
            "typescript": self.ts_node_path is not None or self.npx_path is not None,
            "bash": shutil.which("bash") is not None,
            "file_operations": True,
            "shell_commands": self.config.allow_shell,
            "file_deletion": self.config.allow_delete,
        }


# =============================================================================
# BACKWARDS COMPATIBILITY - ClaudeCodeExecutor
# =============================================================================

class ClaudeCodeExecutor(ExpandedExecutor):
    """
    Legacy executor class for backwards compatibility.

    Wraps ExpandedExecutor with the original interface.
    """

    def __init__(
        self,
        working_dir: Path,
        timeout: int = 300,
        claude_path: Optional[str] = None,
        npx_path: Optional[str] = None
    ):
        """Initialize with legacy parameters."""
        config = ExecutionConfig(default_timeout=timeout, claude_timeout=timeout)
        super().__init__(working_dir, config, claude_path, npx_path)

    async def execute(
        self,
        prompt: str,
        output_format: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> ExecutionResult:
        """Execute a task using Claude Code CLI (legacy interface)."""
        action = Action(
            type=ActionType.CLAUDE_CODE,
            details={
                "prompt": prompt,
                "output_format": output_format
            },
            timeout=timeout
        )
        return await super().execute(action)

    async def execute_swarm(
        self,
        task: str,
        config: Optional[SwarmConfig] = None,
        timeout: Optional[int] = None
    ) -> ExecutionResult:
        """Execute a Claude Flow swarm (legacy interface)."""
        config = config or SwarmConfig()
        action = Action(
            type=ActionType.CLAUDE_FLOW,
            details={
                "task": task,
                "topology": config.topology,
                "max_agents": config.max_agents,
                "strategy": config.strategy,
                "priority": config.priority
            },
            timeout=timeout
        )
        return await super().execute(action)

    async def execute_with_context(
        self,
        prompt: str,
        context_files: List[Path],
        output_format: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> ExecutionResult:
        """Execute a task with file context (legacy interface)."""
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

        # Build enhanced prompt
        if context_parts:
            context_str = "\n\n".join(context_parts)
            enhanced_prompt = f"""Context files:
{context_str}

Task:
{prompt}"""
        else:
            enhanced_prompt = prompt

        result = await self.execute(enhanced_prompt, output_format, timeout)
        result.metadata["context_files"] = valid_files

        return result


# =============================================================================
# EXECUTOR POOL
# =============================================================================

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
        self._executor = ExpandedExecutor(
            working_dir,
            ExecutionConfig(default_timeout=timeout)
        )
        self._active_tasks: Dict[str, asyncio.Task] = {}

    async def execute(
        self,
        task_id: str,
        action: Action
    ) -> ExecutionResult:
        """
        Execute an action with concurrency control.

        Args:
            task_id: Unique identifier for the task
            action: The action to execute

        Returns:
            ExecutionResult from the execution
        """
        async with self._semaphore:
            task = asyncio.current_task()
            if task:
                self._active_tasks[task_id] = task

            try:
                return await self._executor.execute(action)
            finally:
                self._active_tasks.pop(task_id, None)

    async def execute_prompt(
        self,
        task_id: str,
        prompt: str,
        **kwargs
    ) -> ExecutionResult:
        """Execute a prompt with Claude Code (convenience method)."""
        action = Action.claude_code(prompt)
        return await self.execute(task_id, action)

    def get_active_tasks(self) -> List[str]:
        """Get list of active task IDs."""
        return list(self._active_tasks.keys())

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        task = self._active_tasks.get(task_id)
        if task:
            task.cancel()
            return True
        return False


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

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
    executor = ExpandedExecutor(wd, ExecutionConfig(claude_timeout=timeout))
    return await executor.execute(Action.claude_code(prompt))


async def execute_action(
    action: Action,
    working_dir: Optional[Path] = None
) -> ExecutionResult:
    """
    Convenience function for executing any action.

    Args:
        action: The action to execute
        working_dir: Optional working directory

    Returns:
        ExecutionResult from the execution
    """
    wd = working_dir or Path.cwd()
    executor = ExpandedExecutor(wd)
    return await executor.execute(action)


# =============================================================================
# MAIN - Testing
# =============================================================================

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG)

    async def main():
        """Test the expanded executor."""
        executor = ExpandedExecutor(
            working_dir=Path.cwd(),
            config=ExecutionConfig(allow_delete=False)
        )

        print("=" * 60)
        print("Expanded Executor Test Suite")
        print("=" * 60)

        # Check capabilities
        print("\nCapabilities:")
        for cap, available in executor.get_capabilities().items():
            status = "YES" if available else "NO"
            print(f"  {cap}: {status}")

        # Test 1: Write file
        print("\n--- Test 1: Write File ---")
        result = await executor.execute(Action(
            type=ActionType.WRITE_FILE,
            details={
                "path": ".consciousness/temp/test_file.txt",
                "content": "Hello from the Consciousness daemon!\n"
            }
        ))
        print(f"Success: {result.success}")
        print(f"Output: {result.output}")

        # Test 2: Run Python
        print("\n--- Test 2: Run Python ---")
        result = await executor.execute(Action(
            type=ActionType.RUN_PYTHON,
            details={
                "code": "print('Hello from Python!')\nprint(2 + 2)"
            }
        ))
        print(f"Success: {result.success}")
        print(f"Output: {result.output}")

        # Test 3: Run Bash
        print("\n--- Test 3: Run Bash ---")
        result = await executor.execute(Action(
            type=ActionType.RUN_BASH,
            details={
                "script": "echo 'Hello from Bash!'\ndate"
            }
        ))
        print(f"Success: {result.success}")
        print(f"Output: {result.output}")

        # Test 4: Claude Code (if available)
        if executor.is_available():
            print("\n--- Test 4: Claude Code ---")
            result = await executor.execute(Action(
                type=ActionType.CLAUDE_CODE,
                details={
                    "prompt": "Say 'Hello from Claude!' and nothing else."
                }
            ))
            print(f"Success: {result.success}")
            print(f"Output: {result.output[:200] if result.output else 'No output'}")
        else:
            print("\n--- Test 4: Claude Code (SKIPPED - not available) ---")

        # Test 5: Gemini Analyze (if available)
        if executor._check_gemini_available():
            print("\n--- Test 5: Gemini Analyze (Tier 4) ---")
            result = await executor.execute(Action.gemini_analyze(
                prompt="Say 'Hello from Gemini!' and nothing else.",
                model="gemini-1.5-flash"  # Use flash for quick test
            ))
            print(f"Success: {result.success}")
            print(f"Output: {result.output[:200] if result.output else 'No output'}")
            print(f"Trust Level: {result.metadata.get('trust_level', 'N/A')}")
            print(f"Tier: {result.metadata.get('tier', 'N/A')}")
            if result.metadata.get('warning'):
                print(f"Warning: {result.metadata['warning']}")
        else:
            print("\n--- Test 5: Gemini Analyze (SKIPPED - not available) ---")
            print("  Set GOOGLE_API_KEY to enable Gemini integration.")

        print("\n" + "=" * 60)
        print("Tests complete!")

    asyncio.run(main())
