# AURORA Framework - Unified MVP Specification v3.0

**Date:** December 20, 2025
**Status:** ✅ COMPLETE - Ready for Implementation
**Combines:** AURORA-MVP-Correction.md + COMPLETE-SPEC-v2.1-SUMMARY.md + New MVP Additions

---

## Executive Summary

**AURORA** is a reasoning and orchestration framework that solves LLM reasoning failures through **verification-driven decomposition**. Unlike basic orchestration frameworks, AURORA adds a critical verification layer that catches invalid reasoning before wasting compute and money.

### Core Innovation

> **Decomposition doesn't solve reasoning - it just distributes it.**
> **Verification ensures quality at every step.**

### The Architecture

```
DECOMPOSE ──▶ VERIFY ──▶ AGENTS ──▶ VERIFY ──▶ RESPOND
    │           │          │          │
   LLM        LLM        WORK       LLM
(structure)  (check)    (solve)   (check)
```

### What Makes AURORA Different

| Component | What It Does | Why It Matters |
|-----------|--------------|----------------|
| **Hybrid Verification** | Self-verify (cheap) or adversarial (robust) based on complexity | Catches reasoning errors without blind trust |
| **Structured JSON** | All reasoning in traceable JSON format | Auditable, cacheable, debuggable |
| **Complexity Routing** | Different verification depth by query type | Optimize cost vs quality trade-off |
| **ACT-R Learning** | Cache verified patterns, avoid recomputation | Gets better over time |
| **Cost Budget Enforcement** | Hard limits prevent runaway spending | Safety for personal users |
| **LLM Preference Routing** | Auto-select cheap/expensive models | 40% cost savings on model selection |

---

## Part 1: Problem Analysis

### Why LLMs Fail at Complex Reasoning

| Failure Mode | Description | How AURORA Addresses |
|--------------|-------------|----------------------|
| **Attention degradation** | Each step compounds errors | Structured decomposition + verification |
| **No working memory** | Can't maintain state | ACT-R persistent memory |
| **Probability collapse** | Unreliable on novel problems | Multiple verification passes |
| **No self-verification** | Can't distinguish plausible from valid | Explicit verification layer |
| **Hallucination as feature** | Generates coherent nonsense | Groundedness checks in JSON |

### What Original Orchestration Frameworks Miss

| Component | What It Claims | What It Actually Does | Gap |
|-----------|----------------|----------------------|-----|
| Decomposition | "Breaks complex problems" | Just structured prompting | No validation of quality |
| Agent Routing | "Specialized expertise" | Distribution only | No output verification |
| ACT-R Memory | "Learning from experience" | Caching patterns | Doesn't verify correctness |

**Critical insight:** Without verification, you inherit all the reasoning failures you claim to solve.

---

## Part 2: The Corrected Architecture

### Four Core Steps

| Step | Actor | Purpose | Cost | Validation |
|------|-------|---------|------|------------|
| **1. Decompose** | LLM | Break problem into subgoals (JSON) | $0.01 | Structure check |
| **2. Verify Decomposition** | LLM | Is decomposition valid/complete? | $0.01 | Score 0-1 |
| **3. Execute Agents** | Agents | Actually solve each subgoal | $0.02-0.10 | Work happens here |
| **4. Verify Results** | LLM | Are results correct/consistent? | $0.01 | Score 0-1 |

### Key Principles

1. **Verification is cheap** (~$0.01 per check) vs agent work ($0.02-0.10)
2. **Catch errors early** - Bad decomposition costs $0.01 to catch, $0.10 if agents run on it
3. **Complexity-based depth** - Simple queries skip verification, complex get adversarial review
4. **Always produce output** - Even failed verifications return best-effort results

---

## Part 3: Hybrid Verification Strategy (Options A, B, C)

### Complexity-Based Routing

