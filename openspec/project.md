# Project Context

## Purpose

**Aurora** is an Adaptive Unified Reasoning and Orchestration Architecture - a cognitive framework for AI systems with persistent memory, reasoning, and multi-agent orchestration. Aurora enables:

- **Persistent Memory**: Semantic chunking, activation scoring, hybrid retrieval (BM25 + embedding-based)
- **Intelligent Reasoning**: LLM-powered analysis with configurable backends (Anthropic, OpenAI, Ollama)
- **Agent Orchestration**: 9-phase SOAR pipeline for complex task decomposition and delegation
- **Planning System**: Native plan creation, decomposition, and multi-tool integration (Claude Code, OpenCode, AmpCode, Droid)

**Strategic Vision**: Aurora v0.2.0 is the foundation for AI-augmented software development, enabling agents to understand codebases, reason about architecture, and execute complex development tasks.

## Tech Stack

**Core Framework**:
- Python 3.12+ (strict type hints, mypy required)
- Pydantic v2+ (schema validation, JSON serialization)
- Tree-sitter (code parsing, Python-only currently)

**Storage & Retrieval**:
- SQLite (chunk storage, metadata)
- Numpy (embeddings, similarity computation)
- BM25 (term-based retrieval, hybrid hybrid search)

**LLM Integration**:
- Anthropic Claude (primary)
- OpenAI (fallback)
- Ollama (local models)

**Planning & Orchestration**:
- Jinja2 (template rendering)
- python-slugify (URL-safe ID generation)
- OpenSpec (planning infrastructure, 284 passing tests)

**CLI & MCP**:
- Click/Typer (CLI framework)
- Model Context Protocol (MCP) for tool integration
- JSON for config/metadata formats

**Development Tools**:
- pytest (testing, 2,369 tests at 97% pass rate)
- mypy (strict type checking, 0 errors required)
- ruff (linting, code formatting)
- Coverage.py (test coverage reporting)

## Project Conventions

### Code Style

**Python Standards**:
- Type hints mandatory (no `Any` except where documented)
- mypy strict mode enforced (0 errors)
- ruff formatting rules applied
- Docstrings for all public functions/classes (Google style)
- Variable naming: snake_case (functions, variables), PascalCase (classes)
- Constants: UPPER_SNAKE_CASE

**Import Organization**:
- Standard library → Third-party → Aurora packages
- Namespace packages: `from aurora.core import ...` (not `from aurora_core`)
- Circular imports must be avoided (dependency injection pattern)

**Error Handling**:
- Custom exceptions inherit from `AuroraException`
- Structured error codes: `ERROR_CATEGORY_DESCRIPTION` (e.g., `PLANNING_INIT_FAILED`)
- Error messages include: code, description, recovery suggestion
- No silent failures; always log at appropriate level

### Architecture Patterns

**Package Structure**:
- Modular packages: `aurora.core`, `aurora.soar`, `aurora.planning`, `aurora.cli`
- Namespace packages: `packages/*/src/aurora_*/` structure
- Clear separation of concerns: services, schemas, commands, templates

**9-Phase SOAR Orchestration**:
1. **Assess**: Analyze request, determine complexity
2. **Retrieve**: Fetch relevant context via memory system
3. **Decompose**: Break into subgoals (rule-based or AI-powered)
4. **Verify**: Validate decomposition against constraints
5. **Route**: Dispatch to appropriate agents/tools
6. **Collect**: Gather results and metrics
7. **Synthesize**: Combine outputs into coherent response
8. **Record**: Store learnings in memory (future)
9. **Respond**: Format and return to user

**Activation Scoring**:
- Hybrid approach: 60% semantic similarity + 40% frequency/recency
- Context boost for project-specific terms
- Performance target: <2s for simple queries, <10s for complex

**Planning Architecture** (Phase 1+):
- Plan ID format: `NNNN-slug` (sequential + human-readable)
- Four-file workflow: `plan.md`, `prd.md`, `tasks.md`, `agents.json`
- Directory structure: `~/.aurora/plans/active/` and `~/.aurora/plans/archive/`
- Phase 2: SOAR-powered decomposition + memory integration
- Phase 3: Execution orchestration with agent delegation

### Testing Strategy

**Test Coverage**: ≥95% for all packages (current: 81.06% overall, 2,369 tests)

**Test Organization**:
- `tests/unit/` - Unit tests for individual modules (fast, isolated)
- `tests/integration/` - Integration tests for workflows (moderate, with fixtures)
- `tests/e2e/` (future) - End-to-end tests for real scenarios

**Testing Approach**:
- Pytest with fixtures for common setup
- Parameterized tests for multiple scenarios
- Mocking for external services (LLMs, external APIs)
- No test-only code in production (design for testability)

**Critical Test Marks**:
- `@pytest.mark.critical` - Must pass before merge
- Some external API tests skipped (14 currently documented)
- Mypy compatibility issues in llm_client.py (tracked, non-blocking)

**TDD Requirement** (Phase 1 Planning):
- Write tests first
- Watch them fail
- Write minimal code to pass
- All implementations verified with shell command output

### Git Workflow

**Branching Strategy**:
- Main branch: `main` (stable, all tests passing)
- Feature branches: `feature/description` (short-lived)
- No force pushes to main
- All changes require passing CI (tests, type checks, linting)

