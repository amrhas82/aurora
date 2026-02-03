# Tasks: LSP Integration via MCP Tools

## Relevant Files

### MCP Server & Tools
- `/home/hamr/PycharmProjects/aurora/src/aurora_mcp/server.py` - Main MCP server, currently deprecated, will host new tools
- `/home/hamr/PycharmProjects/aurora/src/aurora_mcp/tools.py` - MCP tool implementations
- `/home/hamr/PycharmProjects/aurora/packages/lsp/poc_mcp_server.py` - POC implementation to wire into production

### LSP Package
- `/home/hamr/PycharmProjects/aurora/packages/lsp/src/aurora_lsp/facade.py` - High-level sync API for LSP
- `/home/hamr/PycharmProjects/aurora/packages/lsp/src/aurora_lsp/analysis.py` - Dead code detection, usage summary, callers
- `/home/hamr/PycharmProjects/aurora/packages/lsp/src/aurora_lsp/client.py` - Async LSP client wrapper
- `/home/hamr/PycharmProjects/aurora/packages/lsp/src/aurora_lsp/filters.py` - Import vs usage filtering

### Slash Commands (to modify)
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/templates/slash_commands.py` - Remove search/get templates
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/templates/test_slash_commands.py` - Update tests for 4 commands

### MCP Configurator Infrastructure
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/mcp/base.py` - Base MCP configurator
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/mcp/registry.py` - MCP registry

### Documentation
- `/home/hamr/PycharmProjects/aurora/CLAUDE.md` - Add MCP tool guidance to managed block
- `/home/hamr/PycharmProjects/aurora/.aurora/AGENTS.md` - Add MCP tool documentation
- `/home/hamr/PycharmProjects/aurora/README.md` - Document MCP tools availability
- `/home/hamr/PycharmProjects/aurora/docs/02-features/mcp/MCP.md` - New file for MCP documentation
- `/home/hamr/PycharmProjects/aurora/docs/02-features/lsp/LSP.md` - Update to reference MCP integration

### Configuration
- `/home/hamr/PycharmProjects/aurora/pyproject.toml` - Add aurora-lsp dependency

