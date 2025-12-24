# Prompt Template Review Checklist (Task 9.18)

**Reviewer**: Automated Review
**Date**: 2025-12-22
**Status**: ✅ PASSED

## Overview

This document verifies that all prompt templates properly enforce JSON-only output (where applicable) and follow best practices for LLM prompting.

## Templates Reviewed

### 1. AssessPromptTemplate (`assess.py`)

**Purpose**: LLM-based complexity assessment
**Output Format**: JSON
**JSON Enforcement**: ✅ PASSED

**Review**:
- ✅ Explicit instruction: "You MUST respond with valid JSON only"
- ✅ Exact schema provided with format specification
- ✅ No markdown code blocks mentioned
- ✅ Clear field specifications with data types
- ✅ Example format shows raw JSON (no wrapping)

**Schema**:
```json
{
  "complexity": "SIMPLE|MEDIUM|COMPLEX|CRITICAL",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation"
}
```

---

### 2. DecomposePromptTemplate (`decompose.py`)

**Purpose**: Query decomposition into subgoals
**Output Format**: JSON
**JSON Enforcement**: ✅ PASSED

**Review**:
- ✅ Explicit instruction: "You MUST respond with valid JSON only"
- ✅ Complete schema provided with nested structure
- ✅ Clear array and object specifications
- ✅ Field descriptions with types and constraints
- ✅ No markdown formatting mentioned

**Schema**:
```json
{
  "goal": "string",
  "subgoals": [
    {
      "description": "string",
      "suggested_agent": "string",
      "is_critical": boolean,
      "depends_on": [indices]
    }
  ],
  "execution_order": [...],
  "expected_tools": [...]
}
```

---

### 3. VerifySelfPromptTemplate (`verify_self.py`)

**Purpose**: Self-verification of decompositions (Option A)
**Output Format**: JSON
**JSON Enforcement**: ✅ PASSED

**Review**:
- ✅ Explicit instruction: "You MUST respond with valid JSON only"
- ✅ Exact format specification with all required fields
- ✅ Score ranges clearly specified (0.0-1.0)
- ✅ Verdict values enumerated (PASS|RETRY|FAIL)
- ✅ Array fields properly typed

**Schema**:
```json
{
  "completeness": 0.0-1.0,
  "consistency": 0.0-1.0,
  "groundedness": 0.0-1.0,
  "routability": 0.0-1.0,
  "overall_score": 0.0-1.0,
  "verdict": "PASS|RETRY|FAIL",
  "issues": [...],
  "suggestions": [...]
}
```

---

### 4. VerifyAdversarialPromptTemplate (`verify_adversarial.py`)

**Purpose**: Adversarial verification (Option B)
**Output Format**: JSON
**JSON Enforcement**: ✅ PASSED

**Review**:
- ✅ Explicit instruction: "You MUST respond with valid JSON only"
- ✅ Exact format with additional adversarial fields
- ✅ All score ranges specified
- ✅ Verdict logic clearly explained
- ✅ Multiple issue categories (critical, minor, edge_cases)

**Schema**:
```json
{
  "completeness": 0.0-1.0,
  "consistency": 0.0-1.0,
  "groundedness": 0.0-1.0,
  "routability": 0.0-1.0,
  "overall_score": 0.0-1.0,
  "verdict": "PASS|RETRY|FAIL",
  "critical_issues": [...],
  "minor_issues": [...],
  "edge_cases": [...],
  "suggestions": [...]
}
```

---

### 5. VerifyAgentOutputPromptTemplate (`verify_agent_output.py`)

**Purpose**: Verify agent execution outputs
**Output Format**: JSON
**JSON Enforcement**: ✅ PASSED

**Review**:
- ✅ Explicit instruction: "You MUST respond with valid JSON only"
- ✅ Clear format specification
- ✅ Simpler schema appropriate for agent output verification
- ✅ Quality score and verdict clearly defined

**Schema**:
```json
{
  "quality_score": 0.0-1.0,
  "verdict": "PASS|RETRY",
  "issues": [...],
  "confidence": 0.0-1.0
}
```

---

### 6. VerifySynthesisPromptTemplate (`verify_synthesis.py`)

**Purpose**: Verify synthesized responses
**Output Format**: JSON
**JSON Enforcement**: ✅ PASSED

**Review**:
- ✅ Explicit instruction: "You MUST respond with valid JSON only"
- ✅ Three-dimensional scoring (coherence, completeness, factuality)
- ✅ Average calculation specified
- ✅ Issue and suggestion fields included

