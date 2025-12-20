# How SOAR/ACT-R Maintain Memory and Track Success Without Neural Weights
## Symbolic Knowledge Representation and Persistent Learning

**Date**: December 5, 2025
**Question**: How do SOAR and ACT-R maintain memory, track success, and improve over time without neural network weights?

**Answer**: Symbolic databases and explicit success tracking—completely different from neural networks.

---

## The Core Difference: Weights vs. Symbols

### Neural Networks (LLMs)

```
What gets stored: Billions of parameters/weights
├─ Weight for connection A→B: 0.0742
├─ Weight for connection C→D: -0.1283
├─ Bias: 0.0042
└─ ... 7 billion times

How learning works:
  New data → Backpropagation → Adjust weights
  Knowledge is encoded in weight distributions
  Can't ask "why did you do that?" (black box)
  Can't move weights to another model easily
```

### SOAR/ACT-R (Symbolic)

```
What gets stored: Explicit rules and facts
├─ Rule: "IF debugging AND database_query THEN check_if_empty"
├─ Fact: "Paris is capital of France"
├─ Utility: "check_query has 0.82 success rate"
├─ Memory: "Yesterday I solved problem X with approach Y"
└─ ... hundreds or thousands of rules/facts

How learning works:
  Successful problem → Extract to rule
  Rule applied → Track success
  Track success → Adjust utility score
  Knowledge is explicit and interpretable
  Can ask "why?" and get clear answer
  Can easily move rules to another system
```

---

## Part 1: Memory in SOAR

### 1. Working Memory (Current State)

**Job**: Hold what's happening right now

**Storage**: JSON-like data structure (in RAM)

```
{
  "state_type": "debugging",
  "problem": "getUserById(42) returns null",
  "goal": "find_root_cause",
  "context": {
    "function_name": "getUserById",
    "database_connected": true,
    "test_data_verified": true
  },
  "operators_tried": [
    "check_function_logic",
    "test_with_sample_data"
  ],
  "current_hypothesis": "query_returns_empty",
  "time_since_start": "5 minutes"
}
```

**Persistence**: Lives in memory (RAM) during execution
**Updates**: Every SOAR cycle (when state changes)
**Clears**: When problem solved or session ends

---

### 2. Long-Term Memory: Production Rules

**Job**: Store IF-THEN rules learned from experience

**Storage**: Database (JSON file, SQL, or structured storage)

```json
{
  "rule_id": 1,
  "name": "database_null_debugging",
  "condition": {
    "state_type": "debugging",
    "goal": "find_root_cause",
    "error_type": "null_return",
    "context_pattern": "database_related"
  },
  "action": {
    "propose_operator": "check_database_query"
  },
  "created": "2025-12-01",
  "first_success": "2025-12-01",
  "total_uses": 47,
  "successful_uses": 38,
  "failed_uses": 9,
  "utility": 0.81
}
```

**Persistence**: Written to disk (survives session end)
**How rules are created**: Captured from successful problem-solving traces
**How rules are used**: Queried when state matches conditions
**How they improve**: Utility updates accumulate over time

#### Rule Creation Example

```
Problem-solving trace:
  Initial state: {error: null_return, context: database}
    ↓ [Try operator: check_database_query]
  New state: {query_status: empty_result}
    ↓ [Try operator: check_test_data]
  Final state: {root_cause: no_test_data}
    ↓ SUCCESS

Rule extraction:
  Create rule: "IF error is null_return AND context is database
               THEN check_database_query"

Store in rule memory:
  {
    "condition": {error: null_return, context: database},
    "action": check_database_query,
    "first_success": now,
    "uses": 1,
    "successful_uses": 1,
    "utility": 1.0
  }
```

#### Rule Querying Example

```
Current state:
  {error: null_return, context: database, goal: debugging}

Query rules:
  For each rule in memory:
    if rule.condition MATCHES current_state:
      add rule.action to operators

Matching rules:
  ✓ Rule 1: {error, context} matches → add "check_database_query"
  ✓ Rule 12: {error, goal} matches → add "trace_execution"
  ✗ Rule 5: {file_error, context} doesn't match

Proposed operators: [check_database_query, trace_execution, ...]
```

