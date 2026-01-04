"""
Consciousness Decision Engine

This module provides the decision-making layer between observation and action.
It categorizes file changes, matches them against action templates, and uses
LLM evaluation to determine appropriate responses with confidence scores.

Components:
- categories.py: Observation categorization (ObservationCategory)
- actions.py: Action templates and definitions (ActionTemplate, BUILT_IN_ACTIONS)
- evaluator.py: LLM-based action evaluation (ActionEvaluator)
- engine.py: Main decision engine (DecisionEngine)

Usage:
    from consciousness.decision import DecisionEngine, ActionTemplate

    engine = DecisionEngine(thinker, actions)
    decision = await engine.process(changes)
"""

from .categories import (
    ObservationCategory,
    CategorizedChanges,
    categorize_changes,
    categorize_single_change,
)

from .actions import (
    ActionTemplate,
    ActionMatch,
    BUILT_IN_ACTIONS,
    match_actions,
    get_action_by_name,
)

from .evaluator import (
    ActionEvaluator,
    EvaluationResult,
    MultiActionEvaluation,
)

from .engine import (
    DecisionEngine,
    EngineDecision,
    DecisionContext,
)

__all__ = [
    # Categories
    "ObservationCategory",
    "CategorizedChanges",
    "categorize_changes",
    "categorize_single_change",
    # Actions
    "ActionTemplate",
    "ActionMatch",
    "BUILT_IN_ACTIONS",
    "match_actions",
    "get_action_by_name",
    # Evaluator
    "ActionEvaluator",
    "EvaluationResult",
    "MultiActionEvaluation",
    # Engine
    "DecisionEngine",
    "EngineDecision",
    "DecisionContext",
]
