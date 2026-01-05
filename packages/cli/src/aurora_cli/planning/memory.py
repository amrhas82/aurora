"""Memory-based file path resolution for planning.

Wraps MemoryRetriever to resolve actual file paths from indexed memory.
"""

import logging
from typing import Optional

from aurora_cli.config import Config
from aurora_cli.memory.retrieval import MemoryRetriever
from aurora_cli.planning.models import FileResolution, Subgoal
from aurora_core.store.sqlite import SQLiteStore

logger = logging.getLogger(__name__)


class FilePathResolver:
    """Resolves file paths from memory index for subgoals.

    Wraps MemoryRetriever to provide file path resolution with confidence
    scores for planning tasks. Handles graceful degradation when memory
    is not indexed.
    """

    def __init__(
        self, store: Optional[SQLiteStore] = None, config: Optional[Config] = None
    ) -> None:
        """Initialize file path resolver.

        Args:
            store: SQLite store for memory retrieval (uses default if None)
            config: Configuration object (uses default if None)
        """
        self.config = config or Config()
        self.store = store
        self.retriever = MemoryRetriever(store=store, config=config)

    def resolve_for_subgoal(
        self, subgoal: Subgoal, limit: int = 5
    ) -> list[FileResolution]:
        """Resolve file paths for a subgoal from indexed memory.

        Args:
            subgoal: Subgoal to resolve file paths for
            limit: Maximum number of file paths to return (default 5)

        Returns:
            List of FileResolution objects with paths, line ranges, and confidence
        """
        # Check if memory is indexed
        if not self.has_indexed_memory():
            logger.warning(
                "Memory not indexed. Run 'aur mem index .' for code-aware tasks. "
                "Generating generic paths with low confidence."
            )
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
            path_str = (
                f"{resolution.path} lines {resolution.line_start}-{resolution.line_end}"
            )
        else:
            path_str = resolution.path

        # Add confidence annotation based on thresholds
        if resolution.confidence >= 0.8:
            # High confidence - no annotation needed
            return path_str
        elif resolution.confidence >= 0.6:
            # Medium confidence - suggest it's a suggestion
            return f"{path_str} (suggested)"
        else:
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
            )
        ]
