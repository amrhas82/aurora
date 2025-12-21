"""Unit tests for verify phase."""

from unittest.mock import MagicMock, call, patch

import pytest

from aurora_reasoning.decompose import DecompositionResult
from aurora_reasoning.verify import (
    VerificationOption,
    VerificationResult,
    VerificationVerdict,
)
from aurora_soar.phases.verify import (
    VerifyPhaseResult,
    _generate_retry_feedback,
    _select_verification_option,
    verify_decomposition,
)


class TestSelectVerificationOption:
    """Tests for _select_verification_option function."""

    def test_simple_uses_self(self):
        """Test SIMPLE complexity uses self-verification."""
        option = _select_verification_option("SIMPLE")
        assert option == VerificationOption.SELF

    def test_medium_uses_self(self):
        """Test MEDIUM complexity uses self-verification."""
        option = _select_verification_option("MEDIUM")
        assert option == VerificationOption.SELF

    def test_complex_uses_adversarial(self):
        """Test COMPLEX complexity uses adversarial verification."""
        option = _select_verification_option("COMPLEX")
        assert option == VerificationOption.ADVERSARIAL

    def test_critical_uses_adversarial(self):
        """Test CRITICAL complexity uses adversarial verification."""
        option = _select_verification_option("CRITICAL")
        assert option == VerificationOption.ADVERSARIAL

    def test_case_insensitive(self):
        """Test complexity is case-insensitive."""
        option1 = _select_verification_option("medium")
        option2 = _select_verification_option("MEDIUM")
        option3 = _select_verification_option("Medium")
        assert option1 == option2 == option3 == VerificationOption.SELF

    def test_invalid_complexity(self):
        """Test invalid complexity raises error."""
        with pytest.raises(ValueError, match="Invalid complexity level"):
            _select_verification_option("INVALID")


class TestGenerateRetryFeedback:
    """Tests for _generate_retry_feedback function."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        from aurora_reasoning.llm_client import LLMResponse
        client = MagicMock()
        client.generate.return_value = LLMResponse(
            content="Fix the following issues:\n1. Add error handling\n2. Clarify dependencies",
            model="test-model",
            input_tokens=100,
            output_tokens=50,
            finish_reason="stop",
        )
        return client

    @pytest.fixture
    def sample_verification(self):
        """Create sample verification result."""
        return VerificationResult(
            completeness=0.6,
            consistency=0.7,
            groundedness=0.5,
            routability=0.6,
            overall_score=0.6,
            verdict=VerificationVerdict.RETRY,
            issues=["Missing error handling", "Unclear dependencies"],
            suggestions=["Add error handling subgoal", "Clarify execution order"],
            option_used=VerificationOption.SELF,
        )

    def test_generate_feedback(self, mock_llm_client, sample_verification):
        """Test feedback generation."""
        feedback = _generate_retry_feedback(
            llm_client=mock_llm_client,
            verification=sample_verification,
            attempt_number=1,
        )

        assert "Fix the following issues" in feedback
        assert "Add error handling" in feedback

        # Verify LLM was called
        mock_llm_client.generate.assert_called_once()
        call_args = mock_llm_client.generate.call_args
        assert call_args.kwargs["temperature"] == 0.3

    def test_verification_dict_in_prompt(self, mock_llm_client, sample_verification):
        """Test that verification dict is included in prompt."""
        feedback = _generate_retry_feedback(
            llm_client=mock_llm_client,
            verification=sample_verification,
            attempt_number=2,
        )

        call_args = mock_llm_client.generate.call_args
        user_prompt = call_args.kwargs["user_prompt"]
        assert "Attempt 2" in user_prompt
        assert "0.6" in user_prompt  # Score


class TestVerifyPhaseResult:
    """Tests for VerifyPhaseResult class."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        verification = VerificationResult(
            completeness=0.8,
            consistency=0.8,
            groundedness=0.8,
            routability=0.8,
            overall_score=0.8,
            verdict=VerificationVerdict.PASS,
            issues=[],
            suggestions=[],
            option_used=VerificationOption.SELF,
        )
        result = VerifyPhaseResult(
            verification=verification,
            retry_count=1,
            all_attempts=[verification],
            final_verdict="PASS",
            timing_ms=250.5,
        )

        data = result.to_dict()
        assert data["retry_count"] == 1
        assert data["final_verdict"] == "PASS"
        assert data["timing_ms"] == 250.5
        assert len(data["all_attempts"]) == 1


