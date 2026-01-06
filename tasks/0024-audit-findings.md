# PRD-0024: Phase 1 Audit Findings

## Executive Summary

Phase 1 baseline audit completed successfully. All critical infrastructure identified and preservation strategy documented. Ready to proceed with Phase 2 (Configuration Architecture).

## Audit Scope

**Date**: January 6, 2026
**Branch**: feature/mcp-deprecation
**Baseline Tag**: mcp-deprecation-baseline
**Auditor**: AI Assistant (Claude)

---

## 1. SOAR Phase Handler Audit

### Files Identified: 9 Phase Handlers

**Location**: `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/phases/`

| File | Purpose | Lines of Code | Status |
|------|---------|---------------|--------|
| `assess.py` | Phase 1: Complexity Assessment | 35,810 chars | ✅ Preserved |
| `retrieve.py` | Phase 2: Context Retrieval | 6,803 chars | ✅ Preserved |
| `decompose.py` | Phase 3: Query Decomposition | 6,411 chars | ✅ Preserved |
| `verify.py` | Phase 4: Decomposition Verification | 13,442 chars | ✅ Preserved |
| `route.py` | Phase 5: Agent Routing | 11,247 chars | ✅ Preserved |
| `collect.py` | Phase 6: Agent Execution | 15,486 chars | ✅ Preserved |
| `synthesize.py` | Phase 7: Result Synthesis | 6,067 chars | ✅ Preserved |
| `record.py` | Phase 8: ACT-R Pattern Caching | 6,415 chars | ✅ Preserved |
| `respond.py` | Phase 9: Response Formatting | 10,832 chars | ✅ Preserved |

**Preservation Action Taken**: Added "DO NOT DELETE" comments to all 9 phase handler file headers explaining dual orchestration approach (bash vs Python).

### Unit Test Coverage: 239 Tests Passing

**Test Files**: 9 files in `/home/hamr/PycharmProjects/aurora/tests/unit/soar/`

| Test File | Tests Count | Status |
|-----------|-------------|--------|
| `test_phase_assess.py` | 58 tests | ✅ All passing |
| `test_phase_collect.py` | 26 tests | ✅ All passing |
| `test_phase_decompose.py` | 14 tests | ✅ All passing |
| `test_phase_record.py` | 23 tests | ✅ All passing |
| `test_phase_respond.py` | 22 tests | ✅ All passing |
| `test_phase_retrieve.py` | 31 tests | ✅ All passing |
| `test_phase_route.py` | 30 tests | ✅ All passing |
| `test_phase_verify.py` | 32 tests | ✅ All passing |
| `test_phase_verify_retry.py` | 3 tests | ✅ All passing |

**Total**: 239 tests passing (100% pass rate)

**Risk Assessment**: ✅ LOW RISK - All phase handlers have excellent test coverage and are actively tested.

---

## 2. Deprecated Tool Reference Audit

### aurora_query References: 16 Files

**Primary Locations**:
- `src/aurora_mcp/server.py` - Tool registration
- `src/aurora_mcp/tools.py` - Tool implementation
- `packages/cli/src/aurora_cli/configurators/mcp/claude.py` - Permission list
- `packages/cli/src/aurora_cli/health_checks.py` - MCP functional checks
- `packages/cli/src/aurora_cli/templates/slash_commands.py` - Slash command templates

**Test Files** (8 files):
- `tests/unit/mcp/test_aurora_query_simplified.py`
- `tests/unit/mcp/test_aurora_query_tool.py`
- `tests/unit/mcp/test_aurora_get.py`
- `tests/unit/cli/test_mcp_functional_checks.py`
- `tests/integration/test_mcp_no_api_key.py`
- `tests/integration/mcp/test_mcp_soar_multi_turn.py`
- `tests/e2e/test_mcp_e2e.py`
- `tests/e2e/test_aurora_query_e2e.py`

**Archive Files** (2 files):
- `tests/archive/2025-01-mcp-simplification/test_mcp_aurora_query_integration.py`
- `tests/archive/2025-01-mcp-simplification/test_aurora_query_llm_tests.py`

