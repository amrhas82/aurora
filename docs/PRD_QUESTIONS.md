# PRD Discovery Questions - AURORA CLI Fixes & MCP Integration

**Please answer these questions to help create the PRD**

---

## 1. MCP Architecture & Embeddings Strategy

### Q1.1 - Embeddings Provider
For the MCP server's semantic search capability, which approach do you prefer?

- [ ] A) **Sentence-BERT (local)** - Free, offline, no API key, slightly lower quality
- [ ] B) **OpenAI embeddings API** - Higher quality, requires API key, costs money
- [ ] C) **Configurable** - Default to Sentence-BERT, allow users to upgrade via config
- [ ] D) **Other** - Specify preferred approach

**My recommendation: C**

---

### Q1.2 - MCP Library Choice
Which MCP implementation library should we use?

- [ ] A) **FastMCP** - Simpler, faster development, Python-native
- [ ] B) **Official MCP SDK** - More features, official support, TypeScript/Node
- [ ] C) **Build from scratch** - Maximum control, more effort
- [ ] D) **Unsure** - Need recommendation

**My recommendation: A**

---

### Q1.3 - MCP Server Lifecycle
How should the MCP server start/stop?

- [ ] A) **Auto-start by Claude Desktop** - User configures once, works automatically
- [ ] B) **Manual start** - User runs `aurora-mcp start` before using Claude
- [ ] C) **Both options** - Auto-start preferred, manual for debugging
- [ ] D) **Other** - Specify

**My recommendation: A**

---

## 2. Package Consolidation & Migration

### Q2.1 - Migration Path for Existing Users
Do you have existing users who installed the 6 separate packages?

- [ ] A) **Yes, need migration guide** - Provide clear upgrade path
- [ ] B) **No existing users** - Just publish new structure
- [ ] C) **Few users, can break** - Major version bump, no backward compatibility
- [ ] D) **Unsure** - Check if anyone is using it

**My recommendation: C**

---

### Q2.2 - Deprecated Package Wrappers
Should we keep the old 6 packages as deprecated wrappers pointing to new package?

- [ ] A) **Yes, keep for 6 months** - Gradual migration, less breaking
- [ ] B) **Yes, keep forever** - Maximum backward compatibility
- [ ] C) **No, clean break** - Remove old packages, force migration
- [ ] D) **Conditional** - Depends on Q2.1 answer

**My recommendation: C**

---

### Q2.3 - Import Path Changes
After consolidation, which import style do you prefer?

- [ ] A) **Flat imports** - `from aurora import SQLiteStore, HybridRetriever`
- [ ] B) **Namespaced imports** - `from aurora.core import SQLiteStore`
- [ ] C) **Both supported** - Flat for convenience, namespaced for clarity
- [ ] D) **Keep current style** - Minimal import changes

**My recommendation: B**

---

## 3. Installation Feedback & Verification

### Q3.1 - Installation Feedback Level
How much detail should `pip install aurora` show?

- [ ] A) **Minimal** - Just "✓ AURORA installed successfully"
- [ ] B) **Component-level** - Show each subsystem (Core, CLI, MCP, etc.)
- [ ] C) **Verbose** - Show all dependencies and versions
- [ ] D) **Configurable** - `pip install aurora` quiet, `pip install -v aurora` verbose

**My recommendation: B**

---

### Q3.2 - Post-Install Verification
What should `aur --verify` check? (Select numbers to include)

1. Core packages installed
2. CLI commands available
3. MCP server binary exists
4. Python version compatibility
5. ML dependencies (embeddings)
6. Database connectivity
7. Config file exists
8. Sample query execution

**My recommendation: 1,2,3,4,5,7 (skip 6,8)**

---

### Q3.3 - Failure Recovery
If `aur --verify` finds issues, should it offer auto-fix?

- [ ] A) **Yes, auto-fix** - "Run `aur --repair` to fix issues"
- [ ] B) **No, just report** - Show problems, user fixes manually
- [ ] C) **Prompt user** - Ask "Would you like to fix this? (y/n)"
- [ ] D) **Depends on issue** - Some auto-fix, some require manual

**My recommendation: B**

---

## 4. Testing Strategy & Coverage

### Q4.1 - Integration Test Scope
For TD-P2-003 (Memory integration tests), what should we test end-to-end? (Select numbers)

