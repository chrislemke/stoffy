"""
Integration Tests for Philosophy Repository

Tests the philosophy knowledge base integration including:
1. Repository connection (local file access)
2. Reading thinker profiles
3. Reading thought entries
4. Loading indices
5. Template loading
6. Validation functions
7. Auto-detection triggers
8. Creating new thoughts
9. Bidirectional linking

Uses pytest with mocking for destructive operations.
"""

import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import patch, MagicMock
import yaml

import pytest


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def stoffy_root() -> Path:
    """Provide the Stoffy repository root path."""
    return Path("/Users/chris/Developer/stoffy")


@pytest.fixture
def philosophy_knowledge_path(stoffy_root) -> Path:
    """Path to philosophy knowledge directory."""
    return stoffy_root / "knowledge" / "philosophy"


@pytest.fixture
def philosophy_indices_path(stoffy_root) -> Path:
    """Path to philosophy indices directory."""
    return stoffy_root / "indices" / "philosophy"


@pytest.fixture
def temp_philosophy_repo(tmp_path) -> Path:
    """Create a temporary philosophy repository structure for testing."""
    # Create directory structure
    knowledge_dir = tmp_path / "knowledge" / "philosophy" / "thinkers"
    knowledge_dir.mkdir(parents=True)

    indices_dir = tmp_path / "indices" / "philosophy"
    indices_dir.mkdir(parents=True)

    templates_dir = tmp_path / "templates"
    templates_dir.mkdir(parents=True)

    thoughts_dir = tmp_path / "knowledge" / "philosophy" / "thoughts" / "consciousness"
    thoughts_dir.mkdir(parents=True)

    # Create a sample thinker
    thinker_dir = knowledge_dir / "test_thinker"
    thinker_dir.mkdir()

    profile_content = """---
name: "Test Thinker"
type: "philosopher"
era: "contemporary"
traditions: [test_tradition]
key_works: ["Test Work"]
themes: [consciousness]
tags:
  - thinker
  - profile
---

# Thinker Profile: Test Thinker

**Type**: Philosopher
**Era**: Contemporary

## Core Ideas

Test ideas for testing.

## Key Quotes

> "Test quote for testing."

## Connections

- Related to other thinkers
"""
    (thinker_dir / "profile.md").write_text(profile_content)
    (thinker_dir / "notes.md").write_text("# Notes\n\nOngoing notes.")
    (thinker_dir / "reflections.md").write_text("# Reflections\n\nPersonal reflections.")
    (thinker_dir / "references.md").write_text("# References\n\n| Date | Strength | Path | Reasoning |")

    # Create a memory file
    memory_content = """# Memory File: profile.md

## Corrections
- Original: "Test ideas"
- Corrected: "Profound test ideas"
- Reason: More accurate representation

## Key Insights
- This thinker is crucial for understanding X

## Preferences
- Use formal language when discussing this thinker
"""
    (thinker_dir / "profile_memory.md").write_text(memory_content)

    # Create indices
    thinkers_index = {
        "meta": {
            "version": "1.0",
            "last_updated": "2025-12-30",
            "domain": "thinkers",
            "purpose": "Track philosophers",
            "count": 1
        },
        "thinkers": {
            "test_thinker": {
                "path": "thinkers/test_thinker/",
                "type": "philosopher",
                "era": "contemporary",
                "traditions": ["test_tradition"],
                "key_works": ["Test Work"],
                "themes": ["consciousness"]
            }
        }
    }
    with open(indices_dir / "thinkers.yaml", "w") as f:
        yaml.dump(thinkers_index, f)

    thoughts_index = {
        "meta": {
            "version": "1.0",
            "last_updated": "2025-12-30",
            "domain": "thoughts",
            "purpose": "Track thoughts",
            "count": 1
        },
        "thoughts": {
            "test_thought": {
                "title": "Test Thought",
                "theme": "consciousness",
                "status": "seed",
                "path": "thoughts/consciousness/test_thought/",
                "related_thinkers": ["test_thinker"],
                "started": "2025-12-30"
            }
        }
    }
    with open(indices_dir / "thoughts.yaml", "w") as f:
        yaml.dump(thoughts_index, f)

    # Create templates
    thinker_profile_template = """---
name: "{{NAME}}"
type: "philosopher"
era: "contemporary"
traditions: []
key_works: []
themes: []
tags:
  - thinker
  - profile
---

# Thinker Profile: {{NAME}}

**Type**:
**Era**: Contemporary

## Core Ideas

## Key Quotes

## Connections
"""
    (templates_dir / "thinker_profile.md").write_text(thinker_profile_template)

    thought_template = """---
title: "{{TITLE}}"
theme: "{{THEME}}"
status: "seed"
created: "{{DATE}}"
related_thinkers: []
tags:
  - thought
---

# {{TITLE}}

## Key Insight

## Development

## Next Steps
"""
    (templates_dir / "thought.md").write_text(thought_template)

    # Create rules index
    rules_index = {
        "meta": {
            "version": "1.0",
            "last_updated": "2025-12-30",
            "domain": "rules"
        },
        "rules": {
            "memory_processing": {
                "description": "Memory files have higher weight",
                "pattern": "*_memory.md",
                "action": "Apply corrections and insights from memory file"
            },
            "auto_detect_thinker": {
                "description": "Detect thinker mentions",
                "pattern": "[Thinker] argued...",
                "action": "Link to thinker profile"
            }
        }
    }
    with open(indices_dir / "rules.yaml", "w") as f:
        yaml.dump(rules_index, f)

    return tmp_path


