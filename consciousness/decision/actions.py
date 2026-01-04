"""
Action Definitions

Defines action templates that map observation patterns to executable actions.
Each template specifies trigger conditions, prompt templates, and execution parameters.
"""

from dataclasses import dataclass, field
from typing import Optional
import fnmatch
import re
from pathlib import Path

from .categories import ObservationCategory


@dataclass
class ActionTemplate:
    """
    Template for an action that can be triggered by file changes.

    Attributes:
        name: Unique identifier for this action
        description: Human-readable description of what this action does
        trigger_pattern: Glob pattern(s) that trigger this action (pipe-separated)
        trigger_categories: Categories that can trigger this action
        prompt_template: Template string for the execution prompt
        executor_type: Type of executor ('claude_code' or 'claude_flow')
        min_confidence: Minimum confidence threshold to execute (0.0 - 1.0)
        priority: Execution priority (lower = higher priority)
        cooldown_seconds: Minimum time between executions of this action
        requires_content: Whether to read file contents for the prompt
        max_files: Maximum number of files to process in one action
        tags: Optional tags for filtering/grouping actions
    """

    name: str
    description: str
    trigger_pattern: str
    trigger_categories: list[ObservationCategory]
    prompt_template: str
    executor_type: str = "claude_code"
    min_confidence: float = 0.6
    priority: int = 5
    cooldown_seconds: int = 30
    requires_content: bool = False
    max_files: int = 10
    tags: list[str] = field(default_factory=list)

    def matches_path(self, relative_path: str) -> bool:
        """Check if a path matches this action's trigger pattern."""
        patterns = self.trigger_pattern.split("|")
        for pattern in patterns:
            pattern = pattern.strip()
            if fnmatch.fnmatch(relative_path, pattern):
                return True
            # Also check just the filename
            if fnmatch.fnmatch(Path(relative_path).name, pattern):
                return True
        return False

    def matches_category(self, category: ObservationCategory) -> bool:
        """Check if a category matches this action's trigger categories."""
        return category in self.trigger_categories

    def render_prompt(self, **kwargs) -> str:
        """
        Render the prompt template with provided variables.

        Args:
            **kwargs: Variables to substitute in the template

        Returns:
            Rendered prompt string
        """
        prompt = self.prompt_template
        for key, value in kwargs.items():
            placeholder = "{" + key + "}"
            if isinstance(value, list):
                value = "\n".join(str(v) for v in value)
            prompt = prompt.replace(placeholder, str(value))
        return prompt

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "description": self.description,
            "trigger_pattern": self.trigger_pattern,
            "trigger_categories": [c.value for c in self.trigger_categories],
            "executor_type": self.executor_type,
            "min_confidence": self.min_confidence,
            "priority": self.priority,
            "cooldown_seconds": self.cooldown_seconds,
            "requires_content": self.requires_content,
            "max_files": self.max_files,
            "tags": self.tags,
        }


@dataclass
class ActionMatch:
    """Represents a matched action with its matched files."""

    template: ActionTemplate
    matched_files: list[str]
    category: ObservationCategory
    change_types: list[str]

    @property
    def file_count(self) -> int:
        return len(self.matched_files)

    def get_prompt_context(self) -> dict:
        """Get context variables for prompt rendering."""
        return {
            "file_paths": self.matched_files,
            "file_path": self.matched_files[0] if self.matched_files else "",
            "file_count": len(self.matched_files),
            "category": self.category.value,
            "change_types": ", ".join(set(self.change_types)),
        }


