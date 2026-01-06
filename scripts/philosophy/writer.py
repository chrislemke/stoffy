"""
Content Writer for Philosophy Repository

Creates and updates philosophical content (thoughts, thinkers, sources)
using templates, with automatic validation and index updates.

Writing Rules:
1. Always use templates when creating new files
2. Naming: lowercase_with_underscores
3. Dates: ISO 8601 (YYYY-MM-DD)
4. Thought files: YYYY-MM-DD_<topic>.md or folder YYYY-MM-DD_<topic>/
5. Thinker folders: <first>_<last>/
6. Auto-update relevant indices after creation
7. Auto-commit to main branch
"""

import os
import re
import subprocess
from datetime import date
from pathlib import Path
from typing import Optional

# Base paths
REPO_ROOT = Path(__file__).parent.parent.parent
KNOWLEDGE_ROOT = REPO_ROOT / "knowledge" / "philosophy"
TEMPLATES_ROOT = REPO_ROOT / "templates" / "philosophy"
INDICES_ROOT = REPO_ROOT / "indices" / "philosophy"

# Content paths
THOUGHTS_PATH = KNOWLEDGE_ROOT / "thoughts"
THINKERS_PATH = KNOWLEDGE_ROOT / "thinkers"
SOURCES_PATH = KNOWLEDGE_ROOT / "sources"

# Valid themes and source types
VALID_THEMES = ["life_meaning", "consciousness", "free_will", "morality", "existence", "knowledge"]
VALID_SOURCE_TYPES = ["book", "article", "lecture", "essay", "podcast", "conversation"]
VALID_STATUSES = ["seed", "exploring", "developing", "crystallized", "challenged", "integrated", "archived"]

# Philosophical commit verbs
COMMIT_VERBS = {
    "create": ["Seed", "Plant", "Kindle", "Begin"],
    "update": ["Explore", "Develop", "Refine", "Deepen"],
    "complete": ["Synthesize", "Crystallize", "Integrate", "Illuminate"],
    "challenge": ["Question", "Reconsider", "Examine", "Probe"],
    "connect": ["Link", "Weave", "Bridge", "Unite"],
}


def _slugify(text: str) -> str:
    """Convert text to lowercase_with_underscores slug."""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '_', text)
    return text.strip('_')


def _today() -> str:
    """Return today's date in ISO 8601 format."""
    return date.today().isoformat()


def _read_template(template_name: str) -> str:
    """Read a template file."""
    template_path = TEMPLATES_ROOT / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    return template_path.read_text()


def _fill_template(template: str, replacements: dict) -> str:
    """Fill template placeholders with values."""
    result = template
    for key, value in replacements.items():
        # Handle both {{key}} and {{key: format}} patterns
        # Pattern for {{key}}
        pattern1 = r'\{\{' + re.escape(key) + r'\}\}'
        result = re.sub(pattern1, str(value), result)
        # Pattern for {{key: format}}
        pattern2 = r'\{\{' + re.escape(key) + r': [^}]+\}\}'
        result = re.sub(pattern2, str(value), result)
    return result


def _git_commit(file_path: str, message: str) -> bool:
    """Stage and commit a file with the given message."""
    try:
        subprocess.run(
            ["git", "add", file_path],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True
        )
        return True
    except subprocess.CalledProcessError:
        return False


def generate_commit_message(action: str, entity_type: str, name: str) -> str:
    """
    Generate philosophical commit message using verbs:
    Seed, Explore, Refine, Synthesize, etc.

    Args:
        action: One of 'create', 'update', 'complete', 'challenge', 'connect'
        entity_type: 'thought', 'thinker', or 'source'
        name: Name/title of the entity

    Returns:
        Formatted commit message
    """
    import random

    verbs = COMMIT_VERBS.get(action, COMMIT_VERBS["update"])
    verb = random.choice(verbs)

    # Format entity type
    type_map = {
        "thought": "thought",
        "thinker": "thinker profile",
        "source": "source"
    }
    formatted_type = type_map.get(entity_type, entity_type)

    return f"{verb} {formatted_type}: {name}"


