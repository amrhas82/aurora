# WS2: Dual Approaches Summary
## Small Model Learning vs. SOAR-Based Reasoning

**Date**: December 5, 2025
**Context**: Clarifying two complementary paths to emergent reasoning

---

## The Question You Asked

> "If SOAR/ACT-R can do the HOW part (learning strategies, improving decisions), why do we need the small model learning from trajectories? Which one here works with WHAT and which is the HOW? High-level implementation?"

---

## Simple Answer

| Layer | **Approach A: Small Model** | **Approach B: SOAR** |
|-------|---|---|
| **WHAT** (problem understanding) | Big LLM | LLM (perception layer) |
| **HOW** (strategy learning) | Small model learns from trajectories | Symbolic rules + utilities (automatic) |
| **Implementation** | Existing LLM + fine-tuning | Programmable agent following SOAR cycle |

**Key difference**:
- Approach A: Small neural model learns patterns
- Approach B: Symbolic rules learn patterns (no separate model)

---

## Visual Comparison

### Approach A: Small Model Learning Flow

```
Problem Input
    ↓
Big LLM (WHAT)
├─ Understand context
├─ Decompose problem
└─ Generate approach
    ↓
Agent Executes (CoT, ReAct, etc.)
    ↓
Record Outcome
    ├─ Was it successful?
    ├─ What problem type?
    └─ Which approach worked?
    ↓
Small Model (HOW)
├─ Observes trajectory
├─ Learns patterns: "For problem_type X, approach Y works 75% of time"
└─ Fine-tunes on accumulated data
    ↓
Next Problem: Small model suggests approach → Big LLM executes
```

**Who learns what**:
- Big model: Stays frozen (never fine-tuned)
- Small model: Learns "which approaches work for which problems"

**Mechanism**: Pattern learning from trajectories (implicit knowledge)

---

### Approach B: SOAR-Based Reasoning Flow

```
Problem Input (Raw)
    ↓
State Parser (LLM grounds input to JSON)
├─ "What's the current situation?"
├─ "What's the goal?"
└─ Output: {state: {...}, goal: "..."}
    ↓
Elaboration (Query Rules)
├─ "What can I do?" (IF-THEN rules)
├─ "What operators are applicable?"
└─ Output: ["check_nulls", "trace", "test", ...]
    ↓
Evaluation (LLM scores options)
├─ For each operator: "Will this help?"
├─ Score: 0.0 → 1.0
└─ Rank by score + past utility
    ↓
Decision
├─ IF clear best: Execute it
├─ IF tie: Create sub-goal (test both, deep search)
└─ Output: Selected operator
    ↓
Execution (Run it)
├─ Call appropriate function/tool
├─ Observe result
└─ New state: {...}
    ↓
Learning (Automatic)
├─ IF success:
│  ├─ Capture trace as NEW RULE: "When X, try operator Y"
│  └─ Increase utility of operators used
├─ IF failure:
│  ├─ Decrease utility
│  └─ Create sub-goals to understand why
```

**Who learns what**:
- Reasoning engine: Learns rules + utilities automatically
- No separate small model needed
- Rules are symbolic (explicit, portable, explainable)

**Mechanism**: Automatic rule extraction from successful traces (explicit knowledge)

---

## The Core Difference

### Approach A (Small Model)

```
Data Path:
Trajectories → Small Model learns → Pattern extraction
              (neural network)    (implicit, weights-based)

What's portable: Just the patterns (unclear what was learned)
Knowledge type: Implicit (hidden in weights)
Learning mechanism: Fine-tuning on examples
```

### Approach B (SOAR)

```
Data Path:
Trajectories → Rule extraction → Rules + utilities
              (symbolic)        (explicit, portable)

What's portable: Exact rules ("IF X THEN Y"), utilities
Knowledge type: Explicit (clear rules anyone can understand)
Learning mechanism: Automatic capture + utility update
```

---

## SOAR Implementation (High Level)

### The SOAR Cycle (One Iteration)

```
def soar_cycle(state, rules, utilities):

    # 1. ELABORATION: What can I do?
    applicable_rules = [r for r in rules if r.matches(state)]
    operators = [r.operator for r in applicable_rules]

    # 2. EVALUATION: Which is best?
    scores = {}
    for op in operators:
        predicted_outcome = llm.evaluate(state, op)  # LLM scores it
        historical_utility = utilities.get(op, 0.5)   # How often worked?
        scores[op] = predicted_outcome * historical_utility

    # 3. DECISION: Select action
    best_op = max(scores, key=scores.get)
    if scores[best_op] > 0.8:
        return best_op  # Confident, execute
    else:
        return create_subgoal(state, operators)  # Uncertain, explore

    # 4. EXECUTION: Do it
    new_state = execute(best_op)

    # 5. LEARNING: Remember for next time
    if problem_solved(new_state):
        # Create new rule from trace
        new_rule = extract_rule(state, best_op, new_state)
        rules.append(new_rule)

        # Increase utility
        utilities[best_op] += reward
    else:
        # Decrease utility
        utilities[best_op] -= penalty

    return new_state
```

### Implementation Stack

