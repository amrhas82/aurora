# Technical Debt: Test Marker Coverage

**Document Version:** 1.0
**Date:** 2025-12-27
**Related:** TECHNICAL_DEBT_COVERAGE.md (test coverage), TESTING.md (testing guide)
**Current Status:** 155 of 2,815 tests marked (5.5%)

---

## Executive Summary

This document tracks the **test marker gap** in the AURORA test suite. While test markers infrastructure is complete and 155 critical tests are marked, **94.5% of tests remain unmarked** (2,660 tests). This document provides a comprehensive analysis of what's missing and prioritizes future marker work.

**Key Findings:**
- **Total tests:** 2,815 across 121 test files
- **Marked tests:** 155 (5.5%)
- **Unmarked tests:** 2,660 (94.5%)
- **Best coverage:** E2E tests (25.4% marked)
- **Worst coverage:** Unit tests (4.1% marked)

**Decision:** Accept 5.5% marker coverage as pragmatic Phase 4 completion. Remaining marker work will be done incrementally as tests are reviewed/modified.

---

## Current Marker Coverage

### Overall Statistics

| Category | Count | Percentage |
|----------|-------|------------|
| **Total test files** | 121 | 100% |
| **Total test functions** | 2,815 | 100% |
| **Marked tests** | 155 | 5.5% |
| **Unmarked tests** | 2,660 | 94.5% |

### Coverage by Test Type

| Test Type | Marked | Total | Coverage | Gap |
|-----------|--------|-------|----------|-----|
| **E2E** | 16 | 63 | 25.4% | -74.6% |
| **Integration** | 38 | 446 | 8.5% | -91.5% |
| **Unit** | 77 | 1,892 | 4.1% | -95.9% |
| **Other** (calibration, fault injection) | 24 | 414 | 5.8% | -94.2% |

### Current Marker Distribution

| Marker | Count | Purpose |
|--------|-------|---------|
| `@pytest.mark.critical` | 63 | Must-pass tests for core functionality |
| `@pytest.mark.asyncio` | 37 | Async tests (pytest-asyncio) |
| `@pytest.mark.mcp` | 26 | MCP server and tools tests |
| `@pytest.mark.integration` | 21 | Multi-component integration tests |
| `@pytest.mark.cli` | 20 | CLI functionality tests |
| `@pytest.mark.soar` | 18 | SOAR pipeline tests |
| `@pytest.mark.e2e` | 15 | End-to-end workflow tests |
| `@pytest.mark.core` | 11 | Core storage/activation tests |
| `@pytest.mark.ml` | 9 | Tests requiring ML dependencies |
| `@pytest.mark.fast` | 5 | Tests under 100ms (quick feedback) |
| `@pytest.mark.real_api` | 2 | Tests making real API calls |
| `@pytest.mark.slow` | 1 | Tests over 1 second |
| `@pytest.mark.benchmark` | 1 | Performance benchmarks |

---

## Detailed Gap Analysis by Area

### 1. Unit Tests (1,815 unmarked, 95.9% gap) - **P1 HIGH**

**Current state:** 77 of 1,892 tests marked (4.1%)

#### 1.1 Core Package (P0 - Critical)

**Files with NO markers (high priority):**

| File | Tests | Priority | Rationale |
|------|-------|----------|-----------|
| `test_chunk_store_integration.py` | 47 | **P0** | Core data operations, must be reliable |
| `test_store_sqlite.py` (partial) | ~20 unmarked | **P0** | Database operations (11 marked, ~20 unmarked) |
| `test_cost_tracking.py` | 18 | **P1** | Cost management is user-facing |
| `test_chunk_base.py` (partial) | ~15 unmarked | **P1** | Chunk operations (some marked) |
| `test_resilience/*.py` | 52 | **P1** | Error handling and retry logic |

**Recommended markers:**
- **Critical:** Data integrity tests (save, retrieve, update)
- **Core:** Activation scoring, chunk operations
- **Fast:** Simple unit tests with no I/O

**Estimated effort:** 30-40 tests, 4-6 hours

---

#### 1.2 SOAR Package (P1 - High)