```
┌─────────────────────────────────────────────────────────────┐
│                    COMPLEXITY ROUTER                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  SIMPLE ───▶ Direct LLM, no verification                   │
│              Cost: 1x base                                  │
│                                                             │
│  MEDIUM ───▶ Decompose + Option A (self-verify) + agents   │
│              Cost: 3-4x base                                │
│                                                             │
│  COMPLEX ──▶ Decompose + Option B (adversarial) + agents   │
│              Cost: 5-6x base                                │
│                                                             │
│  CRITICAL ─▶ Option C (deep reasoning) - Phase 2           │
│              Cost: 8-10x base                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Option A: Self-Verification (MVP)

**How it works:**
- Same LLM reviews its own decomposition/results
- Checks: completeness, consistency, groundedness

**Strengths:**
- Fast, low cost (~$0.01 per verification)
- Catches obvious gaps and structural issues

**Limitations:**
- Same blind spots as the original LLM
- May miss subtle logical flaws

**When to use:** Medium complexity queries (standard use)

### Option B: Adversarial Verification (MVP)

**How it works:**
- Second LLM (or adversarial prompt) acts as skeptical critic
- Actively seeks flaws, alternative interpretations, hidden assumptions

**Strengths:**
- Catches subtle errors Option A misses
- Different perspective reveals blind spots

**Limitations:**
- ~2x cost of Option A
- Slower (sequential LLM calls)

**When to use:** Complex/high-stakes queries

### Option C: Deep Reasoning (Phase 2)

**How it works:**
- Multi-step reasoning chains with explicit intermediate conclusions
- Each step verified before proceeding
- External knowledge integration (RAG)

**Strengths:**
- Highest accuracy on novel problems
- Explicit reasoning trace

**Limitations:**
- 8-10x cost
- Slow (multiple sequential passes)

**When to use:** Critical queries, or when Option B fails 2+ times

### Verification Scoring

**Each verification returns structured score:**

```json
{
  "score": 0.85,
  "reasoning": "Decomposition covers all aspects of query...",
  "issues": [
    {"severity": "minor", "description": "Subgoal 3 could be more specific"}
  ],
  "decision": "PASS"
}
```

**Score thresholds:**
- **≥ 0.8:** PASS + cache pattern (success)
- **0.7-0.8:** PASS but don't cache (uncertain)
- **0.5-0.7:** RETRY with feedback (fixable issues)
- **< 0.5:** FAIL (fundamental problems)

---

## Part 4: Structured JSON Contracts

### Why JSON?

- **Parseable:** Programmatic validation of structure
- **Traceable:** Every inference has explicit sources
- **Auditable:** Full reasoning chain preserved
- **Cacheable:** ACT-R can store/retrieve patterns

### 4.1 Decomposition Output

```json
{
  "decomposition": {
    "id": "decomp-uuid-123",
    "original_query": "Design a migration strategy for X to Y",
    "complexity": "complex",

    "given": [
      {"id": "G1", "fact": "Current system is X", "source": "query"},
      {"id": "G2", "fact": "Target system is Y", "source": "context"}
    ],

    "goal": {
      "description": "Provide step-by-step migration strategy",
      "success_criteria": [
        "All components covered",
        "Dependencies identified",
        "Risks assessed"
      ]
    },

    "subgoals": [
      {
        "id": "SG1",
        "description": "Analyze current X architecture",
        "requires": ["G1"],
        "agent": "research-agent",
        "expected_output": "Architecture document",
        "depends_on": [],
        "complexity": "medium",
        "max_retries": 1
      },
      {
        "id": "SG2",
        "description": "Map X components to Y equivalents",
        "requires": ["G1", "G2", "SG1.output"],
        "agent": "analysis-agent",
        "expected_output": "Component mapping table",
        "depends_on": ["SG1"],
        "complexity": "complex",
        "max_retries": 2
      },
      {
        "id": "SG3",
        "description": "Design migration sequence",
        "requires": ["SG2.output"],
        "agent": "strategy-agent",
        "expected_output": "Step-by-step migration plan",
        "depends_on": ["SG2"],
        "complexity": "complex",
        "max_retries": 2
      }
    ],

    "execution_order": ["SG1", "SG2", "SG3"],
    "estimated_cost_usd": 0.45,
    "estimated_time_sec": 180
  }
}
```

### 4.2 Verification Output

```json
{
  "verification": {
    "checkpoint": "decomposition",
    "score": 0.85,
    "breakdown": {
      "completeness": 0.9,
      "consistency": 0.8,
      "groundedness": 0.85,
      "routability": 0.85
    },
    "decision": "PASS",
    "reasoning": "Decomposition covers all query aspects. Dependencies clear. All subgoals have executable agents.",
    "issues": [
      {
        "severity": "minor",
        "component": "SG2",
        "description": "Expected output could be more specific",
        "suggestion": "Specify format (JSON vs Markdown)"
      }
    ],
    "confidence": 0.85
  }
}
```

### 4.3 Agent Result

```json
{
  "agent_result": {
    "subgoal_id": "SG1",
    "agent": "research-agent",
    "success": true,
    "output": "X uses microservices architecture with 12 services...",
    "metadata": {
      "execution_time_sec": 45,
      "cost_usd": 0.12,
      "sources": ["documentation", "code analysis"],
      "confidence": 0.9
    }
  }
}
```

### 4.4 Final Synthesis

```json
{
  "synthesis": {
    "query": "Design migration strategy for X to Y",
    "answer": "Migration strategy in 3 phases...",
    "confidence": 0.85,
    "sources": ["SG1.output", "SG2.output", "SG3.output"],
    "verification_score": 0.85,
    "reasoning_trace": [
      "Analyzed current architecture (SG1)",
      "Mapped components (SG2)",
      "Designed sequence (SG3)"
    ],
    "caveats": ["Assumes Y supports async patterns"],
    "cache_worthy": true
  }
}
```

---

## Part 5: Self-Correction with Complexity-Based Retries

### How Self-Correction Works

**Self-correction happens at TWO checkpoints:**

1. **After DECOMPOSE → VERIFY:** If decomposition invalid, retry decomposition
2. **After AGENTS → VERIFY:** If agent output invalid, retry agent execution

**Critical:** Self-correction does NOT loop back to DECOMPOSE after agent failure. It only retries the agent.

### Retry Logic by Complexity

```json
{
  "self_correction": {
    "enabled": true,
    "retry_by_complexity": {
      "simple": 0,
      "medium": 1,
      "complex": 2,
      "critical": 3
    },
    "max_cost_per_retry_usd": 0.50
  }
}
```

**Behavior:**

```python
def execute_subgoal_with_retry(subgoal):
    max_retries = get_retries_for_complexity(subgoal.complexity)

    for attempt in range(1, max_retries + 1):
        # Execute agent
        result = agent.invoke(subgoal)

        # Verify result
        verification = verify_agent_output(result, subgoal)

        if verification.score >= 0.7:
            return result  # Success

        # Failed validation
        if attempt < max_retries:
            # Inject failure context for next retry
            subgoal.context += f"\n\nPrevious attempt failed:\n"
            subgoal.context += f"Score: {verification.score}\n"
            subgoal.context += f"Issues: {verification.reasoning}\n"
            subgoal.context += f"Fix these issues in your next attempt."
        else:
            # Exhausted retries, use fallback LLM
            return fallback_llm.execute(subgoal)
