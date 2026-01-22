"""Unit tests for aurora_get MCP tool (PRD-0008).

This module tests the NEW aurora_get tool that retrieves full chunks by index
from the last search results (stored in session cache). These tests are written
FIRST (TDD RED phase) before implementing the aurora_get functionality.

Test Coverage:
- Basic functionality (get by valid index, first item, last item)
- Error handling (invalid indices, no previous search)
- Session cache (storage, clearing, expiry)
- Response format (full chunk, index metadata)

Expected State: ALL TESTS SHOULD FAIL initially (TDD RED phase).
After implementation: ALL TESTS SHOULD PASS (TDD GREEN phase).

Related PRD: /home/hamr/PycharmProjects/aurora/tasks/0008-prd-mcp-aurora-query-simplification.md
"""

import json
import time
from unittest.mock import MagicMock, patch  # noqa: F401

import pytest

from aurora_mcp.tools import AuroraMCPTools


# Skip all tests in this file - MCP functionality is dormant (PRD-0024)
pytestmark = pytest.mark.skip(reason="MCP functionality dormant - tests deprecated (PRD-0024)")


# ==============================================================================
# Task 3.2: Basic Functionality Tests
# ==============================================================================


class TestBasicFunctionality:
    """Test basic aurora_get functionality with valid indices."""

    def test_get_valid_index_returns_chunk(self):
        """Getting a valid index should return the corresponding chunk."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Simulate previous search results
        mock_results = [
            {
                "chunk_id": "code:test1.py:func1",
                "content": "def func1(): pass",
                "file_path": "test1.py",
                "function_name": "func1",
                "score": 0.9,
                "line_range": [1, 1],
            },
            {
                "chunk_id": "code:test2.py:func2",
                "content": "def func2(): pass",
                "file_path": "test2.py",
                "function_name": "func2",
                "score": 0.8,
                "line_range": [5, 5],
            },
        ]

        # Set up cache (this should be done by aurora_search/aurora_query in production)
        tools._last_search_results = mock_results
        tools._last_search_timestamp = time.time()

        # Get the second result (1-indexed)
        result = tools.aurora_get(2)
        response = json.loads(result)

        # Should return the second chunk
        assert "chunk" in response
        chunk = response["chunk"]
        assert chunk["chunk_id"] == "code:test2.py:func2"
        assert chunk["content"] == "def func2(): pass"
        assert chunk["file_path"] == "test2.py"

    def test_get_first_item_index_1(self):
        """Index 1 should return the first item (1-indexed, not 0-indexed)."""
        tools = AuroraMCPTools(db_path=":memory:")

        mock_results = [
            {
                "chunk_id": "code:first.py:first_func",
                "content": "def first_func(): pass",
                "file_path": "first.py",
                "function_name": "first_func",
                "score": 0.95,
                "line_range": [1, 1],
            },
            {
                "chunk_id": "code:second.py:second_func",
                "content": "def second_func(): pass",
                "file_path": "second.py",
                "function_name": "second_func",
                "score": 0.85,
                "line_range": [1, 1],
            },
        ]

        tools._last_search_results = mock_results
        tools._last_search_timestamp = time.time()

        # Get first result (1-indexed)
        result = tools.aurora_get(1)
        response = json.loads(result)

        # Should return the FIRST chunk
        assert response["chunk"]["chunk_id"] == "code:first.py:first_func"
        assert response["chunk"]["content"] == "def first_func(): pass"

    def test_get_last_item(self):
        """Should be able to get the last item in search results."""
        tools = AuroraMCPTools(db_path=":memory:")

        mock_results = [
            {
                "chunk_id": f"code:test{i}.py:func{i}",
                "content": f"content {i}",
                "file_path": f"test{i}.py",
                "function_name": f"func{i}",
                "score": 0.9 - (i * 0.1),
                "line_range": [1, 1],
            }
            for i in range(5)
        ]

        tools._last_search_results = mock_results
        tools._last_search_timestamp = time.time()

        # Get last result (index 5 for 5 items)
        result = tools.aurora_get(5)
        response = json.loads(result)

        # Should return the last chunk
        assert response["chunk"]["chunk_id"] == "code:test4.py:func4"
        assert response["chunk"]["content"] == "content 4"


# ==============================================================================
# Task 3.3: Error Handling Tests
# ==============================================================================


class TestErrorHandling:
    """Test error handling for invalid inputs."""

    def test_get_index_zero_returns_error(self):
        """Index 0 should return an error (1-indexed system)."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Set up cache
        mock_results = [
            {
                "chunk_id": "code:test.py:func",
                "content": "content",
                "file_path": "test.py",
                "function_name": "func",
                "score": 0.9,
                "line_range": [1, 1],
            },
        ]
        tools._last_search_results = mock_results
        tools._last_search_timestamp = time.time()

        result = tools.aurora_get(0)
        response = json.loads(result)

        # Should be an error
        assert "error" in response
        assert response["error"]["type"] == "InvalidParameter"
        assert "index" in response["error"]["message"].lower()
        assert (
            "must be >= 1" in response["error"]["message"]
            or "1-indexed" in response["error"]["message"]
        )

    def test_get_negative_index_returns_error(self):
        """Negative index should return an error."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Set up cache
        mock_results = [
            {
                "chunk_id": "code:test.py:func",
                "content": "content",
                "file_path": "test.py",
                "function_name": "func",
                "score": 0.9,
                "line_range": [1, 1],
            },
        ]
        tools._last_search_results = mock_results
        tools._last_search_timestamp = time.time()

        result = tools.aurora_get(-1)
        response = json.loads(result)

        # Should be an error
        assert "error" in response
        assert response["error"]["type"] == "InvalidParameter"
        assert "index" in response["error"]["message"].lower()

    def test_get_index_out_of_range_returns_error(self):
        """Index beyond the number of results should return an error."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Set up cache with only 3 results
        mock_results = [
            {
                "chunk_id": f"code:test{i}.py:func{i}",
                "content": f"content {i}",
                "file_path": f"test{i}.py",
                "function_name": f"func{i}",
                "score": 0.9 - (i * 0.1),
                "line_range": [1, 1],
            }
            for i in range(3)
        ]
        tools._last_search_results = mock_results
        tools._last_search_timestamp = time.time()

        # Try to get index 4 (only 3 results available)
        result = tools.aurora_get(4)
        response = json.loads(result)

        # Should be an error
        assert "error" in response
        assert response["error"]["type"] == "InvalidParameter"
        assert (
            "out of range" in response["error"]["message"].lower()
            or "only 3" in response["error"]["message"]
        )
        # Should suggest valid range
        assert "1" in response["error"]["message"]
        assert "3" in response["error"]["message"]

    def test_get_no_previous_search_returns_error(self):
        """Calling aurora_get without previous search should return error."""
        tools = AuroraMCPTools(db_path=":memory:")

        # No previous search (cache not initialized)
        result = tools.aurora_get(1)
        response = json.loads(result)

        # Should be an error
        assert "error" in response
        assert response["error"]["type"] == "NoSearchResults"
        assert (
            "no previous search" in response["error"]["message"].lower()
            or "search first" in response["error"]["message"].lower()
        )
        # Should suggest running aurora_search or aurora_query first
        assert (
            "aurora_search" in response["error"]["suggestion"]
            or "aurora_query" in response["error"]["suggestion"]
        )