1. Index real Python files → Search → Retrieve correct results
2. Index → Delete → Verify cleanup
3. Index large codebase (1000+ files) → Performance metrics
4. Concurrent indexing (multiple processes)
5. Index → Export → Import → Verify integrity

**My recommendation: 1,2 (core functionality)**

---

### Q4.2 - MCP Testing Approach
How should we test the MCP server?

- [ ] A) **Unit tests only** - Mock MCP protocol, test tools in isolation
- [ ] B) **Integration with real Claude Desktop** - Requires manual testing
- [ ] C) **MCP test harness** - Automated MCP client that calls tools
- [ ] D) **Combination** - A + C for automation, B for final verification

**My recommendation: D**

---

### Q4.3 - Test-First vs. Fix-First
Should we write tests before or after implementing fixes?

- [ ] A) **Test-first** - Write failing test, then fix bug, then verify
- [ ] B) **Fix-first** - Bugs already fixed, now add tests to prevent regression
- [ ] C) **Parallel** - One person writes tests, another fixes bugs
- [ ] D) **Hybrid** - Test-first for new features, fix-first for verified bugs

**My recommendation: B (bugs already fixed)**

---

## 5. Phase Ordering & Parallelization

### Q5.1 - Critical Path
Which phase MUST happen first to unblock others?

- [ ] A) **Phase 1 (Bug Fixes)** - Stable foundation needed first
- [ ] B) **Phase 2 (Package Consolidation)** - Changes all imports, affects everything
- [ ] C) **Either** - Phases are independent, can parallelize
- [ ] D) **Unsure** - Need analysis

**My recommendation: B (consolidation changes all imports)**

---

### Q5.2 - Parallelization Opportunities
Can we work on multiple phases simultaneously?

- [ ] A) **Yes, full parallel** - Bugs in branch A, MCP in branch B, consolidation in branch C
- [ ] B) **Some parallel** - Bugs + consolidation sequential, MCP in parallel
- [ ] C) **No, sequential only** - Too much merge conflict risk
- [ ] D) **Conditional** - Depends on team size

**My recommendation: C (sequential to avoid conflicts)**

---

### Q5.3 - MCP Development Timing
When should we build the MCP server?

- [ ] A) **After package consolidation** - Ensures correct import paths
- [ ] B) **Before package consolidation** - Get MCP working first, then refactor
- [ ] C) **Parallel track** - Develop against current structure, update later
- [ ] D) **Doesn't matter** - MCP is self-contained

**My recommendation: A**

---

## 6. CLI Improvements & User Experience

### Q6.1 - Headless Flag Syntax
For Issue 4 (headless syntax confusion), which solution?

- [ ] A) **Add `--headless` global flag** - `aur --headless test.md` works
- [ ] B) **Keep subcommand only** - Document that it's `aur headless test.md`
- [ ] C) **Both work** - Accept both syntaxes for flexibility
- [ ] D) **Rename to `--batch`** - Clearer semantic meaning

**My recommendation: C**

---

### Q6.2 - Error Message Quality
Should we audit and improve ALL error messages in this sprint?

- [ ] A) **Yes, comprehensive audit** - Every error message reviewed
- [ ] B) **No, just fix what's broken** - Focus on bugs only
- [ ] C) **Quick pass** - Review common error paths, defer deep audit
- [ ] D) **Separate sprint** - Log issues, tackle in UX improvement sprint

**My recommendation: C**

---

### Q6.3 - Help Text & Examples
Should we add inline examples to help text?

- [ ] A) **Yes, add to all commands** - Much better UX
- [ ] B) **No, keep help concise** - Examples in docs only
- [ ] C) **Some commands** - Complex commands only (init, index, query)
- [ ] D) **Separate sprint** - Good idea but not blocking

**My recommendation: C**

---

## 7. Success Metrics & Demo Workflow

### Q7.1 - Definition of "Done"
What's the final acceptance test that proves everything works?

- [ ] A) **Smoke test suite passes** - Automated tests all green
- [ ] B) **User demo workflow** - Specific scenario works end-to-end
- [ ] C) **Both** - Tests pass AND demo works
- [ ] D) **User validates** - You personally try it and approve

**My recommendation: C**

---

### Q7.2 - Demo Workflow Priority
Rank these in priority order (1=highest):

___ Fresh install → Init → Index → Search → Get results
___ Fresh install → MCP setup → Claude Desktop integration → Query via chat
___ Upgrade from 6 packages → Single package → Verify no breakage
___ All of the above must work

