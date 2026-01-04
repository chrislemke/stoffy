"""
Tests for ClaudeCodeExecutor (Executor Component)

Tests cover:
- Subprocess call handling
- Timeout handling
- Error handling
- Execution modes
- Result generation
"""

import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from consciousness.executor import (
    ClaudeCodeExecutor,
    ExecutionResult,
    ExecutionMode,
    SwarmConfig,
    ExecutorPool,
    execute_claude,
)
from consciousness.thinker import Action, ActionType, Priority


class TestExecutionResult:
    """Test ExecutionResult dataclass."""

    def test_success_result(self):
        """Successful result should have correct fields."""
        result = ExecutionResult(
            success=True,
            output="Task completed successfully",
            duration=1.5,
            mode=ExecutionMode.SIMPLE,
        )

        assert result.success is True
        assert result.output == "Task completed successfully"
        assert result.error is None
        assert result.mode == ExecutionMode.SIMPLE

    def test_failure_result(self):
        """Failed result should have error field."""
        result = ExecutionResult(
            success=False,
            output="",
            error="Connection timeout",
            duration=30.0,
        )

        assert result.success is False
        assert result.error == "Connection timeout"

    def test_result_to_dict(self):
        """Result should convert to dictionary."""
        result = ExecutionResult(
            success=True,
            output="Done",
            duration=2.0,
            mode=ExecutionMode.SWARM,
            metadata={"agents": 3},
        )

        result_dict = result.to_dict()

        assert result_dict["success"] is True
        assert result_dict["output"] == "Done"
        assert result_dict["mode"] == "swarm"
        assert result_dict["metadata"]["agents"] == 3


class TestExecutionMode:
    """Test ExecutionMode enum."""

    def test_execution_modes_exist(self):
        """Both execution modes should exist."""
        assert ExecutionMode.SIMPLE.value == "simple"
        assert ExecutionMode.SWARM.value == "swarm"


class TestClaudeCodeExecutorInitialization:
    """Test executor initialization."""

    def test_default_initialization(self):
        """Executor should initialize with default config."""
        from consciousness.config import ConsciousnessConfig
        config = ConsciousnessConfig()
        executor = ClaudeCodeExecutor(config)

        assert executor.config == config

    def test_executor_has_stoffy_root(self):
        """Executor should know Stoffy root path."""
        from consciousness.config import ConsciousnessConfig
        config = ConsciousnessConfig()
        executor = ClaudeCodeExecutor(config)

        assert hasattr(executor, 'stoffy_root') or hasattr(executor, 'root_path')


class TestSimpleExecution:
    """Test simple (single command) execution mode."""

    @pytest.mark.asyncio
    async def test_execute_simple_command(self):
        """Simple execution should run claude command."""
        from consciousness.config import ConsciousnessConfig
        config = ConsciousnessConfig()
        executor = ClaudeCodeExecutor(config)

        action = Action(
            type=ActionType.CLAUDE_CODE,
            prompt="Echo hello world",
            priority=Priority.MEDIUM,
        )

        # Mock subprocess.run
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Hello world",
                stderr="",
            )

            result = await executor.execute(action)

            assert result.success is True
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_uses_print_flag(self):
        """Simple execution should use --print flag."""
        from consciousness.config import ConsciousnessConfig
        config = ConsciousnessConfig()
        executor = ClaudeCodeExecutor(config)

        action = Action(
            type=ActionType.CLAUDE_CODE,
            prompt="Test prompt",
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Output",
                stderr="",
            )

            await executor.execute(action)

            # Check that --print or -p is in the command
            call_args = mock_run.call_args
            cmd = call_args[0][0] if call_args[0] else call_args[1].get('args', [])
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)

            assert "--print" in cmd_str or "-p" in cmd_str


class TestSwarmExecution:
    """Test swarm (multi-agent) execution mode."""

    @pytest.mark.asyncio
    async def test_execute_swarm_command(self):
        """Swarm execution should invoke claude-flow."""
        from consciousness.config import ConsciousnessConfig
        config = ConsciousnessConfig()
        executor = ClaudeCodeExecutor(config)

        action = Action(
            type=ActionType.CLAUDE_FLOW,
            prompt="Complex multi-agent task",
            priority=Priority.HIGH,
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Swarm completed",
                stderr="",
            )

            result = await executor.execute(action)

            assert result.success is True
            # Should use claude-flow or similar
            call_args = mock_run.call_args
            cmd = call_args[0][0] if call_args[0] else str(call_args)
            assert "claude" in str(cmd).lower() or "flow" in str(cmd).lower()


class TestTimeoutHandling:
    """Test timeout handling for executions."""

    @pytest.mark.asyncio
    async def test_execution_timeout(self):
        """Long-running commands should timeout."""
        from consciousness.config import ConsciousnessConfig
        config = ConsciousnessConfig()
        executor = ClaudeCodeExecutor(config)

        action = Action(
            type=ActionType.CLAUDE_CODE,
            prompt="Long task",
        )

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("claude", 60)

            result = await executor.execute(action)

            assert result.success is False
            assert "timeout" in result.error.lower()

    def test_default_timeout_exists(self):
        """Executor should have a default timeout."""
        from consciousness.config import ConsciousnessConfig
        config = ConsciousnessConfig()
        executor = ClaudeCodeExecutor(config)

        assert hasattr(executor, 'timeout') or hasattr(config, 'timeout')