# ==============================================================================
# Task 3.4: Session Cache Tests
# ==============================================================================


class TestSessionCache:
    """Test session cache storage and management."""

    @pytest.mark.ml
    def test_cache_stores_last_search_results(self):
        """aurora_search should store results in session cache."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Mock the retriever to return some results
        mock_search_results = [
            {
                "chunk_id": "code:test.py:func",
                "content": "def func(): pass",
                "metadata": {"file_path": "test.py", "name": "func", "line_range": [1, 1]},
                "hybrid_score": 0.9,
            },
        ]

        with patch.object(tools, "_retriever") as mock_retriever:
            mock_retriever.retrieve.return_value = mock_search_results

            # Run aurora_search
            tools._ensure_initialized()
            tools.aurora_search("test query")

            # Cache should be populated
            assert hasattr(tools, "_last_search_results")
            assert tools._last_search_results is not None
            assert len(tools._last_search_results) > 0
            assert hasattr(tools, "_last_search_timestamp")
            assert tools._last_search_timestamp is not None

    @pytest.mark.ml
    def test_new_search_clears_previous_cache(self):
        """New search should replace previous cache, not append."""
        tools = AuroraMCPTools(db_path=":memory:")

        # First search
        first_results = [
            {
                "chunk_id": "code:first.py:func1",
                "content": "first content",
                "metadata": {"file_path": "first.py", "name": "func1", "line_range": [1, 1]},
                "hybrid_score": 0.9,
            },
        ]

        # Second search (different results)
        second_results = [
            {
                "chunk_id": "code:second.py:func2",
                "content": "second content",
                "metadata": {"file_path": "second.py", "name": "func2", "line_range": [1, 1]},
                "hybrid_score": 0.85,
            },
        ]

        with patch.object(tools, "_retriever") as mock_retriever:
            tools._ensure_initialized()

            # First search
            mock_retriever.retrieve.return_value = first_results
            tools.aurora_search("first query")
            first_cache = tools._last_search_results.copy()

            # Second search
            mock_retriever.retrieve.return_value = second_results
            tools.aurora_search("second query")
            second_cache = tools._last_search_results

            # Cache should be replaced, not appended
            assert len(second_cache) == 1  # Only second results
            assert second_cache[0]["chunk_id"] == "code:second.py:func2"
            # Should NOT contain first results
            second_chunk_ids = [r["chunk_id"] for r in second_cache]
            assert "code:first.py:func1" not in second_chunk_ids
            # Verify first cache was valid before replacement
            assert len(first_cache) == 1

    def test_cache_expires_after_timeout(self):
        """Cache should expire after 10 minutes (600 seconds)."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Set up cache with old timestamp (11 minutes ago)
        mock_results = [
            {
                "chunk_id": "code:old.py:func",
                "content": "old content",
                "file_path": "old.py",
                "function_name": "func",
                "score": 0.9,
                "line_range": [1, 1],
            },
        ]
        tools._last_search_results = mock_results
        tools._last_search_timestamp = time.time() - (11 * 60)  # 11 minutes ago

        # Try to get a result
        result = tools.aurora_get(1)
        response = json.loads(result)

        # Should return error for expired cache
        assert "error" in response
        assert response["error"]["type"] in ["CacheExpired", "NoSearchResults"]
        assert (
            "expired" in response["error"]["message"].lower()
            or "search again" in response["error"]["message"].lower()
        )


