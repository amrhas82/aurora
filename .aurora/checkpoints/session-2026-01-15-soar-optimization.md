# Session Checkpoint: SOAR Optimization

**Timestamp:** 2026-01-15
**Branch:** aur-soar-optim

---

## Session Summary

Fixed `aur goals` TypeError (used `any` instead of `Any` in agents.py), then rewrote README.md and created docs/guides/FLOWS.md. Now investigating two SOAR performance issues.

---

## Completed Work

1. **Bug Fix:** `packages/cli/src/aurora_cli/planning/agents.py:371,374`
   - Changed `any | None` to `Any | None` (was using built-in function instead of type)

2. **README Simplification:** Rewrote README.md (~300 lines)
   - Value proposition upfront
   - Visual workflow diagrams
   - Agent gap detection examples
   - Design philosophy section

3. **Created docs/guides/FLOWS.md**
   - Optimum plan flow: `aur goals` -> `/aur:plan` -> `/aur:implement`
   - Regular plan flow: `/aur:plan` -> `/aur:implement`
   - Research flow: `aur soar`
   - Execution flow: `aur spawn`
   - Memory search flow: `/aur:search` -> `/aur:get`
   - Decision tree for flow selection

---

## Active Investigation: SOAR Performance Issues

### Problem 1: Smart Recovery Slowdown

**Symptom:** `aur soar` is slow, more failures than successes since smart recovery added.

**Root Cause Found:**
- `collect.py:execute_agents()` processes agents **sequentially** (line 236 loop)
- Each agent goes through `spawn_with_retry_and_fallback` with:
  - 300s timeout per attempt
  - max_retries=2 (so 3 attempts total)
  - fallback_to_llm=True (adds 4th attempt)
- **Worst case:** 5 agents × 3 attempts × 300s = 75 minutes

**Proposed Solution:**
- True parallel execution with global timeout (120s for all agents)
- No retries - fail fast, synthesize from partial results
- Remove `spawn_with_retry_and_fallback`, use direct `spawn()` calls

### Problem 2: Binary Gap Detection

**Symptom:** System reports gaps and spawns ad-hoc agents even when existing agents can do the work.

**Root Cause Found:**
- In `verify.py:85-100`: if `ideal_agent != assigned_agent`, creates placeholder with `is_spawn=True`
- LLM generates `ideal_agent` names like `@creative-writer` that never match manifest
- **Every subgoal becomes a gap → every task triggers ad-hoc spawning**

**Proposed Solution:**
- Remove `ideal_agent` concept entirely
- Gap only when `assigned_agent` is None or `@unknown`
- Use whatever agent was assigned - no dreaming of ideal agents

---

## Key Files for Implementation

**Problem 1 (Recovery):**
- `packages/soar/src/aurora_soar/phases/collect.py` - sequential loop at line 236
- `packages/spawner/src/aurora_spawner/spawner.py` - `spawn_with_retry_and_fallback()`
- `packages/soar/src/aurora_soar/orchestrator.py:700-710` - calls execute_agents

**Problem 2 (Gaps):**
- `packages/soar/src/aurora_soar/phases/verify.py:85-100` - ideal_agent check
- `packages/cli/src/aurora_cli/planning/agents.py` - AgentMatcher.match_subgoal()
- `packages/cli/src/aurora_cli/planning/decompose.py` - generates ideal_agent field

---

## User Context

- User rejected confidence-based scoring (LLMs bad at self-assessment)
- User rejected retry-based recovery (already implemented, causing slowdowns)
- Novel solutions needed, not circular suggestions
- Goal: simplify, use less code

---

## Next Steps

1. Implement parallel execution in collect.py with global timeout
2. Remove ideal_agent from verify.py gap detection
3. Test with `aur soar` query
