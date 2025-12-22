# Code Review Checklist (Task 9.21)

**Reviewers Required**: 2+ people
**Focus Areas**: Verification logic, error handling, overall code quality
**Status**: ⏳ PENDING REVIEW

## Pre-Review Setup

- [ ] All tests passing (881/895 = 98.4%)
- [ ] Coverage ≥85% (current: 88.06%) ✅
- [ ] Documentation complete ✅
- [ ] No critical security issues (see SECURITY_AUDIT_CHECKLIST.md)

## Review Areas

### 1. Verification Logic (Priority: CRITICAL)

**Files to Review**:
- `packages/reasoning/src/aurora_reasoning/verify.py`
- `packages/soar/src/aurora_soar/phases/verify.py`
- `packages/reasoning/src/aurora_reasoning/prompts/verify_self.py`
- `packages/reasoning/src/aurora_reasoning/prompts/verify_adversarial.py`

**Checklist**:
- [ ] **Scoring Formula Correctness**
  - [ ] Formula matches PRD: 0.4*completeness + 0.2*consistency + 0.2*groundedness + 0.2*routability
  - [ ] Weights sum to 1.0
  - [ ] Score range validated (0.0-1.0)

- [ ] **Verdict Logic**
  - [ ] PASS threshold (≥0.7) correctly implemented
  - [ ] RETRY threshold (0.5-0.7) correctly implemented
  - [ ] FAIL threshold (<0.5) correctly implemented
  - [ ] Edge cases handled (scores exactly 0.5, 0.7)

- [ ] **Option A vs Option B**
  - [ ] Option A (self-verification) works correctly
  - [ ] Option B (adversarial) is stricter/more thorough
  - [ ] Complexity-based selection logic correct (MEDIUM→A, COMPLEX→B)

- [ ] **Retry Loop**
  - [ ] Max 2 retries enforced
  - [ ] Feedback generation working
  - [ ] Feedback injection into retry prompts correct
  - [ ] Infinite loop prevention verified

- [ ] **Edge Cases**
  - [ ] Malformed LLM responses handled
  - [ ] Missing fields caught with clear errors
  - [ ] Timeout handling works
  - [ ] Score calculation edge cases (division by zero, NaN)

**Review Notes**:
```
Reviewer 1:
-

Reviewer 2:
-
```

---

### 2. Error Handling (Priority: HIGH)

**Files to Review**:
- `packages/core/src/aurora_core/exceptions.py`
- `packages/soar/src/aurora_soar/orchestrator.py`
- `packages/reasoning/src/aurora_reasoning/llm_client.py`
- All phase files in `packages/soar/src/aurora_soar/phases/`

**Checklist**:
- [ ] **Exception Hierarchy**
  - [ ] Custom exceptions clearly defined
  - [ ] Exception inheritance makes sense
  - [ ] Error messages are descriptive

- [ ] **Graceful Degradation**
  - [ ] Partial failures return partial results
  - [ ] Critical failures abort gracefully
  - [ ] No silent failures

- [ ] **Error Propagation**
  - [ ] Errors propagate correctly up the stack
  - [ ] Context preserved in error messages
  - [ ] Stack traces available for debugging

- [ ] **Retry Logic**
  - [ ] Exponential backoff implemented correctly
  - [ ] Max retries enforced
  - [ ] Transient vs permanent errors distinguished
  - [ ] Retry state properly managed

- [ ] **User-Facing Errors**
  - [ ] Clear, actionable error messages
  - [ ] No internal implementation details leaked
  - [ ] Suggestions for fixes provided where possible

- [ ] **Logging**
  - [ ] Errors logged at appropriate levels
  - [ ] Debug info available for troubleshooting
  - [ ] No sensitive data in error logs

**Review Notes**:
```
Reviewer 1:
-

Reviewer 2:
-
```

---

### 3. LLM Integration (Priority: HIGH)

**Files to Review**:
- `packages/reasoning/src/aurora_reasoning/llm_client.py`
- `packages/reasoning/src/aurora_reasoning/prompts/*.py`

