# PRD 0008: MCP aurora_query Simplification

**Version:** 1.0
**Date:** 2025-12-26
**Status:** Draft
**Author:** Product Manager Agent

---

## 1. Introduction / Overview

### Problem Statement

AURORA's MCP `aurora_query` tool currently calls the Anthropic API directly, requiring users to configure an API key even when running inside Claude Code CLI or Claude Desktop. This is fundamentally flawed because:

1. **Redundant LLM calls**: When MCP tools run inside Claude Code CLI, the CLI *is* the LLM. Calling Anthropic API from MCP means paying twice for reasoning.
2. **Unnecessary API key requirement**: Users with Claude Pro subscriptions should not need a separate Anthropic API key for MCP tools.
3. **CI/CD complexity**: LLM mockups in tests have inflated the test suite, causing CI/CD failures and maintenance burden.
4. **Codebase bloat**: The feature set has grown beyond what was originally envisioned, making the codebase difficult to maintain.

### Proposed Solution

Remove all LLM API calls from MCP tools. MCP tools perform **code-only work** (retrieval, heuristic assessment) and return structured context to the host LLM (Claude Code CLI or Claude Desktop). The host LLM performs all reasoning using the user's existing subscription.

**Key Principle:**
- MCP tools (inside CC CLI/Desktop) = NO API KEY EVER
- CLI commands (`$ aur query`) = Needs API KEY (running outside LLM context)

### High-Level Goal

Simplify AURORA to be a **thin interoperability layer** that is portable across CLI AI agents and Desktop applications, without requiring separate API credentials for MCP usage.

---

## 2. Goals

### Primary Goals

1. **Remove API key requirement for MCP tools**: All 7 MCP tools (including new `aurora_get`) must function without any Anthropic API key when running inside Claude Code CLI or Claude Desktop.

2. **Reduce codebase complexity**: Delete approximately 700 lines of LLM-related code from `tools.py` and 800 lines of associated tests.

3. **Simplify CI/CD**: Eliminate LLM mockups from test suite, reducing test complexity and CI/CD failures.

4. **Maintain CLI functionality**: The `$ aur query` command continues to work with API key for terminal usage (outside LLM context).

### Secondary Goals

5. **Improve response times**: MCP tool calls become faster (no API round-trips).

6. **Reduce costs**: Users no longer pay for redundant LLM calls when using MCP inside Claude Code CLI.

7. **Archive removed tests**: Preserve deleted test code in `/tests/archive/` for reference.

8. **Add aurora_get tool**: New MCP tool to retrieve chunk by index from last search results (user says "#4" → get item 4).

9. **Comprehensive documentation**: Update all docs with CLI vs MCP comparison table showing API key requirements.

### Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| `tools.py` lines | ~1,166 | ~700 (+aurora_get, -LLM code) |
| `test_aurora_query_tool.py` lines | ~1,407 | ~600 (-57%) |
| API key required for MCP | YES | NO |
| CI/CD test complexity | High (LLM mocks) | Low (pure code) |
| MCP response time | ~2-5s (API call) | <100ms (retrieval only) |
| MCP tools count | 6 | 7 (+aurora_get) |
| Docs with CLI/MCP comparison | 0 | 6 files updated |

---

## 3. User Stories

### US-1: Claude Code CLI User (Primary)

**As a** Claude Code CLI user with a Pro subscription,
**I want** AURORA MCP tools to work without configuring an API key,
**So that** I can use memory search and context retrieval without extra setup or costs.

**Acceptance Criteria:**
- `aurora_query` tool works without `ANTHROPIC_API_KEY` set
- Tool returns structured context that Claude Code CLI can use for reasoning
- No error messages about missing API key

### US-2: Claude Desktop User

**As a** Claude Desktop user,
**I want** AURORA MCP tools to return relevant code context,
**So that** Claude Desktop can reason about my codebase using its built-in capabilities.

**Acceptance Criteria:**
- All MCP tools function without API key configuration
- Returned context includes relevance scores for ranking
- Desktop can display and reason about retrieved chunks

### US-3: CLI Terminal User

**As a** developer using the `aur` CLI in my terminal,
**I want** `$ aur query` to still work with my API key,
**So that** I can get AI-powered answers when not inside an LLM context.

**Acceptance Criteria:**
- `$ aur query` continues to require `ANTHROPIC_API_KEY`
- CLI behavior unchanged from current implementation
- Clear error message if API key missing

