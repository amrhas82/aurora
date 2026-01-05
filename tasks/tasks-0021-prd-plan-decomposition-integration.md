# Task List: PRD 0021 - Plan Decomposition & Integration

**PRD**: `/home/hamr/PycharmProjects/aurora/tasks/0021-prd-plan-decomposition-integration.md`
**Generated**: 2026-01-05
**Status**: Complete - Ready for Implementation
**Methodology**: TDD (Test-Driven Development)

---

## Relevant Files

### New Files to Create

- `packages/cli/src/aurora_cli/planning/commands/__init__.py` - Package init for commands submodule
- `packages/cli/src/aurora_cli/planning/commands/archive.py` - Ported ArchiveCommand from OpenSpec
- `packages/cli/src/aurora_cli/planning/decompose.py` - PlanDecomposer class orchestrating SOAR + Memory + AgentDiscovery
- `packages/cli/src/aurora_cli/planning/memory.py` - FilePathResolver wrapping MemoryRetriever
- `packages/cli/src/aurora_cli/planning/agents.py` - AgentRecommender wrapping AgentManifest

### Files to Modify

- `packages/cli/src/aurora_cli/planning/core.py` - Integrate PlanDecomposer, add checkpoint flow
- `packages/cli/src/aurora_cli/planning/models.py` - Add DecompositionSummary, FileResolution, AgentGap models
- `packages/cli/src/aurora_cli/planning/renderer.py` - Update templates context for enhanced file generation
- `packages/cli/src/aurora_cli/planning/results.py` - Add DecomposeResult type
- `packages/cli/src/aurora_cli/planning/validation/types.py` - Port validation types from OpenSpec
- `packages/cli/src/aurora_cli/planning/validation/validator.py` - Port validator from OpenSpec
- `packages/cli/src/aurora_cli/planning/validation/constants.py` - Port validation constants from OpenSpec
- `packages/cli/src/aurora_cli/planning/parsers/requirements.py` - Port requirements parser from OpenSpec
- `packages/cli/src/aurora_cli/planning/templates/tasks.md.j2` - Add file paths with confidence
- `packages/cli/src/aurora_cli/planning/templates/agents.json.j2` - Add gaps, file_resolutions, decomposition_source
- `packages/cli/src/aurora_cli/planning/templates/plan.md.j2` - Add ASCII dependency graph

### Test Files Created

- `tests/unit/cli/planning/validation/test_types.py` - Unit tests for validation types (18 tests, all passing)
- `tests/unit/cli/planning/validation/test_constants.py` - Unit tests for validation constants (12 tests, all passing)

### Test Files to Create

- `tests/unit/cli/planning/test_archive_command.py` - Unit tests for ArchiveCommand (port from OpenSpec)
- `tests/unit/cli/planning/test_decompose.py` - Unit tests for PlanDecomposer
- `tests/unit/cli/planning/test_file_path_resolver.py` - Unit tests for FilePathResolver
- `tests/unit/cli/planning/test_agent_recommender.py` - Unit tests for AgentRecommender
- `tests/unit/cli/planning/test_checkpoint.py` - Unit tests for user checkpoint flow
- `tests/unit/cli/planning/test_enhanced_generation.py` - Unit tests for enhanced file generation
- `tests/integration/cli/test_plan_decomposition_e2e.py` - End-to-end integration tests

### Source Files for Porting (Reference Only)

- `/home/hamr/PycharmProjects/aurora/openspec-source/aurora/commands/archive.py` - ArchiveCommand source (638 lines)
- `/home/hamr/PycharmProjects/aurora/openspec-source/aurora/parsers/requirements.py` - Requirements parser (412 lines)
- `/home/hamr/PycharmProjects/aurora/openspec-source/aurora/validation/validator.py` - Validator (783 lines)
- `/home/hamr/PycharmProjects/aurora/openspec-source/aurora/validation/types.py` - Validation types (59 lines)
- `/home/hamr/PycharmProjects/aurora/openspec-source/aurora/validation/constants.py` - Validation constants
- `/home/hamr/PycharmProjects/aurora/openspec-source/tests/unit/commands/test_archive.py` - Archive tests (771 lines)

### Notes

- **Testing Framework**: pytest with fixtures, Click CliRunner for CLI tests
- **TDD Workflow**: Write failing test first, implement to make green, refactor
- **Port Strategy**: Copy-paste from OpenSpec, update imports and paths, verify tests pass
- **Path Mappings**:
  - `openspec/changes/` -> `.aurora/plans/active/`
  - `openspec/changes/archive/` -> `.aurora/plans/archive/`
  - `openspec/specs/` -> `.aurora/capabilities/`
- **Import Mappings**:
  - `from aurora.parsers.requirements import ...` -> `from aurora_cli.planning.parsers.requirements import ...`
  - `from aurora.validation.validator import ...` -> `from aurora_cli.planning.validation.validator import ...`
