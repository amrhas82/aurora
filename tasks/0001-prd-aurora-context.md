# AURORA-Context Framework
## Complete Technical Specification

**Version**: 3.0
**Date**: December 20, 2025
**Status**: Ready for Implementation
**Product Name**: AURORA-Context (Architecture-Agnostic Unified Reasoning Orchestration + Context Retrieval)

---

## DOCUMENT PURPOSE

This is the **SINGLE SOURCE OF TRUTH** for AURORA-Context implementation. It consolidates:
- Original PRD requirements
- MVP corrections from architectural review
- All clarifications and missing specifications
- Complete LLM prompt specifications
- Implementation architecture decisions

This document is comprehensive and implementation-ready. A cleaner, marketing-focused PRD will be derived from this spec.

---

## CHANGELOG

### Version 3.0 (December 20, 2025)

**Major Feature Additions (7 new features):**

1. **Guardrails (Phase 0)** - Section 3.1
   - Input validation layer before complexity assessment
   - PII detection (redact/reject)
   - Length limits (max 10,000 characters)
   - Format validation (UTF-8, control characters)
   - Budget pre-check integration

2. **LLM Preference Routing** - Section 3.3
   - Model selection based on complexity (Haiku/Sonnet/Opus)
   - One decision per query (before SOAR orchestration)
   - 97% cost savings vs always-Opus
   - Clean separation: routing chooses model, SOAR chooses agents

3. **Timing Logs with Percentages** - Section 9.4.1
   - Per-phase execution time tracking
   - Percentage of total query time
   - Bottleneck identification (e.g., "Agents took 97.8%")

4. **Cost Budget Tracking & Enforcement** - Section 9.4.2
   - Soft/hard spending limits
   - Pre-query cost estimation
   - Budget tracker file (~/.aurora/budget_tracker.json)
   - CLI commands for budget management

5. **Self-Correction Clarification** - Appendix D
   - Explicit documentation of TWO INDEPENDENT RETRY LOOPS
   - Loop 1: Decomposition self-correction
   - Loop 2: Agent execution self-correction
   - Separate retry counters, feedback mechanisms, failure modes

6. **Headless Mode** - Section 9.8
   - Autonomous experiments with human out of the loop
   - Goal-based termination criteria
   - Git branch isolation (headless branch only)
   - Scratchpad for iteration memory
   - CLI: `aurora --headless --prompt=prompt.md --scratchpad=scratchpad.md`

7. **Memory Integration Modes** - Section 9.9
   - Mode 1: Smart auto-escalation (simple → direct LLM, complex → full AURORA)
   - Mode 2: Intentional memory recall (`aur mem "search query"`)
   - In-process memory loading (no daemon for MVP)
   - Lazy update strategy (updates only during AURORA runs)

**Version Bump Rationale:**
- Major version (2.4 → 3.0) due to significant new capabilities
- 7 production-ready features added
- Focus: Personal users, cost optimization, safety, autonomous operation

---

## TABLE OF CONTENTS

