"""
Fallback System - Graceful degradation when LM Studio is unavailable.

This package provides seamless fallback from LM Studio to Claude Code + Gemini
when the primary local LLM backend is unavailable.

Components:
- lm_studio_detector: Monitors LM Studio availability
- fallback_router: Routes requests to appropriate backends
- gemini_consciousness: Gemini-powered thinking/awareness
- task_intent: Classifies user intent from messages
- autonomous_executor: Executes tasks in fallback mode
- consciousness_forwarder: Forwards consciousness requests to fallback
- response_synthesizer: Combines results into coherent responses
- fallback_system: Main integration that ties everything together

Usage:
    from consciousness.fallback import FallbackSystem, FallbackConfig

    system = FallbackSystem(
        working_dir=Path.cwd(),
        config=FallbackConfig(prefer_lm_studio=True),
    )

    await system.initialize()
    response = await system.process_user_input("Hey Stoffy, run the tests")
    await system.shutdown()
"""

# Core system
from .fallback_system import (
    FallbackSystem,
    FallbackConfig,
    FallbackResponse,
    create_fallback_system,
)

# Router and detection
from .fallback_router import (
    FallbackRouter,
    FallbackMode,
    BackendType,
    RouteDecision,
    RouterConfig,
)

from .lm_studio_detector import (
    LMStudioDetector,
    LMStudioStatus,
    LMStudioHealth,
    DetectorConfig,
    check_lm_studio_available,
)

# Consciousness
from .gemini_consciousness import (
    GeminiConsciousness,
    GeminiConfig,
    ConsciousnessThought,
)

from .consciousness_forwarder import (
    ConsciousnessForwarder,
    ForwardedDecision,
)

# Intent and execution
from .task_intent import (
    IntentClassifier,
    TaskIntent,
    IntentType,
    Urgency,
    classify_message,
)

from .autonomous_executor import (
    AutonomousExecutor,
    ExecutionResult,
    ExecutorConfig,
)

# Response synthesis
from .response_synthesizer import (
    ResponseSynthesizer,
    SynthesizedResponse,
    SynthesizerConfig,
)


__all__ = [
    # Core system
    "FallbackSystem",
    "FallbackConfig",
    "FallbackResponse",
    "create_fallback_system",
    # Router
    "FallbackRouter",
    "FallbackMode",
    "BackendType",
    "RouteDecision",
    "RouterConfig",
    # Detection
    "LMStudioDetector",
    "LMStudioStatus",
    "LMStudioHealth",
    "DetectorConfig",
    "check_lm_studio_available",
    # Consciousness
    "GeminiConsciousness",
    "GeminiConfig",
    "ConsciousnessThought",
    "ConsciousnessForwarder",
    "ForwardedDecision",
    # Intent
    "IntentClassifier",
    "TaskIntent",
    "IntentType",
    "Urgency",
    "classify_message",
    # Execution
    "AutonomousExecutor",
    "ExecutionResult",
    "ExecutorConfig",
    # Synthesis
    "ResponseSynthesizer",
    "SynthesizedResponse",
    "SynthesizerConfig",
]
