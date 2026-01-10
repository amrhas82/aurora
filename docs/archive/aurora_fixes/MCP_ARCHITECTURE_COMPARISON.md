# MCP Architecture Comparison: Bash Wrapper vs Real Implementation

**Date**: 2025-12-28
**Purpose**: Compare two fundamental approaches to Aurora MCP integration

---

## User's Question

> "i have 2 ways in mind, and i need your help to compare"

### Option 1: MCP as Bash Wrapper
- MCP tools just call CLI commands via subprocess
- Need to change CLI to work without API key
- **Question**: What would MCP be in this case? Not really MCP?

### Option 2: MCP as Real Implementation
- Develop full SOAR in MCP (Path B)
- Two routing modes:
  - **Always-on**: Keyword-based complexity assessment
  - **Intentional**: "aur/aurora" keyword triggers
- Full CLI/MCP parity

---

## CONCRETE EXAMPLES: CLI vs MCP Behavior

Let me show you EXACTLY what happens with two real Aurora commands.

### Example 1: `aur query "what is SOAR reasoning?"`

This is a **complex query** that needs SOAR pipeline.

#### **CLI Behavior (Current - Working)**

```bash
$ aur query "what is SOAR reasoning?"
```

**Step-by-step execution**:

```
1. Parse command line
   Input: query="what is SOAR reasoning?"

2. Load configuration
   Read: ~/.aurora/config.json
   Config: {
     "api": {
       "provider": "anthropic",
       "default_model": "claude-sonnet-4"
     },
     "query": {
       "complexity_threshold": 0.6
     }
   }

3. Check API key
   Env: ANTHROPIC_API_KEY = "sk-ant-***"
   Status: ✓ Found

4. Initialize QueryExecutor
   Components:
   - SQLiteStore (database: ~/.aurora/aurora.db)
   - LLMClient (Anthropic, model: claude-sonnet-4)
   - CostTracker (budget: ~/.aurora/budget_tracker.json)

5. Assess complexity
   Query: "what is SOAR reasoning?"
   Keywords: ["what", "is", "reasoning"]
   Score: 0.43 (SIMPLE)
   Decision: Use Direct LLM (not SOAR)

6. Retrieve context from memory
   Hybrid search: "SOAR reasoning"
   Results: 5 chunks from codebase
   - orchestrator.py (lines 1-24): SOAR phases
   - assess.py: Complexity assessment
   - retrieve.py: Context retrieval

7. Execute Direct LLM
   API Call: Anthropic Claude Sonnet 4
   Prompt: "Based on this context: [5 chunks] ... what is SOAR reasoning?"

   [API Request]
   → Sending to api.anthropic.com
   → Input tokens: 2,341
   → Processing...

8. Receive answer
   [API Response]
   ← Output tokens: 487
   ← Cost: $0.0089

9. Display result
   ────────────────────────────────────────
   Answer:

   SOAR (Sense-Orient-Adapt-Respond) is a cognitive architecture
   used in Aurora for complex query processing. It consists of
   9 phases:

   1. Assess - Determine query complexity
   2. Retrieve - Get relevant context from memory
   3. Decompose - Break query into subgoals
   4. Verify - Validate decomposition quality
   5. Route - Assign agents to subgoals
   6. Collect - Execute agents and gather results
   7. Synthesize - Combine results into answer
   8. Record - Cache reasoning patterns
   9. Respond - Format final response

   [Based on: orchestrator.py:1-24, assess.py:45-67]

   ────────────────────────────────────────
   Execution: Direct LLM
   Duration: 2.3s
   Cost: $0.0089
   Tokens: 2,341 in / 487 out
   Budget remaining: $49.99
```

**User sees**:
- ✅ Full answer with sources
- ✅ Cost and timing info
- ✅ Execution path (Direct LLM)
- ✅ Clear, formatted output

---

#### **MCP Behavior (Current - Broken)**

```
User in Claude Code CLI: "what is SOAR reasoning?"
```

**Step-by-step execution**:

```
1. Claude (me) receives user message
   Input: "what is SOAR reasoning?"

2. Claude's internal decision process
   Available tools: aurora_search, aurora_query, aurora_index, ...
   Intent analysis: User asking about SOAR
   Decision: ⚠️ Might use aurora_query, might use my own knowledge

3. If Claude calls aurora_query:
   Tool call: aurora_query(query="what is SOAR reasoning?", limit=10)

4. MCP tool executes (NO SOAR, NO LLM)
   - Hybrid retrieval: "SOAR reasoning"
   - Returns: 5 chunks as JSON

5. MCP tool returns to Claude
   {
     "context": [
       {
         "file_path": "orchestrator.py",
         "content": "SOAR phases: Assess → Retrieve → ...",
         "score": 0.95
       },
       ...
     ],
     "assessment": {
       "complexity": 0.43,
       "confidence": 0.82
     }
   }

6. Claude (me) reads the JSON
   - I see 5 code chunks
   - I use MY knowledge + the chunks to answer
   - No SOAR pipeline execution
   - No Aurora LLM call

7. Claude responds to user
   "SOAR reasoning is a cognitive architecture used in Aurora.
   It consists of 9 phases: Assess, Retrieve, Decompose, ..."

   [Claude's answer based on chunks + my knowledge]
```

