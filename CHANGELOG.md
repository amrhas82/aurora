# Changelog

All notable changes to the AURORA project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.11.2] - 2026-02-02

### Removed

**CLI Cleanup - Deprecated Commands:**
- `aur health` command (dead code, never registered)
- `aur query` command (MCP-dependent, deprecated)
- `aur plan init` and `aur plan create` subcommands (use `aur goals` instead)
- `aur verify` command (merged into `aur doctor`)

**MCP Deprecation:**
- `MCPFunctionalChecks` class from health checks (~360 lines)
- MCP configuration functions from init helpers
- All MCP-related test files (~20 files, ~5,000 lines)

### Added

**Doctor Command Enhancements:**
- New `InstallationChecks` class verifying:
  - Python version (>= 3.10)
  - Core package imports (aurora_core, aurora_context_code, aurora_soar, aurora_reasoning, aurora_cli)
- Installation checks merged from removed `aur verify` command

**Init Command Enhancements:**
- `create_default_config()` function creates `.aurora/config.json` with sensible defaults
- Config file created automatically during `aur init`

### Changed

**Spawn Command:**
- `--verbose` is now the default (use `--quiet` or `-q` to suppress output)
- Changed from `--verbose` flag to `--verbose/--quiet` boolean pair

### Fixed

**Test Suite:**
- Fixed `Subgoal` model field mismatch in plan command tests (`recommended_agent` → `assigned_agent`)
- Fixed timezone-naive vs timezone-aware datetime issues in archive tests
- Removed broken MCP patches from init unified tests

## [0.10.1] - 2026-01-30

### Added

**SOAR Pipeline Enhancements:**
- Vague word detection in complexity assessment
  - Detects ambiguous terms: "it", "this", "that", "something", "stuff", "thing", etc.
  - Increases complexity score for queries needing clarification
- Complexity-based subgoal limits (2-4-6 by complexity tier)
  - SIMPLE: max 2 subgoals
  - MEDIUM/MODERATE: max 4 subgoals
  - COMPLEX/CRITICAL: max 6 subgoals
  - Reduces over-decomposition and improves response times
- `log_path` field in aur soar response metadata
  - Returns path to SOAR reasoning log for debugging
- SOAR cache circuit breaker and failed log cleanup
  - Prevents repeated cache failures from blocking queries
  - Automatic cleanup of corrupted cache entries

### Fixed

**SOAR Pipeline:**
- Normalize dependency format in collect phase (sg-N → int conversion)
- Handle both int and string dependency formats in Phase 8 respond
- Display Phase 3 when using cached decomposition for better UX
- Show cached decomposition indicator in aur soar Phase 3
- Correct phase_callback attribute name (removed underscore prefix)
- Add SOAR complexity value mapping (MEDIUM → MODERATE for consistency)
- Use SOAR Phase 1 complexity assessment instead of reassessing locally
- Fail explicitly when SOAR verification fails instead of degrading to fallback
- Normalize dependency format in verify_lite (sg-N → int)

**Agent Discovery:**
- Enable agent discovery for all 20 tools via dynamic path resolution
- Fixed agent path resolution for tools outside standard directories

**Memory Search:**
- Improve search UX with better help message and silent model loading
- Suppress verbose embedding model loading messages

**Goals Command:**
- Resolve aur goals failures (examples file path + enum value)

**CI/CD:**
- Add timeouts to CI workflow to prevent runaway jobs

### Changed

**Documentation:**
- Update subgoal limits to 2-4-6 in aur-soar and aur-goals command docs
- Update aur-soar and aur-goals with v0.10.0 optimization details
- Clarify upgrade path from 0.9.x to 0.10.0 in README
- Add pip uninstall command to README

**Code Organization:**
- Organize documentation and scripts into proper directories
- ML dependency improvements and cleanup

## [0.10.0] - 2026-01-26

### Added

**Epic 1: Memory Search Performance (Foundation Caching)**
- Module-level HybridRetriever instance caching with LRU policy
  - Cache keyed by `(db_path, config_hash)` with configurable size (default: 10)
  - Reduces cold search time by 30-40% (15-19s → 10-12s)
  - Configurable via `AURORA_RETRIEVER_CACHE_SIZE` and `AURORA_RETRIEVER_CACHE_TTL`
- ActivationEngine singleton caching per database path
  - Reduces warm search time by 40-50% (4-5s → 2-3s)
  - Automatically shared across all retrievers using same database
- Shared QueryEmbeddingCache with LRU policy
  - Cache hit rate typically >60% in SOAR multi-phase operations
  - Reduces embedding computation on repeated queries
- Enhanced BM25 index persistence validation
  - Disk-cached at `.aurora/indexes/bm25_index.pkl`
  - Load time <100ms (vs 9.7s rebuild)
- Cache invalidation support via `aur mem index` and config changes
- Comprehensive caching guide in documentation

**Epic 2: Lazy BM25 Loading + Dual-Hybrid Fallback**
- Lazy BM25 index loading deferred to first retrieve() call
  - Creation time: 150-250ms → 0.0ms (99.9% improvement)
  - Thread-safe double-checked locking ensures single load
  - No impact on search performance (index loaded once and reused)
- Dual-hybrid fallback mode (BM25 + Activation) when embeddings unavailable
  - Automatically triggers when embedding model not installed or `AURORA_EMBEDDING_PROVIDER=none`
  - Quality testing showed 85-100% overlap with tri-hybrid (BM25 + Activation + Semantic)
  - Graceful degradation from tri-hybrid → dual-hybrid → activation-only
- Performance benchmarks and qualitative validation

**Planning System Refactor (Complete R1-R9)**
- New `/aur:tasks` slash command for regenerating tasks from PRD
  - Available in all 20 tool configurators (6 commands total: search, get, plan, tasks, implement, archive)
  - Reads prd.md, goals.json, agents.json and regenerates tasks.md
  - Includes same TDD hints and format as /aur:plan
- `source_file` field added to Subgoal and SubgoalData models
  - Tracks primary source file for each subgoal
  - Extracted from LLM responses with validation
  - Supports both code files and markdown documentation
  - Backward compatible (optional field, defaults to None)
  - Integrated into both `aur goals` and `aur soar` decomposition
- agents.json schema documentation in PLAN_REFERENCES
  - Complete template with required and optional fields
  - Reference to official schema file
- TDD hints in tasks.md template
  - Format: `tdd: yes|no` and `verify: command`
  - Guidelines for when to use TDD (models, APIs, bugs) vs when to skip (docs, config)
  - Matches 2-generate-tasks agent pattern
- 3-SIMPLE-STEPS.md comprehensive planning guide created
  - Step-by-step workflow documentation
  - Code-aware (with goals.json) vs prompt-based planning paths
  - Artifact generation order and dependencies