def write_thought(
    title: str,
    theme: str,
    initial_spark: str,
    status: str = "seed",
    related_thinkers: Optional[list] = None,
    related_thoughts: Optional[list] = None,
    current_position: str = "",
    arguments: Optional[list] = None,
    open_questions: Optional[list] = None,
    use_folder: bool = False,
    auto_commit: bool = True
) -> str:
    """
    Create new thought exploration.

    Args:
        title: Thought title
        theme: One of VALID_THEMES
        initial_spark: What triggered this thought
        status: One of VALID_STATUSES (default: 'seed')
        related_thinkers: List of thinker slugs
        related_thoughts: List of thought paths
        current_position: Current view on the topic
        arguments: List of supporting arguments
        open_questions: List of questions to explore
        use_folder: If True, create folder structure; if False, single file
        auto_commit: Whether to auto-commit changes

    Returns:
        Path to created thought file/folder
    """
    # Validate theme
    if theme not in VALID_THEMES:
        raise ValueError(f"Invalid theme: {theme}. Must be one of {VALID_THEMES}")

    # Validate status
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}. Must be one of {VALID_STATUSES}")

    # Generate slug and path
    today = _today()
    slug = _slugify(title)

    if use_folder:
        thought_dir = THOUGHTS_PATH / theme / f"{today}_{slug}"
        thought_dir.mkdir(parents=True, exist_ok=True)
        thought_path = thought_dir / "thought.md"
    else:
        theme_dir = THOUGHTS_PATH / theme
        theme_dir.mkdir(parents=True, exist_ok=True)
        thought_path = theme_dir / f"{today}_{slug}.md"

    # Read and fill template
    template = _read_template("thought.md")

    # Build replacements
    replacements = {
        "thought_title": title,
        "theme": theme,
        "date": today,
        "what_triggered_this_thought": initial_spark,
        "my_current_view": current_position or "To be developed.",
    }

    content = _fill_template(template, replacements)

    # Update frontmatter
    frontmatter_updates = [
        (r'status: seed', f'status: {status}'),
        (r'started: "{{date: YYYY-MM-DD}}"', f'started: "{today}"'),
        (r'last_updated: "{{date: YYYY-MM-DD}}"', f'last_updated: "{today}"'),
    ]

    for pattern, replacement in frontmatter_updates:
        content = re.sub(pattern, replacement, content)

    # Handle related_thinkers
    if related_thinkers:
        thinkers_yaml = "\n".join(f"  - {t}" for t in related_thinkers)
        content = re.sub(r'related_thinkers: \[\]', f'related_thinkers:\n{thinkers_yaml}', content)

    # Handle related_thoughts
    if related_thoughts:
        thoughts_yaml = "\n".join(f"  - {t}" for t in related_thoughts)
        content = re.sub(r'related_thoughts: \[\]', f'related_thoughts:\n{thoughts_yaml}', content)

    # Handle arguments
    if arguments:
        args_text = "\n".join(f"{i+1}. {arg}" for i, arg in enumerate(arguments))
        content = re.sub(
            r'## Supporting Arguments\n\n1\. \{\{argument_1\}\}\n2\. \{\{argument_2\}\}\n3\. \{\{argument_3\}\}',
            f'## Supporting Arguments\n\n{args_text}',
            content
        )

    # Handle open_questions
    if open_questions:
        questions_text = "\n".join(f"- [ ] {q}" for q in open_questions)
        content = re.sub(
            r'## Open Questions\n\n- \[ \] \{\{question_1\}\}\n- \[ \] \{\{question_2\}\}',
            f'## Open Questions\n\n{questions_text}',
            content
        )

    # Clean up remaining placeholders
    content = re.sub(r'\{\{[^}]+\}\}', '', content)

    # Write file
    thought_path.write_text(content)

    # Auto-commit
    if auto_commit:
        commit_msg = generate_commit_message("create", "thought", title)
        _git_commit(str(thought_path), commit_msg)

    return str(thought_path)


