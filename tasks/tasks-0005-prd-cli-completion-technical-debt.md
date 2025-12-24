# Task List: CLI Completion & P1 Technical Debt

**Generated From**: `/home/hamr/PycharmProjects/aurora/tasks/0005-prd-cli-completion-technical-debt.md`
**Target Release**: AURORA v1.1.0
**Total Estimated Effort**: 5-7 days (individual contributor)
**Created**: 2025-12-24

---

## Relevant Files

### Phase 1: Smoke Tests ✓ COMPLETED
- `/packages/examples/smoke_test_memory.py` - Validate memory store Python API (CREATED)
- `/packages/examples/smoke_test_soar.py` - Validate SOAR orchestrator Python API (CREATED)
- `/packages/examples/smoke_test_llm.py` - Validate LLM client Python API (CREATED)
- `/packages/examples/run_smoke_tests.sh` - Master smoke test runner script (CREATED)

### Phase 2: CLI Execution ✓ COMPLETED
- `/packages/cli/src/aurora_cli/main.py` - Main CLI entry point (MODIFIED: removed TODOs, added QueryExecutor integration)
- `/packages/cli/src/aurora_cli/execution.py` - Query executor implementation with direct LLM and AURORA support (CREATED)
- `/packages/cli/tests/test_query_command.py` - Unit tests for QueryExecutor (CREATED: 19 tests, 94.69% coverage)
- `/packages/cli/tests/integration/test_query_e2e.py` - Integration tests for query workflow (CREATED: 12 E2E tests)

### Phase 3: Configuration ✓ COMPLETED
- `/packages/cli/src/aurora_cli/config.py` - Configuration management module (CREATED: 100% coverage)
- `/packages/cli/src/aurora_cli/commands/init.py` - Init command implementation (CREATED: 77.78% coverage)
- `/packages/cli/src/aurora_cli/main.py` - Main CLI entry point (MODIFIED: added init command registration)
- `/packages/cli/tests/test_config.py` - Unit tests for configuration (CREATED: 31 tests)
- `/packages/cli/tests/test_init_command.py` - Unit tests for init command (CREATED: 17 tests)
- `~/.aurora/config.json` - User configuration file (CREATED BY USER)

### Phase 4: Memory ✓ COMPLETED
- `/packages/cli/src/aurora_cli/commands/memory.py` - Memory commands implementation (MODIFIED: added index, search, stats subcommands)
- `/packages/cli/src/aurora_cli/memory_manager.py` - Memory management logic (CREATED)
- `/packages/cli/src/aurora_cli/main.py` - Main CLI entry point (MODIFIED: added auto-index prompt, full AURORA execution)
- `/packages/cli/tests/test_memory_manager.py` - Unit tests for MemoryManager (CREATED: 30+ tests, 85%+ coverage)
- `/packages/cli/tests/integration/test_memory_e2e.py` - Integration tests for memory workflow (CREATED: 20+ E2E tests)

### Phase 5: Error Handling
- `/packages/cli/src/aurora_cli/errors.py` - Error handling utilities (NEW)
- `/packages/cli/src/aurora_cli/execution.py` - Add error handling to executor (MODIFY)
- `/packages/cli/tests/test_error_handling.py` - Unit tests for error scenarios (NEW)

### Phase 6: Technical Debt
- `/packages/core/tests/store/test_migrations.py` - Migration test suite (NEW)
- `/packages/reasoning/tests/test_llm_client_errors.py` - LLM client error tests (NEW)
- `/packages/core/src/aurora_core/store/migrations.py` - Migration logic (REVIEW for coverage)
- `/packages/reasoning/src/aurora_reasoning/llm_client.py` - LLM client (REVIEW for coverage)

### Phase 7: Documentation
- `/docs/cli/CLI_USAGE_GUIDE.md` - Comprehensive CLI usage guide (NEW)
- `/docs/cli/ERROR_CATALOG.md` - Error message catalog with solutions (NEW)
- `/README.md` - Main README update with CLI examples (MODIFY)
- `/packages/cli/tests/integration/README.md` - Integration test documentation (NEW)

---

## Notes

### Testing Framework
- **Unit Tests**: Use `pytest` with mocked dependencies
- **Integration Tests**: Use real API calls with `ANTHROPIC_API_KEY` from environment (budget: $5)
- **Smoke Tests**: Throwaway validation scripts, not part of regular test suite
- **Coverage Targets**:
  - CLI package: 85%+
  - migrations.py: 80%+
  - llm_client.py: 70%+

### Architectural Patterns
- **Configuration Precedence**: CLI flags > Env vars > Config file > Defaults
- **Error Recovery**: Exponential backoff for transient errors (network, rate limit)
- **Memory Initialization**: Lazy loading, prompt user on first query if memory empty
- **Response Formatting**: Use `rich` library for terminal output (already in dependencies)

### Important Considerations
- **Security**: Never log full API keys (redact to `sk-ant-...xyz` format)
- **API Key Sources**: Support both `ANTHROPIC_API_KEY` env var and config file
- **TODO Comments**: All TODO comments in `/packages/cli/src/aurora_cli/main.py` lines 155-166 must be removed
- **Backward Compatibility**: Existing CLI command parsing works, only execution is stub

### Command Priority (Implementation Order)
1. `aur query` - Core functionality (Phase 2)
2. `aur init` - Setup experience (Phase 3)
3. `aur mem index` - Memory indexing (Phase 4)
4. `aur mem search` - Memory search (Phase 4)
5. `aur config` - Configuration management (Phase 3)
6. `aur headless` - Already working, verify only (Phase 7)

### Performance Targets
- Direct LLM query: <2 seconds
- AURORA query (simple): <5 seconds
- AURORA query (complex): <15 seconds
- Index 100 files: <30 seconds
- Index 1,000 files: <5 minutes

---

## Tasks

### Phase 1: Smoke Test Core Components (2 hours) ✓ COMPLETED

- [x] **1.0 Create smoke test suite for core Python API validation**
  - [x] **1.1 Create memory store smoke test script**
    - Create `/packages/examples/smoke_test_memory.py`
    - Import: `from aurora_core.store.memory import MemoryStore`
    - Test: Create store instance with in-memory SQLite
    - Test: Add 10 test code chunks with embeddings
    - Test: Search by keyword (verify results returned)
    - Test: Search by semantic similarity (verify results returned)
    - Test: Retrieve chunk by ID (verify exact match)
    - Test: ACT-R activation updates on chunk access
    - Test: Memory cleanup and close (no errors)
    - Print: "✓ Memory store: PASS" on success
    - Print: "✗ Memory store: FAIL - <error>" on failure
    - Exit code: 0 on pass, 1 on fail
    - **Acceptance**: Script runs without errors, all assertions pass
    - **Estimated Effort**: XS (<1hr)
    - **Files**: `/packages/examples/smoke_test_memory.py`
    - **Testing**: Run script manually: `python packages/examples/smoke_test_memory.py`

  - [x] **1.2 Create SOAR orchestrator smoke test script**
    - Create `/packages/examples/smoke_test_soar.py`
    - Import: `from aurora_soar.orchestrator import SOAROrchestrator`
    - Mock: LLM client (no real API calls)
    - Mock: Memory store (in-memory)
    - Test: Create orchestrator instance with mocked dependencies
    - Test: Simple query decomposition (verify subgoals generated)
    - Test: Subgoal planning (verify plan structure)
    - Test: Agent selection (verify correct agents chosen)
    - Mock: Agent execution (return fake responses)
    - Test: Response synthesis (verify final response)
    - Print: "✓ SOAR orchestrator: PASS" on success
    - Print: "✗ SOAR orchestrator: FAIL - <error>" on failure
    - Exit code: 0 on pass, 1 on fail
    - **Acceptance**: Script runs without errors, all SOAR phases execute
    - **Estimated Effort**: XS (<1hr)
    - **Files**: `/packages/examples/smoke_test_soar.py`
    - **Testing**: Run script manually: `python packages/examples/smoke_test_soar.py`

  - [x] **1.3 Create LLM client smoke test script**
    - Create `/packages/examples/smoke_test_llm.py`
    - Import: `from aurora_reasoning.llm_client import LLMClient`
    - Check: `ANTHROPIC_API_KEY` environment variable exists (skip if not set)
    - Test: Client initialization with API key from environment
    - Test: Simple prompt execution: "Say 'test passed' exactly"
    - Verify: Response contains expected text
    - Test: Rate limiting initialization (verify no errors)
    - Test: Retry logic with mocked transient failure
    - Print: "✓ LLM client: PASS" on success
    - Print: "⊗ LLM client: SKIP - No ANTHROPIC_API_KEY" if key missing
    - Print: "✗ LLM client: FAIL - <error>" on failure
    - Exit code: 0 on pass/skip, 1 on fail
    - **Acceptance**: Script succeeds with valid API key, skips gracefully without
    - **Estimated Effort**: S (1hr)
    - **Files**: `/packages/examples/smoke_test_llm.py`
    - **Testing**: Run script: `ANTHROPIC_API_KEY=sk-... python packages/examples/smoke_test_llm.py`

  - [x] **1.4 Create master smoke test runner script**
    - Create `/packages/examples/run_smoke_tests.sh`
    - Make executable: `chmod +x`
    - Run each smoke test sequentially
    - Capture exit codes for each test
    - Display summary table:
      ```
      ===== SMOKE TEST RESULTS =====
      Memory Store:      ✓ PASS
      SOAR Orchestrator: ✓ PASS
      LLM Client:        ⊗ SKIP (no API key)
      ===========================
      2/3 tests passed, 1 skipped
      ```
    - Exit with code 0 if all non-skipped tests pass
    - Exit with code 1 if any test fails
    - **Acceptance**: Runner script executes all smoke tests and reports results
    - **Estimated Effort**: XS (<1hr)
    - **Files**: `/packages/examples/run_smoke_tests.sh`
    - **Testing**: Run: `./packages/examples/run_smoke_tests.sh`

