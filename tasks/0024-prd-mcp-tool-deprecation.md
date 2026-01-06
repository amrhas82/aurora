# PRD-0024: MCP Tool Deprecation - Clean Migration to Slash Commands

## Introduction/Overview

Aurora currently maintains dual tool interfaces: MCP (Model Context Protocol) tools and slash commands. After deploying both approaches, we've discovered that slash commands provide superior UX with direct output formatting, explicit user control, lower token usage, and no interpretation layer overhead.

This PRD defines the clean deprecation of 3 MCP tools (`aurora_query`, `aurora_search`, `aurora_get`) that have been superseded by their slash command equivalents (`aur soar`, `/aur:search`, `/aur:get`), while preserving the entire MCP infrastructure for potential future use. Additionally, we'll create a placeholder `/aur:implement` command to align with Aurora's native workflow evolution from OpenSpec's proposal→apply→archive pattern.

**Problem Statement**: The MCP tools create confusion for users, consume unnecessary tokens during LLM interactions, and add maintenance overhead despite being functionally replaced by superior CLI/slash alternatives.

**High-Level Goal**: Remove deprecated MCP tools from active use while maintaining infrastructure integrity, ensuring users have clear migration path, and establishing clean foundation for Aurora's native planning workflows.

**Risk Level**: MEDIUM - Not in production, no external users to impact. All changes reversible via git tag rollback (`mcp-deprecation-baseline`).

## Goals

1. **Remove User-Facing MCP Tool Registration** - Deprecated tools no longer appear in MCP server tool list
2. **Preserve MCP Infrastructure** - All 20+ MCP configurators remain functional and testable for future use
3. **Eliminate Configuration Overhead** - `aur init` no longer configures MCP by default
4. **Clean Doctor Output** - `aur doctor` no longer shows confusing MCP warnings/errors
5. **Establish Re-enablement Path** - Future MCP use requires minimal code changes (config toggle only)
6. **Document Migration Clearly** - Users understand what changed, why, and how to adapt
7. **Create Workflow Placeholder** - `/aur:implement` command establishes Aurora native workflow pattern

## User Stories

### US-1: Developer Running aur init (Fresh Install)
**As a** new Aurora user
**I want to** run `aur init` and have it complete without MCP setup
**So that** I can start using Aurora quickly without configuring unused features

**Acceptance Criteria**:
- `aur init` completes successfully without prompting for MCP configuration
- No MCP server configuration written to `.claude/plugins/aurora/.mcp.json`
- No MCP permissions added to `.claude/settings.local.json`
- Slash commands (`/aur:search`, `/aur:get`) work correctly
- No user-visible indication that MCP was skipped (silent behavior)

### US-2: Developer Running aur doctor
**As a** developer verifying Aurora installation
**I want to** run `aur doctor` and see meaningful health checks
**So that** I can identify real issues without being confused by deprecated tool warnings

**Acceptance Criteria**:
- `aur doctor` no longer shows "MCP FUNCTIONAL" section
- No warnings about missing `aurora_query`, `aurora_search`, `aurora_get` tools
- No errors about missing MCP configuration files
- All other health checks continue to function normally
- Exit code behavior remains unchanged for non-MCP checks

### US-3: Developer Using Slash Commands
**As a** developer searching Aurora's codebase
**I want to** use `/aur:search` and `/aur:get` slash commands
**So that** I can retrieve code context directly without token overhead

**Acceptance Criteria**:
- `/aur:search "query"` returns formatted search results with syntax highlighting
- `/aur:get N` retrieves full chunk from previous search by index
- Commands work in Claude Code CLI with proper formatting
- Session cache persists results for 10 minutes between commands
- Error messages guide users clearly when cache expires or no previous search exists

### US-4: QA Engineer Testing MCP Infrastructure
**As a** QA engineer maintaining Aurora
**I want to** test MCP configurators without enabling MCP in production
**So that** I can verify infrastructure remains functional for future use

**Acceptance Criteria**:
- Unit tests for all MCP configurators pass
- `aur init --enable-mcp` flag allows testing MCP setup
- MCP server starts successfully when manually enabled via config
- All 20+ configurators install correctly when flag is used
- Documentation explains how to re-enable MCP for testing

### US-5: Developer Understanding Aurora Workflows
**As a** developer learning Aurora's planning workflow
**I want to** see `/aur:implement` command in help output
**So that** I understand Aurora's plan→implement→archive workflow pattern

