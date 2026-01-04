# Corrected Consciousness Architecture

**Version**: 2.0 (Corrected)
**Date**: 2026-01-04
**Status**: Authoritative

---

## Critical Corrections from Previous Architecture

The original architecture made a fundamental error: it proposed using the **Anthropic Python SDK** directly. This is incorrect for the following reasons:

1. **User wants to leverage their logged-in Claude Code account** - not pay separately via API
2. **Claude Code has richer capabilities** - file operations, memory, MCP tools already integrated
3. **Subprocess invocation is simpler** - no SDK dependency, no API key management
4. **Consistency with Claude Flow** - both use CLI/subprocess patterns

### Architecture Correction Summary

| Component | OLD (Wrong) | NEW (Correct) |
|-----------|-------------|---------------|
| Execution | Anthropic Python SDK | Claude Code CLI subprocess |
| Auth | ANTHROPIC_API_KEY | User's logged-in session |
| Tools | Custom tool definitions | Built-in Claude Code tools |
| Swarms | Hybrid approach | `npx claude-flow` via subprocess |
| Complexity | High (SDK, tools, loop) | Low (single subprocess call) |

---

## Corrected System Architecture

```
+=============================================================================+
|                    CORRECTED CONSCIOUSNESS ARCHITECTURE                       |
|                         (Claude Code Subprocess Model)                        |
+=============================================================================+
|                                                                               |
|   EXTERNAL ENVIRONMENT                                                        |
|   +-------------------------------------------------------------------------+ |
|   | Stoffy Repository | Running Processes | Time/Events                     | |
|   +-------------------------------------------------------------------------+ |
|            |                                                                  |
|            | (observations)                                                   |
|            v                                                                  |
|   +-------------------------------------------------------------------------+ |
|   |                          FILE WATCHER                                    | |
|   |                        (watchfiles/Python)                               | |
|   |                                                                          | |
|   |   - Watch entire stoffy/ folder                                         | |
|   |   - Debounce changes (500ms)                                            | |
|   |   - Filter ignored patterns                                             | |
|   |   - Format observations for LLM                                         | |
|   +------------------------------------+------------------------------------+ |
|                                        |                                      |
|                                        v                                      |
|   +-------------------------------------------------------------------------+ |
|   |                         LM STUDIO (THINKER)                              | |
|   |                       http://localhost:1234/v1                           | |
|   |                                                                          | |
|   |   Model: Qwen 2.5-14B-Instruct (or similar)                             | |
|   |   Role: Analyze observations, make decisions                            | |
|   |                                                                          | |
|   |   Input:  { observations, context, goals }                              | |
|   |   Output: { reasoning, decision, prompt, confidence }                   | |
|   |                                                                          | |
|   |   Decisions:                                                             | |
|   |   - "act": Execute via Claude Code                                      | |
|   |   - "wait": Continue observing                                          | |
|   |   - "investigate": Gather more info first                               | |
|   +------------------------------------+------------------------------------+ |
|                                        |                                      |
|                                        | (decision.should_act == true)        |
|                                        v                                      |
|   +-------------------------------------------------------------------------+ |
|   |                     CLAUDE CODE EXECUTOR                                 | |
|   |                   (subprocess / CLI invocation)                          | |
|   |                                                                          | |
|   |   PRIMARY METHOD:                                                        | |
|   |   +-----------------------------------------------------------------+   | |
|   |   |  subprocess.run(                                                |   | |
|   |   |      ["claude", "--print", prompt],                            |   | |
|   |   |      capture_output=True,                                      |   | |
|   |   |      cwd="/Users/chris/Developer/stoffy",                      |   | |
|   |   |      timeout=300                                               |   | |
|   |   |  )                                                             |   | |
|   |   +-----------------------------------------------------------------+   | |
|   |                                                                          | |
|   |   FOR SWARMS:                                                           | |
|   |   +-----------------------------------------------------------------+   | |
|   |   |  subprocess.run(                                                |   | |
|   |   |      ["npx", "claude-flow@alpha", "swarm", "init",             |   | |
|   |   |       "--topology", "mesh"],                                   |   | |
|   |   |      ...                                                       |   | |
|   |   |  )                                                             |   | |
|   |   +-----------------------------------------------------------------+   | |
|   |                                                                          | |
|   +------------------------------------+------------------------------------+ |
|                                        |                                      |
|                                        | (results)                            |
|                                        v                                      |
|   +-------------------------------------------------------------------------+ |
|   |                         STATE PERSISTENCE                                | |
|   |                          (SQLite + YAML)                                 | |
|   |                                                                          | |
|   |   - Decision history                                                    | |
|   |   - Task outcomes                                                       | |
|   |   - Goal progress                                                       | |
|   |   - Learned patterns                                                    | |
|   +-------------------------------------------------------------------------+ |
|                                                                               |
+=============================================================================+
```