def write_thinker(
    name: str,
    thinker_type: str = "philosopher",
    era: str = "contemporary",
    traditions: Optional[list] = None,
    key_works: Optional[list] = None,
    themes: Optional[list] = None,
    core_ideas: Optional[list] = None,
    relevance: str = "",
    auto_commit: bool = True
) -> str:
    """
    Create new thinker profile structure.

    Args:
        name: Full name (e.g., "Karl Friston")
        thinker_type: philosopher, author, scientist, etc.
        era: ancient, medieval, modern, contemporary
        traditions: List of philosophical traditions
        key_works: List of major works
        themes: List of relevant themes
        core_ideas: List of core philosophical ideas
        relevance: Why this thinker matters to you
        auto_commit: Whether to auto-commit changes

    Returns:
        Path to created thinker folder
    """
    # Generate slug
    slug = _slugify(name)
    thinker_dir = THINKERS_PATH / slug

    # Create folder
    thinker_dir.mkdir(parents=True, exist_ok=True)

    today = _today()

    # Create profile.md
    profile_template = _read_template("thinker_profile.md")
    profile_replacements = {
        "full_name": name,
        "thinker_type": thinker_type,
        "era": era,
        "traditions": ", ".join(traditions) if traditions else "",
        "personal_relevance_why_this_thinker_matters_to_me": relevance or "To be explored.",
        "date": today,
    }
    profile_content = _fill_template(profile_template, profile_replacements)

    # Update frontmatter lists
    if traditions:
        traditions_yaml = "\n".join(f"  - {t}" for t in traditions)
        profile_content = re.sub(r'traditions: \[\]', f'traditions:\n{traditions_yaml}', profile_content)

    if key_works:
        works_yaml = "\n".join(f"  - {w}" for w in key_works)
        profile_content = re.sub(r'key_works: \[\]', f'key_works:\n{works_yaml}', profile_content)

    if themes:
        themes_yaml = "\n".join(f"  - {t}" for t in themes)
        profile_content = re.sub(r'themes: \[\]', f'themes:\n{themes_yaml}', profile_content)

    # Handle core_ideas
    if core_ideas:
        ideas_text = "\n".join(f"- {idea}" for idea in core_ideas)
        profile_content = re.sub(
            r'## Core Ideas\n\n- \{\{core_idea_1\}\}\n- \{\{core_idea_2\}\}\n- \{\{core_idea_3\}\}',
            f'## Core Ideas\n\n{ideas_text}',
            profile_content
        )

    # Clean placeholders
    profile_content = re.sub(r'\{\{[^}]+\}\}', '', profile_content)

    profile_path = thinker_dir / "profile.md"
    profile_path.write_text(profile_content)

    # Create notes.md
    notes_template = _read_template("thinker_notes.md")
    notes_content = _fill_template(notes_template, {"full_name": name, "name": name.split()[-1]})
    notes_content = re.sub(r'\{\{[^}]+\}\}', '', notes_content)
    (thinker_dir / "notes.md").write_text(notes_content)

    # Create reflections.md
    reflections_template = _read_template("thinker_reflections.md")
    reflections_content = _fill_template(reflections_template, {"full_name": name, "name": name.split()[-1]})
    reflections_content = re.sub(r'\{\{[^}]+\}\}', '', reflections_content)
    (thinker_dir / "reflections.md").write_text(reflections_content)

    # Create references.md
    references_template = _read_template("thinker_references.md")
    references_content = _fill_template(references_template, {"full_name": name, "name": name.split()[-1]})
    references_content = re.sub(r'\{\{[^}]+\}\}', '', references_content)
    (thinker_dir / "references.md").write_text(references_content)

    # Auto-commit
    if auto_commit:
        commit_msg = generate_commit_message("create", "thinker", name)
        # Stage entire folder
        subprocess.run(
            ["git", "add", str(thinker_dir)],
            cwd=REPO_ROOT,
            capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=REPO_ROOT,
            capture_output=True
        )

    return str(thinker_dir)


