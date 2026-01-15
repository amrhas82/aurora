# Parallel Spawning Edge Cases and Failure Scenarios Test Suite

Comprehensive test suite for parallel agent spawning with focus on adhoc agents, concurrent failures, circuit breaker behavior, and recovery mechanisms.

## Overview

These tests validate robust parallel execution of agents, particularly addressing common failure modes in adhoc (dynamically generated) agent spawning. Tests cover concurrency control, failure handling, circuit breaker integration, and resource contention.

## Test Files

### 1. Integration Tests - Parallel Spawn Edge Cases (`tests/integration/soar/test_parallel_spawn_edge_cases.py`)

End-to-end scenarios testing parallel execution in the SOAR collect phase.

**Test Classes:**

#### TestParallelSpawnConcurrency (3 tests)
Tests concurrent execution and race conditions:
- `test_concurrent_adhoc_agent_spawns` - Multiple adhoc agents spawn in parallel without interference
- `test_mixed_adhoc_and_registered_agents` - Adhoc and registered agents execute correctly together
- `test_concurrent_circuit_breaker_updates` - Circuit breaker state updates correctly under concurrent failures

**Key validations:**
- Adhoc agents tracked in `spawned_agents` metadata
- `spawn_count` accurately reflects adhoc spawns
- Circuit breaker state remains consistent across parallel updates

#### TestAdhocAgentFailures (3 tests)
Tests failure scenarios specific to adhoc agents:
- `test_adhoc_agent_inference_failures` - Lenient circuit breaker treatment for inference failures
- `test_adhoc_agent_fast_fail_threshold` - Longer fast-fail window (30s vs 10s) for adhoc agents
- `test_adhoc_agent_missing_matcher` - Fallback spawn prompt when AgentMatcher unavailable

**Key validations:**
- Adhoc threshold = 4 failures (vs 2 for regular agents)
- Inference failures don't trigger fast-fail for adhoc agents
- Fallback prompt contains "act as a" when matcher missing

#### TestCircuitBreakerEdgeCases (3 tests)
Tests circuit breaker behavior in edge cases:
- `test_circuit_breaker_pre_spawn_blocking` - Circuit blocks agents before spawning (fast-fail)
- `test_circuit_breaker_with_fallback` - Circuit triggers fallback to LLM
- `test_circuit_recovery_in_parallel` - Circuit recovers when agent succeeds in parallel

**Key validations:**
- `circuit_blocked_count` tracks pre-spawn blocks
- Fallback agents tracked in `fallback_agents` list
- Circuit closes on successful recovery

#### TestResourceContention (2 tests)
Tests resource limits and contention:
- `test_max_concurrent_limit_respected` - Parallel spawning respects max_concurrent limit
- `test_global_timeout_with_slow_agents` - Global timeout prevents pipeline hanging

**Key validations:**
- Max concurrent never exceeded during execution
- Global timeout = agent_timeout * 1.5
- Partial results returned on global timeout

#### TestFailurePatternDetection (2 tests)
Tests failure categorization:
- `test_error_pattern_early_termination` - Error patterns trigger early termination tracking
- `test_mixed_failure_types` - Different failure types tracked separately

**Key validations:**
- `early_terminations` metadata includes reason and detection time
- Rate limit, auth, timeout failures categorized correctly

#### TestRecoveryMechanisms (2 tests)
Tests retry and recovery:
- `test_retry_with_exponential_backoff` - Retries use exponential backoff
- `test_partial_success_handling` - Partial successes handled correctly

**Key validations:**
- Retry delays increase exponentially
- `failed_subgoals` count accurate with partial failures

#### TestEdgeCasesAndBoundaries (5 tests)
Tests boundary conditions:
- `test_empty_agent_list` - Empty list handled gracefully
- `test_single_agent_execution` - Single agent works correctly
- `test_very_high_concurrency` - 100+ agents handled correctly
- `test_exception_during_spawn` - Exceptions caught and converted to failures
- Tests complete in reasonable time with high concurrency

**Total Integration Tests:** 20 async tests

---

### 2. Unit Tests - spawn_parallel Edge Cases (`tests/unit/spawner/test_spawn_parallel_edge_cases.py`)

Direct tests of `spawn_parallel()` function behavior.

**Test Classes:**

#### TestConcurrencyControl (4 tests)
Tests semaphore and concurrency limiting:
- `test_max_concurrent_enforced` - Max concurrent limit strictly enforced
- `test_single_concurrent_slot` - Works with max_concurrent=1 (serial)
- `test_zero_max_concurrent_raises` - max_concurrent=0 raises ValueError
- `test_unlimited_concurrency` - High max_concurrent allows full parallelism

**Key validations:**
- Active task count never exceeds max_concurrent
- Serial execution (max=1) maintains order
- Semaphore prevents over-subscription

