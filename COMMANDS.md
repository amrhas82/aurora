# Aurora Commands Reference

Complete reference for all Aurora CLI and slash commands.

**Version:** 0.5.0

---

## Quick Reference Table

| Command | Type | Purpose | Syntax | Example |
|---------|------|---------|--------|---------|
| `aur init` | CLI | Initialize Aurora in project | `aur init [OPTIONS]` | `aur init --tools=claude` |
| `aur doctor` | CLI | Health checks & diagnostics | `aur doctor [OPTIONS]` | `aur doctor --verbose` |
| `aur mem index` | CLI | Index codebase | `aur mem index [PATH]` | `aur mem index .` |
| `aur mem search` | CLI | Search indexed code | `aur mem search <QUERY>` | `aur mem search "auth"` |
| `aur mem stats` | CLI | Memory statistics | `aur mem stats` | `aur mem stats` |
| `aur soar` | CLI | Multi-turn SOAR reasoning | `aur soar <QUERY>` | `aur soar "explain flow"` |
| `aur query` | CLI | Simple context query | `aur query <QUERY>` | `aur query "login function"` |
| `aur plan` | CLI | Plan management | `aur plan <SUBCOMMAND>` | `aur plan create "Feature"` |
| `aur agents` | CLI | Agent discovery | `aur agents <SUBCOMMAND>` | `aur agents search "test"` |
| `/aur:search` | Slash | Search code (Claude/Cursor) | `/aur:search <query>` | `/aur:search authentication` |
| `/aur:get` | Slash | Get chunk by index | `/aur:get <index>` | `/aur:get 3` |
| `/aur:plan` | Slash | Plan workflows | `/aur:plan [subcommand]` | `/aur:plan create` |
| `/aur:checkpoint` | Slash | Save session context | `/aur:checkpoint` | `/aur:checkpoint` |
| `/aur:implement` | Slash | Plan implementation | `/aur:implement [plan-name]` | `/aur:implement plan-001` |
| `/aur:archive` | Slash | Archive completed plan | `/aur:archive [plan-id]` | `/aur:archive plan-001` |

---

## CLI Commands

### Initialization & Setup

#### `aur init`

Initialize Aurora in your project.

**Runs 3 steps:**
1. Planning setup - Creates `.aurora/` directory
2. Memory indexing - Indexes codebase
3. Tool configuration - Sets up slash commands

```bash
# Interactive mode
aur init

# Non-interactive (uses defaults)
aur init --non-interactive

# Select specific tools
aur init --tools=claude,cursor

# Skip tool configuration
aur init --tools=none
```

**Options:**
- `--config` - Configure tools only (skip indexing)
- `--tools=TOOLS` - Comma-separated list or "all" or "none"
- `--non-interactive` - Use defaults, no prompts
- `--db-path PATH` - Custom database location

---

#### `aur doctor`

Health checks and diagnostics.

```bash
# Run all checks
aur doctor

# Verbose output
aur doctor --verbose
```

**Checks:**
- Python version (>= 3.10)
- Database connectivity
- Indexing status
- Configuration validity

---

### Memory Management

#### `aur mem index`

Index codebase for semantic search.

```bash
# Index current directory
aur mem index

# Index specific path
aur mem index src/

# Use custom database
aur mem index . --db-path /tmp/test.db
```

**What gets indexed:**
- **code** - Python functions, classes, methods (tree-sitter AST)
- **kb** - Markdown docs (README.md, docs/, PRDs)
- **soar** - Reasoning patterns (auto-indexed after `aur soar`)

**Default exclusions:** `.git/`, `venv/`, `node_modules/`, `tasks/`, `CHANGELOG.md`, `LICENSE*`

**Custom exclusions:** Create `.auroraignore` in project root (gitignore-style patterns).

---

#### `aur mem search`

Search indexed code semantically.

```bash
# Basic search
aur mem search "authentication logic"

# Limit results
aur mem search "login" --limit 5

# Filter by type
aur mem search "docs" --type kb

# Custom database
aur mem search "query" --db-path /tmp/test.db
```

**Options:**
- `--limit N` - Max results (default: 10)
- `--type TYPE` - Filter by chunk type (code, kb, soar)
- `--db-path PATH` - Custom database location

**Retrieval strategy:**
- Default: 40% BM25 + 30% ACT-R activation + 30% Git signals
- With ML: 30% BM25 + 40% Semantic + 30% ACT-R activation

---

#### `aur mem stats`

Display memory database statistics.

```bash
# Show stats
aur mem stats

# Custom database
aur mem stats --db-path /tmp/test.db
```

**Output:**
- Total chunks (code, kb, soar)
- Total files indexed
- Language distribution
- Database size
- Last indexed timestamp
- Query performance metrics

---

### Reasoning & Query

#### `aur soar`

Multi-turn SOAR reasoning for complex queries.

```bash
# SOAR query
aur soar "How does the payment flow work?"

# Force complexity level
aur soar "explain architecture" --complexity COMPLEX
```

**When to use:**
- Complex system analysis
- Architecture understanding
- Multi-step reasoning
- "How does X work?" questions

