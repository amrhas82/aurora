# Replay (HER) Learning: Will It Learn from ACT-R or All Interactions?

**Date**: December 10, 2025
**Question**: "Will Replay HER learn from ACT-R or all interactions?"
**Direct Answer**: **ALL interactions** - every LLM call, success or failure

---

## The Short Answer

**Replay (HER) learns from ALL LLM interactions**, not just the ones successfully ranked by ACT-R.

```
Every LLM Query
    ↓
Generate Output (guided by ACT-R ranking)
    ↓
Execute/Test Output
    ↓
Get Feedback (success, failure, discovery)
    ↓
Store in Replay Buffer ← Happens regardless of outcome
    ↓
Extract Learning (ACT-R update + model fine-tuning)
```

**Key point**: ACT-R's initial ranking is the INPUT to the system, but the learning is based on the OUTCOME, not the ranking quality.

---

## Three Specific Scenarios

### Scenario 1: ACT-R Ranks Correctly, Query Succeeds

```
ACT-R Ranking:
  Agent1 (Caching): 0.92 ← Ranked high
  Agent2 (Consistency): 0.75 ← Ranked medium

LLM Uses: Top-ranked agents (Agent1, Agent2)

Output: Code for distributed cache

Execution: ✅ PASSES TEST

Learning (Replay Buffer Stores):
  ├─ SUCCESS signal
  ├─ Functions used: [func_A, func_B, ...]
  ├─ ACT-R Update: Agent1 += 0.25, Agent2 += 0.25
  └─ Model: Fine-tune on this successful output

Result: ACT-R learned it ranked correctly
```

---

### Scenario 2: ACT-R Ranks Incorrectly, Query Fails

```
ACT-R Ranking:
  Agent1 (Caching): 0.85 ← Ranked high
  Agent2 (DataStructure): 0.60 ← Ranked low

LLM Uses: Top-ranked agents (Agent1, Agent2)

Output: Cache implementation with wrong data structure

Execution: ❌ FAILS TEST

Learning (Replay Buffer Stores):
  ├─ FAILURE signal
  ├─ Functions used: [func_C, func_D, ...]
  ├─ ACT-R Update: Agent1 -= 0.075, Agent2 -= 0.075
  ├─ Tag: "Used wrong data structure"
  └─ Model: Don't train on this failed output

Result: ACT-R learned it ranked wrongly, activations decreased
```

---

### Scenario 3: ACT-R Ranks, Discovery Happens

```
ACT-R Ranking:
  Agent1 (Caching): 0.90 ← High
  Agent2 (Consistency): 0.70 ← Medium

LLM Uses: Top agents + generates new function

Output: "def efficient_cache(): ..."
        + "def helper_utility(): ..." (not in original goal)

Execution: ✅ Helper function becomes useful later

Learning (Replay Buffer - Hindsight Relabel):
  ├─ ORIGINAL LABEL:
  │  └─ Goal: "Efficient cache"
  │  └─ Outcome: "def efficient_cache() + def helper_utility()"
  │  └─ Direct success: +0.25 (for main goal)
  │
  ├─ HINDSIGHT LABEL (NEW):
  │  └─ Goal: "Generate helper_utility()"
  │  └─ Outcome: "def helper_utility()"
  │  └─ Discovery success: +0.15
  │
  └─ ACT-R Update:
     ├─ Agent1: +0.25 (direct success)
     ├─ Agent2: +0.25 (helped with main goal)
     └─ Agents related to helper: +0.15 (spreading activation)

Result: Agents learn helper was valuable, even though not directly queried
```

---

## Key Distinction: Ranking vs Learning

### ACT-R's Role (At Query Time)
```
ACT-R calculates agent activations
  ├─ Uses: BLA (git history)
  ├─ Uses: CB (query relevance)
  ├─ Uses: SA (dependencies)
  └─ Output: Ranked list of agents → guides LLM

Effect: Better initial agent selection
```

### Replay's Role (After Execution)
```
Replay buffer stores outcome
  ├─ Stores: Query, output, execution result
  ├─ Stores: Which agents/functions were used
  ├─ Stores: Whether execution succeeded
  └─ Input: ACT-R's ranking doesn't matter anymore

Updates:
  ├─ ACT-R scores: Based on outcome success/failure
  ├─ Model: Fine-tune on successful patterns
  └─ Learning: Not from ACT-R quality, from OUTCOME quality
```

