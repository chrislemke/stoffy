"""
Learning Integration - Integrates learning into the consciousness daemon.

Provides:
- Automatic outcome recording after action execution
- Confidence adjustment based on historical data
- Periodic pattern extraction
- Learning-enhanced decision making
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from consciousness.executor import ExecutionResult
    from consciousness.thinker import Decision

from .tracker import OutcomeTracker, Outcome
from .patterns import PatternLearner, Suggestion

logger = logging.getLogger(__name__)


@dataclass
class LearningConfig:
    """Configuration for the learning integration."""

    # Outcome tracking
    record_all_outcomes: bool = True
    max_outcome_age_days: int = 30
    max_outcomes: int = 10000

    # Pattern learning
    pattern_update_interval: int = 50  # Update patterns every N decisions
    min_pattern_occurrences: int = 3
    min_pattern_success_rate: float = 0.5

    # Confidence adjustment
    enable_confidence_adjustment: bool = True
    min_history_for_adjustment: int = 5  # Minimum outcomes before adjusting

    # Suggestions
    max_suggestions: int = 3
    min_suggestion_confidence: float = 0.6


class LearningIntegration:
    """
    Integrates outcome tracking and pattern learning into the daemon.

    Provides methods to:
    - Record outcomes after action execution
    - Adjust confidence based on history
    - Get suggestions from learned patterns
    - Periodically update pattern database
    """

    def __init__(
        self,
        db_path: str | Path,
        config: Optional[LearningConfig] = None,
    ):
        """
        Initialize learning integration.

        Args:
            db_path: Path to the SQLite database
            config: Optional learning configuration
        """
        self.db_path = Path(db_path)
        self.config = config or LearningConfig()

        self.outcome_tracker = OutcomeTracker(db_path)
        self.pattern_learner = PatternLearner(db_path, self.outcome_tracker)

        self._decision_count = 0
        self._last_pattern_update = 0.0
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the learning system."""
        if self._initialized:
            return

        await self.outcome_tracker.initialize()
        self._initialized = True
        logger.info("Learning integration initialized")

    async def close(self) -> None:
        """Close database connections."""
        await self.outcome_tracker.close()
        await self.pattern_learner.close()

    async def record_outcome(
        self,
        observation: str,
        action_type: str,
        action_details: str,
        result: "ExecutionResult",
        confidence_used: float = 0.0,
        context: Optional[dict[str, Any]] = None,
    ) -> int:
        """
        Record the outcome of an executed action.

        Args:
            observation: The observation that triggered the action
            action_type: Type of action executed
            action_details: Details/prompt of the action
            result: ExecutionResult from the executor
            confidence_used: Confidence level at decision time
            context: Additional context

        Returns:
            ID of the recorded outcome
        """
        if not self.config.record_all_outcomes:
            return 0

        outcome_id = await self.outcome_tracker.record_outcome(
            observation=observation,
            action_type=action_type,
            action_details=action_details,
            success=result.success,
            output=result.output[:5000] if result.output else "",  # Limit output size
            error=result.error,
            execution_time=result.duration,
            confidence_used=confidence_used,
            context=context,
        )

        self._decision_count += 1

        # Periodically update patterns
        if self._decision_count % self.config.pattern_update_interval == 0:
            asyncio.create_task(self._update_patterns_async())

        return outcome_id

    async def _update_patterns_async(self) -> None:
        """Update patterns in background."""
        try:
            await self.pattern_learner.update_patterns()
            self._last_pattern_update = time.time()
        except Exception as e:
            logger.warning(f"Failed to update patterns: {e}")

    async def adjust_confidence(
        self,
        action_type: str,
        base_confidence: float,
        observation: str,
    ) -> tuple[float, str]:
        """
        Adjust confidence based on historical outcomes.

        Args:
            action_type: Type of action being considered
            base_confidence: Original confidence from decision engine
            observation: Current observation

        Returns:
            Tuple of (adjusted_confidence, reasoning)
        """
        if not self.config.enable_confidence_adjustment:
            return base_confidence, "Confidence adjustment disabled"

        return await self.outcome_tracker.calculate_confidence_adjustment(
            action_type=action_type,
            base_confidence=base_confidence,
            observation=observation,
        )

    async def get_suggestions(
        self,
        observation: str,
    ) -> list[Suggestion]:
        """
        Get action suggestions based on learned patterns.

        Args:
            observation: Current observation

        Returns:
            List of suggestions sorted by confidence
        """
        suggestions = await self.pattern_learner.suggest_from_patterns(
            observation=observation,
            max_suggestions=self.config.max_suggestions,
        )

        # Filter by minimum confidence
        return [
            s for s in suggestions
            if s.confidence >= self.config.min_suggestion_confidence
        ]

    async def get_success_rate(
        self,
        action_type: str,
        time_window_hours: Optional[float] = None,
    ) -> tuple[float, int]:
        """
        Get historical success rate for an action type.

        Args:
            action_type: Action type to check
            time_window_hours: Optional time window

        Returns:
            Tuple of (success_rate, total_count)
        """
        return await self.outcome_tracker.get_success_rate(
            action_type=action_type,
            time_window_hours=time_window_hours,
        )

    async def get_action_statistics(self) -> dict[str, dict[str, Any]]:
        """Get statistics for all action types."""
        return await self.outcome_tracker.get_action_statistics()

    async def get_learning_status(self) -> dict[str, Any]:
        """Get overall learning system status."""
        pattern_stats = await self.pattern_learner.get_statistics()
        action_stats = await self.outcome_tracker.get_action_statistics()

        return {
            "initialized": self._initialized,
            "decision_count": self._decision_count,
            "last_pattern_update": self._last_pattern_update,
            "pattern_statistics": pattern_stats,
            "action_statistics": action_stats,
            "config": {
                "record_outcomes": self.config.record_all_outcomes,
                "confidence_adjustment": self.config.enable_confidence_adjustment,
                "pattern_update_interval": self.config.pattern_update_interval,
            },
        }

    async def cleanup(self) -> dict[str, int]:
        """
        Clean up old data.

        Returns:
            Dictionary with cleanup counts
        """
        outcomes_cleaned = await self.outcome_tracker.cleanup_old_outcomes(
            max_age_days=self.config.max_outcome_age_days,
            max_entries=self.config.max_outcomes,
        )

        patterns_cleaned = await self.pattern_learner.cleanup_stale_patterns()

        return {
            "outcomes_cleaned": outcomes_cleaned,
            "patterns_cleaned": patterns_cleaned,
        }

    async def force_pattern_update(self) -> int:
        """Force an immediate pattern update."""
        return await self.pattern_learner.update_patterns()

    async def get_recent_outcomes(
        self,
        limit: int = 20,
        action_type: Optional[str] = None,
    ) -> list[Outcome]:
        """Get recent outcomes."""
        return await self.outcome_tracker.get_recent_outcomes(
            limit=limit,
            action_type=action_type,
        )


# Convenience function for creating integration with daemon
def create_learning_integration(
    state_db_path: str | Path,
    config: Optional[LearningConfig] = None,
) -> LearningIntegration:
    """
    Create a LearningIntegration instance for use with the daemon.

    Args:
        state_db_path: Path to the state database (same as StateManager uses)
        config: Optional learning configuration

    Returns:
        Configured LearningIntegration instance
    """
    return LearningIntegration(
        db_path=state_db_path,
        config=config,
    )
