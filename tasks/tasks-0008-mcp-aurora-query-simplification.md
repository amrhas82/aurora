# Task List: PRD 0008 - MCP aurora_query Simplification

**PRD Source:** `/home/hamr/PycharmProjects/aurora/tasks/0008-prd-mcp-aurora-query-simplification.md`
**Generated:** 2025-12-26
**Status:** Complete

---

## Summary

This task list implements the simplification of the AURORA MCP `aurora_query` tool by:
1. Removing all LLM API calls from MCP tools (MCP runs inside Claude Code CLI which IS the LLM)
2. Returning structured context instead of calling Anthropic API
3. Archiving ~800 lines of LLM-related tests
4. Simplifying the tool signature and response format
5. Adding new `aurora_get` tool for retrieving chunks by index from search results
6. Comprehensive documentation updates with CLI vs MCP comparison table

**Key Principle:** MCP tools (inside CC CLI) = NO API KEY EVER | CLI commands (`$ aur query`) = Needs API KEY

**MCP Tool Count:** 6 → 7 (adding aurora_get)

---

## Relevant Files

### Production Files
- `src/aurora/mcp/tools.py` - Main MCP tools implementation (995 lines); added aurora_get method with session cache (Tasks 7.1-7.12 complete)
- `src/aurora/mcp/server.py` - MCP server registration; updated aurora_query tool signature and registered aurora_get tool (Tasks 8.1-8.7 complete)
- `src/aurora/mcp/config.py` - MCP configuration; may need minor updates for removed features

### Test Files (To Archive)
- `tests/unit/mcp/test_aurora_query_tool.py` - Current test file; archive LLM-related test classes

### Test Files (Created)
- `tests/unit/mcp/test_aurora_query_simplified.py` - New tests for simplified aurora_query (24 tests, all passing)
- `tests/unit/mcp/test_aurora_get.py` - Tests for aurora_get tool (12 tests, TDD RED phase - all failing as expected)

### Test Files (To Create)
- `tests/integration/test_mcp_no_api_key.py` - Integration tests verifying no API key required
- `tests/e2e/test_mcp_e2e.py` - End-to-end tests for MCP workflow

### Archive Directory
- `tests/archive/2025-01-mcp-simplification/` - Directory for archived test code
- `tests/archive/2025-01-mcp-simplification/README.md` - Explanation of archived tests
- `tests/archive/2025-01-mcp-simplification/test_aurora_query_llm_tests.py` - Archived LLM tests

### Reference Files (Do Not Modify)
- `packages/cli/src/aurora_cli/` - CLI code remains unchanged (still requires API key)
- `packages/cli/src/aurora_cli/commands/query.py` - CLI query command (reference only)

---

### Notes

- **TDD Workflow:** All development is TEST-DRIVEN. Write failing test FIRST, then implement code to make it pass.
- **Testing Framework:** pytest with fixtures; follow existing patterns in `tests/unit/mcp/`
- **Architecture Pattern:** MCP tools do retrieval only; host LLM (Claude Code CLI) does reasoning
- **Response Format:** All MCP tool responses are JSON strings returned via `json.dumps()`
- **Existing Patterns:** See `aurora_search` method for example of retrieval-only tool
- **CLI Preservation:** The CLI in `packages/cli/` must NOT be modified; it still requires API keys for standalone usage
- **Line Count Targets:** `tools.py` ~700 lines (net: -LLM code +aurora_get)
- **Test Archival:** Move tests to archive, do not delete; maintain git history

---

## Tasks

### Phase 1: Test Setup (TDD - Write Failing Tests First)

- [x] 1.0 Archive Existing LLM Tests
  - [x] 1.1 Create archive directory structure at `/tests/archive/2025-01-mcp-simplification/`
  - [x] 1.2 Create `README.md` in archive directory explaining why tests were archived, what functionality they tested, the date archived, and reference to PRD-0008 (use template from Appendix B of PRD)
  - [x] 1.3 Identify test classes to archive from `test_aurora_query_tool.py`: `TestAPIKeyHandling`, `TestBudgetEnforcement`, `TestAutoEscalation`, `TestRetryLogic`, `TestMemoryGracefulDegradation`, `TestErrorLogging`, `TestProgressTracking`, `TestEnhancedVerbosity`
  - [x] 1.4 Extract and move identified test classes to `tests/archive/2025-01-mcp-simplification/test_aurora_query_llm_tests.py` preserving imports and structure
  - [x] 1.5 Remove archived test classes from `tests/unit/mcp/test_aurora_query_tool.py`, keeping only `TestParameterValidation` and `TestConfigurationLoading` (modified versions)
  - [x] 1.6 Commit archive with message: "chore(tests): archive LLM-related tests for MCP simplification"