### Doctor Command
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/doctor.py` - Update for MCP status

### Test Files
- `/home/hamr/PycharmProjects/aurora/tests/unit/mcp/test_lsp_tool.py` - New tests for lsp MCP tool
- `/home/hamr/PycharmProjects/aurora/tests/unit/mcp/test_mem_search_tool.py` - New tests for mem_search tool
- `/home/hamr/PycharmProjects/aurora/tests/unit/mcp/test_mcp_configurator.py` - New tests for MCP configurator integration
- `/home/hamr/PycharmProjects/aurora/tests/integration/mcp/test_mcp_server.py` - Integration tests
- `/home/hamr/PycharmProjects/aurora/packages/lsp/tests/test_filters.py` - Existing tests (7 passing)

### Notes

- **Testing Framework**: Use pytest with pytest-asyncio for async tests. Run with `make test` or `pytest tests/`.
- **TDD Pattern**: Write tests BEFORE implementation for all new MCP tool functions.
- **POC Reuse**: Wire `packages/lsp/poc_mcp_server.py` patterns into `src/aurora_mcp/server.py`. Do NOT create new LSP implementations.
- **FastMCP**: Use `fastmcp` package (already in dependencies) for MCP tool registration.
- **Read-Only MCP**: All `lsp` MCP actions must use `readOnlyHint: true`. Inline annotation is done by Claude via Edit tool as automatic follow-up.
- **Import Filtering**: The LSP package already separates imports from usages - leverage `aurora_lsp.analysis.CodeAnalyzer`.
- **Lazy Loading**: Initialize LSP servers on first request, not on startup.
- **Current slash command count**: The test expects 5 commands but COMMAND_TEMPLATES has 6 entries (search, get, plan, tasks, implement, archive). After removal of search/get, target is 4 (plan, tasks, implement, archive).

---

## Tasks

- [x] 0.0 Create feature branch
  <!-- @agent: @code-developer -->
  - [x] 0.1 Create and checkout branch `feature/lsp-mcp-integration`
    - tdd: no
    - verify: `git branch --show-current` shows `feature/lsp-mcp-integration`

- [x] 1.0 Write TDD tests for MCP tools (tests before implementation)
  <!-- @agent: @code-developer -->
  - [x] 1.1 Create test directory structure for MCP tests
    - tdd: no
    - Create `/home/hamr/PycharmProjects/aurora/tests/unit/mcp/__init__.py`
    - Create `/home/hamr/PycharmProjects/aurora/tests/integration/mcp/__init__.py`
    - verify: `ls tests/unit/mcp/__init__.py tests/integration/mcp/__init__.py`
  - [x] 1.2 Write unit tests for `lsp` MCP tool - deadcode action
    - tdd: yes
    - Create `tests/unit/mcp/test_lsp_tool.py`
    - Test `lsp(action="deadcode", path="src/")` returns expected structure
    - Test returns `dead_code` list with `name`, `file`, `line`, `kind` fields
    - Test returns `total` count
    - verify: `pytest tests/unit/mcp/test_lsp_tool.py::test_lsp_deadcode -v` (should fail - no implementation yet)
  - [x] 1.3 Write unit tests for `lsp` MCP tool - impact action
    - tdd: yes
    - Test `lsp(action="impact", path="file.py", line=42)` returns impact structure
    - Test returns `used_by_files`, `total_usages`, `top_callers`, `risk` fields
    - Test risk levels: low (0-2), medium (3-10), high (11+)
    - verify: `pytest tests/unit/mcp/test_lsp_tool.py::test_lsp_impact -v`
  - [x] 1.4 Write unit tests for `lsp` MCP tool - check action
    - tdd: yes
    - Test `lsp(action="check", path="file.py", line=42)` returns check structure
    - Test returns `used_by`, `risk` fields
    - Test default action is "check" when not specified
    - verify: `pytest tests/unit/mcp/test_lsp_tool.py::test_lsp_check -v`
  - [x] 1.5 Write unit tests for `mem_search` MCP tool
    - tdd: yes
    - Create `tests/unit/mcp/test_mem_search_tool.py`
    - Test `mem_search(query="SOAR")` returns search results
    - Test results contain `file`, `type`, `symbol`, `lines`, `score`, `used_by`, `called_by`, `calling`, `git` fields
    - Test `used_by` format is "N files(M)" for code or "-" for non-code
    - Test `called_by` returns list of caller functions/methods
    - Test `calling` returns list of called functions/methods (where LSP supports it)
    - Test `limit` parameter defaults to 5
    - verify: `pytest tests/unit/mcp/test_mem_search_tool.py -v`
  - [x] 1.6 Write integration tests for MCP server startup
    - tdd: yes
    - Create `tests/integration/mcp/test_mcp_server.py`
    - Test MCP server initializes with `lsp` and `mem_search` tools
    - Test tool registration with FastMCP
    - verify: `pytest tests/integration/mcp/test_mcp_server.py -v`
  - [x] 1.7 Write tests for CODE_QUALITY_REPORT.md generation format
    - tdd: yes
    - Test report includes severity categories: CRITICAL, HIGH, MEDIUM, LOW
    - Test report format includes file:line references
    - Test report location logic (docs/ if exists, else root)
    - verify: `pytest tests/unit/mcp/test_lsp_tool.py::test_code_quality_report -v`
  - [x] 1.8 Write tests for MCP configurator integration
    - tdd: yes
    - Test MCP tools register with `configurators/mcp/registry.py`
    - Test configurator supports Claude, Cursor, Cline, Continue tools
    - verify: `pytest tests/unit/mcp/test_mcp_configurator.py -v`
  - [x] 1.9 Verify: all TDD tests exist and fail appropriately (no implementation)
    - tdd: no
    - verify: `pytest tests/unit/mcp/ tests/integration/mcp/ -v --collect-only` shows >10 tests

- [x] 2.0 Implement `lsp` MCP tool
  <!-- @agent: @code-developer -->
  - [x] 2.1 Create LSP tool wrapper in aurora_mcp
    - tdd: yes
    - Add `lsp_tool.py` to `src/aurora_mcp/`
    - Import and use `AuroraLSP` from `aurora_lsp.facade`
    - Implement lazy initialization (server starts on first request)
    - Share caching with existing Aurora caching infrastructure (`.aurora/cache/`)
    - verify: `pytest tests/unit/mcp/test_lsp_tool.py::test_lsp_initialization -v`
  - [x] 2.1.1 Wire POC patterns from poc_mcp_server.py
    - tdd: no
    - Review `packages/lsp/poc_mcp_server.py` for patterns to reuse
    - Integrate POC tool registration and response formatting
    - Do NOT create new LSP implementations - reuse POC code
    - verify: `grep -q "poc" src/aurora_mcp/lsp_tool.py` or patterns are integrated
  - [x] 2.2 Implement `deadcode` action
    - tdd: yes
    - Wire to `AuroraLSP.find_dead_code(path)`
    - Return format: `{action, path, dead_code: [{name, file, line, kind}], total}`
    - verify: `pytest tests/unit/mcp/test_lsp_tool.py::test_lsp_deadcode -v`
  - [x] 2.3 Implement `impact` action
    - tdd: yes
    - Wire to `AuroraLSP.get_usage_summary(path, line, col)`
    - Return format: `{action, path, line, symbol, used_by_files, total_usages, top_callers, risk}`
    - Calculate risk from usage count (0-2: low, 3-10: medium, 11+: high)
    - verify: `pytest tests/unit/mcp/test_lsp_tool.py::test_lsp_impact -v`
  - [x] 2.4 Implement `check` action
    - tdd: yes
    - Quick pre-edit check - lighter than impact
    - Return format: `{action, path, line, symbol, used_by, risk}`
    - verify: `pytest tests/unit/mcp/test_lsp_tool.py::test_lsp_check -v`
  - [x] 2.5 Add MCP tool description with auto-invocation triggers
    - tdd: no
    - Add docstring triggers: "BEFORE modifying or deleting functions/classes"
    - Add keyword triggers: "deadcode", "dead code", "unused code", "cleanup", "refactor"
    - Add post-analysis instruction for automatic inline annotation:
      - After `deadcode` action: add `#DEADCODE` markers to flagged symbols
      - After `impact` action with high-risk: add `#REFAC` markers
      - Supported markers: `#DEADCODE`, `#REFAC`, `#UNUSED`, `#COMPLEX`, `#TYPE`
      - Marker format: `# #DEADCODE: 0 usages - safe to remove` (end-of-line comment)
    - verify: `grep -q "BEFORE modifying" src/aurora_mcp/lsp_tool.py`
  - [x] 2.6 Register `lsp` tool in MCP server with annotations
    - tdd: yes
    - Add tool registration in `server.py` `_register_tools()`
    - Add `readOnlyHint: true` annotation
    - Add `title: "LSP Code Intelligence"` for discoverability
    - verify: `pytest tests/integration/mcp/test_mcp_server.py::test_lsp_tool_registered -v`
  - [x] 2.7 Implement CODE_QUALITY_REPORT.md generation
    - tdd: yes
    - Generate report as part of `deadcode` action output
    - Location logic: `/docs/CODE_QUALITY_REPORT.md` if `/docs` exists, else project root
    - Severity categories: CRITICAL, HIGH, MEDIUM, LOW
    - Format: summary counts, file:line references, symbol names, suggested actions
    - verify: `pytest tests/unit/mcp/test_lsp_tool.py::test_code_quality_report -v`
  - [x] 2.8 Integrate with MCP configurator infrastructure
    - tdd: yes
    - Wire new MCP tools with `configurators/mcp/base.py` and `registry.py`
    - Ensure tools are registered for Claude, Cursor, Cline, Continue
    - verify: `pytest tests/unit/mcp/test_mcp_configurator.py -v`
  - [x] 2.9 Verify: `lsp` tool unit tests pass
    - tdd: no
    - verify: `pytest tests/unit/mcp/test_lsp_tool.py -v`