**Checklist**:
- [ ] **API Key Handling**
  - [ ] Keys loaded from environment variables
  - [ ] No keys hardcoded
  - [ ] Fallback handling if key missing

- [ ] **Rate Limiting**
  - [ ] Retry logic respects rate limits
  - [ ] Exponential backoff implemented
  - [ ] Max retries prevent infinite loops

- [ ] **JSON Parsing**
  - [ ] Handles markdown code blocks
  - [ ] Handles plain JSON
  - [ ] Malformed JSON caught with clear errors
  - [ ] Schema validation (if implemented)

- [ ] **Prompt Templates**
  - [ ] All templates enforce JSON output correctly (see PROMPT_TEMPLATE_REVIEW.md)
  - [ ] System prompts are clear and specific
  - [ ] Few-shot examples are appropriate
  - [ ] No prompt injection vulnerabilities

- [ ] **Token Counting**
  - [ ] Token estimation accurate enough
  - [ ] Cost tracking integrated
  - [ ] Budget checks prevent overruns

**Review Notes**:
```
Reviewer 1:
-

Reviewer 2:
-
```

---

### 4. SOAR Orchestrator (Priority: HIGH)

**Files to Review**:
- `packages/soar/src/aurora_soar/orchestrator.py`
- All phase files in `packages/soar/src/aurora_soar/phases/`

**Checklist**:
- [ ] **Phase Sequencing**
  - [ ] Phases execute in correct order
  - [ ] Phase outputs passed correctly to next phase
  - [ ] Early exit paths work (e.g., SIMPLE queries)

- [ ] **State Management**
  - [ ] Phase state properly tracked
  - [ ] No state leakage between queries
  - [ ] Thread-safe if parallelization used

- [ ] **Cost Tracking**
  - [ ] Budget checked before expensive operations
  - [ ] Actual costs recorded accurately
  - [ ] Budget exceeded errors handled

- [ ] **Timeouts**
  - [ ] Per-phase timeouts enforced
  - [ ] Overall query timeout enforced
  - [ ] Timeout handling is graceful

- [ ] **Metadata Collection**
  - [ ] All required metadata captured
  - [ ] Metadata format consistent
  - [ ] No sensitive data in metadata

**Review Notes**:
```
Reviewer 1:
-

Reviewer 2:
-
```

---

### 5. Agent Routing & Execution (Priority: MEDIUM)

**Files to Review**:
- `packages/soar/src/aurora_soar/phases/route.py`
- `packages/soar/src/aurora_soar/phases/collect.py`
- `packages/soar/src/aurora_soar/agent_registry.py`

**Checklist**:
- [ ] **Agent Registry**
  - [ ] Agent lookup efficient
  - [ ] Capability-based search works
  - [ ] Fallback to llm-executor correct

- [ ] **Routing Logic**
  - [ ] Dependency resolution correct
  - [ ] Circular dependencies detected
  - [ ] Execution order validation works

- [ ] **Parallel Execution**
  - [ ] Independent subgoals run in parallel
  - [ ] Dependent subgoals wait correctly
  - [ ] Race conditions prevented
  - [ ] Error handling in parallel context

- [ ] **Agent Output Validation**
  - [ ] Required fields checked
  - [ ] Output format validated
  - [ ] Verification applied correctly

**Review Notes**:
```
Reviewer 1:
-

Reviewer 2:
-
```

---

### 6. ReasoningChunk & Pattern Caching (Priority: MEDIUM)

**Files to Review**:
- `packages/core/src/aurora_core/chunks/reasoning_chunk.py`
- `packages/soar/src/aurora_soar/phases/record.py`

**Checklist**:
- [ ] **Schema Compliance**
  - [ ] All required fields present
  - [ ] Field types correct
  - [ ] Validation logic comprehensive

- [ ] **Serialization**
  - [ ] to_json() correct
  - [ ] from_json() correct
  - [ ] Round-trip testing passed (see tests)

- [ ] **Caching Policy**
  - [ ] Score thresholds correct (≥0.5 cache, ≥0.8 pattern)
  - [ ] Learning updates correct (+0.2 success, -0.1 failure)
  - [ ] Cache eviction (if implemented) works

