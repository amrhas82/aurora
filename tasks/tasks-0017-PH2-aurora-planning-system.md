# Phase 2 Tasks: PRD & Task Generation for Aurora Planning System

**PRD Reference**: `/home/hamr/PycharmProjects/aurora/tasks/0017-prd-aurora-planning-system.md`
**Phase**: 2 (PRD & Task Generation)
**Status**: Ready for Implementation
**Prerequisites**: Phase 1 Complete (plan init, create, list, show, archive)

---

## Relevant Files

### Models & Schemas (FR-2.4)
- `packages/cli/src/aurora_cli/planning/prd_models.py` - NEW: Pydantic models for PRD, requirements, tasks, file paths
- `tests/unit/cli/test_prd_models.py` - Unit tests for PRD Pydantic models

### Error Handling (FR-2.5)
- `packages/cli/src/aurora_cli/planning/errors.py` - EXTEND: Add Phase 2 validation messages
- `tests/unit/cli/test_planning_errors.py` - EXTEND: Tests for Phase 2 error messages

### Result Types (FR-2.6)
- `packages/cli/src/aurora_cli/planning/results.py` - EXTEND: Add PRDResult, TaskGenerationResult, etc.
- `tests/unit/cli/test_planning_results.py` - EXTEND: Tests for Phase 2 result types

### PRD Generation (FR-2.1)
- `packages/cli/src/aurora_cli/planning/prd_generator.py` - NEW: PRD expansion logic
- `tests/unit/cli/test_prd_generator.py` - Unit tests for PRD generation

### Task Generation (FR-2.2)
- `packages/cli/src/aurora_cli/planning/task_generator.py` - NEW: Code-aware task generation
- `tests/unit/cli/test_task_generator.py` - Unit tests for task generation

### File Resolution
- `packages/cli/src/aurora_cli/planning/file_resolver.py` - NEW: File path resolution from memory
- `tests/unit/cli/test_file_resolver.py` - Unit tests for file resolution

### Templates
- `packages/cli/src/aurora_cli/planning/templates/prd.md.jinja2` - NEW: PRD template
- `packages/cli/src/aurora_cli/planning/templates/tasks.md.jinja2` - NEW: Tasks template

### CLI Commands
- `packages/cli/src/aurora_cli/commands/plan.py` - EXTEND: Add expand and tasks subcommands
- `tests/unit/cli/test_plan_commands.py` - EXTEND: Tests for expand and tasks commands

### Slash Commands (FR-2.3)
- `packages/cli/src/aurora_cli/slash_commands/__init__.py` - NEW: Slash command registration
- `packages/cli/src/aurora_cli/slash_commands/aur_plan.py` - NEW: /aur:plan slash command
- `packages/cli/src/aurora_cli/slash_commands/aur_archive.py` - NEW: /aur:archive slash command
- `tests/unit/cli/test_slash_commands.py` - Unit tests for slash commands

### Core Planning (EXTEND)
- `packages/cli/src/aurora_cli/planning/core.py` - EXTEND: Add expand_plan, generate_tasks functions
- `packages/cli/src/aurora_cli/planning/__init__.py` - EXTEND: Export new functions

### Shell Tests (FR-2.8)
- `tests/shell/test_27_prd_expansion.sh` - Shell test for PRD expansion
- `tests/shell/test_28_task_generation.sh` - Shell test for task generation
- `tests/shell/test_29_task_code_aware.sh` - Shell test for code-aware tasks
- `tests/shell/test_30_prd_template_validation.sh` - Shell test for PRD template validation

### Integration Tests
- `tests/integration/test_prd_workflow.py` - Integration tests for PRD workflow

### Notes