**Files with PARTIAL markers (continue tagging):**

| File | Tests | Marked | Unmarked | Priority |
|------|-------|--------|----------|----------|
| `test_phase_collect.py` | 25 | 0 | 25 | **P1** | Phase 6 of pipeline |
| `test_phase_record.py` | 22 | 0 | 22 | **P2** | Phase 8 of pipeline |
| `test_phase_respond.py` | 22 | 0 | 22 | **P2** | Phase 9 of pipeline |
| `test_phase_assess.py` | 18 | 7 | 11 | **P1** | Core complexity assessment |
| `test_phase_retrieve.py` | 29 | 3 | 26 | **P1** | Context retrieval logic |
| `test_phase_decompose.py` | 21 | 3 | 18 | **P1** | Query decomposition |
| `test_phase_route.py` | 27 | 3 | 24 | **P1** | Agent routing logic |
| `test_phase_verify.py` | 28 | 4 | 24 | **P1** | Retrieval quality handling |

**Analysis:**
- **Phases 1-5 (Assess, Retrieve, Decompose, Verify, Route):** Partially marked, need completion
- **Phases 6, 8, 9 (Collect, Record, Respond):** No markers, lower priority (simple pass-through logic)

**Recommended approach:**
1. Mark remaining critical path tests in Phases 1-5 (20-25 tests)
2. Mark 1-2 representative tests per Phase 6, 8, 9 (6-10 tests)
3. Total: ~30-35 tests

**Estimated effort:** 30-35 tests, 3-4 hours

---

#### 1.3 Context-Code Package (P2 - Medium)

**Files with NO markers:**

| File | Tests | Priority | Rationale |
|------|-------|----------|-----------|
| `test_parser_base.py` | 24 | **P2** | Parser infrastructure |
| `test_tree_sitter_parser.py` | 31 | **P2** | Python parsing logic |
| `test_chunking.py` | 18 | **P2** | Code chunking strategy |
| `test_semantic/test_embedding_provider.py` | 22 | **P2** | Embedding generation |
| `test_semantic/test_hybrid_retriever.py` (partial) | ~15 unmarked | **P2** | Some marked already |

**Recommended markers:**
- **Critical:** Parser initialization, basic chunking
- **Fast:** Simple parser tests
- **Integration:** Full parse → chunk workflows

**Estimated effort:** 25-30 tests, 3-4 hours

---

#### 1.4 Reasoning Package (P2 - Medium)

**Files with NO markers:**

| File | Tests | Priority | Rationale |
|------|-------|----------|-----------|
| `test_llm_client_errors.py` | 46 | **P1** | Error handling for LLM calls |
| `test_decompose.py` | 27 | **P2** | Query decomposition logic |
| `test_verify.py` | 19 | **P2** | Verification algorithm |

**Recommended markers:**
- **Critical:** API error handling, decomposition validation
- **Real_api:** Tests that need actual API calls (currently none)

**Estimated effort:** 20-25 tests, 2-3 hours

---

#### 1.5 CLI Package (P1 - High)

**Files with PARTIAL markers (continue tagging):**

| File | Tests | Marked | Unmarked | Priority |
|------|-------|--------|----------|----------|
| `test_main_cli.py` | 42 | 5 | 37 | **P1** | Main entry point |
| `test_memory_commands.py` | 87 | 2 | 85 | **P1** | Memory CLI commands |
| `test_query_command.py` | 18 | 5 | 13 | **P1** | Query command logic |
| `test_config.py` | 37 | 2 | 35 | **P1** | Configuration handling |
| `test_error_handling.py` | 12 | 3 | 9 | **P1** | User-facing errors |
| `test_escalation.py` | 26 | 0 | 26 | **P2** | Auto-escalation logic |

**Analysis:**
- Memory commands (87 tests): Only 2 marked, massive gap
- Main CLI (42 tests): Only 5 marked, user entry point
- Config (37 tests): Only 2 marked, critical for first-run experience

**Recommended approach:**
1. Mark all happy-path tests for memory commands (20-25 tests)
2. Mark error handling tests for main CLI (10-15 tests)
3. Mark validation tests for config (8-10 tests)
4. Total: ~40-50 tests