```

### Two Verification Loops (Don't Confuse Them)

**Loop 1: DECOMPOSE → VERIFY (structural)**
```
DECOMPOSE → VERIFY
    ↑          │
    └─(retry)──┘
```
**Checks:** Is decomposition valid? Complete? Consistent?
**If fail:** Re-decompose with feedback
**Cost:** ~$0.01 per retry

**Loop 2: AGENTS → VERIFY (results)**
```
AGENTS → VERIFY
   ↑        │
   └─(retry)┘
```
**Checks:** Did agent solve the subgoal correctly?
**If fail:** Retry agent execution with error context
**Cost:** ~$0.02-0.10 per retry

**They are independent loops - agent retry does NOT trigger re-decomposition.**

---

## Part 6: New MVP Additions

### 6.1 LLM Preference Routing (Cost Optimization)

**Problem:** User has multiple models (Haiku $0.25/M, Sonnet $3/M, Opus $15/M). Which to use?

**Solution:** AURORA auto-selects based on query complexity.

**Configuration:**

```json
{
  "llm_models": [
    {
      "name": "fast-model",
      "provider": "anthropic",
      "model": "claude-3-haiku-20240307",
      "cost_per_1m_tokens": {
        "input": 0.25,
        "output": 1.25
      },
      "use_for": "simple queries, quick answers, summaries, routine tasks"
    },
    {
      "name": "reasoning-model",
      "provider": "anthropic",
      "model": "claude-3-5-sonnet-20241022",
      "cost_per_1m_tokens": {
        "input": 3.00,
        "output": 15.00
      },
      "use_for": "complex reasoning, code generation, multi-step problems, analysis"
    },
    {
      "name": "best-model",
      "provider": "anthropic",
      "model": "claude-opus-4-20250514",
      "cost_per_1m_tokens": {
        "input": 15.00,
        "output": 75.00
      },
      "use_for": "critical tasks, maximum quality needed, novel problems"
    }
  ],
  "routing_strategy": "llm_based"
}
```

**How it works:**

```python
def select_model(user_query, available_models, complexity):
    # Use Haiku to route (cheap: $0.0001 per routing)
    prompt = f"""
    You have these models:
    - fast-model: {models[0].use_for}
    - reasoning-model: {models[1].use_for}
    - best-model: {models[2].use_for}

    Query: "{user_query}"
    Complexity: {complexity}

    Which model should handle this? Return JSON:
    {{"model": "reasoning-model", "reasoning": "brief justification"}}
    """

    decision = llm_call(prompt, model="fast-model")  # Use cheapest for routing
    return decision.model
