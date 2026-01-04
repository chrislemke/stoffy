"""Tests for the Dreamer (Dream Cycle) component."""

import asyncio
import json
import pytest
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from consciousness.learning.dreamer import (
    Dreamer,
    DreamerConfig,
    DreamResult,
    DreamPhase,
    LLMTier,
    LocalLLMClient,
    create_dreamer,
)
from consciousness.learning.tracker import OutcomeTracker, OutcomeType


@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path."""
    return tmp_path / "test_consciousness.db"


@pytest.fixture
def temp_project_root(tmp_path):
    """Create a temporary project root with necessary directories."""
    project = tmp_path / "project"
    project.mkdir()
    (project / "knowledge" / "patterns").mkdir(parents=True)
    (project / ".hive-mind" / "templates").mkdir(parents=True)
    return project


@pytest.fixture
async def dreamer(temp_db_path, temp_project_root):
    """Create a Dreamer instance for testing."""
    config = DreamerConfig(
        inactivity_minutes=1,  # Short for testing
        action_threshold=5,
        min_time_between_dreams_minutes=0,  # Allow immediate dreams for testing
        max_dream_duration_minutes=1,
    )
    dreamer = Dreamer(
        db_path=temp_db_path,
        project_root=temp_project_root,
        config=config,
    )
    await dreamer.outcome_tracker.initialize()
    yield dreamer
    await dreamer.close()


class TestDreamerConfig:
    """Tests for DreamerConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = DreamerConfig()
        assert config.inactivity_minutes == 60
        assert config.action_threshold == 100
        assert config.recall_outcomes_limit == 200
        assert config.recall_thoughts_limit == 100
        assert config.min_occurrences_for_template == 5
        assert config.max_dream_duration_minutes == 15

    def test_custom_config(self):
        """Test custom configuration values."""
        config = DreamerConfig(
            inactivity_minutes=30,
            action_threshold=50,
            large_log_threshold=100000,
        )
        assert config.inactivity_minutes == 30
        assert config.action_threshold == 50
        assert config.large_log_threshold == 100000


class TestDreamerInitialization:
    """Tests for Dreamer initialization."""

    async def test_create_dreamer(self, temp_db_path, temp_project_root):
        """Test creating a Dreamer instance."""
        dreamer = create_dreamer(
            db_path=temp_db_path,
            project_root=temp_project_root,
        )
        assert dreamer is not None
        assert dreamer.db_path == temp_db_path
        assert dreamer.project_root == temp_project_root
        await dreamer.close()

    async def test_dreamer_with_config(self, temp_db_path, temp_project_root):
        """Test creating a Dreamer with custom config."""
        config = DreamerConfig(inactivity_minutes=30)
        dreamer = Dreamer(
            db_path=temp_db_path,
            project_root=temp_project_root,
            config=config,
        )
        assert dreamer.config.inactivity_minutes == 30
        await dreamer.close()


class TestDreamerTriggers:
    """Tests for dream trigger conditions."""

    async def test_should_dream_inactivity(self, dreamer):
        """Test dream trigger based on inactivity."""
        # Just initialized - should not dream
        assert not dreamer.should_dream()

        # Simulate inactivity by backdating last activity
        dreamer._last_activity_time = time.time() - 120  # 2 minutes ago
        assert dreamer.should_dream()

    async def test_should_dream_action_threshold(self, dreamer):
        """Test dream trigger based on action count."""
        # Record actions up to threshold
        for _ in range(5):
            dreamer.record_action()

        assert dreamer.should_dream()

    async def test_should_not_dream_when_already_dreaming(self, dreamer):
        """Test that dream is blocked when already in progress."""
        dreamer._is_dreaming = True
        dreamer._last_activity_time = time.time() - 3700  # Over threshold
        assert not dreamer.should_dream()

    async def test_record_activity_resets_timer(self, dreamer):
        """Test that recording activity resets the inactivity timer."""
        dreamer._last_activity_time = time.time() - 120
        dreamer.record_activity()
        assert dreamer.inactivity_minutes < 1

    async def test_record_action_increments_counter(self, dreamer):
        """Test that recording action increments the counter."""
        initial_count = dreamer.actions_since_dream
        dreamer.record_action()
        assert dreamer.actions_since_dream == initial_count + 1


