"""
Unit tests for CodeChunk implementation.

Tests serialization, validation, and edge cases for code chunks.
"""

from datetime import datetime
from pathlib import Path

import pytest
from aurora_core.chunks.code_chunk import CodeChunk


class TestCodeChunkBasic:
    """Basic functionality tests for CodeChunk."""

    def test_code_chunk_initialization(self):
        """Test that CodeChunk initializes correctly."""
        chunk = CodeChunk(
            chunk_id="code:test.py:func",
            file_path="/absolute/path/test.py",
            element_type="function",
            name="test_func",
            line_start=10,
            line_end=20,
        )

        assert chunk.id == "code:test.py:func"
        assert chunk.type == "code"
        assert chunk.file_path == "/absolute/path/test.py"
        assert chunk.element_type == "function"
        assert chunk.name == "test_func"
        assert chunk.line_start == 10
        assert chunk.line_end == 20
        assert chunk.signature is None
        assert chunk.docstring is None
        assert chunk.dependencies == []
        assert chunk.complexity_score == 0.0
        assert chunk.language == "python"

    def test_code_chunk_with_optional_fields(self):
        """Test CodeChunk with all optional fields."""
        chunk = CodeChunk(
            chunk_id="code:test.py:func",
            file_path="/absolute/path/test.py",
            element_type="function",
            name="test_func",
            line_start=10,
            line_end=20,
            signature="def test_func(x: int) -> str",
            docstring="Test function docstring",
            dependencies=["code:other.py:helper"],
            complexity_score=0.75,
            language="python",
        )

        assert chunk.signature == "def test_func(x: int) -> str"
        assert chunk.docstring == "Test function docstring"
        assert chunk.dependencies == ["code:other.py:helper"]
        assert chunk.complexity_score == 0.75
        assert chunk.language == "python"

    def test_code_chunk_repr(self):
        """Test string representation."""
        chunk = CodeChunk(
            chunk_id="code:test.py:func",
            file_path="/absolute/path/test.py",
            element_type="function",
            name="test_func",
            line_start=10,
            line_end=20,
        )

        repr_str = repr(chunk)
        assert "CodeChunk" in repr_str
        assert "code:test.py:func" in repr_str
        assert "/absolute/path/test.py" in repr_str
        assert "function" in repr_str
        assert "test_func" in repr_str
        assert "10-20" in repr_str


