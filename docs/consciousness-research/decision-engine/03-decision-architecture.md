# Decision Engine Architecture

## Executive Summary

The Decision Engine is the cognitive core of the Consciousness system. It receives observations from the file watcher and other sensors, processes them through multi-step reasoning, and produces actionable decisions that are executed by Claude Code or Claude Flow.

**Core Design Principles:**
1. **Proactive, not reactive**: Decisions are based on goals and context, not just events
2. **Multi-step reasoning**: No single-shot decisions; all decisions follow OBSERVE -> CATEGORIZE -> MATCH_PATTERN -> EVALUATE -> DECIDE -> ACT/WAIT
3. **Confidence-based**: Every decision has a confidence score; low confidence triggers investigation
4. **Learning-enabled**: Outcomes are tracked and inform future decisions
5. **Template-driven**: Pre-defined action templates ensure consistent, reliable execution

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DECISION ENGINE ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   OBSERVATIONS              DECISION CORE              ACTIONS               │
│  ┌──────────────┐    ┌────────────────────────┐    ┌──────────────────┐    │
│  │ File Changes │───▶│                        │───▶│ Execute Action   │    │
│  │ Process Evts │───▶│   Multi-Step Reasoner  │───▶│ Wait + Observe   │    │
│  │ Time Events  │───▶│   (OIDA Loop)          │───▶│ Investigate More │    │
│  │ Task Results │───▶│                        │───▶│ Escalate         │    │
│  └──────────────┘    └────────────────────────┘    └──────────────────┘    │
│         │                      │                           │               │
│         │           ┌──────────┴──────────┐               │               │
│         │           │                     │               │               │
│         │    ┌──────▼──────┐    ┌─────────▼─────────┐    │               │
│         │    │  Knowledge  │    │  Action Templates │    │               │
│         │    │    Base     │    │  & Patterns       │    │               │
│         │    └─────────────┘    └───────────────────┘    │               │
│         │                                                 │               │
│         └─────────────────────────────────────────────────┘               │
│                            (Learning Loop)                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Part I: Observation Processing

### 1.1 Observation Types and Categories

Every observation is categorized upon receipt. This categorization determines processing priority and routing.

```python
"""
Observation processing and categorization.
First stage of the decision pipeline.
"""
from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
import hashlib


class ObservationType(str, Enum):
    """Types of observations the system can receive."""
    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    FILE_DELETED = "file_deleted"
    FILE_MOVED = "file_moved"
    PROCESS_STARTED = "process_started"
    PROCESS_COMPLETED = "process_completed"
    PROCESS_FAILED = "process_failed"
    TASK_QUEUED = "task_queued"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TIME_ELAPSED = "time_elapsed"
    SCHEDULE_TRIGGERED = "schedule_triggered"
    EXTERNAL_EVENT = "external_event"


class ObservationUrgency(str, Enum):
    """Urgency classification for observations."""
    CRITICAL = "critical"     # Requires immediate attention (errors, failures)
    URGENT = "urgent"         # Should be handled soon (user actions, important changes)
    ROUTINE = "routine"       # Normal processing (scheduled tasks, updates)
    LOW = "low"               # Can be batched (cleanup, optimization)
    NOISE = "noise"           # Should be filtered or ignored


class ObservationCategory(str, Enum):
    """Semantic categories for observations."""
    # Content categories
    INTAKE = "intake"                    # New input to process (_input, _intake)
    KNOWLEDGE = "knowledge"              # Knowledge base changes
    THINKER = "thinker"                  # Philosopher/thinker profiles
    INDEX = "index"                      # Index file updates
    TEMPLATE = "template"                # Template modifications
    CONFIG = "config"                    # Configuration changes

    # Process categories
    TASK_LIFECYCLE = "task_lifecycle"    # Task state changes
    EXECUTION = "execution"              # Claude Code/Flow execution
    SYSTEM = "system"                    # System-level events

    # Meta categories
    SELF_REFERENCE = "self_reference"    # Changes to consciousness system
    LEARNING = "learning"                # Outcome/feedback signals


@dataclass
class Observation:
    """
    A single observation from the monitoring system.

    This is the atomic unit of input to the Decision Engine.
    """
    id: str                                       # Unique observation ID
    timestamp: datetime                           # When observation occurred
    observation_type: ObservationType             # Type of observation

    # Classification (assigned during processing)
    urgency: ObservationUrgency = ObservationUrgency.ROUTINE
    category: ObservationCategory = ObservationCategory.SYSTEM

    # Context
    path: Optional[Path] = None                   # File path if applicable
    content_hash: Optional[str] = None            # Hash of file content if applicable
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Relationships
    related_observations: List[str] = field(default_factory=list)
    parent_observation: Optional[str] = None

    # Processing state
    processed: bool = False
    decision_id: Optional[str] = None             # ID of decision made for this

    def to_context_string(self) -> str:
        """Generate context string for LLM consumption."""
        parts = [
            f"[{self.timestamp.isoformat()}]",
            f"Type: {self.observation_type.value}",
            f"Urgency: {self.urgency.value}",
            f"Category: {self.category.value}"
        ]

        if self.path:
            parts.append(f"Path: {self.path}")

        if self.metadata:
            parts.append(f"Metadata: {self.metadata}")

        return " | ".join(parts)


class ObservationClassifier:
    """
    Classify observations by urgency and category.

    Uses pattern matching and heuristics for fast classification,
    with LLM fallback for ambiguous cases.
    """

    # Path-based category patterns
    CATEGORY_PATTERNS = {
        ObservationCategory.INTAKE: [
            "_input/", "_intake/", "inbox/"
        ],
        ObservationCategory.KNOWLEDGE: [
            "knowledge/", "docs/", "research/"
        ],
        ObservationCategory.THINKER: [
            "thinkers/", "philosophers/"
        ],
        ObservationCategory.INDEX: [
            "indices/", "index.yaml", "index.md"
        ],
        ObservationCategory.TEMPLATE: [
            "templates/"
        ],
        ObservationCategory.CONFIG: [
            ".claude/", "config/", ".yaml", ".json", "CLAUDE.md"
        ],
        ObservationCategory.SELF_REFERENCE: [
            "consciousness/", "decision-engine/", "orchestrator/"
        ]
    }

    # Urgency rules based on observation type
    URGENCY_RULES = {
        ObservationType.PROCESS_FAILED: ObservationUrgency.CRITICAL,
        ObservationType.TASK_FAILED: ObservationUrgency.CRITICAL,
        ObservationType.FILE_DELETED: ObservationUrgency.URGENT,
        ObservationType.PROCESS_COMPLETED: ObservationUrgency.ROUTINE,
        ObservationType.TASK_COMPLETED: ObservationUrgency.ROUTINE,
        ObservationType.TIME_ELAPSED: ObservationUrgency.LOW,
    }

    def classify(self, observation: Observation) -> Observation:
        """
        Classify an observation by urgency and category.

        Args:
            observation: Raw observation to classify

        Returns:
            Observation with urgency and category set
        """
        # Classify urgency
        observation.urgency = self._classify_urgency(observation)

        # Classify category
        observation.category = self._classify_category(observation)

        return observation

    def _classify_urgency(self, observation: Observation) -> ObservationUrgency:
        """Determine urgency based on type and context."""

        # Check type-based rules first
        if observation.observation_type in self.URGENCY_RULES:
            return self.URGENCY_RULES[observation.observation_type]

        # File changes in intake are urgent
        if observation.path:
            path_str = str(observation.path).lower()
            if any(p in path_str for p in ["_input/", "_intake/"]):
                return ObservationUrgency.URGENT

        # User-initiated actions are urgent
        if observation.metadata.get("user_initiated"):
            return ObservationUrgency.URGENT

        # Filter noise
        if self._is_noise(observation):
            return ObservationUrgency.NOISE

        return ObservationUrgency.ROUTINE

    def _classify_category(self, observation: Observation) -> ObservationCategory:
        """Determine category based on path and metadata."""

        if not observation.path:
            # Non-file observations
            if observation.observation_type in [
                ObservationType.TASK_QUEUED,
                ObservationType.TASK_COMPLETED,
                ObservationType.TASK_FAILED
            ]:
                return ObservationCategory.TASK_LIFECYCLE

            if observation.observation_type in [
                ObservationType.PROCESS_STARTED,
                ObservationType.PROCESS_COMPLETED,
                ObservationType.PROCESS_FAILED
            ]:
                return ObservationCategory.EXECUTION

            return ObservationCategory.SYSTEM

        # Path-based classification
        path_str = str(observation.path).lower()

        for category, patterns in self.CATEGORY_PATTERNS.items():
            if any(pattern in path_str for pattern in patterns):
                return category

        # Default to knowledge for documentation
        if path_str.endswith((".md", ".txt", ".yaml")):
            return ObservationCategory.KNOWLEDGE

        return ObservationCategory.SYSTEM

    def _is_noise(self, observation: Observation) -> bool:
        """Detect noise observations that should be filtered."""

        if not observation.path:
            return False

        path_str = str(observation.path)

        # Common noise patterns
        noise_patterns = [
            ".DS_Store",
            ".git/",
            "__pycache__/",
            "*.pyc",
            ".swp",
            "~",
            ".lock",
            "node_modules/",
            ".env.local"
        ]

        return any(pattern.replace("*", "") in path_str for pattern in noise_patterns)
```

