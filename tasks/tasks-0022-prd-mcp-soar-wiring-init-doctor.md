# Task List: PRD-0022 MCP-SOAR Wiring and Init/Doctor Enhancements

Generated from: `/home/hamr/PycharmProjects/aurora/tasks/0022-prd-mcp-soar-wiring-init-doctor.md`

## Relevant Files

### MCP Tools
- `/home/hamr/PycharmProjects/aurora/src/aurora_mcp/tools.py` - MCP tool implementations; refactor `aurora_query` to support phase parameter, remove 6 redundant tools
- `/home/hamr/PycharmProjects/aurora/src/aurora_mcp/server.py` - FastMCP server registration; update to register only 3 tools
- `/home/hamr/PycharmProjects/aurora/src/aurora_mcp/config.py` - MCP configuration and logging utilities

### SOAR Pipeline
- `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/phases/assess.py` - Complexity assessment; exports `assess_complexity()` for assess phase
- `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/phases/retrieve.py` - Context retrieval; exports `retrieve_context()` for retrieve phase
- `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/phases/decompose.py` - Query decomposition; returns prompt templates for Claude reasoning
- `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/phases/verify.py` - Verification logic; validates Claude's decomposition results
- `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/phases/route.py` - Agent routing; maps subgoals to available agents
- `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/phases/collect.py` - Agent execution; orchestrates agent task execution
- `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/phases/synthesize.py` - Result synthesis; returns prompt templates for combining results
- `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/phases/record.py` - Pattern caching; records patterns in ACT-R memory
- `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/phases/respond.py` - Response formatting; formats final answer with metadata

### CLI Commands and Health Checks
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/init.py` - Main init command; orchestrates project initialization workflow
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/init_helpers.py` - Init helper functions; contains `configure_mcp_servers()` needing validation enhancement
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/health_checks.py` - Health check system; add new `MCPFunctionalChecks` class for doctor command
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/doctor.py` - Doctor command implementation; integrates MCPFunctionalChecks

### MCP Configurators
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/mcp/base.py` - Base configurator class; defines ConfigResult and MCPConfigurator interface
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/mcp/claude.py` - Claude Code MCP configurator
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/mcp/continue_.py` - Continue.dev MCP configurator
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/mcp/registry.py` - MCP configurator registry

### Test Files (TDD - Create These First)
- `/home/hamr/PycharmProjects/aurora/tests/unit/mcp/test_aurora_query_phases.py` - Unit tests for aurora_query phase parameter and multi-turn flow
- `/home/hamr/PycharmProjects/aurora/tests/unit/mcp/test_phase_handlers.py` - Unit tests for all 9 phase handler functions
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/test_init_validation.py` - Unit tests for aur init MCP validation
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/test_mcp_functional_checks.py` - Unit tests for MCPFunctionalChecks class
- `/home/hamr/PycharmProjects/aurora/tests/integration/test_mcp_soar_multi_turn.py` - Integration tests for complete multi-turn SOAR flow
- `/home/hamr/PycharmProjects/aurora/tests/integration/test_doctor_mcp_checks.py` - Integration tests for aur doctor MCP health checks

### Documentation
- `/home/hamr/PycharmProjects/aurora/COMMANDS.md` - User-facing command documentation; update for simplified MCP tools and multi-turn architecture

### Notes

**Testing Framework:**
- Use pytest for all tests
- Use unittest.mock for mocking phase modules and LLM clients
- Test structure follows existing patterns in `/home/hamr/PycharmProjects/aurora/tests/unit/mcp/test_aurora_query_simplified.py`
- Mark tests with `@pytest.mark.critical` and `@pytest.mark.mcp` for categorization

**TDD Workflow (CRITICAL):**
1. Write failing test FIRST (RED phase)
2. Implement minimal code to pass test (GREEN phase)
3. Refactor for quality (REFACTOR phase)
4. Never skip to implementation without tests

**Multi-Turn Architecture:**
- MCP tools provide structure and data only
- Claude (host LLM) performs all reasoning
- No external LLM API calls from MCP tools
- Each phase returns JSON with `next_action` guidance for Claude

