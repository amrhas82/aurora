# Phase 0.5: OpenSpec → Aurora Port (Comprehensive)

**PRD Reference**: `/home/hamr/PycharmProjects/aurora/tasks/0017-prd-aurora-planning-system.md` Section 11
**Phase**: 0.5 (Pre-requisite for revised Phase 1-3)
**Status**: ✅ COMPLETE
**Fork**: https://github.com/amrhas82/OpenSpec
**Branch**: `refactored`
**Working Directory**: `/tmp/openspec-source/`
**Detailed Report**: `/tmp/openspec-source/PORT_REPORT.md`

---

## Objective

Port OpenSpec TypeScript to Python (Aurora), keeping detailed documentation of what was ported vs skipped. This becomes the foundation for Aurora's planning system.

**Port Strategy**: ~5,800 lines (~67% of considered source)
**Skip**: Completions (use Click), Artifact-Graph (experimental), Slash Configurators (~2,800 lines)

---

## Summary: Files to Port

| Phase | Category | Files | Lines | Status |
|-------|----------|-------|-------|--------|
| 1 | Schemas | 3 | 76 | ✅ DONE (23 tests) |
| 2 | Validation | 3 | 515 | ✅ DONE (23 tests) |
| 3 | Parsers | 3 | 703 | ✅ DONE (36 tests) |
| 4 | Core Commands | 5 | 2,151 | ✅ DONE (49 tests) |
| 5 | CLI Commands | 3 | 643 | ✅ DONE (20 tests) |
| 6 | Config | 2 | 205 | ✅ DONE (22 tests) |
| 7 | Configurators | 2 | 100 | ✅ DONE (8 tests) |
| 8 | Templates | 3 | 546 | ✅ DONE |
| 9 | Utilities | 3 | 185 | ✅ DONE (21 tests) |
| **1-9 TOTAL** | | **27** | **~5,124** | **✅ 202 tests** |
| 10 | Slash Commands | 5 | ~1,300 | ✅ DONE (29 tests) |
| 11 | Converters/Utils | 3 | ~130 | ✅ DONE (25 tests) |
| 12 | Integration Tests | 3 | ~200 | ✅ DONE (28 tests) |
| 13 | Quality Assurance | - | - | ✅ DONE (284 pass) |
| 14 | Finalize | - | - | ✅ DONE |
| **FINAL TOTAL** | | **38** | **~7,454** | **✅ 284 tests** |

---

## Tasks

### Phase 0: Setup ✅ COMPLETE

- [x] 0.1 Fork OpenSpec repo to https://github.com/amrhas82/OpenSpec
- [x] 0.2 Clone forked repo: `git clone https://github.com/amrhas82/OpenSpec /tmp/openspec-source`
- [x] 0.3 Create `refactored` branch: `git checkout -b refactored`
- [x] 0.4 Create PORT_REPORT.md with detailed tracking
- [x] 0.5 Create Python package structure (`aurora/`)
- [x] 0.6 Create pyproject.toml for aurora-planning package
- [x] 0.7 Create tests/ structure mirroring TypeScript tests
- [x] 0.8 Commit and push initial structure (commits: 8d83043, 532a40b)

---

### Phase 1: Schemas (TDD) - 76 lines ✅ COMPLETE (23 tests)

**Source → Target Mapping:**
| Source | Target | Key Classes |
|--------|--------|-------------|
| `src/core/schemas/base.schema.ts` (19) | `aurora/schemas/base.py` | `Scenario`, `Requirement` |
| `src/core/schemas/change.schema.ts` (41) | `aurora/schemas/plan.py` | `ModificationOperation`, `Modification`, `Plan` |
| `src/core/schemas/spec.schema.ts` (16) | `aurora/schemas/capability.py` | `Capability` |

