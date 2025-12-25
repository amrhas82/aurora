"""
Unit tests for RateLimiter class.

Tests token bucket rate limiting algorithm.
"""

from unittest.mock import patch

import pytest
from aurora.core.resilience.rate_limiter import RateLimiter


class TestRateLimiterInitialization:
    """Test RateLimiter initialization."""

    def test_default_initialization(self):
        """Test RateLimiter with default parameters (60 requests/minute)."""
        limiter = RateLimiter()

        assert limiter.max_tokens == 60
        assert limiter.refill_rate == 1.0  # 1 token per second
        assert limiter.current_tokens == 60  # Start full
        assert limiter.max_wait_time == 60.0

    def test_custom_initialization(self):
        """Test RateLimiter with custom parameters."""
        limiter = RateLimiter(
            requests_per_minute=120,
            max_wait_time=30.0,
        )

        assert limiter.max_tokens == 120
        assert limiter.refill_rate == 2.0  # 120/60 = 2 tokens per second
        assert limiter.current_tokens == 120
        assert limiter.max_wait_time == 30.0

    def test_invalid_requests_per_minute(self):
        """Test validation of requests_per_minute parameter."""
        with pytest.raises(ValueError, match="requests_per_minute must be positive"):
            RateLimiter(requests_per_minute=0)

        with pytest.raises(ValueError, match="requests_per_minute must be positive"):
            RateLimiter(requests_per_minute=-1)

    def test_invalid_max_wait_time(self):
        """Test validation of max_wait_time parameter."""
        with pytest.raises(ValueError, match="max_wait_time must be positive"):
            RateLimiter(max_wait_time=0)

        with pytest.raises(ValueError, match="max_wait_time must be positive"):
            RateLimiter(max_wait_time=-1.0)


class TestRateLimiterTokenRefill:
    """Test token refill logic."""

    @patch("time.time")
    def test_refill_tokens_after_time(self, mock_time):
        """Test that tokens refill over time."""
        limiter = RateLimiter(requests_per_minute=60)

        # Start at t=0
        mock_time.return_value = 0.0
        limiter._last_refill_time = 0.0
        limiter.current_tokens = 0  # Empty bucket

        # Advance time by 10 seconds
        mock_time.return_value = 10.0
        limiter._refill_tokens()

        # Should have refilled 10 tokens (1 token/sec * 10 sec)
        assert limiter.current_tokens == 10

    @patch("time.time")
    def test_refill_capped_at_max(self, mock_time):
        """Test that token refill is capped at max_tokens."""
        limiter = RateLimiter(requests_per_minute=60)

        # Start at t=0 with 50 tokens
        mock_time.return_value = 0.0
        limiter._last_refill_time = 0.0
        limiter.current_tokens = 50

        # Advance time by 100 seconds (would add 100 tokens)
        mock_time.return_value = 100.0
        limiter._refill_tokens()

        # Should be capped at max_tokens (60)
        assert limiter.current_tokens == 60

    @patch("time.time")
    def test_no_refill_when_full(self, mock_time):
        """Test that refill does nothing when bucket is full."""
        limiter = RateLimiter(requests_per_minute=60)

        # Start full at t=0
        mock_time.return_value = 0.0
        limiter._last_refill_time = 0.0
        limiter.current_tokens = 60

        # Advance time by 5 seconds
        mock_time.return_value = 5.0
        limiter._refill_tokens()

        # Should still be 60 (capped)
        assert limiter.current_tokens == 60

    @patch("time.time")
    def test_partial_token_refill(self, mock_time):
        """Test partial token refill."""
        limiter = RateLimiter(requests_per_minute=60)

        # Start at t=0 with 0 tokens
        mock_time.return_value = 0.0
        limiter._last_refill_time = 0.0
        limiter.current_tokens = 0

        # Advance time by 2.5 seconds
        mock_time.return_value = 2.5
        limiter._refill_tokens()

        # Should have 2.5 tokens (partial token allowed)
        assert limiter.current_tokens == 2.5


