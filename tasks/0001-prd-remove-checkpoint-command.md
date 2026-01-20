# PRD: Complete Removal of aur:checkpoint Slash Command

## Plan ID
`0001-remove-checkpoint-command`

## Summary

Remove the `aur:checkpoint` slash command from Aurora's tool integration system (20 tools), including template removal, configurator updates, and cleanup of checkpoint-related infrastructure. This change aligns Aurora's surface area with its strategic focus on planning and execution oversight.

## Problem Statement

**Current State:**
- Aurora generates 6 slash commands for 20 tools: `search`, `get`, `plan`, `checkpoint`, `implement`, `archive`
- The `checkpoint` command was feature creep - not part of Aurora's core mission
- The command name causes confusion with Claude Code's native checkpoint/rewind feature
- The functionality has been moved to "stash" as part of standard slash commands
- Checkpoint is unused by the user community

**Pain Points:**
1. **Name collision**: Confusing with Claude Code's existing checkpoint/rewind functionality
2. **Unused feature**: No active usage, adding maintenance burden
3. **Feature creep**: Not aligned with Aurora's strategic focus on planning and execution
4. **Alternative exists**: Functionality moved to "stash" in standard slash commands
5. **Command clutter**: Users see 6 commands when only 5 are needed

## Proposed Solution

**Complete removal of checkpoint infrastructure:**

1. **Template Removal**: Remove `CHECKPOINT_TEMPLATE` and `checkpoint` entry from `slash_commands.py`
2. **Configurator Updates**: Remove checkpoint file paths from all 20 tool configurators
3. **Config Cleanup**: Remove checkpoint-related configuration options if any exist
4. **Code Cleanup**: Remove or deprecate checkpoint implementation code in `aurora_cli`
5. **Documentation Updates**: Update all guides to reflect 5 commands instead of 6

**Migration Path:**
- No user migration needed (checkpoint was not a core workflow)
- Users with existing `.aurora/checkpoints/` directories - preserve but don't manage
- Configuration graceful degradation - ignore checkpoint-related config keys

## Benefits

1. **Reduced Complexity**: 5 commands instead of 6 (17% reduction in command surface area)
2. **Clearer Focus**: Command set aligns with strategic priorities (memory, planning, execution)
3. **Maintenance Savings**: Less code to test, document, and maintain across 20 tools
4. **Cleaner User Experience**: Users see only strategically important commands
5. **Faster Onboarding**: Fewer concepts for new users to learn

## Scope

### In Scope

1. **Template System** (`packages/cli/src/aurora_cli/templates/slash_commands.py`):
   - Remove `CHECKPOINT_TEMPLATE` constant (lines 252-289)
   - Remove `"checkpoint"` key from `COMMAND_TEMPLATES` dict (line 334)
   - Update `ALL_COMMANDS` list (if exists)

2. **All 20 Tool Configurators** (`packages/cli/src/aurora_cli/configurators/slash/*.py`):
   - **Markdown tools (14)**: claude, cursor, windsurf, cline, github_copilot, codex, opencode, amazon_q, codebuddy, auggie, costrict, crush, antigravity, factory
     - Remove `"checkpoint"` from `FILE_PATHS` dict
     - Remove `"checkpoint"` from `FRONTMATTER` dict
   - **TOML tools (6)**: gemini, qwen, kilocode, roocode, qoder, iflow
     - Remove `"checkpoint"` from `FILE_PATHS` dict
     - Remove `"checkpoint"` from `DESCRIPTIONS` dict

3. **Configuration Reference** (`docs/reference/CONFIG_REFERENCE.md`):
   - Remove any checkpoint-related configuration sections
   - Update command count from 6 to 5 throughout document

4. **Tools Guide** (`docs/guides/TOOLS_GUIDE.md`):
   - Update command count from 6 to 5 (line 235, 843, etc.)
   - Remove checkpoint from command lists
   - Update "What It Creates" section (lines 312-332)

5. **CLAUDE.md** (Project instructions):
   - Update command count from 6 to 5 (line 235)
   - Remove checkpoint from documented commands

6. **README.md**:
   - Update command references
   - Update command count if mentioned