**Important**: Replay learns from outcomes, not from whether ACT-R ranked correctly.

---

## Learning Mechanism: In Detail

### What Replay (HER) Learns

**At immediate feedback time** (after each query):
```
For each agent in the generated output:
  if outcome == SUCCESS:
    agent.activation += 0.25
  elif outcome == DISCOVERY:
    agent.activation += 0.15  (via hindsight relabel)
  elif outcome == FAILURE:
    agent.activation -= 0.075
```

This happens regardless of ACT-R's ranking. If ACT-R ranked an agent highly but the output failed, that agent gets -0.075 (learning that high ranking was wrong).

**At batch training time** (weekly):
```
Sample replay buffer:
  ├─ Take 1000 random examples
  ├─ Filter for SUCCESS and DISCOVERY signals
  ├─ Fine-tune QLoRA model on these examples
  └─ Model learns: "When this query pattern appears, generate this kind of output"
```

Model fine-tuning is orthogonal to ACT-R. It learns directly from the replay buffer outcomes.

---

## Data Flow: Where Learning Comes From

### All Interactions Are Recorded

```
┌─────────────────────────────────────────┐
│ LLM Query #1 → Attempt 1 → FAILS        │
├─────────────────────────────────────────┤
│ ✅ Stored in Replay Buffer              │
│ ✅ ACT-R scores updated (-0.075)        │
│ ❌ Model NOT fine-tuned on this         │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ LLM Query #2 → Attempt 1 → SUCCESS      │
├─────────────────────────────────────────┤
│ ✅ Stored in Replay Buffer              │
│ ✅ ACT-R scores updated (+0.25)         │
│ ✅ Model fine-tuned on this (weekly)    │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ LLM Query #3 → Attempt 1 → FAILURE      │
│             → Hindsight → DISCOVERY     │
├─────────────────────────────────────────┤
│ ✅ Stored in Replay Buffer (both)       │
│ ✅ ACT-R scores updated (+0.15 HER)     │
│ ✅ Model fine-tuned on this (weekly)    │
└─────────────────────────────────────────┘

All three are analyzed and learned from
```

---

## Why Learning from ALL Interactions Matters

### Example: Learning from Failures

```
Query: "Implement a cache"
LLM Output: "def bad_cache(): ..."
Execution: ❌ FAILS (timeout due to O(n²) complexity)

Without Replay/Learning:
  └─ Next query: Might make same mistake again
  └─ Cost: Wasted generation, wasted time

With Replay (HER) Learning:
  ├─ Store failure: "This agent caused timeout"
  ├─ ACT-R update: Agent activation decreases
  ├─ Tag metadata: "Avoid O(n²) patterns from this agent"
  ├─ Next query: Agent has lower activation, less likely selected
  └─ Result: Pattern learning prevents repetition
```

### Example: Learning from Discovery

```
Query: "Design auth system"
LLM Output: "def authenticate(): ..." + "def token_cache(): ..."
Execution: ✅ Auth works, token_cache becomes reusable utility

Without HER:
  └─ Learn: "Authentication is important"
  └─ Forget: "token_cache was discovered"

With HER (Hindsight Experience Replay):
  ├─ Store original: "Generated auth, +0.25"
  ├─ Hindsight relabel: "Generated token_cache, +0.15"
  ├─ Both agents boosted (discovery learning)
  ├─ Next time similar query appears: Both more likely
  └─ Result: Discovery pattern remembered and reused
```

---

## The Interplay: ACT-R + Replay (HER)

### How They Work Together

```
Query 1: Initial ranking
  ├─ ACT-R scores agents (based on git history)
  ├─ LLM uses top agents
  ├─ Output: Succeeds
  ├─ Replay: Stores success
  └─ ACT-R: Updates activations up (+0.25)

Query 2: Improved ranking
  ├─ ACT-R scores agents (now with updated history)
  ├─ Previously successful agents ranked higher
  ├─ LLM uses these again
  ├─ Output: More likely to succeed
  ├─ Replay: Stores success
  └─ ACT-R: Updates activations up again (+0.25)

Query 3+: Positive feedback loop
  ├─ System learns which agents work
  ├─ Rankings improve continuously
  ├─ Model also improves (from fine-tuning on successes)
  ├─ Combined: +2-5% improvement per session
  └─ Result: 85% → 90%+ accuracy over time
```

