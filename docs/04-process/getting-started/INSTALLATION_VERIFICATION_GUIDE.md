# AURORA Installation Verification & Testing Guide

**Date**: 2025-12-24
**Version**: v1.0.0-phase3
**Status**: Production Ready (1,824 tests passing, 88.41% coverage)

---

## Current Installation Issue: NumPy Compatibility

### Problem Identified

Your AURORA installation is experiencing a **NumPy version incompatibility**:

```
A NumPy version >=1.21.6 and <1.28.0 is required for this version of SciPy (detected version 2.2.6)
A module that was compiled using NumPy 1.x cannot be run in NumPy 2.2.6
```

**Root Cause**: The ML dependencies (sentence-transformers, scikit-learn, scipy) were compiled against NumPy 1.x but your system has NumPy 2.2.6 installed.

### Solution: Downgrade NumPy

```bash
# Downgrade NumPy to compatible version
pip3 install "numpy<2.0"

# Verify the fix
aur --help
```

**Expected output after fix**:
```
Usage: aur [OPTIONS] COMMAND [ARGS]...

  AURORA: Adaptive Unified Reasoning and Orchestration Architecture.

  A cognitive architecture framework for intelligent context management,
  reasoning, and agent orchestration.

  Examples:
      aur mem "authentication"              # Search memory
      aur query "How to calculate totals?"  # Query with auto-escalation
      aur goals "Add feature"               # Decompose goals and match agents

Options:
  -v, --verbose       Enable verbose logging
  --debug             Enable debug logging
  --version           Show the version and exit.
  --help              Show this message and exit.

Commands:
  mem       Search AURORA memory for relevant chunks.
  query     Execute a query with automatic escalation.
  goals     Decompose goals and match agents to tasks.
  spawn     Execute tasks in parallel.
```

---

## CLI Commands Available

### Command Aliases

AURORA provides **two command aliases** (not `aurora-cli`):
- `aur` - Short form (recommended)
- `aurora` - Long form

### Core Commands

#### 1. Memory Search (`aur mem`)

Search AURORA's memory for relevant code chunks and reasoning patterns:

```bash
# Basic memory search
aur mem "authentication"

# With filters and options
aur mem "calculate total" --max-results 20 --type function

# Show content of retrieved chunks
aur mem "error handling" --show-content

# Search specific types
aur mem "database" --type class    # Search for classes
aur mem "config" --type function   # Search for functions
```

**Options**:
- `--max-results N` - Limit number of results (default: 10)
- `--type TYPE` - Filter by chunk type (function, class, etc.)
- `--show-content` - Display full chunk content (not just metadata)

#### 2. Query with Auto-Escalation (`aur query`)

Execute queries with automatic routing between direct LLM (fast) and full AURORA pipeline (comprehensive):

```bash
# Simple query (likely uses direct LLM)
aur query "What is a function?"

# Complex query (likely uses full AURORA)
aur query "Design a microservices architecture for user authentication"

# Show escalation reasoning
aur query "Refactor the database layer" --show-reasoning

# Force AURORA mode
aur query "Explain classes" --force-aurora

# Force direct LLM mode
aur query "What is Python?" --force-direct

# Custom complexity threshold (0.0-1.0, default 0.6)
aur query "Implement caching" --threshold 0.4
```

**Auto-Escalation Features**:
- **Complexity Assessment**: Automatically analyzes query complexity
- **Intelligent Routing**: Routes simple queries to fast LLM, complex queries to full AURORA
- **Transparent**: Shows which path was chosen with `--show-reasoning`
- **Configurable**: Adjust threshold or force specific mode

