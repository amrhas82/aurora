# PRD: AURORA MCP Query Tool - Full Framework Integration

**Document ID**: tasks-0007-prd-mcp-aurora-query-full-integration
**Version**: 1.0
**Status**: Draft
**Created**: 2025-12-25
**Author**: Senior Software Engineer (AI Agent)
**Target Sprint**: Medium (3-5 days)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Goals & Non-Goals](#goals--non-goals)
3. [User Stories & Use Cases](#user-stories--use-cases)
4. [Functional Requirements](#functional-requirements)
5. [Technical Requirements](#technical-requirements)
6. [API Specification](#api-specification)
7. [Error Handling & User Experience](#error-handling--user-experience)
8. [Testing Strategy](#testing-strategy)
9. [Success Metrics](#success-metrics)
10. [Implementation Plan](#implementation-plan)
11. [Tech Debt Consideration](#tech-debt-consideration)
12. [Open Questions](#open-questions)

---

## Executive Summary

### Problem Statement

AURORA's MCP (Model Context Protocol) integration currently provides 5 tools for code indexing and search (`aurora_search`, `aurora_index`, `aurora_stats`, `aurora_context`, `aurora_related`), but is missing the **core reasoning and orchestration capability** that defines AURORA's value proposition: the `aurora_query` tool.

Users who install AURORA through Claude Desktop MCP integration can index and search their codebase, but cannot execute the full 9-phase SOAR pipeline for complex queries, nor can they access the direct LLM interface with memory-augmented context. This creates a fundamental gap between CLI functionality and MCP functionality.

### Solution Overview

Add the `aurora_query` MCP tool that mirrors the CLI's `aur query` and `aur "question"` commands, providing:

1. **Direct LLM execution** for simple queries (fast mode)
2. **Full SOAR pipeline execution** for complex queries (deep reasoning)
3. **Auto-escalation logic** that automatically chooses the appropriate execution path
4. **Progress visibility** showing declarative steps as the query executes
5. **Helpful error messages** that guide users to fix configuration or API issues

This completes the MCP integration, making AURORA fully functional through Claude Desktop without requiring CLI usage for core features.

### Success Criteria

1. **Functional Completeness**: All CLI core features available via MCP (query, memory, indexing)
2. **Seamless Integration**: Works from Claude Desktop without additional configuration beyond MCP setup
3. **Error Quality**: Error messages are friendly, self-descriptive, and point users to solutions
4. **CI/CD Compliance**: All new code passes existing CI/CD quality gates (tests, type-checking, linting)
5. **User Adoption**: Primary interface becomes MCP > CLI > Web (as stated in user requirements)

---

## Goals & Non-Goals

### In Scope (Goals)

1. **MCP Tool Implementation**
   - Add `aurora_query` tool to `AuroraMCPTools` class
   - Register tool in `AuroraMCPServer` with FastMCP
   - Implement direct LLM and SOAR pipeline execution paths
   - Add auto-escalation logic (simple vs complex query detection)

2. **Progress Visibility**
   - Show declarative steps during SOAR pipeline execution
   - Display current phase (Assess → Retrieve → Decompose → ...)
   - Respect user's CLI verbosity configuration
   - Provide timing and cost information in verbose mode

3. **Error Handling**
   - Friendly, non-technical error messages
   - Self-descriptive errors that tell users what's wrong
   - Guidance on how to fix issues (missing API key, broken phase, etc.)
   - Match CLI error quality standards

4. **Configuration Integration**
   - Read existing CLI configuration from `~/.aurora/config.json`
   - Support API key from environment variables or config file
   - Respect user's verbosity, model, and temperature settings
   - No additional MCP-specific configuration required

5. **Testing & Quality**
   - TDD approach with tests written first
   - Unit tests for `aurora_query` tool
   - Integration tests with QueryExecutor
   - CI/CD compliance (all tests pass, type-checking, linting)

6. **Documentation**
   - Update MCP_SETUP.md with `aurora_query` usage
   - Add examples to TROUBLESHOOTING.md
   - Update README.md to reflect complete MCP functionality

### Out of Scope (Non-Goals)

1. **CLI Configuration Interface**: Advanced configuration remains in CLI and manual JSON editing (not needed in MCP)
2. **Web Interface**: Web UI is lower priority than MCP
3. **Streaming Responses**: Real-time token streaming (future enhancement)
4. **Multi-turn Conversations**: Maintaining context across multiple queries (future enhancement)
5. **Custom Plugin Integration**: Beyond existing MCP tools (future enhancement)
6. **Fine-tuning or Model Training**: Not a query tool responsibility
7. **Web Search Integration**: Out of scope for this PRD
8. **Image/Multimodal Input**: Text-only queries for now

---

## User Stories & Use Cases

### Primary User Personas

**Persona 1: Developer Using Claude Desktop**
- Installed AURORA via MCP integration
- Wants to query codebase with AI reasoning
- Expects seamless experience without switching to CLI
- Values error messages that help self-diagnose issues

**Persona 2: Power User Optimizing Costs**
- Uses AURORA for complex architectural questions
- Wants auto-escalation to avoid unnecessary SOAR costs
- Needs visibility into which execution path was chosen
- Monitors cost and token usage

**Persona 3: Team Lead Evaluating AURORA**
- Testing AURORA's reasoning capabilities
- Compares MCP vs CLI functionality
- Expects feature parity between interfaces
- Values clear documentation and examples

### User Stories (Prioritized)

**Priority 1 (Critical - Must Have)**

1. **US-1.1**: As a developer, I want to query my indexed codebase using `aurora_query` from Claude Desktop so that I get context-aware answers without switching to CLI.
   - **Acceptance Criteria**:
     - `aurora_query` tool is available in Claude Desktop after MCP setup
     - Tool accepts a query string parameter
     - Returns a response string with the answer
     - Uses indexed memory if available
   - **Testing**: Unit test, integration test with mock store, end-to-end test with real query

2. **US-1.2**: As a user, I want AURORA to automatically choose between simple LLM and SOAR pipeline based on query complexity so that I don't waste time/money on simple questions.
   - **Acceptance Criteria**:
     - Simple queries ("What is X?", "Define Y") use direct LLM
     - Complex queries ("Analyze architecture", "Compare approaches") use SOAR
     - Auto-escalation logic matches CLI behavior
     - Response metadata indicates which path was used
   - **Testing**: Unit tests for complexity detection, integration tests for both paths

3. **US-1.3**: As a user, I want to see declarative progress steps during SOAR execution so that I understand what AURORA is doing and can estimate completion time.
   - **Acceptance Criteria**:
     - Each SOAR phase displays status as it executes (e.g., "Assessing query complexity...", "Retrieving context...")
     - Progress updates match CLI verbose mode output
     - Final response includes phase summary in verbose mode
     - Non-verbose mode shows minimal progress (just start/end)
   - **Testing**: Integration test with verbose flag, verify output format

4. **US-1.4**: As a user, I want helpful error messages when something goes wrong so that I can fix the issue myself without needing expert support.
   - **Acceptance Criteria**:
     - Missing API key → "API key not found. Set ANTHROPIC_API_KEY environment variable or add to ~/.aurora/config.json"
     - Budget exceeded → "Monthly budget limit reached ($X/$Y). Increase limit in config or wait until next month."
     - SOAR phase failure → "Phase [name] failed: [reason]. This may indicate [possible cause]. Try [suggested fix]."
     - All errors include actionable guidance
   - **Testing**: Unit tests for each error condition, verify error message content

**Priority 2 (Important - Should Have)**

5. **US-2.1**: As a power user, I want to force SOAR pipeline execution for deep analysis so that I can bypass auto-escalation when I know I need complex reasoning.
   - **Acceptance Criteria**:
     - `force_soar` boolean parameter (default: false)
     - When true, skips complexity assessment and uses SOAR
     - Response metadata indicates forced execution
   - **Testing**: Integration test with force_soar=true

6. **US-2.2**: As a developer, I want to see cost and timing information for my queries so that I can optimize my usage and stay within budget.
   - **Acceptance Criteria**:
     - Response includes cost breakdown (input tokens, output tokens, total $)
     - Response includes timing (total duration, per-phase duration in verbose mode)
     - Cost respects user's CLI budget configuration
   - **Testing**: Integration test verifying cost calculation accuracy

7. **US-2.3**: As a user, I want to control response verbosity so that I can get detailed traces for debugging or concise answers for quick questions.
   - **Acceptance Criteria**:
     - `verbose` boolean parameter (default: reads from CLI config)
     - Verbose=true returns phase trace, timing, cost
     - Verbose=false returns minimal response (just answer)
   - **Testing**: Unit tests for both verbosity modes

**Priority 3 (Nice to Have - Could Have)**

8. **US-3.1**: As a developer, I want to override LLM model and temperature for specific queries so that I can experiment with different configurations.
   - **Acceptance Criteria**:
     - Optional `model` parameter (e.g., "claude-sonnet-4-20250514")
     - Optional `temperature` parameter (0.0-1.0)
     - Defaults to CLI config if not specified
   - **Testing**: Integration test with custom model/temperature

9. **US-3.2**: As a user, I want to see which indexed files/chunks were used to answer my query so that I can verify the answer's context.
   - **Acceptance Criteria**:
     - Response includes `sources` field (list of file paths and chunk IDs)
     - Each source includes relevance score
     - Only populated when memory was used
   - **Testing**: Integration test verifying source tracking

---

## Functional Requirements

### FR-1: Core Query Execution

**FR-1.1**: The system MUST provide an `aurora_query` MCP tool that accepts a query string and returns a response.

**FR-1.2**: The system MUST support two execution paths:
- **Direct LLM**: Fast execution (<2s typical) for simple queries
- **SOAR Pipeline**: Deep reasoning (<10s typical) for complex queries

**FR-1.3**: The system MUST automatically detect query complexity and choose the appropriate execution path unless overridden by `force_soar` parameter.

**FR-1.4**: The system MUST integrate with the existing `QueryExecutor` class from `aurora_cli.execution` to avoid code duplication.

### FR-2: Configuration Management

**FR-2.1**: The system MUST read API key from:
1. `ANTHROPIC_API_KEY` environment variable (highest priority)
2. `~/.aurora/config.json` file under `api.anthropic_key` field
3. Return error if neither is found

**FR-2.2**: The system MUST read default model, temperature, and verbosity settings from `~/.aurora/config.json`.

**FR-2.3**: The system MUST respect user's budget configuration from `~/.aurora/budget_tracker.json`.

**FR-2.4**: The system MUST NOT require additional MCP-specific configuration beyond standard AURORA setup.

### FR-3: Progress Visibility

**FR-3.1**: The system MUST display declarative status messages during SOAR pipeline execution:
- "Assessing query complexity..."
- "Retrieving relevant context from memory..."
- "Decomposing query into subgoals..."
- "Verifying context quality..."
- "Routing subgoals to agents..."
- "Collecting agent responses..."
- "Synthesizing final answer..."
- "Recording patterns in memory..."
- "Formatting response..."

**FR-3.2**: The system MUST adjust progress detail based on verbosity setting:
- **Verbose**: Show all 9 phases with timing and detail
- **Normal**: Show high-level progress (3-4 steps)
- **Quiet**: No progress, just final result

**FR-3.3**: The system MUST display progress in a format compatible with Claude Desktop's MCP response streaming (if supported by FastMCP).

### FR-4: Response Format

**FR-4.1**: The system MUST return responses as JSON with the following structure:

```json
{
  "answer": "The response text...",
  "execution_path": "direct_llm" | "soar_pipeline",
  "metadata": {
    "duration_seconds": 2.34,
    "cost_usd": 0.0045,
    "input_tokens": 1234,
    "output_tokens": 567,
    "model": "claude-sonnet-4-20250514",
    "temperature": 0.7
  },
  "phases": [  // Only if verbose=true and execution_path=soar_pipeline
    {
      "name": "Assess",
      "duration_seconds": 0.12,
      "summary": "Complexity: high"
    },
    // ... other phases
  ],
  "sources": [  // Only if memory was used
    {
      "file_path": "/path/to/file.py",
      "chunk_id": "code:file:function",
      "score": 0.87
    }
  ]
}
```

**FR-4.2**: The system MUST return error responses in a consistent JSON format:

```json
{
  "error": {
    "type": "APIKeyMissing" | "BudgetExceeded" | "SOARPhaseFailed" | "InvalidParameter",
    "message": "Human-readable error description",
    "suggestion": "Actionable fix suggestion",
    "details": {
      // Additional context (optional)
    }
  }
}
```

### FR-5: Error Handling

**FR-5.1**: The system MUST validate input parameters before execution:
- `query` must be non-empty string
- `model` (if provided) must be a valid Anthropic model ID
- `temperature` (if provided) must be between 0.0 and 1.0
- `max_tokens` (if provided) must be positive integer

**FR-5.2**: The system MUST handle missing API key with error:
```
Error: API key not found.

To fix this:
1. Set environment variable: export ANTHROPIC_API_KEY="your-key"
2. Or add to config: ~/.aurora/config.json under "api.anthropic_key"

See docs/TROUBLESHOOTING.md for more details.
```

**FR-5.3**: The system MUST handle budget exceeded with error:
```
Error: Monthly budget limit reached.

Current: $45.67 / $50.00 monthly limit
This query estimated cost: $2.34

To fix this:
1. Wait until next month (resets on [date])
2. Or increase limit in ~/.aurora/config.json under "budget.monthly_limit_usd"

See docs/cli/CLI_USAGE_GUIDE.md for budget management.
```

**FR-5.4**: The system MUST handle SOAR phase failures with specific guidance:
```
Error: SOAR pipeline failed at [Phase Name].

What happened: [Brief technical explanation]
Possible causes:
- [Cause 1]
- [Cause 2]

Suggested fixes:
- [Fix 1]
- [Fix 2]

If this persists, check logs at ~/.aurora/logs/ or report at [GitHub issues URL]
```

**FR-5.5**: The system MUST handle LLM API failures (rate limits, timeouts, server errors) with retry logic:
- 3 retry attempts with exponential backoff
- Clear error message after all retries exhausted
- Suggestion to check API status or try again later

### FR-6: Memory Integration

**FR-6.1**: The system MUST use indexed memory when available:
- Check if `~/.aurora/memory.db` exists and has chunks
- Include relevant chunks in LLM context (up to 3 for direct LLM, more for SOAR)
- Track which chunks were used in response metadata

**FR-6.2**: The system MUST handle missing or empty memory gracefully:
- If no memory indexed, proceed with query using only LLM's base knowledge
- Log warning in verbose mode: "No indexed memory found. Answering from base knowledge."

**FR-6.3**: The system MUST respect memory scope from CLI configuration:
- Use `memory.search_scope` setting (e.g., "current_project", "all")
- Filter indexed chunks accordingly

### FR-7: Integration with Existing MCP Tools

**FR-7.1**: The system MUST be discoverable alongside existing MCP tools:
- Listed in `aurora-mcp status` output
- Documented in MCP_SETUP.md
- Included in FastMCP tool registry

**FR-7.2**: The system SHOULD suggest related tools when appropriate:
- If query is about searching code → suggest `aurora_search`
- If query asks for stats → suggest `aurora_stats`
- If query references a specific file → suggest `aurora_context`

---

## Technical Requirements

### TR-1: Architecture & Design

**TR-1.1**: Implementation must follow existing AURORA MCP patterns:
- Add `aurora_query` method to `AuroraMCPTools` class (`src/aurora/mcp/tools.py`)
- Register tool in `AuroraMCPServer._register_tools()` (`src/aurora/mcp/server.py`)
- Use `@log_performance` decorator for timing metrics

**TR-1.2**: Implementation must reuse existing CLI components:
- Use `QueryExecutor` from `aurora_cli.execution` for all query execution
- Use `ErrorHandler` from `aurora_cli.errors` for error formatting
- Use `ConfigManager` from `aurora_cli.config` for configuration loading

**TR-1.3**: Implementation must maintain separation of concerns:
- `tools.py`: MCP tool interface (parameter validation, response formatting)
- `execution.py`: Query execution logic (LLM calls, SOAR pipeline)
- `escalation.py`: Auto-escalation logic (complexity detection)

**TR-1.4**: Implementation must use dependency injection:
- Initialize `QueryExecutor` with config in `AuroraMCPTools.__init__`
- Pass `memory_store` reference (not initialize it in QueryExecutor)
- Allow mocking for unit tests

### TR-2: Dependencies

**TR-2.1**: Required packages (already in pyproject.toml):
- `fastmcp` - MCP server framework
- `aurora-cli` - CLI components (QueryExecutor, ErrorHandler, etc.)
- `aurora-core` - Store and memory management
- `aurora-soar` - SOAR orchestrator
- `aurora-reasoning` - LLM clients

**TR-2.2**: Optional packages (for enhanced functionality):
- `sentence-transformers` - For semantic search (already optional `[ml]` extra)

**TR-2.3**: No new dependencies required for this implementation.

### TR-3: Performance Targets

**TR-3.1**: Direct LLM execution:
- Target: <2 seconds typical response time
- Maximum: <5 seconds for 95th percentile
- Memory: <50MB additional heap usage

**TR-3.2**: SOAR pipeline execution:
- Target: <10 seconds typical response time
- Maximum: <30 seconds for complex queries (95th percentile)
- Memory: <100MB additional heap usage

**TR-3.3**: MCP tool overhead:
- Tool invocation overhead: <100ms
- Parameter validation: <10ms
- Response formatting: <50ms

**TR-3.4**: Memory retrieval (when used):
- Hybrid search: <500ms for 1000 chunks
- Embedding generation: <200ms per query

### TR-4: Error Recovery

**TR-4.1**: The system must implement graceful degradation:
- If SOAR pipeline fails, fall back to direct LLM (with user warning)
- If memory retrieval fails, proceed without memory context
- If cost tracking fails, proceed with warning (don't block query)

**TR-4.2**: The system must implement retry logic:
- LLM API calls: 3 retries with exponential backoff (100ms, 200ms, 400ms)
- Memory retrieval: 2 retries with linear backoff (100ms)
- Budget check: No retry (fail fast)

**TR-4.3**: The system must log all errors:
- Error level for user-facing errors (API key missing, budget exceeded)
- Warning level for degradation (memory unavailable, phase skipped)
- Debug level for retry attempts

### TR-5: Configuration Schema

**TR-5.1**: Add to `~/.aurora/config.json`:

```json
{
  "api": {
    "anthropic_key": "sk-ant-...",
    "default_model": "claude-sonnet-4-20250514",
    "temperature": 0.7,
    "max_tokens": 4000
  },
  "query": {
    "auto_escalate": true,
    "complexity_threshold": 0.6,
    "verbosity": "normal"  // "quiet", "normal", "verbose"
  },
  "memory": {
    "search_scope": "current_project",  // "current_project", "all"
    "max_context_chunks": 10
  },
  "budget": {
    "monthly_limit_usd": 50.0
  }
}
```

**TR-5.2**: Environment variable overrides:
- `ANTHROPIC_API_KEY` → `api.anthropic_key`
- `AURORA_VERBOSITY` → `query.verbosity`
- `AURORA_MODEL` → `api.default_model`

### TR-6: Logging & Monitoring

**TR-6.1**: Log to `~/.aurora/logs/mcp.log`:
- All tool invocations with parameters (sanitized, no API keys)
- Execution path chosen (direct vs SOAR)
- Timing metrics per phase
- Error conditions with stack traces

**TR-6.2**: Performance metrics (via `@log_performance` decorator):
- Query execution time
- LLM API latency
- Memory retrieval time
- SOAR phase breakdown

**TR-6.3**: Cost tracking (via existing budget tracker):
- Update `~/.aurora/budget_tracker.json` after each query
- Track per-query cost and cumulative monthly cost
- Enforce budget limits before execution

### TR-7: Testing Requirements

**TR-7.1**: Unit tests (pytest):
- Test `aurora_query` with valid/invalid parameters
- Test error handling for each error type
- Test response formatting (verbose vs non-verbose)
- Test auto-escalation logic
- Test configuration loading (env vars, config file, defaults)

**TR-7.2**: Integration tests:
- Test with real `QueryExecutor` (mocked LLM)
- Test with real memory store (indexed test codebase)
- Test both execution paths (direct LLM, SOAR pipeline)
- Test budget enforcement
- Test graceful degradation scenarios

**TR-7.3**: End-to-end tests (optional, requires real API key):
- Test real query through MCP server
- Verify response format and content
- Verify cost tracking accuracy
- Verify memory integration

**TR-7.4**: CI/CD compliance:
- All tests must pass in CI environment
- MyPy type-checking: 0 errors (existing 6 errors in llm_client.py are tracked separately)
- Ruff linting: 0 errors
- Coverage: ≥74% (current project coverage)

---

## API Specification

### Tool Signature

```python
@mcp.tool()
def aurora_query(
    query: str,
    force_soar: bool = False,
    verbose: bool | None = None,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    """
    Execute AURORA query with reasoning and memory integration.

    This tool provides access to AURORA's core reasoning capabilities:
    - Simple queries use direct LLM for fast responses
    - Complex queries use full 9-phase SOAR pipeline
    - Auto-escalation chooses the best approach automatically

    Args:
        query: The question or prompt to process
        force_soar: If True, always use SOAR pipeline (skip auto-escalation)
        verbose: If True, include phase trace and detailed metrics in response.
                 If None, uses verbosity from config (default behavior).
        model: Override default LLM model (e.g., "claude-sonnet-4-20250514")
        temperature: Override default temperature (0.0-1.0, default: 0.7)
        max_tokens: Override default max tokens (default: 4000)

    Returns:
        JSON string with response structure:
        {
          "answer": "The response text...",
          "execution_path": "direct_llm" | "soar_pipeline",
          "metadata": {
            "duration_seconds": 2.34,
            "cost_usd": 0.0045,
            "input_tokens": 1234,
            "output_tokens": 567,
            "model": "claude-sonnet-4-20250514",
            "temperature": 0.7
          },
          "phases": [...],  // Only if verbose=true and SOAR used
          "sources": [...]  // Only if memory was used
        }

    Raises:
        ValueError: If query is empty or parameters are invalid
        APIError: If API key is missing, budget exceeded, or LLM call fails
        RuntimeError: If SOAR pipeline fails (with detailed error message)

    Examples:
        # Simple query (uses direct LLM)
        aurora_query("What is ACT-R?")

        # Complex query (auto-escalates to SOAR)
        aurora_query("Compare the architecture of SOAR vs ACT-R memory systems")

        # Force SOAR for deep analysis
        aurora_query("Analyze this codebase", force_soar=True)

        # Verbose output with phase trace
        aurora_query("How does the SOAR pipeline work?", verbose=True)
    """
```

### Implementation Outline

```python
# In src/aurora/mcp/tools.py

class AuroraMCPTools:
    def __init__(self, db_path: str, config_path: str | None = None):
        # Existing initialization...

        # Add QueryExecutor initialization
        self._query_executor: QueryExecutor | None = None
        self._config_manager: ConfigManager | None = None

    def _ensure_query_executor_initialized(self) -> None:
        """Ensure QueryExecutor is initialized with config."""
        if self._query_executor is None:
            # Load config
            config = self._load_config()

            # Initialize QueryExecutor
            self._query_executor = QueryExecutor(config=config)

    def _load_config(self) -> dict[str, Any]:
        """Load AURORA config from file and environment."""
        # 1. Read ~/.aurora/config.json
        # 2. Override with environment variables
        # 3. Set defaults for missing values
        # 4. Return config dict
        pass

    @log_performance("aurora_query")
    def aurora_query(
        self,
        query: str,
        force_soar: bool = False,
        verbose: bool | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """
        Execute AURORA query with reasoning and memory.

        See tool signature above for full documentation.
        """
        try:
            # 1. Validate parameters
            if not query or not query.strip():
                return self._format_error(
                    error_type="InvalidParameter",
                    message="Query cannot be empty",
                    suggestion="Provide a non-empty query string"
                )

            # 2. Ensure initialized
            self._ensure_initialized()
            self._ensure_query_executor_initialized()

            # 3. Get API key
            api_key = self._get_api_key()
            if not api_key:
                return self._format_error(
                    error_type="APIKeyMissing",
                    message="API key not found",
                    suggestion=(
                        "Set ANTHROPIC_API_KEY environment variable or "
                        "add to ~/.aurora/config.json under 'api.anthropic_key'"
                    )
                )

            # 4. Check budget
            if not self._check_budget():
                return self._format_error(
                    error_type="BudgetExceeded",
                    message=self._get_budget_error_message(),
                    suggestion=self._get_budget_suggestion()
                )

            # 5. Determine verbosity
            if verbose is None:
                verbose = self._get_config_verbosity()

            # 6. Build execution config (override defaults with params)
            exec_config = self._build_execution_config(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )

            # 7. Execute query
            if force_soar:
                # Force SOAR pipeline
                result = self._execute_soar(query, api_key, verbose, exec_config)
            else:
                # Auto-escalate
                result = self._execute_with_auto_escalation(query, api_key, verbose, exec_config)

            # 8. Format response
            return self._format_response(result, verbose)

        except Exception as e:
            logger.error(f"Error in aurora_query: {e}", exc_info=True)
            return self._format_error_from_exception(e)

    def _execute_with_auto_escalation(
        self,
        query: str,
        api_key: str,
        verbose: bool,
        config: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute query with auto-escalation logic."""
        # 1. Assess complexity (reuse CLI escalation logic)
        from aurora_cli.escalation import assess_query_complexity

        complexity = assess_query_complexity(query)
        threshold = config.get("complexity_threshold", 0.6)

        # 2. Choose execution path
        if complexity < threshold:
            # Use direct LLM
            response = self._query_executor.execute_direct_llm(
                query=query,
                api_key=api_key,
                memory_store=self._store,
                verbose=verbose
            )
            return {
                "answer": response,
                "execution_path": "direct_llm",
                "complexity_score": complexity
            }
        else:
            # Use SOAR pipeline
            return self._execute_soar(query, api_key, verbose, config)

    def _execute_soar(
        self,
        query: str,
        api_key: str,
        verbose: bool,
        config: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute query using SOAR pipeline."""
        # Update QueryExecutor config
        self._query_executor.config.update(config)

        # Execute SOAR
        result = self._query_executor.execute_aurora(
            query=query,
            api_key=api_key,
            memory_store=self._store,
            verbose=verbose
        )

        # Result is either str or tuple[str, dict]
        if isinstance(result, tuple):
            response, phase_trace = result
            return {
                "answer": response,
                "execution_path": "soar_pipeline",
                "phase_trace": phase_trace
            }
        else:
            return {
                "answer": result,
                "execution_path": "soar_pipeline"
            }

    def _format_response(self, result: dict[str, Any], verbose: bool) -> str:
        """Format query result as JSON response."""
        # Build response structure per FR-4.1
        response = {
            "answer": result.get("answer", ""),
            "execution_path": result.get("execution_path", "unknown"),
            "metadata": self._extract_metadata(result)
        }

        # Add optional fields
        if verbose and "phase_trace" in result:
            response["phases"] = result["phase_trace"].get("phases", [])

        if "sources" in result:
            response["sources"] = result["sources"]

        return json.dumps(response, indent=2)

    def _format_error(
        self,
        error_type: str,
        message: str,
        suggestion: str,
        details: dict[str, Any] | None = None
    ) -> str:
        """Format error response per FR-4.2."""
        error_response = {
            "error": {
                "type": error_type,
                "message": message,
                "suggestion": suggestion
            }
        }

        if details:
            error_response["error"]["details"] = details

        return json.dumps(error_response, indent=2)
```

### Response Examples

**Example 1: Simple Query (Direct LLM)**

Request:
```python
aurora_query("What is ACT-R?")
```

Response:
```json
{
  "answer": "ACT-R (Adaptive Control of Thought-Rational) is a cognitive architecture that models human cognition through a modular system of buffers and production rules. It combines declarative knowledge (facts) stored in chunks with procedural knowledge (skills) encoded as production rules...",
  "execution_path": "direct_llm",
  "metadata": {
    "duration_seconds": 1.23,
    "cost_usd": 0.0012,
    "input_tokens": 45,
    "output_tokens": 150,
    "model": "claude-sonnet-4-20250514",
    "temperature": 0.7
  }
}
```

**Example 2: Complex Query (SOAR Pipeline, Verbose)**

Request:
```python
aurora_query(
    "Compare the memory systems in SOAR vs ACT-R and explain which is better for code understanding",
    verbose=True
)
```

Response:
```json
{
  "answer": "After analyzing both architectures, SOAR and ACT-R have fundamentally different approaches to memory...\n\n[Detailed comparison]\n\nFor code understanding specifically, SOAR's episodic memory and chunking mechanism provides better support because...",
  "execution_path": "soar_pipeline",
  "metadata": {
    "duration_seconds": 8.45,
    "cost_usd": 0.0234,
    "input_tokens": 2345,
    "output_tokens": 1200,
    "model": "claude-sonnet-4-20250514",
    "temperature": 0.7
  },
  "phases": [
    {
      "name": "Assess",
      "duration_seconds": 0.34,
      "summary": "Complexity: high (comparative analysis)"
    },
    {
      "name": "Retrieve",
      "duration_seconds": 0.56,
      "summary": "Retrieved 12 chunks from memory"
    },
    {
      "name": "Decompose",
      "duration_seconds": 0.78,
      "summary": "Created 4 subgoals"
    },
    {
      "name": "Verify",
      "duration_seconds": 0.45,
      "summary": "Quality score: 0.89"
    },
    {
      "name": "Route",
      "duration_seconds": 0.23,
      "summary": "Assigned 3 agents"
    },
    {
      "name": "Collect",
      "duration_seconds": 4.12,
      "summary": "Executed 3 agents"
    },
    {
      "name": "Synthesize",
      "duration_seconds": 1.34,
      "summary": "Synthesized from 4 sources"
    },
    {
      "name": "Record",
      "duration_seconds": 0.45,
      "summary": "Cached 2 patterns"
    },
    {
      "name": "Respond",
      "duration_seconds": 0.18,
      "summary": "Formatted response"
    }
  ],
  "sources": [
    {
      "file_path": "/home/user/docs/soar-architecture.md",
      "chunk_id": "doc:soar-architecture:memory-section",
      "score": 0.92
    },
    {
      "file_path": "/home/user/docs/actr-activation.md",
      "chunk_id": "doc:actr-activation:intro",
      "score": 0.87
    }
  ]
}
```

**Example 3: Error - Missing API Key**

Request:
```python
aurora_query("What is SOAR?")
# (API key not configured)
```

Response:
```json
{
  "error": {
    "type": "APIKeyMissing",
    "message": "API key not found. AURORA requires an Anthropic API key to execute queries.",
    "suggestion": "To fix this:\n1. Set environment variable: export ANTHROPIC_API_KEY=\"your-key\"\n2. Or add to config file: ~/.aurora/config.json under \"api.anthropic_key\"\n\nGet your API key at: https://console.anthropic.com/\n\nSee docs/TROUBLESHOOTING.md for more details."
  }
}
```

**Example 4: Error - Budget Exceeded**

Request:
```python
aurora_query("Complex analysis question...")
# (User has spent $49.50 of $50 monthly budget)
```

Response:
```json
{
  "error": {
    "type": "BudgetExceeded",
    "message": "Monthly budget limit reached. Cannot execute query.",
    "suggestion": "Current usage: $49.67 / $50.00 monthly limit\nEstimated query cost: $2.34\n\nTo fix this:\n1. Wait until next month (budget resets on 2025-02-01)\n2. Or increase limit in ~/.aurora/config.json under \"budget.monthly_limit_usd\"\n\nSee docs/cli/CLI_USAGE_GUIDE.md for budget management.",
    "details": {
      "current_usage_usd": 49.67,
      "monthly_limit_usd": 50.0,
      "estimated_query_cost_usd": 2.34,
      "reset_date": "2025-02-01"
    }
  }
}
```

---

## Error Handling & User Experience

### Error Message Philosophy

AURORA's error messages must follow these principles:

1. **Be Friendly**: No technical jargon, assume user is not an expert
2. **Be Specific**: Tell user exactly what went wrong (not generic "error occurred")
3. **Be Actionable**: Always include "To fix this:" section with steps
4. **Be Contextual**: Provide relevant details (current budget, file paths, etc.)
5. **Be Helpful**: Link to documentation or support resources

### Error Catalog

#### Error 1: Missing API Key

**Trigger**: `ANTHROPIC_API_KEY` env var not set and not in config file

**Message**:
```
Error: API key not found

AURORA requires an Anthropic API key to execute queries.

To fix this:
1. Set environment variable:
   export ANTHROPIC_API_KEY="your-key-here"

2. Or add to config file:
   Edit ~/.aurora/config.json and add:
   {
     "api": {
       "anthropic_key": "your-key-here"
     }
   }

Get your API key at: https://console.anthropic.com/

See docs/TROUBLESHOOTING.md for more details.
```

#### Error 2: Budget Exceeded

**Trigger**: Current monthly usage + estimated query cost > monthly limit

**Message**:
```
Error: Monthly budget limit reached

Current usage: $45.67 / $50.00 monthly limit
Estimated query cost: $5.23

Cannot execute query without exceeding budget.

To fix this:
1. Wait until next month (budget resets on 2025-02-01)
2. Or increase limit in ~/.aurora/config.json:
   {
     "budget": {
       "monthly_limit_usd": 100.0
     }
   }

See docs/cli/CLI_USAGE_GUIDE.md for budget management.
```

#### Error 3: SOAR Phase Failure

**Trigger**: Exception during SOAR pipeline execution

**Message**:
```
Error: SOAR pipeline failed at [Phase Name]

What happened: [Brief explanation of what the phase does and why it failed]

Possible causes:
- Memory store is corrupted or inaccessible
- LLM returned unexpected response format
- Agent execution timeout

Suggested fixes:
1. Try a simpler query first to isolate the issue
2. Check ~/.aurora/logs/mcp.log for detailed error trace
3. Verify memory store integrity: aurora-mcp aurora_stats
4. Re-index codebase if needed: aurora-mcp aurora_index /path/to/code

If this persists, please report at:
https://github.com/yourusername/aurora/issues

Include logs from ~/.aurora/logs/mcp.log
```

#### Error 4: Invalid Parameter

**Trigger**: Parameter validation fails (empty query, invalid temperature, etc.)

**Message**:
```
Error: Invalid parameter "[parameter_name]"

Problem: [Specific validation failure]

Valid values:
- query: Non-empty string
- temperature: Float between 0.0 and 1.0
- model: Valid Anthropic model ID (e.g., "claude-sonnet-4-20250514")
- max_tokens: Positive integer (1-4000)

Example valid call:
aurora_query("What is SOAR?", temperature=0.7, max_tokens=500)
```

#### Error 5: Memory Store Unavailable

**Trigger**: `~/.aurora/memory.db` doesn't exist or is corrupted

**Behavior**: This is NOT a hard error - proceed with warning

**Message** (logged as warning):
```
Warning: Memory store not available

AURORA will answer from base knowledge without indexed context.

To fix this:
1. Index your codebase: aurora-mcp aurora_index /path/to/code
2. Or use CLI: aur mem index /path/to/code

See docs/cli/CLI_USAGE_GUIDE.md for indexing guide.
```

#### Error 6: LLM API Failure

**Trigger**: API call fails after all retries (rate limit, timeout, server error)

**Message**:
```
Error: LLM API call failed

Problem: [Specific API error - rate limit, timeout, server error, etc.]

What we tried:
- 3 retry attempts with exponential backoff
- Total wait time: [X] seconds

Suggested fixes:
1. Check Anthropic API status: https://status.anthropic.com/
2. Verify API key is valid and has credits
3. Try again in a few minutes (may be temporary rate limit)
4. If using custom model, verify it's available

See docs/TROUBLESHOOTING.md for more details.
```

### Progress Visibility Design

Progress messages should be:
- **Declarative**: "Retrieving context..." not "Calling retrieval function..."
- **User-focused**: "Analyzing query complexity..." not "Running assess phase..."
- **Informative**: Include key metrics when helpful ("Retrieved 12 chunks...")

**Progress Format (SOAR Pipeline)**:

```
[1/9] Assessing query complexity...
      → Complexity: high (comparative analysis)

[2/9] Retrieving relevant context from memory...
      → Retrieved 12 chunks (345ms)

[3/9] Decomposing query into subgoals...
      → Created 4 subgoals

[4/9] Verifying context quality...
      → Quality score: 0.89

[5/9] Routing subgoals to agents...
      → Assigned 3 specialized agents

[6/9] Collecting agent responses...
      → Agent 1/3 complete (1.2s)
      → Agent 2/3 complete (2.3s)
      → Agent 3/3 complete (1.8s)

[7/9] Synthesizing final answer...
      → Combining insights from 4 sources

[8/9] Recording patterns in memory...
      → Cached 2 new patterns

[9/9] Formatting response...
      → Complete! (8.45s total, $0.0234)
```

**Progress Format (Direct LLM)**:

```
→ Executing query... (fast mode)
→ Complete! (1.23s, $0.0012)
```

---

## Testing Strategy

### Test-Driven Development (TDD) Approach

Following AURORA's TDD requirement, all tests must be written BEFORE implementation:

1. **Write failing test** for each requirement
2. **Run test** to verify it fails (proves test is valid)
3. **Implement minimal code** to make test pass
4. **Refactor** while keeping tests green
5. **Repeat** for next requirement

### Test Pyramid

```
        /\
       /E2E\           5 tests (optional, requires API key)
      /------\
     /  INT   \        20 tests (with real components, mocked LLM)
    /----------\
   /    UNIT    \      50 tests (pure unit tests, all mocked)
  /--------------\
```

### Unit Tests (50 tests, ~4 hours to write)

**File**: `tests/unit/mcp/test_aurora_query_tool.py`

```python
"""Unit tests for aurora_query MCP tool."""

import json
import pytest
from unittest.mock import Mock, MagicMock, patch

from aurora.mcp.tools import AuroraMCPTools


class TestAuroraQueryParameterValidation:
    """Test parameter validation (US-1.4, FR-1.1, FR-5.1)."""

    def test_empty_query_returns_error(self):
        """Empty query should return InvalidParameter error."""
        tools = AuroraMCPTools(db_path=":memory:")
        result = tools.aurora_query("")

        response = json.loads(result)
        assert "error" in response
        assert response["error"]["type"] == "InvalidParameter"
        assert "empty" in response["error"]["message"].lower()

    def test_whitespace_only_query_returns_error(self):
        """Whitespace-only query should return InvalidParameter error."""
        tools = AuroraMCPTools(db_path=":memory:")
        result = tools.aurora_query("   \n  \t  ")

        response = json.loads(result)
        assert "error" in response
        assert response["error"]["type"] == "InvalidParameter"

    def test_valid_query_passes_validation(self):
        """Valid query should pass validation."""
        tools = AuroraMCPTools(db_path=":memory:")
        # Mock QueryExecutor to avoid actual LLM call
        with patch.object(tools, '_query_executor'):
            result = tools.aurora_query("What is ACT-R?")
            # Should not have error (will fail on other checks, but validation passed)

    def test_temperature_out_of_range_returns_error(self):
        """Temperature outside [0.0, 1.0] should return error."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Temperature too high
        result = tools.aurora_query("Test", temperature=1.5)
        response = json.loads(result)
        assert "error" in response
        assert response["error"]["type"] == "InvalidParameter"

        # Temperature too low
        result = tools.aurora_query("Test", temperature=-0.1)
        response = json.loads(result)
        assert "error" in response

    def test_negative_max_tokens_returns_error(self):
        """Negative max_tokens should return error."""
        tools = AuroraMCPTools(db_path=":memory:")
        result = tools.aurora_query("Test", max_tokens=-100)

        response = json.loads(result)
        assert "error" in response
        assert response["error"]["type"] == "InvalidParameter"


class TestAuroraQueryAPIKeyHandling:
    """Test API key loading and validation (US-1.4, FR-2.1, FR-5.2)."""

    def test_missing_api_key_returns_helpful_error(self):
        """Missing API key should return APIKeyMissing error with guidance."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Mock config loading to return no API key
        with patch.object(tools, '_get_api_key', return_value=None):
            result = tools.aurora_query("Test query")

        response = json.loads(result)
        assert "error" in response
        assert response["error"]["type"] == "APIKeyMissing"
        assert "ANTHROPIC_API_KEY" in response["error"]["suggestion"]
        assert "config.json" in response["error"]["suggestion"]

    def test_api_key_from_environment_variable(self):
        """API key should be loaded from ANTHROPIC_API_KEY env var."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            api_key = tools._get_api_key()
            assert api_key == 'test-key'

    def test_api_key_from_config_file(self):
        """API key should be loaded from config file if env var not set."""
        tools = AuroraMCPTools(db_path=":memory:")

        mock_config = {"api": {"anthropic_key": "config-key"}}
        with patch.object(tools, '_load_config', return_value=mock_config):
            with patch.dict('os.environ', {}, clear=True):
                api_key = tools._get_api_key()
                assert api_key == 'config-key'

    def test_env_var_overrides_config_file(self):
        """Environment variable should take precedence over config file."""
        tools = AuroraMCPTools(db_path=":memory:")

        mock_config = {"api": {"anthropic_key": "config-key"}}
        with patch.object(tools, '_load_config', return_value=mock_config):
            with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'env-key'}):
                api_key = tools._get_api_key()
                assert api_key == 'env-key'


class TestAuroraQueryBudgetEnforcement:
    """Test budget checking and enforcement (US-2.2, FR-2.3, FR-5.3)."""

    def test_budget_exceeded_returns_error(self):
        """Query that would exceed budget should return BudgetExceeded error."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Mock budget check to return False
        with patch.object(tools, '_check_budget', return_value=False):
            with patch.object(tools, '_get_api_key', return_value='test-key'):
                result = tools.aurora_query("Test query")

        response = json.loads(result)
        assert "error" in response
        assert response["error"]["type"] == "BudgetExceeded"
        assert "monthly_limit" in response["error"]["suggestion"].lower()

    def test_budget_check_allows_query_under_limit(self):
        """Query under budget limit should proceed."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Mock budget check to return True
        with patch.object(tools, '_check_budget', return_value=True):
            with patch.object(tools, '_get_api_key', return_value='test-key'):
                with patch.object(tools._query_executor, 'execute_direct_llm'):
                    # Should not raise budget error
                    tools.aurora_query("Test query")


class TestAuroraQueryAutoEscalation:
    """Test auto-escalation logic (US-1.2, FR-1.3)."""

    def test_simple_query_uses_direct_llm(self):
        """Simple query should use direct LLM execution."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Mock complexity assessment to return low complexity
        with patch('aurora_cli.escalation.assess_query_complexity', return_value=0.3):
            with patch.object(tools._query_executor, 'execute_direct_llm') as mock_direct:
                with patch.object(tools, '_get_api_key', return_value='test-key'):
                    with patch.object(tools, '_check_budget', return_value=True):
                        mock_direct.return_value = "Answer"
                        tools.aurora_query("What is X?")

                        # Should call direct LLM, not SOAR
                        assert mock_direct.called

    def test_complex_query_uses_soar_pipeline(self):
        """Complex query should use SOAR pipeline."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Mock complexity assessment to return high complexity
        with patch('aurora_cli.escalation.assess_query_complexity', return_value=0.8):
            with patch.object(tools._query_executor, 'execute_aurora') as mock_aurora:
                with patch.object(tools, '_get_api_key', return_value='test-key'):
                    with patch.object(tools, '_check_budget', return_value=True):
                        mock_aurora.return_value = "Answer"
                        tools.aurora_query("Analyze complex architecture...")

                        # Should call SOAR, not direct LLM
                        assert mock_aurora.called

    def test_force_soar_bypasses_escalation(self):
        """force_soar=True should always use SOAR pipeline."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Even with low complexity, should use SOAR
        with patch('aurora_cli.escalation.assess_query_complexity', return_value=0.2):
            with patch.object(tools._query_executor, 'execute_aurora') as mock_aurora:
                with patch.object(tools, '_get_api_key', return_value='test-key'):
                    with patch.object(tools, '_check_budget', return_value=True):
                        mock_aurora.return_value = "Answer"
                        tools.aurora_query("Simple question", force_soar=True)

                        # Should call SOAR despite low complexity
                        assert mock_aurora.called


class TestAuroraQueryResponseFormatting:
    """Test response formatting (US-2.3, FR-4.1)."""

    def test_response_includes_required_fields(self):
        """Response should include answer, execution_path, and metadata."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Mock successful execution
        with patch.object(tools._query_executor, 'execute_direct_llm') as mock_exec:
            with patch.object(tools, '_get_api_key', return_value='test-key'):
                with patch.object(tools, '_check_budget', return_value=True):
                    # Return mock LLM response
                    mock_response = Mock()
                    mock_response.content = "Test answer"
                    mock_response.input_tokens = 100
                    mock_response.output_tokens = 50
                    mock_exec.return_value = mock_response

                    result = tools.aurora_query("Test")
                    response = json.loads(result)

                    assert "answer" in response
                    assert "execution_path" in response
                    assert "metadata" in response
                    assert response["execution_path"] in ["direct_llm", "soar_pipeline"]

    def test_verbose_response_includes_phases(self):
        """Verbose response should include phase trace for SOAR queries."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Mock SOAR execution with phase trace
        with patch.object(tools._query_executor, 'execute_aurora') as mock_exec:
            with patch.object(tools, '_get_api_key', return_value='test-key'):
                with patch.object(tools, '_check_budget', return_value=True):
                    # Return mock SOAR response with phase trace
                    phase_trace = {
                        "phases": [{"name": "Assess", "duration_seconds": 0.1}],
                        "total_duration": 1.0,
                        "total_cost": 0.01
                    }
                    mock_exec.return_value = ("Answer", phase_trace)

                    result = tools.aurora_query("Test", verbose=True)
                    response = json.loads(result)

                    assert "phases" in response
                    assert len(response["phases"]) > 0

    def test_non_verbose_response_excludes_phases(self):
        """Non-verbose response should not include phase trace."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools._query_executor, 'execute_direct_llm') as mock_exec:
            with patch.object(tools, '_get_api_key', return_value='test-key'):
                with patch.object(tools, '_check_budget', return_value=True):
                    mock_response = Mock()
                    mock_response.content = "Answer"
                    mock_exec.return_value = mock_response

                    result = tools.aurora_query("Test", verbose=False)
                    response = json.loads(result)

                    assert "phases" not in response


class TestAuroraQueryMemoryIntegration:
    """Test memory integration (US-3.2, FR-6.1, FR-6.2)."""

    def test_uses_memory_when_available(self):
        """Should use indexed memory when available."""
        # Test that memory store is passed to QueryExecutor
        # Test that memory chunks are included in context
        pass

    def test_graceful_degradation_when_memory_unavailable(self):
        """Should proceed without memory if store is empty/missing."""
        # Test warning is logged
        # Test query still executes
        pass

    def test_sources_included_when_memory_used(self):
        """Response should include sources when memory was used."""
        # Test sources field is populated
        # Test sources have correct format (file_path, chunk_id, score)
        pass


# 40 more unit tests covering:
# - Configuration loading (env vars, file, defaults)
# - Error formatting for each error type
# - Progress message generation
# - Metadata extraction (cost, tokens, timing)
# - Parameter override logic (model, temperature, max_tokens)
# - Graceful degradation scenarios
# - Retry logic for LLM API calls
# - Logging behavior (what gets logged at each level)
```

### Integration Tests (20 tests, ~3 hours to write)

**File**: `tests/integration/test_mcp_aurora_query_integration.py`

```python
"""Integration tests for aurora_query with real components."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, Mock

from aurora.mcp.tools import AuroraMCPTools
from aurora.mcp.server import AuroraMCPServer
from aurora_core.store.sqlite import SQLiteStore
from aurora_cli.execution import QueryExecutor


@pytest.fixture
def test_db_path(tmp_path):
    """Provide temporary database path."""
    return str(tmp_path / "test_memory.db")


@pytest.fixture
def indexed_store(test_db_path, sample_codebase):
    """Provide pre-indexed memory store."""
    # Index sample codebase
    # Return initialized store
    pass


class TestAuroraQueryEndToEnd:
    """End-to-end integration tests with real components (mocked LLM)."""

    def test_direct_llm_execution_flow(self, indexed_store):
        """Test complete flow for direct LLM execution."""
        tools = AuroraMCPTools(db_path=indexed_store.db_path)

        # Mock LLM response
        with patch('aurora_reasoning.llm_client.AnthropicClient.generate') as mock_llm:
            mock_response = Mock()
            mock_response.content = "ACT-R is a cognitive architecture..."
            mock_response.input_tokens = 50
            mock_response.output_tokens = 100
            mock_llm.return_value = mock_response

            # Execute query
            with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
                result = tools.aurora_query("What is ACT-R?")

            # Verify response
            response = json.loads(result)
            assert response["execution_path"] == "direct_llm"
            assert "ACT-R" in response["answer"]
            assert response["metadata"]["cost_usd"] > 0

    def test_soar_pipeline_execution_flow(self, indexed_store):
        """Test complete flow for SOAR pipeline execution."""
        tools = AuroraMCPTools(db_path=indexed_store.db_path)

        # Mock LLM for SOAR pipeline
        with patch('aurora_reasoning.llm_client.AnthropicClient.generate') as mock_llm:
            mock_response = Mock()
            mock_response.content = json.dumps({
                "complexity": "high",
                "subgoals": ["goal1", "goal2"]
            })
            mock_llm.return_value = mock_response

            # Execute complex query
            with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
                result = tools.aurora_query(
                    "Compare SOAR and ACT-R memory systems",
                    verbose=True
                )

            # Verify response
            response = json.loads(result)
            assert response["execution_path"] == "soar_pipeline"
            assert "phases" in response
            assert len(response["phases"]) == 9

    def test_memory_context_included_in_query(self, indexed_store):
        """Test that indexed memory is used in query context."""
        # Execute query that should use indexed memory
        # Verify memory chunks were retrieved
        # Verify sources are included in response
        pass

    def test_budget_tracking_updates_correctly(self, test_db_path):
        """Test that budget tracker is updated after query."""
        # Execute query
        # Verify budget_tracker.json was updated
        # Verify cost calculation is accurate
        pass

    def test_force_soar_parameter_works(self, indexed_store):
        """Test force_soar parameter forces SOAR execution."""
        # Execute simple query with force_soar=True
        # Verify SOAR pipeline was used despite low complexity
        pass


class TestAuroraQueryErrorScenarios:
    """Integration tests for error scenarios."""

    def test_missing_api_key_scenario(self, test_db_path):
        """Test complete error flow for missing API key."""
        tools = AuroraMCPTools(db_path=test_db_path)

        # Clear environment and mock config
        with patch.dict('os.environ', {}, clear=True):
            with patch.object(tools, '_load_config', return_value={}):
                result = tools.aurora_query("Test")

        # Verify error response
        response = json.loads(result)
        assert "error" in response
        assert response["error"]["type"] == "APIKeyMissing"

    def test_budget_exceeded_scenario(self, test_db_path):
        """Test complete error flow for budget exceeded."""
        # Mock budget tracker showing exceeded budget
        # Execute query
        # Verify BudgetExceeded error is returned
        pass

    def test_soar_phase_failure_scenario(self, indexed_store):
        """Test error handling when SOAR phase fails."""
        # Mock SOAR phase to raise exception
        # Execute query
        # Verify SOARPhaseFailed error is returned with helpful message
        pass

    def test_llm_api_failure_with_retry(self, indexed_store):
        """Test retry logic for LLM API failures."""
        # Mock LLM to fail 2 times then succeed
        # Execute query
        # Verify retry happened and query succeeded
        pass

    def test_llm_api_failure_exhausted_retries(self, indexed_store):
        """Test error when all retries are exhausted."""
        # Mock LLM to always fail
        # Execute query
        # Verify APIError is returned after 3 retries
        pass


class TestAuroraQueryConfiguration:
    """Integration tests for configuration loading and overrides."""

    def test_config_file_loaded_correctly(self, test_db_path, tmp_path):
        """Test that config file is loaded and used."""
        # Create config file with custom settings
        # Execute query
        # Verify custom settings were used
        pass

    def test_parameter_overrides_config(self, test_db_path):
        """Test that parameters override config file."""
        # Set config with default temperature=0.5
        # Execute query with temperature=0.9
        # Verify 0.9 was used
        pass

    def test_verbosity_from_config(self, test_db_path):
        """Test verbosity setting from config."""
        # Set config with verbosity="verbose"
        # Execute query without verbose parameter
        # Verify verbose response is returned
        pass


# 10 more integration tests covering:
# - MCP server registration and tool discovery
# - Performance under load (multiple concurrent queries)
# - Memory retrieval accuracy
# - Cost calculation accuracy
# - Phase timing accuracy
# - Graceful degradation (memory unavailable, config missing)
# - Log file creation and content
```

### End-to-End Tests (5 tests, optional, requires API key)

**File**: `tests/e2e/test_aurora_query_e2e.py`

```python
"""End-to-end tests with real LLM API (requires ANTHROPIC_API_KEY)."""

import json
import pytest
import os


# Skip all tests if no API key
pytestmark = pytest.mark.skipif(
    not os.getenv('ANTHROPIC_API_KEY'),
    reason="E2E tests require ANTHROPIC_API_KEY environment variable"
)


class TestAuroraQueryRealAPI:
    """E2E tests with real Anthropic API."""

    def test_simple_query_real_api(self, indexed_store):
        """Test simple query with real API."""
        tools = AuroraMCPTools(db_path=indexed_store.db_path)

        result = tools.aurora_query("What is 2+2?")
        response = json.loads(result)

        assert "answer" in response
        assert "4" in response["answer"]
        assert response["execution_path"] == "direct_llm"

    def test_complex_query_real_api(self, indexed_store):
        """Test complex query triggering SOAR with real API."""
        tools = AuroraMCPTools(db_path=indexed_store.db_path)

        result = tools.aurora_query(
            "Explain the differences between SOAR and ACT-R cognitive architectures, "
            "focusing on memory systems and production rules",
            verbose=True
        )
        response = json.loads(result)

        assert "answer" in response
        assert response["execution_path"] == "soar_pipeline"
        assert "phases" in response
        assert len(response["phases"]) == 9

    # 3 more E2E tests...
```

### Test Execution Strategy

**Phase 1: Unit Tests (TDD)**
1. Write all 50 unit tests FIRST (before any implementation)
2. Run tests - all should fail (no implementation yet)
3. Implement `aurora_query` method incrementally
4. Run tests after each increment - watch tests turn green
5. Target: 100% unit test pass rate

**Phase 2: Integration Tests**
1. Write integration tests (after unit tests pass)
2. Run with real components (mocked LLM only)
3. Fix integration issues
4. Target: 100% integration test pass rate

**Phase 3: CI/CD Validation**
1. Run `make quality-check` (includes all quality gates)
2. Fix any linting, type-checking, or test failures
3. Target: All CI/CD checks pass

**Phase 4: Optional E2E Tests**
1. Run E2E tests with real API key (only if available)
2. Validate end-to-end behavior
3. These can be skipped in CI (use `pytest -m "not e2e"`)

### CI/CD Integration

**Existing CI Pipeline** (from `.github/workflows/test.yml`):
```yaml
# Add to existing test job
- name: Run MCP query tests
  run: |
    pytest tests/unit/mcp/test_aurora_query_tool.py -v
    pytest tests/integration/test_mcp_aurora_query_integration.py -v
```

**Test Coverage Target**:
- Current: 74% overall coverage
- Target for this feature: ≥80% coverage for new code
- Required: All new code must have unit tests

### Known CI/CD Challenges

**Issue**: CI/CD has been a major hurdle (per user requirements)

**Mitigation Strategies**:
1. **Run tests locally first** before pushing to CI
2. **Use same Python version as CI** (3.12) for local testing
3. **Mock all external dependencies** (LLM APIs, filesystem where possible)
4. **Skip expensive tests in CI** using markers: `@pytest.mark.slow`
5. **Separate unit vs integration tests** - run unit tests first (fast feedback)
6. **Use CI environment markers** to skip problematic tests in CI:
   ```python
   @pytest.mark.skipif(os.getenv('CI') == 'true', reason="Flaky in CI")
   ```

---

## Success Metrics

### Functional Completeness Metrics

**Metric 1: Feature Parity**
- **Target**: 100% of CLI `aur query` functionality available via MCP
- **Measurement**: Feature checklist comparison (CLI vs MCP)
- **Success Criteria**: All CLI features present in MCP

**Metric 2: Tool Availability**
- **Target**: `aurora_query` tool discoverable in Claude Desktop
- **Measurement**: Manual verification via Claude Desktop tool list
- **Success Criteria**: Tool appears and is callable

### Quality Metrics

**Metric 3: Test Coverage**
- **Target**: ≥80% coverage for new code
- **Measurement**: pytest-cov report
- **Success Criteria**: Coverage report shows ≥80% for `aurora.mcp.tools.aurora_query`

**Metric 4: CI/CD Pass Rate**
- **Target**: 100% CI/CD checks pass
- **Measurement**: GitHub Actions workflow status
- **Success Criteria**: Green checkmark on PR, all jobs pass

**Metric 5: Type Safety**
- **Target**: 0 new MyPy errors
- **Measurement**: `make type-check` output
- **Success Criteria**: No errors in new code (existing 6 errors in llm_client.py are tracked separately)

### User Experience Metrics

**Metric 6: Error Message Quality**
- **Target**: All error messages include actionable guidance
- **Measurement**: Manual review of error catalog
- **Success Criteria**: Each error has "To fix this:" section with steps

**Metric 7: Performance**
- **Target**: Direct LLM <2s, SOAR <10s (typical)
- **Measurement**: Integration test timing
- **Success Criteria**: 80th percentile meets targets

### Adoption Metrics (Post-Launch)

**Metric 8: MCP vs CLI Usage**
- **Target**: MCP becomes primary interface (>50% of queries)
- **Measurement**: Query count logs (MCP vs CLI)
- **Success Criteria**: More queries via MCP than CLI within 1 month

**Metric 9: User Support Requests**
- **Target**: <5 support requests per 100 queries
- **Measurement**: GitHub issues tagged with "mcp" or "aurora_query"
- **Success Criteria**: Low support request rate indicates clear UX

---

## Implementation Plan

### Task Breakdown

The implementation is structured into **5 parent tasks** to keep the sprint manageable (per user requirement: "If more than 5 parent tasks, skip tech debt").

**Parent Task 1: Core Implementation** (Day 1, 6 hours)
- 1.1: Add `aurora_query` method to `AuroraMCPTools` class
- 1.2: Implement parameter validation (query, model, temperature, max_tokens)
- 1.3: Implement API key loading (env var, config file)
- 1.4: Implement budget checking logic
- 1.5: Write unit tests for parameter validation and config loading

**Parent Task 2: Query Execution Integration** (Day 2, 6 hours)
- 2.1: Integrate with `QueryExecutor.execute_direct_llm()`
- 2.2: Integrate with `QueryExecutor.execute_aurora()` (SOAR pipeline)
- 2.3: Implement auto-escalation logic (complexity assessment)
- 2.4: Add `force_soar` parameter handling
- 2.5: Write unit tests for execution paths and escalation

**Parent Task 3: Response Formatting & Error Handling** (Day 2, 4 hours)
- 3.1: Implement response formatting (JSON structure per FR-4.1)
- 3.2: Implement error formatting (JSON structure per FR-4.2)
- 3.3: Add all error messages per error catalog
- 3.4: Implement verbosity handling (verbose vs non-verbose responses)
- 3.5: Write unit tests for response/error formatting

**Parent Task 4: MCP Server Registration & Testing** (Day 3, 6 hours)
- 4.1: Register `aurora_query` tool in `AuroraMCPServer._register_tools()`
- 4.2: Add tool docstring and parameter descriptions for Claude Desktop
- 4.3: Write integration tests (with real components, mocked LLM)
- 4.4: Test budget tracking integration
- 4.5: Test memory integration (using indexed test codebase)

**Parent Task 5: Documentation & CI/CD** (Day 3-4, 6 hours)
- 5.1: Update `docs/MCP_SETUP.md` with `aurora_query` usage examples
- 5.2: Update `docs/TROUBLESHOOTING.md` with error scenarios
- 5.3: Update `README.md` to mention complete MCP functionality
- 5.4: Run `make quality-check` and fix all issues
- 5.5: Manual testing via Claude Desktop (if available)

**Total Estimated Time**: 3-4 days (28 hours of development work)

### Dependencies

**Internal Dependencies**:
- Requires completed MCP infrastructure (already done in tasks-0006)
- Requires `QueryExecutor` from CLI package (already implemented)
- Requires config loading from `aurora_cli.config` (already implemented)
- Requires budget tracking from `aurora_core` (already implemented)

**External Dependencies**:
- FastMCP library (already installed)
- Anthropic API key for testing (user provides)
- Claude Desktop for manual testing (optional, can be done later)

### Risk Assessment

**Risk 1: CI/CD Failures**
- **Probability**: Medium (user noted this as "major hurdle")
- **Impact**: High (blocks PR merge)
- **Mitigation**:
  - Run all tests locally with Python 3.12 before pushing
  - Mock all external dependencies aggressively
  - Add CI-specific skips for flaky tests
  - Use pytest markers to separate stable vs flaky tests

**Risk 2: Integration with QueryExecutor**
- **Probability**: Low (QueryExecutor already working in CLI)
- **Impact**: Medium (core functionality affected)
- **Mitigation**:
  - Write integration tests early
  - Reuse existing CLI code patterns
  - Test both execution paths (direct LLM, SOAR)

**Risk 3: Claude Desktop Compatibility**
- **Probability**: Low (FastMCP is standard)
- **Impact**: Medium (tool may not appear in Claude Desktop)
- **Mitigation**:
  - Follow FastMCP tool registration patterns exactly
  - Test with MCP inspector tool (if available)
  - Manual testing in Claude Desktop (can be done post-implementation)

**Risk 4: Budget Tracking Accuracy**
- **Probability**: Low (budget tracker already implemented)
- **Impact**: High (user cost concerns)
- **Mitigation**:
  - Add explicit integration tests for budget tracking
  - Verify cost calculations match Anthropic's pricing
  - Add logging for all budget updates

### Acceptance Criteria

The implementation is considered **DONE** when:

1. **Functional**:
   - [ ] `aurora_query` tool is callable from Claude Desktop
   - [ ] Direct LLM execution works for simple queries
   - [ ] SOAR pipeline execution works for complex queries
   - [ ] Auto-escalation correctly chooses execution path
   - [ ] All 6 parameters (query, force_soar, verbose, model, temperature, max_tokens) work

2. **Error Handling**:
   - [ ] All 6 error scenarios return helpful error messages
   - [ ] Each error message includes actionable "To fix this:" guidance
   - [ ] Error responses follow JSON format per FR-4.2

3. **Testing**:
   - [ ] All 50 unit tests pass (100% pass rate)
   - [ ] All 20 integration tests pass (100% pass rate)
   - [ ] Test coverage ≥80% for new code
   - [ ] `make quality-check` passes (all quality gates green)

4. **CI/CD**:
   - [ ] All GitHub Actions workflows pass
   - [ ] No new MyPy errors introduced
   - [ ] No new linting errors
   - [ ] Tests run successfully in CI environment

5. **Documentation**:
   - [ ] MCP_SETUP.md includes `aurora_query` examples
   - [ ] TROUBLESHOOTING.md includes error scenarios
   - [ ] README.md mentions complete MCP functionality
   - [ ] Tool docstring is clear and includes examples

6. **Manual Verification** (optional, can be done post-merge):
   - [ ] Tool appears in Claude Desktop tool list
   - [ ] Simple query returns correct answer
   - [ ] Complex query triggers SOAR pipeline
   - [ ] Error messages display correctly in Claude Desktop

---

## Tech Debt Consideration

Per user requirements:
- "Pick up next tech debt in line by priority"
- "If more than 5 parent tasks, skip tech debt"
- Current implementation plan: **5 parent tasks** (exactly at limit)

**Decision**: **SKIP tech debt for this sprint** to keep focus on core MCP query functionality.

**Rationale**:
- Adding tech debt would exceed 5 parent tasks
- MCP query is foundational and blocking further development
- Tech debt can be addressed in dedicated sprint after MCP is complete

**Next Tech Debt Priority** (for future sprint):
From `docs/TECHNICAL_DEBT.md` (would need to review current debt log):
1. Fix remaining 6 MyPy errors in `aurora_reasoning.llm_client`
2. Implement proper spreading activation for `aurora_related` (currently simplified)
3. Add streaming response support for MCP tools
4. Consolidate logging configuration (currently scattered across modules)

These will be addressed in a dedicated tech debt sprint after MCP query is complete and stable.

---

## Open Questions

### Q1: Progress Streaming
**Question**: Does FastMCP support streaming progress updates to Claude Desktop in real-time?

**Options**:
- A) Yes - implement real-time progress updates during SOAR execution
- B) No - return progress summary at end of execution
- C) Unknown - investigate and decide based on findings

**Impact**: Affects FR-3.3 (progress display format)

**Decision Required By**: Start of Day 2 (before implementing response formatting)

**Recommended Approach**: Investigate FastMCP docs/examples. If unsupported, use approach B (summary at end).

---

### Q2: Memory Scope Configuration
**Question**: Should `aurora_query` support a `memory_scope` parameter to override config?

**Options**:
- A) Yes - add `memory_scope` parameter ("all", "current_project", "none")
- B) No - always use config file setting
- C) Partial - only support "none" to explicitly disable memory

**Impact**: Affects API specification and user flexibility

**Decision Required By**: Start of Day 1 (before implementing parameter validation)

**Recommended Approach**: Option C (support "none" only) for MVP. Option A can be added in v2.

---

### Q3: Response Size Limits
**Question**: Should `aurora_query` truncate very long responses to avoid MCP payload limits?

**Options**:
- A) Yes - truncate responses over 10KB with "..." and suggestion to use CLI
- B) No - return full response regardless of size
- C) Configurable - add `max_response_length` parameter

**Impact**: Affects response formatting and error handling

**Decision Required By**: Start of Day 2 (before implementing response formatting)

**Recommended Approach**: Option B for MVP (no truncation). If MCP payload issues arise, add truncation in patch.

---

### Q4: Cost Estimation Accuracy
**Question**: Should we pre-estimate query cost before execution to warn users?

**Options**:
- A) Yes - estimate cost and warn if >$0.10 (or user-configurable threshold)
- B) No - only track cost after execution
- C) Partial - estimate for SOAR only (direct LLM is cheap enough to not warn)

