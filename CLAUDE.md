# AURORA - Adaptive Unified Reasoning and Orchestration Architecture

## Agent System

**IMPORTANT**: Global agentic agent system is active (from `~/.claude/CLAUDE.md`).
- All requests route through **orchestrator** first (unless you specify `@agent-id` or `As agent-id, ...`)
- Orchestrator analyzes intent and matches to optimal workflow pattern
- You'll be asked conditional questions at each workflow step (e.g., "Research first?")
- See `~/.claude/CLAUDE.md` for 9 pre-defined workflow patterns
- Available agents: orchestrator, 1-create-prd, 2-generate-tasks, business-analyst, holistic-architect, full-stack-dev, qa-test-architect, ux-expert, product-owner, product-manager, scrum-master, master, context-initializer

---

## Quick Context

AURORA is a production-ready cognitive architecture framework enabling AI systems to maintain persistent memory, reason about complex queries, and orchestrate multi-agent tasks. Built on ACT-R/SOAR cognitive science principles with Python 3.10+, published to PyPI as `aurora-actr`.

**Current Version**: v0.2.0 (Production Ready)
**Project Root**: /home/hamr/PycharmProjects/aurora
**Quality Metrics**: 1,766+ tests (97% pass rate), 74%+ coverage, 100% type safety

---

## Architecture

### Package Structure (Namespace Packages)
- **aurora-core** - Storage (SQLite), chunks, activation scoring, cost tracking, context providers
- **aurora-context-code** - Code parsing (tree-sitter for Python), intelligent chunking, dependency tracking
- **aurora-soar** - Agent registry, 9-phase SOAR orchestration pipeline
- **aurora-reasoning** - LLM integration (Anthropic/OpenAI/Ollama), reasoning logic
- **aurora-cli** - CLI interface (`aur` command)
- **aurora-testing** - Test utilities, fixtures, mocks, benchmarks

**Import Pattern**: `from aurora.core import ...` (but packages are `aurora_core`, etc.)
**Primary Interface**: MCP server (Claude Desktop integration)
**Secondary Interface**: Standalone CLI (`aur` command)

### Core Concepts
- **9-Phase SOAR Pipeline**: Assess → Retrieve → Decompose → Verify → Route → Collect → Synthesize → Record → Respond
- **ACT-R Activation**: Memory scoring via frequency + recency + semantic similarity + context boost
- **Hybrid Retrieval**: 60% activation + 40% semantic similarity
- **Multi-Tier Caching**: Hot cache (LRU) + persistent cache + activation scores (10min TTL)
- **Cost Optimization**: Keyword-based assessment bypasses LLM for 60-70% of simple queries

---

## Common Commands

### Development
```bash
make install-dev           # Install with dev dependencies
make quality-check         # Run all quality checks (lint, type, test)
make test                  # Run all 1,766+ tests
make test-unit             # Unit tests only
make lint                  # Ruff linting
make format                # Auto-format code
make type-check            # MyPy strict mode (0 errors required)
make benchmark             # Performance benchmarks
make coverage              # HTML coverage report
```

### CLI Usage
```bash
aur --verify               # Check installation health
aur query "text"           # Query with auto-escalation (direct LLM vs AURORA pipeline)
aur mem index .            # Index current directory for semantic search
aur mem search "text"      # Search indexed code
aur mem stats              # View memory statistics
aur headless file.md       # Run autonomous reasoning experiment
aurora-mcp status          # Check MCP server status
```

### Testing
```bash
pytest tests/unit/         # Unit tests (fast)
pytest tests/integration/  # Integration tests
pytest tests/performance/  # Performance benchmarks
pytest -v -k "test_name"   # Run specific test
pytest --cov=packages --cov-report=html  # Coverage report
```

---

## Key Patterns

### Code Organization
- Namespace packages: `packages/core/src/aurora_core/` → `from aurora.core import ...`
- Test structure mirrors package structure: `tests/unit/core/`, `tests/integration/soar/`
- Config files: `pyproject.toml` (central), `pytest.ini`, `mypy.ini`, `ruff.toml`
- Entry points: `packages/cli/src/aurora_cli/main.py` → `aur` command

### Quality Standards
- **Type Safety**: MyPy strict mode, 0 errors required
- **Test Coverage**: Maintain 74%+ coverage (target 85%)
- **Linting**: Ruff with comprehensive rules (see `ruff.toml`)
- **Security**: Bandit scanning, no secrets in code
- **Performance**: Simple queries <2s, complex queries <10s, memory <100MB for 10K chunks

