# PRD 0003: AURORA SOAR Pipeline & Verification
## Product Requirements Document

**Version**: 1.0
**Date**: December 20, 2025
**Status**: Ready for Implementation
**Phase**: MVP Phase 2 of 3 (SOAR Pipeline)
**Product**: AURORA-Context Framework
**Dependencies**: Phase 1 (0002-prd-aurora-foundation.md)

---

## DOCUMENT PURPOSE

This PRD defines **Phase 2: SOAR Pipeline & Verification** for the AURORA-Context framework. This phase implements the 9-phase SOAR orchestrator with verification at decomposition, agent execution, and synthesis stages.

**Success Criteria**: This phase is complete when all SOAR phases are operational, verification catches invalid outputs, and the system produces reliable reasoning with earned confidence scores.

**Related Documents**:
- Source Specification: `/tasks/0001-prd-aurora-context.md` (Sections 3.2, 5, 7, 8)
- Previous Phase: `/tasks/0002-prd-aurora-foundation.md` (MUST be complete)
- Next Phase: `/tasks/0004-prd-aurora-advanced-features.md` (depends on 0002+0003)

---

## TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [Goals & Success Metrics](#2-goals--success-metrics)
3. [User Stories](#3-user-stories)
4. [Functional Requirements](#4-functional-requirements)
5. [Architecture & Design](#5-architecture--design)
6. [Quality Gates & Acceptance Criteria](#6-quality-gates--acceptance-criteria)
7. [Testing Strategy](#7-testing-strategy)
8. [Inter-Phase Dependencies](#8-inter-phase-dependencies)
9. [Non-Goals (Out of Scope)](#9-non-goals-out-of-scope)
10. [Technical Considerations](#10-technical-considerations)
11. [Delivery Verification Checklist](#11-delivery-verification-checklist)
12. [Open Questions](#12-open-questions)

---

## 1. EXECUTIVE SUMMARY

### 1.1 What is AURORA SOAR Pipeline?

The SOAR (State, Operator, And Result) Pipeline is AURORA's reasoning orchestration layer that:
1. Assesses query complexity
2. Retrieves relevant context from ACT-R memory
3. Decomposes complex queries into verifiable subgoals
4. Routes subgoals to specialized agents
5. Verifies outputs at multiple checkpoints
6. Synthesizes agent results into coherent answers
7. Learns from successes and failures

**The Critical Innovation**: Multi-stage verification prevents unreliable reasoning from propagating through the system.

### 1.2 Key Components (Phase 2)

1. **9-Phase SOAR Orchestrator**: Assess → Retrieve → Decompose → Verify → Route → Collect → Synthesize → Record → Respond
2. **Complexity Assessment**: Two-tier (keyword + LLM) classification
3. **Verification System**: Options A (self-verify), B (adversarial), C (debate - Phase 3)
4. **LLM Routing**: Separate reasoning vs solving models
5. **Cost Tracking**: Budget enforcement and estimation
6. **Agent Execution**: Parallel where possible, with retry logic
7. **ReasoningChunk**: Full implementation (stub from Phase 1)

### 1.3 Why Verification Matters

Without verification, decomposition just **distributes unreliable reasoning**. With verification:
- Catch invalid decompositions before wasting compute
- Detect agent outputs that don't address subgoals
- Identify contradictions between results
- Provide **earned** confidence scores (not heuristic guesses)
- Enable learning from **verified** successes

---

## 2. GOALS & SUCCESS METRICS

### 2.1 Primary Goals

1. **Implement end-to-end SOAR orchestration** with all 9 phases
2. **Establish verification at 3 checkpoints** (decomposition, agent output, synthesis)
3. **Enable complexity-based routing** (simple → direct, complex → full pipeline)
4. **Deliver reliable confidence scoring** (earned from verification checks)
5. **Support agent parallel execution** where subgoals allow
6. **Track costs and enforce budgets** to prevent runaway spending

### 2.2 Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Reasoning Accuracy** | ≥80% on benchmark suite | Verifiable test queries |
| **Verification Catch Rate** | ≥70% of injected errors | Fault injection tests |
| **Score Calibration** | ≥0.7 correlation with correctness | Score vs ground truth |
| **Latency (Simple)** | <2s end-to-end | Performance benchmarks |
| **Latency (Complex)** | <10s end-to-end | Performance benchmarks |
| **Cost per Complex Query** | ≤3x baseline LLM-only | Cost tracking |
| **Retry Rate** | ≤20% decompositions need retry | Telemetry data |
| **Agent Utilization** | ≥90% subgoals routed successfully | Success tracking |

### 2.3 Phase Completion Criteria

Phase 2 is **COMPLETE** when:
- ✅ All 9 SOAR phases implemented and tested
- ✅ Options A and B verification operational
- ✅ Complexity assessment (keyword + LLM) works
- ✅ Agent routing and execution reliable
- ✅ Cost tracking and budget enforcement functional
- ✅ All quality gates passed (≥85% coverage)
- ✅ Reasoning accuracy ≥80% on benchmarks
- ✅ Documentation complete with examples

---

## 3. USER STORIES

### 3.1 Developer Solving Complex Problem

**As a** developer using Claude Code with AURORA,
**I want** complex queries decomposed into verifiable subgoals,
**So that** I get reliable, traceable answers even for multi-step problems.

**Acceptance Criteria**:
- Query "Implement OAuth2 authentication" decomposes into 4-5 subgoals
- Each subgoal verified before execution
- Final answer synthesizes all agent outputs coherently
- Confidence score reflects actual verification results
- If verification fails, system retries or escalates

---

### 3.2 Cost-Conscious Personal User

**As a** personal developer with limited budget,
**I want** AURORA to route simple queries directly (skip decomposition),
**So that** I don't pay for unnecessary orchestration overhead.

**Acceptance Criteria**:
- Simple queries ("What is OAuth2?") bypass decomposition (1 LLM call)
- Complex queries use full pipeline (multiple LLM calls)
- Cost tracking shows per-query breakdown
- Budget warning at 80% limit, block at 100%
- Monthly budget resets automatically

---

### 3.3 Quality-Focused Team Lead

**As a** team lead integrating AURORA into CI/CD,
**I want** verification to catch unreliable outputs before they're used,
**So that** automated tasks don't fail due to low-quality reasoning.

**Acceptance Criteria**:
- Decomposition verification catches incomplete breakdowns (score <0.7)
- Agent output verification catches irrelevant responses (score <0.7)
- Synthesis verification catches inconsistent answers (score <0.7)
- System retries failed verifications up to 2 times
- Failed queries return partial results with explicit warnings

---

### 3.4 Agent Developer

**As a** developer building custom agents,
**I want** clear interface definitions and response formats,
**So that** my agents integrate smoothly with SOAR routing.

**Acceptance Criteria**:
- Agent response format documented (JSON envelope with `summary`, `data`, `confidence`)
- Example agent implementation provided
- Verification checks documented (relevance, completeness, groundedness)
- Error handling specified (retry, fallback, escalation)
- Testing utilities available for agent validation

---

## 4. FUNCTIONAL REQUIREMENTS

### 4.1 SOAR Orchestrator (Core Component)

**Package**: `packages/soar/src/aurora_soar/orchestrator.py`

#### 4.1.1 Orchestrator Interface

**MUST** implement `SOAROrchestrator` class:

```python
from typing import Dict, Any, List, Optional
from aurora_core.store import Store
from aurora_soar.agent_registry import AgentRegistry
from aurora_core.config import Config

class SOAROrchestrator:
    """Main SOAR orchestration engine."""

    def __init__(self, store: Store, agent_registry: AgentRegistry, config: Config):
        self.store = store
        self.agent_registry = agent_registry
        self.config = config
        self.reasoning_llm = self._init_reasoning_llm()
        self.solving_llm = self._init_solving_llm()

    def execute(self, query: str, verbosity: str = "quiet") -> Dict[str, Any]:
        """
        Execute full SOAR pipeline for a query.

        Args:
            query: User query string
            verbosity: "quiet" | "normal" | "verbose" | "json"

        Returns:
            {
                "answer": str,
                "confidence": float,
                "overall_score": float,
                "reasoning_trace": Dict,
                "metadata": Dict
            }
        """
        pass
```

#### 4.1.2 Phase 1: ASSESS (Complexity Classification)

**MUST** implement two-tier assessment:

**Tier 1: Keyword Classifier** (from spec Appendix G):
```python
def _assess_tier1_keyword(self, query: str) -> Tuple[str, float, float]:
    """
    Fast keyword-based complexity assessment.

    Returns:
        (complexity_level, score, confidence)
        - complexity_level: "simple" | "medium" | "complex" | "critical"
        - score: 0.0-1.0 (keyword match score)
        - confidence: 0.0-1.0 (how confident in classification)
    """
    pass
```

**Tier 2: LLM Verification** (for borderline cases):
```python
def _assess_tier2_llm(self, query: str, keyword_result: Dict) -> Dict[str, Any]:
    """
    LLM-based complexity verification.

    Only called if keyword confidence < 0.8 or score in [0.4, 0.6].

    Returns:
        {
            "complexity": str,
            "confidence": float,
            "reasoning": str,
            "indicators": List[str],
            "recommended_verification": str
        }
    """
    pass
```

**Decision Logic**:
```python
def _assess_complexity(self, query: str) -> Dict[str, Any]:
    """
    Assess query complexity using two-tier approach.

    1. Run keyword classifier (instant, free)
    2. If confidence >= 0.8 AND score not in [0.4, 0.6]:
       → Use keyword result (skip LLM)
    3. Else:
       → Run LLM verification
    """
    pass
```

**Cost Optimization**:
- 60-70% of queries use keyword only (zero LLM cost)
- 30-40% use LLM verification (~$0.0002/query)
- Target: <$0.0001 average per complexity assessment

---

#### 4.1.3 Phase 2: RETRIEVE (ACT-R Memory)

**MUST** retrieve relevant context from Phase 1 storage:

```python
def _retrieve_context(self, query: str, complexity: str) -> Dict[str, Any]:
    """
    Retrieve relevant chunks from ACT-R memory.

    Args:
        query: User query
        complexity: Complexity level (determines budget)

    Returns:
        {
            "code_chunks": List[CodeChunk],
            "reasoning_chunks": List[ReasoningChunk],
            "total_chunks": int,
            "retrieval_time_ms": float
        }
    """
    pass
```

**Budget Allocation**:
- SIMPLE: budget = 5 chunks (minimal context)
- MEDIUM: budget = 10 chunks (standard)
- COMPLEX: budget = 15 chunks (extensive context)
- CRITICAL: budget = 20 chunks (maximum context)

**Retrieval Algorithm** (Phase 2 - basic):
- Use `CodeContextProvider` from Phase 1 (keyword-based)
- Query `Store.retrieve_by_activation()` (Phase 3 will use ACT-R scores)
- For now: return top-N by keyword relevance
- Phase 3 upgrade: spreading activation, base-level learning

---

#### 4.1.4 Phase 3: DECOMPOSE (Structured JSON)

**MUST** decompose complex queries using reasoning LLM:

```python
def _decompose_query(self, query: str, context: Dict, complexity: str) -> Dict[str, Any]:
    """
    Decompose query into structured subgoals.

    Uses LLM with prompt from spec Section 8.3.

    Returns:
        {
            "decomposition": {
                "id": str,
                "original_query": str,
                "given": List[Dict],
                "goal": Dict,
                "subgoals": List[Dict],
                "execution_order": List[str],
                "parallelizable": List[List[str]]
            }
        }
    """
    pass
```

**Decomposition Schema** (from spec Section 4.2):
```json
{
  "decomposition": {
    "id": "uuid",
    "original_query": "user's question",
    "complexity": "simple | medium | complex | critical",
    "given": [
      {"id": "G1", "fact": "extracted fact 1", "source": "query"}
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

**Prompt Construction**:
- Use `reasoning.prompts.decompose` module (spec Section 8.3)
- Include retrieved context chunks
- Include available agents from registry
- Inject few-shot examples scaled by complexity (0/2/4/6)
- Enforce JSON-only output (no markdown, no explanation)

---

#### 4.1.5 Phase 4: VERIFY (Decomposition)

**MUST** verify decomposition quality before execution:

```python
def _verify_decomposition(self, decomposition: Dict, option: str) -> Dict[str, Any]:
    """
    Verify decomposition using specified option.

    Args:
        decomposition: Decomposition JSON from Phase 3
        option: "option_a" (self-verify) | "option_b" (adversarial)

    Returns:
        {
            "verification": {
                "decomposition_id": str,
                "checks": {
                    "completeness": {"score": float, "pass": bool, "issues": List, "detail": str},
                    "consistency": {"score": float, "pass": bool, "issues": List, "detail": str},
                    "groundedness": {"score": float, "pass": bool, "issues": List, "detail": str},
                    "routability": {"score": float, "pass": bool, "issues": List, "detail": str}
                },
                "overall_score": float,
                "verdict": "pass" | "retry" | "fail",
                "critical_issues": List[str],
                "suggestions": List[str]
            }
        }
    """
    pass
```

**Option A: Self-Verification** (MEDIUM complexity):
- Same LLM reviews its own decomposition
- Prompt: Check completeness, consistency, groundedness, routability
- Fast, low cost (~1.5x baseline)
- Limitation: same blind spots

**Option B: Adversarial Verification** (COMPLEX complexity):
- Second LLM (or different prompt) acts as critic
- Finds hidden assumptions, alternative conclusions, logical leaps
- More thorough, higher cost (~2-3x baseline)
- Better for complex/critical tasks

**Verification Process**:
1. Generator creates decomposition (Phase 3)
2. Critic identifies weaknesses (Phase 4)
3. If score 0.5-0.7: retry with feedback (max 2 attempts)
4. If score ≥0.7: pass, proceed to routing
5. If score <0.5: fail, return error

**Scoring Formula** (weighted):
```python
overall_score = (
    0.4 * completeness_score +
    0.2 * consistency_score +
    0.2 * groundedness_score +
    0.2 * routability_score
)
```

**Verdict Rules**:
- `pass`: overall_score ≥ 0.7
- `retry`: overall_score 0.5-0.7 AND retry_count < 2
- `fail`: overall_score < 0.5 OR retry_count ≥ 2

---

#### 4.1.6 Phase 5: ROUTE (Agent Selection)

**MUST** match subgoals to agents:

```python
def _route_subgoals(self, subgoals: List[Dict]) -> List[Dict]:
    """
    Match subgoals to agents from registry.

    Args:
        subgoals: List of subgoal dicts from decomposition

    Returns:
        [
            {
                "subgoal_id": str,
                "agent_id": str,
                "agent_type": str,
                "agent_info": AgentInfo
            }
        ]
    """
    pass
```

**Routing Algorithm**:
1. For each subgoal:
   - Get `subgoal.agent` (suggested agent from decomposition)
   - Check if agent exists: `registry.get_agent(agent_id)`
   - If exists: route to that agent
   - If missing: find by capability: `registry.find_by_capability(capability)`
   - If no match: route to fallback `llm-executor`

2. Validate routing:
   - All subgoals assigned
   - No circular dependencies
   - Respect execution order

3. Return routing plan

**Fallback Behavior**:
- If agent not found: use `llm-executor` (built-in)
- Log warning: "Agent {id} not found, using fallback"
- Track fallback usage for metrics

---

#### 4.1.7 Phase 6: COLLECT (Agent Execution)

**MUST** execute agents and collect outputs:

```python
def _execute_agents(self, routing_plan: List[Dict], decomposition: Dict) -> List[Dict]:
    """
    Execute agents in correct order, parallelizing where possible.

    Args:
        routing_plan: Agent assignments from Phase 5
        decomposition: Full decomposition (for parallelization info)

    Returns:
        [
            {
                "subgoal_id": str,
                "agent_id": str,
                "status": "success" | "partial" | "error",
                "output": {
                    "summary": str,
                    "data": Dict,
                    "confidence": float
                },
                "user_interactions": List[Dict],
                "metadata": Dict
            }
        ]
    """
    pass
```

**Execution Strategy**:
1. Parse `decomposition.execution_order` and `decomposition.parallelizable`
2. Execute subgoals in order:
   - Parallel where `parallelizable` indicates
   - Sequential otherwise (wait for dependencies)
3. For each agent execution:
   - Call agent with subgoal context
   - Verify output format (spec Section 7.2.1)
   - Track user interactions if any
   - Log metadata (tools_used, duration_ms, model_used)

**Agent Response Format** (spec Section 7.2.1):
```json
{
  "subgoal_id": "SG1",
  "agent_id": "research-agent",
  "status": "success",
  "output": {
    "summary": "Natural language summary (REQUIRED)",
    "data": {
      "flexible": "LLM-adapted structure"
    },
    "confidence": 0.92
  },
  "user_interactions": [
    {
      "turn": 1,
      "agent_question": "What's your budget?",
      "user_response": "$2000/month",
      "timestamp": "ISO 8601"
    }
  ],
  "metadata": {
    "tools_used": ["websearch", "mcp:reddit"],
    "duration_ms": 12500,
    "model_used": "claude-sonnet-4.5"
  }
}
```

**Parallel Execution**:
- Use `asyncio` or thread pool for parallelizable subgoals
- Max concurrency: 5 agents (configurable)
- Timeout per agent: 60 seconds (configurable)

**Error Handling**:
- If agent fails: retry once (different agent if available)
- If retry fails: mark as `partial` success, continue
- If critical subgoal fails: abort entire query

**Verification of Agent Outputs**:
- After each agent: run output verification (Phase 4b)
- Check: relevance, completeness, groundedness
- If score <0.7: retry with feedback (max 2 attempts)
- If still fails: accept as `partial` with warning

---

#### 4.1.8 Phase 7: SYNTHESIZE (Recomposition)

**MUST** synthesize agent outputs into coherent answer:

```python
def _synthesize_results(self, agent_outputs: List[Dict], decomposition: Dict) -> Dict[str, Any]:
    """
    Synthesize agent outputs into natural language answer.

    Args:
        agent_outputs: List of agent responses from Phase 6
        decomposition: Original decomposition (for context)

    Returns:
        {
            "final_answer": str,
            "synthesis_metadata": {
                "subgoals_completed": int,
                "total_files_modified": int,
                "user_interactions_count": int
            }
        }
    """
    pass
```

**Synthesis Process**:
1. Gather all agent `output.summary` fields (natural language)
2. Use reasoning LLM with synthesis prompt (spec Section 8.6)
3. Recompose into ONE coherent natural language answer
4. Include context from user interactions if relevant
5. Ensure traceability (every claim links to agent summary)

**Prompt Construction**:
- Use `reasoning.prompts.synthesize` module
- Input: original query + agent summaries + decomposition goal
- Output: Natural language answer (NOT JSON)
- Ensure: addresses query, traceable, consistent, calibrated confidence

**Synthesis Verification** (Phase 4c):
- Verify synthesized answer against agent summaries
- Checks: addresses_query, traceable, consistent, calibrated
- If score <0.7: retry with feedback (max 2 attempts)
- If still fails: return partial results with warnings

---

#### 4.1.9 Phase 8: RECORD (ACT-R Storage)

**MUST** cache successful patterns to ACT-R memory:

```python
def _record_pattern(self, query: str, decomposition: Dict, verification_score: float, complexity: str) -> Dict[str, Any]:
    """
    Store reasoning pattern if score meets threshold.

    Args:
        query: Original user query
        decomposition: Full decomposition JSON
        verification_score: Final synthesis verification score
        complexity: Query complexity level

    Returns:
        {
            "stored_to_actr": bool,
            "chunk_id": Optional[str],
            "reasoning": str
        }
    """
    pass
```

**Caching Policy** (spec Section 6.7):
- If `verification_score >= 0.5`: Cache to ACT-R
- If `verification_score >= 0.8`: Mark as `is_pattern: true`
- If `verification_score < 0.5`: Do NOT cache (failed attempt)

**ReasoningChunk Schema** (spec Section 6.3.5):
```json
{
  "id": "reas:auth-flow-123",
  "type": "reasoning",
  "content": {
    "pattern": "authentication-setup",
    "original_query": "Build OAuth2 authentication",
    "complexity": "complex",
    "subgoals": [...],
    "tools_used": [
      {"subgoal": "SG1", "agent": "researcher", "tools": ["websearch", "mcp:reddit"]}
    ],
    "tool_sequence": ["websearch", "mcp:reddit", "grep", "read", "edit"],
    "success_score": 0.92,
    "verification_option": "option_b"
  },
  "metadata": {
    "timestamp": "ISO 8601",
    "execution_time_ms": 15420,
    "total_cost_usd": 0.0234,
    "semantic_role": "oauth-decomposition-pattern",
    "keywords": ["oauth2", "authentication", "token"],
    "domain": "security"
  }
}
```

**Learning Updates** (spec Section 6.7):
- Success (score ≥0.8): +0.2 activation to retrieved chunks
- Partial (score 0.5-0.8): +0.05 to helpful, -0.05 to unhelpful
- Failure (score <0.5): -0.1 to retrieved reasoning patterns

---

#### 4.1.10 Phase 9: RESPOND (Format Output)

**MUST** format response based on verbosity level:

```python
def _format_response(self, final_answer: str, metadata: Dict, verbosity: str) -> Dict[str, Any]:
    """
    Format final response according to verbosity.

    Args:
        final_answer: Synthesized natural language answer
        metadata: Execution metadata (timing, costs, scores)
        verbosity: "quiet" | "normal" | "verbose" | "json"

    Returns:
        Formatted response dict
    """
    pass
```

**Verbosity Levels** (spec Section 9.5):

**QUIET** (default):
```
aurora: done (score: 0.85)
```

**NORMAL** (`-v`):
```
aurora: assessing complexity... COMPLEX (0.82)
aurora: decomposing... 3 subgoals
aurora: verifying (adversarial)... PASS (0.85)
aurora: routing to agents...
aurora: done (score: 0.85, cached: yes)
```

**VERBOSE** (`-vv`):
```
aurora: assessing complexity...
  keywords: [auth, feature, implement] → score: 0.7
  llm verification: COMPLEX (confidence: 0.82)
aurora: retrieving context (budget: 15)...
  reas: patterns: 2 (activation: 0.8, 0.6)
  code: chunks: 5 (auth.py:0.9, session.py:0.7, ...)
... (full trace)
```

**JSON** (`--json`):
```json
{"stage":"assess","status":"complete","complexity":"complex","confidence":0.82}
{"stage":"retrieve","status":"complete","chunks":{"code":5,"reas":2}}
...
{"stage":"done","final_score":0.85,"cached":true}
```

**Response Structure**:
```python
{
    "answer": str,                    # Natural language final answer
    "confidence": float,              # 0.0-1.0 (from verification scores)
    "overall_score": float,           # Synthesis verification score
    "reasoning_trace": Dict,          # Full SOAR execution trace (if verbose)
    "metadata": {
        "total_duration_ms": float,
        "tokens_used": Dict,
        "estimated_cost_usd": float,
        "cached_to_actr": bool,
        "complexity": str,
        "verification_option": str
    }
}
```

---

### 4.2 LLM Integration (Reasoning Package)

**Package**: `packages/reasoning/src/aurora_reasoning/`

#### 4.2.1 LLM Client Abstraction

**MUST** support multi-provider LLMs:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class LLMClient(ABC):
    """Abstract LLM client interface."""

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate response from LLM."""
        pass

    @abstractmethod
    def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate JSON response from LLM."""
        pass

class AnthropicClient(LLMClient):
    """Anthropic API client."""
    pass

class OpenAIClient(LLMClient):
    """OpenAI API client."""
    pass

class OllamaClient(LLMClient):
    """Ollama local LLM client."""
    pass
```

**Configuration** (from Phase 1 Config):
```python
def _init_reasoning_llm(self) -> LLMClient:
    """Initialize reasoning LLM from config."""
    provider = self.config.get("llm.reasoning_provider")
    model = self.config.get("llm.reasoning_model")
    # Return appropriate client
    pass

def _init_solving_llm(self) -> LLMClient:
    """Initialize solving LLM from config."""
    provider = self.config.get("llm.solving_provider")
    model = self.config.get("llm.solving_model")
    # Return appropriate client
    pass
```

---

#### 4.2.2 Prompt Templates

**MUST** implement all 6 prompts from spec Section 8:

**Files**:
- `prompts/assess.py` - Complexity assessment (Tier 2 LLM)
- `prompts/decompose.py` - Structured decomposition
- `prompts/verify_self.py` - Self-verification (Option A)
- `prompts/verify_adversarial.py` - Adversarial verification (Option B)
- `prompts/verify_agent_output.py` - Agent output verification
- `prompts/verify_synthesis.py` - Synthesis verification
- `prompts/retry_feedback.py` - Retry feedback generation

**Prompt Structure** (all prompts):
```python
def build_prompt(context: Dict[str, Any], config: Config) -> str:
    """
    Build prompt from template + context.

    Args:
        context: Query-specific data
        config: Global config (for few-shot examples, etc.)

    Returns:
        Complete prompt string (JSON instructions + examples)
    """
    pass
```

**Few-Shot Examples** (spec Section 8, Appendix C.1):
- Load built-in examples by default
- Support external override: `config.scoring.calibration_examples.external_path`
- Scale by complexity: simple=0, medium=2, complex=4, critical=6
- Merge strategy: "replace" or "merge"

---

### 4.3 Cost Tracking & Budget Enforcement

**Package**: `packages/core/src/aurora_core/budget/`

#### 4.3.1 Cost Estimator

**MUST** estimate query costs before execution:

```python
class CostEstimator:
    """Estimate LLM costs for queries."""

    def estimate_query_cost(self, query: str, complexity: str) -> float:
        """
        Estimate cost for a query.

        Formula: base_cost × complexity_multiplier × (tokens / 1000)

        Base costs:
            SIMPLE: $0.001 (Haiku)
            MEDIUM: $0.05 (Sonnet)
            COMPLEX: $0.50 (Opus)

        Complexity multipliers:
            SIMPLE: 1.0
            MEDIUM: 3.0
            COMPLEX: 5.0

        Returns:
            Estimated cost in USD
        """
        pass
```

#### 4.3.2 Budget Tracker

**MUST** track spending and enforce limits:

```python
class BudgetTracker:
    """Track and enforce spending limits."""

    def __init__(self, config: Config):
        self.config = config
        self.tracker_file = Path.home() / ".aurora" / "budget_tracker.json"
        self._load_tracker()

    def check_budget(self, estimated_cost: float) -> Tuple[bool, str]:
        """
        Check if query would exceed budget.

        Returns:
            (allowed, message)
            - allowed: True if query can proceed
            - message: Warning/error message if applicable
        """
        pass

    def record_cost(self, actual_cost: float) -> None:
        """Record actual cost after query execution."""
        pass

    def get_status(self) -> Dict[str, Any]:
        """Get current budget status."""
        pass
```

**Budget Tracker File** (`~/.aurora/budget_tracker.json`):
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

**Budget Enforcement** (spec Section 9.4.2):
- Soft limit (80%): Warn user, allow query
- Hard limit (100%): Block query, show status
- Pre-query check in SOAR Phase 1 (before assessment)

---

### 4.4 Conversation Logging

**Package**: `packages/core/src/aurora_core/logging/`

#### 4.4.1 Conversation Logger

**MUST** log all SOAR interactions to markdown files:

```python
class ConversationLogger:
    """Log complete SOAR interactions."""

    def __init__(self, config: Config):
        self.log_path = config.get("logging.conversations.path")
        self.enabled = config.get("logging.conversations.enabled")

    def log_interaction(self, query_id: str, query: str, phases: List[Dict]) -> Path:
        """
        Log full SOAR interaction to markdown file.

        Args:
            query_id: Unique query ID
            query: Original user query
            phases: List of phase outputs (all 9 phases)

        Returns:
            Path to log file
        """
        pass

    def _extract_keywords(self, query: str) -> List[str]:
        """Extract 2 keywords from query for filename."""
        pass

    def _format_log(self, query: str, phases: List[Dict]) -> str:
        """Format log as markdown."""
        pass
```

**File Structure** (spec Section 9.7):
```
~/.aurora/logs/conversations/
  └── YYYY/
      └── MM/
          ├── oauth-authentication-2025-12-13.md
          ├── database-migration-2025-12-13.md
          └── ...
```

**Log Format** (markdown with JSON blocks):
```markdown
---
## Query: 2025-12-13T14:32:15Z | ID: aurora-20251213-143215-abc123

**User Query**: "Implement OAuth2 authentication"

### Phase 1: ASSESS
```json
{"phase": "assess", "complexity": "complex", ...}
```

### Phase 2-9: [Complete trace]

### Execution Summary
- **Total Duration**: 12.8 seconds
- **Verification Score**: 0.93
---
```

---

## 5. ARCHITECTURE & DESIGN

### 5.1 Package Dependencies (Phase 2)

```
packages/
├── soar/
│   ├── src/aurora_soar/
│   │   ├── orchestrator.py              # Main SOAR orchestrator
│   │   ├── phases/
│   │   │   ├── assess.py                # Phase 1 (keyword + LLM)
│   │   │   ├── retrieve.py              # Phase 2 (ACT-R)
│   │   │   ├── decompose.py             # Phase 3 (calls reasoning/)
│   │   │   ├── verify.py                # Phase 4 (calls reasoning/)
│   │   │   ├── route.py                 # Phase 5 (agent registry)
│   │   │   ├── collect.py               # Phase 6 (agent execution)
│   │   │   ├── synthesize.py            # Phase 7 (calls reasoning/)
│   │   │   ├── record.py                # Phase 8 (ACT-R storage)
│   │   │   └── respond.py               # Phase 9 (format output)
│   │   └── agent_registry.py            # From Phase 1
│   └── depends on → reasoning/, core/
│
├── reasoning/
│   ├── src/aurora_reasoning/
│   │   ├── pipeline.py                  # Reasoning pipeline interface
│   │   ├── assessment.py                # Complexity assessment
│   │   ├── decompose.py                 # Decomposition logic
│   │   ├── verify.py                    # Verification (A/B/C)
│   │   ├── synthesize.py                # Synthesis logic
│   │   ├── prompts/
│   │   │   ├── assess.py
│   │   │   ├── decompose.py
│   │   │   ├── verify_self.py
│   │   │   ├── verify_adversarial.py
│   │   │   ├── verify_agent_output.py
│   │   │   ├── verify_synthesis.py
│   │   │   └── retry_feedback.py
│   │   └── llm_client.py                # LLM abstraction
│   └── depends on → core/
│
├── core/
│   ├── src/aurora_core/
│   │   ├── chunks/
│   │   │   └── reasoning_chunk.py       # Full implementation (Phase 2)
│   │   ├── budget/                      # NEW
│   │   │   ├── estimator.py
│   │   │   └── tracker.py
│   │   └── logging/
│   │       └── conversation_logger.py   # NEW
│   └── (from Phase 1)
```

### 5.2 SOAR Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    SOAR ORCHESTRATOR                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Phase 1: ASSESS [SOAR + reasoning/]                        │
│  ├── Keyword classifier (internal function)                 │
│  ├── LLM verification if borderline (reasoning.assessment)  │
│  └── Output: complexity, confidence, route                  │
│                                                              │
│  Phase 2: RETRIEVE [SOAR only]                              │
│  ├── Call: core.store.retrieve_by_activation()             │
│  ├── Budget allocation by complexity                        │
│  └── Output: code_chunks, reasoning_chunks                  │
│                                                              │
│  Phase 3: DECOMPOSE [reasoning/]                            │
│  ├── Call: reasoning.decompose(query, context, complexity) │
│  ├── LLM with few-shot examples                            │
│  └── Output: decomposition JSON                             │
│                                                              │
│  Phase 4: VERIFY [reasoning/]                               │
│  ├── Call: reasoning.verify(decomposition, option)         │
│  ├── Option A (self) or B (adversarial)                    │
│  ├── Retry loop (max 2 attempts) if score 0.5-0.7         │
│  └── Output: verification scores, verdict                   │
│                                                              │
│  Phase 5: ROUTE [SOAR only]                                 │
│  ├── Query agent_registry for each subgoal                 │
│  ├── Fallback to llm-executor if agent missing             │
│  └── Output: routing_plan                                   │
│                                                              │
│  Phase 6: COLLECT [SOAR only]                               │
│  ├── Execute agents (parallel where possible)              │
│  ├── Verify outputs (reasoning.verify_agent_output)        │
│  ├── Retry failed outputs (max 2 attempts)                 │
│  └── Output: agent_outputs (JSON envelopes)                │
│                                                              │
│  Phase 7: SYNTHESIZE [reasoning/]                           │
│  ├── Call: reasoning.synthesize(agent_summaries)           │
│  ├── LLM recomposes natural language answer                │
│  ├── Verify synthesis (reasoning.verify_synthesis)         │
│  └── Output: final_answer (natural language)               │
│                                                              │
│  Phase 8: RECORD [SOAR only]                                │
│  ├── If score >= 0.5: cache ReasoningChunk                 │
│  ├── If score >= 0.8: mark as pattern                      │
│  ├── Update activations (+0.2 success, -0.1 failure)       │
│  └── Output: cached (bool), chunk_id                        │
│                                                              │
│  Phase 9: RESPOND [SOAR only]                               │
│  ├── Format response by verbosity level                    │
│  ├── Log to conversation file (markdown)                   │
│  └── Output: final response + metadata                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 Verification Checkpoints

```
┌─────────────────────────────────────────────────────────────┐
│                  VERIFICATION CHECKPOINTS                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  CHECKPOINT 1: Decomposition Verification (Phase 4)         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Score >= 0.7 → PASS (proceed to execution)           │   │
│  │ Score 0.5-0.7 → RETRY (max 2, with feedback)         │   │
│  │ Score < 0.5 → FAIL (reject decomposition)            │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  CHECKPOINT 2: Agent Output Verification (Phase 6)          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Score >= 0.7 → PASS (accept output)                  │   │
│  │ Score 0.5-0.7 → RETRY (max 2, different agent if avail)│  │
│  │ Score < 0.5 → REJECT (try alternative agent)         │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  CHECKPOINT 3: Synthesis Verification (Phase 7)             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Score >= 0.8 → SUCCESS (cache pattern)               │   │
│  │ Score 0.7-0.8 → PARTIAL (return with caveats)        │   │
│  │ Score 0.5-0.7 → LOW CONFIDENCE (return with warnings)│   │
│  │ Score < 0.5 → FAIL (return partial results)          │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. QUALITY GATES & ACCEPTANCE CRITERIA

### 6.1 Code Quality Gates

| Gate | Requirement | Tool | Blocker |
|------|-------------|------|---------|
| **Code Coverage** | ≥85% for soar/, ≥85% for reasoning/ | pytest-cov | YES |
| **Type Checking** | 0 mypy errors (strict mode) | mypy | YES |
| **Linting** | 0 critical issues | ruff | YES |
| **Security** | 0 high/critical vulnerabilities | bandit | YES |
| **Prompt Validation** | All prompts enforce JSON-only output | Manual review | YES |

### 6.2 Performance Gates

| Metric | Target | Measurement | Blocker |
|--------|--------|-------------|---------|
| **Simple Query Latency** | <2s end-to-end | Benchmark | YES |
| **Complex Query Latency** | <10s end-to-end | Benchmark | YES |
| **Keyword Assessment** | <50ms | Benchmark | YES |
| **LLM Assessment** | <500ms | Benchmark | NO (warning) |
| **Verification Overhead** | <2x baseline LLM | Benchmark | NO (warning) |

### 6.3 Functional Acceptance Tests

**Each scenario MUST pass**:

#### Test Scenario 1: Simple Query (Direct Path)
```python
def test_simple_query_direct():
    """Simple query bypasses decomposition."""
    # GIVEN: Simple query
    query = "What is OAuth2?"

    # WHEN: Execute SOAR
    orchestrator = SOAROrchestrator(store, registry, config)
    result = orchestrator.execute(query)

    # THEN: Direct LLM path (no decomposition)
    assert result["metadata"]["complexity"] == "simple"
    assert "decomposition" not in result["reasoning_trace"]
    assert result["metadata"]["total_duration_ms"] < 2000
```

#### Test Scenario 2: Complex Query (Full Pipeline)
```python
def test_complex_query_full_pipeline():
    """Complex query uses full SOAR pipeline."""
    # GIVEN: Complex query
    query = "Implement OAuth2 authentication for our API"

    # WHEN: Execute SOAR
    result = orchestrator.execute(query)

    # THEN: Full pipeline executed
    assert result["metadata"]["complexity"] == "complex"
    assert "decomposition" in result["reasoning_trace"]
    assert len(result["reasoning_trace"]["decomposition"]["subgoals"]) >= 3
    assert result["metadata"]["verification_option"] == "option_b"
    assert result["overall_score"] >= 0.7
```

#### Test Scenario 3: Verification Catches Bad Decomposition
```python
def test_verification_catches_incomplete():
    """Verification catches incomplete decomposition."""
    # GIVEN: Forced incomplete decomposition (via mock)
    mock_llm.set_response("decompose", incomplete_decomposition_json)

    # WHEN: Execute SOAR
    result = orchestrator.execute("Build complex feature")

    # THEN: Verification catches issue, triggers retry
    assert result["reasoning_trace"]["decomposition_retries"] >= 1
    assert "completeness" in result["reasoning_trace"]["verification_issues"]
```

#### Test Scenario 4: Cost Tracking Works
```python
def test_cost_tracking():
    """Cost tracking records actual costs."""
    # GIVEN: Budget tracker initialized
    tracker = BudgetTracker(config)
    initial_consumed = tracker.get_status()["consumed_usd"]

    # WHEN: Execute query
    result = orchestrator.execute("Implement OAuth2")

    # THEN: Cost recorded
    final_consumed = tracker.get_status()["consumed_usd"]
    assert final_consumed > initial_consumed
    assert result["metadata"]["estimated_cost_usd"] > 0
```

#### Test Scenario 5: Agent Parallel Execution
```python
def test_parallel_agent_execution():
    """Parallelizable subgoals execute concurrently."""
    # GIVEN: Query with independent subgoals
    query = "Research 3 different OAuth providers"

    # WHEN: Execute SOAR
    with benchmark.measure("parallel_execution"):
        result = orchestrator.execute(query)

    # THEN: Execution time < sequential sum
    total_agent_time = sum(
        output["metadata"]["duration_ms"]
        for output in result["reasoning_trace"]["agent_outputs"]
    )
    actual_time = result["metadata"]["total_duration_ms"]
    assert actual_time < (total_agent_time * 0.8)  # At least 20% speedup
```

---

## 7. TESTING STRATEGY

### 7.1 Unit Tests

**MUST test each phase in isolation**:

**SOAR Package**:
- `test_orchestrator.py`: Main orchestrator flow
- `test_phase_assess.py`: Keyword + LLM assessment
- `test_phase_retrieve.py`: Context retrieval
- `test_phase_decompose.py`: Decomposition logic (calls reasoning/)
- `test_phase_verify.py`: Verification (calls reasoning/)
- `test_phase_route.py`: Agent routing
- `test_phase_collect.py`: Agent execution
- `test_phase_synthesize.py`: Synthesis (calls reasoning/)
- `test_phase_record.py`: ACT-R storage
- `test_phase_respond.py`: Response formatting

**Reasoning Package**:
- `test_assessment.py`: Complexity assessment
- `test_decompose.py`: Decomposition prompt building
- `test_verify.py`: Verification logic (A/B)
- `test_synthesize.py`: Synthesis logic
- `test_prompts.py`: Prompt template rendering
- `test_llm_client.py`: LLM client abstraction

**Core Package**:
- `test_reasoning_chunk.py`: ReasoningChunk implementation
- `test_cost_estimator.py`: Cost estimation
- `test_budget_tracker.py`: Budget enforcement
- `test_conversation_logger.py`: Log formatting

### 7.2 Integration Tests

**MUST test end-to-end flows**:

1. **Simple Query E2E**: Assess → Direct LLM → Respond
2. **Complex Query E2E**: All 9 phases with real LLM
3. **Verification Retry**: Bad decomposition → retry with feedback → pass
4. **Agent Execution**: Route → Execute → Verify outputs → Synthesize
5. **Cost Budget**: Pre-check → Execute → Record → Verify tracking

### 7.3 Performance Benchmarks

**MUST establish baselines**:

```python
def test_performance_benchmarks(benchmark_fixture):
    """Benchmark SOAR phases."""

    test_cases = [
        ("simple_query", "What is OAuth?", "simple", 2000),
        ("medium_query", "Compare OAuth1 vs OAuth2", "medium", 5000),
        ("complex_query", "Implement OAuth2 authentication", "complex", 10000),
    ]

    for name, query, expected_complexity, max_ms in test_cases:
        with benchmark_fixture.measure(f"query_{name}"):
            result = orchestrator.execute(query)

        benchmark_fixture.assert_performance(
            f"query_{name}",
            max_ms=max_ms
        )

        assert result["metadata"]["complexity"] == expected_complexity
```

### 7.4 Fault Injection Tests

**MUST test error handling**:

1. **Bad Decomposition**: Force low verification score, test retry logic
2. **Agent Failure**: Simulate agent error, test fallback
3. **LLM Timeout**: Simulate timeout, test graceful degradation
4. **Budget Exceeded**: Force budget limit, test blocking
5. **Malformed Output**: Send invalid JSON from agent, test validation

---

## 8. INTER-PHASE DEPENDENCIES

### 8.1 What Phase 2 Depends On (From Phase 1)

| Component | Phase 1 Interface | Usage |
|-----------|-------------------|-------|
| **Store** | `save_chunk()`, `get_chunk()`, `retrieve_by_activation()` | Phase 8 (RECORD) |
| **CodeChunk** | `to_json()`, `from_json()` | Phase 2 (RETRIEVE) |
| **AgentRegistry** | `list_agents()`, `get_agent()`, `find_by_capability()` | Phase 5 (ROUTE) |
| **Config** | `load()`, `get()`, `llm_config()` | All phases |
| **ContextProvider** | `retrieve()` | Phase 2 (RETRIEVE) |

### 8.2 What Phase 3 Depends On (From Phase 2)

| Component | Phase 2 Output | Phase 3 Usage |
|-----------|----------------|---------------|
| **ReasoningChunk** | Full implementation with tool tracking | ACT-R activation calculations |
| **Activation Storage** | `activations` table populated | Spreading activation, BLA formulas |
| **Verification Scores** | Historical scores stored | Learning rate adjustments |
| **Cost Tracking** | Budget tracker operational | Cost-aware activation boost |

### 8.3 Breaking Changes Policy

**Phase 2 guarantees**:
- SOAR orchestrator API stable: `execute(query, verbosity)`
- ReasoningChunk schema stable (frozen after Phase 2)
- Verification checkpoint scores stable (thresholds configurable)
- Agent response format stable (spec Section 7.2.1)

---

## 9. NON-GOALS (OUT OF SCOPE)

### 9.1 Explicitly NOT in Phase 2

| Feature | Why Not Now | When |
|---------|-------------|------|
| **Option C Verification** | Requires debate infrastructure | Phase 3 |
| **ACT-R Activation** | Formulas complex, foundation first | Phase 3 |
| **Spreading Activation** | Requires full ACT-R implementation | Phase 3 |
| **Multi-language Parsing** | Python sufficient for Phase 2 | Phase 3 |
| **Knowledge Context Provider** | API/schema retrieval not needed yet | Phase 3 |
| **Headless Mode** | Autonomous execution not critical | Phase 3 |
| **Memory Commands** | `aur mem` not needed until Phase 3 | Phase 3 |

### 9.2 Technical Constraints (Accepted for Phase 2)

- **No fine-tuning**: Use LLM APIs as-is
- **No caching optimization**: Simple TTL-based caching
- **No distributed execution**: Single-process only
- **No streaming responses**: Batch responses only
- **No real-time metrics**: Log-based metrics acceptable

---

## 10. TECHNICAL CONSIDERATIONS

### 10.1 LLM Prompt Engineering

**Critical Requirements**:
- All prompts MUST enforce JSON-only output
- NO markdown, NO explanation text outside JSON
- Include schema validation instructions in every prompt
- Use few-shot examples (scaled by complexity)
- Calibration examples prevent over-confident scoring

**Prompt Testing**:
- Test each prompt with 10 sample inputs
- Verify JSON parsing works 100% of time
- Check output matches expected schema
- Validate few-shot examples are relevant

### 10.2 Retry Logic & Exponential Backoff

**Retry Strategy**:
- Max 2 retries per checkpoint (decomposition, agent output, synthesis)
- Each retry includes feedback from previous attempt
- Exponential backoff for LLM API errors: 100ms, 200ms, 400ms
- Different retry counters for each checkpoint (independent loops)

**Feedback Format** (spec Section 8.7):
```json
{
  "retry_feedback": {
    "attempt": 2,
    "previous_score": 0.62,
    "issues": [
      {
        "check": "completeness",
        "score": 0.5,
        "issue": "Missing error handling subgoal",
        "suggestion": "Add subgoal for error scenarios"
      }
    ],
    "instruction": "Revise decomposition to include error handling"
  }
}
```

### 10.3 Parallel Execution Safety

**Thread Safety**:
- Use `asyncio` for parallel agent execution
- No shared mutable state between agents
- Each agent gets isolated context copy
- Results collected via queue (thread-safe)

**Timeout Handling**:
- Per-agent timeout: 60 seconds (configurable)
- Overall query timeout: 5 minutes (configurable)
- Graceful cancellation: save partial results on timeout

### 10.4 Error Handling Philosophy

**Error Categories**:

1. **Validation Errors** (user-fixable):
   - Invalid configuration
   - Budget exceeded
   - Response: Clear message + suggestion

2. **System Errors** (transient):
   - LLM API timeout
   - Agent unavailable
   - Response: Retry with backoff (max 3 attempts)

3. **Fatal Errors** (unrecoverable):
   - Invalid decomposition after 2 retries
   - All agents failed
   - Response: Return partial results + error explanation

**Graceful Degradation**:
- If verification fails: return unverified result with warning
- If agent fails: use fallback agent or skip subgoal
- If synthesis fails: return raw agent outputs
- Always provide partial results (never fail silently)

---

## 11. DELIVERY VERIFICATION CHECKLIST

**Phase 2 is complete when ALL items checked**:

### 11.1 Implementation Complete
- [ ] All 9 SOAR phases implemented
- [ ] Options A and B verification operational
- [ ] Keyword + LLM complexity assessment works
- [ ] Agent routing and execution reliable
- [ ] Cost tracking and budget enforcement functional
- [ ] ReasoningChunk fully implemented
- [ ] Conversation logging operational

### 11.2 Testing Complete
- [ ] Unit test coverage ≥85% for soar/, reasoning/
- [ ] All integration tests pass (5 scenarios)
- [ ] Performance benchmarks met (simple <2s, complex <10s)
- [ ] Fault injection tests pass (5 scenarios)
- [ ] Reasoning accuracy ≥80% on benchmark suite

### 11.3 Documentation Complete
- [ ] All SOAR phases documented with examples
- [ ] Verification checkpoint logic explained
- [ ] Agent response format documented
- [ ] Cost tracking guide written
- [ ] Troubleshooting guide for common errors

### 11.4 Quality Assurance
- [ ] Code review completed (2+ reviewers)
- [ ] Security audit passed
- [ ] Prompt engineering review completed
- [ ] Verification calibration validated
- [ ] Performance profiling completed

### 11.5 Phase 3 Readiness
- [ ] ReasoningChunk schema stable
- [ ] Activation storage schema ready
- [ ] Cost tracking baseline established
- [ ] Learning update hooks in place

---

## 12. OPEN QUESTIONS

### 12.1 Design Decisions

1. **Verification Strictness**
   - **Question**: Should failed verification block execution or just warn?
   - **Impact**: Safety vs usability tradeoff
   - **Recommendation**: Block on score <0.5, warn on 0.5-0.7, allow retry

2. **Parallel Execution Concurrency**
   - **Question**: Max concurrent agents? (3, 5, 10?)
   - **Impact**: Performance vs resource usage
   - **Recommendation**: Start with 5, make configurable

3. **Few-Shot Example Count**
   - **Question**: How many examples per complexity? (0/2/4/6 or 1/2/3/4?)
   - **Impact**: Prompt length vs guidance quality
   - **Recommendation**: 0/2/4/6 (spec Section 8, Appendix C.1)

### 12.2 Performance Tradeoffs

1. **Verification Overhead**
   - **Question**: Is 2-3x cost for verification acceptable?
   - **Tradeoff**: Reliability vs cost
   - **Recommendation**: YES - earned confidence worth the cost

2. **Retry Policy**
   - **Question**: Max 2 retries sufficient? Or allow 3?
   - **Tradeoff**: More chances vs longer latency
   - **Recommendation**: Max 2 (spec Appendix D)

---

## APPENDIX A: SAMPLE DECOMPOSITION

**Query**: "Implement OAuth2 authentication for our API"

**Decomposition JSON**:
```json
{
  "decomposition": {
    "id": "decomp-20251220-143215-abc123",
    "original_query": "Implement OAuth2 authentication for our API",
    "complexity": "complex",
    "given": [
      {"id": "G1", "fact": "Need OAuth2 authentication", "source": "query"},
      {"id": "G2", "fact": "Target is our API", "source": "query"}
    ],
    "goal": {
      "description": "Implement complete OAuth2 authentication system",
      "success_criteria": [
        "Token generation and validation working",
        "Integration tests passing",
        "Security best practices followed"
      ]
    },
    "subgoals": [
      {
        "id": "SG1",
        "description": "Research OAuth2 providers (Auth0, Okta, Custom)",
        "requires": ["G1"],
        "agent": "research-agent",
        "expected_output": "Comparison of providers with recommendation",
        "depends_on": []
      },
      {
        "id": "SG2",
        "description": "Design user model with OAuth fields",
        "requires": ["G1", "G2"],
        "agent": "code-developer",
        "expected_output": "User model schema with OAuth fields",
        "depends_on": ["SG1"]
      },
      {
        "id": "SG3",
        "description": "Implement token generation and validation",
        "requires": ["G1", "G2"],
        "agent": "code-developer",
        "expected_output": "Token management implementation",
        "depends_on": ["SG2"]
      },
      {
        "id": "SG4",
        "description": "Write integration tests for OAuth flow",
        "requires": ["G1", "G2"],
        "agent": "quality-assurance",
        "expected_output": "Passing integration tests",
        "depends_on": ["SG3"]
      }
    ],
    "execution_order": ["SG1", "SG2", "SG3", "SG4"],
    "parallelizable": []
  }
}
```

---

## APPENDIX B: VERIFICATION EXAMPLE

**Decomposition Verification Output**:
```json
{
  "verification": {
    "decomposition_id": "decomp-20251220-143215-abc123",
    "checks": {
      "completeness": {
        "score": 0.90,
        "pass": true,
        "issues": [],
        "detail": "All major aspects covered: research, data model, implementation, testing"
      },
      "consistency": {
        "score": 0.95,
        "pass": true,
        "issues": [],
        "detail": "No contradictions, clear dependency chain"
      },
      "groundedness": {
        "score": 0.85,
        "pass": true,
        "issues": [],
        "detail": "All subgoals trace to given facts (G1, G2)"
      },
      "routability": {
        "score": 0.90,
        "pass": true,
        "issues": [],
        "detail": "All agents exist in registry and have appropriate capabilities"
      }
    },
    "overall_score": 0.90,
    "verdict": "pass",
    "critical_issues": [],
    "suggestions": []
  }
}
```

---

## DOCUMENT HISTORY

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-12-20 | Initial PRD for Phase 2 SOAR Pipeline | Product Team |

---

**END OF PRD 0003: AURORA SOAR Pipeline & Verification**
