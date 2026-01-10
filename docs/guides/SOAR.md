# SOAR Reasoning Pipeline

AURORA's simplified 7-phase cognitive reasoning system for complex queries and goal decomposition.

## What is SOAR?

SOAR (State, Operator, And Result) is a cognitive architecture that breaks complex problems into structured phases. AURORA implements a streamlined 7-phase pipeline that automatically escalates based on complexity, with simplified paths for SIMPLE queries.

**SOAR powers two core workflows:**
1. **Query Answering** (`aur soar`) - Complex question answering with multi-turn reasoning
2. **Goal Decomposition** (`aur goals`) - Breaking high-level goals into actionable subgoals with agent assignments

This guide covers both use cases.

## When SOAR Activates

**Simple queries** (4 phases: assess → retrieve → synthesize → respond):
- Direct code search: "find UserService class"
- Simple lookups: "what does function X do?"
- Fast path bypasses decomposition, verification, and agent execution

**SOAR queries** (full 7-phase pipeline):
- Complex analysis: "How does the payment flow work?"
- System understanding: "Explain the authentication architecture"
- Planning queries: "What would it take to add feature X?"

Complexity is auto-detected. Use `aur soar "query"` to force SOAR mode.

## The 7 Phases

**Key improvements in simplified pipeline:**
- **Phases reduced:** 9 → 7 phases for MEDIUM/COMPLEX queries
- **Verify Lite:** Combines validation + agent assignment (eliminates separate routing phase)
- **Lightweight Record:** Minimal overhead caching with simple keyword extraction
- **Streaming Progress:** Real-time feedback during agent execution
- **Automatic Retry:** Spawner retries with fallback to LLM on agent failures

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

### Phase 4: Verify Lite (NEW - Combined Verification + Agent Assignment)
**Goal:** Validate decomposition AND assign agents in single phase

**Combines old Phase 4 (Verify) + Phase 5 (Route) into one lightweight check:**

1. **Validation checks:**
   - At least one subgoal exists
   - No circular dependencies in subgoal dependency graph
   - Required fields present (description, agent_id, etc.)
   - Valid decomposition structure

2. **Agent assignment:**
   - Match each subgoal's suggested agent_id to available agents
   - Create (subgoal_index, AgentInfo) assignment tuples
   - Detect missing agents early
   - Return issues list if agents not found

3. **Auto-retry on failure:**
   - If validation fails, generate retry feedback
   - Orchestrator calls decompose again with feedback
   - Maximum 2 retry attempts before failing

**Return format:** `(passed: bool, agent_assignments: list, issues: list)`

**Why combined?**
- Old Route phase was ~150 lines doing simple agent lookups
- Verification already had all decomposition context
- Combining eliminates phase transition overhead
- ~40% latency reduction for MEDIUM queries

### Phase 5: Collect (Enhanced with Streaming + Retry)
**Goal:** Execute agents and gather results with automatic retry and fallback

**New features:**
1. **Streaming progress output:**
   - Format: `[Agent 1/3] agent-id: Status`
   - Real-time status: "Starting...", "Completed (2.3s)", "Fallback to LLM (timeout)"
   - Multiple agents show multiple progress lines

2. **Automatic retry with fallback:**
   - Uses `spawn_with_retry_and_fallback()` from aurora_spawner
   - 3 retry attempts with exponential backoff
   - Automatic fallback to LLM if agent fails
   - Tracks which agents used fallback in metadata

3. **Increased timeout:**
   - Default timeout: 60s → 300s (5 minutes)
   - Accommodates complex agent tasks
   - Prevents premature timeouts on large codebases

4. **Direct agent assignments:**
   - Takes list of (subgoal_index, AgentInfo) tuples
   - No intermediate RouteResult structure
   - Simpler execution flow

### Phase 6: Synthesize
**Goal:** Integrate results into coherent answer

- Combines outputs from all subgoals
- Resolves conflicts between results
- Validates consistency
- Scores confidence in final answer

### Phase 7: Record (Lightweight Caching)
**Goal:** Cache successful reasoning patterns with minimal overhead

**Simplified lightweight implementation:**
1. **Simple keyword extraction:**
   - Extract top 10 keywords from query + summary
   - Filter common stop words
   - No complex NLP or embeddings

2. **Minimal data stored:**
   - SummaryRecord with id, keywords, summary, confidence, log_path
   - Truncated query (200 chars) and summary (500 chars)
   - No full execution trace or detailed metrics

3. **Fast caching decision:**
   - High confidence (≥0.8): Cache with +0.2 activation boost (pattern reuse)
   - Medium confidence (≥0.5): Cache with +0.05 activation boost (learning)
   - Low confidence (<0.5): Skip caching, no penalty

