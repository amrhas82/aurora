# Task List: BM25 Tri-Hybrid Memory Search Implementation

**Source PRD**: `/home/hamr/PycharmProjects/aurora/tasks/0015-prd-bm25-trihybrid-memory-search.md`

**Estimated Effort**: 8-10 hours

**Implementation Approach**: Staged retrieval architecture with BM25 filter (Stage 1) → Semantic+Activation re-rank (Stage 2)

**TDD Strategy**: Shell tests FIRST → Unit tests for pure functions → Implementation → Integration tests

---

## Task 1.0: Implement BM25 Core with Code-Aware Tokenization

**Estimated**: 2.5 hours

### 1.1 Write Shell Tests for BM25 Exact Match (30 min)
- [x] Create `tests/shell/test_01_exact_soarorchestrator.sh`
- [x] Create `tests/shell/test_02_exact_processquery.sh`
- [x] Create `tests/shell/test_03_camelcase_getuserdata.sh`
- [x] Add validation logic for top-3 results
- [x] Make tests executable (`chmod +x`)
- **Dependencies**: None
- **Verification**: `bash tests/shell/test_01_*.sh` runs and shows PENDING

### 1.2 Write Unit Tests for Tokenization (30 min)
- [x] Create `tests/unit/test_bm25_tokenizer.py`
- [x] Implement UT-BM25-01: CamelCase splitting
- [x] Implement UT-BM25-02: snake_case splitting
- [x] Implement UT-BM25-03: Dot notation
- [x] Implement UT-BM25-04: Acronym preservation
- [x] Implement UT-BM25-05: Mixed case handling
- **Dependencies**: None
- **Verification**: `pytest tests/unit/test_bm25_tokenizer.py` shows 9 failures (expected)

### 1.3 Create BM25Scorer Class with Tokenizer (1 hour)
- [x] Create `packages/context-code/src/aurora_context_code/semantic/bm25_scorer.py`
- [x] Implement `tokenize()` function with code-aware patterns
- [x] Pass UT-BM25-01 through UT-BM25-09
- [x] Add logging for tokenization debug
- **Dependencies**: 1.2
- **Files Modified**: New file
- **Verification**: `pytest tests/unit/test_bm25_tokenizer.py` passes 9/9

### 1.4 Write Unit Tests for BM25 Scoring (20 min)
- [x] Add UT-BM25-10: IDF calculation test
- [x] Add UT-BM25-11: Term frequency test
- [x] Add UT-BM25-12: Document length normalization test
- [x] Add UT-BM25-13: Multiple term scoring test
- [x] Add UT-BM25-14: Exact match test
- [x] Add UT-BM25-15: No match test
- **Dependencies**: 1.3
- **Verification**: All tests added to test_bm25_tokenizer.py

### 1.5 Implement BM25 Scoring Algorithm (30 min)
- [x] Implement `calculate_idf(term, document_count, term_doc_count)`
- [x] Implement `calculate_bm25(query_terms, doc_terms, doc_length, avg_doc_length)`
- [x] Use k1=1.5, b=0.75 (Okapi BM25 parameters)
- [x] Pass UT-BM25-10 through UT-BM25-15
- [x] Fix tokenization to preserve duplicates for term frequency
- **Dependencies**: 1.4
- **Verification**: `pytest tests/unit/test_bm25_tokenizer.py` passes 15/15

---

## Task 2.0: Refactor Hybrid Retriever for Staged Retrieval Architecture

**Estimated**: 2 hours

### 2.1 Write Shell Tests for Staged Retrieval (20 min)
- [ ] Create `tests/shell/test_04_staged_exact_wins.sh` (exact match beats high-activation)
- [ ] Create `tests/shell/test_05_staged_topk_coverage.sh` (Stage 1 captures diverse results)
- [ ] Add validation for staged retrieval behavior
- **Dependencies**: 1.5
- **Verification**: Tests show PENDING (implementation not ready)

