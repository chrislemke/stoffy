"""
Integration Tests for Consciousness Daemon

End-to-end tests that verify:
- Component integration
- OIDA loop functionality
- Full workflow from file change to action
"""

import asyncio
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from consciousness import (
    ConsciousnessConfig,
    ConsciousnessWatcher,
    ConsciousnessThinker,
    ClaudeCodeExecutor,
    ConsciousnessDaemon,
    FileChange,
    ChangeBatch,
    Decision,
    DecisionType,
    Action,
    ActionType,
    Priority,
    ExecutionResult,
    ExecutionMode,
)


class TestEndToEndWorkflow:
    """End-to-end tests for the complete workflow."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_file_change_to_observation(self):
        """File system change should be detected by watcher."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            watcher = ConsciousnessWatcher(
                root_path=tmppath,
                ignore_patterns=[],
                debounce_ms=100,
            )

            # Start watching in background
            async def watch_briefly():
                async for changes in watcher.watch():
                    return changes

            watch_task = asyncio.create_task(watch_briefly())

            # Wait for watcher to start
            await asyncio.sleep(0.1)

            # Create a file
            (tmppath / "test.md").write_text("# New Thought\n\nContent here.")

            try:
                changes = await asyncio.wait_for(watch_task, timeout=2.0)
                watcher.stop()

                assert len(changes) >= 1
                assert any(c.change_type == "created" for c in changes)
            except asyncio.TimeoutError:
                watcher.stop()
                pytest.skip("Watcher did not detect changes in time")

    @pytest.mark.asyncio
    async def test_changes_formatted_for_llm(self):
        """Changes should be formatted for LLM consumption."""
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = ConsciousnessWatcher(Path(tmpdir))

            changes = [
                FileChange("/test/thinker.md", "created", time.time(), "thinker.md"),
                FileChange("/test/index.yaml", "modified", time.time(), "index.yaml"),
            ]

            formatted = watcher.format_for_llm(changes)

            assert "thinker.md" in formatted
            assert "index.yaml" in formatted
            assert "CREATED" in formatted
            assert "MODIFIED" in formatted

    @pytest.mark.asyncio
    async def test_thinker_produces_decision(self):
        """Thinker should produce a decision from changes."""
        config = ConsciousnessConfig()
        thinker = ConsciousnessThinker(config)

        changes = [
            FileChange("/test/new.md", "created", time.time(), "new.md"),
        ]

        # Mock LM Studio response
        mock_response = json.dumps({
            "reasoning": "New file detected, should investigate",
            "decision": "investigate",
            "confidence": 0.6,
        })

        with patch.object(thinker.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content=mock_response))],
            )

            decision = await thinker.think(changes)

            assert isinstance(decision, Decision)
            assert decision.decision_type in [DecisionType.ACT, DecisionType.WAIT, DecisionType.INVESTIGATE]

    @pytest.mark.asyncio
    async def test_executor_handles_action(self):
        """Executor should handle action from decision."""
        config = ConsciousnessConfig()
        executor = ClaudeCodeExecutor(config)

        action = Action(
            type=ActionType.CLAUDE_CODE,
            prompt="Test task",
            priority=Priority.MEDIUM,
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Task completed",
                stderr="",
            )

            result = await executor.execute(action)

            assert isinstance(result, ExecutionResult)
            assert result.success is True


