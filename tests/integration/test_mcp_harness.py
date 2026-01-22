"""MCP Test Harness - FastMCP Testing Integration

This module provides a test harness for Aurora's MCP server using FastMCP
testing utilities. It validates that all 5 MCP tools work correctly with
proper JSON responses and error handling.

Tests:
- aurora_search: semantic search over indexed code
- aurora_index: indexing files into memory store
- aurora_stats: database statistics
- aurora_context: file content retrieval
- aurora_related: relationship-based chunk traversal
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

# Import MCP tools directly for testing
from aurora_mcp.tools import AuroraMCPTools


# Skip all tests in this module unless MCP is explicitly enabled (PRD-0024)
pytestmark = pytest.mark.skipif(
    not os.environ.get("AURORA_ENABLE_MCP"),
    reason="MCP not enabled (use AURORA_ENABLE_MCP=1 to run)",
)


@pytest.mark.ml
class TestMCPHarness:
    """Test harness for MCP server tools using FastMCP patterns."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        # Cleanup
        Path(db_path).unlink(missing_ok=True)

    @pytest.fixture
    def mcp_tools(self, temp_db):
        """Create MCP tools instance."""
        return AuroraMCPTools(db_path=temp_db)

    @pytest.fixture
    def codebase(self, tmp_path):
        """Create test codebase for indexing."""
        codebase = tmp_path / "test_code"
        codebase.mkdir()

        # Create sample Python file
        test_file = codebase / "sample.py"
        test_file.write_text(
            '''"""Sample module for MCP testing."""


def hello_world(name: str) -> str:
    """Greet someone by name."""
    return f"Hello, {name}!"


def add_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b
''',
        )

        return codebase

    def test_aurora_search_valid_json(self, mcp_tools, codebase):
        """Test that aurora_search returns valid JSON."""
        # Index first
        mcp_tools.aurora_index(str(codebase))

        # Search
        result = mcp_tools.aurora_search("hello world greeting")

        # Verify it's valid JSON
        if isinstance(result, str):
            data = json.loads(result)
        else:
            data = result

        # Should be a list
        assert isinstance(data, list), "Result should be a list"

        # Verify required fields if results exist
        if len(data) > 0:
            for item in data:
                assert "file_path" in item, "Should have file_path"
                assert "score" in item, "Should have score"

    def test_aurora_index_returns_stats(self, mcp_tools, codebase):
        """Test that aurora_index successfully indexes and returns stats."""
        result = mcp_tools.aurora_index(str(codebase))

        # Parse result
        if isinstance(result, str):
            data = json.loads(result)
        else:
            data = result

        # Verify required fields
        assert "files_indexed" in data, "Should have files_indexed"
        assert "chunks_created" in data, "Should have chunks_created"
        assert "duration_seconds" in data, "Should have duration_seconds"

        # Verify values make sense
        assert data["files_indexed"] >= 1, "Should index at least 1 file"
        assert data["chunks_created"] >= 1, "Should create at least 1 chunk"
        assert data["duration_seconds"] >= 0, "Duration should be non-negative"

    def test_aurora_stats_returns_counts(self, mcp_tools, codebase):
        """Test that aurora_stats returns valid counts."""
        # Index first
        mcp_tools.aurora_index(str(codebase))

        # Get stats
        result = mcp_tools.aurora_stats()

        # Parse result
        if isinstance(result, str):
            data = json.loads(result)
        else:
            data = result

        # Verify required fields
        assert "total_chunks" in data, "Should have total_chunks"
        assert "total_files" in data, "Should have total_files"
        assert "database_size_mb" in data, "Should have database_size_mb"

        # Verify values
        assert data["total_chunks"] > 0, "Should have chunks after indexing"
        assert data["total_files"] > 0, "Should have files after indexing"
        assert data["database_size_mb"] >= 0, "Database size should be non-negative"

    def test_aurora_context_retrieves_file(self, mcp_tools, codebase):
        """Test that aurora_context retrieves file content correctly."""
        # Get path to sample file
        sample_file = codebase / "sample.py"

        # Retrieve content
        result = mcp_tools.aurora_context(str(sample_file))

        # Verify content
        if isinstance(result, dict) and "error" in result:
            pytest.fail(f"aurora_context returned error: {result['error']}")

        assert isinstance(result, str), "Should return string content"
        assert "hello_world" in result, "Should contain function name"
        assert "def" in result, "Should contain Python code"

    def test_aurora_context_with_nonexistent_file(self, mcp_tools):
        """Test aurora_context handles non-existent files gracefully."""
        result = mcp_tools.aurora_context("/nonexistent/file.py")

        # Should return error JSON
        if isinstance(result, str):
            data = json.loads(result)
        else:
            data = result

        assert "error" in data, "Should have error field"

    def test_aurora_related_returns_chunks(self, mcp_tools, codebase):
        """Test that aurora_related returns related chunks."""
        # Index first
        mcp_tools.aurora_index(str(codebase))

        # Search to get a chunk ID
        search_result = mcp_tools.aurora_search("hello")
        if isinstance(search_result, str):
            search_data = json.loads(search_result)
        else:
            search_data = search_result

        if len(search_data) > 0:
            chunk_id = search_data[0].get("chunk_id")

            # Get related chunks
            result = mcp_tools.aurora_related(chunk_id)

            # Parse result
            if isinstance(result, str):
                data = json.loads(result)
            else:
                data = result

            # Should be a list (may be empty if no relationships)
            assert isinstance(data, list), "Result should be a list"

    def test_error_handling_invalid_inputs(self, mcp_tools):
        """Test that MCP tools handle invalid inputs gracefully."""
        # Test 1: Empty query for search
        try:
            result = mcp_tools.aurora_search("")
            if isinstance(result, str):
                data = json.loads(result)
            else:
                data = result
            # Should return error or empty list
            assert isinstance(data, (list, dict)), "Should return valid JSON"
        except Exception as e:
            # Exception is acceptable for invalid input
            assert "empty" in str(e).lower() or "invalid" in str(e).lower()

        # Test 2: Non-existent path for index
        result = mcp_tools.aurora_index("/nonexistent/path")
        if isinstance(result, str):
            data = json.loads(result)
        else:
            data = result
        assert "error" in data, "Should return error for non-existent path"

    def test_all_tools_return_valid_json(self, mcp_tools, codebase):
        """Test that all tools return valid JSON (no exceptions)."""
        # Index codebase
        index_result = mcp_tools.aurora_index(str(codebase))
        assert index_result is not None, "aurora_index should return result"

        # Search
        search_result = mcp_tools.aurora_search("hello")
        assert search_result is not None, "aurora_search should return result"

        # Stats
        stats_result = mcp_tools.aurora_stats()
        assert stats_result is not None, "aurora_stats should return result"

        # Context
        sample_file = codebase / "sample.py"
        context_result = mcp_tools.aurora_context(str(sample_file))
        assert context_result is not None, "aurora_context should return result"

        # Related (use chunk_id from search if available)
        if isinstance(search_result, str):
            search_data = json.loads(search_result)
        else:
            search_data = search_result

        if len(search_data) > 0:
            chunk_id = search_data[0].get("chunk_id", "test_chunk")
            related_result = mcp_tools.aurora_related(chunk_id)
            assert related_result is not None, "aurora_related should return result"


