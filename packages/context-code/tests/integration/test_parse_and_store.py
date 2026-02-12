"""Integration test for parse → store → retrieve flow.

Tests the complete workflow:
1. Parse Python files to extract code chunks
2. Store chunks in storage backend
3. Retrieve and verify chunk data

This validates end-to-end functionality of:
- PythonParser
- SQLiteStore and MemoryStore
- CodeChunk serialization
- Round-trip data integrity
"""

import pytest

from aurora_context_code.languages.python import PythonParser
from aurora_core.store.memory import MemoryStore
from aurora_core.store.sqlite import SQLiteStore
from aurora_core.types import ChunkID


class TestParseAndStoreFlow:
    """Test complete parse → store → retrieve workflow."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return PythonParser()

    @pytest.fixture
    def memory_store(self):
        """Create memory store."""
        return MemoryStore()

    @pytest.fixture
    def sqlite_store(self):
        """Create SQLite store."""
        store = SQLiteStore(db_path=":memory:")
        yield store
        store.close()

    @pytest.fixture
    def sample_python_file(self, tmp_path):
        """Create sample Python file for parsing."""
        test_file = tmp_path / "sample.py"
        test_file.write_text(
            '''
"""Sample module for testing."""

def simple_function(x, y):
    """Add two numbers."""
    return x + y


class SampleClass:
    """A sample class."""

    def __init__(self, value):
        """Initialize with value."""
        self.value = value

    def process(self, data):
        """Process data."""
        result = []
        for item in data:
            if item > 0:
                result.append(item * 2)
        return result


def complex_function(items, threshold=10):
    """Complex function with multiple branches."""
    filtered = []
    for item in items:
        if item is None:
            continue
        elif item > threshold:
            filtered.append(item)
        elif item < 0:
            filtered.append(abs(item))

    return filtered
''',
        )
        return test_file

    def test_parse_store_retrieve_memory(self, parser, memory_store, sample_python_file):
        """Test complete flow with memory store."""
        # Parse file
        chunks = parser.parse(sample_python_file)
        assert len(chunks) > 0, "Parser should extract chunks"

        # Store all chunks and collect IDs
        chunk_ids = []
        for chunk in chunks:
            memory_store.save_chunk(chunk)
            chunk_ids.append(chunk.id)

        # Retrieve and verify each chunk
        for original_chunk in chunks:
            retrieved = memory_store.get_chunk(ChunkID(original_chunk.id))
            assert retrieved is not None, f"Chunk {original_chunk.id} should be retrievable"

            # Verify chunk data integrity
            assert retrieved.id == original_chunk.id
            assert retrieved.type == original_chunk.type
            assert retrieved.file_path == original_chunk.file_path
            assert retrieved.element_type == original_chunk.element_type
            assert retrieved.name == original_chunk.name
            assert retrieved.line_start == original_chunk.line_start
            assert retrieved.line_end == original_chunk.line_end

    def test_parse_store_retrieve_sqlite(self, parser, sqlite_store, sample_python_file):
        """Test complete flow with SQLite store."""
        # Parse file
        chunks = parser.parse(sample_python_file)
        assert len(chunks) > 0, "Parser should extract chunks"

        # Store all chunks
        for chunk in chunks:
            sqlite_store.save_chunk(chunk)

        # Retrieve and verify each chunk
        for original_chunk in chunks:
            retrieved = sqlite_store.get_chunk(ChunkID(original_chunk.id))
            assert retrieved is not None, f"Chunk {original_chunk.id} should be retrievable"

            # Verify chunk data integrity
            assert retrieved.id == original_chunk.id
            assert retrieved.file_path == original_chunk.file_path
            assert retrieved.name == original_chunk.name

    def test_parse_preserves_metadata(self, parser, memory_store, sample_python_file):
        """Test that parsing preserves all metadata through storage."""
        chunks = parser.parse(sample_python_file)

        # Find a chunk with docstring
        chunk_with_docstring = None
        for chunk in chunks:
            if chunk.docstring:
                chunk_with_docstring = chunk
                break

        assert chunk_with_docstring is not None, "Should find chunk with docstring"

        # Store and retrieve
        memory_store.save_chunk(chunk_with_docstring)
        retrieved = memory_store.get_chunk(ChunkID(chunk_with_docstring.id))

        # Verify metadata preserved
        assert retrieved.docstring == chunk_with_docstring.docstring
        assert retrieved.signature == chunk_with_docstring.signature
        assert retrieved.complexity_score == chunk_with_docstring.complexity_score
        assert retrieved.dependencies == chunk_with_docstring.dependencies

    def test_multiple_files_parse_and_store(self, parser, memory_store, tmp_path):
        """Test parsing and storing multiple files."""
        # Create multiple files
        file1 = tmp_path / "module1.py"
        file1.write_text(
            """
def func_a():
    return 1
""",
        )

        file2 = tmp_path / "module2.py"
        file2.write_text(
            """
def func_b():
    return 2
""",
        )

        file3 = tmp_path / "module3.py"
        file3.write_text(
            """
class ClassC:
    def method_c(self):
        return 3
""",
        )

        # Parse all files and store chunks
        all_chunks = []
        for file in [file1, file2, file3]:
            chunks = parser.parse(file)
            all_chunks.extend(chunks)
            for chunk in chunks:
                memory_store.save_chunk(chunk)

        assert len(all_chunks) >= 3, "Should extract chunks from all files"

        # Verify each is retrievable
        for chunk in all_chunks:
            retrieved = memory_store.get_chunk(ChunkID(chunk.id))
            assert retrieved is not None

    def test_chunk_update_flow(self, parser, memory_store, tmp_path):
        """Test updating stored chunks."""
        # Create file and parse
        test_file = tmp_path / "test.py"
        test_file.write_text(
            """
