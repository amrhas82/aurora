# AURORA Interface Guide

## Overview

This guide documents all public interfaces for AURORA across three interface types: CLI (Command-Line Interface), MCP (Model Context Protocol), and Slash Commands. Each interface type serves a specific use case and audience.

## Interface Decision Criteria

### When to Use CLI Commands

**Audience:** Human developers working in terminal environments

**Use CLI when:**
- Running interactive commands with formatted console output
- Performing setup, configuration, or diagnostic tasks
- Getting human-readable summaries and reports
- Working directly from bash/zsh/fish terminal

**Characteristics:**
- Formatted output with colors, tables, and panels (via Rich library)
- Interactive prompts and confirmations
- Subcommands grouped by domain (e.g., `aur mem search`, `aur plan list`)
- Help text and examples via `--help` flags

### When to Use MCP Tools

**Audience:** Claude Code and other LLM-based development tools

**Use MCP when:**
- Programmatic access to AURORA features from Claude
- JSON-structured data exchange between tools
- Automated workflows without human interaction
- Integration with LLM reasoning loops

**Characteristics:**
- JSON input/output for structured data exchange
- No interactive prompts or colored output
- Registered with Model Context Protocol for LLM tool use
- Optimized for machine consumption, not human reading

### When to Use Slash Commands

**Audience:** Claude Code users invoking multi-step workflows

**Use Slash Commands when:**
- Orchestrating multi-step workflows with decision points
- Following the OpenSpec pattern (read state → make decisions → invoke tools → write results)
- Creating, managing, or archiving structured work artifacts (plans, proposals, etc.)
- Coordinating between CLI commands, MCP tools, and file operations

**Characteristics:**
- High-level workflow orchestration
- State management across multiple steps
- Integration with Aurora's planning and change management system
- Declarative workflow definitions in markdown format

## OpenSpec Workflow Pattern

Slash commands follow the OpenSpec pattern, which provides a structured approach to managing changes:

1. **Read State**: Gather current context (files, plans, configurations)
2. **Make Decisions**: Analyze state and determine appropriate actions
3. **Invoke Tools**: Execute CLI commands or MCP tools based on decisions
4. **Write Results**: Update plans, create artifacts, record decisions

This pattern is used by `/aur:plan` for managing work proposals and will be used by future commands like `/aur:archive` (archiving completed work) and `/aur:implement` (executing approved plans).

## Complete Interface Reference

### CLI Commands (8 commands)

| Command Name | Interface Type | Purpose | When To Use | Syntax | Example |
|--------------|----------------|---------|-------------|--------|---------|
| `aur init` | CLI | Initialize AURORA configuration | First-time setup, reinitialize after config issues | `aur init [OPTIONS]` | `aur init --api-key-source env` |
| `aur doctor` | CLI | Run health checks and diagnostics | Troubleshooting installation, verifying configuration | `aur doctor [OPTIONS]` | `aur doctor --verbose` |
| `aur mem index` | CLI | Index code directory for semantic search | After adding new code, updating codebase | `aur mem index <PATH> [OPTIONS]` | `aur mem index packages/ --recursive` |
| `aur mem search` | CLI | Search indexed codebase | Finding code by natural language query | `aur mem search <QUERY> [OPTIONS]` | `aur mem search "authentication logic" --limit 5` |
| `aur mem stats` | CLI | Show memory database statistics | Understanding index size, checking indexing success | `aur mem stats` | `aur mem stats` |
| `aur agents` | CLI | Discover and search available agents | Finding agents by keyword, listing all agents | `aur agents list \| aur agents search <QUERY>` | `aur agents search "test"` |
| `aur plan` | CLI | Manage planning workflows | Creating, listing, validating work plans | `aur plan <SUBCOMMAND> [OPTIONS]` | `aur plan list --active` |
| `aur headless` | CLI | Pipe prompts to CLI tool for autonomous execution | Multi-iteration experiments, autonomous exploration | `aur headless <PROMPT_FILE> [OPTIONS]` | `aur headless prompt.md --tool claude --max-iter 5` |

### MCP Tools (9 tools)

| Command Name | Interface Type | Purpose | When To Use | Syntax | Example |
|--------------|----------------|---------|-------------|--------|---------|
| `aurora_search` | MCP | Search indexed codebase with semantic + keyword search | When Claude needs to find code by natural language query | `aurora_search(query: str, limit: int = 10, type_filter: str \| None = None)` | `aurora_search("async patterns", limit=5)` |
| `aurora_index` | MCP | Index a directory of code files | When Claude needs to index new code for search | `aurora_index(path: str, recursive: bool = True)` | `aurora_index("packages/core", recursive=True)` |
| `aurora_context` | MCP | Retrieve code context from specific file/function | When Claude needs focused context from known location | `aurora_context(file_path: str, symbol: str \| None = None)` | `aurora_context("src/main.py", symbol="init")` |
| `aurora_related` | MCP | Find related code using ACT-R spreading activation | When Claude needs to discover related code chunks | `aurora_related(chunk_id: str, max_hops: int = 2)` | `aurora_related("chunk-123", max_hops=3)` |
| `aurora_query` | MCP | Retrieve relevant context without LLM inference | When Claude needs context with complexity assessment | `aurora_query(query: str, limit: int = 10, type_filter: str \| None = None, verbose: bool = False)` | `aurora_query("SOAR pipeline", verbose=True)` |
| `aurora_get` | MCP | Get full chunk by index from last search results | After search, when Claude needs complete chunk content | `aurora_get(index: int)` | `aurora_get(3)` |
| `aurora_list_agents` | MCP | List all discovered agents | When Claude needs inventory of available agents | `aurora_list_agents()` | `aurora_list_agents()` |
| `aurora_search_agents` | MCP | Search agents by keyword with relevance scoring | When Claude needs to find agents matching criteria | `aurora_search_agents(query: str)` | `aurora_search_agents("quality")` |
| `aurora_show_agent` | MCP | Show full agent details including markdown content | When Claude needs complete agent instructions | `aurora_show_agent(agent_id: str)` | `aurora_show_agent("qa-test-architect")` |