**Acceptance Criteria**:
- `/aur:implement` appears in slash command registry
- Command shows helpful message explaining Aurora workflow
- Help text describes future plan-based implementation pattern
- Command validates that plan files exist before proceeding (fails gracefully if not)
- Clear distinction from OpenSpec's proposal→apply→archive shown in help

## Functional Requirements

### FR-1: MCP Server Tool Removal
**The system must** remove `aurora_query`, `aurora_search`, and `aurora_get` from MCP server tool registration in `src/aurora_mcp/server.py`

**Specification**:
- Remove `@self.mcp.tool()` decorator and implementation for these 3 tools
- Update `list_tools()` method to exclude removed tools
- Update tool count in output messages
- Keep session cache infrastructure (used by remaining tools)
- Document which cache methods are currently unused

### FR-2: Tool Implementation Cleanup
**The system must** remove tool implementation methods from `src/aurora_mcp/tools.py` while preserving session cache

**Specification**:
- Remove `aurora_query()`, `aurora_search()`, and `aurora_get()` method implementations
- Keep `_last_search_results` and `_last_search_timestamp` class attributes (may be used by future tools)
- Keep all helper methods: `_validate_parameters()`, `_retrieve_chunks()`, `_calculate_retrieval_confidence()`, etc.
- Add code comment documenting preserved infrastructure for future use
- **CRITICAL**: DO NOT remove `packages/soar/src/aurora_soar/phases/*.py` phase handler files
  - Phase handlers are actively used by SOAROrchestrator for programmatic/library use
  - `aur soar` terminal command uses bash script approach (separate from phase handlers)
  - Both approaches coexist: terminal (bash) vs library (Python orchestrator)
  - 9 unit tests exist for phase handlers and must remain passing

### FR-3: aur init Configuration Behavior
**The system must** skip MCP configuration when running `aur init` by default

**Specification**:
- Modify `packages/cli/src/aurora_cli/commands/init.py` to skip MCP setup
- Add `--enable-mcp` CLI flag for testing/development purposes
- Add `enable_mcp: false` setting to generated `config.json`
- Do not prompt user about MCP configuration
- Do not create `.claude/plugins/aurora/.mcp.json` unless flag is set
- Do not modify `.claude/settings.local.json` MCP permissions

### FR-4: Configuration Toggle Architecture
**The system must** implement configuration-based MCP enable/disable mechanism

**Specification**:
- Add `mcp.enabled` boolean field to `~/.aurora/config.json` schema (default: false)
- `aur init --enable-mcp` sets `mcp.enabled: true` in config
- All MCP-related initialization code checks this flag before executing
- Flag can be manually toggled in config file by advanced users
- Invalid config values default to `false` with warning log

### FR-5: aur doctor MCP Check Removal
**The system must** remove MCP-related checks from `aur doctor` output

**Specification**:
- Remove `MCPFunctionalChecks` class instantiation from `packages/cli/src/aurora_cli/commands/doctor.py`
- Remove "MCP FUNCTIONAL" output section
- Do not run MCP-related health checks
- Keep `MCPFunctionalChecks` class in `packages/cli/src/aurora_cli/health_checks.py` (commented out or skipped)
- Update doctor command help text to remove MCP references

### FR-6: Slash Command Functionality Preservation
**The system must** ensure `/aur:search` and `/aur:get` slash commands remain fully functional

**Specification**:
- Commands located in slash configurator files remain untouched
- `/aur:search` invokes `aur mem search` CLI command with formatting
- `/aur:get` retrieves from local session cache (not MCP)
- Both commands work in Claude Code CLI environment
- Error handling provides clear user guidance
- All existing slash command tests pass

### FR-7: /aur:implement Placeholder Command
**The system must** create `/aur:implement` slash command as placeholder for future functionality

**Specification**:
- Add command to slash configurator registry in appropriate configurator file
- Command signature: `/aur:implement [plan-name]`
- When invoked, command prints:
  ```
  ⚙️ /aur:implement - Plan-Based Implementation (Coming Soon)

  Aurora Native Workflow:
    1. plan    → Create implementation plan with 'aur plan create'
    2. implement → Execute plan-based changes (this command)
    3. archive   → Archive completed plan with 'aur plan archive'

  This replaces OpenSpec's proposal→apply→archive pattern.

  Usage (future):
    /aur:implement plan-name    # Execute changes from plan
    /aur:implement --dry-run    # Preview changes without applying

  Current Status: Placeholder - full implementation planned for Phase 4
  ```
