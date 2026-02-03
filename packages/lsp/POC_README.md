# Aurora LSP MCP POC

Proof-of-concept MCP server to test Claude invocation of Aurora LSP tools.

## Quick Test (Local)

```bash
cd /home/hamr/PycharmProjects/aurora
python packages/lsp/test_poc_mcp.py
```

## Test with Claude Code

Add to `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "aurora-lsp-poc": {
      "command": "python",
      "args": ["/home/hamr/PycharmProjects/aurora/packages/lsp/poc_mcp_server.py"]
    }
  }
}
```

Then restart Claude Code. Tools will appear as:
- `mcp__aurora-lsp-poc__lsp`
- `mcp__aurora-lsp-poc__mem_search`

## Tools

### `lsp` - Code Intelligence

Use BEFORE modifying/deleting code to understand impact.

| Action | Purpose | Required Params |
|--------|---------|-----------------|
| `check` | Quick pre-edit check | path, line |
| `impact` | Full impact analysis | path, line |
| `deadcode` | Find unused code | path |

**Test prompts:**
- "Check usage of line 42 in src/main.py before I delete it"
- "Find dead code in packages/core/"
- "Show impact of changing SQLiteStore"

### `mem_search` - Search Code Memory

Search indexed code and knowledge base with LSP enrichment.

**Test prompts:**
- "Search for SOAR orchestrator"
- "Find code related to memory storage"

**To get full content:** Claude uses `Read` tool with file + lines from search results.

## What POC Returns

All responses include `"_poc": true` - mock data:

```json
{
  "action": "check",
  "symbol": "symbol_at_line_42",
  "used_by": 7,
  "risk": "medium",
  "_poc": true
}
```

## Files

```
packages/lsp/
├── poc_mcp_server.py   # MCP server (lsp, mem_search)
├── test_poc_mcp.py     # Local test
└── POC_README.md       # This file
```

## Next Steps

Wire POC to real implementations:
- `lsp` → `AuroraLSP` facade
- `mem_search` → `memory_store.search()` + LSP enrichment
