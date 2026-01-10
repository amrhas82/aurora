# AURORA: Unified Technical Specification

**Purpose:** Single source of truth for AURORA implementation
**Audience:** Development team, architects, technical leads
**Status:** 🚧 IN PROGRESS - Section-by-section construction
**Version:** 1.0-draft
**Date:** December 20, 2025

**Note:** This is the definitive technical specification. For product requirements document (PRD), see separate PRD after this spec is complete.

---

## Document Purpose & Scope

This document consolidates 5 source documents (9,413 lines) into a single technical specification:

**Source Documents:**
1. `AURORA-Framework-PRD.md` (1,783 lines) - Original product requirements
2. `AURORA-Framework-SPECS.md` (1,535 lines) - Original technical specs
3. `AURORA-MVP-Correction.md` (2,700 lines) - Critical verification layer addition
4. `context-mind/ACT-R-Code-Context-Management-PRD.md` (2,331 lines) - Code context subsystem
5. `context-mind/ACT-R-Code-Context-Management-SPECS.md` (1,064 lines) - Code context algorithms

**Scope:**
- ✅ Complete architecture (all layers, subsystems, data flows)
- ✅ Implementation details (algorithms, pseudocode, data structures)
- ✅ Configuration schema (all settings, thresholds, parameters)
- ✅ Repository structure (folder hierarchy, module organization)
- ✅ Integration points (LLM providers, git, MCP, IDE hooks)
- ✅ Testing strategy (unit, integration, validation)
- ❌ Marketing content (competitive positioning, go-to-market)
- ❌ Financial projections (cost analysis, ROI calculations)
- ❌ User stories & acceptance criteria (see PRD after this)

---

# PART A: PRODUCT FOUNDATION

## 1. Executive Summary

### 1.1 The Core Problem

Large Language Models fail at complex, multi-step reasoning tasks despite impressive capabilities on simple queries. Three fundamental issues plague current AI systems:

**Issue 1: Orchestration ≠ Reasoning**

Breaking a problem into parts (decomposition) doesn't guarantee those parts are correct. Current orchestration frameworks assume:
- The decomposition is valid → **Not verified**
- Agent outputs are correct → **Not verified**
- The synthesis makes sense → **Not verified**

**Result:** Garbage in, garbage out. A bad decomposition wastes expensive agent compute.

**Issue 2: Code Context Bottleneck**

When working with large codebases (10k+ functions), AI systems face a token budget crisis:
- Semantic search finds 50 related functions
- Including all 50 = 100k+ tokens (too expensive)
- Picking 10 randomly = 40% include wrong functions
- No learning from success/failure patterns

**Result:** 40% of tokens wasted, 65-75% accuracy on code generation.

**Issue 3: No Genuine Learning**

Each query is treated independently. Systems don't:
- Remember what worked before
- Learn from failures
- Improve accuracy over time
- Adapt to user/domain patterns

**Result:** Same query tomorrow gets same (possibly wrong) answer.

### 1.2 The AURORA Solution

**AURORA** (Adaptive Universal Reasoning with Orchestrated Reasoning Architecture) solves these problems through **verification-driven reasoning** combined with **intelligent code context management**.

**Three core innovations:**

**Innovation 1: Verification Layer**

```
DECOMPOSE → VERIFY → AGENTS → VERIFY → RESPOND
    ↓         ↓         ↓         ↓
   LLM      LLM      WORK      LLM
(structure) (check) (solve)  (check)
```

- **Catches bad decompositions** before wasting agent compute (~$0.01 to catch vs $0.10 wasted)
- **Three verification levels:** Self-verify (cheap), Adversarial (robust), Deep reasoning (thorough)
- **Structured reasoning:** All decompositions in JSON format (parseable, traceable, auditable)
- **Self-correction:** Retry with feedback when verification fails

**Innovation 2: ContextMind - Intelligent Code Context**

```
Code Query → Semantic Search (find candidates)
           → ACT-R Activation (rank by importance)
           → Top-K Selection (5-10 functions)
           → LLM Context (inject into prompt)
```

- **cAST chunking:** Function-level (not file-level) for precision
- **Git integration:** Continuous activation signals from git history + polling
- **ACT-R prioritization:** Rank by actual importance (frequency + recency + relevance + dependencies)
- **Learning loop:** Improve from every code generation (Post-MVP)

**Innovation 3: Unified ACT-R Memory System**

Three specialized memory types:
1. **Knowledge Memory:** Facts, definitions, domain knowledge (long retention)
2. **Reasoning Memory:** Verified decomposition patterns (medium retention)
3. **Code Memory:** Function activations from git + usage (decay-based retention)

Each memory type has its own retention policy and learning signals.

### 1.3 Key Architectural Decisions

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| **Verification required for reasoning** | Orchestration alone doesn't catch logic errors | +$0.01-0.02 per query |
| **SOAR + Reasoning separated in repo** | Different concerns: problem structure vs verification logic | More modules to maintain |
| **Option C triggered by Option B failure** | Escalate only when adversarial verification fails twice | May retry unnecessarily |
| **JSON for all SOAR orchestration** | Parseable, traceable, auditable reasoning chains | Verbose logs |
| **Function-level code chunks (cAST)** | Files too coarse (10+ unrelated functions), need precision | More complex parsing |
| **Git as continuous signal source** | Already tracks everything, no new infrastructure needed | Coarse-grained (file-level) |
| **Three ACT-R memory types** | Different retention/decay needs for knowledge vs code | More complex memory management |
| **Learning deferred to Post-MVP** | Validate core verification first, then add intelligence | No improvement in MVP |

### 1.4 What AURORA Is NOT

To avoid confusion, AURORA explicitly does **NOT**:

❌ **Replace specialized agents** - AURORA orchestrates them, doesn't compete with them
❌ **Fine-tune LLMs** - Uses existing LLMs via API (QLoRA fine-tuning is Post-MVP)
❌ **Guarantee 100% accuracy** - Improves accuracy to 85-92%, not perfect
❌ **Solve all LLM problems** - Focused on reasoning + code context, not general AI
❌ **Require agent ecosystem** - Can run with LLM-only fallback mode

### 1.5 Target Operating Environment

**Primary:**
- Personal users experimenting with AI agents
- Small dev teams (3-50 engineers) with moderate codebases (500-5k functions)
- Software companies building AI-powered tools

**Secondary (Post-MVP):**
- Enterprise development teams (100-1000+ developers)
- AI research labs validating reasoning approaches
- Open-source projects with complex architectures

**Minimum Requirements:**
- Python 3.10+
- 8GB RAM (16GB recommended)
- LLM API access (Anthropic, OpenAI, or local model)
- Git installed (for code context features)
- 1GB disk space for memory + logs

---

## 2. Problem Statement

### 2.1 The Reasoning Failure

**Current State:** LLMs achieve 25-30% accuracy on complex, multi-step reasoning tasks requiring structured decomposition.

**Why They Fail:**

| Failure Mode | Description | Example |
|--------------|-------------|---------|
| **Attention degradation** | Each step compounds errors as model loses focus | Query: "Design migration from monolith to microservices" → LLM forgets constraint from step 2 by step 5 |
| **No working memory** | Can't maintain persistent state between inference calls | LLM can't remember "we decided on event-driven" from previous reasoning step |
| **Probability collapse** | When problem diverges from training distribution, token prediction unreliable | Novel architecture combination not in training data → hallucinated approach |
| **No verification** | Can't distinguish plausible-sounding from logically valid | LLM generates "use blockchain for caching" (sounds technical but nonsensical) |
| **Hallucination as feature** | Generates coherent text even without factual basis | LLM invents "AWS ServiceX" that doesn't exist |

**Critical Insight:** Decomposition doesn't solve reasoning - it just distributes the problem. If the LLM is unreliable at reasoning, asking it to propose decompositions means **the decomposition itself is unreliable**.

### 2.2 The Code Context Bottleneck

**Current State:** AI code assistants waste 40% of tokens on irrelevant context, achieving only 65-75% accuracy.

**The Problem:**

Developer asks: *"How do we validate credentials in authentication flow?"*

Semantic search finds 50 related functions:
- `authenticate()` ✓ Relevant
- `validate_password()` ✓ Relevant
- `check_session()` ✓ Relevant
- `deprecated_old_login()` ❌ Irrelevant (old code)
- `format_jwt_token()` ~ Maybe relevant
- `send_welcome_email()` ❌ Irrelevant (different concern)
- ... 44 more functions

**Current approaches:**
1. **Include all 50** → 100k+ tokens, $5 cost ❌
2. **Pick top 10 by similarity** → All scores 0.82-0.89, which 10? Often wrong ❌
3. **Use file-level chunks** → Entire auth.py (500 lines, 10 unrelated functions) ❌

**Result:** 40% of tokens spent on wrong context.

**Why This Happens:**
- Semantic similarity scores cluster (all "close enough")
- No understanding of actual importance (is this function frequently used? recently changed? on critical path?)
- Treats all code equally (deprecated function = actively maintained function)
- No learning from past successes/failures

### 2.3 The Learning Gap

**Current State:** Each query is processed independently. No accumulation of knowledge.

**Scenarios:**

**Scenario 1: Repeated Mistakes**
- Query: "Design caching strategy"
- LLM suggests Redis (wrong for this use case)
- User rejects, provides correct approach
- **Tomorrow:** Same query → Same wrong Redis suggestion

**Scenario 2: Successful Patterns Not Reused**
- Query: "Implement auth flow"
- LLM generates excellent solution using JWT + refresh tokens
- **Next week:** Similar auth query → LLM suggests different approach (worse quality)

**Scenario 3: Code Context Never Improves**
- Function `validate_token()` used in 50 successful code generations
- Function `deprecated_auth()` causes failures every time
- **Next query:** Both functions still ranked equally by semantic search

**Missing:**
- Memory of what worked
- Learning from failures
- Pattern recognition across queries
- Adaptation to user/domain preferences

---

## 3. Solution Overview

### 3.1 High-Level Architecture

AURORA combines three systems:

```
┌─────────────────────────────────────────────────────────────┐
│                     AURORA SYSTEM                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  CORE: Verification-Driven Reasoning                 │  │
│  │  DECOMPOSE → VERIFY → AGENTS → VERIFY → RESPOND      │  │
│  │  (Catches reasoning errors before wasting compute)   │  │
│  └──────────────────────────────────────────────────────┘  │
│                           ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  SUBSYSTEM: ContextMind (Code Intelligence)          │  │
│  │  cAST + Git + ACT-R → Smart Context Selection        │  │
│  │  (Reduces token waste from 40% to near-zero)         │  │
│  └──────────────────────────────────────────────────────┘  │
│                           ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  FOUNDATION: Unified ACT-R Memory                    │  │
│  │  3 Memory Types: Knowledge + Reasoning + Code        │  │
│  │  (Retrieves verified patterns, prioritizes by use)   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 The 7-Layer Architecture

AURORA processes queries through 7 distinct layers (SOAR and Reasoning are separate):

**Layer 0: Input Processing**
- Guardrails (PII detection, length limits)
- Cost budget pre-check
- Query normalization

**Layer 1: Assessment & Discovery**
- Complexity assessment (keyword + optional LLM)
- Agent registry discovery
- ContextMind activation (for code queries)

**Layer 2: Unified ACT-R Memory**
- Three memory types: Knowledge, Reasoning, Code
- Retrieve relevant patterns/context
- Activation-based ranking

**Layer 3: SOAR Problem-Space Reasoning**
- Decompose query into subgoals (JSON format)
- Evaluate operators (agent templates)
- Select execution order
- **Note:** Decomposition only, no verification here

**Layer 4: Verification Layer** ← CRITICAL INNOVATION
- Verify decomposition (Options A/B/C)
- Score 0-1 scale
- Retry with feedback if score < 0.7
- Escalate to Option C if Option B fails 2x

**Layer 5: Agent Orchestration**
- Route subgoals to agents
- Execute in parallel/sequential order
- Self-correction with configurable retries (2, 4, or 6 attempts)
- Verify agent outputs
- Timing logs per agent

**Layer 6: LLM Integration & Synthesis**
- LLM preference routing (fast/reasoning/best models)
- Provider abstraction (Anthropic, OpenAI, etc.)
- Synthesize final response
- Cost tracking

**Layer 7: Learning & Feedback** (Post-MVP)
- Capture user feedback (implicit: "thanks", follow-ups)
- Update ACT-R activations
- Store in Replay buffer (HER)
- Pattern caching (score ≥ 0.8)

### 3.3 Key Data Flows

**Flow 1: Simple Query (No Decomposition)**
```
User: "What's the capital of France?"
  → Layer 1: SIMPLE complexity
  → Skip Layers 3-4 (no decomposition needed)
  → Layer 6: Direct LLM call
  → Response: "Paris"
Cost: ~$0.001
```

**Flow 2: Complex Query (Full Pipeline)**
```
User: "Design migration from monolith to microservices"
  → Layer 1: COMPLEX
  → Layer 2: Retrieve past migration patterns (ACT-R)
  → Layer 3: SOAR decomposes into 5 subgoals (JSON)
  → Layer 4: Verify decomposition (Option B: adversarial)
       Score: 0.65 → RETRY with feedback
       Re-decompose → Score: 0.82 → PASS
  → Layer 5: Execute 5 agents (architecture, data, consistency, etc.)
       Agent 1 (architecture): Score 0.88 → PASS
       Agent 2 (data migration): Score 0.62 → RETRY (1 attempt)
       Agent 2 retry: Score 0.79 → PASS
       Agents 3-5: All PASS
  → Layer 4: Verify synthesis (Option B)
       Score: 0.85 → PASS
  → Layer 6: Synthesize final response
  → Layer 7: Cache pattern (score ≥ 0.8)
Cost: ~$0.50
```

**Flow 3: Code Query (With ContextMind)**
```
User: "How do we validate credentials in auth flow?"
  → Layer 1: CODE QUERY detected
  → Layer 2: ContextMind activation
       → cAST: Find all auth-related functions (50 candidates)
       → Git signals: Boost recently changed functions
       → ACT-R: Rank by importance
       → Top-10 selection: Only relevant functions
       → Tokens: 50k → 10k (80% reduction)
  → Layer 3: Simple decomposition (explain + show code)
  → Layer 4: Verify (Option A: self-verify) → PASS
  → Layer 5: Execute with smart context
  → Response with 10 relevant functions only