# ==============================================================================
# Task 3.5: Response Format Tests
# ==============================================================================


class TestResponseFormat:
    """Test response format structure."""

    def test_response_includes_full_chunk(self):
        """Response should include full chunk with all metadata."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Set up cache with complete metadata
        mock_results = [
            {
                "chunk_id": "code:test.py:my_function",
                "content": "def my_function():\n    return 42",
                "file_path": "/path/to/test.py",
                "function_name": "my_function",
                "score": 0.95,
                "line_range": [10, 11],
            },
        ]
        tools._last_search_results = mock_results
        tools._last_search_timestamp = time.time()

        result = tools.aurora_get(1)
        response = json.loads(result)

        # Should have complete chunk
        assert "chunk" in response
        chunk = response["chunk"]

        # Verify all fields present
        assert "chunk_id" in chunk
        assert chunk["chunk_id"] == "code:test.py:my_function"
        assert "content" in chunk
        assert chunk["content"] == "def my_function():\n    return 42"
        assert "file_path" in chunk
        assert chunk["file_path"] == "/path/to/test.py"
        assert "function_name" in chunk
        assert chunk["function_name"] == "my_function"
        assert "score" in chunk
        assert chunk["score"] == 0.95
        assert "line_range" in chunk
        assert chunk["line_range"] == [10, 11]

    def test_response_includes_index_and_total(self):
        """Response should include index position and total count."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Set up cache with 5 results
        mock_results = [
            {
                "chunk_id": f"code:test{i}.py:func{i}",
                "content": f"content {i}",
                "file_path": f"test{i}.py",
                "function_name": f"func{i}",
                "score": 0.9 - (i * 0.1),
                "line_range": [1, 1],
            }
            for i in range(5)
        ]
        tools._last_search_results = mock_results
        tools._last_search_timestamp = time.time()

        # Get item 3 of 5
        result = tools.aurora_get(3)
        response = json.loads(result)

        # Should include metadata about position
        assert "metadata" in response
        metadata = response["metadata"]
        assert "index" in metadata
        assert metadata["index"] == 3  # The requested index
        assert "total_results" in metadata
        assert metadata["total_results"] == 5  # Total available
        # Optional: helpful message
        assert "retrieved_from" in metadata or "message" in metadata


# ==============================================================================
# Fixture: Mock Search Results for Tests
# ==============================================================================


@pytest.fixture
def sample_search_results():
    """Sample search results for testing."""
    return [
        {
            "chunk_id": f"code:module{i}.py:function_{i}",
            "content": f"def function_{i}():\n    return {i}",
            "file_path": f"/src/module{i}.py",
            "function_name": f"function_{i}",
            "score": 0.9 - (i * 0.05),
            "line_range": [i * 10, i * 10 + 2],
        }
        for i in range(1, 11)  # 10 results
    ]