**Validation Strategy:**
- Init validation uses soft failures (warnings, not errors)
- Doctor validation provides auto-fix suggestions where possible
- Both validate against the 3 essential tools: `aurora_query`, `aurora_search`, `aurora_get`

**Phase Response Schema:**
```json
{
  "phase": "phase_name",
  "progress": "N/9 phase_name",
  "status": "complete" | "error",
  "result": { /* phase-specific data */ },
  "next_action": "Human-readable guidance for Claude",
  "prompt_template": "Optional: template for Claude's reasoning",
  "metadata": { "duration_ms": 45 }
}
```

## Tasks

- [x] 1.0 Remove 6 Redundant MCP Tools and Update Server Configuration
  - [x] 1.1 Write unit tests for 3-tool validation (TDD RED phase)
  - [x] 1.2 Remove `aurora_index` method from `AuroraMCPTools` class in `/home/hamr/PycharmProjects/aurora/src/aurora_mcp/tools.py`
  - [x] 1.3 Remove `aurora_context` method from `AuroraMCPTools` class in `/home/hamr/PycharmProjects/aurora/src/aurora_mcp/tools.py`
  - [x] 1.4 Remove `aurora_related` method from `AuroraMCPTools` class in `/home/hamr/PycharmProjects/aurora/src/aurora_mcp/tools.py`
  - [x] 1.5 Remove `aurora_list_agents` method from `AuroraMCPTools` class in `/home/hamr/PycharmProjects/aurora/src/aurora_mcp/tools.py`
  - [x] 1.6 Remove `aurora_search_agents` method from `AuroraMCPTools` class in `/home/hamr/PycharmProjects/aurora/src/aurora_mcp/tools.py`
  - [x] 1.7 Remove `aurora_show_agent` method from `AuroraMCPTools` class in `/home/hamr/PycharmProjects/aurora/src/aurora_mcp/tools.py`
  - [x] 1.8 Update `/home/hamr/PycharmProjects/aurora/src/aurora_mcp/server.py` to remove tool registrations for the 6 deleted methods
  - [x] 1.9 Verify only 3 tools remain registered: `aurora_search`, `aurora_query`, `aurora_get`
  - [x] 1.10 Run unit tests to confirm 3-tool configuration (TDD GREEN phase)

- [ ] 2.0 Refactor aurora_query to Support Multi-Turn SOAR Phase Orchestration
  - [ ] 2.1 Write unit tests for phase parameter validation (TDD RED phase) - create `/home/hamr/PycharmProjects/aurora/tests/unit/mcp/test_aurora_query_phases.py` testing invalid phase names, missing phase parameter defaults to "assess"
  - [ ] 2.2 Write unit tests for phase response schema validation (TDD RED phase) - verify each response has phase, progress, status, result, next_action, metadata fields
  - [ ] 2.3 Add `phase` parameter to `aurora_query` method signature in `/home/hamr/PycharmProjects/aurora/src/aurora_mcp/tools.py` with default value "assess" and type annotation `Literal["assess", "retrieve", "decompose", "verify", "route", "collect", "synthesize", "record", "respond"]`
  - [ ] 2.4 Add phase validation logic at the start of `aurora_query` method to check phase is in allowed list, return error JSON if invalid
  - [ ] 2.5 Create `_handle_phase()` dispatcher method in `AuroraMCPTools` class that routes to appropriate phase handler based on phase parameter
  - [ ] 2.6 Refactor existing `aurora_query` logic to become `_handle_assess_phase()` private method
  - [ ] 2.7 Update `aurora_query` method to call `_handle_phase()` dispatcher instead of executing retrieval directly
  - [ ] 2.8 Ensure all phase handlers return JSON with required fields: phase, progress, status, result, next_action, metadata
  - [ ] 2.9 Run unit tests to verify phase parameter handling (TDD GREEN phase)
  - [ ] 2.10 Refactor for code quality and consistency (TDD REFACTOR phase)

