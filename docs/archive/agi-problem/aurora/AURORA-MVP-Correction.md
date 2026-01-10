# AURORA MVP Correction

## Executive Summary

This document captures the critical corrections to the AURORA Framework MVP based on product review and architectural analysis. The core finding: **AURORA as originally designed is an orchestration and caching framework, not a reasoning solution.** To actually solve the reasoning problem, a verification layer must be added.

---

## Part 1: Problem Analysis

### What the Original PRD Claims to Solve

The PRD states LLMs have "25-30% accuracy on complex, multi-step problems" and proposes SOAR + ACT-R to fix this.

### Why LLMs Actually Fail at Reasoning

| Failure Mode | Description |
|--------------|-------------|
| **Attention degradation** | Each step introduces compounding error as model loses focus on earlier reasoning |
| **No working memory** | LLMs don't maintain persistent state between inference calls |
| **Probability collapse** | When problem diverges from training distribution, token prediction becomes unreliable |
| **No verification** | LLMs can't distinguish plausible-sounding from logically valid |
| **Hallucination as feature** | LLMs generate coherent text even without basis |

### What Original MVP Actually Does

| Component | What It Does | Solves Reasoning? |
|-----------|--------------|-------------------|
| Hybrid Assessment | Classify query complexity | No - routing optimization |
| SOAR Decomposition | Break problem into subgoals | No - just structured prompting |
| Agent Routing | Send subgoals to specialists | No - distribution, not reasoning |
| ACT-R Memory | Cache successful patterns | No - helps repeated problems, not novel reasoning |

**Conclusion:** Original MVP optimizes **cost** and **routing**, not **reasoning quality**.

---

## Part 2: What's Missing

### Critical Gap: No Verification Layer

The original MVP has no mechanism to verify:

1. **Decomposition validity** - Is the breakdown complete? Consistent? Does it cover the problem?
2. **Agent output correctness** - Did agents actually solve their subgoals correctly?
3. **Synthesis integrity** - Does the final answer follow from the evidence?
4. **Logical consistency** - Do intermediate conclusions contradict each other?

### The Core Issue

> Decomposition doesn't solve the reasoning problem - it just distributes it.

If the LLM is unreliable at reasoning, asking it to propose decompositions means the decomposition itself is unreliable. Without verification, you inherit all the reasoning failures the system claims to solve.

### What Verification Enables

- Catches invalid decompositions before wasting agent compute
- Detects when agent outputs don't address subgoals
- Identifies contradictions between results
- Provides **earned** confidence scores (not heuristic guesses)
- Enables learning from **verified** successes (not user satisfaction)

---

## Part 3: The Corrected Architecture

### The Simple Model

```
DECOMPOSE ──▶ VERIFY ──▶ AGENTS ──▶ VERIFY ──▶ RESPOND
    │           │          │          │
   LLM        LLM        WORK       LLM
(structure)  (check)    (solve)   (check)
```

### Four Core Steps

| Step | Actor | Purpose | Output |
|------|-------|---------|--------|
| **1. Decompose** | LLM | Break problem into subgoals (structured JSON) | Decomposition plan |
| **2. Verify Decomposition** | LLM | Is this decomposition valid? | Score 0-1, pass/retry |
| **3. Execute** | Agents | Actually solve each subgoal | Results per subgoal |
| **4. Verify Results** | LLM | Are results good? Consistent? Complete? | Score 0-1, final answer |

### Key Insight

**Solving happens in Step 3 - agents do the actual work.**

The reasoning layer ensures:
- Good decomposition (before agents)
- Good outputs (after agents)
- Good synthesis (final answer)

It's **quality assurance for the thinking process**, not a replacement for agents doing work.

---

## Part 4: Hybrid Verification Strategy (A+B)

### Complexity-Based Path Selection