**Action Required**: Update server.py, tools.py, configurators, health_checks.py. Mark integration tests as skippable.

### aurora_search References: 14 Files

**Primary Locations**:
- `src/aurora_mcp/server.py` - Tool registration
- `src/aurora_mcp/tools.py` - Tool implementation
- `src/aurora_mcp/config.py` - MCP configuration
- `packages/cli/src/aurora_cli/configurators/mcp/claude.py` - Permission list
- `packages/cli/src/aurora_cli/health_checks.py` - MCP functional checks
- `packages/cli/src/aurora_cli/commands/memory.py` - Memory commands

**Test Files** (8 files):
- Integration tests, e2e tests, MCP harness tests

**Action Required**: Remove tool registration and implementation. Update configurators and tests.

### aurora_get References: 9 Files

**Primary Locations**:
- `src/aurora_mcp/server.py` - Tool registration
- `src/aurora_mcp/tools.py` - Tool implementation
- `packages/cli/src/aurora_cli/configurators/mcp/claude.py` - Permission list
- `packages/cli/src/aurora_cli/health_checks.py` - MCP functional checks

**Test Files** (5 files):
- Unit tests, integration tests, e2e tests

**Action Required**: Remove tool registration and implementation. Update configurators and tests.

**Risk Assessment**: ⚠️ MEDIUM RISK - Many files reference deprecated tools, but most are test files. Main risk is missing a reference in production code.

---

## 3. MCP Configurator Infrastructure Audit

### Configurator Files: 7 Files

**Location**: `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/mcp/`

| File | Type | Tool Permissions | Status |
|------|------|------------------|--------|
| `__init__.py` | Package init | N/A | ✅ Preserved |
| `base.py` | Base class | N/A | ✅ Preserved |
| `registry.py` | Registry | N/A | ✅ Preserved |
| `claude.py` | Configurator | 9 tools (AURORA_MCP_PERMISSIONS list) | ⚠️ Needs update |
| `cline.py` | Configurator | No permission list | ✅ Preserved |
| `continue_.py` | Configurator | No permission list | ✅ Preserved |
| `cursor.py` | Configurator | No permission list | ✅ Preserved |

**Note**: The PRD expected 20+ configurators, but only 7 files exist. This suggests consolidation or fewer IDE integrations than originally documented.

**Current AURORA_MCP_PERMISSIONS in claude.py**:
```python
AURORA_MCP_PERMISSIONS = [
    "mcp__aurora__aurora_query",      # ❌ REMOVE
    "mcp__aurora__aurora_search",     # ❌ REMOVE
    "mcp__aurora__aurora_index",      # ✅ KEEP
    "mcp__aurora__aurora_context",    # ✅ KEEP
    "mcp__aurora__aurora_related",    # ✅ KEEP
    "mcp__aurora__aurora_get",        # ❌ REMOVE
    "mcp__aurora__aurora_list_agents", # ✅ KEEP
    "mcp__aurora__aurora_search_agents", # ✅ KEEP
    "mcp__aurora__aurora_show_agent",  # ✅ KEEP
]
```

**Action Required**: Update claude.py to remove 3 deprecated tools (query, search, get), keeping 6 remaining tools.

**Risk Assessment**: ✅ LOW RISK - Only 1 configurator file needs updating (claude.py). Other configurators have no permission lists.

---

## 4. Documentation Audit

### Existing Documentation

**Location**: `/home/hamr/PycharmProjects/aurora/docs/`

| File | Exists | Needs Update |
|------|--------|--------------|
| `README.md` | ✅ Yes | ⚠️ May need MCP reference updates |
| `ARCHITECTURE.md` | ❌ No | ⚠️ Created in Phase 1 |
| `MCP_DEPRECATION.md` | ❌ No | ⚠️ Will create in Phase 7 |
| `MIGRATION.md` | ❌ No | ⚠️ Will create in Phase 7 |
| `ROLLBACK.md` | ❌ No | ⚠️ Will create in Phase 7 |

**New Documentation Created in Phase 1**:
- ✅ `docs/ARCHITECTURE.md` - Dual SOAR orchestration explanation
- ✅ `tasks/0024-preservation-checklist.md` - Infrastructure preservation guide
- ✅ `tasks/0024-audit-findings.md` - This document

