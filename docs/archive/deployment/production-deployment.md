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

## Retrieval Quality Configuration

### Overview

AURORA implements a 3-tier retrieval quality handling system to prevent silent degradation when memory retrieval fails or returns weak matches:

1. **No Match (0 chunks)**: Auto-proceed with general knowledge, add context note
2. **Weak Match (groundedness < 0.7 OR < 3 high-quality chunks)**: Interactive prompt (CLI only)
3. **Good Match (groundedness ≥ 0.7 AND ≥ 3 high-quality chunks)**: Auto-proceed normally

**Production Considerations**:
- Interactive prompts are CLI-only (not in MCP tools or headless mode)
- Use `--non-interactive` flag for automation, CI/CD, and scheduled jobs
- Tune thresholds based on your project's indexing quality

---

### Activation Threshold Tuning

The activation threshold filters out low-relevance chunks during retrieval. Only chunks with activation scores ≥ threshold are returned to the user.

**Environment Variable**: `AURORA_ACTIVATION_THRESHOLD`

**Default**: `0.3` (hardcoded in `packages/soar/src/aurora_soar/phases/retrieve.py`)

**Recommended Range**: `0.2 - 0.4`

```bash
# Conservative (more chunks, may include noise)
export AURORA_ACTIVATION_THRESHOLD="0.2"

# Balanced (default)
export AURORA_ACTIVATION_THRESHOLD="0.3"

# Strict (fewer chunks, higher precision)
export AURORA_ACTIVATION_THRESHOLD="0.4"
```

**Tuning Guidance**:
- **Too low (< 0.2)**: Retrieves irrelevant chunks, increases noise, degrades response quality
- **Too high (> 0.4)**: Misses relevant matches, triggers weak match warnings frequently
- **Monitor**: Track "no match" and "weak match" rates (see Monitoring Recommendations below)

**How to Tune**:
1. Start with default (0.3)
2. If weak match rate > 50%: Lower threshold to 0.25
3. If response quality degrades (too much noise): Raise threshold to 0.35
4. Iterate based on user feedback and metrics

---

### Groundedness Threshold Tuning

The groundedness threshold determines when retrieval quality is considered "weak" and requires user confirmation (CLI interactive mode only).

**Environment Variable**: `AURORA_GROUNDEDNESS_THRESHOLD`

**Default**: `0.7` (hardcoded in `packages/soar/src/aurora_soar/phases/verify.py`)

**Recommended Range**: `0.6 - 0.8`

```bash
# Lenient (fewer weak match warnings)
export AURORA_GROUNDEDNESS_THRESHOLD="0.6"

# Balanced (default)
export AURORA_GROUNDEDNESS_THRESHOLD="0.7"

# Strict (more cautious about weak matches)
export AURORA_GROUNDEDNESS_THRESHOLD="0.8"
```

**Tuning Guidance**:
- **Too low (< 0.6)**: Accepts poor matches, users receive low-quality answers
- **Too high (> 0.8)**: Over-cautious, prompts user even for decent matches
- **Monitor**: Track user choice patterns (continue, start over, start anew)

**How to Tune**:
1. Start with default (0.7)
2. If users frequently choose "continue anyway": Lower threshold to 0.65
3. If users frequently choose "start over": Raise threshold to 0.75
4. Iterate based on user feedback

---

### Non-Interactive Mode for Production

**IMPORTANT**: Always use `--non-interactive` flag in production automation to prevent blocking on user prompts.

```bash
# CI/CD pipelines
aur query --non-interactive "What is the API contract?"

# Scheduled jobs
0 2 * * * /usr/bin/aur query --non-interactive "Daily analysis" >> /var/log/aurora.log

# Automation scripts
#!/bin/bash
for query in "${queries[@]}"; do
  aur query --non-interactive "$query" || echo "Query failed: $query"
done
```

**Behavior in Non-Interactive Mode**:
- **No Match (0 chunks)**: Auto-proceeds with general knowledge (no prompt)
- **Weak Match**: Auto-continues with weak chunks (no prompt)
- **Good Match**: Proceeds normally

**Interactive vs Non-Interactive**:

| Mode | Weak Match Behavior | Use Case |
|------|-------------------|----------|
| **Interactive** (default CLI) | Prompts user with 3 options | Human-in-loop, exploratory queries |
| **Non-Interactive** (`--non-interactive` flag) | Auto-continues | CI/CD, automation, scheduled jobs |
| **Headless** (programmatic) | Always non-interactive | Embedded systems, APIs |
| **MCP Tools** | Always non-interactive | Claude Desktop integration |

---

### Monitoring Recommendations

Track retrieval quality metrics to tune thresholds and identify indexing issues.

**Key Metrics to Monitor**:

1. **No Match Rate**: % of queries with 0 chunks retrieved
   - **Target**: < 10% (indicates good indexing coverage)
   - **Alert**: > 20% (indexing issue or irrelevant queries)

2. **Weak Match Rate**: % of queries with weak retrieval (groundedness < threshold OR < 3 high-quality chunks)
   - **Target**: < 20% (indicates good chunk quality)
   - **Alert**: > 50% (indexing issue, threshold too strict, or poor chunk granularity)

