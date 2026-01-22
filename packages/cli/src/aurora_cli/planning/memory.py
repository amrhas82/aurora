"""Memory-based file path resolution for planning.

Wraps MemoryRetriever to resolve actual file paths from indexed memory.
Provides memory search functionality for goal decomposition context.
"""

import logging
from pathlib import Path as PathLib


# Code file extensions to include in memory search results
CODE_EXTENSIONS = {
    # Python
    ".py",
    ".pyi",
    # JavaScript/TypeScript
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    # Java/JVM
    ".java",
    ".kt",
    ".kts",
    ".scala",
    ".groovy",
    # C/C++
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".cc",
    ".cxx",
    # Go
    ".go",
    # Rust
    ".rs",
    # Ruby
    ".rb",
    # PHP
    ".php",
    # C#
    ".cs",
    # Swift
    ".swift",
    # Shell
    ".sh",
    ".bash",
    ".zsh",
    # SQL
    ".sql",
}


# Directories to exclude from memory search results
EXCLUDED_DIRS = {
    "htmlcov",
    "coverage",
    "__pycache__",
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    ".eggs",
}


def is_code_file(file_path: str) -> bool:
    """Check if a file path is a code file based on extension.

    Args:
        file_path: Path to check

    Returns:
        True if file has a code extension, False otherwise

    """
    path = PathLib(file_path)

    # Exclude files in noise directories
    for part in path.parts:
        if part in EXCLUDED_DIRS:
            return False

    suffix = path.suffix.lower()
    return suffix in CODE_EXTENSIONS


from aurora_cli.config import Config  # noqa: E402
from aurora_cli.memory.retrieval import MemoryRetriever  # noqa: E402
from aurora_cli.planning.models import FileResolution, Subgoal  # noqa: E402
from aurora_core.store.sqlite import SQLiteStore  # noqa: E402


logger = logging.getLogger(__name__)


def search_memory_for_goal(
    goal: str,
    config: Config | None = None,
    limit: int = 10,
    threshold: float = 0.3,
) -> list[tuple[str, float]]:
    """Search indexed memory for files relevant to a goal.

    Searches the memory index for code chunks relevant to the goal keywords,
    returning file paths with relevance scores. Results are deduplicated by
    file path (keeping highest score) and filtered by threshold.

    Args:
        goal: High-level goal description to search for
        config: Configuration object (uses default if None)
        limit: Maximum number of results to return (default: 10)
        threshold: Minimum relevance score threshold (default: 0.3)

    Returns:
        List of (file_path, relevance_score) tuples, sorted by score descending.
        Returns empty list if memory not indexed or on retrieval error.

    Example:
        >>> results = search_memory_for_goal("Add OAuth2 authentication", limit=5)
        >>> for path, score in results:
        ...     print(f"{path}: {score:.2f}")
        src/auth/oauth.py: 0.85
        src/auth/jwt.py: 0.72

    """
    # Load config if not provided
    if config is None:
        config = Config()

    # Get database path and check if it exists
    from pathlib import Path

    db_path = Path(config.get_db_path())
    if not db_path.exists():
        return []

    # Create store and retriever
    try:
        store = SQLiteStore(str(db_path))
        retriever = MemoryRetriever(store=store, config=config)
    except Exception as e:
        logger.warning(f"Failed to open memory store: {e}")
        return []

    # Check if memory is indexed (silently return empty - caller handles messaging)
    if not retriever.has_indexed_memory():
        return []

    # Retrieve relevant code chunks
    # Get 4x limit to account for deduplication + code-only filtering
    try:
        chunks = retriever.retrieve(goal, limit=limit * 4)
    except Exception as e:
        logger.warning(f"Failed to retrieve from memory: {e}")
        return []

    # Deduplicate by file path (keep highest score)
    # Note: chunks can be either CodeChunk objects or dicts depending on retriever version
    seen_paths: dict[str, float] = {}
    for chunk in chunks:
        # Handle both CodeChunk objects and dicts
        if isinstance(chunk, dict):
            # file_path may be in metadata for dict results
            metadata = chunk.get("metadata", {})
            file_path = chunk.get("file_path") or metadata.get("file_path", "")
            # Score might be in different fields
            score = chunk.get("hybrid_score", chunk.get("score", chunk.get("semantic_score", 0.0)))
        else:
            # CodeChunk object
            file_path = getattr(chunk, "file_path", "")
            score = getattr(chunk, "score", getattr(chunk, "hybrid_score", 0.0))

        if not file_path:
            continue

        # Filter to code files only (exclude docs, markdown, config)
        if not is_code_file(file_path):
            continue

        if file_path not in seen_paths:
            seen_paths[file_path] = score
        else:
            # Keep highest score
            seen_paths[file_path] = max(seen_paths[file_path], score)

    # Filter by threshold and convert to list of tuples
    results = [(path, score) for path, score in seen_paths.items() if score >= threshold]

    # Sort by score descending
    results.sort(key=lambda x: x[1], reverse=True)

    # Limit results
    return results[:limit]