@patch("aurora_soar.phases.verify.reasoning_verify")
class TestVerifyDecomposition:
    """Tests for verify_decomposition function."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        return MagicMock()

    @pytest.fixture
    def sample_decomposition(self):
        """Create sample decomposition."""
        return DecompositionResult(
            goal="Test goal",
            subgoals=[
                {
                    "description": "Test subgoal",
                    "suggested_agent": "code-analyzer",
                    "is_critical": True,
                    "depends_on": [],
                }
            ],
            execution_order=[{"phase": 1, "parallelizable": [0], "sequential": []}],
            expected_tools=["code_reader"],
        )

    @pytest.fixture
    def passing_verification(self):
        """Create passing verification result."""
        return VerificationResult(
            completeness=0.9,
            consistency=0.8,
            groundedness=0.85,
            routability=0.9,
            overall_score=0.875,
            verdict=VerificationVerdict.PASS,
            issues=[],
            suggestions=[],
            option_used=VerificationOption.SELF,
        )

    @pytest.fixture
    def retry_verification(self):
        """Create retry verification result."""
        return VerificationResult(
            completeness=0.6,
            consistency=0.7,
            groundedness=0.5,
            routability=0.6,
            overall_score=0.6,
            verdict=VerificationVerdict.RETRY,
            issues=["Missing error handling"],
            suggestions=["Add error handling subgoal"],
            option_used=VerificationOption.SELF,
        )

    @pytest.fixture
    def failing_verification(self):
        """Create failing verification result."""
        return VerificationResult(
            completeness=0.3,
            consistency=0.4,
            groundedness=0.2,
            routability=0.5,
            overall_score=0.32,
            verdict=VerificationVerdict.FAIL,
            issues=["Fundamental design flaw"],
            suggestions=["Redesign from scratch"],
            option_used=VerificationOption.ADVERSARIAL,
        )

    def test_pass_on_first_attempt(self, mock_reasoning_verify, mock_llm_client, sample_decomposition, passing_verification):
        """Test verification passes on first attempt."""
        mock_reasoning_verify.return_value = passing_verification

        result = verify_decomposition(
            decomposition=sample_decomposition,
            complexity="MEDIUM",
            llm_client=mock_llm_client,
            query="Test query",
        )

        assert result.final_verdict == "PASS"
        assert result.retry_count == 0
        assert len(result.all_attempts) == 1
        assert result.verification.verdict == VerificationVerdict.PASS

        # Verify reasoning function was called once
        mock_reasoning_verify.assert_called_once()

    def test_fail_on_first_attempt(self, mock_reasoning_verify, mock_llm_client, sample_decomposition, failing_verification):
        """Test verification fails on first attempt."""
        mock_reasoning_verify.return_value = failing_verification

        result = verify_decomposition(
            decomposition=sample_decomposition,
            complexity="COMPLEX",
            llm_client=mock_llm_client,
            query="Test query",
        )

        assert result.final_verdict == "FAIL"
        assert result.retry_count == 0
        assert len(result.all_attempts) == 1
        assert result.verification.verdict == VerificationVerdict.FAIL

    @patch("aurora_soar.phases.verify.phase_decompose")
    @patch("aurora_soar.phases.verify._generate_retry_feedback")
    def test_retry_then_pass(
        self,
        mock_generate_feedback,
        mock_phase_decompose,
        mock_reasoning_verify,
        mock_llm_client,
        sample_decomposition,
        retry_verification,
        passing_verification,
    ):
        """Test verification retries and then passes."""
        from aurora_soar.phases.decompose import DecomposePhaseResult

        # First verification returns RETRY, second returns PASS
        mock_reasoning_verify.side_effect = [retry_verification, passing_verification]
        mock_generate_feedback.return_value = "Fix these issues"
        mock_phase_decompose.return_value = DecomposePhaseResult(
            decomposition=sample_decomposition,
            cached=False,
            query_hash="abc",
            timing_ms=100,
        )

        result = verify_decomposition(
            decomposition=sample_decomposition,
            complexity="MEDIUM",
            llm_client=mock_llm_client,
            query="Test query",
        )

        assert result.final_verdict == "PASS"
        assert result.retry_count == 1
        assert len(result.all_attempts) == 2

        # Verify retry feedback was generated
        mock_generate_feedback.assert_called_once()

        # Verify re-decomposition was called
        mock_phase_decompose.assert_called_once()
        call_args = mock_phase_decompose.call_args
        assert call_args.kwargs["retry_feedback"] == "Fix these issues"
        assert call_args.kwargs["use_cache"] is False

    @patch("aurora_soar.phases.verify.phase_decompose")
    @patch("aurora_soar.phases.verify._generate_retry_feedback")
    def test_max_retries_exhausted(
        self,
        mock_generate_feedback,
        mock_phase_decompose,
        mock_reasoning_verify,
        mock_llm_client,
        sample_decomposition,
        retry_verification,
    ):
        """Test that max retries are enforced."""
        from aurora_soar.phases.decompose import DecomposePhaseResult

        # Always return RETRY
        mock_reasoning_verify.return_value = retry_verification
        mock_generate_feedback.return_value = "Fix these issues"
        mock_phase_decompose.return_value = DecomposePhaseResult(
            decomposition=sample_decomposition,
            cached=False,
            query_hash="abc",
            timing_ms=100,
        )

        result = verify_decomposition(
            decomposition=sample_decomposition,
            complexity="MEDIUM",
            llm_client=mock_llm_client,
            query="Test query",
            max_retries=2,
        )

        # Should fail after max retries
        assert result.final_verdict == "FAIL"
        assert result.retry_count == 2
        assert len(result.all_attempts) == 3  # Initial + 2 retries

    def test_medium_uses_self_verification(self, mock_reasoning_verify, mock_llm_client, sample_decomposition, passing_verification):
        """Test MEDIUM complexity uses self-verification."""
        mock_reasoning_verify.return_value = passing_verification

        result = verify_decomposition(
            decomposition=sample_decomposition,
            complexity="MEDIUM",
            llm_client=mock_llm_client,
            query="Test query",
        )

        # Verify reasoning function was called with SELF option
        call_args = mock_reasoning_verify.call_args
        assert call_args.kwargs["option"] == VerificationOption.SELF

    def test_complex_uses_adversarial_verification(self, mock_reasoning_verify, mock_llm_client, sample_decomposition, passing_verification):
        """Test COMPLEX complexity uses adversarial verification."""
        mock_reasoning_verify.return_value = passing_verification

        result = verify_decomposition(
            decomposition=sample_decomposition,
            complexity="COMPLEX",
            llm_client=mock_llm_client,
            query="Test query",
        )

        # Verify reasoning function was called with ADVERSARIAL option
        call_args = mock_reasoning_verify.call_args
        assert call_args.kwargs["option"] == VerificationOption.ADVERSARIAL

    def test_context_summary_passed(self, mock_reasoning_verify, mock_llm_client, sample_decomposition, passing_verification):
        """Test context summary is passed through."""
        mock_reasoning_verify.return_value = passing_verification

        result = verify_decomposition(
            decomposition=sample_decomposition,
            complexity="MEDIUM",
            llm_client=mock_llm_client,
            query="Test query",
            context_summary="Available: 5 code chunks",
        )

        call_args = mock_reasoning_verify.call_args
        assert call_args.kwargs["context_summary"] == "Available: 5 code chunks"

    def test_available_agents_passed(self, mock_reasoning_verify, mock_llm_client, sample_decomposition, passing_verification):
        """Test available agents are passed through."""
        mock_reasoning_verify.return_value = passing_verification
        agents = ["code-analyzer", "test-runner"]

        result = verify_decomposition(
            decomposition=sample_decomposition,
            complexity="MEDIUM",
            llm_client=mock_llm_client,
            query="Test query",
            available_agents=agents,
        )

        call_args = mock_reasoning_verify.call_args
        assert call_args.kwargs["available_agents"] == agents

    def test_timing_recorded(self, mock_reasoning_verify, mock_llm_client, sample_decomposition, passing_verification):
        """Test that timing is recorded."""
        mock_reasoning_verify.return_value = passing_verification

        result = verify_decomposition(
            decomposition=sample_decomposition,
            complexity="MEDIUM",
            llm_client=mock_llm_client,
            query="Test query",
        )

        assert result.timing_ms > 0
