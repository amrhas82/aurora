"""Unit tests for the abstract Store interface contract.

These tests verify that any Store implementation follows the expected
interface contract and behavior patterns.
"""

from abc import ABC
from typing import Any

import pytest

from aurora_core.chunks.base import Chunk
from aurora_core.exceptions import ChunkNotFoundError
from aurora_core.store.base import Store
from aurora_core.types import ChunkID


# Helper Chunk implementation for testing
class SimpleChunk(Chunk):
    """Simple chunk implementation for testing."""

    def __init__(self, chunk_id: str, content: str = "test"):
        super().__init__(chunk_id, "test")
        self.content = content

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "content": {"data": self.content},
            "metadata": {},
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "SimpleChunk":
        chunk_id = data["id"]
        content = data.get("content", {}).get("data", "test")
        return cls(chunk_id, content)

    def validate(self) -> bool:
        if not self.id:
            raise ValueError("Chunk ID cannot be empty")
        return True


class TestStoreInterface:
    """Test the Store abstract interface."""

    def test_store_is_abstract(self):
        """Verify Store cannot be instantiated directly."""
        with pytest.raises(TypeError):
            Store()  # Should fail - abstract class


class StoreContractTests(ABC):
    """Abstract test suite that verifies Store implementation contract.

    Concrete test classes for specific Store implementations should inherit
    from this class and implement the create_store() fixture.
    """

    @pytest.fixture
    def store(self):
        """Create a Store instance for testing.

        This should be overridden by concrete test classes.
        """
        raise NotImplementedError("Subclasses must implement store fixture")

    @pytest.fixture
    def sample_chunk(self):
        """Create a sample chunk for testing."""
        return SimpleChunk("test:chunk:1", "Sample content")

    @pytest.fixture
    def sample_chunks(self):
        """Create multiple sample chunks for testing."""
        return [
            SimpleChunk("test:chunk:1", "Content 1"),
            SimpleChunk("test:chunk:2", "Content 2"),
            SimpleChunk("test:chunk:3", "Content 3"),
        ]

    def test_save_and_retrieve_chunk(self, store, sample_chunk):
        """Test basic save and retrieve operations."""
        # Save chunk
        result = store.save_chunk(sample_chunk)
        assert result is True, "save_chunk should return True on success"

        # Retrieve chunk
        retrieved = store.get_chunk(ChunkID(sample_chunk.id))
        assert retrieved is not None, "get_chunk should return saved chunk"
        # Note: Full equality check depends on deserialization implementation

    def test_get_nonexistent_chunk_returns_none(self, store):
        """Test that retrieving non-existent chunk returns None."""
        result = store.get_chunk(ChunkID("nonexistent:chunk:id"))
        assert result is None, "get_chunk should return None for non-existent chunks"

    def test_update_activation_success(self, store, sample_chunk):
        """Test updating activation for existing chunk."""
        # Save chunk first
        store.save_chunk(sample_chunk)

        # Update activation should not raise
        store.update_activation(ChunkID(sample_chunk.id), 1.5)

    def test_update_activation_nonexistent_chunk(self, store):
        """Test updating activation for non-existent chunk raises error."""
        with pytest.raises(ChunkNotFoundError):
            store.update_activation(ChunkID("nonexistent:chunk"), 1.0)

    def test_retrieve_by_activation_empty(self, store):
        """Test retrieving by activation when no chunks exist."""
        results = store.retrieve_by_activation(min_activation=0.5, limit=10)
        assert isinstance(results, list), "Should return list"
        assert len(results) == 0, "Should return empty list when no chunks exist"

    def test_retrieve_by_activation_with_threshold(self, store, sample_chunks):
        """Test retrieving chunks above activation threshold."""
        # Save chunks and set different activations
        for i, chunk in enumerate(sample_chunks):
            store.save_chunk(chunk)
            store.update_activation(ChunkID(chunk.id), float(i))

        # Retrieve chunks above threshold
        results = store.retrieve_by_activation(min_activation=1.0, limit=10)
        assert isinstance(results, list), "Should return list"
        # At least chunks with activation >= 1.0 should be returned

    def test_retrieve_by_activation_respects_limit(self, store, sample_chunks):
        """Test that retrieve_by_activation respects the limit parameter."""
        # Save all chunks with high activation
        for chunk in sample_chunks:
            store.save_chunk(chunk)
            store.update_activation(ChunkID(chunk.id), 10.0)

        # Retrieve with limit
        results = store.retrieve_by_activation(min_activation=0.0, limit=2)
        assert len(results) <= 2, "Should respect limit parameter"

    def test_add_relationship_success(self, store, sample_chunks):
        """Test adding relationship between chunks."""
        chunk1, chunk2 = sample_chunks[0], sample_chunks[1]

        # Save both chunks
        store.save_chunk(chunk1)
        store.save_chunk(chunk2)

        # Add relationship
        result = store.add_relationship(
            ChunkID(chunk1.id), ChunkID(chunk2.id), "depends_on", weight=1.0
        )
        assert result is True, "add_relationship should return True on success"

    def test_add_relationship_nonexistent_chunks(self, store):
        """Test adding relationship with non-existent chunks raises error."""
        with pytest.raises(ChunkNotFoundError):
            store.add_relationship(ChunkID("nonexistent:1"), ChunkID("nonexistent:2"), "depends_on")

    def test_get_related_chunks_empty(self, store, sample_chunk):
        """Test getting related chunks when none exist."""
        store.save_chunk(sample_chunk)

        results = store.get_related_chunks(ChunkID(sample_chunk.id), max_depth=2)
        assert isinstance(results, list), "Should return list"
        assert len(results) == 0, "Should return empty list when no relationships exist"

    def test_get_related_chunks_nonexistent(self, store):
        """Test getting related chunks for non-existent chunk raises error."""
        with pytest.raises(ChunkNotFoundError):
            store.get_related_chunks(ChunkID("nonexistent:chunk"), max_depth=1)

    def test_close_store(self, store):
        """Test closing the store."""
        # Should not raise an exception
        store.close()


__all__ = ["TestStoreInterface", "StoreContractTests", "SimpleChunk"]
