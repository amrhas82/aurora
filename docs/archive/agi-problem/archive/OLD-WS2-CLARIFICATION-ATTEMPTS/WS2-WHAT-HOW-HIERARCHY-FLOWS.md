# WS2: Complete WHAT/HOW Hierarchy and Flows
## Mapping Both Approaches (Small Model + SOAR/ACT-R) to Problem-Solving Layers

**Date**: December 5, 2025
**Purpose**: Show complete architecture with all layers, WHAT vs. HOW, and how everything flows

---

## Executive Summary

### The Three-Layer Model

Every intelligent system needs three layers:

| Layer | **Approach A (Small Model)** | **Approach B (SOAR)** | **Approach C (ACT-R)** |
|-------|---|---|---|
| **1. PERCEPTION (WHAT?)** | Big LLM grounds problem | LLM parses to state | LLM encodes input |
| **2. REASONING (HOW?)** | Small model suggests approach | SOAR searches operators | ACT-R selects rules |
| **3. LEARNING (IMPROVE)** | Fine-tune small model | Extract rules + utilities | Update utilities |

This document shows the **complete flow** for each, hierarchically organized.

---

## Part 1: Approach A (Small Model Learning)

### Layer 1: PERCEPTION ("WHAT is the problem?")

```
Job: Understand the problem in the world

Input: Raw problem description
  "The function getUserById returns null sometimes when user_id=42"

Process:
  Big LLM reads → Understands context → Extracts key info

Output: Structured representation
  {
    "problem_domain": "debugging",
    "issue_type": "intermittent_null_return",
    "context": {
      "function": "getUserById",
      "failing_case": "user_id=42",
      "frequency": "intermittent"
    },
    "goal": "find_root_cause"
  }

Who does it: BIG LLM
Role: WHAT layer (understanding)
```

### Layer 2: REASONING ("HOW should we solve it?")

#### Sub-layer 2a: Generate Options

```
Big LLM thinks: "What approaches could help?"
├─ Use Chain-of-Thought
├─ Use ReAct (think + act loop)
├─ Use Direct response
├─ Use Code execution

Produces: List of candidate approaches
```

#### Sub-layer 2b: Select Best Approach (HOW-PICKER)

```
Small Model's job: "Given this problem type, which approach works best?"

Input from Big LLM:
├─ Problem domain: "debugging"
├─ Issue type: "intermittent null"
├─ Previous context: [success/fail patterns]

Small Model predicts:
  "For intermittent nulls in database calls, ReAct is 75% successful"
  "CoT is 65% successful"
  "Code execution is 80% successful"

Recommendation: Use Code execution approach
```

### Layer 3: EXECUTION

```
Big LLM executes selected approach:
  "Let me write code to test getUserById(42)"
  → Runs code
  → Observes: "Query returns empty result set"
  → Concludes: "Test data missing"
```

### Layer 4: LEARNING ("How do we improve?")

```
Trajectory captured:
{
  "problem_type": "intermittent_null",
  "domain": "database",
  "approach_used": "code_execution",
  "success": true,
  "time_to_solve": "5 minutes"
}

Small Model learns:
  "Code execution is good for database debugging"
  Increases utility of code execution for database problems

Next time similar problem:
  Small model recommends code execution immediately
  (confidence increases from 75% to 80%)
```

### Approach A: Hierarchy Summary

```
APPROACH A HIERARCHY:

Problem Input
    ↓ (BIG LLM: WHAT?)
┌─────────────────────┐
│ Understand Problem  │
│ (structured state)  │
└─────────┬───────────┘
          ↓
    ┌──────────────────────────────────┐
    │ Generate Candidate Approaches    │
    │ (CoT, ReAct, Code, Direct, etc.) │
    └─────────┬────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│ SMALL MODEL: Which is best? (HOW?)  │
│ - Learned patterns                  │
│ - Success rates for this problem    │
│ - Confidence levels                 │
│ Output: Ranked approaches           │
└─────────┬───────────────────────────┘
          ↓
┌──────────────────────────────────┐
│ Big LLM Executes Best Approach   │
│ (CoT, ReAct, Code, etc.)        │
└─────────┬──────────────────────┘
          ↓
┌──────────────────────────────────┐
│ Record Outcome                   │
│ (success/failure)                │
└─────────┬──────────────────────┘
          ↓
┌──────────────────────────────────┐
│ Small Model Learns               │
│ - Update success rates           │
│ - Improve future recommendations │
└──────────────────────────────────┘
```

