"""
Bidirectional linking for the philosophy repository.

Links between thoughts and thinkers in both directions:
- Thought -> Thinker: via related_thinkers array in thought frontmatter
- Thinker -> Thought: via thinkers/<name>/references.md table
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Repository root (knowledge/philosophy)
REPO_ROOT = Path(__file__).parent.parent.parent / "knowledge" / "philosophy"
THINKERS_DIR = REPO_ROOT / "thinkers"
THOUGHTS_DIR = REPO_ROOT / "thoughts"

VALID_STRENGTHS = ("strong", "moderate", "weak")


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    frontmatter_text = parts[1].strip()
    body = parts[2]

    # Simple YAML parsing for frontmatter
    frontmatter = {}
    current_key = None
    current_list = None

    for line in frontmatter_text.split("\n"):
        line = line.rstrip()
        if not line:
            continue

        # Check for list item
        if line.startswith("  - "):
            if current_list is not None:
                current_list.append(line[4:].strip().strip('"').strip("'"))
            continue

        # Check for key: value
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if value == "":
                # Start of a list
                frontmatter[key] = []
                current_key = key
                current_list = frontmatter[key]
            else:
                frontmatter[key] = value
                current_key = None
                current_list = None

    return frontmatter, body


def _serialize_frontmatter(frontmatter: dict) -> str:
    """Serialize frontmatter dict back to YAML."""
    lines = ["---"]
    for key, value in frontmatter.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        else:
            # Quote strings with special characters
            if isinstance(value, str) and any(c in value for c in ":#"):
                lines.append(f'{key}: "{value}"')
            else:
                lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)


def _read_file(path: Path) -> str:
    """Read file content, return empty string if not exists."""
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _write_file(path: Path, content: str) -> bool:
    """Write content to file, creating parent dirs if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _get_thought_file(thought_path: str) -> Path:
    """Resolve thought path to actual file."""
    path = THOUGHTS_DIR / thought_path

    # If it's a directory, look for thought.md or main.md
    if path.is_dir():
        for name in ("thought.md", "main.md"):
            candidate = path / name
            if candidate.exists():
                return candidate
        # Default to thought.md
        return path / "thought.md"

    # If it's a file path without extension, add .md
    if not path.suffix:
        path = path.with_suffix(".md")

    return path


def _get_references_file(thinker_name: str) -> Path:
    """Get path to thinker's references.md file."""
    return THINKERS_DIR / thinker_name / "references.md"


def _normalize_thinker_name(name: str) -> str:
    """Normalize thinker name to folder format (lowercase, underscores)."""
    return name.lower().replace(" ", "_").replace("-", "_")


def _get_relative_thought_path(thought_path: str) -> str:
    """Get relative path from thoughts dir for display."""
    # Remove leading thoughts/ if present
    if thought_path.startswith("thoughts/"):
        thought_path = thought_path[9:]
    return thought_path


def add_thinker_to_thought(thought_path: str, thinker_name: str) -> bool:
    """
    Add thinker to thought's related_thinkers frontmatter.

    Args:
        thought_path: Path to thought file relative to thoughts/ dir
        thinker_name: Thinker folder name (e.g., 'karl_friston')

    Returns:
        True if successful, False otherwise
    """
    thinker_name = _normalize_thinker_name(thinker_name)
    thought_file = _get_thought_file(thought_path)

    if not thought_file.exists():
        return False

    content = _read_file(thought_file)
    frontmatter, body = _parse_frontmatter(content)

    # Initialize related_thinkers if missing
    if "related_thinkers" not in frontmatter:
        frontmatter["related_thinkers"] = []

    # Add thinker if not already present
    if thinker_name not in frontmatter["related_thinkers"]:
        frontmatter["related_thinkers"].append(thinker_name)

    # Reconstruct file
    new_content = _serialize_frontmatter(frontmatter) + body
    return _write_file(thought_file, new_content)


def add_thought_to_thinker(
    thinker_name: str,
    thought_path: str,
    strength: str,
    reasoning: str
) -> bool:
    """
    Add thought reference to thinker's references.md.

    Args:
        thinker_name: Thinker folder name (e.g., 'karl_friston')
        thought_path: Path to thought relative to thoughts/ dir
        strength: One of 'strong', 'moderate', 'weak'
        reasoning: Brief explanation of the connection

    Returns:
        True if successful, False otherwise
    """
    thinker_name = _normalize_thinker_name(thinker_name)

    if strength not in VALID_STRENGTHS:
        return False

    references_file = _get_references_file(thinker_name)
    content = _read_file(references_file)

    # Normalize thought path for display
    display_path = _get_relative_thought_path(thought_path)
    today = date.today().isoformat()

    # Create new table row
    new_row = f"| {today} | {strength} | {display_path} | {reasoning} |"

    if not content:
        # Create new references.md file
        content = _create_references_template(thinker_name, new_row)
    else:
        # Check if thought already referenced
        if display_path in content:
            # Update existing row
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if display_path in line and line.startswith("|"):
                    lines[i] = new_row
                    break
            content = "\n".join(lines)
        else:
            # Add new row after table header
            content = _insert_table_row(content, new_row)

    return _write_file(references_file, content)


