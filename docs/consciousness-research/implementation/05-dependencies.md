# Python Dependencies Research - Consciousness Orchestrator

## Executive Summary

This document provides comprehensive research on Python dependencies required for building the Consciousness orchestrator daemon. The orchestrator is a continuously-running Python daemon that integrates LLM interactions, file system monitoring, process tracking, state persistence, and async operations.

**Key Findings**:
- Python 3.11+ recommended (async improvements, better performance)
- `watchfiles` superior to `watchdog` for macOS FSEvents
- `httpx` preferred over `aiohttp` for async HTTP
- `aiosqlite` for async SQLite operations
- `structlog` for structured logging
- `pydantic` v2 for configuration validation

---

## 1. Core LLM Dependencies

### 1.1 OpenAI Client (LM Studio)

**Package**: `openai >= 1.0.0`

**Purpose**: Communicate with LM Studio's OpenAI-compatible API

**Features**:
- Native async support (`AsyncOpenAI`)
- Streaming responses
- Function calling support
- Retry logic with exponential backoff
- Type hints throughout

**Usage Pattern**:
```python
from openai import AsyncOpenAI

client = AsyncOpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio"  # LM Studio doesn't validate this
)

async def query_llm(prompt: str) -> str:
    response = await client.chat.completions.create(
        model="local-model",
        messages=[{"role": "user", "content": prompt}],
        stream=False
    )
    return response.choices[0].message.content
```

**Version Considerations**:
- v1.0.0+ uses new API structure (breaking changes from 0.x)
- v1.12.0+ has improved streaming
- Latest stable: 1.55.0+ (as of 2025)

**Alternatives Considered**:
- `llama-cpp-python`: Direct model loading (too heavy, we use LM Studio)
- `litellm`: Multi-provider abstraction (unnecessary overhead)

**Recommendation**: `openai>=1.12.0,<2.0.0`

---

### 1.2 Anthropic Client (Optional)

**Package**: `anthropic >= 0.18.0`

**Purpose**: Direct Claude API access for comparison/fallback

**Features**:
- Async support
- Tool/function calling
- System prompts
- Message streaming

**Usage Pattern**:
```python
from anthropic import AsyncAnthropic

client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

async def query_claude(prompt: str) -> str:
    response = await client.messages.create(
        model="claude-opus-4-5-20251101",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text
```

**Recommendation**: `anthropic>=0.18.0,<1.0.0` (optional dependency)

---

## 2. Async Framework

### 2.1 Built-in AsyncIO

**Module**: `asyncio` (Python standard library)

**Python Version Requirements**:
- **3.11+**: Task groups (`asyncio.TaskGroup`), improved exception handling
- **3.12+**: Per-task contextvars, better performance
- **3.13+**: Free-threaded mode (experimental)

**Key Features for Consciousness Orchestrator**:
```python
import asyncio
from asyncio import TaskGroup

# Python 3.11+ Task Groups (structured concurrency)
async def orchestrate():
    async with TaskGroup() as tg:
        tg.create_task(monitor_filesystem())
        tg.create_task(monitor_processes())
        tg.create_task(process_llm_queue())
        # All tasks cancelled if one fails
```

**Event Loop Considerations**:
- Use `asyncio.run()` for main entry point
- Consider `uvloop` for 2-4x performance boost
- macOS uses `kqueue` by default (good performance)

**Recommendation**: Python 3.11+ (built-in, no package needed)

---

### 2.2 UVLoop (Optional Performance Boost)

**Package**: `uvloop >= 0.19.0`

**Purpose**: Drop-in replacement for asyncio event loop

**Performance**:
- 2-4x faster than default asyncio
- Written in Cython
- Uses libuv (Node.js event loop)

**Usage**:
```python
import asyncio
import uvloop

# Install uvloop as default loop
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

# Now asyncio.run() uses uvloop automatically
asyncio.run(main())
```

**Recommendation**: `uvloop>=0.19.0` (optional, production enhancement)

---

## 3. File System Monitoring

### 3.1 Watchdog vs Watchfiles Comparison

