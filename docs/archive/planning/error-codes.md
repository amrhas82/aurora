# Aurora Planning - Error Code Reference

**Complete reference for all error codes in the Aurora Planning System**

Version: 0.1.0 | Last Updated: 2026-01-03

---

## Overview

Aurora Planning uses a structured error code system (E001-E010) to help diagnose and resolve issues quickly. Each error code includes:

- **Code**: Unique identifier (E001-E010)
- **Error Message**: User-facing message displayed
- **Cause**: Why this error occurs
- **Solution**: How to fix it
- **Prevention**: How to avoid it in the future

---

## Error Codes

### E001: Plan Directory Not Writable

**Error Message:**
```
Error E001: Plan directory not writable
Unable to write to: ~/.aurora/plans/active/

Check directory permissions and ensure the directory is writable.
```

**Cause:**
- Directory permissions don't allow write access
- Directory is owned by different user
- Filesystem is read-only (e.g., mounted with `-o ro`)
- Disk quota exceeded

**Solution:**

1. **Fix permissions:**
   ```bash
   chmod 755 ~/.aurora/plans/
   chmod 755 ~/.aurora/plans/active/
   chmod 755 ~/.aurora/plans/archive/
   ```

2. **Check ownership:**
   ```bash
   ls -ld ~/.aurora/plans/
   # If owned by wrong user:
   sudo chown -R $USER:$USER ~/.aurora/plans/
   ```

3. **Check disk space:**
   ```bash
   df -h ~/.aurora/
   ```

**Prevention:**
- Run `aur plan init` with proper user account
- Don't manually modify directory permissions
- Ensure sufficient disk space (recommend 1GB+ free)

**Related Commands:**
- `aur plan init` - Initialize with correct permissions

---

### E002: Invalid Plan ID Format

**Error Message:**
```
Error E002: Invalid plan ID format: "my-plan"

Plan IDs must follow the format: NNNN-slug
Examples: 0001-oauth-auth, 0042-user-registration

Use auto-generated IDs by running: aur plan create "Your goal"
```

**Cause:**
- Manual plan directory creation with wrong naming
- Attempting to use plan ID without numeric prefix
- Typo in plan ID (missing digits or hyphens)

**Solution:**

1. **Use auto-generated IDs:**
   ```bash
   # Don't manually create plan directories
   # Let the system generate IDs:
   aur plan create "Your goal here"
   ```

2. **Fix existing directory:**
   ```bash
   # If you manually created "my-plan", rename it:
   mv ~/.aurora/plans/active/my-plan ~/.aurora/plans/active/0001-my-plan

   # Update agents.json to match:
   cd ~/.aurora/plans/active/0001-my-plan
   vi agents.json  # Set "plan_id": "0001-my-plan"
   ```

**Prevention:**
- Always use `aur plan create` to generate plans
- Never manually create plan directories
- Don't rename plan directories after creation

**Valid Formats:**
- Active plans: `NNNN-slug` (e.g., `0001-oauth-auth`)
- Archived plans: `YYYY-MM-DD-NNNN-slug` (e.g., `2026-01-15-0001-oauth-auth`)

---

### E003: Plan Not Found

**Error Message:**
```
Error E003: Plan not found: 0005

No plan found with ID: 0005

Similar plans found:
  - 0003-user-dashboard
  - 0004-api-refactor

List all plans: aur plan list --all
```

**Cause:**
- Plan ID doesn't exist (never created or deleted)
- Plan was archived (need `--archived` flag)
- Typo in plan ID
- Using wrong plans directory

**Solution:**

1. **List all plans:**
   ```bash
   # Active plans
   aur plan list

   # Include archived
   aur plan list --all
   ```

2. **Search archived plans:**
   ```bash
   aur plan view 0005 --archived
   ```

3. **Use partial ID matching:**
   ```bash
   # Instead of full ID, use partial match:
   aur plan view oauth
   aur plan view user
   ```

4. **Check plans directory:**
   ```bash
   echo $AURORA_PLANS_DIR
   ls ~/.aurora/plans/active/
   ls ~/.aurora/plans/archive/
   ```

**Prevention:**
- Use `aur plan list` to verify plan IDs before operations
- Use partial ID matching (fuzzy search)
- Don't manually delete plan directories