- [ ] 3.0 Implement Phase Handler Functions for All 9 SOAR Phases
  - [ ] 3.1 Write unit tests for assess phase handler (TDD RED phase) - create `/home/hamr/PycharmProjects/aurora/tests/unit/mcp/test_phase_handlers.py` with tests for SIMPLE/MEDIUM/COMPLEX/CRITICAL classification, early_exit flag for SIMPLE queries
  - [ ] 3.2 Implement `_handle_assess_phase()` in `AuroraMCPTools` - import `assess_complexity` from `aurora_soar.phases.assess`, call it with query parameter, return JSON with complexity level and next_action ("retrieve_and_respond" for SIMPLE, "Call aurora_query with phase='retrieve'" for others)
  - [ ] 3.3 Write unit tests for retrieve phase handler (TDD RED phase) - verify HybridRetriever usage, chunk retrieval, session cache update
  - [ ] 3.4 Implement `_handle_retrieve_phase()` in `AuroraMCPTools` - use existing `_retrieve_chunks()` method, return chunks in result field, set next_action based on complexity ("respond" for SIMPLE, "Call aurora_query with phase='decompose'" for others)
  - [ ] 3.5 Write unit tests for decompose phase handler (TDD RED phase) - verify prompt template generation, context parameter handling, no LLM calls
  - [ ] 3.6 Implement `_handle_decompose_phase()` in `AuroraMCPTools` - accept context parameter, generate decomposition prompt template using patterns from `aurora_soar.phases.decompose`, return prompt_template and context in result, set next_action to "Reason about subgoals, then call aurora_query with phase='verify' and your decomposition"
  - [ ] 3.7 Write unit tests for verify phase handler (TDD RED phase) - verify subgoals parameter required, quality threshold validation, PASS/FAIL verdict
  - [ ] 3.8 Implement `_handle_verify_phase()` in `AuroraMCPTools` - accept subgoals parameter from Claude's reasoning, validate against quality thresholds from `aurora_soar.phases.verify`, return verdict (PASS/FAIL) and next_action ("Call aurora_query with phase='route'" if PASS, "Revise decomposition and retry verify" if FAIL)
  - [ ] 3.9 Write unit tests for route phase handler (TDD RED phase) - verify agent mapping, subgoals parameter handling
  - [ ] 3.10 Implement `_handle_route_phase()` in `AuroraMCPTools` - accept subgoals parameter, use logic from `aurora_soar.phases.route` to map subgoals to available agents, return routing plan in result, set next_action to "Call aurora_query with phase='collect'"
  - [ ] 3.11 Write unit tests for collect phase handler (TDD RED phase) - verify agent task creation, prompt template generation, no actual agent execution
  - [ ] 3.12 Implement `_handle_collect_phase()` in `AuroraMCPTools` - accept routing parameter, generate agent task prompts using patterns from `aurora_soar.phases.collect`, return task prompts for Claude to execute (not execute agents directly), set next_action to "Execute agent tasks, then call aurora_query with phase='synthesize' with results"
  - [ ] 3.13 Write unit tests for synthesize phase handler (TDD RED phase) - verify prompt template generation, agent results parameter handling
  - [ ] 3.14 Implement `_handle_synthesize_phase()` in `AuroraMCPTools` - accept agent_results parameter from Claude, generate synthesis prompt template using patterns from `aurora_soar.phases.synthesize`, return prompt_template in result, set next_action to "Combine agent results into final answer, then call aurora_query with phase='record' with synthesis"
  - [ ] 3.15 Write unit tests for record phase handler (TDD RED phase) - verify pattern caching in ACT-R memory, synthesis parameter handling
  - [ ] 3.16 Implement `_handle_record_phase()` in `AuroraMCPTools` - accept synthesis parameter, use `aurora_soar.phases.record` to cache pattern in memory database, return cache confirmation in result, set next_action to "Call aurora_query with phase='respond'"
  - [ ] 3.17 Write unit tests for respond phase handler (TDD RED phase) - verify response formatting, metadata inclusion
  - [ ] 3.18 Implement `_handle_respond_phase()` in `AuroraMCPTools` - accept final_answer parameter, format response using `aurora_soar.phases.respond`, include all metadata (complexity, timing, agent usage), return formatted response in result, set next_action to "Present final answer to user"
  - [ ] 3.19 Run all phase handler unit tests to verify implementation (TDD GREEN phase)
  - [ ] 3.20 Refactor phase handlers for code reuse and consistency (TDD REFACTOR phase)