### Data Flow for Approach A

```
Big LLM                          Small Model
   │                               │
   ├─→ "Here's the problem" ──────→│
   │                               │
   │   "What approach should we    │
   │    use for THIS problem?"     │
   │                               ↓
   │                        [Pattern matching]
   │                        [Success rate lookup]
   │                        [Confidence calc]
   │                               │
   │←────────────────────────────←┤
   │    "Use ReAct (75% confident)"│
   │                               │
   ├─→ Execute ReAct approach      │
   │    Observe: Success!          │
   │                               │
   ├─→ Log trajectory             │
   │   (problem, approach, outcome)│
   │                               │
   └─→ "Here's the result"────────→│
                                   ↓
                            [Fine-tune on trajectory]
                            [Update success rate: 75% → 76%]
```

---

## Part 2: Approach B (SOAR-Based Reasoning)

### Layer 1: PERCEPTION ("WHAT is the situation?")

```
Job: Parse problem into structured state

Input: Raw problem
  "The function getUserById returns null sometimes when user_id=42"

Process:
  LLM parses input → Converts to JSON working memory

Output: State representation
  {
    "state_type": "debugging",
    "situation": "function_returns_null",
    "goal": "find_root_cause",
    "context": {
      "function_name": "getUserById",
      "failing_input": 42,
      "symptom": "null_return"
    },
    "operators_tried": [],
    "knowledge": {
      "db_connected": true,
      "test_data_exists": true
    }
  }

Who does it: LLM (Perception layer)
Role: WHAT layer (understanding)
```

### Layer 2: REASONING ("HOW should we solve it?")

#### Sub-layer 2a: Elaboration (What can I do?)

```
Job: Query production rules to find applicable operators

Rules in memory:
  Rule 1: IF state == "debugging" AND symptom == "null_return"
          AND error_location == "function_output"
          THEN propose operator "check_function_logic"

  Rule 2: IF state == "debugging" AND symptom == "null_return"
          AND context.function_name matches database pattern
          THEN propose operator "check_database_query"

  Rule 3: IF state == "debugging" AND symptom == "null_return"
          AND db_connected == true
          THEN propose operator "test_with_sample_data"

Process:
  SOAR evaluates each rule against current state
  ✓ Rule 1 matches → Add operator
  ✓ Rule 2 matches → Add operator
  ✓ Rule 3 matches → Add operator

Operators generated:
├─ "check_function_logic"
├─ "check_database_query"
└─ "test_with_sample_data"

Who does it: Rule Engine (elaboration)
Role: HOW layer - part A (generate options)
```

#### Sub-layer 2b: Evaluation (Which is best?)

```
Job: Score each operator by likelihood and past success

For operator "check_function_logic":
  - Predicted usefulness: 0.60 (moderate chance it helps)
  - Historical utility: 0.55 (worked 55% of past times)
  - Combined score: 0.60 × 0.55 = 0.33

For operator "check_database_query":
  - Predicted usefulness: 0.85 (likely, matches pattern)
  - Historical utility: 0.80 (worked 80% of past times)
  - Combined score: 0.85 × 0.80 = 0.68

For operator "test_with_sample_data":
  - Predicted usefulness: 0.90 (very likely)
  - Historical utility: 0.70 (worked 70% of past times)
  - Combined score: 0.90 × 0.70 = 0.63

Ranking:
1. "check_database_query" (0.68)
2. "test_with_sample_data" (0.63)
3. "check_function_logic" (0.33)

Who does it: LLM (evaluation) + Utility tracker
Role: HOW layer - part B (score options)
```

#### Sub-layer 2c: Decision (What should we do?)