### 1.2 Observation Prioritization

When multiple observations arrive simultaneously, they must be prioritized for processing.

```python
"""
Observation prioritization for processing order.
"""
from heapq import heappush, heappop
from typing import List, Tuple
from dataclasses import dataclass


@dataclass(order=True)
class PrioritizedObservation:
    """Observation wrapped with priority for heap ordering."""
    priority: int
    sequence: int  # Tie-breaker for same priority
    observation: Observation = field(compare=False)


class ObservationQueue:
    """
    Priority queue for observations.

    Higher urgency observations are processed first.
    Within same urgency, FIFO order is maintained.
    """

    # Priority values (lower = higher priority)
    PRIORITY_MAP = {
        ObservationUrgency.CRITICAL: 0,
        ObservationUrgency.URGENT: 10,
        ObservationUrgency.ROUTINE: 20,
        ObservationUrgency.LOW: 30,
        ObservationUrgency.NOISE: 100,
    }

    def __init__(self):
        self._heap: List[PrioritizedObservation] = []
        self._sequence = 0

    def add(self, observation: Observation) -> None:
        """Add observation to queue."""
        priority = self.PRIORITY_MAP.get(
            observation.urgency,
            self.PRIORITY_MAP[ObservationUrgency.ROUTINE]
        )

        self._sequence += 1

        heappush(
            self._heap,
            PrioritizedObservation(
                priority=priority,
                sequence=self._sequence,
                observation=observation
            )
        )

    def get_next(self) -> Optional[Observation]:
        """Get highest priority observation."""
        if not self._heap:
            return None

        prioritized = heappop(self._heap)
        return prioritized.observation

    def peek(self) -> Optional[Observation]:
        """View highest priority without removing."""
        if not self._heap:
            return None
        return self._heap[0].observation

    def get_all_critical(self) -> List[Observation]:
        """Get all critical observations (for batch processing)."""
        critical = []
        remaining = []

        while self._heap:
            prioritized = heappop(self._heap)
            if prioritized.observation.urgency == ObservationUrgency.CRITICAL:
                critical.append(prioritized.observation)
            else:
                remaining.append(prioritized)

        # Restore non-critical
        for item in remaining:
            heappush(self._heap, item)

        return critical

    def __len__(self) -> int:
        return len(self._heap)

    @property
    def is_empty(self) -> bool:
        return len(self._heap) == 0


class ObservationBatcher:
    """
    Batch related observations for efficient processing.

    Groups observations by:
    - Same file (multiple edits)
    - Same category (related changes)
    - Time window (rapid succession)
    """

    def __init__(
        self,
        time_window_seconds: float = 2.0,
        max_batch_size: int = 10
    ):
        self.time_window = time_window_seconds
        self.max_batch_size = max_batch_size

    def batch(
        self,
        observations: List[Observation]
    ) -> List[List[Observation]]:
        """
        Group observations into batches.

        Args:
            observations: List of observations to batch

        Returns:
            List of observation batches
        """
        if not observations:
            return []

        # Sort by timestamp
        sorted_obs = sorted(observations, key=lambda o: o.timestamp)

        batches = []
        current_batch = [sorted_obs[0]]

        for obs in sorted_obs[1:]:
            # Check if should add to current batch
            time_diff = (obs.timestamp - current_batch[0].timestamp).total_seconds()
            same_file = (
                obs.path and
                current_batch[0].path and
                obs.path == current_batch[0].path
            )
            same_category = obs.category == current_batch[0].category

            can_batch = (
                time_diff <= self.time_window or
                same_file or
                same_category
            ) and len(current_batch) < self.max_batch_size

            if can_batch:
                current_batch.append(obs)
            else:
                batches.append(current_batch)
                current_batch = [obs]

        # Don't forget the last batch
        if current_batch:
            batches.append(current_batch)

        return batches
```

### 1.3 Context Building

Before making a decision, the system builds rich context from observations.

```python
"""
Context building for decision-making.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path


@dataclass
class DecisionContext:
    """
    Complete context for a decision.

    Contains everything the Decision Engine needs to make
    an informed decision about an observation or batch.
    """
    # Primary observation(s)
    observations: List[Observation]

    # File context (if applicable)
    file_content: Optional[str] = None
    file_metadata: Dict[str, Any] = field(default_factory=dict)
    related_files: List[Path] = field(default_factory=list)

    # Historical context
    similar_past_observations: List[Observation] = field(default_factory=list)
    past_decisions: List[Dict[str, Any]] = field(default_factory=list)

    # Current state
    active_tasks: List[Dict[str, Any]] = field(default_factory=list)
    active_goals: List[str] = field(default_factory=list)
    resource_availability: Dict[str, float] = field(default_factory=dict)

    # Knowledge context
    relevant_knowledge: List[str] = field(default_factory=list)
    action_templates: List[str] = field(default_factory=list)

    def to_prompt(self) -> str:
        """Convert context to LLM prompt."""
        sections = []

        # Observations
        obs_text = "\n".join(o.to_context_string() for o in self.observations)
        sections.append(f"## Observations\n{obs_text}")

        # File content (truncated)
        if self.file_content:
            content = self.file_content[:2000]
            if len(self.file_content) > 2000:
                content += "\n... [truncated]"
            sections.append(f"## File Content\n```\n{content}\n```")

        # Active state
        if self.active_tasks:
            task_text = "\n".join(
                f"- {t['description']} ({t['status']})"
                for t in self.active_tasks[:5]
            )
            sections.append(f"## Active Tasks\n{task_text}")

        if self.active_goals:
            goal_text = "\n".join(f"- {g}" for g in self.active_goals[:5])
            sections.append(f"## Current Goals\n{goal_text}")

        # Past decisions on similar observations
        if self.past_decisions:
            decision_text = "\n".join(
                f"- {d['observation_type']}: {d['decision_type']} -> {d['outcome']}"
                for d in self.past_decisions[:5]
            )
            sections.append(f"## Past Decisions\n{decision_text}")

        # Available action templates
        if self.action_templates:
            template_text = "\n".join(f"- {t}" for t in self.action_templates)
            sections.append(f"## Available Actions\n{template_text}")

        return "\n\n".join(sections)


class ContextBuilder:
    """
    Build decision context from observations.

    Gathers all relevant information needed for decision-making.
    """

    def __init__(
        self,
        knowledge_base,      # Reference to knowledge storage
        decision_history,    # Past decisions
        task_manager,        # Active task tracking
        goal_manager         # Current goals
    ):
        self.knowledge = knowledge_base
        self.history = decision_history
        self.tasks = task_manager
        self.goals = goal_manager

    async def build(
        self,
        observations: List[Observation]
    ) -> DecisionContext:
        """
        Build complete context for observations.

        Args:
            observations: Observations to build context for

        Returns:
            Complete decision context
        """
        context = DecisionContext(observations=observations)

        # Get file content if applicable
        primary_obs = observations[0]
        if primary_obs.path and primary_obs.path.exists():
            try:
                context.file_content = primary_obs.path.read_text()[:5000]
                context.file_metadata = {
                    "size": primary_obs.path.stat().st_size,
                    "modified": primary_obs.path.stat().st_mtime
                }
            except Exception:
                pass

        # Get related files
        if primary_obs.path:
            context.related_files = self._find_related_files(primary_obs.path)

        # Get historical context
        context.similar_past_observations = await self._find_similar_observations(
            primary_obs
        )
        context.past_decisions = await self._get_past_decisions(
            primary_obs.category,
            limit=5
        )

        # Get current state
        context.active_tasks = await self.tasks.get_active_tasks()
        context.active_goals = await self.goals.get_current_goals()
        context.resource_availability = await self._get_resource_availability()

        # Get relevant knowledge
        context.relevant_knowledge = await self._get_relevant_knowledge(
            primary_obs
        )

        # Get applicable action templates
        context.action_templates = self._get_action_templates(primary_obs)

        return context

    def _find_related_files(self, path: Path, max_files: int = 5) -> List[Path]:
        """Find files related to the observed path."""
        related = []

        # Same directory
        if path.parent.exists():
            siblings = list(path.parent.iterdir())[:max_files]
            related.extend([s for s in siblings if s != path])

        # Index files
        for index_name in ["index.yaml", "index.md", "CLAUDE.md"]:
            index_path = path.parent / index_name
            if index_path.exists() and index_path not in related:
                related.append(index_path)

        return related[:max_files]

    async def _find_similar_observations(
        self,
        observation: Observation,
        limit: int = 5
    ) -> List[Observation]:
        """Find similar past observations."""
        return await self.history.find_similar(
            observation_type=observation.observation_type,
            category=observation.category,
            path_pattern=str(observation.path) if observation.path else None,
            limit=limit
        )

    async def _get_past_decisions(
        self,
        category: ObservationCategory,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get past decisions for similar observations."""
        return await self.history.get_decisions_for_category(
            category=category,
            limit=limit
        )

    async def _get_resource_availability(self) -> Dict[str, float]:
        """Check available resources for task execution."""
        return {
            "claude_code_slots": await self.tasks.get_available_slots("claude_code"),
            "claude_flow_slots": await self.tasks.get_available_slots("claude_flow"),
            "memory_mb": await self._get_available_memory(),
            "budget_remaining_usd": await self._get_remaining_budget()
        }

    async def _get_relevant_knowledge(
        self,
        observation: Observation
    ) -> List[str]:
        """Retrieve relevant knowledge for the observation."""
        if not observation.path:
            return []

        # Get knowledge related to the file's domain
        path_str = str(observation.path)

        knowledge = []
        if "philosophy" in path_str:
            knowledge.extend(await self.knowledge.search("philosophy"))
        if "thinker" in path_str:
            knowledge.extend(await self.knowledge.search("thinker profiles"))
        if "consciousness" in path_str:
            knowledge.extend(await self.knowledge.search("consciousness research"))

        return knowledge[:5]

    def _get_action_templates(self, observation: Observation) -> List[str]:
        """Get action templates applicable to this observation."""
        # See Action Templates section below
        templates = []

        if observation.category == ObservationCategory.INTAKE:
            templates.append("process_intake")
        if observation.category == ObservationCategory.INDEX:
            templates.append("update_index")
        if observation.category == ObservationCategory.KNOWLEDGE:
            templates.append("analyze_knowledge")
        if observation.observation_type == ObservationType.TASK_FAILED:
            templates.append("handle_failure")

        return templates
```