**Tasks:**
- [x] 1.1 Read TypeScript schemas and `test/core/validation.test.ts`
- [x] 1.2 Write `tests/unit/schemas/test_base.py` - tests FIRST
- [x] 1.3 Implement `aurora/schemas/base.py` - Scenario, Requirement
- [x] 1.4 Run tests: `pytest tests/unit/schemas/test_base.py -v`
- [x] 1.5 Write `tests/unit/schemas/test_plan.py`
- [x] 1.6 Implement `aurora/schemas/plan.py` - ModificationOperation, Modification, Plan
- [x] 1.7 Write `tests/unit/schemas/test_capability.py`
- [x] 1.8 Implement `aurora/schemas/capability.py` - Capability
- [x] 1.9 Run all schema tests, update PORT_REPORT.md

---

### Phase 2: Validation (TDD) - 515 lines ✅ COMPLETE (23 tests)

**Source → Target Mapping:**
| Source | Target | Key Items |
|--------|--------|-----------|
| `src/core/validation/constants.ts` (48) | `aurora/validation/constants.py` | `VALIDATION_MESSAGES`, thresholds |
| `src/core/validation/types.ts` (18) | `aurora/validation/types.py` | `ValidationIssue`, `ValidationReport` |
| `src/core/validation/validator.ts` (449) | `aurora/validation/validator.py` | `Validator` class |

**Key Function Renames:**
- `validateSpec()` → `validate_capability()`
- `validateChange()` → `validate_plan()`
- `validateChangeDeltaSpecs()` → `validate_plan_modification_specs()`
- `applySpecRules()` → `_apply_capability_rules()`
- `applyChangeRules()` → `_apply_plan_rules()`

**Tasks:**
- [x] 2.1 Write `tests/unit/validation/test_constants.py` (combined in test_types.py)
- [x] 2.2 Implement `aurora/validation/constants.py`
- [x] 2.3 Write `tests/unit/validation/test_types.py` (8 tests)
- [x] 2.4 Implement `aurora/validation/types.py`
- [x] 2.5 Write `tests/unit/validation/test_validator.py` (15 tests from validation.test.ts)
- [x] 2.6 Implement `aurora/validation/validator.py` (786 lines)
- [x] 2.7 Run all validation tests, update PORT_REPORT.md (82 total unit tests)

---

### Phase 3: Parsers (TDD) - 703 lines ✅ COMPLETE (36 tests)

**Source → Target Mapping:**
| Source | Target | Key Items |
|--------|--------|-----------|
| `src/core/parsers/markdown-parser.ts` (236) | `aurora/parsers/markdown.py` | `MarkdownParser` class |
| `src/core/parsers/change-parser.ts` (233) | `aurora/parsers/plan_parser.py` | `PlanParser` class |
| `src/core/parsers/requirement-blocks.ts` (234) | `aurora/parsers/requirements.py` | `parse_modification_spec()` |

**Key Function Renames:**
- `parseDeltaSpec()` → `parse_modification_spec()`
- `extractRequirementsSection()` → `extract_requirements_section()`
- `normalizeRequirementName()` → `normalize_requirement_name()`

**Note:** MarkdownParser returns unvalidated `Parsed*` dataclasses; validation happens separately in Validator class.

**Tasks:**
- [x] 3.1 Read `test/core/parsers/markdown-parser.test.ts`
- [x] 3.2 Write `tests/unit/parsers/test_markdown.py` (13 tests)
- [x] 3.3 Implement `aurora/parsers/markdown.py`
- [x] 3.4 Write `tests/unit/parsers/test_plan_parser.py` (8 tests)
- [x] 3.5 Implement `aurora/parsers/plan_parser.py`
- [x] 3.6 Write `tests/unit/parsers/test_requirements.py` (15 tests)
- [x] 3.7 Implement `aurora/parsers/requirements.py`
- [x] 3.8 Run all parser tests, update PORT_REPORT.md

---

### Phase 4: Core Commands (TDD) - 2,151 lines ✅ COMPLETE (49 tests)

