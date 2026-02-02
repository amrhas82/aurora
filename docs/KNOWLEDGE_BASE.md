# Aurora Knowledge Base

Quick index to documentation for AI assistants and developers.

## Documentation Structure

Full documentation is organized in `/docs/` using a 5-tier hierarchy:
- **[docs/README.md](README.md)** - Navigation guide

## Quick Links

| Topic | Location |
|-------|----------|
| Architecture | [00-context/system-state.md](00-context/system-state.md) |
| CLI Commands | [02-features/cli/COMMANDS.md](02-features/cli/COMMANDS.md) |
| Configuration | [04-process/reference/CONFIG_REFERENCE.md](04-process/reference/CONFIG_REFERENCE.md) |
| SOAR Pipeline | [02-features/soar/SOAR_ARCHITECTURE.md](02-features/soar/SOAR_ARCHITECTURE.md) |
| Troubleshooting | [04-process/troubleshooting/TROUBLESHOOTING.md](04-process/troubleshooting/TROUBLESHOOTING.md) |
| Development | [04-process/development/development.md](04-process/development/development.md) |
| Testing | [04-process/development/TESTING_GUIDE.md](04-process/development/TESTING_GUIDE.md) |

## Package Overview

10-package monorepo: cli, core, context-code, context-doc, soar, reasoning, planning, spawner, implement, testing.

**Core concepts:**
- ACT-R memory + SOAR pipeline + multi-agent orchestration
- Hybrid retrieval: BM25 (40%) + ACT-R activation (30%) + semantic (30%)
- 9-phase SOAR: ASSESS → RETRIEVE → DECOMPOSE → VERIFY → ROUTE → COLLECT → SYNTHESIZE → RECORD → RESPOND

## Key Entry Points

| Area | File |
|------|------|
| CLI commands | `packages/cli/src/aurora_cli/commands/` |
| Memory store | `packages/core/src/aurora_core/store/sqlite.py` |
| SOAR orchestrator | `packages/soar/src/aurora_soar/orchestrator.py` |
| Code indexer | `packages/context-code/src/aurora_context_code/indexer.py` |

## File Locations

**Project-local** (created by `aur init`):
- `.aurora/config.json` - Project config
- `.aurora/memory.db` - Memory database
- `.aurora/plans/` - Generated plans

**Global**:
- `~/.aurora/config.json` - Global config
- `~/.aurora/budget_tracker.json` - Cost tracking

**Note**: Database is ALWAYS project-local. Run `aur init` first, then `aur mem index .`
