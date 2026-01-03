# Claude Code Helper Scripts

Utility script for the Claude Code agent to gather project context before executing tasks.

## Overview

| Script | Purpose | Token Savings |
|--------|---------|---------------|
| `project_context.py` | Extract project structure, config, dependencies | ~500 tokens |

## Installation

No additional installation required. The script uses Python 3.10+ features and standard library only.

## Script: project_context.py

Extracts comprehensive project context for the Claude Code agent. This helps the agent understand the project structure before delegating work to the `claude` CLI.

### Usage

```bash
# Get full project context
python scripts/claude_code_helper/project_context.py /path/to/repo

# Get context for current directory
python scripts/claude_code_helper/project_context.py .
```

### Output

The script returns a JSON object containing:

- **repo_path**: Absolute path to the repository
- **project_mapping**: Matched project folder in lead_stuff (if found)
- **test_config**: Pytest configuration and test directories
- **recent_progress**: Last 5 progress entries from progress_notes.md
- **related_tickets**: Ticket IDs found in recent git commits
- **languages**: Detected programming languages
- **has_opencode_config**: Whether repo has .opencode or .claude config
- **primary_dependencies**: Key ML/AI/web framework dependencies

### Example Output

```json
{
  "success": true,
  "repo_path": "/Users/dev/my-project",
  "project_mapping": {
    "matched_project": "my-project",
    "project_folder": "project_management/my-project",
    "match_method": "folder_name_match"
  },
  "test_config": {
    "test_command": "pytest",
    "test_dir": "tests",
    "unit_test_marker": "unit",
    "has_pytest": true
  },
  "recent_progress": [
    {
      "date": "2025-01-15",
      "title": "Implement feature X",
      "session_link": null
    }
  ],
  "related_tickets": ["FML-123", "FLUG-456"],
  "languages": ["python"],
  "has_opencode_config": true,
  "primary_dependencies": ["fastapi", "pydantic", "boto3"]
}
```

## Path Resolution

The script accepts both absolute and relative paths:

1. **Absolute path**: Used directly
2. **Relative to CWD**: `./my-project` resolves from current directory
3. **Relative to lead_stuff**: `my-project` resolves from lead_stuff root

Example:
```bash
# All equivalent if CWD is lead_stuff:
python scripts/claude_code_helper/project_context.py /Users/me/Developer/my-project
python scripts/claude_code_helper/project_context.py ./my-project
python scripts/claude_code_helper/project_context.py my-project
```

## Integration with Claude Code Agent

The Claude Code agent (`.opencode/agent/claude-code.md`) uses this script at the start of sessions to:

1. **Understand project structure** before delegating to `claude` CLI
2. **Map repositories** to project folders in lead_stuff
3. **Identify test configuration** for the target repository
4. **Find related tickets** from git history
5. **Detect key dependencies** to inform context

### Typical Agent Workflow

```bash
# 1. Agent gathers context first
python scripts/claude_code_helper/project_context.py <repo>

# 2. Agent then delegates to Claude Code CLI
claude -p "<enhanced-prompt-with-context>" --model opus
```

## Error Handling

The script handles common errors gracefully:

- **Path not found**: Returns `success: false` with clear error message
- **Not a git repo**: Returns with `warning` field but continues
- **No project mapping**: Returns null for mapping fields

All output is valid JSON with a `success` boolean for easy parsing.
