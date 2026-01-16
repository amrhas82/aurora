"""Unit tests for aurora_cli.execution QueryExecutor class.

This module tests the QueryExecutor class for query execution logic
using direct function calls with mocking.
IMPORTANT: These are UNIT tests - they use mocks, NOT subprocess.run().
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from aurora_cli.errors import APIError
from aurora_cli.query_executor import QueryExecutor


class TestQueryExecutorInit:
    """Test QueryExecutor initialization."""

    def test_init_with_no_config(self) -> None:
        """Test QueryExecutor.__init__() with no config creates empty dict."""
        executor = QueryExecutor()

        assert executor.config == {}
        assert executor.error_handler is not None

    def test_init_with_config_dict(self) -> None:
        """Test QueryExecutor.__init__() with config dictionary."""
        config = {
            "model": "claude-opus-4-20250514",
            "temperature": 0.9,
            "max_tokens": 1000,
        }
        executor = QueryExecutor(config=config)

        assert executor.config == config
        assert executor.config["model"] == "claude-opus-4-20250514"
        assert executor.config["temperature"] == 0.9
        assert executor.config["max_tokens"] == 1000

    def test_init_with_api_key_in_config(self) -> None:
        """Test QueryExecutor.__init__() with API key in config."""
        config = {"api_key": "sk-ant-test123"}
        executor = QueryExecutor(config=config)

        assert executor.config["api_key"] == "sk-ant-test123"


class TestExecuteDirectLLM:
    """Test direct LLM execution method."""

    @patch("aurora_cli.query_executor.QueryExecutor._initialize_llm_client")
    @patch("aurora_cli.query_executor.QueryExecutor._call_llm_with_retry")
    def test_execute_direct_llm_with_valid_query(
        self, mock_call_llm: Mock, mock_init_llm: Mock
    ) -> None:
        """Test execute_direct_llm() with valid query and API key."""
        # Setup mocks
        mock_llm = Mock()
        mock_init_llm.return_value = mock_llm

        mock_response = Mock()
        mock_response.content = "This is the LLM response"
        mock_response.input_tokens = 10
        mock_response.output_tokens = 20
        mock_call_llm.return_value = mock_response

        # Execute
        executor = QueryExecutor()
        result = executor.execute_direct_llm(query="What is Python?", api_key="sk-ant-test123")

        # Verify
        assert result == "This is the LLM response"
        mock_init_llm.assert_called_once_with("sk-ant-test123")
        mock_call_llm.assert_called_once()

    @patch("aurora_cli.query_executor.QueryExecutor._initialize_llm_client")
    @patch("aurora_cli.query_executor.QueryExecutor._call_llm_with_retry")
    def test_execute_direct_llm_with_memory_context(
        self, mock_call_llm: Mock, mock_init_llm: Mock
    ) -> None:
        """Test execute_direct_llm() includes memory context when store provided."""
        # Setup mocks
        mock_llm = Mock()
        mock_init_llm.return_value = mock_llm

        mock_response = Mock()
        mock_response.content = "Response with context"
        mock_response.input_tokens = 50
        mock_response.output_tokens = 30
        mock_call_llm.return_value = mock_response

        # Mock memory store with search results
        mock_store = Mock()
        mock_store.search_keyword.return_value = [
            {
                "content": "def hello(): pass",
                "metadata": {"file_path": "test.py"},
            }
        ]

        # Execute
        executor = QueryExecutor()
        result = executor.execute_direct_llm(
            query="What is hello?",
            api_key="sk-ant-test123",
            memory_store=mock_store,
        )

        # Verify
        assert result == "Response with context"
        mock_store.search_keyword.assert_called_once_with("What is hello?", limit=3)

        # Verify prompt includes context
        call_args = mock_call_llm.call_args[1]
        assert "Context:" in call_args["prompt"]
        assert "test.py" in call_args["prompt"]
        assert "def hello(): pass" in call_args["prompt"]

    def test_execute_direct_llm_with_empty_query_raises_error(self) -> None:
        """Test execute_direct_llm() with empty query raises ValueError."""
        executor = QueryExecutor()

        with pytest.raises(ValueError, match="Query cannot be empty"):
            executor.execute_direct_llm(query="", api_key="sk-ant-test123")

    def test_execute_direct_llm_with_whitespace_query_raises_error(self) -> None:
        """Test execute_direct_llm() with whitespace-only query raises ValueError."""
        executor = QueryExecutor()

        with pytest.raises(ValueError, match="Query cannot be empty"):
            executor.execute_direct_llm(query="   \n\t  ", api_key="sk-ant-test123")

    def test_execute_direct_llm_with_empty_api_key_raises_error(self) -> None:
        """Test execute_direct_llm() with empty API key raises ValueError."""
        executor = QueryExecutor()

        with pytest.raises(ValueError, match="API key is required"):
            executor.execute_direct_llm(query="What is Python?", api_key="")

    def test_execute_direct_llm_with_whitespace_api_key_raises_error(self) -> None:
        """Test execute_direct_llm() with whitespace API key raises ValueError."""
        executor = QueryExecutor()

        with pytest.raises(ValueError, match="API key is required"):
            executor.execute_direct_llm(query="What is Python?", api_key="  \n  ")

    @patch("aurora_cli.query_executor.QueryExecutor._initialize_llm_client")
    @patch("aurora_cli.query_executor.QueryExecutor._call_llm_with_retry")
    def test_execute_direct_llm_with_verbose_logging(
        self, mock_call_llm: Mock, mock_init_llm: Mock
    ) -> None:
        """Test execute_direct_llm() with verbose=True logs detailed info."""
        # Setup mocks
        mock_llm = Mock()
        mock_init_llm.return_value = mock_llm

        mock_response = Mock()
        mock_response.content = "Verbose response"
        mock_response.input_tokens = 100
        mock_response.output_tokens = 50
        mock_call_llm.return_value = mock_response

        # Execute with verbose
        executor = QueryExecutor()
        with patch("aurora_cli.execution.logger") as mock_logger:
            executor.execute_direct_llm(query="Test query", api_key="sk-ant-test123", verbose=True)

            # Verify verbose logging calls
            assert mock_logger.info.call_count >= 1

    @patch("aurora_cli.query_executor.QueryExecutor._initialize_llm_client")
    @patch("aurora_cli.query_executor.QueryExecutor._call_llm_with_retry")
    def test_execute_direct_llm_uses_config_params(
        self, mock_call_llm: Mock, mock_init_llm: Mock
    ) -> None:
        """Test execute_direct_llm() uses config parameters for LLM call."""
        # Setup mocks
        mock_llm = Mock()
        mock_init_llm.return_value = mock_llm

        mock_response = Mock()
        mock_response.content = "Response"
        mock_response.input_tokens = 10
        mock_response.output_tokens = 20
        mock_call_llm.return_value = mock_response

        # Execute with custom config
        config = {
            "model": "claude-opus-4-20250514",
            "temperature": 0.9,
            "max_tokens": 2000,
        }
        executor = QueryExecutor(config=config)
        executor.execute_direct_llm(query="Test", api_key="sk-ant-test123")

        # Verify LLM was called with config params
        call_args = mock_call_llm.call_args[1]
        assert call_args["model"] == "claude-opus-4-20250514"
        assert call_args["temperature"] == 0.9
        assert call_args["max_tokens"] == 2000

    @patch("aurora_cli.query_executor.QueryExecutor._initialize_llm_client")
    @patch("aurora_cli.query_executor.QueryExecutor._call_llm_with_retry")
    def test_execute_direct_llm_api_error_is_propagated(
        self, mock_call_llm: Mock, mock_init_llm: Mock
    ) -> None:
        """Test execute_direct_llm() propagates APIError from LLM client."""
        # Setup mocks
        mock_llm = Mock()
        mock_init_llm.return_value = mock_llm

        # Simulate API error
        mock_call_llm.side_effect = APIError("API rate limit exceeded")

        # Execute and verify error
        executor = QueryExecutor()
        with pytest.raises(APIError, match="API rate limit exceeded"):
            executor.execute_direct_llm(query="Test", api_key="sk-ant-test123")

    @patch("aurora_cli.query_executor.QueryExecutor._initialize_llm_client")
    @patch("aurora_cli.query_executor.QueryExecutor._call_llm_with_retry")
    def test_execute_direct_llm_generic_error_wrapped_as_api_error(
        self, mock_call_llm: Mock, mock_init_llm: Mock
    ) -> None:
        """Test execute_direct_llm() wraps generic exceptions as APIError."""
        # Setup mocks
        mock_llm = Mock()
        mock_init_llm.return_value = mock_llm

        # Simulate generic error
        mock_call_llm.side_effect = RuntimeError("Unexpected error")

        # Execute and verify error is wrapped
        executor = QueryExecutor()
        with pytest.raises(APIError):
            executor.execute_direct_llm(query="Test", api_key="sk-ant-test123")


class TestExecuteAurora:
    """Test AURORA SOAR pipeline execution method."""

    @patch("aurora_cli.query_executor.QueryExecutor._initialize_orchestrator")
    def test_execute_aurora_with_valid_query(self, mock_init_orch: Mock) -> None:
        """Test execute_aurora() with valid query executes orchestrator."""
        # Setup mocks
        mock_orchestrator = Mock()
        mock_init_orch.return_value = mock_orchestrator

        mock_orchestrator.execute.return_value = {
            "answer": "This is the SOAR response",
            "cost_usd": 0.05,
            "confidence": 0.95,
        }

        mock_store = Mock()

        # Execute
        executor = QueryExecutor()
        result = executor.execute_aurora(
            query="Complex query", api_key="sk-ant-test123", memory_store=mock_store
        )

        # Verify
        assert result == "This is the SOAR response"
        mock_init_orch.assert_called_once_with("sk-ant-test123", mock_store)
        mock_orchestrator.execute.assert_called_once()

    @patch("aurora_cli.query_executor.QueryExecutor._initialize_orchestrator")
    def test_execute_aurora_with_verbose_returns_trace(self, mock_init_orch: Mock) -> None:
        """Test execute_aurora() with verbose=True returns response and trace."""
        # Setup mocks
        mock_orchestrator = Mock()
        mock_init_orch.return_value = mock_orchestrator

        mock_orchestrator.execute.return_value = {
            "answer": "SOAR response",
            "cost_usd": 0.10,
            "confidence": 0.85,
            "reasoning_trace": {
                "assess": {"duration_ms": 100, "complexity": "medium"},
                "retrieve": {"duration_ms": 200, "chunks_retrieved": 5},
            },
            "metadata": {"version": "0.2.0"},
        }

        mock_store = Mock()

        # Execute with verbose
        executor = QueryExecutor()
        response, trace = executor.execute_aurora(
            query="Complex query",
            api_key="sk-ant-test123",
            memory_store=mock_store,
            verbose=True,
        )

        # Verify response
        assert response == "SOAR response"

        # Verify trace structure
        assert isinstance(trace, dict)
        assert "phases" in trace
        assert "total_duration" in trace
        assert "total_cost" in trace
        assert trace["total_cost"] == 0.10
        assert trace["confidence"] == 0.85

    def test_execute_aurora_with_empty_query_raises_error(self) -> None:
        """Test execute_aurora() with empty query raises ValueError."""
        executor = QueryExecutor()
        mock_store = Mock()

        with pytest.raises(ValueError, match="Query cannot be empty"):
            executor.execute_aurora(query="", api_key="sk-ant-test123", memory_store=mock_store)

    def test_execute_aurora_with_none_store_raises_error(self) -> None:
        """Test execute_aurora() with None memory_store raises ValueError."""
        executor = QueryExecutor()

        with pytest.raises(ValueError, match="Memory store is required"):
            executor.execute_aurora(
                query="Test query",
                api_key="sk-ant-test123",
                memory_store=None,  # type: ignore[arg-type]
            )

    @patch("aurora_cli.query_executor.QueryExecutor._initialize_orchestrator")
    def test_execute_aurora_orchestrator_error_wrapped(self, mock_init_orch: Mock) -> None:
        """Test execute_aurora() wraps orchestrator errors as APIError."""
        # Setup mock to raise error
        mock_orchestrator = Mock()
        mock_init_orch.return_value = mock_orchestrator
        mock_orchestrator.execute.side_effect = RuntimeError("Orchestrator failed")

        mock_store = Mock()

        # Execute and verify error
        executor = QueryExecutor()
        with pytest.raises(APIError):
            executor.execute_aurora(query="Test", api_key="sk-ant-test123", memory_store=mock_store)


class TestInitializeLLMClient:
    """Test LLM client initialization."""

    @patch("aurora_cli.execution.AnthropicClient")
    def test_initialize_llm_client_creates_anthropic_client(
        self, mock_anthropic_class: Mock
    ) -> None:
        """Test _initialize_llm_client() creates AnthropicClient with API key."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        executor = QueryExecutor()
        result = executor._initialize_llm_client(api_key="sk-ant-test123")

        # Verify client was created with correct parameters
        mock_anthropic_class.assert_called_once_with(
            api_key="sk-ant-test123", default_model="claude-sonnet-4-20250514"
        )
        assert result == mock_client

    @patch("aurora_cli.execution.AnthropicClient")
    def test_initialize_llm_client_uses_config_model(self, mock_anthropic_class: Mock) -> None:
        """Test _initialize_llm_client() uses model from config."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        config = {"model": "claude-opus-4-20250514"}
        executor = QueryExecutor(config=config)
        executor._initialize_llm_client(api_key="sk-ant-test123")

        # Verify client was created with custom model
        mock_anthropic_class.assert_called_once_with(
            api_key="sk-ant-test123", default_model="claude-opus-4-20250514"
        )


class TestInitializeOrchestrator:
    """Test SOAR orchestrator initialization."""

    @patch("aurora_core.config.loader.Config")
    @patch("aurora_soar.orchestrator.SOAROrchestrator")
    @patch("aurora_soar.agent_registry.AgentRegistry")
    @patch("aurora_cli.query_executor.QueryExecutor._initialize_llm_client")
    def test_initialize_orchestrator_creates_soar_instance(
        self,
        mock_init_llm: Mock,
        mock_registry_class: Mock,
        mock_soar_class: Mock,
        mock_config_class: Mock,
    ) -> None:
        """Test _initialize_orchestrator() creates SOAROrchestrator with dependencies."""
        # Setup mocks
        mock_llm = Mock()
        mock_init_llm.return_value = mock_llm

        mock_config = Mock()
        mock_config_class.return_value = mock_config

        mock_registry = Mock()
        mock_registry_class.return_value = mock_registry

        mock_orchestrator = Mock()
        mock_soar_class.return_value = mock_orchestrator

        mock_store = Mock()

        # Execute
        executor = QueryExecutor()
        result = executor._initialize_orchestrator(
            api_key="sk-ant-test123", memory_store=mock_store
        )

        # Verify orchestrator was created with correct parameters
        mock_soar_class.assert_called_once()
        call_kwargs = mock_soar_class.call_args[1]
        assert call_kwargs["store"] == mock_store
        assert call_kwargs["agent_registry"] == mock_registry
        assert call_kwargs["config"] == mock_config
        assert call_kwargs["reasoning_llm"] == mock_llm
        assert call_kwargs["solving_llm"] == mock_llm

        assert result == mock_orchestrator


class TestGetMemoryContext:
    """Test memory context retrieval."""

    def test_get_memory_context_with_results(self) -> None:
        """Test _get_memory_context() formats search results as context."""
        # Setup mock store with results
        mock_store = Mock()
        mock_store.search_keyword.return_value = [
            {
                "content": "def add(a, b): return a + b",
                "metadata": {"file_path": "math.py"},
            },
            {
                "content": "def subtract(a, b): return a - b",
                "metadata": {"file_path": "math.py"},
            },
        ]

        executor = QueryExecutor()
        context = executor._get_memory_context(mock_store, query="math functions", limit=2)

        # Verify context formatting
        assert "[1] math.py:" in context
        assert "def add(a, b): return a + b" in context
        assert "[2] math.py:" in context
        assert "def subtract(a, b): return a - b" in context

    def test_get_memory_context_with_no_results(self) -> None:
        """Test _get_memory_context() returns empty string with no results."""
        mock_store = Mock()
        mock_store.search_keyword.return_value = []

        executor = QueryExecutor()
        context = executor._get_memory_context(mock_store, query="nonexistent")

        assert context == ""

    def test_get_memory_context_with_limit(self) -> None:
        """Test _get_memory_context() respects limit parameter."""
        mock_store = Mock()
        mock_store.search_keyword.return_value = [
            {"content": "result1", "metadata": {"file_path": "f1.py"}},
        ]

        executor = QueryExecutor()
        executor._get_memory_context(mock_store, query="test", limit=5)

        # Verify limit was passed to search
        mock_store.search_keyword.assert_called_once_with("test", limit=5)

    def test_get_memory_context_handles_search_error(self) -> None:
        """Test _get_memory_context() returns empty string on search error."""
        mock_store = Mock()
        mock_store.search_keyword.side_effect = RuntimeError("Search failed")

        executor = QueryExecutor()
        context = executor._get_memory_context(mock_store, query="test")

        # Should return empty string instead of raising
        assert context == ""


class TestBuildPhaseTrace:
    """Test phase trace building from orchestrator results."""

    def test_build_phase_trace_with_complete_result(self) -> None:
        """Test _build_phase_trace() builds trace from full orchestrator result."""
        result = {
            "answer": "Response",
            "cost_usd": 0.15,
            "confidence": 0.90,
            "overall_score": 0.85,
            "reasoning_trace": {
                "assess": {"duration_ms": 100, "complexity": "medium"},
                "retrieve": {"duration_ms": 200, "chunks_retrieved": 5},
                "decompose": {"duration_ms": 150, "subgoals": ["goal1", "goal2"]},
            },
            "metadata": {"version": "0.2.0", "agent_count": 3},
        }

        executor = QueryExecutor()
        trace = executor._build_phase_trace(result, total_duration=5.0)

        # Verify trace structure
        assert trace["total_duration"] == 5.0
        assert trace["total_cost"] == 0.15
        assert trace["confidence"] == 0.90
        assert trace["overall_score"] == 0.85
        assert trace["metadata"] == {"version": "0.2.0", "agent_count": 3}

        # Verify phases
        assert len(trace["phases"]) == 3
        phase_names = [p["name"] for p in trace["phases"]]
        assert "Assess" in phase_names
        assert "Retrieve" in phase_names
        assert "Decompose" in phase_names

    def test_build_phase_trace_with_minimal_result(self) -> None:
        """Test _build_phase_trace() handles minimal result gracefully."""
        result = {
            "answer": "Response",
            "reasoning_trace": {},
            "metadata": {},
        }

        executor = QueryExecutor()
        trace = executor._build_phase_trace(result, total_duration=1.0)

        # Verify defaults
        assert trace["total_duration"] == 1.0
        assert trace["total_cost"] == 0.0
        assert trace["confidence"] == 0.0
        assert trace["phases"] == []


class TestGetPhaseSummary:
    """Test phase summary generation."""

    def test_get_phase_summary_for_all_phases(self) -> None:
        """Test _get_phase_summary() generates summaries for all phase types."""
        executor = QueryExecutor()

        # Test different phase types
        assert "Complexity:" in executor._get_phase_summary("assess", {"complexity": "high"})
        assert "Retrieved 5 chunks" in executor._get_phase_summary(
            "retrieve", {"chunks_retrieved": 5}
        )
        assert "Created 3 subgoals" in executor._get_phase_summary(
            "decompose", {"subgoals": ["g1", "g2", "g3"]}
        )
        assert "Quality score: 0.95" in executor._get_phase_summary(
            "verify", {"quality_score": 0.95}
        )
        assert "Assigned 2 agents" in executor._get_phase_summary(
            "route", {"agent_assignments": ["a1", "a2"]}
        )

    def test_get_phase_summary_with_missing_data_returns_completed(self) -> None:
        """Test _get_phase_summary() returns 'Completed' for missing data."""
        executor = QueryExecutor()

        # Empty phase data should return default/fallback value
        # Note: assess phase has fallback to "unknown" for complexity
        result = executor._get_phase_summary("assess", {})
        assert result == "Complexity: unknown"

    def test_get_phase_summary_with_unknown_phase_returns_completed(self) -> None:
        """Test _get_phase_summary() returns 'Completed' for unknown phase."""
        executor = QueryExecutor()

        assert executor._get_phase_summary("unknown_phase", {}) == "Completed"


class TestEstimateCost:
    """Test API cost estimation."""

    def test_estimate_cost_with_typical_usage(self) -> None:
        """Test _estimate_cost() calculates cost for typical token counts."""
        executor = QueryExecutor()

        # 1000 input tokens, 500 output tokens
        cost = executor._estimate_cost(input_tokens=1000, output_tokens=500)

        # Expected: (1000/1000 * 0.003) + (500/1000 * 0.015) = 0.003 + 0.0075 = 0.0105
        assert abs(cost - 0.0105) < 0.0001

    def test_estimate_cost_with_zero_tokens(self) -> None:
        """Test _estimate_cost() with zero tokens returns zero cost."""
        executor = QueryExecutor()

        cost = executor._estimate_cost(input_tokens=0, output_tokens=0)
        assert cost == 0.0

    def test_estimate_cost_with_large_usage(self) -> None:
        """Test _estimate_cost() with large token counts."""
        executor = QueryExecutor()

        # 100K input, 50K output
        cost = executor._estimate_cost(input_tokens=100000, output_tokens=50000)

        # Expected: (100 * 0.003) + (50 * 0.015) = 0.3 + 0.75 = 1.05
        assert abs(cost - 1.05) < 0.01


class TestCallLLMWithRetry:
    """Test LLM retry logic."""

    @patch("aurora_cli.execution.time.sleep")
    def test_call_llm_with_retry_succeeds_on_first_attempt(self, mock_sleep: Mock) -> None:
        """Test _call_llm_with_retry() succeeds on first attempt."""
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "Success"
        mock_llm.generate.return_value = mock_response

        executor = QueryExecutor()
        result = executor._call_llm_with_retry(
            llm=mock_llm,
            prompt="Test prompt",
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            temperature=0.7,
        )

        assert result == mock_response
        mock_llm.generate.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("aurora_cli.execution.time.sleep")
    def test_call_llm_with_retry_retries_on_rate_limit(self, mock_sleep: Mock) -> None:
        """Test _call_llm_with_retry() retries on 429 rate limit error."""
        mock_llm = Mock()

        # First call fails with rate limit, second succeeds
        mock_response = Mock()
        mock_response.content = "Success after retry"
        mock_llm.generate.side_effect = [
            Exception("Error 429: rate limit exceeded"),
            mock_response,
        ]

        executor = QueryExecutor()
        result = executor._call_llm_with_retry(
            llm=mock_llm,
            prompt="Test",
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            temperature=0.7,
        )

        assert result == mock_response
        assert mock_llm.generate.call_count == 2
        mock_sleep.assert_called_once()

    @patch("aurora_cli.execution.time.sleep")
    def test_call_llm_with_retry_retries_on_server_error(self, mock_sleep: Mock) -> None:
        """Test _call_llm_with_retry() retries on 500-series server errors."""
        mock_llm = Mock()

        # First call fails with server error, second succeeds
        mock_response = Mock()
        mock_llm.generate.side_effect = [
            Exception("500 internal server error"),
            mock_response,
        ]

        executor = QueryExecutor()
        executor._call_llm_with_retry(
            llm=mock_llm,
            prompt="Test",
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            temperature=0.7,
        )

        assert mock_llm.generate.call_count == 2
        mock_sleep.assert_called_once()

    @patch("aurora_cli.execution.time.sleep")
    def test_call_llm_with_retry_fails_after_max_retries(self, mock_sleep: Mock) -> None:
        """Test _call_llm_with_retry() raises APIError after exhausting retries."""
        mock_llm = Mock()
        mock_llm.generate.side_effect = Exception("429 rate limit exceeded")

        executor = QueryExecutor()
        with pytest.raises(APIError):
            executor._call_llm_with_retry(
                llm=mock_llm,
                prompt="Test",
                model="claude-sonnet-4-20250514",
                max_tokens=100,
                temperature=0.7,
                max_retries=3,
            )

        # Should have tried 3 times
        assert mock_llm.generate.call_count == 3
        assert mock_sleep.call_count == 2  # Sleep between attempts, not after last

    @patch("aurora_cli.execution.time.sleep")
    def test_call_llm_with_retry_does_not_retry_non_retryable_errors(
        self, mock_sleep: Mock
    ) -> None:
        """Test _call_llm_with_retry() does not retry on non-retryable errors."""
        mock_llm = Mock()
        mock_llm.generate.side_effect = Exception("401 Unauthorized")

        executor = QueryExecutor()
        with pytest.raises(APIError):
            executor._call_llm_with_retry(
                llm=mock_llm,
                prompt="Test",
                model="claude-sonnet-4-20250514",
                max_tokens=100,
                temperature=0.7,
            )

        # Should fail immediately without retries
        assert mock_llm.generate.call_count == 1
        mock_sleep.assert_not_called()

    @patch("aurora_cli.execution.time.sleep")
    @patch("aurora_cli.execution.logger")
    def test_call_llm_with_retry_logs_retry_attempts_when_verbose(
        self, mock_logger: Mock, mock_sleep: Mock
    ) -> None:
        """Test _call_llm_with_retry() logs retry attempts with verbose=True."""
        mock_llm = Mock()
        mock_response = Mock()
        mock_llm.generate.side_effect = [
            Exception("503 service unavailable"),
            mock_response,
        ]

        executor = QueryExecutor()
        executor._call_llm_with_retry(
            llm=mock_llm,
            prompt="Test",
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            temperature=0.7,
            verbose=True,
        )

        # Verify retry was logged
        assert mock_logger.info.call_count >= 1
        log_calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("Retrying" in str(call) for call in log_calls)

    @patch("aurora_cli.execution.time.sleep")
    def test_call_llm_with_retry_uses_exponential_backoff(self, mock_sleep: Mock) -> None:
        """Test _call_llm_with_retry() uses exponential backoff for delays."""
        mock_llm = Mock()
        mock_response = Mock()
        mock_llm.generate.side_effect = [
            Exception("503 service unavailable"),
            Exception("503 service unavailable"),
            mock_response,
        ]

        executor = QueryExecutor()
        executor._call_llm_with_retry(
            llm=mock_llm,
            prompt="Test",
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            temperature=0.7,
        )

        # Verify sleep was called twice with increasing delays
        assert mock_sleep.call_count == 2
        first_delay = mock_sleep.call_args_list[0][0][0]
        second_delay = mock_sleep.call_args_list[1][0][0]

        # Second delay should be approximately 2x first delay (with jitter)
        # Base delays: 0.1, 0.2, 0.4 (with up to 10% jitter)
        assert second_delay > first_delay
        assert second_delay < first_delay * 3  # Allow for jitter


class TestQueryExecutorInteractiveMode:
    """Test QueryExecutor with interactive_mode parameter for retrieval quality handling."""

    def test_query_executor_interactive_mode_enabled(self) -> None:
        """Test QueryExecutor initialization with interactive_mode=True."""
        executor = QueryExecutor(config={}, interactive_mode=True)

        assert executor.interactive_mode is True

    def test_query_executor_non_interactive_mode(self) -> None:
        """Test QueryExecutor initialization with interactive_mode=False."""
        executor = QueryExecutor(config={}, interactive_mode=False)

        assert executor.interactive_mode is False

    def test_query_executor_default_non_interactive(self) -> None:
        """Test QueryExecutor defaults to interactive_mode=False when not specified."""
        executor = QueryExecutor(config={})

        assert executor.interactive_mode is False

    @patch("aurora_soar.orchestrator.SOAROrchestrator")
    @patch("aurora_soar.agent_registry.AgentRegistry")
    @patch("aurora_core.config.loader.Config")
    @patch("aurora_cli.execution.AnthropicClient")
    def test_execute_aurora_passes_interactive_mode_to_orchestrator(
        self,
        mock_client_class: Mock,
        mock_config_class: Mock,
        mock_registry_class: Mock,
        mock_orchestrator_class: Mock,
    ) -> None:
        """Test that execute_aurora passes interactive_mode to SOAROrchestrator."""
        # Mock LLM client
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock config
        mock_config = Mock()
        mock_config_class.return_value = mock_config

        # Mock agent registry
        mock_registry = Mock()
        mock_registry_class.return_value = mock_registry

        # Mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.execute.return_value = {"answer": "Test response", "cost_usd": 0.01}
        mock_orchestrator_class.return_value = mock_orchestrator

        # Mock memory store
        mock_store = Mock()

        # Test with interactive_mode=True
        executor = QueryExecutor(config={}, interactive_mode=True)
        executor.execute_aurora(
            query="What is Python?",
            api_key="test-key",
            memory_store=mock_store,
            verbose=False,
        )

        # Verify SOAROrchestrator was initialized with interactive_mode=True
        call_kwargs = mock_orchestrator_class.call_args[1]
        assert call_kwargs["interactive_mode"] is True

        # Test with interactive_mode=False
        executor = QueryExecutor(config={}, interactive_mode=False)
        executor.execute_aurora(
            query="What is Python?",
            api_key="test-key",
            memory_store=mock_store,
            verbose=False,
        )

        # Verify SOAROrchestrator was initialized with interactive_mode=False
        call_kwargs = mock_orchestrator_class.call_args[1]
        assert call_kwargs["interactive_mode"] is False