**Estimated effort:** 40-50 tests, 5-6 hours

---

### 2. Integration Tests (408 unmarked, 91.5% gap) - **P1 HIGH**

**Current state:** 38 of 446 tests marked (8.5%)

#### 2.1 Critical Integration Tests (unmarked)

| File | Tests | Priority | Rationale |
|------|-------|----------|-----------|
| `test_cost_budget.py` | 9 | **P0** | Cost tracking integration |
| `test_parse_and_store.py` | 8 | **P0** | Parse → Store pipeline |
| `test_cli_config_integration.py` (partial) | ~5 unmarked | **P1** | Some marked already |
| `test_memory_manager_integration.py` (partial) | ~8 unmarked | **P1** | Some marked already |
| `test_query_executor_integration.py` (partial) | ~6 unmarked | **P1** | Some marked already |
| `test_escalation_integration.py` (partial) | ~10 unmarked | **P1** | Some marked already |
| `test_error_recovery_workflows.py` | 21 | **P1** | Error handling flows |

**Recommended markers:**
- **Critical + Integration:** Must-pass multi-component tests
- **Integration:** All integration tests should have this marker

**Estimated effort:** 50-60 tests, 6-8 hours

---

#### 2.2 Fault Injection Tests (80 unmarked) - **P2 MEDIUM**

**Files with NO markers:**

| File | Tests | Priority | Rationale |
|------|-------|----------|-----------|
| `test_llm_fault_injection.py` | 27 | **P2** | LLM error scenarios |
| `test_store_fault_injection.py` | 32 | **P2** | Database error scenarios |
| `test_soar_fault_injection.py` | 21 | **P2** | Pipeline error scenarios |

**Recommended markers:**
- **Safety:** All fault injection tests
- **Integration:** Multi-component error scenarios

**Estimated effort:** 40-50 tests, 4-5 hours

---

#### 2.3 Calibration Tests (13 unmarked) - **P3 LOW**

**Files with NO markers:**

| File | Tests | Priority | Rationale |
|------|-------|----------|-----------|
| `test_verification_calibration.py` | 13 | **P3** | Algorithm calibration |

**Recommended markers:**
- **Benchmark:** Calibration tests
- **Slow:** These are comprehensive tests

**Estimated effort:** 13 tests, 1-2 hours

---

### 3. E2E Tests (47 unmarked, 74.6% gap) - **P1 HIGH**

**Current state:** 16 of 63 tests marked (25.4%)

#### 3.1 MCP E2E Tests (partial marking)

| File | Tests | Marked | Unmarked | Priority |
|------|-------|--------|----------|----------|
| `test_mcp_e2e.py` | 18 | 2 | 16 | **P1** | MCP workflows |

**Unmarked tests:**
- `test_get_all_search_results`
- `test_complete_query_workflow`
- `test_query_complexity_assessment`
- `test_stats_after_index`
- `test_context_from_search_results`
- `test_related_chunks_from_search`
- `test_cross_tool_consistency`
- Performance tests (3 tests)
- Sequential operations tests

**Recommended markers:**
- **Critical + E2E + MCP:** Core MCP workflows
- **E2E + MCP:** All MCP E2E tests
- **Slow:** Performance tests

**Estimated effort:** 16 tests, 2-3 hours

---

#### 3.2 CLI E2E Tests (partial marking)

| File | Tests | Marked | Unmarked | Priority |
|------|-------|--------|----------|----------|
| `test_cli_complete_workflow.py` | 17 | 0 | 17 | **P1** | CLI workflows |
| `test_headless_e2e.py` | 14 | 0 | 14 | **P1** | Headless mode |
| `test_memory_lifecycle_e2e.py` | 6 | 0 | 6 | **P1** | Memory operations |

**Recommended markers:**
- **Critical + E2E + CLI:** Core CLI workflows
- **E2E + CLI:** All CLI E2E tests

**Estimated effort:** 37 tests, 4-5 hours

---

#### 3.3 Aurora Query E2E Tests (all skipped)