class TestCodeChunkValidation:
    """Test validation rules for CodeChunk."""

    def test_line_start_must_be_positive(self):
        """Test that line_start must be > 0."""
        with pytest.raises(ValueError, match="line_start must be > 0"):
            CodeChunk(
                chunk_id="code:test.py:func",
                file_path="/absolute/path/test.py",
                element_type="function",
                name="test_func",
                line_start=0,
                line_end=10,
            )

    def test_line_start_cannot_be_negative(self):
        """Test that line_start cannot be negative."""
        with pytest.raises(ValueError, match="line_start must be > 0"):
            CodeChunk(
                chunk_id="code:test.py:func",
                file_path="/absolute/path/test.py",
                element_type="function",
                name="test_func",
                line_start=-5,
                line_end=10,
            )

    def test_line_end_must_be_greater_or_equal_to_start(self):
        """Test that line_end >= line_start."""
        with pytest.raises(ValueError, match="line_end.*must be >= line_start"):
            CodeChunk(
                chunk_id="code:test.py:func",
                file_path="/absolute/path/test.py",
                element_type="function",
                name="test_func",
                line_start=20,
                line_end=10,
            )

    def test_line_end_can_equal_line_start(self):
        """Test that single-line chunks are valid."""
        chunk = CodeChunk(
            chunk_id="code:test.py:func",
            file_path="/absolute/path/test.py",
            element_type="function",
            name="test_func",
            line_start=10,
            line_end=10,
        )
        assert chunk.line_start == chunk.line_end

    def test_file_path_must_be_absolute(self):
        """Test that file_path must be absolute."""
        with pytest.raises(ValueError, match="file_path must be absolute"):
            CodeChunk(
                chunk_id="code:test.py:func",
                file_path="relative/path/test.py",
                element_type="function",
                name="test_func",
                line_start=10,
                line_end=20,
            )

    def test_complexity_score_must_be_in_range(self):
        """Test that complexity_score must be [0.0, 1.0]."""
        # Below range
        with pytest.raises(ValueError, match="complexity_score must be in"):
            CodeChunk(
                chunk_id="code:test.py:func",
                file_path="/absolute/path/test.py",
                element_type="function",
                name="test_func",
                line_start=10,
                line_end=20,
                complexity_score=-0.1,
            )

        # Above range
        with pytest.raises(ValueError, match="complexity_score must be in"):
            CodeChunk(
                chunk_id="code:test.py:func",
                file_path="/absolute/path/test.py",
                element_type="function",
                name="test_func",
                line_start=10,
                line_end=20,
                complexity_score=1.5,
            )

    def test_complexity_score_boundary_values(self):
        """Test that boundary values 0.0 and 1.0 are valid."""
        # Min value
        chunk1 = CodeChunk(
            chunk_id="code:test.py:func1",
            file_path="/absolute/path/test.py",
            element_type="function",
            name="test_func1",
            line_start=10,
            line_end=20,
            complexity_score=0.0,
        )
        assert chunk1.complexity_score == 0.0

        # Max value
        chunk2 = CodeChunk(
            chunk_id="code:test.py:func2",
            file_path="/absolute/path/test.py",
            element_type="function",
            name="test_func2",
            line_start=10,
            line_end=20,
            complexity_score=1.0,
        )
        assert chunk2.complexity_score == 1.0

    def test_element_type_must_be_valid(self):
        """Test that element_type must be one of: function, class, method."""
        with pytest.raises(ValueError, match="element_type must be one of"):
            CodeChunk(
                chunk_id="code:test.py:invalid",
                file_path="/absolute/path/test.py",
                element_type="invalid_type",
                name="test_func",
                line_start=10,
                line_end=20,
            )

    def test_valid_element_types(self):
        """Test all valid element types."""
        for elem_type in ["function", "class", "method"]:
            chunk = CodeChunk(
                chunk_id=f"code:test.py:{elem_type}",
                file_path="/absolute/path/test.py",
                element_type=elem_type,
                name=f"test_{elem_type}",
                line_start=10,
                line_end=20,
            )
            assert chunk.element_type == elem_type

    def test_name_cannot_be_empty(self):
        """Test that name must not be empty."""
        with pytest.raises(ValueError, match="name must not be empty"):
            CodeChunk(
                chunk_id="code:test.py:func",
                file_path="/absolute/path/test.py",
                element_type="function",
                name="",
                line_start=10,
                line_end=20,
            )

    def test_name_cannot_be_whitespace(self):
        """Test that name cannot be only whitespace."""
        with pytest.raises(ValueError, match="name must not be empty"):
            CodeChunk(
                chunk_id="code:test.py:func",
                file_path="/absolute/path/test.py",
                element_type="function",
                name="   ",
                line_start=10,
                line_end=20,
            )

    def test_language_cannot_be_empty(self):
        """Test that language must not be empty."""
        with pytest.raises(ValueError, match="language must not be empty"):
            CodeChunk(
                chunk_id="code:test.py:func",
                file_path="/absolute/path/test.py",
                element_type="function",
                name="test_func",
                line_start=10,
                line_end=20,
                language="",
            )


