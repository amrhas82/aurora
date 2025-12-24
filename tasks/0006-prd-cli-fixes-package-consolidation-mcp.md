# PRD-0006: AURORA v0.2.0 - CLI Fixes, Package Consolidation & MCP Integration

**Date**: December 24, 2025
**Status**: Draft - Ready for Review
**Version**: 0.2.0
**Author**: Product Manager
**Sprint**: Single 5-day sprint

---

## 1. Introduction/Overview

### Problem Statement

AURORA v0.1.0 has three critical CLI bugs blocking basic usage, a confusing 6-package installation process, and no integration with AI coding assistants like Claude Code CLI. Users cannot successfully:

1. Initialize configuration (`aur init` crashes)
2. Index codebases (`aur mem index` fails with API mismatch)
3. Use dry-run mode (import errors)
4. Install AURORA without confusion about which packages to install
5. Use AURORA with Claude Desktop/Code CLI for codebase exploration

### High-Level Goal

Create a stable, production-ready AURORA v0.2.0 that:
- **Works reliably** - All critical bugs fixed with regression tests
- **Installs simply** - Single `pip install aurora` with clear feedback
- **Integrates seamlessly** - MCP server enables Claude Desktop integration
- **Scales maintainably** - Comprehensive testing prevents future regressions

### Success Vision

A developer can:
```bash
# Install in one command
pip install aurora

# Initialize and index their codebase
aur init
aur mem index ~/my-project

# Use with Claude Desktop
# Claude: "Search my codebase for authentication logic"
# AURORA MCP: [Returns relevant code chunks]
```

All without crashes, confusing errors, or API key requirements.

---

## 2. Goals & Success Criteria

### Primary Goals

1. **Stability** - Zero crashes on core workflows (init, index, search, query)
2. **Simplicity** - Single package installation with clear pass/fail feedback
3. **Integration** - MCP server works with Claude Desktop for codebase exploration
4. **Quality** - Integration tests prevent regression of bugs we found

### Success Criteria

**Must Have (Release Blockers)**:
- [ ] All 3 critical CLI bugs fixed and verified working
- [ ] Single `pip install aurora` installs all 6 packages successfully
- [ ] Installation shows component-level feedback (✓ Core, ✓ CLI, etc.)
- [ ] `aur --verify` command validates installation health
- [ ] MCP server implements 5 core tools (search, index, stats, context, related)
- [ ] MCP server works with Claude Desktop in both always-on and on-demand modes
- [ ] Integration tests cover: index→search→retrieve, index→delete→verify, index→export→import
- [ ] Headless mode tests added (TD-P2-002)
- [ ] Memory integration tests added (TD-P2-003)
- [ ] Comprehensive MCP setup documentation with troubleshooting

**Should Have (High Priority)**:
- [ ] `aur --headless` global flag syntax works (in addition to `aur headless`)
- [ ] Help text includes examples for init, index, query commands
- [ ] `aurora-uninstall` helper command for clean removal
- [ ] MCP server status commands (start, stop, status)
- [ ] Error messages reviewed and improved for common paths

**Nice to Have (Can Defer)**:
- [ ] Performance metrics logged (indexing time, search latency)
- [ ] Advanced MCP features (real-time indexing, subscriptions)
- [ ] Remaining P2 technical debt items

### Definition of "Done"

