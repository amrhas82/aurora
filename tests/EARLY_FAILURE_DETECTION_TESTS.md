# Early Failure Detection Test Suite

Comprehensive test suite for early failure detection and recovery in Aurora's SOAR pipeline.

## Overview

These tests validate that the SOAR pipeline detects and handles agent failures **early** (within seconds) rather than waiting for full timeouts (minutes). This prevents wasted time and resources when agents encounter recoverable errors like rate limits, authentication failures, or connection issues.

## Test Files

### 1. Unit Tests - SOAR (`tests/unit/soar/test_early_failure_detection.py`)

Tests SOAR orchestrator and collect phase early detection mechanisms.

**Test Classes:**

- **TestEarlyTerminationDetection** (7 tests)
  - TerminationPolicy detects rate limits, auth failures, connection errors, API errors
  - Custom termination predicates
  - Disabled policy behavior
  - No false positives on benign errors

- **TestProgressiveTimeoutDetection** (4 tests)
  - Progressive timeout extends on activity
  - Caps at max timeout
  - Early detection vs fixed timeout comparison

- **TestNoActivityTimeout** (3 tests)
  - Fast fail policy: 15s no-activity timeout
  - Patient policy: 120s no-activity timeout for agents
  - Test policy: 10s no-activity timeout

- **TestFailFastRetryPolicy** (4 tests)
  - Immediate retry strategy (zero delay)
  - Exponential backoff increases delay
  - Max attempts enforcement
  - Disabled retry on timeout

- **TestCollectPhaseEarlyFailures** (3 async tests)
  - Timeout detected immediately (<1s) without waiting for full timeout
  - Rate limit detected early
  - Global timeout prevents hanging pipeline

- **TestCircuitBreakerIntegration** (3 tests)
  - Circuit breaker enabled in default policy
  - Disabled in development policy for debugging
  - Disabled in test policy for predictability

- **TestFailurePatternAnalysis** (4 tests)
  - Orchestrator categorizes timeouts separately
  - Categorizes rate limits separately
  - Categorizes auth failures separately
  - Tracks early terminations with metadata

- **TestMetadataTracking** (1 test)
  - Phase 5 metadata includes detailed recovery metrics

**Total:** 29 unit tests

### 2. Unit Tests - Spawner (`tests/unit/spawner/test_early_termination.py`)

Tests spawner TerminationPolicy error pattern detection.

**Test Classes:**

- **TestTerminationPolicy** (14 tests)
  - Rate limit pattern detection (various formats)
  - Auth failure patterns (401, 403, invalid key, unauthorized)
  - Connection error patterns (ECONNRESET, refused, reset)
  - API error patterns
  - Quota exceeded patterns
  - Model unavailable patterns
  - No false positives on warnings or progress messages
  - Custom predicate support (single and multiple)
  - Disabled policy behavior
  - Error pattern control flag

- **TestTerminationPolicyPatternCoverage** (5 tests)
  - All default patterns are valid regex
  - Pattern variations matching (rate-limit, rate_limit, ratelimit)
  - Connection pattern variations
  - API error pattern variations
  - Authentication pattern variations

- **TestNoActivityTermination** (1 test)
  - Documents separation between TerminationPolicy and TimeoutPolicy

- **TestTerminationReason** (2 tests)
  - Reason includes matched pattern
  - Custom predicate reason is descriptive

- **TestEdgeCases** (5 tests)
  - Empty stderr doesn't trigger
  - None stderr handled gracefully
  - Very long stderr with error detected
  - Zero elapsed time handled
  - Negative last_activity handled gracefully

**Total:** 27 unit tests

### 3. Integration Tests (`tests/integration/soar/test_early_failure_recovery.py`)

End-to-end scenarios with real timeout policies and spawner integration.

**Test Classes:**

- **TestEarlyTimeoutDetection** (2 async tests)
  - Agent with no activity times out early (<2s) instead of waiting for full 300s
  - Global timeout prevents pipeline hanging on stuck agents

- **TestEarlyErrorPatternDetection** (3 async tests)
  - Rate limit detected immediately (<1s)
  - Auth failure detected immediately (<1s)
  - Connection error detected immediately (<1s)

- **TestOrchestratorFailureAnalysis** (2 tests)
  - Orchestrator categorizes failures in metadata
  - Tracks early terminations separately from timeouts

- **TestProgressiveTimeoutInPipeline** (1 async test)
  - Progressive timeout starts short, extends on activity

- **TestFallbackMetadataTracking** (2 tests)
  - Fallback agents tracked in CollectResult
  - Orchestrator includes fallback in recovery metrics

- **TestRecoveryLogging** (2 async tests)
  - Circuit breaker failures logged to metadata
  - Recovery summary logged after collect

- **TestEndToEndRecovery** (1 test)
  - Mixed failures with appropriate recovery strategies

**Total:** 13 integration tests (11 async)

## Total Test Coverage

- **Unit Tests:** 56 tests (29 SOAR + 27 spawner)
- **Integration Tests:** 13 tests
- **Total:** 69 tests

## Key Features Tested

### 1. Early Termination Detection

- **Error Pattern Matching:** Regex-based detection of common failure patterns
  - Rate limits (429, "rate limit", "quota exceeded")
  - Authentication failures (401, 403, "unauthorized", "invalid API key")
  - Connection errors (ECONNRESET, "connection refused/reset/error")
  - API errors ("API error", service unavailable)
  - Model availability ("model not available")

