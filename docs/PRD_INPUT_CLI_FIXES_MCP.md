# PRD Input: AURORA CLI Fixes, Package Consolidation & MCP Integration

**Date**: December 24, 2025
**Status**: Ready for PRD creation
**Goal**: Fix all CLI issues, consolidate packages, add MCP server support

---

## 1. CLI Fixes Required

### Critical Bugs (BLOCKING - Already Fixed in Code)

#### Bug 1: `aur init` crashes with Path shadowing
- **Status**: ✅ FIXED
- **Location**: `packages/cli/src/aurora_cli/commands/init.py:88`
- **Issue**: Duplicate `from pathlib import Path` inside function shadowed top-level import
- **Fix Applied**: Removed duplicate import
- **Test Status**: NEEDS VERIFICATION

#### Bug 2: `aur mem index` broken - API mismatch
- **Status**: ✅ FIXED
- **Location**: `packages/cli/src/aurora_cli/memory_manager.py:509-543`
- **Issue**: Called non-existent `memory_store.add_chunk()` instead of `save_chunk()`
- **Fix Applied**:
  - Refactored to use `chunk.embeddings = embedding.tobytes()`
  - Changed to `memory_store.save_chunk(chunk)`
  - Renamed method to `_save_chunk_with_retry()`
- **Test Status**: NEEDS VERIFICATION

#### Bug 3: Dry-run import error
- **Status**: ✅ FIXED
- **Location**: `packages/cli/src/aurora_cli/main.py:342, 445`
- **Issue**: Wrong module path `aurora_core.store.hybrid_retriever`
- **Fix Applied**: Changed to `aurora_context_code.semantic.hybrid_retriever`
- **Test Status**: NEEDS VERIFICATION

### Medium Priority Issues

#### Issue 4: Headless syntax confusion
- **User Tried**: `aur --headless test.md`
- **Actual Syntax**: `aur headless test.md`
- **Proposal**: Add `--headless` as global flag that maps to headless command
- **Status**: NOT YET FIXED

---

## 2. Package Consolidation

### Current State: 6 Separate Packages
```
aurora-core
aurora-context-code
aurora-soar
aurora-reasoning
aurora-cli
aurora-testing
```

**Problems**:
- ❌ User confusion about what to install
- ❌ Verbose imports (`aurora_context_code.semantic.hybrid_retriever`)
- ❌ Complex dependency management
- ❌ No clear "just install it" option

### Desired State: Single Package

**User Requirement**: "one package to install all"

**Proposed Structure**:
```
aurora/
├── pyproject.toml          # Single package
├── README.md
└── src/aurora/
    ├── __init__.py
    ├── core/               # Store, activation, chunks
    ├── context_code/       # Parsing, embeddings, retrieval
    ├── soar/               # Orchestrator, phases
    ├── reasoning/          # LLM client, prompts
    ├── cli/                # CLI commands
    ├── mcp/                # MCP server (NEW)
    └── testing/            # Test utilities
```

**Installation**:
```bash
pip install aurora
# Done - everything installed
```

**Imports**:
```python
from aurora.core import SQLiteStore
from aurora.context_code.semantic import HybridRetriever
from aurora.cli import main
```

**Benefits**:
- ✅ Single install command
- ✅ Clearer imports
- ✅ No package confusion
- ✅ Simpler to maintain

---

## 3. Installation Feedback Requirements

### User Requirement: "no verbose installation with clear pass/fail"

**Current State**:
- Pip install shows verbose output
- No clear success/failure indication
- No dependency check feedback

**Desired State**:

#### During Installation:
```bash
$ pip install aurora

Installing aurora v0.2.0...
✓ Core components
✓ Memory management
✓ Context parsing
✓ SOAR orchestrator
✓ CLI tools
✓ MCP server

✓ AURORA installed successfully!

Next steps:
  aur init              # Initialize configuration
  aur mem index .       # Index your codebase
  aur --help            # See all commands
```

#### After Installation - Verification:
```bash
$ aur --verify

Checking AURORA installation...
✓ Core packages installed
✓ CLI available
✓ MCP server available
✓ Python version: 3.10+ (OK)
✓ Dependencies: All satisfied

✓ AURORA is ready to use!
```

#### If Missing Dependencies:
```bash
$ aur --verify

Checking AURORA installation...
✓ Core packages installed
✓ CLI available
✗ ML dependencies missing (embeddings will not work)

  To enable semantic search:
  pip install aurora[ml]

⚠ AURORA partially installed - basic features available
```

**Implementation**:
- Post-install hook that shows summary
- `aur --verify` command for health check
- Clear pass/fail indicators
- Actionable error messages

---

## 4. MCP Integration Architecture

### User Clarification: MCP WITHOUT LLM

**Key Insight**: User uses Claude Code CLI (which already has Claude). AURORA MCP server provides TOOLS to Claude, not LLM calls.

