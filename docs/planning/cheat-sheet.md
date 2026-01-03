# Aurora Planning - Command Cheat Sheet

**Quick reference for all Aurora Planning commands**

Version: 0.1.0 | One-page printable reference

---

## Core Commands

| Command | Syntax | Example | Description |
|---------|--------|---------|-------------|
| **init** | `aur plan init [--path <dir>]` | `aur plan init` | Initialize planning directory structure (.aurora/plans/) |
| **create** | `aur plan create <goal> [options]` | `aur plan create "Add OAuth2 auth"` | Create new plan with 8 files (auto-incrementing ID) |
| **list** | `aur plan list [options]` | `aur plan list --all` | List active/archived plans in table format |
| **view** | `aur plan view <plan_id> [options]` | `aur plan view 0001` | Display plan details with progress tracking |
| **archive** | `aur plan archive <plan_id> [options]` | `aur plan archive 0001 --yes` | Archive completed plan with timestamp |

---

## Command Options

### `aur plan init`

```bash
aur plan init [--path <dir>]
```

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--path` | - | Path | `.` | Directory to initialize (creates .aurora/) |

**Creates:**
- `.aurora/plans/active/` - Active plans directory
- `.aurora/plans/archive/` - Archived plans directory
- `.aurora/config/tools/` - Tool configurations
- `.aurora/project.md` - Project context template
- `AGENTS.md` - Agent registry (root level)

---

### `aur plan create`

```bash
aur plan create <goal> [--context <file>] [--no-decompose] [--format rich|json] [--no-auto-init]
```

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| **goal** | - | **Required** | - | Goal description (10-500 chars) |
| `--context` | `-c` | Path | - | Context files for decomposition (multiple allowed) |
| `--no-decompose` | - | Flag | false | Skip SOAR decomposition (single-task plan) |
| `--format` | `-f` | Choice | `rich` | Output format: `rich` or `json` |
| `--no-auto-init` | - | Flag | false | Disable auto-init if .aurora/ missing |

**Examples:**

```bash
# Simple plan creation
aur plan create "Implement OAuth2 authentication"

# With context files
aur plan create "Add caching" -c src/api.py -c src/database.py

# Skip decomposition for simple tasks
aur plan create "Fix typo in README" --no-decompose

