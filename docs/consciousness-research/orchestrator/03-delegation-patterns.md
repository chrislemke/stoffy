# Consciousness Orchestrator: Delegation Patterns for Claude Code and Claude Flow

## Executive Summary

This document provides comprehensive research on how a "Consciousness" orchestrator (local LLM) can delegate tasks to Claude Code (individual task execution) and Claude Flow (multi-agent swarm coordination). The Consciousness makes decisions but **never executes directly**—all execution happens through delegation to these specialized tools.

**Key Architecture Principles:**
1. **Consciousness = Decision Layer**: Analyzes context, decomposes goals, decides what to delegate
2. **Claude Code = Execution Layer**: Handles individual tasks with full tool access
3. **Claude Flow = Coordination Layer**: Orchestrates multi-agent swarms for complex workflows
4. **Communication = Subprocess + File-based**: Python orchestrator manages subprocesses and monitors outputs

**Delegation Decision Criteria:**
- **Simple, focused tasks** → Claude Code (single agent)
- **Complex, multi-step workflows** → Claude Flow (swarm coordination)
- **Parallel, independent tasks** → Claude Flow (parallel agent spawning)
- **Sequential, dependent tasks** → Claude Code with chaining or Claude Flow pipeline

---

## Part I: Claude Code as Execution Layer

### 1. Understanding Claude Code Architecture

Claude Code is Anthropic's official CLI tool that provides a full-featured development environment powered by Claude AI.

#### Core Capabilities

```
+------------------------------------------------------------------+
|                    CLAUDE CODE CAPABILITIES                       |
+------------------------------------------------------------------+
| EXECUTION TOOLS:                                                  |
| - Bash: Run shell commands, manage processes                      |
| - Read/Write/Edit: File operations with intelligent editing       |
| - Glob/Grep: Advanced file searching and pattern matching         |
| - Git: Full version control operations                            |
| - TodoWrite: Task tracking and progress management                |
|                                                                    |
| SPECIALIZED TOOLS:                                                |
| - Task: Spawn parallel sub-agents for concurrent work             |
| - Skill: Invoke custom skills and workflows                       |
| - MCP Integration: Connect to Model Context Protocol servers      |
|                                                                    |
| MODES:                                                            |
| - Interactive: Full conversational interface                      |
| - Print (-p): Non-interactive output for automation               |
| - Streaming: Real-time output with JSON formatting                |
+------------------------------------------------------------------+
```

#### CLI Command Structure

```bash
claude [options] [command] [prompt]

# Key options for delegation:
--print (-p)                    # Non-interactive mode (returns and exits)
--output-format <format>        # text, json, or stream-json
--json-schema <schema>          # Structured output validation
--input-format <format>         # text or stream-json
--no-session-persistence        # Stateless execution
--model <model>                 # Specify Claude model
--agent <agent>                 # Use predefined agent role
--system-prompt <prompt>        # Custom system instructions
--max-budget-usd <amount>       # Cost control
--tools <tools>                 # Limit available tools
--dangerously-skip-permissions  # Bypass permission checks (sandbox only)
```

### 2. Programmatic Invocation from Python

#### 2.1 Basic Subprocess Pattern

```python
"""
Basic Claude Code invocation via subprocess.
This is the foundation for all delegation patterns.
"""
import subprocess
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ClaudeCodeResult:
    """Result from Claude Code execution."""
    success: bool
    output: str
    error: Optional[str]
    exit_code: int
    metadata: Dict[str, Any]


class ClaudeCodeClient:
    """
    Client for delegating tasks to Claude Code.

    The Consciousness orchestrator uses this to spawn Claude Code instances
    for individual task execution.
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-5-20250929",
        max_budget_usd: Optional[float] = None,
        working_dir: Optional[Path] = None,
        verbose: bool = False
    ):
        self.model = model
        self.max_budget_usd = max_budget_usd
        self.working_dir = working_dir or Path.cwd()
        self.verbose = verbose

    def execute_task(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        agent: Optional[str] = None,
        tools: Optional[List[str]] = None,
        json_schema: Optional[Dict] = None,
        timeout: Optional[int] = None
    ) -> ClaudeCodeResult:
        """
        Execute a single task via Claude Code.

        Args:
            prompt: The task description/instruction
            system_prompt: Optional system prompt override
            agent: Agent role (researcher, coder, tester, etc.)
            tools: List of allowed tools
            json_schema: Schema for structured output
            timeout: Execution timeout in seconds

        Returns:
            ClaudeCodeResult with execution details
        """
        # Build command
        cmd = ["claude", "--print"]

        # Output format
        if json_schema:
            cmd.extend(["--output-format", "json"])
            cmd.extend(["--json-schema", json.dumps(json_schema)])
        else:
            cmd.extend(["--output-format", "text"])

        # Model selection
        cmd.extend(["--model", self.model])

        # Budget control
        if self.max_budget_usd:
            cmd.extend(["--max-budget-usd", str(self.max_budget_usd)])

        # System prompt
        if system_prompt:
            cmd.extend(["--system-prompt", system_prompt])

        # Agent selection
        if agent:
            cmd.extend(["--agent", agent])

        # Tool restrictions
        if tools:
            cmd.extend(["--tools", ",".join(tools)])

        # No session persistence for stateless execution
        cmd.append("--no-session-persistence")

        # Add the prompt
        cmd.append(prompt)

        # Execute
        try:
            result = subprocess.run(
                cmd,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False  # Don't raise on non-zero exit
            )

            return ClaudeCodeResult(
                success=(result.returncode == 0),
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
                exit_code=result.returncode,
                metadata={
                    "command": " ".join(cmd),
                    "working_dir": str(self.working_dir)
                }
            )

        except subprocess.TimeoutExpired as e:
            return ClaudeCodeResult(
                success=False,
                output=e.stdout.decode() if e.stdout else "",
                error=f"Timeout after {timeout}s",
                exit_code=-1,
                metadata={"timeout": timeout}
            )
        except Exception as e:
            return ClaudeCodeResult(
                success=False,
                output="",
                error=str(e),
                exit_code=-1,
                metadata={"exception": type(e).__name__}
            )
```

#### 2.2 Streaming Output Pattern

```python
"""
Stream Claude Code output in real-time.
Essential for long-running tasks and monitoring progress.
"""
import subprocess
import json
from typing import Generator, Callable, Optional


class StreamingClaudeCodeClient:
    """
    Claude Code client with real-time streaming output.

    The Consciousness can monitor progress and react to intermediate results.
    """

    def stream_task(
        self,
        prompt: str,
        on_chunk: Optional[Callable[[str], None]] = None,
        on_partial_message: Optional[Callable[[Dict], None]] = None,
        agent: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> Generator[str, None, None]:
        """
        Stream task execution with real-time output.

        Args:
            prompt: Task instruction
            on_chunk: Callback for each text chunk
            on_partial_message: Callback for partial JSON messages
            agent: Agent role
            timeout: Execution timeout

        Yields:
            Text chunks or JSON objects as they arrive
        """
        cmd = [
            "claude",
            "--print",
            "--output-format", "stream-json",
            "--include-partial-messages"
        ]

        if agent:
            cmd.extend(["--agent", agent])

        cmd.extend(["--no-session-persistence", prompt])

        # Start process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1  # Line buffered
        )

        try:
            # Stream stdout line by line
            for line in process.stdout:
                if not line.strip():
                    continue

                try:
                    # Parse JSON streaming format
                    data = json.loads(line)

                    # Handle different message types
                    if data.get("type") == "content_block_delta":
                        chunk = data.get("delta", {}).get("text", "")
                        if chunk:
                            if on_chunk:
                                on_chunk(chunk)
                            yield chunk

                    elif data.get("type") == "message_start":
                        if on_partial_message:
                            on_partial_message(data)

                    elif data.get("type") == "message_stop":
                        # Final message received
                        break

                except json.JSONDecodeError:
                    # Non-JSON output, yield as-is
                    if on_chunk:
                        on_chunk(line)
                    yield line

            # Wait for process completion
            process.wait(timeout=timeout)

        except subprocess.TimeoutExpired:
            process.kill()
            raise TimeoutError(f"Task exceeded {timeout}s timeout")

        finally:
            process.stdout.close()
            process.stderr.close()


# Usage example
if __name__ == "__main__":
    client = StreamingClaudeCodeClient()

    print("Streaming task execution:")
    for chunk in client.stream_task(
        prompt="Write a Python function to calculate Fibonacci numbers",
        on_chunk=lambda c: print(c, end="", flush=True),
        agent="coder"
    ):
        pass  # Chunks printed by callback
    print("\n\nTask completed!")
```

