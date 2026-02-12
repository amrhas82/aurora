"""Unit tests for RetryHandler class.

Tests exponential backoff retry logic for transient errors.
"""

import time
from unittest.mock import Mock, patch

import pytest

from aurora_core.exceptions import (
    AuroraError,
    BudgetExceededError,
    ConfigurationError,
    StorageError,
    ValidationError,
)
from aurora_core.resilience.retry_handler import RetryHandler


class TestRetryHandlerInitialization:
    """Test RetryHandler initialization and configuration."""

    def test_default_initialization(self):
        """Test RetryHandler with default parameters."""
        handler = RetryHandler()
        assert handler.max_retries == 3
        assert handler.base_delay == 0.1  # 100ms
        assert handler.max_delay == 10.0
        assert handler.backoff_factor == 2.0

    def test_custom_initialization(self):
        """Test RetryHandler with custom parameters."""
        handler = RetryHandler(
            max_retries=5,
            base_delay=0.2,
            max_delay=5.0,
            backoff_factor=3.0,
        )
        assert handler.max_retries == 5
        assert handler.base_delay == 0.2
        assert handler.max_delay == 5.0
        assert handler.backoff_factor == 3.0

    def test_invalid_max_retries(self):
        """Test validation of max_retries parameter."""
        with pytest.raises(ValueError, match="max_retries must be positive"):
            RetryHandler(max_retries=0)
        with pytest.raises(ValueError, match="max_retries must be positive"):
            RetryHandler(max_retries=-1)

    def test_invalid_base_delay(self):
        """Test validation of base_delay parameter."""
        with pytest.raises(ValueError, match="base_delay must be positive"):
            RetryHandler(base_delay=0)
        with pytest.raises(ValueError, match="base_delay must be positive"):
            RetryHandler(base_delay=-0.1)

    def test_invalid_backoff_factor(self):
        """Test validation of backoff_factor parameter."""
        with pytest.raises(ValueError, match="backoff_factor must be >= 1.0"):
            RetryHandler(backoff_factor=0.5)


class TestRetryHandlerRecoverableErrors:
    """Test classification of recoverable vs non-recoverable errors."""

    def test_is_recoverable_network_timeout(self):
        """Test that network timeout errors are recoverable."""
        handler = RetryHandler()

        # Simulate network timeout
        error = TimeoutError("Connection timed out")
        assert handler.is_recoverable(error) is True

    def test_is_recoverable_connection_error(self):
        """Test that connection errors are recoverable."""
        handler = RetryHandler()

        # Simulate connection error
        error = ConnectionError("Failed to connect")
        assert handler.is_recoverable(error) is True

    def test_is_recoverable_storage_error(self):
        """Test that storage errors (database lock) are recoverable."""
        handler = RetryHandler()

        # Database lock error
        error = StorageError("Database is locked", "SQLite lock timeout")
        assert handler.is_recoverable(error) is True

    def test_is_not_recoverable_configuration_error(self):
        """Test that configuration errors are non-recoverable."""
        handler = RetryHandler()

        error = ConfigurationError("Missing required config key")
        assert handler.is_recoverable(error) is False

    def test_is_not_recoverable_budget_exceeded(self):
        """Test that budget exceeded errors are non-recoverable."""
        handler = RetryHandler()

        error = BudgetExceededError("Budget limit exceeded", 10.0, 5.0, 2.0)
        assert handler.is_recoverable(error) is False

    def test_is_not_recoverable_validation_error(self):
        """Test that validation errors are non-recoverable."""
        handler = RetryHandler()

        error = ValidationError("Invalid chunk structure")
        assert handler.is_recoverable(error) is False

    def test_is_recoverable_generic_aurora_error(self):
        """Test that generic AuroraError is not recoverable by default."""
        handler = RetryHandler()

        error = AuroraError("Generic error")
        assert handler.is_recoverable(error) is False

    def test_custom_recoverable_errors(self):
        """Test custom recoverable error types."""
        handler = RetryHandler(recoverable_errors=(ValueError, KeyError))

        assert handler.is_recoverable(ValueError("test")) is True
        assert handler.is_recoverable(KeyError("test")) is True
        assert handler.is_recoverable(TypeError("test")) is False


class TestRetryHandlerExponentialBackoff:
    """Test exponential backoff calculation."""

    def test_calculate_delay_first_attempt(self):
        """Test delay calculation for first retry (attempt 1)."""
        handler = RetryHandler(base_delay=0.1, backoff_factor=2.0)
        delay = handler.calculate_delay(attempt=1)
        assert delay == 0.1  # 100ms

    def test_calculate_delay_second_attempt(self):
        """Test delay calculation for second retry (attempt 2)."""
        handler = RetryHandler(base_delay=0.1, backoff_factor=2.0)
        delay = handler.calculate_delay(attempt=2)
        assert delay == 0.2  # 200ms

    def test_calculate_delay_third_attempt(self):
        """Test delay calculation for third retry (attempt 3)."""
        handler = RetryHandler(base_delay=0.1, backoff_factor=2.0)
        delay = handler.calculate_delay(attempt=3)
        assert delay == 0.4  # 400ms

    def test_calculate_delay_with_max_delay(self):
        """Test delay calculation is capped by max_delay."""
        handler = RetryHandler(base_delay=1.0, backoff_factor=2.0, max_delay=3.0)
        # Would be 8.0 without cap (1.0 * 2^3)
        delay = handler.calculate_delay(attempt=4)
        assert delay == 3.0

    def test_calculate_delay_with_custom_backoff(self):
        """Test delay with custom backoff factor."""
        handler = RetryHandler(base_delay=0.1, backoff_factor=3.0)
        delay = handler.calculate_delay(attempt=2)
        assert abs(delay - 0.3) < 0.001  # 100ms * 3 (with tolerance for floating point)