**Task Execution Improvements**
- Wave-based execution with context passing for dependent tasks
- Topological sorting for dependency-aware parallel execution
- Invalid dependency reference validation

### Changed

**Planning System**
- Plan folders now use slug-only format (e.g., `improve-search` instead of `0001-improve-search`)
  - Backward compatible: numbered plans (NNNN-slug) still work
  - Folder override: Re-running same goal replaces previous attempt
  - Plan ID validators accept both formats
- Artifact generation order now explicitly documented
  - Order: plan.md → prd.md → design.md → agents.json → tasks.md
  - tasks.md generated LAST as it depends on PRD content
- Plan templates emphasize goals.json as recommended but optional
  - Code-aware planning (with goals.json) preferred for production
  - Prompt-based planning (skip goals.json) valid for simpler workflows

**Code Quality**
- Applied 4,425 safe formatting fixes across codebase
- Replaced all `datetime.utcnow()` with `datetime.now(timezone.utc)` (Python 3.12+ compatibility)
- Fixed all ARG001-ARG005 ruff violations (104 unused argument fixes)
- Prefixed unused parameters with underscore for clarity

### Fixed

**Planning System**
- Fixed `aur plan view` schema mismatch
  - Changed `sg.recommended_agent` → `sg.assigned_agent`
  - Removed non-existent `sg.agent_exists` checks
  - Added ideal_agent gap detection
- Removed non-existent command references from templates
  - Removed `aur plan validate` references
  - Removed `--specs` flag from `aur plan list`
  - Replaced `show --json --deltas-only` with `view --format json`
- Fixed configurator method signature incompatibilities (codex.py, kilocode.py)

**Memory Search**
- Fixed embedding model wait logic in mem search
  - Changed from BM25-only fallback to proper embedding wait
- Fixed dual-hybrid fallback test configuration (caplog logger)

**SOAR & Spawner**
- Fixed fallback when SOAR decomposition returns empty subgoals
- Fixed retry_feedback parameter passing to decompose_query
- Fixed _verbose parameter name in _display_goals_results call
- Corrected parameter names in function calls (Phase 2B Task 15.1)

**Type Checking & Linting**
- Resolved all Pyright type-checking errors
  - Fixed Config attribute access with type: ignore comments
  - Fixed Subgoal model attribute references
  - Fixed method signatures to match base classes
- Fixed datetime deprecation warnings throughout codebase
- Removed 12 unused test variables in collect tests
- Removed commented code in packages/cli

### Removed

**Slash Commands**
- Removed `aur:checkpoint` slash command from all tool configurations
  - All 20 tool configurators now generate 6 commands: search, get, plan, tasks, implement, archive
  - Removed checkpoint template from `templates/slash_commands.py`
  - Removed checkpoint command from `templates/commands.py`
  - Existing `.aurora/checkpoints/` directories are preserved (not deleted)
  - Config keys related to checkpoints are silently ignored for backward compatibility

**CLI Implementation**
- Removed checkpoint-related CLI options from `aur spawn` command
  - Removed `--resume`, `--list-checkpoints`, `--clean-checkpoints`, `--no-checkpoint` flags
  - Deleted `packages/cli/src/aurora_cli/planning/checkpoint.py`
  - Deleted `packages/cli/src/aurora_cli/execution/checkpoint.py`
  - Removed checkpoint helper functions from `spawn_helpers.py`

**Planning System**
- Removed spec generation from planning system
  - Plan creation now generates 5 files instead of 8 (plan.md, prd.md, design.md, agents.json, tasks.md)
  - Removed 4 capability spec files: planning, commands, validation, schemas specs
  - Updated all references from "8 files" to "5 files"
  - Removed spec validation from validate_plan_structure()
  - Removed spec entries from show_plan() file status

### Performance

**Startup Improvements**
- Lazy BM25 index loading: 99.9% improvement (150-250ms → 0ms)
- Module-level retriever caching: 30-40% faster cold searches (15-19s → 10-12s)
- Activation engine singleton: 40-50% faster warm searches (4-5s → 2-3s)
- BM25 index persistence: <100ms load vs 9.7s rebuild
- Query embedding caching: >60% cache hit rate in multi-phase operations

**Memory Efficiency**
- Thread-safe double-checked locking for lazy initialization
- LRU caching prevents unbounded memory growth
- Shared instances reduce memory footprint

### Documentation

**New Guides**
- Created `docs/guides/3-SIMPLE-STEPS.md` - Comprehensive planning workflow guide
- Added Epic 1 caching guide with configuration examples
- Added Epic 2 documentation (lazy loading + dual-hybrid fallback)
- Added comprehensive Phase 2 lessons learned

**Updated References**
- Updated PLAN_REFERENCES with agents.json schema and examples
- Updated PLAN_STEPS with artifact generation order
- Updated README.md with real command output examples
- Updated CODE_QUALITY_REPORT with Phase 2A and 2B results
- Updated all documentation to reflect 6-command structure (tasks added)
- Removed checkpoint references from all documentation
- Removed spec file references from all documentation

### Testing

**New Tests**
- Added performance tests for caching (Epic 1 Task 6.0)
- Added integration tests for memory search caching (Epic 1 Task 5.0)
- Added wave execution and performance regression tests
- Added 18 planning system tests for spec removal and enhancements
- Added dual-hybrid fallback tests

**Test Improvements**
- Fixed test fixtures to use assigned_agent instead of recommended_agent
- Added None checks for optional fields in ShowResult tests
- Configured proper caplog logging for pytest

## [0.9.4] - 2026-01-19

### Fixed

**Code Quality:**
- Fixed lint errors in multiple files
  - Removed unused variables in `packages/cli/src/aurora_cli/commands/memory.py`
  - Removed unused variables in `packages/cli/src/aurora_cli/concurrent_executor.py`
  - Removed unused variables in `packages/cli/src/aurora_cli/file_change_aggregator.py`
  - Removed unused variables in `packages/spawner/src/aurora_spawner/spawner.py`
  - Fixed import ordering across all packages (243 auto-fixes)

### Changed

**Project Organization:**
- Moved development documentation from root to `docs/development/`
  - `ADHOC_SPAWNING_VALIDATION.md`
  - `EARLY_DETECTION_ENHANCEMENT_ANALYSIS.md`
  - `GOALS_SOAR_REFACTOR_PLAN.md`
  - `PARALLEL_SPAWN_FAILURE_ANALYSIS.md`
  - `STARTUP_OPTIMIZATIONS.md`
- Moved utility scripts from root to `tools/`
  - `benchmark_startup.py`
  - `profile_indexing.py`
  - `profile_indexing_detailed.py`
- Removed duplicate `CLAUDE (copy).md` file
- Root directory now contains only essential files: README, CHANGELOG, CLAUDE.md, OPENCODE.md, conftest.py

---

## [0.9.3] - 2026-01-19

### Fixed

