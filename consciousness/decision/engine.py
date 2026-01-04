"""
Autonomous Decision Engine

Main orchestrator for fully autonomous decision-making.
The LLM has complete freedom to generate any action that makes sense.
Templates serve only as few-shot examples, not constraints.

OBSERVE -> THINK -> DECIDE -> ACT
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, TYPE_CHECKING, Any

if TYPE_CHECKING:
    from consciousness.thinker import ConsciousnessThinker, Decision, Action
    from consciousness.watcher import FileChange

from .categories import (
    ObservationCategory,
    CategorizedChanges,
    categorize_changes,
    format_categorized_for_llm,
)
from .actions import (
    ActionTemplate,
    ActionMatch,
    BUILT_IN_ACTIONS,
    match_actions,
)
from .evaluator import (
    ActionEvaluator,
    EvaluationResult,
    MultiActionEvaluation,
)

logger = logging.getLogger(__name__)


@dataclass
class DecisionContext:
    """Context information for decision making."""

    changes: list["FileChange"]
    categorized: CategorizedChanges
    matches: list[ActionMatch]
    evaluation: Optional[MultiActionEvaluation] = None
    file_contents: dict[str, str] = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    git_status: str = ""
    learned_patterns: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "change_count": len(self.changes),
            "categories": self.categorized.summary(),
            "match_count": len(self.matches),
            "matched_actions": [m.template.name for m in self.matches],
            "evaluation": self.evaluation.to_dict() if self.evaluation else None,
            "has_file_contents": len(self.file_contents) > 0,
            "has_git_status": bool(self.git_status),
            "learned_pattern_count": len(self.learned_patterns),
            "metadata": self.metadata,
        }


@dataclass
class EngineDecision:
    """Final decision from the engine - fully autonomous."""

    should_act: bool
    action: Optional["Action"] = None  # Now uses thinker.Action, not templates
    prompt: str = ""
    confidence: float = 0.0
    reasoning: str = ""
    observation_summary: str = ""
    expected_outcome: str = ""
    context: Optional[DecisionContext] = None
    executor_type: str = "claude_code"
    priority: int = 5
    timestamp: float = field(default_factory=time.time)

    # For backward compatibility with template-based system
    action_match: Optional[ActionMatch] = None
    action_template: Optional[ActionTemplate] = None

    def to_dict(self) -> dict:
        return {
            "should_act": self.should_act,
            "action": self.action.to_dict() if self.action else None,
            "prompt": self.prompt[:500] + "..." if len(self.prompt) > 500 else self.prompt,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "observation_summary": self.observation_summary,
            "expected_outcome": self.expected_outcome,
            "executor_type": self.executor_type,
            "priority": self.priority,
            "timestamp": self.timestamp,
            "context": self.context.to_dict() if self.context else None,
        }

    @classmethod
    def no_action(cls, reasoning: str, context: Optional[DecisionContext] = None) -> "EngineDecision":
        """Create a decision indicating no action needed."""
        return cls(
            should_act=False,
            reasoning=reasoning,
            context=context,
        )


class AutonomousEngine:
    """
    Fully autonomous decision engine.

    The LLM is given complete freedom to decide what actions to take.
    Templates are used only as few-shot examples to inspire the LLM,
    not as constraints on what actions are possible.

    Flow:
    1. Gather all observations (file changes, git status, etc.)
    2. Retrieve learned patterns from past successes
    3. Let LLM reason freely about what to do
    4. Return the decision for execution
    """

    def __init__(
        self,
        thinker: "ConsciousnessThinker",
        confidence_threshold: float = 0.5,  # Lower threshold for autonomous mode
        working_dir: Optional[Path] = None,
        enable_learning: bool = True,
    ):
        """
        Initialize the autonomous decision engine.

        Args:
            thinker: ConsciousnessThinker for LLM reasoning
            confidence_threshold: Minimum confidence to execute
            working_dir: Working directory for file operations
            enable_learning: Whether to use learned patterns
        """
        self.thinker = thinker
        self.confidence_threshold = confidence_threshold
        self.working_dir = working_dir or Path.cwd()
        self.enable_learning = enable_learning

        # For building few-shot examples
        self.example_templates = BUILT_IN_ACTIONS[:3]  # Just a few examples

        # Statistics
        self._decisions_made = 0
        self._actions_taken = 0

    async def decide(
        self,
        observations: str,
        git_status: Optional[str] = None,
        learned_patterns: Optional[list[str]] = None,
        additional_context: Optional[dict] = None,
    ) -> EngineDecision:
        """
        Make a fully autonomous decision about what to do.

        No template matching - the LLM decides freely.

        Args:
            observations: Formatted string of file changes and observations
            git_status: Current git status output
            learned_patterns: Patterns learned from successful past actions
            additional_context: Any additional context

        Returns:
            EngineDecision with freely-generated action
        """
        self._decisions_made += 1
        start_time = time.time()

        # Build context for the decision
        context = {
            "working_dir": str(self.working_dir),
            "decision_number": self._decisions_made,
            "actions_taken_so_far": self._actions_taken,
            **(additional_context or {})
        }

        # Let the LLM think autonomously
        logger.debug("Autonomous thinking about observations...")

        decision = await self.thinker.think_autonomous(
            observations=observations,
            git_status=git_status,
            learned_patterns=learned_patterns or [],
            context=context,
        )

        # Convert thinker Decision to EngineDecision
        from consciousness.thinker import DecisionType, ActionType

        should_act = (
            decision.decision == DecisionType.ACT
            and decision.confidence >= self.confidence_threshold
        )

        if should_act:
            self._actions_taken += 1

        # Determine executor type from action
        executor_type = "claude_code"
        priority = 5
        prompt = ""

        if decision.action:
            action_type = decision.action.type

            # Map action types to executors
            if action_type == ActionType.CLAUDE_FLOW:
                executor_type = "claude_flow"
                prompt = decision.action.prompt or decision.action.description
            elif action_type == ActionType.CLAUDE_CODE:
                executor_type = "claude_code"
                prompt = decision.action.prompt or decision.action.description
            elif action_type in (ActionType.WRITE_FILE, ActionType.RUN_PYTHON, ActionType.RUN_BASH):
                executor_type = "direct"
                prompt = decision.action.description
            elif action_type in (ActionType.THINK, ActionType.DEBATE, ActionType.RESEARCH):
                executor_type = "cognitive"
                prompt = decision.action.description
            else:
                executor_type = "custom"
                prompt = decision.action.description

            # Map priority
            from consciousness.thinker import Priority
            priority_map = {
                Priority.CRITICAL: 1,
                Priority.HIGH: 3,
                Priority.MEDIUM: 5,
                Priority.LOW: 7,
            }
            priority = priority_map.get(decision.action.priority, 5)

        duration = time.time() - start_time

        logger.info(
            f"Autonomous decision: {'ACT' if should_act else 'WAIT'} "
            f"(confidence: {decision.confidence:.2f}, duration: {duration:.2f}s)"
        )

        return EngineDecision(
            should_act=should_act,
            action=decision.action,
            prompt=prompt,
            confidence=decision.confidence,
            reasoning=decision.reasoning,
            observation_summary=decision.observation_summary,
            expected_outcome=decision.expected_outcome,
            executor_type=executor_type,
            priority=priority,
        )

    def get_statistics(self) -> dict:
        """Get engine statistics."""
        return {
            "decisions_made": self._decisions_made,
            "actions_taken": self._actions_taken,
            "action_rate": self._actions_taken / max(self._decisions_made, 1),
            "confidence_threshold": self.confidence_threshold,
            "learning_enabled": self.enable_learning,
        }


class DecisionEngine:
    """
    Hybrid decision engine supporting both autonomous and template-based modes.

    Can operate in:
    1. AUTONOMOUS mode: LLM decides freely (recommended)
    2. TEMPLATE mode: Match against templates (legacy)
    3. HYBRID mode: Templates inform but don't constrain
    """

    def __init__(
        self,
        thinker: "ConsciousnessThinker",
        actions: Optional[list[ActionTemplate]] = None,
        confidence_threshold: float = 0.6,
        enable_quick_mode: bool = True,
        max_actions_to_evaluate: int = 5,
        read_file_contents: bool = True,
        working_dir: Optional[Path] = None,
        mode: str = "autonomous",  # "autonomous", "template", "hybrid"
    ):
        """
        Initialize the decision engine.

        Args:
            thinker: ConsciousnessThinker for LLM evaluation
            actions: List of action templates (for template/hybrid modes)
            confidence_threshold: Minimum confidence to execute
            enable_quick_mode: Use heuristics for obvious cases
            max_actions_to_evaluate: Limit actions sent to LLM
            read_file_contents: Whether to read file contents for prompts
            working_dir: Working directory for file operations
            mode: Operating mode ("autonomous", "template", "hybrid")
        """
        self.thinker = thinker
        self.actions = actions or BUILT_IN_ACTIONS
        self.confidence_threshold = confidence_threshold
        self.enable_quick_mode = enable_quick_mode
        self.max_actions_to_evaluate = max_actions_to_evaluate
        self.read_file_contents = read_file_contents
        self.working_dir = working_dir or Path.cwd()
        self.mode = mode

        # Autonomous engine for autonomous/hybrid modes
        self.autonomous_engine = AutonomousEngine(
            thinker=thinker,
            confidence_threshold=confidence_threshold,
            working_dir=working_dir,
        )

        # Template evaluator for template/hybrid modes
        self.evaluator = ActionEvaluator(thinker, confidence_threshold)

        # Track action cooldowns
        self._action_last_executed: dict[str, float] = {}

    def _is_on_cooldown(self, template: ActionTemplate) -> bool:
        """Check if an action is on cooldown."""
        last_time = self._action_last_executed.get(template.name)
        if last_time is None:
            return False

        elapsed = time.time() - last_time
        return elapsed < template.cooldown_seconds

    def _filter_cooldown_actions(self, matches: list[ActionMatch]) -> list[ActionMatch]:
        """Filter out actions that are on cooldown."""
        return [m for m in matches if not self._is_on_cooldown(m.template)]

    def mark_action_executed(self, action_name: str) -> None:
        """Mark an action as executed (for cooldown tracking)."""
        self._action_last_executed[action_name] = time.time()

    async def _read_file_content(self, path: str) -> Optional[str]:
        """Read content of a file if it exists."""
        try:
            full_path = self.working_dir / path
            if full_path.exists() and full_path.is_file():
                size = full_path.stat().st_size
                if size > 50000:
                    return f"[File too large: {size} bytes]"
                return full_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.warning(f"Failed to read {path}: {e}")
        return None

    async def _gather_file_contents(
        self,
        matches: list[ActionMatch],
    ) -> dict[str, str]:
        """Gather file contents for actions that require them."""
        contents = {}

        for match in matches:
            if match.template.requires_content:
                for file_path in match.matched_files[:match.template.max_files]:
                    if file_path not in contents:
                        content = await self._read_file_content(file_path)
                        if content:
                            contents[file_path] = content

        return contents

    def _render_action_prompt(
        self,
        match: ActionMatch,
        file_contents: dict[str, str],
    ) -> str:
        """Render the action prompt with all context."""
        template = match.template
        context = match.get_prompt_context()

        if template.requires_content and match.matched_files:
            primary_file = match.matched_files[0]
            if primary_file in file_contents:
                context["file_content"] = file_contents[primary_file]
            else:
                context["file_content"] = "[Content not available]"

        if len(match.matched_files) > 1:
            content_parts = []
            for f in match.matched_files[:template.max_files]:
                if f in file_contents:
                    content_parts.append(f"--- {f} ---\n{file_contents[f]}")
            if content_parts:
                context["all_file_contents"] = "\n\n".join(content_parts)

        return template.render_prompt(**context)

    async def process(
        self,
        changes: list["FileChange"],
        additional_context: Optional[dict] = None,
        git_status: Optional[str] = None,
        learned_patterns: Optional[list[str]] = None,
    ) -> EngineDecision:
        """
        Process file changes and produce a decision.

        This is the main entry point for the decision engine.
        Behavior depends on the operating mode.

        Args:
            changes: List of file changes to process
            additional_context: Optional additional context for evaluation
            git_status: Current git status (for autonomous mode)
            learned_patterns: Learned patterns (for autonomous mode)

        Returns:
            EngineDecision with action recommendation
        """
        logger.debug(f"Processing {len(changes)} file changes in {self.mode} mode")

        # Autonomous mode: bypass templates entirely
        if self.mode == "autonomous":
            # Format changes for LLM
            from consciousness.watcher import ConsciousnessWatcher
            watcher = ConsciousnessWatcher(root_path=self.working_dir)
            observations = watcher.format_for_llm(changes)

            return await self.autonomous_engine.decide(
                observations=observations,
                git_status=git_status,
                learned_patterns=learned_patterns,
                additional_context=additional_context,
            )

        # Template or Hybrid mode: use template matching
        return await self._process_template_mode(
            changes, additional_context, git_status, learned_patterns
        )

    async def _process_template_mode(
        self,
        changes: list["FileChange"],
        additional_context: Optional[dict] = None,
        git_status: Optional[str] = None,
        learned_patterns: Optional[list[str]] = None,
    ) -> EngineDecision:
        """Process using template matching (legacy mode)."""
        # Step 1: Categorize changes
        categorized = categorize_changes(changes)

        if categorized.is_empty():
            logger.debug("All changes categorized as noise, skipping")
            return EngineDecision.no_action(
                "All observed changes are noise (temp files, logs, etc.)",
                DecisionContext(changes=changes, categorized=categorized, matches=[]),
            )

        # Step 2: Match against action templates
        all_matches = match_actions(changes, self.actions)
        matches = self._filter_cooldown_actions(all_matches)

        if not matches:
            reason = "No action templates match the observed changes"
            if len(all_matches) > len(matches):
                reason = f"Matched actions are on cooldown ({len(all_matches)} matches filtered)"

            # In hybrid mode, fall back to autonomous
            if self.mode == "hybrid":
                from consciousness.watcher import ConsciousnessWatcher
                watcher = ConsciousnessWatcher(root_path=self.working_dir)
                observations = watcher.format_for_llm(changes)

                return await self.autonomous_engine.decide(
                    observations=observations,
                    git_status=git_status,
                    learned_patterns=learned_patterns,
                    additional_context=additional_context,
                )

            return EngineDecision.no_action(
                reason,
                DecisionContext(changes=changes, categorized=categorized, matches=all_matches),
            )

        logger.debug(f"Found {len(matches)} matching actions")

        # Step 3: Gather file contents if needed
        file_contents = {}
        if self.read_file_contents:
            file_contents = await self._gather_file_contents(matches)

        # Create decision context
        context = DecisionContext(
            changes=changes,
            categorized=categorized,
            matches=matches,
            file_contents=file_contents,
            metadata=additional_context or {},
            git_status=git_status or "",
            learned_patterns=learned_patterns or [],
        )

        # Step 4: Quick mode for obvious cases
        if self.enable_quick_mode and len(matches) == 1:
            match = matches[0]
            should_exec, quick_conf = await self.evaluator.quick_evaluate(match, changes)

            if should_exec and quick_conf >= match.template.min_confidence:
                logger.debug(f"Quick mode: executing {match.template.name}")
                prompt = self._render_action_prompt(match, file_contents)

                return EngineDecision(
                    should_act=True,
                    action_template=match.template,
                    action_match=match,
                    prompt=prompt,
                    confidence=quick_conf,
                    reasoning=f"Quick evaluation: pattern match with confidence {quick_conf:.2f}",
                    context=context,
                    executor_type=match.template.executor_type,
                    priority=match.template.priority,
                )

        # Step 5: Full LLM evaluation
        matches_to_evaluate = matches[:self.max_actions_to_evaluate]

        evaluation = await self.evaluator.evaluate_multiple(
            matches_to_evaluate,
            changes,
            categorized,
            additional_context,
        )

        context.evaluation = evaluation

        if not evaluation.should_act or not evaluation.recommended_action:
            return EngineDecision.no_action(
                evaluation.overall_reasoning,
                context,
            )

        # Step 6: Build final decision
        recommended = evaluation.recommended_action
        action_match = None
        for match in matches:
            if match.template.name == recommended.action_name:
                action_match = match
                break

        if not action_match:
            return EngineDecision.no_action(
                f"Could not find action match for {recommended.action_name}",
                context,
            )

        prompt = self._render_action_prompt(action_match, file_contents)
        if recommended.modified_prompt:
            prompt = recommended.modified_prompt

        final_priority = action_match.template.priority + recommended.priority_adjustment

        return EngineDecision(
            should_act=True,
            action_template=action_match.template,
            action_match=action_match,
            prompt=prompt,
            confidence=recommended.confidence,
            reasoning=recommended.reasoning,
            context=context,
            executor_type=action_match.template.executor_type,
            priority=max(1, final_priority),
        )

    async def process_batch(
        self,
        changes: list["FileChange"],
        max_decisions: int = 3,
    ) -> list[EngineDecision]:
        """
        Process changes and return multiple decisions if appropriate.

        Useful when changes span multiple unrelated areas that
        can be handled in parallel.
        """
        categorized = categorize_changes(changes)

        if categorized.is_empty():
            return []

        category_groups: dict[ObservationCategory, list["FileChange"]] = {}
        for category in ObservationCategory:
            if category != ObservationCategory.NOISE:
                cat_changes = categorized[category]
                if cat_changes:
                    category_groups[category] = cat_changes

        decisions = []
        for category, cat_changes in category_groups.items():
            if len(decisions) >= max_decisions:
                break

            decision = await self.process(cat_changes)
            if decision.should_act:
                decisions.append(decision)

        return decisions

    def add_action(self, action: ActionTemplate) -> None:
        """Add a new action template."""
        self.actions = [a for a in self.actions if a.name != action.name]
        self.actions.append(action)

    def remove_action(self, name: str) -> bool:
        """Remove an action template by name."""
        original_len = len(self.actions)
        self.actions = [a for a in self.actions if a.name != name]
        return len(self.actions) < original_len

    def get_action_status(self) -> dict:
        """Get status of all actions including cooldowns."""
        now = time.time()
        status = {}

        for action in self.actions:
            last_exec = self._action_last_executed.get(action.name)
            if last_exec:
                elapsed = now - last_exec
                on_cooldown = elapsed < action.cooldown_seconds
                remaining = max(0, action.cooldown_seconds - elapsed)
            else:
                on_cooldown = False
                remaining = 0

            status[action.name] = {
                "priority": action.priority,
                "min_confidence": action.min_confidence,
                "cooldown_seconds": action.cooldown_seconds,
                "on_cooldown": on_cooldown,
                "cooldown_remaining": remaining,
                "executor_type": action.executor_type,
                "tags": action.tags,
            }

        return status


async def create_engine(
    thinker: "ConsciousnessThinker",
    custom_actions: Optional[list[ActionTemplate]] = None,
    mode: str = "autonomous",
    **kwargs,
) -> DecisionEngine:
    """
    Factory function to create a configured DecisionEngine.

    Args:
        thinker: ConsciousnessThinker instance
        custom_actions: Optional custom actions to add
        mode: Operating mode ("autonomous", "template", "hybrid")
        **kwargs: Additional DecisionEngine parameters

    Returns:
        Configured DecisionEngine
    """
    actions = BUILT_IN_ACTIONS.copy()
    if custom_actions:
        actions.extend(custom_actions)

    return DecisionEngine(
        thinker=thinker,
        actions=actions,
        mode=mode,
        **kwargs,
    )