| Feature | `watchdog` | `watchfiles` |
|---------|-----------|--------------|
| **macOS Backend** | FSEvents (via PyObjC) | Rust notify (native) |
| **Performance** | Good (Python) | Excellent (Rust) |
| **CPU Usage** | Moderate | Low |
| **Event Accuracy** | Sometimes duplicate | Debounced, clean |
| **Async Support** | Via threading | Native async |
| **Dependencies** | Pure Python + PyObjC | Rust binary |
| **Installation Size** | ~500KB | ~2MB (includes binary) |
| **Maintenance** | Active | Very active |

### 3.2 Watchfiles (Recommended)

**Package**: `watchfiles >= 0.21.0`

**Why Watchfiles Wins**:
1. **Native Async**: Built for async/await from ground up
2. **Rust Performance**: 10-100x faster than Python watchers
3. **Smart Debouncing**: Coalesces rapid file changes
4. **macOS FSEvents**: Native integration, no PyObjC needed
5. **Cross-Platform**: Consistent behavior across OS

**Usage Pattern**:
```python
from watchfiles import awatch

async def watch_consciousness_files():
    async for changes in awatch(
        '/path/to/consciousness/files',
        recursive=True,
        ignore_paths=['.git', '__pycache__', '*.pyc']
    ):
        for change_type, path in changes:
            # change_type: 'added', 'modified', 'deleted'
            await process_file_change(change_type, path)
```

**Advanced Features**:
```python
from watchfiles import awatch, Change

async def advanced_watch():
    async for changes in awatch(
        '/path',
        watch_filter=lambda change, path: (
            change == Change.modified and
            path.endswith('.md')
        ),
        debounce=1000,  # 1 second debounce
        rust_timeout=5000  # Rust polling interval
    ):
        await handle_changes(changes)
```

**Recommendation**: `watchfiles>=0.21.0,<1.0.0`

---

### 3.3 Watchdog (Alternative)

**Package**: `watchdog >= 3.0.0`

**When to Use**:
- Need pure Python (no Rust compilation)
- Advanced event filtering in Python
- Pattern matching with `PatternMatchingEventHandler`

**Usage**:
```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ConsciousnessHandler(FileSystemEventHandler):
    def on_modified(self, event):
        # Runs in separate thread, not async-native
        asyncio.create_task(self.handle_change(event.src_path))

observer = Observer()
observer.schedule(handler, '/path', recursive=True)
observer.start()
```

**Drawbacks**:
- Thread-based, not async-native
- More CPU usage on macOS
- Occasional duplicate events

**Recommendation**: Only if Rust compilation is problematic

---

## 4. Process Monitoring

### 4.1 PSUtil

**Package**: `psutil >= 5.9.0`

**Purpose**: Cross-platform process and system monitoring

**Key Capabilities**:
```python
import psutil

# Monitor specific process (LM Studio)
def monitor_lm_studio():
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
        if 'LM Studio' in proc.info['name']:
            return {
                'pid': proc.info['pid'],
                'cpu': proc.info['cpu_percent'],
                'memory_mb': proc.info['memory_info'].rss / 1024 / 1024,
                'status': proc.status(),
                'threads': proc.num_threads()
            }

# System-wide monitoring
async def monitor_system():
    while True:
        stats = {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'net_io': psutil.net_io_counters()
        }
        await log_stats(stats)
        await asyncio.sleep(60)
```

**Advanced Features**:
```python
# Process creation/termination callbacks
def on_proc_created(proc):
    if 'python' in proc.name():
        print(f"New Python process: {proc.pid}")

# Monitor process tree
def get_process_tree(pid):
    proc = psutil.Process(pid)
    children = proc.children(recursive=True)
    return [p.pid for p in children]

# Network connections
def get_connections(pid):
    proc = psutil.Process(pid)
    return proc.connections(kind='inet')
```

**Performance Notes**:
- Lightweight C extension
- Minimal overhead (~1-2% CPU for polling)
- Thread-safe

**Recommendation**: `psutil>=5.9.0,<6.0.0`

---

## 5. State Persistence

### 5.1 SQLite Options

#### Option A: aiosqlite (Recommended)

**Package**: `aiosqlite >= 0.19.0`

**Advantages**:
- True async I/O (no thread pool)
- Drop-in replacement for `sqlite3`
- Context manager support
- Transaction handling

