# Implementation Tasks: Aurora Planning System - Phase 1

**PRD**: `/tasks/0017-prd-aurora-planning-system.md`
**Phase**: 1 - Core Planning Commands
**Generated**: 2026-01-02
**Scope**: FR-1.1 through FR-1.9 (Core Planning Infrastructure)

---

## Relevant Files

### New Files to Create

- `packages/cli/src/aurora_cli/planning/__init__.py` - Planning module initialization and exports
- `packages/cli/src/aurora_cli/planning/models.py` - Pydantic models (Plan, Subgoal, PlanManifest, enums)
- `packages/cli/src/aurora_cli/planning/errors.py` - Custom exceptions and VALIDATION_MESSAGES dictionary
- `packages/cli/src/aurora_cli/planning/results.py` - Result dataclasses for graceful degradation pattern
- `packages/cli/src/aurora_cli/planning/core.py` - Core planning logic (init, create, list, show, archive)
- `packages/cli/src/aurora_cli/planning/generator.py` - Plan generation with SOAR integration
- `packages/cli/src/aurora_cli/planning/templates.py` - Jinja2 templates for plan.md, prd.md, tasks.md
- `packages/cli/src/aurora_cli/commands/plan.py` - CLI commands (aur plan init/list/show/archive)
- `packages/cli/src/aurora_cli/slash_commands/__init__.py` - Slash commands module initialization
- `packages/cli/src/aurora_cli/slash_commands/aur_plan.py` - /aur:plan slash command implementation
- `packages/cli/src/aurora_cli/slash_commands/aur_archive.py` - /aur:archive slash command implementation

### New Test Files to Create

- `tests/unit/cli/test_planning_models.py` - Unit tests for Pydantic models and enums
- `tests/unit/cli/test_planning_errors.py` - Unit tests for error messages and exceptions
- `tests/unit/cli/test_planning_results.py` - Unit tests for result dataclasses
- `tests/unit/cli/test_planning_core.py` - Unit tests for core planning logic
- `tests/unit/cli/test_planning_generator.py` - Unit tests for plan generation pipeline
- `tests/unit/cli/test_plan_commands.py` - Unit tests for CLI commands
- `tests/integration/cli/test_plan_workflow.py` - Integration tests for full plan workflow

### Existing Files to Modify

- `packages/cli/src/aurora_cli/main.py` - Register plan command group
- `packages/cli/src/aurora_cli/config.py` - Add planning configuration options
- `packages/cli/pyproject.toml` - Add dependencies (python-slugify, jinja2)

---

### Notes

**Testing Framework**:
- Use pytest with Click's CliRunner for CLI command testing
- Use pytest fixtures for sample plans and manifests (follow pattern in `tests/unit/cli/test_agents_commands.py`)
- Mock SOAR orchestrator and MemoryRetriever for unit tests
- Integration tests should use tmp_path fixture for isolated file system operations
- Target >=85% code coverage for planning package

**Architectural Patterns**:
- Follow existing CLI patterns from `packages/cli/src/aurora_cli/commands/agents.py`
- Use Rich console for formatted output (tables, panels, progress spinners)
- Use `@handle_errors` decorator from `aurora_cli.errors` for CLI commands
- Return Result types from core functions (never raise exceptions in core logic)
- Use Pydantic v2 models with field validators and explicit error messages

**OpenSpec Patterns** (from PRD):
- Pydantic schemas with Field constraints and custom validators
- VALIDATION_MESSAGES dictionary for all error codes
- Graceful degradation: return structured results with warnings instead of crashing
- Atomic operations with rollback on failure

**Dependencies (PRD 0016 APIs assumed available)**:
- `AgentManifest` from `aurora_cli.agent_discovery.models`
- `MemoryRetriever` from `aurora_cli.memory.retrieval`
- `SOAROrchestrator` from `aurora_soar.orchestrator`

**Performance Targets**:
- `aur plan init`: <100ms
- `/aur:plan` (create): <10s end-to-end
- `aur plan list`: <200ms
- `aur plan show`: <500ms
- `/aur:archive`: <1s

---

## Tasks

- [ ] 1.0 Create Planning Package Structure and Pydantic Models (FR-1.6)
  - [ ] 1.1 Create planning module directory structure
    - **File**: `packages/cli/src/aurora_cli/planning/__init__.py`
    - **Action**: Create directory and __init__.py that exports: Plan, Subgoal, PlanStatus, Complexity, PlanManifest, PlanSummary
    - **Dependencies**: None (first task)
    - **Acceptance**: `from aurora_cli.planning import Plan, Subgoal` works
  - [ ] 1.2 Implement PlanStatus and Complexity enums
    - **File**: `packages/cli/src/aurora_cli/planning/models.py`
    - **Action**: Create `PlanStatus(str, Enum)` with values: ACTIVE="active", ARCHIVED="archived", FAILED="failed". Create `Complexity(str, Enum)` with values: SIMPLE="simple", MODERATE="moderate", COMPLEX="complex"
    - **Pattern**: Follow `AgentCategory` enum from `aurora_cli/agent_discovery/models.py`
    - **Dependencies**: Task 1.1
    - **Acceptance**: Enums serialize to lowercase string values in JSON
  - [ ] 1.3 Implement Subgoal Pydantic model with validators
    - **File**: `packages/cli/src/aurora_cli/planning/models.py`
    - **Action**: Create Subgoal(BaseModel) with fields:
      - `id: str = Field(pattern=r'^sg-\d+$')` - Subgoal ID (e.g., 'sg-1')
      - `title: str = Field(min_length=5, max_length=100)` - Short title
      - `description: str = Field(min_length=10, max_length=500)` - Detailed description
      - `recommended_agent: str = Field(pattern=r'^@[a-z0-9-]+$')` - Agent ID (e.g., '@full-stack-dev')
      - `agent_exists: bool = Field(default=True)` - Whether agent found in manifest
      - `dependencies: list[str] = Field(default_factory=list)` - List of subgoal IDs
    - **Validators**: Add @field_validator for id format, agent format with actionable error messages
    - **Dependencies**: Task 1.2
    - **Acceptance**: Validation errors match FR-1.7 message format
  - [ ] 1.4 Implement Plan Pydantic model with validators
    - **File**: `packages/cli/src/aurora_cli/planning/models.py`
    - **Action**: Create Plan(BaseModel) with fields:
      - `plan_id: str = Field(pattern=r'^\d{4}-[a-z0-9-]+$')` - Plan ID (e.g., '0001-oauth-auth')
      - `goal: str = Field(min_length=10, max_length=500)` - Natural language goal
      - `created_at: datetime = Field(default_factory=datetime.utcnow)` - Creation timestamp
      - `status: PlanStatus = Field(default=PlanStatus.ACTIVE)` - Lifecycle status
      - `complexity: Complexity = Field(default=Complexity.MODERATE)` - Assessed complexity
      - `subgoals: list[Subgoal] = Field(min_length=1, max_length=10)` - 1-10 subgoals
      - `agent_gaps: list[str] = Field(default_factory=list)` - Missing agent IDs
      - `context_sources: list[str] = Field(default_factory=list)` - Context origin
      - `archived_at: datetime | None = Field(default=None)` - Archive timestamp
      - `duration_days: int | None = Field(default=None)` - Days from creation to archive
    - **Validators**: Add @field_validator for plan_id format, @field_validator for subgoal dependency graph (no invalid refs)
    - **Methods**: Add `to_json() -> str`, `from_json(data: str) -> Plan`, `model_dump_json()`
    - **Dependencies**: Task 1.3
    - **Acceptance**: Plan validates all constraints from PRD FR-1.6
  - [ ] 1.5 Implement PlanManifest model for fast listing
    - **File**: `packages/cli/src/aurora_cli/planning/models.py`
    - **Action**: Create PlanManifest(BaseModel) with fields:
      - `version: str = Field(default="1.0")` - Manifest schema version
      - `updated_at: datetime = Field(default_factory=datetime.utcnow)` - Last update
      - `active_plans: list[str] = Field(default_factory=list)` - Active plan IDs
      - `archived_plans: list[str] = Field(default_factory=list)` - Archived plan IDs
      - `stats: dict = Field(default_factory=dict)` - Aggregate statistics
    - **Purpose**: Track all plans without loading full plan files for fast listing
    - **Dependencies**: Task 1.2
    - **Acceptance**: Manifest serializes/deserializes to ~/.aurora/plans/manifest.json
  - [ ] 1.6 Write unit tests for all Pydantic models
    - **File**: `tests/unit/cli/test_planning_models.py`
    - **Tests**:
      - Valid model creation for Plan, Subgoal, PlanManifest
      - Validation error messages for invalid plan_id, goal length, subgoal count
      - JSON serialization round-trip
      - Enum string value serialization
      - Subgoal dependency validation (invalid reference)
    - **Pattern**: Follow `tests/unit/cli/test_agent_manifest.py` patterns
    - **Dependencies**: Tasks 1.2-1.5
    - **Acceptance**: >=95% coverage for models.py, all error messages tested

