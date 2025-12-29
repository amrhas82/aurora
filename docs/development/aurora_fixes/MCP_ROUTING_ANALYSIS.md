# MCP Routing Analysis: How Claude Decides to Invoke Aurora Tools

**Date**: 2025-12-28
**Purpose**: Answer user's questions about when/how Aurora MCP tools get invoked

---

## The User's Questions

User has **two modes** they expect Aurora MCP to support:

### Mode 1: Always-On (Config-Based)
- **Behavior**: ANY prompt triggers SOAR 9 phases automatically
- **Trigger**: Config file setting (e.g., `auto_soar: true`)
- **Use case**: User wants Aurora to always process queries through full pipeline

### Mode 2: Intentional Invocation
- **Behavior**: User explicitly says "aur" or "aurora" at beginning of prompt
- **Trigger**: Keyword detection
- **Use case**: User wants control over when Aurora is used

### Three Routing Scenarios to Test

**Scenario A**: Intentional invocation
```
User: "aur explain SOAR reasoning"
User: "aurora what is hybrid retrieval?"
```

**Scenario B**: Mixed invocation
```
User: "use aur to explain this code"
User: "search reddit for X and aurora for Y"
```

**Scenario C**: Implicit (no aurora mentioned)
```
User: "explain SOAR reasoning phases"
User: "how does hybrid retrieval work?"
```

**User's Question**: "how does it know to route to mcp? i understand with reddit mcp if i say search reddit it will know if it has reddit and then will look for search call if available then run api. how would it work in case of aurora?"

---

## How MCP Tool Routing Actually Works

### The MCP Protocol Architecture

When you configure MCP in `~/.config/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "aurora": {
      "command": "python3",
      "args": ["-m", "aurora.mcp.server"]
    }
  }
}
```

**What happens**:
1. Claude Code CLI starts the Aurora MCP server as a subprocess
2. MCP server sends tool definitions (names, descriptions, parameters) to Claude
3. Claude Code (me) receives tool metadata and adds them to my available tools
4. **I (Claude) decide when to call each tool based on tool descriptions**

### Tool Descriptions as Routing Signals

From `src/aurora/mcp/server.py`, here are the tool docstrings Claude sees:

**aurora_search**:
```python
"""
Search AURORA indexed codebase.

Args:
    query: Search query string
    limit: Maximum number of results (default: 10)

Returns:
    JSON string with search results
"""
```

**aurora_query**:
```python
"""
Retrieve relevant context from AURORA memory without LLM inference.

This tool provides intelligent context retrieval with complexity assessment
and confidence scoring. It returns structured context for the host LLM
(Claude Code CLI) to reason about, rather than calling external LLM APIs.

Args:
    query: Natural language query string (required)
    limit: Maximum number of chunks to retrieve (default: 10)
    type_filter: Filter by memory type - "code", "reas", "know", or None
    verbose: Include detailed metadata in response (default: False)

Returns:
    JSON string with:
    - context: Retrieved memory chunks with content, metadata, and relevance scores
    - assessment: Complexity assessment and retrieval confidence score
    - metadata: Database stats and result counts

Examples:
    Basic retrieval:
        aurora_query("What is a Python decorator?")

    Type-filtered retrieval:
        aurora_query("async patterns", type_filter="code", limit=5)

    Detailed metadata:
        aurora_query("SOAR pipeline", verbose=True)

Note:
    No API key required. This tool runs inside Claude Code CLI which
    provides the LLM reasoning capabilities. For standalone usage with
    LLM responses, use the CLI command: $ aur query "your question"
"""
```

---

## Routing Behavior Analysis

### Scenario A: Intentional Invocation ("aur" / "aurora" keywords)

**Test Case 1**: `"aur explain SOAR reasoning"`

**Expected Behavior**:
- Claude interprets "aur" as shell command reference
- **Routes to Bash tool**: `Bash(aur explain SOAR reasoning)`
- **Does NOT route to aurora_query MCP tool**

