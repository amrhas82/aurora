# Implementation Tasks: AURORA Foundation & Infrastructure (Phase 1)

**Source PRD**: `/home/hamr/PycharmProjects/OneNote/smol/agi-problem/tasks/0002-prd-aurora-foundation.md`
**Version**: 1.1 (Detailed Sub-Tasks)
**Generated**: December 20, 2025
**Status**: Ready for Implementation

---

## Overview

This task list breaks down PRD 0002 (AURORA Foundation & Infrastructure) into actionable implementation tasks. Phase 1 establishes the foundational components required for Phase 2 (SOAR Pipeline) and Phase 3 (Advanced Memory).

**Key Deliverables**:
- Storage layer (SQLite + in-memory implementations)
- Python code parser using tree-sitter
- Context management interfaces
- Agent registry for discovery
- Configuration system with validation
- Comprehensive testing framework

---

## Relevant Files

### Core Package (`packages/core/`)
- `packages/core/pyproject.toml` - Core package configuration and dependencies
- `packages/core/src/aurora_core/__init__.py` - Package initialization and exports
- `packages/core/src/aurora_core/types.py` - Shared type definitions (ChunkID, Activation)
- `packages/core/src/aurora_core/exceptions.py` - Custom exception hierarchy

#### Storage Layer
- `packages/core/src/aurora_core/store/__init__.py` - Storage module exports
- `packages/core/src/aurora_core/store/base.py` - Abstract Store interface
- `packages/core/src/aurora_core/store/sqlite.py` - SQLite implementation
- `packages/core/src/aurora_core/store/memory.py` - In-memory implementation for testing
- `packages/core/src/aurora_core/store/schema.py` - Database schema definitions
- `packages/core/src/aurora_core/store/migrations.py` - Schema migration utilities

#### Chunk Types
- `packages/core/src/aurora_core/chunks/__init__.py` - Chunks module exports (exports Chunk, CodeChunk, ReasoningChunk)
- `packages/core/src/aurora_core/chunks/base.py` - Abstract Chunk base class with to_json/from_json/validate
- `packages/core/src/aurora_core/chunks/code_chunk.py` - CodeChunk implementation with full validation and serialization
- `packages/core/src/aurora_core/chunks/reasoning_chunk.py` - ReasoningChunk stub for Phase 2

#### Context Management
- `packages/core/src/aurora_core/context/__init__.py` - Context module exports (exports ContextProvider, CodeContextProvider)
- `packages/core/src/aurora_core/context/provider.py` - Abstract ContextProvider interface with retrieve/update/refresh methods
- `packages/core/src/aurora_core/context/code_provider.py` - CodeContextProvider with query parsing, chunk scoring, and retrieval logic

#### Configuration
- `packages/core/src/aurora_core/config/__init__.py` - Config module exports (Config, get_schema)
- `packages/core/src/aurora_core/config/loader.py` - Config class with typed access, override hierarchy, validation
- `packages/core/src/aurora_core/config/schema.py` - JSON Schema Draft 7 specification for configuration validation
- `packages/core/src/aurora_core/config/defaults.json` - Default configuration values (version 1.0)

### Context-Code Package (`packages/context-code/`)
- `packages/context-code/pyproject.toml` - Context-code package configuration with tree-sitter dependencies and hatchling build backend
- `packages/context-code/README.md` - Package documentation
- `packages/context-code/src/aurora_context_code/__init__.py` - Package initialization
- `packages/context-code/src/aurora_context_code/parser.py` - Abstract CodeParser interface with parse() and can_parse() methods
- `packages/context-code/src/aurora_context_code/registry.py` - ParserRegistry implementation with auto-registration
- `packages/context-code/src/aurora_context_code/languages/__init__.py` - Language parsers module
- `packages/context-code/src/aurora_context_code/languages/python.py` - PythonParser with function/class/method extraction, docstrings, complexity calculation

### SOAR Package (`packages/soar/`)
- `packages/soar/pyproject.toml` - SOAR package configuration with hatchling build backend
- `packages/soar/README.md` - Package documentation
- `packages/soar/src/aurora_soar/__init__.py` - Package initialization with AgentInfo and AgentRegistry exports
- `packages/soar/src/aurora_soar/agent_registry.py` - AgentInfo dataclass and AgentRegistry implementation with discovery, validation, and capability queries

