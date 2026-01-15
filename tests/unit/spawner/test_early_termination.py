"""Unit tests for spawner early termination detection.

Tests the TerminationPolicy and early detection mechanisms in spawner.
"""

import re
from unittest.mock import MagicMock

import pytest

from aurora_spawner.timeout_policy import TerminationPolicy


class TestTerminationPolicy:
    """Test TerminationPolicy error pattern detection."""

    def test_detects_rate_limit_patterns(self):
        """Detects various rate limit error patterns."""
        policy = TerminationPolicy()

        test_cases = [
            "Error: rate limit exceeded",
            "API rate-limit hit",
            "429 Too Many Requests",
            "You have exceeded your rate limit",
        ]

        for stderr in test_cases:
            should_term, reason = policy.should_terminate(
                stdout="", stderr=stderr, elapsed=5.0, last_activity=1.0
            )
            assert should_term, f"Failed to detect: {stderr}"
            assert "rate" in reason.lower() or "429" in reason

    def test_detects_auth_failure_patterns(self):
        """Detects authentication failure patterns."""
        policy = TerminationPolicy()

        test_cases = [
            "Authentication failed: Invalid credentials",  # authentication.?failed
            "Error: Unauthorized (401)",  # unauthorized
            "Invalid API key provided",  # invalid.?api.?key
            "403 Forbidden - Access denied",  # forbidden
        ]

        for stderr in test_cases:
            should_term, reason = policy.should_terminate(
                stdout="", stderr=stderr, elapsed=2.0, last_activity=0.5
            )
            assert should_term, f"Failed to detect: {stderr}"

    def test_detects_connection_error_patterns(self):
        """Detects connection error patterns."""
        policy = TerminationPolicy()

        test_cases = [
            "Error: ECONNRESET",
            "Connection refused by server",
            "Connection reset by peer",
            "Network connection error",
        ]

        for stderr in test_cases:
            should_term, reason = policy.should_terminate(
                stdout="", stderr=stderr, elapsed=1.0, last_activity=0.2
            )
            assert should_term, f"Failed to detect: {stderr}"

    def test_detects_api_error_patterns(self):
        """Detects API error patterns."""
        policy = TerminationPolicy()

        test_cases = [
            "API error: Service unavailable",  # API.?error
            "API-Error: Bad gateway (502)",  # API.?error
        ]

        for stderr in test_cases:
            should_term, reason = policy.should_terminate(
                stdout="", stderr=stderr, elapsed=3.0, last_activity=0.8
            )
            assert should_term, f"Failed to detect: {stderr}"

    def test_detects_quota_exceeded_patterns(self):
        """Detects quota exceeded patterns."""
        policy = TerminationPolicy()

        test_cases = [
            "Quota exceeded for this month",  # quota.?exceeded
            "Error: quota_exceeded",  # quota.?exceeded
        ]

        for stderr in test_cases:
            should_term, reason = policy.should_terminate(
                stdout="", stderr=stderr, elapsed=2.0, last_activity=0.5
            )
            assert should_term, f"Failed to detect: {stderr}"

    def test_detects_model_unavailable_patterns(self):
        """Detects model unavailable patterns."""
        policy = TerminationPolicy()

        test_cases = [
            "Model not available",  # model.?not.?available
            "Error: model-not-available",  # model.?not.?available
        ]

        for stderr in test_cases:
            should_term, reason = policy.should_terminate(
                stdout="", stderr=stderr, elapsed=1.5, last_activity=0.3
            )
            assert should_term, f"Failed to detect: {stderr}"

    def test_no_false_positives_on_warnings(self):
        """Doesn't terminate on benign warnings."""
        policy = TerminationPolicy()

        benign_cases = [
            "Warning: Cache miss, fetching from API",
            "Info: Using fallback strategy",
            "Debug: Retrying connection",
            "Notice: Processing chunk 5/10",
        ]

        for stderr in benign_cases:
            should_term, reason = policy.should_terminate(
                stdout="", stderr=stderr, elapsed=5.0, last_activity=1.0
            )
            assert not should_term, f"False positive on: {stderr}"

    def test_no_false_positives_on_progress_messages(self):
        """Doesn't terminate on progress messages that contain keywords."""
        policy = TerminationPolicy()

        progress_cases = [
            "Authenticating user... done",
            "Establishing connection to server...",
            "Checking API status... OK",
            "Rate: 150 items/sec",
        ]

        for stderr in progress_cases:
            should_term, reason = policy.should_terminate(
                stdout="", stderr=stderr, elapsed=3.0, last_activity=0.5
            )
            assert not should_term, f"False positive on: {stderr}"

    def test_custom_predicate_function(self):
        """Supports custom termination predicates."""

        def detect_memory_error(stdout: str, stderr: str) -> bool:
            return "out of memory" in stderr.lower() or "oom killed" in stderr.lower()

        policy = TerminationPolicy(custom_predicates=[detect_memory_error])

        should_term, reason = policy.should_terminate(
            stdout="", stderr="Fatal: Out of memory", elapsed=10.0, last_activity=2.0
        )

        assert should_term
        assert "custom" in reason.lower()

    def test_multiple_custom_predicates(self):
        """Supports multiple custom termination predicates."""

        def detect_oom(stdout: str, stderr: str) -> bool:
            return "out of memory" in stderr.lower()

        def detect_segfault(stdout: str, stderr: str) -> bool:
            return "segmentation fault" in stderr.lower()

        policy = TerminationPolicy(custom_predicates=[detect_oom, detect_segfault])

        # Test OOM detection
        should_term, _ = policy.should_terminate(
            stdout="", stderr="Fatal: out of memory", elapsed=5.0, last_activity=1.0
        )
        assert should_term

        # Test segfault detection
        should_term, _ = policy.should_terminate(
            stdout="", stderr="Segmentation fault (core dumped)", elapsed=5.0, last_activity=1.0
        )
        assert should_term

    def test_disabled_policy_never_terminates(self):
        """Disabled policy never terminates."""
        policy = TerminationPolicy(enabled=False)

        # Even with obvious error patterns
        should_term, reason = policy.should_terminate(
            stdout="",
            stderr="Error: Rate limit exceeded (429)",
            elapsed=5.0,
            last_activity=1.0,
        )

        assert not should_term
        assert reason == ""

    def test_kill_on_error_patterns_flag(self):
        """kill_on_error_patterns flag controls error pattern detection."""
        policy = TerminationPolicy(enabled=True, kill_on_error_patterns=False)

        should_term, reason = policy.should_terminate(
            stdout="",
            stderr="Error: Rate limit exceeded (429)",
            elapsed=5.0,
            last_activity=1.0,
        )

        assert not should_term

    def test_error_pattern_regex_case_insensitive(self):
        """Error pattern matching is case-insensitive."""
        policy = TerminationPolicy()

        test_cases = [
            "RATE LIMIT EXCEEDED",
            "Rate Limit Exceeded",
            "rate limit exceeded",
            "RaTe LiMiT eXcEeDeD",
        ]

        for stderr in test_cases:
            should_term, _ = policy.should_terminate(
                stdout="", stderr=stderr, elapsed=5.0, last_activity=1.0
            )
            assert should_term, f"Case sensitivity issue: {stderr}"

    def test_error_pattern_with_context(self):
        """Error patterns detected even with surrounding context."""
        policy = TerminationPolicy()

        stderr = """
        Processing request...
        Making API call...
        Error: 429 Too Many Requests
        Retry-After: 60
        Request failed
        """

        should_term, reason = policy.should_terminate(
            stdout="", stderr=stderr, elapsed=5.0, last_activity=1.0
        )

        assert should_term
        assert "429" in reason or "rate" in reason.lower()


