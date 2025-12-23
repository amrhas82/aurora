"""
Unit tests for ReasoningChunk implementation.

Tests the full ReasoningChunk implementation including validation,
serialization, and integration with the chunk system.
"""

from datetime import datetime

import pytest

from aurora_core.chunks.reasoning_chunk import ReasoningChunk


class TestReasoningChunkInitialization:
    """Test suite for ReasoningChunk initialization."""

    def test_minimal_initialization(self):
        """Test creating chunk with minimal required fields."""
        chunk = ReasoningChunk(chunk_id="test-reasoning-1", pattern="implement feature X")

        assert chunk.id == "test-reasoning-1"
        assert chunk.type == "reasoning"
        assert chunk.pattern == "implement feature X"
        assert chunk.complexity == "SIMPLE"
        assert chunk.subgoals == []
        assert chunk.execution_order == []
        assert chunk.tools_used == []
        assert chunk.tool_sequence == []
        assert chunk.success_score == 0.0
        assert chunk.metadata == {}

    def test_full_initialization(self):
        """Test creating chunk with all fields populated."""
        subgoals = [{"id": "sg1", "description": "Parse file", "agent": "parser"}]
        execution_order = [{"sequential": ["sg1"]}]
        tools_used = ["parser", "editor"]
        tool_sequence = [{"tool": "parser", "file": "test.py"}]
        metadata = {"query_id": "q123", "duration_ms": 1500}

        chunk = ReasoningChunk(
            chunk_id="test-reasoning-2",
            pattern="refactor module X",
            complexity="COMPLEX",
            subgoals=subgoals,
            execution_order=execution_order,
            tools_used=tools_used,
            tool_sequence=tool_sequence,
            success_score=0.85,
            metadata=metadata,
        )

        assert chunk.id == "test-reasoning-2"
        assert chunk.type == "reasoning"
        assert chunk.pattern == "refactor module X"
        assert chunk.complexity == "COMPLEX"
        assert chunk.subgoals == subgoals
        assert chunk.execution_order == execution_order
        assert chunk.tools_used == tools_used
        assert chunk.tool_sequence == tool_sequence
        assert chunk.success_score == 0.85
        assert chunk.metadata == metadata

    def test_timestamps_auto_created(self):
        """Test that created_at and updated_at are auto-populated."""
        chunk = ReasoningChunk(chunk_id="test-reasoning-3", pattern="test pattern")

        # Verify timestamps are datetime objects and recent (use UTC)
        assert isinstance(chunk.created_at, datetime)
        assert isinstance(chunk.updated_at, datetime)
        # Timestamps should be within last 10 seconds (reasonable for test execution)
        now = datetime.utcnow()
        time_diff = abs((now - chunk.created_at).total_seconds())
        assert time_diff < 10, f"Timestamp too old: {time_diff}s"