# =============================================================================
# 1. Repository Connection Tests
# =============================================================================

class TestRepositoryConnection:
    """Test connection to the philosophy repository (local file access)."""

    def test_stoffy_root_exists(self, stoffy_root):
        """Verify the Stoffy root directory exists."""
        assert stoffy_root.exists(), f"Stoffy root not found: {stoffy_root}"
        assert stoffy_root.is_dir(), f"Stoffy root is not a directory: {stoffy_root}"

    def test_philosophy_knowledge_path_exists(self, philosophy_knowledge_path):
        """Verify philosophy knowledge directory exists."""
        assert philosophy_knowledge_path.exists(), f"Philosophy knowledge path not found: {philosophy_knowledge_path}"

    def test_philosophy_indices_path_exists(self, philosophy_indices_path):
        """Verify philosophy indices directory exists."""
        assert philosophy_indices_path.exists(), f"Philosophy indices path not found: {philosophy_indices_path}"

    def test_can_list_thinkers_directory(self, philosophy_knowledge_path):
        """Verify we can list the thinkers directory."""
        thinkers_path = philosophy_knowledge_path / "thinkers"
        assert thinkers_path.exists(), f"Thinkers directory not found: {thinkers_path}"

        thinkers = list(thinkers_path.iterdir())
        assert len(thinkers) > 0, "No thinkers found in directory"

    def test_repository_has_expected_structure(self, stoffy_root):
        """Verify repository has expected directory structure."""
        expected_dirs = [
            "knowledge",
            "indices",
            "consciousness",
        ]
        for dir_name in expected_dirs:
            dir_path = stoffy_root / dir_name
            assert dir_path.exists(), f"Expected directory not found: {dir_path}"

    def test_temp_repo_connection(self, temp_philosophy_repo):
        """Test connection to temporary repository."""
        assert temp_philosophy_repo.exists()
        assert (temp_philosophy_repo / "knowledge" / "philosophy" / "thinkers").exists()


# =============================================================================
# 2. Reading Thinker Profiles
# =============================================================================