---

## Part II: Decision Framework

### 2.1 Decision Types

The Decision Engine produces one of four decision types:

```python
"""
Decision types and structures.
"""
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any


class DecisionType(str, Enum):
    """Types of decisions the engine can make."""
    ACT = "act"                    # Execute an action immediately
    WAIT = "wait"                  # Do nothing, continue observing
    INVESTIGATE = "investigate"    # Gather more information before deciding
    ESCALATE = "escalate"          # Flag for human review


class ActionTarget(str, Enum):
    """Execution targets for ACT decisions."""
    CLAUDE_CODE = "claude_code"    # Single-agent task
    CLAUDE_FLOW = "claude_flow"    # Multi-agent swarm
    INTERNAL = "internal"          # Python script/function
    MEMORY = "memory"              # Memory operation only


@dataclass
class Decision:
    """
    A decision made by the Decision Engine.

    This is the output of the decision process.
    """
    id: str                                   # Unique decision ID
    timestamp: datetime                       # When decision was made

    # Decision details
    decision_type: DecisionType               # Type of decision
    confidence: float                         # Confidence score 0.0-1.0
    reasoning: str                            # Explanation of decision

    # For ACT decisions
    action_target: Optional[ActionTarget] = None
    action_template: Optional[str] = None     # Template to use
    action_prompt: Optional[str] = None       # Prompt for execution
    action_params: Dict[str, Any] = field(default_factory=dict)

    # For WAIT decisions
    wait_conditions: List[str] = field(default_factory=list)
    wait_timeout_seconds: Optional[float] = None

    # For INVESTIGATE decisions
    investigation_queries: List[str] = field(default_factory=list)

    # For ESCALATE decisions
    escalation_reason: Optional[str] = None
    escalation_priority: Optional[str] = None

    # Tracking
    observation_ids: List[str] = field(default_factory=list)
    context_hash: Optional[str] = None

    # Outcome (filled after execution)
    executed: bool = False
    outcome: Optional[str] = None
    outcome_success: Optional[bool] = None
    outcome_timestamp: Optional[datetime] = None


class ConfidenceThresholds:
    """Threshold values for decision confidence."""

    # Minimum confidence to take action
    ACT_THRESHOLD = 0.70

    # Below this, investigate instead
    INVESTIGATE_THRESHOLD = 0.50

    # Below this, escalate to human
    ESCALATE_THRESHOLD = 0.30

    # High confidence for critical actions
    CRITICAL_ACT_THRESHOLD = 0.85

    @classmethod
    def determine_type(
        cls,
        confidence: float,
        is_critical: bool = False
    ) -> DecisionType:
        """Determine decision type based on confidence."""

        threshold = cls.CRITICAL_ACT_THRESHOLD if is_critical else cls.ACT_THRESHOLD

        if confidence >= threshold:
            return DecisionType.ACT
        elif confidence >= cls.INVESTIGATE_THRESHOLD:
            return DecisionType.INVESTIGATE
        elif confidence >= cls.ESCALATE_THRESHOLD:
            return DecisionType.WAIT
        else:
            return DecisionType.ESCALATE
```

### 2.2 Multi-Step Reasoning

The Decision Engine never makes single-shot decisions. Every observation goes through the complete reasoning pipeline.

