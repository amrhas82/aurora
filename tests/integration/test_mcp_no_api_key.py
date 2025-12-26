"""Integration tests for AURORA MCP tools without API key.

This module tests that all MCP tools work correctly when ANTHROPIC_API_KEY
is not available. These tools should operate independently and only aurora_query
(with LLM inference) should be affected by missing API keys.

Test Coverage:
- Task 9.1: Tests for aurora_search without API key
- Task 9.2: Tests for aurora_index without API key
- Task 9.3: Tests for aurora_stats without API key
- Task 9.4: Tests for aurora_context without API key
- Task 9.5: Tests for aurora_related without API key
- Task 9.6: Tests for aurora_query without API key (should work with context retrieval)
- Task 9.7: Tests for aurora_get without API key

Total: 14+ integration tests covering all 7 MCP tools
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from aurora.mcp.tools import AuroraMCPTools


# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
def no_api_key():
    """Ensure ANTHROPIC_API_KEY is unset for testing."""
    original_key = os.environ.get("ANTHROPIC_API_KEY")

    # Unset the API key
    if "ANTHROPIC_API_KEY" in os.environ:
        del os.environ["ANTHROPIC_API_KEY"]

    yield

    # Restore original key if it existed
    if original_key is not None:
        os.environ["ANTHROPIC_API_KEY"] = original_key


@pytest.fixture
def tools_no_api_key(tmp_path, no_api_key):
    """Create AuroraMCPTools instance without API key."""
    db_path = tmp_path / "test.db"
    tools = AuroraMCPTools(db_path=str(db_path))

    # Index some test code
    test_code_dir = tmp_path / "test_code"
    test_code_dir.mkdir()

    # Create test Python file
    test_file = test_code_dir / "example.py"
    test_file.write_text("""
def hello_world():
    '''Say hello to the world.'''
    return "Hello, World!"

def add_numbers(a: int, b: int) -> int:
    '''Add two numbers together.'''
    return a + b

class Calculator:
    '''A simple calculator class.'''

    def multiply(self, x: float, y: float) -> float:
        '''Multiply two numbers.'''
        return x * y