- [x] 2.0 Write Failing Tests for Simplified aurora_query (TDD RED)
  - [x] 2.1 Create new test file `tests/unit/mcp/test_aurora_query_simplified.py` with standard pytest imports and fixtures
  - [x] 2.2 Create `TestParameterValidation` class with tests: `test_query_empty_string_returns_error`, `test_query_whitespace_only_returns_error`, `test_invalid_type_filter_returns_error`, `test_valid_type_filters_accepted` (code, reas, know, None)
  - [x] 2.3 Create `TestResponseFormat` class with tests: `test_response_contains_context_section`, `test_response_contains_assessment_section`, `test_response_contains_metadata_section`, `test_chunks_are_numbered`, `test_relevance_scores_included`
  - [x] 2.4 Create `TestConfidenceHandling` class with tests: `test_low_confidence_includes_suggestion` (confidence < 0.5), `test_high_confidence_no_suggestion` (confidence >= 0.5), `test_empty_results_zero_confidence`
  - [x] 2.5 Create `TestTypeFiltering` class with tests: `test_filter_code_type_only`, `test_filter_reas_type_only`, `test_filter_know_type_only`, `test_no_filter_returns_all_types`
  - [x] 2.6 Create `TestComplexityAssessment` class with tests: `test_simple_query_low_complexity`, `test_complex_query_high_complexity`, `test_long_query_medium_complexity`
  - [x] 2.7 Create `TestNoAPIKeyRequired` class with tests: `test_works_without_api_key_env`, `test_works_without_config_api_key`, `test_no_api_key_error_messages` (ensure no APIKeyMissing errors)
  - [x] 2.8 Run `pytest tests/unit/mcp/test_aurora_query_simplified.py -v` - EXPECT FAILURES (TDD RED phase)
  - [x] 2.9 Document expected failure count and which tests fail

- [x] 3.0 Write Failing Tests for aurora_get (TDD RED)
  - [x] 3.1 Create `tests/unit/mcp/test_aurora_get.py` with test classes from PRD Test Plan
  - [x] 3.2 Create `TestBasicFunctionality` class: `test_get_valid_index_returns_chunk`, `test_get_first_item_index_1`, `test_get_last_item`
  - [x] 3.3 Create `TestErrorHandling` class: `test_get_index_zero_returns_error`, `test_get_negative_index_returns_error`, `test_get_index_out_of_range_returns_error`, `test_get_no_previous_search_returns_error`
  - [x] 3.4 Create `TestSessionCache` class: `test_cache_stores_last_search_results`, `test_new_search_clears_previous_cache`, `test_cache_expires_after_timeout`
  - [x] 3.5 Create `TestResponseFormat` class: `test_response_includes_full_chunk`, `test_response_includes_index_and_total`
  - [x] 3.6 Run `pytest tests/unit/mcp/test_aurora_get.py -v` - EXPECT FAILURES (TDD RED phase)

### Phase 2: Implementation (TDD GREEN - Make Tests Pass)

- [x] 4.0 Remove LLM-Related Methods from tools.py
  - [x] 4.1 Remove `_get_api_key()` method (lines ~617-639) from `AuroraMCPTools` class
  - [x] 4.2 Remove `_check_budget()` method (lines ~641-689) from `AuroraMCPTools` class
  - [x] 4.3 Remove `_get_budget_error_message()` method (lines ~691-713) from `AuroraMCPTools` class
  - [x] 4.4 Remove `_ensure_query_executor_initialized()` method (lines ~715-727) from `AuroraMCPTools` class
  - [x] 4.5 Remove `_is_transient_error()` method (lines ~729-778) from `AuroraMCPTools` class
  - [x] 4.6 Remove `_execute_with_retry()` method (lines ~780-832) from `AuroraMCPTools` class
  - [x] 4.7 Remove `_execute_with_auto_escalation()` method (lines ~834-883) from `AuroraMCPTools` class
  - [x] 4.8 Remove `_execute_direct_llm()` method (lines ~925-978) from `AuroraMCPTools` class
  - [x] 4.9 Remove `_execute_soar()` method (lines ~980-1065) from `AuroraMCPTools` class
  - [x] 4.10 Remove unused imports at top of file: `time` (if only used by removed methods), any LLM-related imports
  - [x] 4.11 Retain `_assess_complexity()` method (lines ~885-923) - this is used for heuristic assessment
  - [x] 4.12 Retain `_get_memory_context()` method (lines ~1067-1084) - this becomes the primary function
  - [x] 4.13 Retain `_format_error()` method (lines ~1133-1166) - still needed for error responses
  - [x] 4.14 Run `python -c "from aurora.mcp.tools import AuroraMCPTools"` to verify module still imports

