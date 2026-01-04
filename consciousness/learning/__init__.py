"""
Learning Module for Consciousness Daemon

This module provides outcome tracking and pattern learning capabilities
to improve decision-making over time based on historical data.

Components:
- OutcomeTracker: Records and analyzes action outcomes
- PatternLearner: Extracts and applies learned patterns
- LearningIntegration: Integrates learning into the decision engine
"""

from .tracker import (
    OutcomeTracker,
    Outcome,
    OutcomeType,
)
from .patterns import (
    PatternLearner,
    Pattern,
    PatternType,
    Suggestion,
)

__all__ = [
    "OutcomeTracker",
    "Outcome",
    "OutcomeType",
    "PatternLearner",
    "Pattern",
    "PatternType",
    "Suggestion",
]
