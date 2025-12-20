"""
In-memory storage implementation for testing AURORA chunks.

This module provides a lightweight, fast storage backend using Python
dictionaries for testing purposes. No file I/O is performed, making it
ideal for unit tests and CI/CD environments.
"""

from typing import List, Optional, Dict, Any, Set
from datetime import datetime
from collections import defaultdict

from aurora_core.store.base import Store
from aurora_core.types import ChunkID
from aurora_core.exceptions import (
    StorageError,
    ChunkNotFoundError,
    ValidationError,
)

# Forward reference for type checking
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from aurora_core.chunks.base import Chunk


class MemoryStore(Store):
    """
    In-memory storage implementation for testing.

    This implementation provides the same interface as SQLiteStore but stores
    all data in memory using Python dictionaries. It's fast, thread-safe for
    single-threaded tests, and can be quickly reset between tests.

    Features:
    - No file I/O (pure in-memory)
    - Fast reset between tests
    - Same interface as SQLiteStore
    - Relationship graph traversal support

    Note: This implementation is NOT thread-safe and should only be used
    in single-threaded test environments.
    """

    def __init__(self):
        """Initialize in-memory storage structures."""
        # Core storage
        self._chunks: Dict[str, 'Chunk'] = {}
        self._activations: Dict[str, Dict[str, Any]] = {}
        self._relationships: List[Dict[str, Any]] = []

        # Track if store is closed
        self._closed = False

    def _check_closed(self) -> None:
        """Raise error if store has been closed."""
        if self._closed:
            raise StorageError("Cannot perform operation on closed store")

    def reset(self) -> None:
        """
        Clear all data from memory.

        This is useful for resetting state between tests.
        """
        self._chunks.clear()
        self._activations.clear()
        self._relationships.clear()

    def save_chunk(self, chunk: 'Chunk') -> bool:
        """
        Save a chunk to memory.

        Args:
            chunk: The chunk to save

        Returns:
            True if save was successful

        Raises:
            StorageError: If store is closed
            ValidationError: If chunk validation fails
        """
        self._check_closed()

        # Validate chunk before saving
        try:
            chunk.validate()
        except ValueError as e:
            raise ValidationError(
                f"Chunk validation failed: {chunk.id}",
                details=str(e)
            )

        # Store chunk
        self._chunks[chunk.id] = chunk

        # Initialize or update activation record
        if chunk.id not in self._activations:
            self._activations[chunk.id] = {
                'base_level': 0.0,
                'last_access': datetime.utcnow(),
                'access_count': 0,
            }

        return True

    def get_chunk(self, chunk_id: ChunkID) -> Optional['Chunk']:
        """
        Retrieve a chunk by ID.

        Args:
            chunk_id: The chunk ID to retrieve

        Returns:
            The chunk if found, None otherwise

        Raises:
            StorageError: If store is closed
        """
        self._check_closed()
        return self._chunks.get(str(chunk_id))

    def update_activation(self, chunk_id: ChunkID, delta: float) -> None:
        """
        Update activation score for a chunk.

        Args:
            chunk_id: The chunk to update
            delta: Amount to add to current activation

        Raises:
            StorageError: If store is closed
            ChunkNotFoundError: If chunk doesn't exist
        """
        self._check_closed()

        chunk_id_str = str(chunk_id)
        if chunk_id_str not in self._chunks:
            raise ChunkNotFoundError(chunk_id_str)

        if chunk_id_str not in self._activations:
            self._activations[chunk_id_str] = {
                'base_level': 0.0,
                'last_access': datetime.utcnow(),
                'access_count': 0,
            }

        # Update activation
        self._activations[chunk_id_str]['base_level'] += delta
        self._activations[chunk_id_str]['last_access'] = datetime.utcnow()
        self._activations[chunk_id_str]['access_count'] += 1

    def retrieve_by_activation(
        self,
        min_activation: float,
        limit: int
    ) -> List['Chunk']:
        """
        Retrieve chunks by activation threshold.

        Args:
            min_activation: Minimum activation score
            limit: Maximum number of chunks to return

        Returns:
            List of chunks ordered by activation (highest first)

        Raises:
            StorageError: If store is closed
        """
        self._check_closed()

        # Filter and sort chunks by activation
        results = []
        for chunk_id, activation_data in self._activations.items():
            if activation_data['base_level'] >= min_activation:
                chunk = self._chunks.get(chunk_id)
                if chunk is not None:
                    results.append((chunk, activation_data['base_level']))

        # Sort by activation (highest first) and limit results
        results.sort(key=lambda x: x[1], reverse=True)
        return [chunk for chunk, _ in results[:limit]]

    def add_relationship(
        self,
        from_id: ChunkID,
        to_id: ChunkID,
        rel_type: str,
        weight: float = 1.0
    ) -> bool:
        """
        Add a relationship between chunks.

        Args:
            from_id: Source chunk ID
            to_id: Target chunk ID
            rel_type: Relationship type
            weight: Relationship strength

        Returns:
            True if relationship was added

        Raises:
            StorageError: If store is closed
            ChunkNotFoundError: If either chunk doesn't exist
        """
        self._check_closed()

        from_id_str = str(from_id)
        to_id_str = str(to_id)

        # Verify both chunks exist
        if from_id_str not in self._chunks:
            raise ChunkNotFoundError(from_id_str)
        if to_id_str not in self._chunks:
            raise ChunkNotFoundError(to_id_str)

        # Add relationship
        self._relationships.append({
            'from_chunk': from_id_str,
            'to_chunk': to_id_str,
            'relationship_type': rel_type,
            'weight': weight,
        })

        return True

    def get_related_chunks(
        self,
        chunk_id: ChunkID,
        max_depth: int = 2
    ) -> List['Chunk']:
        """
        Get related chunks via relationship graph traversal.

        Args:
            chunk_id: Starting chunk ID
            max_depth: Maximum traversal depth

        Returns:
            List of related chunks within max_depth hops

        Raises:
            StorageError: If store is closed
            ChunkNotFoundError: If starting chunk doesn't exist
        """
        self._check_closed()

        chunk_id_str = str(chunk_id)
        if chunk_id_str not in self._chunks:
            raise ChunkNotFoundError(chunk_id_str)

        # BFS traversal of relationship graph
        visited: Set[str] = set()
        current_level = {chunk_id_str}
        depth = 0

        while depth < max_depth and current_level:
            next_level = set()
            for current_id in current_level:
                # Find all chunks related to current_id
                for rel in self._relationships:
                    if rel['from_chunk'] == current_id:
                        target_id = rel['to_chunk']
                        if target_id not in visited:
                            visited.add(target_id)
                            next_level.add(target_id)

            current_level = next_level
            depth += 1

        # Return chunks for all visited IDs
        return [self._chunks[cid] for cid in visited if cid in self._chunks]

    def close(self) -> None:
        """
        Close the store and mark it as closed.

        For MemoryStore, this just sets a flag. No actual cleanup is needed
        since everything is in memory.

        Raises:
            StorageError: Never (included for interface compatibility)
        """
        self._closed = True

    def __len__(self) -> int:
        """Return number of chunks in storage."""
        return len(self._chunks)

    def __contains__(self, chunk_id: ChunkID) -> bool:
        """Check if chunk exists in storage."""
        return str(chunk_id) in self._chunks


__all__ = ['MemoryStore']