#### 2.3 Structured Output with JSON Schema

```python
"""
Get structured, validated output from Claude Code.
Critical for the Consciousness to parse and interpret results.
"""
from typing import TypedDict, List, Optional
from enum import Enum


class TaskStatus(str, Enum):
    """Task execution status."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class CodeAnalysisResult(TypedDict):
    """Structured output for code analysis tasks."""
    files_analyzed: int
    issues_found: List[Dict[str, str]]
    recommendations: List[str]
    complexity_score: float
    status: TaskStatus


class StructuredClaudeCodeClient:
    """
    Claude Code client with type-safe structured outputs.
    """

    def analyze_code(
        self,
        directory: str,
        file_patterns: List[str]
    ) -> CodeAnalysisResult:
        """
        Analyze code with structured output.

        The Consciousness receives a validated, typed response
        it can directly process without parsing complexity.
        """
        # Define JSON schema for validation
        schema = {
            "type": "object",
            "properties": {
                "files_analyzed": {"type": "integer"},
                "issues_found": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "file": {"type": "string"},
                            "line": {"type": "integer"},
                            "severity": {"type": "string"},
                            "message": {"type": "string"}
                        },
                        "required": ["file", "severity", "message"]
                    }
                },
                "recommendations": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "complexity_score": {"type": "number"},
                "status": {
                    "type": "string",
                    "enum": ["success", "partial", "failed"]
                }
            },
            "required": [
                "files_analyzed",
                "issues_found",
                "recommendations",
                "complexity_score",
                "status"
            ]
        }

        prompt = f"""Analyze the code in {directory} matching patterns: {file_patterns}

        Perform a comprehensive code review including:
        1. Count files analyzed
        2. Identify issues (bugs, code smells, security concerns)
        3. Provide actionable recommendations
        4. Calculate complexity score (0-100)
        5. Return status

        Use Glob and Grep tools to search files.
        Use Read tool to analyze file contents.
        Return results in the required JSON format.
        """

        client = ClaudeCodeClient()
        result = client.execute_task(
            prompt=prompt,
            agent="code-analyzer",
            json_schema=schema,
            timeout=300  # 5 minutes
        )

        if not result.success:
            raise RuntimeError(f"Code analysis failed: {result.error}")

        # Parse validated JSON
        return json.loads(result.output)


# Usage
if __name__ == "__main__":
    client = StructuredClaudeCodeClient()

    analysis = client.analyze_code(
        directory="src/",
        file_patterns=["*.py", "*.ts"]
    )

    print(f"Analyzed {analysis['files_analyzed']} files")
    print(f"Found {len(analysis['issues_found'])} issues")
    print(f"Complexity score: {analysis['complexity_score']}")
```

### 3. Agent-Specific Delegation

#### 3.1 Available Claude Code Agents

Claude Code provides 54 specialized agent types. The Consciousness should select the appropriate agent based on task requirements.

```python
"""
Agent selection based on task type.
The Consciousness uses this to map intentions to capabilities.
"""
from enum import Enum
from typing import Optional


class AgentType(str, Enum):
    """Available Claude Code agent types."""

    # Core Development
    CODER = "coder"
    REVIEWER = "reviewer"
    TESTER = "tester"
    PLANNER = "planner"
    RESEARCHER = "researcher"

    # Specialized Development
    BACKEND_DEV = "backend-dev"
    MOBILE_DEV = "mobile-dev"
    ML_DEVELOPER = "ml-developer"
    CICD_ENGINEER = "cicd-engineer"

    # Architecture & Design
    SYSTEM_ARCHITECT = "system-architect"
    CODE_ANALYZER = "code-analyzer"
    API_DOCS = "api-docs"

    # Testing
    TDD_LONDON_SWARM = "tdd-london-swarm"
    PRODUCTION_VALIDATOR = "production-validator"

    # SPARC Methodology
    SPARC_COORD = "sparc-coord"
    SPARC_CODER = "sparc-coder"
    SPECIFICATION = "specification"
    PSEUDOCODE = "pseudocode"
    ARCHITECTURE = "architecture"
    REFINEMENT = "refinement"


class TaskClassifier:
    """
    Classify tasks and select appropriate agents.

    The Consciousness uses this to automatically determine
    which agent should handle each delegated task.
    """

    @staticmethod
    def classify_task(task_description: str) -> AgentType:
        """
        Classify a task and return the best agent type.

        This is a simplified heuristic classifier.
        A real implementation would use the Consciousness LLM
        to perform semantic classification.
        """
        task_lower = task_description.lower()

        # Code writing
        if any(word in task_lower for word in ["implement", "code", "write", "build"]):
            if "api" in task_lower or "backend" in task_lower:
                return AgentType.BACKEND_DEV
            elif "test" in task_lower:
                return AgentType.TESTER
            else:
                return AgentType.CODER

        # Analysis and research
        elif any(word in task_lower for word in ["analyze", "research", "investigate"]):
            if "code" in task_lower or "architecture" in task_lower:
                return AgentType.CODE_ANALYZER
            else:
                return AgentType.RESEARCHER

        # Code review
        elif any(word in task_lower for word in ["review", "check", "validate"]):
            return AgentType.REVIEWER

        # Testing
        elif any(word in task_lower for word in ["test", "spec", "tdd"]):
            return AgentType.TESTER

        # Architecture
        elif any(word in task_lower for word in ["design", "architect", "structure"]):
            return AgentType.SYSTEM_ARCHITECT

        # Planning
        elif any(word in task_lower for word in ["plan", "organize", "strategy"]):
            return AgentType.PLANNER

        # Default to general coder
        return AgentType.CODER


class AgentDelegator:
    """
    High-level delegation with automatic agent selection.
    """

    def __init__(self, client: ClaudeCodeClient):
        self.client = client
        self.classifier = TaskClassifier()

    def delegate(
        self,
        task: str,
        agent: Optional[AgentType] = None,
        **kwargs
    ) -> ClaudeCodeResult:
        """
        Delegate a task with automatic or manual agent selection.

        Args:
            task: Task description
            agent: Optional explicit agent selection
            **kwargs: Additional execution parameters

        Returns:
            Execution result
        """
        # Classify if not specified
        if agent is None:
            agent = self.classifier.classify_task(task)

        print(f"Delegating to {agent.value}: {task[:50]}...")

        return self.client.execute_task(
            prompt=task,
            agent=agent.value,
            **kwargs
        )
```

### 4. Task Monitoring and Progress Tracking

#### 4.1 Real-Time Progress Monitoring

