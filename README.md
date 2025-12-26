# AURORA

**Adaptive Unified Reasoning and Orchestration Architecture**

A cognitive architecture framework that brings intelligent memory, reasoning, and orchestration capabilities to AI systems. Built on cognitive science principles (ACT-R, SOAR), AURORA enables AI agents to maintain persistent context, learn from experience, and coordinate complex tasks efficiently.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Features

**MCP Server Integration**
- Native Claude Code CLI integration via Model Context Protocol
- 7 powerful tools for seamless codebase search, analysis, and intelligent querying
- No API key required - MCP tools provide context to Claude Code CLI's built-in LLM
- Conversation-driven development workflow directly from your terminal

**Cognitive Reasoning**
- ACT-R activation-based memory (frequency, recency, semantic similarity)
- SOAR-inspired 9-phase orchestration pipeline for complex reasoning
- Intelligent query assessment with automatic escalation

**Semantic Memory & Context**
- Persistent memory with sentence-transformer embeddings
- Hybrid retrieval (60% activation + 40% semantic similarity)
- Multi-tier caching for sub-500ms retrieval on 10K+ chunks

**Agent Orchestration**
- Discover and coordinate multiple AI agents by capability
- Parallel and sequential task execution
- Support for local, remote, and MCP-based agents

**Code Understanding**
- Tree-sitter powered parsing for Python (extensible to other languages)
- Intelligent chunking with complexity analysis
- Dependency tracking and docstring extraction

**Production Ready**
- Cross-platform support (Windows, macOS, Linux)
- Cost tracking and budget enforcement
- Comprehensive error handling with actionable messages
- Retry logic with exponential backoff

---

## Installation

**From PyPI (Recommended)**

```bash
# Install with all features
pip install aurora-actr[all]

# Or minimal installation (no ML dependencies)
pip install aurora-actr

# Verify installation
aur --verify
```

**From Source**

```bash
git clone https://github.com/aurora-project/aurora.git
cd aurora
pip install -e ".[all]"
```

**Note:** Package is published as `aurora-actr` on PyPI, but import as `from aurora.core import ...`

---

## Quick Start

### MCP Server with Claude Code CLI (Primary Workflow)

AURORA integrates with Claude Code CLI via the Model Context Protocol, enabling you to search and analyze your codebase directly from your development sessions.

#### 1. Install and Index Your Codebase

```bash
pip install aurora-actr[all]
cd /path/to/your/project
aur mem index .
```

#### 2. Configure Claude Code CLI

Create AURORA's MCP configuration:

**Location:** `~/.claude/plugins/aurora/.mcp.json`

```json
{
  "aurora": {
    "command": "python3",
    "args": ["-m", "aurora.mcp.server"],
    "env": {
      "AURORA_DB_PATH": "${HOME}/.aurora/memory.db",
      "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY}"
    }
  }
}
```

Add tool permissions to `~/.claude/settings.local.json`:

```json
{
  "permissions": {
    "allow": [
      "mcp__aurora__aurora_query",
      "mcp__aurora__aurora_search",
      "mcp__aurora__aurora_index",
      "mcp__aurora__aurora_stats",
      "mcp__aurora__aurora_context",
      "mcp__aurora__aurora_related",
      "mcp__aurora__aurora_get"
    ]
  }
}
```

#### 3. Use with Claude Code CLI

Restart Claude Code CLI and AURORA's tools are available in your sessions:

- *"Search my codebase for authentication logic"* → `aurora_search`
- *"Find all usages of the DatabaseConnection class"* → `aurora_search`
- *"Show me error handling in payment processing"* → `aurora_context`
- *"What does the UserService module do?"* → `aurora_context`
- *"Compare our API patterns with best practices"* → `aurora_query` (auto-escalates to SOAR)

Claude Code CLI automatically uses AURORA's tools to search your indexed codebase and provide contextual answers.

**Important:** MCP tools do NOT require API keys. They provide context/search results that Claude Code CLI's built-in LLM processes. No additional API costs beyond your Claude subscription.

**See:** [MCP Setup Guide](docs/MCP_SETUP.md) for detailed configuration and troubleshooting.

---

### Standalone CLI Usage

Use AURORA's CLI directly for queries, memory management, and autonomous reasoning.

**Note:** CLI commands like `aur query` require an `ANTHROPIC_API_KEY` environment variable (they run LLM inference directly). For API-key-free usage, use MCP integration instead.

