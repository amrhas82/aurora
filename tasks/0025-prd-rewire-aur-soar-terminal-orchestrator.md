# PRD-0025: Rewire `aur soar` as Terminal Orchestrator Wrapper

**Status:** Draft
**Created:** 2026-01-07
**Author:** Product Manager Agent
**Priority:** High

---

## 1. Introduction/Overview

### Problem Statement

The current `aur soar` command (`packages/cli/src/aurora_cli/commands/soar.py`) is a **parallel implementation** that duplicates all 9 SOAR phases inline with simplified prompts. It does not use the actual `SOAROrchestrator` class from `packages/soar/src/aurora_soar/orchestrator.py`, which means it misses critical features:

- **Retry logic** with exponential backoff on LLM failures
- **Budget tracking** and cost enforcement
- **Error handling** with graceful degradation
- **Real phase implementations** with proper prompts from `aurora_reasoning.prompts.*`
- **Conversation logging** and pattern caching
- **Token usage tracking** and cost accounting

The current implementation is ~500 lines of duplicated phase logic that must be maintained separately from the orchestrator.

### Proposed Solution

Rewire `aur soar` as a **thin wrapper** (~50-80 lines) that:

1. Creates a new `CLIPipeLLMClient` that implements the `LLMClient` interface but pipes to external CLI tools (claude, cursor, etc.) instead of making API calls
2. Instantiates `SOAROrchestrator` with this CLI client injected
3. Uses an optional `phase_callback` for terminal UX display
4. Calls `orchestrator.execute(query)` and displays results

### High-Level Goal

Eliminate code duplication by having `aur soar` delegate to `SOAROrchestrator`, gaining all its capabilities (retry, budgets, real prompts) while providing terminal-specific UX through callbacks.

---

## 2. Goals

- **Reduce code duplication:** Shrink `soar.py` from ~500 lines to ~50-80 lines
- **Achieve feature parity:** Inherit orchestrator's retry/fallback handling, budget tracking, and real phase implementations
- **Improve maintainability:** Single source of truth for SOAR phase logic
- **Preserve backward compatibility:** Keep existing CLI interface (`--tool`, `--model`, `--verbose` flags)
- **Enable extensibility:** Extensible pattern for adding new CLI tools beyond claude/cursor

---

## 3. User Stories

### US-1: User runs SOAR query with Claude CLI

**As a** developer using Aurora,
**I want to** run `aur soar "What is SOAR orchestrator?"`,
**So that** I get an intelligent answer processed through all 9 SOAR phases using the Claude CLI.

**Acceptance Criteria:**
- Command executes successfully with default `--tool=claude`
- All 9 phases are displayed with appropriate owner labels (`[ORCHESTRATOR]` or `[LLM -> claude]`)
- Final answer is displayed in a formatted box
- Execution time and log path are shown

### US-2: User runs SOAR query with alternate tool

**As a** developer with Cursor installed,
**I want to** run `aur soar "Explain memory" --tool cursor`,
**So that** I can use my preferred AI tool for LLM phases.

**Acceptance Criteria:**
- Command accepts `--tool cursor` parameter
- LLM phases show `[LLM -> cursor]` in terminal output
- Command fails gracefully if specified tool not found in PATH

### US-3: User configures default tool via environment variable

**As a** developer who always uses Cursor,
**I want to** set `AURORA_SOAR_TOOL=cursor` in my environment,
**So that** I don't need to specify `--tool` every time.

**Acceptance Criteria:**
- Environment variable `AURORA_SOAR_TOOL` is respected
- CLI flag `--tool` overrides environment variable
- Default is `claude` if neither is set

### US-4: User benefits from orchestrator retry logic

**As a** developer using Aurora,
**I want** transient LLM failures to be automatically retried,
**So that** occasional network hiccups don't fail my queries.

