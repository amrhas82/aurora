"""Unit tests for simplified aurora_query MCP tool (PRD-0008).

This module tests the NEW simplified aurora_query that returns structured context
instead of calling LLM APIs. These tests are written FIRST (TDD RED phase) before
implementing the simplified functionality.

Test Coverage:
- Parameter validation (empty query, invalid type filters)
- Response format (context, assessment, metadata sections)
- Confidence handling (low confidence suggestions)
- Type filtering (code, reas, know)
- Complexity assessment (heuristic-based)
- No API key required (works without ANTHROPIC_API_KEY)

Expected State: ALL TESTS SHOULD FAIL initially (TDD RED phase).
After implementation: ALL TESTS SHOULD PASS (TDD GREEN phase).
"""

import json
import os
from pathlib import Path  # noqa: F401
from unittest.mock import MagicMock, Mock, patch  # noqa: F401

import pytest

from aurora_mcp.tools import AuroraMCPTools

# Skip all tests in this file - MCP functionality is dormant (PRD-0024)
# aurora_query tool was never implemented, only aurora_search and aurora_get exist
pytestmark = pytest.mark.skip(
    reason="MCP aurora_query not implemented - functionality dormant (PRD-0024)",
)


# ==============================================================================
# Task 2.2: Parameter Validation Tests
# ==============================================================================


class TestParameterValidation:
    """Test parameter validation for simplified aurora_query."""

    def test_query_empty_string_returns_error(self):
        """Empty query string should return InvalidParameter error."""
        tools = AuroraMCPTools(db_path=":memory:")
        result = tools.aurora_query("")

        response = json.loads(result)
        assert "error" in response
        assert response["error"]["type"] == "InvalidParameter"
        assert "empty" in response["error"]["message"].lower()

    def test_query_whitespace_only_returns_error(self):
        """Whitespace-only query should return InvalidParameter error."""
        tools = AuroraMCPTools(db_path=":memory:")
        result = tools.aurora_query("   \n\t   ")

        response = json.loads(result)
        assert "error" in response
        assert response["error"]["type"] == "InvalidParameter"
        assert "empty" in response["error"]["message"].lower()

    def test_invalid_type_filter_returns_error(self):
        """Invalid type_filter should return InvalidParameter error with valid options."""
        tools = AuroraMCPTools(db_path=":memory:")
        result = tools.aurora_query("test query", type_filter="invalid_type")

        response = json.loads(result)
        assert "error" in response
        assert response["error"]["type"] == "InvalidParameter"
        assert "type_filter" in response["error"]["message"].lower()
        # Should suggest valid options
        assert "code" in response["error"]["suggestion"] or "code" in response["error"]["message"]
        assert "reas" in response["error"]["suggestion"] or "reas" in response["error"]["message"]
        assert "know" in response["error"]["suggestion"] or "know" in response["error"]["message"]

    def test_valid_type_filters_accepted(self):
        """Valid type filters (code, reas, know, None) should be accepted."""
        tools = AuroraMCPTools(db_path=":memory:")

        valid_filters = ["code", "reas", "know", None]
        for filter_type in valid_filters:
            result = tools.aurora_query("test query", type_filter=filter_type)
            response = json.loads(result)

            # Should NOT have InvalidParameter error for type_filter
            if "error" in response:
                assert (
                    "type_filter" not in response["error"]["message"].lower()
                ), f"Valid type_filter '{filter_type}' was rejected"


# ==============================================================================
# Task 2.3: Response Format Tests
# ==============================================================================