**Related Commands:**
- `aur plan list --all` - List all plans
- `aur plan view <id> --archived` - Include archived in search

---

### E004: agents.json Validation Error

**Error Message:**
```
Error E004: agents.json validation error

Plan: 0001-oauth-auth
File: .aurora/plans/active/0001-oauth-auth/agents.json

Validation errors:
  - Missing required field: "status"
  - Invalid value for "plan_id": must match NNNN-slug format
  - Invalid value for "agent_id": must start with "@"

See JSON Schema: packages/planning/src/aurora_planning/schemas/agents.schema.json
```

**Cause:**
- Manual editing broke JSON syntax
- Missing required fields
- Invalid field values (wrong format or type)
- Corrupted file from incomplete write

**Solution:**

1. **Check JSON syntax:**
   ```bash
   cd ~/.aurora/plans/active/0001-oauth-auth
   python -c "import json; print(json.load(open('agents.json')))"
   ```

2. **Validate against schema:**
   ```bash
   # Install jsonschema if needed
   pip install jsonschema

   # Validate
   python -c "
   import json
   from pathlib import Path
   import jsonschema

   with open('agents.json') as f:
       data = json.load(f)

   schema_path = Path('packages/planning/src/aurora_planning/schemas/agents.schema.json')
   with open(schema_path) as f:
       schema = json.load(f)

   jsonschema.validate(data, schema)
   print('Valid!')
   "
   ```

3. **Fix common issues:**
   ```json
   {
     "plan_id": "0001-oauth-auth",  // ✓ Must be NNNN-slug format
     "goal": "Implement OAuth2 authentication",  // ✓ Required, 10-500 chars
     "status": "pending",  // ✓ Required: pending|in_progress|complete|archived
     "created_at": "2026-01-15T10:30:00Z",  // ✓ Required: ISO 8601 format
     "subgoals": [  // Optional
       {
         "id": "sg-1",  // ✓ Must be sg-N format
         "title": "Design flow",  // ✓ Required, 3-200 chars
         "agent_id": "@architect",  // ✓ Required, must start with @
         "status": "pending",  // ✓ Required
         "dependencies": []  // Optional
       }
     ]
   }
   ```

**Prevention:**
- Backup `agents.json` before editing: `cp agents.json agents.json.bak`
- Use a JSON validator/linter in your editor
- Use `aur plan view` to check validation after edits
- Let the system generate files when possible

**Required Fields:**
- `plan_id` (string, NNNN-slug format)
- `goal` (string, 10-500 chars)
- `status` (string, valid status value)
- `created_at` (string, ISO 8601 datetime)

**Optional Fields:**
- `archived_at` (string, ISO 8601 datetime)
- `subgoals` (array of subgoal objects)
- Custom fields (preserved but ignored)

---

### E005: Template Rendering Failed

**Error Message:**
```
Error E005: Template rendering failed

Template: plan.md.j2
Error: Variable 'subgoal_count' is undefined

This is likely a bug in the template or missing template variable.
Please report this issue with the full error message.
```

**Cause:**
- Missing template file
- Template file corrupted
- Missing required template variable
- Jinja2 syntax error in template
- Package installation issue

**Solution:**

1. **Verify templates exist:**
   ```bash
   python -c "
   from aurora_planning.planning_config import get_template_dir
   print(get_template_dir())
   "

   # List templates
   ls -l $(python -c "from aurora_planning.planning_config import get_template_dir; print(get_template_dir())")
   ```

2. **Reinstall package:**
   ```bash
   cd packages/planning
   pip install -e . --force-reinstall
   ```

3. **Use custom template directory (workaround):**
   ```bash
   # Copy default templates
   mkdir -p ~/.aurora/templates
   cp -r <package-templates>/* ~/.aurora/templates/

   # Use custom directory
   export AURORA_TEMPLATE_DIR=~/.aurora/templates
   aur plan create "Test"
   ```

4. **Report bug:**
   ```bash
   # Include full error message and system info
   aur --version
   python --version
   pip show aurora-planning
   ```

**Prevention:**
- Don't manually edit template files in package directory
- Use `--template-dir` flag to override templates safely
- Keep Aurora Planning package up to date

**Related Environment Variables:**
- `AURORA_TEMPLATE_DIR` - Override default template directory

---

### E006: Archive Failed (Plan Incomplete)

