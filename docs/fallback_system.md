# Fallback System: LM Studio -> Claude Code + Gemini

## Overview

The Stoffy consciousness system provides seamless degradation when LM Studio (the primary local LLM) is unavailable. When the local LLM is down, the system automatically switches to using Claude Code as the executor with optional Gemini consciousness guidance.

This fallback mechanism ensures continuous operation of the consciousness daemon regardless of whether the local LM Studio instance is running.

## Architecture

```
+------------------------------------------------------------------+
|                     MODE SELECTION FLOW                           |
+------------------------------------------------------------------+
|                                                                   |
|   Start                                                           |
|     |                                                             |
|     v                                                             |
|  +------------------+                                             |
|  |  Check LM Studio |                                             |
|  |  Availability    |                                             |
|  +--------+---------+                                             |
|           |                                                       |
|    +------+------+                                                |
|    |             |                                                |
|    v             v                                                |
| Available    Unavailable                                          |
|    |             |                                                |
|    v             v                                                |
| +------+    +----------------+                                    |
| |PRIMARY|   | Check Gemini   |                                    |
| | MODE  |   | Available?     |                                    |
| +------+    +-------+--------+                                    |
|                     |                                             |
|              +------+------+                                      |
|              |             |                                      |
|              v             v                                      |
|           Available    Unavailable                                |
|              |             |                                      |
|              v             v                                      |
|         +--------+    +--------+                                  |
|         |FALLBACK|    |DEGRADED|                                  |
|         | MODE   |    | MODE   |                                  |
|         +--------+    +--------+                                  |
|                                                                   |
+------------------------------------------------------------------+

+------------------------------------------------------------------+
|                    COMPONENT INTERACTION                          |
+------------------------------------------------------------------+

  PRIMARY MODE (LM Studio Available)
  ==================================

  File Changes --> Watcher --> LM Studio --> Decision --> Executor
                               (Thinker)                    |
                                                            v
                                            +---------------+---------+
                                            |Claude Code|Claude Flow|Bash|
                                            +---------------+---------+

  FALLBACK MODE (Claude Code + Gemini)
  ====================================

  File Changes --> Watcher --> Intent --> Gemini --> Claude Code
                               Classifier  (Guidance)   (Executor)
                                  |
                                  v
                         +----------------+
                         | Simple Query? |
                         +-------+--------+
                                 |
                          +------+------+
                          |             |
                          v             v
                       Gemini      Claude Code
                       (Answer)     (Execute)

  DEGRADED MODE (Claude Code Only)
  ================================

  File Changes --> Watcher --> Claude Code (Direct Execution)
                                    |
                                    v
                         +---------------------+
                         | Full CLI with       |
                         | --permission-mode   |
                         | acceptEdits         |
                         +---------------------+
```

## Modes

### PRIMARY Mode (LM Studio)

The default operating mode when LM Studio is available.

**Characteristics:**
- LM Studio serves as the "thinker" for the consciousness
- Local reasoning with models like Qwen 2.5
- Lower latency for decision-making
- No API costs for thinking phase
- Full autonomous OIDA loop operation

**Data Flow:**
1. File watcher detects changes
2. LM Studio interprets observations and generates structured decisions
3. Decision engine evaluates confidence and action type
4. Executor (Claude Code, Claude Flow, Bash, etc.) performs actions
5. Outcomes recorded for pattern learning

**Configuration:**
```yaml
lm_studio:
  base_url: "http://localhost:1234/v1"
  model: "qwen2.5-14b-instruct"
  temperature: 0.7
  max_tokens: 4096
  timeout_seconds: 60
```

### FALLBACK Mode (Claude Code + Gemini)

Activated when LM Studio is unavailable but Gemini API is configured.

**Characteristics:**
- Claude Code becomes the primary executor AND decision-maker
- Gemini provides consciousness-like guidance for complex decisions
- Gemini handles large context analysis (2M+ tokens)
- Claude Code executes all actions with `--permission-mode acceptEdits`
- Higher API costs but full functionality preserved

**Data Flow:**
1. File watcher detects changes
2. Intent classification determines query type (question vs action)
3. For questions: Gemini provides analysis/answers
4. For actions: Claude Code executes directly
5. Gemini may provide pre-execution guidance for complex tasks