**My recommendation: 2, 1, 4 (MCP #1 priority)**

---

### Q7.3 - Performance Benchmarks
Should we establish performance baselines?

- [ ] A) **Yes, measure** - Indexing speed, search latency, memory usage
- [ ] B) **No, functionality only** - Performance not a goal this sprint
- [ ] C) **Track but don't block** - Log metrics, don't fail on regressions
- [ ] D) **Specific targets** - e.g., "Index 1000 files in < 60 seconds"

**My recommendation: C**

---

## 8. Documentation & Examples

### Q8.1 - MCP Setup Documentation
What level of detail for MCP configuration guide?

- [ ] A) **Minimal** - Just the JSON config snippet
- [ ] B) **Standard** - Config + explanation of each field
- [ ] C) **Comprehensive** - Config + troubleshooting + examples
- [ ] D) **Video + docs** - Written guide plus walkthrough video

**My recommendation: C**

---

### Q8.2 - Example Use Cases
Which example workflows should we document? (Select numbers)

1. "Search my codebase for authentication logic"
2. "Find all usages of DatabaseConnection class"
3. "What does the UserService module do?"
4. "Show me error handling in payment processing"
5. "Analyze code quality in legacy modules"

**My recommendation: 1,2,3**

---

### Q8.3 - Troubleshooting Guide
Should we create a troubleshooting section?

- [ ] A) **Yes, comprehensive** - Common issues + solutions
- [ ] B) **Yes, minimal** - Just "If MCP doesn't work, check X"
- [ ] C) **No, rely on GitHub issues** - Users can ask questions
- [ ] D) **Auto-diagnostic** - `aur --diagnose` command does this

**My recommendation: B**

---

## 9. Risk Mitigation Details

### Q9.1 - Integration Test Confidence
Should we use real dependencies or mocks?

- [ ] A) **Real dependencies only** - No mocks, use actual SQLite, embeddings, etc.
- [ ] B) **Hybrid approach** - Real for critical paths, mocks for edge cases
- [ ] C) **Contract tests** - Define interfaces, test against contracts
- [ ] D) **All of the above** - Comprehensive test pyramid

**My recommendation: A (real dependencies caught our bugs)**

---

### Q9.2 - Rollback Plan
If package consolidation breaks things, what's the rollback strategy?

- [ ] A) **Keep old packages active** - Can revert to 6-package structure
- [ ] B) **Git revert** - Roll back to pre-consolidation commit
- [ ] C) **Version pinning** - Users can `pip install aurora==0.1.0` for old version
- [ ] D) **No rollback needed** - Test thoroughly, no failures expected

**My recommendation: C**

---

## 10. Scope Boundary Clarifications

### Q10.1 - Multi-LLM Support
MCP tools need embeddings. Should we:

- [ ] A) **Hardcode Sentence-BERT** - Only local embeddings, no LLM calls
- [ ] B) **Config file option** - User can specify embedding provider
- [ ] C) **Plugin architecture** - Extensible for future providers
- [ ] D) **Defer completely** - MCP v1 has no semantic search, just keyword search

**My recommendation: A (simple, works offline)**

---

### Q10.2 - Real-Time Indexing
Should the MCP server watch for file changes and auto-reindex?

- [ ] A) **Yes, include in Phase 3** - More useful for development
- [ ] B) **No, manual indexing only** - User runs `aur mem index` when needed
- [ ] C) **Phase 5 (future)** - Good idea but not blocking
- [ ] D) **Optional flag** - `aurora-mcp --watch` for users who want it

**My recommendation: C (defer to future)**

---

### Q10.3 - Cloud/Remote MCP
Should we design for future cloud deployment?

- [ ] A) **Yes, design for it** - Use abstractions that work local or remote
- [ ] B) **No, local-first** - Simplest solution, refactor later if needed
- [ ] C) **Hybrid** - Local default, optional remote mode
- [ ] D) **Never** - AURORA is always local, user data stays private

**My recommendation: B (local-first)**

---

## How to Answer

**Option 1**: Check the boxes for your choices and save this file

**Option 2**: Just say "use recommendations" and I'll answer with all my recommendations

**Option 3**: Answer specific questions like: "Q1.1: C, Q1.2: A, Q2.1: C, ..."

**Option 4**: Say "let's discuss" and we'll go through them together
