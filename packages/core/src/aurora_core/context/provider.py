"""Abstract ContextProvider interface for AURORA context retrieval.

This module defines the interface that all context providers must implement
to supply relevant chunks based on queries.
"""

from abc import ABC, abstractmethod

from aurora_core.chunks.base import Chunk
from aurora_core.types import ChunkID


class ContextProvider(ABC):
    """Abstract interface for context providers.

    Context providers are responsible for:
    - Retrieving relevant chunks based on text queries
    - Updating activation scores based on usage
    - Refreshing cached data when source files change

    Implementations might provide context from:
    - Code repositories (via CodeContextProvider)
    - Documentation databases
    - Reasoning traces
    - External knowledge bases
    """

    @abstractmethod
    def retrieve(self, query: str, limit: int = 10) -> list[Chunk]:
        """Retrieve relevant chunks matching the query.

        Args:
            query: Natural language query or keywords
            limit: Maximum number of chunks to return (default: 10)

        Returns:
            List of relevant chunks, ordered by relevance (highest first)
            Returns empty list if no matches found

        Raises:
            ValueError: If query is empty or limit is invalid
            StorageError: If underlying storage access fails

        """

    @abstractmethod
    def update(self, chunk_id: ChunkID, activation_delta: float) -> None:
        """Update activation score for a chunk based on usage.

        This method is called when a chunk is accessed or used, allowing
        the provider to track relevance over time. Positive deltas indicate
        usage, negative deltas represent decay.

        Args:
            chunk_id: Chunk to update
            activation_delta: Amount to adjust activation score
                            (positive for boost, negative for decay)

        Raises:
            ChunkNotFoundError: If chunk_id does not exist
            StorageError: If update operation fails

        """

    @abstractmethod
    def refresh(self) -> None:
        """Refresh cached data and re-index changed sources.

        This method should:
        - Check modification times of source files
        - Invalidate stale cache entries
        - Re-parse and re-index changed files
        - Update chunk relationships

        Implementations should be idempotent - calling multiple times
        should be safe and not cause duplicate work.

        Raises:
            StorageError: If refresh operation fails

        """


__all__ = ["ContextProvider"]
