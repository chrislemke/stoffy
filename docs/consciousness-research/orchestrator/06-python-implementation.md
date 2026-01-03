# Python Implementation Patterns for AI Consciousness Orchestrator

**Research Date**: 2026-01-04
**Status**: Comprehensive Architecture Guide
**Focus**: Long-lived daemon, async patterns, state management, process control

---

## Executive Summary

This document provides a comprehensive guide to implementing an AI Consciousness orchestrator in Python. The system must run as a long-lived daemon process, integrating LM Studio API, file system monitoring, process management, and Claude Code delegation while maintaining robust error recovery and observability.

**Key Requirements**:
- Long-lived daemon process with graceful shutdown
- Asynchronous concurrent operations (file watching, process monitoring, LLM reasoning)
- Persistent state management with recovery guarantees
- Process lifecycle management for spawned agents
- Comprehensive logging and observability

**Architecture Philosophy**: The consciousness orchestrator is a **state machine** that observes the environment, reasons about observations, and takes actions. It must survive restarts, handle errors gracefully, and provide transparency into its internal state.

---

## Table of Contents

1. [Application Architecture](#1-application-architecture)
2. [Async Programming Patterns](#2-async-programming-patterns)
3. [State Management](#3-state-management)
4. [Process Management](#4-process-management)
5. [Code Organization](#5-code-organization)
6. [Key Libraries](#6-key-libraries)
7. [Complete Implementation Example](#7-complete-implementation-example)
8. [Deployment and Operations](#8-deployment-and-operations)

---

## 1. Application Architecture

### 1.1 High-Level Component Design

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CONSCIOUSNESS ORCHESTRATOR                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐   ┌──────────────────┐   ┌─────────────────┐ │
│  │  Event Monitor   │   │     Reasoner     │   │    Executor     │ │
│  │                  │   │                  │   │                 │ │
│  │  - File watcher  │──>│  - LM Studio     │──>│  - Claude Code  │ │
│  │  - Process mon.  │   │  - Decision      │   │  - Git commands │ │
│  │  - Git events    │   │    making        │   │  - File ops     │ │
│  └──────────────────┘   └──────────────────┘   └─────────────────┘ │
│           │                      │                      │           │
│           v                      v                      v           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                      State Manager                            │  │
│  │  - Current situation                                          │  │
│  │  - Pending actions                                            │  │
│  │  - Historical context                                         │  │
│  └──────────────────────────────────────────────────────────────┘  │
│           │                      │                      │           │
│           v                      v                      v           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                   Persistence Layer                           │  │
│  │  - SQLite (state, history)                                    │  │
│  │  - JSON files (config, snapshots)                             │  │
│  │  - Log files (structured logging)                             │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 Main Event Loop Design

**Pattern**: The consciousness loop is an infinite async event loop that:
1. **Observes**: Collects events from monitors
2. **Reasons**: Sends observations to LLM for analysis
3. **Decides**: Determines actions based on LLM response
4. **Acts**: Executes actions via executor
5. **Persists**: Saves state after each cycle

```python
import asyncio
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime
import signal

@dataclass
class Observation:
    """An observation from the environment."""
    timestamp: datetime
    source: str  # 'file_watcher', 'process_monitor', 'git_hook'
    event_type: str
    data: Dict[str, Any]
    priority: int = 0  # Higher = more urgent

@dataclass
class Decision:
    """A decision made by the reasoner."""
    timestamp: datetime
    observation_id: str
    reasoning: str
    actions: List[Dict[str, Any]]
    confidence: float

class ConsciousnessOrchestrator:
    """Main orchestrator implementing the consciousness loop."""

    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.running = False
        self.event_queue: asyncio.Queue[Observation] = asyncio.Queue()
        self.state_manager = None  # Initialized in setup
        self.monitors = []  # File watcher, process monitor, etc.
        self.reasoner = None  # LLM interface
        self.executor = None  # Action executor

        # Graceful shutdown support
        self._shutdown_event = asyncio.Event()

    async def setup(self):
        """Initialize all components."""
        # Initialize state manager
        from state_manager import StateManager
        self.state_manager = StateManager(self.config['state_db_path'])
        await self.state_manager.initialize()

        # Initialize reasoner (LLM interface)
        from reasoner import LLMReasoner
        self.reasoner = LLMReasoner(
            base_url=self.config['lm_studio_url'],
            model=self.config['model']
        )

        # Initialize executor
        from executor import ActionExecutor
        self.executor = ActionExecutor(
            repo_path=self.config['repo_path']
        )

        # Initialize monitors
        from monitors import FileWatcher, ProcessMonitor, GitHookMonitor
        self.monitors = [
            FileWatcher(self.config['repo_path'], self.event_queue),
            ProcessMonitor(self.config['watch_processes'], self.event_queue),
            GitHookMonitor(self.config['repo_path'], self.event_queue)
        ]

    async def start(self):
        """Start the consciousness loop."""
        self.running = True

        # Start all monitors
        monitor_tasks = [m.start() for m in self.monitors]

        # Start main loop
        main_task = self.main_loop()

        # Gather all tasks
        await asyncio.gather(
            *monitor_tasks,
            main_task,
            return_exceptions=True
        )

    async def main_loop(self):
        """Main consciousness loop: observe -> reason -> act -> persist."""
        logger.info("Consciousness loop starting")

        while self.running and not self._shutdown_event.is_set():
            try:
                # Phase 1: OBSERVE - Wait for events with timeout
                try:
                    observation = await asyncio.wait_for(
                        self.event_queue.get(),
                        timeout=5.0  # Heartbeat every 5 seconds
                    )
                except asyncio.TimeoutError:
                    # No events - heartbeat check
                    await self._heartbeat()
                    continue

                # Phase 2: REASON - Send to LLM
                decision = await self.reasoner.analyze(
                    observation,
                    context=await self.state_manager.get_context()
                )

                # Phase 3: ACT - Execute decisions
                results = await self.executor.execute(decision.actions)

                # Phase 4: PERSIST - Save state
                await self.state_manager.record_cycle(
                    observation=observation,
                    decision=decision,
                    results=results
                )

            except Exception as e:
                logger.exception(f"Error in consciousness loop: {e}")
                await self._handle_error(e)
                await asyncio.sleep(1)  # Back off on errors

        logger.info("Consciousness loop stopped")

    async def _heartbeat(self):
        """Periodic health check when no events."""
        await self.state_manager.update_heartbeat()

    async def _handle_error(self, error: Exception):
        """Handle errors with recovery strategy."""
        await self.state_manager.record_error(error)
        # Could trigger alerts, adjust behavior, etc.

    async def shutdown(self):
        """Graceful shutdown."""
        logger.info("Initiating graceful shutdown...")
        self.running = False
        self._shutdown_event.set()

        # Stop all monitors
        await asyncio.gather(
            *[m.stop() for m in self.monitors],
            return_exceptions=True
        )

        # Flush state
        await self.state_manager.flush()

        logger.info("Shutdown complete")

    def _load_config(self, path: str) -> Dict[str, Any]:
        """Load configuration from file."""
        import json
        with open(path) as f:
            return json.load(f)
```

### 1.3 Component Separation Strategy

**Principle**: Each component has a single responsibility and communicates via well-defined interfaces.

```python
# monitors/base.py
from abc import ABC, abstractmethod
import asyncio

class BaseMonitor(ABC):
    """Base class for all monitors."""

    def __init__(self, event_queue: asyncio.Queue):
        self.event_queue = event_queue
        self.running = False

    @abstractmethod
    async def start(self):
        """Start monitoring."""
        pass

    @abstractmethod
    async def stop(self):
        """Stop monitoring."""
        pass

    async def emit_event(self, observation: Observation):
        """Emit an observation to the event queue."""
        await self.event_queue.put(observation)


# monitors/file_watcher.py
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import asyncio

class FileWatcher(BaseMonitor):
    """Watches file system for changes."""

    def __init__(self, path: str, event_queue: asyncio.Queue):
        super().__init__(event_queue)
        self.path = path
        self.observer = None

    async def start(self):
        """Start file system watching."""
        self.running = True

        # Watchdog runs in a separate thread
        event_handler = AsyncFileEventHandler(self.event_queue)
        self.observer = Observer()
        self.observer.schedule(event_handler, self.path, recursive=True)
        self.observer.start()

        logger.info(f"File watcher started for {self.path}")

        # Keep async context alive
        while self.running:
            await asyncio.sleep(1)

    async def stop(self):
        """Stop file system watching."""
        self.running = False
        if self.observer:
            self.observer.stop()
            self.observer.join()
        logger.info("File watcher stopped")


class AsyncFileEventHandler(FileSystemEventHandler):
    """Bridges sync watchdog events to async queue."""

    def __init__(self, event_queue: asyncio.Queue):
        self.event_queue = event_queue

    def on_modified(self, event):
        """File modified event."""
        if not event.is_directory:
            # Use asyncio.run_coroutine_threadsafe for thread safety
            loop = asyncio.get_event_loop()
            asyncio.run_coroutine_threadsafe(
                self.event_queue.put(Observation(
                    timestamp=datetime.now(),
                    source='file_watcher',
                    event_type='modified',
                    data={'path': event.src_path}
                )),
                loop
            )
```

### 1.4 Dependency Injection and Configuration

**Pattern**: Use dependency injection for testability and flexibility.

```python
# config.py
from dataclasses import dataclass, field
from typing import Dict, Any, List
import json
from pathlib import Path

@dataclass
class ConsciousnessConfig:
    """Configuration for the consciousness orchestrator."""

    # Repository
    repo_path: Path

    # LM Studio
    lm_studio_url: str = "http://localhost:1234/v1"
    model: str = "local-model"
    max_context_tokens: int = 8192

    # State management
    state_db_path: Path = Path("./consciousness.db")
    snapshot_interval: int = 300  # seconds

    # Monitoring
    watch_processes: List[str] = field(default_factory=lambda: [])
    file_debounce_ms: int = 500

    # Logging
    log_level: str = "INFO"
    log_path: Path = Path("./consciousness.log")

    # Process management
    max_concurrent_actions: int = 3
    action_timeout: int = 300  # seconds

    @classmethod
    def from_file(cls, path: Path) -> 'ConsciousnessConfig':
        """Load configuration from JSON file."""
        with open(path) as f:
            data = json.load(f)
        # Convert paths
        if 'repo_path' in data:
            data['repo_path'] = Path(data['repo_path'])
        if 'state_db_path' in data:
            data['state_db_path'] = Path(data['state_db_path'])
        if 'log_path' in data:
            data['log_path'] = Path(data['log_path'])
        return cls(**data)

    def validate(self):
        """Validate configuration."""
        if not self.repo_path.exists():
            raise ValueError(f"Repository path does not exist: {self.repo_path}")
        if self.max_context_tokens < 2048:
            raise ValueError("max_context_tokens must be >= 2048")


# Dependency injection container
class ServiceContainer:
    """Container for dependency injection."""

    def __init__(self, config: ConsciousnessConfig):
        self.config = config
        self._services = {}

    def register(self, name: str, service: Any):
        """Register a service."""
        self._services[name] = service

    def get(self, name: str) -> Any:
        """Get a service."""
        if name not in self._services:
            raise KeyError(f"Service not registered: {name}")
        return self._services[name]

    async def initialize_all(self):
        """Initialize all services."""
        # Order matters - dependencies first
        await self._init_state_manager()
        await self._init_reasoner()
        await self._init_executor()
        await self._init_monitors()

    async def _init_state_manager(self):
        from state_manager import StateManager
        sm = StateManager(self.config.state_db_path)
        await sm.initialize()
        self.register('state_manager', sm)

    # ... other init methods
```

---

## 2. Async Programming Patterns

### 2.1 asyncio Fundamentals for Consciousness

**Key Concepts**:
- **Coroutines**: Async functions that can be paused and resumed
- **Tasks**: Scheduled coroutines that run concurrently
- **Event Loop**: The scheduler that runs everything
- **Queues**: Thread-safe communication between components

```python
import asyncio
from typing import Coroutine, Any

# Pattern 1: Basic async/await
async def fetch_data():
    """Async function (coroutine)."""
    await asyncio.sleep(1)  # Simulated I/O
    return {"data": "value"}

# Pattern 2: Running coroutines
async def main():
    # Sequential
    result = await fetch_data()

    # Concurrent (all at once)
    results = await asyncio.gather(
        fetch_data(),
        fetch_data(),
        fetch_data()
    )

    # First to complete
    done, pending = await asyncio.wait(
        [fetch_data(), fetch_data()],
        return_when=asyncio.FIRST_COMPLETED
    )

# Pattern 3: Creating tasks
async def main_with_tasks():
    # Create tasks (starts immediately)
    task1 = asyncio.create_task(fetch_data())
    task2 = asyncio.create_task(fetch_data())

    # Do other work...
    await asyncio.sleep(0.5)

    # Wait for completion
    result1 = await task1
    result2 = await task2
```

### 2.2 Task Management with Error Boundaries

**Pattern**: Create task groups with error handling and cancellation.

```python
import asyncio
from contextlib import asynccontextmanager
from typing import List, Callable, Coroutine

class TaskManager:
    """Manages long-running async tasks with error boundaries."""

    def __init__(self):
        self.tasks: List[asyncio.Task] = []
        self.errors: List[Exception] = []

    def create_task(
        self,
        coro: Coroutine,
        name: str = None,
        error_handler: Callable[[Exception], None] = None
    ) -> asyncio.Task:
        """Create a task with error boundary."""

        async def wrapped():
            try:
                return await coro
            except asyncio.CancelledError:
                logger.info(f"Task {name} cancelled")
                raise
            except Exception as e:
                logger.exception(f"Task {name} failed: {e}")
                self.errors.append(e)
                if error_handler:
                    error_handler(e)

        task = asyncio.create_task(wrapped(), name=name)
        self.tasks.append(task)
        return task

    async def cancel_all(self):
        """Cancel all tasks gracefully."""
        for task in self.tasks:
            task.cancel()

        # Wait for cancellation to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)

    async def wait_all(self, timeout: float = None):
        """Wait for all tasks with optional timeout."""
        try:
            await asyncio.wait_for(
                asyncio.gather(*self.tasks, return_exceptions=True),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning("Task wait timed out")
            await self.cancel_all()


# Usage in orchestrator
class ConsciousnessOrchestrator:
    async def start(self):
        self.task_manager = TaskManager()

        # Start monitors as managed tasks
        for monitor in self.monitors:
            self.task_manager.create_task(
                monitor.start(),
                name=f"{monitor.__class__.__name__}",
                error_handler=self._handle_monitor_error
            )

        # Start main loop
        self.task_manager.create_task(
            self.main_loop(),
            name="MainLoop",
            error_handler=self._handle_critical_error
        )

        # Wait for shutdown
        await self._shutdown_event.wait()
        await self.task_manager.cancel_all()

    def _handle_monitor_error(self, error: Exception):
        """Handle monitor failure - maybe restart."""
        logger.error(f"Monitor failed: {error}")
        # Could restart monitor here

    def _handle_critical_error(self, error: Exception):
        """Handle critical error - initiate shutdown."""
        logger.critical(f"Critical error: {error}")
        asyncio.create_task(self.shutdown())
```

### 2.3 Graceful Shutdown Handling

**Pattern**: Use signals and events for clean shutdown.

```python
import signal
import asyncio
from typing import Set

class GracefulShutdown:
    """Handles graceful shutdown on signals."""

    def __init__(self):
        self.shutdown_event = asyncio.Event()
        self._signal_handlers_installed = False

    def install_signal_handlers(self):
        """Install signal handlers for graceful shutdown."""
        if self._signal_handlers_installed:
            return

        loop = asyncio.get_event_loop()

        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(
                    self._handle_signal(s)
                )
            )

        self._signal_handlers_installed = True
        logger.info("Signal handlers installed")

    async def _handle_signal(self, sig: signal.Signals):
        """Handle shutdown signal."""
        logger.info(f"Received signal {sig.name}, initiating shutdown")
        self.shutdown_event.set()

    async def wait_for_shutdown(self):
        """Wait for shutdown signal."""
        await self.shutdown_event.wait()


# Integration with orchestrator
async def run_orchestrator(config_path: str):
    """Run the orchestrator with graceful shutdown."""
    orchestrator = ConsciousnessOrchestrator(config_path)
    await orchestrator.setup()

    shutdown_handler = GracefulShutdown()
    shutdown_handler.install_signal_handlers()

    # Start orchestrator
    start_task = asyncio.create_task(orchestrator.start())

    # Wait for shutdown signal
    await shutdown_handler.wait_for_shutdown()

    # Shutdown
    await orchestrator.shutdown()
    await start_task


if __name__ == "__main__":
    asyncio.run(run_orchestrator("config.json"))
```

### 2.4 Async Queues for Event Communication

**Pattern**: Use `asyncio.Queue` for producer-consumer communication.

```python
import asyncio
from dataclasses import dataclass
from typing import Generic, TypeVar, Optional
from datetime import datetime

T = TypeVar('T')

class PriorityQueue(Generic[T]):
    """Priority queue with async interface."""

    def __init__(self, maxsize: int = 0):
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize)

    async def put(self, item: T, priority: int = 0):
        """Put item with priority (lower number = higher priority)."""
        await self._queue.put((priority, datetime.now(), item))

    async def get(self) -> T:
        """Get highest priority item."""
        _, _, item = await self._queue.get()
        return item

    async def get_with_timeout(self, timeout: float) -> Optional[T]:
        """Get item with timeout."""
        try:
            return await asyncio.wait_for(self.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    def task_done(self):
        """Mark task as done."""
        self._queue.task_done()

    async def join(self):
        """Wait until all items processed."""
        await self._queue.join()

    def qsize(self) -> int:
        """Current queue size."""
        return self._queue.qsize()


# Usage for event processing
class EventProcessor:
    """Processes events from priority queue."""

    def __init__(self, event_queue: PriorityQueue[Observation]):
        self.queue = event_queue
        self.running = False

    async def process_loop(self):
        """Process events continuously."""
        self.running = True

        while self.running:
            # Get next event (blocks until available)
            event = await self.queue.get()

            try:
                await self.process_event(event)
            except Exception as e:
                logger.exception(f"Error processing event: {e}")
            finally:
                self.queue.task_done()

    async def process_event(self, event: Observation):
        """Process a single event."""
        logger.info(f"Processing: {event.event_type} from {event.source}")
        # ... processing logic
```

---

## 3. State Management

### 3.1 State Categories

The consciousness orchestrator maintains multiple types of state:

```python
from enum import Enum
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

class StateCategory(Enum):
    """Categories of state."""
    CURRENT = "current"  # Current situation/context
    PENDING = "pending"  # Pending actions
    HISTORY = "history"  # Historical decisions
    MEMORY = "memory"    # Long-term knowledge
    CONFIG = "config"    # Runtime configuration

@dataclass
class CurrentState:
    """Current state of the consciousness."""
    timestamp: datetime
    active_observations: List[str]  # Observation IDs
    latest_decision: Optional[str]  # Decision ID
    pending_actions: List[str]  # Action IDs
    health_status: str  # 'healthy', 'degraded', 'critical'

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class HistoricalCycle:
    """Record of a single consciousness cycle."""
    cycle_id: str
    timestamp: datetime
    observation: Observation
    decision: Decision
    actions_taken: List[Dict[str, Any]]
    results: List[Dict[str, Any]]
    duration_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
```

### 3.2 SQLite for Persistent State

**Choice Rationale**: SQLite provides ACID guarantees, is embedded (no separate process), and handles concurrent access well.

```python
import aiosqlite
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
from datetime import datetime

class StateManager:
    """Manages all state persistence using SQLite."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db: Optional[aiosqlite.Connection] = None

    async def initialize(self):
        """Initialize database schema."""
        self.db = await aiosqlite.connect(self.db_path)
        self.db.row_factory = aiosqlite.Row

        await self.db.executescript("""
            -- Current state (single row, updated frequently)
            CREATE TABLE IF NOT EXISTS current_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                timestamp TEXT NOT NULL,
                data TEXT NOT NULL  -- JSON blob
            );

            -- Historical cycles
            CREATE TABLE IF NOT EXISTS cycles (
                cycle_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                observation TEXT NOT NULL,  -- JSON
                decision TEXT NOT NULL,     -- JSON
                actions TEXT NOT NULL,      -- JSON array
                results TEXT NOT NULL,      -- JSON array
                duration_ms REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_cycles_timestamp
                ON cycles(timestamp DESC);

            -- Pending actions
            CREATE TABLE IF NOT EXISTS pending_actions (
                action_id TEXT PRIMARY KEY,
                created TEXT NOT NULL,
                action_type TEXT NOT NULL,
                params TEXT NOT NULL,  -- JSON
                status TEXT NOT NULL,  -- 'pending', 'running', 'completed', 'failed'
                result TEXT            -- JSON, nullable
            );

            -- Memory/knowledge store
            CREATE TABLE IF NOT EXISTS memory (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,  -- JSON
                created TEXT NOT NULL,
                updated TEXT NOT NULL,
                ttl INTEGER  -- Seconds until expiration, NULL = no expiration
            );
            CREATE INDEX IF NOT EXISTS idx_memory_updated
                ON memory(updated DESC);

            -- Error log
            CREATE TABLE IF NOT EXISTS errors (
                error_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                error_type TEXT NOT NULL,
                message TEXT NOT NULL,
                traceback TEXT,
                context TEXT  -- JSON
            );
            CREATE INDEX IF NOT EXISTS idx_errors_timestamp
                ON errors(timestamp DESC);
        """)

        await self.db.commit()
        logger.info(f"State manager initialized: {self.db_path}")

    async def get_current_state(self) -> Optional[CurrentState]:
        """Get current state."""
        async with self.db.execute(
            "SELECT data FROM current_state WHERE id = 1"
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                data = json.loads(row['data'])
                # Reconstruct CurrentState
                return CurrentState(**data)
        return None

    async def update_current_state(self, state: CurrentState):
        """Update current state."""
        await self.db.execute("""
            INSERT OR REPLACE INTO current_state (id, timestamp, data)
            VALUES (1, ?, ?)
        """, (state.timestamp.isoformat(), json.dumps(state.to_dict())))
        await self.db.commit()

    async def record_cycle(
        self,
        observation: Observation,
        decision: Decision,
        results: List[Dict[str, Any]]
    ):
        """Record a complete consciousness cycle."""
        cycle = HistoricalCycle(
            cycle_id=decision.observation_id,  # Use observation ID
            timestamp=datetime.now(),
            observation=observation,
            decision=decision,
            actions_taken=decision.actions,
            results=results,
            duration_ms=0  # Could track this
        )

        await self.db.execute("""
            INSERT INTO cycles (
                cycle_id, timestamp, observation, decision,
                actions, results, duration_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            cycle.cycle_id,
            cycle.timestamp.isoformat(),
            json.dumps(asdict(cycle.observation)),
            json.dumps(asdict(cycle.decision)),
            json.dumps(cycle.actions_taken),
            json.dumps(cycle.results),
            cycle.duration_ms
        ))
        await self.db.commit()

    async def get_context(self, limit: int = 10) -> List[HistoricalCycle]:
        """Get recent history for context."""
        async with self.db.execute("""
            SELECT * FROM cycles
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_cycle(row) for row in rows]

    def _row_to_cycle(self, row) -> HistoricalCycle:
        """Convert database row to HistoricalCycle."""
        return HistoricalCycle(
            cycle_id=row['cycle_id'],
            timestamp=datetime.fromisoformat(row['timestamp']),
            observation=Observation(**json.loads(row['observation'])),
            decision=Decision(**json.loads(row['decision'])),
            actions_taken=json.loads(row['actions']),
            results=json.loads(row['results']),
            duration_ms=row['duration_ms']
        )

    async def record_error(self, error: Exception, context: Dict = None):
        """Record an error."""
        import traceback
        await self.db.execute("""
            INSERT INTO errors (timestamp, error_type, message, traceback, context)
            VALUES (?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            type(error).__name__,
            str(error),
            ''.join(traceback.format_tb(error.__traceback__)),
            json.dumps(context) if context else None
        ))
        await self.db.commit()

    async def flush(self):
        """Flush all pending writes."""
        await self.db.commit()

    async def close(self):
        """Close database connection."""
        if self.db:
            await self.db.close()
```

### 3.3 State Serialization Strategies

**Pattern**: Use JSON for human-readable, pickle for Python objects, SQLite for queryable state.

```python
import json
import pickle
from pathlib import Path
from typing import Any, Dict
from datetime import datetime

class SnapshotManager:
    """Manages periodic state snapshots."""

    def __init__(self, snapshot_dir: Path):
        self.snapshot_dir = snapshot_dir
        self.snapshot_dir.mkdir(exist_ok=True)

    async def create_snapshot(self, state: Dict[str, Any]):
        """Create a timestamped snapshot."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON snapshot (human-readable)
        json_path = self.snapshot_dir / f"snapshot_{timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump(state, f, indent=2, default=str)

        # Pickle snapshot (full fidelity)
        pickle_path = self.snapshot_dir / f"snapshot_{timestamp}.pkl"
        with open(pickle_path, 'wb') as f:
            pickle.dump(state, f)

        logger.info(f"Snapshot created: {timestamp}")
        return timestamp

    async def restore_snapshot(self, timestamp: str) -> Dict[str, Any]:
        """Restore from a snapshot."""
        pickle_path = self.snapshot_dir / f"snapshot_{timestamp}.pkl"

        if pickle_path.exists():
            with open(pickle_path, 'rb') as f:
                return pickle.load(f)
        else:
            # Fall back to JSON
            json_path = self.snapshot_dir / f"snapshot_{timestamp}.json"
            with open(json_path) as f:
                return json.load(f)

    async def list_snapshots(self) -> List[str]:
        """List available snapshots."""
        snapshots = []
        for path in self.snapshot_dir.glob("snapshot_*.pkl"):
            timestamp = path.stem.replace("snapshot_", "")
            snapshots.append(timestamp)
        return sorted(snapshots, reverse=True)
```

### 3.4 State Consistency Guarantees

**Pattern**: Use write-ahead logging and atomic updates.

```python
class ConsistentStateManager(StateManager):
    """State manager with consistency guarantees."""

    async def atomic_update(self, update_fn):
        """Perform atomic state update."""
        async with self.db.execute("BEGIN IMMEDIATE"):
            try:
                # Get current state
                state = await self.get_current_state()

                # Apply update
                new_state = update_fn(state)

                # Write new state
                await self.update_current_state(new_state)

                await self.db.commit()
                return new_state
            except Exception as e:
                await self.db.rollback()
                raise

    async def create_checkpoint(self) -> str:
        """Create a checkpoint for rollback."""
        checkpoint_id = f"checkpoint_{datetime.now().isoformat()}"

        # Backup current state
        async with self.db.execute(
            "SELECT * FROM current_state WHERE id = 1"
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                await self.db.execute("""
                    INSERT INTO checkpoints (checkpoint_id, timestamp, state_data)
                    VALUES (?, ?, ?)
                """, (checkpoint_id, datetime.now().isoformat(), row['data']))
                await self.db.commit()

        return checkpoint_id

    async def rollback_to_checkpoint(self, checkpoint_id: str):
        """Rollback to a previous checkpoint."""
        async with self.db.execute("""
            SELECT state_data FROM checkpoints
            WHERE checkpoint_id = ?
        """, (checkpoint_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                await self.db.execute("""
                    UPDATE current_state
                    SET data = ?, timestamp = ?
                    WHERE id = 1
                """, (row['state_data'], datetime.now().isoformat()))
                await self.db.commit()
                logger.info(f"Rolled back to checkpoint: {checkpoint_id}")
            else:
                raise ValueError(f"Checkpoint not found: {checkpoint_id}")
```

---

## 4. Process Management

### 4.1 Running as a Daemon (systemd/launchd)

**systemd** (Linux) configuration:

```ini
# /etc/systemd/system/consciousness.service
[Unit]
Description=AI Consciousness Orchestrator
After=network.target

[Service]
Type=simple
User=chris
WorkingDirectory=/Users/chris/Developer/stoffy
ExecStart=/usr/bin/python3 /Users/chris/Developer/stoffy/consciousness/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Environment
Environment="PYTHONUNBUFFERED=1"
Environment="LM_STUDIO_URL=http://localhost:1234/v1"

[Install]
WantedBy=multi-user.target
```

**launchd** (macOS) configuration:

```xml
<!-- ~/Library/LaunchAgents/com.stoffy.consciousness.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.stoffy.consciousness</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/Users/chris/Developer/stoffy/consciousness/main.py</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/chris/Developer/stoffy</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/Users/chris/Developer/stoffy/logs/consciousness.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/chris/Developer/stoffy/logs/consciousness.error.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONUNBUFFERED</key>
        <string>1</string>
        <key>LM_STUDIO_URL</key>
        <string>http://localhost:1234/v1</string>
    </dict>
</dict>
</plist>
```

### 4.2 Signal Handling (SIGTERM, SIGINT)

Already covered in section 2.3. Key points:
- Install handlers for `SIGTERM` (graceful shutdown) and `SIGINT` (Ctrl+C)
- Use `asyncio.Event` to coordinate shutdown
- Clean up resources in shutdown handler

### 4.3 Child Process Management for Claude Code

**Pattern**: Spawn child processes with monitoring and timeout.

```python
import asyncio
from typing import Optional, List, Dict
from dataclasses import dataclass

@dataclass
class ProcessResult:
    """Result of a process execution."""
    returncode: int
    stdout: str
    stderr: str
    duration_ms: float
    timed_out: bool = False

class ProcessExecutor:
    """Manages child process execution with monitoring."""

    def __init__(self, max_concurrent: int = 3):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_processes: Dict[int, asyncio.subprocess.Process] = {}

    async def execute(
        self,
        command: List[str],
        cwd: str = None,
        env: Dict[str, str] = None,
        timeout: float = 300,
        capture_output: bool = True
    ) -> ProcessResult:
        """Execute a command with timeout and monitoring."""

        async with self.semaphore:  # Limit concurrency
            start_time = asyncio.get_event_loop().time()

            try:
                # Create process
                if capture_output:
                    process = await asyncio.create_subprocess_exec(
                        *command,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd=cwd,
                        env=env
                    )
                else:
                    process = await asyncio.create_subprocess_exec(
                        *command,
                        cwd=cwd,
                        env=env
                    )

                self.active_processes[process.pid] = process
                logger.info(f"Started process {process.pid}: {' '.join(command)}")

                # Wait with timeout
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=timeout
                    )

                    duration = (asyncio.get_event_loop().time() - start_time) * 1000

                    return ProcessResult(
                        returncode=process.returncode,
                        stdout=stdout.decode() if stdout else "",
                        stderr=stderr.decode() if stderr else "",
                        duration_ms=duration,
                        timed_out=False
                    )

                except asyncio.TimeoutError:
                    # Timeout - kill process
                    logger.warning(f"Process {process.pid} timed out, killing")
                    process.kill()
                    await process.wait()

                    duration = (asyncio.get_event_loop().time() - start_time) * 1000

                    return ProcessResult(
                        returncode=-1,
                        stdout="",
                        stderr="Process timed out",
                        duration_ms=duration,
                        timed_out=True
                    )

            finally:
                # Clean up
                if process.pid in self.active_processes:
                    del self.active_processes[process.pid]

    async def kill_all(self):
        """Kill all active processes."""
        for pid, process in list(self.active_processes.items()):
            logger.info(f"Killing process {pid}")
            process.kill()
            await process.wait()


# Usage for Claude Code execution
class ClaudeCodeExecutor:
    """Executes Claude Code commands."""

    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.executor = ProcessExecutor(max_concurrent=2)

    async def run_task(self, task_description: str) -> ProcessResult:
        """Run a Claude Code task."""
        command = [
            "claude",  # Assuming 'claude' CLI is in PATH
            "code",
            "--task", task_description,
            "--repo", self.repo_path
        ]

        result = await self.executor.execute(
            command,
            cwd=self.repo_path,
            timeout=600  # 10 minutes
        )

        if result.returncode == 0:
            logger.info(f"Claude Code task completed successfully")
        else:
            logger.error(f"Claude Code task failed: {result.stderr}")

        return result

    async def shutdown(self):
        """Shutdown executor."""
        await self.executor.kill_all()
```

### 4.4 Health Checks and Self-Monitoring

**Pattern**: Periodic health checks with auto-recovery.

```python
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Callable, Awaitable

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"

@dataclass
class HealthCheck:
    name: str
    check_fn: Callable[[], Awaitable[bool]]
    critical: bool = False

class HealthMonitor:
    """Monitors system health and triggers recovery."""

    def __init__(self, interval: float = 60.0):
        self.interval = interval
        self.checks: List[HealthCheck] = []
        self.status = HealthStatus.HEALTHY
        self.running = False

    def register_check(
        self,
        name: str,
        check_fn: Callable[[], Awaitable[bool]],
        critical: bool = False
    ):
        """Register a health check."""
        self.checks.append(HealthCheck(name, check_fn, critical))

    async def run(self):
        """Run health checks periodically."""
        self.running = True

        while self.running:
            try:
                await self.perform_checks()
            except Exception as e:
                logger.exception(f"Health check error: {e}")

            await asyncio.sleep(self.interval)

    async def perform_checks(self):
        """Perform all health checks."""
        results = {}

        for check in self.checks:
            try:
                result = await check.check_fn()
                results[check.name] = result

                if not result:
                    if check.critical:
                        self.status = HealthStatus.CRITICAL
                        logger.error(f"Critical health check failed: {check.name}")
                    else:
                        self.status = HealthStatus.DEGRADED
                        logger.warning(f"Health check failed: {check.name}")
            except Exception as e:
                logger.exception(f"Health check {check.name} threw exception: {e}")
                results[check.name] = False

        # All passed
        if all(results.values()):
            self.status = HealthStatus.HEALTHY

        return results


# Integration with orchestrator
class ConsciousnessOrchestrator:
    async def setup(self):
        # ... other setup

        self.health_monitor = HealthMonitor(interval=30.0)

        # Register checks
        self.health_monitor.register_check(
            "lm_studio_connection",
            self._check_lm_studio,
            critical=True
        )

        self.health_monitor.register_check(
            "database_connection",
            self._check_database,
            critical=True
        )

        self.health_monitor.register_check(
            "disk_space",
            self._check_disk_space,
            critical=False
        )

    async def _check_lm_studio(self) -> bool:
        """Check LM Studio is responsive."""
        try:
            # Try to list models
            response = await self.reasoner.client.models.list()
            return True
        except Exception as e:
            logger.error(f"LM Studio check failed: {e}")
            return False

    async def _check_database(self) -> bool:
        """Check database is accessible."""
        try:
            await self.state_manager.db.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database check failed: {e}")
            return False

    async def _check_disk_space(self) -> bool:
        """Check adequate disk space."""
        import shutil
        stat = shutil.disk_usage(self.config.repo_path)
        free_gb = stat.free / (1024**3)
        return free_gb > 1.0  # At least 1GB free
```

---

## 5. Code Organization

### 5.1 Recommended Project Structure

```
consciousness/
├── __init__.py
├── main.py                    # Entry point
├── config.py                  # Configuration dataclasses
├── orchestrator.py            # Main ConsciousnessOrchestrator class
│
├── monitors/
│   ├── __init__.py
│   ├── base.py                # BaseMonitor abstract class
│   ├── file_watcher.py        # File system monitoring
│   ├── process_monitor.py     # Process monitoring
│   └── git_hooks.py           # Git hook monitoring
│
├── reasoner/
│   ├── __init__.py
│   ├── llm_client.py          # LM Studio API client
│   ├── prompt_builder.py      # Prompt construction
│   └── decision_maker.py      # Decision logic
│
├── executor/
│   ├── __init__.py
│   ├── base.py                # BaseExecutor
│   ├── claude_code.py         # Claude Code integration
│   ├── git_operations.py      # Git commands
│   └── file_operations.py     # File I/O
│
├── state/
│   ├── __init__.py
│   ├── manager.py             # StateManager (SQLite)
│   ├── models.py              # State dataclasses
│   └── snapshots.py           # Snapshot management
│
├── utils/
│   ├── __init__.py
│   ├── logging.py             # Structured logging setup
│   ├── tasks.py               # Task management utilities
│   └── signals.py             # Signal handling
│
└── tests/
    ├── __init__.py
    ├── test_orchestrator.py
    ├── test_state_manager.py
    ├── test_monitors.py
    └── fixtures/
        └── test_config.json
```

### 5.2 Module Responsibilities

```python
# Clear separation of concerns

# monitors/ - OBSERVE the environment
# - File system changes (watchdog)
# - Process events (ps/top parsing)
# - Git hooks (post-commit, post-checkout)
# Output: Observation objects -> event queue

# reasoner/ - REASON about observations
# - Format observations into prompts
# - Call LM Studio API
# - Parse responses into Decision objects
# Output: Decision objects

# executor/ - ACT on decisions
# - Execute shell commands
# - Spawn Claude Code processes
# - Perform file operations
# Output: Result objects

# state/ - PERSIST everything
# - SQLite for structured data
# - JSON for snapshots
# - Ensure consistency and recovery
```

### 5.3 Interface Definitions

```python
# Base interfaces for extension

from abc import ABC, abstractmethod
from typing import List, Dict, Any
import asyncio

# monitors/base.py
class BaseMonitor(ABC):
    @abstractmethod
    async def start(self):
        """Start monitoring."""
        pass

    @abstractmethod
    async def stop(self):
        """Stop monitoring."""
        pass

    @abstractmethod
    async def emit_event(self, observation: Observation):
        """Emit an observation."""
        pass


# reasoner/base.py
class BaseReasoner(ABC):
    @abstractmethod
    async def analyze(
        self,
        observation: Observation,
        context: List[HistoricalCycle]
    ) -> Decision:
        """Analyze observation and make decision."""
        pass


# executor/base.py
class BaseExecutor(ABC):
    @abstractmethod
    async def execute(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute actions and return results."""
        pass
```

### 5.4 Testing Strategies

```python
# tests/test_orchestrator.py
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from consciousness.orchestrator import ConsciousnessOrchestrator
from consciousness.models import Observation

@pytest.fixture
async def orchestrator():
    """Create orchestrator with mocked dependencies."""
    with patch('consciousness.config.ConsciousnessConfig.from_file') as mock_config:
        mock_config.return_value = Mock(
            repo_path="/tmp/test_repo",
            state_db_path="/tmp/test.db",
            # ... other config
        )

        orch = ConsciousnessOrchestrator("fake_config.json")

        # Mock components
        orch.state_manager = AsyncMock()
        orch.reasoner = AsyncMock()
        orch.executor = AsyncMock()

        yield orch

        # Cleanup
        await orch.shutdown()


@pytest.mark.asyncio
async def test_main_loop_processes_observation(orchestrator):
    """Test that main loop processes observations."""

    # Setup mock observation
    obs = Observation(
        timestamp=datetime.now(),
        source="test",
        event_type="test_event",
        data={"key": "value"}
    )

    # Put observation in queue
    await orchestrator.event_queue.put(obs)

    # Mock decision
    decision = Mock(actions=[{"type": "log", "message": "test"}])
    orchestrator.reasoner.analyze.return_value = decision

    # Mock executor results
    orchestrator.executor.execute.return_value = [{"status": "success"}]

    # Run one loop iteration
    orchestrator.running = True
    loop_task = asyncio.create_task(orchestrator.main_loop())

    # Wait briefly
    await asyncio.sleep(0.5)

    # Stop loop
    orchestrator.running = False
    await loop_task

    # Verify calls
    orchestrator.reasoner.analyze.assert_called_once()
    orchestrator.executor.execute.assert_called_once()
    orchestrator.state_manager.record_cycle.assert_called_once()


# tests/test_state_manager.py
import pytest
import aiosqlite
from pathlib import Path
from consciousness.state.manager import StateManager

@pytest.fixture
async def state_manager(tmp_path):
    """Create temporary state manager."""
    db_path = tmp_path / "test.db"
    sm = StateManager(db_path)
    await sm.initialize()
    yield sm
    await sm.close()


@pytest.mark.asyncio
async def test_record_and_retrieve_cycle(state_manager):
    """Test recording and retrieving cycles."""

    obs = Observation(
        timestamp=datetime.now(),
        source="test",
        event_type="test",
        data={}
    )

    decision = Decision(
        timestamp=datetime.now(),
        observation_id="test-123",
        reasoning="Test reasoning",
        actions=[],
        confidence=0.9
    )

    # Record
    await state_manager.record_cycle(obs, decision, [])

    # Retrieve
    history = await state_manager.get_context(limit=1)

    assert len(history) == 1
    assert history[0].cycle_id == "test-123"
```

---

## 6. Key Libraries

### 6.1 openai (for LM Studio)

```bash
pip install openai
```

```python
from openai import AsyncOpenAI
from typing import List, Dict, Any

class LMStudioClient:
    """Async client for LM Studio API."""

    def __init__(self, base_url: str = "http://localhost:1234/v1"):
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key="lm-studio"  # Not validated
        )

    async def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2048,
        temperature: float = 0.7
    ) -> str:
        """Generate completion."""
        response = await self.client.chat.completions.create(
            model="local-model",
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.choices[0].message.content

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2048
    ):
        """Generate streaming completion."""
        stream = await self.client.chat.completions.create(
            model="local-model",
            messages=messages,
            max_tokens=max_tokens,
            stream=True
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
```

### 6.2 watchdog/watchfiles (file monitoring)

**watchdog** is more mature, **watchfiles** is faster (Rust-based).

```bash
pip install watchdog
# or
pip install watchfiles
```

Already covered in section 1.3.

### 6.3 psutil (process monitoring)

```bash
pip install psutil
```

```python
import psutil
from typing import List, Dict

class ProcessMonitor:
    """Cross-platform process monitoring."""

    def get_process_info(self, pid: int) -> Dict:
        """Get information about a process."""
        try:
            proc = psutil.Process(pid)
            return {
                "pid": proc.pid,
                "name": proc.name(),
                "status": proc.status(),
                "cpu_percent": proc.cpu_percent(interval=0.1),
                "memory_mb": proc.memory_info().rss / 1024 / 1024,
                "create_time": proc.create_time(),
                "num_threads": proc.num_threads()
            }
        except psutil.NoSuchProcess:
            return None

    def list_processes(self, name_filter: str = None) -> List[Dict]:
        """List all processes, optionally filtered by name."""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'status']):
            try:
                if name_filter and name_filter not in proc.info['name']:
                    continue
                processes.append(self.get_process_info(proc.info['pid']))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return processes
```

### 6.4 structlog (structured logging)

```bash
pip install structlog
```

```python
import structlog
import logging
from pathlib import Path

def setup_logging(log_path: Path, log_level: str = "INFO"):
    """Configure structured logging."""

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if log_level == "DEBUG"
                else structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(
            file=open(log_path, 'a')
        ),
        cache_logger_on_first_use=True,
    )

    # Get logger
    logger = structlog.get_logger()
    return logger


# Usage
logger = setup_logging(Path("consciousness.log"), "INFO")

logger.info("consciousness_started", repo_path="/Users/chris/Developer/stoffy")
logger.warning("high_cpu_usage", cpu_percent=95.2, process="lm-studio")
logger.error("llm_timeout", timeout_seconds=30, observation_id="obs-123")
```

### 6.5 aiosqlite (async SQLite)

```bash
pip install aiosqlite
```

Already covered extensively in section 3.

---

## 7. Complete Implementation Example

See the comprehensive code samples throughout sections 1-6. Here's a minimal runnable example:

```python
# main.py
import asyncio
import signal
from pathlib import Path
from consciousness.orchestrator import ConsciousnessOrchestrator
from consciousness.utils.logging import setup_logging

async def main():
    """Entry point."""
    # Setup logging
    logger = setup_logging(Path("./logs/consciousness.log"), "INFO")
    logger.info("Starting consciousness orchestrator")

    # Create orchestrator
    orch = ConsciousnessOrchestrator("config.json")

    # Setup signal handlers
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig,
            lambda: asyncio.create_task(orch.shutdown())
        )

    try:
        # Initialize
        await orch.setup()

        # Run
        await orch.start()

    except Exception as e:
        logger.exception("Fatal error", error=str(e))
        await orch.shutdown()
        raise


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 8. Deployment and Operations

### 8.1 Installation and Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python3 -m consciousness.state.manager --init --db ./data/consciousness.db

# Test configuration
python3 -m consciousness.config --validate config.json

# Run in foreground (testing)
python3 main.py

# Install as service (macOS)
cp com.stoffy.consciousness.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.stoffy.consciousness.plist

# Check status
launchctl list | grep consciousness

# View logs
tail -f ~/Library/Logs/consciousness.log
```

### 8.2 Monitoring and Observability

```python
# Export metrics for monitoring
class MetricsExporter:
    """Export metrics for Prometheus/other systems."""

    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager

    async def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return {
            "cycles_total": await self._count_cycles(),
            "errors_24h": await self._count_recent_errors(),
            "avg_cycle_duration_ms": await self._avg_cycle_duration(),
            "pending_actions": await self._count_pending_actions(),
            "last_heartbeat": await self._get_last_heartbeat()
        }

    async def _count_cycles(self) -> int:
        async with self.state_manager.db.execute(
            "SELECT COUNT(*) as count FROM cycles"
        ) as cursor:
            row = await cursor.fetchone()
            return row['count']

    # ... other metric methods
```

### 8.3 Backup and Recovery

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup database
cp ./data/consciousness.db "$BACKUP_DIR/consciousness_$DATE.db"

# Backup logs
tar -czf "$BACKUP_DIR/logs_$DATE.tar.gz" ./logs/

# Clean old backups (keep last 7 days)
find "$BACKUP_DIR" -name "*.db" -mtime +7 -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete

echo "Backup complete: $DATE"
```

### 8.4 Performance Tuning

```python
# Optimize for production

# 1. Connection pooling for external services
# 2. Batch database writes
# 3. Adjust queue sizes based on load
# 4. Monitor memory usage
# 5. Profile async tasks

import cProfile
import pstats

async def profile_main_loop():
    """Profile the main loop."""
    profiler = cProfile.Profile()
    profiler.enable()

    # Run main loop for fixed duration
    orchestrator = ConsciousnessOrchestrator("config.json")
    await orchestrator.setup()

    task = asyncio.create_task(orchestrator.start())
    await asyncio.sleep(60)  # Profile for 1 minute
    await orchestrator.shutdown()

    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)
```

---

## Summary and Key Takeaways

### 1. Architecture Principles

- **Component Separation**: Monitor, Reasoner, Executor, State Manager
- **Async-First**: Use `asyncio` for all I/O-bound operations
- **Event-Driven**: Central event queue for loose coupling
- **Persistent State**: SQLite for reliability and recovery

### 2. Critical Patterns

- **Graceful Shutdown**: Signal handlers + asyncio.Event
- **Error Boundaries**: Task managers with exception handling
- **State Consistency**: Atomic updates with rollback capability
- **Process Monitoring**: Health checks with auto-recovery

### 3. Production Readiness

- Run as daemon (systemd/launchd)
- Structured logging (structlog)
- Metrics export for monitoring
- Automated backups
- Performance profiling

### 4. Key Libraries

| Library | Purpose | Why |
|---------|---------|-----|
| `openai` | LM Studio API | Official, async support |
| `watchdog` | File monitoring | Mature, cross-platform |
| `psutil` | Process monitoring | Cross-platform, comprehensive |
| `aiosqlite` | Async SQLite | ACID guarantees, embedded |
| `structlog` | Logging | Structured, async-compatible |

### 5. Next Steps

1. Implement monitors (file, process, git)
2. Build reasoner (LLM integration)
3. Create executor (Claude Code wrapper)
4. Test end-to-end cycle
5. Deploy as daemon
6. Monitor and iterate

---

## References

### Python Async Documentation
- [asyncio documentation](https://docs.python.org/3/library/asyncio.html)
- [PEP 492 - Coroutines with async and await](https://peps.python.org/pep-0492/)

### Libraries
- [openai-python](https://github.com/openai/openai-python)
- [watchdog](https://github.com/gorakhargosh/watchdog)
- [psutil](https://github.com/giampaolo/psutil)
- [aiosqlite](https://github.com/omnilib/aiosqlite)
- [structlog](https://www.structlog.org/)

### Related Research
- `/docs/consciousness-research/01-lm-studio-api.md`
- `/docs/consciousness-research/02-file-system-monitoring.md`
- `/docs/consciousness-research/03-process-monitoring.md`
- `/docs/consciousness-research/04-self-referential-ai.md`

---

*Research compiled: 2026-01-04*
*Status: Comprehensive implementation guide*
*Ready for: Production implementation*
