# Fix aur init Feedback Issues - Summary

## What Changed from Original Plan

### Original Issue #5: Create `aur mcp` Command
**REJECTED** - Don't create new command

### New Approach: Extend `aur doctor`
**APPROVED** - Reuse existing commands, no bloat

## Rationale

1. **No Command Bloat**: Don't add `aur mcp` when `aur doctor` + `aur init --config` can handle it
2. **Consistent UX**: `aur doctor` diagnoses, `aur init --config` fixes
3. **Code Reuse**: Leverage existing MCP and slash command infrastructure
4. **Simpler Mental Model**: Users don't need to learn a new command

## Implementation Summary

### 5 Core Fixes

1. ✅ **CLAUDE.md Stub Preserves Content** (DONE)
   - Prepends stub instead of overwriting

2. 🔴 **Project-Local Everything** (CRITICAL)
   - Plans in `./.aurora/plans/` not `~/.aurora/plans/`
   - Only budget tracker stays global

3. 🔴 **Sequential Plan Numbering** (HIGH PRIORITY)
   - `0001-name`, `0002-name`, etc.
   - Not `2042-name`

4. ⚠️ **Enhanced Memory Stats** (MEDIUM)
   - `aur mem stats` shows errors/warnings from indexing
   - All indexing messages reference `aur mem stats` not `aur doctor`

5. ⚠️ **Tool Integration in Doctor** (MEDIUM)
   - `aur doctor` checks slash commands (all 20 tools)
   - `aur doctor` checks MCP servers (4 MCP-capable tools)
   - Suggests `aur init --config --tools=<tool>` to fix

## User Workflow

### Problem: Broken MCP/Slash Commands
```bash
# Check what's wrong
aur doctor
# Output shows:
#   ✗ Cursor slash commands missing (0/7)
#   ⚠ Continue MCP config invalid
#
# Suggestion: Run 'aur init --config --tools=cursor,continue'

# Fix the issues
aur init --config --tools=cursor,continue

# Verify fixed
aur doctor
# Output shows:
#   ✓ Cursor slash commands installed (7/7)
#   ✓ Continue MCP server configured
```

No new command needed!

## Estimated Effort (Updated)

| Task | Original | New | Change |
|------|----------|-----|--------|
| Config/Directory | 4-6h | 4-6h | Same |
| Plan Numbering | 2-3h | 2-3h | Same |
| Stats Enhancement | 3-4h | 3-4h | Same |
| Message Updates | 1-2h | 1-2h | Same |
| MCP Command | 4-5h | **REMOVED** | -4-5h |
| Doctor Integration | - | **2-3h** | +2-3h |
| **TOTAL** | **14-20h** | **12-18h** | **-2h saved** |

## Benefits of Simpler Approach

1. **Less Code**: No new command module, less to maintain
2. **Better UX**: One tool for diagnosis (`aur doctor`), one tool for fixing (`aur init --config`)
3. **Faster Implementation**: 2 hours less development time
4. **Easier Testing**: Fewer integration points
5. **More Discoverable**: Users already know `aur doctor`

## Next Steps

1. Review and approve this simplified approach ✓
2. Implement Task 1 (Config) - CRITICAL PATH
3. Implement Task 2 (Numbering) - Depends on Task 1
4. Implement Tasks 3-5 in parallel
5. Integration testing
6. Ship it!
