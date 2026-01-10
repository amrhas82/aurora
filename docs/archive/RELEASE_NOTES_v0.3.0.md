# AURORA v0.3.0 Release Notes

**Release Date**: January 2026
**Version**: 0.3.0
**Phase**: 1.5 - Unified Initialization

---

## Overview

AURORA v0.3.0 introduces a unified initialization experience with project-specific setup, replacing the previous global configuration model. This release improves multi-project isolation, simplifies the setup process, and enhances security by removing API key prompts during initialization.

**Highlights:**
- ✨ New unified `aur init` command (3-step flow)
- 🗂️ Project-specific memory databases and planning directories
- 🔒 Enhanced security (no API keys in config files)
- ♻️ Idempotent re-run capability
- 🎯 Git-aware initialization
- 🧹 Removed legacy `aur init-planning` command

---

## Breaking Changes

### ⚠️ BREAKING: Command Removed

**`aur init-planning` has been removed.**

**Before (v0.2.x):**
```bash
aur init              # Global config setup
aur init-planning     # Separate planning setup
```

**After (v0.3.0):**
```bash
aur init              # Unified 3-step setup
aur init --config     # Quick tool configuration
```

**Migration:** Update scripts and documentation to use `aur init` or `aur init --config`.

---

### ⚠️ BREAKING: Project-Specific Storage

**Memory databases and planning directories are now project-specific.**

**Before (v0.2.x):**
```
~/.aurora/memory.db         # Global (all projects mixed)
~/.aurora/plans/            # Global
```

**After (v0.3.0):**
```
./.aurora/memory.db         # Per-project
./.aurora/plans/            # Per-project
```

**Impact:**
- Each project needs its own indexed memory
- Existing global memory is **not** automatically migrated
- Better multi-project isolation

**Migration:** Run `aur init` in each project to create project-specific databases.

---

### ⚠️ BREAKING: No Global Config File

**Global config file (`~/.aurora/config.json`) is no longer used.**

**Before (v0.2.x):**
```json
~/.aurora/config.json
{
  "llm": {
    "anthropic_api_key": "sk-ant-..."
  }
}
```

**After (v0.3.0):**
```bash
# Use environment variable
export ANTHROPIC_API_KEY=sk-ant-...
```

**Impact:**
- API keys in config files are ignored
- Standalone CLI commands require `ANTHROPIC_API_KEY` environment variable
- MCP tools do NOT require API keys

**Migration:** Extract API key from old config, set as environment variable in shell profile.

---

## New Features

### ✨ Unified `aur init` Command

Single command with 3-step interactive flow:

```bash
aur init
```

**Step 1: Planning Setup (Git + Directories)**
- Prompts to run `git init` if no `.git` directory
- Creates project structure (`.aurora/plans/`, `.aurora/logs/`, `.aurora/cache/`)
- Auto-detects project metadata (Python version, package manager, test framework)
- Generates `.aurora/project.md` with context

**Step 2: Memory Indexing**
- Indexes codebase for semantic search
- Creates project-specific database at `./.aurora/memory.db`
- Progress bar shows indexing status
- Can be skipped and run later

**Step 3: Tool Configuration**
- Interactive checkbox to select AI coding tools
- Detects existing tool configurations
- Creates/updates MCP server configs
- Preserves custom settings (marker-based updates)

**Example Output:**
```
Step 1/3: Planning Setup
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Git repository detected ✓
  ✓ .aurora/plans/active/
  ✓ .aurora/plans/archive/
  ✓ .aurora/logs/
  ✓ .aurora/cache/
  ✓ Created .aurora/project.md

Step 2/3: Memory Indexing
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Indexing . ━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
  ✓ Indexed 47 files, 234 chunks in 3.4s
  ✓ Database: ./.aurora/memory.db

Step 3/3: Tool Configuration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✓ Claude Code configured
  ✓ Universal configured

✓ Initialization Complete!
```

---

### 🎯 Git-Aware Initialization

AURORA now detects Git repositories and prompts to initialize:

