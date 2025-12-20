"""
Integration tests for Chunk types with Store implementations.

Tests that chunks can be properly saved and retrieved from storage.
"""

import pytest
import tempfile
import json
from pathlib import Path

from aurora_core.chunks import CodeChunk, ReasoningChunk
from aurora_core.store import MemoryStore, SQLiteStore


class TestCodeChunkWithMemoryStore:
    """Test CodeChunk integration with MemoryStore."""

    def test_save_and_retrieve_code_chunk(self):
        """Test saving and retrieving a CodeChunk."""
        store = MemoryStore()

        # Create chunk
        chunk = CodeChunk(
            chunk_id="code:test.py:func",
            file_path="/absolute/path/test.py",
            element_type="function",
            name="test_func",
            line_start=10,
            line_end=20,
            signature="def test_func() -> None",
            docstring="Test function",
            dependencies=["code:other.py:helper"],
            complexity_score=0.5,
            language="python",
        )

        # Save
        success = store.save_chunk(chunk)
        assert success is True

        # Retrieve
        retrieved = store.get_chunk("code:test.py:func")
        assert retrieved is not None
        assert isinstance(retrieved, CodeChunk)
        assert retrieved.id == chunk.id
        assert retrieved.name == chunk.name
        assert retrieved.file_path == chunk.file_path
        assert retrieved.line_start == chunk.line_start
        assert retrieved.line_end == chunk.line_end
        assert retrieved.signature == chunk.signature
        assert retrieved.docstring == chunk.docstring
        assert retrieved.dependencies == chunk.dependencies
        assert retrieved.complexity_score == chunk.complexity_score

    def test_code_chunk_serialization_through_store(self):
        """Test that CodeChunk JSON serialization works through store."""
        store = MemoryStore()

        chunk = CodeChunk(
            chunk_id="code:example.py:complex",
            file_path="/absolute/path/example.py",
            element_type="method",
            name="complex_method",
            line_start=50,
            line_end=100,
            complexity_score=0.85,
        )

        # Save
        store.save_chunk(chunk)

        # Retrieve and verify type
        retrieved = store.get_chunk("code:example.py:complex")
        assert type(retrieved) == CodeChunk
        assert retrieved.element_type == "method"

    def test_multiple_code_chunks(self):
        """Test storing multiple CodeChunks."""
        store = MemoryStore()

        chunks = [
            CodeChunk(
                chunk_id=f"code:test.py:func{i}",
                file_path="/absolute/path/test.py",
                element_type="function",
                name=f"func{i}",
                line_start=i * 10 + 1,  # Start from 1, not 0
                line_end=i * 10 + 5,
            )
            for i in range(10)
        ]

        # Save all
        for chunk in chunks:
            store.save_chunk(chunk)

        # Retrieve all
        for i, chunk in enumerate(chunks):
            retrieved = store.get_chunk(f"code:test.py:func{i}")
            assert retrieved is not None
            assert retrieved.name == f"func{i}"

    def test_code_chunk_update(self):
        """Test updating a CodeChunk."""
        store = MemoryStore()

        # Save initial
        chunk1 = CodeChunk(
            chunk_id="code:test.py:func",
            file_path="/absolute/path/test.py",
            element_type="function",
            name="test_func",
            line_start=10,
            line_end=20,
            complexity_score=0.3,
        )
        store.save_chunk(chunk1)

        # Update with different data
        chunk2 = CodeChunk(
            chunk_id="code:test.py:func",
            file_path="/absolute/path/test.py",
            element_type="function",
            name="test_func",
            line_start=10,
            line_end=25,  # Extended
            complexity_score=0.7,  # Increased
        )
        store.save_chunk(chunk2)

        # Retrieve
        retrieved = store.get_chunk("code:test.py:func")
        assert retrieved.line_end == 25
        assert retrieved.complexity_score == 0.7


class TestCodeChunkWithSQLiteStore:
    """Test CodeChunk integration with SQLiteStore."""

    def test_save_and_retrieve_code_chunk_sqlite(self):
        """Test CodeChunk with SQLite storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = SQLiteStore(str(db_path))

            try:
                # Create chunk
                chunk = CodeChunk(
                    chunk_id="code:test.py:func",
                    file_path="/absolute/path/test.py",
                    element_type="function",
                    name="test_func",
                    line_start=10,
                    line_end=20,
                )

                # Save
                success = store.save_chunk(chunk)
                assert success is True

                # Retrieve
                retrieved = store.get_chunk("code:test.py:func")
                assert retrieved is not None
                assert isinstance(retrieved, CodeChunk)
                assert retrieved.id == chunk.id
                assert retrieved.name == chunk.name

            finally:
                store.close()

    def test_code_chunk_persistence_sqlite(self):
        """Test that CodeChunk persists across store instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            # Save with first store instance
            store1 = SQLiteStore(str(db_path))
            chunk = CodeChunk(
                chunk_id="code:persistent.py:func",
                file_path="/absolute/path/persistent.py",
                element_type="function",
                name="persistent_func",
                line_start=1,
                line_end=10,
                signature="def persistent_func() -> str",
            )
            store1.save_chunk(chunk)
            store1.close()

            # Retrieve with second store instance
            store2 = SQLiteStore(str(db_path))
            retrieved = store2.get_chunk("code:persistent.py:func")
            assert retrieved is not None
            assert retrieved.signature == "def persistent_func() -> str"
            store2.close()


