# Tasks: LSP Integration via MCP Tools

## Phase 1: Test Infrastructure & Slash Command Cleanup

- [ ] 1.1 Delete tests for removed slash commands
  <!-- @agent: @code-developer -->
  - tdd: no
  - verify: `make test`
  - Update test asserting command count (change from 5 to 4)
  - Remove tests for `search` and `get` command templates
  - Update `test_all_expected_commands_present` to expect: plan, tasks, implement, archive
  - **Validation**: All existing tests pass, no references to search/get in test files

- [ ] 1.2 Remove `/aur:search` and `/aur:get` slash commands
  <!-- @agent: @code-developer -->
  - tdd: no
  - verify: `make test && grep -r "aur:search\|aur:get" packages/cli/`
  - Update `templates/slash_commands.py` to remove SEARCH_TEMPLATE and GET_TEMPLATE
  - Update COMMAND_TEMPLATES dictionary to have 4 entries (plan, tasks, implement, archive)
  - Remove from skill registration
  - **Validation**: grep returns no matches, `aur doctor` shows 4 slash commands

- [ ] 1.3 Write TDD tests for `lsp` MCP tool (before implementation)
  <!-- @agent: @code-developer -->
  - tdd: yes
  - verify: `pytest packages/lsp/tests/test_mcp_tools.py -v`
  - Create `packages/lsp/tests/test_mcp_tools.py`
  - Test `deadcode` action: input validation, output format, file:line references
  - Test `impact` action: caller analysis, risk level classification
  - Test `check` action: quick usage count, risk level
  - Test CODE_QUALITY_REPORT.md generation and format
  - **Validation**: Tests exist and FAIL (TDD red phase)

- [ ] 1.4 Write TDD tests for `mem_search` MCP tool (before implementation)
  <!-- @agent: @code-developer -->
  - tdd: yes
  - verify: `pytest packages/lsp/tests/test_mem_search_mcp.py -v`
  - Create `packages/lsp/tests/test_mem_search_mcp.py`
  - Test search with LSP enrichment (`used_by`, `called_by`, `calling` fields)
  - Test compact JSON output format
  - Test `query` and `limit` parameters
  - **Validation**: Tests exist and FAIL (TDD red phase)

## Phase 2: MCP Tool Implementation

- [ ] 2.1 Implement `lsp` MCP tool with three actions
  <!-- @agent: @code-developer -->
  - tdd: yes
  - verify: `pytest packages/lsp/tests/test_mcp_tools.py -v`
  - Create `packages/lsp/src/aurora_lsp/mcp_server.py`
  - Reuse patterns from `packages/lsp/poc_mcp_server.py` (no new LSP implementations)
  - Implement `deadcode` action: scan file/directory for symbols with 0 usages
  - Implement `impact` action: full analysis with callers, risk level, usage count
  - Implement `check` action: quick pre-edit usage count with risk level
  - Add `readOnlyHint: true` annotation
  - Add `title: "LSP Code Intelligence"` for discoverability
  - **Validation**: All TDD tests from 1.3 pass (TDD green phase)

- [ ] 2.2 Implement CODE_QUALITY_REPORT.md generation
  <!-- @agent: @code-developer -->
  - tdd: yes
  - verify: `pytest packages/lsp/tests/test_mcp_tools.py::test_report_generation -v`
  - Output location: `/docs/CODE_QUALITY_REPORT.md` if `/docs` exists, otherwise project root
  - Use severity categories: CRITICAL, HIGH, MEDIUM, LOW
  - Format: file:line references grouped by category
  - Include: summary counts, symbol names, suggested actions
  - **Validation**: Report generated matches expected format

- [ ] 2.3 Implement `mem_search` MCP tool
  <!-- @agent: @code-developer -->
  - tdd: yes
  - verify: `pytest packages/lsp/tests/test_mem_search_mcp.py -v`
  - Wrap existing memory store search functionality
  - Enrich code results with LSP call relationship data:
    - `used_by`: files and count (format: "N files(M)")
    - `called_by`: functions/methods that call this symbol
    - `calling`: functions/methods this symbol calls
  - Match `aur mem search --show-scores` output completeness
  - Support `query` (required) and `limit` (default 5) parameters
  - **Validation**: All TDD tests from 1.4 pass (TDD green phase)

- [ ] 2.4 Write MCP tool descriptions for automatic invocation
  <!-- @agent: @code-developer -->
  - tdd: no
  - verify: `grep -A5 "description" packages/lsp/src/aurora_lsp/mcp_server.py`
  - **lsp tool description must include**:
    - "Use this tool BEFORE modifying or deleting functions/classes"
    - "Use this tool for LSP-powered refactoring and symbol analysis"
    - "Use this tool when user mentions 'deadcode', 'dead code', 'unused code', 'cleanup', or 'refactor'"
    - "After generating CODE_QUALITY_REPORT.md, automatically add inline markers to source files"
  - **mem_search tool description must include**:
    - "Use this tool to search indexed code and find symbols"
    - "Returns call relationships alongside search results"
  - Descriptions clear enough for Claude AND existing skills/subagents
  - **Validation**: Descriptions match PRD requirement #3

- [ ] 2.5 Define inline annotation markers in MCP response
  <!-- @agent: @code-developer -->
  - tdd: yes
  - verify: `pytest packages/lsp/tests/test_mcp_tools.py::test_annotation_markers -v`
  - MCP response includes annotation instructions for Claude:
    - After `deadcode`: add `#DEADCODE` markers
    - After `impact` with high-risk: add `#REFAC` markers
  - Markers: `#DEADCODE`, `#REFAC`, `#UNUSED`, `#COMPLEX`, `#TYPE`
  - Format: `# #DEADCODE: 0 usages - safe to remove` (end-of-line comment)
  - **Validation**: MCP response includes annotation_instructions field

