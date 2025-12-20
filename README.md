# AURORA: Adaptive Unified Reasoning and Orchestration Architecture

[![CI/CD Pipeline](https://github.com/aurora-project/aurora/workflows/CI%2FCD%20Pipeline/badge.svg)](https://github.com/aurora-project/aurora/actions)
[![codecov](https://codecov.io/gh/aurora-project/aurora/branch/main/graph/badge.svg)](https://codecov.io/gh/aurora-project/aurora)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

AURORA is a cognitive architecture framework that provides intelligent context management, reasoning, and agent orchestration capabilities for AI systems. Built on principles inspired by cognitive science research (SOAR, ACT-R), AURORA enables AI agents to maintain persistent memory, learn from experience, and efficiently coordinate complex tasks.

### Key Features

- **Intelligent Context Management**: Adaptive chunking and retrieval of code and reasoning contexts
- **Persistent Memory**: SQLite-based storage with activation-based retrieval
- **Code Understanding**: Tree-sitter powered parsing for Python (extensible to other languages)
- **Agent Registry**: Discover and orchestrate AI agents based on capabilities
- **Flexible Configuration**: JSON schema validated configuration with environment overrides
- **Comprehensive Testing**: Unit, integration, and performance testing framework

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/aurora-project/aurora.git
cd aurora

# Install all packages in development mode
make install-dev

# Or install individually
pip install -e packages/core
pip install -e packages/context-code
pip install -e packages/soar
```

### Basic Usage

```python
from aurora_core.store import SQLiteStore
from aurora_core.chunks import CodeChunk
from aurora_context_code import PythonParser
from aurora_core.context import CodeContextProvider

# Initialize storage
store = SQLiteStore("aurora.db")

# Parse Python code
parser = PythonParser()
chunks = parser.parse_file("example.py")

# Store chunks
for chunk in chunks:
    store.save_chunk(chunk)

# Retrieve relevant context
provider = CodeContextProvider(store, parser)
results = provider.query("authentication logic", max_results=5)
for chunk in results:
    print(f"{chunk.chunk_id}: {chunk.metadata.get('signature', 'N/A')}")
```

## Architecture

AURORA is organized as a Python monorepo with four core packages:

### Packages

#### `aurora-core`
Core functionality including:
- Abstract storage interfaces and implementations (SQLite, in-memory)
- Chunk types (CodeChunk, ReasoningChunk)
- Context providers for intelligent retrieval
- Configuration system with validation

#### `aurora-context-code`
Code parsing and analysis:
- Abstract parser interface
- Parser registry for language discovery
- Python parser using tree-sitter
- Extensible to additional languages

#### `aurora-soar`
Agent registry and orchestration:
- Agent discovery from configuration files
- Capability-based agent selection
- Agent lifecycle management

#### `aurora-testing`
Testing utilities:
- Reusable pytest fixtures
- Mock implementations (LLM, agents)
- Performance benchmarking tools

### Directory Structure

```
aurora/
├── packages/
│   ├── core/                    # Core storage and types
│   ├── context-code/            # Code parsing
│   ├── soar/                    # Agent orchestration
│   └── testing/                 # Testing utilities
├── tests/
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   ├── performance/             # Performance benchmarks
│   └── fixtures/                # Test data
├── docs/                        # Documentation
├── tasks/                       # Implementation task lists
└── Makefile                     # Development commands
```

## Development

### Setup Development Environment

```bash
# Install with development dependencies
make install-dev

# Run all quality checks
make quality-check
```

### Common Commands

```bash
make help              # Show all available commands
make test              # Run all tests
make test-unit         # Run unit tests only
make lint              # Run ruff linter
make format            # Format code
make type-check        # Run mypy type checker
make benchmark         # Run performance benchmarks
make coverage          # Generate HTML coverage report
make clean             # Remove build artifacts
```

### Testing

```bash
# Run all tests with coverage
make test

# Run specific test types
make test-unit              # Unit tests only
make test-integration       # Integration tests only
make test-performance       # Performance benchmarks only

# Run with specific markers
pytest tests/ -m "unit and not slow"
pytest tests/ -k "test_store"
```

### Code Quality

The project enforces strict quality standards:

- **Linting**: Ruff with comprehensive rule set
- **Type Checking**: MyPy in strict mode
- **Test Coverage**: Minimum 85% coverage required
- **Security**: Bandit security scanning
- **Performance**: Benchmarks for critical operations

## Project Status

### Phase 1: Foundation (Current)

Phase 1 focuses on building the foundational components:

- ✅ Project structure and tooling setup
- ⏳ Storage layer implementation
- ⏳ Chunk types and validation
- ⏳ Python code parser
- ⏳ Context management
- ⏳ Configuration system
- ⏳ Testing framework

See [tasks/tasks-0002-prd-aurora-foundation.md](tasks/tasks-0002-prd-aurora-foundation.md) for detailed task breakdown.

### Future Phases

- **Phase 2**: SOAR Pipeline (Reasoning and learning)
- **Phase 3**: Advanced Features (Multi-agent coordination, advanced memory)

## Documentation

- [Architecture Documentation](docs/agi-problem/aurora/AURORA_UNIFIED_SPECS_TRUTH.md)
- [PRD Documents](tasks/)
- [API Documentation](#) (Coming soon)

## Contributing

Contributions are welcome! Please ensure:

1. All tests pass (`make test`)
2. Code is formatted (`make format`)
3. Type checking passes (`make type-check`)
4. Coverage remains ≥85%
5. New features include tests

## Performance Targets

Phase 1 performance targets:

- Chunk storage (write): <50ms
- Chunk retrieval (read): <50ms
- Cold start: <200ms
- Python parser (1000-line file): <200ms
- Memory usage (10K cached chunks): <100MB

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contact

For questions or discussions, please open an issue on GitHub.

---

**AURORA Project** - Building intelligent AI systems with persistent memory and reasoning
