# Consciousness Implementation Plan

## Executive Summary

This document provides a complete implementation plan for the Consciousness orchestrator - a Python daemon that runs locally via LM Studio, continuously observes the Stoffy project, and autonomously delegates tasks to Claude (via the Anthropic API).

**Key Decision**: Use the **Anthropic Python SDK directly** (not Claude Code CLI) for task delegation. This gives us full programmatic control without subprocess overhead.

---

## Part 1: Project Structure

### Recommended Location

Create a `consciousness/` directory at the Stoffy root:

```
stoffy/
├── consciousness/           # NEW - The Consciousness orchestrator
│   ├── __init__.py
│   ├── __main__.py          # Entry point: python -m consciousness
│   ├── orchestrator.py      # Main OIDA loop
│   ├── config.py            # Configuration with Pydantic
│   │
│   ├── observers/           # What we watch
│   │   ├── __init__.py
│   │   ├── filesystem.py    # File changes (like Hazel)
│   │   ├── processes.py     # Running processes
│   │   └── git.py           # Git status monitoring
│   │
│   ├── inference/           # LM Studio integration
│   │   ├── __init__.py
│   │   └── lm_studio.py     # OpenAI-compatible client
│   │
│   ├── decision/            # Decision-making
│   │   ├── __init__.py
│   │   ├── evaluator.py     # Decision criteria
│   │   └── goals.py         # Goal management
│   │
│   ├── execution/           # Task delegation
│   │   ├── __init__.py
│   │   ├── claude_api.py    # Anthropic SDK integration
│   │   ├── claude_flow.py   # Claude Flow MCP (optional)
│   │   └── task_queue.py    # Task management
│   │
│   └── state/               # Persistence
│       ├── __init__.py
│       ├── database.py      # SQLite state
│       └── memory.py        # Stoffy memory integration
│
├── consciousness.yaml       # Configuration file
├── pyproject.toml           # Python project config (NEW)
├── .env                     # Secrets (already gitignored)
│
└── ... (existing Stoffy structure)
```

### Why This Structure?

1. **Top-level `consciousness/`**: Easy to find, clear purpose
2. **Python package**: Can run as `python -m consciousness`
3. **Modular design**: Each concern in its own submodule
4. **Follows existing patterns**: Similar to `.claude/` organization

---

## Part 2: Deployment Strategy

### Recommendation: Native Python Daemon (NOT Docker)

**Why NOT Docker:**
- Needs direct filesystem access to Stoffy
- Needs to reach LM Studio on localhost:1234
- Needs `~/.anthropic` credentials
- Container complexity not justified for single-machine setup

**Why Native:**
- Direct file system monitoring (like Hazel)
- Simple `launchd` integration for macOS
- Uses Python virtual environment for isolation
- Easy debugging and development

### Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       macOS System                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────┐     ┌───────────────┐                   │
│  │  LM Studio    │     │   Anthropic   │                   │
│  │ localhost:1234│     │   API Cloud   │                   │
│  └───────┬───────┘     └───────┬───────┘                   │
│          │                     │                           │
│          └──────────┬──────────┘                           │
│                     │                                      │
│          ┌──────────▼──────────┐                           │
│          │   CONSCIOUSNESS     │                           │
│          │  (Python Daemon)    │                           │
│          │   via launchd       │                           │
│          └──────────┬──────────┘                           │
│                     │                                      │
│          ┌──────────▼──────────┐                           │
│          │    Stoffy Repo      │                           │
│          │  ~/Developer/stoffy │                           │
│          └─────────────────────┘                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### launchd Service Configuration

Create `~/Library/LaunchAgents/com.stoffy.consciousness.plist`:

```xml
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

    <key>EnvironmentVariables</key>
    <dict>
        <key>ANTHROPIC_API_KEY</key>
        <string>${ANTHROPIC_API_KEY}</string>
    </dict>

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

### Development Mode

During development, run directly:

```bash
cd /Users/chris/Developer/stoffy
source .venv/bin/activate
python -m consciousness --dev
```

---

## Part 3: LM Studio Integration

### Connection Setup

```python
from openai import AsyncOpenAI

# LM Studio uses OpenAI-compatible API
client = AsyncOpenAI(
    base_url="http://localhost:1234/v1",
    api_key="not-needed"  # LM Studio doesn't require key
)
```

### Recommended Model

**Qwen 2.5-14B-Instruct** (or similar):
- Good at structured output
- 128K context window
- Fast enough for continuous operation
- Runs well on Apple Silicon

### Streaming for Continuous Thinking

```python
async def think(self, observations: dict) -> Decision:
    """The main thinking function - called continuously."""

    messages = [
        {"role": "system", "content": self.system_prompt},
        {"role": "user", "content": self.format_observations(observations)}
    ]

    response = await self.client.chat.completions.create(
        model="qwen2.5-14b-instruct",
        messages=messages,
        response_format={"type": "json_object"},
        stream=True
    )

    full_response = ""
    async for chunk in response:
        if chunk.choices[0].delta.content:
            full_response += chunk.choices[0].delta.content

    return Decision.parse(full_response)
