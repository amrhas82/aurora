# Aurora Dependencies Reference

> Comprehensive reference for all packages, dependencies, and version requirements.
>
> **Last Updated:** 2026-02-04
> **Python Requirement:** >= 3.12

---

## Table of Contents

- [Package Overview](#package-overview)
- [Dependency Graph](#dependency-graph)
- [External Dependencies](#external-dependencies)
- [Development Dependencies](#development-dependencies)
- [Optional Dependencies](#optional-dependencies)
- [Installation](#installation)

---

## Package Overview

Aurora is organized as a monorepo with multiple packages. The root package (`aurora-actr`) bundles everything for simple installation.

| Package | Version | Path | Description |
|---------|---------|------|-------------|
| `aurora-actr` | 0.13.2 | `/` (root) | Main distribution package - bundles all components |
| `aurora-cli` | 0.6.7 | `packages/cli` | Command-line interface (`aur` command) |
| `aurora-core` | 0.6.7 | `packages/core` | Core models, SQLite store, configuration |
| `aurora-context-code` | 0.6.7 | `packages/context-code` | Code parsing, tree-sitter, BM25, embeddings |
| `aurora-context-doc` | 0.10.3 | `packages/context-doc` | Document parsing (PDF, DOCX, Markdown) |
| `aurora-reasoning` | 0.6.7 | `packages/reasoning` | LLM clients (Anthropic, OpenAI, Ollama) |
| `aurora-soar` | 0.6.7 | `packages/soar` | 9-phase SOAR pipeline orchestration |
| `aurora-planning` | 0.6.7 | `packages/planning` | Plan generation and management |
| `aurora-spawner` | 0.6.7 | `packages/spawner` | Parallel subprocess execution |
| `aurora-implement` | 0.6.7 | `packages/implement` | Sequential task execution |
| `aurora-lsp` | 0.1.0 | `packages/lsp` | LSP integration, code intelligence |
| `aurora-testing` | 0.6.7 | `packages/testing` | Test utilities and fixtures |

---

## Dependency Graph

```
aurora-actr (root)
├── aurora-cli
│   ├── aurora-core
│   ├── aurora-context-code
│   │   └── aurora-core
│   ├── aurora-soar
│   │   └── aurora-core
│   ├── aurora-reasoning
│   │   └── aurora-core
│   ├── aurora-planning
│   ├── aurora-spawner
│   │   └── aurora-core
│   └── aurora-implement
│       └── aurora-spawner
├── aurora-lsp
└── aurora-testing
    └── aurora-core
```

---

## External Dependencies

### Core Dependencies

Required for basic functionality:

| Dependency | Version | Used By | Purpose |
|------------|---------|---------|---------|
| `pydantic` | >= 2.0.0 | core, cli, planning, reasoning, root | Data validation and settings |
| `jsonschema` | >= 4.17.0 | core, root | JSON schema validation |
| `click` | >= 8.1.0 | cli, planning, root | CLI framework |
| `rich` | >= 13.0.0 | cli, planning, root | Terminal formatting and output |

### LLM Integration

| Dependency | Version | Used By | Purpose |
|------------|---------|---------|---------|
| `anthropic` | >= 0.18.0 | reasoning, root | Claude API client |
| `openai` | >= 1.0.0 | reasoning, root | OpenAI API client |
| `ollama` | >= 0.1.0 | reasoning, root | Ollama local LLM client |
| `tenacity` | >= 8.2.0 | reasoning, root | Retry logic for API calls |

### Code Analysis

| Dependency | Version | Used By | Purpose |
|------------|---------|---------|---------|
| `tree-sitter` | >= 0.20.0 | context-code, root | Syntax parsing |
| `tree-sitter-python` | >= 0.20.0 | context-code, root | Python grammar |
| `tree-sitter-javascript` | >= 0.20.0 | context-code | JavaScript grammar |
| `tree-sitter-typescript` | >= 0.20.0 | context-code | TypeScript grammar |
| `numpy` | >= 1.24.0 | context-code, root | Numerical operations for embeddings |
| `sentence-transformers` | >= 2.2.0 | context-code | Semantic embeddings (all-MiniLM-L6-v2) |

### LSP & MCP

| Dependency | Version | Used By | Purpose |
|------------|---------|---------|---------|
| `multilspy` | >= 0.0.15 | lsp, root | Multi-language LSP client |
| `mcp` | >= 1.0.0 | lsp | Model Context Protocol server |
| `fastmcp` | >= 0.1.0 | root | Fast MCP utilities |
| `nest-asyncio` | >= 1.5 | lsp | Nested event loop support |

### CLI Utilities

| Dependency | Version | Used By | Purpose |
|------------|---------|---------|---------|
| `python-frontmatter` | >= 1.0.0 | cli, root | YAML frontmatter parsing |
| `jinja2` | >= 3.1.0 | cli, planning, root | Template rendering |
| `python-slugify` | >= 8.0.0 | cli, planning, root | URL-safe slug generation |
| `questionary` | >= 2.0.0 | cli, root | Interactive prompts |
| `pyyaml` | >= 6.0.0 | planning, root | YAML parsing |

---

## Development Dependencies

Used for testing, linting, and type checking (install with `pip install -e ".[dev]"`):

| Dependency | Version | Purpose |
|------------|---------|---------|
| `pytest` | >= 7.4.0 | Test framework |
| `pytest-cov` | >= 4.1.0 | Coverage reporting |
| `pytest-asyncio` | >= 0.21.0 | Async test support |
| `pytest-benchmark` | >= 4.0.0 | Performance benchmarking |
| `ruff` | >= 0.1.0 | Linting and formatting |
| `mypy` | >= 1.5.0 | Static type checking |
| `types-jsonschema` | >= 4.0.0 | Type stubs for jsonschema |
| `bandit` | >= 1.7.5 | Security linting |
| `memory-profiler` | >= 0.61.0 | Memory usage profiling |

---

## Optional Dependencies

### Document Parsing (context-doc)

```bash
# PDF support
pip install aurora-context-doc[pdf]
# Installs: pymupdf >= 1.24.0

# DOCX support
pip install aurora-context-doc[docx]
# Installs: python-docx >= 1.1.0

# All document formats
pip install aurora-context-doc[all]
```

---

## Installation

### Standard Installation (Recommended)

Install the bundled package which includes all components:

```bash
# From PyPI (when published)
pip install aurora-actr

# From source (development)
pip install -e .
```

### Development Installation

```bash
# Clone and install with dev dependencies
git clone https://github.com/hamr0/aurora.git
cd aurora
pip install -e ".[dev]"

# Or use make
make install-dev
```

### Individual Package Installation

For minimal installations, install specific packages:

```bash
# Core only (models, config, store)
pip install -e packages/core

# CLI with all runtime deps
pip install -e packages/cli

# Code analysis only
pip install -e packages/context-code
```

### Verifying Installation

```bash
# Check version
aur --version

# Verify ML dependencies
python -c "from aurora_context_code.semantic.embedding_provider import HAS_SENTENCE_TRANSFORMERS; print(f'Embeddings: {HAS_SENTENCE_TRANSFORMERS}')"

# Run tests
make test
```

---

## Version Compatibility Matrix

| Aurora Version | Python | sentence-transformers | torch |
|----------------|--------|----------------------|-------|
| 0.13.x | >= 3.12 | >= 2.2.0 | >= 2.0.0 |
| 0.12.x | >= 3.10 | >= 2.2.0 | >= 2.0.0 |
| 0.11.x | >= 3.10 | >= 2.2.0 | >= 1.12.0 |

---

## Dependency Version Policies

1. **Minimum Versions**: We specify minimum versions (`>=`) to ensure compatibility while allowing updates
2. **Python Version**: Requires Python 3.12+ (3.10/3.11 EOL approaching)
3. **Major Version Pins**: We don't pin major versions except where breaking changes are known
4. **Security Updates**: Dependencies are reviewed quarterly for security patches

---

## Troubleshooting

### Import Errors

If you see import errors, verify the package is installed in the correct Python:

```bash
# Check which Python aur uses
head -1 $(which aur)

# Install in that Python
python3.X -m pip install -e .
```

### ML Dependencies

If embeddings fail to load:

```bash
# Verify torch and sentence-transformers
python -c "import torch; print(torch.__version__)"
python -c "from sentence_transformers import SentenceTransformer; print('OK')"

# Reinstall if needed
pip install sentence-transformers torch
```

### Dependency Conflicts

Use pip to check for conflicts:

```bash
pip check
```

---

## See Also

- [Installation Guide](../getting-started/QUICK_START.md)
- [ML Models Documentation](../../02-features/memory/ML_MODELS.md)
- [Configuration Reference](./CONFIG_REFERENCE.md)
- [Troubleshooting Guide](../troubleshooting/TROUBLESHOOTING.md)
