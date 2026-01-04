"""
Pytest Configuration for Consciousness Tests

Provides:
- Common fixtures
- Custom markers
- Path setup for imports
"""

import sys
from pathlib import Path

import pytest

# Add consciousness module path
CONSCIOUSNESS_PATH = Path(__file__).parent.parent
sys.path.insert(0, str(CONSCIOUSNESS_PATH.parent))


def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (require actual file I/O, deselect with '-m \"not slow\"')",
    )
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (require multiple components)",
    )
    config.addinivalue_line(
        "markers",
        "requires_lm_studio: marks tests that require LM Studio to be running",
    )
    config.addinivalue_line(
        "markers",
        "requires_claude: marks tests that require Claude CLI or API",
    )


@pytest.fixture
def stoffy_root():
    """Provide the Stoffy repository root path."""
    return Path("/Users/chris/Developer/stoffy")


@pytest.fixture
def consciousness_path():
    """Provide the consciousness module path."""
    return CONSCIOUSNESS_PATH


@pytest.fixture
def sample_file_change():
    """Provide a sample file change for testing."""
    from consciousness.watcher import FileChange
    import time

    return FileChange(
        path="/Users/chris/Developer/stoffy/test/file.md",
        change_type="modified",
        timestamp=time.time(),
        relative_path="test/file.md",
    )


@pytest.fixture
def sample_decision():
    """Provide a sample decision for testing."""
    from consciousness.thinker import (
        Action,
        ActionType,
        Decision,
        DecisionType,
        Priority,
    )

    return Decision(
        reasoning="Test reasoning for action",
        decision_type=DecisionType.ACT,
        confidence=0.85,
        action=Action(
            type=ActionType.CLAUDE_CODE,
            prompt="Execute test task",
            priority=Priority.MEDIUM,
        ),
    )


@pytest.fixture
def consciousness_config():
    """Provide a test consciousness configuration."""
    from consciousness.config import ConsciousnessConfig

    return ConsciousnessConfig()


@pytest.fixture
def temp_watch_dir(tmp_path):
    """Provide a temporary directory for file watching tests."""
    watch_dir = tmp_path / "watch_test"
    watch_dir.mkdir()
    return watch_dir


@pytest.fixture
def mock_lm_response():
    """Provide a mock LM Studio response generator."""
    import json

    def create_response(
        decision: str = "wait",
        confidence: float = 0.5,
        reasoning: str = "Test reasoning",
        action: dict = None,
    ):
        return json.dumps({
            "reasoning": reasoning,
            "decision": decision,
            "action": action,
            "confidence": confidence,
        })

    return create_response
