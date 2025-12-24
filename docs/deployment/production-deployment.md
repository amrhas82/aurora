# AURORA Production Deployment Guide

**Version**: 1.0
**Date**: December 23, 2025
**Status**: Production Ready

---

## Executive Summary

This guide covers deploying AURORA in production environments with monitoring, alerting, rate limiting, and error recovery configured for reliability and performance at scale.

**Production Requirements**:
- Error recovery rate ≥95% for transient failures
- Rate limiting to prevent API abuse
- Metrics collection and alerting
- High availability configuration
- Security hardening

---

## Quick Start

### Minimum Production Configuration

```python
from aurora_core.resilience import (
    RetryHandler, RateLimiter, MetricsCollector, Alerting, AlertRule, AlertSeverity
)

# 1. Retry handler for transient errors
retry_handler = RetryHandler(
    max_retries=3,
    base_delay_ms=100,
    max_delay_ms=5000,
    backoff_multiplier=2.0
)

# 2. Rate limiter (60 requests/minute)
rate_limiter = RateLimiter(
    requests_per_minute=60,
    max_wait_time=60.0
)

# 3. Metrics collector
metrics_collector = MetricsCollector()

# 4. Alerting system
alerting = Alerting()
alerting.add_default_rules()  # Error rate, latency, cache hit rate

# 5. Use in production
def production_retrieve(query, chunks):
    """Production-ready retrieval with all resilience features."""
    # Rate limiting
    rate_limiter.wait_if_needed()

    # Retry with exponential backoff
    def _retrieve():
        start = time.time()
        try:
            results = retriever.retrieve(chunks, query)
            latency_ms = (time.time() - start) * 1000
            metrics_collector.record_query(latency_ms, success=True)
            return results
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            metrics_collector.record_query(latency_ms, success=False)
            raise

    results = retry_handler.execute_with_retry(_retrieve)

    # Check alerts
    metrics = metrics_collector.get_metrics()
    alerts = alerting.check_metrics(metrics)
    for alert in alerts:
        logging.warning(f"ALERT: {alert.message}")

    return results
```

---

## Monitoring Setup

### 1. Metrics Collection

```python
from aurora_core.resilience import MetricsCollector

collector = MetricsCollector()

# After each query
collector.record_query(latency_ms=250, success=True)

# After cache access
collector.record_cache_access(hit=True)

# After error
collector.record_error(error_type="TimeoutError")

# Get aggregated metrics
metrics = collector.get_metrics()
print(f"Total queries: {metrics['query_count']}")
print(f"Success rate: {metrics['success_rate']:.1%}")
print(f"Avg latency: {metrics['avg_latency_ms']:.1f}ms")
print(f"P95 latency: {metrics['p95_latency_ms']:.1f}ms")
print(f"Cache hit rate: {metrics['cache_hit_rate']:.1%}")
print(f"Error rate: {metrics['error_rate']:.1%}")
```

**Key Metrics to Monitor**:
- **query_count**: Total queries processed
- **success_rate**: % of queries that succeeded
- **avg_latency_ms**: Average query latency
- **p95_latency_ms**: 95th percentile latency (SLA target)
- **p99_latency_ms**: 99th percentile latency
- **cache_hit_rate**: % of cache hits
- **error_rate**: % of queries that failed

---

### 2. Alerting Rules

```python
from aurora_core.resilience import AlertRule, AlertSeverity, Alerting

alerting = Alerting()

# High error rate (>5%)
alerting.add_rule(AlertRule(
    name="high_error_rate",
    metric_name="error_rate",
    threshold=0.05,
    comparison="gt",
    severity=AlertSeverity.WARNING,
    description="Error rate exceeds 5%"
))

# High latency (p95 >10s)
alerting.add_rule(AlertRule(
    name="high_latency_p95",
    metric_name="p95_latency_ms",
    threshold=10000,
    comparison="gt",
    severity=AlertSeverity.WARNING,
    description="P95 latency exceeds 10 seconds"
))

# Low cache hit rate (<20%)
alerting.add_rule(AlertRule(
    name="low_cache_hit_rate",
    metric_name="cache_hit_rate",
    threshold=0.20,
    comparison="lt",
    severity=AlertSeverity.INFO,
    description="Cache hit rate below 20%"
))

# Critical error rate (>20%)
alerting.add_rule(AlertRule(
    name="critical_error_rate",
    metric_name="error_rate",
    threshold=0.20,
    comparison="gt",
    severity=AlertSeverity.CRITICAL,
    description="CRITICAL: Error rate exceeds 20%"
))

# Check alerts periodically
metrics = collector.get_metrics()
alerts = alerting.check_metrics(metrics)

for alert in alerts:
    if alert.severity == AlertSeverity.CRITICAL:
        send_pagerduty_alert(alert)
    elif alert.severity == AlertSeverity.WARNING:
        send_slack_alert(alert)
    else:
        logging.info(f"Alert: {alert.message}")
```

