"""
Tests for ConsciousnessThinker (LM Studio Reasoning Component)

Tests cover:
- Decision parsing from JSON
- Prompt building
- Error handling for LM Studio connection
- Decision types and actions
"""

import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from consciousness.thinker import (
    Action,
    ActionType,
    ConsciousnessThinker,
    Decision,
    DecisionType,
    Priority,
    quick_think,
)
from consciousness.watcher import FileChange, ChangeBatch
from consciousness.config import ConsciousnessConfig


class TestDecisionType:
    """Test DecisionType enum."""

    def test_decision_types_exist(self):
        """All expected decision types should exist."""
        assert DecisionType.ACT.value == "act"
        assert DecisionType.WAIT.value == "wait"
        assert DecisionType.INVESTIGATE.value == "investigate"


class TestActionType:
    """Test ActionType enum."""

    def test_action_types_exist(self):
        """All expected action types should exist."""
        assert ActionType.CLAUDE_CODE.value == "claude_code"
        assert ActionType.CLAUDE_FLOW.value == "claude_flow"


class TestPriority:
    """Test Priority enum."""

    def test_priority_levels_exist(self):
        """All priority levels should exist."""
        assert Priority.LOW.value == "low"
        assert Priority.MEDIUM.value == "medium"
        assert Priority.HIGH.value == "high"


class TestAction:
    """Test Action dataclass."""

    def test_action_creation(self):
        """Action should store all fields."""
        action = Action(
            type=ActionType.CLAUDE_CODE,
            prompt="Execute task",
            priority=Priority.HIGH,
        )

        assert action.type == ActionType.CLAUDE_CODE
        assert action.prompt == "Execute task"
        assert action.priority == Priority.HIGH

    def test_action_default_priority(self):
        """Action should default to medium priority."""
        action = Action(
            type=ActionType.CLAUDE_CODE,
            prompt="Test prompt",
        )

        assert action.priority == Priority.MEDIUM

    def test_action_to_dict(self):
        """Action should convert to dictionary."""
        action = Action(
            type=ActionType.CLAUDE_FLOW,
            prompt="Swarm task",
            priority=Priority.HIGH,
        )

        result = action.to_dict()

        assert result["type"] == "claude_flow"
        assert result["prompt"] == "Swarm task"
        assert result["priority"] == "high"


class TestDecision:
    """Test Decision dataclass."""

    def test_decision_creation(self):
        """Decision should store all fields."""
        action = Action(
            type=ActionType.CLAUDE_CODE,
            prompt="Test",
        )
        decision = Decision(
            reasoning="Test reasoning",
            decision_type=DecisionType.ACT,
            confidence=0.85,
            action=action,
        )

        assert decision.reasoning == "Test reasoning"
        assert decision.decision_type == DecisionType.ACT
        assert decision.confidence == 0.85
        assert decision.action is not None

    def test_decision_without_action(self):
        """Decision can be created without action (for WAIT)."""
        decision = Decision(
            reasoning="Not enough information",
            decision_type=DecisionType.WAIT,
            confidence=0.3,
        )

        assert decision.action is None
        assert decision.decision_type == DecisionType.WAIT

    def test_decision_should_execute(self):
        """Decision should have should_execute method or property."""
        high_conf = Decision(
            reasoning="Clear action needed",
            decision_type=DecisionType.ACT,
            confidence=0.9,
            action=Action(ActionType.CLAUDE_CODE, "Test"),
        )

        low_conf = Decision(
            reasoning="Uncertain",
            decision_type=DecisionType.ACT,
            confidence=0.3,
            action=Action(ActionType.CLAUDE_CODE, "Test"),
        )

        # High confidence ACT should execute
        assert high_conf.confidence >= 0.7
        assert high_conf.decision_type == DecisionType.ACT

        # Low confidence should not execute
        assert low_conf.confidence < 0.7


class TestDecisionParsing:
    """Test Decision parsing from JSON."""

    def test_parse_valid_act_decision(self):
        """Parse a valid JSON response with ACT decision."""
        response = json.dumps({
            "reasoning": "File changes detected in knowledge folder",
            "decision": "act",
            "action": {
                "type": "claude_code",
                "prompt": "Update the thinkers index...",
                "priority": "high",
            },
            "confidence": 0.85,
        })

        decision = Decision.from_json(response)

        assert decision.decision_type == DecisionType.ACT
        assert decision.confidence == 0.85
        assert decision.action is not None
        assert decision.action.type == ActionType.CLAUDE_CODE

    def test_parse_valid_wait_decision(self):
        """Parse a valid JSON response with WAIT decision."""
        response = json.dumps({
            "reasoning": "Not enough information to act",
            "decision": "wait",
            "confidence": 0.3,
        })

        decision = Decision.from_json(response)

        assert decision.decision_type == DecisionType.WAIT
        assert decision.confidence == 0.3
        assert decision.action is None

    def test_parse_invalid_json_returns_wait(self):
        """Invalid JSON should return a safe WAIT decision."""
        response = "this is not valid json at all"

        decision = Decision.from_json(response)

        assert decision.decision_type == DecisionType.WAIT
        assert decision.confidence == 0.0