**User sees**:
- ✅ Answer (from Claude, not Aurora)
- ❌ No cost info (Aurora didn't call LLM)
- ❌ No execution path visibility
- ❌ No SOAR pipeline execution
- ❌ No indication Aurora was even used

**Problems**:
1. Aurora just did database search
2. Claude (me) did the reasoning, not Aurora's SOAR
3. No visibility into Aurora's process
4. Completely different from CLI behavior

---

#### **MCP Behavior (Option 1: Bash Wrapper)**

```
User: "aurora what is SOAR reasoning?"
```

**Step-by-step execution**:

```
1. Claude recognizes "aurora" keyword
   Trigger: "aurora" mentioned
   Decision: Call aurora() MCP tool

2. Claude calls MCP tool
   Tool call: aurora(query="what is SOAR reasoning?")

3. MCP tool executes (Bash wrapper)
   Code in tools.py:

   def aurora(query: str) -> str:
       """Invoke Aurora CLI via subprocess"""
       result = subprocess.run(
           ['aur', 'query', query],
           capture_output=True,
           text=True,
           env={'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY')}
       )
       return result.stdout

4. Subprocess spawns CLI
   Command: aur query "what is SOAR reasoning?"

   [Same as CLI behavior above - all 9 steps]

5. CLI returns output to MCP tool
   stdout = """
   ────────────────────────────────────────
   Answer:

   SOAR (Sense-Orient-Adapt-Respond) is a cognitive architecture...

   ────────────────────────────────────────
   Execution: Direct LLM
   Duration: 2.3s
   Cost: $0.0089
   """

6. MCP tool returns CLI output to Claude
   return result.stdout

7. Claude shows user the CLI output
   [Displays the formatted CLI output as-is]
```

**User sees**:
- ✅ Full CLI output (same as running `aur query` directly)
- ✅ Cost and timing info
- ✅ Execution path
- ⚠️ CLI-formatted output (not Claude's natural formatting)
- ⚠️ No indication it was an MCP tool

**Problems**:
1. Subprocess overhead (~100-200ms)
2. Just a wrapper around CLI
3. Can't leverage MCP features (structured returns)
4. User might as well run `aur query` directly
5. Requires API key in environment

**Question**: Is this really MCP, or just a CLI alias?

---

#### **MCP Behavior (Option 2: Real SOAR in MCP)**

```
User: "aurora what is SOAR reasoning?"
```

**Step-by-step execution**:

```
1. Claude recognizes "aurora" keyword (intentional mode)
   OR
   Any query triggers aurora_query (always-on mode)

2. Claude calls MCP tool
   Tool call: aurora_query(
       query="what is SOAR reasoning?",
       mode="auto",  # or force_soar=False
       verbose=True
   )

3. MCP tool initializes (REAL SOAR)
   Components:
   - LLMClient (Anthropic, using MCP-provided API key)
   - SOAROrchestrator
   - CostTracker
   - SQLiteStore

4. Assess complexity
   Query: "what is SOAR reasoning?"
   Score: 0.43 (SIMPLE)
   Decision: Direct LLM path

5. Retrieve context
   Hybrid search: "SOAR reasoning"
   Results: 5 chunks

6. Execute Direct LLM (via MCP's LLM client)
   [Streaming progress to Claude]

   Phase: Assess
   ├─ Complexity: 0.43 (SIMPLE)
   └─ Route: Direct LLM

   Phase: Retrieve
   ├─ Found: 5 chunks
   ├─ Avg score: 0.92
   └─ Confidence: HIGH

   Phase: Respond
   ├─ Calling LLM...
   ├─ Input tokens: 2,341
   └─ Output tokens: 487

7. MCP tool returns structured response
   {
     "answer": "SOAR (Sense-Orient-Adapt-Respond) is...",
     "execution_path": "direct_llm",
     "phases": [
       {"name": "Assess", "duration": 0.12, "status": "completed"},
       {"name": "Retrieve", "duration": 0.45, "status": "completed"},
       {"name": "Respond", "duration": 2.1, "status": "completed"}
     ],
     "cost": {
       "total_usd": 0.0089,
       "input_tokens": 2341,
       "output_tokens": 487
     },
     "sources": [
       {"file": "orchestrator.py", "lines": "1-24", "score": 0.95}
     ],
     "metadata": {
       "complexity_score": 0.43,
       "retrieval_confidence": 0.92,
       "duration_seconds": 2.3
     }
   }

8. Claude formats response for user
   Based on Aurora's analysis, SOAR reasoning is a cognitive
   architecture with 9 phases used for complex query processing...

   Sources:
   - orchestrator.py (lines 1-24)

   Aurora execution:
   • Path: Direct LLM
   • Duration: 2.3s
   • Cost: $0.0089
   • Tokens: 2,341 → 487
```

**User sees**:
- ✅ Aurora's answer (via SOAR/Direct LLM)
- ✅ Declarative phase information
- ✅ Cost and timing
- ✅ Sources from codebase
- ✅ Clear execution path
- ✅ Claude's natural formatting

**Advantages**:
1. Real SOAR pipeline execution
2. Full CLI/MCP parity
3. Structured data for Claude to format
4. Visibility into Aurora's process
5. Native MCP integration

---

### Example 2: `aur mem search "hybrid retrieval"`

This is a **simple search** that doesn't need SOAR or LLM.

#### **CLI Behavior (Current - Working)**

```bash
$ aur mem search "hybrid retrieval"
```

**Step-by-step execution**:

```
1. Parse command
   Input: search="hybrid retrieval"

2. Load configuration
   Read: ~/.aurora/config.json

3. Connect to database
   Database: ~/.aurora/aurora.db
   Status: ✓ Connected (6,277 chunks)

4. Execute hybrid retrieval
   Algorithm: 60% activation + 40% semantic

   Activation scores:
   - hybrid_retriever.py: 0.95 (frequently accessed)
   - embedding_provider.py: 0.82
   - retrieval.py: 0.78

   Semantic scores:
   - hybrid_retriever.py: 0.91 (high similarity)
   - embedding_provider.py: 0.85
   - retrieval.py: 0.79

   Hybrid scores:
   - hybrid_retriever.py: 0.93 (0.6×0.95 + 0.4×0.91)
   - embedding_provider.py: 0.83
   - retrieval.py: 0.79

5. Sort by hybrid score
   Top 5 results

6. Display results
   ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
   ┃ File                      ┃ Type     ┃  Score ┃
   ┡━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━┩
   │ hybrid_retriever.py       │ code     │  0.930 │
   │ embedding_provider.py     │ code     │  0.834 │
   │ retrieval.py              │ code     │  0.786 │
   │ test_hybrid_retriever.py  │ code     │  0.721 │
   │ assess.py                 │ code     │  0.689 │
   └───────────────────────────┴──────────┴────────┘

   Average scores:
     Activation: 0.842
     Semantic:   0.851
     Hybrid:     0.792

   Duration: 0.12s
```

**User sees**:
- ✅ Ranked results with scores
- ✅ Clear table formatting
- ✅ Score breakdown (activation, semantic, hybrid)
- ✅ Fast (<200ms)
- ❌ NO LLM call
- ❌ NO API key needed

---

#### **MCP Behavior (Current - Works, but broken activation)**

```
User: "search for hybrid retrieval in Aurora"
```

**Step-by-step execution**:

```
1. Claude recognizes search intent
   Intent: Search codebase
   Decision: Call aurora_search() MCP tool

2. Claude calls MCP tool
   Tool call: aurora_search(query="hybrid retrieval", limit=5)

3. MCP tool executes hybrid retrieval
   [Same algorithm as CLI: 60% activation + 40% semantic]

   Problem: ALL activation scores = 0.0 (bug!)

   Activation scores:
   - All chunks: 0.0 (never accessed, never tracked)

   Semantic scores:
   - hybrid_retriever.py: 0.91
   - embedding_provider.py: 0.85
   - retrieval.py: 0.79

   Hybrid scores (BROKEN):
   - All: ~0.36-0.37 (0.6×0.0 + 0.4×semantic)
   - Nearly identical due to 0 activation

4. MCP tool returns JSON
   {
     "results": [
       {
         "file_path": "hybrid_retriever.py",
         "function_name": "HybridRetriever.retrieve",
         "content": "def retrieve(self, query: str, top_k: int = 10)...",
         "score": 0.364,
         "chunk_id": "code:hybrid_retriever.py:HybridRetriever.retrieve"
       },
       ... (all with similar scores due to bug)
     ]
   }

5. Claude formats results
   I found these files related to hybrid retrieval:

   1. hybrid_retriever.py - HybridRetriever.retrieve()
   2. embedding_provider.py - EmbeddingProvider
   3. retrieval.py - retrieval logic

   [Claude's formatting, based on JSON]
```

**User sees**:
- ✅ Results from Aurora
- ⚠️ Claude's formatting (not Aurora's table)
- ❌ ALL scores ~0.36 (bug - activation tracking broken)
- ❌ No score breakdown visibility
- ❌ No clear indication Aurora was used

**Problems**:
1. Activation tracking bug (all scores 0.0)
2. Results have identical scores
3. Search quality degraded
4. No visibility into scoring algorithm

---

#### **MCP Behavior (Option 1: Bash Wrapper)**

```
User: "aurora search for hybrid retrieval"
```

**Step-by-step execution**:

```
1. Claude recognizes "aurora search"
   Trigger: "aurora" + "search"
   Decision: Call aurora_search() MCP tool

2. Claude calls MCP tool
   Tool call: aurora_search(query="hybrid retrieval")

3. MCP tool calls CLI via subprocess
   Code:

   def aurora_search(query: str, limit: int = 10) -> str:
       result = subprocess.run(
           ['aur', 'mem', 'search', query],
           capture_output=True,
           text=True
       )
       return result.stdout

4. CLI executes
   Command: aur mem search "hybrid retrieval"

   [Same as CLI behavior - all 6 steps]

5. CLI returns table output
   stdout = """
   ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
   ┃ File                      ┃ Type     ┃  Score ┃
   ┡━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━┩
   │ hybrid_retriever.py       │ code     │  0.930 │
   ...
   """

6. MCP tool returns CLI output
   return result.stdout

7. Claude shows CLI output as-is
   [Displays the raw table]
```

**User sees**:
- ✅ CLI table output (working scores)
- ✅ Score breakdown
- ⚠️ Raw CLI formatting (not natural)
- ⚠️ Subprocess overhead

**Question**: Why not just run `aur mem search` directly?

---

#### **MCP Behavior (Option 2: Real Implementation with Fixed Activation)**

```
User: "search for hybrid retrieval"  (implicit)
OR
User: "aurora search for hybrid retrieval"  (explicit)
```

**Step-by-step execution**:

```
1. Claude calls MCP tool
   Tool call: aurora_search(query="hybrid retrieval", limit=5)

2. MCP tool executes (WITH FIXED ACTIVATION TRACKING)

   Hybrid retrieval:

   Activation scores (FIXED):
   - hybrid_retriever.py: 0.95 (accessed 23 times)
   - embedding_provider.py: 0.82 (accessed 15 times)
   - retrieval.py: 0.78 (accessed 12 times)

   Semantic scores:
   - hybrid_retriever.py: 0.91
   - embedding_provider.py: 0.85
   - retrieval.py: 0.79

   Hybrid scores:
   - hybrid_retriever.py: 0.93
   - embedding_provider.py: 0.83
   - retrieval.py: 0.79

3. Track access (FIX THE BUG)
   for chunk in results:
       store.record_access(chunk.id, datetime.now())

4. MCP tool returns structured JSON
   {
     "results": [
       {
         "file_path": "hybrid_retriever.py",
         "function_name": "HybridRetriever.retrieve",
         "content": "...",
         "scores": {
           "activation": 0.95,
           "semantic": 0.91,
           "hybrid": 0.93
         },
         "line_range": [174, 250],
         "chunk_id": "code:hybrid_retriever.py:HybridRetriever.retrieve"
       },
       ...
     ],
     "metadata": {
       "total_chunks": 6277,
       "avg_activation": 0.842,
       "avg_semantic": 0.851,
       "avg_hybrid": 0.792,
       "duration_ms": 120
     }
   }

5. Claude formats naturally
   I found these files about hybrid retrieval in Aurora's codebase:

   **Top Results**:

   1. **hybrid_retriever.py** (score: 0.93)
      - HybridRetriever.retrieve() method (lines 174-250)
      - Implements 60% activation + 40% semantic scoring

   2. **embedding_provider.py** (score: 0.83)
      - EmbeddingProvider class
      - Handles semantic embeddings

   3. **retrieval.py** (score: 0.79)
      - Core retrieval logic

   Aurora found 5 results in 120ms with high confidence (avg: 0.79).
```

**User sees**:
- ✅ Natural Claude formatting
- ✅ Correct scores (activation tracking fixed)
- ✅ Rich metadata (line ranges, scoring breakdown)
- ✅ Fast (<200ms)
- ✅ Clear indication Aurora was used

---

## Architectural Comparison

### Option 1: MCP as Bash Wrapper

**What it is**:
```python
# In src/aurora/mcp/tools.py

@self.mcp.tool()
def aurora(query: str) -> str:
    """Invoke Aurora CLI"""
    result = subprocess.run(['aur', 'query', query], ...)
    return result.stdout

@self.mcp.tool()
def aurora_search(query: str) -> str:
    """Search via CLI"""
    result = subprocess.run(['aur', 'mem', 'search', query], ...)
    return result.stdout
```

**Pros**:
- ✅ Quick to implement (30 min)
- ✅ Reuses working CLI code
- ✅ No SOAR reimplementation needed
- ✅ CLI output includes costs/timing

**Cons**:
- ❌ Subprocess overhead (100-200ms per call)
- ❌ Just a wrapper, not real MCP
- ❌ Can't leverage MCP features
- ❌ User sees raw CLI output (not Claude's formatting)
- ❌ Requires API key in environment
- ❌ Two processes (MCP + CLI subprocess)
- ❌ No structured data for Claude to work with

**Is this really MCP?**
**No.** It's a shell command alias. The MCP protocol allows:
- Structured returns (JSON schemas)
- Progress streaming
- Tool chaining
- Rich metadata

Bash wrapper uses NONE of these. You might as well just run `aur` commands directly.

---

### Option 2: MCP as Real Implementation

**What it is**:
```python
# In src/aurora/mcp/tools.py

@self.mcp.tool()
def aurora_query(query: str, mode: str = "auto") -> str:
    """Real SOAR integration"""
    # Initialize SOAROrchestrator
    orchestrator = SOAROrchestrator(
        store=self._store,
        agent_registry=self._registry,
        reasoning_llm=self._llm_client,
        solving_llm=self._llm_client
    )

    # Execute query through SOAR
    result = orchestrator.execute(query)

    # Return structured response
    return json.dumps({
        "answer": result.answer,
        "execution_path": result.path,
        "phases": result.phase_trace,
        "cost": result.cost,
        "sources": result.sources
    })
```

**Pros**:
- ✅ Real MCP integration
- ✅ Structured data for Claude
- ✅ No subprocess overhead
- ✅ Full CLI/MCP parity
- ✅ Leverages MCP protocol features
- ✅ Claude can format naturally
- ✅ Progress streaming possible
- ✅ Tool chaining possible

**Cons**:
- ❌ Complex implementation (2-3 days)
- ❌ Need to handle LLM client init
- ❌ Budget tracking complexity
- ❌ More code to maintain

**Is this real MCP?**
**Yes.** Proper MCP server integration following the protocol.

---

## Routing Modes Clarification

### Mode A: Always-On (Keyword-Based Assessment)

**How it works**:
```
User: ANY prompt
↓
Claude calls: aurora_query(query="...", mode="always_on")
↓
MCP tool assesses complexity:
  Keywords: ["complex", "reasoning", "decompose", "SOAR", "agents"]
  If matches → Route to SOAR
  Else → Route to Direct LLM
↓
Execute appropriate path
```

**Examples**:

```
User: "what is 2+2?"
→ aurora_query assesses: SIMPLE (no complex keywords)
→ Routes to: Direct LLM
→ Fast answer: "4"

User: "explain how Aurora's SOAR reasoning handles multi-step decomposition"
→ aurora_query assesses: COMPLEX (keywords: SOAR, reasoning, decomposition, multi-step)
→ Routes to: SOAR 9-phase pipeline
→ Detailed answer with phase breakdown
```

**Config**:
```json
// ~/.aurora/mcp_config.json
{
  "mode": "always_on",
  "complexity_keywords": ["SOAR", "ACT-R", "reasoning", "decompose", "agents", ...]
}
```

---

### Mode B: Intentional (aur/aurora Trigger)

**How it works**:
```
User: Mentions "aur" or "aurora"
↓
Claude recognizes keyword
↓
Claude calls: aurora() MCP tool
↓
MCP tool decides routing (same assessment as Mode A)
↓
Execute

User: No "aur/aurora" mentioned
↓
Claude uses own knowledge
↓
MCP NOT called
```

**Examples**:

```
User: "aurora explain SOAR"
→ Claude sees "aurora" keyword
→ Calls: aurora(query="explain SOAR")
→ Aurora processes

User: "explain SOAR"  (no "aurora" mentioned)
→ Claude doesn't recognize trigger
→ Claude answers from own knowledge
→ Aurora NOT used
```

**Tool description**:
```python
@self.mcp.tool()
def aurora(query: str, mode: str = "auto") -> str:
    """
    Invoke Aurora's cognitive processing.

    USE THIS TOOL WHEN:
    - User says "aurora" or "aur"
    - User wants Aurora's SOAR reasoning
    - User mentions Aurora features

    DO NOT USE when:
    - User asking general questions without "aurora"
    """
```

---

## Question 4: LLM Calls & Declarative Steps

> "if mcp is calling translating intent and executing shell commands, would it use llm call and show details from every command while incurring llm calls? or would it show what each output as in every step of the way?"

### Option 1 (Bash Wrapper): No Declarative Steps

**What happens**:
```
User: "aurora explain SOAR"
↓
Claude calls: aurora(query="explain SOAR")  [MCP tool]
↓
MCP tool runs: subprocess.run(['aur', 'query', 'explain SOAR'])
↓
CLI executes in background:
  [User sees NOTHING while this runs]

  Internally (hidden):
  Phase 1: Assess → 0.12s
  Phase 2: Retrieve → 0.45s
  Phase 3: Decompose → 1.2s
  ...
  Phase 9: Respond → 0.8s

  Total: 2.3s of black box
↓
CLI returns final output
↓
MCP tool returns to Claude
↓
User sees: Final answer only

CLI incurs 1 LLM call (from subprocess)
Claude incurs 0 LLM calls (just displays result)
Total: 1 LLM call
```

**User experience**:
- ⏱️ 2.3 second wait
- 🔳 Black box (no progress shown)
- ✅ Final answer appears
- ❌ No phase visibility
- ❌ No streaming

**LLM calls**: 1 (from CLI subprocess)

---

### Option 2 (Real MCP): Declarative Steps with Progress

**What happens**:
```
User: "aurora explain SOAR"
↓
Claude calls: aurora_query(query="explain SOAR", verbose=True)
↓
MCP tool executes with progress streaming:

  [User sees real-time progress]

  ⚙️ Aurora processing...

  Phase 1/9: Assess
  ├─ Analyzing query complexity
  ├─ Score: 0.67 (COMPLEX)
  └─ Route: SOAR pipeline

  Phase 2/9: Retrieve
  ├─ Searching codebase
  ├─ Found: 12 chunks
  └─ Confidence: HIGH (0.89)

  Phase 3/9: Decompose
  ├─ Breaking into subgoals
  ├─ Subgoals: 3
  └─ Clarity: 0.92

  Phase 4/9: Verify
  ├─ Validating decomposition
  └─ Quality: PASS

  Phase 5/9: Route
  ├─ Assigning agents
  └─ Agents: General, Code Analyzer

  Phase 6/9: Collect
  ├─ Executing agents
  └─ Results: 3 collected

  Phase 7/9: Synthesize
  ├─ Combining results
  └─ Coherence: 0.94

  Phase 8/9: Record
  ├─ Caching patterns
  └─ Cached: reasoning_pattern_47

  Phase 9/9: Respond
  ├─ Formatting answer
  └─ Complete

  ✅ Done in 2.3s
↓
Final answer with sources
```

**User experience**:
- ⏱️ 2.3 second total
- ✅ Live progress updates
- ✅ See each phase
- ✅ Declarative steps
- ✅ Feels responsive

**LLM calls**: 1 (from MCP's SOAR, via Anthropic API directly)

---

## Answer to Question 5: Change CLI to Not Use API?

> "we can turn mcp into explicit bash calls instead of developing mcp, resulting in clear bash calls and it can translate intent if it has aur in it while keeping cli, that means that we also need to change query to use non API."

**This doesn't make sense.** Here's why:

### The Problem

If you want CLI (`aur query`) to NOT use API:
- ❌ Can't run SOAR (SOAR needs LLM for reasoning)
- ❌ Can't run Direct LLM (by definition needs LLM)
- ✅ Can only do retrieval (database search)

**But then CLI becomes useless!** The whole point of `aur query` is to:
1. Retrieve context from memory
2. **Use LLM to reason about that context**
3. Return intelligent answer

Without LLM, it's just `aur mem search`.

### What You Probably Mean

Maybe you meant:
> "If MCP wraps CLI, can MCP provide the API key so CLI doesn't need env var?"

**Answer**: Yes, but complicated:

```python
def aurora(query: str, api_key: str) -> str:
    """MCP tool that calls CLI with API key"""
    result = subprocess.run(
        ['aur', 'query', query],
        env={'ANTHROPIC_API_KEY': api_key},  # Pass key to CLI
        capture_output=True
    )
    return result.stdout
```

**But** this means:
- User provides API key to MCP tool as parameter
- MCP passes it to CLI subprocess
- CLI uses it for LLM calls

**This is terrible design**:
- Security risk (API key in tool parameters)
- Double process overhead
- No benefit over running CLI directly

---

## Recommendation

### For Your Use Case

Based on your questions, I think you want:

**Option 2 (Real MCP) with BOTH routing modes**

**Implement**:
1. **Mode B (Intentional)** first - easier to test
   - Add `aurora()` tool with clear trigger keywords
   - User says "aurora X" → Calls MCP tool

2. **Mode A (Always-on)** second - after Mode B works
   - Add config: `auto_route_mode: "always_on"`
   - Tool description changes based on config
   - ALL queries route through Aurora

**Why NOT Option 1 (Bash wrapper)**:
- ❌ Not real MCP
- ❌ No declarative steps
- ❌ Subprocess overhead
- ❌ Can't leverage MCP features
- ❌ User might as well use CLI directly

**Path forward**:
1. Fix activation tracking bug (Priority 0)
2. Implement real SOAR in MCP (Path B)
3. Add intentional routing (Mode B)
4. Add always-on mode (Mode A)
5. Test with real usage

---

## Summary Table

| Aspect | CLI (Current) | Option 1 (Bash Wrapper) | Option 2 (Real MCP) |
|--------|--------------|------------------------|---------------------|
| **SOAR Pipeline** | ✅ Real | ✅ Real (via subprocess) | ✅ Real (native) |
| **LLM Calls** | 1 per query | 1 per query | 1 per query |
| **Declarative Steps** | ❌ Final only | ❌ Black box | ✅ Live progress |
| **Subprocess** | N/A | ✅ 100-200ms overhead | ❌ None |
| **API Key** | Env var required | Env var or parameter | MCP handles it |
| **Output Format** | CLI table | CLI text | Structured JSON |
| **Claude Formatting** | N/A | Raw CLI output | ✅ Natural |
| **Is it MCP?** | N/A | ❌ Just wrapper | ✅ Real MCP |
| **Implementation Time** | N/A | 30 min | 2-3 days |
| **CLI/MCP Parity** | N/A | ⚠️ Indirect | ✅ Direct |

**Verdict**: **Option 2** is the right choice. Option 1 is a shortcut that gives up MCP's benefits.
