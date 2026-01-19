# Early Detection Enhancement Analysis for Aurora SOAR

## Executive Summary

Aurora SOAR currently has **two independent early detection systems** that detect failures before timeout:

1. **Early Detection Monitor** (`early_detection.py`) - Non-blocking async health checks with stall detection
2. **Proactive Health Monitor** (`observability.py`) - Background thread monitoring with no-output detection

**Key Finding**: Both systems run checks every 2-5 seconds but currently only detect **stall conditions** (no output progress). They lack comprehensive signal detection for other failure patterns like error patterns, API failures, and resource issues.

## Current Architecture

### System 1: Early Detection Monitor
**Location**: `packages/spawner/src/aurora_spawner/early_detection.py`

**Features**:
- Non-blocking async monitoring loop
- Check interval: 2 seconds (configurable)
- Stall threshold: 15 seconds (configurable)
- Tracks stdout/stderr sizes for activity detection

**Limitations**:
- Only detects **stalls** (no output progress after 15s)
- Does NOT scan stderr for error patterns
- Does NOT detect API failures, connection errors
- Requires 2 consecutive stall detections to trigger (30s total)

### System 2: Proactive Health Monitor
**Location**: `packages/spawner/src/aurora_spawner/observability.py`

**Features**:
- Background thread monitoring (daemon)
- Check interval: 5 seconds (configurable)
- No-output threshold: 120 seconds (for LLM thinking time)
- Tracks execution metrics and failure reasons

**Limitations**:
- Only detects **no-output conditions** (120s threshold)
- Does NOT analyze stderr content
- Does NOT detect error patterns
- `terminate_on_failure` is DISABLED (line 352)

### Integration Point: Spawner Main Loop
**Location**: `packages/spawner/src/aurora_spawner/spawner.py:225-343`

The spawner checks BOTH monitors in sequence:

```python
# Line 234: Check early detection monitor
should_terminate_early, early_reason = await early_monitor.should_terminate(task_id)

# Line 251: Check proactive health monitor
should_terminate_health, health_reason = health_monitor.should_terminate(task_id)
```

**Problem**: Both return `(False, None)` for most failure patterns because they only detect stalls/no-output.

## Gap Analysis

### Missing Detection Signals

1. **Stderr Error Patterns** (NOT IMPLEMENTED)
   - API authentication failures (401, 403)
   - Rate limiting (429, "too many requests")
   - Connection errors ("connection refused", "timeout")
   - Invalid parameters ("invalid", "malformed")
   - Resource exhaustion ("out of memory")

2. **Stdout Error Patterns** (NOT IMPLEMENTED)
   - Stack traces
   - Exception messages
   - Error prefixes ("ERROR:", "FATAL:")

3. **Process Health** (NOT IMPLEMENTED)
   - Process exit detection
   - Zombie process detection
   - Memory limit checks (configured but unused)

4. **Behavioral Patterns** (PARTIAL)
   - Rapid repeated failures (detected by circuit breaker)
   - Output cycling/looping (NOT detected)
   - Premature termination (NOT detected)

## Detection Latency Analysis

### Current Detection Times

| Failure Type | Detection Method | Time to Detect |
|-------------|------------------|----------------|
| Stall (no output) | Early Detection | 30s (2x15s checks) |
| No output | Proactive Health | 360s (3x120s) |
| API errors | **None** | Timeout (300s) |
| Connection errors | **None** | Timeout (300s) |
| Rate limiting | **None** | Timeout (300s) |
| Process crash | **None** | Immediate (return code) |

### Target Detection Times

| Failure Type | Target Detection | Improvement |
|-------------|------------------|-------------|
| Stall | 15s | 2x faster |
| API errors | 2-5s | **60x faster** |
| Connection errors | 2-5s | **60x faster** |
| Rate limiting | 2-5s | **60x faster** |
| Invalid params | 2-5s | **60x faster** |

## Recommended Implementation

### Phase 1: Enhance Early Detection Monitor

**Location**: `packages/spawner/src/aurora_spawner/early_detection.py`

**Changes**:
1. Add stderr pattern matching to `_check_execution()` (line 247)
2. Implement progressive detection:
   - Critical errors → terminate immediately (2-5s)
   - Warning patterns → increase check frequency
   - Stall patterns → existing logic (30s)

**Pattern Categories**:

```python
CRITICAL_PATTERNS = [
    r"401 Unauthorized",
    r"403 Forbidden",
    r"Connection refused",
    r"ECONNREFUSED",
    r"Invalid API key",
    r"Authentication failed"
]

WARNING_PATTERNS = [
    r"429 Too Many Requests",
    r"Rate limit exceeded",
    r"Timeout.*request",
    r"Retrying in \d+ seconds"
]

ERROR_PATTERNS = [
    r"ERROR:",
    r"FATAL:",
    r"Exception in thread",
    r"Traceback \(most recent call last\)"
]
```

### Phase 2: Enable Proactive Termination

**Location**: `packages/spawner/src/aurora_spawner/observability.py:352`

**Current**:
```python
if not self._proactive_config.terminate_on_failure:
    return False, None  # DISABLED
```

**Proposed**:
```python
# Enable termination for critical failures only
if state.consecutive_failures >= self._proactive_config.failure_threshold:
    return True, state.termination_reason
```

### Phase 3: Unified Signal Handler

Create new module: `packages/spawner/src/aurora_spawner/signal_detection.py`

