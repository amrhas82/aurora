# PRD 0020: Keyword Complexity Assessor Replacement

## Introduction/Overview

The AURORA MCP server uses a complexity assessment phase (Phase 1 of the SOAR pipeline) to classify user prompts as SIMPLE, MEDIUM, COMPLEX, or CRITICAL. This classification drives routing decisions including whether to use direct LLM calls or the full AURORA pipeline.

**Note:** The `aur query` CLI command is being removed; complexity assessment will be consumed exclusively via MCP tools.

The current implementation in `aurora_soar/phases/assess.py` uses a basic keyword matching approach that has demonstrated poor accuracy in real-world usage. A new, more sophisticated keyword-based complexity assessor has been developed and validated separately, achieving **96% accuracy** on a 101-prompt test corpus through iterative refinement.

This PRD defines the work required to **port** the new, already-developed complexity assessor from `/home/hamr/Documents/PycharmProjects/aurora/docs/development/complexity_assess/` into the AURORA codebase, replacing the existing implementation. This is NOT new development - the algorithm and tests already exist and are validated. The work is integration/porting only.

## Goals

- **Port** the existing developed module from `docs/development/complexity_assess/` into `aurora_soar/phases/assess.py`
- **Maintain** >= 90% accuracy on the validated test corpus (already achieved: 96%)
- **Maintain** sub-millisecond latency (<1ms target, ~0.5ms expected) - already validated
- **Add** CRITICAL level support to the ported implementation (routing same as COMPLEX for now)
- **Preserve** the LLM Tier 2 verification fallback for borderline/low-confidence cases (port from existing)
- **Port** the test corpus and replace existing tests (remove old tests for old module)
- **Zero breaking changes** to the public `assess_complexity()` function signature
- **Follow TDD methodology** - port tests first, verify they fail against current implementation, then port the module

## User Stories

### US-1: Accurate Simple Query Detection
**As a** user querying AURORA via MCP with "what is python",
**I want** the system to correctly classify this as SIMPLE,
**so that** I get a fast, low-cost direct LLM response without unnecessary AURORA pipeline overhead.

### US-2: Accurate Complex Query Detection
**As a** user querying AURORA via MCP with "implement user authentication with oauth",
**I want** the system to correctly classify this as COMPLEX,
**so that** the full AURORA pipeline is engaged with memory retrieval and multi-step reasoning.

### US-3: Accurate Medium Query Detection
**As a** user querying AURORA via MCP with "explain how the caching works",
**I want** the system to correctly classify this as MEDIUM,
**so that** appropriate reasoning effort is applied without over- or under-provisioning.

### US-4: Critical Query Detection
**As a** user querying AURORA via MCP with "fix security vulnerability in authentication",
**I want** the system to correctly classify this as CRITICAL,
**so that** high-stakes queries receive appropriate scrutiny and verification.

### US-5: Fast Classification
**As a** developer using AURORA via MCP,
**I want** complexity assessment to complete in under 1 millisecond,
**so that** there is negligible latency overhead before my query is processed.

### US-6: Transparent Fallback
**As a** system operator,
**I want** the system to fall back to LLM verification when keyword confidence is low,
**so that** borderline cases are handled correctly even if the keyword classifier is uncertain.

## Functional Requirements

### FR-1: Port Core Algorithm
1. The system must port the existing `complexity_assessor.py` module to replace `_assess_tier1_keyword()`.
2. The ported algorithm already implements all 7 scoring dimensions (no new development required):
   - FR-1.1: Lexical metrics (word count, sentence count, punctuation density)
   - FR-1.2: Keyword analysis (simple/medium/analysis/complex verb categories)
   - FR-1.3: Scope analysis (scope expansion keywords, file/directory references)
   - FR-1.4: Constraint analysis (constraint phrases, compound markers, sequence markers)
   - FR-1.5: Structural patterns (numbered lists, bullet points, code blocks, conditionals)
   - FR-1.6: Domain complexity (technical domains, frameworks)
   - FR-1.7: Question type analysis (simple vs complex question patterns)
3. The system must calculate a compound multiplier based on signal combinations.
4. The system must calculate confidence based on score distance from thresholds and signal consistency.

### FR-2: Complexity Level Support
1. The system must support four complexity levels: SIMPLE, MEDIUM, COMPLEX, CRITICAL.
2. The system must use the following score thresholds:
   - FR-2.1: SIMPLE: score <= 11
   - FR-2.2: MEDIUM: score 12-28
   - FR-2.3: COMPLEX: score >= 29
   - FR-2.4: CRITICAL: triggered by critical keyword detection (security, production, etc.)