```

**Example:**
- "What's 2+2?" → fast-model (Haiku, $0.0003)
- "Explain quantum computing" → reasoning-model (Sonnet, $0.04)
- "Design distributed system" → best-model (Opus, $0.20)

**Cost savings:** ~40% by using cheap models when possible.

---

### 6.2 Cost Budget Enforcement (Safety)

**Problem:** Runaway costs from bugs or infinite loops.

**Solution:** Hard limits with soft warnings.

**Configuration:**

```json
{
  "cost_limits": {
    "per_task_usd": 2.00,
    "daily_usd": 10.00,
    "monthly_usd": 100.00,
    "warn_at_percent": 80
  }
}
```

**Implementation:**

```python
class CostTracker:
    def check_budget(self, estimated_cost):
        if self.daily_spent + estimated_cost > self.limits.daily_usd:
            # Soft limit - warn and confirm
            print(f"⚠️  Task will exceed daily limit:")
            print(f"   Current: ${self.daily_spent:.2f}")
            print(f"   Estimated: ${estimated_cost:.2f}")
            print(f"   Limit: ${self.limits.daily_usd:.2f}")

            if not user_confirms("Continue?"):
                raise BudgetExceededError("User cancelled")

        # Warn at 80%
        if self.daily_spent + estimated_cost > self.limits.daily_usd * 0.8:
            print(f"⚠️  Approaching daily limit ({self.daily_spent / self.limits.daily_usd * 100:.0f}%)")

    def record_actual_cost(self, actual_cost):
        self.daily_spent += actual_cost
        self.monthly_spent += actual_cost
        self._persist_to_disk()
```

**CLI commands:**

```bash
# Check budget status
$ aurora budget status
Daily: $3.45 / $10.00 (34%)
Monthly: $47.20 / $100.00 (47%)

# View spending breakdown
$ aurora budget breakdown --last 7d
Task                    Cost
task-123 (reasoning)   $0.34
task-456 (writing)     $1.20
...
Total:                 $3.45
```

---

### 6.3 Timing Logs (Performance Debugging)

**Problem:** "My query took 8 seconds. Where's the slowness?"

**Solution:** Breakdown timing at each layer.

**Task file format:**

```json
{
  "task_id": "task-123",
  "query": "Design migration strategy",
  "timestamp": "2025-12-20T10:30:00Z",
  "timing": {
    "total_ms": 8234,
    "breakdown": {
      "complexity_assessment_ms": 120,
      "actr_retrieval_ms": 230,
      "decomposition_ms": 450,
      "decomposition_verification_ms": 180,
      "agent_execution_ms": 7100,
      "result_verification_ms": 154
    },
    "bottleneck": "agent_execution_ms"
  }
}
```

**CLI command:**

```bash
$ aurora task show task-123 --timing
Task: task-123
Total: 8.2s

Breakdown:
  Complexity assessment:      120ms   (1.5%)
  ACT-R retrieval:            230ms   (2.8%)
  Decomposition:              450ms   (5.5%)
  Decomposition verify:       180ms   (2.2%)
  Agent execution:           7100ms  (86.3%) ← BOTTLENECK
  Result verification:        154ms   (1.9%)
