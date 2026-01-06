"""
Philosophy Repository Integration for Stoffy Consciousness

Seamless integration hooks between Stoffy and the external philosophy repository.
Stoffy can automatically access this repository when thinking philosophically.

Usage:
    from scripts.philosophy.integration import (
        should_activate,
        get_context_for_topic,
        suggest_related_thoughts,
        suggest_related_thinkers,
        capture_thought,
        explore_repository,
    )
"""

from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

# =============================================================================
# Configuration
# =============================================================================

PHILOSOPHY_REPO = Path("/Users/chris/Developer/philosophy")
INDICES_DIR = PHILOSOPHY_REPO / "indices"
THOUGHTS_DIR = PHILOSOPHY_REPO / "thoughts"
THINKERS_DIR = PHILOSOPHY_REPO / "thinkers"
TEMPLATES_DIR = PHILOSOPHY_REPO / "templates"

# =============================================================================
# Philosophical Trigger Detection
# =============================================================================

PHILOSOPHICAL_TRIGGERS = [
    # Core philosophical concepts
    "consciousness",
    "free will",
    "existence",
    "meaning of life",
    "morality",
    "ethics",
    "knowledge",
    "truth",
    "reality",
    "being",
    "nothing",
    "identity",
    "self",
    "mind",
    "awareness",
    "experience",
    "qualia",
    "determinism",
    "agency",
    "virtue",
    "justice",
    # Contemplative phrases
    "I've been thinking",
    "I've been wondering",
    "What if",
    "philosophically",
    "ontologically",
    "epistemologically",
    "metaphysically",
    "it seems to me",
    "I wonder",
    "I believe",
    "my position is",
    "pondering",
    "contemplating",
    "reflecting on",
    # German philosophical terms
    "Dasein",
    "Sein",
    "Nichts",
    "Willensfreiheit",
    "Bewusstsein",
    "Existenz",
    "Potenzialität",
    "Sinnfeld",
    # Technical philosophical terms
    "phenomenology",
    "hermeneutics",
    "dialectic",
    "transcendental",
    "a priori",
    "a posteriori",
    "noumenal",
    "phenomenal",
    "categorical imperative",
    "active inference",
    "free energy principle",
    "Markov blanket",
    # Thinker references
    "according to",
    "argued that",
    "believed that",
    "philosopher",
    "Kant",
    "Hegel",
    "Nietzsche",
    "Heidegger",
    "Sartre",
    "Friston",
    "Dennett",
]

# Theme mapping for auto-detection
THEME_KEYWORDS: dict[str, list[str]] = {
    "life_meaning": [
        "meaning",
        "purpose",
        "fulfillment",
        "worth",
        "value",
        "significance",
        "happiness",
        "good life",
        "flourishing",
        "eudaimonia",
        "absurd",
        "nihilism",
    ],
    "consciousness": [
        "consciousness",
        "mind",
        "awareness",
        "experience",
        "qualia",
        "subjective",
        "mental",
        "perception",
        "self-awareness",
        "phenomenal",
        "intentionality",
        "Bewusstsein",
    ],
    "free_will": [
        "free will",
        "determinism",
        "choice",
        "agency",
        "responsibility",
        "compatibilism",
        "libertarian free will",
        "causation",
        "volition",
        "autonomy",
        "Willensfreiheit",
    ],
    "morality": [
        "moral",
        "ethical",
        "virtue",
        "duty",
        "obligation",
        "right",
        "wrong",
        "good",
        "evil",
        "justice",
        "consequentialism",
        "deontology",
    ],
    "existence": [
        "existence",
        "being",
        "reality",
        "metaphysics",
        "ontology",
        "nothing",
        "time",
        "space",
        "substance",
        "essence",
        "Dasein",
        "Sein",
        "Nichts",
        "Potenzialität",
    ],
    "knowledge": [
        "knowledge",
        "epistemology",
        "truth",
        "belief",
        "justification",
        "certainty",
        "doubt",
        "skepticism",
        "rationalism",
        "empiricism",
        "a priori",
    ],
}


# =============================================================================
# Core Functions
# =============================================================================