- [ ] 3.0 Implement `mem_search` MCP tool
  <!-- @agent: @code-developer -->
  - [ ] 3.1 Create mem_search tool wrapper
    - tdd: yes
    - Add `mem_search_tool.py` to `src/aurora_mcp/`
    - Import existing memory search from `aurora_core.store`
    - verify: `pytest tests/unit/mcp/test_mem_search_tool.py::test_mem_search_initialization -v`
  - [ ] 3.2 Implement search with LSP enrichment
    - tdd: yes
    - Call existing memory store search
    - For code results, enrich with LSP call relationship data:
      - `used_by`: Format as "N files(M)" where N=files, M=total usages
      - `called_by`: List of functions/methods that call this symbol
      - `calling`: List of functions/methods this symbol calls (where supported)
    - Return `-` for non-code (kb) results
    - Match `aur mem search --show-scores` output completeness for call data
    - verify: `pytest tests/unit/mcp/test_mem_search_tool.py::test_mem_search_enrichment -v`
  - [ ] 3.3 Add git info to search results
    - tdd: yes
    - Include commit count and last modified time
    - Format as "N commits, Xh/Xd ago"
    - verify: `pytest tests/unit/mcp/test_mem_search_tool.py::test_mem_search_git_info -v`
  - [ ] 3.4 Add MCP tool description for auto-invocation
    - tdd: no
    - Triggers: "search code", "find symbols", "where is", "usage of"
    - verify: `grep -q "search indexed code" src/aurora_mcp/mem_search_tool.py`
  - [ ] 3.5 Register `mem_search` tool in MCP server
    - tdd: yes
    - Add tool registration in `server.py` `_register_tools()`
    - verify: `pytest tests/integration/mcp/test_mcp_server.py::test_mem_search_tool_registered -v`
  - [ ] 3.6 Verify: `mem_search` tool unit tests pass
    - tdd: no
    - verify: `pytest tests/unit/mcp/test_mem_search_tool.py -v`

