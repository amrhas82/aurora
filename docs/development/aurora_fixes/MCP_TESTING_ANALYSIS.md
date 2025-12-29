# Aurora MCP Integration - Root Cause Analysis

**Date**: 2025-12-28
**Analyst**: Claude Code
**Severity**: CRITICAL - Complete system failure, 15 critical bugs identified

---

## DOCUMENT STRUCTURE & PHASE MAPPING

This document contains comprehensive specifications for fixing Aurora across **2 phases**.

### Phase 1: Core Restoration (THIS PRD - Sprint 1) 🔵

| Aspect | Details |
|--------|---------|
| **Scope** | P0 + P1 issues (Database, activation, SOAR, budget, errors) |
| **Issues** | #2 (DB path), #4 (search), #15 (query), #6 (complexity), #9 (auto-escalate), #10 (budget), #11 (errors) |
| **Sprint Plan** | Days 1-6 (Lines 130-321) |
| **Effort** | 48 hours (32h code + 16h test) |
| **PRD** | **To be created** - "Aurora Phase 1: Core Restoration" |
| **Deliverable** | **v0.2.1** - Working CLI with all critical bugs fixed |
| **Success** | User completes `TESTING_AURORA_FROM_SCRATCH.md` without errors |

### Phase 2: MCP Integration & Polish (FUTURE PRD - Sprint 2) 🟢

| Aspect | Details |
|--------|---------|
| **Scope** | P2 + P3 + P4 + MCP-specific work |
| **Issues** | #1 (install UX), #5 (parse warnings), #7 (LLM warning), #8 (output), #12 (clear cmd), #13 (docs), #14 (MCP setup) |
| **Sprint Plan** | Days 7-10 (Lines 325-388) |
| **Effort** | 12-16 hours + MCP testing (12h) = 24-28 hours |
| **PRD** | **To be created later** - "Aurora Phase 2: MCP Integration & Polish" |
| **Deliverable** | **v0.3.0** - Full CLI/MCP parity with polished UX |
| **Success** | MCP auto-configures, natural language routing works, clean UX |

**Phase Boundary**: Phase 1 ends when all P0-P1 tests pass and user workflows work. Phase 2 begins after v0.2.1 release.

---

## REALITY CHECK: Actual User Testing Results

**Status**: 15 critical failures identified in real-world testing (2025-12-28)

User feedback: *"after fully testing, we almost have nothing working properly... this is detailed specs document that we will use in our major fixes... i am honestly disappointed, as the repo now looks like a spaghetti and makes me doubt all the useless tests you created and said they run perfectly"*

This document now serves as the **comprehensive specification for major fixes**.

---

## FIX PRIORITIES & ROADMAP

### ═══════════════════════════════════════════════════════════════
### 🔵 PHASE 1: CORE RESTORATION (P0 + P1) - THIS PRD
### ═══════════════════════════════════════════════════════════════

### P0 - BLOCKING (Fix First - System Unusable)
1. **Issue #2**: Database path confusion → Single DB at `~/.aurora/memory.db`
2. **Issue #4**: Search returns identical results → Fix DB path + activation tracking
3. **Issue #15**: Query doesn't use indexed data → Retrieval before LLM

**Impact**: Without these, Aurora literally doesn't work. Users get wrong results.

---

### P1 - CRITICAL (Core Features Broken)
4. **Issue #6**: Complexity assessment broken → Add domain keywords + multi-question detection
5. **Issue #9**: Auto-escalation not working → Implement confidence threshold logic
6. **Issue #10**: `aur budget` command missing → Implement budget management
7. **Issue #11**: Stack traces on errors → Add error handling + `--debug` flag

**Impact**: SOAR doesn't trigger, costs uncontrolled, poor user experience.

**Phase 1 Total**: 7 critical issues, 32 hours coding + 16 hours testing = 48 hours

---

### ═══════════════════════════════════════════════════════════════
### 🟢 PHASE 2: MCP INTEGRATION & POLISH (P2 + P3 + P4) - FUTURE PRD
### ═══════════════════════════════════════════════════════════════

### P2 - HIGH (Important Features)
8. **Issue #14**: MCP auto-setup missing → Add to `aur init`
9. **Issue #7**: Confusing "no LLM client" warning → Fix or remove warning
10. **Issue #8**: Messy output → Clean logging separation

**Impact**: Manual MCP setup required, confusing messages.

---

### P3 - MEDIUM (UX Issues)
11. **Issue #1**: Installation feedback poor → Add post-install verification
12. **Issue #5**: Parse warning mid-progress → Collect errors, show summary
13. **Issue #12**: `aur mem clear` missing → Implement command

**Impact**: Harder to use, but functional.

---

### P4 - LOW (Documentation)
14. **Issue #13**: Uninstall instructions missing → Update docs

**Impact**: Minimal, workarounds exist.

**Phase 2 Total**: 7 polish/MCP issues, 12-16 hours

---

## LOGICAL EXECUTION ORDER (TDD Approach)

### The Strategy: Test-First, Then Fix

**Why TDD?**
- ✅ Tests document expected behavior
- ✅ Tests fail now → prove the bug exists
- ✅ Fix code → tests pass → proof it works
- ✅ Never regress again

---

## SPRINT PLAN: Can We Do This in One Sprint?

### Sprint Capacity Analysis

**Standard sprint**: 10 working days (2 weeks)
**Total work**: 30-42 hours of coding + 20-30 hours of testing = **50-72 hours**
**One developer**: 6-8 hours/day × 10 days = **60-80 hours available**

**Answer: YES, barely fits in one sprint** if we:
1. Focus ruthlessly on P0-P1 only (critical path)
2. Write tests FIRST (TDD)
3. Defer P2-P4 to next sprint if needed

---

### ═══════════════════════════════════════════════════════════════
### 🔵 PHASE 1 SPRINT PLAN (10 Days) - THIS PRD
### ═══════════════════════════════════════════════════════════════

### Refined Sprint Plan (10 Days)

#### **Day 1-2: Write Failing Tests (16 hours)** [PHASE 1]

**Goal**: Document all broken behavior with tests that FAIL

**Tasks**:
1. **E2E Tests** (8 hours):
   - `test_e2e_new_user_workflow.py` - Full onboarding (fails on DB path)
   - `test_e2e_database_persistence.py` - Data survives commands (fails)
   - `test_e2e_search_accuracy.py` - Search returns relevant results (fails)
   - `test_e2e_query_uses_index.py` - Query retrieves indexed data (fails)
   - `test_e2e_complexity_assessment.py` - SOAR triggers correctly (fails)

2. **Integration Tests** (8 hours):
   - `test_integration_db_path_consistency.py` - All commands use same DB
   - `test_integration_activation_tracking.py` - record_access() called
   - `test_integration_retrieval_before_llm.py` - Context passed to LLM
   - `test_integration_budget_enforcement.py` - Queries blocked on limit
   - `test_integration_auto_escalation.py` - Low confidence → SOAR

**Deliverable**: Test suite that FAILS comprehensively (proves bugs exist)

---

#### **Day 3-4: P0 Fixes (16 hours)** [PHASE 1]

**Goal**: Make basic functionality work (search, query)

**Task 1: Database Path Unification** (6 hours)
```python
# File: packages/cli/src/aurora_cli/config.py
class Config:
    def get_db_path(self) -> Path:
        """Always return ~/.aurora/memory.db"""
        return Path.home() / ".aurora" / "memory.db"

# Update ALL commands to use config.get_db_path()
# - aurora_cli/commands/memory.py
# - aurora_cli/commands/query.py
# - aurora_cli/main.py (init command)
```

**Task 2: Activation Tracking Fix** (3 hours)
```python
# File: packages/cli/src/aurora_cli/memory_manager.py
def search(self, query: str, limit: int = 5):
    results = self._retriever.retrieve(query, top_k=limit)

    # ADD THIS: Record access for activation
    access_time = datetime.now(timezone.utc)
    for result in results:
        self._store.record_access(
            result["chunk_id"], access_time, context=query
        )

    return results
```

**Task 3: Query Retrieval Integration** (4 hours)
```python
# File: packages/cli/src/aurora_cli/execution.py
def execute_direct_llm(self, query: str):
    # ADD THIS: Retrieve context BEFORE calling LLM
    context_chunks = self.memory_manager.search(query, limit=10)

    # Format context for LLM
    context = "\n\n".join([
        f"## {c.file_path}:{c.name}\n{c.content}"
        for c in context_chunks
    ])

    # Pass context to LLM
    response = llm.generate(
        prompt=f"Context:\n{context}\n\nQuery: {query}"
    )
```

**Task 4: Fix Tests** (3 hours)
- Update existing unit tests that depend on old DB paths
- Ensure E2E tests for P0 now PASS

**Checkpoint**: Run `aur init → index → search → query` - should work ✓

---

#### **Day 5-6: P1 Fixes (16 hours)** [PHASE 1]

**Goal**: SOAR triggers, budget works, errors clean

**Task 1: Complexity Assessment** (4 hours)
```python
# File: packages/soar/src/aurora_soar/phases/assess.py
MEDIUM_KEYWORDS.update({
    # Domain terms
    "soar", "actr", "activation", "retrieval", "reasoning",
    "agentic", "marketplace", "aurora",
    # Scope indicators
    "research", "analyze", "compare", "design", "architecture",
    # Multi-part indicators
    "list all", "find all", "explain how", "show me"
})

# Add multi-question detection
def _count_questions(query: str) -> int:
    return query.count("?")

# Boost score if multiple questions
if _count_questions(query) >= 2:
    score = min(score + 0.3, 1.0)  # MEDIUM or COMPLEX
```

**Task 2: Auto-Escalation Logic** (3 hours)
```python
# File: packages/cli/src/aurora_cli/execution.py
def execute_with_auto_escalation(self, query: str):
    assessment = self._assess_complexity(query)

    # NEW: Check confidence threshold
    if assessment.confidence < 0.6:
        if self.interactive:
            # Prompt user
            choice = click.confirm("Low confidence. Use SOAR?")
            if choice:
                return self.execute_soar(query)
        else:
            # Auto-escalate in non-interactive mode
            logger.info("Auto-escalating to SOAR (low confidence)")
            return self.execute_soar(query)

    # Continue with assessed complexity
    if assessment.complexity == "COMPLEX":
        return self.execute_soar(query)
    else:
        return self.execute_direct_llm(query)
```

