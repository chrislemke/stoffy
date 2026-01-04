"""
Consciousness Orchestrator - Autonomous OIDA Loop Implementation

This package implements a consciousness daemon that:
- OBSERVES: Watches file system for changes (watcher.py)
- INFERS: Uses LM Studio to interpret observations (thinker.py)
- DECIDES: Determines if action is needed (confidence > 0.7)
- ACTS: Delegates tasks to Claude Code (executor.py)

Components:
- daemon.py: Main orchestrator (ConsciousnessDaemon)
- watcher.py: File system observer (ConsciousnessWatcher)
- thinker.py: LM Studio reasoning (ConsciousnessThinker)
- executor.py: Claude Code execution (ClaudeCodeExecutor)
- state.py: SQLite persistence (StateManager)
- config.py: Configuration management (ConsciousnessConfig)

Usage:
    python -m consciousness run
    python -m consciousness run --dry-run
    python -m consciousness status
    python -m consciousness check
"""

__version__ = "0.1.0"
__author__ = "Consciousness Hive Mind"

# Config exports
from .config import ConsciousnessConfig, load_config

# State exports
from .state import (
    ActionRecord,
    Event,
    EventType,
    StateManager,
    ThoughtRecord,
)

# Watcher exports
from .watcher import (
    ConsciousnessWatcher,
    FileChange,
    ChangeBatch,
    create_watcher,
)

# Thinker exports
from .thinker import (
    ConsciousnessThinker,
    Decision,
    DecisionType,
    Action,
    ActionType,
    Priority,
    quick_think,
)

# Executor exports
from .executor import (
    ClaudeCodeExecutor,
    ExecutionResult,
    ExecutionMode,
    SwarmConfig,
    ExecutorPool,
    execute_claude,
)

# Daemon exports
from .daemon import (
    ConsciousnessDaemon,
    setup_signal_handlers,
)

# Decision engine exports
from .decision import (
    # Categories
    ObservationCategory,
    CategorizedChanges,
    categorize_changes,
    categorize_single_change,
    # Actions
    ActionTemplate,
    ActionMatch,
    BUILT_IN_ACTIONS,
    match_actions,
    get_action_by_name,
    # Evaluator
    ActionEvaluator,
    EvaluationResult,
    MultiActionEvaluation,
    # Engine
    DecisionEngine,
    EngineDecision,
    DecisionContext,
)

__all__ = [
    # Version
    "__version__",
    # Config
    "ConsciousnessConfig",
    "load_config",
    # State
    "StateManager",
    "Event",
    "EventType",
    "ThoughtRecord",
    "ActionRecord",
    # Watcher
    "ConsciousnessWatcher",
    "FileChange",
    "ChangeBatch",
    "create_watcher",
    # Thinker
    "ConsciousnessThinker",
    "Decision",
    "DecisionType",
    "Action",
    "ActionType",
    "Priority",
    "quick_think",
    # Executor
    "ClaudeCodeExecutor",
    "ExecutionResult",
    "ExecutionMode",
    "SwarmConfig",
    "ExecutorPool",
    "execute_claude",
    # Daemon
    "ConsciousnessDaemon",
    "setup_signal_handlers",
    # Decision - Categories
    "ObservationCategory",
    "CategorizedChanges",
    "categorize_changes",
    "categorize_single_change",
    # Decision - Actions
    "ActionTemplate",
    "ActionMatch",
    "BUILT_IN_ACTIONS",
    "match_actions",
    "get_action_by_name",
    # Decision - Evaluator
    "ActionEvaluator",
    "EvaluationResult",
    "MultiActionEvaluation",
    # Decision - Engine
    "DecisionEngine",
    "EngineDecision",
    "DecisionContext",
]