```

---

### 6.4 Guardrails (Input/Output Safety)

**Problem:** Sensitive data in prompts, invalid outputs, runaway queries.

**Solution:** System defaults + user overrides.

**Configuration:**

```json
{
  "guardrails": {
    "input": {
      "max_length": 10000,
      "block_patterns": [
        "\\b\\d{3}-\\d{2}-\\d{4}\\b",
        "\\b\\d{16}\\b",
        "password\\s*[:=]\\s*\\S+"
      ],
      "require_confirmation_for": [
        "delete|remove|drop|truncate",
        "sudo|rm -rf"
      ]
    },
    "output": {
      "max_length": 50000,
      "validate_json": true,
      "block_patterns": ["<script>", "eval\\("]
    },
    "cost": {
      "warn_above_tokens": 10000,
      "block_above_cost_usd": 2.00
    }
  }
}
```

**Built-in checks:**
1. **Length limits:** Prevent huge prompts/responses
2. **PII detection:** Block SSN, credit cards via regex
3. **Cost warnings:** Alert on expensive queries
4. **Format validation:** Verify JSON/code syntax if expected

**User experience:**

```bash
$ aurora "My SSN is 123-45-6789, help me..."
❌ Guardrail violation: Detected SSN in prompt
Tip: Remove sensitive data before submitting

$ aurora "Analyze 50-page document"
⚠️  Warning: Large query (45k tokens, ~$1.35)
Continue? (y/n):
```

---

### 6.5 Headless Mode (Autonomous Multi-Iteration)

**Problem:** Long-running tasks need multiple iterations without manual intervention.

**Solution:** Headless mode with goal validation.

**Two invocation methods:**

**Method 1: CLI args (quick tasks)**
```bash
$ aurora "fix all linting errors" \
    --headless \
    --max-iterations 5 \
    --goal "linter returns 0 errors" \
    --scratchpad scratch.md
```

**Method 2: prompt.md (complex experiments)**
```bash
$ aurora --headless --prompt headless/prompt.md
```

**Configuration hierarchy:**
1. CLI args (highest priority)
2. prompt.md (if specified)
3. config.json defaults (fallback)

**headless-prompt.md template:**

```markdown
# Headless Experiment: [Title]

## Goal
[ONE clear, measurable goal]

## Success Criteria
- ✅ [Specific metric 1]
- ✅ [Specific metric 2]

## Your Workspace
- **Branch:** headless-experiment
- **Scratchpad:** scratch.md (append notes after each iteration)
- **Files you can modify:** [list]
- **Restrictions:** Only commit to headless branch, NO merging to main

## Your Tasks
1. [Action 1]
2. [Action 2]
3. [Validation step]

## Constraints
- Max iterations: 10
- Max cost: $5.00
- Timeout: 30 minutes

## When You're Done
Write `EXPERIMENT_COMPLETE` in scratch.md with summary.

## Safety Rules
- Work on headless branch only
- NO merging to main
- Commit after each significant change
```

**How it works:**

```python
def run_headless(query, config):
    for iteration in range(1, config.max_iterations + 1):
        print(f"=== Iteration {iteration}/{config.max_iterations} ===")

        # Execute AURORA
        result = aurora.run(query)

        # Append to scratchpad
        append_to_scratchpad(iteration, query, result)

        # Check goal (use LLM to judge)
        goal_achieved = validate_goal(result, config.goal_criteria)

        if goal_achieved:
            print(f"✓ GOAL_ACHIEVED ({iteration} iterations)")
            return result

        # Adjust query with failure context
        query = adjust_from_failure(query, result, goal_achieved.reason)

    print(f"❌ Max iterations reached without achieving goal")
