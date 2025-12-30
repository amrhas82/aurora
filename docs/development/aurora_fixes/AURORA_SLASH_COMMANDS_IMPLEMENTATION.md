# Aurora Slash Commands Implementation Guide

> Step-by-step guide to implementing `/aur-*` slash commands for Claude Code.

## Overview

This document explains how to add slash commands like `/aur-query`, `/aur-search` to Aurora, following the beads pattern.

## How Slash Commands Work

Slash commands in Claude Code come from **two sources**:

### 1. MCP Server Tools

When you register an MCP tool, Claude Code automatically creates a slash command:

```python
# In your MCP server
@mcp.tool(name="query", description="Semantic search with reasoning")
async def query(question: str):
    ...
```

This becomes available as a tool that Claude can call. The plugin system (below) adds the `/` prefix.

### 2. Claude Code Plugin

The plugin registers your MCP server and can add slash command mappings:

```json
{
  "name": "aurora",
  "mcp": {
    "server": {
      "command": "python",
      "args": ["-m", "aurora.mcp.server"]
    }
  }
}
```

## Step 1: Create Plugin Structure

Create the plugin directory:

```bash
mkdir -p .claude-plugin/agents
```

### .claude-plugin/plugin.json

```json
{
  "name": "aurora",
  "description": "Semantic code memory and retrieval for AI coding agents",
  "version": "0.2.0",
  "author": {
    "name": "Aurora Team",
    "url": "https://github.com/your-org/aurora"
  },
  "repository": "https://github.com/your-org/aurora",
  "license": "MIT",
  "homepage": "https://github.com/your-org/aurora",
  "keywords": [
    "memory",
    "semantic-search",
    "code-retrieval",
    "agent-memory",
    "context-retrieval"
  ],
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "aur prime"
          }
        ]
      }
    ],
    "PreCompact": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "aur prime"
          }
        ]
      }
    ]
  }
}
```

### .claude-plugin/marketplace.json

```json
{
  "name": "aurora-marketplace",
  "description": "Local marketplace for aurora plugin development",
  "owner": {
    "name": "Aurora Team"
  },
  "plugins": [
    {
      "name": "aurora",
      "source": "./",
      "description": "Semantic code memory and retrieval",
      "version": "0.2.0"
    }
  ]
}
```

## Step 2: Update MCP Server with Slash-Command-Friendly Tools

The key is to design MCP tools that work well as slash commands. Here's the pattern:

### packages/mcp/src/aurora_mcp/server.py (additions)

