"""Templates for Aurora Claude Code slash commands.

This module provides template content for .claude/commands/aur/*.md files.
These commands provide convenient Claude Code slash command integrations.
"""


def get_command_template(command_name: str) -> str | None:
    """Get the template for a specific command.

    Args:
        command_name: Name of the command (e.g., "init", "query")

    Returns:
        Template content or None if command not found

    """
    return COMMAND_TEMPLATES.get(command_name)


def get_all_command_templates() -> dict[str, str]:
    """Get all available command templates.

    Returns:
        Dictionary mapping command names to template content

    """
    return COMMAND_TEMPLATES.copy()


# Individual command templates
PLAN_COMMAND = """---
name: Aurora Plan
description: Manage Aurora planning workflows and change proposals.
category: Aurora
tags: [aurora, planning, changes, workflow]
---
<!-- AURORA:START -->
**What this does:**
Manage planning workflows using Aurora's structured change system.
Creates, validates, and tracks implementation plans.

**Steps:**
1. Initialize planning: `aur init` (creates `.aurora/plans/`)
2. Use plan commands to manage your work

**Usage:**
```bash
# List active plans
aur plan list

# Show plan details
aur plan view <plan-id>

# Create new plan
aur plan create "Add user authentication"

# Archive completed plan
aur plan archive <plan-id>
```

**Plan structure:**
- `.aurora/plans/active/` - Work in progress
- `.aurora/plans/archive/` - Completed plans
<!-- AURORA:END -->
"""

ARCHIVE_COMMAND = """---
name: Aurora: Archive
description: Archive completed plans with spec processing
category: Aurora
tags: [aurora, planning, archive]
---
<!-- AURORA:START -->
**What this does:**
Archive a completed Aurora plan, moving it from active to archive directory
with timestamp prefix and updating manifest.

**Steps:**
1. Identify completed plan: `aur plan list`
2. Archive the plan: `aur plan archive <plan-id>`

**Usage:**
```bash
# Archive with confirmation
aur plan archive 0001-oauth-auth

# Archive without confirmation
aur plan archive 0001-oauth -y
```

**What happens:**
- Plan moved from `.aurora/plans/active/` to `.aurora/plans/archive/`
- Directory renamed with timestamp: `YYYY-MM-DD-<plan-id>`
- Plan status updated to "archived"
- Duration calculated from creation to archive date
- Manifest updated with archive metadata

**Example:**
```bash
# Before archive:
.aurora/plans/active/0001-oauth-auth/

# After archive:
.aurora/plans/archive/2024-01-15-0001-oauth-auth/
```
<!-- AURORA:END -->
"""

# Dictionary of all command templates
COMMAND_TEMPLATES: dict[str, str] = {
    "plan": PLAN_COMMAND,
    "archive": ARCHIVE_COMMAND,
}
