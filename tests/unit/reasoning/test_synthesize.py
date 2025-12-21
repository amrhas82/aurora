"""Unit tests for synthesis logic."""

import json
from unittest.mock import MagicMock, patch

import pytest

from aurora_reasoning.llm_client import LLMResponse
from aurora_reasoning.synthesize import (
    SynthesisResult,
    synthesize_results,
    verify_synthesis,
)

# Import internal functions for testing
from aurora_reasoning.synthesize import (
    _build_synthesis_system_prompt,
    _build_synthesis_user_prompt,
    _extract_traceability,
    _parse_synthesis_response,
    _validate_traceability,
)


class TestSynthesisResult:
    """Tests for SynthesisResult class."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = SynthesisResult(
            answer="Test answer",
            confidence=0.85,
            traceability=[{"agent": "test", "subgoal_id": 0}],
            metadata={"retry_count": 0},
        )

        data = result.to_dict()
        assert data["answer"] == "Test answer"
        assert data["confidence"] == 0.85
        assert len(data["traceability"]) == 1
        assert data["metadata"]["retry_count"] == 0

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "answer": "Test answer",
            "confidence": 0.85,
            "traceability": [{"agent": "test", "subgoal_id": 0}],
            "metadata": {"retry_count": 0},
        }

        result = SynthesisResult.from_dict(data)
        assert result.answer == "Test answer"
        assert result.confidence == 0.85
        assert len(result.traceability) == 1


class TestParseSynthesisResponse:
    """Tests for _parse_synthesis_response function."""

    def test_parse_valid_response(self):
        """Test parsing valid synthesis response."""
        response = """ANSWER:
This is the synthesized answer from multiple agents.

CONFIDENCE: 0.85
"""
        result = _parse_synthesis_response(response)
        assert "answer" in result
        assert "This is the synthesized answer" in result["answer"]
        assert result["confidence"] == 0.85

    def test_parse_multiline_answer(self):
        """Test parsing response with multiline answer."""
        response = """ANSWER:
First line of answer.
Second line of answer.
Third line of answer.

CONFIDENCE: 0.90
"""
        result = _parse_synthesis_response(response)
        assert "First line" in result["answer"]
        assert "Second line" in result["answer"]
        assert "Third line" in result["answer"]
        assert result["confidence"] == 0.90

    def test_parse_answer_on_same_line(self):
        """Test parsing when answer starts on same line as ANSWER:."""
        response = """ANSWER: Short answer here.

CONFIDENCE: 0.75
"""
        result = _parse_synthesis_response(response)
        assert result["answer"] == "Short answer here."
        assert result["confidence"] == 0.75

    def test_parse_missing_answer_raises(self):
        """Test that missing ANSWER section raises ValueError."""
        response = """CONFIDENCE: 0.85"""
        with pytest.raises(ValueError, match="No ANSWER section found"):
            _parse_synthesis_response(response)

    def test_parse_invalid_confidence_raises(self):
        """Test that invalid confidence value raises ValueError."""
        response = """ANSWER: Test answer

CONFIDENCE: invalid
"""
        with pytest.raises(ValueError, match="Invalid confidence value"):
            _parse_synthesis_response(response)

    def test_parse_confidence_out_of_range_raises(self):
        """Test that out-of-range confidence raises ValueError."""
        response = """ANSWER: Test answer

