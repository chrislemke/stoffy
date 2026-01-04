"""
Observation Categories

Provides classification of file changes into semantic categories
that help the decision engine determine appropriate actions.
"""

from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING
import fnmatch
import re

if TYPE_CHECKING:
    from consciousness.watcher import FileChange


class ObservationCategory(Enum):
    """Categories of file system observations."""

    INTAKE = "intake"           # New file to process (_input, _intake)
    KNOWLEDGE = "knowledge"     # Knowledge base change (knowledge/, indices/)
    CONFIG = "config"           # Configuration change (.claude/, *.yaml, *.json)
    CODE = "code"               # Code change (*.py, *.ts, *.js, etc.)
    TEMPLATE = "template"       # Template change (templates/)
    DOCUMENTATION = "docs"      # Documentation change (docs/, *.md)
    TEST = "test"               # Test file change (tests/, *_test.py)
    NOISE = "noise"             # Ignorable (logs, temp files, etc.)


@dataclass
class CategorizedChanges:
    """Container for categorized file changes."""

    intake: list["FileChange"] = field(default_factory=list)
    knowledge: list["FileChange"] = field(default_factory=list)
    config: list["FileChange"] = field(default_factory=list)
    code: list["FileChange"] = field(default_factory=list)
    template: list["FileChange"] = field(default_factory=list)
    documentation: list["FileChange"] = field(default_factory=list)
    test: list["FileChange"] = field(default_factory=list)
    noise: list["FileChange"] = field(default_factory=list)

    def __getitem__(self, category: ObservationCategory) -> list["FileChange"]:
        """Get changes by category."""
        return getattr(self, category.value)

    def add(self, category: ObservationCategory, change: "FileChange") -> None:
        """Add a change to a category."""
        getattr(self, category.value).append(change)

    def all_actionable(self) -> list["FileChange"]:
        """Get all non-noise changes."""
        return (
            self.intake +
            self.knowledge +
            self.config +
            self.code +
            self.template +
            self.documentation +
            self.test
        )

    def is_empty(self) -> bool:
        """Check if there are no actionable changes."""
        return len(self.all_actionable()) == 0

    def summary(self) -> dict[str, int]:
        """Get count summary by category."""
        return {
            "intake": len(self.intake),
            "knowledge": len(self.knowledge),
            "config": len(self.config),
            "code": len(self.code),
            "template": len(self.template),
            "documentation": len(self.documentation),
            "test": len(self.test),
            "noise": len(self.noise),
        }

    def primary_category(self) -> ObservationCategory | None:
        """Get the category with the most changes (excluding noise)."""
        categories = [
            (ObservationCategory.INTAKE, len(self.intake)),
            (ObservationCategory.KNOWLEDGE, len(self.knowledge)),
            (ObservationCategory.CONFIG, len(self.config)),
            (ObservationCategory.CODE, len(self.code)),
            (ObservationCategory.TEMPLATE, len(self.template)),
            (ObservationCategory.DOCUMENTATION, len(self.documentation)),
            (ObservationCategory.TEST, len(self.test)),
        ]

        # Sort by count descending
        categories.sort(key=lambda x: x[1], reverse=True)

        if categories[0][1] > 0:
            return categories[0][0]
        return None


