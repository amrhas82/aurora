# SOAR Pipeline Architecture

> **Note:** This is the detailed technical specification. For a high-level user guide, see [SOAR.md](../guides/SOAR.md).

## Overview

The SOAR (Sense, Organize, Act, Respond) pipeline is a simplified 7-phase orchestration system that implements adaptive reasoning for complex query handling and goal decomposition. It integrates ACT-R cognitive architecture principles with modern LLM capabilities.

**Key Simplifications (v0.6.3+):**
- **Phases reduced:** 9 → 7 for MEDIUM/COMPLEX queries
- **SIMPLE queries:** Fast path with only 4 phases (Assess → Retrieve → Synthesize → Respond)
- **Verify + Route combined:** Single lightweight `verify_lite` phase handles both validation and agent assignment
- **Lightweight Record:** Minimal overhead caching with simple keyword extraction
- **Performance:** 40% faster for MEDIUM queries, 60% faster record phase

## Execution Modes

SOAR supports two execution modes with different phase usage patterns:

### Mode 1: Query Answering (`aur soar`)
**Purpose:** Answer complex questions about existing code

**Phases Used:** 4 phases (SIMPLE) or 7 phases (MEDIUM/COMPLEX)

**SIMPLE queries (4 phases):**
1. ASSESS → Determine complexity (returns SIMPLE)
2. RETRIEVE → Gather context from memory
3. SYNTHESIZE → Direct LLM response with context
4. RESPOND → Format and deliver answer

**MEDIUM/COMPLEX queries (7 phases):**
1. ASSESS → Determine complexity
2. RETRIEVE → Gather context from memory
3. DECOMPOSE → Break into research subgoals
4. VERIFY LITE → Validate decomposition + assign agents (combined)
5. COLLECT → Execute agents to gather info (with streaming + retry)
6. SYNTHESIZE → Combine outputs into answer
7. RECORD → Cache reasoning pattern (lightweight)
8. RESPOND → Format and deliver answer

**Output:** Natural language answer with citations

### Mode 2: Goal Decomposition (`aur goals`)
**Purpose:** Break high-level goals into actionable subgoals

**Phases Used:** 1-4, 7-8 (skips execution/synthesis)
1. ASSESS → Determine goal complexity
2. RETRIEVE → Find relevant existing code
3. DECOMPOSE → Break into implementation subgoals
4. VERIFY LITE → Validate decomposition + assign agents (combined)
5. ~~COLLECT~~ → **Skipped** (agents not executed, only assigned)
6. ~~SYNTHESIZE~~ → **Skipped** (goals.json generated instead)
7. RECORD → Cache planning pattern (lightweight)
8. RESPOND → Format goals.json output

**Output:** Structured goals.json file for `/plan` skill

**Key Differences:**

| Aspect | Query Mode | Goals Mode |
|--------|-----------|------------|
| Phases Used | 4 (SIMPLE) or 7 (COMPLEX) | 1-4, 7-8 |
| Phase 3 Output | Research subgoals | Implementation subgoals |
| Phase 4 Output | Validated + agent assignments | Validated + agent assignments + gap detection |
| Phase 5 | Executes agents with retry | Skipped (no execution) |
| Phase 6 | Synthesizes answer | Skipped (outputs goals.json) |
| Final Output | NL answer + citations | Structured goals.json |
| Follow-up | None | `/plan` reads goals.json |

## Architecture Diagram (Simplified 7-Phase Pipeline)

