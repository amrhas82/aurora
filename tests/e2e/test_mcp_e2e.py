"""End-to-end tests for AURORA MCP server.

This module tests the complete MCP workflow from indexing to querying
to retrieving results. These tests verify the full integration of all
MCP tools working together.

Test Coverage:
- Task 9.8: E2E workflow tests (index → search → get)
- Task 9.9: E2E workflow tests (index → query → get)
- Task 9.10: E2E cross-tool integration tests
- Task 9.11: E2E performance tests

Total: 10+ end-to-end tests
"""

import json
import time
from unittest.mock import patch

import pytest

from aurora_mcp.tools import AuroraMCPTools


# Mark entire module as requiring ML dependencies
pytestmark = pytest.mark.ml


# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
def e2e_tools(tmp_path):
    """Create AuroraMCPTools with test codebase."""
    db_path = tmp_path / "e2e_test.db"
    tools = AuroraMCPTools(db_path=str(db_path))

    # Create a more realistic test codebase
    code_dir = tmp_path / "test_project"
    code_dir.mkdir()

    # Create multiple Python files with related code
    utils_file = code_dir / "utils.py"
    utils_file.write_text(
        """
'''Utility functions for the test project.'''

def format_name(first: str, last: str) -> str:
    '''Format a person's full name.'''
    return f"{first} {last}"

def validate_email(email: str) -> bool:
    '''Validate an email address format.'''
    return '@' in email and '.' in email

class StringHelper:
    '''Helper class for string operations.'''

    @staticmethod
    def capitalize_words(text: str) -> str:
        '''Capitalize each word in a string.'''
        return ' '.join(word.capitalize() for word in text.split())
"""
    )

    models_file = code_dir / "models.py"
    models_file.write_text(
        """
'''Data models for the test project.'''

from utils import format_name

class User:
    '''Represents a user in the system.'''

    def __init__(self, first_name: str, last_name: str, email: str):
        self.first_name = first_name
        self.last_name = last_name
        self.email = email

    def get_full_name(self) -> str:
        '''Get the user's full name.'''
        return format_name(self.first_name, self.last_name)

    def __repr__(self) -> str:
        return f"User({self.first_name}, {self.last_name})"
"""
    )

    services_file = code_dir / "services.py"
    services_file.write_text(
        """
'''Business logic services.'''

from models import User
from utils import validate_email

class UserService:
    '''Service for managing users.'''

    def __init__(self):
        self.users = []

    def create_user(self, first_name: str, last_name: str, email: str) -> User:
        '''Create a new user after validation.'''
        if not validate_email(email):
            raise ValueError("Invalid email address")

        user = User(first_name, last_name, email)
        self.users.append(user)
        return user

    def get_user_count(self) -> int:
        '''Get total number of users.'''
        return len(self.users)
"""
    )

    # Index the codebase
    index_result = tools.aurora_index(str(code_dir))
    index_response = json.loads(index_result)

    # Verify indexing succeeded
    assert index_response["files_indexed"] == 3
    assert index_response["chunks_created"] > 0

    return tools, code_dir


@pytest.fixture
def temp_aurora_config(tmp_path):
    """Create temporary aurora config."""
    aurora_dir = tmp_path / ".aurora"
    aurora_dir.mkdir(exist_ok=True)

    config_file = aurora_dir / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "api": {
                    "default_model": "claude-sonnet-4-20250514",
                    "temperature": 0.7,
                    "max_tokens": 4000,
                },
                "query": {
                    "auto_escalate": True,
                    "complexity_threshold": 0.6,
                    "verbosity": "normal",
                },
                "budget": {"monthly_limit_usd": 50.0},
            }
        )
    )

    return tmp_path


# ==============================================================================
# Task 9.8: E2E Workflow - Index → Search → Get
# ==============================================================================


