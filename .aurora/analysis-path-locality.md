# Aurora Path Locality Analysis

**Goal**: Move all generated artifacts to project directory (`./.aurora/`) except budget tracking (global `~/.aurora/`)

## Current State Analysis

### ✅ Already Project-Local (Correct)

These paths are already configured to use `./.aurora/` (project-local):

1. **Database**: `./.aurora/memory.db`
   - Config: `packages/cli/src/aurora_cli/config.py:76`

2. **Logs**: `./.aurora/logs/aurora.log`, `./.aurora/logs/mcp.log`
   - Config: `packages/cli/src/aurora_cli/config.py:72,74`

3. **Planning (via config)**: `./.aurora/plans`
   - Config: `packages/cli/src/aurora_cli/config.py:93`

4. **Agent cache (via config)**: `./.aurora/cache/agent_manifest.json`
   - Config: `packages/cli/src/aurora_cli/config.py:91`

### ✅ Already Global (Correct)

These paths correctly use `~/.aurora/` (global):

1. **Budget tracker**: `~/.aurora/budget_tracker.json`
   - Config: `packages/cli/src/aurora_cli/config.py:78` (marked as "ONLY global file")
   - Implementation: `packages/core/src/aurora_core/budget/tracker.py:159`
   - Budget archives: `~/.aurora/budget_archives/` (line 211)

### ❌ Needs Change: Global → Project-Local

These paths currently default to `~/.aurora/` but should use `./.aurora/`:

#### 1. **Conversation Logs**
**Current**: `~/.aurora/logs/conversations/`
**Target**: `./.aurora/logs/conversations/`

**Files to modify**:
- `packages/core/src/aurora_core/logging/conversation_logger.py:47`
  ```python
  # BEFORE
  base_path = Path.home() / ".aurora" / "logs" / "conversations"

  # AFTER
  base_path = Path.cwd() / ".aurora" / "logs" / "conversations"
  ```

**Impact**:
- Test file: `tests/unit/core/test_conversation_logger.py:63`
- Used by: `packages/soar/src/aurora_soar/orchestrator.py` (ConversationLogger instantiation)

#### 2. **Planning System Fallback**
**Current**: Falls back to `~/.aurora/plans/` when project directory doesn't exist
**Target**: Should create `./.aurora/plans/` in project directory

**Files to modify**:

a) `packages/planning/src/aurora_planning/planning_config.py:45`
   ```python
   # BEFORE (line 44-49)
   # Default to ~/.aurora/plans/
   default_plans_dir = Path.home() / ".aurora" / "plans"
   if not default_plans_dir.exists():
       default_plans_dir.mkdir(parents=True, exist_ok=True)
   return default_plans_dir

   # AFTER
   # Default to ./.aurora/plans/ (project-local)
   default_plans_dir = Path.cwd() / ".aurora" / "plans"
   if not default_plans_dir.exists():
       default_plans_dir.mkdir(parents=True, exist_ok=True)
   return default_plans_dir
   ```

b) `packages/cli/src/aurora_cli/planning/core.py:55`
   ```python
   # BEFORE
   return Path.home() / ".aurora" / "plans"

   # AFTER
   return Path.cwd() / ".aurora" / "plans"
   ```

**Impact**:
- Tests: Multiple references in `tests/unit/planning/test_planning_config.py`
- Docstrings: Update references in planning module

#### 3. **Cache Paths in Health Checks**
**Current**: `~/.aurora/cache`
**Target**: `./.aurora/cache`

**Files to modify**:

a) `packages/cli/src/aurora_cli/health_checks.py:373`
   ```python
   # BEFORE
   cache_dir = Path.home() / ".aurora" / "cache"

   # AFTER
   cache_dir = Path.cwd() / ".aurora" / "cache"
   ```

b) `packages/cli/src/aurora_cli/health_checks.py:405`
   ```python
   # BEFORE
   cache_dir = Path.home() / ".aurora" / "cache"

   # AFTER
   cache_dir = Path.cwd() / ".aurora" / "cache"
   ```

**Note**: Config already has this correct (line 91), but health checks hardcode it

#### 4. **Agent Manifest Cache Paths**
**Current**: `~/.aurora/cache/agent_manifest.json`
**Target**: `./.aurora/cache/agent_manifest.json`

**Files to modify**:

a) `packages/cli/src/aurora_cli/planning/agents.py:321`
   ```python
   # BEFORE
   manifest_path = Path.home() / ".aurora" / "cache" / "agent_manifest.json"

   # AFTER
   manifest_path = Path.cwd() / ".aurora" / "cache" / "agent_manifest.json"
   ```