```

**Progress display (live updates):**

```
=== Iteration 3/10 ===
[12:34:56] Running agent: code-expert
[12:35:12] Result: Fixed 3 bugs
[12:35:15] Validation: Tests still failing (2 remaining)
[12:35:16] Adjusting context for retry...
```

**Config defaults:**

```json
{
  "headless_defaults": {
    "max_iterations": 10,
    "max_cost_usd": 5.00,
    "timeout_minutes": 30,
    "scratchpad": "./scratch.md",
    "progress_display": "live"
  }
}
```

---

## Part 7: Complete Configuration Schema

**File:** `~/.aurora/config.json`

```json
{
  "version": "3.0",

  "llm_models": [
    {
      "name": "fast-model",
      "provider": "anthropic",
      "model": "claude-3-haiku-20240307",
      "cost_per_1m_tokens": {"input": 0.25, "output": 1.25},
      "use_for": "simple queries, summaries, routing decisions"
    },
    {
      "name": "reasoning-model",
      "provider": "anthropic",
      "model": "claude-3-5-sonnet-20241022",
      "cost_per_1m_tokens": {"input": 3.00, "output": 15.00},
      "use_for": "complex reasoning, code generation, analysis"
    },
    {
      "name": "best-model",
      "provider": "anthropic",
      "model": "claude-opus-4-20250514",
      "cost_per_1m_tokens": {"input": 15.00, "output": 75.00},
      "use_for": "critical tasks, maximum quality"
    }
  ],

  "routing_strategy": "llm_based",

  "complexity_thresholds": {
    "simple": {"max_words": 20, "keywords": ["what", "who", "when"]},
    "medium": {"max_words": 100, "keywords": ["how", "compare", "explain"]},
    "complex": {"min_words": 100, "keywords": ["design", "strategy", "architecture"]},
    "critical": {"keywords": ["production", "migration", "security"]}
  },

  "verification": {
    "simple": "none",
    "medium": "option_a",
    "complex": "option_b",
    "critical": "option_c"
  },

  "scoring_thresholds": {
    "cache": 0.8,
    "pass": 0.7,
    "retry": 0.5,
    "fail": 0.5
  },

  "self_correction": {
    "enabled": true,
    "retry_by_complexity": {
      "simple": 0,
      "medium": 1,
      "complex": 2,
      "critical": 3
    },
    "max_cost_per_retry_usd": 0.50
  },

  "cost_limits": {
    "per_task_usd": 2.00,
    "daily_usd": 10.00,
    "monthly_usd": 100.00,
    "warn_at_percent": 80
  },

  "guardrails": {
    "input": {
      "max_length": 10000,
      "block_patterns": [
        "\\b\\d{3}-\\d{2}-\\d{4}\\b",
        "\\b\\d{16}\\b",
        "password\\s*[:=]\\s*\\S+"
      ],
      "require_confirmation_for": [
        "delete|remove|drop|truncate",
        "sudo|rm -rf"
      ]
    },
    "output": {
      "max_length": 50000,
      "validate_json": true,
      "block_patterns": ["<script>", "eval\\("]
    },
    "cost": {
      "warn_above_tokens": 10000,
      "block_above_cost_usd": 2.00
    }
  },

  "headless_defaults": {
    "max_iterations": 10,
    "max_cost_usd": 5.00,
    "timeout_minutes": 30,
    "scratchpad": "./scratch.md",
    "progress_display": "live"
  },

  "agents": {
    "registry_paths": [
      "~/.aurora/agents.json",
      "./.aurora/agents.json"
    ],
    "fallback_mode": "llm_only",
    "auto_discover": true,
    "refresh_interval_sec": 300
  },

  "actr_memory": {
    "decay_rate": 0.5,
    "spread_factor": 0.3,
    "activation_boost_success": 0.2,
    "activation_penalty_failure": -0.1,
    "min_activation": -5.0,
    "max_activation": 5.0
  },

  "logging": {
    "level": "INFO",
    "file": "~/.aurora/logs/aurora.log",
    "timing_logs": true,
    "task_files": true
  }
}
```

---

## Part 8: Full MVP Flow

### Simple Query (No Decomposition)

```
User: "What's the capital of France?"
  ↓
Complexity Assessment: SIMPLE
  ↓
Skip decomposition, call LLM directly
  ↓
Response: "Paris"
  ↓
Cost: ~$0.001
```

### Medium Query (Option A Verification)

```
User: "Compare Python vs JavaScript for backend"
  ↓
Complexity Assessment: MEDIUM
  ↓
DECOMPOSE (LLM):
  - SG1: Research Python backend strengths
  - SG2: Research JavaScript backend strengths
  - SG3: Compare based on criteria (performance, ecosystem, etc.)
  ↓
VERIFY Decomposition (Option A: Self-verify):
  Score: 0.85 → PASS
  ↓
EXECUTE Agents:
  - SG1 → research-agent → Python analysis
  - SG2 → research-agent → JS analysis
  - SG3 → analysis-agent → Comparison
  ↓
VERIFY Results (Option A: Self-verify):
  Score: 0.78 → PASS
  ↓
RESPOND with synthesis
  ↓
Cache pattern (score ≥ 0.8)
  ↓