```python
"""
Multi-step reasoning pipeline.
The core of the Decision Engine.
"""
import json
from typing import Tuple
from dataclasses import dataclass


@dataclass
class ReasoningStep:
    """A single step in the reasoning process."""
    step_name: str
    input_summary: str
    output: Any
    confidence_delta: float
    reasoning: str


class MultiStepReasoner:
    """
    Multi-step reasoning pipeline for decisions.

    Follows the pattern:
    OBSERVE -> CATEGORIZE -> MATCH_PATTERN -> EVALUATE -> DECIDE

    Each step refines understanding and builds confidence.
    """

    def __init__(self, consciousness_llm):
        """
        Initialize with the Consciousness LLM.

        Args:
            consciousness_llm: Local LM Studio LLM for reasoning
        """
        self.llm = consciousness_llm
        self.reasoning_trace: List[ReasoningStep] = []

    async def reason(
        self,
        context: DecisionContext
    ) -> Tuple[Decision, List[ReasoningStep]]:
        """
        Perform multi-step reasoning to reach a decision.

        Args:
            context: Complete decision context

        Returns:
            Tuple of (Decision, reasoning trace)
        """
        self.reasoning_trace = []
        base_confidence = 0.5

        # STEP 1: OBSERVE
        # Summarize what we're seeing
        observation_summary = await self._step_observe(context)
        base_confidence += observation_summary["confidence_delta"]

        # STEP 2: CATEGORIZE
        # Classify the observation and determine significance
        categorization = await self._step_categorize(context, observation_summary)
        base_confidence += categorization["confidence_delta"]

        # STEP 3: MATCH PATTERN
        # Find matching patterns from history and knowledge
        pattern_match = await self._step_match_pattern(
            context, observation_summary, categorization
        )
        base_confidence += pattern_match["confidence_delta"]

        # STEP 4: EVALUATE
        # Assess options and their likely outcomes
        evaluation = await self._step_evaluate(
            context, observation_summary, categorization, pattern_match
        )
        base_confidence += evaluation["confidence_delta"]

        # STEP 5: DECIDE
        # Make final decision based on all previous steps
        decision = await self._step_decide(
            context,
            observation_summary,
            categorization,
            pattern_match,
            evaluation,
            confidence=min(1.0, max(0.0, base_confidence))
        )

        return decision, self.reasoning_trace

    async def _step_observe(
        self,
        context: DecisionContext
    ) -> Dict[str, Any]:
        """
        STEP 1: OBSERVE

        Summarize observations and identify key facts.
        """
        prompt = f"""You are analyzing observations for the Consciousness system.

OBSERVATIONS:
{chr(10).join(o.to_context_string() for o in context.observations)}

FILE CONTENT (if applicable):
{context.file_content[:1000] if context.file_content else "N/A"}

TASK: Summarize what is being observed.

Provide:
1. brief_summary: One sentence describing what happened
2. key_facts: List of 3-5 important facts
3. significance: How significant is this? (low/medium/high/critical)
4. confidence_delta: How much does this observation add to confidence? (-0.1 to +0.2)

Return as JSON.
"""

        result = await self._llm_call(prompt)

        self.reasoning_trace.append(ReasoningStep(
            step_name="OBSERVE",
            input_summary=f"{len(context.observations)} observations",
            output=result,
            confidence_delta=result.get("confidence_delta", 0),
            reasoning=result.get("brief_summary", "")
        ))

        return result

    async def _step_categorize(
        self,
        context: DecisionContext,
        observation_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        STEP 2: CATEGORIZE

        Classify the observation and understand its nature.
        """
        prompt = f"""You are categorizing an observation for the Consciousness system.

OBSERVATION SUMMARY:
{observation_summary['brief_summary']}

KEY FACTS:
{json.dumps(observation_summary['key_facts'], indent=2)}

CURRENT CONTEXT:
- Active tasks: {len(context.active_tasks)}
- Active goals: {context.active_goals[:3]}
- Category from classifier: {context.observations[0].category.value}

TASK: Provide deeper categorization.

Answer:
1. primary_intent: What is the purpose/intent behind this change? (new_content/update/fix/cleanup/unknown)
2. domain: What domain does this belong to? (philosophy/technical/system/meta)
3. requires_action: Does this require us to do something? (yes/no/maybe)
4. action_urgency: If action needed, how urgent? (immediate/soon/whenever/none)
5. confidence_delta: How much does categorization add to confidence? (-0.1 to +0.15)

Return as JSON.
"""

        result = await self._llm_call(prompt)

        self.reasoning_trace.append(ReasoningStep(
            step_name="CATEGORIZE",
            input_summary=observation_summary["brief_summary"],
            output=result,
            confidence_delta=result.get("confidence_delta", 0),
            reasoning=f"Intent: {result.get('primary_intent', 'unknown')}"
        ))

        return result

    async def _step_match_pattern(
        self,
        context: DecisionContext,
        observation_summary: Dict[str, Any],
        categorization: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        STEP 3: MATCH PATTERN

        Find similar past situations and their outcomes.
        """
        past_decisions_text = json.dumps(context.past_decisions[:5], indent=2) \
            if context.past_decisions else "No past decisions found"

        prompt = f"""You are matching patterns for the Consciousness system.

CURRENT SITUATION:
{observation_summary['brief_summary']}
Intent: {categorization['primary_intent']}
Requires action: {categorization['requires_action']}

PAST DECISIONS FOR SIMILAR OBSERVATIONS:
{past_decisions_text}

AVAILABLE ACTION TEMPLATES:
{json.dumps(context.action_templates, indent=2)}

TASK: Match to patterns and templates.

Answer:
1. matched_pattern: Does this match a known pattern? (describe or "none")
2. recommended_template: Which action template fits best? (from list or "none")
3. past_success_rate: What was success rate of past similar decisions? (0-100 or "unknown")
4. pattern_confidence: How confident in the pattern match? (0.0-1.0)
5. confidence_delta: How much does pattern matching add to confidence? (-0.1 to +0.2)

Return as JSON.
"""

        result = await self._llm_call(prompt)

        self.reasoning_trace.append(ReasoningStep(
            step_name="MATCH_PATTERN",
            input_summary=f"Matching against {len(context.past_decisions)} past decisions",
            output=result,
            confidence_delta=result.get("confidence_delta", 0),
            reasoning=f"Template: {result.get('recommended_template', 'none')}"
        ))

        return result

    async def _step_evaluate(
        self,
        context: DecisionContext,
        observation_summary: Dict[str, Any],
        categorization: Dict[str, Any],
        pattern_match: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        STEP 4: EVALUATE

        Assess options and predict outcomes.
        """
        prompt = f"""You are evaluating options for the Consciousness system.

SITUATION SUMMARY:
{observation_summary['brief_summary']}
Significance: {observation_summary['significance']}
Requires action: {categorization['requires_action']}
Matched pattern: {pattern_match['matched_pattern']}
Recommended template: {pattern_match['recommended_template']}

RESOURCES AVAILABLE:
{json.dumps(context.resource_availability, indent=2)}

TASK: Evaluate options.

Consider these options:
1. ACT - Execute the recommended action now
2. WAIT - Do nothing, continue observing
3. INVESTIGATE - Gather more information first
4. ESCALATE - Flag for human review

For each option, assess:
- likelihood_of_success (0-100)
- risk_level (low/medium/high)
- resource_cost (low/medium/high)

Also provide:
- recommended_option: Which option is best?
- reasoning: Why this option?
- confidence_delta: How much does evaluation add to confidence? (-0.1 to +0.15)

Return as JSON with "options" array and recommendation.
"""

        result = await self._llm_call(prompt)

        self.reasoning_trace.append(ReasoningStep(
            step_name="EVALUATE",
            input_summary="Evaluating 4 options",
            output=result,
            confidence_delta=result.get("confidence_delta", 0),
            reasoning=result.get("reasoning", "")[:100]
        ))

        return result

    async def _step_decide(
        self,
        context: DecisionContext,
        observation_summary: Dict[str, Any],
        categorization: Dict[str, Any],
        pattern_match: Dict[str, Any],
        evaluation: Dict[str, Any],
        confidence: float
    ) -> Decision:
        """
        STEP 5: DECIDE

        Make the final decision based on all reasoning steps.
        """
        # Determine decision type based on confidence
        is_critical = observation_summary.get("significance") == "critical"
        decision_type = ConfidenceThresholds.determine_type(confidence, is_critical)

        # Build decision based on type
        decision = Decision(
            id=f"dec-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            timestamp=datetime.now(),
            decision_type=decision_type,
            confidence=confidence,
            reasoning=self._build_reasoning_summary(),
            observation_ids=[o.id for o in context.observations]
        )

        if decision_type == DecisionType.ACT:
            # Determine action details
            template = pattern_match.get("recommended_template")

            if template:
                action_details = await self._get_action_details(
                    template,
                    context,
                    observation_summary,
                    categorization
                )
                decision.action_template = template
                decision.action_target = ActionTarget(
                    action_details.get("target", "claude_code")
                )
                decision.action_prompt = action_details.get("prompt")
                decision.action_params = action_details.get("params", {})
            else:
                # Generate custom action
                decision.action_target = ActionTarget.CLAUDE_CODE
                decision.action_prompt = await self._generate_action_prompt(
                    context, observation_summary
                )

        elif decision_type == DecisionType.WAIT:
            decision.wait_conditions = [
                f"Wait for related observations",
                f"Monitor for {observation_summary['significance']} significance changes"
            ]
            decision.wait_timeout_seconds = 60.0 if is_critical else 300.0

        elif decision_type == DecisionType.INVESTIGATE:
            decision.investigation_queries = await self._generate_investigation_queries(
                context, observation_summary, categorization
            )

        elif decision_type == DecisionType.ESCALATE:
            decision.escalation_reason = f"Low confidence ({confidence:.2f}) on {observation_summary['significance']} observation"
            decision.escalation_priority = "high" if is_critical else "medium"

        self.reasoning_trace.append(ReasoningStep(
            step_name="DECIDE",
            input_summary=f"Final decision with {confidence:.2f} confidence",
            output={"decision_type": decision_type.value, "confidence": confidence},
            confidence_delta=0,
            reasoning=decision.reasoning
        ))

        return decision

    async def _llm_call(self, prompt: str) -> Dict[str, Any]:
        """Make LLM call and parse JSON response."""
        response = await self.llm.generate(prompt, json_mode=True)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"error": "Failed to parse response", "raw": response}

    def _build_reasoning_summary(self) -> str:
        """Build summary of reasoning trace."""
        steps = []
        for step in self.reasoning_trace:
            steps.append(f"{step.step_name}: {step.reasoning}")
        return " -> ".join(steps)

    async def _get_action_details(
        self,
        template: str,
        context: DecisionContext,
        observation_summary: Dict[str, Any],
        categorization: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get action details from template."""
        # See Action Templates section
        from .action_templates import ActionTemplateRegistry
        return ActionTemplateRegistry.get_action_details(
            template, context, observation_summary, categorization
        )

    async def _generate_action_prompt(
        self,
        context: DecisionContext,
        observation_summary: Dict[str, Any]
    ) -> str:
        """Generate custom action prompt."""
        prompt = f"""Generate a Claude Code prompt for handling this observation:

OBSERVATION:
{observation_summary['brief_summary']}

FILE PATH:
{context.observations[0].path if context.observations[0].path else "N/A"}

GOAL:
Handle this observation appropriately and update any relevant indices or knowledge.

Return ONLY the prompt text that should be sent to Claude Code.
"""
        return await self.llm.generate(prompt)

    async def _generate_investigation_queries(
        self,
        context: DecisionContext,
        observation_summary: Dict[str, Any],
        categorization: Dict[str, Any]
    ) -> List[str]:
        """Generate queries for investigation."""
        prompt = f"""What additional information would help make a decision?

OBSERVATION:
{observation_summary['brief_summary']}

CATEGORIZATION:
Intent: {categorization['primary_intent']}
Domain: {categorization['domain']}

UNCERTAINTY:
We're not confident enough to act. What should we investigate?

Return a JSON array of 3-5 specific questions or investigation tasks.
"""
        result = await self._llm_call(prompt)
        return result if isinstance(result, list) else []
```