**Spawner: Rate Limit Error Handling:**
- Rate limit errors now fail fast without wasteful retries
  - Detects patterns: "rate limit", "429", "quota exceeded", "too many requests"
  - Prevents 2-4 retry attempts that would hit the same quota limit
  - Retry policy now skips rate limits with clear message: "Rate limit exceeded - quota exhausted, retries would fail"
- Circuit breaker no longer opens on rate limit errors
  - Rate limits are external API constraints, not agent failures
  - Agents remain healthy in circuit breaker even when quota exhausted
  - Early exit in `record_failure()` prevents tracking as circuit breaker failure
- New `FailureReason.RATE_LIMIT` metric for separate tracking
  - Distinct from inference failures in observability system
  - Allows monitoring of quota-related issues separately
- Files changed:
  - `packages/spawner/src/aurora_spawner/observability.py` - Added RATE_LIMIT enum
  - `packages/spawner/src/aurora_spawner/spawner.py` - Added rate limit detection
  - `packages/spawner/src/aurora_spawner/timeout_policy.py` - Prevent rate limit retries
  - `packages/spawner/src/aurora_spawner/circuit_breaker.py` - Skip circuit breaker for rate limits

### Testing

- Comprehensive test coverage for rate limit handling:
  - 19 new unit tests in `tests/unit/spawner/test_rate_limit_handling.py`
  - Tests cover detection, retry prevention, circuit breaker isolation, metrics, and edge cases
  - All existing tests continue to pass

### Documentation

- Removed "Rate Limit Error Handling" from FEATURES_BACKLOG.md (now implemented)
- Updated backlog last modified date to January 19, 2026

---

## [0.9.1] - 2026-01-16

### Performance

**Startup Optimization - 40-60% Faster Initialization:**
- **Lazy embedding model imports**: Deferred torch/sentence-transformers loading eliminates 20-30s startup delay
  - Only loads ML dependencies when semantic search is actually used
  - Commands like `aur mem index`, `aur soar`, `aur goals` now start instantly
  - Embedding model loads on-demand during first semantic search
- **SQLite connection pooling**: Reuses validated connections across Store instances
  - Eliminates redundant schema checks (60-90ms saved per invocation)
  - Thread-safe per-database pool locks
  - Skips repeated PRAGMA execution for pooled connections
- **Deferred schema initialization**: Schema validation deferred until first database access
  - Store creation now takes <1ms (was 30-50ms)
  - Schema checks only run once per connection pool
- **Combined health monitoring**: Merged two config methods into one
  - Single config lookup pass (saves 10-15ms)
  - Reduced logging verbosity
- **Lazy agent loading**: Discovery adapter loads agents on-demand
  - Eliminates 25-40ms of manifest parsing at startup
  - Agents still available when needed, just loaded lazily

**Total Impact:**
- Cold start: 150-250ms → 60-100ms (40-60% faster)
- Warm start with pooled connections: 150-250ms → 30-50ms (70-80% faster)
- Commands without semantic search: Nearly instant startup (no ML loading)

**Affected Commands:**
- `aur soar` - Orchestrator startup optimized
- `aur goals` - Goal decomposition starts faster
- `aur mem index` - Indexing starts immediately (model loads during processing)
- `aur mem search` - Search command starts instantly (model loads on first query)

### Changed

**Database Layer:**
- New `ConnectionPool` class in `packages/core/src/aurora_core/store/connection_pool.py`
- `SQLiteStore` now uses deferred schema initialization
- Connection pooling enabled by default for better performance

**Orchestrator:**
- Combined `_configure_proactive_health_checks()` and `_configure_early_detection()`
- Health monitoring configuration now single-pass

**CLI Commands:**
- Removed eager agent registry population from `aur soar`
- Discovery adapter handles agent loading on-demand

### Testing

- New benchmark script: `benchmark_startup.py`
- Performance test suite in `tests/performance/`
- Documentation in `docs/PERFORMANCE_TESTING.md`

---

## [0.9.0] - 2026-01-16

### Added

**Spawner: Unified Parallel Execution Infrastructure:**
- New `spawn_parallel_tracked()` function as single source of truth for mature spawning
  - Stagger delays (default 5s) between agent starts to avoid API burst limits
  - Per-task heartbeat monitoring with HeartbeatEmitter + HeartbeatMonitor
  - Global timeout calculation based on waves and policy (num_waves * policy_max + stagger + buffer)
  - Circuit breaker pre-checks for fast-fail on known broken agents
  - Retry with exponential backoff + LLM fallback
  - Execution metadata collection (early_terminations, fallback_count, retried_tasks, etc.)
  - Spinner display during execution showing active task count and elapsed time
- Both `aur spawn` and SOAR collect phase now use the same infrastructure
- New CLI options for `aur spawn`:
  - `--stagger-delay` (default: 5.0s)
  - `--policy` (default: patient)
  - `--max-concurrent` (default: 4)
  - `--no-fallback` to disable LLM fallback
- New spawner configuration in `defaults.json`:
  ```json
  "spawner": {
    "max_concurrent": 4,
    "stagger_delay": 5.0,
    "default_policy": "patient"
  }
  ```
- `display_name` field in `SpawnTask` for progress display even when agent is None

### Changed

**Goals-SOAR Integration Refactor (Unified UX):**
- Removed brittle adapter layer between SOAR and goals command
- Pydantic validators now coerce instead of reject:
  - Agent names: automatically add '@' prefix if missing
  - Subgoal IDs: automatically add 'sg-' prefix if numeric
  - Dependencies: automatically convert numeric IDs to 'sg-N' format
- Removed normalization functions (`normalize_agent_name`, `normalize_dependency_id`)
- `aur goals` and `aur soar` now have unified UX until divergence point
- SOAR phases 1-5 display naturally in both commands
- Goals command shows agent assignments table after SOAR phases complete

**CLI Output Improvements:**
- Ad-hoc spawned agents now display correct agent name instead of "llm"
- Spinner shows during Phase 5 Collect: `⠧ Working... 3 active (125s)`
- Suppressed verbose HuggingFace Hub warnings during embedding model loading
  - No more `WARNING:huggingface_hub.utils._http` noise during `aur soar`
  - Retries still work, just not logged to console
- Observability failure logs changed from WARNING/ERROR to DEBUG level
  - Progress callbacks handle user-facing feedback
  - Clean console output during normal operation
  - Use `--verbose` or `--debug` to see detailed logs

**SOAR Collect Phase:**
- Refactored to use `spawn_parallel_tracked()` instead of inline `tracked_spawn()`
- Sets `display_name=agent.id` when creating SpawnTasks for proper progress display
- Collect phase now inherits all spawner improvements (stagger, heartbeat, global timeout)

### Fixed

