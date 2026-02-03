#!/usr/bin/env python3
"""Test POC MCP tools locally without running the server.

Run: python packages/lsp/test_poc_mcp.py
"""

import json
from poc_mcp_server import lsp, mem_search


def print_result(name: str, result):
    """Pretty print a result."""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print('='*60)
    print(json.dumps(result, indent=2))


def main():
    print("POC MCP Tools - Local Test")
    print("="*60)

    # Test lsp tool
    print_result(
        "lsp(action='check', path='src/main.py', line=42)",
        lsp(action="check", path="src/main.py", line=42)
    )

    print_result(
        "lsp(action='impact', path='src/main.py', line=42)",
        lsp(action="impact", path="src/main.py", line=42)
    )

    print_result(
        "lsp(action='deadcode', path='src/')",
        lsp(action="deadcode", path="src/")
    )

    # Test mem_search tool
    print_result(
        "mem_search(query='SOAR orchestrator', limit=3)",
        mem_search(query="SOAR orchestrator", limit=3)
    )

    print("\n" + "="*60)
    print("All POC tools working!")
    print("="*60)
    print("\nTo get full content: Claude uses Read tool with file + lines from mem_search")
    print("\nTo test with Claude Code, add to .mcp.json:")
    print("""
{
  "mcpServers": {
    "aurora-lsp-poc": {
      "command": "python",
      "args": ["/path/to/aurora/packages/lsp/poc_mcp_server.py"]
    }
  }
}
""")


if __name__ == "__main__":
    main()
