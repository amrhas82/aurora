# AURORA Comprehensive Fix Plan

**Date**: December 24, 2025
**Priority**: CRITICAL - Multiple blocking issues + MCP integration needed

---

## Executive Summary

**User Situation**:
- Has GLM, Synthetic, Fireworks API keys (NOT Anthropic)
- Uses multiple AI CLIs (Claude Code, OpenCode, AmpCode, Droid)
- Wants AURORA as MCP server to work with ANY CLI
- **Cannot use AURORA at all** - multiple crashes and broken features

**Critical Insight**: User doesn't need AURORA to CALL LLMs directly. They need AURORA to PROVIDE TOOLS (search, memory, indexing) to their existing CLIs via MCP. The calling CLI handles LLM calls with user's API keys.

---

## All Issues Found - Prioritized

### 🔥 CRITICAL - Blocks All Usage

#### Issue 1: `aur init` Crashes Immediately
```python
UnboundLocalError: local variable 'Path' referenced before assignment
```

**Location**: `packages/cli/src/aurora_cli/commands/init.py:19`

**Root Cause**: Path imported twice - once at top, once inside function (line 88), shadowing the import

**Impact**: Cannot initialize AURORA at all - complete blocker

**Fix Complexity**: TRIVIAL (remove duplicate import)

**Fix Time**: 30 seconds

---

#### Issue 2: `aur mem index` Completely Broken
```python
AttributeError: 'SQLiteStore' object has no attribute 'add_chunk'
```

**Location**: `packages/cli/src/aurora_cli/memory_manager.py:537-554`

**Root Cause**: API mismatch
- Current: `memory_store.add_chunk(chunk_id, content, embedding, metadata)`
- Correct: `memory_store.save_chunk(chunk_object)`

**Impact**: Cannot index any files - memory features completely unusable

**Fix Complexity**: MEDIUM (refactor to use Chunk objects properly)

**Fix Time**: 15 minutes

**Additional bugs in same flow**:
- ✓ Fixed: `embedding_provider.embed()` → `embed_chunk()`
- ✓ Fixed: `chunk.chunk_id` → `chunk.id`
- ✗ Open: `add_chunk()` → `save_chunk()`

---

### ⚠️ HIGH - Important for User Experience

#### Issue 3: Wrong Import in Dry-Run Mode
```python
ModuleNotFoundError: No module named 'aurora_core.store.hybrid_retriever'
```

**Location**:
- `packages/cli/src/aurora_cli/main.py:342`
- `packages/cli/src/aurora_cli/main.py:445`

**Root Cause**: Wrong module path
- Current: `from aurora_core.store.hybrid_retriever import HybridRetriever`
- Correct: `from aurora_context_code.semantic.hybrid_retriever import HybridRetriever`

**Impact**: Dry-run can't show memory statistics

**Fix Complexity**: TRIVIAL (change import)

**Fix Time**: 30 seconds

---

#### Issue 4: No MCP Server Implementation
**Status**: Feature doesn't exist yet

**User Need**: AURORA as MCP server that provides tools to other CLIs

**Impact**: User cannot use AURORA with their existing API keys and CLIs

**Fix Complexity**: HIGH (new feature, 2-3 days)

**Priority**: CRITICAL for user but not a bug - it's missing functionality

---

#### Issue 5: Hardcoded to Anthropic API Only
**Location**: Throughout codebase

**Impact**: User has GLM/Synthetic/Fireworks keys but can't use them

**Fix Complexity**: MEDIUM-HIGH (abstraction layer needed)

**Priority**: HIGH but may be solved by MCP approach

---

### 📝 MEDIUM - UX Issues

#### Issue 6: Headless Mode Confusing Syntax
**User Tried**: `aur --headless test_prompt.md`
**Actual Syntax**: `aur headless test_prompt.md`

**Issue**: Users expect `--headless` as a flag, not a command

**Fix Options**:
1. Add `--headless` as global flag (maps to headless command)
2. Document better
3. Add helpful error message

**Fix Complexity**: LOW (add alias or improve error)

**Fix Time**: 10 minutes

---

## MCP Architecture Analysis

### Current Misunderstanding vs. Reality

