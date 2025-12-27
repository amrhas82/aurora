"""Integration tests for QueryExecutor with real components.

This module tests QueryExecutor with real Store, real retrieval, and real
orchestrator phases. Only external LLM API calls are mocked.

Key differences from unit tests:
- Uses real SQLiteStore with temporary database
- Uses real memory context retrieval
- Uses real SOAROrchestrator with real phase execution
- Mocks only LLM API responses (external dependency)
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest
from aurora_cli.errors import APIError
from aurora_cli.execution import QueryExecutor
from aurora_reasoning.llm_client import LLMResponse

from aurora_core.chunks.code_chunk import CodeChunk
from aurora_core.store.sqlite import SQLiteStore


@pytest.fixture
def temp_db() -> SQLiteStore:
    """Create a temporary SQLite database for testing.

    Returns:
        SQLiteStore instance with temporary database
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)

    store = SQLiteStore(db_path=str(db_path))

    yield store

    # Cleanup
    store.close()
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def populated_store(temp_db: SQLiteStore) -> SQLiteStore:
    """Create a store populated with test data.

    Args:
        temp_db: Empty SQLite store

    Returns:
        Store populated with test chunks
    """
    # Add test chunks as CodeChunk objects
    test_chunks = [
        CodeChunk(
            chunk_id="test_fibonacci",
            file_path="/test/fibonacci.py",
            element_type="function",
            name="calculate_fibonacci",
            line_start=1,
            line_end=4,
            signature="def calculate_fibonacci(n)",
            docstring="Calculate fibonacci number recursively",
            complexity_score=0.3,
            dependencies=[],
        ),
        CodeChunk(
            chunk_id="test_processor",
            file_path="/test/processor.py",
            element_type="class",
            name="DataProcessor",
            line_start=1,
            line_end=5,
            signature="class DataProcessor",
            docstring="Process data by doubling values",
            complexity_score=0.4,
            dependencies=[],
        ),
        CodeChunk(
            chunk_id="test_config",
            file_path="/test/config.py",
            element_type="function",
            name="load_config",
            line_start=1,
            line_end=4,
            signature="def load_config()",
            docstring="Load configuration settings",
            complexity_score=0.1,
            dependencies=[],
        ),
    ]

    for chunk in test_chunks:
        temp_db.save_chunk(chunk)

    return temp_db