def should_activate(user_message: str) -> bool:
    """
    Detect if philosophy repo should be activated based on message content.

    Args:
        user_message: The incoming message to analyze.

    Returns:
        True if the message contains philosophical content triggers.
    """
    if not user_message:
        return False

    message_lower = user_message.lower()

    # Check direct trigger matches
    for trigger in PHILOSOPHICAL_TRIGGERS:
        if trigger.lower() in message_lower:
            return True

    # Check theme keyword matches (more than 2 matches suggests philosophy)
    match_count = 0
    for theme_keywords in THEME_KEYWORDS.values():
        for keyword in theme_keywords:
            if keyword.lower() in message_lower:
                match_count += 1

    return match_count >= 2


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file safely."""
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _detect_theme(topic: str) -> str | None:
    """Detect the most likely theme for a topic."""
    topic_lower = topic.lower()
    scores: dict[str, int] = {theme: 0 for theme in THEME_KEYWORDS}

    for theme, keywords in THEME_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in topic_lower:
                scores[theme] += 1

    best_theme = max(scores, key=lambda t: scores[t])
    return best_theme if scores[best_theme] > 0 else None


def get_context_for_topic(topic: str) -> dict[str, Any]:
    """
    Get relevant context from repo for a philosophical topic.

    Args:
        topic: The philosophical topic to search for.

    Returns:
        Dictionary with theme info, related thoughts, and thinkers.
    """
    context: dict[str, Any] = {
        "topic": topic,
        "detected_theme": None,
        "theme_info": None,
        "related_thoughts": [],
        "related_thinkers": [],
        "key_questions": [],
    }

    # Detect theme
    theme = _detect_theme(topic)
    context["detected_theme"] = theme

    # Load theme info
    if theme:
        themes_index = _load_yaml(INDICES_DIR / "themes.yaml")
        theme_data = themes_index.get("themes", {}).get(theme, {})
        if theme_data:
            context["theme_info"] = {
                "name": theme,
                "path": theme_data.get("path"),
                "description": theme_data.get("description"),
            }
            context["key_questions"] = theme_data.get("key_questions", [])

    # Find related thoughts
    context["related_thoughts"] = suggest_related_thoughts(topic)[:5]

    # Find related thinkers
    context["related_thinkers"] = suggest_related_thinkers(topic)[:5]

    return context


def suggest_related_thoughts(topic: str) -> list[dict[str, Any]]:
    """
    Find related thoughts in the repository.

    Args:
        topic: The topic to search for.

    Returns:
        List of related thought entries with title, path, status, key_insight.
    """
    thoughts_index = _load_yaml(INDICES_DIR / "thoughts.yaml")
    thoughts = thoughts_index.get("thoughts", {})

    topic_lower = topic.lower()
    results: list[tuple[int, str, dict[str, Any]]] = []

    for thought_id, thought_data in thoughts.items():
        score = 0
        title = thought_data.get("title", "").lower()
        key_insight = thought_data.get("key_insight", "").lower()
        theme = thought_data.get("theme", "").lower()

        # Score based on title match
        if topic_lower in title:
            score += 10

        # Score based on key_insight match
        for word in topic_lower.split():
            if len(word) > 3 and word in key_insight:
                score += 2

        # Score based on theme match
        detected_theme = _detect_theme(topic)
        if detected_theme and theme == detected_theme:
            score += 5

        if score > 0:
            results.append((score, thought_id, thought_data))

    # Sort by score descending
    results.sort(key=lambda x: x[0], reverse=True)

    return [
        {
            "id": thought_id,
            "title": data.get("title"),
            "path": data.get("path"),
            "status": data.get("status"),
            "theme": data.get("theme"),
            "key_insight": data.get("key_insight"),
            "related_thinkers": data.get("related_thinkers", [])[:3],
        }
        for _, thought_id, data in results
    ]


def suggest_related_thinkers(topic: str) -> list[dict[str, Any]]:
    """
    Find relevant thinkers for a topic.

    Args:
        topic: The topic to search for.

    Returns:
        List of thinker entries with name, path, era, traditions, themes.
    """
    thinkers_index = _load_yaml(INDICES_DIR / "thinkers.yaml")
    thinkers = thinkers_index.get("thinkers", {})

    topic_lower = topic.lower()
    detected_theme = _detect_theme(topic)
    results: list[tuple[int, str, dict[str, Any]]] = []

    for thinker_id, thinker_data in thinkers.items():
        score = 0
        thinker_name = thinker_id.replace("_", " ").lower()
        notes = thinker_data.get("notes", "").lower()
        traditions = [t.lower() for t in thinker_data.get("traditions", [])]
        themes = thinker_data.get("themes", [])

        # Score based on name match
        if topic_lower in thinker_name or thinker_name in topic_lower:
            score += 10

        # Score based on notes match
        for word in topic_lower.split():
            if len(word) > 3 and word in notes:
                score += 2

        # Score based on tradition match
        for word in topic_lower.split():
            if any(word in trad for trad in traditions):
                score += 3

        # Score based on theme match
        if detected_theme and detected_theme in themes:
            score += 5

        if score > 0:
            results.append((score, thinker_id, thinker_data))

    # Sort by score descending
    results.sort(key=lambda x: x[0], reverse=True)

    return [
        {
            "id": thinker_id,
            "name": thinker_id.replace("_", " ").title(),
            "path": data.get("path"),
            "era": data.get("era"),
            "traditions": data.get("traditions", []),
            "themes": data.get("themes", []),
            "notes": data.get("notes"),
        }
        for _, thinker_id, data in results
    ]


def capture_thought(
    title: str,
    initial_spark: str,
    theme: str | None = None,
) -> str:
    """
    Quick thought capture - creates a new thought file in the philosophy repo.

    Auto-detects theme if not provided.

    Args:
        title: Title of the thought.
        initial_spark: The initial insight or question.
        theme: Optional theme (auto-detected if not provided).

    Returns:
        Path to the created thought file.
    """
    # Auto-detect theme if not provided
    if theme is None:
        combined_text = f"{title} {initial_spark}"
        theme = _detect_theme(combined_text) or "existence"

    # Generate filename
    date_str = datetime.now().strftime("%Y-%m-%d")
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    filename = f"{date_str}_{slug}.md"

    # Create path
    thought_dir = THOUGHTS_DIR / theme
    thought_dir.mkdir(parents=True, exist_ok=True)
    thought_path = thought_dir / filename

    # Load template
    template_path = TEMPLATES_DIR / "thought.md"
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")
    else:
        template = """---
