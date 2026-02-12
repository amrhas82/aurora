# Aurora Testing Guide

**Last Updated**: 2026-02-12
**Status**: Active (post-cleanup)

---

## Current State

After the February 2026 test cleanup, all tests live in `packages/*/tests/` and pass on Python 3.12+.

| Metric | Value |
|--------|-------|
| **Total Tests** | ~2,440 |
| **Test Files** | 144 |
| **Test Lines** | ~48,000 |
| **Pass Rate** | 100% (0 failures) |
| **Coverage** | ~21% (post-cleanup, many mock-heavy tests deleted) |
| **CI Python** | 3.12 |

### Per-Package Breakdown

| Package | Tests | Unit Files | Integration/E2E Files |
|---------|-------|------------|----------------------|
| **core** | 861 | 20 | 6 |
| **cli** | 544 | 21 | 5 |
| **planning** | 292 | 24 | 1 |
| **context-code** | 253 | 17 | 4 |
| **spawner** | 163 | 4 | 5 |
| **soar** | 162 | 11 | 1 |
| **reasoning** | 121 | 4 | 1 |
| **implement** | 35 | 0 | 4 |

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

**Workflow**: `.github/workflows/testing-infrastructure-new.yml`

- Python 3.12 on ubuntu-latest
- Installs all packages editable
- Runs `pytest -m "not ml and not real_api" --timeout=60`
- Coverage uploaded to Codecov

---

## Coverage Priorities

Coverage is ~21% after deleting mock-heavy tests that tested mocks, not behavior. Areas needing real tests:

| Priority | Area | Current | Why |
|----------|------|---------|-----|
| **P0** | `core/store/sqlite.py` | Low | Core data layer |
| **P0** | `core/activation/` | Low | ACT-R math is critical |
| **P1** | `cli/commands/` | Low | User-facing commands |
| **P1** | `context-code/semantic/` | Low | Retrieval pipeline |
| **P2** | `soar/phases/` | Low | SOAR pipeline phases |
| **P2** | `reasoning/llm_client.py` | Low | LLM integration |

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
**After**: ~2,440 tests, 144 files, 48k lines, 100% pass rate