class TestReasoningChunkValidation:
    """Test suite for ReasoningChunk validation."""

    def test_valid_chunk_passes_validation(self):
        """Test that valid chunk passes validation."""
        chunk = ReasoningChunk(
            chunk_id="test-valid", pattern="valid pattern", complexity="MEDIUM", success_score=0.5
        )
        # Should not raise
        assert chunk.validate() is True

    def test_empty_pattern_fails_validation(self):
        """Test that empty pattern fails validation."""
        with pytest.raises(ValueError, match="pattern must not be empty"):
            ReasoningChunk(chunk_id="test-empty-pattern", pattern="")

    def test_whitespace_only_pattern_fails_validation(self):
        """Test that whitespace-only pattern fails validation."""
        with pytest.raises(ValueError, match="pattern must not be empty"):
            ReasoningChunk(chunk_id="test-whitespace-pattern", pattern="   ")

    def test_success_score_below_range_fails(self):
        """Test that success_score below 0.0 fails validation."""
        with pytest.raises(ValueError, match="success_score must be in"):
            ReasoningChunk(chunk_id="test-low-score", pattern="test pattern", success_score=-0.1)

    def test_success_score_above_range_fails(self):
        """Test that success_score above 1.0 fails validation."""
        with pytest.raises(ValueError, match="success_score must be in"):
            ReasoningChunk(chunk_id="test-high-score", pattern="test pattern", success_score=1.1)

    def test_success_score_at_boundaries_passes(self):
        """Test that success_score at 0.0 and 1.0 passes validation."""
        chunk1 = ReasoningChunk(
            chunk_id="test-score-zero", pattern="test pattern", success_score=0.0
        )
        assert chunk1.success_score == 0.0

        chunk2 = ReasoningChunk(
            chunk_id="test-score-one", pattern="test pattern", success_score=1.0
        )
        assert chunk2.success_score == 1.0

    def test_invalid_complexity_fails(self):
        """Test that invalid complexity level fails validation."""
        with pytest.raises(ValueError, match="complexity must be one of"):
            ReasoningChunk(
                chunk_id="test-invalid-complexity", pattern="test pattern", complexity="INVALID"
            )

    def test_valid_complexity_levels_pass(self):
        """Test that all valid complexity levels pass validation."""
        for complexity in ["SIMPLE", "MEDIUM", "COMPLEX", "CRITICAL"]:
            chunk = ReasoningChunk(
                chunk_id=f"test-{complexity.lower()}", pattern="test pattern", complexity=complexity
            )
            assert chunk.complexity == complexity

    def test_non_list_subgoals_fails(self):
        """Test that non-list subgoals fails validation."""
        with pytest.raises(ValueError, match="subgoals must be a list"):
            ReasoningChunk(
                chunk_id="test-invalid-subgoals",
                pattern="test pattern",
                subgoals="not a list",  # type: ignore
            )

    def test_non_list_execution_order_fails(self):
        """Test that non-list execution_order fails validation."""
        with pytest.raises(ValueError, match="execution_order must be a list"):
            ReasoningChunk(
                chunk_id="test-invalid-order",
                pattern="test pattern",
                execution_order="not a list",  # type: ignore
            )

    def test_non_list_tools_used_fails(self):
        """Test that non-list tools_used fails validation."""
        with pytest.raises(ValueError, match="tools_used must be a list"):
            ReasoningChunk(
                chunk_id="test-invalid-tools",
                pattern="test pattern",
                tools_used="not a list",  # type: ignore
            )

    def test_non_list_tool_sequence_fails(self):
        """Test that non-list tool_sequence fails validation."""
        with pytest.raises(ValueError, match="tool_sequence must be a list"):
            ReasoningChunk(
                chunk_id="test-invalid-sequence",
                pattern="test pattern",
                tool_sequence="not a list",  # type: ignore
            )


