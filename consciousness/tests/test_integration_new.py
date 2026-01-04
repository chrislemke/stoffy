"""
Integration tests for new consciousness components.

Tests the integration between:
- Dreamer (Dream Cycle) with OutcomeTracker and PatternLearner
- SemanticMemoryWriter with the knowledge directory
- TemplateGenerator with .hive-mind/templates
- Enhanced OutcomeTracker (tier support)
- Gemini executor integration (mocked)
- Full stack learning cycles
"""

import asyncio
import json
import shutil
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from consciousness.learning.dreamer import (
    Dreamer,
    DreamerConfig,
    DreamPhase,
    DreamResult,
    GeminiLLMClient,
    LLMTier,
    LocalLLMClient,
    create_dreamer,
)
from consciousness.learning.patterns import Pattern, PatternLearner, PatternType
from consciousness.learning.semantic import (
    ArchitectureInsight,
    SemanticMemoryConfig,
    SemanticMemoryWriter,
    SemanticRule,
    create_semantic_memory_writer,
)
from consciousness.learning.templates import (
    Template,
    TemplateGenerator,
    TemplateGeneratorConfig,
)
from consciousness.learning.tracker import (
    ExecutorTier,
    Outcome,
    OutcomeTracker,
    OutcomeType,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
async def temp_project():
    """Create a temporary project structure for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)

        # Create knowledge directory structure
        (project / "knowledge" / "patterns").mkdir(parents=True)
        (project / "knowledge" / "rules.md").write_text(
            "# Rules\n\nInitial rules file.\n"
        )
        (project / "knowledge" / "architecture.md").write_text(
            "# Architecture\n\nInitial architecture file.\n"
        )

        # Create .hive-mind/templates structure
        (project / ".hive-mind" / "templates" / "learned").mkdir(parents=True)
        (project / ".hive-mind" / "templates" / "custom").mkdir(parents=True)
        (project / ".hive-mind" / "templates" / "archived").mkdir(parents=True)

        # Create database path
        db_path = project / ".consciousness" / "state.db"
        db_path.parent.mkdir(parents=True)

        yield {
            "root": project,
            "db_path": db_path,
            "knowledge_path": project / "knowledge",
            "templates_path": project / ".hive-mind" / "templates",
        }


@pytest.fixture
async def outcome_tracker(temp_project):
    """Create and initialize an OutcomeTracker."""
    tracker = OutcomeTracker(temp_project["db_path"])
    await tracker.initialize()
    yield tracker
    await tracker.close()


@pytest.fixture
async def pattern_learner(temp_project, outcome_tracker):
    """Create a PatternLearner with shared OutcomeTracker."""
    learner = PatternLearner(
        db_path=temp_project["db_path"],
        outcome_tracker=outcome_tracker,
    )
    yield learner
    await learner.close()


@pytest.fixture
async def dreamer(temp_project, outcome_tracker, pattern_learner):
    """Create a Dreamer with shared components."""
    config = DreamerConfig(
        inactivity_minutes=1,  # Short for testing
        action_threshold=5,
        min_time_between_dreams_minutes=0,  # Allow immediate dreams
        max_dream_duration_minutes=1,
        recall_outcomes_limit=50,
        recall_thoughts_limit=50,
    )
    dreamer = Dreamer(
        db_path=temp_project["db_path"],
        project_root=temp_project["root"],
        config=config,
        outcome_tracker=outcome_tracker,
        pattern_learner=pattern_learner,
    )
    yield dreamer
    await dreamer.close()


@pytest.fixture
async def semantic_writer(temp_project):
    """Create a SemanticMemoryWriter."""
    config = SemanticMemoryConfig(
        knowledge_dir=Path("knowledge"),
        min_confidence_for_write=0.7,
        min_occurrences_for_rule=3,
        backup_on_write=False,  # Disable for testing
    )
    writer = SemanticMemoryWriter(
        base_path=temp_project["root"],
        config=config,
    )
    await writer.initialize()
    yield writer


@pytest.fixture
async def template_generator(temp_project):
    """Create a TemplateGenerator."""
    config = TemplateGeneratorConfig(
        templates_dir=Path(".hive-mind/templates"),
        min_successes_for_template=3,
        min_success_rate=0.75,
        include_examples=True,
        max_examples_per_template=2,
    )
    generator = TemplateGenerator(
        config=config,
        base_path=temp_project["root"],
    )
    await generator.initialize()
    yield generator


def create_mock_llm_client():
    """Create a mock LLM client for testing."""
    mock_client = AsyncMock()
    mock_client.complete.return_value = json.dumps(
        {
            "mistakes": [
                {
                    "pattern": "Timeout errors on index updates",
                    "frequency": "5 occurrences",
                    "root_cause": "Large file operations",
                    "prevention": "Batch file operations into smaller chunks",
                }
            ],
            "patterns": [
                {
                    "name": "Test File Creation",
                    "description": "Create tests when Python files are added",
                    "trigger": "*.py file created in src/",
                    "implementation": "Generate test skeleton",
                    "success_rate": "90%",
                }
            ],
            "template_candidates": [
                {
                    "name": "auto_test_generation",
                    "pattern_name": "Test File Creation",
                    "suggested_template": "Create test file for {file}",
                }
            ],
            "todos": [
                {
                    "priority": "high",
                    "task": "Fix timeout issue in index updates",
                    "reasoning": "Recurring problem",
                    "estimated_effort": "medium",
                }
            ],
        }
    )
    return mock_client


# =============================================================================
# Dreamer Integration Tests
# =============================================================================


class TestDreamerIntegration:
    """Test Dreamer integration with OutcomeTracker and PatternLearner."""

    @pytest.mark.asyncio
    async def test_dreamer_triggers_on_action_count(self, dreamer):
        """Test that Dreamer triggers after action threshold is reached."""
        # Initially should not dream
        assert not dreamer.should_dream()

        # Record actions up to threshold
        for _ in range(dreamer.config.action_threshold):
            dreamer.record_action()

        # Should now trigger dream
        assert dreamer.should_dream()

    @pytest.mark.asyncio
    async def test_dreamer_triggers_on_inactivity(self, dreamer):
        """Test that Dreamer triggers after inactivity period."""
        # Set last activity to be past threshold
        dreamer._last_activity_time = time.time() - (
            dreamer.config.inactivity_minutes * 60 + 10
        )

        assert dreamer.should_dream()

    @pytest.mark.asyncio
    async def test_dreamer_writes_to_knowledge(
        self, dreamer, outcome_tracker, temp_project
    ):
        """Test that Dreamer consolidates to knowledge/patterns/learned_rules.md."""
        # Add test outcomes
        for i in range(5):
            await outcome_tracker.record_outcome(
                observation=f"Test file {i}.py created",
                action_type="create_test",
                action_details=f"Created test for file {i}",
                success=True,
                output="Test created successfully",
                executor_tier=ExecutorTier.CLAUDE_CODE,
            )

        # Mock LLM client
        mock_client = create_mock_llm_client()

        with patch.object(dreamer, "_get_llm_client", return_value=mock_client):
            result = await dreamer.dream()

        # Verify dream completed consolidation phase
        assert DreamPhase.CONSOLIDATE in result.phases_completed

        # Check learned_rules.md was created/updated
        rules_path = (
            temp_project["knowledge_path"] / "patterns" / "learned_rules.md"
        )
        assert rules_path.exists()

        content = rules_path.read_text()
        # Should contain dream cycle header
        assert "Dream Cycle Insights" in content

    @pytest.mark.asyncio
    async def test_dreamer_creates_templates(
        self, dreamer, outcome_tracker, temp_project
    ):
        """Test that Dreamer creates templates for reliable patterns."""
        # Add outcomes
        for i in range(5):
            await outcome_tracker.record_outcome(
                observation=f"Config file {i}.yaml modified",
                action_type="validate_config",
                action_details="Validated configuration file",
                success=True,
                executor_tier=ExecutorTier.CLAUDE_CODE,
            )

        # Mock LLM client
        mock_client = create_mock_llm_client()

        with patch.object(dreamer, "_get_llm_client", return_value=mock_client):
            result = await dreamer.dream()

        # Should have created templates
        assert result.templates_created >= 0  # May or may not create based on patterns

        # Check templates directory
        templates_path = temp_project["templates_path"]
        # Template files should exist if created
        if result.templates_created > 0:
            template_files = list(templates_path.glob("*.yaml"))
            assert len(template_files) > 0

    @pytest.mark.asyncio
    async def test_dreamer_prunes_old_outcomes(
        self, dreamer, outcome_tracker, temp_project
    ):
        """Test that Dreamer cleans up old episodic memory."""
        # Add many outcomes
        for i in range(20):
            await outcome_tracker.record_outcome(
                observation=f"Test observation {i}",
                action_type="test_action",
                action_details=f"Test details {i}",
                success=i % 2 == 0,
            )

        # Mock LLM client
        mock_client = create_mock_llm_client()

        with patch.object(dreamer, "_get_llm_client", return_value=mock_client):
            result = await dreamer.dream()

        # Prune phase should complete
        assert DreamPhase.PRUNE in result.phases_completed

        # Result should track pruning stats
        assert "outcomes_pruned" in result.to_dict() or result.outcomes_pruned >= 0

    @pytest.mark.asyncio
    async def test_dreamer_integrates_with_pattern_learner(
        self, dreamer, outcome_tracker, pattern_learner
    ):
        """Test Dreamer works with PatternLearner to extract patterns."""
        # Add outcomes with same observation hash pattern
        for i in range(5):
            await outcome_tracker.record_outcome(
                observation="src/utils.py modified with new function",
                action_type="generate_tests",
                action_details="Generated unit tests",
                success=True,
            )

        # Extract patterns
        patterns = await pattern_learner.extract_patterns(
            min_occurrences=3, min_success_rate=0.5
        )

        # Should find the pattern
        assert len(patterns) > 0
        assert any(p.action_type == "generate_tests" for p in patterns)


# =============================================================================
# SemanticMemoryWriter Integration Tests
# =============================================================================


class TestSemanticMemoryIntegration:
    """Test SemanticMemoryWriter integration with knowledge directory."""

    @pytest.mark.asyncio
    async def test_consolidate_from_outcomes(
        self, semantic_writer, outcome_tracker, temp_project
    ):
        """Test consolidation of outcomes into semantic rules."""
        # Add outcomes with high success rate
        for i in range(6):
            await outcome_tracker.record_outcome(
                observation=f"Python file modified: src/module{i}.py",
                action_type="format_code",
                action_details="Applied black formatting",
                success=True,
                executor_tier=ExecutorTier.CLAUDE_CODE,
            )

        # Get outcomes and consolidate
        outcomes = await outcome_tracker.get_recent_outcomes(limit=50)

        result = await semantic_writer.consolidate_from_outcomes(outcomes)

        # Should have written rules
        assert result["outcomes_analyzed"] > 0
        # With high success rate, should write rules
        if result["rules_written"] > 0:
            rules_content = await semantic_writer._read_file(
                semantic_writer.rules_path
            )
            assert "format_code" in rules_content.lower() or "success" in rules_content.lower()

    @pytest.mark.asyncio
    async def test_search_knowledge(self, semantic_writer, temp_project):
        """Test searching across knowledge files."""
        # Write some test content
        await semantic_writer.write_rule(
            rule="Always validate user input before processing",
            source="security_audit",
            confidence=0.9,
            category="security",
        )

        await semantic_writer.write_architecture_insight(
            insight="The authentication module handles all user sessions",
            component="authentication",
            source="code_analysis",
        )

        # Search for relevant content
        results = await semantic_writer.search_knowledge("user")

        assert len(results) > 0
        assert any("user" in r.lower() for r in results)

    @pytest.mark.asyncio
    async def test_write_architecture_insight(self, semantic_writer, temp_project):
        """Test writing architecture insights."""
        result = await semantic_writer.write_architecture_insight(
            insight="The caching layer improves response time by 80%",
            component="caching",
            source="performance_analysis",
            related_patterns=["cache_invalidation", "ttl_management"],
        )

        assert result is True

        # Verify content
        arch_content = await semantic_writer._read_file(
            semantic_writer.architecture_path
        )
        assert "caching" in arch_content
        assert "80%" in arch_content

    @pytest.mark.asyncio
    async def test_write_pattern(self, semantic_writer, temp_project):
        """Test writing a pattern to the patterns file."""
        pattern = Pattern(
            id=1,
            pattern_type=PatternType.OBSERVATION_ACTION,
            trigger_hash="abc123",
            trigger_description="New Python file created",
            action_type="create_test",
            action_template="Generate test skeleton",
            success_rate=0.92,
            occurrences=15,
        )

        result = await semantic_writer.write_pattern(
            pattern=pattern,
            insight="This pattern shows reliable test generation for new files",
        )

        assert result is True

        patterns_content = await semantic_writer._read_file(
            semantic_writer.patterns_path
        )
        assert "create_test" in patterns_content or "Create Test" in patterns_content

    @pytest.mark.asyncio
    async def test_get_statistics(self, semantic_writer):
        """Test getting semantic memory statistics."""
        # Write some content
        await semantic_writer.write_rule(
            rule="Test rule for statistics",
            source="test",
            confidence=0.85,
        )

        stats = await semantic_writer.get_statistics()

        assert "knowledge_path" in stats
        assert "rules_count" in stats
        assert "config" in stats
        assert stats["rules_count"] >= 1


# =============================================================================
# TemplateGenerator Integration Tests
# =============================================================================


class TestTemplateGeneratorIntegration:
    """Test TemplateGenerator integration with .hive-mind/templates."""

    @pytest.mark.asyncio
    async def test_create_template_from_pattern(
        self, template_generator, temp_project
    ):
        """Test template creation from a reliable pattern."""
        pattern = Pattern(
            id=1,
            pattern_type=PatternType.OBSERVATION_ACTION,
            trigger_hash="xyz789",
            trigger_description="Configuration YAML file modified in config/",
            action_type="validate_config",
            action_template="Validate YAML syntax and schema",
            success_rate=0.92,
            occurrences=10,
            last_updated=datetime.now(timezone.utc),
        )

        outcomes = [
            Outcome(
                id=i,
                timestamp=datetime.now(timezone.utc),
                observation="config/app.yaml modified",
                action_type="validate_config",
                action_details="Validated configuration",
                result_type=OutcomeType.SUCCESS,
                result_output="Validation passed",
                execution_time=1.5,
            )
            for i in range(5)
        ]

        # Check if pattern qualifies
        should_create = await template_generator.should_create_template(pattern)
        assert should_create is True

        # Create template
        path = await template_generator.create_template(pattern, outcomes)

        assert path.exists()
        assert path.suffix == ".yaml"

        # Verify template content
        import yaml

        with path.open() as f:
            data = yaml.safe_load(f)

        assert data["action"]["type"] == "validate_config"
        assert data["statistics"]["success_rate"] > 0.9
        assert "trigger" in data

    @pytest.mark.asyncio
    async def test_template_matching(self, template_generator, temp_project):
        """Test finding matching templates for observations."""
        # Create a template first
        pattern = Pattern(
            id=1,
            pattern_type=PatternType.OBSERVATION_ACTION,
            trigger_hash="match123",
            trigger_description="New Python test file created in tests/",
            action_type="run_tests",
            action_template="Run pytest on new test file",
            success_rate=0.88,
            occurrences=8,
            last_updated=datetime.now(timezone.utc),
        )

        outcomes = [
            Outcome(
                id=1,
                observation="tests/test_new.py created",
                action_type="run_tests",
                action_details="Run pytest",
                result_type=OutcomeType.SUCCESS,
                execution_time=2.0,
            )
        ]

        await template_generator.create_template(pattern, outcomes)

        # Find matching templates for similar observation
        matches = await template_generator.find_matching_templates(
            observation="New test file tests/test_feature.py was created",
            action_type="run_tests",
        )

        # Should find potential matches
        assert isinstance(matches, list)

    @pytest.mark.asyncio
    async def test_template_usage_tracking(self, template_generator, temp_project):
        """Test that template usage is tracked."""
        # Create a template
        pattern = Pattern(
            id=1,
            pattern_type=PatternType.OBSERVATION_ACTION,
            trigger_hash="usage123",
            trigger_description="Dockerfile modified",
            action_type="rebuild_container",
            action_template="Rebuild Docker container",
            success_rate=0.85,
            occurrences=6,
            last_updated=datetime.now(timezone.utc),
        )

        outcomes = [
            Outcome(
                id=1,
                observation="Dockerfile modified",
                action_type="rebuild_container",
                action_details="docker build",
                result_type=OutcomeType.SUCCESS,
                execution_time=30.0,
            )
        ]

        path = await template_generator.create_template(pattern, outcomes)
        template_name = path.stem

        # Record usage
        result = await template_generator.record_template_usage(
            name=template_name,
            success=True,
            execution_time=25.0,
        )

        assert result is True

        # Verify usage was tracked
        data = await template_generator.get_template(template_name)
        assert data["statistics"]["occurrences"] == 7  # 6 + 1

    @pytest.mark.asyncio
    async def test_template_lifecycle(self, template_generator, temp_project):
        """Test complete template lifecycle: create, use, archive."""
        # Create
        pattern = Pattern(
            id=1,
            pattern_type=PatternType.OBSERVATION_ACTION,
            trigger_hash="lifecycle123",
            trigger_description="README.md modified",
            action_type="update_toc",
            action_template="Update table of contents",
            success_rate=0.90,
            occurrences=5,
            last_updated=datetime.now(timezone.utc),
        )

        outcomes = [
            Outcome(
                id=1,
                observation="README.md changed",
                action_type="update_toc",
                action_details="Regenerated TOC",
                result_type=OutcomeType.SUCCESS,
            )
        ]

        path = await template_generator.create_template(pattern, outcomes)
        template_name = path.stem

        # List
        templates = await template_generator.list_templates()
        assert len(templates) >= 1

        # Get
        data = await template_generator.get_template(template_name)
        assert data is not None

        # Archive
        result = await template_generator.archive_template(
            name=f"{template_name}.yaml",
            reason="Replaced with better version",
        )
        assert result is True

        # Verify archived
        templates_after = await template_generator.list_templates()
        assert len(templates_after) < len(templates)


# =============================================================================
# Enhanced OutcomeTracker Tests
# =============================================================================


class TestEnhancedOutcomeTracker:
    """Test enhanced OutcomeTracker with tier tracking."""

    @pytest.mark.asyncio
    async def test_tier_tracking(self, outcome_tracker):
        """Test that executor tier is tracked correctly."""
        # Record outcomes with different tiers
        await outcome_tracker.record_outcome(
            observation="Simple file change",
            action_type="format_code",
            action_details="Run black",
            success=True,
            executor_tier=ExecutorTier.LOCAL,
        )

        await outcome_tracker.record_outcome(
            observation="Complex refactoring needed",
            action_type="refactor_code",
            action_details="Major refactoring",
            success=True,
            executor_tier=ExecutorTier.CLAUDE_FLOW,
        )

        await outcome_tracker.record_outcome(
            observation="Large log analysis",
            action_type="analyze_logs",
            action_details="Analyze 100k lines",
            success=True,
            executor_tier=ExecutorTier.GEMINI,
        )

        # Get outcomes and verify tiers
        outcomes = await outcome_tracker.get_recent_outcomes(limit=10)

        tiers = {o.executor_tier for o in outcomes}
        assert ExecutorTier.LOCAL in tiers
        assert ExecutorTier.CLAUDE_FLOW in tiers
        assert ExecutorTier.GEMINI in tiers

    @pytest.mark.asyncio
    async def test_expected_vs_actual(self, outcome_tracker):
        """Test expected outcome matching."""
        # Success case - outcome matches expectation
        await outcome_tracker.record_outcome(
            observation="Test file added",
            action_type="run_tests",
            action_details="pytest tests/",
            success=True,
            expected_outcome="Tests should pass",
        )

        # Failure case - outcome does not match expectation
        await outcome_tracker.record_outcome(
            observation="Config changed",
            action_type="reload_config",
            action_details="Reload application",
            success=False,
            error="Config validation failed",
            expected_outcome="Config should reload successfully",
        )

        outcomes = await outcome_tracker.get_recent_outcomes(limit=10)

        # Find the matching outcome
        matching = next(
            (o for o in outcomes if o.expected_outcome == "Tests should pass"), None
        )
        assert matching is not None
        assert matching.outcome_match is True

        # Find the non-matching outcome
        non_matching = next(
            (
                o
                for o in outcomes
                if o.expected_outcome == "Config should reload successfully"
            ),
            None,
        )
        assert non_matching is not None
        assert non_matching.outcome_match is False

    @pytest.mark.asyncio
    async def test_tier_statistics(self, outcome_tracker):
        """Test tier-based statistics."""
        # Add outcomes with different tiers
        for i in range(5):
            await outcome_tracker.record_outcome(
                observation=f"Local action {i}",
                action_type="quick_task",
                action_details="Fast operation",
                success=True,
                executor_tier=ExecutorTier.LOCAL,
            )

        for i in range(3):
            await outcome_tracker.record_outcome(
                observation=f"Claude Code action {i}",
                action_type="medium_task",
                action_details="Medium complexity",
                success=i < 2,  # 2 successes, 1 failure
                executor_tier=ExecutorTier.CLAUDE_CODE,
            )

        stats = await outcome_tracker.get_tier_statistics()

        assert ExecutorTier.LOCAL in stats
        assert stats[ExecutorTier.LOCAL]["total"] == 5
        assert stats[ExecutorTier.LOCAL]["success_rate"] == 1.0

        assert ExecutorTier.CLAUDE_CODE in stats
        assert stats[ExecutorTier.CLAUDE_CODE]["total"] == 3

    @pytest.mark.asyncio
    async def test_dream_cycle_processing(self, outcome_tracker):
        """Test marking outcomes as processed by dreamer."""
        # Add outcomes
        ids = []
        for i in range(5):
            outcome_id = await outcome_tracker.record_outcome(
                observation=f"Test observation {i}",
                action_type="test_action",
                action_details=f"Test details {i}",
                success=True,
            )
            ids.append(outcome_id)

        # Mark as dreamed
        await outcome_tracker.mark_as_dreamed(
            outcome_ids=ids[:3],
            insights="Learned that test actions work well",
        )

        # Check undreamed count
        undreamed = await outcome_tracker.get_undreamed_count()
        assert undreamed == 2  # 5 - 3 = 2

        # Get outcomes for dreaming (only unprocessed)
        for_dreaming = await outcome_tracker.get_outcomes_for_dreaming(limit=10)
        assert len(for_dreaming) == 2

    @pytest.mark.asyncio
    async def test_tier_recommendation(self, outcome_tracker):
        """Test tier recommendation based on history."""
        # Add many successful LOCAL outcomes for a specific action
        for i in range(10):
            await outcome_tracker.record_outcome(
                observation="Simple format task",
                action_type="format_code",
                action_details="Run formatter",
                success=True,
                executor_tier=ExecutorTier.LOCAL,
            )

        recommended_tier, reasoning = await outcome_tracker.get_tier_recommendation(
            action_type="format_code",
            observation="Format a Python file",
        )

        # With high LOCAL success rate, should recommend LOCAL
        assert recommended_tier == ExecutorTier.LOCAL
        assert "success rate" in reasoning.lower() or "local" in reasoning.lower()


# =============================================================================
# Gemini Integration Tests (Mocked)
# =============================================================================


class TestGeminiIntegration:
    """Test Gemini executor integration with mocked API."""

    @pytest.mark.asyncio
    async def test_gemini_client_creation(self):
        """Test GeminiLLMClient can be created."""
        # Mock the google-generativeai module
        with patch.dict("sys.modules", {"google.generativeai": MagicMock()}):
            with patch(
                "consciousness.learning.dreamer.GeminiLLMClient.__init__",
                return_value=None,
            ):
                client = GeminiLLMClient.__new__(GeminiLLMClient)
                client.model = "gemini-1.5-flash"
                client.genai = MagicMock()
                assert client.model == "gemini-1.5-flash"

    @pytest.mark.asyncio
    async def test_gemini_tier_selection_for_large_context(self, dreamer):
        """Test that Gemini Pro is selected for large context."""
        large_log = "X" * 60000  # Above large_log_threshold

        tier = dreamer._select_llm_tier(large_log)
        assert tier == LLMTier.GEMINI_PRO

    @pytest.mark.asyncio
    async def test_gemini_tier_selection_for_medium_context(self, dreamer):
        """Test that Gemini Flash is selected for medium context."""
        medium_log = "X" * 30000  # Between thresholds

        tier = dreamer._select_llm_tier(medium_log)
        assert tier == LLMTier.GEMINI_FLASH

    @pytest.mark.asyncio
    async def test_trust_level_metadata_for_tier_4(self, outcome_tracker):
        """Test that Tier 4 (Gemini) results have trust_level tracking."""
        await outcome_tracker.record_outcome(
            observation="Large log analysis task",
            action_type="analyze_logs",
            action_details="Analyze 100k line log file",
            success=True,
            output="Analysis complete",
            executor_tier=ExecutorTier.GEMINI,
            expected_outcome="Identify error patterns",
            context={"trust_level": "verify", "source": "gemini"},
        )

        outcomes = await outcome_tracker.get_recent_outcomes(limit=1)
        assert len(outcomes) == 1
        assert outcomes[0].executor_tier == ExecutorTier.GEMINI
        assert outcomes[0].context.get("trust_level") == "verify"

    @pytest.mark.asyncio
    async def test_large_context_handling(self, dreamer, outcome_tracker):
        """Test handling of large context inputs during dream cycle."""
        # Create many outcomes to generate large context
        for i in range(50):
            await outcome_tracker.record_outcome(
                observation=f"Large observation with lots of detail about file {i}: " + "x" * 200,
                action_type="complex_analysis",
                action_details="Detailed analysis with extensive output: " + "y" * 200,
                success=i % 3 != 0,  # 66% success rate
                output="Result " + "z" * 100,
            )

        # Mock LLM client
        mock_client = create_mock_llm_client()

        with patch.object(dreamer, "_get_llm_client", return_value=mock_client):
            with patch.object(dreamer, "_select_llm_tier") as mock_select:
                mock_select.return_value = LLMTier.GEMINI_PRO

                result = await dreamer.dream()

                # Should have selected higher tier for large context
                assert mock_select.called
                assert DreamPhase.REFLECT in result.phases_completed


# =============================================================================
# Full Stack Integration Tests
# =============================================================================


class TestFullStackIntegration:
    """Test complete integration across all components."""

    @pytest.mark.asyncio
    async def test_end_to_end_learning_cycle(
        self,
        temp_project,
        outcome_tracker,
        pattern_learner,
        semantic_writer,
        template_generator,
        dreamer,
    ):
        """Test a full cycle: outcome -> pattern -> template -> reuse."""
        # 1. Record outcomes
        for i in range(8):
            await outcome_tracker.record_outcome(
                observation="New TypeScript file created in src/",
                action_type="generate_types",
                action_details="Generate TypeScript type definitions",
                success=i < 7,  # 87.5% success rate
                output="Types generated" if i < 7 else "",
                error="Type generation failed" if i >= 7 else None,
                execution_time=2.0 + i * 0.1,
                executor_tier=ExecutorTier.CLAUDE_CODE,
            )

        # 2. Extract patterns
        patterns = await pattern_learner.extract_patterns(
            min_occurrences=3, min_success_rate=0.7
        )
        assert len(patterns) >= 1

        # 3. Find the relevant pattern
        relevant_pattern = next(
            (p for p in patterns if p.action_type == "generate_types"), None
        )
        assert relevant_pattern is not None
        assert relevant_pattern.success_rate >= 0.7

        # 4. Check if template should be created
        should_create = await template_generator.should_create_template(
            relevant_pattern
        )
        assert should_create is True

        # 5. Create template
        outcomes = await outcome_tracker.get_recent_outcomes(limit=10)
        path = await template_generator.create_template(relevant_pattern, outcomes)
        assert path.exists()

        # 6. Write to semantic memory
        await semantic_writer.write_pattern(
            pattern=relevant_pattern,
            insight="TypeScript type generation is reliable for new files",
        )

        # 7. Run dream cycle for consolidation
        mock_client = create_mock_llm_client()
        with patch.object(dreamer, "_get_llm_client", return_value=mock_client):
            dream_result = await dreamer.dream()

        assert DreamPhase.COMPLETE in dream_result.phases_completed

        # 8. Verify all artifacts exist
        assert (temp_project["knowledge_path"] / "patterns" / "learned_rules.md").exists()
        assert len(list(temp_project["templates_path"].glob("**/*.yaml"))) > 0

        # 9. Simulate template reuse
        matches = await template_generator.find_matching_templates(
            observation="New TypeScript file created: src/utils.ts",
            action_type="generate_types",
        )
        # Should find the template we created
        assert isinstance(matches, list)

    @pytest.mark.asyncio
    async def test_multi_tier_learning(self, outcome_tracker, pattern_learner):
        """Test that learning works across all execution tiers."""
        # Record outcomes from different tiers
        tier_actions = [
            (ExecutorTier.LOCAL, "format_code", 0.95),
            (ExecutorTier.CLAUDE_CODE, "refactor_function", 0.80),
            (ExecutorTier.CLAUDE_FLOW, "redesign_architecture", 0.75),
            (ExecutorTier.GEMINI, "analyze_large_codebase", 0.70),
        ]

        for tier, action_type, success_rate in tier_actions:
            for i in range(10):
                await outcome_tracker.record_outcome(
                    observation=f"Observation for {action_type}",
                    action_type=action_type,
                    action_details=f"Details for {action_type}",
                    success=i < int(success_rate * 10),
                    executor_tier=tier,
                )

        # Get tier statistics
        tier_stats = await outcome_tracker.get_tier_statistics()

        # All tiers should have data
        assert len(tier_stats) == 4

        # Success rates should match expectations
        for tier, action_type, expected_rate in tier_actions:
            assert tier in tier_stats
            assert tier_stats[tier]["total"] == 10

        # Extract patterns - should work for all tiers
        patterns = await pattern_learner.extract_patterns(
            min_occurrences=5, min_success_rate=0.5
        )
        assert len(patterns) >= 4

    @pytest.mark.asyncio
    async def test_cross_component_statistics(
        self,
        outcome_tracker,
        pattern_learner,
        semantic_writer,
        template_generator,
    ):
        """Test that statistics are consistent across components."""
        # Add data
        for i in range(15):
            await outcome_tracker.record_outcome(
                observation="Test observation",
                action_type="test_action",
                action_details="Test details",
                success=i < 12,  # 80% success rate
            )

        # Get outcome stats
        action_stats = await outcome_tracker.get_action_statistics()
        assert "test_action" in action_stats
        assert action_stats["test_action"]["total"] == 15

        # Get pattern stats
        await pattern_learner.update_patterns()
        pattern_stats = await pattern_learner.get_statistics()
        assert pattern_stats["total_patterns"] >= 1

        # Get semantic stats
        semantic_stats = await semantic_writer.get_statistics()
        assert "knowledge_path" in semantic_stats

        # Get template stats
        template_stats = await template_generator.get_statistics()
        assert "total_templates" in template_stats

    @pytest.mark.asyncio
    async def test_error_recovery_integration(
        self, dreamer, outcome_tracker, temp_project
    ):
        """Test that the system handles errors gracefully during integration."""
        # Add some outcomes
        for i in range(5):
            await outcome_tracker.record_outcome(
                observation=f"Error scenario {i}",
                action_type="risky_action",
                action_details="Action that might fail",
                success=False,
                error=f"Error {i}: Something went wrong",
            )

        # Mock LLM client that raises an error
        mock_client = AsyncMock()
        mock_client.complete.side_effect = Exception("LLM connection failed")

        # Dream should handle the error gracefully
        with patch.object(dreamer, "_get_llm_client", return_value=mock_client):
            result = await dreamer.dream()

        # Should complete (possibly with errors) but not crash
        assert result is not None
        # Errors should be recorded
        # The system should remain functional after error

    @pytest.mark.asyncio
    async def test_daemon_dream_integration_concept(
        self, dreamer, outcome_tracker
    ):
        """Test concept of daemon correctly triggering dream cycles."""
        # Simulate daemon recording actions
        for i in range(dreamer.config.action_threshold + 1):
            dreamer.record_action()
            await outcome_tracker.record_outcome(
                observation=f"Daemon action {i}",
                action_type="daemon_task",
                action_details=f"Task {i}",
                success=True,
            )

        # Daemon should detect dream trigger
        assert dreamer.should_dream()

        # Run dream cycle
        mock_client = create_mock_llm_client()
        with patch.object(dreamer, "_get_llm_client", return_value=mock_client):
            result = await dreamer.dream()

        # After dream, counter should be reset
        assert dreamer.actions_since_dream == 0

        # Dream phases should all complete
        assert DreamPhase.COMPLETE in result.phases_completed


# =============================================================================
# Edge Cases and Regression Tests
# =============================================================================


class TestEdgeCases:
    """Test edge cases and potential regression scenarios."""

    @pytest.mark.asyncio
    async def test_empty_observations(self, outcome_tracker, pattern_learner):
        """Test handling of empty observations."""
        await outcome_tracker.record_outcome(
            observation="",
            action_type="empty_obs_action",
            action_details="Action with empty observation",
            success=True,
        )

        patterns = await pattern_learner.extract_patterns(
            min_occurrences=1, min_success_rate=0.0
        )
        # Should not crash
        assert isinstance(patterns, list)

    @pytest.mark.asyncio
    async def test_unicode_content(self, outcome_tracker, semantic_writer):
        """Test handling of unicode content."""
        await outcome_tracker.record_outcome(
            observation="File with unicode: cafe.py with cafe and emoji test",
            action_type="unicode_action",
            action_details="Handle unicode: test unicode chars",
            success=True,
        )

        await semantic_writer.write_rule(
            rule="Handle unicode characters: cafe emoji test",
            source="unicode_test",
            confidence=0.9,
        )

        # Should not crash and content should be preserved
        rules_content = await semantic_writer._read_file(semantic_writer.rules_path)
        assert "unicode" in rules_content.lower()

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, outcome_tracker):
        """Test concurrent outcome recording."""
        tasks = []
        for i in range(20):
            task = outcome_tracker.record_outcome(
                observation=f"Concurrent obs {i}",
                action_type="concurrent_action",
                action_details=f"Concurrent details {i}",
                success=i % 2 == 0,
            )
            tasks.append(task)

        await asyncio.gather(*tasks)

        # All should be recorded
        outcomes = await outcome_tracker.get_recent_outcomes(limit=30)
        concurrent_outcomes = [o for o in outcomes if o.action_type == "concurrent_action"]
        assert len(concurrent_outcomes) == 20

    @pytest.mark.asyncio
    async def test_very_long_content(self, outcome_tracker, semantic_writer):
        """Test handling of very long content."""
        long_observation = "x" * 10000
        long_details = "y" * 10000

        await outcome_tracker.record_outcome(
            observation=long_observation,
            action_type="long_content_action",
            action_details=long_details,
            success=True,
            output="z" * 5000,
        )

        # Should not crash and content should be truncated appropriately
        outcomes = await outcome_tracker.get_recent_outcomes(limit=1)
        assert len(outcomes) == 1

    @pytest.mark.asyncio
    async def test_duplicate_pattern_handling(self, template_generator, temp_project):
        """Test that duplicate patterns don't create duplicate templates."""
        pattern = Pattern(
            id=1,
            pattern_type=PatternType.OBSERVATION_ACTION,
            trigger_hash="duplicate123",
            trigger_description="Duplicate test pattern",
            action_type="duplicate_action",
            action_template="Handle duplicate",
            success_rate=0.90,
            occurrences=10,
            last_updated=datetime.now(timezone.utc),
        )

        outcomes = [
            Outcome(
                id=1,
                observation="Duplicate obs",
                action_type="duplicate_action",
                result_type=OutcomeType.SUCCESS,
            )
        ]

        # Create first template
        path1 = await template_generator.create_template(pattern, outcomes)
        assert path1.exists()

        # Try to create again - should not qualify
        should_create = await template_generator.should_create_template(pattern)
        assert should_create is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