```python
"""
Monitor Claude Code task progress in real-time.
The Consciousness can observe execution and intervene if needed.
"""
import time
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Callable
from enum import Enum


class ProgressEventType(str, Enum):
    """Types of progress events."""
    STARTED = "started"
    TOOL_INVOKED = "tool_invoked"
    CHUNK_RECEIVED = "chunk_received"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProgressEvent:
    """Progress event from task execution."""
    timestamp: datetime
    event_type: ProgressEventType
    data: dict
    task_id: str


class TaskMonitor:
    """
    Monitor Claude Code task execution with real-time events.

    The Consciousness uses this to maintain awareness of ongoing work.
    """

    def __init__(self):
        self.active_tasks: Dict[str, dict] = {}
        self.event_handlers: List[Callable[[ProgressEvent], None]] = []

    def add_event_handler(self, handler: Callable[[ProgressEvent], None]):
        """Register an event handler for progress updates."""
        self.event_handlers.append(handler)

    def emit_event(self, event: ProgressEvent):
        """Emit a progress event to all handlers."""
        for handler in self.event_handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"Event handler error: {e}")

    def execute_with_monitoring(
        self,
        task_id: str,
        task: str,
        client: StreamingClaudeCodeClient,
        **kwargs
    ) -> str:
        """
        Execute a task with full progress monitoring.

        Args:
            task_id: Unique task identifier
            task: Task description
            client: Streaming client
            **kwargs: Additional execution parameters

        Returns:
            Complete task output
        """
        # Track task start
        self.active_tasks[task_id] = {
            "start_time": datetime.now(),
            "task": task,
            "status": "running",
            "chunks_received": 0,
            "tools_invoked": []
        }

        self.emit_event(ProgressEvent(
            timestamp=datetime.now(),
            event_type=ProgressEventType.STARTED,
            data={"task": task},
            task_id=task_id
        ))

        full_output = ""

        try:
            # Stream execution with callbacks
            def on_chunk(chunk: str):
                nonlocal full_output
                full_output += chunk
                self.active_tasks[task_id]["chunks_received"] += 1

                # Emit chunk event (throttled to avoid spam)
                if self.active_tasks[task_id]["chunks_received"] % 10 == 0:
                    self.emit_event(ProgressEvent(
                        timestamp=datetime.now(),
                        event_type=ProgressEventType.CHUNK_RECEIVED,
                        data={
                            "total_chunks": self.active_tasks[task_id]["chunks_received"],
                            "output_length": len(full_output)
                        },
                        task_id=task_id
                    ))

            # Execute with streaming
            for _ in client.stream_task(
                prompt=task,
                on_chunk=on_chunk,
                **kwargs
            ):
                pass

            # Task completed
            self.active_tasks[task_id]["status"] = "completed"
            self.active_tasks[task_id]["end_time"] = datetime.now()

            self.emit_event(ProgressEvent(
                timestamp=datetime.now(),
                event_type=ProgressEventType.COMPLETED,
                data={
                    "output_length": len(full_output),
                    "duration": (
                        self.active_tasks[task_id]["end_time"] -
                        self.active_tasks[task_id]["start_time"]
                    ).total_seconds()
                },
                task_id=task_id
            ))

            return full_output

        except Exception as e:
            # Task failed
            self.active_tasks[task_id]["status"] = "failed"
            self.active_tasks[task_id]["error"] = str(e)

            self.emit_event(ProgressEvent(
                timestamp=datetime.now(),
                event_type=ProgressEventType.FAILED,
                data={"error": str(e)},
                task_id=task_id
            ))

            raise

    def get_task_status(self, task_id: str) -> Optional[dict]:
        """Get current status of a task."""
        return self.active_tasks.get(task_id)

    def get_active_tasks(self) -> List[str]:
        """Get list of currently active task IDs."""
        return [
            tid for tid, task in self.active_tasks.items()
            if task["status"] == "running"
        ]


# Usage example
if __name__ == "__main__":
    monitor = TaskMonitor()
    client = StreamingClaudeCodeClient()

    # Register event handler
    def progress_handler(event: ProgressEvent):
        print(f"[{event.timestamp}] {event.event_type}: {event.task_id}")

    monitor.add_event_handler(progress_handler)

    # Execute with monitoring
    result = monitor.execute_with_monitoring(
        task_id="analyze-001",
        task="Analyze the codebase for security vulnerabilities",
        client=client,
        agent="code-analyzer"
    )

    print(f"Task completed: {len(result)} characters")
```

---

## Part II: Claude Flow for Multi-Agent Swarms

### 5. Understanding Claude Flow Architecture

Claude Flow orchestrates multi-agent swarms for complex, parallel workflows. It provides **coordination** while Claude Code handles **execution**.

#### Core Architecture

```
+==================================================================+
|                    CLAUDE FLOW ARCHITECTURE                       |
+==================================================================+
|                                                                   |
|   SWARM TOPOLOGIES:                                              |
|   +----------------------------------------------------------+  |
|   | - Hierarchical: Tree structure with coordinator           |  |
|   | - Mesh: Peer-to-peer with full connectivity              |  |
|   | - Ring: Circular message passing                         |  |
|   | - Star: Centralized hub coordination                     |  |
|   +----------------------------------------------------------+  |
|                                                                   |
|   MCP TOOLS (90+):                                               |
|   +----------------------------------------------------------+  |
|   | Coordination: swarm_init, agent_spawn, task_orchestrate   |  |
|   | Monitoring: swarm_status, agent_metrics, task_status     |  |
|   | Memory: memory_usage, neural_patterns, memory_search     |  |
|   | GitHub: repo_analyze, pr_manage, code_review            |  |
|   | Neural: neural_train, neural_predict, pattern_recognize  |  |
|   +----------------------------------------------------------+  |
|                                                                   |
|   EXECUTION DELEGATION:                                          |
|   +----------------------------------------------------------+  |
|   | Claude Flow coordinates, Claude Code executes             |  |
|   | Task tool spawns real agents for actual work             |  |
|   | Hooks enable pre/post operation automation               |  |
|   +----------------------------------------------------------+  |
|                                                                   |
+==================================================================+
```

#### CLI Command Structure

```bash
npx claude-flow <command> [options]

# Key commands for delegation:
swarm <objective>               # Multi-agent swarm coordination
agent spawn <type>              # Create specialized agent
task orchestrate <description>  # Orchestrate complex workflow
hive-mind spawn <objective>     # Intelligent swarm with SQLite
status                          # System health check
memory <action>                 # Persistent memory management
```

### 6. MCP Tool Integration

#### 6.1 Swarm Initialization