Cost: ~$0.15 (vs $0.40 without ContextMind)
```

### 3.4 What Makes AURORA Different

| Capability | Traditional Orchestration | AURORA |
|------------|---------------------------|--------|
| **Decomposition** | Assumes decomposition is correct | Verifies before executing |
| **Agent outputs** | Assumes outputs are correct | Verifies with scoring system |
| **Code context** | Semantic search only | Semantic + ACT-R activation |
| **Learning** | None | Three memory types with retention policies (Post-MVP) |
| **Cost optimization** | Fixed model selection | LLM preference routing by query |
| **Reasoning trace** | Plain text logs | Structured JSON contracts |
| **Self-correction** | Manual retry | Automatic retry with feedback |
| **Verification depth** | None | Options A/B/C by complexity |

---

## 4. Target Users & Value Propositions

### 4.1 Primary User Personas

AURORA serves two distinct user segments with different needs:

#### Persona Group A: AURORA Orchestration Users

**Persona A1: AI System Integrator ("Agent Coordinator")**
- **Profile**: Software engineer building multi-agent systems
- **Current Pain**:
  - Manual orchestration of 3-5 specialized agents is error-prone
  - No standard way to decompose complex tasks
  - Cost scaling unpredictable (every query hits LLM)
  - Agent coordination requires custom integration code
- **AURORA Solution**:
  - Automatic decomposition via SOAR (Layer 3)
  - Verification catches bad decompositions before execution (Layer 4)
  - Parallel/sequential agent orchestration (Layer 5)
  - Cost optimization via complexity assessment (Layer 1)
- **Success Metrics**:
  - 50% reduction in integration code
  - 30% cost savings
  - 92%+ accuracy on complex problems

**Persona A2: Domain Expert ("Knowledge Keeper")**
- **Profile**: Subject matter expert (analyst, researcher, consultant) using AI for complex analysis
- **Current Pain**:
  - Generic LLMs miss domain nuances
  - No way to teach system domain patterns
  - Repetitive context setup for multi-turn analysis
  - Same mistakes repeated daily
- **AURORA Solution**:
  - ACT-R memory stores domain patterns (Layer 2)
  - Learning from verified decompositions (Post-MVP Layer 7)
  - Multi-turn conversation threading
  - Pattern reuse across similar queries
- **Success Metrics**:
  - 2x faster analysis
  - Trustworthy automation (verifiable reasoning)
  - Accumulated domain expertise

**Persona A3: Data Analyst ("Insight Generator")**
- **Profile**: Non-technical user performing complex data-driven analysis
- **Current Pain**:
  - Multi-step analysis overwhelming
  - No visibility into how answers derived
  - Each project starts from scratch
- **AURORA Solution**:
  - Transparent reasoning via JSON contracts
  - Structured decomposition breaks complexity
  - Memory retrieval for similar past analyses
- **Success Metrics**:
  - 3x increase in analysis throughput
  - Confidence in AI-generated insights

#### Persona Group B: ContextMind Code Context Users

**Persona B1: AI Code Assistant Developer**
- **Profile**: Engineer building/maintaining code assistant platforms (Cursor, Cody, Claude Code integrations)
- **Current Pain**:
  - 40% of tokens wasted on irrelevant code context
  - Semantic search scores cluster (all 0.82-0.89, which 10?)
  - No learning from successful/failed generations
  - Cost scales linearly with codebase size
- **AURORA Solution**:
  - cAST function-level chunking (precise boundaries)
  - ACT-R activation ranking (frequency + recency + relevance)
  - Git integration for continuous signals
  - Learning loop improves accuracy 2-5% per session (Post-MVP)
- **Success Metrics**:
  - 40% token reduction
  - 92% code generation accuracy
  - $40k-$400k annual savings per enterprise

**Persona B2: Software Developer ("Code Explorer")**
- **Profile**: Developer working in large codebase (500-5k functions)
- **Current Pain**:
  - Semantic search returns 50 functions, manual filtering needed
  - Deprecated code ranked same as active code
  - No understanding of code importance/usage patterns
  - Token limits force excluding potentially relevant code
- **AURORA Solution**:
  - Smart context selection (only relevant functions)
  - Activation-based ranking (frequently used > deprecated)
  - Dependency-aware retrieval (spreading activation)
  - Automatic learning from git history
- **Success Metrics**:
  - 80%+ "system understands my codebase"
  - 5-10% faster development cycles
  - Fewer bugs from incomplete context

#### Secondary Support Personas

**Persona S1: DevOps/Operations**
- **Goals**: Monitor system health, understand cost drivers, optimize resource usage
- **AURORA Solution**: Cost budget enforcement, timing logs, LLM preference routing
- **Success Metric**: Predictable costs, clear performance dashboards

**Persona S2: Compliance/Audit**
- **Goals**: Maintain audit trails, ensure decision transparency
- **AURORA Solution**: Complete JSON audit trails for all reasoning chains
- **Success Metric**: Full traceability for compliance reviews

### 4.2 Value Propositions by Benefit

#### Cost Efficiency

**Orchestration Cost Reduction (40%)**
- **Mechanism**: Layer 1 assessment routes simple queries directly to LLM (skip decomposition overhead)
- **Cost breakdown**:
  - Simple queries (50%): ~$0.001 (direct LLM, no SOAR/verification)
  - Medium queries (30%): ~$0.05 (lightweight decomposition + Option A verification)
  - Complex queries (20%): ~$0.50 (full SOAR + Option B/C verification)
- **vs. Baseline**: LLM-only treats all as complex → ~$0.50 per query
- **Savings**: 50% × $0.499 + 30% × $0.45 = $0.38 average savings per query
- **At scale**: 1M queries/month = $380k annual savings

**Code Context Cost Reduction (40%)**
- **Mechanism**: ACT-R retrieves top-10 functions only (not all 50 candidates)
- **Token reduction**: 50k tokens → 10k tokens (80% reduction)
- **Cost impact**: $0.40 → $0.15 per code query
- **At scale**: 100k code queries/month = $300k annual savings

#### Accuracy Improvement

**Reasoning Accuracy: 85-92% (vs. 25-30% baseline)**
- **Verification prevents bad decompositions**: ~70% of decomposition failures caught pre-execution
- **Self-correction with feedback**: 2-6 retries improve success rate
- **Structured reasoning**: JSON format enforces logical structure
- **ACT-R memory**: Past patterns reduce cold-start failures

**Code Generation Accuracy: 92% (vs. 65-75% baseline)**
- **Precise context**: Function-level chunks eliminate irrelevant code noise
- **Activation ranking**: Frequently-used code prioritized over deprecated
- **Dependency awareness**: Spreading activation includes related functions
- **Learning loop (Post-MVP)**: Continuous improvement from feedback

#### Transparency & Auditability

**Complete Reasoning Trace**
- All decompositions logged in JSON format
- Verification scores and retry feedback captured
- ACT-R activation traces show why context was selected
- Agent execution timing and results stored

**Use Cases**:
- Debugging: Why did system choose this approach?
- Compliance: Audit trail for decision history
- Optimization: Identify bottlenecks in reasoning chain

#### Learning & Adaptation

**Accumulated Knowledge (Post-MVP)**
- **Knowledge Memory**: Facts, domain definitions (long retention)
- **Reasoning Memory**: Verified decomposition patterns (medium retention)
- **Code Memory**: Function usage patterns from git (decay-based)
- **Improvement velocity**: 2-5% accuracy gain per session (first 20 sessions)

**Business Impact**:
- Repeated queries answered faster (memory retrieval)
- Domain expertise accumulates automatically
- System adapts to user/project patterns

### 4.3 Value Proposition Summary Table

| Benefit Category | Metric | AURORA | Baseline | Improvement |
|------------------|--------|--------|----------|-------------|
| **Cost** | Avg cost per query | $0.12 | $0.50 | 76% reduction |
| **Cost** | Code query cost | $0.15 | $0.40 | 62% reduction |
| **Accuracy** | Reasoning accuracy | 85-92% | 25-30% | 3x improvement |
| **Accuracy** | Code generation | 92% | 65-75% | 25-35% improvement |
| **Speed** | Simple query | <1s | 2-3s | 3x faster |
| **Speed** | Complex query | 8-12s | 10+ min manual | 50-90x faster |
| **Learning** | Accuracy improvement | +2-5%/session | 0% | Continuous growth |
| **Transparency** | Audit trail | 100% | 0% | Full traceability |

---

## 5. Competitive Landscape & Positioning

### 5.1 Market Context

The AI reasoning and code assistant market is rapidly evolving:

**Market Segments**:
1. **LLM Providers** (Anthropic, OpenAI, Google) - Foundation models via API
2. **Orchestration Frameworks** (LangChain, LlamaIndex, Haystack) - Chaining and routing
3. **Code Assistants** (Cursor, Cody, GitHub Copilot, Claude Code) - AI-powered development
4. **Agent Platforms** (AutoGPT, BabyAGI, MetaGPT) - Autonomous multi-agent systems

**Market Pressures**:
- LLM API costs are 50-70% of operational budgets (driving cost optimization demand)
- Enterprises require audit trails and explainability (regulatory compliance)
- Code generation accuracy plateau at 70-75% (quality ceiling without better context)
- Multi-agent coordination remains manual (integration complexity)

### 5.2 Competitive Analysis

#### vs. LLM-Only Approaches (Claude, GPT-4, etc.)

| Aspect | LLM-Only | AURORA |
|--------|----------|--------|
| **Reasoning** | Single-pass token prediction | Structured decomposition + verification |
| **Accuracy** | 25-30% on complex tasks | 85-92% with verification |
| **Cost per query** | Fixed (~$0.50) | Variable ($0.001-$0.50, avg $0.12) |
| **Learning** | None (stateless) | ACT-R memory + learning loop (Post-MVP) |
| **Transparency** | None | Full JSON audit trail |
| **Multi-turn** | Context window only | Explicit threading + memory |

**AURORA Advantage**: Verification catches reasoning errors; cost optimization via complexity routing; accumulated knowledge.

**LLM Advantage**: Simpler integration; no infrastructure needed; broader general knowledge.

#### vs. Orchestration Frameworks (LangChain, LlamaIndex)

| Aspect | LangChain/LlamaIndex | AURORA |
|--------|----------------------|--------|
| **Reasoning** | Manual chains (developer-defined) | Automatic SOAR decomposition |
| **Verification** | None | Options A/B/C with scoring |
| **Code context** | Embedding-only | Embedding + ACT-R activation |
| **Learning** | None | Continuous (Post-MVP) |
| **Cost optimization** | No | Complexity-based routing |
| **Audit trail** | Manual logging | Automatic JSON contracts |

**AURORA Advantage**: Automatic reasoning decomposition; verification layer catches errors; intelligent code context; learning over time.

**Framework Advantage**: Mature ecosystem; broad LLM provider support; large community.

#### vs. Code Assistants (Cursor, Cody, GitHub Copilot)

| Aspect | Cursor/Cody/Copilot | AURORA ContextMind |
|--------|---------------------|---------------------|
| **Context selection** | Embedding-based only | Embedding + ACT-R activation |
| **Chunking** | File-level or token-split | Function-level (cAST) |
| **Code ranking** | Similarity score only | Activation (frequency + recency + relevance) |
| **Git integration** | None or basic | Continuous activation signals |
| **Learning** | None | Replay HER + activation updates (Post-MVP) |
| **Token efficiency** | 40% waste | Optimized (top-K only) |
| **Accuracy** | 65-75% | 92% |

**AURORA Advantage**: 40% token reduction; 92% accuracy; learning improves over time; git-native activation signals.

**Code Assistant Advantage**: IDE integration; real-time suggestions; established user base.

#### vs. Agent Platforms (AutoGPT, MetaGPT)

| Aspect | AutoGPT/MetaGPT | AURORA |
|--------|-----------------|--------|
| **Reasoning** | Prompt-based reflection | Structured SOAR cycles |
| **Verification** | Self-reflection only | Options A/B/C (adversarial + deep) |
| **Specialization** | Generic agents | Domain-specific agent orchestration |
| **Cost control** | None | Complexity routing + budgets |
| **Audit trail** | Logs only | Structured JSON contracts |
| **Code context** | None | Full ContextMind subsystem |

**AURORA Advantage**: Structured verification; cost optimization; specialized agent coordination; code context intelligence.

**Agent Platform Advantage**: Autonomous iteration; broader task scope (not limited to reasoning).

### 5.3 AURORA's Unique Position

**Three Differentiators**:

1. **Verification-Driven Reasoning**
   - Only system with explicit verification layer (Options A/B/C)
   - Catches bad decompositions before execution (~$0.01 to catch vs $0.10 wasted)
   - Adversarial verification (Option B) uses second LLM to critique
   - Deep reasoning (Option C) with multi-step chain-of-thought

2. **Intelligent Code Context Management**
   - Function-level chunking (cAST) for precision
   - ACT-R activation ranking (not just similarity scores)
   - Git-native continuous learning signals
   - 40% token reduction with 92% accuracy

3. **Unified Cognitive Architecture**
   - SOAR (structured reasoning) + ACT-R (memory/learning) + Verification
   - Three memory types (Knowledge, Reasoning, Code) with retention policies
   - JSON contracts for all orchestration (parseable, traceable, auditable)
   - Learning loop (Post-MVP) improves from every execution

**Market Positioning Statement**:

*"AURORA is the only AI reasoning platform that combines structured cognitive science (SOAR + ACT-R) with explicit verification and intelligent code context management, reducing operational costs 40% while improving accuracy to 85-92% on complex reasoning tasks and 92% on code generation."*

### 5.4 Strategic Advantages

**For Personal Users**:
- No need for expensive enterprise platforms
- Runs locally with any LLM provider
- Transparent reasoning builds trust
- Accumulated knowledge adapts to workflow

**For Small Dev Teams**:
- 40% cost savings matter ($40k-$100k annually)
- Smart code context improves quality (fewer bugs)
- No complex setup (git integration automatic)
- Scales to moderate codebases (500-5k functions)

**For AI Tooling Companies**:
- Differentiation in crowded code assistant market
- Provable accuracy improvement (92% vs 70-75% baseline)
- Cost reduction selling point for enterprise customers
- Extensible platform (integrate specialized agents)

---

**STATUS: Section 1-5 Complete (Part A: Product Foundation)**

**Completed sections:**
- ✅ Section 1: Executive Summary (Problem + Solution + Decisions)
- ✅ Section 2: Problem Statement (Reasoning + Code + Learning failures)
- ✅ Section 3: Solution Overview (7-layer architecture + data flows)
- ✅ Section 4: Target Users & Value Propositions (2 persona groups + 5 personas)
- ✅ Section 5: Competitive Landscape (vs. LLMs, frameworks, code assistants, agents)

**Next: Part B - Architecture & Design**
- Section 6: Complete Layer Architecture (Layers 0-7 detailed specifications)
- Section 7: ContextMind Subsystem (cAST + Git + ACT-R + Retrieval + Learning)
- Section 8: Verification Layer Details (Options A/B/C algorithms)
- Section 9: JSON Contracts & Data Structures
- Section 10: Scoring System & Thresholds
- Section 11: Self-Correction & Retry Logic

---

# PART B: ARCHITECTURE & DESIGN

## 6. Complete Layer Architecture

AURORA processes queries through 8 distinct stages (0-7), with SOAR and Reasoning/Verification as separate layers:

### Layer 0: Input Processing & Guardrails

**Purpose**: Validate, sanitize, and prepare incoming queries before processing.

**Components**:

1. **PII Detection & Redaction**
   - Scan for personally identifiable information
   - Redact or reject queries containing sensitive data
   - Log redactions for audit trail

2. **Length Limits & Format Validation**
   - Max query length: 10,000 characters (configurable)
   - UTF-8 encoding validation
   - Malformed input rejection

3. **Cost Budget Pre-Check**
   - Check user/project remaining budget
   - Estimate query cost based on length
   - Block or warn if budget insufficient
   - **Note**: Part of 6 newly added MVP features (placeholder for integration)

4. **Query Normalization**
   - Trim whitespace
   - Normalize unicode characters
   - Extract query metadata (timestamp, user_id, project_id)

**Outputs**:
- Sanitized query string
- Query metadata object
- Rejection reason (if blocked)

**Configuration** (from config.json):
```json
{
  "input_processing": {
    "max_query_length": 10000,
    "pii_detection_enabled": true,
    "cost_budget_check": true,
    "cost_budget_soft_limit": 100.00,
    "cost_budget_hard_limit": 500.00
  }
}
```

---

### Layer 1: Assessment & Discovery

**Purpose**: Classify query complexity and discover available agents/context.

**Components**:

1. **Hybrid Complexity Assessment**

   **Step 1: Keyword-based Assessment** (~50ms, free)
   - Match query against complexity taxonomy
   - Keywords organized by complexity level:
     - **SIMPLE** (0.9+ confidence): "what is", "define", "who is", factual queries
     - **MEDIUM** (0.5-0.9 confidence): "compare", "analyze", "explain", borderline
     - **COMPLEX** (<0.5 confidence): "design", "architect", "strategy", multi-step
   - Return confidence score (0-1 scale)

   **Step 2: LLM Verification** (only if 0.5-0.9 confidence, ~200ms, cheap)
   - Lightweight prompt: "Classify this query as SIMPLE, MEDIUM, or COMPLEX: {query}"
   - Constrained to <100 tokens
   - Cost: ~$0.001 per verification

   **Step 3: Full Assessment** (only if <0.5 confidence, ~2-3s, justified)
   - Detailed LLM analysis with reasoning
   - Provides preliminary decomposition hints
   - Cost: ~$0.01-0.02

2. **Agent Registry Discovery**
   - Query available agents from registry
   - Match agent capabilities to query domain
   - Return ranked list of candidate agents

3. **ContextMind Activation** (for code queries)
   - Detect code-related keywords ("function", "class", "implement", etc.)
   - Trigger cAST + git + ACT-R code context retrieval
   - Prepare code context for Layer 2

**Outputs**:
- Complexity classification: SIMPLE | MEDIUM | COMPLEX
- Confidence score (0-1)
- Available agents list
- Code context flag (boolean)

**Configuration** (from config.json):
```json
{
  "assessment": {
    "keyword_taxonomy_path": "./config/complexity_keywords.json",
    "llm_verification_threshold_low": 0.5,
    "llm_verification_threshold_high": 0.9,
    "full_assessment_enabled": true,
    "code_query_keywords": ["function", "class", "implement", "code", "debug"]
  }
}
```

---

### Layer 2: Unified ACT-R Memory

**Purpose**: Retrieve relevant patterns/context from three specialized memory types.

**Architecture**: Three memory types with different retention policies (inspired by MemOS paper concepts):

#### Memory Type 1: Knowledge Memory

**What it stores**: Facts, definitions, domain knowledge

**Retention policy**:
- **Long retention** (6-12 months)
- Tagged by security level: PUBLIC | INTERNAL | CONFIDENTIAL
- Path to source: Links to full Aurora conversation logs
- Configurable retention by tag in config.json

**Example entries**:
```json
{
  "chunk_id": "know_001",
  "type": "knowledge",
  "content": "OAuth 2.0 uses authorization code flow for web apps",
  "tags": ["security", "auth", "oauth"],
  "security_level": "PUBLIC",
  "source_log_path": "./logs/aurora_convo_2025_12_15_001.json",
  "created_at": "2025-12-15T10:30:00Z",
  "activation": 0.85,
  "retention_days": 365
}
```

#### Memory Type 2: Reasoning Memory

**What it stores**: Verified decomposition patterns from successful reasoning chains

**Retention policy**:
- **Medium retention** (3-6 months)
- Only stores patterns with verification score ≥ 0.8
- Links to full Aurora orchestration logs (JSON contracts)
- Decay based on reuse frequency

**Example entries**:
```json
{
  "chunk_id": "reas_042",
  "type": "reasoning",
  "pattern": "migration_strategy_decomposition",
  "subgoals": ["assess_current", "design_target", "plan_transition", "validate"],
  "verification_score": 0.87,
  "source_log_path": "./logs/aurora_reasoning_2025_12_10_042.json",
  "activation": 0.72,
  "retention_days": 180,
  "reuse_count": 12
}
```

#### Memory Type 3: Code Memory

**What it stores**: Function-level activation from git + usage patterns

**Retention policy**:
- **Decay-based retention** (power-law forgetting)
- Activation formula: `A = BLA + CB + SA - decay`
- Git + cAST integration provides continuous signals
- **Critical correction**: ACT-R sees what you're searching for (code/reasoning/knowledge)
  - Uses git + cAST to know which FILE and which LINES changed
  - Maps line-level changes → function-level activation (not all functions boosted equally)
  - Example: Git shows lines 45-52 changed in auth.py → cAST maps to `authenticate()` function [lines 45-60] → Only that function gets +0.26 activation

**Activation Formula** (from ContextMind specs):
```
A(chunk) = BLA + CB + SA - decay