**Task 3: Budget Command** (4 hours)
```python
# File: packages/cli/src/aurora_cli/commands/budget.py
@click.group()
def budget():
    """Manage cost budget and spending."""
    pass

@budget.command()
def show():
    """Show current budget and spending."""
    tracker = CostTracker()
    click.echo(f"Spent: ${tracker.total_spent:.4f}")
    click.echo(f"Budget: ${tracker.budget:.4f}")
    click.echo(f"Remaining: ${tracker.budget - tracker.total_spent:.4f}")

@budget.command()
@click.argument("amount", type=float)
def set(amount):
    """Set budget limit."""
    # Update budget_tracker.json

@budget.command()
def history():
    """Show query history with costs."""
    # Read from budget_tracker.json, show table
```

**Task 4: Error Handling** (5 hours)
```python
# File: packages/cli/src/aurora_cli/main.py
@click.group()
@click.option('--debug', is_flag=True, help='Show full stack traces')
@click.pass_context
def cli(ctx, debug):
    ctx.obj = {'debug': debug}

# Wrap all commands with error handler
def handle_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except APIError as e:
            # Clean error message
            click.echo(f"✗ {e.message}")
            if click.get_current_context().obj.get('debug'):
                raise  # Show traceback in debug mode
        except Exception as e:
            click.echo(f"✗ Unexpected error: {e}")
            if click.get_current_context().obj.get('debug'):
                raise
            click.echo("Run with --debug for details")
    return wrapper
```

**Checkpoint**: SOAR triggers, budget enforced, clean errors ✓

---

### ═══════════════════════════════════════════════════════════════
### 🟢 PHASE 2 SPRINT PLAN (Days 7-10) - FUTURE PRD
### ═══════════════════════════════════════════════════════════════

#### **Day 7-8: P2 Fixes + Testing (16 hours)** [PHASE 2]

**Task 1: MCP Auto-Setup** (4 hours)
```python
# File: packages/cli/src/aurora_cli/main.py
@click.command()
def init():
    # ... existing init code ...

    # NEW: Offer MCP setup
    if click.confirm("Setup MCP integration for Claude Desktop?"):
        setup_mcp_config()

def setup_mcp_config():
    """Add Aurora MCP server to Claude Desktop config."""
    # Detect OS
    if sys.platform == "darwin":
        config_path = Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"
    elif sys.platform == "linux":
        config_path = Path.home() / ".config/Claude/claude_desktop_config.json"
    else:
        click.echo("Windows not supported yet")
        return

    # Read existing config
    # Add aurora-mcp server
    # Write back
    # Show restart instructions
```

**Task 2: Clean Output + Warning Fixes** (4 hours)
- Remove "no LLM client" warning
- Separate logging from user output
- Add execution summary

**Task 3: Full Integration Testing** (8 hours)
- Run all E2E tests → should PASS
- Test MCP server manually
- Test full user workflow from `TESTING_AURORA_FROM_SCRATCH.md`

**Checkpoint**: Full CLI + MCP working ✓

---

#### **Day 9: P3/P4 Polish (8 hours)** [PHASE 2]

**Quick wins**:
- Post-install verification
- Parse error summary
- `aur mem clear` command
- Uninstall docs

---

#### **Day 10: Final Testing + Documentation (8 hours)** [PHASE 2]

1. Run FULL test suite (all E2E + integration)
2. Manual testing with fresh install
3. Update all docs
4. Create release notes

---

### Sprint Commitment

### 🔵 PHASE 1 COMMITMENT (THIS PRD)

**MUST HAVE (P0-P1)**: 32 hours coding + 16 hours testing = **48 hours total**
- Database path: 6h
- Activation tracking: 3h
- Query retrieval: 4h
- Complexity assessment: 4h
- Auto-escalation: 3h
- Budget command: 4h
- Error handling: 5h
- Testing: 3h
- E2E test writing: 8h
- Integration test writing: 8h

**WILL HAVE**:
- ✅ Test-first approach (TDD)
- ✅ All P0-P1 tests passing
- ✅ Working CLI end-to-end
- ✅ v0.2.1 release ready

**WILL NOT HAVE** (deferred to Phase 2):
- ❌ MCP auto-setup
- ❌ MCP tool routing improvements
- ❌ Output polish
- ❌ Parse error summaries
- ❌ aur mem clear command
- ❌ Post-install verification

---

### 🟢 PHASE 2 COMMITMENT (FUTURE PRD)

**SHOULD HAVE (P2)**: 8 hours
- MCP auto-setup: 4h
- Output cleanup: 4h

**COULD HAVE (P3-P4)**: 4 hours
- Polish features

**MAY HAVE**:
- Path B (Real SOAR in MCP): 16-24h if time permits

---

### Sprint Success Criteria

**Day 2 checkpoint**:
- ✅ 15 E2E tests written and FAILING
- ✅ 10 integration tests written and FAILING

**Day 4 checkpoint**:
- ✅ P0 tests PASSING
- ✅ `aur init → index → search → query` works end-to-end

**Day 6 checkpoint**:
- ✅ P0 + P1 tests PASSING
- ✅ SOAR triggers on complex queries
- ✅ Budget enforced
- ✅ Clean error messages

**Day 8 checkpoint**:
- ✅ All critical tests PASSING
- ✅ MCP working
- ✅ User can complete `TESTING_AURORA_FROM_SCRATCH.md` without errors

**Day 10 deliverable**:
- ✅ 100% of P0-P1 complete
- ✅ 80%+ of P2 complete
- ✅ All tests passing
- ✅ Docs updated
- ✅ Ready for v0.2.1 release

---

## CRITICAL INSIGHT: Test the Core, Not the Wrapper

### The Architecture Truth

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACES                          │
├─────────────────────────────────────────────────────────────┤
│  CLI (aur commands)          │  MCP (aurora_* tools)        │
│  ↓                            │  ↓                           │
│  aurora_cli.commands.*       │  aurora.mcp.tools.*          │
│  ↓                            │  ↓                           │
│  aurora_cli.MemoryManager ←──┴──┘ (MCP calls directly)      │
├─────────────────────────────────────────────────────────────┤
│                    SHARED CORE COMPONENTS                   │
│  - SQLiteStore (aurora_core.store.sqlite)                   │
│  - HybridRetriever (aurora_context_code.semantic)           │
│  - ActivationEngine (aurora_core.activation)                │
│  - EmbeddingProvider (aurora_context_code.semantic)         │
│  - QueryExecutor (aurora_cli.execution)                     │
│  - SOAROrchestrator (aurora_soar.orchestrator)              │
└─────────────────────────────────────────────────────────────┘
```

### What This Means

**The 2,369 "passing" tests were testing units in isolation**, not the **integrated CLI workflow** that users actually experience.

**MCP and CLI share 90% of the same code**:
- Same database (SQLiteStore)
- Same retrieval (HybridRetriever)
- Same activation (ActivationEngine)
- Same embeddings (EmbeddingProvider)

**Therefore**:
- ✅ **Fix CLI → MCP fixed automatically** (shared core)
- ✅ **Test CLI end-to-end → MCP tested by proxy**
- ✅ **One comprehensive test suite** serves both interfaces

### Missing Test Coverage

**What we thought we had**: Unit tests for isolated components ✓
**What we actually need**: Integration + E2E tests for real workflows ✗

**Current test gaps**:
1. ❌ **No E2E CLI tests** - Never tested `aur init` → `aur mem index .` → `aur mem search` → `aur query` as user would
2. ❌ **No database path integration tests** - Never verified CLI respects config file DB path
3. ❌ **No activation tracking integration tests** - Tested ActivationEngine in isolation, but not that CLI actually calls `record_access()`
4. ❌ **No complexity assessment integration tests** - Tested keyword matching, but not full assess → retrieve → query flow
5. ❌ **No auto-escalation integration tests** - Logic exists but never tested end-to-end
6. ❌ **No budget enforcement integration tests** - Tested cost tracking, but not that CLI actually enforces budget limits

### Required New Tests

#### Unit Tests (Component Level)
Already have these - they passed ✓

#### Integration Tests (Multi-Component)
**MISSING - Add these**:

```python
# tests/integration/test_cli_memory_workflow.py
def test_index_then_search_same_db():
    """Test that indexing and search use same database"""
    db_path = tmp_path / "test.db"

    # Index files
    manager = MemoryManager(store, registry, embeddings)
    manager.index_directory("/path/to/code")

    # Verify chunks stored
    stats = manager.get_stats()
    assert stats.total_chunks > 0

    # Search should return results
    results = manager.search("function")
    assert len(results) > 0

def test_search_updates_activation():
    """Test that search calls record_access()"""
    # Index a file
    # Search multiple times
    # Verify activation scores increase
    # Verify access_count increments

def test_query_retrieves_from_index():
    """Test that query actually uses indexed data"""
    # Index specific code
    # Run query about that code
    # Verify retrieved chunks are passed to LLM
    # Verify answer mentions the code

def test_auto_escalation_on_low_confidence():
    """Test that low confidence triggers SOAR"""
    # Create query with low confidence
    # Verify switches from direct LLM to SOAR

def test_budget_enforcement():
    """Test that budget limit stops execution"""
    # Set budget to $0.001
    # Run expensive query
    # Verify query rejected before API call
```

#### E2E Tests (Full User Workflow)
**MISSING - Add these**:

```python
# tests/e2e/test_cli_user_workflows.py
def test_new_user_onboarding():
    """Simulate full new user experience"""
    # 1. aur init (creates config, DB)
    # 2. aur mem index . (indexes code)
    # 3. aur mem stats (shows data)
    # 4. aur mem search "test" (returns results)
    # 5. aur query "explain X" (uses indexed data)

def test_database_persistence():
    """Test that data persists across commands"""
    # aur mem index .
    # Exit
    # aur mem search (should still work)
    # aur mem stats (should show chunks)

def test_config_file_respected():
    """Test that all commands respect config.json"""
    # Create config with specific DB path
    # Run various commands
    # Verify all use same DB from config
```

#### MCP Integration Tests
**MISSING - Add these**:

```python
# tests/integration/test_mcp_cli_parity.py
def test_mcp_and_cli_return_same_results():
    """Verify MCP and CLI use same underlying code"""
    db_path = tmp_path / "test.db"

    # Index via CLI
    cli_manager = MemoryManager(...)
    cli_manager.index_directory("/path")

    # Search via CLI
    cli_results = cli_manager.search("function")

    # Search via MCP (same DB)
    mcp_tools = AuroraMCPTools(db_path)
    mcp_results = json.loads(mcp_tools.aurora_search("function"))

    # Should return identical data
    assert cli_results == mcp_results
