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

## Learned Rules (from friction analysis)

### 1. Verify Bash exit codes before claiming success
After ANY Bash command:
- Exit code 0 = success. Anything else = failure.
- If exit code != 0, report the error clearly. Do not minimize or claim partial success.
- If running tests, "PASSED" or "ok" must appear in output AND exit code must be 0.
- Never say "done" or "complete" after a failed command.

### 2. Stop after 2 consecutive failures
After 2 consecutive Bash:error results:
- STOP attempting the same approach.
- Read and analyze the actual error output.
- If timeout (exit 124) or killed (exit 137), the command is too heavy - simplify.
- Ask the user for guidance rather than retry blindly.

### 3. After Edit, verify before moving on
After editing code:
- Run the relevant test or linter.
- Wait for completion and check exit code.
- Only proceed if verification passes.

### 4. "Implement the plan" requires incremental verification
When given a multi-step plan:
- Implement ONE step at a time.
- Verify each step before proceeding to the next.
- If a step fails, stop and report - don't cascade into more failures.

### 5. When user asks "test it" or "did you test it"
- Run the actual test command.
- Wait for full output.
- Report exact results: pass count, fail count, exit code.
- If tests fail, show which tests failed and why.

---

## Overview

Aurora is a memory-first planning and multi-agent orchestration framework combining ACT-R cognitive memory, SOAR 9-phase reasoning, and CLI-agnostic agent execution. Python 3.10+ monorepo with 10 packages.

## Commands

| Task | Command |
|------|---------|
| Install (dev) | `make install-dev` |
| Test all | `make test` |
| Test unit | `pytest tests/unit/ -v` |
| Lint + format | `make format` |
| Type check | `make type-check` |
| Quality check | `make quality-check` |
| Benchmark | `make benchmark-soar` |

## Package Structure

```
packages/
  core/         Models, SQLite store, config
  context-code/ Tree-sitter parsing, BM25, embeddings
  context-doc/  PDF/DOCX parsing, hierarchical sections
  reasoning/    LLM clients (Anthropic, OpenAI, Ollama)
  soar/         9-phase orchestration pipeline
  planning/     Plan generation
  spawner/      Parallel task execution
  implement/    Sequential task execution
  cli/          Click CLI (aur command)
  testing/      Test utilities
```

Install order matters: core -> context-code -> reasoning -> soar -> planning -> spawner -> implement -> cli -> testing

## Critical Patterns

**Config Resolution** (highest to lowest):
1. CLI flags (`--tool cursor`)
2. Environment variables (`AURORA_GOALS_TOOL`)
3. Project config (`.aurora/config.json`)
4. Global config (`~/.aurora/config.json`)
5. Built-in defaults

**Memory System:**
- Hybrid retrieval: BM25 (40%) + ACT-R activation (30%) + semantic (30%)
- Chunk types: `code`, `doc`, `kb`, `soar`
- Database always project-local at `.aurora/memory.db`

**SOAR Pipeline:** ASSESS -> RETRIEVE -> DECOMPOSE -> VERIFY -> ROUTE -> COLLECT -> SYNTHESIZE -> RECORD -> RESPOND

**Lazy Loading:** ML imports are deferred to first use. BM25 index loads on first retrieve() call.

## Key Entry Points

| Area | File |
|------|------|
| CLI commands | `packages/cli/src/aurora_cli/commands/` |
| Memory store | `packages/core/src/aurora_core/store/sqlite.py` |
| SOAR orchestrator | `packages/soar/src/aurora_soar/orchestrator.py` |
| Spawner | `packages/spawner/src/aurora_spawner/spawner.py` |
| Code indexer | `packages/context-code/src/aurora_context_code/indexer.py` |
| Doc indexer | `packages/context-doc/src/aurora_context_doc/indexer.py` |
| Slash commands | `packages/cli/src/aurora_cli/templates/slash_commands.py` |

## Testing

```bash
# Single test file
pytest tests/unit/core/test_store.py -v

# Single test function
pytest tests/unit/core/test_store.py::test_save_chunk -v

# With output
pytest tests/unit/core/test_store.py -vv -s
```

Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.performance`, `@pytest.mark.ml`

## Git Conventions

Never add Claude as co-author. Use default git settings only.

Commit format: `type: description` where type is feat, fix, docs, refactor, perf, test, chore

## Documentation Index

See `docs/KNOWLEDGE_BASE.md` for detailed documentation pointers.
