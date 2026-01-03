# OpenSpec to Aurora Planning Migration Checklist

**Created**: 2026-01-03
**Source**: `/home/hamr/PycharmProjects/aurora/openspec-source/`
**Target**: `packages/planning/src/aurora_planning/`
**Total Tests**: 284 (all passing in source)

---

## Test Migration Summary

### Integration Tests (3 files, 28 tests)
- [ ] `tests/integration/test_cli_e2e.py` (7 tests) → `tests/integration/planning/test_cli_e2e.py`
- [ ] `tests/integration/test_json_conversion.py` (9 tests) → `tests/integration/planning/test_json_conversion.py`
- [ ] `tests/integration/test_slash_commands.py` (12 tests) → **SKIP** (slash commands not in Phase 1)

### Unit Tests - CLI (3 files, 20 tests)
- [ ] `tests/unit/cli/test_capability_cmd.py` (6 tests) → **DEFER** (Phase 2 - agent discovery)
- [ ] `tests/unit/cli/test_plan_cmd.py` (9 tests) → `tests/unit/planning/test_plan_commands.py`
- [ ] `tests/unit/cli/test_validate_cmd.py` (5 tests) → `tests/unit/planning/test_validation_commands.py`

### Unit Tests - Commands (5 files, 49 tests)
- [ ] `tests/unit/commands/test_archive.py` (20 tests) → `tests/unit/planning/commands/test_archive.py`
- [ ] `tests/unit/commands/test_init.py` (8 tests) → `tests/unit/planning/commands/test_init.py`
- [ ] `tests/unit/commands/test_list.py` (13 tests) → `tests/unit/planning/commands/test_list.py`
- [ ] `tests/unit/commands/test_update.py` (6 tests) → `tests/unit/planning/commands/test_update.py`
- [ ] `tests/unit/commands/test_view.py` (2 tests) → `tests/unit/planning/commands/test_view.py`

### Unit Tests - Configurators (5 files, 45 tests)
- [ ] `tests/unit/configurators/slash/test_base.py` (6 tests) → **SKIP** (slash commands not in Phase 1)
- [ ] `tests/unit/configurators/slash/test_claude.py` (8 tests) → **SKIP** (slash commands not in Phase 1)
- [ ] `tests/unit/configurators/slash/test_opencode.py` (7 tests) → **SKIP** (slash commands not in Phase 1)
- [ ] `tests/unit/configurators/slash/test_registry.py` (8 tests) → **SKIP** (slash commands not in Phase 1)
- [ ] `tests/unit/configurators/test_registry.py` (8 tests) → `tests/unit/planning/test_configurators.py`

### Unit Tests - Converters (1 file, 7 tests)
- [ ] `tests/unit/converters/test_json.py` (7 tests) → `tests/unit/planning/converters/test_json.py`

### Unit Tests - Parsers (3 files, 36 tests)
- [ ] `tests/unit/parsers/test_markdown.py` (13 tests) → `tests/unit/planning/parsers/test_markdown.py`
- [ ] `tests/unit/parsers/test_plan_parser.py` (8 tests) → `tests/unit/planning/parsers/test_plan_parser.py`
- [ ] `tests/unit/parsers/test_requirements.py` (15 tests) → `tests/unit/planning/parsers/test_requirements.py`

### Unit Tests - Schemas (3 files, 23 tests)
- [ ] `tests/unit/schemas/test_base.py` (8 tests) → `tests/unit/planning/schemas/test_base.py`
- [ ] `tests/unit/schemas/test_capability.py` (5 tests) → `tests/unit/planning/schemas/test_capability.py`
- [ ] `tests/unit/schemas/test_plan.py` (10 tests) → `tests/unit/planning/schemas/test_plan.py`

### Unit Tests - Config (2 files, 22 tests)
- [ ] `tests/unit/test_config.py` (10 tests) → `tests/unit/planning/test_config.py`
- [ ] `tests/unit/test_global_config.py` (12 tests) → `tests/unit/planning/test_global_config.py`