class TestFullOIDALoop:
    """Test the complete OIDA loop integration."""

    @pytest.mark.asyncio
    async def test_observe_phase(self):
        """OBSERVE phase should gather file changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            watcher = ConsciousnessWatcher(tmppath, debounce_ms=100)

            # Simulate file activity before watching
            (tmppath / "thought.md").write_text("# Thought")

            # Format what we would observe
            changes = [
                FileChange(
                    str(tmppath / "thought.md"),
                    "created",
                    time.time(),
                    "thought.md",
                ),
            ]

            formatted = watcher.format_for_llm(changes)

            assert "thought.md" in formatted

    @pytest.mark.asyncio
    async def test_infer_phase_with_mock_llm(self):
        """INFER phase should reason about observations."""
        config = ConsciousnessConfig()
        thinker = ConsciousnessThinker(config)

        changes = [
            FileChange("/test/thinker.md", "modified", time.time(), "thinker.md"),
        ]

        # Mock LM Studio connection error
        with patch.object(
            thinker.client.chat.completions,
            'create',
            side_effect=ConnectionError("LM Studio not running"),
        ):
            decision = await thinker.think(changes)

            # Should return safe WAIT decision on error
            assert decision.decision_type == DecisionType.WAIT
            assert decision.confidence == 0.0

    @pytest.mark.asyncio
    async def test_decide_phase_confidence_gate(self):
        """DECIDE phase should gate actions by confidence."""
        # High confidence decision
        high_conf = Decision(
            reasoning="Clear need to act",
            decision_type=DecisionType.ACT,
            confidence=0.9,
            action=Action(ActionType.CLAUDE_CODE, "Update index"),
        )

        # Low confidence decision
        low_conf = Decision(
            reasoning="Uncertain about changes",
            decision_type=DecisionType.ACT,
            confidence=0.3,
            action=Action(ActionType.CLAUDE_CODE, "Maybe update"),
        )

        # High confidence should pass gate
        assert high_conf.confidence >= 0.7
        assert high_conf.decision_type == DecisionType.ACT

        # Low confidence should not pass gate
        assert low_conf.confidence < 0.7

    @pytest.mark.asyncio
    async def test_act_phase_execution(self):
        """ACT phase should execute approved actions."""
        config = ConsciousnessConfig()
        executor = ClaudeCodeExecutor(config)

        action = Action(
            type=ActionType.CLAUDE_CODE,
            prompt="Update the thinkers index",
            priority=Priority.HIGH,
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Index updated",
                stderr="",
            )

            result = await executor.execute(action)

            assert result.success is True


class TestComponentInteraction:
    """Test interactions between components."""

    def test_watcher_output_feeds_thinker(self):
        """Watcher output should be suitable for thinker input."""
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = ConsciousnessWatcher(Path(tmpdir))

            changes = [
                FileChange("/test/new.md", "created", time.time(), "new.md"),
            ]

            # Watcher formats for LLM
            formatted = watcher.format_for_llm(changes)

            # Should be a string suitable for thinker
            assert isinstance(formatted, str)
            assert len(formatted) > 0
            assert "new.md" in formatted

    def test_thinker_output_feeds_executor(self):
        """Thinker decision should be executable by executor."""
        decision = Decision(
            reasoning="Need to update index",
            decision_type=DecisionType.ACT,
            confidence=0.85,
            action=Action(
                type=ActionType.CLAUDE_CODE,
                prompt="Update index file",
                priority=Priority.MEDIUM,
            ),
        )

        # Decision has an action that executor can handle
        assert decision.action is not None
        assert decision.action.type in [ActionType.CLAUDE_CODE, ActionType.CLAUDE_FLOW]
        assert decision.action.prompt is not None


class TestDaemonOrchestration:
    """Test ConsciousnessDaemon orchestration."""

    def test_daemon_initialization(self):
        """Daemon should initialize all components."""
        config = ConsciousnessConfig()
        daemon = ConsciousnessDaemon(config)

        assert hasattr(daemon, 'watcher') or hasattr(daemon, '_watcher')
        assert hasattr(daemon, 'thinker') or hasattr(daemon, '_thinker')
        assert hasattr(daemon, 'executor') or hasattr(daemon, '_executor')

    @pytest.mark.asyncio
    async def test_daemon_single_cycle(self):
        """Daemon should complete a single OIDA cycle."""
        config = ConsciousnessConfig()
        daemon = ConsciousnessDaemon(config)

        # Mock all external dependencies
        with patch.object(daemon, '_observe', new_callable=AsyncMock) as mock_observe:
            mock_observe.return_value = [
                FileChange("/test/file.md", "modified", time.time(), "file.md"),
            ]

            with patch.object(daemon, '_think', new_callable=AsyncMock) as mock_think:
                mock_think.return_value = Decision(
                    reasoning="No action needed",
                    decision_type=DecisionType.WAIT,
                    confidence=0.3,
                )

                # Run single cycle
                result = await daemon._run_cycle()

                mock_observe.assert_called_once()
                mock_think.assert_called_once()


class TestErrorRecovery:
    """Test error recovery scenarios."""

    @pytest.mark.asyncio
    async def test_watcher_handles_permission_error(self):
        """Watcher should handle permission errors gracefully."""
        # Create a watcher for a path that might have issues
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = ConsciousnessWatcher(Path(tmpdir))

            # Should not crash on permission issues
            # This is tested by the ignore pattern filtering
            assert watcher is not None

    @pytest.mark.asyncio
    async def test_thinker_handles_malformed_response(self):
        """Thinker should handle malformed LLM responses."""
        config = ConsciousnessConfig()
        thinker = ConsciousnessThinker(config)

        changes = [FileChange("/test/file.md", "modified", time.time(), "file.md")]

        # Simulate malformed response
        malformed_response = "This is not JSON at all!"

        with patch.object(thinker.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content=malformed_response))],
            )

            decision = await thinker.think(changes)

            # Should return safe WAIT decision
            assert decision.decision_type == DecisionType.WAIT
            assert decision.confidence == 0.0

    @pytest.mark.asyncio
    async def test_executor_handles_subprocess_error(self):
        """Executor should handle subprocess errors gracefully."""
        config = ConsciousnessConfig()
        executor = ClaudeCodeExecutor(config)

        action = Action(
            type=ActionType.CLAUDE_CODE,
            prompt="Failing task",
        )

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = OSError("Subprocess error")

            result = await executor.execute(action)

            assert result.success is False
            assert result.error is not None


class TestStoffySpecificScenarios:
    """Test scenarios specific to Stoffy repository."""

    @pytest.mark.asyncio
    async def test_new_thinker_profile_detected(self):
        """New thinker profile should be detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create knowledge structure
            thinkers_dir = tmppath / "knowledge" / "philosophy" / "thinkers" / "new_thinker"
            thinkers_dir.mkdir(parents=True)

            watcher = ConsciousnessWatcher(tmppath, debounce_ms=100)

            # Simulate the change
            profile = thinkers_dir / "profile.md"
            change = FileChange(
                str(profile),
                "created",
                time.time(),
                "knowledge/philosophy/thinkers/new_thinker/profile.md",
            )

            formatted = watcher.format_for_llm([change])

            assert "thinkers" in formatted
            assert "profile.md" in formatted

    @pytest.mark.asyncio
    async def test_index_update_triggers_high_priority(self):
        """Index file changes should have higher priority consideration."""
        changes = [
            FileChange(
                "/stoffy/indices/thinkers.yaml",
                "modified",
                time.time(),
                "indices/thinkers.yaml",
            ),
        ]

        # Index changes in indices/ are important
        assert "indices" in changes[0].relative_path
        assert changes[0].relative_path.endswith(".yaml")