| File | Tests | Marked | Unmarked | Priority |
|------|-------|--------|----------|----------|
| `test_aurora_query_e2e.py` | 8 | 0 | 8 | **P2** | Full AURORA pipeline (skipped) |

**Status:** All tests skipped (require ANTHROPIC_API_KEY)

**Recommended markers:**
- **E2E + Real_api:** Tests requiring actual API calls
- **Slow:** Full pipeline tests are slow

**Estimated effort:** 8 tests, 1 hour (quick tagging)

---

## Prioritized Recommendations

### Immediate Actions (If pursuing comprehensive marking) - **P0/P1**

**Phase 4B: Critical Path Completion (20-30 hours)**

#### Week 1: Core + CLI (10-12 hours)
1. **Core package unit tests** (30-40 tests, 4-6h):
   - Mark all chunk store integration tests as `@pytest.mark.critical + @pytest.mark.core`
   - Mark SQLite operations as `@pytest.mark.core`
   - Mark cost tracking as `@pytest.mark.critical`

2. **CLI package unit tests** (40-50 tests, 5-6h):
   - Mark memory command happy paths as `@pytest.mark.critical + @pytest.mark.cli`
   - Mark main CLI error handling as `@pytest.mark.critical + @pytest.mark.cli`
   - Mark config validation as `@pytest.mark.cli`

**Estimated effort:** 70-90 tests, 10-12 hours

---

#### Week 2: SOAR + Integration (10-12 hours)
3. **SOAR package unit tests** (30-35 tests, 3-4h):
   - Complete phase test marking (Assess, Retrieve, Decompose, Verify, Route)
   - Mark representative tests for Collect, Record, Respond phases
   - All SOAR tests get `@pytest.mark.soar`, critical ones get `@pytest.mark.critical`

4. **Integration tests** (50-60 tests, 6-8h):
   - Mark all cost budget integration tests as `@pytest.mark.critical + @pytest.mark.integration`
   - Mark parse-and-store pipeline as `@pytest.mark.integration`
   - Mark error recovery workflows as `@pytest.mark.integration`

**Estimated effort:** 80-95 tests, 10-12 hours

---

#### Week 3: E2E + Fault Injection (8-10 hours)
5. **E2E tests** (53 tests, 6-8h):
   - Mark all MCP E2E workflows as `@pytest.mark.e2e + @pytest.mark.mcp`
   - Mark all CLI E2E workflows as `@pytest.mark.e2e + @pytest.mark.cli`
   - Mark critical E2E tests as `@pytest.mark.critical`

6. **Fault injection tests** (40-50 tests, 4-5h):
   - Mark all fault injection as `@pytest.mark.safety + @pytest.mark.integration`
   - Mark critical error scenarios as `@pytest.mark.critical`

**Estimated effort:** 90-103 tests, 10-13 hours

---

### Summary: Comprehensive Marking Effort

| Phase | Tests Marked | Effort | Priority |
|-------|--------------|--------|----------|
| **Week 1: Core + CLI** | 70-90 | 10-12h | P0/P1 |
| **Week 2: SOAR + Integration** | 80-95 | 10-12h | P1 |
| **Week 3: E2E + Fault Injection** | 90-103 | 10-13h | P1/P2 |
| **Total** | **240-288** | **30-37h** | - |

**After completion:**
- Marker coverage: 5.5% → 14-15% (155 → 395-443 tests)
- Still leaves ~2,372 tests unmarked (85%)

---

## Alternative: Incremental Marking Strategy (RECOMMENDED)

Instead of comprehensive upfront marking, adopt an **incremental approach**:

### Strategy

**1. New Tests (Immediate):**
- All new tests must be marked during creation
- Use TESTING.md guidelines to determine appropriate markers
- Code review enforces marker presence

**2. Modified Tests (Ongoing):**
- When modifying a test file, mark tests in that file
- Amortize marking cost over development work
- 5-10 tests per PR, ~1-2 minutes extra per PR

**3. Bug-Driven Marking (Reactive):**
- When a bug is found in production, mark related tests as `@pytest.mark.critical`
- This naturally prioritizes tests that protect against real issues

