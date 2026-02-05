#!/usr/bin/env python3
"""POC MCP Server for Aurora LSP Tools.

This is a proof-of-concept to test that Claude properly invokes the MCP tools.
Run with: uv run mcp dev packages/lsp/poc_mcp_server.py

Or add to Claude Code settings:
{
  "mcpServers": {
    "aurora-lsp-poc": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/aurora", "python", "packages/lsp/poc_mcp_server.py"]
    }
  }
}
"""

from typing import Literal

from mcp.server.fastmcp import FastMCP


# Create MCP server
mcp = FastMCP("aurora-lsp-poc")


# =============================================================================
# Tool 1: lsp - Code intelligence
# =============================================================================


@mcp.tool()
def lsp(
    action: Literal["deadcode", "impact", "check"] = "check",
    path: str = "",
    line: int | None = None,
) -> dict:
    """Code intelligence - dead code detection, impact analysis, pre-edit usage checks.

    Use this tool BEFORE modifying or deleting functions/classes to understand usage impact.

    Actions:
    - "deadcode": Scan for unused code in a file/directory. Returns list of symbols with 0 usages.
    - "impact": Full impact analysis for a symbol at path:line. Shows all callers and risk level.
    - "check": Quick pre-edit check. Returns usage count and risk level. Use before editing.

    Risk levels:
    - low (0-2 usages): Safe to change
    - medium (3-10 usages): Review callers before changing
    - high (11+ usages): Careful refactoring needed

    Args:
        action: "deadcode" | "impact" | "check" (default: check)
        path: File path (required). For deadcode, can be a directory.
        line: Line number (required for impact/check actions, 1-indexed)

    Returns:
        Action-specific JSON response
    """
    # POC: Return mock data to test invocation
    if action == "deadcode":
        return {
            "action": "deadcode",
            "path": path,
            "dead_code": [
                {"name": "ParseError", "file": "exceptions.py", "line": 45, "kind": "class"},
                {"name": "unused_helper", "file": "utils.py", "line": 120, "kind": "function"},
            ],
            "total": 2,
            "_poc": True,
            "_message": "POC: This is mock data. Real implementation would scan for unused symbols.",
        }

    elif action == "impact":
        return {
            "action": "impact",
            "path": path,
            "line": line,
            "symbol": f"symbol_at_line_{line}",
            "used_by_files": 12,
            "total_usages": 74,
            "top_callers": [
                {"file": "executor.py", "line": 45, "name": "run_task", "usages": 8},
                {"file": "runner.py", "line": 123, "name": "execute", "usages": 6},
                {"file": "manager.py", "line": 89, "name": "process", "usages": 5},
            ],
            "risk": "high",
            "_poc": True,
            "_message": "POC: This is mock data. Real implementation would use LSP references.",
        }

    elif action == "check":
        # Quick pre-edit check
        return {
            "action": "check",
            "path": path,
            "line": line,
            "symbol": f"symbol_at_line_{line}",
            "used_by": 7,
            "risk": "medium",
            "_poc": True,
            "_message": "POC: This is mock data. Real implementation would count LSP references.",
        }

    else:
        return {"error": f"Unknown action: {action}. Use: deadcode, impact, check"}


# =============================================================================
# Tool 2: mem_search - Search indexed code and knowledge base
# =============================================================================


@mcp.tool()
def mem_search(query: str, limit: int = 5) -> list[dict]:
    """Search indexed code and knowledge base with LSP context.

    Searches Aurora's memory (code chunks, knowledge base entries) and enriches
    results with LSP usage data for code symbols.

    Args:
        query: Search query string
        limit: Maximum results to return (default 5)

    Returns:
        List of search results with:
        - file: File path
        - type: "code" or "kb"
        - symbol: Symbol/section name
        - lines: Line range (e.g., "68-2447")
        - score: Relevance score (0-1)
        - used_by: LSP usage info for code (e.g., "12 files(74)"), "-" for non-code
        - git: Git info (commits, modified time)
    """
    # POC: Return mock search results
    results = [
        {
            "file": "orchestrator.py",
            "type": "code",
            "symbol": "SOAROrchestrator",
            "lines": "68-2447",
            "score": 0.564,
            "used_by": "12 files(74)",
            "git": "41 commits, 11h ago",
        },
        {
            "file": "sqlite.py",
            "type": "code",
            "symbol": "SQLiteStore",
            "lines": "38-1200",
            "score": 0.523,
            "used_by": "29 files(171)",
            "git": "23 commits, 2d ago",
        },
        {
            "file": "KNOWLEDGE_BASE.md",
            "type": "kb",
            "symbol": "Entry Points",
            "lines": "1-8",
            "score": 0.489,
            "used_by": "-",
            "git": "-",
        },
    ]

    return [{**r, "_poc": True, "_query": query} for r in results[:limit]]


# =============================================================================
# Run server
# =============================================================================

if __name__ == "__main__":
    print("Starting Aurora LSP POC MCP Server...")
    print("Tools available: lsp, mem_search")
    print()
    print("Test commands:")
    print("  lsp(action='check', path='src/main.py', line=42)")
    print("  lsp(action='impact', path='src/main.py', line=42)")
    print("  lsp(action='deadcode', path='src/')")
    print("  mem_search(query='SOAR orchestrator')")
    print()
    print("To get full content: use Read tool with file + lines from mem_search results")
    print()
    mcp.run()
