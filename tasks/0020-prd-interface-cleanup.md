# PRD: Aurora Interface Cleanup - Simplify CLI/MCP/Slash Commands

## 1. Introduction/Overview

Aurora currently has three overlapping interfaces (CLI, MCP tools, Slash commands) that expose the same functionality through different entry points. This creates confusion about which interface to use, increases maintenance burden, and violates the single responsibility principle.

This PRD defines a cleanup effort to rationalize these interfaces by assigning each command to its appropriate interface based on purpose: CLI for human terminal use, MCP for structured Claude integration, and Slash for workflow orchestration only.

**Problem Statement:** Developers and agents face decision paralysis when choosing between `aur query`, `aurora_query`, and `/aur:query` for the same operation. Code duplication across three interfaces increases maintenance cost and bug surface area.

**High-Level Goal:** Establish clear interface boundaries where CLI serves humans, MCP serves Claude, and Slash orchestrates multi-step workflows - eliminating redundancy while preserving all working functionality.

## 2. Goals

- Remove redundant command implementations across CLI/MCP/Slash interfaces
- Establish clear interface selection criteria (human terminal vs Claude integration vs workflow orchestration)
- Add missing MCP tools for agent discovery functionality
- Create comprehensive documentation showing all commands, their purposes, and correct usage
- Maintain 100% functional correctness for all retained commands
- Achieve zero breaking changes to working functionality (no users exist to migrate)
- Complete compatibility audit of existing workflows, skills, and documentation

## 3. User Stories

**As a developer using Aurora CLI**, I want to use `aur agents list` in my terminal so that I have a human-readable interface for agent discovery without needing to invoke MCP tools.

**As Claude Code using MCP**, I want to call `aurora_list_agents` so that I can programmatically discover available agents and integrate them into my reasoning without spawning shell processes.

**As an agent orchestrating workflows**, I want to use `/aur:plan` to coordinate multi-step planning operations so that I can follow the proven OpenSpec pattern for complex workflows.

**As a new Aurora contributor**, I want to read clear documentation showing which interface to use for each operation so that I don't waste time implementing redundant commands.

**As a maintainer**, I want a single source of truth for each operation so that bug fixes and improvements don't need to be replicated across multiple interfaces.

**As Claude Code**, I want `aurora_search_agents` to return JSON so that I can parse results programmatically without regex scraping markdown tables.

**As a workflow designer**, I want `/aur:archive` and `/aur:implement` (future) to follow the same orchestration pattern as `/aur:plan` so that I have consistent workflow primitives.

## 4. Functional Requirements

### 4.1 Deletions

**REQ-DEL-1:** The system must remove the `aur query` CLI command completely from `packages/cli/src/aurora_cli/main.py`.

**REQ-DEL-2:** The system must remove the `aurora_stats` MCP tool from `src/aurora/mcp/tools.py` (CLI `aur mem stats` is sufficient).

**REQ-DEL-3:** The system must remove six slash command templates from `packages/cli/src/aurora_cli/templates/commands.py`: `/aur:init`, `/aur:doctor`, `/aur:query`, `/aur:search`, `/aur:agents`, `/aur:index`.

**REQ-DEL-4:** The system must remove all test files associated with deleted commands.

### 4.2 Additions

**REQ-ADD-1:** The system must implement `aurora_list_agents` MCP tool that returns JSON array of all discovered agents with fields: `id`, `title`, `source_path`, `when_to_use`.

**REQ-ADD-2:** The system must implement `aurora_search_agents` MCP tool that accepts a `query` parameter and returns JSON array of matching agents with relevance scoring.

**REQ-ADD-3:** The system must implement `aurora_show_agent` MCP tool that accepts an `agent_id` parameter and returns JSON object with complete agent details including full markdown content.

**REQ-ADD-4:** The system must register all three new MCP tools in `src/aurora/mcp/server.py` with comprehensive tool descriptions that include rich keyword coverage for Claude to match user intent. Each description must contain:
- Primary action keywords (list, show, search, find, discover, browse, retrieve, get, fetch)
- Domain keywords (agent, specialist, expert, role, persona, subagent)
- Context keywords (available, registered, defined, configured, ready, accessible)
- Use case keywords (what, which, who, when, help, assist, guide)