### US-4: Developer Maintaining AURORA

**As a** developer maintaining AURORA,
**I want** the codebase to be simpler with fewer LLM-related code paths,
**So that** I can understand and modify the code without tracking complex mock patterns.

**Acceptance Criteria:**
- ~700 lines of code removed from `tools.py`
- ~800 lines of tests archived
- No LLM mock patterns in MCP tool tests
- CI/CD passes without LLM-related flakiness

### US-5: Context Quality Feedback

**As a** Claude Code CLI user,
**I want** to know when retrieved context has low confidence,
**So that** I can refine my query or index more code.

**Acceptance Criteria:**
- Response includes `retrieval_confidence` score
- Scores below 0.5 include suggestion to refine query
- Empty results clearly indicate no matches found

---

## 4. Functional Requirements

### FR-1: MCP Tool API Key Removal

**FR-1.1** The system must allow all MCP tools to execute without any API key environment variable or configuration.

**FR-1.2** The system must remove the `_get_api_key()` method from `AuroraMCPTools` class.

**FR-1.3** The system must remove all code paths that check for or use API keys in MCP tools.

**FR-1.4** The system must NOT remove API key handling from CLI commands (`aurora_cli` package).

### FR-2: aurora_query Simplification

**FR-2.1** The `aurora_query` MCP tool must return structured context instead of LLM-generated answers.

**FR-2.2** The response format must be JSON with the following structure:
```json
{
  "context": {
    "chunks": [
      {
        "id": "code:path/to/file.py:function_name",
        "number": 1,
        "type": "code",
        "content": "def example(): ...",
        "file_path": "path/to/file.py",
        "line_range": [10, 25],
        "relevance_score": 0.85
      }
    ],
    "total_found": 15,
    "returned": 5
  },
  "assessment": {
    "complexity_score": 0.7,
    "suggested_approach": "complex",
    "retrieval_confidence": 0.85
  },
  "metadata": {
    "query": "original query text",
    "retrieval_time_ms": 45,
    "index_stats": {
      "total_chunks": 1500,
      "types": {"code": 1200, "reas": 200, "know": 100}
    }
  }
}
```

**FR-2.3** The system must number results (1, 2, 3...) for easy reference in conversation.

**FR-2.4** The system must include `retrieval_confidence` score (0.0-1.0) in response.

**FR-2.5** When `retrieval_confidence` is below 0.5, the response must include a suggestion field: `"suggestion": "Low confidence results. Consider refining your query or indexing more code."`

**FR-2.6** The system must retain the heuristic complexity assessment (`_assess_complexity()` method).

### FR-3: Code Removal

**FR-3.1** The system must remove the following methods from `tools.py`:
- `_get_api_key()`
- `_check_budget()` (for MCP context only)
- `_get_budget_error_message()`
- `_ensure_query_executor_initialized()`
- `_execute_with_retry()`
- `_is_transient_error()`
- `_execute_with_auto_escalation()`
- `_execute_direct_llm()`
- `_execute_soar()`

**FR-3.2** The system must retain the following methods:
- `_validate_parameters()` (modified: remove model validation)
- `_load_config()` (modified: remove API-key loading)
- `_assess_complexity()`
- `_get_memory_context()` (becomes primary function)
- `_format_response()` (modified: new response structure)
- `_format_error()`

**FR-3.3** The system must remove these parameters from `aurora_query`:
- `force_soar` (no SOAR pipeline in MCP)
- `model` (no LLM selection)
- `temperature` (no LLM parameters)
- `max_tokens` (no LLM parameters)

**FR-3.4** The `aurora_query` function signature must be simplified to:
```python
def aurora_query(
    self,
    query: str,
    limit: int = 10,
    type_filter: str | None = None,
    verbose: bool = False,
) -> str:
```

### FR-4: Type Filtering

**FR-4.1** The `aurora_query` tool must support filtering by memory type via `type_filter` parameter.

**FR-4.2** Valid type filters are: `"code"`, `"reas"`, `"know"`, or `None` (all types).

**FR-4.3** Invalid type filters must return an error with valid options listed.

### FR-5: Other MCP Tools (Review)

**FR-5.1** The `aurora_search` tool must continue to work without API key (already compliant).

**FR-5.2** The `aurora_index` tool must continue to work without API key (already compliant).

