# AURORA Technical Debt Tracker

**Last Updated**: December 24, 2025
**Version**: 1.0.0
**Project Phase**: Post-Phase 3 (MVP Complete)

---

## Table of Contents

1. [Overview](#overview)
2. [How to Use This Document](#how-to-use-this-document)
3. [Priority Levels Explained](#priority-levels-explained)
4. [Phase 1: Foundation & Infrastructure](#phase-1-foundation--infrastructure)
5. [Phase 2: SOAR Pipeline & Verification](#phase-2-soar-pipeline--verification)
6. [Phase 3: ACT-R Activation & Semantic Embeddings](#phase-3-act-r-activation--semantic-embeddings)
7. [Cross-Phase Issues](#cross-phase-issues)
8. [Summary Statistics](#summary-statistics)
9. [Recommended Order of Attack](#recommended-order-of-attack)

---

## Overview

### Purpose

This document tracks **technical debt** accumulated during AURORA's MVP development across three phases. Technical debt represents:

- **Code quality issues** that don't block functionality but reduce maintainability
- **Test coverage gaps** that leave code paths untested
- **Missing features** that would improve developer experience
- **Performance optimizations** deferred for future work
- **Documentation gaps** that reduce accessibility
- **Architectural improvements** for long-term sustainability

### Current State

- **MVP Status**: Complete and production-ready (v1.0.0)
- **Test Coverage**: 88.41% (exceeds 85% target)
- **Test Pass Rate**: 100% (1,824/1,824 tests passing)
- **Security**: Zero critical/high vulnerabilities
- **Technical Debt Items**: 47 tracked items
- **Estimated Total Effort**: ~18-22 weeks

### Philosophy

Technical debt is **not failure**—it's a strategic tradeoff made to ship an MVP quickly. This document ensures we:

1. **Track debt consciously** rather than letting it accumulate invisibly
2. **Prioritize systematically** based on impact and risk
3. **Plan incremental paydown** in future sprints
4. **Communicate transparently** with stakeholders

---

## How to Use This Document

### For Developers

1. **Before starting new work**: Check if related debt items exist
2. **When fixing bugs**: Note if the bug relates to tracked debt
3. **During refactoring**: Mark debt items as resolved
4. **In sprint planning**: Use this to identify quick wins

### For Project Managers

1. **Sprint planning**: Allocate 10-20% of sprint capacity to debt paydown
2. **Risk assessment**: High-priority items represent product risk
3. **Roadmap planning**: Schedule debt sprints between feature sprints
4. **Stakeholder communication**: Use Summary Statistics for reporting

### For QA/Test Engineers

1. **Test planning**: Focus on areas with low coverage (see Phase sections)
2. **Bug reporting**: Reference debt items in bug tickets
3. **Test improvement**: Use coverage gaps to guide test authoring

---

## Priority Levels Explained

| Priority | Description | Timeline | Risk Level |
|----------|-------------|----------|------------|
| **P0 - Critical** | Blocks production use, data integrity risk, security vulnerability | Fix immediately | 🔴 HIGH |
| **P1 - High** | Significant impact on reliability, maintainability, or user experience | Next sprint (1-2 weeks) | 🟠 MEDIUM-HIGH |
| **P2 - Medium** | Moderate impact, technical debt that should be addressed soon | Next quarter (3 months) | 🟡 MEDIUM |
| **P3 - Low** | Nice-to-have improvements, polish, minor optimizations | Backlog (6+ months) | 🟢 LOW |

### Effort Estimates

- **XS**: <2 hours (quick fix)
- **S**: 2-8 hours (half-day to full-day)
- **M**: 1-3 days
- **L**: 1-2 weeks
- **XL**: 2+ weeks (requires planning)

---

## Phase 1: Foundation & Infrastructure

**Phase Completed**: December 20, 2025
**Debt Items**: 12 items
**Total Estimated Effort**: 4-6 weeks

---

### P0 - Critical (0 items)

*None* - Phase 1 foundation is stable.

---

### P1 - High Priority (3 items)

#### TD-P1-001: Migration Logic Zero Test Coverage ✅ RESOLVED
**Category**: Test Coverage Gap
**Location**: `packages/core/src/aurora_core/store/migrations.py` (lines 107-151)
**Impact**: Data corruption risk during schema migrations
**Effort**: M (2-3 days) - **ACTUAL: 2-3 days**
**Resolved**: December 24, 2025 (v1.1.0)

**Description**:
Schema migration v1→v2 has **zero test coverage** (30.10% overall file coverage). This migration:
- Adds `access_history` JSON column to activations table
- Adds `first_access` and `last_access` to chunks table
- Migrates existing data with JSON operations
- Uses error suppression (`pass` statements)

**Risk**:
- Bugs discovered only in production during deployments
- Data loss or corruption possible
- Rollback failures untested

**Resolution**:
- ✅ Created `packages/core/tests/store/test_migrations.py` (33 tests, 725 lines)
- ✅ Achieved 94.17% coverage (exceeded 80% target by 14.17%)
- ✅ All migration paths tested (v1→v2, v2→v3)
- ✅ Rollback scenarios tested with constraint violations
- ✅ Edge cases covered (empty data, NULL values, malformed data)
- ✅ Error conditions tested (locked DB, permissions, disk full)
- ✅ Transaction atomicity verified
- ✅ Idempotent migration execution tested

**Acceptance Criteria**:
- [x] Test each migration path (v1→v2, v2→v3)
- [x] Test rollback scenarios
- [x] Test edge cases (empty data, malformed JSON)
- [x] Test error conditions (locked database, insufficient permissions)
- [x] Achieve 80%+ coverage on migrations.py (achieved 94.17%)

**Commit**: `31e048d` - test: add migration and LLM client error path tests (TD-P1-001, TD-P2-001)

---

#### TD-P1-002: Error Handling Rollback Logic Untested
**Category**: Test Coverage Gap
**Location**: `packages/core/src/aurora_core/store/migrations.py` (lines 49-54)
**Impact**: Migration failures may not rollback cleanly
**Effort**: S (4-6 hours)

**Description**:
Error handling for migration failures is untested:
```python
try:
    self.upgrade_fn(conn)
    conn.commit()
except sqlite3.Error as e:
    conn.rollback()
    raise StorageError(...)
```

**Risk**:
- Rollback failures leave database in inconsistent state
- StorageError may not include sufficient debugging info

**Acceptance Criteria**:
- [ ] Test rollback on migration failure
- [ ] Test partial migration cleanup
- [ ] Verify error messages include actionable info
- [ ] Test concurrent migration attempts (locking)

---

#### TD-P1-003: Missing py.typed Markers
**Category**: Type Safety
**Location**: All packages (`packages/*/src/aurora_*/py.typed`)
**Impact**: External type checkers can't validate AURORA usage
**Effort**: XS (1 hour)

**Description**:
PEP 561 `py.typed` marker files are missing from all packages. This prevents external projects from getting type checking benefits when using AURORA as a library.

**Risk**:
- Integration partners get no type safety
- IDE autocomplete less effective
- Harder to catch API misuse

**Acceptance Criteria**:
- [ ] Add empty `py.typed` file to each package
- [ ] Verify mypy recognizes packages as typed
- [ ] Test in external project context
- [ ] Document typing guarantees

**Packages Affected**:
- `packages/core/src/aurora_core/`
- `packages/context-code/src/aurora_context_code/`
- `packages/soar/src/aurora_soar/`
- `packages/reasoning/src/aurora_reasoning/`
- `packages/cli/src/aurora_cli/`

---

### P2 - Medium Priority (6 items)

#### TD-P1-004: MemoryStore Close() Memory Leak (Resolved but Document)
**Category**: Documentation
**Location**: `packages/core/src/aurora_core/store/memory.py`
**Impact**: Low (already fixed, needs documentation)
**Effort**: XS (1 hour)

**Description**:
Python 3.12 introduced WeakValueDictionary behavior change causing test failures. Fixed by implementing proper `close()` that clears references.

**Action Needed**:
- [ ] Document Python 3.12 compatibility notes
- [ ] Add migration guide for Python 3.11→3.12
- [ ] Update testing docs with GC sensitivity notes

**References**:
- Fixed in commit: `075d681`

---

#### TD-P1-005: datetime.utcnow() Deprecation
**Category**: Deprecated API Usage
**Location**: Multiple files using `datetime.utcnow()`
**Impact**: Low (works but deprecated in Python 3.12+)
**Effort**: S (2-4 hours)

**Description**:
Python 3.12 deprecated `datetime.utcnow()` in favor of `datetime.now(timezone.utc)`. We've fixed some instances but should audit entire codebase.

**Action Needed**:
- [ ] Search codebase for remaining `datetime.utcnow()` calls
- [ ] Replace with `datetime.now(timezone.utc)`
- [ ] Add pre-commit hook to prevent reintroduction
- [ ] Update coding standards documentation

**References**:
- Partial fix in commit: `4137173`

---

#### TD-P1-006: SQLite Connection Pooling Not Tested
**Category**: Test Coverage Gap
**Location**: `packages/core/src/aurora_core/store/sqlite.py`
**Impact**: Concurrency issues may be undetected
**Effort**: M (2-3 days)

**Description**:
SQLite connection pooling implementation lacks concurrent access tests. While single-threaded tests pass, multi-threaded behavior is untested.

**Risk**:
- Database locking issues in production
- Connection pool exhaustion
- Transaction isolation violations

**Acceptance Criteria**:
- [ ] Add multi-threaded test suite
- [ ] Test connection pool exhaustion handling
- [ ] Test database locking with concurrent writes
- [ ] Test transaction isolation levels
- [ ] Benchmark connection pool performance

---

#### TD-P1-007: Parser Registry Thread Safety
**Category**: Concurrency
**Location**: `packages/context-code/src/aurora_context_code/registry.py`
**Impact**: Potential race conditions in multi-threaded contexts
**Effort**: M (2-3 days)

**Description**:
ParserRegistry uses a class-level dictionary for parser storage but lacks thread-safe access patterns. Auto-registration during import may have race conditions.

**Risk**:
- Duplicate parser registration
- Missing parsers in concurrent initialization
- Non-deterministic test failures

**Acceptance Criteria**:
- [ ] Add threading locks around registry access
- [ ] Test concurrent parser registration
- [ ] Test concurrent parser lookup
- [ ] Document thread-safety guarantees

---

#### TD-P1-008: CodeChunk Validation Edge Cases
**Category**: Input Validation
**Location**: `packages/core/src/aurora_core/chunks/code_chunk.py`
**Impact**: Invalid chunks may be stored
**Effort**: S (4-6 hours)

**Description**:
CodeChunk validation covers basic cases but misses edge cases:
- Line ranges that span multiple files (copy-paste errors)
- Complexity scores outside 0.0-1.0 range (rounding errors)
- Empty signatures or docstrings (should be None vs empty string)
- File paths with special characters or unicode

**Acceptance Criteria**:
- [ ] Add validation tests for edge cases
- [ ] Normalize empty strings to None
- [ ] Add bounds checking with clear error messages
- [ ] Test unicode handling in file paths

---

#### TD-P1-009: Store Interface Close() Semantics Unclear
**Category**: API Design
**Location**: `packages/core/src/aurora_core/store/base.py`
**Impact**: Resource leaks in long-running processes
**Effort**: S (4-6 hours)

**Description**:
The `close()` method on Store interface doesn't specify:
- Whether it can be called multiple times safely (idempotent?)
- Whether store can be re-opened after close
- What happens to pending transactions
- Whether close() blocks or is async

**Action Needed**:
- [ ] Document close() semantics clearly
- [ ] Add idempotency tests
- [ ] Test close during active transaction
- [ ] Consider context manager support (`with store:`)

---

### P3 - Low Priority (3 items)

#### TD-P1-010: PythonParser Tree-Sitter Error Messages
**Category**: Developer Experience
**Location**: `packages/context-code/src/aurora_context_code/languages/python.py`
**Impact**: Debugging parse failures is difficult
**Effort**: S (4-6 hours)

**Description**:
When tree-sitter parsing fails, error messages are generic. Should include:
- Line number where parse failed
- Character position
- Expected vs actual tokens
- Snippet of surrounding code

**Acceptance Criteria**:
- [ ] Enhance error messages with context
- [ ] Add parse failure test fixtures
- [ ] Create debugging guide for parse errors
- [ ] Consider fallback to regex-based parsing

---

#### TD-P1-011: Query Parsing Stopword List Incomplete
**Category**: Feature Enhancement
**Location**: `packages/core/src/aurora_core/context/code_provider.py`
**Impact**: Minor - query scoring suboptimal
**Effort**: XS (2 hours)

**Description**:
Current stopword list is minimal. Should expand to include common code terms that don't add semantic value.

**Action Needed**:
- [ ] Research programming-specific stopwords
- [ ] A/B test expanded stopword list
- [ ] Make stopword list configurable
- [ ] Document stopword selection criteria

---

#### TD-P1-012: Cache Invalidation Based on mtime Only
**Category**: Feature Enhancement
**Location**: `packages/core/src/aurora_core/context/code_provider.py`
**Impact**: Minor - cache may be stale if mtime unchanged
**Effort**: M (1-2 days)

**Description**:
Cache invalidation uses file modification time only. Should also consider:
- File size changes
- Content hash (for atomic writes that preserve mtime)
- Explicit cache busting API

**Acceptance Criteria**:
- [ ] Add content hash to cache key
- [ ] Test atomic write scenarios
- [ ] Add manual cache clear command
- [ ] Benchmark cache lookup performance

---

## Phase 2: SOAR Pipeline & Verification

**Phase Completed**: December 22, 2025
**Debt Items**: 15 items
**Total Estimated Effort**: 6-8 weeks

---

### P0 - Critical (0 items)

*None* - Phase 2 SOAR pipeline is production-ready.

---

### P1 - High Priority (5 items)

#### TD-P2-001: LLM Client Initialization Error Paths Untested ✅ RESOLVED
**Category**: Test Coverage Gap
**Location**: `packages/reasoning/src/aurora_reasoning/llm_client.py` (lines 192-210)
**Impact**: Runtime failures with confusing error messages
**Effort**: S (6-8 hours) - **ACTUAL: 6-8 hours**
**Resolved**: December 24, 2025 (v1.1.0)

**Description**:
Anthropic API client initialization has **untested error paths** (36.57% file coverage):
- API key validation from environment variable
- Missing `anthropic` package import error
- Rate limiting initialization
- Client instantiation failures

**Risk**:
- Confusing errors when API key missing
- ImportError without actionable guidance
- Rate limiter misconfiguration

**Resolution**:
- ✅ Created `packages/reasoning/tests/test_llm_client_errors.py` (46 tests, 584 lines)
- ✅ Achieved 93.14% coverage (exceeded 70% target by 23.14%)
- ✅ API key validation tested (Anthropic, OpenAI, Ollama formats)
- ✅ Missing dependency errors tested with installation hints
- ✅ Rate limiter initialization tested (100ms Anthropic/OpenAI, 50ms Ollama)
- ✅ Empty/whitespace prompt validation tested
- ✅ Token counting heuristics tested (4 chars per token)
- ✅ JSON extraction from markdown and plain text tested
- ✅ Error wrapping and RuntimeError handling tested

**Acceptance Criteria**:
- [x] Test API key validation (missing, empty, invalid format)
- [x] Test missing anthropic package (import mocking)
- [x] Test rate limiter initialization
- [x] Improve error messages with troubleshooting steps
- [x] Achieve 70%+ coverage on llm_client.py (achieved 93.14%)

**Commit**: `31e048d` - test: add migration and LLM client error path tests (TD-P1-001, TD-P2-001)

---

#### TD-P2-002: JSON Parsing Fallback Logic Untested
**Category**: Test Coverage Gap
**Location**: `packages/reasoning/src/aurora_reasoning/llm_client.py` (lines 152-153)
**Impact**: Malformed LLM responses may cause failures
**Effort**: S (4-6 hours)

**Description**:
JSON extraction tries multiple parsing strategies but fallback logic is untested:
- Code block extraction
- Inline JSON object extraction
- Error recovery

**Risk**:
- Silent failures when LLM returns unexpected format
- No visibility into which parsing strategy succeeded

**Acceptance Criteria**:
- [ ] Test each JSON extraction strategy independently
- [ ] Test fallback order
- [ ] Test complete parsing failure
- [ ] Add logging for which strategy succeeded
- [ ] Create test fixtures with real LLM response formats

---

#### TD-P2-003: SOAR Phase Verification Option B Underdeveloped
**Category**: Feature Completeness
**Location**: `packages/soar/src/aurora_soar/pipeline.py` (Phase 4: Verify)
**Impact**: Complex queries may miss verification issues
**Effort**: L (1-2 weeks)

**Description**:
Verification Option B (adversarial verification) is implemented but lacks:
- Adversarial prompt templates
- Confidence scoring based on adversarial results
- Calibration data for Option B accuracy
- Decision criteria for when to use Option B

**Risk**:
- Option B may not actually improve verification
- No data to justify using Option B vs Option A
- Performance cost without proven benefit

**Acceptance Criteria**:
- [ ] Develop adversarial prompt templates
- [ ] Run calibration study (50+ test cases)
- [ ] Compare Option A vs B accuracy
- [ ] Document decision criteria
- [ ] Add Option B-specific tests

---

#### TD-P2-004: Cost Tracking Granularity Insufficient
**Category**: Observability
**Location**: `packages/reasoning/src/aurora_reasoning/llm_client.py`
**Impact**: Can't optimize costs without detailed tracking
**Effort**: M (2-3 days)

**Description**:
Cost tracking exists but doesn't track:
- Cost per SOAR phase
- Cost per query complexity level
- Cost savings from keyword optimization
- Cost savings from pattern caching

**Action Needed**:
- [ ] Add phase-level cost tracking
- [ ] Track cache hit/miss cost impact
- [ ] Add cost reporting CLI command
- [ ] Create cost optimization dashboard
- [ ] Document cost optimization strategies

**References**:
- See: `docs/guides/COST_TRACKING_GUIDE.md`

---

#### TD-P2-005: Pattern Cache Eviction Strategy Naive
**Category**: Performance
**Location**: `packages/soar/src/aurora_soar/pipeline.py` (Phase 8: Record)
**Impact**: Cache may grow unbounded or evict useful patterns
**Effort**: M (3-5 days)

**Description**:
Pattern cache uses simple timestamp-based eviction but should consider:
- Access frequency (LRU vs LFU)
- Pattern quality scores
- Storage cost vs retrieval benefit
- Adaptive eviction based on hit rate

**Risk**:
- Memory growth in long-running processes
- Evicting high-value patterns
- Cache pollution from one-time queries

**Acceptance Criteria**:
- [ ] Research cache eviction algorithms
- [ ] Implement LRU or adaptive eviction
- [ ] Add cache metrics (hit rate, eviction rate)
- [ ] Benchmark cache effectiveness
- [ ] Make eviction strategy configurable

---

### P2 - Medium Priority (7 items)

#### TD-P2-006: Retry Logic Exponential Backoff Hardcoded
**Category**: Configuration
**Location**: `packages/reasoning/src/aurora_reasoning/llm_client.py`
**Impact**: Can't tune retry behavior for different LLM providers
**Effort**: S (4-6 hours)

**Description**:
Retry intervals are hardcoded (100ms, 200ms, 400ms). Should be configurable per provider.

**Action Needed**:
- [ ] Make retry config provider-specific
- [ ] Support jitter to avoid thundering herd
- [ ] Add max retry time limit
- [ ] Test retry behavior under various error conditions

---

#### TD-P2-007: SOAR Phase Parallel Execution Limited
**Category**: Performance Optimization
**Location**: `packages/soar/src/aurora_soar/pipeline.py` (Phase 6: Collect)
**Impact**: Complex queries slower than necessary
**Effort**: L (1-2 weeks)

**Description**:
Phase 6 executes agents in parallel but:
- No worker pool size tuning
- No backpressure handling
- Sequential fallback not optimized
- No partial result streaming

**Acceptance Criteria**:
- [ ] Add worker pool configuration
- [ ] Implement backpressure handling
- [ ] Optimize sequential execution path
- [ ] Consider streaming partial results
- [ ] Benchmark parallel vs sequential tradeoffs

---

#### TD-P2-008: Verification Calibration Data Limited
**Category**: Data Quality
**Location**: `packages/testing/src/aurora_testing/calibration/`
**Impact**: Verification accuracy may degrade over time
**Effort**: L (1-2 weeks + ongoing)

**Description**:
Calibration tests use 13 test cases. Should expand to:
- 100+ diverse scenarios
- Coverage of all complexity levels
- Real-world query patterns
- Edge cases and adversarial examples

**Action Needed**:
- [ ] Collect real user queries (anonymized)
- [ ] Create calibration test suite generator
- [ ] Add continuous calibration in CI/CD
- [ ] Track verification accuracy over time
- [ ] Document calibration methodology

---

#### TD-P2-009: Agent Capability Registry Static
**Category**: Extensibility
**Location**: `packages/core/src/aurora_core/agent_registry.py`
**Impact**: Adding new agents requires code changes
**Effort**: M (3-5 days)

**Description**:
Agent registry is hardcoded. Should support:
- Dynamic agent registration
- Plugin-based agent loading
- Capability discovery at runtime
- Agent versioning

**Acceptance Criteria**:
- [ ] Design plugin API
- [ ] Implement dynamic registration
- [ ] Add agent discovery mechanism
- [ ] Test plugin loading
- [ ] Document plugin development guide

---

#### TD-P2-010: Decomposition Few-Shot Examples Minimal
**Category**: Prompt Engineering
**Location**: `packages/soar/src/aurora_soar/pipeline.py` (Phase 3: Decompose)
**Impact**: Decomposition quality could be higher
**Effort**: M (3-5 days)

**Description**:
Few-shot examples for subgoal decomposition are minimal. Should:
- Expand to 10+ diverse examples
- Cover different query types
- Include negative examples (bad decompositions)
- Test decomposition quality systematically

**Action Needed**:
- [ ] Collect decomposition examples
- [ ] A/B test prompt variations
- [ ] Create decomposition quality metrics
- [ ] Add decomposition-specific tests
- [ ] Document prompt engineering process

---

#### TD-P2-011: Keyword Assessment Patterns Hardcoded
**Category**: Machine Learning Opportunity
**Location**: `packages/soar/src/aurora_soar/pipeline.py` (Phase 1: Assess)
**Impact**: Keyword optimization effectiveness limited
**Effort**: XL (2-4 weeks)

**Description**:
Keyword patterns are regex-based and hardcoded. Could use ML:
- Train classifier on query complexity
- Learn which queries benefit from LLM
- Adaptive thresholds based on accuracy

**Action Needed**:
- [ ] Collect labeled training data
- [ ] Train query complexity classifier
- [ ] A/B test ML vs regex approach
- [ ] Implement online learning
- [ ] Monitor classification accuracy

---

#### TD-P2-012: Response Formatting Templates Rigid
**Category**: User Experience
**Location**: `packages/soar/src/aurora_soar/pipeline.py` (Phase 9: Respond)
**Impact**: Output format may not suit all use cases
**Effort**: M (2-3 days)

**Description**:
Response formatting has 4 verbosity levels but:
- Templates are hardcoded
- No custom format support
- No structured output (JSON, YAML)
- No internationalization

**Action Needed**:
- [ ] Make templates configurable
- [ ] Add structured output formats
- [ ] Support custom formatters
- [ ] Add template validation
- [ ] Document formatting options

---

#### TD-P2-013: mypy External Library Type Errors
**Category**: Type Safety
**Location**: `packages/reasoning/src/aurora_reasoning/llm_client.py`
**Impact**: Type checking incomplete for external APIs
**Effort**: S (4-6 hours)

**Description**:
6 mypy errors related to external library types (anthropic, openai). We ignore these but should:
- Add type stubs for external libraries
- Contribute stubs upstream
- Document type coverage gaps

**Action Needed**:
- [ ] Create local type stub files
- [ ] Test type stub completeness
- [ ] Contribute to typeshed
- [ ] Document known type gaps

**References**:
- Errors currently ignored in mypy config

---

### P3 - Low Priority (3 items)

#### TD-P2-014: SOAR Pipeline Telemetry Limited
**Category**: Observability
**Location**: All SOAR pipeline phases
**Impact**: Debugging complex failures is difficult
**Effort**: L (1-2 weeks)

**Description**:
Pipeline telemetry tracks basic metrics but lacks:
- Distributed tracing support
- Phase-level spans
- Correlation IDs across phases
- Performance flamegraphs

**Action Needed**:
- [ ] Integrate OpenTelemetry
- [ ] Add tracing to each phase
- [ ] Create observability dashboard
- [ ] Document telemetry best practices

---

#### TD-P2-015: Verification Option Selection Heuristic Simple
**Category**: AI Optimization
**Location**: `packages/soar/src/aurora_soar/pipeline.py` (Phase 4: Verify)
**Impact**: May use wrong verification option
**Effort**: L (1-2 weeks)

**Description**:
Decision to use Option A vs B is based on complexity only. Should consider:
- Historical accuracy of each option
- Query domain/type
- Cost constraints
- Latency requirements

**Action Needed**:
- [ ] Collect option selection data
- [ ] Build decision model
- [ ] A/B test option selection strategies
- [ ] Add option selection metrics
- [ ] Document selection criteria

---

## Phase 3: ACT-R Activation & Semantic Embeddings

**Phase Completed**: December 23, 2025
**Debt Items**: 20 items
**Total Estimated Effort**: 8-10 weeks

---

### P0 - Critical (0 items)

*None* - Phase 3 MVP is production-ready.

---

### P1 - High Priority (6 items)

#### TD-P3-001: Semantic Embedding Provider Coverage Gaps
**Category**: Test Coverage Gap
**Location**: `packages/context-code/src/aurora_context_code/embeddings/`
**Impact**: Embedding failures may go undetected
**Effort**: M (3-5 days)

**Description**:
Semantic embedding modules have limited test coverage:
- `semantic_provider.py`: Untested error paths
- Model loading failures not tested
- Batch embedding edge cases
- Memory cleanup after model unload

**Risk**:
- OOM errors in production
- Model loading failures without fallback
- Inconsistent embedding dimensions

**Acceptance Criteria**:
- [ ] Test model loading failures
- [ ] Test batch size edge cases
- [ ] Test memory cleanup
- [ ] Test dimension mismatch handling
- [ ] Achieve 75%+ coverage on embedding modules

---

#### TD-P3-002: Hybrid Retrieval Precision Under Target
**Category**: Algorithm Quality
**Location**: `packages/context-code/src/aurora_context_code/retrieval/`
**Impact**: Retrieval quality below expectations
**Effort**: L (1-2 weeks)

**Description**:
Hybrid retrieval precision is 20% (target was 25%+). Investigation needed:
- Keyword vs semantic weight tuning
- Query type specific strategies
- Reranking algorithm improvements

**Risk**:
- Users get irrelevant results
- System credibility suffers
- Complex queries fail

**Action Needed**:
- [ ] Analyze false positive patterns
- [ ] Tune keyword/semantic weights
- [ ] Implement query-specific strategies
- [ ] Add reranking stage
- [ ] Run precision benchmark suite

**References**:
- See: `docs/performance/hybrid-retrieval-precision-report.md`

---

#### TD-P3-003: ACT-R Formula Edge Cases Not Validated
**Category**: Correctness
**Location**: `packages/core/src/aurora_core/activation/actr.py`
**Impact**: Memory decay may be incorrect in edge cases
**Effort**: M (2-3 days)

**Description**:
ACT-R activation formula validated against research but edge cases untested:
- Chunks never accessed (activation = -∞?)
- Very old chunks (numeric overflow?)
- Chunks accessed very frequently (activation ceiling?)
- Negative time deltas (clock skew)

**Risk**:
- Incorrect activation scores
- Numeric errors in production
- Memory management failures

**Acceptance Criteria**:
- [ ] Test never-accessed chunks
- [ ] Test numeric overflow/underflow
- [ ] Test extreme access patterns
- [ ] Add bounds checking
- [ ] Document formula limitations

**References**:
- See: `docs/reports/testing/actr-formula-validation.md`

---

#### TD-P3-004: Headless Mode Success Rate at Lower Bound
**Category**: Reliability
**Location**: `packages/cli/src/aurora_cli/headless.py`
**Impact**: Autonomous execution unreliable
**Effort**: L (1-2 weeks)

**Description**:
Headless mode success rate is 80% (exactly at target). Should improve to 90%+:
- Better prompt validation
- Retry logic for transient failures
- Checkpoint/resume support
- Failure analysis

**Risk**:
- Experiments fail overnight
- Loss of compute time
- User frustration

**Action Needed**:
- [ ] Analyze failure patterns
- [ ] Implement retry logic
- [ ] Add checkpoint/resume
- [ ] Improve error recovery
- [ ] Target 90%+ success rate

---

#### TD-P3-005: Memory Profiling Reveals GC Sensitivity
**Category**: Performance Stability
**Location**: Test suite, particularly memory scaling tests
**Impact**: Tests occasionally fail due to GC timing
**Effort**: M (2-3 days)

**Description**:
Memory scaling tests are sensitive to garbage collection timing:
- Tests pass 95% of time
- Fail when GC doesn't run
- Manual `gc.collect()` calls added as workaround

**Risk**:
- Flaky tests reduce CI reliability
- False positive test failures
- Real memory leaks may be hidden

**Action Needed**:
- [ ] Redesign memory tests to be GC-independent
- [ ] Use memory profiling tools (memray, tracemalloc)
- [ ] Set deterministic GC intervals in tests
- [ ] Add memory leak detection tests
- [ ] Document GC sensitivity in test docs

**References**:
- See: `docs/reports/quality/MEMORY_PROFILING_REPORT.md`
- Fixed in commits: `075d681`, `379e998`

---

#### TD-P3-006: Embedding Model Download Not User-Friendly
**Category**: Developer Experience
**Location**: `packages/context-code/src/aurora_context_code/embeddings/`
**Impact**: First-time setup is slow and unclear
**Effort**: M (2-3 days)

**Description**:
When users first run semantic features:
- Large model downloads with no progress indicator
- No cache location documentation
- No offline mode or pre-download script
- Failures don't suggest workarounds

**Action Needed**:
- [ ] Add download progress indicator
- [ ] Document model cache location
- [ ] Create pre-download script
- [ ] Add offline mode with local models
- [ ] Improve error messages

---

### P2 - Medium Priority (9 items)

#### TD-P3-007: sentence-transformers Made Optional for CI
**Category**: Dependency Management
**Location**: `packages/context-code/pyproject.toml`
**Impact**: CI disk usage reduced but semantic features untested in CI
**Effort**: M (2-3 days)

**Description**:
sentence-transformers made optional to reduce CI disk usage, but:
- Semantic embedding tests skipped in CI
- Potential regressions undetected
- Need lightweight test alternative

**Action Needed**:
- [ ] Create mock embedding provider for CI
- [ ] Add smoke tests with mock provider
- [ ] Run full semantic tests in nightly CI
- [ ] Document CI vs full test differences

**References**:
- Changed in commit: `4629d8e`

---

#### TD-P3-008: Activation Decay Parameter Tuning
**Category**: Algorithm Tuning
**Location**: `packages/core/src/aurora_core/activation/actr.py`
**Impact**: Memory behavior may not match user expectations
**Effort**: L (1-2 weeks)

**Description**:
ACT-R decay parameter (d=0.5) uses research default but should:
- Allow user configuration
- Tune based on use case (code vs documentation)
- Provide presets (aggressive, moderate, conservative)

**Action Needed**:
- [ ] Make decay parameter configurable
- [ ] Create parameter tuning guide
- [ ] Add presets for common use cases
- [ ] Benchmark parameter impact
- [ ] Document parameter selection

---

#### TD-P3-009: Headless Mode Budget Exceeded Handling
**Category**: User Experience
**Location**: `packages/cli/src/aurora_cli/headless.py`
**Impact**: Users surprised by abrupt termination
**Effort**: S (4-6 hours)

**Description**:
When budget is exceeded in headless mode:
- Execution stops abruptly
- No partial results saved
- No graceful degradation
- No budget warnings before limit

**Action Needed**:
- [ ] Add budget warning at 80%, 95%
- [ ] Save partial results before termination
- [ ] Add graceful degradation mode
- [ ] Improve budget exceeded error message

---

#### TD-P3-010: CLI Memory Commands Limited
**Category**: Feature Completeness
**Location**: `packages/cli/src/aurora_cli/commands/memory.py`
**Impact**: Users can't fully inspect/debug memory
**Effort**: M (3-5 days)

**Description**:
Memory CLI commands exist but lack:
- Visual memory map
- Activation history over time
- Memory statistics (avg activation, decay rate)
- Export to analysis tools

**Action Needed**:
- [ ] Add `memory map` command with visualization
- [ ] Add `memory stats` command
- [ ] Add `memory history` command
- [ ] Add export to CSV/JSON
- [ ] Document memory inspection workflow

---

#### TD-P3-011: Performance Tuning Guide Needs More Examples
**Category**: Documentation
**Location**: `docs/guides/performance-tuning.md`
**Impact**: Users can't optimize without examples
**Effort**: S (6-8 hours)

**Description**:
Performance tuning guide has theory but needs:
- Real-world tuning examples
- Before/after benchmarks
- Common performance issues
- Troubleshooting decision tree

**Action Needed**:
- [ ] Add 5+ tuning case studies
- [ ] Include benchmark results
- [ ] Create troubleshooting flowchart
- [ ] Add performance checklist

---

#### TD-P3-012: Embedding Benchmark Results Not Actionable
**Category**: Documentation
**Location**: `docs/performance/embedding-benchmark-results.md`
**Impact**: Users don't know how to interpret results
**Effort**: S (4-6 hours)

**Description**:
Benchmark results report numbers but don't explain:
- What latency is acceptable
- When to use which model
- Tradeoffs between models
- How to reproduce benchmarks

**Action Needed**:
- [ ] Add interpretation guide
- [ ] Create model selection decision tree
- [ ] Document tradeoff analysis
- [ ] Add reproduction instructions

---

#### TD-P3-013: Production Deployment Guide Incomplete
**Category**: Documentation
**Location**: `docs/deployment/production-deployment.md`
**Impact**: Production deployments may miss best practices
**Effort**: M (1-2 days)

**Description**:
Deployment guide missing:
- Kubernetes/Docker examples
- Monitoring setup
- Scaling recommendations
- Disaster recovery

**Action Needed**:
- [ ] Add container deployment examples
- [ ] Document monitoring setup
- [ ] Add scaling guidelines
- [ ] Create DR procedures

---

#### TD-P3-014: Error Recovery Rate Below Stretch Goal
**Category**: Reliability
**Location**: Cross-cutting error handling
**Impact**: Some errors not recoverable
**Effort**: L (1-2 weeks)

**Description**:
Error recovery rate is 96.8% (exceeds 95% requirement but below 99% stretch goal). Common failure scenarios:
- Network timeouts
- Malformed LLM responses
- Database locking

**Action Needed**:
- [ ] Analyze unrecovered error patterns
- [ ] Add recovery strategies for common failures
- [ ] Implement circuit breaker pattern
- [ ] Add retry with backoff universally
- [ ] Target 99% recovery rate

---

#### TD-P3-015: Cache Hit Rate Below Expectations
**Category**: Performance
**Location**: Pattern cache, semantic cache
**Impact**: More LLM calls than necessary
**Effort**: M (3-5 days)

**Description**:
Cache hit rate is 34% (exceeds 30% target but expected 40%+). Investigation shows:
- Query variations not matched (synonyms, paraphrasing)
- Semantic similarity threshold too strict
- Cache key generation too specific

**Action Needed**:
- [ ] Tune semantic similarity threshold
- [ ] Implement query normalization
- [ ] Add fuzzy cache key matching
- [ ] Benchmark cache effectiveness
- [ ] Target 45%+ hit rate

---

### P3 - Low Priority (5 items)

#### TD-P3-016: Headless Mode Prompt Validation Minimal
**Category**: Input Validation
**Location**: `packages/cli/src/aurora_cli/headless.py`
**Impact**: Poor prompts lead to failures
**Effort**: M (2-3 days)

**Description**:
Prompt validation checks basic structure but could:
- Suggest improvements to prompts
- Validate success criteria are measurable
- Check budget allocation is reasonable
- Warn about common pitfalls

**Action Needed**:
- [ ] Add prompt linting
- [ ] Create prompt best practices guide
- [ ] Add prompt examples
- [ ] Implement prompt suggestions

---

#### TD-P3-017: Activation Usage Guide Needs Jupyter Notebooks
**Category**: Documentation
**Location**: `docs/examples/activation_usage.md`
**Impact**: Learning curve for memory features
**Effort**: M (1-2 days)

**Description**:
Activation usage guide has code examples but would benefit from:
- Interactive Jupyter notebooks
- Visualizations of memory decay
- Step-by-step tutorials
- Comparison with traditional caching

**Action Needed**:
- [ ] Create Jupyter notebook tutorials
- [ ] Add memory visualization notebooks
- [ ] Create interactive examples
- [ ] Publish to documentation site

---

#### TD-P3-018: Troubleshooting Guide Needs Search Index
**Category**: Documentation
**Location**: `docs/guides/TROUBLESHOOTING.md`
**Impact**: Finding solutions is difficult
**Effort**: S (4-6 hours)

**Description**:
Troubleshooting guide is comprehensive but:
- No search functionality
- No error code index
- No symptom-based navigation
- No related issues links

**Action Needed**:
- [ ] Add error code index
- [ ] Create symptom decision tree
- [ ] Link to related GitHub issues
- [ ] Add search keywords

---

#### TD-P3-019: API Contracts Need Stability Guarantees
**Category**: API Design
**Location**: `docs/architecture/API_CONTRACTS_v1.0.md`
**Impact**: Breaking changes may surprise users
**Effort**: S (4-6 hours)

**Description**:
API contracts documented but need:
- Semantic versioning policy
- Deprecation timeline
- Breaking change notification
- Compatibility matrix

**Action Needed**:
- [ ] Define versioning policy
- [ ] Document deprecation process
- [ ] Create compatibility matrix
- [ ] Add API stability badges

---

#### TD-P3-020: Security Audit Checklist Not Comprehensive
**Category**: Security
**Location**: `docs/reports/security/SECURITY_AUDIT_CHECKLIST.md`
**Impact**: May miss security issues
**Effort**: M (2-3 days)

**Description**:
Security checklist covers basics but should add:
- Dependency vulnerability scanning (Snyk, Dependabot)
- Secrets scanning (TruffleHog)
- SAST integration (Semgrep)
- Regular penetration testing

**Action Needed**:
- [ ] Integrate automated security scanning
- [ ] Add secrets detection to CI
- [ ] Schedule regular security audits
- [ ] Document security incident response

---

#### TD-P3-021: MCP Control Script Features Not Implemented
**Category**: Feature Completeness
**Location**: `scripts/aurora-mcp` (Task 3.13.10)
**Impact**: MCP debugging and validation features missing
**Effort**: S (8-12 hours total)

**Description**:
Two test cases in Phase 3.13.10 are skipped due to unimplemented features:
1. **Log display** (test_status_shows_recent_logs): Status command shows logs but lacks filtering, streaming, rotation
2. **Config validation** (test_control_script_validates_config): No explicit validation on config save

**Action Needed**:
- [ ] Implement log filtering by severity level
- [ ] Add log streaming (--follow flag)
- [ ] Implement log rotation handling
- [ ] Add config schema validation on save
- [ ] Add --validate-only flag for config checking
- [ ] Validate paths are writable/readable
- [ ] Bounds check max_results (1-1000)

**Test Status**: 7/9 tests passing, 2 legitimately skipped
**References**: `/home/hamr/PycharmProjects/aurora/tasks/tasks-0006-prd-cli-fixes-package-consolidation-mcp.md` (Task 3.13.10)

---

## Phase 4: MCP Integration & aurora_query

**Phase Completed**: December 26, 2025
**Debt Items**: 10 items
**Total Estimated Effort**: 2-3 weeks

---

### P0 - Critical (0 items)

*None* - MCP integration is production-ready.

---

### P1 - High Priority (1 item)

#### TD-MCP-001: MCP Server Subprocess Timeout in Integration Tests
**Category**: Test Infrastructure
**Location**: `tests/integration/test_mcp_python_client.py::TestMCPServer` (6 failing tests)
**Impact**: CI/CD unreliable, integration tests fail intermittently
**Effort**: M (2-3 days)

**Description**:
MCP server integration tests timeout after 10 seconds when running in `--test` mode:
- `test_server_lists_all_tools`
- `test_server_accepts_custom_db_path`
- `test_server_accepts_custom_config`
- `test_server_handles_invalid_db_path`
- `test_server_handles_corrupted_config`
- `test_server_creates_directories`

**Root Cause**:
Server initialization blocks on heavy imports during subprocess startup:
1. **FastMCP import**: Triggers pydantic model validation
2. **EmbeddingProvider initialization**: May attempt to download sentence-transformers model (~500MB)
3. **Registry setup**: Tree-sitter grammar loading
4. **SQLite migrations**: Database schema checks on cold start

**Current Workaround**: Tests skip `fastmcp` import with `test_mode=True`, but subprocess tests spawn full server process.

**Risk**:
- CI/CD fails unpredictably (false negatives)
- Developers lose trust in test suite
- Real MCP server issues may be masked
- Claude Code CLI users experience slow initial connection

**Acceptance Criteria**:
- [ ] Add lazy initialization to MCP server (defer heavy imports until first tool call)
- [ ] Mock sentence-transformers in test environment
- [ ] Add startup health check with progressive timeout (5s → 10s → 20s)
- [ ] Implement `--fast-start` mode that skips ML model loading
- [ ] Test MCP server startup in CI with timeout monitoring
- [ ] Document expected startup time (cold: 3-5s, warm: <1s)

**References**:
- Test output: `/tmp/claude/-home-hamr-PycharmProjects-aurora/tasks/b5b0ae9.output` (lines 92-98)
- Related: TD-P3-006 (Embedding model download UX)

---

### P2 - Medium Priority (6 items)

#### TD-MCP-002: Embedding Performance Test Threshold Too Strict for CI
**Category**: Test Configuration
**Location**: `tests/performance/test_embedding_benchmarks.py::test_embed_chunk_long_text_performance`
**Impact**: Flaky performance tests, false CI failures
**Effort**: S (4-6 hours)

**Description**:
Embedding performance test fails with P95 latency of 1075ms vs 200ms threshold (5.4x over budget).

**Root Cause**:
1. **Cold model loading**: First embedding call loads ~500MB model into memory (takes 500-700ms)
2. **CPU vs GPU**: CI environment has no GPU; CPU inference is 3-5x slower
3. **Long text processing**: Test uses 2000-character chunks requiring multiple tokenizer passes
4. **No warmup phase**: Test measures cold start latency, not steady-state performance

**Actual Production Performance**:
- First query: ~1000ms (model loading)
- Subsequent queries: 50-100ms (acceptable)
- GPU environments: 20-30ms (excellent)

**Risk**:
- Developers ignore performance regressions (test is always failing)
- Real performance issues masked by flaky threshold
- CI time wasted re-running flaky tests

**Acceptance Criteria**:
- [ ] Separate cold start and warm performance tests
- [ ] Set environment-specific thresholds (CPU: 1000ms, GPU: 200ms)
- [ ] Add warmup phase (3 embedding calls before measurement)
- [ ] Skip performance tests in CI (run in nightly or manually)
- [ ] Add performance tracking dashboard (track trends, not absolute values)
- [ ] Document expected latency by environment and text length

**References**:
- Test failure: `AssertionError: P95 time 1075.89ms exceeds 200ms threshold for long text`
- Related: TD-P3-006 (Embedding model download UX)

---

#### TD-MCP-003: aurora_query Error Recovery Coverage Gaps
**Category**: Reliability
**Location**: `src/aurora/mcp/tools.py::aurora_query` (lines 440-510)
**Impact**: Some queries may fail unnecessarily due to transient errors
**Effort**: M (2-3 days)

**Description**:
While `aurora_query` implements retry logic (`_execute_with_retry()`) and graceful degradation, edge cases remain untested:

1. **API Key Rotation Mid-Execution**: No handling if API key expires between assess and execute phases
2. **Heuristic Transient Detection**: `_is_transient_error()` uses pattern matching on error messages (fragile)
3. **No Circuit Breaker**: Repeated failures don't trigger circuit breaker (wastes retries)
4. **Fallback Path Untested**: Graceful degradation from SOAR → Direct LLM lacks integration tests

**Risk**:
- Users experience unnecessary query failures
- Budget wasted on doomed retries
- No visibility into retry effectiveness
- Complex queries fail when direct LLM would succeed

**Acceptance Criteria**:
- [ ] Add integration test for API key expiry mid-query
- [ ] Implement circuit breaker (3 failures → open for 60s)
- [ ] Replace heuristic error detection with error type checking
- [ ] Add integration test for SOAR → Direct LLM fallback
- [ ] Add retry metrics (success rate, avg retries per query)
- [ ] Document retry behavior and fallback logic in MCP_SETUP.md

**Example Untested Scenarios**:
```python
# Scenario 1: API key expires after assess phase
assess_complexity()  # Succeeds with old key
execute_soar()       # Fails with 401 Unauthorized

# Scenario 2: Memory DB locked during SOAR
execute_soar()       # Fails: database is locked
# Should fallback to direct LLM (no memory needed)

# Scenario 3: Rate limit exceeded
execute_direct_llm() # Fails: RateLimitError
# Should exponentially backoff, not retry immediately
```

**References**:
- Implementation: `src/aurora/mcp/tools.py` (lines 749-787, 789-822)

---

#### TD-MCP-004: Claude Code CLI Environment Variable Injection Undocumented
**Category**: Documentation
**Location**: `docs/MCP_SETUP.md` (Configuration section)
**Impact**: Users unaware of critical configuration options
**Effort**: S (2-3 hours)

**Description**:
Claude Code CLI MCP configuration supports environment variable injection, but documentation only shows `AURORA_DB_PATH`. Key undocumented variables:

1. **ANTHROPIC_API_KEY**: Required for `aurora_query` tool (not mentioned in setup guide)
2. **PYTHONPATH**: May be needed if aurora installed in non-standard location
3. **AURORA_CONFIG_PATH**: Override default config file location
4. **AURORA_LOG_LEVEL**: Control logging verbosity (DEBUG, INFO, WARNING, ERROR)

**Current Documentation Gap**:
```json
{
  "mcpServers": {
    "aurora": {
      "command": "python3",
      "args": ["-m", "aurora.mcp.server"],
      "env": {
        "AURORA_DB_PATH": "/home/user/.aurora/memory.db"
        // Missing: ANTHROPIC_API_KEY, PYTHONPATH, etc.
      }
    }
  }
}
```

**Risk**:
- Users try `aurora_query` but get "API key missing" errors
- Installation issues due to missing PYTHONPATH
- No way to debug MCP server issues (logging not documented)
- Confusion about config file priority (env vars vs config.json)

**Acceptance Criteria**:
- [ ] Document all supported environment variables in MCP_SETUP.md
- [ ] Add example with ANTHROPIC_API_KEY for aurora_query
- [ ] Document config priority: env vars > config file > defaults
- [ ] Add troubleshooting section for common env var issues
- [ ] Create config validation command: `aurora-mcp validate`

**Recommended Documentation Addition**:
```json
{
  "mcpServers": {
    "aurora": {
      "command": "python3",
      "args": ["-m", "aurora.mcp.server"],
      "env": {
        // Required: Database path
        "AURORA_DB_PATH": "/home/user/.aurora/memory.db",

        // Required for aurora_query tool
        "ANTHROPIC_API_KEY": "sk-ant-...",

        // Optional: Custom config file
        "AURORA_CONFIG_PATH": "/home/user/.aurora/config.json",

        // Optional: Logging verbosity (DEBUG, INFO, WARNING, ERROR)
        "AURORA_LOG_LEVEL": "INFO",

        // Optional: Python path (if aurora not in system path)
        "PYTHONPATH": "/path/to/aurora/packages"
      }
    }
  }
}
```

**References**:
- Current docs: `docs/MCP_SETUP.md` (lines 118-133, 160-176)
- API key check: `src/aurora/mcp/tools.py` (lines 617-637)

---

#### TD-MCP-005: MCP Tool Registration Error Messages Not User-Friendly
**Category**: Developer Experience
**Location**: `src/aurora/mcp/server.py::_register_tools()` (lines 52-172)
**Impact**: Difficult to debug Claude Code CLI connection issues
**Effort**: S (4-6 hours)

**Description**:
When MCP server fails to register tools with Claude Code CLI, error messages are generic:

1. **FastMCP Import Error**: Shows "Error: FastMCP not installed" but doesn't explain that Claude Code CLI needs to install it
2. **Tool Registration Failure**: No visibility into which tool failed to register
3. **Silent Failures**: Some registration errors are swallowed by FastMCP
4. **No Startup Validation**: Server doesn't verify all tools registered successfully

**Current Error Message**:
```python
except ImportError:
    print("Error: FastMCP not installed. Install with: pip install fastmcp", file=sys.stderr)
    sys.exit(1)
```

**Issue**: This message assumes user controls the Python environment, but Claude Code CLI manages it.

**Risk**:
- Users see "tool not found" in Claude Code CLI with no explanation
- Debugging requires diving into Claude Code CLI logs
- No way to verify MCP server health from Claude Code CLI
- Users don't know if issue is AURORA or Claude Code CLI

**Acceptance Criteria**:
- [ ] Add detailed error messages for each failure mode
- [ ] Create MCP server health check command: `aurora-mcp doctor`
- [ ] Log all tool registrations with success/failure status
- [ ] Add startup validation that reports missing tools
- [ ] Improve FastMCP import error with Claude Code CLI context
- [ ] Document how to check Claude Code CLI logs for MCP errors

**Recommended Error Messages**:
```python
# Import Error
"""
Error: FastMCP not installed in Claude Code CLI's Python environment.

This is expected if you're running the MCP server directly.
Claude Code CLI manages its own Python environment and installs dependencies automatically.

If you see this error in Claude Code CLI:
1. Check Claude Code CLI logs: ~/Library/Logs/Claude/mcp.log (macOS)
2. Verify claude_desktop_config.json is correct
3. Restart Claude Code CLI
4. Contact support if issue persists

For manual testing, install FastMCP:
  pip install fastmcp
"""

# Registration Error
"""
Error: Failed to register tool 'aurora_query'
Reason: Missing dependency 'anthropic'

To fix:
1. Set ANTHROPIC_API_KEY environment variable in claude_desktop_config.json
2. Or disable aurora_query by commenting it out in config
3. Other tools will continue working

See: docs/MCP_SETUP.md#aurora_query-setup
"""
```

**References**:
- Implementation: `src/aurora/mcp/server.py` (lines 14-18)
- Related: TD-MCP-004 (environment variable docs)

---

#### TD-MCP-006: E2E Test Coverage Limited by API Key Requirement
**Category**: Test Coverage Gap
**Location**: `tests/e2e/test_aurora_query_e2e.py` (7 tests, all skipped)
**Impact**: Real-world MCP usage patterns untested in CI
**Effort**: M (2-3 days)

**Description**:
E2E tests for `aurora_query` are comprehensive but skipped in CI due to missing `ANTHROPIC_API_KEY`:
- `test_simple_query_direct_llm_e2e`
- `test_complex_query_soar_pipeline_e2e`
- `test_query_with_memory_integration_e2e`
- `test_query_budget_enforcement_e2e`
- `test_query_error_handling_e2e`
- `test_query_verbose_mode_e2e`
- `test_query_performance_benchmark_e2e`

**Current State**:
```python
@pytest.mark.skipif(
    os.getenv("ANTHROPIC_API_KEY") is None,
    reason="ANTHROPIC_API_KEY environment variable not set"
)
```

**Issues**:
1. **No CI Coverage**: E2E tests never run in CI (only run manually)
2. **No Mock Alternative**: No way to test E2E flow without real API
3. **Performance Benchmarks Skipped**: Can't track aurora_query latency trends
4. **Integration Regressions Possible**: Changes may break real usage without detection

**Risk**:
- Real-world bugs slip through (only found by users)
- Performance regressions undetected
- No validation of Claude Code CLI integration
- Can't reproduce user-reported issues in test environment

**Acceptance Criteria**:
- [ ] Add nightly E2E CI job with API key secret (GitHub Actions)
- [ ] Create mock LLM provider for E2E testing (no API cost)
- [ ] Run performance E2E tests monthly, track latency trends
- [ ] Add smoke test that validates MCP server in Claude Code CLI context
- [ ] Document E2E test execution for contributors
- [ ] Set up performance tracking dashboard (Grafana/Datadog)

**Recommended Approach**:
```yaml
# .github/workflows/nightly-e2e.yml
name: Nightly E2E Tests
on:
  schedule:
    - cron: '0 2 * * *'  # 2am UTC daily
  workflow_dispatch:      # Manual trigger

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run E2E Tests
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          AURORA_E2E_BUDGET: 1.00  # $1 daily budget
        run: |
          pytest tests/e2e/ -v --tb=short

      - name: Report Performance
        run: |
          # Extract latency metrics, post to dashboard
          python scripts/report_e2e_metrics.py
```

**Cost Management**:
- Daily budget: $1 (10-20 queries at $0.05-0.10 each)
- Monthly cost: ~$30
- Performance tracking: Priceless 😊

**References**:
- E2E tests: `tests/e2e/test_aurora_query_e2e.py` (201 lines)
- Test output: Line 72-78 showing 7 skipped tests

---

#### TD-MCP-007: Budget Enforcement Edge Cases Untested
**Category**: Test Coverage Gap
**Location**: `src/aurora/mcp/tools.py::_check_budget()` (lines 641-683)
**Impact**: Budget may be exceeded slightly in edge cases
**Effort**: S (4-6 hours)

**Description**:
Budget checking is implemented but edge cases lack test coverage:

1. **Budget Exceeded Mid-Query**: Budget OK at start, exceeded during SOAR execution
2. **Concurrent Queries**: Multiple MCP tools running simultaneously (race condition)
3. **Budget File Locking**: What happens if budget tracker locked by another process?
4. **Negative Budget**: Misconfiguration allows negative budget values
5. **Monthly Rollover**: Budget resets monthly, but rollover timing untested
6. **Budget Warning Thresholds**: No warnings at 80%, 95% budget consumption

**Current Implementation**:
```python
def _check_budget(self, config: dict[str, Any]) -> tuple[bool, str | None]:
    """Check if query execution would exceed budget."""
    # Basic check: total spent < monthly limit
    # Missing: mid-query checks, warnings, concurrent access
```

**Risk**:
- Users surprised by budget overruns
- No warnings before hitting limit
- Race conditions in concurrent usage
- Budget tracker file corruption

**Acceptance Criteria**:
- [ ] Add unit tests for budget edge cases
- [ ] Test concurrent budget access (file locking)
- [ ] Implement budget warning thresholds (80%, 95%)
- [ ] Add mid-query budget checks (between SOAR phases)
- [ ] Test monthly rollover logic
- [ ] Add budget validation (prevent negative values)
- [ ] Document budget enforcement timing in MCP_SETUP.md

**Example Edge Case Tests**:
```python
def test_budget_exceeded_mid_query():
    """Test budget check between assess and execute phases."""
    # Budget: $10, Spent: $9.50
    # Assess: $0.10 (total: $9.60, under budget)
    # Execute: $0.50 (would exceed $10.00)
    # Expected: Fail after assess, before execute

def test_concurrent_budget_updates():
    """Test multiple MCP tools updating budget simultaneously."""
    # Spawn 3 aurora_query calls in parallel
    # Each costs $0.50, budget is $1.00
    # Expected: Only 2 succeed, 1 fails with budget exceeded

def test_budget_warning_thresholds():
    """Test warnings at 80% and 95% budget consumption."""
    # Budget: $10, Spent: $8.00
    # Expected: Warning in response: "80% of monthly budget used"
```

**References**:
- Implementation: `src/aurora/mcp/tools.py` (lines 641-683)
- Related: `packages/core/src/aurora_core/tracking/budget_tracker.py`

---

### P3 - Low Priority (3 items)

#### TD-MCP-008: Progress Tracking Verbosity Levels Overlapping
**Category**: User Experience
**Location**: `src/aurora/mcp/tools.py::aurora_query` (verbosity parameter)
**Impact**: Minor - verbosity levels may not provide distinct value
**Effort**: S (4-6 hours)

**Description**:
Three verbosity levels implemented but distinctions are subtle:

1. **minimal**: Shows final answer only (good for simple queries)
2. **verbose**: Shows phase transitions, key decisions (recommended default)
3. **detailed**: Shows full execution trace, all intermediate results (debugging)

**Issue**: "verbose" and "detailed" modes overlap significantly (80%+ same information).

**User Feedback Needed**:
- Is "minimal" too sparse for debugging failed queries?
- Is "detailed" overwhelming for most users?
- Should we add "progress" mode with real-time phase updates?

**Risk**:
- Users confused about which verbosity to use
- "detailed" mode generates excessive output (Claude Code CLI chat clutter)
- No streaming progress (only see results after completion)

**Acceptance Criteria**:
- [ ] Gather user feedback on verbosity levels (5-10 users)
- [ ] Create comparison matrix of what each level shows
- [ ] Consider streaming progress updates (MCP progress notifications)
- [ ] Add verbosity recommendations to MCP_SETUP.md
- [ ] Add examples of each level's output to docs

**Potential Improvements**:
```python
# Option 1: Streaming progress (requires MCP extension)
@mcp.tool(supports_progress=True)
def aurora_query(...) -> Generator[ProgressUpdate, None, str]:
    yield {"phase": "assess", "progress": 0.1}
    yield {"phase": "retrieve", "progress": 0.3}
    # ...

# Option 2: Restructure levels
# - silent: No output, just answer
# - normal: Phase transitions only (current "verbose")
# - debug: Full trace (current "detailed")
```

**References**:
- Implementation: `src/aurora/mcp/tools.py` (lines 888-927, 928-980, 981-1030)
- Task: `tasks/tasks-0007-tasklist-mcp-aurora-query.md` (Task 2.0)

---

#### TD-MCP-009: Configuration Priority Not Well Documented
**Category**: Documentation
**Location**: `src/aurora/mcp/tools.py::_load_config()` (lines 556-615)
**Impact**: User confusion about configuration precedence
**Effort**: XS (2 hours)

**Description**:
Configuration loading implements 3-tier priority but lacks documentation:

**Priority Order** (highest to lowest):
1. Environment variables (`ANTHROPIC_API_KEY`)
2. Config file (`~/.aurora/config.json`)
3. Hard-coded defaults

**Issue**: Users don't know which env vars are checked, what config file keys exist, or what defaults are.

**Example Confusion**:
```bash
# User sets API key in config.json
echo '{"api": {"anthropic_key": "sk-ant-..."}}' > ~/.aurora/config.json

# But also has env var set (takes precedence!)
export ANTHROPIC_API_KEY="sk-ant-OLD-KEY"

# Query uses OLD key, user confused why config.json ignored
aur query "test"
```

**Risk**:
- Users set config in wrong place
- Env vars override config unexpectedly
- No way to debug config loading
- Can't validate config without running query

**Acceptance Criteria**:
- [ ] Document all env vars checked (ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.)
- [ ] Document config.json structure and all keys
- [ ] Add configuration priority section to MCP_SETUP.md
- [ ] Create config validation command: `aurora-mcp config --validate`
- [ ] Add config debugging command: `aurora-mcp config --show-effective`

**Recommended Documentation Addition** (MCP_SETUP.md):
```markdown
## Configuration Priority

AURORA uses a 3-tier configuration system:

1. **Environment Variables** (highest priority)
   - `ANTHROPIC_API_KEY` - Anthropic API key for aurora_query
   - `OPENAI_API_KEY` - OpenAI API key (alternative)
   - `AURORA_DB_PATH` - Database location (default: ~/.aurora/memory.db)
   - `AURORA_CONFIG_PATH` - Config file location (default: ~/.aurora/config.json)

2. **Config File** (`~/.aurora/config.json`)
   ```json
   {
     "api": {
       "anthropic_key": "sk-ant-...",
       "default_model": "claude-sonnet-4-20250514",
       "temperature": 0.7,
       "max_tokens": 4000
     },
     "query": {
       "auto_escalate": true,
       "complexity_threshold": 0.6,
       "verbosity": "verbose"
     },
     "budget": {
       "monthly_limit_usd": 50.0
     }
   }
   ```

3. **Hard-coded Defaults** (lowest priority)

### Debugging Configuration

Check effective configuration:
```bash
aurora-mcp config --show-effective
```

Validate configuration:
```bash
aurora-mcp config --validate
```
```

**References**:
- Implementation: `src/aurora/mcp/tools.py` (lines 556-615)
- Related: TD-MCP-004 (env var documentation)

---

#### TD-MCP-010: MCP Server Startup Health Check Missing
**Category**: Observability
**Location**: `src/aurora/mcp/server.py::main()` (lines 202-245)
**Impact**: Difficult to diagnose Claude Code CLI connection issues
**Effort**: M (1-2 days)

**Description**:
MCP server starts but doesn't validate it's ready to serve requests:

**Missing Checks**:
1. **Database Reachable**: Can connect to SQLite database?
2. **Required Tools Available**: Are all 6 tools registered?
3. **Dependencies Loaded**: Is sentence-transformers available (for semantic search)?
4. **API Key Present**: Is ANTHROPIC_API_KEY set (for aurora_query)?
5. **Permissions Valid**: Can write to log files?

**Current Startup**:
```python
def main():
    server = AuroraMCPServer(...)
    print("Starting AURORA MCP Server...")
    server.run()  # No health check!
```

**Issue**: Server may start successfully but fail first request due to missing dependency or config issue.

**Risk**:
- Claude Code CLI shows "tool failed" with no context
- Users don't know if issue is AURORA or Claude Code CLI
- No way to pre-flight check configuration
- Debugging requires checking Claude Code CLI logs

**Acceptance Criteria**:
- [ ] Add health check on startup (before `server.run()`)
- [ ] Validate database connection, log file permissions
- [ ] Check optional dependencies (report missing but don't fail)
- [ ] Add `aurora-mcp doctor` command for pre-flight checks
- [ ] Log health check results to MCP log file
- [ ] Document health check output in troubleshooting guide

**Recommended Implementation**:
```python
def health_check(self) -> dict[str, Any]:
    """Run pre-flight health checks."""
    results = {
        "database": self._check_database(),
        "tools": self._check_tools_registered(),
        "dependencies": self._check_dependencies(),
        "api_keys": self._check_api_keys(),
        "permissions": self._check_permissions()
    }

    # Log results
    logger.info(f"Health check: {results}")

    # Warn on non-critical failures
    for check, status in results.items():
        if not status["ok"] and not status["critical"]:
            logger.warning(f"{check} check failed: {status['message']}")

    return results

def main():
    server = AuroraMCPServer(...)

    # Run health check
    health = server.health_check()

    # Fail on critical issues
    critical_failures = [
        check for check, status in health.items()
        if not status["ok"] and status["critical"]
    ]

    if critical_failures:
        print(f"Critical health check failures: {critical_failures}")
        sys.exit(1)

    print("Starting AURORA MCP Server...")
    server.run()
```

**Command Line Interface**:
```bash
# Pre-flight check (doesn't start server)
aurora-mcp doctor

# Output:
✓ Database: Connected (/home/user/.aurora/memory.db, 1,234 chunks)
✓ Tools: 6/6 registered
⚠ Dependencies: sentence-transformers not found (semantic search disabled)
✓ API Keys: ANTHROPIC_API_KEY present
✓ Permissions: Log file writable
✗ Config: Invalid temperature value: 1.5 (must be 0.0-1.0)

Result: 1 error, 1 warning
Fix errors before starting MCP server.
```

**References**:
- Implementation: `src/aurora/mcp/server.py` (lines 202-245)
- Related: TD-MCP-005 (error messages), TD-MCP-004 (env vars)

---

## Cross-Phase Issues

**Items**: 8 issues affecting multiple phases
**Total Estimated Effort**: 4-6 weeks

---

### P1 - High Priority (3 items)

#### TD-X-001: Type Checking Incomplete Across Codebase
**Category**: Type Safety
**Location**: All packages
**Impact**: Runtime type errors possible
**Effort**: L (1-2 weeks)

**Description**:
While mypy passes with ~95% coverage, issues remain:
- External library type stubs missing
- Some `Any` types used where specific types better
- Generic types not fully specified
- Protocol definitions could be stricter

**Action Needed**:
- [ ] Audit all `Any` type usages
- [ ] Add type stubs for external libraries
- [ ] Strengthen protocol definitions
- [ ] Enable stricter mypy checks
- [ ] Add type checking to pre-commit hooks

**References**:
- Fixed many errors in commits: `7fc58c5`, `56176f4`, `133e4f4`

---

#### TD-X-002: Test Discovery Flakiness on CI
**Category**: CI/CD
**Location**: Test suite configuration
**Impact**: CI failures unrelated to code changes
**Effort**: M (3-5 days)

**Description**:
Test discovery occasionally fails in CI due to:
- Package installation order
- Import side effects
- Pytest collection caching
- Path resolution issues

**Risk**:
- Developers lose trust in CI
- Real failures dismissed as flaky
- Merge delays

**Action Needed**:
- [ ] Audit import side effects
- [ ] Fix package installation order
- [ ] Add test isolation verification
- [ ] Document CI troubleshooting
- [ ] Add CI health monitoring

**References**:
- Fixed in commits: `000cace`, `3106bd3`

---

#### TD-X-003: Linting Configuration Too Strict/Lenient Tradeoffs
**Category**: Code Quality
**Location**: `ruff.toml`, `.flake8`, etc.
**Impact**: Code quality vs developer experience balance
**Effort**: M (2-3 days)

**Description**:
Linting configuration has been adjusted multiple times:
- Initially too strict (1000+ violations)
- Relaxed rules to ship faster
- Need systematic review of what should be strict

**Action Needed**:
- [ ] Review all disabled rules
- [ ] Re-enable rules incrementally
- [ ] Create linting policy document
- [ ] Add linting to pre-commit hooks
- [ ] Balance strictness vs pragmatism

**References**:
- Multiple adjustments in commits: `6cbd322`, `91dffec`, `99cf25f`

---

### P2 - Medium Priority (4 items)

#### TD-X-004: Documentation Organization Still Evolving
**Category**: Documentation
**Location**: `docs/` directory
**Impact**: Documentation may be hard to discover
**Effort**: M (2-3 days)

**Description**:
Documentation recently reorganized but still needs:
- Search functionality
- Documentation site (Sphinx/MkDocs)
- API reference generation
- Tutorial pathway
- Video tutorials

**Action Needed**:
- [ ] Set up documentation site
- [ ] Add API reference auto-generation
- [ ] Create tutorial pathway
- [ ] Add search functionality
- [ ] Create video tutorials

**References**:
- Reorganized in this session (Question 2)

---

#### TD-X-005: Error Messages Generic and Unhelpful
**Category**: Developer Experience
**Location**: Cross-cutting error handling
**Impact**: Debugging is difficult
**Effort**: L (1-2 weeks)

**Description**:
Many error messages are generic:
- "Storage error occurred"
- "Parsing failed"
- "LLM request failed"

Should include:
- Specific error details
- Likely causes
- Suggested fixes
- Debug commands
- Documentation links

**Action Needed**:
- [ ] Audit all error messages
- [ ] Create error message guidelines
- [ ] Add context to exceptions
- [ ] Link errors to troubleshooting docs
- [ ] Add error code system

---

#### TD-X-006: Performance Benchmarking Not Continuous
**Category**: CI/CD
**Location**: Performance test suite
**Impact**: Performance regressions undetected
**Effort**: M (3-5 days)

**Description**:
Performance benchmarks exist but:
- Not run in CI (too slow)
- No historical tracking
- No regression detection
- No performance budgets

**Action Needed**:
- [ ] Set up nightly performance CI
- [ ] Track benchmark results over time
- [ ] Add performance regression detection
- [ ] Set performance budgets per module
- [ ] Create performance dashboard

---

#### TD-X-007: Integration Test Coverage Uneven
**Category**: Test Quality
**Location**: `tests/integration/`
**Impact**: Cross-package issues may be missed
**Effort**: L (1-2 weeks)

**Description**:
Integration tests cover happy paths but lack:
- Error propagation across packages
- Concurrent access patterns
- Resource cleanup edge cases
- Long-running scenario tests

**Action Needed**:
- [ ] Add cross-package error tests
- [ ] Add concurrency integration tests
- [ ] Add resource cleanup tests
- [ ] Add long-running scenario tests
- [ ] Achieve 90%+ integration coverage

---

### P3 - Low Priority (1 item)

#### TD-X-008: Development Environment Setup Not Streamlined
**Category**: Developer Experience
**Location**: Project setup documentation
**Impact**: New contributors face friction
**Effort**: M (2-3 days)

**Description**:
Setting up development environment requires:
- Multiple manual steps
- Understanding of Python packaging
- Knowledge of tree-sitter setup
- Optional dependency confusion

**Action Needed**:
- [ ] Create `make setup` target
- [ ] Add development container (devcontainer.json)
- [ ] Create setup troubleshooting guide
- [ ] Add setup verification script
- [ ] Document VS Code setup

---

## Summary Statistics

**Last Updated**: December 26, 2025 (v0.2.0 + MCP aurora_query)
**Resolved This Release**: 2 P1 items (TD-P1-001, TD-P2-001)
**New This Release**: 10 MCP items (Phase 4)

### By Priority

| Priority | Count | Resolved | Remaining | % Complete | Est. Effort |
|----------|-------|----------|-----------|------------|-------------|
| **P0 - Critical** | 0 | 0 | 0 | - | 0 weeks |
| **P1 - High** | 18 | 2 | 16 | 11% | 7-10 weeks (was 7-9) |
| **P2 - Medium** | 27 | 0 | 27 | 0% | 9-12 weeks (was 8-10) |
| **P3 - Low** | 12 | 0 | 12 | 0% | 3-4 weeks (was 2-3) |
| **Total** | 57 | 2 | 55 | 4% | 19-26 weeks (was 17-22) |

### By Category

| Category | Count | % of Total |
|----------|-------|------------|
| Test Coverage Gap | 14 | 25% |
| Documentation | 11 | 19% |
| Performance | 7 | 12% |
| Feature Completeness | 6 | 11% |
| Developer Experience | 6 | 11% |
| Reliability | 4 | 7% |
| Type Safety | 3 | 5% |
| Observability | 3 | 5% |
| Configuration | 2 | 4% |
| Others | 1 | 2% |

### By Phase

| Phase | Count | Est. Effort |
|-------|-------|-------------|
| Phase 1 | 12 | 4-6 weeks |
| Phase 2 | 15 | 6-8 weeks |
| Phase 3 | 20 | 8-10 weeks |
| Phase 4 (MCP) | 10 | 2-3 weeks |
| Cross-Phase | 8 | 4-6 weeks |

### By Effort

| Effort | Count | % of Total |
|--------|-------|------------|
| XS (<2h) | 4 | 7% |
| S (2-8h) | 17 | 30% |
| M (1-3d) | 23 | 40% |
| L (1-2w) | 12 | 21% |
| XL (2w+) | 1 | 2% |

---

## Recommended Order of Attack

### Sprint 1: Critical Coverage Gaps ✅ PARTIALLY COMPLETE
**Goal**: Address high-risk test coverage gaps
**Status**: 2/4 items resolved in v1.1.0

1. ✅ **TD-P1-001**: Migration logic tests (RESOLVED - 94.17% coverage)
2. **TD-P1-002**: Error handling rollback tests (PENDING)
3. ✅ **TD-P2-001**: LLM client initialization tests (RESOLVED - 93.14% coverage)
4. **TD-P3-001**: Semantic embedding error paths (PENDING)

**Outcome Achieved**:
- migrations.py: 94.17% coverage (exceeded 80% target)
- llm_client.py: 93.14% coverage (exceeded 70% target)
- 79 new tests added (33 migrations + 46 LLM client)
- Production risk significantly reduced for schema migrations and API initialization

---

### Sprint 2: MCP Integration Reliability (1 week)
**Goal**: Stabilize MCP integration for Claude Code CLI usage

1. **TD-MCP-001**: Fix MCP server subprocess timeouts (P1) - 2-3 days
2. **TD-MCP-002**: Adjust embedding performance thresholds (P2) - 4-6 hours
3. **TD-MCP-004**: Document environment variables (P2) - 2-3 hours
4. **TD-MCP-009**: Document configuration priority (P3) - 2 hours

**Expected Outcome**: CI/CD reliable, Claude Code CLI users have clear setup docs

---

### Sprint 3: Type Safety & Developer Experience (2 weeks)
**Goal**: Improve type safety and developer workflow

1. **TD-P1-003**: Add py.typed markers (QUICK WIN)
2. **TD-X-001**: Type checking completeness
3. **TD-X-008**: Development environment streamlining
4. **TD-P1-004**: Document Python 3.12 compatibility

**Expected Outcome**: Better IDE support, easier onboarding, fewer runtime type errors

---

### Sprint 3: Performance & Reliability (2 weeks)
**Goal**: Improve system performance and reliability

1. **TD-P3-002**: Hybrid retrieval precision improvement
2. **TD-P2-005**: Pattern cache eviction strategy
3. **TD-P3-005**: Memory test GC sensitivity
4. **TD-P3-014**: Error recovery rate improvement

**Expected Outcome**: Better retrieval quality, more stable tests, higher reliability

---

### Sprint 4: Feature Completeness (2 weeks)
**Goal**: Complete partially implemented features

1. **TD-P2-003**: SOAR verification Option B development
2. **TD-P3-004**: Headless mode reliability improvement
3. **TD-P3-010**: CLI memory commands expansion
4. **TD-P2-004**: Cost tracking granularity

**Expected Outcome**: Production-grade features, better observability

---

### Sprint 5: Documentation & Usability (1 week)
**Goal**: Improve user-facing documentation

1. **TD-X-004**: Documentation site setup
2. **TD-P3-006**: Embedding model download UX
3. **TD-X-005**: Error message improvements
4. **TD-P3-011**: Performance tuning guide examples

**Expected Outcome**: Better user experience, reduced support burden

---

### Long-term Backlog (P2/P3 items)
**Schedule**: Allocate 10-20% of sprint capacity ongoing

- Algorithmic improvements (TD-P2-011, TD-P3-008)
- Extensibility features (TD-P2-009)
- Advanced optimizations (TD-P2-007)
- Additional documentation polish

---

## Maintenance Strategy

### Continuous Improvement

1. **Every Sprint**:
   - Pick 2-3 small debt items (XS/S effort)
   - Address highest priority items first
   - Update this document with completed items

2. **Monthly**:
   - Review and re-prioritize debt items
   - Add newly discovered debt
   - Archive resolved items

3. **Quarterly**:
   - Dedicated "debt sprint" (1-2 weeks)
   - Focus on architectural improvements
   - Refactor high-churn areas

### Metrics to Track

- **Debt Velocity**: Items resolved per sprint
- **Debt Accumulation**: New items added per sprint
- **Coverage Trend**: Test coverage over time
- **Type Safety**: mypy error count trend
- **CI Stability**: Test flakiness rate

### Preventing New Debt

1. **Code Review Checklist**: Check for debt patterns
2. **Definition of Done**: Include test coverage requirements
3. **Technical Debt Tag**: Label GitHub issues as debt
4. **Retrospectives**: Discuss debt creation patterns
5. **Pre-commit Hooks**: Enforce quality standards

---

## Document Changelog

| Date | Change | Author |
|------|--------|--------|
| 2025-12-24 | Initial creation | Claude |
| TBD | First quarterly review | TBD |

---

## References

### Internal Documentation
- [Coverage Analysis](./reports/testing/COVERAGE_ANALYSIS.md)
- [Phase 1 Verification Report](./phases/phase1/PHASE1_VERIFICATION_REPORT.md)
- [Phase 2 Completion Summary](./phases/phase2/PHASE2_COMPLETION_SUMMARY.md)
- [Phase 3 Stakeholder Report](./phases/phase3/PHASE3_STAKEHOLDER_COMPLETION_REPORT.md)
- [Performance Profiling Report](./performance/PERFORMANCE_PROFILING_REPORT.md)
- [Memory Profiling Report](./performance/MEMORY_PROFILING_REPORT.md)

### External Resources
- [Technical Debt Quadrant (Martin Fowler)](https://martinfowler.com/bliki/TechnicalDebtQuadrant.html)
- [Managing Technical Debt (IEEE)](https://doi.org/10.1109/MS.2012.27)
- [Code Complete (McConnell)](https://www.oreilly.com/library/view/code-complete-2nd/0735619670/)

---

**End of Technical Debt Document**