1. **Automated tests pass** - All unit, integration, and MCP test harness tests green
2. **Demo workflows work** - Both MCP integration (#1 priority) and standalone CLI (#2 priority)
3. **User validates** - Project owner personally tests and approves

---

## 3. User Stories

### Story 1: New User - Simple Installation
**As a** developer new to AURORA
**I want to** install AURORA with a single command
**So that** I can start using it without confusion about which packages to install

**Acceptance Criteria**:
- `pip install aurora` installs all components
- Installation shows component-level progress (✓ Core, ✓ CLI, ✓ MCP, etc.)
- Installation ends with clear success message and next steps
- `aur --verify` confirms all components installed correctly

---

### Story 2: Developer - Reliable CLI Usage
**As a** developer using AURORA standalone
**I want to** initialize, index, and search my codebase without crashes
**So that** I can explore my code using AURORA's cognitive architecture

**Acceptance Criteria**:
- `aur init` creates configuration without Path shadowing crash
- `aur mem index .` successfully indexes Python files without API mismatch errors
- `aur query "test" --dry-run` shows escalation plan without import errors
- `aur mem search "authentication"` returns relevant code chunks
- All commands have clear error messages if something goes wrong

---

### Story 3: AI-Assisted Developer - Claude Desktop Integration
**As a** developer using Claude Desktop
**I want to** chat with Claude about my codebase using AURORA's semantic search
**So that** I can explore code through natural language without leaving my IDE

**Acceptance Criteria**:
- Configure AURORA MCP server in Claude Desktop settings (one-time)
- Index codebase: `aur mem index ~/my-project`
- Chat in Claude Desktop: "Search my codebase for authentication logic"
- Claude calls `aurora_search` tool and returns relevant code chunks
- Works in always-on mode (every query uses AURORA) or on-demand mode (explicit invocation)
- No Anthropic API key required for MCP server operation

---

### Story 4: Developer - Flexible Headless Syntax
**As a** developer running AURORA in automated scripts
**I want to** use intuitive `--headless` flag syntax
**So that** I don't have to remember non-standard subcommand syntax

**Acceptance Criteria**:
- `aur --headless test.md` works (global flag syntax)
- `aur headless test.md` still works (subcommand syntax)
- Both produce identical output
- Help text clarifies both syntaxes are supported

---

### Story 5: Developer - Installation Troubleshooting
**As a** developer experiencing installation issues
**I want to** verify my AURORA installation health
**So that** I can diagnose and fix problems quickly

**Acceptance Criteria**:
- `aur --verify` checks: core packages, CLI, MCP, Python version, ML dependencies, config file
- Clear ✓/✗ indicators for each component
- If issues found, provides actionable guidance (e.g., "Run: pip install aurora[ml]")
- Returns exit code 0 for success, non-zero for failures

---

### Story 6: Developer - Clean Uninstallation
**As a** developer wanting to remove AURORA
**I want to** uninstall all AURORA packages cleanly
**So that** I don't have orphaned packages cluttering my environment

**Acceptance Criteria**:
- `aurora-uninstall` command removes all 6 packages plus meta-package
- Shows progress as each package is removed
- Confirms successful removal
- Option to keep configuration: `aurora-uninstall --keep-config`

---

## 4. Functional Requirements

### FR-1: CLI Bug Fixes

**FR-1.1: Fix `aur init` Path Shadowing Crash**
- **Requirement**: The system must not crash when running `aur init`
- **Implementation**: Remove duplicate `from pathlib import Path` inside function at line 88 of `packages/cli/src/aurora_cli/commands/init.py`
- **Verification**: Integration test creates fresh config directory and runs `aur init` successfully

**FR-1.2: Fix `aur mem index` API Mismatch**
- **Requirement**: The system must successfully save chunks during indexing using the correct API
- **Implementation**:
  - Change `chunk.embeddings = embedding.tobytes()`
  - Call `memory_store.save_chunk(chunk)` instead of non-existent `add_chunk()`
  - Rename method to `_save_chunk_with_retry()`
- **Location**: `packages/cli/src/aurora_cli/memory_manager.py:509-543`
- **Verification**: Integration test indexes real Python files and verifies chunks saved to SQLite

**FR-1.3: Fix Dry-Run Import Error**
- **Requirement**: The system must correctly import HybridRetriever for dry-run mode
- **Implementation**: Change module path from `aurora_core.store.hybrid_retriever` to `aurora_context_code.semantic.hybrid_retriever`
- **Location**: `packages/cli/src/aurora_cli/main.py:342, 445`
- **Verification**: Unit test calls `aur query "test" --dry-run` and validates no ImportError

**FR-1.4: Add Flexible Headless Syntax**
- **Requirement**: The system must accept both `aur --headless` (global flag) and `aur headless` (subcommand)
- **Implementation**: Add `--headless` as global flag that internally maps to headless command
- **Verification**: Integration test verifies both syntaxes produce identical output

---

### FR-2: Package Consolidation

**FR-2.1: Meta-Package Installation**
- **Requirement**: The system must provide a single `pip install aurora` command that installs all 6 packages
- **Implementation**: Create meta-package `aurora` with dependencies on:
  - `aurora-core`
  - `aurora-context-code`
  - `aurora-soar`
  - `aurora-reasoning`
  - `aurora-cli`
  - `aurora-testing`
- **Rationale**: Keep packages separate for modular updates, single install for simplicity

**FR-2.2: Installation Feedback**
- **Requirement**: The system must show component-level installation progress
- **Expected Output**:
```
Installing aurora v0.2.0...
→ Installing aurora-core... ✓
→ Installing aurora-context-code... ✓
→ Installing aurora-soar... ✓
→ Installing aurora-reasoning... ✓
→ Installing aurora-cli... ✓
→ Installing aurora-testing... ✓

✓ AURORA installed successfully!

Next steps:
  aur init              # Initialize configuration
  aur mem index .       # Index your codebase
  aur --help            # See all commands
```
- **Implementation**: Post-install hook in meta-package setup.py

**FR-2.3: Namespaced Imports**
- **Requirement**: The system must support clear, namespaced import paths
- **Import Style**: `from aurora.core import SQLiteStore`, `from aurora.context_code.semantic import HybridRetriever`
- **Implementation**: Update all imports across codebase to use `aurora.` prefix

**FR-2.4: Installation Verification Command**
- **Requirement**: The system must provide `aur --verify` command to check installation health
- **Checks**:
  1. Core packages installed
  2. CLI commands available
  3. MCP server binary exists
  4. Python version compatibility (3.10+)
  5. ML dependencies (sentence-transformers)
  6. Config file exists
- **Output Format**:
```
Checking AURORA installation...
✓ Core packages installed
✓ CLI available
✓ MCP server available
✓ Python version: 3.11 (OK)
✓ ML dependencies: sentence-transformers (OK)
✓ Config file: ~/.aurora/config.toml (OK)

✓ AURORA is ready to use!
```
- **Error Handling**: If missing dependencies:
```
Checking AURORA installation...
✓ Core packages installed
✓ CLI available
✗ ML dependencies missing (semantic search will not work)

  To enable semantic search:
  pip install aurora[ml]

⚠ AURORA partially installed - basic features available
```
- **Exit Code**: 0 for success, 1 for warnings, 2 for critical failures

**FR-2.5: Uninstallation Helper**
- **Requirement**: The system must provide `aurora-uninstall` command to remove all packages
- **Behavior**: Removes aurora-core, aurora-context-code, aurora-soar, aurora-reasoning, aurora-cli, aurora-testing, aurora (meta)
- **Options**: `--keep-config` to preserve ~/.aurora configuration
- **Output**:
```
Uninstalling AURORA...
→ Removing aurora-core... ✓
→ Removing aurora-context-code... ✓
→ Removing aurora-soar... ✓
→ Removing aurora-reasoning... ✓
→ Removing aurora-cli... ✓
→ Removing aurora-testing... ✓
→ Removing aurora (meta-package)... ✓

✓ AURORA uninstalled successfully!

Configuration preserved at: ~/.aurora/
To remove config: rm -rf ~/.aurora
```

---

### FR-3: MCP Server Integration

**FR-3.1: MCP Server Architecture**
- **Requirement**: The system must provide an MCP server that exposes AURORA tools to Claude Desktop
- **Library**: Use FastMCP (Python-native, simple)
- **Key Constraint**: NO LLM calls in MCP server - Claude Desktop handles all LLM interactions
- **Embeddings**: Use Sentence-BERT (local, offline, no API key required)

**FR-3.2: MCP Operating Modes**

**Mode 1 - Always-On**:
- **Requirement**: The system must support always-on mode where every Claude Desktop query uses AURORA
- **Configuration**:
```json
{
  "mcp": {
    "always_on": true
  }
}
```
- **Behavior**: MCP server auto-starts with Claude Desktop, all queries route through AURORA tools

**Mode 2 - On-Demand**:
- **Requirement**: The system must support on-demand mode where user explicitly invokes AURORA
- **Configuration**:
```json
{
  "mcp": {
    "always_on": false
  }
}
```
- **Behavior**: User runs `aur mem add this` or `aur query what is 2+2` manually, or mentions "aur" in Claude chat

**FR-3.3: MCP Server Control Commands**
- **Requirement**: The system must provide CLI commands to manage MCP server
- **Commands**:
  - `aurora-mcp start` - Switch to always-on mode
  - `aurora-mcp stop` - Switch to on-demand mode
  - `aurora-mcp status` - Show current mode and server health

**FR-3.4: MCP Tool - aurora_search**
- **Requirement**: The system must provide semantic code search via MCP tool
- **Function Signature**:
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
- **Implementation**: Use HybridRetriever with Sentence-BERT embeddings
- **Example Usage**: Claude calls `aurora_search("authentication logic")` and receives list of relevant code chunks

**FR-3.5: MCP Tool - aurora_index**
- **Requirement**: The system must provide file indexing via MCP tool
- **Function Signature**:
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
- **Implementation**: Call existing MemoryManager indexing logic
- **Example Usage**: Claude calls `aurora_index("/home/user/project")` to index a codebase

**FR-3.6: MCP Tool - aurora_stats**
- **Requirement**: The system must provide memory statistics via MCP tool
- **Function Signature**:
```python
@mcp_tool()
def aurora_stats() -> Dict:
    """Get memory store statistics.

    Returns:
        MemoryStats: total chunks, files, database size
    """
```
- **Implementation**: Query SQLiteStore for counts and sizes
- **Example Usage**: Claude calls `aurora_stats()` to see how much code is indexed

**FR-3.7: MCP Tool - aurora_context**
- **Requirement**: The system must provide code context retrieval via MCP tool
- **Function Signature**:
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
- **Implementation**: Load file from disk, optionally filter to specific function using AST parsing
- **Example Usage**: Claude calls `aurora_context("/app/auth.py", "login")` to see login function

**FR-3.8: MCP Tool - aurora_related**
- **Requirement**: The system must provide related code discovery via MCP tool
- **Function Signature**:
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
- **Implementation**: Use existing ACT-R spreading activation from aurora.core
- **Example Usage**: Claude calls `aurora_related("chunk_123")` to find related code

**FR-3.9: MCP Configuration**
- **Requirement**: The system must document Claude Desktop MCP configuration
- **Configuration File**: `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or equivalent
- **Example Configuration**:
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

---

### FR-4: Testing & Quality Assurance

**FR-4.1: Memory Integration Tests (TD-P2-003)**
- **Requirement**: The system must include integration tests that use real components (no mocks)
- **Test Cases**:
  1. **Index → Search → Retrieve**: Index real Python files, search for term, verify correct chunks returned
  2. **Index → Delete → Verify**: Index files, delete chunks, verify cleanup
  3. **Index → Export → Import → Verify**: Index files, export to JSON, import to new DB, verify integrity
- **Implementation**: Use real SQLiteStore, real Sentence-BERT embeddings, real file parsing
- **Rationale**: Mocked tests didn't catch API mismatches; integration tests will prevent similar bugs

**FR-4.2: Headless Mode Tests (TD-P2-002)**
- **Requirement**: The system must include tests for headless mode
- **Test Cases**:
  1. `aur headless test.md` executes without errors
  2. `aur --headless test.md` produces identical output
  3. Headless mode handles missing files gracefully
  4. Output format is consistent across runs
- **Implementation**: Unit tests in `tests/unit/cli/test_headless.py`

**FR-4.3: MCP Test Harness**
- **Requirement**: The system must include automated tests for MCP tools
- **Test Approach**: MCP test client that calls each tool and validates responses
- **Test Cases**:
  1. `aurora_search` returns valid JSON with required fields (file_path, content, score)
  2. `aurora_index` successfully indexes test files and returns stats
  3. `aurora_stats` returns valid counts
  4. `aurora_context` retrieves file content correctly
  5. `aurora_related` returns chunks with activation scores
- **Manual Verification**: Final test with real Claude Desktop to confirm end-to-end workflow

**FR-4.4: Smoke Test Suite**
- **Requirement**: The system must include a smoke test suite that runs after installation
- **Test Script**: `tests/smoke_tests.sh`
- **Test Cases**:
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
- **Pass/Fail Criteria**:
  - ✓ PASS: All commands execute without errors
  - ✗ FAIL: Any command crashes or shows error
  - ⚠ WARN: Command works but shows warnings

---

### FR-5: Documentation & User Experience

**FR-5.1: MCP Setup Guide**
- **Requirement**: The system must provide comprehensive MCP setup documentation
- **Location**: `docs/MCP_SETUP.md`
- **Contents**:
  1. **Introduction**: What MCP integration provides
  2. **Prerequisites**: Claude Desktop, Python 3.10+, indexed codebase
  3. **Installation**: `pip install aurora`, `aur mem index .`
  4. **Configuration**: Claude Desktop settings with example JSON
  5. **Usage Examples**: 4 example workflows (authentication search, class usage, module description, error handling)
  6. **Modes**: Always-on vs on-demand mode configuration
  7. **Troubleshooting**: Common issues and solutions
  8. **Advanced**: Custom database paths, performance tuning

**FR-5.2: Example Use Cases**
- **Requirement**: The system must document 4 example MCP workflows
- **Examples**:
  1. **"Search my codebase for authentication logic"**
     - User asks Claude
     - Claude calls `aurora_search("authentication logic")`
     - Returns relevant functions with file paths
  2. **"Find all usages of DatabaseConnection class"**
     - User asks Claude
     - Claude calls `aurora_search("DatabaseConnection class usage")`
     - Returns import statements, instantiations, method calls
  3. **"What does the UserService module do?"**
     - User asks Claude
     - Claude calls `aurora_context("src/user_service.py")`
     - Returns full file content with docstrings
  4. **"Show me error handling in payment processing"**
     - User asks Claude
     - Claude calls `aurora_search("payment error handling try except")`
     - Returns try/except blocks in payment code

**FR-5.3: Troubleshooting Guide**
- **Requirement**: The system must provide troubleshooting documentation for common issues
- **Common Issues**:
  1. **MCP server not starting**
     - Check: `aurora-mcp status`
     - Solution: Verify Python version, check logs at `~/.aurora/mcp.log`
  2. **Claude Desktop not finding tools**
     - Check: Configuration file syntax valid
     - Solution: Restart Claude Desktop, verify `aurora-mcp` in PATH
  3. **Indexing fails**
     - Check: File permissions, disk space
     - Solution: Run with verbose: `aur mem index . --verbose`
  4. **Search returns no results**
     - Check: Files actually indexed (`aur mem stats`)
     - Solution: Reindex with `aur mem index . --force`
  5. **Embeddings slow or failing**
     - Check: Sentence-BERT installed (`pip list | grep sentence-transformers`)
     - Solution: Install ML dependencies: `pip install aurora[ml]`

**FR-5.4: Help Text Examples**
- **Requirement**: The system must add inline examples to help text for init, index, query commands
- **Example for `aur mem index`**:
```bash
$ aur mem index --help
Usage: aur mem index [PATH] [OPTIONS]

Index files into AURORA memory store for semantic search.

Arguments:
  PATH    Directory path to index (default: current directory)

Options:
  --pattern TEXT    File pattern to match (default: *.py)
  --force           Force reindex even if files already indexed
  --verbose         Show detailed progress
  --help            Show this message and exit

Examples:
  aur mem index .                    # Index current directory
  aur mem index ~/projects/myapp    # Index specific project
  aur mem index . --pattern "*.py"  # Only Python files
  aur mem index . --force           # Force reindex all files
```

**FR-5.5: Updated README**
- **Requirement**: The system must update README.md with v0.2.0 installation and usage
- **Sections to Update**:
  1. **Installation**: Show single `pip install aurora` command
  2. **Quick Start**: Add MCP integration as primary workflow
  3. **Standalone Usage**: Show CLI commands for non-MCP usage
  4. **Configuration**: Link to MCP setup guide
  5. **Troubleshooting**: Link to comprehensive troubleshooting guide

**FR-5.6: Error Message Quality Review**
- **Requirement**: The system must review and improve error messages for common failure paths
- **Focus Areas**:
  1. Missing configuration file
  2. Database connection failures
  3. Embedding model download failures
  4. File parsing errors
  5. Invalid command syntax
- **Improvement Pattern**:
  - Before: `Error: Database error`
  - After: `Error: Cannot open database at ~/.aurora/aurora.db. Run 'aur init' to create configuration.`
- **Implementation**: Quick pass this sprint, comprehensive audit tracked as TD-P2-009

---

## 5. Non-Goals (Out of Scope)

### Explicitly NOT Included in v0.2.0

1. **Multi-LLM Provider Support**
   - No GLM, Synthetic, Fireworks integration in MCP server
   - Rationale: MCP server is tools-only, no LLM calls needed
   - Future: v0.3.0 may add configurable embedding providers

2. **SOAR Pipeline in MCP Mode**
   - MCP provides tools only, not full reasoning pipeline
   - Rationale: Claude Desktop handles reasoning
   - Future: Could expose SOAR phases as separate tools

3. **Advanced MCP Features**
   - No subscriptions (real-time updates when files change)
   - No server-sent events
   - Rationale: MCP v1 focuses on core tool calling
   - Future: Track as TD-P2-010 (real-time file watching)

4. **Remaining P2 Technical Debt**
   - Only tackling TD-P2-002 (headless tests) and TD-P2-003 (memory integration tests)
   - Deferring: TD-P2-001, TD-P2-004, TD-P2-005, TD-P2-006, TD-P2-007, TD-P2-008
   - Rationale: Focus on stability first
   - Future: Next sprint after v0.2.0 release

5. **GUI or Web Interface**
   - CLI and MCP integration only
   - Rationale: Out of project scope
   - Future: Not planned

6. **Cloud Hosting for MCP Server**
   - Local-only deployment
   - Rationale: User data privacy, simplicity
   - Future: Could refactor if cloud deployment needed

7. **Performance Optimization**
   - Tracking metrics but not optimizing this sprint
   - Rationale: Functionality first, performance later
   - Future: Optimization sprint after v0.2.0

8. **Backward Compatibility**
   - v0.2.0 is a breaking change from v0.1.0
   - Rationale: Early stage project, clean slate acceptable
   - Migration: Version pinning available (`pip install aurora==0.1.0`)

---

## 6. Technical Considerations

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     AURORA v0.2.0                           │
│                                                             │
│  ┌──────────────────┐          ┌──────────────────┐       │
│  │  Meta-Package    │          │   MCP Server     │       │
│  │   (aurora)       │          │  (FastMCP)       │       │
│  └────────┬─────────┘          └────────┬─────────┘       │
│           │                              │                  │
│           │ Installs                     │ Exposes Tools    │
│           ▼                              ▼                  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              6 Core Packages                        │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐           │  │
│  │  │ aurora-  │ │ aurora-  │ │ aurora-  │           │  │
│  │  │  core    │ │ context- │ │  soar    │           │  │
│  │  │          │ │  code    │ │          │           │  │
│  │  └──────────┘ └──────────┘ └──────────┘           │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐           │  │
│  │  │ aurora-  │ │ aurora-  │ │ aurora-  │           │  │
│  │  │reasoning │ │   cli    │ │ testing  │           │  │
│  │  └──────────┘ └──────────┘ └──────────┘           │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘

External Integrations:
┌─────────────────────┐          ┌─────────────────────┐
│  Claude Desktop     │          │  Sentence-BERT      │
│  (User's AI IDE)    │◄─────────┤  (Local Embeddings) │
└─────────────────────┘   MCP    └─────────────────────┘
                        Protocol
```

### Package Structure

**Before v0.2.0 (6 Packages)**:
```
pip install aurora-core
pip install aurora-context-code
pip install aurora-soar
pip install aurora-reasoning
pip install aurora-cli
pip install aurora-testing
```

**After v0.2.0 (Meta-Package)**:
```
pip install aurora
# Automatically installs all 6 packages underneath
```

**Directory Structure**:
```
aurora/
├── pyproject.toml              # Meta-package (depends on 6 packages)
├── README.md
├── docs/
│   ├── MCP_SETUP.md            # NEW: Comprehensive MCP guide
│   └── TROUBLESHOOTING.md      # NEW: Issue resolution
├── packages/
│   ├── core/                   # aurora-core package
│   ├── context_code/           # aurora-context-code package
│   ├── soar/                   # aurora-soar package
│   ├── reasoning/              # aurora-reasoning package
│   ├── cli/                    # aurora-cli package
│   └── testing/                # aurora-testing package
├── src/aurora/
│   └── mcp/                    # NEW: MCP server
│       ├── server.py           # FastMCP server implementation
│       ├── tools.py            # MCP tool implementations
│       └── config.py           # MCP configuration handling
└── tests/
    ├── integration/
    │   ├── test_memory_e2e.py  # NEW: Integration tests (TD-P2-003)
    │   └── test_mcp_harness.py # NEW: MCP automated tests
    ├── unit/
    │   └── cli/
    │       └── test_headless.py # NEW: Headless tests (TD-P2-002)
    └── smoke_tests.sh          # NEW: Post-install smoke tests
```

### Import Path Migration

**Before v0.2.0**:
```python
from aurora_core.store import SQLiteStore
from aurora_context_code.semantic.hybrid_retriever import HybridRetriever
from aurora_cli.main import main
```

**After v0.2.0**:
```python
from aurora.core.store import SQLiteStore
from aurora.context_code.semantic.hybrid_retriever import HybridRetriever
from aurora.cli.main import main
```

### Dependencies

**Core Dependencies** (all packages):
- Python >= 3.10
- SQLite3 (built-in)
- Click (CLI framework)
- TOML (configuration)

**ML Dependencies** (optional extras):
- sentence-transformers (local embeddings)
- numpy (vector operations)
- scikit-learn (similarity calculations)

**MCP Dependencies**:
- FastMCP (MCP server framework)
- pydantic (data validation)

**Installation Options**:
```bash
pip install aurora              # Core only
pip install aurora[ml]          # Include embeddings
pip install aurora[dev]         # Include testing tools
pip install aurora[all]         # Everything
```

### Configuration

**Config File Location**: `~/.aurora/config.toml`

**Example Configuration**:
```toml
[core]
db_path = "~/.aurora/aurora.db"

[embeddings]
model = "sentence-transformers/all-MiniLM-L6-v2"
cache_dir = "~/.aurora/models"

[mcp]
always_on = false  # Set to true for always-on mode
log_file = "~/.aurora/mcp.log"
```

### Integration Points

1. **Claude Desktop** ↔ **AURORA MCP Server**
   - Protocol: MCP (Model Context Protocol)
   - Transport: stdio (standard input/output)
   - Data Format: JSON-RPC

2. **MCP Server** ↔ **AURORA CLI**
   - Shared: SQLiteStore database
   - Shared: Configuration file
   - No direct API coupling

3. **CLI** ↔ **Core Packages**
   - Direct Python imports
   - Function calls to indexing, search, reasoning

### Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| MCP Server | FastMCP (Python) | Simple, Python-native, fast development |
| Embeddings | Sentence-BERT | Local, offline, no API key, free |
| Database | SQLite | Embedded, no setup, file-based |
| CLI | Click | Rich features, easy testing |
| Testing | pytest | Standard Python testing |
| Packaging | setuptools + pyproject.toml | Modern Python packaging |

### Security Considerations

1. **No API Keys in MCP Server**
   - MCP server uses local embeddings only
   - Claude Desktop handles all LLM calls
   - User's API keys never touch AURORA code

2. **Local Data Only**
   - All code indexed stays on user's machine
   - SQLite database in user's home directory
   - No cloud uploads, no telemetry

3. **File System Access**
   - MCP tools can read files specified by user
   - No automatic file writing
   - User controls what gets indexed

### Performance Considerations

**Indexing Performance**:
- Target: 100 files/minute for Python code
- Bottleneck: Embedding generation (CPU-bound)
- Mitigation: Batch processing, caching

**Search Performance**:
- Target: < 200ms for semantic search
- Bottleneck: Vector similarity calculation
- Mitigation: SQLite indexes, limit result count

**MCP Latency**:
- Target: < 500ms end-to-end for `aurora_search`
- Components: MCP protocol overhead + search time
- Monitoring: Log timestamps for performance tracking

---

## 7. Implementation Plan

### Phase Overview

| Phase | Focus | Duration | Deliverables |
|-------|-------|----------|--------------|
| Phase 2 | Package Consolidation | 1 day | Meta-package, updated imports |
| Phase 1 | CLI Bug Fixes | 1 day | 3 bugs fixed, verified |
| Phase 3 | MCP Server | 2 days | MCP server, 5 tools, Claude Desktop integration |
| Phase 4 | Testing & Documentation | 1 day | Integration tests, MCP guide, README |

**Total: 5 days (1 sprint)**

**Note**: Phase 2 runs before Phase 1 because package consolidation changes all imports, affecting bug fix locations.

---

### Phase 2: Package Consolidation (Day 1)

**Goal**: Create meta-package structure and update all imports

**Tasks**:

1. **Create Meta-Package** (2 hours)
   - Create `aurora/pyproject.toml` with dependencies on 6 packages
   - Add post-install hook to show component-level feedback
   - Test: `pip install -e .` installs all 6 packages
   - Verify: Installation shows "✓ Core, ✓ CLI, ✓ MCP" messages

2. **Update Import Paths** (4 hours)
   - Search: `grep -r "from aurora_core" packages/`
   - Replace: `aurora_core.` → `aurora.core.`
   - Replace: `aurora_context_code.` → `aurora.context_code.`
   - Replace: `aurora_soar.` → `aurora.soar.`
   - Replace: `aurora_reasoning.` → `aurora.reasoning.`
   - Replace: `aurora_cli.` → `aurora.cli.`
   - Test: `python -m pytest tests/unit` passes

3. **Add Verification Command** (2 hours)
   - Implement `aur --verify` in `aurora/cli/main.py`
   - Check: packages, CLI, MCP, Python version, ML deps, config
   - Output: Clear ✓/✗ indicators
   - Test: Run `aur --verify` on fresh install

**Acceptance Criteria**:
- [ ] `pip install aurora` installs all 6 packages
- [ ] Installation shows component-level feedback
- [ ] All imports use `aurora.` prefix
- [ ] `aur --verify` validates installation health
- [ ] All existing unit tests pass

---

### Phase 1: CLI Bug Fixes (Day 2)

**Goal**: Fix 3 critical bugs and add headless syntax flexibility

**Tasks**:

1. **Fix Bug 1 - aur init Path Shadowing** (1 hour)
   - Location: `aurora/cli/commands/init.py:88`
   - Change: Remove duplicate `from pathlib import Path` inside function
   - Test: Add integration test in `tests/integration/test_cli_init.py`
   - Verify: `aur init` creates config without crash

2. **Fix Bug 2 - aur mem index API Mismatch** (2 hours)
   - Location: `aurora/cli/memory_manager.py:509-543`
   - Change: Use `chunk.embeddings = embedding.tobytes()` and `memory_store.save_chunk(chunk)`
   - Rename: `_save_chunk_with_retry()`
   - Test: Add integration test in `tests/integration/test_memory_e2e.py`
   - Verify: Index real files, check SQLite for saved chunks

3. **Fix Bug 3 - Dry-Run Import Error** (1 hour)
   - Location: `aurora/cli/main.py:342, 445`
   - Change: Import from `aurora.context_code.semantic.hybrid_retriever`
   - Test: Add unit test in `tests/unit/cli/test_query.py`
   - Verify: `aur query "test" --dry-run` shows escalation without error

4. **Add Headless Flag Flexibility** (1 hour)
   - Location: `aurora/cli/main.py`
   - Change: Add `--headless` global flag that maps to `headless` subcommand
   - Test: Add tests in `tests/unit/cli/test_headless.py`
   - Verify: Both `aur --headless test.md` and `aur headless test.md` work

5. **Error Message Quick Pass** (1 hour)
   - Review: Common error paths (missing config, DB errors, invalid syntax)
   - Improve: Add actionable guidance to error messages
   - Track: Comprehensive audit as TD-P2-009 for next sprint

6. **Help Text Examples** (1 hour)
   - Add: Examples to `aur init`, `aur mem index`, `aur query` help text
   - Format: Show common usage patterns
   - Test: Manual review of `aur --help`, `aur mem index --help`

7. **Smoke Test Suite** (1 hour)
   - Create: `tests/smoke_tests.sh`
   - Tests: init, index, search, stats, dry-run, MCP test
   - Run: After each fix to verify no regressions
   - CI: Add to GitHub Actions workflow

**Acceptance Criteria**:
- [ ] `aur init` works without Path shadowing crash
- [ ] `aur mem index .` indexes files and saves chunks correctly
- [ ] `aur query "test" --dry-run` shows escalation without import error
- [ ] Both `aur --headless` and `aur headless` syntaxes work
- [ ] Smoke tests pass
- [ ] Error messages provide actionable guidance

---

### Phase 3: MCP Server (Days 3-4)

**Goal**: Implement MCP server with 5 tools and Claude Desktop integration

**Tasks**:

**Day 3 - MCP Server Scaffold & Core Tools**

1. **Setup FastMCP Server** (2 hours)
   - Install: `pip install fastmcp`
   - Create: `aurora/mcp/server.py` with basic MCP server
   - Test: `aurora-mcp --test` starts server and shows available tools
   - Document: Command-line arguments (`--db-path`, `--config`)

2. **Implement aurora_search Tool** (2 hours)
   - Function: Search indexed code using HybridRetriever
   - Input: query (str), limit (int)
   - Output: List[Dict] with file_path, content, score
   - Test: MCP test harness calls tool and validates response

3. **Implement aurora_index Tool** (1 hour)
   - Function: Index files into memory store
   - Input: path (str), pattern (str)
   - Output: Dict with files indexed, chunks created, duration
   - Test: Index test directory, verify chunks in SQLite

4. **Implement aurora_stats Tool** (1 hour)
   - Function: Get memory store statistics
   - Input: None
   - Output: Dict with total chunks, files, database size
   - Test: Verify counts match SQLite queries

5. **Implement aurora_context Tool** (2 hours)
   - Function: Retrieve code context for file/function
   - Input: file_path (str), function (str, optional)
   - Output: Code content as string
   - Test: Retrieve file, retrieve specific function using AST parsing

**Day 4 - Advanced Tool & Integration**

6. **Implement aurora_related Tool** (2 hours)
   - Function: Find related chunks using ACT-R spreading activation
   - Input: chunk_id (str), max_hops (int)
   - Output: List[Dict] with related chunks and activation scores
   - Test: Index files with imports, verify spreading activation works

7. **Add MCP Control Commands** (2 hours)
   - Commands: `aurora-mcp start`, `aurora-mcp stop`, `aurora-mcp status`
   - Implementation: Manage always_on flag in config file
   - Test: Toggle modes and verify config updates

8. **Add Configuration Modes** (1 hour)
   - Add: `mcp.always_on` to config.toml
   - Default: `always_on = false` (on-demand mode)
   - Behavior: Always-on routes all queries, on-demand requires explicit invocation

9. **Claude Desktop Integration Test** (2 hours)
   - Setup: Configure MCP in Claude Desktop settings
   - Index: Sample codebase with `aur mem index`
   - Test: Chat with Claude, verify tools are called
   - Workflows: Test all 4 example use cases
   - Debug: Check logs if tools not found

10. **Performance Logging** (1 hour)
    - Add: Timestamp logging for each MCP tool call
    - Metrics: Search latency, indexing duration
    - Output: Log to `~/.aurora/mcp.log`
    - Track: Don't fail on regressions (informational only)

**Acceptance Criteria**:
- [ ] MCP server starts with `aurora-mcp`
- [ ] All 5 tools implemented and tested
- [ ] MCP test harness validates tool responses
- [ ] Claude Desktop successfully calls AURORA tools
- [ ] Both always-on and on-demand modes work
- [ ] Performance metrics logged

---

### Phase 4: Testing & Documentation (Day 5)

**Goal**: Add comprehensive tests and documentation

**Tasks**:

**Morning - Integration Testing**

1. **Memory Integration Tests - TD-P2-003** (2 hours)
   - File: `tests/integration/test_memory_e2e.py`
   - Test 1: Index real Python files → Search → Retrieve correct results
   - Test 2: Index → Delete chunks → Verify cleanup
   - Test 3: Index → Export to JSON → Import to new DB → Verify integrity
   - Implementation: Use real SQLiteStore, real Sentence-BERT, real parsing
   - Run: `pytest tests/integration/test_memory_e2e.py`

2. **Headless Mode Tests - TD-P2-002** (1 hour)
   - File: `tests/unit/cli/test_headless.py`
   - Test 1: `aur headless test.md` executes
   - Test 2: `aur --headless test.md` produces identical output
   - Test 3: Headless handles missing files gracefully
   - Run: `pytest tests/unit/cli/test_headless.py`

3. **MCP Test Harness** (1 hour)
   - File: `tests/integration/test_mcp_harness.py`
   - Tests: Each MCP tool called with valid/invalid inputs
   - Validation: Response format, error handling
   - Run: `pytest tests/integration/test_mcp_harness.py`

**Afternoon - Documentation**

4. **MCP Setup Guide** (2 hours)
   - File: `docs/MCP_SETUP.md`
   - Sections:
     - Introduction (what MCP provides)
     - Prerequisites (Claude Desktop, Python 3.10+)
     - Installation (`pip install aurora`, `aur mem index`)
     - Configuration (Claude Desktop settings JSON)
     - Usage Examples (4 workflows documented)
     - Modes (always-on vs on-demand)
     - Troubleshooting (5 common issues)
     - Advanced (custom paths, performance)

5. **Troubleshooting Guide** (1 hour)
   - File: `docs/TROUBLESHOOTING.md`
   - Issues:
     - MCP server not starting → Check logs, Python version
     - Claude Desktop not finding tools → Restart, verify PATH
     - Indexing fails → Permissions, disk space
     - Search returns no results → Verify indexed (`aur mem stats`)
     - Embeddings slow → Install ML deps

6. **Update README.md** (1 hour)
   - Sections:
     - Installation: Single `pip install aurora` command
     - Quick Start: MCP integration as primary workflow
     - Standalone Usage: CLI commands
     - Configuration: Link to MCP setup guide
     - Troubleshooting: Link to guide

7. **Uninstall Helper** (30 minutes)
   - Implement: `aurora-uninstall` command
   - Behavior: Remove all 6 packages + meta-package
   - Option: `--keep-config` to preserve ~/.aurora
   - Test: Uninstall, verify packages removed

8. **Final Verification** (30 minutes)
   - Run: Full smoke test suite
   - Run: All integration tests
   - Manual: Claude Desktop demo workflow
   - Checklist: Verify all acceptance criteria met

**Acceptance Criteria**:
- [ ] Memory integration tests pass (TD-P2-003)
- [ ] Headless mode tests pass (TD-P2-002)
- [ ] MCP test harness validates all tools
- [ ] MCP_SETUP.md is comprehensive and clear
- [ ] TROUBLESHOOTING.md covers 5+ common issues
- [ ] README.md updated for v0.2.0
- [ ] `aurora-uninstall` command works
- [ ] All smoke tests pass
- [ ] Manual Claude Desktop demo succeeds

---

### Risk Mitigation During Implementation

**Risk 1: Package consolidation breaks existing functionality**
- Mitigation: Run full test suite after every import path change
- Mitigation: Use automated find/replace with verification
- Rollback: Git branch for easy revert

**Risk 2: MCP integration more complex than expected**
- Mitigation: Start with minimal viable tools (search only)
- Mitigation: Use FastMCP library examples as templates
- Fallback: Reduce scope to 3 tools if 5 is too ambitious

**Risk 3: Integration tests still miss bugs**
- Mitigation: Use real components, no mocks
- Mitigation: Test with actual file system, SQLite, embeddings
- Validation: Manual smoke tests after automated tests

**Risk 4: Sentence-BERT embeddings not good enough**
- Mitigation: Document model choice, make configurable in future
- Fallback: If quality issues, add config option for OpenAI embeddings in v0.2.1
- Acceptance: User understands tradeoff (free/offline vs quality)

---

## 8. Testing Plan

### Test Pyramid

```
                    ┌─────────────┐
                    │   Manual    │  Claude Desktop integration
                    │  Testing    │  (Final validation)
                    └─────────────┘
                  ┌───────────────────┐
                  │   Integration     │  Memory E2E, MCP harness
                  │     Tests         │  (Real components)
                  └───────────────────┘
            ┌─────────────────────────────┐
            │        Unit Tests           │  CLI commands, tools
            │   (Existing + new)          │  (Fast, isolated)
            └─────────────────────────────┘
```

### Unit Tests

**Existing Tests** (must continue passing):
- `tests/unit/core/` - Store, chunks, activation
- `tests/unit/context_code/` - Parsing, embeddings
- `tests/unit/soar/` - Orchestrator, phases
- `tests/unit/reasoning/` - LLM client
- `tests/unit/cli/` - CLI commands

**New Unit Tests**:
1. **test_headless.py** (TD-P2-002)
   - Test both `aur headless` and `aur --headless` syntaxes
   - Test error handling for missing files
   - Test output format consistency

2. **test_query.py** (Bug 3 verification)
   - Test `aur query --dry-run` doesn't raise ImportError
   - Test dry-run shows escalation plan

3. **test_init.py** (Bug 1 verification)
   - Test `aur init` creates config without crash
   - Test init handles existing config gracefully

4. **test_verify.py** (New command)
   - Test `aur --verify` checks all components
   - Test verify shows clear ✓/✗ indicators
   - Test verify provides actionable guidance

### Integration Tests

**New Integration Tests**:

1. **test_memory_e2e.py** (TD-P2-003)
   ```python
   def test_index_search_retrieve():
       """Index real Python files, search, verify correct results."""
       # Setup: Create temp directory with Python files
       # Index: Run memory_manager.index_directory()
       # Search: Run hybrid_retriever.search("function")
       # Verify: Correct chunks returned with scores

   def test_index_delete_cleanup():
       """Index files, delete chunks, verify cleanup."""
       # Index: Add chunks to SQLite
       # Delete: Remove chunks
       # Verify: Database cleaned up, no orphaned data

   def test_index_export_import_integrity():
       """Index, export to JSON, import to new DB, verify."""
       # Index: Original database
       # Export: Dump to JSON
       # Import: Load into new database
       # Verify: Chunk counts match, content identical
   ```

2. **test_mcp_harness.py** (MCP validation)
   ```python
   def test_mcp_search_tool():
       """MCP aurora_search returns valid JSON."""
       # Setup: Start MCP test client
       # Call: aurora_search("authentication")
       # Verify: Response has file_path, content, score

   def test_mcp_index_tool():
       """MCP aurora_index successfully indexes."""
       # Call: aurora_index("/tmp/test_code")
       # Verify: Returns stats (files indexed, chunks created)

   def test_mcp_stats_tool():
       """MCP aurora_stats returns valid counts."""
       # Call: aurora_stats()
       # Verify: Returns chunk count, file count, size

   def test_mcp_context_tool():
       """MCP aurora_context retrieves file content."""
       # Call: aurora_context("/tmp/test.py", "my_function")
       # Verify: Returns function source code

   def test_mcp_related_tool():
       """MCP aurora_related finds related chunks."""
       # Setup: Index files with imports
       # Call: aurora_related("chunk_123")
       # Verify: Returns related chunks with activation scores
   ```

### Smoke Tests

**Script**: `tests/smoke_tests.sh`

```bash
#!/bin/bash
# AURORA v0.2.0 Smoke Test Suite

echo "Running AURORA smoke tests..."

# Test 1: aur init
echo "Test 1: aur init"
rm -rf ~/.aurora
aur init
if [ $? -eq 0 ]; then
    echo "✓ PASS: aur init"
else
    echo "✗ FAIL: aur init"
    exit 1
fi

# Test 2: aur mem index
echo "Test 2: aur mem index"
aur mem index packages/
if [ $? -eq 0 ]; then
    echo "✓ PASS: aur mem index"
else
    echo "✗ FAIL: aur mem index"
    exit 1
fi

# Test 3: aur mem search
echo "Test 3: aur mem search"
aur mem search "SQLiteStore"
if [ $? -eq 0 ]; then
    echo "✓ PASS: aur mem search"
else
    echo "✗ FAIL: aur mem search"
    exit 1
fi

# Test 4: aur mem stats
echo "Test 4: aur mem stats"
aur mem stats
if [ $? -eq 0 ]; then
    echo "✓ PASS: aur mem stats"
else
    echo "✗ FAIL: aur mem stats"
    exit 1
fi

# Test 5: aur query --dry-run
echo "Test 5: aur query --dry-run"
aur query "test" --dry-run
if [ $? -eq 0 ]; then
    echo "✓ PASS: aur query --dry-run"
else
    echo "✗ FAIL: aur query --dry-run"
    exit 1
fi

# Test 6: aurora-mcp --test
echo "Test 6: aurora-mcp --test"
aurora-mcp --test
if [ $? -eq 0 ]; then
    echo "✓ PASS: aurora-mcp --test"
else
    echo "✗ FAIL: aurora-mcp --test"
    exit 1
fi

# Test 7: aur --verify
echo "Test 7: aur --verify"
aur --verify
if [ $? -eq 0 ]; then
    echo "✓ PASS: aur --verify"
else
    echo "✗ FAIL: aur --verify"
    exit 1
fi

echo ""
echo "✓ All smoke tests passed!"
```

### Manual Testing

**Final Validation Checklist**:

1. **Fresh Installation**
   - [ ] Clean Python environment (virtualenv)
   - [ ] `pip install aurora` succeeds
   - [ ] Installation shows component feedback
   - [ ] `aur --verify` shows all green

2. **Standalone CLI Workflow**
   - [ ] `aur init` creates config
   - [ ] `aur mem index .` indexes codebase
   - [ ] `aur mem search "term"` returns results
   - [ ] `aur query "question"` generates response

3. **MCP Integration Workflow**
   - [ ] Configure Claude Desktop settings
   - [ ] Restart Claude Desktop
   - [ ] Chat: "Search my codebase for authentication"
   - [ ] Verify: Claude calls aurora_search and returns results
   - [ ] Chat: "Show me the UserService module"
   - [ ] Verify: Claude calls aurora_context and returns code

4. **Error Scenarios**
   - [ ] `aur mem index /nonexistent` shows clear error
   - [ ] `aur mem search` without indexing shows helpful message
   - [ ] MCP server fails gracefully if database missing

5. **Documentation Verification**
   - [ ] Follow MCP_SETUP.md step-by-step
   - [ ] Verify all examples work
   - [ ] Check troubleshooting guide resolves issues

### Test Coverage Goals

| Component | Unit Test Coverage | Integration Test Coverage |
|-----------|-------------------|---------------------------|
| CLI Commands | 80%+ | 100% (smoke tests) |
| MCP Tools | 90%+ | 100% (test harness) |
| Memory Management | 70%+ | 100% (E2E tests) |
| Core Store | 80%+ | Covered by memory tests |

**Rationale**:
- Integration tests more important than unit test coverage
- Real components catch API mismatches that mocks miss
- Focus on critical paths first, edge cases later

---

## 9. Documentation Plan

### Documentation Deliverables

| Document | Purpose | Audience | Priority |
|----------|---------|----------|----------|
| MCP_SETUP.md | MCP configuration guide | Developers using Claude Desktop | P0 (Must Have) |
| TROUBLESHOOTING.md | Issue resolution | All users | P0 (Must Have) |
| README.md (updated) | Quick start guide | New users | P0 (Must Have) |
| CHANGELOG.md | Version history | All users | P1 (Should Have) |
| API_REFERENCE.md | MCP tool API docs | Advanced users | P2 (Nice to Have) |

### MCP_SETUP.md Structure

```markdown
# AURORA MCP Server Setup Guide

## Introduction
- What MCP integration provides
- Benefits over standalone CLI
- Prerequisites

## Installation
1. Install AURORA: `pip install aurora`
2. Initialize: `aur init`
3. Index codebase: `aur mem index ~/my-project`

## Claude Desktop Configuration
1. Locate config file
2. Add AURORA MCP server:
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
3. Restart Claude Desktop

## Operating Modes
### Always-On Mode
- Config: `mcp.always_on = true`
- Behavior: Every query uses AURORA
- Use case: Deep codebase exploration

### On-Demand Mode
- Config: `mcp.always_on = false`
- Behavior: Explicit invocation only
- Use case: Selective usage

## Usage Examples

### Example 1: Search for Authentication Logic
**User**: "Search my codebase for authentication logic"
**Claude**: [Calls aurora_search("authentication logic")]
**Result**: Returns 5 relevant functions with file paths

### Example 2: Find Class Usages
**User**: "Find all usages of DatabaseConnection class"
**Claude**: [Calls aurora_search("DatabaseConnection class usage")]
**Result**: Import statements, instantiations, method calls

### Example 3: Understand a Module
**User**: "What does the UserService module do?"
**Claude**: [Calls aurora_context("src/user_service.py")]
**Result**: Full file with docstrings and code

### Example 4: Error Handling Analysis
**User**: "Show me error handling in payment processing"
**Claude**: [Calls aurora_search("payment error handling try except")]
**Result**: Try/except blocks in payment code

## Troubleshooting

### MCP Server Not Starting
**Symptoms**: Claude Desktop shows "Server failed to start"
**Checks**:
- Python version: `python --version` (must be 3.10+)
- MCP binary in PATH: `which aurora-mcp`
- Logs: `tail -f ~/.aurora/mcp.log`
**Solutions**:
- Reinstall: `pip install --force-reinstall aurora`
- Check permissions on aurora-mcp binary

### Claude Desktop Not Finding Tools
**Symptoms**: Claude says "I don't have access to that tool"
**Checks**:
- Config syntax valid (JSON)
- Config file location correct
- Claude Desktop restarted after config change
**Solutions**:
- Validate JSON: `python -m json.tool < config.json`
- Restart Claude Desktop completely (not just window)

### Indexing Fails
**Symptoms**: `aur mem index` errors or no chunks created
**Checks**:
- File permissions: Can Python read files?
- Disk space: `df -h`
- Verbose mode: `aur mem index . --verbose`
**Solutions**:
- Fix permissions: `chmod -R u+r ~/my-project`
- Free up disk space
- Check logs for specific errors

### Search Returns No Results
**Symptoms**: `aurora_search` returns empty list
**Checks**:
- Files actually indexed: `aur mem stats`
- Query format: Natural language or keywords
**Solutions**:
- Reindex: `aur mem index . --force`
- Try simpler query: "authentication" instead of "how does auth work"

### Embeddings Slow or Failing
**Symptoms**: Indexing very slow, embedding errors
**Checks**:
- Sentence-BERT installed: `pip list | grep sentence-transformers`
- Model downloaded: Check `~/.aurora/models/`
**Solutions**:
- Install ML deps: `pip install aurora[ml]`
- First run downloads model (can be slow)

## Advanced Configuration

### Custom Database Path
```json
{
  "mcpServers": {
    "aurora": {
      "command": "aurora-mcp",
      "args": ["--db-path", "/custom/path/aurora.db"]
    }
  }
}
```

### Performance Tuning
- Increase search limit: `aurora_search("query", limit=20)`
- Reduce embedding model size for speed (trade quality)
- Index only relevant directories

## FAQ

**Q: Do I need an Anthropic API key?**
A: No, MCP server uses local embeddings. Claude Desktop provides the LLM.

**Q: Can I use AURORA with other AI tools?**
A: Yes, any MCP-compatible client works (not just Claude Desktop).

**Q: How often should I reindex?**
A: After significant code changes. No auto-indexing in v0.2.0.

**Q: Does AURORA send my code to the cloud?**
A: No, all data stays local. Only Claude Desktop (if using Claude) makes API calls.
```

### TROUBLESHOOTING.md Structure

```markdown
# AURORA Troubleshooting Guide

## Common Issues

### Installation Issues
[Details from MCP_SETUP.md troubleshooting section]

### CLI Issues
[Common CLI errors and solutions]

### MCP Issues
[MCP-specific problems and fixes]

## Diagnostic Commands

```bash
# Check installation
aur --verify

# Check MCP server status
aurora-mcp status

# View logs
tail -f ~/.aurora/mcp.log

# Test indexing
aur mem index . --verbose

# Database stats
aur mem stats
```

## Getting Help

- GitHub Issues: [link]
- Documentation: [link]
- Community: [link]
```

### README.md Updates

**Key Changes**:
1. **Installation Section**: Show single `pip install aurora` command
2. **Quick Start**: MCP integration as primary workflow (not buried)
3. **Standalone Usage**: CLI commands for non-MCP usage
4. **Links**: Point to MCP_SETUP.md and TROUBLESHOOTING.md

**Example Quick Start**:
```markdown
## Quick Start

### Install AURORA
```bash
pip install aurora
```

### Use with Claude Desktop (Recommended)
1. Configure MCP server (see [MCP Setup Guide](docs/MCP_SETUP.md))
2. Index your codebase:
   ```bash
   aur mem index ~/my-project
   ```
3. Chat with Claude about your code!

### Use Standalone CLI
```bash
# Initialize
aur init

# Index codebase
aur mem index .

# Search code
aur mem search "authentication"

# Ask questions
aur query "How does the auth system work?"
```

### Verify Installation
```bash
aur --verify
```

For troubleshooting, see [Troubleshooting Guide](docs/TROUBLESHOOTING.md).
```

---

## 10. Success Metrics

### Quantitative Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Installation Success Rate | 100% | Smoke tests pass on clean environments |
| CLI Bug Fix Verification | 3/3 bugs fixed | Integration tests pass |
| MCP Tool Coverage | 5/5 tools implemented | MCP test harness validates all |
| Test Coverage - CLI | 80%+ unit, 100% integration | pytest --cov |
| Test Coverage - MCP | 90%+ unit, 100% integration | pytest --cov |
| Documentation Completeness | 100% | All deliverables listed in plan completed |
| Demo Workflow Success | 2/2 workflows pass | Manual validation |

### Qualitative Metrics

1. **User Satisfaction**
   - User can install AURORA without confusion
   - User understands how to use MCP integration
   - Error messages are actionable

2. **Code Quality**
   - All critical bugs resolved
   - Integration tests prevent future regressions
   - Code is maintainable (clear structure, documented)

3. **Documentation Quality**
   - MCP setup guide is comprehensive and clear
   - Troubleshooting guide resolves common issues
   - Examples work as documented

### Acceptance Testing

**User Validation Checklist**:

**Installation & Setup**:
- [ ] Fresh install with `pip install aurora` succeeds
- [ ] Installation shows clear component feedback
- [ ] `aur --verify` confirms healthy installation
- [ ] MCP server configured in Claude Desktop

**Standalone CLI**:
- [ ] `aur init` creates config without crash
- [ ] `aur mem index .` indexes codebase without errors
- [ ] `aur mem search "term"` returns relevant results
- [ ] `aur query "question"` generates answer

**MCP Integration**:
- [ ] Chat with Claude: "Search my code for authentication"
- [ ] Claude calls aurora_search and returns results
- [ ] Chat: "What does UserService do?"
- [ ] Claude calls aurora_context and shows code
- [ ] Chat: "Find all uses of DatabaseConnection"
- [ ] Claude calls aurora_search and finds usages

**Error Handling**:
- [ ] Missing config shows clear error and next steps
- [ ] Invalid query shows helpful guidance
- [ ] MCP server failure shows diagnostic info

**Documentation**:
- [ ] MCP_SETUP.md is comprehensive and accurate
- [ ] TROUBLESHOOTING.md resolves issues encountered
- [ ] README.md provides clear quick start

**Overall Impression**:
- [ ] Installation is simple (one command)
- [ ] MCP integration "just works"
- [ ] Documentation answers questions
- [ ] Ready for production use

### Definition of Success

**v0.2.0 is successful when**:

1. **Technical**: All acceptance criteria met (must-haves completed)
2. **User**: User validates both demo workflows work end-to-end
3. **Quality**: All tests pass (unit, integration, smoke, manual)
4. **Documentation**: User can follow guides without additional help
5. **Stability**: No crashes or blocking errors in core workflows

**Release Readiness**:
- [ ] All phases completed
- [ ] All acceptance criteria met
- [ ] User validation passed
- [ ] Documentation complete
- [ ] CHANGELOG.md updated
- [ ] Git tagged v0.2.0
- [ ] Ready for PyPI release

---

## 11. Risk Management

### Risk Register

| Risk ID | Risk Description | Probability | Impact | Mitigation Strategy | Owner |
|---------|------------------|-------------|--------|---------------------|-------|
| R1 | Package consolidation breaks imports | Medium | High | Run full test suite after each change, automated find/replace | Dev |
| R2 | MCP integration more complex than expected | Medium | High | Start with minimal tools, use FastMCP library | Dev |
| R3 | Integration tests miss bugs | Low | High | Use real components (no mocks), manual smoke tests | QA |
| R4 | Sentence-BERT quality insufficient | Low | Medium | Document tradeoff, make configurable in future | PM |
| R5 | Claude Desktop config issues | Medium | Medium | Comprehensive troubleshooting guide, test multiple environments | Support |
| R6 | Timeline slips (5 days too aggressive) | Medium | Medium | Prioritize must-haves, defer nice-to-haves | PM |
| R7 | User finds new critical bugs | Low | High | Thorough testing, early user validation | QA |

### Detailed Risk Mitigation

**R1: Package Consolidation Breaks Imports**
- **Probability**: Medium (touching many files)
- **Impact**: High (blocks all functionality)
- **Mitigation**:
  - Use automated find/replace with regex patterns
  - Run unit tests after each batch of changes
  - Git branch for easy rollback
  - Manual spot-checks of critical files
- **Contingency**: If too many breaks, revert and do manual migration

**R2: MCP Integration Complex**
- **Probability**: Medium (new technology)
- **Impact**: High (core v0.2.0 feature)
- **Mitigation**:
  - Start with 1 tool (aurora_search) to prove concept
  - Use FastMCP library examples as templates
  - Allocate 2 full days (buffer time)
  - Fallback: Reduce from 5 tools to 3 core tools
- **Contingency**: If FastMCP doesn't work, switch to official MCP SDK

**R3: Integration Tests Miss Bugs**
- **Probability**: Low (lessons learned from v0.1.0)
- **Impact**: High (defeats purpose of adding tests)
- **Mitigation**:
  - Use real SQLiteStore, real embeddings, real file I/O
  - No mocks for integration tests
  - Manual smoke tests after automated tests
  - User validation as final gate
- **Contingency**: If bugs found post-release, hotfix v0.2.1

**R4: Sentence-BERT Quality Insufficient**
- **Probability**: Low (proven model)
- **Impact**: Medium (affects search relevance)
- **Mitigation**:
  - Document model choice and tradeoffs
  - Make configurable in future (v0.2.1)
  - Use hybrid retrieval (keyword + semantic) to compensate
- **Acceptance**: User understands free/offline vs quality tradeoff
- **Contingency**: Add config option for OpenAI embeddings if needed

**R5: Claude Desktop Configuration Issues**
- **Probability**: Medium (user-facing config)
- **Impact**: Medium (blocks MCP usage)
- **Mitigation**:
  - Comprehensive troubleshooting guide
  - Test on multiple environments (macOS, Linux, Windows)
  - Clear error messages from MCP server
  - Example configs validated
- **Support**: Provide diagnostic command `aurora-mcp --diagnose`

**R6: Timeline Slips**
- **Probability**: Medium (ambitious 5-day sprint)
- **Impact**: Medium (delays release)
- **Mitigation**:
  - Prioritize must-haves over should-haves
  - Daily progress checkpoints
  - Defer nice-to-haves immediately if slipping
  - Cut scope (e.g., 3 MCP tools instead of 5)
- **Escalation**: If > 2 days behind, extend sprint or reduce scope

**R7: User Finds New Critical Bugs**
- **Probability**: Low (thorough testing planned)
- **Impact**: High (blocks release)
- **Mitigation**:
  - Early user validation (Day 4)
  - Comprehensive smoke tests
  - Integration tests with real components
  - Manual testing of all workflows
- **Response**: Fix immediately if P0, defer to v0.2.1 if P1/P2

### Rollback & Recovery

**Rollback Plan**:
1. **Package Consolidation Issues**:
   - Revert to phase2-start branch
   - Keep old 6-package structure for v0.2.0
   - Document cleanup for v0.3.0

2. **MCP Server Issues**:
   - Release v0.2.0 without MCP (just bug fixes + consolidation)
   - MCP becomes v0.2.1 feature

3. **Critical Bug Found Late**:
   - If found in Phase 4: Fix before release
   - If found post-release: Hotfix v0.2.1 within 48 hours

**Version Pinning for Users**:
- If v0.2.0 has issues, users can downgrade: `pip install aurora==0.1.0`
- Keep v0.1.0 packages published on PyPI

---

## 12. Technical Debt Updates

### New Technical Debt Items

**TD-P2-009: Comprehensive Error Message Audit**
- **Priority**: P2
- **Description**: Review and improve ALL error messages across AURORA
- **Scope**: CLI, MCP, core components
- **Effort**: Medium (2-3 days)
- **Sprint**: Next sprint after v0.2.0
- **Rationale**: Quick pass this sprint, full audit later

**TD-P2-010: Real-Time File Watching for Auto-Indexing**
- **Priority**: P2
- **Description**: Watch file system for changes, auto-reindex modified files
- **Scope**: MCP server, CLI
- **Effort**: Medium (2-3 days)
- **Sprint**: Future (v0.3.0)
- **Rationale**: Nice to have but not blocking

### Resolved Technical Debt

**TD-P2-002: No Headless Mode Tests**
- **Status**: ✅ RESOLVED in v0.2.0
- **Resolution**: Added `tests/unit/cli/test_headless.py`

**TD-P2-003: Memory Integration Tests**
- **Status**: ✅ RESOLVED in v0.2.0
- **Resolution**: Added `tests/integration/test_memory_e2e.py`

### Deferred Technical Debt

Still deferred to future sprints:
- TD-P2-001: LLM Client Test Coverage (51.33%)
- TD-P2-004: Configuration Validation Tests
- TD-P2-005: Store Relationship Traversal Tests
- TD-P2-006: Deprecation Warnings (datetime.utcnow)
- TD-P2-007: Token Usage Tracking Missing
- TD-P2-008: No Retries on Transient API Errors

**Rationale**: Focus on stability and MCP integration first. These don't block v0.2.0 release.

---

## 13. Open Questions

### Resolved During Elicitation

✅ **Q1**: Should we keep 6 packages or consolidate to 1?
- **Answer**: Keep 6 packages underneath, provide meta-package for single install

✅ **Q2**: Which MCP library to use?
- **Answer**: FastMCP (Python-native, simpler)

✅ **Q3**: How many integration tests to add?
- **Answer**: 3 for memory (index-search-retrieve, index-delete, index-export-import)

✅ **Q4**: What level of MCP documentation?
- **Answer**: Comprehensive (setup, examples, troubleshooting)

✅ **Q5**: Which embeddings provider?
- **Answer**: Sentence-BERT (local, offline, free)

✅ **Q6**: Phase ordering?
- **Answer**: Phase 2 (consolidation) → Phase 1 (bugs) → Phase 3 (MCP) → Phase 4 (testing)

✅ **Q7**: Always-on vs on-demand MCP?
- **Answer**: Both modes supported, user chooses via config

### Remaining Open Questions

**Q1**: Should we create a video walkthrough for MCP setup?
- **Options**:
  A) Yes, 5-minute video showing installation → config → usage
  B) No, written guide sufficient