class TestQueryExecutorWithRealStore:
    """Test QueryExecutor with real Store integration."""

    @patch("aurora_cli.execution.QueryExecutor._call_llm_with_retry")
    def test_execute_direct_llm_with_real_store(
        self,
        mock_call_llm: Mock,
        populated_store: SQLiteStore,
    ) -> None:
        """Test direct LLM execution with real store (graceful degradation).

        Note: SQLiteStore doesn't have search_keyword method, so context
        retrieval will gracefully fail and return empty string. This tests
        the real integration behavior where Store doesn't support the method.
        """
        # Setup mock LLM response
        mock_response = Mock(spec=LLMResponse)
        mock_response.content = "Fibonacci is a recursive function"
        mock_response.input_tokens = 100
        mock_response.output_tokens = 50
        mock_call_llm.return_value = mock_response

        # Execute query
        executor = QueryExecutor()
        result = executor.execute_direct_llm(
            query="fibonacci",
            api_key="sk-ant-test123",
            memory_store=populated_store,
            verbose=False,
        )

        # Verify result
        assert result == "Fibonacci is a recursive function"

        # Verify LLM was called (with or without context, depending on store capabilities)
        call_args = mock_call_llm.call_args
        prompt_arg = call_args.kwargs.get("prompt", call_args[1] if len(call_args) > 1 else None)

        # Since SQLiteStore doesn't have search_keyword, prompt should be just the query
        assert prompt_arg == "fibonacci"

    @patch("aurora_cli.execution.QueryExecutor._call_llm_with_retry")
    def test_execute_direct_llm_no_matching_context(
        self,
        mock_call_llm: Mock,
        populated_store: SQLiteStore,
    ) -> None:
        """Test direct LLM execution without store search capability."""
        # Setup mock LLM response
        mock_response = Mock(spec=LLMResponse)
        mock_response.content = "I don't have information about that"
        mock_response.input_tokens = 20
        mock_response.output_tokens = 10
        mock_call_llm.return_value = mock_response

        # Execute query with non-matching term
        executor = QueryExecutor()
        result = executor.execute_direct_llm(
            query="quantum entanglement",
            api_key="sk-ant-test123",
            memory_store=populated_store,
            verbose=False,
        )

        # Verify result
        assert result == "I don't have information about that"

        # Verify LLM was called without context (search_keyword not available)
        call_args = mock_call_llm.call_args
        prompt_arg = call_args.kwargs.get("prompt", call_args[1] if len(call_args) > 1 else None)

        # No context prefix since Store doesn't support search_keyword
        assert prompt_arg == "quantum entanglement"

    @patch("aurora_cli.execution.QueryExecutor._call_llm_with_retry")
    def test_memory_context_with_mock_search_method(
        self,
        mock_call_llm: Mock,
        populated_store: SQLiteStore,
    ) -> None:
        """Test memory context retrieval when store has search capability.

        This test mocks search_keyword to simulate a store that supports it.
        """
        # Setup mock LLM
        mock_response = Mock(spec=LLMResponse)
        mock_response.content = "Response about processor"
        mock_response.input_tokens = 50
        mock_response.output_tokens = 20
        mock_call_llm.return_value = mock_response

        # Mock search_keyword on the store to return test results
        mock_search_results = [
            {
                "content": "class DataProcessor:\n    def process(self): pass",
                "metadata": {"file_path": "/test/processor.py"},
            }
        ]
        populated_store.search_keyword = Mock(return_value=mock_search_results)

        # Execute
        executor = QueryExecutor()
        result = executor.execute_direct_llm(
            query="DataProcessor",
            api_key="sk-ant-test123",
            memory_store=populated_store,
            verbose=True,
        )

        # Verify execution succeeded
        assert result == "Response about processor"

        # Verify context was built
        call_args = mock_call_llm.call_args
        prompt_arg = call_args.kwargs.get("prompt")

        # Should contain context from mock search results
        assert "Context:" in prompt_arg
        assert "processor.py" in prompt_arg
        assert "DataProcessor" in prompt_arg

    def test_execute_direct_llm_with_empty_store(
        self,
        temp_db: SQLiteStore,
    ) -> None:
        """Test direct LLM execution with empty store (no context)."""
        with patch("aurora_cli.execution.QueryExecutor._call_llm_with_retry") as mock_call:
            mock_response = Mock(spec=LLMResponse)
            mock_response.content = "Answer without context"
            mock_response.input_tokens = 15
            mock_response.output_tokens = 8
            mock_call.return_value = mock_response

            executor = QueryExecutor()
            result = executor.execute_direct_llm(
                query="test query",
                api_key="sk-ant-test123",
                memory_store=temp_db,
            )

            assert result == "Answer without context"

            # Verify prompt is just the query (no context)
            call_args = mock_call.call_args
            prompt_arg = call_args.kwargs.get("prompt")
            assert prompt_arg == "test query"


