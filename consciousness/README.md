# Consciousness Daemon

An autonomous consciousness orchestrator that continuously observes, reasons, decides, and acts on file system changes within the Stoffy repository.

## Architecture Overview

The Consciousness Daemon implements the **OIDA Loop** (Observe-Infer-Decide-Act):

```
+------------------+     +------------------+     +------------------+     +------------------+
|     OBSERVE      | --> |      INFER       | --> |      DECIDE      | --> |       ACT        |
|  FileSystemObs.  |     |  LMStudioReason. |     | DecisionEvaluator|     |  ClaudeExecutor  |
+------------------+     +------------------+     +------------------+     +------------------+
         |                        |                        |                        |
         v                        v                        v                        v
  File changes,          Interpret meaning,      Confidence gate (0.7),    Delegate to Claude
  Git events,            Identify patterns,      Goal coherence check,     API for execution
  Process states         Generate decision       Resource availability
```

### Core Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `FileSystemObserver` | `observers/filesystem.py` | Watch for file changes with debouncing |
| `LMStudioReasoner` | `inference/lm_studio.py` | Local LLM reasoning via LM Studio |
| `DecisionEvaluator` | `decision/evaluator.py` | Gate decisions by confidence threshold |
| `ClaudeExecutor` | `execution/claude_api.py` | Execute approved actions via Claude API |
| `GlobalWorkspace` | `orchestrator.py` | Capacity-7 attention workspace (GWT) |
| `ConsciousnessOrchestrator` | `orchestrator.py` | Main OIDA loop coordinator |

### Key Principles

