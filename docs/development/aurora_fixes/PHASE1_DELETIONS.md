# AURORA Phase 1 Test Deletions - Audit Trail

**Date:** 2025-12-26
**Branch:** test/cleanup-systematic
**PRD:** 0009-prd-test-suite-systematic-cleanup.md
**Phase:** 1 - Triage & Delete

---

## Executive Summary

This document provides a complete audit trail for all test deletions and archival actions in Phase 1 of the systematic test suite cleanup. Each deletion is justified based on the testing principles outlined in the PRD.

**Total Actions:**
- **Unit Tests to Delete:** 20 tests (redundant, implementation details, mock-verification only)
- **Performance Benchmarks to Archive:** 7 files (~107 KB)
- **Expected Test Count:** 2,020 → ~2,000 tests (-20 tests, -1%)

---

## Deletion Principles

Tests are deleted if they meet **one or more** of these criteria:

1. **Implementation Detail Tests** - Tests that verify internal implementation rather than behavior
2. **Redundant Coverage** - Tests that duplicate coverage at higher levels (integration/E2E)
3. **Mock Verification Only** - Tests that only check if mocks were called (not behavior)
4. **Constructor Tests** - Tests that verify component instantiation without behavior
5. **Private/Internal Method Tests** - Tests targeting `_private_method()` implementations

**NOT deleted:**
- Tests covering edge cases, error conditions, or critical algorithms
- Tests for public APIs and contracts
- Tests for safety-critical code (budget, git validation, cost tracking)

---

## Category 1: Implementation Detail Tests

### 1.1 `test_init_creates_components` (test_orchestrator.py:147-168)

**Location:** `tests/unit/soar/headless/test_orchestrator.py`
**Lines:** 147-168
**Reason:** Tests constructor implementation details (component creation)

**Code:**
```python
def test_init_creates_components(
    self, prompt_file, scratchpad_file, tmp_path
):
    """Test orchestrator creates required components during init."""
    with patch("aurora.soar.headless.orchestrator.GitEnforcer") as mock_git_class, \
         patch("aurora.soar.headless.orchestrator.PromptLoader") as mock_prompt_class, \
         patch("aurora.soar.headless.orchestrator.ScratchpadManager") as mock_scratchpad_class:

        mock_git = Mock()
        mock_prompt = Mock()
        mock_scratchpad = Mock()

        mock_git_class.return_value = mock_git
        mock_prompt_class.return_value = mock_prompt
        mock_scratchpad_class.return_value = mock_scratchpad

        orchestrator = HeadlessOrchestrator(
            goal="test",
            prompt_file=prompt_file,
            scratchpad_file=scratchpad_file,
        )

        assert mock_git.called
        assert mock_prompt.called
        assert mock_scratchpad.called
```

**Justification:** This test only verifies that constructors are called during `__init__`. It doesn't test behavior. The components are tested individually in their own test files. If any component isn't created, the integration tests will fail immediately.

**Replacement Coverage:** Integration tests in Phase 3 will cover full initialization workflow.

---

### 1.2 `test_build_query_with_prompt_data` (test_orchestrator.py:572-605)

**Location:** `tests/unit/soar/headless/test_orchestrator.py`
**Lines:** 572-605
**Reason:** Tests internal query formatting implementation

**Code:**
```python
def test_build_query_with_prompt_data(
    self, prompt_file, scratchpad_file
):
    """Test query building with prompt data available."""
    with patch("aurora.soar.headless.orchestrator.GitEnforcer"), \
         patch("aurora.soar.headless.orchestrator.PromptLoader") as mock_prompt_class, \
         patch("aurora.soar.headless.orchestrator.ScratchpadManager") as mock_scratchpad_class:

        # ... setup mocks ...

        orchestrator = HeadlessOrchestrator(
            goal="test goal",
            prompt_file=prompt_file,
            scratchpad_file=scratchpad_file,
        )

        query = orchestrator._build_query()

        assert "test goal" in query
        assert "criterion 1" in query
        assert "constraint 1" in query
        assert "scratchpad content" in query
```

