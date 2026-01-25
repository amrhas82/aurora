# Epic 2: Memory Search Performance Optimizations (Lazy Loading + Dual-Hybrid Fallback)

**PRD**: `tasks/aur-mem-search/0032-prd-epic2-lazy-loading-fallback.md`
**Estimated Effort**: 15 hours (2 working days)
**Status**: Ready for implementation

---

## Relevant Files

### Core Implementation
- `/home/hamr/PycharmProjects/aurora/packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py` - Primary implementation file (~120 lines changed: 50 modified, 70 added)

### Test Files (To Be Created)
- `/home/hamr/PycharmProjects/aurora/tests/unit/context_code/semantic/test_hybrid_retriever_lazy_loading.py` - Unit tests for lazy BM25 loading (~100 lines)
- `/home/hamr/PycharmProjects/aurora/tests/unit/context_code/semantic/test_hybrid_retriever_dual_fallback.py` - Unit tests for dual-hybrid fallback (~150 lines)
- `/home/hamr/PycharmProjects/aurora/tests/performance/test_hybrid_retriever_lazy_loading.py` - Performance tests for lazy loading (~80 lines)
- `/home/hamr/PycharmProjects/aurora/tests/performance/test_hybrid_retriever_dual_fallback.py` - Performance tests for fallback speed (~60 lines)

### Documentation Files
- `/home/hamr/PycharmProjects/aurora/CLAUDE.md` - Update performance optimization rules and memory system section
- `/home/hamr/PycharmProjects/aurora/docs/KNOWLEDGE_BASE.md` - Update performance benchmarks
- `/home/hamr/PycharmProjects/aurora/docs/analysis/MEMORY_SEARCH_OPTIMIZATION_PLAN.md` - Mark Epic 2 complete
- `/home/hamr/PycharmProjects/aurora/docs/analysis/FALLBACK_QUALITY_ANALYSIS.md` - NEW: Document qualitative testing results

### Reference Files
- `/home/hamr/PycharmProjects/aurora/tests/unit/context_code/semantic/test_hybrid_retriever_cache.py` - Reference for test patterns
- `/home/hamr/PycharmProjects/aurora/tests/unit/context_code/semantic/test_hybrid_retriever_threshold.py` - Reference for test patterns

---

### Notes

**Testing Framework**: Aurora uses pytest with markers (`@pytest.mark.unit`, `@pytest.mark.performance`)

**Test Patterns**:
- Unit tests use mock classes (MockStore, MockActivationEngine, MockEmbeddingProvider)
- Performance tests use `time.perf_counter()` for timing
- Thread-safety tests use `threading.Thread` with concurrent execution
- Assertions include tolerance for floating-point comparisons (`abs(x - y) < 1e-6`)

**Performance Baselines** (from PRD Section 7.1):
- HybridRetriever creation: 150-250ms → Target <50ms
- Fallback search (activation-only): 2-3s → Target <1s
- Tri-hybrid search: 10-12s → No regression allowed

**Architecture Patterns**:
- Double-checked locking: Fast path check → lock → double-check → load
- Lazy initialization: Defer expensive operations until first use
- Weight normalization: Redistribute weights when one component unavailable

**Critical Implementation Details**:
- Lines 529: Add `self._bm25_lock = threading.Lock()`
- Lines 532-533: REMOVE eager `_try_load_bm25_index()` call
- Lines 790-795: ADD lazy loading with double-checked locking in `_stage1_bm25_filter()`
- Lines 628, 639: Update call sites from `_fallback_to_activation_only` to `_fallback_to_dual_hybrid`
- Lines 930-956: REPLACE method implementation with dual-hybrid logic

**Quality Requirements**:
- All existing tests must pass unchanged (no regressions)
- Code coverage maintained at 85%+
- Performance regression tests validate targets
- Qualitative testing documents 85% quality claim

---

## Tasks

- [x] 0.0 Create feature branch
  - [x] 0.1 Create and checkout branch `feature/epic2-lazy-loading-fallback`
    - tdd: no
    - verify: `git branch --show-current`