```

### Test Pyramid (Current vs Required)

**Current** (inverted pyramid - BAD):
```
        ▲
       ███  ← 2,369 unit tests (isolated components)
      ████
     █████
    ██████
   ███      ← ~50 integration tests (some components together)
  ████
 █████
██        ← 0 E2E tests (full user workflows)
```

**Required** (proper pyramid - GOOD):
```
██        ← E2E tests (15-20 tests covering user workflows)
 ███
  ████
   ███    ← Integration tests (50-100 tests for multi-component)
    ████
     █████
      ████
       ███
        ██  ← Unit tests (2,000+ tests for isolated units)
         ▲
```

### Action Plan: Add Missing Test Layers

**Phase 1: E2E Tests (Critical)**
1. Write 15 E2E tests covering each issue from `cli_full_test.txt`
2. Run against current code → All fail ✗
3. Fix issues → Tests pass ✓
4. Never regress again

**Phase 2: Integration Tests (Important)**
1. Write 50 integration tests for component interactions
2. Cover all P0-P1 issues with integration tests
3. Ensure CLI and MCP share test coverage

**Phase 3: CI/CD Integration**
1. Add E2E test suite to CI/CD pipeline
2. Require all E2E tests pass before merge
3. Add test for each new CLI feature

### Why This Fixes MCP Too

**When we add E2E CLI tests**:
- Database path issues → Fixed for both CLI and MCP
- Activation tracking → Fixed for both (shared ActivationEngine)
- Search accuracy → Fixed for both (shared HybridRetriever)
- Complexity assessment → Fixed for both (shared SOAROrchestrator)

**MCP-specific tests only needed for**:
- Tool description routing (Claude invoking correct tool)
- JSON response formatting
- MCP server startup/config
- Claude Desktop integration

**90% of MCP functionality tested via CLI E2E tests** ✓

---

## MCP-SPECIFIC TESTING SCENARIOS

While 90% of MCP is tested via CLI tests (shared core), we need **MCP-specific tests** for the 10% that's unique to MCP.

### MCP Test Categories

#### 1. Tool Invocation & Routing Tests

**Test**: Claude correctly selects MCP tools based on natural language

```python
# tests/integration/test_mcp_tool_routing.py

def test_search_intent_triggers_aurora_search():
    """Natural search language → aurora_search tool"""
    # Simulate Claude deciding which tool to use
    # Input: "search aurora for hybrid retrieval"
    # Expected: Calls aurora_search, not Bash
    assert selected_tool == "aurora_search"

def test_query_intent_triggers_aurora_query():
    """Natural query language → aurora_query tool"""
    # Input: "explain SOAR reasoning from Aurora codebase"
    # Expected: Calls aurora_query, not direct answer
    assert selected_tool == "aurora_query"

def test_aur_command_triggers_mcp_not_bash():
    """'aur X' command → MCP tool, not Bash"""
    # Input: "aur search 'function'"
    # Expected: aurora_search MCP tool
    # NOT: Bash(aur search 'function')
    assert not selected_bash
    assert selected_tool == "aurora_search"
```

**How to test**: Mock Claude's tool selection logic, test descriptions trigger correct tools

---

#### 2. JSON Response Format Tests

**Test**: MCP tools return valid JSON that Claude can parse

```python
# tests/integration/test_mcp_response_format.py

def test_aurora_search_returns_valid_json():
    """aurora_search returns parseable JSON"""
    mcp = AuroraMCPTools(db_path)
    result = mcp.aurora_search("test", limit=5)

    # Should be valid JSON
    data = json.loads(result)

    # Should have expected structure
    assert isinstance(data, list)
    assert all("file_path" in item for item in data)
    assert all("score" in item for item in data)

def test_aurora_query_returns_structured_response():
    """aurora_query returns structured JSON for Claude"""
    result = mcp.aurora_query("explain X", mode="auto")
    data = json.loads(result)

    # Required fields
    assert "answer" in data
    assert "execution_path" in data
    assert "phases" in data  # For SOAR pipeline
    assert "cost" in data

def test_aurora_stats_returns_readable_stats():
    """aurora_stats returns stats in format Claude can present"""
    result = mcp.aurora_stats()
    data = json.loads(result)

    assert "total_chunks" in data
    assert "database_size_mb" in data
```

---

#### 3. MCP Server Lifecycle Tests

**Test**: MCP server starts, stops, handles errors gracefully

```python
# tests/integration/test_mcp_server_lifecycle.py

def test_mcp_server_starts_without_errors():
    """MCP server initializes successfully"""
    server = AuroraMCPServer(db_path="~/.aurora/memory.db")
    # Should not raise
    assert server is not None

def test_mcp_server_handles_missing_db_gracefully():
    """MCP server handles missing DB without crashing"""
    server = AuroraMCPServer(db_path="/nonexistent/db.sqlite")

    # Should return error, not crash
    result = server.aurora_search("test")
    data = json.loads(result)
    assert "error" in data

def test_mcp_server_handles_concurrent_requests():
    """MCP can handle multiple tool calls in sequence"""
    server = AuroraMCPServer(db_path)

    # Call multiple tools
    server.aurora_search("test")
    server.aurora_stats()
    server.aurora_query("explain X")

    # Should not have state pollution
    # Each call should be independent
```

---

#### 4. Claude Desktop Integration Tests (Manual)

**Test**: MCP works end-to-end in actual Claude Desktop

**Manual test script**:
```bash
# 1. Setup
aur init
aur mem index /path/to/code

# 2. Add MCP config
cat >> ~/.config/Claude/claude_desktop_config.json << 'EOF'
{
  "mcpServers": {
    "aurora": {
      "command": "python",
      "args": ["-m", "aurora.mcp.server"],
      "env": {
        "AURORA_DB_PATH": "/home/user/.aurora/memory.db"
      }
    }
  }
}
EOF

# 3. Restart Claude Desktop

# 4. Test in Claude Desktop
# - "search aurora for authentication code"
# - "explain how hybrid retrieval works in aurora"
# - "show me aurora stats"

# Expected:
# - Tools called (not Bash commands)
# - Results returned correctly
# - No errors in logs
```

**Verification checklist**:
- [ ] MCP server appears in Claude Desktop logs
- [ ] Natural language triggers correct tools
- [ ] "aur X" commands use MCP tools, not Bash
- [ ] Results displayed correctly to user
- [ ] No timeout errors
- [ ] DB path from env var respected

---

#### 5. MCP vs CLI Parity Tests

**Test**: MCP and CLI return identical results for same inputs

```python
# tests/integration/test_mcp_cli_parity.py

def test_search_returns_same_results():
    """MCP aurora_search == CLI aur mem search"""
    db_path = "/tmp/test.db"

    # Index via CLI
    subprocess.run(["aur", "mem", "index", "/path/to/code"])

    # Search via CLI
    cli_result = subprocess.run(
        ["aur", "mem", "search", "function", "--output", "json"],
        capture_output=True, text=True
    )
    cli_data = json.loads(cli_result.stdout)

    # Search via MCP
    mcp = AuroraMCPTools(db_path)
    mcp_result = mcp.aurora_search("function", limit=5)
    mcp_data = json.loads(mcp_result)

    # Should return same chunks
    assert len(cli_data) == len(mcp_data)
    assert cli_data[0]["chunk_id"] == mcp_data[0]["chunk_id"]

def test_stats_returns_same_counts():
    """MCP aurora_stats == CLI aur mem stats"""
    # Index data
    # Get stats via CLI
    # Get stats via MCP
    # Should be identical
    assert cli_stats.total_chunks == mcp_stats.total_chunks
```

---

#### 6. MCP Error Handling Tests

**Test**: MCP tools return clean errors, not exceptions

```python
# tests/integration/test_mcp_error_handling.py

def test_search_empty_db_returns_empty_results():
    """Searching empty DB returns [], not error"""
    mcp = AuroraMCPTools("/tmp/empty.db")
    result = mcp.aurora_search("test")
    data = json.loads(result)

    assert data == []  # Empty results, not error

def test_invalid_db_path_returns_error_json():
    """Invalid DB path returns {"error": "..."}, not crash"""
    mcp = AuroraMCPTools("/nonexistent/path.db")
    result = mcp.aurora_search("test")
    data = json.loads(result)

    assert "error" in data
    assert "database" in data["error"].lower()

def test_query_without_api_key_returns_helpful_error():
    """Query without API key returns clear error"""
    # Unset API key
    os.environ.pop("ANTHROPIC_API_KEY", None)

    mcp = AuroraMCPTools(db_path)
    result = mcp.aurora_query("explain X")
    data = json.loads(result)

    assert "error" in data
    assert "api key" in data["error"].lower()
```

---

#### 7. MCP Tool Description Accuracy Tests

**Test**: Tool descriptions accurately reflect behavior

```python
# tests/integration/test_mcp_tool_descriptions.py

def test_aurora_search_description_matches_behavior():
    """aurora_search description accurately describes what it does"""
    from aurora.mcp.server import get_tools

    tools = get_tools()
    search_tool = [t for t in tools if t["name"] == "aurora_search"][0]

    # Description should mention:
    assert "hybrid" in search_tool["description"].lower()
    assert "semantic" in search_tool["description"].lower()
    assert "activation" in search_tool["description"].lower()

    # Should NOT mention things it doesn't do
    assert "llm" not in search_tool["description"].lower()  # Search doesn't call LLM

def test_tool_parameters_documented():
    """All tool parameters have clear descriptions"""
    tools = get_tools()

    for tool in tools:
        for param in tool.get("parameters", {}).get("properties", {}).values():
            # Every param should have description
            assert "description" in param
            assert len(param["description"]) > 10  # Meaningful description
```

---

### MCP Testing Priority

**P0 - MUST HAVE (blocking)**:
1. ✅ JSON response format tests (catches breaking changes)
2. ✅ MCP server lifecycle tests (server starts, handles errors)
3. ✅ MCP vs CLI parity tests (proves shared core works)

**P1 - SHOULD HAVE (important)**:
4. ✅ Tool invocation/routing tests (proves descriptions work)
5. ✅ Error handling tests (graceful degradation)

**P2 - COULD HAVE (nice to have)**:
6. ✅ Tool description accuracy tests
7. ✅ Manual Claude Desktop integration tests

---

### MCP Test Automation Strategy

**Unit tests**: Test individual MCP tool methods
```bash
pytest tests/unit/mcp/
```

**Integration tests**: Test MCP + CLI interaction
```bash
pytest tests/integration/test_mcp_*.py
```

**Manual tests**: Test in actual Claude Desktop
```bash
# Use manual test checklist
# Document results in test report
```

**CI/CD**: Run automated MCP tests on every commit
```yaml
# .github/workflows/test.yml
- name: Test MCP Server
  run: |
    pytest tests/integration/test_mcp_*.py
