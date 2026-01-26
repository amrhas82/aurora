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

# /aur:implement - Plan implementation
IMPLEMENT_TEMPLATE = f"""{BASE_GUARDRAILS}

**Usage**
Execute plan tasks sequentially with progress tracking.

**What it does**
1. Reads plan.md, tasks.md, and specs/ from plan directory
2. Executes tasks in order, marking each `- [x]` when complete
3. Validates completed work against spec scenarios when available

**Commands**
```bash
# Implement specific plan
/aur:implement 0001-add-auth

# Interactive selection (lists active plans)
/aur:implement
```

**Workflow**
1. Read `.aurora/plans/active/<plan-id>/plan.md` for context
2. Read `.aurora/plans/active/<plan-id>/tasks.md` for work items
3. Check `specs/` for formal requirements and scenarios (if exists)
4. For each task:
   - Execute the implementation
   - Run validation (tests, checks) from task description
   - Mark task complete: `- [ ]` → `- [x]`
5. On completion: suggest `/aur:archive <plan-id>`

**Validation**
- If `specs/<capability>/spec.md` exists, use scenarios as acceptance criteria
- Mark validation pass/fail in task completion notes
- Warn if spec scenarios not fully covered

**Reference**
- `aur plan list` - See active plans
- `aur plan show <id>` - View plan details"""

# /aur:plan - Plan generation command (matches OpenSpec proposal template exactly)
PLAN_GUARDRAILS = f"""{BASE_GUARDRAILS}
- Identify any vague or ambiguous details and ask the necessary follow-up questions before editing files.
- Do not write any code during the planning stage. Only create design documents (plan.md, tasks.md, design.md, and spec deltas). Implementation happens in the implement stage after approval."""

PLAN_STEPS = """**Steps**
1. Review `.aurora/project.md`, run `aur plan list` to see existing plans, and inspect related code or docs (e.g., via `rg`/`ls`) to ground the plan in current behaviour; note any gaps that require clarification.
   - **If input is a `goals.json` file (recommended for code-aware planning)**: Read it and populate the Goals Context table with subgoals, agents, files, and dependencies. Goals.json provides code-aware context including source_file mappings for each subgoal.
   - **If input is a prompt (valid but less structured)**: Continue with prompt-based planning. Run `aur agents list` to see available agents. Assign agents to tasks as you plan. Note: Agent searches will happen on-the-fly during implementation rather than upfront.
   - Both paths are valid; goals.json is recommended for production work as it grounds planning in actual codebase structure.
2. Choose a unique verb-led `plan-id` and generate artifacts in this order under `.aurora/plans/active/<id>/`:
   - First: `plan.md` (overview and strategy)
   - Second: `prd.md` (detailed product requirements)
   - Third: `design.md` (when needed - technical architecture)
   - Fourth: `agents.json` (agent assignments)
   - Last: `tasks.md` (depends on PRD content, generated after all other artifacts)
   Note: tasks.md is generated last because it needs complete PRD details to create accurate task breakdowns.
3. Map the change into concrete capabilities or requirements, breaking multi-scope efforts into distinct spec deltas with clear relationships and sequencing.
4. Capture architectural reasoning in `design.md` when the solution spans multiple systems, introduces new patterns, or demands trade-off discussion before committing to specs.
5. Draft spec deltas in `.aurora/plans/active/<id>/specs/<capability>/spec.md` (one folder per capability) using `## ADDED|MODIFIED|REMOVED Requirements` with at least one `#### Scenario:` per requirement and cross-reference related capabilities when relevant.
6. Draft `tasks.md` with `<!-- @agent: @name -->` comment after each parent task. Agent assignment priority: goals.json > agent registry match > LLM inference.
7. Review plan with `aur plan view <id>` and ensure all tasks are well-defined before sharing the plan."""