7. **Implementation Code** (Conditional - based on usage analysis):
   - `packages/cli/src/aurora_cli/planning/checkpoint.py` - Analyze for removal or deprecation
   - `packages/cli/src/aurora_cli/execution/checkpoint.py` - Analyze for removal or deprecation
   - `packages/cli/src/aurora_cli/commands/spawn.py` - Remove checkpoint CLI options (lines 80-100)
   - `packages/cli/src/aurora_cli/commands/spawn_helpers.py` - Remove checkpoint helpers

8. **Test Files**:
   - Remove checkpoint-related tests
   - Update configurator tests to expect 5 commands instead of 6

### Out of Scope

1. **User checkpoint directories** - Don't delete existing `.aurora/checkpoints/` folders
2. **Checkpoint file format** - No need to migrate or convert existing checkpoint files
3. **Alternative session management** - Not adding replacement functionality
4. **Backward compatibility layer** - Clean removal, no deprecation warnings
5. **MCP tool integration** - Only affecting slash command system
6. **ACT-R memory checkpointing** - Not removing memory system checkpointing (different concept)

## Dependencies

**Must complete before implementation:**
- None - this is a straightforward removal task

**Files that depend on checkpoint:**
- `packages/cli/src/aurora_cli/templates/slash_commands.py` (source of truth)
- All 20 configurator files (consumers)
- Documentation files (reference materials)

**No blocking dependencies** - this change is self-contained within the slash command system.

## Implementation Strategy

**Phase 1: Core Template Removal** (30 min)
- Task 1.1: Remove `CHECKPOINT_TEMPLATE` from `slash_commands.py`
- Task 1.2: Remove `"checkpoint"` from `COMMAND_TEMPLATES`
- Task 1.3: Run unit tests to verify template changes

**Phase 2: Configurator Updates** (1-2 hours)
- Task 2.1: Update 14 Markdown configurators (remove checkpoint entries)
- Task 2.2: Update 6 TOML configurators (remove checkpoint entries)
- Task 2.3: Verify registry still has 20 tools registered
- Task 2.4: Run configurator unit tests

**Phase 3: Code Cleanup** (1-2 hours)
- Task 3.1: Analyze checkpoint implementation usage
- Task 3.2: Remove checkpoint CLI options from `spawn.py`
- Task 3.3: Remove checkpoint helper functions
- Task 3.4: Remove or deprecate `checkpoint.py` modules
- Task 3.5: Update imports and dependencies

**Phase 4: Documentation Updates** (1 hour)
- Task 4.1: Update CONFIG_REFERENCE.md
- Task 4.2: Update TOOLS_GUIDE.md
- Task 4.3: Update CLAUDE.md
- Task 4.4: Update README.md
- Task 4.5: Update CLI_USAGE_GUIDE.md if needed

**Phase 5: Testing & Verification** (1 hour)
- Task 5.1: Run full test suite
- Task 5.2: Integration test - `aur init --tools=claude,cursor,gemini`
- Task 5.3: Verify 5 commands created (not 6)
- Task 5.4: Verify no checkpoint files generated
- Task 5.5: Test config loading with old checkpoint config (graceful degradation)

**Total Estimated Time: 4-6 hours**

## Technical Specifications

### File-by-File Changes

#### 1. `/packages/cli/src/aurora_cli/templates/slash_commands.py`

**Remove:**
```python
# Lines 252-289: CHECKPOINT_TEMPLATE
CHECKPOINT_TEMPLATE = f"""{BASE_GUARDRAILS}
...
"""

# Line 334: Dictionary entry
"checkpoint": CHECKPOINT_TEMPLATE,
```

**Result:**
- Template file reduces from ~356 lines to ~289 lines
- `COMMAND_TEMPLATES` has 5 entries instead of 6
- `get_command_body("checkpoint")` will raise `KeyError`

#### 2. **All 20 Configurator Files** - Pattern Example

**Before (claude.py):**
```python
FILE_PATHS: dict[str, str] = {
    "search": ".claude/commands/aur/search.md",
    "get": ".claude/commands/aur/get.md",
    "plan": ".claude/commands/aur/plan.md",
    "checkpoint": ".claude/commands/aur/checkpoint.md",  # REMOVE
    "implement": ".claude/commands/aur/implement.md",
    "archive": ".claude/commands/aur/archive.md",
}

FRONTMATTER: dict[str, str] = {
    # ... 5 other entries ...
    "checkpoint": """---
name: aur:checkpoint
description: Save session context
---""",  # REMOVE
}
```