class TestReasoningChunkWithStore:
    """Test ReasoningChunk integration with stores."""

    def test_save_and_retrieve_reasoning_chunk(self):
        """Test saving and retrieving a ReasoningChunk."""
        store = MemoryStore()

        chunk = ReasoningChunk(
            chunk_id="reasoning:pattern1",
            pattern_type="inference",
            premise="Input data",
            conclusion="Output result",
            confidence=0.85,
            evidence=["code:test.py:func1"],
        )

        # Save
        success = store.save_chunk(chunk)
        assert success is True

        # Retrieve
        retrieved = store.get_chunk("reasoning:pattern1")
        assert retrieved is not None
        assert isinstance(retrieved, ReasoningChunk)
        assert retrieved.pattern_type == "inference"
        assert retrieved.confidence == 0.85


class TestMixedChunkTypes:
    """Test storing different chunk types together."""

    def test_store_mixed_chunk_types(self):
        """Test storing both CodeChunks and ReasoningChunks."""
        store = MemoryStore()

        # Create different chunk types
        code_chunk = CodeChunk(
            chunk_id="code:test.py:func",
            file_path="/absolute/path/test.py",
            element_type="function",
            name="test_func",
            line_start=10,
            line_end=20,
        )

        reasoning_chunk = ReasoningChunk(
            chunk_id="reasoning:pattern1",
            pattern_type="inference",
            confidence=0.9,
        )

        # Save both
        store.save_chunk(code_chunk)
        store.save_chunk(reasoning_chunk)

        # Retrieve both
        retrieved_code = store.get_chunk("code:test.py:func")
        retrieved_reasoning = store.get_chunk("reasoning:pattern1")

        assert isinstance(retrieved_code, CodeChunk)
        assert isinstance(retrieved_reasoning, ReasoningChunk)

    def test_chunk_type_preservation(self):
        """Test that chunk types are correctly preserved through storage."""
        store = MemoryStore()

        chunks = [
            CodeChunk(
                chunk_id="code:a.py:func",
                file_path="/absolute/a.py",
                element_type="function",
                name="func",
                line_start=1,
                line_end=5,
            ),
            ReasoningChunk(
                chunk_id="reasoning:r1",
                pattern_type="deduction",
            ),
        ]

        # Save all
        for chunk in chunks:
            store.save_chunk(chunk)

        # Verify types
        code = store.get_chunk("code:a.py:func")
        reasoning = store.get_chunk("reasoning:r1")

        assert code.type == "code"
        assert reasoning.type == "reasoning"


class TestChunkValidationInStore:
    """Test that store enforces chunk validation."""

    def test_invalid_chunk_rejected(self):
        """Test that invalid chunks are rejected by store."""
        store = MemoryStore()

        # This should fail validation (line_start = 0)
        with pytest.raises(ValueError, match="line_start must be > 0"):
            CodeChunk(
                chunk_id="code:invalid.py:func",
                file_path="/absolute/invalid.py",
                element_type="function",
                name="invalid",
                line_start=0,
                line_end=10,
            )

    def test_chunk_validation_on_retrieval(self):
        """Test that retrieved chunks pass validation."""
        store = MemoryStore()

        chunk = CodeChunk(
            chunk_id="code:valid.py:func",
            file_path="/absolute/valid.py",
            element_type="function",
            name="valid_func",
            line_start=10,
            line_end=20,
        )

        store.save_chunk(chunk)
        retrieved = store.get_chunk("code:valid.py:func")

        # Should not raise
        assert retrieved.validate() is True


class TestChunkRoundTripIntegrity:
    """Test data integrity through save/retrieve cycles."""

    def test_code_chunk_all_fields_preserved(self):
        """Test that all CodeChunk fields survive round-trip."""
        store = MemoryStore()

        original = CodeChunk(
            chunk_id="code:complete.py:func",
            file_path="/absolute/path/complete.py",
            element_type="method",
            name="complete_method",
            line_start=100,
            line_end=200,
            signature="def complete_method(self, a: int, b: str) -> Dict[str, Any]",
            docstring="Complete method with all fields",
            dependencies=["code:dep1.py:func", "code:dep2.py:helper"],
            complexity_score=0.75,
            language="python",
        )

        # Round trip
        store.save_chunk(original)
        retrieved = store.get_chunk("code:complete.py:func")

        # Verify all fields
        assert retrieved.id == original.id
        assert retrieved.type == original.type
        assert retrieved.file_path == original.file_path
        assert retrieved.element_type == original.element_type
        assert retrieved.name == original.name
        assert retrieved.line_start == original.line_start
        assert retrieved.line_end == original.line_end
        assert retrieved.signature == original.signature
        assert retrieved.docstring == original.docstring
        assert retrieved.dependencies == original.dependencies
        assert retrieved.complexity_score == original.complexity_score
        assert retrieved.language == original.language

    def test_reasoning_chunk_all_fields_preserved(self):
        """Test that all ReasoningChunk fields survive round-trip."""
        store = MemoryStore()

        original = ReasoningChunk(
            chunk_id="reasoning:complete",
            pattern_type="deductive",
            premise="Given conditions",
            conclusion="Derived result",
            confidence=0.95,
            evidence=["code:a.py:func", "code:b.py:helper"],
        )

        # Round trip
        store.save_chunk(original)
        retrieved = store.get_chunk("reasoning:complete")

        # Verify all fields
        assert retrieved.id == original.id
        assert retrieved.type == original.type
        assert retrieved.pattern_type == original.pattern_type
        assert retrieved.premise == original.premise
        assert retrieved.conclusion == original.conclusion
        assert retrieved.confidence == original.confidence
        assert retrieved.evidence == original.evidence
