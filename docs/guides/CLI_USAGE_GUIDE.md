# AURORA CLI Usage Guide

Complete guide to using the AURORA command-line interface for intelligent code querying, memory management, and autonomous reasoning.

**Version**: 1.1.0
**Last Updated**: 2024-12-24

---

## Important: CLI vs MCP - API Key Requirements

**Standalone CLI commands (`aur headless`):**
- **REQUIRE** `ANTHROPIC_API_KEY` environment variable
- Run LLM inference directly in the CLI
- You pay for API usage

**MCP tools (inside Claude Code CLI):**
- **DO NOT REQUIRE** API keys
- Provide context/search to Claude Code CLI's built-in LLM
- No additional API costs beyond your Claude subscription

**Note**: For querying with LLM responses, use the `aurora_query` MCP tool from within Claude Code, which does not require an API key.

See [MCP Setup Guide](../MCP_SETUP.md) and [COMMANDS.md](../../COMMANDS.md) for complete command reference with quick reference tables.

---

## Table of Contents

1. [Installation Verification](#installation-verification)
2. [Initial Setup](#initial-setup)
3. [Configuration](#configuration)
4. [Memory Management](#memory-management)
5. [Agent Discovery](#agent-discovery)
6. [Budget Management](#budget-management)
7. [Headless Mode](#headless-mode)
8. [Health Checks & Diagnostics](#health-checks--diagnostics)
9. [Graceful Degradation](#graceful-degradation)
10. [Troubleshooting](#troubleshooting)
11. [Command Reference](#command-reference)

---

## Installation Verification

### Install AURORA CLI

```bash
# Install from monorepo (development)
pip install -e packages/cli

# Or install standalone
pip install aurora-cli
```

### Verify Installation

```bash
# Check version
aur --version

# Expected output:
# aurora, version 0.1.0

# Show help
aur --help
```

---

## Initial Setup

### Unified Setup with `aur init`

AURORA provides a streamlined, project-specific initialization with a 3-step interactive flow:

```bash
aur init
```

**The 3-Step Flow:**

#### Step 1: Planning Setup (Git + Directories)

```
Step 1/3: Planning Setup
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Git repository not detected.
Initialize git repository? [Y/n]: y
  ✓ Git initialized

Creating project structure...
  ✓ .aurora/plans/active/
  ✓ .aurora/plans/archive/
  ✓ .aurora/logs/
  ✓ .aurora/cache/

Detecting project metadata...
  • Python: 3.10.12 (from pyproject.toml)
  • Package Manager: poetry
  • Testing Framework: pytest
  ✓ Created .aurora/project.md
```

**What It Does:**
- Prompts to run `git init` if no `.git` directory detected
- Creates project-specific directory structure
- Auto-detects project metadata (Python version, package manager, test framework)
- Creates `.aurora/project.md` with project context

#### Step 2: Memory Indexing

```
Step 2/3: Memory Indexing
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Index codebase for semantic search? [Y/n]: y

Indexing . ━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
  ✓ Indexed 47 files, 234 chunks in 3.4s
  ✓ Database: ./.aurora/memory.db
```

**What It Does:**
- Indexes Python files for semantic search
- Creates project-specific memory database at `./.aurora/memory.db`
- Progress bar shows indexing status
- Can be skipped and run later with `aur mem index .`

#### Step 3: Tool Configuration

```
Step 3/3: Tool Configuration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Select tools to configure:
❯ ◉ Claude Code (claude_desktop_config.json)
  ◯ Universal (aurora.mcp.json)
  ◯ AMP Code (ampcode-mcp-settings.json)
  ◯ Droid (droid-mcp-settings.json)

  ✓ Claude Code configured
  ✓ Universal configured
```

**What It Does:**
- Interactive checkbox to select AI coding tools
- Detects existing tool configurations
- Creates/updates MCP server configurations
- Updates configs within markers only (preserves custom settings)

#### Success Summary

```
✓ Initialization Complete!

Summary:
  • Git: Initialized
  • Planning: .aurora/plans/ created
  • Memory: 234 chunks indexed
  • Tools: 2 configured (Claude Code, Universal)

Next Steps:
  1. Verify setup: aur doctor
  2. Create a plan: aur plan create "Feature name"
  3. Search codebase: aur mem search "authentication"
```

**Time Estimate:** < 2 minutes

---

### Quick Tool Configuration (Skip Other Steps)

If you've already initialized AURORA and only want to configure AI coding tools:

```bash
aur init --config
```

**What It Does:**
- Skips Steps 1 and 2 (Planning + Memory)
- Runs Step 3 only (Tool Configuration)
- Requires existing `.aurora/` directory

**Example:**
```
Step 3/3: Tool Configuration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Current status:
  ✓ Claude Code (configured 2 days ago)
  ✗ Universal (not configured)

Select tools to configure:
❯ ◯ Claude Code (already configured)
  ◉ Universal (aurora.mcp.json)

  ✓ Universal configured
```

---

### Re-Running `aur init` (Idempotent)

AURORA detects existing setup and offers selective re-run options:

```bash
aur init
```

**Re-Run Menu:**

```
AURORA is already initialized in this project.

Current Status:
  ✓ Step 1 (Planning): Completed 2 days ago
  ✓ Step 2 (Memory):   234 chunks indexed
  ✓ Step 3 (Tools):    2 tools configured

How would you like to proceed?

1. Re-run all steps
2. Select specific steps
3. Configure tools only
4. Exit

Choice [1-4]: _
```

**Options:**

1. **Re-run all steps**: Runs Steps 1-3 with safety features:
   - Git init skipped if `.git` exists
   - `project.md` custom content preserved
   - Memory database backed up before re-indexing
   - Tool configs updated within markers only

2. **Select specific steps**: Interactive checkbox to pick Steps 1, 2, or 3

3. **Configure tools only**: Equivalent to `aur init --config`

4. **Exit**: No changes made

**Safety Features:**
- Project metadata preserves user edits
- Tool configurations update only between `<!-- AURORA:START -->` and `<!-- AURORA:END -->` markers
- Memory database backed up to `memory.db.backup` before re-indexing
- No data loss on re-runs

---

### Project-Specific vs Global Storage

AURORA v0.3.0+ uses **project-specific storage** by default:

| File | Location | Scope |
|------|----------|-------|
| Memory database | `./.aurora/memory.db` | Project-specific |
| Planning data | `./.aurora/plans/` | Project-specific |
| Logs | `./.aurora/logs/` | Project-specific |
| Agent cache | `./.aurora/cache/` | Project-specific |
| Project metadata | `./.aurora/project.md` | Project-specific |
| **Budget tracker** | `~/.aurora/budget_tracker.json` | **Global** (user-wide) |

**Benefits:**
- Multi-project isolation (each project has its own memory)
- No global config file with API keys (use environment variables only)
- Easier to share projects (commit `.aurora/` to git)
- Clean per-project setup

**Migration:** If upgrading from v0.2.x, see [MIGRATION_GUIDE_v0.3.0.md](MIGRATION_GUIDE_v0.3.0.md)

---

### API Key Configuration

**Important:** API keys are **NOT** required for initialization. AURORA uses environment variables only.

```bash
# Set API key for standalone CLI commands (aur headless)
export ANTHROPIC_API_KEY=sk-ant-...

# MCP tools inside Claude Code CLI do NOT require API keys
```

**Get API Key:**
- Anthropic: https://console.anthropic.com
- OpenAI: https://platform.openai.com

**Why No API Key Prompts?**
- MCP tools provide context to Claude Code CLI's built-in LLM (no API costs)
- Standalone CLI commands read from environment variables
- More secure (keys not stored in config files)

See [MCP Setup Guide](../MCP_SETUP.md) for integration details

---

## Configuration

AURORA uses a hierarchical configuration system with multiple sources.

### Configuration Precedence

Configuration is loaded in this order (highest to lowest priority):

1. **CLI flags** (per-command options)
2. **Environment variables** (`ANTHROPIC_API_KEY`, `AURORA_*`)
3. **Config file** (`~/.aurora/config.json` or `./aurora.config.json`)
4. **Default values** (built-in defaults)

### Environment Variables

```bash
# API key (required for queries)
export ANTHROPIC_API_KEY=sk-ant-...

# Escalation threshold (optional)
export AURORA_ESCALATION_THRESHOLD=0.7

# Logging level (optional)
export AURORA_LOGGING_LEVEL=INFO
```

### Config File Structure

**Location**: `~/.aurora/config.json` or `./aurora.config.json`

```json
{
  "version": "1.1.0",
  "llm": {
    "provider": "anthropic",
    "anthropic_api_key": "sk-ant-...",
    "model": "claude-3-5-sonnet-20241022",
    "temperature": 0.7,
    "max_tokens": 4096
  },
  "escalation": {
    "threshold": 0.7,
    "enable_keyword_only": false,
    "force_mode": null
  },
  "memory": {
    "auto_index": true,
    "index_paths": ["."],
    "chunk_size": 1000,
    "overlap": 200
  },
  "logging": {
    "level": "INFO",
    "file": "~/.aurora/aurora.log"
  }
}
```

**Configuration Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `llm.provider` | string | `"anthropic"` | LLM provider (only anthropic supported) |
| `llm.anthropic_api_key` | string | `null` | API key (prefer env var) |
| `llm.model` | string | `"claude-3-5-sonnet-20241022"` | Model identifier |
| `llm.temperature` | float | `0.7` | Response randomness (0.0-1.0) |
| `llm.max_tokens` | integer | `4096` | Maximum response tokens |
| `escalation.threshold` | float | `0.7` | Complexity threshold for AURORA (0.0-1.0) |
| `escalation.enable_keyword_only` | boolean | `false` | Use keyword-only escalation |
| `escalation.force_mode` | string | `null` | Force mode: `"direct"` or `"aurora"` |
| `memory.auto_index` | boolean | `true` | Prompt to index on first query |
| `memory.index_paths` | array | `["."]` | Paths to index automatically |
| `memory.chunk_size` | integer | `1000` | Size of code chunks (characters) |
| `memory.overlap` | integer | `200` | Overlap between chunks (characters) |
| `logging.level` | string | `"INFO"` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `logging.file` | string | `"~/.aurora/aurora.log"` | Log file path |

### Create Custom Config File

```bash
# Manual creation
mkdir -p ~/.aurora
nano ~/.aurora/config.json

# Or copy and edit
cp ~/.aurora/config.json ./aurora.config.json
nano ./aurora.config.json
```

---

## Memory Management

AURORA uses a persistent memory store to provide context for queries.

### Index Current Directory

```bash
aur mem index
```

**What It Does:**
- Scans current directory recursively
- Parses Python files (extensible to other languages)
- Extracts functions, classes, methods
- Stores code chunks with metadata
- Creates embeddings for semantic search

**Output:**
```
Using database: ./aurora.db
Indexing . ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%

┌────────────────────────────────────────────────┐
│ ✓ Indexing complete                            │
│                                                │
│ Files indexed:  47                             │
│ Chunks created: 234                            │
│ Duration:       3.42s                          │
│ Errors:         0                              │
└────────────────────────────────────────────────┘
```

### Index Specific Directory

```bash
aur mem index /path/to/project
```

### Index with Custom Database

```bash
aur mem index . --db-path ~/.aurora/memory.db
```

### Search Memory

```bash
aur mem search "authentication"
```

**Output:**
```
Searching memory from ./aurora.db...

Found 8 results for 'authentication'

┌──────────────────┬──────┬──────────────────┬──────────┬────────┐
│ File             │ Type │ Name             │ Lines    │  Score │
├──────────────────┼──────┼──────────────────┼──────────┼────────┤
│ auth_manager.py  │ func │ authenticate_user│ 45-67    │  0.856 │
│ tokens.py        │ func │ validate_token   │ 23-41    │  0.782 │
│ middleware.py    │ class│ AuthMiddleware   │ 89-145   │  0.734 │
│ decorators.py    │ func │ require_auth     │ 12-28    │  0.689 │
│ models.py        │ class│ User             │ 34-78    │  0.645 │
│ permissions.py   │ func │ check_permission │ 56-72    │  0.612 │
│ session.py       │ class│ SessionManager   │ 23-89    │  0.587 │
│ oauth.py         │ func │ oauth_callback   │ 123-156  │  0.534 │
└──────────────────┴──────┴──────────────────┴──────────┴────────┘

Average scores:
  Activation: 0.245
  Semantic:   0.673
  Hybrid:     0.654
```

#### Type Abbreviations

Search results display abbreviated type names for improved readability:

| Full Type  | Abbreviation | Description                    |
|------------|--------------|--------------------------------|
| function   | func         | Function definitions           |
| method     | meth         | Class method definitions       |
| class      | class        | Class definitions              |
| code       | code         | Generic code chunks            |
| reasoning  | reas         | Reasoning patterns from SOAR   |
| knowledge  | know         | Knowledge from conversation logs|
| document   | doc          | Documentation chunks           |

### Search with More Results

```bash
aur mem search "database" --limit 10
```

### Search with Content Preview

```bash
aur mem search "calculate" --show-content
```

### Search with Score Breakdown

Show detailed score breakdown with intelligent explanations in rich box-drawing format:

```bash
aur mem search "authentication" --show-scores
```

**Output:**
```
Found 8 results for 'authentication'

┌─ auth_manager.py | func | authenticate_user (Lines 45-67) ──────────┐
│ Final Score: 0.856                                                   │
│   ├─ BM25:       0.923 ⭐ (exact keyword match on 'authenticate')    │
│   ├─ Semantic:   0.834 (high conceptual relevance)                  │
│   └─ Activation: 0.450 (accessed 12x, 23 commits, last used 2d ago)│
│ Git: 23 commits, last modified 2 days ago                           │
└──────────────────────────────────────────────────────────────────────┘

┌─ tokens.py | func | validate_token (Lines 23-41) ──────────────────┐
│ Final Score: 0.782                                                   │
│   ├─ BM25:       0.867 (strong term overlap (1/2 terms))           │
│   ├─ Semantic:   0.756 (moderate conceptual relevance)              │
│   └─ Activation: 0.420 (accessed 8x, 15 commits, last used 1w ago) │
│ Git: 15 commits, last modified 1 week ago                           │
└──────────────────────────────────────────────────────────────────────┘
```

#### Score Explanations

The rich box-drawing format shows three score components with intelligent explanations:

| Score Component | Explanation Types | Example |
|-----------------|-------------------|---------|
| **BM25** | exact match, strong overlap, partial match, no match | `⭐ exact keyword match on 'auth'` |
| **Semantic** | very high, high, moderate, low conceptual relevance | `(high conceptual relevance)` |
| **Activation** | access count, commits, recency | `(accessed 3x, 23 commits, last used 2 days ago)` |

**Explanation Details:**

- **BM25 (Keyword Matching)**:
  - Exact match (100% query terms): `⭐ exact keyword match on 'term1', 'term2'...`
  - Strong overlap (≥50% terms): `(strong term overlap (2/3 terms))`
  - Partial match (<50% terms): `(partial match (1/3 terms))`
  - No match (0% terms): `(no keyword match)`

- **Semantic (Conceptual Relevance)**:
  - ≥0.9: `(very high conceptual relevance)`
  - 0.8-0.89: `(high conceptual relevance)`
  - 0.7-0.79: `(moderate conceptual relevance)`
  - <0.7: `(low conceptual relevance)`

- **Activation (Recency/Frequency)**:
  - Shows access count, commit count, and last used time
  - Example: `(accessed 5x, 23 commits, last used 2 days ago)`
  - Omits unavailable metadata gracefully

**Hybrid Score Calculation:**
- Weighted combination: 30% BM25 + 40% Semantic + 30% Activation
- Final score determines result ranking

### Filter by Element Type

Search for specific code element types:

```bash
# Search for functions only
aur mem search "calculate" --type function

# Search for classes only
aur mem search "Manager" --type class

# Search for methods only
aur mem search "validate" --type method

# Search knowledge/documentation chunks
aur mem search "architecture" --type knowledge
```

**Available Types:**
- `function` - Top-level functions
- `class` - Class definitions
- `method` - Class methods
- `knowledge` - Markdown documentation chunks
- `document` - Other document types

### Search with JSON Output

```bash
aur mem search "login" --format json > results.json
```

**JSON Format:**
```json
[
  {
    "chunk_id": "abc123...",
    "file_path": "/home/user/project/auth.py",
    "line_start": 45,
    "line_end": 67,
    "content": "def authenticate_user(username, password):\n    ...",
    "activation_score": 0.245,
    "semantic_score": 0.673,
    "hybrid_score": 0.856,
    "metadata": {
      "type": "function",
      "name": "authenticate_user",
      "complexity": 5
    }
  }
]
```

### View Memory Statistics

```bash
aur mem stats
```

**Output:**
```
Loading statistics from ./aurora.db...

    Memory Store Statistics
┌─────────────────────┬──────────────┐
│ Total Chunks        │ 234          │
│ Total Files         │ 47           │
│ Database Size       │ 12.45 MB     │
│                     │              │
│ Languages           │              │
│   python            │ 234 chunks   │
└─────────────────────┴──────────────┘
```

---

## Agent Discovery

AURORA provides agent discovery to find and manage AI coding assistant agents from multiple sources.

### Supported Agent Sources

AURORA scans 4 directories for agent definition files:

| Source | Directory | Description |
|--------|-----------|-------------|
| Claude Code | `~/.claude/agents/` | Claude Code CLI agents |
| AMP Code | `~/.config/ampcode/agents/` | AMP Code agents |
| Droid | `~/.config/droid/agent/` | Droid agents |
| OpenCode | `~/.config/opencode/agent/` | OpenCode agents |

### List All Agents

```bash
aur agents list
```

**Output:**
```
Discovered 14 agent(s)

General (14)
  1-create-prd - 1 Create Prd
  business-analyst - Business Analyst
  full-stack-dev - Full Stack Dev
  qa-test-architect - Qa Test Architect
  ...
```

### Filter by Category

```bash
aur agents list --category qa
```

**Available Categories:**
- `eng` - Engineering/development agents
- `qa` - Quality assurance/testing agents
- `product` - Product management agents
- `general` - General-purpose agents

### Search Agents

Search for agents by keyword across all fields (id, role, goal, skills):

```bash
aur agents search "test"
```

**Output:**
```
Found 3 agent(s) matching 'test'

┌─────────────────────┬───────┬────────────────────────┬─────────────────┐
│ Agent ID            │ Cate… │ Role                   │ Match           │
├─────────────────────┼───────┼────────────────────────┼─────────────────┤
│ qa-test-architect   │ gene… │ Qa Test Architect      │ partial id match│
│ 3-process-task-list │ gene… │ 3 Process Task List    │ in goal         │
│ full-stack-dev      │ gene… │ Full Stack Dev         │ in goal         │
└─────────────────────┴───────┴────────────────────────┴─────────────────┘
```

### Show Agent Details

Display full details for a specific agent:

```bash
aur agents show qa-test-architect
```

**Output:**
```
╭───────────────────────────── qa-test-architect ──────────────────────────────╮
│ Qa Test Architect                                                            │
│ Category: general                                                            │
│                                                                              │
│ Goal                                                                         │
│ Use this agent for comprehensive quality assessment, test architecture       │
│ review, and quality gate decisions...                                        │
│                                                                              │
│ Source: /home/user/.claude/agents/qa-test-architect.md                       │
╰──────────────────────────────────────────────────────────────────────────────╯
```

**Fuzzy Matching:** If an agent is not found, AURORA suggests similar agents:

```bash
aur agents show non-existent
```

**Output:**
```
Agent 'non-existent' not found.

Did you mean:
  - qa-test-architect
  - holistic-architect
  - context-initializer
```

### Refresh Agent Manifest

Force regenerate the agent manifest from all sources:

```bash
aur agents refresh
```

**Output:**
```
Refreshing agent manifest...

╭──────── Refresh Summary ────────╮
│ Manifest refreshed successfully │
│                                 │
│ Agents found: 14                │
│ Sources scanned: 2              │
│ Malformed files: 0              │
│ Duration: 0.06s                 │
│                                 │
│ Agents by category:             │
│   general: 14                   │
╰─────────────────────────────────╯
```

### Agent File Format

Agent files are Markdown with YAML frontmatter:

```markdown
---
name: my-agent
description: Description of what this agent does
model: inherit
color: cyan
category: eng
skills:
  - skill1
  - skill2
---

# Agent Title

Agent content and instructions...
```

**Required Fields:**
- `name` (or `id`): Unique kebab-case identifier
- `description` (or `goal`): Brief description of agent's purpose

**Optional Fields:**
- `category`: Agent category (eng/qa/product/general)
- `skills`: List of agent capabilities
- `when_to_use`: Guidance on when to invoke this agent
- `dependencies`: Other agents this agent may invoke

### Configuration

Agent discovery settings in `~/.aurora/config.json`:

```json
{
  "agents": {
    "auto_refresh": true,
    "refresh_interval_hours": 24,
    "discovery_paths": [
      "~/.claude/agents",
      "~/.config/ampcode/agents",
      "~/.config/droid/agent",
      "~/.config/opencode/agent"
    ],
    "manifest_path": "~/.aurora/cache/agent_manifest.json"
  }
}
```

**Settings:**

| Setting | Default | Description |
|---------|---------|-------------|
| `auto_refresh` | `true` | Automatically refresh stale manifests |
| `refresh_interval_hours` | `24` | Hours before manifest is considered stale |
| `discovery_paths` | 4 paths | Directories to scan for agents |
| `manifest_path` | `~/.aurora/cache/agent_manifest.json` | Cached manifest location |

### Performance

Agent discovery is optimized for speed:
- **Discovery**: ~37ms for 14 agents
- **Refresh**: ~45ms for full manifest regeneration
- **Manifest caching**: Avoids re-scanning on every command

---

## Budget Management

AURORA provides comprehensive budget management to help you monitor and control API spending.

### Check Budget Status

```bash
aur budget show
```

**Output:**
```
Budget Status
┌─────────────────┬───────────┐
│ Spent           │ $2.3450   │
│ Budget Limit    │ $15.0000  │
│ Remaining       │ $12.6550  │
│ Usage           │ 15.6%     │
└─────────────────┴───────────┘
```

**Alternative (default subcommand):**
```bash
aur budget
```

### Set Budget Limit

```bash
aur budget set 50.00
```

**Output:**
```
✓ Budget limit updated to $50.00
  Previous limit: $15.00
```

**Use Case:**
- Set monthly budget to control costs
- Increase limit when running complex queries
- Lower limit for testing or exploratory work

### Reset Spending

```bash
aur budget reset
```

**Output:**
```
✓ Spending reset to $0.00
  Previous spending: $2.3450
```

**Use Case:**
- Reset at start of billing cycle
- Clear spending after testing
- Start fresh after budget adjustment

### View Query History

```bash
aur budget history
```

**Output:**
```
Query History
┌──────────────────────┬──────────────────────────────────┬───────────┬───────────┐
│ Timestamp            │ Query                            │ Cost      │ Status    │
├──────────────────────┼──────────────────────────────────┼───────────┼───────────┤
│ 2025-12-29 10:30:45  │ "explain SOAR architecture"      │ $0.0234   │ completed │
│ 2025-12-29 10:32:12  │ "list all functions in aurora"   │ $0.0156   │ completed │
│ 2025-12-29 10:35:01  │ "refactor authentication system" │ $0.0000   │ blocked   │
│ 2025-12-29 10:36:22  │ "what is ACT-R?"                 │ $0.0089   │ completed │
└──────────────────────┴──────────────────────────────────┴───────────┴───────────┘

Total Queries: 4 (3 completed, 1 blocked)
Total Cost: $0.0479
```

**Filtering Options:**
```bash
# Show last 10 queries
aur budget history --limit 10

# Show only blocked queries
aur budget history --status blocked

# Show queries from today
aur budget history --today
```

### Budget Enforcement

AURORA automatically enforces budget limits before making API calls.

**Example: Budget Exceeded**
```bash
# Set low budget for demo
aur budget set 0.01

# Attempt expensive operation (e.g., via aur headless with large prompt)
aur headless expensive_task.md
```

**Output:**
```
✗ Budget limit exceeded

Cannot execute query:
  Current spending:  $0.0000
  Budget limit:      $0.0100
  Estimated cost:    $0.0234

To continue:
  1. Increase budget: aur budget set 1.00
  2. Or reset spending: aur budget reset

Current usage: 0.0% of budget
```

### Budget Best Practices

**1. Set Realistic Budget**
```bash
# For testing and exploration
aur budget set 10.00

# For daily development work
aur budget set 50.00

# For intensive research projects
aur budget set 200.00
```

**2. Monitor Usage Regularly**
```bash
# Check before large queries
aur budget show

# Review history weekly
aur budget history --limit 50
```

**3. Reset at Billing Cycle**
```bash
# Monthly reset (add to cron/scheduler)
aur budget reset
```

**4. Monitor Budget for Headless Operations**
```bash
# Check remaining budget before expensive operations
aur budget show
```

### Configuration

Budget settings stored in: `~/.aurora/budget_tracker.json`

**Format:**
```json
{
  "monthly_limit_usd": 15.0,
  "total_spent_usd": 2.345,
  "query_history": [
    {
      "timestamp": "2025-12-29T10:30:45Z",
      "query": "explain SOAR architecture",
      "cost_usd": 0.0234,
      "status": "completed",
      "model": "claude-sonnet-4-20250514",
      "tokens": {
        "input": 450,
        "output": 320
      }
    }
  ],
  "last_reset": "2025-12-01T00:00:00Z"
}
```

**Direct Editing (Not Recommended):**
```bash
# Backup first
cp ~/.aurora/budget_tracker.json ~/.aurora/budget_tracker.json.backup

# Edit carefully
nano ~/.aurora/budget_tracker.json

# Verify JSON syntax
python -m json.tool ~/.aurora/budget_tracker.json
```

**Better Approach:** Use `aur budget` commands for safe updates.

### FAQ

**Q: When is cost calculated?**

A:
1. **Before query**: Estimated cost based on query length and expected response
2. **After query**: Actual cost recorded based on API response tokens
3. Budget check happens BEFORE API call (prevents overage)

**Q: What happens if actual cost exceeds estimate?**

A: Query completes (already paid), but actual cost recorded. Next query may be blocked if total exceeds budget.

**Q: Does budget reset automatically?**

A: No. Use `aur budget reset` manually or schedule with cron/task scheduler.

**Q: Can I set different budgets per project?**

A: Budget is per-user (`~/.aurora/budget_tracker.json`). For per-project budgets, use separate user accounts or manually track.

**Q: What if I delete budget_tracker.json?**

A: Aurora recreates it with default limit ($15.00) and zero spending. History lost.

**Q: Do memory commands count toward budget?**

A: No. Only `aur headless` command that calls LLM APIs counts toward budget. `aur mem index/search/stats` are free.

---

## Headless Mode

Run autonomous experiments without human intervention.

### Basic Usage

```bash
aur headless experiment.md
```

### Custom Budget and Iterations

```bash
aur headless experiment.md --budget 10.0 --max-iter 20
```

### Custom Branch and Scratchpad

```bash
aur headless experiment.md --branch test-1 --scratchpad log.md
```

### Dry Run (Validation Only)

```bash
aur headless experiment.md --dry-run
```

### Show Scratchpad After Completion

```bash
aur headless experiment.md --show-scratchpad
```

### Prompt File Format

Create a markdown file with this structure:

**experiment.md:**
```markdown
## Goal
Refactor the authentication system to use JWT tokens instead of session cookies.

## Success Criteria
- JWT token generation implemented
- Token validation middleware created
- All tests passing
- No breaking changes to API

## Constraints
- Must maintain backward compatibility for 2 weeks
- Budget: $5.00
- Max iterations: 10

## Context
The current system uses server-side sessions stored in Redis.
Migration plan should include:
1. Implement JWT generation
2. Add token validation
3. Update tests
4. Document migration guide
```

### Safety Features

**Git Branch Enforcement:**
- Default: Requires `headless` branch (not `main`/`master`)
- Override: Use `--allow-main` (⚠️ DANGEROUS)

**Budget Limits:**
- Default: $5.00
- Stops execution when exceeded
- Prevents runaway costs

**Max Iterations:**
- Default: 10 iterations
- Prevents infinite loops
- Each iteration tracked in scratchpad

**Scratchpad Audit Trail:**
- Full execution history
- Iteration-by-iteration progress
- Cost tracking
- Decision rationale

---

## Health Checks & Diagnostics

AURORA provides built-in diagnostic tools to verify your installation and identify configuration issues.

### `aur doctor` - Check System Health

The `aur doctor` command performs comprehensive health checks across 4 categories:

```bash
aur doctor
```

**Health Check Categories:**

1. **Core System** (Critical)
   - ✓ Config file exists (`~/.aurora/config.json`)
   - ✓ Aurora directory exists (`~/.aurora/`)
   - ✓ Permissions are correct

2. **Code Analysis** (Important)
   - ✓ Tree-sitter parser available
   - ✓ Python language support installed

3. **Search & Retrieval** (Important)
   - ✓ Vector database accessible
   - ✓ Embedding provider configured

4. **Configuration** (Info)
   - ✓ API keys configured (Anthropic/OpenAI)
   - ✓ LLM provider set

**Example Output:**

```
🏥 AURORA Health Check

Core System
  ✓ Config file exists: ~/.aurora/config.json
  ✓ Aurora home directory exists
  ✓ Permissions correct (0600)

Code Analysis
  ✓ Tree-sitter available
  ✓ Python language support installed

Search & Retrieval
  ✓ Vector database accessible
  ⚠ No embeddings found (database empty)
    → Run 'aur mem index .' to create embeddings

Configuration
  ✓ Anthropic API key configured
  ✓ LLM provider: anthropic

Health Check: 7 passed, 1 warning, 0 failed
```

**Exit Codes:**

- `0`: All checks passed (success)
- `1`: Warnings detected (partial functionality)
- `2`: Critical failures (requires attention)

### `aur doctor --fix` - Auto-Repair Issues

The `--fix` flag automatically repairs common issues:

```bash
aur doctor --fix
```

**Fixable Issues:**

- Missing `~/.aurora/` directory → Creates directory
- Missing config file → Creates default config
- Missing database file → Creates empty database
- Incorrect permissions → Sets secure permissions (0600)
- Missing cache directory → Creates cache

**Manual Issues** (requires user action):

- Missing API keys → Set via environment variable
- Tree-sitter not installed → Run `pip install tree-sitter tree-sitter-python`
- Not in Git repository → Run `git init` (optional)

**Example Session:**

```
🏥 AURORA Health Check with Auto-Repair

Core System
  ✗ Config file missing
    → Creating ~/.aurora/config.json
  ✓ Config file created

  ✗ Database file missing
    → Creating ~/.aurora/memory.db
  ✓ Database created

The following issues require manual attention:
  ⚠ API key not configured
    → Set ANTHROPIC_API_KEY environment variable

Automatic repairs: 2 fixed
Manual actions required: 1

Run 'aur doctor' again to verify fixes.
```

**Safety:**

- All fixes are idempotent (safe to run multiple times)
- No data loss (only creates missing files/directories)
- User confirmation before making changes

### `aur version` - Show Version Information

Display AURORA version and installation details:

```bash
aur version
```

**Example Output:**

```
AURORA Version Information:
  Version: 0.2.0
  Git Hash: 26b54e0
  Python: 3.10.12
  Install Path: /home/user/.local/lib/python3.10/site-packages/aurora_cli
```

**Fields:**

- **Version**: Aurora package version
- **Git Hash**: Commit hash (if installed from Git repo)
- **Python**: Python interpreter version
- **Install Path**: Location of Aurora CLI package

---

## Graceful Degradation

AURORA gracefully handles missing dependencies by falling back to reduced functionality with clear warnings.

### Degraded Modes

**1. Tree-sitter Unavailable (Code Parsing)**

**Symptom:**
```
WARNING: Tree-sitter unavailable - using text chunking (reduced quality)
→ Install with: pip install tree-sitter tree-sitter-python
```

**Impact:**
- Falls back to simple 50-line text chunks
- No function/class-level granularity
- Reduced search precision

**Restore:**
```bash
pip install tree-sitter tree-sitter-python
```

**2. Git Not Available (Base-Level Activation)**

**Symptom:**
```
WARNING: Git disabled via AURORA_SKIP_GIT - BLA will use default activation (0.5)
→ Unset AURORA_SKIP_GIT to enable Git-based activation
```

or (in non-Git directory):
```
DEBUG: Git blame failed for file.py - not a Git repository
```

**Impact:**
- Uses default activation score (0.5) instead of Git-based frequency
- No commit history analysis
- All functions treated equally

**Restore:**
- Ensure you're in a Git repository: `git init`
- Or use Git-tracked project

### Environment Variable Overrides

You can explicitly disable features for testing or restricted environments:

| Variable | Effect | Use Case |
|----------|--------|----------|
| `AURORA_SKIP_TREESITTER=1` | Force text chunking fallback | Test degraded parsing, CI without tree-sitter |
| `AURORA_SKIP_GIT=1` | Disable Git-based activation | Test without Git, non-repo environments |

**Example:**

```bash
# Test without tree-sitter
AURORA_SKIP_TREESITTER=1 aur mem index .

# Test without Git
AURORA_SKIP_GIT=1 aur mem search "test query"

# Test with all features disabled
AURORA_SKIP_TREESITTER=1 AURORA_SKIP_GIT=1 aur mem index .
```

### Recovery Steps

**General Recovery Process:**

1. **Run health check:**
   ```bash
   aur doctor
   ```

2. **Apply automatic fixes:**
   ```bash
   aur doctor --fix
   ```

3. **Address manual issues** (see health check output)

4. **Verify recovery:**
   ```bash
   aur doctor
   # Should show: "Health Check: All checks passed"
   ```

---

## Troubleshooting

**First Step:** Always run `aur doctor` to diagnose issues automatically.

```bash
aur doctor
```

If automatic diagnosis doesn't resolve the issue, see specific troubleshooting steps below.

### Issue: "ANTHROPIC_API_KEY not found"

**Symptom:**
```
Error: ANTHROPIC_API_KEY not found.
```

**Important:** This error only occurs with standalone CLI commands like `aur headless`. MCP tools inside Claude Code CLI do NOT require API keys.

**Solution for CLI commands:**
```bash
# Option 1: Set environment variable (recommended)
export ANTHROPIC_API_KEY=sk-ant-...

# Option 2: Run init command
aur init

# Option 3: Add to config file
nano ~/.aurora/config.json
```

**Get API Key:**
- Visit: https://console.anthropic.com
- Generate new API key
- Copy and store securely

**Alternative:** Use MCP tools inside Claude Code CLI (no API key needed)
- See [MCP Setup Guide](../MCP_SETUP.md)

---

### Issue: "Memory store is locked"

**Symptom:**
```
Error: Memory store is locked.
```

**Cause:**
Another AURORA process is using the database.

**Solution:**
```bash
# 1. Check for other AURORA processes
ps aux | grep aur

# 2. Kill hung processes
kill <pid>

# 3. If stuck, remove lock file
rm aurora.db-wal
rm aurora.db-shm
```

---

### Issue: "Rate limit exceeded"

**Symptom:**
```
Error: Rate limit exceeded. Retry in 5s or upgrade API tier.
```

**Cause:**
Too many API requests in short time period.

**Solution:**
```bash
# 1. Wait a few seconds (automatic retry enabled)
# AURORA will retry with exponential backoff

# 2. Upgrade API tier at console.anthropic.com
```

---

### Issue: Slow memory searches

**Symptom:**
Memory searches take >5 seconds to complete.

**Solution:**
```bash
# 1. Check index size
aur mem stats

# 2. Reduce search limit
aur mem search "query" --limit 5

# 3. Index memory for faster context retrieval
aur mem index

# 4. Check memory database size
aur mem stats
```

---

### Issue: No memory results

**Symptom:**
```
Found 0 results for 'query'
```

**Cause:**
Memory not indexed or query too specific.

**Solution:**
```bash
# 1. Index codebase
aur mem index .

# 2. Verify indexing worked
aur mem stats

# 3. Try broader search query
aur mem search "login"  # Instead of "validate_login_credentials"

# 4. Check database exists
ls -lh aurora.db
```

---

### Issue: Configuration errors

**Symptom:**
```
Error: Configuration file syntax error.
```

**Solution:**
```bash
# 1. Validate JSON syntax
python -m json.tool ~/.aurora/config.json

# 2. Use online validator
# Visit: https://jsonlint.com

# 3. Recreate config
rm ~/.aurora/config.json
aur init

# 4. Check file permissions
chmod 600 ~/.aurora/config.json
chmod 700 ~/.aurora/
```

---

## Command Reference

### Global Options

```bash
aur --verbose    # Enable verbose logging
aur --debug      # Enable debug logging
aur --version    # Show version
aur --help       # Show help
```

### Commands

#### `aur init`

Initialize configuration and optionally index codebase.

```bash
aur init
```

**Options:** None

**Interactive:**
- Prompts for API key
- Prompts to index directory
- Creates `~/.aurora/config.json`

---

#### `aur mem index`

Index code files into memory store.

```bash
aur mem index [PATH] [OPTIONS]
```

**Arguments:**
- `PATH`: Directory to index (default: `.`)

**Options:**
- `--db-path PATH`: Database location (default: `./aurora.db`)

**Examples:**
```bash
aur mem index
aur mem index /path/to/project
aur mem index . --db-path ~/.aurora/memory.db
```

---

#### `aur mem search`

Search memory for relevant chunks.

```bash
aur mem search QUERY [OPTIONS]
```

**Arguments:**
- `QUERY`: Search query (required)

**Options:**
- `--limit N, -n N`: Max results (default: 5)
- `--format FORMAT, -f FORMAT`: Output format: `rich`, `json` (default: `rich`)
- `--show-content, -c`: Show content preview
- `--db-path PATH`: Database location (default: `./aurora.db`)

**Examples:**
```bash
aur mem search "authentication"
aur mem search "database" --limit 10 --show-content
aur mem search "login" --format json
```

---

#### `aur mem stats`

Display memory store statistics.

```bash
aur mem stats [OPTIONS]
```

**Options:**
- `--db-path PATH`: Database location (default: `./aurora.db`)

**Examples:**
```bash
aur mem stats
aur mem stats --db-path ~/.aurora/memory.db
```

---

#### `aur agents`

Discover and manage AI coding assistant agents.

```bash
aur agents COMMAND [OPTIONS]
```

**Commands:**

##### `aur agents list`

List all discovered agents grouped by category.

```bash
aur agents list [OPTIONS]
```

**Options:**
- `-c, --category [eng|qa|product|general]`: Filter by category
- `-f, --format [rich|simple]`: Output format (default: rich)

**Examples:**
```bash
aur agents list
aur agents list --category qa
aur agents list --format simple
```

##### `aur agents search`

Search agents by keyword.

```bash
aur agents search KEYWORD
```

**Arguments:**
- `KEYWORD`: Search term (required)

**Examples:**
```bash
aur agents search "test"
aur agents search "code review"
```

##### `aur agents show`

Display full details for a specific agent.

```bash
aur agents show AGENT_ID
```

**Arguments:**
- `AGENT_ID`: Agent identifier (required)

**Examples:**
```bash
aur agents show qa-test-architect
aur agents show full-stack-dev
```

##### `aur agents refresh`

Force regenerate the agent manifest.

```bash
aur agents refresh
```

**Examples:**
```bash
aur agents refresh
```

---

#### `aur plan`

Plan management commands for creating, viewing, listing, and archiving development plans.

Plans use a four-file structure:
- `plan.md`: Human-readable plan overview
- `prd.md`: Product requirements document
- `tasks.md`: Implementation task list with file paths
- `agents.json`: Machine-readable plan data with agent assignments

```bash
aur plan COMMAND [OPTIONS]
```

**Commands:**

##### `aur plan create`

Create a new plan with SOAR-based goal decomposition.

```bash
aur plan create GOAL [OPTIONS]
```

**Arguments:**
- `GOAL`: Clear description of what you want to achieve (10-500 characters)

**Options:**
- `-c, --context FILE`: Context files for informed decomposition (can be used multiple times)
- `--no-decompose`: Skip SOAR decomposition (create single-task plan)
- `-f, --format [rich|json]`: Output format (default: rich)
- `--no-auto-init`: Disable automatic initialization if `.aurora` doesn't exist
- `-y, --yes`: Skip confirmation prompt and proceed with plan generation
- `--non-interactive`: Non-interactive mode (alias for --yes)

**Checkpoint Flow:**

When creating a plan, AURORA displays a decomposition summary before generating files:

```
╭───────────────────────── Plan Decomposition Summary ─────────────────────────╮
│ Goal: Implement OAuth2 authentication with JWT tokens                        │
│                                                                              │
│ Subgoals: 3                                                                  │
│                                                                              │
│    Plan and design approach (@holistic-architect)                            │
│    Implement solution (@full-stack-dev)                                      │
│    Test and verify (@qa-test-architect)                                      │
│                                                                              │
│ Agents: 3 assigned                                                           │
│ Files: 3 resolved (avg confidence: 0.85)                                     │
│ Complexity: MODERATE                                                         │
│ Source: soar                                                                 │
╰──────────────────────────────────────────────────────────────────────────────╯

Proceed with plan generation? (Y/n):
```

**What the summary shows:**
- **Goal**: Your original goal text
- **Subgoals**: Number of decomposed subgoals with agent assignments
- **Agents**: Count of agents assigned (shows gaps if any)
- **Files**: Number of resolved file paths with average confidence score
- **Complexity**: SIMPLE, MODERATE, or COMPLEX based on analysis
- **Source**: `soar` (SOAR decomposition) or `heuristic` (fallback)

**Graceful Degradation:**

AURORA automatically falls back to heuristic decomposition if SOAR is unavailable:
- Missing LLM client → Uses rule-based decomposition
- API timeout → Falls back after 30 seconds
- Network issues → Continues with heuristic approach
- Plan still generates successfully with `decomposition_source: "heuristic"`

**File Path Resolution:**

If memory is indexed (`aur mem index`), AURORA resolves file paths for each subgoal:
- **High confidence (≥0.8)**: `src/auth/module.py lines 1-50`
- **Medium confidence (0.6-0.8)**: `src/auth/jwt.py lines 20-80 (suggested)`
- **Low confidence (<0.6)**: `src/core/utils.py lines 5-30 (low confidence)`

If memory is not indexed:
- Shows warning: "Memory not indexed. Run 'aur mem index .' for code-aware tasks."
- Generates generic paths: `src/<domain>/<task-slug>.py`
- All paths marked with low confidence (0.1)

**Examples:**
```bash
# Create authentication plan
aur plan create "Implement OAuth2 authentication with JWT tokens"

# Create with context files
aur plan create "Add caching layer" --context src/api.py --context src/config.py

# Skip decomposition (single task)
aur plan create "Fix bug in login form" --no-decompose

# Non-interactive mode (CI/CD)
aur plan create "Add rate limiting" --yes

# JSON output
aur plan create "Add user dashboard" --format json
```

##### `aur plan list`

List active or archived plans.

```bash
aur plan list [OPTIONS]
```

**Options:**
- `--archived`: Show archived plans instead of active
- `--all`: Show both active and archived plans
- `-f, --format [rich|json]`: Output format (default: rich)

**Examples:**
```bash
aur plan list                    # List active plans
aur plan list --archived         # List archived plans
aur plan list --all              # List all plans
aur plan list --format json      # JSON output
```

##### `aur plan view`

Display plan details with file status.

```bash
aur plan view PLAN_ID [OPTIONS]
```

**Arguments:**
- `PLAN_ID`: Full plan ID or partial match

**Options:**
- `--archived`: View archived plan
- `-f, --format [rich|json]`: Output format (default: rich)

**Examples:**
```bash
aur plan view 0001-oauth-auth
aur plan view oauth              # Partial match
aur plan view 0001-oauth --archived
aur plan view 0001-oauth --format json
```

##### `aur plan archive`

Archive a completed plan.

```bash
aur plan archive PLAN_ID [OPTIONS]
```

**Arguments:**
- `PLAN_ID`: Full plan ID or partial match

**Options:**
- `-y, --yes`: Skip confirmation prompt

Moves the plan from `active/` to `archive/` with timestamp prefix (e.g., `2026-01-05-0001-oauth-auth`).
Updates plan status and records duration from creation.

**Examples:**
```bash
aur plan archive 0001-oauth-auth            # With confirmation
aur plan archive 0001-oauth -y              # Skip confirmation
```

---

#### `aur headless`

Run autonomous experiment in headless mode.

```bash
aur headless PROMPT_PATH [OPTIONS]
```

**Arguments:**
- `PROMPT_PATH`: Path to experiment prompt file (required)

**Options:**
- `--scratchpad PATH, -s PATH`: Scratchpad file location
- `--budget FLOAT, -b FLOAT`: Max budget in USD (default: 5.0)
- `--max-iter INT, -m INT`: Max iterations (default: 10)
- `--branch NAME`: Required git branch (default: `headless`)
- `--allow-main`: ⚠️ DANGEROUS: Allow running on main/master
- `--dry-run`: Validate configuration only
- `--show-scratchpad`: Display scratchpad after completion

**Examples:**
```bash
aur headless experiment.md
aur headless experiment.md --budget 10.0 --max-iter 20
aur headless experiment.md --dry-run
aur headless experiment.md --show-scratchpad
```

---

## Performance Expectations

### Direct LLM Queries

- **Latency**: <2 seconds
- **Cost**: ~$0.002-0.005 per query
- **Use Case**: Simple informational queries

### AURORA Queries (Simple)

- **Latency**: <5 seconds
- **Cost**: ~$0.005-0.015 per query
- **Use Case**: Queries requiring memory context

### AURORA Queries (Complex)

- **Latency**: <15 seconds
- **Cost**: ~$0.015-0.050 per query
- **Use Case**: Multi-step reasoning, code generation

### Indexing

- **100 files**: <30 seconds
- **1,000 files**: <5 minutes
- **Database size**: ~50KB per file

---

## Best Practices

### 1. Index Before Querying

```bash
# Index project for semantic search
aur mem index

# Then search with context-aware retrieval
aur mem search "authentication flow"
```

### 2. Use MCP Tools from Claude Code

```bash
# For LLM-powered queries, use aurora_query MCP tool from within Claude Code
# No API key required, no additional costs beyond Claude subscription
```

### 3. Prefer Environment Variables for API Keys

```bash
# Secure: Doesn't persist key in files
export ANTHROPIC_API_KEY=sk-ant-...

# Only needed for aur headless command
```

### 4. Monitor Budget for Headless Operations

```bash
# Check budget before running expensive headless operations
aur budget show
```

### 5. Monitor Costs in Headless Mode

```bash
# Set conservative budget
aur headless experiment.md --budget 5.0 --max-iter 10

# Review scratchpad for cost tracking
cat experiment_scratchpad.md
```

---

## Next Steps

- **Learn More**: See [ERROR_CATALOG.md](ERROR_CATALOG.md) for detailed error solutions
- **Quick Start**: See [QUICK_START.md](QUICK_START.md) for a 5-minute tutorial
- **Troubleshooting**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues
- **API Reference**: See main [README.md](../../README.md) for Python API documentation

---

**Questions or Issues?**

- GitHub Issues: https://github.com/aurora-project/aurora/issues
- Documentation: https://docs.aurora.ai
- Community: https://discord.gg/aurora
