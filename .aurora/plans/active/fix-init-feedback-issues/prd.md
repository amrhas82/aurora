# PRD: Fix aur init Feedback Issues

## Summary

Address critical feedback from `aur init` testing focusing on project-local configuration, sequential plan numbering, enhanced diagnostics, and MCP server management.

## Requirements

### FR-1: Project-Local Configuration (CRITICAL)

All Aurora artifacts MUST be project-local (`./.aurora/`) except budget tracker.

**FR-1.1**: Plans Directory Location
- Plans MUST be created in `./.aurora/plans/active/` when in a project
- Plans MUST NOT be created in `~/.aurora/plans/` when in a project
- Budget tracker MUST remain in `~/.aurora/budget_tracker.json` (global)

**FR-1.2**: Config Loading Priority
- MUST check for `./.aurora/config.json` first (project-local)
- MUST fall back to `~/.aurora/config.json` if no project config
- MUST NOT merge configs (project config wins entirely)

**FR-1.3**: Database and Cache Locations
- Memory database MUST be `./.aurora/memory.db`
- Agent manifest MUST be `./.aurora/cache/agent_manifest.json`
- Logs MUST be in `./.aurora/logs/`

### FR-2: Sequential Plan Numbering

Plan IDs MUST use 4-digit sequential numbering within each project.

**FR-2.1**: Numbering Format
- First plan: `0001-<name>`
- Second plan: `0002-<name>`
- Pattern: `{number:04d}-{kebab-case-name}`

**FR-2.2**: Counting Scope
- MUST count existing plans in project `./.aurora/plans/active/` and `./.aurora/plans/archive/`
- MUST NOT count plans from global `~/.aurora/` directory
- MUST start from 0001 in new projects

**FR-2.3**: Archive Handling
- Archived plans MUST keep their original numbers
- Numbering MUST continue from highest used number (active + archived)

### FR-3: Enhanced Memory Statistics

`aur mem stats` MUST provide actionable diagnostic information.

**FR-3.1**: Error Details
- MUST display files that failed to index
- MUST show error message for each failed file
- MUST limit to first 10 errors by default

**FR-3.2**: Warning Information
- MUST display count of warnings
- MUST show warning types (e.g., "skipped binary files")
- MUST provide brief descriptions

**FR-3.3**: Indexing Metadata
- MUST show last indexing timestamp
- MUST show success/failure rate
- MUST indicate if re-indexing is recommended

**FR-3.4**: Output Format
```
Memory Store Statistics
┌─────────────────────────────────┬──────────────┐
│ Total Chunks                    │ 1,779        │
│ Total Files                     │ 118          │
│ Database Size                   │ 7.64 MB      │
│ Last Indexed                    │ 2 hours ago  │
│ Success Rate                    │ 95% (113/118)│
└─────────────────────────────────┴──────────────┘

Indexing Issues:
  ⚠ 5 files failed to index
  ⚠ 12 warnings during indexing

Failed Files:
  • src/broken.py: SyntaxError: invalid syntax
  • lib/test.js: Unsupported file type
  ... (3 more, use --verbose for all)

Warnings:
  • 10 binary files skipped
  • 2 files too large (>1MB)

💡 Run 'aur mem index .' to re-index
```

### FR-4: Message Consistency

All indexing-related messages MUST reference `aur mem stats`, not `aur doctor`.

**FR-4.1**: Message Pattern
- BEFORE: `"Run 'aur doctor' to check setup"`
- AFTER: `"Run 'aur mem stats' to check indexing status"`

**FR-4.2**: Scope
- All memory/indexing error messages
- All planning warnings about missing context
- All initialization messages about indexing

**FR-4.3**: `aur doctor` Reserved For
- System health checks only
- API key validation
- Database schema validation
- Git repository detection

### FR-5: Tool Integration Health Checks

Extend `aur doctor` with slash command and MCP server diagnostics.

**FR-5.1**: New Check Category - TOOL INTEGRATION
```bash
aur doctor

# Output includes new section:
TOOL INTEGRATION
  ✓ Claude slash commands installed (7/7)
  ✗ Cursor slash commands missing (0/7)
  ✓ Claude MCP server configured
  ✗ Cline MCP server not configured
  ⚠ Continue MCP config invalid

Suggestions:
  • Run 'aur init --config --tools=cursor' to install slash commands
  • Run 'aur init --config --tools=cline,continue' to fix MCP servers
```

**FR-5.2**: Slash Command Detection
- MUST detect slash commands for all 20 supported AI tools
- MUST show count of installed commands (e.g., "7/7")
- MUST distinguish "not configured" vs "partially configured"
- MUST check expected file paths per tool:
  - Claude: `.claude/commands/aur/*.md`
  - Cursor: `.cursorrules/aur/*.toml`
  - Gemini: `.gemini/commands/aur/*.md`
  - etc.

