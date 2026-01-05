# PRD-0022: Wire Aurora MCP Tools to SOAR Pipeline and Simplify MCP Surface

## Introduction/Overview

Aurora's MCP (Model Context Protocol) tools are currently disconnected from the SOAR (Sense-Orient-Adapt-Respond) pipeline. The `aurora_query` MCP tool performs basic retrieval and returns structured context, but it does not route queries through the 9-phase SOAR orchestration pipeline that was built for intelligent query processing.

Additionally, the MCP server exposes 9 tools when only 3 are essential for Claude Code integration. The remaining 6 tools duplicate CLI functionality or can be replaced by Claude's native tools.

This PRD addresses four interconnected problems:
1. **MCP-SOAR Disconnection**: `aurora_query` bypasses SOAR orchestration, losing complexity-based routing, decomposition, verification, and pattern caching
2. **MCP Bloat**: 9 tools exposed when only 3 are needed (query, search, get)
3. **Init Verification Gap**: No post-configuration validation in `aur init` for MCP server setup
4. **Doctor Missing Checks**: No functional testing of MCP tools or SOAR pipeline connectivity in `aur doctor`

## Key Architecture Decision: Multi-Turn Phase Orchestration

**Critical insight:** Claude Code IS the LLM. MCP tools cannot make external LLM API calls. Therefore:

- MCP tools provide **structure, data, and phase guidance**
- Claude (host LLM) provides **reasoning at each phase**
- The 9-phase pipeline executes as a **multi-turn conversation** where Claude calls each phase tool sequentially

This preserves the full SOAR pipeline intelligence while leveraging Claude as the reasoning engine.

## MCP Tool Simplification

### Keep (3 tools)
| Tool | Purpose |
|------|---------|
| `aurora_query` | SOAR-wired reasoning with multi-turn phases |
| `aurora_search` | Search code/reas/know chunks |
| `aurora_get` | Retrieve full chunk from search results |

### Remove (6 tools)
| Tool | Replacement |
|------|-------------|
| `aurora_index` | `aur mem index` CLI |
| `aurora_context` | Claude's `Read` tool |
| `aurora_related` | `aur mem related` CLI |
| `aurora_list_agents` | `aur agents list` CLI |
| `aurora_search_agents` | `aur agents search` CLI |
| `aurora_show_agent` | Claude's `Read` tool |

## Goals

- Wire `aurora_query` to execute multi-turn SOAR phases (not a new tool)
- Remove 6 redundant MCP tools, keep only 3 essential ones
- Each phase returns structured context + `next_action` guidance for Claude
- User sees real-time progress as Claude calls each phase
- SIMPLE queries early-exit after ASSESS phase
- MEDIUM/COMPLEX/CRITICAL queries execute all 9 phases with Claude reasoning
- Update `aur init` to configure only the 3 essential MCP tools
- Update `aur doctor` to verify only the 3 essential MCP tools
- Add post-configuration verification to `aur init` (soft failure with warning)
- Add functional health checks to `aur doctor` for MCP and SOAR connectivity
- Achieve test coverage via unit tests + integration tests with mocks (TDD approach)

## User Stories

### Story 1: Developer Using aurora_query for Complex Queries
**As a** developer using Aurora with Claude Code,
**I want** `aurora_query` to guide me through the full SOAR pipeline phase-by-phase,
**So that** I get intelligent decomposition, verification, and synthesis with Claude reasoning at each step.

**Acceptance Criteria:**
- User sees each phase being called in real-time (e.g., `aurora_query(phase: "assess")`)
- SIMPLE queries early-exit after ASSESS phase with direct context retrieval
- MEDIUM/COMPLEX/CRITICAL queries execute all 9 phases as multi-turn tool calls
- Each phase returns `next_action` guidance telling Claude what to do next
- Claude performs reasoning (decompose, verify, synthesize) using phase context
- No API key required - Claude Code IS the LLM

### Story 2: Developer Running aur init
**As a** developer setting up Aurora in a new project,
**I want** `aur init` to verify MCP configuration after setup,
**So that** I know immediately if something is misconfigured (without blocking setup completion).

