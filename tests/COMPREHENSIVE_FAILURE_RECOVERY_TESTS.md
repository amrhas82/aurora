# Comprehensive Failure Recovery Test Suite

This document outlines additional test scenarios needed to complement the existing early failure detection tests. Focus areas: recovery paths, edge cases, race conditions, and resource exhaustion scenarios.

## Gap Analysis

### Existing Coverage (69 tests)
- Early termination patterns (rate limit, auth, connection)
- Progressive timeout behavior
- Basic circuit breaker integration
- Failure categorization
- Metadata tracking

### Missing Coverage Areas
1. **Non-blocking early detection monitor lifecycle**
2. **Recovery from partial failures**
3. **Concurrent failure scenarios**
4. **Resource exhaustion edge cases**
5. **Health monitor state transitions**
6. **Circuit breaker state recovery**
7. **Stall detection with minimal output**

---

## 1. Early Detection Monitor Tests

### File: `tests/unit/spawner/test_early_detection_monitor.py`

**TestEarlyDetectionMonitor** (10 tests)

```python
def test_monitor_starts_and_stops_cleanly():
    """Monitor starts background task and stops without errors."""

def test_register_execution_creates_state():
    """Registering execution creates ExecutionState entry."""

def test_update_activity_resets_stall_counter():
    """Activity updates reset consecutive stall counter."""

def test_should_terminate_returns_false_initially():
    """Newly registered execution returns False for termination."""

def test_stall_detection_after_threshold():
    """Stall detected after threshold with no activity."""

def test_consecutive_stalls_required_for_termination():
    """Requires 2 consecutive stalls before termination."""

def test_stall_counter_resets_on_activity():
    """Activity resets stall counter even after first stall."""

def test_min_output_bytes_prevents_premature_stall():
    """Stall check skipped if output < min_output_bytes."""

def test_monitor_handles_concurrent_executions():
    """Monitor tracks multiple executions independently."""

def test_unregister_execution_removes_state():
    """Unregistering execution cleans up state."""
```

**TestMonitorLifecycle** (5 tests)

```python
async def test_monitor_can_restart_after_stop():
    """Monitor can be stopped and restarted cleanly."""

async def test_stop_with_active_executions():
    """Stopping monitor with active executions doesn't leak."""

async def test_stop_timeout_cancels_task():
    """Stop timeout cancels background task gracefully."""

async def test_monitor_health_check_interval():
    """Health checks run at configured interval."""

async def test_disabled_monitor_does_nothing():
    """Disabled monitor doesn't start background task."""
```

**TestStallDetection** (8 tests)

```python
async def test_stall_with_stdout_but_no_growth():
    """Stall detected when stdout exists but doesn't grow."""

async def test_stall_with_stderr_activity_counts():
    """Stderr activity also counts as progress."""

async def test_stall_threshold_configurable():
    """Stall threshold can be configured per execution."""

async def test_rapid_stall_checks_dont_false_trigger():
    """Rapid checks within threshold don't trigger stall."""

async def test_stall_detection_after_initial_burst():
    """Initial output burst followed by stall is detected."""

async def test_stall_recovery_on_late_activity():
    """Late activity after stall prevents termination."""

async def test_multiple_tasks_independent_stall():
    """One stalled task doesn't affect others."""

async def test_stall_callback_invoked():
    """Callback invoked when stall termination triggered."""
```

**Total:** 23 tests

---

## 2. Spawner Integration Tests

### File: `tests/integration/spawner/test_spawner_recovery.py`

**TestRetryWithBackoff** (6 tests)

```python
async def test_immediate_retry_no_delay():
    """IMMEDIATE strategy retries without delay."""

async def test_exponential_backoff_increases_delay():
    """EXPONENTIAL_BACKOFF increases delay each retry."""

async def test_retry_stops_at_max_attempts():
    """Retries stop after max_attempts reached."""

async def test_no_retry_on_timeout_when_disabled():
    """Retry on timeout can be disabled."""

async def test_circuit_breaker_prevents_retry():
    """Circuit open prevents retry attempts."""

async def test_fallback_after_all_retries_fail():
    """Fallback to LLM after all agent retries exhausted."""
```

**TestCircuitBreakerRecovery** (8 tests)

```python
async def test_circuit_opens_after_threshold():
    """Circuit opens after failure threshold reached."""

async def test_circuit_prevents_immediate_retry():
    """Open circuit skips agent, goes directly to fallback."""

async def test_circuit_resets_after_timeout():
    """Circuit closes after reset timeout expires."""

async def test_circuit_closes_on_success():
    """Successful execution closes half-open circuit."""

async def test_circuit_state_per_agent():
    """Circuit state is per-agent, not global."""

async def test_circuit_blocked_count_tracked():
    """Circuit blocked count tracked in metadata."""

async def test_circuit_recovery_logged():
    """Circuit recovery events logged to health monitor."""

async def test_multiple_circuits_independent():
    """Multiple agent circuits operate independently."""
```

