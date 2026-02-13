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

## MCP Tools Available

Aurora provides MCP tools for code intelligence (automatically available in Claude):

**`lsp`** - LSP code intelligence with 3 actions:
- `deadcode` - Find unused symbols, generates CODE_QUALITY_REPORT.md
- `impact` - Analyze symbol usage, show callers and risk level
- `check` - Quick usage check before editing

**`mem_search`** - Search indexed code with LSP enrichment:
- Returns code snippets with metadata (type, symbol, lines)
- Enriched with LSP context (used_by, called_by, calling)
- Includes git info (last_modified, last_author)

**When to use:**
- Before edits: Use `lsp check` to see usage impact
- Before refactoring: Use `lsp deadcode` or `lsp impact` to find all references
- Code search: Use `mem_search` instead of grep for semantic results
- After large changes: Use `lsp deadcode` to find orphaned code

Keep this managed block so 'aur init --config' can refresh the instructions.

<!-- AURORA:END -->

---

## Learned Rules

**Errors:** Non-zero exit or tool error = STOP. Never claim "done" with errors. 2 consecutive failures = ask user, don't retry.

**Verify:** Check path exists before Read/Edit. Run tests after Edit. One step at a time.

**User Wins:** When user contradicts with evidence, don't push back. Re-read, acknowledge, try different.

---

## Dev Rules

**POC first.** Always validate logic with a ~15min proof-of-concept before building. Cover happy path + common edges. POC works → design properly → build with tests. Never ship the POC.

**Build incrementally.** Break work into small independent modules. One piece at a time, each must work on its own before integrating.

**Dependency hierarchy — follow strictly:** vanilla language → standard library → external (only when stdlib can't do it in <100 lines). External deps must be maintained, lightweight, and widely adopted. Exception: always use vetted libraries for security-critical code (crypto, auth, sanitization).

**Lightweight over complex.** Fewer moving parts, fewer deps, less config. Express over NestJS, Flask over Django, unless the project genuinely needs the framework. Simple > clever. Readable > elegant.

**Open-source only.** No vendor lock-in. Every line of code must have a purpose — no speculative code, no premature abstractions.

For full development and testing standards, see `.claude/memory/AGENT_RULES.md`.

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

<!-- MEMORY:START -->
## Project Memory

Key facts extracted from session stashes (full details in `.claude/memory/MEMORY.md`):

- Tests must be self-sufficient, no `.aurora/` dependency in CI — use `tmp_path` or `monkeypatch` for `get_aurora_dir`
- All tests in `packages/*/tests/`, CI workflow at `.github/workflows/ci.yml` (2,608 tests, 0 failures)
- LSP supports 5 languages (Python, JS, TS, Go, Java); MCP uses `python3.12` (3.14 has anyio issues)
- `aur headless` and API key functionality removed entirely
- `_identify_dependencies()` returns empty list (imports extracted but discarded)
- CLI `aur mem search` lacks LSP enrichment (separate implementation from MCP `mem_search`)
- MCP registration: use `claude mcp add-json`, not file writes
- Don't use `git stash` with unstaged subagent changes
<!-- MEMORY:END -->