- [ ] 2.0 Implement Validation Error System and Custom Exceptions (FR-1.7)
  - [ ] 2.1 Create VALIDATION_MESSAGES dictionary
    - **File**: `packages/cli/src/aurora_cli/planning/errors.py`
    - **Action**: Define dictionary with all error codes and message templates from PRD FR-1.7:
      ```python
      VALIDATION_MESSAGES = {
          "PLAN_ID_INVALID_FORMAT": "Plan ID must be 'NNNN-slug' format (e.g., '0001-oauth-auth'). Got: {value}",
          "PLAN_ID_ALREADY_EXISTS": "Plan ID '{plan_id}' already exists. Use 'aur plan show {plan_id}' to view it.",
          "PLAN_NOT_FOUND": "Plan '{plan_id}' not found. Use 'aur plan list' to see available plans.",
          "PLAN_ALREADY_ARCHIVED": "Plan '{plan_id}' is already archived. Use 'aur plan list --archived' to view.",
          "GOAL_TOO_SHORT": "Goal must be at least 10 characters. Provide a clear description.",
          "GOAL_TOO_LONG": "Goal exceeds 500 characters. Consider breaking into multiple plans.",
          "SUBGOAL_ID_INVALID": "Subgoal ID must be 'sg-N' format (e.g., 'sg-1'). Got: {value}",
          "SUBGOAL_DEPENDENCY_INVALID": "Subgoal '{subgoal_id}' references unknown dependency: {dependency}",
          "SUBGOAL_CIRCULAR_DEPENDENCY": "Circular dependency detected: {cycle}",
          "TOO_MANY_SUBGOALS": "Plan has {count} subgoals (max 10). Consider splitting.",
          "AGENT_FORMAT_INVALID": "Agent must start with '@' (e.g., '@full-stack-dev'). Got: {value}",
          "AGENT_NOT_FOUND": "Agent '{agent}' not found. Use 'aur agents list' to see available agents.",
          "PLANS_DIR_NOT_INITIALIZED": "Planning directory not initialized. Run 'aur plan init' first.",
          "PLANS_DIR_NO_WRITE_PERMISSION": "Cannot write to {path}. Check directory permissions.",
          "PLANS_DIR_ALREADY_EXISTS": "Planning directory already exists at {path}. Use --force to reinitialize.",
          "PLAN_FILE_CORRUPT": "Plan file '{file}' is corrupt or invalid JSON. Try regenerating.",
          "PLAN_FILE_MISSING": "Expected file '{file}' not found in plan directory.",
          "CONTEXT_FILE_NOT_FOUND": "Context file '{file}' not found. Check the path.",
          "NO_INDEXED_MEMORY": "No indexed memory available. Run 'aur mem index .' or use '--context <file>'.",
          "ARCHIVE_FAILED": "Failed to archive plan: {error}. Plan remains in active state.",
          "ARCHIVE_ROLLBACK": "Archive failed, rolled back to original state. Error: {error}",
      }
      ```
    - **Dependencies**: Task 1.1
    - **Acceptance**: Every error code has {placeholder} syntax for dynamic values
  - [ ] 2.2 Implement PlanningError base exception class
    - **File**: `packages/cli/src/aurora_cli/planning/errors.py`
    - **Action**: Create base exception:
      ```python
      class PlanningError(Exception):
          def __init__(self, code: str, **kwargs):
              self.code = code
              self.message = VALIDATION_MESSAGES.get(code, code).format(**kwargs)
              super().__init__(self.message)
      ```
    - **Pattern**: Follow `AuroraError` from `aurora_cli/errors.py`
    - **Dependencies**: Task 2.1
    - **Acceptance**: `str(error)` returns formatted message with substituted values
  - [ ] 2.3 Implement specific exception subclasses
    - **File**: `packages/cli/src/aurora_cli/planning/errors.py`
    - **Action**: Create exception hierarchy:
      ```python
      class PlanNotFoundError(PlanningError):
          def __init__(self, plan_id: str):
              super().__init__("PLAN_NOT_FOUND", plan_id=plan_id)

      class PlanValidationError(PlanningError):
          pass  # Uses various codes

      class PlanDirectoryError(PlanningError):
          pass  # For init/permission errors

      class PlanArchiveError(PlanningError):
          pass  # For archive failures
      ```
    - **Dependencies**: Task 2.2
    - **Acceptance**: Each exception type provides context-specific error message
  - [ ] 2.4 Write unit tests for error handling
    - **File**: `tests/unit/cli/test_planning_errors.py`
    - **Tests**:
      - VALIDATION_MESSAGES has all expected codes
      - PlanningError formats message with kwargs
      - PlanNotFoundError includes plan_id in message
      - All error codes produce valid messages (no KeyError)
    - **Dependencies**: Tasks 2.1-2.3
    - **Acceptance**: 100% of VALIDATION_MESSAGES codes tested

