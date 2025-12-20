# WS2: SOAR Implementation Approaches
## Two Paths to Emergent Reasoning: Small Model Learning vs. Cognitive Architecture

**Date**: December 5, 2025
**Status**: Architecture Exploration - Hybrid Approaches
**Context**: Workstream 2 (Emergent Reasoning) - comparing small model guidance vs. native cognitive architecture

---

## Executive Summary

We have two distinct approaches to solving "emergent reasoning" in WS2:

**Approach A (Current)**: Small model learns HOW from big model trajectories
- LLM-native
- Minimal architecture changes
- Pattern learning over experience

**Approach B (New)**: Cognitive architecture (SOAR-like) enables native reasoning
- Architecture-native
- Requires new system design
- Symbolic reasoning + learning

**Key question**: Which is more viable at scale? Or should we pursue both in parallel?

---

## Approach A: Small Model Learning (LLM-Based)

### High-Level Flow

```
Big Model (Problem Solver)          Small Model (Strategy Learner)
        ↓                                    ↑
  Problem Input ──────────────────→ Observe trajectory
        ↓                                    ↓
  Generate operators               Learn patterns
        ↓                          (implicit knowledge)
  Evaluate options                         ↓
        ↓                          Suggest heuristics
  Execute action                   (for next problem)
        ↓
  Record outcome
        ↓
  Small model fine-tunes on data
```

### Implementation

**Stack**: LangSmith + LLM + Fine-tuning
- Real-time trajectory capture (what did agent try?)
- Small model observes patterns (successful vs. failed approaches)
- Monthly fine-tune cycle (improve small model)
- Integrate guidance back into big model prompts

### Pros
✅ Works with existing LLM infrastructure
✅ Minimal changes to current agent frameworks
✅ Passive learning (just observing)
✅ Proven fine-tuning works

