# AURORA-Context PRD Updates - Version 1.2

**Date**: December 12, 2025
**Status**: Complete

## Summary

This document summarizes all updates made to the AURORA-Context PRD to reach version 1.2. All requested clarifications and missing prompts have been added.

---

## 1. Added FR-4.10: LLM Prompt Specifications

Added complete section with 6 concise JSON-formatted prompts that enforce JSON-only output:

### FR-4.10.0: Prompt Design Philosophy
- Enforce JSON-only output (no markdown, no explanation)
- Specify exact output schema with validation rules
- Minimal necessary context to reduce token usage
- Structured sections: system, task, schema, constraints

### FR-4.10.1: Complexity Assessment Prompt
- Classifies queries as: simple | medium | complex | critical
- Returns: complexity, confidence, reasoning, indicators, recommended_verification
- Rules for each complexity level
- JSON-only output enforced

### FR-4.10.2: Decomposition Prompt
- Breaks query into 2-5 executable subgoals
- Input: query, context, available_agents
- Output: decomposition JSON with given facts, goal, subgoals, execution_order, parallelizable
- Constraints: max 5 subgoals, DAG dependencies, traceability to given facts

### FR-4.10.3: Decomposition Verification Prompt
- Checks: completeness, consistency, groundedness, routability
- Returns: score per check (0.0-1.0), overall score, verdict (pass/retry/fail)
- Verdict rules:
  - pass: overall_score >= 0.7
  - retry: overall_score 0.5-0.7
  - fail: overall_score < 0.5
- Includes critical_issues and suggestions arrays

### FR-4.10.4: Agent Output Verification Prompt
- Checks: relevance, completeness, groundedness
- Verifies agent output addresses assigned subgoal
- Returns: score per check, overall score, verdict, issues, suggestions
- Retry only if score 0.5-0.7 AND retry_count < 2

### FR-4.10.5: Synthesis Verification Prompt
- Checks: addresses_query, traceable, consistent, calibrated
- Verifies final answer uses subgoal outputs to answer original query
- Returns: scores, verdict, cache_recommendation (cache if >= 0.8)
- Ensures confidence level matches evidence quality

### FR-4.10.6: Retry Feedback Prompt
- Provides structured feedback for retry attempts
- Input: checkpoint (decomposition/agent_output/synthesis), attempt_number, previous_score, verification_result
- Output: issues array with check/score/issue/suggestion per item
- Includes instruction for next attempt and escalate flag

**Key Design Principles**:
- All prompts enforce JSON-only output (no markdown, no prose)
- Clear output schemas prevent format ambiguity
- Minimal token usage (concise, not verbose)
- Explicit verdict rules and thresholds

---

## 2. Clarified FR-4.4.0: SQLite + JSON Architecture

Updated the Implementation Architecture section to clarify:

### pyactr Library Usage (USE, not BUILD)
- ✓ base_level_learning formula (BLA calculation)
- ✓ Activation equation: A = B + S + N
- ✓ Decay functions
- ✓ Threshold formulas

### Custom Implementation (BUILD, not use library)
- ✓ SQLite integration
- ✓ Retrieval logic
- ✓ Spreading activation (dependency traversal)
- ✓ Context boost calculation
- ✓ Chunk type handling
- ✓ JSON schema for chunks

### Storage Architecture Details
**SQLite + JSON means**: JSON is stored IN SQLite columns, NOT as separate files

**Database Structure**:
- Database file: `~/.aurora/memory.db`
- Table: `chunks`
  - Columns: id, type, content (JSON column)
  - Example: `code:auth` stores `{"file": "auth.py", "func": "login", ...}` in JSON column
- Table: `activations` (indexed for fast retrieval)
  - Columns: chunk_id, base_level, last_access, access_count
- Table: `relationships` (for spreading activation)
  - Columns: from_chunk, to_chunk, relationship_type, weight

**Why SQLite + JSON (in columns)**:
- **Efficient**: Indexed queries without reading full memory (no context waste)
- **Flexible**: JSON columns allow schema evolution per chunk type
- **Lightweight**: SQLite is open-source, public domain, no external dependencies
- **Fast**: No file I/O overhead; single database file
- **Type-safe**: Chunk metadata in JSON while maintaining relational integrity

---

