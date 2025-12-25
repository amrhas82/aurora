"""End-to-end integration tests for aur query command.

These tests verify the full query workflow including:
- Direct LLM execution path
- AURORA orchestrator execution path (when implemented)
- Escalation decision logic
- Verbose mode output
- Error handling

Note: Tests requiring real API calls are marked with @pytest.mark.real_api
and will skip if ANTHROPIC_API_KEY environment variable is not set.
"""

from __future__ import annotations

import os
from unittest.mock import Mock, patch

import pytest
from aurora_cli.main import cli
from aurora_reasoning.llm_client import LLMResponse
from click.testing import CliRunner


@pytest.fixture
def runner():
    """Click test runner fixture."""
    return CliRunner()


@pytest.fixture
def mock_api_key():
    """Mock API key for tests that don't need real API."""
    return "test-api-key-sk-ant-1234567890"


@pytest.fixture
def has_real_api_key():
    """Check if real API key is available."""
    return os.environ.get("ANTHROPIC_API_KEY") is not None


class TestQueryCommandIntegration:
    """Integration tests for aur query command."""

    @patch("aurora_cli.execution.AnthropicClient")
    def test_query_direct_llm_basic(self, mock_client_class, runner, mock_api_key):
        """Test basic query execution using direct LLM."""
        # Setup mock
        mock_llm = Mock()
        mock_response = LLMResponse(
            content="Python is a high-level programming language.",
            model="claude-sonnet-4-20250514",
            input_tokens=10,
            output_tokens=15,
            finish_reason="end_turn",
        )
        mock_llm.generate.return_value = mock_response
        mock_client_class.return_value = mock_llm

        # Execute CLI command
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["query", "What is Python?", "--force-direct"],
                env={"ANTHROPIC_API_KEY": mock_api_key},
            )

        # Verify
        assert result.exit_code == 0
        assert "Using Direct LLM (fast mode)" in result.output
        assert "Python is a high-level programming language" in result.output
        mock_llm.generate.assert_called_once()

    @patch("aurora_cli.execution.AnthropicClient")
    def test_query_with_escalation_decision(self, mock_client_class, runner, mock_api_key):
        """Test query with automatic escalation decision."""
        # Setup mock
        mock_llm = Mock()
        mock_response = LLMResponse(
            content="Test response",
            model="claude-sonnet-4-20250514",
            input_tokens=5,
            output_tokens=10,
            finish_reason="end_turn",
        )
        mock_llm.generate.return_value = mock_response
        mock_client_class.return_value = mock_llm

        # Execute simple query (should use direct LLM)
        result = runner.invoke(
            cli,
            ["query", "Hello"],
            env={"ANTHROPIC_API_KEY": mock_api_key},
        )

        # Verify - simple query should auto-select direct LLM
        assert result.exit_code == 0
        assert "Direct LLM" in result.output or "AURORA" in result.output

    @patch("aurora_cli.execution.AnthropicClient")
    def test_query_with_show_reasoning(self, mock_client_class, runner, mock_api_key):
        """Test query with escalation reasoning display."""
        # Setup mock
        mock_llm = Mock()
        mock_response = LLMResponse(
            content="Response",
            model="claude-sonnet-4-20250514",
            input_tokens=5,
            output_tokens=5,
            finish_reason="end_turn",
        )
        mock_llm.generate.return_value = mock_response
        mock_client_class.return_value = mock_llm

        # Execute with show-reasoning flag
        result = runner.invoke(
            cli,
            ["query", "Test", "--show-reasoning"],
            env={"ANTHROPIC_API_KEY": mock_api_key},
        )

        # Verify escalation analysis is shown
        assert result.exit_code == 0
        assert "Escalation Analysis:" in result.output
        assert "Complexity:" in result.output
        assert "Score:" in result.output
        assert "Decision:" in result.output

    def test_query_missing_api_key(self, runner):
        """Test query fails gracefully without API key."""
        result = runner.invoke(
            cli,
            ["query", "Test"],
            env={},  # No API key
        )

        # Verify helpful error message
        assert result.exit_code == 1
        assert "ANTHROPIC_API_KEY environment variable not set" in result.output
        assert "https://console.anthropic.com" in result.output

    @patch("aurora_cli.execution.AnthropicClient")
    def test_query_force_aurora_fallback(self, mock_client_class, runner, mock_api_key):
        """Test AURORA mode falls back to direct LLM (Phase 2 limitation)."""
        # Setup mock
        mock_llm = Mock()
        mock_response = LLMResponse(
            content="AURORA fallback response",
            model="claude-sonnet-4-20250514",
            input_tokens=20,
            output_tokens=30,
            finish_reason="end_turn",
        )
        mock_llm.generate.return_value = mock_response
        mock_client_class.return_value = mock_llm

        # Execute with force-aurora flag
        result = runner.invoke(
            cli,
            ["query", "Complex query", "--force-aurora"],
            env={"ANTHROPIC_API_KEY": mock_api_key},
        )

        # Verify
        assert result.exit_code == 0
        assert "Using AURORA (full pipeline)" in result.output
        assert "AURORA requires memory store setup" in result.output
        assert "AURORA fallback response" in result.output

    @patch("aurora_cli.execution.AnthropicClient")
    def test_query_with_custom_threshold(self, mock_client_class, runner, mock_api_key):
        """Test query with custom escalation threshold."""
        # Setup mock
        mock_llm = Mock()
        mock_response = LLMResponse(
            content="Response",
            model="claude-sonnet-4-20250514",
            input_tokens=10,
            output_tokens=20,
            finish_reason="end_turn",
        )
        mock_llm.generate.return_value = mock_response
        mock_client_class.return_value = mock_llm

        # Execute with custom threshold
        result = runner.invoke(
            cli,
            ["query", "Test", "--threshold", "0.3"],
            env={"ANTHROPIC_API_KEY": mock_api_key},
        )

        # Verify execution succeeds
        assert result.exit_code == 0

    @patch("aurora_cli.execution.AnthropicClient")
    def test_query_api_error_handling(self, mock_client_class, runner, mock_api_key):
        """Test query handles API errors gracefully."""
        # Setup mock to raise error
        mock_llm = Mock()
        mock_llm.generate.side_effect = RuntimeError("API connection failed")
        mock_client_class.return_value = mock_llm

        # Execute query
        result = runner.invoke(
            cli,
            ["query", "Test", "--force-direct"],
            env={"ANTHROPIC_API_KEY": mock_api_key},
        )

        # Verify error is handled
        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "LLM execution failed" in result.output

    @patch("aurora_cli.execution.AnthropicClient")
    def test_query_verbose_mode(self, mock_client_class, runner, mock_api_key):
        """Test query with verbose mode enabled."""
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

        # Execute with verbose flag
        result = runner.invoke(
            cli,
            ["query", "Test", "--verbose", "--force-direct"],
            env={"ANTHROPIC_API_KEY": mock_api_key},
        )

        # Verify execution succeeds (verbose details logged, not printed)
        assert result.exit_code == 0
        assert "Verbose response" in result.output

    @pytest.mark.real_api
    @pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY"),
        reason="Requires ANTHROPIC_API_KEY environment variable",
    )
    def test_query_real_api_simple(self, runner):
        """Test query with real API for simple question.

        This test makes a real API call and incurs cost (~$0.001).
        Only runs when ANTHROPIC_API_KEY is set and --real-api marker is used.
        """
        # Execute real query
        result = runner.invoke(
            cli,
            ["query", "Say 'test passed' exactly", "--force-direct"],
        )

        # Verify
        assert result.exit_code == 0
        assert "test passed" in result.output.lower()
        assert "Response:" in result.output

    @pytest.mark.real_api
    @pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY"),
        reason="Requires ANTHROPIC_API_KEY environment variable",
    )
    def test_query_real_api_with_reasoning(self, runner):
        """Test query with real API showing escalation reasoning.

        This test makes a real API call and incurs cost (~$0.001).
        """
        # Execute real query with reasoning
        result = runner.invoke(
            cli,
            ["query", "What is 2+2?", "--show-reasoning"],
        )

        # Verify
        assert result.exit_code == 0
        assert "Escalation Analysis:" in result.output
        assert "Complexity:" in result.output
        assert "4" in result.output  # Answer to 2+2

    @patch("aurora_cli.execution.AnthropicClient")
    def test_query_multiple_flags(self, mock_client_class, runner, mock_api_key):
        """Test query with multiple flags combined."""
        # Setup mock
        mock_llm = Mock()
        mock_response = LLMResponse(
            content="Multi-flag response",
            model="claude-sonnet-4-20250514",
            input_tokens=10,
            output_tokens=15,
            finish_reason="end_turn",
        )
        mock_llm.generate.return_value = mock_response
        mock_client_class.return_value = mock_llm

        # Execute with multiple flags
        result = runner.invoke(
            cli,
            [
                "query",
                "Test",
                "--force-direct",
                "--show-reasoning",
                "--verbose",
                "--threshold",
                "0.5",
            ],
            env={"ANTHROPIC_API_KEY": mock_api_key},
        )

        # Verify all features work together
        assert result.exit_code == 0
        assert "Escalation Analysis:" in result.output
        assert "Multi-flag response" in result.output


