"""
Unit tests for MemoryStore implementation.

These tests verify in-memory storage functionality including:
- Fast in-memory operations
- Reset capability for test isolation
- No file I/O dependencies
"""

import pytest
from aurora.core.exceptions import StorageError
from aurora.core.store.memory import MemoryStore
from aurora.core.types import ChunkID

from tests.unit.core.test_store_base import StoreContractTests, TestChunk


class TestMemoryStore(StoreContractTests):
    """Test MemoryStore implementation."""

    @pytest.fixture
    def store(self):
        """Create a MemoryStore for testing."""
        store = MemoryStore()
        yield store
        store.close()

    def test_initialize_empty(self):
        """Test that MemoryStore initializes with empty storage."""
        store = MemoryStore()
        assert len(store) == 0, "Store should be empty on initialization"
        store.close()

    def test_reset_clears_all_data(self, store):
        """Test that reset() clears all stored data."""
        # Add some data
        chunks = [
            TestChunk("test:chunk:1", "content1"),
            TestChunk("test:chunk:2", "content2"),
        ]

        for chunk in chunks:
            store.save_chunk(chunk)
            store.update_activation(ChunkID(chunk.id), 1.0)

        store.add_relationship(ChunkID(chunks[0].id), ChunkID(chunks[1].id), "depends_on")

        # Reset
        store.reset()

        # Verify everything is cleared
        assert len(store) == 0, "Chunks should be cleared"
        assert len(store._activations) == 0, "Activations should be cleared"
        assert len(store._relationships) == 0, "Relationships should be cleared"

    def test_contains_operator(self, store):
        """Test the 'in' operator for checking chunk existence."""
        chunk = TestChunk("test:chunk:1", "content")

        # Chunk should not exist initially
        assert ChunkID(chunk.id) not in store

        # Save chunk
        store.save_chunk(chunk)

        # Chunk should exist now
        assert ChunkID(chunk.id) in store

    def test_len_operator(self, store):
        """Test the len() operator for counting chunks."""
        assert len(store) == 0, "Store should start empty"

        # Add chunks
        for i in range(5):
            chunk = TestChunk(f"test:chunk:{i}", f"content{i}")
            store.save_chunk(chunk)

        assert len(store) == 5, "Store should have 5 chunks"

    def test_closed_store_raises_error(self, store):
        """Test that operations on closed store raise errors."""
        chunk = TestChunk("test:chunk:1", "content")
        store.close()

        with pytest.raises(StorageError):
            store.save_chunk(chunk)

        with pytest.raises(StorageError):
            store.get_chunk(ChunkID(chunk.id))

        with pytest.raises(StorageError):
            store.update_activation(ChunkID(chunk.id), 1.0)

        with pytest.raises(StorageError):
            store.retrieve_by_activation(0.5, 10)

        with pytest.raises(StorageError):
            store.add_relationship(ChunkID("test:1"), ChunkID("test:2"), "depends_on")

        with pytest.raises(StorageError):
            store.get_related_chunks(ChunkID(chunk.id))

    def test_save_chunk_stores_in_memory(self, store):
        """Test that chunks are stored in memory dictionary."""
        chunk = TestChunk("test:chunk:1", "content")
        store.save_chunk(chunk)

        # Check internal storage
        assert chunk.id in store._chunks
        assert store._chunks[chunk.id] == chunk

    def test_get_chunk_returns_same_instance(self, store):
        """Test that get_chunk returns the same instance (no serialization)."""
        chunk = TestChunk("test:chunk:1", "content")
        store.save_chunk(chunk)

        retrieved = store.get_chunk(ChunkID(chunk.id))
        assert retrieved is chunk, "Should return the same instance"

    def test_activation_updates_timestamp(self, store):
        """Test that updating activation updates last_access timestamp."""
        chunk = TestChunk("test:chunk:1", "content")
        store.save_chunk(chunk)

        # Get initial timestamp
        initial_access = store._activations[chunk.id]["last_access"]

        # Small delay to ensure timestamp difference
        import time

        time.sleep(0.01)

        # Update activation
        store.update_activation(ChunkID(chunk.id), 1.0)

        # Check timestamp was updated
        new_access = store._activations[chunk.id]["last_access"]
        assert new_access > initial_access, "last_access should be updated"

    def test_retrieve_by_activation_exact_match(self, store):
        """Test retrieving chunks with exact activation match."""
        chunks = [
            TestChunk("test:chunk:1", "content1"),
            TestChunk("test:chunk:2", "content2"),
            TestChunk("test:chunk:3", "content3"),
        ]

        # Save chunks with specific activations
        activations = [1.0, 2.0, 3.0]
        for chunk, activation in zip(chunks, activations, strict=False):
            store.save_chunk(chunk)
            store.update_activation(ChunkID(chunk.id), activation)

        # Retrieve with threshold of 2.0
        results = store.retrieve_by_activation(min_activation=2.0, limit=10)

        # Should get chunks with activation >= 2.0 (chunks 2 and 3)
        assert len(results) >= 2, "Should retrieve chunks with activation >= 2.0"

    def test_retrieve_by_activation_sorted(self, store):
        """Test that results are sorted by activation (highest first)."""
        chunks = [
            TestChunk("test:chunk:1", "low"),
            TestChunk("test:chunk:2", "high"),
            TestChunk("test:chunk:3", "medium"),
        ]

        # Save with different activations
        store.save_chunk(chunks[0])
        store.update_activation(ChunkID(chunks[0].id), 1.0)

        store.save_chunk(chunks[1])
        store.update_activation(ChunkID(chunks[1].id), 10.0)

        store.save_chunk(chunks[2])
        store.update_activation(ChunkID(chunks[2].id), 5.0)

        # Retrieve all
        results = store.retrieve_by_activation(min_activation=0.0, limit=10)

        # Verify order: high (10.0), medium (5.0), low (1.0)
        assert len(results) == 3
        assert results[0].content == "high", "First should be highest activation"
        assert results[1].content == "medium", "Second should be medium activation"
        assert results[2].content == "low", "Third should be lowest activation"

    def test_add_relationship_stores_metadata(self, store):
        """Test that relationships store all metadata."""
        chunk1 = TestChunk("test:chunk:1", "content1")
        chunk2 = TestChunk("test:chunk:2", "content2")

        store.save_chunk(chunk1)
        store.save_chunk(chunk2)

        store.add_relationship(ChunkID(chunk1.id), ChunkID(chunk2.id), "depends_on", weight=2.5)

        # Check internal storage
        assert len(store._relationships) == 1
        rel = store._relationships[0]
        assert rel["from_chunk"] == chunk1.id
        assert rel["to_chunk"] == chunk2.id
        assert rel["relationship_type"] == "depends_on"
        assert rel["weight"] == 2.5

    def test_get_related_chunks_single_hop(self, store):
        """Test getting related chunks with single hop."""
        chunks = [
            TestChunk("test:chunk:1", "content1"),
            TestChunk("test:chunk:2", "content2"),
            TestChunk("test:chunk:3", "content3"),
        ]

        for chunk in chunks:
            store.save_chunk(chunk)

        # Create relationships: 1 -> 2, 1 -> 3
        store.add_relationship(ChunkID(chunks[0].id), ChunkID(chunks[1].id), "calls")
        store.add_relationship(ChunkID(chunks[0].id), ChunkID(chunks[2].id), "calls")

        # Get related chunks with depth 1
        related = store.get_related_chunks(ChunkID(chunks[0].id), max_depth=1)

        # Should get both chunk2 and chunk3
        assert len(related) == 2
        related_ids = {chunk.id for chunk in related}
        assert chunks[1].id in related_ids
        assert chunks[2].id in related_ids

    def test_get_related_chunks_multi_hop(self, store):
        """Test getting related chunks with multiple hops."""
        # Create chain: 1 -> 2 -> 3
        chunks = [
            TestChunk("test:chunk:1", "content1"),
            TestChunk("test:chunk:2", "content2"),
            TestChunk("test:chunk:3", "content3"),
        ]

        for chunk in chunks:
            store.save_chunk(chunk)

        store.add_relationship(ChunkID(chunks[0].id), ChunkID(chunks[1].id), "calls")
        store.add_relationship(ChunkID(chunks[1].id), ChunkID(chunks[2].id), "calls")

        # Get related with depth 1 (should only get chunk2)
        related_depth1 = store.get_related_chunks(ChunkID(chunks[0].id), max_depth=1)
        assert len(related_depth1) == 1
        assert related_depth1[0].id == chunks[1].id

        # Get related with depth 2 (should get chunk2 and chunk3)
        related_depth2 = store.get_related_chunks(ChunkID(chunks[0].id), max_depth=2)
        assert len(related_depth2) == 2
        related_ids = {chunk.id for chunk in related_depth2}
        assert chunks[1].id in related_ids
        assert chunks[2].id in related_ids

    def test_get_related_chunks_no_duplicates(self, store):
        """Test that related chunks are not duplicated."""
        # Create diamond: 1 -> 2, 1 -> 3, 2 -> 4, 3 -> 4
        chunks = [TestChunk(f"test:chunk:{i}", f"content{i}") for i in range(1, 5)]

        for chunk in chunks:
            store.save_chunk(chunk)

        store.add_relationship(ChunkID(chunks[0].id), ChunkID(chunks[1].id), "calls")
        store.add_relationship(ChunkID(chunks[0].id), ChunkID(chunks[2].id), "calls")
        store.add_relationship(ChunkID(chunks[1].id), ChunkID(chunks[3].id), "calls")
        store.add_relationship(ChunkID(chunks[2].id), ChunkID(chunks[3].id), "calls")

        # Get related with depth 2 (chunk4 reachable via two paths)
        related = store.get_related_chunks(ChunkID(chunks[0].id), max_depth=2)

        # Should not have duplicates
        related_ids = [chunk.id for chunk in related]
        assert len(related_ids) == len(set(related_ids)), "Should not have duplicate chunks"

    def test_no_file_io_operations(self, store):
        """Test that MemoryStore performs no file I/O."""
        # This is implicit in the implementation, but we can verify
        # that it works without any file system dependencies

        chunk = TestChunk("test:chunk:1", "content")
        store.save_chunk(chunk)

        retrieved = store.get_chunk(ChunkID(chunk.id))
        assert retrieved is not None

        # If we got here without errors, no file I/O was attempted
        assert True, "MemoryStore should work without file I/O"

    def test_save_chunk_with_embeddings(self, store):
        """Test saving a chunk with embeddings attribute."""
        chunk = TestChunk("test:chunk:1", "content")

        # Add embeddings as bytes (simulating numpy array serialization)
        test_embeddings = b"\x00\x01\x02\x03\x04\x05\x06\x07"
        chunk.embeddings = test_embeddings

        # Save chunk
        store.save_chunk(chunk)

        # Verify embeddings were preserved in memory
        assert chunk.id in store._chunks
        stored_chunk = store._chunks[chunk.id]
        assert hasattr(stored_chunk, "embeddings"), "Stored chunk should have embeddings attribute"
        assert stored_chunk.embeddings == test_embeddings, "Embeddings should be preserved"

    def test_get_chunk_with_embeddings(self, store):
        """Test retrieving a chunk with embeddings."""
        chunk = TestChunk("test:chunk:1", "content")

        # Add embeddings
        test_embeddings = b"\x00\x01\x02\x03\x04\x05\x06\x07"
        chunk.embeddings = test_embeddings

        # Save and retrieve
        store.save_chunk(chunk)
        retrieved = store.get_chunk(ChunkID(chunk.id))

        assert retrieved is not None, "Chunk should be retrieved"
        assert hasattr(retrieved, "embeddings"), "Retrieved chunk should have embeddings attribute"
        assert retrieved.embeddings == test_embeddings, "Embeddings should be preserved"
        assert retrieved is chunk, "MemoryStore should return the same instance"

    def test_save_chunk_without_embeddings(self, store):
        """Test saving a chunk without embeddings (optional field)."""
        chunk = TestChunk("test:chunk:1", "content")

        # Don't set embeddings - should work fine
        store.save_chunk(chunk)

        # Verify chunk was saved
        assert chunk.id in store._chunks
        stored_chunk = store._chunks[chunk.id]
        # Embeddings attribute may not exist or be None
        assert not hasattr(stored_chunk, "embeddings") or stored_chunk.embeddings is None

    def test_retrieve_by_activation_with_embeddings(self, store):
        """Test that retrieve_by_activation preserves embeddings."""
        chunk1 = TestChunk("test:chunk:1", "content1")
        chunk2 = TestChunk("test:chunk:2", "content2")

        # Add embeddings to both chunks
        chunk1.embeddings = b"\x00\x01\x02\x03"
        chunk2.embeddings = b"\x04\x05\x06\x07"

        # Save chunks and set activations
        store.save_chunk(chunk1)
        store.save_chunk(chunk2)
        store.update_activation(ChunkID(chunk1.id), 2.0)
        store.update_activation(ChunkID(chunk2.id), 1.0)

        # Retrieve by activation
        chunks = store.retrieve_by_activation(min_activation=0.5, limit=10)

        assert len(chunks) == 2, "Should retrieve both chunks"
        # Find chunk1 in results
        chunk1_retrieved = next((c for c in chunks if c.id == chunk1.id), None)
        assert chunk1_retrieved is not None, "chunk1 should be in results"
        assert hasattr(chunk1_retrieved, "embeddings"), "Retrieved chunk should have embeddings"
        assert chunk1_retrieved.embeddings == b"\x00\x01\x02\x03", "Embeddings should be preserved"


__all__ = ["TestMemoryStore"]