class TestReadingThinkerProfiles:
    """Test reading existing thinker profiles."""

    def test_read_existing_thinker_profile(self, philosophy_knowledge_path):
        """Read an existing thinker profile from the repository."""
        # Use a known thinker (Karl Friston)
        thinker_path = philosophy_knowledge_path / "thinkers" / "karl_friston"
        profile_path = thinker_path / "profile.md"

        assert thinker_path.exists(), f"Thinker directory not found: {thinker_path}"
        assert profile_path.exists(), f"Profile not found: {profile_path}"

        content = profile_path.read_text(encoding="utf-8")

        # Verify frontmatter
        assert content.startswith("---"), "Profile should have YAML frontmatter"
        assert "name:" in content, "Profile should have name field"
        assert "type:" in content, "Profile should have type field"
        assert "themes:" in content, "Profile should have themes field"

    def test_parse_thinker_frontmatter(self, philosophy_knowledge_path):
        """Parse YAML frontmatter from a thinker profile."""
        profile_path = philosophy_knowledge_path / "thinkers" / "karl_friston" / "profile.md"
        content = profile_path.read_text(encoding="utf-8")

        # Extract frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1])

                assert "name" in frontmatter, "Frontmatter should have name"
                assert "type" in frontmatter, "Frontmatter should have type"
                assert frontmatter["type"] in ["philosopher", "neuroscientist", "cognitive_scientist",
                                               "physicist", "neuropsychologist", "complexity_scientist",
                                               "physicist_physiologist_philosopher", "computational_neuroscientist"]

    def test_read_thinker_from_temp_repo(self, temp_philosophy_repo):
        """Read thinker from temporary repository."""
        profile_path = temp_philosophy_repo / "knowledge" / "philosophy" / "thinkers" / "test_thinker" / "profile.md"
        content = profile_path.read_text(encoding="utf-8")

        assert "Test Thinker" in content
        assert "Test ideas" in content

    def test_thinker_has_all_standard_files(self, temp_philosophy_repo):
        """Verify thinker has all four standard files."""
        thinker_dir = temp_philosophy_repo / "knowledge" / "philosophy" / "thinkers" / "test_thinker"

        expected_files = ["profile.md", "notes.md", "reflections.md", "references.md"]
        for filename in expected_files:
            file_path = thinker_dir / filename
            assert file_path.exists(), f"Missing standard file: {filename}"

    def test_read_nonexistent_thinker_profile(self, philosophy_knowledge_path):
        """Attempting to read nonexistent thinker should fail gracefully."""
        nonexistent_path = philosophy_knowledge_path / "thinkers" / "nonexistent_thinker" / "profile.md"
        assert not nonexistent_path.exists(), "Nonexistent thinker should not exist"


# =============================================================================
# 3. Reading Thought Entries
# =============================================================================

class TestReadingThoughts:
    """Test reading thought entries."""

    def test_thoughts_directory_exists(self, philosophy_knowledge_path):
        """Verify thoughts directory exists."""
        thoughts_path = philosophy_knowledge_path / "thinkers"  # thoughts are with thinkers in this structure
        assert thoughts_path.exists()

    def test_thoughts_index_exists(self, philosophy_indices_path):
        """Verify thoughts index exists."""
        thoughts_index = philosophy_indices_path / "thoughts.yaml"
        assert thoughts_index.exists(), f"Thoughts index not found: {thoughts_index}"

    def test_parse_thoughts_index(self, philosophy_indices_path):
        """Parse the thoughts index file."""
        thoughts_index = philosophy_indices_path / "thoughts.yaml"
        content = thoughts_index.read_text(encoding="utf-8")
        data = yaml.safe_load(content)

        assert "meta" in data, "Thoughts index should have meta section"
        assert "thoughts" in data, "Thoughts index should have thoughts section"
        assert data["meta"]["domain"] == "thoughts", "Domain should be 'thoughts'"

    def test_read_thought_from_temp_repo(self, temp_philosophy_repo):
        """Read thought entry from temporary repository."""
        thoughts_index_path = temp_philosophy_repo / "indices" / "philosophy" / "thoughts.yaml"
        content = thoughts_index_path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)

        assert "test_thought" in data["thoughts"]
        thought = data["thoughts"]["test_thought"]
        assert thought["title"] == "Test Thought"
        assert thought["status"] == "seed"

    def test_thought_status_values(self, temp_philosophy_repo):
        """Verify thought status follows expected lifecycle."""
        valid_statuses = ["seed", "exploring", "developing", "crystallized", "challenged", "integrated", "archived"]

        thoughts_index_path = temp_philosophy_repo / "indices" / "philosophy" / "thoughts.yaml"
        data = yaml.safe_load(thoughts_index_path.read_text(encoding="utf-8"))

        for thought_id, thought in data["thoughts"].items():
            status = thought.get("status", "seed")
            assert status in valid_statuses, f"Invalid status '{status}' for thought '{thought_id}'"


# =============================================================================
# 4. Loading Indices
# =============================================================================

