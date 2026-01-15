# Early Termination System

The Aurora spawner includes a comprehensive early termination system with configurable timeout thresholds, retry policies, and circuit breakers.

## Architecture

### 1. Timeout Policies

Three timeout modes available:

**FIXED**: Single static timeout
```python
TimeoutPolicy(
    mode=TimeoutMode.FIXED,
    timeout=300.0  # 5 minutes
)
```

**PROGRESSIVE**: Starts short, extends on activity
```python
TimeoutPolicy(
    mode=TimeoutMode.PROGRESSIVE,
    initial_timeout=60.0,      # Start with 1 minute
    max_timeout=300.0,         # Cap at 5 minutes
    extension_threshold=10.0,  # Extend if activity < 10s ago
    no_activity_timeout=30.0   # Kill if idle for 30s
)
```

**ADAPTIVE**: Learns from execution history
```python
TimeoutPolicy(
    mode=TimeoutMode.ADAPTIVE,
    history_window=10,    # Track last 10 executions
    percentile=0.90,      # Use 90th percentile
    min_samples=3         # Need 3 samples before adapting
)
```

### 2. Retry Policies

Four retry strategies with configurable backoff:

**IMMEDIATE**: No delay between retries
```python
RetryPolicy(
    max_attempts=3,
    strategy=RetryStrategy.IMMEDIATE
)
```

**FIXED_DELAY**: Constant delay between retries
```python
RetryPolicy(
    max_attempts=3,
    strategy=RetryStrategy.FIXED_DELAY,
    base_delay=2.0  # 2 seconds between retries
)
```

**EXPONENTIAL_BACKOFF**: Exponential increase with jitter
```python
RetryPolicy(
    max_attempts=3,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    base_delay=1.0,       # Start with 1 second
    max_delay=60.0,       # Cap at 60 seconds
    backoff_factor=2.0,   # Double each time
    jitter=True,          # Add ±10% randomness
    jitter_factor=0.1
)
```

**LINEAR_BACKOFF**: Linear increase in delay
```python
RetryPolicy(
    max_attempts=3,
    strategy=RetryStrategy.LINEAR_BACKOFF,
    base_delay=1.0,       # Start with 1 second
    backoff_factor=1.0    # Add 1 second each retry
)
```

### 3. Termination Policies

Controls early process termination:

```python
TerminationPolicy(
    enabled=True,
    kill_on_error_patterns=True,     # Terminate on stderr patterns
    kill_on_no_activity=True,        # Terminate on idle timeout
    error_patterns=[                 # Patterns that trigger termination
        r"rate.?limit",
        r"\b429\b",
        r"API.?error",
        r"authentication.?failed",
        r"quota.?exceeded"
    ],
    custom_predicates=[              # Custom termination logic
        lambda stdout, stderr: "ABORT" in stdout
    ]
)
```

## Policy Presets

Five built-in presets for common scenarios:

### Default (Balanced)
```python
policy = SpawnPolicy.default()
# Progressive: 60s → 300s
# Retries: 3 attempts with exponential backoff
# Termination: Enabled with error patterns + no-activity
```

### Production (Patient)
```python
policy = SpawnPolicy.production()
# Progressive: 120s → 600s (10 minutes)
# Retries: 3 attempts with 2s base delay
# Termination: Error patterns only (patient on idle)
```

### Fast Fail (Aggressive)
```python
policy = SpawnPolicy.fast_fail()
# Fixed: 60s timeout
# Retries: 1 attempt only (no retries)
# Termination: Aggressive on all conditions
```

### Development (Debugging)
```python
policy = SpawnPolicy.development()
# Fixed: 1800s (30 minutes)
# Retries: 1 attempt (no retries)
# Termination: Disabled (observe failures)
```

### Test (Fast Feedback)
```python
policy = SpawnPolicy.test()
# Fixed: 30s timeout
# Retries: 1 attempt only
# Termination: Enabled for fast feedback
```

## Usage

