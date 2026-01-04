"""
Learning Module for Consciousness Daemon

This module provides outcome tracking, pattern learning, and advanced cognitive
capabilities to improve decision-making over time based on historical data.

Components:
- OutcomeTracker: Records and analyzes action outcomes
- PatternLearner: Extracts and applies learned patterns
- LearningIntegration: Integrates learning into the decision engine
- Dreamer: Processes experiences during idle periods for consolidation
- SemanticMemoryWriter: Writes experiences to long-term semantic memory
- TemplateGenerator: Creates reusable templates from successful patterns
"""

from pathlib import Path
from typing import Optional

# Core tracking and patterns
from .tracker import (
    OutcomeTracker,
    Outcome,
    OutcomeType,
)
from .patterns import (
    PatternLearner,
    Pattern,
    PatternType,
    Suggestion,
)

# Integration layer
from .integration import (
    LearningIntegration,
    LearningConfig,
    create_learning_integration,
)

# Advanced learning modules (optional - may not be present in all installations)
try:
    from .dreamer import (
        Dreamer,
        DreamerConfig,
        DreamResult,
        DreamPhase,
        LLMTier,
        create_dreamer,
    )
    _HAS_DREAMER = True
except ImportError:
    _HAS_DREAMER = False
    Dreamer = None  # type: ignore
    DreamerConfig = None  # type: ignore
    DreamResult = None  # type: ignore
    DreamPhase = None  # type: ignore
    LLMTier = None  # type: ignore
    create_dreamer = None  # type: ignore

try:
    from .semantic import (
        SemanticMemoryWriter,
        SemanticMemoryConfig,
        SemanticRule,
        ArchitectureInsight,
        create_semantic_memory_writer,
    )
    _HAS_SEMANTIC = True
except ImportError:
    _HAS_SEMANTIC = False
    SemanticMemoryWriter = None  # type: ignore
    SemanticMemoryConfig = None  # type: ignore
    SemanticRule = None  # type: ignore
    ArchitectureInsight = None  # type: ignore
    create_semantic_memory_writer = None  # type: ignore

try:
    from .templates import (
        TemplateGenerator,
        TemplateGeneratorConfig,
        Template,
    )
    _HAS_TEMPLATES = True
except ImportError:
    _HAS_TEMPLATES = False
    TemplateGenerator = None  # type: ignore
    TemplateGeneratorConfig = None  # type: ignore
    Template = None  # type: ignore


__all__ = [
    # Core tracking
    "OutcomeTracker",
    "Outcome",
    "OutcomeType",
    # Pattern learning
    "PatternLearner",
    "Pattern",
    "PatternType",
    "Suggestion",
    # Integration
    "LearningIntegration",
    "LearningConfig",
    "create_learning_integration",
    # Dreamer (Dream Cycle)
    "Dreamer",
    "DreamerConfig",
    "DreamResult",
    "DreamPhase",
    "LLMTier",
    "create_dreamer",
    # Semantic Memory
    "SemanticMemoryWriter",
    "SemanticMemoryConfig",
    "SemanticRule",
    "ArchitectureInsight",
    "create_semantic_memory_writer",
    # Template Generator
    "TemplateGenerator",
    "TemplateGeneratorConfig",
    "Template",
    # Feature flags
    "has_dreamer",
    "has_semantic_memory",
    "has_templates",
    # Factory functions
    "create_full_learning_stack",
]


def has_dreamer() -> bool:
    """Check if the Dreamer module is available."""
    return _HAS_DREAMER


def has_semantic_memory() -> bool:
    """Check if the SemanticMemoryWriter module is available."""
    return _HAS_SEMANTIC


def has_templates() -> bool:
    """Check if the TemplateGenerator module is available."""
    return _HAS_TEMPLATES


def create_full_learning_stack(
    db_path: str | Path,
    learning_config: Optional[LearningConfig] = None,
    dreamer_config: Optional["DreamerConfig"] = None,
    semantic_config: Optional["SemanticMemoryConfig"] = None,
    template_config: Optional["TemplateGeneratorConfig"] = None,
) -> dict:
    """
    Create a complete learning stack with all available components.

    This factory function creates and configures all learning components
    that are available in the current installation.

    Args:
        db_path: Path to the SQLite database for state storage
        learning_config: Optional configuration for LearningIntegration
        dreamer_config: Optional configuration for Dreamer
        semantic_config: Optional configuration for SemanticMemoryWriter
        template_config: Optional configuration for TemplateGenerator

    Returns:
        Dictionary containing initialized components:
        - 'integration': LearningIntegration instance
        - 'dreamer': Dreamer instance (if available)
        - 'semantic': SemanticMemoryWriter instance (if available)
        - 'templates': TemplateGenerator instance (if available)
        - 'available': List of available component names
    """
    db_path = Path(db_path)
    components: dict = {
        "available": ["integration"],
    }

    # Always create the core integration
    components["integration"] = create_learning_integration(
        state_db_path=db_path,
        config=learning_config,
    )

    # Derive project root from db_path
    project_root = db_path.parent.parent if db_path.parent.name == "state" else db_path.parent

    # Create optional advanced components if available
    if _HAS_DREAMER and Dreamer is not None:
        components["dreamer"] = Dreamer(
            db_path=db_path,
            project_root=project_root,
            config=dreamer_config,
        )
        components["available"].append("dreamer")

    if _HAS_SEMANTIC and SemanticMemoryWriter is not None:
        components["semantic"] = SemanticMemoryWriter(
            base_path=project_root,
            config=semantic_config,
        )
        components["available"].append("semantic")

    if _HAS_TEMPLATES and TemplateGenerator is not None:
        components["templates"] = TemplateGenerator(
            config=template_config,
            base_path=project_root,
        )
        components["available"].append("templates")

    return components
