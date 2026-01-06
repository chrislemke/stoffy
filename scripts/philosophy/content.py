"""
Content reading utilities for the philosophy repository.

Provides functions to read philosophy content with memory file support.
Memory files (_memory.md) have higher weight than source files.
"""

from pathlib import Path
from typing import Optional
import re

# Repository root for philosophy content
PHILOSOPHY_ROOT = Path("/Users/chris/Developer/stoffy/knowledge/philosophy")


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """
    Parse YAML frontmatter from markdown content.

    Args:
        content: Full markdown content with optional frontmatter

    Returns:
        Tuple of (frontmatter_dict, body_without_frontmatter)
        If no frontmatter, returns ({}, full_content)
    """
    if not content.startswith("---"):
        return {}, content

    # Find the closing ---
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n?(.*)', content, re.DOTALL)
    if not match:
        return {}, content

    yaml_block = match.group(1)
    body = match.group(2)

    # Simple YAML parsing (no external dependency)
    frontmatter = {}
    current_key = None
    current_list = None

    for line in yaml_block.split('\n'):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue

        # Check for list item
        if stripped.startswith('- '):
            if current_list is not None:
                current_list.append(stripped[2:].strip().strip('"\''))
            continue

        # Check for key: value
        if ':' in stripped:
            # End previous list if any
            if current_list is not None and current_key:
                frontmatter[current_key] = current_list
                current_list = None

            key, _, value = stripped.partition(':')
            key = key.strip()
            value = value.strip()

            if not value:
                # Could be start of a list or multi-line
                current_key = key
                current_list = []
            elif value.startswith('[') and value.endswith(']'):
                # Inline list
                items = value[1:-1].split(',')
                frontmatter[key] = [item.strip().strip('"\'') for item in items if item.strip()]
            elif value.startswith('"') and value.endswith('"'):
                frontmatter[key] = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                frontmatter[key] = value[1:-1]
            elif value.lower() in ('true', 'false'):
                frontmatter[key] = value.lower() == 'true'
            elif value.isdigit():
                frontmatter[key] = int(value)
            else:
                frontmatter[key] = value

    # Don't forget the last list
    if current_list is not None and current_key:
        frontmatter[current_key] = current_list

    return frontmatter, body


def _get_memory_path(file_path: Path) -> Path:
    """
    Get the memory file path for a given file.

    file.md -> file_memory.md
    """
    return file_path.parent / f"{file_path.stem}_memory{file_path.suffix}"


def read_content(path: str) -> dict:
    """
    Read content with memory file support.

    Args:
        path: Path to the file (absolute or relative to philosophy root)

    Returns:
        Dictionary with:
            - content: Main file content
            - memory: Memory file content if exists, else None
            - has_memory: Boolean indicating if memory file exists
            - frontmatter: Parsed YAML frontmatter dict
            - body: Content without frontmatter
    """
    # Handle both absolute and relative paths
    file_path = Path(path)
    if not file_path.is_absolute():
        file_path = PHILOSOPHY_ROOT / path

    result = {
        'content': None,
        'memory': None,
        'has_memory': False,
        'frontmatter': {},
        'body': ''
    }

    # Read main file
    if file_path.exists():
        result['content'] = file_path.read_text(encoding='utf-8')
        result['frontmatter'], result['body'] = parse_frontmatter(result['content'])

    # Check for memory file
    memory_path = _get_memory_path(file_path)
    if memory_path.exists():
        result['memory'] = memory_path.read_text(encoding='utf-8')
        result['has_memory'] = True

    return result


def read_thought(thought_path: str) -> dict:
    """
    Read a thought file with memory support.

    Args:
        thought_path: Path to thought (e.g., "thoughts/consciousness/2025-12-26_improvised_self.md")

    Returns:
        Same structure as read_content
    """
    # Normalize path - thoughts can be specified multiple ways
    if not thought_path.startswith("thoughts/"):
        thought_path = f"thoughts/{thought_path}"

    # Handle folder-style thoughts (some are folders with thought.md inside)
    path = Path(thought_path)
    if not path.suffix:
        # It's a folder reference, look for thought.md inside
        thought_path = f"{thought_path}/thought.md"

    return read_content(thought_path)