3. The system must route CRITICAL queries the same as COMPLEX queries (for escalation purposes).
4. The system must maintain existing CRITICAL_KEYWORDS set for critical detection.

### FR-3: Interface Contract
1. The system must maintain the existing `assess_complexity(query, llm_client=None)` function signature.
2. The system must return a dictionary with at minimum these fields:
   - FR-3.1: `complexity`: str (SIMPLE, MEDIUM, COMPLEX, CRITICAL)
   - FR-3.2: `confidence`: float (0.0-1.0)
   - FR-3.3: `method`: str ("keyword" or "llm")
   - FR-3.4: `reasoning`: str (explanation of classification)
   - FR-3.5: `score`: float (normalized 0.0-1.0 for compatibility, or raw score)
3. The system may include additional fields (`signals`, `breakdown`) for debugging purposes.

### FR-4: LLM Tier 2 Verification
1. The system must preserve the LLM fallback mechanism for borderline cases.
2. The system must trigger LLM verification when:
   - FR-4.1: Keyword confidence is below 0.8, OR
   - FR-4.2: Score is in borderline range (configurable)
3. The system must gracefully handle LLM client being None (keyword-only mode).
4. The system must log a warning when LLM verification is needed but unavailable.

### FR-5: Keyword Dictionaries
1. The system must implement the following verb categories:
   - FR-5.1: SIMPLE_VERBS: what, show, list, get, find, print, check, read, open, run, where, which, display, view, see, tell, give, name, count, who, when, is
   - FR-5.2: MEDIUM_VERBS: add, update, fix, write, change, modify, remove, delete, improve, enhance, extend, convert, rename, move, test, configure, setup, set, enable, disable
   - FR-5.3: ANALYSIS_VERBS: explain, compare, analyze, debug, understand, investigate, describe, clarify, elaborate, why, difference, mean, interpret, evaluate, assess, review, examine, diagnose, trace, audit
   - FR-5.4: COMPLEX_VERBS: implement, design, architect, refactor, integrate, migrate, build, create, develop, construct, engineer, establish, transform, overhaul, rewrite, restructure, optimize
2. The system must implement scope expansion keywords: all, every, entire, across, comprehensive, complete, codebase, project, system, application, full, whole, everything, throughout, universal, global
3. The system must implement constraint phrase detection for phrases like: "without breaking", "maintaining", "backwards compatible", etc.
4. The system must implement technical domain keywords for cross-cutting concerns.

### FR-6: Special Pattern Detection
1. The system must detect trivial edit patterns (e.g., "fix typo", "add console.log") and NOT boost them to MEDIUM.
2. The system must detect bounded scope patterns (e.g., "refactor this function") and reduce complex verb impact.
3. The system must detect verbose simple patterns (e.g., "I would like you to tell me what...") and not over-classify.
4. The system must detect integration patterns (e.g., "integrate X with Y") and boost complexity.
5. The system must detect open-ended optimization patterns and boost complexity when scope is unbounded.

### FR-7: Data Classes
1. The system must define an `AssessmentResult` dataclass with fields: level, score, confidence, signals, breakdown.
2. The system must provide a `to_dict()` method for serialization.
3. The system must define a `ComplexityLevel` IntEnum for type-safe level handling.

### FR-8: Port Test Corpus (TDD)
1. The system must port the existing 101-prompt test corpus from `docs/development/complexity_assess/`.
2. The test corpus already includes prompts categorized by expected level (simple, medium, complex).
3. The test corpus already includes edge cases (short complex, long simple, ambiguous).
4. The system must port the existing evaluation framework (`evaluate.py`) that reports:
   - FR-8.1: Overall accuracy
   - FR-8.2: Per-level accuracy
   - FR-8.3: Confusion matrix
   - FR-8.4: Misclassification analysis

### FR-9: TDD Methodology
1. **Tests First**: All new tests must be written/ported BEFORE implementation changes.
2. **Verify Failure**: New tests must be run against the current implementation to verify they fail (demonstrating the deficiency of the old implementation).
3. **Remove Old Tests**: Existing tests for the old complexity assessor must be removed or replaced:
   - FR-9.1: Remove/replace `tests/unit/soar/test_phase_assess.py` (old tests)
   - FR-9.2: Remove any other test files testing the old `_assess_tier1_keyword()` implementation
   - FR-9.3: Update integration tests that depend on specific complexity assessment behavior