---

### Phase 2: CLI Execution Engine (1-2 days) ✓ COMPLETED

- [x] **2.0 Implement query execution module with SOAR and direct LLM integration**
  - [x] **2.1 Create QueryExecutor class for execution abstraction**
    - Create `/packages/cli/src/aurora_cli/execution.py`
    - Define `QueryExecutor` class with methods:
      - `execute_direct_llm(query: str, api_key: str, verbose: bool) -> str`
      - `execute_aurora(query: str, api_key: str, memory_store, verbose: bool) -> str`
    - Implement initialization: Accept configuration in constructor
    - Add internal helper: `_initialize_llm_client(api_key: str) -> LLMClient`
    - Add internal helper: `_initialize_orchestrator(llm, memory, config) -> SOAROrchestrator`
    - Add error handling wrapper for API errors
    - Add logging for execution flow
    - **Acceptance**: Module created with class structure and method signatures
    - **Estimated Effort**: S (1-2hrs)
    - **Files**: `/packages/cli/src/aurora_cli/execution.py`
    - **Testing**: Create unit test file (next task)

  - [x] **2.2 Implement direct LLM execution method**
    - In `/packages/cli/src/aurora_cli/execution.py`
    - Implement `execute_direct_llm()` method:
      - Import: `from aurora_reasoning.llm_client import LLMClient`
      - Initialize LLM client with provided API key
      - Optional: Add memory context if memory_store provided and not empty
        - Search memory for relevant chunks (top 3)
        - Prepend context to prompt: "Context:\n<chunks>\n\nQuery: <query>"
      - Call: `llm.generate(prompt=query, max_tokens=500, temperature=0.7)`
      - Handle errors: Wrap in try/except, raise meaningful exceptions
      - If verbose: Log API call details (model, tokens, cost estimate)
      - Return: Response content as string
    - **Acceptance**: Method successfully calls LLM and returns response
    - **Estimated Effort**: S (1-2hrs)
    - **Files**: `/packages/cli/src/aurora_cli/execution.py`
    - **Testing**: Unit test with mocked LLMClient

  - [x] **2.3 Implement AURORA orchestrator execution method**
    - In `/packages/cli/src/aurora_cli/execution.py`
    - Implement `execute_aurora()` method:
      - Import: `from aurora_soar.orchestrator import SOAROrchestrator`
      - Initialize LLM client (reuse helper)
      - Initialize orchestrator with LLM, memory_store, and config
      - Call: `orchestrator.execute(query)`
      - Extract: `response.final_response`
      - If verbose: Extract and return phase trace
        - Collect: Phase names, execution times, actions taken
        - Format: "Phase 1: Assess (0.2s) - Keyword patterns detected"
      - Handle errors: SOAR execution failures
      - Return: Final response string
      - Return (if verbose): Tuple of (response, phase_trace)
    - **Acceptance**: Method successfully executes SOAR pipeline and returns response
    - **Estimated Effort**: M (2-3hrs)
    - **Files**: `/packages/cli/src/aurora_cli/execution.py`
    - **Testing**: Unit test with mocked SOAROrchestrator

  - [x] **2.4 Integrate QueryExecutor into CLI query command**
    - In `/packages/cli/src/aurora_cli/main.py`
    - Remove TODO comments from lines 151-166
    - Import: `from aurora_cli.execution import QueryExecutor`
    - Import: `from aurora_cli.config import load_config` (will implement in Phase 3)
    - Before escalation: Load configuration to get API key
      - Call: `config = load_config()`
      - Extract: `api_key = config.get_api_key()`
      - Handle: Missing API key (raise helpful error)
    - After escalation decision:
      - Create: `executor = QueryExecutor(config=config)`
      - If `result.use_aurora`:
        - Call: `response = executor.execute_aurora(query_text, api_key, memory_store, verbose)`
      - Else:
        - Call: `response = executor.execute_direct_llm(query_text, api_key, verbose)`
    - Replace stub messages with actual responses
    - If verbose and AURORA: Display phase trace
    - Print response using rich formatting
    - **Acceptance**: CLI query command executes real LLM calls and returns responses
    - **Estimated Effort**: S (1-2hrs)
    - **Dependencies**: Task 2.1, 2.2, 2.3 complete; Config system (stub acceptable for now)
    - **Files**: `/packages/cli/src/aurora_cli/main.py`
    - **Testing**: Manual test: `aur query "test" --force-direct`

  - [x] **2.5 Implement verbose mode with phase trace formatting**
    - In `/packages/cli/src/aurora_cli/execution.py`
    - Enhance `execute_aurora()` to capture phase details:
      - Hook into orchestrator phase callbacks (if available)
      - Collect: Phase name, start time, end time, actions
      - Calculate: Duration for each phase
      - Estimate: Cost for LLM phases (based on tokens)
    - Add method: `format_phase_trace(trace_data: list) -> str`
      - Format each phase as: "Phase N: <name> (<duration>s) - <summary>"
      - Include total execution time
      - Include total cost estimate
    - In `/packages/cli/src/aurora_cli/main.py`:
      - When `--verbose` flag set and AURORA used:
        - Call: `response, trace = executor.execute_aurora(..., verbose=True)`
        - Display trace before response
      - Use rich table or panel for formatted output
    - **Acceptance**: Verbose mode displays detailed SOAR execution trace
    - **Estimated Effort**: M (2-3hrs)
    - **Dependencies**: Task 2.3 complete
    - **Files**: `/packages/cli/src/aurora_cli/execution.py`, `/packages/cli/src/aurora_cli/main.py`
    - **Testing**: Manual test: `aur query "complex query" --force-aurora --verbose`

  - [x] **2.6 Create unit tests for query execution**
    - Create `/packages/cli/tests/test_query_command.py`
    - Test `QueryExecutor.execute_direct_llm()`:
      - Mock `LLMClient.generate()` to return test response
      - Verify: Correct prompt passed to LLM
      - Verify: Response returned correctly
      - Test: With and without memory context
    - Test `QueryExecutor.execute_aurora()`:
      - Mock `SOAROrchestrator.execute()` to return test response
      - Verify: Orchestrator called with correct query
      - Verify: Response extracted correctly
      - Test: Verbose mode returns trace data
    - Test error scenarios:
      - LLM API error (mock exception)
      - Orchestrator execution failure
      - Missing API key
    - **Acceptance**: All tests pass, 90%+ coverage on execution.py
    - **Estimated Effort**: M (2-3hrs)
    - **Dependencies**: Task 2.1, 2.2, 2.3 complete
    - **Files**: `/packages/cli/tests/test_query_command.py`
    - **Testing**: Run: `pytest packages/cli/tests/test_query_command.py -v`

  - [x] **2.7 Create integration test for end-to-end query workflow**
    - Create `/packages/cli/tests/integration/` directory
    - Create `/packages/cli/tests/integration/test_query_e2e.py`
    - Test direct LLM query:
      - Require: `ANTHROPIC_API_KEY` in environment (skip if not set)
      - Run: `aur query "What is Python?" --force-direct`
      - Verify: Response contains relevant text
      - Verify: Exit code 0
      - Verify: No error messages
    - Test AURORA query with real API:
      - Setup: Create temp memory store with test chunks
      - Run: `aur query "Explain the test code" --force-aurora`
      - Verify: Response uses memory context
      - Verify: Exit code 0
    - Test escalation decision:
      - Run: Simple query without force flags
      - Verify: Auto-selects direct LLM
      - Run: Complex query without force flags
      - Verify: Auto-selects AURORA
    - Test verbose mode:
      - Run: `aur query "test" --force-aurora --verbose`
      - Verify: Phase trace displayed
    - **Acceptance**: Integration tests pass with real API calls
    - **Estimated Effort**: M (3-4hrs)
    - **Dependencies**: Task 2.4 complete, Phase 4 memory implementation
    - **Files**: `/packages/cli/tests/integration/test_query_e2e.py`
    - **Testing**: Run: `ANTHROPIC_API_KEY=sk-... pytest packages/cli/tests/integration/test_query_e2e.py -v`

---

### Phase 3: Configuration Management (4-6 hours)

