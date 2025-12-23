"""Unit tests for verification logic."""

from unittest.mock import MagicMock

import pytest
from aurora_reasoning.verify import (
    VerificationOption,
    VerificationResult,
    VerificationVerdict,
    _calculate_overall_score,
    _validate_verdict_consistency,
    verify_decomposition,
)


class TestVerificationResult:
    """Tests for VerificationResult class."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = VerificationResult(
            completeness=0.8,
            consistency=0.9,
            groundedness=0.7,
            routability=0.85,
            overall_score=0.8,
            verdict=VerificationVerdict.PASS,
            issues=[],
            suggestions=[],
            option_used=VerificationOption.SELF,
        )

        data = result.to_dict()
        assert data["completeness"] == 0.8
        assert data["verdict"] == "PASS"
        assert data["option_used"] == "self"

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "completeness": 0.8,
            "consistency": 0.9,
            "groundedness": 0.7,
            "routability": 0.85,
            "overall_score": 0.8,
            "verdict": "PASS",
            "issues": [],
            "suggestions": [],
            "option_used": "self",
        }

        result = VerificationResult.from_dict(data)
        assert result.completeness == 0.8
        assert result.verdict == VerificationVerdict.PASS
        assert result.option_used == VerificationOption.SELF


class TestCalculateOverallScore:
    """Tests for _calculate_overall_score function."""

    def test_perfect_scores(self):
        """Test with all perfect scores."""
        score = _calculate_overall_score(1.0, 1.0, 1.0, 1.0)
        assert score == 1.0

    def test_zero_scores(self):
        """Test with all zero scores."""
        score = _calculate_overall_score(0.0, 0.0, 0.0, 0.0)
        assert score == 0.0

    def test_weighted_calculation(self):
        """Test weighted score calculation."""
        # Completeness: 0.8 * 0.4 = 0.32
        # Consistency: 0.6 * 0.2 = 0.12
        # Groundedness: 0.9 * 0.2 = 0.18
        # Routability: 0.7 * 0.2 = 0.14
        # Total: 0.76
        score = _calculate_overall_score(0.8, 0.6, 0.9, 0.7)
        assert abs(score - 0.76) < 0.001

    def test_completeness_weighted_most(self):
        """Test that completeness is weighted 40%."""
        # Perfect completeness, zero others
        score = _calculate_overall_score(1.0, 0.0, 0.0, 0.0)
        assert score == 0.4


class TestValidateVerdictConsistency:
    """Tests for _validate_verdict_consistency function."""

    def test_pass_with_high_score(self):
        """Test PASS verdict with score ≥ 0.7."""
        # Should not raise
        _validate_verdict_consistency(VerificationVerdict.PASS, 0.7)
        _validate_verdict_consistency(VerificationVerdict.PASS, 0.85)
        _validate_verdict_consistency(VerificationVerdict.PASS, 1.0)

    def test_retry_with_medium_score(self):
        """Test RETRY verdict with 0.5 ≤ score < 0.7."""
        # Should not raise
        _validate_verdict_consistency(VerificationVerdict.RETRY, 0.5)
        _validate_verdict_consistency(VerificationVerdict.RETRY, 0.6)
        _validate_verdict_consistency(VerificationVerdict.RETRY, 0.69)

    def test_fail_with_low_score(self):
        """Test FAIL verdict with score < 0.5."""
        # Should not raise
        _validate_verdict_consistency(VerificationVerdict.FAIL, 0.0)
        _validate_verdict_consistency(VerificationVerdict.FAIL, 0.3)
        _validate_verdict_consistency(VerificationVerdict.FAIL, 0.49)

    def test_invalid_pass_with_low_score(self):
        """Test PASS verdict with score < 0.5 raises error."""
        with pytest.raises(ValueError, match=r"Verdict.*PASS inconsistent"):
            _validate_verdict_consistency(VerificationVerdict.PASS, 0.3)

    def test_invalid_fail_with_medium_score(self):
        """Test FAIL verdict with medium score raises error."""
        with pytest.raises(ValueError, match=r"Verdict.*FAIL inconsistent"):
            _validate_verdict_consistency(VerificationVerdict.FAIL, 0.6)


class TestVerifyDecomposition:
    """Tests for verify_decomposition function."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        return MagicMock()

    @pytest.fixture
    def sample_decomposition(self):
        """Create sample decomposition for testing."""
        return {
            "goal": "Test goal",
            "subgoals": [
                {
                    "description": "Test subgoal",
                    "suggested_agent": "code-analyzer",
                    "is_critical": True,
                    "depends_on": [],
                }
            ],
            "execution_order": [{"phase": 1, "parallelizable": [0], "sequential": []}],
            "expected_tools": ["code_reader"],
        }

    def test_self_verification_pass(self, mock_llm_client, sample_decomposition):
        """Test self-verification with PASS verdict."""
        verification_response = {
            "completeness": 0.9,
            "consistency": 0.8,
            "groundedness": 0.85,
            "routability": 0.9,
            "overall_score": 0.875,
            "verdict": "PASS",
            "issues": [],
            "suggestions": [],
        }

        # generate_json returns dict directly, not LLMResponse
        mock_llm_client.generate_json.return_value = verification_response

        result = verify_decomposition(
            llm_client=mock_llm_client,
            query="Test query",
            decomposition=sample_decomposition,
            option=VerificationOption.SELF,
        )

        assert result.verdict == VerificationVerdict.PASS
        assert result.overall_score == 0.875
        assert result.completeness == 0.9
        assert result.option_used == VerificationOption.SELF

        # Verify LLM was called
        mock_llm_client.generate_json.assert_called_once()
        call_args = mock_llm_client.generate_json.call_args
        assert call_args.kwargs["temperature"] == 0.1

    def test_self_verification_retry(self, mock_llm_client, sample_decomposition):
        """Test self-verification with RETRY verdict."""
        verification_response = {
            "completeness": 0.6,
            "consistency": 0.7,
            "groundedness": 0.5,
            "routability": 0.6,
            "overall_score": 0.6,
            "verdict": "RETRY",
            "issues": ["Missing error handling", "Unclear dependencies"],
            "suggestions": ["Add error handling subgoal", "Clarify dependency order"],
        }

        # generate_json returns dict directly, not LLMResponse
        mock_llm_client.generate_json.return_value = verification_response

        result = verify_decomposition(
            llm_client=mock_llm_client,
            query="Test query",
            decomposition=sample_decomposition,
            option=VerificationOption.SELF,
        )

        assert result.verdict == VerificationVerdict.RETRY
        assert result.overall_score == 0.6
        assert len(result.issues) == 2
        assert len(result.suggestions) == 2

    def test_adversarial_verification_fail(self, mock_llm_client, sample_decomposition):
        """Test adversarial verification with FAIL verdict."""
        verification_response = {
            "completeness": 0.3,
            "consistency": 0.4,
            "groundedness": 0.2,
            "routability": 0.5,
            "overall_score": 0.32,
            "verdict": "FAIL",
            "critical_issues": ["Fundamental design flaw", "Missing critical subgoals"],
            "minor_issues": ["Poor agent choices"],
            "edge_cases": ["Doesn't handle concurrent access"],
            "suggestions": ["Redesign from scratch"],
        }

        # generate_json returns dict directly, not LLMResponse
        mock_llm_client.generate_json.return_value = verification_response

        result = verify_decomposition(
            llm_client=mock_llm_client,
            query="Test query",
            decomposition=sample_decomposition,
            option=VerificationOption.ADVERSARIAL,
        )

        assert result.verdict == VerificationVerdict.FAIL
        # Score is recalculated: 0.4*0.3 + 0.2*0.4 + 0.2*0.2 + 0.2*0.5 = 0.34
        assert abs(result.overall_score - 0.34) < 0.01
        assert result.option_used == VerificationOption.ADVERSARIAL
        # Adversarial combines all issue types
        assert len(result.issues) == 4  # critical + minor + edge_cases

    def test_context_summary_included(self, mock_llm_client, sample_decomposition):
        """Test context summary is included in prompt."""
        verification_response = {
            "completeness": 0.8,
            "consistency": 0.8,
            "groundedness": 0.8,
            "routability": 0.8,
            "overall_score": 0.8,
            "verdict": "PASS",
            "issues": [],
            "suggestions": [],
        }

        # generate_json returns dict directly, not LLMResponse
        mock_llm_client.generate_json.return_value = verification_response

        verify_decomposition(
            llm_client=mock_llm_client,
            query="Test query",
            decomposition=sample_decomposition,
            option=VerificationOption.SELF,
            context_summary="Available: 5 code chunks",
        )

        call_args = mock_llm_client.generate_json.call_args
        user_prompt = call_args.kwargs["prompt"]
        assert "Available: 5 code chunks" in user_prompt

    def test_available_agents_included(self, mock_llm_client, sample_decomposition):
        """Test available agents are included in prompt."""
        verification_response = {
            "completeness": 0.8,
            "consistency": 0.8,
            "groundedness": 0.8,
            "routability": 0.8,
            "overall_score": 0.8,
            "verdict": "PASS",
            "issues": [],
            "suggestions": [],
        }

        # generate_json returns dict directly, not LLMResponse
        mock_llm_client.generate_json.return_value = verification_response

        verify_decomposition(
            llm_client=mock_llm_client,
            query="Test query",
            decomposition=sample_decomposition,
            option=VerificationOption.ADVERSARIAL,
            available_agents=["code-analyzer", "test-runner"],
        )

        call_args = mock_llm_client.generate_json.call_args
        user_prompt = call_args.kwargs["prompt"]
        assert "code-analyzer" in user_prompt or "test-runner" in user_prompt

    def test_invalid_json_response(self, mock_llm_client, sample_decomposition):
        """Test handling of invalid JSON response."""
        # Return a non-dict to trigger type validation error
        mock_llm_client.generate_json.return_value = "Not a dict"

        with pytest.raises(ValueError, match="non-dict response"):
            verify_decomposition(
                llm_client=mock_llm_client,
                query="Test query",
                decomposition=sample_decomposition,
                option=VerificationOption.SELF,
            )

    def test_missing_required_fields(self, mock_llm_client, sample_decomposition):
        """Test handling of response with missing required fields."""
        incomplete_response = {
            "completeness": 0.8,
            # Missing other required fields
        }

        # generate_json returns dict directly
        mock_llm_client.generate_json.return_value = incomplete_response

        with pytest.raises(ValueError, match="missing required fields"):
            verify_decomposition(
                llm_client=mock_llm_client,
                query="Test query",
                decomposition=sample_decomposition,
                option=VerificationOption.SELF,
            )

    def test_invalid_score_range(self, mock_llm_client, sample_decomposition):
        """Test handling of scores outside valid range."""
        invalid_response = {
            "completeness": 1.5,  # Invalid: > 1.0
            "consistency": 0.8,
            "groundedness": 0.8,
            "routability": 0.8,
            "overall_score": 0.8,
            "verdict": "PASS",
            "issues": [],
            "suggestions": [],
        }

        # generate_json returns dict directly, not LLMResponse
        mock_llm_client.generate_json.return_value = invalid_response

        with pytest.raises(ValueError, match="Invalid .* score"):
            verify_decomposition(
                llm_client=mock_llm_client,
                query="Test query",
                decomposition=sample_decomposition,
                option=VerificationOption.SELF,
            )

    def test_invalid_verdict(self, mock_llm_client, sample_decomposition):
        """Test handling of invalid verdict value."""
        invalid_response = {
            "completeness": 0.8,
            "consistency": 0.8,
            "groundedness": 0.8,
            "routability": 0.8,
            "overall_score": 0.8,
            "verdict": "MAYBE",  # Invalid
            "issues": [],
            "suggestions": [],
        }

        # generate_json returns dict directly, not LLMResponse
        mock_llm_client.generate_json.return_value = invalid_response

        with pytest.raises(ValueError, match="Invalid verdict"):
            verify_decomposition(
                llm_client=mock_llm_client,
                query="Test query",
                decomposition=sample_decomposition,
                option=VerificationOption.SELF,
            )

    def test_score_calculation_correction(self, mock_llm_client, sample_decomposition):
        """Test that incorrect overall_score is corrected."""
        # LLM returns wrong overall_score calculation
        verification_response = {
            "completeness": 0.8,
            "consistency": 0.6,
            "groundedness": 0.9,
            "routability": 0.7,
            "overall_score": 0.99,  # Wrong! Should be 0.76
            "verdict": "PASS",
            "issues": [],
            "suggestions": [],
        }

        # generate_json returns dict directly, not LLMResponse
        mock_llm_client.generate_json.return_value = verification_response

        result = verify_decomposition(
            llm_client=mock_llm_client,
            query="Test query",
            decomposition=sample_decomposition,
            option=VerificationOption.SELF,
        )

        # Score should be corrected to proper calculation
        expected_score = 0.4 * 0.8 + 0.2 * 0.6 + 0.2 * 0.9 + 0.2 * 0.7
        assert abs(result.overall_score - expected_score) < 0.01