- [x] 1.0 Implement Feature 1: Lazy BM25 Index Loading
  - [x] 1.1 Add thread-safety lock to HybridRetriever.__init__()
    - Add `self._bm25_lock = threading.Lock()` after line 529
    - Imports: `import threading` already present at line 25
    - Location: `/home/hamr/PycharmProjects/aurora/packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py:529`
    - tdd: no
    - verify: `python -c "from aurora_context_code.semantic.hybrid_retriever import HybridRetriever; print('Lock added')"`
  - [x] 1.2 Remove eager BM25 index loading from __init__()
    - Delete lines 532-533: `if self.config.enable_bm25_persistence...self._try_load_bm25_index()`
    - Keep `self._bm25_index_loaded = False` flag (line 529)
    - Location: `/home/hamr/PycharmProjects/aurora/packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py:532-533`
    - tdd: no
    - verify: `grep -n "_try_load_bm25_index" /home/hamr/PycharmProjects/aurora/packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py | grep -v "def _try_load_bm25_index"`
  - [x] 1.3 Add lazy loading to _stage1_bm25_filter() with double-checked locking
    - Insert before line 791 (after docstring, before existing logic)
    - Implement pattern: check flag → acquire lock → double-check → load → release
    - Code block: ~15 lines (see PRD lines 149-162)
    - Location: `/home/hamr/PycharmProjects/aurora/packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py:791`
    - tdd: no
    - verify: `python -c "from aurora_context_code.semantic.hybrid_retriever import HybridRetriever; print('Lazy loading added')"`
  - [x] 1.4 Create unit tests for lazy BM25 loading
    - File: `/home/hamr/PycharmProjects/aurora/tests/unit/context_code/semantic/test_hybrid_retriever_lazy_loading.py`
    - Test cases (4): not loaded on init, loaded on first retrieve, reused on subsequent, thread-safety
    - Reference: `test_hybrid_retriever_cache.py` for patterns
    - Lines: ~100
    - tdd: yes
    - verify: `pytest tests/unit/context_code/semantic/test_hybrid_retriever_lazy_loading.py -v`
  - [x] 1.5 Create performance test for creation time <50ms
    - File: `/home/hamr/PycharmProjects/aurora/tests/performance/test_hybrid_retriever_lazy_loading.py`
    - Test cases (2): creation time <50ms, first retrieve overhead <5%
    - Use `time.perf_counter()` for timing
    - Lines: ~80
    - tdd: yes
    - verify: `pytest tests/performance/test_hybrid_retriever_lazy_loading.py -v -m performance`
  - [x] 1.6 Verify: Run full test suite - no regressions
    - Run unit tests, integration tests, and performance tests
    - Ensure all existing `test_hybrid_retriever_*.py` tests pass
    - Check for thread-safety issues
    - tdd: no
    - verify: `make test-unit && make test-integration`

- [ ] 2.0 Implement Feature 2: BM25+Activation Dual-Hybrid Fallback
  - [ ] 2.1 Rename _fallback_to_activation_only() to _fallback_to_dual_hybrid()
    - Rename method at line 930
    - Update call sites: line 628, line 639
    - Update docstring to reflect dual-hybrid functionality
    - Location: `/home/hamr/PycharmProjects/aurora/packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py:930,628,639`
    - tdd: no
    - verify: `grep -n "_fallback_to_dual_hybrid" /home/hamr/PycharmProjects/aurora/packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py`
  - [ ] 2.2 Implement BM25 filter in fallback method
    - Add `self._stage1_bm25_filter(query, activation_candidates)` call
    - Process stage1 candidates for BM25 scores
    - Code block: ~10 lines
    - Location: `/home/hamr/PycharmProjects/aurora/packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py:935-945`
    - tdd: yes
    - verify: `python -c "from aurora_context_code.semantic.hybrid_retriever import HybridRetriever; print('BM25 filter added')"`
  - [ ] 2.3 Implement weight normalization logic
    - Redistribute semantic_weight to bm25 and activation proportionally
    - Formula: `bm25_dual = bm25_weight / (bm25_weight + activation_weight)`
    - Handle edge case: both weights are 0 (fallback to activation-only)
    - Code block: ~10 lines (see PRD lines 238-246)
    - Location: `/home/hamr/PycharmProjects/aurora/packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py:945-955`
    - tdd: yes
    - verify: `python -c "from aurora_context_code.semantic.hybrid_retriever import HybridRetriever; print('Weight normalization added')"`
  - [ ] 2.4 Implement dual-hybrid scoring calculation
    - Calculate normalized BM25 and activation scores
    - Combine with dual-hybrid weights
    - Return results in tri-hybrid format (semantic_score=0.0)
    - Code block: ~25 lines (see PRD lines 248-309)
    - Location: `/home/hamr/PycharmProjects/aurora/packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py:955-980`
    - tdd: yes
    - verify: `python -c "from aurora_context_code.semantic.hybrid_retriever import HybridRetriever; print('Dual-hybrid scoring added')"`
  - [ ] 2.5 Add WARNING logging with instructions
    - Log at WARNING level when fallback triggered
    - Message: "Embedding model unavailable - using BM25+Activation fallback (estimated 85% quality vs 95% tri-hybrid)"
    - Include instructions: "To restore full quality, check: pip install sentence-transformers"
    - Location: `/home/hamr/PycharmProjects/aurora/packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py:932-935`
    - tdd: no
    - verify: `grep -n "BM25+Activation fallback" /home/hamr/PycharmProjects/aurora/packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py`
  - [ ] 2.6 Create unit tests for dual-hybrid fallback
    - File: `/home/hamr/PycharmProjects/aurora/tests/unit/context_code/semantic/test_hybrid_retriever_dual_fallback.py`
    - Test cases (5): triggered when no provider, triggered when embed fails, weights normalized, WARNING logged, edge case zero weights
    - Use `caplog` fixture for log assertions
    - Lines: ~150
    - tdd: yes
    - verify: `pytest tests/unit/context_code/semantic/test_hybrid_retriever_dual_fallback.py -v`
  - [ ] 2.7 Create performance test for fallback speed <1s
    - File: `/home/hamr/PycharmProjects/aurora/tests/performance/test_hybrid_retriever_dual_fallback.py`
    - Test cases (2): fallback completes <1s, faster than activation-only
    - Use warm search (BM25 index already loaded)
    - Lines: ~60
    - tdd: yes
    - verify: `pytest tests/performance/test_hybrid_retriever_dual_fallback.py -v -m performance`
  - [ ] 2.8 Verify: Run full test suite - no regressions
    - Run unit tests, integration tests, and performance tests
    - Ensure all existing `test_hybrid_retriever_*.py` tests pass
    - Check fallback is triggered correctly
    - tdd: no
    - verify: `make test-unit && make test-integration`

