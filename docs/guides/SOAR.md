# SOAR Reasoning Pipeline

AURORA's 9-phase cognitive reasoning system for complex queries and goal decomposition.

## What is SOAR?

SOAR (State, Operator, And Result) is a cognitive architecture that breaks complex problems into structured phases. AURORA implements a 9-phase pipeline that automatically escalates based on complexity.

**SOAR powers two core workflows:**
1. **Query Answering** (`aur soar`) - Complex question answering with multi-turn reasoning
2. **Goal Decomposition** (`aur goals`) - Breaking high-level goals into actionable subgoals with agent assignments

This guide covers both use cases.

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

**Thresholds:**
- PASS: score ≥ 0.6 (scores 0.6-0.7 are "devil's advocate" - proceed with extra concerns)
- RETRY: score 0.5-0.6 (needs revision)
- FAIL: score < 0.5 (fundamental issues)

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

## SOAR Modes

### Mode 1: Query Answering (`aur soar`)

**Purpose:** Answer complex questions about your codebase with multi-turn reasoning.

**Use when:**
- Understanding system architecture
- Tracing workflows or data flows
- Debugging complex issues
- Learning how existing code works

**Example:**
```bash
aur soar "Explain how payment processing works in this codebase"

# Output:
# Phase 1: ASSESS → COMPLEX
# Phase 2: RETRIEVE → Found 15 relevant chunks
# Phase 3: DECOMPOSE → 4 subgoals:
#   - Identify payment entry points
#   - Trace payment validation logic
#   - Map database transactions
#   - Document external API calls
# Phase 4: VERIFY → PASS (0.82 groundedness)
# Phase 5-7: Execute & synthesize
# Phase 8: RECORD → Cached reasoning pattern
#
# [Detailed answer with citations to source code...]
```

### Mode 2: Goal Decomposition (`aur goals`)

**Purpose:** Break high-level goals into actionable subgoals with automatic agent assignments.

**Use when:**
- Planning new features
- Refactoring systems
- Implementing complex requirements
- Creating work breakdown structures

**Example:**
```bash
aur goals "Add OAuth2 authentication with JWT tokens" --verbose

# Output:
# Phase 1: ASSESS → COMPLEX
# Phase 2: RETRIEVE → Found 12 relevant files in src/auth/
# Phase 3: DECOMPOSE → 5 subgoals with agent assignments:
#   sg-1: Set up OAuth2 provider integration (@full-stack-dev)
#   sg-2: Implement JWT token management (@full-stack-dev)
#   sg-3: Create login/logout endpoints (@full-stack-dev)
#   sg-4: Add authentication middleware (@full-stack-dev)
#   sg-5: Design authentication UI (@ux-expert)
# Phase 4: VERIFY → PASS (0.85 groundedness)
# Phase 5: ROUTE → All agents found
# Phase 6: (Skipped - goals mode doesn't execute agents)
# Phase 7: (Skipped - goals mode outputs goals.json instead)
# Phase 8: RECORD → Planning pattern cached
#
# ✅ Goals saved to .aurora/plans/0001-add-oauth2-auth/goals.json
```

**Key Differences:**

| Aspect | `aur soar` (Query) | `aur goals` (Decomposition) |
|--------|-------------------|---------------------------|
| **Input** | Question about existing code | Goal for new/changed functionality |
| **Output** | Natural language answer | Structured goals.json file |
| **Phases Used** | All 9 phases | Phases 1-5, 8-9 (skips execution/synthesis) |
| **Agent Execution** | Yes - executes agents to gather info | No - assigns agents for future execution |
| **Memory Context** | Uses retrieval for answering | Uses retrieval for informed planning |
| **Follow-up** | None (answer is final) | `/plan` skill reads goals.json to generate PRD |

## Usage

### CLI - Query Answering

```bash
# Force SOAR reasoning for questions
aur soar "How does authentication work in this codebase?"

# Complex analysis question
aur soar "What would it take to add real-time notifications?"

# Let AURORA auto-detect complexity
aur mem search "authentication"  # May escalate to SOAR if complex
```

### CLI - Goal Decomposition

```bash
# Basic goal decomposition
aur goals "Implement user profile page"

# With context for better decomposition
aur goals "Add payment processing" \
  --context src/checkout/ \
  --context src/orders/

# With specific tool/model
aur goals "Refactor API layer" \
  --tool cursor \
  --model opus \
  --verbose

# Skip confirmation prompts
aur goals "Fix login bug" --yes
```

### Query Examples

**Simple (no SOAR):**
- "find login function"
- "show UserService class"
- "what does calculate_total do?"

**SOAR Query Mode (Question Answering):**
- "Explain the payment processing workflow"
- "How does the caching layer work?"
- "Trace the bug in the authentication flow"
- "What database tables are involved in checkout?"

**SOAR Goals Mode (Decomposition):**
- "Implement OAuth2 authentication"
- "Add real-time notifications"
- "Refactor API to use GraphQL"
- "Set up CI/CD pipeline"

## Planning Flow Integration