- **TDD Approach (FR-2.9)**: Write tests BEFORE implementation for each component
- **Graceful Degradation (FR-2.7)**: All functions must return Result types, never crash
- **OpenSpec Format**: PRD must follow OpenSpec conventions (Requirements + Scenarios)
- **Memory Integration**: File paths must be resolved from indexed memory when available
- **Existing Patterns**: Follow patterns from Phase 1 implementation in `core.py`
- **Testing Framework**: pytest with pytest-cov, targeting 85% coverage
- **Type Safety**: All code must pass mypy strict mode with 0 errors

---

## Tasks

- [ ] 1.0 Implement Phase 2 Pydantic Models (FR-2.4)
  - [ ] 1.1 Write unit tests for FilePath model with line number validation
    - **File**: `tests/unit/cli/test_prd_models.py`
    - **Test Cases**: Valid file path, path with lines, invalid line range (end < start), format() method
  - [ ] 1.2 Write unit tests for AcceptanceCriteria model
    - **File**: `tests/unit/cli/test_prd_models.py`
    - **Test Cases**: Valid criteria, too short description, testable flag
  - [ ] 1.3 Write unit tests for Requirement model with FR-N.M ID format
    - **File**: `tests/unit/cli/test_prd_models.py`
    - **Test Cases**: Valid requirement, invalid ID format, missing acceptance criteria
  - [ ] 1.4 Write unit tests for PRDSection model
    - **File**: `tests/unit/cli/test_prd_models.py`
    - **Test Cases**: Valid section, invalid subgoal_id, invalid agent format
  - [ ] 1.5 Write unit tests for PRD model
    - **File**: `tests/unit/cli/test_prd_models.py`
    - **Test Cases**: Valid PRD, missing sections, total_requirements calculation
  - [ ] 1.6 Write unit tests for Task and TaskList models
    - **File**: `tests/unit/cli/test_prd_models.py`
    - **Test Cases**: Valid task, invalid task ID, progress percentage calculation
  - [ ] 1.7 Implement FilePath model with line number validation
    - **File**: `packages/cli/src/aurora_cli/planning/prd_models.py`
    - **Implementation**: path, line_start, line_end, exists, confidence fields; format() method
  - [ ] 1.8 Implement AcceptanceCriteria model
    - **File**: `packages/cli/src/aurora_cli/planning/prd_models.py`
    - **Implementation**: description (10-500 chars), testable flag
  - [ ] 1.9 Implement Requirement model with FR-N.M ID validation
    - **File**: `packages/cli/src/aurora_cli/planning/prd_models.py`
    - **Implementation**: id pattern validation, title, description, type enum, acceptance_criteria, files_to_modify, files_to_create
  - [ ] 1.10 Implement PRDSection model
    - **File**: `packages/cli/src/aurora_cli/planning/prd_models.py`
    - **Implementation**: subgoal_id, title, agent, requirements list, testing_strategy dict, dependencies
  - [ ] 1.11 Implement PRD model with sections validation
    - **File**: `packages/cli/src/aurora_cli/planning/prd_models.py`
    - **Implementation**: plan_id, goal, generated_at, executive_summary, sections, total_requirements, memory_context_used
  - [ ] 1.12 Implement Task model with status enum
    - **File**: `packages/cli/src/aurora_cli/planning/prd_models.py`
    - **Implementation**: id pattern, title, subgoal_id, status enum (pending/in_progress/completed/blocked/skipped), files, test_file, estimated_minutes, depends_on
  - [ ] 1.13 Implement TaskList model with progress tracking
    - **File**: `packages/cli/src/aurora_cli/planning/prd_models.py`
    - **Implementation**: plan_id, generated_at, tasks, total_tasks, completed_tasks, memory_paths_resolved/missing, get_progress_percentage()
  - [ ] 1.14 Verify all tests pass for Pydantic models
    - **Command**: `pytest tests/unit/cli/test_prd_models.py -v`