**Acceptance Criteria:**
- When CLI tool returns non-zero exit code, orchestrator retry logic kicks in
- User sees retry attempts in verbose mode
- Query succeeds after transient failure if retry succeeds

### US-5: User sees clear phase ownership in terminal

**As a** developer watching SOAR execution,
**I want to** see which phases run locally vs. call the LLM,
**So that** I understand the execution flow.

**Acceptance Criteria:**
- Phase 1, 2, 5, 8 show `[ORCHESTRATOR]`
- Phase 3, 4, 6, 7, 9 show `[LLM -> <tool>]`
- Each phase shows its number and name
- Phase result summary is displayed after completion

---

## 4. Functional Requirements

### FR-1: CLIPipeLLMClient Implementation

The system must create a new `CLIPipeLLMClient` class that:

1. **FR-1.1:** Implements the `LLMClient` abstract interface from `aurora_reasoning.llm_client`
2. **FR-1.2:** Implements `generate(prompt, ...)` method that:
   - Accepts prompt string and optional parameters (model, max_tokens, temperature, system)
   - Pipes prompt to external CLI tool using subprocess: `<tool> -p`
   - Captures stdout/stderr with 180-second timeout
   - Returns `LLMResponse` with content, model name, estimated token counts
   - Raises `RuntimeError` on non-zero exit code (for orchestrator retry)
3. **FR-1.3:** Implements `generate_json(prompt, ...)` method that:
   - Calls `generate()` with JSON-enforcing system prompt
   - Extracts JSON from response using `extract_json_from_text()`
   - Returns parsed Python dict
4. **FR-1.4:** Implements `count_tokens(text)` method that:
   - Returns `len(text) // 4` as token estimate (standard heuristic)
5. **FR-1.5:** Implements `default_model` property that:
   - Returns the tool name (e.g., "claude", "cursor")
6. **FR-1.6:** Accepts `tool` parameter in constructor specifying CLI tool name
7. **FR-1.7:** Validates tool exists in PATH during construction
8. **FR-1.8:** Located at `packages/cli/src/aurora_cli/llm/cli_pipe_client.py`

### FR-2: Phase Callback Support in SOAROrchestrator

The system must add optional `phase_callback` parameter to `SOAROrchestrator`:

1. **FR-2.1:** Constructor accepts optional `phase_callback: Callable[[str, str, dict], None] | None`
2. **FR-2.2:** Callback signature: `phase_callback(phase_name, status, result_summary)`
   - `phase_name`: String like "assess", "retrieve", "decompose", etc.
   - `status`: Either "before" or "after"
   - `result_summary`: Dict with phase-specific summary data (empty dict for "before")
3. **FR-2.3:** Callback is invoked before and after each phase execution
4. **FR-2.4:** Callback exceptions are caught and logged, not propagated (non-blocking)
5. **FR-2.5:** Callback is optional; orchestrator works unchanged if not provided

### FR-3: Rewritten `aur soar` Command

The system must rewrite the `soar` command as a thin wrapper:

1. **FR-3.1:** Preserves existing CLI interface:
   - `aur soar <query>` - positional query argument
   - `--model`, `-m` - model selection (sonnet/opus)
   - `--tool`, `-t` - CLI tool to pipe to (default: "claude")
   - `--verbose`, `-v` - verbose output flag
2. **FR-3.2:** Reads `AURORA_SOAR_TOOL` environment variable as default for `--tool`
3. **FR-3.3:** Creates `CLIPipeLLMClient` with specified tool
4. **FR-3.4:** Instantiates `SOAROrchestrator` with:
   - `reasoning_llm`: CLIPipeLLMClient instance
   - `solving_llm`: Same CLIPipeLLMClient instance (both use same CLI tool)
   - `phase_callback`: Terminal display callback function
   - Other required dependencies (store, agent_registry, config)
