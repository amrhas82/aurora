"""
Unit tests for MetricsCollector class.

Tests performance and reliability metrics tracking.
"""

import pytest
from aurora_core.resilience.metrics_collector import MetricsCollector


class TestMetricsCollectorInitialization:
    """Test MetricsCollector initialization."""

    def test_default_initialization(self):
        """Test MetricsCollector starts with zero metrics."""
        collector = MetricsCollector()

        metrics = collector.get_metrics()

        assert metrics["queries"]["total"] == 0
        assert metrics["queries"]["success"] == 0
        assert metrics["queries"]["failed"] == 0
        assert metrics["queries"]["avg_latency"] == 0.0
        assert metrics["queries"]["p95_latency"] == 0.0

        assert metrics["cache"]["hits"] == 0
        assert metrics["cache"]["misses"] == 0
        assert metrics["cache"]["hit_rate"] == 0.0

        assert metrics["errors"]["total"] == 0
        assert metrics["errors"]["error_rate"] == 0.0


class TestMetricsCollectorQueryTracking:
    """Test query metrics tracking."""

    def test_record_query_success(self):
        """Test recording successful query."""
        collector = MetricsCollector()

        collector.record_query(success=True, latency=0.5)

        metrics = collector.get_metrics()
        assert metrics["queries"]["total"] == 1
        assert metrics["queries"]["success"] == 1
        assert metrics["queries"]["failed"] == 0
        assert metrics["queries"]["avg_latency"] == 0.5
        assert metrics["queries"]["p95_latency"] == 0.5

    def test_record_query_failure(self):
        """Test recording failed query."""
        collector = MetricsCollector()

        collector.record_query(success=False, latency=1.0)

        metrics = collector.get_metrics()
        assert metrics["queries"]["total"] == 1
        assert metrics["queries"]["success"] == 0
        assert metrics["queries"]["failed"] == 1
        assert metrics["queries"]["avg_latency"] == 1.0

    def test_record_multiple_queries(self):
        """Test recording multiple queries."""
        collector = MetricsCollector()

        collector.record_query(success=True, latency=0.5)
        collector.record_query(success=True, latency=1.5)
        collector.record_query(success=False, latency=2.0)

        metrics = collector.get_metrics()
        assert metrics["queries"]["total"] == 3
        assert metrics["queries"]["success"] == 2
        assert metrics["queries"]["failed"] == 1
        # Average latency = (0.5 + 1.5 + 2.0) / 3 = 1.333...
        assert abs(metrics["queries"]["avg_latency"] - 1.333) < 0.01

    def test_calculate_average_latency(self):
        """Test average latency calculation."""
        collector = MetricsCollector()

        collector.record_query(success=True, latency=1.0)
        collector.record_query(success=True, latency=2.0)
        collector.record_query(success=True, latency=3.0)

        metrics = collector.get_metrics()
        assert metrics["queries"]["avg_latency"] == 2.0

    def test_calculate_p95_latency(self):
        """Test p95 latency calculation."""
        collector = MetricsCollector()

        # Add 100 queries with latencies from 0.01 to 1.0
        for i in range(100):
            latency = (i + 1) * 0.01
            collector.record_query(success=True, latency=latency)

        metrics = collector.get_metrics()
        # P95 should be around 0.95 (95th percentile)
        assert 0.94 <= metrics["queries"]["p95_latency"] <= 0.96

    def test_p95_with_small_sample(self):
        """Test p95 calculation with small sample size."""
        collector = MetricsCollector()

        collector.record_query(success=True, latency=1.0)
        collector.record_query(success=True, latency=2.0)

        metrics = collector.get_metrics()
        # With small sample, p95 should be near max
        assert metrics["queries"]["p95_latency"] == 2.0

    def test_invalid_latency(self):
        """Test validation of latency values."""
        collector = MetricsCollector()

        with pytest.raises(ValueError, match="latency must be non-negative"):
            collector.record_query(success=True, latency=-1.0)


class TestMetricsCollectorCacheTracking:
    """Test cache metrics tracking."""

    def test_record_cache_hit(self):
        """Test recording cache hit."""
        collector = MetricsCollector()

        collector.record_cache_hit()

        metrics = collector.get_metrics()
        assert metrics["cache"]["hits"] == 1
        assert metrics["cache"]["misses"] == 0
        assert metrics["cache"]["hit_rate"] == 1.0

    def test_record_cache_miss(self):
        """Test recording cache miss."""
        collector = MetricsCollector()

        collector.record_cache_miss()

        metrics = collector.get_metrics()
        assert metrics["cache"]["hits"] == 0
        assert metrics["cache"]["misses"] == 1
        assert metrics["cache"]["hit_rate"] == 0.0

    def test_calculate_hit_rate(self):
        """Test cache hit rate calculation."""
        collector = MetricsCollector()

        # 7 hits, 3 misses = 70% hit rate
        for _ in range(7):
            collector.record_cache_hit()
        for _ in range(3):
            collector.record_cache_miss()

        metrics = collector.get_metrics()
        assert metrics["cache"]["hits"] == 7
        assert metrics["cache"]["misses"] == 3
        assert abs(metrics["cache"]["hit_rate"] - 0.7) < 0.01

    def test_hit_rate_with_no_accesses(self):
        """Test hit rate when no cache accesses recorded."""
        collector = MetricsCollector()

        metrics = collector.get_metrics()
        assert metrics["cache"]["hit_rate"] == 0.0