- [ ] 4.0 Remove deprecated slash commands
  <!-- @agent: @code-developer -->
  - [ ] 4.1 Remove SEARCH_TEMPLATE from slash_commands.py
    - tdd: no
    - Delete `SEARCH_TEMPLATE` variable
    - Remove "search" entry from `COMMAND_TEMPLATES` dict
    - verify: `! grep -q "SEARCH_TEMPLATE" packages/cli/src/aurora_cli/templates/slash_commands.py` (exits 0 when not found)
  - [ ] 4.2 Remove GET_TEMPLATE from slash_commands.py
    - tdd: no
    - Delete `GET_TEMPLATE` variable
    - Remove "get" entry from `COMMAND_TEMPLATES` dict
    - verify: `! grep -q "GET_TEMPLATE" packages/cli/src/aurora_cli/templates/slash_commands.py` (exits 0 when not found)
  - [ ] 4.3 Update test_slash_commands.py for 4 commands
    - tdd: no
    - Change `test_command_templates_count` assertion from 5 to 4
    - Change `test_all_expected_commands_present` expected set to `{"plan", "tasks", "implement", "archive"}`
    - Remove any tests specific to search/get templates
    - verify: `pytest tests/unit/cli/templates/test_slash_commands.py -v`
  - [ ] 4.4 Verify: COMMAND_TEMPLATES has exactly 4 entries
    - tdd: no
    - verify: `python -c "from aurora_cli.templates.slash_commands import COMMAND_TEMPLATES; assert len(COMMAND_TEMPLATES) == 4, f'Got {len(COMMAND_TEMPLATES)}'"` exits 0

- [ ] 5.0 Add aurora-lsp to dependencies
  <!-- @agent: @code-developer -->
  - [ ] 5.1 Add aurora-lsp to pyproject.toml dependencies
    - tdd: no
    - Add `"aurora-lsp"` to dependencies list
    - Ensure LSP package is included in standard Aurora install
    - verify: `grep -q "aurora-lsp" pyproject.toml`
  - [ ] 5.2 Update packages/lsp/pyproject.toml for proper packaging
    - tdd: no
    - Ensure package exports `aurora_lsp` module
    - Add `multilspy>=0.0.15` dependency
    - verify: `pip install -e packages/lsp && python -c "from aurora_lsp import AuroraLSP"`
  - [ ] 5.3 Verify: pip install aurora-actr includes LSP
    - tdd: no
    - verify: `pip install -e . && python -c "from aurora_lsp.facade import AuroraLSP"` exits 0

