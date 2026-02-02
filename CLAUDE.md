# CLAUDE.md

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

---

## Learned Rules

**Exit Codes:** 0 = success, anything else = failure. Never say "done" after failed command. After 2 consecutive errors, STOP and ask.

**Verification:** Implement ONE step at a time, verify each. After Edit, run tests/linter. After Read/Grep error, stop and report.

**Stuck Detection:** Same tool 3+ times with no progress = STOP, try different approach or ask.

**Resource Limits:** After interrupt/timeout/kill, use simpler alternatives or ask before retrying.

---

## Commands

| Task | Command |
|------|---------|
| Install | `make install-dev` |
| Test | `make test` |
| Lint | `make format` |
| Types | `make type-check` |
| Quality | `make quality-check` |

## Packages

```
packages/
  core/         Models, SQLite, config
  context-code/ Tree-sitter, BM25, embeddings
  context-doc/  PDF/DOCX parsing
  reasoning/    LLM clients
  soar/         9-phase pipeline
  planning/     Plan generation
  spawner/      Parallel execution
  implement/    Sequential execution
  cli/          Click CLI (aur)
  testing/      Test utilities
```

## Critical Patterns

**Config Resolution:** CLI flags > env vars > project `.aurora/config.json` > global `~/.aurora/config.json` > defaults

**Memory:** Hybrid retrieval (BM25 40% + ACT-R 30% + semantic 30%). DB at `.aurora/memory.db`

**SOAR:** ASSESS > RETRIEVE > DECOMPOSE > VERIFY > ROUTE > COLLECT > SYNTHESIZE > RECORD > RESPOND

## Entry Points

| Area | File |
|------|------|
| CLI commands | `packages/cli/src/aurora_cli/commands/` |
| Memory store | `packages/core/src/aurora_core/store/sqlite.py` |
| SOAR orchestrator | `packages/soar/src/aurora_soar/orchestrator.py` |
| Code indexer | `packages/context-code/src/aurora_context_code/indexer.py` |

## Git

Commit format: `type: description` (feat, fix, docs, refactor, perf, test, chore). No co-author.

## Docs

See `docs/KNOWLEDGE_BASE.md` for detailed documentation.