b) `packages/cli/src/aurora_cli/planning/decompose.py:299`
   ```python
   # BEFORE
   manifest_path = Path.home() / ".aurora" / "cache" / "agent_manifest.json"

   # AFTER
   manifest_path = Path.cwd() / ".aurora" / "cache" / "agent_manifest.json"
   ```

**Note**: Config already has this correct, but these modules hardcode it

#### 5. **Health Check Aurora Directory**
**Current**: Various health checks reference `~/.aurora`
**Target**: `./.aurora`

**Files to modify**:

a) `packages/cli/src/aurora_cli/health_checks.py:92`
b) `packages/cli/src/aurora_cli/health_checks.py:113`
c) `packages/cli/src/aurora_cli/health_checks.py:158`

Review these and update to use `./.aurora` unless they're specifically checking global config/budget.

## Command-Specific Analysis

### `aur init` Command

**Review**: `packages/cli/src/aurora_cli/commands/init.py`

**Already correct** ✅:
- Line 142: `db_path = project_path / ".aurora" / "memory.db"` (project-local)
- Line 333-338: Creates `.aurora/plans/`, `.aurora/logs/`, `.aurora/cache/` (project-local)
- Line 341-348: Creates `project.md` in `.aurora/` (project-local)
- Line 351-357: Creates `AGENTS.md` in `.aurora/` (project-local)
- Line 360-368: Creates headless templates in `.aurora/headless/` (project-local)

**No changes needed** for `aur init` - it already creates all project-local directories correctly.

### `aur doctor` Command

**Review**: `packages/cli/src/aurora_cli/commands/doctor.py`

**Status**: Doctor delegates to health check classes

**Action needed**:
- Doctor itself is correct - it just calls health check classes
- Fix the health check classes (see #3 and #5 above)
- Once health checks are fixed, doctor will automatically work correctly

**Specific checks affected**:
- `CoreSystemChecks` - may check global vs local paths (line 92, 113, 158 in health_checks.py)
- `SearchRetrievalChecks` - cache checks (line 373, 405 in health_checks.py)

## Implementation Strategy

### Phase 1: Core Logging Changes
1. Update `ConversationLogger` default path
2. Update related tests
3. Verify SOAR orchestrator uses project-local logs

### Phase 2: Planning System
1. Update `planning_config.py` fallback
2. Update `core.py` default path
3. Update planning tests
4. Update documentation

### Phase 3: Cache Paths
1. Update health checks to use project-local cache
2. Update agent manifest paths to read from config
3. Consolidate cache path references to use config

### Phase 4: Health Checks
1. Review all health check path references
2. Keep only budget-related checks as global
3. Move all other checks to project-local

### Phase 5: Testing & Documentation
1. Update all affected tests
2. Update path references in docs
3. Add migration notes if needed

## Commands Impact Summary

| Command | Needs Updates? | Details |
|---------|----------------|---------|
| `aur init` | ❌ No | Already creates all project-local directories correctly |
| `aur doctor` | ⚠️ Indirect | Works via health checks - fix health checks and doctor is fixed |
| `aur plan` | ⚠️ Maybe | Uses planning system - fix planning fallbacks (Phase 2) |
| `aur mem` | ✅ Good | Uses config db_path (already project-local) |
| `aur query` | ⚠️ Maybe | Creates conversation logs - fix ConversationLogger (Phase 1) |
| `aur agents` | ⚠️ Maybe | Uses agent manifest cache - fix cache paths (Phase 3) |

## Key Principles

1. **Budget = Global**: Only budget tracking lives in `~/.aurora/`
   - `budget_tracker.json`
   - `budget_archives/`

2. **Everything Else = Project-Local**: All generated artifacts in `./.aurora/`
   - `logs/`
   - `plans/`
   - `cache/`
   - `memory.db`

3. **Consistency**: Use `Path.cwd()` for project-local, `Path.home()` only for budget

4. **Config-First**: Prefer reading paths from `Config` object rather than hardcoding

## Files Summary

**Total files to modify**: ~10 files

**By package**:
- `packages/core/`: 1 file (conversation_logger.py)
- `packages/planning/`: 1 file (planning_config.py)
- `packages/cli/`: 5 files (planning/core.py, planning/agents.py, planning/decompose.py, health_checks.py x2 locations)
- `tests/`: 2+ files (conversation_logger tests, planning tests)

**No changes needed** (already correct):
- `packages/core/src/aurora_core/budget/tracker.py` (stays global ✓)
- `packages/cli/src/aurora_cli/config.py` (mostly correct ✓)
- `packages/cli/src/aurora_cli/commands/init.py` (already project-local ✓)
- `packages/cli/src/aurora_cli/commands/doctor.py` (delegates to health checks ✓)
- Database paths (already project-local ✓)