```python
class FailureSignalDetector:
    """Unified failure signal detection across stdout/stderr."""

    def analyze_output(self, stdout: str, stderr: str) -> tuple[bool, str, str]:
        """
        Returns:
            (should_terminate, reason, severity)
            severity: "critical" | "warning" | "info"
        """
```

### Phase 4: Progressive Timeout Strategy

**Current**: Fixed timeout OR progressive extension based on activity
**Proposed**: Risk-based timeout adjustment

```python
class AdaptiveTimeoutPolicy:
    """Adjust timeouts based on detected signals."""

    - Reduce timeout on warning patterns (e.g., 300s → 60s)
    - Extend timeout on progress signals (existing)
    - Immediate kill on critical patterns (new)
```

## Configuration Schema

### Proposed Config Structure

```python
early_detection:
  enabled: true
  check_interval: 2.0  # seconds
  stall_threshold: 15.0

  # NEW: Pattern detection
  pattern_detection:
    enabled: true
    critical_patterns: ["401", "403", "ECONNREFUSED"]
    warning_patterns: ["429", "Rate limit"]
    error_patterns: ["ERROR:", "Exception"]

  # NEW: Progressive response
  progressive_termination:
    critical: 0  # Kill immediately
    warning: 30  # Kill after 30s if no recovery
    error: 60    # Kill after 60s if no recovery

proactive_health_checks:
  enabled: true
  check_interval: 5.0
  no_output_threshold: 120.0  # For LLM thinking
  terminate_on_failure: true  # Enable for critical only
```

## Integration with Existing Systems

### Circuit Breaker Integration
- Fast-fail detection feeds circuit breaker with failure velocity data
- Critical errors open circuit immediately (line 615-666 in `circuit_breaker.py`)
- Current: Opens after 2 failures in 300s window
- Proposed: Opens after 1 critical detection

### SOAR Orchestrator Integration
**Location**: `packages/soar/src/aurora_soar/orchestrator.py:769-800`

Current recovery metrics (line 468-484):
```python
"recovery_metrics": {
    "early_terminations": len(early_terminations),
    "early_termination_details": early_terminations,
    # ... existing metrics
}
```

Enhance with signal categorization:
```python
"recovery_metrics": {
    "early_detections": {
        "critical": [],  # API auth, connection failures
        "warning": [],   # Rate limits, timeouts
        "stall": []      # No output progress
    }
}
```

## Expected Improvements

### Detection Latency Reduction

| Scenario | Current | Proposed | Improvement |
|----------|---------|----------|-------------|
| API auth failure | 300s (timeout) | 2-5s | **98% faster** |
| Connection refused | 300s | 2-5s | **98% faster** |
| Rate limit | 300s | 5-30s | **90-98% faster** |
| Process stall | 30s | 15s | **50% faster** |

### Resource Savings

| Metric | Current | Proposed | Savings |
|--------|---------|----------|---------|
| Wasted CPU time | 300s/failure | 5s/failure | **98% reduction** |
| Circuit breaker triggers | 2 failures (600s) | 1 failure (5s) | **120x faster** |
| User feedback latency | 5 minutes | 5 seconds | **60x faster** |

## Implementation Priority

### High Priority (Week 1)
1. Add stderr pattern matching to Early Detection Monitor
2. Define critical/warning/error pattern catalogs
3. Enable immediate termination on critical patterns

### Medium Priority (Week 2)
4. Enable proactive health termination for critical failures
5. Add progressive timeout adjustment
6. Enhance recovery metrics with signal categorization

### Low Priority (Week 3)
7. Add memory limit enforcement
8. Add stdout error pattern detection
9. Add behavioral pattern detection (loops, cycling)

## Testing Strategy

### Unit Tests
**Location**: `tests/unit/spawner/test_early_failure_detection.py`

Test cases needed:
1. Critical pattern detection (API auth, connection)
2. Warning pattern detection (rate limits)
3. Stall detection (existing)
4. Progressive termination timing
5. Circuit breaker integration

### Integration Tests
**Location**: `tests/integration/soar/test_early_detection_e2e.py`

Test scenarios:
1. End-to-end detection with mock failing agents
2. Recovery metrics validation
3. Circuit breaker fast-fail verification

## Rollout Plan

### Phase 1: Observability (No Behavior Change)
- Add pattern detection without termination
- Log detected patterns for tuning
- Collect baseline metrics

### Phase 2: Soft Launch (Opt-In)
- Enable termination via config flag
- Test with non-critical workloads
- Monitor false positive rate

### Phase 3: Full Rollout
- Enable by default
- Add adaptive tuning
- Continuous monitoring

## Success Metrics

### Primary KPIs
1. **Detection Latency P50**: Target <10s (from 300s)
2. **Detection Latency P95**: Target <30s (from 300s)
3. **False Positive Rate**: Target <1%
4. **Resource Waste Reduction**: Target 90%+

### Secondary KPIs
1. Circuit breaker activation speed
2. User feedback latency
3. Recovery success rate
4. System throughput improvement

## Conclusion

The current Aurora SOAR early detection system has a **solid foundation** with two independent monitoring systems, but they only detect **stall conditions**. By adding **stderr pattern matching** and **progressive termination**, we can achieve:

- **60-98x faster** detection for API/connection failures
- **90-98% reduction** in wasted resources
- **Immediate feedback** to users on non-recoverable failures

The implementation is **low-risk** because:
1. Existing monitors provide infrastructure
2. Pattern matching is additive (no breaking changes)
3. Can be rolled out progressively with feature flags

**Recommendation**: Implement Phase 1 (pattern detection) immediately to start realizing detection latency improvements within days.