### Basic Usage with Preset
```python
from aurora_spawner.spawner import spawn_with_retry_and_fallback
from aurora_spawner.models import SpawnTask
from aurora_spawner.timeout_policy import SpawnPolicy

task = SpawnTask(
    prompt="Analyze this codebase",
    agent="code-analyzer",
    policy_name="production"  # Use production preset
)

result = await spawn_with_retry_and_fallback(task)
```

### Custom Policy
```python
policy = SpawnPolicy(
    name="custom",
    timeout_policy=TimeoutPolicy(
        mode=TimeoutMode.PROGRESSIVE,
        initial_timeout=30.0,
        max_timeout=120.0
    ),
    retry_policy=RetryPolicy(
        max_attempts=5,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        retry_on_timeout=False  # Don't retry timeouts
    ),
    termination_policy=TerminationPolicy(
        enabled=True,
        custom_predicates=[
            lambda stdout, stderr: "CRITICAL_ERROR" in stderr
        ]
    )
)

result = await spawn_with_retry_and_fallback(task, policy=policy)
```

### Override Retries at Call Site
```python
# Policy says 5 retries, but override to 2 for this call
result = await spawn_with_retry_and_fallback(
    task,
    max_retries=2,
    policy=policy
)
```

## Integration with Circuit Breaker

The retry policy integrates with circuit breaker for fast failure:

```python
RetryPolicy(
    max_attempts=3,
    circuit_breaker_enabled=True  # Skip known-failing agents
)
```

When an agent consistently fails:
1. Circuit opens after N failures (default: 2)
2. Subsequent calls skip the agent immediately
3. After timeout (default: 120s), circuit enters half-open
4. One test request allowed
5. Success closes circuit, failure reopens

## Execution Flow

```
spawn_with_retry_and_fallback()
    │
    ├─► Check circuit breaker
    │   └─► Skip if open, go to fallback
    │
    ├─► Attempt 1 (initial)
    │   ├─► spawn() with timeout policy
    │   │   ├─► Monitor for error patterns
    │   │   ├─► Check activity timeout
    │   │   ├─► Extend timeout if progressive
    │   │   └─► Terminate early if conditions met
    │   │
    │   └─► Success? Return
    │
    ├─► Retry decision (based on error type)
    │   ├─► Check should_retry()
    │   ├─► Calculate backoff delay
    │   └─► Check circuit breaker again
    │
    ├─► Attempt 2..N (retries)
    │   └─► Same as Attempt 1
    │
    └─► Fallback to LLM (if enabled)
        └─► spawn() with agent=None
```

## Monitoring

The spawner emits heartbeat events for real-time monitoring:

- `STARTED`: Process spawned
- `STDOUT`: Output received (activity detected)
- `STDERR`: Error output received (activity detected)
- `TIMEOUT_WARNING`: Approaching timeout threshold
- `KILLED`: Process terminated early
- `COMPLETED`: Process completed successfully
- `FAILED`: Process failed

## Best Practices

1. **Use presets for common scenarios**: They're well-tested and balanced
2. **Production environments**: Use `production` or `default` preset
3. **Development/debugging**: Use `development` preset for long timeouts
4. **CI/CD pipelines**: Use `fast_fail` or `test` preset for quick feedback
5. **Custom predicates**: Add specific termination logic for your use case
6. **Disable retries for deterministic failures**: If an error won't resolve with retries
7. **Enable circuit breaker in production**: Prevents wasting time on broken agents

## Performance Characteristics

- **Memory**: O(1) - bounded event buffers
- **CPU**: Minimal - checks every 0.5s by default
- **Latency**:
  - Error pattern detection: < 1s
  - Activity timeout: Configurable (default 30s)
  - Circuit breaker: Immediate skip when open

## Configuration Resolution

Priority order for timeout/retry settings:

1. Explicit `policy` parameter
2. Task's `policy_name` field
3. Default policy

Priority for max_retries:

1. Explicit `max_retries` parameter
2. Policy's `retry_policy.max_attempts`