class TestReasoningChunkSerialization:
    """Test suite for ReasoningChunk serialization (to_json)."""

    def test_to_json_minimal(self):
        """Test serialization with minimal fields."""
        chunk = ReasoningChunk(chunk_id="test-json-1", pattern="test pattern")

        json_data = chunk.to_json()

        assert json_data["id"] == "test-json-1"
        assert json_data["type"] == "reasoning"
        assert json_data["content"]["pattern"] == "test pattern"
        assert json_data["content"]["complexity"] == "SIMPLE"
        assert json_data["content"]["subgoals"] == []
        assert json_data["content"]["execution_order"] == []
        assert json_data["content"]["tools_used"] == []
        assert json_data["content"]["tool_sequence"] == []
        assert json_data["content"]["success_score"] == 0.0
        assert "created_at" in json_data["metadata"]
        assert "last_modified" in json_data["metadata"]

    def test_to_json_full(self):
        """Test serialization with all fields populated."""
        subgoals = [{"id": "sg1", "description": "Step 1"}, {"id": "sg2", "description": "Step 2"}]
        execution_order = [{"sequential": ["sg1", "sg2"]}]
        tools_used = ["parser", "editor", "analyzer"]
        tool_sequence = [
            {"tool": "parser", "target": "file1.py"},
            {"tool": "editor", "target": "file1.py"},
            {"tool": "analyzer", "target": "file1.py"},
        ]
        metadata = {"query_id": "q456", "duration_ms": 2500, "agent_count": 3}

        chunk = ReasoningChunk(
            chunk_id="test-json-2",
            pattern="complex operation",
            complexity="COMPLEX",
            subgoals=subgoals,
            execution_order=execution_order,
            tools_used=tools_used,
            tool_sequence=tool_sequence,
            success_score=0.92,
            metadata=metadata,
        )

        json_data = chunk.to_json()

        assert json_data["id"] == "test-json-2"
        assert json_data["type"] == "reasoning"
        assert json_data["content"]["pattern"] == "complex operation"
        assert json_data["content"]["complexity"] == "COMPLEX"
        assert json_data["content"]["subgoals"] == subgoals
        assert json_data["content"]["execution_order"] == execution_order
        assert json_data["content"]["tools_used"] == tools_used
        assert json_data["content"]["tool_sequence"] == tool_sequence
        assert json_data["content"]["success_score"] == 0.92
        assert json_data["metadata"]["query_id"] == "q456"
        assert json_data["metadata"]["duration_ms"] == 2500
        assert json_data["metadata"]["agent_count"] == 3
        assert "created_at" in json_data["metadata"]
        assert "last_modified" in json_data["metadata"]

    def test_to_json_timestamps_are_iso_format(self):
        """Test that timestamps are serialized in ISO format."""
        chunk = ReasoningChunk(chunk_id="test-json-timestamps", pattern="test pattern")

        json_data = chunk.to_json()

        # Verify ISO format by parsing
        created_at = datetime.fromisoformat(json_data["metadata"]["created_at"])
        last_modified = datetime.fromisoformat(json_data["metadata"]["last_modified"])

        assert isinstance(created_at, datetime)
        assert isinstance(last_modified, datetime)


