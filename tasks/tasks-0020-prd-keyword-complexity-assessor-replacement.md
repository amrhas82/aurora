## Relevant Files

### Source Files to Port
- `/home/hamr/PycharmProjects/aurora/docs/development/complexity_assess/complexity_assessor.py` - Validated complexity assessor implementation (96% accuracy)
- `/home/hamr/PycharmProjects/aurora/docs/development/complexity_assess/test_complexity_assessor.py` - Comprehensive unit tests for the new assessor
- `/home/hamr/PycharmProjects/aurora/docs/development/complexity_assess/test_corpus.py` - 101-prompt test corpus with expected classifications
- `/home/hamr/PycharmProjects/aurora/docs/development/complexity_assess/evaluate.py` - Evaluation framework for accuracy reporting

### Destination Files (Implementation)
- `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/phases/assess.py` - Main implementation file (to be replaced)
- `/home/hamr/PycharmProjects/aurora/tests/unit/soar/test_phase_assess.py` - Unit tests (to be replaced)
- `/home/hamr/PycharmProjects/aurora/tests/unit/soar/test_corpus_assess.py` - Test corpus (new file)
- `/home/hamr/PycharmProjects/aurora/tests/unit/soar/evaluate_assess.py` - Evaluation framework (new file, optional)

### Old Test Files to Remove
- `/home/hamr/PycharmProjects/aurora/tests/unit/test_assess.py` - Old unit tests for assess.py
- `/home/hamr/PycharmProjects/aurora/tests/unit/soar/test_phase_assess.py` - Old tests (to be replaced)

### Integration Points
- `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/orchestrator.py` - SOAR orchestrator (uses assess_complexity)
- `/home/hamr/PycharmProjects/aurora/src/aurora/mcp/tools.py` - MCP server tools (primary consumer)
- `/home/hamr/PycharmProjects/aurora/tests/e2e/test_e2e_complexity_assessment.py` - E2E tests (to be updated)

### Notes

**Testing Framework**: pytest with markers `@pytest.mark.soar` and `@pytest.mark.critical`

**Architectural Patterns**:
- Two-tier assessment: Tier 1 (keyword-based, fast) → Tier 2 (LLM fallback for borderline cases)
- Interface contract: `assess_complexity(query: str, llm_client: LLMClient | None = None) -> dict`
- Return dict must include: `complexity`, `confidence`, `method`, `reasoning`, `score`

**Implementation Strategy**:
- Port core algorithm from `complexity_assessor.py` to replace `_assess_tier1_keyword()` in `assess.py`
- Preserve existing `_assess_tier2_llm()` function
- Preserve existing `assess_complexity()` public interface
- Add CRITICAL level support (not in source, needs implementation)
- Update thresholds from source: SIMPLE_THRESHOLD=11, MEDIUM_THRESHOLD=28

**Potential Challenges**:
- Score normalization: Source uses raw integer scores (0-100+), existing interface expects 0.0-1.0
- Complexity level casing: Source uses lowercase ('simple'), existing uses uppercase ('SIMPLE')
- CRITICAL keyword handling: Needs to override score-based classification
- LLM fallback integration: Preserve existing Tier 2 logic while replacing Tier 1

**Test Corpus Statistics** (from source):
- Total: 101 prompts (simple=25, medium=25, complex=51)
- Categories: lookup, command, analysis, debug, edit, refactor, feature, architecture, migration, integration, workflow, edge cases, real-world
- Validated accuracy: 96% overall (stretch goal: 90%, requirement: 85%)

**Performance Requirements**:
- Single prompt latency: <1ms target (~0.5ms expected)
- Long prompt (500+ chars): <5ms target (~2.5ms expected)
- Throughput: >1000/sec target (~2000/sec expected)

## Tasks