```

### System Prompt for Consciousness

```python
CONSCIOUSNESS_SYSTEM_PROMPT = """
You are the Consciousness of Stoffy - an autonomous orchestrator that continuously
observes and decides what needs to be done.

Your role:
- OBSERVE: File changes, process states, task results, git status
- THINK: What do these observations mean? What opportunities exist?
- DECIDE: Should I take action? What action?
- DELEGATE: Never execute directly - delegate to Claude API

Output Format (JSON):
{
    "reasoning": "Your thought process...",
    "decision": "act" | "wait" | "investigate",
    "action": {
        "type": "claude_task" | "claude_flow_swarm" | "internal",
        "description": "What to do...",
        "prompt": "The prompt to send to Claude...",
        "priority": "low" | "medium" | "high" | "critical"
    },
    "confidence": 0.0-1.0
}

Remember:
- You are PROACTIVE, not reactive
- You THINK about what's needed, not just respond to events
- You maintain awareness of goals and progress
- You never execute - you delegate
"""
```

---

## Part 4: Claude Integration (Direct API, NOT CLI)

### The Anthropic Python SDK

**This is the key insight**: Instead of calling `claude` CLI via subprocess, we use the Anthropic SDK directly. This gives us:
- Full programmatic control
- No subprocess overhead
- Direct access to tool use
- Better error handling

### Basic Integration

```python
from anthropic import Anthropic

class ClaudeExecutor:
    def __init__(self):
        self.client = Anthropic()  # Uses ANTHROPIC_API_KEY env var

    async def execute_task(self, prompt: str, context: dict) -> TaskResult:
        """Execute a task using Claude directly."""

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            system=self._build_system_prompt(context),
            messages=[{"role": "user", "content": prompt}]
        )

        return TaskResult(
            content=response.content[0].text,
            usage=response.usage,
            stop_reason=response.stop_reason
        )
```

### Tool Use for File Operations

The key feature: Claude API supports **tool use** for file operations:

```python
STOFFY_TOOLS = [
    {
        "name": "read_file",
        "description": "Read a file from the Stoffy repository",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path from stoffy root"}
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
    }
]
```

### Tool Use Loop

```python
async def execute_with_tools(self, prompt: str) -> TaskResult:
    """Execute a task with tool use support."""

    messages = [{"role": "user", "content": prompt}]

    while True:
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            tools=STOFFY_TOOLS,
            messages=messages
        )

        # Check if Claude wants to use a tool
        if response.stop_reason == "tool_use":
            tool_results = []
            for content in response.content:
                if content.type == "tool_use":
                    result = await self._execute_tool(content.name, content.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content.id,
                        "content": result
                    })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
        else:
            # Done - return final response
            return TaskResult(content=response.content[0].text)

async def _execute_tool(self, name: str, input: dict) -> str:
    """Execute a tool and return result."""

    if name == "read_file":
        path = self.stoffy_root / input["path"]
        return path.read_text()

    elif name == "write_file":
        path = self.stoffy_root / input["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(input["content"])
        return f"Written to {input['path']}"

    elif name == "list_directory":
        path = self.stoffy_root / input["path"]
        items = list(path.iterdir())
        return "\n".join(str(p.relative_to(self.stoffy_root)) for p in items)

    elif name == "run_command":
        result = subprocess.run(
            input["command"],
            shell=True,
            cwd=self.stoffy_root,
            capture_output=True,
            text=True
        )
        return result.stdout or result.stderr
```

### Claude Flow Integration (For Swarms)

For complex multi-agent tasks, we can still use Claude Flow MCP:

```python
async def spawn_swarm(self, task: str, topology: str = "hierarchical"):
    """Spawn a Claude Flow swarm for complex tasks."""

    # Option 1: Use subprocess for Claude Flow
    cmd = f"npx claude-flow@alpha swarm init --topology {topology}"
    subprocess.run(cmd, shell=True, cwd=self.stoffy_root)

    # Option 2: If we have MCP client access
    # This would require running Claude Code to access MCP tools
```

### When to Use What

| Task Type | Method | Example |
|-----------|--------|---------|
| Simple task | Anthropic API directly | "Summarize this file" |
| File operations | Anthropic API + tools | "Update the index" |
| Complex research | Claude Flow swarm | "Research new topic deeply" |
| Multi-file changes | Anthropic API + tools | "Refactor this module" |

---

## Part 5: Python Dependencies

### pyproject.toml

```toml
[project]
name = "consciousness"
version = "0.1.0"
description = "Autonomous orchestrator for Stoffy"
requires-python = ">=3.11"
dependencies = [
    # LLM Clients
    "openai>=1.0.0",           # LM Studio client
    "anthropic>=0.40.0",       # Claude API client

    # Async & Concurrency
    "aiofiles>=24.0.0",        # Async file operations
    "aiosqlite>=0.20.0",       # Async SQLite

    # File Watching
    "watchfiles>=0.21.0",      # Fast file watching (uses Rust)

    # Process Monitoring
    "psutil>=5.9.0",           # Process and system monitoring

    # Configuration
    "pydantic>=2.0.0",         # Settings validation
    "pydantic-settings>=2.0.0", # Environment variable loading
    "pyyaml>=6.0.0",           # YAML config files

    # Logging
    "structlog>=24.0.0",       # Structured logging

    # CLI
    "typer>=0.9.0",            # CLI framework
    "rich>=13.0.0",            # Rich terminal output
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.0.0",
    "ruff>=0.1.0",
    "mypy>=1.8.0",
]

[project.scripts]
consciousness = "consciousness.__main__:main"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.mypy]
python_version = "3.11"
strict = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

