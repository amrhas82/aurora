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
Run `aur mem search "<query>"` to search indexed code.

**Argument Parsing**
User can provide search terms with optional flags in natural order:
- `/aur:search bm25 limit 5` → `aur mem search "bm25" --limit 5`
- `/aur:search "exact phrase" type function` → `aur mem search "exact phrase" --type function`
- `/aur:search authentication` → `aur mem search "authentication"`

Parse intelligently: detect `limit N`, `type X` as flags, rest as query terms.

**Examples**
```bash
# Basic search
aur mem search "authentication handler"

# Search with type filter
aur mem search "validate" --type function

# Search with more results
aur mem search "config" --limit 20

# Natural argument order
aur mem search "bm25" --limit 5
```

**Reference**
- Returns file paths and line numbers
- Uses hybrid BM25 + embedding search
- Shows match scores
- Type filters: function, class, module

**Output Format (MANDATORY - NEVER DEVIATE)**

Every response MUST follow this exact structure:

1. Execute `aur mem search` with parsed args
2. Display the **FULL TABLE** - never collapse with "... +N lines"
3. Create a simplified table showing ALL results (not just top 3):
   ```
   #  | File:Line           | Type | Name              | Score
   ---|---------------------|------|-------------------|------
   1  | memory.py:131       | code | MemoryManager     | 0.81
   2  | tools.py:789        | code | _handle_record    | 0.79
   3  | logs/query.md:1     | docs | Execution Summary | 0.58
   ...
   ```
4. Add exactly 2 sentences of guidance on where to look:
   - Sentence 1: Identify the most relevant result(s) and why
   - Sentence 2: Suggest what other results might provide useful context
5. Single line: `Next: /aur:get N`

NO additional explanations or questions beyond these 2 sentences."""

# /aur:get - Get chunk by index
GET_TEMPLATE = f"""{BASE_GUARDRAILS}

**Usage**
Run `aur mem get <N>` to retrieve the full content of search result N from the last search.

**Examples**
```bash
# Get first result from last search
aur mem get 1

# Get third result
aur mem get 3
```

**Note:** The output includes detailed score breakdown (Hybrid, BM25, Semantic, Activation). For access count details, see the Activation score.

**Workflow**
1. Run `/aur:search <query>` to search
2. Review the numbered results
3. Run `/aur:get <N>` to see full content of result N

**Output**
- Full code content (not truncated)
- File path and line numbers
- Detailed score breakdown (Hybrid, BM25, Semantic, Activation)
- Syntax highlighting

**Notes**
- Results cached for 10 minutes after search
- Index is 1-based (first result = 1)
- Returns error if no previous search or index out of range

**Output Format (MANDATORY - NEVER DEVIATE)**

Every response MUST follow this exact structure:

1. Execute `aur mem get N`
2. Display the content box
3. One sentence: what this is and what it does (include file:line reference from the header)
4. If not code implementation: note the file type (e.g., "log file", "docs", "config")
5. Optional: If relevant to other search results, add: "See also: result #X (relationship)"

NO additional explanations, suggestions, or questions."""

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

# /aur:plan - Plan generation command (exact port from OpenSpec proposal template)
PLAN_GUARDRAILS = f"""{BASE_GUARDRAILS}
- Identify any vague or ambiguous details and ask the necessary follow-up questions before editing files.
- Do not write any code during the planning stage. Only create design documents (plan.md, tasks.md, design.md, and spec deltas). Implementation happens in the implement stage after approval."""

PLAN_STEPS = """**Steps**
1. Review `.aurora/project.md`, run `aur plan list` and `aur plan list --specs`, and inspect related code or docs (e.g., via `rg`/`ls`) to ground the plan in current behaviour; note any gaps that require clarification.
   - **If `goals.json` exists** (from `aur goals`): Read it and include subgoals with confidence >= 0.5 under `## Goals Context`. Skip low-confidence agents (these are gaps, not assignments).
   - **If no goals.json**: Run `aur agents list --format plan` and add the output under `## Available Agents` at the top of plan.md. Assign agents to each task/subgoal as you plan.