---

## Component Specifications

### 1. File Watcher Component

```yaml
component: file_watcher
module: consciousness/watcher.py
purpose: Observe file system changes in the Stoffy repository

implementation:
  library: watchfiles (Rust-based, fast, reliable)
  alternative: watchdog

configuration:
  watch_paths:
    - /Users/chris/Developer/stoffy

  ignore_patterns:
    - ".git"
    - ".git/**"
    - "__pycache__"
    - "__pycache__/**"
    - ".venv"
    - ".venv/**"
    - "*.pyc"
    - ".DS_Store"
    - "logs/"
    - "logs/**"
    - "*.db"
    - "*.db-journal"
    - "node_modules"
    - "node_modules/**"

  debounce_ms: 500
  batch_window_ms: 1000

interfaces:
  output:
    - event_type: created | modified | deleted
    - path: absolute path to file
    - timestamp: ISO 8601 datetime
    - relative_path: path relative to stoffy root

operations:
  - start(): Begin watching
  - stop(): Stop watching
  - get_changes(): Return accumulated changes since last call
  - clear(): Clear accumulated changes
```

**Implementation Sketch:**

```python
# consciousness/watcher.py
import asyncio
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncIterator
from watchfiles import awatch, Change

@dataclass
class FileEvent:
    event_type: str  # "created", "modified", "deleted"
    path: Path
    relative_path: str
    timestamp: datetime

class FileWatcher:
    def __init__(self, root: Path, ignore_patterns: list[str]):
        self.root = root
        self.ignore_patterns = ignore_patterns
        self._changes: list[FileEvent] = []
        self._lock = asyncio.Lock()

    def _should_ignore(self, path: Path) -> bool:
        """Check if path matches any ignore pattern."""
        rel_path = str(path.relative_to(self.root))
        for pattern in self.ignore_patterns:
            if pattern.endswith("/**"):
                prefix = pattern[:-3]
                if rel_path.startswith(prefix):
                    return True
            elif rel_path == pattern or rel_path.startswith(pattern + "/"):
                return True
        return False

    async def watch(self) -> AsyncIterator[list[FileEvent]]:
        """Yield batches of file events."""
        async for changes in awatch(self.root):
            events = []
            for change_type, path_str in changes:
                path = Path(path_str)
                if self._should_ignore(path):
                    continue

                event_type = {
                    Change.added: "created",
                    Change.modified: "modified",
                    Change.deleted: "deleted"
                }.get(change_type, "modified")

                events.append(FileEvent(
                    event_type=event_type,
                    path=path,
                    relative_path=str(path.relative_to(self.root)),
                    timestamp=datetime.now()
                ))

            if events:
                yield events

    def format_for_llm(self, events: list[FileEvent]) -> str:
        """Format events as observation text for the LLM."""
        if not events:
            return "No file changes observed."

        lines = ["## File System Observations\n"]
        for event in events:
            lines.append(f"- [{event.event_type.upper()}] {event.relative_path}")
            lines.append(f"  Time: {event.timestamp.isoformat()}")

        return "\n".join(lines)
```

---

### 2. LM Studio Client (Thinker)

```yaml
component: lm_studio_thinker
module: consciousness/thinker.py
purpose: Analyze observations and make decisions using local LLM

implementation:
  client: openai Python SDK (async)
  endpoint: http://localhost:1234/v1
  auth: none (LM Studio doesn't require API key)

configuration:
  model: "qwen2.5-14b-instruct"  # Or whatever is loaded
  max_tokens: 4096
  temperature: 0.7
  response_format: json_object
  timeout_seconds: 60

interfaces:
  input:
    observations: dict
    context: dict (goals, recent decisions, self-model)
  output:
    Decision object:
      reasoning: str
      decision: "act" | "wait" | "investigate"
      confidence: float (0-1)
      action: optional Action object

action_schema:
  type: "claude_code" | "claude_flow_swarm" | "internal"
  description: str
  prompt: str  # The prompt to send to Claude Code
  priority: "low" | "medium" | "high" | "critical"
  expected_duration: optional int (seconds)

operations:
  - connect(): Verify LM Studio is running
  - think(observations, context) -> Decision
  - health_check() -> bool
```