class TestCodeChunkSerialization:
    """Test JSON serialization for CodeChunk."""

    def test_to_json_basic(self):
        """Test basic to_json() serialization."""
        chunk = CodeChunk(
            chunk_id="code:test.py:func",
            file_path="/absolute/path/test.py",
            element_type="function",
            name="test_func",
            line_start=10,
            line_end=20,
        )

        data = chunk.to_json()

        assert data["id"] == "code:test.py:func"
        assert data["type"] == "code"
        assert data["content"]["file"] == "/absolute/path/test.py"
        assert data["content"]["function"] == "test_func"
        assert data["content"]["line_start"] == 10
        assert data["content"]["line_end"] == 20
        assert data["content"]["signature"] is None
        assert data["content"]["docstring"] is None
        assert data["content"]["dependencies"] == []
        assert data["content"]["ast_summary"]["complexity"] == 0.0
        assert data["content"]["ast_summary"]["element_type"] == "function"
        assert data["metadata"]["language"] == "python"

    def test_to_json_with_all_fields(self):
        """Test to_json() with all optional fields."""
        chunk = CodeChunk(
            chunk_id="code:test.py:func",
            file_path="/absolute/path/test.py",
            element_type="method",
            name="test_method",
            line_start=10,
            line_end=20,
            signature="def test_method(self, x: int) -> str",
            docstring="Test method docstring",
            dependencies=["code:other.py:helper", "code:util.py:process"],
            complexity_score=0.65,
            language="python",
        )

        data = chunk.to_json()

        assert data["content"]["signature"] == "def test_method(self, x: int) -> str"
        assert data["content"]["docstring"] == "Test method docstring"
        assert len(data["content"]["dependencies"]) == 2
        assert data["content"]["ast_summary"]["complexity"] == 0.65
        assert data["content"]["ast_summary"]["element_type"] == "method"

    def test_to_json_includes_timestamps(self):
        """Test that to_json() includes timestamps."""
        chunk = CodeChunk(
            chunk_id="code:test.py:func",
            file_path="/absolute/path/test.py",
            element_type="function",
            name="test_func",
            line_start=10,
            line_end=20,
        )

        data = chunk.to_json()

        assert "created_at" in data["metadata"]
        assert "last_modified" in data["metadata"]

        # Timestamps should be ISO format strings
        created_at = datetime.fromisoformat(data["metadata"]["created_at"])
        modified_at = datetime.fromisoformat(data["metadata"]["last_modified"])
        assert isinstance(created_at, datetime)
        assert isinstance(modified_at, datetime)

    def test_from_json_basic(self):
        """Test basic from_json() deserialization."""
        data = {
            "id": "code:test.py:func",
            "type": "code",
            "content": {
                "file": "/absolute/path/test.py",
                "function": "test_func",
                "line_start": 10,
                "line_end": 20,
                "ast_summary": {"complexity": 0.5, "element_type": "function"},
            },
            "metadata": {"language": "python"},
        }

        chunk = CodeChunk.from_json(data)

        assert chunk.id == "code:test.py:func"
        assert chunk.type == "code"
        assert chunk.file_path == "/absolute/path/test.py"
        assert chunk.name == "test_func"
        assert chunk.line_start == 10
        assert chunk.line_end == 20
        assert chunk.complexity_score == 0.5
        assert chunk.element_type == "function"
        assert chunk.language == "python"

    def test_from_json_with_optional_fields(self):
        """Test from_json() with optional fields."""
        data = {
            "id": "code:test.py:func",
            "type": "code",
            "content": {
                "file": "/absolute/path/test.py",
                "function": "test_func",
                "line_start": 10,
                "line_end": 20,
                "signature": "def test_func() -> None",
                "docstring": "Test docstring",
                "dependencies": ["code:other.py:helper"],
                "ast_summary": {"complexity": 0.8, "element_type": "function"},
            },
            "metadata": {
                "language": "python",
                "created_at": "2025-01-01T00:00:00",
                "last_modified": "2025-01-02T00:00:00",
            },
        }

        chunk = CodeChunk.from_json(data)

        assert chunk.signature == "def test_func() -> None"
        assert chunk.docstring == "Test docstring"
        assert chunk.dependencies == ["code:other.py:helper"]
        assert chunk.created_at == datetime(2025, 1, 1)
        assert chunk.updated_at == datetime(2025, 1, 2)

    def test_from_json_missing_required_field(self):
        """Test that from_json() raises on missing required field."""
        data = {
            "id": "code:test.py:func",
            "type": "code",
            "content": {
                "file": "/absolute/path/test.py",
                # Missing "function" field
                "line_start": 10,
                "line_end": 20,
            },
        }

        with pytest.raises(ValueError, match="Missing required field"):
            CodeChunk.from_json(data)

    def test_from_json_with_defaults(self):
        """Test that from_json() uses defaults for missing optional fields."""
        data = {
            "id": "code:test.py:func",
            "type": "code",
            "content": {
                "file": "/absolute/path/test.py",
                "function": "test_func",
                "line_start": 10,
                "line_end": 20,
                # No ast_summary, dependencies, etc.
            },
        }

        chunk = CodeChunk.from_json(data)

        assert chunk.complexity_score == 0.0
        assert chunk.element_type == "function"
        assert chunk.dependencies == []
        assert chunk.language == "python"

    def test_serialization_round_trip(self):
        """Test that serialization round-trip preserves data."""
        original = CodeChunk(
            chunk_id="code:test.py:complex_func",
            file_path="/absolute/path/test.py",
            element_type="function",
            name="complex_func",
            line_start=100,
            line_end=200,
            signature="def complex_func(a: int, b: str = 'default') -> Dict[str, Any]",
            docstring="Complex function with multiple branches",
            dependencies=["code:util.py:helper1", "code:util.py:helper2"],
            complexity_score=0.85,
            language="python",
        )

        # Serialize
        data = original.to_json()

        # Deserialize
        restored = CodeChunk.from_json(data)

        # Verify all fields match
        assert restored.id == original.id
        assert restored.type == original.type
        assert restored.file_path == original.file_path
        assert restored.element_type == original.element_type
        assert restored.name == original.name
        assert restored.line_start == original.line_start
        assert restored.line_end == original.line_end
        assert restored.signature == original.signature
        assert restored.docstring == original.docstring
        assert restored.dependencies == original.dependencies
        assert restored.complexity_score == original.complexity_score
        assert restored.language == original.language


class TestCodeChunkEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_large_line_numbers(self):
        """Test with very large line numbers."""
        chunk = CodeChunk(
            chunk_id="code:huge.py:func",
            file_path="/absolute/path/huge.py",
            element_type="function",
            name="huge_func",
            line_start=1_000_000,
            line_end=1_000_100,
        )
        assert chunk.line_start == 1_000_000
        assert chunk.line_end == 1_000_100

    def test_very_long_file_path(self):
        """Test with very long file path."""
        long_path = "/absolute/" + "a" * 1000 + "/test.py"
        chunk = CodeChunk(
            chunk_id="code:test.py:func",
            file_path=long_path,
            element_type="function",
            name="test_func",
            line_start=10,
            line_end=20,
        )
        assert chunk.file_path == long_path

    def test_very_long_name(self):
        """Test with very long function name."""
        long_name = "func_" + "x" * 1000
        chunk = CodeChunk(
            chunk_id="code:test.py:func",
            file_path="/absolute/path/test.py",
            element_type="function",
            name=long_name,
            line_start=10,
            line_end=20,
        )
        assert chunk.name == long_name

    def test_many_dependencies(self):
        """Test with many dependencies."""
        deps = [f"code:dep{i}.py:func" for i in range(100)]
        chunk = CodeChunk(
            chunk_id="code:test.py:func",
            file_path="/absolute/path/test.py",
            element_type="function",
            name="test_func",
            line_start=10,
            line_end=20,
            dependencies=deps,
        )
        assert len(chunk.dependencies) == 100

    def test_unicode_in_name(self):
        """Test with unicode characters in name."""
        chunk = CodeChunk(
            chunk_id="code:test.py:func",
            file_path="/absolute/path/test.py",
            element_type="function",
            name="test_函数_función",
            line_start=10,
            line_end=20,
        )
        assert "函数" in chunk.name
        assert "función" in chunk.name

    def test_multiline_docstring(self):
        """Test with multiline docstring."""
        docstring = """
        This is a multiline docstring.

        It has multiple paragraphs.

        Args:
            x: Parameter description

        Returns:
            Something useful
        """
        chunk = CodeChunk(
            chunk_id="code:test.py:func",
            file_path="/absolute/path/test.py",
            element_type="function",
            name="test_func",
            line_start=10,
            line_end=20,
            docstring=docstring,
        )
        assert "multiline" in chunk.docstring
        assert "Args:" in chunk.docstring

    def test_special_characters_in_signature(self):
        """Test with special characters in signature."""
        signature = "def test(x: List[Tuple[int, str]], y: Dict[str, Any] = {}) -> Optional[str]"
        chunk = CodeChunk(
            chunk_id="code:test.py:func",
            file_path="/absolute/path/test.py",
            element_type="function",
            name="test",
            line_start=10,
            line_end=20,
            signature=signature,
        )
        assert chunk.signature == signature

    def test_absolute_path_variations(self):
        """Test various absolute path formats."""
        paths = [
            "/absolute/path/test.py",
            "/home/user/project/test.py",
            "/usr/local/lib/python/test.py",
        ]

        for path in paths:
            chunk = CodeChunk(
                chunk_id=f"code:{Path(path).name}:func",
                file_path=path,
                element_type="function",
                name="test_func",
                line_start=10,
                line_end=20,
            )
            assert chunk.file_path == path