**TestPartialFailureRecovery** (7 tests)

```python
async def test_critical_failure_halts_pipeline():
    """Critical subgoal failure raises RuntimeError."""

async def test_non_critical_failure_continues():
    """Non-critical failures don't halt pipeline."""

async def test_dependency_failure_skips_dependents():
    """Failed dependency causes dependent tasks to skip."""

async def test_parallel_agents_partial_failure():
    """Some agents fail, others succeed in parallel."""

async def test_fallback_success_counts_as_success():
    """Fallback to LLM counts as subgoal success."""

async def test_partial_results_synthesized():
    """Synthesis works with partial agent results."""

async def test_metadata_shows_partial_completion():
    """Metadata indicates which subgoals completed."""
```

**Total:** 21 tests

---

## 3. Health Monitor Tests

### File: `tests/unit/spawner/test_health_monitor.py`

**TestHealthMonitorTracking** (9 tests)

```python
def test_record_execution_start():
    """Start tracking creates execution record."""

def test_update_activity_without_start_ignored():
    """Activity updates ignored if execution not started."""

def test_record_success_updates_metrics():
    """Success recording updates agent success metrics."""

def test_record_failure_categorizes_reason():
    """Failure recording categorizes by FailureReason enum."""

def test_failure_history_per_agent():
    """Failure history tracked per agent."""

def test_circuit_open_event_recorded():
    """Circuit open events tracked with timestamp."""

def test_circuit_close_event_recorded():
    """Circuit close events tracked with timestamp."""

def test_recovery_event_tracks_time():
    """Recovery events include recovery duration."""

def test_health_metrics_aggregate():
    """Health metrics aggregate across executions."""
```

**TestProactiveHealthChecks** (7 tests)

```python
async def test_proactive_check_detects_no_output():
    """Proactive check detects no output within threshold."""

async def test_proactive_check_interval_configurable():
    """Check interval can be configured."""

async def test_failure_threshold_before_termination():
    """Requires N consecutive failures before termination."""

async def test_should_terminate_returns_reason():
    """Should terminate returns descriptive reason."""

async def test_proactive_checks_disabled_in_config():
    """Proactive checks can be disabled via config."""

async def test_no_output_threshold_configurable():
    """No output threshold can be configured."""

async def test_proactive_check_state_per_execution():
    """Proactive check state is per-execution."""
```

**TestHealthMonitorReset** (3 tests)

```python
def test_reset_clears_execution_state():
    """Reset clears all execution tracking state."""

def test_reset_preserves_agent_metrics():
    """Reset doesn't clear agent historical metrics."""

def test_reset_reconfigures_proactive_checks():
    """Reset applies new proactive config."""
```

**Total:** 19 tests

---

## 4. Orchestrator Recovery Tests

### File: `tests/integration/soar/test_orchestrator_recovery.py`

**TestDecompositionFailureRecovery** (5 tests)

```python
async def test_decomposition_failure_partial_response():
    """Decomposition failure returns partial results."""

async def test_decomposition_retry_on_verification_fail():
    """Failed verification triggers decomposition retry."""

async def test_decomposition_feedback_improves_retry():
    """Retry uses verification feedback for improvement."""

async def test_decomposition_failure_after_retry():
    """Two failed decompositions return error response."""

async def test_simple_path_bypasses_decomposition():
    """SIMPLE complexity bypasses decomposition entirely."""
```

**TestCollectPhaseRecovery** (6 tests)

```python
async def test_all_agents_timeout_returns_error():
    """All agents timing out returns error response."""

async def test_mixed_timeout_and_success():
    """Some timeouts, some success returns partial results."""

async def test_rate_limit_triggers_immediate_fallback():
    """Rate limit immediately falls back to LLM."""

async def test_auth_failure_no_fallback_when_disabled():
    """Auth failure with fallback disabled returns error."""

async def test_early_termination_metadata_propagated():
    """Early termination data propagates to final response."""

async def test_fallback_count_in_query_metrics():
    """Fallback count recorded in query metrics."""
```

**TestCriticalFailureHandling** (4 tests)

```python
async def test_critical_failure_activates_recovery():
    """Critical failure handler invoked with context."""

async def test_critical_failure_metadata_includes_reason():
    """Critical failure metadata includes error reason."""

async def test_critical_failure_logs_circuit_state():
    """Critical failure logs circuit breaker state."""

async def test_critical_failure_response_structure():
    """Critical failure response has recovery information."""
```

**Total:** 15 tests

---

## 5. Edge Case Tests

### File: `tests/unit/soar/test_recovery_edge_cases.py`

**TestConcurrentFailures** (6 tests)

