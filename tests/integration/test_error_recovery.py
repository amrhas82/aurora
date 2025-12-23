"""
Integration tests for error recovery.

Tests the full resilience system with retry logic, rate limiting,
metrics collection, and alerting working together.
"""

import time
from unittest.mock import Mock, patch

import pytest

from aurora_core.resilience import (
    Alerting,
    MetricsCollector,
    RateLimiter,
    RetryHandler,
)


class TestTransientErrorRecovery:
    """Test recovery from transient errors."""

    def test_retry_transient_llm_failure(self):
        """Test that transient LLM failures are retried successfully."""
        handler = RetryHandler(max_retries=3, base_delay=0.01)
        metrics = MetricsCollector()

        # Mock LLM call that fails twice, then succeeds
        llm_call = Mock(
            side_effect=[
                TimeoutError("LLM timeout"),
                TimeoutError("LLM timeout"),
                {"response": "success"},
            ]
        )

        # Execute with retry
        start_time = time.time()
        result = handler.execute(llm_call)
        elapsed = time.time() - start_time

        # Should succeed after 2 retries
        assert result == {"response": "success"}
        assert llm_call.call_count == 3

        # Record in metrics
        metrics.record_query(success=True, latency=elapsed)

        # Verify metrics show success
        stats = metrics.get_metrics()
        assert stats["queries"]["total"] == 1
        assert stats["queries"]["success"] == 1

    def test_retry_database_lock(self):
        """Test recovery from database lock (StorageError)."""
        from aurora_core.exceptions import StorageError

        handler = RetryHandler(max_retries=3, base_delay=0.01)

        # Mock database operation that's locked initially
        db_operation = Mock(
            side_effect=[StorageError("Database is locked", "SQLite lock"), "success"]
        )

        result = handler.execute(db_operation)

        assert result == "success"
        assert db_operation.call_count == 2

    def test_retry_connection_error(self):
        """Test recovery from connection errors."""
        handler = RetryHandler(max_retries=3, base_delay=0.01)

        # Mock network operation that fails once
        network_call = Mock(
            side_effect=[ConnectionError("Connection refused"), {"data": "success"}]
        )

        result = handler.execute(network_call)

        assert result == {"data": "success"}
        assert network_call.call_count == 2


class TestNonRecoverableErrors:
    """Test that non-recoverable errors fail fast."""

    def test_configuration_error_no_retry(self):
        """Test that configuration errors fail immediately."""
        from aurora_core.exceptions import ConfigurationError

        handler = RetryHandler(max_retries=3, base_delay=0.01)

        # Mock operation that has config error
        operation = Mock(side_effect=ConfigurationError("Missing API key"))

        with pytest.raises(ConfigurationError):
            handler.execute(operation)

        # Should NOT retry
        assert operation.call_count == 1

    def test_budget_exceeded_no_retry(self):
        """Test that budget exceeded errors fail immediately."""
        from aurora_core.exceptions import BudgetExceededError

        handler = RetryHandler(max_retries=3, base_delay=0.01)

        # Mock operation that exceeds budget
        operation = Mock(side_effect=BudgetExceededError("Budget exceeded", 10.0, 5.0, 2.0))

        with pytest.raises(BudgetExceededError):
            handler.execute(operation)

        # Should NOT retry
        assert operation.call_count == 1

    def test_validation_error_no_retry(self):
        """Test that validation errors fail immediately."""
        from aurora_core.exceptions import ValidationError

        handler = RetryHandler(max_retries=3, base_delay=0.01)

        # Mock operation with invalid input
        operation = Mock(side_effect=ValidationError("Invalid chunk structure"))

        with pytest.raises(ValidationError):
            handler.execute(operation)

        # Should NOT retry
        assert operation.call_count == 1


