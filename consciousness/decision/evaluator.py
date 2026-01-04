"""
Action Evaluator

Uses LLM (via ConsciousnessThinker) to evaluate potential actions
and return confidence scores for execution decisions.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from consciousness.thinker import ConsciousnessThinker
    from consciousness.watcher import FileChange

from .actions import ActionMatch, ActionTemplate
from .categories import ObservationCategory, CategorizedChanges

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Result of evaluating a single action."""

    action_name: str
    should_execute: bool
    confidence: float
    reasoning: str
    modified_prompt: Optional[str] = None
    priority_adjustment: int = 0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "action_name": self.action_name,
            "should_execute": self.should_execute,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "modified_prompt": self.modified_prompt,
            "priority_adjustment": self.priority_adjustment,
            "metadata": self.metadata,
        }


@dataclass
class MultiActionEvaluation:
    """Result of evaluating multiple potential actions."""

    evaluations: list[EvaluationResult]
    recommended_action: Optional[EvaluationResult] = None
    should_act: bool = False
    overall_reasoning: str = ""

    def get_executable_actions(self) -> list[EvaluationResult]:
        """Get actions that should be executed, sorted by confidence."""
        return sorted(
            [e for e in self.evaluations if e.should_execute],
            key=lambda e: e.confidence,
            reverse=True
        )

    def to_dict(self) -> dict:
        return {
            "evaluations": [e.to_dict() for e in self.evaluations],
            "recommended_action": self.recommended_action.to_dict() if self.recommended_action else None,
            "should_act": self.should_act,
            "overall_reasoning": self.overall_reasoning,
        }


EVALUATION_PROMPT = """You are evaluating potential actions for a file system consciousness daemon.

Given the observed file changes and a potential action, determine if the action should be executed.

## Observed Changes
{changes_summary}

## Potential Action
Name: {action_name}
Description: {action_description}
Trigger Pattern: {trigger_pattern}
Matched Files: {matched_files}
Minimum Confidence Required: {min_confidence}

## Action Prompt Template
```
{prompt_template}
```

## Evaluation Criteria
1. Is this action appropriate for the observed changes?
2. Will executing this action provide value?
3. Is the timing right (not too soon after similar action)?
4. Are there any risks or concerns?

## Your Task
Respond with a JSON object:
```json
{{
    "should_execute": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "Your reasoning for this decision",
    "modified_prompt": "Optional: improved version of the action prompt",
    "priority_adjustment": 0
}}
```

The `confidence` should reflect how certain you are that this action is appropriate.
The `priority_adjustment` can be -2 to +2 to adjust execution order (negative = higher priority).
Only provide `modified_prompt` if you have specific improvements to suggest.
"""

MULTI_ACTION_PROMPT = """You are evaluating multiple potential actions for a file system consciousness daemon.

Given the observed file changes and multiple potential actions, determine which (if any) should be executed.

## Observed Changes
{changes_summary}

## Potential Actions
{actions_list}

## Evaluation Task
For each action, determine:
1. Should it be executed? (considering the other actions too)
2. What's your confidence level?
3. What's the priority order?

Consider:
- Actions may overlap or conflict
- Some actions may be redundant if others are executed
- Resource constraints (don't recommend too many simultaneous actions)
- Dependency order (some actions should complete before others)

## Response Format
Respond with a JSON object:
```json
{{
    "overall_reasoning": "Your high-level analysis",
    "should_act": true/false,
    "recommended_action": "name of the single best action to execute",
    "evaluations": [
        {{
            "action_name": "action_name",
            "should_execute": true/false,
            "confidence": 0.0-1.0,
            "reasoning": "Why this action should/shouldn't run",
            "priority_adjustment": 0
        }}
    ]
}}
```
"""


