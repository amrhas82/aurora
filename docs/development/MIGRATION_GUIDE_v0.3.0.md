# Migration Guide: AURORA v0.2.x → v0.3.0

**Version**: v0.3.0
**Release Date**: January 2026
**Migration Time**: < 5 minutes
**Breaking Changes**: Yes

---

## Overview

AURORA v0.3.0 introduces a major architectural change from **global configuration** to **project-specific setup**. This migration brings better multi-project isolation, cleaner initialization, and improved security.

**Key Changes:**
- `aur init` and `aur init-planning` merged into single `aur init` command
- Memory database moved from `~/.aurora/memory.db` to `./.aurora/memory.db`
- Global config file removed (use environment variables for API keys)
- Planning data moved from `~/.aurora/plans/` to `./.aurora/plans/`
- No API key prompts during initialization (environment variables only)

---

## Breaking Changes

### 1. Command Removed: `aur init-planning`

**Before (v0.2.x):**
```bash
aur init              # Created global config
aur init-planning     # Separate command for planning setup
```

**After (v0.3.0):**
```bash
aur init              # Unified command (3 steps: planning + memory + tools)
aur init --config     # Quick tool configuration only
```

**Impact:** Scripts or documentation referencing `aur init-planning` will fail.

**Action Required:** Update scripts to use `aur init` or `aur init --config`.

---

### 2. Memory Database Location Changed

**Before (v0.2.x):**
```
~/.aurora/memory.db    # Global database (all projects mixed)
```

**After (v0.3.0):**
```
./.aurora/memory.db    # Project-specific database
```

**Impact:**
- Each project needs its own indexed memory
- Cannot query one project from another project's context
- Existing global memory database is NOT automatically migrated

**Action Required:**
- Re-index each project: `cd /path/to/project && aur mem index .`
- Optionally backup old database: `cp ~/.aurora/memory.db ~/.aurora/memory.db.v0.2.backup`

---

### 3. Global Config File Removed

**Before (v0.2.x):**
```json
~/.aurora/config.json
{
  "llm": {
    "provider": "anthropic",
    "anthropic_api_key": "sk-ant-...",
    "model": "claude-3-5-sonnet-20241022"
  }
}
```

**After (v0.3.0):**
```bash
# No config file - use environment variables
export ANTHROPIC_API_KEY=sk-ant-...
```

**Impact:**
- API keys in config files are no longer read
- Standalone CLI commands (`aur query`, `aur headless`) require `ANTHROPIC_API_KEY` environment variable

**Action Required:**
```bash
# Add to ~/.bashrc or ~/.zshrc
export ANTHROPIC_API_KEY=sk-ant-...
source ~/.bashrc
```

---

### 4. Planning Directory Location Changed

**Before (v0.2.x):**
```
~/.aurora/plans/active/    # Global planning directory
~/.aurora/plans/archive/
```

**After (v0.3.0):**
```
./.aurora/plans/active/    # Project-specific planning directory
./.aurora/plans/archive/
```

**Impact:**
- Existing plans in `~/.aurora/plans/` are not visible in v0.3.0
- Each project maintains its own plans

**Action Required:**
- Manually copy plans if needed:
  ```bash
  mkdir -p .aurora/plans
  cp -r ~/.aurora/plans/active .aurora/plans/
  cp -r ~/.aurora/plans/archive .aurora/plans/
  ```

---

### 5. Budget Tracker (Global - No Change)

**Still Global (Unchanged):**
```
~/.aurora/budget_tracker.json    # Remains global (user-wide)
```

**Impact:** None. Budget tracking is still per-user, not per-project.

**Action Required:** None.

---

## Migration Steps

### Step 1: Backup Existing Data (Optional but Recommended)

```bash
# Backup global memory database
cp ~/.aurora/memory.db ~/.aurora/memory.db.v0.2.backup

# Backup global plans
cp -r ~/.aurora/plans ~/.aurora/plans.v0.2.backup

# Backup config file (contains API key)
cp ~/.aurora/config.json ~/.aurora/config.json.v0.2.backup
```

**Estimated Time:** < 1 minute

---

### Step 2: Set API Key Environment Variable

Extract API key from old config and set as environment variable:

```bash
# View old config (if exists)
cat ~/.aurora/config.json | grep api_key

# Set environment variable (add to ~/.bashrc or ~/.zshrc)
export ANTHROPIC_API_KEY=sk-ant-api-03-...

# Reload shell
source ~/.bashrc  # or source ~/.zshrc
```

**Verify:**
```bash
echo $ANTHROPIC_API_KEY
# Should print: sk-ant-api-03-...
```

**Estimated Time:** < 1 minute

---

### Step 3: Upgrade AURORA

```bash
# If installed from PyPI
pip install --upgrade aurora-actr[all]

# If installed from source
cd /path/to/aurora
git pull origin main
pip install -e ".[all]"
```

**Verify Version:**
```bash
aur --version
# Should show: aurora, version 0.3.0 or higher
```

**Estimated Time:** < 1 minute

---

### Step 4: Re-Initialize Each Project

For each project where you use AURORA:

```bash
# Navigate to project
cd /path/to/your/project

# Run new unified init
aur init
```

**Interactive Flow:**
```
Step 1/3: Planning Setup
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Git repository detected ✓
Creating project structure...
  ✓ .aurora/plans/active/
  ✓ .aurora/plans/archive/
  ✓ .aurora/logs/
  ✓ .aurora/cache/
  ✓ Created .aurora/project.md

Step 2/3: Memory Indexing
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Index codebase for semantic search? [Y/n]: y
Indexing . ━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
  ✓ Indexed 47 files, 234 chunks in 3.4s
  ✓ Database: ./.aurora/memory.db

Step 3/3: Tool Configuration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Select tools to configure:
❯ ◉ Claude Code
  ◉ Universal

  ✓ Claude Code configured
  ✓ Universal configured

✓ Initialization Complete!
```

**Repeat for Each Project:**
```bash
cd /path/to/project-a && aur init
cd /path/to/project-b && aur init
cd /path/to/project-c && aur init
```

**Estimated Time:** < 2 minutes per project

---

### Step 5: (Optional) Migrate Old Plans

If you want to preserve plans from v0.2.x:

```bash
# Copy plans to current project
cd /path/to/your/project
mkdir -p .aurora/plans
cp -r ~/.aurora/plans.v0.2.backup/active .aurora/plans/
cp -r ~/.aurora/plans.v0.2.backup/archive .aurora/plans/

# Verify
ls -la .aurora/plans/active
```

**Estimated Time:** < 1 minute

---

### Step 6: Clean Up (Optional)

Remove old global config files:

```bash
# Remove old config (API key now in environment variable)
rm ~/.aurora/config.json

# Remove old global memory database (now per-project)
rm ~/.aurora/memory.db

# Remove old global plans (now per-project)
rm -rf ~/.aurora/plans

# Keep backups for safety
ls ~/.aurora/*.backup
```

**Estimated Time:** < 1 minute

---

## Verification

### Verify Migration Success

```bash
# Check AURORA version
aur --version
# Expected: aurora, version 0.3.0

# Check API key is set
echo $ANTHROPIC_API_KEY
# Expected: sk-ant-api-03-...

# Check project structure
ls -la .aurora/
# Expected:
# drwxr-xr-x plans/
# drwxr-xr-x logs/
# drwxr-xr-x cache/
# -rw-r--r-- memory.db
# -rw-r--r-- project.md

# Check memory database works
aur mem stats
# Expected: Shows chunk count and file count

# Check query works
aur query "What is Aurora?"
# Expected: Response from LLM (no errors)

# Run health check
aur doctor
# Expected: All checks passed
```

---

## Troubleshooting

### Issue: "ANTHROPIC_API_KEY not found"

**Symptom:**
```
Error: ANTHROPIC_API_KEY not found.
```

**Solution:**
```bash
# Add to shell profile
echo 'export ANTHROPIC_API_KEY=sk-ant-api-03-...' >> ~/.bashrc
source ~/.bashrc

# Verify
echo $ANTHROPIC_API_KEY
```

---

### Issue: "No such command 'init-planning'"

**Symptom:**
```
Error: No such command 'init-planning'.
```

**Solution:**
```bash
# Update scripts to use new command
# Old: aur init-planning
# New: aur init --config
```

---

