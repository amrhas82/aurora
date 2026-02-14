"""Tests for 'reas' (reasoning) chunk type support in SQLiteStore.

Tests that the store correctly deserializes chunks with type='reas'.
"""

import tempfile
from pathlib import Path

import pytest

from aurora_core.chunks import CodeChunk
from aurora_core.store import SQLiteStore


@pytest.fixture
def store():
    """Create a temporary SQLiteStore for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = SQLiteStore(str(db_path))
        yield store
        store.close()


class TestReasTypeSupport:
    """Tests for 'reas' chunk type in SQLiteStore."""

    def test_save_and_retrieve_reas_chunk(self, store):
        """Should save and retrieve a chunk with type='reas'."""
        # Create a chunk with 'reas' type (SOAR reasoning trace)
        chunk = CodeChunk(
            chunk_id="reas_test_001",
            file_path="/path/to/conversation.md",
            element_type="knowledge",
            name="SOAR Conversation",
            line_start=1,
            line_end=50,
            docstring="Query: What is 2+2?\nResponse: 4",
            language="markdown",
        )
        chunk.type = "reas"  # Set type to reasoning

        # Save the chunk
        store.save_chunk(chunk)

        # Retrieve by ID
        retrieved = store.get_chunk("reas_test_001")

        assert retrieved is not None
        assert retrieved.type == "reas"
        assert isinstance(retrieved, CodeChunk)
        assert retrieved.name == "SOAR Conversation"

    def test_reas_type_preserved_after_save(self, store):
        """Type should be preserved exactly as 'reas' after save."""
        chunk = CodeChunk(
            chunk_id="reas_test_002",
            file_path="/path/to/goals.md",
            element_type="knowledge",
            name="Goals Output",
            line_start=1,
            line_end=20,
            docstring="Goal decomposition output",
            language="markdown",
        )
        chunk.type = "reas"

        store.save_chunk(chunk)
        retrieved = store.get_chunk("reas_test_002")

        # Verify type is exactly 'reas', not converted to something else
        assert retrieved.type == "reas"

    def test_retrieve_by_activation_includes_reas(self, store):
        """retrieve_by_activation with chunk_type='reas' should work."""
        # Save a reas chunk
        chunk = CodeChunk(
            chunk_id="reas_test_003",
            file_path="/path/to/soar.md",
            element_type="knowledge",
            name="SOAR Result",
            line_start=1,
            line_end=30,
            docstring="SOAR execution result",
            language="markdown",
        )
        chunk.type = "reas"
        store.save_chunk(chunk)

        # Retrieve with type filter
        results = store.retrieve_by_activation(
            min_activation=0.0,
            limit=10,
            chunk_type="reas",
        )

        assert len(results) >= 1
        reas_chunks = [c for c in results if c.type == "reas"]
        assert len(reas_chunks) >= 1

    def test_reas_type_not_mixed_with_code(self, store):
        """Chunks with type='reas' should not appear in type='code' filter."""
        # Save a code chunk
        code_chunk = CodeChunk(
            chunk_id="code_test_001",
            file_path="/path/to/module.py",
            element_type="function",
            name="test_func",
            line_start=1,
            line_end=10,
            language="python",
        )
        # type is 'code' by default
        store.save_chunk(code_chunk)

        # Save a reas chunk
        reas_chunk = CodeChunk(
            chunk_id="reas_test_004",
            file_path="/path/to/soar.md",
            element_type="knowledge",
            name="SOAR Result",
            line_start=1,
            line_end=30,
            language="markdown",
        )
        reas_chunk.type = "reas"
        store.save_chunk(reas_chunk)

        # Retrieve only code type
        code_results = store.retrieve_by_activation(
            min_activation=0.0,
            limit=10,
            chunk_type="code",
        )

        # Should not include reas chunks
        reas_in_code = [c for c in code_results if c.type == "reas"]
        assert len(reas_in_code) == 0