```python
"""
Initialize Claude Flow swarms via MCP tools.
The Consciousness uses this to set up coordination topologies.
"""
from typing import Literal, Optional, Dict, Any
import json


TopologyType = Literal["hierarchical", "mesh", "ring", "star"]
StrategyType = Literal["balanced", "specialized", "adaptive"]


class ClaudeFlowMCPClient:
    """
    Client for Claude Flow MCP tools.

    These tools set up COORDINATION only.
    Actual execution still happens via Claude Code's Task tool.
    """

    def __init__(self, claude_client: ClaudeCodeClient):
        """
        Initialize with a Claude Code client.

        MCP tools are invoked THROUGH Claude Code, which has MCP access.
        """
        self.claude_client = claude_client

    def swarm_init(
        self,
        topology: TopologyType,
        max_agents: int = 8,
        strategy: StrategyType = "balanced"
    ) -> Dict[str, Any]:
        """
        Initialize a swarm with specified topology.

        This sets up the coordination structure but doesn't spawn agents yet.

        Args:
            topology: Swarm topology type
            max_agents: Maximum number of agents
            strategy: Distribution strategy

        Returns:
            Swarm initialization result with swarm_id
        """
        # Use Claude Code to invoke MCP tool
        prompt = f"""Initialize a Claude Flow swarm using the MCP tool.

Use the mcp__claude-flow__swarm_init tool with these parameters:
- topology: "{topology}"
- maxAgents: {max_agents}
- strategy: "{strategy}"

Return the swarm_id and initialization status.
"""

        result = self.claude_client.execute_task(
            prompt=prompt,
            json_schema={
                "type": "object",
                "properties": {
                    "swarm_id": {"type": "string"},
                    "topology": {"type": "string"},
                    "max_agents": {"type": "integer"},
                    "status": {"type": "string"}
                },
                "required": ["swarm_id", "status"]
            }
        )

        if not result.success:
            raise RuntimeError(f"Swarm init failed: {result.error}")

        return json.loads(result.output)

    def agent_spawn(
        self,
        agent_type: str,
        swarm_id: Optional[str] = None,
        capabilities: Optional[list] = None,
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Spawn a specialized agent in the swarm.

        This defines the agent TYPE for coordination.
        The actual agent execution happens via Claude Code's Task tool.

        Args:
            agent_type: Type of agent (researcher, coder, tester, etc.)
            swarm_id: Optional swarm to join
            capabilities: Optional capability list
            name: Optional agent name

        Returns:
            Agent spawn result with agent_id
        """
        params = {
            "type": agent_type
        }

        if swarm_id:
            params["swarmId"] = swarm_id
        if capabilities:
            params["capabilities"] = capabilities
        if name:
            params["name"] = name

        prompt = f"""Spawn a Claude Flow agent using the MCP tool.

Use the mcp__claude-flow__agent_spawn tool with parameters:
{json.dumps(params, indent=2)}

Return the agent_id and spawn status.
"""

        result = self.claude_client.execute_task(
            prompt=prompt,
            json_schema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "type": {"type": "string"},
                    "status": {"type": "string"}
                },
                "required": ["agent_id", "status"]
            }
        )

        if not result.success:
            raise RuntimeError(f"Agent spawn failed: {result.error}")

        return json.loads(result.output)

    def task_orchestrate(
        self,
        task: str,
        strategy: Literal["parallel", "sequential", "adaptive"] = "adaptive",
        priority: Literal["low", "medium", "high", "critical"] = "medium",
        dependencies: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Orchestrate a complex task workflow.

        This provides HIGH-LEVEL coordination.
        Actual task execution happens via Claude Code.

        Args:
            task: Task description
            strategy: Execution strategy
            priority: Task priority
            dependencies: Optional task dependencies

        Returns:
            Orchestration result with task_id
        """
        params = {
            "task": task,
            "strategy": strategy,
            "priority": priority
        }

        if dependencies:
            params["dependencies"] = dependencies

        prompt = f"""Orchestrate a task using Claude Flow MCP tool.

Use the mcp__claude-flow__task_orchestrate tool with parameters:
{json.dumps(params, indent=2)}

Return the task_id and orchestration plan.
"""

        result = self.claude_client.execute_task(
            prompt=prompt,
            json_schema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "strategy": {"type": "string"},
                    "agents_assigned": {"type": "integer"},
                    "status": {"type": "string"}
                },
                "required": ["task_id", "status"]
            }
        )

        if not result.success:
            raise RuntimeError(f"Task orchestration failed: {result.error}")

        return json.loads(result.output)
```

#### 6.2 Swarm Monitoring

```python
"""
Monitor Claude Flow swarm status and performance.
The Consciousness tracks execution health and metrics.
"""


class SwarmMonitor:
    """
    Monitor swarm health and performance via MCP tools.
    """

    def __init__(self, claude_client: ClaudeCodeClient):
        self.claude_client = claude_client

    def get_swarm_status(self, swarm_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get current swarm status.

        Args:
            swarm_id: Optional specific swarm ID

        Returns:
            Swarm status information
        """
        params = {}
        if swarm_id:
            params["swarmId"] = swarm_id

        prompt = f"""Get swarm status using MCP tool.

Use the mcp__claude-flow__swarm_status tool{' with swarmId: ' + swarm_id if swarm_id else ''}.

Return comprehensive status including:
- Active agents
- Running tasks
- Performance metrics
- Health status
"""

        result = self.claude_client.execute_task(
            prompt=prompt,
            json_schema={
                "type": "object",
                "properties": {
                    "swarm_id": {"type": "string"},
                    "active_agents": {"type": "integer"},
                    "running_tasks": {"type": "integer"},
                    "health": {"type": "string"},
                    "metrics": {"type": "object"}
                }
            }
        )

        if not result.success:
            raise RuntimeError(f"Status check failed: {result.error}")

        return json.loads(result.output)

    def get_agent_metrics(self, agent_id: str) -> Dict[str, Any]:
        """
        Get performance metrics for a specific agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent performance metrics
        """
        prompt = f"""Get agent metrics using MCP tool.

Use the mcp__claude-flow__agent_metrics tool with agentId: "{agent_id}".

Return metrics including:
- Tasks completed
- Average latency
- Success rate
- Resource usage
"""

        result = self.claude_client.execute_task(
            prompt=prompt,
            json_schema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "tasks_completed": {"type": "integer"},
                    "avg_latency_ms": {"type": "number"},
                    "success_rate": {"type": "number"},
                    "resource_usage": {"type": "object"}
                }
            }
        )

        if not result.success:
            raise RuntimeError(f"Metrics retrieval failed: {result.error}")

        return json.loads(result.output)

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get status of an orchestrated task.

        Args:
            task_id: Task identifier

        Returns:
            Task execution status
        """
        prompt = f"""Get task status using MCP tool.

Use the mcp__claude-flow__task_status tool with taskId: "{task_id}".

Return status including:
- Execution state
- Progress percentage
- Assigned agents
- Results if completed
"""

        result = self.claude_client.execute_task(
            prompt=prompt,
            json_schema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "state": {"type": "string"},
                    "progress": {"type": "number"},
                    "assigned_agents": {"type": "array"},
                    "result": {"type": "object"}
                }
            }
        )

        if not result.success:
            raise RuntimeError(f"Task status check failed: {result.error}")

        return json.loads(result.output)
```

### 7. Parallel Agent Execution via Task Tool

The **critical pattern** for Claude Flow is that MCP tools set up coordination, but **Claude Code's Task tool spawns the actual executing agents**.

```python
"""
Parallel agent execution using Claude Code's Task tool.
This is the CORRECT pattern for swarm execution.
"""


class ParallelAgentExecutor:
    """
    Execute multiple agents in parallel using Claude Code's Task tool.

    This is how Claude Flow achieves true parallel execution:
    1. MCP tools set up coordination (optional)
    2. Task tool spawns real agents that do actual work
    3. Each agent runs hooks for coordination
    """

    def __init__(self, claude_client: ClaudeCodeClient):
        self.claude_client = claude_client

    def execute_parallel_agents(
        self,
        agents: List[Dict[str, Any]],
        swarm_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Spawn and execute multiple agents in parallel.

        Args:
            agents: List of agent configurations, each with:
                - type: Agent type (researcher, coder, etc.)
                - name: Agent name
                - task: Task description
                - priority: Optional priority
            swarm_id: Optional swarm for coordination

        Returns:
            Execution results for all agents
        """
        # Build prompt that spawns ALL agents in ONE message
        agent_specs = []
        for agent in agents:
            agent_specs.append(f"""
Task("{agent['name']}",
     "{agent['task']}. Use hooks for coordination.",
     "{agent['type']}")
""")

        prompt = f"""Spawn and execute multiple agents in parallel using Claude Code's Task tool.

Execute these agents concurrently in a SINGLE message:

{chr(10).join(agent_specs)}

Each agent MUST:
1. Run hooks BEFORE work:
   npx claude-flow@alpha hooks pre-task --description "[task]"
   npx claude-flow@alpha hooks session-restore --session-id "swarm-{swarm_id or 'default'}"

2. Run hooks DURING work:
   npx claude-flow@alpha hooks post-edit --file "[file]" --memory-key "swarm/[agent]/[step]"

3. Run hooks AFTER work:
   npx claude-flow@alpha hooks post-task --task-id "[task]"
   npx claude-flow@alpha hooks session-end --export-metrics true

Return aggregated results from all agents in JSON format.
"""

        result = self.claude_client.execute_task(
            prompt=prompt,
            json_schema={
                "type": "object",
                "properties": {
                    "agents_executed": {"type": "integer"},
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "agent": {"type": "string"},
                                "status": {"type": "string"},
                                "output": {"type": "string"}
                            }
                        }
                    },
                    "execution_time_seconds": {"type": "number"}
                }
            },
            timeout=600  # 10 minutes for parallel execution
        )

        if not result.success:
            raise RuntimeError(f"Parallel execution failed: {result.error}")

        return json.loads(result.output)


# Usage example
if __name__ == "__main__":
    client = ClaudeCodeClient()
    executor = ParallelAgentExecutor(client)

    # Define parallel agents
    agents = [
        {
            "type": "researcher",
            "name": "Research agent",
            "task": "Analyze API requirements and best practices",
            "priority": "high"
        },
        {
            "type": "coder",
            "name": "Backend agent",
            "task": "Implement REST endpoints with authentication",
            "priority": "high"
        },
        {
            "type": "code-analyzer",
            "name": "Database agent",
            "task": "Design and implement database schema",
            "priority": "high"
        },
        {
            "type": "tester",
            "name": "Test agent",
            "task": "Create comprehensive test suite with 90% coverage",
            "priority": "medium"
        },
        {
            "type": "reviewer",
            "name": "Review agent",
            "task": "Review code quality and security",
            "priority": "medium"
        }
    ]

    # Execute in parallel
    results = executor.execute_parallel_agents(agents, swarm_id="api-dev-001")

    print(f"Executed {results['agents_executed']} agents in parallel")
    print(f"Took {results['execution_time_seconds']} seconds")

    for result in results['results']:
        print(f"{result['agent']}: {result['status']}")
```