```
┌─────────────────────────────────────────────────────────────┐
│                    COMPLEXITY ROUTER                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  SIMPLE ───▶ Direct LLM + light self-check (Option A)      │
│              ~1.5x LLM cost                                 │
│                                                             │
│  MEDIUM ───▶ Decompose + self-verify + agents +            │
│              self-verify (Option A)                         │
│              ~3-4x LLM cost                                 │
│                                                             │
│  COMPLEX ──▶ Decompose + adversarial verify + agents +     │
│              adversarial verify (Option B)                  │
│              ~5-6x LLM cost                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Option A: Self-Verification

- Same LLM reviews its own reasoning
- Catches obvious gaps, missing structure, incomplete coverage
- Fast, low cost
- Limitation: same blind spots

### Option B: Adversarial Verification

- Second LLM (or different prompt) acts as skeptical critic
- Finds hidden assumptions, alternative conclusions, logical leaps
- More thorough, higher cost
- Better for complex/critical tasks

### When to Use Each

| Query Type | Verification | Cost | Example |
|------------|--------------|------|---------|
| Simple | None or light self-check | 1-1.5x | "What's the capital of France?" |
| Medium | Self-verification (A) | 3-4x | "Compare these two approaches" |
| Complex | Adversarial (B) | 5-6x | "Design a migration strategy for X" |

---

## Part 5: Structured JSON Contracts

### Why JSON?

- **Parseable** - Can programmatically check structure
- **Traceable** - Every inference has explicit sources
- **Auditable** - Full chain preserved
- **Cacheable** - ACT-R can store/retrieve patterns

### 5.1 Decomposition Output

```json
{
  "decomposition": {
    "id": "uuid",
    "original_query": "user's question",
    "complexity": "complex",

    "given": [
      {"id": "G1", "fact": "extracted fact 1", "source": "query"},
      {"id": "G2", "fact": "extracted fact 2", "source": "context"}
    ],

    "goal": {
      "description": "what we're trying to achieve",
      "success_criteria": ["criterion 1", "criterion 2"]
    },

    "subgoals": [
      {
        "id": "SG1",
        "description": "first subgoal",
        "requires": ["G1"],
        "agent": "research-agent",
        "expected_output": "what this should produce",
        "depends_on": []
      },
      {
        "id": "SG2",
        "description": "second subgoal",
        "requires": ["G1", "G2"],
        "agent": "analysis-agent",
        "expected_output": "what this should produce",
        "depends_on": ["SG1"]
      },
      {
        "id": "SG3",
        "description": "third subgoal",
        "requires": ["SG1.output", "SG2.output"],
        "agent": "synthesis-agent",
        "expected_output": "final combined result",
        "depends_on": ["SG1", "SG2"]
      }
    ],

    "execution_order": ["SG1", "SG2", "SG3"],
    "parallelizable": [["SG1", "SG2"]]
  }
}
```

### 5.2 Decomposition Verification

```json
{
  "verification": {
    "decomposition_id": "uuid",
    "checks": {
      "completeness": {
        "pass": true,
        "score": 0.9,
        "detail": "All aspects of goal covered by subgoals"
      },
      "consistency": {
        "pass": true,
        "score": 1.0,
        "detail": "No contradictions between subgoals"
      },
      "routability": {
        "pass": true,
        "score": 0.85,
        "detail": "All agents available",
        "warnings": ["analysis-agent has 0.7 confidence match"]
      },
      "dependencies": {
        "pass": true,
        "score": 1.0,
        "detail": "Dependency graph is valid DAG"
      },
      "groundedness": {
        "pass": true,
        "score": 0.8,
        "detail": "All subgoals trace to given facts"
      }
    },
    "overall_score": 0.85,
    "verdict": "pass",
    "issues": [],
    "suggestions": []
  }
}
```

### 5.3 Agent Output + Verification

```json
{
  "agent_execution": {
    "subgoal_id": "SG1",
    "agent": "research-agent",

    "input": {
      "task": "subgoal description",
      "context": ["G1 fact"],
      "expected_output": "what to produce"
    },

    "output": {
      "result": "agent's actual output",
      "confidence": "high",
      "sources": ["source1", "source2"],
      "caveats": ["caveat if any"]
    },

    "verification": {
      "relevance": {
        "score": 0.9,
        "detail": "Output addresses the subgoal"
      },
      "consistency": {
        "score": 1.0,
        "detail": "No internal contradictions"
      },
      "groundedness": {
        "score": 0.85,
        "detail": "Claims supported by sources"
      },
      "overall_score": 0.88,
      "verdict": "pass"
    }
  }
}
```

### 5.4 Final Synthesis + Score

```json
{
  "synthesis": {
    "query_id": "uuid",
    "original_query": "user's question",

    "reasoning_trace": {
      "given": ["G1", "G2"],
      "from_agents": [
        {"subgoal": "SG1", "agent": "research-agent", "contributed": "finding X"},
        {"subgoal": "SG2", "agent": "analysis-agent", "contributed": "insight Y"},
        {"subgoal": "SG3", "agent": "synthesis-agent", "contributed": "combined Z"}
      ],
      "inferences": [
        {
          "id": "I1",
          "step": "From X and Y, we conclude...",
          "from": ["SG1.output", "SG2.output"]
        }
      ],
      "conclusion": {
        "answer": "final answer to user",
        "confidence": "high",
        "supports": ["I1", "SG3.output"]
      }
    },

    "final_verification": {
      "addresses_query": {"score": 0.95, "detail": "Directly answers the question"},
      "traceable": {"score": 1.0, "detail": "All claims link to agent outputs"},
      "consistent": {"score": 0.9, "detail": "No contradictions in final answer"},
      "confidence_calibrated": {"score": 0.85, "detail": "Confidence matches evidence"}
    },

    "overall_score": 0.92,
    "verdict": "pass",

    "metadata": {
      "complexity": "complex",
      "path": "decompose → verify → route → verify → synthesize",
      "agents_used": ["research-agent", "analysis-agent", "synthesis-agent"],
      "llm_calls": 7,
      "total_latency_ms": 4500
    }
  }
}
```

---

## Part 6: Scoring System

### Checkpoints

| Checkpoint | What's Scored | Threshold | On Fail |
|------------|---------------|-----------|---------|
| Decomposition | Is breakdown valid? | ≥ 0.7 | Retry decomposition (max 2x) |
| Per-agent output | Did agent deliver? | ≥ 0.7 | Retry that subgoal (max 2x) |
| Final synthesis | Does answer work? | ≥ 0.7 | Return with low confidence flag |
| Cache threshold | Worth remembering? | ≥ 0.8 | Don't cache |

### Verification Checks

**Decomposition Verification:**
- Completeness: Do subgoals cover the goal?
- Consistency: No contradictions between subgoals?
- Routability: Do required agents exist?
- Dependencies: Is execution order valid (DAG)?
- Groundedness: Do subgoals trace to given facts?

**Agent Output Verification:**
- Relevance: Does output address the subgoal?
- Consistency: Is output internally consistent?
- Groundedness: Are claims supported by evidence?

**Final Verification:**
- Addresses query: Does answer respond to original question?
- Traceable: Can all claims link to agent outputs?
- Consistent: No contradictions in final answer?
- Calibrated: Is confidence level appropriate?

---

## Part 7: What Changes From Original PRD

### Architecture Changes

| Original MVP | Corrected MVP |
|--------------|---------------|
| Assessment → Route → Agents | Assessment → **Decompose (JSON)** → **Verify** → Route → **Verify** → Synthesize → **Verify** |
| Heuristic confidence | **Earned scores** at each checkpoint |
| Hope agents work | **Verify agents delivered** |
| Cache based on user satisfaction | **Cache based on verification scores** |
| No trace | **Full JSON trace** of reasoning chain |

### Component Changes

| Component | Original | Corrected |
|-----------|----------|-----------|
| SOAR | Propose/evaluate with heuristics | Decompose with **structured JSON** + **LLM verification** |
| Confidence | Heuristic scoring | Verification-based scoring (earned) |
| Agent outputs | Accept as-is | **Verify each output** against subgoal |
| Learning | Cache on user satisfaction | Cache on **verification score ≥ 0.8** |
| Output | Answer + confidence | Answer + score + **full reasoning trace** |

### New Components to Add

1. **Decomposition Verifier** - LLM prompt to validate decomposition structure
2. **Agent Output Verifier** - LLM prompt to validate each agent result
3. **Synthesis Verifier** - LLM prompt to validate final answer
4. **JSON Schema Enforcement** - Structured output parsing
5. **Retry Logic** - Handle verification failures with bounded retries

### Components to Keep As-Is

1. **Complexity Assessment** - Keyword + LLM hybrid still valid
2. **Agent Routing** - Still routes subgoals to specialized agents
3. **ACT-R Memory** - Still caches patterns (but only verified ones)
4. **Task Files** - Still persists state (now includes reasoning traces)

### Components to Deprioritize

1. **Sophisticated SOAR cycles** - Simple decompose → verify → execute is enough for MVP
2. **Production rules** - Can learn these over time, not needed for MVP
3. **Impasse resolution** - Simple retry/escalate is sufficient

---

## Part 8: Full MVP Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CORRECTED MVP FLOW                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────┐                                                           │
│  │ USER     │                                                           │
│  │ QUERY    │                                                           │
│  └────┬─────┘                                                           │
│       │                                                                  │
│       ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 1. COMPLEXITY ASSESSMENT                                         │   │
│  │    Keyword scoring + LLM verification                            │   │
│  │    Output: SIMPLE | MEDIUM | COMPLEX                             │   │
│  └────┬────────────────────────────────────────────────────────────┘   │
│       │                                                                  │
│       ├───────────────────────────────────────┐                         │
│       │                                       │                         │
│       ▼                                       ▼                         │
│  ┌─────────┐                           ┌─────────────────────────────┐ │
│  │ SIMPLE  │                           │ MEDIUM / COMPLEX            │ │
│  │ Direct  │                           │                             │ │
│  │ LLM +   │                           │  2. DECOMPOSE (JSON)        │ │
│  │ light   │                           │     ↓                       │ │
│  │ verify  │                           │  3. VERIFY DECOMPOSITION    │ │
│  └────┬────┘                           │     Score ≥ 0.7? Continue   │ │
│       │                                │     Score < 0.7? Retry (2x) │ │
│       │                                │     ↓                       │ │
│       │                                │  4. ROUTE TO AGENTS         │ │
│       │                                │     Agents solve subgoals   │ │
│       │                                │     ↓                       │ │
│       │                                │  5. VERIFY AGENT OUTPUTS    │ │
│       │                                │     Score ≥ 0.7? Continue   │ │
│       │                                │     Score < 0.7? Retry      │ │
│       │                                │     ↓                       │ │
│       │                                │  6. SYNTHESIZE              │ │
│       │                                │     ↓                       │ │
│       │                                │  7. FINAL VERIFICATION      │ │
│       │                                │     Score overall answer    │ │
│       │                                └──────────────┬──────────────┘ │
│       │                                               │                 │
│       └───────────────────────────────────────────────┤                 │
│                                                       │                 │
│                                                       ▼                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 8. ACT-R MEMORY                                                  │   │
│  │    If overall_score ≥ 0.8: cache pattern                         │   │
│  │    query_pattern → decomposition → routing → verified_result     │   │
│  └────┬────────────────────────────────────────────────────────────┘   │
│       │                                                                  │
│       ▼                                                                  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ RESPONSE                                                          │  │
│  │ - answer                                                          │  │
│  │ - overall_score                                                   │  │
│  │ - confidence (derived from score)                                 │  │
│  │ - reasoning_trace (JSON)                                          │  │
│  │ - uncertainties (if any)                                          │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Part 9: Success Metrics (Corrected)

### Primary Metrics

| Metric | Definition | Target | How to Measure |
|--------|------------|--------|----------------|
| **Reasoning Accuracy** | Correct answers on verifiable problems | ≥ 80% | Benchmark suite with known answers |
| **Verification Catch Rate** | Errors caught by verification | ≥ 70% | Inject known-bad decompositions |
| **Score Calibration** | High scores = correct, low scores = incorrect | Correlation ≥ 0.7 | Compare scores to actual correctness |
| **Cost Efficiency** | Cost vs. baseline LLM-only | ≤ 2x for medium, ≤ 3x for complex | Track LLM calls per query |

### Secondary Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| Cache hit rate | % queries served from ACT-R | ≥ 30% after 1000 queries |
| Retry rate | % decompositions needing retry | ≤ 20% |
| Agent utilization | % subgoals successfully routed | ≥ 90% |

### What's Different from Original Metrics

| Original Metric | Problem | Corrected Metric |
|-----------------|---------|------------------|
| "92% assessment accuracy" | Measures classification, not reasoning | **Reasoning accuracy on benchmark** |
| "40% cost reduction" | No baseline defined | **Cost relative to LLM-only baseline** |
| "User satisfaction" | Subjective, can reward plausible-wrong | **Verification scores + benchmark accuracy** |

---

## Part 10: Implementation Priority

### Phase 1A (Weeks 1-2): Core Loop

1. Structured decomposition (JSON output)
2. Self-verification for decomposition
3. Agent routing (use existing)
4. Self-verification for agent outputs
5. Basic synthesis

### Phase 1B (Weeks 3-4): Robustness

1. Adversarial verification for complex queries
2. Retry logic with bounded attempts
3. Scoring calibration
4. ACT-R caching of verified patterns

### Phase 2 (Weeks 5-8): Learning

1. Pattern learning from verified successes
2. Production rule extraction
3. Improved routing from learned patterns

---

## Part 11: Key Takeaways

### What We Learned

1. **SOAR is control flow, not reasoning** - It's good for goal-directed behavior but doesn't verify logical validity
2. **Memory isn't the problem** - ACT-R is smart retrieval, but retrieval doesn't help if reasoning is wrong
3. **Verification is the missing piece** - Without checking validity, you're just distributing unreliable reasoning
4. **Structured output enables verification** - JSON format makes reasoning auditable and checkable
5. **Earned scores > heuristic confidence** - Verification-based scoring is trustworthy; heuristics are guesses

### The Core Insight

> The reasoning layer's job isn't to DO reasoning - it's to make reasoning AUDITABLE and VERIFIABLE.

LLM reasoning isn't always wrong - the problem is you can't tell when it's wrong. Verification gates catch errors, provide calibrated confidence, and enable learning from actual successes.

### The Minimal Viable Addition

If nothing else, add this to original MVP:

1. **Force JSON structure** on decomposition and synthesis
2. **LLM verification pass** after decomposition
3. **LLM verification pass** after agent outputs
4. **Score-based caching** instead of satisfaction-based

This is ~2x the LLM calls for complex queries but provides actual reasoning quality assurance.

---

## Appendix: Verification Prompts

### Decomposition Verification Prompt

```
You are a critical reviewer. Analyze this decomposition for logical validity.

DECOMPOSITION:
{decomposition_json}

Check each criterion and score 0.0-1.0:

1. COMPLETENESS: Do the subgoals fully cover the original goal?
   - Are any aspects of the goal missing?
   - Would completing all subgoals actually achieve the goal?

2. CONSISTENCY: Are the subgoals internally consistent?
   - Do any subgoals contradict each other?
   - Are the dependencies logical?

3. GROUNDEDNESS: Do subgoals trace to given facts?
   - Is each subgoal justified by the input?
   - Are there unsupported assumptions?

4. ROUTABILITY: Can each subgoal be executed?
   - Is the agent assignment appropriate?
   - Is the expected output realistic?

Output JSON:
{
  "completeness": {"score": 0.0-1.0, "issues": []},
  "consistency": {"score": 0.0-1.0, "issues": []},
  "groundedness": {"score": 0.0-1.0, "issues": []},
  "routability": {"score": 0.0-1.0, "issues": []},
  "overall_score": 0.0-1.0,
  "verdict": "pass|retry|fail",
  "critical_issues": []
}
```

### Agent Output Verification Prompt

```
You are a critical reviewer. Analyze this agent output against its assigned subgoal.

SUBGOAL:
{subgoal_json}

AGENT OUTPUT:
{output_json}

Check each criterion and score 0.0-1.0:

1. RELEVANCE: Does the output address the subgoal?
   - Is this actually what was asked for?
   - Is anything missing?

2. CONSISTENCY: Is the output internally consistent?
   - Are there contradictions?
   - Does the logic hold?

3. GROUNDEDNESS: Are claims supported?
   - What evidence backs the claims?
   - Are there unsupported assertions?

Output JSON:
{
  "relevance": {"score": 0.0-1.0, "issues": []},
  "consistency": {"score": 0.0-1.0, "issues": []},
  "groundedness": {"score": 0.0-1.0, "issues": []},
  "overall_score": 0.0-1.0,
  "verdict": "pass|retry|fail",
  "critical_issues": []
}
```

### Final Synthesis Verification Prompt

```
You are a critical reviewer. Analyze this final answer against the original query.

ORIGINAL QUERY:
{query}

SYNTHESIS:
{synthesis_json}

Check each criterion and score 0.0-1.0:

1. ADDRESSES_QUERY: Does the answer respond to what was asked?
2. TRACEABLE: Can every claim be traced to agent outputs?
3. CONSISTENT: Are there any contradictions?
4. CALIBRATED: Is the confidence level appropriate given the evidence?

