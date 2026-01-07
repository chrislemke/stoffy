"""
Fallback Consciousness System - When LM Studio Sleeps, Claude Awakens

This module implements a comprehensive fallback system for the consciousness.
When the primary thinking layer (LM Studio) is unavailable, the consciousness
seamlessly switches to an alternative mode:

PRIMARY MODE: LM Studio (local LLM) provides the "thinking" layer
FALLBACK MODE: Gemini provides "inner thoughts" -> Claude Code executes

In fallback mode:
- Gemini acts as the consciousness guidance (the "inner voice")
- Claude Code is the executor with autonomous decision-making capability
- Unlike the daemon, this is NOT a continuous watcher - it responds to
  direct questions and executes tasks when needed

The key insight: Claude Code, when given Gemini's "consciousness thoughts"
as context, can autonomously decide whether a task requires execution
or is simply a question requiring an answer.

Architecture:
  User Input -> FallbackConsciousness.process()
                     |
                     v
             Mode Detection (LM Studio available?)
                     |
          +---------+---------+
          |                   |
    PRIMARY MODE         FALLBACK MODE
    (LM Studio)     (Gemini + Claude Code)
          |                   |
          v                   v
    ConsciousnessThinker  GeminiConsciousness
          |                   |
          v                   v
    Decision/Response    Claude Code Execution
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .thinker import ConsciousnessThinker, Decision, DecisionType
from .executor import (
    ExpandedExecutor,
    ExecutionConfig,
    ExecutionResult,
    Action,
    ActionType,
    Priority,
)
from .gemini_consciousness import GeminiConsciousness, ConsciousnessThought

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Data Classes
# =============================================================================

class FallbackMode(Enum):
    """Operating mode of the fallback system."""
    PRIMARY = "primary"      # LM Studio is available and active
    FALLBACK = "fallback"    # Using Claude Code + Gemini
    OFFLINE = "offline"      # No AI available


class TaskIntent(Enum):
    """
    Classification of user intent.

    Determines whether the user wants:
    - An answer to a question
    - An action to be performed
    - Both (explanation + execution)
    """
    QUESTION = "question"           # User wants information
    ACTION = "action"               # User wants something done
    QUESTION_AND_ACTION = "both"    # User wants explanation + execution
    UNKNOWN = "unknown"             # Intent unclear


@dataclass
class FallbackConfig:
    """Configuration for the fallback consciousness system."""

    # Primary (LM Studio)
    lm_studio_url: str = "http://localhost:1234/v1"
    lm_studio_model: str = "qwen2.5-14b-instruct"
    lm_studio_temperature: float = 0.7
    lm_studio_max_tokens: int = 4096
    lm_studio_timeout: int = 60

    # Gemini
    gemini_model: str = "gemini-2.0-flash-exp"
    gemini_timeout: int = 120

    # Claude Code
    claude_timeout: int = 300

    # Mode detection
    check_interval: float = 30.0  # Seconds between availability checks
    max_consecutive_failures: int = 2  # Failures before switching modes

    # Intent detection keywords
    action_keywords: List[str] = field(default_factory=lambda: [
        "create", "delete", "remove", "add", "update", "modify",
        "run", "execute", "install", "build", "test", "deploy",
        "fix", "refactor", "move", "rename", "copy", "write",
        "start", "stop", "restart", "kill", "clean", "generate",
        "commit", "push", "pull", "merge", "checkout", "branch",
        "please", "can you", "would you", "could you",
    ])

    question_keywords: List[str] = field(default_factory=lambda: [
        "what", "why", "how", "when", "where", "who", "which",
        "explain", "describe", "tell me", "show me", "help me understand",
        "is it", "are there", "does it", "can it", "will it",
    ])

    # Execution thresholds
    min_action_confidence: float = 0.6
    auto_execute_threshold: float = 0.85


@dataclass
class FallbackResponse:
    """
    Response from the fallback consciousness system.

    Contains both the thought process and any action results.
    """
    mode: FallbackMode               # Which mode was used
    response: str                    # Final response to user
    intent: TaskIntent               # Detected intent
    confidence: float                # Confidence in the response
    reasoning: str                   # The reasoning process
    execution_result: Optional[ExecutionResult] = None
    action_taken: Optional[str] = None
    error: Optional[str] = None
    duration: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "mode": self.mode.value,
            "response": self.response,
            "intent": self.intent.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "action_taken": self.action_taken,
            "error": self.error,
            "duration": self.duration,
        }
        if self.execution_result:
            result["execution_result"] = self.execution_result.to_dict()
        return result


# =============================================================================
# Intent Detector - Classify User Input
# =============================================================================

class IntentDetector:
    """
    Detects whether user input is a question, action request, or both.

    Uses keyword heuristics for quick classification before the LLM
    provides a more nuanced analysis.
    """

    def __init__(self, config: Optional[FallbackConfig] = None):
        """Initialize with configuration."""
        self.config = config or FallbackConfig()

    def detect(self, user_input: str) -> tuple[TaskIntent, float]:
        """
        Quickly detect intent from user input.

        Args:
            user_input: The user's message

        Returns:
            Tuple of (TaskIntent, confidence)
        """
        input_lower = user_input.lower().strip()

        # Count keyword matches
        action_score = sum(
            1 for kw in self.config.action_keywords
            if kw in input_lower
        )
        question_score = sum(
            1 for kw in self.config.question_keywords
            if kw in input_lower
        )

        # Check for explicit action indicators
        if input_lower.startswith(("please ", "can you ", "could you ", "would you ")):
            action_score += 2

        # Check for question marks
        if "?" in user_input:
            question_score += 1

        # Check for imperative mood (starts with verb)
        imperative_starts = ["create", "delete", "run", "make", "add", "remove", "fix", "update"]
        if any(input_lower.startswith(verb) for verb in imperative_starts):
            action_score += 3

        # Determine intent
        total_score = action_score + question_score
        if total_score == 0:
            return TaskIntent.UNKNOWN, 0.3

        action_ratio = action_score / (total_score + 0.001)

        if action_ratio > 0.7:
            confidence = min(0.9, 0.5 + (action_score * 0.1))
            return TaskIntent.ACTION, confidence
        elif action_ratio < 0.3:
            confidence = min(0.9, 0.5 + (question_score * 0.1))
            return TaskIntent.QUESTION, confidence
        else:
            return TaskIntent.QUESTION_AND_ACTION, 0.6


# =============================================================================
# Fallback Consciousness - The Main Orchestrator
# =============================================================================

class FallbackConsciousness:
    """
    The fallback consciousness system.

    Orchestrates between PRIMARY (LM Studio) and FALLBACK (Gemini + Claude Code)
    modes. When LM Studio is unavailable, seamlessly switches to the fallback
    mode where Gemini provides "consciousness thoughts" and Claude Code executes.

    Key difference from the daemon:
    - NOT a continuous watcher/loop
    - Responds to direct questions/requests
    - Auto-detects if execution is needed

    Usage:
        fallback = FallbackConsciousness(working_dir)
        response = await fallback.process("Create a new file called test.py")

        # Or use convenience methods
        answer = await fallback.answer("What is the purpose of this project?")
        result = await fallback.execute("Run the tests")
    """

    def __init__(
        self,
        working_dir: Path,
        config: Optional[FallbackConfig] = None,
    ):
        """
        Initialize the fallback consciousness.

        Args:
            working_dir: Project working directory
            config: Configuration for the fallback system
        """
        self.working_dir = Path(working_dir).resolve()
        self.config = config or FallbackConfig()

        # Current operating mode
        self._mode: FallbackMode = FallbackMode.OFFLINE

        # Primary mode: LM Studio thinker
        self._thinker: Optional[ConsciousnessThinker] = None

        # Fallback mode: Gemini consciousness
        self._gemini = GeminiConsciousness(
            model=self.config.gemini_model,
            timeout=self.config.gemini_timeout,
        )

        # Claude Code executor (used in both modes for execution)
        self._executor = ExpandedExecutor(
            working_dir=self.working_dir,
            config=ExecutionConfig(
                claude_timeout=self.config.claude_timeout,
            ),
        )

        # Intent detector for quick classification
        self._intent_detector = IntentDetector(self.config)

        # Mode tracking
        self._last_check_time: float = 0.0
        self._consecutive_failures: int = 0
        self._mode_callbacks: List[Callable[[FallbackMode, FallbackMode], None]] = []

        # Statistics
        self._stats = {
            "primary_calls": 0,
            "fallback_calls": 0,
            "executions": 0,
            "errors": 0,
        }

    async def check_availability(self) -> FallbackMode:
        """
        Check which mode is available and set the current mode.

        Uses ConsciousnessThinker.check_connection() to detect LM Studio.

        Priority:
        1. PRIMARY (LM Studio) if available
        2. FALLBACK (Gemini + Claude) if Gemini available
        3. OFFLINE if nothing available

        Returns:
            The available mode
        """
        # Check LM Studio using ConsciousnessThinker.check_connection()
        if await self._check_lm_studio():
            new_mode = FallbackMode.PRIMARY
            logger.info("fallback.mode", mode="primary", provider="lm_studio")
        elif self._gemini.is_available():
            new_mode = FallbackMode.FALLBACK
            logger.info("fallback.mode", mode="fallback", provider="gemini+claude")
        else:
            new_mode = FallbackMode.OFFLINE
            logger.warning("fallback.mode", mode="offline")

        # Trigger callbacks if mode changed
        if self._mode != new_mode and self._mode != FallbackMode.OFFLINE:
            self._trigger_mode_callbacks(self._mode, new_mode)

        self._mode = new_mode
        self._last_check_time = time.time()

        return self._mode

    async def _check_lm_studio(self) -> bool:
        """
        Check if LM Studio is available using ConsciousnessThinker.check_connection().

        Returns:
            True if LM Studio is reachable
        """
        try:
            if self._thinker is None:
                self._thinker = ConsciousnessThinker(
                    base_url=self.config.lm_studio_url,
                    model=self.config.lm_studio_model,
                    temperature=self.config.lm_studio_temperature,
                    max_tokens=self.config.lm_studio_max_tokens,
                    autonomous=True,
                )

            available = await self._thinker.check_connection()

            if available:
                self._consecutive_failures = 0
            else:
                self._consecutive_failures += 1

            return available

        except Exception as e:
            logger.warning(f"LM Studio check failed: {e}")
            self._consecutive_failures += 1
            return False

    async def _should_recheck_mode(self) -> bool:
        """Determine if we should recheck availability."""
        now = time.time()
        return (now - self._last_check_time) > self.config.check_interval

    async def process(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
        force_mode: Optional[FallbackMode] = None,
        auto_execute: bool = True,
    ) -> FallbackResponse:
        """
        Process user input through the consciousness system.

        This is the main entry point. It:
        1. Checks availability and selects mode
        2. Gets consciousness thought (from LM Studio or Gemini)
        3. Detects if execution is needed
        4. Executes via Claude Code if needed
        5. Returns comprehensive response

        Args:
            user_input: What the user said/asked
            context: Optional additional context
            force_mode: Force a specific mode (for testing)
            auto_execute: Whether to auto-execute detected actions

        Returns:
            FallbackResponse with thought, response, and execution result
        """
        start_time = time.time()

        # Determine mode
        if force_mode:
            self._mode = force_mode
        elif await self._should_recheck_mode():
            await self.check_availability()
        elif self._mode == FallbackMode.OFFLINE:
            await self.check_availability()

        if self._mode == FallbackMode.OFFLINE:
            return FallbackResponse(
                mode=FallbackMode.OFFLINE,
                response="I'm currently offline. Please check that LM Studio is running or GOOGLE_API_KEY is set.",
                intent=TaskIntent.UNKNOWN,
                confidence=0.0,
                reasoning="Neither LM Studio nor Gemini is available",
                error="No AI providers available",
                duration=(time.time() - start_time),
            )

        try:
            # Quick intent detection
            quick_intent, quick_confidence = self._intent_detector.detect(user_input)

            # Get consciousness thought/decision based on mode
            if self._mode == FallbackMode.PRIMARY:
                response_data = await self._process_primary(
                    user_input, context, quick_intent, quick_confidence
                )
                self._stats["primary_calls"] += 1
            else:
                response_data = await self._process_fallback(
                    user_input, context, quick_intent, quick_confidence
                )
                self._stats["fallback_calls"] += 1

            # Determine if we should execute
            should_execute = (
                auto_execute and
                response_data["should_execute"] and
                response_data["confidence"] >= self.config.min_action_confidence
            )

            # Execute if needed
            execution_result = None
            action_taken = None
            final_response = response_data["response"]

            if should_execute and response_data.get("suggested_action"):
                logger.info(
                    "fallback.executing",
                    action=response_data["suggested_action"][:100],
                    confidence=response_data["confidence"],
                )

                execution_result = await self._execute_action(
                    response_data["suggested_action"],
                    response_data["reasoning"],
                )
                self._stats["executions"] += 1
                action_taken = response_data["suggested_action"]

                # Combine thought and execution into response
                if execution_result.success:
                    final_response = (
                        f"{response_data['response']}\n\n---\n\n"
                        f"**Executed:** {action_taken}\n\n"
                        f"**Result:**\n{execution_result.output[:1000]}"
                    )
                else:
                    final_response = (
                        f"{response_data['response']}\n\n---\n\n"
                        f"**Execution Failed:**\n{execution_result.error}"
                    )

            return FallbackResponse(
                mode=self._mode,
                response=final_response,
                intent=response_data["intent"],
                confidence=response_data["confidence"],
                reasoning=response_data["reasoning"],
                execution_result=execution_result,
                action_taken=action_taken,
                duration=(time.time() - start_time),
            )

        except Exception as e:
            self._stats["errors"] += 1
            logger.exception(f"fallback.error: {e}")

            return FallbackResponse(
                mode=self._mode,
                response=f"I encountered an error: {e}",
                intent=TaskIntent.UNKNOWN,
                confidence=0.0,
                reasoning=str(e),
                error=str(e),
                duration=(time.time() - start_time),
            )

    async def _process_primary(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]],
        quick_intent: TaskIntent,
        quick_confidence: float,
    ) -> Dict[str, Any]:
        """
        Process using LM Studio (primary mode).

        Uses ConsciousnessThinker to get autonomous decisions.
        """
        if not self._thinker:
            raise RuntimeError("LM Studio thinker not initialized")

        # Build observation for the thinker
        observation = f"""User request: {user_input}