### Cons
❌ Bottlenecked by LLM's reasoning capability
❌ Small model is still pattern-matching (not reasoning)
❌ Doesn't solve "token prediction ceiling"
❌ Learning is implicit (can't explain reasoning)
❌ Not truly emergent (LLM still predicts tokens)

---

## Approach B: SOAR Implementation (Cognitive Architecture)

### What Is SOAR?

**SOAR** = State, Operator, And Result

The core idea: **All intelligence is problem-space search**

```
Current State → [What can I do?] → Evaluate options → Select best → Execute → New state
                     (Operators)      (SOAR cycle)
                                            ↓
                                      [Learn: add rule for next time]
```

### High-Level Implementation

#### The SOAR Cycle (How It Works)

```
┌──────────────────────────────────────────────────────┐
│          SOAR DECISION CYCLE (Every Iteration)       │
├──────────────────────────────────────────────────────┤
│                                                      │
│  1. PERCEPTION PHASE                                 │
│     ├─ Parse current state from environment         │
│     ├─ Convert to working memory representation     │
│     └─ Example: JSON state = {board: [...],         │
│                                goal: "win",          │
│                                pieces: {...}}        │
│                                                      │
│  2. ELABORATION PHASE (What can I do?)              │
│     ├─ Query production rules in memory             │
│     ├─ Apply rules: IF (state properties) THEN...  │
│     ├─ Generate all possible operators              │
│     └─ Example: IF board has undefended piece       │
│                THEN propose "capture it"            │
│                                                      │
│  3. PROPOSAL PHASE (Which operators are relevant?) │
│     ├─ Collect all proposed operators               │
│     ├─ Filter out irrelevant ones                   │
│     └─ Keep only operators that apply to goal       │
│                                                      │
│  4. EVALUATION PHASE (Which is best?)               │
│     ├─ For each operator, predict outcome           │
│     ├─ Score based on proximity to goal             │
│     ├─ Use utilities: past success rates            │
│     └─ Example: "capture piece" has 75% success     │
│           vs. "develop position" has 60%            │
│                                                      │
│  5. DECISION PHASE (Select action)                  │
│     ├─ Choose operator with best utility            │
│     ├─ If multiple equally good: create sub-goal   │
│     │   (deeper search, test-time compute)          │
│     └─ Otherwise: apply operator                    │
│                                                      │
│  6. EXECUTION PHASE (Do it)                         │
│     ├─ Execute selected operator                    │
│     ├─ Observe result (new state)                   │
│     └─ Return to step 1                             │
│                                                      │
│  7. LEARNING PHASE (Remember for next time)        │
│     ├─ IF problem solved successfully:              │
│     │   ├─ Capture decision path as rule           │
│     │   └─ Increase utility of operators used      │
│     └─ IF problem failed:                           │
│          ├─ Decrease utility of bad operators      │
│          └─ Create sub-goals to understand why     │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### Implementation Stack

#### Core Components

```
┌─────────────────────────────────────────┐
│  1. STATE REPRESENTATION (JSON)         │
│  ├─ Current situation (structured)      │
│  ├─ Goals (desired outcome)             │
│  ├─ Context (environment, constraints)  │
│  └─ Example:                            │
│     {                                   │
│       "state": "debugging_code",        │
│       "goal": "find bug",               │
│       "context": {                      │
│         "code_lines": [...],            │
│         "error_message": "...",         │
│         "attempted_fixes": [...]        │
│       },                                │
│       "operators_tried": []             │
│     }                                   │
└─────────────────────────────────────────┘
          ↓
┌─────────────────────────────────────────┐
│  2. PRODUCTION RULE MEMORY              │
│  ├─ Rules learned from experience       │
│  ├─ Format: IF-THEN statements         │
│  ├─ Example:                            │
│  │   IF state=="debugging"              │
│  │   AND goal=="find bug"               │
│  │   AND "error_message" mentions "null"│
│  │   THEN propose "check null pointers" │
│  │                                       │
│  └─ Storage: Database/Knowledge base    │
│     (easily portable, symbolic)         │
└─────────────────────────────────────────┘
          ↓
┌─────────────────────────────────────────┐
│  3. OPERATOR GENERATOR                  │
│  ├─ Input: Current state (JSON)         │
│  ├─ Query rules: what's applicable?     │
│  ├─ Generate operators (possible actions)
│  ├─ Output: List of operators           │
│  └─ Example:                            │
│     Operators = [                       │
│       "check_null_pointers",            │
│       "trace_execution",                │
│       "test_edge_cases",                │
│       "review_logic"                    │
│     ]                                   │
└─────────────────────────────────────────┘
          ↓
┌─────────────────────────────────────────┐
│  4. OPERATOR EVALUATOR                  │
│  ├─ Input: Operator + state             │
│  ├─ Predict outcome (using LLM or rules)│
│  ├─ Score: distance to goal             │
│  ├─ Track: success rate (utility)       │
│  └─ Output: Ranked operators            │
│     Example:                            │
│     "check_null_pointers": score=0.95   │
│     "trace_execution": score=0.75      │
└─────────────────────────────────────────┘
          ↓
┌─────────────────────────────────────────┐
│  5. DECISION MAKER                      │
│  ├─ Input: Ranked operators             │
│  ├─ If clear best: select it            │
│  ├─ If tie: create sub-goal             │
│  │  (deep search / test-time compute)   │
│  ├─ If all bad: impasse resolution      │
│  └─ Output: Selected operator           │
└─────────────────────────────────────────┘
          ↓
┌─────────────────────────────────────────┐
│  6. ACTION EXECUTOR                     │
│  ├─ Input: Selected operator             │
│  ├─ Call appropriate function/tool      │
│  ├─ Observe result (new state)          │
│  └─ Output: Updated state (JSON)        │
│     Example:                            │
│     New state = {                       │
│       "state": "debugging_code",        │
│       "operators_tried": [...,          │
│         "check_null_pointers"],         │
│       "result": "bug found in line 42"  │
│     }                                   │
└─────────────────────────────────────────┘
          ↓
┌─────────────────────────────────────────┐
│  7. LEARNING SYSTEM                     │
│  ├─ Input: Operator + outcome           │
│  ├─ If success:                         │
│  │   ├─ Capture trace as new rule       │
│  │   └─ Increase utility                │
│  ├─ If failure:                         │
│  │   ├─ Decrease utility                │
│  │   └─ Create sub-goals to understand  │
│  └─ Output: Updated rule database       │
└─────────────────────────────────────────┘
```

### Implementation Technology Stack

#### Option 1: Rule Engine + LLM (Hybrid)

```
Framework: Drools, Clara, or custom rule engine

Architecture:
┌────────────────────┐
│  Problem Input     │
│  (JSON State)      │
└─────────┬──────────┘
          ↓
┌────────────────────┐
│  Rule Engine       │
│  (Drools/Clara)    │  ← Elaboration phase
│  Query rules →     │    Generates operators
│  Get operators     │
└─────────┬──────────┘
          ↓
┌────────────────────┐
│  LLM Evaluator     │
│  (GPT-4, Claude)   │  ← Evaluation phase
│  "Which is best?"  │    Scores operators
└─────────┬──────────┘
          ↓
┌────────────────────┐
│  Decision Logic    │
│  Select + Execute  │  ← Decision/execution
└─────────┬──────────┘
          ↓
┌────────────────────┐
│  Learning System   │
│  Update rules      │  ← Learning
│  Track utilities   │
└────────────────────┘
```

**Pros**:
✅ Rule engine handles deterministic elaboration
✅ LLM handles semantic evaluation
✅ Clear separation of concerns
✅ Rules are symbolic (portable)

**Cons**:
❌ Requires two systems to work together
❌ LLM calls every iteration (expensive)
❌ Need to define rule syntax upfront

#### Option 2: Agentic Workflow (Code-Based)

```
Framework: LangGraph, LangChain, or custom

Architecture:
Each step is a node in a graph

Node 1: State Parser
  Input: Raw problem
  Output: JSON state

Node 2: Operator Generator
  Input: JSON state
  Logic: Query rules / LLM
  Output: List of operators

Node 3: Operator Evaluator
  Input: Operators + state
  Logic: Score each operator
  Output: Ranked operators

Node 4: Conflict Resolution (Decision)
  Input: Ranked operators
  Logic: Select best / create sub-goals
  Output: Selected operator

Node 5: Executor
  Input: Operator
  Logic: Call tools/functions
  Output: New state

Node 6: Learning
  Input: Trace (state → operator → result)
  Logic: Update rules / utilities
  Output: Updated knowledge base

Graph:
Parser → Generator → Evaluator → Decision → Executor
                                             ↓
                                          Learning
                                             ↓
                                          (loop back)
```

**Pros**:
✅ Fits naturally into LLM agent frameworks
✅ Can use existing tools (LangGraph, LangChain)
✅ Code-based (easier to understand/debug)
✅ Flexible node design

**Cons**:
❌ Less formal than symbolic rule engine
❌ Rules harder to extract/share
❌ Learning logic more ad-hoc

#### Option 3: Formal SOAR Reimplementation

```
Framework: Python/Rust from scratch or extend Jsoar

Core classes:

class SOARAgent:
  def __init__(self):
    self.working_memory = {}  # current state (JSON)
    self.rules = []           # production rules
    self.utilities = {}       # operator success rates
    self.goals = []           # current goals

  def perceive(self, raw_input):
    """Parse input to JSON state"""
    self.working_memory = parse_to_json(raw_input)

  def elaborate(self):
    """Generate operators by querying rules"""
    for rule in self.rules:
      if rule.matches(self.working_memory):
        operators.append(rule.operator)
    return operators

  def evaluate(self, operators):
    """Score operators"""
    ranked = []
    for op in operators:
      score = predict_outcome(self.working_memory, op)
      utility = self.utilities.get(op, 0.5)
      ranked.append((op, score * utility))
    return sorted(ranked, reverse=True)

  def decide(self, ranked_operators):
    """Select action or create sub-goal"""
    if ranked_operators[0].score > threshold:
      return ranked_operators[0].operator
    else:
      return create_subgoal(ranked_operators)

  def execute(self, operator):
    """Run the operator"""
    new_state = operator.execute(self.working_memory)
    self.working_memory = new_state
    return new_state

  def learn(self, trace):
    """Update rules and utilities"""
    if trace.success:
      # Create new rule from trace
      new_rule = extract_rule_from_trace(trace)
      self.rules.append(new_rule)

      # Increase utilities
      for op in trace.operators_used:
        self.utilities[op] += reward
    else:
      # Decrease utilities
      for op in trace.operators_used:
        self.utilities[op] -= penalty

  def run_cycle(self):
    """One SOAR iteration"""
    operators = self.elaborate()
    ranked = self.evaluate(operators)
    selected = self.decide(ranked)
    new_state = self.execute(selected)
    return new_state
```

**Pros**:
✅ Full control over SOAR semantics
✅ Optimal performance (native implementation)
✅ Clear learning dynamics
✅ Research-friendly

**Cons**:
❌ Significant development effort
❌ Harder to integrate with LLM ecosystem
❌ Requires deep SOAR knowledge

---

## Comparison Matrix

| Aspect | Small Model (A) | Rule Engine (B1) | Agentic (B2) | Native (B3) |
|--------|---|---|---|---|
| **Implementation Difficulty** | Easy | Medium | Medium | Hard |
| **Symbolic Learning** | No | Yes | Partially | Yes |
| **Portability** | Low | High | Medium | High |
| **Explainability** | Low | High | Medium | High |
| **Integration with LLMs** | Easy | Medium | Easy | Hard |
| **Passive Learning** | Yes | Limited | Limited | Yes |
| **Rule Extraction** | Implicit | Explicit | Code-based | Explicit |
| **Scaling** | 10-100 problems | 1000+ problems | 100-1000 | 1000+ |
| **True Reasoning** | No | Yes | Yes | Yes |

---

## Hybrid Approach (Recommended)

### Why Not Both?

You could actually combine the best of both:

```
┌────────────────────────────────────────┐
│  SOAR Agent (Hybrid Implementation)     │
├────────────────────────────────────────┤
│                                        │
│  1. State Parsing (JSON)               │
│  ├─ LLM grounds raw problem            │
│  └─ Outputs structured JSON            │
│                                        │
│  2. Operator Generation                │
│  ├─ Rule engine for known patterns     │
│  ├─ LLM for novel situations           │
│  └─ Combine both sources               │
│                                        │
│  3. Evaluation (Symbolic + Neural)     │
│  ├─ Rules for explicit knowledge       │
│  ├─ LLM for semantic understanding     │
│  └─ Blend scores                       │
│                                        │
│  4. Execution                          │
│  ├─ Call tools/APIs                    │
│  ├─ Observe results                    │
│  └─ Parse outcome                      │
│                                        │
│  5. Learning (Dual Path)               │
│  ├─ Symbolic: Update rules/utilities   │
│  ├─ Neural: Fine-tune small model      │
│  └─ Both improve over time             │
│                                        │
└────────────────────────────────────────┘
```

**Benefits**:
- Rules capture explicit knowledge (portable)
- Small model learns implicit patterns (learning)
- LLM grounds in language (perception)
- Each system improves independently
- Fall back to LLM if rules don't apply

---

## How Would SOAR Agent Actually Work?

### Concrete Example: Code Debugging

**Problem**: "Why does this function return null?"

#### State Representation (JSON)

```json
{
  "state": "debugging",
  "goal": "find null return cause",
  "context": {
    "language": "python",
    "function": "get_user_by_id(user_id)",
    "error": "returned None when user_id=42",
    "code": "def get_user_by_id(uid):\n  result = db.query(uid)\n  return result.first()"
  },
  "operators_tried": [],
  "knowledge": {
    "db_connected": true,
    "test_data_exists": true
  }
}
```

#### Rules in Memory

```
Rule 1:
IF state == "debugging"
AND goal == "find null return cause"
AND "result.first()" in function
THEN propose "check if query returns empty"

Rule 2:
IF state == "debugging"
AND goal == "find null return cause"
AND "db.query" in function
AND db_connected == true
THEN propose "check query parameters"

Rule 3:
IF state == "debugging"
AND all previous operators failed
THEN propose "add print statements for debugging"
```

#### Elaboration (What can I do?)

```
Agent queries rules:
✓ Rule 1 matches → propose "check if query returns empty"
✓ Rule 2 matches → propose "check query parameters"
✗ Rule 3 doesn't match yet
✗ Rule 4 doesn't match

Operators: ["check query", "check parameters"]
```

#### Evaluation (Which is best?)

```
For "check query":
  - Success rate (utility): 0.8 (worked before)
  - Semantic fit: 0.9 (very relevant)
  - Combined score: 0.85

For "check parameters":
  - Success rate (utility): 0.6
  - Semantic fit: 0.7
  - Combined score: 0.65

Ranked: ["check query", "check parameters"]
```

#### Decision

```
Best score: 0.85 (check query)
Confidence: High (>threshold)
Decision: Execute "check query"
```

#### Execution

```
Operator "check query":
  1. Run: db.query(42) → see what it returns
  2. Find: Returns empty ResultSet
  3. New state: {
       "query_returns_empty": true,
       "bug_location": "db.query or data issue",
       "next_step": "check if test data was created"
     }
```

#### Learning

```
Success! Bug found (query returns empty)

1. Create rule from this trace:
   IF db.query returns empty
   THEN check if test data exists

2. Increase utility:
   "check query" success rate: 0.8 → 0.85
   (used successfully in this problem)

3. Store in memory for next time:
   Similar bug with similar pattern → try "check query" first
```

---

## Practical Implementation Phases

### Phase 1: Proof of Concept (Weeks 1-3)

**Goal**: Implement one SOAR cycle

```
Build:
- State parser (JSON from problem input)
- Rule engine (10-20 hand-written rules)
- Operator generator (query rules)
- Evaluator (LLM scores operators)
- Executor (run selected operator)

Test on: Simple debugging task (1-2 problems)

Output: "SOAR agent solved 2/2 test problems correctly"
```

### Phase 2: Learning System (Weeks 4-6)

**Goal**: Add automatic rule learning

```
Build on Phase 1:
- Rule extraction from successful traces
- Utility tracking (success/failure)
- Rule database (persistent storage)

Test on: 20-30 problems in sequence

Output: "Agent accuracy improved from 40% to 70% over 30 problems"
```

### Phase 3: Hybrid Integration (Weeks 7-9)

**Goal**: Combine with LLM + small model

```
Build:
- LLM-based state parser (understand raw input)
- Symbolic rules + LLM evaluation (both sources)
- Small model learns on trajectories (parallel learning)

Test on: Mixed problem domain (50+ diverse problems)

Output: "Hybrid agent outperforms baseline on novel problems"
```

---

## Research Questions for SOAR Implementation

1. **Rule Learning**: How do we automatically extract good rules? How many traces do we need?
2. **Utility Estimation**: How do we score operators when outcome is uncertain?
3. **Scalability**: Can SOAR handle 1000+ rules without performance degradation?
4. **LLM Integration**: Where do we leverage LLM vs. symbolic reasoning?
5. **Portability**: Can rules from SOAR agent A work on agent B?
6. **Sub-Goals**: When should we create sub-goals vs. just pick best option?
7. **Transfer Learning**: Do rules from debugging tasks help math tasks?

---

## Next Steps for WS2

### If Pursuing SOAR Approach (B)

1. **Month 1**: Implement proof-of-concept (Phase 1)
   - One SOAR cycle on one problem domain
   - Hand-written rules
   - Measure: agent completes cycle

2. **Month 2-3**: Add learning system (Phase 2)
   - Automatic rule extraction
   - Utility tracking
   - Measure: improvement over problem sequences

3. **Month 4-6**: Hybrid integration
   - Add LLM perception layer
   - Integrate small model learning
   - Validate on diverse problems

### If Pursuing Small Model Approach (A)

1. **Month 1**: Set up trajectory capture
   - Instrument existing agent
   - Collect 100-200 problem traces

2. **Month 2-3**: Fine-tune small model
   - Train on captured trajectories
   - Evaluate on held-out problems

3. **Month 4-6**: Integration and scaling
   - Test on production agent
   - Measure learning curve

### If Pursuing Both (Hybrid)

Run both in parallel with cross-learning:
- SOAR learns rules + utilities
- Small model learns implicit patterns
- Each improves the other

---

## Recommendation

**For WS2 Research**: Start with **SOAR implementation (Agentic approach B2)**

**Why**:
1. ✅ Fits naturally into LangGraph/LangChain ecosystem
2. ✅ Can leverage existing LLM tools
3. ✅ Explicit rules are portable (WS1 alignment)
4. ✅ Learning is transparent and measurable
5. ✅ Solves reasoning problem at architectural level
6. ✅ Enables knowledge transfer (symbolic rules)

**Proof of concept**: 4-6 weeks
**Full implementation**: 3-4 months
**Integration with other WS**: Feeds directly into WS1 (portable rules), WS3 (framework agnostic)

---

## Conclusion

SOAR implementation isn't magic—it's **programmable agents that follow a deliberate reasoning process**:

1. Parse input to JSON state
2. Query rules to find applicable operators
3. Evaluate and rank options
4. Execute best one
5. Learn from outcome
6. Repeat

The agent is **explicit about its reasoning** (you can see every decision), **learns automatically** (improves over time), and **portable** (rules work across systems).

This is how you move from "token prediction" to "actual reasoning."