```

---

### Total MCP Testing Effort

**Writing tests**: 8 hours
- JSON format tests: 2h
- Server lifecycle tests: 2h
- Parity tests: 2h
- Error handling tests: 2h

**Manual testing**: 4 hours
- Claude Desktop integration: 2h
- Tool routing verification: 2h

**Total**: 12 hours (fits in Day 7-8 of sprint)

---

## ═══════════════════════════════════════════════════════════════
## DETAILED ISSUE SPECIFICATIONS (Reference for Both Phases)
## ═══════════════════════════════════════════════════════════════

## CRITICAL FAILURES FROM ACTUAL TESTING

### 🔵 PHASE 1 ISSUES (P0 + P1 - THIS PRD)

The following issues (#2, #4, #6, #9, #10, #11, #15) are in scope for Phase 1.

---

### 🟢 PHASE 2 ISSUES (P2 + P3 + P4 - FUTURE PRD)

### Issue #1: Installation Feedback Poor [PHASE 2]
**Severity**: MEDIUM - UX Issue

**Problem**: `pip install aurora-actr` shows no clear success/failure per package

**Current behavior**:
```
Requirement already satisfied: aurora-actr in /home/hamr/.local/lib/python3.10/site-packages (0.2.0)
Requirement already satisfied: aurora-reasoning in /home/hamr/.local/lib/python3.10/site-packages (from aurora-actr) (0.1.0)
...
```

**Expected behavior**:
```
Installing aurora-actr...
✓ aurora-core installed successfully
✓ aurora-reasoning installed successfully
✓ aurora-context-code installed successfully
✓ aurora-soar installed successfully
✓ aurora-cli installed successfully
✓ aurora-testing installed successfully

Aurora v0.2.0 installed successfully!
```

**Fix Required**:
- Add post-install script that verifies each package
- Show clear success/failure per component
- Indicate missing optional dependencies (e.g., `sentence-transformers`)

---

### Issue #2: Database Path Confusion (CRITICAL) [PHASE 1 - P0]
**Severity**: CRITICAL - Data loss risk, multiple DBs created

**Problem**: Aurora creates/uses multiple database locations inconsistently

**Evidence**:
- `aur init` creates `~/.aurora/memory.db`
- `aur mem stats` reads from `/home/hamr/PycharmProjects/aurora/aurora.db`
- `aur mem search` reads from `/home/hamr/PycharmProjects/aurora/aurora.db`
- User deletes `~/.aurora/memory.db` but searches still return results

**Root cause**: CLI uses **local `aurora.db`** when run from project directory, **ignoring** `~/.aurora/memory.db`

**Fix Required**:
1. **Single source of truth**: Always use `~/.aurora/memory.db` (user's home directory)
2. **Never create local `aurora.db`** in project directories
3. **Config file must specify DB path** and all commands must respect it
4. **Migration**: Warn users if local `aurora.db` exists, offer to migrate to `~/.aurora/`

---

### Issue #3: Indexing Shows 4933 Chunks, Stats Show 0 (CRITICAL) [PHASE 1 - P0]
**Severity**: CRITICAL - Data not persisted

**Problem**: Indexing reports success but data not actually stored

**Evidence**:
```bash
aur init
# Output: ✓ Indexed 219 files, 4933 chunks in 275.69s

aur mem stats
# Output: Total Chunks: 0, Total Files: 0
```

**Root cause**: Indexing writes to **one database**, stats reads from **different database** (see Issue #2)

**Fix Required**: Same as Issue #2 - enforce single DB path

---

### Issue #4: All Search Results Identical (CRITICAL) [PHASE 1 - P0]
**Severity**: CRITICAL - Search completely broken

**Problem**: All searches return same 5 results with identical scores (1.000), regardless of query

**Evidence**:
```bash
aur mem search "where is sora reasoning script?"
# Returns: tools.py methods, all score 1.000

aur mem search "where can i find sqllite script?"
# Returns: SAME tools.py methods, all score 1.000

aur mem search "where can i find payment authentication?"
# Returns: SAME tools.py methods, all score 1.000
```

**Additional issues**:
- Line ranges show `0-0` (broken metadata)
- Activation scores all 1.000 (normalization breaks when all equal)
- Semantic scores all 1.000 (embeddings not working?)
- Returns same file for unrelated queries

**Root causes**:
1. **Activation tracking broken** - all chunks have base_level=0.0 (see original Issue #1)
2. **Wrong database** - searching in wrong DB or DB is empty (see Issue #2)
3. **Line range metadata missing** - parser not storing correct line numbers
4. **Embeddings not working** - semantic scores shouldn't all be 1.000

**Fix Required**:
1. Fix database path (Issue #2)
2. Fix activation tracking (add `record_access()` calls)
3. Fix metadata storage (line ranges)
4. Verify embeddings are actually computed during indexing

---

### Issue #5: Indexing Shows Parse Warning at 8% [PHASE 2 - P3]
**Severity**: LOW - Cosmetic, but should be clearer

**Problem**: Warning appears mid-progress without context

**Evidence**:
```
⠏ Indexing files ━━━╺━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   8%WARNING:aurora_context_code.languages.python:Parse errors in /home/hamr/PycharmProjects/aurora/tests/fixtures/sample_python_files/broken.py, extracting partial results
  Indexing files ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
✓ Indexed 219 files, 4933 chunks in 275.69s
```

**Expected behavior**:
```
⠏ Indexing files ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   8%
⚠ Parse error in tests/fixtures/sample_python_files/broken.py (partial results extracted)
  Indexing files ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%

✓ Indexed 219 files, 4933 chunks in 275.69s
⚠ 1 file had parse errors (partial data indexed)
```

**Fix Required**:
- Collect errors during indexing
- Show clean summary at end
- Don't interrupt progress bar with warnings

**User question**: *"is aur mem index for codebase ast treesitter with git add history?"*
**Answer**: Currently NO - only AST via tree-sitter. Git history integration is a future feature (could use git blame for initial activation scores).

---

### Issue #6: Complexity Assessment Completely Broken (CRITICAL) [PHASE 1 - P1]
**Severity**: CRITICAL - Core SOAR feature doesn't work

**Problem**: All queries classified as SIMPLE, even obviously complex ones

**Evidence**:
```bash
# Query #1: Obviously complex multi-part question
aur query "research agentic ai market? who are the top players? what features every one? when should i choose agentic ai with code vs persona md files for agentic ai? which is better for what job?" --dry-run

# Result:
Complexity: SIMPLE
Score: 0.143
Confidence: 0.460
Decision: Would use: Direct LLM

# Query #2: Simple listing request
aur query "list all functions in the codebase" --non-interactive

# Result:
Complexity: SIMPLE (should be MEDIUM)
Score: 0.167
Confidence: 0.233
```

**Root cause**: Keyword-based assessment uses generic programming keywords, misses:
- Aurora/AI domain terms (SOAR, ACT-R, agentic, marketplace)
- Multi-part questions (?, multiple questions)
- Scope indicators ("research", "analyze", "compare")
- Context-specific terms

**Fix Required**:
1. Add domain-specific keywords (Issue #3 in original doc)
2. Add multi-question detection (count `?`)
3. Add scope keywords ("research", "analyze", "compare", "design", "architecture")
4. Increase MEDIUM threshold from current settings

---

### Issue #7: "No LLM client provided" Warning is Confusing [PHASE 2 - P2]
**Severity**: MEDIUM - User confusion

**Problem**: Warning says "no LLM client provided" even when API key is configured

**Evidence**:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
aur query "where can i find agentic ai marketplace?"

# Output:
WARNING:aurora_soar.phases.assess:Keyword assessment borderline or low confidence (confidence=0.438, score=0.286), but no LLM client provided. Using keyword result.
→ Using Direct LLM (fast mode)
# [Then successfully calls LLM and returns answer]
```

**Contradiction**: Says "no LLM client" but then USES LLM successfully!

**Root cause**: Assessment phase doesn't have LLM client (by design), but warning is misleading

**Fix Required**:
Change warning to:
```
INFO: Using keyword-based assessment (confidence: 0.438, score: 0.286)
      For more accurate assessment, enable LLM-based complexity verification
```

Or remove warning entirely if using keyword-only by design.

---

### Issue #8: Query Output is Messy (MEDIUM) [PHASE 2 - P2]
**Severity**: MEDIUM - UX issue

**Problem**: Warning appears inline with output, unclear separation

**Evidence**:
```bash
WARNING:aurora_soar.phases.assess:Keyword assessment borderline or low confidence...
→ Using Direct LLM (fast mode)

Response:
╭────────────────────────────────────────────────────────╮
│ Answer here...                                         │
```

**Expected behavior**:
```bash
Assessing query complexity...
→ Complexity: SIMPLE (confidence: 0.438)
→ Using Direct LLM (fast mode)

╭────────────────────────────────────────────────────────╮
│ Answer here...                                         │
╰────────────────────────────────────────────────────────╯

Execution: 2.3s | Cost: $0.012
```

**Fix Required**:
- Clean up logging vs user output
- Use Rich console consistently
- Show complexity assessment clearly (not as warning)
- Add execution summary at end

---

### Issue #9: Auto-Escalation Not Working (CRITICAL) [PHASE 1 - P1]
**Severity**: CRITICAL - Feature doesn't exist

**Problem**: System never auto-escalates from SIMPLE → SOAR, even with `--non-interactive`

**Evidence**:
```bash
aur query "list all functions in the codebase" --non-interactive

# Expected: Low confidence → Auto-escalate to SOAR
# Actual: Uses Direct LLM, doesn't access indexed codebase
```

**Root cause**: Auto-escalation logic not implemented (or broken)

**Fix Required**:
1. Implement confidence threshold check
2. If confidence < 0.6 → escalate to SOAR
3. In `--non-interactive` mode → auto-escalate without prompt
4. In interactive mode → prompt user

---

### Issue #10: `aur budget` Command Doesn't Exist (CRITICAL) [PHASE 1 - P1]
**Severity**: CRITICAL - Documented feature missing

