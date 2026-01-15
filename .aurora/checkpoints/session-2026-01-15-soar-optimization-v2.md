# Session Checkpoint: SOAR Optimization v2

**Timestamp:** 2026-01-15
**Branch:** aur-soar-optim

---

## Session Summary

Investigated two SOAR performance issues. Found root causes and designed minimal solutions that reuse existing code.

---

## Completed Earlier

1. **Bug Fix:** `agents.py:371,374` - `any` -> `Any`
2. **README.md** - Simplified, value proposition upfront
3. **docs/guides/FLOWS.md** - Created with all workflow patterns

---

## Problem 1: Sequential Execution Slowdown

**Root Cause:**
- `collect.py:execute_agents()` processes agents sequentially (line 236 loop)
- Each agent: 300s timeout × 3 attempts via `spawn_with_retry_and_fallback()`
- 5 failing agents = 75 minutes worst case

**Solution: Reuse spawn_parallel()**
```python
# Replace sequential loop in collect.py with:
from aurora_spawner import spawn_parallel

async def execute_agents_parallel(tasks, global_timeout=120):
    try:
        results = await asyncio.wait_for(
            spawn_parallel(tasks, max_concurrent=5),
            timeout=global_timeout
        )
    except asyncio.TimeoutError:
        # Return partial results
    return results
```

**Progress streaming:** Simple counter "[3/5 done]" - SOAR synthesizes at end anyway

**LOC change:** ~30 lines

---

## Problem 2: Binary Gap Detection

**Root Cause:**
- `verify.py:85-100` compares `ideal_agent != assigned_agent` as strings
- LLM invents agent names like `@creative-writer` that never exist
- Every subgoal becomes gap → every task spawns ad-hoc

**Solution: Use existing AgentRecommender**

`AgentRecommender` in `agents.py` already has keyword matching. verify.py bypasses it.

```python
# In verify.py, replace string comparison with:
from aurora_cli.planning.agents import AgentRecommender

recommender = AgentRecommender(manifest)
best_agent, score = recommender.recommend_for_description(ideal_agent_desc)

if score < 0.15:  # True gap
    # Create spawn placeholder
else:
    # Use best_agent, no gap
```

**LOC change:** ~15 lines

---

## Key Files

**Problem 1:**
- `packages/soar/src/aurora_soar/phases/collect.py` - line 236 sequential loop
- `packages/spawner/src/aurora_spawner/spawner.py` - `spawn_parallel()` to reuse

**Problem 2:**
- `packages/soar/src/aurora_soar/phases/verify.py:85-100` - string comparison to remove
- `packages/cli/src/aurora_cli/planning/agents.py` - AgentRecommender to reuse

---

## User Constraints

- No confidence scoring from LLM (unreliable)
- No more retry logic (already causing slowdowns)
- Goal: simplify, less LOC, reuse existing code
- Novel solutions, not circular suggestions

---

## Decision: Simple Word Matching Alternative

If AgentRecommender doesn't have `recommend_for_description()`:

```python
def match_agent(ideal_desc: str, agents: list) -> tuple[str, float]:
    """Jaccard similarity on tokenized descriptions."""
    ideal_tokens = set(ideal_desc.lower().split()) - STOP_WORDS

    best_agent, best_score = None, 0.0
    for agent in agents:
        agent_text = f"{agent.id} {agent.description} {' '.join(agent.capabilities)}"
        agent_tokens = set(agent_text.lower().split()) - STOP_WORDS
        score = len(ideal_tokens & agent_tokens) / len(ideal_tokens | agent_tokens)
        if score > best_score:
            best_score, best_agent = score, agent

    return best_agent, best_score
```

~25 lines, no dependencies, uses existing STOP_WORDS.

---

## Next Steps

1. Check if AgentRecommender has description-based matching
2. If not, add simple Jaccard matching (~25 lines)
3. Modify verify.py to use recommender instead of string compare
4. Replace sequential loop in collect.py with spawn_parallel()
5. Test with `aur soar` query

---

## Total Estimated Changes

| Problem | Solution | LOC |
|---------|----------|-----|
| 1. Parallel | Reuse `spawn_parallel()` | ~30 |
| 2. Matching | Reuse `AgentRecommender` | ~15 |
| **Total** | | **~45** |