```python
"""Aurora MCP Server with slash-command-friendly tools."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="Aurora",
    instructions="""
Aurora provides semantic code search and memory.

Quick commands:
- query: Ask questions about the codebase
- search: Find code by keyword
- index: Index current directory
- stats: Show memory statistics
- show: View chunk details

Use discover_tools() to see all available tools.
"""
)

# =============================================================================
# CONTEXT ENGINEERING: Minimal Models
# =============================================================================

class ChunkMinimal:
    """Minimal chunk representation for list views."""
    def __init__(self, chunk):
        self.id = chunk.id
        self.file_path = chunk.file_path
        self.symbol_name = getattr(chunk, 'symbol_name', None)
        self.relevance = getattr(chunk, 'relevance', 0.0)
        self.preview = chunk.content[:100] + "..." if len(chunk.content) > 100 else chunk.content

    def to_dict(self):
        return {
            "id": self.id,
            "file": self.file_path,
            "symbol": self.symbol_name,
            "relevance": round(self.relevance, 3),
            "preview": self.preview
        }


# =============================================================================
# TOOL DISCOVERY (Lazy Schema Loading)
# =============================================================================

TOOL_CATALOG = {
    "query": "Semantic search - ask questions about the codebase",
    "search": "Keyword search - find code containing specific text",
    "index": "Index directory - create/update the code index",
    "stats": "Statistics - show memory and index stats",
    "show": "Show chunk - view full content of a specific chunk",
    "context": "Context - set/show workspace context",
    "prime": "Prime - output workflow context for session start"
}

@mcp.tool(
    name="discover_tools",
    description="List available Aurora tools (names only). Use get_tool_info() for details."
)
async def discover_tools():
    """Discover available tools without loading full schemas."""
    return {
        "tools": TOOL_CATALOG,
        "count": len(TOOL_CATALOG),
        "hint": "Use get_tool_info('tool_name') for parameters and examples"
    }


@mcp.tool(
    name="get_tool_info",
    description="Get detailed information about a specific Aurora tool."
)
async def get_tool_info(tool_name: str):
    """Get full details for a specific tool."""
    tool_details = {
        "query": {
            "name": "query",
            "description": "Semantic search with AI reasoning over your codebase",
            "parameters": {
                "question": "str (required) - Natural language question",
                "limit": "int (default 5) - Max results to return",
                "brief": "bool (default True) - Return minimal format"
            },
            "example": 'query(question="how does authentication work")'
        },
        "search": {
            "name": "search",
            "description": "Keyword search in indexed code chunks",
            "parameters": {
                "text": "str (required) - Text to search for",
                "limit": "int (default 10) - Max results",
                "file_pattern": "str (optional) - Filter by file pattern (e.g., '*.py')"
            },
            "example": 'search(text="authenticate_user", file_pattern="*.py")'
        },
        "index": {
            "name": "index",
            "description": "Index a directory for semantic search",
            "parameters": {
                "path": "str (default '.') - Directory to index",
                "force": "bool (default False) - Force re-index"
            },
            "example": 'index(path="src/")'
        },
        "stats": {
            "name": "stats",
            "description": "Show index and memory statistics",
            "parameters": {},
            "example": "stats()"
        },
        "show": {
            "name": "show",
            "description": "Show full content of a specific chunk",
            "parameters": {
                "chunk_id": "str (required) - Chunk ID (e.g., 'aur-abc123')"
            },
            "example": 'show(chunk_id="aur-abc123")'
        },
        "context": {
            "name": "context",
            "description": "Manage workspace context",
            "parameters": {
                "action": "str (default 'show') - set, show, or init",
                "workspace": "str (optional) - Workspace path for 'set'"
            },
            "example": 'context(action="set", workspace="/path/to/project")'
        }
    }

    if tool_name not in tool_details:
        return {
            "error": f"Unknown tool: {tool_name}",
            "available": list(tool_details.keys())
        }

    return tool_details[tool_name]


# =============================================================================
# WORKSPACE CONTEXT (Persistent across calls)
# =============================================================================

_aurora_context = {
    "workspace": None,
    "index_path": None,
    "last_query": None
}

@mcp.tool(
    name="context",
    description="Manage Aurora workspace context. Actions: set, show."
)
async def context(
    action: str = "show",
    workspace: str = None
):
    """Set or show workspace context."""
    if action == "set" and workspace:
        import os
        resolved = os.path.abspath(workspace)
        _aurora_context["workspace"] = resolved

        # Find index
        index_path = os.path.join(resolved, ".aurora", "index.db")
        if os.path.exists(index_path):
            _aurora_context["index_path"] = index_path
        else:
            _aurora_context["index_path"] = None

        return f"Context set:\n  Workspace: {resolved}\n  Index: {_aurora_context['index_path'] or 'Not found'}"

    # Show current context
    return f"""Aurora Context:
  Workspace: {_aurora_context.get('workspace') or 'NOT SET'}
  Index: {_aurora_context.get('index_path') or 'NOT SET'}
  Last query: {_aurora_context.get('last_query') or 'None'}"""


# =============================================================================
# CORE TOOLS (Slash-command friendly)
# =============================================================================

COMPACTION_THRESHOLD = 20
PREVIEW_COUNT = 5

@mcp.tool(
    name="query",
    description="Semantic search - ask natural language questions about your codebase."
)
async def query(
    question: str,
    limit: int = 5,
    brief: bool = True
):
    """
    Semantic search with AI reasoning.

    Args:
        question: Natural language question about the code
        limit: Maximum results (1-20)
        brief: Return minimal format (default True for efficiency)
    """
    # TODO: Implement actual query logic
    # For now, placeholder structure

    _aurora_context["last_query"] = question

    # Placeholder results
    results = []  # Would come from actual semantic search

    if brief:
        return [ChunkMinimal(r).to_dict() for r in results]

    # Apply compaction if too many results
    if len(results) > COMPACTION_THRESHOLD:
        return {
            "compacted": True,
            "total_count": len(results),
            "preview": [ChunkMinimal(r).to_dict() for r in results[:PREVIEW_COUNT]],
            "hint": "Use show(chunk_id) for full content"
        }

    return results


@mcp.tool(
    name="search",
    description="Keyword search - find code containing specific text."
)
async def search(
    text: str,
    limit: int = 10,
    file_pattern: str = None,
    brief: bool = True
):
    """
    Keyword search in indexed chunks.

    Args:
        text: Text to search for
        limit: Maximum results
        file_pattern: Optional file filter (e.g., "*.py")
        brief: Return minimal format
    """
    # TODO: Implement actual search
    results = []

    if brief:
        return [ChunkMinimal(r).to_dict() for r in results]

    return results


@mcp.tool(
    name="index",
    description="Index a directory for semantic search."
)
async def index(
    path: str = ".",
    force: bool = False
):
    """
    Index directory for semantic search.

    Args:
        path: Directory to index (default: current)
        force: Force re-index even if up-to-date
    """
    import os

    resolved = os.path.abspath(path)

    # TODO: Implement actual indexing
    return {
        "status": "indexed",
        "path": resolved,
        "chunks": 0,  # Would be actual count
        "files": 0
    }


@mcp.tool(
    name="stats",
    description="Show index and memory statistics."
)
async def stats():
    """Show Aurora statistics."""
    # TODO: Get actual stats
    return {
        "workspace": _aurora_context.get("workspace"),
        "index": {
            "chunks": 0,
            "files": 0,
            "last_updated": None
        },
        "memory": {
            "cache_size": 0,
            "avg_relevance": 0.0
        }
    }


@mcp.tool(
    name="show",
    description="Show full content of a specific chunk."
)
async def show(chunk_id: str):
    """
    Show full chunk details.

    Args:
        chunk_id: The chunk ID (e.g., 'aur-abc123')
    """
    # TODO: Implement actual lookup
    return {
        "error": f"Chunk not found: {chunk_id}",
        "hint": "Use search() or query() to find chunks first"
    }


@mcp.tool(
    name="prime",
    description="Output workflow context for session start."
)
async def prime():
    """Output AI-optimized workflow context."""
    # Get stats
    stat_info = await stats()

    output = f"""# Aurora Memory Active

## Current State
- Workspace: {_aurora_context.get('workspace') or 'Not set (use context(action="set", workspace="..."))'}
- Chunks indexed: {stat_info['index']['chunks']}
- Files indexed: {stat_info['index']['files']}

## Quick Commands
- `query`: Ask questions about the codebase
- `search`: Find code by keyword
- `show`: View full chunk content
- `stats`: See index statistics

## Session Protocol
1. Set context if needed: context(action="set", workspace="/path")
2. Search: query("your question") or search("keyword")
3. Deep dive: show(chunk_id) for full content

Start: Use query() for semantic search or search() for keyword lookup.
"""
    return output


# =============================================================================
# SERVER ENTRY POINT
# =============================================================================

def main():
    """Run the Aurora MCP server."""
    import asyncio
    asyncio.run(mcp.run_async(transport="stdio"))


if __name__ == "__main__":
    main()
```