**Problem**: Command documented in help/guides but not implemented

**Evidence**:
```bash
aur budget
# Error: No such command 'budget'.

aur budget --help
# Error: No such command 'budget'.
```

**Fix Required**: Implement `aur budget` command with:
- `aur budget` - Show current spending
- `aur budget set <amount>` - Set budget limit
- `aur budget reset` - Reset spending to $0
- `aur budget history` - Show query history with costs

---

### Issue #11: Invalid API Key Shows Stack Trace (HIGH) [PHASE 1 - P1]
**Severity**: HIGH - Poor error handling

**Problem**: Full Python traceback shown to user instead of clean error

**Evidence**:
```bash
aur query "explain everything"
# (with invalid API key)

# Output: 50+ lines of traceback ending with:
aurora_cli.errors.APIError: [bold red][API][/] Authentication failed.
...
Traceback (most recent call last):
  File "/home/hamr/PycharmProjects/aurora/packages/reasoning/src/aurora_reasoning/llm_client.py", line 260, in generate
...
```

**Expected behavior**:
```bash
✗ Authentication failed

Invalid API key.

Solutions:
  1. Check your API key: export ANTHROPIC_API_KEY=sk-ant-...
  2. Get a new key at: https://console.anthropic.com
  3. Update config: aur init
```

**Fix Required**:
- Catch `AuthenticationError` at top level
- Show ONLY user-friendly message (no traceback)
- Add `--debug` flag to show traceback if needed

---

### Issue #12: `aur mem clear` Command Doesn't Exist (MEDIUM) [PHASE 2 - P3]
**Severity**: MEDIUM - Documented feature missing

**Problem**: Command mentioned in testing guide but not implemented

**Evidence**:
```bash
aur mem clear
# Error: No such command 'clear'.
```

**Fix Required**: Implement `aur mem clear` with confirmation prompt:
```bash
aur mem clear
# Warning: This will delete all indexed chunks. Continue? [y/N]:
```

---

### Issue #13: Uninstall Instructions Missing (LOW) [PHASE 2 - P4]
**Severity**: LOW - Documentation gap

**User question**: *"how do i uninstall pypi or pip?"*

**Fix Required**: Add to docs:
```bash
# Uninstall Aurora
pip uninstall aurora-actr aurora-core aurora-context-code aurora-soar aurora-reasoning aurora-cli aurora-testing

# Or use convenience script
aurora-uninstall
```

---

### Issue #14: MCP Configuration Not Auto-Setup (HIGH) [PHASE 2 - P2]
**Severity**: HIGH - Feature incomplete

**User feedback**: *"mcp configuration didn't happen on it's own. when you use aur init it should index, get api key, add configuration"*

**Problem**: `aur init` should configure MCP but doesn't

**Expected behavior**:
```bash
aur init
# 1. Prompt for API key
# 2. Create config files
# 3. Index current directory (with confirmation)
# 4. Setup MCP integration (add to claude_desktop_config.json)
# 5. Show next steps
```

**Fix Required**:
- Add MCP setup to `aur init`
- Detect OS (Linux/Mac/Windows)
- Add server config to appropriate location
- Show instructions for restarting Claude Desktop

---

### Issue #15: Query Doesn't Use Indexed Codebase (CRITICAL) [PHASE 1 - P0]
**Severity**: CRITICAL - Core feature broken

**Problem**: Queries don't retrieve from indexed codebase, even when relevant

**Evidence**:
```bash
aur init  # Indexes 4933 chunks
aur query "list all functions in the codebase"

# Expected: Retrieves from indexed chunks, lists actual functions
# Actual: Ignores indexed data, gives generic answer about how to list functions
```

**Root cause**: Query execution doesn't retrieve from memory store