- [ ] 3.0 Implement Result Types for Graceful Degradation (FR-1.8, FR-1.9)
  - [ ] 3.1 Create InitResult dataclass
    - **File**: `packages/cli/src/aurora_cli/planning/results.py`
    - **Action**: Create dataclass:
      ```python
      @dataclass
      class InitResult:
          success: bool
          path: Path | None = None
          created: bool = False
          message: str | None = None
          warning: str | None = None
          error: str | None = None
      ```
    - **Pattern**: Commands return InitResult instead of raising exceptions
    - **Dependencies**: Task 1.1
    - **Acceptance**: Supports success+warning and failure+error states
  - [ ] 3.2 Create PlanResult dataclass
    - **File**: `packages/cli/src/aurora_cli/planning/results.py`
    - **Action**: Create dataclass:
      ```python
      @dataclass
      class PlanResult:
          success: bool
          plan: Plan | None = None
          plan_dir: Path | None = None
          warnings: list[str] | None = None
          error: str | None = None
      ```
    - **Purpose**: Returned from create_plan() to capture partial success (plan created but with warnings)
    - **Dependencies**: Task 1.4 (Plan model)
    - **Acceptance**: Can express "plan created but agent gaps detected"
  - [ ] 3.3 Create ListResult dataclass
    - **File**: `packages/cli/src/aurora_cli/planning/results.py`
    - **Action**: Create dataclass:
      ```python
      @dataclass
      class ListResult:
          plans: list[PlanSummary]
          warning: str | None = None
          errors: list[str] | None = None
      ```
    - **Purpose**: Returned from list_plans() with graceful degradation
    - **Dependencies**: Task 3.6 (PlanSummary)
    - **Acceptance**: Returns empty list with warning if not initialized
  - [ ] 3.4 Create ShowResult dataclass
    - **File**: `packages/cli/src/aurora_cli/planning/results.py`
    - **Action**: Create dataclass:
      ```python
      @dataclass
      class ShowResult:
          success: bool
          plan: Plan | None = None
          plan_dir: Path | None = None
          files_status: dict[str, bool] | None = None  # {"plan.md": True, "prd.md": False}
          error: str | None = None
      ```
    - **Purpose**: Returned from show_plan() with file existence status
    - **Dependencies**: Task 1.4 (Plan model)
    - **Acceptance**: files_status shows which of 4 files exist
  - [ ] 3.5 Create ArchiveResult dataclass
    - **File**: `packages/cli/src/aurora_cli/planning/results.py`
    - **Action**: Create dataclass:
      ```python
      @dataclass
      class ArchiveResult:
          success: bool
          plan: Plan | None = None
          source_dir: Path | None = None
          target_dir: Path | None = None
          duration_days: int | None = None
          error: str | None = None
      ```
    - **Purpose**: Returned from archive_plan() with archive location
    - **Dependencies**: Task 1.4 (Plan model)
    - **Acceptance**: Includes computed duration_days
  - [ ] 3.6 Create PlanSummary dataclass for listing
    - **File**: `packages/cli/src/aurora_cli/planning/results.py`
    - **Action**: Create dataclass:
      ```python
      @dataclass
      class PlanSummary:
          plan_id: str
          goal: str  # Truncated to 50 chars
          created_at: datetime
          status: str
          subgoal_count: int
          agent_gaps: int

          @classmethod
          def from_plan(cls, plan: Plan, status: str) -> "PlanSummary":
              return cls(
                  plan_id=plan.plan_id,
                  goal=plan.goal[:50] + "..." if len(plan.goal) > 50 else plan.goal,
                  created_at=plan.created_at,
                  status=status,
                  subgoal_count=len(plan.subgoals),
                  agent_gaps=len(plan.agent_gaps)
              )
      ```
    - **Purpose**: Lightweight summary for fast listing
    - **Dependencies**: Task 1.4 (Plan model)
    - **Acceptance**: from_plan() factory creates summary from full Plan
  - [ ] 3.7 Write unit tests for result types
    - **File**: `tests/unit/cli/test_planning_results.py`
    - **Tests**:
      - Each result type instantiates correctly
      - PlanSummary.from_plan() truncates long goals
      - Result types handle None values
      - Success vs error states work correctly
    - **Dependencies**: Tasks 3.1-3.6
    - **Acceptance**: All result types have example usage in docstrings

- [ ] 4.0 Implement `aur plan init` Command (FR-1.1)
  - [ ] 4.1 Implement init_planning_directory core function
    - **File**: `packages/cli/src/aurora_cli/planning/core.py`
    - **Action**: Create function:
      ```python
      def init_planning_directory(path: Path | None = None) -> InitResult:
          """Initialize planning directory with graceful degradation."""
          target = path or Path.home() / ".aurora" / "plans"

          # Check if already initialized
          if (target / "active").exists():
              return InitResult(success=True, path=target, created=False,
                  warning="Planning directory already exists. No changes made.")

          # Check write permissions
          if not os.access(target.parent, os.W_OK):
              return InitResult(success=False, path=target,
                  error=VALIDATION_MESSAGES["PLANS_DIR_NO_WRITE_PERMISSION"].format(path=target))

          # Create directories
          (target / "active").mkdir(parents=True, exist_ok=True)
          (target / "archive").mkdir(parents=True, exist_ok=True)
          (target / "templates").mkdir(parents=True, exist_ok=True)

          # Create manifest
          manifest = PlanManifest()
          (target / "manifest.json").write_text(manifest.model_dump_json(indent=2))

          return InitResult(success=True, path=target, created=True,
              message=f"Planning directory initialized at {target}")
      ```
    - **Dependencies**: Tasks 1.5, 2.1, 3.1
    - **Acceptance**: Creates active/, archive/, templates/, manifest.json; <100ms latency
  - [ ] 4.2 Add planning configuration to Config class
    - **File**: `packages/cli/src/aurora_cli/config.py`
    - **Action**: Add fields to Config dataclass:
      ```python
      plans_directory: str = "~/.aurora/plans"
      plans_auto_archive: bool = False

      def get_plans_path(self) -> str:
          """Get expanded absolute plans directory path."""
          return str(Path(self.plans_directory).expanduser().resolve())
      ```
    - **Dependencies**: None
    - **Acceptance**: Config.get_plans_path() returns expanded path
  - [ ] 4.3 Create plan command group and init subcommand
    - **File**: `packages/cli/src/aurora_cli/commands/plan.py`
    - **Action**: Create Click command group:
      ```python
      @click.group(name="plan")
      def plan_group() -> None:
          """Plan management commands.

          Create, list, show, and archive development plans.
          """
          pass

      @plan_group.command(name="init")
      @click.option("--path", "-p", type=click.Path(), default=None,
          help="Custom directory path (default: ~/.aurora/plans)")
      @handle_errors
      def init_command(path: str | None) -> None:
          """Initialize planning directory structure."""
          result = init_planning_directory(Path(path) if path else None)

          if result.warning:
              console.print(f"[yellow]{result.warning}[/]")
          elif result.error:
              console.print(f"[red]{result.error}[/]")
              raise click.Abort()
          else:
              console.print(f"[green]{result.message}[/]")
              console.print(f"  - Active plans: {result.path}/active/")
              console.print(f"  - Archived plans: {result.path}/archive/")
              console.print("\nReady to create plans with: aur plan create \"goal\"")
      ```
    - **Pattern**: Follow `agents_group` from `commands/agents.py`
    - **Dependencies**: Tasks 4.1, 4.2
    - **Acceptance**: `aur plan init` creates directories with Rich output
  - [ ] 4.4 Register plan command group in main.py
    - **File**: `packages/cli/src/aurora_cli/main.py`
    - **Action**: Add import and registration:
      ```python
      from aurora_cli.commands.plan import plan_group
      # ... after other registrations ...
      cli.add_command(plan_group)
      ```
    - **Dependencies**: Task 4.3
    - **Acceptance**: `aur plan --help` shows subcommands
  - [ ] 4.5 Write unit tests for init command
    - **File**: `tests/unit/cli/test_plan_commands.py`
    - **Tests**:
      - `test_init_creates_directory_structure` - creates active/, archive/, manifest.json
      - `test_init_already_initialized` - returns warning, no changes
      - `test_init_permission_denied` - returns error (mock os.access)
      - `test_init_custom_path` - uses --path option
      - `test_init_cli_output` - verifies Rich console output
    - **Fixtures**: Use tmp_path for isolated testing
    - **Pattern**: Follow `tests/unit/cli/test_agents_commands.py`
    - **Dependencies**: Tasks 4.1-4.4
    - **Acceptance**: All init scenarios covered with CliRunner

