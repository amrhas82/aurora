# Task List: Interface Cleanup - Simplify CLI/MCP/Slash Commands

Generated from: `/home/hamr/PycharmProjects/aurora/tasks/0020-prd-interface-cleanup.md`

## Relevant Files

### New Files to Create
- `/home/hamr/PycharmProjects/aurora/tests/unit/mcp/test_agent_tools.py` - Unit tests for new MCP agent tools
- `/home/hamr/PycharmProjects/aurora/tests/integration/mcp/test_agent_tools_integration.py` - Integration tests for MCP agent tools
- `/home/hamr/PycharmProjects/aurora/docs/INTERFACE_GUIDE.md` - Comprehensive interface documentation

### Files Modified
- `/home/hamr/PycharmProjects/aurora/src/aurora/mcp/tools.py` - Added 3 agent tools (list/search/show), removed aurora_stats
- `/home/hamr/PycharmProjects/aurora/src/aurora/mcp/server.py` - Registered new agent tools with rich descriptions, removed aurora_stats registration
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/main.py` - Removed aur query command and all helper functions
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/templates/commands.py` - Removed 6 slash command templates (init/query/index/search/doctor/agents), kept 2 (plan/checkpoint)
- `/home/hamr/PycharmProjects/aurora/CLAUDE.md` - TODO: Remove deleted slash command references
- `/home/hamr/PycharmProjects/aurora/docs/cli/CLI_USAGE_GUIDE.md` - TODO: Remove aur query documentation

### Files to Delete
- Any test files for deleted commands (if they exist):
  - `tests/unit/cli/test_query.py`
  - `tests/integration/mcp/test_stats.py`

### Files to Audit (scan for deleted command references)
- All agent files in `~/.claude/agents/*.md` (if exist)
- All skill files in `~/.claude/skills/**/*.md` (if exist)
- All task briefs in `~/.claude/resources/task-briefs.md` (if exists)
- All documentation in `/home/hamr/PycharmProjects/aurora/docs/**/*.md`

### Notes

**Testing Framework:**
- Use pytest with `@pytest.mark.mcp` for MCP tests
- Follow existing test patterns in `tests/unit/mcp/test_aurora_query_tool.py`
- Mock AuroraMCPTools with `db_path=":memory:"` for unit tests
- Use `json.loads()` to parse tool output and assert on structure

**Architectural Patterns:**
- Reuse `aurora_cli.agent_discovery.scanner.AgentScanner` and `ManifestManager`
- Follow error handling pattern from existing MCP tools (return JSON with "error" key)
- Use shared manifest cache at `~/.aurora/agent_manifest.json` (TTL: 5 minutes)
- MCP tools return structured JSON, CLI returns human-readable formatted output

**TDD Approach:**
- Write tests BEFORE implementation for all new MCP tools
- Test success cases, error cases (agent not found, invalid parameters), edge cases (empty results)
- Verify JSON structure matches PRD schema

**Shell Integration Tests:**
- After deletions in Phase 2, run: `pytest tests/integration/ -v`
- Verify no import errors or missing command references

**Important Considerations:**
- Substring matching for `aurora_search_agents` relevance scoring (not fuzzy matching)
- Error JSON format: `{"error": "message", "agent_id": "id"}` when agent not found
- Rich keyword descriptions in tool registration for Claude intent matching
- All 24 checklist items from PRD must be covered

## Tasks

- [x] 1.0 Phase 1: Add MCP Agent Tools with TDD
  - [x] 1.1 Write unit tests for `aurora_list_agents` MCP tool covering: success with agents, empty result when no agents, JSON structure validation (array of objects with id/title/source_path/when_to_use fields)
  - [x] 1.2 Implement `aurora_list_agents` in `/home/hamr/PycharmProjects/aurora/src/aurora/mcp/tools.py` by importing and using `AgentScanner` and `ManifestManager` from `aurora_cli.agent_discovery`, returning JSON array of all discovered agents
  - [x] 1.3 Write unit tests for `aurora_search_agents` MCP tool covering: successful search with matches, no matches returns empty array, relevance scoring based on substring matching in id/title/when_to_use fields, query parameter validation (empty/whitespace)
  - [x] 1.4 Implement `aurora_search_agents` with substring-based relevance scoring (0.0-1.0 scale) that searches agent id, title, and when_to_use fields, returning JSON array sorted by relevance_score descending
  - [x] 1.5 Write unit tests for `aurora_show_agent` MCP tool covering: successful retrieval with valid agent_id, error JSON when agent not found, full content field includes complete markdown, agent_id parameter validation
  - [x] 1.6 Implement `aurora_show_agent` that accepts agent_id parameter, returns JSON with full agent details including complete markdown content, or error JSON `{"error": "Agent not found", "agent_id": "..."}` if not found
  - [x] 1.7 Register all 3 tools in `/home/hamr/PycharmProjects/aurora/src/aurora/mcp/server.py` in the `_register_tools()` method following the existing pattern with `@self.mcp.tool()` decorator
  - [x] 1.8 Add rich keyword descriptions for each tool in registration covering: primary action keywords (list/show/search/find/discover/browse/retrieve/get/fetch), domain keywords (agent/specialist/expert/role/persona/subagent), context keywords (available/registered/defined/configured/ready/accessible), use case keywords (what/which/who/when/help/assist/guide)
  - [x] 1.9 Write MCP integration tests in `/home/hamr/PycharmProjects/aurora/tests/integration/mcp/test_agent_tools_integration.py` that verify tools work end-to-end through AuroraMCPServer instance (initialize server, call tools, verify JSON output)
  - [x] 1.10 Run all new tests with `pytest tests/unit/mcp/test_agent_tools.py tests/integration/mcp/test_agent_tools_integration.py -v` and verify 100% pass rate

