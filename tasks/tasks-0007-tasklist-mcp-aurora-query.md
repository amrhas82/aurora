# Task List: MCP Aurora Query Integration

**PRD**: tasks-0007-prd-mcp-aurora-query-full-integration.md
**Version**: 2.0 - Complete with Sub-Tasks
**Status**: Ready for Implementation
**Sprint**: Medium (3-4 days, 28 hours estimated)
**Approach**: TDD with CI/CD focus

---

## Relevant Files

### Core Implementation Files
- `/home/hamr/PycharmProjects/aurora/src/aurora/mcp/tools.py` - aurora_query method fully implemented (lines 405-1041, 636 lines total)
  - Main method: aurora_query() - lines 405-507
  - Helper methods: _validate_parameters(), _load_config(), _get_api_key(), _check_budget(), _ensure_query_executor_initialized() - lines 509-719
  - Execution methods: _execute_with_auto_escalation(), _assess_complexity(), _execute_direct_llm(), _execute_soar() - lines 721-938
  - Response formatting: _format_response(), _extract_metadata(), _format_error() - lines 959-1041
- `/home/hamr/PycharmProjects/aurora/src/aurora/mcp/server.py` - Register aurora_query tool with FastMCP (pending Task 5.1)
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/execution.py` - Reference for QueryExecutor integration patterns
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/errors.py` - Reference for error handling patterns

### Test Files
- `/home/hamr/PycharmProjects/aurora/tests/unit/mcp/test_aurora_query_tool.py` - Unit tests for aurora_query (54 tests, ALL PASSING)
  - TestParameterValidation - 7 tests for parameter validation
  - TestConfigurationLoading - 8 tests for config loading
  - TestAPIKeyHandling - 2 tests for API key management
  - TestBudgetEnforcement - 2 tests for budget checking
  - TestAutoEscalation - 6 tests for complexity-based routing
  - TestResponseFormatting - 7 tests for response JSON structure
  - TestErrorHandling - 7 tests for error scenarios
  - TestVerbosityHandling - 3 tests for verbosity parameter
  - TestProgressTracking - 6 tests for SOAR phase tracking
  - TestEnhancedVerbosity - 6 tests for verbosity levels
- `/home/hamr/PycharmProjects/aurora/tests/integration/test_mcp_aurora_query_integration.py` - Integration tests (not yet created)
- `/home/hamr/PycharmProjects/aurora/tests/e2e/test_aurora_query_e2e.py` - End-to-end tests with real API (optional, not yet created)

### Documentation Files
- `/home/hamr/PycharmProjects/aurora/docs/MCP_SETUP.md` - Add aurora_query usage examples
- `/home/hamr/PycharmProjects/aurora/docs/TROUBLESHOOTING.md` - Add error scenarios and solutions
- `/home/hamr/PycharmProjects/aurora/README.md` - Update to reflect complete MCP functionality

### Configuration Files
- `~/.aurora/config.json` - User configuration (query settings, API key, budget)
- `~/.aurora/budget_tracker.json` - Budget tracking state

---

## Implementation Notes

### Testing Framework
- Use pytest with fixtures from `/home/hamr/PycharmProjects/aurora/tests/integration/test_mcp_python_client.py`
- Follow TDD: Write test FIRST, watch it fail, implement, watch it pass
- Mock all external dependencies (LLM API, file system where possible)
- Run tests locally with Python 3.12 before CI/CD submission

### Architectural Patterns
- Follow existing MCP tool patterns from `tools.py` (aurora_search, aurora_index, etc.)
- Use `@log_performance` decorator for timing metrics
- Lazy initialization of components in `_ensure_initialized()`
- Return JSON strings for both success and error responses
- Reuse QueryExecutor from CLI package (no code duplication)

### Error Handling Strategy
- All errors return JSON with `{"error": {...}}` structure
- Include "To fix this:" guidance in every error message
- Log all errors to `~/.aurora/logs/mcp.log`
- Implement retry logic for transient LLM API failures
- Graceful degradation for non-critical failures (memory unavailable)

### Configuration Priority
1. Environment variables (highest priority)
2. Function parameters (override defaults)
3. Config file `~/.aurora/config.json`
4. Hard-coded defaults (lowest priority)

---

## Tasks

- [x] 1.0 Implement aurora_query MCP Tool (Core Implementation)
  - [x] 1.1 Write unit tests for parameter validation (TDD) (1.5h)
  - [x] 1.2 Add aurora_query method skeleton to AuroraMCPTools (0.5h)
  - [x] 1.3 Implement parameter validation logic (1h)
  - [x] 1.4 Implement configuration loading (_load_config helper) (1h)
  - [x] 1.5 Implement API key loading (_get_api_key helper) (0.5h)
  - [x] 1.6 Implement budget checking integration (1h)
  - [x] 1.7 Initialize QueryExecutor with configuration (1h)
  - [x] 1.8 Implement auto-escalation logic (complexity assessment) (1.5h)

- [x] 2.0 Add Progress Visibility and Response Formatting
  - [x] 2.1 Write unit tests for response formatting (TDD) (1h)
  - [x] 2.2 Implement _format_response helper method (1.5h)
  - [x] 2.3 Implement _extract_metadata helper method (1h)
  - [x] 2.4 Implement progress tracking for SOAR phases (1.5h)
  - [x] 2.5 Add verbosity handling (verbose vs non-verbose) (1h)

- [ ] 3.0 Implement Error Handling and User Messages
  - [ ] 3.1 Write unit tests for error scenarios (TDD) (1.5h)
  - [ ] 3.2 Implement _format_error helper method (0.5h)
  - [ ] 3.3 Add error messages for all 6 error types (1h)
  - [ ] 3.4 Implement LLM API retry logic (1h)
  - [ ] 3.5 Add graceful degradation for memory unavailable (0.5h)
  - [ ] 3.6 Add error logging to mcp.log (0.5h)

- [ ] 4.0 Write Tests (TDD - 75 tests total)
  - [ ] 4.1 Write unit tests for configuration loading (1h)
  - [ ] 4.2 Write unit tests for auto-escalation logic (1h)
  - [ ] 4.3 Write unit tests for response formatting (1h)
  - [ ] 4.4 Write integration tests for direct LLM execution (1h)
  - [ ] 4.5 Write integration tests for SOAR pipeline (1.5h)
  - [ ] 4.6 Write integration tests for error scenarios (1h)
  - [ ] 4.7 Write E2E tests with real API (optional) (0.5h)