CONFIDENCE: 1.5
"""
        with pytest.raises(ValueError, match="Invalid confidence value"):
            _parse_synthesis_response(response)

    def test_parse_default_confidence(self):
        """Test that missing confidence uses default value."""
        response = """ANSWER: Test answer"""
        result = _parse_synthesis_response(response)
        assert result["confidence"] == 0.5  # Default


class TestValidateTraceability:
    """Tests for _validate_traceability function."""

    def test_valid_traceability(self):
        """Test that valid traceability passes."""
        answer = "According to agent-1, the feature is implemented."
        summaries = [
            {"agent": "agent-1", "summary": "Feature implemented"}
        ]
        # Should not raise
        _validate_traceability(answer, summaries)

    def test_missing_reference_raises(self):
        """Test that missing agent reference raises ValueError."""
        answer = "The feature is implemented."
        summaries = [
            {"agent": "agent-1", "summary": "Feature implemented"}
        ]
        with pytest.raises(ValueError, match="does not reference any agent"):
            _validate_traceability(answer, summaries)

    def test_empty_summaries_skips_validation(self):
        """Test that empty summaries skips validation."""
        answer = "The feature is implemented."
        summaries = []
        # Should not raise
        _validate_traceability(answer, summaries)


class TestExtractTraceability:
    """Tests for _extract_traceability function."""

    def test_extract_single_agent(self):
        """Test extraction with single agent reference."""
        answer = "According to agent-1, the implementation is complete."
        summaries = [
            {"agent": "agent-1", "subgoal_id": 0, "subgoal_description": "Implement feature"}
        ]

        traceability = _extract_traceability(answer, summaries)
        assert len(traceability) == 1
        assert traceability[0]["agent"] == "agent-1"
        assert traceability[0]["subgoal_id"] == 0

    def test_extract_multiple_agents(self):
        """Test extraction with multiple agent references."""
        answer = "Agent-1 implemented the feature, and agent-2 wrote tests."
        summaries = [
            {"agent": "agent-1", "subgoal_id": 0, "subgoal_description": "Implement"},
            {"agent": "agent-2", "subgoal_id": 1, "subgoal_description": "Test"},
        ]

        traceability = _extract_traceability(answer, summaries)
        assert len(traceability) == 2

    def test_extract_no_references(self):
        """Test extraction with no agent references."""
        answer = "The feature is complete."
        summaries = [
            {"agent": "agent-1", "subgoal_id": 0, "subgoal_description": "Implement"}
        ]

        traceability = _extract_traceability(answer, summaries)
        assert len(traceability) == 0


class TestBuildPrompts:
    """Tests for prompt building functions."""

    def test_build_system_prompt(self):
        """Test system prompt building."""
        prompt = _build_synthesis_system_prompt()
        assert "synthesizing information" in prompt.lower()
        assert "ANSWER:" in prompt
        assert "CONFIDENCE:" in prompt
        assert "Do NOT output JSON" in prompt


class TestVerifySynthesis:
    """Tests for verify_synthesis function."""

    def test_verify_synthesis_pass(self):
        """Test synthesis verification with passing scores."""
        mock_llm = MagicMock()
        # generate_json returns dict directly, not LLMResponse
        mock_llm.generate_json.return_value = {
                "coherence": 0.9,
                "completeness": 0.85,
                "factuality": 0.95,
                "overall_score": 0.9,
                "issues": [],
                "suggestions": [],
            }

        result = verify_synthesis(
            llm_client=mock_llm,
            query="Test query",
            agent_outputs=[{"summary": "Test"}],
            synthesis_answer="Test answer",
        )

        assert result["overall_score"] == 0.9
        assert result["coherence"] == 0.9
        assert result["completeness"] == 0.85
        assert result["factuality"] == 0.95

    def test_verify_synthesis_calculates_score(self):
        """Test that overall_score is calculated if wrong."""
        mock_llm = MagicMock()
        # generate_json returns dict directly, not LLMResponse
        mock_llm.generate_json.return_value = {
                "coherence": 0.9,
                "completeness": 0.9,
                "factuality": 0.9,
                "overall_score": 0.5,  # Wrong calculation
                "issues": [],
                "suggestions": [],
            }

        result = verify_synthesis(
            llm_client=mock_llm,
            query="Test query",
            agent_outputs=[],
            synthesis_answer="Test",
        )

        # Should be corrected to (0.9 + 0.9 + 0.9) / 3 = 0.9
        assert abs(result["overall_score"] - 0.9) < 0.01

    def test_verify_synthesis_invalid_json_raises(self):
        """Test that invalid JSON raises ValueError."""
        mock_llm = MagicMock()
        # Return a non-dict to trigger type validation error
        mock_llm.generate_json.return_value = "Not a dict"

        with pytest.raises(ValueError, match="non-dict response"):
            verify_synthesis(
                llm_client=mock_llm,
                query="Test",
                agent_outputs=[],
                synthesis_answer="Test",
            )

    def test_verify_synthesis_missing_fields_raises(self):
        """Test that missing required fields raises ValueError."""
        mock_llm = MagicMock()
        # generate_json returns dict directly, not LLMResponse
        mock_llm.generate_json.return_value = {
                "coherence": 0.8,
                # Missing completeness, factuality, overall_score
            }

        with pytest.raises(ValueError, match="missing required fields"):
            verify_synthesis(
                llm_client=mock_llm,
                query="Test",
                agent_outputs=[],
                synthesis_answer="Test",
            )

    def test_verify_synthesis_invalid_score_range_raises(self):
        """Test that invalid score range raises ValueError."""
        mock_llm = MagicMock()
        # generate_json returns dict directly, not LLMResponse
        mock_llm.generate_json.return_value = {
                "coherence": 1.5,  # Out of range
                "completeness": 0.8,
                "factuality": 0.8,
                "overall_score": 0.8,
            }

        with pytest.raises(ValueError, match="Invalid coherence score"):
            verify_synthesis(
                llm_client=mock_llm,
                query="Test",
                agent_outputs=[],
                synthesis_answer="Test",
            )


class TestSynthesizeResults:
    """Tests for synthesize_results function."""

    def test_synthesize_success_first_try(self):
        """Test successful synthesis on first attempt."""
        mock_llm = MagicMock()

        # Mock synthesis call
        mock_llm.generate.return_value = LLMResponse(
            content="""ANSWER:
The feature has been successfully implemented by agent-coder.

