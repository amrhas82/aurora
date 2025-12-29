"""Unit tests for QueryExecutor auto-escalation logic.

Tests the execute_with_auto_escalation() method with various scenarios:
- Non-interactive mode with low confidence (auto-escalates)
- Interactive mode with user acceptance/decline
- High confidence queries (no escalation)
- Complex/Critical queries (always escalate)
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from aurora_cli.execution import QueryExecutor


class TestAutoEscalation:
    """Tests for auto-escalation logic in QueryExecutor."""

    @pytest.fixture
    def mock_memory_store(self):
        """Create a mock memory store."""
        store = MagicMock()
        store.search.return_value = []
        return store

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = MagicMock()
        response = MagicMock()
        response.content = "Mock response"
        response.input_tokens = 100
        response.output_tokens = 50
        client.generate.return_value = response
        return client

    def test_non_interactive_low_confidence_auto_escalates(self, mock_memory_store):
        """Test that non-interactive mode auto-escalates on low confidence."""
        executor = QueryExecutor(config={}, interactive_mode=False)

        # Mock assess_complexity to return low confidence
        mock_assessment = {
            "complexity": "SIMPLE",
            "confidence": 0.4,  # Below threshold
            "method": "keyword",
        }

        with (
            patch("aurora_cli.execution.QueryExecutor._initialize_llm_client"),
            patch("aurora_soar.phases.assess.assess_complexity", return_value=mock_assessment),
            patch.object(executor, "execute_aurora", return_value="SOAR response") as mock_soar,
        ):
            result = executor.execute_with_auto_escalation(
                query="ambiguous query",
                api_key="test-key",
                memory_store=mock_memory_store,
            )

            # Should auto-escalate to SOAR
            mock_soar.assert_called_once()
            assert result == "SOAR response"

    def test_interactive_low_confidence_user_accepts(self, mock_memory_store):
        """Test that interactive mode prompts user and escalates on acceptance."""
        executor = QueryExecutor(config={}, interactive_mode=True)

        mock_assessment = {
            "complexity": "SIMPLE",
            "confidence": 0.4,
            "method": "keyword",
        }

        with (
            patch("aurora_cli.execution.QueryExecutor._initialize_llm_client"),
            patch("aurora_soar.phases.assess.assess_complexity", return_value=mock_assessment),
            patch("click.confirm", return_value=True),
            patch.object(executor, "execute_aurora", return_value="SOAR response") as mock_soar,
        ):
            result = executor.execute_with_auto_escalation(
                query="ambiguous query",
                api_key="test-key",
                memory_store=mock_memory_store,
            )

            # Should escalate to SOAR after user confirms
            mock_soar.assert_called_once()
            assert result == "SOAR response"

    def test_interactive_low_confidence_user_declines(self, mock_memory_store):
        """Test that interactive mode uses direct LLM when user declines."""
        executor = QueryExecutor(config={}, interactive_mode=True)

        mock_assessment = {
            "complexity": "SIMPLE",
            "confidence": 0.4,
            "method": "keyword",
        }

        with (
            patch("aurora_cli.execution.QueryExecutor._initialize_llm_client"),
            patch("aurora_soar.phases.assess.assess_complexity", return_value=mock_assessment),
            patch("click.confirm", return_value=False),
            patch.object(
                executor, "execute_direct_llm", return_value="Direct LLM response"
            ) as mock_llm,
            patch.object(executor, "execute_aurora") as mock_soar,
        ):
            result = executor.execute_with_auto_escalation(
                query="ambiguous query",
                api_key="test-key",
                memory_store=mock_memory_store,
            )

            # Should use direct LLM, not SOAR
            mock_llm.assert_called_once()
            mock_soar.assert_not_called()
            assert result == "Direct LLM response"

    def test_high_confidence_no_escalation(self, mock_memory_store):
        """Test that high confidence queries don't escalate regardless of mode."""
        executor = QueryExecutor(config={}, interactive_mode=False)

        mock_assessment = {
            "complexity": "SIMPLE",
            "confidence": 0.9,  # High confidence
            "method": "keyword",
        }

        with (
            patch("aurora_cli.execution.QueryExecutor._initialize_llm_client"),
            patch("aurora_soar.phases.assess.assess_complexity", return_value=mock_assessment),
            patch.object(
                executor, "execute_direct_llm", return_value="Direct LLM response"
            ) as mock_llm,
            patch.object(executor, "execute_aurora") as mock_soar,
        ):
            result = executor.execute_with_auto_escalation(
                query="what is Python?",
                api_key="test-key",
                memory_store=mock_memory_store,
            )

            # Should use direct LLM, not SOAR
            mock_llm.assert_called_once()
            mock_soar.assert_not_called()
            assert result == "Direct LLM response"

    def test_complex_query_always_escalates(self, mock_memory_store):
        """Test that COMPLEX queries always use SOAR regardless of confidence."""
        executor = QueryExecutor(config={}, interactive_mode=False)

        mock_assessment = {
            "complexity": "COMPLEX",
            "confidence": 0.9,  # High confidence
            "method": "keyword",
        }

        with (
            patch("aurora_cli.execution.QueryExecutor._initialize_llm_client"),
            patch("aurora_soar.phases.assess.assess_complexity", return_value=mock_assessment),
            patch.object(executor, "execute_aurora", return_value="SOAR response") as mock_soar,
        ):
            result = executor.execute_with_auto_escalation(
                query="design system architecture",
                api_key="test-key",
                memory_store=mock_memory_store,
            )

            # Should use SOAR for COMPLEX query
            mock_soar.assert_called_once()
            assert result == "SOAR response"

    def test_critical_query_always_escalates(self, mock_memory_store):
        """Test that CRITICAL queries always use SOAR regardless of confidence."""
        executor = QueryExecutor(config={}, interactive_mode=False)

        mock_assessment = {
            "complexity": "CRITICAL",
            "confidence": 1.0,
            "method": "keyword",
        }

        with (
            patch("aurora_cli.execution.QueryExecutor._initialize_llm_client"),
            patch("aurora_soar.phases.assess.assess_complexity", return_value=mock_assessment),
            patch.object(executor, "execute_aurora", return_value="SOAR response") as mock_soar,
        ):
            result = executor.execute_with_auto_escalation(
                query="fix security vulnerability",
                api_key="test-key",
                memory_store=mock_memory_store,
            )

            # Should use SOAR for CRITICAL query
            mock_soar.assert_called_once()
            assert result == "SOAR response"

    def test_custom_confidence_threshold(self, mock_memory_store):
        """Test that custom confidence threshold is respected."""
        executor = QueryExecutor(config={}, interactive_mode=False)

        mock_assessment = {
            "complexity": "SIMPLE",
            "confidence": 0.7,  # Above default 0.6, but below custom 0.8
            "method": "keyword",
        }

        with (
            patch("aurora_cli.execution.QueryExecutor._initialize_llm_client"),
            patch("aurora_soar.phases.assess.assess_complexity", return_value=mock_assessment),
            patch.object(executor, "execute_aurora", return_value="SOAR response") as mock_soar,
        ):
            result = executor.execute_with_auto_escalation(
                query="test query",
                api_key="test-key",
                memory_store=mock_memory_store,
                confidence_threshold=0.8,  # Custom threshold
            )

            # Should escalate because 0.7 < 0.8
            mock_soar.assert_called_once()
            assert result == "SOAR response"

    def test_verbose_mode_returns_metadata(self, mock_memory_store):
        """Test that verbose mode returns metadata along with response."""
        executor = QueryExecutor(config={}, interactive_mode=False)

        mock_assessment = {
            "complexity": "SIMPLE",
            "confidence": 0.9,
            "method": "keyword",
        }

        with (
            patch("aurora_cli.execution.QueryExecutor._initialize_llm_client"),
            patch("aurora_soar.phases.assess.assess_complexity", return_value=mock_assessment),
            patch.object(executor, "execute_direct_llm", return_value="Direct LLM response"),
        ):
            result = executor.execute_with_auto_escalation(
                query="what is Python?",
                api_key="test-key",
                memory_store=mock_memory_store,
                verbose=True,
            )

            # Should return tuple with metadata
            assert isinstance(result, tuple)
            response, metadata = result
            assert response == "Direct LLM response"
            assert "assessment" in metadata
            assert metadata["method"] == "direct_llm"
            assert metadata["escalated"] is False

    def test_empty_query_raises_error(self, mock_memory_store):
        """Test that empty query raises ValueError."""
        executor = QueryExecutor(config={}, interactive_mode=False)

        with pytest.raises(ValueError, match="Query cannot be empty"):
            executor.execute_with_auto_escalation(
                query="",
                api_key="test-key",
                memory_store=mock_memory_store,
            )

    def test_none_memory_store_raises_error(self):
        """Test that None memory store raises ValueError."""
        executor = QueryExecutor(config={}, interactive_mode=False)

        with pytest.raises(ValueError, match="Memory store is required"):
            executor.execute_with_auto_escalation(
                query="test query",
                api_key="test-key",
                memory_store=None,
            )