**When Gemini is Preferred:**
- Large context analysis (logs, documentation sets)
- Pattern finding across thousands of lines
- Information retrieval and summarization
- When massive context window (2M tokens) is needed

**Trust Levels:**
- Claude Code: HIGH trust - execute code and actions
- Gemini: MEDIUM trust - analysis and guidance (verify code output)

### DEGRADED Mode (Claude Code Only)

Activated when both LM Studio and Gemini are unavailable.

**Characteristics:**
- Claude Code handles all operations directly
- No separate consciousness/thinking layer
- User messages still receive responses
- Basic file watching and response capability
- Most autonomous features remain functional

**Limitations:**
- No large context analysis capability
- Reduced reasoning depth for complex decisions
- Higher latency for simple queries
- Full API cost for all operations

## Usage

### Chat Command

The `chat` command automatically handles fallback:

```bash
# Auto-select best available tool
python -m consciousness chat

# Force Claude Code (default)
python -m consciousness chat --tool claude_code

# Force Gemini for analysis
python -m consciousness chat --tool gemini

# Quiet mode with fallback
python -m consciousness chat --quiet
```

### Daemon Operation

The daemon continuously monitors LM Studio availability:

```bash
# Run with automatic fallback enabled (default)
python -m consciousness run

# Run with development logging (shows mode changes)
python -m consciousness run --dev

# Dry run to test fallback detection
python -m consciousness run --dry-run
```

### Check System Status

```bash
# View all component availability
python -m consciousness check

# Output shows:
# - LM Studio: Connected/Not connected
# - Claude CLI: Available/Not found
# - Claude Flow: Available/Not available
# - Database: Exists/Will be created
```

### Programmatic Usage

```python
from consciousness import ConsciousnessConfig, load_config
from consciousness.executor import ExpandedExecutor, Action, ActionType
from consciousness.thinker import ConsciousnessThinker

# Check LM Studio availability
config = load_config()
thinker = ConsciousnessThinker(base_url=config.lm_studio.base_url)
is_available = await thinker.check_connection()

# Create executor with fallback capability
executor = ExpandedExecutor(working_dir=Path.cwd())
capabilities = executor.get_capabilities()

# capabilities returns:
# {
#     'claude_code': True,      # Usually always available
#     'claude_flow': True,      # Optional swarm capability
#     'gemini': True/False,     # Depends on GOOGLE_API_KEY
#     'python': True,
#     'node': True,
#     'typescript': True,
#     'bash': True,
#     'file_operations': True,
#     'shell_commands': True,
#     'file_deletion': False,   # Safety default
# }

# Execute with appropriate fallback
if capabilities['gemini']:
    # Use Gemini for large context analysis
    action = Action.gemini_analyze(
        prompt="Analyze these logs",
        files=["/path/to/logs/*.log"],
        model="gemini-1.5-pro"
    )
else:
    # Fall back to Claude Code
    action = Action.claude_code(prompt="Analyze these logs")

result = await executor.execute(action)
```

## Configuration

### consciousness.yaml

```yaml
# Primary LM Studio configuration
lm_studio:
  base_url: "http://localhost:1234/v1"
  model: "qwen2.5-14b-instruct"
  temperature: 0.7
  max_tokens: 4096
  timeout_seconds: 60

# Fallback system configuration
fallback:
  # Master switch for fallback behavior
  enabled: true

  # Prefer LM Studio when it becomes available again
  prefer_lm_studio: true

  # How often to check if primary is back online
  check_interval_seconds: 30.0

  # Quick timeout for availability checks (don't block)
  lm_studio_timeout: 5.0

  # Retries before switching to fallback
  lm_studio_retry_count: 2

  # Gemini consciousness settings
  gemini_model: "gemini-1.5-flash"  # Use flash for speed
  gemini_timeout: 30.0
  gemini_enabled: true  # Set false to skip to DEGRADED mode

  # Claude Code settings for fallback execution
  claude_timeout: 120.0
  auto_execute_threshold: 0.8  # Confidence for auto-execution

  # UI/UX settings
  show_mode_changes: true  # Notify when mode switches
  log_consciousness_thoughts: false
  sign_off: "- Stoffy"  # Signature for responses

# Executor configuration
executor:
  timeout_seconds: 300
  working_dir: "."
  allowed_commands:
    - "git"
    - "python"
    - "pip"
    - "npm"
    - "node"
  blocked_patterns:
    - "rm -rf /"
    - "sudo"
    - "> /dev"

# Display configuration
display:
  show_thinking: true
  show_observations: true
  show_decisions: true
  show_actions: true
  thinking_style: "full"  # full, summary, minimal
```