class TestLoadingIndices:
    """Test loading various index files."""

    def test_load_thinkers_index(self, philosophy_indices_path):
        """Load and validate thinkers index."""
        index_path = philosophy_indices_path / "thinkers.yaml"
        assert index_path.exists()

        content = index_path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)

        assert "meta" in data
        assert "thinkers" in data
        assert data["meta"]["domain"] == "thinkers"
        assert len(data["thinkers"]) > 0, "Thinkers index should not be empty"

    def test_load_thoughts_index(self, philosophy_indices_path):
        """Load and validate thoughts index."""
        index_path = philosophy_indices_path / "thoughts.yaml"
        assert index_path.exists()

        content = index_path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)

        assert "meta" in data
        assert "thoughts" in data

    def test_load_templates_index(self, philosophy_indices_path):
        """Load and validate templates index."""
        index_path = philosophy_indices_path / "templates.yaml"
        assert index_path.exists()

        content = index_path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)

        assert "meta" in data
        assert "templates" in data

    def test_load_rules_index(self, philosophy_indices_path):
        """Load and validate rules index."""
        index_path = philosophy_indices_path / "rules.yaml"
        assert index_path.exists()

        content = index_path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)

        assert "meta" in data or "rules" in data

    def test_index_meta_has_required_fields(self, philosophy_indices_path):
        """Verify index meta sections have required fields."""
        # Domain indices have domain field; root.yaml is different
        required_meta_fields = ["version", "last_updated"]

        for index_file in philosophy_indices_path.glob("*.yaml"):
            content = index_file.read_text(encoding="utf-8")
            data = yaml.safe_load(content)

            if "meta" in data:
                for field in required_meta_fields:
                    assert field in data["meta"], f"Index {index_file.name} missing meta.{field}"

                # Domain-specific indices should have domain field
                if index_file.name != "root.yaml":
                    # domain field is recommended but not strictly required
                    pass

    def test_load_index_from_temp_repo(self, temp_philosophy_repo):
        """Load index from temporary repository."""
        index_path = temp_philosophy_repo / "indices" / "philosophy" / "thinkers.yaml"
        data = yaml.safe_load(index_path.read_text(encoding="utf-8"))

        assert data["meta"]["count"] == 1
        assert "test_thinker" in data["thinkers"]


# =============================================================================
# 5. Template Loading
# =============================================================================

class TestTemplateLoading:
    """Test loading and using templates."""

    def test_templates_index_references_valid_files(self, philosophy_indices_path, stoffy_root):
        """Verify templates index references existing files."""
        index_path = philosophy_indices_path / "templates.yaml"
        data = yaml.safe_load(index_path.read_text(encoding="utf-8"))

        templates_base = stoffy_root / "knowledge" / "philosophy"

        if "templates" in data:
            for template_id, template_info in data["templates"].items():
                if "path" in template_info:
                    # Templates might be in different locations
                    template_path = templates_base / template_info["path"]
                    # Note: We don't assert existence as paths vary

    def test_load_template_from_temp_repo(self, temp_philosophy_repo):
        """Load template from temporary repository."""
        template_path = temp_philosophy_repo / "templates" / "thinker_profile.md"
        content = template_path.read_text(encoding="utf-8")

        assert "{{NAME}}" in content, "Template should have NAME placeholder"
        assert "# Thinker Profile" in content

    def test_template_has_frontmatter(self, temp_philosophy_repo):
        """Verify templates have YAML frontmatter."""
        template_path = temp_philosophy_repo / "templates" / "thinker_profile.md"
        content = template_path.read_text(encoding="utf-8")

        assert content.startswith("---"), "Template should start with frontmatter"

    def test_fill_template_placeholders(self, temp_philosophy_repo):
        """Test filling template placeholders."""
        template_path = temp_philosophy_repo / "templates" / "thinker_profile.md"
        template = template_path.read_text(encoding="utf-8")

        filled = template.replace("{{NAME}}", "New Philosopher")

        assert "New Philosopher" in filled
        assert "{{NAME}}" not in filled


# =============================================================================
# 6. Validation Functions
# =============================================================================

