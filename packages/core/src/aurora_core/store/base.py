"""Abstract storage interface for AURORA chunks.

This module defines the base Store interface that all storage implementations
must implement, ensuring consistent behavior across SQLite, in-memory, and
future storage backends.
"""

from abc import ABC, abstractmethod
from datetime import datetime

# Forward reference to avoid circular imports - Chunk will be defined in chunks module
from typing import TYPE_CHECKING, Any, Optional


if TYPE_CHECKING:
    from aurora_core.chunks.base import Chunk

from aurora_core.types import ChunkID


class Store(ABC):
    """Abstract storage interface for AURORA chunks.

    This interface defines the contract that all storage implementations must
    follow. It provides methods for:
    - Storing and retrieving chunks
    - Managing activation scores for spreading activation
    - Tracking relationships between chunks
    - Querying based on activation thresholds

    Implementations MUST be thread-safe and handle errors gracefully.
    """

    @abstractmethod
    def save_chunk(self, chunk: "Chunk") -> bool:
        """Save a chunk to storage.

        Args:
            chunk: The chunk to save. Must have a valid ID and pass validation.

        Returns:
            True if save was successful, False otherwise.

        Raises:
            StorageError: If storage operation fails
            ValidationError: If chunk fails validation

        """

    @abstractmethod
    def get_chunk(self, chunk_id: ChunkID) -> Optional["Chunk"]:
        """Retrieve a chunk by its ID.

        Args:
            chunk_id: The unique identifier of the chunk to retrieve

        Returns:
            The chunk if found, None otherwise

        Raises:
            StorageError: If storage operation fails

        """

    @abstractmethod
    def update_activation(self, chunk_id: ChunkID, delta: float) -> None:
        """Update the activation score for a chunk.

        This method is used by the spreading activation algorithm to adjust
        chunk relevance scores based on usage patterns.

        Args:
            chunk_id: The chunk whose activation should be updated
            delta: The amount to add to the current activation score
                   (can be negative for decay)

        Raises:
            StorageError: If storage operation fails
            ChunkNotFoundError: If chunk_id does not exist

        """

    @abstractmethod
    def retrieve_by_activation(self, min_activation: float, limit: int) -> list["Chunk"]:
        """Retrieve top N chunks above an activation threshold.

        Results are ordered by activation score (highest first).

        Args:
            min_activation: Minimum activation score (inclusive)
            limit: Maximum number of chunks to return

        Returns:
            List of chunks with activation >= min_activation, ordered by score

        Raises:
            StorageError: If storage operation fails

        """

    @abstractmethod
    def add_relationship(
        self,
        from_id: ChunkID,
        to_id: ChunkID,
        rel_type: str,
        weight: float = 1.0,
    ) -> bool:
        """Add a relationship between two chunks.

        Relationships represent dependencies, function calls, imports, or other
        semantic connections between code elements.

        Args:
            from_id: Source chunk ID
            to_id: Target chunk ID
            rel_type: Type of relationship (e.g., "depends_on", "calls", "imports")
            weight: Strength of the relationship (default: 1.0)

        Returns:
            True if relationship was added successfully

        Raises:
            StorageError: If storage operation fails
            ChunkNotFoundError: If either chunk ID does not exist

        """

    @abstractmethod
    def get_related_chunks(self, chunk_id: ChunkID, max_depth: int = 2) -> list["Chunk"]:
        """Get related chunks via relationships (for spreading activation).

        Traverses the relationship graph up to max_depth levels from the
        starting chunk, returning all connected chunks.

        Args:
            chunk_id: Starting chunk ID
            max_depth: Maximum relationship traversal depth (default: 2)

        Returns:
            List of chunks related to chunk_id within max_depth hops

        Raises:
            StorageError: If storage operation fails
            ChunkNotFoundError: If chunk_id does not exist

        """

    @abstractmethod
    def record_access(
        self,
        chunk_id: ChunkID,
        access_time: datetime | None = None,
        context: str | None = None,
    ) -> None:
        """Record an access to a chunk for ACT-R activation tracking.

        This method updates the chunk's access history, which is used to calculate
        Base-Level Activation (BLA) based on frequency and recency of access.

        Args:
            chunk_id: The chunk that was accessed
            access_time: Timestamp of access (defaults to current time)
            context: Optional context information (e.g., query keywords)

        Raises:
            StorageError: If storage operation fails
            ChunkNotFoundError: If chunk_id does not exist

        """

    @abstractmethod
    def get_access_history(
        self,
        chunk_id: ChunkID,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve access history for a chunk.

        Returns a list of access records, most recent first.

        Args:
            chunk_id: The chunk whose history to retrieve
            limit: Maximum number of records to return (None = all)

        Returns:
            List of access records with 'timestamp' and optional 'context' keys

        Raises:
            StorageError: If storage operation fails
            ChunkNotFoundError: If chunk_id does not exist

        """

    @abstractmethod
    def get_access_stats(self, chunk_id: ChunkID) -> dict[str, Any]:
        """Get access statistics for a chunk.

        Provides quick access to summary statistics without retrieving
        the full access history.

        Args:
            chunk_id: The chunk to get statistics for

        Returns:
            Dictionary with keys:
                - access_count: Total number of accesses
                - last_access: Timestamp of most recent access
                - first_access: Timestamp of first access
                - created_at: Timestamp of chunk creation

        Raises:
            StorageError: If storage operation fails
            ChunkNotFoundError: If chunk_id does not exist

        """

    def get_access_stats_batch(self, chunk_ids: list[ChunkID]) -> dict[ChunkID, dict[str, Any]]:
        """Get access statistics for multiple chunks in a single query.

        This is an optimized batch method that avoids N+1 query issues when
        retrieving stats for multiple chunks.

        Args:
            chunk_ids: List of chunk IDs to get statistics for

        Returns:
            Dictionary mapping chunk_id to stats dictionary:
                - access_count: Total number of accesses
                - last_access: Timestamp of most recent access
                - first_access: Timestamp of first access
                - created_at: Timestamp of chunk creation

        Note:
            - Missing chunks are silently omitted from results
            - Default implementation falls back to individual queries

        Raises:
            StorageError: If storage operation fails

        """
        # Default implementation - subclasses should override for efficiency
        results: dict[ChunkID, dict[str, Any]] = {}
        for chunk_id in chunk_ids:
            try:
                results[chunk_id] = self.get_access_stats(chunk_id)
            except Exception:
                # Skip missing chunks
                pass
        return results

    @abstractmethod
    def close(self) -> None:
        """Close storage connection and cleanup resources.

        This method should:
        - Close any open database connections
        - Flush pending writes
        - Release file locks
        - Clean up temporary resources

        After calling close(), the Store instance should not be used.

        Raises:
            StorageError: If cleanup fails

        """

    def get_chunk_count(self) -> int:
        """Get the total number of chunks in storage.

        This is a fast operation for checking if memory has been indexed,
        avoiding the overhead of loading chunk data or embeddings.

        Returns:
            Number of chunks stored

        Note:
            Default implementation uses retrieve_by_activation which may be
            slower. Subclasses should override with a more efficient COUNT query.

        Raises:
            StorageError: If storage operation fails

        """
        # Default implementation - subclasses should override for efficiency
        chunks = self.retrieve_by_activation(min_activation=-float("inf"), limit=1)
        return 1 if chunks else 0


__all__ = ["Store"]
