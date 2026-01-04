"""
Template Generator - Creates reusable templates from successful patterns.

When a specific fix or action pattern works consistently (5+ times with 85%+ success),
this module generates reusable YAML templates that can be used by the swarm.

Templates are stored in `.hive-mind/templates/` and can be used as:
- Few-shot examples for the decision engine
- Automated responses to known patterns
- Knowledge sharing between swarm agents
"""

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

from .patterns import Pattern, PatternType
from .tracker import Outcome, OutcomeType

logger = logging.getLogger(__name__)


@dataclass
class TemplateGeneratorConfig:
    """Configuration for the template generator."""

    templates_dir: Path = field(default_factory=lambda: Path(".hive-mind/templates"))
    min_successes_for_template: int = 5
    min_success_rate: float = 0.85
    template_format: str = "yaml"  # "yaml" or "json"
    max_templates: int = 100
    auto_version_increment: bool = True
    include_examples: bool = True
    max_examples_per_template: int = 3

    def to_dict(self) -> dict[str, Any]:
        return {
            "templates_dir": str(self.templates_dir),
            "min_successes_for_template": self.min_successes_for_template,
            "min_success_rate": self.min_success_rate,
            "template_format": self.template_format,
            "max_templates": self.max_templates,
            "auto_version_increment": self.auto_version_increment,
            "include_examples": self.include_examples,
            "max_examples_per_template": self.max_examples_per_template,
        }


