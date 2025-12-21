"""
Unit tests for Phase 4 verification retry logic.

Tests the retry loop when decompositions fail verification.
"""

import pytest

from aurora_reasoning import verify
from aurora_reasoning.llm_client import LLMClient


class MockRetryLLMClient(LLMClient):
    """Mock LLM for testing retry scenarios."""

    def __init__(self, fail_first: bool = True):
        """Initialize mock.

        Args:
            fail_first: If True, first verification fails, second passes
        """
        self.fail_first = fail_first
        self.call_count = 0

    @property
    def default_model(self) -> str:
        """Get default model."""
        return "mock"

    def count_tokens(self, text: str) -> int:
        """Count tokens."""
        return 10

    def generate(self, prompt: str, system: str = "", **kwargs) -> str:
        """Generate verification response."""
        self.call_count += 1

        if "verify" in prompt.lower() or "score" in prompt.lower():
            if self.fail_first and self.call_count == 1:
                # First attempt fails
                return """
{
  "completeness": 0.5,
  "consistency": 0.7,
  "groundedness": 0.8,
  "routability": 0.6,
  "overall_score": 0.6,
  "verdict": "RETRY",
  "issues": ["Incomplete decomposition"]
}
"""
            else:
                # Subsequent attempts pass
                return """
{
  "completeness": 0.9,
  "consistency": 0.9,
  "groundedness": 0.9,
  "routability": 0.9,
  "overall_score": 0.9,
  "verdict": "PASS",
  "issues": []
}
"""

        # Decomposition request
        return """
{
  "subgoals": [{"id": "sg1", "description": "Test", "suggested_agent": "test"}],
  "execution_order": ["sg1"]
}
"""

    def generate_json(self, prompt: str, system: str = "", schema: dict | None = None, **kwargs) -> dict:
        """Generate JSON."""
        import json
        return json.loads(self.generate(prompt, system, **kwargs))


class TestVerificationRetry:
    """Test verification retry loop."""

    def test_retry_triggered_on_low_score(self):
        """Test that retry is triggered when score is below threshold."""
        llm_client = MockRetryLLMClient(fail_first=True)

        decomposition = {
            "subgoals": [{"id": "sg1", "description": "Test", "suggested_agent": "test"}],
            "execution_order": ["sg1"]
        }

        # Verify with retry
        result = verify.verify_decomposition(
            query="Test query",
            decomposition=decomposition,
            chunks=[],
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

        decomposition = {
            "subgoals": [{"id": "sg1", "description": "Test", "suggested_agent": "test"}],
            "execution_order": ["sg1"]
        }

        # Verify without retry needed
        result = verify.verify_decomposition(
            query="Test query",
            decomposition=decomposition,
            chunks=[],
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
        llm_client = MockRetryLLMClient(fail_first=True)
        # Force all attempts to fail
        llm_client.fail_first = True

        decomposition = {
            "subgoals": [{"id": "sg1", "description": "Test", "suggested_agent": "test"}],
            "execution_order": ["sg1"]
        }

        # Verify with max retries
        result = verify.verify_decomposition(
            query="Test query",
            decomposition=decomposition,
            chunks=[],
            llm_client=llm_client,
            complexity="CRITICAL",
            max_retries=2,
        )

        # Should stop at max retries
        assert result.retry_count == 2, "Should respect max retries"
        assert len(result.all_attempts) == 3, "Should have initial + 2 retry attempts"
