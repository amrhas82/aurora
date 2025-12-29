# MCP Intent Matching Strategy: Simple & Effective

**Date**: 2025-12-28
**Philosophy**: Keep it simple. Better descriptions > Complex routing logic.

---

## User's Core Insight

> "wouldn't adding adequate comprehensive desc for each mcp tool render better invocation matching?"

**YES.** This is the simplest and most effective solution.

**Current problem**: Tool descriptions are vague
**Simple fix**: Make them explicit and comprehensive
**No new logic needed**: Claude already knows how to pick tools based on descriptions

---

## The Four Questions Analyzed

### Question 1: Better Descriptions = Better Matching?

**Answer: ABSOLUTELY YES**

**Current description (vague)**:
```python
@mcp.tool()
def aurora_query(query: str):
    """
    Retrieve relevant context from AURORA memory without LLM inference.

    Args:
        query: Natural language query string
    """
```

**Problems**:
- ❌ Doesn't mention trigger keywords
- ❌ Doesn't explain WHEN to use it
- ❌ Doesn't distinguish from other tools
- ❌ Doesn't prevent CLI routing

**Improved description (explicit)**:
```python
@mcp.tool()
def aurora_query(query: str, mode: str = "auto"):
    """
    Query Aurora's cognitive memory using SOAR reasoning and ACT-R activation.

    **USE THIS TOOL WHEN**:
    - User explicitly says "aurora query", "aur query", or "ask aurora"
    - User wants Aurora's SOAR reasoning pipeline (9 phases)
    - User asks about Aurora's codebase or indexed code
    - User mentions Aurora features: SOAR, ACT-R, hybrid retrieval, cognitive architecture
    - User wants complex reasoning with decomposition and synthesis

    **DO NOT USE WHEN**:
    - User just wants to search files → Use aurora_search instead
    - User wants to index code → Use aurora_index instead
    - User asks general questions without Aurora context → Answer directly

    **IMPORTANT**: Use this MCP tool instead of running the CLI command `aur query`.
    When user says "aur query X", call this tool with query="X", do NOT run bash.

    **Trigger keywords**: aurora query, aur query, ask aurora, SOAR, ACT-R,
    reasoning pipeline, cognitive memory, indexed codebase, aurora explain

    **Examples**:
    - "aurora query 'what is SOAR?'" → aurora_query("what is SOAR?")
    - "aur query 'explain hybrid retrieval'" → aurora_query("explain hybrid retrieval")
    - "ask aurora about decomposition" → aurora_query("about decomposition")

    Args:
        query: Natural language query string
        mode: "auto" (default), "soar" (force SOAR), or "fast" (direct LLM only)

    Returns:
        JSON with answer, execution path, phases, cost, sources
    """
```

**Impact**:
- ✅ Clear trigger keywords
- ✅ Explicit WHEN to use / WHEN NOT to use
- ✅ Prevents CLI routing ("use this MCP tool instead of CLI")
- ✅ Examples show exact matching
- ✅ Mentions all Aurora-specific terms

**Estimated improvement**: 80-90% better intent matching

**Implementation time**: 1-2 hours to update all 7 tool descriptions

---

### Question 2: Always-On Mode - Necessary?

**Answer: NO, AGREE IT'S OVERKILL**

**Your insight**:
> "now thinking about it, always on doesn't add much, if we better mcp description and intent capture we should yield better results"

**You're right!** Here's why:

**Always-on mode problems**:
1. Every query through Aurora = slow for simple questions
2. Expensive (API costs for "what is 2+2?")
3. Adds configuration complexity
4. User loses control

**Better descriptions achieve the same goal**:
```python
# With good descriptions, Claude naturally routes:

User: "what is 2+2?"
→ Claude thinks: No Aurora keywords, simple math
→ Claude answers: "4" (no tool call)

User: "aurora what is 2+2?"
→ Claude sees: "aurora" keyword
→ Claude calls: aurora_query("what is 2+2?")
→ Aurora assesses: SIMPLE → Direct LLM → "4"

User: "explain SOAR reasoning in Aurora"
→ Claude sees: "SOAR" + "Aurora" keywords
→ Claude calls: aurora_query("explain SOAR reasoning")
→ Aurora assesses: COMPLEX → SOAR pipeline
```