### Environment Variables

```bash
# Required for Gemini fallback
export GOOGLE_API_KEY="your-google-api-key"

# Optional: Override config settings
export CONSCIOUSNESS_FALLBACK__ENABLED="true"
export CONSCIOUSNESS_FALLBACK__GEMINI_MODEL="gemini-1.5-pro"
export CONSCIOUSNESS_LM_STUDIO__BASE_URL="http://localhost:1234/v1"
```

## How It Works

### 1. Availability Detection

The system performs availability checks at multiple points:

**Startup Check:**
```python
# In ConsciousnessDaemon.run()
connected = await self.thinker.check_connection()
if not connected:
    logger.warning("daemon.lm_studio_not_connected")
    # System continues with fallback mode
```

**Connection Test:**
```python
class ConsciousnessThinker:
    async def check_connection(self) -> bool:
        """Check if LM Studio is reachable."""
        try:
            await self.client.models.list()
            return True
        except Exception as e:
            logger.warning(f"LM Studio connection check failed: {e}")
            return False
```

**Periodic Recheck:**
- The fallback system rechecks primary availability periodically
- Interval configured via `fallback.check_interval_seconds`
- Automatic switchback when LM Studio becomes available

### 2. Intent Classification

The responder classifies user intents to route appropriately:

```python
# In ConsciousnessResponder._build_response_prompt()
action_keywords = [
    'remove', 'delete', 'create', 'make', 'run', 'execute',
    'fix', 'install', 'update', 'move', 'rename', 'copy',
    'build', 'test', 'deploy', 'start', 'stop'
]

message_lower = message.message.lower()
is_action_request = any(kw in message_lower for kw in action_keywords)

# Action requests -> Claude Code execution
# Questions/analysis -> May use Gemini
```

### 3. Gemini Consciousness

When used for consciousness guidance, Gemini provides:

**Analysis Capabilities:**
- Large context processing (2M+ tokens)
- Pattern recognition across files
- Documentation summarization
- Log analysis

**Trust Level: VERIFY**
```python
# Gemini results include verification metadata
result.metadata["tier"] = 4
result.metadata["trust_level"] = "verify"
result.metadata["warning"] = "Gemini output - verify code with Claude before using"
```

**Execution Flow:**
```python
async def _execute_gemini(self, action: Action) -> ExecutionResult:
    # Try SDK first
    result = await self._execute_gemini_sdk(full_prompt, model, timeout)

    # Fall back to CLI
    if result is None:
        result = await self._execute_gemini_cli(full_prompt, model, timeout)

    # Final fallback to curl API
    if result is None:
        result = await self._execute_gemini_curl(full_prompt, model, timeout)
```

### 4. Autonomous Execution

Claude Code execution with full permissions:

```python
# Claude Code is invoked with permission to edit files
cmd = [
    self.claude_path,
    "--print",
    "--permission-mode", "acceptEdits",  # Key for autonomous operation
    prompt
]
```

**Execution Rules Embedded in Prompts:**
```
CRITICAL EXECUTION DIRECTIVE: You have FULL EXECUTION CAPABILITIES.
When the user asks you to DO something:
1. NEVER just describe what command would work - EXECUTE IT
2. NEVER ask for permission - you already have it
3. NEVER say "you can run..." - RUN IT YOURSELF
4. After executing, report WHAT YOU ACTUALLY DID
```

## Examples

### Example 1: Simple Question (Fallback Mode)

**User Input:**
```
Hey Stoffy, how does the watcher work?
```

**System Behavior:**
1. Daemon detects user message in file
2. Checks LM Studio - unavailable
3. Routes to Claude Code with Gemini analysis option
4. Claude Code generates response with file context
5. Response inserted into file