- **Impact**: Higher adoption if video provided
- **Effort**: 2-3 hours
- **Decision**: Defer to post-v0.2.0 (nice to have, not blocking)

**Q2**: Should we add telemetry to track MCP tool usage?
- **Options**:
  A) Yes, anonymous usage stats (which tools called, frequency)
  B) No, privacy-first, no telemetry
- **Impact**: Helps prioritize future features if we know usage patterns
- **Privacy**: Opt-in only, no code content sent
- **Decision**: Defer to v0.3.0 (not needed for v0.2.0)

**Q3**: Should we support Windows for MCP server?
- **Options**:
  A) Yes, test on Windows and document
  B) macOS/Linux only for v0.2.0
- **Impact**: Windows is large developer base
- **Effort**: Windows testing adds 1 day
- **Decision**: **NEEDS USER INPUT** - Support Windows in v0.2.0 or defer to v0.2.1?

---

## 14. Dependencies & Prerequisites

### External Dependencies

**Required for All Users**:
- Python >= 3.10
- pip (Python package installer)
- SQLite3 (included with Python)

**Required for MCP Integration**:
- Claude Desktop (or other MCP-compatible client)
- Sentence-BERT model (auto-downloaded on first use)

**Optional**:
- Git (for version control)
- Virtual environment (recommended)