**Acceptance Criteria:**
- After MCP configuration, `aur init` runs validation checks
- Validation includes: JSON syntax, required fields, server path existence
- Failures produce warnings (not errors) with clear messages
- Suggestion to run `aur doctor` for detailed diagnostics
- Init completes successfully even if validation warns

### Story 3: Developer Diagnosing MCP Issues
**As a** developer experiencing MCP tool failures,
**I want** `aur doctor` to perform functional tests on MCP tools,
**So that** I can identify exactly which component is broken and get fix suggestions.

**Acceptance Criteria:**
- Doctor checks MCP config JSON is syntactically valid
- Doctor checks Aurora MCP tools are registered (importable)
- Doctor checks SOAR phases are importable/accessible
- Doctor checks memory database is accessible
- Doctor checks slash command configs reference valid MCP servers
- Doctor offers auto-fix for fixable issues (matching `--fix` behavior)

### Story 4: Developer with Inconsistent Configurations
**As a** developer with both slash commands and MCP configured,
**I want** `aur doctor` to check configuration consistency,
**So that** I can ensure slash commands and MCP servers are aligned.

**Acceptance Criteria:**
- Doctor validates that MCP servers referenced in configs exist
- Doctor validates that expected Aurora tools are present in MCP server
- Inconsistencies reported with clear remediation steps

## Functional Requirements

### MCP-SOAR Integration (Multi-Turn Architecture)

1. **FR-1**: The existing `aurora_query` MCP tool MUST be refactored to accept a `phase` parameter with values: "assess", "retrieve", "decompose", "verify", "route", "collect", "synthesize", "record", "respond".

2. **FR-2**: Each phase invocation MUST return a JSON response containing:
   - `phase`: Current phase name
   - `status`: "complete" or "error"
   - `result`: Phase-specific output data
   - `next_action`: Guidance for Claude on what to do next
   - `progress`: Human-readable progress indicator (e.g., "2/9 retrieve")

3. **FR-3**: The "assess" phase MUST classify query complexity using `assess.assess_complexity()` and return the complexity level (SIMPLE/MEDIUM/COMPLEX/CRITICAL).

4. **FR-4**: For SIMPLE queries, the "assess" phase MUST set `next_action` to "retrieve_and_respond" enabling early exit.

5. **FR-5**: For MEDIUM/COMPLEX/CRITICAL queries, each phase MUST set `next_action` to the next phase name, guiding Claude through all 9 phases.

6. **FR-6**: The "decompose" phase MUST return a prompt template and context for Claude to perform the actual decomposition reasoning.

7. **FR-7**: The "verify" phase MUST accept Claude's decomposition result and validate it against quality thresholds.

8. **FR-8**: The "synthesize" phase MUST return a prompt template for Claude to combine agent results into a final answer.

9. **FR-9**: The `aurora_query` tool MUST NOT make external LLM API calls. Claude (host LLM) performs all reasoning.

### MCP Tool Simplification