### Testing Package (`packages/testing/`)
- `packages/testing/pyproject.toml` - Testing utilities package configuration with hatchling build backend
- `packages/testing/README.md` - Package documentation
- `packages/testing/src/aurora_testing/__init__.py` - Package initialization with fixtures, mocks, benchmarks exports
- `packages/testing/src/aurora_testing/fixtures.py` - Comprehensive pytest fixtures (stores, chunks, parsers, files, configs)
- `packages/testing/src/aurora_testing/mocks.py` - Mock implementations (MockLLM with rules, MockAgent, MockParser, MockStore)
- `packages/testing/src/aurora_testing/benchmarks.py` - Performance utilities (PerformanceBenchmark, MemoryProfiler, BenchmarkSuite)

### Test Files
- `tests/unit/core/test_store_base.py` - Store interface tests
- `tests/unit/core/test_store_sqlite.py` - SQLite store tests
- `tests/unit/core/test_store_memory.py` - Memory store tests
- `tests/unit/core/test_chunk_base.py` - Base chunk tests (15 tests, all passing)
- `tests/unit/core/test_chunk_code.py` - CodeChunk tests (31 tests, all passing)
- `tests/unit/core/test_chunk_store_integration.py` - Chunk-Store integration tests (13 tests, all passing)
- `tests/unit/core/test_context_provider.py` - Context provider tests (31 tests: 9 interface + 9 CodeContextProvider + 7 query parsing + 7 chunk scoring - all passing)
- `tests/unit/core/test_config_loader.py` - Configuration loader tests (23 tests: typed access, loading hierarchy, env vars, path expansion, validation, secrets - all passing)
- `tests/unit/context_code/test_parser_base.py` - Parser interface tests (10 tests, all passing)
- `tests/unit/context_code/test_python_parser.py` - Python parser tests (21 tests, all passing)
- `tests/unit/context_code/test_parser_registry.py` - Parser registry tests (23 tests, all passing)
- `tests/unit/soar/test_agent_registry.py` - Agent registry tests (29 tests, all passing, 86.49% coverage)
- `tests/integration/test_parse_and_store.py` - Parse → Store → Retrieve flow (33 tests: parse/store/retrieve, metadata preservation, multi-file, updates, persistence - all passing)
- `tests/integration/test_context_retrieval.py` - End-to-end context retrieval (10 tests: 7 flow tests + 3 edge cases - all passing)
- `tests/integration/test_config_integration.py` - Configuration integration (12 tests: full workflow, multi-file, env vars, CLI overrides, components - all passing)
- `tests/performance/test_parser_benchmarks.py` - Parser performance tests (27 tests: small/medium/large files, scaling, memory, cold start - all passing at ~420ms for 1000 lines)
- `tests/performance/test_storage_benchmarks.py` - Storage performance tests (12 tests: read/write, bulk ops, activation, relationships - all passing, meeting <50ms targets)
- `tests/fixtures/sample_python_files/simple.py` - Simple test file with 2 functions
- `tests/fixtures/sample_python_files/medium.py` - Medium complexity file with class and methods
- `tests/fixtures/sample_python_files/complex.py` - Complex file with nested classes and high complexity
- `tests/fixtures/sample_python_files/broken.py` - File with syntax errors for error handling tests
- `tests/fixtures/agents/agents.json` - Sample agent configuration with 3 agents (local/remote types, various capabilities)

### Root Files
- `pyproject.toml` - Root project configuration (workspace)
- `Makefile` - Common development commands
- `README.md` - Project documentation and quick start (updated with architecture diagrams and comprehensive usage examples)
- `.github/workflows/ci.yml` - CI/CD pipeline configuration
- `pytest.ini` - Pytest configuration
- `ruff.toml` - Ruff linting configuration
- `mypy.ini` - MyPy type checking configuration

