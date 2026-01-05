# Plan: Fix aur init Feedback Issues

## Goal

Address all user feedback issues from `aur init` testing to ensure:
1. Project-local configuration and plans (not global)
2. Sequential plan numbering (0001, 0002, etc.)
3. Enhanced `aur mem stats` with error details
4. Proper message referencing `aur mem stats` instead of `aur doctor`
5. New `aur mcp` CLI command for MCP server management

## Context

User tested `aur init` and found 5 issues:
1. ✅ CLAUDE.md stub overwrites content (FIXED)
2. ⚠️ `aur mem index` suggests checking `aur doctor` instead of `aur mem stats`
3. 🔴 Plans created in `~/.aurora/` instead of `./.aurora/` (project-local)
4. 🔴 Plan numbering uses high numbers (e.g., 2042) instead of sequential (0001)
5. 🔴 No `aur mcp` command to manage MCP servers

## Subgoals

### 1. Fix Config and Directory Resolution (@full-stack-dev)

**Scope**: Ensure all paths default to project-local `./.aurora/` except budget tracker

**Changes**:
- Config loading should prioritize project-local over global
- Plans should always be in project `./.aurora/plans/`
- Only `budget_tracker_path` should be global (`~/.aurora/budget_tracker.json`)
- Agent manifest can be project-local (`./.aurora/cache/agent_manifest.json`)

**Files**:
- `packages/cli/src/aurora_cli/config.py` - Already has correct defaults
- `packages/cli/src/aurora_cli/planning/core.py` - Verify uses project config
- Need to ensure config loading works correctly

**Acceptance Criteria**:
- [ ] Running `aur plan create` in a project creates plans in `./.aurora/plans/active/`
- [ ] Budget tracker remains in `~/.aurora/budget_tracker.json`
- [ ] All other artifacts (memory.db, logs, cache) use project `./.aurora/`

### 2. Fix Plan ID Sequential Numbering (@full-stack-dev)

**Scope**: Use sequential numbering 0001, 0002, 0003 instead of year-based or random

**Current Behavior**: Plan IDs like `2042-test-feature`
**Expected Behavior**: Plan IDs like `0001-test-feature`, `0002-another-feature`

**Investigation**:
- Check `packages/planning/src/aurora_planning/id_generator.py`
- Likely counting existing plans in global directory
- Should count plans in project directory only

**Acceptance Criteria**:
- [ ] First plan in new project: `0001-<name>`
- [ ] Second plan: `0002-<name>`
- [ ] Numbering continues sequentially in project
- [ ] Different projects have independent numbering

### 3. Enhance `aur mem stats` with Error Details (@full-stack-dev)

**Scope**: Add detailed error/warning information to `aur mem stats` output

**Current Output**: Basic statistics only
**Enhanced Output**: Should include:
- Files that failed to index (with error messages)
- Warnings during indexing (with brief descriptions)
- Last indexing timestamp
- Success/error rate

**Files**:
- `packages/cli/src/aurora_cli/commands/memory.py` - `stats` subcommand
- `packages/cli/src/aurora_cli/memory_manager.py` - Store error/warning metadata

**Acceptance Criteria**:
- [ ] `aur mem stats` shows failed files with error snippets
- [ ] Warning count and brief descriptions displayed
- [ ] Clear indication if indexing had issues
- [ ] Suggests re-running `aur mem index` if errors present

### 4. Update Messages to Reference `aur mem stats` (@full-stack-dev)

**Scope**: Change all "check aur doctor" messages to "check aur mem stats" for indexing context

**Files to Update** (from grep results):
- `packages/cli/src/aurora_cli/planning/errors.py:85`
- `packages/cli/src/aurora_cli/planning/memory.py:53`
- `packages/cli/src/aurora_cli/planning/core.py:1098`
- `packages/cli/src/aurora_cli/planning/core.py:1177`
- `packages/cli/src/aurora_cli/errors.py:340,383,399,523,578`
- `packages/cli/src/aurora_cli/commands/memory.py:228,275,344`
- Any other locations referencing `aur doctor` in indexing context

**Pattern**:
- BEFORE: `"Run 'aur doctor' to check setup"`
- AFTER: `"Run 'aur mem stats' to check indexing status"`