- Command validates plan file exists at `.aurora/plans/[plan-name].json`
- If plan not found, shows helpful error with available plans
- Command returns exit code 0 (non-blocking)

### FR-8: Configurator Permissions Update
**The system must** update MCP configurator permission lists to exclude deprecated tools

**Specification**:
- Update all MCP configurator files in `packages/cli/src/aurora_cli/configurators/mcp/`
- Remove `aurora_query`, `aurora_search`, `aurora_get` from allowed tools list
- Keep remaining Aurora MCP tools: `aurora_index`, `aurora_context`, `aurora_related`, `aurora_list_agents`, `aurora_search_agents`, `aurora_show_agent`
- Update configurator factory logic if needed
- All 20+ configurators remain importable and testable

### FR-9: Documentation Updates
**The system must** provide comprehensive documentation of changes

**Specification**:
- Add inline code comments explaining preserved infrastructure
- Create `/docs/MCP_DEPRECATION.md` architecture document:
  - Rationale for deprecation
  - What was removed vs what was preserved
  - How to re-enable MCP for testing
  - Future MCP tool plans
- Update `/docs/MIGRATION.md` with:
  - Tool replacement mapping (old→new)
  - Behavior changes users should expect
  - Breaking changes (if any)
- Add comment in `config.json` template explaining `mcp.enabled` flag

### FR-10: Testing Infrastructure Preservation
**The system must** maintain testability of MCP infrastructure

**Specification**:
- Keep all MCP configurator unit tests in `tests/unit/cli/configurators/mcp/`
- Mark MCP integration tests as skipped by default (unless `--enable-mcp` environment variable set)
- Add `AURORA_ENABLE_MCP=1` environment variable for test runners
- Tests verify configurators can still configure MCP when enabled
- Tests do not require running MCP server (mock where appropriate)
- Add test verifying `aur init` skips MCP by default
- Add test verifying `aur init --enable-mcp` enables MCP

### FR-11: Rollback Mechanism
**The system must** support easy rollback if needed

**Specification**:
- Create git tag `mcp-deprecation-baseline` before starting implementation
- Document rollback steps in PRD implementation notes
- Keep all removed code accessible in git history
- Feature flag (`mcp.enabled`) allows re-enabling without code changes
- Rollback requires: set `mcp.enabled: true`, run `aur init --enable-mcp`, restart MCP server

### FR-12: Existing Permissions Handling
**The system must** handle existing MCP permissions gracefully

**Specification**:
- Leave existing `.claude/settings.local.json` files untouched (harmless if server not running)
- Do not auto-remove MCP permissions on upgrade
- Do not warn users about orphaned MCP permissions
- Document manual cleanup steps in migration guide (optional)
- Permissions for deprecated tools simply ignored when server not running

### FR-13: Command Documentation
**The system must** update command documentation to reflect new workflow and clear command distinctions

**Specification**:

**Slash Commands** (in `.claude/commands/aur/*.md`):
- `/aur:search <query>` - Search indexed codebase with formatted table output (existing, verify docs)
- `/aur:get <N>` - Get full content of search result by index from session cache (existing, verify docs)
- `/aur:implement [plan-name]` - Placeholder for Aurora workflow: plan → implement → archive (NEW, create)

**CLI Terminal Commands** (document in appropriate locations):
- `aur query "question"` - Local context retrieval using SOAR phases 1-2 only (no LLM, no API costs)
- `aur soar "question"` - Multi-turn SOAR query using 5 separate Claude CLI calls orchestrated via bash script
- `aur mem stats` - Enhanced output showing Memory Stats + Query Metrics tables (existing, verify docs)