class TestRateLimitingIntegration:
    """Test rate limiting with retry and metrics."""

    @patch("time.sleep")
    @patch("time.time")
    def test_rate_limit_blocks_then_succeeds(self, mock_time, mock_sleep):
        """Test that rate limiting blocks requests then allows after refill."""
        limiter = RateLimiter(requests_per_minute=60)  # 1/sec
        metrics = MetricsCollector()

        # Set up time mocking
        mock_time.return_value = 0.0
        limiter._last_refill_time = 0.0

        def sleep_side_effect(duration):
            mock_time.return_value += duration

        mock_sleep.side_effect = sleep_side_effect

        # Empty the bucket
        for _ in range(60):
            limiter.try_acquire()

        # Next request should wait
        limiter.wait_if_needed()

        # Should have waited 1 second
        assert mock_sleep.called

        # Record successful request
        metrics.record_query(success=True, latency=1.0)

        stats = metrics.get_metrics()
        assert stats["queries"]["total"] == 1
        assert stats["queries"]["success"] == 1

    def test_rate_limit_timeout_error(self):
        """Test that excessive wait times raise TimeoutError."""
        limiter = RateLimiter(requests_per_minute=60, max_wait_time=1.0)

        # Set tokens to 0
        limiter.current_tokens = 0
        limiter._last_refill_time = time.time()

        # Try to acquire 100 tokens (would take ~100 seconds)
        with pytest.raises(TimeoutError):
            limiter.wait_if_needed(tokens=100)


class TestMetricsAndAlertingIntegration:
    """Test metrics collection triggering alerts."""

    def test_high_error_rate_triggers_alert(self):
        """Test that high error rate triggers alert."""
        metrics = MetricsCollector()
        alerting = Alerting()
        alerting.add_default_rules()

        # Simulate 10 queries: 8 failures (80% error rate)
        for _ in range(8):
            metrics.record_query(success=False, latency=1.0)
        for _ in range(2):
            metrics.record_query(success=True, latency=0.5)

        # Get metrics
        stats = metrics.get_metrics()

        # Evaluate alerts
        alerts = alerting.evaluate(
            {
                "error_rate": stats["errors"]["error_rate"],
                "p95_latency": stats["queries"]["p95_latency"],
                "cache_hit_rate": 0.5,  # Good cache rate
            }
        )

        # Should trigger high error rate alert (80% > 5%)
        assert len(alerts) >= 1
        assert any(a.rule_name == "high_error_rate" for a in alerts)

    def test_high_p95_latency_triggers_alert(self):
        """Test that high p95 latency triggers alert."""
        metrics = MetricsCollector()
        alerting = Alerting()
        alerting.add_default_rules()

        # Simulate queries with high latency
        for i in range(100):
            # 95 queries at 1s, 5 queries at 15s
            latency = 15.0 if i >= 95 else 1.0
            metrics.record_query(success=True, latency=latency)

        stats = metrics.get_metrics()

        # Evaluate alerts
        alerts = alerting.evaluate(
            {
                "error_rate": stats["errors"]["error_rate"],
                "p95_latency": stats["queries"]["p95_latency"],
                "cache_hit_rate": 0.5,
            }
        )

        # Should trigger high p95 latency alert (>10s)
        assert len(alerts) >= 1
        assert any(a.rule_name == "high_p95_latency" for a in alerts)

    def test_low_cache_hit_rate_triggers_alert(self):
        """Test that low cache hit rate triggers alert."""
        metrics = MetricsCollector()
        alerting = Alerting()
        alerting.add_default_rules()

        # Simulate low cache hit rate: 10 hits, 90 misses (10%)
        for _ in range(10):
            metrics.record_cache_hit()
        for _ in range(90):
            metrics.record_cache_miss()

        stats = metrics.get_metrics()

        # Evaluate alerts
        alerts = alerting.evaluate(
            {
                "error_rate": 0.0,
                "p95_latency": 1.0,
                "cache_hit_rate": stats["cache"]["hit_rate"],
            }
        )

        # Should trigger low cache hit rate alert (10% < 20%)
        assert len(alerts) >= 1
        assert any(a.rule_name == "low_cache_hit_rate" for a in alerts)