---

### 3. Long-Term Memory: Semantic Knowledge

**Job**: Store facts about the domain

**Storage**: Semantic database

```json
[
  {
    "fact": "Null returns are often caused by empty database queries",
    "reliability": 0.85,
    "learned_from": ["problem_1", "problem_5", "problem_12"],
    "context": "database_debugging"
  },
  {
    "fact": "Test data must be created before query tests",
    "reliability": 0.95,
    "learned_from": ["problem_3", "problem_7"],
    "context": "database_debugging"
  },
  {
    "fact": "Paris is the capital of France",
    "reliability": 1.0,
    "source": "initial_knowledge",
    "context": "geography"
  }
]
```

**Persistence**: Written to disk
**Used for**: Evaluating operators ("is this operator likely to help?")
**Learning**: Extracted from successful problem-solving

---

### 4. Utility Scores: The Success Tracking System

**Job**: Remember how often each operator succeeded

**Storage**: Simple table/dictionary

```
Operator Success Rates:

check_database_query:
  ├─ Total uses: 47
  ├─ Successful: 38
  ├─ Failed: 9
  ├─ Success rate: 38/47 = 0.81
  ├─ Last used: 2025-12-05 15:33
  └─ Utility score: 0.81

test_with_sample_data:
  ├─ Total uses: 23
  ├─ Successful: 16
  ├─ Failed: 7
  ├─ Success rate: 16/23 = 0.70
  ├─ Last used: 2025-12-04 10:15
  └─ Utility score: 0.70

add_debug_logging:
  ├─ Total uses: 5
  ├─ Successful: 2
  ├─ Failed: 3
  ├─ Success rate: 2/5 = 0.40
  ├─ Last used: 2025-12-03 09:22
  └─ Utility score: 0.40
```

**Persistence**: Stored with rules (JSON/SQL)
**Updates**: Incremented when operator used
- If success: `successes += 1`
- If failure: `failures += 1`
- Utility recalculated: `success_count / (success_count + failure_count)`

#### How Utilities Drive Decisions

```
Operator evaluation:

check_database_query:
  Predicted score (will it help?): 0.85
  Historical utility: 0.81
  Combined: 0.85 × 0.81 = 0.69

test_with_sample_data:
  Predicted score: 0.65
  Historical utility: 0.70
  Combined: 0.65 × 0.70 = 0.46

check_function_logic:
  Predicted score: 0.50
  Historical utility: 0.55
  Combined: 0.50 × 0.55 = 0.28

Ranking: [0.69, 0.46, 0.28]
Decision: Use check_database_query (highest score)
```

---

### SOAR Memory Summary

```
SOAR Memory Architecture:

┌──────────────────────────────────────┐
│ WORKING MEMORY (RAM)                 │
│ Current state, operators tried       │
│ Lives in RAM, updates every cycle    │
└──────────────────────────────────────┘
           ↓ (references)
┌──────────────────────────────────────┐
│ LONG-TERM MEMORY (Disk/Database)     │
│                                      │
│ 1. Production Rules                  │
│    IF state THEN operator           │
│    {condition, action, utility}     │
│                                      │
│ 2. Semantic Knowledge                │
│    Facts about domain               │
│    {fact, reliability, context}     │
│                                      │
│ 3. Utilities/Preferences             │
│    Success rates of operators       │
│    {operator, uses, successes}      │
│                                      │
│ 4. Episodes/Traces                   │
│    "Yesterday I solved problem X"   │
│    {problem, approach, outcome}     │
│                                      │
└──────────────────────────────────────┘
           ↑ (learns from)
┌──────────────────────────────────────┐
│ LEARNING MECHANISM                   │
│ Extract rules from successful traces │
│ Update utilities from successes/failures
│ Consolidate into long-term memory   │
└──────────────────────────────────────┘
```

---

## Part 2: Memory in ACT-R

### 1. Declarative Memory (Facts/Knowledge)

**Job**: Store facts and concepts

**Storage**: Memory chunks with activation values

