# SOAR and ACT-R: Cognitive Architectures and Why They Matter For Your Research

**Date**: December 5, 2025
**Status**: Deep Dive Into Foundational Cognitive Science
**Purpose**: Understand why these 40+ year old systems matter for modern AI agent research

---

## Executive Summary

**SOAR** (developed at University of Michigan by John Laird since 1983) and **ACT-R** (developed at Carnegie Mellon by John Anderson since 1993) are the two most successful cognitive architectures ever built.

They've been used to model human cognition for 40+ years with remarkable success. Now, in 2025, AI researchers are recognizing what should have been obvious: **cognitive science knows how intelligence actually works.**

**Critical insight for your research**: These architectures solve problems that current LLM agents can't. They should be your foundational inspiration for WS2 (Emergent Reasoning).

---

## What Is A Cognitive Architecture?

A cognitive architecture is a theory about the **fundamental structures and processes that enable intelligence.**

Unlike most AI systems that are task-specific (train a model to do X), cognitive architectures are **universal frameworks for intelligence.**

**The goal**: Build ONE architecture that can handle reasoning, learning, problem-solving, planning, and decision-making across ANY domain.

SOAR and ACT-R are the only two systems to achieve this at scale.

---

## SOAR: The Problem-Space Architecture

### Foundational Concept

**SOAR** = "State, Operator, And Result"

The core insight: **All intelligent behavior can be modeled as problem-space search.**