- [ ] 1.0 TDD Phase 1: Port and Prepare Test Infrastructure
  - [ ] 1.1 Create new test corpus file at `/home/hamr/PycharmProjects/aurora/tests/unit/soar/test_corpus_assess.py` by copying content from `/home/hamr/PycharmProjects/aurora/docs/development/complexity_assess/test_corpus.py`
  - [ ] 1.2 Verify test corpus structure: 101 prompts with (prompt, expected_level, category, notes) tuples
  - [ ] 1.3 Add helper functions `get_corpus()`, `get_by_category()`, `get_by_level()` to test corpus file
  - [ ] 1.4 Create evaluation framework file at `/home/hamr/PycharmProjects/aurora/tests/unit/soar/evaluate_assess.py` by porting from `/home/hamr/PycharmProjects/aurora/docs/development/complexity_assess/evaluate.py`
  - [ ] 1.5 Update evaluation framework imports to use `from aurora_soar.phases.assess import assess_complexity` and `from tests.unit.soar.test_corpus_assess import TEST_CORPUS`
  - [ ] 1.6 Add `EvaluationResult` dataclass and `evaluate_corpus()` function to evaluation framework
  - [ ] 1.7 Add reporting functions: `print_report()`, `analyze_misclassifications()`, `_find_optimal_thresholds()`
  - [ ] 1.8 Verify evaluation framework can be imported without errors (tests will fail, but imports must work)