**What I Initially Thought**:
- AURORA needs to call LLMs via MCP
- Support multiple LLM providers through MCP

**What User Actually Needs**:
- AURORA provides TOOLS via MCP (search, index, stats)
- Other CLIs call AURORA tools
- Those CLIs use their own API keys for LLM calls
- AURORA doesn't need to make LLM calls in MCP mode

### Proposed Architecture

```
┌──────────────────┐
│ User's CLI       │  (Claude Code, OpenCode, etc.)
│ - Has API key    │  - User's GLM/Synthetic/Fireworks key
│ - Makes LLM calls│  - Handles reasoning
└────────┬─────────┘
         │ MCP Protocol
         ▼
┌──────────────────┐
│ AURORA MCP Server│
│ Tools:           │
│ - search_code()  │  ← Hybrid retrieval
│ - index_files()  │  ← Memory indexing
│ - get_stats()    │  ← Memory statistics
│ - get_context()  │  ← Retrieve code chunks
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Local Database   │
│ - aurora.db      │
│ - Embeddings     │
│ - Activation     │
└──────────────────┘
```

**Key Insight**: AURORA MCP server is a **memory/search service**, not an LLM caller!

### MCP Tools to Implement

1. **search_code(query: str, limit: int = 10) → List[CodeChunk]**
   - Hybrid keyword + semantic search
   - Returns ranked code chunks
   - No LLM needed

2. **index_directory(path: str, pattern: str = "*.py") → IndexStats**
   - Index code files
   - Generate embeddings
   - No LLM needed (embeddings from local model)

3. **get_memory_stats() → Dict**
   - Total chunks, files, DB size
   - No LLM needed

4. **get_code_context(file_path: str, function: str) → str**
   - Retrieve specific code context
   - No LLM needed

5. **activate_related(chunk_id: str, max_hops: int = 2) → List[CodeChunk]**
   - ACT-R spreading activation
   - Find related chunks
   - No LLM needed

**Conclusion**: AURORA MCP server can work 100% without ANY API keys! It's pure memory/search.

---

## Package Structure Deep Dive

### User's Proposal
- `aurora-core`: Reasoning without memory
- `aurora-memory`: Memory without reasoning
- `aurora-full`: Everything

### Analysis: Why This Won't Work

**Problem 1: Reasoning needs memory**
- SOAR phases (collect, synthesize) require memory retrieval
- Can't have "reasoning without memory" - they're coupled

**Problem 2: Memory needs embeddings**
- Hybrid retrieval needs semantic search
- Semantic search needs embeddings
- Embeddings need... an embedding model (which is kind of an LLM)

**Problem 3: Current structure already modular**
```
aurora-core      → Store, activation, base types
aurora-context-code → Parsing, embeddings, retrieval
aurora-soar      → Orchestration, phases
aurora-reasoning → LLM client, prompts
aurora-cli       → CLI commands
aurora-testing   → Test utilities
```

### Alternative Proposal: Usage-Based Packages

**Package 1: `aurora-mcp` (NEW)**
```
Includes: core + context-code
Purpose: MCP server for memory/search
LLM: Not needed (embeddings only)
Use case: Provide tools to other CLIs
```

**Package 2: `aurora-cli` (CURRENT)**
```
Includes: Everything
Purpose: Standalone CLI with full SOAR
LLM: Required (Anthropic)
Use case: Direct usage
```

**Package 3: `aurora` (META-PACKAGE)**
```
Installs: Both aurora-mcp and aurora-cli
Purpose: Everything
```

**Package 4-9: Current packages remain**
```
For advanced users who want specific components
```

### Recommendation

**Option A (SIMPLEST)**:
1. Keep current 6 packages as-is
2. Add `aurora-mcp` as 7th package
3. Add `aurora` as meta-package (installs everything)

**Option B (CLEANER)**:
1. Consolidate into single `aurora` package with:
   - `aurora.mcp` module (MCP server)
   - `aurora.cli` module (CLI commands)
   - `aurora.core`, `aurora.soar`, etc. (internals)
2. Single install: `pip install aurora`
3. Can use either MCP or CLI or both

**My Vote**: Option B (cleaner, less confusing)

---

## Strategic Roadmap