- Spinner regression in Phase 5 - spinner now properly displays and cleans up
- Ad-hoc agent display name showing "llm" instead of actual agent name
- Missing `finally` block in `spawn_parallel_tracked()` to stop spinner
- HuggingFace warning spam during model loading

### Performance

- Stagger delays prevent API burst limits and improve success rates
- Global timeout prevents hanging on stuck agents
- Heartbeat monitoring detects and handles stalled agents

### Testing

- 40 unit tests passing for planning models (Goals-SOAR refactor)
- All spawner functionality tested via existing test suite
- Clean output verified with manual `aur soar` and `aur spawn` testing

---

## [0.8.0] - 2026-01-15

### Added

**Spawner: Early Failure Detection & Circuit Breaker:**
- Circuit breaker pattern with CLOSED/OPEN/HALF_OPEN states (2 failures → skip agent for 120s)
- Early error detection with 11 regex patterns (rate limit, 429, connection errors, auth failures)
- Per-attempt failure tracking for faster circuit opening within same query
- Soft error handling: timeouts/rate-limits don't stop execution of other agents
- Heartbeat emitter support for real-time progress tracking
- All spawner logs changed to DEBUG level for clean CLI output
- New file: `packages/spawner/src/aurora_spawner/circuit_breaker.py` (~100 lines)

**SOAR UI Enhancements:**
- Plan Decomposition table display after Phase 4 verification
  - Shows subgoal number, description, and assigned agent
  - Spawned agents marked with asterisk (*) indicator
- Summary panel with intelligent gap detection
  - Format: "X subgoals • Y assigned • Z spawned"
  - Lists missing agents that will fallback to LLM
  - Proper singular/plural grammar (1 subgoal vs 2 subgoals)
- `is_spawn` flag propagation from verify_lite through orchestrator to UI

### Changed

**SOAR Phase Improvements:**
- Collect phase now distinguishes soft vs hard errors
  - Soft errors (timeout, rate limit, quota) continue execution
  - Hard errors (auth failures, code errors) stop immediately
- Timeouts don't block other agents from running in parallel
- Better error messages and user feedback throughout pipeline

**Memory:**
- `aur mem search` now records access and updates activation scores
- ACT-R decay formula applied after each search (frequency + recency)
- Chunks retrieved more often get higher activation in future searches

### Fixed

- Summary panel grammar: "1 subgoals" → "1 subgoal"
- Gap detection using `is_spawn` flag instead of unreliable string matching
- Non-friendly WARNING logs changed to DEBUG level
- Clean CLI output with no verbose error messages during normal operation

### Performance

- Circuit breaker prevents wasting time on broken agents (skip after 2 failures)
- Error patterns kill processes within 5s instead of waiting for 300s timeout
- Parallel agent execution continues even when some agents fail

---

## [0.6.7] - 2026-01-12

### Improved

**CLI Output Enhancements:**
- Added "For more details: aur mem stats" hint after indexing issues summary
- Added log file path display: "Skipped files logged to: .aurora/logs/index.log"
- Improved user guidance when indexing encounters warnings or errors

**Documentation Updates:**
- Updated `aur agents list` documentation with all subcommands (`--all`, `--category`, `search`, `refresh`)
- Updated `aur init` documentation with 3-step flow, `--tools` flag, and agent refresh option
- Added agent discovery explanation and re-run options to init docs
- Updated Quick Reference table with new agent commands

## [0.6.6] - 2026-01-12

### Fixed

- Synchronized all package versions to 0.6.6
- Pre-commit lint fixes (MD5→SHA256, docstrings, f-strings)

## [0.6.5] - 2026-01-12

### Added

**TypeScript/JavaScript Parser Support:**
- Added `TypeScriptParser` for `.ts` and `.tsx` files
  - Extracts classes, functions, arrow functions, methods, interfaces, and type aliases
  - JSDoc comment extraction
  - Handles React/JSX syntax
- Added `JavaScriptParser` for `.js`, `.jsx`, `.mjs`, `.cjs` files
  - Extracts classes, functions, arrow functions, function expressions, and methods
  - JSDoc comment extraction
- New dependencies: `tree-sitter-typescript>=0.20.0`, `tree-sitter-javascript>=0.20.0`
- Auto-registered in parser registry

**Memory Index Improvements:**
- File-level git blame caching for 336x speedup on subsequent function lookups
- Batch embedding using native sentence-transformers batching
- Two-line progress display with overall progress and phase detail
- Files-by-language breakdown in `aur mem stats` output
- Success rate now calculated from parseable files only (not all discovered)
- Detailed index log written to `.aurora/logs/index.log` with:
  - Summary statistics
  - Files by language breakdown
  - Failed files with error messages
  - Skipped files (parseable but no extractable elements)

### Fixed

- `aur init` tool detection and duplicate display issues
- Progress bar showing grey at 100% completion
- Total Files count in stats now matches language breakdown sum
- Warning help text now points to `aur mem stats`

## [0.6.2] - 2026-01-10

### Fixed

**Build Configuration:**
- Removed non-existent `headless/py.typed` reference from `aurora-soar` package build config
- Fixes `FileNotFoundError` during package installation in CI environments
- Note: The headless directory was removed in previous refactoring (commit 5299248), but pyproject.toml reference was left behind

## [0.6.1] - 2026-01-10

### Fixed

**Critical Dependency Fixes:**
- Fixed `aurora-implement` package name (was incorrectly named "implement")
- Added missing dependencies to `aurora-cli` package:
  - `aurora-reasoning>=0.1.0`
  - `aurora-planning>=0.1.0`
  - `aurora-spawner>=0.1.0`
  - `aurora-implement>=0.1.0`
- Updated all sub-package versions to 0.6.0 for consistency
- Fixes `ModuleNotFoundError: No module named 'aurora_spawner'` when installing from PyPI

**CI/CD Fixes:**
- Updated Makefile install targets to include all packages
- Updated GitHub Actions workflow to install spawner, implement, and planning packages
- Fixes 26 import errors in CI test suite

**What this means for users:**
- `pip install aurora-actr` now correctly installs all required packages
- Sprint 4 features (`aur goals`, `aur spawn`) now work out of the box
- No manual package installation required

## [0.6.0] - 2026-01-10

### Added - Planning Flow & Execution (PRD-0026: All 4 Sprints)

**`aur goals` Command:**
- New command for decomposing high-level goals into actionable subgoals with agent assignments
- SOAR-based goal decomposition with 2-7 subgoals per goal
- Automatic agent matching using keyword patterns and LLM fallback
- Memory context integration with ACT-R activation-based search
- Generates `goals.json` in `.aurora/plans/NNNN-slug/` for `/plan` skill integration
- Interactive user review flow with `$EDITOR` integration
- Validation: 10-500 character goals, CLI tool existence checking
- **Options:**
  - `--tool`, `-t`: CLI tool selection (claude/cursor/windsurf)
  - `--model`, `-m`: Model selection (sonnet/opus)
  - `--context`, `-c`: Context files for informed decomposition
  - `--no-decompose`: Skip decomposition for simple single-task goals
  - `--format`, `-f`: Output format (rich/json)
  - `--yes`, `-y`: Skip confirmation prompts
  - `--verbose`, `-v`: Show detailed progress