# Category patterns - order matters (first match wins)
CATEGORY_PATTERNS: list[tuple[ObservationCategory, list[str]]] = [
    # Intake patterns (highest priority)
    (ObservationCategory.INTAKE, [
        "_input/*",
        "_input/**/*",
        "_intake/pending/*",
        "_intake/pending/**/*",
        "intake/*",
        "intake/**/*",
    ]),

    # Test patterns
    (ObservationCategory.TEST, [
        "tests/*",
        "tests/**/*",
        "test/*",
        "test/**/*",
        "*_test.py",
        "*_test.ts",
        "*_test.js",
        "test_*.py",
        "*.test.ts",
        "*.test.js",
        "*.spec.ts",
        "*.spec.js",
        "conftest.py",
        "pytest.ini",
        "jest.config.*",
    ]),

    # Configuration patterns
    (ObservationCategory.CONFIG, [
        ".claude/*",
        ".claude/**/*",
        "*.yaml",
        "*.yml",
        "*.json",
        "*.toml",
        ".env*",
        "pyproject.toml",
        "package.json",
        "tsconfig.json",
        "requirements.txt",
        "setup.py",
        "setup.cfg",
    ]),

    # Template patterns
    (ObservationCategory.TEMPLATE, [
        "templates/*",
        "templates/**/*",
    ]),

    # Documentation patterns
    (ObservationCategory.DOCUMENTATION, [
        "docs/*",
        "docs/**/*",
        "*.md",
        "*.rst",
        "*.txt",
        "README*",
        "CHANGELOG*",
        "LICENSE*",
    ]),

    # Knowledge patterns
    (ObservationCategory.KNOWLEDGE, [
        "knowledge/*",
        "knowledge/**/*",
        "indices/*",
        "indices/**/*",
    ]),

    # Code patterns (catch-all for source files)
    (ObservationCategory.CODE, [
        "*.py",
        "*.ts",
        "*.tsx",
        "*.js",
        "*.jsx",
        "*.rs",
        "*.go",
        "*.java",
        "*.c",
        "*.cpp",
        "*.h",
        "*.hpp",
        "*.rb",
        "*.php",
        "*.swift",
        "*.kt",
        "*.scala",
        "*.vue",
        "*.svelte",
        "src/*",
        "src/**/*",
        "lib/*",
        "lib/**/*",
    ]),

    # Noise patterns (lowest priority - things to ignore)
    (ObservationCategory.NOISE, [
        "*.log",
        "*.tmp",
        "*.temp",
        "*.bak",
        "*.swp",
        "*.swo",
        "*~",
        ".DS_Store",
        "__pycache__/*",
        "__pycache__/**/*",
        "*.pyc",
        "node_modules/*",
        "node_modules/**/*",
        ".git/*",
        ".git/**/*",
        "*.db",
        "*.db-*",
        "logs/*",
        "logs/**/*",
        "_intake/processed/*",
        "_intake/processed/**/*",
    ]),
]


def categorize_single_change(change: "FileChange") -> ObservationCategory:
    """
    Categorize a single file change.

    Args:
        change: The file change to categorize

    Returns:
        The appropriate ObservationCategory
    """
    rel_path = change.relative_path

    # Check each category's patterns in order
    for category, patterns in CATEGORY_PATTERNS:
        for pattern in patterns:
            if fnmatch.fnmatch(rel_path, pattern):
                return category
            # Also check just the filename for extension patterns
            if fnmatch.fnmatch(Path(rel_path).name, pattern):
                return category

    # Default to noise if no pattern matches
    return ObservationCategory.NOISE


def categorize_changes(changes: list["FileChange"]) -> CategorizedChanges:
    """
    Categorize a list of file changes.

    Args:
        changes: List of file changes to categorize

    Returns:
        CategorizedChanges container with changes grouped by category
    """
    result = CategorizedChanges()

    for change in changes:
        category = categorize_single_change(change)
        result.add(category, change)

    return result


def get_category_description(category: ObservationCategory) -> str:
    """Get a human-readable description of a category."""
    descriptions = {
        ObservationCategory.INTAKE: "New content to be processed and integrated",
        ObservationCategory.KNOWLEDGE: "Changes to the knowledge base or indices",
        ObservationCategory.CONFIG: "Configuration or settings modifications",
        ObservationCategory.CODE: "Source code changes",
        ObservationCategory.TEMPLATE: "Template file modifications",
        ObservationCategory.DOCUMENTATION: "Documentation updates",
        ObservationCategory.TEST: "Test file changes",
        ObservationCategory.NOISE: "Ignorable system or temporary files",
    }
    return descriptions.get(category, "Unknown category")


def format_categorized_for_llm(categorized: CategorizedChanges) -> str:
    """
    Format categorized changes for LLM consumption.

    Args:
        categorized: CategorizedChanges to format

    Returns:
        Formatted string suitable for LLM processing
    """
    lines = ["=== CATEGORIZED OBSERVATIONS ===", ""]

    summary = categorized.summary()
    total = sum(summary.values())
    actionable = sum(v for k, v in summary.items() if k != "noise")

    lines.append(f"Total changes: {total}")
    lines.append(f"Actionable: {actionable}")
    lines.append("")

    # List each category with changes
    for category in ObservationCategory:
        changes = categorized[category]
        if changes:
            lines.append(f"[{category.value.upper()}] ({len(changes)} files)")
            lines.append(f"  Description: {get_category_description(category)}")
            for change in changes[:10]:  # Limit to first 10
                symbol = {"created": "+", "modified": "~", "deleted": "-"}.get(
                    change.change_type, "?"
                )
                lines.append(f"  {symbol} {change.relative_path}")
            if len(changes) > 10:
                lines.append(f"  ... and {len(changes) - 10} more")
            lines.append("")

    lines.append("=== END CATEGORIZED OBSERVATIONS ===")
    return "\n".join(lines)
