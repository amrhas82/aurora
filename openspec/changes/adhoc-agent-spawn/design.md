# Design: Ad-hoc Agent Spawning

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      aur spawn CLI                          │
│                                                             │
│  1. Load tasks from tasks.md                               │
│  2. Check agent manifest for each agent                    │
│  3. If missing + --adhoc flag:                             │
│     → Trigger AdHocAgentInferrer                           │
│  4. Execute tasks with agents (manifest or ad-hoc)         │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              AdHocAgentInferrer (NEW)                       │
│                                                             │
│  - infer_agent(task_desc, agent_id) → AgentInfo           │
│  - infer_batch(tasks) → dict[agent_id, AgentInfo]         │
│  - Uses LLM client to generate role + goal                 │
│  - Validates inferred definitions                          │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│           AdHocAgentCache (NEW)                             │
│                                                             │
│  - store(agent_id, agent_info)                             │
│  - get(agent_id) → AgentInfo | None                        │
│  - Session-scoped: cleared after spawn completes           │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  aurora-spawner                             │
│                                                             │
│  - spawn(task, agent_info=None) → SpawnResult              │
│  - If agent_info provided, pass as context to CLI tool     │
└─────────────────────────────────────────────────────────────┘
```

## Component Design

### 1. AdHocAgentInferrer

**Location**: `packages/spawner/src/aurora_spawner/adhoc_inference.py`

**Responsibilities**:
- Infer agent role and goal from task description and agent ID
- Batch inference for multiple missing agents
- Validate inferred agent definitions

**Interface**:
```python
@dataclass
class InferredAgent:
    """Ad-hoc agent definition inferred from task context."""
    id: str
    role: str
    goal: str
    confidence: float  # 0.0-1.0, for future quality metrics

class AdHocAgentInferrer:
    """Infer agent definitions from task descriptions."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    async def infer_agent(
        self,
        task_description: str,
        agent_id: str,
    ) -> InferredAgent:
        """Infer single agent definition from task.

        Args:
            task_description: Task text describing what needs to be done
            agent_id: Agent identifier (e.g., "db-migration-expert")

        Returns:
            InferredAgent with role, goal, and confidence

        Raises:
            ValueError: If inference fails or produces invalid definition
        """
        ...

    async def infer_batch(
        self,
        tasks: list[tuple[str, str]],  # (task_desc, agent_id)
    ) -> dict[str, InferredAgent]:
        """Batch infer multiple agents from their tasks.

        More efficient than calling infer_agent repeatedly when
        multiple missing agents detected.

        Args:
            tasks: List of (task_description, agent_id) tuples

        Returns:
            Mapping of agent_id → InferredAgent
        """
        ...

    def validate_agent(self, agent: InferredAgent) -> bool:
        """Validate inferred agent meets minimum quality criteria.

        Checks:
        - Role is non-empty and ≤200 chars
        - Goal is non-empty and ≤500 chars
        - No placeholder text like "TODO" or "TBD"

        Returns:
            True if valid, False otherwise
        """
        ...
```

**Inference Prompt Design**:
```python
# packages/reasoning/src/aurora_reasoning/prompts/infer_agent.py

INFER_AGENT_PROMPT = """
You are helping generate an agent definition for a task execution system.

Given:
- Agent ID: {agent_id}
- Task Description: {task_description}

Generate a minimal agent definition with:
1. **Role**: A concise title for this agent (max 200 chars)
   - Example: "Database Migration Specialist"
   - Example: "Python Test Architect"

2. **Goal**: Brief description of the agent's purpose in context of this task (max 500 chars)
   - Example: "Execute PostgreSQL database schema migrations with attention to data integrity and rollback strategies"

Requirements:
- Role should be a job title or functional role
- Goal should be specific to the task domain
- Avoid generic phrases like "help the user" or "perform tasks"
- Focus on domain expertise implied by the agent ID and task

Respond in JSON:
{{
  "role": "...",
  "goal": "..."
}}
"""

INFER_BATCH_PROMPT = """
You are helping generate agent definitions for a task execution system.

Given a list of tasks with their agent IDs, generate definitions for each agent.

Tasks:
{tasks_json}

For each agent, provide:
1. **Role**: Concise title (max 200 chars)
2. **Goal**: Purpose in context of associated task (max 500 chars)