- [ ] 5.0 Implement `/aur:plan` Slash Command with SOAR Integration (FR-1.2)
  - [ ] 5.1 Add python-slugify dependency
    - **File**: `packages/cli/pyproject.toml`
    - **Action**: Add to dependencies: `python-slugify>=8.0`
    - **Dependencies**: None
    - **Acceptance**: `from slugify import slugify` works
  - [ ] 5.2 Implement plan ID generation function
    - **File**: `packages/cli/src/aurora_cli/planning/generator.py`
    - **Action**: Create function:
      ```python
      from slugify import slugify

      def generate_plan_id(goal: str, existing_ids: list[str]) -> str:
          """Generate unique plan ID from goal.
          Format: NNNN-slug (e.g., 0001-oauth-auth)
          """
          base_slug = slugify(goal, max_length=30, word_boundary=True)
          next_num = len(existing_ids) + 1
          return f"{next_num:04d}-{base_slug}"
      ```
    - **Dependencies**: Task 5.1
    - **Acceptance**: IDs are unique, slug max 30 chars, 4-digit number
  - [ ] 5.3 Implement context retrieval wrapper
    - **File**: `packages/cli/src/aurora_cli/planning/generator.py`
    - **Action**: Create function:
      ```python
      from aurora_cli.memory import MemoryRetriever

      def retrieve_context(
          goal: str,
          context_paths: list[Path] | None = None,
          config: Config | None = None
      ) -> tuple[list[CodeChunk], list[str]]:
          """Retrieve context for planning with priority strategy.

          Returns: (chunks, warnings)
          Priority:
          1. If context_paths provided, use those files only
          2. If indexed memory available, retrieve by goal
          3. Return empty with warning
          """
          warnings = []
          retriever = MemoryRetriever(config=config)

          if context_paths:
              chunks = retriever.load_context_files(context_paths)
              return chunks, warnings

          if retriever.has_indexed_memory():
              chunks = retriever.retrieve(goal, limit=20)
              return chunks, warnings

          warnings.append(VALIDATION_MESSAGES["NO_INDEXED_MEMORY"])
          return [], warnings
      ```
    - **Dependencies**: MemoryRetriever from PRD 0016 (assumed available)
    - **Acceptance**: Follows priority strategy from PRD FR-1.2 Step 2
  - [ ] 5.4 Implement SOAR decomposition wrapper
    - **File**: `packages/cli/src/aurora_cli/planning/generator.py`
    - **Action**: Create function:
      ```python
      from aurora_soar.orchestrator import SOAROrchestrator

      def decompose_goal(
          goal: str,
          context: list[CodeChunk],
          agents: list[AgentInfo]
      ) -> tuple[Plan, list[str]]:
          """Decompose goal using SOAR orchestrator.

          Returns: (plan, warnings)
          """
          warnings = []
          try:
              orchestrator = SOAROrchestrator()
              result = orchestrator.decompose(goal, context, agents)

              # Convert SOAR result to Plan model
              subgoals = [
                  Subgoal(
                      id=f"sg-{i+1}",
                      title=sg.title,
                      description=sg.description,
                      recommended_agent=f"@{sg.agent_id}",
                      dependencies=[f"sg-{d}" for d in sg.dependencies]
                  )
                  for i, sg in enumerate(result.subgoals)
              ]

              complexity = assess_complexity(len(subgoals), result.dependency_depth)
              plan = Plan(goal=goal, subgoals=subgoals, complexity=complexity)
              return plan, warnings

          except Exception as e:
              warnings.append(f"SOAR decomposition failed: {e}. Using simple plan.")
              # Fallback: single subgoal
              plan = Plan(
                  goal=goal,
                  subgoals=[Subgoal(id="sg-1", title="Implement goal",
                      description=goal, recommended_agent="@full-stack-dev")],
                  complexity=Complexity.SIMPLE
              )
              return plan, warnings
      ```
    - **Dependencies**: SOAROrchestrator (assumed available), Task 1.3-1.4
    - **Acceptance**: Graceful fallback if SOAR fails
  - [ ] 5.5 Implement agent recommendation function
    - **File**: `packages/cli/src/aurora_cli/planning/generator.py`
    - **Action**: Create function:
      ```python
      from aurora_cli.agent_discovery import AgentManifest

      def recommend_agents(
          plan: Plan,
          manifest: AgentManifest
      ) -> tuple[Plan, list[str]]:
          """Match subgoals to agents, detect gaps.

          Returns: (updated_plan, agent_gaps)
          """
          agent_gaps = []

          for subgoal in plan.subgoals:
              agent_id = subgoal.recommended_agent.lstrip("@")
              agent = manifest.get_agent(agent_id)

              if agent is None:
                  subgoal.agent_exists = False
                  agent_gaps.append(agent_id)
              else:
                  subgoal.agent_exists = True

          plan.agent_gaps = agent_gaps
          return plan, agent_gaps
      ```
    - **Dependencies**: AgentManifest from PRD 0016 (assumed available)
    - **Acceptance**: Each subgoal has agent_exists flag, gaps collected
  - [ ] 5.6 Create Jinja2 templates for plan files
    - **File**: `packages/cli/src/aurora_cli/planning/templates.py`
    - **Action**: Create templates matching PRD Section 5.1-5.3:
      ```python
      PLAN_MD_TEMPLATE = """# Plan: {{ plan.goal }}

      **Plan ID**: {{ plan.plan_id }}
      **Created**: {{ plan.created_at.strftime('%Y-%m-%d %H:%M:%S') }}
      **Status**: {{ plan.status.value }}
      **Complexity**: {{ plan.complexity.value }}

      ## Goal

      {{ plan.goal }}

      ## Subgoals

      {% for sg in plan.subgoals %}
      ### Subgoal {{ loop.index }}: {{ sg.title }}
      **Agent**: {{ sg.recommended_agent }} {% if sg.agent_exists %}✓{% else %}⚠ NOT FOUND{% endif %}
      **Dependencies**: {% if sg.dependencies %}{{ sg.dependencies | join(', ') }}{% else %}None{% endif %}

      {{ sg.description }}

      {% endfor %}

      ## Agent Assignments

      | Subgoal | Agent | Status |
      |---------|-------|--------|
      {% for sg in plan.subgoals %}
      | {{ loop.index }}. {{ sg.title }} | {{ sg.recommended_agent }} | {% if sg.agent_exists %}✓ Found{% else %}⚠ Not found{% endif %} |
      {% endfor %}

      ## Next Steps

      1. Review this plan for accuracy
      2. Generate detailed PRD: Continue with /aur:plan
      3. Execute: /aur:implement {{ plan.plan_id }}
      """

      PRD_MD_TEMPLATE = """# PRD: {{ plan.goal }}

      **Plan ID**: {{ plan.plan_id }}
      **Status**: Pending expansion

      > This PRD will be generated when you continue with /aur:plan.
      > Review the plan.md first, then confirm to expand.
      """

      TASKS_MD_TEMPLATE = """# Tasks: {{ plan.goal }}

      **Plan ID**: {{ plan.plan_id }}
      **Status**: Pending generation

      > Tasks will be generated when you continue with /aur:plan.
      """
      ```
    - **Dependencies**: Add jinja2 to pyproject.toml if not present
    - **Acceptance**: Templates render with Plan model data
  - [ ] 5.7 Implement plan file generation function
    - **File**: `packages/cli/src/aurora_cli/planning/generator.py`
    - **Action**: Create function:
      ```python
      from jinja2 import Template
      from .templates import PLAN_MD_TEMPLATE, PRD_MD_TEMPLATE, TASKS_MD_TEMPLATE

      def generate_plan_files(plan: Plan, plans_dir: Path) -> Path:
          """Generate plan.md, prd.md, tasks.md, agents.json in plan directory.

          Uses atomic write (temp file + rename) for safety.
          """
          plan_dir = plans_dir / "active" / plan.plan_id
          plan_dir.mkdir(parents=True, exist_ok=True)

          # Render templates
          plan_md = Template(PLAN_MD_TEMPLATE).render(plan=plan)
          prd_md = Template(PRD_MD_TEMPLATE).render(plan=plan)
          tasks_md = Template(TASKS_MD_TEMPLATE).render(plan=plan)

          # Write files atomically
          _atomic_write(plan_dir / "plan.md", plan_md)
          _atomic_write(plan_dir / "prd.md", prd_md)
          _atomic_write(plan_dir / "tasks.md", tasks_md)
          _atomic_write(plan_dir / "agents.json", plan.model_dump_json(indent=2))

          return plan_dir

      def _atomic_write(path: Path, content: str) -> None:
          """Write file atomically using temp file + rename."""
          temp_path = path.with_suffix(path.suffix + ".tmp")
          temp_path.write_text(content)
          temp_path.rename(path)
      ```
    - **Dependencies**: Tasks 5.6, 1.4
    - **Acceptance**: All 4 files created atomically
  - [ ] 5.8 Implement create_plan core function
    - **File**: `packages/cli/src/aurora_cli/planning/core.py`
    - **Action**: Create orchestration function:
      ```python
      def create_plan(
          goal: str,
          context_paths: list[Path] | None = None,
          from_file: Path | None = None,
          config: Config | None = None
      ) -> PlanResult:
          """Create plan with full pipeline.

          Pipeline:
          1. Validate goal
          2. Check plans_dir initialized
          3. Load existing plan IDs
          4. Retrieve context
          5. SOAR decompose
          6. Recommend agents
          7. Generate files
          8. Update manifest
          """
          warnings = []

          # Validate goal
          if len(goal) < 10:
              return PlanResult(success=False, error=VALIDATION_MESSAGES["GOAL_TOO_SHORT"])

          if len(goal) > 500:
              return PlanResult(success=False, error=VALIDATION_MESSAGES["GOAL_TOO_LONG"])

          # Check initialized
          plans_dir = Path(config.get_plans_path() if config else "~/.aurora/plans").expanduser()
          if not (plans_dir / "active").exists():
              return PlanResult(success=False, error=VALIDATION_MESSAGES["PLANS_DIR_NOT_INITIALIZED"])

          # Get existing IDs for uniqueness
          existing_ids = _get_existing_plan_ids(plans_dir)

          # Retrieve context
          context, ctx_warnings = retrieve_context(goal, context_paths, config)
          warnings.extend(ctx_warnings)

          # Load agent manifest
          try:
              from aurora_cli.commands.agents import get_manifest
              manifest = get_manifest()
          except Exception as e:
              warnings.append(f"Agent manifest unavailable: {e}")
              manifest = AgentManifest()

          # SOAR decompose
          plan, decomp_warnings = decompose_goal(goal, context, manifest.agents)
          warnings.extend(decomp_warnings)

          # Generate plan ID
          plan.plan_id = generate_plan_id(goal, existing_ids)
          plan.context_sources = ["custom_files" if context_paths else "indexed_memory"]

          # Recommend agents
          plan, agent_gaps = recommend_agents(plan, manifest)
          if agent_gaps:
              warnings.append(f"Agent gaps detected: {', '.join(agent_gaps)}")

          # Generate files
          try:
              plan_dir = generate_plan_files(plan, plans_dir)
          except Exception as e:
              return PlanResult(success=False, error=f"Failed to save plan: {e}")

          # Update manifest
          _update_manifest(plans_dir, plan.plan_id, "active")

          return PlanResult(
              success=True,
              plan=plan,
              plan_dir=plan_dir,
              warnings=warnings if warnings else None
          )
      ```
    - **Dependencies**: Tasks 5.2-5.7, 4.1
    - **Acceptance**: Full pipeline completes in <10s
  - [ ] 5.9 Create slash commands module
    - **File**: `packages/cli/src/aurora_cli/slash_commands/__init__.py`
    - **Action**: Create module init:
      ```python
      """Slash commands for Claude Code integration."""
      from .aur_plan import slash_plan
      from .aur_archive import slash_archive

      __all__ = ["slash_plan", "slash_archive"]
      ```
    - **Dependencies**: None
    - **Acceptance**: Module importable
  - [ ] 5.10 Implement /aur:plan slash command
    - **File**: `packages/cli/src/aurora_cli/slash_commands/aur_plan.py`
    - **Action**: Create slash command with checkpoint:
      ```python
      from rich.console import Console
      from rich.progress import Progress, SpinnerColumn, TextColumn
      from rich.panel import Panel
      import click

      console = Console()

      def slash_plan(
          goal: str | None = None,
          from_file: Path | None = None,
          context: list[Path] | None = None
      ) -> None:
          """Generate plan via /aur:plan slash command.

          Interactive flow:
          1. Generate plan.md + agents.json
          2. Show preview (first 3 subgoals)
          3. Prompt: "Continue to generate PRD and tasks? (Y/n)"
          4. On Y: Generate prd.md + tasks.md
          """
          # Get goal from file if provided
          if from_file:
              goal = _extract_goal_from_file(from_file)

          if not goal:
              console.print("[red]Goal required. Use --from-file or provide goal string.[/]")
              return

          # Show progress
          with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
              task = progress.add_task("Decomposing goal with SOAR...", total=None)
              result = create_plan(goal, context_paths=context)
              progress.update(task, description="Complete!")

          if not result.success:
              console.print(f"[red]{result.error}[/]")
              return

          # Show warnings
          if result.warnings:
              for warning in result.warnings:
                  console.print(f"[yellow]Warning: {warning}[/]")

          # Show preview
          console.print(f"\n[bold green]Plan created:[/] {result.plan_dir}/")
          console.print(Panel(_format_plan_preview(result.plan), title="Preview"))

          # Checkpoint prompt
          if click.confirm("Continue to generate detailed PRD and tasks?", default=True):
              # Phase 2 expansion would happen here (out of scope for Phase 1)
              console.print("[dim]PRD and task expansion coming in Phase 2[/]")

          console.print(f"\n[bold]Next:[/] /aur:implement {result.plan.plan_id}")

      def _format_plan_preview(plan: Plan) -> str:
          """Format first 3 subgoals for preview."""
          lines = []
          for i, sg in enumerate(plan.subgoals[:3]):
              status = "✓" if sg.agent_exists else "⚠ missing"
              lines.append(f"{i+1}. {sg.title}")
              lines.append(f"   Agent: {sg.recommended_agent} ({status})")
          if len(plan.subgoals) > 3:
              lines.append(f"   ... and {len(plan.subgoals) - 3} more subgoals")
          return "\n".join(lines)
      ```
    - **Dependencies**: Tasks 5.8, 3.2
    - **Acceptance**: Interactive flow matches PRD FR-1.2 output
  - [ ] 5.11 Write unit tests for plan generation
    - **File**: `tests/unit/cli/test_planning_generator.py`
    - **Tests**:
      - `test_generate_plan_id_unique` - IDs are unique and formatted correctly
      - `test_generate_plan_id_slug_truncation` - Long goals truncated to 30 chars
      - `test_retrieve_context_with_files` - Uses provided files
      - `test_retrieve_context_from_memory` - Uses indexed memory
      - `test_retrieve_context_empty` - Returns warning when no context
      - `test_decompose_goal_success` - SOAR returns subgoals
      - `test_decompose_goal_fallback` - Fallback on SOAR failure
      - `test_recommend_agents_with_gaps` - Detects missing agents
      - `test_generate_plan_files` - All 4 files created
    - **Mocks**: Mock SOAROrchestrator, MemoryRetriever, AgentManifest
    - **Dependencies**: Tasks 5.2-5.7
    - **Acceptance**: >=85% coverage for generator.py
  - [ ] 5.12 Write integration test for plan creation
    - **File**: `tests/integration/cli/test_plan_workflow.py`
    - **Tests**:
      - `test_create_plan_end_to_end` - Full workflow with tmp_path
      - Verify plan.md, prd.md, tasks.md, agents.json created
      - Verify agents.json matches Plan schema
      - Verify manifest.json updated
    - **Dependencies**: All Task 5.x subtasks
    - **Acceptance**: E2E test passes with real file operations