1. [Executive Summary](#executive-summary)
2. [Problem Analysis](#problem-analysis)
3. [Solution Architecture](#solution-architecture)
4. [Core Components](#core-components)
5. [Verification System](#verification-system)
6. [ACT-R Memory System](#act-r-memory-system)
7. [SOAR Orchestrator](#soar-orchestrator)
8. [LLM Prompt Specifications](#llm-prompt-specifications)
9. [Implementation Details](#implementation-details)
10. [Success Metrics](#success-metrics)
11. [Appendices](#appendices)

---

## 1. EXECUTIVE SUMMARY

### What is AURORA-Context?

AURORA-Context is a **unified framework** that combines intelligent reasoning orchestration with context retrieval to improve AI agent reasoning quality. It merges two previously separate systems:

- **AURORA** (Architecture for Unified Reasoning with Orchestrated Routing and Agents): Reasoning orchestration and verification
- **ContextMind**: ACT-R-based code context retrieval

### The Critical Insight

**AURORA as originally designed is an orchestration and caching framework, not a reasoning solution.** To actually solve the reasoning problem, a **verification layer** must be added.

### The Core Problem

```
DECOMPOSE ──▶ VERIFY ──▶ AGENTS ──▶ VERIFY ──▶ RESPOND
    │           │          │          │
   LLM        LLM        WORK       LLM
(structure)  (check)    (solve)   (check)
```

Without verification, decomposition just distributes unreliable reasoning. With verification, we can:
- Catch invalid decompositions before wasting agent compute
- Detect when agent outputs don't address subgoals
- Identify contradictions between results
- Provide **earned** confidence scores (not heuristic guesses)
- Enable learning from **verified** successes

---

## 2. PROBLEM ANALYSIS

### Why LLMs Fail at Reasoning

| Failure Mode | Description |
|--------------|-------------|
| **Attention degradation** | Each step introduces compounding error as model loses focus |
| **No working memory** | LLMs don't maintain persistent state between inference calls |
| **Probability collapse** | Token prediction becomes unreliable when problems diverge from training distribution |
| **No verification** | LLMs cannot distinguish plausible-sounding from logically valid |
| **Context overload** | Including too much irrelevant code/context wastes tokens and degrades accuracy |
| **No learning** | Systems make the same mistakes repeatedly; no accumulation of experience |

### What Original MVP Actually Does (Without Verification)

| Component | What It Does | Solves Reasoning? |
|-----------|--------------|-------------------|
| Hybrid Assessment | Classify query complexity | No - routing optimization |
| SOAR Decomposition | Break problem into subgoals | No - just structured prompting |
| Agent Routing | Send subgoals to specialists | No - distribution, not reasoning |
| ACT-R Memory | Cache successful patterns | No - helps repeated problems, not novel reasoning |

**Conclusion:** Original MVP optimizes **cost** and **routing**, not **reasoning quality**.

### The Critical Gap: No Verification Layer

The original MVP has no mechanism to verify:

1. **Decomposition validity** - Is the breakdown complete? Consistent? Does it cover the problem?
2. **Agent output correctness** - Did agents actually solve their subgoals correctly?
3. **Synthesis integrity** - Does the final answer follow from the evidence?
4. **Logical consistency** - Do intermediate conclusions contradict each other?

> **Decomposition doesn't solve the reasoning problem - it just distributes it.**

---

## 3. SOLUTION ARCHITECTURE

### 3.1 Input Processing & Guardrails (Phase 0)

**Purpose:** Validate and protect input BEFORE any LLM processing to ensure safety, cost control, and system stability.

**Phase 0 executes before complexity assessment:**

```
USER QUERY
    ↓
PHASE 0: GUARDRAILS
    ├─ PII Detection → redact/reject
    ├─ Length Check → reject if > limit
    ├─ Format Validation → reject if malformed
    └─ Budget Pre-Check → warn/block
    ↓
[If passed] → PHASE 1: COMPLEXITY ASSESSMENT
[If blocked] → Return error with reason
```

**Guardrail Components:**

**1. PII Detection**
- Scan for personally identifiable information
- Patterns: emails, SSNs, credit cards, phone numbers, API keys
- Action: `redact` (replace with [REDACTED]) or `reject` (block query)
- Log: What was redacted for audit trail
- Why: Prevent accidental data leaks to LLM providers

**2. Length Limits**
- Max query length: 10,000 characters (configurable)
- Action: Reject with helpful error message
- Reason: Prevent token explosion, DoS attacks, cost blowout
- Cost protection: Very long queries = very expensive AURORA runs

**3. Format Validation**
- UTF-8 encoding check (reject invalid characters)
- Malformed input rejection (control characters, null bytes)
- Action: Return error with specific formatting issue
- Reason: Prevent crashes from malformed input

**4. Cost Budget Pre-Check**
- Check remaining budget before processing
- Estimate query cost based on: `base_cost × complexity_hint × (length / 1000)`
- Compare: `current_usage + estimated_cost > limit?`
- Actions:
  - Soft limit (80%): Warn user, allow query
  - Hard limit (100%): Block query, show budget status
- Integration: See Section 9.4 for budget tracking details

**Guardrail Flow Example:**

```
Query: "What's the authentication bug? My email is john@example.com"
    ↓
1. PII Detection: Found email → Redact
   Modified query: "What's the authentication bug? My email is [REDACTED]"
    ↓
2. Length Check: 65 chars < 10,000 → PASS
    ↓
3. Format Validation: Valid UTF-8 → PASS
    ↓
4. Budget Check:
   - Current: $18.50 / $20.00 (92%)
   - Estimated: $0.50
   - Total would be: $19.00 (95%)
   → ACTION: WARN "Near budget limit (95%), proceed? [y/N]"
    ↓
[User confirms] → Proceed to COMPLEXITY ASSESSMENT
```

**Configuration:** See Appendix C for complete `guardrails` config schema.

---

### 3.2 The Corrected Flow

```
+-----------------------------------------------------------------------+
|                         CORRECTED MVP FLOW                              |
+-----------------------------------------------------------------------+
|                                                                         |
|  +----------+                                                          |
|  | USER     |                                                          |
|  | QUERY    |                                                          |
|  +----+-----+                                                          |
|       |                                                                 |
|       v                                                                 |
|  +------------------------------------------------------------+       |
|  | 1. COMPLEXITY ASSESSMENT                                    |       |
|  |    Output: SIMPLE | MEDIUM | COMPLEX | CRITICAL            |       |
|  +----+---------------------------------------------------+---+       |
|       |                                                   |            |
|       v                                                   v            |
|  +---------+                                   +-------------------+   |
|  | SIMPLE  |                                   | MEDIUM / COMPLEX  |   |
|  | Direct  |                                   |                   |   |
|  | LLM     |                                   | 2. DECOMPOSE JSON |   |
|  +---------+                                   |        v          |   |
|       |                                        | 3. VERIFY (A/B/C) |   |
|       |                                        | Score >= 0.7?     |   |
|       |                                        |        v          |   |
|       |                                        | 4. ROUTE TO AGENTS|   |
|       |                                        |        v          |   |
|       |                                        | 5. VERIFY OUTPUTS |   |
|       |                                        |        v          |   |
|       |                                        | 6. SYNTHESIZE     |   |
|       |                                        |        v          |   |
|       |                                        | 7. FINAL VERIFY   |   |
|       |                                        +--------+----------+   |
|       |                                                 |              |
|       +-------------------------------------------------+              |
|                                                         |              |
|                                                         v              |
|  +------------------------------------------------------------+       |
|  | 8. ACT-R MEMORY                                             |       |
|  |    If overall_score >= 0.8: cache pattern                   |       |
|  +------------------------------------------------------------+       |
|       |                                                                 |
|       v                                                                 |
|  +------------------------------------------------------------+       |
|  | RESPONSE                                                    |       |
|  | - answer                                                    |       |
|  | - overall_score                                             |       |
|  | - confidence (derived from score)                           |       |
|  | - reasoning_trace (JSON)                                    |       |
|  +------------------------------------------------------------+       |
|                                                                         |
+-----------------------------------------------------------------------+
```

### Complexity Routing

| Complexity | Flow | Verification | Cost |
|------------|------|--------------|------|
| **SIMPLE** | Query → LLM → Response | **None** - direct pass-through | 1x |
| **MEDIUM** | Query → Decompose → Verify (A) → Agents → Verify → Synthesize | Self-verify | 3-4x |
| **COMPLEX** | Query → Decompose → Verify (B) → Agents → Verify → Synthesize | Adversarial | 5-6x |
| **CRITICAL** | Query → Multi-path → Debate → Verify (C) → Execute → Deep Verify | Full debate (Phase 2) | 5-10x |

**Escalation Rule**: If Option B fails 2x, escalate to Option C (becomes CRITICAL)

### High-Level Architecture

```
+---------------------------------------------------------------------+
|                     AURORA-CONTEXT FRAMEWORK                          |
|            "Architecture-Agnostic Reasoning + Retrieval"              |
+---------------------------------------------------------------------+
|                                                                       |
|  +---------------------------------------------------------------+   |
|  |                    UNIFIED ACT-R MEMORY                        |   |
|  |                                                                |   |
|  |  +-----------------+  +-----------------+  +----------------+  |   |
|  |  | Reasoning       |  | Code            |  | Domain         |  |   |
|  |  | Patterns        |  | Chunks          |  | Knowledge      |  |   |
|  |  | (decompositions,|  | (functions,     |  | (APIs, schemas,|  |   |
|  |  | routing maps)   |  | dependencies)   |  | conventions)   |  |   |
|  |  | ID: reas:*      |  | ID: code:*      |  | ID: know:*     |  |   |
|  |  +-----------------+  +-----------------+  +----------------+  |   |
|  |           |                    |                   |           |   |
|  |           +--------------------+-------------------+           |   |
|  |                                |                               |   |
|  |                    +-----------v-----------+                   |   |
|  |                    |  ACTIVATION ENGINE    |                   |   |
|  |                    |  - Base-level         |                   |   |
|  |                    |  - Spreading          |                   |   |
|  |                    |  - Context boost      |                   |   |
|  |                    |  - Decay              |                   |   |
|  |                    +-----------------------+                   |   |
|  +---------------------------------------------------------------+   |
|                                                                       |
|  +---------------------------------------------------------------+   |
|  |                    REASONING LAYER                             |   |
|  |  Query -> Decompose (JSON) -> Verify -> Route -> Verify        |   |
|  +---------------------------------------------------------------+   |
|                                                                       |
|  +---------------------------------------------------------------+   |
|  |                 CONTEXT PROVIDERS (Pluggable)                  |   |
|  |  - CodeContextProvider (cAST + Git)                            |   |
|  |  - ReasoningContextProvider (pattern templates)                |   |
|  |  - KnowledgeContextProvider (Phase 2)                          |   |
|  +---------------------------------------------------------------+   |
|                                                                       |
+---------------------------------------------------------------------+
```

---

### 3.3 LLM Preference Routing

**Purpose:** Select the optimal model ONCE per query based on complexity, then use that model for the entire SOAR chain.

**Decision Point:** After complexity assessment (Phase 1), BEFORE SOAR orchestration

**Routing Strategy:**

```
PHASE 1: COMPLEXITY ASSESSMENT
    ↓
Complexity Result: SIMPLE | MEDIUM | COMPLEX | CRITICAL
    ↓
PHASE 1.5: LLM PREFERENCE ROUTING (NEW)
    ↓
Map Complexity → Model Tier:
    - SIMPLE → fast tier (Haiku, ~$0.001/query)
    - MEDIUM → reasoning tier (Sonnet, ~$0.05/query)
    - COMPLEX/CRITICAL → best tier (Opus, ~$0.50/query)
    ↓
Pass selected model to SOAR Orchestrator
    ↓
SOAR uses THAT model for entire chain:
    - Decomposition prompt
    - Verification prompts
    - Synthesis prompt
    - (Agent execution uses solving_llm separately)
```

**Separation of Concerns:**
- **Preference Routing:** Chooses MODEL (one decision per query)
- **SOAR Orchestrator:** Chooses AGENTS, STEPS, ORDER (doesn't know about models)

**Why One Decision Per Query (Not Per-Prompt):**
- Clean separation: routing decides model, SOAR decides agents/steps
- One decision point (predictable)
- Simple to implement
- Easy to debug
- Predictable costs

**Model Tier Configuration:**

```json
{
  "llm": {
    "preference_routing": {
      "enabled": true,
      "tiers": {
        "fast": {
          "model": "claude-3-haiku-20240307",
          "use_for": ["simple"]
        },
        "reasoning": {
          "model": "claude-3-5-sonnet-20241022",
          "use_for": ["medium"]
        },
        "best": {
          "model": "claude-opus-4-5-20251101",
          "use_for": ["complex", "critical"]
        }
      },
      "apply_to": "reasoning_llm"
    }
  }
}
```

**Cost Impact:**

| Complexity | Old (always Opus) | New (tiered routing) | Savings |
|------------|-------------------|----------------------|---------|
| SIMPLE (90%) | $0.50 × 0.9 = $0.45 | $0.001 × 0.9 = $0.0009 | 99.8% |
| MEDIUM (8%) | $0.50 × 0.08 = $0.04 | $0.05 × 0.08 = $0.004 | 90% |
| COMPLEX (2%) | $0.50 × 0.02 = $0.01 | $0.50 × 0.02 = $0.01 | 0% |
| **Total** | **$0.50/query** | **$0.015/query** | **97% savings** |

**Note:** Savings assume 90% simple queries. Actual distribution varies by user.

**Integration:** This routing decision happens BEFORE the existing flow diagram (Section 3.2). The selected model is passed to all subsequent SOAR prompts.

---

## 4. CORE COMPONENTS

### 4.1 Complexity Assessment

**Hybrid Assessment Strategy:**

```
┌─────────────────────────────────────────────────────────────┐
│                    COMPLEXITY ROUTER                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  SIMPLE ───▶ Direct LLM (no decomposition)                 │
│              Example: "What is X?", "List Y"                │
│              ~1x LLM cost                                   │
│                                                             │
│  MEDIUM ───▶ Decompose + self-verify (Option A)            │
│              Example: "Compare A and B"                     │
│              ~3-4x LLM cost                                 │
│                                                             │
│  COMPLEX ──▶ Decompose + adversarial verify (Option B)     │
│              Example: "Design system for X"                 │
│              ~5-6x LLM cost                                 │
│                                                             │
│  CRITICAL ─▶ Multi-path + debate (Option C) - Phase 2      │
│              Example: Mission-critical decisions            │
│              ~5-10x LLM cost                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Assessment Methods:**
1. **Fast keyword scoring** (~50ms, free) - basic heuristics
2. **LLM verification for borderline cases** (~200ms) - confidence check
3. **Full LLM analysis** (~2-3s) - only when necessary

### 4.2 Structured Decomposition (JSON)

**Why JSON?**
- **Parseable** - Can programmatically check structure
- **Traceable** - Every inference has explicit sources
- **Verifiable** - Schemas enforce completeness
- **Cacheable** - Structured patterns are reusable

**Decomposition Schema:**
```json
{
  "decomposition": {
    "id": "uuid",
    "original_query": "user's question",
    "complexity": "simple | medium | complex | critical",
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
      }
    ],
    "execution_order": ["SG1", "SG2", "SG3"],
    "parallelizable": [["SG1", "SG2"]]
  }
}
```

---

## 5. VERIFICATION SYSTEM

### 5.1 Three Verification Options

#### Option A: Self-Verification (MEDIUM complexity)

- Same LLM reviews its own reasoning
- Catches obvious gaps, missing structure, incomplete coverage
- Fast, low cost (~1.5x baseline)
- **Limitation**: same blind spots

**Use when:**
- Medium complexity queries
- 2-3 step problems
- Low ambiguity

#### Option B: Adversarial Verification (COMPLEX complexity)

- Second LLM (or different prompt) acts as skeptical critic
- Finds hidden assumptions, alternative conclusions, logical leaps
- More thorough, higher cost (~2-3x baseline)
- Better for complex/critical tasks

**Use when:**
- Complex queries (4+ steps)
- High ambiguity
- Critical decisions

**Adversarial Process:**
1. Generator creates decomposition
2. Critic identifies weaknesses
3. Generator addresses critique
4. Re-verification
5. If fails 2x, escalate to Option C

#### Option C: Deep Reasoning (CRITICAL complexity) - Phase 2

- Generate 3 alternative decomposition paths
- Debate round: advocates argue for each path
- Judge synthesizes best path or hybrid
- Verify after EACH subgoal execution
- Cost: ~5-10x baseline

**Triggered when:**
- Option B fails 2+ cycles, OR
- Task flagged CRITICAL, OR
- Complexity score > 0.95

### 5.2 Verification Criteria

**Decomposition Verification:**
- **Completeness**: Do subgoals fully cover the original goal?
- **Consistency**: Do any subgoals contradict each other?
- **Groundedness**: Does each subgoal trace to given facts?
- **Routability**: Does an appropriate agent exist for each subgoal?

**Agent Output Verification:**
- **Relevance**: Does output address the assigned subgoal?
- **Consistency**: Is output internally consistent?
- **Groundedness**: Are claims supported by evidence?

**Final Synthesis Verification:**
- **Addresses query**: Does answer respond to original question?
- **Traceable**: Can every claim link to agent outputs?
- **Consistent**: Are there contradictions in final answer?
- **Calibrated**: Is confidence level appropriate given evidence?

### 5.3 Scoring and Thresholds

```
Score >= 0.8:  CACHE (learn from this success)
Score >= 0.7:  PASS (proceed to next stage)
Score 0.5-0.7: RETRY (with feedback, max 2 retries)
Score < 0.5:   FAIL (reject, try alternative or mark failed)
```

**Escalation:**
- MEDIUM with 2 retry failures → escalate to COMPLEX (Option B)
- COMPLEX with 2 retry failures → escalate to CRITICAL (Option C)

### 5.4 Verification Output Format

```json
{
  "verification": {
    "decomposition_id": "uuid",
    "checks": {
      "completeness": {"pass": true, "score": 0.9, "detail": "...", "issues": []},
      "consistency": {"pass": true, "score": 1.0, "detail": "...", "issues": []},
      "routability": {"pass": true, "score": 0.85, "detail": "...", "issues": []},
      "groundedness": {"pass": true, "score": 0.8, "detail": "...", "issues": []}
    },
    "overall_score": 0.85,
    "verdict": "pass | retry | fail",
    "critical_issues": [],
    "suggestions": []
  }
}
```

---

## 6. ACT-R MEMORY SYSTEM

### 6.1 What Is ACT-R?

ACT-R (Adaptive Control of Thought—Rational) is a **cognitive architecture** from psychology/cognitive science. It models how human memory actually works - not just storage, but **how we retrieve what's relevant**.

### 6.2 The Problem ACT-R Solves

Regular memory systems (like vector databases) answer:
> "What's semantically similar to this query?"

ACT-R answers:
> "What's most **useful to recall right now** given context, recency, and past usefulness?"

### 6.3 Activation Formula

```
Activation = Base-Level + Spreading + Context-Boost - Decay
```

**Base-Level Activation (BLA):**
- How often has this been used? (frequency)
- How recently? (recency)
- Formula: `B = ln(Σ t_j^(-d))` where t_j is time since each access, d is decay rate

**Spreading Activation:**
- Current context **primes** related memories
- Memories connected to current context get activation boost
- Formula: 0.7x per hop, max 3 hops
- Example: If "migration" is active, "schema" and "rollback" get boosted

**Context Boost:**
- Overlap with current query keywords
- Range: 0-0.5

**Decay:**
- `-0.5 * log10(days_since_access)`
- Recent use = low decay, old use = high decay

#### 6.3.5 JSON Schema Specifications

**Complete JSON schemas for all chunk types stored in ACT-R memory:**

**CodeChunk Schema** (with Governance & Semantic Tagging):
```json
{
  "id": "code:auth.py:login",
  "type": "code",
  "content": {
    "file": "src/auth.py",
    "function": "login",
    "line_start": 45,
    "line_end": 78,
    "signature": "def login(username: str, password: str) -> AuthToken",
    "dependencies": ["code:auth.py:validate_password", "code:db.py:get_user"],
    "imports": ["hashlib", "jwt"],
    "calls": ["validate_password", "get_user", "generate_token"],
    "ast_summary": {
      "complexity": "medium",
      "branches": 3,
      "loops": 0
    }
  },
  "metadata": {
    "language": "python",
    "last_modified": "2025-12-12T10:30:00Z",
    "git_hash": "abc123def",
    "semantic_role": "authentication-handler",
    "keywords": ["login", "auth", "token", "password", "validation"],
    "domain": "security"
  },
  "governance": {
    "compliance_tags": ["security-reviewed", "tested", "production-ready"],
    "lifespan_policy": "conditional",
    "retention_rules": [
      {"if": "access_count > 0", "then": "retain_while_active"},
      {"if": "contains_tag('security')", "then": "retain_for_365_days"},
      {"if": "inactive_for_90_days", "then": "decay_to_inactive"}
    ]
  },
  "conversation_log_reference": {
    "date": "2025-12-13",
    "file": "oauth-authentication-2025-12-13.md",
    "section": "Phase 6: COLLECT",
    "line_range": [45, 78]
  }
}
```

**ReasoningChunk Schema** (with tool tracking, Governance & Semantic Tagging):
```json
{
  "id": "reas:auth-flow-123",
  "type": "reasoning",
  "content": {
    "pattern": "authentication-setup",
    "original_query": "Build OAuth2 authentication",
    "complexity": "complex",
    "subgoals": [
      {"id": "SG1", "description": "Research OAuth2 providers", "agent": "researcher"},
      {"id": "SG2", "description": "Implement token validation", "agent": "coder"},
      {"id": "SG3", "description": "Test auth flow", "agent": "tester"}
    ],
    "tools_used": [
      {"subgoal": "SG1", "agent": "researcher", "tools": ["websearch", "mcp:reddit"]},
      {"subgoal": "SG2", "agent": "coder", "tools": ["grep", "read", "edit", "write"]},
      {"subgoal": "SG3", "agent": "tester", "tools": ["bash", "pytest"]}
    ],
    "tool_sequence": ["websearch", "mcp:reddit", "grep", "read", "edit", "write", "bash", "pytest"],
    "success_score": 0.92,
    "verification_option": "option_b"
  },
  "metadata": {
    "timestamp": "2025-12-12T14:20:00Z",
    "execution_time_ms": 15420,
    "total_cost_usd": 0.0234,
    "semantic_role": "oauth-decomposition-pattern",
    "keywords": ["oauth2", "authentication", "token", "provider", "verification"],
    "domain": "security"
  },
  "governance": {
    "compliance_tags": ["high-confidence-pattern", "security-critical", "tested"],
    "lifespan_policy": "conditional",
    "retention_rules": [
      {"if": "is_pattern == true", "then": "retain_indefinitely"},
      {"if": "success_score >= 0.8", "then": "retain_for_365_days"},
      {"if": "access_count > 10", "then": "escalation_candidate"}
    ]
  },
  "conversation_log_reference": {
    "date": "2025-12-12",
    "file": "oauth-implementation-2025-12-12.md",
    "section": "Phase 3: DECOMPOSE",
    "line_range": [56, 124]
  }
}
```

**KnowledgeChunk Schema** (Phase 2, with Governance & Semantic Tagging):
```json
{
  "id": "know:oauth2-providers",
  "type": "knowledge",
  "content": {
    "topic": "OAuth2 provider comparison",
    "summary": "Auth0 vs Okta vs custom implementation tradeoffs",
    "facts": [
      {"id": "F1", "statement": "Auth0 supports social providers out-of-box"},
      {"id": "F2", "statement": "Custom implementation gives full control but requires security audit"}
    ],
    "sources": ["https://auth0.com/docs", "https://developer.okta.com"],
    "confidence": 0.85
  },
  "metadata": {
    "acquired": "2025-12-12T15:00:00Z",
    "validated": true,
    "semantic_role": "oauth-provider-knowledge",
    "keywords": ["oauth2", "auth0", "okta", "provider", "comparison", "tradeoff"],
    "domain": "security"
  },
  "governance": {
    "compliance_tags": ["validated", "external-source", "security-relevant"],
    "lifespan_policy": "conditional",
    "retention_rules": [
      {"if": "confidence >= 0.8", "then": "retain_for_180_days"},
      {"if": "contains_tag('security')", "then": "retain_for_365_days"},
      {"if": "access_count > 5", "then": "escalation_candidate"}
    ]
  },
  "conversation_log_reference": {
    "date": "2025-12-12",
    "file": "oauth-research-2025-12-12.md",
    "section": "Phase 1: ASSESS and Phase 2: RETRIEVE",
    "line_range": [23, 67]
  }
}
```

**Benefits of Explicit JSON Schemas**:
- **Retrievability**: Can query by specific fields (e.g., find all chunks using "websearch")
- **Tool Learning**: Discover which tool combinations work well together
- **Pattern Matching**: Find similar reasoning patterns by tool usage
- **Agent Routing**: Suggest agents based on historical tool proficiency
- **Governance**: Track compliance tags, retention policies, and semantic roles per chunk
- **Traceability**: Cross-link to original conversation logs for context retrieval and audit
- **Semantic Search**: Query by domain, semantic_role, or keywords for better discovery

#### 6.3.6 Governance Metadata Specification

All chunks include three governance dimensions:

**1. Semantic Metadata** (`metadata` section):
- `semantic_role`: Classification of chunk's purpose (e.g., "oauth-decomposition-pattern", "authentication-handler")
- `keywords`: Array of terms for semantic search and clustering
- `domain`: Domain category (security, performance, architecture, etc.)

**2. Governance Attributes** (`governance` section):
- `compliance_tags`: Array of compliance/quality indicators (e.g., "security-reviewed", "tested", "production-ready")
- `lifespan_policy`: Type of retention rule ("conditional", "time-based", "indefinite")
- `retention_rules`: Array of conditional rules determining when/how chunk is retained or decayed

**3. Cross-Linking** (`conversation_log_reference` section):
- Points to original conversation log file and specific section/lines
- Enables quick context retrieval without reloading entire logs
- Supports audit trail and "why was this stored?" queries

**Retention Rule Examples**:
```
"retention_rules": [
  {"if": "is_pattern == true", "then": "retain_indefinitely"},
  {"if": "success_score >= 0.8", "then": "retain_for_365_days"},
  {"if": "access_count > 10", "then": "escalation_candidate"},
  {"if": "contains_tag('security')", "then": "retain_for_365_days"},
  {"if": "inactive_for_90_days", "then": "decay_to_inactive"}
]
```

**Why This Matters**:
- Enables fine-grained compliance tracking without external systems
- Supports multi-tier retention policies (different rules for different chunk types)
- Escalation flag identifies candidates for pattern-to-parametric conversion
- Cross-links reduce log retrieval overhead while maintaining full audit trail

#### 6.3.7 Semantic Tagging Mechanism

Semantic tags are **automatically generated** during Phase 7 (SYNTHESIZE):

1. **During Phase 7 Synthesis**: LLM extracts semantic role and keywords from chunk content
2. **Storage**: Tags stored in `metadata.semantic_role` and `metadata.keywords` fields
3. **Phase 2 Retrieval**: Semantic tags enable clustering (related chunks activate together via spreading activation)
4. **Future Indexing**: Tags used for semantic search and log index (Phase 2 enhancement)

**Automatic Extraction Rules**:
- `semantic_role`: Inferred from chunk pattern name + content summary
  - Example: "oauth-impl-20251213" + content → "oauth-decomposition-pattern"
- `keywords`: Top 5-7 NLP keywords from chunk content (excluding stopwords)
  - Example: oauth, authentication, token, provider, verification
- `domain`: Classified from keywords and chunk type
  - Example: "security", "performance", "architecture"

**Benefits of Automatic Tagging**:
- No manual effort required (zero adoption friction)
- Consistent tagging across all chunk types
- Enables semantic clustering in Phase 2 retrieval
- Supports future Phase 2 knowledge base indexing

### 6.4 Implementation Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ACT-R IMPLEMENTATION SPLIT                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  USE pyactr Library:              BUILD Ourselves:                  │
│  ┌──────────────────────┐         ┌──────────────────────────────┐  │
│  │ ✓ base_level_learning│         │ ✓ SQLite integration         │  │
│  │   formula (BLA calc) │         │ ✓ Retrieval logic            │  │
│  │ ✓ Activation equation│         │ ✓ Spreading activation       │  │
│  │   A = B + S + N      │         │   (dependency traversal)     │  │
│  │ ✓ Decay functions    │         │ ✓ Context boost calculation  │  │
│  │ ✓ Threshold formulas │         │ ✓ Chunk type handling        │  │
│  └──────────────────────┘         │ ✓ JSON schema for chunks     │  │
│                                    └──────────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.5 Storage: SQLite + JSON

**Architecture:**
```
┌─────────────────────────────────────────────────────────────────────┐
│                SQLite + JSON STORAGE (Hybrid Approach)               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  SQLite Database: ~/.aurora/memory.db                               │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Table: chunks                                                 │   │
│  │ ┌─────┬──────┬──────────────────────────────────────────────┐│   │
│  │ │ id  │ type │ content (JSON column)                        ││   │
│  │ ├─────┼──────┼──────────────────────────────────────────────┤│   │
│  │ │code:│ code │ {"file": "auth.py", "func": "login", ...}   ││   │
│  │ │auth │      │                                              ││   │
│  │ ├─────┼──────┼──────────────────────────────────────────────┤│   │
│  │ │reas:│ reas │ {"pattern": "auth-flow", "subgoals": [...]} ││   │
│  │ │auth │      │                                              ││   │
│  │ └─────┴──────┴──────────────────────────────────────────────┘│   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  Table: activations (indexed for fast retrieval)                    │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ chunk_id │ base_level │ last_access │ access_count          │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  Table: relationships (for spreading activation)                    │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ from_chunk │ to_chunk │ relationship_type │ weight          │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Why SQLite + JSON (in columns)?**
- **Efficient**: Indexed queries without reading full memory (no context waste)
- **Flexible**: JSON columns allow schema evolution per chunk type
- **Lightweight**: SQLite is open-source, public domain, no external dependencies
- **Fast**: No file I/O overhead; single database file
- **Type-safe**: Chunk metadata in JSON while maintaining relational integrity

### 6.6 Chunk Types with Memory Identifiers

| Chunk Type | Prefix | Description |
|------------|--------|-------------|
| **CodeChunk** | `code:` | Function/class with metadata (file, line range, dependencies) |
| **ReasoningChunk** | `reas:` | Decomposition pattern with metadata (query signature, routing) |
| **KnowledgeChunk** | `know:` | API docs, schemas, conventions (Phase 2) |

**Example chunk IDs:**
- `code:auth/login.py:authenticate:45-89`
- `reas:payment-flow-decomposition:v3`
- `know:stripe-api:charges:create`

The prefix enables:
- Quick filtering by chunk type
- Separate activation pools if needed
- Clear provenance in logs and traces

### 6.7 Learning Updates & Conditional Lifespan Management

The system updates activations based on outcomes:

**Success (score >= 0.8):**
- +0.2 activation to all retrieved chunks
- Cache full pattern and mark as "pattern" for high-confidence retrieval

**Partial Success (score 0.5-0.8):**
- +0.05 to helpful chunks, -0.05 to unhelpful
- Cache to ACT-R but do NOT mark as "pattern" (lower confidence)

**Failure (score < 0.5):**
- -0.1 to retrieved reasoning patterns
- Do NOT cache to ACT-R
- Mark query as "difficult" for analysis

**Caching Policy**:
```json
{
  "cache_if_score_gte": 0.5,
  "mark_as_pattern_if_gte": 0.8,
  "include_confidence_flag": true
}
```

**Why Cache Partial Successes (0.5-0.8)?**
- Learn from "almost correct" attempts
- Identify patterns that need refinement
- Build statistical confidence over repeated similar queries
- Enable incremental improvement through activation decay

#### 6.7.1 Conditional Lifespan Policy

Beyond implicit time-based decay, chunks include explicit **conditional retention rules** that govern when/how they are retained or aged:

**Policy Types**:

| Type | Trigger Condition | Action |
|------|-------------------|--------|
| **Indefinite** | `is_pattern == true` | Retain forever (proven patterns) |
| **Confidence-Based** | `success_score >= 0.8` | Retain for N days (e.g., 365) |
| **Usage-Based** | `access_count > threshold` | Retain while actively used; decay after inactivity |
| **Importance-Based** | `contains_tag('security')` | Retain longer (e.g., 365 days for security) |
| **Escalation** | `access_count > 10` | Mark as candidate for fine-tuning/parametric conversion |
| **Decay-After-Inactivity** | `inactive_for_N_days` | Move to low-activation state or archive |

**Example Policy Configuration**:
```json
{
  "retention_policies": {
    "patterns": {
      "condition": "is_pattern == true AND success_score >= 0.8",
      "lifespan": "indefinite",
      "decay_mechanism": "logarithmic"
    },
    "security_critical": {
      "condition": "contains_tag('security') OR domain == 'security'",
      "lifespan": "365_days",
      "decay_mechanism": "none"
    },
    "high_usage": {
      "condition": "access_count > 10",
      "lifespan": "indefinite",
      "escalation_action": "candidate_for_fine_tuning"
    },
    "inactive": {
      "condition": "last_accessed_days > 90 AND access_count <= 2",
      "lifespan": "decay",
      "decay_mechanism": "exponential"
    }
  }
}
```

**When Policies Are Evaluated**:
1. **Phase 8 (RECORD)**: During storage decision (should this chunk be cached?)
2. **During Activation Calculation**: Base-level decay applies policy rules
3. **Periodic Maintenance**: System reviews inactive chunks based on policies
4. **Phase 2 Retrieval**: Chunks in "decay" state are deprioritized

**Why Conditional Policies**:
- **Compliance**: Retain security-related chunks longer for audit trails
- **Performance**: Decay inactive patterns to keep index lean
- **Learning**: Escalate high-usage patterns for fine-tuning
- **Flexibility**: Different chunk types have different lifecycle needs
- **Explicit**: No guessing about why chunks are retained/removed

### 6.8 ACT-R Storage Rules (Selective vs Complete Logs)

AURORA uses **two separate storage systems** with distinct purposes:

#### 6.8.1 ACT-R Memory (Selective Storage)

**Purpose**: Optimize retrieval by storing only successful patterns

**Storage Location**: SQLite database (`~/.aurora/memory.db`)

**What Gets Stored**:
- ReasoningChunks with score >= 0.5
- CodeChunks (function-level, based on usage)
- KnowledgeChunks (Phase 2+)

**Storage Rules**:

| Score Range | Action | Reasoning |
|-------------|--------|-----------|
| **>= 0.8** | Store + mark as "pattern" | High-confidence, proven pattern for direct reuse |
| **0.5-0.8** | Store (no pattern flag) | Partial success, learn from attempts, build statistical confidence |
| **< 0.5** | Do NOT store | Failed attempt, no learning value for retrieval |

**Data Stored per Chunk**:
```json
{
  "chunk_id": "reas:oauth-impl-20251213",
  "type": "reasoning",
  "content": {
    "pattern": "authentication-setup",
    "original_query": "Implement OAuth2 authentication",
    "complexity": "complex",
    "subgoals": [...],
    "tools_used": [
      {"subgoal": "SG1", "agent": "researcher", "tools": ["websearch", "mcp:reddit"]},
      {"subgoal": "SG2", "agent": "coder", "tools": ["grep", "read", "edit", "write"]}
    ],
    "tool_sequence": ["websearch", "mcp:reddit", "grep", "read", "edit", "write"],
    "success_score": 0.92,
    "verification_option": "option_b"
  },
  "activation": 0.85,
  "base_level_activation": 0.7,
  "spreading_activation": 0.15,
  "created_at": "2025-12-13T14:33:27Z",
  "last_accessed": "2025-12-13T14:33:27Z",
  "access_count": 1,
  "is_pattern": true
}
```

**Why Selective Storage?**
- **Performance**: Only retrieve high-quality patterns
- **Precision**: Reduce noise in activation calculations
- **Learning**: Focus on successful approaches, not failed attempts
- **Scalability**: Limit memory growth to valuable patterns only

#### 6.8.2 Conversation Logs (Complete Audit Trail)

**Purpose**: Complete record of ALL interactions for debugging, compliance, traceability

**Storage Location**: Markdown files organized by year/month
```
~/.aurora/logs/conversations/YYYY/MM/keyword1-keyword2-YYYY-MM-DD.md
```

**What Gets Stored**:
- **ALL** AURORA interactions, regardless of score
- Complete 9-phase SOAR execution trace
- All user ↔ agent interactions
- Full JSON outputs from each phase
- Execution metadata (tokens, cost, duration)

**Storage Rules**:
- **No filtering**: Every interaction is logged
- **Individual files**: One file per SOAR interaction (allows multiple same-day interactions)
- **Keyword-based naming**: 2 keywords extracted from query for easy identification
- **Year/month directories**: Organized by `YYYY/MM/` for efficient browsing
- **Retention**: 90 days (configurable)
- **Compression**: Auto-compress files older than 7 days

**Example Entry** (see Section 9.7 for full format):
```markdown
---
## Query: 2025-12-13T14:32:15Z | ID: aurora-20251213-143215-abc123

**User Query**: "Implement OAuth2 authentication"

### Phase 1: ASSESS
```json
{"phase": "assess", "complexity": "complex", "confidence": 0.87, ...}
```

### Phase 2-9: [Complete trace of all phases]

### Execution Summary
- **Total Duration**: 12.8 seconds
- **Verification Score**: 0.93 (stored to ACT-R: yes)
---
```

#### 6.8.2.1 Log Indexing (Plaintext Memory Discovery)

**Purpose**: Enable Phase 2 retrieval to discover and reference plaintext conversation logs without loading entire files

**How It Works**:

1. **Automatic Indexing** (during Phase 8: RECORD):
   - Extract keywords/topics from conversation log
   - Create SQLite index entries mapping keywords to log file + section

2. **Phase 2 Retrieval Fallback**:
   - If ACT-R query yields weak matches → Query log index
   - Return references (file + line range) instead of loading full logs
   - User/system can read original plaintext from reference

**Index Schema** (SQLite table: `log_index`):
```json
{
  "keyword": "oauth",
  "topic": "authentication",
  "file": "2025/12/oauth-authentication-2025-12-13.md",
  "section": "Phase 3: DECOMPOSE",
  "line_start": 45,
  "line_end": 78,
  "phase": 3,
  "query_id": "aurora-20251213-143215-abc123"
}
```

**Index Creation Rules**:
- Automatic: Extracted from each conversation log during storage
- Keywords: Top 5-7 NLP terms from log content (Phase 1-9 summaries)
- Topics: Derived from semantic roles (if chunks extracted governance metadata)
- Phases: Index entries tagged with their source phase for filtering

**Phase 2 Retrieval Integration**:
```
Phase 2: RETRIEVE [SOAR only]
├── Query 1: ACT-R activation-based retrieval
│   └── If activation score < threshold:
├── Query 2: Log index keyword search (fallback)
│   └── Return file references + line ranges
└── Output: context_bundle (ACT-R chunks + log references)
```

**Benefits**:
- Plaintext knowledge discoverable without structured extraction
- Reduces context window usage (references instead of full logs)
- Maintains complete audit trail while supporting semantic discovery
- Bridge to Phase 2 knowledge base (indexed logs → extracted facts)

**Examples**:
```
Query: "How do we implement OAuth2?"

ACT-R Results: [reas:oauth-impl-20251213 (activation: 0.85)]

Log Index Results: [
  {file: "oauth-authentication-2025-12-12.md", section: "Phase 3", lines: 56-124},
  {file: "oauth-research-2025-12-11.md", section: "Phase 1", lines: 23-67}
]

Phase 2 Output:
  - Cached pattern from ACT-R
  - "See oauth-authentication log, Phase 3, lines 56-124 for full decomposition"
```

#### 6.8.3 Key Differences

| Aspect | ACT-R Memory | Conversation Logs |
|--------|--------------|-------------------|
| **Purpose** | Learning & retrieval optimization | Audit trail & debugging |
| **Filter** | Selective (score >= 0.5) | Complete (all interactions) |
| **Storage** | SQLite (structured, indexed) | Markdown files (human-readable) |
| **Query** | Activation-based retrieval | Text search, date filtering |
| **Size** | Grows with successful patterns | Grows with all usage |
| **Retention** | Permanent (with decay) | 90 days (configurable) |
| **Access** | API queries, context retrieval | CLI commands, file system |

#### 6.8.4 Storage Lifecycle Example

**Scenario**: User asks "Implement OAuth2 authentication"

1. **During Execution**: All 9 phases execute
   - Phase 8 (RECORD): Checks verification_score = 0.93
   - **Action**: Score >= 0.5 → Store to ACT-R with `is_pattern: true` (score >= 0.8)
   - **Action**: Create conversation log file `oauth-authentication-2025-12-13.md` in `2025/12/` directory

2. **ACT-R Storage**:
   ```json
   {
     "chunk_id": "reas:oauth-impl-20251213",
     "content": {/* full decomposition */},
     "success_score": 0.93,
     "is_pattern": true,
     "activation": 0.85
   }
   ```

3. **Conversation Log**:
   - File: `~/.aurora/logs/conversations/2025/12/oauth-authentication-2025-12-13.md`
   - Complete markdown entry with all 9 phases
   - User interactions (2 questions from research-agent)
   - All agent outputs (JSON + natural language summaries)
   - Execution summary

**Next Similar Query** (1 week later):

1. **Phase 2 (RETRIEVE)**: ACT-R finds `reas:oauth-impl-20251213` with high activation (0.85)
2. **Phase 3 (DECOMPOSE)**: Uses retrieved pattern as template
3. **Conversation Log**: New file `oauth-implementation-2025-12-20.md` in `2025/12/` directory

**If Score Had Been 0.45** (failure):

- **ACT-R**: Would NOT store (score < 0.5)
- **Conversation Log**: Would STILL log complete trace for debugging

**Summary**:
- **ACT-R**: "Remember what works" (selective, optimized for retrieval)
- **Conversation Logs**: "Record what happened" (complete, optimized for audit)

---

## 7. SOAR ORCHESTRATOR

### 7.1 Amalgamated Architecture

Unlike traditional SOAR implementations, AURORA-Context uses an **amalgamated** architecture where all phases are handled by a single orchestrator.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AURORA SOAR ORCHESTRATOR (packages/soar/)                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Phase 1: ASSESS [SOAR calls reasoning/]                                    │
│  ├── Call: reasoning.assessment.assess() (complexity classification)        │
│  ├── Input: user query                                                      │
│  └── Output: complexity_level, confidence, method                           │
│                                                                              │
│  Phase 2: RETRIEVE [SOAR only]                                              │
│  ├── Call: core.activation.retrieve() (ACT-R memory lookup)                 │
│  ├── Input: query + context_budget                                          │
│  └── Output: context_bundle (code, reasoning, knowledge chunks)             │
│                                                                              │
│  Phase 3: DECOMPOSE [SOAR calls reasoning/]                                 │
│  ├── Call: reasoning.decompose.decompose() (LLM reasoning)                  │
│  ├── Input: query + context_bundle                                          │
│  └── Output: decomposition_json with subgoals                               │
│                                                                              │
│  Phase 4: VERIFY [SOAR calls reasoning/]                                    │
│  ├── Call: reasoning.verify.verify() (Options A/B/C)                        │
│  ├── Input: decomposition + verification_option                             │
│  └── Output: score, verdict (pass/retry/fail), issues                       │
│                                                                              │
│  Phase 5: ROUTE [SOAR only]                                                 │
│  ├── Query: agent_registry (available agents)                               │
│  ├── Match: subgoals to agents based on capabilities                        │
│  └── Output: routing_plan                                                   │
│                                                                              │
│  Phase 6: COLLECT [SOAR only]                                               │
│  ├── Execute: agents in parallel where possible                             │
│  ├── Verify: agent outputs (format validation)                              │
│  └── Output: agent_outputs[] (JSON envelopes with summaries)                │
│                                                                              │
│  Phase 7: SYNTHESIZE [SOAR calls reasoning/]                                │
│  ├── Call: reasoning.synthesize.synthesize() (LLM recomposition)            │
│  ├── Input: agent_summaries (natural language from each agent)              │
│  └── Output: final_answer (natural language) + verification JSON            │
│                                                                              │
│  Phase 8: RECORD [SOAR only]                                                │
│  ├── Call: core.store.save() (ACT-R persistence)                            │
│  ├── Logic: if final_score >= 0.5, cache to SQLite                          │
│  └── Output: cached (bool), chunk_id                                        │
│                                                                              │
│  Phase 9: RESPOND [SOAR only]                                               │
│  ├── Format: response per verbosity level (quiet/normal/verbose/json)       │
│  ├── Log: complete interaction to conversation logs                         │
│  └── Output: response + metadata                                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Legend:**
- `[SOAR only]` = soar/ handles orchestration (packages/soar/phases/)
- `[SOAR calls reasoning/]` = soar/ coordinates, reasoning/ does the LLM work (packages/reasoning/)
- LLM-based phases: 1 (ASSESS), 3 (DECOMPOSE), 4 (VERIFY), 7 (SYNTHESIZE)

### 7.2 Agent Registry

The system maintains an agent registry with auto-discovery:

```json
{
  "agent_registry": {
    "agents": [
      {
        "id": "code-developer",
        "type": "mcp",
        "path": "~/.claude/agents/code-developer",
        "endpoint": null,
        "capabilities": ["code_implementation", "debugging", "refactoring"],
        "domains": ["python", "javascript", "go"],
        "availability": "always",
        "success_rate": 0.92,
        "last_refresh": "2025-12-12T10:00:00Z"
      },
      {
        "id": "research-agent",
        "type": "executable",
        "path": "/usr/local/bin/research-agent",
        "endpoint": null,
        "capabilities": ["web_search", "documentation_lookup"],
        "domains": ["general"],
        "availability": "always",
        "success_rate": 0.88,
        "last_refresh": "2025-12-12T10:00:00Z"
      },
      {
        "id": "remote-coder",
        "type": "http",
        "path": null,
        "endpoint": "https://api.example.com/agents/coder",
        "capabilities": ["code_generation"],
        "domains": ["python"],
        "availability": "depends_on_network",
        "success_rate": 0.85,
        "last_refresh": "2025-12-12T10:00:00Z"
      }
    ],
    "refresh_interval_days": 15,
    "auto_discover": true
  }
}
```

**Agent Types**:
- **`mcp`**: MCP server agent (path to MCP server config or executable)
- **`executable`**: Standalone script/binary (path to executable, invoked via shell)
- **`http`**: HTTP API endpoint (endpoint URL for REST calls)
- **`builtin`**: Built-in Aurora agent like "llm-executor" (no path needed)

**Agent Response Format**:
All agents registered in this registry MUST return responses following the format specified in **Section 7.2.1**. This ensures consistent synthesis and verification across all agent types.

**Registry Operations:**
- Auto-discover agents from MCP server configuration
- Periodic refresh (configurable interval, default 15 days)
- Check file modification timestamps before refresh
- Manual refresh via CLI: `aurora agents refresh`
- List agents via CLI: `aurora agents list`
- Track agent success rates for improved routing

### 7.2.1 Agent Response Format

All agents must return a **JSON response** with the following structure:

**Recommended Format** (LLM-Adaptive):

```json
{
  "subgoal_id": "string (which subgoal this answers)",
  "agent_id": "string (agent that executed)",
  "status": "success | partial | error",
  "output": {
    "summary": "string (REQUIRED: natural language summary for synthesis)",
    "data": {
      // FLEXIBLE: LLM decides structure based on subgoal needs
      // Can be any JSON structure appropriate for the task
      // Examples: {"providers": [...]} or {"analysis": "..."} or any schema
    },
    "confidence": "number 0.0-1.0 (REQUIRED: for verification)"
  },
  "user_interactions": [
    {
      "turn": "number",
      "agent_question": "string",
      "user_response": "string",
      "timestamp": "ISO 8601"
    }
  ],
  "metadata": {
    "tools_used": ["array of tool names"],
    "duration_ms": "number",
    "model_used": "string (optional)"
  },
  "error": "string (only if status=error)"
}
```

**Example Response**:

```json
{
  "subgoal_id": "SG1",
  "agent_id": "research-agent",
  "status": "success",
  "output": {
    "summary": "Auth0 recommended for $2000 budget. Setup: 1-2 days, includes social auth (saves 2 weeks dev time).",
    "data": {
      "providers": [
        {
          "name": "Auth0",
          "pricing": {"monthly": 25, "mau": 7000},
          "features": ["social_auth", "mfa"],
          "setup_time": "1-2 days"
        },
        {
          "name": "Okta",
          "pricing": {"monthly": 100, "mau": "unlimited"},
          "features": ["enterprise_sso"],
          "setup_time": "1 week"
        }
      ],
      "recommendation": "Auth0",
      "reasoning": "Fits budget, fastest setup, includes social auth"
    },
    "confidence": 0.92
  },
  "user_interactions": [
    {
      "turn": 1,
      "agent_question": "What's your monthly budget for OAuth2 service?",
      "user_response": "$2000",
      "timestamp": "2025-12-13T10:01:15Z"
    },
    {
      "turn": 2,
      "agent_question": "How urgent is your timeline?",
      "user_response": "Need to launch in 2 weeks",
      "timestamp": "2025-12-13T10:01:32Z"
    }
  ],
  "metadata": {
    "tools_used": ["websearch", "mcp:pricing_db"],
    "duration_ms": 3420,
    "model_used": "claude-sonnet-4.5"
  }
}
```

**Design Philosophy**:

1. **Required Fields**:
   - `summary` (natural language): Enables synthesis to recompose into final answer
   - `confidence` (number): Enables verification scoring

2. **Flexible `data` Structure**:
   - LLM adapts schema to subgoal needs (not too rigid)
   - Can be any JSON appropriate for the task
   - No forced schemas - balance structure with flexibility

3. **User Interactions Tracked**:
   - Full conversation history for audit/traceability
   - Agents may ask clarifying questions during execution
   - Final response includes all user interactions

4. **Synthesis Flow**:
   - Agents return structured JSON (possibly after user interactions)
   - SOAR Phase 7 gathers all `summary` fields (natural language)
   - Synthesis LLM recomposes summaries → ONE natural language answer
   - User receives natural language (NOT JSON)

5. **Two Storage Systems**:
   - **ACT-R** (selective): Stores patterns based on score thresholds (learning/retrieval)
   - **Conversation Logs** (complete): All interactions logged to markdown files (audit/debugging)

**Agent Implementation Note**:
- Agents can be any type (MCP, executable, HTTP, builtin)
- All must conform to this response format
- Simple text-only agents can use: `{"summary": "text response", "data": {}, "confidence": 0.8}`

---

## 8. LLM PROMPT SPECIFICATIONS

### 8.1 Prompt Design Philosophy

All LLM prompts in the system MUST:
- Enforce JSON-only output (no markdown, no explanation)
- Specify exact output schema with validation rules
- Include minimal necessary context to reduce token usage
- Use structured sections: system, task, schema, constraints

### 8.2 Complexity Assessment (Two-Tier Approach)

**Tier 1: Keyword-Based Classifier** (Internal Function, No LLM)

**Purpose**: Fast, free complexity assessment for 60-70% of queries

**Implementation**: See Appendix G for complete Python implementation

**Flow**:
```
1. Run keyword classifier (instant, free)
   ↓
2. If confidence ≥ 0.8 → Use keyword result (skip LLM)
   ↓
3. If confidence < 0.8 OR score in [0.4, 0.6] → Run Tier 2 (LLM verification)
```

**Benefits**:
- **Zero cost** for clear cases (60-70% of queries)
- **Instant** classification (~50ms vs 200ms LLM call)
- **Configurable** keyword dictionaries per domain

---

**Tier 2: LLM Verification** (Only for Borderline Cases)

**Triggered when**:
- Keyword classifier confidence < 0.8
- Keyword score in borderline range [0.4, 0.6]
- User explicitly requests LLM classification

**LLM Prompt**:
```json
{
  "system": "You are a complexity classifier. Respond with ONLY valid JSON.",
  "task": "Classify query complexity based on: multi-step reasoning, ambiguity, domain expertise needed, verification requirements.",
  "query": "{user_query}",
  "keyword_result": "{keyword_complexity} (confidence: {keyword_confidence})",
  "schema": {
    "complexity": "simple | medium | complex | critical",
    "confidence": "number 0.0-1.0",
    "reasoning": "string 2-3 sentences",
    "indicators": ["array of keywords"],
    "recommended_verification": "none | option_a | option_b | option_c",
    "keyword_assessment_correct": "bool"
  },
  "rules": {
    "simple": "Direct answer, no decomposition (e.g., 'What is X?', 'List Y')",
    "medium": "2-3 steps, low ambiguity (e.g., 'Compare A and B')",
    "complex": "4+ steps, high ambiguity (e.g., 'Design system for X')",
    "critical": "Mission-critical or safety-critical decisions"
  },
  "output": "JSON only, no markdown, no text outside JSON"
}
```

**Cost Savings**:
- Without keyword tier: 100% of queries use LLM (~$0.0002/query)
- With keyword tier: 30-40% use LLM (~$0.00008/query average)
- **Savings**: ~60% reduction in complexity assessment costs

### 8.3 Decomposition Prompt

```json
{
  "system": "You are a reasoning decomposition engine. Respond with ONLY valid JSON.",
  "task": "Break query into 2-5 executable subgoals with dependencies.",
  "query": "{user_query}",
  "context": "{retrieved_chunks}",
  "available_agents": [
    {"id": "agent-id", "capabilities": ["list"], "domains": ["list"]}
  ],
  "schema": {
    "decomposition": {
      "id": "uuid",
      "original_query": "string",
      "given": [{"id": "G1", "fact": "string", "source": "query|context"}],
      "goal": {"description": "string", "success_criteria": ["array"]},
      "subgoals": [{
        "id": "SG1",
        "description": "string",
        "requires": ["G1"],
        "agent": "agent-id",
        "expected_output": "string",
        "depends_on": []
      }],
      "execution_order": ["SG1", "SG2"],
      "parallelizable": [["SG1", "SG2"]]
    }
  },
  "constraints": {
    "max_subgoals": 5,
    "dependencies_must_be_dag": true,
    "each_subgoal_traces_to_given": true
  },
  "output": "JSON only, no markdown, no text outside JSON"
}
```

### 8.4 Decomposition Verification Prompt

```json
{
  "system": "You are a critical verification engine. Check decomposition validity. Respond with ONLY valid JSON.",
  "task": "Verify decomposition structure and logic (NOT solve the problem).",
  "decomposition": "{decomposition_json}",
  "checks": {
    "completeness": "Do subgoals fully cover original goal?",
    "consistency": "Do subgoals contradict each other or have circular dependencies?",
    "groundedness": "Does each subgoal trace to given facts?",
    "routability": "Is agent assignment appropriate for each subgoal?"
  },
  "schema": {
    "verification": {
      "decomposition_id": "string",
      "checks": {
        "completeness": {"score": "0.0-1.0", "pass": "bool", "issues": ["array"], "detail": "string"},
        "consistency": {"score": "0.0-1.0", "pass": "bool", "issues": ["array"], "detail": "string"},
        "groundedness": {"score": "0.0-1.0", "pass": "bool", "issues": ["array"], "detail": "string"},
        "routability": {"score": "0.0-1.0", "pass": "bool", "issues": ["array"], "detail": "string"}
      },
      "overall_score": "0.0-1.0 (weighted average)",
      "verdict": "pass | retry | fail",
      "critical_issues": ["array"],
      "suggestions": ["array"]
    }
  },
  "scoring": {
    "0.9-1.0": "Excellent",
    "0.7-0.9": "Good, minor issues",
    "0.5-0.7": "Needs improvement",
    "0.0-0.5": "Major issues"
  },
  "verdict_rules": {
    "pass": "overall_score >= 0.7",
    "retry": "overall_score 0.5-0.7",
    "fail": "overall_score < 0.5"
  },
  "calibration_examples": [
    {
      "complexity": "medium",
      "query": "Build OAuth2 authentication",
      "decomposition": {
        "subgoals": ["SG1: Research OAuth2", "SG2: Implement login"]
      },
      "expected_scores": {
        "completeness": 0.5,
        "consistency": 0.9,
        "groundedness": 0.8,
        "routability": 0.9
      },
      "overall_score": 0.67,
      "why": "Missing critical steps: password hashing (SG3), token generation (SG4), logout (SG5). Only 2 subgoals for complex auth = incomplete."
    },
    {
      "complexity": "medium",
      "query": "Build OAuth2 authentication",
      "decomposition": {
        "subgoals": ["SG1: Research OAuth2", "SG2: Design user model", "SG3: Hash passwords", "SG4: Login endpoint", "SG5: Token generation", "SG6: Logout"]
      },
      "expected_scores": {
        "completeness": 0.95,
        "consistency": 0.95,
        "groundedness": 0.9,
        "routability": 0.95
      },
      "overall_score": 0.94,
      "why": "Covers all auth components systematically. Each step traces to OAuth2 requirements."
    }
  ],
  "note": "Examples scaled by complexity: MEDIUM=2, COMPLEX=4, CRITICAL=6 (see Appendix C)",
  "output": "JSON only, no markdown, no text outside JSON"
}
```

### 8.5 Agent Output Verification Prompt

```json
{
  "system": "You are a critical output verifier. Respond with ONLY valid JSON.",
  "task": "Verify agent output addresses assigned subgoal.",
  "subgoal": "{subgoal_json}",
  "agent_response": "{agent_response_json (see Section 7.2.1 for format)}",
  "checks": {
    "relevance": "Does output.summary address the subgoal description?",
    "completeness": "Is output.summary complete? Does output.data provide supporting evidence?",
    "groundedness": "Are claims in output.summary specific and verifiable (not vague)?"
  },
  "schema": {
    "verification": {
      "subgoal_id": "string",
      "checks": {
        "relevance": {"score": "0.0-1.0", "pass": "bool", "issues": ["array"], "detail": "string"},
        "completeness": {"score": "0.0-1.0", "pass": "bool", "issues": ["array"], "detail": "string"},
        "groundedness": {"score": "0.0-1.0", "pass": "bool", "issues": ["array"], "detail": "string"}
      },
      "overall_score": "0.0-1.0",
      "verdict": "pass | retry | fail",
      "issues": ["array"],
      "suggestions": ["array if retry"]
    }
  },
  "verdict_rules": {
    "pass": "overall_score >= 0.7",
    "retry": "overall_score 0.5-0.7 AND retry_count < 2",
    "fail": "overall_score < 0.5 OR retry_count >= 2"
  },
  "calibration_examples": [
    {
      "complexity": "medium",
      "subgoal": {"id": "SG1", "description": "Research OAuth2 providers"},
      "agent_response": {
        "output": {
          "summary": "OAuth2 is a protocol. Popular providers exist.",
          "data": {},
          "confidence": 0.5
        }
      },
      "expected_scores": {
        "relevance": 0.6,
        "completeness": 0.3,
        "groundedness": 0.4
      },
      "overall_score": 0.43,
      "why": "Vague summary, no structured data. Missing provider comparison, pricing, features. Not actionable."
    },
    {
      "complexity": "medium",
      "subgoal": {"id": "SG1", "description": "Research OAuth2 providers"},
      "agent_response": {
        "output": {
          "summary": "Auth0 recommended for $2000 budget. Setup: 1-2 days, includes social auth (saves 2 weeks dev time).",
          "data": {
            "providers": [
              {"name": "Auth0", "price": 25, "setup": "1-2 days"},
              {"name": "Okta", "price": 100, "setup": "1 week"},
              {"name": "Custom", "price": 0, "setup": "4 weeks"}
            ],
            "recommendation": "Auth0"
          },
          "confidence": 0.92
        }
      },
      "expected_scores": {
        "relevance": 0.95,
        "completeness": 0.9,
        "groundedness": 0.95
      },
      "overall_score": 0.93,
      "why": "Clear summary + structured data. Specific providers, pricing, tradeoffs. Actionable for decision-making."
    }
  ],
  "note": "Examples scaled by complexity: MEDIUM=2, COMPLEX=4, CRITICAL=6",
  "output": "JSON only, no markdown, no text outside JSON"
}
```

### 8.6 Synthesis Verification Prompt

**Note**: Synthesis (Phase 7) combines all agent `summary` fields into ONE natural language final answer. This prompt VERIFIES that natural language synthesis.

```json
{
  "system": "You are a final synthesis verifier. Respond with ONLY valid JSON.",
  "task": "Verify final natural language answer addresses original query using agent summaries.",
  "original_query": "{query}",
  "agent_summaries": [
    {
      "subgoal_id": "SG1",
      "summary": "string (natural language from agent)",
      "confidence": "number"
    }
  ],
  "synthesis": "{final_natural_language_answer}",
  "checks": {
    "addresses_query": "Does synthesis directly answer the original query?",
    "traceable": "Can every claim in synthesis link to an agent summary?",
    "consistent": "Are there contradictions between synthesis claims?",
    "calibrated": "Is confidence level appropriate given agent confidences?"
  },
  "schema": {
    "verification": {
      "checks": {
        "addresses_query": {"score": "0.0-1.0", "pass": "bool", "issues": ["array"], "detail": "string"},
        "traceable": {"score": "0.0-1.0", "pass": "bool", "issues": ["array"], "detail": "string"},
        "consistent": {"score": "0.0-1.0", "pass": "bool", "issues": ["array"], "detail": "string"},
        "calibrated": {"score": "0.0-1.0", "pass": "bool", "issues": ["array"], "detail": "string"}
      },
      "overall_score": "0.0-1.0",
      "verdict": "pass | retry | fail",
      "cache_recommendation": "cache | no_cache (cache if overall_score >= 0.8)",
      "issues": ["array"],
      "suggestions": ["array if retry"]
    }
  },
  "calibration_examples": [
    {
      "complexity": "medium",
      "query": "Which OAuth2 provider should we use?",
      "agent_summaries": [
        {"subgoal_id": "SG1", "summary": "Auth0 $25/mo (7k MAU), Okta $100/mo (enterprise), Custom free (4 week dev time)", "confidence": 0.92},
        {"subgoal_id": "SG2", "summary": "Auth0 fastest setup (1-2 days), Okta enterprise features, Custom most flexible", "confidence": 0.88}
      ],
      "synthesis": "Based on research, Auth0 is good.",
      "expected_scores": {
        "addresses_query": 0.5,
        "traceable": 0.4,
        "consistent": 0.9,
        "calibrated": 0.3
      },
      "overall_score": 0.45,
      "why": "Doesn't explain WHY Auth0. Missing context: user's budget, timeline, team size. Over-confident conclusion ('good') from thin reasoning. Claims don't trace well to agent summaries."
    },
    {
      "complexity": "medium",
      "query": "Which OAuth2 provider should we use?",
      "agent_summaries": [
        {"subgoal_id": "SG1", "summary": "Auth0 $25/mo (7k MAU), Okta $100/mo (enterprise), Custom free (4 week dev time)", "confidence": 0.92},
        {"subgoal_id": "SG2", "summary": "Auth0 fastest setup (1-2 days), includes social auth. Okta enterprise features. Custom most flexible but requires security audit.", "confidence": 0.88},
        {"subgoal_id": "SG3", "summary": "User budget: $2000/mo. Timeline: urgent (2 weeks). Team size: 10 people.", "confidence": 1.0}
      ],
      "synthesis": "For your 10-person startup with $2000 budget and urgent 2-week timeline, we recommend Auth0. It costs $25/mo (well within budget) and setup takes only 1-2 days (meets deadline). Auth0 includes social authentication which saves approximately 2 weeks of development time. Compared to alternatives: Okta is $100/mo (over budget for startup), and Custom would take 4 weeks to build (missing your deadline) plus requires ongoing security audits.",
      "expected_scores": {
        "addresses_query": 0.95,
        "traceable": 0.95,
        "consistent": 0.95,
        "calibrated": 0.9
      },
      "overall_score": 0.94,
      "why": "Context-specific recommendation using user constraints from SG3. Every claim traces to agent summaries (pricing from SG1, setup time from SG2, constraints from SG3). Acknowledges tradeoffs. Appropriate confidence given high agent confidence scores."
    }
  ],
  "note": "Examples scaled by complexity: MEDIUM=2, COMPLEX=4, CRITICAL=6",
  "output": "JSON only, no markdown, no text outside JSON"
}
```

### 8.7 Retry Feedback Prompt

```json
{
  "system": "You are a retry coordinator. Respond with ONLY valid JSON.",
  "task": "Provide structured feedback for retry attempt.",
  "checkpoint": "decomposition | agent_output | synthesis",
  "attempt_number": "number",
  "max_attempts": 2,
  "previous_score": "number",
  "verification_result": "{verification_json}",
  "schema": {
    "retry_feedback": {
      "attempt": "number",
      "previous_score": "number",
      "issues": [
        {
          "check": "string (which check failed)",
          "score": "number",
          "issue": "string (what's wrong)",
          "suggestion": "string (how to fix)"
        }
      ],
      "instruction": "string (clear directive for next attempt)",
      "escalate": "bool (true if retry_count >= max_attempts)"
    }
  },
  "output": "JSON only, no markdown, no text outside JSON"
}
```

---

## 9. IMPLEMENTATION DETAILS

### 9.1 Repository Structure

```
aurora-context/
├── README.md
├── pyproject.toml                 # Root project config
├── Makefile                       # Common commands
│
├── packages/
│   ├── core/                      # Core library (no external deps)
│   │   ├── pyproject.toml
│   │   └── src/aurora_core/
│   │       ├── __init__.py
│   │       ├── activation/        # ACT-R activation engine (uses pyactr for math)
│   │       │   ├── engine.py      # Main activation calculator
│   │       │   ├── base_level.py  # Frequency + recency decay
│   │       │   ├── spreading.py   # Context spreading
│   │       │   └── retrieval.py   # Threshold-based retrieval
│   │       ├── chunks/            # Chunk type definitions
│   │       │   ├── base.py        # Abstract Chunk interface
│   │       │   ├── code_chunk.py  # code: prefixed chunks
│   │       │   ├── reasoning_chunk.py  # reas: prefixed chunks
│   │       │   └── knowledge_chunk.py  # know: prefixed chunks (Phase 2)
│   │       ├── store/             # Persistence layer (SQLite + JSON)
│   │       │   ├── base.py        # Abstract Store interface
│   │       │   ├── sqlite.py      # SQLite for chunks + activations
│   │       │   └── memory.py      # In-memory for testing
│   │       ├── logging/           # Comprehensive logging
│   │       │   ├── logger.py      # Main logger
│   │       │   ├── metrics.py     # Metrics collection
│   │       │   └── reporting.py   # Daily/cumulative/monthly reports
│   │       └── types.py           # Shared types (ChunkID, Activation)
│   │
│   ├── soar/                      # SOAR Orchestrator (depends on reasoning/)
│   │   ├── pyproject.toml
│   │   └── src/aurora_soar/
│   │       ├── __init__.py
│   │       ├── orchestrator.py    # Main SOAR orchestrator (entry point)
│   │       ├── phases/            # SOAR phases (orchestration layer)
│   │       │   ├── assess.py      # Phase 1: Assess complexity (calls reasoning.assessment)
│   │       │   ├── retrieve.py    # Phase 2: Retrieve context (calls core.activation)
│   │       │   ├── decompose.py   # Phase 3: Decompose to subgoals (calls reasoning.decompose)
│   │       │   ├── verify.py      # Phase 4: Verify decomposition (calls reasoning.verify)
│   │       │   ├── route.py       # Phase 5: Route to agents (SOAR logic)
│   │       │   ├── collect.py     # Phase 6: Collect agent outputs (SOAR logic)
│   │       │   ├── synthesize.py  # Phase 7: Synthesize results (calls reasoning.synthesize)
│   │       │   ├── record.py      # Phase 8: Record to ACT-R (calls core.store)
│   │       │   └── respond.py     # Phase 9: Format response (SOAR logic)
│   │       └── agent_registry.py  # Agent discovery + refresh
│   │
│   ├── reasoning/                 # Reasoning pipeline (independent, reusable)
│   │   ├── pyproject.toml
│   │   └── src/aurora_reasoning/
│   │       ├── __init__.py
│   │       ├── pipeline.py        # Main pipeline interface
│   │       ├── assessment.py      # Complexity assessment (keyword + LLM)
│   │       ├── decompose.py       # Structured decomposition (LLM)
│   │       ├── verify.py          # Verification (Options A/B/C, LLM)
│   │       ├── synthesize.py      # Result synthesis (LLM)
│   │       ├── learn.py           # Learning loop logic
│   │       └── prompts/           # LLM prompts (all 6 verification types)
│   │           ├── assess.py
│   │           ├── decompose.py
│   │           ├── verify_self.py
│   │           ├── verify_adversarial.py
│   │           ├── verify_agent_output.py
│   │           ├── verify_synthesis.py
│   │           └── retry_feedback.py
│   │
│   ├── context-code/              # Code context provider (cAST)
│   │   ├── pyproject.toml
│   │   └── src/aurora_context_code/
│   │       ├── __init__.py
│   │       ├── provider.py        # CodeContextProvider
│   │       ├── parser.py          # cAST tree-sitter wrapper
│   │       ├── git.py             # Git signal extraction
│   │       ├── chunker.py         # Function-level chunking
│   │       └── languages/         # Language-specific parsers
│   │           ├── python.py      # tree-sitter-python (Phase 1)
│   │           ├── typescript.py  # tree-sitter-typescript (Phase 1, covers JS/TS/TSX/JSX)
│   │           └── go.py          # tree-sitter-go (Phase 1.5, high AI dev usage)
│   │
│   ├── context-reasoning/         # Reasoning context provider
│   │   ├── pyproject.toml
│   │   └── src/aurora_context_reasoning/
│   │       ├── __init__.py
│   │       ├── provider.py
│   │       ├── patterns.py
│   │       └── similarity.py
│   │
│   ├── mcp-server/                # MCP server for agent integration
│   │   ├── pyproject.toml
│   │   └── src/aurora_mcp/
│   │       ├── __init__.py
│   │       ├── server.py          # MCP server implementation
│   │       ├── tools.py           # Tool definitions
│   │       ├── handlers.py        # Request handlers
│   │       └── notifications.py   # Progress notifications
│   │
│   └── cli/                       # CLI interface
│       ├── pyproject.toml
│       └── src/aurora_cli/
│           ├── __init__.py
│           ├── main.py
│           ├── commands/
│           │   ├── assess.py
│           │   ├── decompose.py
│           │   ├── verify.py
│           │   ├── context.py
│           │   ├── learn.py
│           │   ├── agents.py      # Agent registry commands
│           │   └── report.py      # Reporting commands
│           └── output.py          # Output formatting
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

### 9.1.1 Package Architecture & Dependencies

**Separation of Concerns:**

```
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION LAYER                       │
│                    (packages/soar/)                          │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐   │
│  │ Phase 1  │ Phase 2  │ Phase 3  │ Phase 4  │ Phase 5  │   │
│  │ (SOAR)   │ (SOAR)   │ (REASON) │ (REASON) │ (SOAR)   │   │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘   │
│       ↓          ↓          ↓          ↓          ↓          │
│   assess  →  retrieve  →  decompose → verify   →  route    │
└────────────────────────────────────────────────────────────┬─┘
                                                              │
                 ↓                                            │
        ┌────────────────────────────────────────┐           │
        │       REASONING LAYER                   │           │
        │    (packages/reasoning/)                │           │
        │                                         │           │
        │  • assessment.py (complexity)          │           │
        │  • decompose.py (LLM reasoning)        │           │
        │  • verify.py (A/B/C verification)      │           │
        │  • synthesize.py (result synthesis)    │           │
        │  • prompts/ (all LLM prompts)          │           │
        └────────────────────────────────────────┘           │
                                                              │
                 ↓ (phases 6-9)                               │
        ┌────────────────────────────────────────┐           │
        │       ORCHESTRATION LAYER (cont)       │           │
        │                                         │           │
        │  • collect.py (Phase 6)                │           │
        │  • synthesize.py (Phase 7)  ─────────┐ │           │
        │  • record.py (Phase 8)               │ │           │
        │  • respond.py (Phase 9)               │ │           │
        └────────────────────────────────────────┘           │
                                                              │
                                                   ←──────────┘
                                    calls reasoning.synthesize
```

**Package Roles:**

| Package | Role | Scope | Dependencies |
|---------|------|-------|--------------|
| **soar/** | Orchestration & coordination | 9-phase workflow, phase management | core/, reasoning/, context-*, mcp-server |
| **reasoning/** | LLM-based reasoning | Prompts, verification logic, assessment | core/ (for types) |
| **core/** | Foundation | ACT-R memory, activation, storage | pyactr (formulas only) |
| **context-code/** | Code context extraction | Code parsing, chunking | core/ |
| **context-reasoning/** | Pattern retrieval | Similarity matching | core/ |

**Dependency Flow:**
```
soar/ ──depends on──> reasoning/
  │                      │
  └──depends on──> core/ <────┘
                     │
          depends on─┼──> context-code/
                     │
                     └──> context-reasoning/
```

**Key Design Decision:**
- **soar/** and **reasoning/** are separate packages to enable:
  - ✅ Independent iteration on reasoning prompts/logic without touching orchestration
  - ✅ Isolated testing of reasoning in development cycle
  - ✅ Future flexibility: swap reasoning backends without changing orchestrator
  - ✅ Version independence: reasoning v1.2 with soar v1.0

- **soar/** CALLS **reasoning/** for LLM-based phases (1, 3, 4, 7)
- **soar/** ORCHESTRATES phases and manages flow

### 9.2 Supported Languages

**Code Context Parsing** (cAST via tree-sitter):

**Phase 1 (MVP)**:
- **Python** (`.py`) - tree-sitter-python
  - Primary AI dev language, full support
- **TypeScript/JavaScript** (`.ts`, `.tsx`, `.js`, `.jsx`) - tree-sitter-typescript
  - #1 language for AI CLI tools (Claude Code, Cursor, Continue, Cody)
  - Single parser covers all JS/TS variants

**Phase 1.5** (High priority based on AI dev adoption):
- **Go** (`.go`) - tree-sitter-go
  - Common for backend AI services, CLI tools, Kubernetes/cloud-native AI
  - Examples: vector DBs, embedding servers, gh/kubectl patterns

**Phase 2+** (Based on community demand):
- **Rust** (`.rs`) - Systems programming, performance-critical agents
- **Java** (`.java`) - Enterprise AI applications
- **C++** (`.cpp`, `.cc`) - ML/AI inference engines
- **Ruby** (`.rb`) - Rails-based AI apps

**Why These Languages First?**
1. **TypeScript** - Dominant in AI CLI tooling ecosystem
2. **Python** - Default for AI/ML development
3. **Go** - Increasingly common for AI infrastructure

### 9.3 Installation Options

```bash
# Full install (everything - most users)
pip install aurora-context[all]

# Just MCP server (for CLI agent integration)
pip install aurora-context[mcp]

# Just core (for custom integrations / library use)
pip install aurora-context-core

# Development install (all packages editable)
git clone https://github.com/yourorg/aurora-context
cd aurora-context
pip install -e ".[dev]"
```

### 9.4 Logging and Metrics

**Logging Configuration:**
```json
{
  "logging": {
    "levels": ["DEBUG", "INFO", "WARN", "ERROR"],
    "default_level": "INFO",
    "outputs": ["console", "file", "json"],
    "log_path": "~/.aurora/logs/",
    "rotation": {
      "max_size_mb": 100,
      "max_files": 10
    }
  }
}
```

**Metrics to Collect:**

| Metric | Type | Description |
|--------|------|-------------|
| `aurora_queries_total` | counter | Total queries processed |
| `aurora_query_complexity` | histogram | Distribution by complexity |
| `aurora_verification_score` | histogram | Distribution of verification scores |
| `aurora_cache_hits` | counter | ACT-R cache hit count |
| `aurora_retry_count` | counter | Retry attempts by checkpoint |
| `aurora_agent_latency_ms` | histogram | Agent execution time |
| `aurora_llm_calls` | counter | LLM API calls by type |
| `aurora_tokens_used` | counter | Token consumption |

#### 9.4.1 Timing Breakdown with Percentages

**Purpose:** Track execution time per phase with percentage of total query time to identify bottlenecks.

**What's Tracked:**
- **Per-phase duration** (`duration_ms`) - Already exists
- **Phase percentage** (NEW) - `percentage = (phase_duration / total_duration) × 100`
- **Total query duration** - Sum of all phases

**Example Output:**
```json
{
  "execution_summary": {
    "total_duration_ms": 12785,
    "phases": [
      {
        "phase": "GUARDRAILS",
        "duration_ms": 45,
        "percentage": 0.4
      },
      {
        "phase": "ASSESS",
        "duration_ms": 450,
        "percentage": 3.5
      },
      {
        "phase": "RETRIEVE",
        "duration_ms": 320,
        "percentage": 2.5
      },
      {
        "phase": "DECOMPOSE",
        "duration_ms": 2100,
        "percentage": 16.4
      },
      {
        "phase": "VERIFY (Decomposition)",
        "duration_ms": 1800,
        "percentage": 14.1
      },
      {
        "phase": "ROUTE",
        "duration_ms": 120,
        "percentage": 0.9
      },
      {
        "phase": "COLLECT (Agents)",
        "duration_ms": 12500,
        "percentage": 97.8
      },
      {
        "phase": "SYNTHESIZE",
        "duration_ms": 1500,
        "percentage": 11.7
      },
      {
        "phase": "VERIFY (Synthesis)",
        "duration_ms": 1200,
        "percentage": 9.4
      }
    ]
  }
}
```

**Benefit:**
- **Immediately identify bottlenecks:** "Agents took 97.8% → optimize agents first"
- **Prioritize optimization efforts:** Focus on phases with highest percentage
- **Track performance regressions:** Monitor percentage changes over time
- **Validate improvements:** Verify that optimizations reduce phase percentage

**Configuration:**
```json
{
  "logging": {
    "timing": {
      "enabled": true,
      "include_percentages": true,
      "breakdown_level": "phase"
    }
  }
}
```

**Note:** Percentages may sum to more than 100% if phases overlap or run in parallel. The percentage represents each phase's duration relative to total query time from start to finish.

---

#### 9.4.2 Cost Budget Tracking & Enforcement

**Purpose:** Enforce spending limits to prevent runaway API costs for personal users.

**Budget Configuration:**
```json
{
  "cost_budgets": {
    "enabled": true,
    "soft_limit_usd": 100.00,
    "hard_limit_usd": 500.00,
    "period": "monthly",
    "auto_reset": true,
    "warn_at_percent": 80,
    "block_at_percent": 100,
    "allow_force_override": false,
    "tracking_file": "~/.aurora/budget_tracker.json"
  }
}
```

**Budget Tracking File Format** (`~/.aurora/budget_tracker.json`):
```json
{
  "period_start": "2025-12-01T00:00:00Z",
  "period_end": "2025-12-31T23:59:59Z",
  "limit_usd": 100.00,
  "consumed_usd": 18.50,
  "remaining_usd": 81.50,
  "query_count": 142,
  "last_updated": "2025-12-20T14:30:00Z"
}
```

**Pre-Query Cost Estimation** (in Guardrails Phase 0):
- **Formula:** `estimated_cost = base_cost × complexity_multiplier × (tokens / 1000)`
- **Base costs:**
  - SIMPLE: $0.001 (Haiku)
  - MEDIUM: $0.05 (Sonnet)
  - COMPLEX: $0.50 (Opus)
- **Complexity multiplier:** 1.0 (simple), 3.0 (medium), 5.0 (complex)
- **Token estimate:** Based on query length

**Budget Check Flow:**
```
GUARDRAILS (Phase 0)
    ↓
Cost Budget Pre-Check:
    1. Load current budget from tracking file
    2. Estimate query cost
    3. Calculate: current_usage + estimated_cost
    4. Check against limits:
       ↓
    Soft Limit (80%):
        → WARN user, show remaining budget
        → Allow query to proceed
       ↓
    Hard Limit (100%):
        → BLOCK query
        → Show budget status
        → Suggest: wait for reset or increase limit
       ↓
    [If passed] → Continue to COMPLEXITY ASSESSMENT
```

**User Actions:**

**Soft Limit Reached (80%):**
```
⚠️  Budget Warning: 80% consumed ($80.00 / $100.00)
Remaining: $20.00 (est. 40 queries)
Period ends: 2025-12-31

Proceed with query? [y/N]
```

**Hard Limit Reached (100%):**
```
🛑 Budget Limit Exceeded: $100.00 / $100.00
Query blocked to prevent overspending.

Options:
  1. Wait for monthly reset (2025-12-31)
  2. Increase budget limit: aurora config set cost_budgets.hard_limit_usd 200
  3. Force override (if enabled): aurora --force "query"

Current usage: 142 queries, $100.00 spent
```

**Budget Management Commands:**
```bash
# View current budget status
aurora budget status

# Reset budget manually
aurora budget reset

# Adjust limits
aurora config set cost_budgets.soft_limit_usd 200
aurora config set cost_budgets.hard_limit_usd 500

# View budget history
aurora budget history --month 2025-12
```

**Integration Points:**
- **Phase 0 (Guardrails):** Pre-query budget check
- **Post-query:** Update budget tracker with actual cost
- **Section 3.1:** Budget pre-check mentioned in Guardrails flow

**Why This Matters:**
- Personal users can't afford $500 surprise bills
- Prevents accidental infinite loops from consuming budget
- Forces conscious cost management
- Critical safety feature for production use

---

**Reporting Structure:**
```json
{
  "reporting": {
    "daily": {
      "enabled": true,
      "output_path": "~/.aurora/reports/daily/",
      "metrics": ["queries", "accuracy", "cache_hits", "errors"]
    },
    "cumulative": {
      "enabled": true,
      "output_path": "~/.aurora/reports/cumulative/",
      "metrics": ["total_queries", "learning_improvement", "pattern_growth"]
    },
    "monthly": {
      "enabled": true,
      "output_path": "~/.aurora/reports/monthly/",
      "metrics": ["trends", "cost_analysis", "accuracy_over_time"]
    }
  }
}
```

**CLI Commands for Reports:**
```bash
aurora report daily              # Today's report
aurora report daily --date 2025-12-11  # Specific day
aurora report cumulative         # All-time stats
aurora report monthly            # Current month
aurora report monthly --month 2025-11  # Specific month
```

### 9.5 Verbosity Control

| Level | Flag | Description |
|-------|------|-------------|
| QUIET | (default) | Minimal output: final result only |
| NORMAL | `-v` | Standard progress: stages and scores |
| VERBOSE | `-vv` | Detailed: all checks, activations, routing |
| JSON | `--json` | Machine-readable: full structured output |

**Examples:**
```
QUIET (default):
aurora: done (score: 0.85)

NORMAL (-v):
aurora: assessing complexity... COMPLEX (0.82)
aurora: decomposing... 3 subgoals
aurora: verifying (adversarial)... PASS (0.85)
aurora: routing to agents...
aurora: done (score: 0.85, cached: yes)

VERBOSE (-vv):
aurora: assessing complexity...
  keywords: [auth, feature, implement] → score: 0.7
  llm verification: COMPLEX (confidence: 0.82)
aurora: retrieving context (budget: 10)...
  reas: patterns: 2 (activation: 0.8, 0.6)
  code: chunks: 5 (auth.py:0.9, session.py:0.7, ...)
aurora: decomposing...
  subgoal 1: "Research OAuth providers" → research-agent
  subgoal 2: "Implement OAuth flow" → code-developer
  subgoal 3: "Write tests" → quality-assurance
aurora: verifying (adversarial)...
  completeness: 0.9
  consistency: 1.0
  groundedness: 0.8
  routability: 0.85
  overall: 0.85 → PASS
... (full trace)

JSON (--json):
{"stage":"assess","status":"complete","complexity":"complex","confidence":0.82}
{"stage":"retrieve","status":"complete","chunks":{"code":5,"reas":2}}
{"stage":"decompose","status":"complete","subgoals":3}
{"stage":"verify","status":"complete","score":0.85,"verdict":"pass"}
{"stage":"done","final_score":0.85,"cached":true}
```

### 9.6 MCP Server Integration

**Tool Definitions:**

| Tool | Input | Output |
|------|-------|--------|
| `aurora_assess` | query | complexity, confidence, route |
| `aurora_retrieve_context` | query, budget | relevant chunks (code + reasoning) |
| `aurora_decompose` | query, context | subgoals JSON |
| `aurora_verify` | decomposition or output | score, issues, verdict |
| `aurora_learn` | result, score | cached/not |

**Configuration:**
- Standard MCP settings file location
- Command-line arguments (--project, --verbosity)
- Environment variables (AURORA_LLM_PROVIDER, AURORA_API_KEY)

**Progress Notifications:**
- Stage (assess, decompose, verify, route, synthesize)
- Status (in_progress, complete, retry, failed)
- Detail (human-readable description)
- Progress (0.0-1.0 where applicable)
- Verbose data (scores, check details)

### 9.7 Conversation Logging

**Purpose**: Complete audit trail of all AURORA interactions, separate from ACT-R selective storage.

**Design Philosophy**:
- **ACT-R Storage**: Selective (only interactions meeting score thresholds ≥ 0.5) for learning/retrieval
- **Conversation Logs**: Complete append-only record of ALL interactions for audit, debugging, and traceability

**File Location**:
```
~/.aurora/logs/conversations/
  └── YYYY/
      └── MM/
          ├── keyword1-keyword2-YYYY-MM-DD.md
          ├── keyword1-keyword2-YYYY-MM-DD.md
          └── ...
```

**File Naming Convention**:
- **Format**: `{keyword1}-{keyword2}-YYYY-MM-DD.md`
- **Keywords**: Two most relevant keywords extracted from the user query (lowercase, hyphen-separated)
- **Date**: ISO date format (YYYY-MM-DD)
- **Directory Structure**: Organized by year and month for efficient browsing

**Keyword Extraction**:
- Extract 2 most semantically relevant nouns/verbs from user query
- Remove stop words ("the", "a", "an", "is", "are", etc.)
- Lowercase and normalize (replace spaces with hyphens)
- Fallback to "query-{number}" if extraction fails

**Examples**:
- Query: "Implement OAuth2 authentication for our API"
  → File: `oauth-authentication-2025-12-13.md`
- Query: "Fix database migration issue"
  → File: `database-migration-2025-12-13.md`
- Query: "Optimize React component rendering"
  → File: `react-rendering-2025-12-13.md`

**File Format**: Markdown with structured JSON blocks

**Log Structure**:

Each interaction is logged with:
1. **Header**: Timestamp, query ID, user query
2. **All 9 SOAR Phases**: Complete trace with JSON outputs
3. **User Interactions**: All agent ↔ user conversations during execution
4. **Final Response**: Natural language answer delivered to user
5. **Metadata**: Execution time, tokens used, cost, verification scores

**Example Log Entry**:

File: `~/.aurora/logs/conversations/2025/12/oauth-authentication-2025-12-13.md`

```markdown
---
## Query: 2025-12-13T14:32:15Z | ID: aurora-20251213-143215-abc123

**User Query**: "Implement OAuth2 authentication for our API"
**Keywords**: oauth, authentication

### Phase 1: ASSESS
```json
{
  "phase": "assess",
  "timestamp": "2025-12-13T14:32:15.123Z",
  "input": {
    "query": "Implement OAuth2 authentication for our API",
    "mode": "always_on"
  },
  "output": {
    "complexity": "complex",
    "confidence": 0.87,
    "reasoning": "Multi-step feature requiring security, token management, user flow",
    "route": "full_decomposition"
  },
  "duration_ms": 450
}
```

### Phase 2: RETRIEVE
```json
{
  "phase": "retrieve",
  "timestamp": "2025-12-13T14:32:15.573Z",
  "input": {
    "query": "Implement OAuth2 authentication for our API",
    "context_budget": 10
  },
  "output": {
    "chunks_retrieved": {
      "code": [
        {"id": "code:auth.py:123", "activation": 0.92, "content": "..."},
        {"id": "code:session.py:45", "activation": 0.78, "content": "..."}
      ],
      "reasoning": [
        {"id": "reas:oauth-pattern-67", "activation": 0.85, "content": "..."}
      ]
    },
    "total_chunks": 7
  },
  "duration_ms": 320
}
```

### Phase 3: DECOMPOSE
```json
{
  "phase": "decompose",
  "timestamp": "2025-12-13T14:32:15.893Z",
  "input": {
    "query": "Implement OAuth2 authentication for our API",
    "context": "{retrieved_chunks}"
  },
  "output": {
    "subgoals": [
      {"id": "SG1", "description": "Research OAuth2 providers (Auth0, Okta, Custom)", "agent": "research-agent"},
      {"id": "SG2", "description": "Design user model with OAuth fields", "agent": "code-developer"},
      {"id": "SG3", "description": "Implement token generation and validation", "agent": "code-developer"},
      {"id": "SG4", "description": "Write integration tests", "agent": "quality-assurance"}
    ]
  },
  "duration_ms": 2100
}
```

### Phase 4: VERIFY (Decomposition)
```json
{
  "phase": "verify_decomposition",
  "timestamp": "2025-12-13T14:32:17.993Z",
  "input": {
    "decomposition": "{subgoals_from_phase_3}",
    "verification_option": "option_b"
  },
  "output": {
    "scores": {
      "completeness": 0.90,
      "consistency": 0.95,
      "groundedness": 0.85,
      "routability": 0.90
    },
    "overall_score": 0.90,
    "verdict": "pass",
    "issues": []
  },
  "duration_ms": 1800
}
```

### Phase 5: ROUTE
```json
{
  "phase": "route",
  "timestamp": "2025-12-13T14:32:19.793Z",
  "input": {
    "subgoals": "{subgoals_from_phase_3}"
  },
  "output": {
    "routing": [
      {"subgoal_id": "SG1", "agent_id": "research-agent", "agent_type": "http", "endpoint": "https://api.example.com/agents/research"},
      {"subgoal_id": "SG2", "agent_id": "code-developer", "agent_type": "mcp", "path": "~/.claude/agents/code-developer"},
      {"subgoal_id": "SG3", "agent_id": "code-developer", "agent_type": "mcp", "path": "~/.claude/agents/code-developer"},
      {"subgoal_id": "SG4", "agent_id": "quality-assurance", "agent_type": "mcp", "path": "~/.claude/agents/quality-assurance"}
    ]
  },
  "duration_ms": 120
}
```

### Phase 6: COLLECT (Agent Outputs)

**Agent SG1: research-agent**
```json
{
  "subgoal_id": "SG1",
  "agent_id": "research-agent",
  "status": "success",
  "output": {
    "summary": "Auth0 recommended for $2000 budget. Setup: 1-2 days, includes social auth (saves 2 weeks dev time). Alternatives: Okta ($100/mo, enterprise features), Custom (free, 4 weeks dev time).",
    "data": {
      "providers": [
        {"name": "Auth0", "price_per_month": 25, "setup_time": "1-2 days", "features": ["social_auth", "mfa", "sso"]},
        {"name": "Okta", "price_per_month": 100, "setup_time": "1 week", "features": ["enterprise_sso", "scim", "advanced_mfa"]},
        {"name": "Custom", "price_per_month": 0, "setup_time": "4 weeks", "features": ["full_control", "custom_flows"]}
      ],
      "recommendation": "Auth0",
      "reasoning": "Best balance of cost, speed, and features for startup"
    },
    "confidence": 0.92
  },
  "user_interactions": [
    {
      "turn": 1,
      "agent_question": "What's your monthly budget for OAuth provider?",
      "user_response": "$2000/month",
      "timestamp": "2025-12-13T14:32:25.100Z"
    },
    {
      "turn": 2,
      "agent_question": "Timeline for launch?",
      "user_response": "Urgent - 2 weeks",
      "timestamp": "2025-12-13T14:32:45.300Z"
    }
  ],
  "metadata": {
    "tools_used": ["websearch", "mcp:reddit"],
    "duration_ms": 12500,
    "model_used": "claude-sonnet-4.5"
  },
  "timestamp": "2025-12-13T14:32:52.413Z"
}
```

**Agent SG2: code-developer** (User model design)
```json
{
  "subgoal_id": "SG2",
  "agent_id": "code-developer",
  "status": "success",
  "output": {
    "summary": "Created User model with OAuth fields: oauth_provider, oauth_id, access_token (encrypted), refresh_token (encrypted), token_expiry. Added migration and updated authentication middleware.",
    "data": {
      "files_modified": ["models/user.py", "migrations/0023_add_oauth_fields.py", "middleware/auth.py"],
      "schema_changes": {
        "table": "users",
        "added_columns": ["oauth_provider VARCHAR(50)", "oauth_id VARCHAR(255)", "access_token_encrypted TEXT", "refresh_token_encrypted TEXT", "token_expiry TIMESTAMP"]
      }
    },
    "confidence": 0.95
  },
  "user_interactions": [],
  "metadata": {
    "tools_used": ["read", "edit", "write"],
    "duration_ms": 8200,
    "model_used": "claude-sonnet-4.5"
  },
  "timestamp": "2025-12-13T14:33:00.613Z"
}
```

*(Agent SG3 and SG4 outputs would follow the same format)*

### Phase 7: SYNTHESIZE

**Synthesis (Natural Language Recomposition)**
```json
{
  "phase": "synthesize",
  "timestamp": "2025-12-13T14:33:25.100Z",
  "input": {
    "agent_summaries": [
      {"subgoal_id": "SG1", "summary": "Auth0 recommended for $2000 budget...", "confidence": 0.92},
      {"subgoal_id": "SG2", "summary": "Created User model with OAuth fields...", "confidence": 0.95},
      {"subgoal_id": "SG3", "summary": "Implemented token generation using PyJWT...", "confidence": 0.93},
      {"subgoal_id": "SG4", "summary": "Added 12 integration tests covering OAuth flow...", "confidence": 0.90}
    ]
  },
  "output": {
    "final_answer": "I've implemented OAuth2 authentication for your API using Auth0 as the provider. Based on your $2000/month budget and urgent 2-week timeline, Auth0 is the optimal choice—it costs only $25/month and setup takes 1-2 days, well within your constraints.\n\nHere's what was completed:\n\n1. **Provider Research**: Evaluated Auth0, Okta, and custom solutions. Auth0 provides social authentication out-of-the-box, saving approximately 2 weeks of development time.\n\n2. **Data Model**: Extended the User model with OAuth fields (provider, oauth_id, encrypted tokens, expiry). Created migration 0023_add_oauth_fields.py.\n\n3. **Token Management**: Implemented secure token generation and validation using PyJWT. Tokens are encrypted at rest and automatically refreshed before expiry.\n\n4. **Testing**: Added 12 integration tests covering the complete OAuth flow (login, token refresh, logout, error scenarios).\n\nAll tests are passing. The implementation is production-ready and follows OAuth2 security best practices.",
    "synthesis_metadata": {
      "subgoals_completed": 4,
      "total_files_modified": 8,
      "user_interactions_count": 2
    }
  },
  "duration_ms": 1500
}
```

### Phase 4b: VERIFY (Synthesis)
```json
{
  "phase": "verify_synthesis",
  "timestamp": "2025-12-13T14:33:26.600Z",
  "input": {
    "agent_summaries": "{from_phase_7_input}",
    "synthesis": "{final_answer_from_phase_7}"
  },
  "output": {
    "scores": {
      "addresses_query": 0.95,
      "traceable": 0.92,
      "consistent": 0.95,
      "calibrated": 0.90
    },
    "overall_score": 0.93,
    "verdict": "pass",
    "issues": []
  },
  "duration_ms": 1200
}
```

### Phase 8: RECORD
```json
{
  "phase": "record",
  "timestamp": "2025-12-13T14:33:27.800Z",
  "input": {
    "query": "Implement OAuth2 authentication for our API",
    "decomposition": "{subgoals}",
    "verification_score": 0.93,
    "complexity": "complex"
  },
  "output": {
    "stored_to_actr": true,
    "chunk_id": "reas:oauth-impl-20251213",
    "reasoning": "Score 0.93 >= threshold 0.5, stored for future retrieval"
  },
  "duration_ms": 85
}
```

### Phase 9: RESPOND
```json
{
  "phase": "respond",
  "timestamp": "2025-12-13T14:33:27.885Z",
  "output": {
    "format": "natural_language",
    "response": "{final_answer from synthesis}",
    "metadata": {
      "total_duration_ms": 12785,
      "tokens_used": {
        "reasoning_llm": 8450,
        "agents": 15200
      },
      "estimated_cost_usd": 0.0234,
      "cached_to_actr": true
    }
  }
}
```

### Execution Summary
- **Total Duration**: 12.8 seconds
- **Complexity**: COMPLEX (0.87 confidence)
- **Verification Scores**: Decomposition 0.90, Synthesis 0.93
- **Agent Interactions**: 4 subgoals, 2 user interactions
- **ACT-R Storage**: Yes (score ≥ 0.5)
- **Tokens Used**: 23,650 total
- **Estimated Cost**: $0.0234

---
```

**File Management**:
- **Individual files**: One file per SOAR interaction (allows multiple same-day interactions)
- **Directory structure**: Organized by year/month (`YYYY/MM/`)
- **Retention**: Configurable (default: 90 days)
- **Compression**: Auto-compress files older than 7 days (gzip)
- **Collision handling**: If keywords+date already exists, append `-{n}` counter

**Log Configuration** (`~/.aurora/config.json`):
```json
{
  "logging": {
    "conversations": {
      "enabled": true,
      "path": "~/.aurora/logs/conversations/",
      "format": "markdown",
      "file_naming": {
        "strategy": "keyword-date",
        "keyword_count": 2,
        "fallback_prefix": "query"
      },
      "retention_days": 90,
      "compress_after_days": 7,
      "include_phases": ["assess", "retrieve", "decompose", "verify", "route", "collect", "synthesize", "record", "respond"],
      "include_user_interactions": true,
      "include_metadata": true
    }
  }
}
```

**CLI Commands**:
```bash
# List today's conversations
aurora logs today

# List conversations for specific date
aurora logs --date 2025-12-13

# List conversations for specific month
aurora logs --month 2025-12

# Search logs by keyword
aurora logs search "oauth"
aurora logs search "authentication"

# Search within specific date range
aurora logs search "database" --from 2025-12-01 --to 2025-12-13

# View specific conversation file
aurora logs view oauth-authentication-2025-12-13

# Export conversation by ID
aurora logs export aurora-20251213-143215-abc123

# List all conversations in year/month
aurora logs list 2025/12
```

**Use Cases**:
1. **Debugging**: Trace exact flow of failed interactions
2. **Auditing**: Compliance and security review of all interactions
3. **Learning**: Analyze patterns in successful vs. failed queries
4. **Optimization**: Identify bottlenecks in agent execution
5. **User Support**: Reproduce user issues from conversation ID

**Separation from ACT-R**:
- **ACT-R (SQLite)**: Selective storage (score ≥ 0.5), optimized for retrieval, pattern matching
- **Conversation Logs (Markdown)**: Complete audit trail, human-readable, append-only, all interactions

---

### 9.8 Headless Mode

**Purpose:** Run AURORA in autonomous loop with human out of the loop for focused, goal-driven experiments.

**Use Cases:**
1. **Autonomous validation experiments** - Verify system behavior, test pipelines, validate assumptions
2. **Continuous testing/monitoring** - Run repeated experiments, gather data, test edge cases

**Directory Structure:**
```
./headless/
  ├── prompt.md        # Goal definition and constraints
  └── scratchpad.md    # Agent memory between iterations (read/write)
```

**CLI Command:**
```bash
aurora --headless \
  --prompt=./headless/prompt.md \
  --scratchpad=./headless/scratchpad.md \
  --max-iterations=10 \
  --budget-limit=5.00
```

**Flags:**
- `--headless` - Enable headless mode (human out of the loop)
- `--prompt` - Path to prompt.md (goal definition, default: `./headless/prompt.md`)
- `--scratchpad` - Path to scratchpad.md (agent memory, default: `./headless/scratchpad.md`)
- `--max-iterations` - Hard limit on iterations (default: 10)
- `--budget-limit` - Max cost in USD (default: from config or unlimited)

**Termination Criteria** (either stops loop):
1. **Goal Completion** - Agent writes `GOAL_ACHIEVED: [reason]` to scratchpad.md
2. **Max Iterations** - Configured limit reached

**Safety Constraints:**

**1. Git Branch Isolation**
- AURORA enforces: If current branch is "main" or "master" → reject headless mode
- Error message: "Headless mode requires 'headless' branch. Run: git checkout -b headless"
- prompt.md MUST include safety rules:
  ```markdown
  # Safety Rules (in prompt.md)

  1. CREATE AND USE HEADLESS BRANCH:
     - git checkout -b headless (if not exists)
     - ALL work happens on "headless" branch ONLY

  2. ALLOWED OPERATIONS:
     - Read any file in repository
     - Edit/create files on headless branch
     - git add, git commit (on headless branch only)

  3. FORBIDDEN OPERATIONS:
     - NO git merge (keep headless isolated)
     - NO git push (keep experiment local)
     - NO git checkout main (stay on headless)
     - NO rm -rf or destructive commands

  4. GOAL FOCUS:
     - ONE measurable, achievable goal per experiment
     - Write progress to scratchpad.md after each iteration
  ```

**2. Read-Only Main Branch**
- On "main" or "master" branch: headless mode blocked
- On "headless" branch: agent can edit, add, commit freely
- All changes stay isolated (no merge, no push)
- Easy to discard: `git checkout main && git branch -D headless`

**3. Cost Budget Per Experiment**
- prompt.md can specify: `BUDGET_LIMIT: $5.00`
- AURORA tracks cumulative cost in scratchpad.md
- Stops if budget exceeded (writes `BUDGET_EXCEEDED` to scratchpad)

**Headless Flow:**
```
START HEADLESS LOOP (iteration = 1)
    ↓
Read prompt.md (goal definition)
Read scratchpad.md (previous iteration memory)
    ↓
USER QUERY (from prompt.md + scratchpad context)
    ↓
[Normal AURORA flow: GUARDRAILS → ASSESS → DECOMPOSE → VERIFY → AGENTS → SYNTHESIZE]
    ↓
Write results to scratchpad.md (append iteration log)
    ↓
Check termination:
  - Goal achieved? (LLM evaluates goal from prompt.md)
  - Max iterations reached?
  - Budget exceeded?
    ↓
If NOT terminated:
  → INCREMENT iteration
  → LOOP BACK to start
    ↓
If TERMINATED:
  → Write final status to scratchpad.md
  → EXIT with code 0 (success) or 1 (failure/timeout)
```

**Scratchpad Format:**
```markdown
# Headless Experiment Scratchpad

**Experiment:** [Brief description from prompt.md]
**Started:** 2025-12-20 14:30:00
**Current Iteration:** 3 / 10
**Cost So Far:** $0.45 / $5.00

---

## Iteration 1 (14:30:00)
**Action:** Created test file test_aurora.py
**Observation:** File created successfully
**Next Step:** Run tests to verify behavior

## Iteration 2 (14:31:15)
**Action:** Ran pytest tests/
**Observation:** 329/329 tests passing
**Next Step:** Check if goal is met

## Iteration 3 (14:32:30)
**Action:** Verified all tests pass, checked output matches expected
**Observation:** Goal criteria satisfied (all tests pass, output correct)
**Decision:** GOAL_ACHIEVED: All tests passing, validation complete

---

**STATUS:** GOAL_ACHIEVED
**Reason:** Successfully validated that all 329 tests pass with correct output
**Total Cost:** $0.45
**Total Iterations:** 3
```

**Configuration:**
```json
{
  "headless": {
    "enabled": true,
    "default_max_iterations": 10,
    "default_budget_limit_usd": 5.00,
    "required_branch": "headless",
    "enforce_branch_check": true,
    "prompt_file": "./headless/prompt.md",
    "scratchpad_file": "./headless/scratchpad.md",
    "goal_achievement_signal": "GOAL_ACHIEVED",
    "budget_exceeded_signal": "BUDGET_EXCEEDED"
  }
}
```

**External Loop Pattern** (for continuous runs):
```bash
# Continuous loop until goal achieved
while :; do
  aurora --headless --prompt=./headless/prompt.md --scratchpad=./headless/scratchpad.md
  # Check exit code or scratchpad for completion signal
  if grep -q "GOAL_ACHIEVED" ./headless/scratchpad.md; then break; fi
done
```

**Why Needed:**
- Autonomous validation without human supervision
- Focused experiments on single measurable goals
- Testing workflows repeatedly (e.g., nightly validation)
- Personal users can run experiments safely (branch isolation, budget limits)

---

### 9.9 Memory Commands & Integration Modes

**Purpose:** Two modes for accessing AURORA memory within Claude Code - auto-escalation and explicit recall.

**Mode 1: Smart Auto-Escalation (Default Behavior)**

All queries to Claude Code go through lightweight assessment:
- **SIMPLE queries (90%):** Direct LLM + passive memory retrieval (~$0.01-0.05)
- **COMPLEX queries (10%):** Auto-escalate to full AURORA (~$0.10-0.50)

**Passive Memory Retrieval:**
- Memory always available (in-process, not daemon)
- SQLite database loaded on-demand
- Top-K chunks boost context automatically
- No orchestration, no verification (simple queries only)

**User Experience:**
```bash
# User just types query to Claude Code (normal behavior)
claude "how do I implement authentication?"

# If simple: Direct LLM + memory boost
# If complex: Auto-escalate to full AURORA
# User doesn't need to think about it
```

**Mode 2: Intentional Memory Recall (Explicit Command)**

**New Command: `aur mem "search query"`**

```bash
# Search reasoning patterns
aur mem "how did we solve authentication bugs?"

# Search code patterns
aur mem "functions related to user login"

# Search domain knowledge
aur mem "AWS Polly configuration patterns"

# Short form
aur m "search query"
```

**What `aur mem` Does:**
1. Query ACT-R memory directly (no orchestration)
2. Semantic search + activation ranking
3. Return top-K chunks with context
4. Read-only (no learning, no memory updates)

**Output Format:**
```
Memory Search Results for: "authentication bugs"

Found 5 relevant patterns (sorted by activation):

1. [Reasoning Pattern] ID: reas:auth-token-expiry-2024-11
   Activation: 0.89 | Last used: 2 days ago
   Context: "Fixed token expiry bug by checking refresh window"
   Decomposition: [subgoal 1: verify token age, subgoal 2: refresh if needed]

2. [Code Chunk] ID: code:src/auth/token_manager.py:validate_token
   Activation: 0.78 | Last modified: 5 days ago
   Function: validate_token(token: str) -> bool
   Context: Token validation with expiry check

3. [Reasoning Pattern] ID: reas:auth-session-timeout-2024-10
   Activation: 0.65 | Last used: 3 weeks ago
   Context: "Session timeout causing logout loop"
   Solution: Adjusted session TTL in config
```

**Memory Update Strategy (Lazy Updates for MVP):**

Memory gets updated ONLY during full AURORA runs:
- **Success (score ≥ 0.8):** Cache reasoning pattern, boost activation
- **Failure (score < 0.5):** Decay activation, mark as difficult
- **NOT updated on:** Simple queries, memory-only searches, file saves

**Why lazy updates work:**
- Personal users don't generate 1000s of queries/hour
- Memory updates naturally during complex problem-solving
- Good enough for MVP, can add real-time updates later (daemon mode in Phase 2)

**Architecture: In-Process Memory (Not Daemon)**

```
┌─────────────────────────────────────────────────────┐
│                  CLAUDE CODE PROCESS                 │
├─────────────────────────────────────────────────────┤
│                                                      │
│  User Query                                          │
│      ↓                                               │
│  ┌────────────────────────────────────┐             │
│  │  Lightweight Assessment            │             │
│  │  (decide: simple or complex?)      │             │
│  └────────────────────────────────────┘             │
│      ↓                    ↓                          │
│  [SIMPLE]            [COMPLEX]                       │
│      ↓                    ↓                          │
│  ┌─────────────┐    ┌──────────────────┐            │
│  │ Direct LLM  │    │ Full AURORA      │            │
│  │     +       │    │ Orchestration    │            │
│  │ ACT-R Load  │    │     +            │            │
│  │ (on-demand) │    │ Learning Loop    │            │
│  └─────────────┘    └──────────────────┘            │
│      ↓                    ↓                          │
│      └────────────────────┘                          │
│              ↓                                       │
│  ┌────────────────────────────────────┐             │
│  │     ACT-R Memory (SQLite)          │             │
│  │  - reasoning patterns               │             │
│  │  - code chunks                      │             │
│  │  - domain knowledge                 │             │
│  │  - activation values                │             │
│  └────────────────────────────────────┘             │
│                                                      │
└─────────────────────────────────────────────────────┘
```

**Key Points:**
- No separate daemon process (simpler for MVP)
- Memory loaded on-demand (fast enough for personal use)
- Updates happen in-process during AURORA runs
- Can upgrade to daemon later if needed (Phase 2)

**Configuration:**
```json
{
  "memory_modes": {
    "auto_escalation": {
      "enabled": true,
      "assessment_threshold": {
        "simple": ["single_step", "factual", "lookup"],
        "complex": ["multi_step", "reasoning", "planning"]
      },
      "passive_retrieval": {
        "enabled": true,
        "max_chunks": 10,
        "activation_threshold": 0.5
      }
    },
    "explicit_recall": {
      "enabled": true,
      "command": "aur mem",
      "short_command": "aur m",
      "max_results": 10,
      "include_context": true,
      "show_activation_scores": true
    },
    "memory_updates": {
      "strategy": "lazy",
      "update_on_aurora_run": true,
      "update_on_simple_query": false,
      "update_on_file_save": false
    }
  }
}
```

**Why This Approach:**
- Memory always available (valuable!)
- Auto-invocation (smart!)
- Explicit search when needed (intentional!)
- No daemon complexity for MVP (simple!)
- Can upgrade to daemon later (future-proof!)

---

## 10. SUCCESS METRICS

### 10.1 Primary Metrics

| Metric | Definition | Target | Measurement |
|--------|------------|--------|-------------|
| **Reasoning Accuracy** | Correct answers on verifiable benchmark | >= 80% | Benchmark suite with known answers |
| **Verification Catch Rate** | Errors caught by verification | >= 70% | Inject known-bad decompositions |
| **Score Calibration** | Correlation between score and correctness | >= 0.7 | Compare scores to actual correctness |
| **Code Retrieval Precision** | Relevant chunks / retrieved chunks | >= 85% | Ground truth from successful generations |
| **Token Efficiency** | Tokens used vs. embedding-only baseline | 40% reduction | Track average tokens per query |

### 10.2 Secondary Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| **Learning Improvement** | Accuracy increase over sessions | >= 5% over 20 sessions |
| **Cache Hit Rate** | Queries using cached patterns | >= 30% after 1000 queries |
| **Retry Rate** | Decompositions needing retry | <= 20% |
| **Agent Utilization** | Subgoals successfully routed | >= 90% |
| **Latency (Simple)** | End-to-end response time | < 2 seconds |
| **Latency (Complex)** | End-to-end response time | < 10 seconds |

### 10.3 Operational Metrics

| Metric | Target |
|--------|--------|
| **Cost per Complex Query** | <= 3x baseline LLM-only |
| **Memory Usage** | <= 100MB for 100k chunks |
| **Startup Time** | < 5 seconds |
| **Error Rate** | < 1% with graceful degradation |

---

## 11. APPENDICES

### Appendix A: Phase Roadmap

**Phase 1: MVP (Weeks 1-4)**
- Core activation engine (using pyactr for formulas)
- SQLite + JSON storage
- Reasoning pipeline with Options A + B
- Code context provider (cAST + Git)
- Reasoning context provider
- MCP server
- Basic CLI
- Logging and metrics collection

**Phase 2: Deep Reasoning + Knowledge (Weeks 5-8)**
- Option C deep reasoning (multi-path + debate)
- Knowledge context provider (APIs, schemas, conventions)
- Cross-context spreading activation (between code and reasoning)
- Production monitoring/telemetry
- Advanced reporting

**Phase 3: Personalization + Scale (Weeks 9-12)**
- Per-developer profiles
- Transfer learning across codebases
- Additional language support (Java, Rust, C++)
- IDE integration
- Web interface (optional)

### Appendix B: Non-Goals

**MVP Non-Goals:**
1. Option C Deep Reasoning - Phase 2
2. KnowledgeContextProvider - Phase 2
3. Cross-context spreading activation - Phase 2
4. Replay HER advanced learning - Phase 2
5. Per-developer profiles - Phase 3
6. Transfer learning across codebases - Phase 3
7. Languages beyond Python/JavaScript/Go - Phase 3
8. Production monitoring/telemetry - Phase 2
9. IDE integration - Phase 3
10. Web interface - CLI/MCP only in MVP

**Permanent Non-Goals:**
1. Agent implementation (AURORA routes to agents; does not build them)
2. Fine-tuning or custom model training (uses LLM APIs as-is)
3. Real-time collaboration (single-user orientation)
4. Scheduled task execution (on-demand queries only)
5. Document ingestion pipeline (knowledge comes from code/agents, not uploaded docs)

### Appendix C: Configuration File (~/. aurora/config.json)

**Default Configuration**:
```json
{
  "version": "1.0",
  "llm": {
    "mode": "standalone",
    "reasoning_llm": {
      "provider": "anthropic",
      "model": "claude-sonnet-4.5",
      "base_url": "https://api.anthropic.com/v1",
      "api_key_env": "ANTHROPIC_API_KEY",
      "max_tokens": 4096,
      "temperature": 0.0,
      "timeout_seconds": 30,
      "headers": {},
      "purpose": "Decomposition, verification, scoring - requires JSON precision"
    },
    "solving_llm": {
      "provider": "anthropic",
      "model": "claude-sonnet-4.5",
      "base_url": "https://api.anthropic.com/v1",
      "api_key_env": "ANTHROPIC_API_KEY",
      "max_tokens": 8192,
      "temperature": 0.7,
      "timeout_seconds": 60,
      "headers": {},
      "purpose": "Agent execution - requires creativity and problem-solving"
    }
  },
  "aurora": {
    "user_invoked": true,
    "always_on": false,
    "prefix": ["aur", "aurora:", "/aurora"],
    "exclude_patterns": ["thanks", "yes", "no", "ok", "got it", "thank you"]
  },
  "scoring": {
    "cache_threshold": 0.8,
    "pass_threshold": 0.7,
    "retry_threshold": 0.5,
    "max_retries": 2,
    "weighted_scoring": {
      "decomposition": {
        "completeness": 0.4,
        "consistency": 0.2,
        "groundedness": 0.2,
        "routability": 0.2
      },
      "agent_output": {
        "relevance": 0.4,
        "completeness": 0.3,
        "groundedness": 0.3
      },
      "synthesis": {
        "addresses_query": 0.3,
        "traceable": 0.3,
        "consistent": 0.2,
        "calibrated": 0.2
      }
    },
    "calibration_examples": {
      "mode": "builtin",
      "external_path": null,
      "merge_strategy": "replace",
      "scale_by_complexity": true,
      "counts": {
        "simple": 0,
        "medium": 2,
        "complex": 4,
        "critical": 6
      },
      "example_max_tokens": 200,
      "focus_on_edge_cases": true
    }
  },
  "complexity": {
    "keyword_classifier": {
      "enabled": true,
      "simple_keywords": ["what is", "list", "show", "define", "tell me"],
      "medium_keywords": ["compare", "explain", "analyze", "how does"],
      "complex_keywords": ["design", "architect", "strategy", "optimize", "implement"],
      "critical_keywords": ["critical", "production", "safety", "security", "mission-critical"],
      "borderline_llm_verify": true,
      "borderline_range": [0.4, 0.6]
    },
    "routing": {
      "simple": {"verification": "none", "cost_multiplier": 1.0},
      "medium": {"verification": "option_a", "cost_multiplier": 3.0},
      "complex": {"verification": "option_b", "cost_multiplier": 5.0},
      "critical": {"verification": "option_c", "cost_multiplier": 8.0}
    }
  },
  "agents": {
    "auto_discover": true,
    "discovery_paths": [
      "./.aurora/agents.json",
      "./.claude/agents",
      "./agents",
      "./droids",
      "./agent",
      "~/.aurora/agents.json",
      "~/.claude/agents",
      "~/.config/amp/agents",
      "~/.factory/droids",
      "~/.config/opencode/agent"
    ],
    "last_discovered_path": null,
    "refresh_interval_days": 15,
    "check_file_modified": true,
    "refresh_on_startup": false,
    "fallback_mode": "llm_only",
    "prompt_for_path_if_missing": true
  },
  "signals": {
    "positive": ["thanks", "great", "perfect", "excellent", "good"],
    "followup": ["also", "additionally", "and", "furthermore"],
    "negative": ["wrong", "no", "incorrect", "not what I meant"],
    "recourse": ["try again", "different approach", "retry"],
    "abort": ["never mind", "skip", "cancel", "stop"]
  },
  "memory": {
    "database_path": "~/.aurora/memory.db",
    "activation": {
      "decay_rate": 0.5,
      "spread_factor": 0.7,
      "max_spread_hops": 3,
      "context_boost_max": 0.5,
      "retrieval_threshold": 0.5
    },
    "learning": {
      "success_boost": 0.2,
      "partial_boost": 0.05,
      "neutral": 0.0,
      "failure_penalty": -0.1
    },
    "caching_policy": {
      "cache_if_score_gte": 0.5,
      "mark_as_pattern_if_gte": 0.8,
      "include_confidence_flag": true
    },
    "lifespan_policies": {
      "enabled": true,
      "default_policy": "usage_based",
      "policies": {
        "patterns": {
          "condition": "is_pattern == true AND success_score >= 0.8",
          "lifespan": "indefinite",
          "decay_mechanism": "logarithmic",
          "description": "Proven patterns retained forever with slow decay"
        },
        "security_critical": {
          "condition": "contains_tag('security') OR domain == 'security'",
          "lifespan": "365_days",
          "decay_mechanism": "none",
          "description": "Security-related chunks retain full activation for 1 year"
        },
        "high_usage": {
          "condition": "access_count > 10",
          "lifespan": "indefinite",
          "escalation_action": "candidate_for_fine_tuning",
          "description": "Frequently-used patterns marked for escalation to fine-tuning"
        },
        "inactive": {
          "condition": "last_accessed_days > 90 AND access_count <= 2",
          "lifespan": "decay",
          "decay_mechanism": "exponential",
          "description": "Inactive, low-usage chunks decay quickly"
        },
        "default": {
          "condition": "score >= 0.5",
          "lifespan": "180_days",
          "decay_mechanism": "logarithmic",
          "description": "Default: retain successful chunks for 180 days"
        }
      }
    }
  },
  "logging": {
    "level": "INFO",
    "outputs": ["console", "file"],
    "log_path": "~/.aurora/logs/",
    "rotation": {
      "max_size_mb": 100,
      "max_files": 10
    }
  },
  "reporting": {
    "daily": {"enabled": true, "output_path": "~/.aurora/reports/daily/"},
    "cumulative": {"enabled": true, "output_path": "~/.aurora/reports/cumulative/"},
    "monthly": {"enabled": true, "output_path": "~/.aurora/reports/monthly/"}
  }
}
```

**Dual-LLM Configuration (Phase 2 Cost Optimization)**:
```json
{
  "llm": {
    "mode": "standalone",
    "reasoning_llm": {
      "provider": "anthropic",
      "model": "claude-haiku-4.0",
      "base_url": "https://api.anthropic.com/v1",
      "api_key_env": "ANTHROPIC_API_KEY",
      "max_tokens": 4096,
      "temperature": 0.0,
      "timeout_seconds": 20,
      "purpose": "Fast, cheap reasoning/scoring (80% of calls)"
    },
    "solving_llm": {
      "provider": "anthropic",
      "model": "claude-opus-4.5",
      "base_url": "https://api.anthropic.com/v1",
      "api_key_env": "ANTHROPIC_API_KEY",
      "max_tokens": 8192,
      "temperature": 0.7,
      "timeout_seconds": 90,
      "purpose": "Expensive, high-quality problem solving (20% of calls)"
    }
  }
}
```

**Multi-Provider Example** (OpenAI + Anthropic):
```json
{
  "llm": {
    "mode": "standalone",
    "reasoning_llm": {
      "provider": "openai",
      "model": "gpt-4-turbo",
      "base_url": "https://api.openai.com/v1",
      "api_key_env": "OPENAI_API_KEY"
    },
    "solving_llm": {
      "provider": "anthropic",
      "model": "claude-opus-4.5",
      "base_url": "https://api.anthropic.com/v1",
      "api_key_env": "ANTHROPIC_API_KEY"
    }
  }
}
```

**Custom Endpoint Example** (Ollama local):
```json
{
  "llm": {
    "mode": "standalone",
    "reasoning_llm": {
      "provider": "ollama",
      "model": "llama3:70b",
      "base_url": "http://localhost:11434/v1",
      "api_key_env": null,
      "headers": {"Authorization": "Bearer optional-token"}
    }
  }
}
```

**Configuration Override Order**:
1. Default config (embedded in code)
2. `~/.aurora/config.json` (global user config)
3. `<project>/.aurora/config.json` (project-specific)
4. Environment variables (`AURORA_*`)
5. Command-line flags (`--config`, `--llm-provider`, etc.)

### Appendix C.1: Calibration Examples Override (Few-Shot JSON)

**Purpose**: Users can override the built-in calibration examples with custom few-shot examples for verification prompts.

**Configuration**:
```json
"scoring": {
  "calibration_examples": {
    "mode": "builtin",
    "external_path": null,
    "merge_strategy": "replace",
    "scale_by_complexity": true,
    "counts": {
      "simple": 0,
      "medium": 2,
      "complex": 4,
      "critical": 6
    }
  }
}
```

**Override User's Few-Shot Examples**:

Set `external_path` to a custom JSON file:
```json
"calibration_examples": {
  "mode": "builtin",
  "external_path": "~/.aurora/custom_examples.json",
  "merge_strategy": "replace"
}
```

Or in project-specific config:
```json
"calibration_examples": {
  "mode": "builtin",
  "external_path": "./.aurora/calibration_examples.json",
  "merge_strategy": "merge"
}
```

**External Few-Shot JSON Format** (`~/.aurora/custom_examples.json`):

```json
{
  "decomposition_verification": [
    {
      "complexity": "medium",
      "query": "Build a caching layer for our API",
      "decomposition": {
        "subgoals": [
          {"id": "SG1", "description": "Design cache architecture (Redis vs in-memory)"},
          {"id": "SG2", "description": "Implement cache invalidation strategy"},
          {"id": "SG3", "description": "Add monitoring and metrics"}
        ]
      },
      "expected_scores": {
        "completeness": 0.85,
        "consistency": 0.90,
        "groundedness": 0.80,
        "routability": 0.85
      },
      "overall_score": 0.85,
      "why": "Covers main concerns but misses error handling and performance tuning."
    }
  ],
  "agent_output_verification": [
    {
      "subgoal": {"id": "SG1", "description": "Research Redis alternatives"},
      "agent_response": {
        "summary": "Redis best for speed, Memcached for distributed caching, in-memory for simplicity.",
        "data": {
          "options": [
            {"name": "Redis", "latency": "< 1ms", "scaling": "horizontal"},
            {"name": "Memcached", "latency": "< 5ms", "scaling": "distributed"}
          ]
        },
        "confidence": 0.88
      },
      "expected_scores": {
        "relevance": 0.88,
        "completeness": 0.80,
        "groundedness": 0.85
      },
      "overall_score": 0.84
    }
  ],
  "synthesis_verification": [
    {
      "agent_summaries": [
        {"subgoal_id": "SG1", "summary": "Redis recommended for performance", "confidence": 0.88},
        {"subgoal_id": "SG2", "summary": "TTL-based invalidation for simplicity", "confidence": 0.80},
        {"subgoal_id": "SG3", "summary": "Prometheus metrics for monitoring", "confidence": 0.85}
      ],
      "synthesis": "Implement Redis caching with TTL-based invalidation. Use Prometheus for monitoring cache hit rates and latency. This approach balances performance with operational simplicity.",
      "expected_scores": {
        "addresses_query": 0.88,
        "traceable": 0.85,
        "consistent": 0.90,
        "calibrated": 0.87
      },
      "overall_score": 0.88
    }
  ]
}
```

**Configuration Options**:

| Option | Value | Description |
|--------|-------|-------------|
| `mode` | `"builtin"` | Use built-in examples (default) |
| `external_path` | `null` | No external file (use builtin) |
| `external_path` | `"path/to/file.json"` | Load examples from custom JSON file |
| `merge_strategy` | `"replace"` | Replace all builtin examples with external (default) |
| `merge_strategy` | `"merge"` | Merge external with builtin (external takes precedence) |
| `scale_by_complexity` | `true` | Scale examples by complexity: simple=0, medium=2, complex=4, critical=6 |
| `scale_by_complexity` | `false` | Use all examples regardless of complexity |
| `counts` | `{...}` | Override example counts per complexity level |

**Example Use Cases**:

1. **Domain-Specific Examples**:
   - User is building a fintech system → use finance-specific few-shot examples
   - Set: `external_path: "~/.aurora/fintech_examples.json"`

2. **Different Verification Strategy**:
   - Default examples focus on correctness
   - User wants examples that focus on edge cases
   - Set: `focus_on_edge_cases: true`

3. **Multi-Team Config**:
   - Team A uses builtin examples
   - Team B uses custom examples
   - Each team has their own `<project>/.aurora/config.json`

**Loading Order**:
1. Load builtin examples from code
2. If `external_path` is set and file exists:
   - Load external JSON
   - Apply `merge_strategy` (replace or merge)
3. If `scale_by_complexity: true`:
   - Scale to complexity-appropriate counts (simple=0, medium=2, complex=4, critical=6)
4. Use final examples in verification prompts

**Error Handling**:
- If external file not found: warn and fall back to builtin
- If external file malformed JSON: error and fail to start
- If external examples missing required fields: validate and warn

### Appendix C.2: Lifespan Policies Configuration

**Purpose**: Define retention rules for chunks in ACT-R memory. Policies determine how long chunks are retained and at what activation level.

**Storage Location**: `memory.lifespan_policies` in config.json (global) or project-specific config

**Configuration Structure**:
```json
{
  "memory": {
    "lifespan_policies": {
      "enabled": true,
      "default_policy": "usage_based",
      "policies": {
        "policy_name": {
          "condition": "chunk_property == value",
          "lifespan": "indefinite | N_days | decay",
          "decay_mechanism": "logarithmic | exponential | none",
          "escalation_action": "candidate_for_fine_tuning (optional)",
          "description": "Human-readable description"
        }
      }
    }
  }
}
```

**Policy Configuration Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | boolean | Enable/disable lifespan policy evaluation (default: true) |
| `default_policy` | string | Default policy name if no conditions match |
| `policies` | object | Named policy definitions |
| `condition` | string | Logical condition to trigger this policy |
| `lifespan` | string | Retention: `indefinite`, `N_days`, or `decay` |
| `decay_mechanism` | string | Rate: `logarithmic` (slow), `exponential` (fast), `none` |
| `escalation_action` | string | Optional action (e.g., `candidate_for_fine_tuning`) |
| `description` | string | Explanation of policy |

**Default Policies** (built-in):
1. **patterns**: Retain indefinitely, patterns only
2. **security_critical**: Retain 365 days, no decay, security domain
3. **high_usage**: Retain indefinitely + escalation flag
4. **inactive**: Exponential decay, unused chunks
5. **default**: Retain 180 days, all others

**Override Example** (project-specific):

Global config (`~/.aurora/config.json`):
```json
{
  "memory": {
    "lifespan_policies": {
      "enabled": true,
      "default_policy": "default",
      "policies": {
        "default": {
          "condition": "score >= 0.5",
          "lifespan": "180_days",
          "decay_mechanism": "logarithmic"
        }
      }
    }
  }
}
```

Project-specific override (`./<project>/.aurora/config.json`):
```json
{
  "memory": {
    "lifespan_policies": {
      "enabled": true,
      "default_policy": "default",
      "policies": {
        "fintech_critical": {
          "condition": "domain == 'fintech' OR contains_tag('security')",
          "lifespan": "730_days",
          "decay_mechanism": "none",
          "description": "Financial systems: retain for 2 years with no decay"
        },
        "default": {
          "condition": "score >= 0.5",
          "lifespan": "90_days",
          "decay_mechanism": "exponential",
          "description": "Project: aggressive cleanup"
        }
      }
    }
  }
}
```

**When Policies Are Evaluated**:
1. **Phase 8 (RECORD)**: Store chunk + set lifespan
2. **Activation Calculation**: Apply decay based on policy
3. **Periodic Maintenance**: Archive chunks past lifespan
4. **Phase 2 Retrieval**: Deprioritize decayed chunks

**Configuration Override Order**:
1. Built-in defaults (code)
2. `~/.aurora/config.json` (global)
3. `<project>/.aurora/config.json` (project-specific)
4. Environment: `AURORA_LIFESPAN_POLICIES=path`
5. CLI: `--lifespan-policies`

**Key Points**:
- ✅ **Changeable at runtime**: Edit config.json, restart Aurora
- ✅ **Granular**: Different rules per domain/type
- ✅ **Transparent**: Human-readable JSON
- ✅ **Queryable**: Check `governance.lifespan_policy` on any chunk
- ✅ **Auditable**: Stored in logs and metadata

### Appendix D: Feedback Handling Matrix

**Complete Decision Tree for All Checkpoints**:

**IMPORTANT:** This matrix defines **TWO INDEPENDENT RETRY LOOPS**:

- **LOOP 1: Decomposition Self-Correction** (Checkpoint 1)
  - Retries DECOMPOSITION when verification score is 0.5-0.7
  - Has its own `decomposition_retry_count` (max 2)
  - Loop back: VERIFY (Step 3) → DECOMPOSE (Step 2)

- **LOOP 2: Agent Execution Self-Correction** (Checkpoint 2)
  - Retries AGENT EXECUTION when output verification score is 0.5-0.7
  - Has its own `agent_retry_count` (max 2)
  - Loop back: VERIFY OUTPUTS (Step 5) → ROUTE TO AGENTS (Step 4)

**These loops are INDEPENDENT:**
- Each maintains its own retry counter (not shared)
- Each has its own feedback mechanism
- Each has different failure modes
- Both can trigger in the same query

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

**Learning from Scores**:

```
┌─────────────────────────────────────────────────────────────────────┐
│                LEARNING FROM SCORES                                  │
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

### Appendix E: Query Signal Detection

**Implicit Signal Handling**:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    QUERY SIGNAL DETECTION                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  POSITIVE SIGNALS ("thanks", "great", "perfect")                    │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Action: Log user satisfaction                               │    │
│  │ Learning: Boost pattern confidence +0.1                      │    │
│  │ Response: Acknowledge and offer follow-up                    │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  FOLLOW-UP SIGNALS ("also", "additionally", "and")                  │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Action: Maintain current context                            │    │
│  │ Learning: Don't re-assess complexity (continue session)      │    │
│  │ Routing: Append to current decomposition if compatible       │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  NEGATIVE SIGNALS ("wrong", "no", "not what I meant")               │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Action: Trigger re-decomposition from scratch               │    │
│  │ Learning: Mark current pattern as incorrect                  │    │
│  │ Ask: "What did I misunderstand? Can you clarify?"           │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  RECOURSE SIGNALS ("try again", "different approach")               │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Action: Escalate to next verification level                 │    │
│  │ Learning: Mark approach as insufficient                      │    │
│  │ Example: MEDIUM (Option A) → COMPLEX (Option B)             │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ABORT SIGNALS ("never mind", "skip", "cancel")                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Action: Gracefully exit current flow                        │    │
│  │ Learning: No penalties (user changed mind)                   │    │
│  │ Cleanup: Save partial state for potential resume            │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Configuration**:
```json
{
  "signals": {
    "enabled": true,
    "confidence_threshold": 0.8,
    "patterns": {
      "positive": {
        "keywords": ["thanks", "great", "perfect", "excellent", "good", "awesome"],
        "action": "boost_confidence",
        "boost_amount": 0.1
      },
      "followup": {
        "keywords": ["also", "additionally", "and", "furthermore", "plus"],
        "action": "maintain_context",
        "skip_complexity_reassessment": true
      },
      "negative": {
        "keywords": ["wrong", "no", "incorrect", "not what I meant", "that's not right"],
        "action": "re_decompose",
        "clear_current_state": true
      },
      "recourse": {
        "keywords": ["try again", "different approach", "retry", "rethink"],
        "action": "escalate_verification",
        "escalation_map": {
          "simple": "medium",
          "medium": "complex",
          "complex": "critical"
        }
      },
      "abort": {
        "keywords": ["never mind", "skip", "cancel", "stop", "forget it"],
        "action": "graceful_exit",
        "save_partial_state": true
      }
    }
  }
}
```

### Appendix F: Agent Registry Fallback

**No Agents Found Handling**:

```
┌─────────────────────────────────────────────────────────────────────┐
│                AGENT REGISTRY FALLBACK LOGIC                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. DISCOVERY ATTEMPT                                                │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Check: ~/.aurora/agents.json                                │    │
│  │ Check: <project>/.aurora/agents.json                        │    │
│  │ Check: MCP server config                                    │    │
│  │ Auto-discover: Scan available MCP tools                     │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  2. IF NO AGENTS FOUND                                               │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Option 1: PROMPT USER                                       │    │
│  │   → "No agents found. Please provide agent registry path:"  │    │
│  │   → User provides path → retry discovery                    │    │
│  │                                                             │    │
│  │ Option 2: LLM-ONLY MODE                                     │    │
│  │   → "Proceed with LLM-only mode? (y/n)"                    │    │
│  │   → If yes: All subgoals assigned to built-in "llm-executor"│    │
│  │   → SOAR becomes pure LLM pipeline (no agent routing)       │    │
│  │                                                             │    │
│  │ Option 3: USE DEFAULT AGENTS (if configured)                │    │
│  │   → Fall back to generic LLM agent definitions             │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  3. LLM-ONLY MODE BEHAVIOR                                           │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Built-in agent: "llm-executor"                              │    │
│  │   - Capabilities: ["all"] (generic problem solving)         │    │
│  │   - Domains: ["general"] (no specialization)                │    │
│  │   - Implementation: Direct LLM API call with subgoal context│    │
│  │   - Advantage: Always works (no external dependencies)      │    │
│  │   - Disadvantage: No specialization benefits                │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Configuration**:
```json
{
  "agents": {
    "fallback_mode": "llm_only",
    "prompt_for_path_if_missing": true,
    "default_agent": {
      "id": "llm-executor",
      "capabilities": ["all"],
      "domains": ["general"],
      "type": "built_in"
    }
  }
}
```

### Appendix G: Keyword-Based Complexity Classifier

**Fast Path Algorithm (Pre-LLM)**:

```python
def calculate_complexity_score(query: str) -> tuple[str, float]:
    """
    Fast keyword-based complexity scoring.
    Returns: (complexity_level, confidence_score)
    """
    query_lower = query.lower()
    tokens = query_lower.split()

    # Keyword dictionaries with weights
    keywords = {
        "simple": {
            "keywords": ["what is", "list", "show", "define", "tell me", "who is"],
            "weight": 0.0,
            "single_tokens": ["what", "list", "show"]
        },
        "medium": {
            "keywords": ["compare", "explain", "analyze", "how does", "difference between"],
            "weight": 0.3,
            "single_tokens": ["compare", "analyze", "explain"]
        },
        "complex": {
            "keywords": ["design", "architect", "strategy", "optimize", "implement", "build"],
            "weight": 0.7,
            "single_tokens": ["design", "architect", "optimize"]
        },
        "critical": {
            "keywords": ["critical", "production", "safety", "security", "mission-critical"],
            "weight": 1.0,
            "single_tokens": ["critical", "production", "security"]
        }
    }

    # Calculate score
    max_weight = 0.0
    matched_level = "simple"

    for level, data in keywords.items():
        # Check multi-word phrases
        for phrase in data["keywords"]:
            if phrase in query_lower:
                if data["weight"] > max_weight:
                    max_weight = data["weight"]
                    matched_level = level

        # Check single tokens
        for token in data["single_tokens"]:
            if token in tokens:
                if data["weight"] > max_weight:
                    max_weight = data["weight"]
                    matched_level = level

    # Additional heuristics
    question_count = query_lower.count("?")
    word_count = len(tokens)

    # Adjust score based on query characteristics
    if word_count > 20:
        max_weight = min(1.0, max_weight + 0.1)  # Longer queries tend to be complex
    if question_count > 1:
        max_weight = min(1.0, max_weight + 0.1)  # Multiple questions = complexity

    # Confidence based on match quality
    confidence = 0.9 if max_weight in [0.0, 1.0] else 0.6

    return matched_level, max_weight, confidence
```

**Decision Flow**:
```
Query arrives
    ↓
Run keyword classifier (fast, free)
    ↓
Score 0.0-0.4 or 0.6-1.0? → High confidence → Use keyword result
    ↓                                          (skip LLM call)
Score 0.4-0.6 (borderline)? → Low confidence
    ↓
Run LLM verification (~200ms, small cost)
    ↓
Use LLM result
```

**Configuration**:
```json
{
  "complexity": {
    "keyword_classifier": {
      "enabled": true,
      "borderline_llm_verify": true,
      "borderline_range": [0.4, 0.6],
      "custom_keywords": {
        "domain_specific_simple": ["status", "version"],
        "domain_specific_complex": ["migrate", "refactor"]
      }
    }
  }
}
```

### Appendix H: Glossary

| Term | Definition |
|------|------------|
| **ACT-R** | Adaptive Control of Thought - Rational; cognitive architecture for memory and retrieval |
| **Activation** | Numeric score determining chunk retrieval priority |
| **BLA** | Base-Level Activation; frequency and recency component |
| **cAST** | Code Abstract Syntax Tree; function-level code chunking |
| **Chunk** | Atomic unit of retrievable context (code function, reasoning pattern, etc.) |
| **MCP** | Model Context Protocol; standard for AI tool integration |
| **SOAR** | State, Operator, And Result; cognitive architecture for reasoning (used as inspiration) |
| **Spreading Activation** | Activation boost to related chunks via dependency graph |
| **Verification Layer** | LLM-based checking of decomposition and output validity |
| **Reasoning LLM** | LLM used for decomposition, verification, scoring (typically faster/cheaper) |
| **Solving LLM** | LLM used for actual agent work (typically more capable/expensive) |

---

### Appendix I: Implementation Guide - End-to-End Development Reference

**Purpose**: This appendix serves as a development roadmap, pointing to all critical sections needed to implement AURORA-Context from scratch. Reference this when building to ensure no component or nuance is forgotten.

---

#### **Phase 1: MVP - Core Components** (Weeks 1-4)

**1. Configuration System** → See: Appendix C
- Implement config file loading (`~/.aurora/config.json`)
- Override order: defaults → global → project → env vars → CLI flags
- **Critical nuances**:
  - Mode selection: `standalone` vs `mcp_integrated`
  - Multi-provider LLM support (Anthropic, OpenAI, Ollama)
  - Base URL customization for local endpoints
  - Aurora activation modes (`user_invoked`, `always_on`, `exclude_patterns`)

**2. ACT-R Memory System** → See: Section 6, Section 6.3.5
- SQLite + JSON storage architecture
- Activation formula: Base-Level + Spreading + Context-Boost - Decay
- Use `pyactr` library for formulas only (build retrieval ourselves)
- **Critical nuances**:
  - JSON schemas for all chunk types (CodeChunk, ReasoningChunk, KnowledgeChunk)
  - Tool tracking in ReasoningChunk (`tools_used`, `tool_sequence`)
  - Partial score caching (cache if ≥0.5, mark as pattern if ≥0.8)
  - Learning boosts: success (+0.2), partial (+0.05), neutral (0.0), failure (-0.1)

**3. Complexity Assessment** → See: Section 8.2, Appendix G
- **Two-tier approach** (keyword first, LLM fallback)
- Tier 1: Keyword classifier (60-70% of queries, free, instant)
- Tier 2: LLM verification (30-40% of queries, borderline cases only)
- **Critical nuances**:
  - Keyword classifier must run FIRST before any LLM call
  - Borderline range [0.4, 0.6] triggers LLM verification
  - Configurable keyword dictionaries per domain

**4. SOAR Orchestrator** → See: Section 7
- 9-phase flow: Assess → Retrieve → Decompose → Verify → Route → Collect → Synthesize → Record → Respond
- **Critical nuances**:
  - Phase 1 uses keyword classifier (internal function, not LLM)
  - Phase 4 verification options scale with complexity (A/B/C)
  - Phase 8 caching policy: only cache if final_score ≥ 0.5

**5. Verification System** → See: Section 5, Section 8.3-8.6, Appendix D
- Option A (self-verify) for MEDIUM queries
- Option B (adversarial) for COMPLEX queries
- Option C (debate) for CRITICAL queries (Phase 2)
- **Critical nuances**:
  - Weighted scoring (completeness 40%, others 20% each)
  - Complexity-scaled few-shot examples (0/2/4/6 based on complexity)
  - Feedback handling matrix (score thresholds: 0.8/0.7/0.5)
  - Retry limit: 2 attempts before escalation or failure

**6. Agent Registry** → See: Section 9.6, Appendix C, Appendix F
- Multi-path discovery (project → global → CLI tools)
- **Critical nuances**:
  - Discovery paths for all major CLI agents (Claude Code, Ampcode, Droid, Opencode)
  - Refresh interval: 15 days (not 60 minutes!)
  - Check file modification timestamp before re-scanning
  - Fallback to LLM-only mode if no agents found
  - Prompt user for path on first discovery failure

**7. Code Context Provider** → See: Section 9.2, Section 6.3.5
- cAST parsing via tree-sitter
- **Supported languages (Phase 1)**:
  - Python (`.py`) - tree-sitter-python
  - TypeScript/JavaScript (`.ts`, `.tsx`, `.js`, `.jsx`) - tree-sitter-typescript
  - Go (`.go`) - tree-sitter-go (Phase 1.5)
- **Critical nuances**:
  - Function-level chunking (not file-level)
  - Track dependencies, imports, calls in CodeChunk schema
  - Git signal extraction for recency boost

**8. LLM Prompt Specifications** → See: Section 8
- All 6 prompts must return ONLY valid JSON
- **Critical nuances**:
  - Section 8.2: Complexity assessment (two-tier, keyword first)
  - Section 8.3: Decomposition (with few-shot examples scaled by complexity)
  - Section 8.4: Decomposition verification (weighted scoring)
  - Section 8.5: Agent output verification
  - Section 8.6: Synthesis verification
  - Section 8.7: Retry feedback
  - Few-shot examples: built-in with external file override option

**9. Query Signal Detection** → See: Appendix E
- 5 signal types: positive, follow-up, negative, recourse, abort
- **Critical nuances**:
  - Positive → +0.1 confidence boost
  - Follow-up → maintain context, skip complexity re-assessment
  - Negative → re-decompose from scratch, clear state
  - Recourse → escalate verification level
  - Abort → graceful exit, save partial state

---

#### **Phase 2: Deep Reasoning + Knowledge** (Weeks 5-8)

**10. Option C Verification** → See: Section 5.1
- Multi-path decomposition + debate
- **Critical nuances**:
  - 3 independent decompositions
  - Cross-examination between paths
  - Final synthesis with confidence calibration

**11. KnowledgeContextProvider** → See: Section 6.3.5
- API documentation, schema retrieval, conventions
- **Critical nuances**:
  - KnowledgeChunk schema with source tracking
  - Confidence scoring for retrieved knowledge

**12. Dual-LLM Cost Optimization** → See: Appendix C
- Reasoning LLM (Haiku): decomposition, verification, scoring (80% of calls)
- Solving LLM (Opus): agent execution (20% of calls)
- **Critical nuances**:
  - Can mix providers (OpenAI for reasoning, Anthropic for solving)
  - Custom endpoints for local LLMs (Ollama, vLLM)

---

#### **Phase 3: Additional Languages + Scale** (Weeks 9-12)

**13. Additional Language Support** → See: Section 9.2
- Rust, Java, C++, Ruby based on community demand
- **Critical nuances**:
  - Each language needs tree-sitter parser + language-specific chunking rules

---

#### **Critical Implementation Checklist**

Before claiming "done", verify ALL of these:

- [ ] Config file loads with proper override order
- [ ] Keyword classifier runs BEFORE any LLM call (Tier 1)
- [ ] LLM verification only for borderline cases (Tier 2)
- [ ] Few-shot examples scale by complexity (0/2/4/6)
- [ ] Weighted scoring prevents over-inflation (completeness 40%)
- [ ] Partial scores cached with confidence flags (≥0.5)
- [ ] Agent discovery checks all CLI tool paths
- [ ] Agent refresh is 15 days, not 60 minutes
- [ ] Tools tracked in ReasoningChunk for learning
- [ ] Query signals detected and acted upon
- [ ] Aurora activation modes work (`user_invoked` + `always_on`)
- [ ] All 6 LLM prompts return valid JSON only
- [ ] ACT-R uses pyactr for formulas, builds retrieval logic
- [ ] Fallback to LLM-only mode if no agents found

---

#### **Key Files to Implement** (from Section 9.1)

**Core**:
- `packages/core/src/aurora_core/activation/engine.py` - ACT-R activation calculator
- `packages/core/src/aurora_core/store/sqlite.py` - SQLite + JSON storage
- `packages/core/src/aurora_core/chunks/reasoning_chunk.py` - With tool tracking

**SOAR**:
- `packages/soar/src/aurora_soar/orchestrator.py` - 9-phase flow
- `packages/soar/src/aurora_soar/phases/assess.py` - Keyword classifier (NOT LLM)
- `packages/soar/src/aurora_soar/agent_registry.py` - Multi-path discovery

**Reasoning**:
- `packages/reasoning/src/aurora_reasoning/assessment.py` - Two-tier complexity
- `packages/reasoning/src/aurora_reasoning/prompts/*.py` - All 6 prompts with few-shot

**Code Context**:
- `packages/context-code/src/aurora_context_code/languages/python.py`
- `packages/context-code/src/aurora_context_code/languages/typescript.py`
- `packages/context-code/src/aurora_context_code/languages/go.py`

**MCP Server**:
- `packages/mcp-server/src/aurora_mcp/server.py` - Aurora activation handling

---

**This appendix ensures no critical detail is forgotten during implementation. Cross-reference liberally!**

---

## DOCUMENT VERSION HISTORY

**v2.3 (2025-12-13):**
- **ADDED**: Appendix C.1 - Calibration Examples Override (Few-Shot JSON)
  - Complete guide for users to override built-in few-shot examples
  - External path configuration: `external_path: "~/.aurora/custom_examples.json"`
  - Merge strategies: "replace" vs "merge"
  - Full JSON schema for custom examples (decomposition, agent_output, synthesis)
  - Configuration options table with all available settings
  - Real-world use cases (domain-specific examples, multi-team configs)
  - Loading order and error handling documentation
- **CLARIFIED**: soar/ and reasoning/ Package Separation
  - Added Section 9.1.1: Package Architecture & Dependencies diagram
  - Explicitly shows soar/ depends on reasoning/ (not combined into one)
  - Documented rationale: independent iteration, isolated testing, version independence
  - Added dependency flow diagram showing package relationships
  - Added package roles table (soar/, reasoning/, core/, context-*, mcp-server)
- **UPDATED**: Section 7.1 Flow Diagram (SOAR Orchestrator)
  - Added explicit labels: `[SOAR only]` vs `[SOAR calls reasoning/]` for each phase
  - Shows specific function calls: reasoning.assessment.assess(), reasoning.decompose.decompose(), etc.
  - Clarified LLM-based phases: 1 (ASSESS), 3 (DECOMPOSE), 4 (VERIFY), 7 (SYNTHESIZE)
  - Identified orchestration-only phases: 2 (RETRIEVE), 5 (ROUTE), 6 (COLLECT), 8 (RECORD), 9 (RESPOND)
- **UPDATED**: Repository Structure (Section 9.1)
  - Added package dependency labels: soar/ "depends on reasoning/"
  - Added phase annotations showing which package implements each phase
  - Clarified reasoning/ as "independent, reusable" package
- **CORRECTED**: AURORA Acronym Expansion
  - Previous: "Agentic Universal Reasoning with Orchestrated Agent Architecture" (AUROAA - duplicate A)
  - Current: "Architecture for Unified Reasoning with Orchestrated Routing and Agents" (AURORA - correct)
  - Reason: New expansion properly spells AURORA and explicitly includes "Routing" (Phase 5 of SOAR)
- **UPDATED**: Section 9.7 - Conversation Logging File Structure
  - Changed from daily files (`YYYY-MM-DD.md`) to individual interaction files
  - File naming: `{keyword1}-{keyword2}-YYYY-MM-DD.md` (2 keywords extracted from query)
  - Directory structure: Organized by `YYYY/MM/` for efficient browsing
  - Allows multiple same-day SOAR interactions
  - Keyword extraction with fallback to "query-{n}" if extraction fails
  - Updated CLI commands for searching by keyword, date range, month
  - Collision handling: append `-{n}` counter if filename exists
- **UPDATED**: Section 6.8.2 - Conversation Logs storage location
  - Updated to reflect year/month directory structure
  - Individual files instead of daily append-only files
- **UPDATED**: Section 6.8.4 - Storage Lifecycle Example
  - Updated conversation log references to show keyword-based file names
- **ADDED**: Section 7.2.1 - Agent Response Format
  - Defined JSON envelope structure with required `summary` field (natural language)
  - Flexible `data` structure allows LLM to adapt schema based on subgoal needs
  - Required `confidence` field for verification
  - User interaction tracking within agent responses
  - Metadata includes tools_used, duration_ms, model_used
- **ADDED**: Section 9.7 - Conversation Logging
  - Complete audit trail in markdown files (`~/.aurora/logs/conversations/YYYY-MM-DD.md`)
  - All 9 SOAR phases logged with JSON outputs
  - User ↔ agent interactions captured
  - Daily rotation, 90-day retention, auto-compression after 7 days
  - CLI commands for log viewing and searching
  - Separate from ACT-R (complete vs selective storage)
- **ADDED**: Section 6.8 - ACT-R Storage Rules (Selective vs Complete Logs)
  - Clarified two separate storage systems with distinct purposes
  - ACT-R Memory: Selective (score ≥ 0.5), SQLite, optimized for retrieval
  - Conversation Logs: Complete (all interactions), Markdown, optimized for audit
  - Storage lifecycle examples showing both systems working together
  - Key differences table comparing ACT-R vs Conversation Logs
- **UPDATED**: Section 6.7 - Learning Updates
  - Corrected caching thresholds: cache if score ≥ 0.5 (not ≥ 0.8)
  - Mark as "pattern" if score ≥ 0.8 (high confidence)
  - Cache partial successes (0.5-0.8) for learning from "almost correct" attempts
  - Do NOT cache failures (score < 0.5)
  - Added rationale for caching partial successes
- **UPDATED**: Section 7.2 - Agent Registry
  - Added explicit reference to Section 7.2.1 for agent response format
  - Updated refresh interval to 15 days (consistent with config)
  - Added note about file modification timestamp checking
- **UPDATED**: Section 8.5 - Agent Output Verification
  - Changed variable name from `agent_output` to `agent_response` for consistency
  - Added calibration examples showing structured JSON agent responses
  - Examples demonstrate proper use of `summary`, `data`, and `confidence` fields
- **UPDATED**: Section 8.6 - Synthesis Verification
  - Updated to receive `agent_summaries` (natural language from each agent)
  - Synthesis recomposes summaries into coherent natural language answer
  - Added calibration examples showing synthesis from agent summaries
  - Clarified synthesis outputs natural language (not JSON)
- **ARCHITECTURAL CLARIFICATION**: Agent → Synthesis → User Flow
  - Agents return JSON envelope with natural language `summary` + flexible `data`
  - Synthesis gathers all agent `summary` fields (natural language)
  - Synthesis recomposes into ONE coherent natural language answer
  - User receives natural language (not JSON)
  - All JSON interactions logged to conversation logs for traceability
- **ARCHITECTURAL CLARIFICATION**: Two Storage Systems
  - ACT-R: "Remember what works" (selective, optimized for retrieval)
  - Conversation Logs: "Record what happened" (complete, optimized for audit)
  - Clear separation of concerns and use cases documented

**v2.2 (2025-12-13):**
- **ADDED**: Appendix I - Implementation Guide (End-to-End Development Reference)
  - Phase-by-phase development roadmap with section references
  - Critical implementation checklist (14 must-verify items)
  - Key files to implement from repository structure
  - All critical nuances documented to prevent forgetting during implementation
- **ADDED**: Section 9.2 - Supported Languages
  - Phase 1: Python, TypeScript/JavaScript (covers TS/TSX/JS/JSX)
  - Phase 1.5: Go (high AI dev usage for backend services, CLI tools)
  - Phase 2+: Rust, Java, C++, Ruby (based on community demand)
- **ADDED**: Section 6.3.5 - JSON Schema Specifications
  - Complete CodeChunk schema with tool tracking
  - Complete ReasoningChunk schema with `tools_used` and `tool_sequence`
  - Complete KnowledgeChunk schema (Phase 2)
  - Benefits: retrievability by tools, pattern matching, agent routing suggestions
- **UPDATED**: Appendix C - Configuration File
  - Aurora activation modes: `user_invoked` (default), `always_on` (power user)
  - Both modes can be true simultaneously (explicit prefix overrides always_on)
  - Exclude patterns for common short responses ("thanks", "yes", "ok")
  - Multi-LLM config: added `mode`, `base_url`, `headers`, `timeout_seconds`
  - Agent discovery paths for all CLI tools (Claude Code, Ampcode, Droid, Opencode)
  - Agent refresh interval: 15 days (not 60 minutes), with file modification check
  - Calibration examples: complexity-scaled (0/2/4/6 examples), built-in with external override
  - Memory caching policy: cache if ≥0.5, mark as pattern if ≥0.8, include confidence flag
  - Learning boosts: added `neutral: 0.0` for score 0.5-0.7 range
- **UPDATED**: Section 8.2 - Complexity Assessment (Restructured)

**v2.4 (2025-12-13):**
- **ENHANCED**: Section 6.3.5 - JSON Schema Specifications
  - Added `governance` section to all chunk types (CodeChunk, ReasoningChunk, KnowledgeChunk)
  - Governance includes: `compliance_tags`, `lifespan_policy`, `retention_rules`
  - Added `conversation_log_reference` for cross-linking ACT-R chunks to conversation logs
  - Added `metadata.semantic_role`, `metadata.keywords`, `metadata.domain` for semantic tagging
  - Semantic tags automatically extracted during Phase 7 (SYNTHESIZE)
- **ADDED**: Section 6.3.6 - Governance Metadata Specification
  - Three governance dimensions: semantic metadata, governance attributes, cross-linking
  - Retention rule examples and interpretation logic
  - Escalation candidate flagging for pattern-to-parametric conversion
  - Benefits: compliance tracking, multi-tier retention, audit trail, traceability
- **ADDED**: Section 6.3.7 - Semantic Tagging Mechanism
  - Automatic extraction during Phase 7 (zero manual effort)
  - Rules for semantic_role, keywords, domain classification
  - Enables semantic clustering in Phase 2 retrieval
  - Supports future Phase 2 knowledge base indexing
- **ENHANCED**: Section 6.7 - Learning Updates & Conditional Lifespan Management
  - Added Section 6.7.1: Conditional Lifespan Policy (beyond time-based decay)
  - Policy types: Indefinite, Confidence-Based, Usage-Based, Importance-Based, Escalation, Decay-After-Inactivity
  - Policy configuration with conditional rules (table format)
  - When policies are evaluated (Phase 8, during activation calc, periodic maintenance, Phase 2 retrieval)
  - Why conditional policies matter: compliance, performance, learning, flexibility, explicitness
- **ENHANCED**: Section 6.8.2 - Conversation Logs
  - Added Section 6.8.2.1: Log Indexing (Plaintext Memory Discovery)
  - Index schema (SQLite table: `log_index`) with keyword, topic, file, section, phase
  - Automatic indexing during Phase 8 (RECORD)
  - Phase 2 retrieval fallback: ACT-R → Log index → file references
  - Benefits: plaintext discoverable, reduced context usage, audit trail, bridge to Phase 2
  - Examples showing ACT-R + log index results combined
- **CLARIFIED**: Plaintext Memory Strategy
  - NOW (Phase 1): Simple keyword index of conversation logs
  - Phase 2: Formalize knowledge extraction and validation
  - Hybrid approach: index enables discovery, later extraction adds structure
- **ADDED**: Appendix C.2 - Lifespan Policies Configuration
  - Storage location: `memory.lifespan_policies` in config.json
  - Configuration fields: condition, lifespan, decay_mechanism, escalation_action
  - Default policies: patterns, security_critical, high_usage, inactive, default
  - Policy override examples (global and project-specific)
  - Configuration override order (built-in → global → project → env → CLI)
  - Key point: Changeable at runtime by editing config.json
  - When policies evaluated: Phase 8 (store), activation calc, maintenance, Phase 2 retrieval

**v2.3 (2025-12-13):**
- **ADDRESSED**: Language parser code (TypeScript, Go consideration)
  - Now shows two-tier approach (keyword first, LLM fallback)
  - Tier 1: Keyword-based classifier (internal function, 60-70% of queries, free)
  - Tier 2: LLM verification (only for borderline cases, 30-40% of queries)
  - Cost savings: ~60% reduction in complexity assessment costs
  - Clarified this is NOT an LLM call by default
- **ADDED**: Multi-provider LLM configuration examples
  - Dual-LLM Phase 2 (Haiku reasoning + Opus solving)
  - Multi-provider (OpenAI + Anthropic)
  - Custom endpoint (Ollama local)

**v2.1 (2025-12-12):**
- **ADDED**: Complete Aurora config file specification (`~/.aurora/config.json`)
  - Dual-LLM support (reasoning_llm vs solving_llm for Phase 2 cost optimization)
  - Weighted scoring configuration for all checkpoints
  - Keyword-based complexity classifier configuration
  - Agent registry fallback settings
  - Query signal detection patterns
- **ADDED**: Appendix D - Complete Feedback Handling Matrix (from MVP-Correction Part 18)
  - Decision trees for all 3 checkpoints (decomposition, agent output, synthesis)
  - Learning updates based on scores (success/partial/failure)
- **ADDED**: Appendix E - Query Signal Detection
  - Positive, follow-up, negative, recourse, abort signal handling
  - Configuration for signal patterns and actions
- **ADDED**: Appendix F - Agent Registry Fallback Logic
  - No agents found handling (prompt user, LLM-only mode, default agents)
  - Built-in "llm-executor" agent specification
- **ADDED**: Appendix G - Keyword-Based Complexity Classifier
  - Fast path algorithm (pre-LLM, free) with Python implementation
  - Borderline case LLM verification logic
  - Decision flow diagram

**v2.0 (2025-12-12):**
- Complete consolidation from AURORA-MVP-Correction.md
- Added all 6 LLM prompt specifications with JSON schemas
- Clarified SQLite+JSON architecture (JSON IN columns, not separate files)
- Clarified pyactr usage scope (formulas only, build retrieval ourselves)
- Added SOAR orchestrator 9-phase flow
- Added agent registry with auto-discovery
- Added logging, metrics, and reporting specifications
- Added verbosity control levels
- Merged all missing Parts 12-26 from Correction document
- This is now the SINGLE SOURCE OF TRUTH

**v1.0 (2025-12-12):**
- Initial PRD (incomplete, missing verification layer)

---

**END OF SPECIFICATION**

This document is NOW COMPLETE with ALL missing parts:
✅ Aurora config file (`~/.aurora/config.json`) with dual-LLM support
✅ Feedback handling matrix (Part 18 from MVP-Correction)
✅ Query signal detection (positive, negative, follow-up, recourse, abort)
✅ Agent registry fallback logic (LLM-only mode)
✅ Keyword-based complexity classifier (fast path algorithm)
✅ Weighted scoring configuration
✅ All 6 LLM prompt specifications
✅ Complete SOAR orchestrator flow
✅ ACT-R memory system details

**Ready for implementation!** A cleaner, marketing-focused PRD will be derived from this spec.