**Planning Flow Workflow:**
1. `aur goals "feature description"` - Decompose goal → creates `goals.json`
2. `/plan` skill in Claude Code - Generate PRD and tasks from `goals.json`
3. `aur implement` or `aur spawn` - Execute tasks sequentially or in parallel

**Documentation:**
- `docs/commands/aur-goals.md` - Comprehensive command reference (200+ lines)
- `docs/workflows/planning-flow.md` - Complete workflow guide (400+ lines)
- `examples/goals/goals-example.json` - Reference OAuth2 authentication example
- Updated `README.md` with planning flow quick start
- Updated `COMMANDS.md` with goals command and goals.json format specification

**Test Coverage:**
- 24 unit tests for goals command (100% coverage of core functionality)
- 4 E2E tests for command workflow
- 5 E2E tests for goals → /plan integration
- **Total: 33 new tests passing**

**Related Files:**
- Core implementation: `packages/cli/src/aurora_cli/commands/goals.py`
- Planning models: Extended `packages/cli/src/aurora_cli/planning/models.py`
- Planning core: Extended `packages/cli/src/aurora_cli/planning/core.py`
- Tests: `packages/cli/tests/test_commands/test_goals.py`
- E2E tests: `tests/e2e/test_goals_command.py`, `tests/e2e/test_goals_plan_flow.py`

**Configuration:**
- Environment variables: `AURORA_GOALS_TOOL`, `AURORA_GOALS_MODEL`
- Config file support: `[goals]` section with `default_tool` and `default_model`
- Resolution order: CLI flag → env var → config file → default

**`aur spawn` Command (Sprint 3):**
- New command for parallel task execution from terminal
- Reads `tasks.md` with agent metadata comments (`<!-- agent: X -->`)
- Parallel spawns CLI tools (claude, cursor, aider, etc.) per task
- Reports completion status with rich progress display
- Lightweight ~100-line spawning primitive (90% reduction vs complex orchestration)

**Enhanced `aur soar` Command (Sprint 3):**
- CLI-agnostic execution using `CLIPipeLLMClient`
- Parallel spawning for research sub-questions
- Terminal-based orchestrator for complex queries
- Tool/model resolution: CLI flag → env var → config → default

**Infrastructure (Sprints 1-2):**
- New `aurora-spawner` package: Core spawning primitives
- New `implement` package: In-Claude execution for `/implement` skill
- SOAR collect phase now uses real agent spawning (replaced `_mock_agent_execution()`)
- Deprecated `AgentRegistry`, unified on `agent_discovery` module
- Agent gap detection with LLM fallback for capability matching

### Changed

**Documentation Reorganization:**
- Consolidated 280+ scattered files into organized structure
- Created 4 main directories: `reference/`, `guides/`, `development/`, `archive/`
- Added 3 specialized directories: `commands/`, `workflows/`, `examples/`
- Created README.md index for each section
- Updated all internal documentation cross-references
- Moved root-level completion summaries to archive
- Comprehensive Sprint 4 documentation (1,695 lines COMMANDS.md, 1,954 lines TOOLS_GUIDE.md)

### Removed

**Test Artifacts:**
- Removed accidentally committed `MagicMock/` test fixtures from repository root
- Added to `.gitignore` to prevent future commits

## [0.5.0] - 2026-01-06

### Removed

- **Deprecated MCP tools** (`aurora_query`, `aurora_search`, `aurora_get`) - replaced by slash commands and CLI equivalents
- **MCP configuration from `aur init`** - now requires `--enable-mcp` flag for testing/development
- **MCP checks from `aur doctor`** - MCP FUNCTIONAL section no longer displayed

### Added

- **`/aur:implement` placeholder command** - Future Aurora native workflow command for plan-based implementation
- **`--enable-mcp` flag** - Opt-in flag for MCP server configuration during `aur init`
- **Comprehensive MCP deprecation documentation**:
  - `docs/MCP_DEPRECATION.md` - Architecture rationale and re-enablement guide
  - `docs/MIGRATION.md` - Tool replacement mapping and behavior changes
  - `docs/ROLLBACK.md` - Complete rollback procedures with 3 options

### Changed

- **Slash commands now recommended** - `/aur:search` and `/aur:get` are preferred over MCP tools
- **MCP infrastructure preserved** - All 20+ MCP configurators and session cache kept dormant for future use
- **Default behavior** - Fresh installations skip MCP configuration by default

### Migration Guide

**Tool Replacements:**

| Deprecated MCP Tool | CLI Replacement | Slash Command | Notes |
|---------------------|-----------------|---------------|-------|
| `aurora_query` | `aur soar "query"` | N/A | Full SOAR pipeline execution |
| `aurora_search` | `aur mem search "query"` | `/aur:search "query"` | Formatted table output |
| `aurora_get` | N/A | `/aur:get N` | Session cache retrieval |

**Breaking Changes:** None - deprecated tools were already replaced by superior alternatives.

**Re-enablement:** Use `aur init --enable-mcp --tools=claude` to configure MCP for testing/development.

**Rollback Options:**
1. Git tag: `git checkout mcp-deprecation-baseline` (complete revert)
2. Feature flag: Set `"mcp": {"enabled": true}` in config (fastest, no code changes)
3. Revert commits: See `docs/ROLLBACK.md` for detailed instructions

### Reference

- **PRD**: `docs/prd/PRD-0024-mcp-tool-deprecation.md`
- **Git Tag**: `mcp-deprecation-baseline` (rollback baseline)
- **Documentation**: `docs/MCP_DEPRECATION.md`, `docs/MIGRATION.md`, `docs/ROLLBACK.md`

## [0.4.0] - 2026-01-05

### BREAKING CHANGES

**Package Structure Simplified:**
- All sub-packages (`aurora-core`, `aurora-cli`, etc.) now bundled directly into `aurora-actr`
- Single package installation: `pip install aurora-actr` includes everything
- No more separate package dependencies on PyPI
- Package size: ~528KB (still tiny!)

**What This Means:**
- ✅ Users: Just run `pip install aurora-actr` - everything works
- ✅ Simpler installation, no verbose sub-package output
- ✅ All features included by default (CLI, MCP, memory, reasoning, planning, SOAR)
- ⚠️ If you had `aurora-cli` or other sub-packages installed separately, uninstall them first

**Optional Dependencies:**
- `[ml]`: Machine learning features (sentence-transformers, torch) for semantic embeddings
- `[dev]`: Development tools for contributors (pytest, mypy, ruff, etc.)