Example descriptions:
- `aurora_list_agents`: "List all available agents and specialists. Shows discovered agents, roles, and personas with their purposes. Use to browse available experts, find what agents exist, or discover which specialists are ready to help."
- `aurora_search_agents`: "Search and find agents by keyword. Discovers relevant specialists based on your query. Use to locate agents for specific tasks, find experts by capability, or match agents to your needs."
- `aurora_show_agent`: "Get complete details for a specific agent. Retrieves full agent definition, instructions, and capabilities. Use to understand what an agent does, read agent prompts, or see detailed agent documentation."

**REQ-ADD-5:** The system must implement unit tests for each new MCP tool covering success cases, error cases, and edge cases.

**REQ-ADD-6:** The system must implement MCP integration tests that verify tools work end-to-end through the MCP protocol.

### 4.3 Retention (No Changes Required)

**REQ-KEEP-1:** The system must retain CLI commands: `aur init`, `aur doctor`, `aur mem index`, `aur mem search`, `aur mem stats`, `aur agents`, `aur plan`.

**REQ-KEEP-2:** The system must retain MCP tools: `aurora_query`, `aurora_search`, `aurora_index`, `aurora_context`, `aurora_related`, `aurora_get`.

**REQ-KEEP-3:** The system must retain slash commands: `/aur:plan`, `/aur:checkpoint`.

### 4.4 Documentation

**REQ-DOC-1:** The system must create a new `docs/INTERFACE_GUIDE.md` document containing a comprehensive table of all commands (current + planned future) with columns: Command Name, Interface Type, Purpose, When To Use, Syntax, Example.

**REQ-DOC-2:** The documentation must include decision criteria for interface selection: "Use CLI for human terminal interaction, MCP for Claude programmatic access, Slash for multi-step workflow orchestration."

**REQ-DOC-3:** The documentation must explain the OpenSpec workflow pattern and why `/aur:plan`, `/aur:archive` (future), `/aur:implement` (future) exist as slash commands.

**REQ-DOC-4:** The system must update `CLAUDE.md` to reference the new interface guide and remove references to deleted slash commands.

**REQ-DOC-5:** The system must update `docs/cli/CLI_USAGE_GUIDE.md` to remove `aur query` documentation.

### 4.5 Compatibility Audit

**REQ-AUDIT-1:** The system must scan all agent definition files (`.claude/agents/*.md`) for references to deleted slash commands and update them.

**REQ-AUDIT-2:** The system must scan all skill files (`.claude/skills/**/*.md`) for references to deleted slash commands and update them.

**REQ-AUDIT-3:** The system must scan all task briefs (`.claude/resources/task-briefs.md`) for references to deleted commands and update them.

**REQ-AUDIT-4:** The system must scan all documentation files (`docs/**/*.md`) for references to deleted commands and update them.

**REQ-AUDIT-5:** The system must update the global CLAUDE.md (`~/.claude/CLAUDE.md` references in comments) to reflect the new command structure.

### 4.6 Implementation Approach

**REQ-IMPL-1:** The system must use Test-Driven Development (TDD) where tests are written before implementation for all new MCP tools.

**REQ-IMPL-2:** The system must reuse existing agent discovery logic from `packages/cli/src/aurora_cli/agent_discovery/` module in the new MCP tools.

**REQ-IMPL-3:** The system must use the same manifest caching strategy for MCP agent tools as the CLI `aur agents` command (simplest approach: shared cache).

**REQ-IMPL-4:** The system must ensure all new MCP tools follow the error handling patterns established in existing tools (`aurora_query`, `aurora_search`).

**REQ-IMPL-5:** The system must run shell integration tests after implementing deletions to verify no runtime errors occur.

## 5. Non-Goals (Out of Scope)

- Implementing `/aur:archive` or `/aur:implement` slash commands (future work)
- Refactoring the agent discovery module internals (only interface changes)
- Changing the MCP protocol version or transport mechanism
- Migrating existing users (product not live, no users to migrate)
- Adding deprecation warnings for deleted commands (immediate removal)
- Performance optimization of agent discovery (unless regressions occur)
- Adding new CLI commands beyond agent-related MCP tools
- Changing the OpenSpec workflow pattern used by `/aur:plan`

## 6. Design Considerations

### 6.1 Interface Selection Criteria

**CLI Interface (Human-Facing):**
- Direct terminal usage by developers
- Human-readable output (tables, formatted text)
- Interactive prompts allowed
- Examples: `aur agents list`, `aur mem stats`