#### Basic Queries

```bash
# Simple query (fast direct LLM) - requires API key
aur query "What is a Python decorator?"

# Complex query (full AURORA pipeline with context) - requires API key
aur query "How does the authentication system work?"

# Force specific mode - requires API key
aur query "Explain classes" --force-aurora --verbose
```

#### Memory Management

```bash
# Index current directory - no API key required
aur mem index

# Search indexed code - no API key required
aur mem search "authentication"

# View statistics - no API key required
aur mem stats

# Advanced search - no API key required
aur mem search "database" --limit 10 --show-content --format json
```

#### Headless Mode (Autonomous Reasoning)

```bash
# Run autonomous experiment
aur headless experiment.md

# Custom budget and iterations
aur headless experiment.md --budget 10.0 --max-iter 20

# Dry run (validation only)
aur headless experiment.md --dry-run
```

**Safety features:** Git branch enforcement, budget limits, iteration caps

#### Verification and Diagnostics

```bash
# Check installation health
aur --verify

# Check MCP server status
aurora-mcp status

# View help
aur --help
```

**CLI Features:**
- Automatic escalation (direct LLM vs AURORA pipeline)
- Hybrid search (activation + semantic)
- Configuration management (env vars, config files)
- Rich terminal output with progress bars
- Installation verification and diagnostics

---

## Usage Examples

### Example 1: Codebase Q&A with Claude Desktop

**Scenario:** You're working on a large codebase and need to quickly understand authentication logic.

1. Index your codebase: `aur mem index .`
2. Open Claude Desktop
3. Ask: *"Find all authentication-related functions and explain the flow"*
4. Claude uses AURORA to search, retrieve relevant code, and explain the implementation

**Benefits:** No manual file hunting, contextual understanding, instant answers

### Example 2: Autonomous Code Analysis

**Scenario:** You want to analyze code quality across your project autonomously.

1. Create experiment file: `analyze_code_quality.md`
2. Run: `aur headless analyze_code_quality.md`
3. AURORA executes reasoning loop, analyzes code, generates report
4. Safety controls prevent unwanted changes

**Benefits:** Hands-free analysis, systematic coverage, safety guarantees

### Example 3: Multi-Agent Orchestration

**Scenario:** Complex task requiring multiple AI capabilities (code generation, review, testing).

```python
from aurora_soar import SOAROrchestrator, AgentRegistry
from aurora_reasoning import AnthropicClient

# Initialize orchestrator with agent registry
orchestrator = SOAROrchestrator(
    store=store,
    agent_registry=AgentRegistry(),
    reasoning_llm=AnthropicClient()
)

# Execute complex query - AURORA decomposes, routes to agents, synthesizes
result = orchestrator.execute(
    query="Implement JWT authentication with tests and security review"
)

print(f"Agents used: {result['metadata']['agents_used']}")
print(f"Confidence: {result['confidence']:.2f}")
```

**Benefits:** Coordinated multi-agent execution, automatic routing, cost tracking

---

## Python API

Quick examples for programmatic use:

**Parse and Store Code**

```python
from aurora_core.store import SQLiteStore
from aurora_context_code import PythonParser

store = SQLiteStore("aurora.db")
parser = PythonParser()
chunks = parser.parse_file("example.py")

for chunk in chunks:
    store.save_chunk(chunk)
```

**Context Retrieval with Scoring**

```python
from aurora_core.context import CodeContextProvider

provider = CodeContextProvider(store, parser_registry)
results = provider.retrieve("authentication logic", max_results=5)

for chunk in results:
    print(f"{chunk.metadata['name']} (score: {chunk.metadata['_score']:.2f})")
```

**SOAR Orchestrator**

```python
from aurora_soar import SOAROrchestrator

orchestrator = SOAROrchestrator(store, agent_registry, reasoning_llm)
result = orchestrator.execute(query="Analyze security vulnerabilities")
```

**Full API documentation:** [API Reference](docs/architecture/API_CONTRACTS_v1.0.md)

---

## Architecture

AURORA is organized as a Python monorepo with modular packages:

**Core Packages:**

- **aurora-core** - Storage, chunks, configuration, context providers, cost tracking
- **aurora-context-code** - Code parsing (Python via tree-sitter, extensible)
- **aurora-soar** - Agent registry, 9-phase orchestration pipeline
- **aurora-reasoning** - LLM integration (Anthropic, OpenAI, Ollama), reasoning logic
- **aurora-testing** - Testing utilities, fixtures, mocks, benchmarks