**FR-5.3** The `aurora_stats` tool must continue to work without API key (already compliant).

**FR-5.4** The `aurora_context` tool must continue to work without API key (already compliant).

**FR-5.5** The `aurora_related` tool must continue to work without API key (already compliant).

### FR-6: CLI Preservation

**FR-6.1** The CLI command `$ aur query` must continue to require `ANTHROPIC_API_KEY`.

**FR-6.2** The CLI code in `packages/cli/src/aurora_cli/` must remain unchanged.

**FR-6.3** The `QueryExecutor` and `AutoEscalationHandler` classes must remain unchanged.

### FR-7: Test Archival

**FR-7.1** The system must archive removed tests to `/tests/archive/2025-01-mcp-simplification/`.

**FR-7.2** The archive directory must include a `README.md` explaining:
- Why tests were archived
- What functionality they tested
- When they were archived
- Reference to this PRD

**FR-7.3** Archived test files must retain their original names.

### FR-8: Memory Schema

**FR-8.1** Each memory chunk must include the following fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier (e.g., `code:auth.py:login_user`, `know:pref:auth`) |
| `type` | enum | Yes | One of: `code`, `reas`, `know` |
| `content` | string | Yes | The actual content (code, JSON, text) |
| `project_path` | string | Yes | Absolute path to project root |
| `tags` | array | No | List of tags for categorization and decay policy |
| `decay_days` | int/null | No | Days until expiry (null = never decay) |
| `created_at` | datetime | Yes | Creation timestamp |
| `last_accessed` | datetime | Yes | Last access timestamp (for activation) |
| `access_count` | int | Yes | Number of accesses (for activation) |
| `embedding` | vector | No | Semantic embedding for search |
| `metadata` | object | No | Type-specific metadata |

**FR-8.2** The `metadata` field structure varies by type:

```json
// code type
{
  "file": "auth.py",
  "function": "login_user",
  "lines": [45, 67],
  "language": "python"
}

// reas type
{
  "session": "2025-12-26T10:30:00Z",
  "original_query": "How does auth work?",
  "decomposition": {...}
}

// know type
{
  "source": "conversation:session_xyz",
  "expires": "2025-06-25",
  "confidence": 0.85
}
```

**FR-8.3** Tags must support decay policy lookup from config.

### FR-9: Decay Policy Configuration

**FR-9.1** The system must support decay policy configuration in `~/.aurora/config.json`:

```json
{
  "memory": {
    "scope": "project",
    "decay": {
      "enabled": true,
      "default_days": 90,
      "by_tag": {
        "security": 180,
        "preference": 365,
        "temporary": 7,
        "critical": null
      },
      "by_type": {
        "code": null,
        "reas": 30,
        "know": 90
      }
    }
  }
}
```

**FR-9.2** Decay priority order:
1. Tag-specific decay (highest priority)
2. Type-specific decay
3. Default decay (lowest priority)
4. `null` = never decay

**FR-9.3** The system must apply decay during memory retrieval, filtering out expired chunks.

### FR-10: Project-Scoped Memory Storage

**FR-10.1** Memory must be stored per-project in `<project>/.aurora/` directory:

```
/home/user/my-project/
├── .aurora/
│   ├── memory.db        # SQLite database for this project
│   └── scratchpad.md    # Headless mode output
├── src/
└── ...
```

**FR-10.2** The `project_path` field must be set automatically based on:
- Current working directory when indexing
- Config file location if specified

**FR-10.3** Memory queries must default to current project scope.

**FR-10.4** Cross-project search must be explicitly requested via `--global` flag (CLI) or `global: true` parameter (MCP).

### FR-11: aurora_get Tool (New MCP Tool)

**FR-11.1** The system must add a new MCP tool `aurora_get` for retrieving chunks by index from search results.

**FR-11.2** The `aurora_get` function signature must be:
```python
def aurora_get(
    self,
    index: int,
) -> str:
```

**FR-11.3** The workflow for `aurora_get`:
1. User runs `aurora_search` or `aurora_query` → sees numbered results (1, 2, 3...)
2. User says "#4" or "get item 4" → Claude Code CLI invokes `aurora_get(index=4)`
3. `aurora_get` retrieves the full chunk content from the last search result set

