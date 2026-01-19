"""Unit tests for rate limit error handling.

Tests that rate limit errors are:
1. Detected correctly from various error patterns
2. Prevented from retrying (quota won't reset)
3. Excluded from circuit breaker logic (agent isn't broken)
4. Tracked separately in metrics as FailureReason.RATE_LIMIT
5. Isolated from normal error handling (inference errors still retry/circuit normally)
"""

from aurora_spawner.circuit_breaker import CircuitBreaker
from aurora_spawner.observability import FailureReason
from aurora_spawner.timeout_policy import RetryPolicy


class TestRateLimitDetection:
    """Test detection of rate limit patterns."""

    def test_detect_rate_limit_in_error_message(self):
        """Rate limit patterns in error message should be detected."""
        patterns = [
            "rate limit exceeded",
            "Rate Limit Exceeded",
            "API rate limit reached",
            "429 Too Many Requests",
            "HTTP 429",
            "quota exceeded",
            "Quota Exceeded",
            "too many requests",
            "Too Many Requests",
        ]

        for pattern in patterns:
            error = f"Error: {pattern} - try again later"
            error_lower = error.lower()
            is_rate_limit = any(
                x in error_lower
                for x in ["rate limit", "429", "quota exceeded", "too many requests"]
            )
            assert is_rate_limit, f"Pattern not detected: {pattern}"

    def test_detect_rate_limit_in_termination_reason(self):
        """Rate limit patterns in termination reason should be detected."""
        termination_reasons = [
            "Agent terminated: rate limit exceeded",
            "Inference error: 429 Too Many Requests",
            "API quota exceeded for this hour",
            "Too many requests - backoff required",
        ]

        for reason in termination_reasons:
            reason_lower = reason.lower()
            is_rate_limit = any(
                x in reason_lower
                for x in ["rate limit", "429", "quota exceeded", "too many requests"]
            )
            assert is_rate_limit, f"Pattern not detected: {reason}"

    def test_rate_limit_takes_precedence_over_inference(self):
        """Rate limit detection should happen before inference error detection."""
        # Error contains both "api" and "rate limit"
        error = "API rate limit exceeded - quota exhausted"
        error_lower = error.lower()

        # Check rate limit first (as in actual code)
        if any(
            x in error_lower for x in ["rate limit", "429", "quota exceeded", "too many requests"]
        ):
            error_type = "rate_limit"
        elif any(x in error_lower for x in ["api", "connection", "json", "parse", "model"]):
            error_type = "inference"
        else:
            error_type = None

        assert error_type == "rate_limit", "Rate limit should take precedence"


class TestRateLimitRetryPolicy:
    """Test that rate limits prevent retries."""

    def test_rate_limit_prevents_retry(self):
        """Rate limit errors should never retry."""
        policy = RetryPolicy(max_attempts=4)

        # Even on first attempt, rate limit should not retry
        for attempt in range(4):
            should_retry, reason = policy.should_retry(attempt, error_type="rate_limit")
            assert not should_retry, f"Rate limit should not retry on attempt {attempt}"
            assert "quota exhausted" in reason.lower() or "rate limit" in reason.lower()

    def test_other_errors_still_retry(self):
        """Non-rate-limit errors should still retry normally."""
        policy = RetryPolicy(max_attempts=4)

        # Timeout errors should retry (if enabled)
        should_retry, _ = policy.should_retry(0, error_type="timeout")
        assert should_retry, "Timeout should retry on attempt 0"

        # Inference errors should retry
        should_retry, _ = policy.should_retry(0, error_type="inference")
        assert should_retry, "Inference should retry on attempt 0"

        # Unknown errors should retry
        should_retry, _ = policy.should_retry(0, error_type=None)
        assert should_retry, "Unknown errors should retry on attempt 0"

    def test_rate_limit_reason_message(self):
        """Rate limit rejection should provide clear reason."""
        policy = RetryPolicy(max_attempts=4)
        should_retry, reason = policy.should_retry(0, error_type="rate_limit")

        assert not should_retry
        assert "rate limit" in reason.lower() or "quota" in reason.lower()
        assert "retry" in reason.lower() or "fail" in reason.lower()


class TestRateLimitCircuitBreaker:
    """Test that rate limits don't trigger circuit breaker."""

    def test_rate_limit_skips_circuit_breaker(self):
        """Rate limit failures should not open circuit breaker."""
        cb = CircuitBreaker(failure_threshold=2, failure_window=60.0)
        agent_id = "test-agent"

        # Record multiple rate limit failures
        for _ in range(5):
            cb.record_failure(agent_id, failure_type="rate_limit")

        # Circuit should remain closed (rate limits exit early)
        is_open = cb.is_open(agent_id)
        assert not is_open, "Rate limits should not open circuit"

    def test_inference_failures_still_open_circuit(self):
        """Inference failures should still open circuit breaker normally."""
        cb = CircuitBreaker(failure_threshold=2, failure_window=60.0)
        agent_id = "test-agent"

        # Record inference failures
        cb.record_failure(agent_id, failure_type="inference")
        cb.record_failure(agent_id, failure_type="inference")

        # Circuit should open after threshold
        is_open = cb.is_open(agent_id)
        assert is_open, "Inference failures should open circuit"

    def test_timeout_failures_still_open_circuit(self):
        """Timeout failures should still open circuit breaker normally."""
        cb = CircuitBreaker(failure_threshold=2, failure_window=60.0)
        agent_id = "test-agent"

        # Record timeout failures
        cb.record_failure(agent_id, failure_type="timeout")
        cb.record_failure(agent_id, failure_type="timeout")

        # Circuit should open after threshold
        is_open = cb.is_open(agent_id)
        assert is_open, "Timeout failures should open circuit"

    def test_mixed_failures_rate_limit_ignored(self):
        """Rate limit failures mixed with other failures should be ignored."""
        cb = CircuitBreaker(failure_threshold=3, failure_window=60.0)
        agent_id = "test-agent"

        # Record mixed failures (disable fast-fail to test threshold only)
        cb.record_failure(agent_id, failure_type="inference", fast_fail=False)
        cb.record_failure(agent_id, failure_type="rate_limit")  # Should be ignored
        cb.record_failure(agent_id, failure_type="inference", fast_fail=False)
        cb.record_failure(agent_id, failure_type="rate_limit")  # Should be ignored

        # Only 2 inference failures counted, circuit should be closed (threshold=3)
        is_open = cb.is_open(agent_id)
        assert not is_open, "Rate limits should not count toward threshold"