- [ ] **3.0 Implement configuration system with file and environment variable support**
  - [ ] **3.1 Define configuration data structure and schema**
    - Create `/packages/cli/src/aurora_cli/config.py`
    - Define `Config` dataclass with fields:
      - `version: str`
      - `llm_provider: str`
      - `anthropic_api_key: str | None`
      - `llm_model: str`
      - `llm_temperature: float`
      - `llm_max_tokens: int`
      - `escalation_threshold: float`
      - `escalation_enable_keyword_only: bool`
      - `escalation_force_mode: str | None`
      - `memory_auto_index: bool`
      - `memory_index_paths: list[str]`
      - `memory_chunk_size: int`
      - `memory_overlap: int`
      - `logging_level: str`
      - `logging_file: str`
    - Define `CONFIG_SCHEMA` dict with default values
    - Add method: `Config.get_api_key() -> str`
      - Check env var `ANTHROPIC_API_KEY` first
      - Fall back to `self.anthropic_api_key`
      - Raise `ConfigurationError` if neither exists
    - Add method: `Config.validate() -> None`
      - Validate threshold: 0.0-1.0
      - Validate provider: "anthropic" only for now
      - Validate paths exist (warn if not)
      - Validate numeric ranges
    - **Acceptance**: Config class defined with validation methods
    - **Estimated Effort**: S (1hr)
    - **Files**: `/packages/cli/src/aurora_cli/config.py`
    - **Testing**: Create unit test file (next task)

  - [ ] **3.2 Implement configuration file loading with precedence**
    - In `/packages/cli/src/aurora_cli/config.py`
    - Add function: `load_config(path: str | None = None) -> Config`
    - Search order (if path not provided):
      1. Current directory: `./aurora.config.json`
      2. Home directory: `~/.aurora/config.json`
      3. Use built-in defaults
    - Parse JSON file with error handling:
      - Catch: `json.JSONDecodeError` (invalid JSON)
      - Raise: `ConfigurationError` with line number
    - Merge: File values with defaults (defaults for missing keys)
    - Override: Environment variables take precedence
      - Map: `ANTHROPIC_API_KEY` → `anthropic_api_key`
      - Map: `AURORA_ESCALATION_THRESHOLD` → `escalation_threshold`
      - Map: `AURORA_LOGGING_LEVEL` → `logging_level`
    - Validate: Call `config.validate()`
    - Log: Which config source was used (file path or defaults)
    - Return: Populated `Config` instance
    - **Acceptance**: Function loads config from file and merges with env vars
    - **Estimated Effort**: M (2-3hrs)
    - **Dependencies**: Task 3.1 complete
    - **Files**: `/packages/cli/src/aurora_cli/config.py`
    - **Testing**: Unit test with temp config files

  - [ ] **3.3 Implement init command for configuration setup**
    - Create `/packages/cli/src/aurora_cli/commands/init.py`
    - Define `init_command()` function with `@click.command()` decorator
    - Check: Config file already exists at `~/.aurora/config.json`
      - If exists: Prompt "Config exists. Overwrite? [y/N]"
      - If "N": Exit with message "Keeping existing config"
    - Prompt: "Enter Anthropic API key (or press Enter to skip):"
      - Use: `click.prompt()` with `default=""`
      - If provided: Validate format (starts with "sk-ant-")
    - Create: `~/.aurora/` directory if not exists
    - Write: Config file with defaults and provided API key
    - Set: File permissions to 0600 (user read/write only)
    - Check: If permissions set failed, warn user
    - Prompt: "Index current directory? [Y/n]"
      - If "Y": Import and call `memory.index_command(path=".")`
      - Show progress during indexing
      - Display summary: "✓ Indexed N files, M chunks"
    - Display final summary:
      - "✓ Configuration created at ~/.aurora/config.json"
      - "✓ Indexed current directory" (if indexed)
      - "Next: Run 'aur query \"your question\"' to start"
    - **Acceptance**: Init command creates config file and optionally indexes codebase
    - **Estimated Effort**: M (2-3hrs)
    - **Dependencies**: Task 3.1, 3.2 complete; Phase 4 memory (can stub indexing for now)
    - **Files**: `/packages/cli/src/aurora_cli/commands/init.py`
    - **Testing**: Manual test: `aur init`

  - [ ] **3.4 Register init command in CLI**
    - In `/packages/cli/src/aurora_cli/main.py`
    - Import: `from aurora_cli.commands.init import init_command`
    - Register: `cli.add_command(init_command)` (after line 63)
    - Update docstring: Add init command to examples
    - **Acceptance**: `aur init` command available in CLI
    - **Estimated Effort**: XS (<1hr)
    - **Dependencies**: Task 3.3 complete
    - **Files**: `/packages/cli/src/aurora_cli/main.py`
    - **Testing**: Run: `aur --help` (verify init listed)

  - [ ] **3.5 Create unit tests for configuration system**
    - Create `/packages/cli/tests/test_config.py`
    - Test `load_config()` with file only:
      - Create temp config file
      - Load config
      - Verify: Values match file
    - Test `load_config()` with env vars:
      - Mock: Environment variables
      - Create config file
      - Load config
      - Verify: Env vars override file values
    - Test `load_config()` with defaults:
      - No config file, no env vars
      - Load config
      - Verify: Default values used
    - Test `Config.validate()`:
      - Test: Invalid threshold (>1.0)
      - Test: Invalid provider
      - Verify: Raises `ConfigurationError`
    - Test `Config.get_api_key()`:
      - Test: From env var
      - Test: From config file
      - Test: Missing (verify raises error)
    - Test precedence: CLI flags > Env > File > Defaults
    - **Acceptance**: All tests pass, 90%+ coverage on config.py
    - **Estimated Effort**: M (2-3hrs)
    - **Dependencies**: Task 3.1, 3.2 complete
    - **Files**: `/packages/cli/tests/test_config.py`
    - **Testing**: Run: `pytest packages/cli/tests/test_config.py -v`

  - [ ] **3.6 Create unit tests for init command**
    - Create `/packages/cli/tests/test_init_command.py`
    - Test init with API key provided:
      - Mock: User input with API key
      - Run: init_command()
      - Verify: Config file created
      - Verify: API key written to file
      - Verify: File permissions 0600
    - Test init skipping API key:
      - Mock: User input (empty string)
      - Run: init_command()
      - Verify: Config file created without API key
    - Test init with indexing:
      - Mock: User input "Y" for indexing
      - Mock: memory.index_command()
      - Run: init_command()
      - Verify: Indexing called
    - Test init skipping indexing:
      - Mock: User input "n"
      - Run: init_command()
      - Verify: Indexing not called
    - Test init with existing config:
      - Create: Existing config file
      - Mock: User input "N" (don't overwrite)
      - Run: init_command()
      - Verify: Existing config unchanged
    - **Acceptance**: All tests pass, 85%+ coverage on init.py
    - **Estimated Effort**: M (2-3hrs)
    - **Dependencies**: Task 3.3 complete
    - **Files**: `/packages/cli/tests/test_init_command.py`
    - **Testing**: Run: `pytest packages/cli/tests/test_init_command.py -v`

---

### Phase 4: Memory Store Initialization (2-4 hours) ✓ COMPLETED

- [x] **4.0 Implement memory management commands for indexing and search**
  - [x] **4.1 Create MemoryManager class for memory operations**
    - Create `/packages/cli/src/aurora_cli/memory_manager.py`
    - Define `MemoryManager` class:
      - Constructor: Accept memory_store instance
      - Method: `index_path(path: str, progress_callback: Callable | None = None) -> IndexStats`
      - Method: `search(query: str, limit: int = 5) -> list[SearchResult]`
      - Method: `get_stats() -> MemoryStats`
    - Define `IndexStats` dataclass:
      - `files_indexed: int`
      - `chunks_created: int`
      - `duration_seconds: float`
    - Define `SearchResult` dataclass:
      - `file_path: str`
      - `line_range: tuple[int, int]`
      - `content: str`
      - `activation_score: float`
    - Define `MemoryStats` dataclass:
      - `total_chunks: int`
      - `total_files: int`
      - `languages: dict[str, int]`
      - `database_size_mb: float`
    - **Acceptance**: MemoryManager class defined with method signatures
    - **Estimated Effort**: S (1hr)
    - **Files**: `/packages/cli/src/aurora_cli/memory_manager.py`
    - **Testing**: Create unit test file (next task)

  - [x] **4.2 Implement index_path method with progress reporting**
    - In `/packages/cli/src/aurora_cli/memory_manager.py`
    - Implement `index_path()`:
      - Import: Code parser from aurora_core (language-specific parsers)
      - Discover: All code files in path (recursively)
      - Skip: Common directories (`.git/`, `node_modules/`, `venv/`, `__pycache__/`)
      - For each file:
        - Parse: Extract code chunks using appropriate parser
        - Generate: Semantic embeddings for each chunk
        - Store: In memory store with metadata (file path, line range)
        - Call: `progress_callback(files_processed, total_files)` if provided
      - Handle errors: Parse failures (log warning, continue)
      - Track: Statistics (files indexed, chunks created, duration)
      - Return: `IndexStats` object
    - Add internal helper: `_should_skip_path(path: str) -> bool`
      - Check against skip list
    - Add internal helper: `_detect_language(file_path: str) -> str`
      - Based on file extension
    - **Acceptance**: Method successfully indexes codebase and reports progress
    - **Estimated Effort**: M (3-4hrs)
    - **Dependencies**: Task 4.1 complete
    - **Files**: `/packages/cli/src/aurora_cli/memory_manager.py`
    - **Testing**: Unit test with temp directory of test files

  - [x] **4.3 Implement search method with rich result formatting**
    - In `/packages/cli/src/aurora_cli/memory_manager.py`
    - Implement `search()`:
      - Call: `memory_store.search(query, limit=limit)`
      - Hybrid: Combine keyword (BM25) and semantic search
        - Weight: 30% keyword, 70% semantic (configurable)
      - Extract: Results with activation scores
      - Format: Each result as `SearchResult` dataclass
      - Sort: By relevance (combined score + activation)
      - Apply: ACT-R activation boost to frequently accessed chunks
      - Return: List of `SearchResult` objects
    - **Acceptance**: Method returns relevant search results sorted by score
    - **Estimated Effort**: S (1-2hrs)
    - **Dependencies**: Task 4.1 complete
    - **Files**: `/packages/cli/src/aurora_cli/memory_manager.py`
    - **Testing**: Unit test with mocked memory store

  - [x] **4.4 Enhance memory commands with MemoryManager integration**
    - In `/packages/cli/src/aurora_cli/commands/memory.py` (existing file)
    - Import: `from aurora_cli.memory_manager import MemoryManager`
    - Enhance `index` subcommand:
      - Accept: Path argument (default: ".")
      - Create: MemoryManager instance with memory_store
      - Display: Spinner "⠋ Indexing files..."
      - Create progress callback using rich progress bar
      - Call: `manager.index_path(path, progress_callback)`
      - Display: Summary "✓ Indexed {files} files, {chunks} chunks in {duration}s"
      - Handle errors: Display helpful messages
    - Enhance `search` subcommand:
      - Accept: Query string argument
      - Accept: `--limit` option (default: 5)
      - Accept: `--format` option (choices: ["rich", "json"], default: "rich")
      - Create: MemoryManager instance
      - Call: `manager.search(query, limit)`
      - If format=="rich":
        - Display: Each result in panel with:
          - File path (clickable if supported)
          - Line range
          - Activation score as colored bar
          - Code preview with syntax highlighting
      - If format=="json":
        - Output: JSON array of results
      - Handle: No results (display "No results found")
    - Add `stats` subcommand (optional):
      - Call: `manager.get_stats()`
      - Display: Statistics table (total chunks, files, languages, DB size)
    - **Acceptance**: Memory commands use MemoryManager and display rich output
    - **Estimated Effort**: M (2-3hrs)
    - **Dependencies**: Task 4.1, 4.2, 4.3 complete
    - **Files**: `/packages/cli/src/aurora_cli/commands/memory.py`
    - **Testing**: Manual test: `aur mem index .` and `aur mem search "test"`

  - [x] **4.5 Implement auto-index prompt for first-time queries**
    - In `/packages/cli/src/aurora_cli/execution.py`
    - Add method: `QueryExecutor._check_memory_empty() -> bool`
      - Query: Memory store for chunk count
      - Return: True if count == 0
    - In `/packages/cli/src/aurora_cli/main.py`, in `query_command()`:
      - Before execution:
        - Initialize: Memory store
        - Check: If memory empty using `_check_memory_empty()`
        - If empty and `memory_auto_index` config is True:
          - Prompt: "Memory empty. Index current directory? [Y/n]"
          - If "Y":
            - Import: `from aurora_cli.commands.memory import index_command`
            - Call: Index current directory
            - Display: Progress and summary
          - If "n":
            - Continue without memory context
            - Save preference: Update config `memory_auto_index = false`
        - Remember: Don't prompt again if user already said "n"
    - **Acceptance**: First query prompts user to index if memory empty
    - **Estimated Effort**: S (1-2hrs)
    - **Dependencies**: Task 4.4 complete, Task 3.2 (config system)
    - **Files**: `/packages/cli/src/aurora_cli/execution.py`, `/packages/cli/src/aurora_cli/main.py`
    - **Testing**: Manual test: Fresh install, run `aur query "test"` (should prompt)

  - [x] **4.6 Create unit tests for memory management**
    - Create `/packages/cli/tests/test_memory_commands.py`
    - Test `MemoryManager.index_path()`:
      - Create: Temp directory with test files (.py, .js)
      - Call: `index_path(temp_dir)`
      - Verify: Files discovered and indexed
      - Verify: Chunks created in memory store
      - Verify: Progress callback called
      - Verify: Statistics accurate
    - Test `MemoryManager.search()`:
      - Setup: Memory store with test chunks
      - Call: `search("test query", limit=3)`
      - Verify: Results returned
      - Verify: Limit respected
      - Verify: Results sorted by relevance
    - Test memory command integration:
      - Mock: MemoryManager
      - Run: `aur mem index .` (CLI invoke)
      - Verify: Manager called correctly
      - Run: `aur mem search "test"` (CLI invoke)
      - Verify: Results formatted
    - Test auto-index prompt:
      - Mock: Empty memory store
      - Mock: User input "Y"
      - Run: `aur query "test"`
      - Verify: Indexing triggered
    - **Acceptance**: All tests pass, 85%+ coverage on memory_manager.py
    - **Estimated Effort**: M (3-4hrs)
    - **Dependencies**: Task 4.1, 4.2, 4.3, 4.4 complete
    - **Files**: `/packages/cli/tests/test_memory_commands.py`
    - **Testing**: Run: `pytest packages/cli/tests/test_memory_commands.py -v`

  - [x] **4.7 Create integration test for memory workflow**
    - Create `/packages/cli/tests/integration/test_memory_e2e.py`
    - Test full indexing workflow:
      - Create: Temp codebase with test files
      - Run: `aur mem index <temp_dir>`
      - Verify: Success message displayed
      - Verify: Database file created
      - Query: Database for chunks
      - Verify: Chunks exist for indexed files
    - Test search workflow:
      - Setup: Indexed test codebase
      - Run: `aur mem search "function"`
      - Verify: Results displayed
      - Verify: Results contain relevant code
    - Test search with different formats:
      - Run: `aur mem search "test" --format json`
      - Verify: JSON output valid
      - Parse: JSON and verify structure
    - Test auto-index integration:
      - Setup: Fresh CLI with empty memory
      - Mock: User input "Y"
      - Run: `aur query "test"`
      - Verify: Indexing triggered before query
    - **Acceptance**: Integration tests pass with real memory operations
    - **Estimated Effort**: M (2-3hrs)
    - **Dependencies**: Task 4.4 complete
    - **Files**: `/packages/cli/tests/integration/test_memory_e2e.py`
    - **Testing**: Run: `pytest packages/cli/tests/integration/test_memory_e2e.py -v`

---

### Phase 5: Error Handling (4-6 hours)

- [ ] **5.0 Implement comprehensive error handling with actionable messages**
  - [ ] **5.1 Create error handling utilities module**
    - Create `/packages/cli/src/aurora_cli/errors.py`
    - Define custom exceptions:
      - `ConfigurationError(Exception)` - Configuration issues
      - `APIError(Exception)` - LLM API failures
      - `MemoryStoreError(Exception)` - Memory store issues
    - Define `ErrorHandler` class:
      - Method: `format_error(error: Exception) -> str`
        - Returns formatted error message with context and solution
      - Method: `handle_api_error(error: Exception) -> str`
        - Parse API error (auth, rate limit, network)
        - Return actionable message
      - Method: `handle_config_error(error: Exception) -> str`
        - Parse config error (missing key, invalid value)
        - Return setup instructions
      - Method: `handle_memory_error(error: Exception) -> str`
        - Parse memory error (locked, corrupted, disk full)
        - Return recovery steps
    - Define error message templates:
      - Template: "**[Context]** What happened. Why it matters. **How to fix.**"
    - **Acceptance**: Error handling utilities module created
    - **Estimated Effort**: S (1-2hrs)
    - **Files**: `/packages/cli/src/aurora_cli/errors.py`
    - **Testing**: Create unit test file (next task)

  - [ ] **5.2 Implement LLM API error handling with retry logic**
    - In `/packages/cli/src/aurora_cli/execution.py`
    - Import: `from aurora_cli.errors import ErrorHandler, APIError`
    - Wrap LLM calls with try/except:
      - Catch: Authentication errors (HTTP 401)
        - Message: "[API] Authentication failed. Check ANTHROPIC_API_KEY environment variable or ~/.aurora/config.json"
        - Suggest: "Get your API key at: https://console.anthropic.com"
        - Exit code: 1
      - Catch: Rate limit errors (HTTP 429)
        - Extract: Retry-after header
        - Message: "[API] Rate limit exceeded. Retry in {seconds}s or upgrade API tier."
        - Implement: Exponential backoff retry (3 attempts)
          - Delays: 100ms, 200ms, 400ms
          - Add: Random jitter to avoid thundering herd
        - Display: "Retrying in 0.4s... (attempt 2/3)"
      - Catch: Network errors (ConnectionError, Timeout)
        - Message: "[Network] Cannot reach Anthropic API. Check internet connection."
        - Suggest: "Try: ping api.anthropic.com"
        - Exit code: 1
      - Catch: Model not found (HTTP 404)
        - Message: "[API] Model '{model}' not found. Available models: claude-3-5-sonnet-20241022, ..."
        - Exit code: 1
      - Catch: Server errors (HTTP 5xx)
        - Implement: Retry with backoff (transient failures)
        - Message: "[API] Server error. Retrying..."
        - After 3 attempts: "[API] Server unavailable. Try again later."
    - Log: All API errors for debugging
    - **Acceptance**: API errors handled with retry logic and clear messages
    - **Estimated Effort**: M (2-3hrs)
    - **Dependencies**: Task 5.1 complete, Task 2.2 (LLM execution)
    - **Files**: `/packages/cli/src/aurora_cli/execution.py`
    - **Testing**: Unit test with mocked API errors

  - [ ] **5.3 Implement configuration error handling**
    - In `/packages/cli/src/aurora_cli/config.py`
    - Import: `from aurora_cli.errors import ConfigurationError`
    - In `load_config()`:
      - Catch: `FileNotFoundError` (no config file)
        - Use: Built-in defaults (not an error)
        - Log: "No config file found, using defaults"
      - Catch: `json.JSONDecodeError` (invalid JSON)
        - Message: "[Config] Config file syntax error: Unexpected token at line {line}"
        - Suggest: "Validate JSON: jsonlint ~/.aurora/config.json"
        - Exit code: 1
      - Catch: `PermissionError` (can't read config)
        - Message: "[Config] Cannot read ~/.aurora/config.json. Check file permissions."
        - Suggest: "Fix permissions: chmod 600 ~/.aurora/config.json"
        - Exit code: 1
    - In `Config.validate()`:
      - Invalid threshold:
        - Raise: `ConfigurationError("escalation.threshold must be 0.0-1.0, got {value}")`
      - Invalid provider:
        - Raise: `ConfigurationError("llm.provider must be 'anthropic', got '{value}'")`
      - Invalid paths:
        - Warn: "Path '{path}' does not exist" (don't fail, just warn)
    - In `Config.get_api_key()`:
      - Missing API key:
        - Raise: `ConfigurationError` with multi-line message:
          ```
          [Config] ANTHROPIC_API_KEY not found. AURORA needs this to connect to LLM.

          Configure via:
            1. Environment: export ANTHROPIC_API_KEY=sk-ant-...
            2. Config file: aur init

          Get your API key at: https://console.anthropic.com
          ```
    - **Acceptance**: Config errors have clear messages with setup instructions
    - **Estimated Effort**: S (1-2hrs)
    - **Dependencies**: Task 5.1 complete, Task 3.2 (config loading)
    - **Files**: `/packages/cli/src/aurora_cli/config.py`
    - **Testing**: Unit test with invalid configs

  - [ ] **5.4 Implement memory store error handling**
    - In `/packages/cli/src/aurora_cli/memory_manager.py`
    - Import: `from aurora_cli.errors import MemoryStoreError`
    - In `index_path()`:
      - Catch: Parse errors for individual files
        - Log: Warning "Failed to parse {file}: {error}"
        - Continue: Processing other files (don't fail entire indexing)
      - Catch: `sqlite3.OperationalError` (database locked)
        - Message: "[Memory] Memory store is locked. Close other AURORA processes."
        - Implement: Retry logic (5 attempts, 100ms delay)
        - After retries: Exit with error
      - Catch: `PermissionError` (can't write database)
        - Message: "[Memory] Cannot write to ~/.aurora/memory.db. Check file permissions."
        - Suggest: "Fix permissions: chmod 700 ~/.aurora"
        - Exit code: 1
      - Catch: `OSError` (disk full)
        - Message: "[Memory] Disk full. Free space needed: ~50MB"
        - Exit code: 1
      - Catch: `sqlite3.DatabaseError` (corrupted database)
        - Message: "[Memory] Memory store is corrupted. Backup and recreate: aur mem reset"
        - Suggest: "Backup: cp ~/.aurora/memory.db ~/.aurora/memory.db.backup"
        - Exit code: 1
    - **Acceptance**: Memory errors handled gracefully with recovery steps
    - **Estimated Effort**: S (1-2hrs)
    - **Dependencies**: Task 5.1 complete, Task 4.2 (indexing)
    - **Files**: `/packages/cli/src/aurora_cli/memory_manager.py`
    - **Testing**: Unit test with mocked errors

  - [ ] **5.5 Implement dry-run mode for testing configuration**
    - In `/packages/cli/src/aurora_cli/main.py`, in `query_command()`:
      - Add: `--dry-run` flag option
      - If `--dry-run`:
        - Display: "[bold yellow]DRY RUN MODE[/] - No API calls will be made"
        - Load: Configuration
        - Display: Configuration summary:
          - Provider: anthropic
          - Model: claude-3-5-sonnet-20241022
          - API Key: sk-ant-...xyz (redacted last 3 chars)
          - Memory chunks: {count}
        - Run: Escalation assessment (no API call)
        - Display: Escalation decision:
          - Complexity: {score}
          - Decision: "Would use: Direct LLM" or "Would use: AURORA"
          - Reasoning: {reasoning}
        - Estimate: API cost for this query (~$0.002)
        - Display: "Exiting without API calls"
        - Exit: Code 0
    - Add helper: `redact_api_key(key: str) -> str`
      - Show first 7 chars and last 3 chars
      - Replace middle with "..."
      - Example: "sk-ant-...xyz"
    - **Acceptance**: Dry-run mode shows what would execute without API calls
    - **Estimated Effort**: S (1-2hrs)
    - **Dependencies**: Task 3.2 (config), Task 2.4 (query execution)
    - **Files**: `/packages/cli/src/aurora_cli/main.py`
    - **Testing**: Manual test: `aur query "test" --dry-run`

  - [ ] **5.6 Create unit tests for error handling**
    - Create `/packages/cli/tests/test_error_handling.py`
    - Test API error handling:
      - Mock: HTTP 401 (auth error)
      - Run: Query command
      - Verify: Error message contains "ANTHROPIC_API_KEY"
      - Verify: Exit code 1
    - Test rate limit retry:
      - Mock: HTTP 429 on first 2 calls, success on 3rd
      - Run: Query command
      - Verify: Retries automatically
      - Verify: Success after retries
    - Test config error handling:
      - Create: Invalid JSON config file
      - Run: Query command
      - Verify: Error message contains "syntax error"
      - Verify: Suggests jsonlint
    - Test memory error handling:
      - Mock: Database locked error
      - Run: Index command
      - Verify: Error message contains "locked"
      - Verify: Suggests closing other processes
    - Test dry-run mode:
      - Run: `aur query "test" --dry-run`
      - Verify: No API calls made
      - Verify: Configuration displayed
      - Verify: Escalation decision shown
      - Verify: API key redacted
    - **Acceptance**: All tests pass, 85%+ coverage on error handling code
    - **Estimated Effort**: M (2-3hrs)
    - **Dependencies**: Task 5.1, 5.2, 5.3, 5.4, 5.5 complete
    - **Files**: `/packages/cli/tests/test_error_handling.py`
    - **Testing**: Run: `pytest packages/cli/tests/test_error_handling.py -v`

---

### Phase 6: Technical Debt Resolution (2-3 days)

- [ ] **6.0 Implement comprehensive tests for migration and LLM error paths (TD-P1-001, TD-P2-001)**
  - [ ] **6.1 Create migration test suite for data safety (TD-P1-001)**
    - Create `/packages/core/tests/store/test_migrations.py`
    - Test v1 → v2 migration (add access_history column):
      - Setup: Create v1 database schema
      - Insert: 100 test chunks with activations
      - Insert: 50 test activations
      - Run: Migration to v2
      - Verify: All 100 chunks preserved (no data loss)
      - Verify: All 50 activations preserved
      - Verify: New column `access_history` exists in activations table
      - Verify: access_history column has correct type (JSON)
      - Query: Sample data to ensure integrity
    - Test empty database migration:
      - Setup: Empty v1 database
      - Run: Migration to v2
      - Verify: No errors
      - Verify: Schema upgraded correctly
    - Test migration with NULL values:
      - Setup: v1 database with NULL embeddings (allowed in v1)
      - Run: Migration to v2
      - Verify: NULLs handled gracefully
      - Verify: No data corruption
    - Test migration with malformed JSON:
      - Setup: v1 database with invalid JSON in metadata
      - Run: Migration to v2
      - Verify: Error caught and logged
      - Verify: Migration continues for valid rows
      - Or: Migration fails with clear error (depending on policy)
    - **Acceptance**: Migration tests cover main path and edge cases
    - **Estimated Effort**: M (4-6hrs)
    - **Files**: `/packages/core/tests/store/test_migrations.py`
    - **Testing**: Run: `pytest packages/core/tests/store/test_migrations.py -v`

  - [ ] **6.2 Create migration rollback tests (TD-P1-001)**
    - In `/packages/core/tests/store/test_migrations.py`
    - Test rollback on migration failure:
      - Setup: v1 database with test data
      - Mock: Migration failure mid-process (e.g., constraint violation)
      - Run: Migration to v2
      - Verify: Migration fails
      - Verify: Rollback triggered automatically
      - Verify: Database restored to v1 state
      - Verify: All original data intact
    - Test transaction atomicity:
      - Setup: v1 database
      - Inject: Error in middle of migration
      - Verify: No partial changes committed
      - Verify: Database either fully v1 or fully v2 (no in-between)
    - Test error message quality:
      - Trigger: Migration failure
      - Verify: Error message includes:
        - Migration version attempted (v1→v2)
        - Error location (table, column)
        - Database state before failure
        - Rollback status
    - **Acceptance**: Rollback tests verify database consistency after failures
    - **Estimated Effort**: M (3-4hrs)
    - **Dependencies**: Task 6.1 complete
    - **Files**: `/packages/core/tests/store/test_migrations.py`
    - **Testing**: Run: `pytest packages/core/tests/store/test_migrations.py::test_rollback* -v`

  - [ ] **6.3 Create migration error condition tests (TD-P1-001)**
    - In `/packages/core/tests/store/test_migrations.py`
    - Test database locked during migration:
      - Setup: v1 database
      - Mock: SQLite LOCKED error
      - Run: Migration to v2
      - Verify: Error caught with clear message
      - Verify: Migration aborted safely
    - Test insufficient permissions:
      - Setup: v1 database with read-only permissions
      - Run: Migration to v2
      - Verify: Permission error caught
      - Verify: Helpful error message (check permissions)
    - Test disk full during migration:
      - Setup: v1 database
      - Mock: OSError (disk full)
      - Run: Migration to v2
      - Verify: Error caught
      - Verify: Rollback triggered
      - Verify: Message suggests freeing disk space
    - **Acceptance**: Error conditions handled gracefully with helpful messages
    - **Estimated Effort**: S (2-3hrs)
    - **Dependencies**: Task 6.1 complete
    - **Files**: `/packages/core/tests/store/test_migrations.py`
    - **Testing**: Run: `pytest packages/core/tests/store/test_migrations.py -v`

  - [ ] **6.4 Verify migration test coverage meets 80%+ target (TD-P1-001)**
    - Run: `pytest packages/core/tests/store/test_migrations.py --cov=aurora_core.store.migrations --cov-report=term-missing`
    - Review: Coverage report
    - Identify: Uncovered lines in `migrations.py`
    - Add: Tests for uncovered code paths:
      - Edge cases
      - Error handling branches
      - Helper functions
    - Achieve: 80%+ line coverage on `migrations.py`
    - Document: Coverage report in task notes
    - **Acceptance**: migrations.py has 80%+ test coverage
    - **Estimated Effort**: S (2-3hrs)
    - **Dependencies**: Task 6.1, 6.2, 6.3 complete
    - **Files**: `/packages/core/tests/store/test_migrations.py`
    - **Testing**: Run: `pytest packages/core/tests/store/test_migrations.py --cov=aurora_core.store.migrations --cov-report=html`

  - [ ] **6.5 Create LLM client error path tests (TD-P2-001)**
    - Create `/packages/reasoning/tests/test_llm_client_errors.py`
    - Test API key validation:
      - Test: Missing API key (env var not set)
        - Unset: `ANTHROPIC_API_KEY` environment variable
        - Run: `LLMClient(provider="anthropic")`
        - Verify: Raises `ConfigurationError`
        - Verify: Error message mentions "ANTHROPIC_API_KEY"
        - Verify: Error suggests environment variable or config file
      - Test: Empty API key (env var = "")
        - Set: `ANTHROPIC_API_KEY=""`
        - Run: `LLMClient(provider="anthropic")`
        - Verify: Raises `ConfigurationError`
        - Verify: Error message indicates key is empty
      - Test: Invalid API key format
        - Set: `ANTHROPIC_API_KEY="invalid-format"`
        - Run: `LLMClient(provider="anthropic")`
        - Verify: Warning logged (optional: allow, will fail on API call)
    - **Acceptance**: API key validation tests cover all error paths
    - **Estimated Effort**: S (1-2hrs)
    - **Files**: `/packages/reasoning/tests/test_llm_client_errors.py`
    - **Testing**: Run: `pytest packages/reasoning/tests/test_llm_client_errors.py -v`

  - [ ] **6.6 Create LLM client dependency tests (TD-P2-001)**
    - In `/packages/reasoning/tests/test_llm_client_errors.py`
    - Test missing anthropic package:
      - Mock: Import failure for `anthropic` module
      - Run: `LLMClient(provider="anthropic")`
      - Verify: Raises `ImportError` or `ConfigurationError`
      - Verify: Error message says "anthropic package not found"
      - Verify: Error suggests: "pip install anthropic"
    - Test rate limiter initialization:
      - Mock: Invalid rate limit values in config
      - Run: `LLMClient(provider="anthropic", rate_limit=-1)`
      - Verify: Error caught or default rate limits used
      - Verify: System logs warning
    - Test client instantiation failures:
      - Mock: Network unavailable during client creation
      - Run: `LLMClient(provider="anthropic")`
      - Verify: Error handled gracefully
      - Verify: Helpful error message
    - Test invalid model name:
      - Run: `LLMClient(provider="anthropic", model="invalid-model")`
      - Verify: Warning logged (will fail on API call)
        - Or: Immediate validation if model list available
    - **Acceptance**: Dependency and initialization tests cover error paths
    - **Estimated Effort**: M (2-3hrs)
    - **Dependencies**: Task 6.5 complete
    - **Files**: `/packages/reasoning/tests/test_llm_client_errors.py`
    - **Testing**: Run: `pytest packages/reasoning/tests/test_llm_client_errors.py -v`

  - [ ] **6.7 Improve LLM client error messages based on tests (TD-P2-001)**
    - In `/packages/reasoning/src/aurora_reasoning/llm_client.py`
    - Review: Current error messages in initialization code
    - Enhance: Error messages based on test requirements:
      - Missing API key: Add multi-line message with setup instructions
      - Missing package: Add installation command
      - Rate limiter errors: Add fallback and warning
    - Add: Troubleshooting steps to each error message
    - Add: Links to documentation where appropriate
    - Test: Run new tests to verify improved messages
    - **Acceptance**: Error messages are clear and actionable
    - **Estimated Effort**: S (1-2hrs)
    - **Dependencies**: Task 6.5, 6.6 complete
    - **Files**: `/packages/reasoning/src/aurora_reasoning/llm_client.py`
    - **Testing**: Verify with: `pytest packages/reasoning/tests/test_llm_client_errors.py -v`

  - [ ] **6.8 Verify LLM client test coverage meets 70%+ target (TD-P2-001)**
    - Run: `pytest packages/reasoning/tests/test_llm_client_errors.py --cov=aurora_reasoning.llm_client --cov-report=term-missing`
    - Review: Coverage report for `llm_client.py`
    - Identify: Uncovered initialization and error handling code
    - Add: Tests for uncovered paths:
      - Edge cases in initialization
      - Error handling branches
      - Fallback logic
    - Achieve: 70%+ line coverage on `llm_client.py`
    - Document: Coverage improvements in commit message
    - **Acceptance**: llm_client.py has 70%+ test coverage
    - **Estimated Effort**: M (2-3hrs)
    - **Dependencies**: Task 6.5, 6.6, 6.7 complete
    - **Files**: `/packages/reasoning/tests/test_llm_client_errors.py`
    - **Testing**: Run: `pytest packages/reasoning/tests/ --cov=aurora_reasoning.llm_client --cov-report=html`

---

### Phase 7: Documentation & Testing (4-6 hours)

- [ ] **7.0 Create comprehensive user-facing documentation and integration tests**
  - [ ] **7.1 Create CLI usage guide**
    - Create `/docs/cli/CLI_USAGE_GUIDE.md`
    - Section 1: Installation Verification
      - Command: `pip install -e packages/cli`
      - Command: `aur --version`
      - Expected: Version number displayed
    - Section 2: Initial Setup
      - Command: `aur init`
      - Walkthrough: Interactive prompts
      - Result: Config file created
      - Optional: Directory indexing
    - Section 3: Configuration
      - Subsection: Environment Variables
        - `ANTHROPIC_API_KEY` - API key for LLM
        - `AURORA_ESCALATION_THRESHOLD` - Complexity threshold
        - `AURORA_LOGGING_LEVEL` - Logging verbosity
      - Subsection: Config File Structure
        - Location: `~/.aurora/config.json`
        - Schema: Document each field
        - Example: Full config file example
      - Subsection: Precedence
        - CLI flags > Env vars > Config file > Defaults
    - Section 4: Basic Queries
      - Command: `aur query "How does authentication work?"`
      - Example: Simple query (direct LLM)
      - Example: Complex query (AURORA pipeline)
      - Flag: `--force-direct` - Force direct LLM
      - Flag: `--force-aurora` - Force AURORA
      - Flag: `--show-reasoning` - Show escalation reasoning
      - Flag: `--verbose` - Show SOAR phase trace
      - Flag: `--dry-run` - Test without API calls
    - Section 5: Memory Management
      - Command: `aur mem index <path>`
      - Example: Index current directory
      - Example: Index specific project
      - Command: `aur mem search "query"`
      - Flag: `--limit N` - Limit results
      - Flag: `--format json` - JSON output
      - Command: `aur mem stats` (optional)
      - Example: View memory statistics
    - Section 6: Headless Mode
      - Command: `aur headless <prompt-file>`
      - Prompt file structure
      - Budget and iteration limits
      - Output file location
    - Section 7: Troubleshooting
      - Issue: "ANTHROPIC_API_KEY not found"
        - Solution: Set environment variable or run `aur init`
      - Issue: "Memory store is locked"
        - Solution: Close other AURORA processes
      - Issue: "Rate limit exceeded"
        - Solution: Wait or upgrade API tier
      - Issue: Slow queries
        - Solution: Use `--force-direct` for simple queries
      - Issue: No memory results
        - Solution: Run `aur mem index .`
    - **Acceptance**: Comprehensive guide covers all CLI features with examples
    - **Estimated Effort**: M (2-3hrs)
    - **Files**: `/docs/cli/CLI_USAGE_GUIDE.md`
    - **Testing**: Manual review, test all examples in guide

  - [ ] **7.2 Create error message catalog**
    - Create `/docs/cli/ERROR_CATALOG.md`
    - Format each error as:
      ```markdown
      ## ERR-XXX: Error Title

      **Message**: "Actual error message displayed to user"

      **Cause**: What causes this error

      **Solutions**:
      1. Step-by-step solution 1
      2. Step-by-step solution 2

      **Related**: ERR-YYY, ERR-ZZZ
      ```
    - Catalog errors from Phase 5 (FR-5.x):
      - ERR-001: API Authentication Failed
      - ERR-002: Rate Limit Exceeded
      - ERR-003: Network Error
      - ERR-004: Model Not Found
      - ERR-005: Missing API Key (Config)
      - ERR-006: Invalid Config File (JSON Syntax)
      - ERR-007: Invalid Config Values
      - ERR-008: Database Locked
      - ERR-009: Insufficient Permissions
      - ERR-010: Disk Full
      - ERR-011: Corrupted Database
    - Add: Index at top (links to each error)
    - Add: Appendix with common patterns
    - Cross-reference: CLI usage guide troubleshooting section
    - **Acceptance**: All error messages documented with solutions
    - **Estimated Effort**: S (1-2hrs)
    - **Files**: `/docs/cli/ERROR_CATALOG.md`
    - **Testing**: Manual review, verify error codes match implementation

  - [ ] **7.3 Create integration test suite documentation**
    - Create `/packages/cli/tests/integration/README.md`
    - Section 1: Overview
      - Purpose: Test end-to-end CLI workflows
      - Scope: Query execution, memory management, configuration
    - Section 2: Requirements
      - Environment: `ANTHROPIC_API_KEY` required for real API tests
      - Budget: ~$5/month for nightly runs
      - Dependencies: pytest, real database, real API client
    - Section 3: Running Integration Tests
      - Command: `pytest packages/cli/tests/integration/ -v`
      - Command: `pytest packages/cli/tests/integration/ --real-api` (flag to enable API tests)
      - Skip tests: If no API key, tests skip gracefully
    - Section 4: Test Coverage
      - Workflow 1: Install → Init → Query (simple)
      - Workflow 2: Install → Init → Index → Query (complex)
      - Workflow 3: Query with empty memory (auto-index prompt)
      - Workflow 4: Memory indexing and search
      - Workflow 5: Error scenarios (invalid API key, etc.)
    - Section 5: Mocking Strategy
      - When to mock: CI runs without API budget
      - When to use real API: Nightly validation, pre-release
      - Mock approach: Patch LLMClient and orchestrator
    - Section 6: Adding New Tests
      - Template: Test structure
      - Guidelines: Test naming, setup, assertions
    - **Acceptance**: Integration test documentation is clear and complete
    - **Estimated Effort**: S (1hr)
    - **Files**: `/packages/cli/tests/integration/README.md`
    - **Testing**: Manual review

  - [ ] **7.4 Create comprehensive integration test suite**
    - Review existing integration tests from Phase 2 and Phase 4
    - Add missing workflow tests:
      - Test: Install → Init → Query workflow
        - Fresh virtualenv
        - Install CLI package
        - Run `aur init` (mock user input)
        - Run `aur query "test"`
        - Verify: Response received
      - Test: Configuration precedence
        - Set: Environment variable
        - Create: Config file with different value
        - Run: Query
        - Verify: Env var value used
      - Test: Error recovery
        - Mock: Rate limit on first call
        - Run: Query
        - Verify: Automatic retry succeeds
      - Test: Headless mode (verification only)
        - Create: Test prompt file
        - Run: `aur headless <file>`
        - Verify: Executes without errors (was already working)
    - Ensure: All integration tests can run with mocked API
    - Add: `@pytest.mark.integration` marker
    - Add: `@pytest.mark.real_api` marker for tests requiring real API
    - **Acceptance**: Comprehensive integration tests cover all key workflows
    - **Estimated Effort**: M (3-4hrs)
    - **Dependencies**: Phase 2, 4 integration tests complete
    - **Files**: `/packages/cli/tests/integration/test_workflows.py`
    - **Testing**: Run: `pytest packages/cli/tests/integration/ -v -m integration`

  - [ ] **7.5 Update main README with CLI examples**
    - In `/README.md`
    - Update: "Quick Start" section
      - Add: CLI installation
        ```bash
        pip install -e packages/cli
        ```
      - Add: CLI initialization
        ```bash
        aur init
        ```
      - Add: Example query
        ```bash
        aur query "How does authentication work?"
        ```
    - Update: "Features" section
      - Add: CLI bullet points
        - "✓ Command-line interface for queries"
        - "✓ Automatic escalation (direct LLM vs AURORA)"
        - "✓ Memory indexing and search"
        - "✓ Headless mode for batch processing"
    - Add: "What's New in v1.1.0" section
      - Completed CLI implementation
      - Configuration management
      - Memory management commands
      - Comprehensive error handling
      - Migration and LLM client test coverage
    - Update: "Usage Examples" section
      - Add: CLI examples
        ```bash
        # Basic query
        aur query "What is a decorator?"

        # Complex query with verbose mode
        aur query "Refactor auth system" --force-aurora --verbose

        # Index codebase
        aur mem index .

        # Search memory
        aur mem search "login function"
        ```
    - Add: Link to CLI usage guide
      - "For detailed CLI documentation, see [CLI Usage Guide](docs/cli/CLI_USAGE_GUIDE.md)"
    - Update: "Testing" section
      - Add: Integration test information
      - Add: Test coverage achievements
    - **Acceptance**: README updated with CLI information and examples
    - **Estimated Effort**: S (1hr)
    - **Files**: `/README.md`
    - **Testing**: Manual review, verify all commands work

  - [ ] **7.6 Run full test suite and verify coverage targets**
    - Run: All unit tests
      - Command: `pytest packages/cli/tests/ -v`
      - Verify: All tests pass
    - Run: All integration tests (with mocked API)
      - Command: `pytest packages/cli/tests/integration/ -v`
      - Verify: All tests pass
    - Run: Coverage analysis
      - CLI package: `pytest packages/cli/ --cov=aurora_cli --cov-report=term-missing`
      - Target: 85%+ coverage
      - migrations.py: `pytest packages/core/tests/store/test_migrations.py --cov=aurora_core.store.migrations`
      - Target: 80%+ coverage
      - llm_client.py: `pytest packages/reasoning/tests/test_llm_client_errors.py --cov=aurora_reasoning.llm_client`
      - Target: 70%+ coverage
    - Generate: HTML coverage reports
      - Command: `pytest --cov --cov-report=html`
      - Review: htmlcov/index.html
    - Document: Coverage results
      - Create: `TESTING_RESULTS.md` with coverage summary
    - If targets not met:
      - Identify: Uncovered code
      - Add: Tests for uncovered lines
      - Iterate: Until targets met
    - **Acceptance**: All coverage targets met (CLI 85%+, migrations 80%+, llm_client 70%+)
    - **Estimated Effort**: M (2-3hrs)
    - **Dependencies**: All Phase 2-6 tests complete
    - **Files**: Test suite, coverage reports
    - **Testing**: Run full suite: `pytest -v --cov`

  - [ ] **7.7 Perform manual testing checklist for user acceptance**
    - Create: Manual testing checklist
    - Test: Fresh installation workflow
      - [ ] Clean virtualenv
      - [ ] Install CLI: `pip install -e packages/cli`
      - [ ] Verify: `aur --version` works
      - [ ] Run: `aur init`
      - [ ] Verify: Config file created at `~/.aurora/config.json`
      - [ ] Run: `aur query "test"` with API key
      - [ ] Verify: Response received
      - [ ] Time to first response: <5 minutes
    - Test: Memory workflow
      - [ ] Run: `aur mem index .`
      - [ ] Verify: Progress bar displayed
      - [ ] Verify: Summary shows files/chunks count
      - [ ] Run: `aur mem search "function"`
      - [ ] Verify: Results displayed with highlighting
      - [ ] Verify: Results are relevant
    - Test: Error scenarios
      - [ ] Unset API key
      - [ ] Run: `aur query "test"`
      - [ ] Verify: Clear error message about missing key
      - [ ] Verify: Suggests how to set API key
      - [ ] Set invalid API key
      - [ ] Run: `aur query "test"`
      - [ ] Verify: Authentication error message
      - [ ] Verify: Exit code 1
    - Test: Escalation modes
      - [ ] Run: Simple query without flags
      - [ ] Verify: Auto-selects direct LLM
      - [ ] Run: Complex query without flags
      - [ ] Verify: Auto-selects AURORA
      - [ ] Run: `aur query "test" --show-reasoning`
      - [ ] Verify: Escalation reasoning displayed
    - Test: Verbose mode
      - [ ] Run: `aur query "test" --force-aurora --verbose`
      - [ ] Verify: Phase trace displayed
      - [ ] Verify: Timing information shown
    - Test: Dry-run mode
      - [ ] Run: `aur query "test" --dry-run`
      - [ ] Verify: Configuration displayed
      - [ ] Verify: API key redacted
      - [ ] Verify: No API call made (check account)
    - Document: Results in testing report
    - **Acceptance**: All manual tests pass, user workflows smooth
    - **Estimated Effort**: M (2-3hrs)
    - **Dependencies**: All implementation complete
    - **Files**: Manual testing checklist (document)
    - **Testing**: Manual execution by developer

---

## Post-Implementation Verification

After all tasks complete, verify these success criteria from PRD:

- [ ] **Functional Completion**
  - [ ] All TODO comments removed from `/packages/cli/src/aurora_cli/main.py`
  - [ ] `aur query "question"` executes full SOAR pipeline
  - [ ] `aur query "simple"` uses direct LLM correctly
  - [ ] `aur init` creates config and indexes directory
  - [ ] `aur mem search "term"` returns relevant results
  - [ ] LLM errors show actionable messages
  - [ ] All commands in `aur --help` work

- [ ] **Test Coverage**
  - [ ] CLI package: 85%+ coverage
  - [ ] migrations.py: 80%+ coverage
  - [ ] llm_client.py: 70%+ coverage
  - [ ] Integration tests: All workflows covered

- [ ] **Documentation**
  - [ ] CLI usage guide complete
  - [ ] Error catalog complete
  - [ ] README updated with CLI examples
  - [ ] Integration test documentation complete

- [ ] **User Acceptance**
  - [ ] User completes: `aur init` → `aur query` → response
  - [ ] User can index codebase
  - [ ] User can search memory
  - [ ] Error messages lead to resolution
  - [ ] Time to first response: <5 minutes

---

## Git Commit Guidelines

For this project, commit messages should follow this pattern:

**After Phase 1** (Smoke Tests):
```bash
git add packages/examples/smoke_test_*.py packages/examples/run_smoke_tests.sh
git commit -m "feat(cli): add smoke test suite for core API validation

Add Python smoke test scripts for memory store, SOAR orchestrator, and LLM client.
These validate core components work via Python API before CLI implementation.

- Memory store: Create, index, search, ACT-R activation
- SOAR orchestrator: Query decomposition, planning, agent selection
- LLM client: Initialization, API calls, rate limiting
- Master runner: Execute all smoke tests with summary

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

**After Phase 2** (CLI Execution):
```bash
git add packages/cli/src/aurora_cli/execution.py packages/cli/src/aurora_cli/main.py
git commit -m "feat(cli): implement query execution with SOAR and direct LLM

Complete CLI execution engine by wiring SOAR orchestrator and direct LLM calls.
Remove TODO comments from main.py lines 151-166.

- Add QueryExecutor class for execution abstraction
- Implement execute_aurora() with SOAR integration
- Implement execute_direct_llm() with optional memory context
- Add verbose mode with phase trace formatting
- Wire executor into CLI query command

Closes #[issue-number] (if applicable)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

**After Phase 3** (Configuration):
```bash
git add packages/cli/src/aurora_cli/config.py packages/cli/src/aurora_cli/commands/init.py
git commit -m "feat(cli): add configuration management and init command

Implement configuration system with file and environment variable support.
Add 'aur init' command for easy setup.

- Define Config dataclass with validation
- Implement load_config() with precedence (Env > File > Defaults)
- Add init command with API key prompt and optional indexing
- Support ~/.aurora/config.json and ./aurora.config.json
- Set secure file permissions (0600)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

**After Phase 4** (Memory):
```bash
git add packages/cli/src/aurora_cli/memory_manager.py packages/cli/src/aurora_cli/commands/memory.py
git commit -m "feat(cli): implement memory indexing and search with rich output

Complete memory management commands with progress reporting and rich formatting.

- Add MemoryManager class for memory operations
- Implement index_path() with progress callback
- Enhance search with hybrid (keyword + semantic) ranking
- Add rich output formatting with syntax highlighting
- Add auto-index prompt for first-time queries
- Support --format json for programmatic use

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

**After Phase 5** (Error Handling):
```bash
git add packages/cli/src/aurora_cli/errors.py packages/cli/src/aurora_cli/execution.py
git commit -m "feat(cli): add comprehensive error handling with retry logic

Implement error handling for API, config, and memory errors with actionable messages.

- Add ErrorHandler class with formatted error messages
- Implement API error handling (auth, rate limit, network) with retry
- Implement config error handling with setup instructions
- Implement memory error handling with recovery steps
- Add --dry-run mode for testing configuration
- Add exponential backoff retry for transient failures

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

**After Phase 6** (Technical Debt):
```bash
git add packages/core/tests/store/test_migrations.py packages/reasoning/tests/test_llm_client_errors.py
git commit -m "test: add migration and LLM client error path tests (TD-P1-001, TD-P2-001)

Address P1 technical debt with comprehensive test coverage.

- Add migration test suite (80%+ coverage on migrations.py)
  - Test v1→v2 migration with data preservation
  - Test rollback on failure
  - Test error conditions (locked, permissions, disk full)
- Add LLM client error path tests (70%+ coverage on llm_client.py)
  - Test API key validation
  - Test missing anthropic package
  - Test initialization failures
  - Improve error messages

Closes TD-P1-001, TD-P2-001

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

**After Phase 7** (Documentation):
```bash
git add docs/cli/CLI_USAGE_GUIDE.md docs/cli/ERROR_CATALOG.md README.md
git commit -m "docs: add comprehensive CLI documentation and update README

Complete user-facing documentation for CLI features.

- Add CLI usage guide with examples for all commands
- Add error catalog with solutions (ERR-001 through ERR-011)
- Update README with CLI quick start and v1.1.0 features
- Add integration test documentation
- Update testing section with coverage achievements

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Estimated Task Timeline

**Week 1:**
- Day 1 Morning: Phase 1 (Smoke Tests) - 2 hours
- Day 1 Afternoon: Phase 2 Start (Execution Module) - 4 hours
- Day 2: Phase 2 Complete (CLI Integration, Tests) - 6 hours
- Day 3: Phase 3 (Configuration System) - 6 hours

**Week 2:**
- Day 4: Phase 4 (Memory Management) - 6 hours
- Day 5: Phase 5 (Error Handling) - 6 hours
- Day 6-7: Phase 6 (Technical Debt) - 2 days

**Week 3:**
- Day 8: Phase 7 (Documentation & Integration Tests) - 6 hours
- Day 9: Manual Testing & Verification - 4 hours
- Day 10: Buffer for issues/refinement - 4 hours

**Total: 5-7 working days (flexible based on team velocity)**

---

## Notes for Using with 3-process-task-list Agent

This task list is designed for systematic execution:

1. **Sequential Phases**: Each phase has clear dependencies
2. **Atomic Tasks**: Each sub-task is 1-4 hours maximum
3. **Testable**: Every task has acceptance criteria
4. **Dependencies Marked**: Tasks note which prior tasks must complete
5. **Files Listed**: Specific file paths for each task
6. **Testing Approach**: Unit/integration/manual testing specified

When using with `3-process-task-list` agent:
- Start with Phase 1, complete all tasks before Phase 2
- Verify smoke tests pass before proceeding to CLI implementation
- Run tests after each task to catch issues early
- Update this document to check off completed tasks
- Document any blockers or deviations in task notes

---

**End of Task List**
