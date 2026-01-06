# PRD-0024: "Keep Dormant" Preservation Checklist

## Purpose

This checklist ensures critical infrastructure is preserved during MCP tool deprecation. All items listed here must remain functional and untouched except for comment updates or permission list adjustments.

## Preservation Status Legend

- ✅ **PRESERVED** - Must remain functional and untouched
- ⚠️ **MODIFIED** - Updated but infrastructure preserved
- ❌ **REMOVED** - Deleted as part of deprecation

---

## 1. SOAR Phase Handlers (CRITICAL - DO NOT DELETE)

All phase handlers serve Python `SOAROrchestrator` library use case.

| File | Status | Reason for Preservation |
|------|--------|------------------------|
| `packages/soar/src/aurora_soar/phases/assess.py` | ✅ PRESERVED | Phase 1: Complexity Assessment - used by SOAROrchestrator |
| `packages/soar/src/aurora_soar/phases/retrieve.py` | ✅ PRESERVED | Phase 2: Context Retrieval - used by SOAROrchestrator |
| `packages/soar/src/aurora_soar/phases/decompose.py` | ✅ PRESERVED | Phase 3: Query Decomposition - used by SOAROrchestrator |
| `packages/soar/src/aurora_soar/phases/verify.py` | ✅ PRESERVED | Phase 4: Decomposition Verification - used by SOAROrchestrator |
| `packages/soar/src/aurora_soar/phases/route.py` | ✅ PRESERVED | Phase 5: Agent Routing - used by SOAROrchestrator |
| `packages/soar/src/aurora_soar/phases/collect.py` | ✅ PRESERVED | Phase 6: Agent Execution - used by SOAROrchestrator |
| `packages/soar/src/aurora_soar/phases/synthesize.py` | ✅ PRESERVED | Phase 7: Result Synthesis - used by SOAROrchestrator |
| `packages/soar/src/aurora_soar/phases/record.py` | ✅ PRESERVED | Phase 8: ACT-R Pattern Caching - used by SOAROrchestrator |
| `packages/soar/src/aurora_soar/phases/respond.py` | ✅ PRESERVED | Phase 9: Response Formatting - used by SOAROrchestrator |

**Total**: 9 phase handler files preserved

---

## 2. MCP Configurator Infrastructure

All MCP configurator files preserved for future re-enablement.

| File | Status | Reason for Preservation |
|------|--------|------------------------|
| `packages/cli/src/aurora_cli/configurators/mcp/__init__.py` | ✅ PRESERVED | Package initialization |
| `packages/cli/src/aurora_cli/configurators/mcp/base.py` | ✅ PRESERVED | Base class for all MCP configurators |
| `packages/cli/src/aurora_cli/configurators/mcp/registry.py` | ✅ PRESERVED | Configurator registry system |
| `packages/cli/src/aurora_cli/configurators/mcp/claude.py` | ⚠️ MODIFIED | Claude Code configurator - AURORA_MCP_PERMISSIONS list updated (9→6 tools) |
| `packages/cli/src/aurora_cli/configurators/mcp/cline.py` | ✅ PRESERVED | Cline configurator - no tool permissions list |
| `packages/cli/src/aurora_cli/configurators/mcp/continue_.py` | ✅ PRESERVED | Continue configurator - no tool permissions list |
| `packages/cli/src/aurora_cli/configurators/mcp/cursor.py` | ✅ PRESERVED | Cursor configurator - no tool permissions list |

**Total**: 7 MCP configurator files preserved (1 modified for permission list)

---

## 3. MCP Server Infrastructure

Session cache and helper methods preserved for future tools.

| Component | Status | Reason for Preservation |
|-----------|--------|------------------------|
| `src/aurora_mcp/server.py` | ⚠️ MODIFIED | MCP server - tool registrations removed, server infrastructure preserved |
| `src/aurora_mcp/tools.py` - Session Cache | ✅ PRESERVED | `_last_search_results`, `_last_search_timestamp` for future tools |
| `src/aurora_mcp/tools.py` - `_ensure_initialized()` | ✅ PRESERVED | Helper method for store initialization |
| `src/aurora_mcp/tools.py` - `_format_error()` | ✅ PRESERVED | Error formatting helper for MCP responses |
| `src/aurora_mcp/config.py` | ✅ PRESERVED | MCP server configuration |

**Removed Components**:
- ❌ `aurora_search()` tool implementation - replaced by `/aur:search` slash command
- ❌ `aurora_get()` tool implementation - replaced by `/aur:get` slash command
- ❌ `aurora_query()` tool registration (if exists) - replaced by `aur soar` terminal command