Quick intent analysis: {quick_intent.value} (confidence: {quick_confidence:.2f})

Context: Direct user query - respond thoughtfully and take action if needed.
This is NOT the daemon watching files - this is a direct conversation.
"""

        decision = await self._thinker.think_autonomous(
            observations=observation,
            context=context,
        )

        # Convert Decision to response format
        should_execute = decision.decision == DecisionType.ACT
        suggested_action = None
        if decision.action:
            suggested_action = decision.action.prompt or decision.action.description

        return {
            "response": decision.reasoning,
            "intent": quick_intent if not should_execute else TaskIntent.ACTION,
            "confidence": decision.confidence,
            "reasoning": decision.reasoning,
            "should_execute": should_execute,
            "suggested_action": suggested_action,
            "source": "lm_studio",
        }

    async def _process_fallback(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]],
        quick_intent: TaskIntent,
        quick_confidence: float,
    ) -> Dict[str, Any]:
        """
        Process using Gemini + Claude Code (fallback mode).

        Gemini provides "inner thoughts" that guide Claude Code's actions.
        """
        # Get consciousness thought from Gemini
        thought = await self._gemini.contemplate(
            user_input,
            context=context,
        )

        # Map Gemini's thought to our format
        if thought.should_act:
            intent = TaskIntent.ACTION
        elif quick_intent == TaskIntent.QUESTION:
            intent = TaskIntent.QUESTION
        else:
            intent = quick_intent

        # If this is a question, we might want Claude to elaborate
        response = thought.understanding
        if intent == TaskIntent.QUESTION and thought.confidence < 0.7:
            # Get a more complete answer from Claude
            elaborated = await self._elaborate_with_claude(user_input, thought)
            if elaborated:
                response = elaborated

        return {
            "response": response,
            "intent": intent,
            "confidence": thought.confidence,
            "reasoning": thought.suggested_approach,
            "should_execute": thought.should_act,
            "suggested_action": thought.action_hint,
            "source": "gemini",
        }

    async def _elaborate_with_claude(
        self,
        user_input: str,
        thought: ConsciousnessThought,
    ) -> Optional[str]:
        """
        Use Claude Code to elaborate on a question.

        When Gemini's thought is analysis-focused, Claude provides
        a more user-friendly response.
        """
        prompt = f"""Based on this analysis, provide a helpful response to the user.