```
Best score: 0.68
Second best: 0.63
Margin: 0.05 (small gap)

If margin > 0.1: Execute best (confident)
If margin < 0.1: Create sub-goal (test both)

Decision: Margin is small (0.05 < 0.1)
  → Create sub-goal: "Which is really better?"
  → Spend test-time compute exploring both
  → Learn from the comparison

Who does it: Decision logic
Role: HOW layer - part C (commit to action)
```

### Layer 3: EXECUTION

```
Execute selected operator "check_database_query":
  - Run: db.query(42) with logging
  - Observe: Returns empty ResultSet
  - New state: {
      "query_returned_empty": true,
      "potential_cause": "no_test_data"
    }

Who does it: Executor
Role: EXECUTE layer
```

### Layer 4: LEARNING ("How do we improve?")

```
Success criterion: Did we advance toward goal?
Actual outcome: Found potential cause (empty query result)
Result: SUCCESS (significant progress)

Learning mechanisms:

1. RULE EXTRACTION (SOAR):
   Trace: state → check_database_query → success

   New Rule:
   "IF debugging function that returns null
    AND involves database
    AND database query returns empty
    THEN likely cause is missing test data"

   This rule added to rule memory

2. UTILITY UPDATE (ACT-R-like):
   "check_database_query" success rate: 0.80 → 0.82
   (Increased because it helped this time)

3. SUB-GOAL LEARNING:
   We explored "check_database_query" vs "test_with_sample_data"

   Comparison result:
   "check_database_query" found problem faster

   Update decision utility:
   "For intermittent null returns, prefer check_database_query"

Who does it: Learning system
Role: IMPROVE layer
```

### Approach B: Hierarchy Summary

```
APPROACH B (SOAR) HIERARCHY:

Problem Input
    ↓ (LLM: WHAT?)
┌─────────────────────────────┐
│ Parse to State (JSON)       │
│ (what's the situation?)     │
└─────────┬───────────────────┘
          ↓
┌──────────────────────────────────────┐
│ ELABORATION (Rule engine: HOW-A?)    │
│ "What can I do?"                     │
│ - Query rules for operators          │
│ Output: List of operators            │
└─────────┬──────────────────────────┘
          ↓
┌──────────────────────────────────────┐
│ EVALUATION (LLM + Utilities: HOW-B?) │
│ "Which is best?"                     │
│ - Score each operator                │
│ - Rank by utility                    │
│ Output: Ranked operators             │
└─────────┬──────────────────────────┘
          ↓
┌──────────────────────────────────────┐
│ DECISION (Decision Logic: HOW-C?)    │
│ "What should we do?"                 │
│ - If confident: execute              │
│ - If unsure: create sub-goal         │
│ Output: Selected operator             │
└─────────┬──────────────────────────┘
          ↓
┌──────────────────────────────────────┐
│ EXECUTION                             │
│ Run selected operator                │
│ Observe new state                    │
└─────────┬──────────────────────────┘
          ↓
┌──────────────────────────────────────┐
│ LEARNING (Automatic)                 │
│ - Extract rules from successful trace│
│ - Update operator utilities          │
│ - Store in rule memory               │
└──────────────────────────────────────┘
```

### Data Flow for Approach B

```
Problem Input
    ↓
┌─────────────────────────────────────┐
│ LLM Perception Layer                │
│ Parse to JSON state                 │
└────────┬────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ Rule Engine (Elaboration)           │
│ If state matches rule → propose     │
└────────┬────────────────────────────┘
         ↓
    [Operators: check_db, test_data, ...]
         ↓
┌─────────────────────────────────────┐
│ LLM Evaluator                       │
│ "Will this help?"                   │
│ Score × historical utility          │
└────────┬────────────────────────────┘
         ↓
    [Ranked: 0.68, 0.63, 0.33]
         ↓
┌─────────────────────────────────────┐
│ Decision Logic                      │
│ Confident? (margin > 0.1)           │
│ No → Create sub-goal (test both)    │
└────────┬────────────────────────────┘
         ↓
    [Selected: check_database_query]
         ↓
┌─────────────────────────────────────┐
│ Executor                            │
│ Run operator, observe result        │
└────────┬────────────────────────────┘
         ↓
    [New state: query_empty=true]
         ↓
┌─────────────────────────────────────┐
│ Learning System                     │
│ Extract rule from trace             │
│ Update utilities                    │
│ Store new rule in memory            │
└─────────────────────────────────────┘
         ↓
    [Rule memory updated]
    [Utilities updated]
    [Next similar problem: faster decision]
```

