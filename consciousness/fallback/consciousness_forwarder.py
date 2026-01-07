"""
Consciousness Forwarder - Forwards consciousness requests to fallback.

When LM Studio is down, this component forwards thinking/reasoning
requests to Gemini while maintaining the same interface as the
original ConsciousnessThinker.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

import structlog

from .gemini_consciousness import GeminiConsciousness, GeminiConfig, ConsciousnessThought
from .lm_studio_detector import LMStudioDetector, LMStudioStatus

logger = structlog.get_logger(__name__)


@dataclass
class ForwardedDecision:
    """
    A decision forwarded through the consciousness forwarder.

    Wraps ConsciousnessThought to provide interface compatibility
    with the original Decision class from thinker.py.
    """
    observation_summary: str
    reasoning: str
    decision: str  # "act", "wait", "investigate"
    action: Optional[Dict[str, Any]] = None
    confidence: float = 0.5
    expected_outcome: str = ""
    raw_response: str = ""
    source: str = "gemini"  # Where this decision came from

    def to_dict(self) -> dict:
        result = {
            "observation_summary": self.observation_summary,
            "reasoning": self.reasoning,
            "decision": self.decision,
            "confidence": self.confidence,
            "expected_outcome": self.expected_outcome,
            "source": self.source,
        }
        if self.action:
            result["action"] = self.action
        return result

    @classmethod
    def from_thought(cls, thought: ConsciousnessThought) -> "ForwardedDecision":
        """Create a ForwardedDecision from a ConsciousnessThought."""
        action = None
        if thought.suggested_action:
            action = {
                "type": "claude_code",
                "description": thought.suggested_action,
                "details": thought.action_details or {},
                "priority": "medium",
            }

        return cls(
            observation_summary=thought.observation,
            reasoning=thought.reasoning,
            decision=thought.conclusion,
            action=action,
            confidence=thought.confidence,
            expected_outcome=thought.suggested_action or "No specific action",
            raw_response=thought.raw_response,
            source="gemini",
        )

    @classmethod
    def wait(cls, reasoning: str = "No action needed") -> "ForwardedDecision":
        """Create a wait decision."""
        return cls(
            observation_summary="",
            reasoning=reasoning,
            decision="wait",
            confidence=1.0,
            source="fallback",
        )

    @classmethod
    def error(cls, error_msg: str) -> "ForwardedDecision":
        """Create an error decision."""
        return cls(
            observation_summary="Error occurred",
            reasoning=f"Error: {error_msg}",
            decision="wait",
            confidence=0.0,
            source="error",
        )


class ConsciousnessForwarder:
    """
    Forwards consciousness requests to fallback backends.

    Provides the same interface as ConsciousnessThinker but routes
    to Gemini when in fallback mode. Automatically switches between
    primary and fallback based on LM Studio availability.
    """

    def __init__(
        self,
        detector: Optional[LMStudioDetector] = None,
        gemini: Optional[GeminiConsciousness] = None,
        gemini_config: Optional[GeminiConfig] = None,
    ):
        """
        Initialize the forwarder.

        Args:
            detector: LM Studio detector
            gemini: Gemini consciousness instance
            gemini_config: Gemini configuration
        """
        self._detector = detector
        self._gemini = gemini or GeminiConsciousness(gemini_config)

        # Import thinker here to avoid circular imports
        self._thinker = None
        self._initialized = False

        # Statistics
        self._forward_count = 0
        self._primary_count = 0
        self._gemini_count = 0

    async def initialize(self) -> None:
        """Initialize the forwarder."""
        if self._initialized:
            return

        try:
            from ..thinker import ConsciousnessThinker

            self._thinker = ConsciousnessThinker(autonomous=True)
            await self._gemini.initialize()
            self._initialized = True

            logger.info("consciousness_forwarder.initialized")

        except Exception as e:
            logger.error(f"consciousness_forwarder.init_error: {e}")

    async def think(
        self,
        observations: str,
        context: Optional[Dict[str, Any]] = None,
        git_status: Optional[str] = None,
        learned_patterns: Optional[List[str]] = None,
        force_gemini: bool = False,
    ) -> ForwardedDecision:
        """
        Think about observations using available backend.

        Args:
            observations: What was observed
            context: Additional context
            git_status: Git status information
            learned_patterns: Patterns from learning
            force_gemini: Force use of Gemini regardless of LM Studio status

        Returns:
            ForwardedDecision with reasoning and decision
        """
        await self.initialize()

        self._forward_count += 1

        # Determine which backend to use
        use_primary = False
        if not force_gemini and self._detector:
            use_primary = self._detector.is_available
        elif not force_gemini and self._thinker:
            use_primary = await self._thinker.check_connection()

        if use_primary and self._thinker:
            # Use LM Studio
            return await self._think_primary(
                observations, context, git_status, learned_patterns
            )
        else:
            # Use Gemini
            return await self._think_gemini(
                observations, context, git_status, learned_patterns
            )

    async def _think_primary(
        self,
        observations: str,
        context: Optional[Dict[str, Any]],
        git_status: Optional[str],
        learned_patterns: Optional[List[str]],
    ) -> ForwardedDecision:
        """Think using primary LM Studio backend."""
        self._primary_count += 1

        try:
            if not self._thinker:
                return ForwardedDecision.error("Thinker not initialized")

            decision = await self._thinker.think_autonomous(
                observations=observations,
                git_status=git_status,
                learned_patterns=learned_patterns,
                context=context,
            )

            # Convert Decision to ForwardedDecision
            action = None
            if decision.action:
                action = decision.action.to_dict()

            return ForwardedDecision(
                observation_summary=decision.observation_summary,
                reasoning=decision.reasoning,
                decision=decision.decision.value,
                action=action,
                confidence=decision.confidence,
                expected_outcome=decision.expected_outcome,
                raw_response=decision.raw_response,
                source="lm_studio",
            )

        except Exception as e:
            logger.warning(f"consciousness_forwarder.primary_failed: {e}")
            # Fall back to Gemini
            return await self._think_gemini(
                observations, context, git_status, learned_patterns
            )

    async def _think_gemini(
        self,
        observations: str,
        context: Optional[Dict[str, Any]],
        git_status: Optional[str],
        learned_patterns: Optional[List[str]],
    ) -> ForwardedDecision:
        """Think using Gemini fallback backend."""
        self._gemini_count += 1

        try:
            thought = await self._gemini.think(
                observations=observations,
                context=context,
                git_status=git_status,
                learned_patterns=learned_patterns,
            )

            return ForwardedDecision.from_thought(thought)

        except Exception as e:
            logger.error(f"consciousness_forwarder.gemini_failed: {e}")
            return ForwardedDecision.error(str(e))

    async def analyze_context(
        self,
        context: str,
        question: str,
    ) -> str:
        """
        Analyze large context using Gemini.

        This always uses Gemini regardless of mode, as it excels
        at large context analysis.

        Args:
            context: Large text context
            question: Question to answer

        Returns:
            Analysis result
        """
        await self.initialize()
        return await self._gemini.analyze_large_context(context, question)

    def get_statistics(self) -> dict:
        """Get forwarder statistics."""
        return {
            "forward_count": self._forward_count,
            "primary_count": self._primary_count,
            "gemini_count": self._gemini_count,
            "primary_rate": (
                self._primary_count / self._forward_count
                if self._forward_count > 0 else 0.0
            ),
            "initialized": self._initialized,
            "gemini_available": self._gemini.is_available(),
        }


if __name__ == "__main__":
    async def test():
        print("Testing Consciousness Forwarder...")

        forwarder = ConsciousnessForwarder()
        await forwarder.initialize()

        observations = """
File changed: consciousness/fallback/test.py
Change type: created
Content appears to be a test file.
"""

        # Force Gemini to test fallback
        decision = await forwarder.think(
            observations=observations,
            context={"mode": "test"},
            force_gemini=True,
        )

        print(f"\nDecision: {decision.to_dict()}")
        print(f"\nStatistics: {forwarder.get_statistics()}")

    asyncio.run(test())