- [ ] 5.0 Documentation, CI/CD Validation, and Integration
  - [ ] 5.1 Register aurora_query in server.py (0.5h)
  - [ ] 5.2 Update MCP_SETUP.md with usage examples (0.5h)
  - [ ] 5.3 Update TROUBLESHOOTING.md with error scenarios (0.5h)
  - [ ] 5.4 Update README.md with MCP query feature (0.25h)
  - [ ] 5.5 Run make quality-check and fix issues (0.25h)

---

## Detailed Task Breakdown

### Task 1.0: Implement aurora_query MCP Tool (Core Implementation)
**Total Time**: 8 hours | **Priority**: P0 (Critical) | **Dependencies**: None

#### 1.1 Write unit tests for parameter validation (TDD) (1.5h)
**Priority**: P0 | **Dependencies**: None

**Files**:
- Create: `/home/hamr/PycharmProjects/aurora/tests/unit/mcp/test_aurora_query_tool.py`
- Reference: `/home/hamr/PycharmProjects/aurora/tests/integration/test_mcp_python_client.py` (for fixtures)

**Implementation**:
- [ ] Create test file with pytest structure
- [ ] Write test for empty query (should fail with InvalidParameter)
- [ ] Write test for whitespace-only query (should fail)
- [ ] Write test for temperature out of range [0.0, 1.0] (should fail)
- [ ] Write test for negative max_tokens (should fail)
- [ ] Write test for invalid model string (should fail)
- [ ] Write test for valid parameters (should pass validation)
- [ ] Run tests - ALL SHOULD FAIL (no implementation yet)

**Acceptance Criteria**:
- 7 unit tests written for parameter validation
- All tests fail initially (TDD - no implementation)
- Test file follows pytest conventions (test class, test methods, fixtures)
- Tests are isolated and can run independently

**Verification**:
```bash
pytest tests/unit/mcp/test_aurora_query_tool.py::TestParameterValidation -v
# Expected: 7 failed (no aurora_query method exists yet)
```

---

#### 1.2 Add aurora_query method skeleton to AuroraMCPTools (0.5h)
**Priority**: P0 | **Dependencies**: Task 1.1

**Files**:
- Modify: `/home/hamr/PycharmProjects/aurora/src/aurora/mcp/tools.py`

**Implementation**:
- [ ] Add aurora_query method after aurora_related method (line ~403)
- [ ] Define method signature with all 6 parameters:
  - query: str
  - force_soar: bool = False
  - verbose: bool | None = None
  - model: str | None = None
  - temperature: float | None = None
  - max_tokens: int | None = None
- [ ] Add @log_performance("aurora_query") decorator
- [ ] Add docstring following existing pattern (see aurora_search for reference)
- [ ] Return placeholder: `return json.dumps({"answer": "Not implemented"})`
- [ ] Initialize helper attributes in __init__:
  - `self._query_executor: QueryExecutor | None = None`
  - `self._config: dict[str, Any] | None = None`

**Acceptance Criteria**:
- Method signature matches PRD API specification
- Docstring includes all 6 parameters with descriptions
- Method returns valid JSON (even if placeholder)
- No syntax errors, imports correct

**Verification**:
```bash
python3 -c "from aurora.mcp.tools import AuroraMCPTools; t = AuroraMCPTools(':memory:'); print(t.aurora_query('test'))"
# Expected: {"answer": "Not implemented"}
```

---

#### 1.3 Implement parameter validation logic (1h)
**Priority**: P0 | **Dependencies**: Task 1.2

**Files**:
- Modify: `/home/hamr/PycharmProjects/aurora/src/aurora/mcp/tools.py`

**Implementation**:
- [ ] Add validation at start of aurora_query method:
  - Check query is non-empty and not whitespace-only
  - Check temperature is in [0.0, 1.0] if provided
  - Check max_tokens is positive if provided
  - Check model is non-empty string if provided
- [ ] Call _format_error() for validation failures (will implement in Task 3.2)
- [ ] For now, use basic error dict: `{"error": {"type": "InvalidParameter", "message": "...", "suggestion": "..."}}`
- [ ] Add helper method: `_validate_parameters(query, temperature, max_tokens, model) -> tuple[bool, str | None]`

**Acceptance Criteria**:
- Empty query returns InvalidParameter error
- Invalid temperature returns InvalidParameter error
- Invalid max_tokens returns InvalidParameter error
- Valid parameters pass validation
- Parameter validation tests (Task 1.1) now PASS

**Verification**:
```bash
pytest tests/unit/mcp/test_aurora_query_tool.py::TestParameterValidation -v
# Expected: 7 passed (all validation tests pass)
```

---

#### 1.4 Implement configuration loading (_load_config helper) (1h)
**Priority**: P0 | **Dependencies**: Task 1.3

**Files**:
- Modify: `/home/hamr/PycharmProjects/aurora/src/aurora/mcp/tools.py`

**Implementation**:
- [ ] Add `_load_config()` method to AuroraMCPTools class
- [ ] Read `~/.aurora/config.json` if exists, parse JSON
- [ ] Handle missing file gracefully (return empty dict)
- [ ] Handle JSON parse errors (log warning, return empty dict)
- [ ] Set defaults for missing values:
  - `api.default_model`: "claude-sonnet-4-20250514"
  - `api.temperature`: 0.7
  - `api.max_tokens`: 4000
  - `query.auto_escalate`: true
  - `query.complexity_threshold`: 0.6
  - `query.verbosity`: "normal"
- [ ] Override with environment variables:
  - `AURORA_MODEL` → `api.default_model`
  - `AURORA_VERBOSITY` → `query.verbosity`
- [ ] Cache config in `self._config` (lazy load on first call)

**Acceptance Criteria**:
- Config loaded from ~/.aurora/config.json if exists
- Defaults applied for missing values
- Environment variables override config file
- Invalid JSON doesn't crash (logs warning, uses defaults)
- Config cached (only loaded once per instance)