5. **FR-3.5:** Calls `orchestrator.execute(query)` and displays result
6. **FR-3.6:** Displays header box with query summary
7. **FR-3.7:** Displays final answer in formatted box
8. **FR-3.8:** Shows execution time and log path
9. **FR-3.9:** Total rewritten code should be ~50-80 lines (excluding imports)

### FR-4: Terminal UX Phase Callback

The system must implement a phase callback for terminal display:

1. **FR-4.1:** Shows phase header with owner, number, and name:
   - Format for orchestrator phases: `[ORCHESTRATOR] Phase N: Name`
   - Format for LLM phases: `[LLM -> tool] Phase N: Name`
2. **FR-4.2:** Phase ownership classification:
   | Phase | Number | Owner |
   |-------|--------|-------|
   | Assess | 1 | ORCHESTRATOR |
   | Retrieve | 2 | ORCHESTRATOR |
   | Decompose | 3 | LLM |
   | Verify | 4 | LLM |
   | Route | 5 | ORCHESTRATOR |
   | Collect | 6 | LLM |
   | Synthesize | 7 | LLM |
   | Record | 8 | ORCHESTRATOR |
   | Respond | 9 | LLM |
3. **FR-4.3:** Shows brief result summary after each phase completes
4. **FR-4.4:** Uses Rich console for styled output (blue for orchestrator, green for LLM)
5. **FR-4.5:** Terminal UX must match this exact format:
   ```
   ╭─────────── Aurora SOAR ───────────╮
   │ Query: what is ACT-R memory?      │
   ╰───────────────────────────────────╯

   [ORCHESTRATOR] Phase 1: Assess
     Complexity: MEDIUM (score: 24, confidence: 85%)

   [ORCHESTRATOR] Phase 2: Retrieve
     Matched: 5 chunks from memory

   [LLM → claude] Phase 3: Decompose
     Breaking query into subgoals...
     ✓ 3 subgoals identified

   [LLM → claude] Phase 4: Verify
     Validating decomposition...
     ✓ PASS

   [ORCHESTRATOR] Phase 5: Route
     Assigned: web-search, analyzer

   [LLM → claude] Phase 6: Collect
     Researching subgoals...
     ✓ Research complete

   [LLM → claude] Phase 7: Synthesize
     Combining findings...
     ✓ Answer ready

   [ORCHESTRATOR] Phase 8: Record
     ✓ Pattern cached

   [LLM → claude] Phase 9: Respond
     Formatting response...

   ╭─────────── Final Answer ───────────╮
   │ ...                                │
   ╰────────────────────────────────────╯

   Log: .aurora/logs/conversations/2026/01/act-r-memory-2026-01-07.md
   ```
6. **FR-4.6:** Phase descriptions (2-liner context per phase):
   | Phase | Description shown during execution |
   |-------|-----------------------------------|
   | Assess | "Analyzing query complexity..." |
   | Retrieve | "Looking up memory index..." |
   | Decompose | "Breaking query into subgoals..." |
   | Verify | "Validating decomposition..." |
   | Route | "Assigning agents to subgoals..." |
   | Collect | "Researching subgoals..." |
   | Synthesize | "Combining findings..." |
   | Record | "Caching reasoning pattern..." |
   | Respond | "Formatting response..." |

### FR-5: Error Handling

The system must handle errors appropriately:

1. **FR-5.1:** `CLIPipeLLMClient` raises `RuntimeError` on CLI tool failure
2. **FR-5.2:** Orchestrator's existing retry logic handles transient failures
3. **FR-5.3:** Command shows helpful error if tool not found in PATH
4. **FR-5.4:** Command shows helpful error on budget exceeded
5. **FR-5.5:** Non-fatal errors in phase callback are logged, not propagated

### FR-6: Configuration Support

The system must support configuration:

1. **FR-6.1:** `--tool` CLI flag takes precedence over all other config
2. **FR-6.2:** `AURORA_SOAR_TOOL` environment variable is fallback
3. **FR-6.3:** Default value is "claude" if neither is set
4. **FR-6.4:** Any tool name is accepted if it exists in PATH (extensible)

