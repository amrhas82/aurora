# PRD-0024: MCP Tool Deprecation - Progress Tracker

## Status: In Progress (Phases 0-4 Complete)

### Completed Phases

- [x] **Phase 0: Pre-Implementation Setup**
  - [x] Created git baseline tag: `mcp-deprecation-baseline`
  - [x] Branch: `feature/mcp-deprecation`
  - [x] Commit: `1d8de3c`

- [x] **Phase 1: Baseline Audit**
  - [x] Audited all 9 SOAR phase handlers - DO NOT DELETE
  - [x] Verified 239 phase handler tests pass
  - [x] Created docs/ARCHITECTURE.md
  - [x] Created tasks/0024-preservation-checklist.md
  - [x] Created tasks/0024-audit-findings.md
  - [x] Commit: `0d1c08f`

- [x] **Phase 2: Configuration Architecture**
  - [x] Added `mcp_enabled: bool = False` to Config dataclass
  - [x] Added `--enable-mcp` flag to `aur init`
  - [x] Hardcoded MCP to disabled (`if False:`)
  - [x] Commit: `0d1c08f`

- [x] **Phase 3: MCP Tool Removal**
  - [x] Removed tool registrations from src/aurora_mcp/server.py
  - [x] Deprecated aurora_search() in src/aurora_mcp/tools.py
  - [x] Deprecated aurora_get() in src/aurora_mcp/tools.py
  - [x] Updated list_tools() with deprecation message
  - [x] Commit: `0d1c08f`

- [x] **Phase 4: Doctor Command Updates**
  - [x] Commented out MCP FUNCTIONAL section in packages/cli/src/aurora_cli/commands/doctor.py
  - [x] Doctor output no longer shows confusing MCP warnings
  - [x] Commit: `843eb25`

### Remaining Phases

- [ ] **Phase 5: Configurator Permission Updates**
  - [ ] Update AURORA_MCP_PERMISSIONS in packages/cli/src/aurora_cli/configurators/mcp/claude.py
  - [ ] Remove: aurora_query, aurora_search, aurora_get
  - [ ] Keep: aurora_index, aurora_context, aurora_related, aurora_list_agents, aurora_search_agents, aurora_show_agent

- [ ] **Phase 6: Slash Command Enhancements**
  - [ ] Create /aur:implement placeholder in .claude/commands/aur/implement.md
  - [ ] Document CLI commands: aur query, aur soar, aur mem stats

- [ ] **Phase 7: Documentation**
  - [ ] Create docs/MCP_DEPRECATION.md
  - [ ] Create MIGRATION.md
  - [ ] Update inline code comments

- [ ] **Phase 8: Testing**
  - [ ] Verify aur init works without MCP
  - [ ] Verify aur doctor shows clean output
  - [ ] Test /aur:search and /aur:get slash commands
  - [ ] Verify 9 SOAR phase tests still pass

- [ ] **Phase 9: Review and Merge**
  - [ ] Code review
  - [ ] Update CHANGELOG
  - [ ] Merge to main

- [ ] **Phase 10: Rollback Verification**
  - [ ] Test git checkout mcp-deprecation-baseline
  - [ ] Document rollback procedures

## Files Modified

1. packages/cli/src/aurora_cli/config.py
2. packages/cli/src/aurora_cli/commands/init.py
3. src/aurora_mcp/server.py
4. src/aurora_mcp/tools.py
5. packages/cli/src/aurora_cli/commands/doctor.py
6. docs/ARCHITECTURE.md (new)
7. tasks/0024-preservation-checklist.md (new)
8. tasks/0024-audit-findings.md (new)

## Key Preservation

- ✅ All 9 SOAR phase handlers untouched
- ✅ Session cache infrastructure preserved
- ✅ All MCP configurators intact (dormant)
- ✅ Helper methods preserved

## Commits

- `1d8de3c` - Branch preparation
- `0d1c08f` - Phases 0-3 complete
- `843eb25` - Phase 4 complete
