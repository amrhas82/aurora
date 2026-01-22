"""RateLimiter using token bucket algorithm.

Implements rate limiting following PRD Section 5.3.
"""

import time


class RateLimiter:
    """Implements token bucket rate limiting.

    This class uses the token bucket algorithm to enforce rate limits:
    - Tokens are added to a bucket at a constant rate (refill_rate)
    - Each request consumes one or more tokens
    - Requests are allowed if sufficient tokens are available
    - Requests can wait for tokens to refill (with timeout)

    **Token Bucket Algorithm**:
    - Bucket capacity: max_tokens (e.g., 60 for 60 requests/minute)
    - Refill rate: requests_per_minute / 60 (tokens per second)
    - Tokens refill continuously up to max capacity
    - Requests consume tokens; if insufficient, request is denied or waits

    **Default Configuration**:
    - requests_per_minute: 60 (1 request per second)
    - max_wait_time: 60 seconds

    **Thread Safety**: This implementation is NOT thread-safe.
    For multi-threaded environments, use locks around methods.

    Example:
        >>> limiter = RateLimiter(requests_per_minute=60)
        >>> limiter.wait_if_needed()  # Blocks until token available
        >>> # Make API call
        >>>
        >>> # Or use as context manager:
        >>> with limiter:
        >>>     # Make API call

    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        max_wait_time: float = 60.0,
    ):
        """Initialize the RateLimiter.

        Args:
            requests_per_minute: Maximum requests allowed per minute (must be > 0)
            max_wait_time: Maximum time to wait for token in seconds (must be > 0)

        Raises:
            ValueError: If parameters are invalid

        """
        if requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be positive")
        if max_wait_time <= 0:
            raise ValueError("max_wait_time must be positive")

        self.max_tokens = requests_per_minute
        self.refill_rate = requests_per_minute / 60.0  # tokens per second
        self.max_wait_time = max_wait_time

        # Initialize with full bucket
        self.current_tokens = float(self.max_tokens)
        self._last_refill_time = time.time()

    def _refill_tokens(self) -> None:
        """Refill tokens based on time elapsed since last refill.

        Tokens are added at refill_rate per second, capped at max_tokens.
        """
        now = time.time()
        time_elapsed = now - self._last_refill_time

        # Calculate tokens to add
        tokens_to_add = time_elapsed * self.refill_rate

        # Add tokens and cap at max
        self.current_tokens = min(self.current_tokens + tokens_to_add, self.max_tokens)

        self._last_refill_time = now

    def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens without blocking.

        Args:
            tokens: Number of tokens to acquire (default 1, must be > 0)

        Returns:
            True if tokens were acquired, False if insufficient tokens

        Raises:
            ValueError: If tokens <= 0

        """
        if tokens <= 0:
            raise ValueError("tokens must be positive")

        # Refill tokens based on elapsed time
        self._refill_tokens()

        # Check if sufficient tokens available
        if self.current_tokens >= tokens:
            self.current_tokens -= tokens
            return True

        return False

    def wait_if_needed(self, tokens: int = 1) -> None:
        """Wait until tokens are available, then acquire them.

        Blocks until sufficient tokens are available or timeout is exceeded.

        Args:
            tokens: Number of tokens to acquire (default 1, must be > 0)

        Raises:
            ValueError: If tokens <= 0
            TimeoutError: If wait time would exceed max_wait_time

        """
        if tokens <= 0:
            raise ValueError("tokens must be positive")

        # Refill tokens based on elapsed time
        self._refill_tokens()

        # Check if we need to wait
        if self.current_tokens >= tokens:
            # Sufficient tokens available
            self.current_tokens -= tokens
            return

        # Calculate wait time needed
        tokens_needed = tokens - self.current_tokens
        wait_time = tokens_needed / self.refill_rate

        # Check if wait time exceeds maximum
        if wait_time > self.max_wait_time:
            raise TimeoutError(
                f"Rate limit wait time would exceed max_wait_time "
                f"({wait_time:.2f}s > {self.max_wait_time:.2f}s)",
            )

        # Wait for tokens to refill
        time.sleep(wait_time)

        # Refill and acquire
        self._refill_tokens()
        self.current_tokens -= tokens

    def reset(self) -> None:
        """Reset the rate limiter to full capacity."""
        self.current_tokens = float(self.max_tokens)
        self._last_refill_time = time.time()

    def __enter__(self) -> "RateLimiter":
        """Context manager entry: wait for and acquire one token.

        Example:
            >>> with limiter:
            >>>     # Make rate-limited API call

        """
        self.wait_if_needed()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Context manager exit: no cleanup needed."""