**Why**: "aur" is a CLI command name, not an MCP tool trigger

**Actual Routing**: ❌ **Goes to CLI, not MCP!**

---

**Test Case 2**: `"aurora what is hybrid retrieval?"`

**Expected Behavior**:
- Claude sees "aurora" in user message
- Tool description says "Search AURORA indexed codebase"
- **May or may not route to MCP** (depends on how Claude interprets intent)

**Why**: Tool descriptions don't mention "aurora" as a trigger keyword

**Actual Routing**: ⚠️ **Unpredictable - depends on Claude's judgment**

---

### Scenario B: Mixed Invocation

**Test Case**: `"use aur to explain this code"`

**Expected Behavior**:
- "use aur to" suggests CLI command
- **Routes to Bash**: `Bash(aur query "explain this code")`
- **Does NOT route to MCP**

**Actual Routing**: ❌ **Goes to CLI, not MCP!**

---

### Scenario C: Implicit (No "aurora" mentioned)

**Test Case**: `"explain SOAR reasoning phases in Aurora's codebase"`

**Expected Behavior**:
- Claude sees request about Aurora's codebase
- Checks tool descriptions:
  - `aurora_search`: "Search AURORA indexed codebase" ✅ Match!
  - `aurora_query`: "Retrieve relevant context from AURORA memory" ✅ Match!
- **Routes to MCP**: Calls `aurora_query` or `aurora_search`

**Why**: Tool descriptions mention "AURORA codebase" and "context retrieval"

**Actual Routing**: ✅ **May route to MCP** (if Claude recognizes codebase context need)

---

## The Routing Problem

### Issue #1: "aur" / "aurora" Keywords Don't Trigger MCP

**Why**:
- MCP tools have names like `aurora_search`, `aurora_query`
- But tool descriptions don't emphasize keyword triggers
- Claude treats "aur" as a **CLI command**, not an **MCP tool invocation**

**Example**:
```
User: "aur search for SOAR"
Claude: Runs Bash(aur mem search "SOAR")  ← CLI command!
Claude: Does NOT call aurora_search() MCP tool
```

### Issue #2: Implicit Routing is Unpredictable

**Claude's Decision Process** (simplified):
1. Analyze user intent
2. Check which tools match the intent
3. Pick the most relevant tool(s)

**For Aurora**:
- If user says "search Aurora's codebase" → Likely calls `aurora_search`
- If user says "explain SOAR" → May or may not call Aurora (could just use my knowledge)
- If user says "aur query X" → Calls CLI, not MCP

**Problem**: No explicit trigger mechanism for MCP tools!

---

## Reddit MCP Example (How It Works Better)

User mentioned: "with reddit mcp if i say search reddit it will know"

**Reddit MCP Tool Description** (hypothetical):
```python
@mcp.tool()
def search_reddit(query: str, subreddit: str = "all"):
    """
    Search Reddit for posts and comments.

    Use this tool when the user wants to search Reddit, find Reddit posts,
    or asks about content on Reddit.

    Trigger keywords: reddit, subreddit, r/
    """
```

**Why it works**:
- Tool description explicitly mentions "search Reddit"
- Keywords "reddit", "subreddit" in description
- Clear use case: "when the user wants to search Reddit"

**Aurora's tools lack this clarity!**

---

## Solutions for Aurora MCP Routing

### Solution 1: Improve Tool Descriptions (Quick - 30 min)

Update `aurora_query` description to include explicit triggers:

```python
@self.mcp.tool()
def aurora_query(query: str, ...):
    """
    Query Aurora's cognitive memory with ACT-R activation and SOAR reasoning.

    **Use this tool when**:
    - User mentions "aurora", "aur", or Aurora-related concepts
    - User asks about code in the indexed codebase
    - User wants SOAR reasoning or complexity assessment
    - User asks about ACT-R, hybrid retrieval, or Aurora features

    **Trigger keywords**: aurora, aur, SOAR, ACT-R, hybrid retrieval,
    cognitive architecture, reasoning pipeline

    This tool provides intelligent context retrieval with 9-phase SOAR
    pipeline and ACT-R spreading activation.

    [rest of description...]
    """
```

**Pros**: Makes routing more predictable
**Cons**: Still relies on Claude's interpretation

---

### Solution 2: Mode Configuration (Medium - 2 hours)

Add config-based auto-routing:

**Config file** (`~/.aurora/mcp_config.json`):
```json
{
  "auto_route_mode": "always_on",  // or "explicit_only"
  "trigger_keywords": ["aur", "aurora", "SOAR", "ACT-R"],
  "fallback_to_mcp": true
}
```

**MCP server reads config**:
```python
# In server.py startup
config = load_mcp_config()
if config["auto_route_mode"] == "always_on":
    # Include note in tool description
    # that ALL queries should use this tool first
```

**Pros**: User controls routing behavior
**Cons**: Requires config management, doesn't solve explicit keyword routing

---

### Solution 3: Dedicated Routing Tool (Medium - 3 hours)

Add a meta-tool that decides routing:

```python
@self.mcp.tool()
def aurora_should_handle(user_message: str) -> dict:
    """
    Check if Aurora should handle this query.

    Returns routing decision based on:
    - Keyword detection (aur, aurora, SOAR, etc.)
    - Code/codebase mention
    - Complexity assessment
    - Config settings (auto_route_mode)
    """
    keywords = ["aur", "aurora", "SOAR", "ACT-R", "hybrid"]
    has_keyword = any(kw in user_message.lower() for kw in keywords)

    return {
        "should_route_to_aurora": has_keyword or config["auto_route_mode"] == "always_on",
        "suggested_tool": "aurora_query" if complex else "aurora_search",
        "confidence": 0.95 if has_keyword else 0.3
    }
```

**Pros**: Explicit routing decision
**Cons**: Adds complexity, Claude might not use it

---

### Solution 4: Two-Tier Tool Design (RECOMMENDED - 4 hours)

Create **two different tools** for explicit vs implicit:

**Tool 1**: `aurora` (explicit invocation)
```python
@self.mcp.tool()
def aurora(query: str, mode: str = "auto"):
    """
    Explicitly invoke Aurora's SOAR reasoning pipeline.

    Use this tool when user explicitly says "aurora", "aur", or clearly
    wants Aurora's cognitive processing.

    Modes:
    - auto: Auto-escalation (simple → complex → SOAR)
    - soar: Force full 9-phase SOAR pipeline
    - fast: Direct LLM with Aurora context only
    """
```

**Tool 2**: `aurora_codebase_context` (implicit, specific use case)
```python
@self.mcp.tool()
def aurora_codebase_context(topic: str):
    """
    Retrieve context from Aurora's indexed codebase.

    Use this tool when user asks about code, implementation details,
    or concepts that might be in the indexed codebase.

    This is the implicit/background tool - use when Aurora isn't
    explicitly mentioned but codebase context is needed.
    """
```

**Pros**: Clear separation of explicit vs implicit
**Cons**: More tools to maintain

---

## Recommendation

**For your two modes**:

### Mode 1: Always-On (Config-Based)
**Implement**: Solution 2 (Mode Configuration)
- Add `auto_route_mode: "always_on"` config
- Tool description includes "Use for ALL queries when auto_route_mode enabled"
- Claude sees this and routes everything to Aurora

### Mode 2: Explicit Invocation
**Implement**: Solution 4 (Two-Tier Tools) + Solution 1 (Better descriptions)
- Create explicit `aurora()` tool with clear "use when user says aurora/aur" description
- Improve descriptions with trigger keywords
- Claude routes when keywords detected

---

## Testing Plan