4. **Why lightweight?**
   - Old record_pattern: ~230 lines with complex heuristics
   - New record_pattern_lightweight: ~120 lines, simple logic
   - 10-15ms overhead vs 50-100ms previously
   - 95% of benefits with 20% of the code

### Phase 8: Respond
**Goal:** Format and deliver final answer

- Formats response for user
- Includes confidence scores
- Provides citations to source chunks
- Returns execution metadata

## Query Complexity Paths

SOAR adapts its execution path based on query complexity:

### SIMPLE Queries (4 phases)
**Path:** Assess → Retrieve → Synthesize → Respond

**Bypassed phases:** Decompose, Verify Lite, Collect, Record

**Example queries:**
- "find UserService class"
- "show login function"
- "what does calculate_total do?"

**Performance:** <500ms

### MEDIUM/COMPLEX Queries (7 phases)
**Path:** Assess → Retrieve → Decompose → Verify Lite → Collect → Synthesize → Record → Respond

**All phases executed with full reasoning pipeline**

**Example queries:**
- "Explain payment processing workflow"
- "How does authentication work?"
- "What would it take to add feature X?"

**Performance:** 5-20 seconds (depends on agent execution)

## Caching Policy

SOAR automatically caches successful reasoning patterns (Phase 7):

- **confidence >= 0.8:** Cache as reusable pattern (+0.2 activation boost)
- **confidence >= 0.5:** Cache for learning (+0.05 activation boost)
- **confidence < 0.5:** Skip caching (no penalty applied)

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
#   - Identify payment entry points (@full-stack-dev)
#   - Trace payment validation logic (@full-stack-dev)
#   - Map database transactions (@full-stack-dev)
#   - Document external API calls (@full-stack-dev)
# Phase 4: VERIFY LITE → PASS (all agents found, no circular deps)
# Phase 5: COLLECT → Executing 4 agents...
#   [Agent 1/4] full-stack-dev: Starting...
#   [Agent 1/4] full-stack-dev: Completed (3.2s)
#   [Agent 2/4] full-stack-dev: Starting...
#   [Agent 2/4] full-stack-dev: Completed (2.8s)
#   ...
# Phase 6: SYNTHESIZE → Combining 4 agent outputs
# Phase 7: RECORD → Cached reasoning pattern (confidence: 0.89)
# Phase 8: RESPOND → Formatting response
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
# Phase 4: VERIFY LITE → PASS (all agents found, no circular deps)
# Phase 5: (Skipped - goals mode doesn't execute agents)
# Phase 6: (Skipped - goals mode outputs goals.json instead)
# Phase 7: RECORD → Planning pattern cached
# Phase 8: RESPOND → Formatting goals.json
#
# ✅ Goals saved to .aurora/plans/0001-add-oauth2-auth/goals.json
```

**Key Differences:**

| Aspect | `aur soar` (Query) | `aur goals` (Decomposition) |
|--------|-------------------|---------------------------|
| **Input** | Question about existing code | Goal for new/changed functionality |
| **Output** | Natural language answer | Structured goals.json file |
| **Phases Used** | 4 (SIMPLE) or 7 (COMPLEX) | Phases 1-4, 7-8 (skips execution/synthesis) |
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
#     sg-5: Configure PCI compliance (@security-engineer)
# - Phase 4: VERIFY LITE → Validates decomposition + assigns agents
#     ✓ All agents found except security-engineer
#     ⚠ Gap detected: sg-5 has no matching agent
# - Phase 7: RECORD → Caches "payment integration" pattern
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
3. **Agent Matching:** Automatic capability-based assignment (Verify Lite phase)
4. **Gap Detection:** Identifies missing agent capabilities early
5. **Pattern Learning:** Caches successful decomposition patterns
6. **Fast Validation:** Lightweight verify_lite checks decomposition + assigns agents in one pass

## Performance

**Improvements in simplified pipeline:**
- **40% faster** for MEDIUM queries (combined verify + routing)
- **60% faster** record phase (lightweight caching)
- **30% better reliability** (automatic retry with fallback)

**Query Mode (`aur soar`):**
- **SIMPLE queries:** <500ms (4 phases: assess → retrieve → synthesize → respond)
- **MEDIUM queries:** 5-15 seconds (was 10-25s before simplification)
- **COMPLEX queries:** 15-45 seconds (depends on # of agents, execution time)
- **Caching:** Subsequent similar queries ~2-5 seconds (pattern reuse from Phase 7)

**Goals Mode (`aur goals`):**
- **Simple goals:** 2-4 seconds (was 2-5s)
- **Complex goals:** 8-20 seconds (was 10-30s, includes Verify Lite speedup)
- **With context:** +2-5 seconds (memory retrieval overhead)
- **Caching:** Similar goal patterns ~3-8 seconds (pattern reuse)

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