class TestFullResilienceWorkflow:
    """Test complete resilience workflow with all components."""

    @patch("time.sleep")
    @patch("time.time")
    def test_complete_resilient_query(self, mock_time, mock_sleep):
        """Test a complete query with retry, rate limit, metrics, and alerts."""
        # Initialize components
        retry_handler = RetryHandler(max_retries=3, base_delay=0.01)
        rate_limiter = RateLimiter(requests_per_minute=60)
        metrics = MetricsCollector()
        alerting = Alerting()
        alerting.add_default_rules()

        # Set up time mocking
        mock_time.return_value = 0.0
        rate_limiter._last_refill_time = 0.0

        def sleep_side_effect(duration):
            mock_time.return_value += duration

        mock_sleep.side_effect = sleep_side_effect

        # Mock query that fails once then succeeds
        query_call = Mock(side_effect=[TimeoutError("Timeout"), {"result": "success"}])

        # Execute complete workflow
        def execute_query():
            # 1. Apply rate limit
            rate_limiter.wait_if_needed()

            # 2. Execute with retry
            return retry_handler.execute(query_call)

        start_time = mock_time.return_value
        result = execute_query()
        end_time = mock_time.return_value

        # 3. Record metrics
        metrics.record_query(success=True, latency=end_time - start_time)

        # 4. Check alerts
        stats = metrics.get_metrics()
        alerts = alerting.evaluate(
            {
                "error_rate": stats["errors"]["error_rate"],
                "p95_latency": stats["queries"]["p95_latency"],
                "cache_hit_rate": 1.0,  # Assume perfect cache
            }
        )

        # Verify results
        assert result == {"result": "success"}
        assert query_call.call_count == 2  # 1 failure + 1 success
        assert stats["queries"]["total"] == 1
        assert stats["queries"]["success"] == 1
        assert len(alerts) == 0  # No alerts with good metrics

    def test_partial_failure_recovery(self):
        """Test recovery from partial failures with graceful degradation."""
        retry_handler = RetryHandler(max_retries=2, base_delay=0.01)
        metrics = MetricsCollector()

        results = []

        # Mock 5 operations: 2 succeed, 3 fail after retries
        operations = [
            Mock(return_value="success1"),
            Mock(side_effect=TimeoutError("Permanent failure")),
            Mock(return_value="success2"),
            Mock(side_effect=TimeoutError("Permanent failure")),
            Mock(side_effect=TimeoutError("Permanent failure")),
        ]

        # Execute all operations
        for op in operations:
            try:
                result = retry_handler.execute(op)
                results.append(result)
                metrics.record_query(success=True, latency=0.1)
            except TimeoutError:
                results.append(None)
                metrics.record_query(success=False, latency=0.1)

        # Verify partial success
        assert results.count("success1") == 1
        assert results.count("success2") == 1
        assert results.count(None) == 3

        # Verify metrics
        stats = metrics.get_metrics()
        assert stats["queries"]["total"] == 5
        assert stats["queries"]["success"] == 2
        assert stats["queries"]["failed"] == 3
        assert stats["errors"]["error_rate"] == 0.6  # 60% failure rate


class TestRecoveryRateVerification:
    """Test that recovery rate meets ≥95% target for transient errors."""

    def test_95_percent_recovery_rate(self):
        """Test ≥95% recovery rate for transient errors."""
        retry_handler = RetryHandler(max_retries=3, base_delay=0.01)

        total_attempts = 100
        successful_recoveries = 0

        # Simulate 100 operations with transient failures
        for i in range(total_attempts):
            # Each operation fails 1-2 times then succeeds
            operation = Mock(side_effect=[TimeoutError("Transient"), {"result": f"success{i}"}])

            try:
                result = retry_handler.execute(operation)
                if result == {"result": f"success{i}"}:
                    successful_recoveries += 1
            except Exception:
                pass

        recovery_rate = successful_recoveries / total_attempts

        # Should meet ≥95% recovery rate target
        assert recovery_rate >= 0.95
        assert successful_recoveries == 100  # All should recover

    def test_recovery_with_mixed_error_types(self):
        """Test recovery rate with mix of recoverable and non-recoverable errors."""
        retry_handler = RetryHandler(max_retries=3, base_delay=0.01)
        from aurora_core.exceptions import ConfigurationError

        total_operations = 100
        recoverable_operations = 95  # 95% transient, 5% non-recoverable
        successful_recoveries = 0

        # 95 recoverable, 5 non-recoverable
        for _i in range(recoverable_operations):
            operation = Mock(side_effect=[TimeoutError("Transient"), "success"])
            try:
                retry_handler.execute(operation)
                successful_recoveries += 1
            except Exception:
                pass

        for _i in range(total_operations - recoverable_operations):
            operation = Mock(side_effect=ConfigurationError("Config error"))
            try:
                retry_handler.execute(operation)
            except ConfigurationError:
                pass  # Expected to fail

        # Recovery rate for recoverable errors
        recovery_rate = successful_recoveries / recoverable_operations

        # Should achieve ≥95% recovery for transient errors
        assert recovery_rate >= 0.95