When you encounter a problem, you:
1. **Recognize the state** (what's the current situation?)
2. **Identify operators** (what can you do?)
3. **Select an operator** (which action makes sense?)
4. **Apply it** (do it)
5. **Observe result** (what changed?)
6. **Repeat** until problem solved

### The Architecture

```
┌─────────────────────────────────────┐
│     SOAR Problem-Space Engine       │
├─────────────────────────────────────┤
│                                     │
│  Working Memory                     │
│  ├─ Current state representation    │
│  ├─ Possible operators              │
│  └─ Evaluation criteria             │
│                                     │
│  Long-Term Memory                   │
│  ├─ Production rules (if-then)      │
│  ├─ Semantic knowledge              │
│  └─ Episodic memory (experiences)   │
│                                     │
│  Decision Cycle                     │
│  1. Elaborate: What operators exist?│
│  2. Propose: Which are relevant?    │
│  3. Evaluate: Which is best?        │
│  4. Apply: Execute chosen operator  │
│  5. Learn: Update for future        │
│                                     │
└─────────────────────────────────────┘
```

### Key Mechanisms

**1. Production Rules**
```
IF (state has property X AND goal is Y)
THEN (propose operator Z)

Example:
IF (chess position AND goal is to win)
THEN (propose move that captures opponent piece)
```

Production rules are learned through experience and refined over time.

**2. Deliberate Search**
When SOAR can't decide between operators, it:
- Generates sub-problems to explore each option
- Searches the problem space deeply
- Eventually converges on best decision

**3. Automatic Learning**
Every time SOAR successfully solves a problem:
- It learns a new production rule
- Rule captures "when to use this approach"
- Rule gets stronger with repetition
- Rules compete based on success rate

**4. Impasse Resolution**
When stuck (multiple equally-good operators):
- SOAR creates sub-goals to disambiguate
- Explores outcomes of different choices
- Learns which choice is best
- Updates preferences accordingly

### What SOAR Does Well

✅ **Learns from experience** - Each successful problem-solving creates new rules
✅ **Develops strategies** - Rules become more specific and useful over time
✅ **Transfers knowledge** - Rules apply across similar problems
✅ **Handles uncertainty** - Can explore multiple paths when uncertain
✅ **Exhibits emergent behavior** - Complex behaviors emerge from simple rules
✅ **Explains decisions** - Can trace why it chose action X
✅ **Improves automatically** - No external training signal needed
✅ **Works across domains** - Same engine handles chess, driving, debugging, etc.

### Evidence of Success

SOAR has been applied to:
- Chess and game playing
- Scheduling and planning
- Robotic control
- Cognitive modeling of humans
- Language understanding
- Complex problem-solving

In every domain, SOAR learns and improves with experience.

---

## ACT-R: The Modular Architecture

### Foundational Concept

**ACT-R** = "Adaptive Control of Thought - Rational"

The core insight: **Intelligence emerges from coordinating specialized cognitive modules.**

Unlike SOAR (single problem-space engine), ACT-R has:
- Separate modules for perception, memory, attention, action
- Each module follows a rational principle (maximize utility)
- Modules coordinate to produce intelligent behavior

### The Architecture

```
┌──────────────────────────────────────────┐
│         ACT-R Modular System            │
├──────────────────────────────────────────┤
│                                          │
│  Perceptual Module        Motor Module   │
│  ├─ Visual processing      ├─ Hand/arm  │
│  └─ Auditory processing    └─ Voice     │
│                                          │
│           ↓            ↓                 │
│                                          │
│    Central Production System             │
│    ├─ Procedural Memory (how-to)         │
│    ├─ Conflict Resolution (best rule)    │
│    └─ Rule Selection (utility-based)     │
│                                          │
│           ↓            ↓                 │
│                                          │
│  Declarative Memory      Attention Focus │
│  ├─ Facts/knowledge      ├─ What's      │
│  ├─ Recent events        │  important   │
│  └─ Semantic knowledge   └─ What's next │
│                                          │
│    Utility Learning                     │
│    ├─ Track rule success                │
│    ├─ Update rule utilities             │
│    └─ Adapt strategy                    │
│                                          │
└──────────────────────────────────────────┘
```

### Key Mechanisms

**1. Production Rules (Like SOAR)**
```
IF (goal is answer question AND
    fact is in declarative memory)
THEN (retrieve fact AND state answer)

Utility = Success Rate - Cost
```

**2. Declarative Memory**
- Chunks of knowledge (facts, events, concepts)
- Activation decay (older memories weaker)
- Spreading activation (related memories activate each other)
- Retrieval: most activated chunk retrieved

**3. Utility Learning**
```
Every rule has a utility score:
Utility = (successes × reward) - (failures × penalty) - costs

When rule succeeds: utility increases
When rule fails: utility decreases
Rules compete: highest utility wins

Over time: good rules dominate, bad rules disappear
```

**4. Attention and Interaction**
- Focus on one thing at a time
- Switch attention strategically
- Build up mental models
- Use models to predict outcomes

### What ACT-R Does Well

✅ **Realistic human cognition modeling** - Predicts human performance precisely
✅ **Utility-based learning** - Rules improve through success/failure tracking
✅ **Memory dynamics** - Forgets unreliable information, retains useful knowledge
✅ **Chunking and abstraction** - Groups information into meaningful units
✅ **Expertise development** - Novice behavior → expert performance through practice
✅ **Transfer learning** - Knowledge from one domain helps similar domains
✅ **Explains behavior** - Can predict reaction times, errors, learning curves
✅ **Perceptual integration** - Coordinates visual, auditory, motor systems

### Evidence of Success

ACT-R has successfully modeled:
- Learning to read and write
- Mathematical problem-solving
- Language comprehension
- Memory experiments with remarkable precision
- Categorization and concept learning
- Strategy development in games
- Expert performance in domains like aviation

ACT-R accurately predicts human behavior including **error patterns**, **learning curves**, and **response times**.

---

## SOAR vs. ACT-R: The Differences

### Problem Space vs. Modular

| **Aspect** | **SOAR** | **ACT-R** |
|-----------|---------|----------|
| **Core Model** | Single problem-space search | Multiple specialized modules |
| **When Uncertain** | Creates sub-goals to resolve impasse | Produces probabilistic conflict resolution |
| **Memory** | Episodic (what happened) + semantic | Declarative (facts) + procedural (how-to) |
| **Learning** | Production rules from successes | Utility-based rule refinement |
| **Performance Focus** | Optimality (find best solution) | Rationality (make good decision with constraints) |

### Problem-Space Search (SOAR)

```
State A → [Which operator?] → State B → [Which next?] → Goal

When uncertain: elaborate the state space to resolve ambiguity
Learning: capture the decision path that worked
```

### Modular Coordination (ACT-R)

```
Goal → [Production rules compete] → Best rule selected
       [Based on utility: success rate - cost]
       → Action → Feedback → Update utilities

Learning: successful rules get higher utility
         failing rules get lower utility
```

### Which Is Better?

**Neither is universally better. They're different approaches:**

- **SOAR**: Better for complex deliberate reasoning (chess, planning, debugging)
- **ACT-R**: Better for realistic human-like behavior (learning, skill development, adaptation)

In practice: **You'd use both together.**
- ACT-R's modular attention for rapid decision-making
- SOAR's problem-space search for when deeper reasoning needed

---

## Why These Matter For Your Research

### 1. They Prove Reasoning Is Possible Without Neural Networks

**Critical insight**: SOAR and ACT-R are almost entirely symbolic. No deep learning. No neural networks.

Yet they:
- Solve complex problems
- Learn and improve
- Transfer knowledge
- Behave intelligently

**What this proves**: Intelligence doesn't require neural networks. It requires the right architecture.

**For your WS2 (Emergent Reasoning)**: You don't need to reinvent cognitive science. Build on 40+ years of research.

---

### 2. They Show How Learning Actually Works

Current LLM agents don't learn. They predict tokens.

SOAR and ACT-R learn by:
- **SOAR**: Capturing successful problem-solving paths as rules
- **ACT-R**: Updating rule utilities based on outcomes

Both create **persistent improvement** that survives between sessions.

**For your WS1 (Intelligence Portability)**: This shows what "learning" actually means: rules/strategies that improve with experience.

---

### 3. They Solve The Reasoning Problem

Current LLM agents "reason" by predicting tokens that sound like reasoning.

SOAR and ACT-R reason by:
- **Decomposing problems** into sub-goals
- **Evaluating alternatives** based on knowledge
- **Selecting actions** strategically
- **Executing and observing** outcomes

This is **actual reasoning**, not token prediction that mimics reasoning.

**For your WS2**: Study how SOAR resolves impasses. Study how ACT-R's utilities drive decision-making. That's real reasoning.

---

### 4. They Show How to Build Universal Systems

Both SOAR and ACT-R work across ANY domain without retraining.

Same engine handles chess, driving, debugging, language, math, etc.

This is because the architectures capture **fundamental principles of intelligence**, not domain-specific patterns.

**For your WS3 (Framework Convergence)**: Universal abstraction is possible. SOAR proves it.

---

### 5. They Explain Why Current Agents Fail

Modern agents fail on novel problems because they're token prediction systems.

SOAR agents can solve novel problems because they:
- Use problem-space search to explore unknown territory
- Apply learned rules to new situations
- Adjust when rules don't work

**For your WS2**: This explains why test-time compute (o1, r1) is just brute-force search. SOAR's approach is more elegant.

---

## The Problem: Why Aren't These Used?

If SOAR and ACT-R are so powerful, why don't we use them?

### Historical Reasons

1. **Symbol Grounding Problem** (1980s-2000s)
   - SOAR/ACT-R work with symbols
   - Real world is perception (vision, sound, touch)
   - How do you connect symbols to perceptions?
   - Deep learning solved this (finally, 2012+)

2. **Scalability Questions**
   - SOAR/ACT-R work well on small problems
   - Large-scale domains seemed out of reach
   - Deep learning proved to scale to billions of parameters

3. **Neural Networks Hype**
   - Deep learning breakthroughs were real and impressive
   - Cognitive architectures felt old-fashioned
   - Research funding shifted almost entirely to neural approaches

### Modern Context (2025)

The context has completely changed:
- We have LLMs that handle perception AND language
- We have test-time compute for reasoning
- We have massive compute resources
- We have 40+ years of cognitive science research

**Now it makes sense to combine them:**
- Use LLMs for perception/language grounding
- Use SOAR/ACT-R principles for reasoning/learning
- Hybrid systems could have both neural perception AND cognitive reasoning

---

## How To Use SOAR/ACT-R Insights For Your Research

### For WS2: Emergent Reasoning Architecture

**Learn from SOAR**:
```
Current LLM Agent:
Problem → [Predict tokens] → Answer

SOAR Agent:
Problem → [Identify state]
        → [Elaborate: what can I do?]
        → [Evaluate operators]
        → [Select best one]
        → [Apply]
        → [Observe result]
        → [Learn: add rule]

Your hybrid approach:
Problem → [Perception: LLM grounds problem]
        → [Reasoning: SOAR-like search through operators]
        → [Evaluation: Utility-based decision-making]
        → [Action: Execute]
        → [Learning: Update rules/strategies]
```

**Key insight**: Structure the reasoning with explicit stages (identify state, elaborate, evaluate, select, apply), not just predict next token.

---

### For WS1: Intelligence Portability

**Learn from ACT-R**:
- Rules are portable (if-then statements)
- Utilities are portable (success rates)
- Knowledge is structured (chunks)
- No weights to transfer (unlike neural networks)

Your portable knowledge representation could:
- Use production rules (like SOAR/ACT-R)
- Track rule utilities (what works)
- Store structured chunks (concepts, patterns)
- Transfer across models (models just execute rules)

**Key insight**: Symbolic knowledge is more portable than neural weights.

---

### For WS5: Test-Time Learning

**Learn from SOAR's impasse resolution**:
- When SOAR gets stuck, it doesn't give up
- It creates sub-goals to explore the issue
- It learns from the exploration
- Next time: doesn't get stuck (has rule)

Test-time learning should work similarly:
- When agent encounters uncertainty
- Spend more compute exploring options (test-time)
- Learn from the exploration
- Capture insights for next time (persistent)

**Key insight**: Test-time thinking should feed into persistent rules, not just predict better this time.

---

## What Research Actually Says About Combining LLMs + Cognitive Architectures

### Recent Research (2025)

**"LLM-ACTR: Bridging Cognitive Models to LLMs"**
- Researchers taking ACT-R principles
- Encoding them into LLM prompting
- Getting better performance than pure LLMs
- Learning faster than before

**"Toward Visual-Symbolic Integration in SOAR"**
- Extending SOAR with neural perception
- Using LLMs for language grounding
- Maintaining SOAR's symbolic reasoning
- Getting benefits of both systems

**"Cognitive Architectures for Language Agents (CoALA)"**
- Framework for integrating cognitive principles with LLMs
- Modular memory (like ACT-R)
- Production rules (like SOAR)
- Better learning and reasoning than pure LLM agents

### What's Working

The consensus emerging in 2025: **Hybrid systems are the future**

```
Hybrid = Neural (perception + language) + Symbolic (reasoning + learning)

Not: Replace LLMs with SOAR/ACT-R
But: Use LLMs for what they're good at (grounding, perception, language)
     Use SOAR/ACT-R principles for what they're good at (reasoning, learning)
```

---

## Implementation Strategy For Your Research

### Phase 1: Learn From The Architecture

Don't try to reimplement SOAR/ACT-R. Instead:

1. **Study the problem-space approach** (SOAR)
   - How it identifies states
   - How it elaborates operators
   - How it resolves impasses
   - How it learns from solutions

2. **Study the modular approach** (ACT-R)
   - How modules coordinate
   - How utilities guide decisions
   - How learning updates strategies
   - How memory works (activation decay)

3. **Study the learning mechanisms**
   - SOAR: Rule acquisition from successful traces
   - ACT-R: Utility-based rule refinement
   - Both: How experience improves performance

### Phase 2: Identify What To Keep vs. Change

**Keep**:
- Problem decomposition idea (SOAR)
- Utility-based decision making (ACT-R)
- Learning from experience (both)
- Modular architecture (ACT-R)
- Rule-based knowledge (both)

**Change**:
- Use LLMs to implement perception/language parts (both used symbolic parsing)
- Use test-time compute for search (SOAR used older search algorithms)
- Handle continuous perceptions (both dealt with discrete symbols)
- Scale to modern problem domains

### Phase 3: Build Hybrid System

```
┌─────────────────────────────────┐
│  Perception Layer: LLM          │
│  (Ground problem in language)   │
├─────────────────────────────────┤
│  Reasoning Layer: SOAR-like      │
│  (Problem-space search)         │
├─────────────────────────────────┤
│  Decision Layer: ACT-R-like      │
│  (Utility-based selection)      │
├─────────────────────────────────┤
│  Action Layer: Tool Interface   │
│  (Execute decisions)            │
├─────────────────────────────────┤
│  Learning Layer: Rule Update    │
│  (Improve rules over time)      │
└─────────────────────────────────┘
```

---

## Why This Matters For Your Competitive Position

### Against SuperMemory/Mem0/ACE

They optimize token prediction and memory management.

You're building actual reasoning and learning using **proven cognitive science foundations.**

This is fundamentally more powerful.

### Against ii.inc

They build excellent agents on top of current architecture.

You're changing the architecture itself using **40 years of cognitive science research.**

This is structurally superior.

### Against Current Frameworks

They all assume token prediction is enough.

You're showing that **cognitive architectures are necessary for genuine intelligence.**

This is foundationally different.

---

## Conclusion: Standing On The Shoulders of Giants

SOAR and ACT-R represent **40+ years of research into how intelligence actually works.**

They've been proven on countless domains. They succeed where pure token prediction fails.

The opportunity in 2025: **Combine the best of both worlds.**

Use LLMs for what they excel at (perception, language, grounding).
Use cognitive architecture principles for what they excel at (reasoning, learning, problem-solving).

This hybrid approach is what your WS2 should implement.

**The research is done.** The proof is done. The implementations exist.

Your job isn't to reinvent cognitive science. It's to:
1. Understand the principles
2. Integrate with modern LLMs
3. Make it work at scale
4. Make it portable across systems

That's the path from "better token prediction" to "actual intelligence."

---

## Resources To Study

### Primary Papers

1. **"Introduction to the Soar Cognitive Architecture"** (Laird, 2022)
   - Overview of SOAR philosophy and mechanisms

2. **"An Analysis and Comparison of ACT-R and Soar"** (Laird, 2022)
   - Side-by-side comparison of both systems

3. **"The ACT-R Architecture"** (Anderson et al., various)
   - Official ACT-R documentation and theory

### Recent Hybrid Research

1. **"LLM-ACTR: Bridging Cognitive Models to LLMs"** (Wu, 2025)
   - How to combine ACT-R with modern LLMs

2. **"Toward Visual-Symbolic Integration in SOAR"** (Boggs, 2025)
   - Modern SOAR with neural perception

3. **"Cognitive Architectures for Language Agents"** (Wu et al., 2024)
   - Framework for LLM + cognitive architecture

### Open Source

- **SOAR**: Available at soar.eecs.umich.edu
- **ACT-R**: Available at act-r.psy.cmu.edu
- Both have active communities and modern implementations

---

## Final Thought

The most interesting research happening in 2025 isn't in pure LLMs or pure cognitive architectures.

It's in the hybrid space: combining neural perception with symbolic reasoning, combining deep learning with cognitive principles, combining modern compute with 40 years of cognitive science.

**That's where your research should live.**

Not choosing between LLMs or cognitive architectures, but asking: **How do we build systems that have the benefits of both?**

SOAR and ACT-R show the answer. Your research implements it at modern scale.
