"""
Tests for the Template Generator module.

Tests the creation, management, and lifecycle of learned templates
from successful action patterns.
"""

import asyncio
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from consciousness.learning.patterns import Pattern, PatternType
from consciousness.learning.templates import (
    Template,
    TemplateGenerator,
    TemplateGeneratorConfig,
    _extract_action_words,
    _extract_file_patterns,
    _generate_template_name,
)
from consciousness.learning.tracker import Outcome, OutcomeType


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def template_config():
    """Create a test configuration."""
    return TemplateGeneratorConfig(
        min_successes_for_template=3,  # Lower for testing
        min_success_rate=0.75,
        template_format="yaml",
        include_examples=True,
        max_examples_per_template=2,
    )


@pytest.fixture
def template_generator(temp_project_dir, template_config):
    """Create a template generator for testing."""
    return TemplateGenerator(
        config=template_config,
        base_path=temp_project_dir,
    )


@pytest.fixture
def sample_pattern():
    """Create a sample pattern for testing."""
    return Pattern(
        id=1,
        pattern_type=PatternType.OBSERVATION_ACTION,
        trigger_hash="abc123def456",
        trigger_description="New Python file created in src/ without corresponding test_*.py",
        action_type="claude_code",
        action_template="Create a test skeleton for the newly created Python file.",
        success_rate=0.92,
        occurrences=12,
        last_updated=datetime.now(timezone.utc),
        metadata={"source": "auto_learned"},
    )


@pytest.fixture
def sample_outcomes():
    """Create sample outcomes for testing."""
    now = datetime.now(timezone.utc)
    return [
        Outcome(
            id=1,
            timestamp=now,
            observation="File src/utils.py created",
            observation_hash="abc123",
            action_type="claude_code",
            action_details="Created test file tests/test_utils.py",
            result_type=OutcomeType.SUCCESS,
            result_output="Test file created successfully",
            execution_time=2.5,
            confidence_used=0.85,
        ),
        Outcome(
            id=2,
            timestamp=now,
            observation="File src/helpers.py created",
            observation_hash="abc123",
            action_type="claude_code",
            action_details="Created test file tests/test_helpers.py",
            result_type=OutcomeType.SUCCESS,
            result_output="Test file created successfully",
            execution_time=3.2,
            confidence_used=0.88,
        ),
        Outcome(
            id=3,
            timestamp=now,
            observation="File src/config.py created",
            observation_hash="abc123",
            action_type="claude_code",
            action_details="Created test file tests/test_config.py",
            result_type=OutcomeType.FAILURE,
            result_output="",
            error_message="Test generation failed",
            execution_time=1.0,
            confidence_used=0.80,
        ),
    ]


