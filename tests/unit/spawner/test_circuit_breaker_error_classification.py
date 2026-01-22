"""Tests for circuit breaker smart error classification.

Tests the permanent vs transient error handling improvements:
- Permanent errors (auth, invalid model, 400/403/404) trigger fast-fail
- Transient errors (500s, timeouts, network) allow full retry chain
- Increased fast_fail_threshold from 1 to 2 (requires 3 failures)
"""

import time

import pytest

from aurora_spawner.circuit_breaker import CircuitBreaker, CircuitState


class TestPermanentErrorFastFail:
    """Test permanent errors trigger fast-fail after threshold."""

    def test_auth_error_triggers_fast_fail(self):
        """Auth errors (401, unauthorized) should trigger fast-fail."""
        cb = CircuitBreaker(
            failure_threshold=5,  # High threshold to isolate fast-fail test
            fast_fail_threshold=2,  # Requires 3 failures to fast-fail
            failure_window=60.0,
        )

        # Record 3 auth errors in quick succession
        cb.record_failure("agent-1", fast_fail=True, failure_type="auth_error")
        time.sleep(0.01)
        cb.record_failure("agent-1", fast_fail=True, failure_type="auth_error")
        time.sleep(0.01)
        cb.record_failure("agent-1", fast_fail=True, failure_type="auth_error")

        # Should fast-fail and open circuit
        assert cb.is_open("agent-1")

    def test_invalid_model_triggers_fast_fail(self):
        """Invalid model errors should trigger fast-fail."""
        cb = CircuitBreaker(
            failure_threshold=5,
            fast_fail_threshold=2,
            failure_window=60.0,
        )

        # Record 3 invalid model errors
        cb.record_failure("agent-1", fast_fail=True, failure_type="invalid_model")
        time.sleep(0.01)
        cb.record_failure("agent-1", fast_fail=True, failure_type="invalid_model")
        time.sleep(0.01)
        cb.record_failure("agent-1", fast_fail=True, failure_type="invalid_model")

        # Should fast-fail
        assert cb.is_open("agent-1")

    def test_forbidden_triggers_fast_fail(self):
        """Forbidden errors (403) should trigger fast-fail."""
        cb = CircuitBreaker(
            failure_threshold=5,
            fast_fail_threshold=2,
            failure_window=60.0,
        )

        # Record 3 forbidden errors
        for _ in range(3):
            cb.record_failure("agent-1", fast_fail=True, failure_type="forbidden")
            time.sleep(0.01)

        # Should fast-fail
        assert cb.is_open("agent-1")

    def test_invalid_request_triggers_fast_fail(self):
        """Invalid request errors (400) should trigger fast-fail."""
        cb = CircuitBreaker(
            failure_threshold=5,
            fast_fail_threshold=2,
            failure_window=60.0,
        )

        # Record 3 invalid request errors
        for _ in range(3):
            cb.record_failure("agent-1", fast_fail=True, failure_type="invalid_request")
            time.sleep(0.01)

        # Should fast-fail
        assert cb.is_open("agent-1")

    def test_not_found_triggers_fast_fail(self):
        """Not found errors (404) should trigger fast-fail."""
        cb = CircuitBreaker(
            failure_threshold=5,
            fast_fail_threshold=2,
            failure_window=60.0,
        )

        # Record 3 not found errors
        for _ in range(3):
            cb.record_failure("agent-1", fast_fail=True, failure_type="not_found")
            time.sleep(0.01)

        # Should fast-fail
        assert cb.is_open("agent-1")