---

## Part 3: Approach C (ACT-R-Based Reasoning)

### Layer 1: PERCEPTION ("WHAT is the input?")

```
Job: Encode input into attention focus

Input: Problem statement
  "The function getUserById returns null sometimes when user_id=42"

Perceptual Processing:
  Visual module processes text
  → Extracts key elements
  → Creates chunks in working memory

Attention focus:
  {
    "focus": "function_behavior",
    "key_chunk": "getUserById",
    "issue": "intermittent_null"
  }

Who does it: Perceptual modules (LLM equivalent)
Role: WHAT layer (perceive input)
```

### Layer 2: REASONING ("HOW should we respond?")

#### Sub-layer 2a: Declarative Retrieval (Recall knowledge)

```
Goal: Retrieve relevant knowledge about null returns

Activation spread:
  "getUserById" activates:
    ├─ database queries (associated)
    ├─ null_returns (associated)
    └─ debugging_techniques (associated)

Retrieval strength:
  "For database null returns, check if query executed"
    (High activation: used 50 times, 90% successful)

  "For null returns, check function logic"
    (Medium activation: used 20 times, 60% successful)

Retrieved chunks (ordered by activation):
1. "Database null returns = query issue" (0.95 activation)
2. "Check function logic for null" (0.65 activation)
3. "Test with sample data" (0.70 activation)

Who does it: Declarative memory
Role: HOW layer - part A (recall options)
```

#### Sub-layer 2b: Production Rule Selection

```
Goal: Choose best rule from available productions

Available production rules:
  Rule A: "IF focus is null_return AND domain is database
          THEN retrieve solution_approach AND update goal"
          Utility = (success: 45, failure: 5, cost: 0.1) = 4.4

  Rule B: "IF focus is null_return AND uncertain
          THEN elaborate AND create sub-goal"
          Utility = (success: 20, failure: 15, cost: 0.2) = 1.8

  Rule C: "IF domain is database
          THEN test_with_sample_data"
          Utility = (success: 35, failure: 10, cost: 0.15) = 3.35

Utility calculation:
  Utility = (successes × reward) - (failures × penalty) - cost

Conflict resolution:
  Rule A has highest utility (4.4)

Selected: Rule A

Who does it: Central production system
Role: HOW layer - part B (select best rule)
```

#### Sub-layer 2c: Action Execution

```
Execute Rule A:
  - Retrieve: Solution approach for database nulls
  - Update goal: "Test database query"
  - Action: Run query with logging

Who does it: Motor/Action system
Role: HOW layer - part C (execute)
```

### Layer 3: EXECUTION

```
Execute: Run db.query(42) with logging
Result: Returns empty
New focus: "Query returned empty"
```

### Layer 4: LEARNING ("How do we improve?")

```
Outcome: Successful (found cause)

Learning mechanism:

UTILITY UPDATE (ACT-R core):
  Rule A succeeded:
    Successes: 45 → 46
    New utility: (46 × 1) - (5 × 0.5) - 0.1 = 43.4 (was 44)

  Wait, let me recalculate:
    Old utility: (45 × 1) - (5 × 0.5) - 0.1 = 43.9
    New utility: (46 × 1) - (5 × 0.5) - 0.1 = 44.9

  Increase: +1.0 (rule becomes stronger)

ACTIVATION UPDATE:
  Knowledge chunk "database_null_debugging" activation increases
  (Will be retrieved faster next time)

MEMORY CONSOLIDATION:
  New episode: "Problem X solved using Rule A"
  Stored in episodic memory
  Adds to future decision context

Next time similar problem:
  Rule A has higher utility (44.9 vs 4.4)
  Will be selected immediately
  Decision is faster and more confident

Who does it: Learning mechanisms (utility + activation)
Role: IMPROVE layer
```

### Approach C: Hierarchy Summary

