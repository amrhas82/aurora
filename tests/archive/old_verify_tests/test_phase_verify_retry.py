"""
Unit tests for Phase 4 verification retry logic.

Tests the retry loop when decompositions fail verification.
"""

from aurora_reasoning.decompose import DecompositionResult
from aurora_reasoning.llm_client import LLMClient
from aurora_soar.phases.verify import verify_decomposition


class MockRetryLLMClient(LLMClient):
    """Mock LLM for testing retry scenarios."""

    def __init__(self, fail_first: bool = True, always_retry: bool = False):
        """Initialize mock.

        Args:
            fail_first: If True, first verification fails, second passes
            always_retry: If True, all verifications return RETRY (for max retry test)
        """
        self.fail_first = fail_first
        self.always_retry = always_retry
        self.call_count = 0
        self.verification_call_count = 0

    @property
    def default_model(self) -> str:
        """Get default model."""
        return "mock"

    def count_tokens(self, text: str) -> int:
        """Count tokens."""
        return 10

    def generate(self, prompt: str, system: str = "", **kwargs):
        """Generate text response."""
        from aurora_reasoning.llm_client import LLMResponse

        # For feedback generation (returns LLMResponse)
        return LLMResponse(
            content="Fix the issues",
            model="mock",
            input_tokens=10,
            output_tokens=5,
            finish_reason="stop",
        )

    def generate_json(
        self, prompt: str, system: str = "", schema: dict | None = None, **kwargs
    ) -> dict:
        """Generate JSON response."""
        self.call_count += 1

        # Check if this is a verification request (has "completeness" in system prompt or prompt contains verification keywords)
        # or a decomposition request (has "goal" and "subgoals" keywords)
        is_verification = "completeness" in system.lower() or "groundedness" in system.lower()

        if is_verification:
            # Track verification calls separately
            self.verification_call_count += 1

            if self.always_retry:
                # Always return RETRY (for max retry test)
                return {
                    "completeness": 0.5,
                    "consistency": 0.6,
                    "groundedness": 0.7,
                    "routability": 0.5,
                    "overall_score": 0.575,
                    "verdict": "RETRY",
                    "issues": ["Still incomplete"],
                    "suggestions": [],
                }
            if self.fail_first and self.verification_call_count == 1:
                # First verification attempt fails with RETRY verdict
                return {
                    "completeness": 0.5,
                    "consistency": 0.7,
                    "groundedness": 0.8,
                    "routability": 0.6,
                    "overall_score": 0.6,
                    "verdict": "RETRY",
                    "issues": ["Incomplete decomposition"],
                    "suggestions": [],
                }
            # Pass on subsequent attempts or if not failing first
            return {
                "completeness": 0.9,
                "consistency": 0.9,
                "groundedness": 0.9,
                "routability": 0.9,
                "overall_score": 0.9,
                "verdict": "PASS",
                "issues": [],
                "suggestions": [],
            }
        # Decomposition request (for retry loop)
        return {
            "goal": "Test goal",
            "subgoals": [
                {
                    "description": "Test refined",
                    "suggested_agent": "test",
                    "is_critical": True,
                    "depends_on": [],
                }
            ],
            "execution_order": [{"phase": 1, "parallelizable": [0], "sequential": []}],
            "expected_tools": ["test-tool"],
        }


class TestVerificationRetry:
    """Test verification retry loop."""

    def test_retry_triggered_on_low_score(self):
        """Test that retry is triggered when score is below threshold."""
        llm_client = MockRetryLLMClient(fail_first=True)

        decomposition = DecompositionResult(
            goal="Test goal",
            subgoals=[
                {
                    "description": "Test",
                    "suggested_agent": "test",
                    "is_critical": True,
                    "depends_on": [],
                }
            ],
            execution_order=[{"phase": 1, "parallelizable": [0], "sequential": []}],
            expected_tools=["test-tool"],
        )

        # Verify with retry
        result = verify_decomposition(
            query="Test query",
            decomposition=decomposition,
            llm_client=llm_client,
            complexity="COMPLEX",
            max_retries=2,
        )

        # Should have retried and eventually passed
        assert result.retry_count >= 1, "Should have retried"
        assert result.final_verdict == "PASS", "Should pass after retry"
        assert len(result.all_attempts) >= 2, "Should have multiple attempts"

    def test_no_retry_on_pass(self):
        """Test that no retry occurs when first attempt passes."""
        llm_client = MockRetryLLMClient(fail_first=False)

        decomposition = DecompositionResult(
            goal="Test goal",
            subgoals=[
                {
                    "description": "Test",
                    "suggested_agent": "test",
                    "is_critical": True,
                    "depends_on": [],
                }
            ],
            execution_order=[{"phase": 1, "parallelizable": [0], "sequential": []}],
            expected_tools=["test-tool"],
        )

        # Verify without retry needed
        result = verify_decomposition(
            query="Test query",
            decomposition=decomposition,
            llm_client=llm_client,
            complexity="COMPLEX",
            max_retries=2,
        )

        # Should pass without retry
        assert result.retry_count == 0, "Should not retry when passing"
        assert result.final_verdict == "PASS", "Should pass"
        assert len(result.all_attempts) == 1, "Should have only one attempt"

    def test_max_retries_respected(self):
        """Test that max retries limit is respected."""
        llm_client = MockRetryLLMClient(fail_first=True, always_retry=True)

        decomposition = DecompositionResult(
            goal="Test goal",
            subgoals=[
                {
                    "description": "Test",
                    "suggested_agent": "test",
                    "is_critical": True,
                    "depends_on": [],
                }
            ],
            execution_order=[{"phase": 1, "parallelizable": [0], "sequential": []}],
            expected_tools=["test-tool"],
        )

        # Verify with max retries
        result = verify_decomposition(
            query="Test query",
            decomposition=decomposition,
            llm_client=llm_client,
            complexity="CRITICAL",
            max_retries=2,
        )

        # Should stop at max retries
        assert result.retry_count == 2, "Should respect max retries"
        assert len(result.all_attempts) == 3, "Should have initial + 2 retry attempts"