- [ ] 6.0 Implement `aur plan list` Command (FR-1.3)
  - [ ] 6.1 Implement list_plans core function
    - **File**: `packages/cli/src/aurora_cli/planning/core.py`
    - **Action**: Create function:
      ```python
      def list_plans(
          archived: bool = False,
          all_plans: bool = False,
          config: Config | None = None
      ) -> ListResult:
          """List plans with filtering.

          Returns empty list with warning if not initialized.
          """
          plans_dir = Path(config.get_plans_path() if config else "~/.aurora/plans").expanduser()

          if not plans_dir.exists():
              return ListResult(plans=[], warning=VALIDATION_MESSAGES["PLANS_DIR_NOT_INITIALIZED"])

          plans = []
          errors = []

          # Determine directories to scan
          dirs_to_scan = []
          if all_plans or not archived:
              dirs_to_scan.append(("active", plans_dir / "active"))
          if all_plans or archived:
              dirs_to_scan.append(("archived", plans_dir / "archive"))

          for status, scan_dir in dirs_to_scan:
              if not scan_dir.exists():
                  continue

              for plan_path in scan_dir.iterdir():
                  if not plan_path.is_dir():
                      continue

                  agents_json = plan_path / "agents.json"
                  if not agents_json.exists():
                      errors.append(f"Missing agents.json in {plan_path.name}")
                      continue

                  try:
                      plan = Plan.model_validate_json(agents_json.read_text())
                      plans.append(PlanSummary.from_plan(plan, status))
                  except Exception as e:
                      errors.append(f"Invalid plan {plan_path.name}: {e}")

          # Sort by creation date (newest first)
          plans.sort(key=lambda p: p.created_at, reverse=True)

          return ListResult(plans=plans, errors=errors if errors else None)
      ```
    - **Dependencies**: Tasks 1.4, 3.3, 3.6
    - **Acceptance**: List completes in <200ms for 100 plans
  - [ ] 6.2 Implement aur plan list CLI command
    - **File**: `packages/cli/src/aurora_cli/commands/plan.py`
    - **Action**: Add list subcommand:
      ```python
      @plan_group.command(name="list")
      @click.option("--archived", is_flag=True, help="Show archived plans only")
      @click.option("--all", "all_plans", is_flag=True, help="Show all plans")
      @click.option("--format", "-f", "output_format", type=click.Choice(["rich", "json"]),
          default="rich", help="Output format")
      @handle_errors
      def list_command(archived: bool, all_plans: bool, output_format: str) -> None:
          """List plans with filtering options."""
          result = list_plans(archived=archived, all_plans=all_plans)

          if result.warning:
              console.print(f"[yellow]{result.warning}[/]")
              return

          if output_format == "json":
              import json
              data = [{"plan_id": p.plan_id, "goal": p.goal, "status": p.status,
                       "created_at": p.created_at.isoformat(), "subgoals": p.subgoal_count,
                       "agent_gaps": p.agent_gaps} for p in result.plans]
              console.print(json.dumps(data, indent=2))
              return

          if not result.plans:
              console.print("[yellow]No plans found.[/]")
              return

          # Rich table output
          table = Table(title=f"{'Archived' if archived else 'Active'} Plans ({len(result.plans)} total)")
          table.add_column("ID", style="cyan")
          table.add_column("Goal", style="white", max_width=40)
          table.add_column("Created", style="green")
          table.add_column("Status", style="blue")
          table.add_column("Subgoals", justify="right")
          table.add_column("Agents", style="yellow")

          for p in result.plans:
              agent_status = "✓ All found" if p.agent_gaps == 0 else f"⚠ {p.agent_gaps} gap(s)"
              table.add_row(
                  p.plan_id, p.goal, p.created_at.strftime("%Y-%m-%d"),
                  p.status, str(p.subgoal_count), agent_status
              )

          console.print(table)

          if result.errors:
              for error in result.errors:
                  console.print(f"[dim red]{error}[/]")
      ```
    - **Pattern**: Follow list_command from commands/agents.py
    - **Dependencies**: Task 6.1
    - **Acceptance**: Output matches PRD FR-1.3 format
  - [ ] 6.3 Write unit tests for list command
    - **File**: `tests/unit/cli/test_plan_commands.py`
    - **Tests**:
      - `test_list_active_plans` - Default shows active only
      - `test_list_archived_plans` - --archived shows archived only
      - `test_list_all_plans` - --all shows both
      - `test_list_empty` - Shows message when no plans
      - `test_list_not_initialized` - Shows warning
      - `test_list_json_output` - --format json outputs valid JSON
      - `test_list_sorted_by_date` - Newest first
    - **Dependencies**: Tasks 6.1-6.2
    - **Acceptance**: All list scenarios covered