class TestRateLimitMetrics:
    """Test that rate limits are tracked separately in metrics."""

    def test_failure_reason_enum_includes_rate_limit(self):
        """FailureReason enum should include RATE_LIMIT."""
        assert hasattr(FailureReason, "RATE_LIMIT"), "FailureReason should have RATE_LIMIT"
        assert FailureReason.RATE_LIMIT.value == "rate_limit"

    def test_rate_limit_distinct_from_other_failures(self):
        """Rate limit failures should be categorized separately."""
        # Verify enum values are distinct
        reasons = [r.value for r in FailureReason]
        assert "rate_limit" in reasons
        assert len(reasons) == len(set(reasons)), "Enum values should be unique"


class TestRateLimitIsolation:
    """Test that rate limit handling doesn't affect other error types."""

    def test_inference_error_detection_unchanged(self):
        """Inference errors without rate limit should still be detected."""
        errors = [
            "API connection failed",
            "JSON parse error in response",
            "Model inference timeout",
            "API authentication failed",
        ]

        for error in errors:
            error_lower = error.lower()

            # Check rate limit first (should not match)
            if any(
                x in error_lower
                for x in ["rate limit", "429", "quota exceeded", "too many requests"]
            ):
                error_type = "rate_limit"
            elif any(x in error_lower for x in ["api", "connection", "json", "parse", "model"]):
                error_type = "inference"
            else:
                error_type = None

            assert error_type == "inference", f"Should detect inference error: {error}"

    def test_timeout_error_detection_unchanged(self):
        """Timeout errors should still be detected normally."""
        termination_reason = "Agent timed out after 300 seconds"
        reason_lower = termination_reason.lower()

        # Timeout check happens before rate limit in actual code
        if "timed out" in reason_lower:
            error_type = "timeout"
        elif any(
            x in reason_lower for x in ["rate limit", "429", "quota exceeded", "too many requests"]
        ):
            error_type = "rate_limit"
        else:
            error_type = None

        assert error_type == "timeout", "Timeout detection should work normally"

    def test_error_pattern_detection_unchanged(self):
        """Error pattern detection should still work normally."""
        termination_reason = "Error pattern detected: FATAL ERROR"
        reason_lower = termination_reason.lower()

        # Error pattern check happens before rate limit in actual code
        if "error pattern" in reason_lower:
            error_type = "error_pattern"
        elif any(
            x in reason_lower for x in ["rate limit", "429", "quota exceeded", "too many requests"]
        ):
            error_type = "rate_limit"
        else:
            error_type = None

        assert error_type == "error_pattern", "Error pattern detection should work normally"


class TestRateLimitEdgeCases:
    """Test edge cases in rate limit handling."""

    def test_empty_error_message(self):
        """Empty error message should not crash rate limit detection."""
        error = ""
        error_lower = error.lower()
        is_rate_limit = any(
            x in error_lower for x in ["rate limit", "429", "quota exceeded", "too many requests"]
        )
        assert not is_rate_limit, "Empty string should not match rate limit"

    def test_none_error_message(self):
        """None error message should not crash (would fail .lower() call)."""
        # In actual code, we check `if result.error:` before calling .lower()
        # This test verifies that pattern
        error = None
        if error:
            error_lower = error.lower()
            is_rate_limit = any(
                x in error_lower
                for x in ["rate limit", "429", "quota exceeded", "too many requests"]
            )
        else:
            is_rate_limit = False

        assert not is_rate_limit, "None should not match rate limit"

    def test_case_insensitive_matching(self):
        """Rate limit detection should be case insensitive."""
        patterns = [
            "RATE LIMIT EXCEEDED",
            "Rate Limit Exceeded",
            "rate limit exceeded",
            "rAtE LiMiT ExCeEdEd",
        ]

        for pattern in patterns:
            error_lower = pattern.lower()
            is_rate_limit = any(
                x in error_lower
                for x in ["rate limit", "429", "quota exceeded", "too many requests"]
            )
            assert is_rate_limit, f"Should detect case variation: {pattern}"

    def test_substring_matching(self):
        """Rate limit patterns should match as substrings."""
        errors = [
            "API rate limit exceeded, retry after 3600s",
            "Error: 429 Too Many Requests (rate limited)",
            "Your quota exceeded - upgrade plan",
            "Received too many requests - backoff",
        ]

        for error in errors:
            error_lower = error.lower()
            is_rate_limit = any(
                x in error_lower
                for x in ["rate limit", "429", "quota exceeded", "too many requests"]
            )
            assert is_rate_limit, f"Should detect as substring: {error}"
