"""Unit tests for Reasoning Chunk embeddings and search.

Tests:
- UT-REAS-01: Generate embeddings test
- UT-REAS-02: Store embeddings test
- UT-REAS-03: Retrieve by pattern test

Note: Reasoning chunks are created by the SOAR pipeline, not by file parsing.
These tests verify that reasoning chunks CAN be embedded and searched once created.
"""

import pytest

from aurora_core.chunks.reasoning_chunk import ReasoningChunk


def test_reasoning_chunk_creation():
    """UT-REAS-01: Verify reasoning chunks can be created with content for embedding."""
    chunk = ReasoningChunk(
        chunk_id="reas_001",
        pattern="implement feature X with testing",
        complexity="MEDIUM",
        subgoals=[
            {"id": "sg1", "description": "Write unit tests first"},
            {"id": "sg2", "description": "Implement feature logic"},
        ],
        tools_used=["Write", "Bash", "Edit"],
        success_score=0.9,
        metadata={"agent": "code-developer", "duration_seconds": 120},
    )

    assert chunk.id == "reas_001"
    assert chunk.type == "reasoning"
    assert chunk.pattern == "implement feature X with testing"
    assert chunk.complexity == "MEDIUM"
    assert len(chunk.subgoals) == 2
    assert chunk.success_score == 0.9


def test_reasoning_chunk_serialization():
    """UT-REAS-02: Verify reasoning chunks can be serialized (for storage with embeddings)."""
    chunk = ReasoningChunk(
        chunk_id="reas_002",
        pattern="debug authentication failure",
        complexity="COMPLEX",
        subgoals=[{"id": "sg1", "description": "Investigate logs"}],
        tools_used=["Grep", "Read"],
        success_score=0.95,
    )

    # Serialize to JSON
    json_data = chunk.to_json()

    assert json_data["id"] == "reas_002"
    assert json_data["type"] == "reasoning"
    assert json_data["content"]["pattern"] == "debug authentication failure"
    assert json_data["content"]["complexity"] == "COMPLEX"
    assert json_data["content"]["success_score"] == 0.95

    # Deserialize from JSON
    restored = ReasoningChunk.from_json(json_data)

    assert restored.id == chunk.id
    assert restored.pattern == chunk.pattern
    assert restored.complexity == chunk.complexity
    assert restored.success_score == chunk.success_score


def test_reasoning_chunk_searchable_content():
    """UT-REAS-03: Verify reasoning chunks have searchable content for embeddings."""
    chunk = ReasoningChunk(
        chunk_id="reas_003",
        pattern="refactor codebase for better maintainability",
        complexity="CRITICAL",
        subgoals=[
            {"id": "sg1", "description": "Identify duplicated code"},
            {"id": "sg2", "description": "Extract common patterns into utilities"},
            {"id": "sg3", "description": "Update tests to match new structure"},
        ],
        tools_used=["Grep", "Edit", "Bash"],
        success_score=0.85,
        metadata={"tags": ["refactoring", "technical-debt"]},
    )

    # For embedding generation, we typically combine pattern + subgoals
    searchable_text = chunk.pattern
    for subgoal in chunk.subgoals:
        searchable_text += " " + subgoal.get("description", "")

    assert "refactor codebase" in searchable_text
    assert "duplicated code" in searchable_text
    assert "Extract common patterns" in searchable_text
    assert len(searchable_text) > 50  # Should have substantial content

    # Metadata should be accessible
    assert "refactoring" in chunk.metadata.get("tags", [])


def test_reasoning_chunk_validation():
    """Test that reasoning chunks validate their structure."""
    # Valid chunk
    valid = ReasoningChunk(
        chunk_id="reas_004",
        pattern="test pattern",
        complexity="SIMPLE",
        success_score=0.8,
    )
    assert valid.validate()

    # Test complexity validation
    with pytest.raises(ValueError, match="complexity must be one of"):
        ReasoningChunk(
            chunk_id="reas_005",
            pattern="test",
            complexity="INVALID",
        )

    # Test success_score range
    with pytest.raises(ValueError, match="success_score must be in"):
        ReasoningChunk(
            chunk_id="reas_006",
            pattern="test",
            success_score=1.5,  # Out of range
        )
