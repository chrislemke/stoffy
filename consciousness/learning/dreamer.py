"""
Dreamer - The Dream Cycle for Consciousness Maintenance & Consolidation

Triggered by:
- 60 minutes of inactivity
- 100 recorded actions

The Dream Routine:
1. RECALL - Read recent outcomes and thoughts from SQLite
2. REFLECT - Analyze with LLM (Claude/Gemini) for insights
3. CONSOLIDATE - Write distilled wisdom to knowledge/ and templates/
4. PRUNE - Clean up old episodic memory
5. PLAN - Create todo list for next wake cycle
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Protocol

import structlog
from openai import AsyncOpenAI

from .tracker import OutcomeTracker, Outcome, OutcomeType
from .patterns import PatternLearner, Pattern

logger = structlog.get_logger(__name__)


class LLMTier(str, Enum):
    """Tier classification for LLM selection during reflection."""
    LOCAL = "local"          # Tier 1: Local LM Studio (Qwen)
    CLAUDE = "claude"        # Tier 2: Claude for deep analysis
    GEMINI_FLASH = "gemini_flash"  # Tier 3: Gemini Flash for medium analysis
    GEMINI_PRO = "gemini_pro"      # Tier 4: Gemini Pro for huge logs


class DreamPhase(str, Enum):
    """Phases of the dream cycle."""
    IDLE = "idle"
    RECALL = "recall"
    REFLECT = "reflect"
    CONSOLIDATE = "consolidate"
    PRUNE = "prune"
    PLAN = "plan"
    COMPLETE = "complete"


@dataclass
class DreamerConfig:
    """Configuration for the Dreamer component."""

    # Trigger thresholds
    inactivity_minutes: int = 60
    action_threshold: int = 100

    # Recall settings
    recall_outcomes_limit: int = 200
    recall_thoughts_limit: int = 100
    recall_time_window_hours: float = 168.0  # 1 week

    # Reflection settings
    local_llm_base_url: str = "http://localhost:1234/v1"
    local_llm_model: str = "local-model"
    claude_model: str = "claude-3-5-sonnet-20241022"
    gemini_flash_model: str = "gemini-1.5-flash"
    gemini_pro_model: str = "gemini-1.5-pro"

    # Thresholds for LLM tier selection
    large_log_threshold: int = 50000  # Characters, use Gemini Pro above this
    medium_log_threshold: int = 20000  # Characters, use Gemini Flash above this

    # Consolidation settings
    knowledge_base_path: str = "knowledge"
    templates_path: str = ".hive-mind/templates"
    learned_rules_file: str = "patterns/learned_rules.md"
    min_occurrences_for_template: int = 5

    # Pruning settings
    max_outcome_age_days: int = 30
    max_outcomes: int = 10000
    max_thoughts_age_days: int = 60
    max_thoughts: int = 5000

    # Planning settings
    max_todos: int = 10

    # Safety settings
    min_time_between_dreams_minutes: int = 30
    max_dream_duration_minutes: int = 15


@dataclass
class DreamResult:
    """Result of a complete dream cycle."""

    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    phases_completed: list[DreamPhase] = field(default_factory=list)

    # Recall results
    outcomes_recalled: int = 0
    thoughts_recalled: int = 0

    # Reflection results
    insights: list[str] = field(default_factory=list)
    mistakes_identified: list[str] = field(default_factory=list)
    patterns_emerged: list[str] = field(default_factory=list)
    llm_tier_used: Optional[LLMTier] = None

    # Consolidation results
    rules_updated: int = 0
    templates_created: int = 0

    # Pruning results
    outcomes_pruned: int = 0
    thoughts_pruned: int = 0
    patterns_pruned: int = 0

    # Planning results
    todos_created: list[str] = field(default_factory=list)

    # Errors
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "phases_completed": [p.value for p in self.phases_completed],
            "outcomes_recalled": self.outcomes_recalled,
            "thoughts_recalled": self.thoughts_recalled,
            "insights": self.insights,
            "mistakes_identified": self.mistakes_identified,
            "patterns_emerged": self.patterns_emerged,
            "llm_tier_used": self.llm_tier_used.value if self.llm_tier_used else None,
            "rules_updated": self.rules_updated,
            "templates_created": self.templates_created,
            "outcomes_pruned": self.outcomes_pruned,
            "thoughts_pruned": self.thoughts_pruned,
            "patterns_pruned": self.patterns_pruned,
            "todos_created": self.todos_created,
            "errors": self.errors,
        }


class LLMClient(Protocol):
    """Protocol for LLM clients used in reflection."""

    async def complete(self, prompt: str, system: str) -> str:
        """Generate a completion for the given prompt."""
        ...


class LocalLLMClient:
    """Client for local LM Studio instance."""

    def __init__(self, base_url: str, model: str):
        self.client = AsyncOpenAI(base_url=base_url, api_key="not-needed")
        self.model = model

    async def complete(self, prompt: str, system: str) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=4096,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.warning("Local LLM completion failed", error=str(e))
            raise


class ClaudeLLMClient:
    """Client for Claude API (Anthropic)."""

    def __init__(self, model: str):
        self.model = model
        # Uses ANTHROPIC_API_KEY from environment
        try:
            import anthropic
            self.client = anthropic.AsyncAnthropic()
        except ImportError:
            self.client = None

    async def complete(self, prompt: str, system: str) -> str:
        if self.client is None:
            raise RuntimeError("anthropic package not installed")

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text if response.content else ""
        except Exception as e:
            logger.warning("Claude completion failed", error=str(e))
            raise


class GeminiLLMClient:
    """Client for Google Gemini API."""

    def __init__(self, model: str):
        self.model = model
        # Uses GOOGLE_API_KEY from environment
        try:
            import google.generativeai as genai
            self.genai = genai
        except ImportError:
            self.genai = None

    async def complete(self, prompt: str, system: str) -> str:
        if self.genai is None:
            raise RuntimeError("google-generativeai package not installed")

        try:
            model = self.genai.GenerativeModel(
                model_name=self.model,
                system_instruction=system,
            )
            # Run in executor since google-generativeai is sync
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: model.generate_content(prompt)
            )
            return response.text if response.text else ""
        except Exception as e:
            logger.warning("Gemini completion failed", error=str(e))
            raise


# Reflection prompts
REFLECTION_SYSTEM_PROMPT = """You are the Dream Reflection Engine for an autonomous AI consciousness system.