**Action Required**: Create MCP_DEPRECATION.md, MIGRATION.md, and ROLLBACK.md in Phase 7. Update README.md if MCP references exist.

---

## 5. Session Cache Infrastructure Audit

### Session Cache in tools.py

**Location**: `src/aurora_mcp/tools.py`

**Components to Preserve**:
```python
# Session cache (lines ~54-56)
_last_search_results: Optional[List[Dict[str, Any]]] = None
_last_search_timestamp: Optional[float] = None

# Helper methods
def _ensure_initialized() -> MemoryStore  # Line ~58
def _format_error() -> str               # Line ~247
```

**Current Status**: Session cache and helpers exist and functional.

**Action Required**: Add preservation comments explaining these are kept for future MCP tools.

**Risk Assessment**: ✅ LOW RISK - Small, well-defined components with clear preservation requirements.

---

## 6. Health Check Infrastructure Audit

### MCPFunctionalChecks Class

**Location**: `packages/cli/src/aurora_cli/health_checks.py`

**Current Status**: Class exists and is actively used by `aur doctor` command.

**Action Required in Phase 4**:
1. Comment out MCPFunctionalChecks instantiation in doctor.py
2. Comment out MCP FUNCTIONAL output section in doctor.py
3. Add preservation comment or skip decorator to MCPFunctionalChecks class
4. Update doctor command tests

**Risk Assessment**: ⚠️ MEDIUM RISK - Doctor command is user-facing. Must ensure no errors appear after commenting out MCP checks.

---

## 7. Risk Assessment and Mitigation

### Overall Risk Level: ⚠️ MEDIUM

**High-Risk Areas**:
1. ⚠️ Doctor command updates (Phase 4) - User-facing feature
2. ⚠️ Test file updates (Phase 8) - Many test files reference deprecated tools
3. ⚠️ Integration test skipif decorators (Phase 8) - Must not break CI/CD

**Medium-Risk Areas**:
1. ⚠️ MCP configurator updates (Phase 5) - Only 1 file to update
2. ⚠️ Server.py tool removal (Phase 3) - Clear boundaries
3. ⚠️ Tools.py method removal (Phase 3) - Clear boundaries

**Low-Risk Areas**:
1. ✅ SOAR phase handlers - No changes required (preservation only)
2. ✅ Session cache preservation - Simple comment additions
3. ✅ Documentation creation - New files, no risk to existing code

### Mitigation Strategies

**Strategy 1: Incremental Testing**
- Run full test suite after each phase
- Mark phase complete only when all tests pass
- Verify doctor command output manually after Phase 4

**Strategy 2: Feature Flag Safety Net**
- mcp.enabled flag allows instant re-enablement
- No code changes required to restore functionality
- Users can override deprecation if needed

**Strategy 3: Git Rollback Tag**
- mcp-deprecation-baseline tag created in Phase 0
- Full state snapshot before any changes
- Single command to revert all changes

**Strategy 4: Preservation Documentation**
- Preservation checklist created
- Each preserved component documented with reason
- Clear verification checklist at each phase

---

## 8. Acceptance Criteria Verification

### Phase 1 Acceptance Criteria (from PRD):

- [x] **1.1**: 9 SOAR phase handler files identified and preservation confirmed
  - ✅ All 9 files found and "DO NOT DELETE" comments added

- [x] **1.2**: All 9 phase handler unit tests passing
  - ✅ 239 tests passing (100% pass rate)

- [x] **1.3**: Dual orchestration approach documented
  - ✅ ARCHITECTURE.md created with comprehensive explanation

- [x] **1.4**: Complete list of deprecated tool references documented
  - ✅ aurora_query: 16 files, aurora_search: 14 files, aurora_get: 9 files

- [x] **1.5**: List of all MCP configurator files created
  - ✅ 7 configurator files identified, 1 needs permission list update

- [x] **1.6**: "Keep Dormant" preservation checklist created
  - ✅ tasks/0024-preservation-checklist.md created with all preservation items

