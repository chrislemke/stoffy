"""
Fallback Router - Intelligent Routing Between LM Studio and Claude Code

This module implements seamless fallback routing for the Consciousness daemon.
When LM Studio is unavailable, it gracefully switches to Claude Code + Gemini
for thinking and response generation.

ROUTING HIERARCHY:
1. PRIMARY: LM Studio (local, fast, cost-free)
2. FALLBACK: Claude Code + Gemini (cloud-based, more capable)
3. DEGRADED: Claude Code only (when Gemini is also unavailable)

The router automatically detects availability and switches modes transparently,
ensuring the Consciousness daemon remains operational regardless of which
backend services are available.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any

from .thinker import (
    ConsciousnessThinker,
    Decision,
    DecisionType,
    Action,
    ActionType,
    Priority,
)
from .executor import (
    ExpandedExecutor,
    ExecutionResult,
    ExecutionConfig,
    Action as ExecutorAction,
    ActionType as ExecutorActionType,
)

logger = logging.getLogger(__name__)


class FallbackMode(Enum):
    """Operating modes for the fallback router."""

    PRIMARY = "lm_studio"      # LM Studio is available - use local inference
    FALLBACK = "claude_gemini" # Using Claude Code + Gemini for thinking
    DEGRADED = "claude_only"   # Gemini also unavailable - Claude only


@dataclass
class FallbackConfig:
    """Configuration for the fallback router."""

    # LM Studio settings
    lm_studio_url: str = "http://localhost:1234/v1"
    lm_studio_model: str = "local-model"
    lm_studio_temperature: float = 0.7
    lm_studio_max_tokens: int = 4096

    # Availability check settings
    check_interval: float = 30.0  # Seconds between availability checks
    connection_timeout: float = 5.0  # Timeout for connection checks
    max_consecutive_failures: int = 3  # Failures before switching modes

    # Routing preferences
    prefer_gemini_for_analysis: bool = True  # Use Gemini for large context analysis
    gemini_context_threshold: int = 8000  # Chars above which to prefer Gemini

    # Execution settings
    auto_execute_threshold: float = 0.8  # Confidence threshold for auto-execution
    claude_timeout: int = 300  # Timeout for Claude Code operations
    gemini_timeout: int = 600  # Timeout for Gemini operations

    # Claude Code settings
    claude_system_prompt: str = """You are Stoffy's thinking layer. Analyze observations
and make decisions about what actions to take.

When given observations, respond with a JSON decision in this exact format:
{
    "observation_summary": "Brief summary of what was observed",
    "reasoning": "Your step-by-step thinking process",
    "decision": "act" | "wait" | "investigate",
    "action": {
        "type": "claude_code|write_file|run_python|run_bash|claude_flow",
        "description": "What you are doing and why",
        "details": { ... },
        "priority": "low|medium|high|critical"
    },
    "confidence": 0.0 to 1.0,
    "expected_outcome": "What you anticipate"
}

