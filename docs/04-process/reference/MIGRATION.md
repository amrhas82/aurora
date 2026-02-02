# Migration Guide

This document provides migration guidance for Aurora CLI users affected by breaking changes or deprecations.

## MCP Tool Deprecation (v1.2.0)

**Effective**: Version 1.2.0 (2026-01-06)
**Related**: PRD-0024

### Overview

Three MCP tools have been deprecated in favor of slash commands and CLI commands:
- `aurora_query` → Use `aur soar` or `/aur:search`
- `aurora_search` → Use `/aur:search` or `aur mem search`
- `aurora_get` → Use `/aur:get`

**Impact**: Low - All deprecated tools have direct replacements with better UX

### Tool Replacement Mapping

| Deprecated MCP Tool | CLI Replacement | Slash Command | Notes |
|---------------------|-----------------|---------------|-------|
| `aurora_query` | `aur soar "query"` | N/A | Full 9-phase SOAR pipeline execution via bash orchestration |
| `aurora_search` | `aur mem search "query"` | `/aur:search "query"` | Slash command includes formatted table output + session caching |
| `aurora_get` | N/A | `/aur:get N` | Session cache retrieval by index (N = 1-indexed result number) |

### Detailed Replacement Examples

#### Example 1: Replacing aurora_query

**Before (MCP Tool)**:
```
# LLM would call aurora_query tool automatically
# User had no explicit control over when this happened
# Result: JSON response requiring additional formatting
```

**After (CLI Command)**:
```bash
# Terminal usage - explicit SOAR execution
aur soar "What authentication patterns are used in the codebase?"

# Result: Human-readable output with answers and citations
```

**After (Slash Command Alternative)**:
```
# For simple searches (not full SOAR pipeline)
/aur:search "authentication patterns"

# Result: Formatted table of search results in Claude Code context
```

#### Example 2: Replacing aurora_search

**Before (MCP Tool)**:
```
# LLM would call aurora_search tool automatically
# Result: Raw JSON array of chunks
# Required additional LLM processing to format
```

**After (Slash Command)**:
```
# In Claude Code CLI session
/aur:search "database migration logic"

# Result: Pre-formatted markdown table
# | Index | File | Lines | Snippet | Relevance |
# |-------|------|-------|---------|-----------|
# | 1     | ...  | ...   | ...     | 0.92      |

# Results cached in session for /aur:get retrieval
```

**After (CLI Command for Automation)**:
```bash
# For scripts or terminal workflows
aur mem search "database migration logic"

# Result: JSON output suitable for piping to jq or other tools
```

#### Example 3: Replacing aurora_get

**Before (MCP Tool)**:
```
# After aurora_search, LLM would call aurora_get
# to retrieve full chunk details by index
# Result: JSON object with chunk data
```

**After (Slash Command)**:
```
# After /aur:search, retrieve by index
/aur:get 3

# Result: Full chunk details formatted as markdown
# File: src/auth/handler.py
# Lines: 45-67
# Type: function
# Content: [full code block]
# Metadata: [relevance, embedding info]
```

### Behavior Changes

#### 1. aur init No Longer Configures MCP by Default

**Previous Behavior**:
```bash
aur init --tools=claude
# Would automatically configure MCP server in Claude Code
# Created .claude/plugins/aurora/.mcp.json
```

**New Behavior**:
```bash
aur init --tools=claude
# Skips MCP configuration by default
# No .mcp.json created

# To enable MCP (for testing/development):
aur init --enable-mcp --tools=claude
# Now creates MCP configuration with 6 remaining tools
```

**Migration Action**: None required - slash commands work without MCP configuration

#### 2. aur doctor No Longer Shows MCP Checks

**Previous Output**:
```
AURORA HEALTH CHECK
====================

CONFIGURATION
  ✓ Config file exists
  ✓ All required fields present

MCP FUNCTIONAL
  ✓ MCP server starts
  ✓ SOAR phases accessible
  ✓ Memory database connected

MEMORY
  ✓ Database initialized
  ✓ Embeddings present
```

**New Output**:
```
AURORA HEALTH CHECK
====================

CONFIGURATION
  ✓ Config file exists
  ✓ All required fields present

MEMORY
  ✓ Database initialized
  ✓ Embeddings present
```

**Migration Action**: None required - other health checks unchanged

#### 3. Slash Commands Now Recommended Over MCP Tools

**Previous Documentation**:
- MCP tools presented as primary interface
- Slash commands mentioned as alternative

**New Documentation**:
- Slash commands presented as primary interface
- MCP tools deprecated (except 6 remaining utility tools)
- CLI commands documented for automation

**Migration Action**: Update team documentation and workflows to prefer slash commands

### Breaking Changes