```
Git repository not detected.
Initialize git repository? [Y/n]: _
```

**Benefits:**
- Seamless setup for new projects
- Optional (can decline and skip planning setup)
- Integrates with existing Git workflows

---

### ♻️ Idempotent Re-Run Capability

Run `aur init` multiple times safely:

```bash
aur init  # Run again in initialized project
```

**Re-Run Menu:**
```
AURORA is already initialized in this project.

Current Status:
  ✓ Step 1 (Planning): Completed 2 days ago
  ✓ Step 2 (Memory):   234 chunks indexed
  ✓ Step 3 (Tools):    2 tools configured

How would you like to proceed?

1. Re-run all steps
2. Select specific steps
3. Configure tools only
4. Exit

Choice [1-4]: _
```

**Safety Features:**
- Project metadata preserves user edits
- Tool configs update only within markers
- Memory database backed up before re-indexing (`memory.db.backup`)
- No data loss on re-runs

---

### 🚀 Quick Tool Configuration

Skip Steps 1-2 and configure tools only:

```bash
aur init --config
```

**Use Case:**
- Already initialized AURORA
- Want to add/update tool configurations
- Reconfigure after tool updates

---

### 📝 Auto-Detected Project Metadata

AURORA detects project context automatically:

```
Detecting project metadata...
  • Python: 3.10.12 (from pyproject.toml)
  • Package Manager: poetry
  • Testing Framework: pytest
  ✓ Created .aurora/project.md
```

**Detects:**
- Project name (from directory or git remote)
- Python version (`pyproject.toml`, `setup.py`)
- Package manager (poetry, pip, pipenv)
- JavaScript/TypeScript (`package.json`)
- Test framework (pytest, jest)

---

## Improvements

### 🔒 Enhanced Security

- No API key prompts during initialization
- No API keys stored in config files
- Environment variable-only for standalone CLI
- MCP tools never require API keys

### 🗂️ Multi-Project Isolation

- Each project has its own memory database
- No cross-project contamination
- Easier to share projects (commit `.aurora/` to git)
- Clean per-project setup

### 🧪 Comprehensive Test Suite

- 99 new tests for unified init command
- >90% coverage for init logic
- Integration tests for end-to-end flow
- Idempotent re-run tests

### 📚 Updated Documentation

- New initialization section in [CLI_USAGE_GUIDE.md](cli/CLI_USAGE_GUIDE.md)
- Created [MIGRATION_GUIDE_v0.3.0.md](cli/MIGRATION_GUIDE_v0.3.0.md)
- Updated [README.md](../README.md) quick start
- Removed all `init-planning` references

---

## Deprecations

### Removed: `aur init-planning`

**Command has been removed.**

**Replacement:** Use `aur init` (full setup) or `aur init --config` (tools only).

**Timeline:**
- v0.2.x: Both commands available
- v0.3.0: `init-planning` removed

---

## Migration Guide

**See:** [MIGRATION_GUIDE_v0.3.0.md](cli/MIGRATION_GUIDE_v0.3.0.md) for detailed migration steps.

**Quick Migration (< 5 minutes):**

1. **Backup existing data:**
   ```bash
   cp ~/.aurora/memory.db ~/.aurora/memory.db.v0.2.backup
   cp -r ~/.aurora/plans ~/.aurora/plans.v0.2.backup
   cp ~/.aurora/config.json ~/.aurora/config.json.v0.2.backup
   ```

2. **Set API key environment variable:**
   ```bash
   # Extract from old config
   cat ~/.aurora/config.json | grep api_key

   # Add to shell profile
   echo 'export ANTHROPIC_API_KEY=sk-ant-...' >> ~/.bashrc
   source ~/.bashrc
   ```

3. **Upgrade AURORA:**
   ```bash
   pip install --upgrade aurora-actr[all]
   aur --version  # Should show v0.3.0
   ```

4. **Re-initialize each project:**
   ```bash
   cd /path/to/project-a && aur init
   cd /path/to/project-b && aur init
   cd /path/to/project-c && aur init
   ```