### 2.2 Write Unit Tests for Staged Architecture (30 min)
- [ ] Create `tests/unit/test_hybrid_retriever_staged.py`
- [ ] Implement UT-HYBRID-01: Stage 1 BM25 filtering test
- [ ] Implement UT-HYBRID-02: Stage 2 re-ranking test
- [ ] Implement UT-HYBRID-03: Score preservation test (no normalization conflicts)
- [ ] Implement UT-HYBRID-04: Empty query handling
- **Dependencies**: 1.5
- **Verification**: `pytest tests/unit/test_hybrid_retriever_staged.py` shows 4 failures

### 2.3 Backup Current HybridRetriever (10 min)
- [ ] Copy `hybrid_retriever.py` to `hybrid_retriever_v1_backup.py`
- [ ] Add docstring: "Backup of 60/40 activation/semantic (pre-BM25)"
- [ ] Git commit backup
- **Dependencies**: None
- **Verification**: `git log --oneline -1` shows backup commit

### 2.4 Refactor HybridRetriever for Staged Retrieval (1 hour)
- [ ] Modify `retrieve()` method signature to accept `use_staged=True`
- [ ] Implement Stage 1: BM25 filtering (top_k=100)
- [ ] Implement Stage 2: Semantic+Activation re-ranking
- [ ] Update `_combine_scores()` for tri-hybrid (30% BM25 + 40% Semantic + 30% Activation)
- [ ] Pass UT-HYBRID-01 through UT-HYBRID-04
- [ ] Run ST-04 and ST-05 shell tests
- **Dependencies**: 2.2, 2.3
- **Files Modified**: `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py`
- **Verification**:
  - `pytest tests/unit/test_hybrid_retriever_staged.py` passes 4/4
  - `bash tests/shell/test_04_staged_exact_wins.sh` passes

---

## Task 3.0: Implement Knowledge Chunk Parser and Indexing

**Estimated**: 1.5 hours

### 3.1 Write Shell Tests for Knowledge Chunk Indexing (20 min)
- [ ] Create `tests/shell/test_06_knowledge_indexing.sh` (index conversation logs)
- [ ] Create `tests/shell/test_07_knowledge_search.sh` (search knowledge chunks)
- [ ] Add sample conversation log for testing
- **Dependencies**: None
- **Verification**: Tests show PENDING

### 3.2 Write Unit Tests for KnowledgeParser (30 min)
- [ ] Create `tests/unit/test_knowledge_parser.py`
- [ ] Implement UT-KNOW-01: Parse markdown sections test
- [ ] Implement UT-KNOW-02: Extract metadata test (keywords, date)
- [ ] Implement UT-KNOW-03: Chunk splitting test
- [ ] Implement UT-KNOW-04: Empty file handling
- **Dependencies**: None
- **Verification**: `pytest tests/unit/test_knowledge_parser.py` shows 4 failures