**Impact**: Affects budget handling and user experience

**Decision Required By**: Start of Day 2 (before implementing budget checking)

**Recommended Approach**: Option C (estimate for SOAR only) - provides value without adding complexity to direct LLM path.

---

### Q5: Concurrent Query Limits
**Question**: Should we limit concurrent queries to prevent budget/resource exhaustion?

**Options**:
- A) Yes - limit to 1 concurrent query per user
- B) Yes - limit to 3 concurrent queries per user
- C) No - allow unlimited concurrent queries

**Impact**: Affects system design and resource management

**Decision Required By**: Start of Day 1 (before implementing query execution)

**Recommended Approach**: Option C for MVP (no limits). Add rate limiting in v2 if needed based on usage patterns.

---

## Appendices

### Appendix A: Command Mapping (CLI to MCP)

Complete mapping of CLI commands to MCP tools:

| CLI Command | MCP Tool | Status | Notes |
|-------------|----------|--------|-------|
| `aur "question"` | `aurora_query` | **MISSING** | This PRD |
| `aur query "question"` | `aurora_query` | **MISSING** | Same as above |
| `aur mem index /path` | `aurora_index` | EXISTS | Implemented in tasks-0006 |
| `aur mem search "text"` | `aurora_search` | EXISTS | Implemented in tasks-0006 |
| `aur stats` | `aurora_stats` | EXISTS | Implemented in tasks-0006 |
| `aur context /path/file.py` | `aurora_context` | EXISTS | Implemented in tasks-0006 |
| `aur related chunk-id` | `aurora_related` | EXISTS | Implemented in tasks-0006 |
| `aur code search "text"` | `aurora_search` | EXISTS | Same as mem search |
| `aur --verify` | N/A | CLI ONLY | Installation health check |
| `aur init` | N/A | CLI ONLY | Configuration setup |