@pytest.mark.ml
class TestMCPHarnessEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        Path(db_path).unlink(missing_ok=True)

    @pytest.fixture
    def mcp_tools(self, temp_db):
        """Create MCP tools instance."""
        return AuroraMCPTools(db_path=temp_db)

    def test_search_on_empty_database(self, mcp_tools):
        """Test search on empty database returns empty list."""
        result = mcp_tools.aurora_search("anything")

        if isinstance(result, str):
            data = json.loads(result)
        else:
            data = result

        # Should return empty list or error, not crash
        assert isinstance(data, (list, dict)), "Should return valid JSON"
        if isinstance(data, list):
            assert len(data) == 0, "Empty database should return empty results"

    def test_stats_on_empty_database(self, mcp_tools):
        """Test stats on empty database returns zeros."""
        result = mcp_tools.aurora_stats()

        if isinstance(result, str):
            data = json.loads(result)
        else:
            data = result

        # Should return valid stats with zero counts
        assert "total_chunks" in data, "Should have total_chunks"
        assert data["total_chunks"] == 0, "Empty database should have 0 chunks"

    def test_index_empty_directory(self, mcp_tools, tmp_path):
        """Test indexing empty directory returns zero stats."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = mcp_tools.aurora_index(str(empty_dir))

        if isinstance(result, str):
            data = json.loads(result)
        else:
            data = result

        # Should succeed with zero files
        assert data["files_indexed"] == 0, "Empty directory should index 0 files"
        assert data["chunks_created"] == 0, "Empty directory should create 0 chunks"

    def test_related_with_invalid_chunk_id(self, mcp_tools):
        """Test aurora_related with invalid chunk ID."""
        result = mcp_tools.aurora_related("invalid_chunk_id")

        if isinstance(result, str):
            data = json.loads(result)
        else:
            data = result

        # Should return error or empty list
        assert isinstance(data, (list, dict)), "Should return valid JSON"


@pytest.mark.ml
class TestMCPHarnessPerformance:
    """Performance and stress tests for MCP tools."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        Path(db_path).unlink(missing_ok=True)

    @pytest.fixture
    def mcp_tools(self, temp_db):
        """Create MCP tools instance."""
        return AuroraMCPTools(db_path=temp_db)

    def test_search_performance(self, mcp_tools, tmp_path):
        """Test search performance with moderate dataset."""
        # Create moderate codebase (10 files)
        codebase = tmp_path / "codebase"
        codebase.mkdir()

        for i in range(10):
            file_path = codebase / f"module_{i}.py"
            file_path.write_text(
                f'''"""Module {i} for testing."""

def function_{i}(x):
    """Function {i} implementation."""
    return x * {i}
''',
            )

        # Index
        index_result = mcp_tools.aurora_index(str(codebase))
        if isinstance(index_result, str):
            index_data = json.loads(index_result)
        else:
            index_data = index_result

        # Verify indexing succeeded
        assert index_data["files_indexed"] == 10, "Should index all 10 files"

        # Perform search (should complete in reasonable time)
        import time

        start = time.time()
        result = mcp_tools.aurora_search("function implementation")
        elapsed = time.time() - start

        # Should complete in under 5 seconds
        assert elapsed < 5.0, f"Search took {elapsed:.2f}s, should be under 5s"

        # Verify results
        if isinstance(result, str):
            data = json.loads(result)
        else:
            data = result

        assert len(data) > 0, "Should find matching functions"