Output JSON:
{
  "addresses_query": {"score": 0.0-1.0, "detail": ""},
  "traceable": {"score": 0.0-1.0, "detail": ""},
  "consistent": {"score": 0.0-1.0, "detail": ""},
  "calibrated": {"score": 0.0-1.0, "detail": ""},
  "overall_score": 0.0-1.0,
  "verdict": "pass|pass_with_caveats|fail",
  "final_confidence": "high|medium|low",
  "uncertainties": []
}
```

---

## Part 12: ACT-R Memory System

### What Is ACT-R?

ACT-R (Adaptive Control of Thought—Rational) is a **cognitive architecture** from psychology/cognitive science. It models how human memory actually works - not just storage, but **how we retrieve what's relevant**.

### The Problem ACT-R Solves

Regular memory systems (like vector databases) answer:
> "What's semantically similar to this query?"

ACT-R answers:
> "What's most **useful to recall right now** given context, recency, and past usefulness?"

### Core Concepts

#### 1. Activation-Based Retrieval

Every memory chunk has an **activation level** that determines if it gets retrieved:

```
Activation = Base-Level + Spreading Activation + Noise
```

**Base-Level Activation:**
- How often has this been used? (frequency)
- How recently? (recency)
- Formula: `B = ln(Σ t_j^(-d))` where t_j is time since each access, d is decay rate

```
Example:
- Pattern used 10x in last hour: HIGH activation
- Pattern used once 3 weeks ago: LOW activation
- Pattern used 100x but not for 6 months: MEDIUM activation (frequent but decayed)
```

#### 2. Spreading Activation

Current context **primes** related memories:

```
┌─────────────────────────────────────────────┐
│                                             │
│  Current Context: "database migration"      │
│                                             │
│       ┌─────────┐                           │
│       │migration│ ◄── HIGH activation       │
│       └────┬────┘                           │
│            │ spreads to                     │
│       ┌────┴────┐                           │
│       ▼         ▼                           │
│  ┌────────┐ ┌────────┐                      │
│  │schema  │ │rollback│ ◄── MEDIUM           │
│  └────────┘ └────────┘     (related)        │
│                                             │
│  ┌────────┐                                 │
│  │ auth   │ ◄── LOW (unrelated)             │
│  └────────┘                                 │
│                                             │
└─────────────────────────────────────────────┘
```

Memories connected to current context get activation boost.

#### 3. Retrieval Threshold

Only memories above a threshold get retrieved:

```
If Activation > Threshold: Retrieved
If Activation < Threshold: Not retrieved (forgotten)
```

This prevents irrelevant memories from cluttering retrieval.

### How ACT-R Applies to AURORA

#### Traditional Cache (Dumb)
```
Query → Hash → Exact match? → Return cached result
```

#### Vector Store (Similarity)
```
Query → Embed → Find similar vectors → Return top-k
```

#### ACT-R Memory (Smart)
```
Query → Extract context → Calculate activation for all patterns:
  - Base: How often/recently used?
  - Spread: Related to current context?
  - Threshold: Above minimum usefulness?
→ Return highest activation patterns
```

### ACT-R in AURORA MVP

#### What Gets Stored

When a query succeeds (verification score ≥ 0.8):

```json
{
  "pattern": {
    "id": "uuid",
    "query_signature": "normalized query features",
    "domain": "detected domain",
    "complexity": "complex",

    "decomposition": { /* the successful decomposition */ },
    "routing": { /* which agents handled which subgoals */ },
    "result_summary": "what worked",

    "activation_data": {
      "creation_time": "timestamp",
      "access_times": ["t1", "t2", "t3"],
      "access_count": 3,
      "success_rate": 1.0,
      "contexts_used": ["migration", "database", "postgres"]
    }
  }
}
```

#### Retrieval Process

```
┌─────────────────────────────────────────────────────────────┐
│                    ACT-R RETRIEVAL                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. NEW QUERY arrives                                       │
│     "How do I migrate from MySQL to Postgres?"              │
│                                                             │
│  2. EXTRACT CONTEXT                                         │
│     context = ["migration", "MySQL", "Postgres", "database"]│
│                                                             │
│  3. CALCULATE ACTIVATION for each stored pattern           │
│                                                             │
│     Pattern A: "database migration strategy"                │
│     ├── Base-level: 0.7 (used 5x in last week)             │
│     ├── Spreading: 0.8 (shares migration, database)         │
│     └── Total: 1.5 ✓ ABOVE THRESHOLD                       │
│                                                             │
│     Pattern B: "API authentication setup"                   │
│     ├── Base-level: 0.9 (used 10x recently)                │
│     ├── Spreading: 0.1 (no context overlap)                 │
│     └── Total: 1.0 ✗ BELOW THRESHOLD                       │
│                                                             │
│     Pattern C: "MySQL backup procedure"                     │
│     ├── Base-level: 0.3 (used 2x, month ago)               │
│     ├── Spreading: 0.5 (shares MySQL)                       │
│     └── Total: 0.8 ✗ BELOW THRESHOLD                       │
│                                                             │
│  4. RETRIEVE highest activation patterns                    │
│     → Pattern A retrieved                                   │
│     → Use its decomposition as template/reference           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### The Key Insight

ACT-R isn't just "find similar" - it's **"find what's been useful in similar situations"**.

| Approach | What It Finds | Limitation |
|----------|---------------|------------|
| Exact match | Same query | Misses variations |
| Vector similarity | Semantically close | May retrieve irrelevant but "similar" |
| ACT-R | Useful + relevant + recent | Requires usage history |

### ACT-R Activation Formula (Simplified)

```python
def calculate_activation(pattern, current_context):
    # Base-level: frequency and recency
    base = 0
    for access_time in pattern.access_times:
        time_since = now() - access_time
        base += time_since ** (-0.5)  # decay factor
    base = log(base) if base > 0 else -inf

    # Spreading activation: context overlap
    overlap = len(set(pattern.contexts) & set(current_context))
    spreading = overlap * 0.3  # weight per shared concept

    # Total activation
    activation = base + spreading

    return activation

def retrieve(query, memory, threshold=0.5):
    context = extract_context(query)

    candidates = []
    for pattern in memory:
        activation = calculate_activation(pattern, context)
        if activation > threshold:
            candidates.append((pattern, activation))

    # Return highest activation
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[:3]  # top 3
```

### Why ACT-R Matters for AURORA

1. **Learns from verified successes** - Only patterns that passed verification get cached
2. **Prioritizes useful patterns** - Frequently successful patterns rise to top
3. **Context-aware retrieval** - Related problems retrieve related solutions
4. **Natural decay** - Unused patterns fade, keeping memory relevant
5. **No cold start for similar problems** - New query can use decomposition template from similar past success

### ACT-R vs. Original PRD

| Original PRD | Correction |
|--------------|------------|
| "Stores successful patterns" | Store based on **verification score ≥ 0.8**, not user satisfaction |
| "Retrieval based on activation" | Correct - keep this |
| Learning signal | Learn from **verified correct** patterns, not plausible-sounding ones |

### ACT-R Integration with Verification Layer

```
┌─────────────────────────────────────────────────────────────┐
│              ACT-R + VERIFICATION INTEGRATION               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  BEFORE DECOMPOSITION:                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 1. Check ACT-R for similar past queries             │   │
│  │ 2. If high-activation match found:                  │   │
│  │    → Use cached decomposition as template           │   │
│  │    → Still verify (patterns can become stale)       │   │
│  │ 3. If no match:                                     │   │
│  │    → Generate fresh decomposition                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  AFTER SUCCESSFUL COMPLETION:                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 1. Check final verification score                   │   │
│  │ 2. If score ≥ 0.8:                                  │   │
│  │    → Store in ACT-R memory                          │   │
│  │    → Include: decomposition, routing, result        │   │
│  │ 3. If score < 0.8:                                  │   │
│  │    → Do NOT cache (unreliable pattern)              │   │
│  │ 4. Update activation of retrieved patterns:         │   │
│  │    → Used successfully? +activation                 │   │
│  │    → Not helpful? -activation (decay faster)        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

This ensures ACT-R learns from **actually correct** reasoning patterns, not just patterns that seemed good.

---

## Part 13: Unified Framework - AURORA-Context

### The Core Insight

Both reasoning orchestration (AURORA) and code retrieval (ContextMind) solve the same fundamental problem:

> **"How do I give an LLM the right context to reason correctly?"**

| AURORA | ContextMind |
|--------|-------------|
| Right **reasoning pattern** for the task | Right **code** for the task |
| What approach worked before? | What functions are relevant? |
| ACT-R for reasoning templates | ACT-R for code chunks |

**They're both context retrieval problems with the same underlying mechanism.**

### Why Unified Makes Sense

1. **Same Activation Math** - Identical ACT-R mechanisms, different chunk types
2. **Cross-Domain Learning** - Reasoning patterns can prime code retrieval and vice versa
3. **One Learning Signal** - Single verification score updates all retrieved context
4. **Simpler Architecture** - One framework with pluggable context types

### Unified Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     AURORA-CONTEXT FRAMEWORK                         │
│            "Architecture-Agnostic Reasoning + Retrieval"             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    UNIFIED ACT-R MEMORY                         │ │
│  │                                                                 │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐  │ │
│  │  │ Reasoning       │  │ Code            │  │ Domain         │  │ │
│  │  │ Patterns        │  │ Chunks          │  │ Knowledge      │  │ │
│  │  │                 │  │                 │  │                │  │ │
│  │  │ decompositions  │  │ functions       │  │ API docs       │  │ │
│  │  │ routing maps    │  │ classes         │  │ schemas        │  │ │
│  │  │ verification    │  │ dependencies    │  │ conventions    │  │ │
│  │  │ patterns        │  │                 │  │                │  │ │
│  │  └────────┬────────┘  └────────┬────────┘  └───────┬────────┘  │ │
│  │           │                    │                   │           │ │
│  │           └────────────────────┼───────────────────┘           │ │
│  │                                │                                │ │
│  │                    ┌───────────▼───────────┐                   │ │
│  │                    │  ACTIVATION ENGINE    │                   │ │
│  │                    │  - Base-level         │                   │ │
│  │                    │  - Spreading          │                   │ │
│  │                    │  - Context boost      │                   │ │
│  │                    │  - Decay              │                   │ │
│  │                    └───────────────────────┘                   │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    REASONING LAYER                              │ │
│  │                                                                 │ │
│  │  Query → Decompose (JSON) → Verify → Route → Verify → Respond  │ │
│  │                                                                 │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    RETRIEVAL LAYER                              │ │
│  │                                                                 │ │
│  │  At each step, retrieve relevant context:                       │ │
│  │  - Reasoning patterns (how to decompose similar problems)       │ │
│  │  - Code chunks (what code is relevant)                          │ │
│  │  - Domain knowledge (what constraints apply)                    │ │
│  │                                                                 │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                 CONTEXT PROVIDERS (Pluggable)                   │ │
│  │                                                                 │ │
│  │  CodeContextProvider:     ReasoningContextProvider:             │ │
│  │  - cAST parser            - Pattern templates                   │ │
│  │  - Git integration        - Decomposition history               │ │
│  │  - Dependency graph       - Routing maps                        │ │
│  │                                                                 │ │
│  │  KnowledgeContextProvider:  [Future: CustomContextProvider]     │ │
│  │  - API documentation                                            │ │
│  │  - Domain schemas                                               │ │
│  │  - Team conventions                                             │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Cross-Context Learning Example

```
Query: "Why is our auth slow and how do we fix it?"