### Slash Commands (2 current + 2 planned)

| Command Name | Interface Type | Purpose | When To Use | Syntax | Example |
|--------------|----------------|---------|-------------|--------|---------|
| `/aur:plan` | Slash | Manage Aurora planning workflows and change proposals | Creating, validating, and tracking implementation plans | `/aur:plan [create\|list\|show\|validate]` | `/aur:plan create "Add user auth"` |
| `/aur:checkpoint` | Slash | Save session context for continuity across compaction | Before context compaction, at critical decision points | `/aur:checkpoint` | `/aur:checkpoint` |
| `/aur:archive` | Slash (Planned) | Archive deployed OpenSpec changes and update specs | After deploying a change, marking work complete | `/aur:archive <plan-id>` | `/aur:archive auth-feature-001` |
| `/aur:implement` | Slash (Planned) | Implement approved OpenSpec changes with task tracking | Executing approved plans systematically | `/aur:implement <plan-id>` | `/aur:implement auth-feature-001` |

## Command Groups and Relationships

### Memory Management
- **CLI**: `aur mem index`, `aur mem search`, `aur mem stats`
- **MCP**: `aurora_search`, `aurora_index`, `aurora_context`, `aurora_related`, `aurora_query`, `aurora_get`
- **Relationship**: CLI provides human-readable output, MCP provides structured JSON for programmatic access

### Agent Discovery
- **CLI**: `aur agents list`, `aur agents search`
- **MCP**: `aurora_list_agents`, `aurora_search_agents`, `aurora_show_agent`
- **Relationship**: CLI formats output for terminal, MCP returns JSON for Claude to parse

### Planning & Workflow
- **CLI**: `aur plan list`, `aur plan show`, `aur plan create`, `aur plan validate`
- **Slash**: `/aur:plan`, `/aur:checkpoint`, `/aur:archive` (planned), `/aur:implement` (planned)
- **Relationship**: CLI for direct plan manipulation, Slash for orchestrated workflows

### Configuration & Diagnostics
- **CLI**: `aur init`, `aur doctor`
- **MCP**: None (human-interactive tasks only)
- **Slash**: None (direct CLI usage preferred)

## Migration Notes

### Deprecated Commands (Removed in v0.2.0)

The following commands have been removed to simplify the interface:

**Removed CLI Commands:**
- `aur query` - Use `aurora_query` MCP tool from Claude instead

**Removed MCP Tools:**
- `aurora_stats` - Use `aur mem stats` CLI command instead

**Removed Slash Commands:**
- `/aur:init` - Use `aur init` CLI command directly
- `/aur:query` - Use `aurora_query` MCP tool instead
- `/aur:index` - Use `aurora_index` MCP tool instead
- `/aur:search` - Use `aurora_search` MCP tool instead
- `/aur:agents` - Use `aurora_list_agents` or `aurora_search_agents` MCP tools instead
- `/aur:doctor` - Use `aur doctor` CLI command directly

**Rationale:**
- Reduces redundancy across interfaces
- Clarifies when to use CLI vs MCP vs Slash
- Focuses Slash commands on multi-step workflows (OpenSpec pattern)
- Keeps CLI for human-interactive setup/diagnostic tasks
- Keeps MCP for programmatic data access

### Upgrade Path

If you have scripts or workflows using removed commands, update as follows:

```bash
# Before (removed)
aur query "authentication"

# After (use MCP from Claude)
# In Claude Code: aurora_query("authentication")
```

```bash
# Before (removed slash command)
/aur:init

# After (use CLI directly)
# Run: aur init
```

## Additional Resources

- **MCP Setup Guide**: `/home/hamr/PycharmProjects/aurora/docs/MCP_SETUP.md`
- **CLI Usage Guide**: `/home/hamr/PycharmProjects/aurora/docs/cli/CLI_USAGE_GUIDE.md`
- **SOAR Architecture**: `/home/hamr/PycharmProjects/aurora/docs/architecture/SOAR_ARCHITECTURE.md`
- **Testing Guide**: `/home/hamr/PycharmProjects/aurora/docs/development/TESTING.md`

## Getting Help

For any command, use:
- CLI: `aur <command> --help`
- MCP: Tool descriptions visible in Claude Code
- Slash: Read command markdown files in `.claude/commands/aur/*.md`

For troubleshooting: `aur doctor --verbose`
