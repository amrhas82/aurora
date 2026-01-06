# Rollback Procedures

**Related**: PRD-0024 - MCP Tool Deprecation
**Version**: 1.2.0
**Date**: 2026-01-06

This document provides detailed procedures for rolling back the MCP tool deprecation changes if needed.

## Overview

Three rollback options are available, each with different characteristics:

| Option | Speed | Impact | Reversibility | Use Case |
|--------|-------|--------|---------------|----------|
| **Option 1: Feature Flag** | < 1 minute | Partial | Immediate | Quick test/development |
| **Option 2: Git Tag Checkout** | < 5 minutes | Complete | Creates detached HEAD | Full revert needed |
| **Option 3: Git Revert Commits** | < 15 minutes | Complete | Preserves history | Production rollback |

**Recommendation**: Start with Option 1 (feature flag) for quick testing. Use Option 3 (git revert) for production rollback.

---

## Option 1: Feature Flag Re-enablement

**Speed**: < 1 minute
**Scope**: Partial (MCP infrastructure only, deprecated tools remain unavailable)
**Reversibility**: Immediate (just change flag back)

### What This Does

- Re-enables MCP configuration in `aur init`
- Makes 6 remaining MCP tools available:
  - `aurora_index`, `aurora_context`, `aurora_related`
  - `aurora_list_agents`, `aurora_search_agents`, `aurora_show_agent`
- Does NOT restore deprecated tools (`aurora_query`, `aurora_search`, `aurora_get`)

### Procedure

#### Step 1: Edit Config File

Edit `~/.aurora/config.json`:

```bash
nano ~/.aurora/config.json
```

Change `mcp.enabled` to `true`:

```json
{
  "mcp": {
    "enabled": true
  }
}
```

#### Step 2: Re-run Init with MCP

```bash
# For Claude Code
aur init --enable-mcp --tools=claude

# For Cursor
aur init --enable-mcp --tools=cursor

# For other tools
aur init --enable-mcp --tools=<tool-name>
```

#### Step 3: Verify MCP Configuration

```bash
# For Claude Code
cat ~/.claude/plugins/aurora/.mcp.json

# Expected: MCP server configuration present
```

#### Step 4: Verify Tools Available

```bash
# In Claude Code CLI
# Ask: "What Aurora tools are available?"
# Expected: 6 tools listed (not 9)
```

### Verification Checklist

- [ ] Config file has `mcp.enabled: true`
- [ ] MCP configuration files created (e.g., `.mcp.json`)
- [ ] 6 tools available (aurora_index, aurora_context, aurora_related, aurora_list_agents, aurora_search_agents, aurora_show_agent)
- [ ] Deprecated tools NOT available (aurora_query, aurora_search, aurora_get)

### Rollback This Rollback (Revert to Slash Commands)

```bash
# Edit config
nano ~/.aurora/config.json
# Set mcp.enabled: false

# Run init without flag
aur init --tools=claude
```

---

## Option 2: Git Checkout Baseline Tag

**Speed**: < 5 minutes
**Scope**: Complete (full revert to pre-deprecation state)
**Reversibility**: Creates detached HEAD (requires branch creation for permanent use)

### What This Does

- Reverts codebase to exact state before MCP deprecation
- Restores all 3 deprecated tools (`aurora_query`, `aurora_search`, `aurora_get`)
- Restores MCP checks in `aur doctor`
- Restores MCP configuration as default in `aur init`

### ⚠️ Warning

This creates a **detached HEAD state**. To work on this state, you must create a branch.

### Procedure

#### Step 1: Verify Tag Exists

```bash
git tag -l mcp-deprecation-baseline
```

**Expected output**:
```
mcp-deprecation-baseline
```

If tag doesn't exist, use Option 3 instead.

#### Step 2: Checkout Tag

```bash
# This creates detached HEAD
git checkout mcp-deprecation-baseline
```

**Expected output**:
```
Note: switching to 'mcp-deprecation-baseline'.

You are in 'detached HEAD' state...
HEAD is now at <commit-hash> <commit-message>
```

#### Step 3: Create Branch (Optional but Recommended)

```bash
# Create branch from this state
git checkout -b rollback-to-mcp-baseline

# Or stay in detached HEAD (not recommended for development)
```

#### Step 4: Verify Deprecated Tools Restored

```bash
# Check server.py has tool registrations
grep -A5 "def aurora_search" /home/hamr/PycharmProjects/aurora/src/aurora_mcp/server.py

# Expected: Function definition present
```

