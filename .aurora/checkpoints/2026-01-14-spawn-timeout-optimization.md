# Checkpoint: Spawn Timeout Optimization

**Date**: 2026-01-14
**Branch**: aur-soar-optim

## Context

Working on optimizing SOAR pipeline, specifically agent spawning reliability.

## Completed Work

### 1. Fixed SOAR Retrieve Phase
- **File**: `packages/soar/src/aurora_soar/phases/retrieve.py`
- **Change**: Switched from `store.retrieve_by_activation()` (broken - 0 results due to negative ACT-R decay) to `MemoryRetriever` with `HybridRetriever` (BM25 30% + semantic 40% + activation 30%)
- **Result**: Now retrieves chunks correctly (tested: 3 chunks matched)

### 2. Increased Default Timeout (needs revisit)
- **Files changed**:
  - `packages/cli/src/aurora_cli/policies/models.py:53` - RecoveryConfig default 120→300
  - `packages/soar/src/aurora_soar/orchestrator.py:640` - Fallback default 120→300
- **Issue**: User questioned if timeout increase is right approach

## Active Discussion: Early Failure Detection

**Problem**: Timeout is passive waiting. With 300s × 3 retries × 7 agents = 105 min worst case.

**Why agents fail**:
1. API issues (rate limits, connection errors)
2. Task ambiguity
3. Claude CLI hangs
4. Model overload

**Options presented**:

| Option | Description |
|--------|-------------|
| Output streaming | Read stdout async, no output = stuck |
| Error pattern matching | Parse stderr, kill on "Error:" |
| Circuit breaker | Track failures, skip known-bad agents |
| Pre-flight health check | Quick health check before spawn |
| Progressive timeout | 30s initial, extend if activity |
| Two-phase ack | Expect quick ack, then work |

**Recommendations**:
- **Option A**: Error pattern + progressive timeout
- **Option B**: Circuit breaker + pre-flight

## Pending Decision

User needs to choose direction for early failure detection strategy.

## Related Plans

- `.aurora/plans/active/0008-unify-goals-soar-pipeline/` - Unify goals and SOAR
- `.aurora/plans/active/0006-enhance-spawn-multiturn-statefulness/` - Spawn enhancement

## Key Files

- `packages/soar/src/aurora_soar/phases/retrieve.py` - Retrieve phase (fixed)
- `packages/soar/src/aurora_soar/phases/collect.py` - Agent execution
- `packages/spawner/src/aurora_spawner/spawner.py` - Core spawn logic
- `packages/cli/src/aurora_cli/policies/models.py` - RecoveryConfig

## Commands to Resume

```bash
# Test current state
aur soar "test query" -t claude -v

# Check retrieve phase
python -c "from aurora_soar.phases.retrieve import retrieve_context; print('ok')"
```