### Phase 1: Critical Fixes (TODAY - 2 hours)

**Goal**: Make AURORA minimally usable

**Tasks**:
1. Fix `aur init` Path shadowing bug (5 min)
2. Fix `aur mem index` add_chunk API mismatch (15 min)
3. Fix dry-run import error (5 min)
4. Fix headless UX (add --headless flag alias) (10 min)
5. Test all fixes (30 min)
6. Commit and push

**Deliverable**: AURORA CLI works for basic operations

**Blockers Removed**: User can init, index, search memory

---

### Phase 2: MCP Server MVP (THIS WEEK - 2-3 days)

**Goal**: AURORA provides tools via MCP (no LLM calls needed)

**Day 1: MCP Server Setup**
- [ ] Create `packages/mcp/` structure
- [ ] Install FastMCP or MCP SDK
- [ ] Basic server scaffold
- [ ] Test MCP server starts

**Day 2: Implement Tools**
- [ ] Tool: `search_code()` - uses HybridRetriever
- [ ] Tool: `index_directory()` - uses MemoryManager
- [ ] Tool: `get_stats()` - uses MemoryStore
- [ ] Tool: `get_context()` - retrieves chunks

**Day 3: Integration & Testing**
- [ ] Test MCP server with Claude Code CLI
- [ ] Test with other CLIs if possible
- [ ] Document configuration
- [ ] Create examples

**Deliverable**: AURORA MCP server that user can connect their CLIs to

**Value**: User can use AURORA with their existing API keys via their preferred CLIs

---

### Phase 3: Multi-Provider Support (NEXT WEEK - 3-5 days)

**Goal**: AURORA CLI works with GLM/Synthetic/Fireworks (not just Anthropic)

**Why**: If user wants to use `aur query` directly (not via MCP)

**Tasks**:
- [ ] Abstract LLM interface
- [ ] Add GLM provider
- [ ] Add Synthetic provider
- [ ] Add Fireworks provider
- [ ] Add provider selection in config
- [ ] Test with user's API keys

**Deliverable**: `aur query` works with any provider

**Note**: Lower priority than MCP - user can use CLIs via MCP instead

---

### Phase 4: Package Consolidation (FUTURE)

**Goal**: Simplify installation and imports

**Decision Point**: Gather user feedback first
- Do current 6 packages confuse users?
- Is MCP server popular enough to justify separate package?
- Should we consolidate everything?

**Defer until**: v2.0 or user demand

---

## Devil's Advocate: What Are We Overcomplicating?

### Question 1: Do we need SOAR pipeline in MCP mode?
**Current**: AURORA has complex SOAR orchestration
**Reality**: MCP tools just need search/index - no orchestration

**Implication**: MCP server can be much simpler than full AURORA

---

### Question 2: Do we need multiple LLM providers?
**Current**: Hardcoded to Anthropic
**User Need**: Use with GLM/Synthetic/Fireworks via their CLIs

**Implication**: MCP approach solves this WITHOUT multi-provider support in AURORA!

---

### Question 3: Are we building the right thing?
**What we built**: Complex cognitive architecture with SOAR pipeline
**What user needs**: Fast code search via MCP

**Possible Pivot**:
- Focus AURORA on being the BEST code memory/search via MCP
- Let other CLIs handle the reasoning/orchestration
- Specialize rather than generalize

---

### Question 4: Is 6 packages too complex?
**Current**: 6 separate packages
**Reality**: Most users want "just install it"

**Implication**: Consolidate to 1-2 packages, make internals private

---

## Controversial Takes

### Take 1: AURORA Should Be MCP-First
Instead of building a CLI with MCP support, build an MCP server with CLI support.

**Why**:
- User has multiple CLIs already
- MCP is the integration point
- CLI is just one way to access AURORA

**Restructure**:
```
aurora-mcp (CORE)
  ├── Memory management
  ├── Search/retrieval
  └── MCP server

aurora-cli (OPTIONAL)
  └── CLI wrapper around aurora-mcp
```

---

### Take 2: Drop SOAR Pipeline from MCP Mode
SOAR is complex. MCP tools should be simple, fast, focused.

**MCP Mode**: Just search/index - no orchestration
**CLI Mode**: Full SOAR pipeline