# Built-in action templates
BUILT_IN_ACTIONS: list[ActionTemplate] = [
    # Intake Processing
    ActionTemplate(
        name="process_intake",
        description="Process new intake files and integrate into knowledge base",
        trigger_pattern="_input/*|_input/**/*|_intake/pending/*|_intake/pending/**/*",
        trigger_categories=[ObservationCategory.INTAKE],
        prompt_template="""Process this intake file and integrate it into the knowledge base:

File: {file_path}
{file_content}

Instructions:
1. Analyze the content and determine its type (source, thought, thinker, etc.)
2. Create appropriate entries in the knowledge base
3. Update relevant indices
4. Move the file to _intake/processed/ when done
5. Log the processing in _intake/processed/log.yaml""",
        executor_type="claude_code",
        min_confidence=0.6,
        priority=1,
        requires_content=True,
        tags=["intake", "knowledge"],
    ),

    # Knowledge Index Update
    ActionTemplate(
        name="update_indices",
        description="Update indices when knowledge base changes",
        trigger_pattern="knowledge/**/*",
        trigger_categories=[ObservationCategory.KNOWLEDGE],
        prompt_template="""Knowledge base files have changed. Update the relevant indices.

Changed files:
{file_paths}

Change types: {change_types}

Instructions:
1. Read the changed files to understand what was modified
2. Update the appropriate index files in indices/
3. Ensure cross-references are maintained
4. Verify index consistency""",
        executor_type="claude_code",
        min_confidence=0.7,
        priority=2,
        cooldown_seconds=60,
        tags=["knowledge", "indices"],
    ),

    # Thinker Profile Sync
    ActionTemplate(
        name="sync_thinker_profile",
        description="Synchronize thinker profile with related files",
        trigger_pattern="knowledge/philosophy/thinkers/*/profile.md|knowledge/philosophy/thinkers/*/notes.md",
        trigger_categories=[ObservationCategory.KNOWLEDGE],
        prompt_template="""A thinker's profile or notes have changed. Ensure consistency.

Changed file: {file_path}

Instructions:
1. Check if profile.md, notes.md, references.md, and reflections.md are consistent
2. Update the thinkers index if needed
3. Verify cross-references to other thinkers""",
        executor_type="claude_code",
        min_confidence=0.65,
        priority=3,
        requires_content=True,
        tags=["thinkers", "knowledge"],
    ),

    # Configuration Validation
    ActionTemplate(
        name="validate_config",
        description="Validate configuration files after changes",
        trigger_pattern=".claude/**/*|*.yaml|*.yml|*.json",
        trigger_categories=[ObservationCategory.CONFIG],
        prompt_template="""Configuration files have changed. Validate the changes.

Changed files:
{file_paths}

Instructions:
1. Parse and validate the configuration syntax
2. Check for any breaking changes
3. Verify references to other files still exist
4. Report any issues found""",
        executor_type="claude_code",
        min_confidence=0.5,
        priority=4,
        tags=["config", "validation"],
    ),

    # Code Quality Check
    ActionTemplate(
        name="check_code_quality",
        description="Run code quality checks on changed source files",
        trigger_pattern="*.py|*.ts|*.js|consciousness/**/*.py",
        trigger_categories=[ObservationCategory.CODE],
        prompt_template="""Source code files have changed. Perform quality checks.

Changed files:
{file_paths}

Instructions:
1. Check for syntax errors
2. Review code style and formatting
3. Look for potential issues or anti-patterns
4. Suggest improvements if applicable""",
        executor_type="claude_code",
        min_confidence=0.5,
        priority=5,
        cooldown_seconds=120,
        tags=["code", "quality"],
    ),

    # Test Trigger
    ActionTemplate(
        name="run_related_tests",
        description="Run tests related to changed code",
        trigger_pattern="consciousness/**/*.py|src/**/*.py",
        trigger_categories=[ObservationCategory.CODE],
        prompt_template="""Code files have changed. Run related tests.

Changed files:
{file_paths}

Instructions:
1. Identify test files related to the changed code
2. Run those specific tests
3. Report any failures
4. Suggest fixes if tests fail""",
        executor_type="claude_code",
        min_confidence=0.6,
        priority=6,
        cooldown_seconds=180,
        tags=["code", "testing"],
    ),

    # Documentation Sync
    ActionTemplate(
        name="sync_documentation",
        description="Ensure documentation stays in sync with code",
        trigger_pattern="docs/**/*|*.md",
        trigger_categories=[ObservationCategory.DOCUMENTATION],
        prompt_template="""Documentation files have changed.

Changed files:
{file_paths}

Instructions:
1. Verify documentation accuracy
2. Check for broken links
3. Update table of contents if needed
4. Ensure consistency with code""",
        executor_type="claude_code",
        min_confidence=0.4,
        priority=7,
        cooldown_seconds=300,
        tags=["docs"],
    ),

    # Template Validation
    ActionTemplate(
        name="validate_templates",
        description="Validate template files after changes",
        trigger_pattern="templates/**/*",
        trigger_categories=[ObservationCategory.TEMPLATE],
        prompt_template="""Template files have changed. Validate them.

Changed files:
{file_paths}

Instructions:
1. Check template syntax
2. Verify placeholder variables are documented
3. Ensure templates are complete and usable
4. Update template index if needed""",
        executor_type="claude_code",
        min_confidence=0.5,
        priority=4,
        tags=["templates"],
    ),

    # Swarm Orchestration (for complex changes)
    ActionTemplate(
        name="orchestrate_major_change",
        description="Use swarm orchestration for major changes",
        trigger_pattern="**/*",
        trigger_categories=[
            ObservationCategory.CODE,
            ObservationCategory.KNOWLEDGE,
            ObservationCategory.CONFIG,
        ],
        prompt_template="""Major changes detected across multiple areas. Orchestrate a comprehensive response.

Changed files:
{file_paths}

Categories affected: {category}
Change types: {change_types}

Instructions:
1. Analyze the scope of changes
2. Coordinate updates across affected areas
3. Ensure consistency
4. Run validation checks""",
        executor_type="claude_flow",
        min_confidence=0.8,
        priority=1,
        max_files=50,
        tags=["swarm", "major"],
    ),
]