**Acceptance Criteria**:
- [ ] All memory/indexing related errors suggest `aur mem stats`
- [ ] `aur doctor` only referenced for system health checks
- [ ] Consistent messaging across all commands

### 5. Add Tool Integration Checks to `aur doctor` (@full-stack-dev)

**Scope**: Extend `aur doctor` with MCP and slash command diagnostics

**Rationale**: Reuse existing `aur doctor` instead of creating new `aur mcp` command. Fixes via `aur init --config`.

**New Check Category**: TOOL INTEGRATION
```bash
aur doctor

# Output adds:
TOOL INTEGRATION
  ✓ Claude slash commands installed
  ✗ Cursor slash commands missing
  ✓ Claude MCP server configured
  ✗ Cline MCP server not configured
  ⚠ Continue MCP config invalid

Suggestions:
  • Run 'aur init --config --tools=cursor' to fix slash commands
  • Run 'aur init --config --tools=cline,continue' to fix MCP servers
```

**Checks to Add**:
1. **Slash Command Checks**: For each AI tool, check if slash command files exist
   - Claude: `.claude/commands/aur/*.md` (7 commands)
   - Cursor: `.cursorrules/aur/*.toml` (7 commands)
   - Gemini: `.gemini/commands/aur/*.md` (7 commands)
   - etc. for all 20 tools

2. **MCP Server Checks**: For MCP-capable tools (Claude, Cursor, Cline, Continue)
   - Check if config file exists
   - Validate JSON structure
   - Check Aurora MCP server entry exists

**Files to Modify**:
- `packages/cli/src/aurora_cli/health_checks.py` - Add `ToolIntegrationChecks` class
- `packages/cli/src/aurora_cli/commands/doctor.py` - Add tool integration section
- Reuse existing slash/MCP registry for detection

**Acceptance Criteria**:
- [ ] `aur doctor` shows slash command status for all configured tools
- [ ] `aur doctor` shows MCP server status for 4 MCP-capable tools
- [ ] Suggests `aur init --config --tools=<tool>` to fix issues
- [ ] Reports tools as "not configured" vs "misconfigured" vs "configured"
- [ ] Clear, actionable suggestions for fixing each issue

## Success Criteria

1. **Project Isolation**: All project artifacts stay in `./.aurora/` except budget tracker
2. **Predictable IDs**: Plan numbering starts at 0001 and increments sequentially
3. **Better Diagnostics**: `aur mem stats` provides actionable error information
4. **Clear Messaging**: All indexing messages reference `aur mem stats`, not `aur doctor`
5. **Tool Health Checks**: `aur doctor` shows slash command and MCP server status with fix suggestions

## Testing Strategy

1. **Fresh Project Test**:
   ```bash
   cd /tmp/test-fresh
   git init
   aur init --tools=claude
   aur plan create "First feature"  # Should be 0001-first-feature
   ls .aurora/plans/active/         # Should exist here, not ~/.aurora/
   ```

2. **MCP Command Test**:
   ```bash
   aur mcp                    # Should show status
   aur mcp add cursor         # Should configure Cursor
   aur mcp test cursor        # Should validate
   ```

3. **Stats Enhancement Test**:
   ```bash
   aur mem index .
   aur mem stats             # Should show detailed info
   ```

## Dependencies

- No external dependencies
- All changes within Aurora CLI codebase
- Reuses existing configurators and infrastructure

## Implementation Order

1. **Subgoal 1** (Config/Directory) - CRITICAL, blocks everything else
2. **Subgoal 2** (Plan Numbering) - Depends on Subgoal 1
3. **Subgoal 4** (Message Updates) - Independent, can be done anytime
4. **Subgoal 3** (Stats Enhancement) - Independent
5. **Subgoal 5** (MCP Command) - Independent, but nice to have with proper config

## Risk Assessment

- **Low Risk**: Message updates (Subgoal 4)
- **Medium Risk**: Stats enhancement (Subgoal 3), MCP command (Subgoal 5)
- **High Risk**: Config resolution (Subgoal 1) - affects core behavior
- **Medium Risk**: Plan numbering (Subgoal 2) - changes ID generation

## Notes

- Config defaults already look correct (`./.aurora/` paths)
- Issue likely in config loading logic prioritizing global over local
- Budget tracker is ONLY file that should remain global
- MCP command should mirror structure of existing `aur mem`, `aur plan` commands