**Note**: Query command execution is partially implemented (shows routing decision but doesn't execute actual query yet).

#### 3. Goals Command (`aur goals`)

Decompose goals and match agents to tasks:

```bash
# Decompose a goal
aur goals "Add user authentication"

# View matched agents
aur agents list
```

---

## Testing Workflow

### 1. Basic CLI Verification

```bash
# Test command help
aur --help
aur mem --help
aur query --help
aur goals --help

# Test version
aur --version
```

### 2. Memory System Test

```bash
# Initialize test database
cd /home/hamr/PycharmProjects/aurora

# Run memory search (will create DB if needed)
aur mem "store" --max-results 5

# Search for specific code patterns
aur mem "SQLiteStore" --type class --show-content
```

### 3. Auto-Escalation Test

```bash
# Test simple query routing
aur query "What is AURORA?" --show-reasoning

# Test complex query routing
aur query "Design a distributed caching system with Redis and implement connection pooling" --show-reasoning

# Compare with forced modes
aur query "Explain functions" --force-direct --show-reasoning
aur query "Explain functions" --force-aurora --show-reasoning
```

### 4. Python API Test

Create a test script to verify programmatic access:

```python
# test_aurora.py
from aurora_core.store import SQLiteStore
from aurora_context_code import PythonParser
from aurora_soar.orchestrator import SOAROrchestrator

# Test 1: Storage
print("Test 1: Storage System")
store = SQLiteStore("test_aurora.db")
print(f"✓ Store initialized")

# Test 2: Code Parsing
print("\nTest 2: Code Parser")
parser = PythonParser()
chunks = parser.parse_file("packages/core/src/aurora_core/models.py")
print(f"✓ Parsed {len(chunks)} chunks")

# Test 3: SOAR Orchestrator
print("\nTest 3: SOAR Orchestrator")
orchestrator = SOAROrchestrator(
    config_path="tests/fixtures/test-config.json"
)
print(f"✓ Orchestrator initialized")
print(f"✓ All core systems operational")
```

Run with:
```bash
python3 test_aurora.py
```

### 5. Run Existing Test Suite

```bash
# Run all tests
cd /home/hamr/PycharmProjects/aurora
pytest -v

# Run specific test modules
pytest tests/unit/cli/ -v          # CLI tests
pytest tests/unit/core/ -v         # Core functionality
pytest tests/integration/ -v       # Integration tests

# Run with coverage
pytest --cov=packages --cov-report=html
```

---

## MCP Integration: Current Status

### Short Answer
**AURORA does not currently have native MCP (Model Context Protocol) integration implemented.**

### What MCP Integration Would Provide

MCP integration would allow AURORA to be used as a **context server** for Claude Desktop or other MCP-compatible AI tools, enabling:

1. **Memory Access**: Claude could query AURORA's memory directly
2. **Code Understanding**: Semantic search across parsed codebases
3. **Agent Orchestration**: Use AURORA's SOAR pipeline from within Claude
4. **Persistent Context**: Share memory across multiple Claude sessions

### MCP Status in AURORA

Based on codebase analysis:

✗ **Not Implemented**: No MCP server code exists
✗ **Not Documented**: No MCP setup guides
✓ **Mentioned in Research**: MCP discussed in strategic planning docs
✓ **Architecture Compatible**: AURORA's design supports MCP integration

### How to Create MCP Integration (Future Work)

If you want to create an MCP server for AURORA, you would need to:

#### Option 1: Python MCP Server (Recommended)

Create `packages/mcp-server/src/aurora_mcp/server.py`:

```python
"""AURORA MCP Server - Model Context Protocol integration."""

from mcp.server import Server
from mcp.types import Tool, TextContent
from aurora_core.store import SQLiteStore
from aurora_soar.orchestrator import SOAROrchestrator

# Initialize MCP server
server = Server("aurora-mcp")

# Initialize AURORA components
store = SQLiteStore("aurora.db")
orchestrator = SOAROrchestrator()

@server.tool()
async def search_memory(
    query: str,
    max_results: int = 10,
    chunk_type: str = None
) -> TextContent:
    """Search AURORA memory for relevant code chunks."""
    results = store.search(query, limit=max_results, type=chunk_type)
    return TextContent(
        type="text",
        text=format_search_results(results)
    )

@server.tool()
async def reason(query: str) -> TextContent:
    """Execute SOAR reasoning pipeline."""
    result = await orchestrator.execute(query)
    return TextContent(
        type="text",
        text=result.response
    )

if __name__ == "__main__":
    server.run()
```

#### Option 2: Configuration for Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "aurora": {
      "command": "python",
      "args": ["-m", "aurora_mcp.server"],
      "cwd": "/home/hamr/PycharmProjects/aurora",
      "env": {
        "AURORA_DB": "/home/hamr/.aurora/memory.db"
      }
    }
  }
}
```

#### Option 3: Use FastMCP (Simpler)

```python
# packages/mcp-server/src/aurora_mcp/server.py
from fastmcp import FastMCP
from aurora_core.store import SQLiteStore