class TestReasoningChunkDeserialization:
    """Test suite for ReasoningChunk deserialization (from_json)."""

    def test_from_json_minimal(self):
        """Test deserialization with minimal fields."""
        json_data = {
            "id": "test-deser-1",
            "type": "reasoning",
            "content": {
                "pattern": "test pattern",
                "complexity": "SIMPLE",
                "subgoals": [],
                "execution_order": [],
                "tools_used": [],
                "tool_sequence": [],
                "success_score": 0.0,
            },
            "metadata": {
                "created_at": "2025-01-01T12:00:00",
                "last_modified": "2025-01-01T12:00:00",
            },
        }

        chunk = ReasoningChunk.from_json(json_data)

        assert chunk.id == "test-deser-1"
        assert chunk.type == "reasoning"
        assert chunk.pattern == "test pattern"
        assert chunk.complexity == "SIMPLE"
        assert chunk.subgoals == []
        assert chunk.execution_order == []
        assert chunk.tools_used == []
        assert chunk.tool_sequence == []
        assert chunk.success_score == 0.0

    def test_from_json_full(self):
        """Test deserialization with all fields populated."""
        json_data = {
            "id": "test-deser-2",
            "type": "reasoning",
            "content": {
                "pattern": "complex operation",
                "complexity": "COMPLEX",
                "subgoals": [{"id": "sg1", "description": "Step 1"}],
                "execution_order": [{"sequential": ["sg1"]}],
                "tools_used": ["parser", "editor"],
                "tool_sequence": [{"tool": "parser", "file": "test.py"}],
                "success_score": 0.85,
            },
            "metadata": {
                "created_at": "2025-01-01T12:00:00",
                "last_modified": "2025-01-01T12:30:00",
                "query_id": "q789",
                "duration_ms": 3000,
            },
        }

        chunk = ReasoningChunk.from_json(json_data)

        assert chunk.id == "test-deser-2"
        assert chunk.type == "reasoning"
        assert chunk.pattern == "complex operation"
        assert chunk.complexity == "COMPLEX"
        assert len(chunk.subgoals) == 1
        assert chunk.subgoals[0]["id"] == "sg1"
        assert len(chunk.execution_order) == 1
        assert len(chunk.tools_used) == 2
        assert len(chunk.tool_sequence) == 1
        assert chunk.success_score == 0.85
        assert chunk.metadata["query_id"] == "q789"
        assert chunk.metadata["duration_ms"] == 3000

    def test_from_json_missing_content_raises(self):
        """Test that missing content field raises ValueError."""
        json_data = {"id": "test-missing-content", "type": "reasoning", "metadata": {}}

        with pytest.raises(ValueError, match="Missing required field"):
            ReasoningChunk.from_json(json_data)

    def test_from_json_missing_id_raises(self):
        """Test that missing id field raises ValueError."""
        json_data = {"type": "reasoning", "content": {"pattern": "test"}, "metadata": {}}

        with pytest.raises(ValueError, match="Missing required field"):
            ReasoningChunk.from_json(json_data)

    def test_from_json_missing_optional_content_fields_uses_defaults(self):
        """Test that missing optional content fields use default values."""
        json_data = {
            "id": "test-defaults",
            "type": "reasoning",
            "content": {"pattern": "minimal pattern"},
            "metadata": {},
        }

        chunk = ReasoningChunk.from_json(json_data)

        assert chunk.pattern == "minimal pattern"
        assert chunk.complexity == "SIMPLE"
        assert chunk.subgoals == []
        assert chunk.execution_order == []
        assert chunk.tools_used == []
        assert chunk.tool_sequence == []
        assert chunk.success_score == 0.0

    def test_from_json_excludes_standard_metadata_from_custom(self):
        """Test that created_at and last_modified are not in custom metadata."""
        json_data = {
            "id": "test-metadata-exclusion",
            "type": "reasoning",
            "content": {"pattern": "test pattern"},
            "metadata": {
                "created_at": "2025-01-01T12:00:00",
                "last_modified": "2025-01-01T12:00:00",
                "custom_field": "custom_value",
            },
        }

        chunk = ReasoningChunk.from_json(json_data)

        assert "custom_field" in chunk.metadata
        assert chunk.metadata["custom_field"] == "custom_value"
        assert "created_at" not in chunk.metadata
        assert "last_modified" not in chunk.metadata


class TestReasoningChunkRoundTrip:
    """Test suite for serialization/deserialization round-trips."""

    def test_round_trip_preserves_data(self):
        """Test that serializing then deserializing preserves all data."""
        original = ReasoningChunk(
            chunk_id="test-round-trip",
            pattern="round trip test",
            complexity="MEDIUM",
            subgoals=[{"id": "sg1", "description": "Test subgoal"}],
            execution_order=[{"sequential": ["sg1"]}],
            tools_used=["tool1", "tool2"],
            tool_sequence=[{"tool": "tool1", "action": "parse"}],
            success_score=0.75,
            metadata={"custom": "value"},
        )

        json_data = original.to_json()
        restored = ReasoningChunk.from_json(json_data)

        assert restored.id == original.id
        assert restored.type == original.type
        assert restored.pattern == original.pattern
        assert restored.complexity == original.complexity
        assert restored.subgoals == original.subgoals
        assert restored.execution_order == original.execution_order
        assert restored.tools_used == original.tools_used
        assert restored.tool_sequence == original.tool_sequence
        assert restored.success_score == original.success_score
        assert restored.metadata == original.metadata

    def test_multiple_round_trips_stable(self):
        """Test that multiple round-trips produce stable results."""
        original = ReasoningChunk(
            chunk_id="test-stability",
            pattern="stability test",
            complexity="COMPLEX",
            success_score=0.88,
        )

        # First round-trip
        json1 = original.to_json()
        restored1 = ReasoningChunk.from_json(json1)

        # Second round-trip
        json2 = restored1.to_json()
        restored2 = ReasoningChunk.from_json(json2)

        # Third round-trip
        json3 = restored2.to_json()
        restored3 = ReasoningChunk.from_json(json3)

        assert restored1.pattern == restored2.pattern == restored3.pattern
        assert restored1.complexity == restored2.complexity == restored3.complexity
        assert restored1.success_score == restored2.success_score == restored3.success_score