- [ ] 3.0 Qualitative Validation
  - [ ] 3.1 Run manual testing with 10 queries
    - Index Aurora codebase: `aur mem index .`
    - Test queries (10): SoarOrchestrator, memory search caching, BM25 scoring, etc. (see PRD lines 850-861)
    - For each query: run tri-hybrid (normal) and dual-hybrid (AURORA_EMBEDDING_PROVIDER=none)
    - Record top 10 results for both modes
    - Calculate overlap: `len(set(tri_results) & set(dual_results)) / 10`
    - Expected: 70-90% overlap (7-9 matching results)
    - tdd: no
    - verify: Manual testing complete, results documented
  - [ ] 3.2 Document results in FALLBACK_QUALITY_ANALYSIS.md
    - File: `/home/hamr/PycharmProjects/aurora/docs/analysis/FALLBACK_QUALITY_ANALYSIS.md`
    - Table: Query | Tri-Hybrid Results | Dual-Hybrid Results | Overlap %
    - Summary: Average overlap, quality assessment, edge cases
    - Validation: Is 85% quality claim validated?
    - Lines: ~50-100
    - tdd: no
    - verify: `cat /home/hamr/PycharmProjects/aurora/docs/analysis/FALLBACK_QUALITY_ANALYSIS.md`
  - [ ] 3.3 Run performance benchmarks (before/after)
    - Benchmark retriever creation time: `python -c "..." ` (see PRD lines 907-930)
    - Benchmark fallback search speed: `AURORA_EMBEDDING_PROVIDER=none python -c "..."` (see PRD lines 933-964)
    - Document results: Creation time <50ms? Fallback search <1s?
    - Compare to baselines (PRD Section 7.1)
    - tdd: no
    - verify: Performance benchmarks meet targets
  - [ ] 3.4 Verify: All success metrics met
    - AC-F1.1: Creation time <50ms ✓
    - AC-F1.4: Thread-safety guaranteed ✓
    - AC-F2.2: BM25+Activation scores present ✓
    - AC-F2.3: Weights sum to 1.0 ✓
    - AC-F2.5: Search completes <1s ✓
    - AC-F2.6: Search quality ~85% ✓
    - tdd: no
    - verify: Manual checklist verification