def _create_references_template(thinker_name: str, first_row: str) -> str:
    """Create a new references.md file with the first reference."""
    display_name = thinker_name.replace("_", " ").title()
    return f"""---
thinker: "{display_name}"
tags:
  - thinker
  - references
---

# References for {display_name}

Track all references to {display_name} across thoughts, sources, and reflections.

## Cross-References to Thoughts

| Date | Strength | Path | Reasoning |
|------|----------|------|-----------|
{first_row}

## Related Thinkers in Repository

| Thinker | Connection Type | Notes |
|---------|-----------------|-------|

## External References

## Notes

"""


def _insert_table_row(content: str, row: str) -> str:
    """Insert a row into the Cross-References table."""
    # Find the table header separator line
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("|---") and "Strength" in lines[i-1]:
            # Insert after this line
            lines.insert(i + 1, row)
            return "\n".join(lines)

    # If table not found, append to end
    return content + "\n" + row


def create_bidirectional_link(
    thought_path: str,
    thinker_name: str,
    strength: str,
    reasoning: str
) -> bool:
    """
    Create both directions of the link.

    Args:
        thought_path: Path to thought relative to thoughts/ dir
        thinker_name: Thinker folder name (e.g., 'karl_friston')
        strength: One of 'strong', 'moderate', 'weak'
        reasoning: Brief explanation of the connection

    Returns:
        True if both links created successfully, False otherwise
    """
    thought_ok = add_thinker_to_thought(thought_path, thinker_name)
    thinker_ok = add_thought_to_thinker(thinker_name, thought_path, strength, reasoning)
    return thought_ok and thinker_ok


def get_thinker_thoughts(thinker_name: str) -> list[dict]:
    """
    Get all thoughts referencing a thinker.

    Args:
        thinker_name: Thinker folder name (e.g., 'karl_friston')

    Returns:
        List of dicts with keys: date, strength, path, reasoning
    """
    thinker_name = _normalize_thinker_name(thinker_name)
    references_file = _get_references_file(thinker_name)
    content = _read_file(references_file)

    if not content:
        return []

    thoughts = []
    in_thoughts_table = False

    for line in content.split("\n"):
        if "Cross-References to Thoughts" in line:
            in_thoughts_table = True
            continue

        if in_thoughts_table and line.startswith("## "):
            # End of thoughts table
            break

        if in_thoughts_table and line.startswith("|") and not line.startswith("|---") and "Date" not in line:
            # Parse table row
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 5:
                thoughts.append({
                    "date": parts[1],
                    "strength": parts[2],
                    "path": parts[3],
                    "reasoning": parts[4]
                })

    return thoughts


def get_thought_thinkers(thought_path: str) -> list[str]:
    """
    Get all thinkers referenced in a thought.

    Args:
        thought_path: Path to thought relative to thoughts/ dir

    Returns:
        List of thinker names
    """
    thought_file = _get_thought_file(thought_path)
    content = _read_file(thought_file)

    if not content:
        return []

    frontmatter, _ = _parse_frontmatter(content)
    return frontmatter.get("related_thinkers", [])


def remove_link(thought_path: str, thinker_name: str) -> bool:
    """
    Remove bidirectional link between thought and thinker.

    Args:
        thought_path: Path to thought relative to thoughts/ dir
        thinker_name: Thinker folder name (e.g., 'karl_friston')

    Returns:
        True if both removals successful, False otherwise
    """
    thinker_name = _normalize_thinker_name(thinker_name)

    # Remove from thought frontmatter
    thought_file = _get_thought_file(thought_path)
    thought_ok = False

    if thought_file.exists():
        content = _read_file(thought_file)
        frontmatter, body = _parse_frontmatter(content)

        if "related_thinkers" in frontmatter and thinker_name in frontmatter["related_thinkers"]:
            frontmatter["related_thinkers"].remove(thinker_name)
            new_content = _serialize_frontmatter(frontmatter) + body
            thought_ok = _write_file(thought_file, new_content)
        else:
            thought_ok = True  # Nothing to remove

    # Remove from thinker references
    references_file = _get_references_file(thinker_name)
    thinker_ok = False

    if references_file.exists():
        content = _read_file(references_file)
        display_path = _get_relative_thought_path(thought_path)

        lines = content.split("\n")
        new_lines = []
        removed = False

        for line in lines:
            if display_path in line and line.startswith("|"):
                removed = True
                continue
            new_lines.append(line)

        if removed:
            thinker_ok = _write_file(references_file, "\n".join(new_lines))
        else:
            thinker_ok = True  # Nothing to remove
    else:
        thinker_ok = True  # No references file

    return thought_ok and thinker_ok


