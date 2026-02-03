# PRD: LSP Integration via MCP Tools

## Overview

Aurora needs to transition from slash commands (`/aur:search`, `/aur:get`) to MCP tools (`lsp`, `mem_search`) for code intelligence and memory search. This refactoring leverages the existing dormant MCP configurator infrastructure and the completed LSP POC to provide semantic code analysis (dead code detection, impact analysis, usage tracking) through natural language interactions with Claude. MCP tools replace slash commands entirely - there is no CLI equivalent.

## Goals

1. **Enable semantic code intelligence** - Provide dead code detection, impact analysis, and pre-edit usage checks via the `lsp` MCP tool
2. **Enhance memory search with LSP context** - Enrich search results with call relationship data (used_by, called_by, calling)
3. **Autonomous background operation** - MCP tools read files and gather context silently without interrupting users (avoid Serena-like prompting annoyances)
4. **Ensure automatic invocation** - MCP tool descriptions must be clear enough that Claude and existing skills/subagents invoke them autonomously for refactoring, dead code, and code search tasks

## User Stories

1. As a developer, I want to ask Claude "find dead code in this file" so that I can clean up unused symbols without manually tracing references
2. As a developer, I want Claude to automatically check usage before modifying any function so that I'm warned about breaking changes without asking
3. As a developer, I want to search code and see call relationships (who calls this, what it calls) alongside results so that I can understand code structure
4. As a developer, I want to say "refactor this function" and have Claude use LSP intelligence so that renames and changes are safe
5. As a developer, I want to say "clean up this file" and get both a CODE_QUALITY_REPORT.md AND inline markers in my source code so I can see issues in context

## Supported Languages

Multilspy provides automatic support for 10 languages out of the box (already mapped in `client.py` lines 61-76):

| Language | Status |
|----------|--------|
| Python | Tested in POC |
| TypeScript | Tested in POC |
| JavaScript | Tested in POC |
| Rust | Supported |
| Go | Supported |
| Java | Supported |
| Ruby | Supported |
| C# | Supported |
| Dart | Supported |
| Kotlin | Supported |

No incremental language setup required (unlike tree-sitter). All languages work automatically when the corresponding language server is available on the system.

## Requirements

### MCP Tools

1. System MUST implement `lsp` MCP tool with three actions:
   - `deadcode`: Scan file/directory for symbols with 0 usages
   - `impact`: Full analysis showing callers, risk level, and usage count
   - `check`: Quick pre-edit usage count with risk level

2. System MUST implement `mem_search` MCP tool that:
   - Wraps existing memory store search functionality
   - Enriches code results with LSP call relationship data:
     - `used_by`: files and count (format: "N files(M)")
     - `called_by`: functions/methods that call this symbol
     - `calling`: functions/methods this symbol calls (where supported)
   - Matches `aur mem search --show-scores` output completeness for call data
   - Returns compact JSON for Claude to process
   - Supports `query` (required) and `limit` (default 5) parameters

3. System MUST write MCP tool descriptions that trigger automatic invocation AND instruct Claude to annotate source files:
   - **File edits**: "Use this tool BEFORE modifying or deleting functions/classes"
   - **Code searching**: "Use this tool to search indexed code and find symbols"
   - **Refactoring**: "Use this tool for LSP-powered refactoring and symbol analysis"
   - **Dead code**: "Use this tool when user mentions 'deadcode', 'dead code', 'unused code', 'cleanup', or 'refactor'"
   - **Post-analysis instruction**: "After generating CODE_QUALITY_REPORT.md, automatically add inline markers (#DEADCODE, #REFAC, etc.) to source files using Edit tool"
   - Descriptions MUST be clear enough for both Claude AND existing skills/subagents to invoke MCP autonomously

4. System MUST support autonomous background operation:
   - MCP tools read files silently without user prompts
   - No confirmation dialogs for read-only operations
   - Gather context autonomously to perform better without user interruption

