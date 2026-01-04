"""
Decision Evaluator - OIDA Loop Decision Gate

Implements the metacognitive gate (ARCH-006) that determines whether
a decision should be executed or if more information is needed.

Decision Criteria:
1. Significance > 0.3 (observation is meaningful)
2. Confidence > 0.7 (high certainty in decision)
3. Coherence with goals (action aligns with objectives)
4. Capability (action is feasible)
5. Resources available (within concurrency limits)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from ..inference.lm_studio import Decision, DecisionType


class GateResult(Enum):
    """Result of passing through the metacognitive gate."""
    PASS = "pass"           # Execute the action
    BLOCK_LOW_CONFIDENCE = "block_low_confidence"  # Need more information
    BLOCK_LOW_SIGNIFICANCE = "block_low_significance"  # Not important enough
    BLOCK_GOAL_CONFLICT = "block_goal_conflict"  # Conflicts with goals
    BLOCK_RESOURCES = "block_resources"  # No resources available
    BLOCK_DRY_RUN = "block_dry_run"  # Dry run mode


@dataclass
class EvaluationResult:
    """Result of decision evaluation."""
    gate_result: GateResult
    should_execute: bool
    decision: Decision
    reason: str
    scores: dict[str, float]

    @property
    def passed(self) -> bool:
        return self.gate_result == GateResult.PASS


class DecisionEvaluator:
    """
    Evaluates decisions against the metacognitive gate criteria.

    Implements Expected Free Energy principles:
    - Pragmatic value: Does this help achieve goals?
    - Epistemic value: Does this reduce uncertainty?
    """

    def __init__(
        self,
        min_confidence: float = 0.7,
        min_significance: float = 0.3,
        max_concurrent_tasks: int = 5,
        dry_run: bool = False,
    ):
        self.min_confidence = min_confidence
        self.min_significance = min_significance
        self.max_concurrent_tasks = max_concurrent_tasks
        self.dry_run = dry_run
        self._active_task_count = 0

    def evaluate(
        self,
        decision: Decision,
        current_goals: Optional[list[str]] = None,
        active_tasks: int = 0,
    ) -> EvaluationResult:
        """
        Evaluate a decision against all gate criteria.

        Returns EvaluationResult indicating whether to execute.
        """
        self._active_task_count = active_tasks
        current_goals = current_goals or []

        scores = {
            "confidence": decision.confidence,
            "goal_coherence": self._calculate_goal_coherence(decision, current_goals),
            "resource_availability": self._calculate_resource_availability(),
            "epistemic_value": self._calculate_epistemic_value(decision),
        }

        # Check dry run mode first
        if self.dry_run:
            return EvaluationResult(
                gate_result=GateResult.BLOCK_DRY_RUN,
                should_execute=False,
                decision=decision,
                reason="Dry run mode enabled - action logged but not executed",
                scores=scores,
            )

        # Only "act" decisions go through the gate
        if decision.decision != DecisionType.ACT:
            return EvaluationResult(
                gate_result=GateResult.PASS,
                should_execute=False,  # No action needed for wait/investigate
                decision=decision,
                reason=f"Decision type is {decision.decision.value}, no action required",
                scores=scores,
            )

        # Gate 1: Confidence threshold (ARCH-006)
        if decision.confidence < self.min_confidence:
            return EvaluationResult(
                gate_result=GateResult.BLOCK_LOW_CONFIDENCE,
                should_execute=False,
                decision=decision,
                reason=f"Confidence {decision.confidence:.2f} below threshold {self.min_confidence}",
                scores=scores,
            )

        # Gate 2: Resource availability
        if scores["resource_availability"] < 0.5:
            return EvaluationResult(
                gate_result=GateResult.BLOCK_RESOURCES,
                should_execute=False,
                decision=decision,
                reason=f"Resource availability too low ({scores['resource_availability']:.2f})",
                scores=scores,
            )

        # Gate 3: Goal coherence
        if scores["goal_coherence"] < 0.3:
            return EvaluationResult(
                gate_result=GateResult.BLOCK_GOAL_CONFLICT,
                should_execute=False,
                decision=decision,
                reason=f"Action conflicts with current goals (coherence: {scores['goal_coherence']:.2f})",
                scores=scores,
            )

        # All gates passed
        return EvaluationResult(
            gate_result=GateResult.PASS,
            should_execute=True,
            decision=decision,
            reason="All gate criteria satisfied",
            scores=scores,
        )

    def _calculate_goal_coherence(
        self,
        decision: Decision,
        current_goals: list[str],
    ) -> float:
        """
        Calculate how well the action aligns with current goals.

        Uses simple keyword matching for now - can be enhanced with embeddings.
        """
        if not current_goals or not decision.action:
            return 0.5  # Neutral if no goals or no action

        action_text = f"{decision.action.description} {decision.action.prompt}".lower()

        # Count goal keyword matches
        matches = 0
        for goal in current_goals:
            goal_words = goal.lower().split()
            for word in goal_words:
                if len(word) > 3 and word in action_text:
                    matches += 1

        # Normalize to 0-1
        max_possible = sum(len(g.split()) for g in current_goals)
        if max_possible == 0:
            return 0.5

        return min(1.0, 0.5 + (matches / max_possible) * 0.5)

    def _calculate_resource_availability(self) -> float:
        """Calculate available resource capacity."""
        if self._active_task_count >= self.max_concurrent_tasks:
            return 0.0

        utilization = self._active_task_count / self.max_concurrent_tasks
        return 1.0 - utilization

    def _calculate_epistemic_value(self, decision: Decision) -> float:
        """
        Calculate the information value of taking this action.

        Based on Free Energy Principle: actions that reduce uncertainty
        have high epistemic value.
        """
        # Use uncertainty sources as a proxy
        uncertainty_count = len(decision.self_assessment.uncertainty_sources)

        if decision.decision == DecisionType.INVESTIGATE:
            # Investigation has high epistemic value
            return 0.8 + (0.2 * min(1.0, uncertainty_count / 3))

        if decision.decision == DecisionType.ACT and decision.action:
            # Actions have moderate epistemic value based on uncertainty reduction
            if uncertainty_count == 0:
                return 0.5  # Already certain, low epistemic value
            return 0.6 + (0.3 * min(1.0, uncertainty_count / 5))

        return 0.5  # Wait has neutral epistemic value

    def update_active_tasks(self, count: int) -> None:
        """Update the count of active tasks."""
        self._active_task_count = count