Respond in JSON:
{{
  "agent_id_1": {{"role": "...", "goal": "..."}},
  "agent_id_2": {{"role": "...", "goal": "..."}},
  ...
}}
"""
```

### 2. AdHocAgentCache

**Location**: `packages/spawner/src/aurora_spawner/adhoc_cache.py`

**Responsibilities**:
- Store inferred agents for reuse within a spawn session
- Prevent duplicate inference calls for same agent ID
- Clear cache after spawn completes (session-scoped)

**Interface**:
```python
class AdHocAgentCache:
    """Session-scoped cache for inferred agent definitions."""

    def __init__(self):
        self._cache: dict[str, InferredAgent] = {}

    def store(self, agent: InferredAgent) -> None:
        """Store inferred agent in cache."""
        self._cache[agent.id] = agent

    def get(self, agent_id: str) -> InferredAgent | None:
        """Get cached agent by ID."""
        return self._cache.get(agent_id)

    def has(self, agent_id: str) -> bool:
        """Check if agent is cached."""
        return agent_id in self._cache

    def clear(self) -> None:
        """Clear all cached agents."""
        self._cache.clear()

    def size(self) -> int:
        """Get number of cached agents."""
        return len(self._cache)
```

### 3. CLI Integration

**Location**: `packages/cli/src/aurora_cli/commands/spawn.py`

**Changes**:
```python
@click.command(name="spawn")
@click.argument("task_file", ...)
@click.option("--adhoc", is_flag=True, help="Enable ad-hoc agent inference for missing agents")
@click.option("--adhoc-log", type=click.Path(), help="Save inferred agent definitions to file")
def spawn_command(
    task_file: Path,
    parallel: bool,
    sequential: bool,
    verbose: bool,
    dry_run: bool,
    adhoc: bool,  # NEW
    adhoc_log: Path | None,  # NEW
) -> None:
    """Execute tasks with optional ad-hoc agent inference."""

    # Load tasks
    tasks = load_tasks(task_file)

    # Load agent manifest
    manifest = load_agent_manifest()

    # NEW: Detect missing agents
    missing_agents = detect_missing_agents(tasks, manifest)

    if missing_agents and not adhoc:
        # Fail fast (current behavior)
        console.print(f"[red]Error:[/] Missing agents: {', '.join(missing_agents)}")
        console.print("Use --adhoc to enable ad-hoc agent inference")
        raise click.Abort()

    # NEW: Infer missing agents
    inferred = {}
    if missing_agents and adhoc:
        console.print(f"[yellow]Inferring {len(missing_agents)} ad-hoc agents...[/]")
        inferred = await infer_missing_agents(tasks, missing_agents)

        if verbose:
            for agent_id, agent in inferred.items():
                console.print(f"  → {agent.role}: {agent.goal[:50]}...")

        # Optional: Log inferred agents
        if adhoc_log:
            save_inferred_agents(inferred, adhoc_log)

    # Execute tasks (existing logic + ad-hoc agents)
    result = await execute_tasks(tasks, manifest, inferred)
    ...
```

**Helper Functions**:
```python
def detect_missing_agents(
    tasks: list[ParsedTask],
    manifest: AgentManifest,
) -> list[str]:
    """Detect agent IDs referenced by tasks but not in manifest."""
    referenced = {t.agent for t in tasks if t.agent and t.agent != "self"}
    existing = {a.id for a in manifest.agents}
    return list(referenced - existing)

async def infer_missing_agents(
    tasks: list[ParsedTask],
    missing_agent_ids: list[str],
) -> dict[str, InferredAgent]:
    """Infer agent definitions for missing agents.

    Uses batch inference if >1 agent missing for efficiency.
    """
    # Build task→agent mapping
    agent_tasks = {}
    for task in tasks:
        if task.agent in missing_agent_ids:
            agent_tasks[task.agent] = task.description

    # Initialize inferrer
    from aurora_reasoning.llm_client import get_llm_client
    from aurora_spawner.adhoc_inference import AdHocAgentInferrer

    llm_client = get_llm_client()
    inferrer = AdHocAgentInferrer(llm_client)

    # Batch inference
    task_list = [(desc, agent_id) for agent_id, desc in agent_tasks.items()]
    inferred = await inferrer.infer_batch(task_list)

    return inferred

def save_inferred_agents(
    inferred: dict[str, InferredAgent],
    output_path: Path,
) -> None:
    """Save inferred agents to file for review/reuse."""
    output_path.write_text(
        json.dumps(
            {
                agent_id: {
                    "role": agent.role,
                    "goal": agent.goal,
                    "confidence": agent.confidence,
                }
                for agent_id, agent in inferred.items()
            },
            indent=2,
        )
    )
```

### 4. Spawner Integration

**Location**: `packages/spawner/src/aurora_spawner/spawner.py`

**Changes**:
```python
async def spawn(
    task: SpawnTask,
    tool: str | None = None,
    model: str | None = None,
    config: dict[str, Any] | None = None,
    on_output: Callable[[str], None] | None = None,
    agent_info: InferredAgent | None = None,  # NEW
) -> SpawnResult:
    """Spawn subprocess with optional ad-hoc agent context.

    Args:
        task: Task to execute
        ...existing args...
        agent_info: Optional ad-hoc agent definition (role + goal)

    Returns:
        SpawnResult with execution details
    """
    # Build command
    cmd = [resolved_tool, "-p", "--model", resolved_model]

    # Add agent flag if specified
    if task.agent:
        cmd.extend(["--agent", task.agent])

    # NEW: If ad-hoc agent provided, pass role/goal as context
    # Note: This assumes the CLI tool supports --agent-role and --agent-goal flags
    # For Claude Code, this would be added to ~/.claude/agents/ dynamically
    if agent_info:
        # Option 1: Pass via command flags (requires CLI tool support)
        cmd.extend([
            "--agent-role", agent_info.role,
            "--agent-goal", agent_info.goal,
        ])

        # Option 2: Inject into prompt
        # modified_prompt = f"Acting as {agent_info.role} ({agent_info.goal})\n\n{task.prompt}"
        # task = SpawnTask(prompt=modified_prompt, agent=task.agent, timeout=task.timeout)

    # ... existing spawn logic ...
```

**Note**: The exact mechanism for passing agent context to CLI tools needs clarification:
- **If CLI supports custom agent context**: Use command flags
- **If not**: Inject role/goal into prompt as system message

## Data Flow

### Scenario: Task with missing agent

```
1. User runs: aur spawn tasks.md --adhoc

2. spawn_command():
   - Loads tasks from tasks.md
   - Task 1: agent="db-migration-expert" (not in manifest)
   - detect_missing_agents() → ["db-migration-expert"]

3. infer_missing_agents():
   - Creates AdHocAgentInferrer
   - Calls inferrer.infer_batch([("Migrate schema...", "db-migration-expert")])
   - LLM generates: role="Database Migration Specialist", goal="Execute PostgreSQL migrations..."
   - Validates and returns InferredAgent

4. execute_tasks():
   - For Task 1, checks inferred agents
   - Passes InferredAgent to spawn()

5. spawn():
   - Builds command with agent context
   - Spawns subprocess with role/goal
   - Returns result

6. Display:
   - "✓ Task 1: Success (using ad-hoc agent)"
```

## Configuration

**Global Config** (`~/.aurora/config.json`):
```json
{
  "spawn": {
    "adhoc_default": false,
    "adhoc_confidence_threshold": 0.7,
    "adhoc_max_batch_size": 10,
    "adhoc_cache_session": true
  }
}
```

**Environment Variables**:
- `AURORA_SPAWN_ADHOC` - Enable ad-hoc by default (true/false)
- `AURORA_SPAWN_ADHOC_LOG` - Default path for ad-hoc logs

## Performance Considerations

**Inference Cost**:
- Single agent: ~500 tokens prompt + ~100 tokens response = 600 tokens
- Batch of 5: ~1000 tokens prompt + ~300 tokens response = 1300 tokens
- **Savings**: Batching saves ~60% tokens vs individual calls

**Caching Strategy**:
- Session-scoped cache prevents duplicate inferences within a spawn run
- Future: Persist to `~/.aurora/cache/adhoc_agents.json` with TTL

**Timeout Handling**:
- Inference has 10s timeout
- On timeout, fall back to direct LLM (agent=None)

## Testing Strategy

**Unit Tests**:
- `test_adhoc_inference.py` - AdHocAgentInferrer logic
- `test_adhoc_cache.py` - Cache behavior
- `test_spawn_adhoc.py` - CLI integration

**Integration Tests**:
- `test_spawn_adhoc_e2e.py` - End-to-end workflow with missing agents
- Mock LLM responses for deterministic testing

**Test Cases**:
1. Single missing agent inference
2. Batch inference (3+ agents)
3. Cache hit avoids duplicate inference
4. Invalid inference falls back gracefully
5. --adhoc-log writes correct JSON
6. Without --adhoc, fail fast with clear error

## Security Considerations

**Prompt Injection**:
- Task descriptions are user-controlled input
- Sanitize task descriptions before passing to LLM
- Use structured output format (JSON) to prevent injection

**Resource Limits**:
- Max 10 agents per batch inference
- 10s timeout per inference call
- Cached agents cleared after spawn completes

## Migration Path

**Phase 1** (This change):
- Implement core inference + caching
- CLI integration with `--adhoc` flag
- Basic validation

**Phase 2** (Future):
- Persistent ad-hoc agent cache with TTL
- `aur spawn promote-agent` command
- Custom inference templates

**Phase 3** (Future):
- Multi-task agent inference (detect same agent across tasks)
- Agent recommendation UI in SOAR
- Quality metrics and confidence scoring
