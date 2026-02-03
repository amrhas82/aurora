# Migration Guide

This document provides migration guidance for Aurora CLI users affected by breaking changes or deprecations.

## MCP Tool Migration (v1.3.0)

**Effective**: Version 1.3.0 (2026-02)

### Overview

Aurora now provides two MCP tools for code intelligence:
- `lsp` - Dead code detection, impact analysis, pre-edit checks
- `mem_search` - Search indexed code with LSP enrichment

Old MCP tools (`aurora_query`, `aurora_search`, `aurora_get`) and slash commands (`/aur:search`, `/aur:get`) have been removed.

### Current Interface

| Task | CLI Command | MCP Tool |
|------|-------------|----------|
| Search code | `aur mem search "query"` | `mem_search` |
| SOAR research | `aur soar "question"` | N/A |
| Dead code detection | N/A | `lsp action=deadcode` |
| Impact analysis | N/A | `lsp action=impact` |
| Pre-edit check | N/A | `lsp action=check` |

### Migration Examples

#### Searching Code

**CLI (Terminal)**:
```bash
# Basic search
aur mem search "authentication"

# With content preview
aur mem search "authentication" --show-content

# With detailed scores
aur mem search "authentication" --show-scores
```

**MCP Tool (Claude)**:
```
# Claude can call mem_search automatically
# Results include LSP enrichment (usage counts, callers)
```

#### Code Intelligence (New)

**Before refactoring** - Check symbol usage:
```
# MCP tool: lsp action=check path=src/auth.py line=45
# Returns: usage count and risk level
```

**Finding dead code**:
```
# MCP tool: lsp action=deadcode path=src/
# Returns: list of unused symbols
```

**Impact analysis**:
```
# MCP tool: lsp action=impact path=src/auth.py line=45
# Returns: all callers and risk assessment
```

### Removed Commands

The following have been removed:
- `/aur:search` - Use `aur mem search` or `mem_search` MCP tool
- `/aur:get` - No longer needed, search results include full context
- `aurora_query` MCP tool - Use `aur soar` CLI
- `aurora_search` MCP tool - Use `mem_search` MCP tool
- `aurora_get` MCP tool - Use `mem_search` MCP tool

### Best Practices

1. **For terminal workflows**: Use `aur mem search` CLI
2. **For Claude interactions**: Let Claude use `mem_search` and `lsp` MCP tools
3. **Before editing code**: Use `lsp check` to understand impact
4. **Before refactoring**: Use `lsp deadcode` to find unused code

---

## See Also

- [MCP.md](../../02-features/mcp/MCP.md) - Full MCP tool documentation
- [MCP_SETUP.md](MCP_SETUP.md) - MCP server setup guide
- [COMMANDS.md](../../02-features/COMMANDS.md) - Full CLI reference