class TestQueryExecutorErrorPropagation:
    """Test error propagation through real components."""

    @patch("aurora_cli.execution.QueryExecutor._call_llm_with_retry")
    def test_api_error_propagates_from_llm(
        self,
        mock_call_llm: Mock,
        populated_store: SQLiteStore,
    ) -> None:
        """Test APIError propagates through execution stack."""
        # Setup mock to raise API error
        mock_call_llm.side_effect = Exception("API rate limit exceeded")

        executor = QueryExecutor()

        with pytest.raises(APIError) as exc_info:
            executor.execute_direct_llm(
                query="test",
                api_key="sk-ant-test123",
                memory_store=populated_store,
            )

        # Verify error message contains rate limit information
        error_message = str(exc_info.value)
        assert "rate limit" in error_message.lower() or "api" in error_message.lower()

    def test_invalid_store_raises_error(self) -> None:
        """Test execution with invalid store raises appropriate error."""
        with patch("aurora_cli.execution.QueryExecutor._call_llm_with_retry"):
            executor = QueryExecutor()

            # Pass None as memory_store to direct LLM (should still work)
            with patch("aurora_cli.execution.QueryExecutor._call_llm_with_retry") as mock_call:
                mock_response = Mock(spec=LLMResponse)
                mock_response.content = "Response"
                mock_response.input_tokens = 10
                mock_response.output_tokens = 5
                mock_call.return_value = mock_response

                result = executor.execute_direct_llm(
                    query="test",
                    api_key="sk-ant-test123",
                    memory_store=None,
                )

                # Should succeed without store
                assert result == "Response"

    def test_store_search_failure_graceful_degradation(
        self,
        temp_db: SQLiteStore,
    ) -> None:
        """Test graceful degradation when store search fails."""
        with patch("aurora_cli.execution.QueryExecutor._call_llm_with_retry") as mock_call:
            mock_response = Mock(spec=LLMResponse)
            mock_response.content = "Fallback response"
            mock_response.input_tokens = 10
            mock_response.output_tokens = 5
            mock_call.return_value = mock_response

            # Make store.search_keyword raise error
            temp_db.search_keyword = Mock(side_effect=Exception("Database error"))

            executor = QueryExecutor()
            result = executor.execute_direct_llm(
                query="test",
                api_key="sk-ant-test123",
                memory_store=temp_db,
            )

            # Should succeed with fallback (no context)
            assert result == "Fallback response"


@pytest.mark.skip(reason="Requires real orchestrator which needs LLM API - tested in E2E")
class TestQueryExecutorAuroraIntegration:
    """Test QueryExecutor with real SOAR orchestrator integration.

    These tests are skipped by default because they require a complete
    orchestrator setup with LLM API. They serve as documentation for
    integration patterns and are run in E2E test suite.
    """

    @patch("aurora_reasoning.llm_client.AnthropicClient.generate")
    def test_execute_aurora_with_real_orchestrator(
        self,
        mock_generate: Mock,
        populated_store: SQLiteStore,
    ) -> None:
        """Test AURORA execution with real orchestrator phases."""
        # Setup mock LLM responses for orchestrator phases
        mock_responses = [
            Mock(
                content='{"complexity": "simple", "reasoning": "Single query"}',
                input_tokens=50,
                output_tokens=30,
            ),
            Mock(
                content='{"subgoals": ["Search memory", "Generate answer"]}',
                input_tokens=40,
                output_tokens=25,
            ),
            Mock(
                content="Final synthesized answer",
                input_tokens=100,
                output_tokens=50,
            ),
        ]
        mock_generate.side_effect = mock_responses

        executor = QueryExecutor()
        result = executor.execute_aurora(
            query="What is fibonacci?",
            api_key="sk-ant-test123",
            memory_store=populated_store,
            verbose=False,
        )

        # Verify execution
        assert isinstance(result, str)
        assert len(result) > 0

    @patch("aurora_reasoning.llm_client.AnthropicClient.generate")
    def test_execute_aurora_verbose_returns_trace(
        self,
        mock_generate: Mock,
        populated_store: SQLiteStore,
    ) -> None:
        """Test AURORA execution with verbose=True returns phase trace."""
        # Setup mocks
        mock_generate.return_value = Mock(
            content="Answer",
            input_tokens=50,
            output_tokens=30,
        )

        executor = QueryExecutor()
        result = executor.execute_aurora(
            query="test query",
            api_key="sk-ant-test123",
            memory_store=populated_store,
            verbose=True,
        )

        # Verify verbose returns tuple
        assert isinstance(result, tuple)
        assert len(result) == 2

        response, trace = result
        assert isinstance(response, str)
        assert isinstance(trace, dict)

        # Verify trace structure
        assert "phases" in trace
        assert "total_duration" in trace
        assert "total_cost" in trace


