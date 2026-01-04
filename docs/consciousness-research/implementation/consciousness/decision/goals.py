"""
Goal Manager - Hierarchical Goal Management

Implements a 5-level goal hierarchy (from implementation spec):
1. Meta-goals: System-level objectives (e.g., "maintain Stoffy health")
2. Strategic goals: Long-term projects
3. Tactical goals: Current session objectives
4. Operational goals: Immediate tasks
5. Atomic goals: Single actions

Goals are managed with:
- Activation scoring based on relevance and recency
- Conflict resolution between competing goals
- Persistence across sessions
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Any, Optional
from uuid import UUID, uuid4


class GoalLevel(IntEnum):
    """Goal hierarchy levels."""
    META = 0        # System-level, persistent
    STRATEGIC = 1   # Long-term projects
    TACTICAL = 2    # Session objectives
    OPERATIONAL = 3 # Immediate tasks
    ATOMIC = 4      # Single actions


@dataclass
class Goal:
    """A goal in the hierarchy."""
    id: UUID = field(default_factory=uuid4)
    level: GoalLevel = GoalLevel.OPERATIONAL
    description: str = ""
    activation: float = 0.5  # 0.0 to 1.0, current relevance
    priority: float = 0.5    # 0.0 to 1.0, importance
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    parent_id: Optional[UUID] = None
    children_ids: list[UUID] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        return self.completed_at is None and self.activation > 0.1

    @property
    def is_completed(self) -> bool:
        return self.completed_at is not None

    def decay_activation(self, rate: float = 0.95) -> None:
        """Decay activation over time."""
        self.activation *= rate

    def boost_activation(self, amount: float = 0.2) -> None:
        """Boost activation when goal is referenced."""
        self.activation = min(1.0, self.activation + amount)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "level": self.level.name,
            "description": self.description,
            "activation": self.activation,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "parent_id": str(self.parent_id) if self.parent_id else None,
        }


class GoalManager:
    """
    Manages the hierarchical goal system.

    Implements:
    - Goal activation/deactivation
    - Conflict resolution
    - Persistence (via external state manager)
    """

    def __init__(self):
        self._goals: dict[UUID, Goal] = {}
        self._default_goals_initialized = False

    def initialize_defaults(self) -> None:
        """Initialize default meta-goals."""
        if self._default_goals_initialized:
            return

        # Default meta-goals (always active)
        defaults = [
            Goal(
                level=GoalLevel.META,
                description="Maintain system health and stability",
                activation=1.0,
                priority=1.0,
            ),
            Goal(
                level=GoalLevel.META,
                description="Support user productivity",
                activation=1.0,
                priority=0.9,
            ),
            Goal(
                level=GoalLevel.META,
                description="Learn and improve from experience",
                activation=0.8,
                priority=0.7,
            ),
        ]

        for goal in defaults:
            self._goals[goal.id] = goal

        self._default_goals_initialized = True

    def add_goal(self, goal: Goal) -> UUID:
        """Add a new goal."""
        self._goals[goal.id] = goal
        return goal.id

    def get_goal(self, goal_id: UUID) -> Optional[Goal]:
        """Get a goal by ID."""
        return self._goals.get(goal_id)

    def get_active_goals(self, level: Optional[GoalLevel] = None) -> list[Goal]:
        """Get all active goals, optionally filtered by level."""
        goals = [g for g in self._goals.values() if g.is_active]
        if level is not None:
            goals = [g for g in goals if g.level == level]
        return sorted(goals, key=lambda g: (-g.priority, -g.activation))

    def get_goals_as_strings(self) -> list[str]:
        """Get active goal descriptions for prompt inclusion."""
        return [g.description for g in self.get_active_goals()]

    def complete_goal(self, goal_id: UUID) -> bool:
        """Mark a goal as completed."""
        goal = self._goals.get(goal_id)
        if goal:
            goal.completed_at = datetime.utcnow()
            goal.activation = 0.0
            return True
        return False

    def decay_all_activations(self, rate: float = 0.95) -> None:
        """Decay activation for all non-meta goals."""
        for goal in self._goals.values():
            if goal.level != GoalLevel.META:
                goal.decay_activation(rate)

    def resolve_conflicts(self) -> list[tuple[Goal, Goal, str]]:
        """
        Identify and report conflicting goals.

        Returns list of (goal1, goal2, conflict_reason) tuples.
        Conflict resolution is left to the consciousness for now.
        """
        conflicts = []
        active = self.get_active_goals()

        # Simple conflict detection: same level, similar activation
        for i, g1 in enumerate(active):
            for g2 in active[i + 1:]:
                if g1.level == g2.level:
                    activation_diff = abs(g1.activation - g2.activation)
                    if activation_diff < 0.2 and g1.priority == g2.priority:
                        conflicts.append((
                            g1, g2,
                            "Similar priority and activation at same level"
                        ))

        return conflicts

    def update_from_context(self, context: dict[str, Any]) -> None:
        """
        Update goal activations based on context.

        Boosts goals that are relevant to current observations.
        """
        if "observations" in context:
            # Boost goals mentioned in observations
            obs_text = str(context["observations"]).lower()
            for goal in self._goals.values():
                if any(word in obs_text for word in goal.description.lower().split()):
                    goal.boost_activation(0.1)

    def to_dict(self) -> dict[str, Any]:
        """Export all goals for persistence."""
        return {
            str(goal_id): goal.to_dict()
            for goal_id, goal in self._goals.items()
        }