- [ ] 2.0 Add Phase 2 Validation Error Messages (FR-2.5)
  - [ ] 2.1 Write tests for Phase 2 validation messages
    - **File**: `tests/unit/cli/test_planning_errors.py`
    - **Test Cases**: PRD_PLAN_NOT_FOUND, PRD_ALREADY_EXISTS, TASKS_PRD_NOT_FOUND, FILE_PATH_NOT_RESOLVED, REQUIREMENT_ID_INVALID
  - [ ] 2.2 Add PRD error messages to VALIDATION_MESSAGES
    - **File**: `packages/cli/src/aurora_cli/planning/errors.py`
    - **Messages**: PRD_PLAN_NOT_FOUND, PRD_ALREADY_EXISTS, PRD_NO_SUBGOALS, PRD_GENERATION_FAILED, PRD_TEMPLATE_INVALID
  - [ ] 2.3 Add task generation error messages
    - **File**: `packages/cli/src/aurora_cli/planning/errors.py`
    - **Messages**: TASKS_PRD_NOT_FOUND, TASKS_ALREADY_EXIST, TASKS_NO_REQUIREMENTS, TASKS_GENERATION_FAILED
  - [ ] 2.4 Add file path resolution error messages
    - **File**: `packages/cli/src/aurora_cli/planning/errors.py`
    - **Messages**: FILE_PATH_NOT_RESOLVED, FILE_PATH_NOT_EXISTS, FILE_PATH_LINE_INVALID, MEMORY_INDEX_EMPTY, MEMORY_SEARCH_FAILED
  - [ ] 2.5 Add requirement validation error messages
    - **File**: `packages/cli/src/aurora_cli/planning/errors.py`
    - **Messages**: REQUIREMENT_ID_INVALID, REQUIREMENT_NO_ACCEPTANCE_CRITERIA, REQUIREMENT_DUPLICATE_ID
  - [ ] 2.6 Implement PRDGenerationError, TaskGenerationError, FileResolutionError exception classes
    - **File**: `packages/cli/src/aurora_cli/planning/errors.py`
  - [ ] 2.7 Verify error message tests pass
    - **Command**: `pytest tests/unit/cli/test_planning_errors.py -v`

- [ ] 3.0 Implement Phase 2 Result Types (FR-2.6)
  - [ ] 3.1 Write tests for PRDResult dataclass
    - **File**: `tests/unit/cli/test_planning_results.py`
    - **Test Cases**: Success with PRD, failure with error, warnings list
  - [ ] 3.2 Write tests for TaskGenerationResult dataclass
    - **File**: `tests/unit/cli/test_planning_results.py`
    - **Test Cases**: Success with task_list, files_resolved/missing counts, warnings
  - [ ] 3.3 Write tests for ExpandResult dataclass
    - **File**: `tests/unit/cli/test_planning_results.py`
    - **Test Cases**: Full expand success, checkpoint_confirmed flag
  - [ ] 3.4 Write tests for FileResolutionResult dataclass
    - **File**: `tests/unit/cli/test_planning_results.py`
    - **Test Cases**: Resolved paths, missing entities, confidence_avg
  - [ ] 3.5 Implement PRDResult dataclass
    - **File**: `packages/cli/src/aurora_cli/planning/results.py`
    - **Fields**: success, prd, prd_path, sections_generated, requirements_generated, memory_files_resolved, warnings, error
  - [ ] 3.6 Implement TaskGenerationResult dataclass
    - **File**: `packages/cli/src/aurora_cli/planning/results.py`
    - **Fields**: success, task_list, tasks_path, tasks_generated, files_resolved, files_missing, warnings, error
  - [ ] 3.7 Implement ExpandResult dataclass
    - **File**: `packages/cli/src/aurora_cli/planning/results.py`
    - **Fields**: success, prd_result, task_result, plan_dir, checkpoint_confirmed, warnings, error
  - [ ] 3.8 Implement FileResolutionResult dataclass
    - **File**: `packages/cli/src/aurora_cli/planning/results.py`
    - **Fields**: success, resolved_paths, missing_entities, confidence_avg, memory_queries, warning
  - [ ] 3.9 Verify result type tests pass
    - **Command**: `pytest tests/unit/cli/test_planning_results.py -v`

