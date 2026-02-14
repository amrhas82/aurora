"""Integration tests for error recovery.

Tests the retry logic for transient and non-recoverable errors.
"""

from unittest.mock import Mock

import pytest

from aurora_core.resilience import RetryHandler


class TestTransientErrorRecovery:
    """Test recovery from transient errors."""

    def test_retry_transient_llm_failure(self):
        """Test that transient LLM failures are retried successfully."""
        handler = RetryHandler(max_retries=3, base_delay=0.01)

        # Mock LLM call that fails twice, then succeeds
        llm_call = Mock(
            side_effect=[
                TimeoutError("LLM timeout"),
                TimeoutError("LLM timeout"),
                {"response": "success"},
            ],
        )

        # Execute with retry
        result = handler.execute(llm_call)

        # Should succeed after 2 retries
        assert result == {"response": "success"}
        assert llm_call.call_count == 3

    def test_retry_database_lock(self):
        """Test recovery from database lock (StorageError)."""
        from aurora_core.exceptions import StorageError

        handler = RetryHandler(max_retries=3, base_delay=0.01)

        # Mock database operation that's locked initially
        db_operation = Mock(
            side_effect=[StorageError("Database is locked", "SQLite lock"), "success"],
        )

        result = handler.execute(db_operation)

        assert result == "success"
        assert db_operation.call_count == 2

    def test_retry_connection_error(self):
        """Test recovery from connection errors."""
        handler = RetryHandler(max_retries=3, base_delay=0.01)

        # Mock network operation that fails once
        network_call = Mock(
            side_effect=[ConnectionError("Connection refused"), {"data": "success"}],
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


class TestRecoveryRateVerification:
    """Test that recovery rate meets >=95% target for transient errors."""

    def test_95_percent_recovery_rate(self):
        """Test >=95% recovery rate for transient errors."""
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

        # Should meet >=95% recovery rate target
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

        # Should achieve >=95% recovery for transient errors
        assert recovery_rate >= 0.95
