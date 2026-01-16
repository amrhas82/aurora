# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

<!-- AURORA:START -->
# Aurora Instructions

These instructions are for AI assistants working in this project.

Always open `@/.aurora/AGENTS.md` when the request:
- Mentions planning or proposals (words like plan, create, implement)
- Introduces new capabilities, breaking changes, or architecture shifts
- Sounds ambiguous and you need authoritative guidance before coding

Use `@/.aurora/AGENTS.md` to learn:
- How to create and work with plans
- Aurora workflow and conventions
- Project structure and guidelines

Keep this managed block so 'aur init --config' can refresh the instructions.

<!-- AURORA:END -->

---

## Overview

Aurora is a memory-first planning and multi-agent orchestration framework combining ACT-R cognitive memory, SOAR 9-phase reasoning, and CLI-agnostic agent execution. Python 3.10+ monorepo with 9 packages.

---

## Development Commands

### Setup & Installation
```bash
# Install all packages in editable mode
make install            # Production dependencies only
make install-dev        # Includes pytest, ruff, mypy, etc.
./install.sh            # Alternative: shell script that does make install

# Clean build artifacts
make clean
```

### Testing
```bash
# Run all tests
make test

# Run specific test suites
make test-unit          # Unit tests only (~30s)
make test-integration   # Integration tests
make test-performance   # Performance benchmarks

# Run single test file
pytest tests/unit/core/test_store.py -v

# Run single test function
pytest tests/unit/core/test_store.py::test_save_chunk -v

# Run with coverage
make coverage           # Generates HTML report, opens in browser
```

### Code Quality
```bash
# Run linter
make lint               # ruff check

# Auto-fix issues and format
make format             # ruff check --fix + ruff format

# Type checking
make type-check         # mypy on core packages

# All quality checks (lint + type + test)
make quality-check
```

### Performance Benchmarks
```bash
# SOAR startup benchmarks only (~30s)
make benchmark-soar

# All startup benchmarks (~2min)
make benchmark-startup

# Full benchmark suite (~5min)
make benchmark

# Manual benchmark script
python3 benchmark_startup.py
```

### Release
```bash
# Bump version
./scripts/bump-version.sh 0.9.2

# Release to PyPI (requires PyPI credentials)
./scripts/release.sh 0.9.2
```

---

## Architecture

### Package Structure (9 packages)

```
packages/
  core/         aurora_core        Pydantic models, SQLite store, config
  context-code/ aurora_context_code Tree-sitter parsing, BM25, embeddings
  reasoning/    aurora_reasoning   LLM clients (Anthropic, OpenAI, Ollama)
  soar/         aurora_soar        9-phase orchestration pipeline
  planning/     aurora_planning    OpenSpec-inspired plan generation
  spawner/      aurora_spawner     Parallel task execution
  implement/    aurora_implement   Sequential task execution
  cli/          aurora_cli         Click-based CLI (aur command)
  testing/      aurora_testing     Test utilities and fixtures
```

**Critical Patterns:**
- All packages use `hatchling` build system
- Install order matters: core → context-code → reasoning → soar → planning → spawner → implement → cli → testing
- Each package is independently installable but depends on previous packages

### Data Flow

```
aur command (aurora_cli)
    ↓
aurora_context_code (index/search memory)
    ↓
aurora_soar (9-phase pipeline)
    ↓
aurora_planning (generate PRD/tasks)
    ↓
aurora_spawner/aurora_implement (execute tasks)
```

### Configuration Resolution (Multi-Tier)

**Order of precedence** (highest to lowest):
1. CLI flags: `--tool cursor --model opus`
2. Environment variables: `AURORA_GOALS_TOOL=cursor`
3. Project config: `.aurora/config.json`
4. Global config: `~/.aurora/config.json`
5. Built-in defaults

**Critical:** Database is always **project-local** at `.aurora/memory.db`, not global.

### Memory System (ACT-R)

**Hybrid Retrieval** (3 components):
1. **BM25** (keyword search) - 40% weight
2. **ACT-R Activation** (access patterns) - 30% weight
3. **Semantic similarity** (optional embeddings) - 30% weight

**Chunk Types:**
- `code` - Functions, classes (tree-sitter parsed)
- `kb` - Markdown documentation
- `soar` - Cached reasoning traces

**Performance:** Lazy embedding imports (0.9.1+) eliminate 20-30s startup delay.

### SOAR Pipeline (9 Phases)

```
1. ASSESS     -> Complexity scoring (SIMPLE/MEDIUM/COMPLEX/CRITICAL)
2. RETRIEVE   -> Memory search for context
3. DECOMPOSE  -> Break into sub-questions
4. VERIFY     -> Validate decomposition quality
5. ROUTE      -> Assign agents to sub-questions
6. COLLECT    -> Execute agents in parallel (spawn_parallel)
7. SYNTHESIZE -> Combine results
8. RECORD     -> Store reasoning trace
9. RESPOND    -> Format final answer
```

