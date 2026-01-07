"""
Fallback System - Complete fallback orchestration.

This is the main integration module that ties all fallback components together:
- LM Studio detection and monitoring
- Fallback routing between backends
- Gemini consciousness for thinking
- Task intent classification
- Autonomous execution
- Consciousness forwarding
- Response synthesis

Provides seamless degradation from LM Studio to Claude Code + Gemini.
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable

import structlog

from .lm_studio_detector import (
    LMStudioDetector,
    LMStudioStatus,
    LMStudioHealth,
    DetectorConfig,
)
from .fallback_router import (
    FallbackRouter,
    FallbackMode,
    BackendType,
    RouteDecision,
    RouterConfig,
)
from .gemini_consciousness import (
    GeminiConsciousness,
    GeminiConfig,
    ConsciousnessThought,
)
from .task_intent import (
    IntentClassifier,
    TaskIntent,
    IntentType,
    Urgency,
)
from .autonomous_executor import (
    AutonomousExecutor,
    ExecutionResult,
    ExecutorConfig,
)
from .consciousness_forwarder import (
    ConsciousnessForwarder,
    ForwardedDecision,
)
from .response_synthesizer import (
    ResponseSynthesizer,
    SynthesizedResponse,
    SynthesizerConfig,
)

logger = structlog.get_logger(__name__)


@dataclass
class FallbackConfig:
    """
    Configuration for the complete fallback system.

    Combines configuration for all sub-components.
    """
    # Mode settings
    enabled: bool = True
    prefer_lm_studio: bool = True
    check_interval_seconds: float = 30.0

    # LM Studio settings
    lm_studio_url: str = "http://localhost:1234/v1"
    lm_studio_timeout: float = 5.0
    lm_studio_retry_count: int = 2

    # Gemini settings
    gemini_model: str = "gemini-1.5-flash"
    gemini_timeout: float = 60.0
    gemini_enabled: bool = True

    # Execution settings
    claude_timeout: float = 120.0
    auto_execute_threshold: float = 0.8

    # Behavior settings
    show_mode_changes: bool = True
    log_consciousness_thoughts: bool = False
    sign_off: str = "- Stoffy"


@dataclass
class FallbackResponse:
    """
    Response from the fallback system.

    Contains all information about how a request was processed.
    """
    mode: FallbackMode
    response: str
    thought: Optional[ConsciousnessThought]
    execution_result: Optional[ExecutionResult]
    intent: TaskIntent
    processing_time: float
    success: bool = True
    route_decision: Optional[RouteDecision] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "mode": self.mode.value,
            "response": self.response[:1000] if self.response else "",
            "thought": self.thought.to_dict() if self.thought else None,
            "execution_result": self.execution_result.to_dict() if self.execution_result else None,
            "intent": self.intent.to_dict(),
            "processing_time": self.processing_time,
            "success": self.success,
            "route_decision": self.route_decision.to_dict() if self.route_decision else None,
            "metadata": self.metadata,
        }


class FallbackSystem:
    """
    Complete fallback system that provides seamless degradation
    from LM Studio to Claude Code + Gemini.

    This is the main integration class that orchestrates:
    1. Detection of LM Studio availability
    2. Routing to appropriate backends
    3. Consciousness thinking (via LM Studio or Gemini)
    4. Intent classification
    5. Task execution
    6. Response synthesis

    Usage:
        system = FallbackSystem(working_dir=Path.cwd())
        await system.initialize()

        response = await system.process_user_input("Hey Stoffy, run the tests")

        await system.shutdown()
    """

    def __init__(
        self,
        working_dir: Path,
        config: Optional[FallbackConfig] = None,
        on_mode_change: Optional[Callable[[FallbackMode, FallbackMode], Any]] = None,
    ):
        """
        Initialize the fallback system.

        Args:
            working_dir: Working directory for execution
            config: System configuration
            on_mode_change: Callback when mode changes
        """
        self.working_dir = Path(working_dir).resolve()
        self.config = config or FallbackConfig()
        self.on_mode_change = on_mode_change

        # Initialize components
        self.detector = LMStudioDetector(
            config=DetectorConfig(
                base_url=self.config.lm_studio_url,
                check_interval_seconds=self.config.check_interval_seconds,
                timeout_seconds=self.config.lm_studio_timeout,
            ),
            on_status_change=self._on_lm_studio_status_change,
        )

        self.router = FallbackRouter(
            config=RouterConfig(
                lm_studio_url=self.config.lm_studio_url,
                prefer_lm_studio=self.config.prefer_lm_studio,
                check_interval_seconds=self.config.check_interval_seconds,
            ),
            detector=self.detector,
            on_mode_change=self._on_router_mode_change,
        )

        self.gemini = GeminiConsciousness(
            config=GeminiConfig(
                model=self.config.gemini_model,
                timeout_seconds=self.config.gemini_timeout,
            )
        )

        self.intent_classifier = IntentClassifier()

        self.executor = AutonomousExecutor(
            working_dir=self.working_dir,
            config=ExecutorConfig(
                claude_timeout=int(self.config.claude_timeout),
            ),
        )

        self.forwarder = ConsciousnessForwarder(
            detector=self.detector,
            gemini=self.gemini,
        )

        self.synthesizer = ResponseSynthesizer(
            config=SynthesizerConfig(
                sign_off=self.config.sign_off,
            )
        )

        # State
        self._initialized = False
        self._mode = FallbackMode.PRIMARY

        # Statistics
        self._request_count = 0
        self._primary_count = 0
        self._fallback_count = 0
        self._execution_count = 0
        self._error_count = 0
        self._start_time: Optional[datetime] = None

    async def initialize(self) -> None:
        """
        Initialize the system and detect initial mode.

        This should be called before processing any requests.
        """
        if self._initialized:
            return

        logger.info("fallback_system.initializing")
        self._start_time = datetime.now(timezone.utc)

        try:
            # Initialize router (which initializes detector)
            await self.router.initialize()

            # Initialize gemini
            if self.config.gemini_enabled:
                await self.gemini.initialize()

            # Initialize executor
            await self.executor.initialize()

            # Initialize forwarder
            await self.forwarder.initialize()

            self._mode = self.router.mode
            self._initialized = True

            logger.info(
                "fallback_system.initialized",
                mode=self._mode.value,
                lm_studio_available=self.detector.is_available,
                gemini_available=self.gemini.is_available(),
            )

        except Exception as e:
            logger.error(f"fallback_system.init_error: {e}")
            # Start in fallback mode if initialization fails
            self._mode = FallbackMode.HYBRID
            self._initialized = True

    async def shutdown(self) -> None:
        """Clean shutdown of all components."""
        logger.info("fallback_system.shutting_down")

        try:
            await self.router.shutdown()
        except Exception as e:
            logger.warning(f"fallback_system.router_shutdown_error: {e}")

        stats = self.get_status()
        logger.info("fallback_system.shutdown_complete", statistics=stats.get("statistics"))

    async def process_user_input(self, message: str) -> FallbackResponse:
        """
        Main entry point: process user input through the fallback system.

        This method:
        1. Classifies the intent of the message
        2. Routes to appropriate backend(s)
        3. Generates consciousness thought if needed
        4. Executes action if needed
        5. Synthesizes response

        Args:
            message: User input message

        Returns:
            FallbackResponse with complete processing results
        """
        if not self._initialized:
            await self.initialize()

        start_time = time.time()
        self._request_count += 1

        try:
            # 1. Classify intent
            intent = self.intent_classifier.classify(message)

            logger.debug(
                "fallback_system.intent_classified",
                intent=intent.intent_type.value,
                urgency=intent.urgency.value,
                confidence=intent.confidence,
            )

            # 2. Get routing decision
            route = self.router.route_request(
                is_consciousness=intent.requires_thinking,
            )

            # Track statistics
            if route.mode == FallbackMode.PRIMARY:
                self._primary_count += 1
            else:
                self._fallback_count += 1

            # 3. Process based on intent type
            thought: Optional[ConsciousnessThought] = None
            execution_result: Optional[ExecutionResult] = None

            if intent.requires_thinking:
                # Get consciousness thought
                decision = await self.forwarder.think(
                    observations=message,
                    context={
                        "intent": intent.to_dict(),
                        "mode": self._mode.value,
                    },
                    force_gemini=(route.mode != FallbackMode.PRIMARY),
                )

                # Convert decision to thought
                thought = ConsciousnessThought(
                    observation=decision.observation_summary,
                    reasoning=decision.reasoning,
                    conclusion=decision.decision,
                    confidence=decision.confidence,
                    suggested_action=decision.expected_outcome,
                    raw_response=decision.raw_response,
                )

                if self.config.log_consciousness_thoughts:
                    logger.debug(
                        "fallback_system.thought",
                        conclusion=thought.conclusion,
                        confidence=thought.confidence,
                    )

            if intent.requires_execution:
                # Execute the task
                self._execution_count += 1

                if thought and thought.suggested_action:
                    execution_result = await self.executor.execute_from_thought(
                        thought, intent
                    )
                else:
                    # Direct execution without thought
                    execution_result = await self.executor.execute_claude_code(message)

            # 4. Synthesize response
            processing_time = time.time() - start_time

            synthesized = self.synthesizer.synthesize(
                mode=self._mode,
                thought=thought,
                execution_result=execution_result,
                intent=intent,
                processing_time=processing_time,
            )

            return FallbackResponse(
                mode=self._mode,
                response=synthesized.response,
                thought=thought,
                execution_result=execution_result,
                intent=intent,
                processing_time=processing_time,
                success=synthesized.success,
                route_decision=route,
            )

        except Exception as e:
            self._error_count += 1
            processing_time = time.time() - start_time

            logger.error(f"fallback_system.process_error: {e}")

            # Return error response
            error_synthesized = self.synthesizer.format_error(
                error=str(e),
                mode=self._mode,
            )

            return FallbackResponse(
                mode=self._mode,
                response=error_synthesized.response,
                thought=None,
                execution_result=None,
                intent=self.intent_classifier.classify(message),
                processing_time=processing_time,
                success=False,
                metadata={"error": str(e)},
            )

    async def process_observation(
        self,
        observations: str,
        context: Optional[Dict[str, Any]] = None,
        git_status: Optional[str] = None,
        learned_patterns: Optional[List[str]] = None,
    ) -> FallbackResponse:
        """
        Process file/git observations (for daemon integration).

        This is similar to process_user_input but optimized for
        automated observation processing.

        Args:
            observations: Formatted observations
            context: Additional context
            git_status: Git status information
            learned_patterns: Patterns from learning

        Returns:
            FallbackResponse
        """
        if not self._initialized:
            await self.initialize()

        start_time = time.time()
        self._request_count += 1

        try:
            # Get consciousness thought
            decision = await self.forwarder.think(
                observations=observations,
                context=context,
                git_status=git_status,
                learned_patterns=learned_patterns,
            )

            # Convert to thought
            thought = ConsciousnessThought(
                observation=decision.observation_summary,
                reasoning=decision.reasoning,
                conclusion=decision.conclusion,
                confidence=decision.confidence,
                suggested_action=decision.expected_outcome,
                raw_response=decision.raw_response,
            )

            # Execute if decided
            execution_result: Optional[ExecutionResult] = None

            if decision.decision == "act" and decision.confidence >= self.config.auto_execute_threshold:
                self._execution_count += 1
                execution_result = await self.executor.execute_from_thought(thought)

            # Classify intent (for response synthesis)
            intent = TaskIntent(
                intent_type=IntentType.ANALYZE,
                urgency=Urgency.NORMAL,
                confidence=decision.confidence,
                keywords=[],
                requires_execution=(decision.decision == "act"),
                requires_thinking=True,
                description="Observation processing",
            )

            processing_time = time.time() - start_time

            synthesized = self.synthesizer.synthesize(
                mode=self._mode,
                thought=thought,
                execution_result=execution_result,
                intent=intent,
                processing_time=processing_time,
            )

            return FallbackResponse(
                mode=self._mode,
                response=synthesized.response,
                thought=thought,
                execution_result=execution_result,
                intent=intent,
                processing_time=processing_time,
                success=synthesized.success,
            )

        except Exception as e:
            self._error_count += 1
            processing_time = time.time() - start_time

            logger.error(f"fallback_system.observation_error: {e}")

            return FallbackResponse(
                mode=self._mode,
                response=f"Error processing observation: {e}",
                thought=None,
                execution_result=None,
                intent=TaskIntent(
                    intent_type=IntentType.ANALYZE,
                    urgency=Urgency.NORMAL,
                    confidence=0.0,
                    keywords=[],
                    requires_execution=False,
                    requires_thinking=True,
                    description="Error",
                ),
                processing_time=processing_time,
                success=False,
            )

    def _on_lm_studio_status_change(
        self,
        old_status: LMStudioStatus,
        new_status: LMStudioStatus,
    ) -> None:
        """Handle LM Studio status changes."""
        if self.config.show_mode_changes:
            logger.info(
                "fallback_system.lm_studio_status_changed",
                old=old_status.value,
                new=new_status.value,
            )

    async def _on_router_mode_change(
        self,
        old_mode: FallbackMode,
        new_mode: FallbackMode,
    ) -> None:
        """Handle router mode changes."""
        self._mode = new_mode

        if self.config.show_mode_changes:
            logger.info(
                "fallback_system.mode_changed",
                old=old_mode.value,
                new=new_mode.value,
            )

        if self.on_mode_change:
            try:
                result = self.on_mode_change(old_mode, new_mode)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.warning(f"fallback_system.mode_callback_error: {e}")

    def get_status(self) -> dict:
        """
        Get system status including mode and component health.

        Returns:
            Comprehensive status dictionary
        """
        uptime = None
        if self._start_time:
            uptime = (datetime.now(timezone.utc) - self._start_time).total_seconds()

        return {
            "initialized": self._initialized,
            "mode": self._mode.value,
            "uptime_seconds": uptime,
            "lm_studio": self.detector.get_status_summary(),
            "gemini": self.gemini.get_status(),
            "router": self.router.get_status(),
            "executor": self.executor.get_statistics(),
            "forwarder": self.forwarder.get_statistics(),
            "statistics": {
                "request_count": self._request_count,
                "primary_count": self._primary_count,
                "fallback_count": self._fallback_count,
                "execution_count": self._execution_count,
                "error_count": self._error_count,
                "fallback_rate": (
                    self._fallback_count / self._request_count
                    if self._request_count > 0 else 0.0
                ),
            },
        }

    @property
    def mode(self) -> FallbackMode:
        """Get current operating mode."""
        return self._mode

    @property
    def is_primary_mode(self) -> bool:
        """Check if using primary (LM Studio) mode."""
        return self._mode == FallbackMode.PRIMARY

    @property
    def is_fallback_mode(self) -> bool:
        """Check if using fallback mode."""
        return self._mode != FallbackMode.PRIMARY

    async def force_fallback(self) -> None:
        """Force switch to fallback mode."""
        await self.router.force_fallback_mode("Manually triggered")
        self._mode = self.router.mode

    async def force_primary(self) -> None:
        """Force switch to primary mode (if available)."""
        await self.router.force_primary_mode("Manually triggered")
        self._mode = self.router.mode


# Factory function for easy creation
def create_fallback_system(
    working_dir: Optional[Path] = None,
    config: Optional[FallbackConfig] = None,
) -> FallbackSystem:
    """
    Create a fallback system instance.

    Args:
        working_dir: Working directory (defaults to cwd)
        config: System configuration

    Returns:
        FallbackSystem instance
    """
    return FallbackSystem(
        working_dir=working_dir or Path.cwd(),
        config=config,
    )


if __name__ == "__main__":
    async def test():
        print("Testing Fallback System...")
        print("=" * 60)

        system = FallbackSystem(
            working_dir=Path.cwd(),
            config=FallbackConfig(
                show_mode_changes=True,
                log_consciousness_thoughts=True,
            ),
        )

        await system.initialize()

        print(f"\nInitial Status:")
        import json
        print(json.dumps(system.get_status(), indent=2, default=str))

        # Test user input processing
        test_messages = [
            "Hey Stoffy, what's the status of the project?",
            "Create a new file called test.txt",
            "Thanks for your help!",
        ]

        for msg in test_messages:
            print(f"\n{'=' * 60}")
            print(f"Processing: {msg}")
            response = await system.process_user_input(msg)
            print(f"\nMode: {response.mode.value}")
            print(f"Intent: {response.intent.intent_type.value}")
            print(f"Processing time: {response.processing_time:.2f}s")
            print(f"Success: {response.success}")
            print(f"\nResponse:\n{response.response[:500]}")

        await system.shutdown()

        print(f"\n{'=' * 60}")
        print("Test complete!")

    asyncio.run(test())