- [ ] 6.0 Update aur doctor command
  <!-- @agent: @code-developer -->
  - [ ] 6.1 Add MCP tools status check to doctor
    - tdd: yes
    - Check that MCP server has `lsp` and `mem_search` tools
    - Show installed MCP tools count
    - Write test first in `tests/unit/cli/test_doctor.py`
    - verify: `pytest tests/unit/cli/test_doctor.py::test_doctor_mcp_tools -v`
  - [ ] 6.2 Update slash command count detection
    - tdd: no
    - Doctor should expect 4 slash commands (not 6)
    - verify: `aur doctor 2>&1 | grep -q "4"` or similar validation
  - [ ] 6.3 Add LSP package installation check
    - tdd: no
    - Verify aurora-lsp is importable
    - Show warning if LSP not available
    - verify: `aur doctor` runs without error

- [ ] 7.0 Update documentation
  <!-- @agent: @code-developer -->
  - [ ] 7.1 Update CLAUDE.md managed block with MCP guidance
    - tdd: no
    - Add section about `lsp` and `mem_search` MCP tools availability
    - Explain when Claude should use them (before edits, for searches, refactoring)
    - Document automatic annotation workflow
    - verify: `grep -q "mem_search" CLAUDE.md`
  - [ ] 7.2 Update AGENTS.md with MCP tool documentation
    - tdd: no
    - Document available MCP tools and their actions
    - Provide natural language trigger examples
    - Document two-step workflow: report generation + automatic annotation
    - verify: `grep -q "lsp.*MCP" .aurora/AGENTS.md`
  - [ ] 7.3 Create docs/02-features/mcp/MCP.md
    - tdd: no
    - Create directory if needed: `mkdir -p docs/02-features/mcp`
    - Document `lsp` and `mem_search` tools with examples
    - Document CODE_QUALITY_REPORT.md output format
    - Document automatic inline annotation workflow
    - Reference LSP.md for LSP details
    - verify: `test -f docs/02-features/mcp/MCP.md`
  - [ ] 7.4 Update README.md with MCP tools section
    - tdd: no
    - Add section about MCP tools availability
    - Explain LSP integration benefits
    - List supported languages (10 via multilspy)
    - verify: `grep -q "MCP" README.md`
  - [ ] 7.5 Update LSP.md to reference MCP integration
    - tdd: no
    - Add "MCP Integration" section
    - Link to new MCP.md
    - verify: `grep -q "MCP" docs/02-features/lsp/LSP.md`
  - [ ] 7.6 Verify: all documentation files exist and have required content
    - tdd: no
    - verify: `grep -l "lsp\|MCP" CLAUDE.md .aurora/AGENTS.md docs/02-features/mcp/MCP.md README.md docs/02-features/lsp/LSP.md | wc -l` equals 5

- [ ] 8.0 Integration testing and validation
  <!-- @agent: @code-developer -->
  - [ ] 8.1 Run full MCP integration test suite
    - tdd: no
    - verify: `pytest tests/integration/mcp/ -v`
  - [ ] 8.2 Run existing LSP package tests
    - tdd: no
    - Ensure 7/7 filter tests still pass
    - verify: `pytest packages/lsp/tests/test_filters.py -v`
  - [ ] 8.3 Run full test suite
    - tdd: no
    - verify: `make test`
  - [ ] 8.4 Run linter and type checker
    - tdd: no
    - verify: `make format && make type-check`
  - [ ] 8.5 Verify MCP server starts with both tools
    - tdd: no
    - Test MCP server can be started
    - verify: `python -c "from aurora_mcp.server import AuroraMCPServer; s = AuroraMCPServer(test_mode=True); s.list_tools()" | grep -q "lsp"`
  - [ ] 8.6 Verify: all success metrics met
    - tdd: no
    - MCP tools: 2 (lsp, mem_search)
    - Slash commands: 4 (plan, tasks, implement, archive)
    - MCP tool unit tests: >10
    - LSP action coverage: 100% (deadcode, impact, check)
    - Existing LSP tests: 7/7 passing
    - verify: `pytest tests/unit/mcp/ -v --tb=no | grep -c "PASSED"` >= 10