1. **Metacognitive Gate**: Actions only execute when confidence >= 0.7
2. **Global Workspace**: Limited attention capacity (7 items, Miller's number)
3. **Strange Loop**: Self-observation feeds back into processing
4. **Expected Free Energy**: Balances goal achievement with information gain
5. **Delegation Only**: Never executes directly, always delegates to Claude API

## Installation

### Prerequisites

1. **LM Studio**: Running at `http://localhost:1234` with a model loaded
2. **Claude Code CLI**: Available in PATH
3. **Python 3.11+**: With required packages
4. **Anthropic API Key**: Set as `ANTHROPIC_API_KEY` environment variable

### Install Dependencies

```bash
# Navigate to the consciousness implementation
cd /Users/chris/Developer/stoffy/docs/consciousness-research/implementation

# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .
# Or install manually:
pip install watchfiles openai anthropic pydantic pydantic-settings structlog typer rich pyyaml
```

## Running the Daemon

### Validation First

Always validate the setup before running:

```bash
# Run validation checks
python consciousness/validate.py

# Or as a module
python -m consciousness.validate
```

This checks:
- LM Studio connection
- Claude Code availability
- File permissions
- Python dependencies
- Configuration files

### Start the Daemon

```bash
# Basic run (from implementation directory)
python -m consciousness run

# With options
python -m consciousness run --interval 5.0 --dry-run

# Development mode (verbose logging)
python -m consciousness run --dev

# Using custom config
python -m consciousness run --config ./my-consciousness.yaml
```

### Command Options

| Option | Default | Description |
|--------|---------|-------------|
| `--config, -c` | Auto-detect | Path to consciousness.yaml |
| `--dev` | False | Enable verbose debug logging |
| `--dry-run` | False | Log decisions without executing |
| `--interval, -i` | 5.0 | Seconds between thinking cycles |

### Other Commands

```bash
# Check status (if running as daemon)
python -m consciousness status

# Run single observation cycle (debugging)
python -m consciousness observe
```

## Configuration

Create `consciousness.yaml` for custom settings:

```yaml
# LM Studio connection
lm_studio:
  base_url: "http://localhost:1234/v1"
  model: "qwen2.5-14b-instruct"
  temperature: 0.7
  max_tokens: 4096

# File system observation
observers:
  filesystem:
    watch_paths:
      - "."
    ignore_patterns:
      - ".git"
      - "__pycache__"
      - "node_modules"
      - "*.pyc"
      - "*.db"
    debounce_ms: 500

# Decision engine
decision:
  min_confidence_to_act: 0.7
  max_concurrent_tasks: 5
  thinking_interval_seconds: 5.0
  dry_run: false

# Global Workspace (GWT)
global_workspace:
  capacity: 7  # Miller's number
  salience_decay_rate: 0.95
```

## Testing

### Run All Tests

```bash
# From the tests directory
cd /Users/chris/Developer/stoffy/consciousness/tests

# Run with pytest
pytest -v

# Run specific test file
pytest test_watcher.py -v

# Run with coverage
pytest --cov=consciousness --cov-report=html
```

### Test Categories

| Test File | Coverage |
|-----------|----------|
| `test_watcher.py` | FileSystemObserver ignore patterns, debouncing, priority |
| `test_thinker.py` | LMStudioReasoner decision parsing, formatting, errors |
| `test_executor.py` | ClaudeExecutor tool execution, timeouts, errors |
| `test_integration.py` | End-to-end OIDA loop, component interaction |

### Running Integration Tests

Some tests require actual file system operations:

```bash
# Run with slow marker for integration tests
pytest -v -m slow

# Skip slow tests for quick feedback
pytest -v -m "not slow"
```

## Validation Script

The validation script (`validate.py`) checks all requirements:

```bash
python consciousness/validate.py
```

### Checks Performed

1. **LM Studio Connection**
   - Verifies `http://localhost:1234` is accessible
   - Reports loaded model name

2. **Claude Code CLI**
   - Checks `claude --version` works
   - Reports version number

3. **Anthropic API Key**
   - Verifies `ANTHROPIC_API_KEY` is set
   - Shows masked key for confirmation

4. **File Permissions**
   - Read/write access to Stoffy directory
   - Temp file write test

5. **Python Dependencies**
   - All required packages installed
   - Reports missing packages

6. **Configuration**
   - Looks for consciousness.yaml
   - Shows path if found

7. **Stoffy Structure**
   - Validates expected directories exist
   - knowledge/, indices/, .claude/

8. **File System Observer**
   - Async startup test
   - Event detection test

## Troubleshooting

### LM Studio Not Connecting

```bash
# Check if LM Studio is running
curl http://localhost:1234/v1/models

# Common issues:
# - LM Studio not started
# - No model loaded
# - Different port configured
```

### Claude Code Not Found

```bash
# Check PATH
which claude

# Install if needed
npm install -g @anthropic-ai/claude-code

# Verify
claude --version
```

### Missing Dependencies

```bash
# Install all at once
pip install watchfiles openai anthropic pydantic pydantic-settings structlog typer rich pyyaml httpx

# Or use requirements.txt if available
pip install -r requirements.txt
```

### Permission Denied

```bash
# Check directory permissions
ls -la /Users/chris/Developer/stoffy

# Ensure write access
touch /Users/chris/Developer/stoffy/.test && rm /Users/chris/Developer/stoffy/.test
```

## Development

### Adding New Observers

1. Implement `ObserverProtocol` from `consciousness/observers/__init__.py`
2. Add to orchestrator initialization
3. Create corresponding tests

### Adding New Decision Types

1. Extend `DecisionType` enum in `inference/lm_studio.py`
2. Update decision evaluator logic
3. Add handling in orchestrator

### Modifying the OIDA Loop

The main loop is in `orchestrator.py`:

```python
async def _oida_cycle(self) -> None:
    # OBSERVE
    observations = await self._observe()

    # Submit to global workspace
    for obs in observations:
        self.workspace.submit(obs)

    focused = self.workspace.get_focused()

    # INFER
    decision = await self._infer(focused, context)

    # DECIDE
    evaluation = self.evaluator.evaluate(decision, ...)

    # ACT
    if evaluation.should_execute and decision.action:
        await self._act(decision)
```

## License

Part of the Stoffy philosophical knowledge management system.

## See Also

- [Implementation Plan](../docs/consciousness-research/implementation/00-implementation-plan.md)
- [Architecture Overview](../docs/consciousness-research/orchestrator/00-architecture-overview.md)
- [LM Studio Integration](../docs/consciousness-research/implementation/03-lm-studio-integration.md)