CONFIDENCE: 0.85
""",
            model="test-model",
            input_tokens=200, output_tokens=100, finish_reason="stop",
        )

        # Mock verification call
        # generate_json returns dict directly, not LLMResponse
        mock_llm.generate_json.return_value = {
                "coherence": 0.9,
                "completeness": 0.85,
                "factuality": 0.9,
                "overall_score": 0.88,
                "issues": [],
                "suggestions": [],
            }

        agent_outputs = [
            {
                "subgoal_index": 0,
                "agent_name": "agent-coder",
                "summary": "Feature implemented",
                "confidence": 0.9,
                "success": True,
                "data": {},
            }
        ]

        decomposition = {
            "goal": "Implement feature",
            "subgoals": [{"description": "Implement"}],
        }

        result = synthesize_results(
            llm_client=mock_llm,
            query="Implement feature",
            agent_outputs=agent_outputs,
            decomposition=decomposition,
        )

        assert result.confidence >= 0.7
        assert "agent-coder" in result.answer
        assert result.metadata["retry_count"] == 0
        assert len(result.traceability) > 0

    def test_synthesize_retry_on_low_score(self):
        """Test synthesis retries when quality score is low."""
        mock_llm = MagicMock()

        # Mock synthesis calls - need 3 calls (first + retry + 1 extra for test logic)
        synthesis_responses = [
            LLMResponse(
                content="""ANSWER: Short answer by agent-test.
CONFIDENCE: 0.6""",
                model="test",
                input_tokens=200, output_tokens=50, finish_reason="stop",
            ),
            LLMResponse(
                content="""ANSWER: Agent-test completed the work successfully.
CONFIDENCE: 0.8""",
                model="test",
                input_tokens=250, output_tokens=100, finish_reason="stop",
            ),
        ]

        # Mock verification calls - generate_json returns dict directly
        verification_responses = [
            {
                "coherence": 0.6,
                "completeness": 0.5,
                "factuality": 0.6,
                "overall_score": 0.57,
                "issues": ["Too brief"],
            },
            {
                "coherence": 0.85,
                "completeness": 0.8,
                "factuality": 0.85,
                "overall_score": 0.83,
                "issues": [],
            },
        ]

        mock_llm.generate.side_effect = synthesis_responses
        mock_llm.generate_json.side_effect = verification_responses

        result = synthesize_results(
            llm_client=mock_llm,
            query="Test",
            agent_outputs=[{"agent_name": "agent-test", "summary": "Done", "confidence": 0.9}],
            decomposition={"goal": "Test", "subgoals": []},
        )

        assert result.metadata["retry_count"] == 1
        assert result.confidence >= 0.7

    def test_synthesize_max_retries_returns_best_effort(self):
        """Test that max retries returns best-effort result."""
        mock_llm = MagicMock()

        # All attempts return low scores - but include agent reference
        mock_llm.generate.return_value = LLMResponse(
            content="""ANSWER: Agent-test completed briefly.
CONFIDENCE: 0.5""",
            model="test",
            input_tokens=200, output_tokens=20, finish_reason="stop",
        )

        # generate_json returns dict directly, not LLMResponse
        mock_llm.generate_json.return_value = {
                "coherence": 0.5,
                "completeness": 0.4,
                "factuality": 0.5,
                "overall_score": 0.47,
                "issues": ["Too brief"],
            }

        result = synthesize_results(
            llm_client=mock_llm,
            query="Test",
            agent_outputs=[{"agent_name": "agent-test", "summary": "Done", "confidence": 0.9}],
            decomposition={"goal": "Test", "subgoals": []},
            max_retries=2,
        )

        assert result.metadata["retry_count"] == 2
        assert "quality_warning" in result.metadata
        assert result.confidence < 0.7

    def test_synthesize_parsing_error_retries(self):
        """Test that parsing errors trigger retry."""
        mock_llm = MagicMock()

        synthesis_responses = [
            # First synthesis - invalid format
            LLMResponse(content="Invalid format", model="test", input_tokens=50, output_tokens=10, finish_reason="stop"),
            # Second synthesis - valid
            LLMResponse(
                content="""ANSWER: Agent-test completed work.
CONFIDENCE: 0.8""",
                model="test",
                input_tokens=200, output_tokens=50, finish_reason="stop",
            ),
        ]

        # Verification - generate_json returns dict directly
        verification_response = {
            "coherence": 0.8,
            "completeness": 0.8,
            "factuality": 0.8,
            "overall_score": 0.8,
            "issues": [],
        }

        mock_llm.generate.side_effect = synthesis_responses
        mock_llm.generate_json.return_value = verification_response

        result = synthesize_results(
            llm_client=mock_llm,
            query="Test",
            agent_outputs=[{"agent_name": "agent-test", "summary": "Done", "confidence": 0.9}],
            decomposition={"goal": "Test", "subgoals": []},
        )

        assert result.metadata["retry_count"] == 1