**Error Message:**
```
Error E006: Archive failed - plan incomplete

Plan: 0001-oauth-auth
Progress: 18/24 tasks complete (75%)

The plan has incomplete tasks. Archive anyway?

Options:
  - Complete remaining tasks before archiving
  - Use --force flag to archive incomplete plan
  - Wait and archive later

To force archive: aur plan archive 0001 --force
```

**Cause:**
- Attempting to archive plan with incomplete tasks (<100%)
- Tasks checklist in `tasks.md` has unchecked items
- Intentionally archiving incomplete/abandoned plan

**Solution:**

1. **Complete remaining tasks:**
   ```bash
   # View plan progress
   aur plan view 0001

   # Edit tasks.md to check off remaining items
   cd ~/.aurora/plans/active/0001-oauth-auth
   vi tasks.md  # Check off tasks: - [x] Task description
   ```

2. **Force archive (if intentional):**
   ```bash
   aur plan archive 0001 --force
   # or
   aur plan archive 0001 -y
   ```

3. **Update plan status:**
   ```bash
   # If abandoning the plan, update status in agents.json
   cd ~/.aurora/plans/active/0001-oauth-auth
   vi agents.json  # Set "status": "complete" or "archived"
   ```

**Prevention:**
- Only archive when all tasks are done (100%)
- Use task checklist diligently
- Update plan status as you work

**When to Force Archive:**
- Plan abandoned or no longer relevant
- Tasks moved to different plan
- Project cancelled or pivoted
- Historical record (document "why" in plan.md)

---

### E007: Config Value Invalid

**Error Message:**
```
Error E007: Invalid configuration value

Config: planning.base_dir
Value: "/invalid/path/that/doesnt/exist"
Expected: Writable directory path

The configuration value is invalid or doesn't meet requirements.
Check your configuration file or environment variables.
```

**Cause:**
- Invalid path in config file
- Directory doesn't exist
- Wrong data type (string instead of boolean)
- Malformed YAML/JSON syntax

**Solution:**

1. **Check config file:**
   ```bash
   # User-level config
   cat ~/.aurora/config.yaml

   # Project-level config
   cat .aurora/config/planning.yaml
   ```

2. **Validate config syntax:**
   ```bash
   python -c "
   import yaml
   with open('~/.aurora/config.yaml') as f:
       config = yaml.safe_load(f)
   print('Valid YAML')
   "
   ```

3. **Fix invalid values:**
   ```yaml
   # ~/.aurora/config.yaml
   planning:
     base_dir: ~/.aurora/plans  # ✓ Must be writable directory
     template_dir: <package>/templates  # ✓ Optional override
     auto_increment: true  # ✓ Must be boolean
     archive_on_complete: false  # ✓ Must be boolean
   ```

4. **Use environment variables (override config):**
   ```bash
   export AURORA_PLANS_DIR=~/.aurora/plans
   export AURORA_PLANNING_AUTO_INCREMENT=true
   ```

**Prevention:**
- Use `aur plan init` to generate default config
- Validate YAML syntax before saving
- Use absolute paths for directories
- Check typos in boolean values (true/false, not True/False)

**Valid Config Values:**

| Field | Type | Valid Values | Default |
|-------|------|--------------|---------|
| `base_dir` | Path | Writable directory | `~/.aurora/plans` |
| `template_dir` | Path | Directory with .j2 files | `<package>/templates` |
| `auto_increment` | Bool | `true` or `false` | `true` |
| `archive_on_complete` | Bool | `true` or `false` | `false` |

---

### E008: Plan ID Collision

**Error Message:**
```
Error E008: Plan ID collision detected

Plan ID: 0003-caching-layer
Collision: Plan already exists at .aurora/plans/active/0003-caching-layer/

This should not happen with auto-increment enabled.
Retrying with next available ID...

Generated new ID: 0004-caching-layer
```

**Cause:**
- Race condition (two plans created simultaneously)
- Manual directory creation conflict
- Bug in auto-increment logic
- Corrupted manifest.json

**Solution:**

1. **Let system retry automatically:**
   The system will automatically retry with the next available ID (0004, 0005, etc.)

