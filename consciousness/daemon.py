"""
Autonomous Consciousness Daemon

Fully autonomous OIDA Loop Orchestrator with learning and git integration.

OIDA = Observe -> Infer -> Decide -> Act

Components:
1. watcher.py - File system observation
2. git_watcher.py - Git repository observation
3. thinker.py - LM Studio reasoning (FULLY AUTONOMOUS)
4. executor.py - Claude Code/Flow execution
5. learner.py - Pattern learning from outcomes

The daemon is FULLY AUTONOMOUS:
- It observes changes and decides freely what to do
- It is NOT limited to templates - the LLM decides
- It learns from outcomes over time
- It executes without asking permission
"""

import asyncio
import signal
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import json

import structlog

# Import existing modules
from .config import ConsciousnessConfig, load_config
from .watcher import ConsciousnessWatcher, FileChange
from .watcher_git import GitWatcher, GitStatus, GitObservation
from .thinker import ConsciousnessThinker, Decision, DecisionType, ActionType
from .executor import ClaudeCodeExecutor, ExecutionResult, ExecutionMode
from .state import StateManager, Event, EventType, ThoughtRecord, ActionRecord
from .learning import PatternLearner
from .learning.integration import LearningIntegration, LearningConfig
from .decision.engine import AutonomousEngine, EngineDecision

# Configure structlog (simple console output)
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer(colors=True),
    ],
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger("consciousness")


# =============================================================================
# Autonomous Executor - Handles all action types
# =============================================================================