**FR-11.4** The response format for `aurora_get`:
```json
{
  "chunk": {
    "id": "code:auth.py:login_user",
    "type": "code",
    "content": "def login_user(username, password):\n    ...",
    "file_path": "src/auth.py",
    "line_range": [45, 92],
    "metadata": {...}
  },
  "index": 4,
  "total_in_set": 15
}
```

**FR-11.5** If the index is out of range, return error:
```json
{
  "error": "Index 20 out of range. Last search returned 15 results (1-15).",
  "suggestion": "Run aurora_search or aurora_query first, then use aurora_get with a valid index."
}
```

**FR-11.6** The system must maintain a session cache of the last search results for `aurora_get` to reference.

**FR-11.7** The session cache must expire after 10 minutes of inactivity or when a new search is performed.

### FR-12: Documentation Updates

**FR-12.1** The system must update all documentation to reflect MCP vs CLI distinctions.

**FR-12.2** The `docs/MCP_SETUP.md` must include a comparison table:

| Feature | CLI Command | MCP Tool | API Key Required |
|---------|-------------|----------|------------------|
| Search code | `aur mem search "query"` | `aurora_search` | CLI: No, MCP: No |
| Query with AI | `aur query "question"` | `aurora_query` | CLI: Yes, MCP: No |
| Index code | `aur mem index .` | `aurora_index` | CLI: No, MCP: No |
| Get stats | `aur mem stats` | `aurora_stats` | CLI: No, MCP: No |
| Get chunk by ID | `aur mem get <id>` | `aurora_context` | CLI: No, MCP: No |
| Find related | `aur mem related <id>` | `aurora_related` | CLI: No, MCP: No |
| Get by index | N/A | `aurora_get` | CLI: N/A, MCP: No |

**FR-12.3** Documentation must explain the fundamental difference:
- **MCP tools** run inside Claude Code CLI → the CLI IS the LLM → no API key needed
- **CLI commands** run in terminal → need to call LLM API → API key required for `aur query`

**FR-12.4** The following documentation files must be updated:
- `docs/MCP_SETUP.md` - Primary MCP guide
- `docs/cli/CLI_USAGE_GUIDE.md` - CLI reference
- `docs/cli/QUICK_START.md` - Getting started
- `docs/TROUBLESHOOTING.md` - Common issues
- `README.md` - Project overview
- `docs/KNOWLEDGE_BASE.md` - Comprehensive reference

**FR-12.5** Each tool's docstring must clearly state whether API key is required.

---

## 5. Non-Goals (Out of Scope)

### Explicitly Out of Scope

1. **CLI command changes**: The `$ aur query`, `$ aur mem search`, and other CLI commands are NOT modified by this PRD.

2. **Memory architecture changes**: The memory types (`code:*`, `reas:*`, `know:*`) and storage structure are not changed.

3. **Headless mode fixes**: The `aur headless` command issues are tracked separately.

4. **Performance optimization**: While response times will improve naturally, this PRD does not include specific performance optimization work.

5. **Backward compatibility**: There is no backward compatibility requirement. MCP response format changes completely.

---

## 6. Design Considerations

