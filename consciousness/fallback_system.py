"""
Fallback System - Complete Orchestration for Graceful Degradation.

This is the main integration module that ties all existing fallback components
together into a unified system for seamless degradation from LM Studio to
Claude Code + Gemini.

Components Integrated:
- LMStudioDetector: Monitors LM Studio availability
- FallbackRouter: Routes requests to appropriate backends
- GeminiConsciousness: Gemini-powered thinking/awareness
- IntentClassifier: Classifies user intent from messages
- AutonomousExecutorWithConsciousness: Executes tasks with consciousness
- ConsciousnessForwarder: Forwards consciousness requests

Usage:
    system = FallbackSystem(working_dir=Path.cwd())
    await system.initialize()

    response = await system.process_user_input("Hey Stoffy, run the tests")

    await system.shutdown()
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable

import structlog

# Import existing components
from .fallback_router import (
    FallbackRouter,
    FallbackMode,
    FallbackConfig as RouterConfig,
    LMStudioDetector,
    LMStudioStatus,
)
from .gemini_consciousness import (
    GeminiConsciousness,
    ConsciousnessThought,
)
from .task_intent import (
    IntentClassifier,
    TaskIntent,
    IntentType,
    Urgency,
)
from .consciousness_forwarder import (
    ConsciousnessForwarder,
    ConsciousnessGuidance,
)
from .autonomous_executor import (
    AutonomousExecutorWithConsciousness,
    ExecutionResponse,
)
from .executor import (
    ExpandedExecutor,
    ExecutionResult,
    ExecutionConfig,
)

logger = structlog.get_logger(__name__)


@dataclass
class FallbackSystemConfig:
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
    lm_studio_model: str = "local-model"
    lm_studio_timeout: float = 5.0

    # Gemini settings
    gemini_model: Optional[str] = None  # Use CLI default
    gemini_timeout: float = 30.0
    gemini_enabled: bool = True

    # Execution settings
    claude_timeout: int = 300
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
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "mode": self.mode.value,
            "response": self.response[:1000] if self.response else "",
            "thought": self.thought.to_dict() if self.thought else None,
            "execution_result": {
                "success": self.execution_result.success,
                "output": self.execution_result.output[:500] if self.execution_result else "",
                "error": self.execution_result.error if self.execution_result else None,
            } if self.execution_result else None,
            "intent": {
                "type": self.intent.type.value,
                "confidence": self.intent.confidence,
                "urgency": self.intent.urgency.value,
            },
            "processing_time": self.processing_time,
            "success": self.success,
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
    """

    def __init__(
        self,
        working_dir: Path,
        config: Optional[FallbackSystemConfig] = None,
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
        self.config = config or FallbackSystemConfig()
        self.on_mode_change = on_mode_change

        # Initialize router config
        router_config = RouterConfig(
            lm_studio_url=self.config.lm_studio_url,
            lm_studio_model=self.config.lm_studio_model,
            connection_timeout=self.config.lm_studio_timeout,
            check_interval=self.config.check_interval_seconds,
            auto_execute_threshold=self.config.auto_execute_threshold,
            claude_timeout=self.config.claude_timeout,
        )

        # Initialize components
        self.router = FallbackRouter(
            working_dir=self.working_dir,
            config=router_config,
        )

        # Register mode change callback
        if self.on_mode_change:
            self.router.on_mode_change(self._handle_mode_change)

        self.gemini = GeminiConsciousness(
            model=self.config.gemini_model,
            timeout=self.config.gemini_timeout,
        )

        self.intent_classifier = IntentClassifier()

        self.executor = ExpandedExecutor(
            working_dir=self.working_dir,
            config=ExecutionConfig(
                claude_timeout=self.config.claude_timeout,
            ),
        )

        self.consciousness_executor = AutonomousExecutorWithConsciousness(
            working_dir=self.working_dir,
        )

        self.forwarder = ConsciousnessForwarder(
            working_dir=self.working_dir,
        )

        # State
        self._initialized = False
        self._mode: Optional[FallbackMode] = None

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
            # Get initial mode (this checks LM Studio availability)
            self._mode = await self.router.get_current_mode()
            self._initialized = True

            logger.info(
                "fallback_system.initialized",
                mode=self._mode.value,
                lm_studio_available=self.router.detector.status.available,
                gemini_available=self.gemini.is_available(),
            )

        except Exception as e:
            logger.error(f"fallback_system.init_error: {e}")
            # Start in fallback mode if initialization fails
            self._mode = FallbackMode.FALLBACK
            self._initialized = True

    async def shutdown(self) -> None:
        """Clean shutdown of all components."""
        logger.info("fallback_system.shutting_down")

        stats = self.get_status()
        logger.info("fallback_system.shutdown_complete", statistics=stats.get("statistics"))

    def _handle_mode_change(self, old_mode: FallbackMode, new_mode: FallbackMode) -> None:
        """Handle mode changes from router."""
        self._mode = new_mode

        if self.config.show_mode_changes:
            logger.info(
                "fallback_system.mode_changed",
                old=old_mode.value,
                new=new_mode.value,
            )

        if self.on_mode_change:
            try:
                self.on_mode_change(old_mode, new_mode)
            except Exception as e:
                logger.warning(f"fallback_system.mode_callback_error: {e}")

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
                intent=intent.type.value,
                urgency=intent.urgency.value,
                confidence=intent.confidence,
            )

            # 2. Get current mode
            mode = await self.router.get_current_mode()
            self._mode = mode

            # Track statistics
            if mode == FallbackMode.PRIMARY:
                self._primary_count += 1
            else:
                self._fallback_count += 1

            # 3. Process based on intent type and mode
            thought: Optional[ConsciousnessThought] = None
            execution_result: Optional[ExecutionResult] = None
            response_text = ""

            if intent.type == IntentType.TASK and intent.confidence >= 0.7:
                # Task request - use consciousness executor
                self._execution_count += 1

                exec_response = await self.consciousness_executor.process_message(message)

                if exec_response.thought:
                    thought = exec_response.thought

                if exec_response.execution_result:
                    execution_result = exec_response.execution_result
                    response_text = exec_response.execution_result.output

                if not response_text:
                    response_text = exec_response.response

            elif intent.type in (IntentType.QUESTION, IntentType.PHILOSOPHICAL, IntentType.META):
                # Analysis/thinking request
                if mode == FallbackMode.PRIMARY:
                    # Use router for thinking
                    decision = await self.router.route_thinking(
                        observations=message,
                        context={"intent": intent.type.value},
                    )
                    response_text = decision.reasoning
                else:
                    # Use Gemini for consciousness
                    thought = await self.gemini.contemplate(
                        message,
                        context={"intent": intent.type.value, "mode": mode.value},
                    )
                    response_text = thought.suggested_approach

                    if self.config.log_consciousness_thoughts:
                        logger.debug(
                            "fallback_system.thought",
                            understanding=thought.understanding[:100],
                            should_act=thought.should_act,
                            confidence=thought.confidence,
                        )

            else:
                # Conversational - route through forwarder for quick response
                guidance = await self.forwarder.get_guidance(message)
                response_text = guidance.guidance

            # Add sign-off
            if response_text and self.config.sign_off:
                response_text = response_text.strip() + f"\n\n{self.config.sign_off}"

            processing_time = time.time() - start_time

            return FallbackResponse(
                mode=mode,
                response=response_text,
                thought=thought,
                execution_result=execution_result,
                intent=intent,
                processing_time=processing_time,
                success=True,
            )

        except Exception as e:
            self._error_count += 1
            processing_time = time.time() - start_time

            logger.error(f"fallback_system.process_error: {e}")

            return FallbackResponse(
                mode=self._mode or FallbackMode.DEGRADED,
                response=f"I encountered an issue: {e}\n\n{self.config.sign_off}",
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
            # Route thinking through the router (handles mode selection)
            decision = await self.router.route_thinking(
                observations=observations,
                context=context,
                git_status=git_status,
                learned_patterns=learned_patterns,
            )

            # Convert decision to thought if we have Gemini thought
            thought = None
            if hasattr(decision, 'raw_response') and decision.raw_response:
                thought = ConsciousnessThought(
                    understanding=decision.observation_summary,
                    suggested_approach=decision.reasoning,
                    should_act=decision.decision.value == "act",
                    action_hint=decision.action.type.value if decision.action else None,
                    confidence=decision.confidence,
                    raw_response=decision.raw_response,
                )

            # Execute if decided
            execution_result: Optional[ExecutionResult] = None

            if decision.decision.value == "act" and decision.confidence >= self.config.auto_execute_threshold:
                self._execution_count += 1

                if decision.action:
                    from .executor import Action as ExecutorAction, ActionType as ExecutorActionType

                    action = ExecutorAction(
                        type=ExecutorActionType.CLAUDE_CODE,
                        details={"prompt": decision.action.description},
                    )
                    execution_result = await self.executor.execute(action)

            # Create a minimal intent for response
            intent = TaskIntent(
                type=IntentType.TASK if decision.decision.value == "act" else IntentType.QUESTION,
                confidence=decision.confidence,
                urgency=Urgency.MEDIUM,
                raw_message=observations[:100],
            )

            processing_time = time.time() - start_time

            response_text = decision.reasoning
            if execution_result:
                response_text += f"\n\n**Execution Result:**\n{execution_result.output[:500]}"

            return FallbackResponse(
                mode=self._mode or FallbackMode.PRIMARY,
                response=response_text,
                thought=thought,
                execution_result=execution_result,
                intent=intent,
                processing_time=processing_time,
                success=True,
            )

        except Exception as e:
            self._error_count += 1
            processing_time = time.time() - start_time

            logger.error(f"fallback_system.observation_error: {e}")

            return FallbackResponse(
                mode=self._mode or FallbackMode.DEGRADED,
                response=f"Error processing observation: {e}",
                thought=None,
                execution_result=None,
                intent=TaskIntent(
                    type=IntentType.QUESTION,
                    confidence=0.0,
                    raw_message=observations[:100],
                ),
                processing_time=processing_time,
                success=False,
            )

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
            "mode": self._mode.value if self._mode else "unknown",
            "uptime_seconds": uptime,
            "lm_studio": {
                "available": self.router.detector.status.available,
                "last_check": self.router.detector.status.last_check,
                "consecutive_failures": self.router.detector.status.consecutive_failures,
                "last_error": self.router.detector.status.last_error,
            },
            "gemini": self.gemini.get_availability_info(),
            "router_status": self.router.get_status(),
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
    def mode(self) -> Optional[FallbackMode]:
        """Get current operating mode."""
        return self._mode

    @property
    def is_primary_mode(self) -> bool:
        """Check if using primary (LM Studio) mode."""
        return self._mode == FallbackMode.PRIMARY

    @property
    def is_fallback_mode(self) -> bool:
        """Check if using fallback mode."""
        return self._mode in (FallbackMode.FALLBACK, FallbackMode.DEGRADED)


# Factory function for easy creation
def create_fallback_system(
    working_dir: Optional[Path] = None,
    config: Optional[FallbackSystemConfig] = None,
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
            config=FallbackSystemConfig(
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
            print(f"Intent: {response.intent.type.value}")
            print(f"Processing time: {response.processing_time:.2f}s")
            print(f"Success: {response.success}")
            print(f"\nResponse:\n{response.response[:500]}")

        await system.shutdown()

        print(f"\n{'=' * 60}")
        print("Test complete!")

    asyncio.run(test())