class TestReasoningChunkRepresentation:
    """Test suite for ReasoningChunk string representation."""

    def test_repr_format(self):
        """Test that __repr__ returns expected format."""
        chunk = ReasoningChunk(
            chunk_id="test-repr",
            pattern="this is a very long pattern that should be truncated in the repr output",
            complexity="MEDIUM",
            subgoals=[{"id": "sg1"}, {"id": "sg2"}],
            tools_used=["tool1", "tool2", "tool3"],
            success_score=0.65,
        )

        repr_str = repr(chunk)

        assert "ReasoningChunk" in repr_str
        assert "id=test-repr" in repr_str
        assert "pattern='this is a very long pattern that should be trunca" in repr_str
        assert "complexity=MEDIUM" in repr_str
        assert "success_score=0.65" in repr_str
        assert "subgoals=2" in repr_str
        assert "tools=3" in repr_str

    def test_repr_short_pattern_not_truncated(self):
        """Test that short patterns are not truncated."""
        chunk = ReasoningChunk(
            chunk_id="test-short-repr", pattern="short", complexity="SIMPLE", success_score=0.5
        )

        repr_str = repr(chunk)

        assert "pattern='short..." in repr_str


class TestReasoningChunkEdgeCases:
    """Test suite for edge cases and special scenarios."""

    def test_empty_lists_allowed(self):
        """Test that empty lists for all list fields are allowed."""
        chunk = ReasoningChunk(
            chunk_id="test-empty-lists",
            pattern="test pattern",
            subgoals=[],
            execution_order=[],
            tools_used=[],
            tool_sequence=[],
        )

        assert chunk.subgoals == []
        assert chunk.execution_order == []
        assert chunk.tools_used == []
        assert chunk.tool_sequence == []

    def test_none_to_empty_list_conversion(self):
        """Test that None values are converted to empty lists."""
        chunk = ReasoningChunk(
            chunk_id="test-none-conversion",
            pattern="test pattern",
            subgoals=None,
            execution_order=None,
            tools_used=None,
            tool_sequence=None,
        )

        assert chunk.subgoals == []
        assert chunk.execution_order == []
        assert chunk.tools_used == []
        assert chunk.tool_sequence == []

    def test_empty_metadata_allowed(self):
        """Test that empty metadata dict is allowed."""
        chunk = ReasoningChunk(chunk_id="test-empty-metadata", pattern="test pattern", metadata={})

        assert chunk.metadata == {}

    def test_none_metadata_converted_to_empty_dict(self):
        """Test that None metadata is converted to empty dict."""
        chunk = ReasoningChunk(chunk_id="test-none-metadata", pattern="test pattern", metadata=None)

        assert chunk.metadata == {}

    def test_complex_nested_structures(self):
        """Test handling of complex nested data structures."""
        chunk = ReasoningChunk(
            chunk_id="test-complex-nested",
            pattern="complex nested test",
            subgoals=[
                {
                    "id": "sg1",
                    "description": "Complex subgoal",
                    "dependencies": ["sg2", "sg3"],
                    "metadata": {"priority": 1, "tags": ["critical", "frontend"]},
                },
                {
                    "id": "sg2",
                    "description": "Another subgoal",
                    "dependencies": [],
                    "metadata": {"priority": 2},
                },
            ],
            execution_order=[
                {"parallel": [{"sequential": ["sg2", "sg3"]}, {"sequential": ["sg4"]}]},
                {"sequential": ["sg1"]},
            ],
        )

        # Verify complex structures are preserved
        assert len(chunk.subgoals) == 2
        assert chunk.subgoals[0]["metadata"]["tags"] == ["critical", "frontend"]
        assert len(chunk.execution_order) == 2

        # Verify round-trip preserves complex structures
        json_data = chunk.to_json()
        restored = ReasoningChunk.from_json(json_data)

        assert restored.subgoals == chunk.subgoals
        assert restored.execution_order == chunk.execution_order

    def test_unicode_in_pattern(self):
        """Test that unicode characters in pattern are handled correctly."""
        chunk = ReasoningChunk(
            chunk_id="test-unicode", pattern="Implement feature with émojis 🚀 and spëcial çhars"
        )

        assert "émojis" in chunk.pattern
        assert "🚀" in chunk.pattern
        assert "spëcial" in chunk.pattern

        # Verify round-trip preserves unicode
        json_data = chunk.to_json()
        restored = ReasoningChunk.from_json(json_data)

        assert restored.pattern == chunk.pattern

    def test_very_long_lists(self):
        """Test handling of very long lists."""
        large_subgoals = [{"id": f"sg{i}", "description": f"Subgoal {i}"} for i in range(100)]
        large_tools = [f"tool{i}" for i in range(50)]

        chunk = ReasoningChunk(
            chunk_id="test-large-lists",
            pattern="large lists test",
            subgoals=large_subgoals,
            tools_used=large_tools,
        )

        assert len(chunk.subgoals) == 100
        assert len(chunk.tools_used) == 50

        # Verify serialization works with large lists
        json_data = chunk.to_json()
        restored = ReasoningChunk.from_json(json_data)

        assert len(restored.subgoals) == 100
        assert len(restored.tools_used) == 50

    def test_float_precision_in_success_score(self):
        """Test that float precision is preserved for success_score."""
        chunk = ReasoningChunk(
            chunk_id="test-float-precision", pattern="test pattern", success_score=0.123456789
        )

        assert chunk.success_score == 0.123456789

        # Verify round-trip preserves precision
        json_data = chunk.to_json()
        restored = ReasoningChunk.from_json(json_data)

        assert restored.success_score == 0.123456789