class TestResponseFormat:
    """Test response format structure (FR-2.2)."""

    def test_response_contains_context_section(self):
        """Response must include 'context' section with chunks."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Mock retrieval to return some chunks
        with patch.object(
            tools,
            "_retrieve_chunks",
            return_value=[
                {
                    "id": "code:test.py:func",
                    "type": "code",
                    "content": "def func(): pass",
                    "file_path": "test.py",
                    "line_range": [1, 1],
                    "relevance_score": 0.9,
                },
            ],
        ):
            result = tools.aurora_query("test query")
            response = json.loads(result)

            assert "context" in response
            assert "chunks" in response["context"]
            assert isinstance(response["context"]["chunks"], list)

    def test_response_contains_assessment_section(self):
        """Response must include 'assessment' section with complexity and confidence."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, "_retrieve_chunks", return_value=[]):
            result = tools.aurora_query("test query")
            response = json.loads(result)

            assert "assessment" in response
            assert "complexity_score" in response["assessment"]
            assert "suggested_approach" in response["assessment"]
            assert "retrieval_confidence" in response["assessment"]

    def test_response_contains_metadata_section(self):
        """Response must include 'metadata' section with query info and stats."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, "_retrieve_chunks", return_value=[]):
            result = tools.aurora_query("test query")
            response = json.loads(result)

            assert "metadata" in response
            assert "query" in response["metadata"]
            assert "retrieval_time_ms" in response["metadata"]
            assert "index_stats" in response["metadata"]
            assert response["metadata"]["query"] == "test query"

    def test_chunks_are_numbered(self):
        """Chunks must be numbered (1, 2, 3...) for easy reference (FR-2.3)."""
        tools = AuroraMCPTools(db_path=":memory:")

        mock_chunks = [
            {
                "id": f"code:test{i}.py:func",
                "type": "code",
                "content": f"content {i}",
                "file_path": f"test{i}.py",
                "line_range": [1, 1],
                "relevance_score": 0.8,
            }
            for i in range(3)
        ]

        with patch.object(tools, "_retrieve_chunks", return_value=mock_chunks):
            result = tools.aurora_query("test query")
            response = json.loads(result)

            chunks = response["context"]["chunks"]
            assert len(chunks) == 3
            # Should have number field starting from 1
            assert chunks[0]["number"] == 1
            assert chunks[1]["number"] == 2
            assert chunks[2]["number"] == 3

    def test_relevance_scores_included(self):
        """Each chunk must include relevance_score."""
        tools = AuroraMCPTools(db_path=":memory:")

        mock_chunks = [
            {
                "id": "code:test.py:func",
                "type": "code",
                "content": "content",
                "file_path": "test.py",
                "line_range": [1, 1],
                "relevance_score": 0.85,
            },
        ]

        with patch.object(tools, "_retrieve_chunks", return_value=mock_chunks):
            result = tools.aurora_query("test query")
            response = json.loads(result)

            chunk = response["context"]["chunks"][0]
            assert "relevance_score" in chunk
            assert 0.0 <= chunk["relevance_score"] <= 1.0


# ==============================================================================
# Task 2.4: Confidence Handling Tests
# ==============================================================================


class TestConfidenceHandling:
    """Test retrieval confidence calculation and suggestions (FR-2.4, FR-2.5)."""

    def test_low_confidence_includes_suggestion(self):
        """Response with confidence < 0.5 must include suggestion (FR-2.5)."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Mock low-confidence results (low scores, few results)
        mock_chunks = [
            {
                "id": "code:test.py:func",
                "type": "code",
                "content": "content",
                "file_path": "test.py",
                "line_range": [1, 1],
                "relevance_score": 0.3,
            },
        ]

        with patch.object(tools, "_retrieve_chunks", return_value=mock_chunks):
            with patch.object(tools, "_calculate_retrieval_confidence", return_value=0.4):
                result = tools.aurora_query("test query")
                response = json.loads(result)

                assert response["assessment"]["retrieval_confidence"] < 0.5
                # Should include suggestion
                assert "suggestion" in response["assessment"]
                suggestion = response["assessment"]["suggestion"]
                assert "low confidence" in suggestion.lower() or "refine" in suggestion.lower()

    def test_high_confidence_no_suggestion(self):
        """Response with confidence >= 0.5 should NOT include suggestion."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Mock high-confidence results
        mock_chunks = [
            {
                "id": f"code:test{i}.py:func",
                "type": "code",
                "content": f"content {i}",
                "file_path": f"test{i}.py",
                "line_range": [1, 1],
                "relevance_score": 0.9,
            }
            for i in range(5)
        ]

        with patch.object(tools, "_retrieve_chunks", return_value=mock_chunks):
            with patch.object(tools, "_calculate_retrieval_confidence", return_value=0.85):
                result = tools.aurora_query("test query")
                response = json.loads(result)

                assert response["assessment"]["retrieval_confidence"] >= 0.5
                # Should NOT have suggestion field
                assert "suggestion" not in response["assessment"]

    def test_empty_results_zero_confidence(self):
        """Empty search results should have confidence of 0.0."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, "_retrieve_chunks", return_value=[]):
            result = tools.aurora_query("test query")
            response = json.loads(result)

            assert response["assessment"]["retrieval_confidence"] == 0.0
            # Should include suggestion for empty results
            assert "suggestion" in response["assessment"]