**MCP Interface (Claude-Facing):**
- Programmatic access by Claude Code
- Structured JSON output for parsing
- No user interaction (async tool calls)
- Examples: `aurora_list_agents`, `aurora_query`

**Slash Interface (Workflow Orchestration):**
- Multi-step workflows coordinating multiple operations
- Follows OpenSpec pattern: read state → make decisions → invoke CLI/MCP → write results
- Not simple wrappers (must add orchestration value)
- Examples: `/aur:plan` (coordinates planning workflow), `/aur:checkpoint` (saves session state)

### 6.2 MCP Tool Output Format

All new agent MCP tools return JSON:

```json
// aurora_list_agents
[
  {
    "id": "orchestrator",
    "title": "Master Orchestrator",
    "source_path": "/home/user/.claude/agents/orchestrator.md",
    "when_to_use": "Use for workflow coordination, multi-agent tasks..."
  }
]

// aurora_search_agents
[
  {
    "id": "qa-test-architect",
    "title": "Test Architect & Quality Advisor",
    "relevance_score": 0.92,
    "when_to_use": "Use for comprehensive test architecture review...",
    "source_path": "/home/user/.claude/agents/qa-test-architect.md"
  }
]

// aurora_show_agent
{
  "id": "ux-expert",
  "title": "UX Expert",
  "source_path": "/home/user/.claude/agents/ux-expert.md",
  "when_to_use": "Use for UI/UX design, wireframes...",
  "full_content": "# UX Expert\n\nYou are an expert..."
}
```

### 6.3 Caching Strategy

Use shared manifest cache between CLI and MCP:
- Cache location: `~/.aurora/agent_manifest.json`
- TTL: 5 minutes (matches CLI behavior)
- Refresh: On-demand via `aur agents refresh` or first access after TTL
- Simplest approach: reuse existing `AgentManifest` class from CLI module

## 7. Technical Considerations

### 7.1 Dependencies

- Existing agent discovery module: `aurora_cli.agent_discovery`
- MCP server framework: `src/aurora/mcp/server.py`
- Test utilities: `aurora_testing` package

### 7.2 Integration Points

- CLI commands invoke `aurora_cli.agent_discovery.scanner.scan_agents()`
- MCP tools will import and reuse same scanner module
- Slash commands invoke CLI via subprocess (existing pattern)

### 7.3 Suggested Implementation Order

1. **Phase 1 - Add MCP Tools (TDD):**
   - Write tests for `aurora_list_agents`
   - Implement `aurora_list_agents` using existing scanner
   - Write tests for `aurora_search_agents`
   - Implement `aurora_search_agents` with relevance scoring
   - Write tests for `aurora_show_agent`
   - Implement `aurora_show_agent` with error handling
   - Register tools in MCP server

2. **Phase 2 - Delete Redundant Commands:**
   - Remove `aur query` from CLI (update main.py)
   - Remove `aurora_stats` from MCP tools
   - Remove 6 slash command templates
   - Remove associated test files
   - Run shell integration tests

3. **Phase 3 - Documentation & Audit:**
   - Create `docs/INTERFACE_GUIDE.md` with comprehensive table
   - Update `CLAUDE.md`, `CLI_USAGE_GUIDE.md`
   - Audit and update agent definitions
   - Audit and update skills
   - Audit and update task briefs
   - Audit and update all docs

4. **Phase 4 - Verification:**
   - Run full test suite (`make quality-check`)
   - Manual MCP tool testing via Claude Desktop
   - Verify slash commands still work
   - Verify CLI commands still work

### 7.4 Key Files to Modify

**Deletions:**
- `packages/cli/src/aurora_cli/main.py` (remove query command)
- `packages/cli/src/aurora_cli/templates/commands.py` (remove slash templates)
- `src/aurora/mcp/tools.py` (remove stats tool)
- `tests/unit/cli/test_query.py` (if exists)
- `tests/integration/mcp/test_stats.py` (if exists)

**Additions:**
- `src/aurora/mcp/tools.py` (add 3 agent tools)
- `src/aurora/mcp/server.py` (register new tools)
- `tests/unit/mcp/test_agent_tools.py` (new file)
- `tests/integration/mcp/test_agent_tools_integration.py` (new file)
- `docs/INTERFACE_GUIDE.md` (new file)

**Updates:**
- `CLAUDE.md` (remove deleted slash references)
- `docs/cli/CLI_USAGE_GUIDE.md` (remove query docs)
- All agent/skill/task files (audit for deleted commands)

## 8. Success Metrics