- **Performance Targets**: Decomposition <10s, Retrieval <2s/subgoal, Checkpoint <100ms, Archive <3s

---

## Tasks

- [ ] 1.0 Port Archive Command from OpenSpec with Aurora Path Conventions (DEFERRED - Independent of core integration work)
  - [x] 1.1 Port validation types module from OpenSpec
    - Copy `/home/hamr/PycharmProjects/aurora/openspec-source/aurora/validation/types.py` to `packages/cli/src/aurora_cli/planning/validation/types.py`
    - Verify `ValidationLevel`, `ValidationIssue`, `ValidationSummary`, `ValidationReport` classes exist
    - Update imports to use `pydantic` (already compatible)
    - No path changes needed for this module
    - **Test**: Create `tests/unit/cli/planning/validation/test_types.py` with model validation tests
  - [x] 1.2 Port validation constants from OpenSpec
    - Copy constants from `/home/hamr/PycharmProjects/aurora/openspec-source/aurora/validation/constants.py`
    - Update any OpenSpec-specific error messages to Aurora terminology
    - Add new constants for Aurora-specific validation (e.g., `PLANS_DIR_NOT_FOUND`)
    - **Test**: Verify constants are importable and have expected values
  - [x] 1.3 Port requirements parser module from OpenSpec
    - Copy `/home/hamr/PycharmProjects/aurora/openspec-source/aurora/parsers/requirements.py` (412 lines) to `packages/cli/src/aurora_cli/planning/parsers/requirements.py`
    - Port dataclasses: `RequirementBlock`, `RequirementsSectionParts`, `ModificationPlan`
    - Port functions: `normalize_requirement_name`, `extract_requirements_section`, `parse_modification_spec`
    - Port internal helpers: `_normalize_line_endings`, `_split_top_level_sections`, `_get_section_case_insensitive`, `_parse_requirement_blocks_from_section`, `_parse_removed_names`, `_parse_renamed_pairs`
    - No import changes needed (pure Python, no external dependencies)
    - **Test**: Port tests from `openspec-source/tests/unit/parsers/test_requirements.py`
  - [x] 1.4 Port Validator class from OpenSpec
    - Copy `/home/hamr/PycharmProjects/aurora/openspec-source/aurora/validation/validator.py` (783 lines) to `packages/cli/src/aurora_cli/planning/validation/validator.py`
    - Update imports: `from aurora.parsers...` -> `from aurora_cli.planning.parsers...`
    - Update imports: `from aurora.validation...` -> `from aurora_cli.planning.validation...`
    - Keep all validation methods: `validate_capability`, `validate_capability_content`, `validate_plan`, `validate_plan_modification_specs`
    - **Test**: Port tests from `openspec-source/tests/unit/validation/test_validator.py`
  - [x] 1.5 Create commands submodule and port ArchiveCommand structure
    - Create `packages/cli/src/aurora_cli/planning/commands/__init__.py` with `__all__ = ["ArchiveCommand"]`
    - Copy `/home/hamr/PycharmProjects/aurora/openspec-source/aurora/commands/archive.py` (638 lines) to `packages/cli/src/aurora_cli/planning/commands/archive.py`
    - Update imports at top of file:
      - `from aurora.parsers.requirements import ...` -> `from aurora_cli.planning.parsers.requirements import ...`
      - `from aurora.validation.validator import Validator` -> `from aurora_cli.planning.validation.validator import Validator`
    - Keep `SpecUpdate` and `OperationCounts` dataclasses unchanged
    - **Test**: Write basic import test to verify module structure
  - [x] 1.6 Update ArchiveCommand path conventions for Aurora
    - Change `target / "openspec" / "changes"` to `target / ".aurora" / "plans" / "active"`
    - Change `target / "openspec" / "changes" / "archive"` to `target / ".aurora" / "plans" / "archive"`
    - Change `target / "openspec" / "specs"` to `target / ".aurora" / "capabilities"`
    - Update error message: `"No OpenSpec changes directory found"` -> `"No Aurora plans directory found. Run 'aur plan init' first."`
    - Update `_build_spec_skeleton` method to use Aurora terminology
    - **Test**: Write test verifying correct Aurora paths are used
  - [x] 1.7 Implement FR-1.1: Task completion validation
    - Verify `_get_task_progress()` method correctly parses `tasks.md` checkboxes (`- [x]`, `- [ ]`, `- [X]`)
    - Verify `_format_task_status()` returns "X/Y (Z%)" format
    - Ensure warning is displayed when tasks incomplete
    - Ensure `--yes` flag suppresses confirmation prompt for incomplete tasks
    - **Test**: `test_warn_about_incomplete_tasks`, `test_handle_changes_without_tasks` (port from OpenSpec)
  - [x] 1.8 Implement FR-1.2: Spec delta processing
    - Verify `_find_spec_updates()` scans `<plan-dir>/specs/` for delta files
    - Verify `_build_updated_spec()` handles ADDED, MODIFIED, REMOVED, RENAMED sections
    - Verify duplicate detection within sections
    - Verify cross-section conflict detection
    - Verify atomic operation (all or nothing) via prepared list pattern
    - Verify `--skip-specs` flag bypasses this step
    - Update output paths to use `.aurora/capabilities/<capability>/spec.md`
    - **Test**: Port `test_update_specs_with_added_requirements`, `test_operations_applied_in_order`, `test_multiple_specs_atomic`, `test_aggregated_totals_across_multiple_specs`
  - [ ] 1.9 Implement FR-1.3: Atomic move operation
    - Verify `_get_archive_date()` returns `YYYY-MM-DD` format
    - Verify archive directory name is `YYYY-MM-DD-<plan-id>`
    - Verify atomic move via `Path.rename()` operation
    - Add rollback logic: if move fails, restore original agents.json
    - Update `agents.json` with `archived_at` timestamp before move
    - **Test**: `test_archive_change_successfully`, `test_error_if_archive_already_exists`
  - [ ] 1.10 Implement FR-1.4: Interactive plan selection
    - Verify `_select_plan()` lists directories in `.aurora/plans/active/` excluding `archive/`
    - Verify plans are sorted alphabetically
    - Verify progress shown as "X/Y (Z%)" or "No tasks"
    - Verify numbered selection prompt accepts valid input
    - Verify invalid input prompts for retry
    - Verify empty directory shows message and returns None
    - Verify Ctrl+C handling (KeyboardInterrupt)
    - **Test**: `test_interactive_change_selection`, test with empty directory
  - [ ] 1.11 Implement FR-1.5: Archive command flags
    - Verify `--yes` / `-y` flag skips all confirmation prompts
    - Verify `--skip-specs` flag skips spec delta processing
    - Verify `--no-validate` flag skips validation with warning
    - Verify `validate=False` parameter works same as `--no-validate`
    - Verify flags can be combined (e.g., `--yes --skip-specs`)
    - Update help text for Aurora CLI
    - **Test**: `test_skip_specs_flag`, `test_skip_validation_with_no_validate_flag`
  - [ ] 1.12 Integrate ArchiveCommand with Aurora manifest system
    - After successful archive, call `_update_manifest(plans_dir, plan_id, "archive", archived_id)`
    - Ensure `PlanManifest` is updated correctly (active -> archived)
    - Add logging for archive operation
    - **Test**: Write test verifying manifest is updated after archive
  - [ ] 1.13 Port and adapt archive tests from OpenSpec
    - Create `tests/unit/cli/planning/test_archive_command.py`
    - Port all 25+ tests from `/home/hamr/PycharmProjects/aurora/openspec-source/tests/unit/commands/test_archive.py`
    - Update fixture `setup_openspec_structure` -> `setup_aurora_structure` with Aurora paths
    - Update assertions to use Aurora paths (`.aurora/plans/` instead of `openspec/changes/`)
    - Ensure all tests pass with updated paths
    - **Coverage Target**: >= 95% for archive.py