### FR-7: JSON File Placeholders for LLM Communication

The system must use transitory JSON files to pass data between orchestrator and LLM, preserving formatting that terminals may lose:

1. **FR-7.1:** Create `.aurora/soar/` directory structure:
   ```
   .aurora/soar/
   ├── input.json     # Orchestrator writes before LLM call
   ├── output.json    # Captured from LLM stdout, parsed
   └── state.json     # Current phase state (for debugging/resume)
   ```
2. **FR-7.2:** Use `aurora_core.paths.get_aurora_dir()` to resolve project-local `.aurora/`
3. **FR-7.3:** `CLIPipeLLMClient.generate()` writes `input.json` before each LLM call
4. **FR-7.4:** `CLIPipeLLMClient.generate()` writes `output.json` after receiving LLM response
5. **FR-7.5:** `state.json` tracks current phase for debugging visibility
6. **FR-7.6:** Files are overwritten on each new `aur soar` run
7. **FR-7.7:** Successful completions are logged to `.aurora/logs/` (existing ConversationLogger)

---

## 5. Non-Goals (Out of Scope)

1. **Progress spinners/bars** - Keep terminal UX minimal for now; can add later
2. **Token/budget display during execution** - Not needed for MVP
3. **Config file support for tool selection** - Environment variable is sufficient
4. **Parallel phase execution** - Keep sequential execution model
5. **Changes to SOAROrchestrator core logic** - Only add phase_callback parameter
6. **New CLI tools beyond existing pattern** - Just ensure extensible design
7. **E2E tests with real CLI tools** - Unit/integration tests with mocks are sufficient
8. **Changes to orchestrator's retry counts or timeouts** - Use existing defaults

---

## 6. Design Considerations

### 6.1 File Locations

| File | Type | Purpose |
|------|------|---------|
| `packages/cli/src/aurora_cli/llm/cli_pipe_client.py` | NEW | CLIPipeLLMClient implementation |
| `packages/cli/src/aurora_cli/llm/__init__.py` | NEW | Package init with exports |
| `packages/soar/src/aurora_soar/orchestrator.py` | MODIFY | Add phase_callback parameter |
| `packages/cli/src/aurora_cli/commands/soar.py` | REWRITE | Thin wrapper implementation |

### 6.2 Class Diagram

```
                    +---------------+
                    |   LLMClient   |  (abstract base)
                    +---------------+
                           ^
                           |
         +-----------------+------------------+
         |                 |                  |
+----------------+  +---------------+  +------------------+
| AnthropicClient|  | OpenAIClient  |  | CLIPipeLLMClient |
+----------------+  +---------------+  +------------------+
                                              |
                                              | pipes to
                                              v
                                       +-------------+
                                       | claude -p   |
                                       | cursor -p   |
                                       | <tool> -p   |
                                       +-------------+
```

### 6.3 Subprocess Command Pattern

```python
# CLIPipeLLMClient.generate() implementation pattern
result = subprocess.run(
    [self.tool, "-p"],
    input=prompt,
    capture_output=True,
    text=True,
    timeout=180,
)
```

### 6.4 Phase Callback Usage Pattern

```python
# In SOAROrchestrator._phase1_assess()
if self.phase_callback:
    try:
        self.phase_callback("assess", "before", {})
    except Exception as e:
        logger.warning(f"Phase callback failed: {e}")

result = assess.assess_complexity(query, llm_client=self.reasoning_llm)

if self.phase_callback:
    try:
        self.phase_callback("assess", "after", {"complexity": result["complexity"]})
    except Exception as e:
        logger.warning(f"Phase callback failed: {e}")
```

---

## 7. Technical Considerations

### 7.1 Dependencies

- `SOAROrchestrator` requires: `store`, `agent_registry`, `config`, `reasoning_llm`, `solving_llm`
- These must be instantiated or mocked in `aur soar` command
- Use lazy initialization pattern from existing CLI commands