### Documentation Files
- `docs/EXTENSION_GUIDE.md` - Guide for creating custom parsers, storage backends, context providers, and agents
- `docs/TROUBLESHOOTING.md` - Common errors and solutions for installation, storage, parsing, configuration, and performance issues
- `docs/PHASE2_CONTRACTS.md` - Stable interfaces and dependency contracts for Phase 2 developers
- `docs/PHASE2_MIGRATION_GUIDE.md` - Comprehensive migration guide for Phase 2 developers with integration examples

### Phase 1 Completion Reports
- `PHASE1_VERIFICATION_REPORT.md` - Complete functional requirements verification
- `QUALITY_GATES_REPORT.md` - Code quality, performance, and security verification
- `ACCEPTANCE_TEST_REPORT.md` - All acceptance test scenarios validation
- `MEMORY_PROFILING_REPORT.md` - Memory usage analysis (15.52 MB for 10K chunks)
- `DELIVERY_CHECKLIST.md` - PRD Section 11 delivery verification checklist (89% complete)
- `CODE_REVIEW_CHECKLIST.md` - Comprehensive code review checklist with automated verification and manual review sections
- `RELEASE_NOTES_v1.0.0-phase1.md` - Complete release notes with quality metrics, API guarantees, and migration guide
- `PHASE1_ARCHIVE.md` - Complete Phase 1 archive with deliverables, achievements, lessons learned, and Phase 2 handoff

---

## Notes

### Testing Strategy
- Unit tests isolate individual components using mocks and fixtures
- Integration tests verify cross-component interactions
- Performance benchmarks establish baselines for critical operations
- All tests use pytest framework with coverage tracking (target: ≥85%)

### Architectural Patterns
- Abstract interfaces defined before concrete implementations
- Dependency injection for testability (stores, parsers passed as arguments)
- Factory pattern for parser registry and store creation
- Builder pattern for complex chunk construction
- Strategy pattern for different storage backends

### Performance Considerations
- SQLite optimized with WAL mode, connection pooling
- Parser caching based on file mtime to avoid redundant parsing
- Lazy loading for configuration and agent discovery
- Memory profiling required for 10K chunk target

### Error Handling
- Custom exception hierarchy (AuroraError → StorageError, ParseError, ConfigError)
- Validation errors provide actionable messages with fix suggestions
- System errors use retry with exponential backoff
- Fatal errors fail fast with recovery instructions

---

## Tasks

- [x] 1.0 Project Foundation & Setup
  - [x] 1.1 Create monorepo package structure with base directories and __init__.py files
  - [x] 1.2 Create pyproject.toml for each package (core, context-code, soar, testing) with dependencies
  - [x] 1.3 Create root pyproject.toml with workspace configuration and development dependencies
  - [x] 1.4 Set up pytest configuration (pytest.ini) with coverage settings and test discovery
  - [x] 1.5 Configure code quality tools (ruff.toml, mypy.ini) with strict settings
  - [x] 1.6 Create Makefile with common commands (install, test, lint, format, benchmark)
  - [x] 1.7 Set up GitHub Actions CI/CD pipeline (.github/workflows/ci.yml) with test, lint, type-check jobs
  - [x] 1.8 Create README.md with project overview, quick start, and architecture documentation
  - [x] 1.9 Verify all packages install correctly and tests can be discovered (smoke test)

- [x] 2.0 Core Storage Layer Implementation
  - [x] 2.1 Define shared types in packages/core/src/aurora_core/types.py (ChunkID, Activation typehints)
  - [x] 2.2 Create custom exception hierarchy in packages/core/src/aurora_core/exceptions.py
  - [x] 2.3 Define abstract Store interface in packages/core/src/aurora_core/store/base.py with all required methods
  - [x] 2.4 Create database schema definitions in packages/core/src/aurora_core/store/schema.py (SQL CREATE statements)
  - [x] 2.5 Implement SQLiteStore in packages/core/src/aurora_core/store/sqlite.py with connection pooling
  - [x] 2.6 Add transaction support and error handling to SQLiteStore (rollback on failure)
  - [x] 2.7 Implement MemoryStore in packages/core/src/aurora_core/store/memory.py for testing
  - [x] 2.8 Create schema migration utilities in packages/core/src/aurora_core/store/migrations.py
  - [x] 2.9 Write unit tests for Store interface contract (tests/unit/core/test_store_base.py)
  - [x] 2.10 Write unit tests for SQLiteStore (tests/unit/core/test_store_sqlite.py) covering all methods
  - [x] 2.11 Write unit tests for MemoryStore (tests/unit/core/test_store_memory.py)
  - [x] 2.12 Create performance benchmarks for storage operations (tests/performance/test_storage_benchmarks.py)
  - [x] 2.13 Verify storage performance targets met (write/read <50ms, cold start <200ms)

