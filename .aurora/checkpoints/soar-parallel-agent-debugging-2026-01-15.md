# Checkpoint: SOAR Parallel Agent Debugging

**Created**: 2026-01-15
**Branch**: aur-soar-optim

## Current State

### Root Cause Identified
**Model ID is invalid**: `eu.anthropic.claude-opus-4-5-20251101-v1:0` returns 400 error
- Agents spawn correctly with stagger (10s between each)
- Claude CLI fails immediately with API error
- Error goes to stderr, not captured/surfaced properly
- Health monitor only checks stdout → times out after 120s

### Key Finding
```bash
claude -p "hello"
# API Error (eu.anthropic.claude-opus-4-5-20251101-v1:0): 400 The provided model identifier is invalid
```

## Changes Made This Session

### Working Changes (Keep)
1. **Stagger delay** - 10s between agent starts (collect.py:357-365)
2. **Progress display** - Shows "Agent X/Y starting in Ns..." messages
3. **Skip circuit breaker for adhoc agents** (collect.py:256)
4. **Progress instructions in adhoc prompts** (agents.py:269)
5. **Cleaner warnings** - Debug level for repeated messages
6. **Spinner** during agent execution (collect.py:501-513)

### Reverted
- `spawn_with_retry_and_fallback()` → back to `spawn()` (wasn't the issue)

### Timeout Architecture Documented
- SpawnPolicy: Primary timeout control
- ProactiveHealthConfig: `terminate_on_failure=False`
- EarlyDetectionConfig: `terminate_on_stall=False`, `stall_threshold=120s`

## Files Modified
- `packages/soar/src/aurora_soar/phases/collect.py` - stagger, spinner, circuit breaker skip
- `packages/cli/src/aurora_cli/planning/agents.py` - progress instructions
- `packages/spawner/src/aurora_spawner/observability.py` - warning levels, termination control
- `packages/spawner/src/aurora_spawner/early_detection.py` - warning levels, terminate_on_stall
- `docs/development/SPAWN_TESTING_GUIDE.md` - timeout architecture docs

## Next Steps

### Immediate
1. **Fix model ID resolution** - Why EU model when AWS_REGION=us-east-1?
2. **Capture stderr errors** - Fail fast on API errors instead of waiting 120s

### Research Findings
Google ADK ParallelAgent pattern:
- Context isolation with distinct branch paths
- Shared state with distinct keys (avoid race conditions)
- `escalate=True` flag for error bubbling
- Fan-Out/Gather pattern

## Questions to Resolve
1. Where is model ID being resolved? Check spawn() and CLI config
2. Why isn't stderr being surfaced in progress/errors?
3. Should we implement ADK-style error escalation?

## Test Commands
```bash
# Simple test (bypasses agents)
aur soar "what is 2+2?" -t claude

# Complex test (spawns agents)
aur soar "explain SOAR architecture" -t claude

# Manual CLI test
claude -p "hello"
```