### Python Package Dependencies

**Core Dependencies** (installed with `pip install aurora`):
```toml
[dependencies]
click = "^8.1.0"           # CLI framework
toml = "^0.10.2"           # Configuration parsing
pydantic = "^2.0.0"        # Data validation
fastmcp = "^0.5.0"         # MCP server framework
sentence-transformers = "^2.2.0"  # Local embeddings
numpy = "^1.24.0"          # Vector operations
sqlalchemy = "^2.0.0"      # Database ORM
```

**Development Dependencies** (installed with `pip install aurora[dev]`):
```toml
[dev-dependencies]
pytest = "^7.4.0"          # Testing framework
pytest-cov = "^4.1.0"      # Coverage reporting
black = "^23.0.0"          # Code formatting
mypy = "^1.5.0"            # Type checking
ruff = "^0.1.0"            # Linting
```

### System Requirements

**Minimum**:
- 4 GB RAM
- 2 GB free disk space (for embeddings model)
- Python 3.10+

**Recommended**:
- 8 GB RAM
- 5 GB free disk space
- Python 3.11+
- SSD for faster indexing

### Platform Support

**Supported Platforms**:
- macOS (Intel and Apple Silicon)
- Linux (Ubuntu 20.04+, Debian 11+, Fedora 35+)
- Windows (**Q3 above - decision needed**)

