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
- Search codebase with memory system: `aur query <question>`"""

# /aur:query - Codebase query with memory
QUERY_TEMPLATE = f"""{BASE_GUARDRAILS}

**Usage**
Run `aur query "<your question>"` to search the codebase using Aurora's memory system.

**Features**
- Semantic search across indexed code
- Hybrid BM25 + embedding search
- Context-aware results with file paths and line numbers
- Automatic quality scoring (groundedness)

**Flags**
- `--context FILE` - Use specific files as context
- `--show-reasoning` - Display complexity assessment
- `--force-aurora` - Use full SOAR pipeline
- `--non-interactive` - No prompts (for CI/CD)

**Reference**
- Use `aur mem index` to index the codebase first
- Use `aur query --context file.py` to add specific files as context"""

# /aur:index - Index codebase for semantic search
INDEX_TEMPLATE = f"""{BASE_GUARDRAILS}

**Usage**
Run `aur mem index <path>` to index codebase for semantic search.

**Examples**
```bash
# Index entire project
aur mem index .

# Index specific directories
aur mem index src/ tests/

# Index with verbose output
aur mem index . --verbose
```

**Reference**
- Indexes Python files by default
- Creates chunks for semantic search
- Enables `aur query` functionality
- Index is stored in `.aurora/memory.db`"""

# /aur:search - Search indexed code
SEARCH_TEMPLATE = f"""{BASE_GUARDRAILS}

**Usage**
Run `aur mem search "<query>"` to search indexed code.

**Examples**
```bash
# Basic search
aur mem search "authentication handler"

# Search with type filter
aur mem search "validate" --type function

# Search with more results
aur mem search "config" --limit 20
```

**Reference**
- Returns file paths and line numbers
- Uses hybrid BM25 + embedding search
- Shows match scores
- Type filters: function, class, module"""

# /aur:init - Initialize Aurora
INIT_TEMPLATE = f"""{BASE_GUARDRAILS}

**Usage**
Run `aur init` to set up Aurora for the current project.

**What it creates**
- `.aurora/` directory with project-specific configuration
- Memory index for semantic code search
- Tool configurations (AGENTS.md, CLAUDE.md, etc.)

**Steps**
1. Run `aur init` in the project root
2. Follow the interactive prompts to:
   - Set up planning directories (requires git)
   - Index code for semantic search
   - Configure AI tool integrations
3. Verify setup with `aur doctor`

**Reference**
- Use `aur init --config` to reconfigure tools only"""

# /aur:doctor - Health checks
DOCTOR_TEMPLATE = f"""{BASE_GUARDRAILS}

**Usage**
Run `aur doctor` to check Aurora installation health.

**What it checks**
- Package installation status
- Python version compatibility
- Configuration files
- Memory database health
- API key configuration
- MCP server status

**Commands**
```bash
# Run health checks
aur doctor

# Auto-repair issues
aur doctor --fix
```"""

# /aur:agents - Agent discovery
AGENTS_TEMPLATE = f"""{BASE_GUARDRAILS}

**Usage**
Browse and search available AI agents.

**Commands**
```bash
# List all agents
aur agents list

# Search agents by keyword
aur agents search "test"

# Show full agent details
aur agents show qa-test-architect

# Force refresh agent manifest
aur agents refresh
```

**Agent types**
- Product agents: product-manager, product-owner
- Development agents: full-stack-dev, qa-test-architect
- Architecture agents: holistic-architect
- Process agents: scrum-master, orchestrator"""

# Command templates dictionary
COMMAND_TEMPLATES: dict[str, str] = {
    "plan": PLAN_TEMPLATE,
    "query": QUERY_TEMPLATE,
    "index": INDEX_TEMPLATE,
    "search": SEARCH_TEMPLATE,
    "init": INIT_TEMPLATE,
    "doctor": DOCTOR_TEMPLATE,
    "agents": AGENTS_TEMPLATE,
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
