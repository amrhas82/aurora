# Aurora Knowledge Base

Quick index to detailed documentation for AI assistants and developers.

## Architecture
10-package monorepo: cli, core, context-code, context-doc, soar, reasoning, planning, spawner, implement, testing. ACT-R memory + SOAR pipeline + multi-agent orchestration.
- `docs/architecture.md`

## Document Indexing (context-doc)
PDF/DOCX parsing with hierarchical section extraction, TOC support, and page references. Uses DocChunk type.
- `packages/context-doc/src/aurora_context_doc/indexer.py` - Main indexer
- `packages/context-doc/src/aurora_context_doc/parser/` - PDF and DOCX parsers

## Development
Setup, testing (84%+ coverage), code style (ruff, mypy), CI/CD workflow.
- `docs/development.md`

## Performance Testing
Startup benchmarks, regression guards, profiling guide. Target: <3s for `aur soar`.
- `docs/PERFORMANCE_TESTING.md` (full guide)
- `docs/PERFORMANCE_QUICK_REF.md` (quick reference)
- `tests/performance/README.md` (test suite docs)

## Performance Analysis
Memory search profiling, cache hit/miss patterns, optimization roadmap.
- `docs/analysis/MEMORY_SEARCH_PERFORMANCE_PROFILE.md` - Detailed profiling of `aur mem search` (20.4s breakdown)
- `docs/analysis/MEMORY_SEARCH_OPTIMIZATION_PLAN.md` - Optimization roadmap (pre-tokenization, BM25, query cache)
- `docs/analysis/MEMORY_SEARCH_QUICK_REF.md` - Quick reference for memory search performance
- `docs/analysis/CACHE_HIT_MISS_ANALYSIS.md` - Comprehensive cache behavior analysis (3 layers, patterns)
- `docs/analysis/CACHE_QUICK_REF.md` - Quick reference for cache hit/miss patterns
- `docs/analysis/FALLBACK_QUALITY_ANALYSIS.md` - Epic 2 qualitative validation (100% overlap, 10 test queries)
- `docs/analysis/EPIC2_PERFORMANCE_RESULTS.md` - Epic 2 performance metrics (lazy loading, dual-hybrid fallback)

## CLI Commands
All aur commands: init, mem, soar, goals, spawn, agents, doctor, headless, budget.
- `docs/guides/COMMANDS.md`

## Configuration
Multi-tier config resolution, environment variables, goals/soar/spawn settings.
- `docs/reference/CONFIG_REFERENCE.md`

## SOAR Pipeline
9-phase orchestration: Assess, Retrieve, Decompose, Verify, Route, Collect, Synthesize, Record, Respond.
- `docs/reference/SOAR_ARCHITECTURE.md`

## Tools Integration
20+ CLI tools supported (claude, cursor, aider, etc.), tool selection, model configuration.
- `docs/guides/TOOLS_GUIDE.md`

## Agent System
Agent discovery, matching, gap detection, custom agent definitions.
- `docs/reference/AGENT_INTEGRATION.md`

## API Contracts
Memory store, SOAR orchestrator, agent registry interfaces.
- `docs/reference/API_CONTRACTS_v1.0.md`

## ML/Embeddings
Optional semantic search with sentence-transformers, custom embedding models.
- `docs/reference/ML_MODELS.md`

## Troubleshooting
Common issues: install, permissions, config, memory, agent gaps.
- `docs/guides/CLI_TROUBLESHOOTING.md`

## ACT-R Memory
Activation scoring, hybrid retrieval weights, chunk types.
- `docs/guides/ACTR_ACTIVATION.md`

## Migration
From MCP tools, version upgrades, config changes.
- `docs/reference/MIGRATION.md`

---

**File Locations**

Project-local (created by `aur init` in project directory):
- Project config: `.aurora/config.json`
- Memory DB: `.aurora/memory.db` (project-specific, not global)
- Plans: `.aurora/plans/`
- Agents: `.aurora/agents/` (optional, project-specific)

Global (user-level):
- Global config: `~/.aurora/config.json`
- Budget tracker: `~/.aurora/budget_tracker.json`
- Agents: `~/.aurora/agents/` (optional, global)

**Note**: Database is ALWAYS project-local. Must run `aur init` in project directory first, then `aur mem index .` to populate.