**After:**
```python
FILE_PATHS: dict[str, str] = {
    "search": ".claude/commands/aur/search.md",
    "get": ".claude/commands/aur/get.md",
    "plan": ".claude/commands/aur/plan.md",
    "implement": ".claude/commands/aur/implement.md",
    "archive": ".claude/commands/aur/archive.md",
}

FRONTMATTER: dict[str, str] = {
    # ... 5 entries only ...
}
```

**Apply to all 20 tools:**
- amazon_q.py
- antigravity.py
- auggie.py
- claude.py
- cline.py
- codebuddy.py
- codex.py
- costrict.py
- crush.py
- cursor.py
- factory.py
- gemini.py (TOML)
- github_copilot.py
- iflow.py (TOML)
- kilocode.py (TOML)
- opencode.py
- qoder.py (TOML)
- qwen.py (TOML)
- roocode.py (TOML)
- windsurf.py

#### 3. `/packages/cli/src/aurora_cli/commands/spawn.py`

**Remove options:**
```python
# Lines 80-100: Remove these CLI options
@click.option("--resume", ...)
@click.option("--list-checkpoints", ...)
@click.option("--clean-checkpoints", ...)
@click.option("--no-checkpoint", ...)
```

**Remove imports:**
```python
# Lines 33-35: Remove checkpoint helper imports
from aurora_cli.commands.spawn_helpers import clean_checkpoints as _clean_checkpoints_impl
from aurora_cli.commands.spawn_helpers import list_checkpoints as _list_checkpoints_impl
from aurora_cli.commands.spawn_helpers import resume_from_checkpoint as _resume_from_checkpoint_impl
```

**Remove conditional logic:**
- Any checkpoint save/restore logic in command body
- Checkpoint directory references

#### 4. `/packages/cli/src/aurora_cli/commands/spawn_helpers.py`

**Remove functions:**
```python
def list_checkpoints() -> None:
    """..."""

def clean_checkpoints(days: int) -> None:
    """..."""

def resume_from_checkpoint(execution_id: str) -> None:
    """..."""
```

#### 5. Documentation Updates

**`/docs/reference/CONFIG_REFERENCE.md`:**
- Search for "checkpoint" (case-insensitive)
- Remove any configuration sections
- Update command counts from 6 to 5

**`/docs/guides/TOOLS_GUIDE.md`:**
- Line 235: Update from "6 commands" to "5 commands"
- Line 318: Remove checkpoint.md from example
- Line 843: Update `ALL_COMMANDS` from 6 to 5

**`/CLAUDE.md`:**
- Line 235: Update from "6 commands" to "5 commands"
- Remove checkpoint from command list

**`/README.md`:**
- Update any command count references
- Remove checkpoint from feature lists

### Configuration Migration

**Backward Compatibility Strategy:**

If users have checkpoint-related config keys, they will be silently ignored:

```json
// Old config (still works, checkpoint key ignored)
{
  "planning": {
    "enable_checkpoints": true,
    "checkpoint_dir": ".aurora/checkpoints"
  }
}
```

**No migration script needed** - Aurora's config loading is permissive and ignores unknown keys.

### Testing Strategy

**Unit Tests:**

1. **Template tests:**
```python
def test_command_templates_count():
    """Verify only 5 commands in template dict."""
    from aurora_cli.templates.slash_commands import COMMAND_TEMPLATES
    assert len(COMMAND_TEMPLATES) == 5
    assert "checkpoint" not in COMMAND_TEMPLATES

def test_get_command_body_checkpoint_raises():
    """Verify checkpoint raises KeyError."""
    from aurora_cli.templates.slash_commands import get_command_body
    with pytest.raises(KeyError):
        get_command_body("checkpoint")
```

2. **Configurator tests (per tool):**
```python
def test_claude_configurator_has_5_commands():
    """Verify Claude configurator defines 5 commands."""
    from aurora_cli.configurators.slash.claude import FILE_PATHS, FRONTMATTER
    assert len(FILE_PATHS) == 5
    assert len(FRONTMATTER) == 5
    assert "checkpoint" not in FILE_PATHS
    assert "checkpoint" not in FRONTMATTER
```

**Integration Tests:**

