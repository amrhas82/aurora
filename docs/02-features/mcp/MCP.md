# MCP Tools

Aurora provides Model Context Protocol (MCP) tools for code intelligence and search.

## Overview

Aurora's MCP server exposes two primary tools:
- **lsp** - Language Server Protocol integration for code analysis
- **mem_search** - Hybrid search with LSP enrichment

These tools are available in:
- Claude Desktop (via MCP)
- Cursor (via MCP)
- Cline (VS Code extension)
- Continue (VS Code extension)

## lsp Tool

The `lsp` MCP tool provides five actions for code intelligence.

> **Speed Note:** Many operations use ripgrep (~2ms/symbol) instead of LSP (~300ms/symbol) for 100x speed improvement.
>
> See [Code Intelligence Status](../lsp/CODE_INTELLIGENCE_STATUS.md) for comprehensive feature documentation.

### deadcode Action

Find unused symbols across the codebase.

**Usage:**
```json
{
  "action": "deadcode",
  "path": ""  // Optional: specific file or directory
}
```

**Returns:**
```json
{
  "action": "deadcode",
  "path": "/path/to/codebase",
  "dead_code": [
    {
      "file": "src/utils/helper.py",
      "line": 42,
      "symbol": "unused_function",
      "type": "function",
      "severity": "HIGH"
    }
  ],
  "total": 5,
  "report_path": "/docs/CODE_QUALITY_REPORT.md"
}
```

**CODE_QUALITY_REPORT.md Format:**
```markdown
# Code Quality Report

Generated: 2024-01-15 14:30:00

## Summary
- Total Dead Code Items: 5
- CRITICAL: 0
- HIGH: 2
- MEDIUM: 2
- LOW: 1

## Dead Code Details

### CRITICAL (0 items)
(none)

### HIGH (2 items)

#### File: src/utils/helper.py
- **Line 42**: Function `unused_function`
  - **Severity**: HIGH
  - **Reason**: Unused function
  - **Action**: Consider removing or documenting why it's kept

### MEDIUM (2 items)
...
```

**Automatic Annotation Workflow:**
1. Run `lsp(action="deadcode")`
2. Aurora generates CODE_QUALITY_REPORT.md
3. Aurora automatically annotates source files:
   ```python
   # aurora:dead-code HIGH - Line 42: unused_function
   def unused_function():  # Not used anywhere
       pass
   ```
4. Review report + inline annotations
5. Safely remove dead code

### impact Action

Analyze symbol usage and impact.

**Usage:**
```json
{
  "action": "impact",
  "path": "src/auth/login.py",
  "line": 42
}
```

**Returns:**
```json
{
  "action": "impact",
  "path": "src/auth/login.py",
  "line": 42,
  "symbol": "authenticate_user",
  "used_by_files": 5,
  "total_usages": 12,
  "top_callers": [
    {"file": "src/api/endpoints.py", "line": 25, "count": 4},
    {"file": "src/tests/test_auth.py", "line": 10, "count": 3}
  ],
  "risk": "medium"
}
```

**Risk Levels:**
- **low**: 0-2 usages (safe to modify/remove)
- **medium**: 3-10 usages (review carefully)
- **high**: 11+ usages (breaking change, needs migration plan)

### check Action

Quick usage check before editing.

**Usage:**
```json
{
  "action": "check",
  "path": "src/utils/helper.py",
  "line": 42
}
```

**Returns:**
```json
{
  "action": "check",
  "path": "src/utils/helper.py",
  "line": 42,
  "symbol": "helper_function",
  "used_by": 3,
  "risk": "low"
}
```

### imports Action

Find all files that import a given module. Uses ripgrep for speed (<1s).

**Usage:**
```json
{
  "action": "imports",
  "path": "src/utils/helper.py"
}
```

**Returns:**
```json
{
  "action": "imports",
  "path": "src/utils/helper.py",
  "imported_by": [
    "src/api/endpoints.py",
    "src/services/auth.py",
    "tests/test_helper.py"
  ],
  "total": 3
}
```

### related Action

Find what a symbol depends on (outgoing calls). Uses tree-sitter AST parsing (~50ms).

**Usage:**
```json
{
  "action": "related",
  "path": "src/auth/login.py",
  "line": 42
}
```

**Returns:**
```json
{
  "action": "related",
  "path": "src/auth/login.py",
  "line": 42,
  "calls": [
    {"name": "validate_credentials", "line": 45},
    {"name": "create_session", "line": 48},
    {"name": "log_login_attempt", "line": 50}
  ],
  "total_calls": 3
}
```

**Note:** Currently Python-only (requires tree-sitter-python).

## mem_search Tool

Hybrid search with LSP enrichment combining BM25, ACT-R activation, and semantic embeddings.

**Usage:**
```json
{
  "query": "authentication login",
  "limit": 5
}
```

**Returns:**
```json
[
  {
    "file": "src/auth/login.py",
    "type": "code",
    "symbol": "authenticate_user",
    "lines": "42-58",
    "score": 0.856,
    "used_by": "5 files (12 usages)",
    "called_by": [
      "login_endpoint (src/api/endpoints.py:25)"
    ],
    "calling": [
      "validate_credentials (src/auth/validators.py:10)",
      "create_session (src/auth/session.py:15)"
    ],
    "git": {
      "last_modified": "2024-01-15",
      "last_author": "john.doe@example.com"
    }
  }
]
```

**LSP Enrichment Fields:**
- **used_by**: Format "N files (M usages)" where N=unique files, M=total call sites
- **called_by**: List of functions that call this symbol
- **calling**: List of functions this symbol calls
- For non-code results (kb/docs), LSP fields show "-"

**Hybrid Scoring:**
- BM25: 40% (keyword matching)
- ACT-R: 30% (recency + frequency activation)
- Semantic: 30% (embedding similarity)

## When to Use

| Scenario | Tool | Action | Speed |
|----------|------|--------|-------|
| Before editing a symbol | `lsp` | `check` | ~1s |
| Before refactoring | `lsp` | `impact` | ~2s |
| Find unused code | `lsp` | `deadcode` | 2-20s |
| Who imports this module? | `lsp` | `imports` | <1s |
| What does this call? | `lsp` | `related` | ~50ms |
| Search codebase | `mem_search` | - | <1s |

## MCP Server

The Aurora MCP server runs via `aurora-mcp` command:

```bash
# Start MCP server (used by MCP clients)
aurora-mcp

# Or with custom paths
aurora-mcp --db-path ~/.aurora/memory.db --config-path ~/.aurora/config.json
```

## Language Support

LSP integration supports 10+ languages via [multilspy](https://github.com/microsoft/monitors4codegen/tree/main/multilspy):
- Python
- JavaScript/TypeScript
- Java
- C/C++
- C#
- Go
- Rust
- Ruby
- PHP
- And more...

## References

- [Code Intelligence Status](../lsp/CODE_INTELLIGENCE_STATUS.md) - All 16 features, language matrix, benchmarks
- [LSP Package](../lsp/LSP.md) - Architecture, accuracy metrics, API usage
- [Memory System](../memory/MEMORY.md) - Hybrid retrieval details
- [MCP Protocol](https://modelcontextprotocol.io/) - MCP specification