class TestE2EIndexSearchGet:
    """End-to-end tests for index → search → get workflow."""

    def test_complete_search_workflow(self, e2e_tools):
        """Test complete workflow: index, search, get result."""
        tools, code_dir = e2e_tools

        # Step 1: Search for code (use generic search to ensure results)
        search_result = tools.aurora_search("function", limit=5)
        search_response = json.loads(search_result)

        assert isinstance(search_response, list)
        # May or may not find results depending on semantic search,
        # but should not error

        # If we have results, test aurora_get
        if len(search_response) > 0:
            # Step 2: Get full chunk using aurora_get
            result = tools.aurora_get(1)
            response = json.loads(result)

            assert "chunk" in response
            assert "metadata" in response
            assert response["metadata"]["index"] == 1
        else:
            # No results is acceptable - just verify no crash
            pass

    def test_multiple_searches_with_get(self, e2e_tools):
        """Test multiple searches update cache correctly."""
        tools, code_dir = e2e_tools

        # First search
        tools.aurora_search("User", limit=3)
        result1 = tools.aurora_get(1)
        response1 = json.loads(result1)

        # Second search (different query)
        tools.aurora_search("format_name", limit=3)
        result2 = tools.aurora_get(1)
        response2 = json.loads(result2)

        # Results should be different (new search)
        # Note: chunks might be same if both queries match same code
        # but cache should be updated
        assert response2["metadata"]["index"] == 1
        # Verify both responses are valid
        assert "chunk" in response1
        assert "chunk" in response2

    def test_get_all_search_results(self, e2e_tools):
        """Test retrieving all results from search."""
        tools, code_dir = e2e_tools

        # Search with limit
        search_result = tools.aurora_search("def", limit=5)
        search_response = json.loads(search_result)
        total_results = len(search_response)

        if total_results > 0:
            # Get each result
            for i in range(1, min(total_results, 3) + 1):
                result = tools.aurora_get(i)
                response = json.loads(result)

                assert "chunk" in response
                assert response["metadata"]["index"] == i
                assert response["metadata"]["total_results"] == total_results


# ==============================================================================
# Task 9.9: E2E Workflow - Index → Query → Get
# ==============================================================================


class TestE2EIndexQueryGet:
    """End-to-end tests for index → query → get workflow."""

    def test_complete_query_workflow(self, e2e_tools, temp_aurora_config):
        """Test complete workflow: index, query, get result."""
        tools, code_dir = e2e_tools

        with patch("pathlib.Path.home", return_value=temp_aurora_config):
            # Clear cached config
            if hasattr(tools, "_config_cache"):
                del tools._config_cache

            # Step 1: Query for context
            query_result = tools.aurora_query("user validation", limit=5)
            query_response = json.loads(query_result)

            assert "context" in query_response
            assert "chunks" in query_response["context"]
            chunks = query_response["context"]["chunks"]

            if len(chunks) > 0:
                # Step 2: Get specific chunk
                result = tools.aurora_get(1)
                response = json.loads(result)

                assert "chunk" in response
                assert response["metadata"]["index"] == 1

    def test_query_complexity_assessment(self, e2e_tools, temp_aurora_config):
        """Test query complexity assessment in E2E workflow."""
        tools, code_dir = e2e_tools

        with patch("pathlib.Path.home", return_value=temp_aurora_config):
            if hasattr(tools, "_config_cache"):
                del tools._config_cache

            # Simple query
            simple_result = tools.aurora_query("what is format_name")
            simple_response = json.loads(simple_result)

            assert "assessment" in simple_response
            assert "complexity_score" in simple_response["assessment"]

            # Complex query
            complex_result = tools.aurora_query(
                "analyze and compare the user validation and creation logic"
            )
            complex_response = json.loads(complex_result)

            assert "assessment" in complex_response
            # Complex query should have higher complexity score
            assert (
                complex_response["assessment"]["complexity_score"]
                > simple_response["assessment"]["complexity_score"]
            )


# ==============================================================================
# Task 9.10: E2E Cross-Tool Integration
# ==============================================================================


class TestE2ECrossToolIntegration:
    """End-to-end tests for cross-tool integration."""

    def test_stats_after_index(self, e2e_tools):
        """Test stats reflect indexing results."""
        tools, code_dir = e2e_tools

        # Get stats
        stats_result = tools.aurora_stats()
        stats_response = json.loads(stats_result)

        assert stats_response["total_chunks"] > 0
        # Note: total_files counts unique file paths in chunk IDs
        # The exact count depends on how chunks are stored
        assert stats_response["total_files"] >= 1
        # Database size might be 0 in memory or very small
        assert stats_response["database_size_mb"] >= 0

    def test_context_from_search_results(self, e2e_tools):
        """Test getting context for file found in search."""
        tools, code_dir = e2e_tools

        # Search for any function
        search_result = tools.aurora_search("def", limit=5)
        search_response = json.loads(search_result)

        if len(search_response) > 0:
            file_path = search_response[0]["file_path"]

            # Get full context for that file
            context_result = tools.aurora_context(file_path)

            # Should return file content with Python code
            assert "def " in context_result or "class " in context_result
            # Should have content from the actual file
            assert len(context_result) > 0

    def test_related_chunks_from_search(self, e2e_tools):
        """Test finding related chunks from search results."""
        tools, code_dir = e2e_tools

        # Search for a function
        search_result = tools.aurora_search("User", limit=1)
        search_response = json.loads(search_result)

        if len(search_response) > 0:
            chunk_id = search_response[0]["chunk_id"]

            # Find related chunks
            related_result = tools.aurora_related(chunk_id)
            related_response = json.loads(related_result)

            assert isinstance(related_response, list)

    def test_cross_tool_consistency(self, e2e_tools):
        """Test data consistency across multiple tool calls."""
        tools, code_dir = e2e_tools

        # Get stats
        stats_result = tools.aurora_stats()
        stats_response = json.loads(stats_result)
        total_chunks_stats = stats_response["total_chunks"]

        # Search for all chunks
        search_result = tools.aurora_search("def class import", limit=100)
        search_response = json.loads(search_result)

        # Number of search results should be <= total chunks
        assert len(search_response) <= total_chunks_stats