- [x] 2.0 Phase 2: Delete Redundant Commands and Tests
  - [x] 2.1 Remove `aur query` command from `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/main.py` by deleting the query command function, imports, and CLI group registration
  - [x] 2.2 Check if `/home/hamr/PycharmProjects/aurora/tests/unit/cli/test_query.py` exists and delete it if present
  - [x] 2.3 Remove `aurora_stats` tool from `/home/hamr/PycharmProjects/aurora/src/aurora/mcp/tools.py` by deleting the method implementation in AuroraMCPTools class
  - [x] 2.4 Remove `aurora_stats` tool registration from `/home/hamr/PycharmProjects/aurora/src/aurora/mcp/server.py` by deleting the `@self.mcp.tool()` decorated function in `_register_tools()`
  - [x] 2.5 Check if `/home/hamr/PycharmProjects/aurora/tests/integration/mcp/test_stats.py` exists and delete it if present
  - [x] 2.6 Remove 6 slash command templates from `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/templates/commands.py`: delete INIT_COMMAND, QUERY_COMMAND, INDEX_COMMAND, SEARCH_COMMAND, AGENTS_COMMAND, DOCTOR_COMMAND constants and remove them from COMMAND_TEMPLATES dictionary
  - [x] 2.7 Update `get_command_template()` and `get_all_command_templates()` functions in templates/commands.py to reflect removed commands
  - [x] 2.8 Search for test files referencing deleted slash commands with `grep -r "aur:init\|aur:query\|aur:index\|aur:search\|aur:agents\|aur:doctor" tests/` and delete any found test files
  - [x] 2.9 Run shell integration tests with `pytest tests/integration/ -v --tb=short` to verify no runtime errors or import failures from deletions

- [ ] 3.0 Phase 3: Documentation and Compatibility Audit
  - [ ] 3.1 Create `/home/hamr/PycharmProjects/aurora/docs/INTERFACE_GUIDE.md` with comprehensive table containing: columns (Command Name, Interface Type, Purpose, When To Use, Syntax, Example), all current commands (7 CLI: init/doctor/mem index/mem search/mem stats/agents/plan + 9 MCP: query/search/index/context/related/get/list_agents/search_agents/show_agent + 2 Slash: plan/checkpoint), 2 future slash commands marked as "planned" (archive/implement)
  - [ ] 3.2 Add decision criteria section to INTERFACE_GUIDE.md explaining: CLI for human terminal interaction with formatted output, MCP for Claude programmatic access with JSON output, Slash for multi-step workflow orchestration following OpenSpec pattern
  - [ ] 3.3 Add OpenSpec workflow pattern explanation to INTERFACE_GUIDE.md describing the read state → make decisions → invoke CLI/MCP → write results pattern used by /aur:plan and future /aur:archive and /aur:implement commands
  - [ ] 3.4 Update `/home/hamr/PycharmProjects/aurora/CLAUDE.md` to remove all references to deleted slash commands (/aur:init, /aur:query, /aur:index, /aur:search, /aur:agents, /aur:doctor) and add reference to new INTERFACE_GUIDE.md
  - [ ] 3.5 Update `/home/hamr/PycharmProjects/aurora/docs/cli/CLI_USAGE_GUIDE.md` to remove all documentation for `aur query` command including usage examples, flags, and any cross-references
  - [ ] 3.6 Scan `~/.claude/agents/*.md` files (if they exist) with `grep -r "/aur:init\|/aur:query\|/aur:index\|/aur:search\|/aur:agents\|/aur:doctor" ~/.claude/agents/` and update any references to use appropriate replacements (CLI commands or MCP tools)
  - [ ] 3.7 Scan `~/.claude/skills/**/*.md` files (if they exist) with `grep -r "/aur:init\|/aur:query\|/aur:index\|/aur:search\|/aur:agents\|/aur:doctor" ~/.claude/skills/` and update any references
  - [ ] 3.8 Scan `~/.claude/resources/task-briefs.md` (if exists) with `grep "/aur:init\|/aur:query\|/aur:index\|/aur:search\|/aur:agents\|/aur:doctor"` and update any references
  - [ ] 3.9 Scan all project documentation files with `grep -r "/aur:init\|/aur:query\|/aur:index\|/aur:search\|/aur:agents\|/aur:doctor\|aur query" /home/hamr/PycharmProjects/aurora/docs/` and update all found references
  - [ ] 3.10 Add comment in CLAUDE.md noting that global `~/.claude/CLAUDE.md` should be updated to reflect new command structure (for user action, not automated)