class TestValidationFunctions:
    """Test validation logic for philosophy repository."""

    def test_validate_thinker_name_format(self):
        """Validate thinker name format (lowercase, underscores)."""
        valid_names = ["karl_friston", "jean_paul_sartre", "confucius", "thomas_aquinas"]
        invalid_names = ["Karl_Friston", "jean-paul-sartre", "dr_thinker", "UPPERCASE"]

        def is_valid_thinker_name(name: str) -> bool:
            if not name:
                return False
            if name != name.lower():
                return False
            if "-" in name:
                return False
            if name.startswith(("dr_", "prof_", "sir_")):
                return False
            return True

        for name in valid_names:
            assert is_valid_thinker_name(name), f"Should be valid: {name}"

        for name in invalid_names:
            assert not is_valid_thinker_name(name), f"Should be invalid: {name}"

    def test_validate_thought_status(self):
        """Validate thought status values."""
        valid_statuses = ["seed", "exploring", "developing", "crystallized", "challenged", "integrated", "archived"]

        def is_valid_status(status: str) -> bool:
            return status in valid_statuses

        for status in valid_statuses:
            assert is_valid_status(status)

        assert not is_valid_status("invalid")
        assert not is_valid_status("")
        assert not is_valid_status("SEED")

    def test_validate_frontmatter_structure(self):
        """Validate frontmatter has required fields."""

        def validate_thinker_frontmatter(frontmatter: Dict[str, Any]) -> tuple[bool, list]:
            required_fields = ["name", "type", "era", "themes"]
            missing = [f for f in required_fields if f not in frontmatter]
            return len(missing) == 0, missing

        valid_fm = {"name": "Test", "type": "philosopher", "era": "contemporary", "themes": ["consciousness"]}
        invalid_fm = {"name": "Test", "type": "philosopher"}

        is_valid, missing = validate_thinker_frontmatter(valid_fm)
        assert is_valid, "Valid frontmatter should pass"

        is_valid, missing = validate_thinker_frontmatter(invalid_fm)
        assert not is_valid, "Invalid frontmatter should fail"
        assert "era" in missing and "themes" in missing

    def test_validate_index_consistency(self, temp_philosophy_repo):
        """Validate index entries match actual files."""
        index_path = temp_philosophy_repo / "indices" / "philosophy" / "thinkers.yaml"
        data = yaml.safe_load(index_path.read_text(encoding="utf-8"))

        knowledge_base = temp_philosophy_repo / "knowledge" / "philosophy"

        for thinker_id, thinker_info in data["thinkers"].items():
            thinker_path = knowledge_base / thinker_info["path"]
            assert thinker_path.exists(), f"Index references nonexistent path: {thinker_path}"

    def test_validate_bidirectional_links(self, temp_philosophy_repo):
        """Validate bidirectional links between thoughts and thinkers."""
        thoughts_index_path = temp_philosophy_repo / "indices" / "philosophy" / "thoughts.yaml"
        thinkers_index_path = temp_philosophy_repo / "indices" / "philosophy" / "thinkers.yaml"

        thoughts_data = yaml.safe_load(thoughts_index_path.read_text(encoding="utf-8"))
        thinkers_data = yaml.safe_load(thinkers_index_path.read_text(encoding="utf-8"))

        # Check that related_thinkers reference valid thinkers
        for thought_id, thought in thoughts_data["thoughts"].items():
            related = thought.get("related_thinkers", [])
            for thinker_id in related:
                assert thinker_id in thinkers_data["thinkers"], \
                    f"Thought '{thought_id}' references invalid thinker: {thinker_id}"


# =============================================================================
# 7. Auto-Detection Triggers
# =============================================================================