- [ ] 4.0 Implement File Path Resolution from Memory
  - [ ] 4.1 Write tests for entity extraction from requirement text
    - **File**: `tests/unit/cli/test_file_resolver.py`
    - **Test Cases**: Extract class names, file paths, API endpoints, deduplicate entities
  - [ ] 4.2 Write tests for memory index queries
    - **File**: `tests/unit/cli/test_file_resolver.py`
    - **Test Cases**: Query with mock memory, empty memory, memory failure, rank by confidence
  - [ ] 4.3 Write tests for line number suggestion
    - **File**: `tests/unit/cli/test_file_resolver.py`
    - **Test Cases**: Find class definition, find function, expand to block end, entity not found
  - [ ] 4.4 Implement extract_entities() function
    - **File**: `packages/cli/src/aurora_cli/planning/file_resolver.py`
    - **Patterns**: Capitalized class names, file paths (*.py), API endpoints (/path), deduplicate
  - [ ] 4.5 Implement query_memory_for_files() function
    - **File**: `packages/cli/src/aurora_cli/planning/file_resolver.py`
    - **Integration**: Use MemoryRetriever from memory/retrieval.py, filter by code type, rank by confidence
  - [ ] 4.6 Implement suggest_line_numbers() function
    - **File**: `packages/cli/src/aurora_cli/planning/file_resolver.py`
    - **Logic**: Search for entity definition (class/def), find block end by indentation
  - [ ] 4.7 Implement resolve_file_paths() main function
    - **File**: `packages/cli/src/aurora_cli/planning/file_resolver.py`
    - **Return**: FileResolutionResult with resolved paths and missing entities
  - [ ] 4.8 Add graceful degradation for memory failures
    - **File**: `packages/cli/src/aurora_cli/planning/file_resolver.py`
    - **Pattern**: Return empty results with warning if memory unavailable
  - [ ] 4.9 Verify file resolver tests pass
    - **Command**: `pytest tests/unit/cli/test_file_resolver.py -v`

- [ ] 5.0 Implement PRD Generation (FR-2.1)
  - [ ] 5.1 Write tests for generate_prd() plan not found error
    - **File**: `tests/unit/cli/test_prd_generator.py`
    - **Test Case**: Plan ID doesn't exist, returns PRDResult with error
  - [ ] 5.2 Write tests for generate_prd() already exists without force
    - **File**: `tests/unit/cli/test_prd_generator.py`
    - **Test Case**: prd.md exists, returns error unless --force
  - [ ] 5.3 Write tests for generate_prd() success with memory context
    - **File**: `tests/unit/cli/test_prd_generator.py`
    - **Test Case**: Valid plan, memory retrieval works, PRD generated
  - [ ] 5.4 Write tests for generate_prd() graceful degradation on memory failure
    - **File**: `tests/unit/cli/test_prd_generator.py`
    - **Test Case**: Memory fails, PRD still generated with warning
  - [ ] 5.5 Write tests for generate_prd_section() per subgoal
    - **File**: `tests/unit/cli/test_prd_generator.py`
    - **Test Case**: Subgoal converted to PRDSection with requirements
  - [ ] 5.6 Write tests for generate_executive_summary()
    - **File**: `tests/unit/cli/test_prd_generator.py`
    - **Test Case**: Plan goal summarized, 50-2000 chars
  - [ ] 5.7 Create PRD template (prd.md.jinja2)
    - **File**: `packages/cli/src/aurora_cli/planning/templates/prd.md.jinja2`
    - **Sections**: Frontmatter, Executive Summary, Goals, Functional Requirements per subgoal, Testing Strategy, Agent Assignments
  - [ ] 5.8 Implement generate_executive_summary() function
    - **File**: `packages/cli/src/aurora_cli/planning/prd_generator.py`
    - **Logic**: Use LLM or template to generate summary from plan goal
  - [ ] 5.9 Implement generate_prd_section() function
    - **File**: `packages/cli/src/aurora_cli/planning/prd_generator.py`
    - **Logic**: Convert subgoal to PRDSection with FR-N.M requirements, acceptance criteria
  - [ ] 5.10 Implement render_prd_markdown() function
    - **File**: `packages/cli/src/aurora_cli/planning/prd_generator.py`
    - **Logic**: Render PRD using Jinja2 template, follow OpenSpec format
  - [ ] 5.11 Implement generate_prd() main function with graceful degradation
    - **File**: `packages/cli/src/aurora_cli/planning/prd_generator.py`
    - **Pattern**: Load plan, retrieve memory context, generate sections, validate, write prd.md
  - [ ] 5.12 Add expand_plan() function to core.py
    - **File**: `packages/cli/src/aurora_cli/planning/core.py`
    - **Signature**: expand_plan(plan_id: str, force: bool = False, config: Config | None = None) -> PRDResult
  - [ ] 5.13 Verify PRD generator tests pass
    - **Command**: `pytest tests/unit/cli/test_prd_generator.py -v`