class TestTerminationPolicyPatternCoverage:
    """Test coverage of all default error patterns."""

    def test_all_default_patterns_valid_regex(self):
        """All default error patterns are valid regex."""
        policy = TerminationPolicy()

        for pattern in policy.error_patterns:
            try:
                re.compile(pattern, re.IGNORECASE)
            except re.error as e:
                pytest.fail(f"Invalid regex pattern '{pattern}': {e}")

    def test_rate_limit_pattern(self):
        """rate.?limit pattern matches variations."""
        policy = TerminationPolicy()

        variations = [
            "rate limit",
            "rate-limit",
            "ratelimit",
            "rate_limit",
        ]

        for var in variations:
            should_term, _ = policy.should_terminate(
                stdout="", stderr=f"Error: {var} exceeded", elapsed=5.0, last_activity=1.0
            )
            assert should_term, f"Failed to match: {var}"

    def test_connection_pattern(self):
        """connection pattern matches variations."""
        policy = TerminationPolicy()

        variations = [
            "connection refused",
            "connection reset",
            "connection error",
            "connection-refused",
            "connectionrefused",
        ]

        for var in variations:
            should_term, _ = policy.should_terminate(
                stdout="", stderr=f"Error: {var}", elapsed=5.0, last_activity=1.0
            )
            assert should_term, f"Failed to match: {var}"

    def test_api_error_pattern(self):
        """API.?error pattern matches variations."""
        policy = TerminationPolicy()

        variations = [
            "API error",
            "API-error",
            "APIerror",
            "API_error",
        ]

        for var in variations:
            should_term, _ = policy.should_terminate(
                stdout="", stderr=f"{var}: Service down", elapsed=5.0, last_activity=1.0
            )
            assert should_term, f"Failed to match: {var}"

    def test_authentication_pattern(self):
        """authentication.?failed pattern matches variations."""
        policy = TerminationPolicy()

        variations = [
            "authentication failed",
            "authentication-failed",
            "authenticationfailed",
            "authentication_failed",
        ]

        for var in variations:
            should_term, _ = policy.should_terminate(
                stdout="", stderr=f"Error: {var}", elapsed=5.0, last_activity=1.0
            )
            assert should_term, f"Failed to match: {var}"