class TestMetricsCollectorErrorTracking:
    """Test error metrics tracking."""

    def test_record_error(self):
        """Test recording error."""
        collector = MetricsCollector()

        collector.record_error("TimeoutError")

        metrics = collector.get_metrics()
        assert metrics["errors"]["total"] == 1

    def test_record_multiple_errors(self):
        """Test recording multiple errors."""
        collector = MetricsCollector()

        collector.record_error("TimeoutError")
        collector.record_error("ConnectionError")
        collector.record_error("TimeoutError")

        metrics = collector.get_metrics()
        assert metrics["errors"]["total"] == 3
        assert metrics["errors"]["by_type"]["TimeoutError"] == 2
        assert metrics["errors"]["by_type"]["ConnectionError"] == 1

    def test_calculate_error_rate(self):
        """Test error rate calculation."""
        collector = MetricsCollector()

        # 7 successful queries, 3 failures
        for _ in range(7):
            collector.record_query(success=True, latency=0.1)
        for _ in range(3):
            collector.record_query(success=False, latency=0.1)

        metrics = collector.get_metrics()
        # Error rate = 3 / 10 = 0.3
        assert abs(metrics["errors"]["error_rate"] - 0.3) < 0.01

    def test_error_rate_with_no_queries(self):
        """Test error rate when no queries recorded."""
        collector = MetricsCollector()

        metrics = collector.get_metrics()
        assert metrics["errors"]["error_rate"] == 0.0

    def test_error_rate_all_success(self):
        """Test error rate with all successful queries."""
        collector = MetricsCollector()

        for _ in range(10):
            collector.record_query(success=True, latency=0.1)

        metrics = collector.get_metrics()
        assert metrics["errors"]["error_rate"] == 0.0

    def test_error_rate_all_failures(self):
        """Test error rate with all failed queries."""
        collector = MetricsCollector()

        for _ in range(10):
            collector.record_query(success=False, latency=0.1)

        metrics = collector.get_metrics()
        assert metrics["errors"]["error_rate"] == 1.0


class TestMetricsCollectorReset:
    """Test metrics reset functionality."""

    def test_reset_metrics(self):
        """Test resetting all metrics to zero."""
        collector = MetricsCollector()

        # Record some metrics
        collector.record_query(success=True, latency=1.0)
        collector.record_cache_hit()
        collector.record_error("TimeoutError")

        # Reset
        collector.reset()

        # Verify all metrics are zero
        metrics = collector.get_metrics()
        assert metrics["queries"]["total"] == 0
        assert metrics["cache"]["hits"] == 0
        assert metrics["errors"]["total"] == 0


class TestMetricsCollectorSnapshot:
    """Test metrics snapshot functionality."""

    def test_get_metrics_returns_copy(self):
        """Test that get_metrics() returns a copy, not reference."""
        collector = MetricsCollector()

        collector.record_query(success=True, latency=1.0)

        metrics1 = collector.get_metrics()
        metrics2 = collector.get_metrics()

        # Modifying one should not affect the other
        metrics1["queries"]["total"] = 999

        assert metrics2["queries"]["total"] == 1

    def test_get_metrics_consistent(self):
        """Test that metrics snapshot is consistent."""
        collector = MetricsCollector()

        # Record metrics
        for i in range(10):
            collector.record_query(success=True, latency=i * 0.1)

        metrics = collector.get_metrics()

        # Verify internal consistency
        assert metrics["queries"]["total"] == 10
        assert metrics["queries"]["success"] == 10
        assert metrics["queries"]["failed"] == 0


class TestMetricsCollectorEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_latency(self):
        """Test recording query with zero latency."""
        collector = MetricsCollector()

        collector.record_query(success=True, latency=0.0)

        metrics = collector.get_metrics()
        assert metrics["queries"]["avg_latency"] == 0.0

    def test_very_large_latency(self):
        """Test recording query with very large latency."""
        collector = MetricsCollector()

        collector.record_query(success=True, latency=1000.0)

        metrics = collector.get_metrics()
        assert metrics["queries"]["avg_latency"] == 1000.0

    def test_many_queries(self):
        """Test recording many queries (performance check)."""
        collector = MetricsCollector()

        # Record 10,000 queries
        for _i in range(10000):
            collector.record_query(success=True, latency=0.1)

        metrics = collector.get_metrics()
        assert metrics["queries"]["total"] == 10000

    def test_concurrent_access_simulation(self):
        """Test simulated concurrent access (thread-safety check)."""
        collector = MetricsCollector()

        # Simulate concurrent recording
        for _i in range(100):
            collector.record_query(success=True, latency=0.1)
            collector.record_cache_hit()
            collector.record_error("Error")

        metrics = collector.get_metrics()
        assert metrics["queries"]["total"] == 100
        assert metrics["cache"]["hits"] == 100
        assert metrics["errors"]["total"] == 100


class TestMetricsCollectorExport:
    """Test metrics export functionality."""

    def test_export_format(self):
        """Test that exported metrics have correct structure."""
        collector = MetricsCollector()

        collector.record_query(success=True, latency=1.0)
        collector.record_cache_hit()
        collector.record_error("TimeoutError")

        metrics = collector.get_metrics()

        # Verify structure
        assert "queries" in metrics
        assert "cache" in metrics
        assert "errors" in metrics

        assert all(
            k in metrics["queries"]
            for k in ["total", "success", "failed", "avg_latency", "p95_latency"]
        )
        assert all(k in metrics["cache"] for k in ["hits", "misses", "hit_rate"])
        assert all(k in metrics["errors"] for k in ["total", "error_rate", "by_type"])