**Natural, smart routing without config!**

**Recommendation**: **Drop always-on mode**. Better descriptions are sufficient.

---

### Question 3: Wildcard/Disambiguation Tool?

**Your idea**:
> "borderline cases we can display to user multi options (did you mean #1 aur query #2 aur init #3 aur mem search)"

**Analysis**: Interesting, but **NOT NEEDED** with good descriptions.

**Why disambiguation is complex**:

**Approach A**: Dedicated disambiguation tool
```python
@mcp.tool()
def aurora_help(user_message: str):
    """When unsure which Aurora tool to use"""
    return {
        "options": [
            "1. aurora_query - Search and reason",
            "2. aurora_search - Just search files",
            "3. aurora_index - Index code"
        ]
    }
```

**Problem**: Claude can't show interactive menus. Would be:
1. Claude calls aurora_help
2. Claude shows options to user
3. User picks one
4. Claude calls chosen tool

**This is clunky!**

**Approach B**: Claude naturally asks (already works!)
```
User: "search aurora"

Claude (already does this naturally):
"I can help you search Aurora in two ways:
1. aurora_search - Fast file search (no reasoning)
2. aurora_query - Full SOAR reasoning pipeline

Which would you prefer?"

User: "1"

Claude: [calls aurora_search]
```

**This already works!** No new tool needed.

**When does Claude naturally disambiguate?**
- When multiple tools could match
- When confidence is low
- When user request is ambiguous

**Better descriptions make this clearer**:
```python
@mcp.tool()
def aurora_search(query: str):
    """
    Fast file search without reasoning.

    Use when user wants SPEED over depth.
    Don't use if user wants reasoning or explanation.
    """

@mcp.tool()
def aurora_query(query: str):
    """
    Full SOAR reasoning with explanation.

    Use when user wants DEPTH over speed.
    Use when user wants explanation, not just file list.
    """
```

Now Claude can naturally pick or ask!

**Recommendation**: **No disambiguation tool**. Better descriptions + Claude's natural behavior is enough.

---

### Question 4: Recourse Mechanism?

**Your question**:
> "which is best to keep it simple, capture user intent correctly and offer recourse if wrong tool called"

**Answer: Recourse is AUTOMATIC with good descriptions**

**How recourse naturally works**:

**Scenario 1: Claude picks wrong tool**
```
User: "search aurora for X"

Claude calls: aurora_query (oops, should be aurora_search)

Tool returns: {answer with full reasoning, cost $0.01, 2.3s}

User: "that was slow, I just wanted a file list"

Claude: "You're right, let me use fast search instead"
[calls aurora_search this time]
```

**Recourse**: User corrects Claude naturally

---

**Scenario 2: User is explicit, Claude still wrong**
```
User: "use aurora search, not query"

Claude calls: aurora_search (correct this time)
```

**Recourse**: User's explicit instruction overrides

---

**Scenario 3: Proactive disambiguation**
```
User: "search aurora"

Claude (uncertain, asks first):
"I can search Aurora's codebase in two ways:
- Fast search (files only, <1s)
- Full query (with reasoning, ~2s)

Which do you prefer?"
```

**Recourse**: Built into Claude's natural behavior

---

**The key**: With **good tool descriptions**, Claude:
1. Picks correctly more often (80-90% accuracy)
2. Asks when uncertain (built-in behavior)
3. Accepts user corrections (natural conversation)

**No special recourse mechanism needed!**

---

## The "aur" vs MCP Problem (CRITICAL)

**Current bug**:
```
User: "aur search for X"
Claude: Runs Bash(aur mem search X)  ← WRONG!
Should: Call aurora_search MCP tool
```

**Why this happens**:
- "aur" looks like a CLI command to Claude
- Claude has Bash tool available
- Claude prefers Bash for command-like syntax

**Fix Strategy**:

### Strategy A: Explicit "Instead of CLI" Notes