**Schema**:
```json
{
  "coherence": 0.0-1.0,
  "completeness": 0.0-1.0,
  "factuality": 0.0-1.0,
  "overall_score": 0.0-1.0,
  "issues": [...],
  "suggestions": [...]
}
```

---

### 7. RetryFeedbackPromptTemplate (`retry_feedback.py`)

**Purpose**: Generate retry feedback for failed verifications
**Output Format**: **Plain Text** (NOT JSON)
**JSON Enforcement**: ✅ N/A (Correctly uses plain text)

**Review**:
- ✅ Explicitly specifies: "Respond in plain text (NOT JSON)"
- ✅ Appropriate for feedback messages that need to be human-readable
- ✅ Focuses on actionable guidance
- ✅ System prompt correctly sets expectations

**Rationale**: Retry feedback is injected back into decomposition prompts as natural language guidance, so plain text is the correct format here.

---

## JSON Parsing Strategy

All templates that expect JSON output are processed through the LLM client's JSON extraction logic:

**Location**: `packages/reasoning/src/aurora_reasoning/llm_client.py`

**Features**:
1. Extracts JSON from markdown code blocks (```json...```)
2. Handles plain JSON responses
3. Validates JSON structure
4. Returns parsed dict or raises clear error

**Test Coverage**:
- `tests/unit/reasoning/test_llm_client.py` validates JSON parsing
- All prompt templates tested with JSON validation

---

## Best Practices Verified

### ✅ Schema Clarity
- All JSON templates provide exact schema format
- Field types explicitly specified (string, number, boolean, array)
- Range constraints clearly stated (e.g., 0.0-1.0)

### ✅ Explicit Instructions
- Every JSON template includes "You MUST respond with valid JSON only"
- No ambiguity about expected format
- Examples show raw JSON (no markdown wrappers)

### ✅ Error Prevention
- Enumerations provided for categorical fields (PASS|RETRY|FAIL)
- Scoring formulas explicitly stated
- Required vs. optional fields implied through schema

### ✅ Consistency
- All verification templates use similar scoring structure
- Common field names across templates (issues, suggestions, confidence)
- Unified scoring range (0.0-1.0)

---

## Potential Improvements (Non-Blocking)

### Suggestion 1: Add Schema Validation
Consider adding runtime schema validation using `jsonschema` library to catch malformed LLM outputs early.

**Implementation**:
```python
from jsonschema import validate, ValidationError

ASSESS_SCHEMA = {
    "type": "object",
    "required": ["complexity", "confidence", "reasoning"],
    "properties": {
        "complexity": {"enum": ["SIMPLE", "MEDIUM", "COMPLEX", "CRITICAL"]},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "reasoning": {"type": "string"}
    }
}

def validate_assess_output(data: dict) -> None:
    validate(instance=data, schema=ASSESS_SCHEMA)
```

### Suggestion 2: Add Output Examples
Include 1-2 example outputs directly in system prompts for few-shot learning effect.

### Suggestion 3: Token Optimization
Some system prompts are verbose. Consider condensing while maintaining clarity to reduce token costs.

---

## Conclusion

**Overall Assessment**: ✅ **PASSED**

All prompt templates properly enforce JSON-only output where required. The one exception (retry_feedback) correctly uses plain text as intended. No changes required for JSON enforcement.

**Recommendations**:
1. Current implementation is production-ready
2. Optional schema validation could improve robustness
3. Monitor LLM output parsing failures in production logs

**Next Steps**: Proceed to Task 9.19 (Verification Calibration)

---

**Reviewed Files**:
- `/home/hamr/PycharmProjects/aurora/packages/reasoning/src/aurora_reasoning/prompts/assess.py`
- `/home/hamr/PycharmProjects/aurora/packages/reasoning/src/aurora_reasoning/prompts/decompose.py`
- `/home/hamr/PycharmProjects/aurora/packages/reasoning/src/aurora_reasoning/prompts/verify_self.py`
- `/home/hamr/PycharmProjects/aurora/packages/reasoning/src/aurora_reasoning/prompts/verify_adversarial.py`
- `/home/hamr/PycharmProjects/aurora/packages/reasoning/src/aurora_reasoning/prompts/verify_agent_output.py`
- `/home/hamr/PycharmProjects/aurora/packages/reasoning/src/aurora_reasoning/prompts/verify_synthesis.py`
- `/home/hamr/PycharmProjects/aurora/packages/reasoning/src/aurora_reasoning/prompts/retry_feedback.py`