class TestRetryHandlerExecute:
    """Test retry execution logic."""

    def test_execute_success_first_try(self):
        """Test successful execution on first attempt (no retries)."""
        handler = RetryHandler()

        func = Mock(return_value="success")
        result = handler.execute(func)

        assert result == "success"
        assert func.call_count == 1

    def test_execute_success_after_retries(self):
        """Test successful execution after transient failures."""
        handler = RetryHandler(base_delay=0.01)  # Fast for testing

        # Fail twice, then succeed
        func = Mock(side_effect=[TimeoutError("timeout"), TimeoutError("timeout"), "success"])

        result = handler.execute(func)

        assert result == "success"
        assert func.call_count == 3

    def test_execute_max_retries_exceeded(self):
        """Test that max retries limit is enforced."""
        handler = RetryHandler(max_retries=2, base_delay=0.01)

        # Always fail
        func = Mock(side_effect=TimeoutError("timeout"))

        with pytest.raises(TimeoutError):
            handler.execute(func)

        # Initial attempt + 2 retries = 3 calls
        assert func.call_count == 3

    def test_execute_non_recoverable_error_immediate_failure(self):
        """Test that non-recoverable errors fail immediately without retries."""
        handler = RetryHandler(base_delay=0.01)

        func = Mock(side_effect=ConfigurationError("invalid config"))

        with pytest.raises(ConfigurationError):
            handler.execute(func)

        # Should not retry non-recoverable errors
        assert func.call_count == 1

    def test_execute_with_args_and_kwargs(self):
        """Test execute passes args and kwargs to function."""
        handler = RetryHandler()

        func = Mock(return_value="success")
        result = handler.execute(func, "arg1", "arg2", key1="value1", key2="value2")

        assert result == "success"
        func.assert_called_once_with("arg1", "arg2", key1="value1", key2="value2")

    @patch("time.sleep")
    def test_execute_delays_between_retries(self, mock_sleep):
        """Test that delays are applied between retry attempts."""
        handler = RetryHandler(base_delay=0.1, backoff_factor=2.0)

        func = Mock(side_effect=[TimeoutError("timeout"), TimeoutError("timeout"), "success"])

        result = handler.execute(func)

        assert result == "success"
        # Should have two delays: 100ms and 200ms
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(0.1)
        mock_sleep.assert_any_call(0.2)

    def test_execute_records_retry_count(self):
        """Test that retry count is tracked."""
        handler = RetryHandler(base_delay=0.01)

        func = Mock(side_effect=[TimeoutError("timeout"), TimeoutError("timeout"), "success"])

        result = handler.execute(func)

        assert result == "success"
        assert handler.last_retry_count == 2

    def test_execute_records_total_delay(self):
        """Test that total delay is tracked."""
        handler = RetryHandler(base_delay=0.1, backoff_factor=2.0)

        func = Mock(side_effect=[TimeoutError("timeout"), TimeoutError("timeout"), "success"])

        start = time.time()
        result = handler.execute(func)
        elapsed = time.time() - start

        assert result == "success"
        # Total delay should be 0.1 + 0.2 = 0.3 seconds (with some tolerance)
        assert 0.25 <= elapsed <= 0.5  # Allow for execution overhead


class TestRetryHandlerCallable:
    """Test RetryHandler as a callable decorator."""

    def test_as_decorator(self):
        """Test RetryHandler can be used as a decorator."""
        handler = RetryHandler(base_delay=0.01)

        call_count = {"count": 0}

        @handler
        def flaky_function():
            call_count["count"] += 1
            if call_count["count"] < 3:
                raise TimeoutError("timeout")
            return "success"

        result = flaky_function()
        assert result == "success"
        assert call_count["count"] == 3

    def test_as_decorator_with_args(self):
        """Test decorated function with arguments."""
        handler = RetryHandler(base_delay=0.01)

        @handler
        def add(a: int, b: int) -> int:
            return a + b

        result = add(2, 3)
        assert result == 5


class TestRetryHandlerEdgeCases:
    """Test edge cases and error conditions."""

    def test_execute_with_none_return(self):
        """Test function that returns None."""
        handler = RetryHandler()

        func = Mock(return_value=None)
        result = handler.execute(func)

        assert result is None
        assert func.call_count == 1

    def test_execute_with_exception_in_finally(self):
        """Test that exceptions in retry logic are handled."""
        handler = RetryHandler(base_delay=0.01)

        def problematic_func():
            raise ValueError("always fails")

        # Should raise the original exception
        with pytest.raises(ValueError, match="always fails"):
            handler.execute(problematic_func, recoverable_errors=(ValueError,))

    def test_zero_max_retries_validation(self):
        """Test that max_retries=0 is rejected."""
        with pytest.raises(ValueError):
            RetryHandler(max_retries=0)

    def test_execute_with_custom_recoverable_in_call(self):
        """Test passing custom recoverable errors to execute()."""
        handler = RetryHandler(base_delay=0.01)

        func = Mock(side_effect=[ValueError("error"), "success"])

        # ValueError not recoverable by default
        with pytest.raises(ValueError):
            handler.execute(func)

        # Make ValueError recoverable for this call
        func.reset_mock()
        func.side_effect = [ValueError("error"), "success"]
        result = handler.execute(func, recoverable_errors=(ValueError,))
        assert result == "success"