@dataclass
class Template:
    """Represents a reusable action template."""

    name: str
    version: str = "1.0.0"
    created: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "learned_from_outcomes"

    # Trigger configuration
    trigger_observation_pattern: str = ""
    trigger_observation_hash: str = ""
    trigger_file_patterns: list[str] = field(default_factory=list)
    trigger_action_words: list[str] = field(default_factory=list)

    # Action configuration
    action_type: str = ""
    action_prompt: str = ""
    action_priority: str = "medium"
    action_timeout: int = 300
    action_parameters: dict[str, Any] = field(default_factory=dict)

    # Statistics
    success_rate: float = 0.0
    occurrences: int = 0
    last_used: Optional[datetime] = None
    total_execution_time: float = 0.0

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)
    examples: list[dict[str, Any]] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert template to dictionary for serialization."""
        return {
            "name": self.name,
            "version": self.version,
            "created": self.created.isoformat(),
            "updated": self.updated.isoformat(),
            "source": self.source,
            "trigger": {
                "observation_pattern": self.trigger_observation_pattern,
                "observation_hash": self.trigger_observation_hash,
                "file_patterns": self.trigger_file_patterns,
                "action_words": self.trigger_action_words,
            },
            "action": {
                "type": self.action_type,
                "prompt": self.action_prompt,
                "priority": self.action_priority,
                "timeout": self.action_timeout,
                "parameters": self.action_parameters,
            },
            "statistics": {
                "success_rate": round(self.success_rate, 4),
                "occurrences": self.occurrences,
                "last_used": self.last_used.isoformat() if self.last_used else None,
                "avg_execution_time": (
                    round(self.total_execution_time / max(self.occurrences, 1), 2)
                ),
            },
            "metadata": {
                **self.metadata,
                "learned_from": "observation_action_pattern",
                "confidence": round(
                    self.success_rate * (1 - 1 / (self.occurrences + 1)), 4
                ),
            },
            "examples": self.examples[:3] if self.examples else [],
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Template":
        """Create template from dictionary."""
        trigger = data.get("trigger", {})
        action = data.get("action", {})
        statistics = data.get("statistics", {})
        metadata = data.get("metadata", {})

        return cls(
            name=data.get("name", ""),
            version=data.get("version", "1.0.0"),
            created=_parse_datetime(data.get("created")),
            updated=_parse_datetime(data.get("updated")),
            source=data.get("source", "learned_from_outcomes"),
            trigger_observation_pattern=trigger.get("observation_pattern", ""),
            trigger_observation_hash=trigger.get("observation_hash", ""),
            trigger_file_patterns=trigger.get("file_patterns", []),
            trigger_action_words=trigger.get("action_words", []),
            action_type=action.get("type", ""),
            action_prompt=action.get("prompt", ""),
            action_priority=action.get("priority", "medium"),
            action_timeout=action.get("timeout", 300),
            action_parameters=action.get("parameters", {}),
            success_rate=statistics.get("success_rate", 0.0),
            occurrences=statistics.get("occurrences", 0),
            last_used=_parse_datetime(statistics.get("last_used")),
            total_execution_time=(
                statistics.get("avg_execution_time", 0.0)
                * statistics.get("occurrences", 1)
            ),
            metadata={
                k: v
                for k, v in metadata.items()
                if k not in ("learned_from", "confidence")
            },
            examples=data.get("examples", []),
            tags=data.get("tags", []),
        )

    @property
    def filename(self) -> str:
        """Generate filename for this template."""
        # Sanitize name for filesystem
        safe_name = re.sub(r"[^\w\-]", "_", self.name.lower())
        return f"{safe_name}.yaml"

    @property
    def confidence(self) -> float:
        """Calculate confidence score for this template."""
        if self.occurrences == 0:
            return 0.0
        return min(0.95, self.success_rate * (1 - 1 / (self.occurrences + 1)))


def _parse_datetime(value: Any) -> datetime:
    """Parse datetime from string or return current time."""
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return datetime.now(timezone.utc)


def _generate_template_name(pattern: Pattern) -> str:
    """Generate a semantic name for a template based on the pattern."""
    # Extract key terms from trigger description
    description = pattern.trigger_description.lower()

    # Common pattern categories
    categories = [
        ("test", ["test", "spec", "unittest", "pytest"]),
        ("doc", ["doc", "readme", "documentation", "comment"]),
        ("fix", ["fix", "bug", "error", "issue"]),
        ("create", ["create", "new", "add", "init"]),
        ("update", ["update", "modify", "change", "edit"]),
        ("delete", ["delete", "remove", "clean"]),
        ("refactor", ["refactor", "restructure", "reorganize"]),
        ("config", ["config", "settings", "env", "yaml", "json"]),
    ]

    detected_category = "action"
    for category, keywords in categories:
        if any(kw in description for kw in keywords):
            detected_category = category
            break

    # Extract file type hints
    file_types = re.findall(r"\.([a-zA-Z0-9]+)", description)
    file_hint = file_types[0] if file_types else ""

    # Build name
    action_type_short = pattern.action_type.replace("_", "-")

    if file_hint:
        name = f"{detected_category}_{file_hint}_{action_type_short}"
    else:
        name = f"{detected_category}_{action_type_short}"

    # Add hash suffix for uniqueness
    name += f"_{pattern.trigger_hash[:6]}"

    return name


def _extract_file_patterns(observation: str) -> list[str]:
    """Extract file patterns from an observation string."""
    patterns = []

    # Find file extensions mentioned
    extensions = re.findall(r"\*?\.[a-zA-Z0-9]+", observation)
    patterns.extend(set(extensions))

    # Find directory patterns
    dir_matches = re.findall(r"([\w\-]+/)", observation)
    patterns.extend(f"{d}*" for d in set(dir_matches))

    return patterns[:5]  # Limit to 5 patterns


def _extract_action_words(observation: str) -> list[str]:
    """Extract action words from an observation string."""
    action_words = [
        "created",
        "modified",
        "deleted",
        "changed",
        "added",
        "removed",
        "updated",
        "new",
        "error",
        "failed",
        "success",
        "missing",
        "invalid",
        "deprecated",
    ]

    found = []
    obs_lower = observation.lower()
    for word in action_words:
        if word in obs_lower:
            found.append(word)

    return found


class TemplateGenerator:
    """
    Generates reusable templates from successful patterns.

    When patterns consistently succeed, this class creates YAML template files
    that can be used by the swarm for:
    - Automated responses to known situations
    - Few-shot learning examples
    - Knowledge transfer between agents
    """

    def __init__(
        self,
        config: Optional[TemplateGeneratorConfig] = None,
        base_path: Optional[Path] = None,
    ):
        """
        Initialize the template generator.

        Args:
            config: Configuration for template generation
            base_path: Base path for the project (templates_dir is relative to this)
        """
        self.config = config or TemplateGeneratorConfig()
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self._templates_path = self.base_path / self.config.templates_dir

    @property
    def templates_path(self) -> Path:
        """Get the absolute path to templates directory."""
        return self._templates_path

    async def initialize(self) -> None:
        """Ensure templates directory exists with proper structure."""
        self._templates_path.mkdir(parents=True, exist_ok=True)

        # Create subdirectories for organization
        (self._templates_path / "learned").mkdir(exist_ok=True)
        (self._templates_path / "custom").mkdir(exist_ok=True)
        (self._templates_path / "archived").mkdir(exist_ok=True)

        # Create index file if it doesn't exist
        index_path = self._templates_path / "index.yaml"
        if not index_path.exists():
            index_data = {
                "version": "1.0.0",
                "created": datetime.now(timezone.utc).isoformat(),
                "updated": datetime.now(timezone.utc).isoformat(),
                "templates": [],
                "categories": {
                    "learned": "Auto-generated from successful patterns",
                    "custom": "Manually created templates",
                    "archived": "Deprecated or replaced templates",
                },
            }
            with index_path.open("w") as f:
                yaml.dump(index_data, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Template generator initialized at {self._templates_path}")

    async def should_create_template(self, pattern: Pattern) -> bool:
        """
        Check if a pattern qualifies for template creation.

        A pattern qualifies if:
        - It has occurred at least min_successes_for_template times
        - Its success rate is at least min_success_rate
        - A template for this pattern doesn't already exist

        Args:
            pattern: The pattern to evaluate

        Returns:
            True if a template should be created
        """
        # Check minimum occurrences
        if pattern.occurrences < self.config.min_successes_for_template:
            logger.debug(
                f"Pattern {pattern.trigger_hash} has {pattern.occurrences} occurrences, "
                f"needs {self.config.min_successes_for_template}"
            )
            return False

        # Check minimum success rate
        if pattern.success_rate < self.config.min_success_rate:
            logger.debug(
                f"Pattern {pattern.trigger_hash} has {pattern.success_rate:.0%} success rate, "
                f"needs {self.config.min_success_rate:.0%}"
            )
            return False

        # Check if template already exists
        template_name = _generate_template_name(pattern)
        existing = await self._find_existing_template(pattern.trigger_hash)
        if existing:
            logger.debug(f"Template already exists for pattern {pattern.trigger_hash}")
            return False

        logger.info(
            f"Pattern qualifies for template: {template_name} "
            f"(occurrences={pattern.occurrences}, success_rate={pattern.success_rate:.0%})"
        )
        return True

    async def _find_existing_template(self, trigger_hash: str) -> Optional[Path]:
        """Find an existing template for a trigger hash."""
        learned_dir = self._templates_path / "learned"
        if not learned_dir.exists():
            return None

        for template_file in learned_dir.glob("*.yaml"):
            try:
                with template_file.open() as f:
                    data = yaml.safe_load(f)
                if data and data.get("trigger", {}).get("observation_hash") == trigger_hash:
                    return template_file
            except Exception:
                continue

        return None

    async def create_template(
        self,
        pattern: Pattern,
        outcomes: list[Outcome],
    ) -> Path:
        """
        Generate a template file from a pattern and its outcomes.

        Args:
            pattern: The learned pattern to create a template from
            outcomes: List of outcomes that informed this pattern

        Returns:
            Path to the created template file
        """
        # Ensure directory exists
        await self.initialize()

        # Generate template
        template = Template(
            name=_generate_template_name(pattern),
            version="1.0.0",
            created=datetime.now(timezone.utc),
            updated=datetime.now(timezone.utc),
            source="learned_from_outcomes",
            trigger_observation_pattern=pattern.trigger_description,
            trigger_observation_hash=pattern.trigger_hash,
            trigger_file_patterns=_extract_file_patterns(pattern.trigger_description),
            trigger_action_words=_extract_action_words(pattern.trigger_description),
            action_type=pattern.action_type,
            action_prompt=pattern.action_template,
            action_priority=self._determine_priority(pattern),
            action_timeout=300,
            action_parameters={},
            success_rate=pattern.success_rate,
            occurrences=pattern.occurrences,
            last_used=pattern.last_updated,
            total_execution_time=sum(o.execution_time for o in outcomes if o.success),
            metadata={
                "pattern_id": pattern.id,
                "pattern_type": pattern.pattern_type.value,
            },
            examples=self._build_examples(outcomes) if self.config.include_examples else [],
            tags=self._generate_tags(pattern),
        )

        # Write template file
        template_path = self._templates_path / "learned" / template.filename
        template_data = template.to_dict()

        if self.config.template_format == "yaml":
            with template_path.open("w") as f:
                yaml.dump(template_data, f, default_flow_style=False, sort_keys=False)
        else:
            template_path = template_path.with_suffix(".json")
            with template_path.open("w") as f:
                json.dump(template_data, f, indent=2)

        # Update index
        await self._update_index(template)

        logger.info(f"Created template: {template_path}")
        return template_path

    def _determine_priority(self, pattern: Pattern) -> str:
        """Determine action priority based on pattern characteristics."""
        if pattern.success_rate >= 0.95 and pattern.occurrences >= 10:
            return "high"
        elif pattern.success_rate >= 0.90:
            return "medium"
        else:
            return "low"

    def _build_examples(self, outcomes: list[Outcome]) -> list[dict[str, Any]]:
        """Build example entries from successful outcomes."""
        successful = [o for o in outcomes if o.success]
        successful.sort(key=lambda o: o.timestamp, reverse=True)

        examples = []
        for outcome in successful[: self.config.max_examples_per_template]:
            examples.append(
                {
                    "observation": outcome.observation[:200],
                    "action": outcome.action_details[:300],
                    "result": outcome.result_output[:200] if outcome.result_output else "",
                    "execution_time": round(outcome.execution_time, 2),
                    "timestamp": outcome.timestamp.isoformat(),
                }
            )

        return examples

    def _generate_tags(self, pattern: Pattern) -> list[str]:
        """Generate tags for a template based on pattern."""
        tags = [pattern.action_type, pattern.pattern_type.value]

        # Add file type tags
        file_types = re.findall(r"\.([a-zA-Z0-9]+)", pattern.trigger_description)
        tags.extend(set(file_types))

        # Add action word tags
        tags.extend(_extract_action_words(pattern.trigger_description))

        # Add reliability tag
        if pattern.success_rate >= 0.95:
            tags.append("highly-reliable")
        elif pattern.success_rate >= 0.85:
            tags.append("reliable")

        return list(set(tags))[:10]  # Limit to 10 unique tags

    async def _update_index(self, template: Template) -> None:
        """Update the templates index file."""
        index_path = self._templates_path / "index.yaml"

        if index_path.exists():
            with index_path.open() as f:
                index_data = yaml.safe_load(f) or {}
        else:
            index_data = {"version": "1.0.0", "templates": []}

        # Update or add template entry
        templates = index_data.get("templates", [])
        entry = {
            "name": template.name,
            "path": f"learned/{template.filename}",
            "trigger_hash": template.trigger_observation_hash,
            "action_type": template.action_type,
            "success_rate": round(template.success_rate, 4),
            "occurrences": template.occurrences,
            "created": template.created.isoformat(),
        }

        # Check if entry exists
        existing_idx = None
        for i, t in enumerate(templates):
            if t.get("trigger_hash") == template.trigger_observation_hash:
                existing_idx = i
                break

        if existing_idx is not None:
            templates[existing_idx] = entry
        else:
            templates.append(entry)

        index_data["templates"] = templates
        index_data["updated"] = datetime.now(timezone.utc).isoformat()

        with index_path.open("w") as f:
            yaml.dump(index_data, f, default_flow_style=False, sort_keys=False)

    async def list_templates(
        self,
        category: Optional[str] = None,
        min_success_rate: float = 0.0,
        tags: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        """
        List existing templates with optional filtering.

        Args:
            category: Filter by category ("learned", "custom", "archived")
            min_success_rate: Filter by minimum success rate
            tags: Filter by tags (templates must have all specified tags)

        Returns:
            List of template summary dictionaries
        """
        templates = []

        # Determine directories to search
        if category:
            dirs = [self._templates_path / category]
        else:
            dirs = [
                self._templates_path / "learned",
                self._templates_path / "custom",
            ]

        for dir_path in dirs:
            if not dir_path.exists():
                continue

            for template_file in dir_path.glob("*.yaml"):
                if template_file.name == "index.yaml":
                    continue

                try:
                    with template_file.open() as f:
                        data = yaml.safe_load(f)

                    if not data:
                        continue

                    # Apply filters
                    stats = data.get("statistics", {})
                    if stats.get("success_rate", 0) < min_success_rate:
                        continue

                    if tags:
                        template_tags = data.get("tags", [])
                        if not all(t in template_tags for t in tags):
                            continue

                    templates.append(
                        {
                            "name": data.get("name"),
                            "path": str(template_file.relative_to(self._templates_path)),
                            "action_type": data.get("action", {}).get("type"),
                            "success_rate": stats.get("success_rate", 0),
                            "occurrences": stats.get("occurrences", 0),
                            "tags": data.get("tags", []),
                            "category": dir_path.name,
                        }
                    )
                except Exception as e:
                    logger.warning(f"Error reading template {template_file}: {e}")
                    continue

        # Sort by success rate descending
        templates.sort(key=lambda t: t.get("success_rate", 0), reverse=True)
        return templates

    async def get_template(self, name: str) -> Optional[dict[str, Any]]:
        """
        Load a template by name.

        Args:
            name: Template name (with or without extension)

        Returns:
            Template data dictionary or None if not found
        """
        # Normalize name
        if not name.endswith(".yaml") and not name.endswith(".json"):
            name = f"{name}.yaml"

        # Search in all directories
        for category in ["learned", "custom"]:
            template_path = self._templates_path / category / name
            if template_path.exists():
                try:
                    with template_path.open() as f:
                        if template_path.suffix == ".yaml":
                            return yaml.safe_load(f)
                        else:
                            return json.load(f)
                except Exception as e:
                    logger.error(f"Error loading template {name}: {e}")
                    return None

        logger.warning(f"Template not found: {name}")
        return None

    async def get_template_by_hash(self, trigger_hash: str) -> Optional[dict[str, Any]]:
        """
        Load a template by its trigger hash.

        Args:
            trigger_hash: The observation hash that triggers this template

        Returns:
            Template data dictionary or None if not found
        """
        template_path = await self._find_existing_template(trigger_hash)
        if template_path:
            try:
                with template_path.open() as f:
                    return yaml.safe_load(f)
            except Exception as e:
                logger.error(f"Error loading template: {e}")

        return None

    async def update_template(
        self,
        name: str,
        updates: dict[str, Any],
    ) -> bool:
        """
        Update template metadata or statistics.

        Args:
            name: Template name
            updates: Dictionary of updates to apply

        Returns:
            True if update was successful
        """
        # Find the template
        template_data = await self.get_template(name)
        if not template_data:
            return False

        # Find the file path
        if not name.endswith(".yaml"):
            name = f"{name}.yaml"

        template_path = None
        for category in ["learned", "custom"]:
            path = self._templates_path / category / name
            if path.exists():
                template_path = path
                break

        if not template_path:
            return False

        # Apply updates
        for key, value in updates.items():
            if key in template_data:
                if isinstance(template_data[key], dict) and isinstance(value, dict):
                    template_data[key].update(value)
                else:
                    template_data[key] = value

        # Update timestamp
        template_data["updated"] = datetime.now(timezone.utc).isoformat()

        # Auto-increment version if enabled
        if self.config.auto_version_increment:
            version = template_data.get("version", "1.0.0")
            parts = version.split(".")
            if len(parts) == 3:
                parts[2] = str(int(parts[2]) + 1)
                template_data["version"] = ".".join(parts)

        # Write back
        try:
            with template_path.open("w") as f:
                yaml.dump(template_data, f, default_flow_style=False, sort_keys=False)
            logger.info(f"Updated template: {name}")
            return True
        except Exception as e:
            logger.error(f"Error updating template {name}: {e}")
            return False

    async def record_template_usage(
        self,
        name: str,
        success: bool,
        execution_time: float = 0.0,
    ) -> bool:
        """
        Record that a template was used and update its statistics.

        Args:
            name: Template name
            success: Whether the usage was successful
            execution_time: How long the action took

        Returns:
            True if recording was successful
        """
        template_data = await self.get_template(name)
        if not template_data:
            return False

        stats = template_data.get("statistics", {})

        # Update statistics
        occurrences = stats.get("occurrences", 0) + 1
        successes = int(stats.get("success_rate", 0) * stats.get("occurrences", 0))
        if success:
            successes += 1

        new_success_rate = successes / occurrences if occurrences > 0 else 0

        updates = {
            "statistics": {
                "success_rate": round(new_success_rate, 4),
                "occurrences": occurrences,
                "last_used": datetime.now(timezone.utc).isoformat(),
                "avg_execution_time": round(
                    (
                        stats.get("avg_execution_time", 0) * (occurrences - 1)
                        + execution_time
                    )
                    / occurrences,
                    2,
                ),
            }
        }

        return await self.update_template(name, updates)

    async def archive_template(self, name: str, reason: str = "") -> bool:
        """
        Move a template to the archived directory.

        Args:
            name: Template name
            reason: Reason for archiving

        Returns:
            True if archiving was successful
        """
        if not name.endswith(".yaml"):
            name = f"{name}.yaml"

        # Find source path
        source_path = None
        for category in ["learned", "custom"]:
            path = self._templates_path / category / name
            if path.exists():
                source_path = path
                break

        if not source_path:
            logger.warning(f"Template not found for archiving: {name}")
            return False

        # Ensure archive directory exists
        archive_dir = self._templates_path / "archived"
        archive_dir.mkdir(exist_ok=True)

        # Load, update, and move
        try:
            with source_path.open() as f:
                data = yaml.safe_load(f)

            data["archived"] = datetime.now(timezone.utc).isoformat()
            data["archive_reason"] = reason

            dest_path = archive_dir / name
            with dest_path.open("w") as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)

            source_path.unlink()

            # Update index
            await self._remove_from_index(name)

            logger.info(f"Archived template: {name}")
            return True
        except Exception as e:
            logger.error(f"Error archiving template {name}: {e}")
            return False

    async def _remove_from_index(self, template_name: str) -> None:
        """Remove a template from the index."""
        index_path = self._templates_path / "index.yaml"

        if not index_path.exists():
            return

        try:
            with index_path.open() as f:
                index_data = yaml.safe_load(f) or {}

            templates = index_data.get("templates", [])
            index_data["templates"] = [
                t for t in templates if not t.get("path", "").endswith(template_name)
            ]
            index_data["updated"] = datetime.now(timezone.utc).isoformat()

            with index_path.open("w") as f:
                yaml.dump(index_data, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            logger.warning(f"Error updating index: {e}")

    async def get_statistics(self) -> dict[str, Any]:
        """Get overall template statistics."""
        templates = await self.list_templates()

        if not templates:
            return {
                "total_templates": 0,
                "by_category": {},
                "avg_success_rate": 0,
                "total_occurrences": 0,
                "by_action_type": {},
            }

        by_category: dict[str, int] = {}
        by_action_type: dict[str, int] = {}
        total_success_rate = 0.0
        total_occurrences = 0

        for t in templates:
            category = t.get("category", "unknown")
            by_category[category] = by_category.get(category, 0) + 1

            action_type = t.get("action_type", "unknown")
            by_action_type[action_type] = by_action_type.get(action_type, 0) + 1

            total_success_rate += t.get("success_rate", 0)
            total_occurrences += t.get("occurrences", 0)

        return {
            "total_templates": len(templates),
            "by_category": by_category,
            "avg_success_rate": round(total_success_rate / len(templates), 4),
            "total_occurrences": total_occurrences,
            "by_action_type": by_action_type,
        }

    async def find_matching_templates(
        self,
        observation: str,
        action_type: Optional[str] = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Find templates that match a given observation.

        Args:
            observation: The observation to match against
            action_type: Optional filter by action type
            limit: Maximum templates to return

        Returns:
            List of matching templates with match scores
        """
        from .tracker import _compute_observation_hash

        observation_hash = _compute_observation_hash(observation)

        # First, try exact hash match
        exact_match = await self.get_template_by_hash(observation_hash)
        if exact_match:
            if action_type is None or exact_match.get("action", {}).get("type") == action_type:
                return [
                    {
                        **exact_match,
                        "match_score": 1.0,
                        "match_type": "exact_hash",
                    }
                ]

        # Fall back to fuzzy matching
        templates = await self.list_templates()
        matches = []

        # Extract features from observation for matching
        obs_words = set(_extract_action_words(observation))
        obs_patterns = set(_extract_file_patterns(observation))

        for t in templates:
            if action_type and t.get("action_type") != action_type:
                continue

            # Load full template for matching
            full_template = await self.get_template(t["name"])
            if not full_template:
                continue

            trigger = full_template.get("trigger", {})
            template_words = set(trigger.get("action_words", []))
            template_patterns = set(trigger.get("file_patterns", []))

            # Calculate match score
            word_overlap = len(obs_words & template_words) / max(
                len(obs_words | template_words), 1
            )
            pattern_overlap = len(obs_patterns & template_patterns) / max(
                len(obs_patterns | template_patterns), 1
            )

            match_score = (word_overlap * 0.6) + (pattern_overlap * 0.4)

            if match_score > 0.3:  # Minimum threshold
                matches.append(
                    {
                        **full_template,
                        "match_score": round(match_score, 4),
                        "match_type": "fuzzy",
                    }
                )

        # Sort by match score and success rate
        matches.sort(
            key=lambda m: (m["match_score"], m.get("statistics", {}).get("success_rate", 0)),
            reverse=True,
        )

        return matches[:limit]

    async def cleanup_stale_templates(
        self,
        max_age_days: int = 90,
        min_occurrences: int = 3,
        min_success_rate: float = 0.5,
    ) -> int:
        """
        Archive templates that are stale or underperforming.

        Args:
            max_age_days: Archive templates not used in this many days
            min_occurrences: Archive templates with fewer occurrences
            min_success_rate: Archive templates below this success rate

        Returns:
            Number of templates archived
        """
        templates = await self.list_templates()
        archived = 0
        cutoff = datetime.now(timezone.utc).timestamp() - (max_age_days * 24 * 3600)

        for t in templates:
            template_data = await self.get_template(t["name"])
            if not template_data:
                continue

            stats = template_data.get("statistics", {})
            last_used = stats.get("last_used")

            should_archive = False
            reason = ""

            # Check age
            if last_used:
                try:
                    last_used_ts = _parse_datetime(last_used).timestamp()
                    if last_used_ts < cutoff:
                        should_archive = True
                        reason = f"Not used in {max_age_days} days"
                except Exception:
                    pass

            # Check occurrences
            if stats.get("occurrences", 0) < min_occurrences:
                should_archive = True
                reason = f"Low occurrences: {stats.get('occurrences', 0)}"

            # Check success rate
            if stats.get("success_rate", 0) < min_success_rate:
                should_archive = True
                reason = f"Low success rate: {stats.get('success_rate', 0):.0%}"

            if should_archive:
                if await self.archive_template(t["name"], reason):
                    archived += 1

        logger.info(f"Archived {archived} stale templates")
        return archived