class FilePathResolver:
    """Resolves file paths from memory index for subgoals.

    Wraps MemoryRetriever to provide file path resolution with confidence
    scores for planning tasks. Handles graceful degradation when memory
    is not indexed.
    """

    # Class-level flag to warn only once per session
    _warned_not_indexed = False

    def __init__(self, store: SQLiteStore | None = None, config: Config | None = None) -> None:
        """Initialize file path resolver.

        Args:
            store: SQLite store for memory retrieval (uses default if None)
            config: Configuration object (uses default if None)

        """
        self.config = config or Config()
        self.store = store
        self.retriever = MemoryRetriever(store=store, config=config)

    def resolve_for_subgoal(self, subgoal: Subgoal, limit: int = 5) -> list[FileResolution]:
        """Resolve file paths for a subgoal from indexed memory.

        Args:
            subgoal: Subgoal to resolve file paths for
            limit: Maximum number of file paths to return (default 5)

        Returns:
            List of FileResolution objects with paths, line ranges, and confidence

        """
        # Check if memory is indexed (silently degrade - caller shows user message)
        if not self.has_indexed_memory():
            return self._generate_generic_paths(subgoal)

        # Retrieve relevant code chunks from memory
        try:
            chunks = self.retriever.retrieve(subgoal.description, limit=limit)
        except Exception as e:
            logger.warning(f"Failed to retrieve from memory: {e}. Using generic paths.")
            return self._generate_generic_paths(subgoal)

        # Convert chunks to FileResolution objects
        resolutions = []
        for chunk in chunks:
            resolution = FileResolution(
                path=chunk.file_path,
                line_start=chunk.line_start,
                line_end=chunk.line_end,
                confidence=chunk.score,
            )
            resolutions.append(resolution)

        return resolutions

    def has_indexed_memory(self) -> bool:
        """Check if memory has been indexed.

        Returns:
            True if memory is indexed, False otherwise

        """
        return self.retriever.has_indexed_memory()

    def format_path_with_confidence(self, resolution: FileResolution) -> str:
        """Format file path with confidence annotation for display.

        Formatting rules:
        - High confidence (>= 0.8): No annotation
        - Medium confidence (0.6-0.8): "(suggested)"
        - Low confidence (< 0.6): "(low confidence)"

        Args:
            resolution: FileResolution to format

        Returns:
            Formatted string for display

        """
        # Build base path string
        if resolution.line_start is not None and resolution.line_end is not None:
            path_str = f"{resolution.path} lines {resolution.line_start}-{resolution.line_end}"
        else:
            path_str = resolution.path

        # Add confidence annotation based on thresholds
        if resolution.confidence >= 0.8:
            # High confidence - no annotation needed
            return path_str
        if resolution.confidence >= 0.6:
            # Medium confidence - suggest it's a suggestion
            return f"{path_str} (suggested)"
        # Low confidence - warn user
        return f"{path_str} (low confidence)"

    def _generate_generic_paths(self, subgoal: Subgoal) -> list[FileResolution]:
        """Generate generic file paths when memory not indexed.

        Creates placeholder paths based on subgoal title, marked with
        low confidence to indicate they need manual resolution.

        Args:
            subgoal: Subgoal to generate generic paths for

        Returns:
            List of generic FileResolution objects with low confidence

        """
        # Create a slug from the subgoal title
        slug = subgoal.title.lower().replace(" ", "_")
        # Keep only alphanumeric and underscores
        slug = "".join(c for c in slug if c.isalnum() or c == "_")

        # Generate generic path pattern
        generic_path = f"src/{slug}.py"

        return [
            FileResolution(
                path=generic_path,
                line_start=None,
                line_end=None,
                confidence=0.1,  # Very low confidence to mark as placeholder
            ),
        ]