```json
{
  "chunk": {
    "type": "geography_fact",
    "fact": "Paris is capital of France",
    "creation_time": "2025-12-01 10:00",
    "last_accessed": "2025-12-05 15:33",
    "access_count": 127
  },
  "activation": {
    "base_level": 0.75,
    "recent_use_boost": 0.15,
    "spreading_activation": 0.08,
    "total_activation": 0.98
  }
},
{
  "chunk": {
    "type": "debugging_strategy",
    "strategy": "For database nulls, check if query returns empty",
    "creation_time": "2025-12-03 14:20",
    "last_accessed": "2025-12-05 14:55",
    "access_count": 23
  },
  "activation": {
    "base_level": 0.65,
    "recent_use_boost": 0.18,
    "spreading_activation": 0.12,
    "total_activation": 0.95
  }
}
```

**Persistence**: Chunks stored in declarative memory (disk)
**Activation**: Calculated dynamically based on usage

#### Activation Calculation

```
Total activation = Base level + Recent use boost + Spreading activation

Base level:
  How reliable is this memory?
  ├─ Used 100 times, failed 0: base = 1.0
  ├─ Used 50 times, failed 5: base = 0.90
  └─ Used 5 times, failed 4: base = 0.20

Recent use boost:
  How recently was it used?
  ├─ Used 1 minute ago: +0.20
  ├─ Used 1 hour ago: +0.10
  ├─ Used 1 day ago: +0.02
  └─ Used 1 month ago: 0

Spreading activation:
  Related memories activate each other
  ├─ "Paris" activates "France"
  ├─ "France" activates "capital"
  └─ Activation spreads between related chunks

Total: 0.65 + 0.18 + 0.12 = 0.95 (very retrievable)
```

---

### 2. Procedural Memory (How-To Rules)

**Job**: Store how to do things (rules)

**Storage**: Production rules with utilities

```json
{
  "rule_id": "debug_database_null",
  "rule": "IF goal is find_root_cause AND problem is null_return AND context is database THEN check_database_query",
  "success_record": {
    "successes": 38,
    "failures": 9,
    "total_uses": 47
  },
  "utility": {
    "base_utility": 0.81,
    "recent_boost": 0.05,
    "total_utility": 0.86
  },
  "cost": 0.1,
  "learning_history": [
    {"date": "2025-12-01", "outcome": "success", "reward": 1.0},
    {"date": "2025-12-02", "outcome": "success", "reward": 1.0},
    {"date": "2025-12-02", "outcome": "failure", "reward": -0.5},
    {"date": "2025-12-03", "outcome": "success", "reward": 1.0}
  ]
}
```

**Persistence**: Rules stored on disk
**Utilities**: Updated after each use

---

### 3. Activation Decay (Natural Forgetting)

**Key mechanism**: Memory automatically weakens if unused

```
Memory activation over time:

Strong (0.9) ┤                    /‾‾
             │                  /
             │                /
             │              /
             │            /
Medium (0.5) ├──────────/────────────
             │        /
             │      /
             │    /
Weak (0.1)   │  /
             │/________
             └──────────────────→ Time

Usage pattern:
  Day 1: Access → activation boost (0.9)
  Day 2: No use → decays (0.8)
  Day 3: No use → decays (0.7)
  Day 7: No use → decays (0.4)
  Day 30: No use → very weak (0.1)
  Day 30 + 1 access: Boost back up to 0.8

Mathematical model:
  Activation(t) = Base_level + Recent_boost(t)

  Recent_boost(t) = Sum of [time_weight × recency_bonus]

  time_weight = 1 / (t - last_access + 1)^0.5
```

#### Why Activation Decay Matters

```
Scenario: Learned a debugging technique last year

Without activation decay (neural network):
  Weights permanently stored
  System equally confident in old and new learning
  Accumulates all past knowledge equally
  Problem: Old knowledge might be obsolete

With activation decay (ACT-R):
  Old technique weakens if not used
  Recent techniques stronger
  Naturally weights recent learning
  Benefit: System adapts to changing problems

Example:
  Learned "Use X debugging approach": activation 0.9
  Haven't used it 6 months: activation drops to 0.3
  Recently discovered "Use Y approach works better": activation 0.95
  System naturally prefers Y (higher activation)
  No need to manually update—natural forgetting does it
```