```
APPROACH C (ACT-R) HIERARCHY:

Problem Input
    ↓ (Perceptual module: WHAT?)
┌─────────────────────────────────────┐
│ Encode Input                        │
│ (attention focus on key elements)   │
└─────────┬───────────────────────────┘
          ↓
┌──────────────────────────────────────┐
│ DECLARATIVE RETRIEVAL (HOW-A?)       │
│ "What do I know about this?"         │
│ - Activate relevant chunks           │
│ - Spread activation                  │
│ Output: Retrieved knowledge          │
└─────────┬──────────────────────────┘
          ↓
┌──────────────────────────────────────┐
│ PRODUCTION SELECTION (HOW-B?)        │
│ "Which rule is best?"                │
│ - Rules compete by utility           │
│ - Highest utility selected           │
│ Output: Selected rule                │
└─────────┬──────────────────────────┘
          ↓
┌──────────────────────────────────────┐
│ ACTION EXECUTION (HOW-C?)            │
│ "Do it"                              │
│ - Execute selected rule              │
│ - Observe feedback                   │
│ Output: Result                       │
└─────────┬──────────────────────────┘
          ↓
┌──────────────────────────────────────┐
│ LEARNING (Automatic)                │
│ - Update rule utilities              │
│ - Activate successful chunks         │
│ - Strengthen memory                  │
└──────────────────────────────────────┘
```

---

## Comparison: WHAT/HOW Layers Across All Three

### PERCEPTION Layer (WHAT)

| Approach | Input | Process | Output |
|----------|-------|---------|--------|
| **A (Small)** | Raw problem | Big LLM understands | Structured context |
| **B (SOAR)** | Raw problem | LLM parses to JSON | Working memory state |
| **C (ACT-R)** | Raw problem | Perceptual encoding | Attention focus + chunks |

**Key difference**: What abstraction is used? (Context vs. State vs. Focus)

### REASONING Layer (HOW)

| Phase | **A (Small)** | **B (SOAR)** | **C (ACT-R)** |
|-------|---|---|---|
| **Generate** | Big LLM lists approaches | Rule engine elaborates operators | Declarative retrieval |
| **Evaluate** | Small model scores | LLM scores + utilities | Production utilities |
| **Decide** | Select highest rank | Select if confident, else sub-goal | Select highest utility |

**Key difference**: Who does the scoring? (Small model vs. LLM vs. Rule utility vs. Production utility)

### EXECUTION Layer

| Approach | Action | Result | Who? |
|----------|--------|--------|------|
| **A** | Big LLM executes approach | Outcome | LLM |
| **B** | Tool/function executes | New state | Executor |
| **C** | Action system executes | Feedback | Motor module |

### LEARNING Layer (IMPROVE)

| Approach | Mechanism | Storage | Improvement |
|----------|-----------|---------|-------------|
| **A** | Trajectory fine-tuning | Neural weights | Next recommendations better |
| **B** | Rule extraction + utility update | Rule database | Faster decisions + better scores |
| **C** | Utility update + activation | Memory + utilities | Stronger rules, faster retrieval |

---

## Complete End-to-End Flows

### Approach A: Complete Flow Example

```
Input: "Why does getUserById(42) return null?"

1. BIG LLM (WHAT):
   Understands: Database debugging problem

2. BIG LLM -> asks SMALL MODEL:
   "For database debugging, which approach works best?"

3. SMALL MODEL (HOW-SELECTOR):
   Checks learned patterns:
   "For database nulls → Code execution 80%, CoT 65%"
   Recommends: Code execution

4. BIG LLM executes:
   Writes code, runs query, sees empty result
   Concludes: Test data missing

5. SMALL MODEL learns:
   "Code execution was successful for this problem type"
   Updates: database_debugging with code_execution = 0.81

Next time: Immediately recommends code execution
```

### Approach B: Complete Flow Example