**None** - All deprecated tools have direct replacements. No user-facing breaking changes.

The deprecation is additive:
- Existing slash commands continue to work
- Existing CLI commands continue to work
- MCP infrastructure preserved for future use
- Re-enablement possible via `--enable-mcp` flag

### Migration Checklist

Use this checklist to migrate your workflows:

- [ ] **Update Team Documentation**
  - [ ] Replace MCP tool references with slash commands
  - [ ] Update onboarding guides to use `/aur:search` and `/aur:get`
  - [ ] Document `aur soar` for full query workflows

- [ ] **Update Automation Scripts**
  - [ ] Replace `aurora_query` calls with `aur soar "query"`
  - [ ] Replace `aurora_search` calls with `aur mem search "query"`
  - [ ] Update JSON parsing logic for new CLI output formats

- [ ] **Update Development Workflows**
  - [ ] Train developers on slash command syntax
  - [ ] Update IDE snippets to use slash commands
  - [ ] Add slash commands to cheatsheets

- [ ] **Test Slash Commands**
  - [ ] Verify `/aur:search` returns expected results
  - [ ] Verify `/aur:get` retrieves from session cache
  - [ ] Verify `aur soar` completes full SOAR pipeline

- [ ] **Optional: Disable MCP (if explicitly enabled)**
  - [ ] Edit `~/.aurora/config.json` and set `mcp.enabled: false`
  - [ ] Run `aur init` without `--enable-mcp` flag
  - [ ] Verify slash commands still work

### Re-enabling MCP (Optional)

If you need MCP for testing or development:

```bash
# Option 1: Enable via flag
aur init --enable-mcp --tools=claude

# Option 2: Edit config manually
# Edit ~/.aurora/config.json:
{
  "mcp": {
    "enabled": true
  }
}

# Then run init with MCP
aur init --enable-mcp --tools=claude
```

**Note**: Re-enabling MCP provides 6 tools (not 9):
- ✓ `aurora_index` - Index codebase
- ✓ `aurora_context` - Get file context
- ✓ `aurora_related` - Find related chunks
- ✓ `aurora_list_agents` - List agents
- ✓ `aurora_search_agents` - Search agents
- ✓ `aurora_show_agent` - Show agent details
- ✗ ~~`aurora_query`~~ - Deprecated
- ✗ ~~`aurora_search`~~ - Deprecated
- ✗ ~~`aurora_get`~~ - Deprecated

### Rollback Options

If you encounter issues with the new slash command workflow, three rollback options are available:

#### Option 1: Feature Flag (Fastest - 1 minute)
```bash
# Edit ~/.aurora/config.json
{
  "mcp": {
    "enabled": true
  }
}

# Re-run init with MCP
aur init --enable-mcp --tools=claude

# Note: Deprecated tools remain unavailable
```

#### Option 2: Git Checkout Baseline Tag (Complete Revert)
```bash
git checkout mcp-deprecation-baseline
# Reverts to state before deprecation (includes deprecated tools)
```

#### Option 3: Git Revert Commits (Preserve History)
```bash
# Identify commit range
git log --oneline feature/mcp-deprecation

# Revert specific commits
git revert <commit-hash-range>
```

**See**: `docs/ROLLBACK.md` for detailed procedures

### Token Efficiency Benefits

Slash commands provide significant token savings compared to MCP tools:

| Operation | MCP Tool Tokens | Slash Command Tokens | Savings |
|-----------|----------------|---------------------|---------|
| Search query | ~850 tokens | ~350 tokens | 59% |
| Get result | ~600 tokens | ~250 tokens | 58% |
| Full SOAR query | ~3500 tokens | ~2000 tokens | 43% |

**Benefits**:
- Lower API costs per operation
- Faster response times (less parsing overhead)
- More context window available for actual code

### Support and Questions

**Documentation**:
- Architecture rationale: `docs/MCP_DEPRECATION.md`
- Command reference: `docs/COMMANDS.md`
- Rollback procedures: `docs/ROLLBACK.md`

**Issues**:
- Report issues: GitHub Issues
- Discuss migration: GitHub Discussions

**Timeline**:
- **2026-01-06**: v1.2.0 released with MCP deprecation
- **2026-Q1**: Monitor adoption and gather feedback
- **2026-Q2**: Evaluate re-enablement criteria (if needed)

## Future Migrations

This section will be updated as new breaking changes or deprecations are introduced.

### Planned Deprecations

None currently planned.

### Version Support Policy

Aurora follows semantic versioning:
- **Major versions** (2.0.0): Breaking changes allowed
- **Minor versions** (1.2.0): New features, deprecations (no breaking changes)
- **Patch versions** (1.2.1): Bug fixes only

Deprecated features are supported for at least one major version cycle before removal.