To validate routing behavior, we need tests for each scenario:

### Test 1: Explicit Keyword Routing
```python
def test_explicit_aur_keyword():
    """Test: 'aur explain SOAR' should route to aurora() tool"""
    user_message = "aur explain SOAR reasoning"
    # Verify: aurora() tool was called
    # Verify: Bash tool was NOT called
```

### Test 2: Implicit Context Routing
```python
def test_implicit_codebase_context():
    """Test: 'explain SOAR in the codebase' should route to aurora_codebase_context()"""
    user_message = "explain how SOAR reasoning works in Aurora's codebase"
    # Verify: aurora_codebase_context() was called
    # Verify: Got code chunks from indexed codebase
```

### Test 3: Always-On Mode
```python
def test_always_on_mode():
    """Test: With auto_route_mode=always_on, all queries go through Aurora"""
    set_config(auto_route_mode="always_on")
    user_message = "what is 2+2?"
    # Verify: aurora() tool was called even for simple math
```

---

## Current State vs Desired State

### Current State (Broken)

| User Input | Expected Routing | Actual Routing | Status |
|-----------|-----------------|----------------|--------|
| `"aur explain SOAR"` | MCP aurora tool | Bash(aur query) | ❌ Wrong |
| `"aurora search for X"` | MCP aurora_search | Unpredictable | ⚠️ Unreliable |
| `"explain SOAR phases"` | MCP aurora_query | Claude's knowledge | ⚠️ Doesn't use MCP |

### Desired State (After Implementation)

| User Input | Mode | Expected Routing | Tool Called |
|-----------|------|-----------------|-------------|
| `"aur explain SOAR"` | Explicit | MCP | `aurora(query="explain SOAR", mode="auto")` |
| `"aurora search for X"` | Explicit | MCP | `aurora(query="search for X")` |
| `"explain SOAR phases"` | Implicit | MCP | `aurora_codebase_context(topic="SOAR phases")` |
| `"what is 2+2?"` | Always-On | MCP | `aurora(query="what is 2+2?")` |
| `"what is 2+2?"` | Explicit-Only | Direct | No MCP (Claude answers directly) |

---

## Implementation Priority

**Phase 1**: Fix explicit routing (HIGH - needed for Mode 2)
- Solution 1: Improve tool descriptions with trigger keywords
- Solution 4: Add explicit `aurora()` tool
- **Estimated**: 4 hours

**Phase 2**: Add always-on mode (HIGH - needed for Mode 1)
- Solution 2: Config-based auto-routing
- Update tool descriptions based on config
- **Estimated**: 2 hours

**Phase 3**: Testing & validation
- Test all 3 scenarios (A, B, C)
- Document routing behavior
- **Estimated**: 2 hours

**Total**: 8 hours (1 day)

---

## Open Questions

1. **Does always-on mode make sense?** If every query goes through Aurora's 9-phase SOAR, simple queries like "what is 2+2?" will be slow and expensive.

2. **Should "aur" trigger MCP or CLI?** User expects "aur" to invoke Aurora, but Claude interprets it as the CLI command. Need to decide which takes precedence.

3. **How to handle conflicts between tools?** If both Reddit MCP and Aurora MCP are installed, and user says "search reddit and aurora for X", how should routing work?

4. **Config location?** Should auto-routing config be in:
   - `~/.aurora/config.json` (Aurora's main config)
   - `~/.aurora/mcp_config.json` (MCP-specific)
   - `~/.config/Claude/claude_desktop_config.json` (Claude's MCP config)

5. **Override mechanism?** If always-on mode is enabled, how can user temporarily disable it for a single query?

---

## Next Steps

1. Get user feedback on routing design (modes 1 & 2)
2. Decide on config location and format
3. Implement Phase 1 (explicit routing)
4. Test with real user interactions
5. Implement Phase 2 (always-on mode) based on Phase 1 learnings