5. System MUST integrate with existing MCP configurator infrastructure:
   - Reuse `packages/cli/src/aurora_cli/configurators/mcp/base.py`
   - Reuse `packages/cli/src/aurora_cli/configurators/mcp/registry.py`
   - Support Claude, Cursor, Cline, and Continue tools

6. System MUST add MCP tool annotations:
   - `readOnlyHint: true` for all `lsp` actions (no source file modification by MCP)
   - `title: "LSP Code Intelligence"` for discoverability

7. System MUST reuse LSP POC implementation from `packages/lsp/poc_mcp_server.py`:
   - No new LSP function implementations
   - Wire POC patterns into production MCP server
   - Integrate with existing `packages/lsp/src/aurora_lsp/` modules

### Code Quality Report Generation

8. System MUST generate `CODE_QUALITY_REPORT.md` file (MCP `lsp` tool output):
   - **Location**: `/docs/CODE_QUALITY_REPORT.md` if `/docs` exists, otherwise project root
   - **Trigger**: When user requests "refactor", "dead code", "cleanup", "code quality", or similar
   - **Format**: File:line references grouped by severity category
   - **No source modifications by MCP**: MCP tool is read-only (`readOnlyHint: true`)

9. Report MUST use severity categories matching existing CODE_QUALITY_REPORT.md format:
   - **CRITICAL** - Type errors, potential runtime errors
   - **HIGH** - Dead code, complex functions, unused imports/arguments
   - **MEDIUM** - Missing type annotations, commented-out code
   - **LOW** - Style issues, best practices suggestions

10. Report format MUST include:
    - Summary counts per category
    - Grouped findings with file:line references
    - Symbol name and description of issue
    - Suggested action (e.g., "Remove unused function", "Add type annotation")

### Automatic Inline Annotation (Claude follow-up workflow)

11. System MUST define automatic inline annotation as part of the code quality workflow:
    - **Step 1**: MCP `lsp` tool generates CODE_QUALITY_REPORT.md (read-only)
    - **Step 2**: Claude AUTOMATICALLY reads report and adds inline markers to source files using Edit tool
    - **No separate user request needed** - annotation is automatic after report generation
    - User receives BOTH: report file AND annotated source code

12. MCP tool description MUST instruct Claude to perform automatic annotation:
    - After `deadcode` action: add `#DEADCODE` markers to flagged symbols
    - After `impact` action with high-risk findings: add `#REFAC` markers
    - Markers: `#DEADCODE`, `#REFAC`, `#UNUSED`, `#COMPLEX`, `#TYPE`
    - Marker format: `# #DEADCODE: 0 usages - safe to remove` (as end-of-line comment)

13. Annotation workflow triggers:
    - User says: "find dead code" -> MCP generates report -> Claude adds `#DEADCODE` markers
    - User says: "check code quality" -> MCP generates report -> Claude adds relevant markers
    - User says: "refactor analysis" -> MCP generates report -> Claude adds `#REFAC` markers

### Slash Command Deprecation

14. System MUST remove `/aur:search` slash command from templates
15. System MUST remove `/aur:get` slash command from templates
16. System MUST retain `/aur:plan`, `/aur:implement`, `/aur:archive`, `/aur:tasks` slash commands
17. System MUST update `templates/slash_commands.py` to remove SEARCH_TEMPLATE and GET_TEMPLATE
18. System MUST update COMMAND_TEMPLATES dictionary to have 4 entries (plan, tasks, implement, archive)

### Installation and Dependencies

19. System MUST declare LSP as mandatory dependency in all relevant packages:
    - Add `aurora-lsp` to dependencies in root `pyproject.toml`
    - Ensure `pip install aurora-actr` includes LSP package
    - LSP package MUST be installed with all Aurora installations

20. System MUST use lazy-loading for LSP servers:
    - Initialize LSP servers on first request, not on startup
    - Share caching with existing Aurora caching infrastructure (`.aurora/cache/`)
    - Do not pre-initialize language servers