class ActionEvaluator:
    """
    Evaluates potential actions using LLM reasoning.

    Uses the ConsciousnessThinker to analyze file changes and determine
    which actions should be executed with what confidence.
    """

    def __init__(
        self,
        thinker: "ConsciousnessThinker",
        default_confidence_threshold: float = 0.6,
    ):
        """
        Initialize the evaluator.

        Args:
            thinker: ConsciousnessThinker instance for LLM evaluation
            default_confidence_threshold: Default minimum confidence to recommend execution
        """
        self.thinker = thinker
        self.default_confidence_threshold = default_confidence_threshold

    def _format_changes_summary(
        self,
        changes: list["FileChange"],
        categorized: Optional[CategorizedChanges] = None,
    ) -> str:
        """Format changes into a summary string."""
        lines = []

        if categorized:
            summary = categorized.summary()
            lines.append(f"Total changes: {sum(summary.values())}")
            lines.append(f"Breakdown: {json.dumps(summary)}")
            lines.append("")

        for change in changes[:20]:  # Limit to first 20
            symbol = {"created": "+", "modified": "~", "deleted": "-"}.get(
                change.change_type, "?"
            )
            lines.append(f"{symbol} {change.relative_path}")

        if len(changes) > 20:
            lines.append(f"... and {len(changes) - 20} more files")

        return "\n".join(lines)

    def _format_action_for_prompt(self, match: ActionMatch) -> str:
        """Format an action match for the evaluation prompt."""
        template = match.template
        return f"""- **{template.name}**: {template.description}
  Pattern: {template.trigger_pattern}
  Matched {len(match.matched_files)} files: {', '.join(match.matched_files[:5])}{'...' if len(match.matched_files) > 5 else ''}
  Min confidence: {template.min_confidence}, Priority: {template.priority}"""

    async def evaluate_single(
        self,
        match: ActionMatch,
        changes: list["FileChange"],
        categorized: Optional[CategorizedChanges] = None,
        context: Optional[dict] = None,
    ) -> EvaluationResult:
        """
        Evaluate a single action match.

        Args:
            match: The action match to evaluate
            changes: All file changes
            categorized: Optional categorized changes
            context: Optional additional context

        Returns:
            EvaluationResult with decision and confidence
        """
        template = match.template

        prompt = EVALUATION_PROMPT.format(
            changes_summary=self._format_changes_summary(changes, categorized),
            action_name=template.name,
            action_description=template.description,
            trigger_pattern=template.trigger_pattern,
            matched_files=", ".join(match.matched_files[:10]),
            min_confidence=template.min_confidence,
            prompt_template=template.prompt_template,
        )

        try:
            decision = await self.thinker.think(prompt, context)

            # Parse the response
            if decision.raw_response:
                try:
                    data = json.loads(decision.raw_response)

                    confidence = float(data.get("confidence", 0.5))
                    should_execute = (
                        data.get("should_execute", False) and
                        confidence >= template.min_confidence
                    )

                    return EvaluationResult(
                        action_name=template.name,
                        should_execute=should_execute,
                        confidence=confidence,
                        reasoning=data.get("reasoning", decision.reasoning),
                        modified_prompt=data.get("modified_prompt"),
                        priority_adjustment=int(data.get("priority_adjustment", 0)),
                        metadata={
                            "matched_files": match.matched_files,
                            "change_types": match.change_types,
                        }
                    )
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    logger.warning(f"Failed to parse evaluation response: {e}")

            # Fallback: use decision confidence
            return EvaluationResult(
                action_name=template.name,
                should_execute=decision.confidence >= template.min_confidence,
                confidence=decision.confidence,
                reasoning=decision.reasoning,
                metadata={
                    "parse_error": True,
                    "matched_files": match.matched_files,
                }
            )

        except Exception as e:
            logger.error(f"Evaluation failed for {template.name}: {e}")
            return EvaluationResult(
                action_name=template.name,
                should_execute=False,
                confidence=0.0,
                reasoning=f"Evaluation error: {str(e)}",
                metadata={"error": str(e)}
            )

    async def evaluate_multiple(
        self,
        matches: list[ActionMatch],
        changes: list["FileChange"],
        categorized: Optional[CategorizedChanges] = None,
        context: Optional[dict] = None,
    ) -> MultiActionEvaluation:
        """
        Evaluate multiple potential actions together.

        This considers interactions between actions and recommends
        the optimal set to execute.

        Args:
            matches: List of action matches to evaluate
            changes: All file changes
            categorized: Optional categorized changes
            context: Optional additional context

        Returns:
            MultiActionEvaluation with recommendations
        """
        if not matches:
            return MultiActionEvaluation(
                evaluations=[],
                should_act=False,
                overall_reasoning="No actions matched the observed changes.",
            )

        if len(matches) == 1:
            # Single action - use simple evaluation
            result = await self.evaluate_single(
                matches[0], changes, categorized, context
            )
            return MultiActionEvaluation(
                evaluations=[result],
                recommended_action=result if result.should_execute else None,
                should_act=result.should_execute,
                overall_reasoning=result.reasoning,
            )

        # Multiple actions - evaluate together
        actions_list = "\n".join(
            self._format_action_for_prompt(m) for m in matches
        )

        prompt = MULTI_ACTION_PROMPT.format(
            changes_summary=self._format_changes_summary(changes, categorized),
            actions_list=actions_list,
        )

        try:
            decision = await self.thinker.think(prompt, context)

            if decision.raw_response:
                try:
                    data = json.loads(decision.raw_response)

                    evaluations = []
                    for eval_data in data.get("evaluations", []):
                        # Find the matching template
                        template = None
                        for match in matches:
                            if match.template.name == eval_data.get("action_name"):
                                template = match.template
                                break

                        min_conf = template.min_confidence if template else self.default_confidence_threshold
                        confidence = float(eval_data.get("confidence", 0.5))

                        evaluations.append(EvaluationResult(
                            action_name=eval_data.get("action_name", "unknown"),
                            should_execute=(
                                eval_data.get("should_execute", False) and
                                confidence >= min_conf
                            ),
                            confidence=confidence,
                            reasoning=eval_data.get("reasoning", ""),
                            priority_adjustment=int(eval_data.get("priority_adjustment", 0)),
                        ))

                    # Find recommended action
                    recommended = None
                    recommended_name = data.get("recommended_action")
                    if recommended_name:
                        for eval_result in evaluations:
                            if eval_result.action_name == recommended_name:
                                recommended = eval_result
                                break

                    return MultiActionEvaluation(
                        evaluations=evaluations,
                        recommended_action=recommended,
                        should_act=data.get("should_act", False),
                        overall_reasoning=data.get("overall_reasoning", decision.reasoning),
                    )

                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    logger.warning(f"Failed to parse multi-action evaluation: {e}")

            # Fallback: evaluate each action individually
            evaluations = []
            for match in matches:
                result = await self.evaluate_single(match, changes, categorized, context)
                evaluations.append(result)

            executable = [e for e in evaluations if e.should_execute]
            recommended = max(executable, key=lambda e: e.confidence) if executable else None

            return MultiActionEvaluation(
                evaluations=evaluations,
                recommended_action=recommended,
                should_act=len(executable) > 0,
                overall_reasoning=decision.reasoning,
            )

        except Exception as e:
            logger.error(f"Multi-action evaluation failed: {e}")
            return MultiActionEvaluation(
                evaluations=[],
                should_act=False,
                overall_reasoning=f"Evaluation error: {str(e)}",
            )

    async def quick_evaluate(
        self,
        match: ActionMatch,
        changes: list["FileChange"],
    ) -> tuple[bool, float]:
        """
        Quick evaluation without full LLM reasoning.

        Uses heuristics for fast decisions on obvious cases.

        Args:
            match: Action match to evaluate
            changes: File changes

        Returns:
            Tuple of (should_execute, confidence)
        """
        template = match.template

        # Heuristic confidence based on match quality
        base_confidence = 0.5

        # Boost for pattern matches
        pattern_matches = sum(
            1 for f in match.matched_files
            if template.matches_path(f)
        )
        if pattern_matches > 0:
            base_confidence += 0.2

        # Boost for category matches
        if template.matches_category(match.category):
            base_confidence += 0.1

        # Boost for multiple files (indicates broader change)
        if len(match.matched_files) > 3:
            base_confidence += 0.1

        # Reduce for very broad patterns
        if "**/*" in template.trigger_pattern:
            base_confidence -= 0.1

        # Cap at 1.0
        confidence = min(base_confidence, 1.0)

        should_execute = confidence >= template.min_confidence

        return should_execute, confidence
