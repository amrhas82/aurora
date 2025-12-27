# Changelog

All notable changes to the AURORA project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

**Test Suite Systematic Cleanup (Phases 1-5):**
- Removed 20 low-value tests (constructor tests, implementation detail tests)
- Archived 7 performance benchmarks for manual execution
- Converted 79 @patch decorators to Dependency Injection pattern
- Added 26 integration tests for CLI, memory manager, and auto-escalation
- Improved test pyramid from 95/4/1 to 76/21/3 (unit/integration/E2E)
- Increased coverage from 74.95% to 81.06% (+6.11 percentage points)
- Created comprehensive testing documentation (TESTING.md, TEST_REFERENCE.md)
- Marked 86 tests with pytest markers (critical, core, integration, e2e)
- Fixed Python 3.11/3.12 compatibility (from 28+27 failures to 0)

**Testing Documentation:**
- Added `docs/development/TESTING.md` - Testing principles and best practices
- Added `docs/development/TEST_REFERENCE.md` - Test categorization and markers
- Added `docs/development/TESTING_TECHNICAL_DEBT.md` - Technical debt tracking

### Fixed

- Python 3.11/3.12 test failures caused by @patch decorators (79 instances)
- Import organization issues (19 auto-fixes)
- Test fragility across Python versions

---

## [0.2.0] - 2025-01-24

### Added

**MCP Server Integration:**
- Added FastMCP-based server with 5 tools for Claude Desktop integration
- `aurora_search`: Semantic search across indexed codebase with hybrid scoring
- `aurora_index`: Index directory with configurable file patterns
- `aurora_stats`: Database statistics and metrics
- `aurora_context`: Retrieve full file or specific function content
- `aurora_related`: Find related chunks using ACT-R spreading activation
- MCP configuration schema in CLI config with `always_on`, `log_file`, `max_results`
- `aurora-mcp` control script: `start`, `stop`, `status` commands
- Performance logging decorator for all MCP tools with latency tracking
- Cross-platform MCP setup for Windows, macOS, and Linux

**Package Consolidation:**
- Meta-package installation: `pip install aurora` installs all 6 components
- Post-install hook displaying component-level feedback (✓ Core, ✓ CLI, etc.)
- Optional dependencies: `[ml]` for sentence-transformers, `[mcp]` for FastMCP, `[all]` for everything
- Automated import path migration script: `aurora_*` → `aurora.*` namespace
- `aurora-uninstall` helper script with `--keep-config` flag

**CLI Enhancements:**
- `aur --verify` command: Installation health check, dependency verification, diagnostics
- Flexible `--headless` global flag: Both `aur --headless file.md` and `aur headless file.md` work
- Enhanced help text with multiple examples for all commands
- Improved error messages with actionable recovery steps for common failures
- Better Path handling in `aur init` command

**Documentation:**
- Comprehensive MCP Setup Guide (`docs/MCP_SETUP.md`) with 9 sections
- Troubleshooting Guide (`docs/TROUBLESHOOTING.md`) with platform-specific notes
- Updated README for v0.2.0 with MCP integration as primary workflow
- Installation verification documentation

**Testing:**
- Comprehensive MCP test suite (120+ tests) via Python client
- Integration tests for all 5 MCP tools
- MCP server startup/shutdown tests
- Error handling and edge case tests
- Performance and logging tests
- Platform compatibility tests (Linux, with Windows/macOS support)
- Smoke test suite with 11 end-to-end CLI tests

### Fixed

- **Bug #1**: `aur init` crash due to duplicate `from pathlib import Path` import (line 88 shadowing)
- **Bug #2**: `aur mem index` API mismatch - changed `add_chunk()` to `save_chunk()`, fixed embeddings serialization
- **Bug #3**: Dry-run import error - corrected import path to `aurora.context_code.semantic.hybrid_retriever`
- Fixed 39 import statements across packages (aurora.* -> aurora_* for backward compatibility)
- Resolved memory leak in `MemoryStore.close()` for Python 3.12
- Fixed deprecated `datetime.utcnow()` for Python 3.12 compatibility

### Changed