### Documentation Updates

21. System MUST update CLAUDE.md managed block to reference MCP tools:
    - Add guidance that MCP tools `lsp` and `mem_search` are available
    - Explain when Claude should use them (edits, searches, refactoring)
    - Document automatic annotation workflow

22. System MUST update AGENTS.md to include MCP tool documentation:
    - Document available MCP tools and their actions
    - Provide examples of natural language triggers
    - Document the two-step workflow: report generation + automatic annotation

23. System MUST update `aur doctor` command to:
    - Detect reduced slash command count (4 instead of 6)
    - Show MCP tools installed and configured
    - Verify LSP package is installed

24. System MUST update README.md:
    - Document MCP tools availability
    - Explain LSP integration benefits
    - List supported languages

25. System MUST create new `docs/02-features/mcp/MCP.md`:
    - Explain what MCP tools do and how they work
    - Document `lsp` and `mem_search` tools with examples
    - Document CODE_QUALITY_REPORT.md output format
    - Document automatic inline annotation workflow
    - Reference existing `docs/02-features/lsp/LSP.md` for LSP details

### Testing

26. System MUST delete tests for removed slash commands:
    - Update test asserting command count (change from 5 to 4)
    - Remove tests for `search` and `get` command templates
    - Update `test_all_expected_commands_present` to expect: plan, tasks, implement, archive

27. System MUST add TDD tests for MCP tools before implementation:
    - Unit tests for `lsp` tool (all three actions)
    - Unit tests for `mem_search` tool with call relationship data
    - Integration tests for MCP server startup
    - Tests for LSP data enrichment in search results
    - Tests for CODE_QUALITY_REPORT.md generation and format

28. System MUST maintain existing LSP package tests:
    - `packages/lsp/tests/test_filters.py` (7 passing tests)
    - Filter accuracy tests for import vs usage distinction

## Non-Goals

1. **CLI commands for LSP** - No `aur lsp` CLI; MCP tools only. CLI without LLM adds no value.
2. **Linting integration** - Do not wrap language linters (use ruff, eslint, clippy directly)
3. **Outgoing call analysis limitations** - "calling" data is best-effort where multilspy supports it
4. **LSP data indexing** - Usage counts must be live; code changes invalidate cached data
5. **New slash commands** - No new slash commands; use MCP tools instead
6. **New LSP function implementations** - Reuse POC code only
7. **Automatic code deletion** - Markers and reports only; human reviews before any deletion
8. **MCP source file modification** - MCP tools are read-only; inline annotations are Claude Edit actions (but automatic, not optional)

## Constraints

- **Existing MCP infrastructure**: Must reuse dormant `configurators/mcp/` code, not create parallel system
- **POC code reuse**: Must integrate `packages/lsp/poc_mcp_server.py` patterns; no new LSP implementations
- **FastMCP framework**: Use `mcp.server.fastmcp` for MCP tool implementation
- **multilspy dependency**: Continue using Microsoft's multilspy for LSP client functionality
- **Mandatory installation**: LSP package must be included in standard Aurora install
- **Read-only MCP**: All MCP `lsp` actions use `readOnlyHint: true`; Claude performs source annotations via Edit tool as automatic follow-up

## Success Metrics

| Metric | Target |
|--------|--------|
| MCP tools implemented | 2 (`lsp`, `mem_search`) |
| Slash commands remaining | 4 (plan, tasks, implement, archive) |
| MCP tool unit tests | >10 |
| LSP action coverage | 100% (deadcode, impact, check) |
| Existing LSP tests passing | 7/7 |
| Claude auto-invocation | MCP used for edits/search/refactor without explicit request |
| Skill/subagent integration | Existing agents can invoke MCP tools autonomously |
| Languages supported | 10 (via multilspy) |
| Automatic annotation | Claude adds inline markers after every code quality report |