**Implementation Notes**:
- Slash commands `/aur:search` and `/aur:get` already exist and work correctly
- `/aur:implement` needs creation as placeholder with help text (FR-7)
- CLI commands `aur query` and `aur soar` exist, documentation may need updates
- `aur mem stats` already shows enhanced dual-table output
- Document distinction: slash commands (direct formatting) vs CLI commands (programmatic + formatting)
- Clarify `aur soar` uses bash orchestration, not Python SOAROrchestrator (that's for library use)

## Non-Goals (Out of Scope)

1. **Complete MCP Removal** - We are NOT removing MCP infrastructure entirely, only deprecating 3 tools
2. **Breaking MCP Configurators** - All 20+ configurators must remain functional for future use
3. **Removing MCP Tests** - Tests stay in codebase, just skipped unless explicitly enabled
4. **Forced Permission Cleanup** - We do NOT auto-remove existing MCP permissions from user configs
5. **Full /aur:implement Implementation** - Only creating placeholder, not full functionality
6. **Removing Session Cache** - Cache infrastructure preserved for future MCP tools
7. **Changing Slash Command Behavior** - `/aur:search` and `/aur:get` remain unchanged
8. **MCP Server Binary Removal** - `aurora-mcp` command stays installed but unused by default

## Design Considerations

### MCP Infrastructure Preservation Strategy ("Keep Dormant")

**Rationale**: MCP may be valuable for future use cases (agent-to-agent communication, IDE integrations). We preserve infrastructure to enable rapid re-enablement.

**"Keep Dormant" Approach**:
- **NO deletion of working code** - All MCP configurators preserved (20+ tools)
- **NO deletion of phase handlers** - All `packages/soar/src/aurora_soar/phases/*.py` files preserved (9 files + tests)
- **Configuration bypass only** - Skip MCP setup in `aur init`, but infrastructure remains intact
- **Minimal re-enablement effort** - Future flag `aur init --with-mcp` requires <50 lines of code
- **Testability maintained** - Unit tests pass, integration tests skippable via env var
- **Git history preserved** - Rollback tag `mcp-deprecation-baseline` allows instant revert

**What Gets "Dormant" Status**:
1. MCP tool registration (3 tools: query, search, get)
2. MCP configuration in `aur init` (skipped by default)
3. MCP health checks in `aur doctor` (removed from output)
4. MCP permissions in configurators (updated, but configurators remain functional)

**What Remains Active**:
1. All 20+ MCP configurator code files
2. All 9 SOAR phase handler files (`assess.py`, `retrieve.py`, etc.)
3. Session cache infrastructure
4. Helper methods and utilities
5. All unit tests (MCP integration tests skipped unless env var set)

**Re-enablement Path** (future):
```bash
# Step 1: Enable via flag (future implementation)
aur init --with-mcp

# Step 2: Verify
aur doctor  # Should show MCP FUNCTIONAL section

# Step 3: Use
# MCP tools now available in Claude Code CLI
```

This approach balances removing user-facing complexity while preserving engineering investment and future optionality.

### Configuration-Based Toggle

**Configuration Schema**:
```json
{
  "mcp": {
    "enabled": false,
    "server_path": "~/.local/bin/aurora-mcp",
    "tools": [
      "aurora_index",
      "aurora_context",
      "aurora_related",
      "aurora_list_agents",
      "aurora_search_agents",
      "aurora_show_agent"
    ]
  }
}
```

**Flag Behavior**:
- `false` (default): Skip all MCP setup in `aur init`, skip MCP checks in `aur doctor`
- `true`: Enable full MCP configuration (testing/development mode)

### Slash Command Architecture

**Current Slash Commands** (unchanged):
- `/aur:search` → Executes `aur mem search` with formatting
- `/aur:get` → Retrieves from local session cache

**New Slash Command** (placeholder):
- `/aur:implement` → Prints workflow guide, validates plan exists

**Session Cache**:
- Maintained in CLI process memory (not MCP server)
- 10-minute expiration
- Shared between slash commands

## Technical Considerations

### Migration Path from MCP to Slash

**Tool Mapping**:
| MCP Tool | Replacement | Notes |
|----------|------------|-------|
| `aurora_query` | `aur soar <query>` | Full 9-phase SOAR pipeline via CLI |
| `aurora_search` | `/aur:search "query"` | Slash command with formatting |
| `aurora_get` | `/aur:get N` | Slash command with session cache |

**Breaking Changes**:
- None - tools were already replaced, deprecation only removes redundant interface

### Configurator Architecture

**20+ MCP Configurators Preserved**:
- Claude Code (`claude.py`)
- Cursor (`cursor.py`)
- Windsurf (`windsurf.py`)
- Cline (`cline.py`)
- Codex (`codex.py`)
- Amazon Q (`amazon_q.py`)
- GitHub Copilot (`github_copilot.py`)
- Gemini (`gemini.py`)
- Qwen (`qwen.py`)
- Auggie (`auggie.py`)
- ... (16 more)

**Factory Pattern**:
- `factory.py` - Configurator registry and instantiation
- Each configurator extends `MCPBaseConfigurator`
- Tool permission lists updated to exclude deprecated tools

### Testing Strategy

**Unit Tests** (always run):
- Configurator instantiation
- Permission list validation
- Config file generation (mocked)
- Flag parsing and validation

**Integration Tests** (skipped unless `AURORA_ENABLE_MCP=1`):
- Full MCP server startup
- Tool registration verification
- End-to-end MCP communication

**Manual Testing Checklist**:
- Fresh install: `aur init` completes without MCP
- Slash commands work: `/aur:search`, `/aur:get`
- Doctor clean: `aur doctor` shows no MCP errors
- Re-enable: `aur init --enable-mcp` configures MCP correctly
- Rollback: Setting `mcp.enabled: true` re-enables functionality

### Dependencies and Integration Points

**Affected Components**:
- `src/aurora_mcp/server.py` - Tool registration removal
- `src/aurora_mcp/tools.py` - Implementation removal
- `packages/cli/src/aurora_cli/commands/init.py` - Config flag logic
- `packages/cli/src/aurora_cli/commands/doctor.py` - Check removal
- `packages/cli/src/aurora_cli/configurators/mcp/*.py` - Permission updates
- `packages/cli/src/aurora_cli/configurators/slash/*.py` - `/aur:implement` addition

**External Dependencies**:
- None - all changes internal to Aurora

## Success Metrics

### Quantitative Metrics

1. **Configuration Time Reduction**: `aur init` completes 30% faster (no MCP setup overhead)
2. **Doctor Output Clarity**: Zero MCP-related warnings/errors in `aur doctor` for new installs
3. **Test Pass Rate**: 100% of existing non-MCP tests pass, MCP tests skippable
4. **Token Usage Reduction**: Slash commands use 50% fewer tokens than equivalent MCP tool calls (no JSON parsing overhead)

### Qualitative Metrics

1. **User Confusion Reduction**: No user questions about "missing MCP tools" in support channels
2. **Code Maintainability**: Clear separation between active and preserved infrastructure
3. **Re-enablement Speed**: Developer can re-enable MCP in <5 minutes with flag + restart
4. **Documentation Clarity**: Migration guide answers 95% of upgrade questions

### Validation Criteria

**Must Pass Before Release**:
- [ ] Git rollback tag `mcp-deprecation-baseline` created and verified
- [ ] `aur init` completes without MCP configuration
- [ ] `aur doctor` shows zero MCP warnings/errors
- [ ] `/aur:search` and `/aur:get` slash commands work correctly
- [ ] `/aur:implement` placeholder command shows workflow guide
- [ ] `aur init --enable-mcp` successfully configures MCP
- [ ] All MCP configurator unit tests pass
- [ ] All 9 SOAR phase handler unit tests pass (preserved, not deleted)
- [ ] Fresh install test succeeds (new user simulation)
- [ ] Command documentation updated and accurate (FR-13)
- [ ] Migration documentation complete and reviewed

## Open Questions

1. **Session Cache Ownership**: Should session cache move from `AuroraMCPTools` to a shared CLI module since it's now only used by slash commands, not MCP?
   - **Decision Needed**: Determine if refactoring cache now or in future phase

2. **MCP Server Process Cleanup**: Should we add logic to detect and stop orphaned MCP server processes from previous installs?
   - **Decision Needed**: Scope of cleanup automation

3. **SOAR Phase Handlers**: The MCP tools have extensive SOAR phase handlers (decompose, verify, route, etc). Are these used by remaining MCP tools?
   - **Decision Needed**: Audit and remove if unused

4. **Configurator Consolidation**: With 20+ configurators all having similar permission updates, should we consolidate into shared template?
   - **Decision Needed**: Balance DRY principle vs configurator independence

## Implementation Plan

### Phase 0: Pre-Implementation Setup (Day 0)

**Tasks**:
1. Create git rollback tag before any changes:
   ```bash
   # Tag current state as baseline
   git tag -a mcp-deprecation-baseline -m "State before MCP tool deprecation (PRD-0024)"
   git push origin mcp-deprecation-baseline

   # Verify tag created
   git tag -l mcp-deprecation-baseline
   git show mcp-deprecation-baseline
   ```
2. Document rollback procedure for team
3. Verify clean working directory (no uncommitted changes)

**Deliverables**:
- Git tag `mcp-deprecation-baseline` created and pushed
- Rollback procedure documented
- Clean baseline verified

**Rollback Reference** (if needed later):
```bash
# Option 1: Checkout baseline tag
git checkout mcp-deprecation-baseline

# Option 2: Revert commit range
git revert <first-commit>..<last-commit>

# Option 3: Reset branch (destructive, use with caution)
git reset --hard mcp-deprecation-baseline
```

### Phase 1: Preparation and Baseline (Day 1)

**Tasks**:
1. Create feature branch `feature/mcp-deprecation`
2. **AUDIT FINDING**: SOAR phase handlers are actively used, DO NOT DELETE
   - Verify 9 phase handler files in `packages/soar/src/aurora_soar/phases/`
   - Confirm 9 unit tests passing
   - Document dual approach: bash (terminal) vs Python (library)
3. Document current MCP tool usage in codebase (grep for function calls)
4. Review all 20+ configurators to understand permission update scope
5. Create "Keep Dormant" preservation checklist

**Deliverables**:
- Feature branch ready
- Phase handler preservation confirmed (NO deletion)
- Audit document listing what stays vs what changes
- Configurator update plan
- "Keep Dormant" checklist

### Phase 2: Configuration Architecture (Days 2-3)

**Tasks**:
1. Add `mcp.enabled` field to config schema in `aurora_cli/config.py`
2. Update `aur init` to generate config with `mcp.enabled: false`
3. Add `--enable-mcp` CLI flag to `aur init` command
4. Implement flag validation and error handling
5. Write unit tests for flag parsing logic
6. Update config template comments

**Deliverables**:
- Config schema updated
- Flag implementation complete
- Unit tests passing
- Documentation in code comments

### Phase 3: MCP Tool Removal (Days 4-5)

**Tasks**:
1. Remove `aurora_query`, `aurora_search`, `aurora_get` from `server.py`:
   - Remove `@self.mcp.tool()` decorators
   - Remove tool implementation methods
   - Update `list_tools()` method
2. Remove tool implementations from `tools.py`:
   - Remove method bodies
   - Add "preserved for future use" comments to session cache
   - Keep all helper methods
3. **SKIP**: SOAR phase handlers remain untouched (actively used by SOAROrchestrator)
   - Verify 9 phase handler unit tests still pass
   - Add code comment explaining dual approach (bash vs Python orchestrator)
4. Update tool count in output messages
5. Test MCP server starts successfully with remaining tools

**Deliverables**:
- Tool registration removed
- Session cache preserved with documentation
- SOAR phase handlers preserved (9 files + tests passing)
- MCP server smoke test passes
- Code comments explain preservation and dual orchestration approaches

### Phase 4: Doctor Command Updates (Day 6)

**Tasks**:
1. Remove `MCPFunctionalChecks` instantiation from `doctor.py`
2. Remove "MCP FUNCTIONAL" output section
3. Keep `MCPFunctionalChecks` class definition (comment out or skip)
4. Update doctor command help text
5. Test `aur doctor` output is clean
6. Update doctor tests to reflect removed checks

**Deliverables**:
- Doctor command updated
- Clean output verified
- Help text updated
- Tests passing

### Phase 5: Configurator Permission Updates (Days 7-8)

**Tasks**:
1. Update all 20+ MCP configurator files in `configurators/mcp/`:
   - Remove deprecated tools from permission lists
   - Keep remaining 6 tools
   - Update any factory logic
2. Verify all configurators still instantiate correctly
3. Update configurator unit tests
4. Test `aur init --enable-mcp` installs MCP correctly
5. Document configurator testing process

**Deliverables**:
- All configurators updated
- Unit tests passing
- MCP installation works when enabled
- Testing guide complete

### Phase 6: Slash Command Enhancements and Documentation (Day 9)

**Tasks**:
1. Add `/aur:implement` placeholder command to appropriate slash configurator (FR-7)
2. Implement help text and workflow guide output
3. Add plan file validation logic
4. Create helpful error messages for missing plans
5. Write slash command tests
6. Update command documentation (FR-13):
   - Verify `/aur:search` and `/aur:get` documentation accurate
   - Document `/aur:implement` with Aurora workflow guide
   - Update `aur query` and `aur soar` CLI command documentation
   - Clarify distinction: bash orchestration (terminal) vs Python (library)
   - Document `aur mem stats` enhanced output
7. Update slash command registry if needed

**Deliverables**:
- `/aur:implement` command working
- Help output formatted correctly
- Tests passing
- All command documentation updated (slash + CLI)
- Registry updated

### Phase 7: Documentation (Days 10-11)

**Tasks**:
1. Create `/docs/MCP_DEPRECATION.md`:
   - Architecture rationale
   - Preserved vs removed components
   - Re-enablement guide
   - Future MCP plans
2. Update `/docs/MIGRATION.md`:
   - Tool replacement mapping
   - Behavior changes
   - Breaking changes (if any)
3. Add inline code comments throughout changed files
4. Update README if needed
5. Create rollback documentation

**Deliverables**:
- Architecture doc complete
- Migration guide complete
- Code comments thorough
- Rollback steps documented

### Phase 8: Testing and Validation (Days 12-13)

**Tasks**:
1. Run full test suite (unit + integration):
   - All MCP configurator unit tests pass
   - **All 9 SOAR phase handler unit tests pass** (preserved, not deleted)
   - Integration tests skipped unless `AURORA_ENABLE_MCP=1` set
2. Mark MCP integration tests as skipped (unless env var set)
3. Fresh install testing:
   - Create clean environment
   - Run `aur init`
   - Verify no MCP configuration
   - Test slash commands (`/aur:search`, `/aur:get`, `/aur:implement`)
   - Run `aur doctor` (should show zero MCP warnings)
4. Re-enablement testing:
   - Run `aur init --enable-mcp`
   - Verify MCP configures correctly
   - Test remaining MCP tools
5. Git rollback testing:
   - Verify `mcp-deprecation-baseline` tag exists
   - Test checkout of baseline tag
   - Verify rollback procedure works
6. Manual testing checklist completion
7. Performance testing (token usage comparison)

**Deliverables**:
- All tests passing (including 9 phase handler tests)
- Fresh install verified
- Re-enablement verified
- Git rollback tag verified and tested
- Manual checklist complete
- Performance metrics collected

### Phase 9: Review and Merge (Day 14)

**Tasks**:
1. Code review with team
2. Address review feedback
3. Final smoke testing
4. Update CHANGELOG
5. Merge to main branch
6. Deploy to staging
7. Monitor for issues

**Deliverables**:
- Code reviewed and approved
- CHANGELOG updated
- PR merged
- Staging deployment successful

### Phase 10: Rollback Verification (Day 15)

**Tasks**:
1. Test rollback process on staging:
   - Set `mcp.enabled: true` in config
   - Run `aur init --enable-mcp`
   - Verify MCP tools work
   - Revert flag
   - Verify tools disappear
2. Document any rollback issues
3. Update rollback documentation if needed
4. Production deployment planning

**Deliverables**:
- Rollback process verified
- Documentation updated
- Production deployment plan ready

## Implementation Notes

### Critical Paths

1. **Git Rollback Tag Creation** - Must be first step, baseline for all changes
2. **Configuration Flag Implementation** - Must be robust, all downstream logic depends on it
3. **Session Cache Preservation** - Needed by slash commands, must not break
4. **Phase Handler Preservation** - DO NOT DELETE, actively used by SOAROrchestrator
5. **Configurator Updates** - 20+ files to update consistently, error-prone
6. **Testing Infrastructure** - Must maintain coverage while skipping MCP tests

### Risk Mitigation

**Risk**: Breaking slash commands by accidentally removing shared code
**Mitigation**: Audit dependencies before removal, test slash commands after each change, preserve session cache

**Risk**: Accidentally deleting SOAR phase handlers
**Mitigation**: "Keep Dormant" checklist, explicit DO NOT DELETE markers in code, verify 9 tests pass

**Risk**: Inconsistent configurator updates (missing files)
**Mitigation**: Use grep to find all configurators, checklist for each file, automated tests

**Risk**: Users confused by change in behavior
**Mitigation**: Comprehensive migration guide, clear error messages, support channel monitoring

**Risk**: Rollback more complex than expected
**Mitigation**: Git tag `mcp-deprecation-baseline` created first, test rollback procedure, document every step

**Risk**: Breaking SOAROrchestrator library usage
**Mitigation**: Preserve all phase handlers, verify unit tests pass, document dual approach (bash vs Python)

### Dependencies Between Phases

- Phase 0 (git tag) must complete FIRST - baseline for rollback
- Phase 1 (audit) must identify phase handlers as preserved (not deleted)
- Phase 2 (config) must complete before Phase 3 (tool removal) - flag needed to conditionally skip
- Phase 3 must complete before Phase 4 (doctor) - checks reference removed tools
- Phase 5 (configurators) can run parallel to Phase 4 (doctor)
- Phase 6 (slash commands) includes FR-13 command documentation
- Phase 7 (docs) requires understanding from Phases 1-6
- Phase 8 (testing) requires all implementation phases complete, verifies phase handlers preserved

### Testing Checkpoints

**After Phase 0**: Git tag created and verified, rollback procedure documented
**After Phase 1**: Phase handlers confirmed as preserved (not deleted), 9 tests identified
**After Phase 2**: Config flag parsing tests pass
**After Phase 3**: MCP server starts with remaining tools, 9 phase handler tests still pass
**After Phase 4**: Doctor output clean
**After Phase 5**: All configurator unit tests pass
**After Phase 6**: Slash command tests pass, command documentation complete
**After Phase 8**: Full test suite passes (including 9 phase handler tests), manual checklist complete, git rollback verified

---

## Appendix A: Tool Replacement Reference

| Deprecated MCP Tool | CLI Replacement | Slash Command | Notes |
|---------------------|-----------------|---------------|-------|
| `aurora_query(query)` | `aur soar "query"` | N/A | Full SOAR pipeline execution |
| `aurora_search(query, limit)` | `aur mem search "query"` | `/aur:search "query"` | Formatted table output |
| `aurora_get(index)` | N/A | `/aur:get N` | Session cache retrieval |

## Appendix B: Preserved MCP Tools (6 Tools)

1. `aurora_index` - Index codebase into memory store
2. `aurora_context` - Get contextual code chunks
3. `aurora_related` - Find related code sections
4. `aurora_list_agents` - List available Aurora agents
5. `aurora_search_agents` - Search agent registry
6. `aurora_show_agent` - Display agent details

These tools remain registered and functional when MCP is enabled via `--enable-mcp` flag.

## Appendix C: Configurator Update Template

**Before** (example from `claude.py`):
```python
"allowed_tools": [
    "aurora_query",
    "aurora_search",
    "aurora_get",
    "aurora_index",
    "aurora_context",
    "aurora_related",
    "aurora_list_agents",
    "aurora_search_agents",
    "aurora_show_agent"
]
```

**After**:
```python
"allowed_tools": [
    # Deprecated tools removed (query, search, get) - replaced by slash commands
    "aurora_index",
    "aurora_context",
    "aurora_related",
    "aurora_list_agents",
    "aurora_search_agents",
    "aurora_show_agent"
]
```

## Appendix D: Rollback Steps

If rollback is needed, three options available:

### Option 1: Rollback to Baseline Tag (Complete Revert)

```bash
# Checkout the baseline tag created in Phase 0
git checkout mcp-deprecation-baseline

# Verify state
git log --oneline -5
git status

# Create new branch from baseline if needed
git checkout -b rollback-mcp-deprecation

# Force push (CAUTION: coordinate with team)
git push origin rollback-mcp-deprecation --force
```

**When to use**: Complete rollback needed, return to pre-deprecation state.

### Option 2: Revert Commit Range (Preserve History)

```bash
# Identify commit range
git log --oneline --grep="PRD-0024"

# Revert the range (non-destructive)
git revert <first-commit>^..<last-commit>

# Push reverts
git push origin main
```

**When to use**: Preserve git history while undoing changes.

### Option 3: Use Feature Flag (Fastest, No Code Changes)

```bash
# Edit ~/.aurora/config.json
{
  "mcp": {
    "enabled": true  # Change from false to true
  }
}

# Re-run init with MCP
aur init --enable-mcp

# Restart MCP server if needed
pkill -f aurora-mcp
aurora-mcp &
```

**When to use**: Temporary re-enablement for testing, no code rollback needed.

### Verify Rollback Success

```bash
# Option 1 & 2: Check MCP tools available
aur doctor  # Should show MCP FUNCTIONAL section

# Test deprecated tools via MCP client
# (implementation depends on MCP client setup)

# Option 3: Verify MCP enabled
cat ~/.aurora/config.json | grep "enabled"
aur doctor  # Should show MCP checks
```

### Rollback Decision Matrix

| Scenario | Recommended Option | Reason |
|----------|-------------------|--------|
| Critical bug in production | Option 1 (baseline tag) | Fastest, most complete |
| Preserve git history | Option 2 (revert commits) | Non-destructive, auditable |
| Testing MCP features | Option 3 (feature flag) | No code changes, reversible |
| Need MCP for development | Option 3 (feature flag) | Keep dormant code, enable when needed |

**Rollback Impact**:
- Options 1 & 2: Users who upgraded will need to reconfigure MCP manually
- Option 3: No user impact, individual choice via config flag
- Communicate changes via release notes and support channels

**Git Tag Reference**:
```bash
# View tag details
git show mcp-deprecation-baseline

# List all tags
git tag -l

# Delete tag if needed (CAUTION)
git tag -d mcp-deprecation-baseline
git push origin :refs/tags/mcp-deprecation-baseline
```