- [ ] 4.0 Phase 4: Verification and Integration Testing
  - [ ] 4.1 Run full test suite with `make quality-check` and verify all tests pass (allowing existing 14 skipped tests and 6 mypy errors)
  - [ ] 4.2 Run unit tests specifically for MCP agent tools with `pytest tests/unit/mcp/test_agent_tools.py -v --cov=src/aurora/mcp/tools` and verify ≥80% coverage for new code
  - [ ] 4.3 Run integration tests with `pytest tests/integration/ -v` and verify no new failures introduced
  - [ ] 4.4 Manual test: Start MCP server with `python -m aurora.mcp.server` and verify it starts without errors
  - [ ] 4.5 Manual test: Use Claude Desktop to invoke `aurora_list_agents` and verify it returns JSON array with agent information
  - [ ] 4.6 Manual test: Use Claude Desktop to invoke `aurora_search_agents` with query "test" and verify it returns relevant agents with scores
  - [ ] 4.7 Manual test: Use Claude Desktop to invoke `aurora_show_agent` with valid agent_id and verify full content is returned
  - [ ] 4.8 Manual test: Use Claude Desktop to invoke `aurora_show_agent` with invalid agent_id and verify error JSON is returned
  - [ ] 4.9 Verify retained CLI commands work: run `aur init --help`, `aur doctor --help`, `aur mem index --help`, `aur mem search --help`, `aur mem stats --help`, `aur agents --help`, `aur plan --help` and verify all display help correctly
  - [ ] 4.10 Verify retained slash commands: check that `/aur:plan` and `/aur:checkpoint` command files still exist in appropriate locations and are accessible
  - [ ] 4.11 Run type checking with `mypy packages/cli/src/aurora_cli/ src/aurora/mcp/ --strict` and verify no NEW mypy errors beyond existing 6
  - [ ] 4.12 Calculate code reduction metric: count lines deleted vs added using `git diff --stat` and verify net reduction ≥200 lines
  - [ ] 4.13 Verify documentation completeness: review INTERFACE_GUIDE.md table and confirm all 18 current commands (7 CLI + 9 MCP + 2 Slash) are documented with complete information
  - [ ] 4.14 Final verification: Compare output of retained commands before/after changes to ensure 100% functional parity (run `aur agents list` and compare output format)

---

## Implementation Notes

**Phase 1 - TDD Pattern:**
1. Write test file with all test cases for one tool
2. Run tests and watch them fail (red)
3. Implement tool to make tests pass (green)
4. Refactor if needed
5. Move to next tool

**Phase 2 - Safe Deletions:**
- Use `git rm` for file deletions to track in version control
- Run tests after each deletion group to catch issues early
- Keep a backup branch before starting deletions

**Phase 3 - Audit Strategy:**
- Use grep with multiple patterns in single command for efficiency
- Document all found references in a temp file before updating
- Validate updates don't break markdown formatting

**Phase 4 - Verification Priority:**
- Automated tests first (fast feedback)
- Manual MCP tests second (require Claude Desktop setup)
- CLI verification last (simple smoke tests)

**Manifest Caching:**
- Both CLI and MCP tools share `~/.aurora/agent_manifest.json`
- 5-minute TTL ensures consistency across interfaces
- Use `ManifestManager.get_or_refresh()` pattern for auto-refresh

**Error Handling:**
- All MCP tools must return valid JSON even in error cases
- Use try-except blocks around agent discovery operations
- Log errors to MCP logger for debugging

**Success Criteria:**
- All 24 checklist items from PRD completed
- Zero new test failures
- Net code reduction ≥200 lines
- 100% command coverage in INTERFACE_GUIDE.md

---

**Status:** Ready for implementation
**Generated:** 2026-01-05
**Next Step:** Begin Phase 1, Task 1.1 - Write unit tests for aurora_list_agents
