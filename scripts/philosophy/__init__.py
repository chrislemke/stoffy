"""
Philosophy Repository Integration for Stoffy.

This module provides Stoffy with the ability to read from and write to
the philosophy repository (chrisgscott/philosophy on GitHub).

Main interface:
    PhilosophyRepo - High-level API for all philosophy operations

Example:
    from scripts.philosophy import PhilosophyRepo

    repo = PhilosophyRepo()
    thought = repo.read_thought("stoicism/on-impermanence")
    repo.write_thought("On Presence", "mindfulness", "Being here, now...")
"""

import logging
from typing import Optional, Dict, List, Any, Union

# Set up module logger
logger = logging.getLogger("stoffy.philosophy")

# Version
__version__ = "0.1.0"

# Lazy imports to avoid circular dependencies and allow graceful degradation
_repo = None
_indices = None
_templates = None
_content = None
_writer = None
_validator = None
_linker = None
_integration = None


def _import_submodules():
    """Lazy import all submodules."""
    global _repo, _indices, _templates, _content, _writer, _validator, _linker, _integration

    try:
        from . import repo as _repo
    except ImportError:
        logger.debug("repo module not available")

    try:
        from . import indices as _indices
    except ImportError:
        logger.debug("indices module not available")

    try:
        from . import templates as _templates
    except ImportError:
        logger.debug("templates module not available")

    try:
        from . import content as _content
    except ImportError:
        logger.debug("content module not available")

    try:
        from . import writer as _writer
    except ImportError:
        logger.debug("writer module not available")

    try:
        from . import validator as _validator
    except ImportError:
        logger.debug("validator module not available")

    try:
        from . import linker as _linker
    except ImportError:
        logger.debug("linker module not available")

    try:
        from . import integration as _integration
    except ImportError:
        logger.debug("integration module not available")


