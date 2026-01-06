# SOAR Reasoning Pipeline

AURORA's 9-phase cognitive reasoning system for complex queries.

## What is SOAR?

SOAR (State, Operator, And Result) is a cognitive architecture that breaks complex problems into structured phases. AURORA implements a 9-phase pipeline that automatically escalates based on query complexity.

## When SOAR Activates

**Simple queries** (use BM25 + activation only):
- Direct code search: "find UserService class"
- Simple lookups: "what does function X do?"

**SOAR queries** (multi-turn reasoning):
- Complex analysis: "How does the payment flow work?"
- System understanding: "Explain the authentication architecture"
- Planning queries: "What would it take to add feature X?"

Complexity is auto-detected. Use `aur soar "query"` to force SOAR mode.

## The 9 Phases

### Phase 1: Assess
**Goal:** Determine query complexity and requirements

- Analyzes query intent
- Classifies as SIMPLE, MEDIUM, COMPLEX, or CRITICAL
- Decides if SOAR pipeline is needed
- Routes to appropriate handler

### Phase 2: Retrieve
**Goal:** Gather relevant context from memory

- Searches indexed memory (code, kb, soar chunks)
- Uses hybrid retrieval (BM25 + activation + optional semantic)
- Retrieves top K relevant chunks
- Includes reasoning patterns from past queries

### Phase 3: Decompose
**Goal:** Break complex query into manageable subgoals

- Identifies sub-questions
- Creates dependency graph
- Determines execution order (parallel vs sequential)
- Assigns complexity to each subgoal

### Phase 4: Verify
**Goal:** Validate decomposition and check groundedness

- Checks if subgoals are answerable with available context
- Validates no circular dependencies
- Scores groundedness (prevents hallucination)
- May trigger re-retrieval if context insufficient

### Phase 5: Route
**Goal:** Assign subgoals to appropriate handlers

- Routes to specialized agents/tools
- Considers tool availability and capabilities
- Plans tool invocation sequence
- Optimizes for parallelization

### Phase 6: Collect
**Goal:** Execute subgoals and gather results

- Invokes agents/tools in planned order
- Collects outputs from each subgoal
- Handles errors and retries
- Aggregates intermediate results

### Phase 7: Synthesize
**Goal:** Integrate results into coherent answer

- Combines outputs from all subgoals
- Resolves conflicts between results
- Validates consistency
- Scores confidence in final answer

### Phase 8: Record
**Goal:** Cache successful reasoning patterns

- Stores reasoning pattern to memory
- Records tools used and execution order
- Updates activation scores
- Only caches patterns with success_score >= 0.5

### Phase 9: Respond
**Goal:** Format and deliver final answer

- Formats response for user
- Includes confidence scores
- Provides citations to source chunks
- Returns execution metadata

## Caching Policy

SOAR automatically caches successful reasoning patterns:

- **success_score >= 0.8:** Cache as reusable pattern (+0.2 activation boost)
- **success_score >= 0.5:** Cache for learning (+0.05 activation boost)
- **success_score < 0.5:** Skip caching, apply penalty (-0.1 activation)

Cached patterns are retrieved in Phase 2 for similar future queries.

## Usage

### CLI

```bash
# Force SOAR reasoning
aur soar "How does authentication work in this codebase?"

# Let AURORA auto-detect complexity
aur mem search "authentication"  # May escalate to SOAR if complex
```

### Query Examples

**Simple (no SOAR):**
- "find login function"
- "show UserService class"
- "what does calculate_total do?"

**SOAR-appropriate:**
- "Explain the payment processing workflow"
- "How do I add OAuth integration?"
- "What's the architecture of the caching layer?"
- "Trace the bug in the authentication flow"

## Performance

- **Simple queries:** <500ms (BM25 + activation only)
- **SOAR queries:** 10-60 seconds (depends on complexity, # of subgoals)
- **Caching:** Subsequent similar queries ~2-5 seconds (pattern reuse)

## Output

SOAR queries return:

1. **Answer:** Synthesized response
2. **Confidence:** 0.0-1.0 score
3. **Citations:** Source chunks referenced
4. **Metadata:** Execution details (phases, timing, tools used)

## Advanced: Programmatic Usage

```python
from aurora_soar import SOAROrchestrator

orchestrator = SOAROrchestrator(store=store, config=config)

result = orchestrator.query(
    query="How does the payment flow work?",
    complexity="COMPLEX"  # or "SIMPLE", "MEDIUM", "CRITICAL"
)

print(f"Answer: {result.answer}")
print(f"Confidence: {result.confidence}")
print(f"Phases: {result.phases_executed}")
```

## Configuration

SOAR behavior can be tuned via config (advanced):

```json
{
  "soar": {
    "max_subgoals": 10,
    "retrieval_top_k": 50,
    "min_groundedness_score": 0.6,
    "cache_threshold": 0.5
  }
}
```

## See Also

- [Commands Reference](../COMMANDS.md) - `aur soar` command details
- [Architecture](../docs/ARCHITECTURE.md) - SOAR implementation details
- ACT-R Memory - How activation scores work