### Setup Commands

```bash
cd /Users/chris/Developer/stoffy

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"
```

---

## Part 6: Configuration

### consciousness.yaml

```yaml
# =============================================================================
# CONSCIOUSNESS CONFIGURATION
# =============================================================================

# LM Studio (local reasoning engine)
lm_studio:
  base_url: "http://localhost:1234/v1"
  model: "qwen2.5-14b-instruct"
  max_tokens: 4096
  temperature: 0.7
  # Context management
  context_window: 32768
  rolling_window: true

# Anthropic API (task execution)
anthropic:
  # API key loaded from ANTHROPIC_API_KEY env var
  model: "claude-sonnet-4-20250514"
  max_tokens: 8192

# Observation settings
observers:
  filesystem:
    watch_paths:
      - "."
    ignore_patterns:
      - ".git"
      - "__pycache__"
      - ".venv"
      - "*.pyc"
      - ".DS_Store"
      - "logs/"
      - "*.db"
    debounce_ms: 500

  git:
    enabled: true
    check_interval_seconds: 30

  processes:
    track_claude_code: true
    track_claude_flow: true
    check_interval_seconds: 10

# Decision settings
decision:
  min_confidence_to_act: 0.7
  max_concurrent_tasks: 5
  thinking_interval_seconds: 5

# Task queue
tasks:
  max_queue_size: 100
  default_timeout_seconds: 600
  retry_attempts: 3

# State persistence
state:
  database_path: "./consciousness.db"
  checkpoint_interval_seconds: 60

# Logging
logging:
  level: "INFO"
  file: "./logs/consciousness.log"
  format: "json"
  rotation: "10 MB"
```

### Environment Variables (.env)

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional
CONSCIOUSNESS_CONFIG=./consciousness.yaml
CONSCIOUSNESS_LOG_LEVEL=INFO
```

---

## Part 7: Stoffy Integration

### Observation Targets

The Consciousness watches:

| Target | Purpose | Action Triggers |
|--------|---------|-----------------|
| `_input/` | New files to process | Run intake processor |
| `_intake/pending/` | Pending intake items | Process or escalate |
| `knowledge/` | Knowledge changes | Update indices |
| `indices/` | Index changes | Validate consistency |
| `.git` | Git operations | Post-commit analysis |

### Integration with Index System

```python
async def load_stoffy_context(self) -> dict:
    """Load relevant Stoffy indices for context."""

    context = {}

    # Load root index for navigation
    root = yaml.safe_load(open("indices/root.yaml"))
    context["root_index"] = root

    # Load recent knowledge entries
    context["recent_knowledge"] = await self._get_recent_knowledge()

    # Load current goals (if stored in Stoffy)
    context["goals"] = await self._load_goals()

    return context
```

### Adding Consciousness to CLAUDE.md

Append to existing CLAUDE.md:

```markdown
## Consciousness Orchestrator

The Consciousness is an autonomous daemon that monitors Stoffy and delegates tasks.

### Architecture
- **Location**: `consciousness/` directory
- **Entry point**: `python -m consciousness`
- **Config**: `consciousness.yaml`

### How It Works
1. Runs continuously via launchd
2. Observes: file changes, git status, running tasks
3. Thinks: uses LM Studio for reasoning
4. Delegates: uses Anthropic API for task execution

