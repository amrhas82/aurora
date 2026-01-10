# MCP Tool Deprecation

**Related**: PRD-0024
**Version**: 1.2.0
**Date**: 2026-01-06

## Architecture Rationale

### Why Deprecation Was Needed

The deprecation of three MCP tools (`aurora_query`, `aurora_search`, `aurora_get`) addresses critical user experience and technical issues:

#### 1. Token Overhead and Cost
- **MCP Tool Pattern**: LLM must generate JSON tool call → Parse JSON → Execute → Return JSON → Parse result
- **Slash Command Pattern**: Direct formatting and execution, no JSON serialization overhead
- **Impact**: Slash commands use ~50% fewer tokens per operation, reducing API costs significantly

#### 2. User Experience Issues
- **Opaque Decision Making**: Users couldn't predict when LLM would choose MCP tools vs native commands
- **Formatting Loss**: MCP tools returned raw JSON, requiring additional LLM processing for readable output
- **Control Gap**: No way to explicitly request specific tool behavior

#### 3. Code Complexity
- **Dual Implementations**: Maintaining both MCP tools and CLI commands created redundancy
- **Configuration Burden**: 20+ MCP configurator files needed updates for every tool change
- **Testing Overhead**: Separate test suites for MCP and CLI paths

### Benefits of Slash Commands

#### Direct Formatting
Slash commands return pre-formatted output optimized for Claude Code's context window:
```
/aur:search "authentication"
# Returns: Markdown table with results, ready for LLM consumption
# No JSON parsing, no additional formatting step
```

#### Explicit Control
Users can now explicitly choose search behavior:
- `/aur:search "query"` - Formatted search results with session caching
- `aur mem search "query"` - CLI output for scripts/automation
- `aur soar "query"` - Full multi-turn SOAR pipeline

#### Lower Token Usage
Example token comparison:
```
MCP Tool Approach:
- Tool call JSON: ~150 tokens
- Tool result JSON: ~500 tokens
- Format for display: ~200 tokens
Total: ~850 tokens

Slash Command Approach:
- Command invocation: ~50 tokens
- Pre-formatted result: ~300 tokens
Total: ~350 tokens

Savings: ~60% reduction
```

### Infrastructure Preservation Strategy: "Keep Dormant"

Rather than deleting MCP infrastructure, we preserve it in a dormant state. This approach provides:

#### 1. Future Flexibility
- Agent-to-agent communication patterns may emerge
- IDE integrations may benefit from MCP protocol
- Enterprise use cases may require MCP for compliance/auditing

#### 2. Rollback Safety
- Feature flag (`mcp.enabled: true`) enables instant re-activation
- No code changes needed for rollback
- All configurators remain functional

#### 3. Infrastructure Value
- 20+ MCP configurators represent significant engineering investment
- 9 SOAR phase handlers serve both MCP and CLI use cases
- Session cache infrastructure may benefit future tools

#### Preserved Components
- **All 20+ MCP configurator files** in `packages/cli/src/aurora_cli/configurators/mcp/`
- **All 9 SOAR phase handler files** in `packages/soar/src/aurora_soar/phases/`
- **Session cache infrastructure** in `src/aurora_mcp/tools.py`
- **Helper methods and utilities** throughout MCP codebase
- **All unit tests** (integration tests made skippable via environment variable)

#### Removed Components
- **3 MCP tool registrations**: `aurora_query`, `aurora_search`, `aurora_get` in `server.py`
- **Tool implementations** in `tools.py` (cache and helpers preserved)
- **MCP checks** from `aur doctor` command
- **Default MCP configuration** in `aur init` (now requires `--enable-mcp` flag)

### Re-enablement Path

Re-enabling MCP requires minimal effort:

#### For Testing/Development
```bash
# Option 1: Flag at init time
aur init --enable-mcp --tools=claude

# Option 2: Manual config edit
# Edit ~/.aurora/config.json:
{
  "mcp": {
    "enabled": true
  }
}

# Then run init with MCP
aur init --enable-mcp --tools=claude
```

#### For Production Use
If future requirements justify MCP re-enablement:
1. Set `mcp.enabled: true` in global config
2. Re-implement the 3 deprecated tools (code preserved in git history)
3. Update configurators to include new tools
4. Enable MCP checks in `aur doctor`

**Estimated effort**: 2-4 hours (all infrastructure preserved)

## Preserved vs Removed Components

### Removed Components

#### MCP Tool Registrations (server.py)
- `aurora_query()` tool registration and handler
- `aurora_search()` tool registration and handler
- `aurora_get()` tool registration and handler