---

## Part III: Action Templates

### 3.1 Template Registry

Action templates define pre-configured actions with trigger conditions and execution details.

```yaml
# /Users/chris/Developer/stoffy/config/action-templates.yaml

# =============================================================================
# ACTION TEMPLATES
# =============================================================================
# Pre-defined actions for the Consciousness to execute.
# Each template specifies:
# - trigger: When this action applies
# - conditions: Additional requirements
# - target: Execution target (claude_code, claude_flow, internal)
# - prompt_template: Template for generating execution prompt
# - parameters: Required/optional parameters
# - success_criteria: How to determine if action succeeded
# =============================================================================

templates:

  # ---------------------------------------------------------------------------
  # INTAKE PROCESSING
  # ---------------------------------------------------------------------------
  process_intake:
    name: "Process Intake File"
    description: "Process a new file in the intake directory"

    trigger:
      observation_category: "intake"
      observation_types:
        - "file_created"
        - "file_modified"
      path_patterns:
        - "_input/*"
        - "_intake/*"

    conditions:
      - "file_extension in ['.md', '.txt', '.yaml', '.pdf']"
      - "file_size < 10MB"

    target: "claude_code"
    agent: "researcher"

    prompt_template: |
      Process the intake file at: {{ path }}

      Tasks:
      1. Analyze the content and determine its type (source, thought, thinker info, etc.)
      2. Extract key information and themes
      3. Determine appropriate storage location in the knowledge base
      4. Create necessary files in the correct locations
      5. Update relevant indices

      Content preview:
      {{ content_preview }}

      Store results in: knowledge/philosophy/
      Update indices in: indices/philosophy/

    parameters:
      path:
        type: "path"
        required: true
        description: "Path to intake file"
      content_preview:
        type: "string"
        required: false
        max_length: 2000
        description: "Preview of file content"

    success_criteria:
      - "Output contains 'created' or 'updated'"
      - "No error messages in output"

    timeout_seconds: 300
    max_retries: 2

  # ---------------------------------------------------------------------------
  # INDEX MANAGEMENT
  # ---------------------------------------------------------------------------
  update_index:
    name: "Update Index Files"
    description: "Update index files after knowledge changes"

    trigger:
      observation_category: "knowledge"
      observation_types:
        - "file_created"
        - "file_modified"
        - "file_deleted"
      path_patterns:
        - "knowledge/**/*.md"
        - "knowledge/**/*.yaml"

    conditions:
      - "not path.endswith('index.yaml')"
      - "not path.endswith('index.md')"

    target: "claude_code"
    agent: "code-analyzer"

    prompt_template: |
      A knowledge file has been {{ change_type }}: {{ path }}

      Tasks:
      1. Identify which indices need updating based on the file location
      2. Read current index files
      3. Update indices to reflect the change
      4. Ensure cross-references are maintained

      Index locations:
      - indices/philosophy/thinkers.yaml
      - indices/philosophy/sources.yaml
      - indices/philosophy/thoughts.yaml
      - indices/philosophy/themes.yaml

      Only update indices that are actually affected by this change.

    parameters:
      path:
        type: "path"
        required: true
      change_type:
        type: "enum"
        values: ["created", "modified", "deleted"]
        required: true

    success_criteria:
      - "Index files updated successfully"

    timeout_seconds: 180
    max_retries: 1

  # ---------------------------------------------------------------------------
  # RESEARCH AND ANALYSIS
  # ---------------------------------------------------------------------------
  research_topic:
    name: "Research a Topic"
    description: "Deep research on a philosophical or technical topic"

    trigger:
      observation_category: "knowledge"
      observation_types:
        - "file_created"
      path_patterns:
        - "knowledge/**/thoughts/**"

    conditions:
      - "file contains 'needs_research: true' or 'status: draft'"

    target: "claude_flow"
    topology: "mesh"
    strategy: "parallel"

    prompt_template: |
      Research the following topic in depth:

      Topic: {{ topic }}
      Context: {{ context }}

      Research objectives:
      1. Find relevant sources and references
      2. Identify key thinkers who have addressed this topic
      3. Map connections to existing knowledge
      4. Identify gaps in current understanding
      5. Generate synthesis document

      Store findings in: knowledge/philosophy/thoughts/{{ domain }}/
      Cross-reference with: thinkers, sources, themes

    parameters:
      topic:
        type: "string"
        required: true
      context:
        type: "string"
        required: false
      domain:
        type: "string"
        required: true
        default: "general"

    agents:
      - type: "researcher"
        task: "Find sources and references"
      - type: "code-analyzer"
        task: "Analyze existing knowledge connections"
      - type: "coder"
        task: "Generate synthesis document"

    success_criteria:
      - "Research document created"
      - "At least 3 sources identified"

    timeout_seconds: 600
    max_retries: 1

  # ---------------------------------------------------------------------------
  # THINKER MANAGEMENT
  # ---------------------------------------------------------------------------
  create_thinker:
    name: "Create Thinker Profile"
    description: "Create a complete profile for a new thinker"

    trigger:
      observation_category: "intake"
      content_patterns:
        - "new thinker:"
        - "philosopher:"
        - "create profile for"

    target: "claude_code"
    agent: "researcher"

    prompt_template: |
      Create a complete thinker profile for: {{ thinker_name }}

      Use the templates at: templates/philosophy/
      - thinker_profile.md (main profile)
      - thinker_notes.md (reading notes)
      - thinker_references.md (works and citations)
      - thinker_reflections.md (personal reflections)

      Store in: knowledge/philosophy/thinkers/{{ thinker_slug }}/

      Include:
      1. Biographical information
      2. Major works and contributions
      3. Key concepts and terminology
      4. Philosophical positions
      5. Connections to other thinkers
      6. Relevance to current themes

      Update indices:
      - indices/philosophy/thinkers.yaml

    parameters:
      thinker_name:
        type: "string"
        required: true
      thinker_slug:
        type: "string"
        required: true
        description: "URL-safe name (e.g., 'immanuel_kant')"
      era:
        type: "string"
        required: false

    success_criteria:
      - "Profile directory created"
      - "All four template files populated"
      - "Thinker index updated"

    timeout_seconds: 300
    max_retries: 2

  # ---------------------------------------------------------------------------
  # ERROR HANDLING
  # ---------------------------------------------------------------------------
  handle_failure:
    name: "Handle Task Failure"
    description: "Respond to a failed task execution"

    trigger:
      observation_types:
        - "task_failed"
        - "process_failed"

    conditions:
      - "error_count < 3"  # Don't infinite loop

    target: "internal"

    prompt_template: |
      A task has failed. Analyze and determine recovery:

      Task: {{ task_description }}
      Error: {{ error_message }}
      Attempt: {{ attempt_number }} of {{ max_attempts }}

      Options:
      1. Retry with same parameters
      2. Retry with modified parameters
      3. Escalate to human review
      4. Mark as unrecoverable

      Consider:
      - Is the error transient or permanent?
      - Can we work around the issue?
      - Is human intervention needed?

    parameters:
      task_description:
        type: "string"
        required: true
      error_message:
        type: "string"
        required: true
      attempt_number:
        type: "integer"
        required: true
      max_attempts:
        type: "integer"
        required: true
        default: 3

    success_criteria:
      - "Recovery decision made"

    timeout_seconds: 60
    max_retries: 0

  # ---------------------------------------------------------------------------
  # PERIODIC MAINTENANCE
  # ---------------------------------------------------------------------------
  periodic_index_sync:
    name: "Periodic Index Synchronization"
    description: "Ensure all indices are in sync with actual files"

    trigger:
      observation_types:
        - "schedule_triggered"
      schedule: "0 */4 * * *"  # Every 4 hours

    target: "claude_code"
    agent: "code-analyzer"

    prompt_template: |
      Perform a full index synchronization:

      1. Scan all files in knowledge/philosophy/
      2. Compare against entries in indices/philosophy/
      3. Add missing entries
      4. Remove orphaned entries
      5. Fix any inconsistencies

      Report:
      - Files found
      - Index entries
      - Additions made
      - Removals made
      - Errors encountered

    success_criteria:
      - "Sync completed"
      - "No critical errors"

    timeout_seconds: 600
    max_retries: 1
```