#### TestResultOrdering (2 tests)
Tests result order preservation:
- `test_results_match_input_order` - Results match input order despite random completion
- `test_mixed_success_failure_order` - Mixed success/failure maintains order

**Key validations:**
- Output order matches input order regardless of completion timing
- Failed results preserve position in output list

#### TestExceptionHandling (3 tests)
Tests exception handling:
- `test_exception_converts_to_failed_result` - Exceptions convert to failed SpawnResult
- `test_multiple_exceptions_handled` - Multiple exceptions don't abort
- `test_asyncio_cancellation` - CancelledError propagates correctly

**Key validations:**
- RuntimeError/ValueError caught and returned as failed results
- Exception message preserved in result.error
- CancelledError not caught (propagates for proper cancellation)

#### TestProgressCallback (2 tests)
Tests on_progress callback:
- `test_progress_callback_called` - Callback invoked for each task
- `test_progress_callback_exception_ignored` - Callback exceptions don't abort

**Key validations:**
- Start and complete events for each task
- Total count correct in all callbacks
- Execution continues if callback raises

#### TestEmptyAndEdgeCases (4 tests)
Tests edge cases:
- `test_empty_task_list` - Empty input returns empty output
- `test_single_task` - Single task handled correctly
- `test_all_tasks_fail` - All failures handled gracefully
- `test_very_large_task_list` - 1000+ tasks handled efficiently

**Key validations:**
- Empty list returns `[]` (not None or error)
- Single task doesn't require special handling
- Performance scales with large task counts

#### TestKwargsPassthrough (2 tests)
Tests parameter passing:
- `test_tool_and_model_passed` - Tool and model kwargs passed to spawn
- `test_config_passed` - Config dict passed to spawn

**Key validations:**
- All kwargs forwarded to spawn() calls
- No parameter mutation or loss

#### TestTimingAndPerformance (2 tests)
Tests performance characteristics:
- `test_parallel_faster_than_serial` - Parallel significantly faster than serial
- `test_respects_task_execution_time` - Varying durations handled correctly

**Key validations:**
- Parallel execution < 50% of serial time
- All tasks complete regardless of duration variance

**Total Unit Tests:** 19 async tests

---

## Total Test Coverage

- **Integration Tests:** 20 async tests
- **Unit Tests:** 19 async tests
- **Total:** 39 comprehensive async tests

---

## Key Features Tested

### 1. Adhoc Agent Spawning

**Adhoc agents** are dynamically generated agents that don't exist in the registry. They're identified by:
- `config["is_spawn"] = True` flag
- Naming patterns: "adhoc", "ad-hoc", "generated", "dynamic"
- Explicit marking via `CircuitBreaker.mark_as_adhoc()`

**Special handling:**
- Spawn prompt generated via AgentMatcher or fallback template
- `agent=None` passed to spawn (direct LLM call without persona)
- Higher circuit breaker threshold (4 vs 2 failures)
- Longer fast-fail window (30s vs 10s)
- Inference failures don't trigger fast-fail

**Metadata tracking:**
```python
{
    "spawned_agents": ["adhoc-agent-1", "adhoc-agent-2"],
    "spawn_count": 2,
}
```

### 2. Concurrency Control

**Max Concurrent Limiting:**
- Semaphore enforces strict limit
- Tasks queue when limit reached
- Default: 5 concurrent tasks
- No over-subscription of resources

**Benefits:**
- Prevents resource exhaustion
- Controls API rate limit exposure
- Maintains system stability

### 3. Circuit Breaker Integration

**Pre-spawn Blocking:**
- Circuit checked BEFORE spawning task
- Fast-fail if circuit open (no spawn overhead)
- Blocks tracked in `circuit_blocked` metadata

**Thresholds:**
- Regular agents: 2 failures → open
- Adhoc agents: 4 failures → open
- Fast-fail: 2 failures within 10s (30s for adhoc)
- Reset timeout: 120s

**Failure Type Tracking:**
```python
failure_types = ["timeout", "error_pattern", "inference", "crash"]
```

**Health Status:**
```python
{
    "state": "open" | "closed" | "half_open",
    "recent_failures": 3,
    "failure_velocity": 2.5,  # failures per minute
    "risk_level": "critical" | "high" | "medium" | "low",
}
```

### 4. Failure Categorization

**Early Termination Metadata:**
```python
{
    "early_terminations": [
        {
            "agent_id": "rate-limited-agent",
            "reason": "Early detection: rate limit pattern detected",
            "detection_time": 1250,  # milliseconds
        }
    ]
}
```