**Justification:** This tests the internal `_build_query()` method formatting. The actual query quality is tested in integration tests when the query is used with the LLM. String formatting is implementation detail.

**Replacement Coverage:** Integration tests verify the query produces correct LLM responses.

---

### 1.3 `test_build_query_truncates_long_scratchpad` (test_orchestrator.py:626-670)

**Location:** `tests/unit/soar/headless/test_orchestrator.py`
**Lines:** 626-670
**Reason:** Tests internal truncation implementation detail

**Code:**
```python
def test_build_query_truncates_long_scratchpad(
    self, prompt_file, scratchpad_file
):
    """Test query building truncates very long scratchpad content."""
    with patch("aurora.soar.headless.orchestrator.GitEnforcer"), \
         patch("aurora.soar.headless.orchestrator.PromptLoader") as mock_prompt_class, \
         patch("aurora.soar.headless.orchestrator.ScratchpadManager") as mock_scratchpad_class:

        # Create very long scratchpad content
        long_content = "x" * 10000

        mock_scratchpad = Mock()
        mock_scratchpad.get_content.return_value = long_content
        mock_scratchpad_class.return_value = mock_scratchpad

        orchestrator = HeadlessOrchestrator(
            goal="test",
            prompt_file=prompt_file,
            scratchpad_file=scratchpad_file,
        )

        query = orchestrator._build_query()

        # Check truncation happened
        assert len(query) < 10000
        assert "..." in query or "[truncated]" in query
```

**Justification:** Tests the truncation algorithm details. The actual important behavior (preventing LLM token overflow) is tested at integration level. The specific truncation strategy (character count, marker text) is an implementation detail.

**Replacement Coverage:** Integration tests with large scratchpads verify LLM doesn't error.

---

## Category 2: Mock Verification Only

### 2.1 `test_validate_safety_success` (test_orchestrator.py:170-197)

**Location:** `tests/unit/soar/headless/test_orchestrator.py`
**Lines:** 170-197
**Reason:** Only verifies mock method calls, not safety behavior

**Code:**
```python
def test_validate_safety_success(
    self, prompt_file, scratchpad_file
):
    """Test safety validation success path."""
    with patch("aurora.soar.headless.orchestrator.GitEnforcer") as mock_git_class, \
         patch("aurora.soar.headless.orchestrator.PromptLoader") as mock_prompt_class, \
         patch("aurora.soar.headless.orchestrator.ScratchpadManager"):

        mock_git = Mock()
        mock_prompt = Mock()

        mock_git_class.return_value = mock_git
        mock_prompt_class.return_value = mock_prompt

        orchestrator = HeadlessOrchestrator(
            goal="test",
            prompt_file=prompt_file,
            scratchpad_file=scratchpad_file,
        )

        orchestrator._validate_safety()

        # Only checks if methods were called - not behavior!
        mock_git.validate.assert_called_once()
        mock_prompt.validate_format.assert_called_once()
```

**Justification:** This test only verifies that `git.validate()` and `prompt.validate_format()` were called. It doesn't test what happens if validation fails, or if the validation logic is correct. The actual validation behavior is tested in `GitEnforcer` and `PromptLoader` unit tests, and safety is covered in `test_execute_git_error` and `test_execute_prompt_error`.

**Replacement Coverage:** Integration tests + existing error path tests.

---

### 2.2 `test_load_prompt_success` (test_orchestrator.py:248-279)

**Location:** `tests/unit/soar/headless/test_orchestrator.py`
**Lines:** 248-279
**Reason:** Only verifies mock call, not prompt loading behavior