Cost: ~$0.15
```

### Complex Query (Option B Verification)

```
User: "Design migration strategy from monolith to microservices"
  ↓
Complexity Assessment: COMPLEX
  ↓
DECOMPOSE (LLM):
  - SG1: Analyze current monolith
  - SG2: Identify service boundaries
  - SG3: Design migration sequence
  - SG4: Assess risks
  ↓
VERIFY Decomposition (Option B: Adversarial):
  - Adversarial LLM challenges assumptions
  - Finds missing consideration: "What about data migration?"
  - Score: 0.65 → RETRY
  ↓
RE-DECOMPOSE with feedback:
  - Add SG5: Design data migration strategy
  ↓
VERIFY again (Option B):
  Score: 0.82 → PASS
  ↓
EXECUTE Agents (parallel where possible):
  - SG1 → architecture-agent
  - SG2 → domain-expert-agent
  - SG3 → strategy-agent
  - SG4 → risk-agent
  - SG5 → data-agent
  ↓
VERIFY Results (Option B: Adversarial):
  - Checks consistency across agent outputs
  - Score: 0.81 → PASS
  ↓
RESPOND with comprehensive plan
  ↓
Cache pattern (score ≥ 0.8)
  ↓
Cost: ~$0.50
```

---

## Part 9: Success Metrics

### Primary Metrics (MVP)

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Reasoning Accuracy** | >85% on complex queries | Human eval on 100 test cases |
| **Cost Efficiency** | <40% of LLM-only baseline | $ per query comparison |
| **Response Time** | <10s for medium, <30s for complex | 95th percentile |
| **User Satisfaction** | NPS >40 | Survey after 50 queries |
| **Learning Velocity** | +5% accuracy per week | ACT-R activation improvements |

### Secondary Metrics

| Metric | Target | Purpose |
|--------|--------|---------|
| **Cache Hit Rate** | >30% after 100 queries | Validates ACT-R learning |
| **Verification Pass Rate** | 70-85% first attempt | Too high = too lenient, too low = too strict |
| **Retry Rate** | <20% of queries | High retry = poor decomposition quality |
| **Fallback Rate** | <5% of queries | High fallback = missing agent capabilities |

---

## Part 10: Implementation Priority

### Phase 1: MVP (Weeks 1-4)

**Week 1: Core Loop**
- [ ] Complexity assessment (keyword + LLM)
- [ ] Basic decomposition (JSON output)
- [ ] Agent registry + routing
- [ ] Simple LLM executor

**Week 2: Verification**
- [ ] Option A: Self-verification (decomposition + results)
- [ ] Scoring system (0-1 scale)
- [ ] Retry logic with feedback
- [ ] Structured JSON contracts

**Week 3: Learning + Cost**
- [ ] ACT-R memory (SQLite)
- [ ] Pattern caching (score ≥ 0.8)
- [ ] LLM preference routing
- [ ] Cost budget enforcement

**Week 4: Safety + UX**
- [ ] Guardrails (input/output)
- [ ] Timing logs
- [ ] CLI commands
- [ ] Task file persistence

### Phase 2: Enhancements (Weeks 5-8)

**Week 5: Advanced Verification**
- [ ] Option B: Adversarial verification
- [ ] Option C: Deep reasoning (CRITICAL queries)

**Week 6: Headless Mode**
- [ ] Headless CLI mode
- [ ] Goal validation
- [ ] prompt.md support
- [ ] Scratchpad management

**Week 7: Performance**
- [ ] Parallel agent execution
- [ ] Caching optimizations
- [ ] Cost profiling

**Week 8: Testing + Documentation**
- [ ] End-to-end test suite
- [ ] User documentation
- [ ] Example workflows
- [ ] Performance benchmarks

---

## Part 11: Key Takeaways

### What AURORA Actually Solves

1. **Reasoning failures** → Verification catches invalid logic
2. **Cost inefficiency** → Complexity routing + LLM selection
3. **No learning** → ACT-R caches verified patterns
4. **Black box execution** → Structured JSON + timing logs
5. **Runaway costs** → Budget limits + guardrails

### What Makes It Work

1. **Verification is cheap** (~$0.01) vs execution (~$0.10)
2. **Complexity-based depth** - Pay for quality when needed
3. **Structured reasoning** - JSON enables validation
4. **Self-correction built in** - Retry with feedback, not blind retry
5. **Learning from success** - Only cache verified patterns

### Critical Design Decisions

| Decision | Rationale |
|----------|-----------|
| **JSON contracts** | Parseable, traceable, auditable |
| **Hybrid verification** | A/B/C based on complexity |
| **Cost budgets** | Safety for personal users |
| **LLM routing** | 40% cost savings on model selection |
| **Complexity-based retries** | More retries for critical tasks |
| **Headless mode** | Autonomous multi-iteration tasks |

---

## Appendix A: Sample Headless Prompt Template

**File:** `headless/headless-prompt.md`

```markdown
# Headless Experiment: Fix All Linting Errors

