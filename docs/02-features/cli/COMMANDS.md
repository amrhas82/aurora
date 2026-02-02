# Aurora Commands Reference

Complete reference for all Aurora CLI commands.

## What's New

** Sprint 4 - Planning Flow (PRD-0026)**

The modern planning workflow is now available! Use `aur goals` to decompose high-level goals into actionable subgoals with automatic agent matching.

```bash
# New workflow (recommended)
aur goals "Add user authentication"      # Decompose with agent matching
cd .aurora/plans/0001-add-user-auth/
/plan                                    # Generate PRD + tasks in Claude Code
aur spawn tasks.md                       # Execute in parallel

# Key features:
[OK] CLI-agnostic execution (works with 20+ tools)
[OK] Intelligent goal decomposition using SOAR
[OK] Automatic agent matching with confidence scores
[OK] LLM fallback for complex agent selection
[OK] Gap detection for missing capabilities
[OK] Memory-aware context integration
[OK] User review flow before committing
```

**Quick comparison:**

| Feature | Legacy (aur plan) | Modern (aur goals) |
|---------|-------------------|-------------------|
| CLI Tool Support | API-only | 20+ CLI tools |
| Goal Decomposition | Manual | SOAR-powered |
| Agent Matching | Manual | Automatic + LLM fallback |
| Gap Detection | None | Automatic with suggestions |
| Memory Integration | None | Context-aware via aur mem |
| User Review | None | Built-in editor review |

