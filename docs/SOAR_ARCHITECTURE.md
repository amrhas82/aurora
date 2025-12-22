# SOAR Pipeline Architecture

## Overview

The SOAR (Sense, Organize, Act, Respond) pipeline is a 9-phase orchestration system that implements adaptive reasoning for complex query handling. It integrates ACT-R cognitive architecture principles with modern LLM capabilities.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         SOAR PIPELINE                            │
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
       ▼ SIMPLE                                ▼ MEDIUM/COMPLEX/CRITICAL
┌──────────────┐                        ┌─────────────────────────┐
│ EARLY EXIT   │                        │ Phase 2: RETRIEVE        │
│ Direct LLM   │                        │  - Budget: 5-20 chunks   │
│ Response     │                        │  - ACT-R activation      │
└──────┬───────┘                        └──────────┬───────────────┘
       │                                           │
       │                                           ▼
       │                                  ┌─────────────────────────┐
       │                                  │ Phase 3: DECOMPOSE       │
       │                                  │  - Few-shot examples     │
       │                                  │  - JSON schema           │
       │                                  │  - Retry feedback        │
       │                                  └──────────┬───────────────┘
       │                                             │
       │                                             ▼
       │                                  ┌─────────────────────────┐
       │                                  │ Phase 4: VERIFY          │
       │                                  │  Option A: Self (MEDIUM) │
       │                                  │  Option B: Adversarial   │
       │                                  │    (COMPLEX/CRITICAL)    │
       │                                  │  - Max 2 retries         │
       │                                  └──────────┬───────────────┘
       │                                             │
       │                                    ┌────────┴────────┐
       │                                    │                 │
       │                                    ▼ PASS            ▼ RETRY/FAIL
       │                          ┌─────────────────┐   ┌────────────┐
       │                          │ Phase 5: ROUTE   │   │ Retry or   │
       │                          │  - Agent lookup  │   │ Degrade    │
       │                          │  - Fallbacks     │   └─────┬──────┘
       │                          └────────┬─────────┘         │
       │                                   │                   │
       │                                   │  ◄────────────────┘
       │                                   ▼
       │                          ┌─────────────────────────┐
       │                          │ Phase 6: COLLECT         │
       │                          │  - Sequential execution  │
       │                          │  - Parallel execution    │
       │                          │  - Timeout handling      │
       │                          └──────────┬───────────────┘
       │                                     │
       │                                     ▼
       │                          ┌─────────────────────────┐
       │                          │ Phase 7: SYNTHESIZE      │
       │                          │  - Combine agent outputs │
       │                          │  - Traceability          │
       │                          │  - Verification          │
       │                          └──────────┬───────────────┘
       │                                     │
       └─────────────────────────────────────┤
                                             ▼
                                  ┌─────────────────────────┐
                                  │ Phase 8: RECORD          │
                                  │  - Pattern caching       │
                                  │  - ACT-R learning        │
                                  │  - Activation updates    │
                                  └──────────┬───────────────┘
                                             │
                                             ▼
                                  ┌─────────────────────────┐
                                  │ Phase 9: RESPOND         │
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

## Phase Details

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

**Purpose**: Validate decomposition quality before expensive agent execution.

**Inputs**:
- Original query
- Decomposition result
- Verification option (A: self, B: adversarial)
- Retry count

**Outputs**:
- `completeness`: 0.0-1.0 (covers all query aspects?)
- `consistency`: 0.0-1.0 (subgoals compatible?)
- `groundedness`: 0.0-1.0 (grounded in context?)
- `routability`: 0.0-1.0 (agents exist and capable?)
- `overall_score`: Weighted average (0.4×C + 0.2×C + 0.2×G + 0.2×R)
- `verdict`: PASS | RETRY | FAIL
- `issues`: List of identified problems
- `suggestions`: List of improvements

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
- PASS: `overall_score ≥ 0.7` → Proceed to routing
- RETRY: `0.5 ≤ overall_score < 0.7` AND `retry_count < 2` → Generate feedback, retry decomposition
- FAIL: `overall_score < 0.5` OR `retry_count ≥ 2` → Return error with issues

### Phase 5: Route (Agent Routing)

**Purpose**: Match subgoals to capable agents.

**Inputs**:
- Decomposition result (subgoals with suggested agents)
- Agent registry

**Outputs**:
- `agent_assignments`: List of (subgoal_index, agent_info) tuples
- `execution_plan`: Parsed execution order
- `routing_metadata`: Fallback info, warnings

**Routing Logic**:
1. Try suggested agent from decomposition
2. If not found, search by capability keywords
3. If still not found, fallback to `llm-executor` (generic agent)
4. Log warning if fallback used

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

## Future Enhancements (Phase 3)

- Spreading activation for semantic retrieval
- Base-level learning decay
- Pattern-based query routing
- Adaptive timeout adjustment
- Multi-modal reasoning support
