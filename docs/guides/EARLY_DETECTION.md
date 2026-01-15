# Early Failure Detection in SOAR

## Overview

Early failure detection provides non-blocking health checks that detect problematic agents before full timeout, enabling faster recovery and better resource utilization.

## Architecture

### Components

1. **Early Detection Monitor** (`packages/spawner/src/aurora_spawner/early_detection.py`)
   - Non-blocking async health checks
   - Stall detection (no output progress)
   - Independent monitoring loop
   - Configurable thresholds

2. **SOAR Integration** (`packages/soar/src/aurora_soar/orchestrator.py`)
   - Automatic configuration during initialization
   - Config-driven thresholds
   - Metadata collection and reporting

3. **Spawner Integration** (`packages/spawner/src/aurora_spawner/spawner.py`)
   - Monitors stdout/stderr activity
   - Triggers early termination on detection
   - Updates execution metadata

### Detection Flow

```
Agent Execution Start
├─ Early Monitor: register_execution(task_id, agent_id)
├─ Start monitoring loop (check_interval: 2s)
│
During Execution
├─ Spawner: update_activity(task_id, stdout_size, stderr_size)
├─ Monitor: check_execution() every 2s
│   ├─ Check stall: time_since_activity > stall_threshold
│   ├─ Check output growth
│   └─ Trigger termination if consecutive_stalls >= 2
│
Early Termination Detected
├─ Monitor: trigger_termination(reason)
├─ Spawner: should_terminate() returns (True, reason)
├─ Process: killed with termination_reason
├─ Collect: extract early_terminations metadata
└─ Orchestrator: report in recovery_metrics
```

## Configuration

### SOAR Configuration

Add to `.aurora/config.yaml`:

```yaml
early_detection:
  enabled: true
  check_interval: 2.0        # Health check interval (seconds)
  stall_threshold: 15.0      # No output threshold (seconds)
  min_output_bytes: 100      # Min output before stall check
  stderr_pattern_check: true # Enable stderr pattern matching
  memory_limit_mb: null      # Optional memory limit
```

### Default Values

- `enabled`: `true`
- `check_interval`: `2.0s` (check every 2 seconds)
- `stall_threshold`: `15.0s` (terminate after 15s no output)
- `min_output_bytes`: `100` (require 100 bytes before stall check)

## Detection Mechanisms

### 1. Stall Detection

Detects agents that stop producing output:

- Monitors stdout/stderr size changes
- Only checks after `min_output_bytes` produced
- Requires 2 consecutive stall detections (`stall_threshold` apart)
- Terminates with reason: `"Stalled: no output for Xs (2 checks)"`

**Example Timeline:**
```
0s   - Agent starts, produces 150 bytes
5s   - Last output received
15s  - First stall detection (15s since last output)
17s  - Health check: still stalled, consecutive_stalls = 1
30s  - Second stall detection (consecutive_stalls = 2)
30s  - TERMINATE: "Stalled: no output for 25.0s (2 checks)"
```

### 2. Consecutive Stall Threshold

Prevents false positives from brief pauses:

- First stall: log warning, increment counter
- Second stall: trigger termination
- Any output: reset counter to 0

## Graceful Degradation

### Recovery Strategies

1. **Retry with Backoff**
   - Early termination treated as retriable failure
   - Exponential backoff between attempts
   - Max retries: configurable (default: 2)

2. **Circuit Breaker**
   - Tracks early termination patterns
   - Opens circuit after threshold failures
   - Skips known-stalled agents immediately

3. **Fallback to LLM**
   - Used when agent consistently stalls
   - Direct LLM call without agent wrapper
   - Tracked in `fallback_agents` metadata

### Metadata Collection

Early terminations are tracked in execution metadata:

```python
{
  "early_terminations": [
    {
      "agent_id": "code-analyzer",
      "reason": "Stalled: no output for 20.5s (2 checks)",
      "detection_time": 22400  # ms from start
    }
  ]
}
```

## Integration with Existing Systems

### Proactive Health Checks

Works alongside proactive health monitoring:

- Early detection: non-blocking stall detection
- Proactive health: periodic status checks
- Both report through same metadata pipeline

### Circuit Breaker

Early terminations contribute to circuit breaker state:

- Each early termination counts as failure
- Opens circuit after threshold (default: 3)
- Prevents future attempts until reset

### Timeout Policies

Early detection complements timeout policies:

- Timeout policy: maximum execution time
- Early detection: activity-based termination
- Whichever triggers first wins

## Monitoring and Observability

### Logs

```
INFO  - Early detection enabled: check_interval=2.0s, stall_threshold=15.0s, min_output=100b
DEBUG - Health check: task_id=..., elapsed=10.0s, time_since_activity=5.0s, output_grew=True
WARN  - Stall detected: task_id=..., time_since_activity=15.2s, consecutive_stalls=1
ERROR - Early termination triggered: task_id=..., reason=Stalled: no output for 20.5s (2 checks)
```

### Recovery Metrics

SOAR orchestrator reports recovery metrics:

```python
recovery_metrics = {
  "early_terminations": 2,
  "early_termination_details": [
    {"agent_id": "...", "reason": "...", "detection_time": 22400}
  ],
  "circuit_breaker_blocks": 1,
  "timeout_count": 0,
  "fallback_used_count": 2
}
```

## Performance Impact

### Overhead

- Monitoring loop: async, runs every 2s
- Activity updates: O(1) dict lookups
- Termination checks: O(1) flag checks

### Detection Latency

- Best case: `check_interval` (2s)
- Typical: `check_interval + stall_threshold` (17s for first detection)
- With consecutive threshold: `2 * stall_threshold + check_interval` (32s)

### Improvement Over Timeout

Traditional timeout: 300s (5 minutes)
Early detection: ~30s for stalled agents
**Speedup: 10x faster failure detection**

## Troubleshooting

### False Positives

**Symptom:** Agents terminated despite working correctly

**Solutions:**
- Increase `stall_threshold` (e.g., 30s)
- Increase `min_output_bytes` (e.g., 500)
- Check agent output patterns (bursty vs. continuous)

### False Negatives

**Symptom:** Stalled agents not detected

**Solutions:**
- Decrease `stall_threshold` (e.g., 10s)
- Enable debug logging to verify activity updates
- Check if agent produces any output (needs > min_output_bytes)

### Disable for Debugging

```yaml
early_detection:
  enabled: false
```

Or via environment:
```bash
export AURORA_EARLY_DETECTION_ENABLED=false
```

## Best Practices

1. **Tune for workload**: Adjust thresholds based on typical agent behavior
2. **Monitor metrics**: Track false positive/negative rates
3. **Combine strategies**: Use early detection + circuit breaker + fallback
4. **Test recovery**: Verify graceful degradation under failures
5. **Log analysis**: Review early termination patterns for optimization

## Future Enhancements

- Memory-based detection (resource usage monitoring)
- Pattern-based detection (stderr error patterns)
- Adaptive thresholds (learn from agent history)
- Per-agent threshold configuration
- Detection reason classification (stall vs. crash vs. hung)