---

## Part 3: Tracking Success (The Learning Signal)

### How SOAR Tracks Success

#### 1. Outcome Observation

```
After executing operator:

Before: state = {problem: null_return, ...}
Operator: check_database_query
Execute: db.query(42) → Result: empty

After: state = {problem: null_return, result: empty}

Question: Did we make progress?
  ├─ Were we closer to goal? YES
  ├─ Did we advance understanding? YES
  ├─ New information discovered? YES
  └─ SUCCESS SIGNAL: +1
```

#### 2. Rule Utility Update

```
Original utility:
  check_database_query:
    Successful uses: 38
    Failed uses: 9
    Utility: 38/47 = 0.81

After this success:
  Successful uses: 38 + 1 = 39
  Failed uses: 9 (unchanged)
  New utility: 39/48 = 0.8125

Change: +0.0025 improvement
```

#### 3. Accumulation Over Time

```
As more problems are solved:

Day 1: 10 successes → utility 0.70
Day 2: 12 successes (2 new) → utility 0.71
Day 3: 15 successes (3 new) → utility 0.72
Day 4: 21 successes (6 new) → utility 0.74
Day 5: 25 successes (4 new) → utility 0.76

Month 2: 150 successes → utility 0.89
Month 3: 200 successes → utility 0.92
Month 4: 250 successes → utility 0.94

Observation: Slow but steady improvement through accumulation
```

---

### How ACT-R Tracks Success

#### 1. Utility Update Formula

```
Utility = (Successes × Reward) - (Failures × Penalty) - Cost

Initial:
  Successes: 38
  Failures: 9
  Reward per success: 1.0
  Penalty per failure: 0.5
  Cost: 0.1

  Utility = (38 × 1.0) - (9 × 0.5) - 0.1 = 38 - 4.5 - 0.1 = 33.4

After one success:
  Successes: 39
  Failures: 9

  Utility = (39 × 1.0) - (9 × 0.5) - 0.1 = 39 - 4.5 - 0.1 = 34.4

Change: +1.0 (significant boost for success)
```

#### 2. Competitive Selection

```
When multiple rules could apply:

Rule A: Utility = 34.4 ← Winner (highest)
Rule B: Utility = 25.8
Rule C: Utility = 18.5
Rule D: Utility = 10.2

Decision: Use Rule A

If Rule A succeeds:
  Next time: Utility = 35.4 (even stronger)
  Will win even more consistently

If Rule B succeeds:
  Next time: Utility = 26.8
  Still won't beat Rule A (35.4 > 26.8)

Result: System learns which rules work best through competition
```

---

### Tracking Success: Key Differences from Neural Networks

#### Neural Networks (LLMs)

```
How learning works:
  Gradient descent
  ├─ Loss function computed
  ├─ Backpropagation through network
  ├─ Each weight adjusted slightly
  └─ Requires thousands of examples to show improvement

Tracking:
  ├─ Loss metric
  ├─ Accuracy percentage
  └─ Cannot ask "why this weight changed?"
```

#### SOAR/ACT-R (Symbolic)

```
How learning works:
  Counter increment
  ├─ Success event occurs
  ├─ Counter: successes += 1
  ├─ Utility recalculated: successes / (successes + failures)
  └─ Improvement visible immediately (next decision)

Tracking:
  ├─ Success count
  ├─ Failure count
  ├─ Utility score
  └─ Can ask "why? Because rule X succeeded Y times"
```

---

## Part 4: Persistence Across Sessions

### SOAR Persistence

```
Session 1 (Day 1):
  ├─ Load rule database from disk
  ├─ Solve 10 problems
  │  ├─ Learn 3 new rules
  │  └─ Update utilities 10 times
  ├─ Save updated rule database to disk
  └─ Close session

Session 2 (Day 2):
  ├─ Load rule database from disk (includes Day 1 learning)
  ├─ Utilities reflect Day 1 successes
  ├─ Solve 15 problems (faster than Day 1)
  │  ├─ Learn 2 new rules
  │  └─ Update utilities 15 times
  ├─ Save updated rule database
  └─ Close session

Session 100 (Month 4):
  ├─ Load rule database from disk
  ├─ Now has 300+ rules learned over months
  ├─ Utilities optimized through thousands of applications
  ├─ Solve problems with high accuracy
  ├─ Save updated database
  └─ Close session

Key insight: Knowledge accumulates across all sessions
```

