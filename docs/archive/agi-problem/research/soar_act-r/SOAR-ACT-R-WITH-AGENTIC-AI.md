# SOAR/ACT-R Integration with Agentic AI
## How Cognitive Architectures Work With Agent Frameworks

**Date**: December 5, 2025
**Question**: How would SOAR or ACT-R be used with agentic AI? Does it break every prompt and run it through all this, or passively capture?

**Answer**: Both, in different ways. This document explains the integration patterns.

---

## The Core Insight

SOAR/ACT-R are **NOT separate from the agent**—they ARE the agent's decision-making engine.

Think of it like this:

```
WRONG WAY (separating):
User prompt → Agent (runs normally) → Result
          ↓ (separate)
       SOAR/ACT-R (analyzes after)

RIGHT WAY (integrated):
User prompt → SOAR/ACT-R agent (integrated reasoning) → Result
```

---

## Part 1: SOAR as Agentic Framework

### How It Works with Prompts

#### Scenario: User Gives Agent a Task

```
User: "Help me debug why my database query returns null for user_id=42"

Flow:
  ↓
[SOAR Agent receives prompt]
  ├─ Perceive: Parse prompt to state
  │   {goal: debug, issue: null_return, context: database}
  │
  ├─ Elaborate: Query rules → what can I do?
  │   [check_database, trace_execution, test_data, ...]
  │
  ├─ Evaluate: Which operator is best?
  │   (Uses both semantic scoring + historical utilities)
  │
  ├─ Decide: Select operator or explore
  │   (If confident: execute; if tied: test both)
  │
  ├─ Execute: Run operator
  │   check_database_query() → observe result
  │
  └─ Learn: Update rules + utilities automatically
      (Success → new rule + higher utility)

Result to user: "Found issue: Query returns empty because..."
```

### NOT Per-Prompt Breakdown

SOAR doesn't "break every prompt" into steps. Instead:

```
Misconception:
  "Parse prompt → SOAR step 1 → SOAR step 2 → ..."
  (Linear processing, overhead for each step)

Reality:
  "Parse prompt → SOAR runs internally until done"
  (Prompt enters state, cycles until goal achieved)
```

### SOAR Agent Cycles (Multiple Iterations)

One prompt might trigger **multiple SOAR cycles**:

```
Prompt: "Debug the database issue"

SOAR Cycle 1:
  Proposal: [check_query, trace_execution, test_data]
  Decision: Execute check_query
  Result: "Query returns empty"

SOAR Cycle 2:
  Proposal: [check_test_data, check_query_syntax]
  Decision: Execute check_test_data
  Result: "Test data not created"

SOAR Cycle 3:
  Proposal: [create_test_data, verify_connection]
  Decision: Execute create_test_data
  Result: Success - data created

SOAR Cycle 4:
  Goal achieved: Root cause found
  Cycles stop

Return to user: Complete analysis with root cause
```

**Key**: The cycles happen **inside the agent**, not exposed to user or framework.

---

## Part 2: Integration Patterns

### Pattern 1: SOAR as Core Reasoning Engine

```
LangGraph / LangChain / CrewAI
        ↓
    [Agent Node]
        ↓
┌─────────────────────────────┐
│  SOAR Agent (Core)          │
├─────────────────────────────┤
│ 1. Perceive state           │
│ 2. Elaborate operators      │
│ 3. Evaluate + rank          │
│ 4. Decide (or sub-goal)     │
│ 5. Execute tool/function    │
│ 6. Learn (rule + utility)   │
└─────────────────────────────┘
        ↓
   Return result to framework
```

**In LangGraph**:
```python
class SOARAgentNode:
    def __init__(self):
        self.rules = load_rules("rules.json")
        self.utilities = load_utilities("utilities.json")

    def __call__(self, state):
        # SOAR runs entirely here
        while not goal_achieved(state):
            operators = self.elaborate(state)  # What can I do?
            scores = self.evaluate(operators)   # Which is best?
            op = self.decide(scores)            # Commit to action
            state = self.execute(op, state)     # Do it
            self.learn(state)                   # Remember it

        return state

# In graph
graph.add_node("soar_agent", SOARAgentNode())
```