class TestDreamPhases:
    """Tests for individual dream phases."""

    async def test_recall_phase(self, dreamer):
        """Test the recall phase retrieves outcomes."""
        # Add some test outcomes
        await dreamer.outcome_tracker.record_outcome(
            observation="Test observation",
            action_type="test_action",
            action_details="Test details",
            success=True,
            output="Test output",
        )

        outcomes, thoughts = await dreamer.recall()
        assert len(outcomes) >= 1
        assert outcomes[0].action_type == "test_action"

    async def test_prune_phase(self, dreamer):
        """Test the prune phase cleans up old data."""
        result = await dreamer.prune()
        assert "outcomes_pruned" in result
        assert "thoughts_pruned" in result
        assert "patterns_pruned" in result

    async def test_plan_phase_with_fallback(self, dreamer):
        """Test the plan phase generates todos."""
        mistakes = [
            {"pattern": "Test mistake", "prevention": "Fix it"}
        ]
        patterns = [
            {"name": "Test pattern", "description": "A test pattern"}
        ]

        todos = await dreamer.plan(mistakes, patterns)
        assert len(todos) > 0


class TestDreamCycle:
    """Tests for the complete dream cycle."""

    async def test_dream_cycle_completes_phases(self, dreamer):
        """Test that a dream cycle completes all phases."""
        # Mock the LLM client to avoid actual API calls
        mock_client = AsyncMock()
        mock_client.complete.return_value = json.dumps({
            "mistakes": [],
            "patterns": [],
            "template_candidates": [],
            "todos": [{"priority": "high", "task": "Test task"}],
        })

        with patch.object(dreamer, '_get_llm_client', return_value=mock_client):
            result = await dreamer.dream()

        assert DreamPhase.RECALL in result.phases_completed
        assert DreamPhase.REFLECT in result.phases_completed
        assert DreamPhase.CONSOLIDATE in result.phases_completed
        assert DreamPhase.PRUNE in result.phases_completed
        assert DreamPhase.PLAN in result.phases_completed
        assert DreamPhase.COMPLETE in result.phases_completed

    async def test_dream_cycle_resets_counters(self, dreamer):
        """Test that dream cycle resets action counter."""
        dreamer._action_count_since_dream = 10

        with patch.object(dreamer, '_get_llm_client', return_value=AsyncMock(
            complete=AsyncMock(return_value='{}')
        )):
            await dreamer.dream()

        assert dreamer.actions_since_dream == 0

    async def test_dream_result_structure(self, dreamer):
        """Test DreamResult contains expected fields."""
        result = DreamResult()
        assert result.started_at is not None
        assert result.completed_at is None
        assert result.phases_completed == []
        assert result.outcomes_recalled == 0
        assert result.errors == []

        result_dict = result.to_dict()
        assert "started_at" in result_dict
        assert "phases_completed" in result_dict
        assert "insights" in result_dict


class TestLLMTierSelection:
    """Tests for LLM tier selection."""

    async def test_tier_selection_small_logs(self, dreamer):
        """Test that small logs use Claude."""
        small_log = "A" * 10000
        tier = dreamer._select_llm_tier(small_log)
        assert tier == LLMTier.CLAUDE

    async def test_tier_selection_medium_logs(self, dreamer):
        """Test that medium logs use Gemini Flash."""
        medium_log = "A" * 30000
        tier = dreamer._select_llm_tier(medium_log)
        assert tier == LLMTier.GEMINI_FLASH

    async def test_tier_selection_large_logs(self, dreamer):
        """Test that large logs use Gemini Pro."""
        large_log = "A" * 60000
        tier = dreamer._select_llm_tier(large_log)
        assert tier == LLMTier.GEMINI_PRO