2. Choose a unique verb-led `plan-id` and scaffold `plan.md`, `tasks.md`, and `design.md` (when needed) under `.aurora/plans/active/<id>/`.
3. Map the change into concrete capabilities or requirements, breaking multi-scope efforts into distinct spec deltas with clear relationships and sequencing.
4. Capture architectural reasoning in `design.md` when the solution spans multiple systems, introduces new patterns, or demands trade-off discussion before committing to specs.
5. Draft spec deltas in `.aurora/plans/active/<id>/specs/<capability>/spec.md` (one folder per capability) using `## ADDED|MODIFIED|REMOVED Requirements` with at least one `#### Scenario:` per requirement and cross-reference related capabilities when relevant.
6. Draft `tasks.md` as an ordered list of small, verifiable work items that deliver user-visible progress, include validation (tests, tooling), and highlight dependencies or parallelizable work.
7. Validate with `aur plan validate <id> --strict` and resolve every issue before sharing the plan."""

PLAN_REFERENCES = """**Reference**
- Use `aur plan show <id> --json --deltas-only` or `aur plan show <spec> --type spec` to inspect details when validation fails.
- Search existing requirements with `rg -n "Requirement:|Scenario:" .aurora/specs` before writing new ones.
- Explore the codebase with `rg <keyword>`, `ls`, or direct file reads so plans align with current implementation realities.

**plan.md Format**:

*With goals.json* (only include agents with confidence >= 0.5):
```markdown
## Goals Context
> Source: `goals.json`

| Subgoal | Agent | Dependencies |
|---------|-------|--------------|
| [title] | @agent-id | - |
```

*Without goals.json* (run command, paste output):
```bash
aur agents list --format plan
```
Then add output under `## Available Agents` and assign agents to tasks."""

PLAN_TEMPLATE = f"""{PLAN_GUARDRAILS}

{PLAN_STEPS}

{PLAN_REFERENCES}"""

# /aur:proposal - Proposal generation command (exact port from OpenSpec proposal template)
PROPOSAL_GUARDRAILS = f"""{BASE_GUARDRAILS}
- Identify any vague or ambiguous details and ask the necessary follow-up questions before editing files.
- Do not write any code during the proposal stage. Only create design documents (proposal.md, tasks.md, design.md, and spec deltas). Implementation happens in the apply stage after approval."""

PROPOSAL_STEPS = """**Steps**
1. Review `.aurora/project.md`, run `aur plan list` and `aur plan list --specs`, and inspect related code or docs (e.g., via `rg`/`ls`) to ground the proposal in current behaviour; note any gaps that require clarification.
2. Choose a unique verb-led `plan-id` and scaffold `proposal.md`, `tasks.md`, and `design.md` (when needed) under `.aurora/plans/active/<id>/`.
3. Map the change into concrete capabilities or requirements, breaking multi-scope efforts into distinct spec deltas with clear relationships and sequencing.
4. Capture architectural reasoning in `design.md` when the solution spans multiple systems, introduces new patterns, or demands trade-off discussion before committing to specs.
5. Draft spec deltas in `.aurora/plans/active/<id>/specs/<capability>/spec.md` (one folder per capability) using `## ADDED|MODIFIED|REMOVED Requirements` with at least one `#### Scenario:` per requirement and cross-reference related capabilities when relevant.
6. Draft `tasks.md` as an ordered list of small, verifiable work items that deliver user-visible progress, include validation (tests, tooling), and highlight dependencies or parallelizable work.
7. Validate with `aur plan validate <id> --strict` and resolve every issue before sharing the proposal."""

PROPOSAL_REFERENCES = """**Reference**
- Use `aur plan show <id> --json --deltas-only` or `aur plan show <spec> --type spec` to inspect details when validation fails.
- Search existing requirements with `rg -n "Requirement:|Scenario:" .aurora/specs` before writing new ones.
- Explore the codebase with `rg <keyword>`, `ls`, or direct file reads so proposals align with current implementation realities."""

PROPOSAL_TEMPLATE = f"""{PROPOSAL_GUARDRAILS}

{PROPOSAL_STEPS}

{PROPOSAL_REFERENCES}"""

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
    "proposal": PROPOSAL_TEMPLATE,
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