BLA (Base-Level Activation):
  - Frequency: How often function modified (from git history)
  - Recency: Time since last modification
  - Formula: ln(Σ t_j^-d) where d = decay parameter (0.5)

CB (Context Boost):
  - Relevance to current query (keyword matching)
  - Relevance to current file being edited
  - Value: 0-0.3

SA (Spreading Activation):
  - Related functions already activated (via dependency graph)
  - Propagates activation through call graph
  - Value: 0-0.2

decay:
  - Time-based forgetting: -0.5 * log10(days_since_access)
  - Ensures unused code naturally cools
```

**Example entries**:
```json
{
  "chunk_id": "code_auth_001",
  "type": "code",
  "function_name": "authenticate",
  "file_path": "src/auth.py",
  "line_range": [45, 60],
  "language": "python",
  "activation": 0.92,
  "BLA": 0.80,
  "CB": 0.20,
  "SA": 0.15,
  "decay": -0.23,
  "git_commit_count": 47,
  "last_modified": "2025-12-19",
  "dependencies": ["validate_token", "check_session"]
}
```

#### Unified Retrieval Pipeline

**Input**: Query + complexity + code_flag
**Process**:
1. Semantic search across all 3 memory types
2. Rank by activation (ACT-R formula)
3. Filter by activation threshold (>0.5 for inclusion)
4. Top-K selection (K = 5-10 for reasoning, K = 10-20 for code)
5. Return context with activation trace

**Output**: Relevant chunks + activation scores + source paths

**Configuration** (config.json):
```json
{
  "memory": {
    "knowledge": {
      "retention_days_default": 365,
      "retention_by_tag": {
        "PUBLIC": 730,
        "INTERNAL": 365,
        "CONFIDENTIAL": 180
      },
      "source_logs_enabled": true
    },
    "reasoning": {
      "retention_days": 180,
      "min_verification_score": 0.8,
      "decay_enabled": true
    },
    "code": {
      "activation_threshold": 0.5,
      "decay_parameter": 0.5,
      "git_integration_enabled": true,
      "cAST_function_level": true,
      "BLA_weight": 1.0,
      "CB_weight": 0.3,
      "SA_weight": 0.2
    },
    "retrieval": {
      "top_k_reasoning": 10,
      "top_k_code": 20,
      "activation_min": 0.5
    }
  }
}
```

**MVP Status**:
- ✅ Activation formula in MVP (updates happen when chunks are accessed)
- ✅ Three memory types with retention policies in MVP
- ❌ Learning loop (Post-MVP, Layer 7)

---

### Layer 3: SOAR Problem-Space Reasoning

**Purpose**: Decompose complex queries into structured subgoals using SOAR cognitive architecture.

**Key Principle**: This layer does **decomposition only**, no verification (verification is Layer 4).

**SOAR Decision Cycle**:

```
┌─────────────────────────────────────────────────────────────┐
│                    SOAR CYCLE                                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. ELABORATE                                                │
│     → Query ACT-R memory for relevant patterns              │
│     → Extract givens from query + context                   │
│     → Define goal and success criteria                      │
│                                                              │
│  2. PROPOSE                                                  │
│     → Generate candidate subgoal decompositions             │
│     → Use LLM for semantic understanding                    │
│     → Apply SOAR production rules from memory               │
│                                                              │
│  3. DECIDE                                                   │
│     → Evaluate candidates (internal scoring)                │
│     → Commit to best decomposition                          │
│     → Detect impasses (no good candidates)                  │
│                                                              │
│  4. APPLY                                                    │
│     → Output decomposition as JSON contract                 │
│     → Determine execution order (sequential/parallel)       │
│     → Match subgoals to agents                              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**JSON Contract Output** (all SOAR orchestration in JSON format - logged for audit):

