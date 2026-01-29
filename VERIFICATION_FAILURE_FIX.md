# Fix: SOAR Verification Failure Handling

## Issues Fixed

### 1. **Prompting to save after verification failure**
**Problem:** When SOAR verification fails (e.g., due to circular dependencies), the system shows "Save goals? [Y/n]" even though the decomposition failed.

**Root Cause:** The code created a fallback single-task plan when SOAR returned empty subgoals, then proceeded to show the save prompt as if everything succeeded.

**Fix:** Now when verification fails, `create_plan()` returns `PlanResult(success=False)` with an error message instead of creating a fallback plan. The "Save goals?" prompt is never shown for failed decompositions.

### 2. **Complexity inconsistency (MEDIUM → SIMPLE)**
**Problem:** Initial assessment shows `Complexity: MEDIUM`, but the final summary shows `Complexity: SIMPLE`.

**Root Cause:**
- Phase 1 (Assess) correctly evaluated the query as MEDIUM complexity
- When verification failed and a fallback single-task plan was created, the complexity was reassessed
- A single-task plan is always SIMPLE, causing the inconsistency

**Fix:** Verification failure now returns an error immediately, so complexity is never reassessed. The original MEDIUM assessment is preserved in the error flow.

### 3. **Should fail instead of degrading silently**
**Problem:** When verification fails with circular dependencies, the system silently degrades to a single-task plan instead of failing explicitly.

**Root Cause:** The fallback logic treated empty subgoals as a recoverable condition and created a generic single-task plan.

**Fix:** Empty subgoals from SOAR are now treated as a hard failure. The system returns an explicit error message:
```
Failed to decompose goal: verification failed after retry.
This may be due to circular dependencies or invalid decomposition.
Please rephrase your goal or try a simpler approach.
```

## Changes Made

### File: `packages/cli/src/aurora_cli/planning/core.py`

#### Change 1: Added error detection in `_decompose_with_soar()` (line ~1358)
```python
# Check for verification failure in phase metadata
phases_metadata = metadata.get("phases", {})
if "verification_failure" in phases_metadata:
    verification_error = phases_metadata["verification_failure"]
    feedback = verification_error.get("feedback", "Unknown verification error")
    issues = verification_error.get("issues", [])
    error_details = f": {', '.join(issues)}" if issues else ""
    logger.error(f"SOAR verification failed{error_details}")
    # Return empty subgoals to trigger error handling in create_plan
    return [], {}, "failed", []
```

This checks for the `verification_failure` key in the SOAR result metadata and returns empty subgoals to signal failure.

#### Change 2: Modified `create_plan()` to handle verification failure (line ~1504)
```python
try:
    subgoals, file_resolutions, decomposition_source, soar_memory_context = (
        _decompose_with_soar(
            goal=goal,
            config=config,
            context_files=[str(f) for f in context_files] if context_files else None,
            no_cache=no_cache,
        )
    )
    # Use SOAR's memory context (from phase 2 retrieve)
    memory_context = soar_memory_context or []

    # Check if SOAR decomposition failed (returns empty subgoals)
    # This happens when verification fails (e.g., circular dependencies)
    if not subgoals:
        logger.error("SOAR decomposition failed - returning error instead of fallback")
        return PlanResult(
            success=False,
            error=(
                "Failed to decompose goal: verification failed after retry. "
                "This may be due to circular dependencies or invalid decomposition. "
                "Please rephrase your goal or try a simpler approach."
            ),
        )
except Exception as e:
    logger.error("SOAR decomposition raised exception: %s", e)
    return PlanResult(
        success=False,
        error=f"Failed to decompose goal: {e}",
    )
```

This replaces the fallback logic with explicit error handling. When empty subgoals are detected (signaling verification failure), it returns a `PlanResult` with `success=False`.

## Behavior Changes

### Before
```
[ORCHESTRATOR] Phase 4: Verify
WARNING: Verification failed: ['Circular dependency detected in subgoal dependency graph involving subgoal 6']
ERROR: Decomposition verification failed after retry
WARNING: SOAR decomposition returned empty subgoals, using fallback

╭──────────────────────────────────── Plan Decomposition Summary ─────────────────────────────────────╮
│ Goal: how can i improve aur mem search when it starts?                                              │
│ Subgoals: 1                                                                                         │
│   [++] Implement goal: @code-developer                                                              │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────╯

╭────────────────────────────────────────────── Summary ──────────────────────────────────────────────╮
│ Complexity: SIMPLE                  [Inconsistent! Was MEDIUM]                                      │
│ Source: heuristic                   [Should be "failed"]                                            │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────╯

Save goals? [Y/n] ():  [SHOULD NOT PROMPT!]
```

### After
```
[ORCHESTRATOR] Phase 4: Verify
WARNING: Verification failed: ['Circular dependency detected in subgoal dependency graph involving subgoal 6']
ERROR: Decomposition verification failed after retry
ERROR: SOAR decomposition failed - returning error instead of fallback

Error: Failed to decompose goal: verification failed after retry.
This may be due to circular dependencies or invalid decomposition.
Please rephrase your goal or try a simpler approach.

[No prompt, exit with error code 1]
```

## Testing

Run the test script to verify the changes:
```bash
python test_verification_failure.py
```

## Recovery Actions

When you see a verification failure:

1. **Rephrase the goal** - Make it clearer or more specific
2. **Simplify the goal** - Break it into smaller, independent pieces
3. **Check for circular logic** - Ensure your goal doesn't have implicit circular dependencies
4. **Use --no-cache** - Force fresh decomposition if you think the cached result is bad:
   ```bash
   aur goals "your goal" --no-cache
   ```

## Related Files

- `packages/cli/src/aurora_cli/planning/core.py` - Main fix location
- `packages/soar/src/aurora_soar/orchestrator.py` - Verification logic
- `packages/cli/src/aurora_cli/execution/review.py` - "Save goals?" prompt logic

## Commit Message

```
fix: fail explicitly when SOAR verification fails instead of degrading to fallback

When SOAR verification fails (e.g., due to circular dependencies), the
system was silently degrading to a single-task fallback plan and still
prompting to save goals. This caused:
- Inconsistent complexity (MEDIUM → SIMPLE)
- Misleading "Save goals?" prompt on failed decomposition
- Silent failures instead of explicit error messages

Now when verification fails:
- Returns PlanResult(success=False) with clear error message
- No "Save goals?" prompt is shown
- Original complexity assessment is preserved
- User gets actionable error message explaining the failure

Fixes three issues reported in user feedback:
1. Should not offer save goals after failure
2. Complexity inconsistency (MEDIUM vs SIMPLE)
3. Should fail explicitly instead of degrading silently
```

## Verification

To verify the fix works:

1. Create a goal that triggers circular dependencies (or use a complex goal that might fail verification)
2. Run: `aur goals "complex goal that may fail"`
3. Expected: See error message, no "Save goals?" prompt
4. Verify: Check that no plan is created in `.aurora/plans/active/`
