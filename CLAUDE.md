<!-- AURORA:START -->
# Aurora Instructions

These instructions are for AI assistants working in this project.

Always open `@/.aurora/AGENTS.md` when the request:
- Mentions planning or proposals (words like plan, create, implement)
- Introduces new capabilities, breaking changes, or architecture shifts
- Sounds ambiguous and you need authoritative guidance before coding

Use `@/.aurora/AGENTS.md` to learn:
- How to create and work with plans
- Aurora workflow and conventions
- Project structure and guidelines

Keep this managed block so 'aur init --config' can refresh the instructions.

<!-- AURORA:END -->

# Aurora

## Agent System
Global agents: `~/.claude/CLAUDE.md`
Orchestrator-first routing for complex requests

---

## Quick Context
Memory-first planning and multi-agent orchestration framework. Uses ACT-R memory, SOAR decomposition, and CLI-agnostic agent execution. Local-first with optional LLM features.

## Tech Stack
Python 3.10+, Click CLI, Pydantic, SQLite, tree-sitter, BM25, sentence-transformers (optional)

## Commands
Build: `make install` | Test: `make test` | Lint: `make lint` | Quality: `make quality-check`

## CLI Entry Points
- `aur init` - Initialize project
- `aur mem index .` - Index codebase
- `aur mem search "query"` - Search memory
- `aur goals "Add feature"` - Decompose goal into tasks
- `aur soar "How does X work?"` - Answer complex questions
- `aur spawn tasks.md` - Execute tasks in parallel
- `aur doctor` - Health check

## Key Patterns
- Monorepo: 9 packages in `packages/` (cli, core, context-code, soar, reasoning, planning, spawner, implement, testing)
- All packages use hatchling build, installed editable
- Tests in `tests/` with markers: unit, integration, performance, ml
- Config resolution: CLI flag > env var > project config > global config > default

## Critical Paths
- CLI commands: `packages/cli/src/aurora_cli/commands/`
- Memory store: `packages/core/src/aurora_core/store/`
- SOAR pipeline: `packages/soar/src/aurora_soar/orchestrator.py`
- Code indexing: `packages/context-code/src/aurora_context_code/`

## Development
```bash
./install.sh              # Install all packages editable
make test-unit            # Fast tests (~30s)
aur mem index . --force   # Rebuild memory index
```

## Documentation
Index: `docs/KNOWLEDGE_BASE.md`