- [ ] 6.0 Implement Task Generation (FR-2.2)
  - [ ] 6.1 Write tests for generate_tasks() PRD not found error
    - **File**: `tests/unit/cli/test_task_generator.py`
    - **Test Case**: prd.md doesn't exist, returns TaskGenerationResult with error
  - [ ] 6.2 Write tests for generate_tasks() tasks already exist without force
    - **File**: `tests/unit/cli/test_task_generator.py`
    - **Test Case**: tasks.md exists, returns error unless --force
  - [ ] 6.3 Write tests for generate_tasks() with file path resolution
    - **File**: `tests/unit/cli/test_task_generator.py`
    - **Test Case**: PRD requirements resolved to file paths from memory
  - [ ] 6.4 Write tests for generate_tasks() missing files warning
    - **File**: `tests/unit/cli/test_task_generator.py`
    - **Test Case**: Some file paths not found, success with warning
  - [ ] 6.5 Write tests for task grouping by subgoal
    - **File**: `tests/unit/cli/test_task_generator.py`
    - **Test Case**: Tasks grouped and numbered by subgoal (2.1, 2.2, etc.)
  - [ ] 6.6 Create tasks template (tasks.md.jinja2)
    - **File**: `packages/cli/src/aurora_cli/planning/templates/tasks.md.jinja2`
    - **Sections**: Header, per-subgoal sections with checkboxes, file paths, dependencies, progress summary
  - [ ] 6.7 Implement parse_prd_markdown() function to extract requirements
    - **File**: `packages/cli/src/aurora_cli/planning/task_generator.py`
    - **Logic**: Parse prd.md markdown, extract PRDSection and Requirements
  - [ ] 6.8 Implement create_task_from_requirement() function
    - **File**: `packages/cli/src/aurora_cli/planning/task_generator.py`
    - **Logic**: Convert Requirement to Task with resolved file paths
  - [ ] 6.9 Implement render_tasks_markdown() function
    - **File**: `packages/cli/src/aurora_cli/planning/task_generator.py`
    - **Logic**: Render TaskList using Jinja2 template with checkboxes
  - [ ] 6.10 Implement generate_tasks() main function with graceful degradation
    - **File**: `packages/cli/src/aurora_cli/planning/task_generator.py`
    - **Pattern**: Load PRD, resolve file paths, create tasks, validate, write tasks.md
  - [ ] 6.11 Add generate_plan_tasks() function to core.py
    - **File**: `packages/cli/src/aurora_cli/planning/core.py`
    - **Signature**: generate_plan_tasks(plan_id: str, force: bool = False, config: Config | None = None) -> TaskGenerationResult
  - [ ] 6.12 Verify task generator tests pass
    - **Command**: `pytest tests/unit/cli/test_task_generator.py -v`