**Installation:**
```bash
# Full installation (recommended)
pip install aurora-actr

# With ML features
pip install aurora-actr[ml]

# Development (contributors only)
pip install aurora-actr[dev]
```

## [0.3.1] - 2026-01-05

## [0.3.0] - 2026-01-05

### Added - Developer Experience & Configuration

**Project-Local Configuration (Breaking Change):**
- All Aurora artifacts now stored in project-local `./.aurora/` directory (except budget tracker)
- Plans created in `./.aurora/plans/` with sequential numbering (0001, 0002, etc.)
- Config loading detects project mode when `./.aurora/` exists
- Database, plans, and metadata now project-scoped for better isolation

**Enhanced `aur mem stats`:**
- Added `Last Indexed` timestamp display (e.g., "2 hours ago")
- Added `Success Rate` percentage when < 100%
- Displays failed files list (up to 10) with error details
- Displays warnings list (up to 10) for parse issues
- Metadata persisted in `.aurora/.indexing_metadata.json`

**Improved `aur doctor` Health Checks:**
- **New TOOL INTEGRATION section:**
  - CLI tools detection (checks for claude, cursor, aider, cline)
  - Slash commands status (configured/not configured)
  - MCP servers status with tool names listed
- **Enhanced CODE ANALYSIS section:**
  - Tree-sitter language parsers detection and listing
  - Shows available languages (python, javascript, typescript, etc.)
- **Removed duplicate/unnecessary checks:**
  - Removed redundant MCP check from CONFIGURATION section
  - Removed API key check (no longer needed)

**MCP Server Configuration:**
- MCP servers now configured automatically during `aur init` Step 3
- Supports Claude, Cursor, Cline, Continue
- Shows "(+ MCP server)" notation in init output

### Fixed

- Fixed CLAUDE.md stub overwriting existing content (now prepends stub)
- Fixed error messages to reference `aur mem stats` instead of `aur doctor` for indexing issues
- Fixed plan numbering to use project-local sequence instead of global
- Fixed init command to show "Check with aur mem stats" for indexing errors

### Changed

- Updated all package versions from 0.1.0 → 0.2.0
- Updated main version from 0.2.0 → 0.3.0
- Doctor output now shows binary status (configured/not) instead of fractions

---

### Added - BM25 Tri-Hybrid Search

**Tri-Hybrid Retrieval Architecture:**
- **BM25 Keyword Matching (30% weight)**: Code-aware tokenization for exact identifier matches
  - Splits camelCase: `getUserData` → `["get", "user", "data", "getuserdata"]`
  - Splits snake_case: `user_manager` → `["user", "manager", "user_manager"]`
  - Preserves acronyms: `HTTPRequest` → `["HTTP", "Request", "httprequest"]`
  - Handles dot notation: `auth.oauth` → `["auth", "oauth"]`
- **Staged Retrieval Pipeline**:
  - Stage 1: BM25 filtering (top-k=100 candidates from activation-ranked chunks)
  - Stage 2: Tri-hybrid re-ranking (30% BM25 + 40% Semantic + 30% Activation)
- **Backward Compatibility**: Dual-hybrid mode (set `bm25_weight=0.0` for original 60/40 activation/semantic)

**Configuration:**
- New `HybridConfig` parameters: `bm25_weight`, `stage1_top_k`, `use_staged_retrieval`
- Config validation ensures weights sum to 1.0
- Supports config loading from `aurora_config.get("context.code.hybrid_weights")`

**Implementation:**
- `BM25Scorer` class with Okapi BM25 algorithm (k1=1.5, b=0.75)
- Index persistence: save/load BM25 indexes
- Result format now includes `bm25_score` field alongside `activation_score` and `semantic_score`
- Backup of v1 hybrid retriever saved as `hybrid_retriever_v1_backup.py`

**CLI Features:**
- `--show-scores` flag: Display detailed score breakdown with intelligent explanations in rich box-drawing format
  - BM25 explanations: exact keyword match, strong term overlap, partial match
  - Semantic explanations: very high/high/moderate/low conceptual relevance
  - Activation explanations: access count, commit count, last used time
  - Box-drawing format with Unicode characters for visual clarity
  - Git metadata display: commit count and last modified time
- `--type` filter: Search specific element types (function, class, method, knowledge, document)
- Type abbreviations: Search results display abbreviated types (func, meth, class, code, reas, know, doc) for improved readability
- Knowledge chunk support: Index and search markdown documentation files

**Knowledge & Reasoning Chunk Support:**
- `KnowledgeParser`: Parse markdown files into searchable chunks (section-based splitting)
- `MarkdownParser`: Registered in global parser registry for automatic .md file handling
- `ReasoningChunk`: Support for SOAR reasoning patterns (created during pipeline execution)
- CodeChunk validation expanded to support "knowledge" and "document" chunk types

**Testing & Quality:**
- **Unit Tests**: 52 tests (15 BM25 + 5 staged + 6 knowledge + 4 reasoning + 4 type abbreviations + 7 box drawing + 6 BM25 explanations + 5 semantic explanations + 5 activation explanations)
- **Shell Tests**: 20 acceptance tests covering exact match, CamelCase, staged retrieval, knowledge indexing, type abbreviations, box-drawing format, score explanations
- **Integration Tests**:
  - `test_e2e_search_quality.py`: MRR validation (target ≥0.85)
  - `test_index_rebuild.py`: Index rebuild and BM25 IDF recalculation
  - `test_performance_benchmarks.py`: Query latency and memory usage benchmarks
- **Type Safety**: MyPy strict mode, all BM25 code type-checked
- **Lint**: Ruff clean (code formatting and import organization)

**Performance:**
- Simple queries: <2s latency (exact identifier matches)
- Complex queries: <10s latency (semantic concept search)
- Memory usage: <100MB for 10K chunks
- Indexing throughput: >2 files/sec, >10 chunks/sec

**Documentation:**
- Updated `docs/cli/CLI_USAGE_GUIDE.md` with --show-scores and --type examples
- Added BM25 architecture section to `docs/KNOWLEDGE_BASE.md`
- Comprehensive docstrings in BM25Scorer and HybridRetriever

---

## [0.2.1] - 2025-12-29

### Fixed - Phase 1: Core Restoration

**Critical Bug Fixes (P0 Priority):**
- **Issue #2 - Database Path Unification**: All commands now use `~/.aurora/memory.db` as single source of truth. No more local `aurora.db` files created. Config-based path resolution ensures consistency across all operations.
- **Issue #4 - Activation Tracking**: Fixed `record_access()` not being called during search. Activation scores now properly update with each chunk access, using ACT-R decay formula. Scores vary across chunks instead of remaining static.
- **Issue #15 - Query Retrieval Integration**: Direct LLM queries now retrieve context from indexed codebase before generating responses. Memory store properly initialized and passed to all query execution modes.
- **Issue #16 - Git-Based BLA Initialization**: Chunks now initialized with activation scores based on Git commit history at FUNCTION level using `git blame -L <start>,<end>`. Frequently-edited functions have higher initial activation than rarely-touched functions in the same file. Gracefully falls back to base_level=0.5 for non-Git directories.

