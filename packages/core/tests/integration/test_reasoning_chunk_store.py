"""Integration test for ReasoningChunk storage and retrieval.

Tests the complete workflow:
1. Create ReasoningChunk instances
2. Store chunks in storage backend (SQLite and Memory)
3. Retrieve and verify chunk data integrity
4. Test activation updates

This validates end-to-end functionality of:
- ReasoningChunk serialization (to_json)
- ReasoningChunk deserialization (from_json)
- Store.save_chunk with ReasoningChunk
- Store.get_chunk retrieval
- Store.update_activation
- Round-trip data integrity
"""

import pytest

from aurora_core.chunks import ReasoningChunk
from aurora_core.store.memory import MemoryStore
from aurora_core.store.sqlite import SQLiteStore


class TestReasoningChunkStoreIntegration:
    """Test ReasoningChunk storage integration with Store backends."""

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
    def simple_reasoning_chunk(self):
        """Create a simple ReasoningChunk for testing."""
        return ReasoningChunk(
            chunk_id="reasoning_test_simple",
            pattern="implement feature X",
            complexity="SIMPLE",
            success_score=0.8,
        )

    @pytest.fixture
    def complex_reasoning_chunk(self):
        """Create a complex ReasoningChunk with all fields populated."""
        return ReasoningChunk(
            chunk_id="reasoning_test_complex",
            pattern="refactor module Y with comprehensive tests",
            complexity="COMPLEX",
            subgoals=[
                {
                    "id": "sg1",
                    "description": "Parse existing code",
                    "agent": "parser-agent",
                    "dependencies": [],
                },
                {
                    "id": "sg2",
                    "description": "Refactor implementation",
                    "agent": "editor-agent",
                    "dependencies": ["sg1"],
                },
                {
                    "id": "sg3",
                    "description": "Write comprehensive tests",
                    "agent": "test-agent",
                    "dependencies": ["sg2"],
                },
            ],
            execution_order=[
                {"sequential": ["sg1"]},
                {"sequential": ["sg2"]},
                {"parallel": [["sg3"], ["sg4"]]},
            ],
            tools_used=["parser", "editor", "analyzer", "test-runner"],
            tool_sequence=[
                {"tool": "parser", "file": "module.py", "duration_ms": 100},
                {"tool": "editor", "file": "module.py", "lines_changed": 150},
                {"tool": "analyzer", "target": "module.py"},
                {"tool": "test-runner", "tests_run": 25, "tests_passed": 25},
            ],
            success_score=0.92,
            metadata={
                "query_id": "q123",
                "duration_ms": 5000,
                "llm_calls": 8,
                "total_cost_usd": 0.0125,
                "subgoals_completed": 3,
                "subgoals_failed": 0,
                "files_modified": 5,
                "user_interactions": 2,
            },
        )

    # ===== Memory Store Tests =====

    def test_memory_store_save_and_retrieve_simple_chunk(
        self,
        memory_store,
        simple_reasoning_chunk,
    ):
        """Test saving and retrieving simple ReasoningChunk from MemoryStore."""
        # Save chunk
        memory_store.save_chunk(simple_reasoning_chunk)

        # Retrieve chunk
        retrieved_chunk = memory_store.get_chunk(simple_reasoning_chunk.id)

        # Verify retrieval
        assert retrieved_chunk is not None
        assert isinstance(retrieved_chunk, ReasoningChunk)
        assert retrieved_chunk.id == simple_reasoning_chunk.id
        assert retrieved_chunk.pattern == simple_reasoning_chunk.pattern
        assert retrieved_chunk.complexity == simple_reasoning_chunk.complexity
        assert retrieved_chunk.success_score == simple_reasoning_chunk.success_score

    def test_memory_store_save_and_retrieve_complex_chunk(
        self,
        memory_store,
        complex_reasoning_chunk,
    ):
        """Test saving and retrieving complex ReasoningChunk from MemoryStore."""
        # Save chunk
        memory_store.save_chunk(complex_reasoning_chunk)

        # Retrieve chunk
        retrieved_chunk = memory_store.get_chunk(complex_reasoning_chunk.id)

        # Verify all fields preserved
        assert retrieved_chunk is not None
        assert isinstance(retrieved_chunk, ReasoningChunk)
        assert retrieved_chunk.id == complex_reasoning_chunk.id
        assert retrieved_chunk.pattern == complex_reasoning_chunk.pattern
        assert retrieved_chunk.complexity == complex_reasoning_chunk.complexity
        assert retrieved_chunk.subgoals == complex_reasoning_chunk.subgoals
        assert retrieved_chunk.execution_order == complex_reasoning_chunk.execution_order
        assert retrieved_chunk.tools_used == complex_reasoning_chunk.tools_used
        assert retrieved_chunk.tool_sequence == complex_reasoning_chunk.tool_sequence
        assert retrieved_chunk.success_score == complex_reasoning_chunk.success_score
        assert retrieved_chunk.metadata == complex_reasoning_chunk.metadata

    def test_memory_store_round_trip_preserves_nested_data(
        self,
        memory_store,
        complex_reasoning_chunk,
    ):
        """Test that nested data structures are preserved through round-trip."""
        # Save and retrieve
        memory_store.save_chunk(complex_reasoning_chunk)
        retrieved_chunk = memory_store.get_chunk(complex_reasoning_chunk.id)

        # Verify nested subgoal structure
        assert len(retrieved_chunk.subgoals) == 3
        assert retrieved_chunk.subgoals[0]["id"] == "sg1"
        assert retrieved_chunk.subgoals[0]["description"] == "Parse existing code"
        assert retrieved_chunk.subgoals[1]["dependencies"] == ["sg1"]
        assert retrieved_chunk.subgoals[2]["dependencies"] == ["sg2"]

        # Verify nested execution_order structure
        assert len(retrieved_chunk.execution_order) == 3
        assert "sequential" in retrieved_chunk.execution_order[0]
        assert "parallel" in retrieved_chunk.execution_order[2]

        # Verify nested tool_sequence
        assert len(retrieved_chunk.tool_sequence) == 4
        assert retrieved_chunk.tool_sequence[0]["tool"] == "parser"
        assert retrieved_chunk.tool_sequence[3]["tests_passed"] == 25

    def test_memory_store_update_activation(self, memory_store, simple_reasoning_chunk):
        """Test updating activation for ReasoningChunk in MemoryStore."""
        # Save chunk
        memory_store.save_chunk(simple_reasoning_chunk)

        # Update activation (should not raise)
        memory_store.update_activation(simple_reasoning_chunk.id, 0.2)
        memory_store.update_activation(simple_reasoning_chunk.id, 0.05)
        memory_store.update_activation(simple_reasoning_chunk.id, -0.1)

        # Verify chunk can still be retrieved after activation updates
        retrieved_chunk = memory_store.get_chunk(simple_reasoning_chunk.id)
        assert retrieved_chunk is not None
        assert retrieved_chunk.id == simple_reasoning_chunk.id

    def test_memory_store_multiple_chunks(self, memory_store):
        """Test storing and retrieving multiple ReasoningChunks."""
        # Create multiple chunks
        chunks = [
            ReasoningChunk(
                chunk_id=f"reasoning_multi_{i}",
                pattern=f"pattern {i}",
                complexity="MEDIUM",
                success_score=0.5 + (i * 0.1),
            )
            for i in range(5)
        ]

        # Save all chunks
        for chunk in chunks:
            memory_store.save_chunk(chunk)

        # Retrieve and verify all chunks
        for original_chunk in chunks:
            retrieved_chunk = memory_store.get_chunk(original_chunk.id)
            assert retrieved_chunk is not None
            assert retrieved_chunk.id == original_chunk.id
            assert retrieved_chunk.pattern == original_chunk.pattern
            assert retrieved_chunk.success_score == original_chunk.success_score

    # ===== SQLite Store Tests =====

    def test_sqlite_store_save_and_retrieve_simple_chunk(
        self,
        sqlite_store,
        simple_reasoning_chunk,
    ):
        """Test saving and retrieving simple ReasoningChunk from SQLiteStore."""
        # Save chunk
        sqlite_store.save_chunk(simple_reasoning_chunk)

        # Retrieve chunk
        retrieved_chunk = sqlite_store.get_chunk(simple_reasoning_chunk.id)

        # Verify retrieval
        assert retrieved_chunk is not None
        assert isinstance(retrieved_chunk, ReasoningChunk)
        assert retrieved_chunk.id == simple_reasoning_chunk.id
        assert retrieved_chunk.pattern == simple_reasoning_chunk.pattern
        assert retrieved_chunk.complexity == simple_reasoning_chunk.complexity
        assert retrieved_chunk.success_score == simple_reasoning_chunk.success_score

    def test_sqlite_store_save_and_retrieve_complex_chunk(
        self,
        sqlite_store,
        complex_reasoning_chunk,
    ):
        """Test saving and retrieving complex ReasoningChunk from SQLiteStore."""
        # Save chunk
        sqlite_store.save_chunk(complex_reasoning_chunk)

        # Retrieve chunk
        retrieved_chunk = sqlite_store.get_chunk(complex_reasoning_chunk.id)

        # Verify all fields preserved
        assert retrieved_chunk is not None
        assert isinstance(retrieved_chunk, ReasoningChunk)
        assert retrieved_chunk.id == complex_reasoning_chunk.id
        assert retrieved_chunk.pattern == complex_reasoning_chunk.pattern
        assert retrieved_chunk.complexity == complex_reasoning_chunk.complexity
        assert retrieved_chunk.subgoals == complex_reasoning_chunk.subgoals
        assert retrieved_chunk.execution_order == complex_reasoning_chunk.execution_order
        assert retrieved_chunk.tools_used == complex_reasoning_chunk.tools_used
        assert retrieved_chunk.tool_sequence == complex_reasoning_chunk.tool_sequence
        assert retrieved_chunk.success_score == complex_reasoning_chunk.success_score
        assert retrieved_chunk.metadata == complex_reasoning_chunk.metadata

    def test_sqlite_store_round_trip_preserves_nested_data(
        self,
        sqlite_store,
        complex_reasoning_chunk,
    ):
        """Test that nested data structures are preserved through SQLite round-trip."""
        # Save and retrieve
        sqlite_store.save_chunk(complex_reasoning_chunk)
        retrieved_chunk = sqlite_store.get_chunk(complex_reasoning_chunk.id)

        # Verify nested subgoal structure
        assert len(retrieved_chunk.subgoals) == 3
        assert retrieved_chunk.subgoals[0]["id"] == "sg1"
        assert retrieved_chunk.subgoals[1]["dependencies"] == ["sg1"]

        # Verify nested execution_order structure
        assert len(retrieved_chunk.execution_order) == 3
        assert "sequential" in retrieved_chunk.execution_order[0]

        # Verify nested tool_sequence
        assert len(retrieved_chunk.tool_sequence) == 4
        assert retrieved_chunk.tool_sequence[0]["tool"] == "parser"

    def test_sqlite_store_update_activation(self, sqlite_store, simple_reasoning_chunk):
        """Test updating activation for ReasoningChunk in SQLiteStore."""
        # Save chunk
        sqlite_store.save_chunk(simple_reasoning_chunk)

        # Update activation (should not raise)
        sqlite_store.update_activation(simple_reasoning_chunk.id, 0.2)
        sqlite_store.update_activation(simple_reasoning_chunk.id, 0.05)
        sqlite_store.update_activation(simple_reasoning_chunk.id, -0.1)

        # Verify chunk can still be retrieved after activation updates
        retrieved_chunk = sqlite_store.get_chunk(simple_reasoning_chunk.id)
        assert retrieved_chunk is not None
        assert retrieved_chunk.id == simple_reasoning_chunk.id

    def test_sqlite_store_multiple_chunks(self, sqlite_store):
        """Test storing and retrieving multiple ReasoningChunks in SQLite."""
        # Create multiple chunks
        chunks = [
            ReasoningChunk(
                chunk_id=f"reasoning_sqlite_{i}",
                pattern=f"sqlite pattern {i}",
                complexity="COMPLEX",
                success_score=0.6 + (i * 0.05),
            )
            for i in range(5)
        ]

        # Save all chunks
        for chunk in chunks:
            sqlite_store.save_chunk(chunk)

        # Retrieve and verify all chunks
        for original_chunk in chunks:
            retrieved_chunk = sqlite_store.get_chunk(original_chunk.id)
            assert retrieved_chunk is not None
            assert retrieved_chunk.id == original_chunk.id
            assert retrieved_chunk.pattern == original_chunk.pattern
            assert retrieved_chunk.success_score == original_chunk.success_score

    def test_sqlite_store_persistence_across_connections(self, tmp_path):
        """Test that ReasoningChunks persist across SQLite connection closes/opens."""
        db_path = tmp_path / "test_reasoning.db"

        chunk = ReasoningChunk(
            chunk_id="reasoning_persist",
            pattern="persistent pattern",
            complexity="MEDIUM",
            success_score=0.75,
            metadata={"test": "persistence"},
        )

        # Save chunk and close store
        store1 = SQLiteStore(db_path=str(db_path))
        store1.save_chunk(chunk)
        store1.close()

        # Open new store and retrieve chunk
        store2 = SQLiteStore(db_path=str(db_path))
        retrieved_chunk = store2.get_chunk(chunk.id)
        store2.close()

        # Verify data persisted
        assert retrieved_chunk is not None
        assert retrieved_chunk.id == chunk.id
        assert retrieved_chunk.pattern == chunk.pattern
        assert retrieved_chunk.complexity == chunk.complexity
        assert retrieved_chunk.success_score == chunk.success_score
        assert retrieved_chunk.metadata == chunk.metadata

    # ===== Edge Cases =====

    def test_unicode_in_pattern_preserved(self, memory_store, sqlite_store):
        """Test that unicode characters in pattern are preserved."""
        chunk = ReasoningChunk(
            chunk_id="reasoning_unicode",
            pattern="Implement feature with émojis 🚀 and spëcial çhars",
            complexity="SIMPLE",
            success_score=0.8,
        )

        # Test MemoryStore
        memory_store.save_chunk(chunk)
        retrieved_memory = memory_store.get_chunk(chunk.id)
        assert retrieved_memory.pattern == chunk.pattern

        # Test SQLiteStore
        sqlite_store.save_chunk(chunk)
        retrieved_sqlite = sqlite_store.get_chunk(chunk.id)
        assert retrieved_sqlite.pattern == chunk.pattern

    def test_empty_lists_preserved(self, memory_store, sqlite_store):
        """Test that empty lists are preserved through storage."""
        chunk = ReasoningChunk(
            chunk_id="reasoning_empty",
            pattern="test pattern",
            complexity="SIMPLE",
            subgoals=[],
            execution_order=[],
            tools_used=[],
            tool_sequence=[],
            success_score=0.8,
        )

        # Test MemoryStore
        memory_store.save_chunk(chunk)
        retrieved_memory = memory_store.get_chunk(chunk.id)
        assert retrieved_memory.subgoals == []
        assert retrieved_memory.execution_order == []
        assert retrieved_memory.tools_used == []
        assert retrieved_memory.tool_sequence == []

        # Test SQLiteStore
        sqlite_store.save_chunk(chunk)
        retrieved_sqlite = sqlite_store.get_chunk(chunk.id)
        assert retrieved_sqlite.subgoals == []
        assert retrieved_sqlite.execution_order == []
        assert retrieved_sqlite.tools_used == []
        assert retrieved_sqlite.tool_sequence == []

    def test_float_precision_preserved(self, memory_store, sqlite_store):
        """Test that float precision in success_score is preserved."""
        chunk = ReasoningChunk(
            chunk_id="reasoning_float",
            pattern="test pattern",
            complexity="SIMPLE",
            success_score=0.123456789,
        )

        # Test MemoryStore
        memory_store.save_chunk(chunk)
        retrieved_memory = memory_store.get_chunk(chunk.id)
        assert retrieved_memory.success_score == 0.123456789

        # Test SQLiteStore
        sqlite_store.save_chunk(chunk)
        retrieved_sqlite = sqlite_store.get_chunk(chunk.id)
        # SQLite may have slight precision differences, so check within tolerance
        assert abs(retrieved_sqlite.success_score - 0.123456789) < 1e-9

    def test_large_metadata_preserved(self, memory_store, sqlite_store):
        """Test that large metadata dictionaries are preserved."""
        large_metadata = {f"key_{i}": f"value_{i}" for i in range(100)}

        chunk = ReasoningChunk(
            chunk_id="reasoning_large_meta",
            pattern="test pattern",
            complexity="SIMPLE",
            success_score=0.8,
            metadata=large_metadata,
        )

        # Test MemoryStore
        memory_store.save_chunk(chunk)
        retrieved_memory = memory_store.get_chunk(chunk.id)
        assert retrieved_memory.metadata == large_metadata

        # Test SQLiteStore
        sqlite_store.save_chunk(chunk)
        retrieved_sqlite = sqlite_store.get_chunk(chunk.id)
        assert retrieved_sqlite.metadata == large_metadata

    # ===== Activation Tracking Tests =====

    def test_activation_multiple_updates(self, memory_store):
        """Test multiple activation updates work correctly."""
        chunk = ReasoningChunk(
            chunk_id="reasoning_activation",
            pattern="test pattern",
            complexity="SIMPLE",
            success_score=0.8,
        )

        memory_store.save_chunk(chunk)

        # Apply multiple updates (should not raise)
        memory_store.update_activation(chunk.id, 0.2)  # High score pattern
        memory_store.update_activation(chunk.id, 0.05)  # Medium score pattern
        memory_store.update_activation(chunk.id, -0.1)  # Low score penalty

        # Verify chunk can still be retrieved after multiple updates
        retrieved_chunk = memory_store.get_chunk(chunk.id)
        assert retrieved_chunk is not None
        assert retrieved_chunk.id == chunk.id

    def test_negative_activation_from_failures(self, memory_store):
        """Test that failed patterns receive negative activation updates."""
        chunk = ReasoningChunk(
            chunk_id="reasoning_failure",
            pattern="failed pattern",
            complexity="SIMPLE",
            success_score=0.2,  # Low score
        )

        memory_store.save_chunk(chunk)

        # Apply negative update for failure (should not raise)
        memory_store.update_activation(chunk.id, -0.1)

        # Verify chunk can still be retrieved after negative update
        retrieved_chunk = memory_store.get_chunk(chunk.id)
        assert retrieved_chunk is not None
        assert retrieved_chunk.id == chunk.id
        assert retrieved_chunk.success_score == 0.2