### Storage Format Example

```json
// rules.json (persisted to disk)
{
  "metadata": {
    "created": "2025-12-01",
    "last_updated": "2025-12-05 16:45",
    "total_rules": 347,
    "total_sessions": 23
  },
  "rules": [
    {
      "id": 1,
      "name": "database_null_debugging",
      "condition": {...},
      "action": "check_database_query",
      "utility": 0.823,
      "uses": {
        "total": 127,
        "successful": 104,
        "failed": 23
      },
      "learning_history": [
        {"session": 1, "uses": 3, "successes": 3},
        {"session": 2, "uses": 5, "successes": 4},
        {"session": 3, "uses": 8, "successes": 7},
        ...
        {"session": 23, "uses": 12, "successes": 10}
      ]
    },
    ...
  ]
}
```

---

## Part 5: Portability Across Systems

### Why SOAR/ACT-R Rules Are Portable

```
SOAR Rules are symbolic:
{
  "condition": {"error": "null_return", "context": "database"},
  "action": "check_database_query",
  "utility": 0.82
}

Why portable:
  ✓ Human-readable
  ✓ Self-contained (no dependencies on specific weights)
  ✓ Can be implemented in any language
  ✓ Can be moved to any reasoning engine
  ✓ Can be adapted for similar problems

Example portability:
  System A (Python + SOAR):
    rule = load_json("rules.json")

  System B (JavaScript + React):
    const rule = loadJSON("rules.json")

  System C (Rust + optimized):
    let rule = load_rules("rules.json")

  All can use the same rule!
```

### Neural Network Weights Are NOT Portable

```
Neural weights are coupled:
  Model architecture: Specific layer count, dimensions
  Learning rate: How quickly model was trained
  Initialization: How weights were initially set
  Dataset: What data was trained on

Why NOT portable:
  ✗ Can't just move weights to different model
  ✗ Weights depend on specific layer configuration
  ✗ Moving to different LLM ≠ same behavior
  ✗ Must retrain from scratch for new system

This is why WS1 (Portability) favors SOAR/symbolic approach!
```

---

## Part 6: Comparison Table

### Memory Storage

| Aspect | SOAR | ACT-R | Neural Network |
|--------|------|-------|---|
| **What stores knowledge** | Rules + facts | Chunks + rules | Weights |
| **Storage format** | JSON/Database | JSON/Database | Binary/HDF5 |
| **Size** | Compact (rules) | Compact (chunks) | Huge (billions of params) |
| **Interpretable** | YES (read rules) | YES (read chunks) | NO (black box) |
| **Portable** | YES (move JSON) | YES (move JSON) | NO (model-specific) |

### Success Tracking

| Aspect | SOAR | ACT-R | Neural Network |
|--------|------|-------|---|
| **Tracks** | Counts (success/fail) | Counts (success/fail) | Loss metric |
| **Updates** | Immediate | Immediate | After batch training |
| **Granularity** | Per rule | Per rule | Across all weights |
| **Improvement visible** | Next decision | Next decision | After hundreds of examples |
| **Explainable** | YES ("rule succeeded 10x") | YES ("utility is 0.82") | NO (weights opaque) |

### Learning Speed

| Aspect | SOAR | ACT-R | Neural Network |
|--------|------|-------|---|
| **Learn from 1 example** | YES | YES | NO (needs batch) |
| **Show improvement immediately** | YES | YES | NO (need thousands) |
| **Transparent learning** | YES | YES | NO |
| **Continuous learning** | YES (no catastrophic forgetting) | YES (activation decay) | HARD (catastrophic forgetting) |

---

## Real Example: Full Learning Cycle

### Day 1: SOAR Learns a Debugging Rule

