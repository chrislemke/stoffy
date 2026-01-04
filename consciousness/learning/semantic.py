"""
Semantic Memory Writer - Writes distilled wisdom to the knowledge directory.

Semantic Memory is the "Wisdom" layer - it contains distilled truths written to
Markdown files in the `knowledge/` directory. Unlike Episodic (logs) and Procedural
(patterns in SQLite) memory, Semantic memory persists as permanent documentation.

Target Files:
- knowledge/rules.md - Behavioral rules and conventions
- knowledge/architecture.md - System architecture insights
- knowledge/patterns/learned_rules.md - Learned patterns from outcomes

Integration:
- The Dreamer calls consolidate_from_outcomes() during the dream cycle
- New rules are appended, not overwritten
- Uses structured markdown format with frontmatter-style headers
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .tracker import Outcome, OutcomeType
from .patterns import Pattern, PatternType

logger = logging.getLogger(__name__)


@dataclass
class SemanticMemoryConfig:
    """Configuration for semantic memory writing."""

    knowledge_dir: Path = field(default_factory=lambda: Path("knowledge"))
    rules_file: str = "rules.md"
    architecture_file: str = "architecture.md"
    patterns_file: str = "patterns/learned_rules.md"
    min_confidence_for_write: float = 0.8
    min_occurrences_for_rule: int = 5
    max_rules_per_consolidation: int = 10
    backup_on_write: bool = True


@dataclass
class SemanticRule:
    """A rule extracted from patterns and outcomes."""

    name: str
    description: str
    source: str
    confidence: float
    first_observed: datetime
    occurrences: int
    category: str = "general"
    action_type: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_markdown(self) -> str:
        """Convert rule to markdown format."""
        lines = [
            f"## Rule: {self.name}",
            f"- **Source**: {self.source}",
            f"- **Confidence**: {self.confidence:.2f}",
            f"- **First observed**: {self.first_observed.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"- **Occurrences**: {self.occurrences}",
            f"- **Category**: {self.category}",
        ]

        if self.action_type:
            lines.append(f"- **Action type**: {self.action_type}")

        lines.append("")
        lines.append(self.description)
        lines.append("")

        return "\n".join(lines)


@dataclass
class ArchitectureInsight:
    """An architecture insight to record."""

    component: str
    insight: str
    source: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    related_patterns: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        """Convert insight to markdown format."""
        lines = [
            f"### {self.component}",
            f"*Recorded: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}*",
            f"*Source: {self.source}*",
            "",
            self.insight,
            "",
        ]

        if self.related_patterns:
            lines.append("**Related patterns:**")
            for pattern in self.related_patterns:
                lines.append(f"- {pattern}")
            lines.append("")

        return "\n".join(lines)


class SemanticMemoryWriter:
    """
    Writes distilled wisdom to the knowledge directory.

    Manages three types of semantic memory:
    1. Rules - Behavioral guidelines learned from outcomes
    2. Architecture - System design insights
    3. Patterns - Consolidated patterns from learning

    All files use structured markdown format for human readability
    and LLM accessibility.
    """

    def __init__(
        self,
        base_path: str | Path,
        config: Optional[SemanticMemoryConfig] = None,
    ):
        """
        Initialize the semantic memory writer.

        Args:
            base_path: Base path for the project (contains knowledge/ directory)
            config: Optional configuration
        """
        self.base_path = Path(base_path)
        self.config = config or SemanticMemoryConfig()
        self._lock = asyncio.Lock()
        self._initialized = False

    @property
    def knowledge_path(self) -> Path:
        """Get the full path to the knowledge directory."""
        return self.base_path / self.config.knowledge_dir

    @property
    def rules_path(self) -> Path:
        """Get the full path to the rules file."""
        return self.knowledge_path / self.config.rules_file

    @property
    def architecture_path(self) -> Path:
        """Get the full path to the architecture file."""
        return self.knowledge_path / self.config.architecture_file

    @property
    def patterns_path(self) -> Path:
        """Get the full path to the learned patterns file."""
        return self.knowledge_path / self.config.patterns_file

    async def initialize(self) -> None:
        """
        Ensure directories and files exist with proper structure.

        Creates the knowledge directory structure if it doesn't exist,
        and initializes files with headers if they don't exist.
        """
        if self._initialized:
            return

        async with self._lock:
            # Create directories
            self.knowledge_path.mkdir(parents=True, exist_ok=True)
            (self.knowledge_path / "patterns").mkdir(parents=True, exist_ok=True)

            # Initialize rules file
            if not self.rules_path.exists():
                await self._write_file(
                    self.rules_path,
                    self._get_rules_header(),
                )

            # Initialize architecture file
            if not self.architecture_path.exists():
                await self._write_file(
                    self.architecture_path,
                    self._get_architecture_header(),
                )

            # Initialize learned patterns file
            if not self.patterns_path.exists():
                await self._write_file(
                    self.patterns_path,
                    self._get_patterns_header(),
                )

            self._initialized = True
            logger.info(f"Semantic memory initialized at {self.knowledge_path}")

    def _get_rules_header(self) -> str:
        """Get the header content for the rules file."""
        return """# Behavioral Rules and Conventions

