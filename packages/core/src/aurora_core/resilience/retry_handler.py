"""RetryHandler for exponential backoff retry logic.

Implements retry logic with exponential backoff for transient errors,
following the resilience patterns from PRD Section 5.1.
"""

import time
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar


P = ParamSpec("P")
T = TypeVar("T")


class RetryHandler:
    """Handles retry logic with exponential backoff for transient errors.

    This class implements the retry pattern with exponential backoff delays,
    distinguishing between recoverable (transient) and non-recoverable errors.

    **Recoverable Errors** (will retry):
    - Network timeouts (TimeoutError)
    - Connection errors (ConnectionError)
    - Database locks (StorageError with lock message)

    **Non-Recoverable Errors** (fail fast):
    - Invalid configuration (ConfigurationError)
    - Budget exceeded (BudgetExceededError)
    - Validation errors (ValidationError)
    - Malformed input (ValueError with wrong type)

    **Exponential Backoff Formula**:
    delay = min(base_delay * (backoff_factor ^ attempt), max_delay)

    **Default Configuration**:
    - max_retries: 3
    - base_delay: 100ms
    - backoff_factor: 2.0
    - max_delay: 10s

    Example:
        >>> handler = RetryHandler(max_retries=3, base_delay=0.1)
        >>> result = handler.execute(flaky_api_call, arg1, arg2)
        # Retries up to 3 times with 100ms, 200ms, 400ms delays

        >>> @handler
        >>> def flaky_function():
        >>>     # ... may fail transiently ...
        >>>     pass

    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 0.1,
        max_delay: float = 10.0,
        backoff_factor: float = 2.0,
        recoverable_errors: tuple[type[Exception], ...] | None = None,
    ):
        """Initialize the RetryHandler.

        Args:
            max_retries: Maximum number of retry attempts (must be > 0)
            base_delay: Base delay in seconds for first retry (must be > 0)
            max_delay: Maximum delay in seconds (cap for exponential backoff)
            backoff_factor: Multiplier for each retry (must be >= 1.0)
            recoverable_errors: Tuple of exception types to retry (overrides defaults)

        Raises:
            ValueError: If parameters are invalid

        """
        if max_retries <= 0:
            raise ValueError("max_retries must be positive")
        if base_delay <= 0:
            raise ValueError("base_delay must be positive")
        if backoff_factor < 1.0:
            raise ValueError("backoff_factor must be >= 1.0")

        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor

        # Default recoverable errors: network, connection, timeouts
        if recoverable_errors is None:
            from aurora_core.exceptions import StorageError

            self._recoverable_errors: tuple[type[Exception], ...] = (
                TimeoutError,
                ConnectionError,
                StorageError,  # Database locks
            )
        else:
            self._recoverable_errors = recoverable_errors

        # Track statistics
        self.last_retry_count = 0
        self.last_total_delay = 0.0

    def is_recoverable(self, error: Exception) -> bool:
        """Determine if an error is recoverable (transient).

        Args:
            error: The exception to check

        Returns:
            True if error is recoverable and should be retried, False otherwise

        """
        # Check if error type is in recoverable list
        return isinstance(error, self._recoverable_errors)

    def calculate_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay for a retry attempt.

        Formula: min(base_delay * (backoff_factor ^ attempt), max_delay)

        Args:
            attempt: The retry attempt number (1-indexed)

        Returns:
            Delay in seconds for this attempt

        """
        delay = self.base_delay * (self.backoff_factor ** (attempt - 1))
        return min(delay, self.max_delay)

    def execute(
        self,
        func: Callable[P, T],
        *args: Any,
        recoverable_errors: tuple[type[Exception], ...] | None = None,
        **kwargs: Any,
    ) -> T:
        """Execute a function with retry logic.

        Attempts to execute the function, retrying on transient errors with
        exponential backoff. Non-recoverable errors fail immediately.

        Args:
            func: The function to execute
            *args: Positional arguments for func
            recoverable_errors: Override default recoverable errors for this call
            **kwargs: Keyword arguments for func

        Returns:
            The return value from func

        Raises:
            Exception: The last exception if all retries are exhausted,
                      or immediately for non-recoverable errors

        """
        # Use call-specific recoverable errors if provided
        original_recoverable = self._recoverable_errors
        if recoverable_errors is not None:
            self._recoverable_errors = recoverable_errors

        try:
            self.last_retry_count = 0
            self.last_total_delay = 0.0
            attempt = 0

            while True:
                attempt += 1
                try:
                    # Attempt execution
                    return func(*args, **kwargs)

                except Exception as e:
                    # Check if we should retry
                    if not self.is_recoverable(e):
                        # Non-recoverable error: fail immediately
                        raise

                    if attempt > self.max_retries:
                        # Exhausted all retries
                        raise

                    # Calculate delay and retry
                    self.last_retry_count += 1
                    delay = self.calculate_delay(attempt)
                    self.last_total_delay += delay

                    # Sleep before retry
                    time.sleep(delay)

        finally:
            # Restore original recoverable errors
            if recoverable_errors is not None:
                self._recoverable_errors = original_recoverable

    def __call__(self, func: Callable[P, T]) -> Callable[P, T]:
        """Use RetryHandler as a decorator.

        Example:
            >>> handler = RetryHandler(max_retries=3)
            >>> @handler
            >>> def flaky_function():
            >>>     # ... may fail transiently ...
            >>>     pass

        Args:
            func: The function to decorate

        Returns:
            Wrapped function with retry logic

        """

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return self.execute(func, *args, **kwargs)

        return wrapper