## 3. Routing Complexity Clarifications

Confirmed the routing logic (already in PRD, now explicitly clarified):

### Complexity → Verification Option Mapping
- **SIMPLE** → Direct LLM (no decomposition, no verification overhead)
- **MEDIUM** → Decompose → Option A (self-verification)
- **COMPLEX** → Decompose → Option B (adversarial verification)
- **CRITICAL** → Decompose → Option C (deep reasoning with debate) - Phase 2
- **Escalation**: If Option B fails 2x, escalate to Option C (becomes CRITICAL)

---

## 4. Test Prompts vs Production Prompts

Two separate resources created:

### Production Prompts (in PRD - FR-4.10)
- 6 concise JSON prompt specifications
- 20-40 lines each
- Pure JSON structure for request format
- Clear output schema enforcement
- **Purpose**: Reference for implementation

### Test Prompts (in JSON-PROMPT-TESTS.md)
- 6 comprehensive test scenarios
- Full end-to-end examples using agentic AI research scenario
- Includes expected outputs
- Validation checklists
- **Purpose**: Testing and validation before implementation

---

## 5. All Missing Prompts Now Added

The user requested these prompts be added. Status:

- [x] **Assessment prompt**: FR-4.10.1 (originally found in AURORA-Framework-SPECS.md, now in PRD)
- [x] **Decomposition prompt**: FR-4.10.2
- [x] **Decomposition verification prompt**: FR-4.10.3
- [x] **Agent output verification prompt**: FR-4.10.4
- [x] **Synthesis verification prompt**: FR-4.10.5
- [x] **Retry feedback prompt**: FR-4.10.6

---

## 6. Version History Updated

Updated PRD footer with complete version history:

```
PRD Version: 1.2
Created: December 12, 2025
Last Updated: December 12, 2025

Version History:
- v1.2 (2025-12-12): Added FR-4.10 LLM Prompt Specifications with 6 concise
  JSON prompts; Clarified FR-4.4.0 SQLite+JSON architecture; Clarified pyactr
  usage scope
- v1.1 (2025-12-12): Added SOAR orchestrator (FR-4.0), agent registry,
  logging/metrics (FR-4.8), reporting structure, verbosity control (FR-4.9),
  and JSON test prompts (Appendix D)
- v1.0 (2025-12-12): Initial PRD
```

---

## Files Modified/Created

### Modified
1. **`/home/hamr/Documents/smol/agi-problem/aurora/AURORA-Context-PRD.md`** (v1.2)
   - Added FR-4.10: LLM Prompt Specifications (lines 755-964)
   - Updated FR-4.4.0: Implementation Architecture (lines 534-597)
   - Updated version history (lines 1921-1930)

### Previously Created (from v1.1)
2. **`/home/hamr/Documents/smol/agi-problem/aurora/JSON-PROMPT-TESTS.md`**
   - Complete test suite with 6 test prompts using agentic AI research scenario
   - Expected outputs and validation checklists

---

## Implementation Readiness

The PRD now contains:

✅ **Complete architectural clarity**:
- pyactr scope defined (formulas only)
- Storage architecture specified (SQLite with JSON columns)
- Memory identifiers documented (code:, reas:, know: prefixes)

✅ **All verification prompts**:
- 6 production-ready JSON prompt specifications
- Clear output schemas
- Explicit verdict rules and thresholds

✅ **Complete test suite**:
- 6 end-to-end test scenarios
- Practical examples (agentic AI research)
- Validation checklists for testing

✅ **Clear routing logic**:
- SIMPLE → direct LLM
- MEDIUM → Option A
- COMPLEX → Option B
- CRITICAL/escalation → Option C

---

## Next Steps

The PRD is now complete for MVP implementation. Recommended workflow:

1. **Phase 1 (Weeks 1-4)**: Implement MVP
   - Core activation engine (using pyactr for formulas)
   - SQLite + JSON storage
   - Reasoning pipeline with Options A + B
   - Code context provider (cAST + Git)
   - MCP server

2. **Testing**: Use JSON-PROMPT-TESTS.md to validate LLM prompt compatibility

3. **Phase 2 (Weeks 5-8)**: Option C deep reasoning, Knowledge provider

---

**Status**: All user-requested clarifications and missing prompts added to PRD v1.2 ✓
