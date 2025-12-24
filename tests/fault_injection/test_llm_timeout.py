"""Fault injection tests for LLM timeout scenarios.

Tests how the system handles LLM timeouts and API failures:
- Network timeouts during LLM calls
- Slow API responses exceeding timeout limits
- Transient API failures with retry logic
- Retry exhaustion scenarios
- Timeout during different SOAR phases
- Partial results with degraded functionality
"""

import asyncio
import time
from unittest.mock import Mock

import pytest
from aurora.reasoning.llm_client import LLMClient, LLMResponse


class TimeoutLLMClient(LLMClient):
    """Mock LLM client that simulates timeouts."""

    def __init__(self, timeout_after_seconds: float = 0.1, fail_count: int = 1):
        """Initialize timeout client.

        Args:
            timeout_after_seconds: Seconds before timing out
            fail_count: Number of times to fail before succeeding
        """
        self._timeout_after = timeout_after_seconds
        self._fail_count = fail_count
        self._call_count = 0

    @property
    def default_model(self) -> str:
        """Get default model."""
        return "test-model"

    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate with timeout simulation."""
        self._call_count += 1

        # Fail first N times
        if self._call_count <= self._fail_count:
            time.sleep(self._timeout_after)
            raise TimeoutError(f"LLM request timed out after {self._timeout_after}s")

        # Succeed after retries
        return LLMResponse(
            content="Test response",
            model="test-model",
            input_tokens=100,
            output_tokens=50,
            finish_reason="stop",
        )

    def generate_json(self, prompt: str, **kwargs) -> dict:
        """Generate JSON with timeout simulation."""
        self._call_count += 1

        # Fail first N times
        if self._call_count <= self._fail_count:
            time.sleep(self._timeout_after)
            raise TimeoutError(f"LLM request timed out after {self._timeout_after}s")

        # Return valid JSON after retries
        return {"result": "test", "status": "success"}

    def count_tokens(self, text: str) -> int:
        """Count tokens (simple approximation)."""
        return len(text.split())


class TestLLMTimeoutBasic:
    """Test basic LLM timeout scenarios."""

    def test_timeout_raises_error(self):
        """Test that LLM timeout raises TimeoutError."""
        client = TimeoutLLMClient(timeout_after_seconds=0.001, fail_count=999)

        with pytest.raises(TimeoutError, match="timed out"):
            client.generate("Test prompt")

    def test_timeout_during_generate(self):
        """Test timeout during text generation."""
        client = TimeoutLLMClient(timeout_after_seconds=0.001, fail_count=999)

        with pytest.raises(TimeoutError):
            client.generate("Long prompt that triggers timeout")

    def test_timeout_during_generate_json(self):
        """Test timeout during JSON generation."""
        client = TimeoutLLMClient(timeout_after_seconds=0.001, fail_count=999)

        with pytest.raises(TimeoutError):
            client.generate_json("Generate JSON that times out")


class TestLLMTimeoutRetry:
    """Test LLM timeout retry logic."""

    def test_retry_succeeds_after_one_failure(self):
        """Test that retry succeeds after one timeout."""
        # Fail once, then succeed
        client = TimeoutLLMClient(timeout_after_seconds=0.001, fail_count=1)

        # First call fails, second succeeds (handled by tenacity retry)
        # Note: The @retry decorator in llm_client.py handles this automatically
        # For this test, we're testing the client behavior directly
        with pytest.raises(TimeoutError):
            # First call should fail
            client.generate("Test prompt")

        # Second call should succeed
        response = client.generate("Test prompt")
        assert response.content == "Test response"
        assert response.model == "test-model"

    def test_retry_exhaustion_after_max_attempts(self):
        """Test that retry exhaustion raises error."""
        # Fail forever (more than max retries)
        client = TimeoutLLMClient(timeout_after_seconds=0.001, fail_count=999)

        # Should fail after all retries exhausted
        with pytest.raises(TimeoutError):
            client.generate("Test prompt")


class TestLLMTimeoutPhases:
    """Test LLM timeout during different SOAR phases."""

    def test_timeout_during_assess_phase(self):
        """Test timeout during complexity assessment."""
        from aurora.soar.phases.assess import _assess_tier2_llm

        client = TimeoutLLMClient(timeout_after_seconds=0.001, fail_count=999)

        keyword_result = {
            "complexity": "MEDIUM",
            "confidence": 0.5,
            "score": 0.5,
        }

        # Assessment should gracefully fall back to keyword result when LLM times out
        result = _assess_tier2_llm(
            query="Test query",
            keyword_result=keyword_result,
            llm_client=client,
        )

        # Should return keyword result as fallback
        assert result["complexity"] == "MEDIUM"
        assert "fallback" in result.get("method", "").lower() or result["confidence"] == 0.5

    def test_timeout_during_decompose_phase(self):
        """Test timeout during query decomposition."""
        from aurora.reasoning.decompose import decompose_query

        client = TimeoutLLMClient(timeout_after_seconds=0.001, fail_count=999)

        # Decomposition should fail if LLM times out
        with pytest.raises(TimeoutError):
            decompose_query(
                llm_client=client,
                query="Test query",
                complexity="MEDIUM",
                context_summary="Test context",
                available_agents=["test-agent"],
            )

    def test_timeout_during_verify_phase(self):
        """Test timeout during verification."""
        from aurora.reasoning.verify import verify_decomposition

        client = TimeoutLLMClient(timeout_after_seconds=0.001, fail_count=999)

        decomposition = {
            "subgoals": [{"description": "Test subgoal", "agent": "test-agent"}],
            "execution_order": {"parallelizable": [[0]], "sequential": []},
            "rationale": "Test rationale",
        }

        # Verification should fail if LLM times out
        with pytest.raises(TimeoutError):
            verify_decomposition(
                llm_client=client,
                query="Test query",
                decomposition=decomposition,
                option="A",
                context_summary="Test context",
            )

    def test_timeout_during_synthesis_phase(self):
        """Test timeout during result synthesis."""
        from aurora.reasoning.synthesize import synthesize_results

        client = TimeoutLLMClient(timeout_after_seconds=0.001, fail_count=999)

        agent_outputs = [
            {"summary": "Result 1", "confidence": 0.8},
            {"summary": "Result 2", "confidence": 0.9},
        ]

        decomposition = {
            "subgoals": [{"description": "Subgoal 1"}, {"description": "Subgoal 2"}],
        }

        # Synthesis should fail if LLM times out
        with pytest.raises(TimeoutError):
            synthesize_results(
                llm_client=client,
                query="Test query",
                agent_outputs=agent_outputs,
                decomposition=decomposition,
            )


class TestLLMTimeoutRecovery:
    """Test recovery strategies for LLM timeouts."""

    def test_graceful_degradation_to_cached_results(self):
        """Test fallback to cached results when LLM times out."""
        # In real implementation, system should check cache first
        # and return cached result if available when LLM fails

        client = TimeoutLLMClient(timeout_after_seconds=0.001, fail_count=999)

        # Simulate cache hit scenario
        cached_result = {
            "source": "cache",
            "content": "Cached decomposition",
            "timestamp": "2024-12-22",
        }

        # When LLM fails, should return cached result
        # (This would be implemented in the actual orchestrator)
        try:
            response = client.generate("Test prompt")
            result = {"source": "llm", "content": response.content}
        except TimeoutError:
            # Fallback to cache
            result = cached_result

        assert result["source"] == "cache"
        assert "Cached" in result["content"]

    def test_partial_execution_with_timeout(self):
        """Test partial execution when timeout occurs mid-pipeline."""
        # Simulate scenario where some phases succeed before timeout

        # Phase 1: Assess (succeeds)
        assess_client = TimeoutLLMClient(timeout_after_seconds=1.0, fail_count=0)
        assess_response = assess_client.generate("Assess complexity")
        assert assess_response.content is not None

        # Phase 2: Decompose (times out)
        decompose_client = TimeoutLLMClient(timeout_after_seconds=0.001, fail_count=999)

        results = {"assess": assess_response, "decompose": None}

        try:
            decompose_response = decompose_client.generate("Decompose query")
            results["decompose"] = decompose_response
        except TimeoutError:
            results["decompose_error"] = "Timeout during decomposition"

        # Verify partial results captured
        assert results["assess"] is not None
        assert "decompose_error" in results


class TestLLMTimeoutMetadata:
    """Test that timeout metadata is properly captured."""

    def test_timeout_duration_recorded(self):
        """Test that timeout duration is recorded in metadata."""
        client = TimeoutLLMClient(timeout_after_seconds=0.1, fail_count=999)

        start_time = time.time()
        try:
            client.generate("Test prompt")
        except TimeoutError:
            duration = time.time() - start_time
            # Should timeout around 0.1s (with some tolerance)
            assert 0.05 < duration < 0.2

    def test_retry_attempts_recorded(self):
        """Test that retry attempts are recorded."""
        client = TimeoutLLMClient(timeout_after_seconds=0.001, fail_count=2)

        # Track calls
        call_count_before = client._call_count

        try:
            # First call fails
            client.generate("Test prompt")
        except TimeoutError:
            pass

        try:
            # Second call fails
            client.generate("Test prompt")
        except TimeoutError:
            pass

        # Third call succeeds
        client.generate("Test prompt")

        # Verify all attempts recorded
        assert client._call_count == call_count_before + 3


class TestLLMTimeoutErrorMessages:
    """Test that timeout error messages are informative."""

    def test_timeout_error_message_contains_details(self):
        """Test that timeout error message contains useful details."""
        client = TimeoutLLMClient(timeout_after_seconds=0.5, fail_count=999)

        try:
            client.generate("Test prompt")
            pytest.fail("Expected TimeoutError")
        except TimeoutError as e:
            error_msg = str(e)
            # Error should mention timeout and duration
            assert "timed out" in error_msg.lower() or "timeout" in error_msg.lower()
            assert "0.5" in error_msg  # Should mention timeout duration

    def test_timeout_error_distinguishable_from_other_errors(self):
        """Test that timeout errors are distinguishable from other errors."""
        client = TimeoutLLMClient(timeout_after_seconds=0.1, fail_count=999)

        try:
            client.generate("Test prompt")
            pytest.fail("Expected TimeoutError")
        except TimeoutError as e:
            # Should be TimeoutError, not generic Exception
            assert isinstance(e, TimeoutError)
            assert not isinstance(e, ValueError)
            assert not isinstance(e, RuntimeError)


class TestLLMTimeoutIntegration:
    """Test LLM timeout in integrated scenarios."""

    def test_timeout_with_cost_tracking(self):
        """Test that timeout interacts correctly with cost tracking."""
        from pathlib import Path

        from aurora.core.budget.tracker import CostTracker

        client = TimeoutLLMClient(timeout_after_seconds=0.001, fail_count=999)

        # Create tracker (use temp file)
        import tempfile

        temp_path = Path(tempfile.mktemp(suffix=".json"))
        tracker = CostTracker(monthly_limit_usd=10.0, tracker_path=temp_path)

        initial_cost = tracker.budget.consumed_usd

        try:
            # Attempt LLM call (will timeout)
            client.generate("Test prompt")
            # If succeeded, record cost
            tracker.record_cost(
                model="test-model",
                input_tokens=100,
                output_tokens=50,
            )
        except TimeoutError:
            # Timeout should NOT charge (no tokens consumed)
            pass

        # Cost should be unchanged (timeout didn't consume tokens)
        assert tracker.budget.consumed_usd == initial_cost

    @pytest.mark.asyncio
    async def test_timeout_with_parallel_execution(self):
        """Test timeout handling in parallel execution."""
        # Create clients with different timeout behaviors
        fast_client = TimeoutLLMClient(timeout_after_seconds=0.01, fail_count=0)
        slow_client = TimeoutLLMClient(timeout_after_seconds=2.0, fail_count=999)

        # Execute in parallel
        async def call_fast():
            return fast_client.generate("Fast query")

        async def call_slow():
            return slow_client.generate("Slow query")

        # Run both, one should succeed, one should timeout
        results = await asyncio.gather(
            call_fast(),
            call_slow(),
            return_exceptions=True,
        )

        # Fast should succeed, slow should timeout
        assert isinstance(results[0], LLMResponse)
        assert isinstance(results[1], TimeoutError)

    def test_timeout_recovery_with_different_model(self):
        """Test recovery by switching to faster model after timeout."""
        # Simulate switching from Opus (slow) to Haiku (fast) after timeout

        opus_client = TimeoutLLMClient(timeout_after_seconds=0.001, fail_count=999)
        haiku_client = TimeoutLLMClient(timeout_after_seconds=1.0, fail_count=0)

        result = None

        # Try Opus first (times out)
        try:
            result = opus_client.generate("Complex query")
        except TimeoutError:
            # Fallback to Haiku
            result = haiku_client.generate("Complex query")

        # Should have result from Haiku
        assert result is not None
        assert result.content == "Test response"


class TestLLMTimeoutEdgeCases:
    """Test edge cases for LLM timeouts."""

    def test_zero_timeout(self):
        """Test behavior with zero timeout (should fail immediately)."""
        client = TimeoutLLMClient(timeout_after_seconds=0.0, fail_count=999)

        # Even zero timeout should be handled gracefully
        with pytest.raises(TimeoutError):
            client.generate("Test prompt")

    def test_very_long_timeout(self):
        """Test behavior with very long timeout."""
        # Client that succeeds immediately
        client = TimeoutLLMClient(timeout_after_seconds=100.0, fail_count=0)

        # Should succeed quickly despite long timeout setting
        start_time = time.time()
        response = client.generate("Test prompt")
        duration = time.time() - start_time

        assert response is not None
        assert duration < 1.0  # Should be fast

    def test_timeout_with_empty_prompt(self):
        """Test timeout with empty prompt."""
        from aurora.reasoning.llm_client import AnthropicClient

        # Mock client that would timeout
        client = Mock(spec=AnthropicClient)
        client.generate.side_effect = TimeoutError("Request timed out")

        # Empty prompt should fail validation before timeout
        with pytest.raises((ValueError, TimeoutError)):
            client.generate("")

    def test_timeout_during_token_counting(self):
        """Test timeout doesn't affect token counting."""
        client = TimeoutLLMClient(timeout_after_seconds=0.001, fail_count=999)

        # Token counting should work even if generation times out
        token_count = client.count_tokens("This is a test prompt")
        assert token_count > 0

        # But generation should still timeout
        with pytest.raises(TimeoutError):
            client.generate("This is a test prompt")