### 7.2 Existing Code to Reuse

| Component | Location | Purpose |
|-----------|----------|---------|
| `extract_json_from_text()` | `aurora_reasoning.llm_client` | JSON parsing from LLM responses |
| `LLMResponse` | `aurora_reasoning.llm_client` | Response data class |
| `LLMClient` | `aurora_reasoning.llm_client` | Abstract base class |
| `ComplexityAssessor` | `aurora_soar.phases.assess` | Phase 1 implementation |
| `ConversationLogger` | `aurora_core.logging` | Log storage |
| `get_aurora_dir()` | `aurora_core.paths` | Directory helpers |

### 7.3 Integration Points

- `SOAROrchestrator` uses `Store` for memory operations
- `AgentRegistry` provides available agents for routing
- `Config` provides budget limits and settings
- `CostTracker` tracks API costs (may need adjustment for CLI tool "costs")

### 7.4 Test Strategy - TDD Approach

**CRITICAL: Tests must be written FIRST, before implementation.**

#### TDD Workflow
1. Write failing test
2. Run test, confirm it fails
3. Write minimal implementation to pass
4. Run test, confirm it passes
5. Refactor if needed
6. Repeat

#### Test File Location
`tests/unit/cli/commands/test_soar.py`

#### Test Cases (Write First)

| # | Test Name | What It Verifies |
|---|-----------|------------------|
| 1 | `test_soar_creates_placeholder_dir` | `.aurora/soar/` created on run |
| 2 | `test_soar_tool_parameter` | `--tool` accepts claude/cursor/etc |
| 3 | `test_soar_tool_validation` | Fails if tool not found in PATH |
| 4 | `test_pipe_to_llm_writes_input_json` | `input.json` written before call |
| 5 | `test_pipe_to_llm_parses_output_json` | Extracts JSON from LLM response |
| 6 | `test_phase_display_orchestrator` | Shows `[ORCHESTRATOR]` for Python phases |
| 7 | `test_phase_display_llm` | Shows `[LLM → tool]` for LLM phases |
| 8 | `test_complexity_shown` | Complexity displayed after Phase 1 |
| 9 | `test_chunks_shown` | Matched chunks shown after Phase 2 |
| 10 | `test_extract_json_from_markdown` | Parses ```json blocks |
| 11 | `test_extract_json_plain` | Parses raw JSON response |
| 12 | `test_env_var_fallback` | `AURORA_SOAR_TOOL` respected |
| 13 | `test_cli_flag_overrides_env` | `--tool` beats env var |
| 14 | `test_state_json_updated` | `state.json` tracks current phase |
| 15 | `test_output_json_written` | `output.json` saved after LLM call |

#### Mocking Strategy
```python
# Mock subprocess.run for LLM calls
@patch("subprocess.run")
def test_pipe_to_llm_writes_input_json(mock_run, tmp_path):
    mock_run.return_value = Mock(returncode=0, stdout='{"result": "ok"}')
    # ... test logic

# Mock shutil.which for tool validation
@patch("shutil.which")
def test_soar_tool_validation(mock_which):
    mock_which.return_value = None  # Tool not found
    # ... expect error

# Use tmp_path fixture for .aurora/soar/ files
def test_soar_creates_placeholder_dir(tmp_path):
    # ... verify directory creation
