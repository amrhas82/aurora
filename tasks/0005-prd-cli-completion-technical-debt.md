# Product Requirements Document: CLI Completion & P1 Technical Debt

**PRD ID**: 0005
**Feature Name**: CLI Completion & Critical Technical Debt Resolution
**Version**: 1.0
**Status**: Draft
**Created**: 2025-12-24
**Owner**: Product Manager
**Target Release**: AURORA v1.1.0

---

## Table of Contents

1. [Introduction/Overview](#introductionoverview)
2. [Goals](#goals)
3. [User Stories](#user-stories)
4. [Functional Requirements](#functional-requirements)
5. [Non-Goals (Out of Scope)](#non-goals-out-of-scope)
6. [Design Considerations](#design-considerations)
7. [Technical Considerations](#technical-considerations)
8. [Success Metrics](#success-metrics)
9. [Open Questions](#open-questions)

---

## Introduction/Overview

### Problem Statement

AURORA v1.0.0 MVP is complete with 87% test coverage and all core components fully functional. However, the CLI is currently a **stub implementation** that parses commands but cannot execute queries. Users who install AURORA expecting a working CLI discover:

1. `aur query` shows escalation decisions but displays "execution not yet implemented"
2. No LLM client configuration or initialization in CLI
3. Memory commands exist but return empty results (no indexed data)
4. Cannot execute any actual queries through the CLI

Additionally, several **P1 (High Priority) technical debt items** pose data integrity and runtime reliability risks that should be addressed before CLI is promoted as production-ready.

### Current State

**What Works**:
- SOAR orchestrator (fully tested, 1,755+ tests passing)
- ACT-R activation system (validated against research)
- Memory store with semantic embeddings (87% coverage)
- CLI command parsing and escalation decision logic
- Installation and dependency management

**What's Missing**:
- CLI execution engine (TODO comments in code)
- LLM configuration and initialization
- Memory store initialization and code indexing
- Config file support
- Error handling for runtime failures

### High-Level Goal

Complete the CLI implementation to wire up existing, tested components into a functional command-line tool, while addressing critical technical debt items (TD-P1-001, TD-P2-001) that affect data integrity and error handling.

---

## Goals

### Primary Goals (Must Have for v1.1.0)

1. **Functional CLI**: Users can execute `aur query "question"` and receive LLM-generated responses
2. **LLM Configuration**: Support Anthropic API key configuration via environment variables and config file
3. **Memory Initialization**: Enable users to index codebases and search memory effectively
4. **Core Workflow**: Complete `aur init` → `aur mem index` → `aur query` workflow
5. **Data Safety**: Add migration tests (TD-P1-001) to prevent data corruption
6. **Error Reliability**: Test LLM initialization error paths (TD-P2-001) for better error messages

### Secondary Goals (Nice to Have)

1. **Smoke Test Suite**: Validate core components work via Python API before CLI work
2. **Dry-Run Mode**: Add `--dry-run` flag for testing configuration without API calls
3. **Enhanced Memory Commands**: Complete `aur mem search` with rich output

### Success Criteria

- [ ] `aur query "question"` executes full SOAR pipeline and returns response
- [ ] `aur query "simple question"` uses direct LLM mode correctly
- [ ] `aur init` creates config file and indexes current directory
- [ ] `aur mem search "term"` returns relevant code chunks
- [ ] LLM errors show actionable messages (e.g., "Check ANTHROPIC_API_KEY")
- [ ] Migration tests achieve 80%+ coverage on migrations.py
- [ ] LLM client error path tests achieve 70%+ coverage on llm_client.py
- [ ] All TODO comments removed from CLI code
- [ ] Documentation updated with CLI usage examples

---

## User Stories

### Epic 1: CLI Query Execution

**US-001: As a developer, I want to query AURORA via CLI so that I can get intelligent responses to my code questions**

**Acceptance Criteria**:
- Given I have AURORA installed and configured
- When I run `aur query "How does authentication work?"`
- Then the system assesses query complexity
- And executes either direct LLM or full SOAR pipeline
- And returns a formatted response to stdout
- And the response is relevant to my codebase context

**Testing**:
- Unit tests for query command with mocked LLM
- Integration test with real API call (anthropic test key)
- Test both escalation paths (direct vs AURORA)

---

**US-002: As a developer, I want control over escalation behavior so that I can optimize for speed or quality**

**Acceptance Criteria**:
- Given I run `aur query "question" --force-direct`
- Then the system bypasses escalation and uses direct LLM
- When I run `aur query "question" --force-aurora`
- Then the system uses full SOAR pipeline regardless of complexity
- When I use `--show-reasoning`
- Then I see complexity score, confidence, and escalation decision

**Testing**:
- Test `--force-direct` flag forces direct LLM
- Test `--force-aurora` flag forces SOAR
- Test `--show-reasoning` displays all decision factors
- Test default behavior follows complexity threshold

---

**US-003: As a developer, I want verbose output so that I can debug issues and understand system behavior**

**Acceptance Criteria**:
- Given I run `aur query "question" --verbose`
- Then I see SOAR phase execution trace
- When I use `--verbose --show-reasoning`
- Then I see both escalation analysis and phase execution
- Default mode (no `--verbose`) shows only final response

**Testing**:
- Test verbose mode shows phase trace
- Test default mode shows only response
- Test combined flags work together

---

### Epic 2: Configuration & Setup

**US-004: As a new user, I want to initialize AURORA easily so that I can start using it quickly**

**Acceptance Criteria**:
- Given I installed AURORA
- When I run `aur init`
- Then the system creates `~/.aurora/config.json` with defaults
- And prompts me: "Index current directory? [Y/n]"
- And if I answer "Y", indexes the current directory into memory
- And displays setup summary: "Indexed 42 files, 237 chunks"

**Testing**:
- Test `aur init` creates config file
- Test config file has correct defaults
- Test user prompt for indexing
- Test skipping indexing with "n"
- Test indexing counts are accurate

---

**US-005: As a developer, I want flexible API key configuration so that I can secure my credentials**

**Acceptance Criteria**:
- Given I set `ANTHROPIC_API_KEY` environment variable
- When I run any `aur query` command
- Then the system uses the environment variable key
- When I also have `~/.aurora/config.json` with `anthropic_api_key`
- Then environment variable takes precedence
- When neither exists
- Then I get clear error: "ANTHROPIC_API_KEY not found. Set via environment or ~/.aurora/config.json"

**Testing**:
- Test env var only (no config file)
- Test config file only (no env var)
- Test env var precedence over config
- Test error message when both missing
- Test error suggests configuration methods

---

**US-006: As a developer, I want to validate configuration without making API calls so that I can test setup**

**Acceptance Criteria**:
- Given I run `aur query "test" --dry-run`
- Then the system shows what it would execute
- And displays: "Would use: Direct LLM" or "Would use: AURORA"
- And shows configuration values (redacted API key)
- But does NOT make actual API calls
- And does NOT charge my API account

**Testing**:
- Test `--dry-run` prevents API calls
- Test dry-run shows escalation decision
- Test dry-run shows config values
- Test API key is redacted in output

---

### Epic 3: Memory Management

**US-007: As a developer, I want to index my codebase so that AURORA can provide contextual responses**

**Acceptance Criteria**:
- Given I have code in current directory
- When I run `aur mem index .`
- Then the system parses code files
- And creates code chunks
- And stores them in memory store with embeddings
- And shows progress: "Indexed: 42/100 files"
- And displays summary: "Indexed 100 files, 542 chunks"

**Testing**:
- Test indexing Python files
- Test indexing multiple languages
- Test progress indicator updates
- Test summary counts are correct
- Test repeated indexing updates existing chunks

---

**US-008: As a developer, I want to search memory for code so that I can verify indexing worked**

**Acceptance Criteria**:
- Given I have indexed code
- When I run `aur mem search "authentication"`
- Then the system searches both keyword and semantic
- And returns top-k relevant chunks (default: 5)
- And displays: file path, line range, chunk content preview
- And shows activation score and relevance

**Testing**:
- Test search returns relevant results
- Test search respects `--limit` parameter
- Test search handles no results gracefully
- Test search output formatting

---

**US-009: As a developer, I want automatic memory initialization so that I don't need manual setup**

**Acceptance Criteria**:
- Given I run `aur query` for the first time
- When memory store is empty
- Then the system prompts: "Memory empty. Index current directory? [Y/n]"
- And if I answer "Y", indexes before executing query
- And if I answer "n", runs query without memory context
- And remembers my choice for subsequent queries

**Testing**:
- Test first-time query shows prompt
- Test "Y" triggers indexing
- Test "n" skips indexing
- Test subsequent queries don't re-prompt

---

### Epic 4: Error Handling & User Experience

**US-010: As a developer, I want clear error messages so that I can fix problems quickly**

**Acceptance Criteria**:
- Given ANTHROPIC_API_KEY is invalid
- When I run `aur query "test"`
- Then I see: "API authentication failed. Check ANTHROPIC_API_KEY environment variable."
- When network is down
- Then I see: "Network error: Cannot reach Anthropic API. Check internet connection."
- When rate limited
- Then I see: "Rate limit exceeded. Retry in 60 seconds or upgrade API tier."

**Testing**:
- Test invalid API key error message
- Test network failure error message
- Test rate limit error message
- Test each suggests actionable fix

---

**US-011: As a developer, I want headless mode verified so that I can run batch experiments**

**Acceptance Criteria**:
- Given I have a prompt file `experiment.md`
- When I run `aur headless experiment.md`
- Then the system validates prompt structure
- And shows: "Budget: $5.00, Max Iterations: 10"
- And executes headless workflow
- And saves results to output file
- And displays final summary

**Testing**:
- Test headless command parses prompt file
- Test budget validation
- Test iteration limit enforcement
- Test output file creation
- Test summary display

---

### Epic 5: Technical Debt - Data Safety

**US-012: As a system maintainer, I want migration tests so that schema changes don't corrupt data**

**Acceptance Criteria** (from TD-P1-001):
- Given a migration from schema v1 to v2
- When migration is applied
- Then all existing data is preserved
- And new columns/tables are created correctly
- And rollback restores original state
- And edge cases (empty data, malformed JSON) are handled
- And file achieves 80%+ test coverage

**Testing**:
- Unit tests for each migration path (v1→v2, v2→v3)
- Integration tests with real SQLite database
- Test rollback scenarios
- Test error conditions (locked database, insufficient permissions)
- Test edge cases (empty tables, NULL values)

---

**US-013: As a system maintainer, I want LLM error path tests so that runtime failures are graceful**

**Acceptance Criteria** (from TD-P2-001):
- Given LLM client initialization
- When API key is missing
- Then clear error: "ANTHROPIC_API_KEY environment variable not set"
- When `anthropic` package not installed
- Then error: "anthropic package not found. Install: pip install anthropic"
- When rate limiter initialization fails
- Then system logs error and uses default rate limits
- And file achieves 70%+ test coverage

**Testing**:
- Test API key validation (missing, empty, invalid format)
- Test missing anthropic package (import mocking)
- Test rate limiter initialization failures
- Test client instantiation edge cases
- Improve error messages with troubleshooting steps

---

## Functional Requirements

### Phase 1: Smoke Test Core Components (2 hours)

#### FR-1.1: Memory Store Validation
**Priority**: MUST HAVE
**The system must** provide smoke test scripts to validate memory store functionality via Python API.

**Details**:
- Create `/examples/smoke_test_memory.py`
- Test: Create store, add chunks, search, retrieve by ID
- Test: ACT-R activation updates on access
- Test: Memory cleanup and close
- Expected output: "✓ Memory store: PASS"

---

#### FR-1.2: SOAR Orchestrator Validation
**Priority**: MUST HAVE
**The system must** provide smoke test scripts to validate SOAR orchestrator functionality.

**Details**:
- Create `/examples/smoke_test_soar.py`
- Test: Query decomposition
- Test: Subgoal planning
- Test: Agent selection (mocked execution)
- Expected output: "✓ SOAR orchestrator: PASS"

---

#### FR-1.3: LLM Client Validation
**Priority**: MUST HAVE
**The system must** provide smoke test scripts to validate LLM client functionality.

**Details**:
- Create `/examples/smoke_test_llm.py`
- Test: Client initialization with test API key
- Test: Simple prompt execution
- Test: Rate limiting and retry logic
- Expected output: "✓ LLM client: PASS"

---

#### FR-1.4: Smoke Test Orchestration
**Priority**: SHOULD HAVE
**The system should** provide a master smoke test runner.

**Details**:
- Create `/examples/run_smoke_tests.sh`
- Runs all smoke tests sequentially
- Displays summary: "3/3 tests passed"
- Exits with error code if any test fails

---

### Phase 2: CLI Execution Engine (1-2 days)

#### FR-2.1: SOAR Orchestrator Integration
**Priority**: MUST HAVE
**The system must** integrate SOAR orchestrator into `aur query` command.

**Details**:
- Location: `packages/cli/src/aurora_cli/main.py` lines 151-158
- Replace TODO with actual orchestrator call:
  ```python
  from aurora_soar.orchestrator import SOAROrchestrator
  from aurora_reasoning.llm_client import LLMClient

  llm = LLMClient(provider="anthropic", api_key=api_key)
  orchestrator = SOAROrchestrator(
      llm_client=llm,
      memory_store=memory_store,
      config=soar_config
  )
  response = orchestrator.execute(query_text)
  console.print(response.final_response)
  ```
- Handle errors gracefully
- Show spinner during execution: "⠋ Executing query..."

---

#### FR-2.2: Direct LLM Integration
**Priority**: MUST HAVE
**The system must** integrate direct LLM calls into `aur query` command.

**Details**:
- Location: `packages/cli/src/aurora_cli/main.py` lines 159-166
- Replace TODO with actual LLM call:
  ```python
  from aurora_reasoning.llm_client import LLMClient

  llm = LLMClient(provider="anthropic", api_key=api_key)
  response = llm.generate(
      prompt=query_text,
      max_tokens=500,
      temperature=0.7
  )
  console.print(response.content)
  ```
- Add optional memory context if memory exists
- Handle API errors with retry logic

---

#### FR-2.3: Response Formatting
**Priority**: MUST HAVE
**The system must** format responses appropriately for terminal display.

**Details**:
- Default mode: Clean response text only
- `--verbose`: Include phase execution trace
- `--show-reasoning`: Include escalation analysis
- Use rich library for formatted output
- Wrap long lines to terminal width

---

#### FR-2.4: Verbose Mode Implementation
**Priority**: SHOULD HAVE
**The system should** implement verbose mode with SOAR phase trace.

**Details**:
- Add `--verbose` flag to `aur query` command
- Display each SOAR phase execution:
  - Phase 1: Assess (keyword patterns detected)
  - Phase 2: Orient (context retrieved: 3 chunks)
  - Phase 3: Decompose (2 subgoals identified)
  - Phase 4: Verify (Option A: LLM self-check)
  - etc.
- Show timing for each phase
- Show cost for LLM phases

---

### Phase 3: Configuration Management (4-6 hours)

#### FR-3.1: Config File Structure
**Priority**: MUST HAVE
**The system must** define config file structure at `~/.aurora/config.json`.

**Details**:
```json
{
  "version": "1.1.0",
  "llm": {
    "provider": "anthropic",
    "anthropic_api_key": "sk-ant-...",
    "model": "claude-3-5-sonnet-20241022",
    "temperature": 0.7,
    "max_tokens": 4000
  },
  "escalation": {
    "threshold": 0.6,
    "enable_keyword_only": true,
    "force_mode": null
  },
  "memory": {
    "auto_index": true,
    "index_paths": ["."],
    "chunk_size": 500,
    "overlap": 50
  },
  "logging": {
    "level": "INFO",
    "file": "~/.aurora/aurora.log"
  }
}
```

---

#### FR-3.2: Config File Loading
**Priority**: MUST HAVE
**The system must** load configuration from file with environment variable override.

**Details**:
- Create `packages/cli/src/aurora_cli/config.py`
- Function: `load_config() -> Config`
- Search order:
  1. Current directory: `./aurora.config.json`
  2. Home directory: `~/.aurora/config.json`
  3. Environment variables (override file values)
  4. Built-in defaults
- Validate config schema
- Log which config source was used

---

#### FR-3.3: Init Command Implementation
**Priority**: MUST HAVE
**The system must** implement `aur init` command to create config file.

**Details**:
- Create `packages/cli/src/aurora_cli/commands/init.py`
- Check if config exists: "Config already exists at ~/.aurora/config.json"
- Prompt for API key (optional): "Enter Anthropic API key (or press Enter to skip):"
- Create config file with defaults
- Prompt: "Index current directory? [Y/n]"
- If "Y", run `aur mem index .`
- Display summary: "✓ Configuration created at ~/.aurora/config.json"

---

#### FR-3.4: Environment Variable Override
**Priority**: MUST HAVE
**The system must** allow environment variables to override config file values.

**Details**:
- Environment variable naming: `AURORA_<SECTION>_<KEY>`
- Examples:
  - `ANTHROPIC_API_KEY` overrides `llm.anthropic_api_key`
  - `AURORA_ESCALATION_THRESHOLD` overrides `escalation.threshold`
  - `AURORA_LOGGING_LEVEL` overrides `logging.level`
- Environment variables take precedence over config file
- Log when environment variable is used: "Using ANTHROPIC_API_KEY from environment"

---

#### FR-3.5: Config Validation
**Priority**: MUST HAVE
**The system must** validate configuration values and provide clear error messages.

**Details**:
- Validate API key format (starts with expected prefix)
- Validate numeric ranges (threshold: 0.0-1.0)
- Validate paths exist for `memory.index_paths`
- Validate enum values (provider, log level)
- Error format: "Invalid config: escalation.threshold must be 0.0-1.0, got 1.5"

---

### Phase 4: Memory Store Initialization (2-4 hours)

#### FR-4.1: Memory Index Command
**Priority**: MUST HAVE
**The system must** implement `aur mem index <path>` command to index codebases.

**Details**:
- Create or enhance `packages/cli/src/aurora_cli/commands/memory.py`
- Parse code files in specified path
- Create code chunks using existing parser registry
- Generate semantic embeddings
- Store in memory store
- Show progress bar: "Indexing: 42/100 files [=====>    ] 42%"
- Display summary: "✓ Indexed 100 files, 542 chunks in 12.3s"

---

#### FR-4.2: Memory Search Enhancement
**Priority**: SHOULD HAVE
**The system should** enhance `aur mem search` command with rich output.

**Details**:
- Current: Basic search exists but output minimal
- Enhancement: Rich formatted output
- Display for each result:
  - File path (clickable if terminal supports)
  - Line range: `Lines 42-58`
  - Activation score: `[0.87]`
  - Code preview (syntax highlighted)
  - Relevance explanation
- Support `--limit` parameter (default: 5)
- Support `--format json` for programmatic use

---

#### FR-4.3: Auto-Index Prompt
**Priority**: MUST HAVE
**The system must** prompt user to index when memory is empty.

**Details**:
- When `aur query` is run with empty memory
- Display: "Memory empty. Index current directory? [Y/n]"
- If "Y": Run indexing, then execute query
- If "n": Run query without memory context
- Save preference to config: `memory.prompted_index = true`
- Don't prompt again if user said "n" previously

---

#### FR-4.4: Memory Statistics
**Priority**: SHOULD HAVE
**The system should** provide memory statistics command.

**Details**:
- Add `aur mem stats` command
- Display:
  - Total chunks: 542
  - Total files: 100
  - Languages: Python (450 chunks), JavaScript (92 chunks)
  - Average activation: 0.65
  - Most accessed chunks (top 5)
  - Least accessed chunks (candidates for eviction)
  - Database size: 45.2 MB

---

### Phase 5: Error Handling (4-6 hours)

#### FR-5.1: LLM API Error Handling
**Priority**: MUST HAVE
**The system must** handle LLM API errors with actionable messages.

**Details**:
- **Authentication Error**:
  - Detect: HTTP 401 or "invalid API key"
  - Message: "Authentication failed. Check ANTHROPIC_API_KEY environment variable or ~/.aurora/config.json"
  - Exit code: 1

- **Rate Limit Error**:
  - Detect: HTTP 429
  - Message: "Rate limit exceeded. Retry in <seconds>s or upgrade API tier."
  - Retry automatically with exponential backoff (3 attempts)

- **Network Error**:
  - Detect: Connection timeout, DNS failure
  - Message: "Network error: Cannot reach Anthropic API. Check internet connection."
  - Suggest: "Try: ping api.anthropic.com"

- **Model Not Found**:
  - Detect: HTTP 404 on model
  - Message: "Model 'claude-x' not found. Available models: claude-3-5-sonnet-20241022, ..."

---

#### FR-5.2: Configuration Error Handling
**Priority**: MUST HAVE
**The system must** handle configuration errors with helpful messages.

**Details**:
- **Missing API Key**:
  - Message: "ANTHROPIC_API_KEY not found. Configure via:"
  - "  1. Environment: export ANTHROPIC_API_KEY=sk-ant-..."
  - "  2. Config file: aur init"

- **Invalid Config File**:
  - Detect: JSON parse error
  - Message: "Config file syntax error: Unexpected token at line 5"
  - Suggest: "Validate JSON: jsonlint ~/.aurora/config.json"

- **Invalid Config Values**:
  - Message: "Invalid config: escalation.threshold must be 0.0-1.0, got 1.5"
  - Show: "See: aur config --help"

---

#### FR-5.3: Memory Store Error Handling
**Priority**: MUST HAVE
**The system must** handle memory store errors gracefully.

**Details**:
- **Database Locked**:
  - Detect: SQLite LOCKED error
  - Message: "Memory store is locked. Close other AURORA processes."

- **Insufficient Permissions**:
  - Detect: Permission denied on database file
  - Message: "Cannot write to ~/.aurora/memory.db. Check file permissions."

- **Disk Full**:
  - Detect: Disk full error during indexing
  - Message: "Disk full. Free space needed: ~50MB"

- **Corrupted Database**:
  - Detect: SQLite corruption errors
  - Message: "Memory store is corrupted. Backup and recreate: aur mem reset"

---

#### FR-5.4: Dry-Run Mode
**Priority**: SHOULD HAVE
**The system should** implement `--dry-run` flag to test without API calls.

**Details**:
- Add `--dry-run` to `aur query` command
- Display:
  - "DRY RUN MODE - No API calls will be made"
  - Query complexity assessment
  - Escalation decision: "Would use: Direct LLM" or "Would use: AURORA"
  - Configuration summary:
    - Provider: anthropic
    - Model: claude-3-5-sonnet-20241022
    - API Key: sk-ant-...xyz (redacted)
    - Memory chunks: 542
  - Estimated cost: ~$0.002
- Exit without making API calls

---

### Phase 6: Technical Debt Resolution (2-3 days)

#### FR-6.1: Migration Test Suite (TD-P1-001)
**Priority**: MUST HAVE
**The system must** implement comprehensive migration tests to prevent data corruption.

**Details**:
- Location: `packages/core/tests/store/test_migrations.py`
- Test each migration path:
  - Test v1 → v2 migration (add access_history column)
  - Test v2 → v3 migration (future)
- Test rollback scenarios:
  - Test migration failure triggers rollback
  - Test partial migration cleanup
- Test edge cases:
  - Empty database migration
  - Malformed JSON in existing data
  - NULL values in required columns
- Test error conditions:
  - Database locked during migration
  - Insufficient permissions
  - Disk full during migration
- Target: 80%+ coverage on `migrations.py`

**Acceptance Test**:
```python
def test_v1_to_v2_migration_preserves_data():
    """Test migration preserves all existing data."""
    # Create v1 database with test data
    v1_db = create_v1_database()
    add_test_data(v1_db, chunks=100, activations=50)

    # Run migration
    migration = Migration(v1_db)
    migration.upgrade_to_v2()

    # Verify all data preserved
    assert count_chunks(v1_db) == 100
    assert count_activations(v1_db) == 50

    # Verify new columns exist
    assert column_exists(v1_db, "activations", "access_history")
```

---

#### FR-6.2: LLM Client Error Path Tests (TD-P2-001)
**Priority**: MUST HAVE
**The system must** implement tests for LLM client initialization error paths.

**Details**:
- Location: `packages/reasoning/tests/test_llm_client_errors.py`
- Test API key validation:
  - Missing API key (env var not set)
  - Empty API key (env var = "")
  - Invalid API key format
- Test missing anthropic package:
  - Mock import failure
  - Verify error message suggests installation
- Test rate limiter initialization:
  - Invalid rate limit values
  - Rate limiter initialization failure
- Test client instantiation failures:
  - Network unavailable during client creation
  - Invalid model name
- Target: 70%+ coverage on `llm_client.py`

**Acceptance Test**:
```python
def test_missing_api_key_error_message():
    """Test clear error when API key missing."""
    # Unset environment variable
    with mock.patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ConfigurationError) as exc:
            client = LLMClient(provider="anthropic")

        # Verify error message is helpful
        assert "ANTHROPIC_API_KEY" in str(exc.value)
        assert "environment variable" in str(exc.value).lower()
        assert "config file" in str(exc.value).lower()
```

---

#### FR-6.3: Migration Rollback Tests
**Priority**: MUST HAVE
**The system must** implement rollback tests to verify database consistency after failures.

**Details**:
- Test rollback on migration failure:
  - Trigger error mid-migration
  - Verify rollback restores original state
  - Verify no partial changes remain
- Test transaction atomicity:
  - Verify all-or-nothing migration
- Test error message includes debugging info:
  - Migration version attempted
  - Error location (line/column)
  - Database state before failure

---

### Phase 7: Documentation & Testing (4-6 hours)

#### FR-7.1: CLI Usage Documentation
**Priority**: MUST HAVE
**The system must** provide comprehensive CLI usage documentation.

**Details**:
- Create `docs/cli/CLI_USAGE_GUIDE.md`
- Sections:
  1. Installation verification
  2. Initial setup (`aur init`)
  3. Configuration (env vars, config file)
  4. Basic queries (`aur query`)
  5. Memory management (`aur mem`)
  6. Headless mode (`aur headless`)
  7. Troubleshooting common errors
- Include examples for each command
- Include expected output samples

---

#### FR-7.2: Integration Test Suite
**Priority**: MUST HAVE
**The system must** provide integration tests for end-to-end CLI workflows.

**Details**:
- Location: `packages/cli/tests/integration/`
- Test complete workflows:
  - Test: Install → Init → Query (simple)
  - Test: Install → Init → Index → Query (complex)
  - Test: Query with empty memory
  - Test: Query with auto-index prompt
- Use real API calls with test key (budget permitting)
- Mock API calls if budget constrained
- Target: 90%+ coverage on CLI commands

---

#### FR-7.3: Error Message Catalog
**Priority**: SHOULD HAVE
**The system should** document all error messages and their solutions.

**Details**:
- Create `docs/cli/ERROR_CATALOG.md`
- Format:
  ```markdown
  ## ERR-001: API Authentication Failed

  **Message**: "Authentication failed. Check ANTHROPIC_API_KEY..."

  **Cause**: Invalid or missing API key

  **Solutions**:
  1. Set environment variable: `export ANTHROPIC_API_KEY=...`
  2. Add to config: `aur init`
  3. Verify key at: https://console.anthropic.com

  **Related**: ERR-002, ERR-005
  ```
- Include all FR-5.x error messages
- Cross-reference troubleshooting guide

---

#### FR-7.4: README Update
**Priority**: MUST HAVE
**The system must** update README with CLI completion information.

**Details**:
- Update "Quick Start" section
- Add CLI examples:
  ```bash
  # Install
  pip install -e packages/cli

  # Initialize
  aur init

  # Query
  aur query "How does authentication work?"

  # Index codebase
  aur mem index .

  # Search memory
  aur mem search "login"
  ```
- Add "What's New in v1.1.0" section
- Link to CLI usage guide

---

## Non-Goals (Out of Scope)

### Explicitly NOT Included in v1.1.0

1. **Web UI or API Server**: CLI only; web interface is future work
2. **Advanced Features**:
   - Multi-turn conversation mode
   - Agent mode (autonomous execution beyond headless)
   - Streaming responses
3. **Performance Optimization**:
   - Caching of LLM responses
   - Async/parallel processing in CLI
   - Memory store indexing optimization
4. **Additional LLM Providers**:
   - OpenAI support deferred to v1.2.0
   - Only Anthropic in v1.1.0
5. **Interactive REPL Mode**: Single-shot commands only
6. **MCP Server Integration**: Deferred to post-v1.1.0
7. **Advanced Memory Features**:
   - Memory visualization
   - Memory export/import
   - Memory statistics dashboard
8. **Additional Technical Debt**: Only P1 items (TD-P1-001, TD-P2-001); P2/P3 deferred

---

## Design Considerations

### User Experience

**Expected User Workflow**:
1. User installs AURORA: `pip install -e packages/cli`
2. User initializes: `aur init` (creates config, prompts for indexing)
3. User queries: `aur query "How does X work?"`
4. System responds with answer using codebase context

**Terminal Output Design**:
- Use `rich` library for formatted output
- Color coding:
  - Blue: System actions ("→ Using AURORA")
  - Green: Success messages ("✓ Indexed 100 files")
  - Yellow: Warnings ("⚠ Memory empty")
  - Red: Errors ("✗ Authentication failed")
- Spinners for long operations: "⠋ Executing query..."
- Progress bars for indexing: "[=====>    ] 42%"

**Error Message Design**:
- Format: `[Context] What happened. Why it matters. How to fix.`
- Example: `[Config] ANTHROPIC_API_KEY not found. AURORA needs this to connect to LLM. Set via: export ANTHROPIC_API_KEY=...`
- Always include actionable next step
- Link to docs when appropriate: "See: https://docs.aurora.ai/errors/ERR-001"

### Configuration Philosophy

**Layered Configuration**:
1. **Defaults**: Built into code (conservative, safe values)
2. **Config File**: User preferences (`~/.aurora/config.json`)
3. **Environment Variables**: Session-specific overrides
4. **Command-Line Flags**: One-off overrides

**Precedence**: Flags > Env Vars > Config File > Defaults

**Security**:
- Never log full API keys (redact: `sk-ant-...xyz`)
- Config file permissions: 0600 (user read/write only)
- Warn if config file is world-readable

### Memory Store Design

**Smart Initialization**:
- Lazy loading: Only initialize when needed
- Auto-detect project type (Python, JavaScript, etc.)
- Default index paths based on project structure
- Skip common directories: `node_modules/`, `.git/`, `venv/`, `__pycache__/`

**Indexing Strategy**:
- Parse files in parallel (up to CPU count)
- Show progress every 10 files
- Handle parse errors gracefully (skip file, log warning)
- Incremental updates: Only re-index changed files

**Search Strategy**:
- Hybrid: Keyword (BM25) + Semantic (embeddings)
- Keyword weight: 0.3, Semantic weight: 0.7 (tunable)
- Apply ACT-R activation boost to frequently accessed chunks
- Return top-k with diversity (avoid returning 5 chunks from same file)

---

## Technical Considerations

### Integration Points

**Existing Components (Already Working)**:
- `aurora_core.store.memory.MemoryStore`: Tested, production-ready
- `aurora_soar.orchestrator.SOAROrchestrator`: Tested, 1,755+ tests passing
- `aurora_reasoning.llm_client.LLMClient`: Tested, supports Anthropic
- `aurora_core.activation.engine.ActivationEngine`: Validated against ACT-R research

**New Components (Need to Build)**:
- `aurora_cli.config.Config`: Load/validate configuration
- `aurora_cli.commands.init.InitCommand`: Initialize setup
- `aurora_cli.execution.QueryExecutor`: Execute queries via SOAR or direct LLM
- `aurora_cli.memory.MemoryManager`: Manage indexing and search

### Dependencies

**Required**:
- `click>=8.0`: CLI framework
- `rich>=13.0`: Terminal formatting
- `anthropic>=0.8.0`: Anthropic API client (already installed)

**Optional**:
- `sentence-transformers`: Semantic embeddings (already optional in core)

### Database Schema

**No Changes Required**: Existing schema is sufficient.

**Migration Note**: TD-P1-001 adds tests for existing v1→v2 migration, not a new migration.

### Error Recovery Strategy

**Network Errors**:
- Retry with exponential backoff: 100ms, 200ms, 400ms (3 attempts)
- Add jitter to avoid thundering herd
- Display: "Retrying in 0.4s... (attempt 2/3)"

**API Errors**:
- Authentication: Don't retry (fail fast)
- Rate limit: Retry after delay from response header
- Server error (5xx): Retry with backoff (transient failures)

**Database Errors**:
- Locked: Retry after 100ms (up to 5 seconds)
- Corrupted: Suggest backup and reset
- Disk full: Fail immediately with clear message

### Testing Strategy

**Unit Tests**:
- Mock LLM responses for CLI command tests
- Mock memory store for query execution tests
- Test each command in isolation
- Target: 85%+ coverage on CLI code

**Integration Tests**:
- Use real anthropic API with test key (budget: $5)
- Test end-to-end workflows
- Run in CI if budget allows, otherwise nightly
- Target: Key workflows have integration tests

**Smoke Tests**:
- Python API level validation (Phase 1)
- Throwaway after validation
- Not part of regular test suite

### Performance Targets

**Query Latency**:
- Direct LLM: <2 seconds (network + API)
- AURORA (simple): <5 seconds
- AURORA (complex): <15 seconds

**Indexing Performance**:
- 100 files: <30 seconds
- 1,000 files: <5 minutes
- Show progress every 10 files

**Memory Usage**:
- CLI idle: <50 MB
- During indexing: <500 MB
- During query: <200 MB

### Backward Compatibility

**Config File**:
- v1.0.0 had no config file → No breaking changes
- v1.1.0 config is new feature

**CLI Commands**:
- `aur mem` existed but was stub → Enhancement, not breaking
- `aur query` existed but was stub → Enhancement, not breaking
- `aur headless` existed → Verify still works (FR-11)

**Python API**:
- No changes to public APIs
- Only CLI-level additions

---

## Success Metrics

### Completion Metrics (Definition of Done)

**Functional Completion**:
- [ ] All TODO comments removed from CLI code
- [ ] All FR-2.x requirements (CLI execution) implemented
- [ ] All FR-3.x requirements (configuration) implemented
- [ ] All FR-4.x requirements (memory) implemented
- [ ] All FR-5.x requirements (error handling) implemented
- [ ] All FR-6.x requirements (technical debt) implemented

**Test Coverage**:
- [ ] CLI package: 85%+ coverage
- [ ] migrations.py: 80%+ coverage (TD-P1-001)
- [ ] llm_client.py: 70%+ coverage (TD-P2-001)
- [ ] Integration tests: All key workflows covered

**Documentation**:
- [ ] CLI usage guide created
- [ ] Error catalog created
- [ ] README updated
- [ ] All commands documented with examples

**User Acceptance**:
- [ ] User can complete workflow: `aur init` → `aur query` → receive response
- [ ] User can index codebase: `aur mem index .`
- [ ] User can search memory: `aur mem search "term"`
- [ ] Error messages are clear and actionable

### Quality Metrics

**Reliability**:
- Success rate: 95%+ for valid queries
- Error recovery: 95%+ of transient errors recovered
- No data corruption in migration tests

**Performance**:
- Query latency: Within targets (FR-7.x)
- Indexing speed: Within targets
- Memory usage: Within targets

**Usability**:
- New user can get first response within 5 minutes
- Error messages lead to resolution without docs (80% of cases)
- No user confusion about stub vs complete features

### Business Metrics (Optional)

**Adoption** (if tracking):
- CLI usage vs Python API usage
- Queries per user per day
- Indexing frequency

**Satisfaction** (if surveying):
- Net Promoter Score (NPS) for CLI
- Time to first successful query
- Support ticket reduction (fewer "how do I use this?" questions)

---

## Open Questions

### High Priority (Need Answers Before Implementation)

**Q1: LLM API Budget**
- **Question**: What's the budget for real API calls in CI/testing?
- **Impact**: Determines if we use real API calls or mocks in CI
- **Proposed**: $5/month for nightly integration tests
- **Decision Needed By**: Before FR-7.2 (integration tests)

**Q2: Embedding Model Default**
- **Question**: Which sentence-transformers model should be default?
- **Options**:
  - A) `all-MiniLM-L6-v2` (fast, 80 MB)
  - B) `all-mpnet-base-v2` (accurate, 420 MB)
- **Impact**: Download size on first run
- **Proposed**: A for CLI (speed), B for Python API (accuracy)
- **Decision Needed By**: Before FR-4.1 (memory indexing)

**Q3: Config File Location Precedence**
- **Question**: Should project-local config override user-global config?
- **Options**:
  - A) Project (`./aurora.config.json`) overrides user (`~/.aurora/config.json`)
  - B) User overrides project (safer default)
- **Impact**: Multi-user projects
- **Proposed**: A (project-specific settings make sense)
- **Decision Needed By**: Before FR-3.2 (config loading)

### Medium Priority (Can Defer Decision)

**Q4: Verbose Output Verbosity Levels**
- **Question**: Do we need multiple verbosity levels beyond `--verbose`?
- **Options**: `--verbose`, `--debug`, `-vv`, `-vvv`
- **Impact**: User control over output detail
- **Proposed**: Single `--verbose` for v1.1.0, expand later if needed

**Q5: Memory Store Eviction Strategy**
- **Question**: Should CLI implement memory eviction for large codebases?
- **Impact**: Disk usage for very large projects
- **Proposed**: No eviction in v1.1.0 (defer to TD-P2-005)

**Q6: Dry-Run Output Format**
- **Question**: Should dry-run output be JSON-formatted for scripting?
- **Options**: Human-readable text vs JSON vs both via flag
- **Proposed**: Human-readable default, `--format json` later

### Low Priority (Nice to Know)

**Q7: Headless Mode Testing Scope**
- **Question**: How extensive should headless mode testing be in v1.1.0?
- **Proposed**: Basic smoke test only (it worked in Phase 3)

**Q8: Migration Backward Compatibility**
- **Question**: Do we need downgrade migrations (v2→v1)?
- **Proposed**: No for v1.1.0 (forward-only migrations)

---

## Appendices

### A. Technical Debt Items

**TD-P1-001: Migration Logic Zero Test Coverage**
- Priority: P1 (High)
- Effort: M (2-3 days)
- Addressed in: FR-6.1, FR-6.3
- Location: `packages/core/src/aurora_core/store/migrations.py`

**TD-P2-001: LLM Client Initialization Error Paths Untested**
- Priority: P1 (High)
- Effort: S (6-8 hours)
- Addressed in: FR-6.2
- Location: `packages/reasoning/src/aurora_reasoning/llm_client.py`

### B. Effort Estimates

**Phase 1: Smoke Tests** - 2 hours
- FR-1.1: Memory validation - 30 min
- FR-1.2: SOAR validation - 30 min
- FR-1.3: LLM validation - 30 min
- FR-1.4: Test runner - 30 min

**Phase 2: CLI Execution** - 1-2 days
- FR-2.1: SOAR integration - 4-6 hours
- FR-2.2: Direct LLM integration - 2-3 hours
- FR-2.3: Response formatting - 2-3 hours
- FR-2.4: Verbose mode - 2-3 hours

**Phase 3: Configuration** - 4-6 hours
- FR-3.1: Config structure - 1 hour
- FR-3.2: Config loading - 2-3 hours
- FR-3.3: Init command - 2-3 hours
- FR-3.4: Env var override - 1 hour
- FR-3.5: Config validation - 1-2 hours

**Phase 4: Memory** - 2-4 hours
- FR-4.1: Index command - 2-3 hours
- FR-4.2: Search enhancement - 1-2 hours
- FR-4.3: Auto-index prompt - 1 hour
- FR-4.4: Memory stats - 1-2 hours

**Phase 5: Error Handling** - 4-6 hours
- FR-5.1: LLM errors - 2-3 hours
- FR-5.2: Config errors - 1-2 hours
- FR-5.3: Memory errors - 1-2 hours
- FR-5.4: Dry-run mode - 1-2 hours

**Phase 6: Technical Debt** - 2-3 days
- FR-6.1: Migration tests - 1-2 days
- FR-6.2: LLM error tests - 6-8 hours
- FR-6.3: Rollback tests - 4-6 hours

**Phase 7: Documentation** - 4-6 hours
- FR-7.1: CLI usage guide - 2-3 hours
- FR-7.2: Integration tests - 2-3 hours
- FR-7.3: Error catalog - 1-2 hours
- FR-7.4: README update - 1 hour

**Total Estimated Effort**: 5-7 days (individual contributor)

### C. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Smoke tests reveal core issues | Medium | High | Budget 1-2 extra days for fixes |
| API key management too complex | Low | Medium | Follow standard practices (env vars) |
| Memory indexing too slow | Medium | Medium | Show progress, optimize if needed |
| Migration tests uncover bugs | Low | High | Good! Fix before promoting to users |
| LLM API costs exceed budget | Low | Low | Use mocks in CI, real calls for validation |
| Integration tests flaky | Medium | Medium | Use retries, condition-based waiting |
| Config schema changes needed | Low | Low | Version config file, migrate old format |

### D. Release Checklist

**Pre-Release**:
- [ ] All functional requirements implemented
- [ ] All tests passing (unit + integration)
- [ ] Coverage targets met
- [ ] Documentation complete
- [ ] README updated
- [ ] CHANGELOG updated
- [ ] Version bumped to v1.1.0

**Release**:
- [ ] Tag release: `git tag v1.1.0`
- [ ] Build packages: `python -m build`
- [ ] Test installation on clean system
- [ ] Verify all CLI commands work
- [ ] Verify smoke tests pass

**Post-Release**:
- [ ] Announce in changelog
- [ ] Update documentation site
- [ ] Close related GitHub issues
- [ ] Update technical debt document
- [ ] Plan v1.2.0 features

---

## Document History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-12-24 | Initial PRD creation | Claude (Product Manager) |

---

**End of PRD**