5. **Verify:**
   ```bash
   aur doctor          # Health check
   aur mem stats       # Check indexed memory
   aur query "test"    # Test query
   ```

---

## Upgrade Path

### From v0.2.x → v0.3.0

**Compatibility:** Breaking changes require manual migration.

**Recommended Steps:**
1. Read [MIGRATION_GUIDE_v0.3.0.md](cli/MIGRATION_GUIDE_v0.3.0.md)
2. Backup existing data
3. Set `ANTHROPIC_API_KEY` environment variable
4. Upgrade: `pip install --upgrade aurora-actr[all]`
5. Re-initialize projects: `aur init`

**Estimated Time:** < 5 minutes per user + 2 minutes per project

---

## Known Issues

### Memory Indexing May Prompt Re-Index

**Issue:** Running `aur init` in a project with existing `.aurora/memory.db` prompts to re-index.

**Workaround:** Choose "skip" if you want to keep existing index.

**Status:** Expected behavior (re-indexing ensures up-to-date context).

---

### Tool Configuration Requires Tool Installation

**Issue:** Selecting a tool in Step 3 requires the tool to be installed (e.g., Claude Code CLI).

**Workaround:** Skip uninstalled tools, configure later with `aur init --config`.

**Status:** By design (AURORA detects and configures available tools).

---

## Performance

### Initialization Performance

- **Step 1 (Planning):** < 1 second
- **Step 2 (Indexing 100 files):** < 7 seconds
- **Step 3 (Tool Config):** < 2 seconds
- **Total:** < 10 seconds for typical project

### Memory Usage

- Indexing: < 100MB for 10K chunks
- Runtime: < 50MB base memory

---

## Testing

### Test Coverage

- **Unit Tests:** 89 tests for init logic
- **Integration Tests:** 10 end-to-end flow tests
- **Coverage:** >90% for `aurora_cli.commands.init`
- **Total Tests:** 3,016 tests (Phase 1 baseline maintained)

### Quality Gates

- ✅ All Phase 1 tests pass
- ✅ 0 mypy errors in init modules
- ✅ 0 ruff lint errors in init modules
- ✅ >90% coverage for new code

---

## Documentation

### New Documents

- [MIGRATION_GUIDE_v0.3.0.md](cli/MIGRATION_GUIDE_v0.3.0.md) - Detailed migration steps
- [RELEASE_NOTES_v0.3.0.md](RELEASE_NOTES_v0.3.0.md) - This document

### Updated Documents

- [CLI_USAGE_GUIDE.md](cli/CLI_USAGE_GUIDE.md) - New initialization section
- [README.md](../README.md) - Updated quick start
- [CLAUDE.md](../CLAUDE.md) - Updated context notes

### Removed References

- All `init-planning` command references removed
- Global config file documentation removed
- Updated examples to use unified `aur init`

---

## Contributors

This release includes contributions from:

- Claude Sonnet 4.5 (AI pair programmer)
- AURORA development team

**Special Thanks:** To the community for feedback on initialization UX improvements.

---

## What's Next

### Planned for v0.4.0

- Enhanced agent discovery with auto-refresh
- Planning system enhancements (task templates, status tracking)
- Multi-language support beyond Python
- Improved error messages and recovery

### Feedback Welcome

Open issues or discussions on GitHub:
- GitHub Issues: https://github.com/aurora-project/aurora/issues
- Discussions: https://github.com/aurora-project/aurora/discussions

---

## Additional Resources

- **Migration Guide:** [MIGRATION_GUIDE_v0.3.0.md](cli/MIGRATION_GUIDE_v0.3.0.md)
- **CLI Usage Guide:** [CLI_USAGE_GUIDE.md](cli/CLI_USAGE_GUIDE.md)
- **Troubleshooting:** [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **MCP Setup:** [MCP_SETUP.md](MCP_SETUP.md)

---

**Thank you for using AURORA!**

For questions or support, see our [documentation](https://docs.aurora.ai) or open a GitHub issue.