2. **If retries fail:**
   ```bash
   # Check for duplicate directories
   ls ~/.aurora/plans/active/ | grep "^[0-9]\{4\}-"

   # Manually resolve conflict
   # Option A: Delete the duplicate (if empty/test)
   rm -rf ~/.aurora/plans/active/0003-duplicate/

   # Option B: Rename manually to next ID
   mv ~/.aurora/plans/active/0003-duplicate ~/.aurora/plans/active/0004-duplicate
   ```

3. **Rebuild manifest:**
   ```bash
   rm ~/.aurora/plans/manifest.json
   aur plan list  # Rebuilds manifest automatically
   ```

4. **Report bug if persistent:**
   ```bash
   # This should be extremely rare
   # Report with:
   aur --version
   ls ~/.aurora/plans/active/ > active-plans.txt
   ls ~/.aurora/plans/archive/ > archived-plans.txt
   # Attach both files to bug report
   ```

**Prevention:**
- Don't manually create plan directories
- Don't run multiple `aur plan create` commands simultaneously
- Keep manifest.json up to date

**Note:** The system has automatic retry logic (up to 10 attempts), so this error is rare.

---

### E009: Atomic Operation Failed

**Error Message:**
```
Error E009: Atomic operation failed

Operation: Archive plan 0001-oauth-auth
Stage: Move to archive directory
Error: No space left on device

The operation was rolled back. No changes were made.
Original plan remains at: .aurora/plans/active/0001-oauth-auth/
```

**Cause:**
- Disk space exhausted during operation
- Filesystem error (I/O error, read-only)
- Permission denied mid-operation
- Network filesystem timeout (NFS, etc.)

**Solution:**

1. **Check disk space:**
   ```bash
   df -h ~/.aurora/
   # Free up space if needed
   ```

2. **Check filesystem errors:**
   ```bash
   # Check for read-only filesystem
   touch ~/.aurora/test-write && rm ~/.aurora/test-write

   # Check system logs
   dmesg | grep -i "error\|failed"
   ```

3. **Retry operation:**
   ```bash
   # After fixing the issue:
   aur plan archive 0001 --force
   ```

4. **Manual recovery (if needed):**
   ```bash
   # Check temp directory for partial files
   ls ~/.aurora/plans/.tmp/

   # Clean up temp files
   rm -rf ~/.aurora/plans/.tmp/*
   ```

**Prevention:**
- Ensure sufficient disk space (recommend 1GB+ free)
- Use local filesystem (avoid network drives for .aurora/)
- Regular monitoring of disk usage
- Backup important plans

**Rollback Behavior:**
The system automatically rolls back failed operations:
- Temp files are cleaned up
- Original plan remains untouched
- No partial state left behind

---

### E010: Missing Required File

**Error Message:**
```
Error E010: Missing required file(s)

Plan: 0001-oauth-auth
Location: .aurora/plans/active/0001-oauth-auth/

Missing files:
  ✗ tasks.md - Implementation task checklist (REQUIRED)
  ✗ agents.json - Machine-readable metadata (REQUIRED)

Optional files (warnings only):
  ⚠ specs/planning/oauth-auth-planning.md
  ⚠ specs/validation/oauth-auth-validation.md

To fix: Recreate plan or restore files from backup.
```

**Cause:**
- Manual deletion of plan files
- Incomplete plan creation (interrupted)
- Filesystem corruption
- Accidental `rm` command

**Solution:**

1. **Restore from backup:**
   ```bash
   # If you have backups
   cp backup/0001-oauth-auth/tasks.md .aurora/plans/active/0001-oauth-auth/
   cp backup/0001-oauth-auth/agents.json .aurora/plans/active/0001-oauth-auth/
   ```

2. **Restore from git (if versioned):**
   ```bash
   git checkout .aurora/plans/active/0001-oauth-auth/tasks.md
   git checkout .aurora/plans/active/0001-oauth-auth/agents.json
   ```

3. **Recreate files manually:**

   **tasks.md template:**
   ```markdown
   # Task Checklist: [Plan Name]

   ## Subgoal 1: [Title]

   - [ ] 1.1 First task
   - [ ] 1.2 Second task

   ## Subgoal 2: [Title]

   - [ ] 2.1 First task
   - [ ] 2.2 Second task
   ```

   **agents.json template:**
   ```json
   {
     "plan_id": "0001-oauth-auth",
     "goal": "Implement OAuth2 authentication",
     "status": "pending",
     "created_at": "2026-01-15T10:30:00Z",
     "subgoals": []
   }
   ```

