# Feedback Issues from aur init Testing

## ✅ Issue #1: CLAUDE.md Stub Overwrites Content (FIXED)

**Problem**: When CLAUDE.md already exists without Aurora markers, running `aur init --config` overwrites the entire file instead of prepending the stub.

**Status**: **FIXED** in `packages/cli/src/aurora_cli/configurators/base.py:142-146`

**Solution**: Modified `_update_file_with_markers()` to prepend stub when file exists but has no markers, preserving existing content.

---

## ⚠️ Issue #2: Indexing Warnings Not in `aur doctor`

**Problem**: User expected detailed warnings from `aur mem index` to appear in `aur doctor` output.

**Status**: **BY DESIGN** - `aur doctor` checks system health, not indexing-specific warnings.

**Recommendation**: Consider adding an `aur mem status` command that shows:
- Last index time
- Number of files indexed
- Any warnings from last indexing session
- Index health metrics

---

## 🔴 Issue #3: Plans Created in Wrong Location

**Problem**: `aur plan create` creates plans in `~/.aurora/plans/active/` (global user directory) instead of project-local `.aurora/plans/active/`.

**Root Cause**: Config is loading from `~/.aurora/config.json` instead of project-local config.

**Expected Behavior**:
- If in a project with `.aurora/` directory → use project-local plans
- If outside a project → use global `~/.aurora/` directory

**Files to investigate**:
- `packages/cli/src/aurora_cli/config.py` - Config loading logic
- `packages/cli/src/aurora_cli/planning/core.py` - Plan creation logic

---

## ❓ Issue #4: Unexpected Plan Numbering

**Problem**: Plan ID generated as `2042-test-feature` - where does `2042` come from?

**Expected**: Sequential numbering like `0001-test-feature`, `0002-another-feature`, etc.

**Files to investigate**:
- `packages/planning/src/aurora_planning/id_generator.py`
- Check if there are existing plans in `~/.aurora/plans/` causing high numbering

---

## 🔴 Issue #5: `aur mcp` Command Doesn't Exist

**Problem**: User tried `aur mcp` but command doesn't exist.

**Status**: **MISSING COMMAND**

**Current Behavior**:
- MCP servers are configured during `aur init --tools=<tool>`
- No dedicated command to manage/view MCP configuration

**Recommendation**: Add `aur mcp` command with subcommands:
```bash
aur mcp status           # Show configured MCP servers
aur mcp add <tool>       # Add MCP server for a tool
aur mcp remove <tool>    # Remove MCP server
aur mcp test <tool>      # Test MCP server connection
```

---

## Priority Order

1. **HIGH**: Issue #3 (Plans in wrong location) - breaks core workflow
2. **HIGH**: Issue #4 (Plan numbering) - confusing UX
3. **MEDIUM**: Issue #5 (Missing `aur mcp` command) - usability
4. **LOW**: Issue #2 (Warnings in doctor) - nice-to-have
5. **DONE**: Issue #1 (CLAUDE.md overwrite) - fixed

---

## Next Steps

1. Fix plan location logic (Issue #3)
2. Investigate plan numbering (Issue #4)
3. Design and implement `aur mcp` command (Issue #5)
4. Consider adding `aur mem status` command (Issue #2)
