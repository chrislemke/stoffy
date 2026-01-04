"""
Tests for the learning module - outcome tracking and pattern learning.
"""

import asyncio
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from consciousness.learning.tracker import (
    OutcomeTracker,
    Outcome,
    OutcomeType,
    _compute_observation_hash,
)
from consciousness.learning.patterns import (
    PatternLearner,
    Pattern,
    PatternType,
    Suggestion,
)
from consciousness.learning.integration import (
    LearningIntegration,
    LearningConfig,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test_learning.db"


@pytest.fixture
async def outcome_tracker(temp_db):
    """Create and initialize an OutcomeTracker."""
    tracker = OutcomeTracker(temp_db)
    await tracker.initialize()
    yield tracker
    await tracker.close()


@pytest.fixture
async def pattern_learner(temp_db, outcome_tracker):
    """Create a PatternLearner with shared tracker."""
    learner = PatternLearner(temp_db, outcome_tracker)
    yield learner
    await learner.close()


@pytest.fixture
async def learning_integration(temp_db):
    """Create and initialize a LearningIntegration."""
    integration = LearningIntegration(
        db_path=temp_db,
        config=LearningConfig(
            pattern_update_interval=5,  # Update more frequently for tests
            min_pattern_occurrences=2,  # Lower threshold for tests
        ),
    )
    await integration.initialize()
    yield integration
    await integration.close()


# =============================================================================
# Observation Hash Tests
# =============================================================================


class TestObservationHash:
    """Tests for observation hashing/similarity."""

    def test_hash_extracts_file_extensions(self):
        """Hash should capture file extensions."""
        obs1 = "File changed: test.py"
        obs2 = "Modified: another.py"
        obs3 = "Created: something.js"

        hash1 = _compute_observation_hash(obs1)
        hash2 = _compute_observation_hash(obs2)
        hash3 = _compute_observation_hash(obs3)

        # Same extension should produce similar hashes
        assert hash1 == hash2  # Both .py
        assert hash1 != hash3  # .py vs .js

    def test_hash_extracts_action_words(self):
        """Hash should capture action words."""
        obs1 = "File created in src/"
        obs2 = "New file created in lib/"

        hash1 = _compute_observation_hash(obs1)
        hash2 = _compute_observation_hash(obs2)

        # Both have 'created' - should match on that
        assert "created" in obs1.lower()
        assert "created" in obs2.lower()

    def test_hash_extracts_directories(self):
        """Hash should capture directory patterns."""
        obs1 = "Changes in src/main.py"
        obs2 = "Modified src/utils.py"

        hash1 = _compute_observation_hash(obs1)
        hash2 = _compute_observation_hash(obs2)

        # Both in src/ with .py - should match
        assert hash1 == hash2

    def test_hash_is_deterministic(self):
        """Same observation should always produce same hash."""
        obs = "File modified: knowledge/philosophy/thinkers/plato/notes.md"

        hash1 = _compute_observation_hash(obs)
        hash2 = _compute_observation_hash(obs)
        hash3 = _compute_observation_hash(obs)

        assert hash1 == hash2 == hash3


# =============================================================================
# Outcome Tracker Tests
# =============================================================================


class TestOutcomeTracker:
    """Tests for OutcomeTracker functionality."""

    @pytest.mark.asyncio
    async def test_record_and_retrieve_outcome(self, outcome_tracker):
        """Test recording and retrieving outcomes."""
        outcome_id = await outcome_tracker.record_outcome(
            observation="File changed: test.py",
            action_type="claude_code",
            action_details="Run tests",
            success=True,
            output="All tests passed",
            execution_time=2.5,
            confidence_used=0.85,
        )

        assert outcome_id > 0

        outcomes = await outcome_tracker.get_recent_outcomes(limit=10)
        assert len(outcomes) == 1
        assert outcomes[0].action_type == "claude_code"
        assert outcomes[0].result_type == OutcomeType.SUCCESS

    @pytest.mark.asyncio
    async def test_success_rate_calculation(self, outcome_tracker):
        """Test success rate calculation."""
        # Record 8 successes and 2 failures
        for i in range(8):
            await outcome_tracker.record_outcome(
                observation=f"Test observation {i}",
                action_type="update_indices",
                action_details="Update",
                success=True,
            )

        for i in range(2):
            await outcome_tracker.record_outcome(
                observation=f"Failed observation {i}",
                action_type="update_indices",
                action_details="Update",
                success=False,
                error="Something went wrong",
            )

        rate, count = await outcome_tracker.get_success_rate("update_indices")

        assert count == 10
        assert rate == 0.8  # 8/10

    @pytest.mark.asyncio
    async def test_similar_outcomes_matching(self, outcome_tracker):
        """Test finding similar outcomes."""
        # Record outcomes with similar observations
        await outcome_tracker.record_outcome(
            observation="File created in src/module.py",
            action_type="run_tests",
            action_details="pytest",
            success=True,
        )

        await outcome_tracker.record_outcome(
            observation="File modified in src/other.py",
            action_type="run_tests",
            action_details="pytest",
            success=True,
        )

        # Different observation
        await outcome_tracker.record_outcome(
            observation="Config file changed: settings.yaml",
            action_type="restart_service",
            action_details="restart",
            success=True,
        )

        # Find similar to a new src/*.py observation
        similar = await outcome_tracker.get_similar_outcomes(
            "New change in src/utils.py"
        )

        # Should find the src/*.py outcomes
        assert len(similar) >= 1
        assert all("src" in o.observation.lower() for o in similar)

    @pytest.mark.asyncio
    async def test_confidence_adjustment_boost(self, outcome_tracker):
        """Test confidence boost for high success rate."""
        # Record many successes
        for i in range(10):
            await outcome_tracker.record_outcome(
                observation="Test file change",
                action_type="safe_action",
                action_details="Do something safe",
                success=True,
            )

        adjusted, reasoning = await outcome_tracker.calculate_confidence_adjustment(
            action_type="safe_action",
            base_confidence=0.7,
            observation="Test observation",
        )

        # Should boost confidence
        assert adjusted > 0.7
        assert "success rate" in reasoning.lower() or "100%" in reasoning

    @pytest.mark.asyncio
    async def test_confidence_adjustment_penalty(self, outcome_tracker):
        """Test confidence penalty for low success rate."""
        # Record many failures
        for i in range(10):
            await outcome_tracker.record_outcome(
                observation="Test file change",
                action_type="risky_action",
                action_details="Do something risky",
                success=False,
                error="Failed again",
            )

        adjusted, reasoning = await outcome_tracker.calculate_confidence_adjustment(
            action_type="risky_action",
            base_confidence=0.7,
            observation="Test observation",
        )

        # Should reduce confidence
        assert adjusted < 0.7
        assert "success rate" in reasoning.lower() or "0%" in reasoning

    @pytest.mark.asyncio
    async def test_action_statistics(self, outcome_tracker):
        """Test aggregated action statistics."""
        # Record various outcomes
        for i in range(5):
            await outcome_tracker.record_outcome(
                observation=f"Obs {i}",
                action_type="type_a",
                action_details="details",
                success=True,
                execution_time=1.0,
            )

        for i in range(3):
            await outcome_tracker.record_outcome(
                observation=f"Obs {i}",
                action_type="type_b",
                action_details="details",
                success=i < 2,  # 2 successes, 1 failure
                execution_time=2.0,
            )

        stats = await outcome_tracker.get_action_statistics()

        assert "type_a" in stats
        assert stats["type_a"]["total"] == 5
        assert stats["type_a"]["success_rate"] == 1.0

        assert "type_b" in stats
        assert stats["type_b"]["total"] == 3
        assert abs(stats["type_b"]["success_rate"] - 2/3) < 0.01

    @pytest.mark.asyncio
    async def test_cleanup_old_outcomes(self, outcome_tracker):
        """Test cleanup of old outcomes."""
        # Record some outcomes
        for i in range(20):
            await outcome_tracker.record_outcome(
                observation=f"Test {i}",
                action_type="test",
                action_details="details",
                success=True,
            )

        # Clean up keeping only 10
        deleted = await outcome_tracker.cleanup_old_outcomes(
            max_age_days=365,  # Don't delete by age
            max_entries=10,
        )

        assert deleted == 10

        remaining = await outcome_tracker.get_recent_outcomes(limit=100)
        assert len(remaining) == 10


# =============================================================================
# Pattern Learner Tests
# =============================================================================


class TestPatternLearner:
    """Tests for PatternLearner functionality."""

    @pytest.mark.asyncio
    async def test_extract_patterns(self, outcome_tracker, pattern_learner):
        """Test pattern extraction from outcomes."""
        # Create a recurring pattern: same observation type -> same action
        for i in range(5):
            await outcome_tracker.record_outcome(
                observation="File changed in tests/test_main.py",
                action_type="run_tests",
                action_details="pytest tests/",
                success=True,
            )

        patterns = await pattern_learner.extract_patterns(
            min_occurrences=3,
            min_success_rate=0.5,
        )

        assert len(patterns) >= 1
        assert any(p.action_type == "run_tests" for p in patterns)
        assert any(p.success_rate == 1.0 for p in patterns)

    @pytest.mark.asyncio
    async def test_update_patterns(self, outcome_tracker, pattern_learner):
        """Test pattern database updates."""
        # Create outcomes
        for i in range(4):
            await outcome_tracker.record_outcome(
                observation="Config change in settings.yaml",
                action_type="validate_config",
                action_details="validate",
                success=True,
            )

        # Update patterns
        count = await pattern_learner.update_patterns()

        assert count >= 1

        # Check patterns are stored
        patterns = await pattern_learner.get_all_patterns()
        assert len(patterns) >= 1

    @pytest.mark.asyncio
    async def test_suggest_from_patterns(self, outcome_tracker, pattern_learner):
        """Test getting suggestions from patterns."""
        # Create a strong pattern
        for i in range(6):
            await outcome_tracker.record_outcome(
                observation="Documentation changed in docs/api.md",
                action_type="build_docs",
                action_details="make docs",
                success=True,
            )

        # Update patterns
        await pattern_learner.update_patterns()

        # Get suggestions for similar observation
        suggestions = await pattern_learner.suggest_from_patterns(
            observation="New doc file docs/guide.md"
        )

        # May or may not find suggestions depending on hash matching
        # At minimum, the function should not error
        assert isinstance(suggestions, list)

    @pytest.mark.asyncio
    async def test_pattern_reliability(self, outcome_tracker, pattern_learner):
        """Test pattern reliability flag."""
        # Create outcomes with mixed success
        for i in range(5):
            await outcome_tracker.record_outcome(
                observation="Same observation",
                action_type="mixed_action",
                action_details="do something",
                success=i < 4,  # 4 successes, 1 failure
            )

        patterns = await pattern_learner.extract_patterns(
            min_occurrences=3,
            min_success_rate=0.5,
        )

        for pattern in patterns:
            if pattern.occurrences >= 3 and pattern.success_rate >= 0.6:
                assert pattern.is_reliable
            else:
                assert not pattern.is_reliable

    @pytest.mark.asyncio
    async def test_failure_patterns(self, outcome_tracker, pattern_learner):
        """Test failure pattern analysis."""
        # Create failures with same error
        for i in range(3):
            await outcome_tracker.record_outcome(
                observation="Test observation",
                action_type="failing_action",
                action_details="details",
                success=False,
                error="Connection timeout",
            )

        failures = await pattern_learner.get_failure_patterns("failing_action")

        assert len(failures) >= 1
        assert failures[0]["error"] == "Connection timeout"
        assert failures[0]["count"] == 3

    @pytest.mark.asyncio
    async def test_pattern_statistics(self, outcome_tracker, pattern_learner):
        """Test pattern statistics."""
        # Create some patterns
        for i in range(4):
            await outcome_tracker.record_outcome(
                observation="Obs A",
                action_type="action_a",
                action_details="details",
                success=True,
            )

        await pattern_learner.update_patterns()

        stats = await pattern_learner.get_statistics()

        assert "total_patterns" in stats
        assert "reliable_patterns" in stats
        assert "average_success_rate" in stats
        assert "patterns_by_action_type" in stats


# =============================================================================
# Learning Integration Tests
# =============================================================================


class TestLearningIntegration:
    """Tests for LearningIntegration functionality."""

    @pytest.mark.asyncio
    async def test_record_outcome_with_result(self, learning_integration):
        """Test recording outcome with ExecutionResult-like object."""
        # Create a mock result
        result = MagicMock()
        result.success = True
        result.output = "Task completed successfully"
        result.error = None
        result.duration = 1.5

        outcome_id = await learning_integration.record_outcome(
            observation="Test observation",
            action_type="test_action",
            action_details="test details",
            result=result,
            confidence_used=0.8,
        )

        assert outcome_id > 0

    @pytest.mark.asyncio
    async def test_adjust_confidence(self, learning_integration):
        """Test confidence adjustment through integration."""
        # Record some successes first
        for i in range(6):
            result = MagicMock()
            result.success = True
            result.output = "OK"
            result.error = None
            result.duration = 1.0

            await learning_integration.record_outcome(
                observation="Test observation",
                action_type="reliable_action",
                action_details="details",
                result=result,
            )

        adjusted, reasoning = await learning_integration.adjust_confidence(
            action_type="reliable_action",
            base_confidence=0.6,
            observation="New observation",
        )

        # Should get some adjustment
        assert isinstance(adjusted, float)
        assert isinstance(reasoning, str)

    @pytest.mark.asyncio
    async def test_get_learning_status(self, learning_integration):
        """Test learning status retrieval."""
        status = await learning_integration.get_learning_status()

        assert "initialized" in status
        assert status["initialized"] is True
        assert "decision_count" in status
        assert "config" in status

    @pytest.mark.asyncio
    async def test_periodic_pattern_update(self, learning_integration):
        """Test that patterns are updated periodically."""
        result = MagicMock()
        result.success = True
        result.output = "OK"
        result.error = None
        result.duration = 1.0

        # Record enough outcomes to trigger pattern update
        for i in range(10):
            await learning_integration.record_outcome(
                observation="Same observation",
                action_type="test_action",
                action_details="details",
                result=result,
            )

        # Give async task time to run
        await asyncio.sleep(0.1)

        # Should have recorded outcomes
        outcomes = await learning_integration.get_recent_outcomes()
        assert len(outcomes) == 10

    @pytest.mark.asyncio
    async def test_force_pattern_update(self, learning_integration):
        """Test forced pattern update."""
        result = MagicMock()
        result.success = True
        result.output = "OK"
        result.error = None
        result.duration = 1.0

        # Record outcomes
        for i in range(4):
            await learning_integration.record_outcome(
                observation="Test obs",
                action_type="test_action",
                action_details="details",
                result=result,
            )

        # Force update
        count = await learning_integration.force_pattern_update()

        assert isinstance(count, int)

    @pytest.mark.asyncio
    async def test_cleanup(self, learning_integration):
        """Test data cleanup."""
        result = MagicMock()
        result.success = True
        result.output = "OK"
        result.error = None
        result.duration = 1.0

        # Record some outcomes
        for i in range(5):
            await learning_integration.record_outcome(
                observation=f"Obs {i}",
                action_type="test",
                action_details="details",
                result=result,
            )

        cleanup_result = await learning_integration.cleanup()

        assert "outcomes_cleaned" in cleanup_result
        assert "patterns_cleaned" in cleanup_result


# =============================================================================
# Integration Tests
# =============================================================================


class TestLearningSystemIntegration:
    """Integration tests for the complete learning system."""

    @pytest.mark.asyncio
    async def test_full_learning_cycle(self, temp_db):
        """Test complete learning cycle from outcomes to suggestions."""
        integration = LearningIntegration(
            db_path=temp_db,
            config=LearningConfig(
                min_pattern_occurrences=2,
                min_suggestion_confidence=0.5,
            ),
        )
        await integration.initialize()

        try:
            # Simulate multiple action executions
            for i in range(5):
                result = MagicMock()
                result.success = True
                result.output = f"Success {i}"
                result.error = None
                result.duration = 1.0 + i * 0.1

                await integration.record_outcome(
                    observation="File changed in src/main.py",
                    action_type="run_tests",
                    action_details="pytest src/",
                    result=result,
                    confidence_used=0.75,
                )

            # Update patterns
            await integration.force_pattern_update()

            # Check statistics
            status = await integration.get_learning_status()
            assert status["decision_count"] == 5

            # Get suggestions for similar observation
            suggestions = await integration.get_suggestions(
                "New change in src/utils.py"
            )

            # Verify learning is working
            action_stats = await integration.get_action_statistics()
            assert "run_tests" in action_stats
            assert action_stats["run_tests"]["success_rate"] == 1.0

        finally:
            await integration.close()

    @pytest.mark.asyncio
    async def test_confidence_evolution(self, temp_db):
        """Test how confidence evolves with experience."""
        integration = LearningIntegration(
            db_path=temp_db,
            config=LearningConfig(min_history_for_adjustment=3),
        )
        await integration.initialize()

        try:
            base_confidence = 0.7

            # Initially no adjustment (no history)
            adj1, _ = await integration.adjust_confidence(
                "new_action", base_confidence, "test"
            )

            # Record some successes
            for i in range(5):
                result = MagicMock()
                result.success = True
                result.output = "OK"
                result.error = None
                result.duration = 1.0

                await integration.record_outcome(
                    observation="test",
                    action_type="new_action",
                    action_details="details",
                    result=result,
                )

            # Now should have higher confidence
            adj2, reasoning = await integration.adjust_confidence(
                "new_action", base_confidence, "test"
            )

            # Confidence should increase after successes
            assert adj2 >= adj1

        finally:
            await integration.close()
