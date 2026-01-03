"""Claude Code Helper Scripts.

A utility module for the claude-code agent workflow. Provides project context
extraction to help the agent understand repository structure before delegating
work to the Claude Code CLI.

Modules:
    project_context: Extract project mapping, test configuration, recent progress,
        dependencies, and related tickets from a repository.

Example:
    Get project context for a repository::

        $ python -m claude_code_helper.project_context /path/to/repo

    Or use the script directly::

        $ python scripts/claude_code_helper/project_context.py /path/to/repo

Note:
    The script outputs JSON to stdout for easy parsing by the claude-code agent.
    Exit code 0 indicates success, non-zero indicates failure.
"""

__version__ = "2.0.0"