4. **Implementation**: Only after tests are in place and verified to fail, implement the new assessor.
5. **Verify Pass**: All new tests must pass after implementation.
6. **No Orphaned Tests**: No tests for the old module should remain after implementation.

## Non-Goals (Out of Scope)

1. **New algorithm development** - The algorithm already exists and is validated. This is a porting task only.
2. **Changing the SOAR pipeline structure** - This PRD only replaces the complexity assessment algorithm, not the overall pipeline flow.
3. **Modifying downstream consumers** - The orchestrator and MCP tools should continue to work without modification.
4. **Adding new complexity levels beyond CRITICAL** - The four-level system (SIMPLE, MEDIUM, COMPLEX, CRITICAL) is preserved.
5. **Machine learning-based classification** - The ported implementation remains purely rule-based/keyword-based.
6. **Real-time threshold tuning** - Thresholds are fixed based on corpus analysis (already done).
7. **Prompt preprocessing/normalization** - The assessor works on raw prompt text.
8. **Multi-language support** - English prompts only.

## Design Considerations

### File Structure
The implementation will replace the existing file in place:
- **Location**: `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/phases/assess.py`
- **Test Location**: `/home/hamr/PycharmProjects/aurora/tests/unit/soar/test_phase_assess.py`
- **Test Corpus**: New file at `/home/hamr/PycharmProjects/aurora/tests/unit/soar/test_corpus_assess.py`
- **Evaluation**: New file at `/home/hamr/PycharmProjects/aurora/tests/unit/soar/evaluate_assess.py` (optional, for development)

### Score Normalization
The new implementation uses raw integer scores (0-100+), while the existing interface expects 0.0-1.0 normalized scores. The implementation should:
1. Keep raw scores internally for threshold comparison
2. Normalize to 0.0-1.0 for the `score` field in the return dict
3. Optionally include raw score in breakdown for debugging

### Critical Level Handling
CRITICAL detection uses a separate keyword set that overrides the score-based classification:
1. If any CRITICAL_KEYWORDS match, set level to CRITICAL
2. Set confidence to >= 0.9 for critical detections
3. Route CRITICAL same as COMPLEX for escalation decisions

### Backward Compatibility Strategy
Since this is a complete replacement with the same interface:
1. All existing callers (`escalation.py`, `orchestrator.py`, MCP tools) continue unchanged
2. Return dict structure is maintained
3. Complexity level strings are uppercase (SIMPLE, not simple)

## Technical Considerations

### Dependencies
- No new external dependencies required
- Uses only Python standard library: `re`, `dataclasses`, `enum`, `typing`

### Performance Requirements
| Metric | Target | Expected |
|--------|--------|----------|
| Single prompt latency | <1ms | ~0.5ms |
| Long prompt (500+ chars) | <5ms | ~2.5ms |
| Throughput | >1000/sec | ~2000/sec |

### Integration Points
The following modules depend on `assess_complexity()`:
1. `aurora_soar/orchestrator.py` - SOAR pipeline Phase 1
2. `aurora/mcp/tools.py` - MCP server tools (primary consumer)
3. Tests in `tests/unit/` and `tests/integration/`

**Note:** `aurora_cli/escalation.py` and `aur query` CLI command are being removed - not integration points.

### Migration Checklist (TDD Order)
1. **[TDD Phase 1 - Port Tests First]**
   - Port test corpus from `docs/development/complexity_assess/test_complexity_assessor.py`
   - Port evaluation framework from `docs/development/complexity_assess/evaluate.py`
   - Remove old tests for `_assess_tier1_keyword()`
   - Run ported tests to verify they FAIL against current implementation
2. **[TDD Phase 2 - Port Module]**
   - Port `complexity_assessor.py` to `assess.py` (NOT new development)
   - Add CRITICAL level support (minor modification)
   - Adapt interface to match existing `assess_complexity()` signature
   - Port LLM Tier 2 fallback from existing implementation
3. **[TDD Phase 3 - Verification]**
   - Run ported tests to verify they PASS
   - Run full test suite to verify no regressions
   - Verify MCP server tools work correctly end-to-end (via `aurora-mcp` or integration tests)