### Current Architecture (Before)

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Code CLI                          │
│                    (User's Pro Subscription)                │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ MCP Protocol
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    AURORA MCP Server                        │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ aurora_query tool                                     │  │
│  │   1. Validate parameters                              │  │
│  │   2. Get API key ◄──────── PROBLEM: Requires key     │  │
│  │   3. Check budget                                     │  │
│  │   4. Assess complexity                                │  │
│  │   5. Call Anthropic API ◄─ PROBLEM: Redundant call   │  │
│  │   6. Return LLM response                              │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Target Architecture (After)

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Code CLI                          │
│                    (User's Pro Subscription)                │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Claude LLM (does all reasoning)                       │  │
│  │   - Receives structured context from MCP              │  │
│  │   - Generates answers using Pro subscription          │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ MCP Protocol
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    AURORA MCP Server                        │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ aurora_query tool (SIMPLIFIED)                        │  │
│  │   1. Validate parameters                              │  │
│  │   2. Assess complexity (heuristic)                    │  │
│  │   3. Retrieve from memory                             │  │
│  │   4. Return structured context ◄─ NO LLM CALL        │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### UI/UX Considerations

**For Claude Code CLI users:**
- No visible change in workflow
- `aurora_query` tool still available
- Claude uses returned context automatically

**For developers:**
- Response format changes (JSON structure)
- No more API key errors
- Faster tool responses

---

## 7. Technical Considerations

### Files to Modify

| File | Changes | Lines Changed |
|------|---------|---------------|
| `src/aurora/mcp/tools.py` | Remove LLM methods, simplify aurora_query | -560 lines |
| `src/aurora/mcp/server.py` | Update tool registration (fewer params) | ~10 lines |
| `tests/unit/mcp/test_aurora_query_tool.py` | Archive LLM tests, add context tests | -800, +200 |

### Dependencies

**No new dependencies required.**

**Dependencies removed/unused:**
- No direct Anthropic API calls from MCP tools
- No LLM retry logic needed

### Migration Path

1. **Phase 1**: Archive existing tests
2. **Phase 2**: Remove LLM methods from `tools.py`
3. **Phase 3**: Implement new response format
4. **Phase 4**: Update MCP server registration
5. **Phase 5**: Add new tests for simplified tool
6. **Phase 6**: Verify all MCP tools work without API key

### Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| CLI code accidentally modified | Low | High | Clear separation in requirements, code review |
| Tests not properly archived | Low | Medium | Verify archive before deletion |
| Response format breaks existing usage | N/A | N/A | No backward compat requirement |
| Heuristic assessment too simple | Medium | Low | Keep existing logic, can enhance later |

---

## 8. Test Plan

### Unit Tests (New)

**test_aurora_query_simplified.py:**

```python
# Test categories:

# 1. Parameter Validation
def test_query_empty_string_returns_error():
def test_query_whitespace_only_returns_error():
def test_invalid_type_filter_returns_error():
def test_valid_type_filters_accepted():

# 2. Response Format
def test_response_contains_context_section():
def test_response_contains_assessment_section():
def test_response_contains_metadata_section():
def test_chunks_are_numbered():
def test_relevance_scores_included():

# 3. Confidence Handling
def test_low_confidence_includes_suggestion():
def test_high_confidence_no_suggestion():
def test_empty_results_zero_confidence():

# 4. Type Filtering
def test_filter_code_type_only():
def test_filter_reas_type_only():
def test_filter_know_type_only():
def test_no_filter_returns_all_types():

# 5. Complexity Assessment
def test_simple_query_low_complexity():
def test_complex_query_high_complexity():
def test_long_query_medium_complexity():

# 6. No API Key Required
def test_works_without_api_key_env():
def test_works_without_config_api_key():
def test_no_api_key_error_messages():
```

**test_aurora_get.py:**

```python
# Test categories:

# 1. Basic Functionality
def test_get_valid_index_returns_chunk():
def test_get_first_item_index_1():
def test_get_last_item():

# 2. Error Handling
def test_get_index_zero_returns_error():
def test_get_negative_index_returns_error():
def test_get_index_out_of_range_returns_error():
def test_get_no_previous_search_returns_error():

# 3. Session Cache
def test_cache_stores_last_search_results():
def test_new_search_clears_previous_cache():
def test_cache_expires_after_timeout():

# 4. Response Format
def test_response_includes_full_chunk():
def test_response_includes_index_and_total():
```

### Integration Tests

**test_mcp_no_api_key.py:**

```python
# Test all MCP tools work without API key
def test_aurora_search_no_api_key():
def test_aurora_index_no_api_key():
def test_aurora_stats_no_api_key():
def test_aurora_context_no_api_key():
def test_aurora_related_no_api_key():
def test_aurora_query_no_api_key():
def test_aurora_get_no_api_key():
```

### E2E Tests

**test_mcp_e2e.py:**

```python
# Test full MCP flow
def test_index_then_query_returns_context():
def test_query_with_type_filter():
def test_query_empty_index_low_confidence():
```

### Tests to Archive

Move to `/tests/archive/2025-01-mcp-simplification/`:

```
test_aurora_query_tool.py (partial):
- TestAutoEscalation class
- TestRetryLogic class
- TestBudgetEnforcement class
- TestAPIKeyHandling class
- TestDirectLLMExecution class
- TestSOARExecution class
- test_execute_with_retry_* functions
- test_transient_error_* functions
```

---

## 9. Success Criteria

### Definition of Done

- [ ] All MCP tools work without `ANTHROPIC_API_KEY` environment variable
- [ ] All MCP tools work without API key in `~/.aurora/config.json`
- [ ] `aurora_query` returns structured JSON context (not LLM answer)
- [ ] Response includes numbered chunks with relevance scores
- [ ] Response includes `retrieval_confidence` score
- [ ] Low confidence responses include suggestion text
- [ ] Type filtering works (`code`, `reas`, `know`, `null`)
- [ ] Heuristic complexity assessment retained
- [ ] CLI `$ aur query` still works with API key
- [ ] ~560 lines removed from `tools.py`
- [ ] ~800 lines of tests archived with README
- [ ] All new unit tests pass
- [ ] All integration tests pass
- [ ] All E2E tests pass
- [ ] CI/CD pipeline passes without LLM mocks

### Verification Commands

```bash
# Verify no API key required for MCP
unset ANTHROPIC_API_KEY
python -m aurora.mcp.server --test

# Run new test suite
pytest tests/unit/mcp/test_aurora_query_simplified.py -v
pytest tests/integration/test_mcp_no_api_key.py -v
pytest tests/e2e/test_mcp_e2e.py -v

# Verify CLI still requires API key
unset ANTHROPIC_API_KEY
aur query "test"  # Should show API key error

export ANTHROPIC_API_KEY="sk-ant-..."
aur query "test"  # Should work

# Verify code reduction
wc -l src/aurora/mcp/tools.py  # Target: ~600 lines
```

---

## 10. Open Questions

### Resolved

1. **Q: Should CLI code be modified?**
   A: No. CLI code is separate and remains unchanged.

2. **Q: What heuristics to keep?**
   A: Keep existing keyword-based complexity assessment as-is.

3. **Q: Backward compatibility?**
   A: Not required. Complete change for MCP tools.

### Unresolved

1. **Q: Should `aurora_get` be added as a new MCP tool?**
   Note: Deferred to separate PRD. Current scope is simplification only.

2. **Q: Should documentation be updated as part of this PRD?**
   Note: Recommended as follow-up task, not blocking.

3. **Q: Should we add a "retrieval mode" to return raw chunks vs. formatted?**
   Note: Can be added later if needed. Start with single format.

---

## Appendix A: Code Removal Checklist

### Methods to Remove from `tools.py`

```python
# Lines ~617-639: _get_api_key()
# Lines ~641-713: _check_budget(), _get_budget_error_message()
# Lines ~715-727: _ensure_query_executor_initialized()
# Lines ~729-832: _is_transient_error(), _execute_with_retry()
# Lines ~834-883: _execute_with_auto_escalation()
# Lines ~925-978: _execute_direct_llm()
# Lines ~980-1065: _execute_soar()
```

### Parameters to Remove from aurora_query

```python
# Current signature:
def aurora_query(
    self,
    query: str,
    force_soar: bool = False,      # REMOVE
    verbose: bool | None = None,   # KEEP (but simplify)
    model: str | None = None,      # REMOVE
    temperature: float | None = None,  # REMOVE
    max_tokens: int | None = None,     # REMOVE
) -> str:

# New signature:
def aurora_query(
    self,
    query: str,
    limit: int = 10,
    type_filter: str | None = None,
    verbose: bool = False,
) -> str:
```

---

## Appendix B: Archive README Template

```markdown
# Archived Tests: MCP Simplification (2025-01)

## Why Archived

These tests were archived as part of PRD-0008 (MCP aurora_query Simplification).
The functionality they tested was removed because:

1. MCP tools no longer call LLM APIs directly
2. API key handling removed from MCP context
3. Budget enforcement moved to CLI-only
4. Retry logic for API calls no longer needed

## What Was Tested

- `TestAutoEscalation`: Auto-escalation from direct LLM to SOAR pipeline
- `TestRetryLogic`: Exponential backoff for transient API errors
- `TestBudgetEnforcement`: Monthly budget limits for API calls
- `TestAPIKeyHandling`: API key loading from env/config
- `TestDirectLLMExecution`: Direct Anthropic API calls
- `TestSOARExecution`: Full 9-phase SOAR pipeline execution

## When Archived

- Date: 2025-01-XX
- PRD: 0008-prd-mcp-aurora-query-simplification.md
- Commit: [to be filled]

## Reference

These tests may be useful if:
- Re-implementing LLM calls in MCP (not recommended)
- Understanding original aurora_query behavior
- Debugging CLI query command (which still uses this logic)
```

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-26 | PM Agent | Initial draft |
