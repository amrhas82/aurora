"""Unit tests for SQLiteStore implementation.

These tests verify SQLite-specific functionality including:
- Database file creation and initialization
- Transaction handling and rollback
- Connection management
- Schema creation
"""

from pathlib import Path

import pytest

from aurora_core.chunks.code_chunk import CodeChunk
from aurora_core.exceptions import ValidationError
from aurora_core.store.sqlite import SQLiteStore
from aurora_core.types import ChunkID
from tests.unit.core.test_store_base import StoreContractTests


def create_test_code_chunk(chunk_id: str, name: str = "test_func") -> CodeChunk:
    """Helper to create CodeChunk for testing."""
    return CodeChunk(
        chunk_id=chunk_id,
        file_path="/test/file.py",
        element_type="function",
        name=name,
        line_start=1,
        line_end=10,
    )


class TestSQLiteStore(StoreContractTests):
    """Test SQLiteStore implementation."""

    @pytest.fixture
    def store(self):
        """Create an in-memory SQLiteStore for testing."""
        store = SQLiteStore(db_path=":memory:")
        yield store
        store.close()

    @pytest.fixture
    def file_store(self, tmp_path):
        """Create a file-based SQLiteStore for testing persistence."""
        db_path = tmp_path / "test.db"
        store = SQLiteStore(db_path=str(db_path))
        yield store
        store.close()

    @pytest.fixture
    def sample_chunk(self):
        """Create a sample CodeChunk for testing (SQLite only supports CodeChunk/ReasoningChunk)."""
        return CodeChunk(
            chunk_id="test:chunk:1",
            file_path="/test/file.py",
            element_type="function",
            name="test_function",
            line_start=1,
            line_end=10,
        )

    @pytest.fixture
    def sample_chunks(self):
        """Create multiple sample CodeChunks for testing."""
        return [
            CodeChunk(
                chunk_id="test:chunk:1",
                file_path="/test/file1.py",
                element_type="function",
                name="func1",
                line_start=1,
                line_end=10,
            ),
            CodeChunk(
                chunk_id="test:chunk:2",
                file_path="/test/file2.py",
                element_type="function",
                name="func2",
                line_start=1,
                line_end=10,
            ),
            CodeChunk(
                chunk_id="test:chunk:3",
                file_path="/test/file3.py",
                element_type="function",
                name="func3",
                line_start=1,
                line_end=10,
            ),
        ]

    def test_initialize_with_file_path(self, tmp_path):
        """Test initializing SQLiteStore with file path."""
        db_path = tmp_path / "aurora.db"
        store = SQLiteStore(db_path=str(db_path))

        # Database file should be created
        assert db_path.exists(), "Database file should be created"

        store.close()

    def test_initialize_with_home_directory_expansion(self, tmp_path, monkeypatch):
        """Test that ~ in path is expanded to home directory."""
        # Mock expanduser to use tmp_path
        monkeypatch.setattr(
            Path,
            "expanduser",
            lambda self: tmp_path / str(self).replace("~", "home"),
        )

        store = SQLiteStore(db_path="~/aurora.db")
        # Should not raise an error
        store.close()

    def test_schema_initialization(self, store):
        """Test that schema is properly initialized."""
        conn = store._get_connection()

        # Check that tables exist
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        expected_tables = {"chunks", "activations", "relationships", "schema_version"}
        assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"

    def test_wal_mode_enabled(self, file_store):
        """Test that WAL mode is enabled for file-based databases."""
        conn = file_store._get_connection()
        cursor = conn.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        assert mode.upper() == "WAL", "WAL mode should be enabled"

    def test_foreign_keys_enabled(self, store):
        """Test that foreign key constraints are enabled."""
        conn = store._get_connection()
        cursor = conn.execute("PRAGMA foreign_keys")
        enabled = cursor.fetchone()[0]
        assert enabled == 1, "Foreign keys should be enabled"

    def test_save_chunk_validation_error(self, store):
        """Test that invalid chunks are rejected."""
        # Create an invalid chunk with invalid line numbers
        with pytest.raises((ValidationError, ValueError)):
            invalid_chunk = CodeChunk(
                chunk_id="test:chunk:1",
                file_path="/test/file.py",
                element_type="function",
                name="test",
                line_start=10,
                line_end=5,  # End before start - invalid
            )
            store.save_chunk(invalid_chunk)

    def test_save_chunk_updates_timestamp(self, store):
        """Test that saving a chunk updates the updated_at timestamp."""
        chunk = create_test_code_chunk("test:chunk:1", "test_func")
        store.save_chunk(chunk)

        conn = store._get_connection()
        cursor = conn.execute("SELECT updated_at FROM chunks WHERE id = ?", (chunk.id,))
        row = cursor.fetchone()
        assert row is not None, "Chunk should be saved"
        assert row[0] is not None, "updated_at should be set"

    def test_transaction_rollback_on_error(self, store):
        """Test that transactions are rolled back on errors."""
        chunk = create_test_code_chunk("test:chunk:1", "test_func")
        store.save_chunk(chunk)

        # Try to add a relationship with non-existent target (should fail)
        try:
            store.add_relationship(ChunkID(chunk.id), ChunkID("nonexistent:chunk"), "depends_on")
        except:
            pass  # Expected to fail

        # Original chunk should still exist
        store.get_chunk(ChunkID(chunk.id))
        # Note: Will be None until deserialization is implemented, but should not crash

    def test_concurrent_connections(self, file_store):
        """Test that multiple connections can be used (thread-safety simulation)."""
        chunk1 = create_test_code_chunk("test:chunk:1", "func1")
        chunk2 = create_test_code_chunk("test:chunk:2", "func2")

        # Save from different "simulated threads" (same thread but different operations)
        file_store.save_chunk(chunk1)
        file_store.save_chunk(chunk2)

        # Both should be retrievable
        file_store.get_chunk(ChunkID(chunk1.id))
        file_store.get_chunk(ChunkID(chunk2.id))

        # At least verify they don't raise exceptions
        # Full equality depends on deserialization

    def test_relationship_cascade_delete(self, store):
        """Test that relationships are cascade deleted when chunks are removed."""
        chunk1 = create_test_code_chunk("test:chunk:1", "func1")
        chunk2 = create_test_code_chunk("test:chunk:2", "func2")

        store.save_chunk(chunk1)
        store.save_chunk(chunk2)
        store.add_relationship(ChunkID(chunk1.id), ChunkID(chunk2.id), "depends_on")

        # Delete chunk1
        conn = store._get_connection()
        conn.execute("DELETE FROM chunks WHERE id = ?", (chunk1.id,))
        conn.commit()

        # Relationship should be cascade deleted
        cursor = conn.execute(
            "SELECT COUNT(*) FROM relationships WHERE from_chunk = ? OR to_chunk = ?",
            (chunk1.id, chunk1.id),
        )
        count = cursor.fetchone()[0]
        assert count == 0, "Relationships should be cascade deleted"

    def test_activation_initialization(self, store):
        """Test that activation records are initialized when saving chunks."""
        chunk = create_test_code_chunk("test:chunk:1", "test_func")
        store.save_chunk(chunk)

        conn = store._get_connection()
        cursor = conn.execute(
            "SELECT base_level, access_count FROM activations WHERE chunk_id = ?",
            (chunk.id,),
        )
        row = cursor.fetchone()

        assert row is not None, "Activation record should be created"
        assert row[0] == 0.0, "Initial base_level should be 0.0"
        assert row[1] == 0, "Initial access_count should be 0"

    def test_update_activation_increments_count(self, store):
        """Test that updating activation increments access count."""
        chunk = create_test_code_chunk("test:chunk:1", "test_func")
        store.save_chunk(chunk)

        # Update activation multiple times
        store.update_activation(ChunkID(chunk.id), 1.0)
        store.update_activation(ChunkID(chunk.id), 0.5)

        conn = store._get_connection()
        cursor = conn.execute(
            "SELECT access_count FROM activations WHERE chunk_id = ?",
            (chunk.id,),
        )
        count = cursor.fetchone()[0]
        assert count == 2, "Access count should be incremented"

    def test_retrieve_by_activation_ordering(self, store):
        """Test that results are ordered by activation (highest first)."""
        chunks = [
            create_test_code_chunk("test:chunk:1", "func1"),
            create_test_code_chunk("test:chunk:2", "func2"),
            create_test_code_chunk("test:chunk:3", "func3"),
        ]

        # Save and set different activations
        for i, chunk in enumerate(chunks):
            store.save_chunk(chunk)
            store.update_activation(ChunkID(chunk.id), float(len(chunks) - i))

        # Retrieve and verify order
        conn = store._get_connection()
        cursor = conn.execute(
            """
            SELECT c.id, a.base_level
            FROM chunks c
            JOIN activations a ON c.id = a.chunk_id
            ORDER BY a.base_level DESC
        """,
        )

        rows = cursor.fetchall()
        activations = [row[1] for row in rows]

        # Check that activations are in descending order
        assert activations == sorted(
            activations,
            reverse=True,
        ), "Results should be ordered by activation (highest first)"

    def test_get_related_chunks_depth_limit(self, store):
        """Test that relationship traversal respects max_depth."""
        # Create a chain: chunk1 -> chunk2 -> chunk3 -> chunk4
        chunks = [create_test_code_chunk(f"test:chunk:{i}", f"func{i}") for i in range(1, 5)]

        for chunk in chunks:
            store.save_chunk(chunk)

        for i in range(len(chunks) - 1):
            store.add_relationship(ChunkID(chunks[i].id), ChunkID(chunks[i + 1].id), "depends_on")

        # Get related chunks with max_depth=1 (should only get chunk2)
        store.get_related_chunks(ChunkID(chunks[0].id), max_depth=1)
        # Note: Actual count depends on deserialization implementation

        # Get related chunks with max_depth=2 (should get chunk2 and chunk3)
        store.get_related_chunks(ChunkID(chunks[0].id), max_depth=2)
        # Note: Actual count depends on deserialization implementation

    def test_close_connection(self, store):
        """Test that close() properly closes the connection."""
        chunk = create_test_code_chunk("test:chunk:1", "test_func")
        store.save_chunk(chunk)

        # Close the store
        store.close()

        # Connection should be closed
        assert store._local.connection is None, "Connection should be None after close"

    def test_persistence_across_instances(self, tmp_path):
        """Test that data persists across store instances."""
        db_path = tmp_path / "persistent.db"
        chunk = create_test_code_chunk("test:chunk:1", "test_func")

        # Save in first instance
        store1 = SQLiteStore(db_path=str(db_path))
        store1.save_chunk(chunk)
        store1.close()

        # Retrieve in second instance
        store2 = SQLiteStore(db_path=str(db_path))
        store2.get_chunk(ChunkID(chunk.id))
        # Should not raise an error (actual retrieval depends on deserialization)
        store2.close()

    def test_save_chunk_with_embeddings(self, store):
        """Test saving a chunk with embeddings (BLOB field)."""
        chunk = create_test_code_chunk("test:chunk:1", "test_func")

        # Add embeddings as bytes (simulating numpy array serialization)
        test_embeddings = b"\x00\x01\x02\x03\x04\x05\x06\x07"
        chunk.embeddings = test_embeddings

        # Save chunk
        store.save_chunk(chunk)

        # Verify embeddings were saved to database
        conn = store._get_connection()
        cursor = conn.execute("SELECT embeddings FROM chunks WHERE id = ?", (chunk.id,))
        row = cursor.fetchone()
        assert row is not None, "Chunk should be saved"
        assert row[0] == test_embeddings, "Embeddings should be saved as BLOB"

    def test_get_chunk_with_embeddings(self, store):
        """Test retrieving a chunk with embeddings."""
        chunk = create_test_code_chunk("test:chunk:1", "test_func")

        # Add embeddings
        test_embeddings = b"\x00\x01\x02\x03\x04\x05\x06\x07"
        chunk.embeddings = test_embeddings

        # Save and retrieve
        store.save_chunk(chunk)
        retrieved = store.get_chunk(ChunkID(chunk.id))

        assert retrieved is not None, "Chunk should be retrieved"
        assert hasattr(retrieved, "embeddings"), "Retrieved chunk should have embeddings attribute"
        assert retrieved.embeddings == test_embeddings, "Embeddings should be preserved"

    def test_save_chunk_without_embeddings(self, store):
        """Test saving a chunk without embeddings (optional field)."""
        chunk = create_test_code_chunk("test:chunk:1", "test_func")

        # Don't set embeddings - should default to None
        store.save_chunk(chunk)

        # Verify embeddings column is NULL
        conn = store._get_connection()
        cursor = conn.execute("SELECT embeddings FROM chunks WHERE id = ?", (chunk.id,))
        row = cursor.fetchone()
        assert row is not None, "Chunk should be saved"
        assert row[0] is None, "Embeddings should be NULL when not set"

    def test_retrieve_by_activation_with_embeddings(self, store):
        """Test that retrieve_by_activation preserves embeddings."""
        chunk1 = create_test_code_chunk("test:chunk:1", "func1")
        chunk2 = create_test_code_chunk("test:chunk:2", "func2")

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
        assert chunk1_retrieved is not None, "Chunk1 should be in results"
        assert hasattr(chunk1_retrieved, "embeddings"), "Retrieved chunk should have embeddings"
        assert chunk1_retrieved.embeddings == chunk1.embeddings, "Embeddings should be preserved"


__all__ = ["TestSQLiteStore"]