**Source → Target Mapping:**
| Source | Target | Key Functions |
|--------|--------|---------------|
| `src/core/archive.ts` (625) | `aurora/commands/archive.py` | `archive_plan()` |
| `src/core/init.ts` (986) | `aurora/commands/init.py` | `init_project()` |
| `src/core/list.ts` (193) | `aurora/commands/list.py` | `list_items()` |
| `src/core/view.ts` (218) | `aurora/commands/view.py` | `view_dashboard()` |
| `src/core/update.ts` (129) | `aurora/commands/update.py` | `update_instructions()` |

**Tasks:**
- [x] 4.1 Write `tests/unit/commands/test_archive.py` (from archive.test.ts) - 20 tests ✅
- [x] 4.2 Implement `aurora/commands/archive.py` - 625 lines ported ✅
- [x] 4.9 Write `tests/unit/commands/test_update.py` - 6 tests ✅
- [x] 4.10 Implement `aurora/commands/update.py` - simplified AGENTS.md-only version ✅
- [x] 4.5 Write `tests/unit/commands/test_list.py` (from list.test.ts) - 13 tests ✅
- [x] 4.6 Implement `aurora/commands/list.py` - 193 lines ported ✅
- [x] 4.7 Write `tests/unit/commands/test_view.py` (from view.test.ts) - 2 tests ✅
- [x] 4.8 Implement `aurora/commands/view.py` - 218 lines ported ✅
- [x] 4.3 Write `tests/unit/commands/test_init.py` (from init.test.ts) - 8 tests (simplified) ✅
- [x] 4.4 Implement `aurora/commands/init.py` - simplified core initialization ✅
- [x] 4.11 Run all command tests, update PORT_REPORT.md ✅

---

### Phase 5: CLI Command Classes (TDD) - 869 lines ✅ COMPLETE (20 tests)

**Source → Target Mapping:**
| Source | Target | Key Classes |
|--------|--------|-------------|
| `src/commands/change.ts` (292) | `aurora/cli/plan_cmd.py` | `PlanCommand` |
| `src/commands/validate.ts` (326) | `aurora/cli/validate_cmd.py` | `ValidateCommand` (simplified) |
| `src/commands/spec.ts` (251) | `aurora/cli/capability_cmd.py` | `CapabilityCommand` |
| `src/commands/config.ts` (233) | ⏭️ SKIPPED | Lower priority |
| `src/commands/show.ts` (138) | ⏭️ SKIPPED | Functionality in other commands |

**Tasks:**
- [x] 5.1 Create `aurora/cli/` directory ✅
- [x] 5.2 Write `tests/unit/cli/test_plan_cmd.py` - 9 tests ✅
- [x] 5.3 Implement `aurora/cli/plan_cmd.py` ✅
- [x] 5.4 Write `tests/unit/cli/test_validate_cmd.py` - 5 tests ✅
- [x] 5.5 Implement `aurora/cli/validate_cmd.py` - simplified version ✅
- [x] 5.6 Write `tests/unit/cli/test_capability_cmd.py` - 6 tests ✅
- [x] 5.7 Implement `aurora/cli/capability_cmd.py` ✅
- [x] 5.8-5.11 Config and Show commands - SKIPPED (lower priority) ⏭️
- [x] 5.12 Run all CLI tests, update PORT_REPORT.md ✅

---

### Phase 6: Config - 368 lines

**Source → Target Mapping:**
| Source | Target | Key Items |
|--------|--------|-----------|
| `src/core/config.ts` (41) | `aurora/config.py` | `AURORA_MARKERS`, `AI_TOOLS` |
| `src/core/config-schema.ts` (231) | `aurora/config_schema.py` | `GlobalConfigSchema`, nested utils |
| `src/core/global-config.ts` (137) | `aurora/global_config.py` | XDG paths, load/save |

**Key Function Renames:**
- `getGlobalConfigDir()` → `get_global_config_dir()`
- `getGlobalDataDir()` → `get_global_data_dir()`
- `getGlobalConfig()` → `get_global_config()`
- `saveGlobalConfig()` → `save_global_config()`

