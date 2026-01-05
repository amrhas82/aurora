# Aurora Commands Reference

Complete reference for all Aurora CLI commands, MCP tools, and slash commands.

**Version:** 0.4.0

---

## Table of Contents

1. [Quick Reference Table](#quick-reference-table)
2. [CLI Commands](#cli-commands)
3. [MCP Tools](#mcp-tools)
4. [Slash Commands](#slash-commands)
5. [Command Comparison](#command-comparison)

---

## Quick Reference Table

### CLI Commands (8 commands)

| Command | Purpose | When To Use | Syntax | Example |
|---------|---------|-------------|--------|---------|
| `aur init` | Initialize Aurora | First-time setup, reconfigure tools | `aur init [OPTIONS]` | `aur init --tools=claude,cursor` |
| `aur doctor` | Health checks & diagnostics | Troubleshooting, verify setup | `aur doctor [OPTIONS]` | `aur doctor --verbose` |
| `aur mem index` | Index code for search | After code changes | `aur mem index [PATH]` | `aur mem index packages/` |
| `aur mem search` | Search indexed code | Find code by query | `aur mem search <QUERY>` | `aur mem search "auth logic"` |
| `aur mem stats` | Memory statistics | Check indexing status | `aur mem stats` | `aur mem stats` |
| `aur agents` | Agent discovery | Find/list agents | `aur agents <SUBCOMMAND>` | `aur agents search "test"` |
| `aur plan` | Planning workflows | Create/manage plans | `aur plan <SUBCOMMAND>` | `aur plan create "Feature"` |
| `aur headless` | Pipe to CLI tool | Multi-iteration experiments | `aur headless <FILE>` | `aur headless prompt.md --tool claude` |

### MCP Tools (9 tools)

| Tool | Purpose | When To Use | Syntax |
|------|---------|-------------|--------|
| `aurora_search` | Search code semantically | Claude needs to find code | `aurora_search(query, limit=10)` |
| `aurora_index` | Index code directory | Claude needs to index new code | `aurora_index(path, recursive=True)` |
| `aurora_context` | Get code context | Claude needs specific file/function | `aurora_context(file_path, symbol=None)` |
| `aurora_related` | Find related code | Claude needs to discover connections | `aurora_related(chunk_id, max_hops=2)` |
| `aurora_query` | Query with complexity assessment | Claude needs context retrieval | `aurora_query(query, limit=10)` |
| `aurora_get` | Get full chunk by index | After search, get complete content | `aurora_get(index)` |
| `aurora_list_agents` | List all agents | Claude needs agent inventory | `aurora_list_agents()` |
| `aurora_search_agents` | Search agents by keyword | Claude needs to find matching agents | `aurora_search_agents(query)` |
| `aurora_show_agent` | Show full agent details | Claude needs agent instructions | `aurora_show_agent(agent_id)` |

### Slash Commands (2 commands)

| Command | Purpose | When To Use | Syntax |
|---------|---------|-------------|--------|
| `/aur:plan` | Planning workflows | Multi-step plan orchestration | `/aur:plan [create\|list\|show]` |
| `/aur:checkpoint` | Save session context | Before context compaction | `/aur:checkpoint` |

---

## CLI Commands

Use these commands directly in your terminal with the `aur` command.

### Initialization & Setup

#### `aur init`
**Initialize Aurora in your project**

Runs 3 unified setup steps:
1. **Planning setup** - Creates `.aurora/` directory structure
2. **Memory indexing** - Indexes codebase for semantic search
3. **Tool configuration** - Sets up MCP servers and slash commands

```bash
# Interactive mode (default)
aur init

# Non-interactive mode (uses defaults)
aur init --non-interactive

# Configure tools only
aur init --config

# Select specific tools
aur init --tools=claude,cursor

# Select all tools
aur init --tools=all

# Skip tool configuration
aur init --tools=none
```

**When to use:** First time setup in a new project, or to reconfigure tools.

---

### Memory Management

#### `aur mem index`
**Index codebase for semantic search**

```bash
# Index current directory
aur mem index

# Index specific directory
aur mem index /path/to/project

# With progress updates
aur mem index --verbose
```

**When to use:** After initial setup, or when codebase changes significantly.

---

#### `aur mem search`
**Search indexed code**

```bash
# Basic search
aur mem search "authentication"

# Limit results
aur mem search "database" --limit 10

# Show code content
aur mem search "api" --show-content

# JSON output
aur mem search "class UserService" --format json

# Filter by type
aur mem search "validate" --type function
```

**When to use:** Quick code search without LLM, finding specific functions/classes.

---

#### `aur mem stats`
**Show memory statistics**

```bash
aur mem stats
```

Shows:
- Total chunks indexed
- File count and language breakdown
- Last indexed timestamp
- Success rate
- Failed files (if any)
- Warnings (if any)

**When to use:** Check indexing status, diagnose indexing issues.

---

### Planning Commands

#### `aur plan create`
**Create a new plan**

```bash
# Interactive creation
aur plan create "Add user authentication"

# Non-interactive
aur plan create "Feature XYZ" --non-interactive
```

**When to use:** Starting a new feature, tracking implementation tasks.

---

#### `aur plan list`
**List all plans**

```bash
# List all plans
aur plan list

# Show active plans only
aur plan list --status active
```

**When to use:** Review existing plans, check plan status.

---

#### `aur plan show`
**Show plan details**

```bash
aur plan show 0001-add-auth
```

**When to use:** View specific plan content and tasks.

---

### Agent Discovery

#### `aur agents list`
**List available AI agents**

```bash
# List all agents
aur agents list

# JSON output
aur agents list --format json
```

**When to use:** Discover available agents, check agent capabilities.

---

#### `aur agents scan`
**Scan for new agents**

```bash
aur agents scan
```

**When to use:** After adding new agents, updating agent manifest.

---

### Health & Diagnostics

#### `aur doctor`
**Run health checks**

```bash
aur doctor
```

Shows:
- **Configuration:** Database, plans directory, budget tracker
- **Memory System:** Indexing status, chunk count
- **Code Analysis:** Tree-sitter languages, parsers
- **Tool Integration:** CLI tools, slash commands, MCP servers

**When to use:** Diagnose setup issues, verify configuration.

---

#### `aur --version`
**Show version**

```bash
aur --version
```

**When to use:** Check installed version, verify installation.

---

### Query & Reasoning

#### `aur query`
**Query with LLM reasoning**

**⚠️ Requires:** `ANTHROPIC_API_KEY` environment variable

```bash
# Simple query
aur query "What is a Python decorator?"

# Complex query with context
aur query "How does authentication work in this codebase?"

# Force Aurora pipeline
aur query "Explain classes" --force-aurora

# Non-interactive mode
aur query "Show me database models" --non-interactive

# Verbose output
aur query "API endpoints" --verbose
```

**When to use:** Asking questions about code, getting AI explanations.

**Note:** For API-key-free usage, use MCP tools instead via Claude Code CLI.

---

### Headless Mode

#### `aur headless`
**Pipe prompts to your preferred CLI tool for autonomous execution**

**⚠️ Note:** Does NOT require Aurora API key. Uses your chosen CLI tool (claude, cursor, etc.) directly.

```bash
# Run with default tool (claude) and settings
aur headless prompt.md

# Use different CLI tool
aur headless prompt.md --tool cursor

# Custom iteration limit (default: 10)
aur headless prompt.md --max-iter 5

# Custom scratchpad location (default: .aurora/headless/scratchpad.md)
aur headless prompt.md --scratchpad results.md

# Show scratchpad after execution
cat .aurora/headless/scratchpad.md
```

**Simple Design:**
- Pipes your prompt to any CLI tool (e.g., `claude`, `cursor`)
- Repeats N times (default: 10 iterations)
- Saves output to scratchpad after each iteration
- No API key management, no budget tracking, no SOAR orchestration
- Just a simple wrapper around: `while [ $i -lt N ]; do cat prompt.md | claude -p; done`

**Tool Support:**
- **claude** - Claude Code CLI (default)
- **cursor** - Cursor CLI
- Any CLI tool that accepts piped input and uses `-p` flag

**Prompt format:** (created at `.aurora/headless/prompt.md.template`)
```markdown
# Goal
[Describe what you want to achieve]

# Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

# Constraints (Optional)
- Constraint 1
- Constraint 2

# Context (Optional)
Additional context about the task...
```

**When to use:** Autonomous exploration, multi-iteration experiments, testing agent capabilities.

---

### Budget Tracking

#### `aur budget show`
**Show current budget usage**

```bash
aur budget show
```

**When to use:** Monitor API costs, check budget remaining.

---

## MCP Tools

Use these tools through Claude Code CLI, Cursor, or other MCP-compatible clients.

**⚠️ Important:** MCP tools do NOT require API keys. They provide search/context that the host LLM processes.

---

### `aurora_search`
**Search indexed codebase**

**Purpose:** Fast keyword/semantic search across indexed code.

**Example prompts:**
- "Search for authentication functions"
- "Find all database connection code"
- "Show me error handling patterns"

**Parameters:**
- `query` (required): Search query
- `limit` (optional): Max results (default: 10)
- `type_filter` (optional): Filter by type (function, class, method)

**When to use:** Finding specific code patterns, locating functions/classes.

---

### `aurora_context`
**Get detailed context for code elements**

**Purpose:** Retrieve full context (code + metadata) for specific elements.

**Example prompts:**
- "Show me the UserService class implementation"
- "Get context for the validate_email function"
- "What does the DatabaseManager module do?"

**Parameters:**
- `query` (required): Element to get context for
- `limit` (optional): Max results (default: 5)

**When to use:** Understanding specific code elements, viewing full implementations.

---

### `aurora_query`
**Complex queries with SOAR reasoning**

**Purpose:** Multi-step reasoning with automatic context retrieval and analysis.

**Example prompts:**
- "Compare our API patterns with REST best practices"
- "Analyze security vulnerabilities in authentication"
- "How does the payment processing flow work end-to-end?"

**Parameters:**
- `query` (required): Complex question
- `force_aurora` (optional): Force SOAR pipeline (default: auto-detect)

**When to use:** Complex analysis, multi-step reasoning, architectural questions.

---

### `aurora_agents_list`
**List available agents**

**Purpose:** Discover AI agents and their capabilities.

**Example prompts:**
- "What agents are available?"
- "Show me all code generation agents"

**When to use:** Agent discovery, checking available capabilities.

---

### `aurora_agents_scan`
**Scan for new agents**

**Purpose:** Update agent manifest with newly added agents.

**Example prompts:**
- "Scan for new agents"
- "Update agent list"

**When to use:** After adding new agent definitions.

---

### `aurora_mem_stats`
**Show memory statistics**

**Purpose:** Check indexing status and health.

**Example prompts:**
- "Show me indexing stats"
- "How many files are indexed?"

**When to use:** Verify indexing, check memory health.

---

### `aurora_doctor`
**Run health checks**

**Purpose:** Full diagnostic report of Aurora configuration.

**Example prompts:**
- "Run Aurora health check"
- "Check Aurora configuration"

**When to use:** Troubleshooting, verifying setup.

---

## Slash Commands

Slash commands are configured during `aur init` for various AI coding tools.

---

### Claude Code CLI

Located in: `~/.config/claude/commands/`

**`/aurora-search`**
```bash
Search codebase: /aurora-search authentication functions
```

**`/aurora-context`**
```bash
Get context: /aurora-context UserService class
```

**`/aurora-query`**
```bash
Complex query: /aurora-query How does auth flow work?
```

**`/aurora-agents`**
```bash
List agents: /aurora-agents list
```

**`/aurora-mem`**
```bash
Memory stats: /aurora-mem stats
```

**`/aurora-doctor`**
```bash
Health check: /aurora-doctor
```

---

### Cursor

Located in: `.cursorrules`

Same commands as Claude Code CLI, but configured in project-local `.cursorrules` file.

---

### Cline

Located in: `~/.cline/mcp_settings.json`

MCP integration via JSON configuration. Use natural language prompts; Cline automatically uses Aurora tools.

---

### Continue

Located in: `~/.continue/config.json`

MCP integration via JSON configuration. Use natural language prompts; Continue automatically uses Aurora tools.

---

## Command Comparison

| Task | CLI Command | MCP Tool | Slash Command |
|------|-------------|----------|---------------|
| **Search code** | `aur mem search "auth"` | Natural: "Search for auth" → `aurora_search` | `/aurora-search auth` |
| **Get context** | `aur mem search "UserService" --show-content` | Natural: "Show UserService" → `aurora_context` | `/aurora-context UserService` |
| **Complex query** | `aur query "How does X work?"` (needs API key) | Natural: "Explain X" → `aurora_query` | `/aurora-query Explain X` |
| **Health check** | `aur doctor` | Natural: "Run health check" → `aurora_doctor` | `/aurora-doctor` |
| **Index code** | `aur mem index` | N/A (use CLI) | N/A |
| **Create plan** | `aur plan create "Feature"` | N/A (use CLI) | N/A |

---

## When to Use Each Interface

### Use CLI Commands When:
- Setting up Aurora (`aur init`)
- Indexing codebase (`aur mem index`)
- Managing plans (`aur plan create/list`)
- Running diagnostics (`aur doctor`)
- Batch processing or scripts

### Use MCP Tools When:
- Working in Claude Code CLI/Cursor/Cline/Continue
- Want natural language interaction
- Don't want to leave your editor
- No API key available (host LLM handles reasoning)

### Use Slash Commands When:
- Quick access in supported editors
- Muscle memory for specific commands
- Explicit tool invocation preferred

---

## Environment Variables

### Required for CLI `aur query`:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

**Note:** `aur headless` does NOT require Aurora API key - it uses your chosen CLI tool's configuration.

### Optional Configuration:
```bash
# Custom database location
export AURORA_DB_PATH=/path/to/aurora.db

# Custom plans directory
export AURORA_PLANS_DIR=/path/to/plans

# Budget limits
export AURORA_BUDGET_LIMIT=10.0

# Debug logging
export AURORA_DEBUG=1
```

---

## Quick Reference

**Most Common Commands:**
```bash
# First-time setup
aur init

# Index code
aur mem index

# Search code
aur mem search "function_name"

# Health check
aur doctor

# Create plan
aur plan create "Feature name"

# Check version
aur --version
```

**No API Key Needed:**
- `aur init`
- `aur mem index`
- `aur mem search`
- `aur mem stats`
- `aur doctor`
- `aur plan *`
- `aur agents *`
- All MCP tools (use host LLM's API key)

**API Key Required:**
- `aur query` (uses Anthropic API directly)

**Uses Your CLI Tool's API Key:**
- `aur headless` (pipes to claude/cursor/etc., uses their API config)

---

## Getting Help

```bash
# General help
aur --help

# Command-specific help
aur init --help
aur mem --help
aur plan --help
aur query --help

# MCP tools help
aurora-mcp --help
```

---

**See Also:**
- [README.md](README.md) - Main documentation
- [MCP_SETUP.md](docs/MCP_SETUP.md) - MCP integration guide
- [CLI_USAGE_GUIDE.md](docs/cli/CLI_USAGE_GUIDE.md) - Detailed CLI usage