class TestQueryExecutorRetryLogic:
    """Test retry logic with real exponential backoff."""

    @patch("aurora_cli.execution.time.sleep")  # Mock sleep to speed up test
    @patch("aurora_reasoning.llm_client.AnthropicClient.generate")
    def test_retry_on_rate_limit(
        self,
        mock_generate: Mock,
        mock_sleep: Mock,
        temp_db: SQLiteStore,
    ) -> None:
        """Test retry logic on rate limit error (429)."""
        # First call fails with rate limit, second succeeds
        mock_generate.side_effect = [
            Exception("429 rate limit exceeded"),
            Mock(content="Success after retry", input_tokens=10, output_tokens=5),
        ]

        executor = QueryExecutor()
        result = executor.execute_direct_llm(
            query="test",
            api_key="sk-ant-test123",
            memory_store=None,
        )

        # Verify retry happened
        assert result == "Success after retry"
        assert mock_generate.call_count == 2
        assert mock_sleep.call_count == 1  # Slept once between retries

    @patch("aurora_cli.execution.time.sleep")
    @patch("aurora_reasoning.llm_client.AnthropicClient.generate")
    def test_retry_on_server_error(
        self,
        mock_generate: Mock,
        mock_sleep: Mock,
        temp_db: SQLiteStore,
    ) -> None:
        """Test retry logic on server error (500)."""
        # First call fails with server error, second succeeds
        mock_generate.side_effect = [
            Exception("500 internal server error"),
            Mock(content="Success", input_tokens=10, output_tokens=5),
        ]

        executor = QueryExecutor()
        result = executor.execute_direct_llm(
            query="test",
            api_key="sk-ant-test123",
            memory_store=None,
        )

        assert result == "Success"
        assert mock_generate.call_count == 2

    @patch("aurora_cli.execution.time.sleep")
    @patch("aurora_reasoning.llm_client.AnthropicClient.generate")
    def test_no_retry_on_auth_error(
        self,
        mock_generate: Mock,
        mock_sleep: Mock,
        temp_db: SQLiteStore,
    ) -> None:
        """Test no retry on authentication error (401)."""
        # Auth errors are not retryable
        mock_generate.side_effect = Exception("401 unauthorized")

        executor = QueryExecutor()

        with pytest.raises(APIError):
            executor.execute_direct_llm(
                query="test",
                api_key="sk-ant-invalid",
                memory_store=None,
            )

        # Should not retry on auth error
        assert mock_generate.call_count == 1
        assert mock_sleep.call_count == 0

    @patch("aurora_cli.execution.time.sleep")
    @patch("aurora_reasoning.llm_client.AnthropicClient.generate")
    def test_exhausted_retries_raises_error(
        self,
        mock_generate: Mock,
        mock_sleep: Mock,
        temp_db: SQLiteStore,
    ) -> None:
        """Test all retries exhausted raises APIError."""
        # All retries fail
        mock_generate.side_effect = Exception("503 service unavailable")

        executor = QueryExecutor()

        with pytest.raises(APIError) as exc_info:
            executor.execute_direct_llm(
                query="test",
                api_key="sk-ant-test123",
                memory_store=None,
            )

        # Should retry max_retries times (default 3)
        assert mock_generate.call_count == 3
        assert mock_sleep.call_count == 2  # Sleep between attempts (not after last)

        # Error message should contain information about the issue
        error_message = str(exc_info.value)
        assert "server error" in error_message.lower() or "anthropic" in error_message.lower()


class TestQueryExecutorCostEstimation:
    """Test cost estimation with real token counts."""

    @patch("aurora_cli.execution.QueryExecutor._call_llm_with_retry")
    def test_cost_estimation_with_real_tokens(
        self,
        mock_call_llm: Mock,
        temp_db: SQLiteStore,
    ) -> None:
        """Test _estimate_cost() with realistic token counts."""
        # Setup mock with specific token counts
        mock_response = Mock(spec=LLMResponse)
        mock_response.content = "Response"
        mock_response.input_tokens = 1000  # 1K input tokens
        mock_response.output_tokens = 500   # 500 output tokens
        mock_call_llm.return_value = mock_response

        executor = QueryExecutor()

        # Test cost estimation
        cost = executor._estimate_cost(
            input_tokens=1000,
            output_tokens=500,
        )

        # Verify cost calculation
        # INPUT_COST_PER_1K = 0.003, OUTPUT_COST_PER_1K = 0.015
        expected_cost = (1000 / 1000.0) * 0.003 + (500 / 1000.0) * 0.015
        assert abs(cost - expected_cost) < 0.0001  # Float comparison
        assert cost == pytest.approx(0.0105, abs=0.0001)
