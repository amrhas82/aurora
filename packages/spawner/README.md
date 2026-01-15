# Aurora Spawner

Subprocess spawner for Aurora framework with agent recovery and circuit breaker protection.

## Installation

```bash
pip install aurora-spawner
```

## Quick Start

```python
from aurora_spawner import spawn, SpawnTask

task = SpawnTask(prompt="Hello world")
result = await spawn(task)
print(result.output)
```

## Parallel Execution with Recovery

For production workloads, use `spawn_parallel_with_recovery` for automatic retry and fallback:

```python
from aurora_spawner import spawn_parallel_with_recovery, SpawnTask

tasks = [
    SpawnTask(prompt="Implement feature A", agent="coder"),
    SpawnTask(prompt="Write tests for feature A", agent="tester"),
    SpawnTask(prompt="Document feature A", agent="writer"),
]

results = await spawn_parallel_with_recovery(
    tasks=tasks,
    max_retries=2,
    fallback_to_llm=True,
)

for result in results:
    print(f"Task {result.task_index}: {'OK' if result.success else 'FAILED'}")
    if result.retry_count > 0:
        print(f"  Recovered after {result.retry_count} retries")
    if result.fallback:
        print(f"  Used LLM fallback (original agent: {result.original_agent})")
```

## Recovery Policies

Use preset policies for common scenarios:

```python
from aurora_spawner import spawn_parallel_with_recovery
from aurora_spawner.recovery import RecoveryPolicy

# Default: 2 retries with exponential backoff, then LLM fallback
policy = RecoveryPolicy.default()

# Aggressive: 5 retries, no fallback (agent must succeed)
policy = RecoveryPolicy.aggressive_retry()

# Fast: skip retries, immediate LLM fallback
policy = RecoveryPolicy.fast_fallback()

# Patient: 3 retries with longer delays (for complex tasks)
policy = RecoveryPolicy.patient()

results = await spawn_parallel_with_recovery(
    tasks=tasks,
    recovery_policy=policy,
)
```

### Per-Agent Overrides

Customize recovery behavior for specific agents:

```python
policy = RecoveryPolicy.default().with_override(
    "slow-agent",
    max_retries=5,
    base_delay=2.0,
)
```

### Load from Config

```python
policy = RecoveryPolicy.from_config({
    "spawner": {
        "recovery": {
            "preset": "patient",
            "max_retries": 4,
        }
    }
})
```

## Error Classification

Recovery decisions are based on automatic error classification:

| Category | Examples | Behavior |
|----------|----------|----------|
| `transient` | Rate limit, 429, connection reset | Retry |
| `timeout` | Timed out, deadline exceeded | Retry |
| `resource` | Quota exceeded, out of memory | Retry |
| `permanent` | Auth failed, 401, invalid API key | Fail |
| `unknown` | Unclassified | Default behavior |

## Circuit Breaker

Prevents repeated attempts to failing agents:

```python
from aurora_spawner.circuit_breaker import CircuitBreaker

breaker = CircuitBreaker(
    failure_threshold=2,   # failures to open
    reset_timeout=120,     # seconds before testing
    failure_window=300,    # time window for counting
)
```

States:
- **Closed**: Normal operation
- **Open**: Rejecting requests (agent failing)
- **Half-Open**: Testing recovery (one request allowed)

## Recovery Metrics

Track recovery statistics:

```python
from aurora_spawner.recovery import get_recovery_metrics

metrics = get_recovery_metrics()
print(f"Success rate: {metrics.success_rate():.1f}%")
print(f"Recovery rate: {metrics.recovery_rate():.1f}%")
```

## API Reference

### Functions

- `spawn(task)` - Execute single task
- `spawn_parallel(tasks, max_concurrent)` - Execute tasks in parallel
- `spawn_parallel_with_recovery(tasks, ...)` - Parallel execution with recovery

### Classes

- `SpawnTask` - Task definition (prompt, agent, context)
- `SpawnResult` - Execution result with recovery metadata
- `RecoveryPolicy` - Recovery configuration
- `CircuitBreaker` - Circuit breaker for failing agents

## Documentation

- [Command Reference](../../docs/commands/aur-spawn.md) - CLI usage and examples
- [Config Reference](../../docs/reference/CONFIG_REFERENCE.md) - Configuration options