USER QUESTION:
{user_input}

ANALYSIS:
{thought.understanding}

APPROACH:
{thought.suggested_approach}

Provide a clear, friendly, and helpful response.
Keep it concise but complete. Sign off as "- Stoffy" at the end.
"""

        try:
            result = await self._executor.execute(Action(
                type=ActionType.CLAUDE_CODE,
                details={"prompt": prompt},
                priority=Priority.MEDIUM,
                timeout=60,
            ))

            if result.success and result.output:
                return result.output.strip()

        except Exception as e:
            logger.warning(f"Claude elaboration failed: {e}")

        return None

    async def _execute_action(
        self,
        action_description: str,
        reasoning: str,
    ) -> ExecutionResult:
        """
        Execute an action using Claude Code.

        Claude Code is given the consciousness reasoning as context,
        allowing it to understand the reasoning behind the action.
        """
        prompt = f"""You are executing an action as part of the Stoffy consciousness.

REASONING:
{reasoning}

ACTION TO EXECUTE:
{action_description}

Execute this action. You have full permissions (--permission-mode acceptEdits).
Be direct and execute what was requested. Report what you did.
Do NOT just explain how to do it - ACTUALLY DO IT.
"""

        action = Action(
            type=ActionType.CLAUDE_CODE,
            details={"prompt": prompt},
            priority=Priority.HIGH,
            timeout=self.config.claude_timeout,
        )

        return await self._executor.execute(action)

    def on_mode_change(
        self,
        callback: Callable[[FallbackMode, FallbackMode], None]
    ) -> None:
        """
        Register a callback for mode changes.

        The callback receives (old_mode, new_mode) when the operating
        mode changes.

        Args:
            callback: Function to call on mode change
        """
        self._mode_callbacks.append(callback)

    def _trigger_mode_callbacks(
        self,
        old_mode: FallbackMode,
        new_mode: FallbackMode
    ) -> None:
        """Trigger all registered mode change callbacks."""
        for callback in self._mode_callbacks:
            try:
                callback(old_mode, new_mode)
            except Exception as e:
                logger.error(f"Mode change callback error: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the fallback system."""
        return {
            "mode": self._mode.value,
            "lm_studio_url": self.config.lm_studio_url,
            "gemini_model": self.config.gemini_model,
            "gemini_available": self._gemini.is_available(),
            "last_check_time": self._last_check_time,
            "consecutive_failures": self._consecutive_failures,
            "stats": self._stats.copy(),
            "working_dir": str(self.working_dir),
        }

    async def answer(self, question: str) -> str:
        """
        Simple interface - just get an answer to a question.

        This is a convenience method that wraps process() for simple Q&A.

        Args:
            question: User's question

        Returns:
            The response string
        """
        response = await self.process(question, auto_execute=False)
        return response.response

    async def execute(self, task: str) -> ExecutionResult:
        """
        Simple interface - execute a task.

        This is a convenience method that wraps process() for execution.

        Args:
            task: Task description

        Returns:
            ExecutionResult from the action
        """
        response = await self.process(task, auto_execute=True)

        if response.execution_result:
            return response.execution_result

        # If no execution happened, create a result from the response
        return ExecutionResult(
            success=response.error is None,
            output=response.response,
            error=response.error,
        )


