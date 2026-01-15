# Tasks: Spawn Early Failure Detection

**Total**: 8 tasks across 3 phases
**Status**: COMPLETE
**Files**: 2 (spawner.py modified, circuit_breaker.py new)

---

## Phase 1: Circuit Breaker (2 tasks)

**Goal**: Track agent failures and skip known-broken agents

- [x] 1. Create CircuitBreaker class
  - Location: `packages/spawner/src/aurora_spawner/circuit_breaker.py`
  - States: CLOSED (normal), OPEN (skip), HALF_OPEN (test)
  - ~100 lines

- [x] 2. Add module exports
  - Updated `packages/spawner/src/aurora_spawner/__init__.py`
  - Exports: `CircuitBreaker`, `get_circuit_breaker`

---

## Phase 2: Error Detection + Progressive Timeout (4 tasks)

**Goal**: Detect errors early and fail fast

- [x] 3. Define error patterns
  - 11 patterns: rate limit, 429, connection errors, API errors, auth failures, etc.

- [x] 4. Implement async stderr reader
  - Reads stderr line by line
  - Kills process immediately on error pattern match

- [x] 5. Add stdout activity tracking
  - Tracks if stdout received
  - Used to determine if process is "active"

- [x] 6. Implement progressive timeout
  - Initial: 60s (fail fast if no activity)
  - Extended: 300s (if stdout activity detected)

---

## Phase 3: Integration (2 tasks)

**Goal**: Wire everything together

- [x] 7. Integrate into spawn_with_retry_and_fallback()
  - Checks circuit before spawn
  - Records failures/successes
  - Skips to fallback when circuit open

- [x] 8. Add logging and metrics
  - Logs circuit state changes
  - Logs error pattern detection
  - Logs timeout decisions

---

## Implementation Summary

**New file**: `packages/spawner/src/aurora_spawner/circuit_breaker.py` (~100 lines)
- `CircuitBreaker` class with CLOSED/OPEN/HALF_OPEN states
- `get_circuit_breaker()` singleton accessor

**Modified**: `packages/spawner/src/aurora_spawner/spawner.py`
- Added `ERROR_PATTERNS` (11 regex patterns)
- Added `INITIAL_TIMEOUT=60`, `EXTENDED_TIMEOUT=300`
- Rewrote `spawn()` with async stderr/stdout readers
- Added circuit breaker integration to `spawn_with_retry_and_fallback()`

**Behavior**:
```
Error in stderr  → Kill in <5s (vs 300s timeout)
No stdout 60s    → Fail fast (vs 300s wait)
Stdout activity  → Extend to 300s
2 agent failures → Skip agent, go to fallback
After 120s       → Try agent once (half-open)
```

---

## Validation

```bash
# Verify imports
python3 -c "from aurora_spawner import CircuitBreaker; print('OK')"

# Test circuit breaker
python3 -c "
from aurora_spawner import CircuitBreaker
cb = CircuitBreaker(failure_threshold=2)
cb.record_failure('test')
cb.record_failure('test')
print(cb.should_skip('test'))  # (True, 'Circuit open...')
"
```

---

## Definition of Done

- [x] Circuit breaker skips agents after 2 failures
- [x] Error patterns kill process within 5s of error output
- [x] Progressive timeout: 60s initial, 300s if activity
- [x] Logging shows circuit state changes