**Key Architecture Patterns:**

- **9-Phase SOAR Pipeline:** Assess → Retrieve → Decompose → Verify → Route → Collect → Synthesize → Record → Respond
- **ACT-R Memory Activation:** Frequency, recency, semantic similarity, context boost
- **Hybrid Retrieval:** 60% activation scoring + 40% semantic similarity
- **Multi-Tier Caching:** Hot cache (LRU) + persistent cache + activation scores (10min TTL)
- **Cost Optimization:** Keyword-based assessment bypasses LLM for 60-70% of simple queries

**Performance:**

- Simple query latency: <2s (achieved: 0.002s)
- Complex query latency: <10s
- Memory usage: <100MB for 10K chunks (achieved: 39MB)
- Retrieval: <500ms for 10K chunks

**Detailed architecture:** [SOAR Architecture](docs/architecture/SOAR_ARCHITECTURE.md), [Verification Checkpoints](docs/reports/quality/VERIFICATION_CHECKPOINTS.md)

---

## Documentation

**Getting Started**
- [MCP Setup Guide](docs/MCP_SETUP.md) - Claude Desktop integration
- [Quick Start](docs/cli/QUICK_START.md) - Get started in 5 minutes
- [CLI Usage Guide](docs/cli/CLI_USAGE_GUIDE.md) - Comprehensive command reference
- [Troubleshooting Guide](docs/TROUBLESHOOTING.md) - Common issues and solutions

**Architecture & Design**
- [SOAR Architecture](docs/architecture/SOAR_ARCHITECTURE.md) - 9-phase pipeline details
- [Verification Checkpoints](docs/reports/quality/VERIFICATION_CHECKPOINTS.md) - Scoring and thresholds
- [Agent Integration Guide](docs/architecture/AGENT_INTEGRATION.md) - Agent formats and execution
- [Cost Tracking Guide](docs/guides/COST_TRACKING_GUIDE.md) - Budget management
- [Prompt Engineering Guide](docs/development/PROMPT_ENGINEERING_GUIDE.md) - Template design

**Development**
- [Pre-Push Validation](docs/development/PRE_PUSH_VALIDATION.md) - Local CI/CD checks before pushing
- [API Contracts](docs/architecture/API_CONTRACTS_v1.0.md) - API reference
- [Migration Guide](docs/development/PHASE4_MIGRATION_GUIDE.md) - Upgrade guide
- [Code Review Report](docs/reports/quality/CODE_REVIEW_REPORT_v1.0.0-phase3.md) - Quality analysis
- [Security Audit](docs/reports/security/SECURITY_AUDIT_REPORT_v1.0.0-phase3.md) - Security review

**Project History**
- [Release Notes](RELEASE_NOTES_v1.0.0-phase3.md) - Version history
- [Phase Archives](docs/phases/phase3/PHASE3_ARCHIVE_MANIFEST.md) - Development phases

---

## Development

**Setup Development Environment**

```bash
# Clone and install with dev dependencies
git clone https://github.com/aurora-project/aurora.git
cd aurora
make install-dev

# Run quality checks
make quality-check
```

**Common Commands**

```bash
make test              # Run all tests (1,766+ tests, 97% pass rate)
make test-unit         # Unit tests only
make lint              # Ruff linter
make format            # Format code
make type-check        # MyPy type checker (100% type safety)
make benchmark         # Performance benchmarks
make coverage          # HTML coverage report (74%+ coverage)
```

**Code Quality Standards**

- **Linting:** Ruff with comprehensive rules
- **Type Checking:** MyPy strict mode (zero type errors)
- **Test Coverage:** 74%+ coverage maintained
- **Security:** Bandit security scanning
- **Performance:** Benchmarks for critical operations

**Contributing**

Contributions welcome! Please ensure:

1. All tests pass (`make test`)
2. Code is formatted (`make format`)
3. Type checking passes (`make type-check`)
4. New features include tests
5. Documentation updated

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Contact

For questions, issues, or discussions:
- **GitHub Issues:** [aurora-project/aurora/issues](https://github.com/aurora-project/aurora/issues)
- **Discussions:** [aurora-project/aurora/discussions](https://github.com/aurora-project/aurora/discussions)

---

**AURORA** - Intelligent AI systems with persistent memory and cognitive reasoning
