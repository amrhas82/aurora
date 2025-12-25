"""Unit tests for QueryExecutor class."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import pytest
from aurora_cli.execution import QueryExecutor
from aurora_reasoning.llm_client import LLMResponse


class TestQueryExecutor:
    """Tests for QueryExecutor class."""

    def test_init_with_config(self):
        """Test QueryExecutor initialization with config."""
        config = {"model": "claude-sonnet-4-20250514", "temperature": 0.5}
        executor = QueryExecutor(config=config)

        assert executor.config == config
        assert executor.config["model"] == "claude-sonnet-4-20250514"
        assert executor.config["temperature"] == 0.5

    def test_init_without_config(self):
        """Test QueryExecutor initialization without config."""
        executor = QueryExecutor()

        assert executor.config == {}

    @patch("aurora_cli.execution.AnthropicClient")
    def test_execute_direct_llm_basic(self, mock_client_class):
        """Test basic direct LLM execution."""
        # Setup mock
        mock_llm = Mock()
        mock_response = LLMResponse(
            content="This is a test response",
            model="claude-sonnet-4-20250514",
            input_tokens=10,
            output_tokens=20,
            finish_reason="end_turn",
        )
        mock_llm.generate.return_value = mock_response
        mock_client_class.return_value = mock_llm

        # Execute
        executor = QueryExecutor()
        response = executor.execute_direct_llm(
            query="What is Python?",
            api_key="test-api-key",
            memory_store=None,
            verbose=False,
        )

        # Verify
        assert response == "This is a test response"
        mock_client_class.assert_called_once_with(
            api_key="test-api-key", default_model="claude-sonnet-4-20250514"
        )
        mock_llm.generate.assert_called_once()
        call_kwargs = mock_llm.generate.call_args[1]
        assert call_kwargs["prompt"] == "What is Python?"
        assert call_kwargs["max_tokens"] == 500

    @patch("aurora_cli.execution.AnthropicClient")
    def test_execute_direct_llm_with_verbose(self, mock_client_class):
        """Test direct LLM execution with verbose mode."""
        # Setup mock
        mock_llm = Mock()
        mock_response = LLMResponse(
            content="Verbose response",
            model="claude-sonnet-4-20250514",
            input_tokens=15,
            output_tokens=25,
            finish_reason="end_turn",
        )
        mock_llm.generate.return_value = mock_response
        mock_client_class.return_value = mock_llm

        # Execute
        executor = QueryExecutor()
        response = executor.execute_direct_llm(
            query="Test query",
            api_key="test-key",
            memory_store=None,
            verbose=True,
        )

        # Verify
        assert response == "Verbose response"
        mock_llm.generate.assert_called_once()

    def test_execute_direct_llm_empty_query(self):
        """Test direct LLM execution with empty query raises error."""
        executor = QueryExecutor()

        with pytest.raises(ValueError, match="Query cannot be empty"):
            executor.execute_direct_llm(
                query="",
                api_key="test-key",
                memory_store=None,
            )

    def test_execute_direct_llm_empty_api_key(self):
        """Test direct LLM execution with empty API key raises error."""
        executor = QueryExecutor()

        with pytest.raises(ValueError, match="API key is required"):
            executor.execute_direct_llm(
                query="Test query",
                api_key="",
                memory_store=None,
            )

    @patch("aurora_cli.execution.AnthropicClient")
    def test_execute_direct_llm_with_memory_context(self, mock_client_class):
        """Test direct LLM execution with memory context."""
        # Setup mock LLM
        mock_llm = Mock()
        mock_response = LLMResponse(
            content="Response with context",
            model="claude-sonnet-4-20250514",
            input_tokens=30,
            output_tokens=40,
            finish_reason="end_turn",
        )
        mock_llm.generate.return_value = mock_response
        mock_client_class.return_value = mock_llm

        # Setup mock memory store
        mock_memory = Mock()
        mock_memory.search_keyword.return_value = [
            {
                "content": "def authenticate(user): pass",
                "metadata": {"file_path": "auth.py"},
            },
            {
                "content": "class User: pass",
                "metadata": {"file_path": "models.py"},
            },
        ]

        # Execute
        executor = QueryExecutor()
        response = executor.execute_direct_llm(
            query="How does authentication work?",
            api_key="test-key",
            memory_store=mock_memory,
            verbose=False,
        )

        # Verify
        assert response == "Response with context"
        mock_memory.search_keyword.assert_called_once_with(
            "How does authentication work?", limit=3
        )
        # Verify prompt includes context
        call_kwargs = mock_llm.generate.call_args[1]
        assert "Context:" in call_kwargs["prompt"]
        assert "auth.py" in call_kwargs["prompt"]

    @patch("aurora_cli.execution.AnthropicClient")
    def test_execute_direct_llm_api_error(self, mock_client_class):
        """Test direct LLM execution handles API errors."""
        # Setup mock to raise error
        mock_llm = Mock()
        mock_llm.generate.side_effect = RuntimeError("API connection failed")
        mock_client_class.return_value = mock_llm

        # Execute and verify error handling
        executor = QueryExecutor()
        with pytest.raises(RuntimeError, match="LLM execution failed"):
            executor.execute_direct_llm(
                query="Test query",
                api_key="test-key",
                memory_store=None,
            )

    @patch("aurora_soar.orchestrator.SOAROrchestrator")
    @patch("aurora_soar.agent_registry.AgentRegistry")
    @patch("aurora_core.config.loader.Config")
    @patch("aurora_cli.execution.AnthropicClient")
    def test_execute_aurora_basic(
        self, mock_client_class, mock_config_class, mock_registry_class, mock_orchestrator_class
    ):
        """Test basic AURORA execution."""
        # Setup mocks
        mock_llm = Mock()
        mock_client_class.return_value = mock_llm

        mock_config = Mock()
        mock_config_class.return_value = mock_config

        mock_registry = Mock()
        mock_registry_class.return_value = mock_registry

        mock_orchestrator = Mock()
        mock_result = {
            "answer": "This is the AURORA response",
            "confidence": 0.85,
            "overall_score": 0.9,
            "cost_usd": 0.05,
            "reasoning_trace": {},
            "metadata": {},
        }
        mock_orchestrator.execute.return_value = mock_result
        mock_orchestrator_class.return_value = mock_orchestrator

        mock_memory = Mock()

        # Execute
        executor = QueryExecutor()
        response = executor.execute_aurora(
            query="Complex query requiring AURORA",
            api_key="test-key",
            memory_store=mock_memory,
            verbose=False,
        )

        # Verify
        assert response == "This is the AURORA response"
        mock_orchestrator.execute.assert_called_once_with(
            query="Complex query requiring AURORA", verbosity="NORMAL"
        )

    @patch("aurora_soar.orchestrator.SOAROrchestrator")
    @patch("aurora_soar.agent_registry.AgentRegistry")
    @patch("aurora_core.config.loader.Config")
    @patch("aurora_cli.execution.AnthropicClient")
    def test_execute_aurora_with_verbose(
        self, mock_client_class, mock_config_class, mock_registry_class, mock_orchestrator_class
    ):
        """Test AURORA execution with verbose mode returns phase trace."""
        # Setup mocks
        mock_llm = Mock()
        mock_client_class.return_value = mock_llm

        mock_config = Mock()
        mock_config_class.return_value = mock_config

        mock_registry = Mock()
        mock_registry_class.return_value = mock_registry

        mock_orchestrator = Mock()
        mock_result = {
            "answer": "AURORA verbose response",
            "confidence": 0.9,
            "overall_score": 0.95,
            "cost_usd": 0.08,
            "reasoning_trace": {
                "assess": {"duration_ms": 100, "complexity": "high"},
                "decompose": {"duration_ms": 200, "subgoals": ["goal1", "goal2"]},
            },
            "metadata": {"total_tokens": 500},
        }
        mock_orchestrator.execute.return_value = mock_result
        mock_orchestrator_class.return_value = mock_orchestrator

        mock_memory = Mock()

        # Execute
        executor = QueryExecutor()
        result = executor.execute_aurora(
            query="Complex query",
            api_key="test-key",
            memory_store=mock_memory,
            verbose=True,
        )

        # Verify
        assert isinstance(result, tuple)
        response, phase_trace = result
        assert response == "AURORA verbose response"
        assert isinstance(phase_trace, dict)
        assert "phases" in phase_trace
        assert "total_duration" in phase_trace
        assert "total_cost" in phase_trace
        assert phase_trace["total_cost"] == 0.08
        mock_orchestrator.execute.assert_called_once_with(
            query="Complex query", verbosity="VERBOSE"
        )

    def test_execute_aurora_empty_query(self):
        """Test AURORA execution with empty query raises error."""
        executor = QueryExecutor()
        mock_memory = Mock()

        with pytest.raises(ValueError, match="Query cannot be empty"):
            executor.execute_aurora(
                query="",
                api_key="test-key",
                memory_store=mock_memory,
            )

    def test_execute_aurora_no_memory_store(self):
        """Test AURORA execution without memory store raises error."""
        executor = QueryExecutor()

        with pytest.raises(ValueError, match="Memory store is required"):
            executor.execute_aurora(
                query="Test query",
                api_key="test-key",
                memory_store=None,
            )

    @patch("aurora_cli.execution.AnthropicClient")
    def test_initialize_llm_client(self, mock_client_class):
        """Test LLM client initialization."""
        mock_llm = Mock()
        mock_client_class.return_value = mock_llm

        executor = QueryExecutor(config={"model": "custom-model"})
        client = executor._initialize_llm_client("test-api-key")

        mock_client_class.assert_called_once_with(
            api_key="test-api-key", default_model="custom-model"
        )
        assert client == mock_llm

    def test_get_memory_context_with_results(self):
        """Test memory context retrieval with results."""
        mock_memory = Mock()
        mock_memory.search_keyword.return_value = [
            {"content": "chunk 1", "metadata": {"file_path": "file1.py"}},
            {"content": "chunk 2", "metadata": {"file_path": "file2.py"}},
        ]

        executor = QueryExecutor()
        context = executor._get_memory_context(mock_memory, "test query", limit=2)

        assert "chunk 1" in context
        assert "chunk 2" in context
        assert "file1.py" in context
        assert "file2.py" in context
        mock_memory.search_keyword.assert_called_once_with("test query", limit=2)

    def test_get_memory_context_no_results(self):
        """Test memory context retrieval with no results."""
        mock_memory = Mock()
        mock_memory.search_keyword.return_value = []

        executor = QueryExecutor()
        context = executor._get_memory_context(mock_memory, "test query")

        assert context == ""

    def test_get_memory_context_error_handling(self):
        """Test memory context retrieval handles errors gracefully."""
        mock_memory = Mock()
        mock_memory.search_keyword.side_effect = Exception("Memory error")

        executor = QueryExecutor()
        context = executor._get_memory_context(mock_memory, "test query")

        # Should return empty string on error, not raise
        assert context == ""

    def test_estimate_cost(self):
        """Test cost estimation calculation."""
        executor = QueryExecutor()
        cost = executor._estimate_cost(input_tokens=1000, output_tokens=2000)

        # 1000 * 0.003 + 2000 * 0.015 = 3 + 30 = 33 cents
        assert cost == pytest.approx(0.033, rel=1e-6)

    def test_build_phase_trace(self):
        """Test phase trace building."""
        executor = QueryExecutor()

        orchestrator_result = {
            "answer": "response",
            "confidence": 0.9,
            "overall_score": 0.95,
            "cost_usd": 0.05,
            "reasoning_trace": {
                "assess": {"duration_ms": 100, "complexity": "medium"},
                "decompose": {"duration_ms": 150, "subgoals": ["a", "b"]},
            },
            "metadata": {"total_tokens": 300},
        }

        trace = executor._build_phase_trace(orchestrator_result, total_duration=2.5)

        assert "phases" in trace
        assert trace["total_duration"] == 2.5
        assert trace["total_cost"] == 0.05
        assert trace["confidence"] == 0.9
        assert trace["overall_score"] == 0.95
        assert len(trace["phases"]) == 2

        # Check assess phase
        assess_phase = trace["phases"][0]
        assert assess_phase["name"] == "Assess"
        assert assess_phase["duration"] == 0.1  # 100ms in seconds
        assert "Complexity" in assess_phase["summary"]

    def test_get_phase_summary(self):
        """Test phase summary generation."""
        executor = QueryExecutor()

        # Test assess phase
        summary = executor._get_phase_summary("assess", {"complexity": "high"})
        assert summary == "Complexity: high"

        # Test decompose phase
        summary = executor._get_phase_summary(
            "decompose", {"subgoals": ["goal1", "goal2", "goal3"]}
        )
        assert summary == "Created 3 subgoals"

        # Test route phase
        summary = executor._get_phase_summary(
            "route", {"agent_assignments": ["agent1", "agent2"]}
        )
        assert summary == "Assigned 2 agents"

        # Test unknown phase
        summary = executor._get_phase_summary("unknown_phase", {})
        assert summary == "Completed"