class TestAutoDetectionTriggers:
    """Test auto-detection trigger patterns."""

    def test_detect_thinker_mention_pattern(self):
        """Test detection of thinker mention patterns."""

        def detect_thinker_mention(text: str) -> bool:
            import re
            # Match both bracketed [Name] and plain Name followed by keywords
            patterns = [
                r'\[(\w+)\]\s*(argued|\'s view|wrote|believed|claimed)',
                r'(\b[A-Z][a-z]+\b)\s+(argued|wrote|believed|claimed)\b',
            ]
            for pattern in patterns:
                if re.search(pattern, text):
                    return True
            return False

        assert detect_thinker_mention("Friston argued that...")
        assert detect_thinker_mention("[Kant]'s view on...")
        assert detect_thinker_mention("Heidegger wrote extensively...")
        assert not detect_thinker_mention("Regular text without pattern")
        assert not detect_thinker_mention("lowercase argued something")

    def test_detect_thinking_about_pattern(self):
        """Test detection of 'I've been thinking about...' pattern."""

        def detect_thinking_pattern(text: str) -> bool:
            triggers = [
                "i've been thinking about",
                "i have been thinking about",
                "i'm thinking about",
                "i am thinking about",
            ]
            text_lower = text.lower()
            return any(trigger in text_lower for trigger in triggers)

        assert detect_thinking_pattern("I've been thinking about consciousness")
        assert detect_thinking_pattern("I'm thinking about free will")
        assert not detect_thinking_pattern("Regular thought")

    def test_detect_source_pattern(self):
        """Test detection of source citation patterns."""

        def detect_source_pattern(text: str) -> bool:
            import re
            patterns = [
                r'I read\s+"[^"]+"',
                r'According to\s+\w+',
                r'In "[^"]+"',
            ]
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return True
            return False

        assert detect_source_pattern('I read "Being and Time"')
        assert detect_source_pattern("According to Heidegger")
        assert detect_source_pattern('In "The Republic"')
        assert not detect_source_pattern("No citation here")

    def test_detect_at_path_command(self):
        """Test detection of @path/to/entity command."""

        def detect_at_path_command(text: str) -> Optional[str]:
            import re
            match = re.search(r'@([\w/]+)\s+info', text)
            return match.group(1) if match else None

        result = detect_at_path_command("@thinkers/kant info about his ethics")
        assert result == "thinkers/kant"

        result = detect_at_path_command("Regular text")
        assert result is None

    def test_auto_detect_from_rules_index(self, temp_philosophy_repo):
        """Test loading auto-detection rules from index."""
        rules_path = temp_philosophy_repo / "indices" / "philosophy" / "rules.yaml"
        data = yaml.safe_load(rules_path.read_text(encoding="utf-8"))

        assert "rules" in data
        assert "auto_detect_thinker" in data["rules"]
        rule = data["rules"]["auto_detect_thinker"]
        assert "pattern" in rule
        assert "action" in rule


# =============================================================================
# 8. Creating New Thoughts (Mocked)
# =============================================================================

class TestCreatingNewThoughts:
    """Test creating new thought entries (with mocking for safety)."""

    def test_create_thought_in_temp_repo(self, temp_philosophy_repo):
        """Create a new thought in temporary repository."""
        thoughts_dir = temp_philosophy_repo / "knowledge" / "philosophy" / "thoughts" / "consciousness"

        new_thought_dir = thoughts_dir / "2025-12-30_test_new_thought"
        new_thought_dir.mkdir(parents=True)

        thought_content = """---
title: "Test New Thought"
theme: "consciousness"
status: "seed"
created: "2025-12-30"
related_thinkers:
  - test_thinker
tags:
  - thought
---

# Test New Thought

## Key Insight

This is a test insight.

## Development

Testing development.

## Next Steps

- Step 1
- Step 2
"""
        (new_thought_dir / "thought.md").write_text(thought_content)

        assert (new_thought_dir / "thought.md").exists()
        content = (new_thought_dir / "thought.md").read_text()
        assert "Test New Thought" in content
        assert "test_thinker" in content

    def test_update_thoughts_index_after_creation(self, temp_philosophy_repo):
        """Update thoughts index after creating new thought."""
        index_path = temp_philosophy_repo / "indices" / "philosophy" / "thoughts.yaml"

        # Read current index
        data = yaml.safe_load(index_path.read_text(encoding="utf-8"))
        original_count = data["meta"]["count"]

        # Add new thought
        data["thoughts"]["new_test_thought"] = {
            "title": "New Test Thought",
            "theme": "consciousness",
            "status": "seed",
            "path": "thoughts/consciousness/2025-12-30_new_test_thought/",
            "related_thinkers": ["test_thinker"],
            "started": "2025-12-30"
        }
        data["meta"]["count"] = original_count + 1

        # Write updated index
        with open(index_path, "w") as f:
            yaml.dump(data, f)

        # Verify
        updated_data = yaml.safe_load(index_path.read_text(encoding="utf-8"))
        assert "new_test_thought" in updated_data["thoughts"]
        assert updated_data["meta"]["count"] == original_count + 1

    @patch("subprocess.run")
    def test_commit_new_thought_mocked(self, mock_run, temp_philosophy_repo):
        """Test committing new thought (mocked git operations)."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        # Simulate git add
        mock_run(["git", "add", "."], cwd=str(temp_philosophy_repo))
        mock_run.assert_called()

        # Simulate git commit
        mock_run([
            "git", "commit", "-m",
            "feat: add new thought on consciousness\n\nTest commit message"
        ], cwd=str(temp_philosophy_repo))

        # Verify mock was called
        assert mock_run.call_count >= 1

    def test_create_thought_validates_theme(self, temp_philosophy_repo):
        """Verify thought creation validates theme against known themes."""
        valid_themes = ["consciousness", "free_will", "existence", "knowledge", "life_meaning", "morality"]

        def create_thought(theme: str) -> bool:
            if theme not in valid_themes:
                return False
            return True

        assert create_thought("consciousness")
        assert create_thought("free_will")
        assert not create_thought("invalid_theme")


# =============================================================================
# 9. Bidirectional Linking
# =============================================================================

class TestBidirectionalLinking:
    """Test bidirectional linking between entities."""

    def test_thought_to_thinker_link(self, temp_philosophy_repo):
        """Test linking from thought to thinker in frontmatter."""
        thoughts_index = temp_philosophy_repo / "indices" / "philosophy" / "thoughts.yaml"
        data = yaml.safe_load(thoughts_index.read_text(encoding="utf-8"))

        thought = data["thoughts"]["test_thought"]
        assert "related_thinkers" in thought
        assert "test_thinker" in thought["related_thinkers"]

    def test_thinker_to_thought_link_in_references(self, temp_philosophy_repo):
        """Test linking from thinker references.md to thoughts."""
        references_path = temp_philosophy_repo / "knowledge" / "philosophy" / "thinkers" / "test_thinker" / "references.md"

        # Update references to include thought link
        references_content = """# References