**Architecture**:
```
┌─────────────────────────────┐
│ Claude Code CLI             │
│ (User chats with Claude)    │
│                             │
│ Claude internally calls:    │
│  aurora_search("auth")      │ ← MCP tool
└──────────────┬──────────────┘
               │ MCP Protocol
               ▼
┌─────────────────────────────┐
│ AURORA MCP Server           │
│                             │
│ Tools (NO LLM):             │
│ - search_code()             │ ← Hybrid retrieval
│ - index_files()             │ ← Memory indexing
│ - get_stats()               │ ← Memory stats
│ - get_context()             │ ← Code retrieval
│ - activate_related()        │ ← ACT-R spreading
│                             │
│ Uses: Local embeddings      │
│ NO API KEY NEEDED           │
└─────────────────────────────┘
```

### MCP Tools to Implement

#### Tool 1: `aurora_search`
```python
@mcp_tool()
def aurora_search(query: str, limit: int = 10) -> List[Dict]:
    """Search indexed codebase using hybrid retrieval.

    Args:
        query: Search query (natural language or keywords)
        limit: Maximum results to return

    Returns:
        List of code chunks with file path, function name, content, relevance score
    """
```

#### Tool 2: `aurora_index`
```python
@mcp_tool()
def aurora_index(path: str, pattern: str = "*.py") -> Dict:
    """Index files into AURORA memory.

    Args:
        path: Directory path to index
        pattern: File pattern to match

    Returns:
        IndexStats: files indexed, chunks created, duration
    """
```

#### Tool 3: `aurora_stats`
```python
@mcp_tool()
def aurora_stats() -> Dict:
    """Get memory store statistics.

    Returns:
        MemoryStats: total chunks, files, database size
    """
```

#### Tool 4: `aurora_context`
```python
@mcp_tool()
def aurora_context(file_path: str, function: str = None) -> str:
    """Retrieve code context for specific file/function.

    Args:
        file_path: Path to source file
        function: Optional specific function name

    Returns:
        Code content with context
    """
```

#### Tool 5: `aurora_related`
```python
@mcp_tool()
def aurora_related(chunk_id: str, max_hops: int = 2) -> List[Dict]:
    """Find related code chunks using ACT-R spreading activation.

    Args:
        chunk_id: Starting chunk identifier
        max_hops: Maximum relationship hops

    Returns:
        List of related chunks with activation scores
    """
```

### MCP Configuration

User configures in Claude Desktop settings:
```json
{
  "mcpServers": {
    "aurora": {
      "command": "aurora-mcp",
      "args": ["--db-path", "~/my-project/aurora.db"]
    }
  }
}
```

### User Workflow
```bash
# 1. Index codebase (one-time)
aur mem index ~/my-project

# 2. Start Claude Desktop (MCP auto-starts)

# 3. Chat with Claude:
User: "Search my project for authentication code"
Claude: [Calls aurora_search tool] "I found 5 functions..."

User: "Show me the LoginHandler"
Claude: [Calls aurora_context tool] "Here's the LoginHandler class..."
```

**Key Point**: NO API KEY NEEDED for MCP server. Claude Code CLI handles all LLM calls.

---

## 5. Testing Requirements

### Verification After Each Fix

**Test Suite**:
```bash
# 1. Test aur init
rm -rf ~/.aurora
aur init
# Expected: Config created, no crash

# 2. Test indexing
aur mem index packages/
# Expected: X files indexed, Y chunks created

# 3. Test search
aur mem search "SQLiteStore"
# Expected: Search results displayed

# 4. Test stats
aur mem stats
# Expected: Memory statistics shown

# 5. Test dry-run
aur query "test" --dry-run
# Expected: Shows escalation, no import error

# 6. Test MCP server
aurora-mcp --test
# Expected: MCP server starts, tools available
```

**Pass/Fail Criteria**:
- ✓ PASS: All commands execute without errors
- ✗ FAIL: Any command crashes or shows error
- ⚠ WARN: Command works but shows warnings

---

## 6. Technical Debt Consideration

### P2 Technical Debt Items (TECHNICAL_DEBT.md)

**Question**: Should we tackle P2 debt in this sprint or defer?

**P2 Items**:
1. **TD-P2-001**: LLM Client Test Coverage (51.33%)
2. **TD-P2-002**: No headless mode tests
3. **TD-P2-003**: Memory integration tests
4. **TD-P2-004**: Configuration validation tests
5. **TD-P2-005**: Store relationship traversal tests
6. **TD-P2-006**: Deprecation warnings (datetime.utcnow)
7. **TD-P2-007**: Token usage tracking missing
8. **TD-P2-008**: No retries on transient API errors

**Recommendation**:
- **Include in PRD**: TD-P2-003 (Memory integration tests) - Critical for verifying our fixes
- **Include in PRD**: TD-P2-002 (Headless tests) - We're touching CLI extensively
- **Defer**: Others to next sprint (focus on stability first)

