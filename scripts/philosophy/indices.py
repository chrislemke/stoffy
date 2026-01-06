"""
Philosophy Repository Index Manager

Manages YAML index files for the philosophy repository:
- thoughts.yaml: Thought explorations registry
- thinkers.yaml: Philosopher profiles
- sources.yaml: Reference materials
- themes.yaml: Thematic categories

All operations work on local files. Use git to sync with remote.
"""

from pathlib import Path
from datetime import date
from typing import Optional
import yaml


# Repository paths
REPO_ROOT = Path(__file__).parent.parent.parent
INDICES_DIR = REPO_ROOT / "indices" / "philosophy"

# Valid status values
THOUGHT_STATUSES = [
    "seed", "exploring", "developing", "crystallized", "challenged", "integrated", "archived"
]
SOURCE_STATUSES = ["to_read", "reading", "read", "revisiting"]


def _get_index_path(index_name: str) -> Path:
    """Get the full path for an index file."""
    return INDICES_DIR / f"{index_name}.yaml"


def load_index(index_name: str) -> dict:
    """
    Load a YAML index file.

    Args:
        index_name: Name of the index (thoughts, thinkers, sources, themes, etc.)

    Returns:
        Dict containing the parsed YAML content.

    Raises:
        FileNotFoundError: If index file doesn't exist.
        yaml.YAMLError: If YAML parsing fails.
    """
    path = _get_index_path(index_name)
    if not path.exists():
        raise FileNotFoundError(f"Index file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_index(index_name: str, data: dict) -> bool:
    """
    Save a YAML index file.

    Args:
        index_name: Name of the index.
        data: Dict to serialize to YAML.

    Returns:
        True if save succeeded.
    """
    path = _get_index_path(index_name)

    # Update meta.last_updated if present
    if "meta" in data:
        data["meta"]["last_updated"] = date.today().isoformat()

    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(
            data,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )
    return True


def add_thought(thought_data: dict) -> bool:
    """
    Add a new thought entry to thoughts.yaml.

    Args:
        thought_data: Dict with required keys:
            - id: str (snake_case identifier)
            - title: str
            - theme: str (must match themes.yaml)
            - path: str (relative path from repo root)
            - key_insight: str (optional, can be None)
        Optional keys:
            - status: str (default: "seed")
            - related_thinkers: list[str]
            - started: str (ISO date, default: today)
            - next_step: str

    Returns:
        True if thought was added successfully.

    Raises:
        ValueError: If required fields missing or invalid.
    """
    required = ["id", "title", "theme", "path"]
    for field in required:
        if field not in thought_data:
            raise ValueError(f"Missing required field: {field}")

    thought_id = thought_data.pop("id")
    status = thought_data.get("status", "seed")

    if status not in THOUGHT_STATUSES:
        raise ValueError(f"Invalid status: {status}. Must be one of {THOUGHT_STATUSES}")

    # Load current index
    data = load_index("thoughts")

    # Check if thought already exists
    if thought_id in data.get("thoughts", {}):
        raise ValueError(f"Thought already exists: {thought_id}")

    # Build thought entry
    entry = {
        "title": thought_data["title"],
        "theme": thought_data["theme"],
        "status": status,
        "path": thought_data["path"],
        "related_thinkers": thought_data.get("related_thinkers", []),
        "started": thought_data.get("started", date.today().isoformat()),
        "key_insight": thought_data.get("key_insight"),
        "next_step": thought_data.get("next_step"),
    }

    # Remove None values
    entry = {k: v for k, v in entry.items() if v is not None}

    # Add to index
    if "thoughts" not in data:
        data["thoughts"] = {}
    data["thoughts"][thought_id] = entry

    # Update count
    if "meta" in data:
        data["meta"]["count"] = len(data["thoughts"])

    # Add changelog entry
    if "changelog" not in data:
        data["changelog"] = []
    data["changelog"].append({
        "date": date.today().isoformat(),
        "change": f"Added thought: {thought_data['title']}"
    })

    return save_index("thoughts", data)


def add_thinker(thinker_data: dict) -> bool:
    """
    Add a new thinker entry to thinkers.yaml.

    Args:
        thinker_data: Dict with required keys:
            - id: str (snake_case identifier)
            - path: str (relative path from repo root)
            - type: str (philosopher, author, cognitive_scientist, etc.)
            - era: str (ancient, medieval, modern, contemporary)
            - traditions: list[str]
            - key_works: list[str]
            - themes: list[str]
            - notes: str

    Returns:
        True if thinker was added successfully.

    Raises:
        ValueError: If required fields missing.
    """
    required = ["id", "path", "type", "era", "traditions", "key_works", "themes", "notes"]
    for field in required:
        if field not in thinker_data:
            raise ValueError(f"Missing required field: {field}")

    thinker_id = thinker_data.pop("id")

    # Load current index
    data = load_index("thinkers")

    # Check if thinker already exists
    if thinker_id in data.get("thinkers", {}):
        raise ValueError(f"Thinker already exists: {thinker_id}")

    # Build thinker entry
    entry = {
        "path": thinker_data["path"],
        "type": thinker_data["type"],
        "era": thinker_data["era"],
        "traditions": thinker_data["traditions"],
        "key_works": thinker_data["key_works"],
        "themes": thinker_data["themes"],
        "notes": thinker_data["notes"],
    }

    # Optional fields
    for opt in ["birth_year", "death_year", "influence"]:
        if opt in thinker_data:
            entry[opt] = thinker_data[opt]

    # Add to index
    if "thinkers" not in data:
        data["thinkers"] = {}
    data["thinkers"][thinker_id] = entry

    # Update count
    if "meta" in data:
        data["meta"]["count"] = len(data["thinkers"])

    # Add changelog entry
    if "changelog" not in data:
        data["changelog"] = []
    data["changelog"].append({
        "date": date.today().isoformat(),
        "change": f"Added thinker: {thinker_id}"
    })

    return save_index("thinkers", data)


def add_source(source_data: dict) -> bool:
    """
    Add a new source entry to sources.yaml.

    Args:
        source_data: Dict with required keys:
            - id: str (snake_case identifier)
            - path: str (relative path from repo root)
            - type: str (book, article, lecture, essay, podcast, conversation)
            - author: str or list[str]
            - year: int
            - themes: list[str]
            - status: str (to_read, reading, read, revisiting)
            - key_takeaways: str

    Returns:
        True if source was added successfully.

    Raises:
        ValueError: If required fields missing or invalid.
    """
    required = ["id", "path", "type", "author", "year", "themes", "status", "key_takeaways"]
    for field in required:
        if field not in source_data:
            raise ValueError(f"Missing required field: {field}")

    source_id = source_data.pop("id")
    status = source_data["status"]

    if status not in SOURCE_STATUSES:
        raise ValueError(f"Invalid status: {status}. Must be one of {SOURCE_STATUSES}")

    # Load current index
    data = load_index("sources")

    # Check if source already exists
    if source_id in data.get("sources", {}):
        raise ValueError(f"Source already exists: {source_id}")

    # Build source entry
    entry = {
        "path": source_data["path"],
        "type": source_data["type"],
        "author": source_data["author"],
        "year": source_data["year"],
        "themes": source_data["themes"],
        "status": status,
        "key_takeaways": source_data["key_takeaways"],
    }

    # Add to index
    if "sources" not in data:
        data["sources"] = {}
    data["sources"][source_id] = entry

    # Update count
    if "meta" in data:
        data["meta"]["count"] = len(data["sources"])

    # Add changelog entry
    if "changelog" not in data:
        data["changelog"] = []
    data["changelog"].append({
        "date": date.today().isoformat(),
        "change": f"Added source: {source_id}"
    })

    return save_index("sources", data)


def update_thought_status(thought_id: str, new_status: str) -> bool:
    """
    Update the status of an existing thought.

    Args:
        thought_id: The thought identifier (snake_case).
        new_status: New status value.

    Returns:
        True if update succeeded.

    Raises:
        ValueError: If thought not found or invalid status.
    """
    if new_status not in THOUGHT_STATUSES:
        raise ValueError(f"Invalid status: {new_status}. Must be one of {THOUGHT_STATUSES}")

    data = load_index("thoughts")

    if thought_id not in data.get("thoughts", {}):
        raise ValueError(f"Thought not found: {thought_id}")

    old_status = data["thoughts"][thought_id].get("status", "unknown")
    data["thoughts"][thought_id]["status"] = new_status

    # Add changelog entry
    if "changelog" not in data:
        data["changelog"] = []
    data["changelog"].append({
        "date": date.today().isoformat(),
        "change": f"Updated thought status: {thought_id} ({old_status} -> {new_status})"
    })

    return save_index("thoughts", data)


def _normalize_query(query: str) -> list[str]:
    """
    Normalize a query into multiple search variants.
    Handles spaces, underscores, and common variations.
    """
    query_lower = query.lower().strip()
    variants = {query_lower}
    # Add space/underscore variants
    variants.add(query_lower.replace(" ", "_"))
    variants.add(query_lower.replace("_", " "))
    return list(variants)


def find_thought(query: str) -> list[dict]:
    """
    Search for thoughts by title, key_insight, theme, or ID.

    Args:
        query: Search string (case-insensitive substring match).
               Handles both "free will" and "free_will" formats.

    Returns:
        List of matching thought entries with their IDs.
    """
    data = load_index("thoughts")
    results = []
    queries = _normalize_query(query)

    for thought_id, thought in data.get("thoughts", {}).items():
        thought_id_lower = thought_id.lower()
        title = thought.get("title", "").lower()
        key_insight = thought.get("key_insight", "").lower() if thought.get("key_insight") else ""
        theme = thought.get("theme", "").lower()

        for q in queries:
            if q in thought_id_lower or q in title or q in key_insight or q in theme:
                results.append({"id": thought_id, **thought})
                break  # Avoid duplicates

    return results


def find_thinker(query: str) -> list[dict]:
    """
    Search for thinkers by name, era, traditions, or themes.

    Args:
        query: Search string (case-insensitive substring match).

    Returns:
        List of matching thinker entries with their IDs.
    """
    data = load_index("thinkers")
    results = []
    query_lower = query.lower()

    for thinker_id, thinker in data.get("thinkers", {}).items():
        # Search in ID (name)
        if query_lower in thinker_id.lower():
            results.append({"id": thinker_id, **thinker})
            continue

        # Search in era
        if query_lower in thinker.get("era", "").lower():
            results.append({"id": thinker_id, **thinker})
            continue

        # Search in traditions
        traditions = " ".join(thinker.get("traditions", [])).lower()
        if query_lower in traditions:
            results.append({"id": thinker_id, **thinker})
            continue

        # Search in themes
        themes = " ".join(thinker.get("themes", [])).lower()
        if query_lower in themes:
            results.append({"id": thinker_id, **thinker})
            continue

        # Search in notes
        if query_lower in thinker.get("notes", "").lower():
            results.append({"id": thinker_id, **thinker})
            continue

    return results


def find_source(query: str) -> list[dict]:
    """
    Search for sources by title (id), author, or themes.

    Args:
        query: Search string (case-insensitive substring match).

    Returns:
        List of matching source entries with their IDs.
    """
    data = load_index("sources")
    results = []
    query_lower = query.lower()

    for source_id, source in data.get("sources", {}).items():
        # Search in ID (title)
        if query_lower in source_id.lower():
            results.append({"id": source_id, **source})
            continue

        # Search in author
        author = source.get("author", "")
        if isinstance(author, list):
            author = " ".join(author)
        if query_lower in author.lower():
            results.append({"id": source_id, **source})
            continue

        # Search in themes
        themes = " ".join(source.get("themes", [])).lower()
        if query_lower in themes:
            results.append({"id": source_id, **source})
            continue

        # Search in key_takeaways
        if query_lower in source.get("key_takeaways", "").lower():
            results.append({"id": source_id, **source})
            continue

    return results


def get_thoughts_by_status(status: str) -> list[dict]:
    """
    Get all thoughts with a specific status.

    Args:
        status: Status to filter by.

    Returns:
        List of matching thought entries with their IDs.
    """
    if status not in THOUGHT_STATUSES:
        raise ValueError(f"Invalid status: {status}. Must be one of {THOUGHT_STATUSES}")

    data = load_index("thoughts")
    results = []

    for thought_id, thought in data.get("thoughts", {}).items():
        if thought.get("status") == status:
            results.append({"id": thought_id, **thought})

    return results


def get_thoughts_by_theme(theme: str) -> list[dict]:
    """
    Get all thoughts for a specific theme.

    Args:
        theme: Theme to filter by.

    Returns:
        List of matching thought entries with their IDs.
    """
    data = load_index("thoughts")
    results = []

    for thought_id, thought in data.get("thoughts", {}).items():
        if thought.get("theme") == theme:
            results.append({"id": thought_id, **thought})

    return results


def get_thinkers_by_era(era: str) -> list[dict]:
    """
    Get all thinkers from a specific era.

    Args:
        era: Era to filter by (ancient, medieval, modern, contemporary).

    Returns:
        List of matching thinker entries with their IDs.
    """
    data = load_index("thinkers")
    results = []

    for thinker_id, thinker in data.get("thinkers", {}).items():
        if thinker.get("era") == era:
            results.append({"id": thinker_id, **thinker})

    return results


def get_sources_by_status(status: str) -> list[dict]:
    """
    Get all sources with a specific status.

    Args:
        status: Status to filter by (to_read, reading, read, revisiting).

    Returns:
        List of matching source entries with their IDs.
    """
    if status not in SOURCE_STATUSES:
        raise ValueError(f"Invalid status: {status}. Must be one of {SOURCE_STATUSES}")

    data = load_index("sources")
    results = []

    for source_id, source in data.get("sources", {}).items():
        if source.get("status") == status:
            results.append({"id": source_id, **source})

    return results


def link_thought_to_thinker(thought_id: str, thinker_id: str) -> bool:
    """
    Add a thinker to a thought's related_thinkers list.

    Args:
        thought_id: The thought identifier.
        thinker_id: The thinker identifier to add.

    Returns:
        True if link was added.

    Raises:
        ValueError: If thought or thinker not found.
    """
    # Verify thinker exists
    thinkers_data = load_index("thinkers")
    if thinker_id not in thinkers_data.get("thinkers", {}):
        raise ValueError(f"Thinker not found: {thinker_id}")

    # Load and update thought
    data = load_index("thoughts")
    if thought_id not in data.get("thoughts", {}):
        raise ValueError(f"Thought not found: {thought_id}")

    thought = data["thoughts"][thought_id]
    if "related_thinkers" not in thought:
        thought["related_thinkers"] = []

    if thinker_id not in thought["related_thinkers"]:
        thought["related_thinkers"].append(thinker_id)

        # Add changelog entry
        if "changelog" not in data:
            data["changelog"] = []
        data["changelog"].append({
            "date": date.today().isoformat(),
            "change": f"Linked thinker {thinker_id} to thought {thought_id}"
        })

        return save_index("thoughts", data)

    return True  # Already linked


def get_index_stats() -> dict:
    """
    Get statistics about all indices.

    Returns:
        Dict with counts and metadata for each index.
    """
    stats = {}

    for index_name in ["thoughts", "thinkers", "sources", "themes"]:
        try:
            data = load_index(index_name)
            meta = data.get("meta", {})
            stats[index_name] = {
                "count": meta.get("count", len(data.get(index_name, {}))),
                "version": meta.get("version", "unknown"),
                "last_updated": meta.get("last_updated", "unknown"),
            }
        except FileNotFoundError:
            stats[index_name] = {"error": "Index not found"}

    return stats