### Issue: Memory search returns 0 results

**Symptom:**
```
Found 0 results for 'authentication'
```

**Solution:**
```bash
# Re-index project (memory.db is now project-specific)
aur mem index .

# Verify indexing
aur mem stats
# Should show: Total Chunks: 234 (or similar)
```

---

### Issue: Old plans not visible

**Symptom:**
```bash
aur plan list
# Shows: No plans found
```

**Solution:**
```bash
# Copy plans from backup
cp -r ~/.aurora/plans.v0.2.backup/active .aurora/plans/
cp -r ~/.aurora/plans.v0.2.backup/archive .aurora/plans/

# Verify
aur plan list
```

---

## Rollback (Emergency)

If migration fails and you need to rollback:

```bash
# Uninstall v0.3.0
pip uninstall aurora-actr

# Reinstall v0.2.x
pip install aurora-actr==0.2.0

# Restore backups
cp ~/.aurora/config.json.v0.2.backup ~/.aurora/config.json
cp ~/.aurora/memory.db.v0.2.backup ~/.aurora/memory.db
cp -r ~/.aurora/plans.v0.2.backup ~/.aurora/plans

# Verify
aur --version
# Should show: aurora, version 0.2.0
```

---

## FAQ

### Q: Do I need to re-index every project?

**A:** Yes. Memory databases are now project-specific. Run `aur mem index .` in each project.

---

### Q: Can I use the same memory database for multiple projects?

**A:** No. v0.3.0 enforces project-specific memory for better isolation. Each project needs its own `.aurora/memory.db`.

---

### Q: Will my budget tracker be reset?

**A:** No. Budget tracker remains global at `~/.aurora/budget_tracker.json` and is unchanged.

---

### Q: Can I still use MCP tools?

**A:** Yes. MCP integration is unchanged. Tool configuration is now part of `aur init` Step 3.

---

### Q: Do I need to set API key for MCP tools?

**A:** No. MCP tools inside Claude Code CLI do NOT require API keys. Only standalone commands (`aur query`, `aur headless`) require `ANTHROPIC_API_KEY` environment variable.

---

### Q: What happens if I run `aur init` multiple times?

**A:** v0.3.0 is idempotent. Re-running `aur init` shows a menu to re-run all steps, select specific steps, or exit. No data loss.

---

### Q: Can I commit `.aurora/` to git?

**A:** Yes! v0.3.0 encourages committing `.aurora/` (except `memory.db` - add to `.gitignore`). This shares project metadata, plans, and tool configs with your team.

**Recommended `.gitignore`:**
```gitignore
.aurora/memory.db
.aurora/memory.db.backup
.aurora/logs/
.aurora/cache/
```

---

## Migration Checklist

Use this checklist to track your migration:

- [ ] Backup existing data (`~/.aurora/`)
- [ ] Extract API key from `~/.aurora/config.json`
- [ ] Set `ANTHROPIC_API_KEY` environment variable
- [ ] Add to shell profile (`~/.bashrc` or `~/.zshrc`)
- [ ] Upgrade AURORA: `pip install --upgrade aurora-actr[all]`
- [ ] Verify version: `aur --version` shows v0.3.0
- [ ] Re-initialize project 1: `cd project-a && aur init`
- [ ] Re-initialize project 2: `cd project-b && aur init`
- [ ] Re-initialize project 3: `cd project-c && aur init`
- [ ] (Optional) Migrate old plans to each project
- [ ] Verify `aur mem stats` shows chunks
- [ ] Verify `aur query "test"` works
- [ ] Run `aur doctor` to check health
- [ ] Update scripts/docs to use `aur init` (not `aur init-planning`)
- [ ] (Optional) Clean up old global files

---

## Additional Resources

- **Full CLI Guide**: [CLI_USAGE_GUIDE.md](CLI_USAGE_GUIDE.md)
- **Release Notes**: [RELEASE_NOTES_v0.3.0.md](../RELEASE_NOTES_v0.3.0.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)
- **GitHub Issues**: https://github.com/aurora-project/aurora/issues

---

**Questions?** Open an issue on GitHub or see the troubleshooting section above.

**Estimated Total Migration Time:** < 5 minutes per user + 2 minutes per project