```
┌─────────────────────────────────────────────────────────────────┐
│                   SOAR PIPELINE (Simplified)                     │
│                   9 phases → 7 phases (v0.6.3+)                  │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐
│ User Query   │
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 1: ASSESS                                                  │
│  - Tier 1: Keyword-based classification (60-70% queries)        │
│  - Tier 2: LLM verification (borderline cases)                  │
│  - Output: SIMPLE | MEDIUM | COMPLEX | CRITICAL                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │
       ┌───────────────────┴───────────────────┐
       │                                       │
       ▼ SIMPLE (Fast Path - 4 phases)        ▼ MEDIUM/COMPLEX (Full Pipeline - 7 phases)
┌──────────────────┐                    ┌─────────────────────────┐
│ Phase 2: RETRIEVE│                    │ Phase 2: RETRIEVE        │
│  - 5-20 chunks   │                    │  - Budget: 5-20 chunks   │
└────────┬─────────┘                    │  - ACT-R activation      │
         │                              └──────────┬───────────────┘
         ▼                                         │
┌──────────────────┐                              ▼
│ Phase 3: SYNTH.  │                    ┌─────────────────────────┐
│  - Direct LLM    │                    │ Phase 3: DECOMPOSE       │
└────────┬─────────┘                    │  - Few-shot examples     │
         │                              │  - JSON schema           │
         ▼                              │  - Auto-retry on fail    │
┌──────────────────┐                    └──────────┬───────────────┘
│ Phase 4: RESPOND │                               │
│  - Format output │                               ▼
└────────┬─────────┘                    ┌─────────────────────────┐
         │                              │ Phase 4: VERIFY LITE     │
         │                              │  (COMBINED VERIFY+ROUTE) │
         │                              │  - Validate structure    │
         │                              │  - Check circular deps   │
         │                              │  - Assign agents         │
         │                              │  - Max 2 retries         │
         │                              └──────────┬───────────────┘
         │                                         │
         │                                ┌────────┴────────┐
         │                                ▼ PASS            ▼ RETRY/FAIL
         │                      ┌─────────────────┐   ┌────────────┐
         │                      │ Phase 5: COLLECT │   │ Retry      │
         │                      │  - Streaming     │   │ Decompose  │
         │                      │  - Auto-retry    │   └─────┬──────┘
         │                      │  - LLM fallback  │         │
         │                      │  - 300s timeout  │   ◄─────┘
         │                      └────────┬─────────┘
         │                               │
         │                               ▼
         │                      ┌─────────────────────────┐
         │                      │ Phase 6: SYNTHESIZE      │
         │                      │  - Combine agent outputs │
         │                      │  - Traceability          │
         │                      └──────────┬───────────────┘
         │                                 │
         └─────────────────────────────────┤
                                           ▼
                                ┌─────────────────────────┐
                                │ Phase 7: RECORD          │
                                │  (LIGHTWEIGHT)           │
                                │  - Simple keywords       │
                                │  - Truncated storage     │
                                │  - Fast (10-15ms)        │
                                └──────────┬───────────────┘
                                           │
                                           ▼
                                ┌─────────────────────────┐
                                │ Phase 8: RESPOND         │
                                │  - Format output         │
                                │  - Verbosity levels      │
                                │  - Log conversation      │
                                └──────────┬───────────────┘
                                           │
                                           ▼
                                ┌─────────────────────────┐
                                │ Response to User         │
                                └──────────────────────────┘
```

**Key Changes:**
- **Phase 4 & 5 combined** → Single "Verify Lite" phase (validation + agent assignment)
- **SIMPLE path** → Only 4 phases (bypasses decompose, verify, collect, record)
- **Phase 5 (Collect)** → Enhanced with streaming, auto-retry, LLM fallback
- **Phase 7 (Record)** → Lightweight implementation (10-15ms vs 50-100ms)
- **Total:** 9 phases → 7 phases for complex queries

## Phase Details

> **Note:** This section describes the simplified 7-phase pipeline (v0.6.3+). Phase numbering has changed:
> - Phases 1-3: Unchanged (Assess, Retrieve, Decompose)
> - **Phase 4: NEW "Verify Lite"** - Combined verification + agent assignment (old Phases 4+5)
> - **Phase 5: "Collect"** - Enhanced with streaming + retry (was Phase 6)
> - **Phase 6: "Synthesize"** - Unchanged functionality (was Phase 7)
> - **Phase 7: "Record"** - Lightweight implementation (was Phase 8)
> - **Phase 8: "Respond"** - Unchanged functionality (was Phase 9)
> - **Removed: Old "Route" phase** - Functionality integrated into Verify Lite

### Phase 1: Assess (Complexity Assessment)

**Purpose**: Determine query complexity to optimize downstream processing.

**Inputs**:
- User query string
- Optional LLM client (for Tier 2)