### Appendix B: Configuration Schema Reference

Complete configuration file schema for `~/.aurora/config.json`:

```json
{
  "api": {
    "anthropic_key": "sk-ant-...",
    "default_model": "claude-sonnet-4-20250514",
    "temperature": 0.7,
    "max_tokens": 4000,
    "timeout_seconds": 60
  },
  "query": {
    "auto_escalate": true,
    "complexity_threshold": 0.6,
    "verbosity": "normal",
    "retry_attempts": 3,
    "retry_backoff_base_ms": 100
  },
  "memory": {
    "search_scope": "current_project",
    "max_context_chunks": 10,
    "hybrid_weight_semantic": 0.6,
    "hybrid_weight_activation": 0.4
  },
  "budget": {
    "monthly_limit_usd": 50.0,
    "warning_threshold_percent": 80,
    "cost_estimation_enabled": true
  },
  "logging": {
    "level": "INFO",
    "file": "~/.aurora/logs/mcp.log",
    "max_file_size_mb": 10,
    "backup_count": 5
  }
}
```

### Appendix C: Example Workflows

**Workflow 1: First-Time User**
1. Install AURORA: `pip install aurora-actr[all]`
2. Configure MCP in Claude Desktop (per MCP_SETUP.md)
3. Open Claude Desktop, ask: "Can you help me understand this codebase?"
4. Claude suggests: "Let me index your codebase first"
5. Uses `aurora_index` to index project
6. Then uses `aurora_query` to answer questions about code