```python
async def test_simultaneous_rate_limits():
    """Multiple agents hit rate limit simultaneously."""

async def test_simultaneous_timeouts():
    """Multiple agents timeout simultaneously."""

async def test_mixed_concurrent_failures():
    """Different failure types occur concurrently."""

async def test_circuit_opens_mid_execution():
    """Circuit opens while agents are executing."""

async def test_rate_limit_during_retry():
    """Rate limit occurs during retry attempt."""

async def test_timeout_during_fallback():
    """Timeout occurs during fallback execution."""
```

**TestResourceExhaustion** (5 tests)

```python
async def test_many_concurrent_agents():
    """System handles max concurrent agents."""

async def test_memory_pressure_detection():
    """Detection of memory pressure (if monitoring enabled)."""

async def test_all_circuits_open():
    """System handles all agents circuit broken."""

async def test_cascading_timeouts():
    """Cascading timeouts across dependent tasks."""

async def test_rapid_failure_succession():
    """Rapid succession of failures handled gracefully."""
```

**TestBoundaryConditions** (7 tests)

```python
async def test_zero_timeout_configuration():
    """Zero timeout handled as immediate failure."""

async def test_very_large_timeout():
    """Very large timeout values don't overflow."""

async def test_negative_retry_count():
    """Negative retry count treated as zero."""

async def test_empty_agent_assignments():
    """Empty agent list handled gracefully."""

async def test_null_agent_in_assignment():
    """Null agent assignment handled gracefully."""

async def test_circular_dependencies():
    """Circular task dependencies detected."""

async def test_very_long_error_message():
    """Very long error messages don't break parsing."""
```

**TestRaceConditions** (5 tests)

```python
async def test_circuit_state_race_condition():
    """Circuit state changes during concurrent access."""

async def test_health_monitor_concurrent_updates():
    """Health monitor handles concurrent updates."""

async def test_early_detection_concurrent_checks():
    """Early detection monitor concurrent health checks."""

async def test_metadata_concurrent_writes():
    """Metadata updates from concurrent agents."""

async def test_fallback_decision_race():
    """Fallback decision with concurrent failures."""
```

**Total:** 23 tests

---

## 6. Policy Configuration Tests

### File: `tests/unit/spawner/test_policy_configuration.py`

**TestPolicyPresets** (8 tests)

```python
def test_fast_fail_policy_values():
    """Fast fail policy has expected values."""

def test_patient_policy_values():
    """Patient policy has expected values."""

def test_test_policy_values():
    """Test policy has expected values."""

def test_development_policy_values():
    """Development policy has expected values."""

def test_custom_policy_creation():
    """Custom policy can be created from scratch."""

def test_policy_from_name_resolution():
    """Policy.from_name() resolves correct preset."""

def test_invalid_policy_name_raises():
    """Invalid policy name raises ValueError."""

def test_policy_serialization():
    """Policy can be serialized/deserialized."""
```

**TestTimeoutPolicyModes** (6 tests)

```python
def test_fixed_timeout_no_extension():
    """Fixed mode never extends timeout."""

def test_progressive_timeout_extends():
    """Progressive mode extends on activity."""

def test_adaptive_timeout_extension():
    """Adaptive mode adjusts based on history."""

def test_timeout_mode_from_string():
    """TimeoutMode created from string name."""

def test_get_initial_timeout_per_mode():
    """Initial timeout varies by mode."""

def test_get_extended_timeout_caps_at_max():
    """Extended timeout never exceeds max."""
```

**TestRetryPolicyConfiguration** (5 tests)

```python
def test_retry_strategy_immediate():
    """Immediate strategy has zero delay."""

def test_retry_strategy_exponential():
    """Exponential strategy increases delay."""

def test_retry_strategy_linear():
    """Linear strategy increases linearly."""

def test_jitter_applied_to_delay():
    """Jitter randomizes delay slightly."""

def test_max_attempts_enforcement():
    """Max attempts enforced across retries."""
```

**Total:** 19 tests

---

## 7. Integration Scenarios

### File: `tests/integration/soar/test_end_to_end_recovery.py`

**TestComplexRecoveryFlows** (10 tests)

```python
async def test_multi_agent_cascade_failure():
    """Agent failures cascade through dependencies."""

async def test_recovery_from_transient_errors():
    """Transient errors recovered via retry."""

async def test_persistent_errors_trigger_fallback():
    """Persistent errors eventually fallback to LLM."""

async def test_circuit_recovery_after_cooldown():
    """Circuit recovers after cooldown period."""

async def test_mixed_success_failure_synthesis():
    """Synthesis with mixed success/failure results."""

async def test_early_detection_plus_circuit_breaker():
    """Early detection works with circuit breaker."""

async def test_progressive_timeout_with_retries():
    """Progressive timeout with retry logic."""

async def test_fallback_chain_multiple_agents():
    """Multiple agents fallback in sequence."""

async def test_recovery_metadata_complete():
    """Recovery metadata complete for all scenarios."""

async def test_full_pipeline_with_all_features():
    """Full pipeline with all recovery features enabled."""
```