**Total removed**: 3 tool registrations (~150 lines of code)

#### MCP Tool Implementations (tools.py)
- `aurora_search()` method implementation
- `aurora_get()` method implementation

**Total removed**: 2 method implementations (~160 lines of code)

#### MCP Configuration and Checks
- MCP checks section in `aur doctor` output
- `MCPFunctionalChecks` instantiation and execution in `doctor.py`
- Default MCP configuration in `aur init` (now opt-in via `--enable-mcp`)

### Preserved Components

#### MCP Configurators (20+ files)
All configurator files in `packages/cli/src/aurora_cli/configurators/mcp/` remain functional:
- `claude.py` - Claude Code MCP configuration
- `cursor.py` - Cursor IDE MCP configuration
- `cline.py` - Cline extension MCP configuration
- `continue_.py` - Continue extension MCP configuration
- `windsurf.py` - Windsurf IDE MCP configuration
- `zed.py` - Zed editor MCP configuration
- 14+ additional configurators

**Update**: Tool permissions lists updated to reflect 6 remaining tools (down from 9)

#### SOAR Phase Handlers (9 files)
All phase handler files in `packages/soar/src/aurora_soar/phases/` preserved:
- `assess.py` - Context assessment phase
- `collect.py` - Information collection phase
- `decompose.py` - Query decomposition phase
- `record.py` - Result recording phase
- `respond.py` - Response generation phase
- `retrieve.py` - Memory retrieval phase
- `route.py` - Query routing phase
- `synthesize.py` - Information synthesis phase
- `verify.py` - Result verification phase

**Reason**: These serve `SOAROrchestrator` library use (Python API), not just `aur soar` command (bash orchestration)

#### Session Cache Infrastructure (tools.py)
- `_last_search_results` session attribute
- `_last_search_timestamp` session attribute
- Session cache expiration logic (10-minute TTL)

**Reason**: May be used by future MCP tools or slash command implementations

#### Helper Methods (tools.py)
- `_ensure_initialized()` - Database initialization check
- `_format_error()` - Error message formatting
- `_validate_index()` - Index validation logic

**Reason**: Reusable utilities for future tools

#### Unit Tests
All unit tests preserved in `tests/unit/`:
- `test_config_mcp.py` - Config flag parsing tests
- `tests/unit/cli/configurators/mcp/*.py` - Configurator tests
- `tests/unit/soar/test_phase_*.py` - SOAR phase handler tests

**Integration tests**: Made skippable via `@pytest.mark.skipif(not os.environ.get('AURORA_ENABLE_MCP'))` decorator

## Re-enablement Guide

### Step 1: Enable via Configuration Flag

Edit your Aurora configuration file at `~/.aurora/config.json`:

```json
{
  "mcp": {
    "enabled": true
  }
}
```

Or use the CLI flag during initialization:

```bash
aur init --enable-mcp --tools=claude
```

### Step 2: Verify MCP Configuration Created

After running `aur init --enable-mcp`, verify MCP configuration files exist:

```bash
# For Claude Code
cat ~/.claude/plugins/aurora/.mcp.json

# For other tools (Cursor, Cline, etc.)
# Check tool-specific configuration directories
```

Expected configuration content:
```json
{
  "mcpServers": {
    "aurora": {
      "command": "python",
      "args": ["-m", "aurora_mcp.server"],
      "cwd": "/path/to/aurora"
    }
  }
}
```

### Step 3: Verify Available Tools

The re-enabled MCP server provides 6 tools (deprecated tools remain unavailable):

**Available Tools**:
- `aurora_index` - Index codebase for search
- `aurora_context` - Get context about indexed files
- `aurora_related` - Find related code chunks
- `aurora_list_agents` - List available agents
- `aurora_search_agents` - Search agent definitions
- `aurora_show_agent` - Show agent details

**Unavailable Tools** (use slash commands instead):
- ~~`aurora_query`~~ → Use `/aur:search` or `aur soar`
- ~~`aurora_search`~~ → Use `/aur:search`
- ~~`aurora_get`~~ → Use `/aur:get`

### Step 4: Use via MCP Client

With MCP enabled, tools are automatically available in your Claude Code CLI sessions:

```bash
# Start Claude Code
claude

# Tools available via natural language
> "Search the codebase for authentication logic"
# Claude may choose to use aurora_search_agents or aurora_context

> "Show me the details of the qa-test-architect agent"
# Claude may use aurora_show_agent
```

### Step 5: Disable MCP (Return to Default)

To return to slash command workflow:

```json
// Edit ~/.aurora/config.json
{
  "mcp": {
    "enabled": false
  }
}
```

