"""Unit tests for aurora_cli.execution QueryExecutor class.

Tests error handling, retry logic, and validation behavior.
IMPORTANT: These are UNIT tests - they use mocks, NOT subprocess.run().
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from aurora_cli.errors import APIError
from aurora_cli.query_executor import QueryExecutor


class TestExecuteDirectLLMValidation:
    """Test input validation for direct LLM execution."""

    def test_empty_query_raises_error(self) -> None:
        executor = QueryExecutor()
        with pytest.raises(ValueError, match="Query cannot be empty"):
            executor.execute_direct_llm(query="", api_key="sk-ant-test123")

    def test_empty_api_key_raises_error(self) -> None:
        executor = QueryExecutor()
        with pytest.raises(ValueError, match="API key is required"):
            executor.execute_direct_llm(query="What is Python?", api_key="")

    @patch("aurora_cli.query_executor.QueryExecutor._initialize_llm_client")
    @patch("aurora_cli.query_executor.QueryExecutor._call_llm_with_retry")
    def test_api_error_is_propagated(self, mock_call_llm: Mock, mock_init_llm: Mock) -> None:
        mock_init_llm.return_value = Mock()
        mock_call_llm.side_effect = APIError("API rate limit exceeded")

        executor = QueryExecutor()
        with pytest.raises(APIError, match="API rate limit exceeded"):
            executor.execute_direct_llm(query="Test", api_key="sk-ant-test123")

    @patch("aurora_cli.query_executor.QueryExecutor._initialize_llm_client")
    @patch("aurora_cli.query_executor.QueryExecutor._call_llm_with_retry")
    def test_generic_error_wrapped_as_api_error(self, mock_call_llm: Mock, mock_init_llm: Mock) -> None:
        mock_init_llm.return_value = Mock()
        mock_call_llm.side_effect = RuntimeError("Unexpected error")

        executor = QueryExecutor()
        with pytest.raises(APIError):
            executor.execute_direct_llm(query="Test", api_key="sk-ant-test123")


class TestExecuteAuroraValidation:
    """Test input validation and error wrapping for AURORA SOAR execution."""

    def test_empty_query_raises_error(self) -> None:
        executor = QueryExecutor()
        with pytest.raises(ValueError, match="Query cannot be empty"):
            executor.execute_aurora(query="", api_key="sk-ant-test123", memory_store=Mock())

    def test_none_store_raises_error(self) -> None:
        executor = QueryExecutor()
        with pytest.raises(ValueError, match="Memory store is required"):
            executor.execute_aurora(query="Test", api_key="sk-ant-test123", memory_store=None)  # type: ignore[arg-type]

    @patch("aurora_cli.query_executor.QueryExecutor._initialize_orchestrator")
    def test_orchestrator_error_wrapped_as_api_error(self, mock_init_orch: Mock) -> None:
        mock_orchestrator = Mock()
        mock_init_orch.return_value = mock_orchestrator
        mock_orchestrator.execute.side_effect = RuntimeError("Orchestrator failed")

        executor = QueryExecutor()
        with pytest.raises(APIError):
            executor.execute_aurora(query="Test", api_key="sk-ant-test123", memory_store=Mock())


class TestGetMemoryContextErrorHandling:
    """Test memory context retrieval error resilience."""

    def test_search_error_returns_empty_string(self) -> None:
        mock_store = Mock()
        mock_store.search_keyword.side_effect = RuntimeError("Search failed")

        executor = QueryExecutor()
        context = executor._get_memory_context(mock_store, query="test")
        assert context == ""

    def test_no_results_returns_empty_string(self) -> None:
        mock_store = Mock()
        mock_store.search_keyword.return_value = []

        executor = QueryExecutor()
        context = executor._get_memory_context(mock_store, query="nonexistent")
        assert context == ""


class TestCallLLMWithRetry:
    """Test LLM retry logic for rate limits, server errors, and backoff."""

    @patch("aurora_cli.execution.time.sleep")
    def test_retries_on_rate_limit(self, mock_sleep: Mock) -> None:
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "Success after retry"
        mock_llm.generate.side_effect = [
            Exception("Error 429: rate limit exceeded"),
            mock_response,
        ]

        executor = QueryExecutor()
        result = executor._call_llm_with_retry(
            llm=mock_llm, prompt="Test", model="claude-sonnet-4-20250514",
            max_tokens=100, temperature=0.7,
        )

        assert result == mock_response
        assert mock_llm.generate.call_count == 2
        mock_sleep.assert_called_once()

    @patch("aurora_cli.execution.time.sleep")
    def test_retries_on_server_error(self, mock_sleep: Mock) -> None:
        mock_llm = Mock()
        mock_response = Mock()
        mock_llm.generate.side_effect = [
            Exception("500 internal server error"),
            mock_response,
        ]

        executor = QueryExecutor()
        executor._call_llm_with_retry(
            llm=mock_llm, prompt="Test", model="claude-sonnet-4-20250514",
            max_tokens=100, temperature=0.7,
        )

        assert mock_llm.generate.call_count == 2
        mock_sleep.assert_called_once()

    @patch("aurora_cli.execution.time.sleep")
    def test_fails_after_max_retries(self, mock_sleep: Mock) -> None:
        mock_llm = Mock()
        mock_llm.generate.side_effect = Exception("429 rate limit exceeded")

        executor = QueryExecutor()
        with pytest.raises(APIError):
            executor._call_llm_with_retry(
                llm=mock_llm, prompt="Test", model="claude-sonnet-4-20250514",
                max_tokens=100, temperature=0.7, max_retries=3,
            )

        assert mock_llm.generate.call_count == 3
        assert mock_sleep.call_count == 2  # Sleep between attempts, not after last

    @patch("aurora_cli.execution.time.sleep")
    def test_does_not_retry_non_retryable_errors(self, mock_sleep: Mock) -> None:
        mock_llm = Mock()
        mock_llm.generate.side_effect = Exception("401 Unauthorized")

        executor = QueryExecutor()
        with pytest.raises(APIError):
            executor._call_llm_with_retry(
                llm=mock_llm, prompt="Test", model="claude-sonnet-4-20250514",
                max_tokens=100, temperature=0.7,
            )

        assert mock_llm.generate.call_count == 1
        mock_sleep.assert_not_called()

    @patch("aurora_cli.execution.time.sleep")
    def test_uses_exponential_backoff(self, mock_sleep: Mock) -> None:
        mock_llm = Mock()
        mock_response = Mock()
        mock_llm.generate.side_effect = [
            Exception("503 service unavailable"),
            Exception("503 service unavailable"),
            mock_response,
        ]

        executor = QueryExecutor()
        executor._call_llm_with_retry(
            llm=mock_llm, prompt="Test", model="claude-sonnet-4-20250514",
            max_tokens=100, temperature=0.7,
        )

        assert mock_sleep.call_count == 2
        first_delay = mock_sleep.call_args_list[0][0][0]
        second_delay = mock_sleep.call_args_list[1][0][0]
        assert second_delay > first_delay
        assert second_delay < first_delay * 3  # Allow for jitter


class TestInteractiveModePassthrough:
    """Test that interactive_mode is passed through to the orchestrator."""

    @patch("aurora_soar.orchestrator.SOAROrchestrator")
    @patch("aurora_soar.agent_registry.AgentRegistry")
    @patch("aurora_core.config.loader.Config")
    @patch("aurora_cli.execution.AnthropicClient")
    def test_interactive_mode_forwarded_to_orchestrator(
        self,
        mock_client_class: Mock,
        mock_config_class: Mock,
        mock_registry_class: Mock,
        mock_orchestrator_class: Mock,
    ) -> None:
        mock_client_class.return_value = Mock()
        mock_config_class.return_value = Mock()
        mock_registry_class.return_value = Mock()

        mock_orchestrator = Mock()
        mock_orchestrator.execute.return_value = {"answer": "Test response", "cost_usd": 0.01}
        mock_orchestrator_class.return_value = mock_orchestrator

        for mode in (True, False):
            executor = QueryExecutor(config={}, interactive_mode=mode)
            executor.execute_aurora(
                query="What is Python?", api_key="test-key",
                memory_store=Mock(), verbose=False,
            )
            call_kwargs = mock_orchestrator_class.call_args[1]
            assert call_kwargs["interactive_mode"] is mode