def write_source(
    title: str,
    author: str,
    source_type: str,
    year: Optional[int] = None,
    themes: Optional[list] = None,
    status: str = "to_read",
    summary: str = "",
    takeaways: Optional[list] = None,
    auto_commit: bool = True
) -> str:
    """
    Create new source entry.

    Args:
        title: Source title
        author: Author name or slug
        source_type: One of VALID_SOURCE_TYPES
        year: Publication year
        themes: List of relevant themes
        status: to_read, reading, read, revisiting
        summary: Brief summary
        takeaways: List of key takeaways
        auto_commit: Whether to auto-commit changes

    Returns:
        Path to created source file
    """
    # Validate source type
    if source_type not in VALID_SOURCE_TYPES:
        raise ValueError(f"Invalid source type: {source_type}. Must be one of {VALID_SOURCE_TYPES}")

    # Generate slug and path
    slug = _slugify(title)

    # Determine subfolder based on type
    type_folders = {
        "book": "books",
        "article": "articles",
        "lecture": "lectures",
        "essay": "articles",
        "podcast": "lectures",
        "conversation": "lectures"
    }
    subfolder = type_folders.get(source_type, "books")

    source_dir = SOURCES_PATH / subfolder
    source_dir.mkdir(parents=True, exist_ok=True)
    source_path = source_dir / f"{slug}.md"

    # Read and fill template
    template = _read_template("source.md")

    today = _today()
    replacements = {
        "source_title": title,
        "author_slug": _slugify(author),
        "author_name": author,
        "source_type": source_type,
        "year": year or "",
        "status": status,
        "rating": "",
        "brief_summary": summary or "To be added.",
        "date": today,
    }

    content = _fill_template(template, replacements)

    # Handle themes
    if themes:
        themes_yaml = "\n".join(f"  - {t}" for t in themes)
        content = re.sub(r'themes: \[\]', f'themes:\n{themes_yaml}', content)

    # Handle takeaways
    if takeaways:
        takeaways_text = "\n".join(f"{i+1}. {t}" for i, t in enumerate(takeaways))
        content = re.sub(
            r'## Key Takeaways\n\n1\. \{\{takeaway_1\}\}\n2\. \{\{takeaway_2\}\}\n3\. \{\{takeaway_3\}\}',
            f'## Key Takeaways\n\n{takeaways_text}',
            content
        )

    # Clean placeholders
    content = re.sub(r'\{\{[^}]+\}\}', '', content)

    # Write file
    source_path.write_text(content)

    # Auto-commit
    if auto_commit:
        commit_msg = generate_commit_message("create", "source", title)
        _git_commit(str(source_path), commit_msg)

    return str(source_path)


def update_content(
    path: str,
    new_content: str,
    commit_message: Optional[str] = None,
    auto_commit: bool = True
) -> bool:
    """
    Update existing content file.

    Args:
        path: Path to file (relative to repo root or absolute)
        new_content: New file content
        commit_message: Optional custom commit message
        auto_commit: Whether to auto-commit changes

    Returns:
        True if successful, False otherwise
    """
    # Resolve path
    file_path = Path(path)
    if not file_path.is_absolute():
        file_path = REPO_ROOT / path

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Update last_updated in frontmatter if present
    today = _today()
    if 'last_updated:' in new_content:
        new_content = re.sub(
            r'last_updated: "[^"]+"',
            f'last_updated: "{today}"',
            new_content
        )

    # Write content
    file_path.write_text(new_content)

    # Auto-commit
    if auto_commit:
        if not commit_message:
            # Extract entity name from path
            name = file_path.stem
            if name in ["thought", "profile", "notes", "main"]:
                name = file_path.parent.name
            commit_message = generate_commit_message("update", "thought", name)

        return _git_commit(str(file_path), commit_message)

    return True


# Convenience functions for index updates (imported from indices.py when available)
def _update_thoughts_index(thought_path: str, title: str, theme: str, status: str) -> bool:
    """Stub for index update - to be implemented with indices.py integration."""
    # This would be integrated with the indices module
    return True


def _update_thinkers_index(thinker_path: str, name: str, **kwargs) -> bool:
    """Stub for index update - to be implemented with indices.py integration."""
    return True


def _update_sources_index(source_path: str, title: str, **kwargs) -> bool:
    """Stub for index update - to be implemented with indices.py integration."""
    return True


if __name__ == "__main__":
    # Test the module
    print(f"Repository root: {REPO_ROOT}")
    print(f"Knowledge root: {KNOWLEDGE_ROOT}")
    print(f"Templates root: {TEMPLATES_ROOT}")
    print(f"Valid themes: {VALID_THEMES}")
    print(f"Valid source types: {VALID_SOURCE_TYPES}")

    # Test commit message generation
    print("\nSample commit messages:")
    print(f"  Create thought: {generate_commit_message('create', 'thought', 'Consciousness and Time')}")
    print(f"  Update thinker: {generate_commit_message('update', 'thinker', 'Karl Friston')}")
    print(f"  Complete source: {generate_commit_message('complete', 'source', 'Being and Time')}")