**Critical Bug Fixes (Found During Manual E2E Testing):**
- **Bug #1**: Fixed `retrieve_by_activation` filtering out negative BLA values (sqlite.py:355) - Changed filter to use `-inf` when min_activation==0.0 to include all chunks
- **Bug #2**: Fixed Query command not passing memory_store to Direct LLM (main.py:340) - Memory store now initialized and passed for all query modes
- **Bug #3**: Fixed HybridRetriever not extracting CodeChunk content properly (hybrid_retriever.py:236) - Now extracts full function signature and docstring with proper line ranges
- **Bug #4**: Fixed Config not respecting AURORA_HOME environment variable (config.py:226,359, init.py:151) - Added `_get_aurora_home()` helper function, tests now use isolated config/database

**Feature Improvements (P1 Priority):**
- **Issue #6 - Complexity Assessment**: Added 16 domain-specific keywords (soar, actr, activation, agentic, marketplace, research, analyze, etc.). Multi-question queries (2+ `?`) get +0.3 complexity boost. Domain queries now correctly classified as MEDIUM/COMPLEX.
- **Issue #9 - Auto-Escalation Logic**: Low confidence queries (<0.6) now trigger escalation to SOAR pipeline. In non-interactive mode, auto-escalates automatically. In interactive mode, prompts user with clear choice.
- **Issue #10 - Budget Management**: Implemented `aur budget` command group with 4 subcommands: `show`, `set <amount>`, `reset`, `history`. Budget checked before LLM calls, queries blocked with helpful error if limit exceeded.
- **Issue #11 - Error Handling**: Added user-friendly error messages for authentication, API, network, configuration, and budget errors. Stack traces hidden by default, shown with `--debug` flag. Each error includes actionable solutions.

### Changed

**Database Management:**
- Default database location changed from `./aurora.db` to `~/.aurora/memory.db`
- Migration tool added to `aur init` for existing local databases
- Config file now specifies database path for all operations

**Activation Scores:**
- Initial BLA calculated from Git commit history at function level (not file level)
- Negative BLA values are valid (ACT-R log-odds representation)
- Each function has individual activation based on its edit history
- Access tracking now updates base_level, access_count, and last_access_time

**Query Execution:**
- Direct LLM mode now retrieves context from memory store (not just SOAR mode)
- Context includes file paths, line ranges, and full chunk content
- Queries about indexed code return accurate answers from codebase

**Complexity Assessment:**
- Threshold adjusted to confidence < 0.6 for auto-escalation
- Domain keywords expanded from 8 to 16 terms
- Multi-question detection added (2+ `?` triggers complexity boost)

### Documentation

**Updated Documentation:**
- CHANGELOG.md - Added v0.2.1 release notes with all fixes and improvements
- CLI_USAGE_GUIDE.md - Added budget commands section with examples
- TROUBLESHOOTING.md - Added budget exceeded errors, configuration errors with --debug usage
- PRD-0010 - Complete Phase 1 implementation documented

**New Features Documented:**
- FUNCTION-level Git tracking via `git blame -L <start>,<end>`
- Base-level activation (BLA) initialization from commit history
- Negative BLA values are valid (ACT-R log-odds)
- Budget management workflow with enforcement and history

### Reference

**Related PRD**: [tasks/0010-prd-aurora-phase1-core-restoration.md](tasks/0010-prd-aurora-phase1-core-restoration.md)

**Issues Fixed**: #2, #4, #6, #9, #10, #11, #15, #16 (8 issues total)

**Test Coverage**: 12 E2E/integration tests added, 62 unit tests added, 4 critical bugs fixed during manual testing

**Test Results**: 31 budget tests passing, 10 integration tests passing, all 4 bugs verified fixed. E2E tests have environment setup issues (unrelated to bug fixes).

---

## [Unreleased]

## [0.3.1] - 2026-01-05

### Added

**Retrieval Quality Handling (TD-P2-016):**
- 3-tier retrieval quality system: no match / weak match / good match detection
- Interactive prompts for weak matches in CLI (groundedness < 0.7 OR < 3 high-quality chunks)
- Automatic groundedness scoring to prevent hallucination on weak context
- Activation threshold filtering (≥0.3) to exclude low-relevance chunks
- `--non-interactive` flag for CI/CD and automation workflows
- Production deployment guide for tuning activation and groundedness thresholds
- MCP tools remain non-interactive (unaffected by retrieval quality handling)
- Comprehensive test coverage: 7 integration tests + 18 edge case tests
- Documentation in CLI_USAGE_GUIDE.md, TROUBLESHOOTING.md, and SOAR_ARCHITECTURE.md

**Decision Matrix:**
| Scenario | Chunks | Groundedness | CLI Interactive | CLI Non-Interactive | MCP/Headless |
|----------|--------|--------------|-----------------|---------------------|--------------|
| No match | 0 | N/A | Auto-proceed + note | Auto-proceed | Auto-proceed |
| Weak match | >0 | <0.7 OR <3 high-quality | Prompt user (3 options) | Auto-continue | Auto-continue |
| Good match | >0 | ≥0.7 AND ≥3 high-quality | Auto-proceed | Auto-proceed | Auto-proceed |

### Changed

**Test Suite Systematic Cleanup (Phases 1-5):**
- Removed 20 low-value tests (constructor tests, implementation detail tests)
- Archived 7 performance benchmarks for manual execution
- Converted 79 @patch decorators to Dependency Injection pattern
- Added 26 integration tests for CLI, memory manager, and auto-escalation
- Improved test pyramid from 95/4/1 to 76/21/3 (unit/integration/E2E)
- Increased coverage from 74.95% to 81.06% (+6.11 percentage points)
- Created comprehensive testing documentation (TESTING.md, TEST_REFERENCE.md)
- Marked 86 tests with pytest markers (critical, core, integration, e2e)
- Fixed Python 3.11/3.12 compatibility (from 28+27 failures to 0)

**Testing Documentation:**
- Added `docs/development/TESTING.md` - Testing principles and best practices
- Added `docs/development/TEST_REFERENCE.md` - Test categorization and markers
- Added `docs/development/TESTING_TECHNICAL_DEBT.md` - Technical debt tracking

### Fixed

- Python 3.11/3.12 test failures caused by @patch decorators (79 instances)
- Import organization issues (19 auto-fixes)
- Test fragility across Python versions

---

## [0.2.0] - 2025-01-24

### Added