Be proactive and autonomous. If action is needed, take it."""


@dataclass
class LMStudioStatus:
    """Status of LM Studio availability."""

    available: bool = False
    last_check: float = 0.0
    consecutive_failures: int = 0
    last_error: Optional[str] = None
    model_info: Optional[Dict[str, Any]] = None


class LMStudioDetector:
    """
    Detects LM Studio availability.

    Performs async health checks against the LM Studio API endpoint
    to determine if local inference is available.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        timeout: float = 5.0
    ):
        """
        Initialize the detector.

        Args:
            base_url: LM Studio API endpoint
            timeout: Connection timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self._status = LMStudioStatus()

    @property
    def status(self) -> LMStudioStatus:
        """Get current status."""
        return self._status

    async def check_availability(self) -> bool:
        """
        Check if LM Studio is available.

        Attempts to connect to the LM Studio API and verify
        that a model is loaded and responding.

        Returns:
            True if LM Studio is available and ready
        """
        from openai import AsyncOpenAI

        try:
            client = AsyncOpenAI(
                base_url=self.base_url,
                api_key="not-needed",
                timeout=self.timeout
            )

            # Try to list models - this confirms API is responsive
            models = await asyncio.wait_for(
                client.models.list(),
                timeout=self.timeout
            )

            # Update status
            self._status.available = True
            self._status.last_check = time.time()
            self._status.consecutive_failures = 0
            self._status.last_error = None

            if hasattr(models, 'data') and models.data:
                self._status.model_info = {
                    "model_count": len(models.data),
                    "models": [m.id for m in models.data[:3]]  # First 3 models
                }

            logger.debug(f"LM Studio available at {self.base_url}")
            return True

        except asyncio.TimeoutError:
            self._record_failure("Connection timeout")
            return False

        except Exception as e:
            self._record_failure(str(e))
            return False

    def _record_failure(self, error: str) -> None:
        """Record a connection failure."""
        self._status.available = False
        self._status.last_check = time.time()
        self._status.consecutive_failures += 1
        self._status.last_error = error
        logger.debug(
            f"LM Studio check failed ({self._status.consecutive_failures}): {error}"
        )

    def is_recently_checked(self, max_age: float = 30.0) -> bool:
        """Check if status was checked recently."""
        if self._status.last_check == 0:
            return False
        return (time.time() - self._status.last_check) < max_age


class FallbackRouter:
    """
    Routes requests to appropriate backend based on availability.

    This is the central routing component that ensures the Consciousness
    daemon can continue operating regardless of which backends are available.

    Features:
    - Automatic mode detection and switching
    - Mode change callbacks for logging/metrics
    - Caching to avoid repeated availability checks
    - Graceful fallback chain: LM Studio -> Claude+Gemini -> Claude-only
    """

    def __init__(
        self,
        working_dir: Path,
        config: Optional[FallbackConfig] = None,
        executor: Optional[ExpandedExecutor] = None
    ):
        """
        Initialize the fallback router.

        Args:
            working_dir: Working directory for execution
            config: Router configuration
            executor: Optional pre-configured executor
        """
        self.working_dir = Path(working_dir).resolve()
        self.config = config or FallbackConfig()

        # Initialize components
        self.detector = LMStudioDetector(
            base_url=self.config.lm_studio_url,
            timeout=self.config.connection_timeout
        )

        self.executor = executor or ExpandedExecutor(
            self.working_dir,
            ExecutionConfig(
                claude_timeout=self.config.claude_timeout,
                gemini_timeout=self.config.gemini_timeout
            )
        )

        self.thinker: Optional[ConsciousnessThinker] = None

        # Mode tracking
        self._current_mode: Optional[FallbackMode] = None
        self._mode_callbacks: List[Callable[[FallbackMode, FallbackMode], None]] = []
        self._last_mode_check: float = 0.0

        # Gemini availability cache
        self._gemini_available: Optional[bool] = None
        self._gemini_last_check: float = 0.0

    @property
    def current_mode(self) -> Optional[FallbackMode]:
        """Get current operating mode (may be stale)."""
        return self._current_mode

    async def get_current_mode(self) -> FallbackMode:
        """
        Get current operating mode, checking availability if needed.

        This method:
        1. Checks if a recent mode check exists
        2. If not, performs availability checks
        3. Updates mode and triggers callbacks if changed
        4. Returns the current mode

        Returns:
            Current FallbackMode
        """
        now = time.time()

        # Use cached mode if checked recently
        if (
            self._current_mode is not None and
            (now - self._last_mode_check) < self.config.check_interval
        ):
            return self._current_mode

        # Check LM Studio availability
        lm_studio_available = await self.detector.check_availability()

        if lm_studio_available:
            new_mode = FallbackMode.PRIMARY
        else:
            # Check Gemini availability
            gemini_available = await self._check_gemini_availability()
            if gemini_available:
                new_mode = FallbackMode.FALLBACK
            else:
                new_mode = FallbackMode.DEGRADED

        # Update mode and trigger callbacks if changed
        old_mode = self._current_mode
        self._current_mode = new_mode
        self._last_mode_check = now

        if old_mode is not None and old_mode != new_mode:
            logger.info(f"Mode changed: {old_mode.value} -> {new_mode.value}")
            self._trigger_mode_callbacks(old_mode, new_mode)

        return new_mode

    async def _check_gemini_availability(self) -> bool:
        """Check if Gemini is available."""
        now = time.time()

        # Use cached result if recent
        if (
            self._gemini_available is not None and
            (now - self._gemini_last_check) < self.config.check_interval
        ):
            return self._gemini_available

        # Check via executor capability
        self._gemini_available = self.executor._check_gemini_available()
        self._gemini_last_check = now

        return self._gemini_available

    async def _ensure_thinker(self) -> ConsciousnessThinker:
        """Ensure thinker is initialized for primary mode."""
        if self.thinker is None:
            self.thinker = ConsciousnessThinker(
                base_url=self.config.lm_studio_url,
                model=self.config.lm_studio_model,
                temperature=self.config.lm_studio_temperature,
                max_tokens=self.config.lm_studio_max_tokens,
                autonomous=True
            )
        return self.thinker

    async def route_thinking(
        self,
        observations: str,
        context: Optional[Dict[str, Any]] = None,
        git_status: Optional[str] = None,
        learned_patterns: Optional[List[str]] = None
    ) -> Decision:
        """
        Route a thinking request to the appropriate backend.

        This is the main entry point for decision-making. It automatically
        routes to LM Studio, Claude+Gemini, or Claude-only based on
        current availability.

        Args:
            observations: Description of what was observed
            context: Additional context dictionary
            git_status: Optional git status output
            learned_patterns: Optional list of learned patterns

        Returns:
            A Decision object with reasoning and recommended action
        """
        mode = await self.get_current_mode()

        logger.debug(f"Routing thinking request in {mode.value} mode")

        try:
            if mode == FallbackMode.PRIMARY:
                return await self._think_with_lm_studio(
                    observations, context, git_status, learned_patterns
                )
            elif mode == FallbackMode.FALLBACK:
                return await self._think_with_claude_gemini(
                    observations, context, git_status, learned_patterns
                )
            else:  # DEGRADED
                return await self._think_with_claude_only(
                    observations, context, git_status, learned_patterns
                )

        except Exception as e:
            logger.exception(f"Thinking failed in {mode.value} mode: {e}")

            # If primary mode failed, try fallback
            if mode == FallbackMode.PRIMARY:
                logger.info("Primary mode failed, attempting fallback")
                self._current_mode = None  # Force recheck
                return await self.route_thinking(
                    observations, context, git_status, learned_patterns
                )

            return Decision.error(str(e))

    async def _think_with_lm_studio(
        self,
        observations: str,
        context: Optional[Dict[str, Any]] = None,
        git_status: Optional[str] = None,
        learned_patterns: Optional[List[str]] = None
    ) -> Decision:
        """Use LM Studio for thinking."""
        thinker = await self._ensure_thinker()

        return await thinker.think_autonomous(
            observations=observations,
            git_status=git_status,
            learned_patterns=learned_patterns,
            context=context
        )

    async def _think_with_claude_gemini(
        self,
        observations: str,
        context: Optional[Dict[str, Any]] = None,
        git_status: Optional[str] = None,
        learned_patterns: Optional[List[str]] = None
    ) -> Decision:
        """
        Use Claude Code + Gemini for thinking.

        Strategy:
        - Use Gemini for large context analysis if configured
        - Use Claude Code for decision generation
        - Combine insights for final decision
        """
        # Build the full context
        full_context = self._build_context_string(
            observations, context, git_status, learned_patterns
        )

        # Determine if we should use Gemini for context analysis
        use_gemini = (
            self.config.prefer_gemini_for_analysis and
            len(full_context) > self.config.gemini_context_threshold
        )

        if use_gemini:
            # Use Gemini to pre-process/summarize context
            gemini_analysis = await self._gemini_analyze_context(full_context)
            if gemini_analysis:
                # Use Claude Code with Gemini's analysis
                return await self._claude_decide_with_analysis(
                    observations, gemini_analysis, context
                )

        # Standard Claude Code decision
        return await self._claude_decide(observations, context)

    async def _think_with_claude_only(
        self,
        observations: str,
        context: Optional[Dict[str, Any]] = None,
        git_status: Optional[str] = None,
        learned_patterns: Optional[List[str]] = None
    ) -> Decision:
        """Use Claude Code only for thinking (degraded mode)."""
        return await self._claude_decide(observations, context)

    def _build_context_string(
        self,
        observations: str,
        context: Optional[Dict[str, Any]] = None,
        git_status: Optional[str] = None,
        learned_patterns: Optional[List[str]] = None
    ) -> str:
        """Build a full context string from all inputs."""
        import json

        parts = [f"## Observations\n{observations}"]

        if git_status:
            parts.append(f"\n## Git Status\n```\n{git_status}\n```")

        if learned_patterns:
            patterns_str = "\n".join(f"- {p}" for p in learned_patterns[:5])
            parts.append(f"\n## Learned Patterns\n{patterns_str}")

        if context:
            parts.append(f"\n## Context\n```json\n{json.dumps(context, indent=2)}\n```")

        return "\n".join(parts)

    async def _gemini_analyze_context(self, context: str) -> Optional[str]:
        """Use Gemini to analyze large context."""
        prompt = f"""Analyze the following context and summarize:
1. Key observations
2. Most important patterns
3. Recommended focus areas

Context:
{context}

Provide a concise analysis (300-500 words) that will help make a decision."""

        try:
            result = await self.executor.execute(
                ExecutorAction.gemini_analyze(
                    prompt=prompt,
                    model="gemini-1.5-flash"  # Use flash for faster analysis
                )
            )

            if result.success:
                return result.output
            else:
                logger.warning(f"Gemini analysis failed: {result.error}")
                return None

        except Exception as e:
            logger.warning(f"Gemini analysis error: {e}")
            return None

    async def _claude_decide_with_analysis(
        self,
        observations: str,
        gemini_analysis: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Decision:
        """Use Claude Code to decide with Gemini's analysis."""
        import json

        prompt = f"""{self.config.claude_system_prompt}

## Gemini Analysis
{gemini_analysis}

## Current Observations
{observations}

## Additional Context
{json.dumps(context or {}, indent=2)}

Based on this analysis, decide what action to take. Respond with the JSON decision format."""

        return await self._execute_claude_decision(prompt)

    async def _claude_decide(
        self,
        observations: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Decision:
        """Use Claude Code alone for decision."""
        import json

        prompt = f"""{self.config.claude_system_prompt}

## Observations
{observations}

## Context
{json.dumps(context or {}, indent=2)}

Analyze the observations and decide what action to take. Respond with the JSON decision format."""

        return await self._execute_claude_decision(prompt)

    async def _execute_claude_decision(self, prompt: str) -> Decision:
        """Execute Claude Code and parse the decision."""
        try:
            result = await self.executor.execute(
                ExecutorAction(
                    type=ExecutorActionType.CLAUDE_CODE,
                    details={"prompt": prompt}
                )
            )

            if not result.success:
                return Decision.error(result.error or "Claude Code execution failed")

            # Parse the response
            return self._parse_claude_response(result.output)

        except Exception as e:
            logger.exception(f"Claude decision execution failed: {e}")
            return Decision.error(str(e))

    def _parse_claude_response(self, response: str) -> Decision:
        """Parse Claude Code response into a Decision object."""
        import json
        import re

        response = response.strip()

        # Try to extract JSON from the response
        # Strategy 1: Handle markdown code blocks
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end > start:
                response = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end > start:
                response = response[start:end].strip()

        # Strategy 2: Try direct parse
        try:
            data = json.loads(response)
            return Decision.from_dict(data)
        except json.JSONDecodeError:
            pass

        # Strategy 3: Find JSON object in response
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, response)
        for match in matches:
            try:
                data = json.loads(match)
                if any(key in data for key in ['decision', 'reasoning', 'action']):
                    return Decision.from_dict(data)
            except json.JSONDecodeError:
                continue

        # Strategy 4: Create a default decision from the response
        logger.warning("Could not parse Claude response as JSON, creating default decision")

        return Decision(
            observation_summary="Claude analysis",
            reasoning=response[:500] if response else "Unable to parse response",
            decision=DecisionType.WAIT,
            confidence=0.3,
            raw_response=response
        )

    async def route_response(
        self,
        user_message: str,
        file_context: Optional[str] = None
    ) -> str:
        """
        Route a user message to get a response.

        This is used for direct user interaction, not autonomous thinking.

        Args:
            user_message: The user's message
            file_context: Optional file context

        Returns:
            Response string
        """
        mode = await self.get_current_mode()

        if mode == FallbackMode.PRIMARY:
            # Use LM Studio directly
            thinker = await self._ensure_thinker()
            decision = await thinker.think(user_message)
            return decision.reasoning

        else:
            # Use Claude Code
            prompt = f"""Respond to this user message:

{user_message}

{f"File context: {file_context}" if file_context else ""}

Provide a helpful, concise response."""

            result = await self.executor.execute(
                ExecutorAction(
                    type=ExecutorActionType.CLAUDE_CODE,
                    details={"prompt": prompt}
                )
            )

            if result.success:
                return result.output
            else:
                return f"I encountered an error: {result.error}"

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

    async def should_auto_execute(self, decision: Decision) -> bool:
        """
        Determine if a decision should be auto-executed.

        Based on confidence threshold and decision type.

        Args:
            decision: The decision to evaluate

        Returns:
            True if the decision should be auto-executed
        """
        if decision.decision != DecisionType.ACT:
            return False

        if decision.confidence < self.config.auto_execute_threshold:
            return False

        # Additional safety checks could go here
        return True

    def get_status(self) -> Dict[str, Any]:
        """Get current router status for monitoring."""
        return {
            "mode": self._current_mode.value if self._current_mode else "unknown",
            "lm_studio": {
                "available": self.detector.status.available,
                "last_check": self.detector.status.last_check,
                "consecutive_failures": self.detector.status.consecutive_failures,
                "last_error": self.detector.status.last_error,
                "model_info": self.detector.status.model_info
            },
            "gemini_available": self._gemini_available,
            "last_mode_check": self._last_mode_check,
            "config": {
                "lm_studio_url": self.config.lm_studio_url,
                "check_interval": self.config.check_interval,
                "auto_execute_threshold": self.config.auto_execute_threshold
            }
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def create_router(
    working_dir: Path,
    config: Optional[FallbackConfig] = None
) -> FallbackRouter:
    """
    Create and initialize a fallback router.

    Performs initial availability checks.

    Args:
        working_dir: Working directory
        config: Optional configuration

    Returns:
        Initialized FallbackRouter
    """
    router = FallbackRouter(working_dir, config)

    # Perform initial mode detection
    mode = await router.get_current_mode()
    logger.info(f"Fallback router initialized in {mode.value} mode")

    return router


async def route_thinking(
    observations: str,
    working_dir: Optional[Path] = None,
    config: Optional[FallbackConfig] = None
) -> Decision:
    """
    Convenience function for one-shot thinking with automatic routing.

    Args:
        observations: What was observed
        working_dir: Optional working directory
        config: Optional configuration

    Returns:
        Decision from the appropriate backend
    """
    wd = working_dir or Path.cwd()
    router = await create_router(wd, config)
    return await router.route_thinking(observations)


# =============================================================================
# MAIN - Testing
# =============================================================================

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    async def test_router():
        """Test the fallback router."""
        print("=" * 60)
        print("Fallback Router Test")
        print("=" * 60)

        router = FallbackRouter(
            working_dir=Path.cwd(),
            config=FallbackConfig(
                check_interval=5.0,  # Short interval for testing
                connection_timeout=3.0
            )
        )

        # Register mode change callback
        def on_mode_change(old: FallbackMode, new: FallbackMode):
            print(f"\n*** MODE CHANGE: {old.value} -> {new.value} ***\n")

        router.on_mode_change(on_mode_change)

        # Check current mode
        print("\n--- Initial Mode Detection ---")
        mode = await router.get_current_mode()
        print(f"Current mode: {mode.value}")

        # Get status
        print("\n--- Router Status ---")
        status = router.get_status()
        for key, value in status.items():
            print(f"  {key}: {value}")

        # Test thinking
        print("\n--- Test Thinking ---")
        observations = """
        File changed: test.py
        Change type: modified
        Lines added: 10
        Lines removed: 5

        The file appears to be a test file that was updated.
        """

        print(f"Routing thinking request in {mode.value} mode...")

        decision = await router.route_thinking(
            observations=observations,
            context={"test": True},
            git_status="On branch main\nChanges not staged for commit:\n  modified: test.py"
        )

        print(f"\nDecision: {decision.decision.value}")
        print(f"Confidence: {decision.confidence:.2f}")
        print(f"Reasoning: {decision.reasoning[:200]}...")

        if decision.action:
            print(f"\nAction: {decision.action.type.value}")
            print(f"Description: {decision.action.description}")

        # Test auto-execute check
        print("\n--- Auto-Execute Check ---")
        should_execute = await router.should_auto_execute(decision)
        print(f"Should auto-execute: {should_execute}")

        print("\n" + "=" * 60)
        print("Test complete!")

    asyncio.run(test_router())
