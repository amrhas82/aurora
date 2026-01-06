"""Template bodies for Aurora slash commands.

Each template provides instructions for AI coding tools on how to execute
the corresponding Aurora command.
"""

# Base guardrails for all commands
BASE_GUARDRAILS = """**Guardrails**
- Favor straightforward, minimal implementations first and add complexity only when requested or clearly required.
- Keep changes tightly scoped to the requested outcome.
- Refer to `.aurora/AGENTS.md` if you need additional Aurora conventions or clarifications."""

# /aur:search - Search indexed code
SEARCH_TEMPLATE = f"""{BASE_GUARDRAILS}

**Usage**
Search Aurora's indexed memory for code, documentation, or reasoning patterns.

**Command**
```bash
aur mem search "query text" --limit 10 --type code
```

**What it does**
1. Searches indexed memory (code, kb, soar chunks)
2. Uses hybrid scoring: BM25 + ACT-R activation + optional semantic
3. Returns top N results with relevance scores
4. Shows file path, chunk name, lines, and score

**Options**
- `--limit N` - Max results (default: 10)
- `--type TYPE` - Filter by chunk type (code, kb, soar)

**When to use**
- Find code by functionality ("authentication logic")
- Locate documentation ("setup guide")
- Find past reasoning patterns ("how we handled X")

**Example**
```bash
/aur:search authentication functions
# Returns: login(), verify_token(), authenticate_user()
```"""

# /aur:get - Get chunk by index
GET_TEMPLATE = f"""{BASE_GUARDRAILS}

**Usage**
Retrieve full content of a chunk after search.

**Workflow**
1. Search: `/aur:search query` or `aur mem search "query"`
2. Review results (numbered list)
3. Get: `/aur:get N` to retrieve full chunk N

**What it does**
- Retrieves complete chunk content
- Shows full code/documentation
- Includes metadata (file path, lines, type)

**Example**
```
User: Find login code
AI: /aur:search login
    Results: 1) login() 2) verify_login() 3) login_handler()
AI: /aur:get 1
    [Retrieves full login() function code]
```"""

# /aur:implement - Plan implementation (placeholder)
IMPLEMENT_TEMPLATE = f"""{BASE_GUARDRAILS}

**Status:** Placeholder in v0.5.0

**Future Vision**
Plan-based implementation that executes changes from Aurora plans.

**Current Workaround**
1. View plan: `aur plan show plan-001`
2. Read tasks: Open `.aurora/plans/active/plan-001/tasks.md`
3. Implement manually following task list
4. Archive when done: `/aur:archive plan-001`

**Planned Features**
- Execute plan-based changes automatically
- Validate against acceptance criteria
- Track task completion
- Generate implementation reports

**Aurora Workflow (Manual for now)**
1. `aur plan create "Feature"` - Create plan
2. Review and refine plan
3. Implement tasks manually
4. `aur plan archive plan-001` - Archive completed

**Reference**
- `aur plan list` - See available plans
- `aur plan show <id>` - View plan details"""

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
    "search": SEARCH_TEMPLATE,
    "get": GET_TEMPLATE,
    "plan": PLAN_TEMPLATE,
    "checkpoint": CHECKPOINT_TEMPLATE,
    "implement": IMPLEMENT_TEMPLATE,
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