**MCP Server Integration:**
- Added FastMCP-based server with 5 tools for Claude Desktop integration
- `aurora_search`: Semantic search across indexed codebase with hybrid scoring
- `aurora_index`: Index directory with configurable file patterns
- `aurora_stats`: Database statistics and metrics
- `aurora_context`: Retrieve full file or specific function content
- `aurora_related`: Find related chunks using ACT-R spreading activation
- MCP configuration schema in CLI config with `always_on`, `log_file`, `max_results`
- `aurora-mcp` control script: `start`, `stop`, `status` commands
- Performance logging decorator for all MCP tools with latency tracking
- Cross-platform MCP setup for Windows, macOS, and Linux

**Package Consolidation:**
- Meta-package installation: `pip install aurora` installs all 6 components
- Post-install hook displaying component-level feedback (✓ Core, ✓ CLI, etc.)
- Optional dependencies: `[ml]` for sentence-transformers, `[mcp]` for FastMCP, `[all]` for everything
- Automated import path migration script: `aurora_*` → `aurora.*` namespace
- `aurora-uninstall` helper script with `--keep-config` flag

**CLI Enhancements:**
- `aur --verify` command: Installation health check, dependency verification, diagnostics
- Flexible `--headless` global flag: Both `aur --headless file.md` and `aur headless file.md` work
- Enhanced help text with multiple examples for all commands
- Improved error messages with actionable recovery steps for common failures
- Better Path handling in `aur init` command

**Documentation:**
- Comprehensive MCP Setup Guide (`docs/MCP_SETUP.md`) with 9 sections
- Troubleshooting Guide (`docs/TROUBLESHOOTING.md`) with platform-specific notes
- Updated README for v0.2.0 with MCP integration as primary workflow
- Installation verification documentation

**Testing:**
- Comprehensive MCP test suite (120+ tests) via Python client
- Integration tests for all 5 MCP tools
- MCP server startup/shutdown tests
- Error handling and edge case tests
- Performance and logging tests
- Platform compatibility tests (Linux, with Windows/macOS support)
- Smoke test suite with 11 end-to-end CLI tests

### Fixed

- **Bug #1**: `aur init` crash due to duplicate `from pathlib import Path` import (line 88 shadowing)
- **Bug #2**: `aur mem index` API mismatch - changed `add_chunk()` to `save_chunk()`, fixed embeddings serialization
- **Bug #3**: Dry-run import error - corrected import path to `aurora.context_code.semantic.hybrid_retriever`
- Fixed 39 import statements across packages (aurora.* -> aurora_* for backward compatibility)
- Resolved memory leak in `MemoryStore.close()` for Python 3.12
- Fixed deprecated `datetime.utcnow()` for Python 3.12 compatibility

### Changed

- **BREAKING**: Import paths migrated to `aurora.*` namespace (e.g., `from aurora.core.store import SQLiteStore`)
  - Old `aurora_core.*` imports still work but deprecated
  - Use migration script: `python scripts/migrate_imports.py`
- Version bumped from `0.1.0` to `0.2.0` in `pyproject.toml`
- Project description updated to include MCP integration
- README reorganized: MCP integration as primary workflow, standalone CLI as secondary
- Updated feature list with Windows support and cross-platform compatibility

### Deprecated

- Old import paths (`aurora_core.*`, `aurora_context_code.*`, etc.) - use `aurora.*` namespace instead
- Individual package installation (`pip install -e packages/core`) - use meta-package (`pip install aurora`)

### Migration Guide (Breaking Changes)

**Import Path Migration:**

Old (v0.1.0):
```python
from aurora_core.store import SQLiteStore
from aurora_context_code import PythonParser
from aurora_soar import SOAROrchestrator
```

New (v0.2.0):
```python
from aurora.core.store import SQLiteStore
from aurora.context_code import PythonParser
from aurora.soar import SOAROrchestrator
```

**Automated Migration:**
```bash
python scripts/migrate_imports.py --dry-run  # Preview changes
python scripts/migrate_imports.py           # Apply changes
```

**Installation Migration:**

Old (v0.1.0):
```bash
pip install -e packages/core
pip install -e packages/context-code
pip install -e packages/soar
pip install -e packages/cli
```

New (v0.2.0):
```bash
pip install aurora[all]  # Single command
```

**Backward Compatibility:**
- Old import paths still work in v0.2.0 but will be removed in v0.3.0
- Individual package installation still works but not recommended
- Migrate before v0.3.0 release to avoid breakage

---

## [0.1.0] - 2025-01-15

### Added

**Phase 1 Foundation:**
- Core storage layer with SQLite and in-memory implementations
- Chunk types: `CodeChunk` and `ReasoningChunk` with validation
- Python code parser using tree-sitter
- Context providers with scoring and caching
- Configuration system with JSON schema validation
- Agent registry for capability-based selection
- Comprehensive testing framework (243 tests, 88% coverage)

**Phase 2 SOAR Pipeline:**
- 9-phase SOAR orchestrator: Assess → Retrieve → Decompose → Verify → Route → Collect → Synthesize → Record → Respond
- Multi-provider LLM integration (Anthropic Claude, OpenAI, Ollama)
- Cost tracking with soft/hard budget limits
- Conversation logging with markdown format
- ReasoningChunk pattern caching with ACT-R activation
- 60-70% query optimization via keyword-based assessment

**Phase 3 Advanced Memory:**
- ACT-R activation engine with BLA, spreading activation, context boost
- Semantic embeddings with sentence-transformers
- Hybrid retrieval: 60% activation + 40% semantic similarity
- Multi-tier caching: hot cache + persistent cache + activation cache
- Query optimization: type filtering, threshold filtering, batch calculation
- Performance: <500ms for 10K chunks, 30%+ cache hit rate

**CLI Implementation (v1.1.0):**
- Complete CLI with `aur` command
- Auto-escalation between direct LLM and full AURORA pipeline
- Memory commands: `aur mem index/search/stats`
- Configuration management with environment variable overrides
- Headless reasoning mode for autonomous experiments
- Dry-run mode for testing without API costs

### Performance

- Simple query latency: 0.002s (target: <2s) - 1000x faster
- Complex query latency: <10s (met target)
- Memory usage: 39.48 MB for 10K chunks (target: <100MB)
- Chunk storage: ~15ms (target: <50ms)
- Chunk retrieval: ~8ms (target: <50ms)
- Throughput: >100 queries/second (target: >10)

---

## Release Links

- [v0.2.0 GitHub Release](https://github.com/aurora-project/aurora/releases/tag/v0.2.0) (pending)
- [v0.1.0 GitHub Release](https://github.com/aurora-project/aurora/releases/tag/v0.1.0) (pending)

## Version History

- **v0.2.0** (2025-01-24): MCP integration, package consolidation, CLI enhancements
- **v0.1.0** (2025-01-15): Initial release with SOAR pipeline and advanced memory

---

**Last Updated:** 2025-01-24