**Total:** 10 tests

---

## Summary

### New Test Count by Category

| Category | Test Classes | Test Count |
|----------|--------------|------------|
| Early Detection Monitor | 3 | 23 |
| Spawner Integration | 3 | 21 |
| Health Monitor | 3 | 19 |
| Orchestrator Recovery | 3 | 15 |
| Edge Cases | 4 | 23 |
| Policy Configuration | 3 | 19 |
| End-to-End Scenarios | 1 | 10 |
| **Total** | **20** | **130** |

### Combined Coverage

| Suite | Test Count |
|-------|------------|
| Existing Tests | 69 |
| New Tests | 130 |
| **Total** | **199** |

---

## Implementation Priority

### Phase 1: Critical Recovery Paths (40 tests)
1. Early Detection Monitor lifecycle (23 tests)
2. Partial failure recovery (7 tests)
3. Critical failure handling (4 tests)
4. Circuit breaker recovery (6 tests)

### Phase 2: Health Monitoring (38 tests)
1. Health monitor tracking (9 tests)
2. Proactive health checks (7 tests)
3. Health monitor reset (3 tests)
4. Policy configuration (19 tests)

### Phase 3: Edge Cases & Concurrency (46 tests)
1. Concurrent failures (6 tests)
2. Resource exhaustion (5 tests)
3. Boundary conditions (7 tests)
4. Race conditions (5 tests)
5. Retry with backoff (6 tests)
6. Decomposition recovery (5 tests)
7. Collect phase recovery (6 tests)
8. Policy presets (6 tests)

### Phase 4: Integration (10 tests)
1. Complex recovery flows (10 tests)

---

## Test Execution

### Run all new tests:
```bash
pytest tests/unit/spawner/test_early_detection_monitor.py \
       tests/integration/spawner/test_spawner_recovery.py \
       tests/unit/spawner/test_health_monitor.py \
       tests/integration/soar/test_orchestrator_recovery.py \
       tests/unit/soar/test_recovery_edge_cases.py \
       tests/unit/spawner/test_policy_configuration.py \
       tests/integration/soar/test_end_to_end_recovery.py -v
```

### Run by priority phase:
```bash
# Phase 1
pytest tests/unit/spawner/test_early_detection_monitor.py \
       tests/integration/spawner/test_spawner_recovery.py::TestPartialFailureRecovery \
       tests/integration/soar/test_orchestrator_recovery.py::TestCriticalFailureHandling \
       tests/integration/spawner/test_spawner_recovery.py::TestCircuitBreakerRecovery -v

# Phase 2
pytest tests/unit/spawner/test_health_monitor.py \
       tests/unit/spawner/test_policy_configuration.py -v

# Phase 3
pytest tests/unit/soar/test_recovery_edge_cases.py \
       tests/integration/spawner/test_spawner_recovery.py::TestRetryWithBackoff -v

# Phase 4
pytest tests/integration/soar/test_end_to_end_recovery.py -v
```

---

## Coverage Goals

### Target Coverage Areas

1. **Early Detection Monitor:** 95%+ coverage
   - `packages/spawner/src/aurora_spawner/early_detection.py`

2. **Health Monitor:** 90%+ coverage
   - `packages/spawner/src/aurora_spawner/observability.py`

3. **Orchestrator Recovery:** 85%+ coverage
   - `packages/soar/src/aurora_soar/orchestrator.py` (recovery methods)

4. **Collect Phase Recovery:** 90%+ coverage
   - `packages/soar/src/aurora_soar/phases/collect.py`

5. **Circuit Breaker:** 95%+ coverage
   - `packages/spawner/src/aurora_spawner/circuit_breaker.py`

### Coverage Command
```bash
pytest tests/unit/spawner/test_early_detection_monitor.py \
       tests/integration/spawner/test_spawner_recovery.py \
       tests/unit/spawner/test_health_monitor.py \
       tests/integration/soar/test_orchestrator_recovery.py \
       tests/unit/soar/test_recovery_edge_cases.py \
       --cov=aurora_spawner.early_detection \
       --cov=aurora_spawner.observability \
       --cov=aurora_spawner.circuit_breaker \
       --cov=aurora_soar.orchestrator \
       --cov=aurora_soar.phases.collect \
       --cov-report=html \
       --cov-report=term-missing
```

---

## Notes

- All async tests use `@pytest.mark.asyncio`
- Mock external dependencies (LLM, store, agents)
- Use fixtures for common setup
- Test both success and failure paths
- Include edge cases and boundary conditions
- Verify metadata propagation
- Test concurrent scenarios with asyncio
- Validate recovery logging
- Test policy configuration variations