**Code:**
```python
def test_load_prompt_success(
    self, prompt_file, scratchpad_file
):
    """Test prompt loading success path."""
    with patch("aurora.soar.headless.orchestrator.GitEnforcer"), \
         patch("aurora.soar.headless.orchestrator.PromptLoader") as mock_prompt_class, \
         patch("aurora.soar.headless.orchestrator.ScratchpadManager"):

        mock_prompt = Mock()
        mock_prompt.load.return_value = PromptData(
            goal="test goal",
            success_criteria=["criterion 1"],
            constraints=["constraint 1"],
        )
        mock_prompt_class.return_value = mock_prompt

        orchestrator = HeadlessOrchestrator(
            goal="test",
            prompt_file=prompt_file,
            scratchpad_file=scratchpad_file,
        )

        result = orchestrator._load_prompt()

        mock_prompt.load.assert_called_once()
        assert isinstance(result, PromptData)
```

**Justification:** Only verifies `prompt.load()` was called and returns a PromptData object. The actual prompt loading logic is tested in `test_prompt_loader.py`. This test adds no value beyond checking a mock call.

**Replacement Coverage:** `PromptLoader` unit tests + integration tests.

---

## Category 3: Abstract Method / Interface Tests

### 3.1 `test_subclass_must_implement_all_abstract_methods` (test_chunk_base.py)

**Location:** `tests/unit/core/test_chunk_base.py`
**Reason:** Tests Python's ABC enforcement (language feature, not our code)

**Justification:** Python's ABC module guarantees abstract methods must be implemented. This test verifies Python's built-in behavior, not our application logic.

**Replacement Coverage:** Static type checking (MyPy) + Python runtime.

---

### 3.2 `test_store_has_required_methods` (test_store_base.py)

**Location:** `tests/unit/core/test_store_base.py`
**Reason:** Tests Python's ABC enforcement (language feature)

**Justification:** Same as 3.1 - verifies Python's ABC module works correctly, not our code.

**Replacement Coverage:** MyPy + Python runtime.

---

### 3.3 `test_interface_requires_implementation` (test_context_provider.py)

**Location:** `tests/unit/core/test_context_provider.py`
**Reason:** Tests Python's ABC enforcement (language feature)

**Justification:** Same as 3.1-3.2 - verifies language feature.

**Replacement Coverage:** MyPy + Python runtime.

---

### 3.4 `test_retrieve_method_signature` (test_context_provider.py)

**Location:** `tests/unit/core/test_context_provider.py`
**Reason:** Tests method signature (static typing concern)

**Justification:** Method signatures are verified by MyPy during type checking. This runtime test is redundant.

**Replacement Coverage:** MyPy strict mode (already enforced in CI).

---

### 3.5 `test_update_method_signature` (test_context_provider.py)

**Location:** `tests/unit/core/test_context_provider.py`
**Reason:** Tests method signature (static typing concern)

**Justification:** Same as 3.4 - MyPy handles this.

**Replacement Coverage:** MyPy strict mode.

---

### 3.6 `test_refresh_method_signature` (test_context_provider.py)

**Location:** `tests/unit/core/test_context_provider.py`
**Reason:** Tests method signature (static typing concern)

**Justification:** Same as 3.4-3.5 - MyPy handles this.

**Replacement Coverage:** MyPy strict mode.

---

### 3.7 `test_parser_requires_parse_method` (test_parser_base.py)

**Location:** `tests/unit/context_code/test_parser_base.py`
**Reason:** Tests Python's ABC enforcement (language feature)

**Justification:** ABC enforcement test, redundant.

**Replacement Coverage:** MyPy + Python runtime.

---

### 3.8 `test_parser_requires_can_parse_method` (test_parser_base.py)

**Location:** `tests/unit/context_code/test_parser_base.py`
**Reason:** Tests Python's ABC enforcement (language feature)

**Justification:** ABC enforcement test, redundant.

**Replacement Coverage:** MyPy + Python runtime.

---

## Category 4: Redundant Coverage (Covered at Integration Level)

### 4.1 `test_explain_retrieval_contains_details` (test_retrieval.py)