- [x] 5.0 Implement Simplified aurora_query Response Format
  - [x] 5.1 Modify `_get_memory_context()` to return structured dict instead of string, including chunk metadata (id, type, content, file_path, line_range, relevance_score)
  - [x] 5.2 Create new `_retrieve_chunks()` method that uses `HybridRetriever` to get chunks with full metadata and relevance scores
  - [x] 5.3 Create new `_calculate_retrieval_confidence()` method that computes confidence score (0.0-1.0) based on top result scores and result count
  - [x] 5.4 Create new `_build_context_response()` method that constructs the JSON response structure per FR-2.2 schema with `context`, `assessment`, and `metadata` sections
  - [x] 5.5 Implement chunk numbering (1, 2, 3...) in response for easy reference per FR-2.3
  - [x] 5.6 Add `retrieval_confidence` field to assessment section per FR-2.4
  - [x] 5.7 Add conditional suggestion field when `retrieval_confidence < 0.5` per FR-2.5: "Low confidence results. Consider refining your query or indexing more code."
  - [x] 5.8 Retain heuristic complexity assessment from `_assess_complexity()` in assessment section per FR-2.6
  - [x] 5.9 Add index stats to metadata section (total_chunks, types breakdown) per FR-2.2
  - [x] 5.10 Replace `_format_response()` method with new implementation that outputs the FR-2.2 schema
  - [x] 5.11 Run `pytest tests/unit/mcp/test_aurora_query_simplified.py::TestResponseFormat -v` - should pass now

- [x] 6.0 Update aurora_query Function Signature
  - [x] 6.1 Remove `force_soar` parameter from `aurora_query()` method signature (no SOAR pipeline in MCP)
  - [x] 6.2 Remove `model` parameter from `aurora_query()` method signature (no LLM selection)
  - [x] 6.3 Remove `temperature` parameter from `aurora_query()` method signature (no LLM parameters)
  - [x] 6.4 Remove `max_tokens` parameter from `aurora_query()` method signature (no LLM parameters)
  - [x] 6.5 Add `limit: int = 10` parameter to control number of chunks returned
  - [x] 6.6 Add `type_filter: str | None = None` parameter for filtering by memory type (`code`, `reas`, `know`)
  - [x] 6.7 Simplify `verbose: bool | None = None` to `verbose: bool = False` (simpler default)
  - [x] 6.8 Update `_validate_parameters()` to remove model/temperature/max_tokens validation and add type_filter validation (must be one of: `code`, `reas`, `know`, or `None`)
  - [x] 6.9 Rewrite `aurora_query()` method body to: validate params, retrieve chunks, assess complexity, build response - no API key checks, no budget checks, no LLM calls
  - [x] 6.10 Update docstring to reflect new behavior: returns structured context for host LLM to reason about, not LLM-generated answers
  - [x] 6.11 Ensure method still returns `str` (JSON string) for MCP compatibility
  - [x] 6.12 Run `pytest tests/unit/mcp/test_aurora_query_simplified.py -v` - ALL tests should pass now (TDD GREEN)

- [x] 7.0 Implement aurora_get Tool (New MCP Tool)
  - [x] 7.1 Add `_last_search_results` class attribute to `AuroraMCPTools` for session cache of last search results
  - [x] 7.2 Add `_last_search_timestamp` attribute for cache expiry tracking (10 minute timeout)
  - [x] 7.3 Modify `aurora_search` to store results in `_last_search_results` with timestamp
  - [x] 7.4 Modify `aurora_query` to store results in `_last_search_results` with timestamp
  - [x] 7.5 Implement `aurora_get(self, index: int) -> str` method per FR-11.2
  - [x] 7.6 Implement cache expiry check (10 minutes) - return error if cache expired
  - [x] 7.7 Implement index validation: must be >= 1 and <= len(results)
  - [x] 7.8 Return full chunk with all metadata per FR-11.4 response format
  - [x] 7.9 Return clear error message for out-of-range index per FR-11.5
  - [x] 7.10 Return clear error message if no previous search exists
  - [x] 7.11 Add docstring explaining workflow: search → see numbered results → get by index
  - [x] 7.12 Run `pytest tests/unit/mcp/test_aurora_get.py -v` - ALL tests should pass now (TDD GREEN)

- [x] 8.0 Update MCP Server Tool Registration
  - [x] 8.1 Update `aurora_query` tool registration in `server.py` `_register_tools()` method to use new signature: `query`, `limit`, `type_filter`, `verbose`
  - [x] 8.2 Update docstring in server registration to remove references to API key, SOAR pipeline, model selection, and LLM-generated answers
  - [x] 8.3 Update docstring examples to show new usage pattern (retrieval-only, no force_soar)
  - [x] 8.4 Remove the "Note" section about requiring ANTHROPIC_API_KEY from docstring
  - [x] 8.5 Add note that MCP tools return context for the host LLM (Claude Code CLI) to reason about
  - [x] 8.6 Register `aurora_get` tool in `server.py` `_register_tools()` method
  - [x] 8.7 Verify tool registration by running `python -m aurora.mcp.server --test` and checking both aurora_query and aurora_get are listed

