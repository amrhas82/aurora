# Cache Metrics and Observability Guide

## Overview

The PlanDecompositionCache includes comprehensive observability features for monitoring cache effectiveness, performance, and behavior.

## Quick Start

```python
from aurora_cli.planning.cache import PlanDecompositionCache

# Enable metrics (default)
cache = PlanDecompositionCache(
    capacity=100,
    ttl_hours=24,
    persistent_path=Path(".aurora/cache.db"),
    enable_metrics=True
)

# Perform operations
cache.set(goal, complexity, subgoals, "soar")
result = cache.get(goal, complexity)

# Check metrics
stats = cache.get_stats()
print(f"Hit rate: {stats['hit_rate']:.1%}")
print(f"Avg latency: {stats['avg_get_latency_ms']:.2f}ms")

# Log summary
cache.log_performance_summary()
```

## Metrics Categories

### Basic Counters
- `hits`: Total cache hits
- `misses`: Total cache misses
- `size`: Current entries in cache
- `capacity`: Maximum cache capacity
- `evictions`: Number of LRU evictions

### Hit Sources
- `memory_hits`: Hits from in-memory cache
- `persistent_hits`: Hits from persistent storage
- `expired_hits`: Entries found but expired
- `memory_hit_rate`: Memory hit rate (0.0-1.0)
- `persistent_hit_rate`: Persistent hit rate (0.0-1.0)

### Performance Metrics
- `avg_get_latency_ms`: Average GET operation latency
- `max_get_latency_ms`: Maximum GET operation latency
- `avg_set_latency_ms`: Average SET operation latency
- `max_set_latency_ms`: Maximum SET operation latency
- `write_operations`: Total write operations

### Derived Metrics
- `hit_rate`: Overall hit rate (0.0-1.0)
- `total_operations`: Total GET operations (hits + misses)

## Structured Logging

All cache operations emit structured logs with contextual data:

### Cache HIT - memory
```python
logger.info(
    "Cache HIT - memory",
    extra={
        "cache_key": "abc123...",
        "source": "soar",
        "age_hours": 2.5,
        "access_count": 3,
        "latency_ms": 0.42,
        "subgoal_count": 5
    }
)
```

### Cache HIT - persistent
```python
logger.info(
    "Cache HIT - persistent",
    extra={
        "cache_key": "def456...",
        "source": "heuristic",
        "latency_ms": 1.23,
        "subgoal_count": 3
    }
)
```

### Cache MISS
```python
logger.info(
    "Cache MISS",
    extra={
        "cache_key": "ghi789...",
        "goal_preview": "Add authentication system...",
        "complexity": "moderate",
        "latency_ms": 0.35
    }
)
```

### Cache SET
```python
logger.info(
    "Cache SET complete",
    extra={
        "cache_key": "jkl012...",
        "source": "soar",
        "latency_ms": 1.87,
        "cache_size": 45,
        "capacity": 100
    }
)
```

### Cache Eviction
```python
logger.debug(
    "Cache eviction - LRU",
    extra={
        "evicted_key": "mno345...",
        "evicted_source": "soar",
        "evicted_age_hours": 18.2,
        "access_count": 12
    }
)
```

## Monitoring Best Practices

### 1. Performance Thresholds
```python
stats = cache.get_stats()

# Alert if hit rate drops below 40%
if stats['hit_rate'] < 0.4:
    logger.warning(
        "Cache hit rate below threshold",
        extra={"hit_rate": stats['hit_rate'], "threshold": 0.4}
    )

# Alert if latency exceeds 5ms
if stats['avg_get_latency_ms'] > 5.0:
    logger.warning(
        "Cache latency above threshold",
        extra={"latency_ms": stats['avg_get_latency_ms'], "threshold_ms": 5.0}
    )
```

### 2. Periodic Reporting
```python
import time

def monitor_cache(cache: PlanDecompositionCache, interval_seconds: int = 300):
    """Log cache metrics every interval_seconds."""
    while True:
        cache.log_performance_summary()
        time.sleep(interval_seconds)
```

### 3. Memory vs Persistent Analysis
```python
stats = cache.get_stats()

# Check balance between memory and persistent hits
if stats['persistent_hit_rate'] > 0.5:
    logger.info(
        "High persistent cache reliance - consider increasing capacity",
        extra={
            "persistent_hit_rate": stats['persistent_hit_rate'],
            "capacity": stats['capacity']
        }
    )
```

### 4. Capacity Planning
```python
stats = cache.get_stats()

# Alert if cache is frequently at capacity
utilization = stats['size'] / stats['capacity']
if utilization > 0.95 and stats['evictions'] > 10:
    logger.warning(
        "Cache near capacity with high evictions",
        extra={
            "utilization": utilization,
            "evictions": stats['evictions'],
            "capacity": stats['capacity']
        }
    )
```

## Integration with Monitoring Systems

### Prometheus Example
```python
from prometheus_client import Gauge, Counter, Histogram

cache_hit_rate = Gauge('cache_hit_rate', 'Cache hit rate')
cache_latency = Histogram('cache_latency_ms', 'Cache operation latency')
cache_operations = Counter('cache_operations', 'Total cache operations', ['result'])

def export_metrics(cache: PlanDecompositionCache):
    """Export cache metrics to Prometheus."""
    stats = cache.get_stats()

    cache_hit_rate.set(stats['hit_rate'])
    cache_latency.observe(stats['avg_get_latency_ms'])
    cache_operations.labels(result='hit').inc(stats['hits'])
    cache_operations.labels(result='miss').inc(stats['misses'])
```

### CloudWatch Example
```python
import boto3

cloudwatch = boto3.client('cloudwatch')

def publish_metrics(cache: PlanDecompositionCache):
    """Publish cache metrics to CloudWatch."""
    stats = cache.get_stats()

    cloudwatch.put_metric_data(
        Namespace='Aurora/Cache',
        MetricData=[
            {
                'MetricName': 'HitRate',
                'Value': stats['hit_rate'],
                'Unit': 'Percent'
            },
            {
                'MetricName': 'GetLatency',
                'Value': stats['avg_get_latency_ms'],
                'Unit': 'Milliseconds'
            }
        ]
    )
```

## Disable Metrics

For performance-critical scenarios or testing:

```python
# Disable metrics collection
cache = PlanDecompositionCache(
    capacity=100,
    ttl_hours=24,
    enable_metrics=False  # Minimal overhead
)

# get_stats() still works but returns basic counters only
stats = cache.get_stats()
# Returns: hits, misses, hit_rate, evictions (no latency tracking)
```

## Performance Impact

Metrics collection overhead:
- Memory: ~200 bytes per cache instance
- CPU: <1% for typical workloads
- Latency: ~0.01ms per operation

Use `enable_metrics=False` if every microsecond counts.