class PhilosophyRepo:
    """
    Main interface for Stoffy to interact with the philosophy repository.

    This class provides a unified API for reading thoughts, writing new content,
    searching the repository, and managing connections between thoughts and thinkers.

    Attributes:
        owner: GitHub repository owner (default: "chrisgscott")
        repo: GitHub repository name (default: "philosophy")

    Example:
        repo = PhilosophyRepo()

        # Read a thought
        thought = repo.read_thought("stoicism/on-impermanence")

        # Write a new thought
        path = repo.write_thought(
            title="On Presence",
            theme="mindfulness",
            content="Being fully here, in this moment..."
        )

        # Search
        results = repo.search("impermanence")

        # Link thought to thinker
        repo.link("stoicism/on-impermanence", "marcus-aurelius", "strong", "Direct influence")
    """

    def __init__(self, owner: str = "chrisgscott", repo: str = "philosophy"):
        """
        Initialize the PhilosophyRepo.

        Args:
            owner: GitHub username/org that owns the repository
            repo: Repository name
        """
        self.owner = owner
        self.repo = repo
        self._ensure_imports()
        logger.info(f"PhilosophyRepo initialized for {owner}/{repo}")

    def _ensure_imports(self):
        """Ensure submodules are imported."""
        if _repo is None:
            _import_submodules()

    # --- Reading Operations ---

    def read_thought(self, path_or_id: str) -> Dict[str, Any]:
        """
        Read a thought from the repository.

        Args:
            path_or_id: Either a full path (e.g., "thoughts/stoicism/on-impermanence.md")
                       or a short ID (e.g., "stoicism/on-impermanence")

        Returns:
            Dictionary containing:
                - title: The thought's title
                - theme: The philosophical theme
                - content: The main content
                - frontmatter: YAML frontmatter as dict
                - connections: Related thoughts and thinkers
                - path: Full path in repository

        Raises:
            FileNotFoundError: If the thought doesn't exist
        """
        path = self._normalize_thought_path(path_or_id)

        if _content is not None and hasattr(_content, 'read_thought'):
            return _content.read_thought(self.owner, self.repo, path)

        # Fallback: direct GitHub API call
        if _repo is not None and hasattr(_repo, 'get_file_content'):
            raw = _repo.get_file_content(self.owner, self.repo, path)
            return self._parse_thought(raw, path)

        raise NotImplementedError("content or repo module required for read_thought")

    def read_thinker(self, name: str) -> Dict[str, Any]:
        """
        Read a thinker profile from the repository.

        Args:
            name: Thinker name or slug (e.g., "marcus-aurelius" or "Marcus Aurelius")

        Returns:
            Dictionary containing:
                - name: Display name
                - slug: URL-friendly identifier
                - era: Historical era
                - tradition: Philosophical tradition
                - bio: Short biography
                - key_ideas: List of main contributions
                - influenced_by: List of influences
                - influenced: List of those they influenced
                - connections: Related thoughts

        Raises:
            FileNotFoundError: If the thinker doesn't exist
        """
        slug = self._slugify(name)
        path = f"thinkers/{slug}.md"

        if _content is not None and hasattr(_content, 'read_thinker'):
            return _content.read_thinker(self.owner, self.repo, path)

        if _repo is not None and hasattr(_repo, 'get_file_content'):
            raw = _repo.get_file_content(self.owner, self.repo, path)
            return self._parse_thinker(raw, path)

        raise NotImplementedError("content or repo module required for read_thinker")

    # --- Writing Operations ---

    def write_thought(
        self,
        title: str,
        theme: str,
        content: str,
        connections: Optional[List[str]] = None,
        thinkers: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Write a new thought to the repository.

        Args:
            title: The thought's title
            theme: Philosophical theme (determines folder, e.g., "stoicism", "mindfulness")
            content: The main content/body of the thought
            connections: Optional list of related thought paths
            thinkers: Optional list of related thinker slugs
            tags: Optional list of tags

        Returns:
            The path where the thought was created

        Raises:
            ValueError: If validation fails
            PermissionError: If write access is denied
        """
        # Validate
        if _validator is not None and hasattr(_validator, 'validate_thought'):
            _validator.validate_thought(title=title, theme=theme, content=content)

        # Generate path
        slug = self._slugify(title)
        path = f"thoughts/{theme}/{slug}.md"

        # Build document
        if _templates is not None and hasattr(_templates, 'render_thought'):
            document = _templates.render_thought(
                title=title,
                theme=theme,
                content=content,
                connections=connections or [],
                thinkers=thinkers or [],
                tags=tags or []
            )
        else:
            document = self._default_thought_template(
                title, theme, content, connections, thinkers, tags
            )

        # Write
        if _writer is not None and hasattr(_writer, 'write_file'):
            _writer.write_file(self.owner, self.repo, path, document, f"Add thought: {title}")
        elif _repo is not None and hasattr(_repo, 'create_or_update_file'):
            _repo.create_or_update_file(
                self.owner, self.repo, path, document, f"Add thought: {title}"
            )
        else:
            raise NotImplementedError("writer or repo module required for write_thought")

        # Update indices
        if _indices is not None and hasattr(_indices, 'update_thought_index'):
            _indices.update_thought_index(self.owner, self.repo, path, title, theme)

        logger.info(f"Created thought: {path}")
        return path

    def write_thinker(
        self,
        name: str,
        era: Optional[str] = None,
        tradition: Optional[str] = None,
        bio: Optional[str] = None,
        key_ideas: Optional[List[str]] = None,
        influenced_by: Optional[List[str]] = None,
        influenced: Optional[List[str]] = None,
        **extra
    ) -> str:
        """
        Write a new thinker profile to the repository.

        Args:
            name: Thinker's display name
            era: Historical era (e.g., "Ancient", "Modern")
            tradition: Philosophical tradition (e.g., "Stoicism", "Existentialism")
            bio: Short biography
            key_ideas: List of main philosophical contributions
            influenced_by: List of thinker slugs who influenced them
            influenced: List of thinker slugs they influenced
            **extra: Additional profile data

        Returns:
            The path where the thinker was created
        """
        slug = self._slugify(name)
        path = f"thinkers/{slug}.md"

        # Build document
        if _templates is not None and hasattr(_templates, 'render_thinker'):
            document = _templates.render_thinker(
                name=name,
                slug=slug,
                era=era,
                tradition=tradition,
                bio=bio,
                key_ideas=key_ideas or [],
                influenced_by=influenced_by or [],
                influenced=influenced or [],
                **extra
            )
        else:
            document = self._default_thinker_template(
                name, slug, era, tradition, bio, key_ideas, influenced_by, influenced
            )

        # Write
        if _writer is not None and hasattr(_writer, 'write_file'):
            _writer.write_file(self.owner, self.repo, path, document, f"Add thinker: {name}")
        elif _repo is not None and hasattr(_repo, 'create_or_update_file'):
            _repo.create_or_update_file(
                self.owner, self.repo, path, document, f"Add thinker: {name}"
            )
        else:
            raise NotImplementedError("writer or repo module required for write_thinker")

        # Update indices
        if _indices is not None and hasattr(_indices, 'update_thinker_index'):
            _indices.update_thinker_index(self.owner, self.repo, slug, name, tradition)

        logger.info(f"Created thinker: {path}")
        return path

    # --- Search Operations ---

    def search(self, query: str, scope: str = "all") -> Dict[str, Any]:
        """
        Search the philosophy repository.

        Args:
            query: Search query string
            scope: Search scope - "all", "thoughts", "thinkers", or "themes"

        Returns:
            Dictionary containing:
                - thoughts: List of matching thoughts
                - thinkers: List of matching thinkers
                - themes: List of matching themes
                - total: Total number of results
        """
        if _indices is not None and hasattr(_indices, 'search'):
            return _indices.search(self.owner, self.repo, query, scope)

        # Fallback: basic GitHub search
        if _repo is not None and hasattr(_repo, 'search_code'):
            results = _repo.search_code(self.owner, self.repo, query)
            return self._format_search_results(results, scope)

        raise NotImplementedError("indices or repo module required for search")

    def get_overview(self) -> Dict[str, Any]:
        """
        Get an overview of the philosophy repository.

        Returns:
            Dictionary containing:
                - themes: List of all themes with thought counts
                - thinkers: List of all thinkers
                - recent: Recently added or modified content
                - stats: Repository statistics
        """
        if _indices is not None and hasattr(_indices, 'get_overview'):
            return _indices.get_overview(self.owner, self.repo)

        # Fallback: build from directory structure
        if _repo is not None and hasattr(_repo, 'get_tree'):
            tree = _repo.get_tree(self.owner, self.repo)
            return self._build_overview_from_tree(tree)

        raise NotImplementedError("indices or repo module required for get_overview")

    # --- Linking Operations ---

    def link(
        self,
        thought: str,
        thinker: str,
        strength: str = "moderate",
        reasoning: str = ""
    ) -> bool:
        """
        Create a bidirectional link between a thought and a thinker.

        Args:
            thought: Path or ID of the thought
            thinker: Slug or name of the thinker
            strength: Link strength - "strong", "moderate", or "weak"
            reasoning: Brief explanation of the connection

        Returns:
            True if link was created successfully
        """
        thought_path = self._normalize_thought_path(thought)
        thinker_slug = self._slugify(thinker)

        if _linker is not None and hasattr(_linker, 'create_link'):
            return _linker.create_link(
                self.owner, self.repo,
                thought_path, thinker_slug,
                strength, reasoning
            )

        # Fallback: manual linking via file updates
        logger.warning("linker module not available, link not created")
        return False

    # --- Helper Methods ---

    def _normalize_thought_path(self, path_or_id: str) -> str:
        """Convert a thought ID to a full path."""
        if path_or_id.startswith("thoughts/"):
            return path_or_id if path_or_id.endswith(".md") else f"{path_or_id}.md"
        if "/" in path_or_id:
            # Assume it's theme/slug format
            return f"thoughts/{path_or_id}.md"
        # Single slug - need to search for it
        return f"thoughts/{path_or_id}.md"

    def _slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug."""
        import re
        slug = text.lower().strip()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s_]+', '-', slug)
        slug = re.sub(r'-+', '-', slug)
        return slug.strip('-')

    def _parse_thought(self, raw: str, path: str) -> Dict[str, Any]:
        """Parse raw markdown into thought dictionary."""
        frontmatter, content = self._split_frontmatter(raw)
        return {
            "title": frontmatter.get("title", "Untitled"),
            "theme": frontmatter.get("theme", "general"),
            "content": content,
            "frontmatter": frontmatter,
            "connections": frontmatter.get("connections", []),
            "path": path
        }

    def _parse_thinker(self, raw: str, path: str) -> Dict[str, Any]:
        """Parse raw markdown into thinker dictionary."""
        frontmatter, content = self._split_frontmatter(raw)
        return {
            "name": frontmatter.get("name", "Unknown"),
            "slug": path.replace("thinkers/", "").replace(".md", ""),
            "era": frontmatter.get("era"),
            "tradition": frontmatter.get("tradition"),
            "bio": content,
            "key_ideas": frontmatter.get("key_ideas", []),
            "influenced_by": frontmatter.get("influenced_by", []),
            "influenced": frontmatter.get("influenced", []),
            "connections": frontmatter.get("connections", [])
        }

    def _split_frontmatter(self, raw: str) -> tuple:
        """Split YAML frontmatter from content."""
        import yaml
        if raw.startswith("---"):
            parts = raw.split("---", 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1]) or {}
                except yaml.YAMLError:
                    frontmatter = {}
                content = parts[2].strip()
                return frontmatter, content
        return {}, raw

    def _default_thought_template(
        self, title, theme, content, connections, thinkers, tags
    ) -> str:
        """Generate default thought markdown."""
        import yaml
        from datetime import datetime

        frontmatter = {
            "title": title,
            "theme": theme,
            "created": datetime.now().isoformat(),
            "connections": connections or [],
            "thinkers": thinkers or [],
            "tags": tags or []
        }

        return f"""---
{yaml.dump(frontmatter, default_flow_style=False)}---

# {title}

{content}
"""

    def _default_thinker_template(
        self, name, slug, era, tradition, bio, key_ideas, influenced_by, influenced
    ) -> str:
        """Generate default thinker markdown."""
        import yaml

        frontmatter = {
            "name": name,
            "slug": slug,
            "era": era,
            "tradition": tradition,
            "key_ideas": key_ideas or [],
            "influenced_by": influenced_by or [],
            "influenced": influenced or []
        }
        # Remove None values
        frontmatter = {k: v for k, v in frontmatter.items() if v is not None}

        return f"""---
{yaml.dump(frontmatter, default_flow_style=False)}---

# {name}

{bio or ""}
"""

    def _format_search_results(self, results: List, scope: str) -> Dict[str, Any]:
        """Format raw search results."""
        thoughts = []
        thinkers = []

        for item in results:
            path = item.get("path", "")
            if scope in ("all", "thoughts") and path.startswith("thoughts/"):
                thoughts.append(item)
            if scope in ("all", "thinkers") and path.startswith("thinkers/"):
                thinkers.append(item)

        return {
            "thoughts": thoughts,
            "thinkers": thinkers,
            "themes": [],
            "total": len(thoughts) + len(thinkers)
        }

    def _build_overview_from_tree(self, tree: Dict) -> Dict[str, Any]:
        """Build overview from repository tree."""
        themes = {}
        thinkers = []

        for item in tree.get("tree", []):
            path = item.get("path", "")
            if path.startswith("thoughts/") and path.endswith(".md"):
                parts = path.split("/")
                if len(parts) >= 3:
                    theme = parts[1]
                    themes[theme] = themes.get(theme, 0) + 1
            elif path.startswith("thinkers/") and path.endswith(".md"):
                slug = path.replace("thinkers/", "").replace(".md", "")
                thinkers.append(slug)

        return {
            "themes": [{"name": k, "count": v} for k, v in themes.items()],
            "thinkers": thinkers,
            "recent": [],
            "stats": {
                "total_thoughts": sum(themes.values()),
                "total_thinkers": len(thinkers),
                "total_themes": len(themes)
            }
        }