```
Input: "Why does getUserById(42) return null?"

1. LLM PERCEPTION (WHAT):
   Parses to state:
   {state: debugging, goal: find_root_cause, issue: null_return}

2. RULE ELABORATION:
   Queries rules matching state
   Finds: [check_function, check_database_query, test_sample_data]

3. LLM EVALUATION (HOW-SCORER):
   Scores operators:
   check_database_query: 0.68
   test_sample_data: 0.63
   check_function: 0.33

4. DECISION:
   Gap too small (0.05 < 0.1)
   Create sub-goal: test both
   Deep search / test-time compute

5. EXECUTOR:
   Runs check_database_query
   Observes: empty result
   Success!

6. LEARNING:
   New rule: "IF null_return AND database_pattern THEN check_query"
   Utility: check_database_query 0.80 → 0.82

Next time: Found rule immediately, faster decision
```

### Approach C: Complete Flow Example

```
Input: "Why does getUserById(42) return null?"

1. PERCEPTUAL ENCODING (WHAT):
   Focus: function_behavior
   Chunks: getUserById, null_return, debugging

2. DECLARATIVE RETRIEVAL:
   Activations:
   - database_null_solution: 0.95
   - function_logic_check: 0.65

3. PRODUCTION SELECTION:
   Rule A (database debugging): utility 4.4
   Rule B (uncertain): utility 1.8

   Select Rule A

4. ACTION:
   Execute rule: test database query
   Observe: empty result

5. LEARNING:
   Rule A succeeded:
   Utility: 4.4 → 5.4
   Chunk activation increases
   Episode stored in memory

Next time: Rule A selected faster with higher confidence
```

---

## Which WHAT/HOW Split Is Best?

### Approach A Clarity

| Layer | What | How |
|-------|------|-----|
| 1 (PERCEPTION) | **Big LLM** understands problem | N/A |
| 2 (REASONING) | **Big LLM** lists options | **Small Model** ranks them |
| 3 (EXECUTION) | **Big LLM** runs chosen approach | N/A |

**Trade-off**: Small model is simple learner, but still bottlenecked by LLM reasoning

### Approach B Clarity

| Layer | What | How |
|-------|------|-----|
| 1 (PERCEPTION) | **LLM** parses to JSON state | N/A |
| 2a (ELABORATION) | N/A | **Rules** generate operators |
| 2b (EVALUATION) | N/A | **LLM + utilities** score |
| 2c (DECISION) | N/A | **Logic** selects operator |
| 3 (EXECUTION) | N/A | **Executor** runs it |

**Trade-off**: Multiple HOW layers, but each is explicit and clear

### Approach C Clarity

| Layer | What | How |
|-------|------|-----|
| 1 (PERCEPTION) | **Perception** encodes input | N/A |
| 2a (RETRIEVAL) | N/A | **Declarative memory** recalls |
| 2b (PRODUCTION) | N/A | **Rules + utilities** select |
| 2c (ACTION) | N/A | **Motor** executes |

**Trade-off**: Modular (each module independent), but interdependencies complex

---

## Recommendation for Your WS2

### Ideal: Start with SOAR (Approach B)

**Why**:
1. **WHAT/HOW split is clearest**: State → elaborate, evaluate, decide
2. **Explicit learning**: Rules are portable (WS1 alignment)
3. **Transparent**: Every decision visible
4. **Scales**: SOAR handles complex problems
5. **Hybrid ready**: Can add ACT-R utilities later

### Then add ACT-R components

By month 3-4:
```
SOAR (problem-space reasoning)
  + ACT-R utilities (rule scoring)
  + ACT-R activation decay (memory management)
```

Result: Best of both worlds

### Why not small model only?

- ✓ Easy to implement
- ✓ Minimal changes
- ✗ Still limited by LLM reasoning ceiling
- ✗ Learning is implicit (can't be portable)
- ✗ Not true emergent reasoning

---

## Conclusion

All three approaches work, but the **WHAT/HOW split tells the story**:

- **Approach A**: Small model picks HOW, big LLM does WHAT + execution
- **Approach B**: LLM/rules handle WHAT perception, SOAR handles all HOW
- **Approach C**: Modules coordinate HOW, perception does WHAT

For your research:
1. **Month 1-2**: Implement SOAR fully (all layers)
2. **Month 3-4**: Add ACT-R utilities (enhanced HOW)
3. **Month 5-6**: Compare to small model baseline
4. **Month 6-9**: Hybrid optimization and publication

The goal: Show that SOAR + ACT-R + LLMs = emergent reasoning at scale.
