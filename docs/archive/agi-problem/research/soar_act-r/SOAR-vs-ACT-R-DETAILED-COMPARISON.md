# SOAR vs. ACT-R: Complete Comparison
## Why Both Matter and How They Differ

**Date**: December 5, 2025
**Status**: Detailed Architecture Comparison
**Purpose**: Understand both approaches and how they solve different problems

---

## Executive Summary

| Aspect | **SOAR** | **ACT-R** |
|--------|---------|----------|
| **Core Model** | Problem-space search | Modular coordination |
| **When uncertain** | Creates sub-goals to resolve | Produces probabilistic decisions |
| **Learning** | Capture successful traces as rules | Update rule utilities based on success |
| **Best for** | Complex deliberate reasoning (chess, debugging, planning) | Realistic human-like behavior (learning, adaptation) |
| **Memory** | Episodic (what happened) + Semantic | Declarative (facts) + Procedural (how-to) |
| **Reasoning style** | Exhaustive search when needed | Quick heuristic + fallback |

**The key insight**: They're **complementary approaches** to the same problem. A hybrid system uses both.

---

## SOAR: The Problem-Space Architecture

### Core Concept

**SOAR** = State, Operator, And Result

**Philosophy**: All intelligent behavior is problem-space search.

When you face a problem:
```
Current State → [Identify operators] → [Evaluate] → [Select best] → [Execute] → New State
                                                            ↓
                                                     [Learn: capture successful trace]
```

### The SOAR Decision Cycle (7 Phases)

#### 1. INPUT: Raw Problem

```
Engineer sees: "Function returns null sometimes"
SOAR perceives: Raw input signal
```

#### 2. PERCEPTION → STATE REPRESENTATION

```
Parse input into working memory (structured state):

{
  "state_type": "debugging",
  "problem": "function_returns_null",
  "goal": "find_root_cause",
  "context": {
    "function_name": "getUserById",
    "error_location": "database_query",
    "previous_attempts": ["check_null_safety"]
  },
  "knowledge_base": {
    "db_connected": true,
    "test_data_exists": true
  }
}
```

**SOAR's view**: Current situation + goal = problem-space location

#### 3. ELABORATION: What can I do?

Query production rules: "If I see THIS state, what operators are applicable?"

```
Rule 1: IF state.type == "debugging" AND goal == "find_root_cause"
        AND error.location == "database_query"
        THEN propose operator "check_if_query_returns_empty"

Rule 2: IF state.type == "debugging" AND goal == "find_root_cause"
        AND db_connected == true
        THEN propose operator "test_query_with_sample_data"

Rule 3: IF state.type == "debugging" AND ALL_OTHER_OPERATORS_FAILED
        THEN propose operator "add_debug_logging"

Operators generated:
├─ "check_if_query_returns_empty"
├─ "test_query_with_sample_data"
└─ (Rule 3 not yet applicable)
```

**What SOAR did**: Searched long-term memory (rules) to find applicable operators

#### 4. PROPOSAL: Which operators are relevant?

Filter operators by relevance to current goal.

```
All proposed operators:
├─ "check_if_query_returns_empty" ← relevant (directly addresses goal)
├─ "test_query_with_sample_data" ← relevant
└─ (imaginary) "optimize_indexes" ← NOT relevant (goal is find root cause, not optimization)

Final candidates:
├─ "check_if_query_returns_empty"
└─ "test_query_with_sample_data"
```

#### 5. EVALUATION: Which is best?

For each operator, predict outcome and score.

```
Operator: "check_if_query_returns_empty"
  - Likelihood to help: 0.85 (very likely)
  - Historical success rate: 0.80 (worked 80% of past debugging problems)
  - Combined score: 0.85 * 0.80 = 0.68

Operator: "test_query_with_sample_data"
  - Likelihood to help: 0.70
  - Historical success rate: 0.60
  - Combined score: 0.70 * 0.60 = 0.42

Best operator: "check_if_query_returns_empty" (0.68)
```

#### 6. DECISION: What to do?

Is the best option clearly better?

```
Best score: 0.68
Second best: 0.42
Margin: 0.26 (significant)

Decision: Execute best operator
```

**What if tied?** Create sub-goal to explore deeper:

```
If scores too close (0.68 vs 0.65):
  → Create sub-goal: "Which operator would help most?"
  → Deep search / test-time compute
  → Spend extra compute to resolve uncertainty
  → Learn from the comparison
```

#### 7. EXECUTION & LEARNING

Execute selected operator and observe result:

```
Execute: "check_if_query_returns_empty"
  → Run: db.query(test_id) → See what returns
  → Result: Empty ResultSet

New state:
{
  "state_type": "debugging",
  "problem": "query_returns_empty",
  "knowledge": {
    "query_works": false,
    "cause_likely": "no_test_data OR query_wrong"
  }
}
```

**If successful** (bug found or significantly advanced):

```
Learning phase:
1. Capture the successful trace as a NEW RULE:
   "IF debugging database query issue
    AND query returns empty
    THEN check if test data was created"

2. Increase utility of "check_if_query_returns_empty":
   Success rate: 0.80 → 0.85

3. Store rule in long-term memory for next time
```

**If unsuccessful** (wrong direction):

```
Learning phase:
1. Decrease utility of failed operator:
   Success rate: 0.80 → 0.70

2. Create sub-goal to understand why it failed:
   "Why didn't checking for empty query help?"
   → Triggers SOAR cycle to investigate

3. Learn that this approach doesn't work for this problem type
```

### SOAR's Key Mechanism: Impasse Resolution

**When SOAR gets stuck** (multiple equally-good operators):

```
Scenario: Two operators have equal scores (0.65 vs 0.64)
Problem: Can't decide which to try first

SOAR's response:
├─ Create sub-goal: "Which operator is better?"
├─ Deep search: Try BOTH operators in simulation
├─ Compare outcomes
├─ Learn: "For this type of problem, operator A works better"
└─ Next time: Won't get stuck (has learned preference)

Cost: More computation now, but faster decisions later
Benefit: Knowledge accumulation through deliberate exploration
```

### SOAR Summary

```
SOAR = Systematic Problem-Space Search + Learning

When uncertain → Explores deeper
Mechanism: Rules (IF-THEN) + Utilities (success rates) + Sub-goals (deeper search)
Learning: Automatic capture of decision traces as new rules
Scale: Handles chess, robotics, debugging, planning across domains
```

---

## ACT-R: The Modular Architecture

### Core Concept

**ACT-R** = Adaptive Control of Thought - Rational

**Philosophy**: Intelligence emerges from specialized modules coordinating rationally.

Unlike SOAR (single unified engine), ACT-R has **separate systems**:

```
Perceptual Modules     ↓        Motor Modules
(See, hear)         Decision      (Hand, voice)
                    Central
                    Production
                    System
                        ↓
Declarative Memory   Procedural   Attention
(Facts, knowledge)   Memory       (Focus)
                    (How-to rules)
```

### The ACT-R Cycle (Decision-Focused)

#### 1. INPUT: Problem or situation

```
User asks: "What's the capital of France?"
ACT-R perceives: Question in visual field
```

#### 2. ENCODING: What do I attend to?

```
Attention module focuses on: "What's the capital of France?"
Perceptual module extracts: Question about capital + France

Working memory:
{
  "focus": "question",
  "content": "capital of France"
}
```

#### 3. DECLARATIVE RETRIEVAL: What do I know?

```
Production rules fire:
  "IF goal is answer question AND topic is geography
   THEN retrieve from declarative memory: capitals"

Activation spread:
  - "Paris" activates (associated with France)
  - "France" already in memory (activated)
  - Links strengthen (spreading activation)

Retrieval: "Paris" retrieved (most activated chunk)
Confidence: High (frequently used, recently reinforced)
```

#### 4. PROCEDURAL DECISION: What's the best rule to use?

```
Available production rules:
├─ Rule A: "IF question about capital THEN retrieve AND state answer"
│   Utility = (5 successes × 1.0) - (1 failure × 0.5) - 0.1 cost = 4.4
│
├─ Rule B: "IF question about capital THEN elaborate with history"
│   Utility = (2 successes × 1.0) - (3 failures × 0.5) - 0.2 cost = 0.5
│
└─ Rule C: "IF unsure THEN ask for clarification"
   Utility = (0 successes) - (0 failures) - 0.15 cost = -0.15

Best rule: Rule A (utility = 4.4)
Decision: Use Rule A
```

**Key: Utility-based conflict resolution**

When multiple rules could apply, ACT-R picks the one with highest utility = (success count × reward) - (failure count × penalty) - cost

#### 5. EXECUTION: Do it

```
Execute Rule A:
├─ State the answer: "Paris"
└─ Observe: User looks satisfied
```

#### 6. FEEDBACK & LEARNING: Update utilities

```
Result: Success!

Update Rule A's utility:
├─ Successes: 5 → 6
├─ New utility: (6 × 1.0) - (1 × 0.5) - 0.1 = 5.4
├─ Confidence in rule increases
└─ Next geography question: Will use this rule again faster

Update Rule B's utility:
├─ Not used this time (no update)
└─ Remains at 0.5 (slowly decays if not used)
```