### Phase 3: Integration & Verification

- [x] 9.0 Integration Tests (Write First - TDD RED, then implement)
  - [x] 9.1 Create integration test file `tests/integration/test_mcp_no_api_key.py`
  - [x] 9.2 Create test fixture that unsets `ANTHROPIC_API_KEY` environment variable and clears any cached config
  - [x] 9.3 Add test `test_aurora_search_no_api_key` verifying aurora_search works without API key
  - [x] 9.4 Add test `test_aurora_index_no_api_key` verifying aurora_index works without API key
  - [x] 9.5 Add test `test_aurora_stats_no_api_key` verifying aurora_stats works without API key
  - [x] 9.6 Add test `test_aurora_context_no_api_key` verifying aurora_context works without API key
  - [x] 9.7 Add test `test_aurora_related_no_api_key` verifying aurora_related works without API key
  - [x] 9.8 Add test `test_aurora_query_no_api_key` verifying aurora_query works without API key and returns structured context (not APIKeyMissing error)
  - [x] 9.9 Add test `test_aurora_get_no_api_key` verifying aurora_get works without API key
  - [x] 9.10 Create E2E test file `tests/e2e/test_mcp_e2e.py` with `test_index_then_query_returns_context`, `test_query_with_type_filter`, `test_query_empty_index_low_confidence`
  - [x] 9.11 Run full test suite: `pytest tests/unit/mcp/ tests/integration/test_mcp_no_api_key.py tests/e2e/test_mcp_e2e.py -v`
  - [x] 9.12 Run verification command from PRD: `unset ANTHROPIC_API_KEY && python -m aurora.mcp.server --test`
  - [x] 9.13 Verify line count: `wc -l src/aurora/mcp/tools.py` should show ~700 lines (includes new aurora_get)
  - [x] 9.14 Run `make quality-check` to ensure all quality gates pass (lint, type-check, tests)

### Phase 4: Documentation

- [x] 10.0 Comprehensive Documentation Updates
  - [x] 10.1 Update `docs/MCP_SETUP.md` with CLI vs MCP comparison table per FR-12.2
  - [x] 10.2 Add explanation of fundamental difference (MCP inside CC CLI = no API key, CLI standalone = needs API key) per FR-12.3
  - [x] 10.3 Add `aurora_get` tool documentation to `docs/MCP_SETUP.md` Available Tools section
  - [x] 10.4 Update `docs/cli/CLI_USAGE_GUIDE.md` with API key requirements table
  - [x] 10.5 Update `docs/cli/QUICK_START.md` with note about MCP vs CLI API key differences
  - [x] 10.6 Update `docs/TROUBLESHOOTING.md` - remove API key troubleshooting for MCP tools
  - [x] 10.7 Update `README.md` Quick Start section with MCP vs CLI distinction
  - [x] 10.8 Update `docs/KNOWLEDGE_BASE.md` MCP section with new tool count (7) and comparison table
  - [x] 10.9 Update all tool docstrings in `tools.py` to state "No API key required" per FR-12.5
  - [x] 10.10 Verify all documentation references 7 MCP tools (not 6)

---

## Verification Checklist (Definition of Done)

From PRD Section 9:

- [x] All 7 MCP tools work without `ANTHROPIC_API_KEY` environment variable
- [x] All MCP tools work without API key in `~/.aurora/config.json`
- [x] `aurora_query` returns structured JSON context (not LLM answer)
- [x] Response includes numbered chunks with relevance scores
- [x] Response includes `retrieval_confidence` score
- [x] Low confidence responses include suggestion text
- [x] Type filtering works (`code`, `reas`, `know`, `null`)
- [x] Heuristic complexity assessment retained
- [x] CLI `$ aur query` still works with API key (not modified)
- [x] ~560 lines removed from `tools.py` (net: ~1,011 with aurora_get added)
- [x] ~800 lines of tests archived with README
- [x] All new unit tests pass (22/22 aurora_query_simplified, 12/12 aurora_get)
- [x] All integration tests pass (21 integration + 16 E2E)
- [x] CI/CD pipeline passes without LLM mocks
- [x] `aurora_get` tool implemented with session cache
- [x] `aurora_get` returns full chunk by index from last search
- [x] Documentation updated with CLI vs MCP comparison table
- [x] All 6 docs files updated per FR-12.4