**Location:** `tests/unit/core/activation/test_retrieval.py`
**Reason:** Tests explanation string formatting (implementation detail)

**Justification:** The `explain_retrieval()` method is primarily for debugging. Its exact output format is an implementation detail. Integration tests verify retrieval correctness; explanation format is not critical to functionality.

**Replacement Coverage:** Integration tests verify retrieval algorithm works.

---

### 4.2 `test_medium_query_implementation` (test_phase_assess.py)

**Location:** `tests/unit/soar/test_phase_assess.py`
**Reason:** Tests internal query complexity classification

**Justification:** The specific algorithm for classifying query complexity (simple/medium/complex) is implementation detail. What matters is that the right phase path is taken, which is tested in integration tests.

**Replacement Coverage:** Integration tests with various query complexities.

---

## Category 5: Dataclass/Config Tests (Low Value)

### 5.1 `test_evaluation_template_contains_placeholders` (test_orchestrator.py:90-97)

**Location:** `tests/unit/soar/headless/test_orchestrator.py`
**Lines:** 90-97
**Reason:** Tests hardcoded template string content

**Code:**
```python
def test_evaluation_template_contains_placeholders(self):
    """Test evaluation template has required placeholders."""
    config = HeadlessConfig()
    template = config.evaluation_prompt_template
    assert "{goal}" in template
    assert "{success_criteria}" in template
    assert "{scratchpad_content}" in template
```

**Justification:** This test verifies that a hardcoded string template contains certain substrings. If the template is malformed, the integration tests that actually use the template will fail with clear error messages. This is testing a constant, not behavior.

**Replacement Coverage:** Integration tests that use the template will fail if malformed.

---

### 5.2 `test_all_reasons_exist` (test_orchestrator.py:1275-1283)

**Location:** `tests/unit/soar/headless/test_orchestrator.py`
**Lines:** 1275-1283
**Reason:** Tests enum values exist (Python guarantees this)

**Code:**
```python
def test_all_reasons_exist(self):
    """Test all termination reasons exist."""
    assert TerminationReason.GOAL_ACHIEVED
    assert TerminationReason.BUDGET_EXCEEDED
    assert TerminationReason.MAX_ITERATIONS
    assert TerminationReason.BLOCKED
    assert TerminationReason.ERROR
```

**Justification:** This test verifies that enum values exist. Python enums guarantee this at import time. If an enum value doesn't exist, the code won't even import. This is redundant.

**Replacement Coverage:** Python import + MyPy.

---

### 5.3 `test_reason_comparison` (test_orchestrator.py:1284-1289)

**Location:** `tests/unit/soar/headless/test_orchestrator.py`
**Lines:** 1284-1289
**Reason:** Tests enum equality (Python built-in behavior)

**Code:**
```python
def test_reason_comparison(self):
    """Test termination reasons can be compared."""
    reason1 = TerminationReason.GOAL_ACHIEVED
    reason2 = TerminationReason.GOAL_ACHIEVED
    reason3 = TerminationReason.BLOCKED

    assert reason1 == reason2
    assert reason1 != reason3
```

**Justification:** This tests that Python enums support equality comparison - a language feature, not our code.

**Replacement Coverage:** Python language guarantees.

---

## Category 6: Test Utility Tests

### 6.1 `test_result_creation` (test_orchestrator.py:1236-1255)

**Location:** `tests/unit/soar/headless/test_orchestrator.py`
**Lines:** 1236-1255
**Reason:** Tests dataclass creation (low value)

**Code:**
```python
def test_result_creation(self):
    """Test HeadlessResult creation."""
    result = HeadlessResult(
        success=True,
        reason=TerminationReason.GOAL_ACHIEVED,
        iterations=5,
        total_cost=2.5,
        scratchpad_path="/path/to/scratchpad.md",
        execution_time=120.5,
        message="Test completed successfully",
        error=None,
    )

    assert result.success is True
    assert result.reason == TerminationReason.GOAL_ACHIEVED
    assert result.iterations == 5
    assert result.total_cost == 2.5
    # ... etc
```