```
Framework: LangGraph (or any agentic framework)

Nodes:
├─ Node 1: Parse Input → JSON State
├─ Node 2: Query Rules → Get operators
├─ Node 3: Score Operators → Rank by utility
├─ Node 4: Decide → Select or explore
├─ Node 5: Execute → Run action
└─ Node 6: Learn → Update rules/utilities

Storage:
├─ Rules: Database (easily portable, SQL/JSON)
├─ Utilities: Simple dict/table (success counts)
└─ Traces: Log file (for debugging, analysis)

Core Components:
├─ Rule Engine: Matches state to rules
├─ LLM Call: Scores operators
├─ Executor: Calls tools/APIs
└─ Learning: Extracts rules, updates utilities
```

### Concrete Code Shape (Pseudocode)

```python
class SOARAgent:
    def __init__(self):
        self.rules = Database("production_rules.db")
        self.utilities = Database("operator_utilities.db")

    def perceive(self, raw_input):
        """Parse input to JSON state"""
        state = llm_parse(raw_input)  # "What's the situation?"
        return state  # JSON: {state: "debugging", goal: "find bug", ...}

    def elaborate(self, state):
        """Generate operators by querying rules"""
        applicable = self.rules.query(state)  # Which rules match?
        operators = [rule.operator for rule in applicable]
        return operators  # ["check_nulls", "trace_execution", ...]

    def evaluate(self, state, operators):
        """Score each operator"""
        scored = {}
        for op in operators:
            score = llm_evaluate(state, op)  # "Will this help?"
            utility = self.utilities.get(op, 0.5)
            scored[op] = score * utility
        return sorted(scored.items(), key=lambda x: x[1], reverse=True)

    def decide(self, scored_operators):
        """Pick best or explore"""
        best_op, best_score = scored_operators[0]
        if best_score > threshold:
            return best_op
        else:
            return create_subgoal()  # Uncertain, test more

    def execute(self, operator):
        """Run it"""
        new_state = operator.run()
        return new_state

    def learn(self, trace):
        """Update rules and utilities"""
        if trace.success:
            # New rule
            rule = extract_from_trace(trace)
            self.rules.add(rule)

            # Higher utility
            for op in trace.operators_used:
                self.utilities[op] += 1
        else:
            # Lower utility
            for op in trace.operators_used:
                self.utilities[op] -= 0.5

    def run_cycle(self, input_problem):
        state = self.perceive(input_problem)
        operators = self.elaborate(state)
        scored = self.evaluate(state, operators)
        op = self.decide(scored)
        new_state = self.execute(op)
        trace = Trace(state, op, new_state)
        self.learn(trace)
        return new_state
```

---

## Why Both?

### Approach A Strengths
- ✅ Minimal changes to existing infrastructure
- ✅ Works with current LLM agents
- ✅ Pattern learning is natural for neural nets
- ✅ Quick to prototype

### Approach A Weaknesses
- ❌ Still bottlenecked by LLM's reasoning limits
- ❌ Small model is pattern-matching, not reasoning
- ❌ Low explainability (can't see what pattern was learned)
- ❌ Non-portable (rules are in neural weights)

### Approach B Strengths
- ✅ Explicit reasoning (everyone understands decision path)
- ✅ True learning (rules capture understanding)
- ✅ Highly portable (rules are JSON)
- ✅ Proven approach (40+ years of SOAR research)
- ✅ Scales to complex problems (chess, debugging, planning)

### Approach B Weaknesses
- ❌ Requires architectural changes
- ❌ More complex to implement initially
- ❌ Rule extraction is non-trivial
- ❌ Integration with LLM ecosystem needs thought

---

## The Recommendation

### Start With: Approach B (SOAR-based)

**Why**:
1. Better alignment with WS1 (symbolic rules are portable)
2. Better alignment with WS3 (framework-agnostic architecture)
3. Proven approach (40+ years of cognitive science)
4. Enables true emergent reasoning (not just pattern matching)
5. More transparent (explainable decisions)

### Then Explore: Hybrid (SOAR + Small Model)

By month 6, integrate both:
- SOAR provides explicit rules + reasoning
- Small model learns implicit patterns
- Each improves the other
- Best of both worlds

---

## What You Need to Understand

**Approach A is**: "Teach a small neural network to predict which strategies work"

**Approach B is**: "Build an agent that reasons about what to do, captures successful strategies as rules, and improves those rules through experience"

**SOAR is not magic**—it's just:
1. Systematic reasoning (state → operators → evaluation → decision)
2. Automatic learning (capture what worked)
3. Utility tracking (remember success rates)
4. Repeating the cycle

---

## Next Steps

### If You Want SOAR Deep Dive
Read: `/home/hamr/Documents/PycharmProjects/OneNote/smol/agi-problem/core-research/WS2-SOAR-IMPLEMENTATION-APPROACHES.md`

This has:
- Detailed SOAR cycle breakdown
- Three implementation options (rule engine, LangGraph, native)
- Code examples
- Research questions
- Phase-by-phase plan

### If You Want Both Approaches Side-by-Side
Check updated: `WS2-EMERGENT-REASONING-RESEARCH-PLAN.md`

This has:
- Approach A (small model) - existing content
- Approach B (SOAR) - new section added
- Comparison matrix
- Hybrid approach
- Recommendation

---

## The Bottom Line

**You don't need to choose—use both**

- **Approach A** for practical, quick learning from trajectories
- **Approach B** for principled, explainable, portable reasoning

By month 6, you'll have evidence which works better, or how to combine them optimally.