```python
@mcp.tool()
def aurora_search(query: str):
    """
    Search Aurora's indexed codebase.

    **CRITICAL**: When user says "aur search" or "aur mem search",
    use THIS MCP TOOL, NOT the bash command. This MCP tool replaces
    the CLI command `aur mem search` when running inside Claude Code.

    Trigger phrases:
    - "aur search X"
    - "aur mem search X"
    - "aurora search X"

    All should call this tool, NOT bash.
    """
```

**Will this work?** Maybe 70% of the time. Claude might still prefer Bash.

---

### Strategy B: Tool Name Matching CLI Command

**Current names**:
- `aurora_query` (doesn't match "aur query")
- `aurora_search` (doesn't match "aur mem search")

**Alternative names**:
- `aur_query` (matches "aur query" exactly!)
- `aur_mem_search` (matches "aur mem search" exactly!)

```python
@mcp.tool()
def aur_query(query: str):
    """
    Execute 'aur query' via MCP (not CLI).

    When user types "aur query X", call this tool.
    """

@mcp.tool()
def aur_mem_search(query: str):
    """
    Execute 'aur mem search' via MCP (not CLI).

    When user types "aur mem search X", call this tool.
    """
```

**Will this work?** Probably 90% of the time. Name matching is strong signal.

**Problem**: Less semantic. "aur_mem_search" is less clear than "aurora_search".

---

### Strategy C: Hybrid - Aliases!

```python
@mcp.tool()
def aurora_search(query: str):
    """Primary search tool"""
    # ... comprehensive description

@mcp.tool()
def aur_search(query: str):
    """Alias for aurora_search. Use when user says 'aur search'."""
    return aurora_search(query)

@mcp.tool()
def aur_mem_search(query: str):
    """Alias for aurora_search. Use when user says 'aur mem search'."""
    return aurora_search(query)
```

**Pros**:
- ✅ Semantic primary name (aurora_search)
- ✅ Exact match aliases (aur_search, aur_mem_search)
- ✅ Clear descriptions on each

**Cons**:
- ⚠️ More tools (7 → ~12-14 with all aliases)
- ⚠️ Maintenance (update aliases when primary changes)

---

### Strategy D: Single Entry Point

```python
@mcp.tool()
def aurora(command: str, args: str):
    """
    Aurora MCP entry point. Replaces ALL 'aur' CLI commands.

    When user says "aur X Y", call: aurora(command="X", args="Y")

    Supported commands:
    - query: aurora(command="query", args="search term")
    - search: aurora(command="search", args="search term")
    - mem search: aurora(command="mem search", args="search term")
    - index: aurora(command="index", args="path")
    - stats: aurora(command="stats", args="")
    - init: aurora(command="init", args="")

    Examples:
    - "aur query X" → aurora(command="query", args="X")
    - "aur mem search X" → aurora(command="mem search", args="X")
    """
    if command == "query":
        return aurora_query(args)
    elif command == "search" or command == "mem search":
        return aurora_search(args)
    elif command == "index":
        return aurora_index(args)
    # ...
```

**Pros**:
- ✅ Single tool for all "aur" commands
- ✅ Clear CLI replacement
- ✅ Easy to understand

**Cons**:
- ❌ Less semantic (command string parsing)
- ❌ Claude might not like the command/args pattern
- ❌ Loses tool-specific descriptions

---

**Recommendation for "aur" problem**:

**Phase 1**: Try Strategy A (better descriptions with "instead of CLI" notes)
- Quick (1 hour)
- Test if it works

**Phase 2**: If Phase 1 fails, try Strategy C (aliases)
- More robust (2 hours)
- Keeps semantic primary names
- Adds exact-match aliases

---

## Recommended Implementation Plan

### What to Build (SIMPLE)

**1. Better Tool Descriptions** (1-2 hours)

Update all 7 MCP tools:
- ✅ Explicit "USE WHEN" section
- ✅ Explicit "DO NOT USE WHEN" section
- ✅ Trigger keywords list
- ✅ "Instead of CLI" notes
- ✅ Examples showing exact phrases

**2. Test with Real Queries** (1 hour)

Test cases:
```
- "aurora explain SOAR" → Should call aurora_query
- "aur search for X" → Should call aurora_search (not Bash)
- "search aurora for X" → Should call aurora_search
- "explain SOAR" (no aurora) → Should use Claude's knowledge
- "aur query X" → Should call aurora_query (not Bash)
```

**3. Add Aliases IF Needed** (2 hours - only if Step 2 fails)

If "aur" still routes to Bash:
- Add `aur_query`, `aur_search`, `aur_mem_search` aliases
- Keep semantic primary names
- Document alias strategy

**Total**: 2-3 hours for simple approach, 4-5 hours if aliases needed

---

### What NOT to Build (COMPLEX)

**❌ Always-on mode** - Unnecessary with good descriptions
**❌ Disambiguation tool** - Claude already does this naturally
**❌ Complex confidence scoring** - Not needed
**❌ Wildcard tools** - Over-engineering
**❌ Routing configuration** - Adds complexity
**❌ Recourse mechanisms** - User corrections work naturally

---

## Testing Strategy

### Test Matrix

| User Input | Expected Tool | Current Behavior | After Descriptions |
|-----------|---------------|------------------|-------------------|
| "aurora explain X" | aurora_query | ⚠️ Unpredictable | ✅ aurora_query |
| "aur query X" | aurora_query | ❌ Bash(aur query) | ⚠️ Test needed |
| "aur search X" | aurora_search | ❌ Bash(aur mem search) | ⚠️ Test needed |
| "search aurora" | aurora_search | ⚠️ Maybe | ✅ aurora_search |
| "explain SOAR" | Claude direct | ⚠️ Maybe aurora | ✅ Claude direct |
| "aur mem search X" | aurora_search | ❌ Bash | ⚠️ Test needed |
| "aurora index ." | aurora_index | ⚠️ Maybe | ✅ aurora_index |

### Success Criteria

**Phase 1 (descriptions only)**:
- ✅ 80%+ correct tool selection
- ✅ "aurora X" phrases always use MCP
- ⚠️ "aur X" might still use Bash (acceptable for Phase 1)

**Phase 2 (with aliases if needed)**:
- ✅ 95%+ correct tool selection
- ✅ "aur X" phrases use MCP, not Bash
- ✅ Natural disambiguation when uncertain

---

## Example: Updated Tool Description

Here's what ONE tool would look like with comprehensive description:

```python
@mcp.tool()
def aurora_query(
    query: str,
    mode: str = "auto",
    verbose: bool = False
) -> str:
    """
    Query Aurora's cognitive memory using SOAR reasoning and ACT-R activation.

    Aurora's primary reasoning tool that provides intelligent answers by:
    1. Retrieving relevant context from indexed codebase
    2. Assessing query complexity (simple vs complex)
    3. Using SOAR 9-phase pipeline for complex reasoning
    4. Synthesizing coherent answers with sources

    ════════════════════════════════════════════════════════════════

    **USE THIS TOOL WHEN**:
    ✓ User explicitly says "aurora query", "aur query", or "ask aurora"
    ✓ User wants SOAR reasoning (9-phase cognitive pipeline)
    ✓ User asks about Aurora's indexed codebase
    ✓ User mentions Aurora-specific features:
      - SOAR, ACT-R, cognitive architecture
      - Hybrid retrieval, spreading activation
      - Reasoning pipeline, decomposition, synthesis
    ✓ User wants explained answers with reasoning steps
    ✓ User asks complex questions requiring multi-step reasoning

    **DO NOT USE THIS TOOL WHEN**:
    ✗ User just wants file search → Use aurora_search (faster)
    ✗ User wants to index code → Use aurora_index
    ✗ User asks general questions without Aurora context → Answer directly
    ✗ User wants statistics → Use aurora_stats
    ✗ User wants specific file content → Use aurora_context

    **CRITICAL - CLI REPLACEMENT**:
    When user says "aur query X", use THIS MCP TOOL, do NOT run bash command.
    This tool replaces the CLI command `aur query` when inside Claude Code.

    ════════════════════════════════════════════════════════════════

    **TRIGGER KEYWORDS** (use tool when these appear):
    Primary: aurora query, aur query, ask aurora, query aurora
    Features: SOAR, ACT-R, cognitive, reasoning pipeline, hybrid retrieval
    Actions: explain aurora, aurora explain, analyze with aurora
    Context: indexed codebase, aurora memory, aurora's knowledge

    **EXAMPLES** (exact phrase matching):

    ✓ "aurora query 'what is SOAR?'"
      → aurora_query(query="what is SOAR?", mode="auto")

    ✓ "aur query 'explain hybrid retrieval'"
      → aurora_query(query="explain hybrid retrieval", mode="auto")

    ✓ "ask aurora about ACT-R activation"
      → aurora_query(query="about ACT-R activation", mode="auto")

    ✓ "use aurora to explain decomposition in the codebase"
      → aurora_query(query="explain decomposition in the codebase")

    ✓ "aurora how does SOAR reasoning work?"
      → aurora_query(query="how does SOAR reasoning work?")

    ✗ "search aurora for files"
      → Use aurora_search instead (faster, no reasoning)

    ✗ "explain SOAR" (no aurora mentioned)
      → Answer directly without tool (user wants general info)

    ════════════════════════════════════════════════════════════════

    Args:
        query (str): Natural language query or question
        mode (str): Execution mode:
            - "auto" (default): Auto-escalation based on complexity
            - "soar": Force full 9-phase SOAR pipeline
            - "fast": Direct LLM only (skip SOAR)
        verbose (bool): Include detailed phase information and timing

    Returns:
        JSON string with:
        {
            "answer": "...",
            "execution_path": "direct_llm" | "soar_pipeline",
            "phases": [{name, duration, status}, ...],
            "cost": {total_usd, input_tokens, output_tokens},
            "sources": [{file, lines, score}, ...],
            "metadata": {complexity_score, confidence, duration_seconds}
        }

    Raises:
        None - gracefully handles errors and returns error in JSON

    ════════════════════════════════════════════════════════════════

    **TECHNICAL NOTES**:
    - Requires API key (handled by MCP context)
    - Uses SOAR orchestrator for complex queries (>0.6 complexity)
    - Uses Direct LLM for simple queries (<0.6 complexity)
    - ACT-R activation: 60% base-level + 40% semantic similarity
    - Budget tracking via ~/.aurora/budget_tracker.json
    - Costs: ~$0.002-0.005 for simple, ~$0.01-0.03 for complex

    **RELATED TOOLS**:
    - aurora_search: Fast file search without reasoning
    - aurora_get: Retrieve chunk by index from last search
    - aurora_context: Get specific file/function content
    - aurora_related: Find related code via spreading activation
    """
    return self.tools.aurora_query(query, mode=mode, verbose=verbose)
```

**This description is**:
- ✅ Comprehensive (covers all cases)
- ✅ Explicit (clear when to use / not use)
- ✅ Example-rich (shows exact phrase matching)
- ✅ Semantic (explains what tool does)
- ✅ Technical (details for debugging)

**Repeat for all 7 tools.**

---

## Summary & Recommendation

### Your Core Insight is CORRECT

> "Better MCP description and intent capture should yield better results"

**YES!** This is the 80/20 solution:
- 20% effort (better descriptions)
- 80% results (correct routing)

### What to Build

**✅ DO**:
1. Write comprehensive tool descriptions (2 hours)
2. Test with real queries (1 hour)
3. Add aliases if "aur" still routes to CLI (2 hours if needed)

**❌ DON'T**:
1. Always-on mode (unnecessary)
2. Disambiguation tool (Claude does this naturally)
3. Complex confidence scoring (over-engineering)
4. Routing configuration (adds complexity)

### Expected Outcome

**With better descriptions**:
- 80-90% correct tool selection
- Natural disambiguation when uncertain
- User corrections work automatically
- Simple to maintain

**Total implementation**: 2-5 hours

### Next Step

**Write the descriptions first**, test, then decide if aliases are needed.

**Should I start writing the comprehensive descriptions for all 7 tools now?**