Then run `aur init` without the `--enable-mcp` flag.

## Future MCP Plans

### Potential Future Use Cases

While deprecated for primary user interaction, MCP may return for:

#### 1. Agent-to-Agent Communication
Future multi-agent architectures may benefit from MCP's structured protocol:
- Master orchestrator coordinates specialist agents
- Agents communicate via MCP tool calls
- Structured JSON provides type safety and validation

#### 2. IDE Deep Integrations
IDE vendors may prefer MCP for:
- Standardized protocol across editors
- Type-safe tool definitions
- Automatic UI generation from tool schemas

#### 3. Enterprise Audit Requirements
Organizations may need MCP for:
- Structured audit logs (JSON-formatted tool calls)
- Compliance tracking (who called what, when)
- Usage analytics (tool call frequency, patterns)

#### 4. Programmatic Access
Library users (not CLI users) may prefer MCP for:
- Python API access to Aurora tools
- Type-checked tool invocations
- Structured result parsing

### Why Infrastructure Is Preserved

The "Keep Dormant" strategy ensures we can quickly pivot to MCP if:

1. **User Demand**: Community requests MCP for specific use cases
2. **Technical Advantages**: New MCP features make it compelling again
3. **Ecosystem Shifts**: Industry standardizes on MCP protocol
4. **Enterprise Requirements**: Customers require MCP for compliance

**Re-enablement effort**: 2-4 hours (all infrastructure functional)

### Evaluation Criteria for Re-introducing MCP Tools

We would consider re-implementing the 3 deprecated tools if:

#### Token Efficiency Improves
- MCP protocol reduces overhead to match slash commands
- LLM providers optimize MCP tool call handling
- Claude gains native MCP parsing (bypassing JSON serialization)

#### User Experience Gap
- Users demonstrate clear need for programmatic tool access
- IDE integrations require MCP-specific features
- Agent-to-agent patterns become standard

#### Maintenance Burden Decreases
- MCP provides auto-configuration across all supported tools
- Configurator count reduced via universal MCP registry
- Testing simplified through protocol standardization

**Decision Authority**: Product and Engineering leads will evaluate against these criteria quarterly.

## Technical Notes

### Dual SOAR Orchestration Approaches

Aurora supports two SOAR orchestration patterns:

#### Bash Orchestration (aur soar command)
- **Command**: `aur soar "your question"`
- **Implementation**: Bash script orchestrates 5 separate Claude CLI calls
- **Use Case**: Terminal usage, quick queries, CLI automation
- **Token Efficiency**: High (each call independent, minimal context passing)

#### Python Orchestration (SOAROrchestrator library)
- **Usage**: `from aurora_soar import SOAROrchestrator`
- **Implementation**: `SOAROrchestrator` class coordinates phase handlers
- **Use Case**: Programmatic integration, IDE plugins, Python applications
- **Token Efficiency**: Lower (full context maintained across phases)

**Note**: The 9 SOAR phase handler files serve the Python library use case and must be preserved.

### Configuration Schema

MCP enablement controlled via config schema:

```python
# packages/cli/src/aurora_cli/config.py
@dataclass
class Config:
    mcp_enabled: bool = False
    # ... other fields

CONFIG_SCHEMA = {
    "mcp": {
        "type": "object",
        "properties": {
            "enabled": {"type": "boolean", "default": False}
        }
    }
}
```

### Rollback Options

Three rollback mechanisms available (in order of speed):

#### Option 1: Feature Flag (Fastest)
```bash
# Edit config
# Set mcp.enabled: true
aur init --enable-mcp
# MCP re-enabled in < 1 minute
```

#### Option 2: Git Checkout Tag (Complete Revert)
```bash
git checkout mcp-deprecation-baseline
# Full revert to pre-deprecation state
```

#### Option 3: Git Revert Commits (Preserve History)
```bash
git log --oneline feature/mcp-deprecation
git revert <commit-range>
# Revert changes while preserving commit history
```

See `docs/ROLLBACK.md` for detailed procedures.

## References

- **PRD**: `tasks/tasks-0024-prd-mcp-tool-deprecation.md`
- **Migration Guide**: `docs/MIGRATION.md`
- **Rollback Procedures**: `docs/ROLLBACK.md`
- **Command Documentation**: `docs/COMMANDS.md`

## Version History

- **v1.2.0** (2026-01-06): Initial MCP deprecation
  - Removed 3 MCP tools (aurora_query, aurora_search, aurora_get)
  - Preserved all infrastructure for future use
  - Added `--enable-mcp` flag for testing/development