- [x] **1.7**: Audit findings documented
  - ✅ This document (tasks/0024-audit-findings.md) completed

**Phase 1 Status**: ✅ **COMPLETE** - All acceptance criteria met

---

## 9. Recommendations for Next Phases

### Phase 2: Configuration Architecture
- **Recommendation**: Test config flag parsing thoroughly with both valid and invalid values
- **Recommendation**: Ensure generated config files have correct mcp.enabled defaults

### Phase 3: MCP Tool Removal
- **Recommendation**: Remove tools one at a time and test server startup after each removal
- **Recommendation**: Verify list_tools() output shows correct reduced count

### Phase 4: Doctor Command Updates
- **Recommendation**: Create backup of doctor.py before modifications
- **Recommendation**: Test `aur doctor` output manually in clean environment
- **Recommendation**: Verify exit codes unchanged for non-MCP checks

### Phase 5: Configurator Permission Updates
- **Recommendation**: Only claude.py needs updating (not 20+ files as PRD suggested)
- **Recommendation**: Test `aur init --enable-mcp` after updating permissions

### Phase 8: Testing and Validation
- **Recommendation**: Create fresh test environment as specified in PRD
- **Recommendation**: Test both fresh install and re-enablement scenarios
- **Recommendation**: Run full pytest suite multiple times to catch flaky tests

---

## 10. Open Questions and Clarifications

### Question 1: Configurator Count Discrepancy
- **Expected**: PRD mentioned 20+ MCP configurator files
- **Actual**: Only 7 files found
- **Resolution**: Appears to be consolidation or fewer IDE integrations. Proceed with 7 files.

### Question 2: Phase 0 Completion Status
- **Context**: Task list shows Phase 0 as incomplete
- **Actual**: User confirmed baseline tag exists and branch created
- **Resolution**: Phase 0 completed, proceeding with Phase 1 ✅

### Question 3: Test File Handling
- **Question**: Should test files in `tests/archive/` be updated?
- **Recommendation**: Leave archived tests unchanged, focus on active test files

---

## Appendix A: File Modification Matrix

| File Category | Files Count | Action | Phase |
|---------------|-------------|--------|-------|
| SOAR Phase Handlers | 9 | Preserve + Comments | Phase 1 ✅ |
| MCP Configurators | 7 | Preserve (1 modify) | Phase 5 |
| MCP Server | 1 | Remove tools, preserve infra | Phase 3 |
| MCP Tools | 1 | Remove methods, preserve cache | Phase 3 |
| Health Checks | 2 | Comment out checks | Phase 4 |
| Config System | 2 | Add mcp.enabled flag | Phase 2 |
| Doctor Command | 1 | Comment out MCP section | Phase 4 |
| Unit Tests | 50+ | Update expectations | Phase 8 |
| Integration Tests | 10+ | Add skipif decorators | Phase 8 |
| Documentation | 4 | Create new docs | Phase 7 |

**Total Files to Modify**: ~90 files
**Total Files to Preserve**: ~25 critical files

---

## Appendix B: Phase Handler Test Coverage Details

| Phase Handler | Test Count | Coverage Areas |
|---------------|------------|----------------|
| assess.py | 58 | Complexity classification, keyword detection, LLM fallback, corpus accuracy |
| collect.py | 26 | Agent execution, parallel/sequential routing, timeouts, validation |
| decompose.py | 14 | Query hashing, context summarization, caching, LLM integration |
| record.py | 23 | Pattern caching, scoring, metadata, ACT-R integration |
| respond.py | 22 | Response formatting, verbosity levels, JSON serialization |
| retrieve.py | 31 | Budget allocation, chunk retrieval, activation filtering |
| route.py | 30 | Agent routing, dependency validation, circular detection |
| verify.py | 32 | Self-verification, adversarial verification, retry logic, retrieval quality |
| verify_retry.py | 3 | Retry mechanism, max retries, score thresholds |

**Total Test Coverage**: 239 tests across 9 phase handlers

---

**Audit Completed**: Phase 1 - January 6, 2026
**Next Phase**: Phase 2 - Configuration Architecture
**Overall Status**: ✅ Ready to proceed
