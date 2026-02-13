# Aurora Testing Guide

**Last Updated**: 2026-02-13
**Status**: Active

---

## Current State

After the February 2026 test cleanup, all tests live in `packages/*/tests/` and pass on Python 3.12+.

| Metric | Value |
|--------|-------|
| **Total Tests** | 2,508 |
| **Test Files** | 140 |
| **Test Lines** | ~47,000 |
| **Pass Rate** | 100% (0 failures, 3 skipped) |
| **Coverage** | 57% |
| **CI Python** | 3.12 |

### Per-Package Coverage

| Package | Tests | Coverage |
|---------|-------|----------|
| **core** | 885 | 78% |
| **cli** | 542 | 55% |
| **planning** | 290 | 70% |
| **context-code** | 276 | 48% |
| **soar** | 167 | 46% |
| **spawner** | 158 | 45% |
| **reasoning** | 121 | 94% |
| **implement** | 35 | 91% |
| **lsp** | 37 | 34% |

---

## Test Location

All tests are in `packages/*/tests/`:

```
packages/<pkg>/tests/
  unit/           # Fast, isolated, mocked dependencies
  integration/    # Multi-component, real DB, real filesystem
  e2e/            # Full CLI workflows, subprocess calls
  conftest.py     # Shared fixtures
```

**pytest.ini** sets `testpaths = packages src`.

---

## Running Tests

```bash
# All tests
make test

# Specific package
pytest packages/core/tests/

# Unit only
pytest packages/core/tests/unit/

# Integration + E2E only
pytest packages/core/tests/integration/ packages/core/tests/e2e/

# Skip ML and real API tests (CI default)
pytest -m "not ml and not real_api"

# With coverage
pytest --cov=packages --cov-report=term
```

---

## Markers

Three essential markers only:

| Marker | Purpose |
|--------|---------|
| `@pytest.mark.ml` | Requires ML deps (torch, transformers). Skipped if not installed. |
| `@pytest.mark.slow` | Runtime > 5s. |
| `@pytest.mark.real_api` | Calls external APIs. Skipped in CI. |

---

## Test Classification

| Type | Characteristics | Location |
|------|----------------|----------|
| **Unit** | Single component, mocked deps, no I/O, <1s | `tests/unit/` |
| **Integration** | Multi-component, real DB/filesystem, tmp_path, <10s | `tests/integration/` |
| **E2E** | Full CLI workflows, subprocess, real config, <60s | `tests/e2e/` |

---

## CI/CD

**Workflow**: `.github/workflows/ci.yml`

- Python 3.12 on ubuntu-latest
- Installs all packages editable
- Runs `pytest -m "not ml and not real_api" --timeout=60`
- Coverage uploaded to Codecov
- Tests must be self-sufficient — no dependency on `.aurora/` directory (use `tmp_path` or `monkeypatch` for `get_aurora_dir`)

---

## Coverage Priorities

### Completed (Feb 2026)

| Area | Tests Added | Coverage Result |
|------|-------------|-----------------|
| `core/store/sqlite.py` — access tracking | 15 | 62% |
| `core/activation/` — E2E pipeline | 12 | 78% (package) |
| `cli/commands/` — mem index/search | 15 | 52% (package) |
| `soar/phases/` — retrieve & synthesize | 16 | 46% (package) |
| `context-code/semantic/` — retriever fallbacks | 14 | 48% (package) |
| `spawner/` — recovery, observability, early detection | 29 | 45% (package) |
| `lsp/` — languages registry, diagnostics | 30 | 34% (package) |
| `cli/` — escalation, health checks, ignore patterns | 28 | 55% (package) |

### Remaining Gaps

| Priority | Area | Coverage | Blocker |
|----------|------|----------|---------|
| **P1** | `spawner/spawner.py` | 3% | No LLM needed — orchestration logic is testable |
| **P1** | `lsp/analysis.py`, `lsp/client.py` | 14-17% | No LLM needed — ripgrep paths, LSP client logic |
| **P1** | `cli/commands/` (agents, budget) | 55% | No LLM needed — CLI arg parsing, config, friction |
| **P2** | `soar/orchestrator.py` | 6% | Needs LLM calls — mark `@pytest.mark.real_api`, skip in CI |
| **P2** | `soar/phases/` (assess, collect, decompose, verify, respond) | 5-13% | Needs LLM calls — mark `@pytest.mark.real_api`, skip in CI |
| **P2** | `reasoning/llm_client.py` | 23% | Needs LLM calls — mark `@pytest.mark.real_api`, skip in CI |

### LLM-Dependent Tests

Tests that make real LLM calls use `@pytest.mark.real_api`. CI skips them via `-m "not ml and not real_api"`. Run locally with:

```bash
# Run only LLM-dependent tests (requires API key in env)
pytest -m real_api -v

# Run everything including LLM tests
pytest -v
```

These tests are for local verification only — they require API keys, cost money, and have non-deterministic output. Keep them focused on contract validation (correct request/response shapes) rather than output quality.

**Philosophy**: Write integration tests that test real behavior over unit tests that mock everything. A test that exercises SQLiteStore with tmp_path is worth 10 tests that mock sqlite3.

---

## Writing Tests

### Do

- Use `tmp_path` for filesystem tests
- Use `:memory:` or `tmp_path` SQLite for DB tests
- Test behavior, not implementation
- Use dependency injection over `@patch`
- Keep tests fast and deterministic

### Don't

- Mock more than 60% of the test
- Write smoke tests (`assert X is not None`)
- Add test-only methods to production code
- Use `@patch` on internal implementation details
- Create test files that duplicate existing ones (causes pytest collection conflicts)

---

## What Was Cleaned Up (February 2026)

| What | Removed | Reason |
|------|---------|--------|
| Root `tests/` directory | ~4,500 lines | Consolidated into `packages/*/tests/` |
| Mock-heavy tests | ~36,400 lines | Tested mocks not behavior (>60% mock) |
| Failing/stale tests | ~17,100 lines | Testing deleted APIs, always failing |
| Import smoke tests | ~12,100 lines | `assert X is not None` adds no value |
| Dead production code | ~2,800 lines | LSP confirmed 0 usages |
| Duplicate test files | 10 renames | pytest module collision |
| MCP package tests | all | MCP package removed |
| Headless tests | all | Headless mode removed |

**Before**: 5,500 tests, 314 files, 126k lines, unknown pass rate
**After cleanup**: 2,359 tests, 137 files, 45.5k lines, 100% pass rate, ~21% coverage
**After P0 integration tests**: 2,451 tests, 56% coverage — 92 real integration tests added across 5 areas
**After P1 integration tests**: 2,508 tests, 57% coverage — 87 more tests (spawner recovery/observability, LSP languages/diagnostics, CLI escalation/health) + fix escalation.py bug
