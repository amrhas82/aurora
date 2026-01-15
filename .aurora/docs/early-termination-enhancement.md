# Early Agent Failure Detection in SOAR

## Problem
Previously, SOAR only detected agent failures after full execution or timeout. This meant:
- Waiting 60-300s to detect stuck agents
- Wasted resources on failing agents
- Delayed failure signals to circuit breaker

## Solution
Enhanced SOAR phases to detect and propagate early termination signals in real-time.

## Implementation

### 1. Spawner Layer (Already Existed)
The spawner already detects failures early via `spawner.py:212-229`:
- Error pattern matching (API errors, auth failures, rate limits)
- No-activity timeout (30-120s based on policy)
- Returns `SpawnResult.termination_reason` with details

### 2. Collect Phase Enhancement (`collect.py`)
**Added early termination tracking during agent execution:**

```python
# Track early termination if detected (line 315-325)
if hasattr(spawn_result, "termination_reason") and spawn_result.termination_reason:
    if "early_terminations" not in execution_metadata:
        execution_metadata["early_terminations"] = []
    execution_metadata["early_terminations"].append({
        "agent_id": agent.id,
        "reason": spawn_result.termination_reason,
        "detection_time": duration_ms,
    })
```

**Store termination reason in AgentOutput metadata (line 351, 369):**
- Success: Include `termination_reason` for diagnostics
- Failure: Propagate `termination_reason` for recovery analysis

### 3. Orchestrator Enhancement (`orchestrator.py`)
**Extract early terminations from collect phase (line 428-430):**
```python
early_terminations = phase5_dict.get("execution_metadata", {}).get("early_terminations", [])
```

**Enhanced recovery metrics (line 433-447):**
```python
phase5_dict["recovery_metrics"] = {
    "early_terminations": len(early_terminations),
    "early_termination_details": early_terminations,  # NEW
    # ... other metrics
}
```

**Enhanced failure analysis (line 1405-1419):**
```python
term_reason = metadata.get("termination_reason")
if term_reason:
    early_term_count += 1
    early_term_details.append({
        "agent_id": output.agent_id,
        "reason": term_reason,
        "detection_time": metadata.get("duration_ms", 0),
    })
    logger.debug(f"Agent {output.agent_id} early termination: {term_reason} (detected in {duration_ms}ms)")
```

**Enhanced logging (line 735-747):**
```python
early_term_details = [
    f"{d['agent_id']} ({d['reason']}, {d['detection_time']}ms)"
    for d in recovery_metrics.get("early_term_details", [])
]
if early_term_details:
    logger.info(f"Early termination details: {', '.join(early_term_details)}")
```

## Detection Timeline

### Before Enhancement
1. Agent spawned → 0s
2. Error occurs → ~5s
3. Wait for timeout → 60-300s
4. Collect phase detects failure → 65-305s
5. Circuit breaker updated → 70-310s

### After Enhancement
1. Agent spawned → 0s
2. Error occurs → ~5s
3. **Spawner detects error pattern → 5-10s** ✓
4. **Collect phase logs termination → 5-10s** ✓
5. **Orchestrator analyzes → 5-10s** ✓
6. **Circuit breaker updated → 10-15s** ✓

**Improvement: 50-295s faster failure detection**

## Error Patterns Detected Early

From `timeout_policy.py:216-229`:
- Rate limits: `rate.?limit`, `429`, `quota.?exceeded`
- Connection errors: `connection.?(refused|reset|error)`, `ECONNRESET`
- API errors: `API.?error`
- Auth failures: `authentication.?failed`, `invalid.?api.?key`, `unauthorized`, `forbidden`
- Model unavailable: `model.?not.?available`

## Metrics Available

### `phase5_collect` metadata:
```python
{
    "execution_metadata": {
        "early_terminations": [
            {
                "agent_id": "search-agent",
                "reason": "Error pattern detected: rate.?limit",
                "detection_time": 8234  # ms
            }
        ]
    }
}
```

### `recovery_metrics`:
```python
{
    "early_terminations": 2,
    "early_termination_details": [...],
    "circuit_failures": ["search-agent"],
    "timeout_failures": [],
    # ...
}
```

### Log output:
```
INFO: Agent execution completed with 2 failures. Early terminations: 2, Circuit breaker: 1
INFO: Early termination details: search-agent (Error pattern detected: rate.?limit, 8234ms)
INFO: Early termination system detected 2 problematic agents in real-time.
```

## Testing

### Verify early detection:
```bash
# Run SOAR with verbose logging
aur soar "complex query" --verbosity VERBOSE 2>&1 | grep -i "early termination"

# Check detection time in logs
grep "early termination" .aurora/logs/soar-*.log
```

### Trigger early termination:
```python
# Test with agent that hits rate limit
aur soar "query requiring rate-limited API" --agent @rate-limited-agent

# Verify detection time < 30s (vs 300s timeout)
```

## Configuration

Early termination uses spawner policies (see `timeout_policy.py`):

```python
# Default policy (60s initial, 300s max)
SpawnPolicy.default()

# Patient policy (120s initial, 600s max, 120s no-activity)
SpawnPolicy.patient()

# Fast fail (60s fixed, 15s no-activity)
SpawnPolicy.fast_fail()
```

Configure via task:
```python
spawn_task = SpawnTask(
    prompt="...",
    agent="my-agent",
    policy_name="fast_fail"  # Use fast_fail policy
)
```

## Benefits

1. **Faster failure detection**: 50-295s improvement
2. **Resource efficiency**: Stop stuck agents immediately
3. **Better UX**: Users see failures within seconds, not minutes
4. **Circuit breaker efficiency**: Block failing agents faster
5. **Detailed diagnostics**: Know exact failure reason and detection time