```json
{
  "decomposition": {
    "id": "uuid",
    "original_query": "Design migration from monolith to microservices",
    "complexity": "complex",

    "given": [
      {"id": "G1", "fact": "Current monolithic architecture", "source": "query"},
      {"id": "G2", "fact": "Need for scalability", "source": "context"}
    ],

    "goal": {
      "description": "Design complete migration strategy",
      "success_criteria": [
        "Target architecture defined",
        "Migration path specified",
        "Risk mitigation included"
      ]
    },

    "subgoals": [
      {
        "id": "SG1",
        "description": "Assess current architecture",
        "agent": "architecture-analyst",
        "expected_output": "Architecture assessment report",
        "depends_on": []
      },
      {
        "id": "SG2",
        "description": "Design target microservices architecture",
        "agent": "architecture-designer",
        "expected_output": "Target architecture design",
        "depends_on": ["SG1"]
      },
      {
        "id": "SG3",
        "description": "Plan migration strategy",
        "agent": "migration-planner",
        "expected_output": "Migration roadmap",
        "depends_on": ["SG1", "SG2"]
      }
    ],

    "execution_order": ["SG1", ["SG2"], "SG3"],
    "estimated_cost": 0.25
  }
}
```

**Impasse Detection**:
- **No operators available**: No agents match subgoal → fallback to LLM-only
- **Tie**: Multiple equally-scored decompositions → escalate to verification with both
- **Reject**: All candidates score too low → return error, suggest query refinement

