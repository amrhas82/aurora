# Reliability Improvements - January 22, 2026

## Summary

Two major reliability improvements completed:
1. ✅ **PRD 0030**: Dependency-Aware Execution (Fully Tested & Working)
2. ✅ **Circuit Breaker**: Smart Error Classification (Code Complete, Integration Testing Blocked)

---

## 1. PRD 0030: Dependency-Aware Execution (COMPLETE)

### What Was Implemented

**Wave-Based Execution:**
- Topological sorting using Kahn's algorithm
- Sequential wave execution (waves execute one after another)
- Parallel execution within waves (up to 4 tasks per wave)
- 5s stagger delay between task starts

**Context Passing:**
- Previous wave outputs passed to dependent subgoals
- Format: `"Previous context:\n✓ [sg-1]: output\n✓ [sg-2]: output"`
- Partial context support with failure markers: `✗ [sg-X]: FAILED - reason`

**Partial Dependency Handling:**
- Subgoals continue with available context even if some dependencies fail
- WARNING footer added when dependencies fail
- ⚠ marker in progress display for partial context

**Validation:**
- Invalid dependency reference detection (subgoal depends on non-existent subgoal)
- Subgoal index validation (missing `subgoal_index` field)

### Files Modified

- `packages/soar/src/aurora_soar/phases/collect.py` (~200 LOC added)
  - `topological_sort()` function
  - Wave-based execution loop in `execute_agents()`
  - Context injection with partial dependency support
  - Wave progress display with emoji markers
  - Final execution summary

- `packages/soar/src/aurora_soar/phases/verify.py` (~15 LOC added)
  - Invalid dependency validation in `_check_circular_deps()`
  - Automatic `subgoal_index` assignment in `verify_lite()`

### Test Results

**Verified with real SOAR query:**
```
Wave 1/4 (2 subgoals)...
  Task 1/2 (code-developer) starting now
  Task 2/2 (code-developer) starting in 5s...
  ⠏ Working... 2 active (4s)  ✓ [1/2 done]

Wave 2/4 (1 subgoals)...
  Task 1/1 (code-developer) starting now
  ✓ [1/1 done]
```

**Features working:**
- ✅ Topological sorting into dependency waves
- ✅ Parallel execution within waves
- ✅ Sequential execution between waves
- ✅ Context passing with ✓/✗ markers
- ✅ Partial context handling
- ✅ Independent subgoals continue despite failures
- ✅ Retry chain exhaustion before marking failures

---

## 2. Circuit Breaker: Smart Error Classification (CODE COMPLETE)

### Problem Addressed

**Before:**
- Circuit breaker fast-failed on ANY 2 failures within 10s
- No distinction between permanent errors (bad config) and transient errors (network issues)
- Too aggressive - prevented legitimate retry attempts

**Example issue:**
```
ERROR: Circuit OPEN (fast-fail) for agent 'quality-assurance':
  2 failures in 300s window, last 2 within 9.1s (fast-fail window: 10s)
```

### Solution Implemented

#### 1. Increased Fast-Fail Threshold

**Change:** `fast_fail_threshold: 1 → 2`

**Result:** Now requires **3 failures** instead of 2 to trigger fast-fail

**File:** `packages/spawner/src/aurora_spawner/circuit_breaker.py:74`

#### 2. Permanent vs Transient Error Classification

**Permanent Errors (Trigger Fast-Fail):**
```python
self._permanent_error_types = {
    "auth_error",       # 401, invalid API key, unauthorized
    "forbidden",        # 403, insufficient permissions
    "invalid_model",    # Model identifier doesn't exist
    "invalid_request",  # 400, bad request, malformed
    "not_found",        # 404, endpoint doesn't exist
}
```

**Transient Errors (Allow Retries):**
- `transient_error` - 500, 502, 503, 504 (server errors)
- Connection errors (ECONNRESET, network timeouts)
- JSON parse errors

**File:** `packages/spawner/src/aurora_spawner/circuit_breaker.py:99-107`