3. **Good Match Rate**: % of queries with good retrieval
   - **Target**: > 70% (indicates healthy system)
   - **Alert**: < 50% (indexing issues)

4. **User Choice Distribution** (interactive mode only):
   - **Option 1 (Start anew)**: User abandoned current context
   - **Option 2 (Start over)**: User wants to refine indexing/query
   - **Option 3 (Continue anyway)**: User accepted weak match
   - **If Option 1+2 > 60%**: Consider lowering groundedness threshold
   - **If Option 3 > 80%**: Consider raising groundedness threshold

**Monitoring Commands**:

```bash
# View retrieval quality metrics (if implemented - see Task 5.6)
aur stats --retrieval-quality

# Example output:
# Retrieval Quality Metrics (Last 7 days)
# ----------------------------------------
# Total Queries:        1,234
# No Match:              98 (7.9%)  ✓ Target < 10%
# Weak Match:           247 (20.0%) ✓ Target < 20%
# Good Match:           889 (72.1%) ✓ Target > 70%
#
# User Choices (Weak Match):
#   Start Anew:          45 (18.2%)
#   Start Over:          89 (36.0%)
#   Continue Anyway:    113 (45.7%)
#
# Avg Groundedness:      0.68
# Avg High-Quality Chunks: 4.2
```

**Log Analysis** (if metrics not available):

```bash
# Count no match occurrences
grep "no indexed context" ~/.aurora/logs/*.log | wc -l

# Count weak match prompts
grep "retrieval quality is weak" ~/.aurora/logs/*.log | wc -l

# Count total queries
grep "Query:" ~/.aurora/logs/*.log | wc -l
```

**Alert Conditions**:

```python
# Example alert rules (pseudocode)
if no_match_rate > 0.20:
    alert("WARN: High no-match rate (%.1f%%) - check indexing coverage" % (no_match_rate * 100))

if weak_match_rate > 0.50:
    alert("WARN: High weak-match rate (%.1f%%) - consider lowering ACTIVATION_THRESHOLD" % (weak_match_rate * 100))

if good_match_rate < 0.50:
    alert("CRITICAL: Low good-match rate (%.1f%%) - indexing degraded" % (good_match_rate * 100))
```

---

### Production Deployment Examples

#### Example 1: CI/CD Pipeline

```bash
# .gitlab-ci.yml
test_retrieval:
  script:
    - export AURORA_ACTIVATION_THRESHOLD="0.3"
    - export AURORA_GROUNDEDNESS_THRESHOLD="0.7"
    - aur mem index ./src
    - aur query --non-interactive "Summarize API contracts" > output.txt
    - test -s output.txt  # Ensure output is not empty
```

#### Example 2: Kubernetes Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aurora-service
spec:
  template:
    spec:
      containers:
      - name: aurora
        image: aurora:v0.2.1
        env:
        - name: AURORA_ACTIVATION_THRESHOLD
          value: "0.3"
        - name: AURORA_GROUNDEDNESS_THRESHOLD
          value: "0.7"
        - name: AURORA_NON_INTERACTIVE
          value: "true"
        command: ["aurora-headless"]
```

#### Example 3: Scheduled Analysis Job

```bash
#!/bin/bash
# daily-analysis.sh

export AURORA_ACTIVATION_THRESHOLD="0.25"  # Lower for broader coverage
export AURORA_GROUNDEDNESS_THRESHOLD="0.65" # Lower to reduce false alarms

# Index codebase
aur mem index /var/app/src

# Run daily queries (non-interactive)
aur query --non-interactive "What changed since last commit?" > /var/log/aurora/daily-$(date +%Y%m%d).txt

# Monitor metrics
no_match_count=$(grep "no indexed context" /var/log/aurora/daily-*.txt | wc -l)
total_queries=10  # Adjust based on actual count

if (( no_match_count > 2 )); then
  echo "WARNING: High no-match rate ($no_match_count/$total_queries)" | mail -s "Aurora Alert" ops@example.com
fi
```

---

### Troubleshooting

**Problem**: High weak match rate (> 50%)

**Solutions**:
1. Lower `AURORA_ACTIVATION_THRESHOLD` from 0.3 to 0.25
2. Improve indexing: `aur mem index --chunk-size 500 --overlap 100`
3. Verify chunks are semantically meaningful (not fragmented)

**Problem**: Too many "no match" results (> 20%)

**Solutions**:
1. Verify indexing completed: `aur mem stats`
2. Check chunk count: Should have 100+ chunks for medium projects
3. Re-index with better chunking strategy

**Problem**: Users frequently choose "Start over" or "Start anew"

**Solutions**:
1. Raise `AURORA_GROUNDEDNESS_THRESHOLD` from 0.7 to 0.75 (be more selective)
2. Improve chunk quality during indexing
3. Use more specific queries

**Problem**: Automation blocking on interactive prompts

**Solutions**:
1. Add `--non-interactive` flag to all automated queries
2. Verify headless mode is used for programmatic access
3. Ensure MCP tools are used (always non-interactive)

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
