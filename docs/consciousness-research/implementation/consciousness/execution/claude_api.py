"""
Claude API Executor - Anthropic SDK Integration

Implements task delegation using the Anthropic Python SDK directly.
Supports tool use for file operations within Stoffy.

Key insight: We use the SDK directly (not Claude CLI) for:
- Full programmatic control
- No subprocess overhead
- Direct access to tool use
- Better error handling
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from anthropic import Anthropic
from anthropic.types import Message, ToolUseBlock, TextBlock

from ..config import AnthropicConfig
from ..inference.lm_studio import Action, ActionType


# Tool definitions for file operations
STOFFY_TOOLS = [
    {
        "name": "read_file",
        "description": "Read a file from the Stoffy repository",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path from stoffy root"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Write content to a file in Stoffy",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "list_directory",
        "description": "List contents of a directory",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "run_command",
        "description": "Run a shell command in Stoffy directory",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string"}
            },
            "required": ["command"]
        }
    },
]


@dataclass
class TaskResult:
    """Result of executing a task."""
    success: bool
    content: str
    tool_calls: list[dict[str, Any]]
    usage: Optional[dict[str, int]] = None
    error: Optional[str] = None


class ClaudeExecutor:
    """
    Executes tasks using Claude API directly.

    Supports tool use for file operations, with an agentic loop
    that continues until Claude is done with the task.
    """

    def __init__(
        self,
        config: AnthropicConfig,
        stoffy_root: Optional[Path] = None,
    ):
        self.config = config
        self.client = Anthropic()  # Uses ANTHROPIC_API_KEY env var
        self.stoffy_root = stoffy_root or Path.cwd()

    def _build_system_prompt(self, context: dict[str, Any]) -> str:
        """Build system prompt with context."""
        system = """You are Claude, executing a task delegated by the Consciousness orchestrator.

Your role:
- Complete the delegated task efficiently
- Use the provided tools for file operations
- Report results clearly

Available tools:
- read_file: Read file contents
- write_file: Write content to file
- list_directory: List directory contents
- run_command: Execute shell command

Remember:
- Work within the Stoffy repository
- Be thorough but concise
- Report any issues encountered
"""
        if context:
            system += f"\n\nAdditional context:\n{context}"

        return system

    async def execute_task(
        self,
        action: Action,
        context: Optional[dict[str, Any]] = None,
    ) -> TaskResult:
        """
        Execute a single task action.

        Routes to appropriate execution method based on action type.
        """
        context = context or {}

        if action.type == ActionType.CLAUDE_TASK:
            return await self._execute_with_tools(action.prompt, context)
        elif action.type == ActionType.CLAUDE_FLOW_SWARM:
            return await self._execute_swarm(action)
        elif action.type == ActionType.INTERNAL:
            return await self._execute_internal(action)
        else:
            return TaskResult(
                success=False,
                content="",
                tool_calls=[],
                error=f"Unknown action type: {action.type}",
            )

    async def _execute_with_tools(
        self,
        prompt: str,
        context: dict[str, Any],
    ) -> TaskResult:
        """Execute task with tool use loop."""
        messages = [{"role": "user", "content": prompt}]
        tool_calls = []

        try:
            while True:
                response: Message = self.client.messages.create(
                    model=self.config.model,
                    max_tokens=self.config.max_tokens,
                    system=self._build_system_prompt(context),
                    tools=STOFFY_TOOLS,
                    messages=messages,
                )

                # Check if Claude wants to use a tool
                if response.stop_reason == "tool_use":
                    # Process tool uses
                    tool_results = []
                    for content in response.content:
                        if isinstance(content, ToolUseBlock):
                            result = await self._execute_tool(
                                content.name,
                                content.input,
                            )
                            tool_calls.append({
                                "tool": content.name,
                                "input": content.input,
                                "result": result[:500],  # Truncate for logging
                            })
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": content.id,
                                "content": result,
                            })

                    # Continue the conversation
                    messages.append({
                        "role": "assistant",
                        "content": response.content,
                    })
                    messages.append({
                        "role": "user",
                        "content": tool_results,
                    })
                else:
                    # Done - extract final text
                    final_text = ""
                    for content in response.content:
                        if isinstance(content, TextBlock):
                            final_text += content.text

                    return TaskResult(
                        success=True,
                        content=final_text,
                        tool_calls=tool_calls,
                        usage={
                            "input_tokens": response.usage.input_tokens,
                            "output_tokens": response.usage.output_tokens,
                        },
                    )

        except Exception as e:
            return TaskResult(
                success=False,
                content="",
                tool_calls=tool_calls,
                error=str(e),
            )

    async def _execute_tool(self, name: str, input_data: dict) -> str:
        """Execute a single tool and return result."""
        try:
            if name == "read_file":
                path = self.stoffy_root / input_data["path"]
                if not path.exists():
                    return f"Error: File not found: {input_data['path']}"
                return path.read_text()

            elif name == "write_file":
                path = self.stoffy_root / input_data["path"]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(input_data["content"])
                return f"Successfully written to {input_data['path']}"

            elif name == "list_directory":
                path = self.stoffy_root / input_data["path"]
                if not path.exists():
                    return f"Error: Directory not found: {input_data['path']}"
                items = list(path.iterdir())
                return "\n".join(
                    str(p.relative_to(self.stoffy_root)) for p in items
                )

            elif name == "run_command":
                result = subprocess.run(
                    input_data["command"],
                    shell=True,
                    cwd=self.stoffy_root,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                output = result.stdout or result.stderr
                return output or "(no output)"

            else:
                return f"Unknown tool: {name}"

        except Exception as e:
            return f"Error executing {name}: {e}"

    async def _execute_swarm(self, action: Action) -> TaskResult:
        """Execute a Claude Flow swarm task."""
        try:
            # Use subprocess to invoke Claude Flow
            cmd = f'npx claude-flow@alpha swarm init --topology hierarchical'
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=self.stoffy_root,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode != 0:
                return TaskResult(
                    success=False,
                    content="",
                    tool_calls=[],
                    error=f"Swarm init failed: {result.stderr}",
                )

            # The swarm handles the rest
            return TaskResult(
                success=True,
                content=f"Swarm initialized for: {action.description}",
                tool_calls=[{"tool": "swarm_init", "result": result.stdout}],
            )

        except Exception as e:
            return TaskResult(
                success=False,
                content="",
                tool_calls=[],
                error=str(e),
            )

    async def _execute_internal(self, action: Action) -> TaskResult:
        """Execute an internal action (no external delegation)."""
        # Internal actions are handled by the orchestrator itself
        return TaskResult(
            success=True,
            content=f"Internal action logged: {action.description}",
            tool_calls=[],
        )