### 3.2 Template Processing

```python
"""
Action template processing and instantiation.
"""
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml


class ActionTemplateRegistry:
    """
    Registry of action templates.

    Loads templates from YAML and provides matching/instantiation.
    """

    def __init__(self, template_path: Path):
        """
        Initialize registry from template file.

        Args:
            template_path: Path to action-templates.yaml
        """
        self.template_path = template_path
        self.templates: Dict[str, Dict[str, Any]] = {}
        self._load_templates()

    def _load_templates(self):
        """Load templates from YAML file."""
        if self.template_path.exists():
            with open(self.template_path) as f:
                data = yaml.safe_load(f)
                self.templates = data.get("templates", {})

    def match(
        self,
        observation: 'Observation',
        context: Optional['DecisionContext'] = None
    ) -> List[str]:
        """
        Find templates that match an observation.

        Args:
            observation: Observation to match
            context: Optional decision context

        Returns:
            List of matching template names
        """
        matches = []

        for name, template in self.templates.items():
            if self._template_matches(template, observation, context):
                matches.append(name)

        return matches

    def _template_matches(
        self,
        template: Dict[str, Any],
        observation: 'Observation',
        context: Optional['DecisionContext']
    ) -> bool:
        """Check if a template matches an observation."""
        trigger = template.get("trigger", {})

        # Check observation category
        if "observation_category" in trigger:
            if observation.category.value != trigger["observation_category"]:
                return False

        # Check observation type
        if "observation_types" in trigger:
            if observation.observation_type.value not in trigger["observation_types"]:
                return False

        # Check path patterns
        if "path_patterns" in trigger and observation.path:
            path_str = str(observation.path)
            if not any(
                self._path_matches(path_str, pattern)
                for pattern in trigger["path_patterns"]
            ):
                return False

        # Check conditions
        conditions = template.get("conditions", [])
        for condition in conditions:
            if not self._evaluate_condition(condition, observation, context):
                return False

        return True

    def _path_matches(self, path: str, pattern: str) -> bool:
        """Check if path matches glob pattern."""
        # Convert glob to regex
        regex = pattern.replace("**/", ".*").replace("*", "[^/]*")
        return bool(re.search(regex, path))

    def _evaluate_condition(
        self,
        condition: str,
        observation: 'Observation',
        context: Optional['DecisionContext']
    ) -> bool:
        """Evaluate a condition string."""
        # Simple condition evaluation
        # In production, use a proper expression evaluator

        if "file_extension" in condition:
            if not observation.path:
                return False
            ext = observation.path.suffix
            return eval(condition.replace("file_extension", f"'{ext}'"))

        if "file_size" in condition:
            if not observation.path or not observation.path.exists():
                return False
            size = observation.path.stat().st_size
            # Convert condition like "file_size < 10MB" to bytes comparison
            condition = condition.replace("10MB", str(10 * 1024 * 1024))
            return eval(condition.replace("file_size", str(size)))

        return True

    def instantiate(
        self,
        template_name: str,
        context: 'DecisionContext',
        observation_summary: Dict[str, Any],
        categorization: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Instantiate a template with context values.

        Args:
            template_name: Name of template to instantiate
            context: Decision context
            observation_summary: Summarized observation
            categorization: Categorization results

        Returns:
            Instantiated action details
        """
        template = self.templates.get(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")

        # Build parameter values
        params = self._build_parameters(template, context, observation_summary)

        # Render prompt template
        prompt = self._render_prompt(
            template.get("prompt_template", ""),
            params
        )

        return {
            "target": template.get("target", "claude_code"),
            "agent": template.get("agent"),
            "prompt": prompt,
            "params": params,
            "timeout": template.get("timeout_seconds", 300),
            "max_retries": template.get("max_retries", 2),
            "success_criteria": template.get("success_criteria", []),
            "topology": template.get("topology"),
            "strategy": template.get("strategy"),
            "agents": template.get("agents", [])
        }

    def _build_parameters(
        self,
        template: Dict[str, Any],
        context: 'DecisionContext',
        observation_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build parameter values from context."""
        params = {}
        param_specs = template.get("parameters", {})

        # Auto-populate from context
        if context.observations:
            obs = context.observations[0]
            if obs.path:
                params["path"] = str(obs.path)

            params["change_type"] = obs.observation_type.value.replace("file_", "")

        if context.file_content:
            params["content_preview"] = context.file_content[:2000]

        # Add observation summary
        params["topic"] = observation_summary.get("brief_summary", "")
        params["context"] = str(observation_summary.get("key_facts", []))

        return params

    def _render_prompt(
        self,
        template_str: str,
        params: Dict[str, Any]
    ) -> str:
        """Render prompt template with parameters."""
        result = template_str

        for key, value in params.items():
            placeholder = "{{ " + key + " }}"
            result = result.replace(placeholder, str(value))

        return result
```

---

## Part IV: Decision Loop

### 4.1 Main Decision Loop