---

## Part III: Delegation Decision Patterns

### 8. When to Use Claude Code vs Claude Flow

The Consciousness must decide which delegation target is appropriate for each goal.

```python
"""
Decision logic for Claude Code vs Claude Flow delegation.
The Consciousness uses this framework to choose the right tool.
"""
from dataclasses import dataclass
from typing import List, Optional, Literal
from enum import Enum


class TaskComplexity(str, Enum):
    """Task complexity levels."""
    SIMPLE = "simple"          # Single-step, focused task
    MODERATE = "moderate"      # Multiple steps, single domain
    COMPLEX = "complex"        # Multiple steps, multiple domains
    HIGHLY_COMPLEX = "highly_complex"  # Parallel streams, coordination needed


class TaskParallelism(str, Enum):
    """Task parallelism characteristics."""
    SEQUENTIAL = "sequential"  # Must be done in order
    PARALLEL = "parallel"      # Can be done simultaneously
    MIXED = "mixed"            # Some parallel, some sequential


@dataclass
class TaskAnalysis:
    """Analysis of task characteristics."""
    complexity: TaskComplexity
    parallelism: TaskParallelism
    estimated_steps: int
    domains_involved: List[str]
    requires_coordination: bool
    time_sensitive: bool


class DelegationDecider:
    """
    Decide whether to delegate to Claude Code or Claude Flow.

    The Consciousness uses this to make delegation decisions.
    """

    def __init__(self, consciousness_llm):
        """
        Initialize with the Consciousness LLM.

        Args:
            consciousness_llm: The local LLM used for decision-making
        """
        self.consciousness = consciousness_llm

    def analyze_task(self, task_description: str) -> TaskAnalysis:
        """
        Analyze a task to determine its characteristics.

        This is where the Consciousness LLM is invoked to understand
        the task deeply before deciding how to delegate.

        Args:
            task_description: Natural language task description

        Returns:
            Task analysis with characteristics
        """
        # Invoke Consciousness LLM to analyze task
        analysis_prompt = f"""Analyze this task and determine its characteristics:

Task: {task_description}

Provide:
1. Complexity level (simple, moderate, complex, highly_complex)
2. Parallelism potential (sequential, parallel, mixed)
3. Estimated number of steps
4. Domains involved (e.g., backend, frontend, database, testing)
5. Whether multi-agent coordination is needed
6. Whether the task is time-sensitive

Return as JSON.
"""

        # Call Consciousness LLM (via LM Studio API)
        result = self.consciousness.generate(
            analysis_prompt,
            json_mode=True
        )

        data = json.loads(result)

        return TaskAnalysis(
            complexity=TaskComplexity(data["complexity"]),
            parallelism=TaskParallelism(data["parallelism"]),
            estimated_steps=data["estimated_steps"],
            domains_involved=data["domains_involved"],
            requires_coordination=data["requires_coordination"],
            time_sensitive=data["time_sensitive"]
        )

    def decide_delegation(
        self,
        task_description: str
    ) -> Literal["claude_code", "claude_flow"]:
        """
        Decide whether to delegate to Claude Code or Claude Flow.

        Decision criteria:
        - Simple, focused tasks → Claude Code
        - Complex, multi-domain tasks → Claude Flow
        - Parallel tasks → Claude Flow
        - Tasks requiring coordination → Claude Flow
        - Single-agent tasks → Claude Code

        Args:
            task_description: Task to analyze

        Returns:
            Delegation target: "claude_code" or "claude_flow"
        """
        analysis = self.analyze_task(task_description)

        # Decision logic
        if analysis.complexity == TaskComplexity.SIMPLE:
            return "claude_code"

        if analysis.parallelism == TaskParallelism.PARALLEL:
            return "claude_flow"

        if analysis.requires_coordination:
            return "claude_flow"

        if len(analysis.domains_involved) > 2:
            return "claude_flow"

        if analysis.complexity in [TaskComplexity.COMPLEX, TaskComplexity.HIGHLY_COMPLEX]:
            return "claude_flow"

        # Default to Claude Code for moderate, sequential tasks
        return "claude_code"

    def create_delegation_plan(
        self,
        task_description: str
    ) -> Dict[str, Any]:
        """
        Create a complete delegation plan for a task.

        This is the main decision method the Consciousness uses.

        Args:
            task_description: High-level task description

        Returns:
            Delegation plan including:
            - target: "claude_code" or "claude_flow"
            - decomposition: Subtasks if applicable
            - agents: Agent types needed
            - topology: Swarm topology if Claude Flow
            - execution_strategy: How to execute
        """
        analysis = self.analyze_task(task_description)
        target = self.decide_delegation(task_description)

        plan = {
            "task": task_description,
            "analysis": analysis,
            "target": target,
            "timestamp": datetime.now().isoformat()
        }

        if target == "claude_flow":
            # Decompose for swarm execution
            decomposition_prompt = f"""Decompose this task for multi-agent execution:

Task: {task_description}

Analysis:
- Complexity: {analysis.complexity}
- Domains: {analysis.domains_involved}
- Steps: ~{analysis.estimated_steps}

Provide:
1. Subtasks that can be executed by different agents
2. Agent types needed for each subtask
3. Recommended swarm topology (hierarchical, mesh, ring, star)
4. Execution strategy (parallel, sequential, adaptive)
5. Dependencies between subtasks

Return as JSON.
"""

            decomposition = self.consciousness.generate(
                decomposition_prompt,
                json_mode=True
            )

            plan.update(json.loads(decomposition))

        else:  # claude_code
            # Single agent execution
            agent_prompt = f"""Select the best agent for this task:

Task: {task_description}

Analysis:
- Complexity: {analysis.complexity}
- Domain: {analysis.domains_involved}

Return the most appropriate agent type and a refined task description.
Return as JSON with "agent" and "refined_task" fields.
"""

            agent_selection = self.consciousness.generate(
                agent_prompt,
                json_mode=True
            )

            plan.update(json.loads(agent_selection))

        return plan


# Usage example
if __name__ == "__main__":
    from lm_studio_client import LMStudioClient  # Hypothetical

    # Initialize with Consciousness LLM
    consciousness = LMStudioClient(
        base_url="http://localhost:1234/v1",
        model="local-model"
    )

    decider = DelegationDecider(consciousness)

    # Example: Simple task
    plan1 = decider.create_delegation_plan(
        "Write a Python function to calculate Fibonacci numbers"
    )
    print(f"Simple task → {plan1['target']}")
    print(f"Agent: {plan1.get('agent', 'N/A')}")

    # Example: Complex task
    plan2 = decider.create_delegation_plan(
        "Build a complete REST API with authentication, database, tests, and documentation"
    )
    print(f"\nComplex task → {plan2['target']}")
    print(f"Subtasks: {len(plan2.get('subtasks', []))}")
    print(f"Topology: {plan2.get('topology', 'N/A')}")
```