mcp = FastMCP("AURORA Context Server")
store = SQLiteStore("aurora.db")

@mcp.tool()
def search_memory(query: str, max_results: int = 10) -> str:
    """Search AURORA memory for code and reasoning patterns."""
    results = store.search(query, limit=max_results)
    return "\n\n".join([
        f"# {r.metadata.get('name', 'Unknown')}\n{r.content}"
        for r in results
    ])

@mcp.tool()
def get_stats() -> str:
    """Get AURORA memory statistics."""
    stats = store.get_statistics()
    return f"Total chunks: {stats['total']}, Types: {stats['types']}"
```

### Recommended Approach

**For immediate use**, I recommend:

1. **Fix NumPy issue first** (see above)
2. **Use AURORA programmatically** via Python API
3. **Create MCP wrapper** as a separate Phase 4 feature

**For MCP integration**, I suggest:

1. Review the `/mcp-builder` skill from your agents (available in Claude Code)
2. Create dedicated `packages/mcp-server` package
3. Implement 2-3 core tools: `search_memory`, `reason`, `get_context`
4. Test with Claude Desktop integration
5. Document in a new `docs/MCP_INTEGRATION_GUIDE.md`

---

## Quick Reference

### Commands Summary

```bash
# Fix NumPy compatibility
pip3 install "numpy<2.0"

# Verify installation
aur --help
aur --version

# Memory operations
aur mem "search term" [--max-results N] [--type TYPE] [--show-content]

# Query with auto-escalation
aur query "your question" [--show-reasoning] [--force-aurora] [--force-direct]

# Goals decomposition
aur goals "Add feature"

# Parallel task execution
aur spawn

# Run tests
pytest -v
pytest tests/unit/cli/ -v
```

### Expected Performance

- **Memory Search**: <100ms for small DBs, <500ms for 10K chunks
- **Simple Queries**: <2s (direct LLM)
- **Complex Queries**: <10s (full SOAR pipeline)

### Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Command hangs | NumPy incompatibility | `pip3 install "numpy<2.0"` |
| `aurora-cli: command not found` | Wrong command name | Use `aur` or `aurora` instead |
| Import errors | Missing dependencies | `pip3 install -e packages/cli` |
| DB not found | Not initialized | Run any `aur mem` command to create DB |

---

## Next Steps

1. **Fix NumPy**: `pip3 install "numpy<2.0"`
2. **Verify CLI**: `aur --help`
3. **Test Memory**: `aur mem "store" --show-content`
4. **Test Escalation**: `aur query "test query" --show-reasoning`
5. **Run Test Suite**: `pytest tests/unit/cli/ -v`
6. **Explore API**: Create test script and run `python3 test_aurora.py`

**For MCP Integration**: This is a future enhancement. Consider creating a feature request issue or using the `@market-researcher` agent to draft an MCP integration PRD.

---

## Support

- **Documentation**: `/home/hamr/PycharmProjects/aurora/docs/`
- **Test Fixtures**: `/home/hamr/PycharmProjects/aurora/tests/fixtures/`
- **Configuration**: `tests/fixtures/test-config.json`
- **Issues**: Check git history and existing test patterns

**Questions?** Use `@orchestrator` or `@code-developer` agents in Claude Code for troubleshooting.
