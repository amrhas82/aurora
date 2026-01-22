"""MetricsCollector for tracking performance and reliability metrics.

Implements metrics collection following PRD Section 5.2.
"""

from collections import defaultdict
from typing import Any


class MetricsCollector:
    """Collects and tracks performance and reliability metrics.

    This class provides centralized metrics collection for:
    - Query performance (total, success, failed, latency, p95)
    - Cache performance (hits, misses, hit rate)
    - Error tracking (total errors, error rate, errors by type)

    **Thread Safety**: This implementation is NOT thread-safe.
    For multi-threaded environments, use locks around record_* methods.

    **Metrics Tracked**:

    Query Metrics:
    - total: Total number of queries
    - success: Number of successful queries
    - failed: Number of failed queries
    - avg_latency: Average query latency in seconds
    - p95_latency: 95th percentile latency in seconds

    Cache Metrics:
    - hits: Number of cache hits
    - misses: Number of cache misses
    - hit_rate: Cache hit rate (hits / total_accesses)

    Error Metrics:
    - total: Total number of errors
    - error_rate: Error rate (failed_queries / total_queries)
    - by_type: Error counts grouped by error type

    Example:
        >>> collector = MetricsCollector()
        >>> collector.record_query(success=True, latency=0.5)
        >>> collector.record_cache_hit()
        >>> metrics = collector.get_metrics()
        >>> print(f"Average latency: {metrics['queries']['avg_latency']}")

    """

    def __init__(self) -> None:
        """Initialize the MetricsCollector with zero metrics."""
        self.reset()

    def reset(self) -> None:
        """Reset all metrics to zero."""
        # Query metrics
        self._total_queries = 0
        self._successful_queries = 0
        self._failed_queries = 0
        self._latencies: list[float] = []

        # Cache metrics
        self._cache_hits = 0
        self._cache_misses = 0

        # Error metrics
        self._total_errors = 0
        self._errors_by_type: dict[str, int] = defaultdict(int)

    def record_query(self, success: bool, latency: float) -> None:
        """Record a query execution.

        Args:
            success: True if query succeeded, False if failed
            latency: Query latency in seconds

        Raises:
            ValueError: If latency is negative

        """
        if latency < 0:
            raise ValueError("latency must be non-negative")

        self._total_queries += 1
        if success:
            self._successful_queries += 1
        else:
            self._failed_queries += 1

        self._latencies.append(latency)

    def record_cache_hit(self) -> None:
        """Record a cache hit."""
        self._cache_hits += 1

    def record_cache_miss(self) -> None:
        """Record a cache miss."""
        self._cache_misses += 1

    def record_error(self, error_type: str) -> None:
        """Record an error occurrence.

        Args:
            error_type: The type of error (e.g., "TimeoutError", "ConnectionError")

        """
        self._total_errors += 1
        self._errors_by_type[error_type] += 1

    def get_metrics(self) -> dict[str, Any]:
        """Get a snapshot of current metrics.

        Returns:
            Dictionary containing all metrics with structure:
            {
                "queries": {
                    "total": int,
                    "success": int,
                    "failed": int,
                    "avg_latency": float,
                    "p95_latency": float
                },
                "cache": {
                    "hits": int,
                    "misses": int,
                    "hit_rate": float
                },
                "errors": {
                    "total": int,
                    "error_rate": float,
                    "by_type": dict[str, int]
                }
            }

        """
        return {
            "queries": {
                "total": self._total_queries,
                "success": self._successful_queries,
                "failed": self._failed_queries,
                "avg_latency": self._calculate_avg_latency(),
                "p95_latency": self._calculate_p95_latency(),
            },
            "cache": {
                "hits": self._cache_hits,
                "misses": self._cache_misses,
                "hit_rate": self._calculate_cache_hit_rate(),
            },
            "errors": {
                "total": self._total_errors,
                "error_rate": self._calculate_error_rate(),
                "by_type": dict(self._errors_by_type),  # Return a copy
            },
        }

    def _calculate_avg_latency(self) -> float:
        """Calculate average latency across all queries."""
        if not self._latencies:
            return 0.0
        return sum(self._latencies) / len(self._latencies)

    def _calculate_p95_latency(self) -> float:
        """Calculate 95th percentile latency.

        Returns:
            The 95th percentile latency, or 0.0 if no latencies recorded

        """
        if not self._latencies:
            return 0.0

        sorted_latencies = sorted(self._latencies)
        index = int(len(sorted_latencies) * 0.95)

        # Handle edge case where index equals length
        if index >= len(sorted_latencies):
            index = len(sorted_latencies) - 1

        return sorted_latencies[index]

    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total_accesses = self._cache_hits + self._cache_misses
        if total_accesses == 0:
            return 0.0
        return self._cache_hits / total_accesses

    def _calculate_error_rate(self) -> float:
        """Calculate error rate (failed queries / total queries)."""
        if self._total_queries == 0:
            return 0.0
        return self._failed_queries / self._total_queries