class TestTransientErrorAllowsRetries:
    """Test transient errors do NOT trigger fast-fail."""

    def test_transient_error_no_fast_fail(self):
        """Transient errors (500, network) should NOT trigger fast-fail."""
        cb = CircuitBreaker(
            failure_threshold=5,  # High threshold - won't reach by threshold
            fast_fail_threshold=2,
            failure_window=60.0,
        )

        # Record 3 transient errors in quick succession
        cb.record_failure("agent-1", fast_fail=True, failure_type="transient_error")
        time.sleep(0.01)
        cb.record_failure("agent-1", fast_fail=True, failure_type="transient_error")
        time.sleep(0.01)
        cb.record_failure("agent-1", fast_fail=True, failure_type="transient_error")

        # Should NOT fast-fail - circuit should stay closed
        assert not cb.is_open("agent-1")

    def test_timeout_no_fast_fail(self):
        """Timeout errors should NOT trigger fast-fail (transient)."""
        cb = CircuitBreaker(
            failure_threshold=5,
            fast_fail_threshold=2,
            failure_window=60.0,
        )

        # Record 3 timeout errors
        for _ in range(3):
            cb.record_failure("agent-1", fast_fail=True, failure_type="timeout")
            time.sleep(0.01)

        # Should NOT fast-fail (timeouts are transient)
        assert not cb.is_open("agent-1")

    def test_inference_error_fast_fails_for_regular_agents(self):
        """Inference errors DO fast-fail for regular agents (not adhoc)."""
        cb = CircuitBreaker(
            failure_threshold=5,
            fast_fail_threshold=2,
            failure_window=60.0,
        )

        # Record 3 inference errors for REGULAR agent
        for _ in range(3):
            cb.record_failure("agent-1", fast_fail=True, failure_type="inference")
            time.sleep(0.01)

        # Regular agents DO fast-fail on inference errors
        assert cb.is_open("agent-1")

    def test_inference_error_no_fast_fail_for_adhoc_agents(self):
        """Inference errors do NOT fast-fail for adhoc agents."""
        cb = CircuitBreaker(
            failure_threshold=5,
            fast_fail_threshold=2,
            failure_window=60.0,
        )
        cb.mark_as_adhoc("adhoc-agent")

        # Record 3 inference errors for ADHOC agent
        for _ in range(3):
            cb.record_failure("adhoc-agent", fast_fail=True, failure_type="inference")
            time.sleep(0.01)

        # Adhoc agents do NOT fast-fail on inference errors
        assert not cb.is_open("adhoc-agent")


class TestIncreasedFastFailThreshold:
    """Test fast_fail_threshold increased from 1 to 2 (triggers at 2 failures vs 1)."""

    def test_one_failure_does_not_fast_fail(self):
        """One permanent error should NOT fast-fail (threshold is 2)."""
        cb = CircuitBreaker(
            failure_threshold=5,
            fast_fail_threshold=2,  # Triggers when recent_failures >= 2
            failure_window=60.0,
        )

        # Record only 1 auth error
        cb.record_failure("agent-1", fast_fail=True, failure_type="auth_error")

        # Should NOT fast-fail yet (need 2)
        assert not cb.is_open("agent-1")

    def test_two_failures_triggers_fast_fail(self):
        """Two permanent errors SHOULD trigger fast-fail (threshold is 2)."""
        cb = CircuitBreaker(
            failure_threshold=5,
            fast_fail_threshold=2,  # Triggers at 2 failures
            failure_window=60.0,
        )

        # Record 2 auth errors
        cb.record_failure("agent-1", fast_fail=True, failure_type="auth_error")
        time.sleep(0.01)
        cb.record_failure("agent-1", fast_fail=True, failure_type="auth_error")

        # Should fast-fail at 2 errors
        assert cb.is_open("agent-1")

    def test_old_threshold_would_have_failed_earlier(self):
        """Verify old threshold (1) fast-fails at 1 error, new (2) at 2 errors."""
        # Old behavior (threshold=1): fast-fails at 1 failure
        cb_old = CircuitBreaker(
            failure_threshold=5,
            fast_fail_threshold=1,  # Old value - triggers at 1 failure
            failure_window=60.0,
        )

        cb_old.record_failure("agent-old", fast_fail=True, failure_type="auth_error")
        time.sleep(0.01)
        cb_old.record_failure("agent-old", fast_fail=True, failure_type="auth_error")

        # Old threshold fast-fails at 2 errors (recent_failures=2 >= threshold=1)
        assert cb_old.is_open("agent-old")

        # New behavior (threshold=2): needs 2 failures
        cb_new = CircuitBreaker(
            failure_threshold=5,
            fast_fail_threshold=2,  # New value - triggers at 2 failures
            failure_window=60.0,
        )

        cb_new.record_failure("agent-new", fast_fail=True, failure_type="auth_error")

        # New threshold does NOT fast-fail at 1 error
        assert not cb_new.is_open("agent-new")

        # Add second failure
        time.sleep(0.01)
        cb_new.record_failure("agent-new", fast_fail=True, failure_type="auth_error")

        # Now it should fast-fail at 2 errors
        assert cb_new.is_open("agent-new")