- [ ] 2.0 Integrate SOAR Decomposition into Planning Core
  - [x] 2.1 Create PlanDecomposer class skeleton with TDD
    - **Test First**: Create `tests/unit/cli/planning/test_decompose.py` with test class `TestPlanDecomposer`
    - Write failing test `test_decomposer_initialization` - verifies class can be instantiated with config
    - Create `packages/cli/src/aurora_cli/planning/decompose.py` with `PlanDecomposer` class
    - Add `__init__(self, config: Config | None = None)` method
    - Add placeholder methods: `decompose()`, `_build_context()`, `_call_soar()`, `_fallback_to_heuristics()`
    - Make test pass
  - [ ] 2.2 Implement FR-2.1: SOAR decompose_query integration
    - **Test First**: Write `test_decompose_with_soar_success` - mocks SOAR call, verifies subgoals returned
    - Import `decompose_query` from `aurora_soar.phases.decompose`
    - Implement `_call_soar()` method:
      - Build context dict with `code_chunks` and `reasoning_chunks`
      - Call `decompose_query(query, context, complexity, llm_client, available_agents)`
      - Convert `DecompositionResult` to list of `Subgoal` objects
      - Handle caching (same goal/complexity returns cached result)
    - **Test**: Write `test_decompose_soar_unavailable_fallback` - verifies fallback when ImportError
    - **Test**: Write `test_decompose_soar_timeout` - verifies 30s timeout handling
    - **Test**: Write `test_decompose_caching` - verifies cache hit returns immediately
  - [ ] 2.3 Implement FR-2.2: Context summary building
    - **Test First**: Write `test_build_context_summary_with_chunks` - verifies summary format
    - Implement `_build_context_summary()` using logic from `aurora_soar.phases.decompose._build_context_summary`
    - Return "Available code context: N code chunks..." when chunks available
    - Return "No indexed context available. Using LLM general knowledge." when no chunks
    - Limit summary to 500 characters
    - **Test**: Write `test_build_context_summary_empty` - verifies special message for empty context
  - [ ] 2.4 Implement FR-2.3: Available agents list
    - **Test First**: Write `test_load_available_agents` - mocks ManifestManager, verifies agent list
    - Load `AgentManifest` via `ManifestManager.get_or_refresh()`
    - Extract agent IDs from manifest: `[f"@{agent.id}" for agent in manifest.agents]`
    - Pass to `decompose_query()` as `available_agents` parameter
    - Handle manifest load failures gracefully (return None)
    - **Test**: Write `test_load_available_agents_manifest_unavailable` - verifies None returned on failure
  - [ ] 2.5 Implement FR-2.4: Complexity assessment from SOAR
    - **Test First**: Write `test_complexity_mapping` - verifies SOAR levels map to Complexity enum
    - Extract complexity from `DecompositionResult`
    - Map SOAR complexity levels:
      - `SIMPLE` -> `Complexity.SIMPLE`
      - `MEDIUM` -> `Complexity.MODERATE`
      - `COMPLEX` -> `Complexity.COMPLEX`
      - `CRITICAL` -> `Complexity.COMPLEX`
    - Override heuristic assessment when SOAR available
    - **Test**: Write `test_complexity_fallback_heuristic` - verifies heuristic used when SOAR unavailable
  - [ ] 2.6 Implement graceful fallback to heuristics
    - **Test First**: Write `test_decompose_fallback_to_heuristics` - verifies heuristic decomposition on LLM failure
    - Catch exceptions from SOAR call (ImportError, RuntimeError, TimeoutError)
    - Log warning: "Using rule-based decomposition (LLM unavailable)"
    - Call existing `_decompose_goal_soar()` heuristic function from `core.py`
    - Set `decomposition_source = "heuristic"` in result
    - **Test**: Write `test_decompose_logs_fallback_warning`
  - [ ] 2.7 Modify create_plan() to use PlanDecomposer
    - **Test First**: Update `tests/unit/cli/test_plan_commands.py` with test for new decomposer integration
    - Replace direct call to `_decompose_goal_soar()` with `PlanDecomposer.decompose()`
    - Pass `context_files` parameter to decomposer
    - Pass `config` for LLM settings
    - Store `decomposition_source` in Plan model (add field if needed)
    - **Test**: Verify create_plan uses PlanDecomposer when `auto_decompose=True`