Retrieved context (unified):
├── Reasoning: "performance debugging" pattern
├── Code: authenticate(), db_query(), cache_manager()
├── Knowledge: "N+1 query pattern", "Redis caching strategy"
└── Domain: "SLA requirements", "current latency metrics"

Decomposition uses ALL context to create better subgoals.
Verification score updates ALL retrieved chunks.
```

### Domain-Agnostic Application

| Domain | Context Providers | Same Core |
|--------|------------------|-----------|
| **Code** | cAST + Git + Dependencies | ✓ Reasoning + ACT-R + Verification |
| **Documents** | Doc chunks + Citations + Sections | ✓ Reasoning + ACT-R + Verification |
| **Research** | Papers + Citations + Claims | ✓ Reasoning + ACT-R + Verification |
| **Business** | Processes + Data + Policies | ✓ Reasoning + ACT-R + Verification |

**One framework, pluggable context types.**

---

## Part 14: Verification Options (A, B, C)

### Option A: Self-Verification (Minimal)

```
LLM generates → Same LLM reviews → Score → Pass/Retry
```

- **Cost**: ~1.5x LLM calls
- **Use when**: SIMPLE or MEDIUM complexity
- **Catches**: Obvious gaps, missing structure, incomplete coverage
- **Limitation**: Same blind spots as generator

### Option B: Adversarial Verification (Robust)

```
LLM-1 generates → LLM-2 critiques → Address critique → Re-verify → Score
```

- **Cost**: ~2-3x LLM calls
- **Use when**: COMPLEX tasks
- **Catches**: Hidden assumptions, alternative conclusions, logical leaps
- **Limitation**: Both LLMs can share biases

### Option C: Deep Reasoning (Thorough)

**Triggered when**: Option B fails 2+ cycles OR task flagged as CRITICAL

```
┌─────────────────────────────────────────────────────────────────────┐
│                    OPTION C: DEEP REASONING                          │
│                      (~5-10x LLM cost)                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  TRIGGER CONDITIONS:                                                 │
│  - Option B retry count ≥ 2 (adversarial failed twice)              │
│  - Task flagged as CRITICAL (security, architecture, compliance)    │
│  - User explicitly requests deep analysis                           │
│  - Complexity score > 0.95                                          │
│                                                                      │
│  PROCESS:                                                            │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ 1. MULTI-PATH DECOMPOSITION                                 │    │
│  │    Generate 3 alternative decompositions                    │    │
│  │    Each takes different approach to the problem             │    │
│  └──────────────────────────┬──────────────────────────────────┘    │
│                             │                                        │
│                             ▼                                        │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ 2. PARALLEL VERIFICATION                                    │    │
│  │    Verify each decomposition independently                  │    │
│  │    Score each path                                          │    │
│  └──────────────────────────┬──────────────────────────────────┘    │
│                             │                                        │
│                             ▼                                        │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ 3. DEBATE ROUND                                             │    │
│  │    LLM-1 (Path A advocate) vs LLM-2 (Path B advocate)       │    │
│  │    vs LLM-3 (Path C advocate)                               │    │
│  │    Each argues for their decomposition                      │    │
│  │    Identify weaknesses in other paths                       │    │
│  └──────────────────────────┬──────────────────────────────────┘    │
│                             │                                        │
│                             ▼                                        │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ 4. SYNTHESIS                                                │    │
│  │    Judge LLM reviews debate                                 │    │
│  │    Selects best path OR synthesizes hybrid                  │    │
│  │    Documents why alternatives were rejected                 │    │
│  └──────────────────────────┬──────────────────────────────────┘    │
│                             │                                        │
│                             ▼                                        │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ 5. EXECUTION WITH CHECKPOINTS                               │    │
│  │    Execute chosen path                                      │    │
│  │    Verify after EACH subgoal (not just at end)              │    │
│  │    Early exit if verification fails                         │    │
│  └──────────────────────────┬──────────────────────────────────┘    │
│                             │                                        │
│                             ▼                                        │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ 6. FINAL DEEP VERIFICATION                                  │    │
│  │    Full trace review                                        │    │
│  │    Check for emergent contradictions                        │    │
│  │    Validate against original constraints                    │    │
│  │    Confidence calibration                                   │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  OUTPUT:                                                             │
│  - Answer + high confidence (if passed)                              │
│  - Full reasoning trace with alternatives considered                 │
│  - Dissenting opinions (if any unresolved)                          │
│  - Risk assessment                                                   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Option C JSON Output

```json
{
  "deep_reasoning": {
    "id": "uuid",
    "trigger": "adversarial_retry_exceeded",
    "paths_explored": [
      {
        "path_id": "A",
        "approach": "description of approach A",
        "decomposition": { /* ... */ },
        "verification_score": 0.75,
        "weaknesses": ["identified weakness 1"]
      },
      {
        "path_id": "B",
        "approach": "description of approach B",
        "decomposition": { /* ... */ },
        "verification_score": 0.82,
        "weaknesses": ["identified weakness 2"]
      },
      {
        "path_id": "C",
        "approach": "description of approach C",
        "decomposition": { /* ... */ },
        "verification_score": 0.68,
        "weaknesses": ["identified weakness 3", "weakness 4"]
      }
    ],
    "debate_summary": {
      "rounds": 2,
      "key_arguments": ["argument 1", "argument 2"],
      "consensus_points": ["agreed point 1"],
      "unresolved_disagreements": ["disagreement 1"]
    },
    "selected_path": "B",
    "selection_rationale": "Path B had highest verification score and addressed...",
    "rejected_alternatives": [
      {"path": "A", "reason": "Failed to account for constraint X"},
      {"path": "C", "reason": "Decomposition was incomplete"}
    ],
    "execution_checkpoints": [
      {"subgoal": "SG1", "status": "pass", "score": 0.9},
      {"subgoal": "SG2", "status": "pass", "score": 0.85},
      {"subgoal": "SG3", "status": "pass", "score": 0.88}
    ],
    "final_verification": {
      "overall_score": 0.87,
      "confidence": "high",
      "dissenting_opinion": null,
      "risk_assessment": "low"
    }
  }
}
```

### Verification Escalation Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    VERIFICATION ESCALATION                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Query arrives                                                       │
│       │                                                              │
│       ▼                                                              │
│  ┌─────────────┐                                                    │
│  │ Complexity  │                                                    │
│  │ Assessment  │                                                    │
│  └──────┬──────┘                                                    │
│         │                                                            │
│    ┌────┴────┬────────────┬────────────┐                            │
│    ▼         ▼            ▼            ▼                            │
│ SIMPLE    MEDIUM      COMPLEX      CRITICAL                         │
│    │         │            │            │                            │
│    ▼         ▼            ▼            ▼                            │
│ ┌──────┐ ┌──────┐    ┌──────┐    ┌──────┐                          │
│ │ Skip │ │Opt A │    │Opt B │    │Opt C │ ← Direct to deep         │
│ │verify│ │self  │    │adver-│    │deep  │                          │
│ └──┬───┘ └──┬───┘    │sarial│    └──┬───┘                          │
│    │        │        └──┬───┘       │                               │
│    │        │           │           │                               │
│    │        ▼           ▼           │                               │
│    │     Score?      Score?         │                               │
│    │     ≥0.7?       ≥0.7?          │                               │
│    │        │           │           │                               │
│    │   ┌────┴────┐ ┌────┴────┐      │                               │
│    │   │Yes  │No │ │Yes  │No │      │                               │
│    │   ▼     ▼   │ ▼     ▼   │      │                               │
│    │  Pass Retry │Pass Retry │      │                               │
│    │        │    │      │    │      │                               │
│    │        │    │      ▼    │      │                               │
│    │        │    │   Retry   │      │                               │
│    │        │    │   count?  │      │                               │
│    │        │    │      │    │      │                               │
│    │        │    │  ┌───┴───┐│      │                               │
│    │        │    │  │≥2     ││      │                               │
│    │        │    │  ▼       ││      │                               │
│    │        │    │ ESCALATE ││      │                               │
│    │        │    │ to Opt C │◄──────┘                               │
│    │        │    │          │                                       │
│    │        │    └──────────┘                                       │
│    │        │                                                        │
│    ▼        ▼                                                        │
│  RESPOND (with confidence level)                                     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Comparison Table

| Aspect | Option A | Option B | Option C |
|--------|----------|----------|----------|
| **LLM Calls** | 1.5x | 2-3x | 5-10x |
| **Cost** | Low | Medium | High |
| **Latency** | ~2 calls | ~4 calls | ~10+ calls |
| **Catches** | Obvious errors | Hidden assumptions | Deep flaws, edge cases |
| **Blind Spots** | Same as generator | Shared LLM biases | Minimized via debate |
| **Use Case** | Simple/Medium | Complex | Critical/Failed B |
| **Trigger** | Default simple | Default complex | Escalation or flag |
| **Output** | Answer + trace | Answer + critique | Answer + alternatives + debate |

---

## Part 15: MVP Summary

### Short Format: What's in MVP

```
┌─────────────────────────────────────────────────────────────┐
│                 AURORA-CONTEXT MVP (4 weeks)                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  CORE:                                                      │
│  ✓ Unified ACT-R Activation Engine                         │
│  ✓ Reasoning Pipeline (Decompose → Verify → Route → Verify)│
│  ✓ Structured JSON output                                   │
│  ✓ Verification Options A + B                               │
│  ✓ Score-based learning (≥0.8 → cache)                     │
│                                                             │
│  CONTEXT PROVIDERS:                                         │
│  ✓ CodeContextProvider (cAST + Git)                        │
│  ✓ ReasoningContextProvider (pattern templates)            │
│                                                             │
│  DEFERRED TO PHASE 2:                                       │
│  ○ Option C deep reasoning                                  │
│  ○ KnowledgeContextProvider                                 │
│  ○ Cross-context spreading activation                       │
│  ○ Replay HER advanced learning                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### MVP Changes from Original PRD

| Original | Changed To | Why |
|----------|------------|-----|
| Heuristic SOAR scoring | LLM verification at checkpoints | Earned scores, not guesses |
| Cache on user satisfaction | Cache on verification score ≥0.8 | Learn from correct patterns |
| Separate AURORA + ContextMind | Unified AURORA-Context | Cross-domain learning |
| No verification layer | Options A/B/C verification | Catches reasoning errors |
| Hope agents work | Verify agent outputs | Quality assurance |

### Long Format: Detailed MVP Specification

#### Week 1-2: Core Infrastructure

**1.1 Unified Activation Engine**
```
Components:
- Chunk interface (generic for any context type)
- Activation calculation (base + spread + context - decay)
- Threshold-based retrieval
- Learning update mechanism