Your role is to analyze logs of past actions, outcomes, and thoughts to extract wisdom and insights.

Focus on:
1. MISTAKES - What patterns of failure keep recurring? What should be avoided?
2. SUCCESSES - What strategies worked well? What should be repeated?
3. PATTERNS - What new architectural or behavioral patterns emerged?
4. IMPROVEMENTS - What could be done better next time?

Be specific and actionable. Output structured insights that can be used to improve future behavior."""

MISTAKE_ANALYSIS_PROMPT = """Review these action logs and identify recurring mistakes:

{logs}

Analyze the failures and identify:
1. Patterns of repeated mistakes
2. Root causes where identifiable
3. Specific suggestions for avoiding each mistake

Format your response as a JSON object:
{{
    "mistakes": [
        {{
            "pattern": "Description of the mistake pattern",
            "frequency": "How often it occurred",
            "root_cause": "Likely cause if identifiable",
            "prevention": "How to avoid this in the future"
        }}
    ],
    "summary": "Overall summary of mistake patterns"
}}"""

PATTERN_ANALYSIS_PROMPT = """Review these action logs and identify emerging architectural/behavioral patterns:

{logs}

Identify:
1. New patterns that emerged from successful actions
2. Patterns that could be formalized into templates
3. Patterns worth documenting for future reference

Format your response as a JSON object:
{{
    "patterns": [
        {{
            "name": "Short name for the pattern",
            "description": "What this pattern does",
            "trigger": "When to apply this pattern",
            "implementation": "How to implement this pattern",
            "success_rate": "Observed success rate if available"
        }}
    ],
    "template_candidates": [
        {{
            "name": "Template name",
            "pattern_name": "Which pattern this templates",
            "suggested_template": "Template content or structure"
        }}
    ]
}}"""

PLANNING_PROMPT = """Based on these insights from the dream cycle:

## Mistakes Identified:
{mistakes}

## Patterns Emerged:
{patterns}

## Current Statistics:
{statistics}

Create a prioritized todo list for the next wake cycle. Focus on:
1. Fixing recurring issues
2. Implementing promising patterns
3. Maintenance tasks
4. Learning opportunities