---

## 4. Health Check Infrastructure

MCPFunctionalChecks class commented out but preserved for re-enablement.

| Component | Status | Reason for Preservation |
|-----------|--------|------------------------|
| `packages/cli/src/aurora_cli/health_checks.py` - `MCPFunctionalChecks` | ⚠️ MODIFIED | Class commented out or skip-decorated, not deleted |
| `packages/cli/src/aurora_cli/commands/doctor.py` - MCP checks | ⚠️ MODIFIED | MCP checks commented out, code preserved |

---

## 5. Test Infrastructure

Unit tests preserved, integration tests made skippable.

| Component | Status | Reason for Preservation |
|-----------|--------|------------------------|
| All SOAR phase handler unit tests (`tests/unit/soar/test_phase_*.py`) | ✅ PRESERVED | 239 tests covering all 9 phase handlers |
| All MCP configurator unit tests (`tests/unit/cli/configurators/mcp/`) | ✅ PRESERVED | Tests for MCP configuration infrastructure |
| MCP integration tests (`tests/integration/*mcp*.py`) | ⚠️ MODIFIED | Tests marked skippable with `@pytest.mark.skipif` decorator |
| MCP functional tests (`tests/unit/cli/test_mcp_functional_checks.py`) | ⚠️ MODIFIED | Tests updated to reflect commented-out MCP checks |

---

## 6. Documentation

Existing documentation preserved and augmented.

| File | Status | Reason for Preservation |
|------|--------|------------------------|
| `docs/ARCHITECTURE.md` | ⚠️ MODIFIED | New file created documenting dual orchestration |
| `docs/MCP_DEPRECATION.md` | ⚠️ MODIFIED | New file explaining deprecation rationale |
| `docs/MIGRATION.md` | ⚠️ MODIFIED | New file with tool replacement mapping |
| `README.md` | ⚠️ MODIFIED | Updated to remove outdated MCP tool references |

---

## 7. Configuration System

Feature flag infrastructure added for easy re-enablement.

| Component | Status | Reason for Preservation |
|-----------|--------|------------------------|
| `packages/cli/src/aurora_cli/config.py` - `mcp_enabled` field | ⚠️ MODIFIED | New field added to Config dataclass |
| `packages/cli/src/aurora_cli/config.py` - CONFIG_SCHEMA | ⚠️ MODIFIED | Schema updated with mcp.enabled section |
| `packages/cli/src/aurora_cli/commands/init.py` - `--enable-mcp` flag | ⚠️ MODIFIED | New CLI flag added |

---

## Preservation Principles

### DO Preserve:
1. ✅ All SOAR phase handler files (9 files)
2. ✅ All MCP configurator infrastructure (7 files)
3. ✅ Session cache variables in tools.py
4. ✅ Helper methods (`_ensure_initialized()`, `_format_error()`)
5. ✅ MCPFunctionalChecks class (commented out, not deleted)
6. ✅ All unit test files
7. ✅ MCP server configuration infrastructure

### DO Remove:
1. ❌ MCP tool implementations (aurora_query, aurora_search, aurora_get)
2. ❌ MCP tool registrations in server.py
3. ❌ MCP checks from doctor command output

### DO Modify:
1. ⚠️ Permission lists in configurators (remove 3 deprecated tools)
2. ⚠️ Integration tests (add skipif decorators)
3. ⚠️ Doctor command (comment out MCP checks)
4. ⚠️ Config system (add mcp.enabled flag)

---

## Verification Checklist

Before completing each phase, verify:

- [ ] All 9 SOAR phase handler files exist and have preservation comments
- [ ] All 9 phase handler unit tests pass (239 tests total)
- [ ] All 7 MCP configurator files exist
- [ ] Session cache variables exist in tools.py
- [ ] Helper methods exist in tools.py
- [ ] MCPFunctionalChecks class exists (commented or skip-decorated)
- [ ] MCP configurator unit tests pass
- [ ] Integration tests skippable with environment variable

---

## Rollback Safety

If any preserved component is accidentally deleted:

**Option 1**: Restore from git tag
```bash
git checkout mcp-deprecation-baseline -- <deleted-file>
```

**Option 2**: Restore from feature branch history
```bash
git log --all --full-history -- <deleted-file>
git checkout <commit-hash> -- <deleted-file>
```

**Option 3**: Use feature flag for quick re-enablement
```json
{
  "mcp": {
    "enabled": true
  }
}
```

---

**Last Updated**: Phase 1 Audit (January 2026)
**Status**: All preservation items identified and documented