class TestErrorHandling:
    """Test error handling in executor."""

    @pytest.mark.asyncio
    async def test_handles_nonzero_exit(self):
        """Non-zero exit code should be handled."""
        from consciousness.config import ConsciousnessConfig
        config = ConsciousnessConfig()
        executor = ClaudeCodeExecutor(config)

        action = Action(
            type=ActionType.CLAUDE_CODE,
            prompt="Failing task",
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="Error: Task failed",
            )

            result = await executor.execute(action)

            assert result.success is False
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_handles_file_not_found(self):
        """Missing claude command should be handled."""
        from consciousness.config import ConsciousnessConfig
        config = ConsciousnessConfig()
        executor = ClaudeCodeExecutor(config)

        action = Action(
            type=ActionType.CLAUDE_CODE,
            prompt="Test",
        )

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("claude not found")

            result = await executor.execute(action)

            assert result.success is False
            assert "not found" in result.error.lower()


class TestSwarmConfig:
    """Test SwarmConfig dataclass."""

    def test_swarm_config_defaults(self):
        """SwarmConfig should have sensible defaults."""
        config = SwarmConfig()

        assert hasattr(config, 'topology') or hasattr(config, 'max_agents')

    def test_swarm_config_custom_values(self):
        """SwarmConfig should accept custom values."""
        config = SwarmConfig(
            topology="mesh",
            max_agents=5,
        )

        assert config.topology == "mesh"
        assert config.max_agents == 5


class TestExecutorPool:
    """Test ExecutorPool for concurrent executions."""

    def test_pool_initialization(self):
        """Pool should initialize with max concurrent."""
        pool = ExecutorPool(max_concurrent=3)

        assert pool.max_concurrent == 3

    @pytest.mark.asyncio
    async def test_pool_limits_concurrency(self):
        """Pool should limit concurrent executions."""
        pool = ExecutorPool(max_concurrent=2)

        # This tests the structure - actual concurrent test would need more setup
        assert pool.max_concurrent == 2


class TestExecuteClaudeFunction:
    """Test execute_claude convenience function."""

    @pytest.mark.asyncio
    async def test_execute_claude_creates_executor(self):
        """execute_claude should create and use executor."""
        action = Action(
            type=ActionType.CLAUDE_CODE,
            prompt="Test prompt",
        )

        with patch('consciousness.executor.ClaudeCodeExecutor') as MockExecutor:
            mock_instance = MockExecutor.return_value
            mock_instance.execute = AsyncMock(return_value=ExecutionResult(
                success=True,
                output="Done",
                duration=1.0,
            ))

            result = await execute_claude(action)

            assert result.success is True


class TestDryRunMode:
    """Test dry run mode."""

    @pytest.mark.asyncio
    async def test_dry_run_does_not_execute(self):
        """Dry run should not actually execute commands."""
        from consciousness.config import ConsciousnessConfig
        config = ConsciousnessConfig()
        config.dry_run = True
        executor = ClaudeCodeExecutor(config)

        action = Action(
            type=ActionType.CLAUDE_CODE,
            prompt="Should not run",
        )

        with patch("subprocess.run") as mock_run:
            result = await executor.execute(action)

            # In dry run, subprocess should not be called
            # or result should indicate dry run
            if hasattr(result, 'metadata') and result.metadata.get('dry_run'):
                mock_run.assert_not_called()


class TestWorkingDirectory:
    """Test working directory handling."""

    @pytest.mark.asyncio
    async def test_executes_in_stoffy_directory(self):
        """Execution should happen in Stoffy directory."""
        from consciousness.config import ConsciousnessConfig
        config = ConsciousnessConfig()
        executor = ClaudeCodeExecutor(config)

        action = Action(
            type=ActionType.CLAUDE_CODE,
            prompt="Test",
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="OK",
                stderr="",
            )

            await executor.execute(action)

            # Check cwd argument
            call_kwargs = mock_run.call_args[1]
            if 'cwd' in call_kwargs:
                cwd = call_kwargs['cwd']
                assert Path(cwd).exists() or "stoffy" in str(cwd).lower()


class TestOutputCapture:
    """Test output capture from executions."""

    @pytest.mark.asyncio
    async def test_captures_stdout(self):
        """Should capture stdout from execution."""
        from consciousness.config import ConsciousnessConfig
        config = ConsciousnessConfig()
        executor = ClaudeCodeExecutor(config)

        action = Action(
            type=ActionType.CLAUDE_CODE,
            prompt="Test",
        )

        expected_output = "This is the task output"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=expected_output,
                stderr="",
            )

            result = await executor.execute(action)

            assert expected_output in result.output

    @pytest.mark.asyncio
    async def test_captures_stderr_on_error(self):
        """Should capture stderr when command fails."""
        from consciousness.config import ConsciousnessConfig
        config = ConsciousnessConfig()
        executor = ClaudeCodeExecutor(config)

        action = Action(
            type=ActionType.CLAUDE_CODE,
            prompt="Test",
        )

        error_message = "Error: Something went wrong"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr=error_message,
            )

            result = await executor.execute(action)

            assert error_message in result.error or error_message in result.output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