class TestQueryCommandEdgeCases:
    """Edge case tests for query command."""

    @patch("aurora_cli.execution.AnthropicClient")
    def test_query_empty_response(self, mock_client_class, runner, mock_api_key):
        """Test handling of empty response from LLM."""
        # Setup mock with empty response
        mock_llm = Mock()
        mock_response = LLMResponse(
            content="",
            model="claude-sonnet-4-20250514",
            input_tokens=10,
            output_tokens=0,
            finish_reason="end_turn",
        )
        mock_llm.generate.return_value = mock_response
        mock_client_class.return_value = mock_llm

        # Execute query
        result = runner.invoke(
            cli,
            ["query", "Test", "--force-direct"],
            env={"ANTHROPIC_API_KEY": mock_api_key},
        )

        # Verify - should handle empty response gracefully
        assert result.exit_code == 0

    @patch("aurora_cli.execution.AnthropicClient")
    def test_query_long_input(self, mock_client_class, runner, mock_api_key):
        """Test query with very long input text."""
        # Setup mock
        mock_llm = Mock()
        mock_response = LLMResponse(
            content="Response to long query",
            model="claude-sonnet-4-20250514",
            input_tokens=500,
            output_tokens=20,
            finish_reason="end_turn",
        )
        mock_llm.generate.return_value = mock_response
        mock_client_class.return_value = mock_llm

        # Create long query (1000 characters)
        long_query = "Test query " * 100

        # Execute
        result = runner.invoke(
            cli,
            ["query", long_query, "--force-direct"],
            env={"ANTHROPIC_API_KEY": mock_api_key},
        )

        # Verify
        assert result.exit_code == 0
        assert "Response to long query" in result.output

    @patch("aurora_cli.execution.AnthropicClient")
    def test_query_special_characters(self, mock_client_class, runner, mock_api_key):
        """Test query with special characters."""
        # Setup mock
        mock_llm = Mock()
        mock_response = LLMResponse(
            content="Special chars handled",
            model="claude-sonnet-4-20250514",
            input_tokens=10,
            output_tokens=10,
            finish_reason="end_turn",
        )
        mock_llm.generate.return_value = mock_response
        mock_client_class.return_value = mock_llm

        # Query with special characters
        special_query = "What is 'this' & \"that\" <tag>?"

        # Execute
        result = runner.invoke(
            cli,
            ["query", special_query, "--force-direct"],
            env={"ANTHROPIC_API_KEY": mock_api_key},
        )

        # Verify
        assert result.exit_code == 0
        assert "Special chars handled" in result.output
