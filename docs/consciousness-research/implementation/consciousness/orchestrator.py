"""
Consciousness Orchestrator - Main OIDA Loop

The central coordinator implementing:
- OBSERVE: Gather observations from all observers
- INFER: Use LM Studio to interpret and reason
- DECIDE: Evaluate decisions against metacognitive gate
- ACT: Delegate approved actions to Claude API

Implements:
- Global Workspace (ARCH-004): Capacity 7 focused items
- Strange Loop: Self-observation feeds back into processing
- Expected Free Energy: Balances pragmatic and epistemic value
"""

import asyncio
from datetime import datetime
from typing import Any, Optional

import structlog

from .config import ConsciousnessConfig
from .decision import DecisionEvaluator, GoalManager
from .execution import ClaudeExecutor, TaskQueue
from .inference import LMStudioReasoner, Decision
from .observers import Observation, ObserverLevel
from .observers.filesystem import FileSystemObserver
from .state import StateDatabase

logger = structlog.get_logger()


class GlobalWorkspace:
    """
    Global Workspace implementation (GWT).

    Implements ARCH-004: Capacity of 7 items (Miller's number).
    Items compete for workspace access based on salience.
    Selected items are broadcast to all modules.
    """

    def __init__(self, capacity: int = 7, salience_decay: float = 0.95):
        self.capacity = capacity
        self.salience_decay = salience_decay
        self._workspace: list[tuple[float, Observation]] = []  # (salience, observation)
        self._history: list[Observation] = []

    def submit(self, observation: Observation) -> bool:
        """Submit observation to compete for workspace access."""
        salience = observation.priority

        # Add to workspace
        self._workspace.append((salience, observation))

        # Sort by salience (highest first)
        self._workspace.sort(key=lambda x: -x[0])

        # Trim to capacity
        if len(self._workspace) > self.capacity:
            evicted = self._workspace.pop()
            self._history.append(evicted[1])
            return salience > evicted[0]  # Return True if this observation stayed

        return True

    def get_focused(self) -> list[Observation]:
        """Get observations currently in the workspace."""
        return [obs for _, obs in self._workspace]

    def decay(self) -> None:
        """Decay salience of all items."""
        self._workspace = [
            (s * self.salience_decay, obs)
            for s, obs in self._workspace
        ]
        # Remove items below threshold
        self._workspace = [
            (s, obs) for s, obs in self._workspace
            if s > 0.1
        ]

    def clear(self) -> None:
        """Clear the workspace."""
        self._history.extend([obs for _, obs in self._workspace])
        self._workspace.clear()