**Usage**:
```python
import aiosqlite

async def init_db():
    async with aiosqlite.connect('consciousness.db') as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS thoughts (
                id INTEGER PRIMARY KEY,
                timestamp REAL,
                content TEXT,
                context JSON,
                processed BOOLEAN
            )
        ''')
        await db.commit()

async def store_thought(content: str, context: dict):
    async with aiosqlite.connect('consciousness.db') as db:
        await db.execute(
            'INSERT INTO thoughts (timestamp, content, context, processed) VALUES (?, ?, ?, ?)',
            (time.time(), content, json.dumps(context), False)
        )
        await db.commit()

async def get_unprocessed():
    async with aiosqlite.connect('consciousness.db') as db:
        async with db.execute('SELECT * FROM thoughts WHERE processed = 0') as cursor:
            return await cursor.fetchall()
```

**Recommendation**: `aiosqlite>=0.19.0,<1.0.0`

---

#### Option B: SQLAlchemy (If Complex Queries Needed)

**Package**: `sqlalchemy[asyncio] >= 2.0.0`

**When to Use**:
- Complex relationships
- Query builder needed
- ORM benefits outweigh overhead

**Usage**:
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Float, Boolean, JSON

Base = declarative_base()

class Thought(Base):
    __tablename__ = 'thoughts'
    id = Column(Integer, primary_key=True)
    timestamp = Column(Float)
    content = Column(String)
    context = Column(JSON)
    processed = Column(Boolean, default=False)

engine = create_async_engine('sqlite+aiosqlite:///consciousness.db')
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def store_thought(content: str, context: dict):
    async with AsyncSessionLocal() as session:
        thought = Thought(timestamp=time.time(), content=content, context=context)
        session.add(thought)
        await session.commit()
```

**Drawbacks**:
- Heavy dependency
- Learning curve
- Overkill for simple key-value storage

**Recommendation**: Only if ORM truly needed

---

#### Option C: File-Based Alternatives

**TinyDB** (`tinydb >= 4.8.0`):
```python
from tinydb import TinyDB, Query

db = TinyDB('consciousness.json')
thoughts = db.table('thoughts')

# Insert
thoughts.insert({'content': 'test', 'timestamp': time.time()})

# Query
Thought = Query()
results = thoughts.search(Thought.processed == False)
```

**Pros**: Pure Python, JSON-based, simple
**Cons**: Not async, slower than SQLite, no ACID guarantees

**Recommendation**: Not suitable for daemon (no async support)

---

### 5.2 Final Persistence Recommendation

**Use `aiosqlite`**:
- Native async
- Lightweight
- ACID guarantees
- Perfect for daemon workloads
- Easy migration to PostgreSQL later if needed

---

## 6. Logging

### 6.1 Structlog vs Standard Logging

| Feature | `structlog` | Standard `logging` |
|---------|------------|-------------------|
| **Structured Output** | Native | Requires custom formatter |
| **JSON Support** | Built-in | Manual implementation |
| **Context Binding** | Excellent | Poor |
| **Performance** | Fast | Moderate |
| **Async Support** | Yes | Limited |
| **Machine Parsing** | Easy | Harder |

### 6.2 Structlog (Recommended)

**Package**: `structlog >= 24.0.0`

**Why Structlog**:
1. **Structured by Default**: Every log is a dictionary
2. **Context Binding**: Attach context that persists
3. **Processors**: Transform logs in pipeline
4. **JSON Output**: Machine-readable logs
5. **Development-Friendly**: Human-readable in dev, JSON in prod

**Configuration**:
```python
import structlog
import logging
from structlog.processors import (
    TimeStamper,
    add_log_level,
    StackInfoRenderer,
    format_exc_info,
    JSONRenderer
)