- [ ] 7.0 Implement `aur plan show` Command (FR-1.4)
  - [ ] 7.1 Implement show_plan core function
    - **File**: `packages/cli/src/aurora_cli/planning/core.py`
    - **Action**: Create function:
      ```python
      def show_plan(
          plan_id: str,
          archived: bool = False,
          config: Config | None = None
      ) -> ShowResult:
          """Show plan details with file status."""
          plans_dir = Path(config.get_plans_path() if config else "~/.aurora/plans").expanduser()

          # Search for plan
          search_dir = plans_dir / ("archive" if archived else "active")
          plan_dirs = list(search_dir.glob(f"*{plan_id}*"))

          if not plan_dirs:
              # Check other location
              other_dir = plans_dir / ("active" if archived else "archive")
              other_matches = list(other_dir.glob(f"*{plan_id}*"))
              if other_matches:
                  hint = "--archived" if not archived else "without --archived"
                  return ShowResult(success=False,
                      error=f"Plan '{plan_id}' found in {'archive' if not archived else 'active'}. Use {hint}.")
              return ShowResult(success=False, error=VALIDATION_MESSAGES["PLAN_NOT_FOUND"].format(plan_id=plan_id))

          plan_dir = plan_dirs[0]
          agents_json = plan_dir / "agents.json"

          if not agents_json.exists():
              return ShowResult(success=False, error=VALIDATION_MESSAGES["PLAN_FILE_MISSING"].format(file="agents.json"))

          try:
              plan = Plan.model_validate_json(agents_json.read_text())
          except Exception as e:
              return ShowResult(success=False, error=VALIDATION_MESSAGES["PLAN_FILE_CORRUPT"].format(file=str(agents_json)))

          # Check file status
          files_status = {
              "plan.md": (plan_dir / "plan.md").exists(),
              "prd.md": (plan_dir / "prd.md").exists(),
              "tasks.md": (plan_dir / "tasks.md").exists(),
              "agents.json": True,
          }

          return ShowResult(success=True, plan=plan, plan_dir=plan_dir, files_status=files_status)
      ```
    - **Dependencies**: Tasks 1.4, 3.4, 2.1
    - **Acceptance**: Returns full plan or helpful error
  - [ ] 7.2 Implement aur plan show CLI command
    - **File**: `packages/cli/src/aurora_cli/commands/plan.py`
    - **Action**: Add show subcommand:
      ```python
      @plan_group.command(name="show")
      @click.argument("plan_id")
      @click.option("--archived", is_flag=True, help="Search in archived plans")
      @click.option("--format", "-f", "output_format", type=click.Choice(["rich", "json"]),
          default="rich", help="Output format")
      @handle_errors
      def show_command(plan_id: str, archived: bool, output_format: str) -> None:
          """Display detailed plan information."""
          result = show_plan(plan_id, archived=archived)

          if not result.success:
              console.print(f"[red]{result.error}[/]")
              raise click.Abort()

          plan = result.plan

          if output_format == "json":
              console.print(plan.model_dump_json(indent=2))
              return

          # Rich panel output
          console.print(f"\n[bold]Plan: {plan.plan_id}[/]")
          console.print("=" * 60)
          console.print(f"Goal:        {plan.goal}")
          console.print(f"Created:     {plan.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
          console.print(f"Status:      {plan.status.value}")
          console.print(f"Complexity:  {plan.complexity.value}")
          console.print(f"Context:     {', '.join(plan.context_sources) or 'None'}")

          console.print(f"\n[bold]Subgoals ({len(plan.subgoals)}):[/]")
          console.print("-" * 60)

          for i, sg in enumerate(plan.subgoals, 1):
              status = "[green]✓[/]" if sg.agent_exists else "[yellow]⚠ NOT FOUND[/]"
              console.print(f"\n{i}. {sg.title} ({sg.recommended_agent} {status})")
              console.print(f"   {sg.description}")
              deps = ", ".join(sg.dependencies) if sg.dependencies else "None"
              console.print(f"   [dim]Dependencies: {deps}[/]")

              if not sg.agent_exists:
                  console.print(f"\n   [yellow]⚠ Agent Gap Detected:[/]")
                  console.print(f"   - Missing: {sg.recommended_agent}")
                  console.print(f"   - Fallback: Use @business-analyst or @full-stack-dev")

          console.print(f"\n[bold]Files:[/]")
          for fname, exists in result.files_status.items():
              status = "[green]✓[/]" if exists else "[red]✗[/]"
              console.print(f"  {status} {fname}")

          console.print(f"\n[bold]Next Steps:[/]")
          console.print(f"1. Review plan for accuracy")
          console.print(f"2. Execute: /aur:implement {plan.plan_id}")
          console.print(f"3. Archive: /aur:archive {plan.plan_id}")
      ```
    - **Pattern**: Follow show_command from commands/agents.py
    - **Dependencies**: Task 7.1
    - **Acceptance**: Output matches PRD FR-1.4 format
  - [ ] 7.3 Write unit tests for show command
    - **File**: `tests/unit/cli/test_plan_commands.py`
    - **Tests**:
      - `test_show_existing_plan` - Shows full plan details
      - `test_show_archived_plan` - --archived finds archived plan
      - `test_show_plan_not_found` - Error message with suggestion
      - `test_show_wrong_location_hint` - Suggests correct flag
      - `test_show_json_output` - --format json outputs valid JSON
      - `test_show_file_status` - Shows which files exist
      - `test_show_agent_gaps` - Displays gap warnings
    - **Dependencies**: Tasks 7.1-7.2
    - **Acceptance**: All show scenarios covered

