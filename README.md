# AURORA

**Version 0.5.1** | [PyPI](https://pypi.org/project/aurora-actr/) | [Commands](COMMANDS.md) | [Configuration](docs/CONFIG_REFERENCE.md) | [SOAR Reasoning](docs/SOAR.md)

Adaptive Unified Reasoning and Orchestration Architecture - Project-based AI memory and reasoning system.

## What It Does

AURORA adds persistent memory and structured reasoning to AI coding tools (Claude Code, Cursor, etc.).

**Three core capabilities:**

1. **Multi-turn SOAR Reasoning** - 9-phase cognitive pipeline for complex queries with automatic escalation
2. **Planning & Agent Discovery** - OpenSpec-adapted workflow orchestration with agent registry
3. **ACT-R Memory** - Tree-sitter AST indexing with activation-based retrieval for code, knowledge, and reasoning patterns

**Retrieval modes:**
- Lightweight: BM25 keyword + Git signals + ACT-R activation (default, ~520KB)
- Enhanced: Add semantic embeddings with optional ML package (~1.9GB)

**Storage:** Project-local `.aurora/` directory (SQLite database, no cloud required).

## Installation

### PyPI (Recommended)

```bash
pip install aurora-actr
```

### With Semantic Search (Optional)

```bash
pip install aurora-actr[ml]  # Adds PyTorch + sentence-transformers (~1.9GB)
```

### Development

```bash
git clone https://github.com/amrhas82/aurora.git
cd aurora
./install.sh
```

## Quick Start

```bash
# Initialize in your project
cd your-project/
aur init

# Index your codebase
aur mem index .

# Search indexed memory
aur mem search "authentication logic"

# Multi-turn SOAR reasoning
aur soar "How does the payment flow work?"

# Create implementation plan
aur plan create "Add user authentication"

# Health check
aur doctor
```

## What Gets Indexed

AURORA indexes three types of chunks:

- **code** - Python functions, classes, methods (tree-sitter AST parsing)
- **kb** - Markdown documentation (README.md, docs/, PRDs)
- **soar** - Reasoning patterns (auto-saved after `aur soar` queries)

**Default exclusions:** `.git/`, `venv/`, `node_modules/`, `tasks/`, `CHANGELOG.md`, `LICENSE*`, `build/`, `dist/`

**Custom exclusions:** Create `.auroraignore` (gitignore-style patterns):

```
# .auroraignore example
tests/**
docs/archive/**
*.tmp
```

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

## Documentation

- [Commands Reference](COMMANDS.md) - Complete CLI command documentation
- [Configuration Reference](docs/CONFIG_REFERENCE.md) - All config settings, file locations, and environment variables
- [SOAR Reasoning](docs/SOAR.md) - 9-phase cognitive pipeline details
- [ML Models Guide](docs/ML_MODELS.md) - Custom embedding model configuration
- [MCP Deprecation](docs/MCP_DEPRECATION.md) - Why MCP tools were deprecated
- [Migration Guide](docs/MIGRATION.md) - Migrating from MCP tools to slash commands

## Architecture

**Cognitive Foundations:**
- ACT-R activation-based memory (cognitive science)
- SOAR 9-phase reasoning pipeline (State/Operator/Result)
- Tree-sitter for accurate AST parsing

**Design Principles:**
- Project-local (no cloud, `.aurora/` directory)
- Lightweight by default (BM25 + activation)
- Optional semantic search (ML package)
- No API keys for memory/search operations

## Configuration

Aurora stores configuration in JSON files with environment variable overrides.

**File locations:**
- `~/.aurora/config.json` - Global user settings
- `.aurora/config.json` - Project-specific settings (takes precedence)

**Quick example:**
```json
{
  "soar": {
    "default_tool": "cursor",
    "default_model": "opus"
  },
  "logging": {
    "level": "DEBUG"
  }
}
```

**Environment variables:**
```bash
export ANTHROPIC_API_KEY=sk-ant-...
export AURORA_SOAR_TOOL=cursor
export AURORA_LOGGING_LEVEL=DEBUG
```

See [Configuration Reference](docs/CONFIG_REFERENCE.md) for all settings.

**Other configuration:**
- **Excluding files:** Create `.auroraignore` in project root
- **ML models:** See [ML Models Guide](docs/ML_MODELS.md)

## Requirements

- Python 3.10+
- ~520KB (base install)
- ~1.9GB additional (with ML features)

## License

MIT License

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)