Data structures:
- ChunkStore (persistent)
- ActivationIndex (fast lookup)
- ContextGraph (for spreading)
```

**1.2 Reasoning Pipeline**
```
Flow:
1. Query intake + complexity assessment
2. Retrieve relevant context (reasoning patterns, code)
3. Decompose into structured JSON
4. Verify decomposition (Option A or B based on complexity)
5. Route subgoals to agents
6. Verify agent outputs
7. Synthesize results
8. Final verification
9. Learn from outcome

JSON contracts:
- Decomposition schema
- Verification schema
- Agent output schema
- Synthesis schema
```

#### Week 2-3: Context Providers

**2.1 CodeContextProvider**
```
Components:
- cAST parser (tree-sitter wrapper)
- Function-level chunking
- Line range tracking
- Git integration (frequency/recency signals)
- Dependency graph extraction

Supported languages (MVP):
- Python
- JavaScript/TypeScript
- Go

Data flow:
- Parse codebase → Function chunks
- Poll git → Update activations
- Query → Retrieve high-activation chunks
```

**2.2 ReasoningContextProvider**
```
Components:
- Pattern template storage
- Query signature extraction
- Similarity matching
- Decomposition caching

What gets stored:
- Successful decomposition patterns
- Routing decisions that worked
- Verification patterns

Retrieval:
- New query → Find similar past queries
- Return decomposition template as starting point
```

#### Week 3-4: Verification + Learning

**3.1 Verification Layer**
```
Option A (Self-Verify):
- Decomposition verification prompt
- Agent output verification prompt
- Final synthesis verification prompt
- Score 0-1 at each checkpoint
- Retry logic (max 2x)

Option B (Adversarial):
- Critic prompt (skeptical reviewer)
- Address critique prompt
- Re-verification prompt
- Escalation trigger (2 failed retries → Option C in Phase 2)

Thresholds:
- Pass: ≥0.7
- Retry: 0.5-0.7
- Fail: <0.5
```

**3.2 Learning Loop**
```
On task completion:
1. Calculate final verification score
2. If score ≥ 0.8:
   - Store reasoning pattern in ACT-R
   - Store code activation updates
3. Update activations for all retrieved context:
   - Used successfully: +activation
   - Not helpful: -activation (faster decay)
4. Log for analysis
```

#### MVP Deliverables Checklist

```
Infrastructure:
□ Activation engine with base/spread/context/decay
□ Generic Chunk interface
□ ChunkStore with persistence
□ ActivationIndex for fast retrieval

Reasoning:
□ Complexity assessment (simple/medium/complex)
□ Decomposition generator (structured JSON)
□ Subgoal router
□ Synthesis generator
□ Full pipeline integration

Code Context:
□ cAST parser (Python, JS, Go)
□ Function-level chunking
□ Git signal integration
□ Dependency graph extraction
□ CodeChunk implementation

Reasoning Context:
□ ReasoningChunk implementation
□ Pattern storage
□ Query similarity matching
□ Template retrieval

Verification:
□ Option A prompts (self-verify)
□ Option B prompts (adversarial)
□ Scoring logic
□ Retry logic
□ Escalation trigger (for Phase 2)

Learning:
□ Verification-based caching
□ Activation updates
□ Learning loop integration

Testing:
□ Benchmark suite (problems with known answers)
□ Baseline measurement (LLM-only accuracy)
□ AURORA-Context accuracy measurement
□ Score calibration validation
```

#### MVP Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Reasoning accuracy | ≥80% on benchmark | Correct answers / total |
| Verification catch rate | ≥70% | Errors caught / errors injected |
| Score calibration | ≥0.7 correlation | Score vs actual correctness |
| Code retrieval precision | ≥85% | Relevant chunks / retrieved chunks |
| Learning improvement | ≥5% over 20 sessions | Accuracy session N vs session 1 |
| Latency (simple) | <2s | End-to-end response time |
| Latency (complex) | <10s | End-to-end response time |

#### MVP Non-Goals (Phase 2+)

```
Explicitly NOT in MVP:
- Option C deep reasoning (Phase 2)
- KnowledgeContextProvider (Phase 2)
- Cross-context spreading activation (Phase 2)
- Replay HER advanced learning (Phase 2)
- Per-developer profiles (Phase 3)
- Transfer learning across codebases (Phase 3)
- Additional language support beyond Py/JS/Go (Phase 3)
- Production monitoring/telemetry (Phase 2)
- IDE integration (Phase 3)
```

---

## Part 16: Phase Roadmap

### Phase 1: MVP (Weeks 1-4)
**Goal**: Core reasoning + verification + code context

```
Week 1: Activation engine + reasoning pipeline
Week 2: Code context provider (cAST + Git)
Week 3: Verification layer (Options A + B)
Week 4: Learning loop + testing + benchmark
```

### Phase 2: Deep Reasoning + Knowledge (Weeks 5-8)
**Goal**: Option C + knowledge context + advanced learning

```
Week 5: Option C deep reasoning implementation
Week 6: KnowledgeContextProvider
Week 7: Cross-context spreading activation
Week 8: Replay HER + production monitoring
```

### Phase 3: Personalization + Scale (Weeks 9-12)
**Goal**: Per-user learning + additional languages + integrations

```
Week 9-10: Per-developer profiles + transfer learning
Week 11: Additional language support (Java, Rust, C++)
Week 12: IDE integration + production hardening
```

### Milestone Summary

| Phase | Duration | Key Deliverable |
|-------|----------|-----------------|
| MVP | 4 weeks | Working reasoning + code context + verification |
| Deep | 4 weeks | Option C + knowledge + advanced learning |
| Scale | 4 weeks | Personalization + languages + integrations |

---

## Part 17: SOAR-Assist Revision (Original vs Corrected)

### What Was SOAR-Assist in Original PRD?

Original SOAR-Assist was a heuristic-based orchestration:

```
Original SOAR Flow:
1. ELABORATE: Gather context
2. PROPOSE: LLM generates multiple decomposition options
3. EVALUATE: Score proposals using heuristics (importance × likelihood - effort)
4. DECIDE: Pick highest-scoring proposal
5. EXECUTE: Route to agents
6. (No verification of results)
```

**Problems with Original:**
- Evaluation was heuristic guessing, not logical verification
- No check if decomposition was actually valid
- No verification of agent outputs
- Learning based on "user satisfaction" (unreliable signal)

### Revised SOAR Logic with Verification (A+B+C)

```
┌─────────────────────────────────────────────────────────────────────┐
│              REVISED SOAR-ASSIST WITH VERIFICATION                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  PHASE 1: ELABORATE (unchanged)                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ - Retrieve context from ACT-R (reasoning patterns, code)    │    │
│  │ - Extract constraints from query                            │    │
│  │ - Identify domain and complexity                            │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  PHASE 2: PROPOSE (unchanged)                                        │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ - LLM generates decomposition (structured JSON)             │    │
│  │ - Uses retrieved patterns as templates                      │    │
│  │ - Outputs: subgoals, dependencies, agent routing            │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  PHASE 3: EVALUATE → VERIFY (CHANGED)                               │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ OLD: Heuristic scoring (importance × likelihood - effort)   │    │
│  │                                                             │    │
│  │ NEW: LLM Verification (Option A, B, or C)                   │    │
│  │ - Check completeness: Do subgoals cover the goal?           │    │
│  │ - Check consistency: No contradictions?                     │    │
│  │ - Check groundedness: Subgoals trace to given facts?        │    │
│  │ - Check routability: Agents exist for each subgoal?         │    │
│  │ - Output: Score 0-1, pass/retry/fail                        │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  PHASE 4: DECIDE (simplified)                                        │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ - If verification score ≥ 0.7: PROCEED                      │    │
│  │ - If score 0.5-0.7: RETRY decomposition (max 2x)            │    │
│  │ - If score < 0.5 or retries exhausted: ESCALATE or FAIL     │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  PHASE 5: EXECUTE + VERIFY (NEW)                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ For each subgoal:                                           │    │
│  │   1. Route to agent with context                            │    │
│  │   2. Agent produces output                                  │    │
│  │   3. VERIFY agent output (relevance, consistency, grounds)  │    │
│  │   4. If score < 0.7: RETRY or ESCALATE                      │    │
│  │   5. If score ≥ 0.7: Continue to next subgoal               │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  PHASE 6: SYNTHESIZE + FINAL VERIFY (NEW)                           │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ - Combine agent outputs into final answer                   │    │
│  │ - Verify synthesis addresses original query                 │    │
│  │ - Calculate overall confidence                              │    │
│  │ - Output: Answer + score + trace                            │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  PHASE 7: LEARN (CHANGED)                                           │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ OLD: Learn from user satisfaction                           │    │
│  │                                                             │    │
│  │ NEW: Learn from verification scores                         │    │
│  │ - If final score ≥ 0.8: Cache pattern in ACT-R              │    │
│  │ - If final score < 0.8: Do NOT cache                        │    │
│  │ - Update activations for all retrieved context              │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Changes Summary

| SOAR Phase | Original | Revised |
|------------|----------|---------|
| ELABORATE | Gather context | Unchanged - retrieve from ACT-R |
| PROPOSE | Generate decomposition | Unchanged - structured JSON |
| EVALUATE | Heuristic scoring | **LLM verification (A/B/C)** |
| DECIDE | Pick highest heuristic | **Pass/retry/escalate based on score** |
| EXECUTE | Route to agents, hope it works | **Route + verify each output** |
| (none) | (none) | **NEW: Synthesize + final verify** |
| LEARN | User satisfaction | **Verification score ≥ 0.8** |

### How LLM Verifies Without Solving

The verification LLM doesn't solve the problem - it **checks structure and logic**:

```
┌─────────────────────────────────────────────────────────────────────┐
│            VERIFICATION = CHECKING STRUCTURE, NOT SOLVING            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  What verification checks (without executing):                       │
│                                                                      │
│  1. COMPLETENESS: "Do these subgoals cover the goal?"               │
│     → Pattern matching, not execution                                │
│     → "Goal says X, Y, Z - are all addressed?"                      │
│                                                                      │
│  2. CONSISTENCY: "Do any subgoals contradict?"                      │
│     → Logical comparison, not computation                            │
│     → "SG1 says 'delete user', SG3 says 'update user' - conflict?"  │
│                                                                      │
│  3. GROUNDEDNESS: "Does each subgoal trace to a given fact?"        │
│     → Reference checking, not reasoning                              │
│     → "SG2 requires 'payment info' - is that in the given facts?"   │
│                                                                      │
│  4. ROUTABILITY: "Does an agent exist for each subgoal?"            │
│     → Lookup, not execution                                          │
│     → "SG1 needs 'research-agent' - is it available?"               │
│                                                                      │
│  ANALOGY:                                                            │
│  A teacher can grade a math problem's SETUP without computing:       │
│  - Correct formula?                                                  │
│  - Right variables identified?                                       │
│  - Logical steps in order?                                          │
│                                                                      │
│  The LLM asks: "Is this a VALID PLAN?"                              │
│  NOT: "Is this the CORRECT ANSWER?"                                 │
│                                                                      │
│  Agents do the actual solving.                                       │
│  Verification ensures the plan is sound BEFORE and AFTER execution. │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Part 18: Feedback Handling (Score < 0.8)

### What Happens When Verification Fails?

```
┌─────────────────────────────────────────────────────────────────────┐
│                    FEEDBACK HANDLING MATRIX                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  CHECKPOINT: Decomposition Verification                              │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Score ≥ 0.7                                                 │    │
│  │   → PASS: Proceed to execution                              │    │
│  │                                                             │    │
│  │ Score 0.5-0.7 (retry_count < 2)                             │    │
│  │   → RETRY: Re-decompose with feedback                       │    │
│  │   → Include: "Previous decomposition failed because: X"     │    │
│  │   → Increment retry_count                                   │    │
│  │                                                             │    │
│  │ Score 0.5-0.7 (retry_count ≥ 2)                             │    │
│  │   → ESCALATE: Trigger Option C (if Phase 2+)                │    │
│  │   → Or FAIL with explanation (if MVP)                       │    │
│  │                                                             │    │
│  │ Score < 0.5                                                 │    │
│  │   → FAIL: Decomposition fundamentally flawed                │    │
│  │   → Return error with specific issues                       │    │
│  │   → Do NOT proceed to execution                             │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  CHECKPOINT: Agent Output Verification                               │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Score ≥ 0.7                                                 │    │
│  │   → PASS: Accept output, continue to next subgoal           │    │
│  │                                                             │    │
│  │ Score 0.5-0.7 (retry_count < 2)                             │    │
│  │   → RETRY SUBGOAL: Re-run agent with feedback               │    │
│  │   → Include: "Output was insufficient because: X"           │    │
│  │   → Try different agent if available                        │    │
│  │                                                             │    │
│  │ Score 0.5-0.7 (retry_count ≥ 2)                             │    │
│  │   → PARTIAL ACCEPT: Use output but flag as low-confidence   │    │
│  │   → Continue with warning in synthesis                      │    │
│  │                                                             │    │
│  │ Score < 0.5                                                 │    │
│  │   → REJECT: Output not usable                               │    │
│  │   → Try alternative agent                                   │    │
│  │   → If no alternative: Mark subgoal as FAILED               │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  CHECKPOINT: Final Synthesis Verification                            │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Score ≥ 0.8                                                 │    │
│  │   → SUCCESS: Return answer, cache pattern                   │    │
│  │                                                             │    │
│  │ Score 0.7-0.8                                               │    │
│  │   → PARTIAL SUCCESS: Return answer with caveats             │    │
│  │   → Do NOT cache (not reliable enough)                      │    │
│  │   → Flag uncertainties in response                          │    │
│  │                                                             │    │
│  │ Score 0.5-0.7                                               │    │
│  │   → LOW CONFIDENCE: Return answer with strong warnings      │    │
│  │   → List specific issues found                              │    │
│  │   → Suggest user verify critical points                     │    │
│  │                                                             │    │
│  │ Score < 0.5                                                 │    │
│  │   → FAIL: Cannot provide reliable answer                    │    │
│  │   → Return partial results with explanation                 │    │
│  │   → Suggest alternative approaches                          │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Retry Feedback Format

When retrying, the system provides structured feedback to the LLM:

```json
{
  "retry_context": {
    "attempt": 2,
    "max_attempts": 3,
    "previous_score": 0.62,
    "issues": [
      {
        "check": "completeness",
        "score": 0.5,
        "issue": "Subgoals do not cover error handling requirement",
        "suggestion": "Add subgoal for error handling"
      },
      {
        "check": "groundedness",
        "score": 0.7,
        "issue": "Subgoal SG2 not traceable to given facts",
        "suggestion": "Justify SG2 from query constraints"
      }
    ],
    "instruction": "Revise decomposition addressing the above issues"
  }
}
```

### Learning from Failed Attempts

Even when final score < 0.8 (not cached), the system still learns:

```
┌─────────────────────────────────────────────────────────────────────┐
│                LEARNING FROM LOW SCORES                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Final Score ≥ 0.8 (SUCCESS):                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ + Cache full pattern (decomposition + routing + result)     │    │
│  │ + Boost activation of all retrieved context (+0.2)          │    │
│  │ + Store as positive example for similar queries             │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  Final Score 0.5-0.8 (PARTIAL):                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ - Do NOT cache pattern (unreliable)                         │    │
│  │ ~ Small activation boost for helpful context (+0.05)        │    │
│  │ ~ Small activation penalty for unhelpful context (-0.05)    │    │
│  │ + Log issues for analysis (what went wrong?)                │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  Final Score < 0.5 (FAILURE):                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ - Do NOT cache pattern                                      │    │
│  │ - Decay activation of retrieved reasoning patterns (-0.1)   │    │
│  │ - Mark query signature as "difficult" (needs Option C)      │    │
│  │ + Log failure for analysis                                  │    │
│  │ + If similar queries keep failing → adjust complexity model │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Agent-Specific Feedback Loop

When an agent's output fails verification:

```json
{
  "agent_feedback": {
    "agent_id": "full-stack-dev",
    "subgoal_id": "SG2",
    "output_score": 0.55,
    "issues": [
      {
        "type": "relevance",
        "detail": "Output addresses login but subgoal was about registration"
      },
      {
        "type": "completeness",
        "detail": "Missing error handling for duplicate email"
      }
    ],
    "action_taken": "retry_with_feedback",
    "retry_prompt_addition": "Focus specifically on REGISTRATION flow, not login. Include error handling for duplicate email addresses.",
    "retry_score": 0.78,
    "final_status": "accepted_with_warning"
  }
}
```

---

## Part 19: Knowledge Context Provider (Phase 2)

### What is "Knowledge" in Phase 2?

Knowledge refers to **domain-specific information** that is neither code nor reasoning patterns:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    KNOWLEDGE CONTEXT TYPES                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. API DOCUMENTATION                                                │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ - External API references (Stripe, AWS, OpenAI, etc.)       │    │
│  │ - Internal API specifications                               │    │
│  │ - Endpoint signatures, parameters, response formats         │    │
│  │ - Rate limits, authentication requirements                  │    │
│  │                                                             │    │
│  │ Example chunk:                                              │    │
│  │ {                                                           │    │
│  │   "type": "api_doc",                                        │    │
│  │   "source": "stripe",                                       │    │
│  │   "endpoint": "POST /v1/charges",                           │    │
│  │   "parameters": {...},                                      │    │
│  │   "activation": 0.7                                         │    │
│  │ }                                                           │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  2. DOMAIN SCHEMAS                                                   │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ - Database schemas                                          │    │
│  │ - Data models and relationships                             │    │
│  │ - Business entity definitions                               │    │
│  │ - Validation rules and constraints                          │    │
│  │                                                             │    │
│  │ Example chunk:                                              │    │
│  │ {                                                           │    │
│  │   "type": "schema",                                         │    │
│  │   "entity": "User",                                         │    │
│  │   "fields": ["id", "email", "role", "created_at"],          │    │
│  │   "constraints": ["email must be unique"],                  │    │
│  │   "relationships": ["has_many: Orders"],                    │    │
│  │   "activation": 0.85                                        │    │
│  │ }                                                           │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  3. TEAM CONVENTIONS                                                 │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ - Coding standards and style guides                         │    │
│  │ - Architecture decisions (ADRs)                             │    │
│  │ - Naming conventions                                        │    │
│  │ - Error handling patterns                                   │    │
│  │ - Testing requirements                                      │    │
│  │                                                             │    │
│  │ Example chunk:                                              │    │
│  │ {                                                           │    │
│  │   "type": "convention",                                     │    │
│  │   "category": "error_handling",                             │    │
│  │   "rule": "All API errors must include error_code field",   │    │
│  │   "rationale": "Enables client-side error mapping",         │    │
│  │   "activation": 0.6                                         │    │
│  │ }                                                           │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  4. BUSINESS RULES                                                   │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ - Domain-specific logic                                     │    │
│  │ - Compliance requirements                                   │    │
│  │ - SLA definitions                                           │    │
│  │ - Security policies                                         │    │
│  │                                                             │    │
│  │ Example chunk:                                              │    │
│  │ {                                                           │    │
│  │   "type": "business_rule",                                  │    │
│  │   "domain": "payments",                                     │    │
│  │   "rule": "Refunds over $1000 require manager approval",    │    │
│  │   "source": "compliance_doc_v2",                            │    │
│  │   "activation": 0.75                                        │    │
│  │ }                                                           │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  5. HISTORICAL CONTEXT                                               │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ - Past incident reports                                     │    │
│  │ - Previous decisions and their outcomes                     │    │
│  │ - Known issues and workarounds                              │    │
│  │ - Migration notes                                           │    │
│  │                                                             │    │
│  │ Example chunk:                                              │    │
│  │ {                                                           │    │
│  │   "type": "historical",                                     │    │
│  │   "category": "incident",                                   │    │
│  │   "summary": "Auth service timeout caused by N+1 query",    │    │
│  │   "resolution": "Added eager loading in user_loader",       │    │
│  │   "date": "2024-03-15",                                     │    │
│  │   "activation": 0.45                                        │    │
│  │ }                                                           │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### How Knowledge Integrates with Reasoning

```
Query: "Add Stripe payment processing to checkout"

Retrieved Context (unified):
├── Reasoning Pattern: "payment integration" decomposition template
├── Code: checkout_controller.py, payment_service.py, order_model.py
├── Knowledge:
│   ├── API: Stripe /v1/charges endpoint spec
│   ├── Schema: Order entity with payment_status field
│   ├── Convention: "All payments must log transaction_id"
│   └── Business Rule: "Refunds over $1000 require approval"
```

### KnowledgeContextProvider Implementation (Phase 2)

```
Components:
- Document parser (markdown, JSON, YAML)
- Chunk extractor (API specs, schemas, rules)
- Source tracking (where did this knowledge come from?)
- Freshness management (when was it last updated?)
- Conflict detection (contradicting rules?)

Activation signals:
- Usage frequency (how often is this knowledge retrieved?)
- Recency (when was it last used successfully?)
- Source authority (official docs vs informal notes)
- Relevance to current domain

