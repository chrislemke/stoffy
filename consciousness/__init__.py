"""
Consciousness Orchestrator - FULLY AUTONOMOUS OIDA Loop Implementation

This package implements a FULLY AUTONOMOUS consciousness daemon that:
- OBSERVES: Watches file system AND git for changes
- INFERS: Uses LM Studio to interpret observations FREELY
- DECIDES: LLM decides autonomously (NOT limited to templates)
- ACTS: Executes ANY action type without confirmation
- LEARNS: Records outcomes and improves over time

The LLM has FULL AUTONOMY to:
- Generate any action that makes sense
- Write files directly
- Execute code (Python, Bash)
- Delegate to Claude Code for complex tasks
- Spawn Claude Flow swarms for research
- Think, debate, and research freely

Components:
- daemon.py: Autonomous orchestrator (ConsciousnessDaemon, AutonomousExecutor)
- watcher.py: File system observer (ConsciousnessWatcher)
- watcher_git.py: Git repository observer (GitWatcher)
- thinker.py: Autonomous LM Studio reasoning (ConsciousnessThinker)
- executor.py: Claude Code/Flow execution (ClaudeCodeExecutor)
- state.py: SQLite persistence (StateManager)
- config.py: Configuration management (ConsciousnessConfig)
- decision/engine.py: Autonomous decision engine (AutonomousEngine)
- learning/: Pattern learning from outcomes

Usage:
    # Fully autonomous mode (default)
    python -m consciousness run

    # Dry-run mode (observe and decide, but don't execute)
    python -m consciousness run --dry-run

    # Supervised mode (would ask for confirmation)
    python -m consciousness run --supervised

    # Check status
    python -m consciousness status
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
    CombinedWatcher,
    CombinedObservation,
    create_combined_watcher,
)

# Git watcher exports
from .watcher_git import (
    GitWatcher,
    GitStatus,
    GitFileChange,
    GitObservation,
    Commit,
    create_git_watcher,
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
    # Core executor classes
    ExpandedExecutor,
    ClaudeCodeExecutor,
    ExecutorPool,
    # Result and config
    ExecutionResult,
    ExecutionMode,
    ExecutionConfig,
    SwarmConfig,
    # Action types (aliased to avoid conflict with thinker.Action)
    ActionType as ExecutorActionType,
    Action as ExecutorAction,
    Priority as ExecutorPriority,
    # Convenience functions
    execute_claude,
    execute_action,
)

# Daemon exports
from .daemon import (
    ConsciousnessDaemon,
    AutonomousExecutor,
    setup_signal_handlers,
    run_autonomous_daemon,
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
    AutonomousEngine,
    EngineDecision,
    DecisionContext,
    create_engine,
)

# Learning exports
from .learning import (
    OutcomeTracker,
    Outcome,
    OutcomeType,
    PatternLearner,
    Pattern,
    PatternType,
    Suggestion,
)
from .learning.integration import (
    LearningIntegration,
    LearningConfig,
)

# Gemini Consciousness exports
from .gemini_consciousness import (
    GeminiConsciousness,
    ConsciousnessThought,
    quick_contemplate,
)

# Autonomous Executor with Consciousness exports
from .autonomous_executor import (
    AutonomousExecutorWithConsciousness,
    ExecutionResponse,
    process_user_message,
    think_then_act,
)

# Task intent exports
from .task_intent import (
    IntentType,
    Urgency,
    TaskIntent,
    IntentClassifier,
    classify_intent,
    is_task_request,
    extract_entities_from_message,
)

# Fallback router exports
from .fallback_router import (
    FallbackRouter,
    FallbackMode,
    FallbackConfig,
    LMStudioDetector,
    LMStudioStatus,
    create_router,
    route_thinking,
)

# Consciousness forwarder exports
from .consciousness_forwarder import (
    ConsciousnessForwarder,
    ConsciousnessGuidance,
    QuestionType,
    ForwarderConfig,
    GuidanceCache,
    ask_consciousness,
    get_quick_guidance,
)

# Fallback System exports (complete integration)
from .fallback_system import (
    FallbackSystem,
    FallbackSystemConfig,
    FallbackResponse,
    create_fallback_system,
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
    "CombinedWatcher",
    "CombinedObservation",
    "create_combined_watcher",
    # Git Watcher
    "GitWatcher",
    "GitStatus",
    "GitFileChange",
    "GitObservation",
    "Commit",
    "create_git_watcher",
    # Thinker
    "ConsciousnessThinker",
    "Decision",
    "DecisionType",
    "Action",
    "ActionType",
    "Priority",
    "quick_think",
    # Executor
    "ExpandedExecutor",
    "ClaudeCodeExecutor",
    "ExecutorPool",
    "ExecutionResult",
    "ExecutionMode",
    "ExecutionConfig",
    "SwarmConfig",
    "ExecutorActionType",
    "ExecutorAction",
    "ExecutorPriority",
    "execute_claude",
    "execute_action",
    # Daemon
    "ConsciousnessDaemon",
    "AutonomousExecutor",
    "setup_signal_handlers",
    "run_autonomous_daemon",
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
    "AutonomousEngine",
    "EngineDecision",
    "DecisionContext",
    "create_engine",
    # Learning
    "OutcomeTracker",
    "Outcome",
    "OutcomeType",
    "PatternLearner",
    "Pattern",
    "PatternType",
    "Suggestion",
    "LearningIntegration",
    "LearningConfig",
    # Gemini Consciousness
    "GeminiConsciousness",
    "ConsciousnessThought",
    "quick_contemplate",
    # Autonomous Executor with Consciousness
    "AutonomousExecutorWithConsciousness",
    "ExecutionResponse",
    "process_user_message",
    "think_then_act",
    # Task Intent
    "IntentType",
    "Urgency",
    "TaskIntent",
    "IntentClassifier",
    "classify_intent",
    "is_task_request",
    "extract_entities_from_message",
    # Fallback Router
    "FallbackRouter",
    "FallbackMode",
    "FallbackConfig",
    "LMStudioDetector",
    "LMStudioStatus",
    "create_router",
    "route_thinking",
    # Consciousness Forwarder
    "ConsciousnessForwarder",
    "ConsciousnessGuidance",
    "QuestionType",
    "ForwarderConfig",
    "GuidanceCache",
    "ask_consciousness",
    "get_quick_guidance",
    # Fallback System (complete integration)
    "FallbackSystem",
    "FallbackSystemConfig",
    "FallbackResponse",
    "create_fallback_system",
]