- **BREAKING**: Import paths migrated to `aurora.*` namespace (e.g., `from aurora.core.store import SQLiteStore`)
  - Old `aurora_core.*` imports still work but deprecated
  - Use migration script: `python scripts/migrate_imports.py`
- Version bumped from `0.1.0` to `0.2.0` in `pyproject.toml`
- Project description updated to include MCP integration
- README reorganized: MCP integration as primary workflow, standalone CLI as secondary
- Updated feature list with Windows support and cross-platform compatibility

### Deprecated

- Old import paths (`aurora_core.*`, `aurora_context_code.*`, etc.) - use `aurora.*` namespace instead
- Individual package installation (`pip install -e packages/core`) - use meta-package (`pip install aurora`)

### Migration Guide (Breaking Changes)

**Import Path Migration:**

Old (v0.1.0):
```python
from aurora_core.store import SQLiteStore
from aurora_context_code import PythonParser
from aurora_soar import SOAROrchestrator
```

New (v0.2.0):
```python
from aurora.core.store import SQLiteStore
from aurora.context_code import PythonParser
from aurora.soar import SOAROrchestrator
```

**Automated Migration:**
```bash
python scripts/migrate_imports.py --dry-run  # Preview changes
python scripts/migrate_imports.py           # Apply changes
```

**Installation Migration:**

Old (v0.1.0):
```bash
pip install -e packages/core
pip install -e packages/context-code
pip install -e packages/soar
pip install -e packages/cli
```

New (v0.2.0):
```bash
pip install aurora[all]  # Single command
```

**Backward Compatibility:**
- Old import paths still work in v0.2.0 but will be removed in v0.3.0
- Individual package installation still works but not recommended
- Migrate before v0.3.0 release to avoid breakage

---

## [0.1.0] - 2025-01-15

### Added

**Phase 1 Foundation:**
- Core storage layer with SQLite and in-memory implementations
- Chunk types: `CodeChunk` and `ReasoningChunk` with validation
- Python code parser using tree-sitter
- Context providers with scoring and caching
- Configuration system with JSON schema validation
- Agent registry for capability-based selection
- Comprehensive testing framework (243 tests, 88% coverage)

**Phase 2 SOAR Pipeline:**
- 9-phase SOAR orchestrator: Assess → Retrieve → Decompose → Verify → Route → Collect → Synthesize → Record → Respond
- Multi-provider LLM integration (Anthropic Claude, OpenAI, Ollama)
- Cost tracking with soft/hard budget limits
- Conversation logging with markdown format
- ReasoningChunk pattern caching with ACT-R activation
- 60-70% query optimization via keyword-based assessment

**Phase 3 Advanced Memory:**
- ACT-R activation engine with BLA, spreading activation, context boost
- Semantic embeddings with sentence-transformers
- Hybrid retrieval: 60% activation + 40% semantic similarity
- Multi-tier caching: hot cache + persistent cache + activation cache
- Query optimization: type filtering, threshold filtering, batch calculation
- Performance: <500ms for 10K chunks, 30%+ cache hit rate

**CLI Implementation (v1.1.0):**
- Complete CLI with `aur` command
- Auto-escalation between direct LLM and full AURORA pipeline
- Memory commands: `aur mem index/search/stats`
- Configuration management with environment variable overrides
- Headless reasoning mode for autonomous experiments
- Dry-run mode for testing without API costs

### Performance

- Simple query latency: 0.002s (target: <2s) - 1000x faster
- Complex query latency: <10s (met target)
- Memory usage: 39.48 MB for 10K chunks (target: <100MB)
- Chunk storage: ~15ms (target: <50ms)
- Chunk retrieval: ~8ms (target: <50ms)
- Throughput: >100 queries/second (target: >10)

---

## Release Links

- [v0.2.0 GitHub Release](https://github.com/aurora-project/aurora/releases/tag/v0.2.0) (pending)
- [v0.1.0 GitHub Release](https://github.com/aurora-project/aurora/releases/tag/v0.1.0) (pending)

## Version History

- **v0.2.0** (2025-01-24): MCP integration, package consolidation, CLI enhancements
- **v0.1.0** (2025-01-15): Initial release with SOAR pipeline and advanced memory

---

**Last Updated:** 2025-01-24