```bash
# Test command generation
cd /tmp/test-aurora-checkpoint-removal
aur init --tools=claude,cursor,gemini

# Verify 5 files created (not 6)
ls .claude/commands/aur/ | wc -l  # Should be 5
test ! -f .claude/commands/aur/checkpoint.md  # Should not exist

# Verify no checkpoint references
grep -r "checkpoint" .claude/ && exit 1 || echo "✓ No checkpoint refs"
```

**Regression Tests:**

```bash
# Verify other commands still work
aur init --tools=claude
test -f .claude/commands/aur/search.md
test -f .claude/commands/aur/get.md
test -f .claude/commands/aur/plan.md
test -f .claude/commands/aur/implement.md
test -f .claude/commands/aur/archive.md
```

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Users actively using checkpoint command | MEDIUM | Unlikely - checkpoint not in core workflows. No telemetry indicates usage. |
| Breaking existing `.aurora/checkpoints/` directories | LOW | Don't delete user checkpoint dirs, just stop managing them. |
| Tests fail after removal | MEDIUM | Update tests to expect 5 commands. Comprehensive test plan included. |
| Documentation inconsistencies | LOW | Systematic grep for "checkpoint" across all docs. |
| Missed configurator files | HIGH | All 20 tools listed explicitly. Verify with registry count test. |
| Config loading breaks | LOW | Aurora's config is permissive. Test graceful degradation. |

## Success Criteria

**Functional Success:**
- [ ] `aur init --tools=all` generates 5 commands per tool (not 6)
- [ ] No `checkpoint.md` or `checkpoint.toml` files created
- [ ] `aur spawn --help` does not show checkpoint options
- [ ] All 20 tools successfully generate 5 commands

**Code Quality:**
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] No `grep -r "checkpoint"` matches in `configurators/slash/*.py` (except comments)
- [ ] `make quality-check` passes

**Documentation:**
- [ ] All docs reference 5 commands, not 6
- [ ] No broken command links
- [ ] CONFIG_REFERENCE.md has no checkpoint sections
- [ ] TOOLS_GUIDE.md examples show 5 commands

**Testing Coverage:**
- [ ] Template tests verify 5 commands
- [ ] Configurator tests updated for all 20 tools
- [ ] Integration test verifies file generation
- [ ] Regression test verifies other commands unaffected

## Open Questions

1. **Should we add deprecation logging?**
   - **Recommendation**: No - clean removal. Checkpoint wasn't in core workflows, no need for deprecation period.

2. **What about existing `.aurora/checkpoints/` directories?**
   - **Recommendation**: Leave them alone. Don't delete user data. If users manually created checkpoints, preserve them.

3. **Should we update changelog/migration guide?**
   - **Recommendation**: Yes - add to CHANGELOG.md under "Removed" section. Not breaking since checkpoint wasn't core.

4. **Remove checkpoint implementation code immediately or deprecate?**
   - **Recommendation**: Remove immediately. The code is only used by the slash command. If spawn.py checkpoint options are removed, implementation has no callers.

5. **Should we keep checkpoint code but just remove slash command?**
   - **Recommendation**: No - if removing from user-facing commands, remove implementation too. Simplifies codebase.

## Migration Guide for Users

### For Users Who Used Checkpoints

**Impact**: The `/aur:checkpoint` slash command will no longer be available.

**Reason for removal**: Checkpoint was unused and caused confusion with Claude Code's native checkpoint/rewind feature. The functionality has been superseded by "stash" in standard slash commands.

**Your existing checkpoint files** (`.aurora/checkpoints/`) are not deleted, but Aurora will no longer manage them.

**Alternative**: Use the standard `stash` slash command for session saving functionality.

**No action required** - Aurora will continue to work. You'll see 5 commands instead of 6.

### For Users Who Never Used Checkpoints

**Impact**: None. You'll see one less command in your slash command list.

**Benefit**: Cleaner command palette, easier to find relevant commands.

## Verification Checklist

**Pre-Implementation:**
- [ ] Backup current codebase (git tag)
- [ ] Document current test coverage baseline
- [ ] List all 20 configurator files to update

**During Implementation:**
- [ ] Remove template code (Phase 1)
- [ ] Update all 20 configurators (Phase 2)
- [ ] Remove CLI code (Phase 3)
- [ ] Update documentation (Phase 4)
- [ ] Run test suite after each phase