- [ ] 4.0 Add MCP Configuration Validation to aur init Command
  - [ ] 4.1 Write unit tests for MCP validation in init (TDD RED phase) - create `/home/hamr/PycharmProjects/aurora/tests/unit/cli/test_init_validation.py` with tests for JSON syntax validation, server path existence check, soft failure behavior (warnings not errors)
  - [ ] 4.2 Create `_validate_mcp_config()` helper function in `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/init_helpers.py` that checks JSON syntax by parsing config file with `json.load()`
  - [ ] 4.3 Add server path validation to `_validate_mcp_config()` to verify Aurora MCP server executable exists at configured path
  - [ ] 4.4 Add required tools validation to `_validate_mcp_config()` to check for exactly 3 tools: `aurora_query`, `aurora_search`, `aurora_get`
  - [ ] 4.5 Update `_validate_mcp_config()` to return validation result tuple: (success: bool, warnings: list[str])
  - [ ] 4.6 Modify `configure_mcp_servers()` function in `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/init_helpers.py` to call `_validate_mcp_config()` after configuration
  - [ ] 4.7 Update `configure_mcp_servers()` return type to include validation_warnings: tuple[list[str], list[str], list[str], list[str]] (created, updated, skipped, validation_warnings)
  - [ ] 4.8 Update callers of `configure_mcp_servers()` in `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/init.py` to display validation warnings with suggestion to run `aur doctor`
  - [ ] 4.9 Ensure validation failures do NOT prevent init completion (soft failure with warnings only)
  - [ ] 4.10 Run unit tests to verify validation behavior (TDD GREEN phase)
  - [ ] 4.11 Add integration test for full init flow with validation warnings

- [ ] 5.0 Implement MCPFunctionalChecks for aur doctor Command
  - [ ] 5.1 Write unit tests for MCPFunctionalChecks class (TDD RED phase) - create `/home/hamr/PycharmProjects/aurora/tests/unit/cli/test_mcp_functional_checks.py` with tests for all 6 check methods, pass/warning/fail scenarios
  - [ ] 5.2 Create `MCPFunctionalChecks` class in `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/health_checks.py` following same pattern as `CoreSystemChecks` and `ToolIntegrationChecks`
  - [ ] 5.3 Implement `__init__()` method in `MCPFunctionalChecks` to accept optional Config parameter and initialize project path
  - [ ] 5.4 Implement `run_checks()` method to execute all 6 functional checks and return list of HealthCheckResult tuples
  - [ ] 5.5 Implement `_check_mcp_config_syntax()` method to validate MCP config JSON by parsing with `json.load()`, catch JSONDecodeError, return (status, message, details) tuple
  - [ ] 5.6 Implement `_check_aurora_mcp_tools_importable()` method to import `aurora_mcp.tools.AuroraMCPTools` and verify 3 required methods exist (`aurora_query`, `aurora_search`, `aurora_get`), return pass/fail with method list in details
  - [ ] 5.7 Implement `_check_soar_phases_importable()` method to import all 9 phase modules from `aurora_soar.phases` (assess, retrieve, decompose, verify, route, collect, synthesize, record, respond), return pass/fail with importable phase list in details
  - [ ] 5.8 Implement `_check_memory_database_accessible()` method to open connection to `.aurora/memory.db` using SQLiteStore, verify database is readable, close connection, return pass/fail with database path in details
  - [ ] 5.9 Implement `_check_slash_command_mcp_consistency()` method to verify slash command configs reference valid MCP servers by cross-checking configurator registries, return warning/pass with inconsistencies in details
  - [ ] 5.10 Implement `_check_mcp_server_tools_complete()` method to verify Aurora MCP server has exactly 3 tools registered, return pass/fail with tool count and missing tools in details
  - [ ] 5.11 Implement `get_fixable_issues()` method to return list of auto-fixable problems (e.g., create missing .aurora directory, initialize missing memory.db)
  - [ ] 5.12 Implement `get_manual_issues()` method to return list of manual intervention issues with clear solution steps (e.g., "Run 'aur init --config' to configure MCP server")
  - [ ] 5.13 Update `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/doctor.py` to instantiate and run `MCPFunctionalChecks` in health check flow
  - [ ] 5.14 Add `--fix` support in doctor command to apply auto-fixes from `MCPFunctionalChecks.get_fixable_issues()`
  - [ ] 5.15 Run unit tests to verify all check methods (TDD GREEN phase)
  - [ ] 5.16 Write integration tests for doctor command with MCPFunctionalChecks - create `/home/hamr/PycharmProjects/aurora/tests/integration/test_doctor_mcp_checks.py` with tests for full doctor flow including --fix flag