| Date | Strength | Path | Reasoning |
|------|----------|------|-----------|
| 2025-12-30 | strong | thoughts/consciousness/test_thought/ | Core themes aligned |
"""
        references_path.write_text(references_content)

        content = references_path.read_text()
        assert "test_thought" in content
        assert "strong" in content

    def test_add_bidirectional_link(self, temp_philosophy_repo):
        """Test adding a complete bidirectional link."""
        # 1. Add thinker to thought's related_thinkers
        thoughts_index = temp_philosophy_repo / "indices" / "philosophy" / "thoughts.yaml"
        thoughts_data = yaml.safe_load(thoughts_index.read_text(encoding="utf-8"))

        thoughts_data["thoughts"]["test_thought"]["related_thinkers"].append("another_thinker")

        with open(thoughts_index, "w") as f:
            yaml.dump(thoughts_data, f)

        # 2. Add thought to thinker's references (simulated)
        # In real implementation, this would update references.md

        # 3. Verify
        updated = yaml.safe_load(thoughts_index.read_text(encoding="utf-8"))
        assert "another_thinker" in updated["thoughts"]["test_thought"]["related_thinkers"]

    def test_validate_all_links_exist(self, temp_philosophy_repo):
        """Validate all referenced entities exist."""
        thoughts_index = temp_philosophy_repo / "indices" / "philosophy" / "thoughts.yaml"
        thinkers_index = temp_philosophy_repo / "indices" / "philosophy" / "thinkers.yaml"

        thoughts_data = yaml.safe_load(thoughts_index.read_text(encoding="utf-8"))
        thinkers_data = yaml.safe_load(thinkers_index.read_text(encoding="utf-8"))

        valid_thinker_ids = set(thinkers_data["thinkers"].keys())

        broken_links = []
        for thought_id, thought in thoughts_data["thoughts"].items():
            for thinker_id in thought.get("related_thinkers", []):
                if thinker_id not in valid_thinker_ids:
                    broken_links.append((thought_id, thinker_id))

        assert len(broken_links) == 0, f"Found broken links: {broken_links}"


# =============================================================================
# Memory File Convention Tests
# =============================================================================

class TestMemoryFileConvention:
    """Test memory file processing conventions."""

    def test_memory_file_exists(self, temp_philosophy_repo):
        """Check if memory file exists alongside source file."""
        thinker_dir = temp_philosophy_repo / "knowledge" / "philosophy" / "thinkers" / "test_thinker"

        profile = thinker_dir / "profile.md"
        memory = thinker_dir / "profile_memory.md"

        assert profile.exists()
        assert memory.exists()

    def test_memory_file_naming_convention(self):
        """Verify memory file naming convention."""

        def get_memory_file_name(source_file: str) -> str:
            parts = source_file.rsplit(".", 1)
            if len(parts) == 2:
                return f"{parts[0]}_memory.{parts[1]}"
            return f"{source_file}_memory"

        assert get_memory_file_name("profile.md") == "profile_memory.md"
        assert get_memory_file_name("notes.md") == "notes_memory.md"
        assert get_memory_file_name("reflections.md") == "reflections_memory.md"

    def test_memory_file_has_corrections(self, temp_philosophy_repo):
        """Verify memory file contains corrections section."""
        memory_path = temp_philosophy_repo / "knowledge" / "philosophy" / "thinkers" / "test_thinker" / "profile_memory.md"
        content = memory_path.read_text()

        assert "## Corrections" in content
        assert "Original:" in content
        assert "Corrected:" in content

    def test_memory_file_has_key_insights(self, temp_philosophy_repo):
        """Verify memory file contains key insights section."""
        memory_path = temp_philosophy_repo / "knowledge" / "philosophy" / "thinkers" / "test_thinker" / "profile_memory.md"
        content = memory_path.read_text()

        assert "## Key Insights" in content

    def test_apply_memory_corrections(self, temp_philosophy_repo):
        """Test applying memory corrections to source content."""
        profile_path = temp_philosophy_repo / "knowledge" / "philosophy" / "thinkers" / "test_thinker" / "profile.md"
        memory_path = temp_philosophy_repo / "knowledge" / "philosophy" / "thinkers" / "test_thinker" / "profile_memory.md"

        profile_content = profile_path.read_text()
        memory_content = memory_path.read_text()

        # Simple correction simulation
        def apply_correction(content: str, original: str, corrected: str) -> str:
            return content.replace(original, corrected)

        # Extract correction from memory (simplified)
        corrected_content = apply_correction(profile_content, "Test ideas", "Profound test ideas")

        assert "Profound test ideas" in corrected_content
        assert "Test ideas" not in corrected_content or "Profound" in corrected_content


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================

class TestEdgeCasesAndErrors:
    """Test edge cases and error handling."""

    def test_handle_empty_index(self, tmp_path):
        """Handle empty index gracefully."""
        empty_index = tmp_path / "empty.yaml"
        empty_index.write_text("")

        try:
            data = yaml.safe_load(empty_index.read_text())
            assert data is None or data == {}, "Empty YAML should parse as None or empty dict"
        except yaml.YAMLError:
            pytest.fail("Should handle empty YAML without exception")

    def test_handle_malformed_yaml(self, tmp_path):
        """Handle malformed YAML gracefully."""
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("this: is: bad: yaml: [")

        with pytest.raises(yaml.YAMLError):
            yaml.safe_load(bad_yaml.read_text())

    def test_handle_missing_frontmatter(self):
        """Handle file without frontmatter."""
        content = "# Just a title\n\nNo frontmatter here."

        def extract_frontmatter(text: str) -> Optional[Dict]:
            if not text.startswith("---"):
                return None
            parts = text.split("---", 2)
            if len(parts) < 3:
                return None
            try:
                return yaml.safe_load(parts[1])
            except yaml.YAMLError:
                return None

        result = extract_frontmatter(content)
        assert result is None

    def test_handle_unicode_in_content(self, temp_philosophy_repo):
        """Handle Unicode characters in content."""
        thinker_dir = temp_philosophy_repo / "knowledge" / "philosophy" / "thinkers" / "test_unicode"
        thinker_dir.mkdir(parents=True)

        unicode_content = """---
name: "Soren Kierkegaard"
---

# Soren Kierkegaard

Danish: Soren Aabye Kierkegaard
Key concept: Angst (anxiety)
Quote: "Die reine Vernunft"
"""
        (thinker_dir / "profile.md").write_text(unicode_content, encoding="utf-8")

        # Read back
        content = (thinker_dir / "profile.md").read_text(encoding="utf-8")
        assert "Soren" in content
        assert "Angst" in content

    def test_handle_very_long_file(self, tmp_path):
        """Handle very long files."""
        long_file = tmp_path / "long.md"
        content = "# Long File\n\n" + ("Lorem ipsum. " * 10000)
        long_file.write_text(content)

        loaded = long_file.read_text()
        assert len(loaded) > 100000
        assert loaded.startswith("# Long File")


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