## Phase 3: MCP Infrastructure Integration

- [ ] 3.1 Integrate with existing MCP configurator infrastructure
  <!-- @agent: @code-developer -->
  - tdd: no
  - verify: `python -c "from aurora_cli.configurators.mcp.registry import MCPRegistry; print('OK')"`
  - Reuse `packages/cli/src/aurora_cli/configurators/mcp/base.py`
  - Reuse `packages/cli/src/aurora_cli/configurators/mcp/registry.py`
  - Register `lsp` and `mem_search` tools with configurator
  - Support Claude, Cursor, Cline, and Continue tools
  - **Validation**: MCP tools appear in configurator registry

- [ ] 3.2 Implement lazy-loading for LSP servers
  <!-- @agent: @code-developer -->
  - tdd: yes
  - verify: `pytest packages/lsp/tests/test_lazy_loading.py -v`
  - Initialize LSP servers on first request, not on startup
  - Share caching with existing Aurora caching infrastructure (`.aurora/cache/`)
  - Do not pre-initialize language servers
  - **Validation**: Startup time not impacted by LSP, cache shared

- [ ] 3.3 Write integration tests for MCP server
  <!-- @agent: @code-developer -->
  - tdd: yes
  - verify: `pytest packages/lsp/tests/test_mcp_integration.py -v`
  - Test MCP server startup and tool registration
  - Test tool invocation via MCP protocol
  - Test autonomous background file reading (no prompts)
  - **Validation**: MCP server starts and responds to tool calls

## Phase 4: Installation & Dependencies

- [ ] 4.1 Declare LSP as mandatory dependency
  <!-- @agent: @code-developer -->
  - tdd: no
  - verify: `pip install -e . && python -c "import aurora_lsp; print('OK')"`
  - Add `aurora-lsp` to dependencies in root `pyproject.toml`
  - Ensure `pip install aurora-actr` includes LSP package
  - Update any package extras that should include LSP
  - **Validation**: Fresh install includes aurora-lsp package

- [ ] 4.2 Verify LSP package tests still pass
  <!-- @agent: @code-developer -->
  - tdd: no
  - verify: `pytest packages/lsp/tests/test_filters.py -v`
  - Maintain existing 7 passing tests in `test_filters.py`
  - Filter accuracy tests for import vs usage distinction
  - **Validation**: 7/7 tests pass

## Phase 5: Documentation Updates

- [ ] 5.1 Update CLAUDE.md managed block
  <!-- @agent: @code-developer -->
  - tdd: no
  - verify: `grep -A10 "MCP" CLAUDE.md`
  - Add guidance that MCP tools `lsp` and `mem_search` are available
  - Explain when Claude should use them (edits, searches, refactoring)
  - Document automatic annotation workflow (report + inline markers)
  - **Validation**: CLAUDE.md contains MCP tool guidance

- [ ] 5.2 Update AGENTS.md with MCP tool documentation
  <!-- @agent: @code-developer -->
  - tdd: no
  - verify: `grep -A10 "MCP\|lsp\|mem_search" .aurora/AGENTS.md`
  - Document available MCP tools and their actions
  - Provide examples of natural language triggers
  - Document the two-step workflow: report generation + automatic annotation
  - **Validation**: AGENTS.md contains MCP documentation

- [ ] 5.3 Update `aur doctor` command
  <!-- @agent: @code-developer -->
  - tdd: yes
  - verify: `aur doctor && pytest packages/cli/tests/test_doctor.py -v`
  - Detect reduced slash command count (4 instead of 6)
  - Show MCP tools installed and configured
  - Verify LSP package is installed
  - **Validation**: `aur doctor` shows MCP status, tests pass

- [ ] 5.4 Update README.md
  <!-- @agent: @code-developer -->
  - tdd: no
  - verify: `grep -A5 "MCP\|LSP" README.md`
  - Document MCP tools availability
  - Explain LSP integration benefits
  - List supported languages (10 via multilspy)
  - **Validation**: README.md contains MCP/LSP documentation

- [ ] 5.5 Create `docs/02-features/mcp/MCP.md`
  <!-- @agent: @code-developer -->
  - tdd: no
  - verify: `test -f docs/02-features/mcp/MCP.md`
  - Explain what MCP tools do and how they work
  - Document `lsp` and `mem_search` tools with examples
  - Document CODE_QUALITY_REPORT.md output format
  - Document automatic inline annotation workflow
  - Reference existing `docs/02-features/lsp/LSP.md` for LSP details
  - **Validation**: File exists with complete documentation

## Phase 6: Final Validation

- [ ] 6.1 Run full test suite
  <!-- @agent: @code-developer -->
  - tdd: no
  - verify: `make test`
  - All unit tests pass
  - All integration tests pass
  - No regressions in existing functionality
  - **Validation**: `make test` exits 0

- [ ] 6.2 Run quality checks
  <!-- @agent: @code-developer -->
  - tdd: no
  - verify: `make quality-check`
  - Type checking passes
  - Linting passes
  - No new warnings introduced
  - **Validation**: `make quality-check` exits 0

- [ ] 6.3 Verify success metrics
  <!-- @agent: @code-developer -->
  - tdd: no
  - verify: `aur doctor`
  - MCP tools implemented: 2 (`lsp`, `mem_search`)
  - Slash commands remaining: 4 (plan, tasks, implement, archive)
  - MCP tool unit tests: >10
  - LSP action coverage: 100% (deadcode, impact, check)
  - Existing LSP tests passing: 7/7
  - Languages supported: 10 (via multilspy)
  - **Validation**: All metrics met per PRD success criteria
