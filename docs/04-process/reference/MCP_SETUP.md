# MCP Setup Guide

Configure Aurora's MCP server with Claude Code or other MCP clients.

## Quick Start

```bash
# 1. Index your codebase
cd /path/to/project
aur init

# 2. Start MCP server (usually automatic via client config)
aurora-mcp
```

## Claude Code Configuration

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "aurora": {
      "command": "aurora-mcp",
      "args": []
    }
  }
}
```

Or with custom database path:

```json
{
  "mcpServers": {
    "aurora": {
      "command": "aurora-mcp",
      "args": ["--db-path", "/path/to/project/.aurora/memory.db"]
    }
  }
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `lsp` | Code intelligence (deadcode, impact, check) |
| `mem_search` | Search indexed code with LSP enrichment |

## Tool Permissions

Add to `~/.claude/settings.local.json`:

```json
{
  "permissions": {
    "allow": [
      "mcp__aurora__lsp",
      "mcp__aurora__mem_search"
    ]
  }
}
```

## Verification

```bash
# Test MCP server
aurora-mcp --test

# Expected output:
# AURORA MCP Server - Test Mode
# Available tools: 2
# - lsp
# - mem_search
```

## Troubleshooting

### MCP Server Not Found

```bash
# Check aurora-mcp is available
which aurora-mcp

# Reinstall if needed
pip install -e .
```

### No Search Results

```bash
# Ensure codebase is indexed
aur init
aur mem stats
```

### Slow First Query

First query loads the embedding model (~500MB). Subsequent queries are fast (<100ms).

## See Also

- [MCP.md](../../02-features/mcp/MCP.md) - Full tool documentation
- [Claude Code MCP Docs](https://docs.anthropic.com/en/docs/claude-code)
