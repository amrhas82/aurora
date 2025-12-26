# Archived Tests: MCP Simplification (2025-01)

## Why Archived

These tests were archived as part of PRD-0008 (MCP aurora_query Simplification).
The functionality they tested was removed because:

1. MCP tools no longer call LLM APIs directly
2. API key handling removed from MCP context
3. Budget enforcement moved to CLI-only
4. Retry logic for API calls no longer needed
5. Auto-escalation between direct LLM and SOAR removed from MCP
6. SOAR pipeline execution removed from MCP tools

**Key Principle**: MCP tools (running inside Claude Code CLI) do NOT need API keys because Claude Code CLI itself IS the LLM. MCP tools should only perform retrieval and return structured context for the host LLM to reason about.

## What Was Tested

The following test classes were archived:

- **TestAPIKeyHandling**: API key loading from ANTHROPIC_API_KEY env var and config.json
- **TestBudgetEnforcement**: Monthly budget limits and cost tracking for API calls
- **TestAutoEscalation**: Auto-escalation from direct LLM to SOAR pipeline based on complexity
- **TestRetryLogic**: Exponential backoff retry for transient API errors (429, 500, timeouts)
- **TestMemoryGracefulDegradation**: Graceful degradation when memory store unavailable
- **TestErrorLogging**: Error logging to mcp.log for LLM API failures
- **TestProgressTracking**: SOAR 9-phase progress tracking for verbose mode
- **TestEnhancedVerbosity**: Verbosity modes (quiet, normal, verbose) for SOAR execution

These tests covered approximately 800 lines of test code validating:
- LLM API integration (Anthropic Claude)
- Cost tracking and budget enforcement
- Retry mechanisms with exponential backoff
- Auto-escalation heuristics
- SOAR pipeline orchestration
- Error handling for API failures

## When Archived

- **Date**: 2025-12-26
- **PRD**: `/home/hamr/PycharmProjects/aurora/tasks/0008-prd-mcp-aurora-query-simplification.md`
- **Task List**: `/home/hamr/PycharmProjects/aurora/tasks/0008-tasks-mcp-aurora-query-simplification.md`
- **Commit**: [To be filled after archival]

## Architecture Change

### Before (Removed)
```
MCP aurora_query → API Key Check → Budget Check → Complexity Assessment
                                                   ↓
                                         Direct LLM ← → SOAR Pipeline
                                                   ↓
                                          LLM-Generated Answer
```

### After (New)
```
MCP aurora_query → Retrieve Chunks → Assess Complexity (heuristic)
                                            ↓
                                   Return Structured Context
                                            ↓
                              Claude Code CLI (host LLM) reasons about context
```

## Reference

These tests may be useful if:
- Understanding the original aurora_query behavior with LLM integration
- Debugging the CLI `aur query` command (which still uses LLM calls and needs API keys)
- Reviewing the SOAR pipeline integration patterns
- Understanding budget enforcement and cost tracking logic

**Note**: The CLI in `packages/cli/` still requires API keys and uses the full LLM integration. This archival only affects MCP tools, not CLI commands.

## Related Files

- **Production**: `src/aurora/mcp/tools.py` (simplified after archival)
- **CLI Reference**: `packages/cli/src/aurora_cli/commands/query.py` (unchanged, still uses LLM)
- **New Tests**: `tests/unit/mcp/test_aurora_query_simplified.py` (simplified behavior)