- [ ] 8.0 Implement `/aur:archive` Slash Command (FR-1.5)
  - [ ] 8.1 Implement archive_plan core function with rollback
    - **File**: `packages/cli/src/aurora_cli/planning/core.py`
    - **Action**: Create function with atomic operation:
      ```python
      import shutil
      from datetime import datetime

      def archive_plan(
          plan_id: str,
          force: bool = False,
          config: Config | None = None
      ) -> ArchiveResult:
          """Archive plan with atomic move and rollback on failure."""
          plans_dir = Path(config.get_plans_path() if config else "~/.aurora/plans").expanduser()
          active_dir = plans_dir / "active"
          archive_dir = plans_dir / "archive"

          # Find the plan
          plan_dirs = list(active_dir.glob(f"*{plan_id}*"))
          if not plan_dirs:
              return ArchiveResult(success=False, error=VALIDATION_MESSAGES["PLAN_NOT_FOUND"].format(plan_id=plan_id))

          source_dir = plan_dirs[0]
          plan_name = source_dir.name

          # Load and validate plan
          agents_json = source_dir / "agents.json"
          try:
              plan = Plan.model_validate_json(agents_json.read_text())
          except Exception as e:
              return ArchiveResult(success=False, error=VALIDATION_MESSAGES["PLAN_FILE_CORRUPT"].format(file=str(agents_json)))

          # Check if already archived
          if plan.status == PlanStatus.ARCHIVED:
              return ArchiveResult(success=False, error=VALIDATION_MESSAGES["PLAN_ALREADY_ARCHIVED"].format(plan_id=plan_id))

          # Calculate archive path
          timestamp = datetime.now().strftime("%Y-%m-%d")
          target_dir = archive_dir / f"{timestamp}-{plan_name}"

          # Atomic archive with rollback
          backup_json = agents_json.read_text()

          try:
              # Update plan metadata
              plan.status = PlanStatus.ARCHIVED
              plan.archived_at = datetime.utcnow()
              plan.duration_days = (plan.archived_at - plan.created_at).days

              # Write updated agents.json
              agents_json.write_text(plan.model_dump_json(indent=2))

              # Move directory
              archive_dir.mkdir(parents=True, exist_ok=True)
              shutil.move(str(source_dir), str(target_dir))

              # Update manifest
              _update_manifest(plans_dir, plan_name, "archive", f"{timestamp}-{plan_name}")

              return ArchiveResult(
                  success=True,
                  plan=plan,
                  source_dir=source_dir,
                  target_dir=target_dir,
                  duration_days=plan.duration_days
              )

          except Exception as e:
              # Rollback
              if agents_json.exists():
                  agents_json.write_text(backup_json)
              if target_dir.exists() and not source_dir.exists():
                  shutil.move(str(target_dir), str(source_dir))

              return ArchiveResult(success=False, error=VALIDATION_MESSAGES["ARCHIVE_ROLLBACK"].format(error=str(e)))
      ```
    - **Dependencies**: Tasks 1.4, 3.5, 2.1
    - **Acceptance**: Archive is atomic - succeeds completely or fails with rollback
  - [ ] 8.2 Implement /aur:archive slash command
    - **File**: `packages/cli/src/aurora_cli/slash_commands/aur_archive.py`
    - **Action**: Create slash command:
      ```python
      from rich.console import Console
      import click

      console = Console()

      def slash_archive(plan_id: str, yes: bool = False) -> None:
          """Archive plan via /aur:archive slash command."""
          # Confirmation unless --yes
          if not yes:
              if not click.confirm(f"Archive plan '{plan_id}'? This will move files to archive/"):
                  console.print("[yellow]Archive cancelled.[/]")
                  return

          result = archive_plan(plan_id)

          if not result.success:
              console.print(f"[red]{result.error}[/]")
              return

          console.print(f"\n[bold green]Plan archived: {result.plan.plan_id}[/]")
          console.print(f"\nArchived to: {result.target_dir}/")
          console.print(f"Duration: {result.duration_days} days")
          console.print(f"\nFiles archived:")
          for fname in ["plan.md", "prd.md", "tasks.md", "agents.json"]:
              console.print(f"  [green]✓[/] {fname}")

          console.print(f"\nView archived plans: aur plan list --archived")
      ```
    - **Dependencies**: Task 8.1
    - **Acceptance**: Output matches PRD FR-1.5 format
  - [ ] 8.3 Add archive subcommand to CLI
    - **File**: `packages/cli/src/aurora_cli/commands/plan.py`
    - **Action**: Add archive subcommand:
      ```python
      @plan_group.command(name="archive")
      @click.argument("plan_id")
      @click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
      @handle_errors
      def archive_command(plan_id: str, yes: bool) -> None:
          """Archive a completed plan."""
          from aurora_cli.slash_commands.aur_archive import slash_archive
          slash_archive(plan_id, yes=yes)
      ```
    - **Dependencies**: Task 8.2
    - **Acceptance**: Both `aur plan archive` and `/aur:archive` work
  - [ ] 8.4 Write unit tests for archive functionality
    - **File**: `tests/unit/cli/test_plan_commands.py`
    - **Tests**:
      - `test_archive_plan_success` - Plan moved to archive/YYYY-MM-DD-id/
      - `test_archive_plan_not_found` - Error when plan doesn't exist
      - `test_archive_already_archived` - Error when already archived
      - `test_archive_rollback_on_failure` - Rollback tested with mock failure
      - `test_archive_updates_manifest` - Manifest updated correctly
      - `test_archive_yes_flag` - --yes skips confirmation
      - `test_archive_duration_calculation` - duration_days calculated correctly
    - **Dependencies**: Tasks 8.1-8.3
    - **Acceptance**: Rollback tested with simulated failure
  - [ ] 8.5 Write integration test for archive workflow
    - **File**: `tests/integration/cli/test_plan_workflow.py`
    - **Tests**:
      - `test_archive_workflow_end_to_end`:
        1. Create plan (from Task 5)
        2. Archive plan
        3. Verify files in archive/YYYY-MM-DD-id/
        4. Verify manifest updated (active decreased, archived increased)
        5. Verify original location empty
    - **Dependencies**: All Task 8.x and Task 5.x subtasks
    - **Acceptance**: Full archive workflow tested