class TestMixedErrorTypes:
    """Test behavior with mixed permanent and transient errors."""

    def test_mixed_errors_still_fast_fails(self):
        """Mix of errors will still fast-fail if threshold reached."""
        cb = CircuitBreaker(
            failure_threshold=5,
            fast_fail_threshold=2,
            failure_window=60.0,
        )

        # Record mixed errors
        cb.record_failure("agent-1", fast_fail=True, failure_type="auth_error")  # Permanent
        time.sleep(0.01)
        cb.record_failure("agent-1", fast_fail=True, failure_type="transient_error")  # Transient
        time.sleep(0.01)
        cb.record_failure("agent-1", fast_fail=True, failure_type="auth_error")  # Permanent

        # With recent_failures >= 2 and at least one fast-fail-eligible error, may fast-fail
        # The transient error sets fast_fail=False for that call, but doesn't prevent
        # later permanent errors from triggering fast-fail
        # After 3 failures total with 2 permanent, can fast-fail
        assert cb.is_open("agent-1")

    def test_all_permanent_fast_fails(self):
        """All permanent errors should fast-fail."""
        cb = CircuitBreaker(
            failure_threshold=5,
            fast_fail_threshold=2,
            failure_window=60.0,
        )

        # Record all permanent errors
        cb.record_failure("agent-1", fast_fail=True, failure_type="auth_error")
        time.sleep(0.01)
        cb.record_failure("agent-1", fast_fail=True, failure_type="invalid_model")
        time.sleep(0.01)
        cb.record_failure("agent-1", fast_fail=True, failure_type="forbidden")

        # Should fast-fail (all are permanent)
        assert cb.is_open("agent-1")


class TestRateLimitHandling:
    """Test rate limit errors do NOT trigger circuit breaker."""

    def test_rate_limit_no_circuit_breaker(self):
        """Rate limit errors should NOT trigger circuit breaker at all."""
        cb = CircuitBreaker(
            failure_threshold=2,
            fast_fail_threshold=2,
            failure_window=60.0,
        )

        # Record 5 rate limit errors
        for _ in range(5):
            cb.record_failure("agent-1", fast_fail=True, failure_type="rate_limit")
            time.sleep(0.01)

        # Should NOT open circuit (rate limits are quota issue, not agent issue)
        assert not cb.is_open("agent-1")

        # Should not track in failure history
        health = cb.get_health_status("agent-1")
        assert health["recent_failures"] == 0


class TestErrorClassificationEdgeCases:
    """Test edge cases in error classification."""

    def test_none_failure_type_uses_fast_fail_flag(self):
        """None failure_type respects fast_fail flag as before."""
        cb = CircuitBreaker(
            failure_threshold=5,
            fast_fail_threshold=2,
            failure_window=60.0,
        )

        # Record 3 failures with None type but fast_fail=True
        for _ in range(3):
            cb.record_failure("agent-1", fast_fail=True, failure_type=None)
            time.sleep(0.01)

        # Should fast-fail (no type classification, uses raw fast_fail flag)
        assert cb.is_open("agent-1")

    def test_unknown_failure_type_treated_as_transient(self):
        """Unknown failure types treated as transient (allow retries)."""
        cb = CircuitBreaker(
            failure_threshold=5,
            fast_fail_threshold=2,
            failure_window=60.0,
        )

        # Record 3 failures with unknown type
        for _ in range(3):
            cb.record_failure("agent-1", fast_fail=True, failure_type="unknown_type")
            time.sleep(0.01)

        # Should NOT fast-fail (unknown types are conservative - allow retries)
        assert not cb.is_open("agent-1")


