# AURORA

## Agent System

**IMPORTANT**: Global agentic agent system is active (from `~/.claude/CLAUDE.md`).
- All requests route through **orchestrator** first (unless you specify `@agent-id` or `As agent-id, ...`)
- Orchestrator analyzes intent and matches to optimal workflow pattern
- See `~/.claude/CLAUDE.md` for 9 pre-defined workflow patterns
- Available agents: orchestrator, business-analyst, holistic-architect, full-stack-dev, qa-test-architect, product-owner, product-manager, context-initializer

---

## Quick Context

AURORA: Adaptive Unified Reasoning and Orchestration Architecture - cognitive framework for AI systems with persistent memory, reasoning, and orchestration. Built on ACT-R/SOAR principles.

**Version**: v0.2.0 | **Root**: /home/hamr/PycharmProjects/aurora | **Quality**: 1,766+ tests (97% pass), 74%+ coverage

## Package Structure

- **aurora-core** - Storage, chunks, activation scoring, cost tracking
- **aurora-context-code** - Tree-sitter parsing (Python), chunking
- **aurora-soar** - Agent registry, 9-phase orchestration pipeline
- **aurora-reasoning** - LLM integration (Anthropic/OpenAI/Ollama)
- **aurora-cli** - CLI interface (`aur` command)
- **aurora-testing** - Test utilities, fixtures, benchmarks

**Import**: `from aurora.core import ...` (namespace packages map `aurora.core` → `aurora_core`)

## Common Commands

```bash
# Development
make quality-check         # Lint, type-check, test (all quality gates)
make test                  # Run 1,766+ tests
make type-check            # MyPy strict mode (0 errors required)

# CLI
aur --verify               # Check installation health
aur mem index .            # Index codebase for semantic search
aur mem search "text"      # Search indexed code
aur query "text"           # Query with auto-escalation
aurora-mcp status          # Check MCP server status

# Testing
pytest tests/unit/         # Unit tests (fast)
pytest --cov=packages      # Coverage report
```

## Critical Gotchas

**PyPI vs Import Names**:
- Install: `pip install aurora-actr[all]` (PyPI name)
- Import: `from aurora.core import ...` (namespace)
- Packages are `aurora_core`, `aurora_soar`, etc.

**MCP Integration** (Primary interface):
- Config: `~/.config/Claude/claude_desktop_config.json` (Linux)
- Command: `python -m aurora.mcp.server`
- Restart Claude Desktop after config changes

**9-Phase SOAR**: Assess → Retrieve → Decompose → Verify → Route → Collect → Synthesize → Record → Respond

**ACT-R Activation**: Frequency + Recency + Semantic Similarity + Context Boost (hybrid 60/40)

**Performance Targets**: Simple queries <2s, complex <10s, memory <100MB for 10K chunks

## Documentation

Complete reference: docs/KNOWLEDGE_BASE.md

Key guides:
- MCP Setup: docs/MCP_SETUP.md
- CLI Usage: docs/cli/CLI_USAGE_GUIDE.md
- Architecture: docs/architecture/SOAR_ARCHITECTURE.md
- Troubleshooting: docs/TROUBLESHOOTING.md
- Testing: docs/development/TESTING.md
- API Contracts: docs/architecture/API_CONTRACTS_v1.0.md

## Important Notes

**Known Issues**:
- 14 skipped tests (external APIs, documented)
- 6 mypy errors in llm_client.py (tracked, non-blocking)
- Tree-sitter: Python-only currently

**Cost Tracking**: Budget at `~/.aurora/budget_tracker.json` | API keys via env vars only

**Git**: Main branch `main` | Clean status | Recent: Python 3.12 compat, mypy fixes
