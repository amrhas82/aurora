# Plan: Add Rate Limit Error Handling

## Scope Assessment

**Answer to "Are they big?"**: **No, this is a SMALL change.**

- **Lines changed**: ~30-50 lines across 4 files
- **New files**: 0 (only test files)
- **Risk level**: Low - surgical changes that integrate with existing patterns
- **Estimated time**: 30-45 minutes

The infrastructure is 90% complete. We're just adding explicit rate limit detection to prevent:
1. Wasteful retries when quota is exhausted
2. Circuit breaker pollution (marking agents as "broken" when quota is the issue)
3. Cascading failures through the SOAR pipeline

## Current Problem

When API quota is exceeded:
- ❌ Retries 2-4 times (same error, wastes time)
- ❌ Opens circuit breaker (agent marked as "broken")
- ❌ Triggers fallback to LLM (hits same quota limit)
- ❌ Synthesis phase fails (same quota issue)

Result: Poor user experience with confusing "degradation" feeling.

## Solution Approach

Add explicit rate limit detection at the spawner layer. Rate limits are already recognized by `ErrorClassifier` (recovery.py) but not used by spawner's error classification logic.

**Key insight**: Rate limits should be treated differently from other failures:
- Don't retry (quota won't reset for hours)
- Don't open circuit breaker (agent isn't broken, API quota is exhausted)
- Provide clear user feedback ("quota exceeded, retry after X")

## Implementation Details

### File 1: `packages/spawner/src/aurora_spawner/observability.py`

**Change**: Add `RATE_LIMIT` to `FailureReason` enum (line 24)

```python
class FailureReason(Enum):
    TIMEOUT = "timeout"
    ERROR_PATTERN = "error_pattern"
    NO_ACTIVITY = "no_activity"
    CIRCUIT_OPEN = "circuit_open"
    CRASH = "crash"
    KILLED = "killed"
    RATE_LIMIT = "rate_limit"  # NEW
    UNKNOWN = "unknown"
```

**Lines changed**: 1 line added

---

### File 2: `packages/spawner/src/aurora_spawner/spawner.py`

**Change**: Add rate limit detection to error classification (lines 1405-1439)

Current code classifies errors as: timeout, error_pattern, inference, crash.

**Add after line 1415** (before "inference" check):
```python
elif any(x in reason_lower for x in ["rate limit", "429", "quota exceeded", "too many requests"]):
    error_type = "rate_limit"
    failure_type = "rate_limit"
```

**Add after line 1425** (in `elif result.error` block):
```python
# Check for rate limit errors first
if any(x in error_lower for x in ["rate limit", "429", "quota exceeded", "too many requests"]):
    error_type = "rate_limit"
    failure_type = "rate_limit"
elif any(x in error_lower for x in ["api", "connection", "json", "parse", "model"]):
    failure_type = "inference"
```

**Lines changed**: 6 lines added

**Pattern detection**: Matches errors containing:
- "rate limit"
- "429" (HTTP status code)
- "quota exceeded"
- "too many requests"

---

### File 3: `packages/spawner/src/aurora_spawner/timeout_policy.py`

**Change**: Prevent retries for rate limits (line 119)

Add before final return in `should_retry()` method:
```python
# Rate limits: Don't retry (quota won't reset for hours)
if error_type == "rate_limit":
    return False, "Rate limit exceeded - quota exhausted, retries would fail"
```

**Lines changed**: 2 lines added

**Impact**: Rate limit errors fail immediately without retries.

---

### File 4: `packages/spawner/src/aurora_spawner/circuit_breaker.py`

**Change**: Skip circuit breaker logic for rate limits (line 181)

Add after adhoc agent inference check (around line 181):
```python
# Rate limit failures should NOT trigger circuit breaker or fast-fail
# The agent isn't broken - API quota is exhausted (external constraint)
is_rate_limit = failure_type == "rate_limit"
if is_rate_limit:
    logger.warning(
        f"Agent '{agent_id}' hit rate limit (quota exhausted) - "
        f"not opening circuit breaker (agent not broken, API quota issue)"
    )
    return  # Early exit - don't track as circuit breaker failure
```

**Lines changed**: 7 lines added

**Impact**: Rate limits don't poison circuit breaker state.

---

## What Stays the Same

**No changes needed** (infrastructure already exists):
- Error message formatting - `ErrorHandler.handle_api_error()` already formats rate limit errors
- LLM client - `CLIPipeLLMClient` raises `RuntimeError` as before
- Error propagation - Spawner wraps in `SpawnResult` as before
- Fallback logic - Still triggers (different agent = different quota)
- Logging - Uses existing logger infrastructure

## Testing Strategy

### Unit Tests
Create `tests/unit/spawner/test_rate_limit_handling.py`:

1. **Test detection** - Verify all rate limit patterns recognized
2. **Test retry policy** - Verify no retries for rate limits
3. **Test circuit breaker** - Verify rate limits don't open circuit
4. **Test metrics** - Verify `FailureReason.RATE_LIMIT` tracked correctly
5. **Test isolation** - Verify inference errors still retry/circuit normally

### Integration Test
Add to `tests/integration/test_error_recovery.py`:

Mock CLI tool to return 429 error, verify:
- Only 1 attempt (no retries)
- Circuit breaker stays closed
- Clear rate limit message returned

### Manual Verification
1. Trigger rate limit error: `aur spawn research-agent "test"`
2. Check logs: Should see "Rate limit exceeded" without "Circuit OPEN"
3. Verify metrics: `FailureReason.RATE_LIMIT` appears in health monitor

## Critical Files

Implementation:
- `packages/spawner/src/aurora_spawner/observability.py` - Add enum value
- `packages/spawner/src/aurora_spawner/spawner.py` - Add detection logic
- `packages/spawner/src/aurora_spawner/timeout_policy.py` - Skip retries
- `packages/spawner/src/aurora_spawner/circuit_breaker.py` - Skip circuit breaker

Testing:
- `tests/unit/spawner/test_rate_limit_handling.py` - New comprehensive test file
- `tests/integration/test_error_recovery.py` - Add integration test

## Implementation Sequence

1. Add enum value (safest, enables metrics)
2. Add detection logic (core change)
3. Add retry guard (prevents waste)
4. Add circuit breaker guard (prevents pollution)
5. Write tests (validates behavior)
6. Manual verification (end-to-end check)

## Edge Cases Covered

- Mixed errors (rate limit + connection) - rate limit takes precedence
- Adhoc agents - same treatment as regular agents
- Fallback to LLM - still works (different quota)
- Partial failures - rate limits tracked separately

## Success Criteria

After implementation:
1. ✅ Rate limit errors fail fast (1 attempt, no retries)
2. ✅ Circuit breaker stays closed after rate limit errors
3. ✅ Clear user message: "quota exceeded, retry after X"
4. ✅ Metrics show rate limits separately from inference failures
5. ✅ Normal errors (timeout, inference) still retry and circuit normally