```
Problem: "Function returns null"

Trace:
  State: {error: null, context: database}
    ↓ [Operator: check_query]
  State: {error: null, query_status: empty}
    ↓ [Operator: check_test_data]
  State: {query_empty: true, test_data: missing}
    ↓ SUCCESS

Extracted Rule:
  {
    "condition": {"error": "null", "context": "database"},
    "action": "check_database_query",
    "utility": 1.0,
    "uses": 1,
    "successes": 1,
    "failures": 0,
    "created": "2025-12-01 10:15"
  }

Saved to: rules.json
```

### Day 2: Rule is Used and Refined

```
Problem: "Another null return in database call"

Rule query:
  Matches: {error: null, context: database}
  Found: database_null_rule (utility: 1.0)
  Propose: check_database_query

Execution: SUCCESS

Update:
  database_null_rule.uses: 1 → 2
  database_null_rule.successes: 1 → 2
  database_null_rule.utility: 1.0/1 → 2/2 = 1.0

Saved to: rules.json
```

### Day 3: Rule Fails Once

```
Problem: "Null return but database looks fine"

Rule query:
  Matches: {error: null, context: database}
  Found: database_null_rule (utility: 1.0)
  Propose: check_database_query

Execution: FAILURE (wrong diagnosis)

Update:
  database_null_rule.uses: 2 → 3
  database_null_rule.failures: 0 → 1
  database_null_rule.utility: 2/2 → 2/3 = 0.67

Observation: Utility drops from 1.0 to 0.67 with one failure
             System now less confident in this rule

Saved to: rules.json
```

### Day 10: Accumulation

```
After 10 days of problem-solving:

database_null_rule statistics:
  uses: 47
  successes: 38
  failures: 9
  utility: 38/47 = 0.81

check_test_data_rule statistics:
  uses: 23
  successes: 16
  failures: 7
  utility: 16/23 = 0.70

System behavior:
  When both applicable: Prefers check_database_query
  (utility 0.81 > 0.70)

Next null_return problem: Immediately recommends
check_database_query first (learned over 10 days)
```

---

## Why This Matters for WS2

### Advantages of Symbolic Memory

✅ **Transparent**: Can read why agent made decision
✅ **Portable**: Rules move to other systems (WS1)
✅ **Explainable**: "Rule X has utility 0.81 because succeeded 38/47 times"
✅ **Fast learning**: Improve after single example
✅ **Persistent**: Survives model changes
✅ **Composable**: Combine rules across domains

### Disadvantages vs. Neural Networks

❌ **Limited pattern discovery**: Needs explicit rule format
❌ **Brittleness**: If state representation changes, rules break
❌ **Slower at some tasks**: Requires careful rule design
❌ **Not automatic**: Rules must be extracted (not learned implicitly)

### Hybrid Solution

```
SOAR + ACT-R + LLM:

LLM handles:
  ├─ Grounding (understand raw input)
  ├─ Pattern recognition (implicit knowledge)
  └─ Generation (create proposals)

SOAR handles:
  ├─ Problem decomposition
  ├─ Operator elaboration
  └─ Explicit reasoning

ACT-R handles:
  ├─ Rapid decision-making
  ├─ Utility-based selection
  └─ Memory management

Symbolic storage:
  ├─ Rules persist (portable)
  ├─ Utilities persist (trackable)
  └─ Knowledge accumulates (learnable)

Result: Transparent, portable, continuously-improving reasoning system
```

---

## Conclusion

**SOAR and ACT-R don't use neural weights—they use symbolic knowledge:**

1. **Rules**: IF-THEN statements (explicit, interpretable)
2. **Utilities**: Success counts (trackable, improvable)
3. **Chunks**: Activation-based memory (forgetting naturally)
4. **Databases**: Persist learning (survive sessions)

**Why this matters**:
- Knowledge is **portable** (move rules between systems)
- Learning is **trackable** (see success counts improve)
- Reasoning is **explainable** (read the rules)
- Memory is **persistent** (save to disk)

This is fundamentally different from neural networks, and it's exactly what WS1 needs for portability and WS2 needs for emergent reasoning.

**For your research**: SOAR/ACT-R provide the infrastructure for persistent, explainable, portable learning—the foundation of true emergent reasoning.