## Step 3: Create the Prime CLI Command

### packages/cli/src/aurora_cli/commands/prime.py

```python
"""Prime command - output AI-optimized workflow context."""

import click
from aurora_cli.utils import get_index_stats


@click.command()
@click.option('--full', is_flag=True, help='Force full output (ignore MCP detection)')
@click.option('--mcp', is_flag=True, help='Force MCP mode (minimal output)')
def prime(full: bool, mcp: bool):
    """Output AI-optimized workflow context.

    Designed for Claude Code hooks (SessionStart, PreCompact) to prevent
    agents from forgetting Aurora workflow after context compaction.
    """
    # Detect MCP mode
    is_mcp = detect_mcp_active() if not (full or mcp) else mcp

    if is_mcp:
        output_mcp_context()
    else:
        output_cli_context()


def detect_mcp_active() -> bool:
    """Detect if MCP server is configured in Claude settings."""
    import os
    import json
    from pathlib import Path

    home = Path.home()
    settings_path = home / ".claude" / "settings.json"

    if not settings_path.exists():
        return False

    try:
        settings = json.loads(settings_path.read_text())
        mcp_servers = settings.get("mcpServers", {})

        # Check for aurora in MCP servers
        for key in mcp_servers:
            if "aurora" in key.lower():
                return True

        return False
    except Exception:
        return False


def output_mcp_context():
    """Output minimal context for MCP mode (~50 tokens)."""
    print("""# Aurora Memory Active

## Quick Tools
- query: Semantic search ("how does X work")
- search: Keyword search
- show: View chunk details

Start: Use query() or search() to find code.""")


def output_cli_context():
    """Output full context for CLI mode (~500 tokens)."""
    stats = get_index_stats()

    print(f"""# Aurora Workflow Context

> Run `aur prime` after compaction or new session

## Current Index
- Chunks: {stats.get('chunks', 0):,}
- Files: {stats.get('files', 0)}
- Last indexed: {stats.get('last_indexed', 'Never')}

## Commands

### Finding Code
- `aur query "question"` - Semantic search with reasoning
- `aur mem search "text"` - Keyword search
- `aur show <chunk-id>` - View full chunk content

### Managing Index
- `aur mem index .` - Index current directory
- `aur --verify` - Check installation health

## Session Protocol
1. Check index: `aur --verify`
2. Search: `aur query "your question"`
3. Deep dive: `aur show <id>` for full content

## Tips
- Use `--non-interactive` for CI/automated usage
- Queries prompt for confirmation on low-quality results

Start: Use `aur query` for semantic search.""")


def get_index_stats() -> dict:
    """Get current index statistics."""
    # TODO: Implement actual stats gathering
    return {
        "chunks": 0,
        "files": 0,
        "last_indexed": "Never"
    }
```

