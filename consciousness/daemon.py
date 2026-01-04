"""
Consciousness Daemon - Main OIDA Loop Orchestrator

Ties together the three components:
1. watcher.py - File system observation
2. thinker.py - LM Studio reasoning
3. executor.py - Claude Code execution

Implements:
- Async main loop with asyncio
- Graceful shutdown on SIGINT/SIGTERM
- Logging with structlog
- State persistence with SQLite
- Configuration via consciousness.yaml
"""

import asyncio
import signal
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import structlog

# Import existing modules
from .config import ConsciousnessConfig, load_config
from .watcher import ConsciousnessWatcher, FileChange
from .thinker import ConsciousnessThinker, Decision, DecisionType, ActionType
from .executor import ClaudeCodeExecutor, ExecutionResult, ExecutionMode
from .state import StateManager, Event, EventType, ThoughtRecord, ActionRecord

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger("consciousness")


# =============================================================================
# Main Daemon
# =============================================================================

class ConsciousnessDaemon:
    """
    Main daemon that orchestrates the OIDA loop.

    Coordinates watcher, thinker, and executor components using the
    existing implementations from watcher.py, thinker.py, and executor.py.

    OIDA Loop:
        1. OBSERVE: Watch file system for changes (watcher.py)
        2. INFER: Use LM Studio to interpret observations (thinker.py)
        3. DECIDE: Determine if action is needed (confidence > 0.7)
        4. ACT: Delegate tasks to Claude Code (executor.py)
    """

    def __init__(
        self,
        config: Optional[ConsciousnessConfig] = None,
        config_path: Optional[Path] = None,
    ):
        """
        Initialize the Consciousness Daemon.

        Args:
            config: Pre-loaded configuration object
            config_path: Path to consciousness.yaml file
        """
        self.config = config or load_config(config_path)
        self.running = False

        # Get root path
        self.root_path = Path(self.config.watcher.root_path).resolve()

        # Initialize components using existing modules
        self.watcher = ConsciousnessWatcher(
            root_path=self.root_path,
            ignore_patterns=self.config.watcher.ignore_patterns,
            debounce_ms=self.config.watcher.debounce_ms,
        )

        self.thinker = ConsciousnessThinker(
            base_url=self.config.lm_studio.base_url,
            model=self.config.lm_studio.model,
            temperature=self.config.lm_studio.temperature,
            max_tokens=self.config.lm_studio.max_tokens,
        )

        self.executor = ClaudeCodeExecutor(
            working_dir=self.root_path,
            timeout=self.config.executor.timeout_seconds,
        )

        self.state = StateManager(self.config.state.database_path)

        # Statistics
        self._cycle_count = 0
        self._decisions_made = 0
        self._actions_executed = 0
        self._last_decision: Optional[Decision] = None

    def request_shutdown(self) -> None:
        """Request graceful shutdown."""
        self.running = False
        self.watcher.stop()
        logger.info("daemon.shutdown_requested")

    async def run(self) -> None:
        """
        Main run loop - OIDA cycle.

        Observe -> Infer -> Decide -> Act -> repeat
        """
        logger.info("daemon.starting", config={
            "lm_studio_url": self.config.lm_studio.base_url,
            "model": self.config.lm_studio.model,
            "confidence_threshold": self.config.decision.min_confidence,
            "thinking_interval": self.config.decision.thinking_interval_seconds,
            "root_path": str(self.root_path),
        })

        self.running = True

        # Initialize state database
        await self.state.initialize()

        # Check LM Studio connection
        connected = await self.thinker.check_connection()
        if not connected:
            logger.warning(
                "daemon.lm_studio_not_connected",
                url=self.config.lm_studio.base_url,
            )

        try:
            while self.running:
                await self._oida_cycle()
                await asyncio.sleep(self.config.decision.thinking_interval_seconds)

        except Exception as e:
            logger.exception("daemon.error", error=str(e))
            raise

        finally:
            await self._shutdown()

    async def _oida_cycle(self) -> None:
        """Single OIDA cycle: Observe -> Infer -> Decide -> Act."""
        self._cycle_count += 1
        cycle_start = datetime.now(timezone.utc)

        logger.info("daemon.cycle.start", cycle=self._cycle_count)

        # 1. OBSERVE: Get file changes from watcher
        changes: list[FileChange] = []
        async for batch in self.watcher.watch():
            changes = batch
            break  # Get one batch per cycle

        if not changes:
            logger.debug("daemon.cycle.no_changes")
            return  # No changes, skip this cycle

        # Log observations to state database
        await self.state.record_event(Event(
            event_type=EventType.OBSERVATION,
            data={
                "changes": [
                    {"path": c.relative_path, "type": c.change_type}
                    for c in changes
                ],
                "count": len(changes),
            },
        ))

        # 2. INFER: Format observations and think
        observations = self.watcher.format_for_llm(changes)
        decision = await self.thinker.think_with_memory(observations)
        self._decisions_made += 1
        self._last_decision = decision

        logger.info(
            "daemon.cycle.decision",
            decision=decision.decision.value,
            confidence=decision.confidence,
            reasoning_preview=decision.reasoning[:100] if decision.reasoning else "",
        )

        # Record thought
        await self.state.record_thought(ThoughtRecord(
            prompt=observations,
            response=decision.raw_response,
            confidence=decision.confidence,
        ))

        # 3. DECIDE & ACT: Execute if confident enough
        result: Optional[ExecutionResult] = None

        if decision.decision == DecisionType.ACT:
            if decision.confidence >= self.config.decision.min_confidence:
                if decision.action:
                    action_type = decision.action.type.value
                    prompt = decision.action.prompt

                    # 4. ACT: Execute the action
                    if decision.action.type == ActionType.CLAUDE_CODE:
                        logger.info(
                            "daemon.cycle.executing",
                            action_type=action_type,
                            prompt_preview=prompt[:100],
                        )
                        result = await self.executor.execute(prompt)
                    elif decision.action.type == ActionType.CLAUDE_FLOW:
                        logger.info(
                            "daemon.cycle.executing_swarm",
                            action_type=action_type,
                            prompt_preview=prompt[:100],
                        )
                        result = await self.executor.execute_swarm(prompt)
                    else:
                        logger.warning(
                            "daemon.cycle.unknown_action_type",
                            action_type=action_type,
                        )

                    if result:
                        if result.success:
                            self._actions_executed += 1

                        logger.info(
                            "daemon.cycle.executed",
                            success=result.success,
                            output_preview=result.output[:200] if result.output else "",
                            error=result.error,
                        )

                        # Record action
                        await self.state.record_action(ActionRecord(
                            action_type=action_type,
                            command=prompt,
                            result=result.output,
                            success=result.success,
                        ))
            else:
                logger.info(
                    "daemon.cycle.low_confidence",
                    confidence=decision.confidence,
                    threshold=self.config.decision.min_confidence,
                )

        cycle_duration = (datetime.now(timezone.utc) - cycle_start).total_seconds()
        logger.info(
            "daemon.cycle.complete",
            cycle=self._cycle_count,
            duration=cycle_duration,
            decisions_total=self._decisions_made,
            actions_total=self._actions_executed,
        )

    async def _shutdown(self) -> None:
        """Graceful shutdown of all components."""
        logger.info("daemon.shutting_down")

        self.watcher.stop()
        await self.state.close()

        logger.info(
            "daemon.shutdown_complete",
            cycles=self._cycle_count,
            decisions=self._decisions_made,
            actions=self._actions_executed,
        )

    async def get_status(self) -> dict:
        """Get current daemon status."""
        stats = await self.state.get_statistics()
        return {
            "running": self.running,
            "cycle_count": self._cycle_count,
            "decisions_made": self._decisions_made,
            "actions_executed": self._actions_executed,
            "last_decision": self._last_decision.to_dict() if self._last_decision else None,
            "database_stats": stats,
        }


def setup_signal_handlers(daemon: ConsciousnessDaemon) -> None:
    """Set up signal handlers for graceful shutdown."""

    def signal_handler(sig: int, frame) -> None:
        logger.info("daemon.signal_received", signal=sig)
        daemon.request_shutdown()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