```

#### Unit Tests (`tests/unit/cli/commands/test_soar.py`)
- `CLIPipeLLMClient.generate()` with mocked subprocess
- `CLIPipeLLMClient.generate_json()` JSON extraction
- `CLIPipeLLMClient.count_tokens()` heuristic
- Phase callback invocation logic
- Environment variable fallback
- JSON file placeholder creation

#### Integration Tests (`tests/integration/cli/test_soar_integration.py`)
- Full command execution with mocked CLI tool
- Error handling when tool not found
- Phase callback display output
- Orchestrator integration with CLI client

### 7.5 Backward Compatibility

| Aspect | Current | After Change | Compatible? |
|--------|---------|--------------|-------------|
| `aur soar "query"` | Works | Works | Yes |
| `--tool claude` | Works | Works | Yes |
| `--tool cursor` | Works | Works | Yes |
| `--model sonnet` | Works | Works | Yes |
| `--verbose` | Works | Works | Yes |
| Phase display | Custom | Via callback | Similar |
| Retry on failure | None | Orchestrator retry | Enhanced |
| Budget tracking | None | Orchestrator tracking | Enhanced |

---

## 8. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Code reduction | soar.py < 100 lines | Line count after rewrite |
| Test coverage | > 80% for new code | pytest-cov report |
| Feature parity | All existing tests pass | Test suite green |
| Retry logic working | Transient failures recovered | Integration test |
| Budget tracking | Costs recorded | Unit test verification |
| Backward compatibility | No CLI interface changes | Manual verification |
| Extensibility | New tool works without code changes | Manual test with arbitrary tool |

---

## 9. Open Questions

1. **Cost Tracking for CLI Tools:** The `CLIPipeLLMClient` doesn't have actual token/cost information since CLI tools don't expose this. Should we:
   - A) Use heuristic estimation (current plan: `len(text) // 4`)
   - B) Skip cost tracking for CLI mode entirely
   - C) Add placeholder costs for budget soft limits

   **Recommendation:** A - Use heuristic, matches existing client implementations.

2. **Orchestrator Dependencies:** The `SOAROrchestrator` requires `store`, `agent_registry`, and `config`. How should `aur soar` obtain these?
   - A) Use existing lazy initialization from CLI infrastructure
   - B) Create lightweight mocks/stubs for CLI mode
   - C) Make dependencies optional in orchestrator

   **Recommendation:** A - Reuse existing patterns from other CLI commands.

3. **Simple Query Path:** `SOAROrchestrator` has a `_execute_simple_path()` for SIMPLE queries. Should this also use the CLI tool?
   - A) Yes, all LLM calls go through CLIPipeLLMClient
   - B) No, let simple path use default API client

   **Recommendation:** A - Consistency; all LLM calls use CLI tool when specified.

---

## 10. Implementation Phases (TDD)

**All phases follow TDD: Write tests FIRST, then implement.**

### Phase 1: Write All Tests First (Est: 2-3 hours)
1. Create `tests/unit/cli/commands/test_soar.py` with all 15 test cases
2. Create `tests/unit/cli/llm/test_cli_pipe_client.py` for client tests
3. Run tests - ALL should fail (red)
4. Commit test files

### Phase 2: CLIPipeLLMClient Implementation (Est: 2-3 hours)
1. Create `packages/cli/src/aurora_cli/llm/__init__.py`
2. Create `packages/cli/src/aurora_cli/llm/cli_pipe_client.py`
3. Implement `generate()` - run tests 4, 5, 10, 11, 15
4. Implement `generate_json()` - run tests 10, 11
5. Implement `count_tokens()`, `default_model`
6. Implement JSON file placeholders (input.json, output.json, state.json)
7. Run tests - client tests should pass (green)

### Phase 3: Phase Callback in Orchestrator (Est: 1-2 hours)
1. Add `phase_callback` parameter to `SOAROrchestrator.__init__()`
2. Add callback invocations before/after each phase
3. Run tests 6, 7, 8, 9 - should pass

### Phase 4: Rewrite soar.py (Est: 2-3 hours)
1. Replace 500-line implementation with thin wrapper
2. Implement terminal display callback matching FR-4.5 format
3. Add environment variable support
4. Run tests 1, 2, 3, 12, 13, 14 - should pass
5. Run ALL tests - should be green

### Phase 5: Integration Testing & Cleanup (Est: 1-2 hours)
1. Run full integration test suite
2. Test backward compatibility manually
3. Verify terminal UX matches specification
4. Final refactor if needed