- **Custom Predicates:** Support for application-specific termination conditions
  - Single predicate support
  - Multiple predicates (OR logic)
  - Example: OOM detection, segmentation faults

### 2. Progressive Timeout

- **Adaptive Timeouts:** Start with short timeout, extend when activity detected
  - Initial timeout: 60-120s depending on policy
  - Extension threshold: 10-15s of recent activity
  - Max timeout: 300-600s depending on policy
  - Extension factor: 1.5x current timeout

- **No-Activity Timeout:** Faster failure when agent produces no output
  - Fast fail policy: 15s
  - Default policy: 30s
  - Patient policy: 120s (for agents that "think")
  - Test policy: 10s

### 3. Failure Categorization

- **Orchestrator Analysis:** `_analyze_execution_failures()` categorizes failures
  - `failed_count`: Total failures
  - `timeout_failures`: List of timed-out agents
  - `rate_limit_failures`: List of rate-limited agents
  - `auth_failures`: List of auth-failed agents
  - `circuit_failures`: List of circuit-broken agents
  - `early_term_count`: Early terminations with metadata
  - `early_term_details`: Detailed termination reasons and timings

### 4. Policy Presets

- **SpawnPolicy.fast_fail()**: Short timeouts, minimal retries
  - Timeout: 60s fixed
  - No-activity: 15s
  - Max attempts: 1
  - No retry on timeout

- **SpawnPolicy.patient()**: Longer timeouts for agent execution
  - Initial: 120s, max: 600s progressive
  - No-activity: 120s
  - Max attempts: 2
  - Early termination enabled

- **SpawnPolicy.test()**: Fast feedback for testing
  - Timeout: 30s fixed
  - No-activity: 10s
  - Max attempts: 1
  - Circuit breaker disabled

- **SpawnPolicy.development()**: Patient for debugging
  - Timeout: 1800s (30 min) fixed
  - No-activity: 300s (5 min)
  - Max attempts: 1
  - Termination disabled

### 5. Global Timeout Protection

- **Parallel Execution Safeguard:** Global timeout = agent_timeout * 0.4
  - Prevents entire pipeline hanging on one stuck agent
  - Returns partial results on timeout
  - Example: 300s agent timeout → 120s global timeout

### 6. Recovery Metadata

- **Phase 5 (Collect) Metadata:** Detailed recovery tracking
  ```python
  {
      "total_failures": int,
      "early_terminations": int,
      "circuit_breaker_blocks": int,
      "circuit_blocked_agents": [agent_ids],
      "timeout_count": int,
      "timeout_agents": [agent_ids],
      "rate_limit_count": int,
      "rate_limit_agents": [agent_ids],
      "auth_failure_count": int,
      "auth_failed_agents": [agent_ids],
      "fallback_used_count": int,
      "fallback_agents": [agent_ids],
  }
  ```

## Running the Tests

### All early failure detection tests:
```bash
pytest tests/unit/soar/test_early_failure_detection.py \
       tests/unit/spawner/test_early_termination.py \
       tests/integration/soar/test_early_failure_recovery.py -v
```

### Unit tests only:
```bash
pytest tests/unit/soar/test_early_failure_detection.py \
       tests/unit/spawner/test_early_termination.py -v
```

### Integration tests only:
```bash
pytest tests/integration/soar/test_early_failure_recovery.py -v
```

### Specific test class:
```bash
pytest tests/unit/soar/test_early_failure_detection.py::TestEarlyTerminationDetection -v
```

### With coverage:
```bash
pytest tests/unit/soar/test_early_failure_detection.py \
       tests/unit/spawner/test_early_termination.py \
       --cov=aurora_soar.orchestrator \
       --cov=aurora_soar.phases.collect \
       --cov=aurora_spawner.timeout_policy
```

## Performance Characteristics

### Before Early Detection
- Rate limit error: Wait 120s (agent timeout) before detecting
- Auth failure: Wait 120s before detecting
- Stuck agent: Wait 300s before global timeout

### After Early Detection
- Rate limit error: Detected in <1s
- Auth failure: Detected in <1s
- No-activity timeout: Detected in 10-30s (vs 120-300s)
- Stuck agent: Global timeout at 120s (vs 300s per agent)

**Time Savings:** 10-100x faster failure detection

## Test Fixtures

### Common Fixtures (in tests)

```python
@pytest.fixture
def mock_store():
    """Mock ACT-R store."""

@pytest.fixture
def test_config(tmp_path):
    """Test configuration."""

@pytest.fixture
def mock_llm():
    """Mock LLM client."""

@pytest.fixture
def orchestrator(mock_store, test_config, mock_llm):
    """SOAR orchestrator with mocked dependencies."""
```

## Implementation References

- **Orchestrator:** `packages/soar/src/aurora_soar/orchestrator.py`
  - `_analyze_execution_failures()` at line 1407
  - `_trigger_circuit_recovery()` at line 1486
  - `_phase5_collect()` at line 671

- **Collect Phase:** `packages/soar/src/aurora_soar/phases/collect.py`
  - `execute_agents()` at line 179
  - Global timeout logic at line 378-384

- **Timeout Policy:** `packages/spawner/src/aurora_spawner/timeout_policy.py`
  - `TerminationPolicy` at line 202
  - `TimeoutPolicy` at line 123
  - `SpawnPolicy` presets at line 290-435

## Notes

- All async tests use `@pytest.mark.asyncio` decorator
- Tests use mocking extensively to avoid real LLM calls
- Integration tests validate end-to-end behavior
- Unit tests focus on individual components
- Coverage includes success paths, failure paths, and edge cases