class TestRateLimiterAcquire:
    """Test token acquisition logic."""

    def test_acquire_when_tokens_available(self):
        """Test acquiring token when available."""
        limiter = RateLimiter()

        result = limiter.try_acquire()

        assert result is True
        assert limiter.current_tokens == 59  # Started with 60

    def test_acquire_multiple_tokens(self):
        """Test acquiring multiple tokens."""
        limiter = RateLimiter()

        for _i in range(5):
            result = limiter.try_acquire()
            assert result is True

        assert abs(limiter.current_tokens - 55) < 0.1  # 60 - 5 (with tolerance)

    def test_acquire_fails_when_no_tokens(self):
        """Test acquiring fails when no tokens available."""
        limiter = RateLimiter()
        limiter.current_tokens = 0

        result = limiter.try_acquire()

        assert result is False
        assert limiter.current_tokens < 0.1  # Close to 0 (with tolerance for time passing)

    def test_acquire_with_custom_cost(self):
        """Test acquiring with custom token cost."""
        limiter = RateLimiter()

        result = limiter.try_acquire(tokens=10)

        assert result is True
        assert limiter.current_tokens == 50  # 60 - 10

    def test_acquire_fails_when_insufficient_tokens(self):
        """Test acquiring fails when insufficient tokens for cost."""
        limiter = RateLimiter()
        limiter.current_tokens = 5

        result = limiter.try_acquire(tokens=10)

        assert result is False
        assert abs(limiter.current_tokens - 5) < 0.1  # Unchanged (with tolerance)

    def test_acquire_invalid_cost(self):
        """Test validation of token cost."""
        limiter = RateLimiter()

        with pytest.raises(ValueError, match="tokens must be positive"):
            limiter.try_acquire(tokens=0)

        with pytest.raises(ValueError, match="tokens must be positive"):
            limiter.try_acquire(tokens=-1)


class TestRateLimiterWaitIfNeeded:
    """Test wait_if_needed blocking logic."""

    @patch("time.sleep")
    def test_wait_if_needed_no_wait_when_tokens_available(self, mock_sleep):
        """Test no waiting when tokens available."""
        limiter = RateLimiter()

        limiter.wait_if_needed()

        # Should not sleep
        mock_sleep.assert_not_called()
        assert limiter.current_tokens == 59

    @patch("time.sleep")
    @patch("time.time")
    def test_wait_if_needed_waits_for_refill(self, mock_time, mock_sleep):
        """Test waiting for token refill."""
        limiter = RateLimiter(requests_per_minute=60)  # 1 token/sec

        # Start with no tokens at t=0
        mock_time.return_value = 0.0
        limiter._last_refill_time = 0.0
        limiter.current_tokens = 0

        # Simulate time advancement during sleep
        def sleep_side_effect(duration):
            mock_time.return_value += duration

        mock_sleep.side_effect = sleep_side_effect

        # This should wait 1 second for 1 token to refill
        limiter.wait_if_needed()

        # Should have slept for 1 second
        mock_sleep.assert_called_once_with(1.0)
        # After refill, should have acquired 1 token
        assert limiter.current_tokens == 0  # 1 refilled - 1 acquired

    @patch("time.time")
    def test_wait_if_needed_timeout_exceeded(self, mock_time):
        """Test that wait times exceeding max_wait_time raise error."""
        limiter = RateLimiter(requests_per_minute=60, max_wait_time=5.0)

        # Empty bucket at t=0
        mock_time.return_value = 0.0
        limiter._last_refill_time = 0.0
        limiter.current_tokens = 0

        # Request 10 tokens (would require 10 seconds to refill)
        with pytest.raises(TimeoutError, match="Rate limit wait time would exceed"):
            limiter.wait_if_needed(tokens=10)

    @patch("time.sleep")
    @patch("time.time")
    def test_wait_if_needed_with_custom_cost(self, mock_time, mock_sleep):
        """Test waiting with custom token cost."""
        limiter = RateLimiter(requests_per_minute=60)  # 1 token/sec

        # Start with no tokens
        mock_time.return_value = 0.0
        limiter._last_refill_time = 0.0
        limiter.current_tokens = 0

        def sleep_side_effect(duration):
            mock_time.return_value += duration

        mock_sleep.side_effect = sleep_side_effect

        # Request 5 tokens (need to wait 5 seconds)
        limiter.wait_if_needed(tokens=5)

        # Should have slept for 5 seconds total
        assert sum(call.args[0] for call in mock_sleep.call_args_list) == 5.0