- [ ] 4.0 Documentation & Review
  - [ ] 4.1 Update docstrings in hybrid_retriever.py
    - Update class docstring to mention lazy loading
    - Update `__init__()` docstring: BM25 loaded on first `retrieve()`
    - Update `_stage1_bm25_filter()` docstring: mention lazy loading logic
    - Update `_fallback_to_dual_hybrid()` docstring (new method)
    - Location: `/home/hamr/PycharmProjects/aurora/packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py:1,498,776,930`
    - tdd: no
    - verify: `grep -A5 "def __init__" /home/hamr/PycharmProjects/aurora/packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py | head -20`
  - [ ] 4.2 Update CLAUDE.md performance section
    - Update "Performance Optimization Rules" with lazy loading pattern
    - Update "Memory System" section with fallback mode description
    - Update benchmarks: Creation <50ms, Fallback quality 85%
    - Location: `/home/hamr/PycharmProjects/aurora/CLAUDE.md`
    - tdd: no
    - verify: `grep -n "Lazy BM25" /home/hamr/PycharmProjects/aurora/CLAUDE.md`
  - [ ] 4.3 Update MEMORY_SEARCH_OPTIMIZATION_PLAN.md
    - Mark Epic 2 tasks as COMPLETED
    - Update roadmap with Epic 3 status (pre-tokenization, etc.)
    - Add performance results summary
    - Location: `/home/hamr/PycharmProjects/aurora/docs/analysis/MEMORY_SEARCH_OPTIMIZATION_PLAN.md`
    - tdd: no
    - verify: `grep -n "Epic 2.*COMPLETED" /home/hamr/PycharmProjects/aurora/docs/analysis/MEMORY_SEARCH_OPTIMIZATION_PLAN.md`
  - [ ] 4.4 Update KNOWLEDGE_BASE.md
    - Update performance benchmarks section
    - Add fallback quality metrics
    - Reference new FALLBACK_QUALITY_ANALYSIS.md
    - Location: `/home/hamr/PycharmProjects/aurora/docs/KNOWLEDGE_BASE.md`
    - tdd: no
    - verify: `grep -n "fallback.*85%" /home/hamr/PycharmProjects/aurora/docs/KNOWLEDGE_BASE.md`
  - [ ] 4.5 Verify: Final code review and cleanup
    - Run linter: `make lint`
    - Run type checker: `make type-check`
    - Run full quality check: `make quality-check`
    - Verify code coverage: `make coverage` (target 85%+)
    - tdd: no
    - verify: `make quality-check && make coverage`

- [ ] 5.0 Final Verification and Merge
  - [ ] 5.1 Run complete test suite
    - Unit tests: `make test-unit`
    - Integration tests: `make test-integration`
    - Performance tests: `make test-performance`
    - Verify: 100% pass rate, no regressions
    - tdd: no
    - verify: `make test`
  - [ ] 5.2 Verify performance targets met
    - HybridRetriever creation: <50ms ✓
    - Fallback search: <1s ✓
    - Tri-hybrid search: no regression (10-12s) ✓
    - Fallback quality: ~85% ✓
    - tdd: no
    - verify: Manual performance validation
  - [ ] 5.3 Create git commit
    - Stage changes: `git add packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py tests/ docs/`
    - Commit message: "feat: add lazy BM25 loading and dual-hybrid fallback (Epic 2)"
    - Body: "- Lazy BM25 index loading: 150-250ms → <50ms creation time\n- Dual-hybrid fallback: 60% → 85% quality when embeddings unavailable\n- Thread-safe lazy loading with double-checked locking\n- Weight normalization for BM25+Activation dual-hybrid mode\n- Comprehensive unit and performance tests\n- Documentation updates"
    - tdd: no
    - verify: `git log -1 --stat`
  - [ ] 5.4 Merge to main
    - Create PR if workflow requires
    - Merge feature branch to main: `git checkout main && git merge feature/epic2-lazy-loading-fallback`
    - Push to remote: `git push origin main`
    - tdd: no
    - verify: `git log --oneline -5`

---

## Summary

**Total Tasks**: 29 subtasks across 6 parent tasks
**Estimated Time**: 15 hours (2 working days)
**Critical Path**: 1.0 → 2.0 → 3.0 → 4.0 → 5.0
**Dependencies**: Tasks 1.0 and 2.0 can run in parallel until integration tests

**Key Deliverables**:
1. Lazy BM25 index loading with thread-safety (Feature 1)
2. BM25+Activation dual-hybrid fallback (Feature 2)
3. 4 new test files (~390 lines total)
4. Qualitative analysis document
5. Updated documentation (CLAUDE.md, KNOWLEDGE_BASE.md, optimization plan)

**Success Criteria**:
- All existing tests pass unchanged
- Performance targets met: <50ms creation, <1s fallback search
- Quality target met: ~85% fallback quality
- Code coverage maintained at 85%+
- No regressions in tri-hybrid search performance
