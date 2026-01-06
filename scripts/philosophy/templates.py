"""
Template loading and filling for philosophy repository.

Provides functions to load templates from the templates/philosophy directory
and fill them with variables using simple string replacement.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional


# Template directory path (relative to project root)
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates" / "philosophy"


def load_template(template_name: str) -> str:
    """
    Load a template file from the templates directory.

    Args:
        template_name: Name of the template file (with or without .md extension)

    Returns:
        Template content as string

    Raises:
        FileNotFoundError: If template does not exist
    """
    # Normalize template name
    if not template_name.endswith(".md"):
        template_name = f"{template_name}.md"

    template_path = TEMPLATES_DIR / template_name

    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_name}")

    return template_path.read_text(encoding="utf-8")


def fill_template(template: str, variables: dict) -> str:
    """
    Fill a template with variable values using simple string replacement.

    Supports two placeholder formats:
    - {{variable_name}} - Simple replacement
    - {{date: FORMAT}} - Date replacement with strftime format

    Args:
        template: Template content with {{placeholders}}
        variables: Dictionary of variable name -> value mappings

    Returns:
        Filled template with placeholders replaced
    """
    result = template

    # Handle date placeholders: {{date: YYYY-MM-DD}} etc.
    date_pattern = r"\{\{date:\s*([^}]+)\}\}"
    today = datetime.now()

    def replace_date(match):
        fmt = match.group(1).strip()
        # Convert common format patterns to strftime
        strftime_fmt = (
            fmt.replace("YYYY", "%Y")
            .replace("MM", "%m")
            .replace("DD", "%d")
            .replace("HH", "%H")
            .replace("mm", "%M")
            .replace("ss", "%S")
        )
        return today.strftime(strftime_fmt)

    result = re.sub(date_pattern, replace_date, result)

    # Handle simple variable placeholders: {{variable_name}}
    for key, value in variables.items():
        placeholder = f"{{{{{key}}}}}"
        if value is not None:
            result = result.replace(placeholder, str(value))

    return result


def _slugify(name: str) -> str:
    """Convert a name to a URL-friendly slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "_", slug)
    return slug


def create_thought_from_template(
    title: str,
    theme: str,
    initial_spark: str,
    current_position: str = "",
    **kwargs
) -> str:
    """
    Create a new thought document from the thought template.

    Args:
        title: Title of the thought/exploration
        theme: Theme category (consciousness, free_will, existence, etc.)
        initial_spark: What triggered this thought
        current_position: Current view/position on the topic
        **kwargs: Additional variables to fill in the template

    Returns:
        Filled thought document as string
    """
    template = load_template("thought")

    variables = {
        "thought_title": title,
        "theme": theme,
        "what_triggered_this_thought": initial_spark,
        "my_current_view": current_position or "To be developed.",
        **kwargs
    }

    return fill_template(template, variables)


def create_thinker_from_template(
    name: str,
    thinker_type: str = "philosopher",
    era: str = "contemporary",
    traditions: str = "",
    relevance: str = "",
    **kwargs
) -> dict[str, str]:
    """
    Create thinker documents from all thinker templates.

    Creates a complete thinker folder structure with:
    - profile.md
    - notes.md
    - reflections.md
    - references.md

    Args:
        name: Full name of the thinker
        thinker_type: Type (philosopher, author, psychologist, etc.)
        era: Era (ancient, medieval, modern, contemporary)
        traditions: Philosophical traditions
        relevance: Why this thinker matters to me
        **kwargs: Additional variables for templates

    Returns:
        Dictionary mapping filename -> content for all thinker files
    """
    slug = _slugify(name)
    short_name = name.split()[-1] if " " in name else name

    base_variables = {
        "full_name": name,
        "name": short_name,
        "slug": slug,
        "thinker_type": thinker_type,
        "era": era,
        "traditions": traditions,
        "personal_relevance_why_this_thinker_matters_to_me": relevance or "To be explored.",
        **kwargs
    }

    files = {}

    # Profile
    profile_template = load_template("thinker_profile")
    files["profile.md"] = fill_template(profile_template, base_variables)

    # Notes
    notes_template = load_template("thinker_notes")
    files["notes.md"] = fill_template(notes_template, base_variables)

    # Reflections
    reflections_template = load_template("thinker_reflections")
    files["reflections.md"] = fill_template(reflections_template, base_variables)

    # References
    references_template = load_template("thinker_references")
    files["references.md"] = fill_template(references_template, base_variables)

    return files


def create_source_from_template(
    title: str,
    author: str,
    source_type: str = "book",
    year: Optional[int] = None,
    status: str = "to_read",
    summary: str = "",
    **kwargs
) -> str:
    """
    Create a new source document from the source template.

    Args:
        title: Title of the source
        author: Author name
        source_type: Type (book, article, lecture, essay, podcast, conversation)
        year: Year of publication
        status: Reading status (to_read, reading, read, revisiting)
        summary: Brief summary of the source
        **kwargs: Additional variables to fill in the template

    Returns:
        Filled source document as string
    """
    template = load_template("source")

    author_slug = _slugify(author)
    current_year = datetime.now().year

    variables = {
        "source_title": title,
        "author_name": author,
        "author_slug": author_slug,
        "source_type": source_type,
        "year": year if year is not None else current_year,
        "status": status,
        "rating": kwargs.pop("rating", 0),
        "brief_summary": summary or "To be written.",
        **kwargs
    }

    return fill_template(template, variables)


def create_memory_from_template(
    source_path: str,
    source_title: str,
    source_type: str = "thought",
    **kwargs
) -> str:
    """
    Create a new memory document from the memory template.

    Memory files capture learned corrections and insights about a source file.

    Args:
        source_path: Path to the source file this memory relates to
        source_title: Title of the source
        source_type: Type of source (thought, thinker, source)
        **kwargs: Additional variables to fill in the template

    Returns:
        Filled memory document as string
    """
    template = load_template("memory")

    variables = {
        "source_path": source_path,
        "source_title": source_title,
        "source_type": source_type,
        "count": 0,
        **kwargs
    }

    return fill_template(template, variables)


def list_templates() -> list[str]:
    """
    List all available templates.

    Returns:
        List of template names (without .md extension)
    """
    if not TEMPLATES_DIR.exists():
        return []

    return [
        f.stem for f in TEMPLATES_DIR.glob("*.md")
        if f.is_file() and not f.name.startswith(".")
    ]