#### Step 5: Reinstall Package

```bash
# Reinstall from rolled-back code
pip install -e .

# Or if using from source
python -m pip install -e .
```

#### Step 6: Verify Tools Available

```bash
# Test MCP server
python -m aurora_mcp.server --list-tools

# Expected: 9 tools listed (including aurora_query, aurora_search, aurora_get)
```

### Verification Checklist

- [ ] Checked out to `mcp-deprecation-baseline` tag
- [ ] Created branch (or comfortable with detached HEAD)
- [ ] Package reinstalled from rolled-back code
- [ ] 9 tools available (including deprecated ones)
- [ ] `aur doctor` shows MCP checks
- [ ] `aur init` configures MCP by default

### Rollback This Rollback (Return to Current State)

```bash
# Return to feature branch
git checkout feature/mcp-deprecation

# Or return to main
git checkout main

# Reinstall current version
pip install -e .
```

---

## Option 3: Git Revert Commits

**Speed**: < 15 minutes
**Scope**: Complete (full revert to pre-deprecation state)
**Reversibility**: Preserves full history (creates new revert commits)

### What This Does

- Creates new commits that undo deprecation changes
- Preserves complete git history (audit trail maintained)
- Restores all functionality to pre-deprecation state
- Suitable for production rollback

### Procedure

#### Step 1: Identify Commit Range

```bash
# List commits on feature branch
git log --oneline feature/mcp-deprecation

# Or compare to main
git log --oneline main..feature/mcp-deprecation
```

**Expected output**:
```
abc1234 feat(doctor): remove MCP checks section (Phase 4)
def5678 feat(mcp): deprecate MCP tools in favor of slash commands (Phases 0-3)
ghi9012 chore: prepare feature branch for MCP tool deprecation (PRD-0024)
```

#### Step 2: Identify Target Commits

Identify the commit range to revert. For example:
- First commit: `ghi9012`
- Last commit: `abc1234`

#### Step 3: Revert Commit Range

```bash
# Revert from oldest to newest
git revert --no-commit ghi9012^..abc1234

# Or revert individual commits
git revert ghi9012
git revert def5678
git revert abc1234
```

**Note**: `--no-commit` creates a single revert commit instead of multiple.

#### Step 4: Review Revert Changes

```bash
# Check what will be reverted
git diff --cached

# Verify files modified
git status
```

#### Step 5: Commit Revert

```bash
git commit -m "Revert PRD-0024 MCP tool deprecation

This reverts the following changes:
- MCP tool deprecation (Phases 0-3)
- Doctor command MCP checks removal (Phase 4)
- Configurator permission updates (Phase 5)

Reason: [Specify reason for rollback]

Reverts commits: ghi9012, def5678, abc1234"
```

#### Step 6: Verify Reverted State

```bash
# Check server.py has tool registrations
grep -A5 "def aurora_search" /home/hamr/PycharmProjects/aurora/src/aurora_mcp/server.py

# Check doctor.py has MCP checks
grep -n "MCP FUNCTIONAL" /home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/doctor.py
```

#### Step 7: Reinstall Package

```bash
pip install -e .
```

#### Step 8: Run Tests

```bash
# Run full test suite
pytest tests/

# Run integration tests with MCP enabled
AURORA_ENABLE_MCP=1 pytest tests/integration/
```

### Verification Checklist

- [ ] Commits identified correctly
- [ ] Revert completed without conflicts
- [ ] Package reinstalled
- [ ] 9 tools available (including deprecated ones)
- [ ] `aur doctor` shows MCP checks
- [ ] `aur init` configures MCP by default
- [ ] All tests passing

### Rollback This Rollback (Re-apply Deprecation)

```bash
# Revert the revert commits
git log --oneline  # Find revert commit hash
git revert <revert-commit-hash>

# Or cherry-pick original deprecation commits
git cherry-pick ghi9012
git cherry-pick def5678
git cherry-pick abc1234
```

---

## Decision Matrix

Use this matrix to choose the right rollback option:

### Use Option 1 (Feature Flag) When:
- ✅ Quick testing needed (< 1 minute)
- ✅ Only need 6 remaining MCP tools
- ✅ Don't need deprecated tools
- ✅ Want minimal disruption
- ✅ Easy reversal important

### Use Option 2 (Git Tag Checkout) When:
- ✅ Need complete revert including deprecated tools
- ✅ Testing/development environment
- ✅ Comfortable with detached HEAD or creating branches
- ✅ Need exact pre-deprecation state
- ❌ NOT for production (no history preservation)