---

## Phase 1 Completion Criteria

From PRD Section 2.3:

- [ ] `aur plan init` scaffolds planning directory (<100ms)
- [ ] `/aur:plan "goal"` generates plan.md in <10s
- [ ] `aur plan list` shows active plans (<200ms)
- [ ] `aur plan show <id>` displays plan details (<500ms)
- [ ] `/aur:archive <id>` moves to archive with timestamp (<1s)
- [ ] Four-file structure working: plan.md, prd.md, tasks.md, agents.json
- [ ] Memory integration operational (uses indexed codebase via MemoryRetriever)
- [ ] Agent recommendation working (uses AgentManifest from PRD 0016)
- [ ] All quality gates passed (>=85% coverage, 0 mypy errors)

---

## Dependencies

**PRD 0016 Prerequisites** (assumed available):
- `AgentManifest` from `aurora_cli.agent_discovery.models`
- `MemoryRetriever` from `aurora_cli.memory.retrieval`
- Agent discovery commands (`aur agents list/search/show/refresh`)

**Existing Aurora Components** (reuse):
- `SOAROrchestrator` from `aurora_soar.orchestrator` - for goal decomposition
- `SQLiteStore` from `aurora_core.store` - for indexed memory access
- `Config` from `aurora_cli.config` - for configuration management
- `handle_errors` from `aurora_cli.errors` - for error handling decorator

**External Dependencies** (add to pyproject.toml):
- `python-slugify>=8.0` - for plan ID slug generation
- `jinja2>=3.1` - for template rendering

---

## Out of Scope (Phase 2 and Phase 3)

**DO NOT IMPLEMENT in Phase 1**:
- PRD expansion with acceptance criteria (`aur plan expand --to-prd`) - Phase 2
- Code-aware task generation (`aur plan tasks`) - Phase 2
- File path resolution with line numbers from memory - Phase 2
- Agent subprocess execution (`/aur:implement`) - Phase 3
- Progress tracking via checkbox parsing - Phase 3
- State persistence and checkpoint recovery - Phase 3
- Resume from checkpoint - Phase 3

---

## Quality Gates

| Gate | Requirement | Tool |
|------|-------------|------|
| Code Coverage | >=85% for planning package | pytest-cov |
| Type Checking | 0 mypy errors (strict mode) | mypy |
| Linting | 0 critical issues | ruff |
| Security | No hardcoded secrets | bandit |

---

## Task Summary

| Parent Task | Sub-tasks | Key Deliverables |
|-------------|-----------|------------------|
| 1.0 Pydantic Models | 6 | Plan, Subgoal, PlanManifest models |
| 2.0 Error System | 4 | VALIDATION_MESSAGES, exceptions |
| 3.0 Result Types | 7 | InitResult, PlanResult, etc. |
| 4.0 `aur plan init` | 5 | Directory structure, CLI command |
| 5.0 `/aur:plan` | 12 | SOAR integration, file generation |
| 6.0 `aur plan list` | 3 | List with filtering, JSON output |
| 7.0 `aur plan show` | 3 | Show details, file status |
| 8.0 `/aur:archive` | 5 | Atomic archive with rollback |

**Total: 8 parent tasks, 45 sub-tasks**

---

*Generated by: 2-generate-tasks agent*
*PRD Reference: `/tasks/0017-prd-aurora-planning-system.md`*
*Phase: 1 of 3*