# --- Convenience Functions ---

def read_thought(path_or_id: str, owner: str = "chrisgscott", repo: str = "philosophy") -> Dict[str, Any]:
    """
    Read a thought from the philosophy repository.

    Convenience function that creates a PhilosophyRepo instance.
    For multiple operations, create a PhilosophyRepo instance directly.
    """
    return PhilosophyRepo(owner, repo).read_thought(path_or_id)


def write_thought(
    title: str,
    theme: str,
    content: str,
    owner: str = "chrisgscott",
    repo: str = "philosophy",
    **kwargs
) -> str:
    """
    Write a thought to the philosophy repository.

    Convenience function that creates a PhilosophyRepo instance.
    """
    return PhilosophyRepo(owner, repo).write_thought(title, theme, content, **kwargs)


def search_philosophy(query: str, owner: str = "chrisgscott", repo: str = "philosophy") -> Dict[str, Any]:
    """
    Search the philosophy repository.

    Convenience function that creates a PhilosophyRepo instance.
    """
    return PhilosophyRepo(owner, repo).search(query)


def get_philosophy_overview(owner: str = "chrisgscott", repo: str = "philosophy") -> Dict[str, Any]:
    """
    Get an overview of the philosophy repository.

    Convenience function that creates a PhilosophyRepo instance.
    """
    return PhilosophyRepo(owner, repo).get_overview()


# --- Public API ---

__all__ = [
    # Main class
    "PhilosophyRepo",

    # Convenience functions
    "read_thought",
    "write_thought",
    "search_philosophy",
    "get_philosophy_overview",

    # Version
    "__version__",
]