- [ ] 6.0 Add Integration Tests for MCP-SOAR Multi-Turn Flow
  - [ ] 6.1 Create integration test file `/home/hamr/PycharmProjects/aurora/tests/integration/test_mcp_soar_multi_turn.py` with pytest fixtures for mock store, mock activation engine, mock embedding provider
  - [ ] 6.2 Write test for SIMPLE query early exit flow - call aurora_query with assess phase, verify complexity=SIMPLE and early_exit=true, call retrieve phase, verify response, confirm no decompose phase needed
  - [ ] 6.3 Write test for MEDIUM query full pipeline - call all 9 phases in sequence with mock Claude reasoning between phases, verify each phase returns correct next_action, verify final response includes all metadata
  - [ ] 6.4 Write test for COMPLEX query with decomposition - mock Claude providing subgoals after decompose phase, verify verify phase validates subgoals, continue through all phases
  - [ ] 6.5 Write test for phase validation errors - call aurora_query with invalid phase name, verify error JSON returned with clear message
  - [ ] 6.6 Write test for missing required parameters - call verify phase without subgoals parameter, verify error JSON returned
  - [ ] 6.7 Write test for verify phase rejection flow - provide invalid subgoals, verify FAIL verdict returned, verify next_action suggests revision
  - [ ] 6.8 Write test for end-to-end timing metadata - execute full COMPLEX query flow, verify each phase includes duration_ms in metadata, verify total timing tracked
  - [ ] 6.9 Mock all SOAR phase function calls to avoid LLM dependencies - use unittest.mock to patch imports from aurora_soar.phases modules
  - [ ] 6.10 Verify no external LLM API calls are made during any phase - assert no network requests, no API key usage
  - [ ] 6.11 Run all integration tests to verify multi-turn architecture (TDD GREEN phase)

- [ ] 7.0 Update Documentation for Simplified MCP Tools and Multi-Turn Architecture
  - [ ] 7.1 Update `/home/hamr/PycharmProjects/aurora/COMMANDS.md` to document only 3 MCP tools (remove documentation for 6 deleted tools)
  - [ ] 7.2 Add "Simplified MCP Tools" section to COMMANDS.md explaining the 3 essential tools: `aurora_query` (SOAR-wired multi-turn), `aurora_search` (search chunks), `aurora_get` (retrieve full chunk)
  - [ ] 7.3 Add "Multi-Turn SOAR Pipeline" section to COMMANDS.md with detailed explanation of phase parameter usage, showing example multi-turn conversation flow from PRD lines 237-260
  - [ ] 7.4 Document each of the 9 phases in COMMANDS.md with parameters, return values, and next_action guidance
  - [ ] 7.5 Add "CLI Alternatives for Removed Tools" section to COMMANDS.md mapping old tools to new approaches: `aurora_index` → `aur mem index`, `aurora_context` → Claude's Read tool, `aurora_related` → `aur mem related`, `aurora_list_agents` → `aur agents list`, `aurora_search_agents` → `aur agents search`, `aurora_show_agent` → Claude's Read tool
  - [ ] 7.6 Document SIMPLE query early exit behavior in COMMANDS.md with example showing assess phase returning early_exit flag
  - [ ] 7.7 Document phase response schema in COMMANDS.md showing JSON structure with all required fields (phase, progress, status, result, next_action, metadata)
  - [ ] 7.8 Add "MCP Health Checks" section to COMMANDS.md documenting new `aur doctor` checks for MCP configuration, SOAR phases, and memory database
  - [ ] 7.9 Document `aur doctor --fix` auto-fix functionality for MCP-related issues
  - [ ] 7.10 Add examples showing how Claude orchestrates multi-turn phase calls for MEDIUM/COMPLEX/CRITICAL queries
  - [ ] 7.11 Review documentation for accuracy and clarity, ensure all 37 functional requirements are represented