**Workflow 2: Power User Analyzing Architecture**
1. User asks complex question in Claude Desktop
2. `aurora_query` assesses complexity (high)
3. Auto-escalates to SOAR pipeline
4. Shows progress: "Retrieving context...", "Decomposing query..."
5. Returns detailed answer with phase trace
6. User sees cost ($0.05) and decides if acceptable

**Workflow 3: User Hits Budget Limit**
1. User asks question in Claude Desktop
2. `aurora_query` checks budget ($49.80 / $50.00)
3. Estimated cost: $0.30 (would exceed)
4. Returns BudgetExceeded error with helpful message
5. User decides to increase limit in config
6. Edits `~/.aurora/config.json`: `"monthly_limit_usd": 100.0`
7. Restarts Claude Desktop (config reloaded)
8. Query succeeds

### Appendix D: Related Documentation

**Internal Documentation** (to be updated):
- `docs/MCP_SETUP.md` - Add `aurora_query` setup and examples
- `docs/TROUBLESHOOTING.md` - Add error scenarios and solutions
- `docs/cli/CLI_USAGE_GUIDE.md` - Reference MCP as alternative interface
- `README.md` - Highlight MCP as primary interface
- `docs/architecture/API_CONTRACTS_v1.0.md` - Add MCP tool contracts

**External References**:
- [FastMCP Documentation](https://github.com/jlowin/fastmcp) - MCP server framework
- [Anthropic API Pricing](https://www.anthropic.com/pricing) - Cost calculations
- [Claude Desktop MCP Guide](https://docs.anthropic.com/claude/docs/model-context-protocol) - Official MCP integration guide

---

## Document Changelog

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-25 | Senior Software Engineer (AI Agent) | Initial PRD creation based on user elicitation |

---

**End of PRD**