### Use Option 3 (Git Revert) When:
- ✅ Production rollback needed
- ✅ Need complete revert including deprecated tools
- ✅ Must preserve git history
- ✅ Need audit trail of rollback
- ✅ Want clean history
- ❌ NOT for quick testing (takes longer)

---

## Common Issues and Troubleshooting

### Issue: Tag Not Found

**Symptom**:
```bash
git tag -l mcp-deprecation-baseline
# No output
```

**Solution**: Use Option 3 (Git Revert) instead. Tag may not have been pushed to remote.

### Issue: Merge Conflicts During Revert

**Symptom**:
```bash
git revert <commit>
# CONFLICT (content): Merge conflict in ...
```

**Solution**:
1. Manually resolve conflicts in affected files
2. Run `git add <resolved-files>`
3. Continue revert: `git revert --continue`

### Issue: MCP Tools Not Available After Rollback

**Symptom**: MCP configuration exists but tools don't work

**Solution**:
```bash
# Reinstall package
pip uninstall aurora-actr
pip install -e .

# Clear MCP cache (Claude Code)
rm -rf ~/.claude/plugins/aurora/
aur init --enable-mcp --tools=claude
```

### Issue: Import Errors After Rollback

**Symptom**:
```
ImportError: cannot import name 'AuroraMCPTools'
```

**Solution**:
```bash
# Clear Python cache
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name '*.pyc' -delete

# Reinstall package
pip install -e .
```

### Issue: Tests Fail After Rollback

**Symptom**: Test failures after reverting changes

**Solution**:
```bash
# Check if test database is stale
rm ~/.aurora/memory.db
aur mem index

# Run tests with verbose output
pytest tests/ -v

# Run MCP integration tests with flag
AURORA_ENABLE_MCP=1 pytest tests/integration/ -v
```

---

## Post-Rollback Verification

After completing any rollback option, verify the system works correctly:

### 1. Health Check
```bash
aur doctor
# Should show MCP FUNCTIONAL section (Options 2-3 only)
```

### 2. MCP Configuration
```bash
# Verify MCP config exists
cat ~/.claude/plugins/aurora/.mcp.json

# Expected: MCP server configuration present
```

### 3. Tool Availability
```bash
# In Claude Code CLI
# Ask: "What Aurora tools are available?"

# Expected (Option 1): 6 tools
# Expected (Options 2-3): 9 tools
```

### 4. Search Functionality
```bash
# In Claude Code CLI
# Ask: "Search my codebase for authentication logic"

# Expected: Results returned (using MCP tools or slash commands)
```

### 5. SOAR Pipeline
```bash
aur soar "How does the authentication system work?"

# Expected: 9-phase SOAR execution completes successfully
```

---

## Emergency Rollback Procedure

If you need to rollback immediately in production:

### Quick Steps

```bash
# 1. Stop all services using Aurora
systemctl stop aurora-services  # Or your service manager

# 2. Fast rollback via feature flag
echo '{"mcp":{"enabled":true}}' > ~/.aurora/config.json
aur init --enable-mcp --tools=claude

# 3. Restart services
systemctl start aurora-services

# 4. Monitor logs
tail -f ~/.aurora/logs/aurora.log
```

### Escalation

If quick rollback fails:
1. Use Option 3 (Git Revert) for complete rollback
2. Notify team of rollback
3. Document issues encountered
4. Review docs/TROUBLESHOOTING.md

---

## Lessons Learned (Post-Rollback)

After any rollback, document:

1. **What triggered the rollback?**
   - User feedback?
   - Technical issues?
   - Business requirements change?

2. **Which option was used?**
   - Why was that option chosen?
   - Did it work as expected?

3. **What could be improved?**
   - Better testing before deployment?
   - Clearer migration documentation?
   - Phased rollout strategy?

4. **Next steps**
   - Re-attempt deprecation?
   - Keep MCP tools permanently?
   - Hybrid approach?

---

## Support

**Documentation**:
- [MCP_DEPRECATION.md](MCP_DEPRECATION.md) - Architecture rationale
- [MIGRATION.md](MIGRATION.md) - User migration guide
- [COMMANDS.md](../COMMANDS.md) - Command reference

**Issues**:
- Report issues: GitHub Issues
- Emergency contact: [Specify emergency contact]

**Timeline for Re-attempt** (if applicable):
- Evaluation: [Date]
- Decision: [Date]
- Re-deployment: [Date]