def read_thinker(thinker_name: str) -> dict:
    """
    Read all files for a thinker: profile, notes, reflections, references.

    Args:
        thinker_name: Thinker folder name (e.g., "karl_friston", "aristotle")

    Returns:
        Dictionary with keys: profile, notes, reflections, references
        Each value is the result of read_content() for that file
    """
    thinker_dir = PHILOSOPHY_ROOT / "thinkers" / thinker_name

    result = {}
    for file_type in ['profile', 'notes', 'reflections', 'references']:
        file_path = thinker_dir / f"{file_type}.md"
        if file_path.exists():
            result[file_type] = read_content(str(file_path))
        else:
            result[file_type] = None

    return result


def read_source(source_path: str) -> dict:
    """
    Read a source file with memory support.

    Args:
        source_path: Path to source (e.g., "sources/books/the_predictive_mind.md"
                     or "books/the_predictive_mind.md")

    Returns:
        Same structure as read_content
    """
    # Normalize path
    if not source_path.startswith("sources/"):
        source_path = f"sources/{source_path}"

    return read_content(source_path)


def read_index(index_name: str) -> dict:
    """
    Convenience wrapper to read an index file.

    Args:
        index_name: Name of index (e.g., "thinkers", "thoughts", "sources")

    Returns:
        Same structure as read_content
    """
    # Indices are at a different location
    index_path = Path("/Users/chris/Developer/stoffy/indices/philosophy") / f"{index_name}.yaml"

    if index_path.exists():
        content = index_path.read_text(encoding='utf-8')
        return {
            'content': content,
            'memory': None,
            'has_memory': False,
            'frontmatter': {},  # YAML files don't have frontmatter in the same sense
            'body': content
        }

    return {
        'content': None,
        'memory': None,
        'has_memory': False,
        'frontmatter': {},
        'body': ''
    }


def list_thinkers() -> list[str]:
    """
    List all available thinker names.

    Returns:
        List of thinker folder names
    """
    thinkers_dir = PHILOSOPHY_ROOT / "thinkers"
    return [d.name for d in thinkers_dir.iterdir()
            if d.is_dir() and not d.name.startswith('.')]


def list_thoughts(theme: Optional[str] = None) -> list[str]:
    """
    List all thought files, optionally filtered by theme.

    Args:
        theme: Optional theme to filter by (e.g., "consciousness", "free_will")

    Returns:
        List of thought paths relative to philosophy root
    """
    thoughts_dir = PHILOSOPHY_ROOT / "thoughts"

    if theme:
        theme_dir = thoughts_dir / theme
        if theme_dir.exists():
            return [f"thoughts/{theme}/{f.name}"
                    for f in theme_dir.iterdir()
                    if f.suffix == '.md' and not f.name.startswith('.')]
        return []

    # All thoughts across all themes
    result = []
    for theme_dir in thoughts_dir.iterdir():
        if theme_dir.is_dir() and not theme_dir.name.startswith('.') and theme_dir.name != 'CLAUDE.md':
            for thought_file in theme_dir.iterdir():
                if thought_file.suffix == '.md' and not thought_file.name.startswith('.'):
                    result.append(f"thoughts/{theme_dir.name}/{thought_file.name}")
    return result


def list_sources(source_type: Optional[str] = None) -> list[str]:
    """
    List all source files, optionally filtered by type.

    Args:
        source_type: Optional type to filter by (e.g., "books", "articles")

    Returns:
        List of source paths relative to philosophy root
    """
    sources_dir = PHILOSOPHY_ROOT / "sources"

    if source_type:
        type_dir = sources_dir / source_type
        if type_dir.exists():
            return [f"sources/{source_type}/{f.name}"
                    for f in type_dir.iterdir()
                    if f.suffix == '.md' and not f.name.startswith('.')]
        return []

    # All sources across all types
    result = []
    for type_dir in sources_dir.iterdir():
        if type_dir.is_dir() and not type_dir.name.startswith('.'):
            for source_file in type_dir.iterdir():
                if source_file.suffix == '.md' and not source_file.name.startswith('.'):
                    result.append(f"sources/{type_dir.name}/{source_file.name}")
    return result