### The Feedback Loop

```
├─ ACT-R provides initial guidance (from git + learning)
├─ Replay (HER) observes outcomes
├─ Learning updates ACT-R scores
├─ Better ACT-R scores → Better LLM guidance
├─ Better LLM outputs → Better outcomes
├─ Better outcomes → Better learning
└─ Loop repeats, system improves
```

---

## Answer to Your Question (Restated)

**"Will Replay HER learn from ACT-R or all interactions?"**

**Answer**: Replay (HER) learns from **ALL interactions**.

### What this means:

| Type | Learned? | Signal | Impact |
|------|----------|--------|--------|
| **Success** (ACT-R ranked well) | ✅ Yes | +0.25 to agents | Positive reinforcement |
| **Failure** (ACT-R ranked poorly) | ✅ Yes | -0.075 to agents | Negative learning |
| **Discovery** (ACT-R was partial) | ✅ Yes | +0.15 hindsight | Pattern discovery |
| **Edge cases** (Unexpected) | ✅ Yes | Logged + analyzed | New pattern learning |

### ACT-R's Role:
- Provides initial ranking (which agents to activate)
- Gets updated by learning from outcomes
- Not a filter (failures still get stored and learned from)

### Replay's Role:
- Stores every LLM call outcome
- Extracts learning signals (success, failure, discovery)
- Trains both ACT-R updates AND model fine-tuning
- Enables negative learning (learn what NOT to do)

---

## Comparison: Replay (HER) vs. Alternatives

### Alternative 1: Learn Only From Successes
```
Limitation: 30% of queries fail or partially work
Cost: Lose learning from 70% of attempts
Result: Slow learning, 1% improvement per session
```

### Alternative 2: Learn from ACT-R Prediction Only
```
Limitation: Only learn if ACT-R ranking matches outcome
Cost: Lose learning when ACT-R is wrong (exactly when we need it)
Result: Can't learn from failures, can't improve poor rankings
```

### Replay (HER) Solution
```
Advantage: Learn from ALL outcomes (100% of attempts)
  ├─ Success: Direct learning
  ├─ Failure: Negative learning
  └─ Discovery: Hindsight learning

Result: +2-5% improvement per session, comprehensive learning
```

---

## Practical Implementation

### What Gets Stored in Replay Buffer

**Every LLM call stores**:
```python
replay_entry = {
    "query": user_query,
    "outcome_code": generated_code,
    "execution_result": "success" | "failure",
    "agents_used": [agent1, agent2, ...],
    "functions_generated": [func_a, func_b, ...],
    "test_passed": boolean,
    "error_message": str | None,
    "execution_time": float,
    "quality_score": float,
    "timestamp": datetime,
}
```

**Learning happens from**:
```
For each entry in replay_buffer:
  if entry.execution_result == "success":
    for agent in entry.agents_used:
      agent.activation += 0.25
  elif entry.execution_result == "failure":
    for agent in entry.agents_used:
      agent.activation -= 0.075
  elif hindsight_relabel_applies(entry):
    # Apply discovery learning
    agent.activation += 0.15
```

---

## Summary

| Question | Answer |
|----------|--------|
| **Does Replay learn from ACT-R?** | No, Replay learns from LLM OUTCOMES |
| **Does Replay learn from all interactions?** | Yes, success + failure + discovery |
| **How does ACT-R benefit?** | From Replay's updated scores, which improve over time |
| **Can Replay learn from failures?** | Yes, explicit negative learning (-0.075) |
| **Can Replay learn from unexpected outcomes?** | Yes, via hindsight relabeling (HER) |
| **Is ACT-R wasted if it ranks wrong?** | No, system learns the ranking was wrong (negative signal) |
| **What prevents learning loops?** | Hindsight relabeling + outcome-based signals |

---

**Status**: Fully clarified
**Referenced in**: PRD Section 12, AURORA-Refined-Architecture.md
**File**: This document (REPLAY-HER-LEARNING-EXPLAINED.md)