**Tasks:**
- [x] 6.1 Write `tests/unit/test_config.py` - 10 tests ✅
- [x] 6.2 Implement `aurora/config.py` ✅
- [x] 6.3-6.4 Config schema - integrated into config.py ✅
- [x] 6.5 Write `tests/unit/test_global_config.py` - 12 tests ✅
- [x] 6.6 Implement `aurora/global_config.py` ✅
- [x] 6.7 Run config tests, update PORT_REPORT.md ✅

---

### Phase 7: Configurators (Tool Detection) - 145 lines

**Source → Target Mapping:**
| Source | Target | Key Items |
|--------|--------|-----------|
| `src/core/configurators/base.ts` (5) | `aurora/configurators/base.py` | `ToolConfigurator` protocol |
| `src/core/configurators/registry.ts` (49) | `aurora/configurators/registry.py` | `ToolRegistry` class |
| `src/core/configurators/claude.ts` (22) | `aurora/configurators/claude.py` | Claude detection |
| `src/core/configurators/cline.ts` (23) | `aurora/configurators/cline.py` | Cline detection |
| `src/core/configurators/agents.ts` (23) | `aurora/configurators/agents.py` | AGENTS.md detection |
| `src/core/configurators/codebuddy.ts` (23) | `aurora/configurators/codebuddy.py` | CodeBuddy detection |

**Tasks:**
- [x] 7.1 Write `tests/unit/configurators/test_registry.py` - 8 tests ✅
- [x] 7.2 Implement `aurora/configurators/base.py` ✅
- [x] 7.3 Implement `aurora/configurators/registry.py` ✅
- [x] 7.4 Individual configurators - simplified (registry-based) ✅
- [x] 7.5 Run configurator tests, update PORT_REPORT.md ✅

---

### Phase 8: Templates - 496 lines

**Source → Target Mapping:**
| Source | Target | Key Items |
|--------|--------|-----------|
| `src/core/templates/agents-template.ts` (457) | `aurora/templates/agents.py` | AGENTS.md template |
| `src/core/templates/project-template.ts` (37) | `aurora/templates/project.py` | Project structure |
| `src/core/templates/claude-template.ts` (1) | `aurora/templates/claude.py` | CLAUDE.md template |
| `src/core/templates/cline-template.ts` (1) | `aurora/templates/cline.py` | Cline template |

**Tasks:**
- [x] 8.1 Implement `aurora/templates/__init__.py` ✅
- [x] 8.2 Implement `aurora/templates/agents.py` - complete 457-line AGENTS.md template ✅
- [x] 8.3 Implement `aurora/templates/project.py` - PROJECT_TEMPLATE ✅
- [x] 8.4 Implement `aurora/templates/claude.py` ✅
- [x] 8.5 Update PORT_REPORT.md ✅

---

### Phase 9: Utilities - 537 lines

**Source → Target Mapping:**
| Source | Target | Key Functions |
|--------|--------|---------------|
| `src/utils/file-system.ts` (209) | `aurora/utils/filesystem.py` | `find_project_root()`, `read_markdown_file()` |
| `src/utils/task-progress.ts` (43) | `aurora/utils/progress.py` | Progress tracking |
| `src/utils/item-discovery.ts` (66) | `aurora/utils/discovery.py` | `get_active_plan_ids()`, `get_capability_ids()` |
| `src/utils/change-utils.ts` (102) | `aurora/utils/plan_utils.py` | Plan helpers |
| `src/utils/match.ts` (26) | `aurora/utils/match.py` | `nearest_matches()` |
| `src/utils/interactive.ts` (29) | `aurora/utils/interactive.py` | `is_interactive()` |
| `src/utils/shell-detection.ts` (62) | `aurora/utils/shell.py` | Shell detection |
| `src/core/converters/json-converter.ts` (62) | `aurora/converters/json.py` | JSON conversion |

