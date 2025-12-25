# AURORA - Knowledge Base

> Complete reference documentation for the Aurora cognitive architecture framework

**Version**: v0.2.0 (Production Ready)
**Last Updated**: December 25, 2025
**Project Root**: /home/hamr/PycharmProjects/aurora

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Package Reference](#package-reference)
4. [Development Guide](#development-guide)
5. [Usage Guide](#usage-guide)
6. [MCP Integration](#mcp-integration)
7. [Testing](#testing)
8. [Performance](#performance)
9. [Security](#security)
10. [Troubleshooting](#troubleshooting)
11. [Release History](#release-history)
12. [Research Background](#research-background)
13. [Resources](#resources)

---

## Overview

### What is AURORA?

AURORA (Adaptive Unified Reasoning and Orchestration Architecture) is a cognitive architecture framework that brings intelligent memory, reasoning, and orchestration capabilities to AI systems. Built on cognitive science principles from ACT-R and SOAR, AURORA enables AI agents to:

- Maintain persistent context across sessions
- Learn from experience through activation-based memory
- Reason about complex queries through multi-phase decomposition
- Coordinate multiple AI agents efficiently
- Parse and understand code semantically

### Key Features

**Cognitive Reasoning**
- ACT-R activation-based memory (frequency, recency, semantic similarity)
- SOAR-inspired 9-phase orchestration pipeline
- Intelligent query assessment with automatic escalation
- Multi-stage verification (self-verification + adversarial)

**Semantic Memory & Context**
- Persistent memory with sentence-transformer embeddings
- Hybrid retrieval (60% activation + 40% semantic similarity)
- Multi-tier caching for sub-500ms retrieval on 10K+ chunks
- ReasoningChunk storage for pattern learning

**Agent Orchestration**
- Discover and coordinate multiple AI agents by capability
- Parallel and sequential task execution
- Support for local, remote, and MCP-based agents
- Intelligent routing with fallback strategies

**Code Understanding**
- Tree-sitter powered parsing for Python (extensible)
- Intelligent chunking with complexity analysis
- Dependency tracking and docstring extraction
- Function, class, and module-level granularity

**Production Ready**
- Cross-platform support (Windows, macOS, Linux)
- Cost tracking and budget enforcement
- Comprehensive error handling with actionable messages
- Retry logic with exponential backoff
- 1,766+ tests, 97% pass rate, 74%+ coverage

### Tech Stack

- **Language**: Python 3.10+
- **Storage**: SQLite with JSON fields
- **Parsing**: tree-sitter (Python grammar)
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **LLM Integration**: Anthropic Claude, OpenAI GPT-4, Ollama
- **CLI**: Rich terminal UI with progress bars
- **MCP**: Model Context Protocol for Claude Desktop
- **Testing**: pytest, pytest-asyncio, pytest-cov
- **Quality**: ruff (linting), mypy (type checking), bandit (security)

### Quick Links

- **PyPI**: `pip install aurora-actr[all]`
- **Import**: `from aurora.core import ...`
- **CLI**: `aur --help`
- **MCP Setup**: [MCP_SETUP.md](../MCP_SETUP.md)
- **GitHub**: https://github.com/aurora-project/aurora (placeholder)

---

## Architecture

### System Design

AURORA implements a layered cognitive architecture:

```
┌─────────────────────────────────────────────┐
│         Interfaces (MCP, CLI)               │
├─────────────────────────────────────────────┤
│    SOAR Orchestrator (9-Phase Pipeline)     │
├─────────────────────────────────────────────┤
│  Reasoning Engine (LLM Integration)         │
├─────────────────────────────────────────────┤
│  Memory System (ACT-R Activation)           │
├─────────────────────────────────────────────┤
│  Context Providers (Code, Reasoning)        │
├─────────────────────────────────────────────┤
│  Storage Layer (SQLite + Embeddings)        │
└─────────────────────────────────────────────┘
```

### 9-Phase SOAR Pipeline

**Detailed Documentation**: [architecture/SOAR_ARCHITECTURE.md](./architecture/SOAR_ARCHITECTURE.md)

1. **Assess** - Classify query complexity (SIMPLE/MEDIUM/COMPLEX/CRITICAL) using keywords + LLM
2. **Retrieve** - Fetch relevant context from memory using hybrid activation+semantic scoring
3. **Decompose** - Break complex queries into executable subgoals with agent assignments
4. **Verify** - Multi-stage verification (self-verify or adversarial) with scoring
5. **Route** - Match subgoals to capable agents with fallback strategies
6. **Collect** - Execute agents (parallel/sequential) with retry logic
7. **Synthesize** - Generate natural language synthesis from agent outputs
8. **Record** - Cache successful patterns in ACT-R memory with activation updates
9. **Respond** - Format response based on verbosity level (QUIET/NORMAL/VERBOSE/JSON)

**Performance**:
- Simple queries bypass decomposition (0.002s latency)
- Keyword assessment eliminates 60-70% of LLM calls
- Complex queries complete in <10s
- Verification accuracy: 100% catch rate on bad decompositions

### ACT-R Activation Model

**Detailed Documentation**: [actr-activation.md](./actr-activation.md)

**Activation Formula**:
```
A = Base + Frequency + Recency + Similarity + Context
```

**Components**:
- **Base Activation**: 0.0 (neutral starting point)
- **Frequency Boost**: +0.1 per access (max +1.0)
- **Recency Decay**: Exponential decay over time (d = 0.5, τ = 24h)
- **Semantic Similarity**: Cosine similarity with query embedding
- **Context Boost**: +0.3 for same project/file

**Retrieval Strategy**:
- Hybrid scoring: 0.6 × activation + 0.4 × semantic similarity
- Top-K selection (default: 5 chunks)
- Activation TTL: 10 minutes (hot cache)

### Multi-Tier Caching

1. **Hot Cache (LRU)**: In-memory, recently accessed chunks (<500ms)
2. **Persistent Cache**: SQLite activation scores (10min TTL)
3. **Embedding Cache**: Pre-computed embeddings for fast similarity search
4. **Pattern Cache**: Successful ReasoningChunks for pattern reuse

### Agent Registry

**Detailed Documentation**: [architecture/AGENT_INTEGRATION.md](./architecture/AGENT_INTEGRATION.md)

**Agent Types**:
- **Local Agents**: Execute locally via subprocess/module import
- **Remote Agents**: HTTP/gRPC APIs with retry logic
- **MCP Agents**: Model Context Protocol tools
- **LLM Agents**: Direct LLM calls with prompt templates

**Execution Patterns**:
- Sequential: `["A", "B", "C"]` (ordered execution)
- Parallel: `[["A", "B"], "C"]` (A and B concurrently, then C)
- Fallback: Try alternative agents on failure

---

## Package Reference

### aurora-core

**Location**: `packages/core/`
**Import**: `from aurora.core import ...`

**Key Components**:
- `Store` - SQLite storage with activation scoring
- `CodeChunk` - Code fragment representation
- `ReasoningChunk` - Reasoning pattern storage
- `CostTracker` - Budget tracking and enforcement
- `CodeContextProvider` - Context retrieval with scoring
- `Config` - Configuration management

**Documentation**:
- API Contracts: [architecture/API_CONTRACTS_v1.0.md](./architecture/API_CONTRACTS_v1.0.md)
- Package README: [../packages/core/README.md](../packages/core/README.md)

### aurora-context-code

**Location**: `packages/context-code/`
**Import**: `from aurora.context_code import ...`

**Key Components**:
- `PythonParser` - tree-sitter based Python parser
- `ParserRegistry` - Multi-language parser registry
- `CodeChunker` - Intelligent code chunking
- `DependencyTracker` - Import and dependency analysis

**Features**:
- Function-level granularity
- Class-level grouping
- Docstring extraction
- Complexity analysis (cyclomatic complexity)
- Extensible to other languages (TypeScript, Java, Go)

**Documentation**:
- Package README: [../packages/context-code/README.md](../packages/context-code/README.md)

### aurora-soar

**Location**: `packages/soar/`
**Import**: `from aurora.soar import ...`

**Key Components**:
- `SOAROrchestrator` - 9-phase pipeline orchestrator
- `AgentRegistry` - Agent discovery and routing
- `QueryDecomposer` - LLM-based query decomposition
- `Verifier` - Multi-stage verification system
- `AgentExecutor` - Parallel/sequential execution

**Verification Modes**:
- **Option A (Self-Verification)**: Fast, single-pass (~$0.001)
- **Option B (Adversarial)**: Rigorous, dual-perspective (~$0.005)

**Documentation**:
- SOAR Architecture: [architecture/SOAR_ARCHITECTURE.md](./architecture/SOAR_ARCHITECTURE.md)
- Verification: [reports/quality/VERIFICATION_CHECKPOINTS.md](./reports/quality/VERIFICATION_CHECKPOINTS.md)
- Package README: [../packages/soar/README.md](../packages/soar/README.md)

### aurora-reasoning

**Location**: `packages/reasoning/`
**Import**: `from aurora.reasoning import ...`

**Key Components**:
- `AnthropicClient` - Claude API integration
- `OpenAIClient` - GPT-4 API integration
- `OllamaClient` - Local Ollama integration
- `PromptTemplate` - Template management
- `LLMResponse` - Structured response parsing

**Supported Models**:
- Anthropic: Sonnet 4.5, Opus 4.5, Haiku
- OpenAI: GPT-4, GPT-4 Turbo, GPT-3.5 Turbo
- Ollama: Llama 3, Mistral, custom models

**Features**:
- Automatic retry with exponential backoff
- Token counting and cost tracking
- JSON extraction from markdown
- Provider-specific pricing

**Documentation**:
- Package README: [../packages/reasoning/README.md](../packages/reasoning/README.md)
- Prompt Engineering: [development/PROMPT_ENGINEERING_GUIDE.md](./development/PROMPT_ENGINEERING_GUIDE.md)

### aurora-cli

**Location**: `packages/cli/`
**Entry Point**: `aur` command

**Commands**:
- `aur query "text"` - Query with auto-escalation
- `aur mem index <path>` - Index code directory
- `aur mem search "text"` - Search indexed code
- `aur mem stats` - Memory statistics
- `aur headless <file>` - Autonomous reasoning
- `aur --verify` - Installation verification
- `aurora-mcp status` - MCP server status

**Documentation**:
- Quick Start: [cli/QUICK_START.md](./cli/QUICK_START.md)
- CLI Usage Guide: [cli/CLI_USAGE_GUIDE.md](./cli/CLI_USAGE_GUIDE.md)
- Error Catalog: [cli/ERROR_CATALOG.md](./cli/ERROR_CATALOG.md)
- Package README: [../packages/cli/README.md](../packages/cli/README.md)

### aurora-testing

**Location**: `packages/testing/`
**Import**: `from aurora.testing import ...`

**Key Components**:
- `MockStore` - Test store with in-memory SQLite
- `MockLLMClient` - Mock LLM for testing
- `TestFixtures` - Reusable test data
- `BenchmarkRunner` - Performance benchmarking

**Documentation**:
- Testing Guide: [development/TESTING.md](./development/TESTING.md)
- Package README: [../packages/testing/README.md](../packages/testing/README.md)

---

## Development Guide

### Setup Development Environment

**Prerequisites**:
- Python 3.10+ (tested on 3.10, 3.11, 3.12)
- Git
- Make (optional, for convenience commands)

**Installation**:
```bash
# Clone repository
git clone https://github.com/aurora-project/aurora.git
cd aurora

# Install with dev dependencies
make install-dev

# Or manual installation
pip install -e "packages/core[dev]"
pip install -e "packages/context-code[dev]"
pip install -e "packages/reasoning[dev]"
pip install -e "packages/soar[dev]"
pip install -e "packages/cli[dev]"
pip install -e "packages/testing[dev]"
```

### Development Workflow

**Detailed Documentation**: [development/EXTENSION_GUIDE.md](./development/EXTENSION_GUIDE.md)

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Write Tests First** (TDD)
   ```bash
   # Create test in tests/unit/package/
   pytest tests/unit/package/test_my_feature.py -v
   ```

3. **Implement Feature**
   ```bash
   # Edit code in packages/package/src/aurora_package/
   ```

4. **Run Quality Checks**
   ```bash
   make quality-check  # Runs lint, type-check, test
   ```

5. **Commit and Push**
   ```bash
   git add .
   git commit -m "feat: implement my feature"
   git push origin feature/my-feature
   ```

6. **Create Pull Request**
   - Ensure CI passes
   - Request code review
   - Address feedback

### Code Quality Standards

**Detailed Documentation**: [development/CODE_REVIEW_CHECKLIST.md](./development/CODE_REVIEW_CHECKLIST.md)

**Linting (Ruff)**:
```bash
make lint          # Check for issues
make format        # Auto-fix formatting
```

**Type Checking (MyPy)**:
```bash
make type-check    # Strict mode, 0 errors required
```

**Testing (Pytest)**:
```bash
make test          # All tests
make test-unit     # Unit tests only
make coverage      # HTML coverage report
```

**Security (Bandit)**:
```bash
bandit -r packages/ -ll  # Security scan
```

**Performance Benchmarks**:
```bash
make benchmark     # Run performance tests
```

### Configuration Files

- **pyproject.toml** - Central project config (dependencies, build, tools)
- **pytest.ini** - Pytest configuration
- **mypy.ini** - MyPy strict mode settings
- **ruff.toml** - Ruff linting rules
- **Makefile** - Development convenience commands

### Extending AURORA

**Add New Parser** (e.g., TypeScript):
1. Create parser class in `packages/context-code/src/aurora_context_code/parsers/`
2. Implement `Parser` protocol (parse_file, chunk_code)
3. Register in `ParserRegistry`
4. Add tests in `tests/unit/context-code/parsers/`

**Add New LLM Provider** (e.g., Cohere):
1. Create client class in `packages/reasoning/src/aurora_reasoning/llm/`
2. Implement `LLMClient` protocol (generate, count_tokens, cost)
3. Add tests in `tests/unit/reasoning/llm/`
4. Update documentation

**Add New Agent Type**:
1. Implement agent in `packages/soar/src/aurora_soar/agents/`
2. Register in `AgentRegistry`
3. Add tests in `tests/unit/soar/agents/`
4. Update agent integration docs

**Documentation**:
- Extension Guide: [development/EXTENSION_GUIDE.md](./development/EXTENSION_GUIDE.md)
- API Contracts: [architecture/API_CONTRACTS_v1.0.md](./architecture/API_CONTRACTS_v1.0.md)

---

## Usage Guide

### Installation

**From PyPI (Recommended)**:
```bash
# Full installation (with ML dependencies)
pip install aurora-actr[all]

# Minimal installation (no embeddings, no ML)
pip install aurora-actr

# Verify installation
aur --verify
```

**From Source**:
```bash
git clone https://github.com/aurora-project/aurora.git
cd aurora
pip install -e ".[all]"
```

### Python API Usage

**Parse and Store Code**:
```python
from aurora.core import SQLiteStore
from aurora.context_code import PythonParser

store = SQLiteStore("aurora.db")
parser = PythonParser()
chunks = parser.parse_file("example.py")

for chunk in chunks:
    store.save_chunk(chunk)
```

**Context Retrieval**:
```python
from aurora.core import CodeContextProvider

provider = CodeContextProvider(store, parser_registry)
results = provider.retrieve("authentication logic", max_results=5)

for chunk in results:
    print(f"{chunk.metadata['name']} (score: {chunk.metadata['_score']:.2f})")
```

**SOAR Orchestrator**:
```python
from aurora.soar import SOAROrchestrator
from aurora.reasoning import AnthropicClient

orchestrator = SOAROrchestrator(
    store=store,
    reasoning_llm=AnthropicClient()
)

response = orchestrator.execute("Analyze security vulnerabilities")
print(response.answer)
print(f"Confidence: {response.confidence:.2f}")
print(f"Cost: ${response.cost_usd:.4f}")
```

**Budget Management**:
```python
from aurora.core import CostTracker

tracker = CostTracker(monthly_limit_usd=10.0)
status = tracker.get_status()
print(f"Budget: ${status['consumed_usd']:.2f} / ${status['limit_usd']:.2f}")

# Execute with budget enforcement
response = orchestrator.execute(query, budget_tracker=tracker)
```

### CLI Usage

**Detailed Documentation**: [cli/CLI_USAGE_GUIDE.md](./cli/CLI_USAGE_GUIDE.md)

**Query Commands**:
```bash
# Simple query (fast, direct LLM)
aur query "What is a Python decorator?"

# Complex query (full AURORA pipeline)
aur query "How does authentication work?"

# Force specific mode
aur query "Explain classes" --force-aurora --verbose
```

**Memory Management**:
```bash
# Index current directory
aur mem index

# Index specific path
aur mem index /path/to/project

# Search indexed code
aur mem search "authentication"

# Advanced search
aur mem search "database" --limit 10 --show-content --format json

# View statistics
aur mem stats
```

**Headless Mode (Autonomous Reasoning)**:
```bash
# Run experiment
aur headless experiment.md

# Custom budget and iterations
aur headless experiment.md --budget 10.0 --max-iter 20

# Dry run (validation only)
aur headless experiment.md --dry-run
```

**Diagnostics**:
```bash
# Installation verification
aur --verify

# MCP server status
aurora-mcp status

# Help
aur --help
```

---

## MCP Integration

### Overview

**Detailed Documentation**: [MCP_SETUP.md](./MCP_SETUP.md)

AURORA provides native Claude Desktop integration via the Model Context Protocol (MCP). This enables Claude to search, index, and navigate your codebase directly from conversations.

### MCP Tools

1. **aurora_search** - Semantic search over indexed codebase
2. **aurora_index** - Index new files or directories
3. **aurora_stats** - View statistics about indexed code
4. **aurora_context** - Retrieve file or function content
5. **aurora_related** - Find related code through dependencies

### Configuration

**Linux**:
```json
# ~/.config/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "aurora": {
      "command": "python",
      "args": ["-m", "aurora.mcp.server"]
    }
  }
}
```

**macOS**:
```json
# ~/Library/Application Support/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "aurora": {
      "command": "python",
      "args": ["-m", "aurora.mcp.server"]
    }
  }
}
```

**Windows**:
```json
# %APPDATA%\Claude\claude_desktop_config.json
{
  "mcpServers": {
    "aurora": {
      "command": "python",
      "args": ["-m", "aurora.mcp.server"]
    }
  }
}
```

### Usage Examples

**Example 1: Code Search**
```
User: "Search my codebase for authentication logic"
Claude: [Uses aurora_search tool]
Claude: "I found 5 relevant code chunks related to authentication..."
```

**Example 2: Index and Query**
```
User: "Index the /src directory and find database queries"
Claude: [Uses aurora_index, then aurora_search]
Claude: "I've indexed 150 files. Here are the database queries..."
```

**Example 3: Related Code**
```
User: "Show me code related to UserService"
Claude: [Uses aurora_related]
Claude: "UserService has dependencies on AuthService, DatabaseService..."
```

### Troubleshooting

**MCP Server Not Starting**:
```bash
# Check status
aurora-mcp status

# Check logs
tail -f ~/.aurora/logs/mcp/server.log

# Verify Python path
which python3
python3 -m aurora.mcp.server --help
```

**Tools Not Appearing**:
1. Restart Claude Desktop
2. Check config file syntax (valid JSON)
3. Verify AURORA is installed: `aur --verify`

**See**: [MCP_SETUP.md](./MCP_SETUP.md) for detailed troubleshooting

---

## Testing

### Overview

**Comprehensive Documentation**: [development/TESTING.md](./development/TESTING.md)

AURORA has 1,766+ tests with 97% pass rate and 74%+ coverage.

### Test Structure

```
tests/
├── unit/                # Unit tests (fast, isolated)
│   ├── core/
│   ├── context-code/
│   ├── reasoning/
│   ├── soar/
│   └── cli/
├── integration/         # Integration tests (cross-package)
│   ├── soar/
│   ├── cli/
│   └── mcp/
├── performance/         # Performance benchmarks
│   ├── memory/
│   ├── retrieval/
│   └── parsing/
├── fault_injection/     # Error handling validation
└── fixtures/           # Test data and mocks
```

### Running Tests

**All Tests**:
```bash
pytest tests/ -v
```

**By Category**:
```bash
pytest tests/unit/ -v                 # Unit tests
pytest tests/integration/ -v          # Integration tests
pytest tests/performance/ -v          # Benchmarks
pytest tests/fault_injection/ -v      # Fault injection
```

**By Package**:
```bash
pytest tests/unit/core/ -v            # Core package only
pytest tests/unit/soar/ -v            # SOAR package only
```

**Specific Test**:
```bash
pytest tests/unit/core/test_store.py::test_save_chunk -v
```

**With Coverage**:
```bash
pytest tests/ --cov=packages --cov-report=html
open htmlcov/index.html
```

### Test Coverage

**Coverage Analysis**: [reports/testing/COVERAGE_ANALYSIS.md](./reports/testing/COVERAGE_ANALYSIS.md)

**Current Metrics**:
- Overall: 74%+ coverage
- Core: 80%+ coverage
- Context-Code: 75%+ coverage
- Reasoning: 70%+ coverage
- SOAR: 85%+ coverage
- CLI: 65%+ coverage

**Target**: 85% coverage (tracked for next release)

### Writing Tests

**Unit Test Template**:
```python
import pytest
from aurora.core import Store

def test_save_chunk():
    """Test chunk saving functionality."""
    store = Store(":memory:")
    chunk = CodeChunk(content="def foo(): pass")

    chunk_id = store.save_chunk(chunk)

    assert chunk_id is not None
    retrieved = store.get_chunk(chunk_id)
    assert retrieved.content == chunk.content
```

**Integration Test Template**:
```python
import pytest
from aurora.soar import SOAROrchestrator
from aurora.testing import MockLLMClient

@pytest.mark.integration
def test_end_to_end_query():
    """Test full query pipeline."""
    orchestrator = SOAROrchestrator(
        store=store,
        reasoning_llm=MockLLMClient()
    )

    response = orchestrator.execute("test query")

    assert response.answer is not None
    assert response.confidence > 0.5
```

### Test Fixtures

**Location**: `tests/fixtures/`

**Available Fixtures**:
- `mock_store` - In-memory SQLite store
- `mock_llm_client` - Mock LLM with canned responses
- `sample_code_chunks` - Reusable test code
- `sample_reasoning_chunks` - Test reasoning patterns

---

## Performance

### Benchmarks

**Detailed Reports**:
- Performance Profiling: [performance/PERFORMANCE_PROFILING_REPORT.md](./performance/PERFORMANCE_PROFILING_REPORT.md)
- Memory Profiling: [performance/MEMORY_PROFILING_REPORT.md](./performance/MEMORY_PROFILING_REPORT.md)
- Retrieval Precision: [performance/hybrid-retrieval-precision-report.md](./performance/hybrid-retrieval-precision-report.md)

### Performance Targets

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Simple query latency | <2s | 0.002s | ✅ 1000x faster |
| Complex query latency | <10s | <10s | ✅ Meets target |
| Retrieval (10K chunks) | <500ms | <500ms | ✅ Meets target |
| Memory (10K chunks) | <100MB | 39MB | ✅ 60% under |
| Test pass rate | >95% | 97% | ✅ Exceeds target |
| Code coverage | >85% | 74% | 🟡 Tracked for Phase 3 |

### Optimization Strategies

**Query Optimization**:
- Keyword-based assessment bypasses LLM for 60-70% of simple queries
- Simple queries skip decomposition entirely
- Cached patterns reused via ACT-R activation

**Memory Optimization**:
- Multi-tier caching (hot/persistent/embedding)
- Activation TTL limits memory growth
- LRU eviction for hot cache

**Retrieval Optimization**:
- Hybrid scoring (activation + semantic) faster than semantic alone
- Top-K selection reduces computation
- Pre-computed embeddings cached

**Cost Optimization**:
- Haiku for simple queries (~$0.001)
- Sonnet for medium queries (~$0.05)
- Opus for complex queries (~$0.50)
- Budget enforcement prevents runaway costs

### Profiling

**Run Performance Benchmarks**:
```bash
make benchmark
```

**Memory Profiling**:
```bash
pytest tests/performance/test_memory.py -v
```

**Retrieval Benchmarks**:
```bash
pytest tests/performance/test_retrieval.py -v
```

---

## Security

### Security Audit

**Detailed Reports**:
- Security Audit Checklist: [reports/security/SECURITY_AUDIT_CHECKLIST.md](./reports/security/SECURITY_AUDIT_CHECKLIST.md)
- Security Audit Report: [reports/security/SECURITY_AUDIT_REPORT_v1.0.0-phase3.md](./reports/security/SECURITY_AUDIT_REPORT_v1.0.0-phase3.md)

### Security Features

**API Key Management**:
- ✅ API keys from environment variables only (ANTHROPIC_API_KEY, OPENAI_API_KEY)
- ✅ No keys hardcoded in source
- ✅ No keys in logs or error messages
- ✅ Keys never transmitted except to official LLM APIs

**Input Validation**:
- ✅ Query length limits enforced
- ✅ JSON schema validation for LLM outputs
- ✅ Path traversal prevention
- ✅ SQL injection prevention (parameterized queries)
- ✅ Command injection prevention (no shell=True)

**Output Sanitization**:
- ✅ No sensitive data in logs
- ✅ No internal paths in error messages
- ✅ Log files with restrictive permissions
- ✅ Log rotation prevents disk overflow

**Security Scanning**:
```bash
# Bandit security scan
bandit -r packages/ -ll

# Result: Clean (1 low severity false positive)
```

### Best Practices

1. **Never commit API keys** - Use environment variables
2. **Rotate keys regularly** - Every 90 days recommended
3. **Use budget limits** - Prevent API key abuse
4. **Monitor logs** - Check for suspicious activity
5. **Update dependencies** - Run `pip list --outdated` regularly

---

## Troubleshooting

### Common Issues

**Comprehensive Guide**: [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
**Error Catalog**: [cli/ERROR_CATALOG.md](./cli/ERROR_CATALOG.md)

### Installation Issues

**"aur command not found"**:
```bash
# Verify installation
pip show aurora-actr

# Reinstall CLI
pip install --force-reinstall aurora-actr[all]

# Check PATH
which aur
```

**"Import error: No module named 'aurora'"**:
```bash
# Verify Python path
python3 -c "import sys; print(sys.path)"

# Reinstall packages
cd packages/core && pip install -e .
cd packages/cli && pip install -e .
```

**"SQLite version too old"**:
```bash
# Check SQLite version
python3 -c "import sqlite3; print(sqlite3.sqlite_version)"

# Upgrade SQLite (if needed)
pip install --upgrade pysqlite3-binary
```

### Runtime Issues

**"LLM API key not found"**:
```bash
# Set API key
export ANTHROPIC_API_KEY="your-key-here"

# Or create ~/.aurora/config.json
{
  "anthropic_api_key": "your-key-here"
}
```

**"Budget exceeded"**:
```bash
# Check budget status
cat ~/.aurora/budget_tracker.json

# Reset budget (new month)
rm ~/.aurora/budget_tracker.json

# Increase limit (edit config)
{
  "monthly_limit_usd": 50.0
}
```

**"Query timeout"**:
```bash
# Increase timeout in config
{
  "query_timeout_seconds": 120
}
```

### MCP Issues

**"MCP server not starting"**:
```bash
# Check status
aurora-mcp status

# Check logs
tail -f ~/.aurora/logs/mcp/server.log

# Verify config
cat ~/.config/Claude/claude_desktop_config.json

# Test server manually
python3 -m aurora.mcp.server --test
```

**"Tools not appearing in Claude Desktop"**:
1. Verify config file is valid JSON
2. Restart Claude Desktop completely
3. Check AURORA installation: `aur --verify`
4. Check Python path in config matches: `which python3`

### Test Failures

**"Tests failing locally"**:
```bash
# Run quality check
make quality-check

# Update dependencies
pip install --upgrade -r requirements-dev.txt

# Clear pytest cache
rm -rf .pytest_cache

# Run specific failing test
pytest tests/unit/path/test_file.py::test_name -vv
```

**"Tests pass locally but fail in CI"**:
- Check Python version (CI uses 3.10, 3.11, 3.12)
- Check environment variables (API keys in CI)
- Check file permissions
- Check for race conditions in async tests

### Getting Help

1. **Check documentation first**:
   - [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
   - [cli/ERROR_CATALOG.md](./cli/ERROR_CATALOG.md)
   - [MCP_SETUP.md](./MCP_SETUP.md)

2. **Run diagnostics**:
   ```bash
   aur --verify
   aurora-mcp status
   ```

3. **Check logs**:
   ```bash
   tail -f ~/.aurora/logs/conversations/*/latest.md
   tail -f ~/.aurora/logs/mcp/server.log
   ```

4. **Report issue**:
   - GitHub Issues: https://github.com/aurora-project/aurora/issues
   - Include: OS, Python version, error message, steps to reproduce

---

## Release History

### v0.2.0 (Current - Production Ready)

**Release Date**: December 22, 2025
**Status**: Production Ready

**Detailed Notes**: [phases/phase2/RELEASE_NOTES_v0.2.0.md](./phases/phase2/RELEASE_NOTES_v0.2.0.md)

**Key Features**:
- 9-phase SOAR orchestrator
- Multi-stage verification system
- LLM abstraction layer (Anthropic/OpenAI/Ollama)
- Cost tracking and budget enforcement
- ReasoningChunk implementation
- Conversation logging
- Agent execution framework

**Quality Metrics**:
- 908 tests, 894 passing (99.84%)
- 88.06% code coverage
- Performance targets exceeded by 20-1000x

**Breaking Changes**: None (backward compatible with Phase 1)

### Phase 1 - Foundation

**Documentation**: [phases/phase1/PHASE1_ARCHIVE.md](./phases/phase1/PHASE1_ARCHIVE.md)

**Key Features**:
- SQLite storage with ACT-R activation
- CodeChunk and ReasoningChunk schemas
- tree-sitter Python parser
- Intelligent chunking with complexity analysis
- Multi-tier caching
- Basic CLI interface

### Phase Roadmap

**Phase 3 (Planned)**:
- Adaptive memory with advanced decay
- Meta-learning and pattern recognition
- Query optimization and complexity downgrading
- Enhanced agents with tool-calling
- Streaming responses

**Phase 4 (Future)**:
- Multi-language parsing (TypeScript, Java, Go)
- Distributed agent execution
- Advanced visualization tools
- Plugin system

---

## Research Background

### Cognitive Science Foundations

AURORA is built on well-established cognitive architectures from decades of research:

**ACT-R (Adaptive Control of Thought-Rational)**:
- Developed at CMU by John Anderson
- Models human memory and learning
- Activation-based retrieval with frequency, recency, and semantic similarity
- Successfully models human cognitive processes

**SOAR (State, Operator, And Result)**:
- Developed at University of Michigan
- Problem-solving through decomposition and search
- Goal-based reasoning with impasse resolution
- Used in AI systems since 1980s

### Research Documentation

**Location**: `docs/agi-problem/`

**Key Entry Points**:
- Master Navigation: [agi-problem/START-HERE.md](./agi-problem/START-HERE.md)
- Aurora Framework PRD: [agi-problem/aurora/AURORA-Framework-PRD.md](./agi-problem/aurora/AURORA-Framework-PRD.md)
- Executive Summary: [agi-problem/aurora/AURORA_EXECUTIVE_SUMMARY.md](./agi-problem/aurora/AURORA_EXECUTIVE_SUMMARY.md)
- Framework Specs: [agi-problem/aurora/AURORA-Framework-SPECS.md](./agi-problem/aurora/AURORA-Framework-SPECS.md)

**Research Areas**:
- Core Research: [agi-problem/research/core-research/](./agi-problem/research/core-research/)
- SOAR & ACT-R: [agi-problem/research/soar_act-r/](./agi-problem/research/soar_act-r/)
- Market Research: [agi-problem/research/market-research/](./agi-problem/research/market-research/)

### Academic Papers

**ACT-R**:
- Anderson, J. R., et al. (2004). "An integrated theory of the mind"
- Anderson, J. R. (1993). "Rules of the mind"

**SOAR**:
- Laird, J. E., et al. (1987). "SOAR: An architecture for general intelligence"
- Newell, A. (1990). "Unified theories of cognition"

**Memory Models**:
- Anderson, J. R., & Schooler, L. J. (1991). "Reflections of the environment in memory"

---

## Resources

### Internal Documentation

**Architecture**:
- [SOAR Architecture](./architecture/SOAR_ARCHITECTURE.md)
- [API Contracts v1.0](./architecture/API_CONTRACTS_v1.0.md)
- [Agent Integration](./architecture/AGENT_INTEGRATION.md)

**Development**:
- [Testing Guide](./development/TESTING.md)
- [Extension Guide](./development/EXTENSION_GUIDE.md)
- [Code Review Checklist](./development/CODE_REVIEW_CHECKLIST.md)
- [Prompt Engineering Guide](./development/PROMPT_ENGINEERING_GUIDE.md)

**Guides**:
- [MCP Setup](./MCP_SETUP.md)
- [Quick Start](./cli/QUICK_START.md)
- [CLI Usage Guide](./cli/CLI_USAGE_GUIDE.md)
- [Troubleshooting](./TROUBLESHOOTING.md)
- [Cost Tracking Guide](./guides/COST_TRACKING_GUIDE.md)

**Reports**:
- [Quality Reports](./reports/quality/)
- [Performance Reports](./performance/)
- [Security Reports](./reports/security/)
- [Testing Reports](./reports/testing/)

### Package Documentation

- [Core Package](../packages/core/README.md)
- [Context-Code Package](../packages/context-code/README.md)
- [Reasoning Package](../packages/reasoning/README.md)
- [SOAR Package](../packages/soar/README.md)
- [CLI Package](../packages/cli/README.md)
- [Testing Package](../packages/testing/README.md)

### External Links

**Project**:
- GitHub: https://github.com/aurora-project/aurora (placeholder)
- PyPI: https://pypi.org/project/aurora-actr/
- Documentation: https://aurora-actr.readthedocs.io/ (planned)

**Dependencies**:
- tree-sitter: https://tree-sitter.github.io/tree-sitter/
- sentence-transformers: https://www.sbert.net/
- Anthropic API: https://docs.anthropic.com/
- OpenAI API: https://platform.openai.com/docs/
- Ollama: https://ollama.ai/

**Cognitive Science**:
- ACT-R: http://act-r.psy.cmu.edu/
- SOAR: https://soar.eecs.umich.edu/

### Community

**Getting Help**:
- GitHub Issues: https://github.com/aurora-project/aurora/issues
- GitHub Discussions: https://github.com/aurora-project/aurora/discussions
- Discord: https://discord.gg/aurora (planned)

**Contributing**:
- See [development/EXTENSION_GUIDE.md](./development/EXTENSION_GUIDE.md)
- Follow code quality standards
- Write tests for new features
- Update documentation

---

## Appendix

### Configuration Reference

**Config File**: `~/.aurora/config.json`

```json
{
  "anthropic_api_key": "sk-...",
  "openai_api_key": "sk-...",
  "monthly_budget_usd": 10.0,
  "query_timeout_seconds": 60,
  "max_iterations": 20,
  "default_llm_provider": "anthropic",
  "default_model": "claude-sonnet-4.5",
  "cache_ttl_minutes": 10,
  "log_level": "INFO"
}
```

### Environment Variables

- `ANTHROPIC_API_KEY` - Anthropic Claude API key
- `OPENAI_API_KEY` - OpenAI GPT-4 API key
- `AURORA_DB_PATH` - Database path (default: `~/.aurora/aurora.db`)
- `AURORA_CONFIG_PATH` - Config file path (default: `~/.aurora/config.json`)
- `AURORA_LOG_LEVEL` - Logging level (DEBUG/INFO/WARNING/ERROR)

### File Locations

- Database: `~/.aurora/aurora.db`
- Config: `~/.aurora/config.json`
- Budget Tracker: `~/.aurora/budget_tracker.json`
- Logs: `~/.aurora/logs/`
- Conversations: `~/.aurora/logs/conversations/YYYY/MM/`
- MCP Logs: `~/.aurora/logs/mcp/`

### Glossary

- **ACT-R**: Adaptive Control of Thought-Rational (cognitive architecture)
- **SOAR**: State, Operator, And Result (problem-solving architecture)
- **MCP**: Model Context Protocol (Claude Desktop integration)
- **Activation**: Memory strength score based on frequency, recency, and similarity
- **Chunk**: Unit of memory (CodeChunk for code, ReasoningChunk for patterns)
- **Orchestrator**: 9-phase pipeline coordinator
- **Verification**: Multi-stage validation of query decompositions
- **Agent**: External tool or service that can execute subgoals
- **Hybrid Retrieval**: Combined activation + semantic similarity scoring
- **Cost Tracking**: LLM token usage monitoring and budget enforcement

---

**Last Updated**: December 25, 2025
**Version**: v0.2.0
**Maintainer**: Aurora Development Team
**License**: MIT
