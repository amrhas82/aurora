# Phase 0.5: OpenSpec → Aurora Port (Comprehensive)

**PRD Reference**: `/home/hamr/PycharmProjects/aurora/tasks/0017-prd-aurora-planning-system.md` Section 11
**Phase**: 0.5 (Pre-requisite for revised Phase 1-3)
**Status**: In Progress
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
| 4 | Core Commands | 5 | 2,151 | 🔲 TODO |
| 5 | CLI Commands | 5 | 1,240 | 🔲 TODO |
| 6 | Config | 3 | 368 | 🔲 TODO |
| 7 | Configurators | 6 | 145 | 🔲 TODO |
| 8 | Templates | 4 | 496 | 🔲 TODO |
| 9 | Utilities | 8 | 537 | 🔲 TODO |
| **TOTAL** | | **40** | **~5,800** | |

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

### Phase 4: Core Commands (TDD) - 2,151 lines

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
- [ ] 4.3 Write `tests/unit/commands/test_init.py`
- [ ] 4.4 Implement `aurora/commands/init.py`
- [ ] 4.7 Write `tests/unit/commands/test_view.py`
- [ ] 4.8 Implement `aurora/commands/view.py`
- [ ] 4.11 Run all command tests, update PORT_REPORT.md

---

### Phase 5: CLI Command Classes (TDD) - 1,240 lines

**Source → Target Mapping:**
| Source | Target | Key Classes |
|--------|--------|-------------|
| `src/commands/change.ts` (292) | `aurora/cli/plan_cmd.py` | `PlanCommand` |
| `src/commands/validate.ts` (326) | `aurora/cli/validate_cmd.py` | `ValidateCommand` |
| `src/commands/spec.ts` (251) | `aurora/cli/capability_cmd.py` | `CapabilityCommand` |
| `src/commands/config.ts` (233) | `aurora/cli/config_cmd.py` | `ConfigCommand` |
| `src/commands/show.ts` (138) | `aurora/cli/show_cmd.py` | `ShowCommand` |

**Tasks:**
- [ ] 5.1 Create `aurora/cli/` directory
- [ ] 5.2 Write `tests/unit/cli/test_plan_cmd.py`
- [ ] 5.3 Implement `aurora/cli/plan_cmd.py`
- [ ] 5.4 Write `tests/unit/cli/test_validate_cmd.py`
- [ ] 5.5 Implement `aurora/cli/validate_cmd.py`
- [ ] 5.6 Write `tests/unit/cli/test_capability_cmd.py`
- [ ] 5.7 Implement `aurora/cli/capability_cmd.py`
- [ ] 5.8 Write `tests/unit/cli/test_config_cmd.py`
- [ ] 5.9 Implement `aurora/cli/config_cmd.py`
- [ ] 5.10 Write `tests/unit/cli/test_show_cmd.py`
- [ ] 5.11 Implement `aurora/cli/show_cmd.py`
- [ ] 5.12 Run all CLI tests, update PORT_REPORT.md

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
- [ ] 6.1 Write `tests/unit/test_config.py`
- [ ] 6.2 Implement `aurora/config.py`
- [ ] 6.3 Write `tests/unit/test_config_schema.py`
- [ ] 6.4 Implement `aurora/config_schema.py`
- [ ] 6.5 Write `tests/unit/test_global_config.py`
- [ ] 6.6 Implement `aurora/global_config.py`
- [ ] 6.7 Run config tests, update PORT_REPORT.md

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
- [ ] 7.1 Write `tests/unit/configurators/test_registry.py`
- [ ] 7.2 Implement `aurora/configurators/base.py`
- [ ] 7.3 Implement `aurora/configurators/registry.py`
- [ ] 7.4 Implement individual configurators (claude, cline, agents, etc.)
- [ ] 7.5 Run configurator tests, update PORT_REPORT.md

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
- [ ] 8.3 Implement `aurora/templates/project.py`
- [ ] 8.4 Implement `aurora/templates/claude.py`
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
- [ ] 9.1 Write `tests/unit/utils/test_filesystem.py`
- [ ] 9.2 Implement `aurora/utils/filesystem.py`
- [ ] 9.3 Write `tests/unit/utils/test_discovery.py`
- [ ] 9.4 Implement `aurora/utils/discovery.py`
- [ ] 9.5 Implement remaining utils (progress, plan_utils, match, interactive, shell)
- [ ] 9.6 Write `tests/unit/converters/test_json.py`
- [ ] 9.7 Implement `aurora/converters/json.py`
- [ ] 9.8 Run all utils tests, update PORT_REPORT.md

---

### Phase 10: Integration Tests

- [ ] 10.1 Read `test/cli-e2e/basic.test.ts`
- [ ] 10.2 Write `tests/integration/test_cli_e2e.py`
- [ ] 10.3 Run integration tests

---

### Phase 11: Quality Assurance

- [ ] 11.1 Run full test suite: `pytest tests/ -v`
- [ ] 11.2 Check coverage: `pytest --cov=aurora tests/`
- [ ] 11.3 Type check: `mypy aurora/`
- [ ] 11.4 Lint: `ruff check aurora/`
- [ ] 11.5 Ensure all pass

---

### Phase 12: Finalize and Push

- [ ] 12.1 Update PORT_REPORT.md with all ✅ status
- [ ] 12.2 Commit: `git add . && git commit -m "Complete OpenSpec → Aurora port"`
- [ ] 12.3 Push: `git push origin refactored`
- [ ] 12.4 Verify on GitHub

---

## Skipped Files (Documented)

| Category | Lines | Reason |
|----------|-------|--------|
| Completions (`src/core/completions/`) | ~1,537 | Use Click's built-in |
| Artifact Graph (`src/core/artifact-graph/`) | ~1,469 | Experimental, Aurora has SOAR |
| Slash Configurators (`src/core/configurators/slash/`) | ~1,500 | Tool-specific, port later if needed |
| CLI Entry (`src/cli/index.ts`) | 326 | Integrate into Aurora's main.py |
| Index re-exports | ~23 | Just re-exports |

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

- [ ] All 12 phases completed
- [ ] All tests pass in `/tmp/openspec-source/`
- [ ] PORT_REPORT.md shows all ported modules as ✅
- [ ] Code pushed to `refactored` branch
- [ ] Ready for integration into Aurora

---

*Working Directory: `/tmp/openspec-source/`*
*Branch: `refactored`*
*Report: `/tmp/openspec-source/PORT_REPORT.md`*