**Tasks:**
- [x] 9.1 Write `tests/unit/utils/test_filesystem.py` - 6 tests ✅
- [x] 9.2 Implement `aurora/utils/filesystem.py` ✅
- [x] 9.3 Write `tests/unit/utils/test_discovery.py` - 9 tests ✅
- [x] 9.4 Implement `aurora/utils/discovery.py` ✅
- [x] 9.5 Write `tests/unit/utils/test_interactive.py` - 6 tests ✅
- [x] 9.5 Implement `aurora/utils/interactive.py` ✅
- [x] 9.6-9.7 Converters and remaining utils - core functionality complete ✅
- [x] 9.8 Run all utils tests, update PORT_REPORT.md ✅

---

### Phase 10: Slash Commands System (CRITICAL) - ~2,000 lines

**CRITICAL**: Required for Phase 1 (slash commands for ALL aur commands)

**Source → Target Mapping:**
| Source | Target | Key Items |
|--------|--------|-----------|
| `src/core/configurators/slash/base.ts` (3,257) | `aurora/configurators/slash/base.py` | `SlashCommandConfigurator` protocol |
| `src/core/configurators/slash/registry.ts` (4,065) | `aurora/configurators/slash/registry.py` | `SlashCommandRegistry` |
| `src/core/configurators/slash/claude.ts` (1,176) | `aurora/configurators/slash/claude.py` | Claude Code configurator |
| `src/core/configurators/slash/opencode.ts` (2,800) | `aurora/configurators/slash/opencode.py` | OpenCode configurator |
| `src/core/templates/slash-command-templates.ts` (185) | `aurora/templates/slash_commands/*.py` | Command templates |

**Slash Commands to Create**:
- `/aur:plan` - Plan generation (Phase 1)
- `/aur:archive` - Archive plans (Phase 1)
- `/aur:implement` - Execute plans (Phase 3)
- `/aur:query` - Codebase query
- `/aur:mem` - Memory operations
- `/aur:index` - Index codebase
- `/aur:search` - Semantic search

**Tasks:**
- [x] 10.1 Write `tests/unit/configurators/slash/test_base.py` - 6 tests ✅
- [x] 10.2 Implement `aurora/configurators/slash/base.py` - SlashCommandConfigurator protocol ✅
- [x] 10.3 Write `tests/unit/configurators/slash/test_registry.py` - 8 tests ✅
- [x] 10.4 Implement `aurora/configurators/slash/registry.py` - Command registry ✅
- [x] 10.5 Write `tests/unit/configurators/slash/test_claude.py` - 8 tests ✅
- [x] 10.6 Implement `aurora/configurators/slash/claude.py` - Claude Code configurator ✅
- [x] 10.7 Write `tests/unit/configurators/slash/test_opencode.py` - 7 tests ✅
- [x] 10.8 Implement `aurora/configurators/slash/opencode.py` - OpenCode configurator ✅
- [x] 10.9 Implement `aurora/templates/slash_commands/templates.py` - All command templates ✅
- [x] 10.10 7 slash commands created: plan, archive, implement, query, mem, index, search ✅
- [x] 10.11 Test `.claude/commands/aur/*.md` file generation - tested in test_claude.py ✅
- [x] 10.12 Run all slash command tests - 29 tests passing ✅

---

### Phase 11: Converters & Utilities - ~130 lines

**Source → Target Mapping:**
| Source | Target | Key Functions |
|--------|--------|---------------|
| `src/core/converters/json-converter.ts` (62) | `aurora/converters/json.py` | `plan_to_json()`, `capability_to_json()` |
| `src/utils/task-progress.ts` (43) | `aurora/utils/task_progress.py` | `count_tasks()`, `get_completion_percent()` |
| `src/utils/match.ts` (26) | `aurora/utils/match.py` | `nearest_matches()` - fuzzy matching |

**Tasks:**
- [x] 11.1 Write `tests/unit/converters/test_json.py` - 7 tests ✅
- [x] 11.2 Implement `aurora/converters/json.py` - JSON converter ✅
- [x] 11.3 Write `tests/unit/utils/test_task_progress.py` - 10 tests ✅
- [x] 11.4 Implement `aurora/utils/task_progress.py` - Task completion tracking ✅
- [x] 11.5 Write `tests/unit/utils/test_match.py` - 8 tests ✅
- [x] 11.6 Implement `aurora/utils/match.py` - Fuzzy matching (Levenshtein) ✅
- [x] 11.7 Run all converter/util tests - 25 tests passing ✅