**Verification**:
```bash
# Create test config
mkdir -p ~/.aurora
echo '{"api": {"temperature": 0.9}}' > ~/.aurora/config.json

# Test config loading
python3 -c "
from aurora.mcp.tools import AuroraMCPTools
t = AuroraMCPTools(':memory:')
config = t._load_config()
assert config['api']['temperature'] == 0.9
assert config['api']['default_model'] == 'claude-sonnet-4-20250514'
print('Config loading: PASS')
"
```

---

#### 1.5 Implement API key loading (_get_api_key helper) (0.5h)
**Priority**: P0 | **Dependencies**: Task 1.4

**Files**:
- Modify: `/home/hamr/PycharmProjects/aurora/src/aurora/mcp/tools.py`

**Implementation**:
- [ ] Add `_get_api_key()` method to AuroraMCPTools class
- [ ] Check environment variable `ANTHROPIC_API_KEY` first (highest priority)
- [ ] If not found, check config: `self._load_config()["api"]["anthropic_key"]`
- [ ] Return None if not found in either location
- [ ] Do NOT log API key (security)

**Acceptance Criteria**:
- Environment variable takes precedence over config file
- Returns None if not found (doesn't raise exception)
- API key never logged or printed
- Empty string treated as "not found"

**Verification**:
```bash
# Test env var priority
ANTHROPIC_API_KEY="test-key-env" python3 -c "
from aurora.mcp.tools import AuroraMCPTools
t = AuroraMCPTools(':memory:')
key = t._get_api_key()
assert key == 'test-key-env'
print('API key loading: PASS')
"
```

---

#### 1.6 Implement budget checking integration (1h)
**Priority**: P0 | **Dependencies**: Task 1.5

**Files**:
- Modify: `/home/hamr/PycharmProjects/aurora/src/aurora/mcp/tools.py`
- Reference: Budget tracking logic from CLI (search for "budget" in codebase)

**Implementation**:
- [ ] Add `_check_budget()` method to AuroraMCPTools class
- [ ] Read budget tracker from `~/.aurora/budget_tracker.json`
- [ ] Get current monthly usage (USD)
- [ ] Get monthly limit from config (default: 50.0)
- [ ] Estimate query cost (rough estimate: $0.01 for direct LLM, $0.05 for SOAR)
- [ ] Return True if usage + estimate < limit, False otherwise
- [ ] Handle missing budget file (create with 0 usage)
- [ ] Add helper: `_get_budget_error_message()` to format budget exceeded message

**Acceptance Criteria**:
- Budget checked before query execution
- Returns True when under limit, False when exceeded
- Budget file created if missing (initialized to 0 usage)
- Estimate is conservative (overestimate to avoid surprises)

**Verification**:
```bash
# Test budget checking
python3 -c "
from aurora.mcp.tools import AuroraMCPTools
import json

# Create budget file (near limit)
budget = {'monthly_usage_usd': 49.5, 'monthly_limit_usd': 50.0}
with open('/tmp/test_budget.json', 'w') as f:
    json.dump(budget, f)

t = AuroraMCPTools(':memory:')
# Mock budget path to test file
# Test will verify budget checking logic
print('Budget checking: PASS')
"
```

---

#### 1.7 Initialize QueryExecutor with configuration (1h)
**Priority**: P0 | **Dependencies**: Task 1.6

**Files**:
- Modify: `/home/hamr/PycharmProjects/aurora/src/aurora/mcp/tools.py`
- Add import: `from aurora_cli.execution import QueryExecutor`

**Implementation**:
- [ ] Add `_ensure_query_executor_initialized()` method
- [ ] Check if `self._query_executor is None`
- [ ] If None:
  - Load config via `_load_config()`
  - Create QueryExecutor instance: `QueryExecutor(config=self._config)`
  - Store in `self._query_executor`
- [ ] Call this method at start of `aurora_query()` (after parameter validation)
- [ ] Follow pattern of `_ensure_initialized()` for consistency

**Acceptance Criteria**:
- QueryExecutor initialized lazily (only on first query)
- Config passed to QueryExecutor constructor
- Subsequent queries reuse same QueryExecutor instance
- No initialization errors

**Verification**:
```bash
pytest tests/unit/mcp/test_aurora_query_tool.py::TestQueryExecutorInitialization -v
# Write test that mocks QueryExecutor and verifies initialization
```

---

#### 1.8 Implement auto-escalation logic (complexity assessment) (1.5h)
**Priority**: P0 | **Dependencies**: Task 1.7

**Files**:
- Modify: `/home/hamr/PycharmProjects/aurora/src/aurora/mcp/tools.py`

**Implementation**:
- [ ] Add `_execute_with_auto_escalation()` method
- [ ] Check `force_soar` parameter:
  - If True: call `_execute_soar()` directly
  - If False: assess complexity first
- [ ] Implement simple complexity assessment (keyword-based for now):
  - Simple queries (complexity < 0.6): "what is", "define", "explain briefly"
  - Complex queries (complexity >= 0.6): "compare", "analyze", "design", "architecture"
  - Return complexity score 0.0-1.0
- [ ] If complexity < threshold (default 0.6): call `_execute_direct_llm()`
- [ ] If complexity >= threshold: call `_execute_soar()`
- [ ] Add helper methods:
  - `_execute_direct_llm(query, api_key, verbose, config) -> dict`
  - `_execute_soar(query, api_key, verbose, config) -> dict`

**Acceptance Criteria**:
- Simple queries use direct LLM path
- Complex queries use SOAR pipeline
- force_soar parameter bypasses assessment
- Complexity threshold configurable in config.json
- Both execution paths return dict with answer and metadata

**Verification**:
```bash
pytest tests/unit/mcp/test_aurora_query_tool.py::TestAutoEscalation -v
# Tests should verify complexity assessment and path selection
```

---

### Task 2.0: Add Progress Visibility and Response Formatting
**Total Time**: 6 hours | **Priority**: P1 (High) | **Dependencies**: Task 1.0

#### 2.1 Write unit tests for response formatting (TDD) (1h)
**Priority**: P1 | **Dependencies**: Task 1.8

**Files**:
- Modify: `/home/hamr/PycharmProjects/aurora/tests/unit/mcp/test_aurora_query_tool.py`

**Implementation**:
- [ ] Add TestResponseFormatting class
- [ ] Test response includes required fields (answer, execution_path, metadata)
- [ ] Test metadata includes duration, cost, tokens, model, temperature
- [ ] Test verbose response includes phases array
- [ ] Test non-verbose response excludes phases
- [ ] Test sources field populated when memory used
- [ ] Test sources field absent when no memory used
- [ ] All tests should FAIL initially (no formatting implemented)

**Acceptance Criteria**:
- 7 response formatting tests written
- All tests fail initially (TDD)
- Tests cover both verbose and non-verbose modes
- Tests verify JSON structure matches PRD FR-4.1

**Verification**:
```bash
pytest tests/unit/mcp/test_aurora_query_tool.py::TestResponseFormatting -v
# Expected: 7 failed (no response formatting yet)
```

---

#### 2.2 Implement _format_response helper method (1.5h)
**Priority**: P1 | **Dependencies**: Task 2.1

**Files**:
- Modify: `/home/hamr/PycharmProjects/aurora/src/aurora/mcp/tools.py`

**Implementation**:
- [ ] Add `_format_response(result: dict, verbose: bool) -> str` method
- [ ] Build response structure per PRD FR-4.1:
  - `answer`: result["answer"]
  - `execution_path`: result["execution_path"] (direct_llm or soar_pipeline)
  - `metadata`: extract via `_extract_metadata(result)`
- [ ] If verbose=True and execution_path=soar_pipeline:
  - Add `phases`: result["phase_trace"]["phases"]
- [ ] If result contains "sources":
  - Add `sources`: result["sources"]
- [ ] Return JSON string with indent=2 for readability

**Acceptance Criteria**:
- Response formatted as JSON string
- All required fields present (answer, execution_path, metadata)
- Optional fields only present when applicable (phases, sources)
- JSON is valid and parseable
- Response formatting tests (Task 2.1) now PASS

**Verification**:
```bash
pytest tests/unit/mcp/test_aurora_query_tool.py::TestResponseFormatting -v
# Expected: 7 passed
```

---

#### 2.3 Implement _extract_metadata helper method (1h)
**Priority**: P1 | **Dependencies**: Task 2.2

**Files**:
- Modify: `/home/hamr/PycharmProjects/aurora/src/aurora/mcp/tools.py`

**Implementation**:
- [ ] Add `_extract_metadata(result: dict) -> dict` method
- [ ] Extract from result dict:
  - `duration_seconds`: result.get("duration", 0.0)
  - `cost_usd`: result.get("cost", 0.0)
  - `input_tokens`: result.get("input_tokens", 0)
  - `output_tokens`: result.get("output_tokens", 0)
  - `model`: result.get("model", "unknown")
  - `temperature`: result.get("temperature", 0.7)
- [ ] Round floats to 2 decimal places for readability
- [ ] Return metadata dict

**Acceptance Criteria**:
- Metadata dict contains all 6 required fields
- Missing values use sensible defaults
- Floats rounded to 2 decimal places
- No exceptions for missing keys

**Verification**:
```bash
python3 -c "
from aurora.mcp.tools import AuroraMCPTools
t = AuroraMCPTools(':memory:')
result = {'duration': 1.234, 'cost': 0.0123, 'input_tokens': 100}
metadata = t._extract_metadata(result)
assert metadata['duration_seconds'] == 1.23
assert metadata['cost_usd'] == 0.01
print('Metadata extraction: PASS')
"
```

---

#### 2.4 Implement progress tracking for SOAR phases (1.5h)
**Priority**: P1 | **Dependencies**: Task 2.3

**Files**:
- Modify: `/home/hamr/PycharmProjects/aurora/src/aurora/mcp/tools.py`

**Implementation**:
- [ ] Add progress logging to `_execute_soar()` method
- [ ] Define 9 SOAR phase names:
  - Assess, Retrieve, Decompose, Verify, Route, Collect, Synthesize, Record, Respond
- [ ] Before each phase, log progress message:
  - `logger.info(f"[{phase_num}/9] {phase_description}...")`
- [ ] After each phase, log completion with timing:
  - `logger.info(f"  → {phase_summary} ({duration}s)")`
- [ ] Store phase trace in result dict for verbose mode
- [ ] Follow pattern from PRD "Progress Visibility Design" section

**Acceptance Criteria**:
- Progress messages logged for all 9 SOAR phases
- Messages are declarative and user-friendly
- Timing included for each phase
- Phase trace stored in result dict for response formatting

**Verification**:
```bash
# Run integration test with verbose logging
pytest tests/integration/test_mcp_aurora_query_integration.py::test_soar_progress -v --log-cli-level=INFO
# Expected: See 9 progress messages in output
```

---

#### 2.5 Add verbosity handling (verbose vs non-verbose) (1h)
**Priority**: P1 | **Dependencies**: Task 2.4

**Files**:
- Modify: `/home/hamr/PycharmProjects/aurora/src/aurora/mcp/tools.py`

**Implementation**:
- [ ] In aurora_query method, determine verbosity:
  - If `verbose` parameter is not None: use parameter value
  - Else: read from config `query.verbosity` ("quiet", "normal", "verbose")
  - Map to boolean: "verbose" → True, others → False
- [ ] Pass verbose flag to execution methods
- [ ] In `_format_response()`:
  - If verbose=False: exclude phases array
  - If verbose=True: include full phase trace
- [ ] In progress logging:
  - If verbose=False: only log start/end
  - If verbose=True: log all 9 phases

**Acceptance Criteria**:
- Verbosity determined from parameter or config
- Verbose mode includes full details
- Non-verbose mode shows minimal output
- Config setting respected when parameter not provided

**Verification**:
```bash
pytest tests/unit/mcp/test_aurora_query_tool.py::TestVerbosity -v
# Tests should verify verbose vs non-verbose output
```

---

### Task 3.0: Implement Error Handling and User Messages
**Total Time**: 5 hours | **Priority**: P1 (High) | **Dependencies**: Task 1.0

#### 3.1 Write unit tests for error scenarios (TDD) (1.5h)
**Priority**: P1 | **Dependencies**: Task 2.5

**Files**:
- Modify: `/home/hamr/PycharmProjects/aurora/tests/unit/mcp/test_aurora_query_tool.py`

**Implementation**:
- [ ] Add TestErrorHandling class
- [ ] Test missing API key returns APIKeyMissing error
- [ ] Test budget exceeded returns BudgetExceeded error
- [ ] Test SOAR phase failure returns SOARPhaseFailed error
- [ ] Test invalid parameter returns InvalidParameter error
- [ ] Test memory unavailable logs warning (not error)
- [ ] Test LLM API failure with retries
- [ ] Test each error includes "suggestion" field with "To fix this:"
- [ ] All tests should FAIL initially

**Acceptance Criteria**:
- 7 error handling tests written
- All tests fail initially (TDD)
- Tests verify error structure matches PRD FR-4.2
- Tests check for actionable "suggestion" field

**Verification**:
```bash
pytest tests/unit/mcp/test_aurora_query_tool.py::TestErrorHandling -v
# Expected: 7 failed (no error handling implemented)
```

---

#### 3.2 Implement _format_error helper method (0.5h)
**Priority**: P1 | **Dependencies**: Task 3.1

**Files**:
- Modify: `/home/hamr/PycharmProjects/aurora/src/aurora/mcp/tools.py`

**Implementation**:
- [ ] Add `_format_error(error_type, message, suggestion, details=None) -> str`
- [ ] Build error structure per PRD FR-4.2:
  ```json
  {
    "error": {
      "type": error_type,
      "message": message,
      "suggestion": suggestion,
      "details": details  # optional
    }
  }
  ```
- [ ] Return JSON string with indent=2
- [ ] Log error to logger before returning

**Acceptance Criteria**:
- Error formatted as JSON string
- All 4 fields present (type, message, suggestion, details optional)
- JSON is valid and parseable
- Error logged before returning

**Verification**:
```bash
python3 -c "
from aurora.mcp.tools import AuroraMCPTools
t = AuroraMCPTools(':memory:')
error = t._format_error('TestError', 'Test message', 'Test fix')
import json
e = json.loads(error)
assert e['error']['type'] == 'TestError'
print('Error formatting: PASS')
"
```

---

#### 3.3 Add error messages for all 6 error types (1h)
**Priority**: P1 | **Dependencies**: Task 3.2

**Files**:
- Modify: `/home/hamr/PycharmProjects/aurora/src/aurora/mcp/tools.py`

**Implementation**:
- [ ] Add error message constants at module level or as class attributes
- [ ] Implement each error type per PRD "Error Catalog":

**Error 1: APIKeyMissing**
```python
return self._format_error(
    error_type="APIKeyMissing",
    message="API key not found. AURORA requires an Anthropic API key to execute queries.",
    suggestion=(
        "To fix this:\n"
        "1. Set environment variable: export ANTHROPIC_API_KEY=\"your-key\"\n"
        "2. Or add to config file: ~/.aurora/config.json under \"api.anthropic_key\"\n\n"
        "Get your API key at: https://console.anthropic.com/\n\n"
        "See docs/TROUBLESHOOTING.md for more details."
    )
)
```

**Error 2: BudgetExceeded**
```python
return self._format_error(
    error_type="BudgetExceeded",
    message="Monthly budget limit reached. Cannot execute query.",
    suggestion=self._get_budget_suggestion(),  # dynamic based on current usage
    details={
        "current_usage_usd": current_usage,
        "monthly_limit_usd": limit,
        "estimated_query_cost_usd": estimate
    }
)
```

**Error 3-6**: Follow same pattern for SOARPhaseFailed, InvalidParameter, MemoryUnavailable, LLMAPIFailure

**Acceptance Criteria**:
- All 6 error messages implemented
- Each includes actionable "To fix this:" section
- Messages are friendly and non-technical
- Dynamic values included where relevant (budget, file paths)

**Verification**:
```bash
pytest tests/unit/mcp/test_aurora_query_tool.py::TestErrorHandling -v
# Expected: 7 passed (all error tests pass)
```

---

#### 3.4 Implement LLM API retry logic (1h)
**Priority**: P1 | **Dependencies**: Task 3.3

**Files**:
- Modify: `/home/hamr/PycharmProjects/aurora/src/aurora/mcp/tools.py`

**Implementation**:
- [ ] Add `_execute_with_retry(func, *args, **kwargs)` helper method
- [ ] Implement retry logic:
  - Maximum 3 attempts
  - Exponential backoff: 100ms, 200ms, 400ms
  - Catch transient errors: rate limits, timeouts, 5xx server errors
  - Don't retry on: authentication errors, invalid requests
- [ ] Wrap LLM calls in `_execute_direct_llm()` and `_execute_soar()` with retry
- [ ] Log each retry attempt (warning level)
- [ ] After 3 failures, return LLMAPIFailure error

**Acceptance Criteria**:
- LLM calls retry up to 3 times on transient failures
- Exponential backoff between retries
- Non-transient errors fail immediately (no retry)
- All retries logged with attempt number
- Final failure returns helpful error message

**Verification**:
```bash
pytest tests/unit/mcp/test_aurora_query_tool.py::TestRetryLogic -v
# Mock LLM to fail 2 times then succeed - should pass
# Mock LLM to always fail - should fail with LLMAPIFailure error
```

---

#### 3.5 Add graceful degradation for memory unavailable (0.5h)
**Priority**: P1 | **Dependencies**: Task 3.4

**Files**:
- Modify: `/home/hamr/PycharmProjects/aurora/src/aurora/mcp/tools.py`

**Implementation**:
- [ ] In `_execute_direct_llm()` and `_execute_soar()`:
  - Try to retrieve memory context
  - If memory store is empty or unavailable:
    - Log warning: "Memory store not available. Answering from base knowledge."
    - Continue execution WITHOUT memory context
    - Do NOT return error (graceful degradation)
- [ ] Add `_get_memory_context(query, limit=3)` helper method
- [ ] Wrap memory retrieval in try-except
- [ ] Return empty string if memory unavailable (don't block query)

**Acceptance Criteria**:
- Missing memory doesn't block query execution
- Warning logged when memory unavailable
- Query proceeds with LLM base knowledge only
- No exception raised for missing memory

**Verification**:
```bash
pytest tests/unit/mcp/test_aurora_query_tool.py::TestMemoryGracefulDegradation -v
# Test with empty memory store - should succeed with warning
```

---

#### 3.6 Add error logging to mcp.log (0.5h)
**Priority**: P1 | **Dependencies**: Task 3.5

**Files**:
- Modify: `/home/hamr/PycharmProjects/aurora/src/aurora/mcp/tools.py`

**Implementation**:
- [ ] Ensure logger is configured (already done in config.py)
- [ ] In `_format_error()`:
  - Log error with full details: `logger.error(f"{error_type}: {message}")`
  - Include stack trace if exception: `logger.error(..., exc_info=True)`
- [ ] In `aurora_query()` exception handler:
  - Catch all unexpected exceptions
  - Log with stack trace
  - Return formatted error to user
- [ ] Verify logs go to `~/.aurora/logs/mcp.log`

**Acceptance Criteria**:
- All errors logged to mcp.log
- Stack traces included for unexpected exceptions
- Log file created if doesn't exist
- No sensitive data logged (API keys, user data)

**Verification**:
```bash
# Trigger error and check log
python3 -c "
from aurora.mcp.tools import AuroraMCPTools
t = AuroraMCPTools(':memory:')
t.aurora_query('')  # Empty query - should error
"
tail ~/.aurora/logs/mcp.log
# Expected: See InvalidParameter error logged
```

---

### Task 4.0: Write Tests (TDD - 75 tests total)
**Total Time**: 7 hours | **Priority**: P0 (Critical - CI/CD blocker) | **Dependencies**: Tasks 1.0, 2.0, 3.0

#### 4.1 Write unit tests for configuration loading (1h)
**Priority**: P0 | **Dependencies**: Task 3.6

**Files**:
- Modify: `/home/hamr/PycharmProjects/aurora/tests/unit/mcp/test_aurora_query_tool.py`

**Implementation**:
- [ ] Add TestConfigurationLoading class
- [ ] Test config loaded from ~/.aurora/config.json
- [ ] Test defaults applied when config missing
- [ ] Test environment variables override config
- [ ] Test ANTHROPIC_API_KEY from env var
- [ ] Test ANTHROPIC_API_KEY from config file
- [ ] Test env var priority over config file
- [ ] Test invalid JSON in config (should use defaults)
- [ ] Test config caching (only loaded once)

**Acceptance Criteria**:
- 8 configuration tests written and passing
- Tests use tmp_path fixture for isolated config files
- Tests verify priority: env var > config > defaults
- Tests cover error cases (missing file, invalid JSON)

**Verification**:
```bash
pytest tests/unit/mcp/test_aurora_query_tool.py::TestConfigurationLoading -v
# Expected: 8 passed
```

---

#### 4.2 Write unit tests for auto-escalation logic (1h)
**Priority**: P0 | **Dependencies**: Task 4.1

**Files**:
- Modify: `/home/hamr/PycharmProjects/aurora/tests/unit/mcp/test_aurora_query_tool.py`

**Implementation**:
- [ ] Add TestAutoEscalation class
- [ ] Test simple query uses direct LLM (complexity < 0.6)
- [ ] Test complex query uses SOAR (complexity >= 0.6)
- [ ] Test force_soar bypasses escalation
- [ ] Test complexity threshold configurable
- [ ] Mock QueryExecutor to verify which method called
- [ ] Test execution_path in response ("direct_llm" vs "soar_pipeline")

**Acceptance Criteria**:
- 6 auto-escalation tests written and passing
- Tests verify correct execution path chosen
- Tests use mocking to avoid actual LLM calls
- Tests confirm force_soar parameter works

**Verification**:
```bash
pytest tests/unit/mcp/test_aurora_query_tool.py::TestAutoEscalation -v
# Expected: 6 passed
```

---

#### 4.3 Write unit tests for response formatting (1h)
**Priority**: P0 | **Dependencies**: Task 4.2

**Files**:
- Modify: `/home/hamr/PycharmProjects/aurora/tests/unit/mcp/test_aurora_query_tool.py`

**Implementation**:
- [ ] Add TestResponseFormatting class (if not already from Task 2.1)
- [ ] Test response JSON structure
- [ ] Test required fields present (answer, execution_path, metadata)
- [ ] Test metadata fields (duration, cost, tokens, model, temp)
- [ ] Test verbose response includes phases
- [ ] Test non-verbose response excludes phases
- [ ] Test sources field when memory used
- [ ] Test sources field absent when no memory
- [ ] Test response is valid JSON

**Acceptance Criteria**:
- 8 response formatting tests written and passing
- Tests verify JSON structure matches PRD
- Tests cover verbose and non-verbose modes
- Tests validate all required/optional fields

**Verification**:
```bash
pytest tests/unit/mcp/test_aurora_query_tool.py::TestResponseFormatting -v
# Expected: 8 passed
```

---

#### 4.4 Write integration tests for direct LLM execution (1h)
**Priority**: P0 | **Dependencies**: Task 4.3

**Files**:
- Create: `/home/hamr/PycharmProjects/aurora/tests/integration/test_mcp_aurora_query_integration.py`
- Reference: `/home/hamr/PycharmProjects/aurora/tests/integration/test_mcp_python_client.py`

**Implementation**:
- [ ] Create integration test file with fixtures
- [ ] Add fixture for test database with indexed code
- [ ] Test simple query end-to-end with mocked LLM
- [ ] Test memory context included in prompt
- [ ] Test cost tracking updated after query
- [ ] Test response includes all required fields
- [ ] Mock AnthropicClient.generate() to return test response
- [ ] Verify database state after query

**Acceptance Criteria**:
- 4 integration tests written and passing
- Tests use real Store, real memory, mocked LLM only
- Tests verify end-to-end flow from query to response
- Tests confirm cost tracking works

**Verification**:
```bash
pytest tests/integration/test_mcp_aurora_query_integration.py::TestDirectLLMExecution -v
# Expected: 4 passed
```

---

#### 4.5 Write integration tests for SOAR pipeline (1.5h)
**Priority**: P0 | **Dependencies**: Task 4.4

**Files**:
- Modify: `/home/hamr/PycharmProjects/aurora/tests/integration/test_mcp_aurora_query_integration.py`

**Implementation**:
- [ ] Add TestSOARPipelineExecution class
- [ ] Test complex query triggers SOAR
- [ ] Test force_soar parameter works
- [ ] Test verbose mode includes 9 phases
- [ ] Test phase timing included in response
- [ ] Test SOAR phase failure handling
- [ ] Mock SOAR orchestrator if needed
- [ ] Verify phase trace in response

**Acceptance Criteria**:
- 5 SOAR integration tests written and passing
- Tests verify SOAR pipeline executed
- Tests confirm phase trace captured
- Tests validate error handling for phase failures

**Verification**:
```bash
pytest tests/integration/test_mcp_aurora_query_integration.py::TestSOARPipelineExecution -v
# Expected: 5 passed
```

---

#### 4.6 Write integration tests for error scenarios (1h)
**Priority**: P0 | **Dependencies**: Task 4.5

**Files**:
- Modify: `/home/hamr/PycharmProjects/aurora/tests/integration/test_mcp_aurora_query_integration.py`

**Implementation**:
- [ ] Add TestErrorScenarios class
- [ ] Test missing API key returns friendly error
- [ ] Test budget exceeded scenario
- [ ] Test LLM API failure with retries
- [ ] Test retry exhaustion returns error
- [ ] Test graceful degradation (memory unavailable)
- [ ] Verify error messages include "suggestion" field
- [ ] Verify errors logged to mcp.log

**Acceptance Criteria**:
- 6 error scenario tests written and passing
- Tests verify error messages are user-friendly
- Tests confirm retry logic works
- Tests validate graceful degradation

**Verification**:
```bash
pytest tests/integration/test_mcp_aurora_query_integration.py::TestErrorScenarios -v
# Expected: 6 passed
```

---

#### 4.7 Write E2E tests with real API (optional) (0.5h)
**Priority**: P2 (Optional) | **Dependencies**: Task 4.6

**Files**:
- Create: `/home/hamr/PycharmProjects/aurora/tests/e2e/test_aurora_query_e2e.py`

**Implementation**:
- [ ] Add pytestmark to skip if no ANTHROPIC_API_KEY
- [ ] Test simple query with real API
- [ ] Test complex query with real API
- [ ] Test verbose response with real API
- [ ] Verify actual cost tracking
- [ ] Mark tests with @pytest.mark.e2e

**Acceptance Criteria**:
- 3-5 E2E tests written
- Tests skipped if ANTHROPIC_API_KEY not set
- Tests pass when API key available
- Tests use @pytest.mark.e2e marker

**Verification**:
```bash
# Without API key
pytest tests/e2e/test_aurora_query_e2e.py -v
# Expected: 5 skipped

# With API key
ANTHROPIC_API_KEY="..." pytest tests/e2e/test_aurora_query_e2e.py -v
# Expected: 5 passed (or skipped if no key)
```

---

### Task 5.0: Documentation, CI/CD Validation, and Integration
**Total Time**: 2 hours | **Priority**: P0 (Critical) | **Dependencies**: All previous tasks

#### 5.1 Register aurora_query in server.py (0.5h)
**Priority**: P0 | **Dependencies**: Tasks 1-4 complete

**Files**:
- Modify: `/home/hamr/PycharmProjects/aurora/src/aurora/mcp/server.py`

**Implementation**:
- [ ] Add aurora_query tool registration in `_register_tools()` method
- [ ] Add after aurora_related tool (line ~120)
- [ ] Follow existing pattern (decorator + docstring + return)
- [ ] Include all 6 parameters in tool signature
- [ ] Add comprehensive docstring with examples

```python
@self.mcp.tool()
def aurora_query(
    query: str,
    force_soar: bool = False,
    verbose: bool | None = None,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    """
    Execute AURORA query with reasoning and memory integration.

    Args:
        query: The question or prompt to process
        force_soar: If True, always use SOAR pipeline (skip auto-escalation)
        verbose: If True, include phase trace and detailed metrics
        model: Override default LLM model
        temperature: Override default temperature (0.0-1.0)
        max_tokens: Override default max tokens

    Returns:
        JSON string with answer and metadata
    """
    return self.tools.aurora_query(query, force_soar, verbose, model, temperature, max_tokens)
```

**Acceptance Criteria**:
- aurora_query registered with FastMCP
- Tool appears in `aurora-mcp status` output
- Docstring includes all parameters and examples
- No syntax errors

**Verification**:
```bash
python3 -m aurora.mcp.server --test
# Expected: aurora_query listed in available tools
```

---

#### 5.2 Update MCP_SETUP.md with usage examples (0.5h)
**Priority**: P0 | **Dependencies**: Task 5.1

**Files**:
- Modify: `/home/hamr/PycharmProjects/aurora/docs/MCP_SETUP.md`

**Implementation**:
- [ ] Add "aurora_query Tool" section after existing tools
- [ ] Include description of direct LLM vs SOAR pipeline
- [ ] Add usage examples:
  - Simple query
  - Complex query with auto-escalation
  - Force SOAR mode
  - Verbose output
  - Custom model/temperature
- [ ] Add note about API key requirement
- [ ] Add link to TROUBLESHOOTING.md for errors

**Acceptance Criteria**:
- MCP_SETUP.md updated with aurora_query section
- At least 5 usage examples included
- Examples show different parameter combinations
- Documentation clear for junior developers

**Verification**:
```bash
# Manual review
cat /home/hamr/PycharmProjects/aurora/docs/MCP_SETUP.md | grep -A 20 "aurora_query"
# Expected: See new section with examples
```

---

#### 5.3 Update TROUBLESHOOTING.md with error scenarios (0.5h)
**Priority**: P0 | **Dependencies**: Task 5.2

**Files**:
- Modify: `/home/hamr/PycharmProjects/aurora/docs/TROUBLESHOOTING.md`

**Implementation**:
- [ ] Add "MCP Query Errors" section
- [ ] Document all 6 error types:
  - APIKeyMissing: how to set API key
  - BudgetExceeded: how to adjust budget
  - SOARPhaseFailed: troubleshooting steps
  - InvalidParameter: valid parameter ranges
  - MemoryUnavailable: how to index codebase
  - LLMAPIFailure: checking API status
- [ ] Include example error messages and solutions
- [ ] Add FAQ for common issues

**Acceptance Criteria**:
- TROUBLESHOOTING.md updated with query errors
- All 6 error types documented
- Solutions are actionable and clear
- Examples match actual error messages

**Verification**:
```bash
# Manual review
cat /home/hamr/PycharmProjects/aurora/docs/TROUBLESHOOTING.md | grep -A 10 "MCP Query"
# Expected: See new section with error scenarios
```

---

#### 5.4 Update README.md with MCP query feature (0.25h)
**Priority**: P0 | **Dependencies**: Task 5.3

**Files**:
- Modify: `/home/hamr/PycharmProjects/aurora/README.md`

**Implementation**:
- [ ] Update "Features" section to mention aurora_query
- [ ] Update "MCP Integration" section (if exists)
- [ ] Add note about feature parity with CLI
- [ ] Update installation instructions if needed
- [ ] Mention "MCP is primary interface" (per user requirements)

**Acceptance Criteria**:
- README.md mentions aurora_query feature
- Feature parity with CLI highlighted
- MCP noted as primary interface
- Updates are concise (don't bloat README)

**Verification**:
```bash
cat /home/hamr/PycharmProjects/aurora/README.md | grep -i "aurora_query\|mcp.*query"
# Expected: See mention of aurora_query
```

---

#### 5.5 Run make quality-check and fix issues (0.25h)
**Priority**: P0 | **Dependencies**: All previous tasks

**Files**:
- All modified files

**Implementation**:
- [ ] Run `make quality-check` locally
- [ ] Fix any linting errors (ruff)
- [ ] Fix any type errors (mypy) - NEW code must be 0 errors
- [ ] Ensure all tests pass (pytest)
- [ ] Verify coverage ≥80% for new code
- [ ] Fix any issues found
- [ ] Re-run until all checks pass

**Acceptance Criteria**:
- `make quality-check` passes locally (green)
- No new mypy errors introduced
- No ruff linting errors
- All tests pass (unit + integration)
- Coverage ≥80% for aurora_query code

**Verification**:
```bash
make quality-check
# Expected: All checks pass
# - Ruff: No issues
# - MyPy: 0 new errors (existing 6 in llm_client.py are tracked separately)
# - Tests: All pass
# - Coverage: ≥74% overall, ≥80% for new code
```

---

## Dependencies Map

```
1.1 (tests) → 1.2 (skeleton) → 1.3 (validation) → 1.4 (config) → 1.5 (api key) → 1.6 (budget) → 1.7 (executor) → 1.8 (escalation)
                                                                                                                      ↓
2.1 (tests) → 2.2 (format) → 2.3 (metadata) → 2.4 (progress) → 2.5 (verbosity) ←──────────────────────────────────┘
                                                                     ↓
3.1 (tests) → 3.2 (format_error) → 3.3 (messages) → 3.4 (retry) → 3.5 (graceful) → 3.6 (logging)
                                                                     ↓
4.1 (config tests) → 4.2 (escalation tests) → 4.3 (format tests) → 4.4 (integration direct) → 4.5 (integration soar) → 4.6 (error tests) → 4.7 (e2e)
                                                                     ↓
5.1 (register) → 5.2 (setup doc) → 5.3 (troubleshoot doc) → 5.4 (readme) → 5.5 (quality check)
```

---

## Testing Checkpoints

### Checkpoint 1: After Task 1.3 (Parameter Validation)
```bash
pytest tests/unit/mcp/test_aurora_query_tool.py::TestParameterValidation -v
# Expected: 7 passed
```

### Checkpoint 2: After Task 1.8 (Core Implementation Complete)
```bash
pytest tests/unit/mcp/test_aurora_query_tool.py -v
# Expected: ~20 passed (all core functionality tests)
```

### Checkpoint 3: After Task 2.5 (Response Formatting Complete)
```bash
pytest tests/unit/mcp/test_aurora_query_tool.py::TestResponseFormatting -v
pytest tests/unit/mcp/test_aurora_query_tool.py::TestVerbosity -v
# Expected: 15 passed
```

### Checkpoint 4: After Task 3.6 (Error Handling Complete)
```bash
pytest tests/unit/mcp/test_aurora_query_tool.py::TestErrorHandling -v
# Expected: 7 passed
```

### Checkpoint 5: After Task 4.6 (All Tests Complete)
```bash
pytest tests/unit/mcp/test_aurora_query_tool.py -v
pytest tests/integration/test_mcp_aurora_query_integration.py -v
# Expected: ~75 passed total
```

### Checkpoint 6: Final (After Task 5.5 - CI/CD)
```bash
make quality-check
# Expected: All checks pass (ruff, mypy, tests, coverage)
```

---

## Critical Success Factors

1. **TDD First**: Write tests BEFORE implementation (Tasks 1.1, 2.1, 3.1, 4.1-4.7)
2. **Local Testing**: Run ALL tests locally before CI/CD submission
3. **Reuse CLI Code**: Use QueryExecutor, ErrorHandler, ConfigManager from CLI
4. **Friendly Errors**: Every error has actionable "To fix this:" guidance
5. **CI/CD Focus**: Fix issues locally, don't rely on CI to catch them

---

## Risk Mitigation Strategies

**Risk 1: CI/CD Failures**
- Run `make quality-check` locally BEFORE pushing
- Use Python 3.12 for local testing (matches CI)
- Mock all external dependencies
- Add `@pytest.mark.skipif(os.getenv('CI'))` for flaky tests

**Risk 2: Integration Complexity**
- Write integration tests early (Task 4.4-4.6)
- Test both execution paths independently
- Use real components with mocked LLM only

**Risk 3: Budget Tracking**
- Explicit integration tests for budget updates (Task 4.6)
- Verify cost calculations match Anthropic pricing
- Log all budget changes for audit

---

## Manual Testing Checklist (Optional - After Task 5.5)

- [ ] Tool appears in Claude Desktop tool list
- [ ] Simple query returns answer (<2s)
- [ ] Complex query triggers SOAR pipeline
- [ ] Verbose mode shows 9 phases
- [ ] Error messages display correctly
- [ ] Budget enforcement works
- [ ] Memory integration works (if indexed)

---

**END OF TASK LIST**

Ready for implementation! Start with Task 1.1 (Write unit tests for parameter validation).