**Fix Required**:
1. Fix database path (Issue #2)
2. Ensure retrieval happens BEFORE LLM call
3. Pass retrieved chunks to LLM as context
4. Show which files/chunks were used

---

## Original Issues (Now Superseded by Real Testing)

## Issue #1: All Search Results Identical (CRITICAL)

### Root Cause

**All chunks have activation score = 0.0 in the database**

Evidence from `/home/hamr/PycharmProjects/aurora/aurora.db`:
```sql
SELECT * FROM activations LIMIT 5;
-- ALL rows: base_level=0.0, access_count=0
```

### Why This Breaks Search

1. **HybridRetriever scoring formula** (60% activation + 40% semantic):
   ```python
   # All activation scores = 0.0
   activation_norm = [1.0, 1.0, 1.0, ...]  # Normalized to 1.0 when all equal

   # Semantic scores are similar for related code
   semantic_norm = [0.85, 0.83, 0.82, ...]

   # Hybrid scores become nearly identical
   hybrid = 0.6 * 1.0 + 0.4 * semantic_norm
          = [0.94, 0.932, 0.928, ...]  # Minimal variation
   ```

2. **Normalization amplifies the problem**:
   - `_normalize_scores()` at line 296 of `hybrid_retriever.py`
   - When all scores equal: returns `[1.0] * len(scores)` (line 298)
   - This makes ALL chunks equally "activated"

3. **Result**: Queries return semi-random chunks with identical scores

### Files Affected
- `/home/hamr/PycharmProjects/aurora/packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py` (lines 174-250)
- `/home/hamr/PycharmProjects/aurora/packages/core/src/aurora_core/store/sqlite.py` (retrieve_by_activation)
- Database: `/home/hamr/PycharmProjects/aurora/aurora.db` (activations table)

### Fix Required
**Activation engine is not updating access tracking!**

Check:
1. `ActivationEngine` - does it call `store.update_access()` on chunk retrieval?
2. Indexing process - should initialize with frequency-based activation
3. Access tracking hooks - are they wired up in MCP tools?

---

## Issue #2: MCP vs CLI Invocation (USER UNDERSTANDING)

### The Confusion

User expects:
```
User: "aurora query 'SOAR reasoning'"
Claude Code: Calls MCP tool aurora_query()  ✓
```

What's actually happening:
```
User: "aurora query 'SOAR reasoning'"
Claude Code: Runs Bash command `aur query 'SOAR reasoning'`  ✗
```

### Root Cause: Natural Language Interpretation

Claude Code interprets "aurora query" as a **shell command request**, not an MCP tool invocation.

**MCP tools are invoked implicitly by context, not by CLI-like syntax!**

### How MCP Actually Works

#### ✗ WRONG (User's expectation):
```
User: "Run aurora_query on 'SOAR reasoning'"
Claude: <calls Bash: aur query 'SOAR reasoning'>
```

#### ✓ CORRECT (MCP design):
```
User: "What is SOAR reasoning in Aurora?"
Claude: <internally calls aurora_query MCP tool>
Claude: Based on the codebase... [answer with context]
```

### The Design Philosophy

**MCP Tools** = Functions Claude calls internally based on user intent
**CLI Commands** = Bash commands users/Claude execute directly

When you configure MCP, you're giving Claude **invisible tools** it uses to gather context before answering, NOT new shell commands.

### Evidence from Code

File: `/home/hamr/PycharmProjects/aurora/src/aurora/mcp/server.py` (lines 122-162)

The `aurora_query` MCP tool docstring explicitly states:
```python
"""
Retrieve relevant context from AURORA memory without LLM inference.

This tool provides intelligent context retrieval with complexity assessment
and confidence scoring. It returns structured context for the host LLM
(Claude Code CLI) to reason about, rather than calling external LLM APIs.

Note:
    No API key required. This tool runs inside Claude Code CLI which
    provides the LLM reasoning capabilities.
"""
```

This is the KEY insight: **MCP tools return context TO Claude, not answers FOR the user**

---

## Issue #3: Complexity Assessment Fails (DESIGN FLAW)

### Root Cause

Keyword-based assessment in `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/phases/assess.py` uses **generic software engineering keywords** that don't match **domain-specific technical terms**.

### Examples of Failures

Query: "Explain SOAR reasoning phases"
- Detected keywords: "explain" (simple)
- Missed: "SOAR", "reasoning", "phases" (not in keyword lists)
- Result: SIMPLE with low confidence (0.159)
- **Expected**: MEDIUM (multi-step explanation)

Query: "How does MCP setup work?"
- Detected keywords: "how" (medium), "does" (no match)
- Missed: "MCP", "setup" (setup is COMPLEX keyword but "MCP setup" is specific)
- Result: SIMPLE or MEDIUM with low confidence (0.327)
- **Expected**: MEDIUM (requires understanding architecture)

### The Keyword Gap

**Missing domain-specific terms**:
- SOAR, ACT-R, Aurora-specific concepts
- MCP, embeddings, hybrid retrieval
- Tree-sitter, AST, parsing
- Specific Aurora package names

**Why this matters**:
- Technical queries score as SIMPLE
- Low confidence triggers unnecessary LLM verification
- Cost optimization (60-70% keyword-only) fails

### Files Affected
- `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/phases/assess.py` (lines 32-171)

---

## Issue #4: API Key Requirements (EXPECTED BEHAVIOR)

### User's Question
> "Why does `aur init` ask for ANTHROPIC_API_KEY if MCP tools don't need it?"

### Answer: Two Different Systems

**MCP Tools** (no API key needed):
- Invoked by Claude Desktop/Code
- Return context only
- Claude processes context using its own API key
- Database queries, search, indexing only

**Aurora CLI** (`aur` command - requires API key):
- Standalone tool for terminal use
- Calls LLM APIs directly (Anthropic/OpenAI/Ollama)
- Needs API key to generate answers
- Full SOAR pipeline with LLM reasoning

This is **correct behavior** - they're separate interfaces to Aurora:
- MCP = Context provider for Claude
- CLI = Standalone question-answering system

---

## Proper MCP Testing Methodology

### ✗ WRONG Testing Approach

```
User: "aurora_query 'SOAR reasoning'"  # Looks like CLI command
Claude Code: <runs Bash: aur query 'SOAR reasoning'>  # Interprets as shell
```

### ✓ CORRECT Testing Approach

```
User: "Can you explain SOAR reasoning? Use the Aurora codebase."
Claude Code: <internally calls aurora_query MCP tool>
Claude Code: <reads returned chunks>
Claude Code: "Based on the Aurora codebase, SOAR reasoning consists of..."
```

### Testing Script

**Test 1: Implicit Context Retrieval**
```
User: "What files contain the HybridRetriever class in Aurora?"
Expected: Claude uses aurora_search, lists files
```

**Test 2: Specific Code Context**
```
User: "Show me the aurora_query function implementation"
Expected: Claude uses aurora_context or aurora_search, returns code
```

**Test 3: Related Code Discovery**
```
User: "What code is related to complexity assessment in Aurora?"
Expected: Claude uses aurora_search + aurora_related
```

**Test 4: Natural Follow-up**
```
User: "Explain how the hybrid retrieval scoring works"
Expected: Claude uses aurora_search for HybridRetriever code, explains
```

### Key Principle

**Never mention MCP tool names in natural language!**

Think of MCP tools like Claude's "hands" - you don't say "use your hands to pick up the cup", you just say "pick up the cup" and Claude figures out to use hands.

Similarly:
- Don't say: "Use aurora_query to find..."
- Do say: "Find information about... in Aurora"

---

## Critical Bugs Summary

| Bug | Severity | Impact | Fix Effort |
|-----|----------|--------|------------|
| Zero activation scores | CRITICAL | All searches broken | Medium - wire up access tracking |
| Complexity keywords missing | HIGH | Assessment fails on technical queries | Low - add domain keywords |
| MCP understanding gap | N/A | User confusion, not a bug | Documentation |

---

## Recommended Actions

### 1. Fix Activation Tracking (PRIORITY 1)

**Investigate**:
```bash
cd /home/hamr/PycharmProjects/aurora
# Check if ActivationEngine updates access
grep -r "update_access" packages/core/src/aurora_core/activation/

# Check if MCP tools trigger access tracking
grep -r "update_access" src/aurora/mcp/
```

**Expected behavior**:
- When `aurora_search()` retrieves chunks → call `store.update_access(chunk_id)`
- When `aurora_query()` retrieves chunks → call `store.update_access(chunk_id)`
- Activation scores should increase with each access

**Verify fix**:
```sql
-- After running searches, activation should update
SELECT chunk_id, base_level, access_count
FROM activations
ORDER BY base_level DESC
LIMIT 10;
-- Should show varying base_level values, access_count > 0
```

### 2. Enhance Complexity Keywords (PRIORITY 2)

Add to `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/phases/assess.py`:

```python
# Aurora/AI domain-specific keywords
MEDIUM_KEYWORDS.update({
    "soar", "act-r", "activation", "retrieval", "reasoning",
    "embedding", "semantic", "hybrid", "chunks", "memory",
    "mcp", "context", "query", "index", "search",
})

COMPLEX_KEYWORDS.update({
    "pipeline", "orchestration", "phase", "assessment",
    "tree-sitter", "ast", "parsing", "spreading activation",
    "actr", "cognitive", "architecture",
})
```

### 3. Update Documentation (PRIORITY 3)

Create `/home/hamr/PycharmProjects/aurora/docs/MCP_USAGE_GUIDE.md`:

```markdown
# MCP Usage Guide: How to Talk to Claude with Aurora

## The Mental Model

MCP tools are NOT shell commands. They are context providers.

### ✗ Don't do this:
"Run aurora_query on 'SOAR reasoning'"

### ✓ Do this instead:
"Explain SOAR reasoning using the Aurora codebase"

## How It Works Behind the Scenes

1. You ask a natural question about Aurora
2. Claude recognizes it needs Aurora context
3. Claude internally calls aurora_query/aurora_search
4. Claude reads the returned code chunks
5. Claude answers your question with that context

You never see the MCP tool calls - they're invisible!
```

---

## Testing Validation

### Before Fixes
```bash
# All searches return identical results
python3 << 'EOF'
import sqlite3
conn = sqlite3.connect("aurora.db")
cursor = conn.cursor()
cursor.execute("SELECT AVG(base_level), COUNT(DISTINCT base_level) FROM activations")
avg, distinct = cursor.fetchone()
print(f"Average activation: {avg}, Distinct values: {distinct}")
# Expected: Average=0.0, Distinct=1 (broken)
EOF
```

### After Fixes
```bash
# Searches should return varied scores
python3 << 'EOF'
import sqlite3
conn = sqlite3.connect("aurora.db")
cursor = conn.cursor()
cursor.execute("SELECT AVG(base_level), COUNT(DISTINCT base_level) FROM activations WHERE base_level > 0")
avg, distinct = cursor.fetchone()
print(f"Average activation: {avg}, Distinct values: {distinct}")
# Expected: Average>0.0, Distinct>100 (working)
EOF
```

---

## Conclusion

The Aurora MCP integration has solid architecture but three critical issues:

1. **Activation tracking is broken** - systematic bug affecting all retrieval
2. **Complexity keywords incomplete** - design limitation for domain queries
3. **MCP mental model unclear** - documentation/UX issue, not a bug

Once activation tracking is fixed, search quality should improve dramatically. The complexity assessment can be incrementally improved by adding domain keywords.

**Estimated Fix Time**: 4-8 hours
- Activation tracking: 3-6 hours (debugging + testing)
- Keyword additions: 30 minutes
- Documentation: 30-60 minutes

---

## Critical Discovery: SOAR Was Never Really Implemented in MCP

### The Truth About MCP SOAR Removal

**Timeline Investigation**:
- **Dec 24**: MCP implemented with SOAR (commit `e11b33b`)
- **Dec 26**: SOAR removed from MCP (commits `662a248`, `6e94e00`)
- **User Discovery**: CLI/MCP should have parity - same 6 features in both

**What Was Actually Removed**: A **placeholder/stub**, not real SOAR!

Evidence from `e11b33b:src/aurora/mcp/tools.py`:
```python
# Simulate phases (in production, this would call actual SOAR pipeline)
for i, phase_name in enumerate(phases):
    phase_start = time.time()
    logger.info(f"[{i+1}/9] {phase_name}...")

    # Simulate phase work
    time.sleep(0.01)  # Placeholder
```

**Key Finding**:
- Never imported `SOAROrchestrator`
- Used `time.sleep()` placeholders
- Returned fake answers
- PRD-0007 specified integration with `QueryExecutor` but it was never built

---

## Restoration Options Analysis

### User Requirements (Clarified)

User expects **CLI/MCP parity** with 6 core Aurora features:
1. Hybrid retrieval (ACT-R + semantic)
2. Complexity assessment
3. Auto-escalation (simple → complex)
4. **SOAR 9-phase pipeline** ← Missing from MCP
5. Agent routing
6. Pattern learning

### Three Restoration Paths

#### Path A: Shell-out to CLI (Quick Stopgap - 30 min)

**What**: Add MCP tool that calls CLI as subprocess

**Implementation**:
```python
@self.mcp.tool()
def aurora_soar_query(query: str) -> str:
    """Run full SOAR via CLI (requires API key in env)"""
    result = subprocess.run(['aur', 'query', query],
                          capture_output=True, text=True)
    return result.stdout
```

**Pros**:
- Immediate functionality
- Uses proven CLI code
- No refactoring needed

**Cons**:
- Subprocess overhead (~100-200ms)
- Doesn't leverage MCP architecture
- Duplicate API calls if used with other MCP tools

**Complexity**: ⭐ Very Low (30 minutes)

---

#### Path B: Real SOAR Integration (User's Choice - 2-3 days)

**What**: Implement actual `QueryExecutor`/`SOAROrchestrator` integration as PRD-0007 intended

**Work Required**:

1. **Import & Initialize Dependencies** (4-6 hours)
   - Import `QueryExecutor` from `aurora_cli.execution`
   - Initialize LLM clients (reasoning + solving)
   - Setup `CostTracker` and `ConversationLogger`
   - Handle API key loading in MCP context

2. **Replace Placeholder Methods** (3-4 hours)
   - Remove fake `_execute_soar()` simulation
   - Implement real SOAR pipeline call via QueryExecutor
   - Add real `_execute_direct_llm()` (not placeholder)
   - Wire up `_execute_with_auto_escalation()` to actual logic

3. **Handle Conflicts with New Code** (2-3 hours)
   - `aurora_get()` was added after removal - ensure compatibility
   - Current `_retrieve_chunks()` vs SOAR's Retrieve phase
   - Current `_assess_complexity()` heuristic vs SOAR's Assess phase
   - Session state management (last search results cache)

4. **Budget & Cost Tracking** (2-3 hours)
   - Restore `_check_budget()` with real budget tracker
   - Restore `_get_budget_error_message()`
   - Track costs across MCP tool calls
   - Handle budget exceeded scenarios

5. **Testing** (4-6 hours)
   - Archived tests won't work (they tested the fake version)
   - Write new integration tests for real SOAR
   - Test API key loading in MCP context
   - Test budget enforcement
   - Test auto-escalation logic
   - Test 9-phase execution with real LLM calls

6. **Documentation** (1-2 hours)
   - Update MCP_SETUP.md with API key requirements
   - Update CLI vs MCP comparison tables
   - Document two execution modes (simple vs SOAR)

**Files to Modify**:
- `src/aurora/mcp/tools.py` (~300 lines added/modified)
- `src/aurora/mcp/server.py` (parameter updates)
- `tests/unit/mcp/test_aurora_query_tool.py` (rewrite)
- `tests/integration/test_mcp_aurora_query_integration.py` (new)
- `docs/MCP_SETUP.md`
- `docs/TROUBLESHOOTING.md`

**Critical Dependencies to Add**:
```python
from aurora_cli.execution import QueryExecutor
from aurora_reasoning.llm_client import LLMClient
from aurora_core.budget import CostTracker
from aurora_core.logging import ConversationLogger
from aurora_soar.orchestrator import SOAROrchestrator
```

**Conflicts to Resolve**:
- `aurora_get()` session cache vs SOAR result format
- Simplified `_assess_complexity()` vs SOAR's full assessment
- Current retrieval-only flow vs full pipeline

**Complexity**: ⭐⭐⭐⭐ High (16-24 hours total)

**Estimated Timeline**: 2-3 days with testing

---

#### Path C: Document Current Limitation (Minimal)

**What**: Keep simplified MCP, document that SOAR is CLI-only

**Pros**: No code changes, honest documentation

**Cons**: Doesn't meet user's parity requirement

**Complexity**: ⭐ Very Low (1 hour)

---

## User's Decision: Path B (Real SOAR Integration) + Simple Routing

### Agreed Approach (Finalized 2025-12-28)

**Core Philosophy**: Keep it simple. Better tool descriptions > Complex routing logic.

**REJECTED Approaches** (too complex):
- ❌ Always-on mode (unnecessary with good descriptions)
- ❌ Disambiguation tool (Claude does this naturally)
- ❌ Complex confidence scoring (over-engineering)
- ❌ Wildcard/recourse tools (built into natural conversation)
- ❌ Routing configuration files (adds complexity)

**ACCEPTED Approach** (simple & effective):
1. ✅ Comprehensive tool descriptions with explicit trigger keywords
2. ✅ "USE WHEN" / "DO NOT USE" sections
3. ✅ Examples showing exact phrase matching
4. ✅ CLI command replacement notes ("use this MCP tool instead of `aur query`")
5. ✅ Test, then add aliases if needed for "aur" commands

---

### Implementation Plan: Phase 1 & 2 (Same Sprint)

#### Phase 1: Better Tool Descriptions (2 hours)

**Update all 7 MCP tools** in `src/aurora/mcp/server.py`:

1. **aurora_query** - Primary reasoning tool
2. **aurora_search** - Fast file search
3. **aurora_index** - Code indexing
4. **aurora_stats** - Statistics
5. **aurora_context** - File/function content
6. **aurora_related** - ACT-R spreading activation
7. **aurora_get** - Retrieve by index

**Each description must include**:

```python
@mcp.tool()
def tool_name(...):
    """
    One-line summary.

    Detailed explanation of what this tool does and Aurora's capabilities.

    ═══════════════════════════════════════════════════════════════

    **USE THIS TOOL WHEN**:
    ✓ User explicitly says "aurora X", "aur X", or "ask aurora"
    ✓ User mentions Aurora-specific features (list them)
    ✓ User wants specific functionality (be explicit)
    ✓ User asks about indexed codebase or Aurora memory

    **DO NOT USE THIS TOOL WHEN**:
    ✗ User wants different functionality → Use other_tool instead
    ✗ User asks general questions without Aurora context → Answer directly
    ✗ More specific cases when NOT to use this tool

    **CRITICAL - CLI REPLACEMENT**:
    When user says "aur command X", use THIS MCP TOOL, do NOT run bash.
    This tool replaces the CLI command `aur command` when inside Claude Code.

    ═══════════════════════════════════════════════════════════════

    **TRIGGER KEYWORDS** (use tool when these appear):
    Primary: aurora X, aur X, ask aurora, query aurora
    Features: SOAR, ACT-R, specific Aurora features
    Actions: search aurora, aurora search, find in aurora
    Context: indexed codebase, aurora memory, previous reasoning

    **EXAMPLES** (exact phrase matching):

    ✓ "aurora command X"
      → tool_name(args)

    ✓ "aur command X"
      → tool_name(args) [NOT bash!]

    ✗ "different request"
      → Use different_tool instead

    ═══════════════════════════════════════════════════════════════

    Args:
        param: Description

    Returns:
        Structured JSON with specific fields

    ═══════════════════════════════════════════════════════════════

    **TECHNICAL NOTES**:
    - Implementation details
    - Performance characteristics
    - Cost information

    **RELATED TOOLS**:
    - other_tool: When to use instead
    """
```

**Success criteria**:
- Each tool has 100+ line description
- Clear trigger keywords listed
- Explicit when to use / not use
- Examples cover edge cases
- CLI replacement notes prevent Bash routing

---

#### Phase 2: Test & Add Aliases if Needed (3 hours)

**Step 1: Test Routing** (1 hour)

Test matrix:

| User Input | Expected Tool | Must Work |
|-----------|---------------|-----------|
| "aurora explain X" | aurora_query | ✅ Required |
| "aur query X" | aurora_query | ⚠️ Test (might be Bash) |
| "aur search X" | aurora_search | ⚠️ Test (might be Bash) |
| "search aurora for X" | aurora_search | ✅ Required |
| "search for previous convo about X" | aurora_search | ✅ Required |
| "explain SOAR" (no aurora) | Claude direct | ✅ Required |
| "aur mem search X" | aurora_search | ⚠️ Test (might be Bash) |
| "aurora index ." | aurora_index | ✅ Required |

**Step 2: Add Aliases if "aur" Still Routes to Bash** (2 hours - conditional)

**Only if** "aur X" commands still call Bash after Phase 1:

```python
# Keep semantic primary names
@mcp.tool()
def aurora_query(...):
    """Comprehensive description from Phase 1"""
    # Real implementation

@mcp.tool()
def aurora_search(...):
    """Comprehensive description from Phase 1"""
    # Real implementation

# Add exact-match aliases
@mcp.tool()
def aur_query(query: str, mode: str = "auto", verbose: bool = False):
    """
    Alias for aurora_query. Use when user says "aur query".

    When user types "aur query X", call this tool (NOT bash command).
    This is an exact-match alias for the aurora_query tool.

    For full documentation, see aurora_query.
    """
    return aurora_query(query, mode, verbose)

@mcp.tool()
def aur_search(query: str, limit: int = 10):
    """
    Alias for aurora_search. Use when user says "aur search".

    When user types "aur search X", call this tool (NOT bash command).
    This is an exact-match alias for the aurora_search tool.

    For full documentation, see aurora_search.
    """
    return aurora_search(query, limit)

@mcp.tool()
def aur_mem_search(query: str, limit: int = 10):
    """
    Alias for aurora_search. Use when user says "aur mem search".

    When user types "aur mem search X", call this tool (NOT bash command).
    This is an exact-match alias for the aurora_search tool.

    For full documentation, see aurora_search.
    """
    return aurora_search(query, limit)
```

**Alias strategy**:
- Semantic primary tools: aurora_query, aurora_search (clear names)
- Exact-match aliases: aur_query, aur_search, aur_mem_search (CLI parity)
- Total tools: 7 primary + ~5 aliases = 12 tools

**Success criteria**:
- 95%+ correct tool selection
- "aur X" commands use MCP, not Bash
- Natural routing without configuration

---

### Declarative State Reporting (SOAR Progress)

**User requirement**: Show SOAR phases to user, but not too verbose or silent.

#### Understanding Verbosity Levels

**Q: "for options A, B, C i understand this will be verbose adjust settings from cli?"**

**A: NO - Not from CLI settings. From MCP tool parameter `verbose`.**

**How it works**:

```python
# MCP tool signature
def aurora_query(query: str, mode: str = "auto", verbose: bool = False):
    """
    Args:
        verbose: Controls output detail level
            - False (default): Brief execution summary (Option B - Recommended)
            - True: Full phase breakdown (Option C - Detailed)
    """
```

**User controls verbosity via**:
1. **Default behavior** → Option B (Informative, not overwhelming)
2. **Explicit request** → "aurora query X with details" → Claude sets `verbose=True` → Option C
3. **User preference** → "keep it brief" → Claude uses `verbose=False` → Option A/B

**NOT controlled by**: CLI config file (MCP is separate from CLI)

---

#### Option A: Minimal (Brief)

**MCP tool returns** (abbreviated JSON):
```json
{
  "answer": "SOAR is a cognitive architecture...",
  "execution_path": "soar_pipeline",
  "duration_seconds": 2.33,
  "cost": {"total_usd": 0.0234}
}
```

**Claude shows user**:
```
SOAR is a cognitive architecture with 9 phases: Assess → Retrieve →
Decompose → Verify → Route → Collect → Synthesize → Record → Respond.

[Aurora used 9-phase SOAR pipeline]
Cost: $0.0234 | Duration: 2.3s
```

**When**: Very simple queries, user wants quick answer only

---

#### Option B: Informative (RECOMMENDED - Default)

**MCP tool returns** (structured JSON):
```json
{
  "answer": "SOAR is a cognitive architecture...",
  "execution_path": "soar_pipeline",
  "phases": [
    {"name": "Assess", "summary": "Complexity: 0.67 (COMPLEX) → SOAR pipeline"},
    {"name": "Retrieve", "summary": "Found 12 chunks, confidence: HIGH (0.89)"},
    {"name": "Decompose", "summary": "3 subgoals identified, clarity: 0.92"},
    {"name": "Verify", "summary": "Quality check: PASS"},
    {"name": "Route", "summary": "Agents: General, Code Analyzer"},
    {"name": "Collect", "summary": "3 results collected from agents"},
    {"name": "Synthesize", "summary": "Coherence score: 0.94"},
    {"name": "Record", "summary": "Cached reasoning_pattern_47"},
    {"name": "Respond", "summary": "Formatted final answer"}
  ],
  "cost": {"total_usd": 0.0234, "input_tokens": 3241, "output_tokens": 687},
  "duration_seconds": 2.33,
  "sources": [{"file": "orchestrator.py", "lines": "1-24", "score": 0.95}]
}
```

**Claude shows user**:
```
**Answer**: SOAR is a cognitive architecture with 9 phases...

**How Aurora reasoned**:
• Assessed query → Complex (0.67) → Used SOAR pipeline
• Retrieved 12 code chunks with high confidence (0.89)
• Decomposed into 3 subgoals (clarity: 0.92)
• Verified quality → PASS
• Routed to General and Code Analyzer agents
• Collected 3 results from agents
• Synthesized coherent answer (0.94 coherence)
• Cached reasoning pattern for future use

**Sources**: orchestrator.py (lines 1-24)
**Cost**: $0.0234 | **Duration**: 2.3s (9 phases completed)
```

**Characteristics**:
- ✅ Answer comes first (most important)
- ✅ Key decision points shown (why SOAR was used)
- ✅ Important metrics (12 chunks, 3 subgoals, 0.94 coherence)
- ✅ Not overwhelming (one-line summaries per phase)
- ✅ User understands what Aurora did
- ❌ Not all timing details (good - not needed)

**When**: Default for all queries. Informative but not verbose.

---

#### Option C: Verbose (Detailed)

**MCP tool returns** (full JSON with timing):
```json
{
  "answer": "SOAR is a cognitive architecture...",
  "execution_path": "soar_pipeline",
  "phases": [
    {
      "name": "Assess",
      "duration": 0.12,
      "status": "completed",
      "details": {
        "complexity_score": 0.67,
        "classification": "COMPLEX",
        "decision": "Use SOAR pipeline",
        "keywords_matched": ["reasoning", "cognitive", "architecture"]
      }
    },
    {
      "name": "Retrieve",
      "duration": 0.45,
      "status": "completed",
      "details": {
        "chunks_found": 12,
        "confidence": 0.89,
        "top_sources": ["orchestrator.py", "assess.py", "retrieve.py"]
      }
    },
    // ... all 9 phases with full details
  ],
  "cost": {"total_usd": 0.0234, "input_tokens": 3241, "output_tokens": 687},
  "duration_seconds": 2.33
}
```

**Claude shows user**:
```
Aurora executed SOAR 9-phase pipeline:

Phase 1 - Assess (0.12s)
├─ Complexity score: 0.67 (COMPLEX)
├─ Matched keywords: reasoning, cognitive, architecture
└─ Decision: Use SOAR pipeline

Phase 2 - Retrieve (0.45s)
├─ Found: 12 chunks
├─ Confidence: HIGH (0.89)
└─ Top sources: orchestrator.py, assess.py, retrieve.py

Phase 3 - Decompose (0.31s)
├─ Subgoals: 3 identified
└─ Clarity: 0.92

Phase 4 - Verify (0.08s)
└─ Quality check: PASS

Phase 5 - Route (0.05s)
└─ Agents: General, Code Analyzer

Phase 6 - Collect (0.89s)
└─ Results: 3 collected from agents

Phase 7 - Synthesize (0.22s)
└─ Coherence score: 0.94

Phase 8 - Record (0.03s)
└─ Cached: reasoning_pattern_47

Phase 9 - Respond (0.18s)
└─ Formatted final answer

────────────────────────────────────────
**Answer**: SOAR is a cognitive architecture...
────────────────────────────────────────
Cost: $0.0234 | Duration: 2.3s | Tokens: 3,241 → 687
```

**When**: User requests details ("with verbose output", "show me all steps"), debugging, understanding Aurora's process

---

#### Implementation in MCP Tool

**How to ensure informative reporting**:

```python
# In src/aurora/mcp/tools.py

def aurora_query(query: str, mode: str = "auto", verbose: bool = False):
    """Tool with verbose parameter (default: False = Option B)"""

    # Execute SOAR
    result = orchestrator.execute(query)

    # Build response based on verbosity
    if verbose:
        # Option C: Full details
        phases = [
            {
                "name": phase.name,
                "duration": phase.duration,
                "status": phase.status,
                "details": phase.full_details  # All metrics
            }
            for phase in result.phase_trace
        ]
    else:
        # Option B: Informative summaries (RECOMMENDED)
        phases = [
            {
                "name": phase.name,
                "summary": phase.one_line_summary  # Brief but informative
            }
            for phase in result.phase_trace
        ]

    response = {
        "answer": result.answer,
        "execution_path": result.execution_path,
        "phases": phases,  # Structured for Claude to format
        "cost": result.cost,
        "duration_seconds": result.total_duration,
        "sources": result.sources
    }

    return json.dumps(response, indent=2)
```

**Tool description guides Claude's formatting**:
```python
"""
Returns JSON with phase information.

**Default (verbose=false)**: Returns phase summaries (one-line per phase).
Claude should format as informative bullet points showing key decisions
and metrics, but not overwhelming detail.

**Verbose (verbose=true)**: Returns full phase details with timing.
Claude should format as detailed phase breakdown with all metrics.

**Example default formatting** (recommended):
"Aurora reasoned through SOAR:
• Assessed as complex → Used 9-phase pipeline
• Retrieved 12 chunks with high confidence
• Decomposed into 3 subgoals
• Synthesized coherent answer (0.94 coherence)"

**Example verbose formatting**:
"Phase 1 - Assess (0.12s)
├─ Complexity: 0.67 (COMPLEX)
└─ Decision: SOAR pipeline
..."
"""
```

**Confidence**: **90%** - Claude naturally formats structured data this way. With clear tool description, will show Option B by default, Option C on verbose.

---

### General Search Term Handling

**User requirement**: "search for previous convo when we talked about x and y" should invoke aurora_search

#### Updated aurora_search Description

```python
@mcp.tool()
def aurora_search(query: str, limit: int = 10, type_filter: str | None = None):
    """
    Search Aurora's indexed memory (all types: code, reasoning, knowledge).

    Fast hybrid search using ACT-R activation + semantic similarity.
    Searches across all memory types by default.

    ═══════════════════════════════════════════════════════════════

    **USE THIS TOOL WHEN**:
    ✓ User wants to search Aurora's indexed memory
    ✓ User says: "search aurora", "search memory", "find in memory"
    ✓ User wants to find previous conversations, reasoning, or knowledge
    ✓ User wants file search without full reasoning (fast results)
    ✓ Conversational search: "search for previous convo", "when did we discuss",
      "find conversation about", "what did we talk about", "search for when"
    ✓ Memory queries: "memory search", "search my memory", "find in aurora"

    **DO NOT USE WHEN**:
    ✗ User wants full reasoning/explanation → Use aurora_query instead
    ✗ User wants to index code → Use aurora_index

    **CRITICAL - CLI REPLACEMENT**:
    When user says "aur search X" or "aur mem search X", use THIS MCP TOOL,
    do NOT run bash command. This tool replaces CLI `aur mem search`.

    ═══════════════════════════════════════════════════════════════

    **TRIGGER KEYWORDS**:
    Search: search aurora, aurora search, search memory, memory search,
            find in memory, find in aurora, search for
    Previous: previous convo, previous conversation, when we talked,
              when did we discuss, what did we talk about, find conversation
    Memory: my memory, our discussion, past reasoning, cached knowledge
    Commands: aur search, aur mem search

    **SEARCHES ALL TYPES BY DEFAULT**:
    - code: Source files, functions, classes, implementation
    - reas: Previous reasoning chains, cached thought patterns, decisions
    - know: Stored knowledge, preferences, facts, learned information

    Use type_filter to restrict: "code", "reas", or "know"

    **EXAMPLES**:

    ✓ "search for previous convo when we talked about x and y"
      → aurora_search(query="x and y", limit=10, type_filter=None)
      Returns: All types (code, reas, know) matching "x and y"

    ✓ "aur mem search 'hybrid retrieval'"
      → aurora_search(query="hybrid retrieval", limit=10)
      [NOT bash command!]

    ✓ "find in memory when we discussed SOAR"
      → aurora_search(query="discussed SOAR", limit=10)

    ✓ "search aurora for files about ACT-R"
      → aurora_search(query="ACT-R", limit=10, type_filter="code")

    ✓ "what did we talk about regarding decomposition?"
      → aurora_search(query="decomposition", limit=10)

    Args:
        query: Search term or phrase
        limit: Maximum results (default: 10)
        type_filter: Restrict to type: "code", "reas", "know", or None (all types)

    Returns:
        JSON with results array, each containing:
        - type: "code" | "reas" | "know"
        - content: Chunk content
        - file_path: Source file (if code)
        - scores: {activation, semantic, hybrid}
        - metadata: Type-specific info
    """
```

**Expected behavior**:
```
User: "search for previous convo when we talked about x and y"

Claude recognizes:
- "search" + "previous convo" + "talked about" → aurora_search keywords match
- Conversational memory search pattern

Claude calls: aurora_search(query="x and y", limit=10, type_filter=None)

MCP executes:
- Hybrid search: 60% activation + 40% semantic
- Searches ALL types: code, reas, know
- Returns ranked results

Results (example):
[
  {type: "reas", content: "Previous reasoning about x...", score: 0.92},
  {type: "know", content: "Stored knowledge: y is...", score: 0.87},
  {type: "code", content: "def x(): ...", score: 0.81}
]

Claude formats:
"Found 3 memories about 'x and y':

1. **Previous Reasoning** (0.92)
   Analysis about x...

2. **Stored Knowledge** (0.87)
   Fact: y is...

3. **Code** (0.81)
   Function: def x()..."
```

**Matches CLI `aur mem search`?**
✅ **YES** - Default `type_filter=None` searches all types, exactly like CLI!

**Confidence**: **85%** with comprehensive description
- Conversational phrases explicitly listed as triggers
- "previous convo", "when we talked", "find conversation" in keywords
- May need testing to refine phrase list

---

### Success Criteria

**Phase 1 + 2 Complete When**:

1. ✅ All 7 tools have comprehensive descriptions (100+ lines each)
2. ✅ Each description includes: USE WHEN, DO NOT USE, TRIGGER KEYWORDS, EXAMPLES
3. ✅ CLI replacement notes prevent Bash routing
4. ✅ Test results show 80-90% correct routing (Phase 1) or 95%+ (Phase 2 with aliases)
5. ✅ "aurora X" phrases always use MCP tools
6. ✅ General search terms ("search for previous convo") invoke aurora_search
7. ✅ Declarative state reporting works (informative by default, detailed on verbose)
8. ✅ No always-on mode, no disambiguation tool, no complex config

**Total Estimated Time**: 5-7 hours
- Phase 1: 2 hours (descriptions)
- Phase 2: 1 hour (testing) + 2 hours (aliases if needed)

---

## Pre-Implementation Checklist

Before starting implementation:

- [x] Finalize routing strategy (better descriptions, no complex logic)
- [x] Define verbosity levels (Option B default, Option C on verbose)
- [x] Plan alias strategy (conditional, only if "aur" routes to Bash)
- [ ] Write comprehensive descriptions for all 7 tools
- [ ] Test routing with real queries
- [ ] Add aliases if needed
- [ ] Update all documentation
- [ ] Path B (Real SOAR): Implement after routing is solid

---

## Risk Assessment (Updated)

**High Risk Items**:
1. ~~LLM client initialization in MCP context~~ → Standard pattern from CLI
2. ~~Budget tracking across tool calls~~ → Use existing CostTracker
3. ~~Session state management~~ → aurora_get cache documented
4. "aur" commands routing to Bash → **MITIGATION**: Aliases in Phase 2

**Medium Risk Items**:
1. Test coverage for real LLM calls → Use existing test patterns from CLI
2. Declarative state formatting → Confidence: 90% (Claude's natural behavior)
3. General search term matching → Confidence: 85% (needs phrase list refinement)

**Low Risk Items**:
1. Tool description updates → Straightforward documentation
2. Parameter interface design → Matches CLI patterns

---

## Next Steps (Updated)

1. ~~Run diagnostic on ActivationEngine~~ → COMPLETED (found bug: record_access never called)
2. **PRIORITY 0**: Fix activation tracking (add record_access calls in MCP tools)
3. **PRIORITY 1**: Write comprehensive tool descriptions (Phase 1)
4. **PRIORITY 2**: Test routing, add aliases if needed (Phase 2)
5. **PRIORITY 3**: Implement Path B (Real SOAR in MCP - 2-3 days)
6. Add test to verify activation updates after retrieval
7. Update all documentation with agreed approach