- [ ] 7.0 Add CLI Commands for expand and tasks
  - [ ] 7.1 Write tests for `aur plan expand` command
    - **File**: `tests/unit/cli/test_plan_commands.py`
    - **Test Cases**: Expand success, plan not found, --force flag, --format json
  - [ ] 7.2 Write tests for `aur plan tasks` command
    - **File**: `tests/unit/cli/test_plan_commands.py`
    - **Test Cases**: Generate tasks success, PRD not found, --force flag, --format json
  - [ ] 7.3 Implement `aur plan expand` command with --to-prd flag
    - **File**: `packages/cli/src/aurora_cli/commands/plan.py`
    - **Options**: PLAN_ID argument, --to-prd flag, --force, --format rich|json
    - **Output**: Rich panel showing sections generated, requirements count, file paths
  - [ ] 7.4 Implement `aur plan tasks` command
    - **File**: `packages/cli/src/aurora_cli/commands/plan.py`
    - **Options**: PLAN_ID argument, --force, --format rich|json
    - **Output**: Rich panel showing tasks generated, file resolution stats
  - [ ] 7.5 Update planning __init__.py exports
    - **File**: `packages/cli/src/aurora_cli/planning/__init__.py`
    - **Exports**: expand_plan, generate_plan_tasks, PRD, TaskList, PRDResult, TaskGenerationResult
  - [ ] 7.6 Verify CLI command tests pass
    - **Command**: `pytest tests/unit/cli/test_plan_commands.py -v`

- [ ] 8.0 Implement Slash Commands (FR-2.3)
  - [ ] 8.1 Write tests for slash command registration
    - **File**: `tests/unit/cli/test_slash_commands.py`
    - **Test Cases**: Commands registered, callable, argument parsing
  - [ ] 8.2 Write tests for /aur:plan slash command
    - **File**: `tests/unit/cli/test_slash_commands.py`
    - **Test Cases**: Goal argument, --from-file option, --context option
  - [ ] 8.3 Write tests for /aur:archive slash command
    - **File**: `tests/unit/cli/test_slash_commands.py`
    - **Test Cases**: Plan ID argument, success output
  - [ ] 8.4 Create slash commands __init__.py with registration
    - **File**: `packages/cli/src/aurora_cli/slash_commands/__init__.py`
    - **Content**: Import and register slash commands, create SLASH_COMMANDS dict
  - [ ] 8.5 Implement /aur:plan slash command
    - **File**: `packages/cli/src/aurora_cli/slash_commands/aur_plan.py`
    - **Logic**: Parse arguments, delegate to create_plan(), format output for Claude Code
    - **Options**: goal, --from-file, --context
  - [ ] 8.6 Implement /aur:archive slash command
    - **File**: `packages/cli/src/aurora_cli/slash_commands/aur_archive.py`
    - **Logic**: Parse plan_id, delegate to archive_plan(), format output
  - [ ] 8.7 Add slash command configuration/documentation
    - **File**: `packages/cli/src/aurora_cli/slash_commands/README.md`
    - **Content**: How to register with Claude Code, usage examples
  - [ ] 8.8 Verify slash command tests pass
    - **Command**: `pytest tests/unit/cli/test_slash_commands.py -v`

- [ ] 9.0 Implement Shell Tests (FR-2.8)
  - [ ] 9.1 Create test_27_prd_expansion.sh
    - **File**: `tests/shell/test_27_prd_expansion.sh`
    - **Verifies**: prd.md created, has required sections (Executive Summary, Functional Requirements, Testing Strategy), at least 5 sections
  - [ ] 9.2 Create test_28_task_generation.sh
    - **File**: `tests/shell/test_28_task_generation.sh`
    - **Verifies**: tasks.md created, has checkboxes, file paths included if memory indexed, dependencies noted, at least 3 tasks
  - [ ] 9.3 Create test_29_task_code_aware.sh
    - **File**: `tests/shell/test_29_task_code_aware.sh`
    - **Verifies**: File paths from memory resolve to actual files, skip if memory not indexed
  - [ ] 9.4 Create test_30_prd_template_validation.sh
    - **File**: `tests/shell/test_30_prd_template_validation.sh`
    - **Verifies**: Frontmatter has plan_id and generated_at, required sections present, FR-N.M format, acceptance criteria present
  - [ ] 9.5 Verify all shell tests pass
    - **Command**: `bash tests/shell/test_27_prd_expansion.sh && bash tests/shell/test_28_task_generation.sh && bash tests/shell/test_29_task_code_aware.sh && bash tests/shell/test_30_prd_template_validation.sh`

