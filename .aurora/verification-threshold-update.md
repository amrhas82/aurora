# Verification Threshold Update (2026-01-08)

## Summary

Lowered SOAR Phase 4 verification threshold from **0.7 → 0.6** to reduce false rejections while maintaining quality through enhanced explanation requirements.

## Motivation

The 0.7 threshold was too strict - valid decompositions with scores of 0.54-0.69 were being rejected and exhausting all 3 retries. This blocked the SOAR pipeline from reaching phases 5-9 even for reasonable decompositions.

## The "Devil's Advocate" Territory

Scores in the range **[0.60, 0.70)** are now considered "devil's advocate" territory:
- **Verdict:** PASS (threshold met, pipeline proceeds)
- **Quality bar:** Acceptable but marginal
- **Requirements:** LLM must provide EXTRA detailed explanations including:
  - Specific concerns in critical_issues/minor_issues
  - Edge cases that could cause problems
  - Actionable suggestions to strengthen the decomposition

This approach balances pragmatism (allowing imperfect but valid decompositions) with quality (surfacing concerns for user awareness).

## Changes Made

### 1. Core Verification Logic
**File:** `packages/reasoning/src/aurora_reasoning/verify.py`

- Updated `VerificationVerdict` enum comments
- Modified `_auto_correct_verdict()` to use 0.6 threshold
- Added documentation explaining devil's advocate behavior

```python
# Before
if score >= 0.7:
    correct_verdict = VerificationVerdict.PASS

# After
if score >= 0.6:
    correct_verdict = VerificationVerdict.PASS
```

### 2. Adversarial Verification Prompt
**File:** `packages/reasoning/src/aurora_reasoning/prompts/verify_adversarial.py`

- Updated system prompt with new verdict logic
- Added explicit instructions for handling scores in [0.60, 0.70):
  ```
  For scores in [0.60, 0.70):
  - Still mark as PASS (threshold met)
  - But provide EXTRA detailed explanation of concerns
  - List specific edge cases that could cause problems
  - Provide actionable suggestions to strengthen the decomposition
  ```

### 3. Self-Verification Prompt
**File:** `packages/reasoning/src/aurora_reasoning/prompts/verify_self.py`

- Updated system prompt with new thresholds
- Added similar devil's advocate instructions

### 4. Synthesis Module
**File:** `packages/reasoning/src/aurora_reasoning/synthesize.py`

- Updated quality threshold check: `>= 0.6` (was `>= 0.7`)
- Updated docstring and feedback messages

### 5. Documentation

**File:** `packages/reasoning/examples/sample_queries.md`
- Updated confidence score interpretation table

**File:** `docs/architecture/SOAR_ARCHITECTURE.md`
- Updated Phase 4 verdict logic section
- Added devil's advocate explanation

## New Verdict Thresholds

| Score Range | Verdict | Behavior |
|-------------|---------|----------|
| ≥ 0.7 | PASS | Strong - proceed with confidence |
| 0.6 - 0.7 | PASS (devil's advocate) | Acceptable - proceed with detailed concerns |
| 0.5 - 0.6 | RETRY | Needs revision - retry with feedback |
| < 0.5 | FAIL | Fundamental issues - abort or degrade |

## Confidence Score Interpretation

| Confidence | Interpretation | Action |
|------------|---------------|---------|
| 0.9-1.0 | Excellent | Use as-is |
| 0.8-0.9 | Good | Review minor issues |
| 0.7-0.8 | Strong | Review key decisions |
| **0.6-0.7** | **Acceptable (devil's advocate)** | **Verify thoroughly, review concerns** |
| 0.5-0.6 | Needs revision | Rework based on feedback |
| 0.0-0.5 | Low | Likely needs significant rework |

## Testing

Verified threshold logic works correctly:

```
Score: 0.55 -> Verdict: RETRY
Score: 0.59 -> Verdict: RETRY
Score: 0.60 -> Verdict: PASS  ← new threshold
Score: 0.65 -> Verdict: PASS  (devil's advocate)
Score: 0.69 -> Verdict: PASS  (devil's advocate)
Score: 0.70 -> Verdict: PASS
Score: 0.75 -> Verdict: PASS
```

## Impact

### Before (0.7 threshold)
- Valid decompositions with scores 0.60-0.69 → exhausted retries → pipeline blocked
- Users frustrated by overly strict verification
- Many legitimate queries failed to reach phases 5-9

### After (0.6 threshold)
- Valid decompositions with scores 0.60-0.69 → PASS with detailed concerns
- Pipeline proceeds to phases 5-9
- Users receive both the answer AND a list of potential concerns/edge cases
- Better balance between quality and pragmatism

## Related Files

### Modified
- `packages/reasoning/src/aurora_reasoning/verify.py` - Core threshold logic
- `packages/reasoning/src/aurora_reasoning/prompts/verify_adversarial.py` - Adversarial verification prompt
- `packages/reasoning/src/aurora_reasoning/prompts/verify_self.py` - Self-verification prompt
- `packages/reasoning/src/aurora_reasoning/synthesize.py` - Synthesis quality threshold
- `packages/reasoning/examples/sample_queries.md` - Confidence score interpretation table
- `docs/SOAR.md` - Added Phase 4 thresholds and cross-references
- `docs/architecture/SOAR_ARCHITECTURE.md` - Updated Phase 4 verdict logic

### Documentation Structure

**Two-tier documentation:**
1. **`docs/SOAR.md`** (5K) - User-facing guide with high-level 9-phase overview
2. **`docs/architecture/SOAR_ARCHITECTURE.md`** (21K) - Technical specification with detailed implementation

Both now cross-reference each other for easy navigation.

### Additional Reference
- `packages/reasoning/examples/sample_queries.md` - Example queries and scoring guidance

## Next Steps

1. ~~Lower verification threshold from 0.7 to 0.6~~ ✅ DONE
2. Test with real COMPLEX queries to validate pipeline reaches phases 5-9
3. Consider merging agent registries (aurora_soar.agent_registry → aurora_cli.agent_discovery)
4. Suppress "no capabilities defined" agent warnings

## References

- Original issue: Verification exhausting 3 retries on valid decompositions (scores 0.54-0.64)
- Decision: Lower to 0.6 with "devil's advocate" explanation requirements
- Implementation date: 2026-01-08