**Response:**
```markdown
<!-- STOFFY -->
The watcher works by monitoring the file system for changes using the
`watchfiles` library. When changes are detected, they are debounced
(default 500ms) and batched before being processed by the OIDA loop.

Key components:
- `ConsciousnessWatcher`: Main file watcher class
- `GitWatcher`: Monitors git status and commits
- Ignore patterns prevent watching temp files, caches, etc.

- Stoffy
<!-- /STOFFY -->
```

### Example 2: Task Execution (Fallback Mode)

**User Input:**
```
Hey consciousness, delete the old test_run_2026_01_04 folder
```

**System Behavior:**
1. Intent classification: ACTION REQUEST
2. Fallback mode active (no LM Studio)
3. Claude Code executes with `--permission-mode acceptEdits`
4. Actually runs: `rm -rf test_run_2026_01_04`
5. Confirms deletion in response

**Response:**
```markdown
<!-- STOFFY -->
Done! I've deleted the `test_run_2026_01_04` folder.

Actions taken:
- Verified folder existed at `/Users/chris/Developer/stoffy/test_run_2026_01_04`
- Executed: `rm -rf test_run_2026_01_04`
- Confirmed removal: folder no longer exists

- Stoffy
<!-- /STOFFY -->
```

### Example 3: Mode Switching

**Scenario:** LM Studio goes down during operation

**Log Output:**
```
2024-01-06T12:00:00 [WARNING] daemon.lm_studio_not_connected url=http://localhost:1234/v1
2024-01-06T12:00:00 [INFO] daemon.mode_switch from=PRIMARY to=FALLBACK
2024-01-06T12:00:00 [INFO] daemon.fallback_enabled gemini=true claude_code=true
```

**Later: LM Studio comes back online**
```
2024-01-06T12:30:00 [INFO] daemon.primary_available url=http://localhost:1234/v1
2024-01-06T12:30:00 [INFO] daemon.mode_switch from=FALLBACK to=PRIMARY
```

## Troubleshooting

### LM Studio Not Connecting

```bash
# Check if LM Studio is running
curl http://localhost:1234/v1/models

# Expected output:
# {"data":[{"id":"qwen2.5-14b-instruct",...}]}

# Common issues:
# 1. LM Studio not started
# 2. No model loaded in LM Studio
# 3. Different port configured
# 4. Firewall blocking localhost
```

### Gemini Not Available

```bash
# Check API key
echo $GOOGLE_API_KEY

# Test Gemini directly
curl -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=$GOOGLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Hello"}]}]}'

# Install Python SDK if needed
pip install google-generativeai
```

### Claude Code Not Found

```bash
# Verify Claude CLI is installed
which claude
claude --version

# If not found, install:
npm install -g @anthropic-ai/claude-code

# Or via pipx:
pipx install claude-code
```

### Mode Stuck in Degraded

1. Check all API keys are set
2. Verify network connectivity
3. Test each component individually:
   ```bash
   python -m consciousness check
   ```
4. Review logs for specific errors:
   ```bash
   tail -f logs/consciousness.log | grep -E "(error|failed|unavailable)"
   ```

### Responses Not Appearing

1. Check file permissions in target directory
2. Verify user message format (must start with "Hey Stoffy" or similar)
3. Check logs for responder errors:
   ```bash
   grep "responder" logs/consciousness.log | tail -20
   ```
4. Ensure file extension is supported: `.md`, `.txt`, `.py`, `.js`, `.ts`

## Tiered Intelligence Reference

| Tier | Name | Use Case | Trust | Context |
|------|------|----------|-------|---------|
| 1 | Local (LM Studio) | Routine decisions, file ops | HIGH | Local |
| 2 | Claude Code | Code execution, complex tasks | HIGH | Project |
| 3 | Claude Flow | Multi-agent swarms | HIGH | Distributed |
| 4 | Gemini | Large context analysis | VERIFY | 2M tokens |

## See Also

- [Consciousness README](/Users/chris/Developer/stoffy/consciousness/README.md)
- [Configuration Reference](/Users/chris/Developer/stoffy/consciousness.yaml)
- [LM Studio Integration](/Users/chris/Developer/stoffy/docs/consciousness-research/implementation/03-lm-studio-integration.md)
- [Architecture Overview](/Users/chris/Developer/stoffy/docs/consciousness-research/orchestrator/00-architecture-overview.md)