[See Planning Flow Workflow →](#planning-flow-workflow-modern---recommended)

---

## Table of Contents

**Core Commands:**
- [Memory & Indexing](#memory--indexing) - `aur mem index`, `aur mem search`
- [Reasoning & Orchestration](#reasoning--orchestration) - `aur soar`, `aur spawn`, `aur query`
- [Planning & Agents](#planning--agents) - `aur goals` , `aur plan`, `aur agents`
- [Configuration](#configuration--management) - `aur init`, `aur doctor`, `aur version`, `aur verify`, `aur budget`

**Workflows:**
- [Research Workflow](#research-workflow) - Memory -> Search -> SOAR
- [Planning Flow (Modern)](#planning-flow-workflow-modern---recommended)  - goals -> /plan -> spawn
- [Legacy Implementation](#legacy-implementation-workflow) - plan -> soar -> spawn
- [Multi-Agent Workflow](#multi-agent-workflow) - Parallel agent execution

**Configuration:**
- [Environment Variables](#environment-variables) - AURORA_GOALS_*, AURORA_SOAR_*, etc.
- [Config Files](#configuration-files) - Global and project configuration
- [File Locations](#file-locations) - Directory structure

**Reference:**
- [Task File Format](#task-file-format) - Markdown checklist format
- [goals.json Format](#goalsjson-format)  - Complete specification with examples
- [Quick Reference](#quick-reference) - Command cheat sheet
- [Getting Help](#getting-help) - Help commands and common scenarios
- [Troubleshooting](#troubleshooting) - Common issues and solutions

 = New in Sprint 4

---

## Core Commands

### Memory & Indexing

#### `aur mem index`
Index code, documentation, and knowledge base.

```bash
aur mem index .                    # Index current directory
aur mem index packages/            # Index specific directory
aur mem index --force              # Rebuild index from scratch
```

[Full Documentation →](../commands/aur-mem.md)

#### `aur mem search`
Search indexed memory with hybrid retrieval.

```bash
# Basic search
aur mem search "authentication"

# Filter by type
aur mem search "auth" --type function    # Functions only
aur mem search "auth" --type class       # Classes only
aur mem search "auth" --type method      # Methods only
aur mem search "auth" --type kb          # Markdown/knowledge base only
aur mem search "auth" --type code        # All code chunks

# Control results
aur mem search "payment" --limit 10      # More results (default: 5)
aur mem search "config" --min-score 0.5  # Higher relevance threshold

# Display options
aur mem search "api" --show-content      # Show code snippets
aur mem search "api" --show-scores       # Detailed score breakdown
aur mem search "api" --format json       # JSON output for scripting
```

**Options:**
```
-n, --limit INT         Max results (default: 5)
-t, --type TYPE         Filter: function, class, method, kb, code, knowledge, document
-f, --format FORMAT     Output: rich (default) or json
-c, --show-content      Show content preview
--show-scores           Detailed score explanations
--min-score FLOAT       Minimum semantic score (0.0-1.0, default: 0.35)
--db-path PATH          Custom database path
```

[Full Documentation →](../commands/aur-mem.md)

### Reasoning & Orchestration

#### `aur soar`
9-phase SOAR reasoning for complex queries with parallel research.

```bash
aur soar "How does authentication work?"
aur soar "Compare React vs Vue" --model opus
aur soar "Explain microservices" --verbose
```

**Features:**
- Automatic complexity assessment
- Parallel agent execution for complex queries
- Synthesized answers with traceability
- Reasoning pattern caching

[Full Documentation →](../commands/aur-soar.md)

#### `aur spawn`
Execute tasks from markdown files in parallel.

```bash
aur spawn tasks.md                 # Execute tasks in parallel
aur spawn --sequential             # Execute one at a time
aur spawn --dry-run                # Validate without executing
aur spawn --verbose                # Show detailed progress
```

**Features:**
- Parallel execution (max 5 concurrent by default)
- Agent assignment via HTML comments
- Task dependency management
- Progress tracking

[Full Documentation →](../commands/aur-spawn.md)

### Planning & Agents

#### `aur goals`
Decompose high-level goals into actionable subgoals with agent assignments.

```bash
# Basic usage - uses default tool and model
aur goals "Implement OAuth2 authentication"

# Skip confirmation prompts (non-interactive mode)
aur goals "Add caching layer" --yes

# Specify CLI tool and model
aur goals "Refactor API layer" --tool cursor --model opus
aur goals "Add metrics" -t claude -m sonnet

# Include context files for informed decomposition
aur goals "Optimize queries" --context src/db/queries.py
aur goals "Refactor auth" -c src/auth/login.py -c src/auth/session.py

# Verbose mode - shows decomposition and agent matching details
aur goals "Add user dashboard" --verbose

# JSON output format
aur goals "Add notifications" --format json

# Skip decomposition (create single-task plan)
aur goals "Fix typo in README" --no-decompose

# Combine multiple options
aur goals "Implement payment processing" \
  --context src/payments/ \
  --tool cursor \
  --model opus \
  --verbose \
  --yes
```

**Features:**
- **CLI-Agnostic Execution**: Works with 20+ CLI tools (claude, cursor, aider, etc.)
- **Intelligent Decomposition**: Uses SOAR reasoning to break goals into 2-7 concrete subgoals
- **Agent Matching**: Automatic agent assignment with confidence scores (0.0-1.0)
- **LLM Fallback**: Uses LLM classification when keyword matching fails
- **Gap Detection**: Identifies missing agent capabilities and suggests fallbacks
- **Memory Integration**: Searches indexed codebase for relevant context files
- **User Review Flow**: Optional editor review before saving goals.json
- **goals.json Output**: Structured format ready for `/plan` skill consumption

**Tool & Model Resolution Order:**
```
1. CLI flag (--tool, --model)
   ↓
2. Environment variable (AURORA_GOALS_TOOL, AURORA_GOALS_MODEL)
   ↓
3. Config file (.aurora/config.json or ~/.aurora/config.json)
   ↓
4. Default ("claude" tool, "sonnet" model)
```

**Example Workflow:**
```bash
# 1. Decompose goal with context
aur goals "Add real-time notifications" \
  --context src/notifications/ \
  --verbose

# Output shows:
# 📋 Decomposing goal into subgoals...
#    Goal: Add real-time notifications
#    Using: claude (sonnet)
#
# 🤖 Agent matching results:
#    [OK] sg-1: @code-developer (exists)
#    [OK] sg-2: @ui-designer (exists)
#    [WARN] sg-3: @devops-engineer (NOT FOUND)
#
# 📁 Plan directory:
#    .aurora/plans/0001-add-real-time-notifications/
#
# Review goals before saving? [Y/n]: y
# (Opens editor for review)
#
# Proceed with saving goals? [Y/n]: y
# [OK] Goals saved.
#
# Next steps:
# 1. Review goals:   cat .aurora/plans/0001-add-real-time-notifications/goals.json
# 2. Generate PRD:   cd .aurora/plans/0001-add-real-time-notifications && /plan
# 3. Start work:     aur implement or aur spawn tasks.md
# 4. Archive:        aur plan archive 0001-add-real-time-notifications
```

**Verbose Output Examples:**

When using `--verbose`, you see:
- Memory search results with relevance scores
- Decomposition reasoning
- Agent matching confidence for each subgoal
- Gap detection warnings

```bash
$ aur goals "Add user authentication" --verbose

[dim]Using tool: claude (model: sonnet)[/]

[bold]📋 Decomposing goal into subgoals...[/]
   Goal: Add user authentication
   Using: claude (sonnet)

[bold]🤖 Agent matching results:[/]
   [OK] sg-1: @code-developer (exists)
   [OK] sg-2: @security-engineer (exists)
   [WARN] sg-3: @compliance-specialist (NOT FOUND - will use @code-developer)

[bold]📁 Plan directory:[/]
   .aurora/plans/0001-add-user-authentication/

[bold]Files created (9 total):[/]
  [OK] goals.json
  [OK] plan.md
  [OK] prd.md
  [OK] tasks.md
  [OK] agents.json
  [OK] specs/0001-add-user-authentication-planning.md
  [OK] specs/0001-add-user-authentication-commands.md
  [OK] specs/0001-add-user-authentication-validation.md
  [OK] specs/0001-add-user-authentication-schemas.md
```

**Planning Flow Position:**
```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ aur goals   │ ──> │ /plan skill  │ ──> │ aur spawn   │
│             │     │ (Claude Code)│     │ or          │
│ Decompose   │     │ Generate PRD │     │ aur         │
│ + Agents    │     │ + tasks.md   │     │ implement   │
└─────────────┘     └──────────────┘     └─────────────┘
      │                    │                     │
      v                    v                     ▼
  goals.json          PRD + tasks           Execute tasks
  (structured)        (detailed)            (parallel/seq)
```

**Common Use Cases:**

1. **New Feature Development:**
   ```bash
   aur goals "Implement user profile page" --context src/users/
   ```

2. **System Refactoring:**
   ```bash
   aur goals "Migrate to microservices" --model opus --verbose
   ```

3. **Bug Fix Planning:**
   ```bash
   aur goals "Fix authentication race condition" --context src/auth/
   ```

4. **Infrastructure Work:**
   ```bash
   aur goals "Set up CI/CD pipeline" --tool cursor
   ```

5. **Quick Tasks (Skip Decomposition):**
   ```bash
   aur goals "Update README with new commands" --no-decompose --yes
   ```

[Full Documentation →](../commands/aur-goals.md) | [Planning Flow Workflow →](../workflows/planning-flow.md)

#### `aur plan create`
Create implementation plans using OpenSpec (legacy).

```bash
aur plan create "Add user authentication"
aur plan list                      # List all plans
aur plan show plan-id              # Show plan details
```

[Full Documentation →](../commands/aur-plan.md)

#### `aur agents list`
Discover and list available agents from configured tools.

```bash
aur agents list                    # List agents for project-configured tools
aur agents list --all              # List agents from all tools
aur agents list --category eng     # Filter by category (eng, qa, product, general)
aur agents search "keyword"        # Search agents by keyword
aur agents show agent-id           # Show agent details
aur agents refresh                 # Force regenerate agent manifest
```

**Features:**
- **Project-scoped by default**: Only shows agents from tools configured in current project
- **Category filtering**: Filter by eng, qa, product, or general
- **Keyword search**: Search across agent id, role, goal, skills, and examples
- **Auto-refresh**: Manifest automatically refreshes when stale

**Options:**
```
-c, --category TYPE    Filter by category (eng, qa, product, general)
-a, --all              Show agents from all tools, not just project-configured
-f, --format FORMAT    Output format: rich (default) or simple
```

[Full Documentation →](../commands/aur-agents.md)

### Configuration & Management

#### `aur init`
Initialize Aurora in your project with a 3-step flow.

```bash
aur init                           # Full initialization (all 3 steps)
aur init --config                  # Configure tools only (Step 3)
aur init --tools=claude,cursor     # Configure specific tools (non-interactive)
aur init --tools=all               # Configure all tools
aur init --tools=none              # Skip tool configuration
```

**3-Step Initialization Flow:**
1. **Planning Setup** - Git initialization and directory structure (.aurora/plans, logs, cache)
2. **Memory Indexing** - Semantic search database for codebase
3. **Tool Configuration** - AI tool integrations with agent discovery

**Re-run Options (when already initialized):**
- `[1] Re-run all steps` - Full re-initialization
- `[2] Selective steps` - Choose which steps to run
- `[3] Configure tools only` - Same as `--config`
- `[4] Refresh agents` - Rescan agent directories for configured tools

**Agent Discovery:**
- Automatically discovers agents from tool-specific directories (e.g., `~/.claude/agents/`)
- Only discovers agents for tools you configure
- Use option `[4]` or `aur agents refresh` to update after adding new agents

#### `aur doctor`
Run health checks and diagnostics.

```bash
aur doctor                         # Run all checks
aur doctor --fix                   # Auto-repair issues
```

#### `aur version`
Show version information.

```bash
aur version                        # Display version
aur --version                      # Alternative syntax
```

#### `aur verify`
Verify Aurora installation and dependencies.

```bash
aur verify                         # Check installation
aur --verify                       # Alternative syntax
```

#### `aur budget`
Manage API usage budget and spending.

```bash
aur budget set 100                 # Set monthly budget ($100)
aur budget status                  # View current spending
aur budget history                 # Show spending history
aur budget reset                   # Reset monthly counter
```

#### `aur query`
Execute SOAR query orchestration (legacy interface).

```bash
aur query "How does auth work?"    # Execute SOAR query
```

**Note:** `aur soar` is the recommended interface for SOAR queries.

## Command Workflows

### Research Workflow

```bash
# 1. Index your codebase
aur mem index .

# 2. Search for relevant context
aur mem search "payment processing"

# 3. Run SOAR reasoning with parallel research
aur soar "Explain how payment processing works"
```

### Planning Flow Workflow (Modern - Recommended)

Complete workflow from idea to implementation using `aur goals` -> `/plan` -> execution.

```bash
# STEP 1: Index your codebase for context-aware planning
aur mem index .

# STEP 2: Decompose goal with agent assignments
aur goals "Add user authentication with JWT tokens" \
  --context src/auth/ \
  --context src/api/ \
  --tool claude \
  --verbose

# Output:
# 📋 Decomposing goal into subgoals...
# 🤖 Agent matching results:
#    [OK] sg-1: Implement JWT middleware (@code-developer)
#    [OK] sg-2: Create login endpoints (@code-developer)
#    [OK] sg-3: Add token refresh logic (@code-developer)
#
# 📁 Plan directory:
#    .aurora/plans/0001-add-user-authentication-with-jwt/
#
# [OK] Goals saved.

# STEP 3: Review generated goals.json
cat .aurora/plans/0001-add-user-authentication-with-jwt/goals.json

# STEP 4: Navigate to plan directory
cd .aurora/plans/0001-add-user-authentication-with-jwt/

# STEP 5: Generate PRD and tasks in Claude Code
# (Inside Claude Code/Cursor/other IDE)
/plan

# This reads goals.json and generates:
#   - prd.md: Detailed product requirements
#   - tasks.md: Actionable task list with agent assignments

# STEP 6: Review generated PRD and tasks
cat prd.md
cat tasks.md

# STEP 7a: Execute tasks sequentially (for careful review between tasks)
aur implement

# OR STEP 7b: Execute tasks in parallel (for speed)
aur spawn tasks.md --verbose

# STEP 8: Re-index updated code
aur mem index .

# STEP 9: Verify implementation
pytest tests/
aur doctor

# STEP 10: Archive completed plan
cd ../..  # Back to project root
aur plan archive 0001-add-user-authentication-with-jwt
```

**Detailed Step-by-Step Example:**

```bash
# Real-world example: Adding payment processing

# 1. Start with indexed codebase
$ aur mem index .
[OK] Indexed 2,431 chunks from 342 files

# 2. Create goals with context
$ aur goals "Implement Stripe payment processing" \
    --context src/checkout/ \
    --context src/orders/ \
    --model opus \
    --verbose

Using tool: claude (model: opus)

📋 Decomposing goal into subgoals...
   Goal: Implement Stripe payment processing
   Using: claude (opus)

Memory search found 8 relevant files:
  - src/checkout/cart.py (0.92)
  - src/orders/models.py (0.87)
  - src/api/payments.py (0.81)
  ...

🤖 Agent matching results:
   [OK] sg-1: Set up Stripe SDK integration (@code-developer, confidence: 0.89)
   [OK] sg-2: Create payment endpoints (@code-developer, confidence: 0.91)
   [OK] sg-3: Add webhook handlers (@code-developer, confidence: 0.85)
   [OK] sg-4: Implement payment UI (@ui-designer, confidence: 0.78)
   [WARN] sg-5: Configure PCI compliance (@security-engineer, NOT FOUND)

Agent gaps detected:
  - Missing @security-engineer for sg-5 (PCI compliance)
  - Fallback: @code-developer (review required)

📁 Plan directory:
   .aurora/plans/0001-implement-stripe-payment-processing/

Review goals before saving? [Y/n]: y

# (Opens $EDITOR with goals.json for review)
# You can edit subgoals, adjust agent assignments, add dependencies

Proceed with saving goals? [Y/n]: y

[OK] Goals saved.

Files created (9 total):
  [OK] goals.json
  [OK] plan.md
  [OK] prd.md (placeholder)
  [OK] tasks.md (placeholder)
  [OK] agents.json
  [OK] specs/0001-implement-stripe-payment-processing-planning.md
  [OK] specs/0001-implement-stripe-payment-processing-commands.md
  [OK] specs/0001-implement-stripe-payment-processing-validation.md
  [OK] specs/0001-implement-stripe-payment-processing-schemas.md

Next steps:
1. Review goals:   cat .aurora/plans/0001-implement-stripe-payment-processing/goals.json
2. Generate PRD:   cd .aurora/plans/0001-implement-stripe-payment-processing && /plan
3. Start work:     aur implement or aur spawn tasks.md
4. Archive:        aur plan archive 0001-implement-stripe-payment-processing

# 3. Navigate and review
$ cd .aurora/plans/0001-implement-stripe-payment-processing/
$ cat goals.json

{
  "id": "0001-implement-stripe-payment-processing",
  "title": "Implement Stripe payment processing",
  "created_at": "2026-01-10T14:30:00Z",
  "status": "ready_for_planning",
  "memory_context": [
    {"file": "src/checkout/cart.py", "relevance": 0.92},
    {"file": "src/orders/models.py", "relevance": 0.87},
    ...
  ],
  "subgoals": [
    {
      "id": "sg-1",
      "title": "Set up Stripe SDK integration",
      "description": "Install Stripe Python SDK, configure API keys, create service wrapper",
      "agent": "@code-developer",
      "confidence": 0.89,
      "dependencies": []
    },
    ...
  ],
  "gaps": [
    {
      "subgoal_id": "sg-5",
      "suggested_capabilities": ["PCI compliance", "security audit"],
      "fallback": "@code-developer"
    }
  ]
}

# 4. Generate PRD and tasks (in Claude Code)
# Open Claude Code in this directory and run:
$ /plan

# /plan reads goals.json and generates detailed PRD + tasks
# This takes 2-3 minutes...

[OK] Generated prd.md (1,234 lines)
[OK] Generated tasks.md (456 lines)

# 5. Review generated artifacts
$ cat prd.md | head -50
$ cat tasks.md | head -50

# 6. Execute tasks in parallel
$ aur spawn tasks.md --verbose

Spawning 5 tasks across 3 agents:
  [@code-developer] Task 1.0: Set up Stripe SDK... RUNNING
  [@code-developer] Task 2.0: Create payment endpoints... QUEUED
  [@code-developer] Task 3.0: Add webhook handlers... QUEUED
  [@ui-designer] Task 4.0: Implement payment UI... RUNNING
  [@code-developer] Task 5.0: PCI compliance review... QUEUED

Task 1.0 COMPLETE (45s)
Task 4.0 COMPLETE (67s)
Task 2.0 RUNNING...
...

All tasks complete! [OK]

# 7. Re-index and verify
$ cd ../../..  # Back to project root
$ aur mem index .
[OK] Indexed 2,498 chunks from 351 files (+9 files)

$ pytest tests/payments/
========================= 24 passed in 3.21s =========================

$ aur doctor
[OK] All checks passed

# 8. Archive completed plan
$ aur plan archive 0001-implement-stripe-payment-processing
[OK] Plan archived to .aurora/plans/archive/0001-implement-stripe-payment-processing/
```

**Key Benefits of Planning Flow:**

1. **Context-Aware**: Memory search finds relevant files automatically
2. **Agent Matching**: Optimal agent assignment with confidence scores
3. **Gap Detection**: Identifies missing capabilities early
4. **User Review**: Edit goals before committing to implementation
5. **Structured Output**: goals.json -> PRD -> tasks provides clear path
6. **Flexible Execution**: Choose sequential (careful) or parallel (fast)
7. **Traceability**: Full audit trail from goal to implementation

### Legacy Implementation Workflow

```bash
# 1. Create implementation plan (legacy)
aur plan create "Add user authentication"

# 2. Generate task list
aur soar "Break down user auth implementation" > auth-tasks.md

# 3. Execute tasks in parallel
aur spawn auth-tasks.md --verbose

# 4. Re-index updated code
aur mem index .
```

### Multi-Agent Workflow

```bash
# 1. List available agents for your configured tools
aur agents list                    # Project-scoped
aur agents list --all              # All tools
aur agents search "developer"      # Find by keyword

# 2. Create task file with agent assignments
cat > tasks.md << 'EOF'
- [ ] 1. Research best practices
<!-- agent: researcher -->

- [ ] 2. Implement feature
<!-- agent: developer -->

- [ ] 3. Write tests
<!-- agent: test-engineer -->
EOF

# 3. Execute with parallel agents
aur spawn tasks.md
```

## Global Options

All commands support these global options:

### `--verbose`, `-v`
Show detailed output.

```bash
aur soar "Query" --verbose
aur spawn tasks.md -v
```

### `--debug`
Enable debug logging.

```bash
aur mem index . --debug
```

### `--help`
Show command help.

```bash
aur --help                         # Show all commands
aur soar --help                    # Show soar command help
aur spawn --help                   # Show spawn command help
```

## Environment Variables

### Goals Configuration

```bash
export AURORA_GOALS_TOOL=claude        # Default CLI tool for aur goals
export AURORA_GOALS_MODEL=sonnet       # Default model (sonnet or opus)

# Supported tools (20+):
# - claude (Claude Code CLI)
# - cursor (Cursor IDE CLI)
# - aider (Aider CLI)
# - continue (Continue CLI)
# - cline, windsurf, bolt, etc.
```

### SOAR Configuration

```bash
export AURORA_SOAR_TOOL=cursor     # Default CLI tool for aur soar
export AURORA_SOAR_MODEL=opus      # Default model
```

### Spawn Configuration

```bash
export AURORA_SPAWN_MAX_CONCURRENT=10  # Max parallel tasks
export AURORA_SPAWN_TIMEOUT=600        # Task timeout (seconds)
```

### Logging

```bash
export AURORA_LOGGING_LEVEL=DEBUG  # Logging level
export AURORA_LOG_FILE=/path/log   # Log file location
```

### CLI Tool Resolution Example

```bash
# Configure different tools for different commands
export AURORA_GOALS_TOOL=claude    # Fast for goal decomposition
export AURORA_SOAR_TOOL=cursor     # Rich UI for complex reasoning

# Run commands - they use their respective tools
aur goals "Add feature"            # Uses claude
aur soar "Complex query"           # Uses cursor
```

## Configuration Files

### Global Config

Location: `~/.aurora/config.json`

```json
{
  "goals": {
    "default_tool": "claude",
    "default_model": "sonnet"
  },
  "soar": {
    "default_tool": "claude",
    "default_model": "sonnet"
  },
  "spawn": {
    "max_concurrent": 5,
    "default_timeout": 300
  },
  "logging": {
    "level": "INFO"
  }
}
```

### Project Config

Location: `.aurora/config.json`

```json
{
  "goals": {
    "default_tool": "cursor",
    "default_model": "opus"
  },
  "soar": {
    "default_tool": "cursor"
  }
}
```

**Configuration Precedence:**
```
CLI flags (--tool, --model)
    ↓
Environment variables (AURORA_GOALS_TOOL, AURORA_GOALS_MODEL)
    ↓
Project config (.aurora/config.json)
    ↓
Global config (~/.aurora/config.json)
    ↓
Defaults (claude, sonnet)
```

**Example Configuration Scenarios:**

1. **Use Claude globally, Cursor for this project:**
   ```json
   # ~/.aurora/config.json
   {"goals": {"default_tool": "claude"}}

   # .aurora/config.json
   {"goals": {"default_tool": "cursor"}}
   ```

2. **Use Opus for complex goals, Sonnet for simple ones:**
   ```bash
   # Simple goals use config default (sonnet)
   aur goals "Fix typo in docs"

   # Complex goals override to opus
   aur goals "Redesign authentication" --model opus
   ```

3. **Environment-specific tools:**
   ```bash
   # Development: fast local tool
   export AURORA_GOALS_TOOL=claude

   # CI/CD: use API-based tool
   export AURORA_GOALS_TOOL=aider
   ```

[Configuration Reference →](../reference/CONFIG_REFERENCE.md)

## File Locations

### Aurora Directory

```
~/.aurora/                         # Global Aurora directory
  ├── config.json                  # Global configuration
  ├── agents/                      # Global agents
  ├── soar/                        # SOAR execution logs
  └── cache/                       # Cache data
```

### Project Directory

```
.aurora/                           # Project Aurora directory
  ├── config.json                  # Project configuration
  ├── agents/                      # Project agents
  ├── plans/                       # OpenSpec plans
  └── memory.db                    # SQLite memory store
```

## Task File Format

Task files use markdown checklist format with HTML comment metadata:

```markdown
# Task List

- [ ] 1. Task description
<!-- agent: agent-name -->
<!-- depends: previous-task-id -->

- [x] 2. Completed task
<!-- agent: self -->
```

**Metadata Comments:**
- `<!-- agent: name -->` - Assign agent
- `<!-- depends: id -->` - Declare dependency
- `<!-- timeout: seconds -->` - Custom timeout *(in development)*
- `<!-- priority: high|medium|low -->` - Priority *(in development)*

## goals.json Format

The `aur goals` command creates a `goals.json` file that serves as input for the `/plan` skill.

### Complete Format Specification

```json
{
  "id": "0001-add-oauth2",
  "title": "Implement OAuth2 authentication",
  "created_at": "2026-01-10T12:00:00Z",
  "status": "ready_for_planning",
  "memory_context": [
    {
      "file": "src/auth/login.py",
      "relevance": 0.85
    },
    {
      "file": "src/api/endpoints.py",
      "relevance": 0.79
    }
  ],
  "subgoals": [
    {
      "id": "sg-1",
      "title": "Implement OAuth provider integration",
      "description": "Add Google/GitHub OAuth providers with PKCE flow",
      "agent": "@code-developer",
      "confidence": 0.85,
      "dependencies": []
    },
    {
      "id": "sg-2",
      "title": "Create token management system",
      "description": "JWT token generation, refresh, and validation",
      "agent": "@code-developer",
      "confidence": 0.89,
      "dependencies": ["sg-1"]
    },
    {
      "id": "sg-3",
      "title": "Add authentication UI",
      "description": "Login/logout buttons, user profile dropdown",
      "agent": "@ui-designer",
      "confidence": 0.78,
      "dependencies": ["sg-1"]
    }
  ],
  "gaps": [
    {
      "subgoal_id": "sg-4",
      "suggested_capabilities": ["security audit", "penetration testing"],
      "fallback": "@code-developer"
    }
  ]
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Plan identifier in NNNN-slug format (e.g., "0001-add-oauth2") |
| `title` | string | Yes | High-level goal description (10-500 characters) |
| `created_at` | ISO datetime | Yes | Timestamp of goal creation |
| `status` | string | Yes | Always "ready_for_planning" after `aur goals` |
| `memory_context` | array | No | Relevant files found by memory search with relevance scores (0.0-1.0) |
| `subgoals` | array | Yes | Decomposed tasks with agent assignments (2-7 subgoals typical) |
| `gaps` | array | No | Missing agent capabilities detected during matching |

### Subgoal Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Subgoal identifier (sg-1, sg-2, etc.) |
| `title` | string | Yes | Brief subgoal title (5-100 characters) |
| `description` | string | Yes | Detailed description of what needs to be done |
| `agent` | string | Yes | Agent ID in @agent-name format |
| `confidence` | float | Yes | Matching confidence score (0.0-1.0) |
| `dependencies` | array | Yes | List of prerequisite subgoal IDs (can be empty) |

### Gap Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `subgoal_id` | string | Yes | ID of subgoal that lacks good agent match |
| `suggested_capabilities` | array | Yes | List of missing capabilities needed |
| `fallback` | string | Yes | Fallback agent to use (typically @code-developer) |

### Real-World Examples

#### Example 1: Simple Feature (No Gaps)

```json
{
  "id": "0002-add-dark-mode",
  "title": "Add dark mode toggle",
  "created_at": "2026-01-10T15:00:00Z",
  "status": "ready_for_planning",
  "memory_context": [
    {"file": "src/ui/theme.css", "relevance": 0.91},
    {"file": "src/components/Header.jsx", "relevance": 0.82}
  ],
  "subgoals": [
    {
      "id": "sg-1",
      "title": "Design dark mode color scheme",
      "description": "Define dark mode colors, ensure WCAG AA contrast",
      "agent": "@ui-designer",
      "confidence": 0.92,
      "dependencies": []
    },
    {
      "id": "sg-2",
      "title": "Implement theme toggle component",
      "description": "React component with local storage persistence",
      "agent": "@code-developer",
      "confidence": 0.88,
      "dependencies": ["sg-1"]
    }
  ],
  "gaps": []
}
```

#### Example 2: Complex Feature (With Gaps and Dependencies)

```json
{
  "id": "0003-add-payment-processing",
  "title": "Implement Stripe payment processing",
  "created_at": "2026-01-10T16:30:00Z",
  "status": "ready_for_planning",
  "memory_context": [
    {"file": "src/checkout/cart.py", "relevance": 0.94},
    {"file": "src/orders/models.py", "relevance": 0.88},
    {"file": "src/api/payments.py", "relevance": 0.82}
  ],
  "subgoals": [
    {
      "id": "sg-1",
      "title": "Set up Stripe SDK integration",
      "description": "Install SDK, configure API keys, create service wrapper",
      "agent": "@code-developer",
      "confidence": 0.91,
      "dependencies": []
    },
    {
      "id": "sg-2",
      "title": "Create payment endpoints",
      "description": "REST endpoints for checkout, payment intent, webhooks",
      "agent": "@code-developer",
      "confidence": 0.89,
      "dependencies": ["sg-1"]
    },
    {
      "id": "sg-3",
      "title": "Implement payment UI components",
      "description": "Checkout form, payment method selector, success/error states",
      "agent": "@ui-designer",
      "confidence": 0.85,
      "dependencies": ["sg-1"]
    },
    {
      "id": "sg-4",
      "title": "Configure PCI compliance",
      "description": "Security audit, data handling review, compliance documentation",
      "agent": "@security-engineer",
      "confidence": 0.42,
      "dependencies": ["sg-2", "sg-3"]
    }
  ],
  "gaps": [
    {
      "subgoal_id": "sg-4",
      "suggested_capabilities": ["PCI DSS compliance", "security audit", "penetration testing"],
      "fallback": "@code-developer"
    }
  ]
}
```

#### Example 3: Bug Fix (Single Task, No Decomposition)

```json
{
  "id": "0004-fix-login-timeout",
  "title": "Fix login session timeout issue",
  "created_at": "2026-01-10T17:00:00Z",
  "status": "ready_for_planning",
  "memory_context": [
    {"file": "src/auth/session.py", "relevance": 0.96}
  ],
  "subgoals": [
    {
      "id": "sg-1",
      "title": "Fix login session timeout issue",
      "description": "Investigate and fix session expiration bug in auth middleware",
      "agent": "@code-developer",
      "confidence": 0.94,
      "dependencies": []
    }
  ],
  "gaps": []
}
```

### Workflow Integration

**How goals.json flows through the system:**

```
┌──────────────┐
│  aur goals   │
│              │
│ • Index memory
│ • Decompose goal
│ • Match agents
│ • Detect gaps
│              │
│ OUTPUT:      │
│ goals.json ───┼───> User reviews in editor
└──────────────┘     │
                     ▼
                ┌──────────────┐
                │  /plan skill │
                │ (Claude Code)│
                │              │
                │ READS:       │
                │ goals.json ───┼───> Generates PRD
                │              │───> Generates tasks.md
                └──────────────┘
                     │
                     ▼
                ┌──────────────┐
                │ aur spawn    │
                │ or           │
                │ aur implement│
                │              │
                │ READS:       │
                │ tasks.md  ───┼───> Executes tasks
                └──────────────┘
```

**Related Commands:**
- `aur goals` - Creates goals.json
- `/plan` skill - Reads goals.json, generates PRD and tasks
- `aur implement` - Executes tasks sequentially
- `aur spawn` - Executes tasks in parallel
- `aur plan archive <id>` - Archives completed plan

**Editing goals.json:**

You can manually edit goals.json before running `/plan`:

```bash
# 1. Generate goals
aur goals "Add feature" --yes

# 2. Edit goals.json
nano .aurora/plans/0001-add-feature/goals.json

# Make changes:
# - Adjust agent assignments
# - Add/remove subgoals
# - Change dependencies
# - Update descriptions

# 3. Run /plan with edited goals
cd .aurora/plans/0001-add-feature/
/plan  # Reads your edited goals.json
```

[Goals.json Examples →](examples/goals/) | [Planning Flow →](../workflows/planning-flow.md)

## Quick Reference

| Command | Purpose | Example |
|---------|---------|---------|
| `aur init` | Initialize project | `aur init` |
| `aur mem index` | Index codebase | `aur mem index .` |
| `aur mem search` | Search memory | `aur mem search "auth"` |
| `aur soar` | SOAR reasoning | `aur soar "Query"` |
| `aur query` | SOAR query (legacy) | `aur query "Query"` |
| `aur goals` | Decompose goals | `aur goals "Add feature"` |
| `aur spawn` | Execute tasks | `aur spawn tasks.md` |
| `aur plan create` | Create plan (legacy) | `aur plan create "Feature"` |
| `aur agents list` | List agents | `aur agents list` |
| `aur agents list --all` | List all agents | `aur agents list --all` |
| `aur agents search` | Search agents | `aur agents search "test"` |
| `aur agents refresh` | Refresh agent manifest | `aur agents refresh` |
| `aur budget` | Manage budget | `aur budget status` |
| `aur doctor` | Health check | `aur doctor` |
| `aur version` | Show version | `aur version` |
| `aur verify` | Verify installation | `aur verify` |

## Getting Help

```bash
# Show all commands
aur --help

# Show command-specific help
aur goals --help            # Goals decomposition help
aur soar --help             # SOAR reasoning help
aur spawn --help            # Task spawning help
aur mem --help              # Memory indexing help
aur plan --help             # Planning help (legacy)
aur agents --help           # Agent management help

# Check system health
aur doctor

# View logs
tail -f ~/.aurora/soar/*.log
tail -f ~/.aurora/goals/*.log

# Get help for specific errors
aur goals "Test" --verbose  # See detailed output
aur doctor --fix            # Auto-repair common issues
```

### Common Help Scenarios

**"How do I start a new feature?"**
```bash
# Quick start
aur goals "Your feature description" --help
# Then follow the workflow shown
```

**"What agents are available?"**
```bash
aur agents list                    # Agents for configured tools
aur agents list --all              # All available agents
aur agents search "test"           # Search by keyword
aur agents show code-developer     # Show specific agent details
```

**"How do I configure my CLI tool?"**
```bash
# See all configuration options
cat ../reference/CONFIG_REFERENCE.md

# Set tool via environment
export AURORA_GOALS_TOOL=claude
aur goals --help  # Shows default tool
```

**"Why is agent matching failing?"**
```bash
# Run with verbose to see matching details
aur goals "Your goal" --verbose

# Check available agents
aur agents list
```

## Troubleshooting

### Command not found

```bash
# Verify installation
pip show aurora-actr

# Check PATH
which aur

# Reinstall if needed
pip install --upgrade aurora-actr
```

### Permission errors

```bash
# Fix permissions
chmod +x $(which aur)

# Or reinstall with --user
pip install --user aurora-actr
```

### Configuration issues

```bash
# Reinitialize
aur init --config

# Check config
cat ~/.aurora/config.json

# Reset to defaults
rm ~/.aurora/config.json && aur init
```

### Memory issues

```bash
# Rebuild index
aur mem index . --force

# Check database
sqlite3 .aurora/memory.db "SELECT COUNT(*) FROM chunks;"

# Clear cache
rm -rf ~/.aurora/cache/
```

### Goals command issues

#### Tool not found

**Error:** `Error: CLI tool 'cursor' not found in PATH`

**Solution:**
```bash
# Check if tool is installed
which cursor

# Install the tool
# For Cursor: Download from cursor.sh
# For Claude: pip install claude-cli
# For Aider: pip install aider-chat

# Or use a different tool
aur goals "Your goal" --tool claude

# Or set environment variable
export AURORA_GOALS_TOOL=claude
aur goals "Your goal"
```

#### Agent gaps detected

**Warning:** `[WARN] sg-3: @security-engineer (NOT FOUND)`

**What it means:** No agent matches the required capabilities.

**Solutions:**

1. **Use fallback agent (automatic):**
   ```bash
   # Gap detection suggests fallback automatically
   # goals.json will use @code-developer as fallback
   ```

2. **Install missing agent:**
   ```bash
   # Download agent definition
   curl -o ~/.aurora/agents/security-engineer.json \
     https://example.com/agents/security-engineer.json

   # Re-run goals
   aur goals "Your goal"
   ```

3. **Manual assignment:**
   ```bash
   # Edit goals.json after generation
   nano .aurora/plans/0001-your-goal/goals.json

   # Change agent field:
   # "agent": "@security-engineer"  ->  "agent": "@code-developer"
   ```

#### Low confidence scores

**Warning:** Multiple subgoals have confidence < 0.7

**Meaning:** Agent matching is uncertain.

**Solutions:**

1. **Add context files:**
   ```bash
   # Provide more context for better agent matching
   aur goals "Your goal" \
     --context src/relevant/file1.py \
     --context src/relevant/file2.py
   ```

2. **Use verbose mode to see matching details:**
   ```bash
   aur goals "Your goal" --verbose
   # Shows why confidence is low
   ```

3. **Review and edit goals.json:**
   ```bash
   # Review agent assignments
   cat .aurora/plans/0001-your-goal/goals.json

   # Edit if needed
   nano .aurora/plans/0001-your-goal/goals.json
   ```

#### goals.json validation errors

**Error:** `Invalid goals.json: missing required field 'subgoals'`

**Solution:**
```bash
# Validate JSON syntax
python -m json.tool .aurora/plans/0001-your-goal/goals.json

# Check required fields
cat .aurora/plans/0001-your-goal/goals.json | jq '.subgoals'

# Regenerate if corrupted
rm -rf .aurora/plans/0001-your-goal/
aur goals "Your goal"
```

#### Memory search returns no results

**Issue:** No relevant context files found

**Solutions:**

1. **Index your codebase first:**
   ```bash
   aur mem index .
   aur goals "Your goal"
   ```

2. **Check memory database:**
   ```bash
   sqlite3 .aurora/memory.db "SELECT COUNT(*) FROM chunks;"
   # Should show > 0 chunks
   ```

3. **Explicitly provide context:**
   ```bash
   aur goals "Your goal" --context src/relevant/
   ```

#### Decomposition produces too many/few subgoals

**Issue:** Goal decomposed into 10+ subgoals or only 1 subgoal

**Solutions:**

1. **For too many subgoals (>7):**
   ```bash
   # Use more specific goal description
   aur goals "Implement OAuth2 Google provider" # Instead of "Implement authentication"

   # Or edit goals.json to merge subgoals
   nano .aurora/plans/0001-your-goal/goals.json
   ```

2. **For too few subgoals (1-2):**
   ```bash
   # Make goal more broad
   aur goals "Implement complete user authentication system" # Instead of "Add login button"

   # Or use --no-decompose for simple tasks
   aur goals "Fix typo" --no-decompose
   ```

3. **Try different model:**
   ```bash
   # Opus may decompose differently than Sonnet
   aur goals "Your goal" --model opus
   ```

#### Editor doesn't open for review

**Issue:** `Review goals before saving? [Y/n]: y` doesn't open editor

**Solutions:**

1. **Set EDITOR environment variable:**
   ```bash
   export EDITOR=nano
   aur goals "Your goal"

   # Or use your preferred editor
   export EDITOR=vim
   export EDITOR=code  # VS Code
   export EDITOR=subl  # Sublime Text
   ```

2. **Skip review prompt:**
   ```bash
   aur goals "Your goal" --yes
   ```

3. **Edit manually after:**
   ```bash
   nano .aurora/plans/0001-your-goal/goals.json
   ```

#### Plans directory doesn't exist

**Error:** `FileNotFoundError: .aurora/plans/`

**Solution:**
```bash
# Initialize Aurora
aur init

# Or let goals command auto-initialize
aur goals "Your goal"  # Auto-creates .aurora/ if missing
```

## Advanced Usage Patterns

### Pattern 1: Context-Driven Planning

Use memory search to inform goal decomposition:

```bash
# 1. Index codebase thoroughly
aur mem index . --force

# 2. Search for relevant context
aur mem search "authentication" --limit 20 > auth-context.txt

# 3. Review context to understand existing patterns
cat auth-context.txt

# 4. Create goals with informed context
aur goals "Add OAuth2 authentication" \
  --context src/auth/login.py \
  --context src/auth/session.py \
  --context src/api/endpoints.py \
  --verbose

# Memory search will find additional relevant files automatically
```

### Pattern 2: Multi-Tool Workflow

Use different CLI tools for different stages:

```bash
# Use fast tool for goal decomposition
export AURORA_GOALS_TOOL=claude
aur goals "Add payment processing"

# Use rich UI tool for PRD generation
cd .aurora/plans/0001-add-payment-processing/
cursor /plan  # Opens in Cursor with rich UI

# Use API-based tool for parallel execution
export AURORA_SPAWN_TOOL=api
aur spawn tasks.md
```

### Pattern 3: Iterative Refinement

Refine goals based on decomposition results:

```bash
# 1. Initial decomposition
aur goals "Add feature X" --verbose

# Output shows 8 subgoals - too many!

# 2. Refine goal to be more specific
aur goals "Add feature X core functionality only" --verbose

# Output shows 3 subgoals - better!

# 3. Create separate goals for extensions
aur goals "Add feature X advanced options"
aur goals "Add feature X integrations"
```

### Pattern 4: Agent Gap Resolution

Handle missing agent capabilities systematically:

```bash
# 1. Run goals and detect gaps
aur goals "Implement secure payment system" --verbose

# Output:
# [WARN] sg-4: @security-engineer (NOT FOUND)
# Gap: ["PCI compliance", "security audit"]
# Fallback: @code-developer

# 2. Option A: Create custom agent
cat > ~/.aurora/agents/security-engineer.json << 'EOF'
{
  "id": "security-engineer",
  "name": "Security Engineer",
  "capabilities": ["security audit", "PCI compliance", "penetration testing"],
  "prompts": {
    "system": "You are a security engineer..."
  }
}
EOF

# 3. Option B: Split work across multiple agents
# Edit goals.json to break sg-4 into:
# - sg-4a: Security review (@code-developer)
# - sg-4b: PCI documentation (@backlog-manager)

# 4. Option C: Accept fallback and add manual review
# Let @code-developer handle it, then manual security review
```

### Pattern 5: Batch Planning

Create multiple related plans efficiently:

```bash
# Create multiple goals in sequence
for feature in "auth" "payments" "notifications" "analytics"; do
  aur goals "Implement ${feature} system" \
    --context "src/${feature}/" \
    --yes
done

# Review all plans
ls -la .aurora/plans/

# Prioritize and execute
cd .aurora/plans/0001-implement-auth-system/
/plan && aur spawn tasks.md
```

### Pattern 6: Goal Templates

Use templates for common patterns:

```bash
# Create template function in .bashrc
goals_feature() {
  aur goals "Implement ${1} feature" \
    --context "src/${1}/" \
    --model sonnet \
    --yes
}

goals_bug_fix() {
  aur goals "Fix ${1} bug" \
    --context "${2}" \
    --no-decompose \
    --yes
}

# Use templates
goals_feature "user-dashboard"
goals_bug_fix "login timeout" "src/auth/session.py"
```

### Pattern 7: CI/CD Integration

Automate goal creation from issues/PRs:

```bash
#!/bin/bash
# .github/workflows/create-plan.sh

ISSUE_TITLE="$1"
ISSUE_LABELS="$2"

# Determine model based on complexity
if [[ "$ISSUE_LABELS" == *"complex"* ]]; then
  MODEL="opus"
else
  MODEL="sonnet"
fi

# Create goals automatically
aur goals "$ISSUE_TITLE" \
  --model "$MODEL" \
  --format json \
  --yes > plan-output.json

# Post plan summary to issue
cat plan-output.json | jq -r '.subgoals[] | "- \(.title) (@\(.agent))"' \
  | gh issue comment "$ISSUE_NUMBER" --body-file -
```

### Pattern 8: Cross-Project Planning

Plan features that span multiple repositories:

```bash
# Project A: Backend API
cd ~/projects/api/
aur goals "Add GraphQL endpoint for payments" \
  --context src/graphql/ \
  --yes

# Project B: Frontend
cd ~/projects/frontend/
aur goals "Add payment UI using GraphQL" \
  --context src/payments/ \
  --yes

# Link plans in documentation
echo "Backend: ~/projects/api/.aurora/plans/0001-add-graphql-endpoint-for-payments/" \
  >> ~/projects/frontend/.aurora/plans/0001-add-payment-ui-using-graphql/DEPENDENCIES.md
```

### Pattern 9: Complexity-Based Model Selection

Automatically choose model based on goal complexity:

```bash
#!/bin/bash
smart_goals() {
  GOAL="$1"
  WORD_COUNT=$(echo "$GOAL" | wc -w)

  # Simple goals (<5 words) -> sonnet
  # Complex goals (≥5 words) -> opus
  if [ "$WORD_COUNT" -lt 5 ]; then
    MODEL="sonnet"
  else
    MODEL="opus"
  fi

  aur goals "$GOAL" --model "$MODEL" --verbose
}

# Usage
smart_goals "Fix typo"                           # Uses sonnet
smart_goals "Implement distributed caching"      # Uses opus
```

### Pattern 10: Knowledge Base Enhancement

Continuously improve agent matching:

```bash
# After each successful plan
cd .aurora/plans/0001-completed-plan/

# Extract successful patterns
cat goals.json | jq -r '.subgoals[] | "\(.title) -> \(.agent) (confidence: \(.confidence))"' \
  >> ~/.aurora/agent-matching-history.txt

# Review low-confidence matches
cat goals.json | jq -r '.subgoals[] | select(.confidence < 0.7)'

# Update agent capabilities based on learnings
# Edit ~/.aurora/agents/code-developer.json to add new keywords
```

## See Also

- [Configuration Reference](../reference/CONFIG_REFERENCE.md) - Detailed configuration guide
- [Tools Guide](TOOLS_GUIDE.md) - Comprehensive tooling ecosystem documentation (same directory)
- [Planning Flow Workflow](../workflows/planning-flow.md) - Complete planning workflow guide
- [Goals Command Documentation](../commands/aur-goals.md) - Full goals command reference
- [SOAR Architecture](SOAR.md) - SOAR pipeline details
- [ML Models Guide](../ML_MODELS.md) - Custom embedding models
- [Migration Guide](../reference/MIGRATION.md) - Migrating from MCP tools

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

MIT License - See [LICENSE](LICENSE) for details.