class AutonomousExecutor:
    """
    Executes any action type the LLM decides on.

    Supports:
    - write_file: Direct file writing
    - run_python: Execute Python code
    - run_bash: Execute shell commands
    - claude_code: Delegate to Claude Code CLI
    - claude_flow: Spawn Claude Flow swarms
    - think: Record deep thoughts
    - debate: Internal dialectic
    - research: Research tasks
    - custom: Custom actions
    """

    def __init__(
        self,
        working_dir: Path,
        timeout: int = 300,
        claude_executor: Optional[ClaudeCodeExecutor] = None,
    ):
        """
        Initialize the autonomous executor.

        Args:
            working_dir: Working directory for execution
            timeout: Default timeout in seconds
            claude_executor: Optional pre-configured Claude executor
        """
        self.working_dir = Path(working_dir)
        self.timeout = timeout
        self.claude_executor = claude_executor or ClaudeCodeExecutor(working_dir, timeout)

    async def execute(self, decision: EngineDecision) -> ExecutionResult:
        """
        Execute any decision the LLM makes.

        Args:
            decision: The engine decision to execute

        Returns:
            ExecutionResult with success status and output
        """
        if not decision.should_act or not decision.action:
            return ExecutionResult(
                success=True,
                output="No action needed",
                mode=ExecutionMode.SIMPLE,
            )

        action = decision.action
        action_type = action.type

        logger.info(
            "autonomous.executing",
            action_type=action_type.value,
            description=action.description[:100],
            priority=action.priority.value,
        )

        try:
            if action_type == ActionType.WRITE_FILE:
                return await self._execute_write_file(action)

            elif action_type == ActionType.RUN_PYTHON:
                return await self._execute_python(action)

            elif action_type == ActionType.RUN_BASH:
                return await self._execute_bash(action)

            elif action_type == ActionType.CLAUDE_CODE:
                return await self._execute_claude_code(action, decision)

            elif action_type == ActionType.CLAUDE_FLOW:
                return await self._execute_claude_flow(action, decision)

            elif action_type == ActionType.THINK:
                return await self._execute_think(action)

            elif action_type == ActionType.DEBATE:
                return await self._execute_debate(action)

            elif action_type == ActionType.RESEARCH:
                return await self._execute_research(action, decision)

            else:
                # Custom or unknown - try to handle generically
                return await self._execute_custom(action, decision)

        except Exception as e:
            logger.exception("autonomous.execute_error", error=str(e))
            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
            )

    async def _execute_write_file(self, action) -> ExecutionResult:
        """Execute a write_file action."""
        file_path = action.file_path or action.details.get("file_path", "")
        content = action.details.get("content", "")

        if not file_path:
            return ExecutionResult(
                success=False,
                output="",
                error="No file_path specified for write_file action",
            )

        try:
            full_path = self.working_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")

            return ExecutionResult(
                success=True,
                output=f"Wrote {len(content)} bytes to {file_path}",
                mode=ExecutionMode.SIMPLE,
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Failed to write file: {e}",
            )

    async def _execute_python(self, action) -> ExecutionResult:
        """Execute a run_python action."""
        code = action.code or action.details.get("code", "")

        if not code:
            return ExecutionResult(
                success=False,
                output="",
                error="No code specified for run_python action",
            )

        try:
            process = await asyncio.create_subprocess_exec(
                "python3", "-c", code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.working_dir),
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout,
            )

            return ExecutionResult(
                success=process.returncode == 0,
                output=stdout.decode("utf-8", errors="replace"),
                error=stderr.decode("utf-8", errors="replace") if process.returncode != 0 else None,
                mode=ExecutionMode.SIMPLE,
            )
        except asyncio.TimeoutError:
            return ExecutionResult(
                success=False,
                output="",
                error="Python execution timed out",
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Python execution failed: {e}",
            )

    async def _execute_bash(self, action) -> ExecutionResult:
        """Execute a run_bash action."""
        command = action.command or action.details.get("command", "")

        if not command:
            return ExecutionResult(
                success=False,
                output="",
                error="No command specified for run_bash action",
            )

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.working_dir),
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout,
            )

            return ExecutionResult(
                success=process.returncode == 0,
                output=stdout.decode("utf-8", errors="replace"),
                error=stderr.decode("utf-8", errors="replace") if process.returncode != 0 else None,
                mode=ExecutionMode.SIMPLE,
            )
        except asyncio.TimeoutError:
            return ExecutionResult(
                success=False,
                output="",
                error="Bash execution timed out",
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Bash execution failed: {e}",
            )

    async def _execute_claude_code(self, action, decision: EngineDecision) -> ExecutionResult:
        """Execute a claude_code action."""
        prompt = action.prompt or decision.prompt or action.description

        if not prompt:
            return ExecutionResult(
                success=False,
                output="",
                error="No prompt specified for claude_code action",
            )

        return await self.claude_executor.execute(prompt)

    async def _execute_claude_flow(self, action, decision: EngineDecision) -> ExecutionResult:
        """Execute a claude_flow action."""
        prompt = action.prompt or decision.prompt or action.description

        if not prompt:
            return ExecutionResult(
                success=False,
                output="",
                error="No prompt specified for claude_flow action",
            )

        return await self.claude_executor.execute_swarm(prompt)

    async def _execute_think(self, action) -> ExecutionResult:
        """Execute a think action - deep reflection."""
        topic = action.details.get("topic", action.description)
        depth = action.details.get("depth", "medium")

        # For think actions, we just record the intention
        # The actual thinking already happened in the thinker
        return ExecutionResult(
            success=True,
            output=f"Contemplated '{topic}' at {depth} depth. Reasoning recorded.",
            mode=ExecutionMode.SIMPLE,
            metadata={"action": "think", "topic": topic, "depth": depth},
        )

    async def _execute_debate(self, action) -> ExecutionResult:
        """Execute a debate action - internal dialectic."""
        thesis = action.details.get("thesis", "")
        antithesis = action.details.get("antithesis", "")

        return ExecutionResult(
            success=True,
            output=f"Debated: '{thesis}' vs '{antithesis}'. Dialectic recorded.",
            mode=ExecutionMode.SIMPLE,
            metadata={"action": "debate", "thesis": thesis, "antithesis": antithesis},
        )

    async def _execute_research(self, action, decision: EngineDecision) -> ExecutionResult:
        """Execute a research action."""
        query = action.details.get("query", action.description)

        # Research actions use Claude Flow for multi-agent research
        prompt = f"Research the following topic thoroughly: {query}"
        return await self.claude_executor.execute_swarm(prompt)

    async def _execute_custom(self, action, decision: EngineDecision) -> ExecutionResult:
        """Execute a custom action."""
        # For custom actions, try to interpret the details
        custom_action = action.details.get("custom_action", "")

        if custom_action:
            # Try to execute as Claude Code
            return await self.claude_executor.execute(
                f"{action.description}\n\nDetails: {custom_action}"
            )

        return ExecutionResult(
            success=True,
            output=f"Custom action noted: {action.description}",
            mode=ExecutionMode.SIMPLE,
        )