def original_function():
    return "original"
""",
        )

        chunks = parser.parse(test_file)
        assert len(chunks) == 1

        original_chunk = chunks[0]
        memory_store.save_chunk(original_chunk)

        # Simulate file modification
        test_file.write_text(
            '''
def original_function():
    """Now with docstring."""
    return "modified"
''',
        )

        # Re-parse
        updated_chunks = parser.parse(test_file)
        assert len(updated_chunks) == 1

        updated_chunk = updated_chunks[0]

        # Should have same ID but different content
        assert updated_chunk.id == original_chunk.id
        assert updated_chunk.docstring != original_chunk.docstring

        # Update in store
        memory_store.save_chunk(updated_chunk)

        # Retrieve and verify it's the updated version
        retrieved = memory_store.get_chunk(ChunkID(updated_chunk.id))
        assert retrieved.docstring == updated_chunk.docstring


class TestComplexParseStoreScenarios:
    """Test complex integration scenarios."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return PythonParser()

    @pytest.fixture
    def memory_store(self):
        """Create memory store."""
        return MemoryStore()

    @pytest.fixture
    def sqlite_file_store(self, tmp_path):
        """Create file-based SQLite store for persistence testing."""
        db_path = tmp_path / "test.db"
        store = SQLiteStore(db_path=str(db_path))
        yield store
        store.close()

    def test_large_file_parse_and_store(self, parser, sqlite_file_store, tmp_path):
        """Test parsing and storing a large file."""
        # Create large file with many functions
        large_file = tmp_path / "large.py"
        lines = []
        for i in range(50):
            lines.append(
                f'''
def function_{i}(x, y):
    """Function {i}."""
    if x > y:
        return x
    elif x < y:
        return y
    else:
        return 0
''',
            )
        large_file.write_text("\n".join(lines))

        # Parse
        chunks = parser.parse(large_file)
        assert len(chunks) == 50, "Should extract all 50 functions"

        # Store all
        for chunk in chunks:
            sqlite_file_store.save_chunk(chunk)

        # Spot check a few by retrieving them using actual chunk IDs
        test_indices = [0, 24, 49]
        for i in test_indices:
            chunk = chunks[i]
            retrieved = sqlite_file_store.get_chunk(ChunkID(chunk.id))
            assert retrieved is not None
            assert retrieved.name == f"function_{i}"

    def test_file_with_imports_parse_and_store(self, parser, memory_store, tmp_path):
        """Test parsing file with imports (dependencies)."""
        file_with_imports = tmp_path / "with_imports.py"
        file_with_imports.write_text(
            '''
import os
import sys
from pathlib import Path
from typing import List, Dict

def process_path(path: Path) -> str:
    """Process a path."""
    return str(path)


def process_list(items: List[str]) -> Dict[str, int]:
    """Process a list."""
    return {item: len(item) for item in items}
''',
        )

        chunks = parser.parse(file_with_imports)

        # Should extract functions
        assert len(chunks) >= 2

        # Store
        for chunk in chunks:
            memory_store.save_chunk(chunk)

        # Verify stored
        for chunk in chunks:
            retrieved = memory_store.get_chunk(ChunkID(chunk.id))
            assert retrieved is not None


class TestErrorHandling:
    """Test error handling in parse-store-retrieve flow."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return PythonParser()

    @pytest.fixture
    def memory_store(self):
        """Create memory store."""
        return MemoryStore()

    def test_parse_broken_file(self, parser, memory_store, tmp_path):
        """Test handling of broken Python files."""
        broken_file = tmp_path / "broken.py"
        broken_file.write_text(
            """
def broken_function(x, y)
    # Missing colon
    return x + y
""",
        )

        # Parser should handle gracefully (return empty or partial results)
        chunks = parser.parse(broken_file)
        # Should not crash, may return empty list
        assert isinstance(chunks, list)

    def test_retrieve_nonexistent_chunk(self, memory_store):
        """Test retrieving chunk that doesn't exist."""
        result = memory_store.get_chunk(ChunkID("nonexistent_id"))
        assert result is None, "Should return None for nonexistent chunk"

    def test_store_chunk_twice(self, memory_store, tmp_path):
        """Test storing same chunk twice (update behavior)."""
        parser = PythonParser()

        test_file = tmp_path / "test.py"
        test_file.write_text(
            """
def test_func():
    return 42
""",
        )

        chunks = parser.parse(test_file)
        assert len(chunks) == 1

        chunk = chunks[0]

        # Store twice
        memory_store.save_chunk(chunk)
        memory_store.save_chunk(chunk)

        # Should be retrievable
        retrieved = memory_store.get_chunk(ChunkID(chunk.id))
        assert retrieved is not None


class TestPersistence:
    """Test data persistence across store instances."""

    def test_sqlite_persistence(self, tmp_path):
        """Test that SQLite data persists across instances."""
        db_path = tmp_path / "persistent.db"
        parser = PythonParser()

        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text(
            """
def persistent_function():
    return "persisted"
""",
        )

        chunks = parser.parse(test_file)
        assert len(chunks) == 1
        chunk = chunks[0]

        # Save in first instance
        store1 = SQLiteStore(db_path=str(db_path))
        store1.save_chunk(chunk)
        store1.close()

        # Retrieve in second instance
        store2 = SQLiteStore(db_path=str(db_path))
        retrieved = store2.get_chunk(ChunkID(chunk.id))
        assert retrieved is not None
        assert retrieved.name == "persistent_function"
        store2.close()