# Configure structlog
structlog.configure(
    processors=[
        add_log_level,
        TimeStamper(fmt="iso"),
        StackInfoRenderer(),
        format_exc_info,
        JSONRenderer()  # Production: JSON output
        # structlog.dev.ConsoleRenderer()  # Development: pretty colors
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Get logger
logger = structlog.get_logger()
```

**Usage Patterns**:
```python
# Basic logging
logger.info("consciousness_startup", version="1.0.0", pid=os.getpid())

# Context binding
log = logger.bind(component="file_watcher", path="/consciousness/files")
log.info("watching_started")
log.debug("file_detected", filename="thought.md")

# Error logging with context
try:
    await process_file(path)
except Exception as exc:
    logger.error(
        "file_processing_failed",
        path=path,
        error=str(exc),
        exc_info=True
    )
```

**Output (JSON)**:
```json
{
  "event": "consciousness_startup",
  "version": "1.0.0",
  "pid": 12345,
  "timestamp": "2025-01-04T10:30:00.123456Z",
  "level": "info"
}
```

**Output (Development)**:
```
2025-01-04 10:30:00 [info     ] consciousness_startup      version=1.0.0 pid=12345
```

**Recommendation**: `structlog>=24.0.0,<25.0.0`

---

### 6.3 Log Rotation

**Package**: `python-json-logger >= 2.0.0` (if using standard logging)

**For Structlog + File Rotation**:
```python
from logging.handlers import RotatingFileHandler
import structlog

# Configure rotating file handler
file_handler = RotatingFileHandler(
    'consciousness.log',
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5
)

# Integrate with structlog
logging.basicConfig(
    handlers=[file_handler],
    level=logging.INFO
)
```

**Alternative: logrotate (System-Level)**:
```bash
# /etc/logrotate.d/consciousness
/var/log/consciousness/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

**Recommendation**: Use system `logrotate` for production

---

## 7. Configuration Management

### 7.1 Pydantic Settings

**Package**: `pydantic >= 2.0.0` + `pydantic-settings >= 2.0.0`

**Why Pydantic v2**:
- 5-50x faster than v1 (Rust core)
- Better type validation
- JSON schema generation
- Nested models
- Environment variable parsing

**Configuration Schema**:
```python
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class LMStudioSettings(BaseSettings):
    base_url: str = Field(default="http://localhost:1234/v1")
    api_key: str = Field(default="lm-studio")
    model: str = Field(default="local-model")
    timeout: int = Field(default=30, ge=1, le=300)
    max_retries: int = Field(default=3, ge=0, le=10)

class FileWatcherSettings(BaseSettings):
    watch_paths: list[str] = Field(default_factory=list)
    ignore_patterns: list[str] = Field(default_factory=lambda: ['.git', '__pycache__'])
    debounce_seconds: float = Field(default=1.0, ge=0.1, le=10.0)

class ConsciousnessConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='CONSCIOUSNESS_',
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False
    )

    lm_studio: LMStudioSettings = Field(default_factory=LMStudioSettings)
    file_watcher: FileWatcherSettings = Field(default_factory=FileWatcherSettings)

    log_level: str = Field(default="INFO")
    db_path: str = Field(default="consciousness.db")

    @field_validator('log_level')
    def validate_log_level(cls, v):
        if v.upper() not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            raise ValueError(f"Invalid log level: {v}")
        return v.upper()

# Load configuration
config = ConsciousnessConfig()
```

**Environment Variables**:
```bash
# .env file
CONSCIOUSNESS_LOG_LEVEL=DEBUG
CONSCIOUSNESS_LM_STUDIO__BASE_URL=http://localhost:1234/v1
CONSCIOUSNESS_FILE_WATCHER__WATCH_PATHS=["/path/one","/path/two"]
```

**Recommendation**: `pydantic>=2.0.0,<3.0.0` + `pydantic-settings>=2.0.0,<3.0.0`

---

### 7.2 Python-dotenv

**Package**: `python-dotenv >= 1.0.0`

**Purpose**: Load `.env` files (Pydantic uses this automatically)

**Standalone Usage**:
```python
from dotenv import load_dotenv
import os

load_dotenv()  # Load .env file

api_key = os.getenv('ANTHROPIC_API_KEY')
```

**Recommendation**: `python-dotenv>=1.0.0,<2.0.0`

---

### 7.3 YAML Configuration (Optional)

**Package**: `pyyaml >= 6.0.0`

**When to Use**: Human-editable config files

**Usage**:
```python
import yaml

with open('consciousness.yaml') as f:
    config = yaml.safe_load(f)
```

**Alternative**: `ruamel.yaml` (preserves comments, better for round-tripping)

**Recommendation**: `pyyaml>=6.0.0,<7.0.0` (optional)

---

## 8. HTTP/Async Client

### 8.1 HTTPX vs AIOHTTP

| Feature | `httpx` | `aiohttp` |
|---------|---------|-----------|
| **API Style** | Requests-like | Lower-level |
| **HTTP/2** | Yes | No |
| **Sync + Async** | Both | Async only |
| **Type Hints** | Excellent | Good |
| **Connection Pooling** | Automatic | Manual setup |
| **Timeouts** | Granular | Basic |
| **Redirects** | Automatic | Manual |
| **Cookies** | Built-in | Requires setup |

### 8.2 HTTPX (Recommended)

**Package**: `httpx >= 0.27.0`

**Why HTTPX**:
1. **Familiar API**: Drop-in replacement for `requests`
2. **HTTP/2**: Better performance with multiplexing
3. **Unified**: Same API for sync and async
4. **Type Hints**: Full type coverage
5. **Modern**: Active development, clean codebase

**Usage**:
```python
import httpx

# Async client
async with httpx.AsyncClient(
    base_url="http://localhost:1234/v1",
    timeout=httpx.Timeout(30.0, connect=5.0),
    limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
) as client:
    response = await client.post(
        "/chat/completions",
        json={
            "model": "local-model",
            "messages": [{"role": "user", "content": "Hello"}]
        }
    )
    data = response.json()
```

**Advanced Features**:
```python
# Custom headers
client = httpx.AsyncClient(
    headers={"User-Agent": "ConsciousnessOrchestrator/1.0"}
)

# Retry logic with httpx-retry
from httpx_retry import AsyncClient

client = AsyncClient(
    retries=3,
    backoff_factor=0.5
)

# Streaming responses
async with client.stream('GET', '/large-file') as response:
    async for chunk in response.aiter_bytes():
        await process_chunk(chunk)
```

**Recommendation**: `httpx>=0.27.0,<1.0.0`

---

### 8.3 AIOHTTP (Alternative)

**Package**: `aiohttp >= 3.9.0`

**When to Use**:
- Need server capabilities (AIOHTTP has both client and server)
- Lower-level control required
- Existing codebase uses it

**Usage**:
```python
import aiohttp

async with aiohttp.ClientSession() as session:
    async with session.post(
        'http://localhost:1234/v1/chat/completions',
        json={"model": "local-model", "messages": [...]}
    ) as response:
        data = await response.json()
```

**Recommendation**: Only if server features needed

---

## 9. Development Dependencies

### 9.1 Testing

**pytest >= 8.0.0**:
```python
# Basic test
def test_thought_storage():
    thought = Thought(content="test")
    assert thought.content == "test"

# Async test
import pytest

@pytest.mark.asyncio
async def test_async_storage():
    await store_thought("test", {})
    thoughts = await get_unprocessed()
    assert len(thoughts) > 0
```

**pytest-asyncio >= 0.23.0**:
- Enables `@pytest.mark.asyncio`
- Async fixtures
- Event loop management

**pytest-cov >= 4.1.0**:
```bash
pytest --cov=consciousness --cov-report=html
```

**pytest-mock >= 3.12.0**:
```python
def test_llm_call(mocker):
    mock_client = mocker.patch('openai.AsyncOpenAI')
    # Test with mocked LLM
```

**Recommendation**:
```
pytest>=8.0.0,<9.0.0
pytest-asyncio>=0.23.0,<1.0.0
pytest-cov>=4.1.0,<5.0.0
pytest-mock>=3.12.0,<4.0.0
```

---

### 9.2 Code Formatting

**black >= 24.0.0**:
- Opinionated formatter
- PEP 8 compliant
- Zero configuration

```bash
black consciousness/
```

**Recommendation**: `black>=24.0.0,<25.0.0`

---

### 9.3 Linting

**ruff >= 0.1.0**:
- 10-100x faster than flake8/pylint
- Rust-based
- Replaces: flake8, isort, pydocstyle, pyupgrade
- Auto-fix capabilities

```bash
ruff check consciousness/
ruff check --fix consciousness/
```

**Configuration (pyproject.toml)**:
```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "ANN", "ASYNC", "B", "C4"]
ignore = ["ANN101", "ANN102"]  # Ignore self/cls annotations
```

**Recommendation**: `ruff>=0.1.0,<1.0.0`

---

### 9.4 Type Checking

**mypy >= 1.8.0**:
```bash
mypy consciousness/
```

**Configuration (pyproject.toml)**:
```toml
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

**Recommendation**: `mypy>=1.8.0,<2.0.0`

---

## 10. Python Version Requirements

### 10.1 Minimum Version: Python 3.11

**Why 3.11+**:

1. **Task Groups** (`asyncio.TaskGroup`):
   ```python
   async with TaskGroup() as tg:
       tg.create_task(task1())
       tg.create_task(task2())
   # Structured concurrency, automatic cleanup
   ```

2. **Exception Groups**:
   ```python
   try:
       async with TaskGroup() as tg:
           tg.create_task(failing_task())
   except* ValueError as eg:
       # Handle grouped exceptions
   ```

3. **Performance**: 10-60% faster than 3.10

4. **Better Error Messages**: Precise line numbers, suggestions

5. **Type Hints**: `Self` type, variadic generics

### 10.2 Python 3.12 Benefits (Optional)

- **Per-task Contextvars**: Better async context isolation
- **f-string Performance**: 2x faster
- **Override Decorator**: Better type safety
- **Performance**: Additional 5-10% speed boost

### 10.3 Python 3.13 (Future)

- **Free-threaded Mode**: No GIL (experimental)
- **JIT Compiler**: Significant speedups
- **Not Recommended Yet**: Wait for ecosystem compatibility

### 10.4 Recommendation

**Minimum**: Python 3.11.0
**Recommended**: Python 3.11.7+ or Python 3.12.1+
**Avoid**: Python 3.13 (too new, ecosystem not ready)

---

## 11. Complete Requirements Files

### 11.1 requirements.txt

```txt
# Core LLM Clients
openai>=1.12.0,<2.0.0
anthropic>=0.18.0,<1.0.0  # Optional

# File System Monitoring
watchfiles>=0.21.0,<1.0.0

# Process Monitoring
psutil>=5.9.0,<6.0.0

# Async Database
aiosqlite>=0.19.0,<1.0.0

# Logging
structlog>=24.0.0,<25.0.0

# Configuration
pydantic>=2.0.0,<3.0.0
pydantic-settings>=2.0.0,<3.0.0
python-dotenv>=1.0.0,<2.0.0

# HTTP Client
httpx>=0.27.0,<1.0.0

# Optional: Performance
uvloop>=0.19.0,<1.0.0; sys_platform != 'win32'

# Optional: YAML Config
pyyaml>=6.0.0,<7.0.0
```

### 11.2 requirements-dev.txt

```txt
# Include main requirements
-r requirements.txt

# Testing
pytest>=8.0.0,<9.0.0
pytest-asyncio>=0.23.0,<1.0.0
pytest-cov>=4.1.0,<5.0.0
pytest-mock>=3.12.0,<4.0.0

# Code Quality
black>=24.0.0,<25.0.0
ruff>=0.1.0,<1.0.0
mypy>=1.8.0,<2.0.0

# Type Stubs
types-pyyaml>=6.0.0
types-psutil>=5.9.0
```

---

### 11.3 pyproject.toml

```toml
[project]
name = "consciousness-orchestrator"
version = "0.1.0"
description = "Continuous consciousness monitoring and LLM orchestration daemon"
requires-python = ">=3.11"
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]
readme = "README.md"
license = {text = "MIT"}

dependencies = [
    "openai>=1.12.0,<2.0.0",
    "watchfiles>=0.21.0,<1.0.0",
    "psutil>=5.9.0,<6.0.0",
    "aiosqlite>=0.19.0,<1.0.0",
    "structlog>=24.0.0,<25.0.0",
    "pydantic>=2.0.0,<3.0.0",
    "pydantic-settings>=2.0.0,<3.0.0",
    "python-dotenv>=1.0.0,<2.0.0",
    "httpx>=0.27.0,<1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0,<9.0.0",
    "pytest-asyncio>=0.23.0,<1.0.0",
    "pytest-cov>=4.1.0,<5.0.0",
    "pytest-mock>=3.12.0,<4.0.0",
    "black>=24.0.0,<25.0.0",
    "ruff>=0.1.0,<1.0.0",
    "mypy>=1.8.0,<2.0.0",
    "types-pyyaml>=6.0.0",
]

performance = [
    "uvloop>=0.19.0,<1.0.0",
]

anthropic = [
    "anthropic>=0.18.0,<1.0.0",
]

yaml = [
    "pyyaml>=6.0.0,<7.0.0",
    "types-pyyaml>=6.0.0",
]

[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[tool.black]
line-length = 100
target-version = ['py311']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
)/
'''

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # pyflakes
    "I",      # isort
    "N",      # pep8-naming
    "UP",     # pyupgrade
    "ANN",    # flake8-annotations
    "ASYNC",  # flake8-async
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "DTZ",    # flake8-datetimez
    "T20",    # flake8-print
    "SIM",    # flake8-simplify
    "PTH",    # flake8-use-pathlib
]
ignore = [
    "ANN101",  # Missing type annotation for self
    "ANN102",  # Missing type annotation for cls
]

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["ANN", "T20"]  # Allow prints in tests, no annotations required

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_generics = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
follow_imports = "normal"
ignore_missing_imports = false

[[tool.mypy.overrides]]
module = [
    "watchfiles.*",
    "structlog.*",
]
ignore_missing_imports = true

[tool.pytest.ini_options]
minversion = "8.0"
addopts = [
    "--strict-markers",
    "--strict-config",
    "--cov=consciousness",
    "--cov-report=term-missing",
    "--cov-report=html",
]
testpaths = ["tests"]
asyncio_mode = "auto"
```

---

## 12. Development Setup Instructions

### 12.1 Initial Setup

```bash
# 1. Ensure Python 3.11+
python --version  # Should be 3.11.0 or higher

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate  # Windows

# 4. Upgrade pip
pip install --upgrade pip setuptools wheel

# 5. Install dependencies
pip install -e ".[dev,performance]"

# 6. Verify installation
python -c "import asyncio; import watchfiles; import structlog; print('All imports successful')"
```

### 12.2 Development Workflow

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=consciousness --cov-report=html
open htmlcov/index.html

# Format code
black consciousness/ tests/

# Lint code
ruff check consciousness/ tests/
ruff check --fix consciousness/ tests/  # Auto-fix

# Type check
mypy consciousness/

# All checks (recommended pre-commit)
black consciousness/ && ruff check --fix consciousness/ && mypy consciousness/ && pytest
```

### 12.3 Pre-commit Hooks (Optional)

**Install pre-commit**:
```bash
pip install pre-commit
```

**Create `.pre-commit-config.yaml`**:
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.1.1
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.14
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-pyyaml, types-psutil]
```

**Install hooks**:
```bash
pre-commit install
```

---

## 13. Dependency Installation Order

### 13.1 Recommended Installation Sequence

```bash
# 1. Core runtime dependencies (required for execution)
pip install openai watchfiles psutil aiosqlite

# 2. Configuration and logging (required for configuration)
pip install pydantic pydantic-settings python-dotenv structlog

# 3. HTTP client (required for API calls)
pip install httpx

# 4. Optional performance boost (macOS/Linux only)
pip install uvloop  # Skip on Windows

# 5. Optional anthropic client
pip install anthropic

# 6. Development dependencies (testing, linting, formatting)
pip install pytest pytest-asyncio pytest-cov pytest-mock black ruff mypy

# 7. Type stubs for type checking
pip install types-pyyaml types-psutil
```

### 13.2 Alternative: Single Command Installation

```bash
# Install everything at once
pip install -e ".[dev,performance,anthropic,yaml]"
```

---

## 14. Dependency Size Analysis

| Package | Size | Install Time | Purpose |
|---------|------|--------------|---------|
| `openai` | ~150KB | <1s | LLM client |
| `watchfiles` | ~2MB | 2-3s | File monitoring (includes Rust binary) |
| `psutil` | ~500KB | <1s | Process monitoring |
| `aiosqlite` | ~20KB | <1s | Async SQLite |
| `structlog` | ~100KB | <1s | Structured logging |
| `pydantic` | ~3MB | 3-5s | Validation (includes Rust core) |
| `httpx` | ~200KB | <1s | HTTP client |
| `uvloop` | ~800KB | 1-2s | Event loop |
| **Total Runtime** | **~7MB** | **10-15s** | |
| **With Dev Tools** | **~15MB** | **20-30s** | |

**Recommendation**: Acceptable size for a daemon, fast installation

---

## 15. Security Considerations

### 15.1 Dependency Security

**Use `pip-audit`** (optional):
```bash
pip install pip-audit
pip-audit
```

**Check for known vulnerabilities**:
```bash
# Safety check (requires safety package)
pip install safety
safety check
```

### 15.2 API Key Management

**NEVER hardcode API keys**:
```python
# ❌ WRONG
api_key = "sk-abc123..."

# ✅ CORRECT
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    raise ValueError("ANTHROPIC_API_KEY not set")
```

**Use `.env` file** (excluded from git):
```bash
# .gitignore
.env
*.env
.env.*
```

---

## 16. Performance Optimization

### 16.1 Async Best Practices

```python
# ✅ Good: Concurrent operations
async def process_multiple():
    async with asyncio.TaskGroup() as tg:
        tg.create_task(task1())
        tg.create_task(task2())
        tg.create_task(task3())

# ❌ Bad: Sequential operations
async def process_sequential():
    await task1()
    await task2()
    await task3()
```

### 16.2 Connection Pooling

```python
# HTTPX connection pooling
client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_connections=20,
        max_keepalive_connections=10
    )
)

# SQLite connection pooling (via connection reuse)
# aiosqlite uses a single connection per context manager
# For pooling, use SQLAlchemy with connection pool
```

### 16.3 Memory Management

```python
# Limit watchfiles memory
async for changes in awatch('/path', rust_timeout=5000):
    # Process quickly to avoid buffering
    await process_immediately(changes)

# Clear processed thoughts from database
async def cleanup_old_thoughts():
    async with aiosqlite.connect('consciousness.db') as db:
        await db.execute(
            'DELETE FROM thoughts WHERE processed = 1 AND timestamp < ?',
            (time.time() - 86400 * 7,)  # Keep 7 days
        )
        await db.commit()
```

---

## 17. Troubleshooting

### 17.1 Common Issues

**Problem**: `watchfiles` won't install
```bash
# Solution: Ensure Rust toolchain (usually bundled)
pip install --upgrade pip
pip install watchfiles --verbose
```

**Problem**: `uvloop` not available on Windows
```bash
# Solution: Skip uvloop on Windows (not needed)
pip install 'uvloop>=0.19.0; sys_platform != "win32"'
```

**Problem**: Type checking errors with `structlog`
```bash
# Solution: Add to mypy config
# [[tool.mypy.overrides]]
# module = ["structlog.*"]
# ignore_missing_imports = true
```

---

## 18. Future Considerations

### 18.1 Potential Upgrades

**When to Consider Postgres**:
- More than 100K thoughts stored
- Complex queries needed
- Multiple writers
- **Migration**: `asyncpg` + `SQLAlchemy 2.0`

**When to Add Redis**:
- Need pub/sub messaging
- Distributed caching
- Real-time coordination
- **Package**: `redis[hiredis]` or `aioredis`

**When to Add Message Queue**:
- Multiple orchestrator instances
- Distributed processing
- Job scheduling
- **Options**: RabbitMQ (`aio-pika`), Redis Queue (`rq`)

---

## 19. Summary and Final Recommendations

### 19.1 Core Dependencies (Required)

```txt
openai>=1.12.0,<2.0.0          # LM Studio client
watchfiles>=0.21.0,<1.0.0      # File monitoring
psutil>=5.9.0,<6.0.0           # Process monitoring
aiosqlite>=0.19.0,<1.0.0       # Async database
structlog>=24.0.0,<25.0.0      # Structured logging
pydantic>=2.0.0,<3.0.0         # Configuration validation
pydantic-settings>=2.0.0,<3.0.0
python-dotenv>=1.0.0,<2.0.0
httpx>=0.27.0,<1.0.0           # HTTP client
```

### 19.2 Optional Dependencies

```txt
# Performance
uvloop>=0.19.0,<1.0.0  # macOS/Linux only

# Claude API
anthropic>=0.18.0,<1.0.0

# YAML config
pyyaml>=6.0.0,<7.0.0
```

### 19.3 Development Dependencies

```txt
pytest>=8.0.0,<9.0.0
pytest-asyncio>=0.23.0,<1.0.0
pytest-cov>=4.1.0,<5.0.0
black>=24.0.0,<25.0.0
ruff>=0.1.0,<1.0.0
mypy>=1.8.0,<2.0.0
```

### 19.4 Python Version

- **Minimum**: Python 3.11.0
- **Recommended**: Python 3.11.7+ or 3.12.1+

---

## 20. Quick Start Commands

```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev,performance]"

# Development
black consciousness/ && ruff check --fix consciousness/ && mypy consciousness/ && pytest

# Run
python -m consciousness.main
```

---

**End of Dependency Research Document**

This comprehensive analysis provides all necessary information for setting up the Python environment for the Consciousness orchestrator daemon. All recommendations are based on current best practices (January 2025), performance benchmarks, and ecosystem maturity.