### Register in CLI

Add to `packages/cli/src/aurora_cli/main.py`:

```python
from aurora_cli.commands.prime import prime

# In your click group
@click.group()
def cli():
    pass

cli.add_command(prime)
```

## Step 4: Create Skill for Claude

### skills/aurora/SKILL.md

```markdown
---
name: aurora
description: >
  Semantic code search and retrieval for coding agents. Use when the user asks
  questions about the codebase, needs to find implementations, or wants context
  before making changes. Triggers: "search for", "find code", "how does X work",
  "where is", "show me the code for".
allowed-tools: "Read,Bash(aur:*)"
version: "0.2.0"
author: "Aurora Team"
license: "MIT"
---

# Aurora - Semantic Code Memory

Semantic search over your codebase. Understands code meaning, not just text.

## When to Use Aurora

**Use Aurora when**:
- User asks "how does X work?"
- User says "find the code that handles Y"
- Need context before making changes
- Searching by meaning, not exact text

**Don't use Aurora when**:
- Looking for file by name (use Glob)
- Exact text search (use Grep)
- Simple questions without code context

## Prerequisites

- Aurora installed: `pip install aurora-actr[all]`
- Index exists: `aur mem index .` (humans run once)

## Instructions

### Finding Code

```bash
# Semantic search (best for questions)
aur query "how does user authentication work"

# Keyword search (best for specific terms)
aur mem search "authenticate_user"

# View full chunk
aur show aur-abc123
```

### Understanding Results

- **id**: Chunk identifier (use with `show`)
- **file**: Source file path
- **symbol**: Function/class name
- **relevance**: 0.0-1.0 (higher = better match)
- **preview**: First 100 characters

### Session Start

1. Run `aur prime` to see index status
2. Use `aur query` for questions
3. Use `aur show <id>` for full details

## Examples

### Example 1: Understanding a Feature

**User**: "How does the login flow work?"

```bash
aur query "login authentication flow"
# Returns relevant chunks

aur show aur-abc123  # Full details of top result
```

### Example 2: Finding Implementation

**User**: "Where do we handle rate limiting?"

```bash
aur mem search "rate limit"
```

## Error Handling

| Error | Solution |
|-------|----------|
| "No index found" | Run `aur mem index .` |
| "Low relevance" | Try different terms or use `aur mem search` |
| "Chunk not found" | ID may be stale; re-search |
```

## Step 5: Installation & Testing

### Install Plugin Locally

```bash
# In Claude Code
/plugin marketplace add ./path/to/aurora
/plugin install aurora

# Restart Claude Code
```

### Test Slash Commands

After installation, these should work:

```
# In Claude Code conversation
User: /aur-query "how does authentication work"
User: /aur-stats
User: /aur-search "authenticate"
```

### Verify Hooks

Check that `aur prime` runs at session start:

1. Start a new Claude Code session
2. You should see Aurora context injected automatically
3. Check with `/plugin list` to verify aurora is installed

## Summary

| Component | File | Purpose |
|-----------|------|---------|
| Plugin config | `.claude-plugin/plugin.json` | Register hooks, metadata |
| Marketplace | `.claude-plugin/marketplace.json` | Plugin discovery |
| MCP Server | `packages/mcp/src/aurora_mcp/server.py` | Tool implementations |
| Prime CLI | `packages/cli/src/aurora_cli/commands/prime.py` | Context injection |
| Skill | `skills/aurora/SKILL.md` | Teach Claude usage |

The slash commands come from the MCP tools registered in the server. The plugin connects Claude Code to the MCP server and adds the session hooks.