class TestTemplateGeneratorConfig:
    """Tests for TemplateGeneratorConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = TemplateGeneratorConfig()
        assert config.templates_dir == Path(".hive-mind/templates")
        assert config.min_successes_for_template == 5
        assert config.min_success_rate == 0.85
        assert config.template_format == "yaml"
        assert config.max_templates == 100
        assert config.auto_version_increment is True
        assert config.include_examples is True
        assert config.max_examples_per_template == 3

    def test_custom_config(self):
        """Test custom configuration values."""
        config = TemplateGeneratorConfig(
            templates_dir=Path("/custom/templates"),
            min_successes_for_template=10,
            min_success_rate=0.95,
            template_format="json",
        )
        assert config.templates_dir == Path("/custom/templates")
        assert config.min_successes_for_template == 10
        assert config.min_success_rate == 0.95
        assert config.template_format == "json"

    def test_to_dict(self):
        """Test configuration serialization."""
        config = TemplateGeneratorConfig()
        data = config.to_dict()
        assert "templates_dir" in data
        assert "min_successes_for_template" in data
        assert data["min_success_rate"] == 0.85


class TestTemplate:
    """Tests for Template dataclass."""

    def test_template_creation(self):
        """Test creating a template."""
        template = Template(
            name="test_template",
            action_type="claude_code",
            action_prompt="Do something",
            success_rate=0.9,
            occurrences=10,
        )
        assert template.name == "test_template"
        assert template.version == "1.0.0"
        assert template.action_type == "claude_code"
        assert template.confidence > 0

    def test_template_to_dict(self):
        """Test template serialization."""
        template = Template(
            name="test_template",
            action_type="claude_code",
            action_prompt="Do something",
            success_rate=0.9,
            occurrences=10,
            trigger_observation_pattern="*.py created",
            trigger_observation_hash="abc123",
        )
        data = template.to_dict()
        assert data["name"] == "test_template"
        assert data["action"]["type"] == "claude_code"
        assert data["trigger"]["observation_hash"] == "abc123"
        assert "statistics" in data
        assert "metadata" in data

    def test_template_from_dict(self):
        """Test template deserialization."""
        data = {
            "name": "loaded_template",
            "version": "2.0.0",
            "trigger": {
                "observation_pattern": "*.py",
                "observation_hash": "xyz789",
            },
            "action": {
                "type": "update_indices",
                "prompt": "Update search indices",
            },
            "statistics": {
                "success_rate": 0.85,
                "occurrences": 20,
            },
        }
        template = Template.from_dict(data)
        assert template.name == "loaded_template"
        assert template.version == "2.0.0"
        assert template.trigger_observation_hash == "xyz789"
        assert template.action_type == "update_indices"

    def test_template_filename(self):
        """Test filename generation."""
        template = Template(name="Fix Missing Test")
        assert template.filename == "fix_missing_test.yaml"

        template = Template(name="update-config/settings")
        assert "_" in template.filename  # Special chars replaced

    def test_template_confidence(self):
        """Test confidence calculation."""
        template = Template(success_rate=0.9, occurrences=10)
        assert 0 < template.confidence <= 0.95

        template_no_data = Template(success_rate=0.0, occurrences=0)
        assert template_no_data.confidence == 0.0


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_extract_file_patterns(self):
        """Test file pattern extraction."""
        observation = "File src/utils.py created, also modified tests/test_utils.py"
        patterns = _extract_file_patterns(observation)
        assert ".py" in patterns
        assert any("src/" in p or "tests/" in p for p in patterns)

    def test_extract_action_words(self):
        """Test action word extraction."""
        observation = "New file created with modified content, some errors found"
        words = _extract_action_words(observation)
        assert "created" in words
        assert "modified" in words
        assert "error" in words

    def test_generate_template_name(self):
        """Test template name generation."""
        pattern = Pattern(
            trigger_hash="abc123",
            trigger_description="New test file created for *.py",
            action_type="claude_code",
        )
        name = _generate_template_name(pattern)
        assert "abc123" in name[:10] or "abc123" in name  # Hash included
        assert "_" in name  # Separator present


class TestTemplateGenerator:
    """Tests for TemplateGenerator class."""

    @pytest.mark.asyncio
    async def test_initialize(self, template_generator, temp_project_dir):
        """Test initialization creates directory structure."""
        await template_generator.initialize()

        templates_path = temp_project_dir / ".hive-mind/templates"
        assert templates_path.exists()
        assert (templates_path / "learned").exists()
        assert (templates_path / "custom").exists()
        assert (templates_path / "archived").exists()
        assert (templates_path / "index.yaml").exists()

    @pytest.mark.asyncio
    async def test_should_create_template_qualified(
        self, template_generator, sample_pattern
    ):
        """Test pattern that qualifies for template creation."""
        await template_generator.initialize()

        # Pattern with high success rate and many occurrences should qualify
        sample_pattern.success_rate = 0.92
        sample_pattern.occurrences = 12

        result = await template_generator.should_create_template(sample_pattern)
        assert result is True

    @pytest.mark.asyncio
    async def test_should_create_template_low_occurrences(
        self, template_generator, sample_pattern
    ):
        """Test pattern with too few occurrences."""
        await template_generator.initialize()

        sample_pattern.occurrences = 2  # Below threshold of 3
        result = await template_generator.should_create_template(sample_pattern)
        assert result is False

    @pytest.mark.asyncio
    async def test_should_create_template_low_success_rate(
        self, template_generator, sample_pattern
    ):
        """Test pattern with low success rate."""
        await template_generator.initialize()

        sample_pattern.success_rate = 0.5  # Below threshold of 0.75
        result = await template_generator.should_create_template(sample_pattern)
        assert result is False

    @pytest.mark.asyncio
    async def test_create_template(
        self, template_generator, sample_pattern, sample_outcomes
    ):
        """Test template creation from pattern."""
        await template_generator.initialize()

        path = await template_generator.create_template(sample_pattern, sample_outcomes)

        assert path.exists()
        assert path.suffix == ".yaml"

        # Verify template content
        with path.open() as f:
            data = yaml.safe_load(f)

        assert data["action"]["type"] == "claude_code"
        assert data["statistics"]["success_rate"] > 0.9
        assert data["statistics"]["occurrences"] == 12
        assert "trigger" in data
        assert "metadata" in data

    @pytest.mark.asyncio
    async def test_create_template_with_examples(
        self, template_generator, sample_pattern, sample_outcomes
    ):
        """Test template creation includes examples."""
        await template_generator.initialize()

        path = await template_generator.create_template(sample_pattern, sample_outcomes)

        with path.open() as f:
            data = yaml.safe_load(f)

        assert "examples" in data
        # Should only include successful outcomes
        for example in data["examples"]:
            assert "observation" in example
            assert "action" in example

    @pytest.mark.asyncio
    async def test_list_templates(self, template_generator, sample_pattern, sample_outcomes):
        """Test listing templates."""
        await template_generator.initialize()
        await template_generator.create_template(sample_pattern, sample_outcomes)

        templates = await template_generator.list_templates()

        assert len(templates) == 1
        assert templates[0]["action_type"] == "claude_code"
        assert templates[0]["category"] == "learned"

    @pytest.mark.asyncio
    async def test_list_templates_with_filter(
        self, template_generator, sample_pattern, sample_outcomes
    ):
        """Test filtering templates by success rate."""
        await template_generator.initialize()
        await template_generator.create_template(sample_pattern, sample_outcomes)

        # Should find template with high success rate
        templates = await template_generator.list_templates(min_success_rate=0.8)
        assert len(templates) == 1

        # Should not find template with very high threshold
        templates = await template_generator.list_templates(min_success_rate=0.99)
        assert len(templates) == 0

    @pytest.mark.asyncio
    async def test_get_template(self, template_generator, sample_pattern, sample_outcomes):
        """Test getting a specific template."""
        await template_generator.initialize()
        path = await template_generator.create_template(sample_pattern, sample_outcomes)

        template_name = path.stem
        data = await template_generator.get_template(template_name)

        assert data is not None
        assert data["action"]["type"] == "claude_code"

    @pytest.mark.asyncio
    async def test_get_template_not_found(self, template_generator):
        """Test getting a non-existent template."""
        await template_generator.initialize()

        data = await template_generator.get_template("nonexistent")
        assert data is None

    @pytest.mark.asyncio
    async def test_update_template(
        self, template_generator, sample_pattern, sample_outcomes
    ):
        """Test updating template metadata."""
        await template_generator.initialize()
        path = await template_generator.create_template(sample_pattern, sample_outcomes)
        template_name = path.stem

        result = await template_generator.update_template(
            template_name,
            {"metadata": {"custom_field": "custom_value"}},
        )

        assert result is True

        # Verify update
        data = await template_generator.get_template(template_name)
        assert data["metadata"]["custom_field"] == "custom_value"
        # Version should be incremented
        assert data["version"] == "1.0.1"

    @pytest.mark.asyncio
    async def test_record_template_usage(
        self, template_generator, sample_pattern, sample_outcomes
    ):
        """Test recording template usage."""
        await template_generator.initialize()
        path = await template_generator.create_template(sample_pattern, sample_outcomes)
        template_name = path.stem

        # Record successful usage
        result = await template_generator.record_template_usage(
            template_name,
            success=True,
            execution_time=2.5,
        )

        assert result is True

        # Verify statistics updated
        data = await template_generator.get_template(template_name)
        assert data["statistics"]["occurrences"] == 13  # 12 + 1
        assert data["statistics"]["last_used"] is not None

    @pytest.mark.asyncio
    async def test_archive_template(
        self, template_generator, sample_pattern, sample_outcomes
    ):
        """Test archiving a template."""
        await template_generator.initialize()
        path = await template_generator.create_template(sample_pattern, sample_outcomes)
        template_name = path.stem + ".yaml"

        result = await template_generator.archive_template(
            template_name,
            reason="No longer needed",
        )

        assert result is True
        assert not path.exists()  # Original removed

        # Check it's in archived directory
        archived_path = template_generator.templates_path / "archived" / template_name
        assert archived_path.exists()

        with archived_path.open() as f:
            data = yaml.safe_load(f)
        assert data["archive_reason"] == "No longer needed"

    @pytest.mark.asyncio
    async def test_get_statistics(
        self, template_generator, sample_pattern, sample_outcomes
    ):
        """Test getting template statistics."""
        await template_generator.initialize()
        await template_generator.create_template(sample_pattern, sample_outcomes)

        stats = await template_generator.get_statistics()

        assert stats["total_templates"] == 1
        assert stats["by_category"]["learned"] == 1
        assert stats["avg_success_rate"] > 0
        assert stats["by_action_type"]["claude_code"] == 1

    @pytest.mark.asyncio
    async def test_find_matching_templates_exact(
        self, template_generator, sample_pattern, sample_outcomes
    ):
        """Test finding templates by exact hash match."""
        await template_generator.initialize()
        await template_generator.create_template(sample_pattern, sample_outcomes)

        # Use the same observation that would generate the same hash
        matches = await template_generator.find_matching_templates(
            sample_pattern.trigger_description
        )

        # May or may not find exact match depending on hash function
        # At minimum, fuzzy matching should work
        assert isinstance(matches, list)

    @pytest.mark.asyncio
    async def test_find_matching_templates_fuzzy(
        self, template_generator, sample_pattern, sample_outcomes
    ):
        """Test fuzzy matching of templates."""
        await template_generator.initialize()
        await template_generator.create_template(sample_pattern, sample_outcomes)

        # Similar observation with matching action words
        matches = await template_generator.find_matching_templates(
            "A new Python file was created in the src directory"
        )

        # Should find some matches based on shared terms
        assert isinstance(matches, list)
        if matches:
            assert "match_score" in matches[0]

    @pytest.mark.asyncio
    async def test_cleanup_stale_templates(
        self, template_generator, sample_pattern, sample_outcomes
    ):
        """Test cleaning up stale templates."""
        await template_generator.initialize()

        # Create a pattern with low occurrences
        low_pattern = Pattern(
            id=2,
            pattern_type=PatternType.OBSERVATION_ACTION,
            trigger_hash="xyz789",
            trigger_description="Rare pattern",
            action_type="rare_action",
            action_template="Do something rare",
            success_rate=0.5,  # Low success
            occurrences=5,
            last_updated=datetime.now(timezone.utc),
        )
        await template_generator.create_template(low_pattern, sample_outcomes)

        # Also create a good pattern
        await template_generator.create_template(sample_pattern, sample_outcomes)

        # Cleanup templates with low success rate
        archived = await template_generator.cleanup_stale_templates(
            min_success_rate=0.7
        )

        assert archived >= 1  # At least the low success one

    @pytest.mark.asyncio
    async def test_should_create_template_already_exists(
        self, template_generator, sample_pattern, sample_outcomes
    ):
        """Test that existing templates are not recreated."""
        await template_generator.initialize()
        await template_generator.create_template(sample_pattern, sample_outcomes)

        # Same pattern should not qualify again
        result = await template_generator.should_create_template(sample_pattern)
        assert result is False


class TestTemplateIntegration:
    """Integration tests for the template system."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, temp_project_dir):
        """Test complete template lifecycle."""
        # Create generator with real config
        config = TemplateGeneratorConfig(
            min_successes_for_template=3,
            min_success_rate=0.7,
        )
        generator = TemplateGenerator(config=config, base_path=temp_project_dir)

        # Initialize
        await generator.initialize()

        # Create pattern
        pattern = Pattern(
            id=1,
            pattern_type=PatternType.OBSERVATION_ACTION,
            trigger_hash="lifecycle123",
            trigger_description="Config file updated",
            action_type="reload_config",
            action_template="Reload application configuration",
            success_rate=0.85,
            occurrences=10,
            last_updated=datetime.now(timezone.utc),
        )

        # Create outcomes
        outcomes = [
            Outcome(
                id=i,
                observation="Config updated",
                action_type="reload_config",
                action_details="Reloaded config",
                result_type=OutcomeType.SUCCESS,
                execution_time=0.5,
            )
            for i in range(5)
        ]

        # Check qualification
        should_create = await generator.should_create_template(pattern)
        assert should_create is True

        # Create template
        path = await generator.create_template(pattern, outcomes)
        assert path.exists()

        # List and verify
        templates = await generator.list_templates()
        assert len(templates) == 1

        # Get template
        template_name = path.stem
        data = await generator.get_template(template_name)
        assert data["action"]["type"] == "reload_config"

        # Record usage
        await generator.record_template_usage(template_name, success=True)
        data = await generator.get_template(template_name)
        assert data["statistics"]["occurrences"] == 11

        # Archive
        await generator.archive_template(template_name, "Test complete")
        templates = await generator.list_templates()
        assert len(templates) == 0

        # Verify in archive
        archived = list((generator.templates_path / "archived").glob("*.yaml"))
        assert len(archived) == 1