PLAN_REFERENCES = """**Reference**
- Use `aur plan view <id> --format json` to inspect plan details in JSON format.
- Search existing requirements with `rg -n "Requirement:|Scenario:" .aurora/specs` before writing new ones.
- Explore the codebase with `rg <keyword>`, `ls`, or direct file reads so plans align with current implementation realities.

**plan.md Template** (matches OpenSpec proposal.md sections):
```markdown
# Plan: [Brief description]

## Plan ID
`{plan-id}`

## Summary
[1-2 sentences]

## Goals Context
> Source: `goals.json` (if provided, otherwise omit this section)

| Subgoal | Agent | Files | Dependencies |
|---------|-------|-------|--------------|
| [title] | @agent-id | [memory_context files] | [dependencies] |

## Problem Statement
[Current state, pain points]

## Proposed Solution
[What changes]

## Benefits
[Why this helps]

## Scope
### In Scope
- [What's included]

### Out of Scope
- [What's excluded]

## Dependencies
[Systems, files, or other plans this depends on]

## Implementation Strategy
[Phased approach with task counts]

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|

## Success Criteria
- [ ] [Measurable outcome]

## Open Questions
1. [Question] - **Recommendation**: [answer]
```

**tasks.md Template** (with @agent per task and TDD hints):
```markdown
## Phase N: [Name]
- [ ] N.1 Task description
  <!-- @agent: @code-developer -->
  - tdd: yes|no
  - verify: `command to verify`
  - Details
  - **Validation**: How to verify

**TDD Detection Guidelines:**
- tdd: yes - For models, API endpoints, bug fixes, business logic, data transformations
- tdd: no - For docs, config files, migrations, pure refactors (no behavior change)
- Default: When unsure, use tdd: yes
```

**agents.json Template** (plan metadata with subgoals):
```json
{
  "plan_id": "unique-plan-identifier",
  "goal": "Original goal statement describing what needs to be achieved",
  "status": "active",
  "complexity": "moderate",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "subgoals": [
    {
      "id": "sg-1",
      "title": "Brief subgoal title",
      "description": "Detailed subgoal description explaining what needs to be done",
      "agent_id": "@code-developer",
      "status": "pending",
      "dependencies": []
    }
  ]
}
```

**agents.json Schema:**
- **plan_id** (required): Unique identifier for the plan
- **goal** (required): Original goal statement (10-500 chars)
- **status** (required): One of: active, completed, archived, failed
- **complexity** (optional): One of: simple, moderate, complex
- **created_at** (required): ISO 8601 timestamp (UTC)
- **updated_at** (required): ISO 8601 timestamp (UTC)
- **subgoals** (required): Array of subgoal objects (1-20 items)
  - **id**: Subgoal identifier (format: sg-N)
  - **title**: Brief subgoal title (5-100 chars, imperative form)
  - **description**: Detailed description (10-500 chars)
  - **agent_id**: Recommended agent (format: @agent-name)
  - **status**: One of: pending, in_progress, completed, blocked
  - **dependencies**: Array of subgoal IDs that must complete first

**Full schema reference:** `packages/planning/src/aurora_planning/schemas/agents.schema.json`
"""

# /aur:tasks - Regenerate tasks.md from PRD (carve-out from /aur:plan)
TASKS_GUARDRAILS = f"""{BASE_GUARDRAILS}
- Only regenerate tasks.md. Do not modify plan.md, prd.md, design.md, or agents.json.
- Read prd.md to understand requirements. Read agents.json for agent assignments. Read goals.json for source_file mappings if available."""

TASKS_STEPS = """**Steps**
1. Read `.aurora/plans/active/<plan-id>/prd.md` to understand requirements
2. Read `.aurora/plans/active/<plan-id>/agents.json` for agent assignments
3. Read `.aurora/plans/active/<plan-id>/goals.json` (if exists) for source_file mappings
4. Generate tasks.md with:
   - Task breakdown matching PRD requirements
   - Agent assignments from agents.json (use `<!-- @agent: @name -->` comment after each parent task)
   - TDD hints (tdd: yes|no, verify: command) matching format below
   - Validation steps per task
5. Save updated tasks.md (replaces existing)"""

TASKS_REFERENCES = """**tasks.md Template** (with @agent per task and TDD hints):
```markdown
## Phase N: [Name]
- [ ] N.1 Task description
  <!-- @agent: @code-developer -->
  - tdd: yes|no
  - verify: `command to verify`
  - Details
  - **Validation**: How to verify

**TDD Detection Guidelines:**
- tdd: yes - For models, API endpoints, bug fixes, business logic, data transformations
- tdd: no - For docs, config files, migrations, pure refactors (no behavior change)
- Default: When unsure, use tdd: yes
```

**Purpose**
Regenerate tasks.md after user edits PRD. The PRD is the source of truth for requirements; tasks.md must always reflect current PRD state.

**When to use**
- After editing prd.md to add/remove requirements
- After changing requirement scope or acceptance criteria
- When task breakdown no longer matches PRD structure"""

TASKS_TEMPLATE = f"""{TASKS_GUARDRAILS}

{TASKS_STEPS}

{TASKS_REFERENCES}"""

PLAN_TEMPLATE = f"""{PLAN_GUARDRAILS}

{PLAN_STEPS}

{PLAN_REFERENCES}"""

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
    "tasks": TASKS_TEMPLATE,
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
