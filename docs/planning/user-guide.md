# Aurora Planning System - User Guide

**Complete guide to structured plan creation and management in Aurora**

Version: 1.0 | Last Updated: 2026-01-03

---

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Planning Workflow](#planning-workflow)
4. [Working with Plans](#working-with-plans)
5. [Best Practices](#best-practices)
6. [Troubleshooting](#troubleshooting)
7. [FAQ](#faq)
8. [Advanced Topics](#advanced-topics)

---

## Introduction

### What is Aurora Planning?

Aurora Planning is a structured approach to breaking down complex development goals into actionable, manageable plans. It provides:

- **Automated Decomposition**: AI-powered goal breakdown into subgoals
- **Agent Assignment**: Intelligent recommendation of AI agents for each task
- **Progress Tracking**: Built-in status tracking and completion metrics
- **Archive Management**: Historical record of completed plans
- **Rich Terminal UI**: Beautiful, informative command-line interface

### When to Use Planning

Use Aurora Planning when you need to:

- Break down a complex feature into manageable steps
- Coordinate work across multiple components or systems
- Track progress on multi-day or multi-week projects
- Document requirements before implementation
- Maintain a historical record of architectural decisions

### When NOT to Use Planning

Skip planning for:

- Simple one-liner fixes (typos, formatting)
- Documentation-only changes
- Emergency hotfixes requiring immediate action
- Experimental proof-of-concepts

---

## Getting Started

### Prerequisites

- Aurora CLI installed (`aur --version` should work)
- Python 3.10 or higher
- Basic familiarity with command-line tools

### Installation Check

Verify your Aurora Planning installation:

```bash
# Check Aurora CLI
aur --version

# Check planning commands are available
aur plan --help
```

Expected output:
```
Usage: aur plan [OPTIONS] COMMAND [ARGS]...

  Plan management commands.

  Create, list, view, and archive development plans.

Commands:
  create   Create a new plan with SOAR-based goal decomposition
  init     Initialize planning directory
  list     List active or archived plans
  view     Display plan details
  archive  Archive a completed plan
```

### First-Time Setup

Initialize the planning directory structure:

```bash
cd /path/to/your/project
aur plan init
```

This creates:
```
.aurora/
├── plans/
│   ├── active/     # Your active plans live here
│   └── archive/    # Completed plans are archived here
├── config/
│   └── tools/      # Tool-specific configurations
└── project.md      # Project context (fill this out!)
```

**Important**: Fill out `.aurora/project.md` with your project context. This helps AI agents understand your codebase structure.

---

## Planning Workflow

### Complete Workflow Example

Let's walk through creating, working on, and archiving a plan for implementing OAuth2 authentication.

#### Step 1: Create the Plan

```bash
aur plan create "Implement OAuth2 authentication with JWT tokens"
```

**Output:**
```
✓ Plan created: 0001-oauth2-authentication

Goal:
Implement OAuth2 authentication with JWT tokens

Subgoals:
  1. [sg-1] Design OAuth2 flow and endpoints → @architect
     Status: pending

  2. [sg-2] Implement token generation and validation → @backend-dev
     Status: pending | Dependencies: sg-1

  3. [sg-3] Add refresh token logic → @backend-dev
     Status: pending | Dependencies: sg-2

  4. [sg-4] Create authentication middleware → @backend-dev
     Status: pending | Dependencies: sg-2

  5. [sg-5] Add OAuth2 integration tests → @qa-engineer
     Status: pending | Dependencies: sg-4

Agent Status:
  ✓ @architect - Available
  ✓ @backend-dev - Available
  ✗ @qa-engineer - Not configured

  → Missing 1 agent. Run 'aur agents init' to configure.

Files generated (8):
  ✓ plan.md                           (2.3 KB)
  ✓ prd.md                            (4.1 KB)
  ✓ tasks.md                          (1.8 KB)
  ✓ agents.json                       (892 B)
  ✓ specs/planning/oauth2-auth-planning.md      (3.2 KB)
  ✓ specs/commands/oauth2-auth-commands.md      (2.1 KB)
  ✓ specs/validation/oauth2-auth-validation.md  (1.9 KB)
  ✓ specs/schemas/oauth2-auth-schemas.md        (2.7 KB)

Location: .aurora/plans/active/0001-oauth2-authentication/

Next Steps:
  1. Review plan.md and prd.md for accuracy
  2. Edit tasks.md to add specific implementation tasks
  3. Run 'aur plan view 0001' to see progress
  4. When complete, run 'aur plan archive 0001'
```

#### Step 2: Review the Generated Files

Open the plan directory and review the generated files:

```bash
cd .aurora/plans/active/0001-oauth2-authentication

# Review the plan overview
cat plan.md

# Review the PRD
cat prd.md

# Review the task checklist
cat tasks.md
```

**Tip**: Use your favorite editor to customize these files. They're plain Markdown and JSON!

#### Step 3: Customize Tasks

Edit `tasks.md` to add specific implementation tasks:

```markdown
# Task Checklist: OAuth2 Authentication

## Subgoal 1: Design OAuth2 flow and endpoints

- [ ] 1.1 Document authorization flow (3-legged OAuth)
- [ ] 1.2 Design token exchange endpoint schema
- [ ] 1.3 Define JWT payload structure
- [ ] 1.4 Review security requirements (PKCE, state parameter)

## Subgoal 2: Implement token generation and validation

- [ ] 2.1 Add JWT library dependency (PyJWT)
- [ ] 2.2 Implement token generation function
- [ ] 2.3 Implement token validation function
- [ ] 2.4 Add token expiration logic (access: 15min, refresh: 30d)
- [ ] 2.5 Write unit tests for token functions

...
```

#### Step 4: Track Progress

As you complete tasks, check them off in `tasks.md`:

```markdown
- [x] 1.1 Document authorization flow (3-legged OAuth)
- [x] 1.2 Design token exchange endpoint schema
- [ ] 1.3 Define JWT payload structure
```

View your progress:

```bash
aur plan view 0001
```

**Output:**
```
Plan: 0001-oauth2-authentication
Goal: Implement OAuth2 authentication with JWT tokens
Status: in_progress
Created: 2 days ago
Modified: 5 minutes ago

Progress: 12/24 tasks complete (50%)

Subgoals:
  ✓ [sg-1] Design OAuth2 flow and endpoints
    Status: complete | Agent: @architect

  → [sg-2] Implement token generation and validation
    Status: in_progress | Agent: @backend-dev
    Tasks: 3/5 complete

  ○ [sg-3] Add refresh token logic
    Status: pending | Agent: @backend-dev
    Blocked by: sg-2

  ...
```

#### Step 5: Archive When Complete

When all tasks are done, archive the plan:

```bash
aur plan archive 0001
```

**Output with Confirmation:**
```
Archive plan 0001-oauth2-authentication?

This will move the plan to:
  .aurora/plans/archive/2026-01-15-0001-oauth2-authentication/

The plan will be marked as 'archived' but all files will be preserved.

Continue? [y/N]: y

✓ Plan archived successfully

New location: .aurora/plans/archive/2026-01-15-0001-oauth2-authentication/
Archived at: 2026-01-15T14:32:00Z

To view archived plan: aur plan view 0001 --archived
```

---

## Working with Plans

### Listing Plans

#### List Active Plans

```bash
aur plan list
```

Output:
```
┏━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Plan ID ┃ Title                         ┃ Progress  ┃ Last Modified  ┃
┡━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ 0003    │ Add user dashboard            │ 8/15      │ 1 hour ago     │
│ 0002    │ User registration system      │ 12/12     │ 3 hours ago    │
│ 0001    │ OAuth2 authentication         │ 5/24      │ 1 day ago      │
└─────────┴───────────────────────────────┴───────────┴────────────────┘

3 active plans
```

#### List Archived Plans

```bash
aur plan list --archived
```

#### List All Plans

```bash
aur plan list --all
```

Output shows both active and archived with status indicators:
```
┏━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Plan ID ┃ Title                         ┃ Status    ┃ Last Modified  ┃
┡━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ 0003    │ Add user dashboard            │ Active    │ 1 hour ago     │
│ 0002    │ User registration system      │ Active    │ 3 hours ago    │
│ 0001    │ OAuth2 authentication         │ Archived  │ 5 days ago     │
└─────────┴───────────────────────────────┴───────────┴────────────────┘
```

#### JSON Output for Scripts

```bash
aur plan list --format json | jq '.plans[0].plan_id'
```

### Viewing Plan Details

#### View by Full ID

```bash
aur plan view 0001-oauth2-authentication
```

#### View by Partial ID

```bash
aur plan view 0001
# or
aur plan view oauth2
# or
aur plan view auth
```

The system matches the first plan that contains your partial ID.

#### View Archived Plans

```bash
aur plan view 0001 --archived
```

#### JSON Output

```bash
aur plan view 0001 --format json
```

Output includes full plan metadata:
```json
{
  "plan_id": "0001-oauth2-authentication",
  "goal": "Implement OAuth2 authentication with JWT tokens",
  "status": "in_progress",
  "created_at": "2026-01-13T10:30:00Z",
  "updated_at": "2026-01-15T14:20:00Z",
  "subgoals": [
    {
      "id": "sg-1",
      "title": "Design OAuth2 flow and endpoints",
      "status": "complete",
      "agent_id": "@architect"
    }
  ],
  "progress": {
    "completed": 12,
    "total": 24,
    "percentage": 50
  }
}
```

### Creating Plans with Context

Provide context files to inform the decomposition:

```bash
aur plan create "Add caching layer to API" \
  --context src/api/routes.py \
  --context src/database/queries.py \
  --context src/config/settings.py
```

The AI will analyze these files to:
- Understand your existing architecture
- Generate more specific subgoals
- Recommend appropriate agents
- Suggest relevant file paths in tasks

### Skipping Decomposition

For simple tasks, skip the SOAR decomposition:

```bash
aur plan create "Fix typo in user model docstring" --no-decompose
```

This creates a single-task plan without subgoal breakdown.

---

## Best Practices

### Plan Naming

**Good plan goals:**
- "Implement OAuth2 authentication with JWT tokens" ✓
- "Add Redis caching layer for API responses" ✓
- "Refactor user model to use SQLAlchemy 2.0 syntax" ✓

**Poor plan goals:**
- "Do the auth thing" ✗ (too vague)
- "Fix bug" ✗ (missing context)
- "Update code" ✗ (missing what/why)

**Guidelines:**
- Be specific about what you're building
- Include key technical terms (OAuth2, JWT, Redis)
- Keep it under 100 characters when possible
- Use action verbs (implement, add, refactor, fix)

### Task Organization

**Organize tasks hierarchically:**

```markdown
## Subgoal 1: Database Schema Design

- [ ] 1.1 Create ERD for new tables
- [ ] 1.2 Write migration scripts
- [ ] 1.3 Add indexes for performance

## Subgoal 2: API Implementation

- [ ] 2.1 Define API schemas
  - [ ] 2.1.1 Request schemas
  - [ ] 2.1.2 Response schemas
  - [ ] 2.1.3 Error schemas
- [ ] 2.2 Implement endpoints
- [ ] 2.3 Add validation
```

**Use time estimates:**

```markdown
- [ ] 1.1 Create ERD for new tables (~2h)
- [ ] 1.2 Write migration scripts (~4h)
- [ ] 1.3 Add indexes for performance (~1h)
```

### When to Archive

Archive a plan when:

- ✓ All tasks are complete (100% progress)
- ✓ Code is merged to main branch
- ✓ Tests are passing
- ✓ Documentation is updated
- ✓ Plan is no longer actively being worked on

**Don't archive if:**
- ✗ Tasks are incomplete (unless abandoning the plan)
- ✗ Code is still in PR review
- ✗ You plan to revisit it soon

### Using Context Files Effectively

**Best practices for `--context` flag:**

1. **Start small**: 1-3 files max for most plans
2. **Choose relevant files**: Only include files directly related to the goal
3. **Prefer entry points**: Main modules, route files, model definitions
4. **Avoid large files**: Skip generated files, logs, large data files

**Example:**

```bash
# Good: Focused, relevant context
aur plan create "Add user profile API" \
  --context src/api/user_routes.py \
  --context src/models/user.py

# Overkill: Too many unrelated files
aur plan create "Add user profile API" \
  --context src/**/*.py  # Don't do this!
```

### Collaborative Planning

When working with a team:

1. **Commit plan files**: Add `.aurora/plans/` to version control
2. **Review PRD together**: Use `prd.md` for alignment discussions
3. **Assign agents**: Map `@agent-id` to team members
4. **Track in standups**: Reference plan ID (0001) in updates
5. **Archive together**: Celebrate completion as a team

---

## Troubleshooting

### Common Errors

#### Error: "Planning directory not initialized"

**Symptoms:**
```bash
$ aur plan create "Test"
Error: Planning directory not initialized
```

**Solution:**
```bash
aur plan init
```

**Root Cause:** The `.aurora/plans/` directory doesn't exist yet.

---

#### Error: "Plan not found: 0005"

**Symptoms:**
```bash
$ aur plan view 0005
Error: Plan not found: 0005

Similar plans:
  - 0003-user-dashboard
  - 0004-api-refactor
```

**Solutions:**
1. Check plan ID: `aur plan list`
2. Search archived plans: `aur plan view 0005 --archived`
3. Use partial match: `aur plan view user`

**Root Cause:** Plan doesn't exist or was archived.

---

#### Error: "Template rendering failed"

**Symptoms:**
```bash
$ aur plan create "Test"
Error: Template rendering failed: plan.md.j2 not found
```

**Solution:**
```bash
# Verify template directory
python -c "from aurora_planning.planning_config import get_template_dir; print(get_template_dir())"

# Reinstall package if templates are missing
cd packages/planning
pip install -e .
```

**Root Cause:** Package installation issue or corrupted templates.

---

#### Error: "Permission denied: .aurora/plans/active/"

**Symptoms:**
```bash
$ aur plan create "Test"
Error: Permission denied: .aurora/plans/active/
```

**Solution:**
```bash
# Fix directory permissions
chmod 755 ~/.aurora/plans/active/

# Or create with correct permissions
aur plan init
```

**Root Cause:** Directory has incorrect permissions.

---

#### Warning: "agents.json validation failed"

**Symptoms:**
```bash
$ aur plan view 0001
Warning: agents.json validation failed: 'status' is required
```

**Solution:**
```bash
# Manually fix agents.json
cd .aurora/plans/active/0001-*
vi agents.json  # Add missing "status" field

# Or regenerate the plan
# (Warning: this will overwrite customizations)
aur plan create "Same goal as before"
```

**Root Cause:** Manual editing broke the JSON schema.

---

### Performance Issues

#### Slow Plan Creation (>10s)

**Potential Causes:**
1. Large context files (>100KB each)
2. Network latency to AI service
3. Disk I/O issues

**Solutions:**
1. Use smaller context files or fewer files
2. Check network connection
3. Use SSD for `.aurora/` directory

---

#### Slow Plan Listing (>2s)

**Potential Causes:**
1. Many plans (>100)
2. Manifest out of sync

**Solutions:**
```bash
# Rebuild manifest
aur plan list --rebuild-manifest

# Or manually:
rm .aurora/plans/manifest.json
aur plan list
```

---

### Data Recovery

#### Accidentally Deleted Plan

**If you haven't committed:**
```bash
# Check trash (macOS/Linux)
ls ~/.Trash/.aurora/

# Restore if found
mv ~/.Trash/.aurora/plans/active/0001-* .aurora/plans/active/
```

**If you have git:**
```bash
git checkout .aurora/plans/active/0001-*
```

---

#### Corrupted agents.json

**Quick Fix:**
```bash
cd .aurora/plans/active/0001-*/

# Validate JSON syntax
python -c "import json; json.load(open('agents.json'))"

# If invalid, restore from template
cp ../../../../templates/agents.json.j2 agents.json
# Then manually edit with correct values
```

---

## FAQ

### General Questions

#### Q1: Can I use Aurora Planning without AI agents?

**A:** Yes! Aurora Planning works perfectly as a standalone task management system. The eight-file structure and CLI commands are useful even if you never use the agent orchestration features. Think of it as a structured way to organize development work with excellent terminal UI.

---

#### Q2: How many plans can I have active at once?

**A:** There's no hard limit, but we recommend:
- **1-3 plans** for individual developers
- **5-10 plans** for small teams
- **10-20 plans** for larger teams

Having too many active plans makes it harder to track progress. Archive completed plans regularly.

---

#### Q3: Can I edit the generated files?

**A:** Absolutely! All files are plain Markdown and JSON. Edit them however you want. The system only reads/writes these files, never locks them. Use your favorite editor.

**Tip**: Keep backups before major edits, or use version control (git).

---

#### Q4: Are plans stored per-project or globally?

**A:** **Per-project** by default. Each project has its own `.aurora/plans/` directory.

You can use a global directory with:
```bash
export AURORA_PLANS_DIR=~/.aurora/plans-global
```

But we recommend per-project for better organization and version control.

---

#### Q5: Can I rename a plan after creation?

**A:** The plan ID (e.g., `0001-oauth-auth`) cannot be changed after creation (it's used as the directory name). However, you can:

1. Edit the `goal` field in `agents.json`
2. Edit the title in `plan.md` and `prd.md`
3. These changes will reflect in `aur plan list` and `aur plan view`

The directory name stays the same for consistency.

---

#### Q6: How do I delete a plan permanently?

**A:** Plans are never automatically deleted. To remove manually:

```bash
# Archive first (optional but recommended)
aur plan archive 0001

# Then manually delete
rm -rf .aurora/plans/archive/2026-01-15-0001-oauth-auth/

# Rebuild manifest
aur plan list --rebuild-manifest
```

**Warning**: This is permanent. Consider archiving instead of deleting.

---

### Workflow Questions

#### Q7: Should I create one big plan or multiple small plans?

**A:** **Multiple small plans** is usually better. Benefits:

- Easier to track progress
- Clearer scope boundaries
- Can archive incrementally
- Better for team coordination

**Example**: Instead of "Build entire API":
- Plan 0001: "Implement user authentication API"
- Plan 0002: "Add product catalog API"
- Plan 0003: "Implement order processing API"

---

#### Q8: How do I handle dependencies between plans?

**A:** Two approaches:

**1. Reference in PRD:**
```markdown
# Dependencies

This plan depends on:
- Plan 0001 (OAuth2 auth) must be complete
- Plan 0002 (Database migrations) must be deployed
```

**2. Use subgoal dependencies within a single plan:**
```json
{
  "subgoals": [
    {
      "id": "sg-2",
      "dependencies": ["sg-1"]  // sg-2 depends on sg-1
    }
  ]
}
```

---

#### Q9: When should I use `--no-decompose`?

**A:** Use `--no-decompose` for:
- Simple fixes (1-2 hours of work)
- Single-file changes
- Documentation updates
- Experimental changes

**Don't use** for:
- Multi-component features
- Cross-cutting changes
- Projects spanning multiple days

---

#### Q10: Can I nest plans (sub-plans)?

**A:** Not directly, but you can:

**1. Use subgoals** (the intended way):
Each plan has multiple subgoals that break down the work.

**2. Reference plans in PRD:**
```markdown
# Related Plans

This plan is part of the larger "V2 API Redesign" initiative:
- Phase 1: Plan 0008 (Authentication refactor)
- Phase 2: Plan 0009 (Database migration) ← This plan
- Phase 3: Plan 0010 (Frontend integration)
```

---

### Technical Questions

#### Q11: What's the format of agents.json?

**A:** See [JSON Schema](../../packages/planning/src/aurora_planning/schemas/agents.schema.json) for full specification.

**Quick reference:**
```json
{
  "plan_id": "0001-oauth-auth",
  "goal": "Implement OAuth2 authentication",
  "status": "pending|in_progress|complete|archived",
  "created_at": "2026-01-15T10:30:00Z",
  "archived_at": "2026-01-20T15:00:00Z",  // Optional
  "subgoals": [
    {
      "id": "sg-1",
      "title": "Design OAuth flow",
      "description": "Detailed description...",
      "agent_id": "@architect",
      "status": "pending|in_progress|complete",
      "dependencies": ["sg-0"]  // Optional
    }
  ]
}
```

---

#### Q12: Can I add custom fields to agents.json?

**A:** Yes! The schema allows additional fields:

```json
{
  "plan_id": "0001-oauth-auth",
  "goal": "...",
  "custom_field": "your value",
  "team": "backend-team",
  "sprint": "2026-01-S1"
}
```

**Note**: Custom fields are preserved but ignored by Aurora Planning commands.

---

#### Q13: How does plan ID auto-increment work?

**A:** The system:
1. Scans both `active/` and `archive/` directories
2. Extracts all numeric IDs (0001, 0002, etc.)
3. Finds the highest number
4. Increments by 1
5. Adds slug from goal text

**Example sequence:**
- First plan: `0001-oauth-auth`
- Second plan: `0002-user-registration`
- Archive 0001 → `2026-01-15-0001-oauth-auth`
- Third plan: `0003-caching-layer` (not reusing 0001)

---

#### Q14: What happens if I manually rename a plan directory?

**A:** The system will lose track of it. Commands like `aur plan view 0001` won't find it.

**Recovery:**
```bash
# Rename back to original
mv .aurora/plans/active/0001-renamed .aurora/plans/active/0001-oauth-auth

# Or rebuild manifest
aur plan list --rebuild-manifest
```

**Best practice**: Never manually rename plan directories. Edit file contents instead.

---

#### Q15: Can I use Aurora Planning in CI/CD?

**A:** Yes! Use JSON output format:

```bash
# In CI pipeline
aur plan create "Deploy to staging" --format json --no-decompose > plan.json
PLAN_ID=$(jq -r '.plan_id' plan.json)

# Later in pipeline
aur plan archive "$PLAN_ID" --yes
```

Disable interactive prompts:
```bash
export AURORA_PLANNING_AUTO_INIT=false
export AURORA_PLANNING_NO_CONFIRM=true
```

---

## Advanced Topics

### Custom Templates

Override default templates:

```bash
# 1. Copy default templates
mkdir -p ~/.aurora/templates
cp -r $(python -c "from aurora_planning.planning_config import get_template_dir; print(get_template_dir())")/* ~/.aurora/templates/

# 2. Customize templates
vi ~/.aurora/templates/plan.md.j2

# 3. Use custom templates
export AURORA_TEMPLATE_DIR=~/.aurora/templates
aur plan create "Test with custom template"
```

### Scripting with Aurora Planning

**Batch create plans:**

```bash
#!/bin/bash
for feature in "Add logging" "Add monitoring" "Add alerting"; do
  aur plan create "$feature" --no-decompose --format json
done
```

**Export all plans:**

```bash
#!/bin/bash
aur plan list --all --format json > all-plans.json

# Process with jq
jq '.plans[] | select(.status == "complete")' all-plans.json
```

### Integration with Git

**Track plans in version control:**

```bash
# Add to .gitignore (optional - only ignore work-in-progress)
echo ".aurora/plans/active/*" >> .gitignore

# Always commit archived plans (project history)
git add .aurora/plans/archive/
git commit -m "Archive completed plans"
```

**Pre-commit hook to check plan progress:**

```bash
#!/bin/bash
# .git/hooks/pre-commit

INCOMPLETE=$(aur plan list --format json | jq '.plans[] | select(.progress.percentage < 100) | .plan_id')

if [ -n "$INCOMPLETE" ]; then
  echo "Warning: Incomplete plans:"
  echo "$INCOMPLETE"
  read -p "Continue? [y/N] " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
  fi
fi
```

---

## Appendix: Complete Command Reference

See [Command Cheat Sheet](cheat-sheet.md) for quick reference.

---

**Questions or Issues?**

- GitHub Issues: https://github.com/aurora-project/aurora/issues
- Documentation: https://aurora-docs.example.com
- Package README: [packages/planning/README.md](../../packages/planning/README.md)

---

**Aurora Planning System** - Part of the Aurora Cognitive Architecture Project