**Tested Environments**:
- macOS 13+ with Python 3.10, 3.11
- Ubuntu 22.04 with Python 3.10, 3.11
- Windows 11 with Python 3.11 (if included)

### Claude Desktop Compatibility

**Supported Versions**:
- Claude Desktop v1.0+
- Any MCP-compatible client

**Configuration File Locations**:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json` (if supported)

---

## 15. Release Checklist

### Pre-Release (Phase 4, Day 5)

**Code Quality**:
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All smoke tests pass
- [ ] Code coverage meets targets (CLI 80%, MCP 90%)
- [ ] No critical linting errors
- [ ] Type checking passes

**Functionality**:
- [ ] All 3 critical bugs fixed and verified
- [ ] Package consolidation works (single install)
- [ ] MCP server implements 5 tools
- [ ] Both MCP modes work (always-on, on-demand)
- [ ] Demo workflows validated

**Documentation**:
- [ ] MCP_SETUP.md complete
- [ ] TROUBLESHOOTING.md complete
- [ ] README.md updated
- [ ] CHANGELOG.md updated with v0.2.0 changes
- [ ] All code examples tested

**User Validation**:
- [ ] User personally tests installation
- [ ] User validates MCP integration workflow
- [ ] User validates standalone CLI workflow
- [ ] User approves documentation

### Release (Post-Validation)

**Version Control**:
- [ ] All changes committed to main branch
- [ ] Git tag created: `v0.2.0`
- [ ] Release notes drafted in GitHub

**Package Publishing**:
- [ ] Meta-package `aurora` built
- [ ] All 6 sub-packages built
- [ ] Test publish to Test PyPI
- [ ] Verify test install works
- [ ] Publish to production PyPI
- [ ] Verify production install works

**Announcement**:
- [ ] GitHub release created
- [ ] Release notes published
- [ ] Documentation site updated (if exists)
- [ ] Community notified (if community exists)

### Post-Release

**Monitoring**:
- [ ] Watch GitHub issues for bug reports
- [ ] Monitor installation success rate
- [ ] Collect user feedback

**Hotfix Readiness**:
- [ ] Hotfix branch ready (if needed)
- [ ] v0.2.1 plan in place for critical bugs

---

## Appendix A: Command Reference

### Installation Commands

```bash
# Install AURORA
pip install aurora