# ==============================================================================
# Task 2.5: Type Filtering Tests
# ==============================================================================


class TestTypeFiltering:
    """Test type_filter parameter functionality (FR-4)."""

    def test_filter_code_type_only(self):
        """type_filter='code' should only return code chunks."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Mock mixed type results, but filtering should only return code
        mock_all_chunks = [
            {
                "id": "code:test.py:func",
                "type": "code",
                "content": "code content",
                "file_path": "test.py",
                "line_range": [1, 1],
                "relevance_score": 0.9,
            },
            {
                "id": "reas:reasoning:1",
                "type": "reas",
                "content": "reasoning content",
                "file_path": None,
                "line_range": None,
                "relevance_score": 0.8,
            },
        ]

        with patch.object(tools, "_retrieve_chunks") as mock_retrieve:
            # Filter should be passed through and only code returned
            mock_retrieve.return_value = [c for c in mock_all_chunks if c["type"] == "code"]

            result = tools.aurora_query("test query", type_filter="code")
            response = json.loads(result)

            # Verify filtering was applied
            mock_retrieve.assert_called()
            call_kwargs = mock_retrieve.call_args[1]
            assert call_kwargs.get("type_filter") == "code"

            # Response should only have code chunks
            chunks = response["context"]["chunks"]
            assert all(chunk["type"] == "code" for chunk in chunks)

    def test_filter_reas_type_only(self):
        """type_filter='reas' should only return reasoning chunks."""
        tools = AuroraMCPTools(db_path=":memory:")

        mock_reas_chunks = [
            {
                "id": "reas:reasoning:1",
                "type": "reas",
                "content": "reasoning",
                "file_path": None,
                "line_range": None,
                "relevance_score": 0.85,
            },
        ]

        with patch.object(
            tools,
            "_retrieve_chunks",
            return_value=mock_reas_chunks,
        ) as mock_retrieve:
            result = tools.aurora_query("test query", type_filter="reas")
            response = json.loads(result)

            # Verify type_filter passed through
            call_kwargs = mock_retrieve.call_args[1]
            assert call_kwargs.get("type_filter") == "reas"

            chunks = response["context"]["chunks"]
            assert all(chunk["type"] == "reas" for chunk in chunks)

    def test_filter_know_type_only(self):
        """type_filter='know' should only return knowledge chunks."""
        tools = AuroraMCPTools(db_path=":memory:")

        mock_know_chunks = [
            {
                "id": "know:pref:auth",
                "type": "know",
                "content": "knowledge",
                "file_path": None,
                "line_range": None,
                "relevance_score": 0.8,
            },
        ]

        with patch.object(
            tools,
            "_retrieve_chunks",
            return_value=mock_know_chunks,
        ) as mock_retrieve:
            result = tools.aurora_query("test query", type_filter="know")
            response = json.loads(result)

            call_kwargs = mock_retrieve.call_args[1]
            assert call_kwargs.get("type_filter") == "know"

            chunks = response["context"]["chunks"]
            assert all(chunk["type"] == "know" for chunk in chunks)

    def test_no_filter_returns_all_types(self):
        """type_filter=None should return all memory types."""
        tools = AuroraMCPTools(db_path=":memory:")

        mock_mixed_chunks = [
            {
                "id": "code:test.py:func",
                "type": "code",
                "content": "code",
                "file_path": "test.py",
                "line_range": [1, 1],
                "relevance_score": 0.9,
            },
            {
                "id": "reas:reasoning:1",
                "type": "reas",
                "content": "reasoning",
                "file_path": None,
                "line_range": None,
                "relevance_score": 0.8,
            },
            {
                "id": "know:pref:auth",
                "type": "know",
                "content": "knowledge",
                "file_path": None,
                "line_range": None,
                "relevance_score": 0.7,
            },
        ]

        with patch.object(
            tools,
            "_retrieve_chunks",
            return_value=mock_mixed_chunks,
        ) as mock_retrieve:
            result = tools.aurora_query("test query", type_filter=None)
            response = json.loads(result)

            call_kwargs = mock_retrieve.call_args[1]
            assert call_kwargs.get("type_filter") is None

            chunks = response["context"]["chunks"]
            types_returned = set(chunk["type"] for chunk in chunks)
            # Should have multiple types
            assert len(types_returned) > 1


# ==============================================================================
# Task 2.6: Complexity Assessment Tests
# ==============================================================================


class TestComplexityAssessment:
    """Test heuristic complexity assessment (FR-2.6)."""

    def test_simple_query_low_complexity(self):
        """Simple, short query should have low complexity score."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, "_retrieve_chunks", return_value=[]):
            result = tools.aurora_query("What is X?")
            response = json.loads(result)

            complexity = response["assessment"]["complexity_score"]
            assert 0.0 <= complexity <= 1.0
            # Simple query should have lower complexity
            assert complexity < 0.5, f"Expected low complexity, got {complexity}"
            assert response["assessment"]["suggested_approach"] in ["simple", "direct"]

    def test_complex_query_high_complexity(self):
        """Complex query with multiple clauses should have high complexity."""
        tools = AuroraMCPTools(db_path=":memory:")

        complex_query = (
            "Analyze the authentication flow across multiple services, "
            "compare the error handling strategies, identify potential race "
            "conditions, and suggest architectural improvements for scalability"
        )

        with patch.object(tools, "_retrieve_chunks", return_value=[]):
            result = tools.aurora_query(complex_query)
            response = json.loads(result)

            complexity = response["assessment"]["complexity_score"]
            assert 0.0 <= complexity <= 1.0
            # Complex query should have higher complexity
            assert complexity > 0.6, f"Expected high complexity, got {complexity}"
            assert response["assessment"]["suggested_approach"] == "complex"

    def test_long_query_medium_complexity(self):
        """Long query with moderate complexity should score in middle range."""
        tools = AuroraMCPTools(db_path=":memory:")

        medium_query = (
            "Explain the implementation of the user authentication system "
            "and how it integrates with the session management module"
        )

        with patch.object(tools, "_retrieve_chunks", return_value=[]):
            result = tools.aurora_query(medium_query)
            response = json.loads(result)

            complexity = response["assessment"]["complexity_score"]
            assert 0.0 <= complexity <= 1.0
            # Should be somewhere in middle range
            assert 0.3 <= complexity <= 0.8, f"Expected medium complexity, got {complexity}"