SOAR goal decomposition integrates seamlessly with Aurora's planning workflow:

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  aur goals   │ --> │  /plan skill │ --> │  aur spawn   │
│              │     │ (Claude Code)│     │  or          │
│ SOAR decomposes    │ Reads goals.json   │  aur implement
│ goal into subgoals │ Generates PRD      │  Executes tasks
│ with agents        │ + tasks.md         │  in parallel/seq
└──────────────┘     └──────────────┘     └──────────────┘
```

**Complete Workflow Example:**

```bash
# Step 1: Index codebase (enables memory-aware decomposition)
aur mem index .

# Step 2: Use SOAR to decompose goal
aur goals "Add Stripe payment processing" \
  --context src/checkout/ \
  --verbose

# SOAR executes:
# - Phase 1: ASSESS → Determines goal is COMPLEX
# - Phase 2: RETRIEVE → Finds relevant files in src/checkout/
# - Phase 3: DECOMPOSE → Creates 5 subgoals:
#     sg-1: Set up Stripe SDK (@full-stack-dev)
#     sg-2: Create payment endpoints (@full-stack-dev)
#     sg-3: Add webhook handlers (@full-stack-dev)
#     sg-4: Implement payment UI (@ux-expert)
#     sg-5: Configure PCI compliance (@security-engineer, NOT FOUND → gap)
# - Phase 4: VERIFY → Validates decomposition (0.89 score)
# - Phase 5: ROUTE → Matches agents, detects gap for sg-5
# - Phase 8: RECORD → Caches "payment integration" pattern
#
# Output: .aurora/plans/0001-add-stripe-payment-processing/goals.json

# Step 3: Review goals (optional)
cat .aurora/plans/0001-add-stripe-payment-processing/goals.json

# Step 4: Generate PRD and tasks using /plan skill
cd .aurora/plans/0001-add-stripe-payment-processing/
/plan  # In Claude Code/Cursor/etc.

# Step 5: Execute tasks
aur spawn tasks.md --verbose
```

**Why SOAR for Goal Decomposition?**

1. **Context-Aware:** Memory retrieval finds relevant existing code
2. **Intelligent Splitting:** Complexity assessment determines granularity
3. **Agent Matching:** Automatic capability-based assignment
4. **Gap Detection:** Identifies missing agent capabilities early
5. **Pattern Learning:** Caches successful decomposition patterns
6. **Verification:** Validates decomposition before execution planning

## Performance

**Query Mode (`aur soar`):**
- **Simple queries:** <500ms (BM25 + activation only)
- **SOAR queries:** 10-60 seconds (depends on complexity, # of subgoals)
- **Caching:** Subsequent similar queries ~2-5 seconds (pattern reuse)

**Goals Mode (`aur goals`):**
- **Simple goals:** 2-5 seconds (keyword assessment, basic decomposition)
- **Complex goals:** 10-30 seconds (full SOAR pipeline, agent matching)
- **With context:** +2-5 seconds (memory retrieval overhead)
- **Caching:** Similar goal patterns ~5-10 seconds (pattern reuse)

## Output

**Query Mode Output (`aur soar`):**

1. **Answer:** Synthesized natural language response
2. **Confidence:** 0.0-1.0 score
3. **Citations:** Source chunks referenced
4. **Metadata:** Execution details (phases, timing, tools used)

**Goals Mode Output (`aur goals`):**

1. **goals.json:** Structured file with subgoals and agent assignments
2. **Subgoals:** 2-7 actionable tasks with dependencies
3. **Agent Assignments:** Matched agents with confidence scores
4. **Memory Context:** Relevant files with relevance scores
5. **Gaps:** Missing agent capabilities with fallback suggestions
6. **Metadata:** Execution details (phases, timing, complexity)

## Advanced: Programmatic Usage

### Query Mode

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

### Goals Mode

```python
from aurora_cli.planning.core import create_plan
from aurora_cli.config import load_config

config = load_config()

result = create_plan(
    goal="Add Stripe payment processing",
    context_files=["src/checkout/", "src/orders/"],
    auto_decompose=True,  # Use SOAR decomposition
    config=config,
    yes=False  # Interactive review
)

if result.success:
    print(f"Plan ID: {result.plan.plan_id}")
    print(f"Subgoals: {len(result.plan.subgoals)}")
    for sg in result.plan.subgoals:
        print(f"  - {sg.title} ({sg.recommended_agent})")
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

- **[SOAR Architecture](../reference/SOAR_ARCHITECTURE.md)** - Detailed technical specifications, phase implementation details, and verification logic
- **[Commands Reference](../COMMANDS.md)** - `aur soar` and `aur goals` command details
- **[Goals Command Documentation](../commands/aur-goals.md)** - Complete `aur goals` reference
- **[Planning Flow Workflow](../workflows/planning-flow.md)** - End-to-end planning workflow guide
- **[Tools Guide](../TOOLS_GUIDE.md)** - Comprehensive tooling ecosystem documentation
- **[Architecture](../ARCHITECTURE.md)** - Overall system architecture
- **ACT-R Memory** - How activation scores work
