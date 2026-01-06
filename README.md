# AURORA

**Adaptive Unified Reasoning and Orchestration Architecture**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/badge/pypi-v0.4.0-blue)](https://pypi.org/project/aurora-actr/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A cognitive architecture framework that brings intelligent memory, reasoning, and orchestration to AI coding tools. Built on cognitive science principles (ACT-R, SOAR), Aurora enables AI assistants to understand your codebase through persistent memory, semantic search, and multi-step reasoning.

---

## What is Aurora?

Aurora is an **AI-powered codebase intelligence system** that:

- **Indexes your code** with semantic understanding (not just text search)
- **Provides context** to AI coding assistants (Claude Code, Cursor, etc.)
- **Remembers everything** with persistent memory (frequency, recency, relevance)
- **Reasons intelligently** using cognitive architecture patterns
- **No API keys needed** for search and memory features

Think of it as a "smart memory layer" for AI coding tools that makes them understand your specific codebase.

---

## Key Features

### 🔍 **Semantic Code Search**
- Tree-sitter powered parsing (Python, with extensible language support)
- Hybrid retrieval: activation scoring + semantic embeddings
- Sub-500ms search on 10K+ code chunks
- Intelligent ranking by relevance, frequency, and recency

### 🧠 **Persistent Memory**
- ACT-R activation-based memory (cognitive science principles)
- Learns from usage patterns (which code gets referenced most)
- Multi-tier caching for fast retrieval
- Project-local `.aurora/` directory (safe, isolated)

### 🤖 **AI Tool Integration**
- **MCP Protocol:** Works with Claude Code CLI, Cursor, Cline, Continue
- **Slash Commands:** Quick `/aurora-search`, `/aurora-query` commands
- **No API keys required** for MCP tools (uses host LLM)
- Native integration with popular AI coding tools

### 🎯 **SOAR Reasoning Pipeline**
- 9-phase cognitive architecture (Assess → Retrieve → Decompose → ...)
- Automatic escalation (simple vs complex queries)
- Multi-agent orchestration and task decomposition
- Groundedness scoring (prevents hallucination)

### 📋 **Planning System**
- Project-local plan management (`.aurora/plans/`)
- Sequential numbering (0001, 0002, etc.)
- Track features, tasks, and implementation progress
- Integrated with CLI and MCP tools

### 🔧 **Production Ready**
- Cross-platform (Windows, macOS, Linux)
- Comprehensive health checks (`aur doctor`)
- Budget tracking and cost control
- Rich terminal output with progress bars

---

## Installation

### From PyPI (Recommended)

```bash
# Install Aurora (includes all features)
pip install aurora-actr

# Verify installation
aur --version
```

**Current Version:** 0.4.0

**Package Size:** ~528KB (tiny!)

**What's Included:**
- CLI commands (`aur`)
- MCP server (`aurora-mcp`)
- Memory system (semantic search)
- Planning system
- SOAR reasoning engine
- All dependencies

### Optional Extras

```bash
# With ML features (semantic embeddings)
pip install aurora-actr[ml]  # Adds ~1.9GB (PyTorch + models)

# Development tools (for contributors)
pip install aurora-actr[dev]
```

#### ML Features (Optional)

**When to use ML:**
- Large codebases (10K+ files)
- Need conceptual/semantic search ("authentication" finds login(), verify_token(), etc.)
- Searching documentation semantically
- Want best possible search quality

**When to skip ML:**
- Small to medium projects (BM25 + Activation works great!)
- Keyword search is sufficient
- Disk/bandwidth constraints (~1.9GB additional)

**Customizing the embedding model:**

Aurora uses `all-MiniLM-L6-v2` by default (general-purpose, 384-dim, ~80MB model). You can use any [sentence-transformers model](https://www.sbert.net/docs/pretrained_models.html):

```python
from aurora_context_code.semantic import EmbeddingProvider

# Code-optimized model (better for code, weaker for docs)
provider = EmbeddingProvider(model_name="microsoft/codebert-base")

# Smaller/faster model
provider = EmbeddingProvider(model_name="paraphrase-MiniLM-L3-v2")

# Multilingual model (50+ languages)
provider = EmbeddingProvider(model_name="paraphrase-multilingual-MiniLM-L12-v2")
```

**Popular model options:**
- `all-MiniLM-L6-v2` - Default, balanced for code + docs + reasoning (80MB)
- `all-MiniLM-L12-v2` - Better quality, slower (120MB)
- `paraphrase-MiniLM-L3-v2` - Faster, smaller (60MB)
- `microsoft/codebert-base` - Code-specific (500MB)

See [sentence-transformers documentation](https://www.sbert.net/docs/pretrained_models.html) for complete model list and benchmarks.

### From Source

```bash
git clone https://github.com/your-org/aurora.git
cd aurora
pip install -e .
```

---

## Quick Start

### 1. Initialize Aurora in Your Project

```bash
cd /path/to/your/project
aur init
```

This runs 3 unified steps:
1. **Planning Setup** - Creates `.aurora/` directory structure
2. **Memory Indexing** - Indexes your codebase for semantic search
3. **Tool Configuration** - Sets up MCP servers and slash commands for AI tools

**What gets created:**
- `.aurora/` directory (project-local, git-ignored)
- `.aurora/memory.db` (SQLite database for indexed code)
- `.aurora/plans/` (for feature planning)
- MCP and slash command configurations

**Controlling what gets indexed:**

Aurora automatically excludes common noise (venv/, node_modules/, tasks/, CHANGELOG.md, etc.). Customize exclusions with `.auroraignore`:

```bash
# Create .auroraignore in your project root
cat > .auroraignore <<EOF
# Exclude test files
tests/**

# Exclude generated docs
docs/archive/**

# Exclude specific files
CONTRIBUTING.md
EOF

# Re-index to apply changes
aur mem index .
```

**What Aurora indexes:**
- **Code** (type: `code`) - Python files, functions, classes, methods
- **Knowledge** (type: `kb`) - Markdown docs (README.md, docs/, PRDs)
- **SOAR** (type: `soar`) - Reasoning patterns (auto-indexed after `aur soar`)

**Default exclusions:** tasks/, CHANGELOG.md, LICENSE*, venv/, node_modules/, build/, .git/

### 2. Use with AI Coding Tools

**No additional setup required!** Restart your AI tool and Aurora's capabilities are available.

#### Claude Code CLI Example:
```
You: "Search my codebase for authentication logic"
Claude: [Uses aurora_search tool automatically]

You: "Show me the UserService class"
Claude: [Uses aurora_context tool to retrieve full code]

You: "How does the payment flow work?"
Claude: [Uses aurora_query with SOAR reasoning]
```

#### Cursor/Cline/Continue:
Same natural language interaction - tools work automatically via MCP.

### 3. Use CLI Directly (Optional)

```bash
# Search indexed code
aur mem search "authentication"

# Get memory stats
aur mem stats

# Create a plan
aur plan create "Add user authentication"

# Health check
aur doctor
```

**See:** [COMMANDS.md](COMMANDS.md) for complete command reference.

---

## What Aurora Offers

### For AI Coding Assistants:
- **Accurate code search** instead of guessing file locations
- **Semantic understanding** of your codebase structure
- **Context-aware responses** using relevant code chunks
- **No hallucination** - grounded in actual code

### For Developers:
- **One-time indexing** (`aur mem index`) - then instant search
- **Project-local setup** - `.aurora/` directory per project
- **No API keys needed** for search/memory (MCP tools use host LLM)
- **Works offline** for search and planning features

### For Teams:
- **Consistent codebase understanding** across team members
- **Shared plans** in `.aurora/plans/` (can be committed to git)
- **Budget tracking** prevents runaway API costs
- **Audit trail** of queries and reasoning

---

## Commands Overview

Aurora provides three ways to interact with your codebase:

### 1. CLI Commands (`aur`)

```bash
aur init              # Initialize Aurora
aur mem search "..."  # Search code
aur mem index         # Re-index codebase
aur mem stats         # Show stats
aur plan create "..." # Create plan
aur doctor            # Health check
aur --version         # Show version
```

### 2. MCP Tools (via AI Assistants)

Natural language prompts automatically use:
- `aurora_search` - Fast code search
- `aurora_context` - Get code context
- `aurora_query` - Complex reasoning
- `aurora_mem_stats` - Memory stats
- `aurora_doctor` - Health check

### 3. Slash Commands (Quick Access)

```bash
/aurora-search authentication
/aurora-context UserService
/aurora-query How does X work?
/aurora-doctor
```

**Complete Reference:** [COMMANDS.md](COMMANDS.md)

---

## How It Works

### Step 1: Indexing (One-Time)
```bash
aur mem index
```
- Parses your codebase with tree-sitter
- Extracts functions, classes, methods, docstrings
- Creates semantic embeddings (if ML features installed)
- Stores in local `.aurora/memory.db` SQLite database

### Step 2: Activation Scoring (ACT-R)
When you search or query:
- **Frequency:** How often this code is referenced
- **Recency:** When it was last accessed
- **Semantic Similarity:** How relevant to your query
- **Context Boost:** Related to current conversation

### Step 3: Retrieval & Reasoning
- **Simple queries:** Direct memory search (< 2s)
- **Complex queries:** SOAR 9-phase pipeline (< 10s)
- **Groundedness check:** Prevents hallucination on weak matches
- **Multi-step reasoning:** Decomposes complex questions

### Step 4: Integration
- MCP tools provide context to AI assistant
- AI assistant uses host LLM to process and respond
- No extra API calls for search (only for AI reasoning)

---

## Architecture

Aurora is built as a single bundled Python package with modular components:

**Core Components:**
- `aurora_core` - Storage, configuration, data structures
- `aurora_cli` - CLI commands and initialization
- `aurora_context_code` - Code parsing and analysis
- `aurora_soar` - SOAR reasoning pipeline
- `aurora_reasoning` - LLM integration (Anthropic, OpenAI, Ollama)
- `aurora_planning` - Plan management

**Key Patterns:**
- **9-Phase SOAR Pipeline:** Assess → Retrieve → Decompose → Verify → Route → Collect → Synthesize → Record → Respond
- **Hybrid Retrieval:** 60% activation + 40% semantic similarity
- **Multi-Tier Caching:** LRU cache + persistent cache + activation scores
- **Cognitive Memory:** ACT-R principles for intelligent retrieval

**Performance:**
- Simple query: < 2s (measured: 0.002s)
- Complex query: < 10s
- Memory usage: < 100MB for 10K chunks (measured: 39MB)
- Retrieval: < 500ms for 10K chunks

---

## Documentation

### Getting Started
- **[COMMANDS.md](COMMANDS.md)** - Complete command reference (CLI, slash commands)
- **[MIGRATION.md](docs/MIGRATION.md)** - MCP deprecation and migration guide (v1.2.0)
- **[MCP_DEPRECATION.md](docs/MCP_DEPRECATION.md)** - Architecture rationale for MCP deprecation
- [MCP_SETUP.md](docs/MCP_SETUP.md) - AI tool integration guide (deprecated - MCP tools removed)
- [CLI_USAGE_GUIDE.md](docs/cli/CLI_USAGE_GUIDE.md) - Advanced CLI usage
- [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - Common issues

### Architecture & Design
- [SOAR_ARCHITECTURE.md](docs/architecture/SOAR_ARCHITECTURE.md) - 9-phase pipeline
- [AGENT_INTEGRATION.md](docs/architecture/AGENT_INTEGRATION.md) - Agent system
- [API_CONTRACTS_v1.0.md](docs/architecture/API_CONTRACTS_v1.0.md) - API reference

### Development
- [RELEASE.md](RELEASE.md) - Release workflow
- [PRE_PUSH_VALIDATION.md](docs/development/PRE_PUSH_VALIDATION.md) - Quality checks
- [CHANGELOG.md](CHANGELOG.md) - Version history

---

## FAQ

**Q: Do I need an API key?**
A: No API key needed for search, memory, or planning. Only `aur soar` and `aur query` commands that make direct LLM calls require `ANTHROPIC_API_KEY`.

**Q: What AI tools work with Aurora?**
A: Claude Code CLI (via slash commands). MCP tools deprecated in v1.2.0 - see [MIGRATION.md](docs/MIGRATION.md).

**Q: Does Aurora send my code to the cloud?**
A: No. Code stays local in `.aurora/memory.db`. Only when you use `aur query` with API key does it send context to LLM.

**Q: How much does it cost?**
A: Aurora itself is free. If you use `aur query` with Anthropic API, you pay for API usage (~$0.01-0.10 per query depending on size).

**Q: Can I use it offline?**
A: Yes! Search (`aur mem search`), memory, and planning work offline. Only `aur query` and autonomous mode need internet.

**Q: What languages are supported?**
A: Python is fully supported. Extensible to other languages via tree-sitter parsers.

**Q: How do I update Aurora?**
A: `pip install --upgrade aurora-actr`

**Q: Where is my data stored?**
A: Project-local `.aurora/` directory (can be git-ignored or committed).

---

## Development

### Setup

```bash
git clone https://github.com/your-org/aurora.git
cd aurora
pip install -e .[dev]
```

### Testing

```bash
# Run all tests
pytest tests/

# Unit tests only
pytest tests/unit/

# Integration tests
pytest tests/integration/

# With coverage
pytest tests/ --cov=aurora_cli --cov-report=html
```

### Code Quality

```bash
# Format code
ruff check --fix .

# Type checking
mypy packages/cli/src/

# Security scan
bandit -r packages/
```

---

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run quality checks: `ruff check --fix . && mypy packages/*/src/`
5. Submit a pull request

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Support

- **Documentation:** [COMMANDS.md](COMMANDS.md), [MCP_SETUP.md](docs/MCP_SETUP.md)
- **Issues:** [GitHub Issues](https://github.com/your-org/aurora/issues)
- **Discussions:** [GitHub Discussions](https://github.com/your-org/aurora/discussions)

---

**Aurora** - Intelligent memory and reasoning for AI coding assistants • Version 0.4.0 • [PyPI](https://pypi.org/project/aurora-actr/)