**FR-5.3**: MCP Server Detection
- MUST detect MCP configuration for 4 MCP-capable tools
- MUST validate JSON structure
- MUST check Aurora MCP server entry exists
- MUST report status: "configured" | "not configured" | "invalid"

**FR-5.4**: Actionable Suggestions
- MUST suggest `aur init --config --tools=<tool>` to fix issues
- MUST list all tools that need fixing
- MUST NOT create new commands (reuse existing `aur init --config`)

**FR-5.5**: Integration with Existing Checks
- MUST appear as 5th section (after CONFIGURATION)
- MUST follow same status format (✓/✗/⚠)
- MUST contribute to overall pass/warning/fail count

## Non-Functional Requirements

### NFR-1: Backward Compatibility
- Existing global configs MUST continue to work
- Projects without `./.aurora/` MUST use global config
- Plan archives MUST NOT break with new numbering

### NFR-2: Performance
- `aur mem stats` MUST complete in <1s for databases up to 10K chunks
- Config loading MUST add <100ms overhead
- MCP commands MUST respond in <500ms

### NFR-3: Usability
- Error messages MUST be actionable
- `aur mcp` MUST have clear help text
- Plan numbering MUST be visible in all listings

### NFR-4: Reliability
- Config changes MUST NOT corrupt existing data
- Plan numbering MUST handle concurrent creation gracefully
- MCP operations MUST be idempotent

## Acceptance Criteria

### AC-1: Project Isolation Works
```bash
cd /tmp/project-a
aur init
aur plan create "Feature A"
test -f ./.aurora/plans/active/0001-feature-a/plan.md
! test -f ~/.aurora/plans/active/0001-feature-a/plan.md
```

### AC-2: Sequential Numbering Works
```bash
cd /tmp/project-b
aur init
aur plan create "First"   # 0001-first
aur plan create "Second"  # 0002-second
aur plan create "Third"   # 0003-third
aur plan list | grep -E "0001|0002|0003"
```

### AC-3: Stats Enhancement Works
```bash
aur mem index .
aur mem stats
# Output includes:
# - Failed files (if any)
# - Warnings (if any)
# - Last indexed timestamp
# - Success rate
```

### AC-4: Messages Are Consistent
```bash
aur plan create "Test" 2>&1 | grep "aur mem stats"
! aur plan create "Test" 2>&1 | grep "aur doctor"
```

### AC-5: Tool Integration Checks Work
```bash
aur doctor
# Output includes TOOL INTEGRATION section
# Shows slash command status for installed tools
# Shows MCP server status for 4 MCP-capable tools
# Provides actionable suggestions to fix issues
```

## Out of Scope

- MCP server implementation (already exists)
- New `aur mcp` command (use `aur doctor` + `aur init --config` instead)
- Changing plan file structure
- Migrating existing plans to new numbering
- Multi-project plan management
- Plan numbering customization
- Automatic migration of global plans to project-local

## Migration Strategy

### For Existing Users

1. **No breaking changes**: Existing global configs continue to work
2. **Opt-in**: Users can create `./.aurora/` to get project-local behavior
3. **Budget tracker**: Remains global (no migration needed)
4. **Plan numbering**: Only affects NEW plans in NEW projects

### For Existing Plans

- Plans keep their current IDs (no renumbering)
- New plans in same project continue from current highest number
- Archived plans don't affect numbering in other projects

## Technical Notes

### Config Resolution Algorithm

```python
def load_config():
    # 1. Check project-local
    if Path("./.aurora/config.json").exists():
        return load_from("./.aurora/config.json")

    # 2. Check environment
    if "AURORA_HOME" in os.environ:
        path = f"{os.environ['AURORA_HOME']}/config.json"
        if Path(path).exists():
            return load_from(path)

    # 3. Check global default
    if Path("~/.aurora/config.json").expanduser().exists():
        return load_from("~/.aurora/config.json")

    # 4. Use built-in defaults
    return Config()
```

### Plan ID Generation Algorithm

```python
def generate_plan_id(name: str, plans_dir: Path) -> str:
    # Get all existing IDs from active and archive
    active_ids = get_plan_ids(plans_dir / "active")
    archive_ids = get_plan_ids(plans_dir / "archive")

    # Find highest number
    max_num = max([
        int(id.split("-")[0])
        for id in (active_ids + archive_ids)
        if id.split("-")[0].isdigit()
    ], default=0)

    # Generate next ID
    next_num = max_num + 1
    return f"{next_num:04d}-{kebab_case(name)}"
```

## Dependencies

- Existing MCP configurators (no changes needed)
- Existing config system (minor changes)
- Existing plan system (minor changes)

## Timeline Estimate

- Subgoal 1 (Config): 4-6 hours (includes testing)
- Subgoal 2 (Numbering): 2-3 hours
- Subgoal 3 (Stats): 3-4 hours
- Subgoal 4 (Messages): 1-2 hours (search & replace)
- Subgoal 5 (MCP CLI): 4-5 hours

**Total**: 14-20 hours of development + testing