Integration:
- Spreads activation to related code chunks
- Informs decomposition (constraints from business rules)
- Validates agent outputs (does output comply with conventions?)
```

### Why Knowledge is Phase 2 (Not MVP)

| Reason | Detail |
|--------|--------|
| MVP complexity | Code + Reasoning is enough to validate core loop |
| Ingestion effort | Knowledge requires parsing diverse formats |
| Quality variance | API docs are structured; conventions may be scattered |
| Value validation | Need to prove reasoning + code works first |

### Knowledge in Context

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CONTEXT RETRIEVAL ORDER                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  MVP (Phase 1):                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Query → Retrieve Reasoning Patterns                         │    │
│  │      → Retrieve Code Chunks                                 │    │
│  │      → Decompose + Verify + Execute + Verify                │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  Phase 2 (with Knowledge):                                           │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Query → Retrieve Reasoning Patterns                         │    │
│  │      → Retrieve Code Chunks                                 │    │
│  │      → Retrieve Knowledge (APIs, schemas, rules)  ← NEW     │    │
│  │      → Decompose (informed by knowledge constraints)        │    │
│  │      → Verify (check against business rules)      ← ENHANCED│    │
│  │      → Execute + Verify                                     │    │
│  │      → Validate output compliance                 ← NEW     │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Part 20: Complexity Routing Clarification

### Simple = No Decomposition, No Verification

| Complexity | Flow | Overhead |
|------------|------|----------|
| **SIMPLE** | Query → LLM → Response | **None** - direct pass-through |
| **MEDIUM** | Query → Decompose → Verify (A) → Agents → Verify → Synthesize | Self-verify |
| **COMPLEX** | Query → Decompose → Verify (B) → Agents → Verify → Synthesize | Adversarial |
| **CRITICAL** | Query → Multi-path → Debate → Verify (C) → Execute → Deep Verify | Full debate |

**SIMPLE queries skip the entire reasoning pipeline.** No decomposition, no verification, no agents. The LLM answers directly.

```
SIMPLE FLOW:
┌─────────┐     ┌─────────┐     ┌──────────┐
│  Query  │────▶│   LLM   │────▶│ Response │
└─────────┘     └─────────┘     └──────────┘

MEDIUM+ FLOW:
┌─────────┐     ┌───────────┐     ┌────────┐     ┌────────┐     ┌──────────┐
│  Query  │────▶│ Decompose │────▶│ Verify │────▶│ Agents │────▶│ Response │
└─────────┘     └───────────┘     └────────┘     └────────┘     └──────────┘
```

---

## Part 21: Dual Activation - Code vs Reasoning ACT-R

### How ContextMind (Code) and Reasoning ACT-R Work Together

They have **different activation signals** but **unified retrieval**:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DUAL ACTIVATION SOURCES                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  CODE CHUNKS (ContextMind):              REASONING PATTERNS:         │
│  ┌─────────────────────────┐            ┌─────────────────────────┐ │
│  │ Activation signals:     │            │ Activation signals:     │ │
│  │ - Git commit frequency  │            │ - Query similarity      │ │
│  │ - Git recency           │            │ - Past usage frequency  │ │
│  │ - Dependency graph      │            │ - Past usage recency    │ │
│  │ - Import relationships  │            │ - Verification scores   │ │
│  │ - Co-edit patterns      │            │ - Domain match          │ │
│  └───────────┬─────────────┘            └───────────┬─────────────┘ │
│              │                                      │                │
│              └──────────────┬───────────────────────┘                │
│                             │                                        │
│                             ▼                                        │
│              ┌─────────────────────────────────────┐                │
│              │     UNIFIED ACTIVATION ENGINE       │                │
│              │                                     │                │
│              │  For each chunk type:               │                │
│              │  activation = base + spread + boost │                │
│              │                                     │                │
│              │  Base-level:                        │                │
│              │  - Code: git_frequency + recency    │                │
│              │  - Reasoning: usage_freq + recency  │                │
│              │                                     │                │
│              │  Spreading:                         │                │
│              │  - Code: imports, dependencies      │                │
│              │  - Reasoning: domain, query terms   │                │
│              │                                     │                │
│              │  Context boost:                     │                │
│              │  - Both: current query overlap      │                │
│              └─────────────────────────────────────┘                │
│                             │                                        │
│                             ▼                                        │
│              ┌─────────────────────────────────────┐                │
│              │     UNIFIED RETRIEVAL               │                │
│              │                                     │                │
│              │  retrieve(query, budget=N):         │                │
│              │    1. Calculate activation for ALL  │                │
│              │       chunks (code + reasoning)     │                │
│              │    2. Rank by activation score      │                │
│              │    3. Return top N within budget    │                │
│              │    4. Mix may include both types    │                │
│              └─────────────────────────────────────┘                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Activation Signal Mapping

| Chunk Type | Signal | How Captured |
|------------|--------|--------------|
| **Code** | Frequency | `git log --follow <file>` count |
| **Code** | Recency | `git log -1 --format=%ct <file>` |
| **Code** | Dependencies | AST import parsing |
| **Code** | Co-edit | Files changed together in commits |
| **Reasoning** | Frequency | Internal usage counter |
| **Reasoning** | Recency | Timestamp of last retrieval |
| **Reasoning** | Success | Verification score when used |
| **Reasoning** | Domain | Extracted keywords from pattern |

### Cross-Type Spreading

Code and reasoning can **prime each other**:

```
Query: "Fix authentication bug"

1. "authentication" activates:
   - Reasoning: "auth debugging" pattern
   - Code: authenticate.py, session.py, middleware.py

2. Spreading from reasoning pattern:
   - Pattern mentions "check token expiry"
   - Boosts: token_validator.py (even if not in initial code match)

3. Spreading from code:
   - authenticate.py imports user_model.py
   - Boosts: user_model.py activation
```

---

## Part 22: Integration with AI Agents (Claude Code, OpenCode, Ampcode, Droid)

### The Problem

AURORA needs to work **inside** existing AI CLI agents, not replace them:
- Claude Code, OpenCode, Ampcode, Droid all have their own orchestration
- All support MCP (Model Context Protocol)
- We can't modify their internal code

### Solution: MCP Server (Model Context Protocol)

AURORA exposes itself as an **MCP server** that any MCP-compatible CLI agent can call:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MCP SERVER INTEGRATION                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │
│  │ Claude Code │  │  OpenCode   │  │   Ampcode   │  │   Droid   │  │
│  │             │  │             │  │             │  │           │  │
│  │  (has MCP)  │  │  (has MCP)  │  │  (has MCP)  │  │ (has MCP) │  │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────┬─────┘  │
│         │                │                │               │         │
│         └────────────────┴────────────────┴───────────────┘         │
│                                   │                                  │
│                                   ▼                                  │
│         ┌────────────────────────────────────┐                      │
│         │        AURORA MCP SERVER           │                      │
│         │                                    │                      │
│         │  Tools exposed:                    │                      │
│         │  ┌──────────────────────────────┐ │                      │
│         │  │ aurora_assess               │ │                      │
│         │  │ - Input: query              │ │                      │
│         │  │ - Output: complexity, route │ │                      │
│         │  └──────────────────────────────┘ │                      │
│         │  ┌──────────────────────────────┐ │                      │
│         │  │ aurora_decompose            │ │                      │
│         │  │ - Input: query, context     │ │                      │
│         │  │ - Output: subgoals JSON     │ │                      │
│         │  └──────────────────────────────┘ │                      │
│         │  ┌──────────────────────────────┐ │                      │
│         │  │ aurora_verify               │ │                      │
│         │  │ - Input: decomposition      │ │                      │
│         │  │ - Output: score, issues     │ │                      │
│         │  └──────────────────────────────┘ │                      │
│         │  ┌──────────────────────────────┐ │                      │
│         │  │ aurora_retrieve_context     │ │                      │
│         │  │ - Input: query, budget      │ │                      │
│         │  │ - Output: relevant chunks   │ │                      │
│         │  └──────────────────────────────┘ │                      │
│         │  ┌──────────────────────────────┐ │                      │
│         │  │ aurora_learn                │ │                      │
│         │  │ - Input: result, score      │ │                      │
│         │  │ - Output: cached/not        │ │                      │
│         │  └──────────────────────────────┘ │                      │
│         │                                    │                      │
│         └────────────────────────────────────┘                      │
│                          │                                           │
│                          ▼                                           │
│         ┌────────────────────────────────────┐                      │
│         │        AURORA CORE LIBRARY         │                      │
│         │  (same code, different interface)  │                      │
│         └────────────────────────────────────┘                      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Usage from Claude Code

```json
// In ~/.claude/settings.json or project settings
{
  "mcpServers": {
    "aurora": {
      "command": "aurora-mcp-server",
      "args": ["--project", "/path/to/project"]
    }
  }
}
```

Then Claude Code can call:
```
User: "Build auth feature"

Claude Code internally:
1. Calls aurora_assess("Build auth feature") → COMPLEX
2. Calls aurora_retrieve_context("Build auth feature", budget=10)
   → Returns relevant code + reasoning patterns
3. Calls aurora_decompose("Build auth feature", context)
   → Returns subgoals JSON
4. Calls aurora_verify(decomposition) → score 0.85, PASS
5. Claude Code executes subgoals using its own agents
6. Calls aurora_learn(result, score=0.82) → cached
```

### Integration Matrix

| Agent | Integration Method | Effort |
|-------|-------------------|--------|
| Claude Code | MCP Server | Low (native support) |
| OpenCode | MCP Server | Low (native support) |
| Ampcode | MCP Server | Low (native support) |
| Droid | MCP Server | Low (native support) |
| Custom | Library import | Low |

### MCP State Reporting + Verbosity Levels

The MCP server provides **declarative progress state** that CLI agents can display:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    VERBOSITY LEVELS                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  QUIET MODE (default):                                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ aurora: assessing... complex → decomposing → routing        │   │
│  │ aurora: done (score: 0.85)                                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  NORMAL MODE (-v):                                                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ aurora: assessing complexity...                             │   │
│  │ aurora: → COMPLEX (score: 0.82)                             │   │
│  │ aurora: decomposing into subgoals...                        │   │
│  │ aurora: → 3 subgoals created                                │   │
│  │ aurora: verifying decomposition (adversarial)...            │   │
│  │ aurora: → score: 0.85, PASS                                 │   │
│  │ aurora: routing to agents...                                │   │
│  │ aurora: → SG1 → full-stack-dev                              │   │
│  │ aurora: → SG2 → research-agent                              │   │
│  │ aurora: verifying outputs...                                │   │
│  │ aurora: → all passed                                        │   │
│  │ aurora: synthesizing...                                     │   │
│  │ aurora: done (final score: 0.85, cached: yes)               │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  VERBOSE MODE (-vv):                                                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ aurora: assessing complexity...                             │   │
│  │   keywords: [auth, feature, implement] → score: 0.7         │   │
│  │   llm verification: COMPLEX (confidence: 0.82)              │   │
│  │ aurora: retrieving context (budget: 10)...                  │   │
│  │   reasoning patterns: 2 (activation: 0.8, 0.6)              │   │
│  │   code chunks: 5 (auth.py:0.9, session.py:0.7, ...)         │   │
│  │ aurora: decomposing...                                      │   │
│  │   subgoal 1: "Research OAuth providers" → research-agent    │   │
│  │   subgoal 2: "Implement OAuth flow" → full-stack-dev        │   │
│  │   subgoal 3: "Write tests" → qa-test-architect              │   │
│  │ aurora: verifying (adversarial)...                          │   │
│  │   completeness: 0.9                                         │   │
│  │   consistency: 1.0                                          │   │
│  │   groundedness: 0.8                                         │   │
│  │   routability: 0.85                                         │   │
│  │   overall: 0.85 → PASS                                      │   │
│  │ ... (full trace)                                            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  JSON MODE (--json):                                                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ {"stage":"assess","status":"complete","complexity":"complex"}│   │
│  │ {"stage":"decompose","status":"complete","subgoals":3}       │   │
│  │ {"stage":"verify","status":"complete","score":0.85}          │   │
│  │ {"stage":"route","status":"in_progress","current":"SG1"}     │   │
│  │ {"stage":"done","final_score":0.85,"cached":true}            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### MCP Progress Notifications

The MCP server emits **progress notifications** that CLI agents can subscribe to:

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/progress",
  "params": {
    "progressToken": "task-123",
    "stage": "verify",
    "status": "in_progress",
    "detail": "Running adversarial verification...",
    "progress": 0.6,
    "verbose": {
      "checks": {
        "completeness": 0.9,
        "consistency": 1.0,
        "groundedness": null,
        "routability": null
      }
    }
  }
}
```