class ConsciousnessOrchestrator:
    """
    Main orchestrator implementing the OIDA loop.

    Coordinates all components:
    - Observers (file system, processes, git)
    - Reasoner (LM Studio)
    - Evaluator (decision gate)
    - Executor (Claude API)
    - State (persistence)
    """

    def __init__(self, config: ConsciousnessConfig):
        self.config = config
        self._shutdown_requested = False

        # Initialize components
        self.workspace = GlobalWorkspace(
            capacity=config.global_workspace.capacity,
            salience_decay=config.global_workspace.salience_decay_rate,
        )

        self.reasoner = LMStudioReasoner(config.lm_studio)

        self.evaluator = DecisionEvaluator(
            min_confidence=config.decision.min_confidence_to_act,
            max_concurrent_tasks=config.decision.max_concurrent_tasks,
            dry_run=config.decision.dry_run,
        )

        self.executor = ClaudeExecutor(config.anthropic)
        self.task_queue = TaskQueue(
            max_concurrent=config.tasks.max_queue_size,
            default_timeout=config.tasks.default_timeout_seconds,
        )

        self.goal_manager = GoalManager()
        self.state = StateDatabase(config.state.database_path)

        # Observers
        self.filesystem_observer = FileSystemObserver(
            watch_paths=config.observers.filesystem.watch_paths,
            ignore_patterns=config.observers.filesystem.ignore_patterns,
            debounce_ms=config.observers.filesystem.debounce_ms,
        )

        # Decision history for strange loop
        self._recent_decisions: list[Decision] = []
        self._cycle_count = 0

    async def run(self) -> None:
        """Main run loop - OIDA cycle."""
        logger.info("consciousness.starting", config=self.config.model_dump())

        # Initialize
        await self.state.connect()
        self.goal_manager.initialize_defaults()
        await self.filesystem_observer.start()

        try:
            while not self._shutdown_requested:
                await self._oida_cycle()
                await asyncio.sleep(self.config.decision.thinking_interval_seconds)

        except Exception as e:
            logger.exception("consciousness.error", error=str(e))
            raise

        finally:
            await self._shutdown()

    async def _oida_cycle(self) -> None:
        """Single OIDA cycle: Observe → Infer → Decide → Act."""
        self._cycle_count += 1
        cycle_start = datetime.utcnow()

        logger.info("consciousness.cycle.start", cycle=self._cycle_count)

        # OBSERVE
        observations = await self._observe()

        # Submit to global workspace
        for obs in observations:
            self.workspace.submit(obs)

        focused = self.workspace.get_focused()

        if not focused:
            logger.debug("consciousness.cycle.no_observations")
            self.workspace.decay()
            return

        # INFER
        context = await self._build_context()
        decision = await self._infer(focused, context)

        # Store for strange loop
        self._recent_decisions.append(decision)
        if len(self._recent_decisions) > 20:
            self._recent_decisions = self._recent_decisions[-20:]

        # DECIDE
        evaluation = self.evaluator.evaluate(
            decision,
            current_goals=self.goal_manager.get_goals_as_strings(),
            active_tasks=self.task_queue.active_count,
        )

        logger.info(
            "consciousness.cycle.decision",
            decision=decision.decision.value,
            confidence=decision.confidence,
            gate_result=evaluation.gate_result.value,
            should_execute=evaluation.should_execute,
        )

        # Save decision to history
        await self.state.save_decision(decision)

        # ACT
        if evaluation.should_execute and decision.action:
            await self._act(decision)

        # Decay workspace
        self.workspace.decay()

        # Periodic reflection (strange loop)
        if self._cycle_count % 10 == 0:
            await self._reflect()

        cycle_duration = (datetime.utcnow() - cycle_start).total_seconds()
        logger.info("consciousness.cycle.complete", duration=cycle_duration)

    async def _observe(self) -> list[Observation]:
        """OBSERVE phase: Gather observations from all sources."""
        observations = []

        # File system observations
        fs_obs = await self.filesystem_observer.get_observations()
        observations.extend(fs_obs)

        # Self-observation (strange loop)
        if self._recent_decisions:
            last_decision = self._recent_decisions[-1]
            self_obs = Observation(
                event_type="pattern_detected",
                source="self_observer",
                level=ObserverLevel.METACOGNITIVE,
                priority=0.4,
                payload={
                    "type": "recent_decision",
                    "decision": last_decision.decision.value,
                    "confidence": last_decision.confidence,
                    "uncertainty_count": len(last_decision.self_assessment.uncertainty_sources),
                },
            )
            observations.append(self_obs)

        logger.debug("consciousness.observe", count=len(observations))
        return observations

    async def _infer(
        self,
        observations: list[Observation],
        context: dict[str, Any],
    ) -> Decision:
        """INFER phase: Use LM Studio to reason about observations."""
        decision = await self.reasoner.think(observations, context)

        logger.debug(
            "consciousness.infer",
            decision=decision.decision.value,
            confidence=decision.confidence,
            reasoning_length=len(decision.reasoning),
        )

        return decision

    async def _act(self, decision: Decision) -> None:
        """ACT phase: Delegate action to Claude API."""
        if not decision.action:
            return

        logger.info(
            "consciousness.act",
            action_type=decision.action.type.value,
            description=decision.action.description[:100],
        )

        # Add to task queue
        task = await self.task_queue.add(decision.action)

        # Execute (could be async in background)
        result = await self.executor.execute_task(decision.action)

        # Complete task
        await self.task_queue.complete(
            task.id,
            result.content if result.success else result.error,
            success=result.success,
        )

        # Save result
        await self.state.save_decision(
            decision,
            result=result.content if result.success else result.error,
        )

    async def _build_context(self) -> dict[str, Any]:
        """Build context for reasoning."""
        return {
            "active_tasks": [
                f"{t.action.description} ({t.status.value})"
                for t in self.task_queue.get_running_tasks()
            ],
            "goals": self.goal_manager.get_goals_as_strings(),
            "recent_decisions": [
                f"{d.decision.value} (conf: {d.confidence:.2f})"
                for d in self._recent_decisions[-5:]
            ],
            "cycle_count": self._cycle_count,
            "queue_status": self.task_queue.get_status(),
        }

    async def _reflect(self) -> None:
        """Metacognitive reflection (strange loop)."""
        if not self._recent_decisions:
            return

        logger.info("consciousness.reflecting")

        reflection = await self.reasoner.reflect(self._recent_decisions)

        # Save reflection as self-observation
        await self.state.save_self_observation(
            "metacognitive_reflection",
            str(reflection),
            {"cycle": self._cycle_count},
        )

        logger.debug("consciousness.reflected", reflection=reflection)

    def request_shutdown(self) -> None:
        """Request graceful shutdown."""
        self._shutdown_requested = True

    async def _shutdown(self) -> None:
        """Graceful shutdown."""
        logger.info("consciousness.shutting_down")

        await self.filesystem_observer.stop()
        await self.state.close()

        logger.info("consciousness.shutdown_complete")