# Install with all extras
pip install aurora[all]

# Install ML dependencies only
pip install aurora[ml]

# Install development tools
pip install aurora[dev]

# Uninstall
aurora-uninstall
# OR
aurora-uninstall --keep-config

# Verify installation
aur --verify
```

### CLI Commands

```bash
# Initialize configuration
aur init

# Memory management
aur mem index <path>              # Index files
aur mem index . --pattern "*.py"  # Index Python files only
aur mem search <query>            # Search indexed code
aur mem stats                     # Show memory statistics

# Query
aur query "question"              # Ask question
aur query "question" --dry-run    # Show escalation plan

# Headless mode (both syntaxes work)
aur headless test.md
aur --headless test.md

# Help
aur --help
aur mem --help
aur query --help
```

### MCP Commands

```bash
# Start MCP server (always-on mode)
aurora-mcp start

# Stop MCP server (on-demand mode)
aurora-mcp stop

# Check MCP server status
aurora-mcp status

# Test MCP server
aurora-mcp --test

# Start MCP server with custom database
aurora-mcp --db-path /custom/path/aurora.db
```

---

## Appendix B: Example Configurations

### Claude Desktop MCP Configuration

**macOS/Linux**:
```json
{
  "mcpServers": {
    "aurora": {
      "command": "aurora-mcp",
      "args": ["--db-path", "~/projects/myapp/aurora.db"]
    }
  }
}
```

**Windows** (if supported):
```json
{
  "mcpServers": {
    "aurora": {
      "command": "aurora-mcp.exe",
      "args": ["--db-path", "C:\\Users\\YourName\\projects\\myapp\\aurora.db"]
    }
  }
}
```

### AURORA Configuration File

**~/.aurora/config.toml**:
```toml
[core]
db_path = "~/.aurora/aurora.db"
log_level = "INFO"