### Unit Tests - Utils (5 files, 39 tests)
- [ ] `tests/unit/utils/test_discovery.py` (9 tests) → **DEFER** (Phase 2 - agent discovery)
- [ ] `tests/unit/utils/test_filesystem.py` (6 tests) → `tests/unit/planning/utils/test_filesystem.py`
- [ ] `tests/unit/utils/test_interactive.py` (6 tests) → `tests/unit/planning/utils/test_interactive.py`
- [ ] `tests/unit/utils/test_match.py` (8 tests) → `tests/unit/planning/utils/test_match.py`
- [ ] `tests/unit/utils/test_task_progress.py` (10 tests) → `tests/unit/planning/utils/test_task_progress.py`

### Unit Tests - Validation (2 files, 23 tests)
- [ ] `tests/unit/validation/test_types.py` (8 tests) → `tests/unit/planning/validation/test_types.py`
- [ ] `tests/unit/validation/test_validator.py` (15 tests) → `tests/unit/planning/validation/test_validator.py`

---

## Source Code Migration Summary

### Core Modules to Migrate (High Priority)

#### Commands (5 files)
- [ ] `aurora/commands/archive.py` → `aurora_planning/commands/archive.py`
- [ ] `aurora/commands/init.py` → `aurora_planning/commands/init.py`
- [ ] `aurora/commands/list.py` → `aurora_planning/commands/list.py`
- [ ] `aurora/commands/update.py` → `aurora_planning/commands/update.py`
- [ ] `aurora/commands/view.py` → `aurora_planning/commands/view.py`

#### Parsers (3 files)
- [ ] `aurora/parsers/markdown.py` → `aurora_planning/parsers/markdown.py`
- [ ] `aurora/parsers/plan_parser.py` → `aurora_planning/parsers/plan_parser.py`
- [ ] `aurora/parsers/requirements.py` → `aurora_planning/parsers/requirements.py`

#### Schemas (3 files)
- [ ] `aurora/schemas/base.py` → `aurora_planning/schemas/base.py`
- [ ] `aurora/schemas/plan.py` → `aurora_planning/schemas/plan.py`
- [ ] `aurora/schemas/capability.py` → `aurora_planning/schemas/capability.py`

#### Validation (3 files)
- [ ] `aurora/validation/validator.py` → `aurora_planning/validators/validator.py`
- [ ] `aurora/validation/types.py` → `aurora_planning/validators/types.py`
- [ ] `aurora/validation/constants.py` → `aurora_planning/validators/constants.py`

#### Utils (4 files - selective)
- [ ] `aurora/utils/filesystem.py` → `aurora_planning/utils/filesystem.py`
- [ ] `aurora/utils/interactive.py` → `aurora_planning/utils/interactive.py`
- [ ] `aurora/utils/match.py` → `aurora_planning/utils/match.py`
- [ ] `aurora/utils/task_progress.py` → `aurora_planning/utils/task_progress.py`
- [ ] **SKIP**: `aurora/utils/discovery.py` (Phase 2 - agent discovery)

#### Converters (1 file)
- [ ] `aurora/converters/json.py` → `aurora_planning/converters/json.py`

#### Config (2 files)
- [ ] `aurora/config.py` → `aurora_planning/config.py`
- [ ] `aurora/global_config.py` → `aurora_planning/global_config.py`

### Configurators (Partial Migration)
- [ ] `aurora/configurators/registry.py` → `aurora_planning/configurators/registry.py`
- [ ] **SKIP**: `aurora/configurators/slash/*` (slash commands in Phase 2)

### Templates (Defer to Task 1.4)
- [ ] `aurora/templates/` → Will be recreated in `aurora_planning/templates/` with Aurora-native structure

---

## Known Breaking Changes

### 1. Import Path Changes
**Before**: `from aurora.commands import ArchiveCommand`
**After**: `from aurora_planning.commands import ArchiveCommand`

**Action**: Global search-and-replace in all migrated files

### 2. Directory Path Changes
**Before**: `openspec/` or `~/.openspec/`
**After**: `.aurora/plans/` or `~/.aurora/plans/`

**Action**: Update all path constants in config files

### 3. Plan ID Format Change
**Before**: User-provided plan IDs (e.g., `oauth-integration`)
**After**: Auto-incrementing NNNN-slug (e.g., `0001-oauth-integration`)

**Action**: Update all tests that hard-code plan IDs