**Outputs**:
- Decomposition JSON contract
- Execution order
- Agent assignments
- Estimated cost

**Configuration** (config.json):
```json
{
  "soar": {
    "production_rules_path": "./config/soar_rules.json",
    "max_subgoals": 10,
    "max_depth": 3,
    "impasse_handling": "fallback_llm",
    "json_logging_enabled": true,
    "json_logs_path": "./logs/soar/"
  }
}
```

**MVP Status**: ✅ Full SOAR decomposition in MVP (JSON output, logged)

---

### Layer 4: Verification Layer

**Purpose**: Verify decomposition quality and agent outputs before/after execution.

**Critical Innovation**: This is AURORA's core differentiation - catches reasoning errors before wasting compute.

**Two Verification Loops** (separate, don't loop back):

```
Loop 1: DECOMPOSE → VERIFY → PASS/RETRY
Loop 2: AGENTS → VERIFY → PASS/RETRY

These are TWO SEPARATE stages, not one continuous loop.
```

#### Option A: Self-Verification

**When**: SIMPLE or MEDIUM complexity queries
**How**: Same LLM reviews its own decomposition
**Cost**: ~$0.01 per verification
**Prompt**:
```
You decomposed this query into subgoals. Review your decomposition:

Original query: {query}
Your decomposition: {json}

Check:
1. Completeness: Do subgoals cover the full query?
2. Consistency: Are subgoals logically compatible?
3. Groundedness: Are subgoals achievable with available agents?

Score 0-1. Return: {score, issues, pass/retry}
```

**Limitations**: Same model, same blind spots

#### Option B: Adversarial Verification

**When**: COMPLEX queries OR when Option A fails
**How**: Second LLM (or different prompt) acts as skeptical critic
**Cost**: ~$0.02 per verification
**Prompt**:
```
Act as a skeptical critic. Another AI proposed this decomposition:

Original query: {query}
Proposed decomposition: {json}

Find flaws:
- Hidden assumptions
- Missing steps
- Logical leaps
- Alternative better decompositions

Score 0-1. Be harsh. Return: {score, critique, alternative}
```

**Trigger**: Escalate to Option B when:
- Complexity = COMPLEX (initial choice)
- Option A fails 2x (escalation path)

#### Option C: Deep Reasoning Verification (Post-MVP / Phase 2)

**When**: CRITICAL queries OR when Option B fails 2x
**How**: Multi-step chain-of-thought with RAG retrieval
**Cost**: ~$0.10 per verification
**Process**:
1. Retrieve similar patterns from reasoning memory
2. Multi-step CoT verification
3. Cross-reference with knowledge base
4. Generate detailed confidence report

**Configuration** (config.json):
```json
{
  "verification": {
    "option_a_enabled": true,
    "option_b_enabled": true,
    "option_c_enabled": false,
    "escalation_threshold_b": 0.7,
    "escalation_max_retries": 2,
    "option_b_trigger_on_failure": true
  }
}
```

#### Scoring System

**Scale**: 0.0 - 1.0

**Thresholds**:
- **≥ 0.8**: PASS + CACHE (store in reasoning memory)
- **≥ 0.7**: PASS (acceptable quality)
- **0.5 - 0.7**: RETRY (give feedback, re-decompose)
- **< 0.5**: FAIL (major issues, escalate or abort)

**Scoring Dimensions**:
1. **Completeness** (0-1): Do subgoals cover full query?
2. **Consistency** (0-1): Are subgoals logically compatible?
3. **Groundedness** (0-1): Are subgoals achievable?
4. **Routability** (0-1): Can subgoals map to available agents?

**Overall Score**: Weighted average (configurable weights)

**Self-Correction Flow**:

```
DECOMPOSE → VERIFY
             ↓
         Score < 0.7?
             ↓
            YES
             ↓
     Retry #1 (with feedback)
         DECOMPOSE → VERIFY
                      ↓
                  Score < 0.7?
                      ↓
                     YES
                      ↓
             Retry #2 (Option B)
                 VERIFY (adversarial)
                      ↓
                  Score < 0.7?
                      ↓
                     YES
                      ↓
          Escalate to Option C (Phase 2)
          OR FAIL with error message
```

**Configurable Retry Attempts** (config.json):
```json
{
  "retry": {
    "max_attempts": 4,
    "options": [2, 4, 6],
    "selected": 4
  }
}
```

**MVP Status**:
- ✅ Options A + B in MVP
- ✅ Self-correction with retry in MVP (configurable: 2, 4, or 6 attempts)
- ❌ Option C in Phase 2 (Post-MVP)

---

**STATUS: Section 6 Layer 0-4 Complete**

**Next: Continue Layer 5-7 + ContextMind subsystem details**