**Execution Metadata:**
```python
{
    "total_subgoals": 10,
    "failed_subgoals": 3,
    "fallback_count": 2,
    "spawn_count": 5,
    "circuit_blocked_count": 1,
    "circuit_blocked": [
        {
            "agent_id": "broken-agent",
            "subgoal_index": 7,
            "reason": "Circuit open: 3 failures, retry in 90s",
            "health_status": {...},
        }
    ],
}
```

### 5. Result Ordering

**Guarantees:**
- Results always match input task order
- Order preserved regardless of:
  - Completion timing variance
  - Success/failure mix
  - Exception occurrence
  - Concurrent execution

**Implementation:**
- `asyncio.gather(*coros)` preserves order
- Index-based result collection
- No sorting or reordering needed

### 6. Exception Handling

**Conversion to SpawnResult:**
```python
SpawnResult(
    success=False,
    output="",
    error=str(exception),
    exit_code=-1,
)
```

**Exceptions converted:**
- `RuntimeError`
- `ValueError`
- `TypeError`
- Any non-CancelledError exception

**Exceptions propagated:**
- `asyncio.CancelledError` - proper task cancellation

### 7. Global Timeout Protection

**Purpose:** Prevent entire pipeline hanging on stuck agents

**Formula:** `global_timeout = agent_timeout * 1.5`

**Example:**
- Agent timeout: 300s (5 min)
- Global timeout: 450s (7.5 min)
- Prevents 10 agents from taking 50 minutes (10 * 5 min)

**Behavior:**
- Returns partial results on timeout
- Logs warning about partial completion
- Does not raise exception

### 8. Progress Tracking

**Callback Signature:**
```python
def on_progress(idx: int, total: int, agent_id: str, status: str):
    pass
```

**Events:**
- `Starting` - Task begins execution
- `Completed (Xs)` - Task finishes successfully
- Various status messages during execution

**Use cases:**
- Real-time UI updates
- Progress bars
- Logging and monitoring

---

## Running the Tests

### All parallel spawn edge case tests:
```bash
pytest tests/integration/soar/test_parallel_spawn_edge_cases.py \
       tests/unit/spawner/test_spawn_parallel_edge_cases.py -v
```

### Integration tests only:
```bash
pytest tests/integration/soar/test_parallel_spawn_edge_cases.py -v
```

### Unit tests only:
```bash
pytest tests/unit/spawner/test_spawn_parallel_edge_cases.py -v
```

### Specific test class:
```bash
pytest tests/integration/soar/test_parallel_spawn_edge_cases.py::TestAdhocAgentFailures -v
```

### With coverage:
```bash
pytest tests/integration/soar/test_parallel_spawn_edge_cases.py \
       tests/unit/spawner/test_spawn_parallel_edge_cases.py \
       --cov=aurora_soar.phases.collect \
       --cov=aurora_spawner.spawner \
       --cov=aurora_spawner.circuit_breaker
```

### Run with specific markers:
```bash
# Run only asyncio tests
pytest -m asyncio tests/integration/soar/test_parallel_spawn_edge_cases.py

# Run with verbose output and timing
pytest -v --durations=10 tests/integration/soar/test_parallel_spawn_edge_cases.py
```

---

## Performance Characteristics

### Concurrency Benefits

**Serial execution (max_concurrent=1):**
- 10 tasks × 100ms = 1000ms total

**Parallel execution (max_concurrent=5):**
- 2 batches × 100ms = 200ms total
- **5x faster** than serial

**Parallel execution (max_concurrent=10):**
- 1 batch × 100ms = 100ms total
- **10x faster** than serial

### Circuit Breaker Benefits

**Without circuit breaker:**
- Broken agent retries 3 times × 60s timeout = 180s wasted per task
- 10 tasks with broken agent = 1800s (30 minutes) wasted

**With circuit breaker:**
- First 2 failures: 2 × 60s = 120s
- Remaining 8 tasks: pre-spawn block = 0s
- Total: 120s (2 minutes) with fast-fail
- **15x faster** failure detection

### Adhoc Agent Considerations

**Why higher thresholds for adhoc agents?**
- Generated on-the-fly, less tested
- May have transient inference issues
- Need more retry opportunities
- Inference failures are recoverable

**Trade-offs:**
- Longer time to circuit open (4 failures vs 2)
- Better success rate for adhoc agents
- Risk of more wasted time on truly broken agents

---

## Implementation References

**Integration test file:**
- `tests/integration/soar/test_parallel_spawn_edge_cases.py`
- Tests SOAR collect phase with `execute_agents()`
- Mocks spawn functions for controlled testing

**Unit test file:**
- `tests/unit/spawner/test_spawn_parallel_edge_cases.py`
- Tests `spawn_parallel()` directly
- Isolated from SOAR orchestration

**Source implementations:**
- Collect phase: `packages/soar/src/aurora_soar/phases/collect.py`
  - `execute_agents()` at line 185
  - Adhoc agent detection at line 298
  - Circuit pre-spawn check at line 252
  - Global timeout at line 490