**Why**: Different use cases, different needs

---

### Take 3: Embeddings Are The Only "LLM" We Need
AURORA MCP server doesn't need GPT-4 or Claude.
It needs:
- Fast embeddings (Sentence-BERT, local model)
- Hybrid search
- Activation spreading

**Implication**: Can work 100% offline with local embeddings

---

### Take 4: We're Solving Too Many Problems
AURORA tries to be:
1. Memory management system ✓
2. Code indexer ✓
3. Hybrid retrieval ✓
4. LLM orchestrator ✓
5. SOAR cognitive architecture ✓
6. CLI tool ✓
7. MCP server ✓ (soon)

**Question**: Should we pick 2-3 and be great at those?

---

## Immediate Action Plan (Next 2 Hours)

### Step 1: Fix Critical Bugs (30 min)

1. **Fix `aur init` Path bug**
   ```python
   # Remove line 88 duplicate import
   ```

2. **Fix `aur mem index` API mismatch**
   ```python
   # Change: memory_store.add_chunk(...)
   # To: chunk.embeddings = embedding.tobytes()
   #     memory_store.save_chunk(chunk)
   ```

3. **Fix dry-run import**
   ```python
   # Change: from aurora_core.store.hybrid_retriever
   # To: from aurora_context_code.semantic.hybrid_retriever
   ```

4. **Add --headless flag alias**
   ```python
   # Add @cli.command("headless") as global --headless option
   ```

### Step 2: Test Fixes (30 min)

```bash
# Test init
rm -rf ~/.aurora
aur init

# Test indexing
aur mem index packages/

# Test search
aur mem search "SQLiteStore"

# Test dry-run
aur query "test" --dry-run

# Test headless
aur --headless test.md  # Should work now
```

### Step 3: Commit & Push (10 min)

```bash
git add .
git commit -m "fix: resolve critical bugs in CLI (init crash, indexing, imports)"
git push
```

### Step 4: User Testing (50 min)

User tests with GLM/Synthetic/Fireworks keys (won't work yet, but bugs should be fixed)

---

## PRD Outline: AURORA MCP Integration & Bug Fixes

### Phase 1: Critical Bug Fixes ✓
- Fix init crash
- Fix indexing
- Fix imports
- Fix UX issues

### Phase 2: MCP Server (Core Value)
- Implement MCP server
- Tools: search, index, stats, context
- No LLM calls needed
- Works with any CLI via MCP

### Phase 3: Multi-Provider Support (Optional)
- Only if user wants standalone CLI with non-Anthropic keys
- Abstract LLM interface
- Add GLM, Synthetic, Fireworks providers

### Phase 4: Package Restructure (Future)
- Based on user feedback
- Consolidate vs keep modular
- Defer decision

---

## Questions for User

1. **MCP Priority**: Is MCP server your #1 need? (seems yes)

2. **Standalone CLI**: Do you also want `aur query` to work with GLM/Synthetic/Fireworks? Or is MCP enough?

3. **Package Structure**: Do 6 packages confuse you? Want single install?

4. **Use Case**: Primary goal is:
   - [ ] Search code from other CLIs via MCP
   - [ ] Use AURORA CLI directly with non-Anthropic keys
   - [ ] Both

5. **Embeddings**: Should AURORA use:
   - [ ] Anthropic embeddings (requires API)
   - [ ] OpenAI embeddings (requires API)
   - [ ] Local embeddings (Sentence-BERT, free)
   - [ ] Let user choose

---

## Recommendation

**Immediate** (TODAY):
1. ✅ Fix all 4 critical bugs (I can do this now)
2. ✅ User tests fixes
3. ✅ Verify AURORA CLI works

**Short-term** (THIS WEEK):
1. ✅ Build MCP server (2-3 days)
2. ✅ User tests with their CLIs
3. ✅ Iterate based on feedback

**Medium-term** (NEXT WEEK):
1. ? Add multi-provider if needed
2. ? Package restructure if needed
3. ✅ Documentation and examples

**What do you want me to start with?**
- Option A: Fix bugs now (30 min), then MCP
- Option B: Create detailed PRD first, then fix
- Option C: Fix bugs + start MCP in parallel