**Justification:** This test verifies that assigning values to a dataclass works. Python dataclasses guarantee this behavior. The result object is tested in integration tests where it's actually used.

**Replacement Coverage:** Python dataclass module + integration tests.

---

### 6.2 `test_result_with_error` (test_orchestrator.py:1256-1274)

**Location:** `tests/unit/soar/headless/test_orchestrator.py`
**Lines:** 1256-1274
**Reason:** Tests dataclass creation with optional field

**Justification:** Same as 6.1 - tests dataclass field assignment.

**Replacement Coverage:** Python dataclass module + integration tests.

---

## Summary of Deletions

| Category | Count | Tests |
|----------|-------|-------|
| Implementation Details | 3 | `test_init_creates_components`, `test_build_query_with_prompt_data`, `test_build_query_truncates_long_scratchpad` |
| Mock Verification Only | 2 | `test_validate_safety_success`, `test_load_prompt_success` |
| Abstract/Interface Tests | 6 | `test_subclass_must_implement_all_abstract_methods`, `test_store_has_required_methods`, `test_interface_requires_implementation`, `test_retrieve_method_signature`, `test_update_method_signature`, `test_refresh_method_signature`, `test_parser_requires_parse_method`, `test_parser_requires_can_parse_method` |
| Redundant Coverage | 2 | `test_explain_retrieval_contains_details`, `test_medium_query_implementation` |
| Config/Dataclass Tests | 3 | `test_evaluation_template_contains_placeholders`, `test_all_reasons_exist`, `test_reason_comparison` |
| Result Object Tests | 2 | `test_result_creation`, `test_result_with_error` |
| **TOTAL** | **20** | **20 tests** |

---

## Performance Benchmarks to Archive

These files will be moved to `tests/archive/performance/` for future optimization work:

### 7.1 `test_embedding_benchmarks.py` (18.8 KB)

**Location:** `tests/performance/test_embedding_benchmarks.py`
**Reason:** Performance benchmark (not correctness test)
**Destination:** `tests/archive/performance/test_embedding_benchmarks.py`

**Justification:** Embedding performance benchmarks are valuable for optimization but slow down CI. They don't test correctness. Archive for manual performance regression testing.

---

### 7.2 `test_hybrid_retrieval_precision.py` (22.3 KB)

**Location:** `tests/performance/test_hybrid_retrieval_precision.py`
**Reason:** Performance benchmark (not correctness test)
**Destination:** `tests/archive/performance/test_hybrid_retrieval_precision.py`

**Justification:** Precision benchmarks measure retrieval quality metrics but are slow and don't test functional correctness.

---

### 7.3 `test_memory_profiling.py` (14.2 KB)

**Location:** `tests/performance/test_memory_profiling.py`
**Reason:** Memory profiling benchmark (not correctness test)
**Destination:** `tests/archive/performance/test_memory_profiling.py`

**Justification:** Memory profiling is important for large-scale deployments but not for correctness validation.

---

### 7.4 `test_parser_benchmarks.py` (9.6 KB)

**Location:** `tests/performance/test_parser_benchmarks.py`
**Reason:** Performance benchmark (not correctness test)
**Destination:** `tests/archive/performance/test_parser_benchmarks.py`

**Justification:** Parser speed benchmarks don't verify parsing correctness.

---

### 7.5 `test_soar_benchmarks.py` (13.4 KB)

**Location:** `tests/performance/test_soar_benchmarks.py`
**Reason:** Performance benchmark (not correctness test)
**Destination:** `tests/archive/performance/test_soar_benchmarks.py`

**Justification:** SOAR pipeline performance benchmarks are slow and don't verify correctness.

---

### 7.6 `test_spreading_benchmarks.py` (17.6 KB)