def list_thinkers() -> list[str]:
    """List all thinker folder names in the repository."""
    if not THINKERS_DIR.exists():
        return []
    return sorted([d.name for d in THINKERS_DIR.iterdir() if d.is_dir()])


def list_thoughts() -> list[str]:
    """List all thought paths in the repository."""
    if not THOUGHTS_DIR.exists():
        return []

    thoughts = []
    for md_file in THOUGHTS_DIR.rglob("*.md"):
        if md_file.name in ("CLAUDE.md", "README.md"):
            continue
        rel_path = md_file.relative_to(THOUGHTS_DIR)
        thoughts.append(str(rel_path))

    return sorted(thoughts)


def validate_links() -> dict:
    """
    Validate all bidirectional links in the repository.

    Returns:
        Dict with 'missing_forward' (thought -> thinker) and
        'missing_reverse' (thinker -> thought) lists
    """
    missing_forward = []  # Thought references thinker but thinker doesn't reference thought
    missing_reverse = []  # Thinker references thought but thought doesn't reference thinker

    # Check all thoughts
    for thought_path in list_thoughts():
        thinkers = get_thought_thinkers(thought_path)
        for thinker in thinkers:
            # Check if thinker references this thought
            thinker_thoughts = get_thinker_thoughts(thinker)
            display_path = _get_relative_thought_path(thought_path)

            if not any(t["path"] == display_path for t in thinker_thoughts):
                missing_forward.append({
                    "thought": thought_path,
                    "thinker": thinker
                })

    # Check all thinkers
    for thinker in list_thinkers():
        thinker_thoughts = get_thinker_thoughts(thinker)
        for thought_ref in thinker_thoughts:
            thought_path = thought_ref["path"]
            thought_thinkers = get_thought_thinkers(thought_path)

            if thinker not in thought_thinkers:
                missing_reverse.append({
                    "thinker": thinker,
                    "thought": thought_path
                })

    return {
        "missing_forward": missing_forward,
        "missing_reverse": missing_reverse
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python linker.py <command> [args]")
        print("Commands:")
        print("  link <thought_path> <thinker> <strength> <reasoning>")
        print("  unlink <thought_path> <thinker>")
        print("  thinker-thoughts <thinker>")
        print("  thought-thinkers <thought_path>")
        print("  validate")
        print("  list-thinkers")
        print("  list-thoughts")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "link" and len(sys.argv) >= 6:
        result = create_bidirectional_link(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
        print(f"Link created: {result}")

    elif cmd == "unlink" and len(sys.argv) >= 4:
        result = remove_link(sys.argv[2], sys.argv[3])
        print(f"Link removed: {result}")

    elif cmd == "thinker-thoughts" and len(sys.argv) >= 3:
        thoughts = get_thinker_thoughts(sys.argv[2])
        for t in thoughts:
            print(f"  [{t['strength']}] {t['path']}: {t['reasoning']}")

    elif cmd == "thought-thinkers" and len(sys.argv) >= 3:
        thinkers = get_thought_thinkers(sys.argv[2])
        for t in thinkers:
            print(f"  {t}")

    elif cmd == "validate":
        result = validate_links()
        if result["missing_forward"]:
            print("Missing reverse links (thought -> thinker, but thinker missing thought):")
            for m in result["missing_forward"]:
                print(f"  {m['thought']} -> {m['thinker']}")
        if result["missing_reverse"]:
            print("Missing forward links (thinker -> thought, but thought missing thinker):")
            for m in result["missing_reverse"]:
                print(f"  {m['thinker']} -> {m['thought']}")
        if not result["missing_forward"] and not result["missing_reverse"]:
            print("All links are valid.")

    elif cmd == "list-thinkers":
        for t in list_thinkers():
            print(t)

    elif cmd == "list-thoughts":
        for t in list_thoughts():
            print(t)

    else:
        print(f"Unknown command or missing arguments: {cmd}")
        sys.exit(1)