---

### 3. Rate Limiting Configuration

```python
from aurora_core.resilience import RateLimiter

# Configure based on LLM provider limits
rate_limiter = RateLimiter(
    requests_per_minute=60,  # Match provider limit
    max_wait_time=60.0       # Max wait for token
)

# Use as context manager
with rate_limiter:
    results = make_llm_call()

# Or explicit wait
rate_limiter.wait_if_needed()
results = make_llm_call()

# Check if would be rate limited (no blocking)
if rate_limiter.would_rate_limit():
    # Queue for later or return cached result
    return cached_result
```

**Provider Rate Limits**:
- OpenAI GPT-4: 60 RPM (requests per minute)
- OpenAI GPT-3.5: 3500 RPM
- Anthropic Claude: 50 RPM
- Custom deployments: Varies

**Configuration**:
```python
# Conservative (avoid rate limit errors)
RateLimiter(requests_per_minute=50)

# Aggressive (maximize throughput)
RateLimiter(requests_per_minute=59)

# Multiple tiers
gpt4_limiter = RateLimiter(requests_per_minute=60)
gpt35_limiter = RateLimiter(requests_per_minute=3500)
```

---

## Error Recovery

### Retry Handler

```python
from aurora_core.resilience import RetryHandler, RetryError

handler = RetryHandler(
    max_retries=3,              # Retry up to 3 times
    base_delay_ms=100,          # Start with 100ms delay
    max_delay_ms=5000,          # Cap at 5 seconds
    backoff_multiplier=2.0      # Exponential: 100ms, 200ms, 400ms
)

# Classify errors
handler.add_recoverable_error(TimeoutError)
handler.add_recoverable_error(ConnectionError)
handler.add_recoverable_error("RateLimitError")

handler.add_non_recoverable_error(ValueError)
handler.add_non_recoverable_error(AuthenticationError)

# Execute with retry
try:
    result = handler.execute_with_retry(lambda: make_api_call())
except RetryError as e:
    logging.error(f"Failed after {e.attempts} attempts: {e.last_error}")
```

**Backoff Sequence**:
```
Attempt 1: Immediate (0ms delay)
  ↓ Fails
Attempt 2: 100ms delay
  ↓ Fails
Attempt 3: 200ms delay (100ms × 2)
  ↓ Fails
Attempt 4: 400ms delay (200ms × 2)
  ↓ Fails (max retries reached)
→ RetryError raised
```

**Recovery Rate**: Target ≥95% for transient errors

---

## Security Configuration

### 1. API Key Management

```python
import os

# Never hardcode API keys
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")

# Use key management service in production
from cloud_kms import get_secret
api_key = get_secret("openai_api_key")
```

### 2. Input Validation

```python
def validate_query(query: str) -> str:
    """Validate and sanitize user queries."""
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")

    if len(query) > 10000:
        raise ValueError("Query exceeds maximum length (10K chars)")

    # Remove potential injection attacks
    query = query.replace("```", "")  # No code blocks
    query = query.replace("<script>", "")  # No script tags

    return query.strip()
```

### 3. Output Sanitization

```python
def sanitize_code_output(code: str) -> str:
    """Sanitize generated code before execution."""
    # Block dangerous operations
    dangerous_patterns = [
        "os.system",
        "subprocess.call",
        "eval(",
        "exec(",
        "__import__"
    ]

    for pattern in dangerous_patterns:
        if pattern in code:
            raise SecurityError(f"Dangerous pattern detected: {pattern}")

    return code