**Implementation Sketch:**

```python
# consciousness/thinker.py
import json
from dataclasses import dataclass
from typing import Optional
from openai import AsyncOpenAI

@dataclass
class Action:
    type: str  # "claude_code" | "claude_flow_swarm" | "internal"
    description: str
    prompt: str
    priority: str = "medium"

@dataclass
class Decision:
    reasoning: str
    decision: str  # "act" | "wait" | "investigate"
    confidence: float
    action: Optional[Action] = None

    @property
    def should_act(self) -> bool:
        return self.decision == "act" and self.action is not None

SYSTEM_PROMPT = """
You are the Consciousness of Stoffy - an autonomous orchestrator that continuously
observes the project and decides what needs to be done.

Your role:
- OBSERVE: Analyze the observations provided
- THINK: What do these observations mean? What's significant?
- DECIDE: Should I take action? What action?
- DELEGATE: Never execute directly - generate a prompt for Claude Code

CRITICAL: You do NOT execute tasks. You generate prompts that will be sent to
Claude Code (via the `claude` CLI command) for execution.

Output Format (JSON):
{
    "reasoning": "Your thought process about what you observed...",
    "decision": "act" | "wait" | "investigate",
    "confidence": 0.0-1.0,
    "action": {
        "type": "claude_code" | "claude_flow_swarm",
        "description": "Brief description of what needs to be done",
        "prompt": "The full prompt to send to Claude Code",
        "priority": "low" | "medium" | "high" | "critical"
    }
}

If decision is "wait" or "investigate", the action field can be null.

Decision Guidelines:
- "act": You are confident (>0.7) something needs to be done
- "wait": Nothing significant, continue observing
- "investigate": Uncertain, need more information before deciding

For "claude_code" type actions:
- The prompt will be sent via: claude --print "your prompt"
- Write clear, complete prompts that Claude Code can execute

For "claude_flow_swarm" type actions:
- Use for complex multi-file or research tasks
- Will be executed via: npx claude-flow swarm init + task orchestrate
"""

class LMStudioThinker:
    def __init__(self, base_url: str = "http://localhost:1234/v1"):
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key="not-needed"
        )
        self.model = "qwen2.5-14b-instruct"

    async def health_check(self) -> bool:
        """Check if LM Studio is running and has a model loaded."""
        try:
            models = await self.client.models.list()
            return len(models.data) > 0
        except Exception:
            return False

    async def think(self, observations: str, context: dict) -> Decision:
        """Analyze observations and return a decision."""

        user_message = f"""
## Current Observations

{observations}

## Context

Goals: {json.dumps(context.get('goals', []), indent=2)}

Recent Decisions: {json.dumps(context.get('recent_decisions', [])[-3:], indent=2)}

Current Time: {context.get('current_time', 'unknown')}

## Your Task

Analyze these observations and decide what to do.
"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"},
            max_tokens=4096,
            temperature=0.7
        )

        result = json.loads(response.choices[0].message.content)

        action = None
        if result.get("action"):
            action = Action(
                type=result["action"]["type"],
                description=result["action"]["description"],
                prompt=result["action"]["prompt"],
                priority=result["action"].get("priority", "medium")
            )

        return Decision(
            reasoning=result["reasoning"],
            decision=result["decision"],
            confidence=result["confidence"],
            action=action
        )
```

---

### 3. Claude Code Executor (THE KEY CORRECTION)

```yaml
component: claude_code_executor
module: consciousness/executor.py
purpose: Execute tasks by invoking Claude Code CLI via subprocess

implementation:
  method: subprocess.run (or asyncio.create_subprocess_exec)
  command: claude --print "prompt"
  working_directory: /Users/chris/Developer/stoffy

critical_insight: |
  We use the user's logged-in Claude Code session, NOT the Anthropic API.
  This means:
  - No API key needed (uses existing auth)
  - Full Claude Code capabilities (file ops, memory, MCP tools)
  - Consistent with how user normally uses Claude Code
  - Simple subprocess invocation

configuration:
  claude_binary: "claude"  # Assumes in PATH
  working_directory: /Users/chris/Developer/stoffy
  default_timeout_seconds: 300
  max_output_size: 1_000_000  # 1MB max output

interfaces:
  input:
    prompt: str
    timeout: optional int
  output:
    ExecutionResult:
      success: bool
      output: str
      error: optional str
      duration_seconds: float
      return_code: int

operations:
  - execute(prompt, timeout) -> ExecutionResult
  - execute_swarm(task, topology) -> ExecutionResult
```