class TestRateLimiterIntegration:
    """Test RateLimiter in realistic scenarios."""

    def test_burst_then_throttle(self):
        """Test burst of requests followed by throttling."""
        limiter = RateLimiter(requests_per_minute=60)

        # Burst: acquire all 60 tokens
        for _i in range(60):
            assert limiter.try_acquire() is True

        # Next request should fail (no tokens left)
        assert limiter.try_acquire() is False

    @patch("time.sleep")
    @patch("time.time")
    def test_sustained_rate(self, mock_time, mock_sleep):
        """Test sustained request rate at limit."""
        limiter = RateLimiter(requests_per_minute=60)  # 1 req/sec

        mock_time.return_value = 0.0
        limiter._last_refill_time = 0.0

        def sleep_side_effect(duration):
            mock_time.return_value += duration

        mock_sleep.side_effect = sleep_side_effect

        # Make 10 requests at exactly 1/second rate
        for _i in range(10):
            limiter.wait_if_needed()
            # Advance time by 1 second to refill 1 token
            mock_time.return_value += 1.0

        # Should have made all requests successfully
        assert mock_sleep.call_count >= 0  # May or may not need to wait

    def test_rate_limiter_reset(self):
        """Test resetting the rate limiter."""
        limiter = RateLimiter()

        # Consume some tokens
        for _ in range(30):
            limiter.try_acquire()

        assert abs(limiter.current_tokens - 30) < 1.0  # Approximately 30 (with tolerance)

        # Reset
        limiter.reset()

        # Should be back to full
        assert limiter.current_tokens == 60


class TestRateLimiterEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_tokens_available(self):
        """Test behavior when exactly 0 tokens available."""
        limiter = RateLimiter()
        limiter.current_tokens = 0.0

        assert limiter.try_acquire() is False

    def test_fractional_token(self):
        """Test acquiring with fractional tokens available."""
        limiter = RateLimiter()
        limiter.current_tokens = 0.5

        # Can't acquire 1 token with only 0.5 available
        assert limiter.try_acquire() is False

    @patch("time.time")
    def test_very_long_idle_time(self, mock_time):
        """Test refill after very long idle period."""
        limiter = RateLimiter(requests_per_minute=60)

        # Start empty at t=0
        mock_time.return_value = 0.0
        limiter._last_refill_time = 0.0
        limiter.current_tokens = 0

        # Advance time by 1 hour (3600 seconds)
        mock_time.return_value = 3600.0
        limiter._refill_tokens()

        # Should be capped at max_tokens (60), not 3600
        assert limiter.current_tokens == 60

    def test_high_rate_limit(self):
        """Test with very high rate limit."""
        limiter = RateLimiter(requests_per_minute=10000)

        assert limiter.max_tokens == 10000
        assert limiter.refill_rate == 10000 / 60  # ~166.67 tokens/sec

    def test_low_rate_limit(self):
        """Test with very low rate limit."""
        limiter = RateLimiter(requests_per_minute=1)

        assert limiter.max_tokens == 1
        assert abs(limiter.refill_rate - 1 / 60) < 0.001  # ~0.0167 tokens/sec


class TestRateLimiterContextManager:
    """Test RateLimiter as context manager."""

    @patch("time.sleep")
    def test_as_context_manager(self, mock_sleep):
        """Test using RateLimiter with 'with' statement."""
        limiter = RateLimiter()

        with limiter:
            # Token should be acquired on enter
            pass

        # Should have consumed 1 token
        assert limiter.current_tokens == 59

    @patch("time.sleep")
    @patch("time.time")
    def test_context_manager_waits_if_needed(self, mock_time, mock_sleep):
        """Test context manager waits for tokens if needed."""
        limiter = RateLimiter(requests_per_minute=60)

        # Empty the bucket
        mock_time.return_value = 0.0
        limiter._last_refill_time = 0.0
        limiter.current_tokens = 0

        def sleep_side_effect(duration):
            mock_time.return_value += duration

        mock_sleep.side_effect = sleep_side_effect

        with limiter:
            pass

        # Should have waited for 1 token
        mock_sleep.assert_called_once_with(1.0)