- [x] 3.0 Chunk Types & Validation
  - [x] 3.1 Define abstract Chunk base class in packages/core/src/aurora_core/chunks/base.py with to_json/from_json
  - [x] 3.2 Implement CodeChunk in packages/core/src/aurora_core/chunks/code_chunk.py with all required fields
  - [x] 3.3 Add JSON serialization methods to CodeChunk following PRD schema (Section 4.2.2)
  - [x] 3.4 Implement validation logic in CodeChunk (line numbers, file paths, complexity range)
  - [x] 3.5 Create ReasoningChunk stub in packages/core/src/aurora_core/chunks/reasoning_chunk.py for Phase 2
  - [x] 3.6 Write unit tests for abstract Chunk interface (tests/unit/core/test_chunk_base.py)
  - [x] 3.7 Write unit tests for CodeChunk (tests/unit/core/test_chunk_code.py) covering serialization and validation
  - [x] 3.8 Test edge cases (invalid line numbers, malformed paths, out-of-range complexity)
  - [x] 3.9 Verify chunks integrate with Store (save/retrieve round-trip test)

- [x] 4.0 Code Context Provider (Python Parser)
  - [x] 4.1 Define abstract CodeParser interface in packages/context-code/src/aurora_context_code/parser.py
  - [x] 4.2 Set up tree-sitter dependency and Python grammar in context-code package
  - [x] 4.3 Implement PythonParser skeleton in packages/context-code/src/aurora_context_code/languages/python.py
  - [x] 4.4 Add function extraction logic to PythonParser (name, signature, line range)
  - [x] 4.5 Add class and method extraction logic to PythonParser (handle nested structures)
  - [x] 4.6 Add docstring extraction (first string literal after definition node)
  - [x] 4.7 Implement cyclomatic complexity calculation (count if/for/while/try branch points)
  - [x] 4.8 Add dependency identification (imports and function call extraction)
  - [x] 4.9 Implement error handling for parse failures (log and return empty list, don't crash)
  - [x] 4.10 Create ParserRegistry in packages/context-code/src/aurora_context_code/registry.py
  - [x] 4.11 Add auto-registration for PythonParser in registry on module import
  - [x] 4.12 Create sample Python test files in tests/fixtures/sample_python_files/ (simple, medium, complex, broken)
  - [x] 4.13 Write unit tests for CodeParser interface (tests/unit/context_code/test_parser_base.py)
  - [x] 4.14 Write unit tests for PythonParser (tests/unit/context_code/test_python_parser.py) covering all extraction features
  - [x] 4.15 Write unit tests for ParserRegistry (tests/unit/context_code/test_parser_registry.py) with multi-language mock
  - [x] 4.16 Create performance benchmarks for parser (tests/performance/test_parser_benchmarks.py)
  - [x] 4.17 Verify parser performance target (<200ms for 1000-line file) and optimize if needed

- [x] 5.0 Context Management & Retrieval
  - [x] 5.1 Define abstract ContextProvider interface in packages/core/src/aurora_core/context/provider.py
  - [x] 5.2 Implement CodeContextProvider skeleton in packages/core/src/aurora_core/context/code_provider.py
  - [x] 5.3 Add keyword-based query parsing (lowercase, split on whitespace, remove stopwords)
  - [x] 5.4 Implement chunk scoring algorithm (keyword_matches / total_keywords)
  - [x] 5.5 Add retrieval logic with ranking (retrieve from store, score, sort, return top N)
  - [x] 5.6 Implement caching strategy (check file mtime, invalidate if modified)
  - [x] 5.7 Add update() method to track usage and update activation timestamps
  - [x] 5.8 Integrate CodeContextProvider with Store and ParserRegistry
  - [x] 5.9 Write unit tests for ContextProvider interface (tests/unit/core/test_context_provider.py)
  - [x] 5.10 Write integration tests for context retrieval flow (tests/integration/test_context_retrieval.py)
  - [x] 5.11 Test caching behavior (verify cache hit/miss, invalidation on file change)
  - [x] 5.12 Verify retrieval returns relevant results for sample queries

- [x] 6.0 Agent Registry & Discovery
  - [x] 6.1 Define AgentInfo dataclass in packages/soar/src/aurora_soar/agent_registry.py
  - [x] 6.2 Implement AgentRegistry class with discovery paths and agent storage
  - [x] 6.3 Add JSON parsing for agent configuration files (validate schema, handle errors)
  - [x] 6.4 Implement agent validation (required fields, valid types, path/endpoint checks)
  - [x] 6.5 Add capability-based query methods (find_by_capability, filter by domain)
  - [x] 6.6 Implement fallback agent creation (default llm-executor if no agents found)
  - [x] 6.7 Add refresh() method to re-scan config files (check mtime for changes)
  - [x] 6.8 Create sample agent configuration files for testing (tests/fixtures/agents.json)
  - [x] 6.9 Write unit tests for AgentRegistry (tests/unit/soar/test_agent_registry.py)
  - [x] 6.10 Test discovery from multiple config paths (project, global, MCP)
  - [x] 6.11 Test validation catches invalid agent configurations
  - [x] 6.12 Verify capability queries return correct agents

- [x] 7.0 Configuration System
  - [x] 7.1 Define JSON schema for configuration in packages/core/src/aurora_core/config/schema.py
  - [x] 7.2 Create default configuration in packages/core/src/aurora_core/config/defaults.json
  - [x] 7.3 Implement Config class in packages/core/src/aurora_core/config/loader.py with typed access methods
  - [x] 7.4 Add configuration loading with override hierarchy (defaults → global → project → env → CLI)
  - [x] 7.5 Implement environment variable mapping (AURORA_* variables to config keys)
  - [x] 7.6 Add path expansion (tilde to home directory, relative to absolute)
  - [x] 7.7 Implement validation against JSON schema (raise ConfigurationError with clear messages)
  - [x] 7.8 Add secrets handling (API keys from environment only, never from files)
  - [x] 7.9 Write unit tests for ConfigLoader (tests/unit/core/test_config_loader.py)
  - [x] 7.10 Test override hierarchy (verify correct precedence order)
  - [x] 7.11 Test environment variable overrides work correctly
  - [x] 7.12 Test validation catches invalid configurations
  - [x] 7.13 Create integration tests for config system (tests/integration/test_config_integration.py)

- [x] 8.0 Testing Framework & Utilities
  - [x] 8.1 Create pytest fixtures in packages/testing/src/aurora_testing/fixtures.py (stores, chunks, parsers)
  - [x] 8.2 Implement MockLLM in packages/testing/src/aurora_testing/mocks.py for predictable testing
  - [x] 8.3 Create PerformanceBenchmark utility in packages/testing/src/aurora_testing/benchmarks.py
  - [x] 8.4 Add memory profiling utilities for tracking memory usage in tests
  - [x] 8.5 Write integration test for parse → store → retrieve flow (tests/integration/test_parse_and_store.py)
  - [x] 8.6 Create integration test for full context retrieval (tests/integration/test_context_retrieval.py)
  - [x] 8.7 Verify all unit tests pass with ≥85% coverage for core packages
  - [x] 8.8 Verify all integration tests pass
  - [x] 8.9 Verify all performance benchmarks meet targets

- [x] 9.0 Documentation & Quality Assurance
  - [x] 9.1 Add docstrings to all public classes and methods (following Google style)
  - [x] 9.2 Run mypy in strict mode and fix all type errors
  - [x] 9.3 Run ruff linting and fix all critical issues (warnings acceptable if documented)
  - [x] 9.4 Run bandit security scanning and address high/critical vulnerabilities
  - [x] 9.5 Generate test coverage report and address gaps below 85%
  - [x] 9.6 Update README.md with architecture diagrams and usage examples
  - [x] 9.7 Create extension guide for custom parsers and storage backends
  - [x] 9.8 Create troubleshooting guide for common errors
  - [x] 9.9 Document inter-phase dependency contracts for Phase 2 developers
  - [x] 9.10 Run full test suite and verify completion in <5 minutes

- [x] 10.0 Phase 1 Completion & Handoff
  - [x] 10.1 Verify all functional requirements from PRD Section 4 are implemented
  - [x] 10.2 Verify all quality gates from PRD Section 6.1 pass
  - [x] 10.3 Verify all acceptance test scenarios from PRD Section 6.3 pass
  - [x] 10.4 Run memory profiling and verify <100MB for 10K cached chunks
  - [x] 10.5 Complete delivery verification checklist from PRD Section 11
  - [x] 10.6 Tag release as v1.0.0-phase1 with release notes
  - [x] 10.7 Document Phase 2 dependencies and stable interface contracts
  - [x] 10.8 Conduct code review with 2+ reviewers
  - [x] 10.9 Create migration guide for Phase 2 developers
  - [x] 10.10 Archive Phase 1 deliverables and update project documentation

---

## Implementation Order & Dependencies

**Critical Path** (must be done in order):
1. **1.0 Project Setup** → Foundation for all other work
2. **7.0 Configuration** → Required by most components
3. **2.0 Storage** + **3.0 Chunks** → Can be done in parallel, both needed for 4.0
4. **4.0 Parser** → Depends on 3.0 (Chunks)
5. **5.0 Context Management** → Depends on 2.0, 3.0, 4.0
6. **6.0 Agent Registry** → Depends on 7.0 (Config)
7. **8.0 Testing Framework** → Can be built incrementally alongside features
8. **9.0 Documentation** → Done continuously, finalized at end
9. **10.0 Completion** → Final verification and handoff

**Parallelization Opportunities**:
- After 1.0 complete: Start 2.0, 3.0, and 7.0 in parallel
- After 3.0 complete: Start 4.0 while continuing 2.0
- 6.0 can be built while 5.0 is in progress (different dependencies)
- 8.0 fixtures can be created as needed for each component

---

## Time Estimates

**Total Estimated Time**: 85-120 hours

| Task | Subtasks | Est. Hours | Complexity |
|------|----------|------------|------------|
| 1.0 Project Setup | 9 | 8-12 | Medium |
| 2.0 Storage Layer | 13 | 16-22 | Complex |
| 3.0 Chunk Types | 9 | 10-14 | Medium |
| 4.0 Python Parser | 17 | 20-28 | Complex |
| 5.0 Context Management | 12 | 12-16 | Medium |
| 6.0 Agent Registry | 12 | 10-14 | Medium |
| 7.0 Configuration | 13 | 12-16 | Medium |
| 8.0 Testing Framework | 9 | 10-14 | Medium |
| 9.0 Documentation | 10 | 8-12 | Simple |
| 10.0 Completion | 10 | 6-10 | Simple |

---

## Success Criteria

Phase 1 is **COMPLETE** when:
- ✅ All 10 parent tasks and their sub-tasks completed
- ✅ All functional requirements from PRD Section 4 implemented
- ✅ All quality gates from PRD Section 6.1 passed
- ✅ All acceptance tests from PRD Section 6.3 passing
- ✅ Performance benchmarks meet targets (Section 2.2)
- ✅ Code coverage ≥85% for core packages
- ✅ Documentation complete and reviewed
- ✅ Delivery verification checklist (PRD Section 11) signed off
- ✅ Phase 2 dependency contracts documented

---

## Next Steps

**Implementation Workflow**:
1. Review this task list with the team
2. Start with Task 1.0 (Project Foundation & Setup)
3. Work through tasks sequentially following dependency order
4. Use the testing package fixtures as you build each component
5. Update this checklist as tasks are completed
6. Conduct milestone reviews after major tasks (2.0, 4.0, 5.0)
7. Final review and handoff at Task 10.0

**For Task Execution**:
- Each sub-task should take 2-4 hours for a junior developer
- Mark sub-tasks complete only when tests pass and code is reviewed
- Update documentation as you implement each component
- Run quality checks (mypy, ruff, bandit) frequently
- Track performance metrics throughout development

---

**END OF DETAILED TASK LIST**