# ==============================================================================
# Task 2.7: No API Key Required Tests
# ==============================================================================


class TestNoAPIKeyRequired:
    """Test that aurora_query works without API key (FR-1)."""

    def test_works_without_api_key_env(self):
        """aurora_query should work when ANTHROPIC_API_KEY env var is not set."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Explicitly unset API key
        with patch.dict("os.environ", {}, clear=True):
            # Ensure no ANTHROPIC_API_KEY in environment
            assert "ANTHROPIC_API_KEY" not in os.environ

            with patch.object(tools, "_retrieve_chunks", return_value=[]):
                result = tools.aurora_query("test query")
                response = json.loads(result)

                # Should NOT have APIKeyMissing error
                if "error" in response:
                    assert (
                        response["error"]["type"] != "APIKeyMissing"
                    ), "aurora_query should work without API key"

                # Should have successful response structure
                assert "context" in response or "error" not in response

    def test_works_without_config_api_key(self):
        """aurora_query should work when config.json has no API key."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Mock config without API key
        mock_config = {"memory": {"default_limit": 10}}

        with patch.object(tools, "_load_config", return_value=mock_config):
            with patch.dict("os.environ", {}, clear=True):
                with patch.object(tools, "_retrieve_chunks", return_value=[]):
                    result = tools.aurora_query("test query")
                    response = json.loads(result)

                    # Should NOT have APIKeyMissing error
                    if "error" in response:
                        assert response["error"]["type"] != "APIKeyMissing"

    def test_no_api_key_error_messages(self):
        """Response should never contain APIKeyMissing error type."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Test various scenarios, none should produce APIKeyMissing
        test_queries = [
            "simple query",
            "complex query with many words and clauses",
            "query with type filter",
        ]

        with patch.dict("os.environ", {}, clear=True):
            for query in test_queries:
                with patch.object(tools, "_retrieve_chunks", return_value=[]):
                    result = tools.aurora_query(query)
                    response = json.loads(result)

                    if "error" in response:
                        error_type = response["error"]["type"]
                        assert (
                            error_type != "APIKeyMissing"
                        ), f"Query '{query}' should not require API key, got error: {error_type}"
                        # Also check error message doesn't mention API key
                        error_msg = response["error"]["message"].lower()
                        assert (
                            "api" not in error_msg or "key" not in error_msg
                        ), f"Error message should not mention API key: {error_msg}"