### Pattern 2: Passive Learning During Normal Agent Execution

This is where "passive capture" happens:

```
Normal Agent Execution (LangGraph):

┌────────────────────┐
│ User Prompt        │
└─────────┬──────────┘
          ↓
┌────────────────────────────────┐
│ Normal Agent Flow              │
│ (LLM → ReAct/CoT → Tool call)  │
└─────────┬──────────────────────┘
          ↓
┌────────────────────────────────┐
│ Trace Captured Passively       │ ← CAPTURE HERE
│ {problem, approach, result}    │
└─────────┬──────────────────────┘
          ↓
┌────────────────────────────────┐
│ Learning System (Runs async)   │ ← LEARN LATER
│ Extract rules from trace       │
│ Update utilities               │
│ Save to knowledge base         │
└────────────────────────────────┘
          ↓
┌────────────────────────────────┐
│ Result to User                 │
└────────────────────────────────┘
```

**Timing**: The trace capture happens **while agent executes**, but learning happens **asynchronously** (doesn't block execution).

```python
# Pseudocode
async def run_agent(prompt):
    # Normal agent execution
    result = await agent.run(prompt)

    # Passively capture trace
    trace = agent.get_trace()  # What did it do?

    # Queue learning (doesn't block)
    asyncio.create_task(learn_from_trace(trace))

    return result  # Return immediately
```

---

## Part 3: Two Integration Strategies

### Strategy A: SOAR Replaces Agent (Active Reasoning)

```
Architecture:
  User Prompt
       ↓
  SOAR Agent
  ├─ Perceive
  ├─ Elaborate (call rules)
  ├─ Evaluate (may call LLM for scoring)
  ├─ Decide
  └─ Execute (call tools)
       ↓
  Result

Characteristics:
  - SOAR is the core reasoning
  - Every decision goes through SOAR cycle
  - Learning is active (after each decision)
  - High reasoning quality
  - Can explore (sub-goals when uncertain)

Use case: Complex problems needing deep reasoning
Timeline: Slower (multiple cycles) but more thorough
```

**Example: Debugging Task**

```
Prompt: "Why does login fail for user@example.com?"

SOAR Cycles:
  1. Check database connection → Connected ✓
  2. Check user exists → Not found
  3. Check signup process → User not in DB
  4. Root cause: User hasn't completed signup

Result: "User hasn't completed signup process"
Time: 4 cycles, 2 minutes (deliberate reasoning)
Quality: High (explored alternatives)
```

### Strategy B: Normal Agent with Passive Learning (Learning Layer)

```
Architecture:
  User Prompt
       ↓
  Normal LLM Agent (ReAct/CoT)
  ├─ LLM thinks
  ├─ Takes action
  └─ Observes result
       ↓
  Trace Capture (Passive)
  ├─ What did we try?
  ├─ Did it work?
  └─ What can we learn?
       ↓
  Learning System (Background)
  ├─ Extract rules from successful traces
  └─ Update utilities
       ↓
  Result
       ↓
  Next time similar problem:
  Small model / rules suggest better approach

Characteristics:
  - Agent runs normally (fast)
  - Learning happens in background (async)
  - Rules accumulate over time
  - Improves with each problem
  - No slowdown to user

Use case: Fast operations, continuous improvement
Timeline: Fast (normal agent speed)
Quality: Improves over time
```

**Example: Customer Support**

```
First time:
  Prompt: "Customer reports cannot login"
  Agent: Uses Trial-and-error (ReAct)
  Time: 3 minutes
  Learning: Traces captured

Second time:
  Prompt: "Another customer cannot login"
  Agent: Runs normally
  But: Rules suggest "Check account status first"
  Time: 1.5 minutes (faster because better approach)

After 100 similar problems:
  Rules optimized through 100 successes/failures
  Average time: 30 seconds (highly optimized)
```

---

## Part 4: Hybrid (Both Active + Passive)

### Best of Both Worlds

```
Architecture:

User Prompt
    ↓
Router: Is this a known problem type?
├─ YES (high confidence): Use fast path
│  ├─ Passive learning (normal agent)
│  └─ Rules suggest best approach
│
└─ NO (novel problem): Use reasoning path
   ├─ Active SOAR reasoning
   ├─ Explores alternatives
   └─ Learns new rules
    ↓
Result
    ↓
Knowledge Base Updated
├─ New rules added (from novel reasoning)
└─ Utilities updated (from passive learning)
```

**Example: Help Desk Agent**

```
Ticket 1: "Can't login"
  → Known problem, use fast path
  → Rules suggest: Check account status
  → Passive learning captures trace
  → Time: 30 seconds

Ticket 2: "Can't access specific feature"
  → Novel problem, use reasoning path
  → SOAR explores: Check permissions, features, limits
  → Explores multiple hypotheses
  → Finds cause: User tier doesn't include feature
  → Learns new rule: "Feature access → check user tier"
  → Time: 3 minutes

Ticket 3: "Can't access specific feature (different user)"
  → Now known problem (learned from ticket 2)
  → Uses fast path + learned rule
  → Time: 30 seconds
```

---

## Part 5: How Rules Are Captured

### During Normal Agent Execution

```
Agent running on prompt: "Debug database issue"

What gets captured (Trace):
{
  "input": "Why does query return null for user_id=42?",
  "state": "debugging",
  "approaches_tried": [
    {
      "approach": "check_database_connection",
      "result": "connected",
      "useful": true
    },
    {
      "approach": "check_query_syntax",
      "result": "valid",
      "useful": false
    },
    {
      "approach": "check_test_data",
      "result": "no_test_data",
      "useful": true,
      "root_cause": true
    }
  ],
  "outcome": "success",
  "time": 180,
  "problem_type": "database_null_debugging"
}

Rule extracted (auto):
IF problem_type == "database_null_debugging"
AND involves database query
THEN try "check_test_data" approach first
WITH utility 0.95
```

### Passive Capture Mechanics

```python
class PassiveTraceCapture:
    def __init__(self, agent):
        self.agent = agent
        self.traces = []

    def run(self, prompt):
        # Start capturing
        with self.capture():
            result = self.agent.execute(prompt)

        # Trace automatically recorded
        trace = self.current_trace
        self.traces.append(trace)

        # Queue async learning
        self.queue_learning(trace)

        return result

    def capture(self):
        """Context manager that captures all agent actions"""
        # Hooks into: LLM calls, tool calls, results
        # Records: what was tried, did it work?
        return self

    def queue_learning(self, trace):
        """Async learning - doesn't block user"""
        asyncio.create_task(self._learn(trace))

    async def _learn(self, trace):
        # Extract rule from trace
        rule = self.extract_rule(trace)

        # Update utilities
        self.update_utilities(trace)

        # Save to persistent storage
        self.save_rules()
```

---

## Part 6: ACT-R Integration Pattern

### ACT-R Works Differently (More Implicit)

ACT-R doesn't need explicit rule extraction—utilities update continuously:

```
Agent execution:

Step 1: Agent encounters problem
  ├─ Retrieves relevant knowledge chunks
  └─ Activation based on past success

Step 2: Agent makes decision
  ├─ Multiple production rules available
  └─ Highest utility rule selected automatically

Step 3: Agent executes and gets result
  ├─ Success: Utility increases
  └─ Failure: Utility decreases

Step 4: Next similar problem
  ├─ Most successful rule has highest utility
  └─ Gets selected immediately (faster decisions)

Learning is automatic, implicit in utility scores
No explicit "rule extraction" needed
```

**Passive Learning with ACT-R**:

```python
class ACTRAgent:
    def execute(self, prompt):
        # Agent runs normally
        result = self._run(prompt)

        # ACT-R learning happens implicitly
        # Utilities already updated based on success/failure
        # No extra code needed

        return result

    def _run(self, prompt):
        # Decode input
        chunks = self.perceive(prompt)

        # Get relevant production rules
        rules = self.get_applicable_rules(chunks)

        # Rules compete by utility
        best_rule = max(rules, key=lambda r: r.utility)

        # Execute best rule
        result = best_rule.execute()

        # Update utilities (automatic learning)
        if successful(result):
            best_rule.utility += REWARD
        else:
            best_rule.utility -= PENALTY

        return result
```

---

## Part 7: Per-Prompt vs. Continuous Learning

### Question: Does it process every prompt?

**Answer**: Yes, but efficiently:

#### For SOAR (Active Reasoning)

```
Every prompt triggers SOAR cycle(s):

Prompt 1 → SOAR cycle 1 → SOAR cycle 2 → Result 1
Prompt 2 → SOAR cycle 1 → Result 2
Prompt 3 → SOAR cycle 1 → SOAR cycle 2 → SOAR cycle 3 → Result 3

Cost:
  - Reasoning happens every prompt
  - Cycles continue until goal achieved
  - Each cycle: elaborate, evaluate, decide, execute
  - Moderate overhead, high reasoning quality
```

#### For Passive Learning (Background)

```
Every prompt TRACES (not SOAR):

Prompt 1 → Normal agent → Trace captured → Result 1
          ├─ (learning queued, doesn't block)

Prompt 2 → Normal agent → Trace captured → Result 2
          ├─ (learning queued, doesn't block)

Prompt 3 → Normal agent → Trace captured → Result 3
          ├─ (learning queued, doesn't block)

Cost:
  - Zero overhead to user (agent runs normally)
  - Trace capture lightweight (just recording)
  - Learning happens async (background job)
  - Accumulates over time
```

#### Hybrid (Smart Routing)

```
Prompt 1 (novel problem) → SOAR reasoning (3 minutes) → Learn rule
Prompt 2 (known problem) → Normal agent (30 seconds) → Trace captured
Prompt 3 (novel problem) → SOAR reasoning (2 minutes) → Learn rule
Prompt 4 (problem like 1) → Normal agent + rule (30 seconds) → Trace

Cost:
  - SOAR only for truly novel problems
  - Normal agent for familiar problems
  - Rules guide toward better decisions
  - Learns from both reasoning and normal execution
```

---

## Part 8: Real Implementation Patterns

### Pattern 1: LangGraph with SOAR Core

```python
from langgraph.graph import StateGraph, END
import json

class SOARNode:
    def __init__(self):
        self.rules = json.load(open("rules.json"))
        self.utilities = json.load(open("utilities.json"))

    def elaborate(self, state):
        """Generate operators by matching rules"""
        operators = []
        for rule in self.rules:
            if self._matches(rule.condition, state):
                operators.append(rule.operator)
        return operators

    def evaluate(self, operators, state):
        """Score each operator"""
        scores = {}
        for op in operators:
            # LLM scores semantic fit
            semantic = self.llm_score(op, state)
            # Utilities provide historical info
            historical = self.utilities.get(op, 0.5)
            scores[op] = semantic * historical
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)

    def decide(self, ranked_ops):
        """Select or explore"""
        best, score = ranked_ops[0]
        second, score2 = ranked_ops[1] if len(ranked_ops) > 1 else (None, 0)

        if score - score2 > 0.15:  # Clear winner
            return best
        else:  # Tie - explore both (sub-goal)
            return self.create_subgoal(ranked_ops)

    def __call__(self, state):
        """SOAR agent node"""
        while not self._goal_achieved(state):
            ops = self.elaborate(state)
            ranked = self.evaluate(ops, state)
            op = self.decide(ranked)
            state = self._execute_operator(op, state)
            self._update_utilities(state)

        return state

# Graph setup
graph = StateGraph()
graph.add_node("soar", SOARNode())
graph.add_edge("start", "soar")
graph.add_edge("soar", END)
```

### Pattern 2: Passive Trace Capture

```python
class TraceCapturingAgent:
    def __init__(self, base_agent):
        self.agent = base_agent
        self.traces = []

    def run(self, prompt):
        # Capture what agent does
        with self._tracer() as tracer:
            result = self.agent.run(prompt)

        trace = tracer.get_trace()
        self.traces.append(trace)

        # Queue learning (async, doesn't block)
        self._queue_learning(trace)

        return result

    def _tracer(self):
        """Context manager that hooks into LLM, tools"""
        return TraceRecorder(self.agent)

    def _queue_learning(self, trace):
        """Queue learning as background job"""
        # Extract rule from successful trace
        if trace.success:
            rule = self._extract_rule(trace)
            self._save_rule(rule)

        # Update utilities
        self._update_utilities(trace)

    def _extract_rule(self, trace):
        """IF this problem type THEN try this approach"""
        return {
            "condition": {
                "problem_type": trace.problem_type,
                "characteristics": trace.key_features
            },
            "action": trace.successful_approach,
            "utility": 1.0 if trace.success else 0.0,
            "created": datetime.now(),
            "source": "traced_execution"
        }
```

### Pattern 3: Hybrid Router

```python
class HybridAgent:
    def __init__(self, soar_agent, normal_agent, rules):
        self.soar = soar_agent
        self.normal = normal_agent
        self.rules = rules

    def run(self, prompt):
        # Classify problem
        problem_type = self._classify(prompt)

        # Check if we have rules for this
        known_approach = self._find_rule(problem_type)

        if known_approach and self._confidence(known_approach) > 0.8:
            # Known problem - use fast path
            result = self.normal.run(prompt, hint=known_approach)
            # Passively capture
            self._capture_trace(prompt, result)
        else:
            # Novel problem - use reasoning path
            result = self.soar.run(prompt)
            # Learn from reasoning
            self._learn_from_result(prompt, result)

        return result

    def _find_rule(self, problem_type):
        """Find applicable rule"""
        for rule in self.rules:
            if rule.applies_to(problem_type):
                return rule.action
        return None
```

---

## Part 9: Overhead Analysis

### Per-Prompt Processing

```
SOAR Active Reasoning:
  Per prompt overhead: 2-5 cycles × (elaborate + evaluate + decide)
  Time: 1-5 minutes (deliberate)
  Benefit: High quality reasoning, learns rules

Passive Learning:
  Per prompt overhead: ~1% (trace capture only)
  Time: <1 second extra
  Benefit: Accumulates knowledge over time

Hybrid:
  Per prompt overhead: varies
  - Known problems: ~1% (fast path)
  - Novel problems: 2-5 minutes (reasoning path)
  Average: Depends on problem distribution
```

### Asymptotic Improvement

```
First N problems: SOAR reasoning (slow, learns rules)
├─ Problem 1: SOAR → 3 min, learns Rule 1
├─ Problem 2: SOAR → 2 min, learns Rule 2
├─ Problem 3: SOAR → 2.5 min, learns Rule 3
└─ Problem 10: SOAR → 2 min, learns Rule 10

After rules learned: Fast path with passive learning
├─ Problem 11: Normal agent + Rule 1 → 30 sec
├─ Problem 12: Normal agent + Rule 2 → 30 sec
└─ Problem 100: Normal agent + rules → 20 sec (highly optimized)

Long-term behavior:
  Early phase: High quality (SOAR), slower
  Late phase: High speed (optimized rules), maintaining quality
```

---

## Part 10: Answering Your Specific Questions

### "Would it take every prompt, break it and run it through all this?"

**SOAR**: Yes, every prompt cycles through SOAR, but not sequentially:
```
Prompt → SOAR internal cycles (elaborate→evaluate→decide→execute loop)
       → Multiple cycles until goal achieved
       → Goal met → return result
       → Learning happens at each cycle
```

**Passive Learning**: No, prompts run normally, capture happens in background:
```
Prompt → Normal agent (unchanged)
      → Trace captured (lightweight)
      → Learning queued (async, doesn't block)
      → Result returned immediately
```

### "Or would it passively capture that?"

**Answer**: Both approaches, depending on your architecture:

1. **Passive Capture Only** (Recommended for speed):
   - Agent runs normally (fast)
   - Traces captured automatically
   - Learning happens async (background)
   - Zero overhead to user
   - Improves over time

2. **Active SOAR Reasoning** (Recommended for quality):
   - Every prompt triggers SOAR reasoning
   - Deliberate decision-making at each step
   - Rules learned immediately
   - Higher overhead (slower)
   - Better initial reasoning quality

3. **Hybrid** (Recommended for balance):
   - Familiar problems: Passive capture (fast)
   - Novel problems: SOAR reasoning (quality)
   - Router decides which path
   - Scales over time

---

## Summary: Integration Architectures

```
Option 1: SOAR Replaces Agent
┌─────────────────────┐
│ User Prompt         │
└────────┬────────────┘
         ↓
┌─────────────────────┐
│ SOAR Agent          │
│ (active reasoning)  │
└────────┬────────────┘
         ↓
┌─────────────────────┐
│ Result              │
└─────────────────────┘

Cost: 1-5 min per prompt (deliberate)
Benefit: High reasoning quality
Learning: Active (per-decision)

Option 2: Passive Learning Over Normal Agent
┌─────────────────────┐
│ User Prompt         │
└────────┬────────────┘
         ↓
┌─────────────────────┐
│ Normal Agent        │
│ (unchanged speed)   │
└────────┬────────────┘
         ↓
┌─────────────────────┐
│ Trace Capture       │
│ (async learning)    │
└────────┬────────────┘
         ↓
┌─────────────────────┐
│ Result              │
└─────────────────────┘

Cost: <1% overhead
Benefit: Accumulates knowledge
Learning: Passive (traces)

Option 3: Hybrid Router (Best)
┌──────────────────────────┐
│ User Prompt              │
└────────┬─────────────────┘
         ↓
┌──────────────────────────┐
│ Router: Known or Novel?  │
└─┬──────────────────────┬─┘
  │                      │
  YES (fast)            NO (reasoning)
  ↓                      ↓
┌─────────────┐      ┌──────────────┐
│Normal Agent │      │SOAR Reasoning│
│+Rule Hint   │      │             │
└──────┬──────┘      └────────┬─────┘
       ↓                      ↓
┌─────────────────────────────────┐
│ Trace/Learn                     │
└──────────────┬──────────────────┘
               ↓
         ┌──────────┐
         │ Result   │
         └──────────┘

Cost: Varies (1% for known, 2-5min for novel)
Benefit: Speed + quality
Learning: Both active + passive
```

---

## Recommendation for Your WS2

**Start with Option 2 (Passive Learning)**:
- ✅ No overhead to user (agent runs normally)
- ✅ Easy to implement (just trace capture + async learning)
- ✅ Accumulates knowledge over time
- ✅ Rules improve agent performance without slowing it down

**Then evolve to Option 3 (Hybrid)**:
- After 100-200 problems, rules guide routing decisions
- Novel problems use SOAR reasoning (high quality)
- Known problems use fast path (high speed)
- Best of both worlds

**Don't start with Option 1** (SOAR only):
- Too much overhead if every prompt cycles through SOAR
- Better to capture and learn passively
- Use SOAR for special cases (complex/novel problems)
