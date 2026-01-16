# Aurora Knowledge Base

Quick index to detailed documentation for AI assistants and developers.

## Architecture
9-package monorepo: cli, core, context-code, soar, reasoning, planning, spawner, implement, testing. ACT-R memory + SOAR pipeline + multi-agent orchestration.
- `docs/architecture.md`

## Development
Setup, testing (84%+ coverage), code style (ruff, mypy), CI/CD workflow.
- `docs/development.md`

## Performance Testing
Startup benchmarks, regression guards, profiling guide. Target: <3s for `aur soar`.
- `docs/PERFORMANCE_TESTING.md` (full guide)
- `docs/PERFORMANCE_QUICK_REF.md` (quick reference)
- `tests/performance/README.md` (test suite docs)

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