**Commit Conventions**:
```
type(scope): short description

Longer explanation if needed.
Include issue numbers: Closes #123

🤖 Generated with [Claude Code](https://claude.com/claude-code)
Co-Authored-By: Claude <model-id> <noreply@anthropic.com>
```

**Types**: feat, fix, docs, style, refactor, test, chore, ci

## Domain Context

### Core Concepts

**Chunks**: Semantic units of code (functions, classes, blocks) stored with metadata:
- Content hash for change detection
- Activation score for retrieval ranking
- Frequency/recency tracking
- Vector embedding for semantic search

**Activation Scoring**: ACT-R inspired approach combining:
- Base-level activation (frequency + recency)
- Associative activation (context similarity)
- Semantic boost (vector embedding distance)
- Context boost (project-specific relevance)

**Planning Domain**:
- Plans decompose goals into subgoals
- Subgoals map to agents with capabilities
- Tasks are actionable items with estimated effort
- Plans progress through: draft → active → archived

**Agent Capabilities**:
- Text analysis, code understanding, architecture review
- Task decomposition, requirement specification
- Code generation, refactoring, optimization
- Testing, validation, deployment

### Problem Space

**User Challenges**:
- Codebases difficult to navigate (thousands of files, complex structure)
- AI assistants lack persistent context across conversations
- Complex tasks require manual decomposition and tracking
- Tool switching interrupts workflow

**Aurora Solutions**:
- Semantic memory indexes codebase intelligently
- SOAR pipeline decomposes complex work automatically
- Persistent plans track multi-phase work
- Integrated CLI + slash commands keep users in flow

## Important Constraints

**Performance**:
- Memory overhead: <100MB for 10K chunks
- Query time: <2s simple, <10s complex (aspirational)
- Chunk processing: milliseconds per file
- API costs: Track and minimize LLM tokens

**Compatibility**:
- Python 3.12+ only (no 3.11 support)
- Namespace packages complicate imports (requires proper setup)
- Tree-sitter only supports Python code parsing (other languages planned)
- Windows path handling (if supporting Windows)

**Quality Gates**:
- Test coverage: ≥95% (hard stop at PR merge)
- Type checking: 0 errors in mypy strict mode
- Linting: 0 violations (ruff)
- Documentation: All public APIs documented

**Token Budget**:
- API costs tracked in `~/.aurora/budget_tracker.json`
- Environment variables for API keys (never hardcoded)
- Anthropic backend is primary (cost-effective)

## External Dependencies

### LLM APIs

**Anthropic Claude**:
- Endpoint: `api.anthropic.com`
- Models: Claude 3.5 Sonnet, Opus, Haiku
- Cost tracking via `budget_tracker.json`
- Environment: `ANTHROPIC_API_KEY`

**OpenAI** (Fallback):
- Endpoint: `api.openai.com`
- Model: GPT-4 (fallback for Anthropic)
- Environment: `OPENAI_API_KEY`

**Ollama** (Local):
- Endpoint: `http://localhost:11434`
- Models: Any supported by Ollama
- Zero cost, for development/testing

### Tool Integration

**Claude Code** (Primary):
- MCP server integration
- Slash commands: `/aur:plan`, `/aur:list`, `/aur:view`, `/aur:archive`
- Config: `~/.config/Claude/claude_desktop_config.json` (Linux)

**OpenCode, AmpCode, Droid**:
- Tool-specific config paths (research needed for exact locations)
- Same slash command set as Claude Code
- Configs generated by `aur plan init`

### OpenSpec (Integrated)

**Source**: `/tmp/openspec-source/aurora/` (284 tests)
**Status**: Refactored, awaiting Phase 1 integration
**Content**: Planning commands, validators, schemas, templates, configurators
**Integration**: Migrate to `packages/planning/src/aurora_planning/` in Phase 1

### File System Conventions

**User Home**:
- `~/.aurora/` - Aurora home directory
- `~/.aurora/plans/` - Planning root
- `~/.aurora/plans/active/` - Active plans
- `~/.aurora/plans/archive/` - Archived plans (with timestamps)
- `~/.aurora/config.json` - Aurora configuration
- `~/.aurora/budget_tracker.json` - LLM token budget tracking

**Project Root**:
- `/openspec/` - Planning specifications (OpenSpec format)
- `/openspec/AGENTS.md` - AI assistant instructions
- `/openspec/project.md` - Project context (this file)
- `/openspec/specs/` - Capability specifications
- `/openspec/changes/` - Active proposals and deployed changes
- `/packages/` - Namespace packages (core, soar, planning, cli, testing, context-code)
- `/docs/` - User and developer documentation
- `/tests/` - Test suite (2,369 tests)

## Quick Reference

**Commands**:
- `aur --verify` - Check installation health
- `aur mem index .` - Index codebase
- `aur mem search "query"` - Semantic search
- `aur query "question"` - Query with context
- `aur agents list` - List available agents
- `aur plan init` - Initialize planning
- `aur plan create "goal"` - Create new plan

**Key Files**:
- Main package: `packages/*/src/aurora_*/`
- Tests: `tests/unit/`, `tests/integration/`
- Docs: `docs/KNOWLEDGE_BASE.md`, `docs/README.md`
- Config: `~/.claude/CLAUDE.md` (global), `./CLAUDE.md` (project)