This file contains learned behavioral rules extracted from outcome analysis.
Rules are added automatically during the dream cycle consolidation process.

**Format:**
- Each rule has a name, source, confidence score, and observation count
- Rules with confidence >= 0.8 are considered reliable
- Rules are never deleted, only deprecated with notes

---

"""

    def _get_architecture_header(self) -> str:
        """Get the header content for the architecture file."""
        return """# Architecture Insights

This file contains architecture insights learned from system operation.
Insights describe component behaviors, interactions, and design decisions.

**Categories:**
- Component insights - How individual components behave
- Integration insights - How components interact
- Performance insights - What affects system performance
- Error insights - Common failure modes and recovery patterns

---

"""

    def _get_patterns_header(self) -> str:
        """Get the header content for the learned patterns file."""
        return """# Learned Patterns

This file contains patterns extracted from outcome analysis.
Patterns describe recurring observation -> action -> outcome sequences.

**Pattern Types:**
- `observation_action` - When X is observed, action Y tends to succeed
- `action_sequence` - After action X, action Y often follows
- `failure_recovery` - When action X fails, action Y often recovers
- `context_based` - Action X works well in context Y

---

"""

    async def _write_file(self, path: Path, content: str) -> None:
        """Write content to a file asynchronously."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: path.write_text(content, encoding="utf-8"),
        )

    async def _read_file(self, path: Path) -> str:
        """Read content from a file asynchronously."""
        if not path.exists():
            return ""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: path.read_text(encoding="utf-8"),
        )

    async def _append_to_file(self, path: Path, content: str) -> None:
        """Append content to a file asynchronously."""
        async with self._lock:
            existing = await self._read_file(path)

            # Backup if configured
            if self.config.backup_on_write and path.exists():
                backup_path = path.with_suffix(f".{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak")
                await self._write_file(backup_path, existing)

            await self._write_file(path, existing + content)

    async def write_rule(
        self,
        rule: str,
        source: str,
        confidence: float,
        category: str = "general",
        action_type: Optional[str] = None,
        occurrences: int = 1,
    ) -> bool:
        """
        Write a new rule to the rules file.

        Args:
            rule: The rule description
            source: Where this rule was learned from
            confidence: Confidence level (0.0-1.0)
            category: Rule category (default: "general")
            action_type: Optional related action type
            occurrences: Number of times this pattern was observed

        Returns:
            True if rule was written, False if confidence too low
        """
        await self.initialize()

        if confidence < self.config.min_confidence_for_write:
            logger.debug(
                f"Rule confidence {confidence:.2f} below threshold "
                f"{self.config.min_confidence_for_write:.2f}, skipping"
            )
            return False

        # Generate a name from the rule
        rule_name = self._generate_rule_name(rule)

        # Check for duplicates
        existing_rules = await self.read_rules()
        if any(rule_name.lower() in existing.lower() for existing in existing_rules):
            logger.debug(f"Rule '{rule_name}' already exists, skipping")
            return False

        semantic_rule = SemanticRule(
            name=rule_name,
            description=rule,
            source=source,
            confidence=confidence,
            first_observed=datetime.now(timezone.utc),
            occurrences=occurrences,
            category=category,
            action_type=action_type,
        )

        content = semantic_rule.to_markdown()
        await self._append_to_file(self.rules_path, content)

        logger.info(f"Wrote rule: {rule_name} (confidence: {confidence:.2f})")
        return True

    def _generate_rule_name(self, rule: str) -> str:
        """Generate a short name from a rule description."""
        # Take first sentence or first 60 chars
        first_sentence = rule.split(".")[0].strip()
        if len(first_sentence) > 60:
            first_sentence = first_sentence[:57] + "..."

        # Clean up for use as name
        name = re.sub(r"[^\w\s-]", "", first_sentence)
        name = " ".join(name.split())

        return name.title()

    async def write_pattern(
        self,
        pattern: Pattern,
        insight: str,
    ) -> bool:
        """
        Write a learned pattern to the patterns file.

        Args:
            pattern: The Pattern object to write
            insight: Human-readable insight about this pattern

        Returns:
            True if pattern was written
        """
        await self.initialize()

        if pattern.success_rate < self.config.min_confidence_for_write:
            logger.debug(
                f"Pattern success rate {pattern.success_rate:.2f} below threshold, skipping"
            )
            return False

        if pattern.occurrences < self.config.min_occurrences_for_rule:
            logger.debug(
                f"Pattern occurrences {pattern.occurrences} below threshold "
                f"{self.config.min_occurrences_for_rule}, skipping"
            )
            return False

        content = self._format_pattern_entry(pattern, insight)
        await self._append_to_file(self.patterns_path, content)

        logger.info(
            f"Wrote pattern: {pattern.action_type} "
            f"(success rate: {pattern.success_rate:.2f}, occurrences: {pattern.occurrences})"
        )
        return True

    def _format_pattern_entry(self, pattern: Pattern, insight: str) -> str:
        """Format a pattern as a markdown entry."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        lines = [
            f"## Pattern: {pattern.action_type.replace('_', ' ').title()}",
            f"- **Type**: {pattern.pattern_type.value}",
            f"- **Success rate**: {pattern.success_rate:.0%}",
            f"- **Occurrences**: {pattern.occurrences}",
            f"- **Recorded**: {timestamp}",
            "",
            "**Trigger:**",
            f"> {pattern.trigger_description[:200] if pattern.trigger_description else 'N/A'}",
            "",
            "**Insight:**",
            insight,
            "",
            "---",
            "",
        ]

        return "\n".join(lines)

    async def write_architecture_insight(
        self,
        insight: str,
        component: str,
        source: str = "outcome_analysis",
        related_patterns: Optional[list[str]] = None,
    ) -> bool:
        """
        Write an architecture insight to the architecture file.

        Args:
            insight: The insight description
            component: Which component this relates to
            source: Where this insight came from
            related_patterns: Optional list of related pattern names

        Returns:
            True if insight was written
        """
        await self.initialize()

        arch_insight = ArchitectureInsight(
            component=component,
            insight=insight,
            source=source,
            related_patterns=related_patterns or [],
        )

        content = arch_insight.to_markdown()
        await self._append_to_file(self.architecture_path, content)

        logger.info(f"Wrote architecture insight for component: {component}")
        return True

    async def read_rules(self) -> list[str]:
        """
        Read all existing rules from the rules file.

        Returns:
            List of rule names/descriptions
        """
        await self.initialize()

        content = await self._read_file(self.rules_path)
        if not content:
            return []

        # Extract rule names from markdown headers
        rules = []
        for line in content.split("\n"):
            if line.startswith("## Rule:"):
                rule_name = line.replace("## Rule:", "").strip()
                rules.append(rule_name)

        return rules

    async def search_knowledge(
        self,
        query: str,
        include_rules: bool = True,
        include_architecture: bool = True,
        include_patterns: bool = True,
    ) -> list[str]:
        """
        Search the knowledge base for relevant entries.

        Args:
            query: Search query (case-insensitive)
            include_rules: Search in rules file
            include_architecture: Search in architecture file
            include_patterns: Search in patterns file

        Returns:
            List of matching sections
        """
        await self.initialize()

        results = []
        query_lower = query.lower()

        if include_rules:
            rules_content = await self._read_file(self.rules_path)
            results.extend(self._search_sections(rules_content, query_lower, "Rule"))

        if include_architecture:
            arch_content = await self._read_file(self.architecture_path)
            results.extend(self._search_sections(arch_content, query_lower, "Architecture"))

        if include_patterns:
            patterns_content = await self._read_file(self.patterns_path)
            results.extend(self._search_sections(patterns_content, query_lower, "Pattern"))

        return results

    def _search_sections(
        self,
        content: str,
        query: str,
        source_type: str,
    ) -> list[str]:
        """Search markdown content for sections matching query."""
        if not content:
            return []

        results = []
        sections = re.split(r"(?=^## )", content, flags=re.MULTILINE)

        for section in sections:
            if query in section.lower():
                # Get the section title and first few lines
                lines = section.strip().split("\n")
                if lines:
                    title = lines[0].replace("##", "").strip()
                    preview = " ".join(lines[1:4])[:200] if len(lines) > 1 else ""
                    results.append(f"[{source_type}] {title}: {preview}...")

        return results

    async def consolidate_from_outcomes(
        self,
        outcomes: list[Outcome],
        patterns: Optional[list[Pattern]] = None,
    ) -> dict[str, int]:
        """
        Analyze outcomes and patterns, write insights to knowledge base.

        This is called by the Dreamer during the dream cycle to consolidate
        learnings from recent outcomes into permanent semantic memory.

        Args:
            outcomes: List of Outcome objects to analyze
            patterns: Optional list of Pattern objects

        Returns:
            Dictionary with counts of items written
        """
        await self.initialize()

        stats = {
            "rules_written": 0,
            "patterns_written": 0,
            "insights_written": 0,
            "outcomes_analyzed": len(outcomes),
        }

        if not outcomes:
            return stats

        # Group outcomes by action type
        by_action_type: dict[str, list[Outcome]] = {}
        for outcome in outcomes:
            if outcome.action_type not in by_action_type:
                by_action_type[outcome.action_type] = []
            by_action_type[outcome.action_type].append(outcome)

        # Analyze each action type
        for action_type, action_outcomes in by_action_type.items():
            total = len(action_outcomes)
            if total < self.config.min_occurrences_for_rule:
                continue

            # Calculate success rate
            successes = sum(1 for o in action_outcomes if o.success)
            success_rate = successes / total

            # Extract rules from high-success patterns
            if success_rate >= self.config.min_confidence_for_write:
                rule_written = await self._extract_success_rule(
                    action_type, action_outcomes, success_rate
                )
                if rule_written:
                    stats["rules_written"] += 1

            # Extract rules from consistent failures
            elif success_rate <= 0.2 and total >= self.config.min_occurrences_for_rule:
                rule_written = await self._extract_failure_rule(
                    action_type, action_outcomes, success_rate
                )
                if rule_written:
                    stats["rules_written"] += 1

            # Check for rate limiting if we've written enough
            if stats["rules_written"] >= self.config.max_rules_per_consolidation:
                logger.info(
                    f"Reached max rules per consolidation "
                    f"({self.config.max_rules_per_consolidation})"
                )
                break

        # Write patterns if provided
        if patterns:
            for pattern in patterns:
                if pattern.is_reliable:
                    insight = self._generate_pattern_insight(pattern)
                    written = await self.write_pattern(pattern, insight)
                    if written:
                        stats["patterns_written"] += 1

        # Generate architecture insights from error patterns
        error_insights = await self._extract_error_insights(outcomes)
        for insight in error_insights:
            written = await self.write_architecture_insight(
                insight=insight["insight"],
                component=insight["component"],
                source="error_analysis",
            )
            if written:
                stats["insights_written"] += 1

        logger.info(
            f"Consolidation complete: {stats['rules_written']} rules, "
            f"{stats['patterns_written']} patterns, {stats['insights_written']} insights"
        )
        return stats

    async def _extract_success_rule(
        self,
        action_type: str,
        outcomes: list[Outcome],
        success_rate: float,
    ) -> bool:
        """Extract a success rule from outcomes."""
        # Find common context elements
        successful = [o for o in outcomes if o.success]
        if not successful:
            return False

        # Generate rule description
        sample_context = successful[0].context if successful else {}
        rule = (
            f"Action '{action_type}' succeeds {success_rate:.0%} of the time. "
            f"This action is reliable and should be preferred when appropriate."
        )

        if sample_context:
            context_keys = list(sample_context.keys())[:3]
            rule += f" Common context: {', '.join(context_keys)}."

        return await self.write_rule(
            rule=rule,
            source="outcome_consolidation",
            confidence=success_rate,
            category="success_pattern",
            action_type=action_type,
            occurrences=len(outcomes),
        )

    async def _extract_failure_rule(
        self,
        action_type: str,
        outcomes: list[Outcome],
        success_rate: float,
    ) -> bool:
        """Extract a failure rule from outcomes."""
        failed = [o for o in outcomes if not o.success and o.error_message]
        if not failed:
            return False

        # Find common error patterns
        error_messages = [o.error_message for o in failed if o.error_message]
        common_errors = self._find_common_patterns(error_messages)

        rule = (
            f"Action '{action_type}' fails {(1 - success_rate):.0%} of the time. "
            f"Consider alternative approaches or additional validation before using."
        )

        if common_errors:
            rule += f" Common error patterns: {common_errors[0][:100]}..."

        return await self.write_rule(
            rule=rule,
            source="outcome_consolidation",
            confidence=1 - success_rate,  # High confidence in the failure pattern
            category="failure_pattern",
            action_type=action_type,
            occurrences=len(outcomes),
        )

    def _find_common_patterns(self, strings: list[str]) -> list[str]:
        """Find common patterns in a list of strings."""
        if not strings:
            return []

        # Simple frequency-based approach
        word_freq: dict[str, int] = {}
        for s in strings:
            words = s.lower().split()
            for word in words:
                if len(word) > 3:  # Skip short words
                    word_freq[word] = word_freq.get(word, 0) + 1

        # Find words that appear in at least 50% of strings
        threshold = len(strings) * 0.5
        common = [word for word, count in word_freq.items() if count >= threshold]

        return common[:5]

    def _generate_pattern_insight(self, pattern: Pattern) -> str:
        """Generate a human-readable insight from a pattern."""
        insight_parts = []

        if pattern.pattern_type == PatternType.OBSERVATION_ACTION:
            insight_parts.append(
                f"When observations match this trigger pattern, "
                f"the action '{pattern.action_type}' succeeds {pattern.success_rate:.0%} of the time."
            )
        elif pattern.pattern_type == PatternType.FAILURE_RECOVERY:
            insight_parts.append(
                f"This pattern indicates a successful recovery strategy "
                f"after a failure condition."
            )
        elif pattern.pattern_type == PatternType.CONTEXT_BASED:
            insight_parts.append(
                f"This action works particularly well in certain contexts "
                f"(success rate: {pattern.success_rate:.0%})."
            )
        else:
            insight_parts.append(
                f"Pattern with {pattern.occurrences} occurrences and "
                f"{pattern.success_rate:.0%} success rate."
            )

        if pattern.occurrences >= 10:
            insight_parts.append("This is a well-established pattern.")

        return " ".join(insight_parts)

    async def _extract_error_insights(
        self,
        outcomes: list[Outcome],
    ) -> list[dict[str, str]]:
        """Extract architecture insights from error patterns."""
        insights = []

        # Group errors by type
        error_outcomes = [o for o in outcomes if o.error_message]
        if not error_outcomes:
            return insights

        error_types: dict[str, list[Outcome]] = {}
        for outcome in error_outcomes:
            # Extract error type from message
            error_type = self._categorize_error(outcome.error_message or "")
            if error_type not in error_types:
                error_types[error_type] = []
            error_types[error_type].append(outcome)

        # Generate insights for frequent errors
        for error_type, error_list in error_types.items():
            if len(error_list) >= 3:
                actions = set(o.action_type for o in error_list)
                insight = (
                    f"Error type '{error_type}' occurs frequently "
                    f"(observed {len(error_list)} times). "
                    f"Affected actions: {', '.join(actions)}. "
                    f"Consider adding error handling or validation."
                )
                insights.append({
                    "component": "error_handling",
                    "insight": insight,
                })

        return insights[:3]  # Limit to top 3 insights

    def _categorize_error(self, error_message: str) -> str:
        """Categorize an error message into a type."""
        error_lower = error_message.lower()

        if "timeout" in error_lower:
            return "timeout"
        elif "permission" in error_lower or "denied" in error_lower:
            return "permission"
        elif "not found" in error_lower or "missing" in error_lower:
            return "not_found"
        elif "connection" in error_lower or "network" in error_lower:
            return "network"
        elif "memory" in error_lower or "oom" in error_lower:
            return "memory"
        elif "syntax" in error_lower or "parse" in error_lower:
            return "syntax"
        else:
            return "general"

    async def get_statistics(self) -> dict[str, Any]:
        """Get statistics about the semantic memory."""
        await self.initialize()

        rules = await self.read_rules()
        rules_content = await self._read_file(self.rules_path)
        arch_content = await self._read_file(self.architecture_path)
        patterns_content = await self._read_file(self.patterns_path)

        return {
            "knowledge_path": str(self.knowledge_path),
            "rules_count": len(rules),
            "rules_file_size": len(rules_content),
            "architecture_file_size": len(arch_content),
            "patterns_file_size": len(patterns_content),
            "config": {
                "min_confidence": self.config.min_confidence_for_write,
                "min_occurrences": self.config.min_occurrences_for_rule,
            },
        }


# Convenience function for creating writer with daemon
def create_semantic_memory_writer(
    base_path: str | Path,
    config: Optional[SemanticMemoryConfig] = None,
) -> SemanticMemoryWriter:
    """
    Create a SemanticMemoryWriter instance for use with the daemon.

    Args:
        base_path: Base path for the project
        config: Optional configuration

    Returns:
        Configured SemanticMemoryWriter instance
    """
    return SemanticMemoryWriter(
        base_path=base_path,
        config=config,
    )
