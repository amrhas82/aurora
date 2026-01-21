# Aurora Tools & Configuration Guide

Complete reference for Aurora's tooling ecosystem, architecture, workflows, and configurator system.

**Last Updated:** 2026-01-16
**Version:** 0.9.1+

---

## Table of Contents

### Part I: User Guide
1. [Overview](#overview)
2. [Tool Ecosystem](#tool-ecosystem)
3. [Core Systems](#core-systems)
4. [Command Reference](#command-reference)
5. [Planning Flow](#planning-flow)
6. [Advanced Workflows](#advanced-workflows)
7. [Configuration](#configuration)
8. [Debugging & Troubleshooting](#debugging--troubleshooting)

### Part II: Developer Guide
9. [Configurator System](#configurator-system)
10. [Adding New Tools](#adding-new-tools)
11. [Modifying Templates](#modifying-templates)
12. [Testing](#testing)
13. [Release Process](#release-process)

### Part III: Reference
14. [Best Practices](#best-practices)
15. [FAQ](#faq)

---

# Part I: User Guide

## Overview

Aurora is a cognitive architecture system combining memory, reasoning, and agent orchestration for AI-powered development workflows.

### Key Features

- **Memory System**: ACT-R-based code indexing and retrieval
- **Reasoning Engine**: SOAR 9-phase reasoning pipeline
- **Agent Orchestration**: Multi-agent task execution
- **Planning Tools**: Goal decomposition and task generation
- **CLI Integration**: Works with 20+ CLI tools (claude, cursor, etc.)
- **Slash Commands**: Automatically generates commands for supported tools

### Architecture

```
+-------------------------------------------------------------+
|                     Aurora Tooling Stack                     |
+-------------------------------------------------------------+
|  CLI Commands (aur)                                          |
|    +- aur goals     -+                                       |
|    +- aur soar      -+- Use CLIPipeLLMClient                |
|    +- aur spawn     -+                                       |
|    +- aur mem       -+                                       |
|    +- aur agents                                             |
+-------------------------------------------------------------+
|  Core Systems                                                |
|    +- Memory (ACT-R): Code indexing & retrieval             |
|    +- SOAR: 9-phase reasoning pipeline                      |
|    +- Spawner: Parallel agent execution                     |
|    +- Planning: Goal decomposition & agent matching         |
|    +- Discovery: Agent capability matching                  |
+-------------------------------------------------------------+
|  Integration Layer                                           |
|    +- CLIPipeLLMClient: CLI-agnostic LLM interface          |
|    +- ManifestManager: Agent discovery & registration       |
|    +- TaskParser: Markdown task file parsing                |
|    +- ConfigManager: Multi-tier configuration               |
|    +- SlashConfigurator: Command generation (20+ tools)     |
+-------------------------------------------------------------+
|  External Tools (20+ supported)                              |
|    +- claude (CLI), cursor, windsurf, cline, etc.           |
+-------------------------------------------------------------+
```

---

## Tool Ecosystem

### Command Overview

| Tool | Type | Purpose | Integration |
|------|------|---------|-------------|
| `aur init` | Setup | Initialize project with slash commands | SlashConfigurator |
| `aur goals` | Planning | Goal decomposition | CLIPipeLLMClient |
| `aur soar` | Reasoning | SOAR research pipeline | CLIPipeLLMClient |
| `aur spawn` | Execution | Parallel task execution | Spawner + CLI tools |
| `aur headless` | Autonomous | Claude loop until goal done | Subprocess + scratchpad |
| `aur mem` | Memory | Code indexing/search | ACT-R + SQLite |
| `aur agents` | Discovery | Agent management | ManifestManager |

### Tool Selection Matrix

```
Task: "I have a complex question"
  +-> Use: aur soar
      Why: SOAR handles research, decomposition, parallel agents

Task: "I want to plan a feature"
  +-> Use: aur goals -> /plan -> aur implement
      Why: Planning flow provides structured approach

Task: "I have a task list to execute"
  +-> Use: aur spawn
      Why: Parallel execution for independent tasks

Task: "I need to find code"
  +-> Use: aur mem search
      Why: Semantic + keyword search of indexed code

Task: "I need slash commands in my IDE"
  +-> Use: aur init
      Why: Generates commands for 20+ tools
```

---

## Core Systems

### 1. Memory System (ACT-R)

**Purpose**: Index and retrieve code with semantic understanding.

**Commands**:
```bash
# Index entire project
aur mem index .

# Index specific directory
aur mem index packages/cli/

# Force rebuild (clears cache)
aur mem index . --force

# Search indexed code
aur mem search "authentication flow"

# Search with filters
aur mem search "payment" --limit 10 --type function
```

**Storage**:
- Database: `.aurora/memory.db`
- Cache: `~/.aurora/cache/`
- Embeddings: Stored in SQLite

**Search Types**:
- `function` - Functions only
- `class` - Classes only
- `method` - Methods only
- `kb` - Markdown/knowledge base
- `code` - All code chunks

### 2. SOAR Reasoning Engine

**Purpose**: 9-phase reasoning for complex queries with parallel research.

**The 9 Phases**:
```
1. ASSESS     -> Determine query complexity (SIMPLE/MEDIUM/COMPLEX/CRITICAL)
2. RETRIEVE   -> Search memory for relevant context
3. DECOMPOSE  -> Break into sub-questions (if complex)
4. VERIFY     -> Validate decomposition quality
5. ROUTE      -> Assign agents to sub-questions
6. COLLECT    -> Execute agents in parallel (spawn_parallel)
7. SYNTHESIZE -> Combine results coherently
8. RECORD     -> Store reasoning trace
9. RESPOND    -> Format final answer
```

**Complexity Routing**:
```python
SIMPLE (score ≤ 11):
  -> Single-step reasoning, no spawning

MEDIUM (score 12-28):
  -> Multi-step with subgoals, some spawning

COMPLEX (score ≥ 29):
  -> Full decomposition, parallel research

CRITICAL (score ≥ 35):
  -> High-stakes with adversarial verification
```

**Usage**:
```bash
# Simple query
aur soar "What is ACT-R?"

# Complex query (triggers parallel agents)
aur soar "Compare React, Vue, and Angular"

# Verbose mode (show all phases)
aur soar "How does authentication work?" --verbose
```

### 3. Spawner System

**Purpose**: Parallel and sequential agent execution with CLI tool integration.

**Functions**:
```python
# Single agent spawn
result = await spawn(
    prompt="Task description",
    tool="claude",
    model="sonnet",
    agent="@code-developer",
    timeout=300
)

# Parallel spawning
results = await spawn_parallel(
    tasks=[SpawnTask(...), ...],
    max_concurrent=5
)
```

**Tool Resolution Order**:
```
1. CLI flag: --tool cursor
   ↓ (if not provided)
2. Environment variable: AURORA_SPAWN_TOOL=cursor
   ↓ (if not set)
3. Config file: spawn.default_tool = "cursor"
   ↓ (if not set)
4. Default: "claude"
```

**Task File Format**:
```markdown
# My Tasks

- [ ] 1. Implement authentication endpoint
<!-- agent: code-developer -->
<!-- timeout: 600 -->

- [ ] 2. Write integration tests
<!-- agent: quality-assurance -->
<!-- depends: 1 -->
```

### 4. Planning System

**Purpose**: Structured goal decomposition and task generation.

**Components**:
- **GoalDecomposer**: Memory search + LLM decomposition
- **AgentRecommender**: Keyword + LLM fallback matching
- **GapDetector**: Missing agent capability detection
- **TaskGenerator**: PRD and tasks.md creation

**Workflow**:
```bash
# 1. Decompose goal
aur goals "Add user authentication"

# 2. Review goals.json
cd .aurora/plans/0001-add-user-auth/
$EDITOR goals.json

# 3. Generate PRD and tasks (in Claude Code)
/plan

# 4. Execute tasks
aur spawn tasks.md
```

---

## Command Reference

### aur init - Project Setup

**Purpose**: Initialize Aurora in a project and generate slash commands for supported tools.

**Syntax**:
```bash
aur init [OPTIONS]
```

**Options**:
```
--tools TEXT          Comma-separated tools (default: all)
--config              Regenerate config files only
--force               Overwrite existing files
--help                Show help message
```

**Examples**:
```bash
# Initialize with all tools (20+)
aur init

# Initialize with specific tools
aur init --tools=claude,cursor,windsurf

# Regenerate commands only
aur init --config --tools=claude

# Force overwrite
aur init --force
```

**What It Creates**:
```
.claude/commands/aur/
  +- search.md
  +- get.md
  +- plan.md
  +- implement.md
  +- archive.md

.cursor/commands/
  +- aurora-search.md
  +- aurora-get.md
  ... (same 5 commands)

.windsurf/commands/
  +- aurora-search.md
  ... (same 5 commands)

... (for all selected tools)
```

**Supported Tools** (20):
1. Claude Code (`.claude/commands/aur/`)
2. Cursor (`.cursor/commands/`)
3. Windsurf (`.windsurf/commands/`)
4. Cline (`.cline/commands/`)
5. GitHub Copilot (`.github/copilot/`)
6. Codex (`.codex/commands/`)
7. OpenCode (`.opencode/commands/`)
8. Amazon Q (`.amazonq/commands/`)
9. CodeBuddy (`.codebuddy/commands/`)
10. Auggie (`.auggie/commands/`)
11. Costrict (`.costrict/commands/`)
12. Crush (`.crush/commands/`)
13. Antigravity (`.antigravity/commands/`)
14. Gemini CLI (`.gemini/commands/aurora/`) - TOML format
15. Qwen (`.qwen/commands/`) - TOML format
16. KiloCode (`.kilocode/commands/`) - TOML format
17. RooCode (`.roocode/commands/`) - TOML format
18. Qoder (`.qoder/commands/`) - TOML format
19. iFlow (`.iflow/commands/`) - TOML format
20. Factory (`.factory/commands/`)

### aur goals - Goal Decomposition

**Syntax**:
```bash
aur goals [OPTIONS] GOAL
```

**Options**:
```
--tool, -t TEXT         CLI tool to use (default: claude)
--model, -m [sonnet|opus] Model to use (default: sonnet)
--context PATH          Add context file (multiple allowed)
--no-decompose          Skip decomposition (single task)
--yes, -y               Skip confirmation prompts
--verbose, -v           Show detailed progress
```

**Examples**:
```bash
# Basic usage
aur goals "Implement OAuth2 authentication"

# With context files
aur goals "Add caching layer" \
  --context src/api.py \
  --context src/database.py

# Skip confirmation (CI/CD)
aur goals "Fix login bug" --yes

# Use specific tool
aur goals "Optimize queries" --tool cursor --model opus
```

### aur soar - SOAR Reasoning

**Syntax**:
```bash
aur soar [OPTIONS] QUERY
```

**Options**:
```
--tool, -t TEXT         CLI tool (default: claude)
--model, -m [sonnet|opus] Model (default: sonnet)
--verbose, -v           Show all 9 phases
--stream                Stream output
--save PATH             Save result to file
```

**Examples**:
```bash
# Simple query
aur soar "How does authentication work?"

# Complex research
aur soar "Compare React, Vue, Angular"

# Verbose mode
aur soar "Explain microservices" --verbose

# Save output
aur soar "Document the API" --save api-docs.md
```

### aur spawn - Task Execution

**Syntax**:
```bash
aur spawn [OPTIONS] [TASK_FILE]
```

**Options**:
```
--parallel/--no-parallel  Enable/disable parallel (default: parallel)
--sequential             Force sequential execution
--dry-run                Validate without executing
--verbose, -v            Show detailed progress
--max-concurrent INT     Max parallel tasks (default: 5)
--timeout INT            Task timeout seconds (default: 300)
```

**Examples**:
```bash
# Execute tasks.md in parallel
aur spawn

# Sequential execution
aur spawn tasks.md --sequential

# Limit parallelism
aur spawn tasks.md --max-concurrent 3

# Custom timeout
aur spawn tasks.md --timeout 600
```

### aur mem - Memory Commands

**Index Command**:
```bash
# Index current directory
aur mem index .

# Force rebuild
aur mem index . --force

# With patterns
aur mem index . --include "*.py" --exclude "node_modules"
```

**Search Command**:
```bash
# Basic search
aur mem search "authentication"

# Filter by type
aur mem search "auth" --type function

# Control results
aur mem search "payment" --limit 10 --min-score 0.5

# Show content
aur mem search "api" --show-content
```

### aur agents - Agent Management

```bash
# List all agents
aur agents list

# Show agent details
aur agents show code-developer

# List by capability
aur agents list --capability testing

# JSON output
aur agents list --json
```

---

## Planning Flow

Complete workflow from goal to execution.

### Stage 1: Goal Decomposition (Terminal)

```bash
aur goals "Implement user authentication system"
```

**What Happens**:
1. Memory search finds relevant context
2. Goal decomposed into 3-7 subgoals
3. Agents matched to each subgoal
4. Gaps detected (missing capabilities)
5. User reviews `goals.json` in editor
6. Directory created: `.aurora/plans/0001-implement-user-auth/`

**goals.json Output**:
```json
{
  "id": "0001-implement-user-auth",
  "title": "Implement user authentication system",
  "status": "ready_for_planning",
  "memory_context": [
    {"file": "src/auth/login.py", "relevance": 0.85}
  ],
  "subgoals": [
    {
      "id": "sg-1",
      "title": "Implement JWT token generation",
      "agent": "@code-developer",
      "confidence": 0.89,
      "dependencies": []
    }
  ]
}
```

### Stage 2: PRD and Task Generation (Claude Code)

```bash
# In Claude Code, run:
/plan
```

**What Happens**:
1. Reads `goals.json`
2. Generates `prd.md` with requirements
3. Generates `tasks.md` with agent metadata
4. Generates `specs/` directory

**tasks.md Format**:
```markdown
# Implementation Tasks

- [ ] 1. Implement JWT token generation
<!-- agent: code-developer -->
<!-- goal: sg-1 -->

- [ ] 2. Create login endpoint
<!-- agent: code-developer -->
<!-- goal: sg-2 -->
<!-- depends: 1 -->
```

### Stage 3: Task Execution

**Option A: Sequential (Claude Code)**:
```bash
aur implement
```

**Option B: Parallel (Terminal)**:
```bash
aur spawn tasks.md --verbose
```

---

## Advanced Workflows

### Workflow 1: Feature Implementation with Traceability

```bash
# 1. Index codebase
aur mem index .

# 2. Research patterns
aur soar "How is API routing implemented?" --verbose

# 3. Create goals
aur goals "Add user profile API" \
  --context src/api/routes.py

# 4. Generate PRD and tasks
# In Claude Code: /plan

# 5. Execute
aur spawn tasks.md --verbose

# 6. Verify
aur mem index .
aur soar "Explain the user profile API"
```

### Workflow 2: Bug Investigation

```bash
# 1. Search context
aur mem search "login authentication error"

# 2. Investigate
aur soar "Why might authentication fail?" --verbose

# 3. Fix
aur goals "Fix authentication failures" \
  --context src/auth/login.py \
  --no-decompose

# 4. Execute
aur spawn tasks.md --sequential
```

### Workflow 3: Multi-Agent Collaboration

```markdown
# tasks.md with explicit assignments

- [ ] 1. Research real-time updates
<!-- agent: researcher -->

- [ ] 2. Design WebSocket API
<!-- agent: architect -->

- [ ] 3. Implement server
<!-- agent: code-developer -->
<!-- depends: 2 -->

- [ ] 4. Write tests
<!-- agent: quality-assurance -->
<!-- depends: 3 -->
```

```bash
aur spawn tasks.md --verbose
```

---

## Configuration

### Multi-Tier Configuration

**Resolution Order** (highest to lowest priority):
```
1. CLI flags (--tool, --model)
2. Environment variables (AURORA_*_TOOL)
3. Project config (.aurora/config.json)
4. Global config (~/.aurora/config.json)
5. Built-in defaults
```

### Global Configuration

**File**: `~/.aurora/config.json`

```json
{
  "goals": {
    "default_tool": "claude",
    "default_model": "sonnet",
    "memory_threshold": 0.3,
    "max_subgoals": 7
  },
  "soar": {
    "default_tool": "claude",
    "enable_parallel": true,
    "max_concurrent": 5
  },
  "spawn": {
    "max_concurrent": 5,
    "default_timeout": 300
  },
  "memory": {
    "embedding_model": "local",
    "chunk_size": 1000,
    "relevance_threshold": 0.3
  }
}
```

### Project Configuration

**File**: `.aurora/config.json`

```json
{
  "goals": {
    "default_tool": "cursor",
    "memory_threshold": 0.5
  },
  "memory": {
    "index_patterns": ["*.py", "*.js", "*.md"],
    "exclude_patterns": ["node_modules", ".git", "venv"]
  }
}
```

### Environment Variables

**Goals**:
```bash
export AURORA_GOALS_TOOL=cursor
export AURORA_GOALS_MODEL=opus
```

**SOAR**:
```bash
export AURORA_SOAR_TOOL=claude
export AURORA_SOAR_MODEL=sonnet
```

**Spawn**:
```bash
export AURORA_SPAWN_MAX_CONCURRENT=10
export AURORA_SPAWN_TIMEOUT=600
```

---

## Debugging & Troubleshooting

### Log Files

**SOAR Logs**:
```bash
# Location
~/.aurora/soar/soar-*.log

# View latest
ls -t ~/.aurora/soar/*.log | head -1 | xargs cat

# Follow live
tail -f ~/.aurora/soar/soar-*.log
```

**Aurora Main Log**:
```bash
# View
tail -f ~/.aurora/aurora.log

# Debug mode
export AURORA_LOGGING_LEVEL=DEBUG
aur goals "Goal" --verbose
```

### Common Issues

#### Issue: "Tool not found"

```bash
# Check if installed
which cursor

# Add to PATH
export PATH=$PATH:/path/to/cursor

# Use different tool
aur goals "Goal" --tool claude
```

#### Issue: "Database locked"

```bash
# Kill stale processes
pkill -f "aur mem"

# Rebuild index
rm .aurora/memory.db
aur mem index . --force
```

#### Issue: "Spawn timeout"

```bash
# Increase timeout
aur spawn tasks.md --timeout 600

# Or set default
cat >> ~/.aurora/config.json << 'EOF'
{"spawn": {"default_timeout": 600}}
EOF
```

### Health Check

```bash
aur doctor

# Auto-fix issues
aur doctor --fix
```

---

# Part II: Developer Guide

## Configurator System

Aurora's configurator system automatically generates slash commands for 20+ AI coding tools.

### Architecture Overview

```
packages/cli/src/aurora_cli/
├── commands/
│   └── init.py                    # aur init command
├── configurators/
│   ├── slash/                     # Slash command configurators
│   │   ├── base.py                # SlashCommandConfigurator base
│   │   ├── toml_base.py           # TomlSlashCommandConfigurator
│   │   ├── registry.py            # SlashCommandRegistry (20 tools)
│   │   ├── claude.py              # Claude Code (.claude/commands/aur/)
│   │   ├── cursor.py              # Cursor (.cursor/commands/)
│   │   └── ... (18 more tools)
│   └── mcp/                       # MCP configurators (dormant)
└── templates/
    └── slash_commands.py          # SINGLE SOURCE OF TRUTH
```

### Key Design Principles

1. **DRY**: All tools use same template bodies from `templates/slash_commands.py`
2. **Separation**: Tool-specific metadata vs shared logic
3. **Managed Blocks**: User can add content outside `AURORA:START/END` markers

### Template System

**Single Source**: `templates/slash_commands.py`

```python
# Defines 5 Aurora commands:
ALL_COMMANDS = ["search", "get", "plan", "implement", "archive"]

# Each command has a template:
COMMAND_TEMPLATES = {
    "search": SEARCH_TEMPLATE,
    "get": GET_TEMPLATE,
    "plan": PLAN_TEMPLATE,
    "implement": IMPLEMENT_TEMPLATE,
    "archive": ARCHIVE_TEMPLATE,
}
```

**All 20 tools use same templates via `get_command_body(command_id)`**.

### Base Classes

#### SlashCommandConfigurator (Markdown)

```python
class SlashCommandConfigurator(ABC):
    @property
    @abstractmethod
    def tool_id(self) -> str:
        """Tool identifier (e.g., "claude", "cursor")"""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether tool is detected/available"""

    @abstractmethod
    def get_relative_path(self, command_id: str) -> str:
        """File path (e.g., ".claude/commands/aur/search.md")"""

    @abstractmethod
    def get_frontmatter(self, command_id: str) -> str | None:
        """YAML frontmatter (name, description, tags)"""

    @abstractmethod
    def get_body(self, command_id: str) -> str:
        """Command body from templates"""
```

**Managed Block System**:
```markdown
---
name: Aurora: Search
---
<!-- AURORA:START -->
[Template body - managed by Aurora]
<!-- AURORA:END -->

User can add custom content here (not managed)
```

#### TomlSlashCommandConfigurator (TOML)

```python
class TomlSlashCommandConfigurator(SlashCommandConfigurator):
    def get_frontmatter(self, command_id: str) -> str | None:
        """Always None (TOML doesn't use frontmatter)"""

    @abstractmethod
    def get_description(self, command_id: str) -> str:
        """Description for TOML field"""
```

**TOML Format**:
```toml
description = "Search indexed code"

prompt = """
<!-- AURORA:START -->
[body]
<!-- AURORA:END -->
"""
```

**Tools using TOML**: Gemini CLI, Qwen, KiloCode, RooCode, Qoder, iFlow

### Registry System

**SlashCommandRegistry** (`configurators/slash/registry.py`):

```python
class SlashCommandRegistry:
    @classmethod
    def get_all() -> list[SlashCommandConfigurator]:
        """Get all 20 registered configurators"""

    @classmethod
    def get(tool_id: str) -> SlashCommandConfigurator | None:
        """Get specific tool configurator"""

    @classmethod
    def get_available() -> list[SlashCommandConfigurator]:
        """Get only available tools (is_available=True)"""
```

---

## Adding New Tools

### Step 1: Create Configurator Class

**Option A: Markdown Format** (most tools):

Create `configurators/slash/newtool.py`:

```python
"""NewTool slash command configurator."""

from aurora_cli.configurators.slash.base import SlashCommandConfigurator
from aurora_cli.templates.slash_commands import get_command_body

FILE_PATHS: dict[str, str] = {
    "search": ".newtool/commands/aurora-search.md",
    "get": ".newtool/commands/aurora-get.md",
    "plan": ".newtool/commands/aurora-plan.md",
    "implement": ".newtool/commands/aurora-implement.md",
    "archive": ".newtool/commands/aurora-archive.md",
}

FRONTMATTER: dict[str, str] = {
    "search": """---
name: Aurora: Search
description: Search indexed code
category: Aurora
tags: [aurora, search]
---""",
    # ... (repeat for all 5 commands)
}


class NewToolSlashCommandConfigurator(SlashCommandConfigurator):
    """Slash command configurator for NewTool."""

    @property
    def tool_id(self) -> str:
        return "newtool"

    @property
    def is_available(self) -> bool:
        return True

    def get_relative_path(self, command_id: str) -> str:
        return FILE_PATHS[command_id]

    def get_frontmatter(self, command_id: str) -> str | None:
        return FRONTMATTER[command_id]

    def get_body(self, command_id: str) -> str:
        return get_command_body(command_id)  # Uses shared templates
```

**Option B: TOML Format**:

```python
from aurora_cli.configurators.slash.toml_base import TomlSlashCommandConfigurator

DESCRIPTIONS: dict[str, str] = {
    "search": "Search indexed code",
    # ... (5 commands)
}

class NewToolSlashCommandConfigurator(TomlSlashCommandConfigurator):
    def get_description(self, command_id: str) -> str:
        return DESCRIPTIONS[command_id]
    # ... (rest similar to Markdown)
```

### Step 2: Register in Registry

Edit `configurators/slash/registry.py`:

```python
from aurora_cli.configurators.slash.newtool import NewToolSlashCommandConfigurator

configurators = [
    # ... existing tools ...
    NewToolSlashCommandConfigurator(),  # Add this
]
```

Update count in docstring: `"""All 21 supported AI coding tools"""`

### Step 3: Create Tests

Create `tests/unit/cli/configurators/slash/test_newtool.py`:

```python
"""Unit tests for NewTool configurator."""

import pytest
from aurora_cli.configurators.slash.newtool import NewToolSlashCommandConfigurator


def test_tool_id():
    config = NewToolSlashCommandConfigurator()
    assert config.tool_id == "newtool"


def test_get_relative_path():
    config = NewToolSlashCommandConfigurator()
    assert config.get_relative_path("search") == ".newtool/commands/aurora-search.md"


def test_get_body_returns_template():
    config = NewToolSlashCommandConfigurator()
    body = config.get_body("search")
    assert "Guardrails" in body
    assert "aur mem search" in body
```

### Step 4: Update Documentation

1. Update this guide - Add tool to supported tools list
2. Update `COMMANDS.md` - Add tool to slash command examples
3. Update `README.md` - Add to supported tools list

### Step 5: Test

```bash
# Run tests
pytest tests/unit/cli/configurators/slash/test_newtool.py -v

# Test in real project
cd /tmp/test-project
aur init --tools=newtool

# Verify files created
ls .newtool/commands/
```

---

## Modifying Templates

### Updating Default Templates

**Location**: `packages/cli/src/aurora_cli/templates/slash_commands.py`

**Impact**: All 20 tools use these templates.

**Example: Update `/aur:search` format**:

```python
# Edit templates/slash_commands.py

SEARCH_TEMPLATE = f"""{BASE_GUARDRAILS}

**Usage**
Run `aur mem search "<query>"` to search indexed code.

**Output Format (MANDATORY - NEVER DEVIATE)**

1. Execute `aur mem search` with parsed args
2. Display the **FULL TABLE** - never collapse
3. Create simplified table showing ALL results
4. Add exactly 2 sentences of guidance
5. Single line: `Next: /aur:get N`

NO additional explanations."""
```

**After editing**:
```bash
# Reinstall
./install.sh

# Test in project
cd /tmp/test-project
aur init --config --tools=claude

# Verify changes
cat .claude/commands/aur/search.md
```

### Tool-Specific Overrides (Rare)

```python
class SpecialToolSlashCommandConfigurator(SlashCommandConfigurator):
    def get_body(self, command_id: str) -> str:
        """Custom body for special tool."""
        if command_id == "search":
            return "Custom search template..."
        else:
            return get_command_body(command_id)
```

**⚠️ Warning**: Avoid tool-specific overrides - breaks single source of truth.

---

## Testing

### Unit Tests

```bash
# Test all configurators
pytest tests/unit/cli/configurators/ -v

# Test specific tool
pytest tests/unit/cli/configurators/slash/test_claude.py -v
```

### Integration Tests

```bash
# Create test project
mkdir -p /tmp/test-aurora
cd /tmp/test-aurora
git init

# Test init
aur init --tools=claude

# Verify files
ls -la .claude/commands/aur/

# Check content
cat .claude/commands/aur/search.md

# Test update
aur init --config --tools=claude

# Verify Aurora markers preserved
grep -A 5 "AURORA:START" .claude/commands/aur/search.md
```

### Testing Template Changes

```bash
# 1. Reinstall
./install.sh

# 2. Test in fresh project
cd /tmp/test-aurora
rm -rf .claude .cursor .windsurf

# 3. Regenerate all tools
aur init --config --tools=all

# 4. Spot check multiple tools
cat .claude/commands/aur/search.md
cat .cursor/commands/aurora-search.md
cat .gemini/commands/aurora/search.toml

# 5. Verify consistency
# All should have same body between markers
```

### Manual Testing Checklist

- [ ] Markdown tools generate correct frontmatter
- [ ] TOML tools generate valid syntax
- [ ] Aurora markers present in all files
- [ ] All 5 commands generated
- [ ] File paths follow tool's naming convention
- [ ] Update preserves user content outside markers
- [ ] Body content matches template

---

## Release Process

### Pre-Release Checklist

#### Code Quality

```bash
# Run full local CI
./scripts/run-local-ci.sh
```

**Must pass**:
- ✅ All tests (including configurator tests)
- ✅ No security issues (bandit)
- ✅ Code formatted (black, isort)
- ✅ Test coverage standards

#### Configurator-Specific Checks

**For ALL changes**:
- [ ] Updated `templates/slash_commands.py`? Test 3+ tools (Markdown + TOML)
- [ ] Added new tool? Updated count in registry docstring
- [ ] Modified base class? Run all configurator tests
- [ ] Changed file paths? Test `aur init --tools=<tool>`

**For template changes**:
- [ ] Test search command: `/aur:search test limit 5`
- [ ] Test get command: `/aur:get 1`
- [ ] Verify "MANDATORY" sections are clear
- [ ] Check all 5 commands render correctly

**For new tools**:
- [ ] Tool added to `configurators/slash/registry.py`
- [ ] Unit tests created
- [ ] Tool listed in this guide
- [ ] README.md updated (if major tool)

#### Cross-Tool Consistency

```bash
# Generate for multiple tools
cd /tmp/test-consistency
aur init --tools=claude,cursor,windsurf,gemini

# Extract bodies between markers
sed -n '/AURORA:START/,/AURORA:END/p' .claude/commands/aur/search.md > /tmp/claude-body
sed -n '/AURORA:START/,/AURORA:END/p' .cursor/commands/aurora-search.md > /tmp/cursor-body

# Bodies should be identical
diff /tmp/claude-body /tmp/cursor-body
```

### Release

```bash
# After all checks pass
./scripts/release.sh <version>
```

### Post-Release

- [ ] Test install from PyPI: `pip install --upgrade aurora-actr`
- [ ] Verify `aur init` works in fresh project
- [ ] Smoke test 2-3 tools (Claude, Cursor, Gemini)
- [ ] Check GitHub release notes

### Critical Files

| File | When to Update |
|------|----------------|
| `templates/slash_commands.py` | Any command behavior/format change |
| `configurators/slash/registry.py` | Adding/removing tools |
| `configurators/slash/base.py` | Base interface changes |
| `configurators/slash/toml_base.py` | TOML format changes |
| `TOOLS_GUIDE.md` | Any configurator change |
| `COMMANDS.md` | Template format changes |
| `README.md` | Major tool additions |

---

# Part III: Reference

## Best Practices

### Memory Management

**Index Regularly**:
```bash
# After code changes
git commit && aur mem index .

# Daily in CI/CD
0 2 * * * cd /project && aur mem index . --force
```

**Optimize Index**:
```json
{
  "memory": {
    "index_patterns": ["*.py", "*.js", "*.md"],
    "exclude_patterns": [
      "node_modules", ".git", "venv", "*.min.js", "build", "dist"
    ]
  }
}
```

### Goal Decomposition

**Good Goals** (specific, actionable):
```bash
✓ aur goals "Add OAuth2 authentication with JWT"
✓ aur goals "Implement WebSocket notifications"
✓ aur goals "Optimize database queries"
```

**Bad Goals** (vague, too broad):
```bash
✗ aur goals "Make it better"
✗ aur goals "Fix all bugs"
✗ aur goals "Improve performance"
```

### Task Organization

**Use Phases**:
```markdown
## Phase 1: Core Implementation
- [ ] 1. Task A
- [ ] 2. Task B

## Phase 2: Testing
- [ ] 3. Test A
- [ ] 4. Test B
```

**Dependencies**:
```markdown
# Independent (parallel)
- [ ] 1. Task A
- [ ] 2. Task B

# Sequential
- [ ] 1. Task A
- [ ] 2. Task B
<!-- depends: 1 -->

# Diamond (A -> B,C -> D)
- [ ] 1. Task A
- [ ] 2. Task B
<!-- depends: 1 -->
- [ ] 3. Task C
<!-- depends: 1 -->
- [ ] 4. Task D
<!-- depends: 2,3 -->
```

### Performance

**Parallel Execution**:
```bash
# Independent tasks
aur spawn tasks.md --max-concurrent 10

# Dependent tasks
aur spawn tasks.md --sequential
```

**Resource Limits**:
```bash
# Laptops
export AURORA_SPAWN_MAX_CONCURRENT=5

# Servers
export AURORA_SPAWN_MAX_CONCURRENT=20
```

### Security

**API Keys**:
```bash
# Use env vars (not config files)
export ANTHROPIC_API_KEY=sk-ant-...

# Don't commit keys
echo "ANTHROPIC_API_KEY=*" >> .gitignore
```

**Config Files**:
```bash
# Project config: OK to commit
git add .aurora/config.json

# Global config: NOT in repo
# (already in ~/.aurora/)
```

---

## FAQ

### General

**Q: Which tool should I use for my task?**
A: See [Tool Selection Matrix](#tool-selection-matrix).

**Q: How do I update existing slash commands?**
A: Run `aur init --config --tools=<tool>` to regenerate.

**Q: Can I customize generated commands?**
A: Yes, add content outside `AURORA:START/END` markers.

### Configuration

**Q: What's the config resolution order?**
A: CLI flags > env vars > project config > global config > defaults.

**Q: Where are config files stored?**
A: Global: `~/.aurora/config.json`, Project: `.aurora/config.json`.

**Q: How do I use a different tool by default?**
A: Set in config or env: `export AURORA_GOALS_TOOL=cursor`.

### Memory

**Q: When should I reindex?**
A: After significant code changes or git pull.

**Q: How do I fix "database locked"?**
A: Kill stale processes: `pkill -f "aur mem"` then rebuild.

**Q: What files are indexed?**
A: By default: `*.py`, `*.js`, `*.md`. Configure with `index_patterns`.

### Development

**Q: How do I add a new tool?**
A: See [Adding New Tools](#adding-new-tools).

**Q: How do I modify command templates?**
A: Edit `templates/slash_commands.py`, see [Modifying Templates](#modifying-templates).

**Q: Where are tests located?**
A: `tests/unit/cli/configurators/slash/test_*.py`.

### Troubleshooting

**Q: "Tool not found" error?**
A: Check `which <tool>`, add to PATH, or use different tool.

**Q: Spawn timeout?**
A: Increase with `--timeout 600` or set in config.

**Q: Commands not working after init?**
A: Check file was created, has Aurora markers, regenerate if needed.

---

## Common Patterns

### Pattern 1: Markdown with YAML Frontmatter

**Example**: Claude, Cursor, Windsurf (14 tools)

```markdown
---
name: Aurora: Search
description: Search indexed code
category: Aurora
tags: [aurora, search]
---
<!-- AURORA:START -->
**Guardrails**
...
<!-- AURORA:END -->
```

### Pattern 2: TOML Format

**Example**: Gemini CLI, Qwen, KiloCode (6 tools)

```toml
description = "Search indexed code"

prompt = """
<!-- AURORA:START -->
**Guardrails**
...
<!-- AURORA:END -->
"""
```

### Pattern 3: Tool Detection

```python
@property
def is_available(self) -> bool:
    """Check if tool exists."""
    return (Path.home() / ".tool-config").exists()
```

### Pattern 4: Naming Conventions

- **Claude**: `.claude/commands/aur/{command}.md`
- **Most tools**: `.tool/commands/aurora-{command}.md`
- **Gemini**: `.gemini/commands/aurora/{command}.toml`

---

## Troubleshooting Guide

### Issue: "Aurora markers missing"

**Cause**: Manually edited file, removed markers.

**Solution**:
```bash
rm .claude/commands/aur/search.md
aur init --config --tools=claude
```

### Issue: Template changes not appearing

**Cause**: Local install didn't update package.

**Solution**:
```bash
./install.sh
cd /tmp/test-project
rm -rf .claude
aur init --config --tools=claude
```

### Issue: Tool not registered

**Cause**: Missing from registry's `_ensure_initialized()`.

**Solution**:
```python
# In configurators/slash/registry.py
from aurora_cli.configurators.slash.newtool import NewToolSlashCommandConfigurator

configurators = [
    # ... existing ...
    NewToolSlashCommandConfigurator(),
]
```

### Issue: TOML syntax error

**Cause**: Invalid TOML generation.

**Check**:
```python
# In toml_base.py _generate_toml()
prompt = """
{AURORA_MARKERS["start"]}
{body}
{AURORA_MARKERS["end"]}
"""
```

### Issue: Inconsistent bodies

**Cause**: One tool has custom `get_body()` override.

**Solution**: Remove override, update shared template instead.

---

## Quick Reference

### Add New Tool

1. ✅ Create `configurators/slash/newtool.py`
2. ✅ Choose format (Markdown or TOML)
3. ✅ Define FILE_PATHS (5 commands)
4. ✅ Define FRONTMATTER or DESCRIPTIONS
5. ✅ Implement required methods
6. ✅ Register in `registry.py`
7. ✅ Create tests
8. ✅ Run tests
9. ✅ Update tool count
10. ✅ Update docs
11. ✅ Test: `aur init --tools=newtool`

### Modify Template

1. ✅ Edit `templates/slash_commands.py`
2. ✅ Reinstall: `./install.sh`
3. ✅ Test with 3+ tools (Markdown + TOML)
4. ✅ Run tests
5. ✅ Update `COMMANDS.md` if needed
6. ✅ Run pre-commit
7. ✅ Run local CI
8. ✅ Release

### Test Changes

```bash
# Unit tests
pytest tests/unit/cli/configurators/slash/ -v

# Integration
cd /tmp/test-config
aur init --tools=claude,cursor,gemini
cat .claude/commands/aur/search.md
cat .cursor/commands/aurora-search.md
```

---

## See Also

- **COMMANDS.md** - Quick command reference
- **RELEASE.md** - Release workflow
- **README.md** - Project overview
- **CONTRIBUTING.md** - Development guide

---

**Maintained by**: Aurora Core Team
**Questions?**: Open an issue at https://github.com/your-repo/aurora/issues