**Outputs**:
- `complexity`: SIMPLE | MEDIUM | COMPLEX | CRITICAL
- `confidence`: 0.0-1.0
- `method`: "keyword" | "llm"
- `reasoning`: Explanation of classification

**Budget by Complexity**:
- SIMPLE: 5 chunks, $0.001 target
- MEDIUM: 10 chunks, $0.05 target
- COMPLEX: 15 chunks, $0.50 target
- CRITICAL: 20 chunks, $2.00 target

**Cost Optimization**:
- 60-70% queries use keyword-only (zero LLM cost)
- 30-40% use LLM verification (~$0.0002/query)
- Target: <$0.0001 average per assessment

### Phase 2: Retrieve (Context Retrieval)

**Purpose**: Retrieve relevant code and reasoning patterns from ACT-R memory.

**Inputs**:
- Query keywords
- Complexity level
- Store instance

**Outputs**:
- `code_chunks`: List of retrieved CodeChunk objects
- `reasoning_chunks`: List of retrieved ReasoningChunk objects
- `total_retrieved`: Count of chunks
- `retrieval_time_ms`: Timing metadata

**Retrieval Budget**:
- SIMPLE: 5 chunks
- MEDIUM: 10 chunks
- COMPLEX: 15 chunks
- CRITICAL: 20 chunks

**Early Exit for SIMPLE**:
If complexity is SIMPLE, skip phases 3-7 and go directly to solving LLM with retrieved context.

### Phase 3: Decompose (Query Decomposition)

**Purpose**: Break complex queries into actionable subgoals with agent routing.

**Inputs**:
- Query
- Complexity
- Retrieved context summary
- Available agents list
- Optional retry feedback (from verification failure)

**Outputs**:
- `goal`: High-level goal
- `subgoals`: List of subgoal dicts with:
  - `id`: Unique identifier
  - `description`: What needs to be done
  - `assigned_agent`: Suggested agent
  - `criticality`: HIGH | MEDIUM | LOW
  - `dependencies`: List of prerequisite subgoal IDs
- `execution_order`: List of execution phases:
  - `phase`: "sequential" | "parallel"
  - `subgoals`: List of subgoal IDs for this phase
- `expected_tools`: List of tool types likely needed

