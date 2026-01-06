"""Template bodies for Aurora slash commands.

Each template provides instructions for AI coding tools on how to execute
the corresponding Aurora command.
"""

# Base guardrails for all commands
BASE_GUARDRAILS = """**Guardrails**
- Favor straightforward, minimal implementations first and add complexity only when requested or clearly required.
- Keep changes tightly scoped to the requested outcome.
- Refer to `.aurora/AGENTS.md` if you need additional Aurora conventions or clarifications."""

# /aur:plan - Plan generation command
PLAN_TEMPLATE = f"""{BASE_GUARDRAILS}
- Identify any vague or ambiguous details and ask the necessary follow-up questions before creating the plan.
- Do not write any code during planning. Only create design documents (plan.md, prd.md, tasks.md).

**Steps**
1. Review existing plans with `aur plan list` and codebase context to ground the plan in current behavior.
2. Choose a unique descriptive plan ID (e.g., "0001-oauth-auth") and create plan.md with high-level overview.
3. If user confirms, expand to prd.md with detailed requirements and acceptance criteria.
4. Generate tasks.md with ordered, verifiable work items that deliver incremental progress.
5. Use `aur agents search` to find relevant agents for subgoals.
6. Validate with `aur plan show <id>` before sharing the plan.

**Reference**
- Use `aur plan list` to see existing plans
- Use `aur agents list` to see available agents
- Search codebase with memory system: `aurora_query` MCP tool or `aur mem search`"""

# /aur:checkpoint - Save session context
CHECKPOINT_TEMPLATE = f"""{BASE_GUARDRAILS}

**Usage**
Save current session context to preserve conversation state across compaction or handoffs.

**What it does**
1. Captures current conversation context and key decisions
2. Records active work in progress
3. Stores important findings and insights
4. Creates checkpoint file in `.aurora/checkpoints/`
5. Enables context restoration after compaction

**When to use**
- Before long-running tasks that may trigger compaction
- When handing off work to another agent or session
- After completing major investigation or analysis
- Before taking a break from complex multi-step work

**Commands**
```bash
# Create checkpoint with auto-generated name
aur checkpoint save

# Create checkpoint with custom name
aur checkpoint save "feature-auth-investigation"

# List available checkpoints
aur checkpoint list

# Restore from checkpoint
aur checkpoint restore <checkpoint-name>
```

**Reference**
- Checkpoints stored in `.aurora/checkpoints/`
- Automatically includes: timestamp, active plan, recent decisions
- Maximum context retention with minimal token usage"""

# /aur:archive - Archive completed plans
ARCHIVE_TEMPLATE = f"""{BASE_GUARDRAILS}

**Usage**
Archive completed plans with spec delta processing and validation.

**What it does**
1. Validates plan structure and task completion
2. Processes capability specification deltas (ADDED/MODIFIED/REMOVED/RENAMED)
3. Updates capability specs in `.aurora/capabilities/`
4. Moves plan to archive with timestamp: `.aurora/plans/archive/YYYY-MM-DD-<plan-id>/`
5. Updates agents.json with `archived_at` timestamp

**Commands**
```bash
# Archive specific plan
aur plan archive 0001-oauth-auth

# Interactive selection (lists all active plans)
aur plan archive

# Archive with flags
aur plan archive 0001 --yes              # Skip confirmations
aur plan archive 0001 --skip-specs       # Skip spec delta processing
aur plan archive 0001 --no-validate      # Skip validation (with warning)
```

**Validation checks**
- Task completion status (warns if < 100%)
- Plan directory structure
- Spec delta conflicts and duplicates
- Agent assignments and gaps

**Reference**
- Plans archived to `.aurora/plans/archive/`
- Specs updated in `.aurora/capabilities/<capability>/spec.md`
- Incomplete plans can be archived with explicit confirmation"""

# Command templates dictionary
COMMAND_TEMPLATES: dict[str, str] = {
    "plan": PLAN_TEMPLATE,
    "checkpoint": CHECKPOINT_TEMPLATE,
    "archive": ARCHIVE_TEMPLATE,
}


def get_command_body(command_id: str) -> str:
    """Get the template body for a command.

    Args:
        command_id: Command identifier (e.g., "plan", "query")

    Returns:
        Template body string

    Raises:
        KeyError: If command_id is not found
    """
    if command_id not in COMMAND_TEMPLATES:
        raise KeyError(f"Unknown command: {command_id}")

    return COMMAND_TEMPLATES[command_id]