**Review Notes**:
```
Reviewer 1:
-

Reviewer 2:
-
```

---

### 7. Code Quality & Style (Priority: LOW)

**General Checklist**:
- [ ] **Naming Conventions**
  - [ ] Functions/methods are verb phrases
  - [ ] Classes are noun phrases
  - [ ] Variables are descriptive
  - [ ] Constants are UPPER_CASE

- [ ] **Documentation**
  - [ ] All public APIs have docstrings
  - [ ] Docstrings follow Google style
  - [ ] Complex logic has inline comments
  - [ ] No outdated comments

- [ ] **Type Hints**
  - [ ] All function signatures typed
  - [ ] Return types specified
  - [ ] Optional types used correctly
  - [ ] mypy passing (with minor exceptions OK)

- [ ] **Code Duplication**
  - [ ] No significant duplication
  - [ ] Shared logic extracted to functions
  - [ ] Constants defined once

- [ ] **Function Length**
  - [ ] Functions are reasonably sized (<100 lines)
  - [ ] Complex functions broken down
  - [ ] Single Responsibility Principle followed

**Review Notes**:
```
Reviewer 1:
-

Reviewer 2:
-
```

---

### 8. Testing Coverage (Priority: MEDIUM)

**Test Files to Review**:
- `tests/unit/reasoning/test_verify.py`
- `tests/unit/soar/test_phase_verify.py`
- `tests/integration/test_verification_retry.py`
- `tests/calibration/test_verification_calibration.py`

**Checklist**:
- [ ] **Test Quality**
  - [ ] Tests are clear and focused
  - [ ] Test names describe what they test
  - [ ] Assertions are specific
  - [ ] No flaky tests

- [ ] **Coverage**
  - [ ] Critical paths all tested
  - [ ] Edge cases covered
  - [ ] Error paths tested
  - [ ] Mock usage appropriate

- [ ] **Test Organization**
  - [ ] Tests grouped logically
  - [ ] Fixtures used appropriately
  - [ ] No test interdependencies

**Review Notes**:
```
Reviewer 1:
-

Reviewer 2:
-
```

---

## Review Sign-Off

### Reviewer 1

**Name**: _________________
**Date**: _________________

**Overall Assessment**: [ ] APPROVED  [ ] APPROVED WITH CHANGES  [ ] NEEDS WORK

**Critical Issues Found**: ___

**Blocking Issues**:
```
(List any issues that must be fixed before merge)
```

**Non-Blocking Suggestions**:
```
(List improvements that can be addressed later)
```

**Signature**: _________________

---

### Reviewer 2

**Name**: _________________
**Date**: _________________

**Overall Assessment**: [ ] APPROVED  [ ] APPROVED WITH CHANGES  [ ] NEEDS WORK

**Critical Issues Found**: ___

**Blocking Issues**:
```
(List any issues that must be fixed before merge)
```

**Non-Blocking Suggestions**:
```
(List improvements that can be addressed later)
```

**Signature**: _________________

---

## Post-Review Actions

### If APPROVED:
- [ ] All reviewer comments addressed
- [ ] Final test suite run (all passing)
- [ ] Documentation updated if needed
- [ ] Ready for security audit (Task 9.22)

### If APPROVED WITH CHANGES:
- [ ] Create issues for non-blocking items
- [ ] Address blocking items immediately
- [ ] Re-review after changes
- [ ] Proceed to security audit

### If NEEDS WORK:
- [ ] Address all blocking issues
- [ ] Request re-review
- [ ] Do not proceed to next phase

---

## Review Completion

**Review Status**: ⏳ PENDING

**Date Completed**: _________________

**Final Verdict**: [ ] PASS  [ ] FAIL

**Ready for Production**: [ ] YES  [ ] NO

---

**Notes**: This is a comprehensive code review checklist. Reviewers should spend 2-4 hours thoroughly examining the codebase, with particular focus on verification logic and error handling as these are the most critical components.