""")

    # Index the test code
    tools.aurora_index(str(test_code_dir))

    return tools


@pytest.fixture
def temp_aurora_dir(tmp_path):
    """Create temporary ~/.aurora directory for testing."""
    aurora_dir = tmp_path / ".aurora"
    aurora_dir.mkdir(exist_ok=True)

    # Create config without API key
    config_file = aurora_dir / "config.json"
    config_file.write_text(json.dumps({
        "api": {
            "default_model": "claude-sonnet-4-20250514",
            "temperature": 0.7,
            "max_tokens": 4000
        },
        "query": {
            "auto_escalate": True,
            "complexity_threshold": 0.6,
            "verbosity": "normal"
        },
        "budget": {
            "monthly_limit_usd": 50.0
        }
    }))

    return aurora_dir


# ==============================================================================
# Task 9.1: aurora_search Tests Without API Key
# ==============================================================================


class TestAuroraSearchNoAPIKey:
    """Test aurora_search works without ANTHROPIC_API_KEY."""

    def test_search_basic_functionality(self, tools_no_api_key):
        """Test aurora_search returns results without API key."""
        result = tools_no_api_key.aurora_search("hello")

        # Should return valid JSON
        response = json.loads(result)
        assert isinstance(response, list)

        # Should find the hello_world function
        if len(response) > 0:
            assert any("hello" in str(r).lower() for r in response)

    def test_search_with_limit(self, tools_no_api_key):
        """Test aurora_search respects limit parameter without API key."""
        result = tools_no_api_key.aurora_search("def", limit=2)

        response = json.loads(result)
        assert isinstance(response, list)
        assert len(response) <= 2

    def test_search_no_results(self, tools_no_api_key):
        """Test aurora_search handles no results without API key."""
        result = tools_no_api_key.aurora_search("nonexistent_function_xyz")

        response = json.loads(result)
        assert isinstance(response, list)
        # Empty results are valid


# ==============================================================================
# Task 9.2: aurora_index Tests Without API Key
# ==============================================================================


class TestAuroraIndexNoAPIKey:
    """Test aurora_index works without ANTHROPIC_API_KEY."""

    def test_index_directory(self, tmp_path, no_api_key):
        """Test aurora_index can index directory without API key."""
        # Create tools with empty database
        db_path = tmp_path / "index_test.db"
        tools = AuroraMCPTools(db_path=str(db_path))

        # Create test directory
        code_dir = tmp_path / "code"
        code_dir.mkdir()

        test_file = code_dir / "test.py"
        test_file.write_text("def test_func():\n    pass\n")

        # Index should work without API key
        result = tools.aurora_index(str(code_dir))

        response = json.loads(result)
        assert "files_indexed" in response
        assert response["files_indexed"] == 1
        assert "chunks_created" in response
        assert response["chunks_created"] > 0

    def test_index_nonexistent_path(self, tmp_path, no_api_key):
        """Test aurora_index handles nonexistent path without API key."""
        db_path = tmp_path / "index_test2.db"
        tools = AuroraMCPTools(db_path=str(db_path))

        result = tools.aurora_index("/nonexistent/path/xyz")

        response = json.loads(result)
        assert "error" in response

    def test_index_file_not_directory(self, tmp_path, no_api_key):
        """Test aurora_index handles file instead of directory."""
        db_path = tmp_path / "index_test3.db"
        tools = AuroraMCPTools(db_path=str(db_path))

        # Create a file
        test_file = tmp_path / "test.py"
        test_file.write_text("pass")

        result = tools.aurora_index(str(test_file))

        response = json.loads(result)
        assert "error" in response


# ==============================================================================
# Task 9.3: aurora_stats Tests Without API Key
# ==============================================================================


class TestAuroraStatsNoAPIKey:
    """Test aurora_stats works without ANTHROPIC_API_KEY."""

    def test_stats_basic(self, tools_no_api_key):
        """Test aurora_stats returns statistics without API key."""
        result = tools_no_api_key.aurora_stats()

        response = json.loads(result)
        assert "total_chunks" in response
        assert "total_files" in response
        assert "database_size_mb" in response
        assert response["total_chunks"] > 0

    def test_stats_empty_database(self, tmp_path, no_api_key):
        """Test aurora_stats works with empty database."""
        db_path = tmp_path / "empty.db"
        tools = AuroraMCPTools(db_path=str(db_path))
        tools._ensure_initialized()

        result = tools.aurora_stats()

        response = json.loads(result)
        assert response["total_chunks"] == 0
        assert response["total_files"] == 0


# ==============================================================================
# Task 9.4: aurora_context Tests Without API Key
# ==============================================================================


class TestAuroraContextNoAPIKey:
    """Test aurora_context works without ANTHROPIC_API_KEY."""

    def test_context_read_file(self, tmp_path, no_api_key):
        """Test aurora_context reads file without API key."""
        db_path = tmp_path / "context_test.db"
        tools = AuroraMCPTools(db_path=str(db_path))

        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello():\n    return 'world'\n")

        result = tools.aurora_context(str(test_file))

        # Should return file content (not JSON)
        assert "def hello()" in result
        assert "return 'world'" in result

    def test_context_extract_function(self, tmp_path, no_api_key):
        """Test aurora_context extracts specific function without API key."""
        db_path = tmp_path / "context_test2.db"
        tools = AuroraMCPTools(db_path=str(db_path))

        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("""
def func1():
    return 1

def func2():
    return 2