**Total Estimated Effort:** 8-12 hours

---

## Appendix A: Current vs. Proposed Architecture

### Current Architecture (Duplicated)
```
aur soar command
    |
    +-- Phase 1: Inline assess (Python)
    +-- Phase 2: Inline retrieve (subprocess aur query)
    +-- Phase 3: Inline decompose (_pipe_to_llm)
    +-- Phase 4: Inline verify (_pipe_to_llm)
    +-- Phase 5: Inline route (Python)
    +-- Phase 6: Inline collect (_pipe_to_llm)
    +-- Phase 7: Inline synthesize (_pipe_to_llm)
    +-- Phase 8: Inline record (Python)
    +-- Phase 9: Inline respond (_pipe_to_llm)
    |
    +-- Logging (ConversationLogger)
    +-- Metrics (QueryMetrics)
```

### Proposed Architecture (Unified)
```
aur soar command (~80 lines)
    |
    +-- Create CLIPipeLLMClient(tool)
    +-- Create SOAROrchestrator(llm=cli_client, callback=display_fn)
    +-- orchestrator.execute(query)
    |
    +-- [Display handled by callback]

SOAROrchestrator (unchanged except callback)
    |
    +-- Phase 1-9 (real implementations)
    +-- Retry logic
    +-- Budget tracking
    +-- Error handling
    +-- Logging

CLIPipeLLMClient
    |
    +-- subprocess.run([tool, "-p"], input=prompt)
    +-- Return LLMResponse
```

---

## Appendix B: Test File Updates

### Files to Update
- `tests/unit/cli/commands/test_soar.py` - Update for new architecture
- `tests/integration/mcp/test_mcp_soar_multi_turn.py` - May need updates

### New Test Files
- `tests/unit/cli/llm/test_cli_pipe_client.py` - Unit tests for CLIPipeLLMClient

### Test Categories

**CLIPipeLLMClient Unit Tests:**
- `test_generate_pipes_to_tool` - Verifies subprocess call
- `test_generate_handles_timeout` - 180s timeout
- `test_generate_raises_on_failure` - Non-zero exit code
- `test_generate_json_extracts_json` - JSON parsing
- `test_generate_json_handles_markdown` - ```json blocks
- `test_count_tokens_heuristic` - len//4 calculation
- `test_default_model_returns_tool_name` - Property value
- `test_constructor_validates_tool_exists` - PATH check

**JSON File Placeholder Tests:**
- `test_soar_creates_placeholder_dir` - `.aurora/soar/` created
- `test_pipe_to_llm_writes_input_json` - `input.json` written before LLM call
- `test_pipe_to_llm_parses_output_json` - `output.json` written after LLM call
- `test_state_json_updated` - `state.json` tracks current phase
- `test_files_overwritten_each_run` - Clean slate per run

**Phase Callback Unit Tests:**
- `test_callback_invoked_before_phase` - "before" status
- `test_callback_invoked_after_phase` - "after" status with result
- `test_callback_exception_logged_not_raised` - Non-blocking
- `test_no_callback_works` - Optional parameter

**Terminal UX Tests:**
- `test_phase_display_orchestrator` - Shows `[ORCHESTRATOR]` for Python phases
- `test_phase_display_llm` - Shows `[LLM → tool]` for LLM phases
- `test_complexity_shown` - Complexity displayed after Phase 1
- `test_chunks_shown` - Matched chunks shown after Phase 2
- `test_header_box_format` - `╭─────────── Aurora SOAR ───────────╮` format
- `test_final_answer_box_format` - Final answer box format

**Command Integration Tests:**
- `test_soar_uses_orchestrator` - Delegation verified
- `test_soar_respects_env_var` - AURORA_SOAR_TOOL
- `test_soar_flag_overrides_env` - --tool precedence
- `test_soar_displays_phases` - Terminal output