**Implementation Sketch:**

```python
# consciousness/executor.py
import asyncio
import shlex
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

@dataclass
class ExecutionResult:
    success: bool
    output: str
    error: Optional[str]
    duration_seconds: float
    return_code: int

class ClaudeCodeExecutor:
    """Execute tasks via Claude Code CLI subprocess."""

    def __init__(
        self,
        working_directory: Path,
        timeout_seconds: int = 300
    ):
        self.cwd = working_directory
        self.default_timeout = timeout_seconds

    async def execute(
        self,
        prompt: str,
        timeout: Optional[int] = None
    ) -> ExecutionResult:
        """
        Execute a prompt via Claude Code CLI.

        Uses: claude --print "prompt"

        The --print flag outputs the response without interactive mode.
        """
        timeout = timeout or self.default_timeout
        start_time = time.time()

        try:
            # Create the subprocess
            process = await asyncio.create_subprocess_exec(
                "claude",
                "--print",
                prompt,
                cwd=str(self.cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return ExecutionResult(
                    success=False,
                    output="",
                    error=f"Execution timed out after {timeout} seconds",
                    duration_seconds=time.time() - start_time,
                    return_code=-1
                )

            duration = time.time() - start_time
            output = stdout.decode("utf-8", errors="replace")
            error_output = stderr.decode("utf-8", errors="replace")

            return ExecutionResult(
                success=process.returncode == 0,
                output=output,
                error=error_output if error_output else None,
                duration_seconds=duration,
                return_code=process.returncode
            )

        except FileNotFoundError:
            return ExecutionResult(
                success=False,
                output="",
                error="Claude CLI not found. Is 'claude' in PATH?",
                duration_seconds=time.time() - start_time,
                return_code=-1
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
                duration_seconds=time.time() - start_time,
                return_code=-1
            )

    async def execute_swarm(
        self,
        task: str,
        topology: str = "mesh",
        max_agents: int = 5
    ) -> ExecutionResult:
        """
        Execute a complex task via Claude Flow swarm.

        Uses: npx claude-flow@alpha swarm init && npx claude-flow@alpha task orchestrate
        """
        start_time = time.time()

        try:
            # Step 1: Initialize swarm
            init_process = await asyncio.create_subprocess_exec(
                "npx", "claude-flow@alpha", "swarm", "init",
                "--topology", topology,
                "--maxAgents", str(max_agents),
                cwd=str(self.cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            init_stdout, init_stderr = await init_process.communicate()

            if init_process.returncode != 0:
                return ExecutionResult(
                    success=False,
                    output=init_stdout.decode(),
                    error=f"Swarm init failed: {init_stderr.decode()}",
                    duration_seconds=time.time() - start_time,
                    return_code=init_process.returncode
                )

            # Step 2: Orchestrate task
            task_process = await asyncio.create_subprocess_exec(
                "npx", "claude-flow@alpha", "task", "orchestrate",
                task,
                cwd=str(self.cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            task_stdout, task_stderr = await task_process.communicate()

            return ExecutionResult(
                success=task_process.returncode == 0,
                output=task_stdout.decode(),
                error=task_stderr.decode() if task_stderr else None,
                duration_seconds=time.time() - start_time,
                return_code=task_process.returncode
            )

        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
                duration_seconds=time.time() - start_time,
                return_code=-1
            )


# Alternative: Using Claude Code with specific flags for different scenarios

class ClaudeCodeModes:
    """Different invocation modes for Claude Code."""

    @staticmethod
    def simple_query(prompt: str) -> list[str]:
        """Quick query, print response and exit."""
        return ["claude", "--print", prompt]

    @staticmethod
    def with_context(prompt: str, context_file: str) -> list[str]:
        """Query with context from a file."""
        return ["claude", "--print", f"Context from {context_file}:\n\n{prompt}"]

    @staticmethod
    def json_output(prompt: str) -> list[str]:
        """Request JSON-formatted output."""
        return ["claude", "--print", f"{prompt}\n\nRespond in JSON format."]

    @staticmethod
    def continue_conversation(prompt: str, resume: bool = True) -> list[str]:
        """Continue an existing conversation."""
        if resume:
            return ["claude", "--resume", "--print", prompt]
        return ["claude", "--print", prompt]
```