### ACT-R's Key Mechanism: Activation Decay

**Memory works like real human memory** (forgets unreliable info):

```
"Paris is capital of France"
├─ First time: Weak activation (just learned)
├─ Used 10 times: Strong activation (reliable)
├─ Not used for year: Weaker activation (might not remember)
├─ Never used/failed often: Very weak (might forget)

Retrieval time proportional to activation:
├─ High activation: Retrieved instantly
├─ Low activation: Takes longer
├─ Zero activation: Can't retrieve
```

**Why this matters**:
- System forgets unreliable information
- Reliable knowledge (used frequently) stays strong
- Implements natural learning decay

### ACT-R's Modular Approach

Unlike SOAR (one decision cycle), ACT-R **coordinates independent modules**:

```
Scenario: Reading a sentence on screen

1. Visual Module
   Sees: "The cat sat on the mat"

2. Declarative Module
   Activates: "cat" (animal), "sat" (past tense)

3. Procedural Module (Rules)
   IF noun THEN check if familiar
   IF familiar THEN continue

4. Attention Module
   Shifts to: Next word "on"

5. Loop: Repeats for each word
   Result: Understands sentence
```

Each module works **independently but rationally**, producing overall intelligent behavior through coordination.

### ACT-R Summary

```
ACT-R = Modular Coordination + Utility-Based Learning

When uncertain → Uses probabilistic conflict resolution
Mechanism: Production rules (IF-THEN) with utilities + Activation decay
Learning: Successful rules get higher utility, failed rules get lower
Scale: Handles reading, math, games, expertise development
```

---

## SOAR vs. ACT-R: Side-by-Side

### Problem-Solving Approach

#### SOAR: Deliberate Search

```
"I'm not sure which approach will work"
    ↓
"Let me create a sub-goal to explore both options"
    ↓
"Deep search / test-time compute"
    ↓
"Learn which works better"
    ↓
"Next similar problem: know which to use"

Cost: Extra computation now
Benefit: Better decisions next time
Style: Thorough, explores uncertainty
```

#### ACT-R: Quick Heuristic

```
"Rule A has utility 0.8, Rule B has 0.6"
    ↓
"Use Rule A (higher utility)"
    ↓
"If it fails, feedback updates utilities"
    ↓
"Next similar problem: utilities guide choice again"

Cost: No extra computation
Benefit: Fast decisions
Style: Quick, adaptive through feedback
```

### Learning Mechanism

#### SOAR: Trace-Based Learning

```
Problem solving trace:
  State A → [Operator 1] → State B → [Operator 2] → Goal

Learning:
  New Rule: "For state A, Operator 1 leads toward goal"

When rule used again:
  Utility increases if leads to goal again
```

**Learning from**: Complete problem-solving paths

#### ACT-R: Utility-Based Learning

```
Rule success:
  "IF question about X THEN retrieve X" → Success

Learning:
  Utility += 1 (success count increases)

Rule failure:
  "IF question about X THEN elaborate" → Failure

Learning:
  Utility -= 0.5 (failure count increases)
```

**Learning from**: Outcome feedback on each rule

### Memory Organization

#### SOAR Memory

```
Working Memory: Current state representation
├─ What's the situation right now?
├─ What's my goal?
└─ What constraints apply?

Long-Term Memory:
├─ Production Rules: IF state THEN operator
├─ Utilities: Success rates of operators
└─ Semantic Knowledge: Facts about domain
```

#### ACT-R Memory

```
Declarative Memory (Facts):
├─ "Paris is capital of France" (chunk)
├─ "Einstein developed relativity" (chunk)
└─ Activation: How often used, how recent

Procedural Memory (How-to):
├─ Production rules: IF goal THEN action
├─ Utilities: Success rates
└─ Learning: Update based on outcomes

Attention: What's in focus right now
```

---

## Where Each Excels

### SOAR Excels At

✅ **Chess and strategic games**
- Deep search when uncertain
- Learns better strategies
- Improves over games

✅ **Debugging and problem-solving**
- Systematic exploration
- Learns solution paths
- Explains decision process

✅ **Planning and scheduling**
- Creates detailed plans
- Handles constraints
- Improves plan quality

✅ **Complex reasoning**
- Explores alternatives when needed
- Transparent decision path
- Learns general principles

### ACT-R Excels At

✅ **Learning from practice**
- Utilities naturally improve with experience
- Captures expertise development (novice → expert)
- Realistic human-like learning curves

✅ **Rapid decision-making**
- Quick probabilistic choices
- No deep search needed
- Fits human speed