```

---

## High Availability

### 1. Database Redundancy

```python
# Primary + replica configuration
from aurora_core.store import SQLiteStore

primary_store = SQLiteStore("primary.db")
replica_store = SQLiteStore("replica.db")

def resilient_retrieve(chunks, query):
    """Try primary, fallback to replica."""
    try:
        return primary_store.get_chunks(chunks)
    except Exception as e:
        logging.warning(f"Primary failed: {e}, using replica")
        return replica_store.get_chunks(chunks)
```

### 2. Circuit Breaker

```python
class CircuitBreaker:
    """Prevent cascading failures."""
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def call(self, func):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpen("Circuit breaker is OPEN")

        try:
            result = func()
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
            raise
```

---

## Deployment Checklist

### Pre-Deployment
- [ ] All tests passing (pytest)
- [ ] No security vulnerabilities (bandit scan)
- [ ] Type checking passes (mypy)
- [ ] Linting clean (ruff)
- [ ] Performance benchmarks meet targets
- [ ] Documentation up-to-date

### Configuration
- [ ] API keys in environment variables / secrets manager
- [ ] Rate limiting configured for LLM provider
- [ ] Retry handler with appropriate backoff
- [ ] Metrics collection enabled
- [ ] Alerting rules configured
- [ ] Log aggregation setup (e.g., CloudWatch, Datadog)

### Monitoring
- [ ] Dashboard created (Grafana, Datadog, etc.)
- [ ] Alerts routed to on-call (PagerDuty, Slack)
- [ ] SLO/SLA defined and tracked
- [ ] Runbooks created for common issues

### Backup & Recovery
- [ ] Database backups automated
- [ ] Cache invalidation strategy
- [ ] Rollback plan documented
- [ ] Disaster recovery tested

---

## Production Environment Variables

```bash
# LLM Configuration
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL="gpt-4-turbo-preview"
export OPENAI_MAX_TOKENS="4096"

# Rate Limiting
export AURORA_RATE_LIMIT_RPM="60"
export AURORA_RATE_LIMIT_MAX_WAIT="60"

# Retry Configuration
export AURORA_MAX_RETRIES="3"
export AURORA_RETRY_BASE_DELAY_MS="100"
export AURORA_RETRY_MAX_DELAY_MS="5000"

# Caching
export AURORA_CACHE_HOT_SIZE="2000"
export AURORA_CACHE_TTL="600"
export AURORA_CACHE_PATH="/var/lib/aurora/cache.db"

# Monitoring
export AURORA_METRICS_ENABLED="true"
export AURORA_METRICS_PORT="9090"
export AURORA_LOG_LEVEL="INFO"

# Security
export AURORA_ENABLE_SECURITY_SCAN="true"
export AURORA_MAX_QUERY_LENGTH="10000"
```

---

## Logging Configuration

```python
import logging
import json

# Structured logging for production
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        if hasattr(record, "query_id"):
            log_data["query_id"] = record.query_id
        if hasattr(record, "latency_ms"):
            log_data["latency_ms"] = record.latency_ms
        return json.dumps(log_data)

# Configure
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.root.addHandler(handler)
logging.root.setLevel(logging.INFO)
```

---

## Performance SLAs

### Target SLAs

| Metric | Target | Alert Threshold |
|--------|--------|----------------|
| Availability | 99.9% | <99.5% |
| P95 Latency | <500ms | >1000ms |
| Error Rate | <1% | >5% |
| Cache Hit Rate | >30% | <20% |

### Monitoring Queries

```python
# Daily SLA report
def generate_sla_report():
    metrics = collector.get_metrics_last_24h()

    availability = 1 - metrics['error_rate']
    meets_latency = metrics['p95_latency_ms'] < 500
    meets_error_rate = metrics['error_rate'] < 0.01

    return {
        "availability": f"{availability:.2%}",
        "p95_latency": f"{metrics['p95_latency_ms']:.0f}ms",
        "error_rate": f"{metrics['error_rate']:.2%}",
        "sla_met": all([
            availability >= 0.999,
            meets_latency,
            meets_error_rate
        ])
    }
```

---

**Document Version**: 1.0
**Last Updated**: December 23, 2025
**Related Tasks**: Task 8.7, Task 8.8