```python
"""
Main decision loop implementation.
The continuous cycle of consciousness.
"""
import asyncio
from datetime import datetime
from typing import Optional, List
import structlog

logger = structlog.get_logger()


class DecisionLoop:
    """
    The main decision loop of the Consciousness.

    Implements: OBSERVE -> CATEGORIZE -> MATCH_PATTERN -> EVALUATE -> DECIDE -> ACT/WAIT
    """

    def __init__(
        self,
        observation_queue: ObservationQueue,
        context_builder: ContextBuilder,
        reasoner: MultiStepReasoner,
        action_executor: 'ActionExecutor',
        decision_history: 'DecisionHistory',
        config: 'LoopConfig'
    ):
        self.observations = observation_queue
        self.context_builder = context_builder
        self.reasoner = reasoner
        self.executor = action_executor
        self.history = decision_history
        self.config = config

        # State
        self.running = False
        self.iteration_count = 0
        self.last_decision: Optional[Decision] = None

    async def run(self):
        """
        Run the decision loop continuously.

        This is the main entry point for the Consciousness.
        """
        self.running = True
        logger.info("Decision loop started")

        while self.running:
            try:
                await self._iteration()
            except Exception as e:
                logger.error("Decision loop error", error=str(e))
                await asyncio.sleep(self.config.error_backoff_seconds)

            # Rate limiting
            await asyncio.sleep(self.config.iteration_delay_seconds)

    async def stop(self):
        """Stop the decision loop gracefully."""
        logger.info("Stopping decision loop")
        self.running = False

    async def _iteration(self):
        """
        Single iteration of the decision loop.

        OBSERVE -> CATEGORIZE -> MATCH_PATTERN -> EVALUATE -> DECIDE -> ACT/WAIT
        """
        self.iteration_count += 1
        iteration_start = datetime.now()

        # ==== OBSERVE ====
        # Get next observation(s) from queue
        observations = await self._observe()

        if not observations:
            # Nothing to process, light sleep
            return

        logger.info(
            "Processing observations",
            count=len(observations),
            urgency=observations[0].urgency.value
        )

        # ==== BUILD CONTEXT ====
        # Gather all relevant context
        context = await self.context_builder.build(observations)

        # ==== REASON (CATEGORIZE -> MATCH -> EVALUATE -> DECIDE) ====
        # Multi-step reasoning to reach decision
        decision, trace = await self.reasoner.reason(context)

        logger.info(
            "Decision made",
            decision_type=decision.decision_type.value,
            confidence=decision.confidence,
            reasoning=decision.reasoning[:100]
        )

        # ==== ACT or WAIT ====
        await self._execute_decision(decision, context)

        # ==== RECORD ====
        await self._record_decision(decision, trace, observations)

        # Update state
        self.last_decision = decision

        iteration_duration = (datetime.now() - iteration_start).total_seconds()
        logger.debug(
            "Iteration complete",
            iteration=self.iteration_count,
            duration_seconds=iteration_duration
        )

    async def _observe(self) -> List[Observation]:
        """
        OBSERVE phase: Get observations from queue.

        Returns:
            List of observations to process (may be empty)
        """
        # Check for critical observations first
        critical = self.observations.get_all_critical()
        if critical:
            return critical

        # Otherwise, get next observation
        obs = self.observations.get_next()
        if obs:
            return [obs]

        return []

    async def _execute_decision(
        self,
        decision: Decision,
        context: DecisionContext
    ):
        """
        Execute the decision (ACT, WAIT, INVESTIGATE, or ESCALATE).
        """
        if decision.decision_type == DecisionType.ACT:
            await self._execute_action(decision)

        elif decision.decision_type == DecisionType.WAIT:
            await self._execute_wait(decision)

        elif decision.decision_type == DecisionType.INVESTIGATE:
            await self._execute_investigate(decision, context)

        elif decision.decision_type == DecisionType.ESCALATE:
            await self._execute_escalate(decision)

    async def _execute_action(self, decision: Decision):
        """Execute an ACT decision."""
        logger.info(
            "Executing action",
            target=decision.action_target.value if decision.action_target else "unknown",
            template=decision.action_template
        )

        try:
            result = await self.executor.execute(decision)

            decision.executed = True
            decision.outcome_timestamp = datetime.now()
            decision.outcome_success = result.success
            decision.outcome = result.output if result.success else result.error

        except Exception as e:
            decision.executed = True
            decision.outcome_success = False
            decision.outcome = str(e)
            logger.error("Action execution failed", error=str(e))

    async def _execute_wait(self, decision: Decision):
        """Execute a WAIT decision."""
        logger.info(
            "Waiting",
            conditions=decision.wait_conditions,
            timeout=decision.wait_timeout_seconds
        )

        decision.executed = True
        decision.outcome = "Waiting"
        decision.outcome_success = True

    async def _execute_investigate(
        self,
        decision: Decision,
        context: DecisionContext
    ):
        """Execute an INVESTIGATE decision."""
        logger.info(
            "Investigating",
            queries=decision.investigation_queries
        )

        # Create investigation tasks
        for query in decision.investigation_queries:
            # Add investigation task to queue
            await self.executor.queue_investigation(query, context)

        decision.executed = True
        decision.outcome = f"Queued {len(decision.investigation_queries)} investigations"
        decision.outcome_success = True

    async def _execute_escalate(self, decision: Decision):
        """Execute an ESCALATE decision."""
        logger.warning(
            "Escalating to human",
            reason=decision.escalation_reason,
            priority=decision.escalation_priority
        )

        # Write escalation to file for human review
        await self._write_escalation(decision)

        decision.executed = True
        decision.outcome = "Escalated to human review"
        decision.outcome_success = True

    async def _record_decision(
        self,
        decision: Decision,
        trace: List[ReasoningStep],
        observations: List[Observation]
    ):
        """Record decision for learning."""
        await self.history.record(
            decision=decision,
            reasoning_trace=trace,
            observations=observations
        )

    async def _write_escalation(self, decision: Decision):
        """Write escalation notice for human review."""
        escalation_path = Path("_escalations")
        escalation_path.mkdir(exist_ok=True)

        filename = f"{decision.timestamp.strftime('%Y%m%d_%H%M%S')}_{decision.escalation_priority}.md"

        content = f"""# Escalation Notice

**Time**: {decision.timestamp.isoformat()}
**Priority**: {decision.escalation_priority}
**Confidence**: {decision.confidence:.2f}

## Reason
{decision.escalation_reason}

## Context
Observation IDs: {decision.observation_ids}

## Reasoning
{decision.reasoning}

## Action Required
Please review and determine appropriate action.
"""

        (escalation_path / filename).write_text(content)


@dataclass
class LoopConfig:
    """Configuration for the decision loop."""
    iteration_delay_seconds: float = 0.5
    error_backoff_seconds: float = 5.0
    max_observations_per_iteration: int = 10
    enable_learning: bool = True
```

---

## Part V: Learning and Adaptation

### 5.1 Decision History

