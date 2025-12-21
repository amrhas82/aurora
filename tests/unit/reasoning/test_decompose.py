"""Unit tests for decomposition logic."""

import json
from unittest.mock import MagicMock, patch

import pytest

from aurora_reasoning.decompose import (
    DecompositionResult,
    decompose_query,
)
from aurora_reasoning.llm_client import LLMResponse
from aurora_reasoning.prompts.examples import Complexity


class TestDecompositionResult:
    """Tests for DecompositionResult class."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = DecompositionResult(
            goal="Test goal",
            subgoals=[{"description": "Test", "suggested_agent": "code-analyzer", "is_critical": True, "depends_on": []}],
            execution_order=[{"phase": 1, "parallelizable": [0], "sequential": []}],
            expected_tools=["code_reader"],
        )

        data = result.to_dict()
        assert data["goal"] == "Test goal"
        assert len(data["subgoals"]) == 1
        assert data["subgoals"][0]["description"] == "Test"

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "goal": "Test goal",
            "subgoals": [{"description": "Test", "suggested_agent": "code-analyzer", "is_critical": True, "depends_on": []}],
            "execution_order": [{"phase": 1, "parallelizable": [0], "sequential": []}],
            "expected_tools": ["code_reader"],
        }

        result = DecompositionResult.from_dict(data)
        assert result.goal == "Test goal"
        assert len(result.subgoals) == 1


class TestDecomposeQuery:
    """Tests for decompose_query function."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        client = MagicMock()
        return client

    @pytest.fixture
    def valid_decomposition_response(self):
        """Create valid decomposition response."""
        return {
            "goal": "Analyze the calculate_total function",
            "subgoals": [
                {
                    "description": "Read calculate_total function",
                    "suggested_agent": "code-analyzer",
                    "is_critical": True,
                    "depends_on": [],
                }
            ],
            "execution_order": [
                {
                    "phase": 1,
                    "parallelizable": [0],
                    "sequential": [],
                }
            ],
            "expected_tools": ["code_reader"],
        }

    def test_simple_query_no_examples(self, mock_llm_client, valid_decomposition_response):
        """Test SIMPLE query gets 0 examples."""
        mock_llm_client.generate_json.return_value = LLMResponse(
            content=json.dumps(valid_decomposition_response),
            model="test-model",
            input_tokens=100,
            output_tokens=50,
            finish_reason="stop",
        )

        result = decompose_query(
            llm_client=mock_llm_client,
            query="What does calculate_total do?",
            complexity=Complexity.SIMPLE,
        )

        assert result.goal == "Analyze the calculate_total function"
        assert len(result.subgoals) == 1

        # Verify LLM was called with JSON generation
        mock_llm_client.generate_json.assert_called_once()
        call_args = mock_llm_client.generate_json.call_args
        assert "system_prompt" in call_args.kwargs
        assert "user_prompt" in call_args.kwargs
        assert call_args.kwargs["temperature"] == 0.2

        # Verify no examples in user prompt for SIMPLE
        user_prompt = call_args.kwargs["user_prompt"]
        assert "Here are some examples:" not in user_prompt

    @patch("aurora_reasoning.decompose.get_loader")
    def test_medium_query_gets_examples(self, mock_get_loader, mock_llm_client, valid_decomposition_response):
        """Test MEDIUM query gets 2 examples."""
        mock_loader = MagicMock()
        mock_loader.get_examples_by_complexity.return_value = [
            {
                "complexity": "MEDIUM",
                "query": "Example 1",
                "decomposition": {"goal": "Example goal", "subgoals": [], "execution_order": [], "expected_tools": []},
            },
            {
                "complexity": "MEDIUM",
                "query": "Example 2",
                "decomposition": {"goal": "Example goal 2", "subgoals": [], "execution_order": [], "expected_tools": []},
            },
        ]
        mock_get_loader.return_value = mock_loader

        mock_llm_client.generate_json.return_value = LLMResponse(
            content=json.dumps(valid_decomposition_response),
            model="test-model",
            input_tokens=100,
            output_tokens=50,
            finish_reason="stop",
        )

        result = decompose_query(
            llm_client=mock_llm_client,
            query="Add email validation",
            complexity=Complexity.MEDIUM,
        )

        assert result.goal == "Analyze the calculate_total function"

        # Verify examples were loaded
        mock_loader.get_examples_by_complexity.assert_called_once_with(
            "example_decompositions.json",
            Complexity.MEDIUM
        )

        # Verify examples in user prompt
        call_args = mock_llm_client.generate_json.call_args
        user_prompt = call_args.kwargs["user_prompt"]
        assert "Here are some examples:" in user_prompt
        assert "Example 1" in user_prompt
        assert "Example 2" in user_prompt

    def test_context_summary_injection(self, mock_llm_client, valid_decomposition_response):
        """Test context summary is injected into prompt."""
        mock_llm_client.generate_json.return_value = LLMResponse(
            content=json.dumps(valid_decomposition_response),
            model="test-model",
            input_tokens=100,
            output_tokens=50,
            finish_reason="stop",
        )

        result = decompose_query(
            llm_client=mock_llm_client,
            query="Test query",
            complexity=Complexity.SIMPLE,
            context_summary="Available: 5 code chunks",
        )

        call_args = mock_llm_client.generate_json.call_args
        user_prompt = call_args.kwargs["user_prompt"]
        assert "Available: 5 code chunks" in user_prompt

    def test_available_agents_injection(self, mock_llm_client, valid_decomposition_response):
        """Test available agents are injected into prompt."""
        mock_llm_client.generate_json.return_value = LLMResponse(
            content=json.dumps(valid_decomposition_response),
            model="test-model",
            input_tokens=100,
            output_tokens=50,
            finish_reason="stop",
        )

        result = decompose_query(
            llm_client=mock_llm_client,
            query="Test query",
            complexity=Complexity.SIMPLE,
            available_agents=["code-analyzer", "test-runner"],
        )

        call_args = mock_llm_client.generate_json.call_args
        user_prompt = call_args.kwargs["user_prompt"]
        assert "code-analyzer" in user_prompt
        assert "test-runner" in user_prompt

    def test_retry_feedback_injection(self, mock_llm_client, valid_decomposition_response):
        """Test retry feedback is injected into prompt."""
        mock_llm_client.generate_json.return_value = LLMResponse(
            content=json.dumps(valid_decomposition_response),
            model="test-model",
            input_tokens=100,
            output_tokens=50,
            finish_reason="stop",
        )

        result = decompose_query(
            llm_client=mock_llm_client,
            query="Test query",
            complexity=Complexity.SIMPLE,
            retry_feedback="Previous attempt was incomplete. Add error handling.",
        )

        call_args = mock_llm_client.generate_json.call_args
        user_prompt = call_args.kwargs["user_prompt"]
        assert "Previous attempt was incomplete" in user_prompt
        assert "Add error handling" in user_prompt

    def test_invalid_json_response(self, mock_llm_client):
        """Test handling of invalid JSON response."""
        mock_llm_client.generate_json.return_value = LLMResponse(
            content="This is not JSON",
            model="test-model",
            input_tokens=100,
            output_tokens=50,
            finish_reason="stop",
        )

        with pytest.raises(ValueError, match="LLM returned invalid JSON"):
            decompose_query(
                llm_client=mock_llm_client,
                query="Test query",
                complexity=Complexity.SIMPLE,
            )

    def test_missing_required_fields(self, mock_llm_client):
        """Test handling of response with missing required fields."""
        incomplete_response = {
            "goal": "Test goal",
            # Missing subgoals, execution_order, expected_tools
        }

        mock_llm_client.generate_json.return_value = LLMResponse(
            content=json.dumps(incomplete_response),
            model="test-model",
            input_tokens=100,
            output_tokens=50,
            finish_reason="stop",
        )

        with pytest.raises(ValueError, match="missing required fields"):
            decompose_query(
                llm_client=mock_llm_client,
                query="Test query",
                complexity=Complexity.SIMPLE,
            )

    def test_invalid_subgoals_structure(self, mock_llm_client):
        """Test handling of invalid subgoals structure."""
        invalid_response = {
            "goal": "Test goal",
            "subgoals": "not a list",  # Should be list
            "execution_order": [],
            "expected_tools": [],
        }

        mock_llm_client.generate_json.return_value = LLMResponse(
            content=json.dumps(invalid_response),
            model="test-model",
            input_tokens=100,
            output_tokens=50,
            finish_reason="stop",
        )

        with pytest.raises(ValueError, match="'subgoals' must be a list"):
            decompose_query(
                llm_client=mock_llm_client,
                query="Test query",
                complexity=Complexity.SIMPLE,
            )

    def test_subgoal_missing_fields(self, mock_llm_client):
        """Test handling of subgoal with missing required fields."""
        invalid_response = {
            "goal": "Test goal",
            "subgoals": [
                {
                    "description": "Test",
                    # Missing suggested_agent, is_critical, depends_on
                }
            ],
            "execution_order": [],
            "expected_tools": [],
        }

        mock_llm_client.generate_json.return_value = LLMResponse(
            content=json.dumps(invalid_response),
            model="test-model",
            input_tokens=100,
            output_tokens=50,
            finish_reason="stop",
        )

        with pytest.raises(ValueError, match="Subgoal .* missing required fields"):
            decompose_query(
                llm_client=mock_llm_client,
                query="Test query",
                complexity=Complexity.SIMPLE,
            )

    def test_invalid_execution_order_structure(self, mock_llm_client):
        """Test handling of invalid execution_order structure."""
        invalid_response = {
            "goal": "Test goal",
            "subgoals": [
                {"description": "Test", "suggested_agent": "code-analyzer", "is_critical": True, "depends_on": []}
            ],
            "execution_order": "not a list",  # Should be list
            "expected_tools": [],
        }

        mock_llm_client.generate_json.return_value = LLMResponse(
            content=json.dumps(invalid_response),
            model="test-model",
            input_tokens=100,
            output_tokens=50,
            finish_reason="stop",
        )

        with pytest.raises(ValueError, match="'execution_order' must be a list"):
            decompose_query(
                llm_client=mock_llm_client,
                query="Test query",
                complexity=Complexity.SIMPLE,
            )

    def test_execution_phase_missing_phase_field(self, mock_llm_client):
        """Test handling of execution phase missing phase field."""
        invalid_response = {
            "goal": "Test goal",
            "subgoals": [
                {"description": "Test", "suggested_agent": "code-analyzer", "is_critical": True, "depends_on": []}
            ],
            "execution_order": [
                {
                    "parallelizable": [0],
                    # Missing phase field
                }
            ],
            "expected_tools": [],
        }

        mock_llm_client.generate_json.return_value = LLMResponse(
            content=json.dumps(invalid_response),
            model="test-model",
            input_tokens=100,
            output_tokens=50,
            finish_reason="stop",
        )

        with pytest.raises(ValueError, match="missing 'phase' field"):
            decompose_query(
                llm_client=mock_llm_client,
                query="Test query",
                complexity=Complexity.SIMPLE,
            )