### Source Files to Port
| Source (from `docs/development/complexity_assess/`) | Destination |
|-----------------------------------------------------|-------------|
| `complexity_assessor.py` | `packages/soar/src/aurora_soar/phases/assess.py` |
| `test_complexity_assessor.py` | `tests/unit/soar/test_phase_assess.py` |
| `evaluate.py` | `tests/unit/soar/evaluate_assess.py` (optional) |
| Test corpus (embedded in test file) | `tests/unit/soar/test_corpus_assess.py` |

## Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Test corpus accuracy | >= 90% | `evaluate_assess.py` report |
| Per-level accuracy (each) | >= 85% | Per-level breakdown in evaluation |
| Latency (p50) | <1ms | Benchmark tests |
| Latency (p99) | <5ms | Benchmark tests |
| No regression in existing tests | 100% pass | `pytest tests/` |
| Zero breaking changes | 0 caller modifications | Manual verification |

## Open Questions

1. **Threshold Tuning**: Should thresholds (11/28) be configurable via environment variables or config file for production tuning?
   - *Current decision*: Hardcoded based on corpus analysis. Can revisit if needed.

2. **Logging Verbosity**: Should the breakdown and signals be logged at DEBUG level for production troubleshooting?
   - *Recommendation*: Yes, log at DEBUG level.

3. **CRITICAL Routing**: Currently CRITICAL routes same as COMPLEX. Should CRITICAL have different behavior (e.g., require human approval)?
   - *Current decision*: Same as COMPLEX. Future PRD can address differentiation.

4. **Corpus Maintenance**: How should the test corpus be maintained and expanded over time?
   - *Recommendation*: Add misclassified production queries to corpus during regular maintenance.

---

## Appendix A: Algorithm Scoring Summary

### Scoring Dimensions

| Dimension | Score Range | Key Factors |
|-----------|-------------|-------------|
| Lexical | 0-25+ | Word count, sentences, punctuation |
| Keywords | -10 to +70 | Verb categories, noun complexity |
| Scope | 0-36+ | Scope keywords, file references |
| Constraints | 0-60+ | Constraint phrases, sequence markers |
| Structure | 0-50+ | Lists, code blocks, conditionals |
| Domain | 0-30+ | Technical domains, frameworks |
| Question Type | -8 to +15 | Simple vs complex patterns |

### Threshold Boundaries

| Level | Score Range | Description |
|-------|-------------|-------------|
| SIMPLE | <= 11 | Lookups, displays, trivial edits |
| MEDIUM | 12-28 | Analysis, debugging, moderate edits |
| COMPLEX | >= 29 | Implementation, architecture, multi-system |
| CRITICAL | N/A | Keyword-triggered (security, production) |

---

## Appendix B: Test Corpus Categories

| Category | Count | Examples |
|----------|-------|----------|
| Lookup/Display | 20 | "what is python", "show git status" |
| Single Action | 5 | "fix the typo", "rename variable" |
| Analysis | 10 | "explain authentication", "debug login" |
| Moderate Edit | 10 | "add error handling", "write a test" |
| Multi-step Bounded | 5 | "run lint and fix issues" |
| Major Implementation | 10 | "implement oauth", "build dashboard" |
| Multi-system | 7 | "migrate database", "integrate stripe" |
| With Constraints | 5 | "refactor without breaking tests" |
| Multi-domain | 5 | "auth on frontend and backend" |
| Edge Cases | 14 | Short complex, long simple, ambiguous |
| Real-world | 10 | Production-like queries |
| **Total** | **101** | |

---

## Appendix C: File Changes Summary

| File | Action | TDD Phase | Description |
|------|--------|-----------|-------------|
| `tests/unit/soar/test_phase_assess.py` | Remove then Replace | Phase 1 | Remove old tests, write new corpus-based tests |
| `tests/unit/soar/test_corpus_assess.py` | Create | Phase 1 | 101-prompt test corpus data |
| `tests/unit/test_assess.py` | Delete | Phase 1 | Remove old tests |
| `packages/soar/src/aurora_soar/phases/assess.py` | Replace | Phase 2 | New complexity assessor implementation |
| `tests/e2e/test_e2e_complexity_assessment.py` | Update | Phase 3 | Verify E2E still passes |

### Old Test Files to Remove (FR-9)
The following test files for the old module must be identified and removed/replaced:
- `tests/unit/soar/test_phase_assess.py` - old unit tests
- `tests/unit/test_assess.py` - if exists, old tests
- Any other files containing tests for `_assess_tier1_keyword()`