class TestNoActivityTermination:
    """Test no-activity based termination."""

    def test_no_activity_timeout_not_in_termination_policy(self):
        """No-activity timeout is handled by TimeoutPolicy, not TerminationPolicy."""
        # This test documents that no-activity timeout is a separate concern
        # from error pattern detection. It's handled by TimeoutPolicy.no_activity_timeout

        from aurora_spawner.timeout_policy import TimeoutPolicy

        timeout_policy = TimeoutPolicy(no_activity_timeout=30.0)
        assert timeout_policy.no_activity_timeout == 30.0

        # TerminationPolicy focuses on error patterns only
        term_policy = TerminationPolicy()
        # No no_activity_timeout attribute in TerminationPolicy
        assert not hasattr(term_policy, "no_activity_timeout")


class TestTerminationReason:
    """Test termination reason messages."""

    def test_reason_includes_matched_pattern(self):
        """Termination reason includes the matched pattern."""
        policy = TerminationPolicy()

        should_term, reason = policy.should_terminate(
            stdout="",
            stderr="Error: Rate limit exceeded",
            elapsed=5.0,
            last_activity=1.0,
        )

        assert should_term
        assert reason  # Non-empty reason
        # Reason should help identify which pattern matched
        assert "rate" in reason.lower() or "pattern" in reason.lower()

    def test_custom_predicate_reason(self):
        """Custom predicate termination has descriptive reason."""

        def custom_check(stdout: str, stderr: str) -> bool:
            return "custom error" in stderr

        policy = TerminationPolicy(custom_predicates=[custom_check])

        should_term, reason = policy.should_terminate(
            stdout="", stderr="custom error occurred", elapsed=5.0, last_activity=1.0
        )

        assert should_term
        assert "custom" in reason.lower()


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_stderr(self):
        """Empty stderr doesn't trigger termination."""
        policy = TerminationPolicy()

        should_term, reason = policy.should_terminate(
            stdout="", stderr="", elapsed=5.0, last_activity=1.0
        )

        assert not should_term
        assert reason == ""

    def test_none_stderr(self):
        """None stderr doesn't crash, treated as no termination."""
        policy = TerminationPolicy()

        # Should handle None gracefully
        should_term, reason = policy.should_terminate(
            stdout="", stderr=None, elapsed=5.0, last_activity=1.0
        )

        assert not should_term

    def test_very_long_stderr(self):
        """Very long stderr with error pattern is detected."""
        policy = TerminationPolicy()

        # Build large stderr with error buried in middle
        padding = "X" * 10000
        stderr = f"{padding}\nError: Rate limit exceeded (429)\n{padding}"

        should_term, reason = policy.should_terminate(
            stdout="", stderr=stderr, elapsed=5.0, last_activity=1.0
        )

        assert should_term

    def test_zero_elapsed_time(self):
        """Zero elapsed time is handled correctly."""
        policy = TerminationPolicy()

        should_term, reason = policy.should_terminate(
            stdout="", stderr="Error: 429", elapsed=0.0, last_activity=0.0
        )

        assert should_term  # Error pattern still detected

    def test_negative_last_activity(self):
        """Negative last_activity (shouldn't happen) doesn't crash."""
        policy = TerminationPolicy()

        # Should handle gracefully
        should_term, reason = policy.should_terminate(
            stdout="", stderr="Error: 429", elapsed=5.0, last_activity=-1.0
        )

        assert should_term  # Error pattern still detected