- [ ] 10.0 Integration Testing and Documentation
  - [ ] 10.1 Write integration test for full PRD workflow
    - **File**: `tests/integration/test_prd_workflow.py`
    - **Flow**: Create plan -> expand to PRD -> generate tasks -> verify all files exist
  - [ ] 10.2 Write integration test for memory integration
    - **File**: `tests/integration/test_prd_workflow.py`
    - **Flow**: Index codebase -> create plan -> generate tasks -> verify file paths resolve
  - [ ] 10.3 Write integration test for agent recommendations in PRD
    - **File**: `tests/integration/test_prd_workflow.py`
    - **Flow**: Create plan with gaps -> expand PRD -> verify agent assignments documented
  - [ ] 10.4 Verify 85% code coverage for planning package
    - **Command**: `pytest tests/unit/cli/test_prd*.py tests/unit/cli/test_task*.py tests/unit/cli/test_file_resolver.py --cov=packages/cli/src/aurora_cli/planning --cov-report=term-missing`
  - [ ] 10.5 Verify mypy passes with 0 errors
    - **Command**: `mypy packages/cli/src/aurora_cli/planning --strict`
  - [ ] 10.6 Update CLI help text and documentation
    - **File**: `packages/cli/src/aurora_cli/commands/plan.py`
    - **Updates**: Add expand and tasks command help, examples, link to PRD format guide
  - [ ] 10.7 Verify all integration tests pass
    - **Command**: `pytest tests/integration/test_prd_workflow.py -v`

---

## Phase 2 Completion Criteria (from PRD Section 12.4-12.6)

### Implementation Complete
- [ ] `aur plan expand --to-prd` generates detailed PRD
- [ ] `aur plan tasks` generates code-aware tasks
- [ ] PRD follows OpenSpec format (Requirements + Scenarios)
- [ ] Tasks include file paths from memory index
- [ ] Tasks include line number suggestions
- [ ] Slash commands working: `/aur:plan`, `/aur:archive`
- [ ] Agent recommendations per subgoal in PRD

### Testing Complete
- [ ] PRD generation tests pass (template validation)
- [ ] Task generation tests pass (file path accuracy >= 90%)
- [ ] Memory integration tests pass (file resolution)
- [ ] Slash command tests pass (Claude Code integration)
- [ ] Shell tests pass (test_27 through test_30)
- [ ] Code coverage >= 85%
- [ ] MyPy strict mode passes (0 errors)

### Documentation Complete
- [ ] PRD format guide with examples
- [ ] Task format guide with file path examples
- [ ] Slash command usage documented
- [ ] OpenSpec alignment documented

---

## User Stories Covered

### 3.3 Developer Expanding Plan to PRD
- `aur plan expand 0001 --to-prd` generates detailed prd.md in <5s
- PRD includes: functional requirements, acceptance criteria per subgoal, testing strategy
- PRD references specific files from memory index
- Agent recommendations included per subgoal
- PRD format follows OpenSpec standards

### 3.4 Developer Generating Code-Aware Tasks
- `aur plan tasks 0001` generates tasks.md with code-specific tasks
- Tasks include file paths with line numbers from memory
- File paths resolved and verified to exist
- Tasks grouped by subgoal with sequential ordering
- Checkboxes provided for progress tracking