**Critical:** Complexity score determines routing:
- ≤11: Single-step, no spawning
- 12-28: Multi-step, some spawning
- ≥29: Full decomposition, parallel research

### Spawner System

**spawn_parallel_tracked()** is the unified spawning function (as of 0.9.0):
- Stagger delays (5s between agent starts)
- Per-task heartbeat monitoring
- Global timeout calculation
- Circuit breaker pre-checks
- Retry with exponential backoff + LLM fallback

**Both `aur spawn` and SOAR collect phase use this function.**

### CLI Tool Integration (CLIPipeLLMClient)

Works with 20+ tools via pipe interface:
```python
# Tool resolution order:
1. CLI flag (--tool cursor)
2. Env var (AURORA_SPAWN_TOOL)
3. Config file (spawn.default_tool)
4. Default ("claude")
```

**Critical:** All tools must support `-p` flag for non-interactive mode and read prompt from stdin.

### Configurator System (Slash Commands)

**Single Source of Truth:** `packages/cli/src/aurora_cli/templates/slash_commands.py`

All 20 tools use same template bodies via `get_command_body(command_id)`.

**6 commands generated:**
- `search`, `get`, `plan`, `checkpoint`, `implement`, `archive`

**Managed Block System:**
```markdown
<!-- AURORA:START -->
[Template content - managed by Aurora]
<!-- AURORA:END -->

User content here (preserved across updates)
```

**Formats:**
- **Markdown** (14 tools): YAML frontmatter + body
- **TOML** (6 tools): `description` + `prompt` fields

---

## Critical Files & Locations

### Package Entry Points
- CLI commands: `packages/cli/src/aurora_cli/commands/`
- Memory store: `packages/core/src/aurora_core/store/sqlite.py`
- SOAR orchestrator: `packages/soar/src/aurora_soar/orchestrator.py`
- Spawner: `packages/spawner/src/aurora_spawner/spawner.py`
- Code indexer: `packages/context-code/src/aurora_context_code/indexer.py`

### Configuration
- Template source: `packages/cli/src/aurora_cli/templates/slash_commands.py`
- Tool registry: `packages/cli/src/aurora_cli/configurators/slash/registry.py`
- Config schema: `packages/core/src/aurora_core/config/defaults.json`

### Tests
- Unit tests: `tests/unit/` (markers: `@pytest.mark.unit`)
- Integration: `tests/integration/` (markers: `@pytest.mark.integration`)
- Performance: `tests/performance/` (markers: `@pytest.mark.performance`)
- ML tests: Use marker `@pytest.mark.ml` (requires torch/sentence-transformers)

### Project-Local Files (Created by `aur init`)
```
.aurora/
  memory.db       # SQLite database (project-specific)
  config.json     # Project configuration
  plans/          # Generated plans (goals.json, tasks.md, prd.md)
  agents/         # Optional project-specific agents
```

### Global Files
```
~/.aurora/
  config.json            # Global configuration
  budget_tracker.json    # Token usage tracking
  agents/                # Optional global agents
  soar/                  # SOAR reasoning logs
```

---

## Development Patterns

### Adding a New CLI Command

1. Create command file: `packages/cli/src/aurora_cli/commands/mycommand.py`
2. Use Click decorators:
```python
import click
from aurora_cli.main import cli

@cli.command("mycommand")
@click.argument("arg")
@click.option("--flag", default="value")
def mycommand(arg: str, flag: str) -> None:
    """Command description."""
    # Implementation
```
3. Add to `packages/cli/src/aurora_cli/main.py` imports
4. Add tests: `tests/unit/cli/commands/test_mycommand.py`

### Adding a New Tool Configurator

1. Create configurator: `packages/cli/src/aurora_cli/configurators/slash/newtool.py`
2. Choose base class:
   - `SlashCommandConfigurator` (Markdown format)
   - `TomlSlashCommandConfigurator` (TOML format)
3. Implement required methods:
   - `tool_id` (string identifier)
   - `is_available` (detection logic)
   - `get_relative_path()` (file paths for 6 commands)
   - `get_frontmatter()` or `get_description()`
   - `get_body()` (uses `get_command_body()` from templates)
4. Register in `packages/cli/src/aurora_cli/configurators/slash/registry.py`
5. Add tests: `tests/unit/cli/configurators/slash/test_newtool.py`

### Modifying Command Templates

**Location:** `packages/cli/src/aurora_cli/templates/slash_commands.py`

**Impact:** All 20 tools use these templates.