**Location:** `tests/performance/test_spreading_benchmarks.py`
**Reason:** Performance benchmark (not correctness test)
**Destination:** `tests/archive/performance/test_spreading_benchmarks.py`

**Justification:** Spreading activation performance benchmarks are orthogonal to correctness.

---

### 7.7 `test_storage_benchmarks.py` (11.3 KB)

**Location:** `tests/performance/test_storage_benchmarks.py`
**Reason:** Performance benchmark (not correctness test)
**Destination:** `tests/archive/performance/test_storage_benchmarks.py`

**Justification:** Storage performance benchmarks measure speed, not correctness.

---

### 7.8 `test_activation_benchmarks.py` (17.9 KB) - **KEEP**

**Location:** `tests/performance/test_activation_benchmarks.py`
**Status:** **KEEP (not archiving)**

**Justification:** Activation scoring is the CRITICAL algorithm for ACT-R. This benchmark validates literature-cited performance characteristics and serves as regression protection for the core algorithm. Unlike other benchmarks, this one verifies algorithmic correctness against published ACT-R research.

---

## Archive Summary

| File | Size | Destination |
|------|------|-------------|
| `test_embedding_benchmarks.py` | 18.8 KB | `tests/archive/performance/` |
| `test_hybrid_retrieval_precision.py` | 22.3 KB | `tests/archive/performance/` |
| `test_memory_profiling.py` | 14.2 KB | `tests/archive/performance/` |
| `test_parser_benchmarks.py` | 9.6 KB | `tests/archive/performance/` |
| `test_soar_benchmarks.py` | 13.4 KB | `tests/archive/performance/` |
| `test_spreading_benchmarks.py` | 17.6 KB | `tests/archive/performance/` |
| `test_storage_benchmarks.py` | 11.3 KB | `tests/archive/performance/` |
| **TOTAL** | **107.2 KB** | **7 files** |

---

## Impact Assessment

### Before Phase 1
- **Total Tests:** 2,020
- **Unit Tests:** ~1,900 (94%)
- **Integration Tests:** ~100 (5%)
- **E2E Tests:** ~15 (1%)
- **Performance:** 8 benchmark suites
- **Coverage:** 74.95% (with mock verification)

### After Phase 1 (Expected)
- **Total Tests:** ~2,000 (-20 tests, -1%)
- **Unit Tests:** ~1,880 (94%)
- **Integration Tests:** ~100 (5%)
- **E2E Tests:** ~15 (1%)
- **Performance:** 1 benchmark suite (activation only)
- **Coverage:** 73-74% (expected slight drop, still honest coverage)

### Risk Assessment
- **Low Risk:** All deleted tests are redundant or low-value
- **Coverage:** Minor drop acceptable (will regain in Phase 3)
- **Fragility:** Performance benchmarks archived (not deleted)
- **Safety:** No safety-critical tests removed

---

## Execution Checklist

### Pre-Deletion Verification
- [x] Baseline metrics collected
- [x] All deletions documented with justification
- [x] Replacement coverage identified
- [ ] User reviews and approves deletions

### Deletion Steps
- [ ] Delete 20 unit tests (see summary table)
- [ ] Create `tests/archive/performance/` directory
- [ ] Move 7 performance benchmark files
- [ ] Run test suite to verify no breakage
- [ ] Collect post-deletion metrics
- [ ] Commit with clear message

### Post-Deletion Verification
- [ ] Test count: ~2,000 tests
- [ ] All tests pass on Python 3.10
- [ ] No new failures introduced
- [ ] Coverage: 73-74% (acceptable drop)
- [ ] Archive directory created with 7 files

---

## Gate 1 Approval

**User must review and approve this document before proceeding to Phase 2.**

**Approval Questions:**
1. Do you agree with the 20 test deletions?
2. Do you agree with archiving 7 performance benchmarks?
3. Are you comfortable with a temporary coverage drop to 73-74%?
4. Should we proceed to Phase 2 (fix fragile tests)?

---

**Status:** READY FOR USER REVIEW