CLI agents can choose how much to display based on user preference.

---

## Part 23: Domain Knowledge Capture in MVP

### Clarification: Knowledge Provider is Phase 2

In MVP, we have:
- **CodeContextProvider** - cAST + Git signals
- **ReasoningContextProvider** - Query patterns + decomposition templates

**KnowledgeContextProvider (APIs, schemas, rules) is Phase 2.**

### What MVP Does Capture

Even without explicit KnowledgeContextProvider, some domain knowledge is implicitly captured:

```
┌─────────────────────────────────────────────────────────────────────┐
│                MVP IMPLICIT KNOWLEDGE CAPTURE                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  FROM CODE CHUNKS:                                                   │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ - Function docstrings → informal API docs                   │    │
│  │ - Type hints → schema information                           │    │
│  │ - Constants/configs → business rules                        │    │
│  │ - Comments → conventions and rationale                      │    │
│  │                                                             │    │
│  │ Example: MAX_REFUND_AMOUNT = 1000  # Requires manager approval   │
│  │ → Implicitly captures business rule                         │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  FROM REASONING PATTERNS:                                            │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ - Successful decompositions encode domain structure         │    │
│  │ - Routing decisions encode which agents handle what         │    │
│  │ - Verification feedback encodes constraints                 │    │
│  │                                                             │    │
│  │ Example: Pattern "payment flow" always routes to            │    │
│  │ compliance-check agent first → learned domain rule          │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  PHASE 2 ADDS EXPLICIT KNOWLEDGE:                                   │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ - Parsed API documentation                                  │    │
│  │ - Structured schema definitions                             │    │
│  │ - Explicit business rules                                   │    │
│  │ - Team conventions from docs                                │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Part 24: What is "Core"?

### Core = Foundation Layer (No LLM, No Parsing)

```
core/
├── activation/     # ACT-R math (base + spread + decay)
│   ├── engine.py         # Main activation calculator
│   ├── base_level.py     # Frequency + recency decay
│   ├── spreading.py      # Context spreading
│   └── retrieval.py      # Threshold-based retrieval
├── chunks/         # Data structures
│   ├── base.py           # Abstract Chunk interface
│   ├── code_chunk.py     # CodeChunk implementation
│   └── reasoning_chunk.py # ReasoningChunk implementation
├── store/          # Persistence
│   ├── base.py           # Abstract Store interface
│   ├── sqlite.py         # SQLite implementation
│   └── memory.py         # In-memory (for testing)
└── types.py        # Shared types (ChunkID, Activation, etc.)
```

**Core contains:**
- ACT-R activation math
- Chunk type definitions
- Persistence layer
- No LLM calls
- No code parsing
- No external dependencies (except standard library)

**Why separate?**
- Can be used standalone for custom integrations
- Other packages build on top
- Easy to test in isolation

---

## Part 25: Installation Options

### Package Installation

```bash
# Full install (everything - most users)
pip install aurora-context[all]

# Just MCP server (for CLI agent integration)
pip install aurora-context[mcp]

# Just core (for custom integrations / library use)
pip install aurora-context-core

# Development install (all packages editable)
git clone https://github.com/your-org/aurora-context
cd aurora-context
make install-dev
```

### What Each Install Includes

| Install | Packages Included | Use Case |
|---------|------------------|----------|
| `aurora-context[all]` | core + reasoning + context-code + context-reasoning + mcp + cli | Full functionality |
| `aurora-context[mcp]` | core + reasoning + context-code + context-reasoning + mcp | MCP integration only |
| `aurora-context-core` | core only | Custom integrations |

### Runtime Dependencies

```
aurora-context-core:
  - (none - pure Python)

aurora-context[mcp]:
  - mcp (Model Context Protocol SDK)
  - tree-sitter (for code parsing)
  - tree-sitter-python, tree-sitter-javascript, tree-sitter-go
  - httpx (for LLM API calls)
  - pydantic (for JSON schemas)

aurora-context[all]:
  - (all above)
  - click (for CLI)
  - rich (for CLI output)
```

---

## Part 26: Repository Structure

### Recommended Monorepo Layout

```
aurora-context/
├── README.md
├── pyproject.toml                 # Root project config
├── Makefile                       # Common commands
│
├── packages/
│   ├── core/                      # Core library (no deps on others)
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   │   └── aurora_core/
│   │   │       ├── __init__.py
│   │   │       ├── activation/    # ACT-R activation engine
│   │   │       │   ├── __init__.py
│   │   │       │   ├── engine.py
│   │   │       │   ├── base_level.py
│   │   │       │   ├── spreading.py
│   │   │       │   └── retrieval.py
│   │   │       ├── chunks/        # Chunk types
│   │   │       │   ├── __init__.py
│   │   │       │   ├── base.py
│   │   │       │   ├── code_chunk.py
│   │   │       │   └── reasoning_chunk.py
│   │   │       ├── store/         # Persistence
│   │   │       │   ├── __init__.py
│   │   │       │   ├── base.py
│   │   │       │   ├── sqlite.py
│   │   │       │   └── memory.py
│   │   │       └── types.py       # Shared types
│   │   └── tests/
│   │
│   ├── reasoning/                 # Reasoning pipeline
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   │   └── aurora_reasoning/
│   │   │       ├── __init__.py
│   │   │       ├── pipeline.py    # Main orchestration
│   │   │       ├── assessment.py  # Complexity assessment
│   │   │       ├── decompose.py   # Structured decomposition
│   │   │       ├── verify.py      # Verification (A/B/C)
│   │   │       ├── synthesize.py  # Result synthesis
│   │   │       ├── learn.py       # Learning loop
│   │   │       └── prompts/       # LLM prompts
│   │   │           ├── decompose.py
│   │   │           ├── verify_self.py
│   │   │           ├── verify_adversarial.py
│   │   │           └── verify_deep.py
│   │   └── tests/
│   │
│   ├── context-code/              # Code context provider
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   │   └── aurora_context_code/
│   │   │       ├── __init__.py
│   │   │       ├── provider.py    # CodeContextProvider
│   │   │       ├── parser.py      # cAST tree-sitter wrapper
│   │   │       ├── git.py         # Git signal extraction
│   │   │       ├── chunker.py     # Function-level chunking
│   │   │       └── languages/     # Language-specific parsers
│   │   │           ├── python.py
│   │   │           ├── javascript.py
│   │   │           └── go.py
│   │   └── tests/
│   │
│   ├── context-reasoning/         # Reasoning context provider
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   │   └── aurora_context_reasoning/
│   │   │       ├── __init__.py
│   │   │       ├── provider.py
│   │   │       ├── patterns.py
│   │   │       └── similarity.py
│   │   └── tests/
│   │
│   ├── mcp-server/                # MCP server for agent integration
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   │   └── aurora_mcp/
│   │   │       ├── __init__.py
│   │   │       ├── server.py      # MCP server implementation
│   │   │       ├── tools.py       # Tool definitions
│   │   │       └── handlers.py    # Request handlers
│   │   └── tests/
│   │
│   └── cli/                       # CLI interface
│       ├── pyproject.toml
│       ├── src/
│       │   └── aurora_cli/
│       │       ├── __init__.py
│       │       ├── main.py
│       │       ├── commands/
│       │       │   ├── assess.py
│       │       │   ├── decompose.py
│       │       │   ├── verify.py
│       │       │   ├── context.py
│       │       │   └── learn.py
│       │       └── output.py
│       └── tests/
│
├── docs/
│   ├── architecture.md
│   ├── getting-started.md
│   ├── integration-guide.md
│   └── api-reference.md
│
├── examples/
│   ├── claude-code-integration/
│   ├── standalone-usage/
│   └── custom-provider/
│
└── benchmarks/
    ├── reasoning-accuracy/
    ├── retrieval-precision/
    └── datasets/
```

### Package Dependencies

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PACKAGE DEPENDENCY GRAPH                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│                         ┌─────────┐                                 │
│                         │  core   │  ← No dependencies              │
│                         └────┬────┘                                 │
│                              │                                       │
│           ┌──────────────────┼──────────────────┐                   │
│           │                  │                  │                   │
│           ▼                  ▼                  ▼                   │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐       │
│  │ context-code    │ │context-reasoning│ │   reasoning     │       │
│  │ (depends: core) │ │ (depends: core) │ │ (depends: core) │       │
│  └────────┬────────┘ └────────┬────────┘ └────────┬────────┘       │
│           │                   │                   │                 │
│           └───────────────────┼───────────────────┘                 │
│                               │                                      │
│                               ▼                                      │
│                    ┌─────────────────────┐                          │
│                    │     mcp-server      │                          │
│                    │ (depends: all above)│                          │
│                    └──────────┬──────────┘                          │
│                               │                                      │
│                               ▼                                      │
│                    ┌─────────────────────┐                          │
│                    │        cli          │                          │
│                    │ (depends: all above)│                          │
│                    └─────────────────────┘                          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Core is dependency-free** - Can be used standalone
2. **Context providers are pluggable** - Easy to add new types
3. **MCP server wraps everything** - Single integration point
4. **CLI is thin** - Just calls library functions

### Development Commands

```makefile
# Makefile
install:
	pip install -e packages/core
	pip install -e packages/reasoning
	pip install -e packages/context-code
	pip install -e packages/context-reasoning
	pip install -e packages/mcp-server
	pip install -e packages/cli

test:
	pytest packages/*/tests

test-core:
	pytest packages/core/tests

lint:
	ruff check packages/

type-check:
	mypy packages/

build:
	python -m build packages/core
	python -m build packages/mcp-server
	python -m build packages/cli

mcp-server:
	aurora-mcp-server --project .

cli:
	aurora --help
```