**Testing after changes:**
```bash
./install.sh
cd /tmp/test-project
aur init --config --tools=claude,cursor,gemini
cat .claude/commands/aur/search.md
cat .cursor/commands/aurora-search.md
cat .gemini/commands/aurora/search.toml
```

### Performance Optimization Rules (0.9.1+)

1. **Lazy imports for ML dependencies:**
   ```python
   # Good (lazy)
   def get_embeddings():
       from sentence_transformers import SentenceTransformer
       return SentenceTransformer(...)

   # Bad (eager)
   from sentence_transformers import SentenceTransformer
   model = SentenceTransformer(...)
   ```

2. **Connection pooling** for SQLite (automatic in 0.9.1+)

3. **Deferred schema initialization** (automatic in 0.9.1+)

4. **Regression guards** in `tests/performance/test_soar_startup_performance.py`:
   - `MAX_IMPORT_TIME = 2.0s`
   - `MAX_CONFIG_TIME = 0.5s`
   - `MAX_STORE_INIT_TIME = 0.1s`
   - `MAX_TOTAL_STARTUP_TIME = 3.0s`

### Testing Patterns

**Unit test example:**
```python
import pytest
from aurora_core.models import CodeChunk

@pytest.mark.unit
def test_chunk_creation():
    chunk = CodeChunk(
        chunk_id="test-1",
        file_path="test.py",
        element_type="function",
        name="test_func",
        line_start=1,
        line_end=10,
        signature="def test_func():",
        language="python"
    )
    assert chunk.chunk_id == "test-1"
```

**Integration test example:**
```python
import pytest
from aurora_core.store import SQLiteStore

@pytest.mark.integration
def test_store_integration(tmp_path):
    db_path = tmp_path / "test.db"
    store = SQLiteStore(str(db_path))
    # Test with real database
```

**Performance test example:**
```python
import pytest
import time

@pytest.mark.performance
def test_startup_speed():
    start = time.time()
    # Operation to benchmark
    elapsed = time.time() - start
    assert elapsed < 3.0, f"Too slow: {elapsed}s"
```

### Git Commit Conventions

**Never add Claude as co-author.** Use default git settings only.

**Commit message format:**
```
type: brief description

Longer description if needed.
- Bullet points for details
- Multiple changes

Fixes #123
```

**Types:** `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `chore`

---

## Common Tasks

### Running a Specific Test
```bash
# Single file
pytest tests/unit/core/test_store.py -v

# Single test
pytest tests/unit/core/test_store.py::test_save_chunk -v

# By marker
pytest -m unit -v
pytest -m "unit and not ml" -v
```

### Debugging Failed Tests
```bash
# Verbose output
pytest tests/unit/core/test_store.py -vv

# Show print statements
pytest tests/unit/core/test_store.py -s

# Drop into debugger on failure
pytest tests/unit/core/test_store.py --pdb
```

### Benchmarking Changes
```bash
# Before changes
make benchmark-soar > before.txt

# After changes
make benchmark-soar > after.txt

# Compare
diff before.txt after.txt
```

### Testing Tool Configurators
```bash
# Generate commands
cd /tmp/test-project
aur init --tools=claude

# Verify files created
ls .claude/commands/aur/

# Check content
cat .claude/commands/aur/search.md

# Test update (preserves user content)
aur init --config --tools=claude
```

### Local Development Workflow
```bash
# 1. Install editable
./install.sh

# 2. Make changes

# 3. Run quality checks
make quality-check

# 4. Test in real project
cd /tmp/test-project
aur init
aur mem index .
aur mem search "test query"
```

---

## Documentation

**Index:** `docs/KNOWLEDGE_BASE.md` (quick reference to all docs)

**Key Guides:**
- `docs/guides/COMMANDS.md` - Full CLI reference
- `docs/guides/TOOLS_GUIDE.md` - Architecture, workflows, configurators
- `docs/guides/FLOWS.md` - Workflow patterns
- `docs/PERFORMANCE_TESTING.md` - Performance benchmarking
- `docs/PERFORMANCE_QUICK_REF.md` - Quick perf reference

**Reference:**
- `docs/reference/CONFIG_REFERENCE.md` - Configuration options
- `docs/reference/SOAR_ARCHITECTURE.md` - SOAR pipeline internals
- `docs/reference/API_CONTRACTS_v1.0.md` - Public API contracts
- `docs/reference/AGENT_INTEGRATION.md` - Agent system

---

## Global Agent System

**Location:** `~/.claude/CLAUDE.md` (user's personal global instructions)

**When processing requests:**
- Orchestrator-first routing for complex requests
- Check for agent mentions: `@agent-id` or `As agent-id, ...`
- Skills invocable via `/skill-name`

**Agent Registry:**
- Global: `~/.aurora/agents/`
- Project: `.aurora/agents/`
- Package: `packages/cli/src/aurora_cli/agents/`