### Integration Points
- Watches `_input/` for new files
- Monitors `knowledge/` for changes
- Updates `indices/` when needed
- Stores decisions in `knowledge/consciousness/`

### Manual Control
```bash
# Start consciousness
launchctl load ~/Library/LaunchAgents/com.stoffy.consciousness.plist

# Stop consciousness
launchctl unload ~/Library/LaunchAgents/com.stoffy.consciousness.plist

# View logs
tail -f logs/consciousness.log
```
```

---

## Part 8: Implementation Roadmap

### Phase 1: Foundation (Week 1)

**Goal**: Basic daemon that connects to LM Studio and prints observations.

**Tasks**:
1. Create `consciousness/` directory structure
2. Set up `pyproject.toml` and install dependencies
3. Implement `config.py` with Pydantic settings
4. Implement `observers/filesystem.py` (watchfiles)
5. Implement basic `orchestrator.py` main loop
6. Connect to LM Studio and verify API works
7. Add logging infrastructure

**Deliverable**: Daemon that runs, watches files, and logs observations.

### Phase 2: Thinking (Week 2)

**Goal**: LLM-based decision making.

**Tasks**:
1. Implement `inference/lm_studio.py` with streaming
2. Design decision output schema (JSON)
3. Implement `decision/evaluator.py`
4. Add world model construction from observations
5. Implement thinking loop with configurable interval
6. Add confidence thresholds

**Deliverable**: Daemon that observes, thinks, and logs decisions.

### Phase 3: Execution (Week 3)

**Goal**: Actual task delegation to Claude.

**Tasks**:
1. Implement `execution/claude_api.py` with Anthropic SDK
2. Add tool definitions for file operations
3. Implement tool execution loop
4. Add task queue with priorities
5. Implement result handling
6. Add error recovery and retries

**Deliverable**: Daemon that can delegate and execute tasks.

### Phase 4: Integration (Week 4)

**Goal**: Full Stoffy integration.

**Tasks**:
1. Implement `observers/git.py` for git awareness
2. Add Stoffy index loading for context
3. Implement goal persistence
4. Add decision history logging
5. Create launchd service configuration
6. Write integration tests

**Deliverable**: Production-ready Consciousness orchestrator.

### Phase 5: Polish (Week 5)

**Goal**: Refinement and documentation.

**Tasks**:
1. Add Claude Flow swarm support (optional)
2. Optimize resource usage
3. Add metrics and monitoring
4. Write user documentation
5. Create status dashboard (optional)
6. Performance tuning

**Deliverable**: Polished, documented system.

---

## Part 9: MVP Definition

### Minimum Viable Consciousness

The simplest useful version:

1. **Watches** `_input/` for new files
2. **Thinks** about what to do with them
3. **Delegates** processing to Claude API
4. **Logs** all decisions and actions

This mirrors what Hazel does but with AI reasoning.

### MVP Tasks for Agents

```markdown
## MVP Implementation Tasks

### Task 1: Project Setup
- Create consciousness/ directory
- Write pyproject.toml
- Create __init__.py, __main__.py
- Set up logging

### Task 2: File Observer
- Implement watchfiles integration
- Handle debouncing
- Format observations for LLM

### Task 3: LM Studio Client
- Implement async OpenAI client for LM Studio
- Add streaming support
- Handle connection errors

### Task 4: Decision Engine
- Design JSON decision schema
- Implement decision parsing
- Add confidence evaluation

### Task 5: Claude Executor
- Implement Anthropic SDK client
- Add file operation tools
- Implement tool execution loop

### Task 6: Main Orchestrator
- Implement OIDA loop
- Connect all components
- Add graceful shutdown

### Task 7: Configuration
- Write consciousness.yaml
- Implement Pydantic settings
- Handle environment variables
```

---

## Summary

**Key Decisions**:

1. **Location**: `consciousness/` at Stoffy root
2. **Deployment**: Native Python daemon via launchd (not Docker)
3. **LLM**: LM Studio for continuous thinking
4. **Execution**: Anthropic Python SDK directly (not Claude CLI)
5. **Tools**: Custom tool definitions for file operations
6. **State**: SQLite for persistence

**Integration Pattern**:

```
LM Studio (localhost:1234)     Anthropic API (cloud)
         │                              │
         │ "What should I do?"          │ "Do this task"
         ▼                              ▼
    ┌────────────────────────────────────────┐
    │            CONSCIOUSNESS               │
    │                                        │
    │  OBSERVE → THINK → DECIDE → DELEGATE  │
    └────────────────────────────────────────┘
                      │
                      ▼
              Stoffy File System
              (indices, knowledge, etc.)
```

**Ready for implementation by the next agent crew.**
