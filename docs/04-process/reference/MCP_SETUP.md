# MCP Setup Guide - Claude Code CLI

This guide explains how to integrate AURORA's MCP (Model Context Protocol) server with Claude Code CLI, enabling you to search, index, and query your codebase directly from your development sessions.

## Table of Contents

- [Introduction](#introduction)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Available Tools](#available-tools)
- [Troubleshooting](#troubleshooting)
- [Advanced Configuration](#advanced-configuration)
- [FAQ](#faq)

---

## Introduction

AURORA's MCP server provides Claude Code CLI with seven powerful tools for code navigation and intelligent querying:

1. **aurora_search**: Semantic search over your indexed codebase
2. **aurora_index**: Index new files or directories
3. **aurora_stats**: View statistics about your indexed codebase
4. **aurora_context**: Retrieve file or function content
5. **aurora_related**: Find related code chunks through dependency relationships
6. **aurora_query**: Execute queries with auto-escalation (direct LLM or SOAR pipeline)
7. **aurora_get**: Retrieve full chunk by index from last search results

**Benefits:**
- Natural language code search directly in your terminal
- Intelligent query processing with automatic complexity assessment
- Contextual code understanding during development
- No manual file copying or context switching
- Memory persistence across Claude Code CLI sessions

### Available Tools

| Tool/Command | Description |
|--------------|-------------|
| **MCP Tools (Inside Claude Code CLI)** |
| `aurora_search` | Uses local index for semantic search |
| `aurora_index` | Local file parsing and storage |
| `aurora_stats` | Reads local database statistics |
| `aurora_context` | Retrieves local file content |
| `aurora_related` | Uses local ACT-R activation |
| `aurora_get` | Retrieves from session cache |
| `aurora_query` | Returns context for Claude Code CLI processing |
| **Standalone CLI Commands** |
| `aur mem index` | Local indexing only |
| `aur mem search` | Local search only |
| `aur mem stats` | Local statistics only |
| `aur goals` | Goal decomposition and agent matching |
| `aur spawn` | Parallel task execution |

---

## Prerequisites

Before setting up MCP integration, ensure you have:

1. **Python 3.10 or higher**
   ```bash
   python3 --version
   ```

2. **AURORA installed**
   ```bash
   pip install aurora-actr[all]
   # Or for development:
   pip install -e .
   ```

3. **Claude Code CLI installed**
   - Verify: `claude-code --version`
   - Installation: See [Claude Code documentation](https://claude.ai/claude-code)

4. **Indexed codebase**
   ```bash
   # Index your project
   cd /path/to/your/project
   aur mem index .

   # Verify indexing worked
   aur mem stats
   ```

---

## Installation

AURORA's MCP server is automatically installed with the `aurora` package. No additional installation is required.

Verify the MCP server is available:

```bash
# Test the MCP server
python3 -m aurora.mcp.server --test
```

Expected output:
```
AURORA MCP Server - Test Mode
Database: /home/user/.aurora/memory.db
Available tools: 7
- aurora_search
- aurora_index
- aurora_stats
- aurora_context
- aurora_related
- aurora_query
- aurora_get
```

---

## Configuration

Configure Claude Code CLI to use AURORA's MCP server in two steps:

### Step 1: Create MCP Server Configuration

Create the plugin directory and configuration file:

```bash
mkdir -p ~/.claude/plugins/aurora
```

Create `~/.claude/plugins/aurora/.mcp.json`:

```json
{
  "aurora": {
    "command": "python3",
    "args": ["-m", "aurora.mcp.server"],
    "env": {
      "AURORA_DB_PATH": "${HOME}/.aurora/memory.db"
    }
  }
}
```

**Environment Variables:**
- `AURORA_DB_PATH`: Path to your AURORA database (default: `~/.aurora/memory.db`)

### Step 2: Add Tool Permissions

Edit `~/.claude/settings.local.json` to grant permissions for AURORA tools:

```json
{
  "permissions": {
    "allow": [
      "// === MCP Tools ===",
      "mcp__aurora__aurora_query",
      "mcp__aurora__aurora_search",
      "mcp__aurora__aurora_index",
      "mcp__aurora__aurora_stats",
      "mcp__aurora__aurora_context",
      "mcp__aurora__aurora_related",
      "mcp__aurora__aurora_get"
    ]
  }
}
```

**Note:** If `settings.local.json` doesn't exist, create it with the structure above.

### Step 3: Restart Claude Code CLI

Restart your Claude Code CLI session for changes to take effect.

---

## Usage Examples

Once configured, AURORA's tools are automatically available in Claude Code CLI sessions. You don't call them directly - Claude Code CLI uses them as needed.

### Example Session

```
User: "Search my codebase for authentication logic"
Claude: [Uses aurora_search tool]
Found 12 matches for authentication in your codebase:
1. auth/login.py:45 - login_user() function
2. auth/middleware.py:89 - verify_token() function
...

User: "What does the UserService class do?"
Claude: [Uses aurora_context tool]
The UserService class in services/user.py handles user management...

User: "Compare our API patterns with REST best practices"
Claude: [Uses aurora_query tool with SOAR pipeline]
Analyzing your API implementation...
[Provides comprehensive analysis with code examples]
```

### Tool Selection (Automatic)

Claude Code CLI automatically selects the appropriate tool based on your request:

| Request Type | Tool Used | Example |
|--------------|-----------|---------|
| Code search | `aurora_search` | "Find all database queries" |
| View file/function | `aurora_context` | "Show me the login function" |
| Find dependencies | `aurora_related` | "What calls this function?" |
| Index new code | `aurora_index` | "Index the new api/ directory" |
| Database stats | `aurora_stats` | "How many files are indexed?" |
| Complex analysis | `aurora_query` | "Explain our authentication flow" |

---

## Available Tools

### 1. aurora_search

Search your indexed codebase using semantic or keyword-based search.

**When Claude Uses It:**
- "Find code that handles authentication"
- "Search for database connection logic"
- "Show me all error handling"

**Returns:** List of relevant code chunks with file paths and snippets

---

### 2. aurora_index

Index new files or directories into AURORA's database.

**When Claude Uses It:**
- "Index the new api/ directory"
- "Add tests/ to the codebase index"

**Returns:** Indexing statistics (files processed, chunks created)

---

### 3. aurora_stats

View statistics about your indexed codebase.

**When Claude Uses It:**
- "How many files are indexed?"
- "Show codebase statistics"

**Returns:** Chunk count, file count, database size

---

### 4. aurora_context

Retrieve content from a specific file or function.

**When Claude Uses It:**
- "Show me the login function"
- "What's in auth/middleware.py?"

**Returns:** Full source code with syntax highlighting

---

### 5. aurora_related

Find related code chunks through ACT-R spreading activation.

**When Claude Uses It:**
- "What calls this function?"
- "Find related authentication code"

**Returns:** Related chunks ranked by activation strength

---

### 6. aurora_query

Execute intelligent queries without LLM inference - returns structured context for Claude Code CLI to process.

**When Claude Uses It:**
- "Explain our authentication architecture"
- "Compare our API design with best practices"
- "How does the payment system work?"

**Features:**
- Returns structured context (chunks, scores, metadata) WITHOUT running LLM
- Complexity assessment helps Claude decide how to process the context
- No API key required (Claude Code CLI's LLM processes the returned context)
- Graceful degradation when memory unavailable

**Important:** This tool does NOT perform LLM inference. It retrieves relevant context from AURORA's memory and returns it to Claude Code CLI, which then uses its own LLM to answer your question.

**Returns:** Structured JSON with:
- `context`: Retrieved chunks with relevance scores
- `assessment`: Complexity score and suggested approach
- `metadata`: Query info, retrieval time, index statistics

---

### 7. aurora_get

Retrieve a full chunk by index from last search results.

**When Claude Uses It:**
- "Get result #3 from the last search"
- "Show me the full content of the second result"
- "Retrieve chunk number 5"

**Workflow:**
1. Run `aurora_search` or `aurora_query` to get numbered results
2. Review the list and choose which result you want
3. Call `aurora_get(N)` to retrieve the full chunk for result N

**Features:**
- 1-indexed system (first result is 1, not 0)
- Session-based caching (10-minute expiry)
- Full chunk content with all metadata
- No API key required

**Returns:** Complete chunk with metadata including:
- Full chunk content
- File path and line range
- Index position and total results
- Cache age

---

## Troubleshooting

### Issue: MCP Server Not Found

**Symptoms:**
- Claude Code CLI shows "unknown tool" errors
- AURORA tools don't appear in tool list

**Solution:**
1. Verify configuration file exists:
   ```bash
   cat ~/.claude/plugins/aurora/.mcp.json
   ```

2. Check file permissions:
   ```bash
   chmod 644 ~/.claude/plugins/aurora/.mcp.json
   ```

3. Restart Claude Code CLI completely (exit and relaunch)

---

### Issue: Search Returns No Results

**Symptoms:**
- `aurora_search` finds nothing
- `aurora_stats` shows 0 chunks

**Solution:**
Index your codebase first:

```bash
cd /path/to/your/project
aur mem index .
aur mem stats  # Verify chunks were created
```

---

### Issue: Slow MCP Server Startup

**Symptoms:**
- First query in a session takes 3-5 seconds
- Subsequent queries are fast

**Root Cause:**
- Cold start: Loading sentence-transformers model (~500MB)
- Tree-sitter grammar initialization

**Solution (Acceptable):**
This is expected behavior. Warm queries are <100ms.

**Solution (Optimization):**
Use keyword-only search (no semantic embeddings):

```bash
# Skip ML dependencies for faster startup
pip install aurora-actr  # Without [all]
```

---

### Issue: Permission Denied Errors

**Symptoms:**
```
Error: Permission denied writing to /home/user/.aurora/memory.db
```

**Solution:**
Check file permissions:

```bash
ls -la ~/.aurora/
chmod 644 ~/.aurora/memory.db
```

---

## Advanced Configuration

### Configuration Priority

AURORA uses a 3-tier configuration system:

1. **Environment Variables** (highest priority)
   - `AURORA_DB_PATH` - Database location
   - `AURORA_CONFIG_PATH` - Config file location

2. **Config File** (`~/.aurora/config.json`)
   ```json
   {
     "query": {
       "auto_escalate": true,
       "complexity_threshold": 0.6,
       "verbosity": "verbose"
     },
     "budget": {
       "monthly_limit_usd": 50.0
     }
   }
   ```

3. **Hard-coded Defaults** (lowest priority)

### Debugging Configuration

Check effective configuration:
```bash
aur --verify
```

Validate MCP server:
```bash
python3 -m aurora.mcp.server --test --db-path ~/.aurora/memory.db
```

---

### Multiple Database Support

Use different databases for different projects:

```json
{
  "aurora": {
    "command": "python3",
    "args": ["-m", "aurora.mcp.server"],
    "env": {
      "AURORA_DB_PATH": "/path/to/project-specific/memory.db"
    }
  }
}
```

---

### Budget Management

Control API costs with budget limits:

```json
// ~/.aurora/config.json
{
  "budget": {
    "monthly_limit_usd": 50.0
  }
}
```

Track spending:
```bash
cat ~/.aurora/budget_tracker.json
```

---

## FAQ

### Q: Can I use AURORA with other MCP clients?

**A:** Yes! AURORA's MCP server implements the standard MCP protocol. It works with:
- Claude Code CLI (primary)
- Any MCP-compatible client
- Custom integrations via MCP SDK

---

### Q: Does aurora_query cost money?

**A:** No. MCP tools do NOT make LLM API calls. The `aurora_query` tool returns context without running any LLM. Claude Code CLI's built-in LLM processes the context using your existing Claude subscription.

---

### Q: Can I disable auto-escalation?

**A:** Yes. Set `auto_escalate: false` in config:

```json
{
  "query": {
    "auto_escalate": false
  }
}
```

This forces all queries to use SOAR pipeline (slower but more thorough).

---

### Q: Do MCP tools use retrieval quality handling?

**A:** No. MCP tools are non-interactive and do NOT use retrieval quality handling. They always return results regardless of quality (no filtering or prompts).

**Retrieval Quality Handling (CLI Only)**:
- The AURORA CLI (`aur query`) includes a 3-tier retrieval quality system that can interactively prompt users when retrieval fails or returns weak matches
- This feature is **CLI-only** and does NOT affect MCP tools

**Why MCP tools are exempt**:
- MCP tools are designed to be non-interactive (no user prompts possible in MCP context)
- MCP tools use `HybridRetriever` directly (not SOAR pipeline with quality checks)
- Claude Code CLI handles quality assessment at a higher level

**For quality-aware queries in Claude Code CLI**:
- MCP tools: Always return raw results (no quality filtering)
- CLI `aur query`: Can prompt user for weak matches (interactive mode only)

**Summary**:
- **MCP Tools** (`aurora_search`, `aurora_index`, `aurora_stats`, `aurora_context`, `aurora_related`, `aurora_query`): No retrieval quality handling, always return results
- **CLI** (`aur query --interactive`): Optional retrieval quality prompts for weak matches
- **CLI** (`aur query --non-interactive`): No prompts, auto-continues

---

### Q: How do I update the indexed codebase?

**A:** Re-index anytime:

```bash
cd /path/to/project
aur mem index .  # Overwrites previous index
```

Or use incremental updates:
```bash
aur mem index src/  # Index only src/ directory
```

---

### Q: What languages are supported?

**A:** Currently:
- **Python**: Full support with tree-sitter parsing
- **Other languages**: Coming soon (TypeScript, JavaScript, Go, Rust)

Generic text-based indexing works for all languages.

---

### Q: Can I use aurora_query in standalone CLI?

**A:** Yes:

```bash
aur query "Explain the authentication system"
```

This bypasses MCP and runs AURORA directly from the command line.

---

## Getting Help

If you encounter issues not covered in this guide:

1. **Check logs:**
   ```bash
   cat ~/.aurora/logs/mcp.log
   ```

2. **Validate installation:**
   ```bash
   aur --verify
   ```

3. **Run diagnostics:**
   ```bash
   python3 -m aurora.mcp.server --test
   ```

4. **Report issues:**
   - GitHub: https://github.com/aurora-project/aurora/issues
   - Include: OS, Python version, error message, config files

---

**End of MCP Setup Guide**