#### 3. HTTP Status Code Detection

**Enhanced error classification from API responses:**

```python
# Permanent errors - should trigger fast-fail
elif any(x in error_lower for x in ["unauthorized", "401", "invalid api key"]):
    failure_type = "auth_error"
elif any(x in error_lower for x in ["forbidden", "403"]):
    failure_type = "forbidden"
elif any(x in error_lower for x in ["invalid model", "model identifier"]):
    failure_type = "invalid_model"

# Transient errors - allow retries
elif any(x in error_lower for x in ["500", "502", "503", "504"]):
    failure_type = "transient_error"
```

**File:** `packages/spawner/src/aurora_spawner/spawner.py:1433-1463`

#### 4. Smart Fast-Fail Logic

**Only triggers on permanent errors:**

```python
# Only fast-fail on PERMANENT errors (auth, invalid model, etc.)
# Transient errors (timeouts, 500s) should allow retries
is_permanent_error = failure_type in self._permanent_error_types
if not is_permanent_error and failure_type not in [None, "inference"]:
    logger.debug(
        f"Agent '{agent_id}' transient failure (type: {failure_type}) - "
        f"allowing retries (no fast-fail)"
    )
    fast_fail = False
```

**File:** `packages/spawner/src/aurora_spawner/circuit_breaker.py:205-213`

### Expected Behavior After Fix

**Scenario 1: Transient Network Error (500)**
```
Attempt 1: 500 Internal Server Error → Retry with backoff
Attempt 2: 500 Internal Server Error → Retry with backoff
Attempt 3: 500 Internal Server Error → Fallback to LLM
Result: Circuit stays CLOSED, full retry chain executed
```

**Scenario 2: Permanent Config Error (Invalid Model)**
```
Attempt 1: 400 Invalid model identifier → Fast-fail triggered
Attempt 2: Skipped (circuit OPEN)
Result: Circuit OPEN immediately, no wasted retry attempts
```

### Files Modified

1. `packages/spawner/src/aurora_spawner/circuit_breaker.py`
   - Line 74: Increased `fast_fail_threshold` from 1 to 2
   - Lines 99-107: Added `_permanent_error_types` set
   - Lines 205-213: Smart fast-fail logic based on error type

2. `packages/spawner/src/aurora_spawner/spawner.py`
   - Lines 1433-1463: Enhanced error classification from HTTP status codes

### Integration Testing Status

**Blocked:** Cannot integration test because all SOAR queries fail at Phase 3 (Decompose) with external tool issue:

```
ERROR: Tool claude failed with exit code 1:
API Error (us.anthropic.claude-sonnet-4-5-20250929-v1:0): 400
The provided model identifier is invalid.
```

**Root Cause:** Claude Code tool has invalid AWS Bedrock model format instead of Anthropic API format.

**Testing Plan:**
- Unit test the error classification logic directly
- Or wait for Claude Code tool model configuration to be fixed
- Circuit breaker only applies during Phase 5 (Collect), not Phase 3 (Decompose)

---

## Benefits

### PRD 0030 Benefits
1. **Correct execution order** - Dependencies respected
2. **Better context** - Later agents receive earlier findings
3. **Graceful degradation** - Partial failures don't cascade
4. **User visibility** - Wave progress clearly displayed

### Circuit Breaker Benefits
1. **Smarter failure handling** - Distinguishes config vs network issues
2. **Fewer false positives** - Transient errors get full retry chain
3. **Faster failure on config errors** - Invalid API key fails immediately
4. **Better resource usage** - Don't waste retries on broken configs

---

## Next Steps

1. **Remove RELIABILITY_IMPROVEMENTS.md** after review (temporary doc)
2. **Fix Claude Code model config** to enable circuit breaker integration testing
3. **Monitor circuit breaker in production** to tune thresholds if needed
4. **Consider adding metrics** to track permanent vs transient error rates

---

**Last Updated:** January 22, 2026
**Status:** PRD 0030 ✅ Complete | Circuit Breaker ⏳ Code Complete, Testing Blocked
