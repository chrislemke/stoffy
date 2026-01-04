"""
Consciousness Decision - OIDA Loop Decision Phase

Implements the DECIDE phase with:
- Expected Free Energy minimization (ARCH-003)
- Confidence thresholds (ARCH-006: 0.7 threshold)
- Goal coherence checking
- Resource availability validation
"""

from .evaluator import DecisionEvaluator, EvaluationResult
from .goals import GoalManager, Goal

__all__ = [
    "DecisionEvaluator",
    "EvaluationResult",
    "GoalManager",
    "Goal",
]
