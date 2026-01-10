"""
Unit tests for the abstract Chunk base class.

Tests the Chunk interface contract that all concrete chunk types must implement.
"""

from datetime import datetime
from typing import Any

import pytest

from aurora_core.chunks.base import Chunk


class ConcreteChunk(Chunk):
    """Test implementation of abstract Chunk for testing."""

    def __init__(self, chunk_id: str, chunk_type: str, data: str = "test"):
        super().__init__(chunk_id, chunk_type)
        self.data = data

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "data": self.data,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "ConcreteChunk":
        chunk = cls(data["id"], data["type"], data.get("data", "test"))
        if "created_at" in data:
            chunk.created_at = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data:
            chunk.updated_at = datetime.fromisoformat(data["updated_at"])
        return chunk

    def validate(self) -> bool:
        if not self.id:
            raise ValueError("ID cannot be empty")
        if not self.type:
            raise ValueError("Type cannot be empty")
        return True


class TestChunkInterface:
    """Test suite for Chunk interface contract."""

    def test_chunk_initialization(self):
        """Test that chunk initializes with correct attributes."""
        chunk = ConcreteChunk("test-id", "test-type")

        assert chunk.id == "test-id"
        assert chunk.type == "test-type"
        assert isinstance(chunk.created_at, datetime)
        assert isinstance(chunk.updated_at, datetime)

    def test_chunk_timestamps_are_utc(self):
        """Test that timestamps are in UTC."""
        chunk = ConcreteChunk("test-id", "test-type")

        # Timestamps should be close to current UTC time
        from datetime import timezone

        now = datetime.now(timezone.utc)
        assert abs((chunk.created_at - now).total_seconds()) < 1
        assert abs((chunk.updated_at - now).total_seconds()) < 1

    def test_chunk_to_json_must_be_implemented(self):
        """Test that to_json() must be implemented by subclasses."""
        chunk = ConcreteChunk("test-id", "test-type", "test-data")
        result = chunk.to_json()

        assert isinstance(result, dict)
        assert result["id"] == "test-id"
        assert result["type"] == "test-type"
        assert result["data"] == "test-data"

    def test_chunk_from_json_must_be_implemented(self):
        """Test that from_json() must be implemented by subclasses."""
        data = {"id": "test-id", "type": "test-type", "data": "test-data"}
        chunk = ConcreteChunk.from_json(data)

        assert isinstance(chunk, ConcreteChunk)
        assert chunk.id == "test-id"
        assert chunk.type == "test-type"
        assert chunk.data == "test-data"

    def test_chunk_validate_must_be_implemented(self):
        """Test that validate() must be implemented by subclasses."""
        chunk = ConcreteChunk("test-id", "test-type")

        # Should return True for valid chunk
        assert chunk.validate() is True

    def test_chunk_validate_raises_on_invalid(self):
        """Test that validate() raises ValueError on invalid data."""
        chunk = ConcreteChunk("", "test-type")

        with pytest.raises(ValueError, match="ID cannot be empty"):
            chunk.validate()

    def test_chunk_repr(self):
        """Test string representation of chunk."""
        chunk = ConcreteChunk("test-id", "test-type")
        repr_str = repr(chunk)

        assert "ConcreteChunk" in repr_str
        assert "test-id" in repr_str
        assert "test-type" in repr_str

    def test_chunk_equality(self):
        """Test that chunks are equal if they have the same ID."""
        chunk1 = ConcreteChunk("test-id", "test-type", "data1")
        chunk2 = ConcreteChunk("test-id", "test-type", "data2")
        chunk3 = ConcreteChunk("other-id", "test-type", "data1")

        assert chunk1 == chunk2  # Same ID
        assert chunk1 != chunk3  # Different ID

    def test_chunk_equality_with_non_chunk(self):
        """Test that chunks are not equal to non-Chunk objects."""
        chunk = ConcreteChunk("test-id", "test-type")

        assert chunk != "test-id"
        assert chunk != 123
        assert chunk is not None
        assert chunk != {"id": "test-id"}

    def test_chunk_hash(self):
        """Test that chunks can be hashed based on ID."""
        chunk1 = ConcreteChunk("test-id", "test-type", "data1")
        chunk2 = ConcreteChunk("test-id", "test-type", "data2")
        chunk3 = ConcreteChunk("other-id", "test-type", "data1")

        # Same ID should have same hash
        assert hash(chunk1) == hash(chunk2)
        # Different ID should (likely) have different hash
        assert hash(chunk1) != hash(chunk3)

    def test_chunk_usable_in_set(self):
        """Test that chunks can be used in sets."""
        chunk1 = ConcreteChunk("id-1", "test-type")
        chunk2 = ConcreteChunk("id-2", "test-type")
        chunk3 = ConcreteChunk("id-1", "test-type")  # Duplicate ID

        chunk_set = {chunk1, chunk2, chunk3}

        # Should only have 2 items (chunk3 is duplicate of chunk1)
        assert len(chunk_set) == 2
        assert chunk1 in chunk_set
        assert chunk2 in chunk_set

    def test_chunk_usable_as_dict_key(self):
        """Test that chunks can be used as dictionary keys."""
        chunk1 = ConcreteChunk("id-1", "test-type")
        chunk2 = ConcreteChunk("id-2", "test-type")

        chunk_dict = {chunk1: "value1", chunk2: "value2"}

        assert chunk_dict[chunk1] == "value1"
        assert chunk_dict[chunk2] == "value2"

    def test_chunk_serialization_round_trip(self):
        """Test that chunk can be serialized and deserialized."""
        original = ConcreteChunk("test-id", "test-type", "test-data")

        # Serialize
        json_data = original.to_json()

        # Deserialize
        restored = ConcreteChunk.from_json(json_data)

        # Verify
        assert restored.id == original.id
        assert restored.type == original.type
        assert restored.data == original.data


class TestChunkAbstractMethods:
    """Test that abstract methods cannot be called directly."""

    def test_cannot_instantiate_abstract_chunk(self):
        """Test that Chunk cannot be instantiated directly."""
        with pytest.raises(TypeError):
            # This should fail because Chunk has abstract methods
            Chunk("test-id", "test-type")  # type: ignore


class InvalidChunk(Chunk):
    """Chunk implementation missing required methods."""

    def to_json(self) -> dict[str, Any]:
        return {}

    # Missing from_json and validate implementations


class TestChunkInheritance:
    """Test chunk inheritance requirements."""