4. **Recreate entire plan (last resort):**
   ```bash
   # Archive broken plan
   mv ~/.aurora/plans/active/0001-oauth-auth ~/.aurora/plans/broken/

   # Create new plan (will get new ID)
   aur plan create "Same goal as before"
   ```

**Prevention:**
- Version control .aurora/ directory with git
- Regular backups of active plans
- Use `aur plan archive` instead of manual deletion
- Don't manually delete files from plan directories

**Required Files (4):**
1. `plan.md` - Plan overview
2. `prd.md` - Requirements document
3. `tasks.md` - Task checklist
4. `agents.json` - Machine metadata

**Optional Files (4):**
- `specs/planning/*.md` - Planning spec
- `specs/commands/*.md` - Commands spec
- `specs/validation/*.md` - Validation spec
- `specs/schemas/*.md` - Schemas spec

---

## Error Code Summary Table

| Code | Error | Severity | Auto-Recoverable |
|------|-------|----------|------------------|
| E001 | Plan directory not writable | Error | No - requires manual fix |
| E002 | Invalid plan ID format | Error | No - requires manual fix |
| E003 | Plan not found | Error | No - user must provide valid ID |
| E004 | agents.json validation error | Error | No - requires manual fix |
| E005 | Template rendering failed | Error | No - requires reinstall or bug report |
| E006 | Archive failed (incomplete) | Warning | Yes - use --force flag |
| E007 | Config value invalid | Error | No - requires config fix |
| E008 | Plan ID collision | Warning | Yes - automatic retry |
| E009 | Atomic operation failed | Error | Yes - automatic rollback |
| E010 | Missing required file | Error | No - requires file restoration |

---

## Troubleshooting Workflow

### General Debugging Steps

1. **Check Aurora version:**
   ```bash
   aur --version
   ```

2. **Verify installation:**
   ```bash
   which aur
   pip show aurora-planning
   ```

3. **Check plans directory:**
   ```bash
   echo $AURORA_PLANS_DIR
   ls -la ~/.aurora/plans/
   ```

4. **Enable debug logging:**
   ```bash
   export AURORA_LOG_LEVEL=DEBUG
   aur plan create "Test" 2>&1 | tee debug.log
   ```

5. **Validate config:**
   ```bash
   aur config show
   ```

### Common Error Patterns

**Pattern: Permission Errors**
- E001: Plan directory not writable
- E009: Atomic operation failed (permission denied)

**Solution:** Fix directory permissions
```bash
chmod -R 755 ~/.aurora/plans/
chown -R $USER:$USER ~/.aurora/plans/
```

---

**Pattern: Validation Errors**
- E002: Invalid plan ID format
- E004: agents.json validation error

**Solution:** Use auto-generated IDs and don't manually edit agents.json
```bash
# Let system generate IDs
aur plan create "Your goal"

# Validate agents.json
python -c "import json; json.load(open('agents.json'))"
```

---

**Pattern: Missing Files/Directories**
- E003: Plan not found
- E010: Missing required file

**Solution:** Verify plan exists and restore missing files
```bash
# List plans
aur plan list --all

# Restore from git/backup
git checkout .aurora/plans/active/0001-*/
```

---

## Getting Help

### Support Channels

1. **Documentation:**
   - [User Guide](user-guide.md) - Complete workflow guide
   - [API Reference](api-reference.md) - Full API documentation
   - [Package README](../../packages/planning/README.md) - Quick start

2. **Community:**
   - GitHub Issues: https://github.com/aurora-project/aurora/issues
   - GitHub Discussions: https://github.com/aurora-project/aurora/discussions

3. **Bug Reports:**
   Include:
   - Error code and full error message
   - Aurora version (`aur --version`)
   - Operating system and Python version
   - Steps to reproduce
   - Relevant log files

### Reporting Bugs

When reporting an error:

```bash
# Gather system info
aur --version > bug-report.txt
python --version >> bug-report.txt
uname -a >> bug-report.txt

# Gather error logs
export AURORA_LOG_LEVEL=DEBUG
aur plan create "Test" 2>&1 >> bug-report.txt

# Attach bug-report.txt to GitHub issue
```

---

**Aurora Planning Error Code Reference** - Version 0.1.0