### 3.3 Implement KnowledgeParser Class (40 min)
- [ ] Create `packages/context-code/src/aurora_context_code/knowledge_parser.py`
- [ ] Implement `parse_conversation_log(file_path)` → list[KnowledgeChunk]
- [ ] Extract metadata from filename (keywords, date)
- [ ] Split by markdown headers (## sections)
- [ ] Pass UT-KNOW-01 through UT-KNOW-04
- [ ] Run ST-06 and ST-07 shell tests
- **Dependencies**: 3.2
- **Files Modified**: New file
- **Verification**:
  - `pytest tests/unit/test_knowledge_parser.py` passes 4/4
  - `bash tests/shell/test_06_knowledge_indexing.sh` passes

---

## Task 4.0: Enable Reasoning Chunk Search Integration

**Estimated**: 1 hour

### 4.1 Write Shell Tests for Reasoning Chunk Search (15 min)
- [ ] Create `tests/shell/test_08_reasoning_search.sh` (search reasoning patterns)
- [ ] Create `tests/shell/test_09_reasoning_type_filter.sh` (--type reasoning)
- **Dependencies**: None
- **Verification**: Tests show PENDING

### 4.2 Write Unit Tests for Reasoning Chunk Embeddings (20 min)
- [ ] Create `tests/unit/test_reasoning_embeddings.py`
- [ ] Implement UT-REAS-01: Generate embeddings test
- [ ] Implement UT-REAS-02: Store embeddings test
- [ ] Implement UT-REAS-03: Retrieve by pattern test
- **Dependencies**: None
- **Verification**: `pytest tests/unit/test_reasoning_embeddings.py` shows 3 failures

### 4.3 Add Embedding Generation for ReasoningChunks (25 min)
- [ ] Modify `packages/cli/src/aurora_cli/memory_manager.py::index_reasoning_chunks()`
- [ ] Generate embeddings for `content + pattern` fields
- [ ] Store embeddings in ChromaDB collection
- [ ] Pass UT-REAS-01 through UT-REAS-03
- [ ] Run ST-08 and ST-09 shell tests
- **Dependencies**: 4.2
- **Files Modified**: `packages/cli/src/aurora_cli/memory_manager.py`
- **Verification**:
  - `pytest tests/unit/test_reasoning_embeddings.py` passes 3/3
  - `bash tests/shell/test_08_reasoning_search.sh` passes

---

## Task 5.0: Enhance Search Result Display with Git Metadata

**Estimated**: 1 hour

### 5.1 Write Shell Tests for Git Metadata Display (15 min)
- [ ] Create `tests/shell/test_10_git_metadata_display.sh` (shows commit count, last modified)
- [ ] Add validation for git metadata presence in output
- **Dependencies**: None
- **Verification**: Test shows PENDING

### 5.2 Write Unit Tests for Display Formatting (20 min)
- [ ] Create `tests/unit/test_display_formatter.py`
- [ ] Implement UT-DISPLAY-01: Git metadata formatting test
- [ ] Implement UT-DISPLAY-02: Rich table generation test
- [ ] Implement UT-DISPLAY-03: Truncation test (long content)
- **Dependencies**: None
- **Verification**: `pytest tests/unit/test_display_formatter.py` shows 3 failures

### 5.3 Update SearchResult Display Logic (25 min)
- [ ] Modify `packages/cli/src/aurora_cli/commands/query.py::display_results()`
- [ ] Add git metadata columns: Commits, Last Modified
- [ ] Format timestamps as relative time ("2 days ago")
- [ ] Pass UT-DISPLAY-01 through UT-DISPLAY-03
- [ ] Run ST-10 shell test
- **Dependencies**: 5.2
- **Files Modified**: `packages/cli/src/aurora_cli/commands/query.py`
- **Verification**:
  - `pytest tests/unit/test_display_formatter.py` passes 3/3
  - `bash tests/shell/test_10_git_metadata_display.sh` passes

---

## Task 6.0: Add Score Transparency and Type Filtering Features

**Estimated**: 1.5 hours

### 6.1 Write Shell Tests for Score Transparency (20 min)
- [ ] Create `tests/shell/test_11_show_scores_flag.sh` (--show-scores)
- [ ] Create `tests/shell/test_12_score_breakdown.sh` (BM25/Semantic/Activation shown)
- [ ] Add validation for score components in output
- **Dependencies**: None
- **Verification**: Tests show PENDING

### 6.2 Write Shell Tests for Type Filtering (20 min)
- [ ] Create `tests/shell/test_13_type_filter_function.sh` (--type function)
- [ ] Create `tests/shell/test_14_type_filter_reasoning.sh` (--type reasoning)
- [ ] Create `tests/shell/test_15_type_filter_knowledge.sh` (--type knowledge)
- **Dependencies**: None
- **Verification**: Tests show PENDING

### 6.3 Write Unit Tests for Filtering and Display (20 min)
- [ ] Create `tests/unit/test_type_filtering.py`
- [ ] Implement UT-FILTER-01: Filter by chunk_type test
- [ ] Implement UT-FILTER-02: Multiple type handling test
- [ ] Implement UT-DISPLAY-04: Score breakdown formatting test
- **Dependencies**: None
- **Verification**: `pytest tests/unit/test_type_filtering.py` shows 3 failures

### 6.4 Implement --show-scores Flag (20 min)
- [ ] Add `--show-scores` option to `aur mem search` command
- [ ] Modify display to show score breakdown table when flag is set
- [ ] Pass UT-DISPLAY-04
- [ ] Run ST-11 and ST-12 shell tests
- **Dependencies**: 6.3
- **Files Modified**: `packages/cli/src/aurora_cli/commands/query.py`
- **Verification**:
  - `bash tests/shell/test_11_show_scores_flag.sh` passes
  - Score breakdown shows BM25, Semantic, Activation components

### 6.5 Implement --type Filtering (30 min)
- [ ] Add `--type` option to `aur mem search` command (choices: function, class, method, reasoning, knowledge, module)
- [ ] Modify `HybridRetriever.retrieve()` to filter by chunk_type
- [ ] Pass UT-FILTER-01 and UT-FILTER-02
- [ ] Run ST-13, ST-14, ST-15 shell tests
- **Dependencies**: 6.3
- **Files Modified**: `packages/cli/src/aurora_cli/commands/query.py`, `hybrid_retriever.py`
- **Verification**:
  - `pytest tests/unit/test_type_filtering.py` passes 3/3
  - `bash tests/shell/test_13_type_filter_function.sh` passes

---

## Task 7.0: Implement Configuration System and Index Management

**Estimated**: 1.5 hours

### 7.1 Write Shell Tests for Configuration (20 min)
- [ ] Create `tests/shell/test_16_config_bm25_weight.sh` (BM25 weight adjustment)
- [ ] Create `tests/shell/test_17_config_stage1_topk.sh` (Stage 1 top-k tuning)
- [ ] Create `tests/shell/test_18_index_summary.sh` (FR-11: show code/reas/know counts)
- **Dependencies**: None
- **Verification**: Tests show PENDING

### 7.2 Write Unit Tests for Configuration (20 min)
- [ ] Create `tests/unit/test_hybrid_config.py`
- [ ] Implement UT-CONFIG-01: Load default config test
- [ ] Implement UT-CONFIG-02: Override weights test
- [ ] Implement UT-CONFIG-03: Stage 1 top-k validation test
- **Dependencies**: None
- **Verification**: `pytest tests/unit/test_hybrid_config.py` shows 3 failures

### 7.3 Create HybridSearchConfig Class (30 min)
- [ ] Add `HybridSearchConfig` to `hybrid_retriever.py`
- [ ] Add fields: `bm25_weight`, `semantic_weight`, `activation_weight`, `stage1_top_k`
- [ ] Add validation: weights sum to 1.0
- [ ] Pass UT-CONFIG-01 through UT-CONFIG-03
- **Dependencies**: 7.2
- **Files Modified**: `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py`
- **Verification**: `pytest tests/unit/test_hybrid_config.py` passes 3/3

### 7.4 Implement Indexing Summary Display (FR-11) (40 min)
- [ ] Modify `packages/cli/src/aurora_cli/memory_manager.py::index_directory()`
- [ ] Track counts: code_chunks, reasoning_chunks, knowledge_chunks
- [ ] Display summary with breakdown by type
- [ ] Format:
  ```
  Summary:
    Files scanned: 103
    Code chunks: 456
    Reasoning chunks: 23
    Knowledge chunks: 18
    Total chunks: 497
  ```
- [ ] Run ST-18 shell test
- **Dependencies**: None
- **Files Modified**: `packages/cli/src/aurora_cli/memory_manager.py`
- **Verification**: `bash tests/shell/test_18_index_summary.sh` passes

---

## Integration Testing (Run After All Tasks Complete)

### INT-1: End-to-End Search Quality Test (30 min)
- [ ] Create `tests/integration/test_e2e_search_quality.py`
- [ ] Index Aurora codebase (103 files)
- [ ] Run 20 queries with known ground truth
- [ ] Validate MRR ≥ 0.85 (Mean Reciprocal Rank)
- **Dependencies**: All tasks 1-7 complete
- **Verification**: `pytest tests/integration/test_e2e_search_quality.py` passes

### INT-2: Index Rebuild and Cache Invalidation (20 min)
- [ ] Create `tests/integration/test_index_rebuild.py`
- [ ] Test full index rebuild
- [ ] Test incremental index update (file modified)
- [ ] Validate BM25 IDF recalculation
- **Dependencies**: All tasks 1-7 complete
- **Verification**: `pytest tests/integration/test_index_rebuild.py` passes

### INT-3: Performance Benchmarks (30 min)
- [ ] Create `tests/integration/test_performance_benchmarks.py`
- [ ] Validate query latency <2s for simple queries
- [ ] Validate query latency <10s for complex queries
- [ ] Validate memory usage <100MB for 10K chunks
- **Dependencies**: All tasks 1-7 complete
- **Verification**: `pytest tests/integration/test_performance_benchmarks.py` passes

---

## Quality Verification (Run Before Final Commit)

### QA-1: Run All Shell Tests (10 min)
- [ ] Execute `bash tests/shell/run_all_shell_tests.sh`
- [ ] Validate 18/18 shell tests pass
- **Dependencies**: All tasks 1-7 complete

### QA-2: Run All Unit Tests (10 min)
- [ ] Execute `pytest tests/unit/test_bm25_* tests/unit/test_hybrid_* tests/unit/test_knowledge_* tests/unit/test_reasoning_* tests/unit/test_display_* tests/unit/test_type_* tests/unit/test_hybrid_config.py`
- [ ] Validate 60/60 unit tests pass
- **Dependencies**: All tasks 1-7 complete

### QA-3: Run All Integration Tests (10 min)
- [ ] Execute `pytest tests/integration/`
- [ ] Validate 15/15 integration tests pass
- **Dependencies**: INT-1, INT-2, INT-3 complete

### QA-4: Type Check and Lint (5 min)
- [ ] Run `make type-check` (MyPy)
- [ ] Run `make lint` (Ruff)
- [ ] Fix any new type errors or lint warnings
- **Dependencies**: All code changes complete

### QA-5: Update Documentation (20 min)
- [ ] Update `docs/cli/CLI_USAGE_GUIDE.md` with new flags (--show-scores, --type)
- [ ] Update `docs/architecture/MEMORY_ARCHITECTURE.md` with BM25 tri-hybrid details
- [ ] Add BM25 section to `docs/KNOWLEDGE_BASE.md`
- [ ] Update `CHANGELOG.md` for v0.3.0
- **Dependencies**: All tasks 1-7 complete

---

## Summary

**Total Subtasks**: 45 subtasks across 7 parent tasks + 3 integration tests + 5 QA steps = **53 checklist items**

**Estimated Total Time**: 8-10 hours (as specified in PRD)

**Critical Path**: Tasks 1 → 2 → 6 → 7 (BM25 core → Staged retrieval → Display → Config)

**Parallel Work Possible**: Tasks 3, 4, 5 can be developed in parallel with Task 2

**Test Coverage**:
- 18 Shell Tests (acceptance criteria)
- 60 Unit Tests (TDD for pure functions)
- 15 Integration Tests (end-to-end validation)
- **Total: 93 tests**

**Success Criteria**: All shell tests pass, demonstrating exact match retrieval, staged architecture, knowledge/reasoning search, git metadata display, type filtering, and score transparency.

---

**Status**: ✅ **READY FOR IMPLEMENTATION**

**Next Step**: Start with Task 1.1 (Write Shell Tests for BM25 Exact Match)
