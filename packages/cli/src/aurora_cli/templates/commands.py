"""Templates for Aurora Claude Code slash commands.

This module provides template content for .claude/commands/aur/*.md files.
These commands provide convenient Claude Code slash command integrations.
"""

from typing import Dict  # noqa: F401


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
aur plan show <plan-id>

# Create new plan
aur plan create "Add user authentication"

# Validate plan structure
aur plan validate <plan-id>
```

**Plan structure:**
- `.aurora/plans/active/` - Work in progress
- `.aurora/plans/archive/` - Completed plans
<!-- AURORA:END -->
"""

CHECKPOINT_COMMAND = """---
name: Checkpoint
description: Save session context for continuity across compaction or handoffs.
category: Aurora
tags: [memory, session, context, handoff]
---
<!-- AURORA:START -->
**What this does:**
Save current session state to `.aurora/session.md` for continuity across
compaction or CLI handoffs. Keeps the last 3 checkpoints (~1500 tokens total).

**When to use:**
- Before context compaction
- At critical decision points
- Before switching between CLIs
- End of complex work sessions

**Steps:**
1. Invoke `/checkpoint` (or `aur:checkpoint` depending on your CLI)
2. Claude creates/updates `.aurora/session.md` with:
   - Current intent and progress
   - Key decisions made
   - Current state and blockers
   - Files being modified
   - Next steps

**After Compaction:**
Reference session history with: `@.aurora/session.md`

**Format:**
```markdown
# Session Checkpoints

---
## @ 2024-01-04 15:45
**Intent:** {What are we trying to accomplish?}
**Progress:** {Checklist: [x] done, [ ] pending}
**Decisions:** {Key choices made and why}
**State:** {Current status, blockers}
**Hot Files:** {Files actively modified}
**Next:** {What should happen next}
```

**Rules:**
- ~500 tokens per checkpoint (concise, specific)
- Latest checkpoint prepended (newest on top)
- Auto-trims to last 3 checkpoints
- Survives compaction (file-based, not conversation)

**Example Usage:**
```
You: /checkpoint
Claude: [Saves session state to .aurora/session.md]

[... auto-compaction happens ...]

You: Continue from @.aurora/session.md
Claude: [Reads checkpoints, resumes with context]
```
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

HEADLESS_COMMAND = """---
name: Aurora: Headless
description: Autonomous Claude execution loop
category: Aurora
tags: [aurora, headless, autonomous, loop]
---
<!-- AURORA:START -->
**What this does:**
Run Claude autonomously in a loop until it achieves a goal or reaches max iterations.
Claude manages its own state via a scratchpad file.

**Setup:**
```bash
# Create prompt from template
cp .aurora/headless/prompt.md.template .aurora/headless/prompt.md
# Edit prompt.md with your goal
```

**Usage (3 forms):**
```bash
# Form 1: Default prompt (.aurora/headless/prompt.md)
aur headless --max=10

# Form 2: Custom prompt file
aur headless -p my-task.md --max=10

# Form 3: With test backpressure
aur headless --test-cmd "pytest tests/" --max=15
```

**How it works:**
1. Claude reads your prompt (goal + instructions)
2. Claude works autonomously, rewriting `.aurora/headless/scratchpad.md`
3. Loop checks for `STATUS: DONE` in scratchpad
4. Exits early when done, or after max iterations

**Key files:**
- `.aurora/headless/prompt.md` - Your goal and instructions
- `.aurora/headless/scratchpad.md` - Claude's state (rewritten each iteration)

**Safety:**
- Blocked on main/master branch by default (use `--allow-main` to override)
- Max iterations prevent runaway execution
<!-- AURORA:END -->
"""


# Dictionary of all command templates
COMMAND_TEMPLATES: dict[str, str] = {
    "plan": PLAN_COMMAND,
    "checkpoint": CHECKPOINT_COMMAND,
    "archive": ARCHIVE_COMMAND,
    "headless": HEADLESS_COMMAND,
}
