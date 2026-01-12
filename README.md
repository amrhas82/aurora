# Aurora

**Memory-First Planning & Multi-Agent Orchestration Framework**

**Version 0.6.7** | [PyPI](https://pypi.org/project/aurora-actr/) | [Commands](docs/guides/COMMANDS.md) | [Docs](docs/)

Aurora is a local-first development automation framework that uses ACT-R memory, SOAR decomposition, and multi-agent orchestration to systematically break down goals and coordinate specialized agents—all without requiring API access.

Built on planning principles adapted from [OpenSpec](https://github.com/openspec-framework/openspec).

---

## What Aurora Actually Is

Aurora provides three core capabilities:

### Memory (ACT-R)
Intelligent code indexing that learns from usage patterns. Your codebase's memory works like human memory—frequently accessed code stays "hot", rarely used code fades.

**Technology:**
- ACT-R activation scores (chunks strengthen/weaken with use)
- BM25 keyword search (fast, reliable, local)
- Git-aware indexing (respects .gitignore, tracks changes)
- Tree-sitter parsing (understands code structure)
- Optional semantic search (if you want it)

**Use case:** `aur mem index .` ->`aur mem search "authentication"`

### Planning (SOAR + OpenSpec)
Systematic goal decomposition with agent matching and gap detection. Breaks high-level goals into actionable subgoals with automatic agent assignment.

**Technology:**
- SOAR 9-phase pipeline (assess ->retrieve ->decompose ->verify ->route)
- Agent capability matching with LLM fallback
- Gap detection (identifies missing agent capabilities early)
- Memory-aware (uses indexed code to inform planning)
- OpenSpec-inspired workflow (goals ->PRD ->tasks)

**Use case:** `aur goals "Add OAuth2 auth"` ->`/plan` ->`/implement`

### Orchestration (Multi-Agent)
CLI-agnostic agent execution with parallel/sequential coordination. Routes tasks to specialized agents without API lock-in.

**Technology:**
- Works with 20+ CLI tools (claude, cursor, aider, etc.)
- Subprocess-based execution (local-first)
- Dependency-aware scheduling (parallel + sequential)
- Agent specialization (right tool for right job)

**Use case:** `/implement` executes tasks sequentially, `aur spawn tasks.md` executes in parallel

---

## What Aurora Is NOT

**Not deep reasoning** - Aurora uses structured decomposition, not chain-of-thought reasoning like o1
**Not API-dependent** - Core functionality works locally with any CLI tool
**Not magical AI** - It's systematic orchestration, not AGI
**Not a replacement for thinking** - It's a framework for organizing development work

---

## Quick Start

```bash
# Install
pip install aurora-actr

# Initialize project
cd your-project/
aur init

# Index your codebase
aur mem index .

# Search indexed memory
aur mem search "authentication logic"

# Answer complex questions with SOAR reasoning
aur soar "How does the payment flow work?"

# Planning flow: Goal ->PRD ->Tasks ->Implementation
aur goals "Add Stripe payment processing" \
  --context src/checkout/ \
  --verbose

# Output: .aurora/plans/0001-add-stripe-payment/goals.json
# Contains: 5 subgoals, agent assignments, memory context, gaps

# Navigate to plan directory
cd .aurora/plans/0001-add-stripe-payment/

# Generate PRD and tasks (in Claude Code/Cursor/etc.)
/plan

# Execute tasks sequentially with specialized agents
/implement

# Alternative: Execute tasks in parallel (faster but less controlled)
aur spawn tasks.md --verbose

# Health check
aur doctor
```

---

## The Planning Flow

```
+---------------+     +---------------+     +---------------+
|  aur goals    | --> |  /plan        | --> |  /implement   |
|               |     |               |     |               |
| SOAR          |     | OpenSpec      |     | Sequential    |
| decomposes    |     | generates     |     | execution     |
| goal into     |     | PRD +         |     | with          |
| subgoals      |     | tasks.md      |     | specialized   |
| with agents   |     |               |     | agents        |
+---------------+     +---------------+     +---------------+
      |                     |                      |
      v                     v                      v
  goals.json           PRD + tasks            Implemented
  (structured)         (detailed)             (tested)

Alternative parallel execution:
                                          +---------------+
                                          |  aur spawn    |
                                          |               |
                                          | Parallel      |
                                          | execution     |
                                          | (faster)      |
                                          +---------------+
```

**Primary workflow:**
- `aur goals` ->SOAR decomposition with agent matching
- `/plan` ->Generate PRD and tasks (Claude Code skill)
- `/implement` ->Execute tasks sequentially, one by one

**Alternative:**
- `aur spawn tasks.md` ->Execute tasks in parallel (faster, less control)

---

## Real Example

```bash
# 1. Index codebase
$ aur mem index .
[OK] Indexed 2,431 chunks from 342 files

# 2. Decompose goal with SOAR
$ aur goals "Add Stripe payment processing" \
    --context src/checkout/ \
    --verbose

Using tool: claude (model: sonnet)

📋 Decomposing goal into subgoals...
   Goal: Add Stripe payment processing

Memory search found 8 relevant files:
  - src/checkout/cart.py (0.92)
  - src/orders/models.py (0.87)
  - src/api/payments.py (0.81)

🤖 Agent matching results:
   [OK] sg-1: Set up Stripe SDK (@full-stack-dev, 0.89)
   [OK] sg-2: Create payment endpoints (@full-stack-dev, 0.91)
   [OK] sg-3: Add webhook handlers (@full-stack-dev, 0.85)
   [OK] sg-4: Implement payment UI (@ux-expert, 0.78)
   [WARN] sg-5: PCI compliance (@security-engineer, NOT FOUND)

Agent gaps detected:
  - Missing @security-engineer for sg-5
  - Suggested capabilities: ["PCI DSS", "security audit"]
  - Fallback: @full-stack-dev (review required)

[OK] Goals saved to .aurora/plans/0001-add-stripe-payment/goals.json

Next steps:
1. Review goals:   cat .aurora/plans/0001-add-stripe-payment/goals.json
2. Generate PRD:   cd .aurora/plans/0001-add-stripe-payment && /plan
3. Implement:      /implement (sequential) or aur spawn tasks.md (parallel)

# 3. Navigate and generate PRD
$ cd .aurora/plans/0001-add-stripe-payment/
$ /plan  # In Claude Code

[OK] Generated prd.md (1,234 lines)
[OK] Generated tasks.md (24 tasks)

# 4. Execute tasks sequentially (recommended)
$ /implement

Task 1/24: Set up Stripe SDK... COMPLETE [OK]
Task 2/24: Create payment models... COMPLETE [OK]
Task 3/24: Add API endpoints... COMPLETE [OK]
...
Task 24/24: Update documentation... COMPLETE [OK]

All tasks complete! [OK]

# Alternative: Execute in parallel (faster)
$ aur spawn tasks.md --verbose

Spawning 5 tasks across 3 agents:
  [@full-stack-dev] Task 1.0: Set up Stripe SDK... COMPLETE (45s)
  [@full-stack-dev] Task 2.0: Create endpoints... COMPLETE (67s)
  [@ux-expert] Task 4.0: Payment UI... COMPLETE (89s)
  ...

All tasks complete! [OK]
```

---

## Key Features

### Memory System
- **ACT-R activation** - Code chunks strengthen/weaken based on usage
- **Hybrid retrieval** - BM25 + activation + optional semantic
- **Git-aware** - Respects .gitignore, tracks file changes
- **Multi-type storage** - Code, knowledge base, reasoning patterns
- **Sub-500ms search** - Fast retrieval on 10K+ chunks

### Planning Workflow (OpenSpec-Inspired)
- **`aur goals`** - SOAR decomposition with agent matching
- **`/plan` skill** - Generate PRD and tasks from goals.json
- **`/implement`** - Sequential task execution with specialized agents
- **Gap detection** - Identifies missing agent capabilities early
- **Memory-aware** - Uses indexed code to inform planning

### Agent Orchestration
- **CLI-agnostic** - Works with claude, cursor, aider, and 20+ tools
- **Local execution** - No cloud APIs required for core features
- **Sequential + parallel** - `/implement` (careful) or `aur spawn` (fast)
- **Specialized agents** - @full-stack-dev, @ux-expert, @qa-architect, etc.

### Configuration
- **Multi-tier resolution** - CLI flag ->env var ->project config ->global config ->default
- **Tool/model selection** - Per-command configuration
- **Project-local** - `.aurora/config.json` overrides global settings

---

## Installation

### Standard (Lightweight)
```bash
pip install aurora-actr  # ~520KB, BM25 + activation only
```

### With Semantic Search (Optional)
```bash
pip install aurora-actr[ml]  # +1.9GB, adds sentence-transformers
```

**Note:** The ML package uses `all-MiniLM-L6-v2` by default. To use different embedding models (OpenAI, Cohere, custom models), see the [ML Models Guide](docs/reference/ML_MODELS.md).

### Development
```bash
git clone https://github.com/amrhas82/aurora.git
cd aurora
./install.sh
```

---

## What Gets Indexed

Aurora indexes three types of chunks:

- **code** - Functions, classes, methods (tree-sitter AST parsing)
- **kb** - Markdown documentation (README.md, docs/, PRDs)
- **soar** - Reasoning patterns (auto-saved from `aur soar` queries)

**Default exclusions:** `.git/`, `venv/`, `node_modules/`, `tasks/`, `CHANGELOG.md`, `LICENSE*`, `build/`, `dist/`

**Custom exclusions:** Create `.auroraignore` (gitignore-style patterns):

```
# .auroraignore example
tests/**
docs/archive/**
*.tmp
```

---

## Retrieval Strategy

**Hybrid scoring (default, no ML required):**
- 40% BM25 keyword matching
- 30% ACT-R activation (usage frequency + recency)
- 30% Git signals (modification patterns)

**With ML option (`[ml]`):**
- 30% BM25 keyword matching
- 40% Semantic similarity (sentence-transformers)
- 30% ACT-R activation

**Speed:** Sub-500ms on 10K+ chunks.

**Custom models:** See [ML Models Guide](docs/reference/ML_MODELS.md) for using OpenAI, Cohere, or custom embedding models.

---

## Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `aur init` | Initialize project | `aur init` |
| `aur mem index` | Index codebase | `aur mem index .` |
| `aur mem search` | Search memory | `aur mem search "auth"` |
| `aur soar` | Answer questions | `aur soar "How does auth work?"` |
| `aur goals` | Decompose goals | `aur goals "Add feature"` |
| `aur spawn` | Execute tasks (parallel) | `aur spawn tasks.md` |
| `aur agents list` | List agents | `aur agents list` |
| `aur doctor` | Health check | `aur doctor` |

**Skills (in Claude Code):**
- `/plan` - Generate PRD and tasks from goals.json
- `/implement` - Execute tasks sequentially

[Full Command Reference →](docs/guides/COMMANDS.md)

---

## Architecture

### SOAR Pipeline (9 Phases)

**Two execution modes:**

**1. Query Mode (`aur soar`)** - Answer questions about code
- Uses all 9 phases to gather info and synthesize answers
- Executes research agents to collect data
- Returns natural language answer with citations

**2. Goals Mode (`aur goals`)** - Decompose goals for planning
- Uses phases 1-5, 8-9 (skips execution/synthesis)
- Matches subgoals to agents, detects gaps
- Returns structured goals.json for `/plan` skill

**9 Phases:**
1. **Assess** - Determine complexity (keyword + optional LLM)
2. **Retrieve** - Get relevant context from ACT-R memory
3. **Decompose** - Break goal into subgoals with agent assignments
4. **Verify** - Validate decomposition (self or adversarial)
5. **Route** - Match agents, detect capability gaps
6. **Collect** - Execute agents (query mode only)
7. **Synthesize** - Combine outputs (query mode only)
8. **Record** - Cache successful patterns
9. **Respond** - Format output (answer or goals.json)

### OpenSpec-Inspired Planning

Aurora's planning workflow is inspired by and adapted from [OpenSpec](https://github.com/openspec-framework/openspec):

**Core workflow:**
- **goals.json** - Structured goal representation with subgoals
- **PRD generation** - Detailed product requirements from goals
- **Task breakdown** - Actionable tasks with agent assignments
- **Implementation tracking** - Sequential execution with validation

**Aurora's extensions:**
- ACT-R memory integration for context-aware planning
- SOAR decomposition for systematic goal breakdown
- Agent capability matching with gap detection
- CLI-agnostic multi-agent orchestration

---

## Configuration

### Global Config (~/.aurora/config.json)
```json
{
  "goals": {
    "default_tool": "claude",
    "default_model": "sonnet"
  },
  "memory": {
    "index_on_save": true
  },
  "logging": {
    "level": "INFO"
  }
}
```

### Project Config (.aurora/config.json)
```json
{
  "goals": {
    "default_tool": "cursor",
    "default_model": "opus"
  }
}
```

### Environment Variables
```bash
export ANTHROPIC_API_KEY=sk-ant-...
export AURORA_GOALS_TOOL=claude
export AURORA_GOALS_MODEL=sonnet
export AURORA_LOGGING_LEVEL=DEBUG
```

**Resolution order:** CLI flag ->env var ->project config ->global config ->default

[Configuration Reference →](docs/reference/CONFIG_REFERENCE.md)

---

## Documentation

- **[Commands Reference](docs/guides/COMMANDS.md)** - Complete CLI command guide
- **[Tools Guide](docs/guides/TOOLS_GUIDE.md)** - Comprehensive tooling ecosystem
- **[Configuration Reference](docs/reference/CONFIG_REFERENCE.md)** - All settings and environment variables
- **[SOAR Architecture](docs/reference/SOAR_ARCHITECTURE.md)** - Technical pipeline details
- **[Planning Flow](docs/workflows/planning-flow.md)** - End-to-end workflow guide
- **[Goals Command](docs/commands/aur-goals.md)** - Full goals command reference
- **[ML Models Guide](docs/reference/ML_MODELS.md)** - Custom embedding model configuration
- **[Migration Guide](docs/reference/MIGRATION.md)** - Migrating from MCP tools

---

## Design Principles

1. **Memory-First** - ACT-R activation as cognitive foundation
2. **Local Execution** - No cloud APIs required for core features
3. **CLI-Agnostic** - Works with any tool, no vendor lock-in
4. **Systematic Over Magical** - Structured pipelines, not black boxes
5. **Honest Capabilities** - We decompose and orchestrate, we don't "reason deeply"
6. **OpenSpec-Inspired** - Proven planning workflow patterns

---

## Requirements

- Python 3.10+
- Git (for git-aware indexing)
- One or more CLI tools: claude, cursor, aider, etc.
- Optional: Anthropic API key (for semantic search with ML package)

**Disk space:**
- Base install: ~520KB
- With ML features: ~1.9GB (PyTorch + sentence-transformers)

---

## Credits

- **[OpenSpec](https://github.com/openspec-framework/openspec)** - Planning and implementation workflow patterns
- **ACT-R** - Cognitive architecture for memory modeling
- **SOAR** - Cognitive architecture for goal decomposition
- **Tree-sitter** - Code parsing
- **Anthropic Claude** - LLM capabilities (when using API)

---

## License

MIT License - See [LICENSE](LICENSE) for details.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.