### Development Workflow
1. Create branch from `main`
2. Write tests first (TDD encouraged)
3. Implement feature
4. Run `make quality-check` before commit
5. Create PR with descriptive title
6. Ensure CI passes (GitHub Actions)

---

## Documentation

### Getting Started
- MCP Setup: @docs/MCP_SETUP.md (Claude Desktop integration)
- Quick Start: @docs/cli/QUICK_START.md (5-minute setup)
- CLI Usage: @docs/cli/CLI_USAGE_GUIDE.md (comprehensive command reference)

### Architecture & Design
- SOAR Pipeline: @docs/architecture/SOAR_ARCHITECTURE.md
- API Contracts: @docs/architecture/API_CONTRACTS_v1.0.md
- Agent Integration: @docs/architecture/AGENT_INTEGRATION.md

### Development
- Testing Guide: @docs/development/TESTING.md (comprehensive testing documentation)
- Extension Guide: @docs/development/EXTENSION_GUIDE.md
- Prompt Engineering: @docs/development/PROMPT_ENGINEERING_GUIDE.md
- Migration Guide: @docs/development/PHASE4_MIGRATION_GUIDE.md

### Reference
- Complete Documentation Index: @docs/KNOWLEDGE_BASE.md
- Troubleshooting: @docs/TROUBLESHOOTING.md
- Error Catalog: @docs/cli/ERROR_CATALOG.md
- Technical Debt: @docs/improvement-areas.md

### Release History
- Latest Release: @docs/phases/phase2/RELEASE_NOTES_v0.2.0.md
- Phase Archives: @docs/phases/ (phase1, phase2, phase3)

---

## Important Notes

### Package Publishing
- **PyPI Name**: `aurora-actr` (install: `pip install aurora-actr[all]`)
- **Import Name**: `aurora` (import: `from aurora.core import ...`)
- **Namespace Mapping**: `aurora.core` → `aurora_core` package

### MCP Integration (Primary Workflow)
- Native Claude Desktop integration via Model Context Protocol
- 5 tools: aurora_search, aurora_index, aurora_stats, aurora_context, aurora_related
- Configuration: `~/.config/Claude/claude_desktop_config.json` (Linux)
- Restart Claude Desktop after config changes

### Performance Targets
- Simple query: <2s (achieved: 0.002s - 1000x faster)
- Complex query: <10s (achieved)
- Memory (10K chunks): <100MB (achieved: 39MB)
- Retrieval: <500ms for 10K chunks
- Test pass rate: 97%+ (1,766+ tests)

### Known Limitations
- 14 skipped tests (external APIs, large-scale tests, edge cases - all documented)
- 6 mypy errors in llm_client.py (non-blocking, tracked for Phase 3)
- Tree-sitter parsing currently Python-only (extensible to other languages)

### Cost Management
- Budget tracking: `~/.aurora/budget_tracker.json`
- Monthly limit enforcement (soft at 80%, hard at 100%)
- Per-query estimation: SIMPLE ~$0.001, MEDIUM ~$0.05, COMPLEX ~$0.50, CRITICAL ~$2.00
- API keys: ANTHROPIC_API_KEY, OPENAI_API_KEY (env vars only)

### Git Workflow
- Main branch: `main`
- Clean git status (no uncommitted changes)
- Recent commits focused on Python 3.12 compatibility, mypy fixes, test improvements

---

## Quick Problem-Solving

**"Tests are failing"**
→ Run `make quality-check` for comprehensive diagnostics
→ Check @docs/TROUBLESHOOTING.md for common issues
→ Review @docs/cli/ERROR_CATALOG.md for specific errors

**"MCP server not working"**
→ Run `aurora-mcp status` to diagnose
→ Check Claude Desktop config: `~/.config/Claude/claude_desktop_config.json`
→ See @docs/MCP_SETUP.md for detailed setup

**"Need to understand architecture"**
→ Start with @docs/architecture/SOAR_ARCHITECTURE.md
→ Review @docs/phases/phase2/RELEASE_NOTES_v0.2.0.md for Phase 2 overview
→ Check @docs/KNOWLEDGE_BASE.md for complete documentation index

**"Want to add new feature"**
→ Review @docs/development/EXTENSION_GUIDE.md
→ Check @docs/development/CODE_REVIEW_CHECKLIST.md for quality gates
→ Ensure tests in place (see @docs/development/TESTING.md)

**"Type errors from mypy"**
→ Strict mode enabled in `mypy.ini`
→ Run `make type-check` for full report
→ 6 known errors in llm_client.py (tracked, non-blocking)

---

**For comprehensive documentation, see** @docs/KNOWLEDGE_BASE.md