```python
"""
Decision history and learning from outcomes.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import sqlite3
import aiosqlite


class DecisionHistory:
    """
    Store and query decision history for learning.

    Tracks:
    - All decisions made
    - Reasoning traces
    - Outcomes
    - Pattern frequencies
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._initialized = False

    async def initialize(self):
        """Initialize the database schema."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS decisions (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    decision_type TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    reasoning TEXT,
                    action_target TEXT,
                    action_template TEXT,
                    executed INTEGER DEFAULT 0,
                    outcome_success INTEGER,
                    outcome TEXT,
                    outcome_timestamp TEXT,
                    observation_category TEXT,
                    observation_type TEXT,
                    path_pattern TEXT
                );

                CREATE TABLE IF NOT EXISTS reasoning_traces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    decision_id TEXT NOT NULL,
                    step_name TEXT NOT NULL,
                    step_order INTEGER NOT NULL,
                    input_summary TEXT,
                    output_json TEXT,
                    confidence_delta REAL,
                    reasoning TEXT,
                    FOREIGN KEY (decision_id) REFERENCES decisions(id)
                );

                CREATE TABLE IF NOT EXISTS pattern_stats (
                    pattern_key TEXT PRIMARY KEY,
                    total_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    last_used TEXT,
                    avg_confidence REAL
                );

                CREATE INDEX IF NOT EXISTS idx_decisions_category
                ON decisions(observation_category);

                CREATE INDEX IF NOT EXISTS idx_decisions_type
                ON decisions(decision_type);

                CREATE INDEX IF NOT EXISTS idx_decisions_timestamp
                ON decisions(timestamp);
            """)
            await db.commit()

        self._initialized = True

    async def record(
        self,
        decision: Decision,
        reasoning_trace: List[ReasoningStep],
        observations: List[Observation]
    ):
        """Record a decision and its reasoning trace."""
        if not self._initialized:
            await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            # Insert decision
            await db.execute("""
                INSERT INTO decisions (
                    id, timestamp, decision_type, confidence, reasoning,
                    action_target, action_template, executed, outcome_success,
                    outcome, outcome_timestamp, observation_category,
                    observation_type, path_pattern
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                decision.id,
                decision.timestamp.isoformat(),
                decision.decision_type.value,
                decision.confidence,
                decision.reasoning,
                decision.action_target.value if decision.action_target else None,
                decision.action_template,
                1 if decision.executed else 0,
                1 if decision.outcome_success else 0 if decision.outcome_success is False else None,
                decision.outcome,
                decision.outcome_timestamp.isoformat() if decision.outcome_timestamp else None,
                observations[0].category.value if observations else None,
                observations[0].observation_type.value if observations else None,
                str(observations[0].path) if observations and observations[0].path else None
            ))

            # Insert reasoning trace
            for i, step in enumerate(reasoning_trace):
                await db.execute("""
                    INSERT INTO reasoning_traces (
                        decision_id, step_name, step_order, input_summary,
                        output_json, confidence_delta, reasoning
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    decision.id,
                    step.step_name,
                    i,
                    step.input_summary,
                    json.dumps(step.output) if step.output else None,
                    step.confidence_delta,
                    step.reasoning
                ))

            # Update pattern stats
            pattern_key = self._make_pattern_key(decision, observations)
            await self._update_pattern_stats(db, pattern_key, decision)

            await db.commit()

    async def find_similar(
        self,
        observation_type: Optional[str] = None,
        category: Optional[str] = None,
        path_pattern: Optional[str] = None,
        limit: int = 5
    ) -> List[Observation]:
        """Find similar past observations."""
        # This would typically return Observation objects from the DB
        # For now, returning empty list as placeholder
        return []

    async def get_decisions_for_category(
        self,
        category: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get past decisions for an observation category."""
        if not self._initialized:
            await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT
                    observation_type,
                    decision_type,
                    action_template,
                    outcome_success,
                    CASE
                        WHEN outcome_success = 1 THEN 'success'
                        WHEN outcome_success = 0 THEN 'failure'
                        ELSE 'unknown'
                    END as outcome
                FROM decisions
                WHERE observation_category = ?
                AND executed = 1
                ORDER BY timestamp DESC
                LIMIT ?
            """, (category, limit))

            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    def _make_pattern_key(
        self,
        decision: Decision,
        observations: List[Observation]
    ) -> str:
        """Create a key for pattern tracking."""
        parts = [
            observations[0].category.value if observations else "unknown",
            observations[0].observation_type.value if observations else "unknown",
            decision.decision_type.value,
            decision.action_template or "custom"
        ]
        return ":".join(parts)

    async def _update_pattern_stats(
        self,
        db: aiosqlite.Connection,
        pattern_key: str,
        decision: Decision
    ):
        """Update pattern statistics."""
        await db.execute("""
            INSERT INTO pattern_stats (pattern_key, total_count, success_count, last_used, avg_confidence)
            VALUES (?, 1, ?, ?, ?)
            ON CONFLICT(pattern_key) DO UPDATE SET
                total_count = total_count + 1,
                success_count = success_count + CASE WHEN ? = 1 THEN 1 ELSE 0 END,
                last_used = ?,
                avg_confidence = (avg_confidence * total_count + ?) / (total_count + 1)
        """, (
            pattern_key,
            1 if decision.outcome_success else 0,
            datetime.now().isoformat(),
            decision.confidence,
            1 if decision.outcome_success else 0,
            datetime.now().isoformat(),
            decision.confidence
        ))


class ConfidenceAdjuster:
    """
    Adjust confidence based on historical outcomes.

    Learns which patterns tend to succeed and adjusts future
    confidence scores accordingly.
    """

    def __init__(self, history: DecisionHistory):
        self.history = history

    async def adjust_confidence(
        self,
        base_confidence: float,
        pattern_key: str
    ) -> float:
        """
        Adjust confidence based on pattern history.

        Args:
            base_confidence: Initial confidence from reasoning
            pattern_key: Pattern identifier

        Returns:
            Adjusted confidence
        """
        stats = await self._get_pattern_stats(pattern_key)

        if not stats or stats["total_count"] < 3:
            # Not enough history, return base confidence
            return base_confidence

        success_rate = stats["success_count"] / stats["total_count"]

        # Blend base confidence with historical success rate
        # Weight historical data more as we have more samples
        history_weight = min(0.5, stats["total_count"] / 20)

        adjusted = (
            base_confidence * (1 - history_weight) +
            success_rate * history_weight
        )

        return adjusted

    async def _get_pattern_stats(self, pattern_key: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a pattern."""
        async with aiosqlite.connect(self.history.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM pattern_stats WHERE pattern_key = ?
            """, (pattern_key,))

            row = await cursor.fetchone()
            return dict(row) if row else None
```

### 5.2 Learning from Outcomes

```python
"""
Learning from decision outcomes.
"""


class OutcomeLearner:
    """
    Learn from decision outcomes to improve future decisions.

    Tracks:
    - Which templates work for which observation types
    - Confidence calibration
    - Common failure patterns
    """

    def __init__(
        self,
        history: DecisionHistory,
        adjuster: ConfidenceAdjuster
    ):
        self.history = history
        self.adjuster = adjuster
        self.lessons: List[Dict[str, Any]] = []

    async def learn_from_outcome(
        self,
        decision: Decision,
        actual_outcome: Dict[str, Any]
    ):
        """
        Learn from a decision outcome.

        Args:
            decision: The decision that was made
            actual_outcome: What actually happened
        """
        # Update decision record with outcome
        await self._update_decision_outcome(decision, actual_outcome)

        # Analyze the outcome
        lesson = await self._analyze_outcome(decision, actual_outcome)

        if lesson:
            self.lessons.append(lesson)
            await self._apply_lesson(lesson)

    async def _update_decision_outcome(
        self,
        decision: Decision,
        outcome: Dict[str, Any]
    ):
        """Update decision record with actual outcome."""
        async with aiosqlite.connect(self.history.db_path) as db:
            await db.execute("""
                UPDATE decisions
                SET outcome_success = ?,
                    outcome = ?,
                    outcome_timestamp = ?
                WHERE id = ?
            """, (
                1 if outcome.get("success") else 0,
                json.dumps(outcome),
                datetime.now().isoformat(),
                decision.id
            ))
            await db.commit()

    async def _analyze_outcome(
        self,
        decision: Decision,
        outcome: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Analyze outcome to extract lessons."""

        if outcome.get("success") and decision.confidence < 0.5:
            # Low confidence but succeeded - we can be more confident
            return {
                "type": "confidence_too_low",
                "pattern": decision.action_template,
                "adjustment": "increase",
                "reason": "Succeeded despite low confidence"
            }

        if not outcome.get("success") and decision.confidence > 0.8:
            # High confidence but failed - we were overconfident
            return {
                "type": "confidence_too_high",
                "pattern": decision.action_template,
                "adjustment": "decrease",
                "reason": f"Failed despite high confidence: {outcome.get('error', 'unknown')}"
            }

        if not outcome.get("success"):
            # Analyze failure reason
            error = outcome.get("error", "")

            if "timeout" in error.lower():
                return {
                    "type": "timeout_failure",
                    "pattern": decision.action_template,
                    "adjustment": "increase_timeout",
                    "reason": "Task timed out"
                }

            if "permission" in error.lower() or "access" in error.lower():
                return {
                    "type": "permission_failure",
                    "pattern": decision.action_template,
                    "adjustment": "check_permissions",
                    "reason": "Permission/access error"
                }

        return None

    async def _apply_lesson(self, lesson: Dict[str, Any]):
        """Apply a learned lesson to improve future decisions."""

        lesson_type = lesson["type"]

        if lesson_type == "confidence_too_low":
            # Record that this pattern tends to succeed
            logger.info(
                "Lesson learned: Increase confidence for pattern",
                pattern=lesson["pattern"]
            )

        elif lesson_type == "confidence_too_high":
            # Record that this pattern may fail
            logger.warning(
                "Lesson learned: Decrease confidence for pattern",
                pattern=lesson["pattern"],
                reason=lesson["reason"]
            )

        elif lesson_type == "timeout_failure":
            # Suggest longer timeouts
            logger.info(
                "Lesson learned: Consider longer timeout",
                pattern=lesson["pattern"]
            )

        # Store lesson for future reference
        lessons_path = Path("_learning/lessons.jsonl")
        lessons_path.parent.mkdir(exist_ok=True)

        with open(lessons_path, "a") as f:
            lesson["timestamp"] = datetime.now().isoformat()
            f.write(json.dumps(lesson) + "\n")
```

---

## Summary

The Decision Engine architecture provides:

1. **Observation Processing**
   - Classification by type, urgency, and category
   - Prioritization for processing order
   - Context building from multiple sources

2. **Decision Framework**
   - Four decision types: ACT, WAIT, INVESTIGATE, ESCALATE
   - Multi-step reasoning: OBSERVE -> CATEGORIZE -> MATCH_PATTERN -> EVALUATE -> DECIDE
   - Confidence-based decision thresholds

3. **Action Templates**
   - Pre-defined actions for common scenarios
   - YAML-based configuration
   - Template matching and instantiation

4. **Decision Loop**
   - Continuous iteration
   - Graceful handling of all decision types
   - Recording for learning

5. **Learning and Adaptation**
   - Decision history tracking
   - Pattern statistics
   - Confidence adjustment based on outcomes
   - Lesson extraction from failures

This architecture ensures the Consciousness makes thoughtful, traceable, and improving decisions over time.