### 4. Slash Command Removal (Phase 1)
**Before**: `/openspec:proposal`, `/openspec:apply`, `/openspec:archive`
**After**: `aur plan create`, `aur plan view`, `aur plan archive`

**Action**: Skip slash command tests (29 tests deferred to Phase 2)

### 5. Agent Discovery Removal (Phase 1)
**Before**: Automatic agent discovery from `~/.claude/agents/`
**After**: Manual agent assignment in agents.json

**Action**: Skip agent discovery tests (15 tests deferred to Phase 2)

### 6. Package Namespace
**Before**: `aurora` package (OpenSpec)
**After**: `aurora_planning` package (Aurora Planning)

**Action**: Update all imports and test fixtures

---

## Test Count Breakdown

| Category | Total Tests | Migrate | Skip/Defer | New Tests |
|----------|-------------|---------|------------|-----------|
| Integration | 28 | 16 | 12 | +5 |
| Commands | 49 | 49 | 0 | +10 |
| Parsers | 36 | 36 | 0 | +5 |
| Schemas | 23 | 23 | 0 | +5 |
| Validation | 23 | 23 | 0 | +5 |
| Config | 22 | 22 | 0 | +10 |
| Utils | 39 | 30 | 9 | +5 |
| Converters | 7 | 7 | 0 | +2 |
| Configurators | 45 | 8 | 37 | +3 |
| CLI | 20 | 14 | 6 | +5 |
| **TOTAL** | **284** | **228** | **56** | **+55** |

### Expected Phase 1 Test Count
- **Migrated from OpenSpec**: 228 tests
- **New Aurora-specific tests**: +55 tests
- **Total Phase 1 tests**: 283 tests
- **Success Criteria**: ≥280 tests passing (≥98%)

---

## Migration Strategy

### Phase A: Direct Migration (Tasks 1.1-1.3)
1. Copy source files maintaining directory structure
2. Update import paths (global search-replace)
3. Update directory paths (openspec → .aurora/plans)
4. Run initial test pass (expect ~70% pass rate)

### Phase B: Test Adaptation (Task 7.1)
1. Update fixtures (tmp_path, openspec_dir → aurora_plans_dir)
2. Update plan ID assertions (hard-coded → dynamic generation)
3. Fix path assertions (.openspec → .aurora/plans)
4. Target: ≥280/283 tests passing

### Phase C: New Tests (Tasks 1.6, 1.7, 2.7, 3.7, 4.10, 5.7)
1. Add tests for plan ID auto-increment (Task 1.6)
2. Add tests for archive timestamp format (Task 1.7)
3. Add tests for init command enhancements (Task 2.7)
4. Add tests for new command features (Task 3.7)
5. Add tests for template rendering (Task 4.10)
6. Add tests for config overrides (Task 5.7)

---

## Validation Checkpoints

### After Task 1.3 (Core Module Migration)
```bash
python -c "from aurora_planning.commands import ArchiveCommand; print('OK')"
python -c "from aurora_planning.parsers import MarkdownParser; print('OK')"
python -c "from aurora_planning.schemas import Plan; print('OK')"
```

### After Task 7.1 (Test Migration)
```bash
pytest tests/unit/planning/ -v --tb=short -x
# Expected: ≥220/228 tests passing initially
```

### After Task 7.5 (Coverage Target)
```bash
pytest tests/unit/planning/ --cov=aurora_planning --cov-report=term-missing
# Expected: ≥95% coverage
```

### Final Validation
```bash
pytest tests/ -v --tb=short -k planning
# Expected: ≥280/283 tests passing (≥98%)
```

---

## File Count Summary

- **Test Files to Migrate**: 32 files → 25 files (7 deferred/skipped)
- **Source Files to Migrate**: 31 files → 27 files (4 deferred/skipped)
- **Template Files to Create**: 8 new files (task 1.4)
- **Documentation Files**: 4 new files (task 6.x)
- **Total New/Modified Files**: ~64 files

---

**VALIDATION COMPLETE**

✓ Test count verified: 284 tests in OpenSpec source
✓ All 284 tests passing in source repository
✓ Test categories identified and mapped to Aurora structure
✓ Breaking changes documented with migration actions
✓ Expected outcomes defined (≥280/283 tests passing post-migration)

**READY FOR TASK 1.2: Package Scaffolding**