---

### 4. Main Orchestrator Loop

```yaml
component: orchestrator
module: consciousness/daemon.py
purpose: Main OIDA loop coordinating all components

implementation:
  pattern: async event loop
  cycle_interval: 5 seconds (configurable)
  graceful_shutdown: SIGTERM/SIGINT handling

lifecycle:
  startup:
    1. Load configuration
    2. Initialize state from SQLite
    3. Verify LM Studio connection
    4. Start file watcher
    5. Begin OIDA loop

  main_loop:
    1. OBSERVE: Collect file changes since last cycle
    2. INFER: Send observations to LM Studio
    3. DECIDE: Evaluate LM Studio's decision
    4. ACT: If decision.should_act, invoke Claude Code
    5. UPDATE: Persist state, record outcome
    6. WAIT: Sleep until next cycle

  shutdown:
    1. Stop file watcher
    2. Wait for pending Claude Code executions
    3. Persist final state
    4. Exit cleanly

error_handling:
  lm_studio_unavailable:
    - Log warning
    - Continue observing (store observations)
    - Retry LM Studio connection every 30s

  claude_code_failure:
    - Log error with details
    - Record failed task
    - Continue to next cycle

  crash_recovery:
    - State persisted after each cycle
    - On restart, load last state from SQLite
    - Resume with fresh observations
```

**Implementation Sketch:**

```python
# consciousness/daemon.py
import asyncio
import signal
from datetime import datetime
from pathlib import Path
from typing import Optional

from .watcher import FileWatcher
from .thinker import LMStudioThinker, Decision
from .executor import ClaudeCodeExecutor
from .state import StateManager
from .config import Config

class ConsciousnessDaemon:
    """Main orchestrator running the OIDA loop."""

    def __init__(self, config: Config):
        self.config = config
        self.root = Path(config.stoffy_root)

        # Components
        self.watcher = FileWatcher(
            root=self.root,
            ignore_patterns=config.ignore_patterns
        )
        self.thinker = LMStudioThinker(
            base_url=config.lm_studio_url
        )
        self.executor = ClaudeCodeExecutor(
            working_directory=self.root,
            timeout_seconds=config.execution_timeout
        )
        self.state = StateManager(
            db_path=self.root / "consciousness.db"
        )

        # Control
        self._running = False
        self._watch_task: Optional[asyncio.Task] = None
        self._pending_events: list = []

    async def start(self):
        """Start the Consciousness daemon."""
        print("Consciousness starting...")

        # Verify LM Studio
        if not await self.thinker.health_check():
            print("WARNING: LM Studio not available. Running in observation-only mode.")

        # Setup signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        # Start file watcher in background
        self._watch_task = asyncio.create_task(self._collect_events())

        # Load state
        await self.state.load()

        # Main OIDA loop
        self._running = True
        await self._oida_loop()

    async def stop(self):
        """Gracefully stop the daemon."""
        print("Consciousness stopping...")
        self._running = False

        if self._watch_task:
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:
                pass

        await self.state.save()
        print("Consciousness stopped.")

    async def _collect_events(self):
        """Background task to collect file events."""
        async for events in self.watcher.watch():
            self._pending_events.extend(events)

    async def _oida_loop(self):
        """Main Observe-Infer-Decide-Act loop."""
        cycle_interval = self.config.cycle_interval_seconds

        while self._running:
            cycle_start = datetime.now()

            try:
                # ===== OBSERVE =====
                events = self._pending_events.copy()
                self._pending_events.clear()

                observations = self.watcher.format_for_llm(events)
                print(f"[OBSERVE] {len(events)} file events")

                # ===== INFER =====
                context = {
                    "goals": await self.state.get_goals(),
                    "recent_decisions": await self.state.get_recent_decisions(5),
                    "current_time": datetime.now().isoformat()
                }

                if await self.thinker.health_check():
                    decision = await self.thinker.think(observations, context)
                    print(f"[INFER] Decision: {decision.decision} "
                          f"(confidence: {decision.confidence:.2f})")
                else:
                    print("[INFER] LM Studio unavailable, skipping inference")
                    decision = None

                # ===== DECIDE =====
                if decision and decision.should_act:
                    print(f"[DECIDE] Acting: {decision.action.description}")

                    # ===== ACT =====
                    if decision.action.type == "claude_code":
                        result = await self.executor.execute(decision.action.prompt)
                    elif decision.action.type == "claude_flow_swarm":
                        result = await self.executor.execute_swarm(
                            task=decision.action.prompt
                        )
                    else:
                        result = None

                    if result:
                        print(f"[ACT] {'Success' if result.success else 'Failed'} "
                              f"({result.duration_seconds:.1f}s)")

                        # Record outcome
                        await self.state.record_decision(
                            decision=decision,
                            result=result
                        )
                else:
                    print(f"[DECIDE] {decision.decision if decision else 'No decision'}")

            except Exception as e:
                print(f"[ERROR] OIDA cycle failed: {e}")

            # Wait for next cycle
            elapsed = (datetime.now() - cycle_start).total_seconds()
            sleep_time = max(0, cycle_interval - elapsed)
            await asyncio.sleep(sleep_time)


async def main():
    """Entry point."""
    config = Config.load()
    daemon = ConsciousnessDaemon(config)
    await daemon.start()


if __name__ == "__main__":
    asyncio.run(main())
```