# =============================================================================
# Autonomous Daemon
# =============================================================================

class ConsciousnessDaemon:
    """
    Fully autonomous OIDA loop daemon.

    OBSERVE: Watch file system and git for changes
    INFER: Use LM Studio to interpret observations
    DECIDE: LLM decides freely what to do (no template constraints)
    ACT: Execute decisions via appropriate executor

    The daemon:
    - Gathers all context (files, git, learned patterns)
    - Lets the LLM decide autonomously what to do
    - Executes without confirmation
    - Learns from outcomes
    """

    def __init__(
        self,
        config: Optional[ConsciousnessConfig] = None,
        config_path: Optional[Path] = None,
        mode: str = "autonomous",  # "autonomous", "supervised", "dry-run"
    ):
        """
        Initialize the Autonomous Consciousness Daemon.

        Args:
            config: Pre-loaded configuration object
            config_path: Path to consciousness.yaml file
            mode: Operating mode
        """
        self.config = config or load_config(config_path)
        self.mode = mode
        self.running = False

        # Get root path
        self.root_path = Path(self.config.watcher.root_path).resolve()

        # Initialize watchers
        self.file_watcher = ConsciousnessWatcher(
            root_path=self.root_path,
            ignore_patterns=self.config.watcher.ignore_patterns,
            debounce_ms=self.config.watcher.debounce_ms,
        )

        self.git_watcher = GitWatcher(repo_path=self.root_path)

        # Initialize thinker (AUTONOMOUS MODE)
        self.thinker = ConsciousnessThinker(
            base_url=self.config.lm_studio.base_url,
            model=self.config.lm_studio.model,
            temperature=self.config.lm_studio.temperature,
            max_tokens=self.config.lm_studio.max_tokens,
            autonomous=True,
        )

        # Initialize executors
        self.claude_executor = ClaudeCodeExecutor(
            working_dir=self.root_path,
            timeout=self.config.executor.timeout_seconds,
        )

        self.executor = AutonomousExecutor(
            working_dir=self.root_path,
            timeout=self.config.executor.timeout_seconds,
            claude_executor=self.claude_executor,
        )

        # Initialize autonomous engine
        self.engine = AutonomousEngine(
            thinker=self.thinker,
            confidence_threshold=self.config.decision.min_confidence,
            working_dir=self.root_path,
        )

        # Initialize state and learning
        self.state = StateManager(self.config.state.database_path)
        self.learning = LearningIntegration(
            db_path=self.config.state.database_path,
            config=LearningConfig(
                record_all_outcomes=True,
                enable_confidence_adjustment=True,
                pattern_update_interval=25,
            ),
        )

        # Statistics
        self._cycle_count = 0
        self._decisions_made = 0
        self._actions_executed = 0
        self._last_decision: Optional[EngineDecision] = None
        self._last_git_observation: Optional[GitObservation] = None

        # Background watcher queue
        self._change_queue: asyncio.Queue[list[FileChange]] = asyncio.Queue()
        self._watcher_task: Optional[asyncio.Task] = None

    async def _background_watcher(self) -> None:
        """Background task that continuously watches for file changes."""
        logger.info("daemon.watcher.started")
        try:
            async for batch in self.file_watcher.watch():
                if not self.running:
                    break
                await self._change_queue.put(batch)
                logger.debug("daemon.watcher.queued", count=len(batch))
        except asyncio.CancelledError:
            logger.info("daemon.watcher.cancelled")
        except Exception as e:
            logger.exception("daemon.watcher.error", error=str(e))

    def request_shutdown(self) -> None:
        """Request graceful shutdown."""
        self.running = False
        self.file_watcher.stop()
        if self._watcher_task:
            self._watcher_task.cancel()
        logger.info("daemon.shutdown_requested")

    async def run(self) -> None:
        """
        Main run loop - Autonomous OIDA cycle.

        Observe -> Infer -> Decide -> Act -> Learn -> repeat
        """
        logger.info("daemon.starting", config={
            "lm_studio_url": self.config.lm_studio.base_url,
            "model": self.config.lm_studio.model,
            "mode": self.mode,
            "confidence_threshold": self.config.decision.min_confidence,
            "thinking_interval": self.config.decision.thinking_interval_seconds,
            "root_path": str(self.root_path),
        })

        self.running = True

        # Initialize components
        await self.state.initialize()
        await self.learning.initialize()

        # Check LM Studio connection
        connected = await self.thinker.check_connection()
        if not connected:
            logger.warning(
                "daemon.lm_studio_not_connected",
                url=self.config.lm_studio.base_url,
            )

        # Check git
        is_git_repo = await self.git_watcher.is_git_repo()
        if is_git_repo:
            logger.info("daemon.git_integration_enabled")

        # Start background file watcher
        self._watcher_task = asyncio.create_task(self._background_watcher())
        logger.info("daemon.background_watcher_started")

        try:
            while self.running:
                await self._autonomous_cycle()
                await asyncio.sleep(self.config.decision.thinking_interval_seconds)

        except Exception as e:
            logger.exception("daemon.error", error=str(e))
            raise

        finally:
            await self._shutdown()

    async def _autonomous_cycle(self) -> None:
        """
        Single autonomous OIDA cycle.

        1. OBSERVE: Gather file changes and git status
        2. Get learned patterns
        3. INFER & DECIDE: Let LLM think autonomously
        4. ACT: Execute without confirmation
        5. LEARN: Record outcome for future improvement
        """
        self._cycle_count += 1
        cycle_start = datetime.now(timezone.utc)

        logger.info("daemon.cycle.start", cycle=self._cycle_count, mode=self.mode)

        # 1. OBSERVE: Get file changes from background queue
        changes: list[FileChange] = []
        try:
            # Check queue with timeout - collect all pending changes
            while True:
                try:
                    batch = await asyncio.wait_for(
                        self._change_queue.get(),
                        timeout=0.5 if not changes else 0.1
                    )
                    changes.extend(batch)
                except asyncio.TimeoutError:
                    break
        except Exception as e:
            logger.warning("daemon.cycle.queue_error", error=str(e))

        if not changes:
            logger.debug("daemon.cycle.no_changes")
            return

        logger.info("daemon.cycle.changes_detected", count=len(changes))

        # Get git observation
        git_status_str = ""
        if await self.git_watcher.is_git_repo():
            git_observation = await self.git_watcher.get_observation()
            git_status_str = self.git_watcher.format_for_llm(git_observation)
            self._last_git_observation = git_observation

        # Log observations
        await self.state.record_event(Event(
            event_type=EventType.OBSERVATION,
            data={
                "changes": [
                    {"path": c.relative_path, "type": c.change_type}
                    for c in changes
                ],
                "count": len(changes),
                "has_git_context": bool(git_status_str),
            },
        ))

        # 2. Get learned patterns/suggestions
        observations = self.file_watcher.format_for_llm(changes)
        suggestions = await self.learning.get_suggestions(observations)
        learned_patterns = [
            f"{s.action_type}: {s.reasoning} (confidence: {s.confidence:.2f})"
            for s in suggestions
        ]

        if learned_patterns:
            logger.debug("daemon.cycle.learned_patterns", count=len(learned_patterns))

        # 3. INFER & DECIDE: Autonomous thinking
        decision = await self.engine.decide(
            observations=observations,
            git_status=git_status_str,
            learned_patterns=learned_patterns,
            additional_context={
                "cycle": self._cycle_count,
                "mode": self.mode,
                "total_actions": self._actions_executed,
            },
        )

        self._decisions_made += 1
        self._last_decision = decision

        logger.info(
            "daemon.cycle.decision",
            should_act=decision.should_act,
            confidence=decision.confidence,
            executor_type=decision.executor_type,
            reasoning_preview=decision.reasoning[:100] if decision.reasoning else "",
        )

        # Record thought
        await self.state.record_thought(ThoughtRecord(
            prompt=observations,
            response=json.dumps(decision.to_dict()),
            confidence=decision.confidence,
        ))

        # 4. ACT: Execute if decided
        result: Optional[ExecutionResult] = None

        if decision.should_act:
            if self.mode == "dry-run":
                # Dry run - log but don't execute
                logger.info(
                    "daemon.cycle.dry_run",
                    action_type=decision.action.type.value if decision.action else "none",
                    description=decision.action.description if decision.action else "",
                )
                result = ExecutionResult(
                    success=True,
                    output="[DRY RUN] Action would be executed",
                    mode=ExecutionMode.SIMPLE,
                )
            elif self.mode == "supervised":
                # Supervised - would ask for confirmation (not implemented in daemon)
                logger.info("daemon.cycle.supervised_mode", action=decision.action)
                result = ExecutionResult(
                    success=True,
                    output="[SUPERVISED] Confirmation required",
                    mode=ExecutionMode.SIMPLE,
                )
            else:
                # Autonomous - execute without confirmation
                logger.info(
                    "daemon.cycle.executing",
                    action_type=decision.action.type.value if decision.action else "none",
                    priority=decision.priority,
                )
                result = await self.executor.execute(decision)
                self._actions_executed += 1

            # Log result
            if result:
                logger.info(
                    "daemon.cycle.executed",
                    success=result.success,
                    output_preview=result.output[:200] if result.output else "",
                    error=result.error,
                )

                # Record action
                await self.state.record_action(ActionRecord(
                    action_type=decision.executor_type,
                    command=decision.prompt or (decision.action.description if decision.action else ""),
                    result=result.output,
                    success=result.success,
                ))

                # 5. LEARN: Record outcome for pattern learning
                if decision.action:
                    await self.learning.record_outcome(
                        observation=decision.observation_summary or observations[:200],
                        action_type=decision.action.type.value,
                        action_details=decision.action.description,
                        result=result,
                        confidence_used=decision.confidence,
                        context={
                            "cycle": self._cycle_count,
                            "reasoning": decision.reasoning[:500],
                            "git_branch": (
                                self._last_git_observation.status.branch
                                if self._last_git_observation else ""
                            ),
                        },
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

        self.file_watcher.stop()
        self.git_watcher.stop()

        # Cancel background watcher
        if self._watcher_task:
            self._watcher_task.cancel()
            try:
                await self._watcher_task
            except asyncio.CancelledError:
                pass

        await self.learning.close()
        await self.state.close()

        # Get final learning stats
        learning_status = await self.learning.get_learning_status()

        logger.info(
            "daemon.shutdown_complete",
            cycles=self._cycle_count,
            decisions=self._decisions_made,
            actions=self._actions_executed,
            learning_status=learning_status,
        )

    async def get_status(self) -> dict:
        """Get current daemon status."""
        stats = await self.state.get_statistics()
        learning_status = await self.learning.get_learning_status()
        engine_stats = self.engine.get_statistics()

        return {
            "running": self.running,
            "mode": self.mode,
            "cycle_count": self._cycle_count,
            "decisions_made": self._decisions_made,
            "actions_executed": self._actions_executed,
            "last_decision": self._last_decision.to_dict() if self._last_decision else None,
            "last_git_observation": (
                self.git_watcher.format_for_llm_compact(self._last_git_observation)
                if self._last_git_observation else None
            ),
            "database_stats": stats,
            "learning_status": learning_status,
            "engine_stats": engine_stats,
        }


def setup_signal_handlers(daemon: ConsciousnessDaemon) -> None:
    """Set up signal handlers for graceful shutdown."""

    def signal_handler(sig: int, frame) -> None:
        logger.info("daemon.signal_received", signal=sig)
        daemon.request_shutdown()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


# =============================================================================
# Main entry point
# =============================================================================

async def run_autonomous_daemon(
    config_path: Optional[Path] = None,
    mode: str = "autonomous",
) -> None:
    """
    Run the fully autonomous consciousness daemon.

    Args:
        config_path: Path to configuration file
        mode: Operating mode ("autonomous", "supervised", "dry-run")
    """
    daemon = ConsciousnessDaemon(config_path=config_path, mode=mode)
    setup_signal_handlers(daemon)
    await daemon.run()


if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "autonomous"
    asyncio.run(run_autonomous_daemon(mode=mode))