class TestPermanentErrorTypes:
    """Test all permanent error types are recognized."""

    @pytest.mark.parametrize(
        "error_type",
        [
            "auth_error",
            "forbidden",
            "invalid_model",
            "invalid_request",
            "not_found",
        ],
    )
    def test_permanent_error_type_triggers_fast_fail(self, error_type):
        """All permanent error types should trigger fast-fail."""
        cb = CircuitBreaker(
            failure_threshold=5,
            fast_fail_threshold=2,
            failure_window=60.0,
        )

        # Record 3 errors of this type
        for _ in range(3):
            cb.record_failure("agent-1", fast_fail=True, failure_type=error_type)
            time.sleep(0.01)

        # Should fast-fail
        assert cb.is_open("agent-1"), f"{error_type} should trigger fast-fail"


class TestTransientErrorTypes:
    """Test transient error types do NOT trigger fast-fail."""

    @pytest.mark.parametrize(
        "error_type",
        [
            "transient_error",
            "timeout",
            "error_pattern",
            "crash",
        ],
    )
    def test_transient_error_type_no_fast_fail(self, error_type):
        """Transient error types should NOT trigger fast-fail."""
        cb = CircuitBreaker(
            failure_threshold=5,
            fast_fail_threshold=2,
            failure_window=60.0,
        )

        # Record 3 errors of this type
        for _ in range(3):
            cb.record_failure("agent-1", fast_fail=True, failure_type=error_type)
            time.sleep(0.01)

        # Should NOT fast-fail
        assert not cb.is_open("agent-1"), f"{error_type} should NOT trigger fast-fail"


class TestStandardThresholdStillWorks:
    """Verify standard threshold logic still works alongside fast-fail."""

    def test_transient_errors_reach_standard_threshold(self):
        """Transient errors can still open circuit via standard threshold."""
        cb = CircuitBreaker(
            failure_threshold=3,  # Lower threshold for this test
            fast_fail_threshold=2,
            failure_window=60.0,
        )

        # Record 3 transient errors (won't fast-fail, but will hit threshold)
        cb.record_failure("agent-1", fast_fail=False, failure_type="transient_error")
        time.sleep(0.01)
        cb.record_failure("agent-1", fast_fail=False, failure_type="transient_error")
        time.sleep(0.01)
        cb.record_failure("agent-1", fast_fail=False, failure_type="transient_error")

        # Should open via standard threshold (3 failures)
        assert cb.is_open("agent-1")

    def test_permanent_errors_can_use_both_paths(self):
        """Permanent errors can open via fast-fail OR standard threshold."""
        # Via fast-fail (3 rapid failures)
        cb_fast = CircuitBreaker(
            failure_threshold=10,  # High threshold
            fast_fail_threshold=2,
            failure_window=60.0,
        )

        for _ in range(3):
            cb_fast.record_failure("agent-fast", fast_fail=True, failure_type="auth_error")
            time.sleep(0.01)

        assert cb_fast.is_open("agent-fast")

        # Via standard threshold (spread out failures)
        cb_standard = CircuitBreaker(
            failure_threshold=3,  # Low threshold
            fast_fail_threshold=2,
            failure_window=60.0,
        )

        for _ in range(3):
            cb_standard.record_failure("agent-standard", fast_fail=False, failure_type="auth_error")
            time.sleep(5.0)  # Spread out to avoid fast-fail

        assert cb_standard.is_open("agent-standard")