- [ ] 2.0 TDD Phase 1: Remove Old Tests and Verify Failures
  - [ ] 2.1 Back up existing test file `/home/hamr/PycharmProjects/aurora/tests/unit/soar/test_phase_assess.py` to `/home/hamr/PycharmProjects/aurora/tests/unit/soar/test_phase_assess.py.backup`
  - [ ] 2.2 Delete old test file `/home/hamr/PycharmProjects/aurora/tests/unit/test_assess.py` if it exists
  - [ ] 2.3 Create new test file `/home/hamr/PycharmProjects/aurora/tests/unit/soar/test_phase_assess.py` by porting from `/home/hamr/PycharmProjects/aurora/docs/development/complexity_assess/test_complexity_assessor.py`
  - [ ] 2.4 Update imports in new test file: `from aurora_soar.phases.assess import ComplexityAssessor, AssessmentResult, assess_complexity` (note: these don't exist yet, will be added in Phase 2)
  - [ ] 2.5 Update imports to include evaluation: `from tests.unit.soar.evaluate_assess import evaluate_corpus`
  - [ ] 2.6 Update imports to include test corpus: `from tests.unit.soar.test_corpus_assess import TEST_CORPUS`
  - [ ] 2.7 Port test class `TestComplexityAssessor` with all basic functionality tests (empty prompt, whitespace, result fields, to_dict serialization)
  - [ ] 2.8 Port parametrized tests for simple prompts (lookup/display operations): `test_simple_prompts()` with 6+ examples from corpus
  - [ ] 2.9 Port parametrized tests for medium prompts (analysis, moderate edits): `test_medium_prompts()` with 5+ examples from corpus
  - [ ] 2.10 Port parametrized tests for complex prompts (major implementations, architecture): `test_complex_prompts()` with 5+ examples from corpus
  - [ ] 2.11 Port pattern detection tests: `test_trivial_edit_pattern()`, `test_complex_verb_detection()`, `test_analysis_verb_detection()`, `test_scope_expansion_detection()`, `test_constraint_detection()`, `test_sequence_marker_detection()`, `test_bounded_scope_detection()`, `test_integration_pattern()`, `test_complex_feature_pattern()`
  - [ ] 2.12 Port threshold tests: `test_simple_threshold()` (score <= 11), `test_medium_threshold()` (score 12-28)
  - [ ] 2.13 Port corpus accuracy tests: `test_corpus_accuracy_above_85_percent()` (hard requirement), `test_corpus_accuracy_above_90_percent()` (stretch goal, can skip), `test_no_level_has_zero_accuracy()`
  - [ ] 2.14 Port edge case tests in `TestEdgeCases` class: very long prompts, unicode, special characters, code blocks, numbered lists, multi-question detection
  - [ ] 2.15 Port convenience function test: `test_assess_prompt_function()`
  - [ ] 2.16 Run new tests against current implementation: `pytest tests/unit/soar/test_phase_assess.py -v` and verify they FAIL (proving old implementation is deficient)
  - [ ] 2.17 Document failure output showing current implementation does not pass corpus accuracy tests (expected: ~60-70% accuracy on current vs. 96% target)
  - [ ] 2.18 Run evaluation framework: `python tests/unit/soar/evaluate_assess.py` and capture baseline metrics report (overall accuracy, per-level accuracy, confusion matrix, misclassifications)

- [ ] 3.0 TDD Phase 2: Port Core Implementation Module
  - [ ] 3.1 Back up existing implementation: `cp packages/soar/src/aurora_soar/phases/assess.py packages/soar/src/aurora_soar/phases/assess.py.backup`
  - [ ] 3.2 Open source file `/home/hamr/PycharmProjects/aurora/docs/development/complexity_assess/complexity_assessor.py` and target file `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/phases/assess.py` side-by-side for porting
  - [ ] 3.3 Add `ComplexityLevel` IntEnum to `assess.py` after imports (lines ~30): `SIMPLE=1, MEDIUM=2, COMPLEX=3` (note: CRITICAL will be added in Task 4.0)
  - [ ] 3.4 Add `AssessmentResult` dataclass to `assess.py` after ComplexityLevel: fields = `level: Literal['simple', 'medium', 'complex']`, `score: int`, `confidence: float`, `signals: list[str]`, `breakdown: dict`
  - [ ] 3.5 Add `to_dict()` method to AssessmentResult dataclass for serialization
  - [ ] 3.6 Create `ComplexityAssessor` class in `assess.py` (replaces `_assess_tier1_keyword` function)
  - [ ] 3.7 Port all keyword dictionaries to ComplexityAssessor class attributes: `SIMPLE_VERBS` (21 verbs), `MEDIUM_VERBS` (20 verbs), `ANALYSIS_VERBS` (20 verbs), `COMPLEX_VERBS` (17 verbs)
  - [ ] 3.8 Port scope and constraint keyword sets: `SCOPE_KEYWORDS` (16 keywords), `CONSTRAINT_PHRASES` (19 phrases), `SEQUENCE_MARKERS` (13 markers), `COMPOUND_MARKERS` (10 markers)
  - [ ] 3.9 Port technical domain keywords: `TECHNICAL_DOMAINS` (21 domains), `COMPLEX_NOUNS` (25 nouns)
  - [ ] 3.10 Port question pattern regexes: `SIMPLE_QUESTION_PATTERNS` (7 patterns), `COMPLEX_QUESTION_PATTERNS` (6 patterns)
  - [ ] 3.11 Add threshold constants to ComplexityAssessor: `SIMPLE_THRESHOLD = 11`, `MEDIUM_THRESHOLD = 28` (calibrated from corpus analysis)
  - [ ] 3.12 Port main `assess()` method to ComplexityAssessor: handles empty prompts, calculates all 7 dimension scores, applies multiplier, determines level from thresholds, calculates confidence
  - [ ] 3.13 Port `_score_lexical()` method: word count scoring (0-25+ points), sentence count, question marks, comma density, formal punctuation (semicolons/colons)
  - [ ] 3.14 Port `_score_keywords()` method: simple verb penalty (-10 max), medium verb bonus (+12 each), analysis verb bonus (+15 each, capped at +20), complex verb bonus (+25 each), integration pattern detection, complex noun combinations, trivial edit pattern detection (with score reduction), bounded scope detection (with score reduction)
  - [ ] 3.15 Port `_score_scope()` method: scope expansion keywords (+12 each), file/path references, directory patterns, verbose simple pattern detection (with score reduction for false positives)
  - [ ] 3.16 Port `_score_constraints()` method: constraint phrase detection (+12 each), compound requirement markers (+10 each), sequence markers (+8 each), negative constraints (+6 each)
  - [ ] 3.17 Port `_score_structure()` method: numbered list detection (+10 per item), bullet points (+8 per item), code blocks (+5 each), success criteria patterns, conditional logic detection (+10 per conditional)
  - [ ] 3.18 Port `_score_domain()` method: technical domain matches (+5 single domain, +8 per domain for multi-domain), framework/library detection (+5 per framework)
  - [ ] 3.19 Port `_score_question_type()` method: simple question pattern penalty (-8), complex question pattern bonus (+15), "how to" pattern detection (+8 for medium)
  - [ ] 3.20 Port `_calculate_multiplier()` method: compound complexity multiplier (1.0 base, +0.2 for 3+ complex indicators, +0.2 for 5+ complex indicators, -0.1 for simple indicators only, clamped to [0.7, 1.5])
  - [ ] 3.21 Port `_calculate_confidence()` method: distance from thresholds, signal consistency bonus, final confidence range [0.5, 0.95]
  - [ ] 3.22 Add `assess_prompt()` convenience function at module level: creates ComplexityAssessor instance and calls assess()
  - [ ] 3.23 Replace `_assess_tier1_keyword()` function with new implementation that wraps ComplexityAssessor
  - [ ] 3.24 Update `_assess_tier1_keyword()` signature to return `(complexity_level: str, score: float, confidence: float)` to maintain compatibility
  - [ ] 3.25 Implement adapter logic in `_assess_tier1_keyword()`: create ComplexityAssessor, call assess(), convert result.level to uppercase, normalize result.score to 0.0-1.0 range (divide by 100 or use configured normalization), return tuple
  - [ ] 3.26 Update module docstring to reflect new implementation: "Two-tier assessment using keyword-based classification (96% accuracy on 101-prompt corpus) with LLM fallback for borderline cases"
  - [ ] 3.27 Update `__all__` export to include: `assess_complexity`, `ComplexityAssessor`, `AssessmentResult`, `ComplexityLevel`
  - [ ] 3.28 Run unit tests: `pytest tests/unit/soar/test_phase_assess.py -v` and verify simple/medium/complex tests PASS (CRITICAL tests will still fail until Task 4.0)
  - [ ] 3.29 Run evaluation framework: `python tests/unit/soar/evaluate_assess.py` and verify accuracy >= 85% (target: 96%)

- [ ] 4.0 TDD Phase 2: Add CRITICAL Level Support
  - [ ] 4.1 Update `ComplexityLevel` IntEnum in `assess.py` to add `CRITICAL = 4`
  - [ ] 4.2 Update `AssessmentResult` dataclass level field to include 'critical': `level: Literal['simple', 'medium', 'complex', 'critical']`
  - [ ] 4.3 Preserve existing `CRITICAL_KEYWORDS` set from old implementation (security, vulnerability, authentication, production, etc.) - do not replace, keep as-is
  - [ ] 4.4 Add `_detect_critical()` method to ComplexityAssessor class: checks if any CRITICAL_KEYWORDS match in query (case-insensitive word boundary matching)
  - [ ] 4.5 Update `ComplexityAssessor.assess()` method to call `_detect_critical()` BEFORE calculating dimension scores
  - [ ] 4.6 Implement critical override logic in `assess()`: if critical keywords detected, set level='critical', confidence=0.95, score=(raw score or high value), add signal 'critical_keyword_detected'
  - [ ] 4.7 Update threshold determination logic in `assess()` to handle 4 levels: score <= 11 = simple, score 12-28 = medium, score >= 29 = complex, critical keyword override = critical
  - [ ] 4.8 Add test prompts for CRITICAL level to test corpus: "fix security vulnerability in authentication", "production outage emergency", "data breach investigation", "encrypt sensitive payment data"
  - [ ] 4.9 Write test case `test_critical_keyword_detection()` in test_phase_assess.py: verify CRITICAL_KEYWORDS trigger critical level with high confidence (>= 0.9)
  - [ ] 4.10 Write test case `test_critical_overrides_score()`: verify that even low-scoring prompts with critical keywords are classified as CRITICAL (e.g., "fix security bug" scores low but is CRITICAL)
  - [ ] 4.11 Write test case `test_critical_routing()`: verify CRITICAL routes same as COMPLEX for escalation purposes (check orchestrator routing decision, not assessment itself)
  - [ ] 4.12 Update evaluation framework to handle CRITICAL level in confusion matrix and per-level accuracy reporting
  - [ ] 4.13 Run unit tests: `pytest tests/unit/soar/test_phase_assess.py::TestComplexityAssessor::test_critical_keyword_detection -v` and verify PASS
  - [ ] 4.14 Run full unit tests: `pytest tests/unit/soar/test_phase_assess.py -v` and verify all tests PASS including CRITICAL tests

- [ ] 5.0 TDD Phase 2: Port LLM Tier 2 Fallback
  - [ ] 5.1 Verify existing `_assess_tier2_llm()` function is preserved in `assess.py` (do not modify unless necessary)
  - [ ] 5.2 Verify existing `assess_complexity()` public function signature is preserved: `assess_complexity(query: str, llm_client: LLMClient | None = None) -> dict[str, Any]`
  - [ ] 5.3 Update `assess_complexity()` to call new `_assess_tier1_keyword()` implementation (which now wraps ComplexityAssessor)
  - [ ] 5.4 Verify LLM fallback trigger logic: confidence < 0.8 OR score in borderline range [0.4, 0.6] (normalized score)
  - [ ] 5.5 Update `assess_complexity()` to handle new return format from `_assess_tier1_keyword()`: complexity level (uppercase), normalized score (0.0-1.0), confidence (0.0-1.0)
  - [ ] 5.6 Verify `assess_complexity()` builds keyword_result dict correctly for LLM call: includes complexity, score, confidence
  - [ ] 5.7 Verify `assess_complexity()` calls `_assess_tier2_llm()` when borderline/low confidence and llm_client is provided
  - [ ] 5.8 Verify `assess_complexity()` return dict includes all required fields: complexity (uppercase), confidence, method ("keyword" or "llm"), reasoning (string explanation), score (0.0-1.0 normalized), optional: recommended_verification, keyword_fallback, llm_verification_needed
  - [ ] 5.9 Add test case `test_llm_fallback_triggered_low_confidence()`: verify LLM fallback is triggered when keyword confidence < 0.8
  - [ ] 5.10 Add test case `test_llm_fallback_triggered_borderline_score()`: verify LLM fallback is triggered when score in [0.4, 0.6] range
  - [ ] 5.11 Add test case `test_llm_fallback_not_available()`: verify graceful handling when llm_client=None and fallback needed (use keyword result with warning)
  - [ ] 5.12 Add test case `test_llm_fallback_critical_keywords()`: verify CRITICAL keywords have high confidence (>= 0.9) and do NOT trigger LLM fallback (cost optimization)
  - [ ] 5.13 Verify existing `_assess_tier2_llm()` integration with reasoning prompt templates works correctly (no changes needed if preserved)
  - [ ] 5.14 Run unit tests: `pytest tests/unit/soar/test_phase_assess.py -v -k "llm_fallback"` and verify LLM fallback tests PASS

- [ ] 6.0 TDD Phase 3: Verification and Integration
  - [ ] 6.1 Run full unit test suite for assess module: `pytest tests/unit/soar/test_phase_assess.py -v` and verify ALL tests PASS (100% pass rate required)
  - [ ] 6.2 Run full unit test suite for old test file location: `pytest tests/unit/test_assess.py -v` (should not exist anymore, verify removal)
  - [ ] 6.3 Run evaluation framework with final implementation: `python tests/unit/soar/evaluate_assess.py` and capture final metrics
  - [ ] 6.4 Verify overall accuracy >= 90% (requirement: 85%, stretch goal: 90%, validated baseline: 96%)
  - [ ] 6.5 Verify per-level accuracy: simple >= 85%, medium >= 85%, complex >= 85%
  - [ ] 6.6 Review confusion matrix for misclassification patterns (over-classification vs. under-classification)
  - [ ] 6.7 Review misclassification list and document edge cases (if any prompts consistently misclassified)
  - [ ] 6.8 Run performance benchmarks: measure single prompt latency with `timeit` or pytest-benchmark (target: <1ms, expected: ~0.5ms)
  - [ ] 6.9 Run performance benchmarks for long prompts (500+ chars): verify <5ms latency
  - [ ] 6.10 Update E2E test expectations in `tests/e2e/test_e2e_complexity_assessment.py`: tests that were EXPECTED TO FAIL should now PASS
  - [ ] 6.11 Run E2E tests: `pytest tests/e2e/test_e2e_complexity_assessment.py -v` and verify tests that previously failed due to Issue #6 now PASS
  - [ ] 6.12 Verify orchestrator integration: check that `aurora_soar/orchestrator.py` calls `assess_complexity()` and receives correct return format (no code changes needed if interface preserved)
  - [ ] 6.13 Run integration tests that depend on complexity assessment: `pytest tests/integration/ -v -k "complexity or assess"` and verify PASS
  - [ ] 6.14 Run full SOAR test suite: `pytest tests/unit/soar/ -v -m "soar or critical"` and verify no regressions
  - [ ] 6.15 Run full project test suite: `pytest tests/ -v --tb=short` and verify overall pass rate >= 97% (current baseline)
  - [ ] 6.16 Verify test coverage for assess.py: `pytest tests/unit/soar/test_phase_assess.py --cov=aurora_soar.phases.assess --cov-report=term-missing` and ensure >= 90% coverage
  - [ ] 6.17 Document any deviations from source implementation (if any): score normalization, casing conventions, threshold adjustments
  - [ ] 6.18 Clean up backup files if all tests pass: remove `assess.py.backup` and `test_phase_assess.py.backup`

- [ ] 7.0 TDD Phase 3: MCP Integration Verification
  - [ ] 7.1 Verify MCP tools integration: open `/home/hamr/PycharmProjects/aurora/src/aurora/mcp/tools.py` and check how it calls `assess_complexity()`
  - [ ] 7.2 Verify MCP tools receive correct return format from `assess_complexity()`: check that tools parse `complexity`, `confidence`, `method`, `reasoning` fields correctly
  - [ ] 7.3 Run MCP unit tests: `pytest tests/unit/mcp/ -v` and verify no regressions
  - [ ] 7.4 Run MCP integration tests: `pytest tests/integration/mcp/ -v` and verify no regressions
  - [ ] 7.5 Test MCP server manually with aurora-mcp CLI (if available): verify complexity assessment works in MCP context
  - [ ] 7.6 Test SIMPLE query via MCP: "what is python" should be classified as SIMPLE with method="keyword"
  - [ ] 7.7 Test MEDIUM query via MCP: "explain how the caching works" should be classified as MEDIUM with method="keyword"
  - [ ] 7.8 Test COMPLEX query via MCP: "implement user authentication with oauth" should be classified as COMPLEX with method="keyword"
  - [ ] 7.9 Test CRITICAL query via MCP: "fix security vulnerability in authentication" should be classified as CRITICAL with high confidence
  - [ ] 7.10 Test borderline query via MCP (if llm_client available): verify LLM fallback is triggered and method="llm"
  - [ ] 7.11 Verify MCP server logs show correct complexity assessment decisions (no errors, correct routing)
  - [ ] 7.12 Test MCP server performance: verify complexity assessment adds <2ms latency to query processing
  - [ ] 7.13 Verify MCP tools use assessment results for routing decisions (SIMPLE -> direct LLM, COMPLEX -> SOAR pipeline)
  - [ ] 7.14 Update MCP-related documentation if assessment behavior changed (routing logic, expected latency, accuracy improvements)
  - [ ] 7.15 Verify no breaking changes for MCP consumers: all existing MCP tool calls should work without modification