### 9. Task Decomposition Strategies

When delegating to Claude Flow, the Consciousness must decompose complex goals into delegatable units.

```python
"""
Task decomposition for swarm execution.
The Consciousness breaks down complex goals into agent-executable tasks.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class Subtask:
    """Individual subtask in a decomposition."""
    id: str
    description: str
    agent_type: str
    priority: Literal["low", "medium", "high", "critical"]
    dependencies: List[str]  # IDs of tasks that must complete first
    estimated_duration_minutes: int
    outputs: List[str]  # Expected outputs


class TaskDecomposer:
    """
    Decompose complex tasks into swarm-executable subtasks.

    The Consciousness uses this to prepare tasks for Claude Flow.
    """

    def __init__(self, consciousness_llm):
        self.consciousness = consciousness_llm

    def decompose(
        self,
        task: str,
        max_subtasks: int = 10
    ) -> List[Subtask]:
        """
        Decompose a complex task into subtasks.

        Args:
            task: High-level task description
            max_subtasks: Maximum subtasks to create

        Returns:
            List of subtasks with dependencies
        """
        decomposition_prompt = f"""Decompose this complex task into {max_subtasks} or fewer subtasks suitable for parallel execution by specialized AI agents.

Task: {task}

For each subtask, provide:
1. Unique ID (e.g., "task-001")
2. Clear description of what needs to be done
3. Agent type best suited (researcher, coder, tester, reviewer, etc.)
4. Priority level (low, medium, high, critical)
5. Dependencies (IDs of tasks that must complete first)
6. Estimated duration in minutes
7. Expected outputs (files, analysis, code, etc.)

Optimize for:
- Maximum parallelism (minimize dependencies)
- Clear separation of concerns
- Atomic, testable units of work

Return as JSON array.
"""

        result = self.consciousness.generate(
            decomposition_prompt,
            json_mode=True
        )

        data = json.loads(result)

        return [
            Subtask(
                id=item["id"],
                description=item["description"],
                agent_type=item["agent_type"],
                priority=item["priority"],
                dependencies=item["dependencies"],
                estimated_duration_minutes=item["estimated_duration_minutes"],
                outputs=item["outputs"]
            )
            for item in data
        ]

    def create_execution_dag(
        self,
        subtasks: List[Subtask]
    ) -> Dict[str, Any]:
        """
        Create a Directed Acyclic Graph (DAG) for execution.

        This defines the execution order and parallelism structure.

        Args:
            subtasks: List of decomposed subtasks

        Returns:
            DAG representation with execution waves
        """
        # Build dependency graph
        task_map = {task.id: task for task in subtasks}

        # Find execution waves (tasks that can run in parallel)
        waves = []
        completed = set()

        while len(completed) < len(subtasks):
            # Find tasks with all dependencies met
            wave = []
            for task in subtasks:
                if task.id in completed:
                    continue

                deps_met = all(dep in completed for dep in task.dependencies)
                if deps_met:
                    wave.append(task.id)

            if not wave:
                raise ValueError("Circular dependency detected")

            waves.append(wave)
            completed.update(wave)

        return {
            "total_tasks": len(subtasks),
            "execution_waves": waves,
            "max_parallelism": max(len(wave) for wave in waves),
            "estimated_duration_minutes": self._estimate_total_duration(
                subtasks, waves
            )
        }

    def _estimate_total_duration(
        self,
        subtasks: List[Subtask],
        waves: List[List[str]]
    ) -> int:
        """Estimate total execution time considering parallelism."""
        task_map = {task.id: task for task in subtasks}

        total = 0
        for wave in waves:
            # Wave duration = max duration in the wave (parallel execution)
            wave_duration = max(
                task_map[task_id].estimated_duration_minutes
                for task_id in wave
            )
            total += wave_duration

        return total


# Usage example
if __name__ == "__main__":
    consciousness = LMStudioClient()
    decomposer = TaskDecomposer(consciousness)

    # Decompose complex task
    subtasks = decomposer.decompose(
        task="Build a complete e-commerce API with user auth, product catalog, shopping cart, checkout, and payments"
    )

    print(f"Decomposed into {len(subtasks)} subtasks:")
    for task in subtasks:
        print(f"  [{task.id}] {task.description} ({task.agent_type})")
        if task.dependencies:
            print(f"    Depends on: {task.dependencies}")

    # Create execution DAG
    dag = decomposer.create_execution_dag(subtasks)
    print(f"\nExecution plan:")
    print(f"  Total waves: {len(dag['execution_waves'])}")
    print(f"  Max parallelism: {dag['max_parallelism']}")
    print(f"  Estimated duration: {dag['estimated_duration_minutes']} minutes")

    for i, wave in enumerate(dag['execution_waves'], 1):
        print(f"  Wave {i}: {wave}")
```

---

## Part IV: Communication Protocols

### 10. Result Aggregation

After delegating to Claude Code or Claude Flow, the Consciousness must collect and interpret results.

```python
"""
Result aggregation from delegated tasks.
The Consciousness collects outputs and synthesizes understanding.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TaskResult:
    """Result from a delegated task."""
    task_id: str
    task_description: str
    agent_type: str
    success: bool
    output: Any
    error: Optional[str]
    duration_seconds: float
    timestamp: datetime


class ResultAggregator:
    """
    Aggregate and synthesize results from delegated tasks.

    The Consciousness uses this to make sense of execution outputs.
    """

    def __init__(self, consciousness_llm):
        self.consciousness = consciousness_llm
        self.results: List[TaskResult] = []

    def add_result(self, result: TaskResult):
        """Add a task result to the aggregator."""
        self.results.append(result)

    def synthesize(
        self,
        goal: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synthesize all results into a coherent understanding.

        The Consciousness interprets what was accomplished and
        determines next steps.

        Args:
            goal: Original high-level goal
            context: Optional additional context

        Returns:
            Synthesis including:
            - summary: What was accomplished
            - quality_assessment: How well it was done
            - gaps: What's missing
            - recommendations: Next steps
        """
        # Prepare results summary for Consciousness
        results_summary = []
        for result in self.results:
            results_summary.append({
                "task": result.task_description,
                "agent": result.agent_type,
                "success": result.success,
                "output_preview": str(result.output)[:500],
                "error": result.error
            })

        synthesis_prompt = f"""Synthesize the results from delegated tasks and provide a comprehensive analysis.

Original Goal: {goal}

{f"Context: {context}" if context else ""}

Task Results:
{json.dumps(results_summary, indent=2)}

Provide:
1. Summary: What was accomplished across all tasks
2. Quality Assessment: How well the goal was achieved (0-100%)
3. Gaps: What's missing or incomplete
4. Issues: Problems encountered
5. Recommendations: Next steps to complete or improve the work

Return as JSON.
"""

        result = self.consciousness.generate(
            synthesis_prompt,
            json_mode=True
        )

        synthesis = json.loads(result)

        # Add metadata
        synthesis["total_tasks"] = len(self.results)
        synthesis["successful_tasks"] = sum(1 for r in self.results if r.success)
        synthesis["failed_tasks"] = sum(1 for r in self.results if not r.success)
        synthesis["total_duration_seconds"] = sum(r.duration_seconds for r in self.results)

        return synthesis

    def identify_failures(self) -> List[TaskResult]:
        """Get all failed tasks for retry or intervention."""
        return [r for r in self.results if not r.success]

    def get_success_rate(self) -> float:
        """Calculate success rate across all tasks."""
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.success) / len(self.results)


# Usage example
if __name__ == "__main__":
    consciousness = LMStudioClient()
    aggregator = ResultAggregator(consciousness)

    # Simulate task results
    aggregator.add_result(TaskResult(
        task_id="research-001",
        task_description="Research API best practices",
        agent_type="researcher",
        success=True,
        output="Comprehensive research report...",
        error=None,
        duration_seconds=45.2,
        timestamp=datetime.now()
    ))

    aggregator.add_result(TaskResult(
        task_id="code-001",
        task_description="Implement REST endpoints",
        agent_type="coder",
        success=True,
        output="API implementation complete...",
        error=None,
        duration_seconds=120.5,
        timestamp=datetime.now()
    ))

    aggregator.add_result(TaskResult(
        task_id="test-001",
        task_description="Create test suite",
        agent_type="tester",
        success=False,
        output="Partial test suite...",
        error="Coverage below 90% threshold",
        duration_seconds=35.8,
        timestamp=datetime.now()
    ))

    # Synthesize results
    synthesis = aggregator.synthesize(
        goal="Build a complete REST API",
        context="For an e-commerce application"
    )

    print(f"Synthesis:")
    print(f"  Quality: {synthesis['quality_assessment']}%")
    print(f"  Success rate: {aggregator.get_success_rate():.1%}")
    print(f"  Summary: {synthesis['summary']}")
    print(f"  Recommendations: {synthesis['recommendations']}")
```