# =============================================================================
# Legacy Compatibility Classes
# =============================================================================

class RouterMode(Enum):
    """Legacy mode enum for backwards compatibility."""
    PRIMARY = "primary"
    FALLBACK = "fallback"
    FORCED_PRIMARY = "forced_primary"
    FORCED_FALLBACK = "forced_fallback"


@dataclass
class RouterStatus:
    """Legacy status class for backwards compatibility."""
    mode: RouterMode
    lm_studio_available: bool
    last_check: float = 0.0
    check_interval: float = 30.0
    consecutive_failures: int = 0
    message: str = ""

    @property
    def is_fallback(self) -> bool:
        return self.mode in (RouterMode.FALLBACK, RouterMode.FORCED_FALLBACK)

    @property
    def mode_display(self) -> str:
        displays = {
            RouterMode.PRIMARY: "PRIMARY (LM Studio)",
            RouterMode.FALLBACK: "FALLBACK (Claude + Gemini)",
            RouterMode.FORCED_PRIMARY: "FORCED PRIMARY (LM Studio)",
            RouterMode.FORCED_FALLBACK: "FORCED FALLBACK (Claude + Gemini)",
        }
        return displays.get(self.mode, str(self.mode.value))


class FallbackRouter:
    """
    Legacy router class for backwards compatibility.

    Wraps FallbackConsciousness with the old FallbackRouter interface.
    """

    def __init__(
        self,
        lm_studio_url: str = "http://localhost:1234/v1",
        check_interval: float = 30.0,
        max_failures_before_fallback: int = 2,
        force_mode: Optional[str] = None,
    ):
        self.lm_studio_url = lm_studio_url
        self.check_interval = check_interval
        self.max_failures = max_failures_before_fallback
        self.force_mode = force_mode

        self._status = RouterStatus(
            mode=RouterMode.PRIMARY,
            lm_studio_available=True,
            check_interval=check_interval,
        )
        self._consciousness: Optional[FallbackConsciousness] = None

    @property
    def status(self) -> RouterStatus:
        return self._status

    async def initialize(self) -> RouterStatus:
        """Initialize the router."""
        config = FallbackConfig(
            lm_studio_url=self.lm_studio_url,
            check_interval=self.check_interval,
            max_consecutive_failures=self.max_failures,
        )

        self._consciousness = FallbackConsciousness(
            working_dir=Path.cwd(),
            config=config,
        )

        # Handle forced modes
        if self.force_mode == "primary":
            self._status.mode = RouterMode.FORCED_PRIMARY
            self._status.message = "Mode forced to PRIMARY by user"
            await self._consciousness._check_lm_studio()
            self._status.lm_studio_available = await self._consciousness._check_lm_studio()
            return self._status

        elif self.force_mode == "fallback":
            self._status.mode = RouterMode.FORCED_FALLBACK
            self._status.lm_studio_available = False
            self._status.message = "Mode forced to FALLBACK by user"
            return self._status

        # Auto mode
        mode = await self._consciousness.check_availability()

        if mode == FallbackMode.PRIMARY:
            self._status.mode = RouterMode.PRIMARY
            self._status.lm_studio_available = True
            self._status.message = "LM Studio available - using primary mode"
        else:
            self._status.mode = RouterMode.FALLBACK
            self._status.lm_studio_available = False
            self._status.message = "LM Studio unavailable - using fallback mode"

        return self._status

    async def should_use_fallback(self) -> bool:
        """Determine if fallback should be used."""
        if self._status.mode == RouterMode.FORCED_PRIMARY:
            return False
        if self._status.mode == RouterMode.FORCED_FALLBACK:
            return True

        if self._consciousness:
            mode = await self._consciousness.check_availability()
            is_fallback = mode == FallbackMode.FALLBACK

            # Update status
            if is_fallback and self._status.mode == RouterMode.PRIMARY:
                self._status.mode = RouterMode.FALLBACK
                self._status.message = "LM Studio failed - switching to fallback mode"
            elif not is_fallback and self._status.mode == RouterMode.FALLBACK:
                self._status.mode = RouterMode.PRIMARY
                self._status.message = "LM Studio restored - switching to primary mode"

            return is_fallback

        return self._status.is_fallback

    async def get_response(
        self,
        message: str,
        executor: Any,
        system_prompt: str = "",
        conversation_history: str = "",
        action_instruction: str = "",
    ) -> str:
        """Get a response using the appropriate backend."""
        if self._consciousness is None:
            await self.initialize()

        prompt = f"""{system_prompt}
{action_instruction}{conversation_history}
USER: {message}

Respond helpfully and concisely:"""

        # Use Claude Code directly for simplicity
        action = Action(
            type=ActionType.CLAUDE_CODE,
            details={"prompt": prompt},
            timeout=120,
        )

        result = await executor.execute(action)

        if result.success and result.output:
            return result.output.strip()
        return f"[Error generating response: {result.error}]"

    def get_status_display(self) -> str:
        """Get a formatted status display string."""
        mode_color = "green" if not self._status.is_fallback else "yellow"
        avail = "[green]OK[/green]" if self._status.lm_studio_available else "[red]DOWN[/red]"
        return f"[{mode_color}]Mode: {self._status.mode_display}[/{mode_color}] | LM Studio: {avail}"