def match_actions(
    changes: list,  # list[FileChange]
    actions: list[ActionTemplate] | None = None,
) -> list[ActionMatch]:
    """
    Match file changes against action templates.

    Args:
        changes: List of file changes to match
        actions: Optional list of action templates (uses BUILT_IN_ACTIONS if None)

    Returns:
        List of ActionMatch objects for matching actions
    """
    from .categories import categorize_single_change

    actions = actions or BUILT_IN_ACTIONS
    matches: dict[str, ActionMatch] = {}

    for change in changes:
        category = categorize_single_change(change)

        for template in actions:
            # Check if action matches this change
            matches_pattern = template.matches_path(change.relative_path)
            matches_cat = template.matches_category(category)

            if matches_pattern or matches_cat:
                if template.name not in matches:
                    matches[template.name] = ActionMatch(
                        template=template,
                        matched_files=[],
                        category=category,
                        change_types=[],
                    )

                match = matches[template.name]
                if change.relative_path not in match.matched_files:
                    match.matched_files.append(change.relative_path)
                if change.change_type not in match.change_types:
                    match.change_types.append(change.change_type)

    # Sort by priority (lower = higher priority)
    result = sorted(matches.values(), key=lambda m: m.template.priority)

    return result


def get_action_by_name(name: str, actions: list[ActionTemplate] | None = None) -> ActionTemplate | None:
    """
    Get an action template by name.

    Args:
        name: Name of the action to find
        actions: Optional list to search (uses BUILT_IN_ACTIONS if None)

    Returns:
        The matching ActionTemplate or None
    """
    actions = actions or BUILT_IN_ACTIONS
    for action in actions:
        if action.name == name:
            return action
    return None


def get_actions_by_tag(tag: str, actions: list[ActionTemplate] | None = None) -> list[ActionTemplate]:
    """
    Get action templates by tag.

    Args:
        tag: Tag to filter by
        actions: Optional list to search (uses BUILT_IN_ACTIONS if None)

    Returns:
        List of matching ActionTemplates
    """
    actions = actions or BUILT_IN_ACTIONS
    return [a for a in actions if tag in a.tags]


def create_custom_action(
    name: str,
    trigger_pattern: str,
    prompt_template: str,
    categories: list[ObservationCategory] | None = None,
    **kwargs
) -> ActionTemplate:
    """
    Create a custom action template.

    Args:
        name: Unique name for the action
        trigger_pattern: Glob pattern(s) to match
        prompt_template: Template for the execution prompt
        categories: Categories to trigger on (defaults to CODE)
        **kwargs: Additional ActionTemplate parameters

    Returns:
        New ActionTemplate instance
    """
    categories = categories or [ObservationCategory.CODE]

    return ActionTemplate(
        name=name,
        description=kwargs.get("description", f"Custom action: {name}"),
        trigger_pattern=trigger_pattern,
        trigger_categories=categories,
        prompt_template=prompt_template,
        **{k: v for k, v in kwargs.items() if k != "description"}
    )