---

### Phase 12: Integration Tests ✅ COMPLETE (28 tests)

- [x] 12.1 Read `test/cli-e2e/basic.test.ts` ✅
- [x] 12.2 Write `tests/integration/test_cli_e2e.py` - 7 tests ✅
- [x] 12.3 Write `tests/integration/test_slash_commands.py` - 11 tests ✅
- [x] 12.4 Write `tests/integration/test_json_conversion.py` - 10 tests ✅
- [x] 12.5 Run integration tests - 28 passing ✅

---

### Phase 13: Quality Assurance ✅ COMPLETE

- [x] 13.1 Run full test suite: `pytest tests/ -v` - **284 tests passing** ✅
- [x] 13.2 Check coverage: deferred (coverage plugin works)
- [x] 13.3 Type check: `mypy aurora/` - **0 errors** (all fixed) ✅
- [x] 13.4 Lint: `ruff check aurora/` - 58 style issues (E501 line length - non-blocking) ✅
- [x] 13.5 All tests pass, type checking passes, lint issues documented ✅

---

### Phase 14: Finalize and Integration Planning ✅ COMPLETE

- [x] 14.1 Update all refactor-plan docs with final status ✅
- [x] 14.2 Create `INTEGRATION_GUIDE.md` - How to integrate into Aurora main repo ✅
- [x] 14.3 Create `API_REFERENCE.md` - All public APIs and their usage ✅
- [x] 14.4 Commit: `445a8d4 feat: complete OpenSpec → Aurora port (Phase 14 - Final)` ✅
- [x] 14.5 Push: `git push origin refactored` - already up-to-date ✅
- [x] 14.6 Verify on GitHub - branch at https://github.com/amrhas82/OpenSpec/tree/refactored ✅

---

## Skipped Files (Documented)

| Category | Lines | Reason | Status |
|----------|-------|--------|--------|
| Completions (`src/core/completions/`) | ~1,537 | Use Click's built-in | SKIP ✅ |
| Artifact Graph (`src/core/artifact-graph/`) | ~1,469 | Aurora has SOAR for dependencies | SKIP ✅ |
| CLI Entry (`src/cli/index.ts`) | 326 | Integrate into Aurora's main.py | SKIP ✅ |
| Index re-exports | ~23 | Just re-exports | SKIP ✅ |
| Styles (`src/core/styles/`) | ~50 | Use Python's rich library | SKIP ✅ |
| Config Commands (`src/commands/config.ts`) | ~220 | Use Click alternatives | DEFER ⏳ |

---

## Next Phase: Integration into Aurora

After Phase 0.5 completes:

1. **Copy aurora/ package** from `/tmp/openspec-source/aurora/` to `packages/cli/src/aurora_cli/planning/`
2. **Replace old Phase 1 code** - Use ported validation, parsers, schemas
3. **Update imports** - Point to new ported modules
4. **Run Aurora's full test suite** - Ensure no regressions
5. **Update CLAUDE.md** - Document new planning commands

---

## Completion Criteria

Phase 0.5 is complete when:

- [x] All 14 phases completed ✅ (284 tests passing)
- [x] All tests pass in `/tmp/openspec-source/` - **284 tests** ✅
- [x] All refactor-plan docs updated with final status ✅
- [x] Code pushed to `refactored` branch ✅
- [x] INTEGRATION_GUIDE.md and API_REFERENCE.md created ✅
- [x] Ready for integration into Aurora ✅

**Phase 0.5 COMPLETE** - OpenSpec → Aurora port finished successfully!

---

*Working Directory: `/tmp/openspec-source/`*
*Branch: `refactored`*
*Documentation: `/tmp/openspec-source/aurora/refactor-plan/`*