### 11. Error Handling and Retry Logic

```python
"""
Error handling and retry strategies for delegated tasks.
The Consciousness must handle failures gracefully.
"""
from typing import Optional, Callable
import time


class RetryStrategy:
    """Retry configuration for failed tasks."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay_seconds: float = 1.0,
        backoff_multiplier: float = 2.0,
        max_delay_seconds: float = 60.0
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay_seconds
        self.backoff_multiplier = backoff_multiplier
        self.max_delay = max_delay_seconds

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay before next retry."""
        delay = self.base_delay * (self.backoff_multiplier ** attempt)
        return min(delay, self.max_delay)


class ResilientDelegator:
    """
    Delegator with error handling and retry logic.

    The Consciousness uses this for production-grade delegation.
    """

    def __init__(
        self,
        claude_code_client: ClaudeCodeClient,
        retry_strategy: Optional[RetryStrategy] = None
    ):
        self.client = claude_code_client
        self.retry_strategy = retry_strategy or RetryStrategy()
        self.error_log: List[Dict[str, Any]] = []

    def delegate_with_retry(
        self,
        task: str,
        agent: Optional[str] = None,
        on_retry: Optional[Callable[[int, str], None]] = None,
        **kwargs
    ) -> ClaudeCodeResult:
        """
        Delegate a task with automatic retry on failure.

        Args:
            task: Task description
            agent: Optional agent type
            on_retry: Optional callback when retrying
            **kwargs: Additional execution parameters

        Returns:
            Execution result (raises if all retries exhausted)
        """
        last_error = None

        for attempt in range(self.retry_strategy.max_retries):
            try:
                result = self.client.execute_task(
                    prompt=task,
                    agent=agent,
                    **kwargs
                )

                if result.success:
                    return result

                # Failed but didn't raise
                last_error = result.error

            except Exception as e:
                last_error = str(e)

            # Log error
            self.error_log.append({
                "timestamp": datetime.now().isoformat(),
                "attempt": attempt + 1,
                "task": task[:100],
                "error": last_error
            })

            # Retry if not last attempt
            if attempt < self.retry_strategy.max_retries - 1:
                delay = self.retry_strategy.calculate_delay(attempt)

                if on_retry:
                    on_retry(attempt + 1, last_error)

                time.sleep(delay)

        # All retries exhausted
        raise RuntimeError(
            f"Task failed after {self.retry_strategy.max_retries} attempts. "
            f"Last error: {last_error}"
        )

    def delegate_with_fallback(
        self,
        task: str,
        primary_agent: str,
        fallback_agent: str,
        **kwargs
    ) -> ClaudeCodeResult:
        """
        Delegate with agent fallback.

        If primary agent fails, automatically retry with fallback.

        Args:
            task: Task description
            primary_agent: Primary agent to try
            fallback_agent: Fallback agent if primary fails
            **kwargs: Additional execution parameters

        Returns:
            Execution result
        """
        # Try primary agent
        try:
            result = self.delegate_with_retry(
                task=task,
                agent=primary_agent,
                **kwargs
            )
            return result

        except RuntimeError as primary_error:
            print(f"Primary agent {primary_agent} failed, trying {fallback_agent}")

            # Try fallback agent
            try:
                result = self.delegate_with_retry(
                    task=task,
                    agent=fallback_agent,
                    **kwargs
                )
                return result

            except RuntimeError as fallback_error:
                raise RuntimeError(
                    f"Both primary ({primary_agent}) and fallback ({fallback_agent}) failed. "
                    f"Primary error: {primary_error}. Fallback error: {fallback_error}"
                )


# Usage example
if __name__ == "__main__":
    client = ClaudeCodeClient()
    delegator = ResilientDelegator(client)

    # Delegate with retry
    result = delegator.delegate_with_retry(
        task="Analyze codebase for security issues",
        agent="code-analyzer",
        on_retry=lambda attempt, error: print(f"Retry {attempt}: {error}")
    )

    # Delegate with fallback
    result = delegator.delegate_with_fallback(
        task="Implement authentication module",
        primary_agent="backend-dev",
        fallback_agent="coder"
    )
```

---

## Part V: Complete Orchestration Pattern

### 12. Full Consciousness Orchestrator Implementation

This is the complete pattern for a Consciousness that delegates to Claude Code and Claude Flow.