- [ ] 3.0 Integrate Memory-Based File Path Resolution
  - [ ] 3.1 Create FilePathResolver class skeleton with TDD
    - **Test First**: Create `tests/unit/cli/planning/test_file_path_resolver.py` with `TestFilePathResolver`
    - Write failing test `test_resolver_initialization` - verifies class instantiation
    - Create `packages/cli/src/aurora_cli/planning/memory.py` with `FilePathResolver` class
    - Add `__init__(self, store: SQLiteStore | None = None, config: Config | None = None)`
    - Add placeholder methods: `resolve_for_subgoal()`, `has_indexed_memory()`, `format_path_with_confidence()`
    - Make test pass
  - [ ] 3.2 Implement FR-3.1: File path resolution from memory
    - **Test First**: Write `test_resolve_paths_with_indexed_memory` - mocks retriever, verifies paths returned
    - Create internal `MemoryRetriever` instance with store and config
    - Implement `resolve_for_subgoal(subgoal: Subgoal, limit: int = 5)`:
      - Call `retriever.retrieve(subgoal.description, limit=limit)`
      - Extract file paths from `CodeChunk.file_path`
      - Extract line ranges from `chunk.line_start` and `chunk.line_end`
      - Calculate confidence score from semantic similarity (use chunk's score attribute)
    - Return `list[FileResolution]` with `path`, `line_start`, `line_end`, `confidence`
    - **Test**: Write `test_line_range_extraction` - verifies line numbers extracted correctly
  - [ ] 3.3 Add FileResolution model to planning models
    - **Test First**: Write test in `test_planning_models.py` for `FileResolution` validation
    - Add `FileResolution` dataclass/model to `models.py`:
      ```python
      class FileResolution(BaseModel):
          path: str
          line_start: int | None = None
          line_end: int | None = None
          confidence: float = Field(ge=0.0, le=1.0)
      ```
    - Add `file_resolutions: dict[str, list[FileResolution]]` field to Plan model (keyed by subgoal ID)
    - Make test pass
  - [ ] 3.4 Implement FR-3.2: Confidence score display formatting
    - **Test First**: Write `test_confidence_score_formatting` - verifies format string output
    - Implement `format_path_with_confidence(resolution: FileResolution) -> str`:
      - High confidence (>= 0.8): `"{path} lines {start}-{end}"`
      - Medium confidence (0.6-0.8): `"{path} lines {start}-{end} (suggested)"`
      - Low confidence (< 0.6): `"{path} lines {start}-{end} (low confidence)"`
    - **Test**: Write tests for each threshold boundary
  - [ ] 3.5 Implement FR-3.3: Graceful degradation when memory not indexed
    - **Test First**: Write `test_resolve_paths_memory_not_indexed` - verifies warning and generic paths
    - Implement `has_indexed_memory()` by delegating to `retriever.has_indexed_memory()`
    - If not indexed:
      - Log warning: "Memory not indexed. Run 'aur mem index .' for code-aware tasks."
      - Generate generic paths using pattern: `src/<domain>/<task-slug>.py`
      - Mark resolutions with `needs_file_resolution: true` in metadata
    - **Test**: Write `test_graceful_degradation` - verifies plan still generates
  - [ ] 3.6 Integrate FilePathResolver into PlanDecomposer
    - **Test First**: Update `test_decompose.py` with test for file resolution integration
    - After subgoal generation, call `resolver.resolve_for_subgoal()` for each subgoal
    - Store resolved paths in subgoal metadata or separate `file_resolutions` dict
    - Calculate average confidence for summary display
    - **Test**: Verify decompose result includes file resolutions

- [ ] 4.0 Integrate Agent Discovery for Capability Matching
  - [ ] 4.1 Create AgentRecommender class skeleton with TDD
    - **Test First**: Create `tests/unit/cli/planning/test_agent_recommender.py` with `TestAgentRecommender`
    - Write failing test `test_recommender_initialization` - verifies class instantiation
    - Create `packages/cli/src/aurora_cli/planning/agents.py` with `AgentRecommender` class
    - Add `__init__(self, manifest: AgentManifest | None = None, config: Config | None = None)`
    - Add placeholder methods: `recommend_for_subgoal()`, `detect_gaps()`, `get_fallback_agent()`, `_extract_keywords()`
    - Make test pass
  - [ ] 4.2 Implement keyword extraction from subgoal text
    - **Test First**: Write `test_keyword_extraction` - verifies keywords extracted from title/description
    - Implement `_extract_keywords(subgoal: Subgoal) -> list[str]`:
      - Tokenize title and description (split on whitespace and punctuation)
      - Convert to lowercase
      - Remove common stop words (the, a, an, is, are, to, for, etc.)
      - Return unique keywords
    - **Test**: Write test with various subgoal texts
  - [ ] 4.3 Implement FR-4.1: Agent capability matching
    - **Test First**: Write `test_recommend_agent_high_score` - verifies best-matching agent returned
    - Load `AgentManifest` via `ManifestManager.get_or_refresh()` if not provided
    - Implement `recommend_for_subgoal(subgoal: Subgoal) -> tuple[str, float]`:
      - Extract keywords from subgoal
      - For each agent in manifest, calculate score based on keyword overlap with `agent.skills` and `agent.when_to_use`
      - Score = (matching keywords) / (total keywords in subgoal)
      - Return highest-scoring agent with score >= threshold (default 0.5)
      - Return `("@full-stack-dev", 0.0)` as fallback if no match
    - **Test**: Write `test_recommend_agent_no_match_fallback` - verifies fallback agent used
  - [ ] 4.4 Add AgentGap model to planning models
    - **Test First**: Write test in `test_planning_models.py` for `AgentGap` validation
    - Add `AgentGap` model to `models.py`:
      ```python
      class AgentGap(BaseModel):
          subgoal_id: str
          recommended_agent: str
          agent_exists: bool
          fallback: str = "@full-stack-dev"
          suggested_capabilities: list[str] = []
      ```
    - Add `agent_gaps: list[AgentGap]` field to Plan model
    - Make test pass
  - [ ] 4.5 Implement FR-4.2: Gap detection and recording
    - **Test First**: Write `test_detect_gaps` - verifies gaps recorded when score < threshold
    - Implement `detect_gaps(subgoals: list[Subgoal], recommendations: dict[str, tuple[str, float]]) -> list[AgentGap]`:
      - For each subgoal, if score < threshold (0.5), create AgentGap
      - Record `recommended_agent` (best match even if low score)
      - Set `agent_exists = False` if agent not in manifest
      - Set `fallback = "@full-stack-dev"`
      - Set `suggested_capabilities` from extracted keywords
    - Return list of AgentGap objects
    - **Test**: Write test verifying gap metadata is complete
  - [ ] 4.6 Implement FR-4.3: Agent existence verification
    - **Test First**: Write `test_agent_existence_check` - verifies agent_exists flag set correctly
    - Implement `verify_agent_exists(agent_id: str) -> bool`:
      - Call `manifest.get_agent(agent_id.lstrip("@"))`
      - Return True if found, False otherwise
    - Update `recommend_for_subgoal()` to set `subgoal.agent_exists` flag
    - Log warning for non-existent agents
    - **Test**: Write test with mix of existing and non-existing agents
  - [ ] 4.7 Integrate AgentRecommender into PlanDecomposer
    - **Test First**: Update `test_decompose.py` with test for agent recommendation integration
    - After subgoal generation, call `recommender.recommend_for_subgoal()` for each subgoal
    - Assign recommended agent to `subgoal.recommended_agent`
    - Set `subgoal.agent_exists` based on verification
    - Collect gaps via `recommender.detect_gaps()`
    - Store gaps in plan metadata
    - **Test**: Verify decompose result includes agent assignments and gaps

- [ ] 5.0 Implement User Checkpoint Before Plan Generation
  - [ ] 5.1 Add DecompositionSummary model
    - **Test First**: Write test in `test_planning_models.py` for `DecompositionSummary` validation
    - Add `DecompositionSummary` dataclass to `models.py`:
      ```python
      @dataclass
      class DecompositionSummary:
          goal: str
          subgoals: list[Subgoal]
          agents_assigned: int
          agent_gaps: list[AgentGap]
          files_resolved: int
          avg_confidence: float
          complexity: Complexity
          decomposition_source: str  # "soar" or "heuristic"
          warnings: list[str]
      ```
    - Add `display()` method placeholder for Rich rendering
    - Make test pass
  - [ ] 5.2 Implement FR-5.1: Decomposition summary display
    - **Test First**: Create `tests/unit/cli/planning/test_checkpoint.py` with `TestCheckpointDisplay`
    - Write `test_summary_display_format` - verifies all sections displayed
    - Implement `DecompositionSummary.display()` using Rich:
      - Display goal echo: `"Goal: {goal}"`
      - Display subgoal count: `"Subgoals: {count}"`
      - List each subgoal: `"  [sg-N] {title} (@{agent})"`
      - Highlight gaps with different color (yellow)
      - Display agent summary: `"Agents: X assigned, Y gaps"`
      - Display file summary: `"Files: X resolved (avg confidence: 0.XX)"`
      - Display complexity: `"Complexity: {SIMPLE/MODERATE/COMPLEX}"`
    - Use Rich Panel for formatted output
    - **Test**: Verify all summary sections present in output
  - [ ] 5.3 Implement FR-5.2: Confirmation prompt
    - **Test First**: Write `test_confirmation_prompt_yes` - verifies 'Y' proceeds
    - **Test First**: Write `test_confirmation_prompt_no` - verifies 'n' aborts
    - Implement `prompt_for_confirmation() -> bool`:
      - Display prompt: `"Proceed with plan generation? (Y/n)"`
      - 'Y', 'y', or Enter: Return True (proceed)
      - 'N' or 'n': Return False (abort)
      - Invalid input: Repeat prompt
      - Ctrl+C (KeyboardInterrupt): Return False with message "Plan creation cancelled."
    - **Test**: Write `test_confirmation_prompt_invalid_input` - verifies retry on invalid
    - **Test**: Write `test_confirmation_prompt_interrupt` - verifies graceful Ctrl+C handling
  - [ ] 5.4 Implement FR-5.3: Non-interactive mode
    - **Test First**: Write `test_non_interactive_mode` - verifies `--yes` skips prompt
    - Add `yes: bool = False` parameter to `create_plan()`
    - Add `non_interactive: bool = False` as alias
    - If `yes` or `non_interactive` is True:
      - Skip confirmation prompt
      - Still display summary (for logging)
    - Return appropriate exit code: 0 on success, non-zero on failure
    - **Test**: Verify both `--yes` and `--non-interactive` flags work identically
  - [ ] 5.5 Integrate checkpoint into create_plan() flow
    - **Test First**: Update `test_plan_commands.py` with checkpoint integration test
    - Modify `create_plan()` to:
      1. Perform decomposition (PlanDecomposer)
      2. Build DecompositionSummary
      3. Call `summary.display()`
      4. If not `yes`: Call `prompt_for_confirmation()`
      5. If confirmed: Proceed with file generation
      6. If not confirmed: Return early with "Plan creation cancelled."
    - **Test**: Write `test_checkpoint_abort_no_files` - verifies no files created on abort
    - **Test**: Write `test_create_plan_with_checkpoint` - verifies full flow

- [ ] 6.0 Enhance Plan File Generation with Code-Aware Content
  - [ ] 6.1 Update Plan model with new fields for enhanced metadata
    - **Test First**: Update `test_planning_models.py` with tests for new Plan fields
    - Add fields to `Plan` model:
      - `decomposition_source: str = "heuristic"` (enum: "soar", "heuristic")
      - `context_summary: str | None = None`
      - `file_resolutions: dict[str, list[FileResolution]] = {}`
      - `agent_gaps: list[AgentGap] = []` (already exists, verify structure)
    - Update JSON serialization to include new fields
    - Make tests pass
  - [ ] 6.2 Implement FR-6.1: Enhanced tasks.md generation with file paths
    - **Test First**: Create `tests/unit/cli/planning/test_enhanced_generation.py` with `TestEnhancedGeneration`
    - Write `test_tasks_md_includes_file_paths` - verifies file paths in output
    - Update `packages/cli/src/aurora_cli/planning/templates/tasks.md.j2`:
      - For each task, include file path when resolved:
        ```markdown
        - [ ] 1.0 {title}
          - Agent: {agent}
          - **File**: {path} lines {start}-{end} (confidence: {score})
        ```
      - Group tasks by subgoal
      - Mark unresolved files: `"**File**: TBD - run 'aur mem index' for resolution"`
    - Update `TemplateRenderer.build_context()` to include `file_resolutions`
    - **Test**: Verify tasks.md contains file paths with confidence scores
  - [ ] 6.3 Implement FR-6.2: Enhanced agents.json generation
    - **Test First**: Write `test_agents_json_includes_gaps` - verifies gap information in output
    - Update `packages/cli/src/aurora_cli/planning/templates/agents.json.j2`:
      - Add `"agent_gaps": [...]` array with gap details
      - Add `"file_resolutions": {...}` map keyed by subgoal ID
      - Add `"decomposition_source": "soar" | "heuristic"`
      - Add `"context_summary": "..."`
    - Ensure JSON is valid and matches schema in PRD Appendix C
    - **Test**: Write `test_agents_json_schema_validation` - verifies against JSON schema
  - [ ] 6.4 Implement FR-6.3: ASCII dependency graph in plan.md
    - **Test First**: Write `test_plan_md_dependency_graph` - verifies graph in output
    - Create helper function `generate_dependency_graph(subgoals: list[Subgoal]) -> str`:
      - Linear dependencies: `sg-1 -> sg-2 -> sg-4`
      - Parallel dependencies: `sg-1 -> sg-3, sg-2 -> sg-3`
      - Show blocked subgoals clearly
      - Include legend: `"Legend: -> dependency, [] blocked"`
    - Update `packages/cli/src/aurora_cli/planning/templates/plan.md.j2`:
      - Add `## Dependency Graph` section
      - Include generated ASCII graph
    - **Test**: Verify graph accurately represents dependencies
  - [ ] 6.5 Update TemplateRenderer.build_context() for new fields
    - **Test First**: Write `test_build_context_includes_new_fields` - verifies context dict
    - Update `renderer.py` `build_context()` method to include:
      - `decomposition_source`
      - `context_summary`
      - `file_resolutions` (formatted for template)
      - `agent_gaps` (formatted for template)
      - `dependency_graph` (generated string)
    - **Test**: Verify all new fields present in context
  - [ ] 6.6 Update render_plan_files() for atomic generation with new content
    - **Test First**: Write `test_render_plan_files_atomic` - verifies atomic write behavior
    - Ensure temp directory pattern is used (already exists)
    - Verify all files include enhanced content
    - Validate JSON after generation (already exists for agents.json)
    - **Test**: Verify all 8 files generated with enhanced content

- [ ] 7.0 Integration Testing, Manual Verification, and Documentation
  - [ ] 7.1 Write end-to-end integration test for SOAR decomposition flow
    - Create `tests/integration/cli/test_plan_decomposition_e2e.py`
    - Write `test_plan_create_with_soar_and_checkpoint`:
      - Mock LLM client to return predictable decomposition
      - Call `create_plan("Implement OAuth2 authentication")`
      - Verify SOAR decomposition was used (`decomposition_source == "soar"`)
      - Verify checkpoint summary displayed
      - Verify all 8 files generated
      - Verify agents.json includes new fields
    - Use pytest fixtures for mock setup
  - [ ] 7.2 Write integration test for graceful degradation
    - Write `test_plan_create_graceful_degradation`:
      - Configure LLM to raise exception
      - Verify fallback to heuristics
      - Verify warning logged
      - Verify plan still generates successfully
      - Verify `decomposition_source == "heuristic"`
  - [ ] 7.3 Write integration test for archive with spec updates
    - Write `test_archive_with_full_spec_updates`:
      - Create plan with delta specs in `specs/` directory
      - Call archive command
      - Verify spec deltas processed (ADDED, MODIFIED, REMOVED, RENAMED)
      - Verify specs moved to `.aurora/capabilities/`
      - Verify manifest updated
      - Verify archive directory created with timestamp prefix
  - [ ] 7.4 Write integration test for checkpoint abort
    - Write `test_checkpoint_abort_no_files`:
      - Mock confirmation prompt to return 'n'
      - Verify no files created
      - Verify message "Plan creation cancelled."
      - Verify exit code is non-zero
  - [ ] 7.5 Write integration test for non-interactive mode
    - Write `test_non_interactive_mode`:
      - Call `create_plan(..., yes=True)`
      - Verify no prompt displayed
      - Verify plan created successfully
      - Verify all files present
  - [ ] 7.6 Manual verification: SOAR decomposition
    - Run: `aur plan create "Implement OAuth2 authentication"`
    - Verify checkpoint summary displays subgoals with agents
    - Verify file paths shown (if memory indexed) or warning (if not)
    - Verify complexity assessment shown
    - Confirm with 'Y' and verify files created
    - Check `agents.json` for `decomposition_source: "soar"`
  - [ ] 7.7 Manual verification: Archive with spec deltas
    - Create plan with delta spec in `specs/` directory
    - Run: `aur archive 0001`
    - Verify task progress displayed
    - Verify spec update prompts (if specs present)
    - Verify archive created in `.aurora/plans/archive/YYYY-MM-DD-0001-...`
    - Verify specs moved to `.aurora/capabilities/`
  - [ ] 7.8 Manual verification: Checkpoint flow
    - Run: `aur plan create "Test goal"`
    - Verify summary displayed with all sections
    - Press 'n' to abort
    - Verify "Plan creation cancelled." message
    - Verify no files created in `.aurora/plans/active/`
    - Run again and press 'Y' to confirm
    - Verify files created
  - [ ] 7.9 Verify performance targets
    - SOAR decomposition: < 10s (measure with `time` command)
    - Memory retrieval: < 2s per subgoal
    - Agent matching: < 500ms total
    - Checkpoint display: < 100ms
    - File generation: < 5s total
    - Archive operation: < 3s
    - Log any performance issues for optimization
  - [ ] 7.10 Update CLI help text and documentation
    - Update `aur plan create --help` with new options (`--yes`, `--non-interactive`)
    - Update `aur archive --help` with flags (`--yes`, `--skip-specs`, `--no-validate`)
    - Add section to CLI usage guide explaining checkpoint flow
    - Document graceful degradation behavior
    - Document file path resolution and confidence scores

---

## Self-Verification Checklist

Before marking complete, verify:

- [ ] All PRD requirements (FR-1 through FR-6) covered by tasks
- [ ] Logical task order with proper dependencies
- [ ] Every implementation file has corresponding test file
- [ ] Sub-tasks specific enough for junior developer (1-4 hours each)
- [ ] TDD methodology followed (test-first approach documented)
- [ ] Existing codebase patterns referenced (fixtures, mocks, CliRunner)
- [ ] Port strategy for OpenSpec code clearly documented
- [ ] Path mappings for Aurora clearly specified

---

## Dependency Graph

```
Task 1.0 (Archive Port)
|-- 1.1-1.4: Port supporting modules (parallel)
|-- 1.5-1.6: Port ArchiveCommand (sequential)
|-- 1.7-1.11: Implement FR-1.x (parallel after 1.6)
|-- 1.12: Integrate with manifest (after 1.9)
+-- 1.13: Port tests (after 1.11)

Task 2.0 (SOAR Integration)
|-- 2.1: PlanDecomposer skeleton
|-- 2.2-2.6: FR-2.x implementations (sequential)
+-- 2.7: Integrate into create_plan (after 2.6)

Task 3.0 (Memory Integration) - Can run parallel with 2.0
|-- 3.1: FilePathResolver skeleton
|-- 3.2-3.5: FR-3.x implementations (sequential)
+-- 3.6: Integrate into PlanDecomposer (after 3.5, 2.7)

Task 4.0 (Agent Discovery) - Can run parallel with 2.0, 3.0
|-- 4.1: AgentRecommender skeleton
|-- 4.2-4.6: FR-4.x implementations (sequential)
+-- 4.7: Integrate into PlanDecomposer (after 4.6, 2.7)

Task 5.0 (Checkpoint) - Depends on 2.7, 3.6, 4.7
|-- 5.1-5.4: Checkpoint components (sequential)
+-- 5.5: Integrate into create_plan flow

Task 6.0 (Enhanced Generation) - Depends on 5.5
|-- 6.1: Model updates
|-- 6.2-6.4: FR-6.x implementations (parallel after 6.1)
|-- 6.5: Renderer updates (after 6.4)
+-- 6.6: Atomic generation (after 6.5)

Task 7.0 (Integration Testing) - Depends on all above
|-- 7.1-7.5: Integration tests (parallel)
|-- 7.6-7.8: Manual verification (sequential)
|-- 7.9: Performance verification
+-- 7.10: Documentation updates
```

---

**END OF TASK LIST**

**Total Tasks**: 7 parent tasks, 70 sub-tasks
**Estimated Total Effort**: 8-12 days
**Coverage**: All 6 functional requirements (FR-1 through FR-6) + integration testing