✅ **Realistic human behavior**
- Predicts human reaction times
- Models error patterns
- Captures forgetting

✅ **Modular flexibility**
- Add new modules for new capabilities
- Modules work independently
- Easy to extend

---

## Hybrid Approach: Using Both

### When to Use SOAR

```
Situation: High stakes, complex problem, time available
Approach: Deep search, explore uncertainty, learn thoroughly

Example: Chess, debugging, planning, reasoning about novel problems
```

### When to Use ACT-R

```
Situation: Rapid decision needed, familiar problem
Approach: Quick heuristic, learn from feedback, adapt utilities

Example: Familiar tasks, skill development, time-constrained decisions
```

### Optimal Hybrid

```
System Architecture:

For each problem:
  1. Try ACT-R rules first (quick decision)
     If confidence high (utility > 0.8):
       Use the rule
     Else:
       Fall back to SOAR

  2. SOAR deep search (when uncertain)
     Explore alternatives
     Learn outcomes
     Update ACT-R utilities for next time

Result:
  Fast decisions when confident
  Thorough reasoning when uncertain
  Learning from both paths
```

---

## Implementation Strategy for Both

### Option 1: SOAR-Dominant (Complex Problems)

```
Use SOAR for:
├─ Problem decomposition
├─ Operator generation (what can I do?)
├─ Deep search when uncertain
└─ Rule learning

Use ACT-R for:
├─ Rapid filtering (is this relevant?)
├─ Quick scoring (how good is this?)
└─ Utility tracking (remember what worked)
```

**Best for**: Reasoning-heavy tasks (debugging, planning, strategic decisions)

### Option 2: ACT-R-Dominant (Learning Tasks)

```
Use ACT-R for:
├─ Rapid decision-making
├─ Utility-based learning
├─ Skill development
└─ Expertise building

Use SOAR for:
├─ Resolve ambiguity (when tied utilities)
├─ Deeper analysis when needed
└─ Explore new alternatives
```

**Best for**: Learning and adaptation (acquiring expertise, rapid feedback)

### Option 3: Truly Integrated (Ideal)

```
Unified Architecture:

┌─────────────────────────────┐
│  Perception (LLM grounds)   │
└──────────────┬──────────────┘
               ↓
┌─────────────────────────────┐
│  SOAR: State representation │
│  ACT-R: Module coordination │
│  Hybrid: Problem search     │
└──────────────┬──────────────┘
               ↓
┌─────────────────────────────┐
│  ACT-R: Quick decision      │
│  SOAR: Deep search when tie │
└──────────────┬──────────────┘
               ↓
┌─────────────────────────────┐
│  Execution: Tools/APIs      │
└──────────────┬──────────────┘
               ↓
┌─────────────────────────────┐
│  Learning (both)            │
│  - SOAR: Rule capture       │
│  - ACT-R: Utility update    │
└─────────────────────────────┘
```

Both contribute to learning and decision-making

---

## Why Your WS2 Should Consider Both

### SOAR Advantages for Your Research

✅ Explicit reasoning (matches WS1 portability goal)
✅ Transparent decision paths (explainable)
✅ Learns rules (symbolic, portable)
✅ Proven on complex tasks
✅ Naturally integrates test-time compute (sub-goals)

### ACT-R Advantages for Your Research

✅ Realistic learning curves (measurable improvement)
✅ Modular (fits with WS3 framework independence)
✅ Utility-based (clear success metrics)
✅ Natural expertise development
✅ Familiar to cognitive scientists (easier publishing)

### Recommendation: Hybrid Approach

```
WS2 Architecture:

Phase 1 (Proof of concept):
  Implement SOAR
  ├─ State parser (LLM grounds problem)
  ├─ Rule elaboration (what can I do?)
  ├─ LLM evaluation (which is best?)
  └─ Learning system (capture traces)

Phase 2 (Hybrid integration):
  Add ACT-R modules
  ├─ Utilities for operators (SOAR + ACT-R)
  ├─ Rapid conflict resolution (ACT-R style)
  ├─ Modular coordination
  └─ Dual learning (rules + utilities)

Result:
  SOAR's reasoning + ACT-R's learning
  Best of both worlds
```

---

## Conclusion

**SOAR**: Best for reasoning and complex problem-solving
**ACT-R**: Best for learning and adaptation
**Optimal**: Use both together

For your WS2 research:
1. Start with SOAR (reasoning framework)
2. Add ACT-R utilities (learning framework)
3. Create hybrid system
4. Measure: reasoning quality + learning curve
5. Publish findings on both

Neither is "better"—they're complementary. Your research opportunity is showing how to combine them with modern LLMs.