class TestReasoningChunkComplexityLevels:
    """Test suite for all complexity level scenarios."""

    def test_simple_complexity(self):
        """Test SIMPLE complexity level."""
        chunk = ReasoningChunk(chunk_id="test-simple", pattern="simple query", complexity="SIMPLE")

        assert chunk.complexity == "SIMPLE"

    def test_medium_complexity(self):
        """Test MEDIUM complexity level."""
        chunk = ReasoningChunk(chunk_id="test-medium", pattern="medium query", complexity="MEDIUM")

        assert chunk.complexity == "MEDIUM"

    def test_complex_complexity(self):
        """Test COMPLEX complexity level."""
        chunk = ReasoningChunk(
            chunk_id="test-complex", pattern="complex query", complexity="COMPLEX"
        )

        assert chunk.complexity == "COMPLEX"

    def test_critical_complexity(self):
        """Test CRITICAL complexity level."""
        chunk = ReasoningChunk(
            chunk_id="test-critical", pattern="critical query", complexity="CRITICAL"
        )

        assert chunk.complexity == "CRITICAL"


class TestReasoningChunkSuccessScores:
    """Test suite for success score scenarios."""

    def test_zero_success_score(self):
        """Test success_score of 0.0 (complete failure)."""
        chunk = ReasoningChunk(
            chunk_id="test-score-zero", pattern="failed pattern", success_score=0.0
        )

        assert chunk.success_score == 0.0

    def test_partial_success_score(self):
        """Test success_score between 0.0 and 1.0."""
        chunk = ReasoningChunk(
            chunk_id="test-score-partial", pattern="partial success", success_score=0.5
        )

        assert chunk.success_score == 0.5

    def test_high_success_score(self):
        """Test success_score close to 1.0."""
        chunk = ReasoningChunk(
            chunk_id="test-score-high", pattern="high success", success_score=0.95
        )

        assert chunk.success_score == 0.95

    def test_perfect_success_score(self):
        """Test success_score of 1.0 (perfect success)."""
        chunk = ReasoningChunk(
            chunk_id="test-score-perfect", pattern="perfect pattern", success_score=1.0
        )

        assert chunk.success_score == 1.0