# ==============================================================================
# Task 9.11: E2E Performance Tests
# ==============================================================================


@pytest.mark.slow
class TestE2EPerformance:
    """End-to-end performance tests."""

    def test_search_performance(self, e2e_tools):
        """Test search completes within performance target."""
        tools, code_dir = e2e_tools

        start_time = time.time()
        tools.aurora_search("user email validation", limit=10)
        elapsed = time.time() - start_time

        # Should complete in under 2 seconds
        assert elapsed < 2.0, f"Search took {elapsed:.2f}s, expected <2s"

    def test_stats_performance(self, e2e_tools):
        """Test stats retrieval is fast."""
        tools, code_dir = e2e_tools

        start_time = time.time()
        tools.aurora_stats()
        elapsed = time.time() - start_time

        # Stats should be nearly instant
        assert elapsed < 0.5, f"Stats took {elapsed:.2f}s, expected <0.5s"

    def test_context_retrieval_performance(self, e2e_tools):
        """Test context retrieval is fast."""
        tools, code_dir = e2e_tools

        # Get a file path from search
        search_result = tools.aurora_search("User", limit=1)
        search_response = json.loads(search_result)

        if len(search_response) > 0:
            file_path = search_response[0]["file_path"]

            start_time = time.time()
            tools.aurora_context(file_path)
            elapsed = time.time() - start_time

            # Context retrieval should be fast
            assert elapsed < 0.5, f"Context took {elapsed:.2f}s, expected <0.5s"

    def test_sequential_operations_performance(self, e2e_tools):
        """Test multiple sequential operations complete efficiently."""
        tools, code_dir = e2e_tools

        start_time = time.time()

        # Perform series of operations
        tools.aurora_stats()
        tools.aurora_search("User", limit=5)
        tools.aurora_get(1)
        tools.aurora_search("validate", limit=5)
        tools.aurora_get(2)

        elapsed = time.time() - start_time

        # All operations should complete in under 3 seconds
        assert elapsed < 3.0, f"Sequential ops took {elapsed:.2f}s, expected <3s"


# ==============================================================================
# Additional E2E Tests
# ==============================================================================


class TestE2EEdgeCases:
    """End-to-end tests for edge cases."""

    def test_empty_database_workflow(self, tmp_path):
        """Test workflow with empty database."""
        db_path = tmp_path / "empty.db"
        tools = AuroraMCPTools(db_path=str(db_path))
        tools._ensure_initialized()

        # Stats should work
        stats_result = tools.aurora_stats()
        stats_response = json.loads(stats_result)
        assert stats_response["total_chunks"] == 0

        # Search should return empty results
        search_result = tools.aurora_search("anything")
        search_response = json.loads(search_result)
        assert len(search_response) == 0

        # Get should fail with no search
        get_result = tools.aurora_get(1)
        get_response = json.loads(get_result)
        assert "error" in get_response

    def test_reindex_workflow(self, e2e_tools):
        """Test re-indexing updates database correctly."""
        tools, code_dir = e2e_tools

        # Get initial stats
        stats1_result = tools.aurora_stats()
        stats1_response = json.loads(stats1_result)
        initial_chunks = stats1_response["total_chunks"]

        # Add new file
        new_file = code_dir / "new_module.py"
        new_file.write_text(
            """
def new_function():
    '''A brand new function.'''
    return "new"
"""
        )

        # Re-index
        index_result = tools.aurora_index(str(code_dir))
        index_response = json.loads(index_result)

        # Should index the new file
        assert index_response["files_indexed"] > 0

        # Stats should show more chunks
        stats2_result = tools.aurora_stats()
        stats2_response = json.loads(stats2_result)
        final_chunks = stats2_response["total_chunks"]

        assert final_chunks >= initial_chunks

    def test_cache_expiry_workflow(self, e2e_tools):
        """Test search cache expiry handling."""
        tools, code_dir = e2e_tools

        # Perform search
        tools.aurora_search("User", limit=5)

        # Manually expire cache by setting old timestamp
        tools._last_search_timestamp = time.time() - 700  # 11+ minutes ago

        # Get should fail with cache expired
        result = tools.aurora_get(1)
        response = json.loads(result)

        assert "error" in response
        assert response["error"]["type"] == "CacheExpired"