**Few-Shot Examples by Complexity**:
- SIMPLE: 0 examples (shouldn't reach this phase)
- MEDIUM: 2 examples
- COMPLEX: 4 examples
- CRITICAL: 6 examples

### Phase 4: Verify (Decomposition Verification)

**Purpose**: Validate decomposition quality before expensive agent execution, and assess retrieval quality to provide user guidance.

**Inputs**:
- Original query
- Decomposition result
- Verification option (A: self, B: adversarial)
- Retry count
- Optional `retrieval_context`: Contains `high_quality_count` and `total_chunks` from Phase 2
- Optional `interactive_mode`: Boolean flag (default: False)

**Outputs**:
- `completeness`: 0.0-1.0 (covers all query aspects?)
- `consistency`: 0.0-1.0 (subgoals compatible?)
- `groundedness`: 0.0-1.0 (grounded in context?)
- `routability`: 0.0-1.0 (agents exist and capable?)
- `overall_score`: Weighted average (0.4×C + 0.2×C + 0.2×G + 0.2×R)
- `verdict`: PASS | RETRY | FAIL
- `issues`: List of identified problems
- `suggestions`: List of improvements
- `retrieval_quality`: NONE | WEAK | GOOD (see below)

**Verification Options**:
- **Option A (Self-Verification)**: Used for MEDIUM queries
  - Same LLM reviews its own decomposition
  - Faster, cheaper (~$0.001/verification)
  - Good for routine queries

- **Option B (Adversarial)**: Used for COMPLEX/CRITICAL queries
  - Different LLM critiques decomposition
  - More rigorous, catches subtle issues
  - Higher cost (~$0.01/verification)
  - Required for security-critical queries

**Verdict Logic**:
- PASS: `overall_score ≥ 0.6` → Proceed to routing
  - Note: Scores in [0.60, 0.70) are "devil's advocate" territory - acceptable but warrant detailed explanation
  - Verification will include extra concerns and suggestions for these marginal cases
- RETRY: `0.5 ≤ overall_score < 0.6` AND `retry_count < 2` → Generate feedback, retry decomposition
- FAIL: `overall_score < 0.5` OR `retry_count ≥ 2` → Return error with issues

#### 4.1 Retrieval Quality Assessment

After verification completes, Phase 4 assesses the quality of retrieved context to guide users toward better results.

**Quality Levels**:

- **NONE**: `total_chunks == 0`
  - No indexed context available
  - Query proceeds automatically using LLM general knowledge
  - Phase 3 receives "No indexed context available. Using LLM general knowledge." message
  - No user interaction required

- **WEAK**: `groundedness < 0.7` OR `high_quality_chunks < 3`
  - Retrieved context exists but quality is questionable
  - Decomposition may not be well-grounded in actual codebase
  - In interactive mode (CLI only), user is prompted with 3 options:
    1. **Start anew** - Clear weak chunks, continue with general knowledge
    2. **Start over** - Abort query, user should rephrase
    3. **Continue** - Proceed with weak chunks (may produce generic results)
  - In non-interactive mode (MCP, headless, automation), automatically continues

- **GOOD**: `groundedness ≥ 0.7` AND `high_quality_chunks ≥ 3`
  - Retrieved context is high-quality and relevant
  - Decomposition is well-grounded in codebase
  - Query proceeds automatically
  - No user interaction required

**Decision Criteria**:

| Metric | Threshold | Meaning |
|--------|-----------|---------|
| `groundedness` | ≥ 0.7 | Decomposition claims are traceable to retrieved context |
| `high_quality_chunks` | ≥ 3 | At least 3 chunks have activation score ≥ 0.3 (ACT-R threshold) |
| `total_chunks` | > 0 | Context was retrieved (not empty) |

**Interactive Mode Behavior** (CLI with default settings):

When `interactive_mode=True` and quality is WEAK, user sees:
```
⚠ Warning: Retrieved context quality is weak
  Groundedness: 0.62 (target: ≥0.7)
  High-quality chunks: 2 (target: ≥3)

Options:
  1. Start anew - Clear weak matches, use general knowledge
  2. Start over - Rephrase query for better matches
  3. Continue - Proceed with weak matches (results may be generic)

Choice (1-3):
```

**Non-Interactive Mode** (MCP, headless, `--non-interactive` flag):
- WEAK quality → auto-continues silently
- No prompts displayed
- Retrieval quality metadata included in response for client-side handling
- Suitable for automation, CI/CD, programmatic usage

### Phase 5: Route (Agent Routing)

**Purpose**: Match subgoals to capable agents.

**Inputs**:
- Decomposition result (subgoals with suggested agents)
- Agent registry

**Outputs**:
- `agent_assignments`: List of (subgoal_index, agent_info) tuples
- `execution_plan`: Parsed execution order
- `routing_metadata`: Fallback info, warnings
- `gaps`: List of AgentGap objects (goals mode only)

**Routing Logic**:
1. Try suggested agent from decomposition
2. If not found, search by capability keywords
3. If still not found, fallback to `llm-executor` (generic agent)
4. Log warning if fallback used

#### 5.1 Agent Gap Detection (Goals Mode)

**New in Sprint 4:** `aur goals` uses enhanced routing with gap detection and LLM fallback.

**Gap Detection Algorithm**:

```python
def detect_gaps(subgoals, agent_recommendations):
    gaps = []
    for sg, (agent_id, confidence) in zip(subgoals, agent_recommendations):
        if confidence < 0.5:  # Low confidence threshold
            capabilities = extract_capabilities_from_subgoal(sg)
            gaps.append(AgentGap(
                subgoal_id=sg.id,
                suggested_capabilities=capabilities,
                fallback=DEFAULT_FALLBACK_AGENT  # @full-stack-dev
            ))
    return gaps
```

**Agent Matching with LLM Fallback**:

```python
async def recommend_agent_for_subgoal(subgoal):
    # 1. Keyword matching (fast, ~1ms)
    agent_id, score = keyword_match(subgoal, agent_registry)
    if score >= 0.7:
        return (agent_id, score)

    # 2. LLM classification (slow, ~500ms, $0.0002)
    if llm_client:
        agent_id, score = await llm_classify(subgoal, agent_registry)
        if score >= 0.5:
            return (agent_id, score)

    # 3. Fallback
    return (DEFAULT_FALLBACK_AGENT, score)
```

**Gap Detection Output Example**:

```json
{
  "gaps": [
    {
      "subgoal_id": "sg-5",
      "suggested_capabilities": [
        "PCI DSS compliance",
        "security audit",
        "penetration testing"
      ],
      "fallback": "@full-stack-dev"
    }
  ]
}
```

**User Feedback (Verbose Mode)**:
```
⚠️ sg-5: Configure PCI compliance (@security-engineer, NOT FOUND)
   Gap detected: Missing agent capabilities
   Suggested capabilities: ["PCI DSS compliance", "security audit"]
   Fallback: @full-stack-dev (review required)
```

**Benefits**:
- **Early Detection**: Identifies missing capabilities before implementation
- **Clear Guidance**: Suggests what capabilities are needed
- **Fallback Safety**: Provides workable alternative (@full-stack-dev)
- **User Choice**: User can install agent, split work, or accept fallback

### Phase 6: Collect (Agent Execution)

**Purpose**: Execute agents according to execution plan with parallelization.

**Inputs**:
- Agent assignments
- Execution plan (sequential/parallel phases)
- Per-agent timeout (default: 60s)
- Overall timeout (default: 5 minutes)

**Outputs**:
- `agent_outputs`: List of agent response dicts:
  - `subgoal_id`: Which subgoal this answers
  - `summary`: Natural language summary
  - `data`: Structured output data
  - `confidence`: 0.0-1.0
  - `tools_used`: List of tools invoked
  - `metadata`: Timing, model, etc.
- `execution_metadata`: Overall timing, parallelization stats

**Execution Modes**:
- **Sequential**: Execute dependencies first, wait for completion
- **Parallel**: Execute independent subgoals concurrently using `asyncio`

**Error Handling**:
- Agent timeout → Retry with different agent (if available)
- Agent failure → Max 2 retries, then mark as partial success
- Critical subgoal failure → Abort entire query
- Non-critical failure → Continue with graceful degradation

### Phase 7: Synthesize (Result Synthesis)

**Purpose**: Combine agent outputs into coherent final answer.

**Inputs**:
- Original query
- Agent outputs (summaries + data)
- Decomposition goal

**Outputs**:
- `answer`: Natural language synthesized answer
- `confidence`: Overall confidence 0.0-1.0
- `traceability`: List of claim-to-source mappings:
  - `claim`: Specific claim in answer
  - `source`: Which agent output(s) support it
  - `confidence`: Confidence in this claim
- `metadata`: Subgoals completed, files modified, interactions

**Verification**:
- Synthesis is verified for traceability (every claim links to agent output)
- If verification score < 0.7, retry synthesis with feedback (max 2 retries)

### Phase 8: Record (Pattern Caching)

**Purpose**: Cache successful reasoning patterns to ACT-R memory for future reuse.

**Inputs**:
- Query pattern
- Decomposition
- Agent outputs
- Success score

**Outputs**:
- `reasoning_chunk`: ReasoningChunk saved to ACT-R memory
- `cached`: Boolean indicating if cached

**Caching Policy**:
- `success_score ≥ 0.8`: Mark as reusable pattern
- `0.5 ≤ success_score < 0.8`: Cache but don't mark as pattern
- `success_score < 0.5`: Skip caching

**Learning Updates** (ACT-R activation):
- Success: +0.2 activation
- Partial success: ±0.05 activation
- Failure: -0.1 activation

### Phase 9: Respond (Response Formatting)

**Purpose**: Format final response according to verbosity level and log conversation.

**Inputs**:
- Synthesis result
- Phase data from all 9 phases
- Verbosity level

**Outputs** (by verbosity):

**QUIET**:
```
✓ Score: 0.85
```

**NORMAL**:
```
Phase 1: ASSESS → MEDIUM (keyword, 0.92 confidence)
Phase 2: RETRIEVE → 10 chunks (15ms)
Phase 3: DECOMPOSE → 3 subgoals (450ms)
Phase 4: VERIFY → PASS (0.78 score, self-verification)
Phase 5: ROUTE → 3 agents assigned
Phase 6: COLLECT → 3/3 completed (2.3s, 2 parallel)
Phase 7: SYNTHESIZE → 0.85 confidence (320ms)
Phase 8: RECORD → Cached as pattern
Score: 0.85
```

**VERBOSE**:
```
[Full trace with all metadata, timing, scores, issues, agent details]
```

**JSON**:
```json
{
  "phases": {
    "assess": {...},
    "retrieve": {...},
    ...
  },
  "overall_score": 0.85,
  "metadata": {...}
}
```

**Conversation Logging**:
- Asynchronously write markdown log to `~/.aurora/logs/conversations/YYYY/MM/`
- Filename: `keyword1-keyword2-YYYY-MM-DD.md`
- Contains: Query, all phase outputs, execution summary

## Cost Tracking

The SOAR pipeline tracks costs at every LLM call site:

1. **Budget Check (Pre-Query)**:
   - Check if estimated cost will exceed monthly budget
   - Soft limit at 80% (warning)
   - Hard limit at 100% (rejection)

2. **Cost Accumulation (During Execution)**:
   - Track input/output tokens per LLM call
   - Calculate cost using provider-specific pricing
   - Aggregate costs across all phases

3. **Cost Recording (Post-Query)**:
   - Save actual cost to `~/.aurora/budget_tracker.json`
   - Update monthly totals
   - Include cost breakdown in response metadata

**Pricing** (as of December 2024):
- Haiku 3.5: $0.80/$4.00 per MTok (input/output)
- Sonnet 4: $3.00/$15.00 per MTok
- Opus 4: $15.00/$75.00 per MTok

## Error Handling Patterns

### Validation Errors (User-Fixable)
- Clear error messages
- Suggestions for fixes
- Example of correct format

### System Errors (Transient)
- Retry with exponential backoff (100ms, 200ms, 400ms)
- Max 3 attempts
- Log errors for debugging

### Fatal Errors (Unrecoverable)
- Return partial results with explanation
- Include what succeeded before failure
- Suggest manual intervention steps

### Graceful Degradation
- Always return best-effort results
- Never fail silently
- Mark partial results clearly
- Explain what couldn't be completed

### Retrieval Quality Degradation
- **No Match (NONE)**: Automatically proceeds with LLM general knowledge, no user intervention
- **Weak Match (WEAK)**: In interactive mode, prompts user with clear options (start anew/over/continue); in non-interactive mode, auto-continues with weak context
- **Quality metadata**: Always included in verification results for observability and client-side decision making
- **Activation filtering**: Chunks with activation < 0.3 are tracked separately but not excluded (preserves context breadth)
- **User guidance**: Interactive prompts explain quality issues and provide actionable choices

## Performance Characteristics

### Latency Targets
- **Simple query**: <2s (keyword assessment + direct LLM)
- **Medium query**: <5s (2 phase verification, 2-3 agents)
- **Complex query**: <10s (adversarial verification, 4-6 agents, parallel execution)

### Throughput
- Keyword assessment: ~5000 queries/second
- LLM assessment: ~10 queries/second (rate limited)
- Agent execution: Variable (depends on parallelization)

### Memory Usage
- 10K CodeChunks: ~18 MB
- 10K ReasoningChunks: ~39 MB
- Total target: <100 MB for fully loaded memory

## Planning Flow Integration (Sprint 4)

SOAR goal decomposition integrates with Aurora's planning workflow to provide end-to-end feature development:

```
┌──────────────────────────────────────────────────────────────────┐
│                     PLANNING FLOW PIPELINE                         │
└──────────────────────────────────────────────────────────────────┘

┌──────────────┐
│  User Goal   │ "Add Stripe payment processing"
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│  aur goals (SOAR Mode 2: Goal Decomposition)                     │
│                                                                   │
│  Phase 1: ASSESS → COMPLEX                                       │
│  Phase 2: RETRIEVE → src/checkout/*.py (12 files, 0.89 avg rel) │
│  Phase 3: DECOMPOSE → 5 subgoals:                                │
│    sg-1: Set up Stripe SDK (@full-stack-dev)                     │
│    sg-2: Create payment endpoints (@full-stack-dev)               │
│    sg-3: Add webhook handlers (@full-stack-dev)                   │
│    sg-4: Implement payment UI (@ux-expert)                        │
│    sg-5: PCI compliance (@security-engineer, MISSING)             │
│  Phase 4: VERIFY → PASS (0.87 score)                             │
│  Phase 5: ROUTE → Agents matched, 1 gap detected                 │
│  Phase 8: RECORD → "payment integration" pattern cached          │
│  Phase 9: RESPOND → goals.json written                           │
│                                                                   │
│  OUTPUT: .aurora/plans/0001-add-stripe-payment/goals.json        │
└──────────────────────────┬────────────────────────────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ User reviews    │
                  │ goals.json in   │
                  │ $EDITOR         │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────────────┐
                  │  /plan skill             │
                  │  (Claude Code)           │
                  │                          │
                  │  READS: goals.json       │
                  │  GENERATES:              │
                  │    - prd.md (1200 lines) │
                  │    - tasks.md (24 tasks) │
                  └──────────┬───────────────┘
                             │
                             ▼
                  ┌─────────────────────────┐
                  │  aur spawn tasks.md     │
                  │  or                     │
                  │  aur implement          │
                  │                         │
                  │  EXECUTES: 24 tasks     │
                  │  across 3 agents        │
                  │  (5 parallel, rest seq) │
                  └──────────┬──────────────┘
                             │
                             ▼
                  ┌─────────────────────────┐
                  │  Completed Feature      │
                  │  ✓ All tests passing    │
                  │  ✓ Code committed       │
                  └─────────────────────────┘
```

**Data Flow:**

1. **goals.json Structure** (from Phase 9):
   ```json
   {
     "id": "0001-add-stripe-payment",
     "title": "Add Stripe payment processing",
     "subgoals": [...],  // From Phase 3
     "memory_context": [...],  // From Phase 2
     "gaps": [...]  // From Phase 5
   }
   ```

2. **/plan skill** reads goals.json and generates:
   - **prd.md**: Expands subgoals into full requirements
   - **tasks.md**: Creates actionable implementation tasks

3. **aur spawn** executes tasks with assigned agents

**Advantages of SOAR Integration:**

1. **Memory-Aware**: Phase 2 retrieval informs decomposition with existing code patterns
2. **Intelligent Granularity**: Phase 1 assessment determines appropriate subgoal count (2-7)
3. **Automatic Agent Matching**: Phase 5 routing finds best agents for each task
4. **Gap Detection**: Phase 5 identifies missing capabilities before implementation
5. **Pattern Learning**: Phase 8 caching improves future decomposition quality
6. **Verification**: Phase 4 validates decomposition before user commits time

## Integration Points

### Agent Integration
Agents must implement:
- `execute(subgoal, context) -> AgentOutput`
- Timeout handling (60s default)
- Error reporting with structured metadata

### Store Integration
Store must provide:
- `retrieve_by_activation(keywords, limit) -> List[Chunk]`
- `save_chunk(chunk) -> None`
- ACT-R activation updates

### LLM Integration
LLM clients must implement:
- `generate(prompt, **kwargs) -> LLMResponse`
- `generate_json(prompt, **kwargs) -> dict`
- Token counting and cost tracking hooks

### CLI Tool Integration (Sprint 4)
For `aur goals`, LLM clients support CLI piping:
- `CLIPipeLLMClient` wraps 20+ CLI tools (claude, cursor, aider, etc.)
- Prompts piped via stdin to subprocess
- Tool/model resolution: CLI flag → env → config → default
- Works with any tool that accepts `echo "prompt" | tool`

## Future Enhancements (Phase 3)

- Spreading activation for semantic retrieval
- Base-level learning decay
- Pattern-based query routing
- Adaptive timeout adjustment
- Multi-modal reasoning support