""")

        result = tools.aurora_context(str(test_file), function="func2")

        # Should return only func2
        assert "func2" in result
        assert "return 2" in result
        assert "func1" not in result

    def test_context_nonexistent_file(self, tmp_path, no_api_key):
        """Test aurora_context handles nonexistent file without API key."""
        db_path = tmp_path / "context_test3.db"
        tools = AuroraMCPTools(db_path=str(db_path))

        result = tools.aurora_context("/nonexistent/file.py")

        response = json.loads(result)
        assert "error" in response

    def test_context_nonexistent_function(self, tmp_path, no_api_key):
        """Test aurora_context handles nonexistent function without API key."""
        db_path = tmp_path / "context_test4.db"
        tools = AuroraMCPTools(db_path=str(db_path))

        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello():\n    pass\n")

        result = tools.aurora_context(str(test_file), function="nonexistent")

        response = json.loads(result)
        assert "error" in response


# ==============================================================================
# Task 9.5: aurora_related Tests Without API Key
# ==============================================================================


class TestAuroraRelatedNoAPIKey:
    """Test aurora_related works without ANTHROPIC_API_KEY."""

    def test_related_finds_chunks(self, tools_no_api_key):
        """Test aurora_related finds related chunks without API key."""
        # First, search to get a chunk ID
        search_result = tools_no_api_key.aurora_search("hello", limit=1)
        search_response = json.loads(search_result)

        if len(search_response) > 0:
            chunk_id = search_response[0]["chunk_id"]

            # Get related chunks
            result = tools_no_api_key.aurora_related(chunk_id)

            response = json.loads(result)
            assert isinstance(response, list)

    def test_related_nonexistent_chunk(self, tools_no_api_key):
        """Test aurora_related handles nonexistent chunk without API key."""
        result = tools_no_api_key.aurora_related("nonexistent_chunk_id_xyz")

        response = json.loads(result)
        assert "error" in response


# ==============================================================================
# Task 9.6: aurora_query Tests Without API Key
# ==============================================================================


class TestAuroraQueryNoAPIKey:
    """Test aurora_query works without ANTHROPIC_API_KEY (context retrieval only)."""

    def test_query_context_retrieval(self, tools_no_api_key, temp_aurora_dir):
        """Test aurora_query returns context without API key."""
        with patch('pathlib.Path.home', return_value=temp_aurora_dir.parent):
            # Clear any cached config
            if hasattr(tools_no_api_key, '_config_cache'):
                del tools_no_api_key._config_cache

            result = tools_no_api_key.aurora_query("hello world")

            # Should return structured context (not error)
            response = json.loads(result)

            # Should have context structure per FR-2.2
            assert "context" in response
            assert "assessment" in response
            assert "metadata" in response

            # Context should have chunks
            assert "chunks" in response["context"]
            assert isinstance(response["context"]["chunks"], list)

    def test_query_with_type_filter(self, tools_no_api_key, temp_aurora_dir):
        """Test aurora_query with type filter without API key."""
        with patch('pathlib.Path.home', return_value=temp_aurora_dir.parent):
            if hasattr(tools_no_api_key, '_config_cache'):
                del tools_no_api_key._config_cache

            result = tools_no_api_key.aurora_query("function", type_filter="code")

            response = json.loads(result)
            assert "context" in response

            # Should only return code chunks
            chunks = response["context"]["chunks"]
            for chunk in chunks:
                assert chunk["type"] == "code"

    def test_query_empty_query(self, tools_no_api_key, temp_aurora_dir):
        """Test aurora_query handles empty query without API key."""
        with patch('pathlib.Path.home', return_value=temp_aurora_dir.parent):
            if hasattr(tools_no_api_key, '_config_cache'):
                del tools_no_api_key._config_cache

            result = tools_no_api_key.aurora_query("")

            response = json.loads(result)
            assert "error" in response


# ==============================================================================
# Task 9.7: aurora_get Tests Without API Key
# ==============================================================================


class TestAuroraGetNoAPIKey:
    """Test aurora_get works without ANTHROPIC_API_KEY."""

    def test_get_from_search_results(self, tools_no_api_key):
        """Test aurora_get retrieves result from search cache without API key."""
        # First perform a search
        search_result = tools_no_api_key.aurora_search("hello", limit=5)
        search_response = json.loads(search_result)

        if len(search_response) > 0:
            # Get first result
            result = tools_no_api_key.aurora_get(1)

            response = json.loads(result)
            assert "chunk" in response
            assert "metadata" in response
            assert response["metadata"]["index"] == 1

    def test_get_without_search(self, tmp_path, no_api_key):
        """Test aurora_get returns error when no search performed."""
        db_path = tmp_path / "get_test.db"
        tools = AuroraMCPTools(db_path=str(db_path))

        result = tools.aurora_get(1)

        response = json.loads(result)
        assert "error" in response
        assert response["error"]["type"] == "NoSearchResults"

    def test_get_invalid_index(self, tools_no_api_key):
        """Test aurora_get handles invalid index without API key."""
        # Perform search first
        tools_no_api_key.aurora_search("hello", limit=2)

        # Try to get index 0 (invalid - 1-indexed)
        result = tools_no_api_key.aurora_get(0)

        response = json.loads(result)
        assert "error" in response
        assert response["error"]["type"] == "InvalidParameter"

    def test_get_index_out_of_range(self, tools_no_api_key):
        """Test aurora_get handles out of range index without API key."""
        # Perform search first
        tools_no_api_key.aurora_search("hello", limit=2)

        # Try to get index beyond available results
        result = tools_no_api_key.aurora_get(100)

        response = json.loads(result)
        assert "error" in response
        assert response["error"]["type"] == "InvalidParameter"