# JSON output for scripts
aur plan create "Add monitoring" --format json
```

**Generates (8 files):**
1. `plan.md` - Plan overview
2. `prd.md` - Requirements document
3. `tasks.md` - Task checklist
4. `agents.json` - Machine metadata
5. `specs/planning/*.md` - Planning spec
6. `specs/commands/*.md` - Commands spec
7. `specs/validation/*.md` - Validation spec
8. `specs/schemas/*.md` - Schemas spec

---

### `aur plan list`

```bash
aur plan list [--archived] [--all] [--format rich|json]
```

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--archived` | - | Flag | false | Show archived plans only |
| `--all` | - | Flag | false | Show both active and archived plans |
| `--format` | `-f` | Choice | `rich` | Output format: `rich` or `json` |

**Examples:**

```bash
# List active plans (default)
aur plan list

# List archived plans
aur plan list --archived

# List all plans
aur plan list --all

# JSON output
aur plan list --format json | jq '.plans[0].plan_id'
```

**Output Columns:**
- **Plan ID** - Numeric ID with slug (0001-oauth-auth)
- **Title** - Goal description (first 50 chars)
- **Progress** - Tasks complete/total (12/24)
- **Last Modified** - Relative time (2 hours ago)

---

### `aur plan view`

```bash
aur plan view <plan_id> [--archived] [--format rich|json]
```

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| **plan_id** | - | **Required** | - | Plan ID (full or partial: 0001, oauth, auth) |
| `--archived` | - | Flag | false | Include archived plans in search |
| `--format` | `-f` | Choice | `rich` | Output format: `rich` or `json` |

**Examples:**

```bash
# View by full ID
aur plan view 0001-oauth-authentication

# View by numeric ID
aur plan view 0001

# View by partial match (first match wins)
aur plan view oauth

# Include archived plans
aur plan view 0001 --archived

# JSON output
aur plan view 0001 --format json
```

**Output Sections:**
- **Header** - Plan ID, goal, status, dates
- **Progress** - Task completion (12/24, 50%)
- **Subgoals** - List with agent assignments
- **Files** - File status (✓ exists, ✗ missing)
- **Next Steps** - Suggested actions

---

### `aur plan archive`

```bash
aur plan archive <plan_id> [--yes]
```

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| **plan_id** | - | **Required** | - | Plan ID to archive (full or partial) |
| `--yes` | `-y` | Flag | false | Skip confirmation prompt |

**Examples:**

```bash
# Archive with confirmation
aur plan archive 0001

# Skip confirmation
aur plan archive 0001 --yes

# Partial ID matching
aur plan archive oauth --yes
```

**Archive Behavior:**
- Moves from `active/0001-oauth-auth/` to `archive/2026-01-15-0001-oauth-auth/`
- Updates `agents.json` with `status: archived` and `archived_at` timestamp
- Uses atomic operations (rollback on error)
- Preserves all files and directory structure

---

## Environment Variables

Override default configuration:

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AURORA_PLANS_DIR` | Path | `~/.aurora/plans` | Base directory for plans |
| `AURORA_TEMPLATE_DIR` | Path | `<package>/templates` | Template directory |
| `AURORA_PLANNING_AUTO_INCREMENT` | Bool | `true` | Enable auto-increment IDs |
| `AURORA_PLANNING_ARCHIVE_ON_COMPLETE` | Bool | `false` | Auto-archive at 100% completion |

**Examples:**

```bash
# Use custom plans directory
export AURORA_PLANS_DIR=/projects/my-app/plans
aur plan create "Test"

# Use custom templates
export AURORA_TEMPLATE_DIR=~/.aurora/custom-templates
aur plan create "Test"

# Disable auto-increment (manual IDs)
export AURORA_PLANNING_AUTO_INCREMENT=false
```

---

## Directory Structure

### Default Layout

```
.aurora/
├── plans/
│   ├── active/                          # Active plans
│   │   ├── 0001-oauth-auth/
│   │   │   ├── plan.md
│   │   │   ├── prd.md
│   │   │   ├── tasks.md
│   │   │   ├── agents.json
│   │   │   └── specs/
│   │   │       ├── planning/
│   │   │       │   └── oauth-auth-planning.md
│   │   │       ├── commands/
│   │   │       │   └── oauth-auth-commands.md
│   │   │       ├── validation/
│   │   │       │   └── oauth-auth-validation.md
│   │   │       └── schemas/
│   │   │           └── oauth-auth-schemas.md
│   │   ├── 0002-user-registration/
│   │   └── 0003-caching-layer/
│   └── archive/                         # Archived plans
│       ├── 2026-01-10-0001-oauth-auth/  # Same structure as active
│       └── 2026-01-12-0002-user-registration/
├── config/
│   └── tools/                           # Tool configurations
└── project.md                           # Project context
```

### Plan Directory (8 Files)

Each plan contains:

| File | Purpose | Format | Required |
|------|---------|--------|----------|
| `plan.md` | Plan overview with subgoals | Markdown | ✓ Yes |
| `prd.md` | Product requirements document | Markdown | ✓ Yes |
| `tasks.md` | Implementation task checklist (GFM) | Markdown | ✓ Yes |
| `agents.json` | Machine-readable metadata | JSON | ✓ Yes |
| `specs/planning/*.md` | Planning capability spec | Markdown | Optional |
| `specs/commands/*.md` | Command schemas | Markdown | Optional |
| `specs/validation/*.md` | Validation rules | Markdown | Optional |
| `specs/schemas/*.md` | Data schemas | Markdown | Optional |

---

## Plan ID Format

### Active Plans

```
Format: NNNN-slug
Example: 0001-oauth2-authentication

Components:
- NNNN: Zero-padded 4-digit number (auto-incrementing)
- slug: URL-safe slug from goal text (max 30 chars)
```

### Archived Plans

```
Format: YYYY-MM-DD-NNNN-slug
Example: 2026-01-15-0001-oauth2-authentication

Components:
- YYYY-MM-DD: Archive date (ISO 8601)
- NNNN-slug: Original plan ID preserved
```

### ID Generation Rules

1. Scan both `active/` and `archive/` directories
2. Extract all numeric IDs (0001, 0002, etc.)
3. Find highest number across both
4. Increment by 1
5. Generate slug from goal text
6. Check for collisions, retry if needed

**Note:** IDs are never reused, even after archiving.

---

## Status Values

### Plan Status

| Status | Description | Color |
|--------|-------------|-------|
| `pending` | Plan created, not started | Yellow |
| `in_progress` | Work in progress | Blue |
| `complete` | All tasks finished | Green |
| `archived` | Completed and archived | Gray |

### Subgoal Status

| Status | Description | Icon |
|--------|-------------|------|
| `pending` | Not started | ○ |
| `in_progress` | Currently working on | → |
| `complete` | Finished | ✓ |

---

## Common Workflows

### Workflow 1: Create and Track Plan

```bash
# 1. Initialize (first time only)
aur plan init

# 2. Create plan
aur plan create "Implement OAuth2 authentication"

# 3. Review generated files
cd .aurora/plans/active/0001-oauth2-authentication
cat plan.md

# 4. Work on tasks (edit tasks.md, check off items)
vi tasks.md

# 5. Check progress
aur plan view 0001

# 6. Archive when complete
aur plan archive 0001 --yes
```

### Workflow 2: List and Filter

```bash
# List active plans
aur plan list

# Find specific plan
aur plan list | grep oauth

# List all plans (active + archived)
aur plan list --all

# Export to JSON for processing
aur plan list --format json > plans.json
jq '.plans[] | select(.progress.percentage < 50)' plans.json
```

### Workflow 3: Batch Operations (Scripting)

```bash
#!/bin/bash
# Create multiple plans from list

while IFS= read -r goal; do
  echo "Creating plan: $goal"
  aur plan create "$goal" --no-decompose --format json
done < goals.txt

# Archive all completed plans
aur plan list --format json | \
  jq -r '.plans[] | select(.progress.percentage == 100) | .plan_id' | \
  while read plan_id; do
    aur plan archive "$plan_id" --yes
  done
```

---

## Validation

### Plan Validation Checks

| Check | Required | Error if Missing |
|-------|----------|------------------|
| `plan.md` exists | Yes | ✓ |
| `prd.md` exists | Yes | ✓ |
| `tasks.md` exists | Yes | ✓ |
| `agents.json` exists | Yes | ✓ |
| `agents.json` valid JSON | Yes | ✓ |
| `agents.json` schema valid | Yes | ✓ |
| Capability specs exist | No | Warning only |
| Plan ID matches directory | Yes | ✓ |

### agents.json Schema

```json
{
  "plan_id": "0001-oauth-auth",           // Required: NNNN-slug format
  "goal": "Implement OAuth2...",          // Required: 10-500 chars
  "status": "pending",                    // Required: valid status
  "created_at": "2026-01-15T10:30:00Z",   // Required: ISO 8601
  "archived_at": "2026-01-20T15:00:00Z",  // Optional: ISO 8601
  "subgoals": [                           // Optional: array
    {
      "id": "sg-1",                       // Required: sg-N format
      "title": "Design flow",             // Required: 3-200 chars
      "description": "...",               // Optional: string
      "agent_id": "@architect",           // Required: @agent-name format
      "status": "pending",                // Required: valid status
      "dependencies": ["sg-0"]            // Optional: array of sg-N
    }
  ]
}
```

---

## Troubleshooting

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Planning directory not initialized` | `.aurora/` missing | Run `aur plan init` |
| `Plan not found: 0005` | Invalid plan ID | Check with `aur plan list` |
| `Template rendering failed` | Missing templates | Reinstall: `pip install -e .` |
| `Permission denied` | Wrong permissions | `chmod 755 .aurora/plans/active/` |
| `Validation failed` | Invalid agents.json | Fix JSON syntax, check schema |

### Debug Commands

```bash
# Verify installation
aur --version
aur plan --help

# Check plans directory
echo $AURORA_PLANS_DIR
ls -la ~/.aurora/plans/

# Verify templates exist
python -c "from aurora_planning.planning_config import get_template_dir; print(get_template_dir())"

# Enable debug logging
export AURORA_LOG_LEVEL=DEBUG
aur plan create "Test" 2>&1 | tee debug.log
```

---

## Quick Reference Card (Printable)

```
┌─────────────────────────────────────────────────────────────────┐
│                  AURORA PLANNING QUICK REFERENCE                │
├─────────────────────────────────────────────────────────────────┤
│ COMMANDS                                                        │
│  aur plan init                    Initialize .aurora/           │
│  aur plan create <goal>           Create new plan               │
│  aur plan list                    List active plans             │
│  aur plan view <id>               Show plan details             │
│  aur plan archive <id>            Archive completed plan        │
│                                                                 │
│ COMMON OPTIONS                                                  │
│  --format json                    JSON output for scripts       │
│  --archived                       Include archived plans        │
│  --yes, -y                        Skip confirmations            │
│  --context, -c <file>             Add context files             │
│                                                                 │
│ PLAN ID FORMAT                                                  │
│  Active:   0001-oauth-auth                                      │
│  Archived: 2026-01-15-0001-oauth-auth                           │
│                                                                 │
│ DIRECTORY STRUCTURE                                             │
│  .aurora/plans/active/            Active plans                  │
│  .aurora/plans/archive/           Archived plans                │
│                                                                 │
│ 8 FILES PER PLAN                                                │
│  plan.md, prd.md, tasks.md, agents.json                         │
│  + 4 capability specs in specs/                                 │
│                                                                 │
│ ENV VARS                                                        │
│  AURORA_PLANS_DIR                 Custom plans directory        │
│  AURORA_TEMPLATE_DIR              Custom template directory     │
│                                                                 │
│ DOCS: docs/planning/user-guide.md                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Resources

- **User Guide**: [user-guide.md](user-guide.md) - Complete workflow documentation
- **API Reference**: [api-reference.md](api-reference.md) - Full API documentation
- **Package README**: [../../packages/planning/README.md](../../packages/planning/README.md) - Installation and overview

---

**Aurora Planning Cheat Sheet** - Version 0.1.0 | One-page reference