10. **FR-10**: The following MCP tools MUST be removed from `tools.py` and `server.py`:
    - `aurora_index` (use `aur mem index` CLI)
    - `aurora_context` (use Claude's `Read` tool)
    - `aurora_related` (use `aur mem related` CLI)
    - `aurora_list_agents` (use `aur agents list` CLI)
    - `aurora_search_agents` (use `aur agents search` CLI)
    - `aurora_show_agent` (use Claude's `Read` tool)

11. **FR-11**: The following MCP tools MUST be retained:
    - `aurora_query` (SOAR-wired, multi-turn phases)
    - `aurora_search` (search code/reas/know chunks)
    - `aurora_get` (retrieve full chunk from search results)

12. **FR-12**: The `aurora_search` tool MUST continue using HybridRetriever for searching across code, reasoning, and knowledge chunks.

13. **FR-13**: The `aurora_get` tool MUST continue providing full chunk retrieval from search results.

### aur init Verification

14. **FR-14**: After MCP server configuration, `aur init` MUST validate that the MCP config file is syntactically valid JSON.

15. **FR-15**: After MCP server configuration, `aur init` MUST validate that the Aurora MCP server path exists and is executable.

16. **FR-16**: Validation failures in `aur init` MUST produce warning messages (not errors) and allow init to complete.

17. **FR-17**: Validation failure messages MUST suggest running `aur doctor` for detailed diagnostics.

18. **FR-18**: The `configure_mcp_servers()` function in `init_helpers.py` MUST return validation status in its result tuple.

### aur doctor Health Checks

19. **FR-19**: `aur doctor` MUST add a new `MCPFunctionalChecks` class that performs functional testing of MCP configuration.

20. **FR-20**: `MCPFunctionalChecks` MUST verify MCP config JSON is syntactically valid by parsing with `json.load()`.

21. **FR-21**: `MCPFunctionalChecks` MUST verify Aurora MCP tools are importable by importing `aurora_mcp.tools.AuroraMCPTools` and checking for the 3 required methods: `aurora_query`, `aurora_search`, `aurora_get`.

22. **FR-22**: `MCPFunctionalChecks` MUST verify SOAR phases are importable by importing each phase module from `aurora_soar.phases`.

23. **FR-23**: `MCPFunctionalChecks` MUST verify the memory database is accessible by opening a connection to the project's `.aurora/memory.db`.

24. **FR-24**: `MCPFunctionalChecks` MUST verify slash command configs reference valid MCP servers by cross-checking configuration files.

25. **FR-25**: `MCPFunctionalChecks` MUST provide `get_fixable_issues()` returning auto-fixable problems (e.g., create missing directories).

26. **FR-26**: `MCPFunctionalChecks` MUST provide `get_manual_issues()` returning issues requiring manual intervention with clear solution steps.

27. **FR-27**: The `aur doctor --fix` command MUST apply auto-fixes from `MCPFunctionalChecks.get_fixable_issues()`.

### Consistency Checks

28. **FR-28**: `MCPFunctionalChecks` MUST verify that MCP server configurations reference an existing Aurora MCP server entry.

29. **FR-29**: `MCPFunctionalChecks` MUST verify that the referenced MCP server has exactly the 3 expected Aurora tools: `aurora_query`, `aurora_search`, `aurora_get`.

### Test-Driven Development

30. **FR-30**: All implementation MUST follow TDD workflow: write failing test first, then implement code to pass, then refactor.

31. **FR-31**: Each MCP tool phase MUST have unit tests written BEFORE implementation, verifying:
    - Input validation
    - Expected JSON response structure
    - `next_action` guidance correctness
    - Error handling

32. **FR-32**: Each `aur doctor` health check MUST have unit tests written BEFORE implementation, covering pass/warning/fail scenarios.

33. **FR-33**: Integration tests MUST be written BEFORE wiring MCP tools to SOAR phases, using mocks for phase modules.

### Documentation Updates

34. **FR-34**: `COMMANDS.md` MUST be updated to document the simplified MCP tool set (3 tools instead of 9).

35. **FR-35**: `COMMANDS.md` MUST document `aurora_query` multi-turn phase flow with examples showing phase parameter usage.

36. **FR-36**: `COMMANDS.md` MUST document the CLI alternatives for removed MCP tools:
    - `aurora_index` → `aur mem index`
    - `aurora_context` → Claude's `Read` tool
    - `aurora_related` → `aur mem related`
    - `aurora_list_agents` → `aur agents list`
    - `aurora_search_agents` → `aur agents search`
    - `aurora_show_agent` → Claude's `Read` tool

37. **FR-37**: `COMMANDS.md` MUST document new `aur doctor` MCP health checks and their output format.

## Non-Goals (Out of Scope)

- Adding new MCP tools (we are simplifying from 9 to 3)
- Changing the SOAR pipeline implementation itself (it is already built)
- Restoring the `aur query` CLI command (not needed - MCP calls Python directly)
- Backwards compatibility with older Aurora installations (assume fresh installs only)
- Spawning MCP server processes for testing (use Python import approach instead)
- Keeping the 6 removed MCP tools for backwards compatibility (CLI alternatives exist)

## Design Considerations

### Multi-Turn Phase Flow

User invokes a query, Claude orchestrates the phases:

```
User: "How does authentication work in this codebase?"

● aurora - aurora_query (MCP)(phase: "assess", query: "How does...")
  ⎿ { "phase": "assess", "progress": "1/9", "result": { "complexity": "COMPLEX" },
      "next_action": "Call aurora_query with phase='retrieve'" }

● aurora - aurora_query (MCP)(phase: "retrieve", query: "How does...")
  ⎿ { "phase": "retrieve", "progress": "2/9", "result": { "chunks": [...] },
      "next_action": "Decompose query into subgoals using provided context" }

● aurora - aurora_query (MCP)(phase: "decompose", context: [...])
  ⎿ { "phase": "decompose", "progress": "3/9",
      "prompt_template": "Break this query into 2-5 subgoals...",
      "next_action": "Reason about subgoals, then call verify with your decomposition" }

[Claude reasons and creates subgoals]

● aurora - aurora_query (MCP)(phase: "verify", subgoals: [...])
  ⎿ { "phase": "verify", "progress": "4/9", "result": { "verdict": "PASS" },
      "next_action": "Call aurora_query with phase='route'" }

... continues through all 9 phases
```

### Phase Response Schema

Each phase returns this structure:

```json
{
  "phase": "decompose",
  "progress": "3/9 decompose",
  "status": "complete",
  "result": {
    // Phase-specific data
  },
  "next_action": "Human-readable guidance for Claude",
  "prompt_template": "Optional: template for Claude's reasoning",
  "metadata": {
    "duration_ms": 45
  }
}
```

### SIMPLE Query Early Exit

For SIMPLE queries, assess phase returns:

```json
{
  "phase": "assess",
  "progress": "1/9 assess",
  "status": "complete",
  "result": { "complexity": "SIMPLE" },
  "next_action": "retrieve_and_respond",
  "early_exit": true
}
```

Claude then calls retrieve and responds directly without remaining phases.

### Health Check Categories

The `aur doctor` output should group checks into categories:

```
=== MCP Integration Checks ===
[PASS] MCP config valid JSON
[PASS] Aurora MCP tools importable
[PASS] SOAR phases importable
[PASS] Memory database accessible
[WARN] Slash command references MCP server "aurora" (not found in config)

=== Suggested Fixes ===
- Run 'aur init --config' to configure MCP server for your AI tool
```

## Technical Considerations

### File Locations

| Component | Path |
|-----------|------|
| MCP Tools | `src/aurora_mcp/tools.py` |
| MCP Server | `src/aurora_mcp/server.py` |
| SOAR Orchestrator | `packages/soar/src/aurora_soar/orchestrator.py` |
| SOAR Phases | `packages/soar/src/aurora_soar/phases/` |
| Health Checks | `packages/cli/src/aurora_cli/health_checks.py` |
| Init Command | `packages/cli/src/aurora_cli/commands/init.py` |
| Init Helpers | `packages/cli/src/aurora_cli/commands/init_helpers.py` |
| MCP Configurators | `packages/cli/src/aurora_cli/configurators/mcp/` |

### Dependencies

The new `aurora_soar` tool requires:
- Phase modules from `aurora_soar.phases` (assess, retrieve, decompose, verify, route, collect, synthesize, record, respond)
- `HybridRetriever` for retrieve phase
- `SQLiteStore` for memory access
- `ActivationEngine` for ACT-R scoring

The `aurora_soar` tool must NOT:
- Instantiate LLM clients
- Make external API calls
- Run multiple phases in a single invocation

### Multi-Turn Integration Approach

Each phase is a separate tool invocation:

1. **assess**: Run keyword-based `assess_complexity()`, return complexity level
2. **retrieve**: Run `HybridRetriever.retrieve()`, return context chunks
3. **decompose**: Return prompt template + context for Claude to reason
4. **verify**: Accept Claude's subgoals, validate against thresholds
5. **route**: Map subgoals to available agents
6. **collect**: Execute agent tasks (or return agent prompts for Claude)
7. **synthesize**: Return prompt template for Claude to combine results
8. **record**: Cache pattern in ACT-R memory
9. **respond**: Format final response using `Verbosity.JSON`

Claude performs the reasoning at phases 3, 4, 7. MCP provides structure and data.

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| MCP tool count | Reduced from 9 to 3 | Code inspection |
| SOAR phase execution | 100% of MEDIUM/COMPLEX/CRITICAL queries route through all 9 phases | Unit test assertions |
| SIMPLE query performance | <100ms response time | Integration test timing |
| Init validation coverage | Validates JSON syntax + server path for all MCP configs | Unit test coverage |
| Doctor check coverage | 6 functional checks implemented | Code inspection |
| Auto-fix functionality | 100% of fixable issues have working fix functions | Integration test with mock filesystem |
| Test coverage | >80% line coverage for new code | pytest-cov report |

## Open Questions

1. ~~**LLM-Free SOAR Execution**~~ **RESOLVED**: Multi-turn architecture adopted. Claude IS the LLM - MCP provides structure, Claude provides reasoning.

2. **MCP Server Process Testing**: FR-17 says "import Python and call functions directly." Is it acceptable to test `AuroraMCPTools` instantiation without a running MCP server?

   **Resolved**: Yes. Testing imports and method existence is sufficient. Actual MCP server testing would require process spawning, which is out of scope.

3. **Phase Timing in Response**: Should each phase response include timing?

   **Resolved**: Yes. Include `duration_ms` in metadata for each phase to help with debugging and optimization.

4. **State Management Between Phases**: How should state be passed between multi-turn phase invocations?

   **Recommended**: Each phase accepts required inputs as parameters. Claude is responsible for passing outputs from one phase as inputs to the next. No server-side session state required.

---

## Appendix: Existing Code References

### Current aurora_query Implementation (tools.py lines 378-457)

The current implementation:
- Validates parameters
- Retrieves chunks using `HybridRetriever`
- Assesses complexity with `_assess_complexity()` (returns float 0.0-1.0)
- Builds context response with `_build_context_response()`
- Returns JSON with context, assessment, and metadata

### SOAROrchestrator.execute() (orchestrator.py lines 129-278)

The orchestrator:
- Runs 9 phases in sequence
- Handles SIMPLE query early exit (line 205-208)
- Tracks costs, timing, and metadata
- Returns structured dict with answer, confidence, reasoning_trace, metadata

### SOAR Phases (packages/soar/src/aurora_soar/phases/)

| Phase | File | Key Function |
|-------|------|--------------|
| Assess | assess.py | `assess_complexity(query, llm_client)` |
| Retrieve | retrieve.py | `retrieve_context(query, complexity, store)` |
| Decompose | decompose.py | `decompose_query(query, context, complexity, llm_client, available_agents)` |
| Verify | verify.py | `verify_decomposition(decomposition, complexity, llm_client, ...)` |
| Route | route.py | `route_subgoals(decomposition, agent_registry)` |
| Collect | collect.py | `execute_agents(routing, context)` |
| Synthesize | synthesize.py | `synthesize_results(llm_client, query, collect_result, decomposition)` |
| Record | record.py | `record_pattern(store, query, complexity, ...)` |
| Respond | respond.py | `format_response(synthesis_result, record_result, metadata, verbosity)` |

### ToolIntegrationChecks (health_checks.py lines 535-707)

Current implementation:
- `_check_cli_tools()`: Checks for common AI CLI tools
- `_check_slash_commands()`: Uses `detect_configured_slash_tools()`
- `_check_mcp_servers()`: Uses `detect_configured_mcp_tools()`

Missing:
- Functional testing of MCP tools
- SOAR phase import verification
- Memory database accessibility check
- Cross-reference validation between slash commands and MCP configs