**Post-Implementation:**
- [ ] All tests pass
- [ ] Manual test: `aur init --tools=claude,cursor,gemini,opencode`
- [ ] Verify 5 commands created per tool
- [ ] Verify no checkpoint.md files exist
- [ ] grep -r "checkpoint" returns only expected results (git history, this PRD)
- [ ] `aur spawn --help` has no checkpoint options
- [ ] Documentation accurate (5 commands everywhere)

**Rollback Plan:**
- Git revert to pre-change commit
- Restore from git tag if needed
- All changes in single PR for easy revert

---

## Appendix A: Complete File List

### Templates (1 file)
- `/packages/cli/src/aurora_cli/templates/slash_commands.py`

### Configurators (20 files)
- `/packages/cli/src/aurora_cli/configurators/slash/amazon_q.py`
- `/packages/cli/src/aurora_cli/configurators/slash/antigravity.py`
- `/packages/cli/src/aurora_cli/configurators/slash/auggie.py`
- `/packages/cli/src/aurora_cli/configurators/slash/claude.py`
- `/packages/cli/src/aurora_cli/configurators/slash/cline.py`
- `/packages/cli/src/aurora_cli/configurators/slash/codebuddy.py`
- `/packages/cli/src/aurora_cli/configurators/slash/codex.py`
- `/packages/cli/src/aurora_cli/configurators/slash/costrict.py`
- `/packages/cli/src/aurora_cli/configurators/slash/crush.py`
- `/packages/cli/src/aurora_cli/configurators/slash/cursor.py`
- `/packages/cli/src/aurora_cli/configurators/slash/factory.py`
- `/packages/cli/src/aurora_cli/configurators/slash/gemini.py` (TOML)
- `/packages/cli/src/aurora_cli/configurators/slash/github_copilot.py`
- `/packages/cli/src/aurora_cli/configurators/slash/iflow.py` (TOML)
- `/packages/cli/src/aurora_cli/configurators/slash/kilocode.py` (TOML)
- `/packages/cli/src/aurora_cli/configurators/slash/opencode.py`
- `/packages/cli/src/aurora_cli/configurators/slash/qoder.py` (TOML)
- `/packages/cli/src/aurora_cli/configurators/slash/qwen.py` (TOML)
- `/packages/cli/src/aurora_cli/configurators/slash/roocode.py` (TOML)
- `/packages/cli/src/aurora_cli/configurators/slash/windsurf.py`

### Implementation Code (4 files)
- `/packages/cli/src/aurora_cli/commands/spawn.py`
- `/packages/cli/src/aurora_cli/commands/spawn_helpers.py`
- `/packages/cli/src/aurora_cli/planning/checkpoint.py`
- `/packages/cli/src/aurora_cli/execution/checkpoint.py`

### Documentation (5 files)
- `/docs/reference/CONFIG_REFERENCE.md`
- `/docs/guides/TOOLS_GUIDE.md`
- `/docs/guides/CLI_USAGE_GUIDE.md`
- `/CLAUDE.md`
- `/README.md`

### Tests (estimate 30+ files)
- `/tests/unit/cli/configurators/slash/test_*.py` (20 files)
- `/tests/unit/cli/commands/test_spawn.py`
- `/tests/unit/cli/execution/test_checkpoint.py`
- `/tests/unit/cli/planning/test_checkpoint.py`
- `/tests/integration/test_spawn_checkpoints.py`
- Additional tests that reference checkpoint

**Total: ~60 files affected**

## Appendix B: Command Count Updates

**Files referencing "6 commands":**

```bash
grep -rn "6 commands" docs/ CLAUDE.md README.md
```

**Expected matches:**
- `docs/guides/TOOLS_GUIDE.md`: Multiple references to 6-command system
- `CLAUDE.md`: "6 commands generated"
- Package docstrings

**Action**: Replace "6" with "5" in all matches after verifying context.

## Appendix C: Grep Search Results

**Search for checkpoint references:**

```bash
# Find all checkpoint references
grep -r "checkpoint" packages/cli/src/aurora_cli/ --include="*.py" | wc -l

# Expected: ~100+ matches

# After removal, expect: ~0 matches (except comments/history)
```

**Critical files with checkpoint:**
- 118 files found containing "checkpoint" (from grep results)
- Systematic review required for each

---

**Document Version**: 1.0
**Created**: 2026-01-20
**Status**: Ready for Review