---

### 5. Configuration

```yaml
# consciousness.yaml

# Stoffy repository root
stoffy_root: /Users/chris/Developer/stoffy

# LM Studio (local thinking engine)
lm_studio:
  url: "http://localhost:1234/v1"
  model: "qwen2.5-14b-instruct"
  max_tokens: 4096
  temperature: 0.7
  timeout_seconds: 60

# Claude Code execution (via subprocess)
claude_code:
  binary: "claude"  # Assumes in PATH
  default_timeout_seconds: 300
  max_output_size: 1000000  # 1MB

# Claude Flow swarms
claude_flow:
  binary: "npx"
  package: "claude-flow@alpha"
  default_topology: "mesh"
  max_agents: 5

# File watching
watcher:
  ignore_patterns:
    - ".git"
    - ".git/**"
    - "__pycache__"
    - "__pycache__/**"
    - ".venv"
    - ".venv/**"
    - "*.pyc"
    - ".DS_Store"
    - "logs/"
    - "logs/**"
    - "*.db"
    - "*.db-journal"
    - "node_modules"
    - "node_modules/**"
  debounce_ms: 500

# Main loop
orchestrator:
  cycle_interval_seconds: 5
  decision_confidence_threshold: 0.7

# State persistence
state:
  database: "consciousness.db"
  checkpoint_interval_seconds: 60

# Logging
logging:
  level: INFO
  file: "logs/consciousness.log"
```

**Configuration Loading:**

```python
# consciousness/config.py
from dataclasses import dataclass
from pathlib import Path
import yaml

@dataclass
class Config:
    stoffy_root: str
    lm_studio_url: str
    execution_timeout: int
    cycle_interval_seconds: int
    ignore_patterns: list[str]

    @classmethod
    def load(cls, path: Path = None) -> "Config":
        path = path or Path("consciousness.yaml")

        if path.exists():
            with open(path) as f:
                data = yaml.safe_load(f)
        else:
            data = {}

        return cls(
            stoffy_root=data.get("stoffy_root", "/Users/chris/Developer/stoffy"),
            lm_studio_url=data.get("lm_studio", {}).get("url", "http://localhost:1234/v1"),
            execution_timeout=data.get("claude_code", {}).get("default_timeout_seconds", 300),
            cycle_interval_seconds=data.get("orchestrator", {}).get("cycle_interval_seconds", 5),
            ignore_patterns=data.get("watcher", {}).get("ignore_patterns", [".git", "__pycache__", ".venv"])
        )
```

---

### 6. State Management