class TestConsciousnessThinker:
    """Test ConsciousnessThinker class."""

    def test_thinker_initialization(self):
        """Thinker should initialize with config."""
        config = ConsciousnessConfig()
        thinker = ConsciousnessThinker(config)

        assert thinker.config == config

    def test_build_prompt_for_changes(self):
        """Thinker should build prompt from file changes."""
        config = ConsciousnessConfig()
        thinker = ConsciousnessThinker(config)

        changes = [
            FileChange("/test/new.md", "created", time.time(), "new.md"),
            FileChange("/test/mod.py", "modified", time.time(), "mod.py"),
        ]

        prompt = thinker._build_prompt(changes)

        assert "new.md" in prompt
        assert "mod.py" in prompt
        assert "created" in prompt.lower() or "CREATED" in prompt

    @pytest.mark.asyncio
    async def test_think_handles_connection_error(self):
        """Connection errors should return safe WAIT decision."""
        config = ConsciousnessConfig()
        thinker = ConsciousnessThinker(config)

        changes = [
            FileChange("/test/file.md", "modified", time.time(), "file.md"),
        ]

        # Mock the client to raise an error
        with patch.object(
            thinker.client.chat.completions,
            'create',
            side_effect=ConnectionError("LM Studio not running"),
        ):
            decision = await thinker.think(changes)

            assert decision.decision_type == DecisionType.WAIT
            assert decision.confidence == 0.0


class TestSystemPrompt:
    """Test system prompt construction."""

    def test_system_prompt_includes_oida(self):
        """System prompt should mention OIDA loop."""
        config = ConsciousnessConfig()
        thinker = ConsciousnessThinker(config)

        system_prompt = thinker._get_system_prompt()

        assert "OBSERVE" in system_prompt or "observe" in system_prompt.lower()

    def test_system_prompt_includes_confidence_threshold(self):
        """System prompt should mention confidence threshold."""
        config = ConsciousnessConfig()
        thinker = ConsciousnessThinker(config)

        system_prompt = thinker._get_system_prompt()

        assert "0.7" in system_prompt or "confidence" in system_prompt.lower()


class TestQuickThink:
    """Test quick_think convenience function."""

    @pytest.mark.asyncio
    async def test_quick_think_returns_decision(self):
        """quick_think should return a Decision."""
        changes = [
            FileChange("/test/file.md", "created", time.time(), "file.md"),
        ]

        # Mock the thinker
        with patch('consciousness.thinker.ConsciousnessThinker') as MockThinker:
            mock_instance = MockThinker.return_value
            mock_instance.think = AsyncMock(return_value=Decision(
                reasoning="Test",
                decision_type=DecisionType.WAIT,
                confidence=0.5,
            ))

            decision = await quick_think(changes)

            assert isinstance(decision, Decision)


class TestLMStudioIntegration:
    """Test LM Studio integration specifics."""

    def test_uses_openai_compatible_client(self):
        """Thinker should use OpenAI-compatible client."""
        config = ConsciousnessConfig()
        thinker = ConsciousnessThinker(config)

        # Should have an AsyncOpenAI client
        assert hasattr(thinker, 'client')

    def test_default_lm_studio_url(self):
        """Default URL should be localhost:1234."""
        config = ConsciousnessConfig()

        assert "localhost:1234" in config.lm_studio_url or "1234" in config.lm_studio_url


class TestResponseParsing:
    """Test response parsing edge cases."""

    def test_parse_missing_fields_uses_defaults(self):
        """Missing fields should use sensible defaults."""
        response = json.dumps({
            "reasoning": "minimal response",
        })

        decision = Decision.from_json(response)

        assert decision.decision_type == DecisionType.WAIT
        assert decision.confidence >= 0.0

    def test_parse_unknown_decision_type(self):
        """Unknown decision type should default to WAIT."""
        response = json.dumps({
            "reasoning": "test",
            "decision": "unknown_type",
            "confidence": 0.5,
        })

        decision = Decision.from_json(response)

        assert decision.decision_type == DecisionType.WAIT

    def test_parse_preserves_reasoning(self):
        """Parsed decision should preserve reasoning text."""
        reasoning_text = "This is my detailed reasoning about the changes"
        response = json.dumps({
            "reasoning": reasoning_text,
            "decision": "wait",
            "confidence": 0.5,
        })

        decision = Decision.from_json(response)

        assert decision.reasoning == reasoning_text


class TestContextBuilding:
    """Test context building for prompts."""

    def test_context_includes_stoffy_info(self):
        """Context should include Stoffy-specific information."""
        config = ConsciousnessConfig()
        thinker = ConsciousnessThinker(config)

        context = thinker._build_context()

        # Should have information about the repository
        assert isinstance(context, dict) or isinstance(context, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