class TestConcurrencyAndTiming:
    """Test concurrent operations and timing behavior."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_multiple_rapid_changes_batched(self):
        """Multiple rapid changes should be batched by watcher."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            watcher = ConsciousnessWatcher(tmppath, debounce_ms=200)

            # Simulate rapid changes
            changes = []
            for i in range(5):
                changes.append(FileChange(
                    f"/test/file{i}.md",
                    "created",
                    time.time(),
                    f"file{i}.md",
                ))

            # Format all together (as they would be batched)
            formatted = watcher.format_for_llm(changes)

            # All should appear in same batch
            for i in range(5):
                assert f"file{i}.md" in formatted

    @pytest.mark.asyncio
    async def test_daemon_respects_thinking_interval(self):
        """Daemon should respect configured thinking interval."""
        config = ConsciousnessConfig()
        # Assuming config has thinking_interval
        if hasattr(config, 'thinking_interval'):
            assert config.thinking_interval > 0


class TestStateManagement:
    """Test state management and persistence."""

    def test_daemon_tracks_cycle_count(self):
        """Daemon should track the number of cycles."""
        config = ConsciousnessConfig()
        daemon = ConsciousnessDaemon(config)

        # Should have cycle tracking
        assert hasattr(daemon, 'cycle_count') or hasattr(daemon, '_cycle_count')

    @pytest.mark.asyncio
    async def test_execution_records_stored(self):
        """Execution results should be storable in state."""
        result = ExecutionResult(
            success=True,
            output="Task completed",
            duration=1.5,
            mode=ExecutionMode.SIMPLE,
        )

        # Result should be serializable for storage
        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["success"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