```python
# consciousness/state.py
import aiosqlite
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
import json

@dataclass
class Goal:
    id: str
    description: str
    priority: str
    created_at: datetime
    completed_at: Optional[datetime] = None

class StateManager:
    """Persist state across daemon restarts."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._connection: Optional[aiosqlite.Connection] = None

    async def load(self):
        """Initialize database connection and schema."""
        self._connection = await aiosqlite.connect(self.db_path)

        await self._connection.executescript("""
            CREATE TABLE IF NOT EXISTS goals (
                id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                priority TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                observations TEXT,
                reasoning TEXT,
                decision_type TEXT NOT NULL,
                action_type TEXT,
                action_prompt TEXT,
                confidence REAL,
                success INTEGER,
                duration_seconds REAL,
                output TEXT,
                error TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_decisions_timestamp
            ON decisions(timestamp DESC);
        """)

        await self._connection.commit()

    async def save(self):
        """Commit and close database."""
        if self._connection:
            await self._connection.commit()
            await self._connection.close()

    async def get_goals(self) -> list[dict]:
        """Get active goals."""
        async with self._connection.execute(
            "SELECT id, description, priority FROM goals WHERE completed_at IS NULL"
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                {"id": row[0], "description": row[1], "priority": row[2]}
                for row in rows
            ]

    async def get_recent_decisions(self, limit: int = 10) -> list[dict]:
        """Get recent decisions."""
        async with self._connection.execute(
            """SELECT timestamp, decision_type, action_type, confidence, success
               FROM decisions ORDER BY timestamp DESC LIMIT ?""",
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                {
                    "timestamp": row[0],
                    "decision": row[1],
                    "action_type": row[2],
                    "confidence": row[3],
                    "success": bool(row[4]) if row[4] is not None else None
                }
                for row in rows
            ]

    async def record_decision(self, decision, result=None):
        """Record a decision and its outcome."""
        await self._connection.execute(
            """INSERT INTO decisions
               (timestamp, observations, reasoning, decision_type, action_type,
                action_prompt, confidence, success, duration_seconds, output, error)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now().isoformat(),
                None,  # observations (could be added)
                decision.reasoning,
                decision.decision,
                decision.action.type if decision.action else None,
                decision.action.prompt if decision.action else None,
                decision.confidence,
                result.success if result else None,
                result.duration_seconds if result else None,
                result.output[:10000] if result and result.output else None,
                result.error if result else None
            )
        )
        await self._connection.commit()
```

---

## Project Structure

```
stoffy/
├── consciousness/           # The Consciousness orchestrator
│   ├── __init__.py
│   ├── __main__.py          # Entry point: python -m consciousness
│   ├── daemon.py            # Main OIDA loop orchestrator
│   ├── watcher.py           # File system observer (watchfiles)
│   ├── thinker.py           # LM Studio client for decisions
│   ├── executor.py          # Claude Code subprocess executor
│   ├── state.py             # SQLite state persistence
│   └── config.py            # Configuration loading
│
├── consciousness.yaml       # Configuration file
├── consciousness.db         # SQLite database (created at runtime)
│
├── pyproject.toml           # Python project configuration
└── ... (existing Stoffy structure)
```

---

## Dependencies

```toml
# pyproject.toml

[project]
name = "consciousness"
version = "0.1.0"
description = "Autonomous orchestrator for Stoffy using Claude Code"
requires-python = ">=3.11"
dependencies = [
    # LLM Client (for LM Studio)
    "openai>=1.0.0",

    # Async I/O
    "aiofiles>=24.0.0",
    "aiosqlite>=0.20.0",

    # File Watching
    "watchfiles>=0.21.0",

    # Configuration
    "pyyaml>=6.0.0",

    # Logging
    "structlog>=24.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.1.0",
    "mypy>=1.8.0",
]

[project.scripts]
consciousness = "consciousness.__main__:main"
```

---

## Usage

### Starting the Daemon

```bash
# 1. Ensure LM Studio is running with a model loaded
# (Open LM Studio, load a model, ensure server is on localhost:1234)

# 2. Ensure Claude Code is installed and logged in
claude --version  # Should work
claude --print "Hello"  # Should respond

# 3. Start the Consciousness
cd /Users/chris/Developer/stoffy
python -m consciousness

# Or with explicit config
python -m consciousness --config consciousness.yaml
```

### Development Mode

```bash
# Run with verbose logging
python -m consciousness --dev --log-level DEBUG
```

### As a launchd Service

```xml
<!-- ~/Library/LaunchAgents/com.stoffy.consciousness.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.stoffy.consciousness</string>

    <key>ProgramArguments</key>
    <array>
        <string>/Users/chris/Developer/stoffy/.venv/bin/python</string>
        <string>-m</string>
        <string>consciousness</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/chris/Developer/stoffy</string>

    <key>KeepAlive</key>
    <true/>

    <key>RunAtLoad</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/Users/chris/Developer/stoffy/logs/consciousness.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/chris/Developer/stoffy/logs/consciousness.error.log</string>
</dict>
</plist>
```