**Rationale**:
- Integration tests will catch bugs like the ones we just found (mocks didn't catch API mismatches)
- Headless tests are quick wins while we're in CLI code
- Other P2 items are important but not blocking

---

## 7. Success Criteria

### Must Have (Release Blockers)
- [ ] All 3 critical CLI bugs fixed and verified
- [ ] Single package installation works (`pip install aurora`)
- [ ] Installation shows clear pass/fail feedback
- [ ] MCP server implemented with all 5 tools
- [ ] MCP server works with Claude Desktop
- [ ] All smoke tests pass
- [ ] Memory integration tests added (TD-P2-003)

### Should Have (High Priority)
- [ ] Headless syntax improved (`--headless` flag)
- [ ] Headless mode tests added (TD-P2-002)
- [ ] `aur --verify` command for health checks
- [ ] Clear documentation for MCP setup
- [ ] Example MCP workflows

### Nice to Have (Can Defer)
- [ ] Multi-LLM provider support (GLM, Synthetic, Fireworks)
- [ ] Remaining P2 technical debt items
- [ ] Advanced MCP features (real-time indexing, subscriptions)

---

## 8. Implementation Phases

### Phase 1: Fix & Verify CLI Bugs (1 day)
- Test all 3 bug fixes
- Add integration tests to catch similar bugs
- Verify smoke tests pass

### Phase 2: Package Consolidation (1 day)
- Restructure to single `aurora` package
- Update all imports
- Test installation from scratch
- Add installation feedback/verification

### Phase 3: MCP Server Core (2 days)
- Implement MCP server scaffold
- Add 5 core tools (search, index, stats, context, related)
- Test with Claude Desktop
- Document configuration

### Phase 4: Testing & Documentation (1 day)
- Memory integration tests (TD-P2-003)
- Headless mode tests (TD-P2-002)
- MCP setup guide
- Example workflows
- Update README

**Total Estimate**: 5 days

---

## 9. Non-Goals (Explicitly Out of Scope)

- ❌ Multi-LLM provider support (defer to next sprint)
- ❌ SOAR pipeline in MCP mode (MCP is tools-only)
- ❌ Advanced MCP features (subscriptions, real-time)
- ❌ P2 technical debt beyond TD-P2-002 and TD-P2-003
- ❌ GUI or web interface
- ❌ Cloud hosting for MCP server

---

## 10. Risks & Mitigations

### Risk 1: Package consolidation breaks existing installs
- **Mitigation**: Keep old packages as deprecated wrappers
- **Mitigation**: Add migration guide for existing users

### Risk 2: MCP integration more complex than expected
- **Mitigation**: Start with minimal viable tools
- **Mitigation**: Use FastMCP library for rapid development

### Risk 3: Tests still miss integration bugs
- **Mitigation**: Add integration tests with REAL components
- **Mitigation**: Add smoke test suite that runs after install

### Risk 4: Local embeddings not good enough
- **Mitigation**: Make embeddings provider configurable
- **Mitigation**: Default to Sentence-BERT, allow upgrade

---

## 11. User Acceptance Criteria

**User will be satisfied when**:

1. ✅ Install works with single command: `pip install aurora`
2. ✅ Clear feedback during install (pass/fail indicators)
3. ✅ `aur init` doesn't crash
4. ✅ `aur mem index .` successfully indexes their code
5. ✅ `aur mem search "query"` returns relevant results
6. ✅ MCP server works with Claude Code CLI
7. ✅ Can chat with Claude about their indexed codebase
8. ✅ No Anthropic API key required for MCP usage

**User can verify with**:
```bash
# Install
pip install aurora

# Verify
aur --verify

# Use standalone
aur init
aur mem index .
aur mem search "test"

# Use with MCP
# (Configure in Claude Desktop)
# Chat with Claude: "Search my code for authentication"
```

---

## 12. Questions for PRD Agent

1. **Phase ordering**: Should we do package consolidation before or after MCP implementation?

2. **Testing strategy**: Should we add tests as we go, or dedicate Phase 4?

3. **MCP library**: FastMCP vs official MCP SDK - which to use?

4. **Embeddings**: Should we use Sentence-BERT (local, free) or require API for embeddings?

5. **Migration**: Do we need a migration path for existing users (6 packages → 1)?

6. **P2 Debt**: Confirm we're only doing TD-P2-002 and TD-P2-003, defer others?

---

## 13. Files to Create/Modify

### New Files
- `src/aurora/mcp/server.py` - MCP server implementation
- `src/aurora/mcp/tools.py` - MCP tool implementations
- `tests/integration/test_memory_e2e.py` - Integration tests (TD-P2-003)
- `tests/unit/cli/test_headless.py` - Headless tests (TD-P2-002)
- `docs/MCP_SETUP.md` - MCP configuration guide

### Modified Files
- `pyproject.toml` - Package consolidation
- All imports throughout codebase - Package name changes
- `src/aurora/cli/main.py` - Add `--verify` command
- `docs/README.md` - Update installation instructions

### Verified Working
- `src/aurora/cli/commands/init.py` - Bug fix verified
- `src/aurora/cli/memory_manager.py` - Bug fix verified
- `src/aurora/cli/main.py` - Import fix verified

---

**READY FOR PRD CREATION**