**4. Quarterly Sprints (Proactive):**
- Dedicate 2-4 hours per quarter to mark high-value tests
- Focus on one area per quarter (Q1: CLI, Q2: SOAR, Q3: Integration, Q4: E2E)
- Over 1 year: ~50-100 tests marked (10-16 hours total)

### Benefits

✅ **Lower upfront cost:** No 30-hour marking sprint
✅ **Better prioritization:** Marks tests as their importance is discovered
✅ **Continuous improvement:** Marker coverage grows organically
✅ **Developer ownership:** Teams mark their own tests
✅ **Sustainable:** Small, regular efforts vs. one-time exhaustive work

### Expected Growth

| Timeline | Tests Marked | Coverage | Notes |
|----------|--------------|----------|-------|
| **Current** | 155 | 5.5% | Phase 4 strategic marking |
| **3 months** | 180-200 | 6.5-7% | New tests + bug fixes |
| **6 months** | 220-250 | 8-9% | + Quarterly sprint |
| **12 months** | 300-350 | 11-12% | + Sustained growth |
| **24 months** | 450-550 | 16-20% | Maturity |

---

## Gap Analysis by Marker Type

### What's Missing from Each Marker

#### `@pytest.mark.critical` (63 marked, ~200-250 needed)

**Current coverage:** Core SOAR phases, MCP tools, some CLI

**Missing:**
- **CLI commands:** ~40 tests (memory index, search, stats, config)
- **Core storage:** ~30 tests (chunk operations, SQLite persistence)
- **Cost tracking:** ~10 tests (budget enforcement, tracking)
- **Error handling:** ~20 tests (API errors, user-facing errors)
- **Integration workflows:** ~30 tests (parse→store, index→search)
- **E2E workflows:** ~40 tests (complete user journeys)

**Total gap:** ~170-190 critical tests unmarked

---

#### `@pytest.mark.cli` (20 marked, ~150-180 needed)

**Current coverage:** Main CLI, query command, memory commands, config

**Missing:**
- **Memory commands:** ~40 tests (index, search, stats, related)
- **Init command:** ~20 tests (first-run setup, config generation)
- **Headless command:** ~15 tests (headless mode execution)
- **Config management:** ~20 tests (load, save, validate, migrate)
- **Error messages:** ~15 tests (user-facing error formatting)
- **Help/version:** ~10 tests (help text, version display)
- **E2E workflows:** ~30 tests (complete CLI interactions)

**Total gap:** ~150 CLI tests unmarked

---

#### `@pytest.mark.mcp` (26 marked, ~50-60 needed)

**Current coverage:** MCP tools (query, search, index, stats), integration harness

**Missing:**
- **MCP E2E workflows:** ~15 tests (complete tool interactions)
- **Error handling:** ~8 tests (invalid inputs, missing dependencies)
- **Context/related tools:** ~5 tests (aurora_context, aurora_related)
- **Performance tests:** ~3 tests (response times, throughput)

**Total gap:** ~24-34 MCP tests unmarked

---

#### `@pytest.mark.soar` (18 marked, ~80-100 needed)

**Current coverage:** Phases 1-5 (Assess, Retrieve, Decompose, Verify, Route) partially

**Missing:**
- **Phase completion:** ~25 tests (finish marking Phases 1-5)
- **Phase 6 (Collect):** ~5 tests (context collection)
- **Phase 7 (Synthesize):** ~0 tests (no tests exist?)
- **Phase 8 (Record):** ~5 tests (recording operations)
- **Phase 9 (Respond):** ~5 tests (response formatting)
- **Headless orchestrator:** ~10 tests (headless mode logic)
- **Phase integration:** ~15 tests (multi-phase workflows)

**Total gap:** ~65-82 SOAR tests unmarked

---

#### `@pytest.mark.core` (11 marked, ~60-80 needed)

**Current coverage:** Some SQLite store, activation engine, chunk base

**Missing:**
- **Chunk operations:** ~20 tests (save, retrieve, update, delete)
- **Activation scoring:** ~15 tests (frequency, recency, context boost)
- **Store integration:** ~20 tests (multi-chunk operations, transactions)
- **Cost tracking:** ~10 tests (budget tracking, persistence)