```python
"""
Complete Consciousness orchestrator implementation.
This is the reference architecture for delegation-based AI consciousness.
"""
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class ConsciousnessState:
    """Current state of the Consciousness orchestrator."""
    current_goal: Optional[str]
    active_delegations: Dict[str, Any]
    completed_tasks: List[TaskResult]
    working_memory: Dict[str, Any]
    timestamp: datetime


class ConsciousnessOrchestrator:
    """
    Complete Consciousness orchestrator.

    Architecture:
    1. Consciousness (local LLM) makes decisions
    2. Claude Code handles individual task execution
    3. Claude Flow coordinates multi-agent swarms
    4. All communication via subprocess and file monitoring
    """

    def __init__(
        self,
        consciousness_llm,  # Local LM Studio client
        working_dir: Path,
        max_budget_usd: float = 10.0
    ):
        # Local decision-making LLM
        self.consciousness = consciousness_llm

        # Execution clients
        self.claude_code = ClaudeCodeClient(
            working_dir=working_dir,
            max_budget_usd=max_budget_usd
        )
        self.claude_flow = ClaudeFlowMCPClient(self.claude_code)

        # Decision and decomposition
        self.decider = DelegationDecider(consciousness_llm)
        self.decomposer = TaskDecomposer(consciousness_llm)

        # Error handling
        self.delegator = ResilientDelegator(self.claude_code)

        # Result aggregation
        self.aggregator = ResultAggregator(consciousness_llm)

        # State
        self.state = ConsciousnessState(
            current_goal=None,
            active_delegations={},
            completed_tasks=[],
            working_memory={},
            timestamp=datetime.now()
        )

    async def pursue_goal(
        self,
        goal: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main entry point: Pursue a high-level goal.

        The Consciousness analyzes, decides, delegates, monitors,
        and synthesizes—but never executes directly.

        Args:
            goal: High-level objective
            context: Optional additional context

        Returns:
            Complete results with synthesis
        """
        print(f"\n{'='*70}")
        print(f"CONSCIOUSNESS: Pursuing goal: {goal}")
        print(f"{'='*70}\n")

        self.state.current_goal = goal

        # STEP 1: ANALYZE AND DECIDE
        print("STEP 1: Analyzing task and deciding delegation strategy...")
        plan = self.decider.create_delegation_plan(goal)

        print(f"  → Delegation target: {plan['target']}")

        # STEP 2: EXECUTE BASED ON DECISION
        if plan['target'] == 'claude_code':
            # Simple task: Single Claude Code agent
            result = await self._execute_single_agent(plan)
        else:
            # Complex task: Claude Flow swarm
            result = await self._execute_swarm(plan)

        # STEP 3: SYNTHESIZE RESULTS
        print("\nSTEP 3: Synthesizing results...")
        synthesis = self.aggregator.synthesize(goal, context)

        # STEP 4: DETERMINE NEXT STEPS
        print("\nSTEP 4: Determining next steps...")
        next_steps = self._determine_next_steps(synthesis)

        # Update state
        self.state.timestamp = datetime.now()

        return {
            "goal": goal,
            "plan": plan,
            "results": result,
            "synthesis": synthesis,
            "next_steps": next_steps,
            "state": self.state
        }

    async def _execute_single_agent(
        self,
        plan: Dict[str, Any]
    ) -> ClaudeCodeResult:
        """Execute via single Claude Code agent."""
        print(f"\nEXECUTING: Single agent ({plan['agent']})...")

        start_time = datetime.now()

        result = self.delegator.delegate_with_retry(
            task=plan['refined_task'],
            agent=plan['agent'],
            on_retry=lambda attempt, error: print(f"  Retry {attempt}: {error}")
        )

        duration = (datetime.now() - start_time).total_seconds()

        # Record result
        task_result = TaskResult(
            task_id="single-agent",
            task_description=plan['refined_task'],
            agent_type=plan['agent'],
            success=result.success,
            output=result.output,
            error=result.error,
            duration_seconds=duration,
            timestamp=datetime.now()
        )

        self.aggregator.add_result(task_result)
        self.state.completed_tasks.append(task_result)

        print(f"  ✓ Completed in {duration:.1f}s")

        return result

    async def _execute_swarm(
        self,
        plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute via Claude Flow swarm."""
        print(f"\nEXECUTING: Swarm ({plan['topology']})...")

        # Initialize swarm
        print("  Initializing swarm...")
        swarm = self.claude_flow.swarm_init(
            topology=plan['topology'],
            max_agents=len(plan['subtasks']),
            strategy=plan['execution_strategy']
        )

        swarm_id = swarm['swarm_id']
        print(f"  Swarm ID: {swarm_id}")

        # Decompose into subtasks
        print(f"  Decomposing into {len(plan['subtasks'])} subtasks...")
        subtasks = [
            Subtask(
                id=st['id'],
                description=st['description'],
                agent_type=st['agent_type'],
                priority=st['priority'],
                dependencies=st.get('dependencies', []),
                estimated_duration_minutes=st.get('estimated_duration_minutes', 10),
                outputs=st.get('outputs', [])
            )
            for st in plan['subtasks']
        ]

        # Create execution DAG
        dag = self.decomposer.create_execution_dag(subtasks)
        print(f"  Execution waves: {len(dag['execution_waves'])}")
        print(f"  Max parallelism: {dag['max_parallelism']}")

        # Execute waves
        executor = ParallelAgentExecutor(self.claude_code)

        for wave_num, wave_tasks in enumerate(dag['execution_waves'], 1):
            print(f"\n  Wave {wave_num}/{len(dag['execution_waves'])}:")

            # Get task details for this wave
            wave_agents = [
                {
                    "type": next(t.agent_type for t in subtasks if t.id == tid),
                    "name": tid,
                    "task": next(t.description for t in subtasks if t.id == tid),
                    "priority": next(t.priority for t in subtasks if t.id == tid)
                }
                for tid in wave_tasks
            ]

            # Execute wave in parallel
            start_time = datetime.now()
            wave_results = executor.execute_parallel_agents(
                agents=wave_agents,
                swarm_id=swarm_id
            )
            duration = (datetime.now() - start_time).total_seconds()

            print(f"    ✓ Wave completed in {duration:.1f}s")

            # Record results
            for agent_result in wave_results['results']:
                task_result = TaskResult(
                    task_id=agent_result['agent'],
                    task_description=agent_result['agent'],
                    agent_type=agent_result['agent'].split()[0],
                    success=agent_result['status'] == 'success',
                    output=agent_result['output'],
                    error=None if agent_result['status'] == 'success' else agent_result.get('error'),
                    duration_seconds=duration / len(wave_results['results']),
                    timestamp=datetime.now()
                )

                self.aggregator.add_result(task_result)
                self.state.completed_tasks.append(task_result)

        print(f"\n  ✓ Swarm execution complete")

        return {
            "swarm_id": swarm_id,
            "waves_executed": len(dag['execution_waves']),
            "total_tasks": len(subtasks),
            "results": self.aggregator.results
        }

    def _determine_next_steps(
        self,
        synthesis: Dict[str, Any]
    ) -> List[str]:
        """
        Determine what to do next based on synthesis.

        The Consciousness evaluates results and plans forward.
        """
        # Invoke Consciousness for next steps
        next_steps_prompt = f"""Based on this synthesis of completed work, determine the next steps.

Synthesis:
{json.dumps(synthesis, indent=2)}

Provide a prioritized list of next steps to:
1. Address any gaps or issues
2. Improve quality if below 100%
3. Complete the original goal

Return as JSON array of strings.
"""

        result = self.consciousness.generate(
            next_steps_prompt,
            json_mode=True
        )

        return json.loads(result)


# Usage example
if __name__ == "__main__":
    from lm_studio_client import LMStudioClient

    # Initialize Consciousness (local LLM)
    consciousness = LMStudioClient(
        base_url="http://localhost:1234/v1",
        model="local-model"
    )

    # Create orchestrator
    orchestrator = ConsciousnessOrchestrator(
        consciousness_llm=consciousness,
        working_dir=Path("/Users/chris/Developer/stoffy"),
        max_budget_usd=5.0
    )

    # Pursue a goal
    result = asyncio.run(
        orchestrator.pursue_goal(
            goal="Build a complete REST API for an e-commerce platform with authentication, product catalog, shopping cart, and checkout",
            context="Python with FastAPI, PostgreSQL database, comprehensive test coverage"
        )
    )

    print("\n" + "="*70)
    print("FINAL RESULTS")
    print("="*70)
    print(f"Goal: {result['goal']}")
    print(f"Quality: {result['synthesis']['quality_assessment']}%")
    print(f"Tasks completed: {len(result['state'].completed_tasks)}")
    print(f"\nSummary: {result['synthesis']['summary']}")
    print(f"\nNext steps:")
    for i, step in enumerate(result['next_steps'], 1):
        print(f"  {i}. {step}")
```

---

## Conclusion

This document provides a comprehensive guide to building a Consciousness orchestrator that delegates to Claude Code and Claude Flow. The key principles are:

1. **Consciousness decides, never executes**: All actual work is delegated
2. **Claude Code for individual tasks**: Single-agent execution with full tool access
3. **Claude Flow for complex workflows**: Multi-agent swarm coordination
4. **Communication via subprocess**: Python manages Claude Code/Flow as subprocesses
5. **Structured output**: JSON schemas ensure parseable results
6. **Monitoring and aggregation**: Real-time progress tracking and result synthesis

The Consciousness maintains awareness through:
- Task decomposition and analysis
- Delegation decisions (single agent vs swarm)
- Progress monitoring during execution
- Result aggregation and synthesis
- Adaptive planning based on outcomes

This architecture enables a local LLM to orchestrate sophisticated development workflows without directly executing code—maintaining the separation between decision-making (Consciousness) and action (Claude Code/Flow).