title: "{title}"
theme: {theme}
status: seed
started: {date}
related_thinkers: []
---

# {title}

## Initial Spark

{initial_spark}

## Development

*To be developed...*

## Connections

*Related thoughts and thinkers to be identified...*

## Next Steps

- [ ] Develop initial insight further
- [ ] Identify related thinkers
- [ ] Connect to existing thoughts
"""

    # Fill template
    content = template.format(
        title=title,
        theme=theme,
        date=date_str,
        initial_spark=initial_spark,
    )

    # Write file
    thought_path.write_text(content, encoding="utf-8")

    return str(thought_path)


def explore_repository() -> dict[str, Any]:
    """
    Get repository overview: counts, recent activity, themes.

    Returns:
        Dictionary with repository statistics and recent activity.
    """
    result: dict[str, Any] = {
        "exists": PHILOSOPHY_REPO.exists(),
        "path": str(PHILOSOPHY_REPO),
        "themes": {},
        "thinkers_count": 0,
        "thoughts_count": 0,
        "thoughts_by_status": {},
        "recent_thoughts": [],
        "crystallized_thoughts": [],
    }

    if not PHILOSOPHY_REPO.exists():
        return result

    # Load indices
    themes_index = _load_yaml(INDICES_DIR / "themes.yaml")
    thoughts_index = _load_yaml(INDICES_DIR / "thoughts.yaml")
    thinkers_index = _load_yaml(INDICES_DIR / "thinkers.yaml")

    # Theme overview
    themes = themes_index.get("themes", {})
    result["themes"] = {
        name: {
            "description": data.get("description"),
            "path": data.get("path"),
            "key_questions": data.get("key_questions", [])[:2],
        }
        for name, data in themes.items()
    }

    # Thinkers count
    thinkers = thinkers_index.get("thinkers", {})
    result["thinkers_count"] = len(thinkers)

    # Thoughts statistics
    thoughts = thoughts_index.get("thoughts", {})
    result["thoughts_count"] = len(thoughts)

    # Count by status
    status_counts: dict[str, int] = {}
    for thought in thoughts.values():
        status = thought.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    result["thoughts_by_status"] = status_counts

    # Recent thoughts (by start date)
    sorted_thoughts = sorted(
        thoughts.items(),
        key=lambda x: x[1].get("started", ""),
        reverse=True,
    )
    result["recent_thoughts"] = [
        {
            "id": tid,
            "title": data.get("title"),
            "theme": data.get("theme"),
            "status": data.get("status"),
            "started": data.get("started"),
        }
        for tid, data in sorted_thoughts[:5]
    ]

    # Crystallized thoughts
    result["crystallized_thoughts"] = [
        {
            "id": tid,
            "title": data.get("title"),
            "theme": data.get("theme"),
            "key_insight": data.get("key_insight"),
        }
        for tid, data in thoughts.items()
        if data.get("status") == "crystallized"
    ]

    return result


# =============================================================================
# Utility Functions
# =============================================================================


def get_thinker_profile(thinker_id: str) -> dict[str, Any] | None:
    """
    Get a specific thinker's profile.

    Args:
        thinker_id: The thinker identifier (e.g., "karl_friston").

    Returns:
        Thinker data or None if not found.
    """
    thinkers_index = _load_yaml(INDICES_DIR / "thinkers.yaml")
    thinkers = thinkers_index.get("thinkers", {})

    # Try exact match
    if thinker_id in thinkers:
        data = thinkers[thinker_id]
        return {
            "id": thinker_id,
            "name": thinker_id.replace("_", " ").title(),
            **data,
        }

    # Try fuzzy match
    thinker_id_lower = thinker_id.lower().replace(" ", "_")
    for tid, data in thinkers.items():
        if tid.lower() == thinker_id_lower:
            return {
                "id": tid,
                "name": tid.replace("_", " ").title(),
                **data,
            }

    return None


def get_thought_details(thought_id: str) -> dict[str, Any] | None:
    """
    Get a specific thought's details.

    Args:
        thought_id: The thought identifier.

    Returns:
        Thought data or None if not found.
    """
    thoughts_index = _load_yaml(INDICES_DIR / "thoughts.yaml")
    thoughts = thoughts_index.get("thoughts", {})

    if thought_id in thoughts:
        return {"id": thought_id, **thoughts[thought_id]}

    # Try fuzzy match
    thought_id_lower = thought_id.lower()
    for tid, data in thoughts.items():
        if tid.lower() == thought_id_lower:
            return {"id": tid, **data}

    return None


def run_ingest(content: str, plan_only: bool = True) -> dict[str, Any]:
    """
    Run the philosophy repo's ingest script on content.

    Args:
        content: Text content to ingest.
        plan_only: If True, only return plan without executing.

    Returns:
        Ingest result dictionary.
    """
    ingest_script = PHILOSOPHY_REPO / "scripts" / "ingest.py"
    if not ingest_script.exists():
        return {"error": "Ingest script not found", "path": str(ingest_script)}

    args = [sys.executable, str(ingest_script), "--text", content, "--json"]
    if plan_only:
        args.append("--plan-only")

    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(PHILOSOPHY_REPO),
        )
        if result.returncode == 0:
            import json

            return json.loads(result.stdout)
        return {"error": result.stderr, "returncode": result.returncode}
    except subprocess.TimeoutExpired:
        return {"error": "Ingest script timed out"}
    except Exception as e:
        return {"error": str(e)}


def list_themes() -> list[dict[str, Any]]:
    """List all available philosophical themes."""
    themes_index = _load_yaml(INDICES_DIR / "themes.yaml")
    themes = themes_index.get("themes", {})

    return [
        {
            "id": theme_id,
            "description": data.get("description"),
            "path": data.get("path"),
            "key_questions": data.get("key_questions", []),
            "status": data.get("status"),
        }
        for theme_id, data in themes.items()
    ]


def list_thoughts_by_status(status: str = "exploring") -> list[dict[str, Any]]:
    """List thoughts filtered by status."""
    thoughts_index = _load_yaml(INDICES_DIR / "thoughts.yaml")
    thoughts = thoughts_index.get("thoughts", {})

    return [
        {
            "id": tid,
            "title": data.get("title"),
            "theme": data.get("theme"),
            "key_insight": data.get("key_insight"),
            "next_step": data.get("next_step"),
        }
        for tid, data in thoughts.items()
        if data.get("status") == status
    ]


# =============================================================================
# Main Entry Point (for testing)
# =============================================================================

if __name__ == "__main__":
    import json

    # Test should_activate
    test_messages = [
        "What is consciousness?",
        "I've been thinking about free will lately",
        "Can you help me with Python code?",
        "The meaning of life seems elusive",
        "Schedule a meeting for tomorrow",
        "Heidegger's concept of Dasein is fascinating",
    ]

    print("=== Testing should_activate ===")
    for msg in test_messages:
        result = should_activate(msg)
        print(f"  '{msg[:40]}...' -> {result}")

    print("\n=== Repository Overview ===")
    overview = explore_repository()
    print(json.dumps(overview, indent=2, default=str))

    print("\n=== Testing get_context_for_topic ===")
    ctx = get_context_for_topic("free will and determinism")
    print(json.dumps(ctx, indent=2, default=str))

    print("\n=== Testing suggest_related_thinkers ===")
    thinkers = suggest_related_thinkers("consciousness")
    for t in thinkers[:3]:
        print(f"  - {t['name']}: {t.get('notes', '')[:60]}...")