**9-phase pipeline:**
1. Assess - Determine complexity
2. Retrieve - Gather context
3. Decompose - Break into subgoals
4. Verify - Validate groundedness
5. Route - Assign to handlers
6. Collect - Execute subgoals
7. Synthesize - Integrate results
8. Record - Cache patterns
9. Respond - Format answer

**Performance:** 10-60 seconds (depends on complexity)

See [docs/SOAR.md](docs/SOAR.md) for detailed explanation.

---

#### `aur query`

Simple context query (local, no LLM).

```bash
# Local query (SOAR phases 1-2 only)
aur query "authentication logic"

# No API calls, no costs
# Returns relevant chunks only
```

**When to use:**
- Quick code lookup
- No reasoning needed
- Want raw chunks, not synthesis

**vs aur soar:**
- `aur query` - Fast, local, returns chunks only (~1s)
- `aur soar` - Multi-turn, synthesis, full reasoning (~30s)

---

### Planning & Agents

#### `aur plan`

Plan management (OpenSpec-adapted workflow).

```bash
# Create plan
aur plan create "Add user authentication"

# List plans
aur plan list

# Show plan details
aur plan show plan-001

# Archive completed plan
aur plan archive plan-001
```

**Subcommands:**
- `create TITLE` - Create new plan
- `list` - List all plans
- `show PLAN_ID` - Show plan details
- `archive PLAN_ID` - Archive completed plan

---

#### `aur agents`

Agent discovery and search.

```bash
# List all agents
aur agents list

# Search agents
aur agents search "test"

# Show agent details
aur agents show qa-test-architect
```

**Subcommands:**
- `list` - List all available agents
- `search QUERY` - Search agents by capabilities
- `show AGENT_ID` - Show agent details

---

## Slash Commands

Slash commands work in Claude Code, Cursor, Cline, and other supported AI tools.

### `/aur:search`

Search indexed code from AI tool.

```
/aur:search authentication logic
```

**Returns:** Top matching chunks with relevance scores.

**Use when:** AI needs to find specific code during conversation.

---

### `/aur:get`

Get full chunk content by index.

```
/aur:get 3
```

**Use when:** After `/aur:search`, retrieve complete chunk content.

**Example workflow:**
```
User: Find login code
AI: /aur:search login
AI: Found 3 results. Let me get the first one.
AI: /aur:get 1
```

---

### `/aur:plan`

Plan workflow orchestration.

```
/aur:plan create Add OAuth integration
/aur:plan list
/aur:plan show plan-001
```

**Subcommands:**
- `create TITLE` - Create new plan
- `list` - List plans
- `show PLAN_ID` - Show plan

---

### `/aur:checkpoint`

Save session context before compaction.

```
/aur:checkpoint
```

**Use when:**
- Before context window fills
- Before major conversation pivot
- Want to preserve reasoning state

---

### `/aur:implement`

Plan-based implementation (placeholder).

```
/aur:implement plan-001
```

**Status:** Placeholder in v0.5.0. Shows Aurora workflow guidance.

**Future:** Will execute plan-based changes automatically.

---

### `/aur:archive`

Archive completed plan.

```
/aur:archive plan-001
```

**Use when:** Plan is completed and ready for archival.

---

## Command Comparison

### Search: CLI vs Slash

| Feature | `aur mem search` | `/aur:search` |
|---------|-----------------|---------------|
| Where | Terminal | AI tool (Claude/Cursor) |
| Output | Terminal table | AI tool response |
| Use case | Manual search | AI-assisted search |

### Reasoning: soar vs query

| Feature | `aur soar` | `aur query` |
|---------|-----------|-------------|
| Complexity | Multi-turn reasoning | Simple lookup |
| Speed | 10-60s | ~1s |
| Output | Synthesized answer | Raw chunks |
| LLM calls | Multiple (SOAR phases) | None |
| Cost | API costs | Free (local only) |

### Planning: CLI vs Slash

| Feature | `aur plan` | `/aur:plan` |
|---------|-----------|-------------|
| Where | Terminal | AI tool |
| Create | `aur plan create` | `/aur:plan create` |
| List | `aur plan list` | `/aur:plan list` |
| Show | `aur plan show ID` | `/aur:plan show ID` |

---

## Configuration

### Database Location

Default: `.aurora/memory.db` (project-local)

Custom location:
```bash
# Per-command
aur mem search "query" --db-path /tmp/test.db

# Via environment
export AURORA_DB_PATH=/tmp/test.db
aur mem search "query"
```

### Indexing Exclusions

Create `.auroraignore` in project root:

```
# Exclude patterns (gitignore-style)
tests/**
docs/archive/**
*.tmp
```

### ML Model Selection

See [docs/ML_MODELS.md](docs/ML_MODELS.md) for custom embedding models.

---

## See Also

- [README.md](README.md) - Overview and installation
- [docs/SOAR.md](docs/SOAR.md) - SOAR reasoning pipeline
- [docs/ML_MODELS.md](docs/ML_MODELS.md) - Custom ML models
- [docs/MCP_DEPRECATION.md](docs/MCP_DEPRECATION.md) - MCP tool deprecation (v0.5.0)