## Goal
Fix all linting errors in the codebase until linter returns 0 errors.

## Success Criteria
- ✅ Linter returns 0 errors
- ✅ All tests still passing
- ✅ No new warnings introduced

## Your Workspace
- **Branch:** headless-lint-fix
- **Scratchpad:** scratch.md (append notes after each iteration)
- **Files you can modify:** src/**/*.py
- **Files you CANNOT modify:** tests/, config/
- **Restrictions:** Only commit to headless-lint-fix branch, NO merging to main

## Your Tasks
1. Run linter: `pylint src/`
2. Identify error types and counts
3. Fix errors by priority (syntax > style > documentation)
4. Run tests: `pytest tests/`
5. Re-run linter to verify 0 errors
6. If errors remain, repeat from step 3

## Constraints
- Max iterations: 5
- Max cost: $2.00
- Timeout: 15 minutes

## Before Each Iteration
1. Read scratch.md to see what you tried before
2. Check what files you've already modified
3. Plan next fix based on remaining errors

## After Each Iteration
Append to scratch.md:
```
## Iteration [N]
- Errors found: [count and types]
- Files modified: [list]
- Tests passing: [yes/no]
- Remaining errors: [count]
- Next step: [plan]
```

## When You're Done
Write `EXPERIMENT_COMPLETE` in scratch.md with:
- Total errors fixed
- Total iterations used
- Files modified
- Verification: linter output showing 0 errors

## Safety Rules
- Work on headless-lint-fix branch only
- NO merging to main
- Commit after each fix with descriptive message
- Run tests after every change
```

---

## Appendix B: CLI Command Reference

```bash
# Basic usage
aurora "your query here"
aurora "complex task" --verbose

# Model selection (override auto-routing)
aurora "query" --model fast-model
aurora "query" --model reasoning-model
aurora "query" --model best-model

# Budget management
aurora budget status
aurora budget breakdown --last 7d
aurora budget set-daily 20.00

# Task history
aurora task list
aurora task show task-123
aurora task show task-123 --timing

# Headless mode
aurora "task" --headless --max-iterations 10 --goal "criteria"
aurora --headless --prompt headless/prompt.md

# Agent management
aurora agent list
aurora agent show code-expert
aurora agent refresh

# Guardrails
aurora "query" --ignore-guardrails  # Override for specific query
```

---

## Appendix C: Migration from Original PRD

### What Changed

| Original | Unified MVP v3.0 | Why |
|----------|------------------|-----|
| Assessment only | Assessment + Verification | Catch bad decompositions |
| Single retry | Complexity-based retries | More attempts for critical tasks |
| No cost limits | Hard budget limits | Safety for personal users |
| Single LLM | LLM preference routing | 40% cost savings |
| No timing | Detailed timing logs | Debug performance issues |
| No guardrails | Input/output validation | Block sensitive data, invalid outputs |
| Synchronous only | + Headless mode | Multi-iteration autonomous tasks |

### What Stayed the Same

- SOAR-based decomposition
- ACT-R learning and memory
- Agent registry and routing
- Structured JSON contracts
- Multi-turn conversation support
- CLI-first interface

---

## Ready for Implementation

**This specification is COMPLETE and ready for:**
1. Task breakdown (use `2-generate-tasks` agent)
2. Sprint planning
3. Development team handoff
4. Iterative implementation (Phase 1 → Phase 2)

**All design questions resolved. All components specified. All JSON schemas defined.**

---

**Document Status:** ✅ FINALIZED
**Next Action:** Generate implementation tasks from this spec
**Command:** `aurora-orchestrator --agent 2-generate-tasks --input AURORA-MVP-UNIFIED-SPEC.md`