[embeddings]
model = "sentence-transformers/all-MiniLM-L6-v2"
cache_dir = "~/.aurora/models"
batch_size = 32

[mcp]
always_on = false  # Set to true for always-on mode
log_file = "~/.aurora/mcp.log"
max_results = 10   # Default search result limit

[soar]
max_iterations = 5
timeout = 300  # seconds
```

---

## Appendix C: File Locations

### User Data

- **Configuration**: `~/.aurora/config.toml`
- **Database**: `~/.aurora/aurora.db` (default, configurable)
- **Logs**: `~/.aurora/mcp.log` (MCP server logs)
- **Models**: `~/.aurora/models/` (sentence-transformers cache)

### Source Code

- **Meta-package**: `aurora/pyproject.toml`
- **Core**: `packages/core/`
- **Context Code**: `packages/context_code/`
- **SOAR**: `packages/soar/`
- **Reasoning**: `packages/reasoning/`
- **CLI**: `packages/cli/`
- **Testing**: `packages/testing/`
- **MCP**: `src/aurora/mcp/`

### Documentation

- **MCP Setup**: `docs/MCP_SETUP.md`
- **Troubleshooting**: `docs/TROUBLESHOOTING.md`
- **README**: `README.md`
- **Changelog**: `CHANGELOG.md`
- **Technical Debt**: `docs/TECHNICAL_DEBT.md`

### Tests

- **Unit**: `tests/unit/`
- **Integration**: `tests/integration/`
- **Smoke**: `tests/smoke_tests.sh`

---

## Appendix D: MCP Tool Schemas

### aurora_search

```typescript
{
  "name": "aurora_search",
  "description": "Search indexed codebase using hybrid retrieval (semantic + keyword)",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search query (natural language or keywords)"
      },
      "limit": {
        "type": "integer",
        "description": "Maximum number of results to return",
        "default": 10
      }
    },
    "required": ["query"]
  },
  "outputSchema": {
    "type": "array",
    "items": {
      "type": "object",
      "properties": {
        "file_path": { "type": "string" },
        "function_name": { "type": "string" },
        "content": { "type": "string" },
        "score": { "type": "number" },
        "chunk_id": { "type": "string" }
      }
    }
  }
}
```

### aurora_index

```typescript
{
  "name": "aurora_index",
  "description": "Index files into AURORA memory store",
  "inputSchema": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "Directory path to index"
      },
      "pattern": {
        "type": "string",
        "description": "File pattern to match (e.g., *.py)",
        "default": "*.py"
      }
    },
    "required": ["path"]
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "files_indexed": { "type": "integer" },
      "chunks_created": { "type": "integer" },
      "duration_seconds": { "type": "number" }
    }
  }
}
```

### aurora_stats

```typescript
{
  "name": "aurora_stats",
  "description": "Get memory store statistics",
  "inputSchema": {
    "type": "object",
    "properties": {}
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "total_chunks": { "type": "integer" },
      "total_files": { "type": "integer" },
      "database_size_mb": { "type": "number" },
      "indexed_at": { "type": "string" }
    }
  }
}
```

### aurora_context

```typescript
{
  "name": "aurora_context",
  "description": "Retrieve code context for specific file/function",
  "inputSchema": {
    "type": "object",
    "properties": {
      "file_path": {
        "type": "string",
        "description": "Path to source file"
      },
      "function": {
        "type": "string",
        "description": "Optional specific function name",
        "default": null
      }
    },
    "required": ["file_path"]
  },
  "outputSchema": {
    "type": "string",
    "description": "Code content with context"
  }
}
```

### aurora_related

```typescript
{
  "name": "aurora_related",
  "description": "Find related code chunks using ACT-R spreading activation",
  "inputSchema": {
    "type": "object",
    "properties": {
      "chunk_id": {
        "type": "string",
        "description": "Starting chunk identifier"
      },
      "max_hops": {
        "type": "integer",
        "description": "Maximum relationship hops",
        "default": 2
      }
    },
    "required": ["chunk_id"]
  },
  "outputSchema": {
    "type": "array",
    "items": {
      "type": "object",
      "properties": {
        "chunk_id": { "type": "string" },
        "file_path": { "type": "string" },
        "function_name": { "type": "string" },
        "content": { "type": "string" },
        "activation_score": { "type": "number" },
        "relationship_type": { "type": "string" }
      }
    }
  }
}
```

---

## Appendix E: Glossary

**ACT-R**: Adaptive Control of Thought—Rational, a cognitive architecture theory used in AURORA for spreading activation and memory retrieval

**Always-On Mode**: MCP operating mode where every Claude Desktop query routes through AURORA tools

**Claude Desktop**: Anthropic's desktop application for chatting with Claude AI

**Chunk**: Unit of code storage in AURORA (typically a function, class, or module)

**FastMCP**: Python library for building Model Context Protocol servers

**Headless Mode**: CLI mode for running AURORA without interactive prompts

**Hybrid Retrieval**: Search combining semantic (embedding-based) and keyword-based retrieval

**Integration Test**: Test using real components (no mocks) to verify end-to-end workflows

**MCP**: Model Context Protocol, standard for AI assistants to call external tools

**Meta-Package**: Python package that installs other packages as dependencies

**On-Demand Mode**: MCP operating mode where AURORA tools are only called when explicitly invoked

**Sentence-BERT**: Sentence embedding model for semantic similarity

**Smoke Test**: Quick validation test to ensure basic functionality works

**Spreading Activation**: ACT-R mechanism for finding related chunks based on relationships

**SQLite**: Embedded SQL database used for AURORA memory storage

---

**END OF PRD**