### 8.1 Functional Correctness

**Metric:** All retained commands (CLI/MCP/Slash) produce identical output before and after cleanup.

**Verification Method:**
- Run `aur agents list` before/after, compare output
- Invoke `aurora_query` via MCP before/after, compare JSON
- Execute `/aur:plan` workflow before/after, verify files generated

**Target:** 100% functional parity for retained commands.

### 8.2 Test Coverage

**Metric:** Maintain or improve test coverage percentage.

**Verification Method:**
- Run `pytest --cov=packages --cov=src` before/after
- Compare coverage report percentages

**Target:** Maintain ≥81% coverage (current baseline).

### 8.3 Code Reduction

**Metric:** Lines of code removed from redundant implementations.

**Verification Method:**
- Count lines deleted in CLI/MCP/Slash implementations
- Count lines added for new MCP tools
- Calculate net reduction

**Target:** Net reduction ≥200 lines (indicative of successful deduplication).

### 8.4 Documentation Completeness

**Metric:** Interface guide contains all current + planned commands with complete information.

**Verification Method:**
- Manual review of `INTERFACE_GUIDE.md` table
- Verify all 7 CLI + 9 MCP + 2 Slash commands documented
- Verify 2 future slash commands (`/aur:archive`, `/aur:implement`) documented as "planned"

**Target:** 100% command coverage in documentation.

### 8.5 Zero Regressions

**Metric:** No test failures introduced by changes.

**Verification Method:**
- Run `make quality-check` after each phase
- Ensure 2,369 tests still pass (allowing existing 14 skipped)

**Target:** 0 new test failures, 0 new mypy errors beyond existing 6.

## 9. Open Questions

**Q1:** Should `aurora_search_agents` use fuzzy matching (Levenshtein distance) or simple substring matching for relevance scoring?
- **Recommendation:** Start with simple substring matching in agent metadata (id, title, when_to_use). Add fuzzy matching in future iteration if needed.

**Q2:** What should `aurora_show_agent` return if agent_id doesn't exist?
- **Recommendation:** Return error JSON: `{"error": "Agent not found", "agent_id": "invalid-id"}` matching existing MCP tool error patterns.

**Q3:** Should the interface guide include performance characteristics (e.g., "CLI faster for batch operations, MCP better for single queries")?
- **Recommendation:** No, keep guide focused on functional selection criteria. Performance is implementation detail.

**Q4:** Should we add a `--json` flag to CLI commands for programmatic use cases?
- **Recommendation:** Out of scope. Use MCP tools for programmatic access (that's the interface boundary).

**Q5:** How should we handle the case where slash command templates are removed but agents still reference them?
- **Recommendation:** This is covered by REQ-AUDIT-1. Compatibility audit will find and update all references.

---

## Implementation Checklist

- [ ] Write tests for `aurora_list_agents` MCP tool
- [ ] Implement `aurora_list_agents` reusing agent discovery scanner
- [ ] Write tests for `aurora_search_agents` MCP tool
- [ ] Implement `aurora_search_agents` with substring relevance scoring
- [ ] Write tests for `aurora_show_agent` MCP tool
- [ ] Implement `aurora_show_agent` with error handling
- [ ] Register all 3 tools in MCP server with descriptions
- [ ] Write MCP integration tests for agent tools
- [ ] Remove `aur query` command from CLI main.py
- [ ] Remove `aurora_stats` tool from MCP tools.py
- [ ] Remove 6 slash command templates from commands.py
- [ ] Remove test files for deleted commands
- [ ] Run shell integration tests to verify no runtime errors
- [ ] Create `docs/INTERFACE_GUIDE.md` with comprehensive command table
- [ ] Update `CLAUDE.md` to remove deleted slash references
- [ ] Update `docs/cli/CLI_USAGE_GUIDE.md` to remove query docs
- [ ] Audit all agent files for deleted command references
- [ ] Audit all skill files for deleted command references
- [ ] Audit all task brief files for deleted command references
- [ ] Audit all documentation files for deleted command references
- [ ] Run `make quality-check` and verify all tests pass
- [ ] Manual test MCP tools via Claude Desktop
- [ ] Verify `/aur:plan` and `/aur:checkpoint` still work
- [ ] Verify all retained CLI commands still work

---

**Document Status:** Ready for Implementation
**Created:** 2026-01-05
**Next Step:** Begin Phase 1 - TDD implementation of MCP agent tools