- Spawner: `packages/spawner/src/aurora_spawner/spawner.py`
  - `spawn_parallel()` at line 471
  - `spawn_with_retry_and_fallback()` at line 576
- Circuit breaker: `packages/spawner/src/aurora_spawner/circuit_breaker.py`
  - Adhoc detection at line 104
  - Failure recording at line 134
  - Health status at line 324

---

## Test Patterns and Best Practices

### Mocking Spawn Functions

```python
async def mock_spawn(task, **kwargs):
    await asyncio.sleep(0.05)  # Simulate work
    return SpawnResult(
        success=True,
        output="Result",
        error=None,
        exit_code=0,
    )

with patch("aurora_soar.phases.collect.spawn", side_effect=mock_spawn):
    result = await execute_agents(...)
```

### Tracking Concurrency

```python
active_count = 0
max_observed = 0
lock = asyncio.Lock()

async def mock_spawn(task, **kwargs):
    async with lock:
        active_count += 1
        max_observed = max(max_observed, active_count)

    await asyncio.sleep(0.1)

    async with lock:
        active_count -= 1

    return SpawnResult(...)

# After execution, assert max_observed <= max_concurrent
```

### Fixture for Circuit Breaker Reset

```python
@pytest.fixture
def reset_circuit_breaker():
    """Reset circuit breaker state before each test."""
    cb = get_circuit_breaker()
    cb.reset_all()
    yield cb
    cb.reset_all()
```

### Testing Failure Patterns

```python
async def mock_spawn_selective_failure(task):
    if "timeout" in task.prompt:
        return SpawnResult(success=False, error="Timeout", ...)
    elif "auth" in task.prompt:
        return SpawnResult(success=False, error="Auth failed", ...)
    else:
        return SpawnResult(success=True, ...)
```

---

## Known Issues and Limitations

### Test Timing Sensitivity

Some tests use `asyncio.sleep()` for timing control. These may be flaky on slow CI systems:
- Use generous timing margins (e.g., `< 2.0s` instead of `< 0.5s`)
- Consider using `pytest-timeout` for hard limits
- Mock timing-sensitive code when possible

### Circuit Breaker State

Circuit breaker is a global singleton. Must reset between tests:
```python
@pytest.fixture(autouse=True)
def reset_circuit():
    get_circuit_breaker().reset_all()
```

### Parallel Test Execution

Tests with global state (circuit breaker, early detection monitor) may conflict if run in parallel:
- Use `pytest-xdist` with caution
- Mark tests that need isolation
- Consider separate test files for isolated features

---

## Future Enhancements

### Additional Test Scenarios

1. **Network partition simulation**
   - Test behavior when agents lose connectivity
   - Validate timeout and retry behavior

2. **Resource exhaustion**
   - Test with memory/CPU limits
   - Validate graceful degradation

3. **Cascading failures**
   - Test when multiple agents fail simultaneously
   - Validate circuit breaker prevents cascade

4. **Load testing**
   - 1000+ concurrent agents
   - Measure throughput and latency

5. **Chaos engineering**
   - Random failures, delays, timeouts
   - Validate system resilience

### Test Infrastructure

1. **Property-based testing**
   - Use `hypothesis` for random test generation
   - Find edge cases automatically

2. **Performance benchmarks**
   - Track execution time over commits
   - Detect performance regressions

3. **Integration with real agents**
   - Test against actual agent implementations
   - Validate assumptions about agent behavior

---

## Troubleshooting

### Tests hanging indefinitely

**Cause:** Missing timeout or infinite loop

**Solution:**
```python
@pytest.mark.asyncio
@pytest.mark.timeout(30)  # Hard timeout
async def test_something():
    ...
```

### Flaky test failures

**Cause:** Timing assumptions or race conditions

**Solution:**
- Increase sleep durations
- Use explicit synchronization
- Mock time-dependent code

### Circuit breaker state contamination

**Cause:** Shared state between tests

**Solution:**
```python
@pytest.fixture(autouse=True)
def reset_all_state():
    get_circuit_breaker().reset_all()
    reset_early_detection_monitor()
```

### Mock not being called

**Cause:** Wrong patch target

**Solution:**
- Patch where imported, not where defined
- Use `side_effect` instead of `return_value` for async

---

## Conclusion

This comprehensive test suite validates robust parallel agent spawning with focus on:
- **Adhoc agent handling** - Dynamic agent generation and execution
- **Failure resilience** - Circuit breakers, retries, fallbacks
- **Concurrency control** - Resource limits and contention management
- **Performance** - Efficient parallel execution at scale

Tests provide confidence that the system handles edge cases gracefully and fails fast when appropriate.