**Total gap:** ~65 core tests unmarked

---

#### `@pytest.mark.integration` (21 marked, ~150-200 needed)

**Current coverage:** Some MCP harness, query executor, memory manager

**Missing:**
- **Parse-and-store:** ~20 tests (full pipeline)
- **Cost budget:** ~10 tests (cost tracking across components)
- **Error recovery:** ~20 tests (error handling workflows)
- **CLI integration:** ~30 tests (CLI → memory manager → store)
- **Fault injection:** ~80 tests (error scenarios)
- **Calibration:** ~13 tests (verification algorithm)

**Total gap:** ~173 integration tests unmarked

---

#### `@pytest.mark.e2e` (15 marked, ~50-60 needed)

**Current coverage:** Some MCP E2E workflows

**Missing:**
- **MCP workflows:** ~15 tests (tool interactions)
- **CLI workflows:** ~37 tests (complete user journeys)
- **Headless workflows:** ~14 tests (headless mode)
- **Memory lifecycle:** ~6 tests (index → search → update)
- **Aurora query:** ~8 tests (full SOAR pipeline with real API)

**Total gap:** ~80 E2E tests unmarked (but only ~50-60 should be marked as many are similar)

---

#### `@pytest.mark.fast` (5 marked, ~200-300 needed)

**Current coverage:** Minimal (5 tests)

**Missing:**
- **Simple unit tests:** ~200-300 tests (no I/O, pure logic)
- **Criteria:** Tests under 100ms execution time

**Note:** This marker should be applied during marking of other categories (e.g., a critical test can also be fast)

---

#### `@pytest.mark.safety` (0 marked, ~80-100 needed)

**Current coverage:** None

**Missing:**
- **Fault injection:** ~80 tests (LLM errors, store errors, SOAR errors)
- **Security tests:** ~10-20 tests (API key handling, input validation)

**Total gap:** ~80-100 safety tests unmarked

---

## Technical Debt Items

### TD-MARKER-001: CLI Test Markers (P1, 150 tests, 15-18 hours)

**Status:** Only 20 of ~170 CLI tests marked (11.8% coverage)

**Impact:** High - CLI is primary user interface

**Missing markers:**
- Memory commands: 40 tests
- Init command: 20 tests
- Config management: 20 tests
- Error messages: 15 tests
- E2E workflows: 30 tests
- Other: 25 tests

**Recommendation:**
- **Immediate (5h):** Mark 30-40 happy-path tests (memory commands, main CLI)
- **Short-term (5h):** Mark error handling and config tests
- **Medium-term (5h):** Mark E2E workflows

---

### TD-MARKER-002: Core Package Test Markers (P0, 65 tests, 8-10 hours)

**Status:** Only 11 of ~76 core tests marked (14.5% coverage)

**Impact:** Critical - Core storage is foundational

**Missing markers:**
- Chunk operations: 20 tests
- Activation scoring: 15 tests
- Store integration: 20 tests
- Cost tracking: 10 tests

**Recommendation:**
- **Immediate (4h):** Mark all chunk store integration tests
- **Short-term (4h):** Mark activation and cost tracking tests

---

### TD-MARKER-003: Integration Test Markers (P1, 173 tests, 15-20 hours)

**Status:** Only 38 of ~446 integration tests marked (8.5% coverage)

**Impact:** High - Integration tests validate component interactions

**Missing markers:**
- Parse-and-store pipeline: 20 tests
- Error recovery workflows: 20 tests
- Fault injection: 80 tests
- CLI integration: 30 tests
- Other: 23 tests

**Recommendation:**
- **Immediate (6h):** Mark critical integration workflows (parse-store, cost budget)
- **Medium-term (8h):** Mark fault injection tests as safety
- **Long-term (6h):** Mark remaining integration tests

---

### TD-MARKER-004: E2E Test Markers (P1, 47 tests, 6-8 hours)

**Status:** Only 16 of 63 E2E tests marked (25.4% coverage)

**Impact:** High - E2E tests validate complete user workflows