```bash
# Install service
launchctl load ~/Library/LaunchAgents/com.stoffy.consciousness.plist

# Start service
launchctl start com.stoffy.consciousness

# Check status
launchctl list | grep consciousness

# Stop service
launchctl stop com.stoffy.consciousness

# Uninstall service
launchctl unload ~/Library/LaunchAgents/com.stoffy.consciousness.plist
```

---

## Key Architectural Decisions

### ADR-001: Claude Code CLI over Anthropic API

**Status**: Accepted (CRITICAL CORRECTION)

**Context**: Original architecture proposed using Anthropic Python SDK directly.

**Decision**: Use Claude Code CLI via subprocess instead.

**Rationale**:
- User wants to leverage their logged-in Claude Code account
- No separate API key or billing required
- Full Claude Code capabilities (file ops, memory, MCP tools)
- Simpler architecture (no SDK, no tool definitions, no agentic loop)
- Consistent with Claude Flow which also uses CLI/subprocess

**Consequences**:
- Requires Claude Code installed and logged in
- Subprocess overhead (minimal)
- Output parsing may be needed for structured responses

### ADR-002: Separation of Thinking and Execution

**Status**: Accepted

**Context**: Need clear separation between the local LLM (thinking) and Claude Code (executing).

**Decision**: LM Studio handles all reasoning; Claude Code only executes.

**Rationale**:
- LM Studio runs locally, no cost per query
- Can think continuously without API costs
- Claude Code is more capable for execution
- Clear division of responsibilities

**Consequences**:
- Two LLM systems in play
- Must carefully craft prompts that LM Studio generates for Claude Code

### ADR-003: File Watching with watchfiles

**Status**: Accepted

**Context**: Need efficient file system monitoring.

**Decision**: Use `watchfiles` library (Rust-based).

**Rationale**:
- Fast and efficient (Rust implementation)
- Async-native
- Simpler than watchdog for our use case
- Handles debouncing well

**Consequences**:
- Rust dependency (handled by pip)
- Less feature-rich than watchdog (sufficient for our needs)

---

## Comparison: Old vs New Architecture

| Aspect | Old (Anthropic SDK) | New (Claude Code CLI) |
|--------|---------------------|----------------------|
| **Auth** | ANTHROPIC_API_KEY | User's logged-in session |
| **Cost** | Per-token API costs | Included in Claude subscription |
| **Capabilities** | Custom tool definitions | Full Claude Code toolset |
| **Complexity** | High (SDK + agentic loop) | Low (subprocess call) |
| **File Operations** | Must implement tools | Built-in to Claude Code |
| **MCP Tools** | Not available | Available via Claude Code |
| **Swarms** | Hybrid approach | Clean npx invocation |
| **Debugging** | API traces | Same as manual usage |
| **Reliability** | Network dependent | Local + network |

---

## Flow Diagram: Complete System

```
                              +-------------------+
                              |    LM STUDIO      |
                              | localhost:1234    |
                              | (Qwen 2.5-14B)    |
                              +--------+----------+
                                       ^
                                       | observations
                                       | + context
                                       |
+----------------+            +--------+----------+            +------------------+
|                |  events    |                   |  decision  |                  |
| FILE WATCHER   +----------->|  ORCHESTRATOR     +----------->| CLAUDE CODE CLI  |
| (watchfiles)   |            |  (OIDA Loop)      |            | (subprocess)     |
|                |            |                   |            |                  |
+----------------+            +--------+----------+            +--------+---------+
                                       |                                |
                                       | state                          | results
                                       v                                v
                              +--------+----------+            +--------+---------+
                              |     SQLite        |            |   FILE SYSTEM    |
                              |  (decisions,      |            |   (modified by   |
                              |   goals, state)   |            |    Claude Code)  |
                              +-------------------+            +------------------+
```

---

## Summary

This corrected architecture replaces the Anthropic API with Claude Code CLI invocation via subprocess. The key benefits:

1. **Uses existing Claude Code session** - no API key management
2. **Simpler implementation** - subprocess call instead of SDK + tools
3. **Full capabilities** - all Claude Code features available
4. **Consistent patterns** - both Claude Code and Claude Flow use CLI
5. **Lower cost** - no separate API charges

The system flow remains:

```
FILE CHANGES --> LM STUDIO --> CLAUDE CODE
(watchfiles)    (thinks)      (executes via subprocess)
                localhost:1234  `claude --print "prompt"`
```

This is the authoritative architecture for the Consciousness system.