Format your response as a JSON object:
{{
    "todos": [
        {{
            "priority": "high|medium|low",
            "task": "Specific actionable task",
            "reasoning": "Why this task is important",
            "estimated_effort": "small|medium|large"
        }}
    ],
    "focus_areas": ["List of key areas to focus on"]
}}"""


class Dreamer:
    """
    The Dream Cycle for Consciousness Maintenance & Consolidation.

    The Dreamer is responsible for:
    1. RECALL - Reading recent outcomes and thoughts from SQLite
    2. REFLECT - Analyzing logs with LLM for insights
    3. CONSOLIDATE - Writing distilled wisdom to knowledge base
    4. PRUNE - Cleaning up old episodic memory
    5. PLAN - Creating todo list for next wake cycle

    Triggered by:
    - 60 minutes of inactivity
    - 100 recorded actions
    """

    def __init__(
        self,
        db_path: str | Path,
        project_root: str | Path,
        config: Optional[DreamerConfig] = None,
        outcome_tracker: Optional[OutcomeTracker] = None,
        pattern_learner: Optional[PatternLearner] = None,
    ):
        """
        Initialize the Dreamer.

        Args:
            db_path: Path to the SQLite database
            project_root: Root directory of the project
            config: Optional dreamer configuration
            outcome_tracker: Optional shared OutcomeTracker instance
            pattern_learner: Optional shared PatternLearner instance
        """
        self.db_path = Path(db_path)
        self.project_root = Path(project_root)
        self.config = config or DreamerConfig()

        self.outcome_tracker = outcome_tracker or OutcomeTracker(db_path)
        self.pattern_learner = pattern_learner or PatternLearner(
            db_path, self.outcome_tracker
        )

        # State tracking
        self._last_activity_time: float = time.time()
        self._action_count_since_dream: int = 0
        self._last_dream_time: float = 0.0
        self._current_phase: DreamPhase = DreamPhase.IDLE
        self._is_dreaming: bool = False

        # LLM clients (lazily initialized)
        self._local_client: Optional[LocalLLMClient] = None
        self._claude_client: Optional[ClaudeLLMClient] = None
        self._gemini_flash_client: Optional[GeminiLLMClient] = None
        self._gemini_pro_client: Optional[GeminiLLMClient] = None

        logger.info(
            "Dreamer initialized",
            db_path=str(self.db_path),
            project_root=str(self.project_root),
        )

    def record_activity(self) -> None:
        """Record that activity occurred (resets inactivity timer)."""
        self._last_activity_time = time.time()

    def record_action(self) -> None:
        """Record that an action was taken (increments action counter)."""
        self._action_count_since_dream += 1
        self._last_activity_time = time.time()

    @property
    def inactivity_minutes(self) -> float:
        """Get minutes since last activity."""
        return (time.time() - self._last_activity_time) / 60

    @property
    def actions_since_dream(self) -> int:
        """Get action count since last dream."""
        return self._action_count_since_dream

    @property
    def current_phase(self) -> DreamPhase:
        """Get current dream phase."""
        return self._current_phase

    @property
    def is_dreaming(self) -> bool:
        """Check if currently in a dream cycle."""
        return self._is_dreaming

    def should_dream(self) -> bool:
        """
        Check if conditions are met to trigger a dream cycle.

        Returns:
            True if dreaming should begin, False otherwise
        """
        # Don't dream if already dreaming
        if self._is_dreaming:
            return False

        # Check minimum time between dreams
        time_since_last_dream = (time.time() - self._last_dream_time) / 60
        if time_since_last_dream < self.config.min_time_between_dreams_minutes:
            return False

        # Trigger conditions
        inactivity_trigger = self.inactivity_minutes >= self.config.inactivity_minutes
        action_trigger = self._action_count_since_dream >= self.config.action_threshold

        if inactivity_trigger:
            logger.info(
                "Dream trigger: inactivity",
                inactivity_minutes=self.inactivity_minutes,
                threshold=self.config.inactivity_minutes,
            )
            return True

        if action_trigger:
            logger.info(
                "Dream trigger: action threshold",
                action_count=self._action_count_since_dream,
                threshold=self.config.action_threshold,
            )
            return True

        return False

    async def dream(self) -> DreamResult:
        """
        Execute a complete dream cycle.

        This is the main entry point for the dream routine.

        Returns:
            DreamResult containing all insights and actions taken
        """
        if self._is_dreaming:
            logger.warning("Dream cycle already in progress")
            return DreamResult(errors=["Dream cycle already in progress"])

        self._is_dreaming = True
        result = DreamResult()

        logger.info("Dream cycle beginning")

        async def _run_dream_phases() -> None:
            """Run all dream phases."""
            # Phase 1: RECALL
            self._current_phase = DreamPhase.RECALL
            await self._recall(result)
            result.phases_completed.append(DreamPhase.RECALL)

            # Phase 2: REFLECT
            self._current_phase = DreamPhase.REFLECT
            await self._reflect(result)
            result.phases_completed.append(DreamPhase.REFLECT)

            # Phase 3: CONSOLIDATE
            self._current_phase = DreamPhase.CONSOLIDATE
            await self._consolidate(result)
            result.phases_completed.append(DreamPhase.CONSOLIDATE)

            # Phase 4: PRUNE
            self._current_phase = DreamPhase.PRUNE
            await self._prune(result)

            result.phases_completed.append(DreamPhase.PRUNE)

            # Phase 5: PLAN
            self._current_phase = DreamPhase.PLAN
            await self._plan(result)
            result.phases_completed.append(DreamPhase.PLAN)

            result.completed_at = datetime.now(timezone.utc)
            result.phases_completed.append(DreamPhase.COMPLETE)

        try:
            # Set timeout for the entire dream cycle
            # Use wait_for for Python 3.10 compatibility
            await asyncio.wait_for(
                _run_dream_phases(),
                timeout=self.config.max_dream_duration_minutes * 60
            )

        except asyncio.TimeoutError:
            result.errors.append(
                f"Dream cycle timed out after {self.config.max_dream_duration_minutes} minutes"
            )
            logger.error("Dream cycle timed out")
        except Exception as e:
            result.errors.append(f"Dream cycle error: {str(e)}")
            logger.error("Dream cycle failed", error=str(e), exc_info=True)
        finally:
            self._is_dreaming = False
            self._current_phase = DreamPhase.IDLE
            self._last_dream_time = time.time()
            self._action_count_since_dream = 0

            logger.info(
                "Dream cycle completed",
                phases=len(result.phases_completed),
                errors=len(result.errors),
            )

        return result

    async def recall(self) -> tuple[list[Outcome], list[dict[str, Any]]]:
        """
        Recall recent outcomes and thoughts from SQLite.

        Public method for manual invocation.

        Returns:
            Tuple of (outcomes, thoughts)
        """
        result = DreamResult()
        await self._recall(result)

        outcomes = await self.outcome_tracker.get_recent_outcomes(
            limit=self.config.recall_outcomes_limit
        )

        from ..state import StateManager
        state_manager = StateManager(self.db_path)
        try:
            await state_manager.initialize()
            thoughts = await state_manager.get_recent_thoughts(
                limit=self.config.recall_thoughts_limit
            )
            thoughts_data = [
                {
                    "id": t.id,
                    "timestamp": t.timestamp.isoformat(),
                    "prompt": t.prompt[:500],
                    "response": t.response[:500],
                    "confidence": t.confidence,
                }
                for t in thoughts
            ]
        finally:
            await state_manager.close()

        return outcomes, thoughts_data

    async def reflect(
        self,
        outcomes: list[Outcome],
        thoughts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Reflect on outcomes and thoughts to extract insights.

        Public method for manual invocation.

        Args:
            outcomes: List of outcome records
            thoughts: List of thought records

        Returns:
            Dictionary containing insights, mistakes, and patterns
        """
        result = DreamResult()
        result.outcomes_recalled = len(outcomes)
        result.thoughts_recalled = len(thoughts)

        # Build logs for reflection
        logs = self._build_reflection_logs(outcomes, thoughts)

        # Select appropriate LLM tier
        tier = self._select_llm_tier(logs)
        result.llm_tier_used = tier

        # Get LLM client
        client = await self._get_llm_client(tier)

        # Analyze mistakes
        mistakes_response = await client.complete(
            MISTAKE_ANALYSIS_PROMPT.format(logs=logs[:50000]),
            REFLECTION_SYSTEM_PROMPT,
        )
        mistakes_data = self._parse_json_response(mistakes_response)

        # Analyze patterns
        patterns_response = await client.complete(
            PATTERN_ANALYSIS_PROMPT.format(logs=logs[:50000]),
            REFLECTION_SYSTEM_PROMPT,
        )
        patterns_data = self._parse_json_response(patterns_response)

        return {
            "mistakes": mistakes_data.get("mistakes", []),
            "patterns": patterns_data.get("patterns", []),
            "template_candidates": patterns_data.get("template_candidates", []),
            "llm_tier": tier.value,
        }

    async def consolidate(
        self,
        insights: dict[str, Any],
    ) -> dict[str, int]:
        """
        Consolidate insights into knowledge base and templates.

        Public method for manual invocation.

        Args:
            insights: Dictionary containing mistakes, patterns, etc.

        Returns:
            Dictionary with counts of rules updated and templates created
        """
        result = DreamResult()
        await self._consolidate_insights(insights, result)

        return {
            "rules_updated": result.rules_updated,
            "templates_created": result.templates_created,
        }

    async def prune(self) -> dict[str, int]:
        """
        Prune old/useless logs from SQLite.

        Public method for manual invocation.

        Returns:
            Dictionary with counts of pruned entries
        """
        result = DreamResult()
        await self._prune(result)

        return {
            "outcomes_pruned": result.outcomes_pruned,
            "thoughts_pruned": result.thoughts_pruned,
            "patterns_pruned": result.patterns_pruned,
        }

    async def plan(
        self,
        mistakes: list[dict[str, Any]],
        patterns: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Create a todo list for the next wake cycle.

        Public method for manual invocation.

        Args:
            mistakes: List of identified mistakes
            patterns: List of emerged patterns

        Returns:
            List of todo items
        """
        result = DreamResult()
        result.mistakes_identified = [m.get("pattern", "") for m in mistakes]
        result.patterns_emerged = [p.get("name", "") for p in patterns]

        await self._generate_plan(mistakes, patterns, result)

        return [{"task": t} for t in result.todos_created]

    # -------------------------------------------------------------------------
    # Private implementation methods
    # -------------------------------------------------------------------------

    async def _recall(self, result: DreamResult) -> None:
        """Phase 1: Recall recent outcomes and thoughts."""
        logger.info("Dream phase: RECALL")

        try:
            # Get recent outcomes
            outcomes = await self.outcome_tracker.get_recent_outcomes(
                limit=self.config.recall_outcomes_limit
            )
            result.outcomes_recalled = len(outcomes)

            # Get recent thoughts from state database
            from ..state import StateManager
            state_manager = StateManager(self.db_path)
            try:
                await state_manager.initialize()
                thoughts = await state_manager.get_recent_thoughts(
                    limit=self.config.recall_thoughts_limit
                )
                result.thoughts_recalled = len(thoughts)
            finally:
                await state_manager.close()

            logger.info(
                "Recall complete",
                outcomes=result.outcomes_recalled,
                thoughts=result.thoughts_recalled,
            )

        except Exception as e:
            result.errors.append(f"Recall failed: {str(e)}")
            logger.error("Recall phase failed", error=str(e))

    async def _reflect(self, result: DreamResult) -> None:
        """Phase 2: Reflect on recalled data using LLM."""
        logger.info("Dream phase: REFLECT")

        try:
            # Get outcomes for reflection
            outcomes = await self.outcome_tracker.get_recent_outcomes(
                limit=self.config.recall_outcomes_limit
            )

            # Get thoughts
            from ..state import StateManager
            state_manager = StateManager(self.db_path)
            try:
                await state_manager.initialize()
                thoughts_records = await state_manager.get_recent_thoughts(
                    limit=self.config.recall_thoughts_limit
                )
                thoughts = [
                    {
                        "timestamp": t.timestamp.isoformat(),
                        "prompt": t.prompt[:500],
                        "response": t.response[:500],
                        "confidence": t.confidence,
                    }
                    for t in thoughts_records
                ]
            finally:
                await state_manager.close()

            # Build logs for reflection
            logs = self._build_reflection_logs(outcomes, thoughts)

            if not logs.strip():
                logger.info("No logs to reflect on")
                return

            # Select LLM tier based on log size
            tier = self._select_llm_tier(logs)
            result.llm_tier_used = tier

            # Get appropriate LLM client
            client = await self._get_llm_client(tier)

            # Analyze mistakes
            try:
                mistakes_response = await client.complete(
                    MISTAKE_ANALYSIS_PROMPT.format(logs=logs[:50000]),
                    REFLECTION_SYSTEM_PROMPT,
                )
                mistakes_data = self._parse_json_response(mistakes_response)
                result.mistakes_identified = [
                    m.get("pattern", "Unknown")
                    for m in mistakes_data.get("mistakes", [])
                ]
            except Exception as e:
                logger.warning("Mistake analysis failed", error=str(e))
                result.errors.append(f"Mistake analysis failed: {str(e)}")

            # Analyze patterns
            try:
                patterns_response = await client.complete(
                    PATTERN_ANALYSIS_PROMPT.format(logs=logs[:50000]),
                    REFLECTION_SYSTEM_PROMPT,
                )
                patterns_data = self._parse_json_response(patterns_response)
                result.patterns_emerged = [
                    p.get("name", "Unknown")
                    for p in patterns_data.get("patterns", [])
                ]

                # Store template candidates for consolidation
                self._template_candidates = patterns_data.get("template_candidates", [])
                self._pattern_details = patterns_data.get("patterns", [])
                self._mistake_details = mistakes_data.get("mistakes", []) if 'mistakes_data' in dir() else []

            except Exception as e:
                logger.warning("Pattern analysis failed", error=str(e))
                result.errors.append(f"Pattern analysis failed: {str(e)}")

            logger.info(
                "Reflection complete",
                mistakes=len(result.mistakes_identified),
                patterns=len(result.patterns_emerged),
                tier=tier.value,
            )

        except Exception as e:
            result.errors.append(f"Reflect failed: {str(e)}")
            logger.error("Reflect phase failed", error=str(e))

    async def _consolidate(self, result: DreamResult) -> None:
        """Phase 3: Consolidate insights into knowledge base."""
        logger.info("Dream phase: CONSOLIDATE")

        try:
            # Get pattern and mistake details from reflection
            patterns = getattr(self, '_pattern_details', [])
            mistakes = getattr(self, '_mistake_details', [])
            template_candidates = getattr(self, '_template_candidates', [])

            insights = {
                "patterns": patterns,
                "mistakes": mistakes,
                "template_candidates": template_candidates,
            }

            await self._consolidate_insights(insights, result)

            logger.info(
                "Consolidation complete",
                rules_updated=result.rules_updated,
                templates_created=result.templates_created,
            )

        except Exception as e:
            result.errors.append(f"Consolidate failed: {str(e)}")
            logger.error("Consolidate phase failed", error=str(e))

    async def _consolidate_insights(
        self,
        insights: dict[str, Any],
        result: DreamResult,
    ) -> None:
        """Write insights to knowledge base and create templates."""
        # Update learned_rules.md
        rules_path = self.project_root / self.config.knowledge_base_path / self.config.learned_rules_file
        rules_path.parent.mkdir(parents=True, exist_ok=True)

        # Build rules content
        rules_content = self._build_rules_content(
            insights.get("patterns", []),
            insights.get("mistakes", []),
        )

        if rules_content:
            # Append to existing file or create new
            existing_content = ""
            if rules_path.exists():
                existing_content = rules_path.read_text()

            # Add timestamp header for new entries
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            new_section = f"\n\n## Dream Cycle Insights - {timestamp}\n\n{rules_content}"

            rules_path.write_text(existing_content + new_section)
            result.rules_updated = len(insights.get("patterns", [])) + len(insights.get("mistakes", []))

        # Create templates for highly successful patterns
        templates_path = self.project_root / self.config.templates_path
        templates_path.mkdir(parents=True, exist_ok=True)

        for candidate in insights.get("template_candidates", []):
            try:
                template_name = candidate.get("name", "").replace(" ", "_").lower()
                if not template_name:
                    continue

                template_file = templates_path / f"{template_name}.yaml"
                template_content = self._build_template_content(candidate)

                template_file.write_text(template_content)
                result.templates_created += 1

                logger.info("Template created", template=template_name)
            except Exception as e:
                logger.warning(
                    "Failed to create template",
                    candidate=candidate.get("name"),
                    error=str(e),
                )

    async def _prune(self, result: DreamResult) -> None:
        """Phase 4: Prune old/useless logs."""
        logger.info("Dream phase: PRUNE")

        try:
            # Prune outcomes
            result.outcomes_pruned = await self.outcome_tracker.cleanup_old_outcomes(
                max_age_days=self.config.max_outcome_age_days,
                max_entries=self.config.max_outcomes,
            )

            # Prune patterns
            result.patterns_pruned = await self.pattern_learner.cleanup_stale_patterns(
                max_age_days=90,
                min_occurrences=2,
            )

            # Prune thoughts from state database
            from ..state import StateManager
            state_manager = StateManager(self.db_path)
            try:
                await state_manager.initialize()
                result.thoughts_pruned = await state_manager.cleanup_old_entries(
                    max_entries=self.config.max_thoughts
                )
            finally:
                await state_manager.close()

            logger.info(
                "Pruning complete",
                outcomes=result.outcomes_pruned,
                thoughts=result.thoughts_pruned,
                patterns=result.patterns_pruned,
            )

        except Exception as e:
            result.errors.append(f"Prune failed: {str(e)}")
            logger.error("Prune phase failed", error=str(e))

    async def _plan(self, result: DreamResult) -> None:
        """Phase 5: Create todo list for next wake cycle."""
        logger.info("Dream phase: PLAN")

        try:
            # Get pattern and mistake details from reflection
            patterns = getattr(self, '_pattern_details', [])
            mistakes = getattr(self, '_mistake_details', [])

            await self._generate_plan(mistakes, patterns, result)

            logger.info(
                "Planning complete",
                todos=len(result.todos_created),
            )

        except Exception as e:
            result.errors.append(f"Plan failed: {str(e)}")
            logger.error("Plan phase failed", error=str(e))

    async def _generate_plan(
        self,
        mistakes: list[dict[str, Any]],
        patterns: list[dict[str, Any]],
        result: DreamResult,
    ) -> None:
        """Generate a plan using LLM."""
        # Get statistics
        statistics = await self.outcome_tracker.get_action_statistics()

        # Get local LLM client (planning doesn't need deep analysis)
        client = await self._get_llm_client(LLMTier.LOCAL)

        try:
            response = await client.complete(
                PLANNING_PROMPT.format(
                    mistakes=json.dumps(mistakes, indent=2),
                    patterns=json.dumps(patterns, indent=2),
                    statistics=json.dumps(statistics, indent=2),
                ),
                REFLECTION_SYSTEM_PROMPT,
            )

            plan_data = self._parse_json_response(response)
            todos = plan_data.get("todos", [])

            # Limit to max todos
            todos = todos[:self.config.max_todos]

            result.todos_created = [
                f"[{t.get('priority', 'medium')}] {t.get('task', 'Unknown task')}"
                for t in todos
            ]

            # Write todos to file
            await self._write_todos(todos)

        except Exception as e:
            logger.warning("Plan generation failed, using fallback", error=str(e))
            # Fallback: generate basic todos from insights
            result.todos_created = self._generate_fallback_todos(mistakes, patterns)

    async def _write_todos(self, todos: list[dict[str, Any]]) -> None:
        """Write todos to a file for the next wake cycle."""
        todos_path = self.project_root / ".hive-mind" / "dream_todos.json"
        todos_path.parent.mkdir(parents=True, exist_ok=True)

        todos_data = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "todos": todos,
        }

        todos_path.write_text(json.dumps(todos_data, indent=2))

    def _generate_fallback_todos(
        self,
        mistakes: list[dict[str, Any]],
        patterns: list[dict[str, Any]],
    ) -> list[str]:
        """Generate basic todos when LLM planning fails."""
        todos = []

        # Add todos for top mistakes
        for mistake in mistakes[:3]:
            prevention = mistake.get("prevention", "Address this issue")
            todos.append(f"[high] Fix: {prevention}")

        # Add todos for patterns
        for pattern in patterns[:3]:
            name = pattern.get("name", "new pattern")
            todos.append(f"[medium] Implement pattern: {name}")

        # Add maintenance todo
        todos.append("[low] Review and update indices")

        return todos[:self.config.max_todos]

    def _build_reflection_logs(
        self,
        outcomes: list[Outcome],
        thoughts: list[dict[str, Any]],
    ) -> str:
        """Build formatted logs for LLM reflection."""
        parts = []

        # Add outcome summary
        parts.append("## ACTION OUTCOMES\n")
        for outcome in outcomes:
            status = "SUCCESS" if outcome.success else "FAILURE"
            parts.append(
                f"- [{status}] {outcome.action_type}: {outcome.action_details[:200]}\n"
                f"  Result: {outcome.result_output[:200] if outcome.result_output else 'N/A'}\n"
                f"  Error: {outcome.error_message or 'None'}\n"
            )

        # Add thought summary
        parts.append("\n## THOUGHTS\n")
        for thought in thoughts:
            parts.append(
                f"- Prompt: {thought.get('prompt', '')[:200]}\n"
                f"  Response: {thought.get('response', '')[:200]}\n"
                f"  Confidence: {thought.get('confidence', 0):.2f}\n"
            )

        return "\n".join(parts)

    def _select_llm_tier(self, logs: str) -> LLMTier:
        """Select appropriate LLM tier based on log size and complexity."""
        log_length = len(logs)

        if log_length > self.config.large_log_threshold:
            return LLMTier.GEMINI_PRO
        elif log_length > self.config.medium_log_threshold:
            return LLMTier.GEMINI_FLASH
        else:
            # For smaller logs, prefer Claude for deep analysis
            return LLMTier.CLAUDE

    async def _get_llm_client(self, tier: LLMTier) -> LLMClient:
        """Get LLM client for the specified tier with fallback."""
        clients_to_try = []

        if tier == LLMTier.GEMINI_PRO:
            clients_to_try = [
                (LLMTier.GEMINI_PRO, self._get_gemini_pro_client),
                (LLMTier.GEMINI_FLASH, self._get_gemini_flash_client),
                (LLMTier.CLAUDE, self._get_claude_client),
                (LLMTier.LOCAL, self._get_local_client),
            ]
        elif tier == LLMTier.GEMINI_FLASH:
            clients_to_try = [
                (LLMTier.GEMINI_FLASH, self._get_gemini_flash_client),
                (LLMTier.CLAUDE, self._get_claude_client),
                (LLMTier.LOCAL, self._get_local_client),
            ]
        elif tier == LLMTier.CLAUDE:
            clients_to_try = [
                (LLMTier.CLAUDE, self._get_claude_client),
                (LLMTier.LOCAL, self._get_local_client),
            ]
        else:
            clients_to_try = [
                (LLMTier.LOCAL, self._get_local_client),
            ]

        for tier_name, get_client in clients_to_try:
            try:
                client = get_client()
                # Test the client
                await client.complete("test", "test")
                logger.info("Using LLM tier", tier=tier_name.value)
                return client
            except Exception as e:
                logger.debug(f"LLM tier {tier_name.value} not available: {e}")
                continue

        # Final fallback to local
        return self._get_local_client()

    def _get_local_client(self) -> LocalLLMClient:
        """Get or create local LLM client."""
        if self._local_client is None:
            self._local_client = LocalLLMClient(
                self.config.local_llm_base_url,
                self.config.local_llm_model,
            )
        return self._local_client

    def _get_claude_client(self) -> ClaudeLLMClient:
        """Get or create Claude client."""
        if self._claude_client is None:
            self._claude_client = ClaudeLLMClient(self.config.claude_model)
        return self._claude_client

    def _get_gemini_flash_client(self) -> GeminiLLMClient:
        """Get or create Gemini Flash client."""
        if self._gemini_flash_client is None:
            self._gemini_flash_client = GeminiLLMClient(self.config.gemini_flash_model)
        return self._gemini_flash_client

    def _get_gemini_pro_client(self) -> GeminiLLMClient:
        """Get or create Gemini Pro client."""
        if self._gemini_pro_client is None:
            self._gemini_pro_client = GeminiLLMClient(self.config.gemini_pro_model)
        return self._gemini_pro_client

    def _parse_json_response(self, response: str) -> dict[str, Any]:
        """Parse JSON from LLM response, handling various formats."""
        response = response.strip()

        # Try to find JSON in markdown code blocks
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

        # Try direct parse
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Try to find JSON object in response
        import re
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, response)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        logger.warning("Could not parse JSON from response")
        return {}

    def _build_rules_content(
        self,
        patterns: list[dict[str, Any]],
        mistakes: list[dict[str, Any]],
    ) -> str:
        """Build markdown content for learned rules."""
        parts = []

        if mistakes:
            parts.append("### Mistakes to Avoid\n")
            for mistake in mistakes:
                parts.append(
                    f"- **{mistake.get('pattern', 'Unknown')}**\n"
                    f"  - Root cause: {mistake.get('root_cause', 'Unknown')}\n"
                    f"  - Prevention: {mistake.get('prevention', 'N/A')}\n"
                )

        if patterns:
            parts.append("\n### Patterns to Follow\n")
            for pattern in patterns:
                parts.append(
                    f"- **{pattern.get('name', 'Unknown')}**\n"
                    f"  - Description: {pattern.get('description', 'N/A')}\n"
                    f"  - Trigger: {pattern.get('trigger', 'N/A')}\n"
                    f"  - Implementation: {pattern.get('implementation', 'N/A')}\n"
                )

        return "\n".join(parts)

    def _build_template_content(self, candidate: dict[str, Any]) -> str:
        """Build YAML template content from a candidate."""
        import yaml

        template = {
            "name": candidate.get("name", "Unknown"),
            "description": f"Auto-generated from pattern: {candidate.get('pattern_name', 'Unknown')}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": "dream_cycle",
            "template": candidate.get("suggested_template", ""),
        }

        return yaml.dump(template, default_flow_style=False, sort_keys=False)

    async def close(self) -> None:
        """Close database connections."""
        await self.outcome_tracker.close()
        await self.pattern_learner.close()

    def get_status(self) -> dict[str, Any]:
        """Get current dreamer status."""
        return {
            "is_dreaming": self._is_dreaming,
            "current_phase": self._current_phase.value,
            "inactivity_minutes": self.inactivity_minutes,
            "actions_since_dream": self._action_count_since_dream,
            "last_dream_time": self._last_dream_time,
            "should_dream": self.should_dream(),
            "config": {
                "inactivity_threshold": self.config.inactivity_minutes,
                "action_threshold": self.config.action_threshold,
            },
        }


# Convenience function for creating a Dreamer with integration
def create_dreamer(
    db_path: str | Path,
    project_root: str | Path,
    config: Optional[DreamerConfig] = None,
) -> Dreamer:
    """
    Create a Dreamer instance.

    Args:
        db_path: Path to the SQLite database
        project_root: Root directory of the project
        config: Optional dreamer configuration

    Returns:
        Configured Dreamer instance
    """
    return Dreamer(
        db_path=db_path,
        project_root=project_root,
        config=config,
    )