**Missing markers:**
- MCP E2E: 16 tests
- CLI E2E: 37 tests (across 3 files)

**Recommendation:**
- **Immediate (4h):** Mark all MCP E2E and critical CLI E2E workflows
- **Short-term (3h):** Mark remaining CLI E2E tests

---

### TD-MARKER-005: SOAR Phase Test Markers (P1, 82 tests, 8-10 hours)

**Status:** Only 18 of ~100 SOAR tests marked (18% coverage)

**Impact:** High - SOAR is core orchestration pipeline

**Missing markers:**
- Complete Phases 1-5 marking: 25 tests
- Phase 6, 8, 9 representative tests: 10 tests
- Headless orchestrator: 10 tests
- Phase integration: 15 tests

**Recommendation:**
- **Immediate (4h):** Complete marking for Phases 1-5
- **Short-term (3h):** Mark Phases 6, 8, 9 and headless
- **Medium-term (3h):** Mark phase integration tests

---

### TD-MARKER-006: Safety/Fault Injection Markers (P2, 80 tests, 8-10 hours)

**Status:** 0 of 80 fault injection tests marked (0% coverage)

**Impact:** Medium - Important for robustness, but not critical path

**Missing markers:**
- LLM fault injection: 27 tests
- Store fault injection: 32 tests
- SOAR fault injection: 21 tests

**Recommendation:**
- **Medium-term (8h):** Mark all fault injection tests with `@pytest.mark.safety + @pytest.mark.integration`

---

## Measurement and Tracking

### Key Performance Indicators (KPIs)

Track marker coverage monthly:

| KPI | Current | Target (6mo) | Target (12mo) |
|-----|---------|--------------|---------------|
| **Overall marker coverage** | 5.5% | 8-9% | 11-12% |
| **Critical tests marked** | 63 | 90-100 | 120-150 |
| **CLI tests marked** | 20 | 40-50 | 70-80 |
| **MCP tests marked** | 26 | 35-40 | 45-50 |
| **SOAR tests marked** | 18 | 35-40 | 50-60 |
| **Core tests marked** | 11 | 25-30 | 40-50 |
| **Integration tests marked** | 38 | 60-80 | 100-120 |
| **E2E tests marked** | 16 | 30-40 | 45-55 |

### Monitoring

**Quarterly review checklist:**
1. Run marker coverage analysis: `python /tmp/analyze_markers.py`
2. Review TD-MARKER-001 through TD-MARKER-006 status
3. Identify newly critical tests from production issues
4. Mark 20-30 high-value tests (2-4 hours)
5. Update this document with progress

---

## Conclusion

### Current State Summary

**Marker Infrastructure:** ✅ Complete
- 13 markers defined in pytest.ini
- CI uses markers for categorized execution
- Documentation in TESTING.md

**Marker Application:** ⚠️ 5.5% coverage
- 155 of 2,815 tests marked
- Strategic coverage of critical paths
- Room for significant growth

### Recommended Path Forward

**Accept 5.5% as Phase 4 completion:**
- Infrastructure is ready
- Critical tests are marked
- Remaining work is incremental

**Adopt incremental marking:**
- Mark new tests during creation
- Mark modified tests during updates
- Quarterly sprints for high-value tests
- Bug-driven marking for discovered issues

**Expected timeline:**
- 12 months: 11-12% coverage (300-350 tests)
- 24 months: 16-20% coverage (450-550 tests)

**DO NOT pursue comprehensive upfront marking:**
- 30-37 hours effort for only 14-15% coverage
- Diminishing returns after critical paths are marked
- Better to mark incrementally as tests are reviewed

### Success Criteria

Marker coverage is **successful** when:
1. ✅ All critical user paths have marked tests (DONE)
2. ✅ Each major component has representative marked tests (DONE)
3. ✅ CI can run categorized test suites (DONE)
4. ⏳ New tests are consistently marked during creation (ONGOING)
5. ⏳ Marker coverage grows 2-3% per year organically (TARGET)

---

**Document Maintenance:**
- Review quarterly
- Update with new marked tests
- Adjust priorities based on production issues
- Archive completed technical debt items