class TestDreamerStatus:
    """Tests for dreamer status reporting."""

    async def test_get_status(self, dreamer):
        """Test status reporting."""
        status = dreamer.get_status()
        assert "is_dreaming" in status
        assert "current_phase" in status
        assert "inactivity_minutes" in status
        assert "actions_since_dream" in status
        assert "should_dream" in status
        assert "config" in status

    async def test_status_reflects_state(self, dreamer):
        """Test that status accurately reflects state."""
        dreamer.record_action()
        dreamer.record_action()
        status = dreamer.get_status()
        assert status["actions_since_dream"] == 2


class TestConsolidation:
    """Tests for knowledge consolidation."""

    async def test_consolidate_creates_rules_file(self, dreamer, temp_project_root):
        """Test that consolidation creates learned_rules.md."""
        insights = {
            "patterns": [
                {"name": "Test Pattern", "description": "A test", "trigger": "When testing", "implementation": "Do test"}
            ],
            "mistakes": [
                {"pattern": "Test Mistake", "root_cause": "Testing", "prevention": "Don't test badly"}
            ],
            "template_candidates": [],
        }

        result = await dreamer.consolidate(insights)
        assert result["rules_updated"] > 0

        rules_path = temp_project_root / "knowledge" / "patterns" / "learned_rules.md"
        assert rules_path.exists()
        content = rules_path.read_text()
        assert "Test Pattern" in content or "Test Mistake" in content

    async def test_consolidate_creates_templates(self, dreamer, temp_project_root):
        """Test that consolidation creates template files."""
        insights = {
            "patterns": [],
            "mistakes": [],
            "template_candidates": [
                {
                    "name": "Test Template",
                    "pattern_name": "Test Pattern",
                    "suggested_template": "template content",
                }
            ],
        }

        result = await dreamer.consolidate(insights)
        assert result["templates_created"] == 1

        template_path = temp_project_root / ".hive-mind" / "templates" / "test_template.yaml"
        assert template_path.exists()


class TestJSONParsing:
    """Tests for JSON response parsing."""

    async def test_parse_valid_json(self, dreamer):
        """Test parsing valid JSON."""
        response = '{"key": "value"}'
        result = dreamer._parse_json_response(response)
        assert result == {"key": "value"}

    async def test_parse_json_in_code_block(self, dreamer):
        """Test parsing JSON from markdown code block."""
        response = '```json\n{"key": "value"}\n```'
        result = dreamer._parse_json_response(response)
        assert result == {"key": "value"}

    async def test_parse_json_with_surrounding_text(self, dreamer):
        """Test parsing JSON embedded in text."""
        response = 'Here is the data: {"key": "value"} and more text'
        result = dreamer._parse_json_response(response)
        assert result == {"key": "value"}

    async def test_parse_invalid_json_returns_empty(self, dreamer):
        """Test that invalid JSON returns empty dict."""
        response = "This is not valid JSON"
        result = dreamer._parse_json_response(response)
        assert result == {}


class TestLocalLLMClient:
    """Tests for LocalLLMClient."""

    async def test_local_client_creation(self):
        """Test creating a local LLM client."""
        client = LocalLLMClient(
            base_url="http://localhost:1234/v1",
            model="test-model",
        )
        assert client.model == "test-model"

    async def test_local_client_complete_mock(self):
        """Test local client completion with mock."""
        client = LocalLLMClient(
            base_url="http://localhost:1234/v1",
            model="test-model",
        )

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="test response"))]

        # Use AsyncMock for the async create method
        with patch.object(
            client.client.chat.completions,
            'create',
            new=AsyncMock(return_value=mock_response)
        ):
            result = await client.complete("test prompt", "test system")
            assert result == "test response"