# =============================================================================
# Convenience Functions
# =============================================================================

async def quick_fallback(
    user_input: str,
    working_dir: Optional[Path] = None,
) -> FallbackResponse:
    """
    Quick one-shot fallback consciousness call.

    Args:
        user_input: What the user wants
        working_dir: Project directory (defaults to cwd)

    Returns:
        FallbackResponse with the result
    """
    wd = working_dir or Path.cwd()
    fallback = FallbackConsciousness(wd)
    return await fallback.process(user_input)


async def create_fallback_router(
    config: Any,
    force_mode: Optional[str] = None,
    fallback_enabled: bool = True,
) -> FallbackRouter:
    """
    Factory function to create and initialize a FallbackRouter.

    Args:
        config: ConsciousnessConfig instance
        force_mode: "primary", "fallback", or None for auto
        fallback_enabled: If False, always use primary (no fallback)

    Returns:
        Initialized FallbackRouter instance
    """
    if not fallback_enabled:
        force_mode = "primary"

    router = FallbackRouter(
        lm_studio_url=config.lm_studio.base_url,
        force_mode=force_mode,
    )

    await router.initialize()
    return router


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    import sys

    async def main():
        """Test the fallback consciousness system."""
        print("=" * 60)
        print("Fallback Consciousness System Test")
        print("=" * 60)

        fallback = FallbackConsciousness(Path.cwd())

        # Check availability
        mode = await fallback.check_availability()
        print(f"\nOperating Mode: {mode.value}")
        print(f"Status: {json.dumps(fallback.get_status(), indent=2)}")

        if mode == FallbackMode.OFFLINE:
            print("\nNo AI providers available. Exiting.")
            return

        # Test with a question
        print("\n" + "-" * 40)
        print("Test 1: Question")
        print("-" * 40)

        response = await fallback.process(
            "What is the purpose of this consciousness system?",
            auto_execute=False,
        )

        print(f"Mode: {response.mode.value}")
        print(f"Intent: {response.intent.value}")
        print(f"Confidence: {response.confidence:.2f}")
        print(f"\nResponse:\n{response.response[:500]}...")

        # Test with an action request (dry run)
        print("\n" + "-" * 40)
        print("Test 2: Action Request")
        print("-" * 40)

        response = await fallback.process(
            "List the files in the current directory",
            auto_execute=False,  # Dry run for safety
        )

        print(f"Mode: {response.mode.value}")
        print(f"Intent: {response.intent.value}")
        print(f"Confidence: {response.confidence:.2f}")
        print(f"Action would be: {response.action_taken or 'N/A'}")

        print("\n" + "=" * 60)
        print("Tests complete!")

    asyncio.run(main())
